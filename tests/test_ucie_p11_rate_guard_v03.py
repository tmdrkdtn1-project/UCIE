"""P11 exact GitHub 403/429 rate guard; no live GET or owner mutation.

All fetches are first-party deterministic injected mock calls in isolated
TemporaryDirectory/UCIE; upstream untrusted text must never be stored.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
import sqlite3
import unittest
from unittest.mock import patch

from ucie_miner import p11_closed_loop as p11
from ucie_miner import p11_rate_guard_v03 as rate
from ucie_miner import pending_queue as q
from ucie_miner import runtime_pipeline as p10

T0 = datetime.now(timezone.utc).replace(microsecond=0)
POISON = "UCIE_PUBLIC_UNTRUSTED_HEADER_OR_PR_TEXT_9876"


def fail(code: int, headers=None):
    return HTTPError("https://invalid.test/" + POISON,
                     code, "BODY " + POISON, headers or {}, None)


class UCIEP11PublicRateGuardV03Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_P11_RATE_GUARD_SYNTH_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        q.initialize_queue(self.root)
        p11.activate(self.root)

    def _failure(self, error, at=T0):
        count = []
        def fake(_url):
            count.append(True)
            raise error
        try:
            with self.assertRaises(HTTPError):
                p11.collect_one(self.root, now=at, fetch=fake)
        finally:
            error.close()
        self.assertEqual(len(count), 1)
        return p11.status(self.root)

    def _read_nonsecret(self):
        return (self.root / "runtime" / p11.DB_NAME).read_bytes()

    def test_01_429_retry_after_enforced_and_success_clears_guard(self):
        status = self._failure(fail(429, {"Retry-After": "900"}))
        self.assertTrue(status["rate_guard_active"])
        self.assertEqual(status["rate_guard_reason"],
                         "HTTP_429_RETRY_AFTER")
        self.assertEqual(status["rate_guard_not_before_utc"],
                         rate._stamp(T0 + timedelta(seconds=960)))
        for mins in (1, 5, 15):
            skipped = p11.collect_one(
                self.root, now=T0 + timedelta(minutes=mins),
                fetch=lambda _: self.fail("GET during exact retry-after"))
            self.assertEqual(skipped["status"], "P11_UPSTREAM_RATE_PAUSED_NO_GET")
            self.assertEqual(skipped["public_api_gets_this_call"], 0)
        success = p11.collect_one(
            self.root, now=T0 + timedelta(minutes=17),
            fetch=lambda _: [])
        self.assertEqual(success["status"],
                         "P11_PUBLIC_HASH_METADATA_STAGED_UNVERIFIED")
        self.assertEqual(success["public_api_gets_this_call"], 1)
        current = p11.status(self.root)
        self.assertFalse(current["rate_guard_active"])
        self.assertIsNone(current["rate_guard_reason"])
        self.assertFalse(current["last_public_attempt_failed"])
        self.assertEqual(current["total_successful_public_gets"], 1)

    def test_02_403_primary_reset_minute_buffer(self):
        reset = int((T0 + timedelta(minutes=90)).timestamp())
        st = self._failure(fail(403, {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset),
        }))
        self.assertEqual(st["rate_guard_reason"], "HTTP_403_PRIMARY_RESET")
        self.assertEqual(st["rate_guard_not_before_utc"],
                         rate._stamp(T0 + timedelta(minutes=91)))
        skipped = p11.collect_one(
            self.root, now=T0 + timedelta(minutes=90, seconds=30),
            fetch=lambda _: self.fail("should remain paused"))
        self.assertEqual(skipped["status"], "P11_UPSTREAM_RATE_PAUSED_NO_GET")
        result = p11.collect_one(
            self.root, now=T0 + timedelta(minutes=92), fetch=lambda _: [])
        self.assertEqual(result["public_api_gets_this_call"], 1)

    def test_03_403_with_no_rate_proof_requires_owner_no_repeat(self):
        st = self._failure(fail(403))
        self.assertEqual(st["rate_guard_reason"], "HTTP_403_OWNER_REVIEW")
        self.assertTrue(st["rate_guard_owner_review_required"])
        self.assertIsNone(st["rate_guard_not_before_utc"])
        skipped = p11.collect_one(
            self.root, now=T0 + timedelta(days=3),
            fetch=lambda _: self.fail("forbidden GET not allowed"))
        self.assertEqual(skipped["status"], "P11_UPSTREAM_RATE_PAUSED_NO_GET")
        self.assertTrue(skipped["rate_owner_review_required"])
        self.assertEqual(p11.status(self.root)["total_successful_public_gets"], 0)

    def test_04_429_no_hint_exponential_repeat_only_after_due(self):
        a = self._failure(fail(429))
        self.assertEqual(a["rate_guard_reason"], "HTTP_429_EXPONENTIAL_FALLBACK")
        self.assertEqual(a["rate_guard_not_before_utc"],
                         rate._stamp(T0 + timedelta(hours=1)))
        b = self._failure(fail(429), at=T0 + timedelta(hours=1, seconds=1))
        self.assertEqual(b["rate_guard_not_before_utc"],
                         rate._stamp(T0 + timedelta(hours=3, seconds=1)))
        with closing(sqlite3.connect(self.root / "runtime" / p11.DB_NAME)) as db:
            self.assertEqual(db.execute(
                "SELECT strikes FROM " + rate.TABLE).fetchone()[0], 2)

    def test_05_malformed_huge_retry_after_holds_for_owner(self):
        st = self._failure(fail(429, {"Retry-After": "999999999999"}))
        self.assertEqual(st["rate_guard_reason"], "RATE_HEADER_OWNER_REVIEW")
        self.assertTrue(st["rate_guard_owner_review_required"])
        self.assertNotIn(POISON.encode(), self._read_nonsecret())
        self.assertNotIn(b"https://invalid.test", self._read_nonsecret())

    def test_06_no_429_in_exception_text_shortcut(self):
        class LocalValidationError(ValueError):
            pass
        with self.assertRaises(LocalValidationError):
            p11.collect_one(
                self.root, now=T0,
                fetch=lambda _: (_ for _ in ()).throw(
                    LocalValidationError("429 " + POISON)))
        st = p11.status(self.root)
        self.assertFalse(st["rate_guard_active"])
        self.assertEqual(st["last_failed_public_attempt_category"],
                         "OTHER_FAILURE")
        self.assertNotIn(POISON.encode(), self._read_nonsecret())

    def test_07_runtime_treats_halted_get_as_no_network_success(self):
        st = self._failure(fail(429, {"Retry-After": "1800"}))
        self.assertTrue(st["rate_guard_active"])
        # _safe_handler is a strict first-party call. It now regards a
        # rate-pause guard as success for the local check, not a public GET.
        with patch.object(p11, "public_feed_get",
                          side_effect=AssertionError("NO_GET")):
            self.assertTrue(p10._safe_handler(
                self.root, "PUBLIC_INCREMENTAL_MINING"))
        st2 = p11.status(self.root)
        self.assertEqual(st2["total_successful_public_gets"], 0)
        self.assertTrue(st2["last_public_attempt_failed"])


    def test_08_both_retry_after_and_primary_reset_use_later_deadline(self):
        reset = int((T0 + timedelta(minutes=90)).timestamp())
        st = self._failure(fail(429, {
            "Retry-After": "900",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset),
        }))
        self.assertEqual(st["rate_guard_not_before_utc"],
                         rate._stamp(T0 + timedelta(minutes=91)))
        held = p11.collect_one(
            self.root, now=T0 + timedelta(minutes=20),
            fetch=lambda _: self.fail("primary reset not yet due"))
        self.assertEqual(held["status"], "P11_UPSTREAM_RATE_PAUSED_NO_GET")
        self.assertEqual(held["public_api_gets_this_call"], 0)

    def test_09_bad_reset_with_valid_retry_after_requires_owner(self):
        st = self._failure(fail(403, {
            "Retry-After": "3600",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "bad-from-upstream-" + POISON,
        }))
        self.assertEqual(st["rate_guard_reason"], "RATE_HEADER_OWNER_REVIEW")
        self.assertTrue(st["rate_guard_owner_review_required"])
        self.assertIsNone(st["next_public_get_due_utc"])
        self.assertNotIn(POISON.encode(), self._read_nonsecret())


if __name__ == "__main__":
    unittest.main()
