"""UCIE V03 Evidence Workbench: visual/semantic contracts, UCIE-only.

No network, scheduler, source execution, owner files or rule promotion.
Full browser responsive acceptance remains a separate observation.
"""
from __future__ import annotations

from pathlib import Path
import unittest

from ucie_miner import local_v1_app_v01 as app
from ucie_miner.local_v1_design_v03 import (
    LEGACY_STYLE, PAGE_METADATA, STYLE, render_shell, skin_nested_local_page,
)
from ucie_miner.skillbook_catalog_union_v01 import (
    preview_skillbook_qa_plan, render_skillbook_qa_plan,
)


class EvidenceWorkbenchV03Tests(unittest.TestCase):
    def test_home_is_task_index_not_ai_marketing_card_wall(self):
        page = app._home()
        self.assertIn('class="intro-workbench"', page)
        self.assertIn('class="quick-query"', page)
        self.assertIn('class="pillar-grid"', page)
        self.assertEqual(page.count('class="pillar-card"'), 4)
        self.assertNotIn('class="hero-visual"', page)
        self.assertNotIn('class="hero-core"', page)
        self.assertNotIn('radial-gradient', page)
        self.assertNotIn('linear-gradient', page)
        self.assertIn('더 좋은 코드를 위한', page)
        self.assertIn('더 나은 선택.', page)
        self.assertIn('주요 기능', page)
        self.assertIn('자료를 살펴보실 때', page)
        self.assertNotIn('온라인·고객 출시 보류', page)
        self.assertIn('action="/local/error" method="get"', page)
        self.assertNotIn('<script', page)
        self.assertNotIn('method="post"', page.lower())
        for route, _, _ in app.ROUTES:
            with self.subTest(route=route):
                self.assertIn('<a class="pillar-card" href="' + route + '">', page)
        for name in ("문제 예방", "개발 도구", "라이브러리", "개선 제안"):
            self.assertIn(name, page)

    def test_workbench_routes_have_accessible_nav_and_closed_scope(self):
        for title in PAGE_METADATA:
            with self.subTest(title=title):
                html = app._page(title, '<section>검토</section>')
                self.assertIn('lang="ko"', html)
                self.assertIn('UCIE · ', html)
                self.assertEqual(html.count('<main '), 1)
                self.assertIn('id="workspace" tabindex="-1"', html)
                self.assertIn('href="#workspace"', html)
                self.assertIn('aria-label="주요 기능"', html)
                self.assertNotIn('LOCAL · 127.0.0.1', html)
                self.assertNotIn('온라인·고객 출시 보류', html)
                self.assertIn('자료 이용 안내', html)
                content = html.split('</style>', 1)[1]
                self.assertEqual(content.count('aria-current="page"'), 1)
        with self.assertRaises(ValueError):
            render_shell('시작', '', app.ROUTES + (('/unknown', '', ''),))
        with self.assertRaises(ValueError):
            render_shell('UNKNOWN', '', app.ROUTES)

    def test_evidence_metadata_is_grouped_and_never_approved(self):
        row = {
            "public_url": "https://github.com/python/cpython/pull/155365",
            "source_id": "repo:python/cpython",
            "domain": "PYTHON",
            "version_scope_claim": "UNDETERMINED",
            "purpose_code": "PY_SCANDIR_SHARED_ITERATOR_RACE",
            "evidence_sha256": "a" * 64,
            "library_item_id": "b" * 64,
        }
        content = app._evidence_rows(
            {"items": [row]}, guidance=True, query="scandir", page=1,
        )
        self.assertIn('class="evidence-properties"', content)
        self.assertIn('class="evidence-title"', content)
        self.assertIn('<dt>출처 / 기술</dt>', content)
        self.assertIn('<dt>원본 공개 근거</dt>', content)
        self.assertIn('<dt>적용 버전 주장</dt>', content)
        self.assertIn('<dt>근거 SHA-256</dt>', content)
        self.assertIn('UNVERIFIED_CANDIDATE_ONLY', content)
        self.assertIn('/local/review?q=scandir&amp;page=1', content)
        self.assertIn('회귀', content)
        self.assertNotIn('AUTO_APPROVED', content)

    def test_empty_and_incomplete_states_do_not_fabricate_evidence(self):
        empty = app._evidence_rows({"items": []})
        self.assertIn('검색 결과가 없습니다', empty)
        incomplete = app._evidence_rows({
            "status": "SOURCE_LINKAGE_INCOMPLETE_NO_GO",
            "items": [{"public_url": "https://unapproved.invalid"}],
        })
        self.assertIn('출처 연결이 불완전', incomplete)
        self.assertNotIn('https://unapproved.invalid', incomplete)

    def test_engine_has_indexed_selectable_rows_not_mixed_prose(self):
        html = app._engine("")
        self.assertIn('class="recipe-list"', html)
        self.assertIn('class="recipe-copy"', html)
        self.assertIn('REAL_PUBLIC_CATALOG', html)
        self.assertIn('예제 체험', html)
        self.assertNotIn('method="post"', html.lower())

    def test_mobile_and_nested_legacy_readability_are_explicit(self):
        self.assertIn('@media (max-width:880px)', STYLE)
        self.assertIn('@media (max-width:640px)', STYLE)
        self.assertIn('prefers-reduced-motion:reduce', STYLE)
        self.assertIn(':focus-visible', STYLE)
        self.assertIn('.evidence-properties', STYLE)
        self.assertIn('.shelf-title', STYLE)
        self.assertIn('.inventory-grid', STYLE)
        self.assertIn('main table', LEGACY_STYLE)
        self.assertIn('overflow-x:auto', LEGACY_STYLE)
        self.assertIn('@media(max-width:760px)', LEGACY_STYLE)
        self.assertNotIn('linear-gradient', STYLE)
        self.assertNotIn('radial-gradient', STYLE)
        self.assertNotIn('@import', STYLE)
        self.assertNotIn('url(', LEGACY_STYLE)

    def test_nested_pages_keep_data_and_are_not_reskinned_twice(self):
        original = render_skillbook_qa_plan(preview_skillbook_qa_plan())
        first = skin_nested_local_page(original)
        second = skin_nested_local_page(first)
        self.assertEqual(first, second)
        self.assertEqual(first.count('data-ucie-nested-theme="v02"'), 1)
        self.assertIn('실행하지 않은 QA 계획', second)
        self.assertIn('독립 QA 미검증', second)
        self.assertNotIn('linear-gradient', second)
        self.assertNotIn('<script', second)

    def test_search_form_remains_bounded_and_get_only(self):
        html = app._error(Path("UCIE"), "")
        self.assertIn('action="/local/error" method="get"', html)
        self.assertIn('name="q" maxlength="80"', html)
        self.assertIn('검토 상태', html)
        self.assertNotIn('method="post"', html.lower())


if __name__ == "__main__":
    unittest.main()
