"""Owner membership signing never substitutes self-asserted payment for provider proof."""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import unittest

from ucie_miner import customer_membership_owner_sign_v01 as sign
from ucie_miner import customer_membership_subscription_v01 as sub
from ucie_miner import customer_private_entitlement_v01 as product
from ucie_miner import local_public_pr_owner_auth_v01 as owner


class OwnerSubscriptionRightsAndPaymentGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from ucie_public.rulepack import key_id
        except ImportError:
            raise unittest.SkipTest("real Ed25519 missing; native Windows must run this signer suite")
        cls.private=Ed25519PrivateKey.generate()  # synthetic in-memory only
        cls.key_id=key_id(cls.private.public_key())

    def record(self,**updates):
        start=datetime(2026,11,1,tzinfo=timezone.utc)
        end=datetime(2026,12,1,tzinfo=timezone.utc)
        r={
            "schema":sub.SCHEMA,"scope":sub.SCOPE,"service":"UCIE",
            "subscription_id_sha256":"a"*64,"recipient_token_sha256":"b"*64,
            "rights_packet_sha256":"c"*64,"owner_key_id":self.key_id,
            "plan":"standard","billing_interval":"monthly",
            "billing_status":"ACTIVE","payment_receipt_sha256":"d"*64,
            "renewal_sequence":1,"product_entitlement_min_serial":1,
            "issued_utc":owner._stamp(start),"period_start_utc":owner._stamp(start),
            "period_end_utc":owner._stamp(end),
            "grace_until_utc":owner._stamp(end),
            "access_lease_expires_utc":owner._stamp(end),
        }
        r.update(updates)
        return r

    def payment(self,record=None,**updates):
        r=record if record is not None else self.record()
        p={
            "schema":sign.PAYMENT_REVIEW_SCHEMA,
            "subscription_id_sha256":r["subscription_id_sha256"],
            "recipient_token_sha256":r["recipient_token_sha256"],
            "payment_receipt_sha256":r["payment_receipt_sha256"],
            "billing_interval":r["billing_interval"],
            "billing_status":r["billing_status"],
            "plan":r["plan"],
            "period_start_utc":r["period_start_utc"],
            "lease_issued_utc":r["issued_utc"],
            "customer_contract_signed_confirmed":True,
            "recurring_billing_disclosure_and_customer_consent_confirmed":True,
            "owner_verified_actual_provider_event":True,
            "customer_cancellation_intent_confirmed":(
                r["billing_status"]=="CANCEL_AT_PERIOD_END"),
        }
        p.update(updates)
        body=product.canonical(p)
        return body,sha256(body).hexdigest()

    def test_01_owner_can_review_consistent_payment_fields_structurally(self):
        rec=self.record()
        body,pin=self.payment(rec)
        result=sign._payment_review(body,expected_sha256=pin,record=rec)
        self.assertTrue(result["owner_verified_actual_provider_event"])
        self.assertNotIn("customer_name",result)

    def test_02_payment_independent_digest_mismatch_denied(self):
        body,pin=self.payment()
        with self.assertRaises(ValueError):
            sign._payment_review(body,expected_sha256="f"*64,record=self.record())

    def test_03_missing_human_recurring_charge_consent_denied(self):
        for k in ("recurring_billing_disclosure_and_customer_consent_confirmed",
                  "owner_verified_actual_provider_event",
                  "customer_contract_signed_confirmed"):
            body,pin=self.payment(**{k:False})
            with self.subTest(k=k),self.assertRaises(ValueError):
                sign._payment_review(body,expected_sha256=pin,record=self.record())

    def test_04_subscription_identity_period_or_plan_mismatch_denied(self):
        for field,value in (
            ("subscription_id_sha256","f"*64),
            ("recipient_token_sha256","e"*64),
            ("billing_interval","annual"),
            ("plan","complete"),
            ("payment_receipt_sha256","f"*64),
        ):
            body,pin=self.payment(**{field:value})
            with self.subTest(field=field),self.assertRaises(ValueError):
                sign._payment_review(body,expected_sha256=pin,record=self.record())

    def test_05_cancel_at_period_end_requires_actual_owner_cancel_intent(self):
        rec=self.record(billing_status="CANCEL_AT_PERIOD_END")
        body,pin=self.payment(rec,customer_cancellation_intent_confirmed=False)
        with self.assertRaises(ValueError):
            sign._payment_review(body,expected_sha256=pin,record=rec)
        body,pin=self.payment(rec,customer_cancellation_intent_confirmed=True)
        self.assertTrue(sign._payment_review(body,expected_sha256=pin,record=rec)[
            "customer_cancellation_intent_confirmed"])

    def test_06_extra_customer_pii_or_unknown_payment_metadata_denied(self):
        body,pin=self.payment(customer_email="x@example.com")
        with self.assertRaises(ValueError):
            sign._payment_review(body,expected_sha256=pin,record=self.record())

    def test_07_noncanonical_forged_approval_denied(self):
        raw=b'{"schema":"A","schema":"B"}\n'
        with self.assertRaises(ValueError):
            sign._payment_review(raw,expected_sha256=sha256(raw).hexdigest(),record=self.record())

    def test_08_no_owner_sensitive_keys_accessed_before_explicit_consent(self):
        with patch.object(owner,"_safe_small",
                          side_effect=AssertionError("owner file read forbidden")):
            with self.assertRaises(ValueError):
                sign._owner_gate(Path("D:/UCIE"),"YES")
            with self.assertRaises(ValueError):
                sign.owner_membership_sign_once(
                    Path("D:/UCIE"),record=self.record(),
                    private_filename="ucie_fake_private.pem",
                    public_filename="ucie_fake_trust.pem",
                    expected_owner_key_id=self.key_id,
                    decision_sha256="c"*64,
                    approved_payment_review_sha256="e"*64,consent="NO")

    def test_09_real_owner_key_not_generated_during_signer_import(self):
        self.assertFalse(hasattr(sign,"generate_key"))
        self.assertFalse(hasattr(sign,"issue_customer_without_payment"))
        self.assertEqual(sign.CONSENT,"OWNER_SIGN_UCIE_MEMBERSHIP_EXISTING_KEY_ONCE")

    def test_10_actual_real_signed_purpose_separation_synthetic_key_only(self):
        data=product.canonical(self.record())
        sig=sub._sig(data,self.private,consent=sign.CONSENT)
        self.assertNotEqual(sub.DOMAIN,product.DOMAIN)
        self.assertIn(b"UCIE_MEMBERSHIP_SUBSCRIPTION_ED25519_ATTESTATION_V01",sig)
        self.assertFalse(hasattr(sign,"payment_processor_charge"))

    def test_11_existing_legal_decision_sha_stays_owner_only(self):
        self.assertEqual(sign.PAYMENT_FILE,"ucie_membership_owner_reviewed_payment_v01.json")
        self.assertNotIn("payment_secret",sign.REVIEW_FIELDS)
        self.assertNotIn("credit_card",sign.REVIEW_FIELDS)


if __name__=="__main__":
    unittest.main()
