"""Offline synthetic tests for bounded real public official-source transport."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from ucie_miner.public_discovery import SOURCES, DiscoveryError
from ucie_miner.public_evidence_routes import DOC_ENDPOINTS
from ucie_miner.public_official_evidence import (
    DB_NAME, OPT_IN_FILE, OPT_IN_TOKEN, official_urls,
    optional_official_evidence_cycle, inspect_official_sources,
    fetch_official_public, _release_rows, _advisory_rows,
)


def public_release():
    return {"id": 42, "tag_name": "v1.2.3",
            "published_at": "2026-09-01T10:00:00Z",
            "draft": False, "prerelease": False, "body": "INERT_UNTRUSTED_RELEASE_TEXT"}


def public_advisory():
    return {"ghsa_id": "GHSA-2222-3333-4444",
            "severity": "high", "state": "published",
            "published_at": "2026-09-02T08:00:00Z",
            "description": "INERT_UNTRUSTED_SECURITY_TEXT"}


class OfficialSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True)
        self.marker = self.runtime / OPT_IN_FILE
        self.calls = []
        self.operating = self.runtime / "public_miner.sqlite3"
        self.knowledge = self.runtime / "knowledge.sqlite3"
        self.operating.write_bytes(b"do not mutate existing miner DB")
        self.knowledge.write_bytes(b"do not mutate existing Knowledge DB")

    def enable(self):
        self.marker.write_text(OPT_IN_TOKEN, encoding="ascii")

    def fetch(self, url):
        self.calls.append(url)
        if "/releases?" in url:
            return json.dumps([public_release()]).encode("utf-8"), 40
        if "/security-advisories?" in url:
            return json.dumps([public_advisory()]).encode("utf-8"), 40
        if url in [v[0] for v in DOC_ENDPOINTS.values()]:
            return b"<html>Official reviewed document snapshot</html>", None
        raise AssertionError("unexpected URL")

    def test_missing_marker_never_makes_public_request_or_db(self):
        result = optional_official_evidence_cycle(
            self.root, fetch=lambda _: self.fail("unapproved GET"))
        self.assertEqual(result["status"], "STAGE14_OFFICIAL_DISABLED")
        self.assertFalse((self.runtime / DB_NAME).exists())

    def test_three_real_evidence_kinds_only_bounded_and_hash_only(self):
        self.enable()
        before = self.operating.read_bytes(), self.knowledge.read_bytes()
        result = optional_official_evidence_cycle(self.root, fetch=self.fetch)
        self.assertEqual(result["status"], "STAGE14_OFFICIAL_OBSERVED_NO_GO")
        self.assertEqual(result["source"], SOURCES[0])
        self.assertEqual(result["official_gets"], 3)
        self.assertEqual(result["new_metadata_revisions"], 3)
        self.assertEqual(len(self.calls), 3)
        snapshot = inspect_official_sources(self.root)
        self.assertEqual(snapshot["revisions"], 3)
        self.assertEqual(snapshot["next_selected_source"], SOURCES[1])
        self.assertEqual((self.operating.read_bytes(),
                          self.knowledge.read_bytes()), before)
        with closing(sqlite3.connect(self.runtime / DB_NAME)) as db:
            rows = db.execute("SELECT * FROM official_revision").fetchall()
        self.assertEqual({x[0] for x in rows}, {"release", "advisory", "document"})
        self.assertTrue(all(x[-1] == "PUBLIC_METADATA_UNVERIFIED" for x in rows))
        raw = str(rows)
        self.assertNotIn("INERT_UNTRUSTED", raw)
        self.assertNotIn("<html>", raw)
        self.assertFalse(result["production_approved"])

    def test_rotates_five_sources_and_idempotent_first_snapshot(self):
        self.enable()
        observations = []
        for _ in range(5):
            observations.append(optional_official_evidence_cycle(
                self.root, fetch=self.fetch))
        self.assertEqual([r["source"] for r in observations], list(SOURCES))
        self.assertEqual(sum(r["official_gets"] for r in observations), 15)
        self.assertEqual(inspect_official_sources(self.root)["revisions"], 15)
        repeat = optional_official_evidence_cycle(self.root, fetch=self.fetch)
        self.assertEqual(repeat["source"], SOURCES[0])
        self.assertEqual(repeat["official_gets"], 2)
        self.assertEqual(repeat["new_metadata_revisions"], 0)
        self.assertEqual(inspect_official_sources(self.root)["revisions"], 15)

    def test_stops_further_requests_when_rate_limit_is_low(self):
        self.enable()
        result = optional_official_evidence_cycle(
            self.root, fetch=lambda url: (
                json.dumps([public_release()]).encode(), 5))
        self.assertEqual(result["status"], "STAGE14_OFFICIAL_RATE_PAUSED_NO_GO")
        self.assertEqual(result["official_gets"], 1)
        self.assertEqual(result["new_metadata_revisions"], 1)

    def test_unavailable_security_does_not_claim_its_success(self):
        self.enable()
        def partial(url):
            if "/security-advisories?" in url:
                raise DiscoveryError("no public GHSA available")
            return self.fetch(url)
        result = optional_official_evidence_cycle(self.root, fetch=partial)
        self.assertEqual(result["status"], "STAGE14_OFFICIAL_PARTIAL_NO_GO")
        self.assertEqual(result["unavailable_evidence_kinds"], ["advisory"])
        self.assertEqual(result["official_gets"], 2)
        self.assertEqual(inspect_official_sources(self.root)["revisions"], 2)

    def test_unknown_published_security_id_and_private_draft_rejected(self):
        with self.assertRaises(DiscoveryError):
            _advisory_rows(SOURCES[0], json.dumps([{
                **public_advisory(), "ghsa_id": "secret-not-a-GHSA"}]).encode())
        self.assertEqual(_release_rows(SOURCES[0], json.dumps([{
            **public_release(), "draft": True}]).encode()), [])

    def test_authorized_route_only(self):
        with self.assertRaises(DiscoveryError):
            official_urls("unapproved/private", 1)
        with self.assertRaises(DiscoveryError):
            fetch_official_public("https://api.github.com/user/repos")
        self.assertEqual(self.calls, [])

    def test_refuse_wrong_marker_without_write(self):
        self.marker.write_text("AUTO_MODEL_TRAIN_AND_DEPLOY", encoding="ascii")
        with self.assertRaises(DiscoveryError):
            optional_official_evidence_cycle(
                self.root, fetch=lambda _: self.fail("no fetch"))
        self.assertFalse((self.runtime / DB_NAME).exists())

    def test_fake_sqlite_and_triggers_refused(self):
        self.enable()
        with closing(sqlite3.connect(self.runtime / DB_NAME)) as db:
            db.execute("CREATE TABLE suspicious(payload TEXT)")
            db.commit()
        with self.assertRaises(DiscoveryError):
            optional_official_evidence_cycle(
                self.root, fetch=lambda _: self.fail("no fetch"))

    def test_bad_untrusted_json_does_not_retain_source_text(self):
        self.enable()
        def garbage(url):
            if "/releases?" in url:
                return b'[{"body":"execute me"}]', 42
            return self.fetch(url)
        result = optional_official_evidence_cycle(self.root, fetch=garbage)
        self.assertEqual(result["status"], "STAGE14_OFFICIAL_PARTIAL_NO_GO")
        self.assertIn("release", result["unavailable_evidence_kinds"])
        inventory = inspect_official_sources(self.root)
        self.assertEqual(inventory["revisions"], 2)


if __name__ == "__main__":
    unittest.main()
