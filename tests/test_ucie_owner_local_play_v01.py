"""UCIE owner Local V1 integrated home: first-party and offline, not customer release."""
from __future__ import annotations

from contextlib import closing
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch
import json
import unittest

from ucie_miner import local_owner_play_v01 as play
from ucie_miner import local_v1_app_v01 as app


class OwnerLocalPlayContractTests(unittest.TestCase):
    def test_01_exact_four_existing_product_cases(self):
        result = play.owner_journeys()
        self.assertEqual(result["case_count"], 4)
        self.assertEqual(tuple(x["case_id"] for x in result["cases"]), play.OWNER_CASES)
        self.assertEqual(result["schema"], play.SCHEMA)
        self.assertEqual(result["status"], play.STATUS)
        self.assertTrue(result["owner_local_only"])
        self.assertFalse(result["customer_distribution_authorized"])

    def test_02_each_case_connects_real_existing_four_routes(self):
        for item in play.owner_journeys()["cases"]:
            with self.subTest(case=item["case_id"]):
                self.assertEqual(item["error_url"],
                                 "/local/error?case=" + item["case_id"])
                self.assertIn("B2_CONNECTED_TRIAGE", item["engine_issue_url"])
                self.assertIn("scenario=issue", item["engine_issue_url"])
                self.assertIn("scenario=control", item["engine_control_url"])
                self.assertTrue(item["library_url"].startswith("/local/library?q="))
                self.assertTrue(item["evolution_url"].startswith("/local/evolution?q="))

    def test_03_report_never_reads_customer_code_or_promotes_rules(self):
        result = play.owner_journeys()
        for key in ("actual_user_project_read", "third_party_code_executed",
                    "independent_user_fix_verified", "customer_distribution_authorized"):
            self.assertIs(result[key], False)
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["operating_database_writes"], 0)

    def test_04_all_four_case_links_rendered_in_original_home(self):
        page = app._home()
        self.assertIn('data-owner-playground="true"', page)
        for item in play.owner_journeys()["cases"]:
            self.assertIn('data-owner-case="' + item["case_id"] + '"', page)
            self.assertIn(item["case_id"], page)
        self.assertIn("내 PC에서 바로 사용해보기", page)
        self.assertIn("실제 사용자 환경을 진단한 것이 아닙니다", page)

    def test_05_no_payment_customer_signing_or_public_url_in_play(self):
        html = play.render_owner_play()
        self.assertNotIn("/local/membership", html)
        self.assertNotIn("payments/", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("customer_distribution_authorized=true", html)
        self.assertIn("미검증", html)

    def test_06_future_unreviewed_case_cannot_become_start_button(self):
        with patch.object(play, "CASE_IDS", play.OWNER_CASES + ("unknown",)):
            with self.assertRaises(play.OwnerPlayError):
                play.owner_journeys()

    def test_07_forced_false_release_flag_fails_closed(self):
        real = play.evaluate_case
        def forged(case_id, scenario):
            value = real(case_id, scenario)
            value["customer_distribution_authorized"] = True
            return value
        with patch.object(play, "evaluate_case", side_effect=forged):
            with self.assertRaises(play.OwnerPlayError):
                play.owner_journeys()

    def test_08_unsafe_query_change_fails_closed(self):
        real = play.evaluate_case
        def forged(case_id, scenario):
            value = real(case_id, scenario)
            value["public_library_query"] = "../../../outside"
            return value
        with patch.object(play, "evaluate_case", side_effect=forged):
            with self.assertRaises(play.OwnerPlayError):
                play.owner_journeys()

    def test_09_malformed_html_link_denied(self):
        for path in ("/local/error\"onclick=\"alert(1)", "/https://outside",
                     "/local/library#unsafe"):
            with self.subTest(path=path), self.assertRaises(play.OwnerPlayError):
                original = play.owner_journeys
                def manipulated():
                    report = original()
                    report["cases"][0]["error_url"] = path
                    return report
                with patch.object(play, "owner_journeys", side_effect=manipulated):
                    play.render_owner_play()

    def test_10_real_loopback_home_and_deep_link_engine_without_billing(self):
        with TemporaryDirectory(prefix="UCIE_OWNER_LOCAL_PLAY_") as tmp:
            root = Path(tmp)/"UCIE"
            (root/".git").mkdir(parents=True)
            with HTTPServer(("127.0.0.1",0),app.make_handler(root)) as server:
                thread=Thread(target=server.serve_forever,daemon=True)
                thread.start()
                try:
                    def get(route,method="GET",host=None):
                        with closing(HTTPConnection("127.0.0.1",server.server_port,timeout=5)) as conn:
                            conn.request(method,route,headers={
                                "Host":host or "127.0.0.1:"+str(server.server_port)})
                            reply=conn.getresponse()
                            return reply.status,reply.read().decode("utf-8","replace"),dict(
                                reply.getheaders())
                    status,html,hdr=get("/local")
                    self.assertEqual(status,200)
                    self.assertIn('data-owner-playground="true"',html)
                    self.assertIn("default-src 'none'",hdr["Content-Security-Policy"])
                    self.assertEqual(get("/local",method="POST")[0],405)
                    self.assertEqual(get("/local",host="other.example")[0],403)
                    status,payload,_=get("/local/health")
                    self.assertEqual(status,200)
                    self.assertFalse(json.loads(payload)["online_release_authorized"])
                    for item in play.owner_journeys()["cases"]:
                        for route in (item["engine_issue_url"],
                                      item["engine_control_url"]):
                            with self.subTest(route=route):
                                status,_,_=get(route)
                                self.assertEqual(status,200)
                finally:
                    server.shutdown()
                    thread.join(timeout=5)
                    self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
