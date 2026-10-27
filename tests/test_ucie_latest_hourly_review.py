"""One focused functional regression for latest hourly Stage12 -> Stage17 handoff."""
from __future__ import annotations

from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import sqlite3
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner.latest_hourly_review import (
    SCHEMA, build_latest_hourly_review, inspect_latest_hourly_review,
    classify_upstream_recency, _history_merge_dates,
)
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, optional_hourly_review_learning,
)
from ucie_miner.public_candidate_staging import stage_public_candidates
from ucie_miner.stage17_review_docket import build_review_docket
from ucie_miner.public_external_history import _schema as init_history_schema
from test_ucie_automated_candidate_qa import handoff
from test_ucie_stage17_review_docket import evidence
from test_ucie_stage11_hourly_stage import fixture_batch

START = "2026-10-27T05:37:11+00:00"
END = "2026-10-27T05:37:20+00:00"


def receipt(count=2):
    return {
        "schema": "UCIE_MINER_CYCLE_V1",
        "status": "COLLECTED_UNVERIFIED",
        "started_utc": START, "finished_utc": END,
        "stage12_review_proposals_added": count,
        "stage12_review_status": "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO",
        "verification_pass": 0, "production_approved": False,
    }


class LatestHourlyReviewTests(unittest.TestCase):
    def setUp(self):
        self.handoff = handoff()
        # The lightweight shared fixture omits display fields that the real
        # Stage12 ledger includes. Populate them before testing the operator view.
        for task in self.handoff["tasks"]:
            task["pattern_code"] = "API_CONTRACT"
            task["skill_id"] = "synthetic-public-review"
            task["safe_guidance_for_review"] = "Manual source review only"
            task["regression_plan_for_review"] = "Review in isolated owned fixture"
        self.docket = build_review_docket(self.handoff, evidence())
        self.ids = [x["candidate_id_sha256"] for x in self.handoff["tasks"]]
        self.first_seen = {
            identity: (START if i < 2 else "2026-10-26T04:00:00+00:00")
            for i, identity in enumerate(self.ids)
        }

    def test_only_two_latest_reviews_are_actionable(self):
        out = build_latest_hourly_review(
            receipt(), self.handoff, self.docket, self.first_seen)
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(out["status"], "LATEST_HOURLY_NEW_REVIEWS_READY_NO_GO")
        self.assertEqual(out["new_review_proposals_reported"], 2)
        self.assertEqual(out["linked_new_review_proposals"], 2)
        self.assertEqual(out["selected_count"], 2)
        self.assertEqual({x["candidate_id_sha256"] for x in out["new_review_tasks"]},
                         set(self.ids[:2]))
        self.assertFalse(out["auto_promoted"])
        self.assertFalse(out["production_approved"])
        self.assertEqual(out["external_api_gets"], 0)
        self.assertEqual(out["persistent_writes"], 0)
        for task in out["new_review_tasks"]:
            self.assertTrue(task["required_next_actions"])
            self.assertFalse(task["human_approved"])
            self.assertFalse(task["independent_fix_verified"])
            self.assertFalse(task["deploy_allowed"])

    def test_old_review_queue_rows_are_not_counted_as_new(self):
        out = build_latest_hourly_review(
            receipt(0), self.handoff, self.docket,
            {key: "2026-10-26T04:00:00+00:00" for key in self.ids})
        self.assertEqual(out["status"], "LATEST_HOURLY_NO_NEW_REVIEWS")
        self.assertEqual(out["selected_count"], 0)

    def test_count_mismatch_never_invents_candidate_identity(self):
        seen = dict(self.first_seen)
        seen[self.ids[1]] = "2026-10-26T04:00:00+00:00"
        out = build_latest_hourly_review(
            receipt(), self.handoff, self.docket, seen)
        self.assertEqual(out["status"], "LATEST_HOURLY_REVIEW_COUNT_MISMATCH_NO_GO")
        self.assertEqual(out["selected_count"], 0)
        self.assertEqual(out["new_review_tasks"], [])

    def test_failed_cycle_cannot_claim_new_candidates(self):
        bad = receipt()
        bad["status"] = "COLLECTION_FAILED"
        out = build_latest_hourly_review(bad, self.handoff, self.docket, self.first_seen)
        self.assertEqual(out["status"], "LATEST_HOURLY_COLLECTION_NOT_COMPLETE_NO_GO")
        self.assertEqual(out["selected_count"], 0)

    def test_false_approval_or_malformed_timestamp_is_rejected(self):
        bad = deepcopy(self.docket)
        bad["items"][0]["human_approval"] = True
        with self.assertRaises(ValueError):
            build_latest_hourly_review(receipt(), self.handoff, bad, self.first_seen)
        r = receipt()
        r["started_utc"] = "2026-10-27T05:37:11"
        with self.assertRaises(ValueError):
            build_latest_hourly_review(r, self.handoff, self.docket, self.first_seen)

    def test_real_stage12_fixture_to_latest_review_without_new_api_or_write(self):
        with tempfile.TemporaryDirectory() as basedir:
            root = Path(basedir) / "UCIE"
            runtime = root / "runtime"
            runtime.mkdir(parents=True)
            batch = fixture_batch(
                root=root,
                sources=("python/cpython", "PowerShell/PowerShell",
                         "git/git", "modelcontextprotocol/python-sdk",
                         "actions/runner-images"),
                max_enrich=1, include_git_commits=True, include_docs=False,
                include_advisories=False, backfill_pages=1)
            stage_public_candidates(batch, root=root, allow_disk_write=True)
            (runtime / OPT_IN_FILENAME).write_text(OPT_IN_TOKEN, encoding="ascii")
            started = datetime.now(timezone.utc) - timedelta(seconds=30)
            result = optional_hourly_review_learning(root)
            self.assertEqual(result["new_review_proposals"], 2)
            finished = datetime.now(timezone.utc) + timedelta(seconds=1)
            r = receipt(result["new_review_proposals"])
            r["started_utc"] = started.isoformat(timespec="seconds")
            r["finished_utc"] = finished.isoformat(timespec="seconds")
            (runtime / "last_run.json").write_text(
                json.dumps(r, sort_keys=True), encoding="utf-8")
            before = {p.name: p.read_bytes() for p in runtime.iterdir()
                      if p.is_file()}
            with patch("ucie_miner.automated_candidate_qa._public_json",
                       side_effect=AssertionError("NO EXTERNAL API")):
                out = inspect_latest_hourly_review(root)
            after = {p.name: p.read_bytes() for p in runtime.iterdir()
                     if p.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(out["selected_count"], 2)
            self.assertEqual(out["linked_new_review_proposals"], 2)
            self.assertEqual(out["status"], "LATEST_HOURLY_SOURCE_RECENCY_UNKNOWN_NO_NEW_UPSTREAM")
            self.assertEqual(out["upstream_age_unknown_review_count"], 2)
            self.assertEqual(out["recent_upstream_review_count"], 0)
            self.assertEqual(out["external_api_gets"], 0)


    def test_historical_2023_revisions_do_not_become_recent_2026_changes(self):
        out = build_latest_hourly_review(
            receipt(), self.handoff, self.docket, self.first_seen)
        merge_dates = {
            (task["source"], task["reference"]): "2023-11-07T00:02:46+00:00"
            for task in out["new_review_tasks"]
        }
        got = classify_upstream_recency(out, merge_dates)
        self.assertEqual(
            got["status"], "LATEST_HOURLY_HISTORICAL_BACKFILL_ONLY_NO_NEW_UPSTREAM")
        self.assertEqual(got["historical_backfill_review_count"], 2)
        self.assertEqual(got["recent_upstream_review_count"], 0)
        self.assertEqual(got["linked_new_review_proposals"], 2)
        self.assertEqual(got["selected_count"], 2)
        self.assertFalse(got["alert_emitted"])
        self.assertFalse(got["important_new_evidence_verified"])
        self.assertTrue(all(
            x["upstream_recency"] == "HISTORICAL_PUBLIC_BACKFILL"
            and x["recent_upstream_change"] is False
            for x in got["new_review_tasks"]))

    def test_exactly_one_recent_and_one_historical_public_merge(self):
        out = build_latest_hourly_review(
            receipt(), self.handoff, self.docket, self.first_seen)
        pairs = [(x["source"], x["reference"]) for x in out["new_review_tasks"]]
        got = classify_upstream_recency(out, {
            pairs[0]: "2026-10-20T00:00:00Z",
            pairs[1]: "2023-11-06T18:24:44Z",
        })
        self.assertEqual(got["status"], "LATEST_HOURLY_NEW_REVIEWS_READY_NO_GO")
        self.assertEqual(got["recent_upstream_review_count"], 1)
        self.assertEqual(got["historical_backfill_review_count"], 1)
        self.assertEqual(len(got["recent_upstream_review_tasks"]), 1)

    def test_unbound_or_future_merge_date_is_not_assumed_recent(self):
        out = build_latest_hourly_review(
            receipt(), self.handoff, self.docket, self.first_seen)
        got = classify_upstream_recency(out, {
            (out["new_review_tasks"][0]["source"],
             out["new_review_tasks"][0]["reference"]): "2026-10-28T00:00:00Z",
        })
        self.assertEqual(got["upstream_age_unknown_review_count"], 2)
        self.assertEqual(got["recent_upstream_review_count"], 0)
        self.assertEqual(
            got["status"], "LATEST_HOURLY_SOURCE_RECENCY_UNKNOWN_NO_NEW_UPSTREAM")

    def test_exact_two_public_pr_merge_dates_from_local_stage13_only(self):
        cases = [
            ("PowerShell/PowerShell", 20644,
             "c8afc18404087ced8f58625966e9bf9ca179155e",
             "d83e704dd46bdccc528c8e2147b78c8247d60a158f2f6fb5702717cfba7a82bd",
             "2023-11-07T00:02:46Z"),
            ("actions/runner-images", 8751,
             "98c6d29ec958daadbbe3300d7931b604fb4b08b8",
             "ea5d7a4701d350f88d4583c67135a853a7d0f81f49ad0f3baa17a29a7d9a8ccf",
             "2023-11-06T18:24:44Z"),
        ]
        with tempfile.TemporaryDirectory() as basedir:
            root = Path(basedir) / "UCIE"
            runtime = root / "runtime"
            runtime.mkdir(parents=True)
            db = runtime / "stage13_external_public_history.sqlite3"
            with closing(sqlite3.connect(db)) as conn:
                init_history_schema(conn, new=True)
                for source, number, merge, sha, when in cases:
                    conn.execute(
                        "INSERT INTO upstream_history VALUES (?,?,?,?,?,?,?,?,?)",
                        (source, number, merge, when, "a"*64, sha,
                         "synthetic-fixture", '["VERSION_COMPAT"]',
                         "UNVERIFIED_CANDIDATE_ONLY"))
                conn.commit()
            refs = [
                {"source": source,
                 "reference": f"fix-pr:{number}:{merge}:{sha}"}
                for source, number, merge, sha, when in cases
            ]
            before = db.read_bytes()
            dates = _history_merge_dates(root, refs)
            self.assertEqual(before, db.read_bytes())
            self.assertEqual(len(dates), 2)
            for source, number, merge, sha, when in cases:
                self.assertEqual(
                    dates[(source, f"fix-pr:{number}:{merge}:{sha}")], when)

    def test_zero_new_cycle_short_circuits_ledger_rechecks(self):
        with tempfile.TemporaryDirectory() as basedir:
            root = Path(basedir) / "UCIE"
            runtime = root / "runtime"
            runtime.mkdir(parents=True)
            (runtime / "last_run.json").write_text(
                json.dumps(receipt(0)), encoding="utf-8")
            out = inspect_latest_hourly_review(root)
            self.assertEqual(out["status"], "LATEST_HOURLY_NO_NEW_REVIEWS")
            self.assertEqual(out["selected_count"], 0)

    def test_duplicate_receipt_properties_are_refused(self):
        with tempfile.TemporaryDirectory() as basedir:
            root = Path(basedir) / "UCIE"
            runtime = root / "runtime"
            runtime.mkdir(parents=True)
            (runtime / "last_run.json").write_text(
                '{"schema":"UCIE_MINER_CYCLE_V1",'
                '"schema":"UCIE_MINER_CYCLE_V1"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                inspect_latest_hourly_review(root)


if __name__ == "__main__":
    unittest.main()
