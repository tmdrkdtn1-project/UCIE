"""P9 integrated product acceptance *negative gates* and standalone draft consumer."""
from __future__ import annotations

from copy import deepcopy
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
