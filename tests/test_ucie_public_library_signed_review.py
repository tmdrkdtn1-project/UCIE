"""Focused UCIE Library signed-claim checks, synthetic keys, no IO."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ucie_public.policy import PolicyError
from ucie_public.rulepack import canonical_json
from ucie_miner.public_batch import build_public_batch
from ucie_miner.public_library_graph import preview_library_knowledge_graph
from ucie_miner.public_library_signed_review import (
    EVENT_SCHEMA, inspect_library_signed_review_ledger,
)
from test_ucie_stage9_batch import metadata, evidence, NOW

OBSERVED = datetime(2026, 10, 22, 5, 0, tzinfo=timezone.utc)


def batch():
    return build_public_batch(
        metadata_fetch=metadata, evidence_fetch=evidence,
        now=NOW, max_enrich=2)


class PublicLibrarySignedReviewTests(unittest.TestCase):
    def setUp(self):
        self.current = batch()
        self.owner = Ed25519PrivateKey.generate()
        self.qa = Ed25519PrivateKey.generate()
        graph = preview_library_knowledge_graph(self.current)
        cards = [x for x in graph["nodes"]
                 if x["kind"] == "UNVERIFIED_PUBLIC_RESEARCH_REFERENCE"]
        self.card = cards[0]

    def event(self, action="REVIEW_ATTESTED", serial=1, *,
              owner=None, qa=None, issued=None, expires=None):
        now = issued or OBSERVED - timedelta(hours=1)
        expiry = expires or now + timedelta(days=7)
        is_review = action == "REVIEW_ATTESTED"
        claim = {
            "schema": EVENT_SCHEMA,
            "action": action,
            "public_url": self.card["public_url"],
            "pinned_revision_sha": self.card["pinned_revision_sha"],
            "evidence_sha256": self.card["evidence_fingerprint_sha256"],
            "version_claim": "3.15.0" if is_review else None,
            "review_evidence_sha256": "e" * 64 if is_review else None,
            "review_claims": {
                "source_license": True, "security": True,
                "regression": True, "release_version": True,
            } if is_review else None,
            "serial": serial,
            "issued_utc": now.isoformat().replace("+00:00", "Z"),
            "expires_utc": (expiry.isoformat().replace("+00:00", "Z")
                            if is_review else None),
        }
        raw = canonical_json(claim)
        return {
            "claim": claim,
            "owner_signature_hex": (owner or self.owner).sign(raw).hex(),
            "qa_signature_hex": (qa or self.qa).sign(raw).hex()
                                 if is_review else None,
        }

    def inspect(self, records, **kwargs):
        return inspect_library_signed_review_ledger(
            self.current, records, owner_trust=self.owner.public_key(),
            qa_trust=self.qa.public_key(), at_time=OBSERVED, **kwargs)

    def test_empty_ledger_denies_distribution(self):
        out = self.inspect([])
        self.assertEqual(out["reviewed_public_candidate_count"], 2)
        self.assertEqual(out["signed_review_claim_count"], 0)
        self.assertEqual(out["distribution_eligible_count"], 0)
        self.assertFalse(out["distribution_authorized"])
        self.assertFalse(out["ledger_is_durable_or_complete"])
        self.assertFalse(out["rollback_protection_persisted"])
        self.assertTrue(all(x["state"] == "NO_SIGNED_REVIEW_RECORD"
                            for x in out["decisions"]))

    def test_dual_signature_attests_claim_only_not_actual_qa(self):
        out = self.inspect([self.event()])
        self.assertEqual(out["signed_review_claim_count"], 1)
        claimed = next(x for x in out["decisions"]
                       if x["state"] ==
                       "SIGNED_REVIEW_CLAIMS_REQUIRE_INDEPENDENT_AUDIT")
        self.assertTrue(claimed["qa_signature_valid"])
        self.assertTrue(claimed["owner_signature_valid"])
        self.assertFalse(claimed["human_review_independently_confirmed"])
        self.assertFalse(claimed["release_version_independently_confirmed"])
        self.assertFalse(claimed["can_install"])
        self.assertFalse(claimed["can_publish"])

    def test_owner_revocation_tombstone_blocks_reapproval(self):
        approved = self.event(serial=1)
        revoked = self.event(action="REVOKE", serial=2)
        result = self.inspect([approved, revoked])
        self.assertEqual(result["signed_revoked_count"], 1)
        self.assertFalse(result["distribution_authorized"])
        self.assertEqual(next(x for x in result["decisions"]
                              if x["serial"] == 2)["state"], "OWNER_REVOKED")
        with self.assertRaises(PolicyError):
            self.inspect([approved, revoked, self.event(serial=3)])

    def test_forgery_duplicate_serial_and_wrong_identity_rejected(self):
        original = self.event()
        modified = deepcopy(original)
        modified["claim"]["version_claim"] = "999.0"
        cases = [
            [modified],
            [original, original],
            [self.event(owner=Ed25519PrivateKey.generate())],
        ]
        altered = self.event()
        altered["claim"]["public_url"] = (
            "https://github.com/unknown/foreign/pull/42")
        cases.append([altered])
        for records in cases:
            with self.subTest(records=records[0]["claim"]["public_url"]):
                with self.assertRaises(PolicyError):
                    self.inspect(records)

    def test_signed_review_expiry_and_separate_key_requirement(self):
        stale = self.event(
            issued=OBSERVED - timedelta(days=20),
            expires=OBSERVED - timedelta(days=1))
        result = self.inspect([stale])
        self.assertEqual(result["signed_review_claim_count"], 0)
        self.assertIn("EXPIRED_SIGNED_REVIEW_CLAIM",
                      {x["state"] for x in result["decisions"]})
        with self.assertRaises(PolicyError):
            inspect_library_signed_review_ledger(
                self.current, [self.event()],
                owner_trust=self.owner.public_key(),
                qa_trust=self.owner.public_key(),
                at_time=OBSERVED)

    def test_unsafe_claim_and_fake_revocation_are_rejected(self):
        no_qa = self.event()
        no_qa["qa_signature_hex"] = None
        forged_revocation = self.event(action="REVOKE")
        forged_revocation["qa_signature_hex"] = "0" * 128
        unbounded = self.event()
        unbounded["claim"]["review_claims"]["source_license"] = False
        for item in (no_qa, forged_revocation, unbounded):
            with self.assertRaises(PolicyError):
                self.inspect([item])


if __name__ == "__main__":
    unittest.main()
