"""Approved public PR identity -> P11/P8 feedback with 65 synthetic legacy rows.

The three public PR identities below were independently retrieved from the
approved GitHub upstream repositories on 2026-10-30. Metadata, NOT source code
or a proven fix, is pinned as inert input. All 65 legacy history rows in this
test are synthetic fixtures: never claim these are the actual owner-host rows.
No API/network, host DB access, scheduler change, or candidate promotion.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import pending_queue
from ucie_miner import p11_closed_loop as p11
from ucie_miner.capability_trials import evaluate_ucie_owned_recipe
from ucie_miner.public_discovery import (
    SOURCES, DiscoveryError, discover_public_leads, public_feed_url,
)

OBSERVED = datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)

PUBLIC = (
    ("python/cpython", 160930,
     "gh-160561: Fix race in test_socket testFromFdError",
     "2026-10-30T06:46:19Z",
     "af79f49308f8f87896d1c09419db3f5ff67185af"),
    ("python/cpython", 160955,
     "[3.15] gh-160561: Fix race in test_socket testFromFdError (GH-160930)",
     "2026-10-30T07:28:24Z",
     "1bbe7e962876c2349d78b2df2a0c5d960e3c2da4"),
    ("PowerShell/PowerShell", 28275,
     "fix(msix): defer PowerShell updates while in use",
     "2026-10-28T22:42:16Z",
     "edcbda3ae12dfdbce68f382572515c7bacde59b2"),
)


def _public_metadata(item: tuple) -> dict:
    source, number, title, merged, commit = item
    return {
        "number": number, "title": title, "merged_at": merged,
        "html_url": f"https://github.com/{source}/pull/{number}",
        "merge_commit_sha": commit,
        "base": {"repo": {"full_name": source}},
    }


class P11PinnedActualPublicRevisionHistoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        pending_queue.initialize_queue(self.root)
        p11.activate(self.root)

    def _seed_65_synthetic_historical_experiences(self):
        """Populate ONLY this disposable test DB with history-shaped rows."""
        trial = evaluate_ucie_owned_recipe(
            "ENGINE_INCREMENTAL_BUILD", rows=128, queries=24, repeats=2)
        self.assertTrue(trial["exact_result_equivalence_observed"])
        self.assertTrue(trial["synthetic_operation_reduction_observed"])
        earlier = "2026-10-01T00:00:00+00:00"
        db = self.root / "runtime" / p11.DB_NAME
        with closing(sqlite3.connect(db)) as conn:
            for n in range(1, 66):
                number = 900000 + n
                conn.execute(
                    "INSERT INTO leads"
                    "(source,pr_number,merged_at,commit_sha,title_sha256,"
                    "tags,observed_at,reviewed) VALUES(?,?,?,?,?,?,?,1)",
                    (SOURCES[0], number, earlier, "a" * 40,
                     f"{n:064x}", '["CRASH"]', earlier))
                conn.execute(
                    "INSERT INTO experience"
                    "(source,pr_number,recipe,workload,baseline_ops,"
                    "candidate_ops,exact_equal,hypothesis_status,"
                    "observed_at,receipt_sha256) "
                    "VALUES(?,?,?,?,?,?,1,?,?,?)",
                    (SOURCES[0], number, "ENGINE_INCREMENTAL_BUILD", 128,
                     trial["baseline_operations"],
                     trial["candidate_operations_including_setup"],
                     "SYNTHETIC_UNVERIFIED_PROMISING", earlier, f"{n:064x}"))
            conn.commit()
        state = p11.status(self.root)
        self.assertEqual(state["first_party_experiences"], 65)
        self.assertEqual(state["improvement_review_record_count"], 0)
        self.assertFalse(state["prior_experience_auto_backfilled"])

    def test_real_upstream_metadata_with_65_legacy_experiences_gets_new_review(self):
        self._seed_65_synthetic_historical_experiences()
        cpython = [_public_metadata(item) for item in PUBLIC[:2]]
        powershell = [_public_metadata(PUBLIC[2])]

        # Verify exact public source metadata and SHA256 of opaque PR titles.
        for source, rows in ((SOURCES[0], cpython),
                             (SOURCES[1], powershell)):
            receipt = discover_public_leads(rows, source=source, now=OBSERVED)
            self.assertEqual(receipt["lead_count"], len(rows))
            self.assertFalse(receipt["production_approved"])
            self.assertEqual(receipt["persistent_writes"], 0)
            for lead, upstream in zip(receipt["leads"], rows):
                self.assertEqual(lead["title_sha256"],
                                 sha256(upstream["title"].encode()).hexdigest())
                self.assertEqual(lead["merge_commit_sha"],
                                 upstream["merge_commit_sha"])
                self.assertEqual(lead["status"], "UNVERIFIED_PUBLIC_LEAD")
                self.assertNotIn("title", lead)

        def first_get(url):
            self.assertEqual(url, public_feed_url(SOURCES[0]))
            return cpython

        def second_get(url):
            self.assertEqual(url, public_feed_url(SOURCES[1]))
            return powershell

        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no external network permitted")):
            staged = p11.collect_one(self.root, now=OBSERVED, fetch=first_get)
            self.assertEqual(staged["new_unverified_leads"], 2)
            self.assertEqual(p11.status(self.root)["awaiting_synthetic_experiment"], 2)
            self.assertEqual(p11.status(self.root)["improvement_review_record_count"], 0)

            first = p11.learn_one(self.root, now=OBSERVED + timedelta(seconds=1))
            second = p11.learn_one(self.root, now=OBSERVED + timedelta(seconds=2))
            self.assertEqual(first["recipe"], "ENGINE_INCREMENTAL_BUILD")
            self.assertEqual(first["workload"], 512)  # 65 prior passes -> 512
            self.assertEqual(second["workload"], 128)  # 66 prior passes -> 128
            for result in (first, second):
                self.assertEqual(result["improvement_review_records_written"], 1)
                self.assertTrue(result["exact_result_equivalence"])
                self.assertFalse(result["auto_promoted"])
                self.assertFalse(result["production_algorithm_changed"])

            staged_next = p11.collect_one(
                self.root, now=OBSERVED + timedelta(minutes=5),
                fetch=second_get)
            self.assertEqual(staged_next["new_unverified_leads"], 1)
            third = p11.learn_one(
                self.root, now=OBSERVED + timedelta(minutes=5, seconds=1))
            self.assertEqual(third["recipe"], "LEARNING_FEEDBACK_LOOP")
            self.assertEqual(third["improvement_review_records_written"], 1)

        summary = p11.status(self.root)
        self.assertEqual(summary["first_party_experiences"], 68)
        self.assertEqual(summary["improvement_review_record_count"], 3)
        self.assertEqual(summary["first_party_retest_proposals_not_adopted"], 3)
        self.assertEqual(summary["awaiting_synthetic_experiment"], 0)
        self.assertEqual(summary["production_improvements_auto_applied"], 0)
        self.assertEqual(summary["total_successful_public_gets"], 2)
        self.assertEqual(p11.learn_one(self.root)["status"],
                         "P11_NO_NEW_UNVERIFIED_LEADS")

        # Historical samples remain historical; never relabel the 65 old
        # receipts as 65 freshly observed P8 improvements.
        with closing(sqlite3.connect(
                self.root / "runtime" / p11.DB_NAME)) as conn:
            old = conn.execute(
                "SELECT COUNT(*) FROM experience "
                "WHERE pr_number BETWEEN 900001 AND 900065").fetchone()[0]
            linked = conn.execute(
                "SELECT e.pr_number,e.receipt_sha256,r.receipt_sha256 "
                "FROM experience AS e JOIN improvement_review AS r "
                "USING(source,pr_number) ORDER BY e.pr_number").fetchall()
        self.assertEqual(old, 65)
        self.assertEqual([r[0] for r in linked], [28275, 160930, 160955])
        self.assertTrue(all(r[1] == r[2] for r in linked))

        # Original PR and 3.15 backport reference the same GH issue family:
        # separate *PR identities* are not proof of distinct fixes.
        self.assertIn("GH-160930", PUBLIC[1][2])
        self.assertFalse(summary["production_algorithm_changed"])

    def test_forged_real_revision_identity_is_rejected_without_learning(self):
        base = _public_metadata(PUBLIC[0])
        for update in (
            {"html_url": "https://github.com/unapproved/repo/pull/160930"},
            {"merge_commit_sha": "not-a-git-sha"},
            {"base": {"repo": {"full_name": "unapproved/repo"}}},
            {"merged_at": "2099-10-30T06:46:19Z"},
        ):
            with self.subTest(update=update):
                with self.assertRaises(DiscoveryError):
                    discover_public_leads(
                        [{**base, **update}], source=SOURCES[0], now=OBSERVED)
        self.assertEqual(p11.status(self.root)["first_party_experiences"], 0)
        self.assertEqual(p11.status(self.root)["improvement_review_record_count"], 0)


if __name__ == "__main__":
    unittest.main()
