"""P8 W05-linked experience tests: actual W05 validator and isolated hashed lineage."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import capability_experience as e
from ucie_miner import capability_trials as t
from test_ucie_positive_capability_discovery import public_pr, NOW


def public_fixture():
    return [
        public_pr(10111, "Add incremental build cache for compilation"),
        public_pr(10112, "Introduce test automation helper"),
        public_pr(10113, "Introduce adaptive learning feedback loop"),
        public_pr(10114, "Add workflow engine"),
        public_pr(10115, "Fix regression in build cache"),
    ]


class P8W05LinkedExperienceTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        self.file = self.root / "runtime" / e.FILE_NAME

    def run_cycle(self, *, record=False, rows=None):
        return e.run_capability_cycle(
            self.root, source_rows=public_fixture(),
            source_id="repo:python/cpython", record=record, now=NOW)

    def test_default_preview_runs_first_party_trial_without_recording(self):
        with (patch("urllib.request.urlopen",
                    side_effect=AssertionError("must not GET")),
              patch("sqlite3.connect",
                    side_effect=AssertionError("must not use operating DB"))):
            result = self.run_cycle()
        self.assertEqual(result["status"], "W05_FIRST_PARTY_EXPERIENCE_PREVIEW_ONLY_NO_GO")
        self.assertTrue(result["trial_receipt"]["equivalent"])
        self.assertFalse(result["new_event_written"])
        self.assertFalse(self.file.exists())
        self.assertFalse(result["upstream_capability_verified"])
        self.assertFalse(result["production_code_changed"])
        self.assertFalse(result["auto_promoted"])
        self.assertEqual(result["operating_database_writes"], 0)

    def test_record_one_candidate_then_new_candidate_without_repeats(self):
        a = self.run_cycle(record=True)
        self.assertTrue(a["new_event_written"])
        self.assertEqual(a["recorded_before"], 0)
        before = self.file.read_bytes()
        self.assertEqual(len(e._load(self.root)), 1)
        b = self.run_cycle(record=True)
        self.assertEqual(b["recorded_before"], 1)
        self.assertNotEqual(a["candidate_id"], b["candidate_id"])
        self.assertTrue(self.file.read_bytes().startswith(before))
        events = e._load(self.root)
        self.assertEqual(events[1]["prev_hash"], events[0]["event_sha256"])
        self.assertEqual(events[-1]["event_sha256"], b["event_sha256"])
        self.assertEqual(e.read_capability_history(self.root)["recorded_count"], 2)

    def test_next_workload_is_selected_after_three_distinct_public_cues(self):
        # The first workload (128,24) is run for each of three supported
        # positive public hypotheses. Unsupported fourth is never executed.
        first = [self.run_cycle(record=True) for _ in range(3)]
        self.assertEqual(len({x["candidate_id"] for x in first}), 3)
        fourth = self.run_cycle(record=True)
        self.assertEqual((fourth["trial_receipt"]["rows"],
                          fourth["trial_receipt"]["queries"]), (256, 16))
        self.assertEqual(fourth["candidate_id"], first[0]["candidate_id"])
        self.assertEqual(e.read_capability_history(self.root)["recorded_count"], 4)

    def test_no_repeat_after_all_bounded_cases(self):
        for _ in range(9):
            self.assertTrue(self.run_cycle(record=True)["new_event_written"])
        original = self.file.read_bytes()
        again = self.run_cycle(record=True)
        self.assertEqual(again["status"], "NO_UNTESTED_IMPLEMENTED_W05_RECIPE")
        self.assertFalse(again["new_event_written"])
        self.assertEqual(self.file.read_bytes(), original)

    def test_replaying_or_tampering_with_event_fails_closed(self):
        self.run_cycle(record=True)
        original = self.file.read_bytes()
        event = json.loads(original)
        event["receipt"]["candidate_operations"] = 0
        self.file.write_text(json.dumps(event) + "\n")
        with self.assertRaises(e.CapabilityExperienceError):
            self.run_cycle(record=True)
        self.file.write_bytes(original + original)
        with self.assertRaises(e.CapabilityExperienceError):
            self.run_cycle(record=True)

    def test_unsupported_only_has_no_written_experiment(self):
        out = e.run_capability_cycle(
            self.root, source_rows=[public_pr(77777, "Implement workflow engine")],
            source_id="repo:python/cpython", record=True, now=NOW)
        self.assertEqual(out["status"], "NO_UNTESTED_IMPLEMENTED_W05_RECIPE")
        self.assertEqual(out["unsupported_recipe_count"], 1)
        self.assertFalse(self.file.exists())

    def test_corrupted_upstream_metadata_cannot_become_local_knowledge(self):
        fake = public_fixture()
        fake[0]["html_url"] = "https://outside.invalid/source"
        with self.assertRaises(ValueError):
            self.run_cycle_with_rows(fake)
        self.assertFalse(self.file.exists())

    def run_cycle_with_rows(self, rows):
        return e.run_capability_cycle(
            self.root, source_rows=rows, source_id="repo:python/cpython",
            record=True, now=NOW)

    def test_existing_p8_ledger_and_operating_data_untouched(self):
        existing = self.root / "runtime" / "ucie_p8_experience_v1.jsonl"
        existing.write_bytes(b"OLDER_UCIE_P8_LEDGER_NOT_TOUCHED\n")
        original = existing.read_bytes()
        self.run_cycle(record=True)
        self.assertEqual(existing.read_bytes(), original)
        self.assertTrue(self.file.is_file())

    def test_recorded_failure_stops_future_automatic_experiments(self):
        original = t.ALGORITHMS["ENGINE_INCREMENTAL_BUILD"]
        def incorrect(n, q):
            data, ops = original[1](n, q)
            return (("bad",),) + data[1:], ops
        # The first cue may be selected among the three supported ones, so
        # make each improved algorithm incorrect to ensure negative receipt.
        with patch.dict(t.ALGORITHMS, {
            k: (v[0], incorrect if k == "ENGINE_INCREMENTAL_BUILD" else
                (lambda n,q,v=v: ((("bad",),) + v[1](n,q)[0][1:], v[1](n,q)[1])))
            for k,v in t.ALGORITHMS.items()
        }):
            first = self.run_cycle(record=True)
        self.assertEqual(first["next_decision"], "HOLD_FOR_FIRST_PARTY_RECIPE_CORRECTION")
        second = self.run_cycle(record=True)
        self.assertEqual(second["status"], "PREVIOUS_FIRST_PARTY_FAILURE_HOLD_NO_GO")
        self.assertFalse(second["new_event_written"])

    def test_history_rejects_foreign_project_root_and_has_no_get(self):
        outside = self.root.parent / "another_project"
        outside.mkdir()
        with self.assertRaises(e.CapabilityExperienceError):
            e.read_capability_history(outside)
        self.run_cycle(record=True)
        previous = self.file.read_bytes()
        with patch("urllib.request.urlopen", side_effect=AssertionError("no GET")):
            report = e.read_capability_history(self.root)
        self.assertEqual(report["items"][0]["source_id"], "repo:python/cpython")
        self.assertFalse(report["items"][0]["upstream_capability_verified"])
        self.assertEqual(self.file.read_bytes(), previous)

    def test_cli_inert_then_opt_in_w05_api_one_get(self):
        with (patch("sys.argv", ["capability_experience", "--ucie-root", str(self.root)]),
              patch("ucie_miner.capability_experience.public_feed_get",
                    side_effect=AssertionError("must be inert")),
              patch("builtins.print") as rendered):
            self.assertEqual(e.main(), 0)
        self.assertEqual(json.loads(rendered.call_args.args[0])["status"],
                         "PUBLIC_REVIEW_GET_NOT_REQUESTED_NO_GO")
        with (patch("sys.argv", [
                "capability_experience", "--ucie-root", str(self.root),
                "--live", "--source-id", "repo:python/cpython"]),
              patch("ucie_miner.capability_experience.public_feed_get",
                    return_value=public_fixture()) as fetch,
              patch("builtins.print") as rendered):
            self.assertEqual(e.main(), 0)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(json.loads(rendered.call_args.args[0])["explicit_public_gets"], 1)
        self.assertFalse(self.file.exists())


if __name__ == "__main__":
    unittest.main()
