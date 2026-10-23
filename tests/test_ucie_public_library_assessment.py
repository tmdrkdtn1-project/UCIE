"""UCIE public Library multidimensional gap and review-handoff regression.

Synthetic approved-source metadata only. No live network, host files, task
mutation, persistence, code execution of external patches or real approvals.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from ucie_miner.public_batch import build_public_batch, _fingerprint
from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.public_library_assessment import (
    GATES, SCHEMA, preview_library_evidence_assessment,
)
from test_ucie_stage9_batch import NOW, metadata, evidence

ROOT = Path(__file__).resolve().parents[1]


def batch(n=3):
    return build_public_batch(
        metadata_fetch=metadata, evidence_fetch=evidence,
        now=NOW, max_enrich=n)


class PublicLibraryAssessmentTests(unittest.TestCase):
    def test_all_dimensions_are_unverified_and_review_gated(self):
        receipt = preview_library_evidence_assessment(batch())
        self.assertEqual(receipt["schema"], SCHEMA)
        self.assertEqual(receipt["current_reference_count"], 3)
        self.assertEqual(receipt["new_or_changed_review_count"], 3)
        self.assertEqual(receipt["unchanged_without_duplicate_alert_count"], 0)
        self.assertEqual(receipt["verified_prevention_rules"], 0)
        self.assertEqual(receipt["rules_auto_promoted"], 0)
        self.assertEqual(receipt["files_or_databases_written"], 0)
        self.assertEqual(receipt["network_requests"], 0)
        self.assertEqual(receipt["external_or_private_project_reads"], 0)
        self.assertFalse(receipt["production_approved"])
        self.assertFalse(receipt["assessment_sha256_is_signature"])
        for card in receipt["cards"]:
            d = card["dimensions"]
            self.assertEqual(
                d["confidence_class"], "UNVERIFIED_METADATA_ONLY_NO_NUMERIC_SCORE")
            self.assertEqual(d["source_identity"], "APPROVED_REFERENCE_FORMAT_ONLY")
            self.assertEqual(d["source_version_applicability"], "NOT_ESTABLISHED")
            self.assertEqual(d["regression"], "NOT_REPRODUCED_IN_ISOLATED_RUNNER")
            self.assertEqual({x["gate"] for x in card["missing_verification_gates"]},
                             set(GATES))
            self.assertTrue(all(x["state"] == "NOT_VERIFIED"
                                for x in card["missing_verification_gates"]))
            self.assertFalse(card["rule_candidate_auto_created"])
            self.assertFalse(card["release_or_install_authorized"])
        self.assertEqual(
            len({x["review_id_sha256"] for x in receipt["manual_review_queue"]}),
            receipt["new_or_changed_review_count"])

    def test_identical_batch_suppresses_duplicate_review_alert(self):
        current = batch()
        first = preview_library_evidence_assessment(current, deepcopy(current))
        second = preview_library_evidence_assessment(deepcopy(current), current)
        self.assertEqual(first, second)
        self.assertEqual(first["new_or_changed_review_count"], 0)
        self.assertEqual(first["manual_review_queue"], [])
        self.assertEqual(first["unchanged_without_duplicate_alert_count"], 3)
        self.assertTrue(all(x["next_action"] ==
            "KEEP_PENDING_NO_DUPLICATE_NOTIFICATION" for x in first["cards"]))
        self.assertFalse(first["production_approved"])

    def test_metadata_revision_delta_only_requeues_changed_reference(self):
        previous = batch()
        current = deepcopy(previous)
        item = current["candidate_skill_queue"][0]
        item["evidence_sha256"] = ("f" if
            item["evidence_sha256"] != "f" * 64 else "e") * 64
        current["candidate_queue_sha256"] = _fingerprint(
            current["candidate_skill_queue"])
        report = preview_library_evidence_assessment(current, previous)
        self.assertEqual(report["new_or_changed_review_count"], 1)
        self.assertEqual(report["unchanged_without_duplicate_alert_count"], 2)
        self.assertEqual(
            report["manual_review_queue"][0]["change_classification"],
            "PUBLIC_EVIDENCE_FINGERPRINT_CHANGED")
        self.assertFalse(report["manual_review_queue"][0]["auto_approved"])

    def test_merge_identity_changed_requires_fresh_review(self):
        previous = batch()
        current = deepcopy(previous)
        item = current["candidate_skill_queue"][0]
        item["pinned_merge_commit_sha"] = (
            "a" * 40 if item["pinned_merge_commit_sha"] != "a" * 40
            else "b" * 40)
        current["candidate_queue_sha256"] = _fingerprint(
            current["candidate_skill_queue"])
        report = preview_library_evidence_assessment(current, previous)
        self.assertEqual(report["new_or_changed_review_count"], 1)
        self.assertEqual(report["manual_review_queue"][0]["change_classification"],
                         "MERGE_IDENTITY_CHANGED_RECHECK")

    def test_bounded_nonselection_never_means_deleted(self):
        previous = batch(3)
        current = batch(1)
        report = preview_library_evidence_assessment(current, previous)
        self.assertEqual(report["current_reference_count"], 1)
        self.assertEqual(len(report["previously_selected_not_seen"]), 2)
        self.assertFalse(report["not_seen_means_deleted"])
        self.assertFalse(report["production_approved"])

    def test_forged_external_approval_fails_closed(self):
        current = batch()
        current["candidate_skill_queue"][0]["human_approval_received"] = True
        current["candidate_queue_sha256"] = _fingerprint(
            current["candidate_skill_queue"])
        with self.assertRaises(DiscoveryError):
            preview_library_evidence_assessment(current)

    def test_unapproved_foreign_source_rejected(self):
        current = batch()
        current["candidate_skill_queue"][0]["public_url"] = (
            "https://github.com/unknown/unapproved/pull/7")
        current["candidate_queue_sha256"] = _fingerprint(
            current["candidate_skill_queue"])
        with self.assertRaises(DiscoveryError):
            preview_library_evidence_assessment(current)

    def test_readonly_cli_valid_and_duplicate_field_rejected(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        command = [sys.executable, "-B", "-m", "ucie_miner",
                   "preview-library-assessment-stdin"]
        current = batch()
        good = subprocess.run(
            command,
            input=json.dumps({"current": current, "previous": current}),
            capture_output=True, text=True, env=env, cwd=ROOT, timeout=15)
        self.assertEqual(good.returncode, 0, good.stderr)
        payload = json.loads(good.stdout)
        self.assertEqual(payload["schema"], SCHEMA)
        self.assertEqual(payload["manual_review_queue"], [])
        self.assertEqual(payload["rules_auto_promoted"], 0)
        for invalid in ('{"current":{},"current":{},"previous":null}',
                        '{"current":[],"previous":null}'):
            bad = subprocess.run(
                command, input=invalid, capture_output=True, text=True,
                env=env, cwd=ROOT, timeout=15)
            self.assertEqual(bad.returncode, 2, bad.stderr)
            self.assertEqual(json.loads(bad.stdout)["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
