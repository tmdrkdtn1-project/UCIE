"""Actual UCIE loopback catalog consumes isolated pinned-source review history.

No upstream network, operating DB, customer files, plugin accounts, publishing,
signed approval, release or automatic withdrawal. Manual raw byte fixtures only.
"""
from __future__ import annotations

from copy import deepcopy
from http.server import HTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ucie_miner import skillbook_catalog_union_v01 as catalog
from ucie_miner import skillbook_editorial_production_v01 as editor
from ucie_miner import skillbook_pinned_source_review_v01 as pinned


class PinnedReviewCatalogTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("/UCIE_ONLY_SYNTHETIC_NO_RUNTIME_READ")
        self.draft = editor.compose_curated_two_book_pilot()
        # An intentionally *wrong* raw source: DO NOT call this official bytes.
        raw = b"This is NOT the upstream Python v3.15.0 RST file.\n"
        self.source = pinned.verify_pinned_raw_bytes("doc:python/cpython", raw)
        self.event = pinned.propose_source_review(self.source)
        self.journal, self.receipt = pinned.extend_review_journal(
            b"", self.event)

    def test_review_dossier_exposes_mismatch_without_automatic_withdrawal(self):
        detail = catalog.inspect_review_candidate(
            self.draft["draft_sha256"], pinned_review_history=self.journal)
        rows = {x["source_id"]: x
                for x in detail["pinned_source_review_statuses"]}
        self.assertEqual(
            rows["doc:python/cpython"]["status"],
            "PINNED_RAW_SOURCE_MISMATCH_REVIEW_REQUIRED")
        self.assertFalse(rows["doc:python/cpython"]["raw_source_sha_match"])
        self.assertEqual(rows["doc:python/cpython"]["review_event_id"],
                         self.event["event_id"])
        self.assertEqual(rows["doc:git/git"]["status"],
                         "NO_MATCHING_PINNED_REVIEW_EVENT")
        self.assertFalse(detail["source_content_independently_verified"])
        self.assertFalse(detail["manual_editorial_review_completed"])
        self.assertFalse(detail["pinned_review_history_is_unsigned"] is False)
        self.assertTrue(detail["pinned_review_history_read_only"])
        self.assertFalse(detail["export_allowed"])
        self.assertEqual(detail["approved_items"], 0)
        html = catalog.render_review_candidate(detail)
        self.assertIn("버전 고정 원본 검토 원장", html)
        self.assertIn("버전 고정 원본 불일치", html)
        self.assertIn("자동 철회 없음", html)
        self.assertNotIn("This is NOT the upstream", html)

    def test_default_catalog_without_history_remains_not_reviewed(self):
        detail = catalog.inspect_review_candidate(self.draft["draft_sha256"])
        self.assertEqual(
            {x["status"] for x in detail["pinned_source_review_statuses"]},
            {"NO_MATCHING_PINNED_REVIEW_EVENT"})
        self.assertEqual(detail["network_requests"], 0)
        self.assertFalse(detail["export_allowed"])

    def test_real_local_http_index_detail_json_reflects_journal(self):
        handler = catalog.make_handler(
            self.root, pinned_review_history=self.journal,
            public_reader=lambda *_a, **_k: self.fail("W04 should not query"))
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            base = "http://127.0.0.1:" + str(server.server_port)
            def get(path, *, host=None):
                req = Request(base + path, headers={
                    } if host is None else {"Host": host})
                try:
                    with urlopen(req, timeout=6) as response:
                        return response.status, response.read().decode("utf-8")
                except HTTPError as exc:
                    with exc:
                        return exc.code, exc.read().decode("utf-8")
            try:
                with patch.object(
                        pinned, "persist_review_event",
                        side_effect=AssertionError("GET must not write")):
                    with patch.object(
                            pinned, "verify_ucie_inbox",
                            side_effect=AssertionError("GET must not read source")):
                        status, body = get("/catalog?q=BOUNDED_METADATA")
                        self.assertEqual(status, 200)
                        self.assertIn("고정 태그 원본 검증 불일치", body)
                        status, body = get("/catalog/review?id=" +
                                           self.draft["draft_sha256"])
                        self.assertEqual(status, 200)
                        self.assertIn("버전 고정 원본 검토 원장", body)
                        self.assertIn("자동 철회 없음", body)
                        status, body = get("/catalog/review.json?id=" +
                                           self.draft["draft_sha256"])
                        self.assertEqual(status, 200)
                        d = json.loads(body)
                        self.assertEqual(d["pinned_source_review_statuses"][1]
                                         ["review_event_id"], self.event["event_id"])
                        self.assertFalse(d["export_allowed"])
                        self.assertFalse(d["pinned_review_history_is_unsigned"] is False)
                        status, body = get("/catalog.json?q=BOUNDED_METADATA")
                        self.assertEqual(status, 200)
                        d = json.loads(body)
                        self.assertEqual(
                            d["editorial_review_candidates"][0]
                             ["pinned_source_review_statuses"][1]["status"],
                            "PINNED_RAW_SOURCE_MISMATCH_REVIEW_REQUIRED")
                        self.assertEqual(get("/catalog?commit-review=true")[0], 400)
                        self.assertEqual(get("/catalog/review?withdraw=true")[0], 400)
                        self.assertEqual(get("/catalog/review.json?id=" +
                                             self.draft["draft_sha256"],
                                             host="unauthorized.invalid")[0], 403)
            finally:
                server.shutdown()
                thread.join(timeout=3)

    def test_tampered_chain_blocks_detail_and_http_instead_of_hiding(self):
        invalid = self.journal.replace(b"review_note", b"revised_note")
        with self.assertRaises(catalog.FederationError):
            catalog.inspect_review_candidate(
                self.draft["draft_sha256"], pinned_review_history=invalid)
        handler = catalog.make_handler(self.root, pinned_review_history=invalid)
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            base = "http://127.0.0.1:" + str(server.server_port)
            try:
                with self.assertRaises(HTTPError) as ctx:
                    urlopen(base + "/catalog/review.json?id=" +
                            self.draft["draft_sha256"], timeout=6)
                self.assertEqual(ctx.exception.code, 400)
                ctx.exception.close()
            finally:
                server.shutdown()
                thread.join(timeout=3)

    def test_owner_only_read_only_snapshot_of_exact_review_journal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "UCIE"
            runtime = root / "runtime"
            runtime.mkdir(parents=True)
            self.assertEqual(pinned.read_isolated_review_journal(root), b"")
            saved = pinned.persist_review_event(
                root, self.event, owner_opt_in=True)
            self.assertEqual(saved["status"],
                             "ISOLATED_REVIEW_EVENT_COMMITTED_NOT_APPROVED")
            readonly_snapshot = pinned.read_isolated_review_journal(root)
            self.assertEqual(readonly_snapshot, self.journal)
            before = readonly_snapshot
            readonly_snapshot_again = pinned.read_isolated_review_journal(root)
            self.assertEqual(readonly_snapshot_again, before)
            self.assertEqual(
                pinned.inspect_review_journal(readonly_snapshot)["total_events"], 1)

    def test_unsigned_review_event_does_not_authenticate_publisher(self):
        view = catalog.inspect_review_candidate(
            self.draft["draft_sha256"], pinned_review_history=self.journal)
        self.assertTrue(view["pinned_review_history_is_unsigned"])
        for row in view["pinned_source_review_statuses"]:
            self.assertFalse(row["human_approval_granted"])
            self.assertFalse(row["source_origin_independently_verified"])
            self.assertFalse(row["withdrawal_executed"])
            self.assertFalse(row["export_allowed"])


if __name__ == "__main__":
    unittest.main()
