"""Owner signed membership import/renewal on an isolated fake recipient root."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from ucie_miner import customer_membership_recipient_v01 as receiver
from ucie_miner import customer_membership_subscription_v01 as mem
from ucie_miner import customer_private_entitlement_v01 as ent
from ucie_miner import local_public_pr_owner_auth_v01 as owner


class SignedMembershipRecipientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            from ucie_public.rulepack import key_id
        except ImportError:
            raise unittest.SkipTest("real native Ed25519 unavailable; no false PASS")
        cls.private=Ed25519PrivateKey.generate()
        cls.pub=cls.private.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.owner_id=key_id(cls.private.public_key())
        cls.now=datetime(2026,11,13,10,0,tzinfo=timezone.utc)
        cls.customer=sha256(b"UCIE FAKE RECEIVER").hexdigest()
        cls.subscription=sha256(b"UCIE FAKE SUBSCRIPTION").hexdigest()
        cls.rights="a"*64

    def record(self,seq=1,status="ACTIVE",plan="complete"):
        start=datetime(2026,11,1,tzinfo=timezone.utc)
        end=datetime(2026,12,1,tzinfo=timezone.utc)
        return {
            "schema":mem.SCHEMA,"scope":mem.SCOPE,"service":"UCIE",
            "subscription_id_sha256":self.subscription,
            "recipient_token_sha256":self.customer,
            "rights_packet_sha256":self.rights,
            "owner_key_id":self.owner_id,
            "plan":plan,"billing_interval":"monthly",
            "billing_status":status,
            "payment_receipt_sha256":"b"*64,
            "renewal_sequence":seq,"product_entitlement_min_serial":8,
            "issued_utc":owner._stamp(start),
            "period_start_utc":owner._stamp(start),
            "period_end_utc":owner._stamp(end),
            "grace_until_utc":owner._stamp(end),
        }

    def signed(self,seq=1,status="ACTIVE",plan="complete"):
        data=ent.canonical(self.record(seq=seq,status=status,plan=plan))
        return data,mem._sig(
            data,self.private,consent="OWNER_SIGN_UCIE_MEMBERSHIP_EXISTING_KEY_ONCE")

    def kwargs(self,**updates):
        data={
            "public_pem":self.pub,"expected_owner_key_id":self.owner_id,
            "expected_recipient_token_sha256":self.customer,
            "expected_rights_packet_sha256":self.rights,
            "expected_subscription_id_sha256":self.subscription,
            "min_product_serial":8,
            "min_renewal_sequence":1,
            "now":self.now,
        }
        data.update(updates)
        return data

    def root(self,base:Path):
        root=base/"UCIE_PRIVATE_RECIPIENT"
        root.mkdir()
        return root

    def product_stub(self):
        return {"owner_signed_serial":8,"customer_distribution_authorized":False}

    def add(self,root,record,sig,**kw):
        with patch.object(receiver.life,"verify_selected",return_value=self.product_stub()):
            return receiver.import_owner_signed_membership(
                root,record,sig,consent=receiver.CONSENT,**self.kwargs(**kw))

    def check(self,root,**kw):
        with patch.object(receiver.life,"verify_selected",return_value=self.product_stub()):
            return receiver.verify_installed_membership(root,**self.kwargs(**kw))

    def test_01_actual_signed_initial_snapshot_atomic_import(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            a,b=self.signed()
            result=self.add(root,a,b)
            self.assertEqual(result["renewal_sequence"],1)
            report=self.check(root)
            self.assertEqual(report["membership_phase"],"ACTIVE")
            self.assertTrue(report["existing_signed_product_verified_before_membership"])
            self.assertTrue((root/"membership"/"current.json").is_file())

    def test_02_idempotent_identical_signed_snapshot(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            a,b=self.signed()
            self.add(root,a,b)
            r=self.add(root,a,b)
            self.assertEqual(r["status"],"MEMBERSHIP_EXISTING_IDENTICAL_SNAPSHOT_NO_OP")

    def test_03_new_signed_renewal_increments_sequence(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            old,olds=self.signed(seq=1)
            new,news=self.signed(seq=2)
            self.add(root,old,olds)
            result=self.add(root,new,news)
            self.assertEqual(result["renewal_sequence"],2)
            self.assertEqual(self.check(root,min_renewal_sequence=2)["renewal_sequence"],2)

    def test_04_replay_old_renewal_denied_before_pointer_change(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            a,b=self.signed(seq=1)
            c,d=self.signed(seq=2)
            self.add(root,a,b)
            self.add(root,c,d)
            before=(root/"membership"/"current.json").read_bytes()
            with self.assertRaises(ValueError):
                self.add(root,a,b)
            self.assertEqual((root/"membership"/"current.json").read_bytes(),before)

    def test_05_same_sequence_different_signed_plan_denied(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            a,b=self.signed(seq=1,plan="standard")
            c,d=self.signed(seq=1,plan="complete")
            self.add(root,a,b)
            with self.assertRaises(ValueError):
                self.add(root,c,d)

    def test_06_signed_cancel_at_period_end_applied_as_new_sequence(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            self.add(root,*self.signed(seq=1))
            self.add(root,*self.signed(seq=2,status="CANCEL_AT_PERIOD_END"))
            self.assertEqual(self.check(root)["membership_phase"],"ENDING")
            self.assertEqual(self.check(root,now=datetime(
                2026,12,1,tzinfo=timezone.utc))["membership_phase"],"EXPIRED")

    def test_07_immediate_signed_revocation_blocks_access(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            self.add(root,*self.signed(seq=1))
            self.add(root,*self.signed(seq=2,status="REVOKED"))
            self.assertEqual(self.check(root)["allowed_pillars"],[])

    def test_08_missing_membership_does_not_infer_paid_access(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            with self.assertRaises(ValueError):
                self.check(root)

    def test_09_tampered_record_file_not_authorized(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            a,b=self.signed()
            self.add(root,a,b)
            selected=json.loads((root/"membership"/"current.json").read_bytes())
            path=root/"membership"/"snapshots"/selected["record_sha256"]/"member.json"
            raw=bytearray(path.read_bytes())
            raw[0]=ord("X")
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                self.check(root)

    def test_10_tampered_detached_signature_not_authorized(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            self.add(root,*self.signed())
            sel=json.loads((root/"membership"/"current.json").read_bytes())
            path=root/"membership"/"snapshots"/sel["record_sha256"]/"member.sig.json"
            path.write_bytes(b"FAKE")
            with self.assertRaises(ValueError):
                self.check(root)

    def test_11_wrong_customer_and_independent_renewal_floor_fail(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            self.add(root,*self.signed())
            for args in (
                {"expected_recipient_token_sha256":"e"*64},
                {"expected_subscription_id_sha256":"f"*64},
                {"min_renewal_sequence":2}):
                with self.subTest(args=args),self.assertRaises(ValueError):
                    self.check(root,**args)

    def test_12_no_user_output_deleted_during_expiry_or_revoke(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            marker=root.parent/"UCIE_CUSTOMER_OUTPUT_PRESERVED.txt"
            marker.write_text("CUSTOMER OWNED NON-UCIE TEST DATA")
            self.add(root,*self.signed())
            self.add(root,*self.signed(seq=2,status="SUSPENDED"))
            self.assertEqual(marker.read_text(),"CUSTOMER OWNED NON-UCIE TEST DATA")
            self.assertEqual(self.check(root)["membership_phase"],"SUSPENDED")

    def test_13_missing_consent_denies_before_changes(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            a,b=self.signed()
            with self.assertRaises(ValueError):
                receiver.import_owner_signed_membership(
                    root,a,b,consent="YES",**self.kwargs())
            self.assertEqual(set(root.iterdir()),set())

    def test_14_membership_active_highwater_has_independent_floor_limit(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            self.add(root,*self.signed(seq=2))
            with self.assertRaises(ValueError):
                self.check(root,min_renewal_sequence=3)
            self.assertEqual(self.check(root,min_renewal_sequence=2)["renewal_sequence"],2)

    def test_15_existing_product_check_required_before_member_record(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            a,b=self.signed()
            with patch.object(receiver.life,"verify_selected",
                              side_effect=ValueError("old product revoked")):
                with self.assertRaises(ValueError):
                    receiver.import_owner_signed_membership(
                        root,a,b,consent=receiver.CONSENT,**self.kwargs())
            self.assertFalse((root/"membership").exists())

    def test_16_other_directory_or_untrusted_symlink_not_used(self):
        with TemporaryDirectory() as tmp:
            root=self.root(Path(tmp))
            a,b=self.signed()
            (root/"unauthorized-private").mkdir()
            with self.assertRaises(ValueError):
                self.add(root,a,b)
            self.assertFalse((root/"membership").exists())


if __name__=="__main__":
    unittest.main()
