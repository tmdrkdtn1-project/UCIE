"""UCIE-only deterministic evidence maturity regression; no network or runtime DB."""
from __future__ import annotations

import unittest

from ucie_miner.public_evidence_maturity_v01 import (
    EvidenceMaturityError, GAPS, INCOMPLETE, assess_public_evidence_maturity,
)
from ucie_public.policy import PolicyError

SOURCE = "python/cpython"
SHA = "a" * 40


def handoff(*, count=2):
    tasks = []
    for index in range(count):
        tasks.append({
            "candidate_id_sha256": f"{index + 1:064x}",
            "evidence_sha256": f"{index + 101:064x}",
            "source": SOURCE,
            "reference": f"pr:153462:{SHA}",
            "skill_id": "python-runtime-safety",
            "pattern_code": "CONCURRENCY",
            "stage6_candidate": None,
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "approval": False,
            "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
        })
    return {
        "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
        "status": "LINKED_UNVERIFIED_NO_GO",
        "source_revisions": count,
        "linked_revisions": count,
        "pending_source_revisions": 0,
        "tasks": tasks,
        "auto_promoted": False,
        "production_approved": False,
        "deploy_allowed": False,
    }


class PublicEvidenceMaturityTests(unittest.TestCase):
    def test_source_linked_candidates_remain_unapproved_with_explicit_gaps(self):
        report = assess_public_evidence_maturity(handoff())
        self.assertEqual(report["status"], GAPS)
        self.assertEqual(report["evidence_revision_count"], 2)
        self.assertEqual(report["distinct_public_identity_count"], 1)
        self.assertEqual(
            report["additional_evidence_revisions_at_shared_public_identity"], 1)
        self.assertEqual(report["by_source"], {"repo:python/cpython": 2})
        self.assertEqual(report["reference_types"], {"PR_METADATA": 2})
        self.assertEqual(report["review_gaps_in_handoff"], {
            "per_revision_license_not_attested_here": 2,
            "affected_runtime_version_not_verified_here": 2,
            "independent_regression_not_performed_here": 2,
        })
        self.assertEqual(report["review_targets"][0]["evidence_revision_count"], 2)
        self.assertFalse(report["production_approved"])
        self.assertFalse(report["auto_promoted"])
        self.assertEqual(report["persistent_writes"], 0)

    def test_incomplete_linkage_never_exposes_assessments_or_targets(self):
        h = handoff()
        h["status"] = "SOURCE_REVISIONS_PENDING_NO_GO"
        h["source_revisions"] = 3
        h["pending_source_revisions"] = 1
        report = assess_public_evidence_maturity(h)
        self.assertEqual(report["status"], INCOMPLETE)
        self.assertIsNone(report["evidence_revision_count"])
        self.assertIsNone(report["review_gaps_in_handoff"])
        self.assertEqual(report["review_targets"], [])

    def test_forged_approval_and_repeated_fingerprint_rejected(self):
        h = handoff()
        h["tasks"][0]["approval"] = True
        with self.assertRaises(PolicyError):
            assess_public_evidence_maturity(h)
        h = handoff()
        h["tasks"][1]["candidate_id_sha256"] = h["tasks"][0]["candidate_id_sha256"]
        with self.assertRaises(PolicyError):
            assess_public_evidence_maturity(h)

    def test_wrong_source_identity_and_skill_are_rejected(self):
        h = handoff()
        h["tasks"][0]["source"] = "unapproved/private"
        with self.assertRaises(ValueError):
            assess_public_evidence_maturity(h)
        h = handoff()
        h["tasks"][0]["skill_id"] = "fabricated-skill"
        with self.assertRaises(EvidenceMaturityError):
            assess_public_evidence_maturity(h)

    def test_unchanged_count_required_and_bounded_preview(self):
        h = handoff()
        h["linked_revisions"] = 1
        # Existing source-linked validation rejects inconsistent counts first.
        with self.assertRaises(PolicyError):
            assess_public_evidence_maturity(h)
        for limit in (0, 13, True, 1.0):
            with self.assertRaises(EvidenceMaturityError):
                assess_public_evidence_maturity(handoff(), preview_limit=limit)

    def test_input_order_has_no_effect_on_report(self):
        h = handoff()
        first = assess_public_evidence_maturity(h)
        h["tasks"].reverse()
        self.assertEqual(first, assess_public_evidence_maturity(h))

    def test_zero_verified_candidates_is_not_approval(self):
        h = handoff(count=0)
        report = assess_public_evidence_maturity(h)
        self.assertEqual(report["evidence_revision_count"], 0)
        self.assertEqual(report["status"], GAPS)
        self.assertEqual(report["review_targets"], [])
        self.assertFalse(report["customer_release_authorized"])


if __name__ == "__main__":
    unittest.main()
