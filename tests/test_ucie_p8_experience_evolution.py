"""P8 real synthetic evolution: next hypothesis, repeat suppression and isolated lineage.

All filesystem fixtures use a disposable UCIE-only temp checkout. The host's
operational SQLite, public miner, signing artifacts and other projects are
never opened. No external HTTP requests or application of experiment results.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import experience_evolution as evo
from ucie_miner.capability_evaluator import evaluate_synthetic_library_index


class P8EvolutionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        self.ledger = self.root / "runtime" / evo.FILE_NAME

    def test_owner_w08_observed_reference_retained_but_not_signed_or_real_performance(self):
        baseline = evo.OWNER_OBSERVED_REFERENCE
        self.assertEqual((baseline["rows"], baseline["queries"]), (1536, 48))
        self.assertEqual(baseline["dataset_sha256"],
                         "cd68799042a9c6c57b15100947541f16731d4cfd18efe6088db85264e92227f7")
        self.assertEqual(baseline["baseline_operations"], 73728)
        self.assertEqual(baseline["candidate_operations"], 1584)
        self.assertIn("NOT_INDEPENDENTLY_AUTHENTICATED", baseline["provenance"])

    def test_first_real_followup_runs_and_proposes_next_without_writing(self):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no UCIE external GET")), (
            patch("sqlite3.connect",
                  side_effect=AssertionError("no existing DB access"))):
            result = evo.run_evolution_cycle(self.root)
        self.assertEqual(result["schema"], evo.SCHEMA)
        self.assertEqual(result["current_workload"], "ROWS_256_QUERIES_16")
        self.assertTrue(result["new_experiment_executed"])
        self.assertFalse(result["new_event_written"])
        self.assertEqual(result["receipt"]["rows"], 256)
        self.assertEqual(result["receipt"]["queries"], 16)
        self.assertEqual(result["receipt"]["baseline_operations"], 4096)
        self.assertEqual(result["receipt"]["candidate_operations"], 272)
        self.assertTrue(result["receipt"]["result_equivalent"])
        self.assertEqual(result["next_experiment"],
                         {"rows": 4096, "queries": 16,
                          "purpose": "TEST_DIFFERENT_SYNTHETIC_WORKLOAD_AND_CHECK_CORRECTNESS"})
        self.assertFalse(self.ledger.exists())
        self.assertFalse(result["production_algorithm_changed"])
        self.assertFalse(result["auto_promoted"])
        self.assertEqual(result["ucie_isolated_ledger_writes"], 0)

    def test_explicit_record_chains_new_scenarios_and_skips_duplicates(self):
        first = evo.run_evolution_cycle(self.root, record=True)
        self.assertEqual(first["status"], "EXPERIENCE_RECORDED_SYNTHETIC_NO_GO")
        self.assertTrue(first["new_event_written"])
        self.assertEqual(first["ucie_isolated_ledger_writes"], 1)
        raw_1 = self.ledger.read_bytes()
        self.assertEqual(len(evo._load_events(self.root)), 1)
        second = evo.run_evolution_cycle(self.root, record=True)
        self.assertEqual(second["current_workload"], "ROWS_4096_QUERIES_16")
        self.assertEqual(second["local_recorded_experiments_before"], 1)
        self.assertEqual(second["receipt"]["baseline_operations"], 4096 * 16)
        self.assertEqual(second["receipt"]["candidate_operations"], 4096 + 16)
        self.assertTrue(self.ledger.read_bytes().startswith(raw_1))
        lines = [json.loads(x) for x in self.ledger.read_text().splitlines()]
        self.assertEqual(lines[1]["prev_hash"], lines[0]["event_sha256"])
        self.assertNotEqual(lines[1]["event_sha256"], lines[0]["event_sha256"])
        self.assertEqual(len(evo._load_events(self.root)), 2)
        self.assertFalse(second["owner_approved"])

    def test_after_all_four_experiments_no_repetition_or_extra_write(self):
        for _ in range(len(evo.WORKLOADS)):
            self.assertTrue(evo.run_evolution_cycle(self.root, record=True)["new_event_written"])
        original = self.ledger.read_bytes()
        done = evo.run_evolution_cycle(self.root, record=True)
        self.assertEqual(done["status"], "NO_UNTESTED_SYNTHETIC_SCENARIOS")
        self.assertFalse(done["new_experiment_executed"])
        self.assertFalse(done["new_event_written"])
        self.assertEqual(done["local_recorded_experiments"], len(evo.WORKLOADS))
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_tamper_or_replayed_event_rejected_before_next_experiment(self):
        evo.run_evolution_cycle(self.root, record=True)
        original = self.ledger.read_bytes()
        event = json.loads(original)
        event["receipt"]["candidate_operations"] = 0
        self.ledger.write_text(json.dumps(event, sort_keys=True) + "\n",
                               encoding="ascii")
        with self.assertRaises(evo.EvolutionError):
            evo.run_evolution_cycle(self.root, record=True)
        self.ledger.write_bytes(original + original)
        with self.assertRaises(evo.EvolutionError):
            evo.run_evolution_cycle(self.root, record=True)

    def test_tampered_chain_parent_does_not_advance(self):
        evo.run_evolution_cycle(self.root, record=True)
        evo.run_evolution_cycle(self.root, record=True)
        lines = self.ledger.read_text().splitlines()
        second = json.loads(lines[1])
        second["prev_hash"] = "f" * 64
        second["event_sha256"] = evo._digest_bytes(
            evo._canonical({k: v for k, v in second.items() if k != "event_sha256"}))
        self.ledger.write_text(lines[0] + "\n" + json.dumps(second) + "\n")
        with self.assertRaises(evo.EvolutionError):
            evo.run_evolution_cycle(self.root)

    def test_different_project_root_and_symlink_paths_refused(self):
        outside = Path(self.folder.name) / "somewhere"
        outside.mkdir()
        with self.assertRaises(evo.EvolutionError):
            evo.run_evolution_cycle(outside)
        with self.assertRaises(evo.EvolutionError):
            evo.run_evolution_cycle(Path(self.folder.name) / "nonexistent")
        self.assertFalse(self.ledger.exists())

    def test_inconsistent_w08_receipts_never_enter_knowledge_lineage(self):
        base = evaluate_synthetic_library_index(rows=256, queries=16, repeats=3)
        for field, value in (
            ("database_writes", 1), ("network_requests", 1),
            ("public_source_data_used", True),
            ("project_data_accessed", True), ("auto_promoted", True),
            ("production_approved", True), ("dataset_sha256", "a"*64),
            ("reference_comparisons_per_run", -3),
            ("owner_approved", True),
        ):
            tampered = deepcopy(base)
            tampered[field] = value
            with self.subTest(field=field):
                with self.assertRaises(evo.EvolutionError):
                    evo._capture_w08(tampered)

    def test_incorrect_result_is_not_presented_as_improvement(self):
        bad = evaluate_synthetic_library_index(rows=256, queries=16, repeats=3)
        bad["exact_result_equivalence_observed"] = False
        bad["mismatched_query_count"] = 1
        bad["status"] = "SYNTHETIC_EVALUATION_REQUIRES_REVIEW_NO_GO"
        receipt = evo._capture_w08(bad)
        self.assertEqual(receipt["decision"],
                         "REJECT_OR_REVISE_SYNTHETIC_CANDIDATE")
        # Never automatically advance after a recorded failure.
        evo._write_event(self.root, (), receipt)
        result = evo.run_evolution_cycle(self.root, record=True)
        self.assertEqual(result["status"], "NEGATIVE_EXPERIENCE_HOLD_FOR_REVIEW")
        self.assertFalse(result["new_experiment_executed"])

    def test_explicit_cli_default_preview_and_record_semantics(self):
        argv = ["evo", "--ucie-root", str(self.root)]
        with patch("sys.argv", argv), patch("builtins.print") as rendered:
            self.assertEqual(evo.main(), 0)
        response = json.loads(rendered.call_args.args[0])
        self.assertFalse(response["new_event_written"])
        self.assertFalse(self.ledger.exists())
        with patch("sys.argv", argv + ["--record"]), patch("builtins.print") as rendered:
            self.assertEqual(evo.main(), 0)
        response = json.loads(rendered.call_args.args[0])
        self.assertTrue(response["new_event_written"])
        self.assertTrue(self.ledger.is_file())

    def test_unknown_or_unbounded_ledger_bytes_fail_closed(self):
        self.ledger.write_bytes(b"x" * (evo.MAX_BYTES + 1))
        with self.assertRaises(evo.EvolutionError):
            evo.run_evolution_cycle(self.root)


if __name__ == "__main__":
    unittest.main()
