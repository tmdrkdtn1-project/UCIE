"""UCIE V04 customer-facing dark UI contracts, no operating I/O."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as app
from ucie_miner.local_v1_design_v04 import (
    NAV, PAGE_NAMES, STYLE, NESTED_STYLE, render_shell, skin_nested_local_page,
)
from ucie_miner.skillbook_catalog_union_v01 import SCHEMA as FEDERATED_SCHEMA
from ucie_miner.public_collection_inventory_v01 import SCHEMA as INVENTORY_SCHEMA


class PublicText(HTMLParser):
    """Extract only visually open text, excluding CSS and closed details."""
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("style", "script") or (
                tag == "details" and "open" not in attrs) or (
                "visually-hidden" in attrs.get("class", "").split()):
            self.hidden += 1
        elif self.hidden:
            self.hidden += 1

    def handle_endtag(self, tag):
        if self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def visible_text(html: str) -> str:
    p = PublicText()
    p.feed(html)
    return " ".join(p.parts)


class PremiumDarkCustomerV04Tests(unittest.TestCase):
    def test_home_is_dark_smooth_customer_navigation(self):
        page = app._home()
        text = visible_text(page)
        self.assertIn('name="color-scheme" content="dark"', page)
        self.assertIn("더 좋은 코드를 위한", text)
        self.assertIn("더 나은 선택.", text)
        for name in ("문제 예방", "개발 도구", "라이브러리", "개선 제안"):
            self.assertIn(name, text)
        self.assertEqual(page.count('class="pillar-card"'), 4)
        self.assertIn('action="/local/error" method="get"', page)
        for forbidden in (
                "OWNER", "READ ONLY", "로컬 V1 실제 사용자 작업",
                "온라인·고객 출시 보류", "고객 출시", "운영 원장",
                "개발단", "UCIE LOCAL V1", "소유자 인수"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_all_existing_routes_keep_active_accessible_customer_labels(self):
        self.assertEqual(len(NAV), 6)
        for original, (customer, _, _) in PAGE_NAMES.items():
            with self.subTest(original=original):
                page = app._page(original, "<section>샘플</section>")
                self.assertIn("lang=\"ko\"", page)
                self.assertIn('aria-label="주요 기능"', page)
                self.assertIn('href="#workspace"', page)
                self.assertIn('id="workspace" tabindex="-1"', page)
                self.assertIn(customer, visible_text(page))
                html = page.split('</style>', 1)[1]
                self.assertEqual(html.count('aria-current="page"'), 1)
                self.assertNotIn("온라인·고객 출시 보류", visible_text(page))
                self.assertNotIn("LOCAL · 127.0.0.1", visible_text(page))
        for bad in ("NON_UCIE", "이상한 페이지"):
            with self.assertRaises(ValueError):
                render_shell(bad, "", app.ROUTES)
        with self.assertRaises(ValueError):
            render_shell("시작", "", app.ROUTES + (("/unknown", "", ""),))

    def test_evidence_card_discloses_unverified_and_has_safe_details(self):
        row = {
            "public_url": "https://github.com/python/cpython/pull/155365",
            "source_id": "repo:python/cpython", "domain": "PYTHON",
            "version_scope_claim": "UNDETERMINED",
            "purpose_code": "PY_SCANDIR_SHARED_ITERATOR_RACE",
            "evidence_sha256": "a" * 64,
            "library_item_id": "b" * 64,
        }
        page = app._evidence_rows({"items": [row]}, guidance=True, query="scandir")
        self.assertIn('class="evidence-properties"', page)
        self.assertIn('class="technical-details"', page)
        self.assertIn("UNVERIFIED_CANDIDATE_ONLY", page)
        self.assertIn("<summary>출처·버전·기술 정보 보기</summary>", page)
        self.assertIn("검토 전", visible_text(page))
        self.assertIn("개선 방향 살펴보기", visible_text(page))
        self.assertNotIn("UNVERIFIED_CANDIDATE_ONLY", visible_text(page))
        self.assertNotIn("a" * 64, visible_text(page))
        self.assertIn("github.com/python/cpython/pull/155365", page)
        self.assertIn('/local/review?q=scandir&amp;page=1', page)

    def test_error_search_and_help_do_not_show_dev_release_gates(self):
        error = app._error(Path("UCIE"), "")
        policy = app._policy()
        self.assertIn("문제 예방 자료 검색", visible_text(error))
        self.assertIn('name="q" maxlength="80"', error)
        self.assertIn("UCIE는 어떤 서비스인가요?", visible_text(policy))
        self.assertIn("자료는 어떻게 활용하나요?", visible_text(policy))
        for html in (error, policy):
            text = visible_text(html)
            self.assertNotIn("LG6_OWNER_HOST_SIGNOFF_RECEIPT", text)
            self.assertNotIn("온라인·고객 출시 보류", text)
            self.assertNotIn("소유자 인수", text)
            self.assertNotIn('method="post"', html.lower())

    def test_library_shelves_are_human_labels_not_internal_catalog(self):
        catalog = {
            "schema": FEDERATED_SCHEMA,
            "status": "READ_ONLY_TWO_SHELF_DRAFT_NOT_APPROVED",
            "public_shelf_status": "NOT_REQUESTED",
            "public_evidence_candidates": [],
            "human_approved": False, "export_allowed": False,
            "approved_packages": 0, "network_requests": 0,
            "operating_database_writes": 0,
            "skillbooks": [], "editorial_review_candidates": [],
        }
        with patch("ucie_miner.skillbook_catalog_union_v01.search_federated", return_value=catalog), \
                patch.object(app, "_paged_evidence", return_value="<section>자료 없음</section>"):
            html = app._library(Path("UCIE"), "q=Git")
        t = visible_text(html)
        for name in ("기술 가이드", "검토 중인 자료", "공개 기술 사례"):
            self.assertIn(name, t)
        self.assertNotIn("SHELF / 03", t)
        self.assertNotIn("로컬", t)

    def test_engine_choices_are_friendly_but_real_recipe_ids_unchanged(self):
        html = app._engine("")
        t = visible_text(html)
        for name in ("증분 빌드 실험", "테스트 탐색 도구",
                     "피드백 분석 예제", "기술 자료 검색 비교"):
            self.assertIn(name, t)
        self.assertIn("purpose=SKILL_TEST_AUTOMATION", html)
        self.assertNotIn("REAL_PUBLIC_CATALOG", t)
        self.assertIn('class="recipe-list"', html)

    def test_evolution_inventory_internal_metrics_are_not_first_screen(self):
        receipt = {
            "schema": INVENTORY_SCHEMA, "status": "READ_ONLY_OK",
            "operating_database_writes": 0, "issues": [],
            "captured_utc": "2026-11-09",
            "legacy_miner": {"candidates": 4},
            "stage10_public_candidate_staging": {"candidate_revisions": 2},
        }
        with patch("ucie_miner.public_collection_inventory_v01.collection_inventory",
                   return_value=receipt), \
                patch.object(app, "_paged_evidence", return_value=""):
            html = app._evolution(Path("UCIE"), "")
        self.assertIn("개선 아이디어 찾아보기", visible_text(html))
        self.assertNotIn("Stage10", visible_text(html))
        self.assertIn("Stage10 개정: 2", html)

    def test_dark_palette_responsiveness_and_static_assets(self):
        for value in ("#08090c", "#14161b", "#f4f5f8"):
            self.assertIn(value, STYLE)
        self.assertIn("border-radius:22px", STYLE)
        self.assertIn("max-width:640px", STYLE)
        self.assertIn("prefers-reduced-motion:reduce", STYLE)
        self.assertIn(":focus-visible", STYLE)
        self.assertIn("color-scheme:dark", STYLE)
        self.assertIn('background:#17191f', STYLE)
        for disallowed in ("@import", "url(http", "<script"):
            self.assertNotIn(disallowed, STYLE)
            self.assertNotIn(disallowed, NESTED_STYLE)

    def test_nested_catalog_dark_skin_remains_idempotent(self):
        valid = (
            '<!doctype html><html lang="ko"><head><title>UCIE</title></head>'
            '<body><main><header><h1>자료</h1></header><section>검토 중</section>'
            '</main></body></html>'
        )
        once = skin_nested_local_page(valid)
        self.assertEqual(skin_nested_local_page(once), once)
        self.assertIn('data-ucie-nested-theme="v02"', once)
        self.assertIn("background:#0d0e12", once)
        self.assertEqual(once.count("</html>"), 1)
        with self.assertRaises(ValueError):
            skin_nested_local_page("<html>unsafe</html>")


if __name__ == "__main__":
    unittest.main()
