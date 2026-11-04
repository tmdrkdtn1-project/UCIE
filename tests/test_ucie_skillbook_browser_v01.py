"""UCIE first SkillBook read-only HTTP catalog, no real public GET or DB writes."""
from __future__ import annotations

from http.server import HTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from ucie_miner import library_browser_skillbook_v01 as ui
from ucie_miner import skillbook_product_v01 as product


class UCIESkillBookUITests(unittest.TestCase):
    def test_readonly_html_has_original_chapters_and_gate_labels(self):
        book = product.build_skillbook()
        html = ui.render_chapter(book)
        self.assertIn("Python os.scandir", html)
        self.assertIn("UCIE_AUTHORED_RECIPE", html)
        self.assertIn("OFFICIAL_PYTHON_DOCUMENTED", html)
        self.assertIn("NOT_REVIEWED_FOR_DISTRIBUTION", html)
        self.assertIn(book["source_evidence"]["source_document_sha256"], html)
        self.assertIn('href="/skillbooks/', html)
        self.assertNotIn("자동 배포 승인 완료", html)

    def test_catalog_rejects_forged_approvals(self):
        good = product.search_skillbooks(query="")
        good["items"][0]["human_approved"] = True
        with self.assertRaises(product.SkillBookProductError):
            ui.render_catalog(good, query="", language="", kind="")
        bad = product.build_skillbook()
        bad["export_allowed"] = True
        with self.assertRaises(product.SkillBookProductError):
            ui.render_chapter(bad)

    def test_search_html_is_escaped(self):
        html = ui.render_catalog(product.search_skillbooks(query="scandir"),
                                 query='" onmouseover="x', language="", kind="")
        self.assertNotIn('value="" onmouseover=', html)
        self.assertIn("&quot;", html)

    def test_http_routes_are_loopback_and_do_not_invoke_public_get(self):
        def forbidden_probe(*args, **kwargs):
            self.fail("SkillBook browsing must never request public source")
        handler = ui.make_handler(Path("/synthetic/ucie"),
                                  public_prober=forbidden_probe)
        with HTTPServer(("127.0.0.1", 0), handler) as srv:
            th = threading.Thread(target=srv.serve_forever, kwargs={
                "poll_interval": 0.05}, daemon=True)
            th.start()
            try:
                addr = "http://127.0.0.1:" + str(srv.server_port)
                def read(path, headers=None):
                    req = Request(addr + path, headers=headers or {})
                    try:
                        with urlopen(req, timeout=5) as response:
                            return response.status, response.read().decode("utf-8")
                    except HTTPError as error:
                        return error.code, error.read().decode("utf-8")
                status, html = read("/skillbooks?q=Python&language=Python")
                self.assertEqual(status, 200)
                self.assertIn("실물 SkillBook", html)
                self.assertIn("기술 챕터", html)
                status, result = read("/skillbooks.json?q=scandir")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(result)["total"], 1)
                status, chapter = read("/skillbooks/" + product.SKILLBOOK_ID)
                self.assertEqual(status, 200)
                self.assertIn("UCIE_AUTHORED_RECIPE", chapter)
                status, data = read("/skillbooks/" + product.SKILLBOOK_ID + ".json")
                self.assertEqual(status, 200)
                self.assertFalse(json.loads(data)["export_allowed"])
                self.assertFalse(json.loads(data)["proof_gates"]["published"])
                status, _ = read("/skillbooks?q=Rust")
                self.assertEqual(status, 200)
                status, _ = read("/skillbooks?q=" + quote("<script>"))
                self.assertEqual(status, 400)
                status, _ = read("/skillbooks/UNKNOWN")
                self.assertEqual(status, 404)
                status, _ = read("/skillbooks/" + product.SKILLBOOK_ID + "?next=/")
                self.assertEqual(status, 400)
                status, _ = read("/skillbooks", {"Host": "untrusted.example"})
                self.assertEqual(status, 403)
                print("UCIE_SKILLBOOK_LOCAL_HTTP="
                      '{"catalog":200,"detail":200,"json":200,'
                      '"untrusted_query":400,"unknown_item":404,'
                      '"bad_host":403,"public_fetches":0}')
            finally:
                srv.shutdown()
                th.join(timeout=3)

    def test_original_v09_is_inherited_unchanged(self):
        handler = ui.make_handler(Path("/synthetic/ucie"))
        self.assertEqual(handler.__bases__[0].__module__, ui.previous.__name__)
        self.assertEqual(handler.__bases__[0].__name__, "Handler")
        self.assertIn('href="/skillbooks"', ui.NAVIGATION)

    def test_powershell_launch_is_owner_only(self):
        script = (Path(__file__).resolve().parents[1] /
                  "scripts" / "ucie_skillbook_library_v01.ps1").read_text(encoding="utf-8")
        self.assertIn("D:\\UCIE", script)
        self.assertIn("PYTHONPATH", script)
        for forbidden in ("Start-ScheduledTask", "Register-ScheduledTask",
                          "Stop-Process", "D:\\MYGAME", "D:\\OFFICE_AGENT"):
            self.assertNotIn(forbidden, script)
        shell = shutil.which("powershell.exe") or shutil.which("pwsh")
        if shell is not None:
            path = str(Path(__file__).resolve().parents[1] /
                       "scripts" / "ucie_skillbook_library_v01.ps1").replace("'", "''")
            command = ("$t=$null;$e=$null;"
                       + "[void][System.Management.Automation.Language.Parser]::ParseFile('"
                       + path + "',[ref]$t,[ref]$e);"
                       + "if($e.Count){$e|%{$_.Message};exit 2}")
            p = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command",
                                command], capture_output=True, text=True,
                               errors="replace", check=False, timeout=20)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
