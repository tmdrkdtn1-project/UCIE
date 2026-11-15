"""UCIE 10-minute PublicMiner: HTTP403/429 must stop unattended GETs.

Only a disposable /UCIE synthetic root executes worker.run_cycle; exact
D:/UCIE owner case reads last_run.json only. No public network, queue
rearm, scheduler changes, secrets, promotion or external projects.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.error import HTTPError

from ucie_miner import worker
from ucie_miner.core import MiningError

ROOT = Path(__file__).resolve().parents[1]
POISON = "UCIE_UNTRUSTED_RESPONSE_DO_NOT_RETAIN_0095"


def failing_http(code: int, headers=None):
    def fail(_root):
        error = HTTPError("https://invalid.test/"+POISON, code,
                          "UNTRUSTED "+POISON, headers or {}, None)
        try:
            raise error
        except HTTPError as exc:
            try:
                raise MiningError("public fix miner rejected response") from exc
            finally:
                error.close()
    return fail


class UCIEPublicMinerRateHoldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_PUBLIC_403_HOLD_SYNTH_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root/"runtime").mkdir(parents=True)
    
    def _last(self):
        return (self.root/"runtime"/"last_run.json").read_bytes()

    def _run(self, collect):
        return worker.run_cycle(self.root, collect=collect,
                                enforce_schedule=True,
                                write_report=lambda _root:
                                    self.fail("failed GET must not write report"))

    def test_01_403_unhinted_sets_indefinite_owner_hold(self):
        first = self._run(failing_http(403))
        self.assertEqual(first["status"], "COLLECTION_FAILED")
        self.assertEqual(first["error_http_status"], 403)
        self.assertEqual(first["public_rate_pause_reason"], "HTTP_403_OWNER_REVIEW")
        self.assertIsNone(first["public_rate_pause_not_before_utc"])
        original = self._last()
        gate = self._run(lambda _: self.fail("403 must not GET again"))
        self.assertEqual(gate["status"],
                         "SKIPPED_PUBLIC_RATE_OWNER_REVIEW_NO_GET")
        self.assertEqual(gate["public_gets_this_run"], 0)
        self.assertTrue(gate["rate_owner_review_required"])
        self.assertEqual(self._last(), original)
        self.assertNotIn(POISON.encode(), original)
        self.assertNotIn(b"https://invalid.test", original)

    def test_02_historical_403_before_patch_still_fails_closed(self):
        now = datetime.now(timezone.utc)
        receipt = {
            "schema":"UCIE_MINER_CYCLE_V1","status":"COLLECTION_FAILED",
            "started_utc":(now-timedelta(minutes=11)).isoformat(),
            "finished_utc":(now-timedelta(minutes=10)).isoformat(),
            "consecutive_failures":1,"error_http_status":403,
            "production_approved":False,
        }
        target = self.root/"runtime"/"last_run.json"
        target.write_text(json.dumps(receipt), encoding="utf-8")
        before=target.read_bytes()
        r=self._run(lambda _: self.fail("no GET on old unknown 403"))
        self.assertEqual(r["status"],
                         "SKIPPED_PUBLIC_RATE_OWNER_REVIEW_NO_GET")
        self.assertEqual(r["public_gets_this_run"], 0)
        self.assertEqual(before, target.read_bytes())

    def test_03_429_retry_after_blocks_until_reset_and_no_raw(self):
        receipt = self._run(failing_http(429, {"Retry-After":"1200"}))
        self.assertEqual(receipt["error_http_status"], 429)
        self.assertEqual(receipt["public_rate_pause_reason"],
                         "HTTP_429_RETRY_AFTER")
        self.assertEqual(receipt["public_rate_pause_strikes"], 1)
        gate=self._run(lambda _: self.fail("early 429 retry not allowed"))
        self.assertEqual(gate["status"],
                         "SKIPPED_PUBLIC_RATE_PAUSED_NO_GET")
        self.assertEqual(gate["public_gets_this_run"], 0)
        until=datetime.fromisoformat(
            receipt["public_rate_pause_not_before_utc"])
        self.assertIsNone(worker._public_rate_failure_gate(
            receipt, now=until + timedelta(seconds=1)))
        self.assertNotIn(POISON.encode(), self._last())

    def test_04_rate_reset_primary_403_has_conservative_deadline(self):
        now = datetime.now(timezone.utc)
        reset = int((now + timedelta(minutes=40)).timestamp())
        receipt = self._run(failing_http(403, {
            "X-RateLimit-Remaining":"0",
            "X-RateLimit-Reset":str(reset),
        }))
        self.assertEqual(receipt["public_rate_pause_reason"],
                         "HTTP_403_PRIMARY_RESET")
        gate = self._run(lambda _: self.fail("reset not reached"))
        self.assertEqual(gate["status"],
                         "SKIPPED_PUBLIC_RATE_PAUSED_NO_GET")
        deadline = datetime.fromisoformat(
            receipt["public_rate_pause_not_before_utc"])
        self.assertGreaterEqual(deadline,
                                datetime.fromtimestamp(reset,timezone.utc))
        self.assertIsNone(worker._public_rate_failure_gate(
            receipt, now=deadline + timedelta(seconds=1)))

    def test_05_optional_stage10_or_stage13_limit_pauses_primary_get(self):
        now = datetime.now(timezone.utc)
        for previous in (
            {"stage10_error_category":"UPSTREAM_HTTP_403"},
            {"stage13_history_status":
                "EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO"},
            {"stage16_safe_qa_status":
                "STAGE16_SAFE_QA_24H_BUDGET_PAUSED_NO_GO"},
        ):
            r=worker._public_rate_failure_gate(previous, now=now)
            self.assertIsNotNone(r)
            self.assertEqual(r["status"],
                             "SKIPPED_PUBLIC_RATE_OWNER_REVIEW_NO_GET")
            self.assertEqual(r["public_gets_this_run"], 0)

    def test_06_safe_success_without_rate_error_not_blocked(self):
        self.assertIsNone(worker._public_rate_failure_gate(
            {"status":"COLLECTED_UNVERIFIED"}, now=datetime.now(timezone.utc)))
        self.assertIsNone(worker._public_rate_failure_gate(
            {"error_http_status":404}, now=datetime.now(timezone.utc)))

    def test_07_expired_http_reset_cannot_override_stage13_hold(self):
        now = datetime.now(timezone.utc)
        result = worker._public_rate_failure_gate({
            "error_http_status": 429,
            "public_rate_pause_reason": "HTTP_429_RETRY_AFTER",
            "public_rate_pause_not_before_utc":
                (now-timedelta(minutes=1)).isoformat(),
            "stage13_history_status":
                "EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO",
        }, now=now)
        self.assertEqual(result["status"],
                         "SKIPPED_PUBLIC_RATE_OWNER_REVIEW_NO_GET")
        self.assertEqual(result["public_gets_this_run"], 0)

    def test_08_safe_skip_is_not_mislabeled_as_collected(self):
        script = (ROOT / "scripts" / "public_miner_cycle.py").read_text(
            encoding="utf-8-sig")
        self.assertIn("SKIPPED_PUBLIC_RATE_OWNER_REVIEW_NO_GET", script)
        self.assertIn("SKIPPED_PUBLIC_RATE_PAUSED_NO_GET", script)
        self.assertIn('"COLLECTED_UNVERIFIED"', script)

    @unittest.skipUnless(os.name == "nt", "real owner Windows only")
    def test_09_real_owner_last_receipt_readonly_rate_gate(self):
        if ROOT.resolve() != Path("D:/UCIE").resolve() or ROOT.is_symlink():
            self.skipTest("exact owner UCIE checkout missing")
        path = ROOT/"runtime"/"last_run.json"
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
            self.skipTest("no bounded owner receipt")
        before = path.read_bytes()
        row = json.loads(before.decode("utf-8"))
        result=worker._public_rate_failure_gate(
            row, now=datetime.now(timezone.utc))
        out = {
            "schema":"UCIE_PUBLIC_MINER_HTTP_FAIL_CLOSED_GATE_V01",
            "previous_status":row.get("status"),
            "previous_http_status":row.get("error_http_status"),
            "rate_safe_skip_status":result.get("status") if result else None,
            "public_gets_requested":0,
            "last_receipt_unchanged":path.read_bytes()==before,
            "task_modified":False,
            "db_modified":False,
        }
        self.assertTrue(out["last_receipt_unchanged"])
        print("UCIE_LIVE_PUBLIC_RATE_GATE=" + json.dumps(
            out, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
