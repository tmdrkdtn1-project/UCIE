"""One focused UCIE Local V1 product + hardcoded development priority test.

Only first-party disposable UCIE app and library inputs; no customer files,
operating DB writes, private code, scheduler modifications, release or signing.
"""
from __future__ import annotations

from http.server import HTTPServer
from pathlib import Path
import http.client
import tempfile
import threading
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import local_v1_priority_v01 as priority
from ucie_miner.library_search import SCHEMA as PUBLIC_SCHEMA
from ucie_miner.public_collection_inventory_v01 import SCHEMA as INV_SCHEMA


def public_rows():
    item = {
        "library_item_id": "a" * 64,
        "purpose_code": "PY_SCANDIR_SHARED_ITERATOR_RACE",
        "source_id": "repo:python/cpython",
        "public_url": "https://github.com/python/cpython/pull/155365",
        "domain": "Python",
        "version_scope_claim": "UNDETERMINED",
        "evidence_sha256": "b" * 64,
        "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
        "human_approved": False,
        "export_allowed": False,
    }
    return {
        "schema": PUBLIC_SCHEMA,
        "status": "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
        "network_requests": 0,
        "operating_database_writes": 0,
        "approved_or_exportable_items": 0,
        "auto_promoted": False,
        "items": [item],
    }


def inventory():
    return {
        "schema": INV_SCHEMA,
        "status": "COLLECTION_LEDGER_COUNTS_OBSERVED_SCHEDULER_UNATTESTED",
        "captured_utc": "2026-11-08T07:00:00+00:00",
        "legacy_miner": {"candidates": 4},
        "stage10_public_candidate_staging": {"candidate_revisions": 2},
        "operating_database_writes": 0,
        "issues": [],
    }


class PriorityContractTests(unittest.TestCase):
    def test_only_local_product_tasks_allowed(self):
        for name in priority.LOCAL_WORK:
            row = priority.require_local_work(name)
            self.assertEqual(row["status"],
                             "LOCAL_PRODUCT_TASK_ALLOWED_UNDER_OWNER_PRIORITY")
            self.assertFalse(row["local_v1_accepted"])
            self.assertFalse(row["online_release_authorized"])
        self.assertFalse(priority.roadmap()["customer_distribution_authorized"])

    def test_online_peripheral_and_unknown_tasks_fail_closed(self):
        for kind in (*priority.DEFERRED_WORK, "UNKNOWN", "", "ONLINE_DEPLOYMENT ",
                     None, True, 5):
            with self.subTest(kind=kind):
                with self.assertRaises(priority.LocalPriorityError):
                    priority.require_local_work(kind)

    def test_acceptance_cannot_be_faked_with_source_flag(self):
        with patch.object(priority, "LOCAL_V1_ACCEPTED_BY_OWNER", True):
            with self.assertRaises(priority.LocalPriorityError):
                priority.require_local_work("LOCAL_APP")
        self.assertEqual(len(priority.LOCAL_ACCEPTANCE_GATES), 6)
        self.assertFalse(priority.ONLINE_RELEASE_AUTHORIZED)
        self.assertFalse(priority.PERIPHERAL_EXPANSION_AUTHORIZED)


class LocalUserJobsTests(unittest.TestCase):
    def test_real_first_party_engine_runs_on_user_selection(self):
        html = app._engine("purpose=SKILL_TEST_AUTOMATION")
        self.assertIn("TAGGED_TEST_CASE_LOOKUP_V1", html)
        self.assertIn("기준 연산", html)
        self.assertIn("결과 동등성", html)
        self.assertIn("합성 workload", html)
        self.assertIn("실제 프로젝트", html)

    def test_real_two_skillbooks_are_clickable_and_draft_only(self):
        html = app._books("q=")
        self.assertIn("/skillbooks/", html)
        self.assertIn("미승인", html)
        self.assertIn("내보내기 불가", html)
        self.assertIn("Git", html)
        self.assertIn("Python", html)

    def test_error_job_shows_real_source_url_and_bound_guidance(self):
        with patch.object(app, "_search", return_value=public_rows()):
            html = app._error(Path("UCIE"), "q=SCANDIR")
        self.assertIn("github.com/python/cpython/pull/155365", html)
        self.assertIn("UNVERIFIED_CANDIDATE_ONLY", html)
        self.assertIn("Never concurrently share a raw scandir iterator", html)
        self.assertIn("회귀", html)

    def test_evolution_displays_real_ucie_only_readonly_snapshot_and_change(self):
        with (patch("ucie_miner.public_collection_inventory_v01.collection_inventory",
                    return_value=inventory()),
              patch.object(app, "_search", return_value=public_rows())):
            html = app._evolution(Path("UCIE"), "q=scandir")
        self.assertIn("기존 공개 PR 후보: 4", html)
        self.assertIn("Stage10 개정: 2", html)
        self.assertIn("github.com/python/cpython/pull/155365", html)
        self.assertIn("수동 검토", html)
        self.assertIn("자동 승격", html)

    def test_forged_approval_and_non_allowed_url_fail(self):
        fake = public_rows()
        fake["items"][0]["human_approved"] = True
        with patch("ucie_miner.library_search.search_existing_public_library",
                   return_value=fake):
            with self.assertRaises(app.LocalProductError):
                app._search(Path("UCIE"), "scandir")
        fake = public_rows()
        fake["items"][0]["public_url"] = "https://private.example.org/secret"
        with patch("ucie_miner.library_search.search_existing_public_library",
                   return_value=fake):
            with self.assertRaises(app.LocalProductError):
                app._search(Path("UCIE"), "scandir")

    def test_invalid_or_duplicate_url_params_fail_closed(self):
        for raw in ("q=one&q=two", "q=%3Cscript%3E",
                    "root=anotherproject", "q=" + "x" * 90):
            with self.subTest(raw=raw), self.assertRaises(
                    app.LocalProductError):
                app._error(Path("UCIE"), raw)
        with self.assertRaises(app.LocalProductError):
            app._engine("purpose=ONLINE_DEPLOYMENT")

    def test_nonexistent_public_evidence_does_not_fabricate_fix(self):
        row = public_rows()
        row["status"] = "SOURCE_LINKAGE_INCOMPLETE_NO_GO"
        row["items"] = []
        with patch.object(app, "_search", return_value=row):
            html = app._error(Path("UCIE"), "q=scandir")
        self.assertIn("출처 연결이 불완전", html)
        self.assertNotIn("근거: <a", html)

    def test_policy_screen_displays_no_go(self):
        home, policy_page = app._home(), app._policy()
        self.assertIn("/local/error", home)
        self.assertIn("/local/engine", home)
        self.assertIn("/local/books", home)
        self.assertIn("/local/evolution", home)
        self.assertIn("보류", policy_page)
        self.assertIn("LG6_OWNER_HOST_SIGNOFF_RECEIPT", policy_page)


class LoopbackOwnerAppTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="UCIE_LOCAL_APP_ROUTE_")
        self.addCleanup(t.cleanup)
        root = Path(t.name) / "UCIE"
        (root / ".git").mkdir(parents=True)
        self.server = HTTPServer(("127.0.0.1", 0), app.make_handler(root))
        th = threading.Thread(target=self.server.serve_forever, daemon=True)
        th.start()
        self.addCleanup(th.join, 2)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, route, *, method="GET", host=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5)
        try:
            headers = {"Host": host or "127.0.0.1:" + str(self.server.server_port)}
            connection.request(method, route, headers=headers)
            response = connection.getresponse()
            return response.status, response.read().decode("utf-8", "replace"), dict(
                response.getheaders())
        finally:
            connection.close()

    def test_one_local_screen_and_four_navigable_routes(self):
        status, body, headers = self.request("/local")
        self.assertEqual(status, 200)
        for name in ("/local/error", "/local/engine",
                     "/local/books", "/local/evolution"):
            self.assertIn(name, body)
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertIn("default-src 'none'",
                      headers.get("Content-Security-Policy", ""))
        for route in ("/local/error", "/local/engine",
                      "/local/books", "/local/policy"):
            status, _, _ = self.request(route)
            self.assertEqual(status, 200, route)

    def test_external_host_rejected_and_post_disabled(self):
        status, _, _ = self.request("/local", host="evil.example")
        self.assertEqual(status, 403)
        status, body, _ = self.request("/local/engine", method="POST")
        self.assertEqual(status, 405)
        self.assertIn("READ_ONLY", body)


if __name__ == "__main__":
    unittest.main()
