"""P11 public collector forward-only sanitized failure classification.

Only isolated disposable UCIE and injected fake public GETs. No actual network,
P10 rearm, model training or production database mutation.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from urllib.error import HTTPError, URLError

from ucie_miner import pending_queue as queue
from ucie_miner import p11_closed_loop as p11
from ucie_miner.public_discovery import DiscoveryError

T0 = datetime(2026, 11, 15, 9, tzinfo=timezone.utc)
POISON = "SYNTHETIC_UNTRUSTED_TITLE_DO_NOT_RETAIN_9482"


class P11ClosedCategoryReceiptsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_P11_ENUM_FAIL_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        queue.initialize_queue(self.root)
        p11.activate(self.root)

    def _fail(self, exc, *, clock=T0):
        calls = []
        def fetch(url):
            calls.append(url)
            raise exc
        with self.assertRaises(type(exc)):
            p11.collect_one(self.root, now=clock, fetch=fetch)
        self.assertEqual(len(calls), 1)
        return p11.status(self.root)

    def test_01_429_is_enum_no_raw_text_and_five_minute_cooldown(self):
        underlying = HTTPError("https://invalid.test/" + POISON, 429,
                               "raw " + POISON, {}, None)
        try:
            raise DiscoveryError("raw " + POISON) from underlying
        except DiscoveryError as exc:
            report = self._fail(exc)
        underlying.close()
        self.assertEqual(report["last_failed_public_attempt_category"],
                         "UPSTREAM_HTTP_429")
        self.assertTrue(report["last_public_attempt_failed"])
        self.assertEqual(report["next_source_id"], "repo:python/cpython")
        result = p11.collect_one(self.root, now=T0 + timedelta(minutes=1),
                                 fetch=lambda _: self.fail("unexpected GET"))
        self.assertEqual(result["status"], "P11_FAILED_SOURCE_REMAINS_PENDING")
        raw = (self.root / "runtime" / p11.DB_NAME).read_bytes()
        self.assertNotIn(POISON.encode(), raw)
        self.assertNotIn(b"https://invalid.test", raw)
        self.assertEqual(report["production_improvements_auto_applied"], 0)

    def test_02_403_and_network_are_distinct_bounded_classes(self):
        error = HTTPError("https://invalid.test", 403, "forbidden", {}, None)
        try:
            raise DiscoveryError("ignored") from error
        except DiscoveryError as exc:
            a = self._fail(exc)
        error.close()
        self.assertEqual(a["last_failed_public_attempt_category"],
                         "UPSTREAM_HTTP_403")
        # Exact one-source cursor remains held on failure, not rotated.
        b = self._fail(URLError("disconnected " + POISON),
                       clock=T0 + timedelta(minutes=5))
        self.assertEqual(b["last_failed_public_attempt_category"],
                         "UPSTREAM_NETWORK_FAILURE")

    def test_03_malformed_response_has_generic_validation_class(self):
        a = self._fail(DiscoveryError("malformed " + POISON))
        self.assertEqual(a["last_failed_public_attempt_category"],
                         "DISCOVERY_VALIDATION_OR_RESPONSE_REJECTED")

    def test_04_success_clears_current_failure_class_without_erasing_receipt(self):
        self._fail(URLError("offline"))
        success = p11.collect_one(
            self.root, now=T0 + timedelta(minutes=5), fetch=lambda _url: [])
        self.assertEqual(success["public_api_gets_this_call"], 1)
        report = p11.status(self.root)
        self.assertIsNone(report["last_failed_public_attempt_category"])
        self.assertFalse(report["last_public_attempt_failed"])
        self.assertEqual(report["next_source_id"], "repo:PowerShell/PowerShell")

    def test_05_absent_new_table_cannot_invent_historical_cause(self):
        # No failure table before the first forward-observed failed attempt.
        self.assertEqual(p11.status(self.root)["last_failed_public_attempt_category"],
                         None)
        with closing(sqlite3.connect(self.root / "runtime" / p11.DB_NAME)) as db:
            self.assertNotIn(p11.ERROR_TABLE, {
                row[0] for row in db.execute("SELECT name FROM sqlite_master")
            })
        self.assertFalse(p11.status(self.root)["last_public_attempt_failed"])


if __name__ == "__main__":
    unittest.main()
