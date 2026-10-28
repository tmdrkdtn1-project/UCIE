"""W05 bounded 1-3 page public metadata discovery with honest zero-candidate diagnostics.

No unapproved source, raw public code, private project data, or unscheduled GET.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner.capability_trials import (
    CapabilityTrialError, validate_w05_page_bundle,
)
from ucie_miner.capability_experience import (
    CapabilityExperienceError, run_capability_cycle, main,
    read_capability_history, FILE_NAME,
)
from ucie_miner.public_discovery import DiscoveryError, public_feed_url
from test_ucie_positive_capability_discovery import public_pr, NOW


SOURCE = "repo:python/cpython"


def public_pages():
    return (
        [
            public_pr(55101, "Fix exception regression in tests"),
            public_pr(55102, "Refactor method argument validation"),
            dict(public_pr(55103, "Add incremental build cache"), merged_at=None),
        ],
        [
            public_pr(55201, "Introduce test automation helper"),
            public_pr(55202, "Add incremental build cache for compilation"),
        ],
        [
            public_pr(55202, "Add incremental build cache for compilation"),
            public_pr(55301, "Introduce adaptive learning feedback loop"),
        ],
    )


class W05BoundedDepthTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        self.ledger = self.root / "runtime" / FILE_NAME

    def test_first_page_zero_but_deeper_pages_have_three_unique_public_title_cues(self):
        bundle = validate_w05_page_bundle(public_pages(), source_id=SOURCE, now=NOW)
        d = bundle["diagnostics"]
        self.assertEqual(d["pages_scanned"], 3)
        self.assertEqual(d["public_rows_examined"], 7)
        self.assertEqual(d["overlapping_rows_deduplicated"], 1)
        self.assertEqual(d["unique_positive_candidates"], 3)
        self.assertEqual(d["pages"][0]["positive_title_cues"], 0)
        self.assertEqual(d["pages"][0]["repair_title_count"], 1)
        self.assertEqual(d["pages"][0]["nonmerged_count"], 1)
        self.assertEqual(d["pages"][1]["positive_title_cues"], 2)
        self.assertEqual(d["pages"][2]["positive_title_cues"], 2)
        self.assertEqual({c["kind"] for c in bundle["cues"]}, {
            "DEVELOPMENT_ENGINE", "REUSABLE_SKILL", "LEARNING_LOGIC"})
        self.assertTrue(all(not c["approved"] and not c["export_allowed"]
                            for c in bundle["cues"]))
        # Never return PR title text, body, patches or source code.
        self.assertNotIn("Introduce test automation", json.dumps(bundle))
        self.assertFalse(d["upstream_capability_verified"])

    def test_deep_pages_drive_one_new_ucie_trial_and_do_not_write_by_default(self):
        pages = public_pages()
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no HTTP in preloaded rows")):
            out = run_capability_cycle(self.root, source_rows=pages,
                                       source_id=SOURCE, now=NOW)
        self.assertEqual(out["source_candidate_count"], 3)
        self.assertEqual(out["source_scan_diagnostics"]["pages_scanned"], 3)
        self.assertFalse(out["new_event_written"])
        self.assertTrue(out["trial_receipt"]["equivalent"])
        self.assertFalse(out["upstream_capability_verified"])
        self.assertFalse(self.ledger.exists())
        first = run_capability_cycle(self.root, source_rows=pages,
                                     source_id=SOURCE, now=NOW, record=True)
        self.assertTrue(first["new_event_written"])
        second = run_capability_cycle(self.root, source_rows=pages,
                                      source_id=SOURCE, now=NOW, record=True)
        self.assertTrue(second["new_event_written"])
        self.assertNotEqual(first["candidate_id"], second["candidate_id"])
        self.assertEqual(read_capability_history(self.root)["recorded_count"], 2)

    def test_stable_cross_page_duplicate_is_ignored_but_conflict_fails_closed(self):
        pages = public_pages()
        altered = deepcopy(pages)
        altered[2][0]["title"] = "Improve adaptive learning feedback loop"
        with self.assertRaises(CapabilityTrialError):
            validate_w05_page_bundle(altered, source_id=SOURCE, now=NOW)
        self.assertFalse(self.ledger.exists())

    def test_invalid_pages_and_forbidden_sources_fail_before_accepting_candidates(self):
        pages = public_pages()
        for value in ((), tuple([pages[0]] * 4), (pages[0], "not a list"),
                      (pages[0] * 8,), [pages[0]]):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises((CapabilityTrialError, DiscoveryError)):
                    validate_w05_page_bundle(value, source_id=SOURCE, now=NOW)
        for source in ("repo:unknown/private", "research:GH Archive",
                       "doc:python/cpython"):
            with self.assertRaises((DiscoveryError, CapabilityTrialError)):
                validate_w05_page_bundle((pages[0],), source_id=source, now=NOW)

    def test_explicit_three_pages_use_only_existing_approved_urls_and_count_real_gets(self):
        argv = ["w05-p8", "--ucie-root", str(self.root),
                "--source-id", SOURCE, "--live", "--pages", "3"]
        pages = public_pages()
        with (
            patch("sys.argv", argv),
            patch("ucie_miner.capability_experience.public_feed_get",
                  side_effect=pages) as fetch,
            patch("builtins.print") as printed,
        ):
            self.assertEqual(main(), 0)
        receipt = json.loads(printed.call_args.args[0])
        self.assertEqual(receipt["source_candidate_count"], 3)
        self.assertEqual(receipt["source_scan_diagnostics"]["pages_scanned"], 3)
        self.assertEqual(receipt["explicit_public_gets"], 3)
        self.assertEqual(receipt["network_requests"], 3)
        self.assertFalse(receipt["new_event_written"])
        self.assertFalse(self.ledger.exists())
        self.assertEqual([call.args[0] for call in fetch.call_args_list], [
            public_feed_url("python/cpython", page=p) for p in (1, 2, 3)])

    def test_empty_valid_feed_explains_zero_candidates_without_error_or_writes(self):
        pages = ([public_pr(66001, "Fix error in exception handler")],)
        out = run_capability_cycle(self.root, source_rows=pages,
                                   source_id=SOURCE, now=NOW)
        self.assertEqual(out["status"], "NO_UNTESTED_IMPLEMENTED_W05_RECIPE")
        self.assertEqual(out["source_candidate_count"], 0)
        d = out["source_scan_diagnostics"]
        self.assertEqual(d["pages"][0]["repair_title_count"], 1)
        self.assertEqual(d["pages"][0]["positive_title_cues"], 0)
        self.assertFalse(self.ledger.exists())

    def test_explicit_depth_never_runs_without_live_or_with_invalid_page_count(self):
        for options in (["--pages", "2"], ["--pages", "0"],
                        ["--pages", "4"], ["--live", "--pages", "4"],
                        ["--history", "--pages", "2"]):
            argv = ["w05-p8", "--ucie-root", str(self.root),
                    "--source-id", SOURCE] + options
            if "--history" in options:
                argv = ["w05-p8", "--ucie-root", str(self.root)] + options
            with (
                patch("sys.argv", argv),
                patch("ucie_miner.capability_experience.public_feed_get",
                      side_effect=AssertionError("must not GET")),
                patch("builtins.print") as printed,
            ):
                self.assertEqual(main(), 2)
            self.assertEqual(json.loads(printed.call_args.args[0])["status"],
                             "FAIL_CLOSED")
        self.assertFalse(self.ledger.exists())

    def test_original_p8_ledger_is_preserved_when_a_new_w05_trial_is_recorded(self):
        original = self.root / "runtime" / "ucie_p8_experience_v1.jsonl"
        original.write_bytes(b"UCIE_OLDER_EXPERIENCE_LEDGER\n")
        before = original.read_bytes()
        out = run_capability_cycle(
            self.root, source_rows=public_pages(),
            source_id=SOURCE, record=True, now=NOW)
        self.assertTrue(out["new_event_written"])
        self.assertEqual(original.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
