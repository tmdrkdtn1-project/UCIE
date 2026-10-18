"""Stage4 dual signature production contract, synthetic keys ONLY.

Tests are NOT QA approval, identity attestation, or permission to publish.
"""
from __future__ import annotations
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ucie_public.policy import PolicyError
from ucie_public.rulepack import (canonical_json, generate_keys, _private_key)
from ucie_public.prevention_rulepack import publish_prevention_review, CONFIRM
from ucie_public.production_release import (
    EXPECTED_QA, OWNER_CONFIRM, publish_production, verify_production,
    validate_qa_attestation,
)


class ProductionContractTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "build").mkdir()
        self.owner, self.owner_pub = generate_keys(
            self.root / "owner", purpose="production")
        self.qa, self.qa_pub = generate_keys(
            self.root / "external_qa", purpose="qa")
        self.claim = self.root / "claim.json"
        self.sig = self.root / "qa.sig"
        self.output = self.root / "build" / "production.zip"
        self.make_fake_independent_qa_claim()

    def make_fake_independent_qa_claim(self, **mutations):
        qa_key = _private_key(self.qa)
        from ucie_public.rulepack import key_id
        obj = dict(EXPECTED_QA)
        obj["qa_key_id"] = key_id(qa_key.public_key())
        obj["reviewed_utc"] = datetime.now(timezone.utc).replace(
            microsecond=0).isoformat().replace("+00:00", "Z")
        obj.update(mutations)
        data = canonical_json(obj)
        self.claim.write_bytes(data)
        self.sig.write_bytes(qa_key.sign(data))

    def issue(self, *, confirm=OWNER_CONFIRM, owner=None):
        return publish_production(
            self.root, owner if owner is not None else self.owner,
            self.claim, self.sig, self.qa_pub, self.output,
            serial=7, confirmation=confirm)

    def test_no_approval_without_two_parties_or_explicit_owner(self):
        with self.assertRaises(PolicyError):
            self.issue(confirm="AUTOMATIC")
        self.assertFalse(self.output.exists())
        self.make_fake_independent_qa_claim(
            independent_security_review="PENDING")
        with self.assertRaises(PolicyError):
            self.issue()
        self.assertFalse(self.output.exists())

    def test_dual_sign_production_and_separate_review_schema(self):
        self.issue()
        res = verify_production(self.output, self.owner_pub, self.qa_pub,
                                min_serial=7)
        self.assertEqual(res["result"],
                         "DUAL_SIGNED_PUBLIC_PRODUCTION_RULEPACK_VERIFIED")
        self.assertEqual(res["owner_signature"], "VALID")
        self.assertEqual(res["independent_qa_signature"], "VALID")
        self.assertEqual(res["scope"], "PUBLIC_ONLY_MANUAL_STATIC_SCAN")
        self.assertTrue(res["production_approved"])
        self.assertTrue(res["deploy_allowed"])
        self.assertFalse(res["auto_apply"])
        from ucie_public.prevention_rulepack import verify_prevention_review
        with self.assertRaises(PolicyError):
            verify_prevention_review(self.output, self.owner_pub)
        with self.assertRaises(PolicyError):
            self.issue()  # never overwrite signed release

    def test_cannot_use_review_key_as_owner_and_no_key_alias(self):
        with self.assertRaises(PolicyError):
            self.issue(owner=self.qa)
        self.assertFalse(self.output.exists())
        self.issue()
        with self.assertRaises(PolicyError):
            verify_production(self.output, self.qa_pub, self.qa_pub)
        review_key, review_trust = generate_keys(
            self.root / "review", purpose="prevention")
        with self.assertRaises(PolicyError):
            verify_production(self.output, review_trust, self.qa_pub)
        with self.assertRaises(PolicyError):
            verify_production(self.output, self.owner_pub, review_trust)

    def test_qa_signature_tamper_and_missing_gate(self):
        self.sig.write_bytes(b"0" * 64)
        with self.assertRaises(PolicyError):
            self.issue()
        self.make_fake_independent_qa_claim(public_source_license_review="UNKNOWN")
        with self.assertRaises(PolicyError):
            self.issue()
        self.make_fake_independent_qa_claim(recipient_acceptance_review="PENDING")
        with self.assertRaises(PolicyError):
            self.issue()

    def test_owner_signature_and_archive_tampering_rejected(self):
        self.issue()
        with zipfile.ZipFile(self.output) as source:
            original = {n: source.read(n) for n in source.namelist()}
        changed = dict(original)
        modified = json.loads(changed["manifest.json"])
        modified["auto_apply"] = True
        changed["manifest.json"] = canonical_json(modified)
        altered = self.root / "build" / "tampered.zip"
        with zipfile.ZipFile(altered, "w") as archive:
            for name, data in changed.items():
                archive.writestr(name, data)
        with self.assertRaises(PolicyError):
            verify_production(altered, self.owner_pub, self.qa_pub)
        injected = self.root / "build" / "injected.zip"
        with zipfile.ZipFile(injected, "w") as archive:
            for name, data in original.items():
                archive.writestr(name, data)
            archive.writestr("../../unexpected", b"invalid")
        with self.assertRaises(PolicyError):
            verify_production(injected, self.owner_pub, self.qa_pub)

    def test_rollback_expiry_future_and_qa_age(self):
        self.issue()
        with self.assertRaises(PolicyError):
            verify_production(self.output, self.owner_pub, self.qa_pub,
                              min_serial=8)
        with self.assertRaises(PolicyError):
            verify_production(self.output, self.owner_pub, self.qa_pub,
                              at_time=datetime.now(timezone.utc)
                              + timedelta(days=8))
        future = datetime.now(timezone.utc) - timedelta(days=31)
        self.make_fake_independent_qa_claim(reviewed_utc=future.isoformat().replace(
            "+00:00", "Z"))
        with self.assertRaises(PolicyError):
            validate_qa_attestation(self.claim.read_bytes(),
                                    self.sig.read_bytes(), self.qa_pub)

    def test_qa_attestation_does_not_imply_actual_review(self):
        # Synthetic test keys prove structural gate behavior only.
        self.make_fake_independent_qa_claim()
        item, _ = validate_qa_attestation(
            self.claim.read_bytes(), self.sig.read_bytes(), self.qa_pub)
        self.assertEqual(item["independent_security_review"], "PASS")
        self.assertFalse(self.output.exists())
        # No owner signing or release occurs in normal test fixture setup.


if __name__ == "__main__":
    unittest.main()
