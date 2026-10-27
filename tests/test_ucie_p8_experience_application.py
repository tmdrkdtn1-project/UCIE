"""P8 experience reuse on the real UCIE-approved public Library review metadata."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import experience_application as app
from ucie_miner import experience_evolution as evo
from ucie_public.policy import PolicyError
from test_ucie_positive_capability_discovery import handoff_two_evidence_revisions
from test_ucie_stage11_hourly_stage import fixture_batch
from test_ucie_stage9_batch import NOW
from ucie_miner.public_candidate_staging import stage_public_candidates, DB_NAME
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, optional_hourly_review_learning,
)


class P8ExperienceApplicationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)

    def test_first_record_from_owner_like_p8_ledger_is_searchable(self):
        record = evo.run_evolution_cycle(self.root, record=True)
        out = app.experience_library_preview(self.root)
        self.assertEqual(out["recorded_experiments"], 1)
        self.assertEqual(out["last_event_sha256"], record["event_sha256"])
        self.assertEqual(out["items"][0]["kind"], "UCIE_EXPERIENCE")
        self.assertEqual(out["items"][0]["workload_id"], "ROWS_256_QUERIES_16")
        self.assertEqual(out["items"][0]["library_item_id"], record["event_sha256"])
        self.assertEqual(out["next_unexecuted_workload"],
                         {"rows": 4096, "queries": 16})
        self.assertEqual(out["items"][0]["baseline_operations"], 4096)
        self.assertEqual(out["items"][0]["index_build_and_lookup_operations"], 272)
        self.assertFalse(out["items"][0]["real_library_benefit_verified"])
        self.assertFalse(out["historical_w08_reference_counted_as_recorded"])
        self.assertEqual(out["operating_database_writes"], 0)
        self.assertFalse(out["auto_promoted"])

    def test_history_preview_does_not_change_existing_record(self):
        evo.run_evolution_cycle(self.root, record=True)
        file = self.root / "runtime" / evo.FILE_NAME
        before = file.read_bytes()
        with patch("urllib.request.urlopen", side_effect=AssertionError("no GET")):
            with patch("sqlite3.connect", side_effect=AssertionError("no DB")):
                one = app.experience_library_preview(self.root)
                two = app.experience_library_preview(self.root)
        self.assertEqual(one, two)
        self.assertEqual(file.read_bytes(), before)
        self.assertFalse(one["source_ledger_modified"])

    def test_bad_experience_hash_refused_no_fake_learning(self):
        evo.run_evolution_cycle(self.root, record=True)
        file = self.root / "runtime" / evo.FILE_NAME
        row = json.loads(file.read_text().strip())
        row["receipt"]["candidate_operations"] = 1
        file.write_text(json.dumps(row) + "\n", encoding="ascii")
        with self.assertRaises(evo.EvolutionError):
            app.experience_library_preview(self.root)

    def test_catalog_benchmark_on_validated_handoff_matches_results(self):
        handoff = handoff_two_evidence_revisions()
        out = app.benchmark_linked_public_catalog(handoff, queries=32, repeats=2)
        self.assertEqual(out["status"],
                         "REAL_PUBLIC_METADATA_EXACT_QUERY_EQUIVALENT_UNAPPROVED")
        self.assertEqual(out["real_public_catalog_items"], 2)
        self.assertEqual(out["query_count"], 32)
        self.assertEqual(out["mismatched_query_results"], 0)
        self.assertGreater(out["matched_query_count"], 0)
        self.assertGreater(out["missing_query_count"], 0)
        self.assertEqual(out["baseline_scan_operations"], 64)
        self.assertEqual(out["candidate_index_build_and_lookup_operations"], 34)
        self.assertFalse(out["full_w04_substring_search_benchmarked"])
        self.assertFalse(out["production_index_applied"])
        self.assertEqual(out["approved_or_exportable_items"], 0)
        self.assertEqual(out["network_requests"], 0)
        self.assertEqual(out["operating_database_writes"], 0)

    def test_incomplete_handoff_cannot_be_marked_real_benchmark_pass(self):
        handoff = handoff_two_evidence_revisions()
        handoff["status"] = "REVIEW_LEDGER_ABSENT_NO_GO"
        handoff["tasks"] = []
        out = app.benchmark_linked_public_catalog(handoff)
        self.assertEqual(out["status"],
                         "NO_COMPLETE_SOURCE_LINKED_PUBLIC_CATALOG_NO_GO")
        self.assertEqual(out["experiments_run"], 0)

    def test_untrusted_source_and_forged_approval_are_rejected(self):
        bad = handoff_two_evidence_revisions()
        bad["tasks"][0]["source"] = "unknown/private"
        with self.assertRaises((ValueError, PolicyError)):
            app.benchmark_linked_public_catalog(bad)
        bad2 = handoff_two_evidence_revisions()
        bad2["tasks"][0]["approval"] = True
        with self.assertRaises((ValueError, PolicyError)):
            app.benchmark_linked_public_catalog(bad2)

    def test_bad_workload_rejected(self):
        handoff = handoff_two_evidence_revisions()
        for args in (
            {"queries": True}, {"queries": 0}, {"queries": 97},
            {"repeats": 0}, {"repeats": 6}, {"repeats": False},
        ):
            with self.subTest(args=args):
                with self.assertRaises(app.ExperienceApplicationError):
                    app.benchmark_linked_public_catalog(handoff, **args)

    def test_genuine_ucie_stage10_to_stage12_public_ledger_stays_byte_identical(self):
        batch = fixture_batch(
            root=self.root,
            sources=("python/cpython", "PowerShell/PowerShell", "git/git",
                     "modelcontextprotocol/python-sdk", "actions/runner-images"),
            max_enrich=1, include_git_commits=True,
            include_docs=False, include_advisories=False, backfill_pages=1)
        stage_public_candidates(batch, root=self.root, allow_disk_write=True)
        runtime = self.root / "runtime"
        (runtime / OPT_IN_FILENAME).write_text(OPT_IN_TOKEN, encoding="ascii")
        result = optional_hourly_review_learning(self.root)
        self.assertEqual(result["new_review_proposals"], 2)
        ledger1 = runtime / DB_NAME
        ledger2 = runtime / "stage12_unverified_review.sqlite3"
        before = (ledger1.read_bytes(), ledger2.read_bytes())
        with patch("urllib.request.urlopen", side_effect=AssertionError("no GET")):
            out = app.benchmark_existing_ucie_public_catalog(
                self.root, queries=16, repeats=1)
        self.assertEqual(before, (ledger1.read_bytes(), ledger2.read_bytes()))
        self.assertEqual(out["status"],
                         "REAL_PUBLIC_METADATA_EXACT_QUERY_EQUIVALENT_UNAPPROVED")
        self.assertEqual(out["real_public_catalog_items"], 2)
        self.assertEqual(out["network_requests"], 0)
        self.assertEqual(out["operating_database_writes"], 0)

    def test_cli_experience_and_real_catalog_return_bounded_json(self):
        evo.run_evolution_cycle(self.root, record=True)
        with patch("sys.argv", ["p8", "--ucie-root", str(self.root)]):
            with patch("builtins.print") as printed:
                self.assertEqual(app.main(), 0)
        out = json.loads(printed.call_args.args[0])
        self.assertEqual(out["recorded_experiments"], 1)
        with patch("sys.argv", [
            "p8", "--ucie-root", str(self.root),
            "--mode", "real-catalog", "--queries", "16", "--repeats", "1",
        ]):
            with patch("builtins.print") as printed:
                self.assertEqual(app.main(), 0)
        out = json.loads(printed.call_args.args[0])
        self.assertEqual(out["status"],
                         "NO_COMPLETE_SOURCE_LINKED_PUBLIC_CATALOG_NO_GO")


if __name__ == "__main__":
    unittest.main()
