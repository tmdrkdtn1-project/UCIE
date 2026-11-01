"""UCIE V0.4: synthetic source-linked review checklist and localhost regression."""
from __future__ import annotations

from contextlib import contextmanager
from html import unescape
from http.server import HTTPServer
from pathlib import Path
import json
import re
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ucie_miner.library_review_v04 import (
    INCOMPLETE, NOT_FOUND, READY, ReviewDossierError,
    dossier_from_linked_handoff,
)
from ucie_miner.library_explore import explore_linked_public_candidates
from ucie_miner.library_compare import compare_linked_public_candidates
from ucie_miner.library_browser_v04 import (
    SCHEMA, make_handler, render_review,
)
from test_ucie_library_v02 import fixture
from ucie_public.policy import PolicyError


def first_item(handoff):
    return explore_linked_public_candidates(handoff)["items"][0]["library_item_id"]


@contextmanager
def ui(handoff):
    def explore(root, **kwargs):
        return explore_linked_public_candidates(handoff, **kwargs)

    def compare(root, *, item_ids):
        return compare_linked_public_candidates(handoff, item_ids=item_ids)

    def review(root, *, item_id):
        return dossier_from_linked_handoff(handoff, item_id=item_id)

    with HTTPServer(("127.0.0.1", 0), make_handler(
            Path("Z:/synthetic/UCIE"), explorer=explore,
            comparer=compare, reviewer=review)) as server:
        t = Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            yield "http://127.0.0.1:" + str(server.server_port)
        finally:
            server.shutdown()
            t.join(timeout=3)


class DossierTests(unittest.TestCase):
    def test_six_gates_one_source_linkage_not_six_verified_claims(self):
        h = fixture()
        item = first_item(h)
        d = dossier_from_linked_handoff(h, item_id=item)
        self.assertEqual(d["status"], READY)
        self.assertEqual(d["item"]["library_item_id"], item)
        self.assertTrue(d["source_linkage_checked"])
        self.assertFalse(d["independently_verified"])
        self.assertFalse(d["owner_approved"])
        self.assertFalse(d["export_allowed"])
        self.assertEqual(d["operating_database_writes"], 0)
        self.assertEqual(d["network_requests"], 0)
        self.assertEqual(len(d["requirements"]), 6)
        self.assertEqual(d["requirements"][0]["status"],
                         "SOURCE_LINKAGE_ONLY_NOT_FIX_VERIFIED")
        self.assertTrue(all(g["status"] == "NOT_VERIFIED"
                            for g in d["requirements"][1:]))
        self.assertEqual(d["item"]["version_scope"], "UNDETERMINED")
        self.assertEqual(d["item"]["evidence_revision_count"], 1)
        self.assertIn("후보별 독립 검증 미수행", d["blocking_reasons"])

    def test_source_linkage_missing_unknown_and_forged_fail_closed(self):
        h = fixture()
        item = first_item(h)
        self.assertEqual(dossier_from_linked_handoff(
            h, item_id="f"*64)["status"], NOT_FOUND)
        for malformed in ("foo", "a"*65, "../" + "a"*64, None):
            with self.subTest(v=malformed), self.assertRaises(ReviewDossierError):
                dossier_from_linked_handoff(h, item_id=malformed)
        partial = fixture()
        partial["status"] = "SOURCE_REVISIONS_PENDING_NO_GO"
        partial["pending_source_revisions"] = 1
        partial["source_revisions"] += 1
        d = dossier_from_linked_handoff(partial, item_id=item)
        self.assertEqual(d["status"], INCOMPLETE)
        self.assertIsNone(d["item"])
        self.assertFalse(d["source_linkage_checked"])
        forged = fixture()
        forged["tasks"][0]["approval"] = True
        with self.assertRaises(PolicyError):
            dossier_from_linked_handoff(forged, item_id=item)

    def test_unknown_blocker_masked_untrusted_guidance_never_displayed(self):
        h = fixture()
        h["tasks"][0]["blocking_reasons"].append("UNTRUSTED_NEW_BLOCKER_PRIVATE")
        h["tasks"][0]["safe_guidance_for_review"] = "UPSTREAM_EXECUTE_THIS_TEXT"
        d = dossier_from_linked_handoff(h, item_id=first_item(h))
        html = render_review(d)
        self.assertNotIn("UNTRUSTED_NEW_BLOCKER_PRIVATE", html)
        self.assertNotIn("UPSTREAM_EXECUTE_THIS_TEXT", html)
        self.assertIn("추가 검증 사유", html)
        self.assertIn("SOURCE_LINKAGE_ONLY_NOT_FIX_VERIFIED", html)
        self.assertIn("NOT_VERIFIED", html)
        self.assertNotIn("PASS", html)

    def test_http_actual_search_dossier_return_and_compare_regression(self):
        h = fixture()
        filtered = explore_linked_public_candidates(
            h, query="Python", domain="Python", limit=5, page=2)
        self.assertEqual(len(filtered["items"]), 4)
        ident = filtered["items"][0]["library_item_id"]
        params = urlencode({
            "q": "Python", "domain": "Python",
            "source": "", "kind": "", "limit": "5", "page": "2",
        })
        with ui(h) as base:
            with urlopen(base + "/", timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn("V0.4", resp.read().decode())
            with urlopen(base + "/?" + params, timeout=5) as resp:
                page = resp.read().decode()
                self.assertEqual(resp.status, 200)
                self.assertIn("2/2", page)
                self.assertIn("검증 준비표", page)
                self.assertIn("비교 선택", page)
                self.assertIn("V0.4", page)
                review_href = re.search(
                    r'href="(/review/' + ident + r'[^"]*)"', page).group(1)
            with urlopen(base + unescape(review_href), timeout=5) as resp:
                review = resp.read().decode()
                self.assertEqual(resp.status, 200)
                self.assertIn("후보별 공개 근거 검증 준비표", review)
                self.assertIn("VERSION_APPLICABILITY", review)
                self.assertIn("LICENSE", review)
                self.assertIn("INDEPENDENT_REGRESSION", review)
                self.assertIn("NOT_VERIFIED", review)
                self.assertIn(ident, review)
                back = re.search(
                    r'<a href="([^"]+)">선택했던 검색 결과로 돌아가기</a>',
                    review).group(1)
            with urlopen(base + unescape(back), timeout=5) as resp:
                back_page = resp.read().decode()
                self.assertIn("2/2", back_page)
                self.assertIn("검증 준비표", back_page)
                self.assertIn('value="Python"', back_page)
            picked = tuple(r["library_item_id"] for r in filtered["items"][:2])
            compare_url = "/compare?" + urlencode(
                [("item", x) for x in picked] + list({
                    "q": "Python", "domain": "Python", "source": "", "kind": "",
                    "limit": "5", "page": "2",
                }.items()))
            with urlopen(base + compare_url, timeout=5) as resp:
                compare_html = resp.read().decode()
                self.assertIn("선택했던 검색 결과로 돌아가기", compare_html)
                self.assertIn("후보 2", compare_html)
            with urlopen(base + "/item/" + ident, timeout=5) as resp:
                self.assertIn("근거 후보 상세", resp.read().decode())
            with urlopen(base + "/health", timeout=5) as resp:
                receipt = json.load(resp)
                self.assertEqual(receipt["schema"], SCHEMA)
                self.assertEqual(receipt["db_writes"], 0)
                self.assertFalse(receipt["auto_promoted"])

    def test_http_denials_and_no_mutation(self):
        h = fixture()
        ident = first_item(h)
        with ui(h) as base:
            for path in (
                "/review/" + "f"*64, "/review/nothex",
                "/review/" + ident + "?q=%3Cscript%3E",
                "/review/" + ident + "?q=x&q=y",
                "/review/" + ident + "?return=https://evil.test",
            ):
                with self.subTest(path=path), self.assertRaises(HTTPError) as e:
                    urlopen(base + path, timeout=5)
                self.assertIn(e.exception.code, (400, 404))
            with self.assertRaises(HTTPError) as e:
                urlopen(Request(base + "/", data=b"write", method="POST"), timeout=5)
            self.assertEqual(e.exception.code, 405)
            with self.assertRaises(HTTPError) as e:
                urlopen(Request(base + "/review/" + ident,
                                headers={"Host": "attack.example"}), timeout=5)
            self.assertEqual(e.exception.code, 403)

    def test_existing_handoff_refuses_fake_approved_and_partial(self):
        h = fixture()
        id1 = first_item(h)
        with ui(h) as base:
            h["tasks"][0]["approval"] = True
            with self.assertRaises(HTTPError) as e:
                urlopen(base + "/review/" + id1, timeout=5)
            self.assertEqual(e.exception.code, 503)
            self.assertEqual(e.exception.read(), b"SOURCE_VALIDATION_FAILED_NO_GO")


if __name__ == "__main__":
    unittest.main()
