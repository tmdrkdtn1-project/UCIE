"""G3: REAL isolated Chromium first-use acceptance on the actual UCIE V2 renderer.

Only with UCIE_G3_BROWSER_QA=1 and an explicitly installed first-party
headless Chromium/Playwright runner. Without that opt-in these browser tests
SKIP (not PASS) in the ordinary four-OS/python offline matrix.

A disposable loopback HTTP server delegates existing approved /local GET paths
to the unchanged V04 handler. Its test-only /__ucie_g3_* routes serve
render_preview() in two CSP modes; they do NOT exist in the product server.
No customer files, model, uploads, external source requests, DB or scheduler.
Actual OWNER Edge, human user studies and distribution remain separate gates.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread
from http.server import HTTPServer
import unittest

from ucie_miner import local_v1_app_v01 as owner_local
from ucie_miner.ucie_v2_beginner_preview_v01 import render_preview

REVIEW_PATH = "/__ucie_g3_preview"
LOCKED_PATH = "/__ucie_g3_preview_strict_csp"
FORGED_PATH = "/__ucie_g3_preview_forged_rights"
TEST_ONLY_ROUTES = frozenset((REVIEW_PATH, LOCKED_PATH, FORGED_PATH))
WORKLOAD_SIZES = (320, 390, 768, 1024, 1440)
MODE = "ISOLATED_HEADLESS_CHROMIUM_NOT_OWNER_EDGE"
REQUIRES_EXPLICIT_OPT_IN = os.environ.get("UCIE_G3_BROWSER_QA") == "1"


@unittest.skipUnless(REQUIRES_EXPLICIT_OPT_IN,
                     "G3 browser opt-in required; offline static QA is not browser acceptance")
class IsolatedBrowserG3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.tmp = TemporaryDirectory(prefix="UCIE_G3_BROWSER_ONLY_")
        root = Path(cls.tmp.name) / "UCIE"
        (root / ".git").mkdir(parents=True, exist_ok=True)
        base_handler = owner_local.make_handler(root)

        class IsolatedHandler(base_handler):
            def do_GET(self):
                if self.path not in TEST_ONLY_ROUTES:
                    return super().do_GET()
                html = render_preview()  # Actual PR source: B1->B4 and old route joins
                if self.path == FORGED_PATH:
                    old = '"rights": "NOT_APPROVED"'
                    if html.count(old) != 1:
                        raise ValueError("forged evidence test fixture drift")
                    html = html.replace(old, '"rights": "APPROVED"', 1)
                locked = self.path == LOCKED_PATH
                csp = (
                    "default-src 'none'; style-src 'unsafe-inline'; "
                    "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
                    if locked else
                    "default-src 'none'; script-src 'unsafe-inline'; "
                    "style-src 'unsafe-inline'; base-uri 'none'; "
                    "frame-ancestors 'none'"
                )
                payload = html.encode("utf-8")
                self.send_response(200)
                for key, value in (
                    ("Content-Type", "text/html; charset=utf-8"),
                    ("Content-Length", str(len(payload))),
                    ("Content-Security-Policy", csp),
                    ("Cache-Control", "no-store"),
                    ("X-Content-Type-Options", "nosniff"),
                    ("X-Frame-Options", "DENY"),
                ):
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_):
                return  # no request path, input or customer log

        cls.server = HTTPServer(("127.0.0.1", 0), IsolatedHandler)
        cls.worker = Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.origin = "http://127.0.0.1:" + str(cls.server.server_port)
        cls.pw = sync_playwright().start()
        binary = next((shutil.which(name) for name in
                       ("google-chrome", "google-chrome-stable", "chromium",
                        "chromium-browser") if shutil.which(name)), None)
        if not binary:
            raise RuntimeError("G3 requires installed Chromium/Chrome (NO MOCK)")
        cls.browser = cls.pw.chromium.launch(
            headless=True, executable_path=binary,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        cls.output = Path(os.environ.get("UCIE_G3_OUTPUT_DIR", cls.tmp.name))
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.receipt = {"schema":"UCIE_V2_G3_REAL_CHROMIUM_ACCEPTANCE_V01",
                       "scope":MODE, "browser":cls.browser.version,
                       "source": "UCIE_SOURCE_RENDER_PREVIEW_NO_MOCK",
                       "workload_sizes":list(WORKLOAD_SIZES),
                       "owner_edge_tested":False, "owner_v04_changed":False,
                       "human_study_observations":0,
                       "customer_release_authorized":False,
                       "network_external_requests":0, "tests": []}
        try:
            cls.receipt["git_head_sha"] = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True, timeout=3,
                stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.SubprocessError):
            cls.receipt["git_head_sha"] = "UNVERIFIED_CHECKOUT"

    @classmethod
    def tearDownClass(cls):
        try:
            (cls.output / "g3-browser-receipt.json").write_text(
                json.dumps(cls.receipt, ensure_ascii=False, indent=2,
                           sort_keys=True) + "\n", encoding="utf-8")
        finally:
            cls.browser.close()
            cls.pw.stop()
            cls.server.shutdown()
            cls.server.server_close()
            cls.worker.join(timeout=5)
            cls.tmp.cleanup()

    def setUp(self):
        self.ctx = self.browser.new_context(
            viewport={"width":390,"height":844}, device_scale_factor=1,
            reduced_motion="reduce")
        self.page = self.ctx.new_page()
        self.page_errors = []
        self.external_requests = []
        self.page.on("pageerror", lambda e: self.page_errors.append(str(e)))
        self.page.on("request", lambda r: (
            self.external_requests.append(r.url)
            if not r.url.startswith(self.origin) else None
        ))

    def tearDown(self):
        try:
            self.assertEqual(self.external_requests, [])
            self.receipt["tests"].append(self.id())
        finally:
            self.ctx.close()

    def open_preview(self, route=REVIEW_PATH):
        response = self.page.goto(self.origin + route, wait_until="load")
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 200)
        self.assertTrue(self.page.locator("#stage1").is_visible())
        return self.page

    def select_case(self, case="mcp-prompts"):
        page = self.open_preview()
        page.locator('[data-flow="solve"]').click()
        self.assertEqual(page.locator("#progress").inner_text(), "2 / 3 단계")
        page.locator('[data-issue="' + case + '"]').click()
        self.assertEqual(page.locator("#progress").inner_text(), "3 / 3 단계")
        return page

    def screenshot(self, filename):
        self.page.screenshot(path=str(self.output / filename),
                             full_page=True, animations="disabled")

    def assert_no_horizontal_overflow(self, page, label):
        metrics = page.evaluate("""() => ({
            scroll: document.documentElement.scrollWidth,
            client: document.documentElement.clientWidth,
            inner: window.innerWidth
        })""")
        self.assertLessEqual(metrics["scroll"], metrics["client"] + 2,
                             (label, metrics))

    def test_01_real_b1_mcp_contract_and_b2_to_b4_actions(self):
        page = self.select_case()
        self.assertIn("비슷한 기술 사례", page.locator("#result-title").inner_text())
        self.assertTrue(page.locator("#proof").is_visible())
        page.locator("#proof summary").click()
        self.assertIn("NOT_APPROVED", page.locator("#e-qa").inner_text())
        self.assertIn("NOT_VERIFIED", page.locator("#e-qa").inner_text())
        page.locator('[data-route-case="mcp-prompts"] summary').click()
        self.assertIn("UCIE-CAPSULE-MCP-PROMPTS",
                      page.locator('[data-route-case="mcp-prompts"]').inner_text())
        self.assertIn("CONTRACT_VIOLATION",
                      page.locator('[data-route-case="mcp-prompts"]').inner_text())
        self.assertIn("CONTRACT_MATCH",
                      page.locator('[data-route-case="mcp-prompts"]').inner_text())
        self.assertTrue(page.locator('[data-route-case="mcp-prompts"] a[href="/local/guide/mcp-prompts"]').is_visible())
        self.assertTrue(page.locator('a[href="/local/evolution?q=MCP"]').is_visible())
        self.assertEqual(self.page_errors, [])
        self.screenshot("g3-mcp-390.png")

    def test_16_korean_fonts_are_present_in_real_browser_runner(self):
        matched = subprocess.check_output(
            ["fc-match", "-f", "%{family}", "sans-serif:lang=ko"],
            text=True, timeout=5,
        ).strip()
        self.assertRegex(matched, r"Noto Sans CJK|Noto Sans KR")
        page = self.open_preview()
        self.assertIn("Noto Sans CJK KR",
                      page.locator("html").evaluate(
                          "(e) => getComputedStyle(e).fontFamily"))
        self.assertIn("도움", page.locator("#stage1 h1").inner_text())

    def test_17_secondary_technical_actions_are_disclosed_not_auto_shown(self):
        page = self.select_case()
        case = page.locator('[data-route-case="mcp-prompts"]')
        self.assertTrue(case.locator(
            'a[href="/local/solve?case=mcp-prompts"]').is_visible())
        self.assertTrue(page.evaluate("""() => {
            const safe = document.querySelector(
                '[data-route-case="mcp-prompts"] a[href="/local/solve?case=mcp-prompts"]');
            const other = document.querySelector('#direct-start-actions');
            const proof = document.querySelector('#proof');
            return Boolean((safe.compareDocumentPosition(other) & 4) &&
                           (safe.compareDocumentPosition(proof) & 4));
        }"""))
        details = case.locator('details[data-synthetic-details="mcp-prompts"]')
        self.assertTrue(details.is_visible())
        self.assertFalse(details.evaluate("(e) => e.open"))
        self.assertTrue(case.locator(
            'a[href="/local/guide/mcp-prompts"]').is_hidden())
        self.assertFalse(page.locator("#direct-start-actions").evaluate(
            "(e) => e.open"))
        self.screenshot("g3-mcp-basic-390.png")
        details.locator("summary").click()
        self.assertTrue(case.locator(
            'a[href="/local/guide/mcp-prompts"]').is_visible())
        self.screenshot("g3-mcp-details-390.png")

    def test_02_try_path_reaches_preexisting_first_party_engine(self):
        page = self.open_preview()
        page.locator('[data-flow="try"]').click()
        page.locator("#continue").click()
        self.assertEqual(page.locator("#progress").inner_text(), "3 / 3 단계")
        row = page.locator('[data-route-flow="try"] a[href="/local/engine?purpose=SKILL_TEST_AUTOMATION"]')
        self.assertTrue(row.is_visible())
        row.click()
        self.assertIn("/local/engine?purpose=SKILL_TEST_AUTOMATION", page.url)
        self.assertIn("예제", page.locator("body").inner_text())

    def test_03_learn_path_reaches_existing_public_library(self):
        page = self.open_preview()
        page.locator('[data-flow="learn"]').click()
        page.locator("#continue").click()
        row = page.locator('[data-route-flow="learn"] a[href="/local/library?q=Git"]')
        self.assertTrue(row.is_visible())
        row.click()
        self.assertIn("/local/library?q=Git", page.url)
        self.assertTrue(page.locator("body").inner_text())

    def test_04_unmatched_case_stays_unsupported(self):
        page = self.select_case("unmatched")
        self.assertIn("아직", page.locator("#result-title").inner_text())
        self.assertTrue(page.locator("#proof").is_hidden())
        self.assertTrue(page.locator('[data-route-case="unmatched"]').is_visible())
        self.assertNotIn("UCIE-CAPSULE-MCP-PROMPTS",
                         page.locator('[data-route-case="unmatched"]').inner_text())

    def test_05_other_case_never_inherits_mcp_capsule(self):
        page = self.select_case("git-repository")
        self.assertTrue(page.locator('[data-route-case="git-repository"]').is_visible())
        self.assertTrue(page.locator('[data-route-case="mcp-prompts"]').is_hidden())
        self.assertIn("MCP의 증거를 잘못 적용하지 않습니다",
                      page.locator("#result-body").inner_text())
        self.assertNotIn("UCIE-CAPSULE-MCP-PROMPTS",
                         page.locator('[data-route-case="git-repository"]').inner_text())

    def test_06_existing_v04_strict_csp_keeps_three_native_actions(self):
        for flow, target in (
            ("solve", "/local/ask"), ("try", "/local/engine?purpose=SKILL_TEST_AUTOMATION"),
            ("learn", "/local/library?q=Git"),
        ):
            with self.subTest(flow=flow):
                page = self.open_preview(LOCKED_PATH)
                self.assertTrue(page.locator("#stage2").is_hidden())
                self.assertTrue(page.locator('[data-flow="' + flow + '"]').is_visible())
                page.locator('[data-flow="' + flow + '"]').click()
                self.assertIn(target, page.url)
                self.assertIn("text/html", page.main_frame.evaluate(
                    "document.contentType"))
        self.assertEqual(self.page_errors, [])

    def test_07_browser_javascript_disabled_still_navigates_existing_get(self):
        context = self.browser.new_context(
            viewport={"width":390,"height":844}, java_script_enabled=False)
        try:
            page = context.new_page()
            response = page.goto(self.origin + REVIEW_PATH)
            self.assertEqual(response.status, 200)
            self.assertTrue(page.locator('[data-flow="solve"]').is_visible())
            page.locator('[data-flow="solve"]').click()
            self.assertIn("/local/ask", page.url)
            self.assertIn("문제 설명", page.locator("body").inner_text())
        finally:
            context.close()

    def test_08_keyboard_enter_forward_back_and_heading_focus(self):
        page = self.open_preview()
        page.keyboard.press("Tab")
        self.assertEqual(page.locator(":focus").get_attribute("data-flow"),
                         "solve")
        page.keyboard.press("Enter")
        self.assertTrue(page.locator("#stage2").is_visible())
        self.assertTrue(page.locator("#stage2 h2").evaluate(
            "(e) => document.activeElement === e"))
        page.locator("#back1").focus()
        page.keyboard.press("Enter")
        self.assertTrue(page.locator("#stage1").is_visible())
        self.assertTrue(page.locator("#stage1 h1").evaluate(
            "(e) => document.activeElement === e"))
        self.assertEqual(self.page_errors, [])

    def test_09_responds_without_horizontal_scroll_at_five_widths(self):
        for width in WORKLOAD_SIZES:
            with self.subTest(width=width):
                self.page.set_viewport_size({"width":width, "height":844})
                page = self.open_preview()
                self.assert_no_horizontal_overflow(page, "home " + str(width))
                self.screenshot("g3-home-" + str(width) + ".png")
                page.locator('[data-flow="solve"]').click()
                page.locator('[data-issue="mcp-prompts"]').click()
                page.locator("#proof summary").click()
                self.assert_no_horizontal_overflow(page, "mcp " + str(width))
                self.assertTrue(page.locator("#proof").is_visible())

    def test_10_css_zoom_200_percent_reflow_and_long_korean(self):
        page = self.select_case()
        page.evaluate("document.documentElement.style.zoom='200%'")
        self.assert_no_horizontal_overflow(page, "390 viewport 200pct CSS zoom")
        page.locator("#result-body").evaluate(
            "(e) => e.textContent = 'UCIE 공식 문서 확인과 안전한 점검 ' .repeat(18)")
        self.assert_no_horizontal_overflow(page, "long Korean at 200pct CSS zoom")
        self.screenshot("g3-zoom-200-390.png")

    def test_11_forged_b1_rights_cannot_reveal_evidence_as_safe(self):
        page = self.open_preview(FORGED_PATH)
        page.locator('[data-flow="solve"]').click()
        page.locator('[data-issue="mcp-prompts"]').click()
        self.assertIn("증거를 확인할 수 없어요", page.locator("#result-title").inner_text())
        self.assertTrue(page.locator("#proof").is_hidden())
        self.assertTrue(page.locator("#existing-actions").is_hidden())
        self.assertNotIn("CONTRACT_MATCH", page.locator("#result-body").inner_text())

    def test_12_offline_after_load_does_not_fabricate_completion(self):
        page = self.open_preview()
        self.ctx.set_offline(True)
        page.locator('[data-flow="solve"]').click()
        page.locator('[data-issue="mcp-prompts"]').click()
        self.assertEqual(page.locator("#progress").inner_text(), "3 / 3 단계")
        self.assertIn("실제 PC와 코드는 검사하지 않았어요",
                      page.locator("#stage3").inner_text())
        page.locator("#proof summary").click()
        self.assertIn("NOT_AUTHORIZED", page.locator("#e-qa").inner_text())
        self.ctx.set_offline(False)

    def test_13_source_evidence_stays_readonly_and_no_external_fetch(self):
        page = self.select_case()
        self.assertTrue(page.locator("#e-link").get_attribute("href").startswith(
            "https://github.com/modelcontextprotocol/python-sdk/pull/3696"))
        self.assertEqual(self.external_requests, [])
        self.assertEqual(self.page_errors, [])
        self.assertEqual(page.locator('form').count(), 0)
        self.assertEqual(page.locator('input[type=file]').count(), 0)

    def test_14_js_enabled_choices_are_wizard_not_automatic_external_get(self):
        page = self.open_preview()
        original_url = page.url
        page.locator('[data-flow="solve"]').click()
        self.assertEqual(page.url, original_url)
        self.assertTrue(page.locator("#stage2").is_visible())
        self.assertIn("2 / 3", page.locator("#progress").inner_text())

    def test_15_no_script_fallback_links_are_keyboard_reachable(self):
        page = self.open_preview(LOCKED_PATH)
        page.keyboard.press("Tab")
        self.assertEqual(page.locator(":focus").get_attribute("data-flow"),
                         "solve")
        page.keyboard.press("Enter")
        page.wait_for_url(lambda url: url.endswith("/local/ask"), timeout=5000)
        self.assertTrue(page.url.endswith("/local/ask"))
