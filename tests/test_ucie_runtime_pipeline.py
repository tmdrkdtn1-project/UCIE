"""P10 real independent-process worker and one-minute short dispatcher tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from ucie_miner import pending_queue as q
from ucie_miner import runtime_pipeline as p


START = datetime(2026, 10, 28, 9, 0, tzinfo=timezone.utc)


class P10WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)

    def init(self):
        obj = p.initialize(self.root)
        self.assertFalse(obj["task_registered"])
        self.assertFalse(obj["public_miner_task_modified"])
        return obj

    def test_inert_no_init_no_public_miner_changed(self):
        self.assertFalse((self.root / "runtime" / q.DB_NAME).exists())
        with self.assertRaises(p.RuntimePipelineError):
            p.dispatch_tick(self.root, now=START, spawn=lambda *_: None)
        self.assertFalse((self.root / "runtime" / q.DB_NAME).exists())
        with patch("sys.argv", ["p10", "--ucie-root", str(self.root), "--tick"]):
            with patch("builtins.print") as printed:
                self.assertEqual(p.main(), 2)
        self.assertEqual(json.loads(printed.call_args.args[0])["status"],
                         "P10_FAIL_CLOSED")
        self.assertFalse((self.root / "runtime" / q.DB_NAME).exists())

    def test_healthy_a_running_does_not_block_other_two(self):
        self.init()
        launches = []
        one = p.dispatch_tick(
            self.root, now=START,
            spawn=lambda _root, lease: launches.append(lease))
        self.assertEqual(one["workers_launched"], 3)
        self.assertEqual(len(launches), 3)
        self.assertFalse(one["waited_for_running_jobs"])
        self.assertEqual(one["jobs_executed_in_dispatcher"], 0)
        state = q.inspect_queue(self.root)
        self.assertEqual(state["counts"]["RUNNING"], 3)
        self.assertEqual(state["counts"]["PENDING"], 2)
        next_tick = p.dispatch_tick(
            self.root, now=START + timedelta(seconds=60),
            spawn=lambda *_: self.fail("must not overlaunch"))
        self.assertEqual(next_tick["workers_launched"], 0)
        self.assertEqual(next_tick["running_before"], 3)
        current = q.inspect_queue(self.root)
        self.assertTrue(all(r["attempts"] == 0 for r in current["jobs"]
                            if r["status"] == "PENDING"))
        self.assertEqual(current["counts"]["RUNNING"], 3)

    def test_blocked_a_pending_b_c_succeed_and_rearm_after_period(self):
        self.init()
        launches = []
        p.dispatch_tick(self.root, now=START,
                        spawn=lambda _root, lease: launches.append(lease))
        a, b, c = launches
        block = q.finish_job(
            self.root, job_id=a["job_id"], lease_token=a["lease_token"],
            outcome="BLOCKED", reason="DEPENDENCY_NOT_READY",
            now=START + timedelta(seconds=1))
        self.assertEqual(block["status"], "PENDING")
        for job in (b, c):
            q.finish_job(self.root, job_id=job["job_id"],
                         lease_token=job["lease_token"],
                         outcome="SUCCEEDED", now=START + timedelta(seconds=2))
        second = []
        p.dispatch_tick(self.root, now=START + timedelta(seconds=3),
                        spawn=lambda _root, lease: second.append(lease))
        self.assertEqual(len(second), 2)
        self.assertNotIn(a["job_id"], {r["job_id"] for r in second})
        counts = q.inspect_queue(self.root)["counts"]
        self.assertEqual(counts["PENDING"], 1)
        self.assertEqual(counts["RUNNING"], 2)
        self.assertEqual(counts["SUCCEEDED"], 2)
        # The first job (1-minute index) was blocked; B/C successes
        # recur after 5 minutes, never after an arbitrary 1-minute tick.
        for job in second:
            q.finish_job(self.root, job_id=job["job_id"],
                         lease_token=job["lease_token"],
                         outcome="SUCCEEDED", now=START + timedelta(seconds=4))
        later = p.dispatch_tick(self.root, now=START + timedelta(seconds=305),
                                spawn=lambda *_: None)
        self.assertGreaterEqual(later["rearmed_successful_jobs"], 1)
        with q.closing(q._conn(self.root)) as db:
            hist = db.execute(
                "SELECT kind, completion_count FROM p10_completed").fetchall()
        self.assertTrue(hist)
        self.assertTrue(all(h["completion_count"] >= 1 for h in hist))

    def test_rearm_history_is_constant_size_with_monotonic_per_kind_count(self):
        self.init()
        kind = "UCIE_LIBRARY_INDEX_CHECK"
        p.dispatch_tick(self.root, now=START, spawn=lambda *_: None)
        with q.closing(q._conn(self.root)) as db:
            job = db.execute("SELECT job_id,lease_token FROM jobs WHERE kind=?",
                             (kind,)).fetchone()
        for n in range(4):
            clock = START + timedelta(minutes=n*2, seconds=3)
            if n:
                p.dispatch_tick(self.root, now=clock,
                                spawn=lambda *_: None)
                with q.closing(q._conn(self.root)) as db:
                    job = db.execute(
                        "SELECT job_id,lease_token FROM jobs WHERE kind=?",
                        (kind,)).fetchone()
            q.finish_job(self.root, job_id=job["job_id"],
                         lease_token=job["lease_token"],
                         outcome="SUCCEEDED", now=clock)
        p._schedule(self.root, now=START + timedelta(minutes=9))
        with q.closing(q._conn(self.root)) as db:
            rows = db.execute(
                "SELECT kind,completion_count FROM p10_completed WHERE kind=?",
                (kind,)).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["completion_count"], 4)
        self.assertLessEqual(sum(q.inspect_queue(self.root)["counts"].values()), 5)

    def test_failed_launch_does_not_block_remaining_workers(self):
        self.init()
        launched = []
        def spawn(_root, job):
            if not launched:
                launched.append("FIRST_FAILED")
                raise OSError("synthetic worker spawn unavailable")
            launched.append(job["job_id"])
        out = p.dispatch_tick(self.root, now=START, spawn=spawn)
        self.assertEqual(out["launch_failures_pending"], 1)
        self.assertEqual(out["workers_launched"], 2)
        self.assertEqual(len(launched), 3)
        with q.closing(q._conn(self.root)) as db:
            failed = db.execute("SELECT status,last_reason FROM jobs WHERE job_id=1").fetchone()
        self.assertEqual(failed["status"], "PENDING")
        self.assertEqual(failed["last_reason"], "RETRYABLE_ERROR")
        self.assertEqual(q.inspect_queue(self.root)["counts"]["RUNNING"], 2)

    def test_stale_lease_is_reclaimed_with_existing_workers_unblocked(self):
        self.init()
        launches = []
        p.dispatch_tick(self.root, now=START,
                        spawn=lambda _root, job: launches.append(job))
        at = START + timedelta(seconds=121)
        new = []
        tick = p.dispatch_tick(self.root, now=at,
                               spawn=lambda _root, job: new.append(job))
        self.assertEqual(tick["expired_worker_jobs_requeued"], 3)
        self.assertEqual(tick["workers_launched"], 2)
        self.assertEqual(len(new), 2)
        with self.assertRaises(q.PendingQueueError):
            q.finish_job(self.root, job_id=launches[0]["job_id"],
                         lease_token=launches[0]["lease_token"],
                         outcome="SUCCEEDED", now=at)

    def test_handlers_actual_first_party_readonly_or_explicit_not_ready(self):
        self.init()
        self.assertTrue(p._safe_handler(self.root, "UCIE_QA_REVIEW"))
        self.assertTrue(p._safe_handler(self.root, "UCIE_FIRST_PARTY_EXPERIMENT"))
        self.assertTrue(p._safe_handler(self.root, "UCIE_REPORT_PREPARATION"))
        self.assertFalse(p._safe_handler(self.root, "PUBLIC_METADATA_REVIEW"))
        self.assertFalse(p._safe_handler(self.root, "UCIE_LIBRARY_INDEX_CHECK"))
        with self.assertRaises(p.RuntimePipelineError):
            p._safe_handler(self.root, "UNTRUSTED_SCRIPT")

    def test_real_independent_python_worker_processes_a_blocks_b_succeeds(self):
        self.init()
        source_dir = Path(__file__).resolve().parents[1] / "src"
        # Only UCIE's own source package copied into the isolated synthetic
        # UCIE test root. Neither a non-UCIE project nor live operator ledgers.
        shutil.copytree(source_dir, self.root / "src")
        actual_now = datetime.now(timezone.utc)
        a = q.enqueue(self.root, kind="PUBLIC_METADATA_REVIEW",
                      dedupe_key="UCIE:TEST:A", due=actual_now)
        b = q.enqueue(self.root, kind="UCIE_QA_REVIEW",
                      dedupe_key="UCIE:TEST:B", due=actual_now)
        leases = q.claim_ready(self.root, now=actual_now, limit=2)
        l1, l2 = leases["claimed"]
        self.assertEqual((l1["job_id"], l2["job_id"]),
                         (a["job_id"], b["job_id"]))
        blocked = p._worker(self.root, a["job_id"], l1["lease_token"])
        good = p._worker(self.root, b["job_id"], l2["lease_token"])
        self.assertEqual(blocked["status"], "PENDING")
        self.assertEqual(good["status"], "SUCCEEDED")
        snapshot = q.inspect_queue(self.root)
        self.assertEqual(snapshot["counts"]["PENDING"], 1)
        self.assertEqual(snapshot["counts"]["SUCCEEDED"], 1)

    def test_real_dispatcher_async_spawns_without_waiting_for_child_results(self):
        self.init()
        shutil.copytree(Path(__file__).resolve().parents[1] / "src",
                        self.root / "src")
        t = time.monotonic()
        out = p.dispatch_tick(self.root)
        elapsed = time.monotonic() - t
        self.assertEqual(out["workers_launched"], 3)
        self.assertLess(elapsed, 5.0)
        # All children must settle before synthetic temp directory cleanup.
        last = None
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            last = q.inspect_queue(self.root)
            if last["counts"]["RUNNING"] == 0:
                break
            time.sleep(0.15)
        self.assertIsNotNone(last)
        self.assertEqual(last["counts"]["RUNNING"], 0, last)
        self.assertGreaterEqual(
            last["counts"]["PENDING"] + last["counts"]["SUCCEEDED"], 3)
        self.assertEqual(out["jobs_executed_in_dispatcher"], 0)

    def test_scheduler_entrypoint_binds_exact_ucie_source_without_task_environment(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        wrapper = (scripts / "internal_minute_tick.py").read_text(encoding="utf-8")
        installer = (scripts / "install_internal_minute_task.ps1").read_text(encoding="utf-8")
        self.assertIn('sys.path.insert(0, str(ROOT / "src"))', wrapper)
        self.assertIn('expected = Path("D:/UCIE").resolve()', wrapper)
        self.assertIn("from ucie_miner.runtime_pipeline import dispatch_tick", wrapper)
        self.assertIn("internal_minute_tick.py", installer)
        self.assertIn("New-TimeSpan -Minutes 1", installer)
        self.assertIn("MultipleInstances IgnoreNew", installer)
        self.assertIn("param([switch]$Install)", installer)
        self.assertIn("PREVIEW_ONLY_NO_QUEUE_OR_TASK_CREATION", installer)
        self.assertNotIn("UCIE-PublicMiner-Hourly", installer)

    def test_explicit_initialization_is_only_queue_mutation(self):
        original = self.root / "runtime" / "public_miner.sqlite3"
        p8 = self.root / "runtime" / "ucie_p8_experience_v1.jsonl"
        original.write_bytes(b"UCIE-existing-miner")
        p8.write_bytes(b"UCIE-existing-P8")
        hashes_before = (original.read_bytes(), p8.read_bytes())
        p.initialize(self.root)
        p.dispatch_tick(self.root, now=START, spawn=lambda *_: None)
        self.assertEqual(hashes_before, (original.read_bytes(), p8.read_bytes()))
        self.assertFalse((self.root / "runtime" / "stage12_unverified_review.sqlite3").exists())

    def test_cli_requires_explicit_queue_init_and_exec_kind_allowlist(self):
        with patch("sys.argv", ["P10", "--ucie-root", str(self.root),
                                "--initialize"]), patch("builtins.print") as out:
            self.assertEqual(p.main(), 0)
        receipt = json.loads(out.call_args.args[0])
        self.assertEqual(receipt["status"], "P10_QUEUE_INITIALIZED_NO_TASK_REGISTERED")
        with patch("sys.argv", ["P10", "--ucie-root", str(self.root),
                                "--execute", "--kind", "UCIE_QA_REVIEW"]), patch(
                                "builtins.print") as out:
            self.assertEqual(p.main(), 0)
        receipt = json.loads(out.call_args.args[0])
        self.assertEqual(receipt["status"], "HANDLER_READ_ONLY_SUCCESS")
        with patch("sys.argv", ["P10", "--ucie-root", str(self.root),
                                "--worker", "--job-id", "2"]), patch(
                                "builtins.print") as out:
            self.assertEqual(p.main(), 2)
        self.assertEqual(json.loads(out.call_args.args[0])["status"], "P10_FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
