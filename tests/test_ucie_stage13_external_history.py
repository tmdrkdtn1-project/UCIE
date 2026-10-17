"""Synthetic offline acceptance for external five-source historical backfill."""
from contextlib import closing
from copy import deepcopy
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from ucie_miner.public_discovery import SOURCES, DiscoveryError
from ucie_miner.public_external_history import (
    DB_NAME, OPT_IN_FILE, OPT_IN_TOKEN, public_history_url,
    optional_external_history_backfill, inspect_external_history,
    fetch_public_history_page, MAX_PAGES,
)


def upstream_pr(source, number, *, title="Fix regression in public API"):
    return {
        "number": number,
        "title": title,
        "merged_at": "2022-02-01T01:02:03Z",
        "html_url": f"https://github.com/{source}/pull/{number}",
        "base": {"repo": {"full_name": source}},
        "merge_commit_sha": f"{number:040x}",
    }


class Stage13ExternalHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True)
        self.marker = self.runtime / OPT_IN_FILE
        self.prior = self.runtime / "public_miner.sqlite3"
        self.knowledge = self.runtime / "knowledge.sqlite3"
        self.prior.write_bytes(b"existing legacy data untouched")
        self.knowledge.write_bytes(b"existing knowledge untouched")
        self.urls = []

    def enable(self):
        self.marker.write_text(OPT_IN_TOKEN, encoding="ascii")

    def fetch(self, url):
        self.urls.append(url)
        source = next(s for s in SOURCES if f"/repos/{s}/" in url)
        page = int(url.split("&page=")[-1])
        if page == 1:
            return ([upstream_pr(source, 1000 + i) for i in range(20)], 42)
        if page == 2:
            return ([upstream_pr(source, 999)], 41)
        return ([], 40)

    def test_off_by_default_not_one_network_call(self):
        state = optional_external_history_backfill(
            self.root, fetch=lambda _: self.fail("unapproved network"))
        self.assertEqual(state["status"], "STAGE13_EXTERNAL_HISTORY_DISABLED")
        self.assertFalse((self.runtime / DB_NAME).exists())
        self.assertEqual(inspect_external_history(self.root)["indexed_evidence_revisions"], 0)

    def test_two_hourly_cycles_reach_historical_pages_and_exhaust(self):
        self.enable()
        old = self.prior.read_bytes(), self.knowledge.read_bytes()
        first = optional_external_history_backfill(self.root, fetch=self.fetch)
        self.assertEqual(first["external_gets"], 5)
        self.assertEqual(first["public_pr_records_examined"], 100)
        self.assertEqual(first["new_unverified_evidence_revisions"], 100)
        self.assertEqual(first["source_scope"], list(SOURCES))
        self.assertEqual(first["status"], "EXTERNAL_HISTORY_BACKFILL_OK_NO_GO")
        first_check = inspect_external_history(self.root)
        self.assertEqual(first_check["indexed_evidence_revisions"], 100)
        self.assertTrue(all(v["next_page"] == 2
                            for v in first_check["source_cursors"].values()))
        second = optional_external_history_backfill(self.root, fetch=self.fetch)
        self.assertEqual(second["external_gets"], 5)
        self.assertEqual(second["new_unverified_evidence_revisions"], 5)
        self.assertEqual(second["public_pr_records_examined"], 5)
        inventory = inspect_external_history(self.root)
        self.assertEqual(inventory["indexed_evidence_revisions"], 105)
        self.assertTrue(all(v["state"] == "EXHAUSTED"
                            for v in inventory["source_cursors"].values()))
        third = optional_external_history_backfill(self.root, fetch=lambda _: self.fail("unexpected"))
        self.assertEqual(third["external_gets"], 0)
        self.assertEqual((self.prior.read_bytes(), self.knowledge.read_bytes()), old)
        with closing(sqlite3.connect(self.runtime / DB_NAME)) as conn:
            raw = str(conn.execute("SELECT * FROM upstream_history LIMIT 1").fetchone())
            bad = conn.execute("""SELECT count(*) FROM upstream_history
                WHERE state <> 'UNVERIFIED_CANDIDATE_ONLY'""").fetchone()[0]
        self.assertNotIn("Fix regression", raw)
        self.assertEqual(bad, 0)
        self.assertEqual([u.split("&page=")[-1] for u in self.urls],
                         ["1"] * 5 + ["2"] * 5)

    def test_older_than_90_days_is_not_dropped(self):
        self.enable()
        result = optional_external_history_backfill(
            self.root, fetch=lambda url: ([upstream_pr(next(
                s for s in SOURCES if f"/repos/{s}/" in url), 7)], 42))
        self.assertEqual(result["new_unverified_evidence_revisions"], 5)

    def test_unapproved_source_or_route_refused(self):
        for source, page in (
            ("example/unauthorized", 1),
            ("python/cpython", 0),
            ("python/cpython", MAX_PAGES + 1),
        ):
            with self.assertRaises(DiscoveryError):
                public_history_url(source, page)
        with self.assertRaises(DiscoveryError):
            fetch_public_history_page(
                "https://api.github.com/repos/python/cpython/private")
        self.assertEqual(self.urls, [])

    def test_git_page22_long_unmerged_title_is_excluded_without_cursor_stall(self):
        # The real approved git/git closed-PR page 22 contains unmerged
        # PR #1774 with a 419-character title. A closed-but-unmerged PR is
        # NOT a revision candidate and must not block the entire page.
        self.enable()
        initial = optional_external_history_backfill(
            self.root, fetch=lambda url: ([], 40))
        self.assertEqual(initial["status"], "EXTERNAL_HISTORY_BACKFILL_OK_NO_GO")
        with closing(sqlite3.connect(self.runtime / DB_NAME)) as db:
            db.execute("""UPDATE history_cursor SET next_page=22, scan_state='ACTIVE'
                WHERE source='git/git'""")
            db.commit()
        rows = [upstream_pr("git/git", 1774, title="L" * 419)]
        rows += [upstream_pr("git/git", 5000 + i) for i in range(19)]
        for entry in rows:
            entry["merged_at"] = None
        requested = []
        def page22_fetch(url):
            requested.append(url)
            self.assertEqual(url, public_history_url("git/git", 22))
            return rows, 40
        result = optional_external_history_backfill(
            self.root, fetch=page22_fetch)
        self.assertEqual(requested, [public_history_url("git/git", 22)])
        self.assertEqual(result["status"], "EXTERNAL_HISTORY_BACKFILL_OK_NO_GO")
        self.assertEqual(result["new_unverified_evidence_revisions"], 0)
        self.assertEqual(result["public_pr_records_examined"], 20)
        cursor = inspect_external_history(self.root)["source_cursors"]["git/git"]
        self.assertEqual(cursor["next_page"], 23)
        self.assertEqual(cursor["state"], "ACTIVE")
        self.assertEqual(inspect_external_history(self.root)["indexed_evidence_revisions"], 0)

    def test_unmerged_long_title_never_weakens_merged_validation(self):
        self.enable()
        def mixed_page(url):
            source = next(s for s in SOURCES if f"/repos/{s}/" in url)
            long_unmerged = upstream_pr(source, 1774, title="L" * 419)
            long_unmerged["merged_at"] = None
            valid = upstream_pr(source, 1775, title="Fix valid public regression")
            return [long_unmerged, valid], 40
        result = optional_external_history_backfill(self.root, fetch=mixed_page)
        self.assertEqual(result["status"], "EXTERNAL_HISTORY_BACKFILL_OK_NO_GO")
        self.assertEqual(result["new_unverified_evidence_revisions"], len(SOURCES))
        self.assertEqual(result["public_pr_records_examined"], 2 * len(SOURCES))
        with closing(sqlite3.connect(self.runtime / DB_NAME)) as db:
            numbers = db.execute("SELECT DISTINCT pr_number FROM upstream_history").fetchall()
        self.assertEqual(numbers, [(1775,)])
        # A MERGED PR with an oversized title must still fail closed, and
        # its cursor must remain on the rejected page.
        def forged_merged_title(url):
            source = next(s for s in SOURCES if f"/repos/{s}/" in url)
            return [upstream_pr(source, 1776, title="L" * 419)], 40
        with closing(sqlite3.connect(self.runtime / DB_NAME)) as db:
            db.execute("""UPDATE history_cursor SET next_page=1,scan_state='ACTIVE'
                WHERE source=?""", (SOURCES[0],))
            db.commit()
        second = optional_external_history_backfill(self.root, fetch=forged_merged_title)
        self.assertEqual(second["status"], "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO")
        self.assertEqual(second["failure_category"], "PUBLIC_METADATA_REJECTED")
        self.assertEqual(second["failure_source"], SOURCES[0])
        cursor = inspect_external_history(self.root)["source_cursors"][SOURCES[0]]
        self.assertEqual(cursor["next_page"], 1)
        self.assertEqual(inspect_external_history(self.root)["indexed_evidence_revisions"], len(SOURCES))

    def test_source_identity_mismatch_rolls_back_current_page(self):
        self.enable()
        def source_mismatch(url):
            source = next(s for s in SOURCES if f"/repos/{s}/" in url)
            bad = upstream_pr(source, 9)
            bad["base"]["repo"]["full_name"] = "unauthorized/cross-project"
            return [bad], 40
        result = optional_external_history_backfill(
            self.root, fetch=source_mismatch)
        self.assertEqual(result["status"], "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO")
        self.assertEqual(result["failure_source"], SOURCES[0])
        self.assertEqual(result["failure_category"], "PUBLIC_METADATA_REJECTED")
        self.assertEqual(result["external_gets"], 0)
        state = inspect_external_history(self.root)
        self.assertEqual(state["indexed_evidence_revisions"], 0)
        self.assertTrue(all(v["next_page"] == 1
                            for v in state["source_cursors"].values()))

    def test_transport_failure_is_bounded_and_identifies_approved_source(self):
        self.enable()
        def failing_public_transport(_):
            raise DiscoveryError("untrusted upstream response never stored")
        result = optional_external_history_backfill(
            self.root, fetch=failing_public_transport)
        self.assertEqual(result["status"], "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO")
        self.assertEqual(result["failure_source"], SOURCES[0])
        self.assertEqual(result["failure_category"], "FETCH_OR_RESPONSE_REJECTED")
        self.assertEqual(result["external_gets"], 0)
        self.assertNotIn("untrusted upstream", str(result))
        inventory = inspect_external_history(self.root)
        self.assertTrue(all(v["next_page"] == 1
                            for v in inventory["source_cursors"].values()))

    def test_rate_budget_pauses_before_second_source(self):
        self.enable()
        state = optional_external_history_backfill(
            self.root, fetch=lambda url: (
                [upstream_pr(SOURCES[0], 8)], 4))
        self.assertEqual(state["status"], "EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO")
        self.assertEqual(state["external_gets"], 1)
        self.assertEqual(state["new_unverified_evidence_revisions"], 1)

    def test_reject_invalid_optin(self):
        self.marker.write_text("AUTO_APPROVE_EXTERNAL_CODE", encoding="ascii")
        with self.assertRaises(DiscoveryError):
            optional_external_history_backfill(
                self.root, fetch=lambda _: self.fail("unapproved GET"))
        self.assertFalse((self.runtime / DB_NAME).exists())

    def test_reject_foreign_db_schema(self):
        self.enable()
        with closing(sqlite3.connect(self.runtime / DB_NAME)) as conn:
            conn.execute("CREATE TABLE unsafe_secret(data TEXT)")
            conn.commit()
        with self.assertRaises(DiscoveryError):
            optional_external_history_backfill(self.root, fetch=self.fetch)
        self.assertEqual(self.urls, [])

    def test_reject_unverified_commit_sha_and_html_url(self):
        self.enable()
        def bad_sha(url):
            source = next(s for s in SOURCES if f"/repos/{s}/" in url)
            wrong = upstream_pr(source, 8)
            wrong["merge_commit_sha"] = "not-a-sha"
            return ([wrong], 40)
        result = optional_external_history_backfill(self.root, fetch=bad_sha)
        self.assertEqual(result["status"], "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO")
        self.assertEqual(result["new_unverified_evidence_revisions"], 0)

    def test_idempotent_duplicate_on_explicit_cursor_revisit(self):
        self.enable()
        self.assertEqual(optional_external_history_backfill(
            self.root, fetch=self.fetch)["new_unverified_evidence_revisions"], 100)
        with closing(sqlite3.connect(self.runtime / DB_NAME)) as conn:
            conn.execute("UPDATE history_cursor SET next_page=1")
            conn.commit()
        repeat = optional_external_history_backfill(self.root, fetch=self.fetch)
        self.assertEqual(repeat["new_unverified_evidence_revisions"], 0)
        self.assertEqual(inspect_external_history(self.root)["indexed_evidence_revisions"], 100)


if __name__ == "__main__":
    unittest.main()
