"""UCIE V0.5: synthetic public claim intake, tamper protection and browser E2E."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import HTTPServer
import json
from pathlib import Path
import re
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from test_ucie_library_v02 import fixture
from ucie_miner.library_review_v04 import dossier_from_linked_handoff
from ucie_miner.library_explore import explore_linked_public_candidates
from ucie_miner.library_compare import compare_linked_public_candidates
from ucie_miner.library_browser_v05 import (
    SCHEMA, make_handler, render_claims_panel,
)
from ucie_miner.library_review_records_v05 import (
    ClaimError, GATES, CLAIM_ONLY,
    record_claim, review_claims, _public_evidence_url,
)

NOW = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
PUBLIC_SHA = "a" * 64


def starting():
    h = fixture()
    item = explore_linked_public_candidates(h)["items"][0]
    dossier = dossier_from_linked_handoff(h, item_id=item["library_item_id"])
    return h, item, dossier


@contextmanager
def owner_synthetic_root():
    with tempfile.TemporaryDirectory(prefix="ucie-v05-only-") as td:
        root = Path(td) / "UCIE"
        root.mkdir()
        yield root


def store_one(root, dossier, **overrides):
    values = dict(
        item_id=dossier["item"]["library_item_id"],
        gate="VERSION_APPLICABILITY",
        evidence_url=dossier["item"]["public_url"],
        claimed_sha256=PUBLIC_SHA,
        version_hint="UNDETERMINED",
        clock=NOW,
    )
    values.update(overrides)
    with patch("ucie_miner.library_review_records_v05.dossier_existing_public_candidate",
               return_value=dossier):
        return record_claim(root, **values)


@contextmanager
def live_ui(root, handoff, dossier):
    def explorer(unused_root, **kw):
        return explore_linked_public_candidates(handoff, **kw)

    def comparer(unused_root, *, item_ids):
        return compare_linked_public_candidates(handoff, item_ids=item_ids)

    def reviewer(unused_root, *, item_id):
        return dossier_from_linked_handoff(handoff, item_id=item_id)

    with HTTPServer(("127.0.0.1", 0), make_handler(
            root, explorer=explorer, comparer=comparer,
            reviewer=reviewer, claims_loader=review_claims)) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield "http://127.0.0.1:" + str(server.server_port)
        finally:
            server.shutdown()
            thread.join(timeout=5)


class PublicClaimLedgerV05(unittest.TestCase):
    def test_explicit_record_dedup_immutable_receipt_and_unknown_gates(self):
        _, item, dossier = starting()
        with owner_synthetic_root() as root:
            empty = review_claims(root, dossier)
            self.assertEqual(empty["total_claims"], 0)
            self.assertFalse((root / "runtime").exists())
            created = store_one(root, dossier)
            self.assertEqual(created["status"], "CLAIM_STORED_UNVERIFIED")
            rid = created["receipt_id"]
            self.assertRegex(rid, r"^[0-9a-f]{64}$")
            again = store_one(root, dossier)
            self.assertEqual(again["status"], "ALREADY_RECORDED_UNVERIFIED")
            self.assertEqual(again["receipt_id"], rid)
            path = root / "runtime" / "public_review_v05" / "receipts" / (rid + ".json")
            self.assertTrue(path.exists())
            self.assertEqual(len(list(path.parent.iterdir())), 1)
            payload = json.loads(path.read_text("ascii"))
            self.assertEqual(payload["status"], CLAIM_ONLY)
            self.assertFalse(payload["independent_verification"])
            self.assertEqual(payload["source_id"], item["source_id"])
            self.assertEqual(payload["source_sha256"], item["evidence_sha256"])
            self.assertEqual(payload["claimed_document_sha256"], PUBLIC_SHA)
            view = review_claims(root, dossier)
            self.assertEqual(view["total_claims"], 1)
            self.assertEqual(view["gate_counts"]["VERSION_APPLICABILITY"], 1)
            self.assertFalse(view["independently_verified"])
            self.assertFalse(view["owner_approved"])
            self.assertEqual(view["operating_database_writes"], 0)
            self.assertEqual(view["network_requests"], 0)

    def test_independent_gates_remain_not_verified_even_after_many_submissions(self):
        _, _, dossier = starting()
        with owner_synthetic_root() as root:
            for gate in sorted(GATES):
                r = store_one(root, dossier, gate=gate)
                self.assertEqual(r["status"], "CLAIM_STORED_UNVERIFIED")
            result = review_claims(root, dossier)
            self.assertEqual(result["total_claims"], len(GATES))
            self.assertTrue(all(v == 1 for v in result["gate_counts"].values()))
            page = render_claims_panel(result, dossier)
            self.assertIn("접수된 공개 검토 근거", page)
            self.assertIn("CLAIM_RECEIVED_UNVERIFIED", page)
            self.assertNotIn("VERIFIED_PASS", page)
            self.assertIn("NOT_VERIFIED", page)
            self.assertNotIn("OWNER_APPROVED", page)

    def test_reject_unapproved_url_and_hash_without_creating_directory(self):
        _, _, dossier = starting()
        bads = [
            {"evidence_url": "https://github.com/private/other/pull/123"},
            {"evidence_url": "https://github.com/python/cpython/pull/3?redirect=x"},
            {"evidence_url": "http://github.com/python/cpython/pull/2"},
            {"evidence_url": "https://github.com@evil.test/python/cpython/pull/2"},
            {"evidence_url": "https://docs.python.org.evil.test/library/"},
            {"evidence_url": "https://evil.test/path"},
            {"evidence_url": "https://github.com/python/cpython/../../private"},
            {"evidence_url": "https://github.com/python/cpython/issues/1"},
            {"claimed_sha256": "NOT_DIGEST"},
            {"gate": "OWNER_SIGNOFF"},
            {"gate": "SOURCE_PROVENANCE"},
            {"gate": "__import__('os')"},
            {"version_hint": "../secret"},
        ]
        with owner_synthetic_root() as root:
            for data in bads:
                with self.subTest(input=data), self.assertRaises(ClaimError):
                    store_one(root, dossier, **data)
            self.assertFalse((root / "runtime" / "public_review_v05").exists())

    def test_tamper_fail_closed_bad_filename_bad_fields_stale_source_sha(self):
        _, _, dossier = starting()
        with owner_synthetic_root() as root:
            saved = store_one(root, dossier)
            receipts = root / "runtime" / "public_review_v05" / "receipts"
            path = receipts / (saved["receipt_id"] + ".json")
            contents = path.read_text("ascii")
            changed = json.loads(contents)
            changed["status"] = "VERIFIED_PASS"
            path.write_text(json.dumps(changed), encoding="ascii")
            with self.assertRaises(ClaimError):
                review_claims(root, dossier)
            path.write_text(contents, encoding="ascii")
            other = dict(dossier)
            other["item"] = dict(dossier["item"])
            other["item"]["evidence_sha256"] = "b" * 64
            with self.assertRaises(ClaimError):
                review_claims(root, other)
            path2 = receipts / "unexpected-private.txt"
            path2.write_text("unsafe", encoding="ascii")
            with self.assertRaises(ClaimError):
                review_claims(root, dossier)

    def test_stale_lock_and_symlink_fail_closed(self):
        _, _, dossier = starting()
        with owner_synthetic_root() as root:
            folder = root / "runtime" / "public_review_v05"
            folder.mkdir(parents=True)
            lock = folder / ".record-v05.lock"
            lock.write_text("other writer", encoding="ascii")
            with self.assertRaises(ClaimError):
                store_one(root, dossier)
            self.assertEqual(lock.read_text("ascii"), "other writer")
            lock.unlink()
            if hasattr(__import__("os"), "symlink"):
                try:
                    (folder / "receipts").symlink_to(root, target_is_directory=True)
                except (OSError, NotImplementedError):
                    pass
                else:
                    with self.assertRaises(ClaimError):
                        store_one(root, dossier)

    def test_local_http_search_review_status_back_and_v03_compare(self):
        handoff, item, dossier = starting()
        with owner_synthetic_root() as root:
            stored = store_one(root, dossier)
            with live_ui(root, handoff, dossier) as url:
                with urlopen(url + "/health", timeout=5) as response:
                    status = json.load(response)
                    self.assertEqual(status["schema"], SCHEMA)
                    self.assertEqual(status["db_writes"], 0)
                    self.assertEqual(status["review_receipt_writes"], 0)
                with urlopen(url + "/", timeout=5) as response:
                    self.assertIn("V0.5", response.read().decode("utf-8"))
                with urlopen(url + "/?q=&source=&domain=&kind=&limit=10&page=1",
                             timeout=5) as response:
                    search = response.read().decode("utf-8")
                    self.assertIn("검증 준비표", search)
                    self.assertIn("비교 선택", search)
                detail = "/review/" + item["library_item_id"]
                with urlopen(url + detail +
                             "?q=&source=&domain=&kind=&limit=10&page=1",
                             timeout=5) as response:
                    html = response.read().decode("utf-8")
                    self.assertEqual(response.status, 200)
                    self.assertIn("V0.5", html)
                    self.assertIn("검증 요구사항", html)
                    self.assertIn("접수된 공개 검토 근거", html)
                    self.assertIn(stored["receipt_id"][:6], stored["receipt_id"])
                    self.assertIn("1</strong>", html)
                    self.assertIn("NOT_VERIFIED", html)
                    self.assertIn("선택했던 검색 결과로 돌아가기", html)
                ids = [r["library_item_id"] for r in
                       explore_linked_public_candidates(handoff, limit=5)["items"][:2]]
                compare = "/compare?" + urlencode(
                    [("item", x) for x in ids] + [
                        ("q", ""), ("source", ""), ("domain", ""),
                        ("kind", ""), ("limit", "5"), ("page", "1")])
                with urlopen(url + compare, timeout=5) as response:
                    html = response.read().decode("utf-8")
                    self.assertIn("후보 2", html)
                    self.assertIn("V0.5", html)
                with urlopen(url + "/item/" + item["library_item_id"],
                             timeout=5) as response:
                    self.assertIn("근거 후보 상세", response.read().decode("utf-8"))
                with self.assertRaises(HTTPError) as ex:
                    urlopen(Request(url + detail, data=b"apply", method="POST"), timeout=5)
                self.assertEqual(ex.exception.code, 405)

    def test_receipt_corruption_returns_503_not_false_verified(self):
        handoff, item, dossier = starting()
        with owner_synthetic_root() as root:
            receipt = store_one(root, dossier)
            p = (root / "runtime" / "public_review_v05" / "receipts" /
                 (receipt["receipt_id"] + ".json"))
            p.write_text("{bad json", encoding="ascii")
            with live_ui(root, handoff, dossier) as url:
                with self.assertRaises(HTTPError) as e:
                    urlopen(url + "/review/" + item["library_item_id"], timeout=5)
                self.assertEqual(e.exception.code, 503)
                self.assertEqual(e.exception.read(), b"SOURCE_VALIDATION_FAILED_NO_GO")


if __name__ == "__main__":
    unittest.main()
