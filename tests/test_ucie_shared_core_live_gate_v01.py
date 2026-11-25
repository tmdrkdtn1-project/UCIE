"""Original BASE HTTP opener + durable shared quota + owner worker integration.

No real network, scheduler mutation, owner live DB, credentials or other project.
Tests use only disposable UCIE directories and mocked original urllib opener.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import urllib.error
import urllib.request

from ucie_miner.core import fetch_public_json, MiningError
from ucie_miner.shared_core_quota import (
    SharedCoreQuota, CoreQuotaHold, BASE_URL, NAME,
)
from ucie_miner.worker import run_cycle

NOW = 1_799_000_000
FILES_URL = (
    "https://api.github.com/repos/python/cpython/"
    "pulls/123/files?per_page=30"
)


def trusted_headers(now, *, remaining=55, reset=None):
    return {
        "Content-Type": "application/json",
        "X-RateLimit-Limit": "60",
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset or (now + 1200)),
        "X-RateLimit-Resource": "core",
    }


class FakeResponse:
    status = 200

    def __init__(self, headers, body=b"[]"):
        self.headers = headers
        self.body = body

    def read(self, _limit):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_unused):
        return False


class CountingOpener:
    def __init__(self, replies):
        self.calls = 0
        self.replies = list(replies)

    def open(self, request, timeout):
        self.calls += 1
        assert request.get_method() == "GET"
        assert request.full_url.startswith(
            "https://api.github.com/repos/python/cpython/")
        assert timeout == 12
        answer = self.replies.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class SharedCoreRealFetcherTests(TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="ucie-base-real-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "UCIE"
        self.root.mkdir()
        (self.root / "runtime").mkdir()
        self.epoch = NOW
        self.quota = SharedCoreQuota(self.root, clock=lambda: self.epoch)

    def _fetch_with(self, url, replies, *, bootstrap=False, quota=True):
        opener = CountingOpener(replies)
        with patch.object(urllib.request, "build_opener",
                          return_value=opener), patch.object(
            urllib.request, "urlopen",
            side_effect=AssertionError("unapproved network branch")
        ):
            response = fetch_public_json(
                url, core_quota=self.quota if quota else None,
                reviewed_first_get=bootstrap)
        return response, opener.calls

    def _bootstrap(self, *, remaining=55, reset=None):
        return self._fetch_with(
            BASE_URL, [FakeResponse(
                trusted_headers(self.epoch, remaining=remaining, reset=reset)
            )], bootstrap=True,
        )

    def test_01_actual_base_fetch_bootstrap_and_files_share_one_sqlite(self):
        value, attempts = self._bootstrap()
        self.assertEqual((value, attempts), ([], 1))
        self.assertEqual(self.quota.inspect()["phase"], "READY")
        self.assertTrue((self.root / "runtime" / NAME).is_file())
        value, attempts = self._fetch_with(
            FILES_URL, [FakeResponse(
                trusted_headers(self.epoch, remaining=54))])
        self.assertEqual((value, attempts), ([], 1))
        self.assertEqual(self.quota.inspect()["remaining_estimate"], 54)

    def test_02_default_original_get_remains_unchanged_and_no_quota_file(self):
        value, attempts = self._fetch_with(
            BASE_URL, [FakeResponse({"Content-Type": "application/json"})],
            quota=False)
        self.assertEqual((value, attempts), ([], 1))
        self.assertFalse((self.root / "runtime" / NAME).exists())

    def test_03_no_new_db_or_get_without_owner_bootstrap(self):
        opener = CountingOpener([FakeResponse(trusted_headers(self.epoch))])
        with patch.object(urllib.request, "build_opener",
                          return_value=opener):
            with self.assertRaises(MiningError):
                fetch_public_json(BASE_URL, core_quota=self.quota)
        self.assertEqual(opener.calls, 0)
        self.assertFalse((self.root / "runtime" / NAME).exists())

    def test_04_http403_sticky_block_with_no_second_opener(self):
        self._bootstrap()
        upstream = urllib.error.HTTPError(
            FILES_URL, 403, "UNTRUSTED_BODY", {}, None)
        opener = CountingOpener([upstream, FakeResponse(
            trusted_headers(self.epoch, remaining=50))])
        with patch.object(urllib.request, "build_opener",
                          return_value=opener):
            try:
                with self.assertRaises(MiningError):
                    fetch_public_json(FILES_URL, core_quota=self.quota)
                with self.assertRaises(MiningError):
                    fetch_public_json(FILES_URL, core_quota=self.quota)
            finally:
                upstream.close()
        self.assertEqual(opener.calls, 1)
        self.assertEqual(self.quota.inspect()["phase"], "HOLD")
        self.assertEqual(self.quota.inspect()["reason"],
                         "UPSTREAM_403_429_STICKY_HOLD")

    def test_05_bad_core_headers_fail_closed_after_one_real_opener(self):
        self._bootstrap()
        opener = CountingOpener(
            [FakeResponse({"Content-Type": "application/json"})])
        with patch.object(urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(MiningError):
                fetch_public_json(FILES_URL, core_quota=self.quota)
        self.assertEqual(opener.calls, 1)
        self.assertEqual(self.quota.inspect()["phase"], "HOLD")
        with self.assertRaises(CoreQuotaHold):
            self.quota.reserve(FILES_URL)

    def test_06_low_primary_remaining_stops_next_get(self):
        opener = CountingOpener([FakeResponse(
            trusted_headers(self.epoch, remaining=8))])
        with patch.object(urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(MiningError):
                fetch_public_json(BASE_URL, core_quota=self.quota,
                                  reviewed_first_get=True)
        self.assertEqual(opener.calls, 1)
        self.assertEqual(self.quota.inspect()["phase"], "HOLD")
        with self.assertRaises(CoreQuotaHold):
            self.quota.reserve(FILES_URL)
        self.assertEqual(self.quota.inspect()["reason"], "LOW_CORE_REMAINING")

    def test_07_untrusted_plan_fails_before_reservation_and_http(self):
        self._bootstrap()
        previous = self.quota.inspect()
        opener = CountingOpener([FakeResponse(
            trusted_headers(self.epoch, remaining=54))])
        with patch.object(urllib.request, "build_opener",
                          return_value=opener):
            for url in (
                "https://api.github.com/repos/private/repo/pulls/1",
                BASE_URL + "&page=999",
                "https://api.github.com/repos/python/cpython/actions/runs/1",
            ):
                with self.assertRaises(MiningError):
                    fetch_public_json(url, core_quota=self.quota)
        self.assertEqual(opener.calls, 0)
        self.assertEqual(self.quota.inspect(), previous)

    def test_08_single_inflight_crash_denies_other_owner_process(self):
        lease = self.quota.reserve(BASE_URL, reviewed_bootstrap=True)
        self.assertEqual(len(lease), 32)
        second = SharedCoreQuota(self.root, clock=lambda: self.epoch)
        with self.assertRaises(CoreQuotaHold):
            second.reserve(BASE_URL)
        self.assertEqual(second.inspect()["phase"], "INFLIGHT")

    def test_09_stale_window_then_one_original_base_reset_probe(self):
        _, attempts = self._bootstrap(reset=NOW + 600)
        self.assertEqual(attempts, 1)
        self.epoch += 400
        with self.assertRaises(CoreQuotaHold):
            self.quota.reserve(FILES_URL)
        self.assertEqual(self.quota.inspect()["phase"], "HOLD")
        self.epoch = NOW + 670
        with self.assertRaises(CoreQuotaHold):
            self.quota.reserve(FILES_URL)
        _, attempts = self._fetch_with(
            BASE_URL, [FakeResponse(trusted_headers(
                self.epoch, remaining=50, reset=NOW + 1800))])
        self.assertEqual(attempts, 1)
        self.assertEqual(self.quota.inspect()["phase"], "READY")
        self.assertEqual(self.quota.inspect()["remaining_estimate"], 50)

    def test_10_invalid_json_stays_sticky_after_get(self):
        opener = CountingOpener([
            FakeResponse(trusted_headers(self.epoch), body=b"{not json"),
        ])
        with patch.object(urllib.request, "build_opener",
                          return_value=opener):
            with self.assertRaises(MiningError):
                fetch_public_json(BASE_URL, core_quota=self.quota,
                                  reviewed_first_get=True)
        self.assertEqual(opener.calls, 1)
        self.assertEqual(self.quota.inspect()["phase"], "HOLD")

    def test_11_owner_interval_and_failed_receipt_never_retry(self):
        calls = []
        def completed(_root):
            calls.append("collect")
            return {
                "status": "COLLECTED_UNVERIFIED",
                "new_candidates": 0, "sources_checked": 1,
                "verification_pass": 0, "production_approved": False,
                "owner_pilot_gets_attempted": 1,
                "shared_core_quota_phase": "READY",
            }
        def write_report(root):
            reports = root / "runtime" / "reports"
            reports.mkdir(exist_ok=True)
            path = reports / "base.md"
            path.write_text("# UCIE UNVERIFIED", encoding="utf-8")
            return path
        first = run_cycle(
            self.root, collect=completed, write_report=write_report,
            enforce_schedule=True, owner_base_core_hourly=True)
        self.assertEqual(first["status"], "COLLECTED_UNVERIFIED")
        self.assertEqual(first["owner_pilot_gets_attempted"], 1)
        second = run_cycle(
            self.root, collect=lambda _: self.fail("NO REPEAT GET"),
            write_report=write_report, enforce_schedule=True,
            owner_base_core_hourly=True)
        self.assertEqual(second["status"], "SKIPPED_NOT_DUE")
        self.assertEqual(calls, ["collect"])
        # An owner failure cannot turn into a recurring automatic GET.
        record = self.root / "runtime" / "last_run.json"
        prior = json.loads(record.read_text(encoding="utf-8"))
        prior["status"] = "COLLECTION_FAILED"
        record.write_text(json.dumps(prior), encoding="utf-8")
        result = run_cycle(
            self.root, collect=lambda _: self.fail("STICKY FAIL"),
            write_report=write_report, enforce_schedule=True,
            owner_base_core_hourly=True)
        self.assertEqual(result["status"],
                         "SKIPPED_PUBLIC_RATE_OWNER_REVIEW_NO_GET")
        self.assertEqual(calls, ["collect"])
        self.assertEqual(json.loads(record.read_text())["status"],
                         "COLLECTION_FAILED")

    def test_12_wrong_old_stage10_rate_hold_blocks_owner_pilot(self):
        prior = {
            "schema": "UCIE_MINER_CYCLE_V1",
            "status": "COLLECTED_UNVERIFIED",
            "started_utc": (datetime.now(timezone.utc)
                             - timedelta(hours=2)).isoformat(),
            "finished_utc": (datetime.now(timezone.utc)
                              - timedelta(hours=2)).isoformat(),
            "stage10_error_category": "UPSTREAM_HTTP_403",
        }
        (self.root / "runtime" / "last_run.json").write_text(
            json.dumps(prior), encoding="utf-8")
        result = run_cycle(
            self.root, collect=lambda _: self.fail("NO GET"),
            enforce_schedule=True, owner_base_core_hourly=True)
        self.assertEqual(result["status"],
                         "SKIPPED_PUBLIC_RATE_OWNER_REVIEW_NO_GET")
        self.assertFalse((self.root / "runtime" / NAME).exists())
