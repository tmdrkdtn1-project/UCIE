"""UCIE owner selected W04 source -> bounded first-party Python/MCP trials.

All fixtures are UCIE-authored source metadata. No upstream code is executed;
actual Windows owner smoke, if present, reads only existing UCIE public metadata.
"""
from __future__ import annotations

from contextlib import closing
from copy import deepcopy
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch
import os
import json
import unittest

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import local_selected_public_trial_v01 as trial
from ucie_miner.local_v1_public_review_v01 import create_review_worksheet
from ucie_miner.library_search import search_existing_public_library
from test_ucie_local_v1_product_v01 import public_rows


SOURCE_ID = "a" * 64
BASE = "q=scandir&page=1&id=" + SOURCE_ID + "&from=library"
PY_ROW = public_rows()["items"][0]


def selection(source_id="repo:python/cpython",
              public_url="https://github.com/python/cpython/pull/155365",
              pattern="PY_SCANDIR_SHARED_ITERATOR_RACE") -> dict:
    item = dict(PY_ROW)
    item.update(source_id=source_id, public_url=public_url, purpose_code=pattern)
    result = public_rows()
    result["items"] = [item]
    return result


def selected_review(report: dict) -> dict:
    return create_review_worksheet(report["items"][0])


class SelectedPublicEvidenceTrialTests(unittest.TestCase):
    def test_01_exact_source_pattern_selected_and_not_approval(self):
        option = trial.available_trial(selected_review(selection()))
        self.assertTrue(option["available"])
        self.assertEqual(option["case"], trial.CASE_SCANDIR)
        self.assertEqual(option["selected_public_candidate_id"], SOURCE_ID)
        self.assertEqual(option["selected_public_evidence_sha256"], "b" * 64)
        self.assertFalse(option["source_fix_independently_verified"])
        self.assertFalse(option["customer_distribution_authorized"])

    def test_02_selected_python_review_displays_real_click_path(self):
        with patch.object(app, "_search", return_value=selection()):
            rendered = app._review(Path("UCIE"), BASE)
        self.assertIn('data-selected-trial="available"', rendered)
        self.assertIn("관련 UCIE 자체 안전 실험 실행", rendered)
        self.assertIn("&amp;trial=1", rendered)
        self.assertIn("155365", rendered)
        self.assertIn("NOT_VERIFIED", rendered)
        self.assertIn("실제 회귀시험: NOT_EXECUTED", rendered)

    def test_03_click_runs_first_party_disposable_python_fixture_only(self):
        with patch.object(app, "_search", return_value=selection()):
            rendered = app._review(Path("UCIE"), BASE + "&trial=1")
        self.assertIn('data-selected-trial="executed"', rendered)
        self.assertIn("임시 파일 4개", rendered)
        self.assertIn("잠금으로 보호", rendered)
        self.assertIn("두 소비자", rendered)
        self.assertIn("155365", rendered)
        self.assertIn("실제 공개 PR의 수정 효과", rendered)
        self.assertIn("모두 미검증", rendered)
        self.assertIn("NOT_VERIFIED", rendered)

    def test_04_only_exact_mcp_prompts_pr_can_run_related_mcp_fixture(self):
        report = selection(
            source_id="repo:modelcontextprotocol/python-sdk",
            public_url="https://github.com/modelcontextprotocol/python-sdk/pull/3696",
            pattern="API_CONTRACT",
        )
        option = trial.available_trial(selected_review(report))
        self.assertTrue(option["available"])
        self.assertEqual(option["case"], trial.CASE_MCP)
        with patch.object(app, "_search", return_value=report):
            html = app._review(Path("UCIE"), BASE + "&trial=1")
        self.assertIn("JSON-RPC 사례 8개", html)
        self.assertIn("계약 일치 6개", html)
        self.assertIn("서버 오류 대조 2개", html)
        self.assertIn("독립 회귀시험", html)

    def test_05_other_mcp_api_contract_pr_gets_distinct_example_not_fix_proof(self):
        report = selection(
            source_id="repo:modelcontextprotocol/python-sdk",
            public_url="https://github.com/modelcontextprotocol/python-sdk/pull/1928",
            pattern="API_CONTRACT",
        )
        available = trial.available_trial(selected_review(report))
        self.assertTrue(available["available"])
        self.assertFalse(available["same_exact_public_reference_as_example"])
        self.assertTrue(available["same_pattern_domain_only_not_same_fix_verified"])
        self.assertEqual(
            available["illustrative_reference_url"],
            "https://github.com/modelcontextprotocol/python-sdk/pull/3696")
        with patch.object(app, "_search", return_value=report):
            html = app._review(Path("UCIE"), BASE)
            self.assertIn('data-selected-trial="available"', html)
            page = app._review(Path("UCIE"), BASE + "&trial=1")
        self.assertIn('data-example-reference-separate="True"', page)
        self.assertIn("pull/1928", page)
        self.assertIn("pull/3696", page)
        self.assertIn("선택한 PR의 코드나 수정 내용을 시험한 것은 아닙니다", page)
        self.assertIn("독립 회귀시험", page)

    def test_06_generic_pattern_does_not_claim_or_run_unrelated_trial(self):
        for source_id, url, pattern in (
            ("repo:python/cpython", "https://github.com/python/cpython/pull/155365", "API_CONTRACT"),
            ("repo:PowerShell/PowerShell",
             "https://github.com/PowerShell/PowerShell/pull/25780",
             "PY_SCANDIR_SHARED_ITERATOR_RACE"),
            ("repo:git/git", "https://github.com/git/git/pull/1000", "RESOURCE_CLEANUP"),
        ):
            with self.subTest(source=source_id, pattern=pattern):
                report = selection(source_id, url, pattern)
                self.assertFalse(trial.available_trial(selected_review(report))["available"])
                with patch.object(app, "_search", return_value=report):
                    self.assertIn('data-selected-trial="unavailable"',
                                  app._review(Path("UCIE"), BASE))
                    with self.assertRaises(app.LocalProductError):
                        app._review(Path("UCIE"), BASE + "&trial=1")

    def test_07_missing_or_stale_public_item_id_never_executes(self):
        with patch.object(app, "_search", return_value=selection()):
            with self.assertRaises(app.LocalProductError):
                app._review(Path("UCIE"), "q=scandir&page=1&id=" +
                            ("f" * 64) + "&from=library&trial=1")
        empty = selection()
        empty["items"] = []
        empty["returned_count"] = 0
        empty["total_matches"] = 0
        with patch.object(app, "_search", return_value=empty):
            with self.assertRaises(app.LocalProductError):
                app._review(Path("UCIE"), BASE + "&trial=1")

    def test_08_bad_trial_mode_duplicate_and_cross_project_field_rejected(self):
        for suffix in ("&trial=0", "&trial=2", "&trial=", "&trial=yes",
                       "&trial=1&trial=1", "&trial=1&root=another-project"):
            with self.subTest(suffix=suffix):
                with patch.object(app, "_search", return_value=selection()):
                    with self.assertRaises(app.LocalProductError):
                        app._review(Path("UCIE"), BASE + suffix)

    def test_09_false_approval_and_tampered_source_rejected(self):
        for field, value in (
            ("human_approved", True), ("export_allowed", True),
            ("lifecycle", "APPROVED"), ("public_url", "https://invalid.example/x"),
        ):
            with self.subTest(field=field):
                report = selection()
                report["items"][0][field] = value
                with patch.object(app, "_search", return_value=report):
                    with self.assertRaises(ValueError):
                        app._review(Path("UCIE"), BASE + "&trial=1")

    def test_10_forged_python_trial_approval_or_incomplete_fixture_rejected(self):
        from ucie_miner import python_scandir_review_v01 as py
        real = py.run_python_scandir_review
        for key, value in (
            ("human_approved", True),
            ("source_executed", True),
            ("synthetic_trial", {"synthetic_file_count": 4}),
        ):
            with self.subTest(key=key):
                forged = deepcopy(real())
                forged[key] = value
                with patch.object(py, "run_python_scandir_review", return_value=forged):
                    with self.assertRaises(trial.SourceSelectedTrialError):
                        trial.run_selected_trial(selected_review(selection()))

    def test_11_forged_mcp_upstream_claim_rejected(self):
        from ucie_miner import mcp_prompt_regression_v01 as mcp
        result = selected_review(selection(
            "repo:modelcontextprotocol/python-sdk",
            "https://github.com/modelcontextprotocol/python-sdk/pull/3696",
            "API_CONTRACT",
        ))
        real = mcp.synthetic_demonstration()
        forged = {**real, "customer_release_authorized": True}
        with patch.object(mcp, "synthetic_demonstration", return_value=forged):
            with self.assertRaises(trial.SourceSelectedTrialError):
                trial.run_selected_trial(result)

    def test_12_real_loopback_candidate_selection_and_blocked_method(self):
        with TemporaryDirectory(prefix="UCIE_SELECTED_PUBLIC_EXPERIMENT_") as tmp:
            root = Path(tmp) / "UCIE"
            (root / ".git").mkdir(parents=True)
            with HTTPServer(("127.0.0.1", 0), app.make_handler(root)) as server:
                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    def get(path, method="GET", host=None):
                        with closing(HTTPConnection("127.0.0.1", server.server_port, timeout=10)) as conn:
                            conn.request(method, path, headers={
                                "Host": host or "127.0.0.1:" + str(server.server_port)})
                            response = conn.getresponse()
                            return response.status, response.read().decode("utf-8", "replace")
                    with patch.object(app, "_search", return_value=selection()):
                        status, page = get("/local/review?" + BASE + "&trial=1")
                        self.assertEqual(status, 200)
                        self.assertIn('data-selected-trial="executed"', page)
                        self.assertEqual(get("/local/review?" + BASE + "&trial=999")[0], 400)
                        self.assertEqual(get("/local/review?" + BASE, "POST")[0], 405)
                        self.assertEqual(get("/local/review?" + BASE,
                                             host="other.example")[0], 403)
                finally:
                    server.shutdown()
                    thread.join(timeout=4)
                    self.assertFalse(thread.is_alive())


@unittest.skipUnless(
    os.name == "nt" and Path(__file__).resolve().parents[1] ==
    Path("D:/UCIE").resolve(),
    "OWNER_UCIE_EXACT_D_DRIVE_ONLY",
)
class ActualOwnerSelectedEvidenceReadOnlyTests(unittest.TestCase):
    def test_13_real_existing_public_scandir_candidate_can_run_related_ucie_trial(self):
        root = Path("D:/UCIE")
        query = "PY_SCANDIR_SHARED_ITERATOR_RACE"
        source = search_existing_public_library(root, query=query, limit=10)
        self.assertEqual(source["status"], "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO")
        entries = [
            item for item in source["items"]
            if item["source_id"] == "repo:python/cpython"
            and item["purpose_code"] == query
        ]
        if not entries:
            self.skipTest("NO_EXACT_REAL_PUBLIC_SCANDIR_SOURCE_IN_OWNER_W04_LEDGER")
        selected = entries[0]
        actual = app._review(
            root, "q=" + query + "&page=1&id=" + selected["library_item_id"] +
            "&from=library&trial=1")
        self.assertIn(selected["public_url"], actual)
        self.assertIn('data-selected-trial="executed"', actual)
        self.assertIn("실제 회귀시험: NOT_EXECUTED", actual)


    def test_14_actual_owner_public_candidate_trial_coverage_readonly(self):
        root = Path("D:/UCIE")
        queries = ("API_CONTRACT", "scandir", "MCP")
        checks = []
        for query in queries:
            report = search_existing_public_library(root, query=query, limit=20)
            self.assertEqual(report["status"], "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO")
            self.assertTrue(all(
                item.get("human_approved") is False and
                item.get("export_allowed") is False
                for item in report["items"]))
            rows = [
                {"source": item["source_id"],
                 "pattern": item["purpose_code"],
                 "url": item["public_url"]}
                for item in report["items"][:5]
            ]
            checks.append({
                "query": query, "total": report["total_matches"],
                "first_page": rows,
                "real_source_selected_trial_currently_available": sum(
                    trial.available_trial(create_review_worksheet(item))["available"]
                    for item in report["items"]),
            })
        print("UCIE_OWNER_REAL_PUBLIC_TRIAL_COVERAGE=" +
              json.dumps(checks, sort_keys=True))


    def test_15_actual_owner_mcp_candidate_clicks_related_ucie_contract_trial(self):
        root = Path("D:/UCIE")
        report = search_existing_public_library(root, query="MCP", limit=20)
        self.assertEqual(report["status"], "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO")
        entries = [
            item for item in report["items"]
            if item["source_id"] == "repo:modelcontextprotocol/python-sdk"
            and item["purpose_code"] == "API_CONTRACT"
            and item["human_approved"] is False
        ]
        self.assertTrue(entries, "no actual MCP API-contract public candidate")
        selected = entries[0]
        page = app._review(
            root, "q=MCP&page=1&id=" + selected["library_item_id"] +
            "&from=library&trial=1")
        self.assertIn(selected["public_url"], page)
        self.assertIn('data-selected-trial="executed"', page)
        self.assertIn("JSON-RPC 사례 8개", page)
        self.assertIn("선택한 PR의 코드나 수정 내용을 시험한 것은 아닙니다", page)
        self.assertIn("실제 회귀시험: NOT_EXECUTED", page)
        print("UCIE_OWNER_ACTUAL_MCP_SELECTED_FIRST_PARTY_TRIAL=" +
              json.dumps({
                  "actual_source_url": selected["public_url"],
                  "public_source_count": report["total_matches"],
                  "ucie_synthetic_mcp_contract_cases": 8,
                  "selected_upstream_pr_verified": False,
                  "auto_promoted": False,
                  "customer_distribution_authorized": False,
                  "operating_db_writes": 0,
              }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
