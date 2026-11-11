"""UCIE W03/W04 real Local V04 library cross-shelf UI and loopback QA.

Synthetic source-linked W04 report is injected; no operating database,
external GET, customer data, upstream code, scheduler or C40 is touched.
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
from ucie_miner import library_python_recipe_shelf_v01 as shelf
from ucie_miner import python_scandir_review_v01 as review
from ucie_miner.library_search import SCHEMA as W04_SCHEMA
from ucie_miner.skillbook_catalog_union_v01 import SCHEMA as FEDERATED_SCHEMA


def catalog():
    return {
        "schema": FEDERATED_SCHEMA,
        "status": "READ_ONLY_TWO_SHELF_DRAFT_NOT_APPROVED",
        "public_shelf_status": "NOT_REQUESTED",
        "public_evidence_candidates": [],
        "human_approved": False, "export_allowed": False,
        "approved_packages": 0,
        "network_requests": 0, "operating_database_writes": 0,
        "skillbooks": [], "editorial_review_candidates": [],
    }


def pr():
    return {
        "library_item_id": "a" * 64,
        "purpose_code": "PY_SCANDIR_SHARED_ITERATOR_RACE",
        "source_id": "repo:python/cpython",
        "public_url": "https://github.com/python/cpython/pull/155365",
        "domain": "Python",
        "kind": "PREVENTION_RULE",
        "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
        "human_approved": False, "export_allowed": False,
        "evidence_sha256": "b" * 64,
        "version_scope_claim": "UNDETERMINED",
    }


def public(*, rows=None, status="READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
           total=None, offset=0):
    rows = [pr()] if rows is None else rows
    record = {
        "schema": W04_SCHEMA,
        "status": status,
        "items": rows, "returned_count": len(rows),
        "total_matches": len(rows) if total is None else total,
        "network_requests": 0,
        "operating_database_writes": 0,
        "approved_or_exportable_items": 0,
        "auto_promoted": False,
    }
    if offset:
        record["page_offset"] = offset
    return record


class UCIEW03W04LocalFlowTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("UCIE")

    def _library(self, query: str, report=None):
        if report is None:
            report = public()
        with patch("ucie_miner.skillbook_catalog_union_v01.search_federated",
                   return_value=catalog()), \
                patch.object(app, "_search", return_value=report) as read:
            html = app._library(self.root, query)
        return html, read

    def test_one_python_search_shows_official_recipe_and_distinct_pr(self):
        html, read = self._library("q=Python")
        read.assert_called_once_with(
            self.root, "Python", limit=10, offset=0)
        self.assertIn('data-shelf="ucie-first-party-recipes"', html)
        self.assertIn("Python os.scandir", html)
        self.assertIn("TEST_RECIPE · 미승인", html)
        self.assertIn("doc:python/cpython", html)
        self.assertIn("PUBLIC_DOCUMENT_REVISION_NOT_PINNED", html)
        self.assertIn("UCIE_REFERENCE_STRING_ONLY_NOT_DOCUMENT_BYTES", html)
        self.assertIn("NOT_ATTESTED_PER_REVISION", html)
        self.assertIn("/local/engine?purpose=PYTHON_SCANDIR_SAFE", html)
        self.assertIn("https://docs.python.org/3/library/os.html", html)
        self.assertIn("https://github.com/python/cpython/pull/155365", html)
        self.assertIn("별도 PR 후보 1건", html)
        self.assertIn("서로 다른 근거", html)
        self.assertIn("개선 방향 살펴보기", html)
        self.assertNotIn("CUSTOMER_RELEASE_GO", html)

    def test_other_domain_search_does_not_forge_python_recipe(self):
        html, reader = self._library("q=Git", public(rows=[]))
        reader.assert_called_once()
        self.assertNotIn('data-shelf="ucie-first-party-recipes"', html)
        self.assertNotIn("TEST_RECIPE · 미승인", html)
        self.assertIn("공개 기술 사례", html)

    def test_korean_query_shows_recipe_without_accessing_public_ledger(self):
        query = "q=" + quote("스레드", safe="")
        with patch("ucie_miner.skillbook_catalog_union_v01.search_federated",
                   return_value=catalog()), \
                patch.object(app, "_search",
                             side_effect=AssertionError("no W04 call")) as reader:
            html = app._library(self.root, query)
        reader.assert_not_called()
        self.assertIn("TEST_RECIPE · 미승인", html)
        self.assertIn("공개 기술 사례는 현재 영문 검색어", html)
        self.assertIn("https://docs.python.org/3/library/os.html", html)
        self.assertNotIn("관련 공개 PR 후보 보기", html)

    def test_incomplete_w04_keeps_doc_candidate_unapproved(self):
        data = public(rows=[], status="SOURCE_LINKAGE_INCOMPLETE_NO_GO")
        html, reader = self._library("q=Python", data)
        reader.assert_called_once()
        self.assertIn("TEST_RECIPE · 미승인", html)
        self.assertIn("출처 연결이 불완전", html)
        self.assertIn("비교를 보류", html)
        self.assertNotIn("별도 PR 후보 1건", html)

    def test_forged_w04_approval_or_url_rejected_even_if_mocked(self):
        for field, value in (
            ("human_approved", True),
            ("export_allowed", True),
            ("lifecycle", "APPROVED"),
            ("public_url", "https://private.invalid/secret"),
        ):
            with self.subTest(field=field):
                row = pr()
                row[field] = value
                with self.assertRaises((app.LocalProductError,
                                        shelf.PythonRecipeShelfError)):
                    self._library("q=Python", public(rows=[row]))

    def test_paging_uses_one_exact_w04_page_and_compares_bounded_items(self):
        page = public(rows=[pr()], total=25, offset=10)
        html, reader = self._library("q=Python&page=2", page)
        reader.assert_called_once_with(
            self.root, "Python", limit=10, offset=10)
        self.assertIn("별도 PR 후보 1건", html)
        self.assertIn("11–11건 표시", html)
        self.assertIn("이전 10건", html)
        self.assertIn("다음 10건", html)

    def test_search_never_runs_the_concurrency_trial_or_downloads_docs(self):
        with patch.object(
                review, "_evaluate_only_ucie_synthetic_inputs",
                side_effect=AssertionError("trial cannot execute on search")
        ) as probe:
            html, _ = self._library("q=Python")
            self.assertIn("합성시험 확인", html)
            probe.assert_not_called()

    def test_ephemeral_local_http_get_and_denied_post(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / ".git").is_dir():
            self.skipTest("requires isolated UCIE checkout")
        with patch("ucie_miner.skillbook_catalog_union_v01.search_federated",
                   return_value=catalog()), \
                patch.object(app, "_search", return_value=public()):
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0), app.make_handler(root))
            server.daemon_threads = True
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                def fetch(method: str, route: str):
                    with closing(HTTPConnection(
                        "127.0.0.1", server.server_port, timeout=10)) as conn:
                        conn.request(method, route)
                        resp = conn.getresponse()
                        data = resp.read(700_000)
                        return resp.status, data
                code, body = fetch("GET", "/local/library?q=Python")
                self.assertEqual(code, 200)
                self.assertIn("TEST_RECIPE".encode(), body)
                self.assertIn(b"https://docs.python.org/3/library/os.html",
                              body)
                self.assertIn(b"github.com/python/cpython/pull/155365", body)
                code, _ = fetch("POST", "/local/library?q=Python")
                self.assertEqual(code, 405)
                code, _ = fetch("GET", "/local/library?q=%3Cscript%3E")
                self.assertEqual(code, 400)
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
