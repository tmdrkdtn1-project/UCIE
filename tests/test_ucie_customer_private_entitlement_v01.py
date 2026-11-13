"""C3 complete four-pillar private release technical verifier; synthetic keys ONLY."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from base64 import b64decode, b64encode
import json
import unittest

from ucie_miner import customer_private_entitlement_v01 as auth
from ucie_miner import local_public_pr_owner_auth_v01 as c3_public
from ucie_miner.customer_owner_wheelhouse_acquire_v01 import PINNED
from ucie_miner.customer_staging_v01 import PILLARS


class C3CustomerReleaseEntitlementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            from ucie_public.rulepack import key_id
        except ImportError:
            raise unittest.SkipTest("real crypto missing; no C3 PASS")
        cls.pr = Ed25519PrivateKey.generate()
        cls.another = Ed25519PrivateKey.generate()
        cls.keyid = key_id(cls.pr.public_key())
        cls.public_pem = cls.pr.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.now = datetime(2026, 11, 13, 7, 0, tzinfo=timezone.utc)
        cls.wheel_hash = "a"*64
        cls.rights = "b"*64
        cls.recipient = sha256(b"UCIE-SYNTHETIC-NOT-A-REAL-CUSTOMER").hexdigest()
        cls.vendors = {name: (str(i + 1)*64) for i, (name, _) in enumerate(PINNED)}

    def setUp(self):
        self.record = {
            "schema": auth.SCHEMA,
            "scope": auth.SCOPE,
            "product": auth.DIST,
            "product_version": auth.VERSION,
            "product_wheel_sha256": self.wheel_hash,
            "vendor_wheels_sha256": self.vendors,
            "recipient_token_sha256": self.recipient,
            "rights_packet_sha256": self.rights,
            "four_pillars": list(PILLARS),
            "serial": 8,
            "owner_key_id": self.keyid,
            "issued_utc": c3_public._stamp(self.now),
            "expires_utc": c3_public._stamp(self.now + timedelta(days=30)),
        }
        self.record_bytes, self.sig_bytes = auth.synthetic_fixture_signing_bytes(
            self.record, self.pr)

    def verify(self, record_bytes=None, sig_bytes=None, **updates):
        args = {
            "record_bytes": self.record_bytes if record_bytes is None else record_bytes,
            "signature_bytes": self.sig_bytes if sig_bytes is None else sig_bytes,
            "independently_provisioned_public_pem": self.public_pem,
            "expected_owner_key_id": self.keyid,
            "min_serial": 8,
            "expected_recipient_token_sha256": self.recipient,
            "expected_product_wheel_sha256": self.wheel_hash,
            "expected_vendor_wheels_sha256": self.vendors,
            "expected_rights_packet_sha256": self.rights,
            "now": self.now + timedelta(days=1),
        }
        args.update(updates)
        return auth.verify_private_entitlement(**args)

    def sign_updated(self, **updates):
        record = {**self.record, **updates}
        return auth.synthetic_fixture_signing_bytes(record, self.pr)

    def test_01_actual_real_ed25519_matches_all_four_pillars_and_hashes(self):
        r = self.verify()
        self.assertTrue(r["private_product_ed25519_signature_verified"])
        self.assertEqual(r["four_pillars_bound"], list(PILLARS))
        self.assertEqual(r["vendor_wheel_count"], 3)
        self.assertFalse(r["customer_entitlement_issued"])
        self.assertFalse(r["customer_distribution_authorized"])
        self.assertFalse(r["independent_legal_and_notice_approval"])
        self.assertFalse(r["real_owner_signing_proven"])
        self.assertFalse(r["out_of_band_owner_approval_independently_proven"])

    def test_02_wrong_recipient_token_does_not_authorize_another_customer(self):
        with self.assertRaises(ValueError):
            self.verify(expected_recipient_token_sha256="f"*64)

    def test_03_wrong_first_party_wheel_sha_rejected(self):
        with self.assertRaises(ValueError):
            self.verify(expected_product_wheel_sha256="f"*64)

    def test_04_wrong_vendor_wheel_sha_rejected(self):
        other = dict(self.vendors)
        other["cffi"] = "f"*64
        with self.assertRaises(ValueError):
            self.verify(expected_vendor_wheels_sha256=other)

    def test_05_missing_transitive_vendor_pin_rejected(self):
        other = dict(self.vendors)
        del other["pycparser"]
        with self.assertRaises(ValueError):
            self.verify(expected_vendor_wheels_sha256=other)

    def test_06_wrong_rights_document_sha_rejected_but_digest_no_approval(self):
        with self.assertRaises(ValueError):
            self.verify(expected_rights_packet_sha256="f"*64)
        self.assertFalse(self.verify()["independent_legal_and_notice_approval"])

    def test_07_expired_or_future_signed_license_denied(self):
        with self.assertRaises(ValueError):
            self.verify(now=self.now + timedelta(days=31))
        with self.assertRaises(ValueError):
            self.verify(now=self.now - timedelta(minutes=6))

    def test_08_signed_older_serial_denied_even_with_valid_signature(self):
        with self.assertRaises(ValueError):
            self.verify(min_serial=9)
        with self.assertRaises(ValueError):
            self.verify(min_serial=True)

    def test_09_public_pr_metadata_c3_signature_cannot_authenticate_product(self):
        self.assertNotEqual(auth.DOMAIN, c3_public.DOMAIN)
        fake_sig = {
            **json.loads(self.sig_bytes),
            "scope": c3_public.SCOPE,
        }
        with self.assertRaises(ValueError):
            self.verify(sig_bytes=auth.canonical(fake_sig))

    def test_10_tampered_product_bytes_even_with_correct_SHA_claim_denied(self):
        modified = self.record_bytes.replace(b'"serial":8', b'"serial":9')
        with self.assertRaises(ValueError):
            self.verify(record_bytes=modified)

    def test_11_second_key_cannot_impersonate_expected_owner(self):
        from cryptography.hazmat.primitives import serialization
        pem = self.another.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        with self.assertRaises(ValueError):
            self.verify(independently_provisioned_public_pem=pem)

    def test_12_signature_bit_flip_and_missing_fields_denied(self):
        sig = json.loads(self.sig_bytes)
        raw = bytearray(b64decode(sig["signature_base64"]))
        raw[0] ^= 1
        sig["signature_base64"] = b64encode(raw).decode("ascii")
        with self.assertRaises(ValueError):
            self.verify(sig_bytes=auth.canonical(sig))
        del sig["owner_key_id"]
        with self.assertRaises(ValueError):
            self.verify(sig_bytes=auth.canonical(sig))

    def test_13_noncanonical_duplicate_json_nan_and_oversize_denied(self):
        for blob in (
            b'{"schema":1,"schema":2}\n',
            b'{"serial": NaN}\n',
            self.record_bytes[:-1],
            self.record_bytes + b" ",
            b"x" * (auth.MAX_RECORD + 1),
        ):
            with self.subTest(blob=blob[:50]), self.assertRaises(ValueError):
                self.verify(record_bytes=blob)

    def test_14_signed_non_four_pillar_or_wrong_product_rejected(self):
        for change in (
            {"four_pillars": list(PILLARS[:3])},
            {"product": "single-rule-demo"},
            {"product_version": "0.1.1"},
            {"scope": c3_public.SCOPE},
        ):
            with self.subTest(change=change):
                a, b = self.sign_updated(**change)
                with self.assertRaises(ValueError):
                    self.verify(record_bytes=a, sig_bytes=b)

    def test_15_signed_rights_token_cannot_be_cited_as_legal_approval(self):
        a, b = self.sign_updated(rights_packet_sha256="d"*64)
        with self.assertRaises(ValueError):
            self.verify(record_bytes=a, sig_bytes=b)
        r = self.verify(record_bytes=a, sig_bytes=b, expected_rights_packet_sha256="d"*64)
        self.assertTrue(r["rights_packet_sha256_bound_but_legal_approval_not_proven"])
        self.assertFalse(r["independent_customer_contract_approved"])

    def test_16_negative_bad_date_and_signature_shape_denied(self):
        a, b = self.sign_updated(expires_utc="2026-11-15T07:00:00Z")
        with self.assertRaises(ValueError):
            self.verify(record_bytes=a, sig_bytes=b)
        a, b = self.sign_updated(issued_utc="2026-11-13T16:00:00+09:00")
        with self.assertRaises(ValueError):
            self.verify(record_bytes=a, sig_bytes=b)

    def test_17_wrong_owner_pin_and_non_utc_now_denied(self):
        with self.assertRaises(ValueError):
            self.verify(expected_owner_key_id="d"*32)
        with self.assertRaises(ValueError):
            self.verify(now=datetime(2026, 11, 14))

    def test_18_synthetic_signer_only_accepts_live_private_key_object(self):
        with self.assertRaises(ValueError):
            auth.synthetic_fixture_signing_bytes(self.record, b"demo-key")
        self.assertFalse(hasattr(auth, "issue_customer_entitlement"))
        self.assertFalse(hasattr(auth, "generate_keys"))


if __name__ == "__main__":
    unittest.main()
