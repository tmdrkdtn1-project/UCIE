"""P11 joined owner quiet collector cadence and first-party improvement QA."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from ucie_miner import p11_closed_loop as p11
from ucie_miner import pending_queue
from ucie_miner.public_discovery import SOURCES, public_feed_url, DiscoveryError

T0 = datetime(2026, 10, 28, 10, tzinfo=timezone.utc)


def item(source, number, title="fix regression in python public tests"):
    return {
        "number": number, "title": title,
        "merged_at": "2026-10-27T02:00:00Z",
        "html_url": f"https://github.com/{source}/pull/{number}",
        "merge_commit_sha": f"{number:040x}",
        "base": {"repo": {"full_name": source}},
    }


class MergedP11OwnerQuietAndFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        pending_queue.initialize_queue(self.root)
        p11.activate(self.root)

    def ten_public_gets_with_no_leads(self):
        seen = []
        for i in range(10):
            source = SOURCES[i % len(SOURCES)]
            def empty(url, src=source):
                self.assertEqual(url, public_feed_url(src))
                seen.append(url)
                return []
            out = p11.collect_one(
                self.root, now=T0 + timedelta(minutes=5 * i), fetch=empty)
            self.assertEqual(out["new_unverified_leads"], 0)
        self.assertEqual(len(seen), 10)
        return seen

    def test_quiet_backoff_only_after_ten_gets_without_pending_leads(self):
        seen = self.ten_public_gets_with_no_leads()
        result = p11.collect_one(
            self.root, now=T0 + timedelta(minutes=50),
            fetch=lambda _: self.fail("quiet cooldown must block GET"))
        self.assertEqual(result["status"], "P11_RATE_WINDOW_NOT_DUE")
        self.assertTrue(result["quiet_collection_backoff"])
        self.assertEqual(result["interval_minutes"], 20)
        status = p11.status(self.root)
        self.assertTrue(status["quiet_collection_backoff"])
        self.assertEqual(status["effective_interval_minutes"], 20)
        self.assertEqual(
            datetime.fromisoformat(status["next_public_get_due_utc"]),
            T0 + timedelta(minutes=65))
        result = p11.collect_one(
            self.root, now=T0 + timedelta(minutes=65),
            fetch=lambda url: seen.append(url) or [])
        self.assertEqual(result["public_api_gets_this_call"], 1)
        self.assertEqual(len(seen), 11)
        self.assertEqual(p11.status(self.root)["total_successful_public_gets"], 11)
        self.assertEqual(p11.status(self.root)["improvement_review_record_count"], 0)

    def test_pending_experiment_disables_quiet_and_learning_writes_real_review(self):
        self.ten_public_gets_with_no_leads()
        selected = SOURCES[0]  # Ten successful GETs completed two rotations.
        added = p11.collect_one(
            self.root, now=T0 + timedelta(minutes=65),
            fetch=lambda url: [item(selected, 651)]
            if url == public_feed_url(selected) else self.fail("wrong source"))
        self.assertEqual(added["new_unverified_leads"], 1)
        status = p11.status(self.root)
        self.assertFalse(status["quiet_collection_backoff"])
        self.assertEqual(status["effective_interval_minutes"], 5)
        blocked = p11.collect_one(
            self.root, now=T0 + timedelta(minutes=68),
            fetch=lambda _: self.fail("base cooldown still applies"))
        self.assertEqual(blocked["interval_minutes"], 5)
        p11.collect_one(
            self.root, now=T0 + timedelta(minutes=70),
            fetch=lambda _: [])
        trial = p11.learn_one(
            self.root, now=T0 + timedelta(minutes=70, seconds=1))
        self.assertEqual(trial["improvement_review_records_written"], 1)
        self.assertTrue(trial["improvement_proposal_created"])
        self.assertFalse(trial["production_algorithm_changed"])
        snapshot = p11.status(self.root)
        self.assertEqual(snapshot["improvement_review_record_count"], 1)
        self.assertEqual(snapshot["awaiting_synthetic_experiment"], 0)
        # The idle interval after learning is clock-relative: a real current
        # time may be long after the synthetic test's frozen T0.
        self.assertEqual(snapshot["production_improvements_auto_applied"], 0)

    def test_failed_source_uses_original_five_minute_cooldown(self):
        self.ten_public_gets_with_no_leads()
        with self.assertRaises(DiscoveryError):
            p11.collect_one(
                self.root, now=T0 + timedelta(minutes=65),
                fetch=lambda _: (_ for _ in ()).throw(
                    DiscoveryError("synthetic rate limit 429")))
        status = p11.status(self.root)
        self.assertTrue(status["last_public_attempt_failed"])
        self.assertFalse(status["quiet_collection_backoff"])
        self.assertEqual(status["effective_interval_minutes"], 5)
        retry_pending = p11.collect_one(
            self.root, now=T0 + timedelta(minutes=66),
            fetch=lambda _: self.fail("early retry must not GET"))
        self.assertEqual(
            retry_pending["status"], "P11_FAILED_SOURCE_REMAINS_PENDING")
        self.assertEqual(retry_pending["interval_minutes"], 5)
        recovered = p11.collect_one(
            self.root, now=T0 + timedelta(minutes=70),
            fetch=lambda _: [])
        self.assertEqual(recovered["public_api_gets_this_call"], 1)
        self.assertFalse(p11.status(self.root)["last_public_attempt_failed"])


if __name__ == "__main__":
    unittest.main()
