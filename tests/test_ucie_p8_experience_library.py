"""P8 experience history uses genuine UCIE-owned W08 trials, never foreign data."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import experience_library as lib
from ucie_miner import capability_evaluator as ev


class P8OwnedExperienceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "UCIE"
        self.root.mkdir()
        self.start = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)

    def _record(self, *, minute=0, rows=256, queries=16):
        return lib.record_owned_experiment(
            self.root, rows=rows, queries=queries, repeats=1,
            allow_write=True,
            at_time=self.start + timedelta(minutes=minute))

    def test_default_read_only_empty_catalog_creates_no_directory(self):
        result = lib.inspect_experience_library(self.root)
        self.assertEqual(result["status"], "UCIE_EXPERIENCE_LEDGER_EMPTY_NO_GO")
        self.assertEqual(result["total_records"], 0)
        self.assertEqual(result["records"], [])
        self.assertFalse((self.root / "runtime").exists())
        self.assertFalse(result["v1_accepted"])

    def test_w08_preview_runs_real_algorithms_without_persisting(self):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no external GET")):
            with patch("sqlite3.connect",
                       side_effect=AssertionError("no SQLite")):
                result = lib.record_owned_experiment(
                    self.root, rows=256, queries=16, repeats=1)
        self.assertFalse(result["metadata_saved"])
        self.assertEqual(result["status"], "EXPERIENCE_PREVIEW_NOT_SAVED")
        self.assertEqual(result["record"]["kind"], "UCIE_EXPERIENCE")
        self.assertEqual(result["record"]["revision_number"], 1)
        self.assertTrue(result["record"]["human_review_required"])
        self.assertFalse((self.root / "runtime").exists())

    def test_explicit_record_and_query_are_real_immutable_file_operations(self):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no network")):
            first = self._record()
        self.assertTrue(first["metadata_saved"])
        self.assertEqual(first["separate_experience_files_written"], 1)
        self.assertEqual(first["operating_database_writes"], 0)
        folder = self.root / "runtime" / lib.FOLDER
        files = list(folder.glob("r_*.json"))
        self.assertEqual(len(files), 1)
        before = files[0].read_bytes()
        catalog = lib.inspect_experience_library(self.root)
        self.assertEqual(catalog["status"],
                         "UCIE_OWNED_EXPERIENCES_READ_ONLY_UNAPPROVED")
        self.assertEqual(catalog["total_records"], 1)
        self.assertEqual(catalog["records"][0]["record_id"], first["record_id"])
        self.assertEqual(catalog["records"][0]["revision_number"], 1)
        self.assertEqual(files[0].read_bytes(), before)
        self.assertTrue(catalog["hash_integrity_verified"])
        self.assertFalse(catalog["cryptographic_signatures_verified"])
        self.assertFalse(catalog["actual_production_improvement_verified"])
        self.assertFalse(catalog["auto_promoted"])
        self.assertFalse(catalog["v1_accepted"])

    def test_second_same_workload_has_exact_parent_link_and_comparison(self):
        old = self._record(minute=0)
        newer = self._record(minute=1)
        self.assertEqual(newer["record"]["parent_record_id"], old["record_id"])
        self.assertEqual(newer["record"]["revision_number"], 2)
        inspected = lib.inspect_experience_library(self.root)
        self.assertEqual(inspected["total_records"], 2)
        self.assertEqual(len(inspected["comparisons"]), 1)
        comparison = inspected["comparisons"][0]
        self.assertEqual(comparison["prior_record_id"], old["record_id"])
        self.assertEqual(comparison["current_record_id"], newer["record_id"])
        self.assertEqual(comparison["operation_reduction_delta"], 0)
        self.assertEqual(comparison["decision"],
                         "FURTHER_UCIE_SYNTHETIC_REVIEW_ONLY")
        self.assertFalse(comparison["promote_to_production"])

    def test_different_workload_has_new_root_no_false_speed_comparison(self):
        self._record(minute=0, rows=256)
        newer = self._record(minute=1, rows=512)
        self.assertIsNone(newer["record"]["parent_record_id"])
        self.assertEqual(newer["record"]["revision_number"], 1)
        out = lib.inspect_experience_library(self.root)
        self.assertEqual(out["total_records"], 2)
        self.assertEqual(out["comparisons"], [])

    def test_same_dataset_but_different_repetition_count_has_separate_history(self):
        first = self._record(minute=0)
        second = lib.record_owned_experiment(
            self.root, rows=256, queries=16, repeats=2,
            allow_write=True, at_time=self.start + timedelta(minutes=1))
        self.assertIsNone(first["record"]["parent_record_id"])
        self.assertIsNone(second["record"]["parent_record_id"])
        self.assertEqual(second["record"]["revision_number"], 1)
        self.assertEqual(lib.inspect_experience_library(self.root)["comparisons"], [])

    def test_modify_record_or_rename_hash_is_detected_before_another_write(self):
        self._record()
        filename = next((self.root / "runtime" / lib.FOLDER).glob("r_*.json"))
        filename.write_bytes(filename.read_bytes() + b" ")
        with self.assertRaises(lib.ExperienceLibraryError):
            lib.inspect_experience_library(self.root)
        with self.assertRaises(lib.ExperienceLibraryError):
            self._record(minute=1)
        self.assertEqual(len(list(filename.parent.glob("r_*.json"))), 1)

    def test_wrong_claim_cannot_become_approved_even_if_rehashed(self):
        self._record()
        file = next((self.root / "runtime" / lib.FOLDER).glob("r_*.json"))
        parsed = json.loads(file.read_text("ascii"))
        parsed["production_adopted"] = True
        data = lib._canonical(parsed)
        file.unlink()
        (file.parent / ("r_" + hashlib.sha256(data).hexdigest() + ".json")
         ).write_bytes(data)
        with self.assertRaises(lib.ExperienceLibraryError):
            lib.inspect_experience_library(self.root)

    def test_invalid_experience_fields_or_missing_ancestry_fail_closed(self):
        self._record(minute=0)
        self._record(minute=1)
        folder = self.root / "runtime" / lib.FOLDER
        files = sorted(folder.glob("r_*.json"))
        parent = next(path for path in files
                      if json.loads(path.read_bytes())["revision_number"] == 1)
        parent.unlink()
        with self.assertRaises(lib.ExperienceLibraryError):
            lib.inspect_experience_library(self.root)

    def test_external_project_and_symlink_catalog_rejected(self):
        other = self.root.parent / "unrelated"
        other.mkdir()
        with self.assertRaises(lib.ExperienceLibraryError):
            lib.inspect_experience_library(other)
        with self.assertRaises(lib.ExperienceLibraryError):
            lib.record_owned_experiment(other, rows=256, queries=16,
                                        repeats=1, allow_write=True)
        self.assertFalse((other / "runtime").exists())

    def test_wrong_candidate_result_is_recorded_as_review_not_approved(self):
        normal = ev._measure_indexed
        def incorrect(catalog, queries):
            actual, checks, elapsed, keys = normal(catalog, queries)
            actual[0] = ("WRONG_RESULT",)
            return actual, checks, elapsed, keys
        with patch.object(ev, "_measure_indexed", incorrect):
            result = self._record()
        self.assertEqual(result["record"]["outcome"], lib.STATUS_REVIEW)
        self.assertFalse(result["record"]["exact_result_equivalence_observed"])
        self.assertEqual(result["record"]["mismatched_query_count"], 1)
        self.assertFalse(result["record"]["production_adopted"])
        self.assertTrue(result["record"]["human_review_required"])

    def test_record_is_not_untrusted_user_receipt_import_api(self):
        result = ev.evaluate_synthetic_library_index(
            rows=256, queries=16, repeats=1)
        result["production_approved"] = True
        with self.assertRaises(lib.ExperienceLibraryError):
            lib._build_record(result, parent=None, at_time=self.start)
        self.assertFalse((self.root / "runtime").exists())

    def test_invalid_sizes_and_bad_query_limits_rejected(self):
        for kwargs in ({"rows": 1}, {"rows": True}, {"queries": 999},
                       {"repeats": 6}):
            with self.subTest(kwargs=kwargs), self.assertRaises(
                    ev.CapabilityEvaluationError):
                lib.record_owned_experiment(self.root, **kwargs)
        for limit in (0, 21, True, "10"):
            with self.assertRaises(lib.ExperienceLibraryError):
                lib.inspect_experience_library(self.root, limit=limit)

    def test_read_only_cli_and_explicit_record_cli(self):
        with patch("sys.argv", ["p8", "--ucie-root", str(self.root)]):
            with patch("builtins.print") as printed:
                self.assertEqual(lib.main(), 0)
        self.assertEqual(
            json.loads(printed.call_args.args[0])["status"],
            "UCIE_EXPERIENCE_LEDGER_EMPTY_NO_GO")
        self.assertFalse((self.root / "runtime").exists())
        with patch("sys.argv", [
            "p8", "--ucie-root", str(self.root), "--record",
            "--rows", "256", "--queries", "16", "--repeats", "1"
        ]), patch("builtins.print") as printed:
            self.assertEqual(lib.main(), 0)
        self.assertTrue(json.loads(printed.call_args.args[0])["metadata_saved"])
        with patch("sys.argv", ["p8", "--ucie-root", str(self.root)]):
            with patch("builtins.print") as printed:
                self.assertEqual(lib.main(), 0)
        self.assertEqual(json.loads(printed.call_args.args[0])["total_records"], 1)


if __name__ == "__main__":
    unittest.main()
