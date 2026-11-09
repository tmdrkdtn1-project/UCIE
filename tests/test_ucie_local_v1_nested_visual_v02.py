"""CSS-only nested UCIE Library/SkillBook visual parity; no owner IO."""
from __future__ import annotations

import unittest

from ucie_miner import local_v1_app_v01 as app
from ucie_miner.local_v1_design_v02 import (
    LEGACY_STYLE, skin_nested_local_page,
)
from ucie_miner.skillbook_catalog_union_v01 import (
    preview_skillbook_qa_plan, render_skillbook_qa_plan,
)


class NestedVisualParityTests(unittest.TestCase):
    def test_real_existing_skillbook_qa_html_gets_one_local_theme(self):
        old = render_skillbook_qa_plan(preview_skillbook_qa_plan())
        self.assertIn('UCIE', old)
        new = skin_nested_local_page(old)
        self.assertEqual(new.count('data-ucie-nested-theme="v02"'), 1)
        self.assertIn('<style data-ucie-nested-theme="v02">', new)
        self.assertIn('실행하지 않은 QA 계획', new)
        self.assertIn('브라우저 조회만으로 시험을 실행', new)
        self.assertIn('독립 QA 미검증', new)
        self.assertEqual(new.count('<html'), 1)
        self.assertEqual(new.count('</html>'), 1)

    def test_nested_re_skin_is_idempotent(self):
        old = render_skillbook_qa_plan(preview_skillbook_qa_plan())
        once = skin_nested_local_page(old)
        self.assertEqual(skin_nested_local_page(once), once)

    def test_only_safe_full_html_envelope_is_accepted(self):
        for bad in ('', '{}', '<section>no head</section>',
                    '<html><head></head></html>',
                    '<!doctype html><html><head></head></html>',
                    '<!doctype html><html><head></head></html></html>'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                skin_nested_local_page(bad)

    def test_nested_style_has_no_scripts_remote_fonts_or_network(self):
        self.assertIn('nav[data-ucie-local-nav="true"]', LEGACY_STYLE)
        self.assertIn('@media(max-width:760px)', LEGACY_STYLE)
        self.assertIn('prefers-reduced-motion:reduce', LEGACY_STYLE)
        self.assertIn(':focus-visible', LEGACY_STYLE)
        self.assertNotIn('@import', LEGACY_STYLE)
        self.assertNotIn('url(', LEGACY_STYLE)
        self.assertNotIn('<script', LEGACY_STYLE)

    def test_main_four_pillar_pages_remain_distinct_from_legacy(self):
        home = app._home()
        self.assertIn('class="app-shell"', home)
        self.assertNotIn('data-ucie-nested-theme="v02"', home)
        for href, _, _ in app.ROUTES:
            self.assertIn(href, home)


if __name__ == "__main__":
    unittest.main()
