"""Paid UCIE membership engine contract, real Ed25519 with SYNTHETIC keys."""
from __future__ import annotations

from base64 import b64decode,b64encode
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
import unittest

from ucie_miner import customer_membership_subscription_v01 as member
from ucie_miner import customer_private_entitlement_v01 as product
from ucie_miner import local_public_pr_owner_auth_v01 as owner
from ucie_miner.customer_staging_v01 import PILLARS


class MembershipSignedAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            from ucie_public.rulepack import key_id
        except ImportError:
            raise unittest.SkipTest("actual cryptography absent; native Windows must run all membership tests")
        cls.private=Ed25519PrivateKey.generate()
        cls.other=Ed25519PrivateKey.generate()
        cls.keyid=key_id(cls.private.public_key())
        cls.pub=cls.private.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.now=datetime(2026,11,13,6,0,tzinfo=timezone.utc)
        cls.start=datetime(2026,11,1,tzinfo=timezone.utc)
        cls.end=datetime(2026,12,1,tzinfo=timezone.utc)
        cls.recipient=sha256(b"UCIE SYNTHETIC member device").hexdigest()
        cls.subid=sha256(b"UCIE SYNTHETIC subscription id").hexdigest()
        cls.rights="b"*64
        cls.payment="a"*64

    def record(self,**updates):
        data={
            "schema":member.SCHEMA,"scope":member.SCOPE,"service":"UCIE",
            "subscription_id_sha256":self.subid,
            "recipient_token_sha256":self.recipient,
            "rights_packet_sha256":self.rights,
            "owner_key_id":self.keyid,
            "plan":"complete","billing_interval":"monthly",
            "billing_status":"ACTIVE",
            "payment_receipt_sha256":self.payment,
            "renewal_sequence":1,
            "product_entitlement_min_serial":8,
            "issued_utc":owner._stamp(self.start),
            "period_start_utc":owner._stamp(self.start),
            "period_end_utc":owner._stamp(self.end),
            "grace_until_utc":owner._stamp(self.end),
            "access_lease_expires_utc":owner._stamp(self.end),
        }
        data.update(updates)
        return data

    def signed(self,**updates):
        body=product.canonical(self.record(**updates))
        sig=member._sig(body,self.private,
            consent="OWNER_SIGN_UCIE_MEMBERSHIP_EXISTING_KEY_ONCE")
        return body,sig

    def verify(self,**updates):
        a,b=self.signed()
        args=dict(
            record_bytes=a,signature_bytes=b,public_pem=self.pub,
            expected_owner_key_id=self.keyid,
            expected_subscription_id_sha256=self.subid,
            expected_recipient_token_sha256=self.recipient,
            expected_rights_packet_sha256=self.rights,
            actual_product_serial=8,min_renewal_sequence=1,now=self.now)
        args.update(updates)
        return member.verify_membership(**args)

    def test_01_true_ed25519_full_complete_monthly_four_pillars(self):
        r=self.verify()
        self.assertTrue(r["owner_membership_signature_verified"])
        self.assertEqual(r["membership_phase"],"ACTIVE")
        self.assertEqual(r["allowed_pillars"],list(PILLARS))
        self.assertFalse(r["independent_payment_provider_event_verified"])
        self.assertFalse(r["membership_is_sale_of_perpetual_install"])

    def test_02_standard_plan_exact_subset_and_deep_url_denial(self):
        body,sig=self.signed(plan="standard")
        r=self.verify(record_bytes=body,signature_bytes=sig)
        self.assertEqual(len(r["allowed_pillars"]),2)
        self.assertTrue(member.route_access("/local/error",r))
        self.assertTrue(member.route_access("/local/library",r))
        for route in ("/local/engine","/local/evolution"):
            self.assertFalse(member.route_access(route,r))

    def test_03_all_known_routes_require_real_verified_grant(self):
        result=self.verify()
        for route in list(member.ROUTE_TO_PILLAR)+list(member.NON_FEATURE_ROUTES):
            self.assertTrue(member.route_access(route,result),route)
        self.assertFalse(member.route_access("/local/hidden-secret",result))
        self.assertFalse(member.route_access("/local",{"allowed_pillars":list(PILLARS)}))

    def test_04_calendar_month_february_and_december(self):
        self.assertEqual(
            member._period_end(datetime(2026,1,31,tzinfo=timezone.utc),"monthly"),
            datetime(2026,2,28,tzinfo=timezone.utc))
        self.assertEqual(
            member._period_end(datetime(2026,12,31,tzinfo=timezone.utc),"monthly"),
            datetime(2027,1,31,tzinfo=timezone.utc))
        self.assertEqual(
            member._period_end(datetime(2024,1,31,tzinfo=timezone.utc),"monthly"),
            datetime(2024,2,29,tzinfo=timezone.utc))

    def test_05_calendar_annual_leap_year(self):
        self.assertEqual(
            member._period_end(datetime(2024,2,29,tzinfo=timezone.utc),"annual"),
            datetime(2025,2,28,tzinfo=timezone.utc))
        start=datetime(2026,4,3,tzinfo=timezone.utc)
        body,sig=self.signed(
            billing_interval="annual",
            period_start_utc=owner._stamp(start),
            period_end_utc=owner._stamp(start.replace(year=2027)),
            grace_until_utc=owner._stamp(start.replace(year=2027)),
            access_lease_expires_utc=owner._stamp(start+timedelta(days=35)),
            issued_utc=owner._stamp(start))
        self.assertEqual(
            self.verify(record_bytes=body,signature_bytes=sig,now=start+timedelta(days=210))["billing_interval"],
            "annual")

    def test_06_paid_expiry_blocks_even_valid_signature(self):
        self.assertEqual(
            self.verify(now=self.end)["membership_phase"],"EXPIRED")
        self.assertFalse(member.route_access("/local/library",self.verify(now=self.end)))
        self.assertFalse(member.route_access("/local",self.verify(now=self.end)))

    def test_07_cancel_at_period_end_does_not_terminate_paid_use_early(self):
        b,s=self.signed(billing_status="CANCEL_AT_PERIOD_END")
        before=self.verify(record_bytes=b,signature_bytes=s)
        self.assertEqual(before["membership_phase"],"ENDING")
        self.assertTrue(before["cancel_at_period_end"])
        self.assertTrue(member.route_access("/local/engine",before))
        after=self.verify(record_bytes=b,signature_bytes=s,now=self.end)
        self.assertEqual(after["membership_phase"],"EXPIRED")

    def test_08_past_due_grace_library_only_then_expired(self):
        b,s=self.signed(billing_status="PAST_DUE",
            grace_until_utc=owner._stamp(self.end+timedelta(days=3)),
            access_lease_expires_utc=owner._stamp(self.end+timedelta(days=3)))
        r=self.verify(record_bytes=b,signature_bytes=s,now=self.end+timedelta(days=2))
        self.assertEqual(r["membership_phase"],"GRACE_READ_ONLY")
        self.assertTrue(member.route_access("/local/library",r))
        self.assertFalse(member.route_access("/local/engine",r))
        self.assertFalse(member.route_access("/local/skillbook-run",r))
        self.assertFalse(member.route_access("/local/review",r))
        self.assertEqual(
            self.verify(record_bytes=b,signature_bytes=s,
                now=self.end+timedelta(days=3))["membership_phase"],"EXPIRED")

    def test_09_long_grace_and_unsanctioned_grace_rejected(self):
        for status,offset in (("ACTIVE",1),("PAST_DUE",8)):
            data=self.record(
                billing_status=status,
                grace_until_utc=owner._stamp(self.end+timedelta(days=offset)))
            with self.subTest(status=status),self.assertRaises(ValueError):
                member._record_checks(data)

    def test_10_revoked_and_suspended_block_before_expiry(self):
        for state in ("REVOKED","SUSPENDED"):
            b,s=self.signed(billing_status=state)
            r=self.verify(record_bytes=b,signature_bytes=s)
            self.assertEqual(r["membership_phase"],state)
            self.assertEqual(r["allowed_pillars"],[])
            self.assertFalse(member.route_access("/local",r))

    def test_11_future_period_is_not_active(self):
        start=datetime(2026,12,1,tzinfo=timezone.utc)
        end=datetime(2027,1,1,tzinfo=timezone.utc)
        b,s=self.signed(period_start_utc=owner._stamp(start),
            period_end_utc=owner._stamp(end),
            grace_until_utc=owner._stamp(end))
        self.assertEqual(
            self.verify(record_bytes=b,signature_bytes=s)["membership_phase"],
            "NOT_STARTED")

    def test_12_different_customer_or_subscription_denied(self):
        for field,value in (("expected_subscription_id_sha256","f"*64),
            ("expected_recipient_token_sha256","e"*64),
            ("expected_rights_packet_sha256","c"*64),
            ("expected_owner_key_id","d"*32)):
            with self.subTest(field=field),self.assertRaises(ValueError):
                self.verify(**{field:value})

    def test_13_old_renewal_sequence_and_old_product_serial_denied(self):
        with self.assertRaises(ValueError):
            self.verify(min_renewal_sequence=2)
        with self.assertRaises(ValueError):
            self.verify(actual_product_serial=7)

    def test_14_time_rollback_before_issue_denied(self):
        with self.assertRaises(ValueError):
            self.verify(now=self.start-timedelta(days=1))

    def test_15_wrong_owner_trust_key_denied(self):
        from cryptography.hazmat.primitives import serialization
        p=self.other.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        with self.assertRaises(ValueError):
            self.verify(public_pem=p)

    def test_16_wrong_domain_public_product_signature_denied(self):
        body,sig=self.signed()
        other=json.loads(sig)
        other["scope"]=product.SCOPE
        with self.assertRaises(ValueError):
            self.verify(record_bytes=body,signature_bytes=product.canonical(other))
        self.assertNotEqual(member.DOMAIN,product.DOMAIN)

    def test_17_signature_tampering_denied(self):
        body,sig=self.signed()
        data=json.loads(sig)
        bits=bytearray(b64decode(data["signature_base64"]))
        bits[4]^=1
        data["signature_base64"]=b64encode(bits).decode("ascii")
        with self.assertRaises(ValueError):
            self.verify(record_bytes=body,signature_bytes=product.canonical(data))

    def test_18_published_claim_cannot_be_payment_processor_proof(self):
        r=self.verify()
        self.assertFalse(r["independent_payment_provider_event_verified"])
        self.assertTrue(r["owner_asserted_payment_receipt_sha256_is_not_billing_api_proof"])
        self.assertTrue(r["customer_owned_work_products_not_deleted"])

    def test_19_invalid_invoice_dates_and_plan_deny(self):
        for change in (
            {"plan":"FREE_UNAUTHORIZED"},
            {"billing_interval":"lifetime"},
            {"period_end_utc":owner._stamp(self.end+timedelta(days=1))},
            {"payment_receipt_sha256":"0"*64},
            {"billing_status":"CANCELED_BUT_STILL_ACTIVE"},
            {"renewal_sequence":True},
            {"product_entitlement_min_serial":0},
            {"access_lease_expires_utc":owner._stamp(self.end+timedelta(days=1))},
            {"access_lease_expires_utc":owner._stamp(self.start)}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                member._record_checks(self.record(**change))

    def test_20_canonical_duplicate_nan_or_oversized_payload_denied(self):
        for data in (b'{"schema":"a","schema":"b"}\n',
             b'{"period_start_utc": NaN}\n',b"a"*(member.MAX_RECORD+1)):
            with self.subTest(data=data[:40]),self.assertRaises(ValueError):
                self.verify(record_bytes=data)

    def test_21_membership_sign_requires_separate_real_owner_consent(self):
        body=product.canonical(self.record())
        for value in ("", "YES", product.SCOPE):
            with self.subTest(consent=value),self.assertRaises(ValueError):
                member._sig(body,self.private,consent=value)
        with self.assertRaises(ValueError):
            member._sig(body,b"fake-private-key",consent="OWNER_SIGN_UCIE_MEMBERSHIP_EXISTING_KEY_ONCE")

    def test_22_wrong_record_fields_cannot_modify_feature_list(self):
        wrong=self.record()
        wrong["allowed_pillars"]=list(PILLARS)
        with self.assertRaises(ValueError):
            member._record_checks(wrong)
        wrong=self.record()
        wrong["plan"]="standard"
        # Rights are derived from a verified plan, not a user-editable list.
        self.assertNotIn("allowed_pillars",member.FIELDS)

    def test_23_fixed_receipt_not_hidden_by_new_app_status(self):
        report=self.verify()
        self.assertFalse(report["customer_distribution_authorized"])
        self.assertFalse(report["automatic_customer_code_collection"])
        self.assertEqual(report["operating_database_writes"],0)


    def test_24_annual_subscription_lease_ends_before_annual_payment(self):
        start=datetime(2026,2,10,tzinfo=timezone.utc)
        end=start.replace(year=2027)
        lease=start+timedelta(days=35)
        b,s=self.signed(billing_interval="annual",
            period_start_utc=owner._stamp(start),
            period_end_utc=owner._stamp(end),
            grace_until_utc=owner._stamp(end),
            issued_utc=owner._stamp(start),
            access_lease_expires_utc=owner._stamp(lease))
        r=self.verify(record_bytes=b,signature_bytes=s,now=lease)
        self.assertEqual(r["membership_phase"],"LEASE_REFRESH_REQUIRED")
        self.assertEqual(r["billing_interval"],"annual")
        self.assertFalse(member.route_access("/local/library",r))
        # A second owner review may issue a short lease in the SAME paid year
        # without pretending the customer was charged again.
        renewed=self.record(billing_interval="annual",
            period_start_utc=owner._stamp(start),
            period_end_utc=owner._stamp(end),
            grace_until_utc=owner._stamp(end),
            issued_utc=owner._stamp(start+timedelta(days=32)),
            access_lease_expires_utc=owner._stamp(start+timedelta(days=67)),
            renewal_sequence=2)
        raw=product.canonical(renewed)
        sig=member._sig(raw,self.private,
            consent="OWNER_SIGN_UCIE_MEMBERSHIP_EXISTING_KEY_ONCE")
        active=self.verify(record_bytes=raw,signature_bytes=sig,
            min_renewal_sequence=2,now=start+timedelta(days=36))
        self.assertEqual(active["membership_phase"],"ACTIVE")
        self.assertTrue(active["offline_lease_must_be_refreshed_without_rebilling"])


    def test_25_long_lived_product_integrity_is_not_paid_membership(self):
        from ucie_miner.customer_owner_wheelhouse_acquire_v01 import PINNED
        vendors={name:sha256(name.encode()).hexdigest() for name,_ in PINNED}
        artifact={
            "schema":product.SCHEMA,"scope":product.SCOPE,
            "product":product.DIST,"product_version":product.VERSION,
            "product_wheel_sha256":"a"*64,
            "vendor_wheels_sha256":vendors,
            "recipient_token_sha256":self.recipient,
            "rights_packet_sha256":self.rights,
            "four_pillars":list(PILLARS),
            "serial":8,"owner_key_id":self.keyid,
            "issued_utc":owner._stamp(self.now),
            "expires_utc":owner._stamp(
                self.now+timedelta(days=product.SUBSCRIPTION_PRODUCT_ARTIFACT_DAYS)),
        }
        body,signature=product.synthetic_fixture_signing_bytes(artifact,self.private)
        verified=product.verify_private_entitlement(
            body,signature,self.pub,expected_owner_key_id=self.keyid,
            min_serial=8,expected_recipient_token_sha256=self.recipient,
            expected_product_wheel_sha256="a"*64,
            expected_vendor_wheels_sha256=vendors,
            expected_rights_packet_sha256=self.rights,
            now=self.now+timedelta(days=700))
        self.assertEqual(verified["artifact_entitlement_validity_days"],1095)
        self.assertTrue(verified["commercial_access_still_requires_separate_signed_membership"])
        # An arbitrary never-ending artifact is never signed-in as paid membership.
        artifact["expires_utc"]=owner._stamp(self.now+timedelta(days=1096))
        newer,detached=product.synthetic_fixture_signing_bytes(artifact,self.private)
        with self.assertRaises(ValueError):
            product.verify_private_entitlement(
                newer,detached,self.pub,expected_owner_key_id=self.keyid,
                min_serial=8,expected_recipient_token_sha256=self.recipient,
                expected_product_wheel_sha256="a"*64,
                expected_vendor_wheels_sha256=vendors,
                expected_rights_packet_sha256=self.rights,now=self.now)


if __name__=="__main__":
    unittest.main()
