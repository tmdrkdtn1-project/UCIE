"""Synthetic UCIE-only W04/SkillBook federated search regression."""
from __future__ import annotations

from http.server import HTTPServer
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from ucie_miner import skillbook_catalog_union_v01 as f
from ucie_miner.library_search import SCHEMA as W04_SCHEMA
from ucie_miner import skillbook_scandir_qa_v01 as qa
from ucie_miner import skillbook_w09_release_gate_v01 as w09
from ucie_miner import skillbook_consumer_pilot_v01 as pilot
from ucie_miner import library_browser_skillbook_v01 as browser
from ucie_miner import skillbook_product_v01 as product


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

    def test_product_funnel_catalog_to_real_manual_consumer_is_consistent(self):
        # One first-party integration acceptance. Existing HTTP tests validate
        # loopback GET routing; this checks the whole product contract without
        # opening a second HTTP server or triggering a live public W04 read.
        def no_public(*_args, **_kwargs):
            self.fail("SkillBook-only funnel must not access W04 or public API")
        catalog = f.search_federated(
            self.root, filters=self.filters(query="scandir"),
            public_reader=no_public)
        self.assertEqual(catalog["public_shelf_status"], "NOT_REQUESTED")
        self.assertEqual(catalog["public_evidence_candidates"], [])
        self.assertEqual(len(catalog["skillbooks"]), 1)
        item = catalog["skillbooks"][0]
        self.assertEqual(item["skillbook_id"], product.SKILLBOOK_ID)
        self.assertFalse(item["export_allowed"])

        # The user's link leads to the same draft, source and consumer
        # contract as the JSON route (HTTP route itself has separate tests).
        html = f.render_federated(catalog)
        self.assertIn('href="/skillbooks/' + product.SKILLBOOK_ID + '"', html)
        book = product.get_skillbook(item["skillbook_id"])
        chapter = browser.render_chapter(book)
        self.assertIn(
            'href="/skillbooks/' + product.SKILLBOOK_ID + '.json"', chapter)
        self.assertIn("ucie_miner.skillbook_consumer_pilot_v01", chapter)
        self.assertIn("--run-synthetic-demo", chapter)
        self.assertIn(product.SOURCE_DOCUMENT_SHA256, chapter)
        contract = book["machine_skill_contract"]
        self.assertEqual(
            contract["callable"],
            "ucie_miner.skillbook_scandir_recipe_v01.bounded_regular_file_names")
        self.assertEqual(book["consumer_pilot"]["manual_opt_in"],
                         "--run-synthetic-demo")
        self.assertFalse(contract["runtime_execution_by_catalog"])
        self.assertFalse(book["proof_gates"]["independent_test_verified"])
        self.assertFalse(book["proof_gates"]["security_review_approved"])
        self.assertFalse(book["proof_gates"]["license_redistribution_approved"])
        self.assertFalse(book["export_allowed"])

        # Browse/display does not execute the consumer: only the explicit
        # manual, UCIE-authored disposable recipe below does.
        with patch.object(
                pilot, "demonstrate_synthetic_consumer",
                side_effect=AssertionError("browser execution is forbidden")):
            self.assertIn("SkillBook", f.render_federated(catalog))
            self.assertIn("직접 실행하는 소비자 예제",
                          browser.render_chapter(book))
        actual = pilot.demonstrate_synthetic_consumer()
        self.assertEqual(actual["skillbook_id"], item["skillbook_id"])
        self.assertEqual(actual["source_document_sha256"],
                         item["source_document_sha256"])
        self.assertEqual(actual["status"], pilot.OBSERVED)
        self.assertEqual(actual["bounded_regular_file_names"],
                         ["alpha.txt", "zeta.txt"])
        self.assertEqual(actual["directory_entry_budget"], 3)
        self.assertTrue(actual["budget_overflow_blocked"])
        self.assertTrue(actual["temporary_fixture_cleaned"])
        self.assertFalse(actual["real_owner_directory_scanned"])
        self.assertFalse(actual["export_allowed"])
        self.assertFalse(actual["independent_qa_verified"])
        self.assertEqual(actual["network_requests"], 0)
        self.assertEqual(actual["operating_database_writes"], 0)

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
        self.assertEqual(len(result["skillbooks"]), 2)
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
        self.assertEqual(len(result["skillbooks"]), 2)
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

    def test_qa_plan_is_linked_and_never_runs_evaluation(self):
        handler = f.make_handler(self.root,
                                 public_reader=lambda *_a, **_kw:
                                 self.fail("unsolicited W04 query"))
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            thread = threading.Thread(target=server.serve_forever,
                                      kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            prefix = "http://127.0.0.1:" + str(server.server_port)
            def get(path, *, host=None):
                headers = {} if host is None else {"Host": host}
                req = Request(prefix + path, headers=headers)
                try:
                    with urlopen(req, timeout=5) as response:
                        return response.status, response.read().decode("utf-8")
                except HTTPError as error:
                    with error:
                        return error.code, error.read().decode("utf-8")
            try:
                with patch.object(
                        qa, "evaluate_skillbook_scandir",
                        side_effect=AssertionError("HTTP must not run QA")):
                    status, homepage = get("/")
                    self.assertEqual(status, 200)
                    status, skillbooks = get("/skillbooks")
                    self.assertEqual(status, 200)
                    self.assertIn('href="/skillbooks/qa-plan"', skillbooks)
                    status, chapter = get(
                        "/skillbooks/UCIE-SKILLBOOK-PY-SCANDIR-001")
                    self.assertEqual(status, 200)
                    self.assertIn('href="/skillbooks/qa-plan"', chapter)
                    status, page = get("/skillbooks/qa-plan")
                    self.assertEqual(status, 200)
                    self.assertIn("이 화면에서 미실행", page)
                    self.assertIn("9개", page)
                    self.assertNotIn("9/9 PASS", page)
                    status, raw = get("/skillbooks/qa-plan.json")
                    self.assertEqual(status, 200)
                    plan = json.loads(raw)
                    self.assertEqual(plan["case_count"], 9)
                    self.assertFalse(plan["qa_receipt_loaded"])
                    self.assertFalse(plan["browser_executes_tests"])
                    self.assertFalse(plan["export_allowed"])
                    self.assertEqual(
                        get("/skillbooks/qa-plan?test=run")[0], 400)
                    self.assertEqual(
                        get("/skillbooks/qa-plan", host="untrusted.invalid")[0],
                        403)
            finally:
                server.shutdown()
                thread.join(timeout=3)

    def test_w09_release_gate_is_linked_and_never_executes_qa(self):
        handler = f.make_handler(self.root,
                                 public_reader=lambda *_a, **_kw:
                                 self.fail("W09 triggered W04 read"))
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            thread = threading.Thread(target=server.serve_forever,
                                      kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            prefix = "http://127.0.0.1:" + str(server.server_port)

            def read(path, *, host=None):
                headers = {} if host is None else {"Host": host}
                request = Request(prefix + path, headers=headers)
                try:
                    with urlopen(request, timeout=5) as response:
                        return response.status, response.read().decode("utf-8")
                except HTTPError as error:
                    with error:
                        return error.code, error.read().decode("utf-8")
            try:
                with patch.object(qa, "evaluate_skillbook_scandir",
                                  side_effect=AssertionError("unsolicited W08")), \
                     patch.object(w09, "assess_release_readiness",
                                  side_effect=AssertionError("unsolicited W09")):
                    for entry in ("/catalog", "/skillbooks", "/skillbooks/qa-plan"):
                        status, html = read(entry)
                        self.assertEqual(status, 200)
                        self.assertIn('href="/skillbooks/release-gates"', html)
                    status, html = read("/skillbooks/release-gates")
                    self.assertEqual(status, 200)
                    self.assertIn("해결되어야 할 관문 6개", html)
                    self.assertIn("이 브라우저에서는 미조회", html)
                    self.assertNotIn("9/9 PASS", html)
                    status, raw = read("/skillbooks/release-gates.json")
                    self.assertEqual(status, 200)
                    preview = json.loads(raw)
                    self.assertEqual(preview["status"], w09.PREVIEW_STATE)
                    self.assertFalse(preview["receipt_validation_performed"])
                    self.assertFalse(preview["package_created"])
                    self.assertFalse(preview["export_allowed"])
                    self.assertEqual(len(preview["blocked_release_requirements"]), 6)
                    self.assertEqual(read(
                        "/skillbooks/release-gates?run=1")[0], 400)
                    self.assertEqual(read(
                        "/skillbooks/release-gates", host="evil.invalid")[0],
                        403)
            finally:
                server.shutdown()
                thread.join(timeout=3)

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
