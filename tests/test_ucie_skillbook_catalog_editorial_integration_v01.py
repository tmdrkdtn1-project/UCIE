"""UCIE actual local HTTP browse -> pending authoring review -> side-by-side compare.

Only source-registry-approved routes and UCIE synthetic data. No external
fetch, operating DB write, upload, export, auto approval or skill execution.
"""
from __future__ import annotations

from copy import deepcopy
from http.server import HTTPServer
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from ucie_miner import skillbook_catalog_union_v01 as catalog
from ucie_miner import skillbook_editorial_production_v01 as editor
from ucie_miner.source_registry import get_source


class EditorialCatalogIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("/UCIE_SYTHETIC_NO_EXISTING_OWNER_TREE")
        self.pilot = editor.compose_curated_two_book_pilot()
        self.record = deepcopy(self.pilot["authoring_input"])

    def test_real_catalog_can_find_pending_skillbook_without_w04(self):
        def forbidden(*_a, **_kw):
            self.fail("read-only SkillBook catalog unexpectedly reads W04/DB")
        for term in ("BOUNDED_METADATA", "scandir", "Git", "원리"):
            with self.subTest(term=term):
                report = catalog.search_federated(
                    self.root, filters=dict(catalog.parse_filters(""), query=term),
                    public_reader=forbidden)
                self.assertEqual(report["public_shelf_status"], "NOT_REQUESTED")
                self.assertEqual(len(report["editorial_review_candidates"]), 1)
                row = report["editorial_review_candidates"][0]
                self.assertEqual(row["draft_sha256"], self.pilot["draft_sha256"])
                self.assertEqual(row["chapter_count"], 5)
                self.assertEqual(row["source_ids"],
                                 ["doc:git/git", "doc:python/cpython"])
                self.assertFalse(row["machine_contract_implemented"])
                self.assertFalse(row["human_approved"])
                self.assertFalse(row["export_allowed"])
                self.assertTrue(report["editorial_candidates_unapproved"])

    def test_separate_approved_public_candidate_shelf_unmodified(self):
        report = catalog.search_federated(
            self.root, filters=dict(catalog.parse_filters(""), shelf="public"),
            public_reader=lambda *_a, **_kw: {
                "schema": "UCIE_W04_READ_ONLY_LIBRARY_CANDIDATE_SEARCH_V1",
                "status": "SOURCE_LINKAGE_INCOMPLETE_NO_GO",
                "items": [], "network_requests": 0,
                "operating_database_writes": 0, "approved_or_exportable_items": 0,
                "auto_promoted": False,
            })
        self.assertEqual(report["editorial_review_candidates"], [])
        self.assertEqual(report["public_evidence_candidates"], [])
        self.assertIsNone(report["public_candidate_total"])
        self.assertFalse(report["export_allowed"])

    def test_select_produces_real_two_book_comparison_and_review(self):
        view = catalog.inspect_review_candidate(self.pilot["draft_sha256"])
        self.assertEqual(view["status"], catalog.REVIEW_STATUS)
        self.assertEqual(view["candidate"], self.pilot)
        self.assertEqual(len(view["comparison"]), 3)
        books = view["comparison"][:2]
        pending = view["comparison"][2]
        self.assertTrue(all(b["asset_type"] == "EXISTING_UCIE_AUTHORED_BOOK_DRAFT"
                            for b in books))
        self.assertTrue(all(b["chapter_count"] == 4 for b in books))
        self.assertTrue(all(b["machine_contract"] ==
                            "FIRST_PARTY_RECIPE_EXISTS_NOT_RELEASED" for b in books))
        self.assertEqual(pending["item_id"], self.pilot["draft_sha256"])
        self.assertEqual(pending["chapter_count"], 5)
        self.assertEqual(pending["machine_contract"], "DESIGN_ONLY_NO_EXECUTABLE")
        self.assertFalse(view["source_content_independently_verified"])
        self.assertFalse(view["manual_editorial_review_completed"])
        self.assertFalse(view["machine_contract_executed"])
        self.assertEqual(view["approved_items"], 0)
        self.assertFalse(view["export_allowed"])
        self.assertEqual(view["network_requests"], 0)
        self.assertEqual(view["operating_database_writes"], 0)
        human = catalog.render_review_candidate(view)
        self.assertIn("기존 실행형 기술서적과 후보 비교", human)
        self.assertIn("사람이 검토할 5개 기술 챕터", human)
        self.assertIn("작동 원리와 공식 근거", human)
        self.assertIn("미승인", human)
        self.assertIn("PENDING", human)
        self.assertIn(self.pilot["draft_sha256"], human)
        self.assertIn('href="/catalog/review.json?id=', human)

    def test_catalog_search_link_opens_same_revision_id(self):
        filters = dict(catalog.parse_filters(""), query="BOUNDED_METADATA")
        report = catalog.search_federated(self.root, filters=filters,
                                           public_reader=lambda *_a, **_kw:
                                           self.fail("W04 read forbidden"))
        html = catalog.render_federated(report)
        self.assertIn('/catalog/review?id=' + self.pilot["draft_sha256"], html)
        self.assertIn("기술 본문/원문 미검증", html)
        self.assertIn('href="/skillbooks/', html)
        self.assertIn("W04 공개 근거 후보", html)

    def test_registered_powershell_synthetic_candidate_can_be_browsed(self):
        record = deepcopy(self.record)
        doc = get_source("doc:PowerShell/PowerShell")
        record["sources"] = [{
            "kind": "REUSABLE_SKILL",
            "source_id": "doc:PowerShell/PowerShell",
            "evidence_reference": doc["public_url"],
            "evidence_sha256": "a" * 64,  # UNVERIFIED synthetic test input
            "purpose_code": "POWERSHELL_SYNTHETIC_REVIEW",
            "version_scope": "PWSH_7_6",
            "dependencies": ["pwsh"],
        }]
        record["topic"] = "POWERSHELL_EDITORIAL_REVIEW"
        for ch in record["chapters"]:
            ch["source_ids"] = ["doc:PowerShell/PowerShell"]
        item = editor.compile_review_draft(record)
        r = catalog.search_federated(
            self.root,
            filters=dict(catalog.parse_filters(""), query="POWERSHELL",
                         domain="PowerShell"),
            public_reader=lambda *_a, **_kw: self.fail("unexpected W04"),
            editorial_records=(record,))
        self.assertEqual(len(r["editorial_review_candidates"]), 1)
        self.assertEqual(r["editorial_review_candidates"][0]["draft_sha256"],
                         item["draft_sha256"])
        d = catalog.inspect_review_candidate(
            item["draft_sha256"], editorial_records=(record,))
        self.assertEqual(d["candidate"]["sources"][0]["evidence_sha256"], "a" * 64)
        self.assertFalse(d["source_content_independently_verified"])
        self.assertFalse(d["candidate"]["human_approved"])
        self.assertEqual(d["comparison"][-1]["machine_contract"],
                         "DESIGN_ONLY_NO_EXECUTABLE")

    def test_wrong_domain_or_kind_filters_do_not_leak_candidate(self):
        filters = dict(catalog.parse_filters(""), domain="Windows")
        result = catalog.search_federated(
            self.root, filters=filters,
            public_reader=lambda *_a, **_kw: self.fail("wrong W04 path"))
        self.assertEqual(result["editorial_review_candidates"], [])
        result = catalog.search_federated(
            self.root, filters=dict(catalog.parse_filters(""),
                                    kind="PREVENTION_RULE"),
            public_reader=lambda *_a, **_kw: self.fail("wrong W04 path"))
        self.assertEqual(result["editorial_review_candidates"], [])

    def test_duplicate_or_unapproved_injected_source_is_rejected(self):
        with self.assertRaises(catalog.FederationError):
            catalog.inspect_review_candidate(editorial_records=(self.record,
                                                                 deepcopy(self.record)))
        for injected in (
            {"human_approved": True}, {"export_allowed": True},
            {"source_id": "doc:unknown/private"},
        ):
            record = deepcopy(self.record)
            if "source_id" in injected:
                record["sources"][0]["source_id"] = injected["source_id"]
            else:
                record.update(injected)
            with self.subTest(injected=injected):
                with self.assertRaises(catalog.FederationError):
                    catalog.inspect_review_candidate(editorial_records=(record,))
        with self.assertRaises(catalog.FederationError):
            catalog.inspect_review_candidate("0" * 64)
        with self.assertRaises(catalog.FederationError):
            catalog.inspect_review_candidate("../../../private")

    def test_browser_never_converts_payload_html_into_trusted_markup(self):
        record = deepcopy(self.record)
        record["chapters"][0]["body"] = "<script>alert(1)</script> Claim approved!"
        fake = editor.compile_review_draft(record)
        detail = catalog.inspect_review_candidate(
            fake["draft_sha256"], editorial_records=(record,))
        rendered = catalog.render_review_candidate(detail)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("미승인", rendered)
        altered = deepcopy(detail)
        altered["human_approved"] = True
        # Rendering does not authorize approval. Host still uses only source data.
        self.assertFalse(detail["candidate"]["human_approved"])

    def test_loopback_http_real_catalog_to_detail_and_json(self):
        def forbidden(*_a, **_kw):
            self.fail("HTTP review reads W04/DB")
        handler = catalog.make_handler(self.root, public_reader=forbidden)
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            thread = threading.Thread(target=server.serve_forever,
                                      kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            prefix = "http://127.0.0.1:" + str(server.server_port)
            def get(path, *, host=None):
                request = Request(prefix + path,
                                  headers={} if host is None else {"Host": host})
                try:
                    with urlopen(request, timeout=6) as r:
                        return r.status, r.read().decode("utf-8")
                except HTTPError as exc:
                    with exc:
                        return exc.code, exc.read().decode("utf-8")
            try:
                status, html = get("/catalog?q=BOUNDED_METADATA")
                self.assertEqual(status, 200)
                self.assertIn("/catalog/review?id=" +
                              self.pilot["draft_sha256"], html)
                status, html = get("/catalog/review?id=" + self.pilot["draft_sha256"])
                self.assertEqual(status, 200)
                self.assertIn("기존 실행형 기술서적과 후보 비교", html)
                self.assertIn("PENDING", html)
                status, raw = get("/catalog/review.json?id=" +
                                  self.pilot["draft_sha256"])
                self.assertEqual(status, 200)
                data = json.loads(raw)
                self.assertEqual(data["candidate"]["draft_sha256"],
                                 self.pilot["draft_sha256"])
                self.assertEqual(data["review_receipt"]["draft_sha256"],
                                 self.pilot["draft_sha256"])
                self.assertEqual(len(data["comparison"]), 3)
                self.assertFalse(data["export_allowed"])
                status, raw = get("/catalog.json?q=BOUNDED_METADATA")
                self.assertEqual(status, 200)
                found = json.loads(raw)
                self.assertEqual(found["editorial_review_candidates"][0]["draft_sha256"],
                                 self.pilot["draft_sha256"])
                self.assertEqual(get("/catalog/review?id=" + "0" * 64)[0], 400)
                self.assertEqual(get("/catalog/review?export=true")[0], 400)
                self.assertEqual(get("/catalog/review?id=" +
                                     self.pilot["draft_sha256"] +
                                     "&approved=true")[0], 400)
                self.assertEqual(get("/catalog/review?id=" +
                                     self.pilot["draft_sha256"],
                                     host="untrusted.invalid")[0], 403)
                self.assertEqual(get("/catalog/review.json?id=" +
                                     self.pilot["draft_sha256"],
                                     host="untrusted.invalid")[0], 403)
            finally:
                server.shutdown()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
