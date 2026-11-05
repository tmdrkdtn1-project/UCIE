"""Synthetic UCIE-only W04/SkillBook federated search regression."""
from __future__ import annotations

from http.server import HTTPServer
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from ucie_miner import skillbook_catalog_union_v01 as f
from ucie_miner.library_search import SCHEMA as W04_SCHEMA


def w04(state="READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO"):
    items = [{
        "library_item_id": "a" * 64,
        "source_id": "repo:python/cpython",
        "kind": "PUBLIC_TECHNICAL_EVIDENCE",
        "purpose_code": "PUBLIC_PYTHON_EVIDENCE",
        "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
        "human_approved": False, "export_allowed": False,
    }] if state == "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO" else []
    return {
        "schema": W04_SCHEMA, "status": state,
        "total_matches": len(items), "items": items,
        "network_requests": 0, "operating_database_writes": 0,
        "approved_or_exportable_items": 0, "auto_promoted": False,
    }


class FederatedReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("/synthetic/ucie")

    def filters(self, **changes):
        return dict(f.parse_filters(""), **changes)

    def test_default_no_w04_read(self):
        result = f.search_federated(
            self.root, filters=self.filters(query="scandir"),
            public_reader=lambda *_a, **_kw: self.fail("unexpected W04 read"))
        self.assertEqual(len(result["skillbooks"]), 1)
        self.assertEqual(result["public_shelf_status"], "NOT_REQUESTED")
        self.assertFalse(result["export_allowed"])
        self.assertTrue(result["distinct_evidence_units_not_joined"])

    def test_opt_in_w04_shelf_uses_original_reader_contract(self):
        calls = []
        def reader(root, **kwargs):
            calls.append(kwargs)
            return w04()
        result = f.search_federated(
            self.root, filters=self.filters(shelf="all", query="Python"),
            public_reader=reader)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["query"], "Python")
        self.assertEqual(len(result["skillbooks"]), 1)
        self.assertEqual(len(result["public_evidence_candidates"]), 1)
        self.assertEqual(result["public_candidate_total"], 1)
        self.assertFalse(result["legacy_sqlite_index_migrated"])

    def test_incomplete_w04_never_looks_like_zero_matches(self):
        result = f.search_federated(
            self.root, filters=self.filters(shelf="all"),
            public_reader=lambda *_a, **_kw: w04(
                "SOURCE_LINKAGE_INCOMPLETE_NO_GO"))
        self.assertIsNone(result["public_candidate_total"])
        self.assertEqual(result["public_shelf_status"],
                         "SOURCE_LINKAGE_INCOMPLETE_NO_GO")

    def test_korean_skips_ascii_only_w04_without_false_results(self):
        result = f.search_federated(
            self.root, filters=self.filters(shelf="all", query="디렉터리"),
            public_reader=lambda *_a, **_kw: self.fail("unexpected W04 read"))
        self.assertEqual(len(result["skillbooks"]), 1)
        self.assertEqual(result["public_shelf_status"],
                         "W04_NONASCII_QUERY_NOT_SUPPORTED_NO_SEARCH")

    def test_kind_filter_skips_incompatible_shelf(self):
        result = f.search_federated(
            self.root, filters=self.filters(shelf="all", kind="REUSABLE_SKILL"),
            public_reader=lambda *_a, **_kw: self.fail("unexpected W04 read"))
        self.assertEqual(len(result["skillbooks"]), 1)
        self.assertEqual(result["public_shelf_status"], "NOT_REQUESTED")
        result = f.search_federated(
            self.root, filters=self.filters(shelf="all", kind="PREVENTION_RULE"),
            public_reader=lambda *_a, **_kw: w04("SOURCE_LINKAGE_INCOMPLETE_NO_GO"))
        self.assertEqual(result["skillbooks"], [])

    def test_python_domain_filter_retains_skillbook(self):
        result = f.search_federated(
            self.root, filters=self.filters(
                shelf="all", domain="Python", kind="REUSABLE_SKILL"),
            public_reader=lambda *_a, **_kw: self.fail("W04 read for SkillBook"))
        self.assertEqual(len(result["skillbooks"]), 1)
        self.assertEqual(result["public_shelf_status"], "NOT_REQUESTED")
        other = f.search_federated(
            self.root, filters=self.filters(
                shelf="all", domain="MCP/API", kind="REUSABLE_SKILL"),
            public_reader=lambda *_a, **_kw: self.fail("W04 read for SkillBook"))
        self.assertEqual(other["skillbooks"], [])

    def test_bad_query_and_parameter_rejected(self):
        for query in ("q=%3Cscript%3E", "q=a&q=b", "shelf=private",
                      "limit=1000", "kind=PUBLISHED", "domain=UNKNOWN",
                      "q=" + "x" * 81, "q=%ZZ", "source=secret"):
            with self.subTest(query=query), self.assertRaises(f.FederationError):
                f.parse_filters(query)

    def test_forged_w04_approval_or_source_rejected(self):
        for mutation in (
                lambda row: row.update(human_approved=True),
                lambda row: row.update(export_allowed=True),
                lambda row: row.update(source_id="repo:unknown/unknown"),
                lambda row: row.update(library_item_id="../../private")):
            report = w04()
            mutation(report["items"][0])
            with self.assertRaises(f.FederationError):
                f.search_federated(
                    self.root, filters=self.filters(shelf="all"),
                    public_reader=lambda *_a, **_kw: report)

    def test_w04_write_or_approval_claim_rejected(self):
        for key, value in (("operating_database_writes", 1),
                           ("network_requests", 1),
                           ("approved_or_exportable_items", 1),
                           ("status", "APPROVED")):
            report = w04()
            report[key] = value
            with self.subTest(key=key), self.assertRaises(f.FederationError):
                f.search_federated(
                    self.root, filters=self.filters(shelf="all"),
                    public_reader=lambda *_a, **_kw: report)

    def test_html_maintains_separate_shelves(self):
        result = f.search_federated(
            self.root, filters=self.filters(shelf="all", query="Python"),
            public_reader=lambda *_a, **_kw: w04())
        html = f.render_federated(result)
        self.assertIn("SkillBook", html)
        self.assertIn("W04 공개", html)
        self.assertIn('href="/item/' + "a" * 64, html)
        self.assertIn('href="/skillbooks/', html)
        self.assertIn("자료 구분", html)
        self.assertIn("기존 W04 정렬순, 관련도 순위 아님", html)
        self.assertIn("후보 ID:", html)
        self.assertIn("UCIE 제작 초안", html)
        self.assertIn("미검증 공개 근거 검색 완료", html)
        self.assertIn(f.SCHEMA, html)

    def test_w04_status_distinguishes_no_read_from_incomplete(self):
        normal = f.search_federated(
            self.root, filters=self.filters(query="scandir"),
            public_reader=lambda *_a, **_kw: self.fail("W04 read without opt-in"))
        self.assertIn("검색하지 않음", f.render_federated(normal))
        incomplete = f.search_federated(
            self.root, filters=self.filters(shelf="public"),
            public_reader=lambda *_a, **_kw: w04(
                "SOURCE_LINKAGE_INCOMPLETE_NO_GO"))
        html = f.render_federated(incomplete)
        self.assertIn("출처 연결 미완료", html)
        self.assertNotIn("전체 일치 후보:", html)

    def test_untrusted_w04_metadata_is_html_escaped(self):
        report = w04()
        report["items"][0]["purpose_code"] = "<script>alert('x')</script>"
        report["items"][0]["revision_hint"] = 'pull/1\" onmouseover=\"alert(1)'
        result = f.search_federated(
            self.root, filters=self.filters(shelf="public"),
            public_reader=lambda *_a, **_kw: report)
        html = f.render_federated(result)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn('onmouseover="alert', html)
        self.assertIn("후보 ID:", html)

    def test_home_to_catalog_navigation_is_clickable(self):
        # The user must not need to type /catalog into the address bar.
        handler = f.make_handler(
            self.root,
            public_reader=lambda *_a, **_kw:
            self.fail("navigation attempted an unsolicited W04 read"),
            public_prober=lambda *_a, **_kw:
            self.fail("navigation attempted an unsolicited public GET"))
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            worker = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05}, daemon=True)
            worker.start()
            try:
                base = "http://127.0.0.1:" + str(server.server_port)

                def request(path):
                    with urlopen(base + path, timeout=5) as resp:
                        return resp.status, resp.read().decode("utf-8")

                for path in ("/", "/skillbooks", "/skillbooks/"
                             "UCIE-SKILLBOOK-PY-SCANDIR-001"):
                    with self.subTest(path=path):
                        status, html = request(path)
                        self.assertEqual(status, 200)
                        self.assertEqual(html.count('href="/catalog"'), 1)
                        self.assertIn("통합 도서관 열기", html)
                status, catalog = request("/catalog")
                self.assertEqual(status, 200)
                self.assertIn('href="/"', catalog)
                self.assertIn("W04 공개 근거 후보", catalog)
                status, data = request("/catalog.json")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(data)["public_shelf_status"],
                                 "NOT_REQUESTED")
                self.assertNotIn("<nav", data)
            finally:
                server.shutdown()
                worker.join(timeout=3)

    def test_loopback_http_routes_and_default_no_database(self):
        reads = []
        def reader(root, **kwargs):
            reads.append(kwargs)
            return w04()
        handler = f.make_handler(self.root, public_reader=reader,
                                 public_prober=lambda *_a, **_kw:
                                 self.fail("unexpected public GET"))
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            worker = threading.Thread(target=server.serve_forever,
                                      kwargs={"poll_interval": 0.05}, daemon=True)
            worker.start()
            try:
                prefix = "http://127.0.0.1:" + str(server.server_port)
                def read(path, headers=None):
                    req = Request(prefix + path, headers=headers or {})
                    try:
                        with urlopen(req, timeout=5) as response:
                            return response.status, response.read().decode("utf-8")
                    except HTTPError as error:
                        with error:
                            return error.code, error.read().decode("utf-8")
                status, html = read("/catalog")
                self.assertEqual(status, 200)
                self.assertIn("SkillBook", html)
                self.assertEqual(reads, [])
                status, raw = read("/catalog.json?shelf=all&q=Python")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(raw)["public_candidate_total"], 1)
                self.assertEqual(len(reads), 1)
                self.assertEqual(read("/catalog?q=%3Cscript%3E")[0], 400)
                self.assertEqual(read("/catalog", {"Host": "other.example"})[0], 403)
                self.assertEqual(read("/skillbooks")[0], 200)
                self.assertEqual(read("/")[0], 200)
                status, raw = read("/catalog.json?shelf=all&q="
                                   + quote("디렉터리"))
                self.assertEqual(status, 200)
                self.assertIsNone(json.loads(raw)["public_candidate_total"])
                self.assertEqual(len(reads), 1)
                print("UCIE_FEDERATED_HTTP={\"catalog\":200,\"json\":200,"
                      "\"bad_query\":400,\"bad_host\":403,\"default_w04_reads\":0}")
            finally:
                server.shutdown()
                worker.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
