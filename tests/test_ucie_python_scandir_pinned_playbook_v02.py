"""B1/B2: user-selectable CPython tag-pinned review playbook regressions.

Uses official-public metadata and UCIE-authored synthetic files exclusively.
No upstream code, arbitrary user path, customer data, external GET, package
publication, rule promotion, or operating database/TaskScheduler mutation.
"""
from __future__ import annotations

from contextlib import closing
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import python_scandir_guide_v01 as guide
from ucie_miner import python_scandir_pinned_playbook_v02 as playbook


class UCIEPythonPinnedPlaybookV02Tests(unittest.TestCase):
    def test_exact_official_tag_document_and_license_scope(self):
        source = playbook.pinned_source_snapshot()
        self.assertEqual(source["source_tag"], "v3.15.0")
        self.assertEqual(source["tag_commit_sha1"],
                         "d220409a13b77de7a6c30abe16ea90db01528edc")
        self.assertEqual(source["doc_blob_sha1"],
                         "74419ee7f3588f1baec83c85b05716e6388719e3")
        self.assertEqual(source["license_blob_sha1"],
                         "20cf39097c68baa17cc566b64e76d34ebf034044")
        self.assertEqual(source["source_id"], "doc:python/cpython")
        self.assertTrue(source["tagged_doc_reference_observed"])
        self.assertTrue(source["context_manager_and_close_documented_at_tag"])
        self.assertFalse(source["live_doc_revision_pinned"])
        self.assertFalse(source["per_revision_redistribution_clearance"])
        self.assertFalse(source["owner_licensing_signoff"])
        self.assertFalse(source["upstream_race_behavior_independently_reproduced"])
        self.assertFalse(source["new_fetch_authority"])

    def test_two_useful_first_party_examples_are_bounded_and_never_run(self):
        for case in playbook.CASE_IDS:
            with self.subTest(case=case):
                out = playbook.review_case(case)
                self.assertEqual(out["schema"], playbook.SCHEMA)
                self.assertEqual(out["case_id"], case)
                self.assertIn("with os.scandir(directory) as entries:",
                              out["safe_example"])
                self.assertIn("def list_directory_names", out["safe_example"])
                self.assertFalse(out["example_executed_by_view"])
                self.assertFalse(out["arbitrary_paths_accepted"])
                self.assertFalse(out["customer_files_read"])
                self.assertFalse(out["human_approved"])
                self.assertFalse(out["auto_promoted"])
                self.assertFalse(out["export_allowed"])
                self.assertFalse(out["customer_release_authorized"])
                self.assertEqual(out["network_requests"], 0)
                self.assertEqual(out["operating_database_writes"], 0)

    def test_guarded_example_joins_workers_before_closing_context(self):
        text = playbook.review_case("shared_guarded")["safe_example"]
        self.assertIn("with guard:", text)
        self.assertIn("next(entries, None)", text)
        self.assertIn("with ThreadPoolExecutor(max_workers=2) as pool:", text)
        self.assertLess(text.index("with os.scandir(directory) as entries:"),
                        text.index("with ThreadPoolExecutor(max_workers=2) as pool:"))
        self.assertNotIn("exec(", text)

    def test_invalid_cases_fail_closed_without_running(self):
        for value in ("", "all", "delete", "../secret", 123, None, True):
            with self.subTest(case=value):
                with self.assertRaises(playbook.PythonPinnedPlaybookError):
                    playbook.review_case(value)

    def test_untrusted_official_doc_registry_rejected(self):
        with patch(
            "ucie_miner.python_scandir_pinned_playbook_v02._source_bound_entry",
            return_value=(
                {"source_id": "doc:python/cpython", "status": "ACTIVE_APPROVED",
                 "public_url": "https://unauthorized.invalid/os",
                 "license_verdict": "NOT_ATTESTED_PER_REVISION",
                 "fetch_authorized_by_this_registry": False},
                {"kind": "TEST_RECIPE",
                 "revision_hint": "PUBLIC_DOCUMENT_REVISION_NOT_PINNED",
                 "human_approved": False, "export_allowed": False,
                 "auto_promoted": False},
            ),
        ):
            with self.assertRaises(playbook.PythonPinnedPlaybookError):
                playbook.review_case("single_owner")

    def test_guide_exposes_separately_pinned_tag_not_fake_approval(self):
        with patch(
            "ucie_miner.python_scandir_review_v01._evaluate_only_ucie_synthetic_inputs",
            side_effect=AssertionError("a guide is not a synthetic trial"),
        ):
            output = guide.build_readonly_guide()
            self.assertEqual(output["tagged_source_snapshot"]["source_tag"],
                             "v3.15.0")
            self.assertEqual(
                output["machine_skill_contract"]["playbook_case_ids"],
                ["single_owner", "shared_guarded"]
            )
            self.assertFalse(output["machine_skill_contract"][
                "playbook_example_auto_executed"])
            self.assertFalse(output["review_gates"]["source_revision_pinned"])
            self.assertFalse(output["review_gates"]["per_revision_rights_cleared"])
            html = app._python_review_guide("")
            self.assertIn("v3.15.0", html)
            self.assertIn(playbook.DOC_BLOB, html)
            self.assertIn(playbook.LICENSE_BLOB, html)
            self.assertIn("case=single_owner", html)
            self.assertIn("case=shared_guarded", html)
            self.assertIn("NOT_ATTESTED_PER_REVISION", html)
            contract = json.loads(app._python_review_guide("", json_mode=True))
            self.assertEqual(contract["tagged_source_snapshot"],
                             output["tagged_source_snapshot"])

    def test_current_engine_default_and_selected_cases_are_real_synthetic(self):
        for query, choice in (
            ("purpose=PYTHON_SCANDIR_SAFE", "shared_guarded"),
            ("purpose=PYTHON_SCANDIR_SAFE&case=single_owner", "single_owner"),
            ("purpose=PYTHON_SCANDIR_SAFE&case=shared_guarded", "shared_guarded"),
        ):
            with self.subTest(query=query):
                html = app._engine(query, root=Path("UCIE"))
                self.assertIn(playbook.CASES[choice]["title"], html)
                self.assertIn("UCIE FIRST-PARTY TEST", html)
                self.assertIn("4개", html)
                self.assertIn("Python 3.15.0", html)
                self.assertIn(playbook.DOC_BLOB, html)
                self.assertIn("case=single_owner", html)
                self.assertIn("case=shared_guarded", html)
                self.assertNotIn("CUSTOMER_RELEASE_GO", html)

    def test_unrelated_engine_cannot_gain_python_case_parameter(self):
        with self.assertRaises(app.LocalProductError):
            app._engine("purpose=MCP_PROMPTS_CONTRACT&case=single_owner",
                        root=Path("UCIE"))
        with self.assertRaises(app.LocalProductError):
            app._engine("purpose=PYTHON_SCANDIR_SAFE&case=invalid",
                        root=Path("UCIE"))

    def test_forged_pinned_source_in_engine_is_rejected(self):
        honest = playbook.review_case("single_owner")
        broken = dict(honest, source_evidence=dict(
            honest["source_evidence"], owner_licensing_signoff=True))
        with patch.object(playbook, "review_case", return_value=broken):
            with self.assertRaises(app.LocalProductError):
                app._engine("purpose=PYTHON_SCANDIR_SAFE&case=single_owner",
                            root=Path("UCIE"))

    def test_http_engine_cases_and_approval_bypass_negative(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / ".git").is_dir():
            self.skipTest("requires clean or owner UCIE checkout")
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(root))
        server.daemon_threads = True
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def call(method, path, *, host=None):
                with closing(HTTPConnection("127.0.0.1", server.server_port,
                                            timeout=8)) as conn:
                    headers = {}
                    if host is not None:
                        headers["Host"] = host
                    conn.request(method, path, headers=headers)
                    resp = conn.getresponse()
                    return resp.status, resp.read(400_000)
            for case in playbook.CASE_IDS:
                status, body = call(
                    "GET", "/local/engine?purpose=PYTHON_SCANDIR_SAFE&case=" + case)
                self.assertEqual(status, 200)
                self.assertIn(playbook.CASES[case]["title"].encode("utf-8"), body)
                self.assertIn(playbook.DOC_BLOB.encode("ascii"), body)
            status, data = call("GET", "/local/guide/python-scandir.json")
            self.assertEqual(status, 200)
            guide_data = json.loads(data)
            self.assertFalse(guide_data["export_allowed"])
            status, _ = call("POST", "/local/engine?purpose=PYTHON_SCANDIR_SAFE")
            self.assertEqual(status, 405)
            status, _ = call("GET",
                             "/local/engine?purpose=PYTHON_SCANDIR_SAFE&case=approved")
            self.assertEqual(status, 400)
            status, _ = call("GET",
                             "/local/engine?purpose=PYTHON_SCANDIR_SAFE&case=shared_guarded",
                             host="private.invalid")
            self.assertEqual(status, 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
