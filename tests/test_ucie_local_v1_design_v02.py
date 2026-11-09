"""UCIE-only offline visual redesign contracts; no network or owner DB."""
from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as app
from ucie_miner.local_v1_design_v02 import PAGE_METADATA, STYLE, render_shell


class LocalVisualDesignTests(unittest.TestCase):
    def test_every_existing_local_page_has_one_shared_accessible_shell(self):
        for title in PAGE_METADATA:
            with self.subTest(title=title):
                doc = app._page(title, '<section><h2>본문</h2></section>')
                self.assertEqual(doc.count('<html'), 1)
                self.assertEqual(doc.count('</html>'), 1)
                self.assertEqual(doc.count('<main '), 1)
                self.assertIn('lang="ko"', doc)
                self.assertIn('href="#workspace"', doc)
                self.assertIn('id="workspace" tabindex="-1"', doc)
                self.assertIn('aria-label="주요 기능"', doc)
                self.assertIn('aria-current="page"', doc)
                self.assertIn('온라인·고객 출시 보류', doc)
                self.assertIn('자동 규칙 승격 없음', doc)

    def test_four_equal_routes_and_real_home_navigation_are_visible(self):
        doc = app._home()
        self.assertEqual(doc.count('class="pillar-card"'), 4)
        for href, title, _ in app.ROUTES:
            self.assertIn('<a class="pillar-card" href="' + href + '">', doc)
            self.assertIn(title, doc)
        self.assertIn('로컬 V1 실제 사용자 작업', doc)
        self.assertIn('출처 연결 ≠ 독립 검증', doc)
        self.assertIn('소유자 인수 완료 · 로컬 한정', doc)
        self.assertNotIn('독립 검증 완료', doc)
        self.assertNotIn('고객 출시 승인', doc)

    def test_active_navigation_follows_secondary_workflows(self):
        cases = (
            ('시작', '/local'),
            ('오류 예방', '/local/error'),
            ('후보 검토 작업', '/local/error'),
            ('개발 엔진·스킬', '/local/engine'),
            ('통합 가상도서관', '/local/library'),
            ('SkillBook 실행 결과', '/local/library'),
            ('근거 기반 개선', '/local/evolution'),
            ('개발 규칙', '/local/policy'),
        )
        for title, route in cases:
            with self.subTest(title=title):
                doc = app._page(title, '')
                self.assertIn('href="' + route + '" aria-current="page"', doc)
                self.assertEqual(doc.count('aria-current="page"'), 1)

    def test_no_remote_assets_scripts_or_mutating_actions_in_shell(self):
        doc = app._home()
        self.assertNotIn('<script', doc)
        self.assertNotIn('<iframe', doc)
        self.assertNotIn('method="post"', doc.lower())
        self.assertNotIn('<link rel="stylesheet"', doc)
        self.assertNotIn('https://fonts.', doc)
        self.assertNotIn('http://', doc)
        self.assertNotIn('https://', doc)
        self.assertIn('LOCAL · 127.0.0.1', doc)

    def test_responsive_focus_reduced_motion_and_contrast_contract(self):
        self.assertIn('@media (max-width:880px)', STYLE)
        self.assertIn('@media (max-width:640px)', STYLE)
        self.assertIn('prefers-reduced-motion:reduce', STYLE)
        self.assertIn(':focus-visible', STYLE)
        self.assertIn('.skip-link:focus', STYLE)
        self.assertIn('.pillar-grid', STYLE)
        self.assertIn('.trust-panel', STYLE)
        self.assertNotIn('@import', STYLE)

    def test_existing_readonly_search_and_selection_forms_stay_intact(self):
        error = app._error(Path("UCIE"), "")
        self.assertIn('action="/local/error" method="get"', error)
        self.assertIn('name="q" maxlength="80"', error)
        self.assertIn('UNVERIFIED', error.upper() if 'UNVERIFIED' in error.upper() else app._home())
        self.assertNotIn('method="post"', error.lower())
        self.assertIn('워크스페이스', error)

    def test_unknown_page_and_new_public_path_fail_closed(self):
        with self.assertRaises(ValueError):
            render_shell('OTHER_PROJECT', '', app.ROUTES)
        forged = app.ROUTES + (
            ('/unknown', '외부', '허용되지 않은 경로'),
        )
        with self.assertRaises(ValueError):
            render_shell('시작', '', forged)

    def test_rendered_metadata_is_not_an_accuracy_or_release_claim(self):
        doc = app._home()
        self.assertNotIn('1,008', doc)
        self.assertIn('미승인', doc)
        self.assertIn('출시 보류', doc)
        self.assertIn('/local/policy', doc)
        self.assertNotIn('AUTO_APPROVED', doc)


if __name__ == '__main__':
    unittest.main()
