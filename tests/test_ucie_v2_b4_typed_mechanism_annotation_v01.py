"""W02 review-only mechanism annotations: no semantic promotion."""
from copy import deepcopy
from unittest import TestCase

from ucie_miner import ucie_v2_b4_typed_mechanism_annotation_v01 as mod
from ucie_miner.ucie_v2_b4_w02_evidence_intake_gate_v01 import triage_w02_evidence


def _records():
    return [
        {"kind": "TEST_RECIPE",
         "source_id": "repo:PowerShell/PowerShell",
         "evidence_reference":
             "pr:28087:373f6a7b7972a0a4b73bfd9737a0d768d28b347e",
         "evidence_sha256": "b" * 64,
         "purpose_code": "PINNED_NEGATIVE",
         "version_scope": "7.6.6", "dependencies": []},
        {"kind": "TEST_RECIPE", "source_id": "repo:python/cpython",
         "evidence_reference":
             "pr:153462:999a046b24cff4ba0e72b574196721f66bd08237",
         "evidence_sha256": "a" * 64,
         "purpose_code": "PINNED_NEGATIVE",
         "version_scope": "3.15.0", "dependencies": []},
    ]


def _annotate(records=None):
    if records is None:
        records = _records()
    queue = triage_w02_evidence(records)["review_queue"]
    return [{
        "library_item_id": r["library_item_id"],
        "evidence_sha256": r["evidence_sha256"],
        "mechanisms": ["VERSION_PINNED_TRIAL"],
        "preconditions": ["EXACT_VERSION_REQUIRED"],
        "counterexamples": ["HISTORICAL_TRIAL_NOT_CURRENT_COMPATIBILITY"],
        "origin": mod.ORIGIN,
        "status": "REVIEW_ONLY_UNVERIFIED",
    } for r in queue]


class AnnotationGateTests(TestCase):
    def test_two_technology_typed_proposal_still_unverified(self):
        out = mod.compare_draft_annotations(_records(), _annotate())
        self.assertEqual(out["reviewed_draft_count"], 2)
        self.assertEqual(len(out["test_proposals"]), 1)
        self.assertEqual(out["test_proposals"][0]["distinct_technology_count"], 2)
        self.assertFalse(out["test_proposals"][0]["test_contract"]["actual_test_executed"])
        self.assertFalse(out["source_revision_authenticated"])
        self.assertFalse(out["independent_qa_verified"])

    def test_identical_source_does_not_count_as_independent(self):
        records = _records()
        records[1]["source_id"] = "repo:PowerShell/PowerShell"
        records[1]["evidence_reference"] = (
            "pr:28042:bd8cb01a7d5b86129c45eaa14ab5830a63b1283f")
        anns = _annotate(records)
        out = mod.compare_draft_annotations(records, anns)
        self.assertEqual(out["test_proposals"], [])
        self.assertEqual(len(out["held_mechanisms"]), 1)

    def test_order_independent(self):
        records = _records()
        annotations = _annotate(records)
        self.assertEqual(mod.compare_draft_annotations(records, annotations),
                         mod.compare_draft_annotations(
                             list(reversed(records)), list(reversed(annotations))))

    def test_unreviewed_input_is_still_held(self):
        records = _records()
        anns = _annotate(records)[:1]
        out = mod.compare_draft_annotations(records, anns)
        self.assertEqual(out["unreviewed_queue_count"], 1)
        self.assertEqual(out["test_proposals"], [])

    def test_forged_source_digest_denied(self):
        anns = _annotate()
        anns[0]["evidence_sha256"] = "f" * 64
        with self.assertRaises(mod.AnnotationError):
            mod.compare_draft_annotations(_records(), anns)

    def test_unhashable_identity_denied(self):
        anns = _annotate()
        anns[0]["library_item_id"] = ["bad"]
        with self.assertRaises(mod.AnnotationError):
            mod.compare_draft_annotations(_records(), anns)

    def test_malicious_mechanism_denied(self):
        anns = _annotate()
        anns[0]["mechanisms"] = ["AUTO_PROMOTE_ALL"]
        with self.assertRaises(mod.AnnotationError):
            mod.compare_draft_annotations(_records(), anns)

    def test_missing_counterexample_denied(self):
        anns = _annotate()
        anns[0]["counterexamples"] = []
        with self.assertRaises(mod.AnnotationError):
            mod.compare_draft_annotations(_records(), anns)

    def test_forged_approval_denied(self):
        anns = _annotate()
        anns[0]["status"] = "APPROVED"
        with self.assertRaises(mod.AnnotationError):
            mod.compare_draft_annotations(_records(), anns)

    def test_duplicate_annotation_denied(self):
        anns = _annotate()
        anns.append(deepcopy(anns[0]))
        with self.assertRaises(mod.AnnotationError):
            mod.compare_draft_annotations(_records(), anns)

    def test_unapproved_source_denied(self):
        records = _records()
        records[0]["source_id"] = "repo:unapproved/private"
        with self.assertRaises(Exception):
            mod.compare_draft_annotations(records, _annotate())

    def test_no_network_or_export_claim(self):
        out = mod.compare_draft_annotations(_records(), _annotate())
        self.assertFalse(out["customer_release_authorized"])
        self.assertFalse(out["actual_first_party_trials_executed"])
        self.assertEqual(out["network_requests"], 0)
        self.assertEqual(out["operating_database_writes"], 0)
        self.assertFalse(out["test_proposals"][0]["export_allowed"])
