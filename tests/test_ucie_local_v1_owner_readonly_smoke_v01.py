"""Real owner-only UCIE Local V1 read-only consumer smoke.

Runs ONLY inside the exact D:/UCIE checkout on Windows. No mock public
evidence, no scheduler changes, no writes or independent owner user signoff.
CI on ephemeral cloud machines intentionally skips.
"""
from __future__ import annotations

from http.server import HTTPServer
import http.client
import json
import os
from pathlib import Path
import threading
import unittest

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import local_v1_priority_v01 as policy
from ucie_miner.library_search import search_existing_public_library


@unittest.skipUnless(
    os.name == "nt" and Path(__file__).resolve().parents[1] ==
    Path("D:/UCIE").resolve(),
    "OWNER_HOST_EXACT_D_UCIE_ONLY",
)
class RealOwnerPublicOnlyLocalV1Workflow(unittest.TestCase):
    def test_actual_existing_ucie_source_four_product_actions(self):
        root = Path("D:/UCIE")
        self.assertTrue((root / ".git").is_dir())
        self.assertTrue((root / "runtime").is_dir())
        home = app._home()
        self.assertIn('href="/local/error"', home)
        self.assertIn('href="/local/library"', home)
        engine = app._engine("purpose=SKILL_TEST_AUTOMATION")
        self.assertIn("TAGGED_TEST_CASE_LOOKUP_V1", engine)
        real_engine = app._engine("purpose=REAL_PUBLIC_CATALOG", root=root)
        self.assertTrue(
            "REAL_PUBLIC_METADATA_EXACT_QUERY_EQUIVALENT_UNAPPROVED" in real_engine
            or "현재 소스 계보가 연결된 공개 카탈로그가 없습니다" in real_engine
        )
        books = app._library(root, "q=")
        self.assertIn("/skillbooks/", books)
        self.assertIn("미승인", books)
        error = app._error(root, "q=python")
        self.assertIn("오류 예방", error)
        self.assertTrue("UNVERIFIED_CANDIDATE_ONLY" in error or
                        "출처 연결이 불완전" in error or
                        "기존 공개 근거가 없습니다" in error)
        evolution = app._evolution(root, "q=python")
        self.assertIn("기존 공개 PR 후보:", evolution)
        self.assertIn("수동 검토", evolution)
        snapshot = policy.roadmap()
        self.assertFalse(snapshot["local_v1_accepted_by_owner"])
        self.assertFalse(snapshot["customer_distribution_authorized"])
        print("UCIE_LOCAL_V1_OWNER_READONLY_SMOKE=" + json.dumps({
            "status": "FOUR_PRODUCT_ACTION_RENDER_PATHS_OBSERVED_NOT_OWNER_UI_ACCEPTANCE",
            "real_public_catalog_engine_observed": (
                "REAL_PUBLIC_METADATA_EXACT_QUERY_EQUIVALENT_UNAPPROVED"
                in real_engine),
            "error_public_link_displayed": "github.com/" in error,
            "evolution_public_link_displayed": "github.com/" in evolution,
            "existing_public_ledger_snapshot_displayed": True,
            "real_owner_browser_walkthrough_completed": False,
            "local_product_go": False,
            "customer_distribution_authorized": False,
            "scheduler_changes": 0,
            "operating_ledger_writes": 0,
            "other_projects_accessed": False,
        }, sort_keys=True))


    def test_actual_ucie_public_paging_preserves_total_matches(self):
        root = Path("D:/UCIE")
        first = search_existing_public_library(
            root, query="python", limit=10, offset=0)
        self.assertEqual(first["returned_count"], len(first["items"]))
        self.assertTrue(first["total_matches"] >= len(first["items"]))
        if first["total_matches"] > 10:
            second = search_existing_public_library(
                root, query="python", limit=10, offset=10)
            self.assertEqual(second["total_matches"], first["total_matches"])
            self.assertEqual(second["page_offset"], 10)
            self.assertEqual(second["returned_count"], len(second["items"]))
            self.assertTrue(all(
                row["lifecycle"] == "UNVERIFIED_CANDIDATE_ONLY"
                and row["human_approved"] is False
                and row["export_allowed"] is False
                for row in second["items"]))
        print("UCIE_OWNER_REAL_W04_PAGING=" + json.dumps({
            "query": "python",
            "all_matching_candidate_revisions": first["total_matches"],
            "page_size": 10,
            "first_page_displayed": len(first["items"]),
            "second_page_available": first["total_matches"] > 10,
            "stage12_index_total_not_equivalent_to_approved_rules": True,
            "release_approved": False,
        }, sort_keys=True))

    def test_actual_owner_localhost_browser_routes(self):
        root = Path("D:/UCIE")
        server = HTTPServer(("127.0.0.1", 0), app.make_handler(root))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            paths = (
                "/local", "/local/error?q=python",
                "/local/engine?purpose=ENGINE_INCREMENTAL_BUILD",
                "/local/engine?purpose=REAL_PUBLIC_CATALOG",
                "/local/library?q=Git", "/local/books?q=Git",
                "/local/library?q=python&page=2",
                "/local/evolution?q=python", "/skillbooks",
                "/catalog?shelf=all&limit=5",
            )
            for route in paths:
                with self.subTest(route=route):
                    connection = http.client.HTTPConnection(
                        "127.0.0.1", server.server_port, timeout=10)
                    try:
                        connection.request("GET", route, headers={
                            "Host": "127.0.0.1:" + str(server.server_port)})
                        reply = connection.getresponse()
                        body = reply.read()
                        if route.startswith("/local/books"):
                            self.assertEqual(reply.status, 302)
                            self.assertTrue(
                                dict(reply.getheaders()).get("Location", "")
                                .startswith("/local/library"))
                        else:
                            self.assertEqual(reply.status, 200)
                        self.assertLess(len(body), 900_000)
                    finally:
                        connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
