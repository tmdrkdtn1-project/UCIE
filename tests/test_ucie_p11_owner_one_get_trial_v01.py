"""At-most-one approved P11 public metadata GET, synthetic-only tests.

Live owner path is only PREVIEWED, never approved or network-called here.
No other projects, accounts, credentials, schedulers or private source.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from ucie_miner import p11_owner_one_get_trial_v01 as trial
from ucie_miner import pending_queue as q
from ucie_miner import runtime_pipeline as runtime
from ucie_miner import p11_closed_loop as p11
from ucie_miner import p11_rate_guard_v03 as rate
from ucie_miner import worker
from ucie_miner import p10_owner_single_live_rearm_v02 as owner
from ucie_miner import public_discovery

T0 = datetime(2026, 11, 15, 10, 0, 0, tzinfo=timezone.utc)
KINDS = (
    "UCIE_LIBRARY_INDEX_CHECK", "PUBLIC_METADATA_REVIEW",
    "UCIE_QA_REVIEW", "UCIE_FIRST_PARTY_EXPERIMENT",
    "UCIE_REPORT_PREPARATION", "PUBLIC_INCREMENTAL_MINING"
)
ROOT = Path(__file__).resolve().parents[1]


class OneOwnerGetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_P11_ONE_GET_SYNTH_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        (self.root / "runtime" / "UCIE_P11_ONE_GET_SYNTH_ONLY.marker"
         ).write_text(trial.SYNTH_MARKER, encoding="ascii")
        q.initialize_queue(self.root)
        for k in KINDS:
            q.enqueue(self.root, kind=k, dedupe_key=runtime.DEDUPES[k], due=T0)
        with closing(owner._conn(self.root, readonly=False)) as db:
            db.execute(
                "UPDATE jobs SET status='REVIEW_REQUIRED',attempts=5,"
                "last_reason='RETRYABLE_ERROR' "
                "WHERE kind='PUBLIC_INCREMENTAL_MINING'"
            )
        p11.activate(self.root)
        with closing(p11._conn(self.root)) as db:
            db.execute(
                "UPDATE cursor SET source_index=0,last_attempt_at=?,"
                "last_attempt_failed=1,total_public_gets=450 WHERE slot=1",
                ((T0-timedelta(days=1)).isoformat(timespec="microseconds"),))
        self._set_last_run(T0)
    
    def _set_last_run(self, finish):
        payload = {"schema":"UCIE_MINER_CYCLE_V1",
                   "status":"COLLECTED_UNVERIFIED",
                   "finished_utc":finish.isoformat(timespec="microseconds"),
                   "production_approved":False,"consecutive_failures":0}
        (self.root/"runtime"/"last_run.json").write_text(
            json.dumps(payload), encoding="utf-8")

    def _preview(self, now=T0):
        return trial.preview(self.root, now=now)

    def _apply(self, fetch, now=T0, sha=None):
        return trial.apply_one(
            self.root,
            expected_sha256=self._preview(now)["exact_held_row_sha256"]
                            if sha is None else sha,
            consent=trial.CONSENT, now=now, fetch=fetch)

    def _trial_state(self):
        with closing(p11._conn(self.root)) as db:
            return db.execute(
                "SELECT state,get_count,source_index,failure_class "
                "FROM "+trial.TABLE+" WHERE slot=1").fetchone()

    def test_01_exact_preview_read_only_unknown_shared_rate(self):
        before = q.inspect_queue(self.root)
        x = self._preview()
        self.assertEqual(x["status"],
                         "ONE_GET_OWNER_PREVIEW_ONLY_SHARED_QUOTA_UNKNOWN")
        self.assertEqual(x["job_id"], 6)
        self.assertEqual(x["source_id"], "repo:python/cpython")
        self.assertEqual(len(x["exact_held_row_sha256"]), 64)
        self.assertEqual(x["max_additional_approved_public_gets"], 1)
        self.assertFalse(x["shared_rate_remaining_verified"])
        self.assertEqual(before, q.inspect_queue(self.root))
        with closing(p11._conn(self.root)) as db:
            self.assertIsNone(db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (trial.TABLE,)).fetchone())

    def test_02_one_synthetic_success_no_job_rearm_replay_denied(self):
        seen = []
        def fake(url):
            seen.append(url)
            return []
        original = q.inspect_queue(self.root)
        x = self._apply(fake)
        self.assertEqual(x["status"],
                         "ONE_APPROVED_PUBLIC_GET_SUCCEEDED_UNVERIFIED")
        self.assertEqual(x["public_gets_requested"], 1)
        self.assertEqual(seen, ["https://api.github.com/repos/python/cpython/"
                                "pulls?state=closed&sort=updated&direction=desc&per_page=20"])
        row = self._trial_state()
        self.assertEqual(row["state"], "SUCCESS")
        self.assertEqual(row["get_count"], 1)
        self.assertIsNone(row["failure_class"])
        self.assertEqual(original, q.inspect_queue(self.root))
        self.assertEqual(p11.status(self.root)["total_successful_public_gets"], 451)
        with self.assertRaises(trial.OneGetError):
            self._apply(lambda _: self.fail("second GET"))
        self.assertEqual(len(seen), 1)

    def test_03_single_429_failure_rate_guard_and_no_replay(self):
        seen = []
        error = HTTPError("https://invalid.test/UNTRUSTED", 429,
                          "DO_NOT_STORE", {"Retry-After": "1200"}, None)
        self.addCleanup(error.close)
        def mock(url):
            seen.append(url)
            raise error
        before = q.inspect_queue(self.root)
        r = self._apply(mock)
        self.assertEqual(r["status"], "ONE_APPROVED_PUBLIC_GET_FAILED_NO_RETRY")
        self.assertEqual(r["public_gets_requested"], 1)
        self.assertEqual(r["sanitized_error_category"], "UPSTREAM_HTTP_429")
        self.assertEqual(self._trial_state()["state"], "FAILED")
        self.assertEqual(p11.status(self.root)["rate_guard_reason"],
                         "HTTP_429_RETRY_AFTER")
        self.assertEqual(q.inspect_queue(self.root), before)
        self.assertEqual(len(seen), 1)
        with self.assertRaises(trial.OneGetError):
            self._apply(lambda _: self.fail("replay GET forbidden"))

    def test_04_single_403_unhinted_permanent_owner_hold(self):
        error = HTTPError("https://invalid.test/UNTRUSTED", 403,
                          "FORBIDDEN", {}, None)
        self.addCleanup(error.close)
        def mock(url):
            raise error
        r = self._apply(mock)
        self.assertEqual(r["public_gets_requested"], 1)
        self.assertEqual(r["sanitized_error_category"], "UPSTREAM_HTTP_403")
        st = p11.status(self.root)
        self.assertEqual(st["rate_guard_reason"], "HTTP_403_OWNER_REVIEW")
        self.assertTrue(st["rate_guard_owner_review_required"])
        self.assertIsNone(st["next_public_get_due_utc"])
        self.assertEqual(q.inspect_queue(self.root)["counts"]["REVIEW_REQUIRED"], 1)

    def test_05_stale_miner_or_wrong_sha_denies_without_get(self):
        self._set_last_run(T0-timedelta(hours=2))
        with self.assertRaises(trial.OneGetError):
            trial.preview(self.root, now=T0)
        self._set_last_run(T0)
        with self.assertRaises(trial.OneGetError):
            self._apply(lambda _: self.fail("wrong SHA requested"), sha="0"*64)
        with closing(p11._conn(self.root)) as db:
            self.assertIsNone(db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (trial.TABLE,)).fetchone())

    def test_06_other_miner_lock_denies_without_get(self):
        with worker._single_instance(self.root/"runtime") as lock:
            self.assertTrue(lock)
            with self.assertRaises(trial.OneGetError):
                self._apply(lambda _: self.fail("no overlap GET"))
        with closing(p11._conn(self.root)) as db:
            self.assertIsNone(db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (trial.TABLE,)).fetchone())

    def test_07_source_cursor_and_rate_hold_deny(self):
        with closing(p11._conn(self.root)) as db:
            db.execute("UPDATE cursor SET source_index=1")
        with self.assertRaises(trial.OneGetError):
            self._preview()
        with closing(p11._conn(self.root)) as db:
            db.execute("UPDATE cursor SET source_index=0")
        error = HTTPError("https://invalid.test", 403, "X", {}, None)
        self.addCleanup(error.close)
        self._apply(lambda _: (_ for _ in ()).throw(error))
        with self.assertRaises(trial.OneGetError):
            self._preview()

    def test_08_recent_other_miner_rate_failure_blocks_trial(self):
        original = q.inspect_queue(self.root)
        self._set_last_run(T0)
        path = self.root/"runtime"/"last_run.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["stage10_status"] = "STAGE10_HOURLY_FAILED_NO_GO"
        data["stage10_error_category"] = "UPSTREAM_HTTP_429"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(trial.OneGetError):
            self._apply(lambda _: self.fail("GET on failed miner denied"))
        self.assertEqual(q.inspect_queue(self.root), original)

    def test_09_headers_observed_on_same_exact_get_no_raw_persistence(self):
        class FakeResponse:
            status = 200
            headers = {
                "Content-Type": "application/json",
                "X-RateLimit-Remaining": "37",
                "X-RateLimit-Reset": "1794720000",
                "X-Unsafe-Body": "UNTRUSTED_NEVER_RETAIN",
            }
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def read(self, n):
                self._max_read=n
                return b"[]"
        class FakeOpener:
            def open(self, request, timeout):
                if request.full_url != public_discovery.public_feed_url(
                        "python/cpython") or timeout != 12:
                    raise AssertionError("unexpected first-party route")
                return FakeResponse()
        seen=[]
        with patch.object(public_discovery.urllib.request, "build_opener",
                          return_value=FakeOpener()):
            payload=public_discovery.public_feed_get(
                public_discovery.public_feed_url("python/cpython"),
                observe_rate_headers=lambda h:
                    seen.append(trial._rate_header_snapshot(h)))
        self.assertEqual(payload, [])
        self.assertEqual(seen, [{
            "remaining":37,"reset_epoch":1794720000
        }])
        self.assertNotIn("X-Unsafe-Body", seen[0])

    @unittest.skipUnless(os.name == "nt", "owner Windows only")
    def test_10_owner_read_only_gate_never_calls_network(self):
        if ROOT.resolve() != owner.ROOT.resolve() or ROOT.is_symlink():
            self.skipTest("exact owner checkout absent")
        before = q.inspect_queue(ROOT)
        try:
            result = trial.preview(ROOT)
            out = {
                "schema": trial.SCHEMA,
                "status": result["status"],
                "kind": result["kind"],
                "job_id": result["job_id"],
                "shared_rate_remaining_verified":
                    result["shared_rate_remaining_verified"],
                "eligible_for_owner_one_get": True,
                "public_gets_requested": 0,
            }
        except trial.OneGetError:
            out = {
                "schema": trial.SCHEMA,
                "status": "OWNER_ONE_GET_PREFLIGHT_BLOCKED_NO_GO",
                "eligible_for_owner_one_get": False,
                "public_gets_requested": 0,
            }
        self.assertEqual(before, q.inspect_queue(ROOT))
        self.assertEqual(out["public_gets_requested"], 0)
        print("UCIE_P11_ONE_GET_OWNER_PREFLIGHT="+
              json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
