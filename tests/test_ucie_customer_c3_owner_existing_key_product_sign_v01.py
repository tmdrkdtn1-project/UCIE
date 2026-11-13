"""C3 owner existing key signer: real Ed25519 in memory, owner access deny by default."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from hashlib import sha256
from unittest.mock import patch
import unittest
from pathlib import Path

from ucie_miner import customer_c3_owner_existing_key_product_sign_v01 as signer
from ucie_miner import customer_private_entitlement_v01 as c3
from ucie_miner import local_public_pr_owner_auth_v01 as auth
from ucie_miner.customer_staging_v01 import PILLARS


class ExistingOwnerPrivateCustomerSigningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            from ucie_public.rulepack import key_id
        except ImportError:
            raise unittest.SkipTest("real Ed25519 vendor absent; no signer crypto PASS")
        cls.key=Ed25519PrivateKey.generate() # ONLY synthetic ephemeral memory
        cls.pub=cls.key.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.keyid=key_id(cls.key.public_key())
        cls.now=datetime(2026,11,13,9,0,tzinfo=timezone.utc)
        cls.rights="d"*64
        cls.recipient="e"*64
        cls.vendors={"cryptography":"1"*64,"cffi":"2"*64,"pycparser":"3"*64}

    def record(self,**updates):
        base={
            "schema":c3.SCHEMA,"scope":c3.SCOPE,
            "product":c3.DIST,"product_version":"0.1.0",
            "product_wheel_sha256":"c"*64,
            "vendor_wheels_sha256":self.vendors,
            "recipient_token_sha256":self.recipient,
            "rights_packet_sha256":self.rights,
            "four_pillars":list(PILLARS),
            "serial":17,"owner_key_id":self.keyid,
            "issued_utc":auth._stamp(self.now),
            "expires_utc":auth._stamp(self.now+timedelta(days=30)),
        }
        base.update(updates)
        return base

    def decision(self,**updates):
        base={k:True for k in signer.REQUIRED_DECISION_TRUE}
        base.update({
            "schema":signer.DECISION_SCHEMA,
            "security_disposition":"HUMAN_ACCEPTED_DOCUMENTED_RESTRICTED_5_LOW_CVE_RISK",
            "customer_distribution_authorized":False,
        })
        base.update(updates)
        data=c3.canonical(base)
        return data,sha256(data).hexdigest()

    def test_01_exact_five_cves_approved_decision_structure_only(self):
        raw,pin=self.decision()
        accepted=signer._decision_bytes(raw,independently_approved_sha256=pin)
        self.assertTrue(accepted["actual_vendor_license_notice_copyright_human_approved"])
        self.assertFalse(accepted["customer_distribution_authorized"])
        self.assertNotIn("customer_name",accepted)

    def test_02_owner_approval_sha_mismatch_rejected(self):
        raw,pin=self.decision()
        with self.assertRaises(ValueError):
            signer._decision_bytes(raw,independently_approved_sha256="f"*64)

    def test_03_missing_any_human_consent_denied(self):
        for requirement in signer.REQUIRED_DECISION_TRUE:
            raw,pin=self.decision(**{requirement:False})
            with self.subTest(requirement=requirement),self.assertRaises(ValueError):
                signer._decision_bytes(raw,independently_approved_sha256=pin)

    def test_04_unknown_security_disposition_denied(self):
        raw,pin=self.decision(security_disposition="I_SKIPPED_THE_CVES")
        with self.assertRaises(ValueError):
            signer._decision_bytes(raw,independently_approved_sha256=pin)

    def test_05_duplicate_untrusted_decision_fields_denied(self):
        raw=b'{"schema":"a","schema":"b"}\n'
        with self.assertRaises(ValueError):
            signer._decision_bytes(raw,independently_approved_sha256=sha256(raw).hexdigest())

    def test_06_new_key_generation_not_in_owner_signer(self):
        self.assertFalse(hasattr(signer,"generate_owner_key"))
        self.assertFalse(hasattr(signer,"create_owner_private_key"))
        self.assertFalse(hasattr(signer,"install_owner_private_key"))

    def test_07_owner_preflight_denies_before_any_private_reads(self):
        with patch.object(signer.auth,"_safe_small",
                          side_effect=AssertionError("sensitive key read")):
            with self.assertRaises(ValueError):
                signer._owner_gate(Path("D:/UCIE"),consent="YES")
            with self.assertRaises(ValueError):
                signer.owner_sign_once(
                    Path("D:/UCIE"),product_wheel=Path("D:/UCIE/downloaded/a.whl"),
                    existing_private_filename="ucie_c3_public_metadata_owner_private.pem",
                    existing_public_trust_filename="ucie_c3_public_metadata_owner_trust.pem",
                    expected_owner_key_id=self.keyid,expected_product_sha256="c"*64,
                    expected_vendor_sha256=self.vendors,
                    recipient_token_sha256=self.recipient,
                    decision_sha256="d"*64,
                    serial=17,consent="BAD")
        self.assertTrue(True)

    def test_08_crypto_real_ed25519_purpose_signature_with_memory_key(self):
        record=self.record()
        body,sig=signer._real_record_and_detached_signature(
            record,self.key,consent=signer.CONSENT)
        result=c3.verify_private_entitlement(
            body,sig,self.pub,expected_owner_key_id=self.keyid,
            expected_product_wheel_sha256="c"*64,
            expected_vendor_wheels_sha256=self.vendors,
            expected_recipient_token_sha256=self.recipient,
            expected_rights_packet_sha256=self.rights,
            min_serial=17,now=self.now+timedelta(hours=1))
        self.assertTrue(result["private_product_ed25519_signature_verified"])
        self.assertFalse(result["customer_distribution_authorized"])
        self.assertFalse(result["real_owner_signing_proven"])

    def test_09_unsigned_or_wrong_purpose_rejected(self):
        with self.assertRaises(ValueError):
            signer._real_record_and_detached_signature(
                self.record(),self.key,consent="no")
        with self.assertRaises(ValueError):
            signer._real_record_and_detached_signature(
                self.record(scope=auth.SCOPE),self.key,consent=signer.CONSENT)

    def test_10_mismatched_owner_key_identifier_denied(self):
        with self.assertRaises(ValueError):
            signer._real_record_and_detached_signature(
                self.record(owner_key_id="f"*32),self.key,consent=signer.CONSENT)

    def test_11_fake_key_bytes_denied(self):
        with self.assertRaises(ValueError):
            signer._real_record_and_detached_signature(
                self.record(),b"secret",consent=signer.CONSENT)

    def test_12_real_crypto_wheel_or_recipient_pin_tampering_denied(self):
        body,sig=signer._real_record_and_detached_signature(
            self.record(),self.key,consent=signer.CONSENT)
        for updates in (
            {"expected_product_wheel_sha256":"f"*64},
            {"expected_recipient_token_sha256":"a"*64},
            {"expected_rights_packet_sha256":"a"*64},
            {"min_serial":18},
        ):
            args=dict(
                record_bytes=body,signature_bytes=sig,
                independently_provisioned_public_pem=self.pub,
                expected_owner_key_id=self.keyid,
                expected_product_wheel_sha256="c"*64,
                expected_vendor_wheels_sha256=self.vendors,
                expected_recipient_token_sha256=self.recipient,
                expected_rights_packet_sha256=self.rights,
                min_serial=17,now=self.now+timedelta(hours=1))
            args.update(updates)
            with self.subTest(updates=updates),self.assertRaises(ValueError):
                c3.verify_private_entitlement(**args)

    def test_13_no_staged_keys_or_owner_contracts_from_unit_test(self):
        self.assertTrue(signer.OUT_PREFIX.startswith("ucie_c3_owner_"))
        self.assertTrue(signer.DECISION_FILE.endswith(".json"))
        self.assertNotIn("customer_name",signer.REQUIRED_DECISION_TRUE)


if __name__ == "__main__":
    unittest.main()
