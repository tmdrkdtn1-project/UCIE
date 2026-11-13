"""Actual Local V1 offline official-reference user flow without any runtime DB.

All tests use a disposable UCIE-only checkout-like root and a bound 127.0.0.1
port. No operating SQLite inspection, network fetch, code from other projects,
vendor execution, source promotion or customer distribution.
"""
from __future__ import annotations

import http.client
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest

from ucie_miner import local_v1_app_v01 as local
from ucie_miner import local_portable_official_reference_v01 as portable


class PortableOfficialReferenceContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_PORTABLE_REF_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / ".git").mkdir(parents=True)

    def test_no_ledger_returns_unknown_not_fabricated_zero_results(self):
        self.assertTrue(portable.reference_only(self.root))
        data = portable.no_captured_public_candidates(
            query="Python", source_id=None, limit=10, offset=0)
        self.assertEqual(data["status"], "SOURCE_LINKAGE_INCOMPLETE_NO_GO")
        self.assertEqual(data["portable_reference_mode"], portable.STATUS)
        self.assertEqual(data["total_matches"], 0)
        self.assertEqual(data["items"], [])
        self.assertFalse(data["v1_library_accepted"])
        self.assertEqual(data["approved_or_exportable_items"], 0)
        inventory = portable.no_captured_inventory()
        self.assertIsNone(inventory["legacy_miner"]["candidates"])
        self.assertIsNone(
            inventory["stage10_public_candidate_staging"]["candidate_revisions"])
        self.assertEqual(inventory["operating_database_writes"], 0)
        self.assertFalse(inventory["customer_distribution_authorized"])

    def test_empty_runtime_directory_is_equivalent_to_absent(self):
        (self.root / "runtime").mkdir()
        self.assertTrue(portable.reference_only(self.root))
        self.assertEqual(list((self.root / "runtime").iterdir()), [])

    def test_unexpected_runtime_artifact_is_never_treated_as_empty(self):
        runtime = self.root / "runtime"
        runtime.mkdir()
        (runtime / "unexpected_ledger.sqlite3").write_bytes(
            b"UCIE inert synthetic non-SQLite file")
        self.assertFalse(portable.reference_only(self.root))

    def test_symlink_or_other_project_root_denied(self):
        other = Path(self.tmp.name) / "OTHER"
        (other / ".git").mkdir(parents=True)
        with self.assertRaises(portable.PortableReferenceError):
            portable.reference_only(other)
        for q in ("../x", "x&admin=true"):
            with self.subTest(q=q), self.assertRaises(ValueError):
                portable.no_captured_public_candidates(
                    query=q, source_id=None, limit=10, offset=0)

    def test_unapproved_source_and_paging_refused(self):
        with self.assertRaises(ValueError):
            portable.no_captured_public_candidates(
                query="Git", source_id="repo:OTHER/NOT_ALLOWED",
                limit=10, offset=0)
        with self.assertRaises(portable.PortableReferenceError):
            portable.no_captured_public_candidates(
                query="Git", source_id=None, limit=10, offset=10)
        with self.assertRaises(ValueError):
            portable.no_captured_public_candidates(
                query="Git", source_id=None, limit=99999, offset=0)


class PortableOfficialReferenceRealHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_CLEAN_FIRST_PARTY_GET_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / ".git").mkdir(parents=True)
        self.server = HTTPServer(("127.0.0.1", 0), local.make_handler(self.root))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.thread.join, 3)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, path, *, method="GET", host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port,
                                          timeout=6)
        try:
            conn.request(method, path, headers={
                "Host": host or "127.0.0.1:" + str(self.server.server_port),
            })
            res = conn.getresponse()
            return res.status, res.read().decode("utf-8", "replace"), dict(
                res.getheaders())
        finally:
            conn.close()

    def test_clean_recipient_can_browse_official_sources_in_two_real_routes(self):
        exact = (
            ("Python", "Python os.scandir", "docs.python.org"),
            ("PowerShell", "Resolve-Path", "learn.microsoft.com"),
            ("Git", "Git 명령", "git-scm.com"),
            ("MCP", "MCP 프로토콜", "modelcontextprotocol.io"),
        )
        for route in ("/local/library", "/local/evolution"):
            for word, term, domain in exact:
                with self.subTest(route=route, word=word):
                    status, page, headers = self.request(route + "?q=" + word)
                    self.assertEqual(status, 200, page[:200])
                    self.assertIn('data-offline-reference-only="true"', page)
                    self.assertIn(portable.NOTE, page)
                    self.assertIn(term, page)
                    self.assertIn(domain, page)
                    self.assertIn("UNVERIFIED_CANDIDATE_ONLY", page)
                    self.assertEqual(headers["Cache-Control"], "no-store")
                    self.assertIn("default-src 'none'",
                                  headers["Content-Security-Policy"])
        self.assertFalse((self.root / "runtime").exists())

    def test_existing_first_party_skillbook_routes_and_b2_links_still_work(self):
        paths = (
            "/local/library?q=Python",
            "/local/library?q=Git",
            "/local/engine?purpose=B2_CONNECTED_TRIAGE&case=git-repository",
            "/local/error?case=git-repository",
        )
        for path in paths:
            with self.subTest(path=path):
                status, body, _ = self.request(path)
                self.assertEqual(status, 200, path + ": " + body[:100])
        status, page, _ = self.request("/local/library?q=Git")
        self.assertEqual(status, 200)
        self.assertIn("가이드", page)

    def test_no_new_pages_post_or_forged_origin_and_invalid_source(self):
        for path, method, host, expected in (
            ("/local/library?q=Git", "POST", None, 405),
            ("/local/evolution?q=MCP", "POST", None, 405),
            ("/local/library?q=Git", "GET", "evil.example", 403),
            ("/local/library?q=Git&source=other/repo", "GET", None, 400),
            ("/local/library?q=Git&page=2", "GET", None, 400),
            ("/local/evolution?q=Python&from=../OTHER", "GET", None, 400),
            ("/local/library?q=Git&q=MCP", "GET", None, 400),
        ):
            with self.subTest(path=path, expected=expected):
                status, _, _ = self.request(path, method=method, host=host)
                self.assertEqual(status, expected)

    def test_existing_unexpected_artifact_must_not_be_called_offline_mode(self):
        runtime = self.root / "runtime"
        runtime.mkdir()
        (runtime / "existing_unknown.bin").write_bytes(b"UCIE inert")
        status, page, _ = self.request("/local/evolution?q=Git")
        self.assertNotIn('data-offline-reference-only="true"', page)
        self.assertNotEqual(status, 200)  # original ledger path fails closed


if __name__ == "__main__":
    unittest.main()
