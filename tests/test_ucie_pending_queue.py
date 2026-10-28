"""UCIE internal minute-tick pending queue: fail a job, keep other jobs moving."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import pending_queue as q


T0 = datetime(2026, 10, 28, 8, 30, tzinfo=timezone.utc)


class UcieNonblockingPendingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        self.db = self.root / "runtime" / q.DB_NAME

    def init(self):
        self.assertFalse(self.db.exists())
        out = q.initialize_queue(self.root)
        self.assertFalse(out["production_handlers_enabled"])
        self.assertFalse(out["existing_hourly_miner_changed"])
        self.assertTrue(self.db.exists())

    def new_job(self, key, kind="PUBLIC_METADATA_REVIEW", at=T0, tries=5):
        return q.enqueue(self.root, kind=kind, dedupe_key=key,
                         due=at, max_attempts=tries)

    def claim(self, at=T0, limit=4, lease=120):
        return q.claim_ready(self.root, now=at, limit=limit,
                             lease_seconds=lease)

    def test_uninitialized_read_is_zero_mutation_and_demo_real_isolated_sqlite(self):
        out = q.inspect_queue(self.root)
        self.assertEqual(out["status"], "QUEUE_NOT_INSTALLED_READ_ONLY")
        self.assertFalse(self.db.exists())
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("public API must not be called")):
            demo = q.demo_pending_no_head_of_line_block()
        self.assertEqual(demo["status"], "NONBLOCKING_PENDING_DEMO_PASS")
        self.assertEqual(demo["blocked_job_status"], "PENDING")
        self.assertEqual(demo["independent_job_status"], "SUCCEEDED")
        self.assertTrue(demo["other_job_proceeded_in_same_minute"])
        self.assertFalse(demo["windows_task_registered"])
        self.assertFalse(demo["production_worker_connected"])
        self.assertFalse(self.db.exists())

    def test_blocked_a_stays_pending_and_b_completes_same_tick(self):
        self.init()
        a = self.new_job("UCIE:A")
        b = self.new_job("UCIE:B", kind="UCIE_LIBRARY_INDEX_CHECK")
        first = self.claim(limit=1)
        self.assertEqual(first["claimed"][0]["job_id"], a["job_id"])
        blocked = q.finish_job(self.root, job_id=a["job_id"],
                               lease_token=first["claimed"][0]["lease_token"],
                               outcome="BLOCKED", reason="UPSTREAM_RATE_LIMIT",
                               now=T0 + timedelta(seconds=2),
                               retry_after_seconds=600)
        self.assertEqual(blocked["status"], "PENDING")
        self.assertEqual(q._parse(blocked["next_due_at"]),
                         T0 + timedelta(seconds=602))
        second = self.claim(at=T0 + timedelta(seconds=3), limit=1)
        self.assertEqual(second["claimed"][0]["job_id"], b["job_id"])
        finished = q.finish_job(
            self.root, job_id=b["job_id"],
            lease_token=second["claimed"][0]["lease_token"],
            outcome="SUCCEEDED", now=T0 + timedelta(seconds=4))
        self.assertEqual(finished["status"], "SUCCEEDED")
        self.assertEqual(self.claim(at=T0 + timedelta(seconds=30))["claimed_count"], 0)
        state = q.inspect_queue(self.root)
        self.assertEqual(state["counts"]["PENDING"], 1)
        self.assertEqual(state["counts"]["SUCCEEDED"], 1)
        self.assertEqual(state["jobs"][0]["last_reason"], "UPSTREAM_RATE_LIMIT")
        self.assertEqual(state["lease_tokens_exported"], 0)

    def test_long_running_a_does_not_block_b_and_heartbeat_preserves_running(self):
        self.init()
        a = self.new_job("UCIE:LONG")
        b = self.new_job("UCIE:NEXT", kind="UCIE_QA_REVIEW")
        job = self.claim(limit=1, lease=120)["claimed"][0]
        beat = q.heartbeat(self.root, job_id=a["job_id"],
                           lease_token=job["lease_token"],
                           now=T0 + timedelta(seconds=80),
                           extension_seconds=300)
        self.assertEqual(beat["status"], "LEASE_RENEWED_RUNNING")
        other = self.claim(at=T0 + timedelta(minutes=2), limit=1)
        self.assertEqual(other["claimed"][0]["job_id"], b["job_id"])
        self.assertEqual(other["stale_requeued_count"], 0)
        state = q.inspect_queue(self.root)
        self.assertEqual(state["counts"]["RUNNING"], 2)
        self.assertEqual(state["counts"]["PENDING"], 0)
        q.finish_job(self.root, job_id=b["job_id"],
                     lease_token=other["claimed"][0]["lease_token"],
                     outcome="SUCCEEDED", now=T0 + timedelta(minutes=2, seconds=1))
        q.finish_job(self.root, job_id=a["job_id"],
                     lease_token=job["lease_token"],
                     outcome="SUCCEEDED", now=T0 + timedelta(minutes=3))
        self.assertEqual(q.inspect_queue(self.root)["counts"]["SUCCEEDED"], 2)

    def test_stale_worker_is_fenced_and_requeued_without_blocking_other_jobs(self):
        self.init()
        a = self.new_job("UCIE:STALE")
        b = self.new_job("UCIE:READY")
        first = self.claim(limit=1, lease=60)["claimed"][0]
        t = T0 + timedelta(seconds=61)
        next_one = self.claim(at=t, limit=1)
        self.assertEqual(next_one["stale_requeued_count"], 1)
        self.assertEqual(next_one["claimed"][0]["job_id"], b["job_id"])
        self.assertEqual(q.inspect_queue(self.root)["counts"]["PENDING"], 1)
        with self.assertRaises(q.PendingQueueError):
            q.finish_job(self.root, job_id=a["job_id"],
                         lease_token=first["lease_token"], outcome="SUCCEEDED",
                         now=t)
        not_yet = self.claim(at=t + timedelta(seconds=30))
        self.assertEqual(not_yet["claimed_count"], 0)
        retry = self.claim(at=t + timedelta(seconds=60), limit=1)
        self.assertEqual(retry["claimed"][0]["job_id"], a["job_id"])
        self.assertNotEqual(retry["claimed"][0]["lease_token"],
                            first["lease_token"])
        self.assertEqual(retry["claimed"][0]["attempt"], 2)

    def test_retry_budget_turns_only_failing_job_into_review_required(self):
        self.init()
        a = self.new_job("UCIE:BAD", tries=2)
        b = self.new_job("UCIE:GOOD")
        first = self.claim(limit=1)["claimed"][0]
        p = q.finish_job(self.root, job_id=a["job_id"],
                         lease_token=first["lease_token"], outcome="BLOCKED",
                         reason="DEPENDENCY_NOT_READY",
                         now=T0 + timedelta(seconds=1))
        self.assertEqual(p["status"], "PENDING")
        other = self.claim(at=T0 + timedelta(seconds=2), limit=1)["claimed"][0]
        self.assertEqual(other["job_id"], b["job_id"])
        q.finish_job(self.root, job_id=b["job_id"], lease_token=other["lease_token"],
                     outcome="SUCCEEDED", now=T0 + timedelta(seconds=3))
        due = q._parse(p["next_due_at"])
        retry = self.claim(at=due, limit=1)["claimed"][0]
        self.assertEqual(retry["job_id"], a["job_id"])
        blocked = q.finish_job(self.root, job_id=a["job_id"],
                               lease_token=retry["lease_token"],
                               outcome="BLOCKED", reason="RETRYABLE_ERROR",
                               now=due + timedelta(seconds=1))
        self.assertEqual(blocked["status"], "REVIEW_REQUIRED")
        self.assertEqual(self.claim(at=due + timedelta(hours=2))["claimed_count"], 0)
        status = q.inspect_queue(self.root)
        self.assertEqual(status["counts"]["SUCCEEDED"], 1)
        self.assertEqual(status["counts"]["REVIEW_REQUIRED"], 1)

    def test_duplicate_is_idempotent_not_a_second_worker(self):
        self.init()
        one = self.new_job("UCIE:SOURCE:PYTHON")
        duplicate = self.new_job("UCIE:SOURCE:PYTHON")
        self.assertEqual(duplicate["status"], "DUPLICATE_NOT_ENQUEUED")
        self.assertEqual(duplicate["job_id"], one["job_id"])
        with self.assertRaises(q.PendingQueueError):
            self.new_job("UCIE:SOURCE:PYTHON", kind="UCIE_QA_REVIEW")
        self.assertEqual(self.claim(limit=4)["claimed_count"], 1)
        self.assertEqual(sum(q.inspect_queue(self.root)["counts"].values()), 1)

    def test_concurrent_dispatcher_transactions_fence_duplicate_claims(self):
        self.init()
        a = self.new_job("UCIE:ONE")
        def one_call(_):
            return self.claim(limit=1)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(one_call, (1, 2)))
        ids = [j["job_id"] for result in results for j in result["claimed"]]
        self.assertEqual(ids, [a["job_id"]])
        self.assertEqual(q.inspect_queue(self.root)["counts"]["RUNNING"], 1)

    def test_invalid_lease_and_outcome_are_rejected_without_state_mutation(self):
        self.init()
        a = self.new_job("UCIE:GUARD")
        claimed = self.claim()["claimed"][0]
        for invalid in (
            {"outcome": "BLOCKED", "reason": "secret failure message"},
            {"outcome": "BLOCKED", "reason": "WORKER_BUSY",
             "retry_after_seconds": 0},
            {"outcome": "SUCCEEDED", "reason": "RETRYABLE_ERROR"},
            {"outcome": "INVALID"},
        ):
            with self.assertRaises(q.PendingQueueError):
                q.finish_job(self.root, job_id=a["job_id"],
                             lease_token=claimed["lease_token"],
                             now=T0 + timedelta(seconds=1), **invalid)
        with self.assertRaises(q.PendingQueueError):
            q.finish_job(self.root, job_id=a["job_id"],
                         lease_token="0"*32, outcome="SUCCEEDED", now=T0)
        with self.assertRaises(q.PendingQueueError):
            q.heartbeat(self.root, job_id=a["job_id"],
                        lease_token="bad", now=T0)
        self.assertEqual(q.inspect_queue(self.root)["counts"]["RUNNING"], 1)

    def test_no_arbitrary_code_payload_source_paths_or_unbounded_queries(self):
        self.init()
        for key in ("../../OTHER", "UCIE job", "ucie:lower", "X"*97, ""):
            with self.subTest(key=key):
                with self.assertRaises(q.PendingQueueError):
                    self.new_job(key)
        with self.assertRaises(q.PendingQueueError):
            self.new_job("UCIE:INJECTION", kind="RUN_SHELL")
        with self.assertRaises(q.PendingQueueError):
            self.new_job("UCIE:BOOL", tries=True)
        with self.assertRaises(q.PendingQueueError):
            self.claim(limit=9)
        with self.assertRaises(q.PendingQueueError):
            self.claim(lease=10)

    def test_storage_is_independent_of_operating_miner_and_p8(self):
        prior_operating = self.root / "runtime" / "public_miner.sqlite3"
        prior_experience = self.root / "runtime" / "ucie_p8_experience_v1.jsonl"
        prior_operating.write_bytes(b"UCIE_PROTECTED_OPERATING_DB_FIXTURE")
        prior_experience.write_bytes(b"UCIE_FIRST_PARTY_EXPERIENCE_FIXTURE")
        before = (prior_operating.read_bytes(), prior_experience.read_bytes())
        self.init()
        self.new_job("UCIE:ISOLATED")
        self.claim()
        self.assertEqual(before, (
            prior_operating.read_bytes(), prior_experience.read_bytes()))

    def test_dedicated_ucie_root_required(self):
        wrong = self.root.parent / "Other"
        (wrong / "runtime").mkdir(parents=True)
        with self.assertRaises(q.PendingQueueError):
            q.initialize_queue(wrong)
        with self.assertRaises(q.PendingQueueError):
            q.inspect_queue(wrong)
        self.assertFalse((wrong / "runtime" / q.DB_NAME).exists())

    def test_cli_demo_and_status_do_not_install_queue_in_owner_checkout(self):
        with patch("sys.argv", ["queue", "--demo"]), patch(
                "builtins.print") as printed:
            self.assertEqual(q.main(), 0)
        body = json.loads(printed.call_args.args[0])
        self.assertEqual(body["status"], "NONBLOCKING_PENDING_DEMO_PASS")
        self.assertFalse(self.db.exists())
        with patch("sys.argv", ["queue", "--ucie-root", str(self.root)]), patch(
                "builtins.print") as printed:
            self.assertEqual(q.main(), 0)
        body = json.loads(printed.call_args.args[0])
        self.assertEqual(body["status"], "QUEUE_NOT_INSTALLED_READ_ONLY")
        self.assertFalse(self.db.exists())


if __name__ == "__main__":
    unittest.main()
