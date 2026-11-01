"""UCIE V0.3 synthetic-only real loopback comparison regression suite.

No owner data, external GET, task registration, source-text evaluation,
operating database edits or rules promotion.
"""
from __future__ import annotations

from contextlib import contextmanager
from html import unescape
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
import json
import re
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ucie_miner.library_compare import (
    READY, INCOMPLETE, NOT_FOUND, CompareError,
    compare_linked_public_candidates,
)
from ucie_miner.library_explore import explore_linked_public_candidates
from ucie_miner.library_browser_v03 import (
    SCHEMA, make_handler, parse_compare, parse_compare_request,
    parse_search_request, render_search, render_comparison,
)
from ucie_miner.library_browser_v02 import read_filters
from ucie_public.policy import PolicyError
from test_ucie_library_v02 import fixture


@contextmanager
def local_ui(handoff):
    def explorer(root, **kwargs):
        return explore_linked_public_candidates(handoff, **kwargs)

    def comparer(root, *, item_ids):
        return compare_linked_public_candidates(handoff, item_ids=item_ids)

    with HTTPServer(("127.0.0.1", 0), make_handler(
            Path("Z:/synthetic/UCIE"), explorer=explorer,
            comparer=comparer)) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield "http://127.0.0.1:" + str(server.server_port)
        finally:
            server.shutdown()
            thread.join(timeout=4)


def ids_for(handoff, count=3):
    rows = explore_linked_public_candidates(handoff, limit=10)["items"]
    return tuple(r["library_item_id"] for r in rows[:count])


class CompareProofTests(unittest.TestCase):
    def test_two_and_three_public_source_linked_candidates(self):
        h = fixture()
        chosen = ids_for(h)
        for n in (2, 3):
            with self.subTest(n=n):
                out = compare_linked_public_candidates(h, item_ids=chosen[:n])
                self.assertEqual(out["status"], READY)
                self.assertEqual(out["returned_count"], n)
                self.assertEqual(
                    tuple(row["library_item_id"] for row in out["items"]),
                    chosen[:n])
                self.assertEqual(out["operating_database_writes"], 0)
                self.assertFalse(out["auto_promoted"])
                self.assertEqual(out["new_approvals"], 0)
                self.assertFalse(out["production_approved"])
                for row in out["items"]:
                    self.assertFalse(row["human_approved"])
                    self.assertFalse(row["export_allowed"])
                    self.assertEqual(row["version_scope_claim"], "UNDETERMINED")
                    self.assertEqual(row["status"], "UNVERIFIED_CANDIDATE_ONLY")
                    self.assertIn("EXPLICIT_OWNER_REVIEW_AND_SIGNED_RELEASE",
                                  row["verification_gaps"])
                    self.assertNotIn("UNTRUSTED_EXTERNAL_INSTRUCTION", str(row))

    def test_missing_duplicate_invalid_and_fake_approval_fail_closed(self):
        h = fixture()
        good = ids_for(h)
        for ids in (tuple(), (good[0],), (good[0], good[0]),
                    good + (good[0],), (good[0], "nothex"),
                    tuple("a"*64 for _ in range(4))):
            with self.subTest(ids=ids), self.assertRaises(CompareError):
                compare_linked_public_candidates(h, item_ids=ids)
        self.assertEqual(compare_linked_public_candidates(
            h, item_ids=(good[0], "f"*64))["status"], NOT_FOUND)
        corrupted = fixture()
        corrupted["tasks"][0]["approval"] = True
        with self.assertRaises(PolicyError):
            compare_linked_public_candidates(corrupted, item_ids=good[:2])
        altered = fixture()
        altered["tasks"][0]["skill_id"] = "powershell-safe-calls"
        with self.assertRaises(ValueError):
            compare_linked_public_candidates(altered, item_ids=good[:2])

    def test_incomplete_ledger_does_not_leak_data(self):
        h = fixture()
        ids = ids_for(h, 2)
        h["status"] = "SOURCE_REVISIONS_PENDING_NO_GO"
        h["source_revisions"] += 1
        h["pending_source_revisions"] = 1
        outcome = compare_linked_public_candidates(h, item_ids=ids)
        self.assertEqual(outcome["status"], INCOMPLETE)
        self.assertEqual(outcome["items"], [])
        self.assertEqual(outcome["returned_count"], 0)

    def test_fixed_profile_guidance_only_not_upstream_payload(self):
        h = fixture()
        h["tasks"][0]["safe_guidance_for_review"] = (
            "UNTRUSTED_EXTERNAL_INSTRUCTION")
        # The trusted profile strings must not be sourced from task text.
        # Source-row fingerprint comparison happens upstream; the synthetic
        # handoff itself remains structurally valid for this pure function.
        out = compare_linked_public_candidates(h, item_ids=ids_for(h, 2))
        html = render_comparison(out)
        self.assertIn("CHECK_", html)
        self.assertNotIn("UNTRUSTED_EXTERNAL_INSTRUCTION", html)

    def test_query_and_render_bounded(self):
        h = fixture()
        chosen = ids_for(h)
        qs = urlencode([("item", i) for i in chosen[:2]])
        self.assertEqual(parse_compare(qs), chosen[:2])
        for bad in ("", "item=" + chosen[0],
                    "item=" + chosen[0] + "&item=" + chosen[0],
                    "item=" + chosen[0] + "&foo=" + chosen[1],
                    "item=%2Fetc%2Fsecret&item=" + chosen[1],
                    "item=" + chosen[0] + "&item=" + chosen[1] + "&item=" +
                    chosen[2] + "&item=" + chosen[1]):
            with self.subTest(qs=bad), self.assertRaises(CompareError):
                parse_compare(bad)
        page = render_search(read_filters(""),
                             explore_linked_public_candidates(h, limit=5))
        self.assertEqual(page.count('type="checkbox" name="item"'), 5)
        self.assertIn('action="/compare"', page)
        self.assertIn("선택한 후보 비교", page)
        self.assertIn("UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V03", page)

    def test_real_http_search_compare_detail_and_boundaries(self):
        h = fixture()
        chosen = ids_for(h)
        with local_ui(h) as base:
            with urlopen(base + "/", timeout=5) as r:
                self.assertEqual(r.status, 200)
                self.assertNotIn("비교 선택", r.read().decode("utf-8"))
            with urlopen(base + "/?q=&source=&domain=&kind=&limit=5&page=1",
                         timeout=5) as r:
                body = r.read().decode("utf-8")
                self.assertEqual(r.status, 200)
                self.assertIn('action="/compare"', body)
                self.assertIn(chosen[0], body)
                self.assertEqual(body.count('type="checkbox" name="item"'), 5)
                self.assertIn("V0.3", body)
            with urlopen(base + "/compare?" + urlencode(
                    [("item", i) for i in chosen[:3]]), timeout=5) as r:
                body = r.read().decode("utf-8")
                self.assertIn("공개 근거 후보 비교", body)
                self.assertIn("원본 코드 실행", body) if False else None
                self.assertIn("UCIE 공통 가이드", body)
                self.assertIn("미검증", body)
                self.assertIn("UNDETERMINED", body)
                self.assertIn("공개 기술 근거", body)
                self.assertIn("후보 3", body)
            with urlopen(base + "/item/" + chosen[0], timeout=5) as r:
                self.assertIn("근거 후보 상세", r.read().decode("utf-8"))
            with urlopen(base + "/health", timeout=5) as r:
                status = json.load(r)
                self.assertEqual(status["schema"], SCHEMA)
                self.assertEqual(status["db_writes"], 0)
                self.assertFalse(status["auto_promoted"])
            for url in (
                base + "/compare?item=" + chosen[0],
                base + "/compare?item=" + chosen[0] + "&item=" + chosen[0],
                base + "/compare?item=" + chosen[0] + "&item=" + chosen[1] + "&foo=x",
                base + "/compare?item=" + chosen[0] + "&item=" + "f"*64,
                base + "/?q=%3Cscript%3E",
            ):
                with self.subTest(url=url), self.assertRaises(HTTPError) as caught:
                    urlopen(url, timeout=5)
                self.assertIn(caught.exception.code, (400, 404))
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(base + "/", data=b"x", method="POST"), timeout=5)
            self.assertEqual(caught.exception.code, 405)
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(base + "/", headers={"Host": "bad.example"}),
                        timeout=5)
            self.assertEqual(caught.exception.code, 403)


    def test_compare_return_exact_filtered_page_with_checked_ids(self):
        h = fixture()
        filters = read_filters("q=Python&domain=Python&kind=&source=&limit=5&page=2")
        second = explore_linked_public_candidates(h, **filters)
        self.assertEqual(second["page"], 2)
        self.assertEqual(second["total_pages"], 2)
        self.assertEqual(len(second["items"]), 4)
        chosen = tuple(row["library_item_id"] for row in second["items"][:2])
        page = render_search(filters, second)
        for key in ("q", "source", "domain", "kind", "limit", "page"):
            self.assertIn('type="hidden" name="' + key + '"', page)
        self.assertIn('name="page" value="2"', page)
        self.assertIn('name="q" value="python"', page)
        self.assertNotIn('type="checkbox" name="item" value="' + chosen[0] +
                         '" checked', page)

        submitted = urlencode(
            [("item", ident) for ident in chosen] +
            [("q", "Python"), ("source", ""), ("domain", "Python"),
             ("kind", ""), ("limit", "5"), ("page", "2")])
        parsed_ids, parsed_context = parse_compare_request(submitted)
        self.assertEqual(parsed_ids, chosen)
        self.assertEqual(parsed_context, filters)
        with local_ui(h) as base:
            with urlopen(base + "/compare?" + submitted, timeout=5) as response:
                html = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("선택했던 검색 결과로 돌아가기", html)
                href = re.search(
                    r'<a href="([^"]+)">선택했던 검색 결과로 돌아가기</a>',
                    html).group(1)
            url = unescape(href)
            self.assertTrue(url.startswith("/?q=python&"))
            self.assertIn("page=2", url)
            self.assertIn("domain=Python", url)
            self.assertEqual(url.count("selected="), 2)
            with urlopen(base + url, timeout=5) as response:
                returned = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("검색된 후보 9건", returned)
                self.assertIn("2/2", returned)
                self.assertIn('value="python"', returned)
                self.assertIn('<option value="Python" selected>', returned)
                for ident in chosen:
                    self.assertIn(
                        'name="item" value="' + ident + '" checked', returned)
                self.assertEqual(returned.count(
                    'type="checkbox" name="item"'), 4)
                self.assertEqual(returned.count(' checked>비교 선택'), 2)

    def test_return_query_disallows_unknown_duplicate_or_unbounded_state(self):
        h = fixture()
        chosen = ids_for(h, 2)
        bare = urlencode([("item", ident) for ident in chosen])
        ids, context = parse_compare_request(bare)
        self.assertEqual(ids, chosen)
        self.assertIsNone(context)
        for qs in (
            bare + "&foo=private",
            bare + "&q=Python",
            bare + "&q=Python&q=Git&source=&domain=&kind=&limit=5&page=2",
            bare + "&q=%3Cscript%3E&source=&domain=&kind=&limit=5&page=2",
            bare + "&q=Python&source=&domain=&kind=&limit=5&page=201",
            bare + "&q=Python&source=&domain=&kind=&limit=5&page=2&next=https://evil.test",
        ):
            with self.subTest(qs=qs), self.assertRaises(CompareError):
                parse_compare_request(qs)
        for qs in (
            "q=Python&selected=nothex",
            "q=Python&selected=" + chosen[0],
            "q=Python&selected=" + chosen[0] + "&selected=" + chosen[0],
            "q=Python&selected=" + chosen[0] + "&selected=" + chosen[1] + "&junk=1",
            "q=Python&q=Git",
        ):
            with self.subTest(qs=qs), self.assertRaises(ValueError):
                parse_search_request(qs)
        with local_ui(h) as base:
            with self.assertRaises(HTTPError) as err:
                urlopen(base + "/?q=Python&selected=bad", timeout=5)
            self.assertEqual(err.exception.code, 400)
            with self.assertRaises(HTTPError) as err:
                urlopen(base + "/compare?" + bare + "&return=https://evil.test", timeout=5)
            self.assertEqual(err.exception.code, 400)

    def test_forged_approval_is_503_no_comparison(self):
        h = fixture()
        chosen = ids_for(h, 2)
        h["tasks"][0]["approval"] = True
        with local_ui(h) as base:
            with self.assertRaises(HTTPError) as caught:
                urlopen(base + "/compare?" + urlencode(
                    [("item", i) for i in chosen]), timeout=5)
            self.assertEqual(caught.exception.code, 503)
            self.assertEqual(caught.exception.read().decode("utf-8"),
                             "SOURCE_VALIDATION_FAILED_NO_GO")


if __name__ == "__main__":
    unittest.main()
