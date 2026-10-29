"""P9 integrated product acceptance *negative gates* and standalone draft consumer."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from ucie_miner import product_v1 as product
from ucie_miner import portable_exact as portable
from ucie_miner import experience_evolution as evo
from ucie_miner.capability_experience import run_capability_cycle
from ucie_miner.public_candidate_staging import stage_public_candidates, DB_NAME
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, optional_hourly_review_learning)
from test_ucie_stage11_hourly_stage import fixture_batch


class P9IntegratedProductTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)

    def test_portable_self_authored_demo_search_equivalent_no_approval(self):
        result = product.portable_consumer_check()
        self.assertTrue(result["all_queries_equivalent"])
        self.assertEqual(result["single_query_strategy"], "LINEAR_EXACT_SCAN")
        self.assertEqual(result["batch_strategy"], "COMPOSITE_INDEX")
        self.assertTrue(result["zero_match_checked"])
        self.assertEqual(result["approved_or_exportable_public_candidates"], 0)
        self.assertFalse(result["standalone_import_independently_tested_here"])

    def test_portable_search_rejects_forged_private_or_approved_metadata(self):
        valid = product._demo_input()
        key = ("repo:python/cpython", "Python",
               "PUBLIC_TECHNICAL_EVIDENCE", "API_CONTRACT")
        for mutate in (
            ("source_id", "repo:private/secret"),
            ("source_id", "research:GH Archive"),
            ("domain", "PRIVATE"),
            ("purpose_code", "UNTRUSTED; DROP"),
            ("library_item_id", "not-a-hash"),
            ("public_url", "https://outside.invalid/pr/1"),
            ("export_allowed", True),
            ("human_approved", True),
        ):
            rows = deepcopy(valid)
            rows[0][mutate[0]] = mutate[1]
            with self.subTest(change=mutate):
                with self.assertRaises(portable.PortableLookupError):
                    portable.search_public_metadata(rows, queries=(key,))
        with self.assertRaises(portable.PortableLookupError):
            portable.search_public_metadata(valid, queries=(key,) * 33)
        with self.assertRaises(portable.PortableLookupError):
            portable.search_public_metadata(valid, queries=(key,), limit=True)
        with self.assertRaises(portable.PortableLookupError):
            portable.search_public_metadata(valid, queries=(key,), limit=21)

    def test_portable_draft_bytes_identical_and_no_public_code(self):
        a, manifest = product.build_draft_package_bytes()
        b, other = product.build_draft_package_bytes()
        self.assertEqual(a, b)
        self.assertEqual(manifest, other)
        self.assertFalse(manifest["signed"])
        self.assertFalse(manifest["owner_release_authorized"])
        self.assertFalse(manifest["independent_qa_signed_off"])
        self.assertFalse(manifest["source_license_signoff"])
        self.assertFalse(manifest["upstream_public_code_included"])
        with tempfile.TemporaryDirectory() as temp:
            f = Path(temp) / "draft.zip"
            f.write_bytes(a)
            with ZipFile(f) as z:
                self.assertEqual(z.namelist(),
                                 ["portable_exact.py", "MANIFEST.json", "README.txt"])
                self.assertEqual(z.read("MANIFEST.json"),
                                 json.dumps(manifest, sort_keys=True,
                                            separators=(",", ":")).encode("ascii"))
                self.assertEqual(z.read("portable_exact.py"),
                                 Path(portable.__file__).read_bytes())
                self.assertNotIn(b"upstream PR contents", z.read("portable_exact.py"))

    def test_actual_independent_consumer_import_works_without_ucie_package(self):
        payload, _manifest = product.build_draft_package_bytes()
        with tempfile.TemporaryDirectory() as temp:
            isolated = Path(temp)
            with ZipFile(io_bytes(payload)) as z:
                z.extract("portable_exact.py", path=isolated)
            consumer_script = (
                "import json,runpy,sys\n"
                "m=runpy.run_path(sys.argv[1]); assert m['VERSION']=='1.0.0'\n"
                "h='a'*64\n"
                "rows=[dict(source_id='repo:python/cpython',domain='Python',"
                "kind='PUBLIC_TECHNICAL_EVIDENCE',purpose_code='API_CONTRACT',"
                "library_item_id=h,public_url='https://github.com/python/cpython/pull/1',"
                "evidence_sha256=h,human_approved=False,export_allowed=False)]\n"
                "key=('repo:python/cpython','Python','PUBLIC_TECHNICAL_EVIDENCE','API_CONTRACT')\n"
                "o=m['search_public_metadata'](rows,queries=(key,))\n"
                "assert o['results'][0]['total_matches']==1\n"
                "assert o['strategy']=='LINEAR_EXACT_SCAN'\n"
                "assert o['production_release_approved'] is False\n"
                "print(json.dumps(dict(status='ISOLATED_DRAFT_CONSUMER_EXECUTED',"
                "matches=o['results'][0]['total_matches'])))\n"
            )
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            p = subprocess.run(
                [sys.executable, "-I", "-c", consumer_script,
                 str(isolated / "portable_exact.py")],
                cwd=isolated, env=env, text=True, capture_output=True,
                timeout=25, check=True)
            out = json.loads(p.stdout)
            self.assertEqual(out["status"], "ISOLATED_DRAFT_CONSUMER_EXECUTED")
            self.assertEqual(out["matches"], 1)

    def test_explicit_draft_export_is_only_ucie_local_and_no_overwrite(self):
        first = product.explicitly_export_draft(self.root)
        self.assertTrue(first["created"])
        self.assertFalse(first["production_release_approved"])
        self.assertFalse(first["standalone_consumer_qa_attested"])
        p = self.root / first["relative_path"]
        original = p.read_bytes()
        second = product.explicitly_export_draft(self.root)
        self.assertFalse(second["created"])
        self.assertEqual(original, p.read_bytes())
        p.write_bytes(b"DIFFERENT")
        with self.assertRaises(product.ProductIntegrationError):
            product.explicitly_export_draft(self.root)

    def test_root_scope_rejects_unrelated_directory_no_exports(self):
        wrong = self.root.parent / "NOT_UCIE"
        (wrong / "runtime").mkdir(parents=True)
        with self.assertRaises(product.ProductIntegrationError):
            product.explicitly_export_draft(wrong)
        with self.assertRaises(product.ProductIntegrationError):
            product.integrated_product_preview(wrong)
        self.assertFalse((wrong / "runtime" / "exports").exists())

    def test_real_synthetic_source_linked_public_ledger_and_p8_readonly(self):
        batch = fixture_batch(
            root=self.root,
            sources=("python/cpython", "PowerShell/PowerShell",
                     "git/git", "modelcontextprotocol/python-sdk",
                     "actions/runner-images"),
            max_enrich=1, include_git_commits=True, include_docs=False,
            include_advisories=False, backfill_pages=1)
        stage_public_candidates(batch, root=self.root, allow_disk_write=True)
        runtime = self.root / "runtime"
        (runtime / OPT_IN_FILENAME).write_text(OPT_IN_TOKEN, encoding="ascii")
        self.assertEqual(optional_hourly_review_learning(self.root)[
            "new_review_proposals"], 2)
        experience = evo.run_evolution_cycle(self.root, record=True)
        self.assertTrue(experience["new_event_written"])
        checks = (
            runtime / DB_NAME,
            runtime / "stage12_unverified_review.sqlite3",
            runtime / evo.FILE_NAME,
        )
        before = [p.read_bytes() for p in checks]
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("P9 preview cannot GET")):
            out = product.integrated_product_preview(
                self.root, query="API_CONTRACT", include_demo=True, limit=5)
        self.assertEqual([p.read_bytes() for p in checks], before)
        self.assertEqual(out["source_registry"]["approved_source_count"], 10)
        self.assertEqual(out["public_candidate_library"]["source_linked_count"], 2)
        self.assertEqual(out["p8_owned_synthetic_experience"][
            "recorded_experiments"], 1)
        self.assertEqual(out["w05_candidate_linked_experience"]["recorded_count"], 0)
        self.assertEqual(out["signed_rules"]["status"], "NOT_INSPECTED_NO_GO")
        self.assertEqual(out["official_public_metadata_library"]["status"],
                         "STAGE14_OFFICIAL_LEDGER_ABSENT_NO_GO")
        self.assertTrue(out["portable_first_party_consumer_demo"]["all_queries_equivalent"])
        self.assertEqual(len(out["first_party_synthetic_experiments"]), 3)
        self.assertTrue(all(
            x["exact_result_equivalence_observed"]
            for x in out["first_party_synthetic_experiments"]))
        self.assertFalse(out["v1_accepted"])
        self.assertFalse(out["package_released"])
        self.assertEqual(out["operating_database_writes"], 0)
        self.assertEqual(out["network_requests"], 0)
        self.assertFalse((runtime / "exports").exists())

    def test_unified_catalog_search_reuses_original_public_ledger(self):
        batch = fixture_batch(
            root=self.root,
            sources=("python/cpython", "PowerShell/PowerShell",
                     "git/git", "modelcontextprotocol/python-sdk",
                     "actions/runner-images"),
            max_enrich=1, include_git_commits=True,
            include_docs=False, include_advisories=False, backfill_pages=1)
        stage_public_candidates(batch, root=self.root, allow_disk_write=True)
        runtime = self.root / "runtime"
        (runtime / OPT_IN_FILENAME).write_text(OPT_IN_TOKEN, encoding="ascii")
        self.assertEqual(optional_hourly_review_learning(self.root)[
            "new_review_proposals"], 2)
        before = {
            p.name: p.read_bytes() for p in (
                runtime / DB_NAME,
                runtime / "stage12_unverified_review.sqlite3",
            )}
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("unified search cannot fetch")):
            out = product.integrated_product_preview(
                self.root, query="API_CONTRACT", limit=5)
        after = {
            p.name: p.read_bytes() for p in (
                runtime / DB_NAME,
                runtime / "stage12_unverified_review.sqlite3",
            )}
        self.assertEqual(before, after)
        view = out["unified_catalog_search"]
        self.assertEqual(view["status"],
                         "READ_ONLY_BOUNDED_MULTI_SHELF_SEARCH_NO_GO")
        self.assertEqual(view["schema"],
                         "UCIE_P9_BOUNDED_UNIFIED_CATALOG_QUERY_V1")
        self.assertFalse(view["full_catalog_match_count_known"])
        self.assertEqual(
            {item["library_item_id"] for item in view["items"]},
            {item["library_item_id"] for item
             in out["public_candidate_library"]["items"]},
        )
        self.assertTrue(all(item["shelf"] == "PUBLIC_CANDIDATE"
                            for item in view["items"]))
        self.assertTrue(all(item["human_approved"] is False
                            and item["export_allowed"] is False
                            for item in view["items"]))
        self.assertEqual(view["network_requests"], 0)
        self.assertEqual(view["operating_database_writes"], 0)
        self.assertFalse(view["v1_accepted"])

    def test_unified_catalog_combines_shelves_without_forged_approval(self):
        public = {"status":"READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
                  "omitted_count":0, "items":[{
                      "library_item_id":"1"*64,
                      "kind":"PUBLIC_TECHNICAL_EVIDENCE",
                      "source_id":"repo:python/cpython",
                      "public_url":"https://github.com/python/cpython/pull/153462",
                      "evidence_sha256":"2"*64,
                      "purpose_code":"SCANDIR_SHARED_RACE",
                      "domain":"Python", "skill_profile":"PYTHON_STDLIB",
                      "revision_hint":"pr:153462",
                      "version_scope_claim":"UNDETERMINED",
                      "lifecycle":"UNVERIFIED_CANDIDATE_ONLY",
                      "signature_status":"NOT_ATTESTED_BY_THIS_SEARCH",
                      "human_approved":False, "export_allowed":False}]}
        official = {"status":"STAGE14_OFFICIAL_METADATA_READ_ONLY_UNVERIFIED_NO_GO",
                    "omitted_count":0, "items":[{
                        "kind":"OFFICIAL_DOCUMENT_EVIDENCE",
                        "source_id":"doc:python/cpython",
                        "public_url":"https://docs.python.org/3/",
                        "source_reference":"pinned-doc-url",
                        "reference_scope":"PINNED_OFFICIAL_DOCUMENT_CURRENT_URL",
                        "content_sha256":"3"*64,
                        "lifecycle":"PUBLIC_METADATA_UNVERIFIED",
                        "human_approved":False, "export_allowed":False}]}
        signed = {"status":"EXISTING_OWNER_SIGNED_RULEPACKS_VERIFIED_READ_ONLY",
                  "items":[{
                      "item_id":"4"*64,
                      "kind":"PREVENTION_RULE",
                      "rule_id":"PY_SCANDIR_SHARED_ITERATOR_RACE",
                      "pack_serial":4,
                      "source_package_sha256":"5"*64,
                      "verification":"OWNER_SIGNED_VERIFIED_AT_INSPECTION_TIME",
                      "approval_basis":"OWNER_RISK_ACCEPTED_CI_ONLY",
                      "independent_qa_approved":False,
                      "new_package_export_allowed":False}]}
        p8 = {"status":"P8_HASH_CHAIN_EXPERIENCE_SEARCHABLE_NO_GO",
              "items":[{
                  "library_item_id":"6"*64,
                  "experiment_id":"UCIE_LIBRARY_EXACT_KEY_INDEX_EXPERIMENT_V1",
                  "workload_id":"UCIE_FIRST_PARTY_ROWS_256",
                  "production_adopted":False}]}
        w05 = {"status":"UCIE_FIRST_PARTY_W05_EXPERIENCE_READ_ONLY",
               "recorded_count":1,"returned_count":1, "items":[{
                   "experience_id":"7"*64,
                   "kind":"REUSABLE_SKILL",
                   "source_id":"repo:python/cpython",
                   "public_url":"https://github.com/python/cpython/pull/153462",
                   "purpose_code":"SKILL_TEST_AUTOMATION",
                   "upstream_capability_verified":False,
                   "approved_or_exportable":False}]}
        params = dict(query="", domain=None, limit=8, public=public,
                      official=official, signed=signed, p8=p8, w05=w05)
        view = product._bounded_catalog_view(**params)
        self.assertEqual(view["matches_in_loaded_windows"], 5)
        self.assertEqual([x["shelf"] for x in view["items"]], [
            "SIGNED_MANUAL_RULE", "PUBLIC_CANDIDATE", "OFFICIAL_METADATA",
            "UCIE_CANDIDATE_TRIAL_EXPERIENCE", "UCIE_SYNTHETIC_EXPERIENCE"])
        self.assertTrue(all(x["export_allowed"] is False for x in view["items"]))
        self.assertEqual(view["items"][0]["independent_qa_approved"], False)
        self.assertFalse(view["v1_accepted"])
        filtered = product._bounded_catalog_view(**{**params,"query":"SCANDIR"})
        self.assertEqual(filtered["matches_in_loaded_windows"], 2)
        self.assertEqual({x["shelf"] for x in filtered["items"]},
                         {"SIGNED_MANUAL_RULE", "PUBLIC_CANDIDATE"})
        typed = product._bounded_catalog_view(**{
            **params, "domain":"Python", "query":"", "limit":2})
        self.assertEqual(typed["matches_in_loaded_windows"], 1)
        self.assertEqual(typed["items"][0]["shelf"], "PUBLIC_CANDIDATE")
        limited = product._bounded_catalog_view(**{
            **params, "limit":2})
        self.assertEqual(limited["returned_count"],2)
        self.assertEqual(limited["omitted_from_loaded_windows"],3)
        for updates in (
            {"public":{**public,"items":[{
                **public["items"][0],"human_approved":True}]}},
            {"official":{**official,"items":[{
                **official["items"][0],"export_allowed":True}]}},
            {"signed":{**signed,"items":[{
                **signed["items"][0],"independent_qa_approved":True}]}},
            {"p8":{**p8,"items":[{
                **p8["items"][0],"production_adopted":True}]}},
            {"w05":{**w05,"items":[{
                **w05["items"][0],"upstream_capability_verified":True}]}},
        ):
            with self.subTest(updates=tuple(updates)):
                with self.assertRaises(product.ProductIntegrationError):
                    product._bounded_catalog_view(**{**params,**updates})

    def test_actual_w05_experience_is_comparable_in_product_without_upstream_execution(self):
        """Actual original W05 hash-chained reader, not a fabricated receipt."""
        repo = "python/cpython"
        pr = {"number": 123456, "title": "Add test automation helpers",
              "merged_at": "2026-10-10T12:00:00Z",
              "merge_commit_sha": "a" * 40,
              "html_url": "https://github.com/python/cpython/pull/123456",
              "base": {"repo": {"full_name": repo}}}
        out = run_capability_cycle(
            self.root, source_rows=[pr], source_id="repo:" + repo,
            record=True, now=datetime(2026, 10, 29, tzinfo=timezone.utc))
        self.assertTrue(out["new_event_written"])
        trial = out["trial_receipt"]
        self.assertFalse(trial["upstream_tested"])
        ledger = self.root / "runtime" / "ucie_p8_w05_capability_experience_v1.jsonl"
        self.assertTrue(ledger.is_file())
        before = ledger.read_bytes()
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("product cannot fetch upstream code")):
            found = product.integrated_product_preview(
                self.root, query="SKILL_TEST_AUTOMATION",
                domain="Python", limit=5)
        self.assertEqual(ledger.read_bytes(), before)
        compare = found["capability_experience_comparison"]
        self.assertEqual(compare["returned_count"], 1)
        row = compare["items"][0]
        self.assertEqual(row["source_id"], "repo:python/cpython")
        self.assertEqual(row["purpose_code"], "SKILL_TEST_AUTOMATION")
        self.assertEqual(row["kind"], "REUSABLE_SKILL")
        self.assertEqual(row["baseline_operations"], trial["baseline_operations"])
        self.assertEqual(row["candidate_operations"], trial["candidate_operations"])
        self.assertEqual(row["domain"], "Python")
        self.assertEqual(row["synthetic_rows"], trial["rows"])
        self.assertEqual(row["synthetic_queries"], trial["queries"])
        self.assertFalse(row["upstream_code_tested"])
        self.assertFalse(row["owner_approved"])
        self.assertFalse(row["export_allowed"])
        self.assertFalse(compare["cross_candidate_speed_ranked"])
        self.assertFalse(found["v1_accepted"])
        self.assertEqual(compare["operating_database_writes"], 0)
        self.assertEqual(compare["network_requests"], 0)
        excluded = product.integrated_product_preview(
            self.root, query="SKILL_TEST_AUTOMATION", domain="Git", limit=5)
        self.assertEqual(
            excluded["capability_experience_comparison"]["returned_count"], 0)

    def test_capability_comparison_bounded_and_fails_closed_on_forged_status(self):
        good = {
            "experience_id": "c" * 64, "candidate_id": "a" * 64,
            "kind": "REUSABLE_SKILL", "purpose_code": "SKILL_TEST_AUTOMATION",
            "recipe_id": "TAGGED_TEST_CASE_LOOKUP_V1",
            "source_id": "repo:python/cpython",
            "public_url": "https://github.com/python/cpython/pull/123456",
            "workload_sha256": "b" * 64, "rows": 128, "queries": 24,
            "baseline_operations": 3072, "candidate_operations": 300,
            "baseline_median_ns": 700, "candidate_median_ns": 400,
            "equivalent": True, "decision": "RETEST_FIRST_PARTY_RECIPE",
            "first_party_synthetic_only": True,
            "upstream_capability_verified": False,
            "approved_or_exportable": False,
        }
        history = {
            "status": "UCIE_FIRST_PARTY_W05_EXPERIENCE_READ_ONLY",
            "recorded_count": 2, "returned_count": 2,
            "items": [good, {**good, "candidate_id": "d"*64,
                              "experience_id": "e"*64}],
        }
        view = product._compare_existing_capability_experiences(
            history=history, query="SKILL", domain=None, limit=1)
        self.assertEqual(view["returned_count"], 1)
        self.assertEqual(view["matches_in_loaded_experience_window"], 2)
        self.assertEqual(view["same_workload_review_groups"], 1)
        self.assertEqual(view["items"][0]["baseline_operations"], 3072)
        self.assertFalse(view["cross_candidate_speed_ranked"])
        self.assertFalse(view["full_history_comparison_complete"])
        for override in (
            {"upstream_capability_verified": True},
            {"first_party_synthetic_only": False},
            {"approved_or_exportable": True},
            {"baseline_operations": 0},
            {"candidate_operations": 0},
            {"equivalent": False},
            {"source_id": "repo:unapproved/repository"},
        ):
            with self.subTest(override=override):
                tampered = {**history, "items": [{**good, **override}]}
                with self.assertRaises(product.ProductIntegrationError):
                    product._compare_existing_capability_experiences(
                        history=tampered, query="", domain=None, limit=5)

    def test_failure_in_one_critical_ledger_must_not_be_claimed_pass(self):
        with patch("ucie_miner.product_v1.search_existing_public_library",
                   side_effect=ValueError("invalid Stage12 provenance")):
            with self.assertRaises(ValueError):
                product.integrated_product_preview(self.root)
        with patch("sys.argv", [
            "product_v1", "--ucie-root", str(self.root)]):
            with patch("ucie_miner.product_v1.search_existing_public_library",
                       side_effect=ValueError("bad evidence")):
                with patch("builtins.print") as printed:
                    self.assertEqual(product.main(), 2)
        payload = json.loads(printed.call_args.args[0])
        self.assertEqual(payload["status"], "P9_PRODUCT_FAIL_CLOSED")
        self.assertFalse(payload["v1_accepted"])

    def test_fresh_isolated_p9_cli_never_imports_optional_signed_verifier(self):
        """Regression for host without ucie_public.fifth_owner_addendum."""
        source = str(Path(product.__file__).resolve().parents[1])
        runner = (
            "import builtins,contextlib,io,json,sys\n"
            "from pathlib import Path\n"
            "original=builtins.__import__\n"
            "def fail_signed(name,*a,**kw):\n"
            "    if name.endswith('signed_rule_library') or name.endswith('fifth_owner_addendum'):\n"
            "        raise ModuleNotFoundError('simulated missing Serial5 addendum',name='ucie_public.fifth_owner_addendum')\n"
            "    return original(name,*a,**kw)\n"
            "builtins.__import__=fail_signed\n"
            "sys.path.insert(0,sys.argv[1])\n"
            "from ucie_miner import product_v1 as p\n"
            "root=Path(sys.argv[2])\n"
            "sys.argv=['product_v1','--ucie-root',str(root),'--demo']\n"
            "output=io.StringIO()\n"
            "with contextlib.redirect_stdout(output):\n"
            "    code=p.main()\n"
            "obj=json.loads(output.getvalue())\n"
            "assert code==0 and obj['status']=='P9_INTEGRATED_READ_ONLY_PRODUCT_PREVIEW_NO_GO'\n"
            "assert obj['signed_rules']['status']=='NOT_INSPECTED_NO_GO'\n"
            "assert obj['portable_first_party_consumer_demo']['all_queries_equivalent']\n"
            "assert obj['network_requests']==0 and obj['operating_database_writes']==0\n"
            "try:\n"
            "    p.integrated_product_preview(root,signed_serial4=root/'not_real_pack',owner_public_trust=root/'not_real_trust')\n"
            "except p.ProductIntegrationError as err:\n"
            "    assert str(err)=='EXPLICIT_SIGNED_RULEPACK_VERIFIER_DEPENDENCY_MISSING_NO_GO'\n"
            "else:\n"
            "    raise AssertionError('explicit signed verifier must fail closed')\n"
            "print(json.dumps({'status':'MISSING_OPTIONAL_SIGNED_DEPENDENCY_HANDLED','exit':code}))\n"
        )
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        process = subprocess.run(
            [sys.executable, "-I", "-c", runner, source, str(self.root)],
            cwd=self.root, env=env, text=True, capture_output=True,
            timeout=30, check=True)
        self.assertEqual(
            json.loads(process.stdout)["status"],
            "MISSING_OPTIONAL_SIGNED_DEPENDENCY_HANDLED")

    def test_cli_readonly_inert_and_explicit_draft_export(self):
        with patch("sys.argv", [
            "product_v1", "--ucie-root", str(self.root), "--demo"]):
            with patch("builtins.print") as printed:
                self.assertEqual(product.main(), 0)
        obj = json.loads(printed.call_args.args[0])
        self.assertEqual(obj["status"], "P9_INTEGRATED_READ_ONLY_PRODUCT_PREVIEW_NO_GO")
        self.assertFalse((self.root / "runtime" / "exports").exists())
        with patch("sys.argv", [
            "product_v1", "--ucie-root", str(self.root), "--export-draft"]):
            with patch("builtins.print") as printed:
                self.assertEqual(product.main(), 0)
        obj = json.loads(printed.call_args.args[0])
        self.assertEqual(obj["status"], "UCIE_ONLY_DRAFT_WRITTEN_NOT_RELEASED")
        self.assertTrue((self.root / obj["relative_path"]).is_file())
        self.assertFalse(obj["v1_accepted"])
        with patch("sys.argv", [
            "product_v1", "--ucie-root", str(self.root),
            "--export-draft", "--demo"]):
            with patch("builtins.print") as printed:
                self.assertEqual(product.main(), 2)
        obj = json.loads(printed.call_args.args[0])
        self.assertEqual(obj["status"], "P9_PRODUCT_FAIL_CLOSED")


def io_bytes(data: bytes):
    from io import BytesIO
    return BytesIO(data)


if __name__ == "__main__":
    unittest.main()
