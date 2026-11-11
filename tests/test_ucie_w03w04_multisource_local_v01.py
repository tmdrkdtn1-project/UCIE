"""UCIE W03/W04 owner Local V04: five approved sources, distinct public evidence.

All public W04 results are injected first-party test fixtures. The sole
HTTP listener is ephemeral loopback. No other-project or operating-data IO.
"""
from __future__ import annotations

from contextlib import closing
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import quote
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import python_scandir_review_v01 as trial
from ucie_miner.library_search import SCHEMA as W04_SCHEMA
from ucie_miner.product_plan import APPROVED_REPOSITORIES
from ucie_miner.skillbook_catalog_union_v01 import SCHEMA as UNION_SCHEMA


def catalog():
    return {
        "schema": UNION_SCHEMA,
        "status": "READ_ONLY_TWO_SHELF_DRAFT_NOT_APPROVED",
        "public_shelf_status": "NOT_REQUESTED",
        "public_evidence_candidates": [],
        "human_approved": False, "export_allowed": False,
        "approved_packages": 0, "network_requests": 0,
        "operating_database_writes": 0,
        "skillbooks": [], "editorial_review_candidates": [],
    }


def record(repo="git/git"):
    return {
        "library_item_id": "a" * 64,
        "review_candidate_sha256": "b" * 64,
        "source_id": "repo:" + repo,
        "kind": "PUBLIC_TECHNICAL_EVIDENCE",
        "public_url": "https://github.com/" + repo +
                      ("/commit/" + "c" * 40 if repo == "git/git"
                       else "/pull/12345"),
        "domain": "Git" if repo == "git/git" else "PowerShell",
        "purpose_code": "SAFE_REVIEW_REFERENCE",
        "version_scope_claim": "UNDETERMINED",
        "evidence_sha256": "d" * 64,
        "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
        "human_approved": False, "export_allowed": False,
    }


def w04(items=None, *, status="READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
        count=None, page_offset=None):
    rows = [] if items is None else items
    doc = {
        "schema": W04_SCHEMA,
        "status": status, "items": rows,
        "total_matches": len(rows) if count is None else count,
        "returned_count": len(rows),
        "network_requests": 0, "operating_database_writes": 0,
        "approved_or_exportable_items": 0, "auto_promoted": False,
    }
    if page_offset is not None:
        doc["page_offset"] = page_offset
    return doc


class UCIEW03W04FiveSourceLocalTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("UCIE")

    def view(self, url="", report=None):
        data = w04() if report is None else report
        with patch("ucie_miner.skillbook_catalog_union_v01.search_federated",
                   return_value=catalog()), \
                patch.object(app, "_search", return_value=data) as read:
            rendered = app._library(self.root, url)
        return rendered, read

    def test_all_five_approved_source_options_and_all_reference_cards(self):
        html, read = self.view("")
        read.assert_called_once_with(self.root, "", limit=10, offset=0)
        for repo in APPROVED_REPOSITORIES:
            self.assertIn('<option value="' + repo + '"', html)
        for target in (
            "https://docs.python.org/3/library/os.html",
            "https://learn.microsoft.com/en-us/powershell/",
            "https://git-scm.com/docs/git",
            "https://modelcontextprotocol.io/specification/2025-11-25",
            "https://docs.github.com/en/actions/reference/runners",
        ):
            self.assertIn(target, html)
        self.assertIn("TEST_RECIPE · 미승인", html)
        self.assertEqual(html.count("OFFICIAL DOC · 검토 전"), 4)
        self.assertIn("출처 선택은 공식 문서와 공개 변경 자료에만", html)
        self.assertIn("PUBLIC_DOCUMENT_REVISION_NOT_PINNED", html)
        self.assertIn("NOT_ATTESTED_PER_REVISION", html)
        self.assertNotIn("CUSTOMER_RELEASE_GO", html)

    def test_each_repo_filters_only_one_metadata_source_or_python_recipe(self):
        for repo in APPROVED_REPOSITORIES:
            with self.subTest(repo=repo):
                source = quote(repo, safe="")
                html, reader = self.view("q=&source=" + source)
                reader.assert_called_once_with(
                    self.root, "", limit=10, offset=0,
                    source_id="repo:" + repo)
                self.assertIn('<option value="' + repo + '" selected>', html)
                if repo == "python/cpython":
                    self.assertIn("TEST_RECIPE · 미승인", html)
                    self.assertNotIn("OFFICIAL DOC · 검토 전", html)
                else:
                    self.assertNotIn("TEST_RECIPE · 미승인", html)
                    self.assertEqual(html.count("OFFICIAL DOC · 검토 전"), 1)
                    self.assertIn("doc:" + repo, html)

    def test_multi_domain_term_search_not_promoted_as_skill(self):
        for term, expected in (
            ("PowerShell", "Resolve-Path"),
            ("Git", "Git 명령"),
            ("MCP", "MCP 프로토콜 사양"),
            ("runner", "GitHub Actions 러너"),
        ):
            with self.subTest(term=term):
                html, _reader = self.view("q=" + quote(term, safe=""))
                self.assertIn(expected, html)
                self.assertIn("검토 전", html)
                self.assertIn("UNDETERMINED", html)

    def test_same_approved_repo_candidate_link_keeps_source_bound_review(self):
        html, reader = self.view(
            "q=Git&source=git%2Fgit", w04([record("git/git")]))
        reader.assert_called_once_with(
            self.root, "Git", limit=10, offset=0,
            source_id="repo:git/git")
        self.assertIn("같은 승인 저장소의 후보 1건", html)
        self.assertIn("동일 문제·수정 효과는", html)
        self.assertIn("github.com/git/git/commit/", html)
        self.assertIn("&amp;source=git%2Fgit", html)
        self.assertIn("UNVERIFIED_CANDIDATE_ONLY", html)

    def test_source_selected_paging_round_trip(self):
        html, reader = self.view(
            "q=PowerShell&page=2&source=PowerShell%2FPowerShell",
            w04([record("PowerShell/PowerShell")],
                count=24, page_offset=10))
        reader.assert_called_once_with(
            self.root, "PowerShell", limit=10, offset=10,
            source_id="repo:PowerShell/PowerShell")
        self.assertIn("11–11건 표시", html)
        self.assertIn("page=1&amp;source=PowerShell%2FPowerShell", html)
        self.assertIn("page=3&amp;source=PowerShell%2FPowerShell", html)
        self.assertIn("&amp;source=PowerShell%2FPowerShell", html)

    def test_review_lookup_reuses_selected_source_not_global_page(self):
        with patch.object(app, "_search",
                          return_value=w04(status="SOURCE_LINKAGE_INCOMPLETE_NO_GO")
                          ) as read:
            with self.assertRaises(app.LocalProductError):
                app._review(
                    self.root, "q=Git&page=1&id=" + "a" * 64 +
                    "&from=library&source=git%2Fgit")
            read.assert_called_once_with(
                self.root, "Git", limit=10, offset=0, source_id="repo:git/git")
        with self.assertRaises(app.LocalProductError):
            app._review(
                self.root, "q=Git&id=" + "a" * 64 +
                "&from=error&source=git%2Fgit")

    def test_korean_keyword_shows_official_doc_without_w04_public_query(self):
        with patch("ucie_miner.skillbook_catalog_union_v01.search_federated",
                   return_value=catalog()), \
                patch.object(app, "_search",
                             side_effect=AssertionError("W04 was requested")) as reader:
            html = app._library(
                self.root, "q=" + quote("러너") +
                "&source=actions%2Frunner-images")
        reader.assert_not_called()
        self.assertIn("GitHub Actions 러너", html)
        self.assertIn("OFFICIAL DOC · 검토 전", html)
        self.assertNotIn("TEST_RECIPE · 미승인", html)
        self.assertIn("공개 기술 사례는 현재 영문 검색어", html)

    def test_incomplete_w04_defers_comparison_for_all_sources(self):
        html, reader = self.view(
            "q=MCP&source=modelcontextprotocol%2Fpython-sdk",
            w04(status="SOURCE_LINKAGE_INCOMPLETE_NO_GO"))
        reader.assert_called_once()
        self.assertIn("MCP 프로토콜 사양", html)
        self.assertIn("출처 연결이 불완전하여 비교를 보류", html)
        self.assertNotIn("관련 공개 변경 후보 ↗", html)

    def test_unknown_or_tampered_source_rejected_before_public_search(self):
        for raw in (
            "q=Git&source=other%2Fprivate",
            "q=Git&source=research%3Aunapproved",
            "q=Git&source=repo%3Agit%2Fgit",
            "q=Git&source=Git%2Fgit",
            "q=Git&source=git%2Fgit&source=git%2Fgit",
            "q=Git&source=..%2Fprivate",
        ):
            with self.subTest(raw=raw), \
                 patch("ucie_miner.skillbook_catalog_union_v01.search_federated",
                       return_value=catalog()), \
                 patch.object(app, "_search",
                              side_effect=AssertionError("must not search")) as reader:
                with self.assertRaises(app.LocalProductError):
                    app._library(self.root, raw)
                reader.assert_not_called()

    def test_library_read_only_never_executes_python_trial(self):
        with patch.object(trial, "_evaluate_only_ucie_synthetic_inputs",
                          side_effect=AssertionError("trial must not run")) as run:
            html, _reader = self.view("q=Python")
            self.assertIn("TEST_RECIPE · 미승인", html)
            run.assert_not_called()

    def test_ephemeral_loopback_http_get_post_and_denied_unknown_filter(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / ".git").is_dir():
            self.skipTest("exact UCIE repo only")
        with patch("ucie_miner.skillbook_catalog_union_v01.search_federated",
                   return_value=catalog()), \
             patch.object(app, "_search", return_value=w04()):
            srv = ThreadingHTTPServer(
                ("127.0.0.1", 0), app.make_handler(root))
            srv.daemon_threads = True
            thread = Thread(target=srv.serve_forever, daemon=True)
            thread.start()
            try:
                def request(method, target):
                    with closing(HTTPConnection(
                        "127.0.0.1", srv.server_port, timeout=10)) as conn:
                        conn.request(method, target)
                        response = conn.getresponse()
                        return response.status, response.read(600000)
                code, data = request(
                    "GET", "/local/library?q=MCP&source=modelcontextprotocol%2Fpython-sdk")
                self.assertEqual(code, 200)
                self.assertIn(b"modelcontextprotocol.io/specification/", data)
                self.assertIn(b'name="source"', data)
                self.assertIn(b"NOT_ATTESTED_PER_REVISION", data)
                code, _ = request("POST", "/local/library?q=MCP")
                self.assertEqual(code, 405)
                code, _ = request(
                    "GET", "/local/library?q=Git&source=other%2Fprivate")
                self.assertEqual(code, 400)
                code, _ = request("GET", "/local/library?q=%3Cscript%3E")
                self.assertEqual(code, 400)
            finally:
                srv.shutdown()
                srv.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
