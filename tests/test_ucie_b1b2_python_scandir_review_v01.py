"""UCIE W01/W02/B1/B2 review workflow: source, entry, real synthetic trial.

No external network or customer paths; all concurrency uses GuardedScandir
against newly created UCIE first-party disposable synthetic fixture files.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import re
import unittest
from unittest.mock import patch

from ucie_miner import python_scandir_review_v01 as review
from ucie_miner import source_registry


class PythonScandirWorkflowTests(unittest.TestCase):
    def test_approved_official_source_becomes_unapproved_library_entry(self):
        src, entry = review._source_bound_entry()
        self.assertEqual(src["source_id"], "doc:python/cpython")
        self.assertEqual(src["status"], "ACTIVE_APPROVED")
        self.assertEqual(src["public_url"],
                         "https://docs.python.org/3/library/os.html")
        self.assertEqual(entry["kind"], "TEST_RECIPE")
        self.assertEqual(entry["source_id"], "doc:python/cpython")
        self.assertEqual(entry["purpose_code"],
                         "SCANDIR_SERIALIZED_ITERATION")
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", entry["library_item_id"]))
        self.assertEqual(entry["revision_hint"],
                         "PUBLIC_DOCUMENT_REVISION_NOT_PINNED")
        self.assertEqual(entry["approval_status"], "NOT_APPROVED")
        for flag in ("human_approved", "export_allowed", "auto_promoted",
                     "version_applicability_verified"):
            self.assertIs(entry[flag], False)

    def test_two_real_guarded_consumers_and_cleanup(self):
        outcome = review._evaluate_only_ucie_synthetic_inputs()
        self.assertEqual(outcome["synthetic_file_count"], 4)
        self.assertEqual(outcome["concurrent_guarded_consumers"], 2)
        for flag in ("unique_entries_match", "sequential_control_match",
                     "closed_iterator_stops", "temporary_synthetic_files_removed"):
            self.assertIs(outcome[flag], True)
        self.assertFalse(outcome["unsafe_raw_iterator_race_executed"])
        self.assertFalse(outcome["customer_or_other_project_files_opened"])

    def test_real_workflow_output_matches_registry_and_first_party_trial(self):
        result = review.run_python_scandir_review()
        self.assertEqual(result["schema"], review.SCHEMA)
        self.assertEqual(result["status"],
                         "UCIE_OWNED_SYNTHETIC_SCANDIR_TRIAL_PASS_NOT_APPROVED")
        self.assertEqual(result["domain"], "Python")
        self.assertEqual(result["version_scope"], "UNDETERMINED")
        self.assertEqual(result["candidate_status"],
                         "UNVERIFIED_CANDIDATE_ONLY")
        self.assertEqual(result["evidence_fingerprint_scope"],
                         "UCIE_REFERENCE_STRING_ONLY_NOT_DOCUMENT_BYTES")
        self.assertTrue(result["synthetic_trial"]["unique_entries_match"])
        for flag in ("human_approved", "export_allowed", "auto_promoted",
                     "version_applicability_verified", "source_executed",
                     "customer_release_authorized"):
            self.assertIs(result[flag], False)
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertEqual(result["network_requests"], 0)

    def test_research_only_or_forged_official_document_refused(self):
        real = source_registry.get_source(review.SOURCE_ID)
        for variant in (
            dict(real, status="RESEARCH_ONLY"),
            dict(real, public_url="https://unexpected.example/private"),
            dict(real, license_verdict="INDEPENDENTLY_APPROVED"),
            dict(real, fetch_authorized_by_this_registry=True),
        ):
            with self.subTest(variant=variant):
                with patch.object(review, "get_source", return_value=variant):
                    with self.assertRaises(review.PythonScandirReviewError):
                        review.run_python_scandir_review()

    def test_registration_failure_and_illicit_approval_refused(self):
        with patch.object(
            review, "get_source",
            side_effect=source_registry.SourceRegistryError("UNKNOWN_SOURCE"),
        ):
            with self.assertRaises(source_registry.SourceRegistryError):
                review.run_python_scandir_review()
        original = review.build_library_entry
        with patch.object(review, "build_library_entry",
                          side_effect=lambda record:
                          dict(original(record), export_allowed=True)):
            with self.assertRaises(review.PythonScandirReviewError):
                review.run_python_scandir_review()

    def test_missing_synthetic_entry_does_not_claim_equivalence(self):
        base = review.GuardedScandir

        class DropAlpha:
            def __init__(self, path):
                self.guard = base(path)
            def __enter__(self):
                self.guard.__enter__()
                return self
            def __exit__(self, exc_type, exc, tb):
                return self.guard.__exit__(exc_type, exc, tb)
            def close(self):
                self.guard.close()
            def __next__(self):
                while True:
                    entry = next(self.guard)
                    if entry.name != "alpha.txt":
                        return entry

        with patch.object(review, "GuardedScandir", DropAlpha):
            with self.assertRaisesRegex(
                    review.PythonScandirReviewError,
                    "SCANDIR_GUARDED_ENUMERATION_MISMATCH"):
                review.run_python_scandir_review()

    def test_cli_success_and_error_hide_exception_message(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(review.main(), 0)
        parsed = json.loads(output.getvalue())
        self.assertEqual(parsed["status"],
                         "UCIE_OWNED_SYNTHETIC_SCANDIR_TRIAL_PASS_NOT_APPROVED")
        with patch.object(review, "GuardedScandir",
                          side_effect=OSError("PRIVATE_SECRET_DO_NOT_PERSIST")):
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(review.main(), 2)
            record = output.getvalue()
            self.assertNotIn("PRIVATE_SECRET", record)
            self.assertEqual(json.loads(record)["error_type"], "OSError")


if __name__ == "__main__":
    unittest.main()
