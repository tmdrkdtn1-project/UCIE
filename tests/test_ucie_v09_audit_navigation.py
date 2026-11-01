"""UCIE V0.9 owner-reported defect: zero receipts hid 588 real candidates.

Synthetic end-to-end localhost navigation with zero V0.5 receipts, source
and domain filters, bounded pages and explicit owner-clicked public lookup.
All candidate identities originate from the validated Stage10/12/15 handoff.
"""
from __future__ import annotations

from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import re
import unittest

from test_ucie_library_v02 import fixture
from test_ucie_public_proof_v09 import (
    browser, checked_json, synthetic_root,
)
from ucie_miner.library_explore import explore_linked_public_candidates
from ucie_miner.library_public_proof_v09 import perform_public_probe_batch
from ucie_miner.library_audit_v07 import audit_handoff_receipts
from ucie_miner.library_browser_v09 import (
    AUDIT_LIST_PAGE_SIZE, _audit_listing_query,
    render_audit_dashboard_with_picker,
    render_audit_candidate_listing,
)


class AuditCandidatePickerRegression(unittest.TestCase):
    def test_zero_receipts_still_shows_all_candidates_and_five_source_preview(self):
        h = fixture()
        report = audit_handoff_receipts(h, [])
        self.assertEqual(report["candidate_count_with_claims"], 0)
        self.assertEqual(report["source_linked_candidates"], 26)
        dashboard = render_audit_dashboard_with_picker(report)
        self.assertIn("공개 후보 선택 · 전체 원장", dashboard)
        self.assertIn("전체 공개 후보 목록 열기", dashboard)
        self.assertIn('href="/audit/candidates"', dashboard)
        self.assertEqual(dashboard.count('href="/audit/item/'), 5)
        self.assertGreaterEqual(
            len(set(re.findall(
                r'<li><a href="/audit/item/[0-9a-f]{64}">([^·<]+)',
                dashboard))), 3)
        self.assertIn("원장에 결속된 공개 후보", dashboard)
        self.assertIn("AUDIT_REVIEW_REQUIRED_NO_GO", dashboard)
        self.assertIn("NOT_VERIFIED", dashboard)
        self.assertNotIn("OWNER_APPROVED", dashboard)

    def test_page_1_and_2_cover_every_eligible_candidate_without_duplicates(self):
        h = fixture()
        report = audit_handoff_receipts(h, [])
        first = render_audit_candidate_listing(report, page=1)
        second = render_audit_candidate_listing(report, page=2)
        self.assertIn("페이지 1 / 2", first)
        self.assertIn("다음 페이지", first)
        self.assertIn("페이지 2 / 2", second)
        self.assertIn("이전 페이지", second)
        hits1 = re.findall(r'href="/audit/item/([0-9a-f]{64})"', first)
        hits2 = re.findall(r'href="/audit/item/([0-9a-f]{64})"', second)
        self.assertEqual(len(hits1), AUDIT_LIST_PAGE_SIZE)
        self.assertEqual(len(hits2), 6)
        self.assertEqual(len(set(hits1 + hits2)), 26)
        self.assertIn('method="get"', first)
        self.assertIn('name="source"', first)
        self.assertIn('name="domain"', first)
        self.assertIn("후보 검토하기", first)
        self.assertIn("외부 공개 GitHub 조회는", first)
        python = render_audit_candidate_listing(
            report, source="repo:python/cpython", domain="Python", page=1)
        self.assertEqual(len(re.findall(r'href="/audit/item/[0-9a-f]{64}"',
                                        python)), 9)
        self.assertIn('value="repo:python/cpython" selected', python)
        self.assertIn('value="Python" selected', python)
        empty = render_audit_candidate_listing(
            report, source="repo:git/git", domain="Python", page=1)
        self.assertIn("조건에 맞는 후보가 없습니다", empty)

    def test_strict_filters_reject_tricks_and_unsafe_pagination(self):
        for query in (
            "source=repo:unknown/unknown",
            "page=0", "page=51", "page=0001", "page=-1",
            "page=1&page=2", "kind=SECRET", "source=%3Cscript%3E",
            "domain=Python&domain=Git", "next=https://evil.test",
            "source=repo%3Apython%2Fcpython&page=2&page=3",
            "q=" + "X" * 400,
        ):
            with self.subTest(query=query), self.assertRaises(ValueError):
                _audit_listing_query(query)
        self.assertEqual(_audit_listing_query(""), ("", "", 1))
        self.assertEqual(_audit_listing_query(
            "source=repo%3Apython%2Fcpython&domain=Python&page=2"),
            ("repo:python/cpython", "Python", 2))

    def test_full_windows_like_http_click_from_zero_claims_to_live_result(self):
        h = fixture()
        actual_candidates = explore_linked_public_candidates(h, limit=20)["items"]
        calls = []

        def fake_external(root, *, item_id, top):
            calls.append((item_id, top))
            with synthetic_root() as local:
                return perform_public_probe_batch(
                    local, item_id=item_id, top=top,
                    handoff_factory=lambda root: h,
                    receipt_reader=lambda path: [],
                    fetch_json=checked_json)
        with browser(h, fake_external) as base:
            with urlopen(base + "/audit", timeout=5) as r:
                dashboard = r.read().decode("utf-8")
                self.assertEqual(r.status, 200)
                self.assertIn("공개 후보 선택", dashboard)
                self.assertIn("전체 공개 후보 목록 열기", dashboard)
            self.assertEqual(calls, [])
            with urlopen(base + "/audit/candidates", timeout=5) as r:
                listing = r.read().decode("utf-8")
                self.assertEqual(r.status, 200)
                self.assertIn("후보 검토하기", listing)
                self.assertIn("페이지 1 / 2", listing)
            self.assertEqual(calls, [])
            found = re.search(
                r'<a href="/audit/item/([0-9a-f]{64})">후보 검토하기</a>',
                listing)
            self.assertIsNotNone(found)
            item = found.group(1)
            self.assertIn(item, {x["library_item_id"]
                                 for x in actual_candidates})
            with urlopen(base + "/audit/item/" + item, timeout=5) as r:
                details = r.read().decode("utf-8")
                self.assertIn("오류 예방 검토 초안", details)
                self.assertIn("공개 원본 SHA 대조 실행", details)
                self.assertIn('href="/public-check/' + item + '"', details)
            self.assertEqual(calls, [])
            with urlopen(base + "/public-check/" + item, timeout=5) as r:
                probe = r.read().decode("utf-8")
                self.assertEqual(r.status, 200)
                self.assertIn("공개 원본 대조 결과", probe)
                self.assertIn("PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED", probe)
                self.assertIn("NOT_VERIFIED", probe)
                self.assertIn("검증 완료 규칙: 0", probe)
            self.assertEqual(calls, [(item, 1)])
            with urlopen(base + "/audit/candidates?page=2", timeout=5) as r:
                self.assertIn("페이지 2 / 2", r.read().decode("utf-8"))
            filt = urlencode({
                "source": "repo:python/cpython", "domain": "Python",
                "page": "1"})
            with urlopen(base + "/audit/candidates?" + filt, timeout=5) as r:
                page = r.read().decode("utf-8")
                self.assertIn("후보 선택 · 9건 / 전체 26건", page)
            self.assertEqual(calls, [(item, 1)])
            for wrong in (
                "/audit?go=evil", "/audit/candidates?source=repo:private/repo",
                "/audit/candidates?page=0",
                "/audit/candidates?page=1&page=2",
                "/audit/candidates?redirect=https://evil.test",
            ):
                with self.subTest(wrong=wrong), self.assertRaises(HTTPError) as e:
                    urlopen(base + wrong, timeout=5)
                self.assertEqual(e.exception.code, 400)
            with self.assertRaises(HTTPError) as e:
                urlopen(Request(base + "/audit/candidates",
                                data=b"write", method="POST"), timeout=5)
            self.assertEqual(e.exception.code, 405)
            with self.assertRaises(HTTPError) as e:
                urlopen(Request(base + "/audit/candidates",
                                headers={"Host": "evil.test"}), timeout=5)
            self.assertEqual(e.exception.code, 403)
            self.assertEqual(calls, [(item, 1)])


if __name__ == "__main__":
    unittest.main()
