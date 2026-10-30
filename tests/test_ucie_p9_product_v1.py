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
from ucie_miner.p9_pinned_public_review import lookup_pinned_review
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

    def test_w09_reference_requires_selected_valid_signed_pack_and_no_draft_mode(self):
        # No implicit trust from a selected ID or an unverified candidate.
        with self.assertRaises(product.ProductIntegrationError):
            product.integrated_product_preview(
                self.root, select_item_id="a" * 64,
                include_consumer_reference=True)
        with self.assertRaises(product.ProductIntegrationError):
            product.integrated_product_preview(
                self.root, include_consumer_reference=True)
        with self.assertRaises(product.ProductIntegrationError):
            product.integrated_product_preview(
                self.root, include_consumer_reference=1)

        # Even a supposedly signed-looking dict cannot become a reference
        # without the original W07/W09 cryptographic verification.
        forged = {
            "selection_status": "CANDIDATE_OR_EXPERIENCE_REUSE_BLOCKED",
            "library_item_id": "a" * 64,
            "manual_reference_to_existing_pack_allowed": False,
            "new_generic_package_export_allowed": False,
            "production_auto_apply_allowed": False,
            "approval_basis": "OWNER_RISK_ACCEPTED_CI_ONLY",
        }
        with patch("ucie_miner.signed_rule_library."
                   "build_existing_pack_consumer_descriptor",
                   side_effect=AssertionError("must never invoke W09 for unsigned")):
            with self.assertRaises(product.ProductIntegrationError):
                product._selected_w09_manual_consumer_reference(
                    self.root, selection=forged,
                    serial4_pack=self.root / "untrusted.zip",
                    owner_public_trust=self.root / "untrusted-public.pem",
                    serial5_pack=None)

    def test_bounded_reuse_selection_never_promotes_unsigned_candidates(self):
        item = {
            "shelf": "PUBLIC_CANDIDATE", "library_item_id": "a" * 64,
            "verification": "UNVERIFIED_CANDIDATE_ONLY",
            "version_scope": "UNDETERMINED",
            "source_license_status": "NOT_ATTESTED_PER_REVISION",
            "export_allowed": False,
        }
        catalog = {
            "status": "READ_ONLY_BOUNDED_MULTI_SHELF_SEARCH_NO_GO",
            "items": [item], "returned_count": 1,
            "omitted_from_loaded_windows": 2,
            "source_window_truncated": True,
        }
        out = product._reuse_eligibility(
            catalog=catalog, signed=None, selected_item_id="a" * 64)
        self.assertEqual(out["schema"], "UCIE_V1_BOUNDED_REUSE_ELIGIBILITY_V1")
        self.assertEqual(out["returned_count"], 1)
        self.assertTrue(out["catalog_window_truncated"])
        self.assertFalse(out["full_catalog_inspected"])
        self.assertFalse(out["original_signed_verifier_used"])
        self.assertEqual(out["manual_reference_count_in_loaded_window"], 0)
        self.assertEqual(out["new_generic_package_exportable_count"], 0)
        selected = out["selected_item"]
        self.assertEqual(selected["selection_status"],
                         "CANDIDATE_OR_EXPERIENCE_REUSE_BLOCKED")
        self.assertEqual(selected["permitted_action"], "EVIDENCE_REVIEW_ONLY")
        self.assertFalse(selected["manual_reference_to_existing_pack_allowed"])
        self.assertFalse(selected["new_generic_package_export_allowed"])
        self.assertFalse(selected["production_auto_apply_allowed"])
        self.assertIn("VERSION_APPLICABILITY_NOT_CONFIRMED",
                      selected["review_blockers"])
        no_match = product._reuse_eligibility(
            catalog=catalog, signed=None, selected_item_id="b" * 64)
        self.assertEqual(no_match["selected_item"]["selection_status"],
                         "NOT_IN_CURRENT_BOUNDED_QUERY_WINDOW_NO_GO")
        self.assertFalse(
            no_match["selected_item"]["not_found_in_full_catalog_proven"])
        for malformed in ("../../secret", "", "a" * 63, "X" * 64, 42):
            with self.subTest(malformed=malformed):
                with self.assertRaises(product.ProductIntegrationError):
                    product._reuse_eligibility(
                        catalog=catalog, signed=None,
                        selected_item_id=malformed)
        forged = {**catalog, "items": [{**item, "export_allowed": True}]}
        with self.assertRaises(product.ProductIntegrationError):
            product._reuse_eligibility(
                catalog=forged, signed=None, selected_item_id=None)
        for forged_claim in (
            {"version_scope": "3.15.0"},
            {"source_license_status": "LICENSE_APPROVED"},
        ):
            with self.subTest(forged_claim=forged_claim):
                with self.assertRaises(product.ProductIntegrationError):
                    product._reuse_eligibility(
                        catalog={**catalog, "items": [{**item, **forged_claim}]},
                        signed=None, selected_item_id=None)
        signed_claim = {**catalog, "items": [{
            "shelf": "SIGNED_MANUAL_RULE", "library_item_id": "a" * 64,
            "verification": "OWNER_SIGNED_VERIFIED_AT_INSPECTION_TIME",
            "rule_id": "UNTRUSTED", "pack_serial": 4,
            "source_package_sha256": "b" * 64,
            "independent_qa_approved": False,
            "export_allowed": False,
        }]}
        with self.assertRaises(product.ProductIntegrationError):
            product._reuse_eligibility(
                catalog=signed_claim, signed=None, selected_item_id=None)

    def test_integrated_reuse_window_absence_is_not_catalog_absence(self):
        out = product.integrated_product_preview(
            self.root, query="", limit=5, select_item_id="a" * 64)
        reuse = out["reuse_eligibility"]
        self.assertEqual(reuse["selected_item"]["selection_status"],
                         "NOT_IN_CURRENT_BOUNDED_QUERY_WINDOW_NO_GO")
        self.assertEqual(reuse["manual_reference_count_in_loaded_window"], 0)
        self.assertEqual(reuse["new_generic_package_exportable_count"], 0)
        self.assertFalse(reuse["original_signed_verifier_used"])
        self.assertFalse(reuse["new_package_released"])
        self.assertEqual(reuse["network_requests"], 0)
        self.assertEqual(reuse["operating_database_writes"], 0)
        self.assertFalse(out["v1_accepted"])

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
        self.assertEqual(manifest["version"], "1.3.0")
        self.assertEqual(manifest["consumer_api_version"], "1.1.0")
        self.assertEqual(manifest["supported_unverified_metadata_kinds"],
                         sorted(portable.KINDS))
        with tempfile.TemporaryDirectory() as temp:
            f = Path(temp) / "draft.zip"
            f.write_bytes(a)
            with ZipFile(f) as z:
                self.assertEqual(z.namelist(),
                                 ["portable_exact.py", "__main__.py", "RIGHTS_SECURITY.txt", "MANIFEST.json", "README.txt"])
                self.assertEqual(z.read("MANIFEST.json"),
                                 json.dumps(manifest, sort_keys=True,
                                            separators=(",", ":")).encode("ascii"))
                self.assertEqual(z.read("portable_exact.py"),
                                 Path(portable.__file__).read_bytes())
                self.assertEqual(z.read("__main__.py"),
                                 Path(product.__file__).with_name(
                                     "portable_zip_main.py").read_bytes())
                self.assertEqual(manifest["standalone_cli_file"], "__main__.py")
                self.assertEqual(manifest["rights_security_file"], "RIGHTS_SECURITY.txt")
                self.assertEqual(z.read("RIGHTS_SECURITY.txt"),
                                 product._portable_rights_security_text())
                self.assertFalse(manifest["owner_source_license_declared_and_approved"])
                self.assertEqual(manifest["standalone_max_stdin_bytes"], 32768)
                self.assertEqual(manifest["standalone_max_stdout_bytes"], 65536)
                self.assertTrue(all(member.create_system == 3
                                    for member in z.infolist()))
                self.assertEqual(manifest["standalone_cli_sha256"],
                                 __import__("hashlib").sha256(
                                     z.read("__main__.py")).hexdigest())
                self.assertFalse(manifest["signed"])
                self.assertNotIn(b"upstream PR contents", z.read("portable_exact.py"))

    def test_portable_unverified_engine_skill_learning_kinds_and_strict_pr_identity(self):
        source = "repo:python/cpython"
        rows = []
        for i, kind in enumerate(
                ("DEVELOPMENT_ENGINE", "REUSABLE_SKILL", "LEARNING_LOGIC"), 1):
            rows.append({
                "source_id": source, "domain": "Python",
                "kind": kind, "purpose_code": "SYNTHETIC_EXACT_LOOKUP",
                "library_item_id": f"{i:064x}",
                "public_url": f"https://github.com/python/cpython/pull/{i}",
                "evidence_sha256": f"{i + 10:064x}",
                "human_approved": False, "export_allowed": False,
            })
        q = tuple((source, "Python", kind, "SYNTHETIC_EXACT_LOOKUP")
                  for kind in ("DEVELOPMENT_ENGINE", "REUSABLE_SKILL",
                               "LEARNING_LOGIC"))
        found = portable.search_public_metadata(rows, queries=q)
        self.assertEqual(len(found["results"]), 3)
        self.assertTrue(all(x["total_matches"] == 1 for x in found["results"]))
        self.assertEqual(found["approved_or_exportable_items"], 0)
        self.assertFalse(found["production_release_approved"])
        for suffix in ("/extra", "-forged", "?query=bad", "#fragment", "x"):
            altered = [dict(row) for row in rows]
            altered[0]["public_url"] += suffix
            with self.subTest(suffix=suffix):
                with self.assertRaises(portable.PortableLookupError):
                    portable.search_public_metadata(altered, queries=q)
        for kind in ("PRODUCTION_APPROVED_ENGINE", "EXECUTABLE_UPSTREAM_CODE"):
            with self.assertRaises(portable.PortableLookupError):
                portable.search_public_metadata(
                    [{**rows[0], "kind": kind}], queries=q)

    def test_actual_independent_consumer_import_works_without_ucie_package(self):
        payload, _manifest = product.build_draft_package_bytes()
        with tempfile.TemporaryDirectory() as temp:
            isolated = Path(temp)
            with ZipFile(io_bytes(payload)) as z:
                z.extract("portable_exact.py", path=isolated)
            consumer_script = (
                "import json,runpy,sys\n"
                "m=runpy.run_path(sys.argv[1]); assert m['VERSION']=='1.1.0'\n"
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
                "for n,kind in enumerate(('DEVELOPMENT_ENGINE','REUSABLE_SKILL','LEARNING_LOGIC'),2):\n"
                "    candidate=dict(rows[0],kind=kind,library_item_id=f'{n:064x}',\n"
                "                   public_url=f'https://github.com/python/cpython/pull/{n}',\n"
                "                   evidence_sha256=f'{n+10:064x}')\n"
                "    k=key[:2]+(kind,key[3])\n"
                "    hit=m['search_public_metadata']([candidate],queries=(k,))\n"
                "    assert hit['results'][0]['total_matches']==1\n"
                "    assert hit['approved_or_exportable_items']==0\n"
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
        with self.assertRaises(product.ProductIntegrationError):
            product.verify_existing_draft(self.root)
        first = product.explicitly_export_draft(self.root)
        self.assertTrue(first["created"])
        self.assertFalse(first["production_release_approved"])
        self.assertFalse(first["standalone_consumer_qa_attested"])
        p = self.root / first["relative_path"]
        original = p.read_bytes()
        verification = product.verify_existing_draft(self.root)
        self.assertEqual(verification["sha256"], first["sha256"])
        self.assertEqual(verification["code_sha256"], first["code_sha256"])
        self.assertEqual(verification["status"],
                         "UCIE_LOCAL_DRAFT_BYTES_VERIFIED_NOT_RELEASED")
        self.assertTrue(verification["canonical_local_source_match"])
        self.assertFalse(verification["independent_signature_verified"])
        self.assertFalse(verification["production_release_approved"])
        self.assertEqual(p.read_bytes(), original)
        second = product.explicitly_export_draft(self.root)
        self.assertFalse(second["created"])
        self.assertEqual(original, p.read_bytes())
        p.write_bytes(b"DIFFERENT")
        with self.assertRaises(product.ProductIntegrationError):
            product.verify_existing_draft(self.root)
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
        reviews = out["library_revision_review_queue"]
        self.assertEqual(reviews["candidate_count_in_loaded_window"], 1)
        self.assertEqual(reviews["returned_count"], 1)
        self.assertFalse(reviews["new_revision_persisted"])
        self.assertFalse(reviews["reviewer_approved"])
        proposal = reviews["items"][0]
        self.assertEqual(proposal["source_library_item_id"],
                         experience["event_sha256"])
        self.assertEqual(proposal["target_ucie_component"],
                         "ucie_miner.library_exact_index:EXACT_QUERY_POLICY")
        self.assertFalse(proposal["production_improvement_verified"])
        unfiltered = product.integrated_product_preview(
            self.root, query="", limit=5)
        linked = [item for item in unfiltered["unified_catalog_search"]["items"]
                  if item["shelf"] == "UCIE_SYNTHETIC_EXPERIENCE"]
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0]["revision_review_proposal_id"],
                         proposal["proposal_id"])
        self.assertEqual([p.read_bytes() for p in checks], before)

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
            # A specific W04 query may match no portable PRs. Verify the
            # actual complete bounded Stage12 window as a separate handoff.
            all_out = product.integrated_product_preview(
                self.root, query="", limit=5)
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
        self.assertFalse(out["source_linked_portable_handoff"]["v1_accepted"])
        handoff = all_out["source_linked_portable_handoff"]
        self.assertEqual(handoff["schema"],
                         "UCIE_P9_SOURCE_LINKED_PORTABLE_HANDOFF_V1")
        self.assertEqual(handoff["status"],
                         "SOURCE_LINKED_PUBLIC_PR_METADATA_PORTABLE_PARITY_NO_GO")
        self.assertGreater(handoff["portable_candidate_items"], 0)
        self.assertTrue(handoff["in_process_exact_search_equivalent"])
        self.assertFalse(handoff["independent_consumer_executed_here"])
        self.assertFalse(handoff["package_released"])
        self.assertFalse(handoff["v1_accepted"])
        payload = handoff["consumer_payload"]
        self.assertEqual(payload["limit"], 5)
        self.assertEqual(len(payload["items"]), handoff["portable_candidate_items"])
        self.assertEqual(
            {row["library_item_id"] for row in payload["items"]},
            {row["library_item_id"] for row in
             all_out["public_candidate_library"]["items"]
             if "/pull/" in row["public_url"]})
        self.assertTrue(all(not row["export_allowed"] and
                            not row["human_approved"] for row in payload["items"]))

        # Actual independent stdlib-only P7 consumer, using this test fixture's
        # original source-linked W04 metadata rather than canned demo rows.
        bundle, _ = product.build_draft_package_bytes()
        with tempfile.TemporaryDirectory() as work:
            isolated = Path(work)
            with ZipFile(io_bytes(bundle)) as archive:
                archive.extract("portable_exact.py", path=isolated)
            script = (
                "import json,runpy,sys\n"
                "payload=json.load(sys.stdin)\n"
                "consumer=runpy.run_path(sys.argv[1])\n"
                "queries=tuple(tuple(q) for q in payload['queries'])\n"
                "out=consumer['search_public_metadata']("
                "payload['items'],queries=queries,limit=payload['limit'])\n"
                "assert not out['production_release_approved']\n"
                "assert out['approved_or_exportable_items']==0\n"
                "print(json.dumps({'matched':sum(x['total_matches'] "
                "for x in out['results']),"
                "'query_count':out['query_count'],"
                "'schema':out['schema']}))\n"
            )
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            observed = subprocess.run(
                [sys.executable, "-I", "-c", script,
                 str(isolated / "portable_exact.py")],
                input=json.dumps(payload, sort_keys=True),
                text=True, capture_output=True, cwd=isolated,
                env=env, check=True, timeout=25)
            seen = json.loads(observed.stdout)
        self.assertEqual(seen["matched"], handoff["portable_candidate_items"])
        self.assertEqual(seen["query_count"], len(payload["queries"]))
        self.assertEqual(seen["schema"], portable.SCHEMA)
        self.assertEqual(before, after)

    def test_portable_public_handoff_rejects_forged_approvals_and_nonpublic_urls(self):
        one = {
            "library_item_id": "a" * 64,
            "kind": "PUBLIC_TECHNICAL_EVIDENCE",
            "source_id": "repo:python/cpython",
            "public_url": "https://github.com/python/cpython/pull/10",
            "domain": "Python", "purpose_code": "API_CONTRACT",
            "evidence_sha256": "b" * 64,
            "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
            "signature_status": "NOT_ATTESTED_BY_THIS_SEARCH",
            "human_approved": False, "export_allowed": False,
        }
        source = {
            "status": "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
            "returned_count": 1, "omitted_count": 0,
            "items": [one],
        }
        valid = product._portable_public_ledger_handoff(source, limit=5)
        self.assertEqual(valid["portable_candidate_items"], 1)
        self.assertTrue(valid["in_process_exact_search_equivalent"])
        self.assertEqual(valid["consumer_payload"]["items"][0]["public_url"],
                         one["public_url"])
        for change in (
            {"human_approved": True}, {"export_allowed": True},
            {"signature_status": "OWNER_SIGNED"},
            {"public_url": "https://github.com/python/cpython/pull/10/extra"},
            {"source_id": "repo:unapproved/repo"},
        ):
            with self.subTest(change=change):
                corrupted = {**source, "items": [{**one, **change}]}
                with self.assertRaises((ValueError, TypeError)):
                    product._portable_public_ledger_handoff(corrupted, limit=5)
        commit = {**one, "source_id": "repo:git/git",
                  "public_url": "https://github.com/git/git/commit/" + "c" * 40,
                  "domain": "Git"}
        only_commit = product._portable_public_ledger_handoff(
            {**source, "items": [commit]}, limit=5)
        self.assertEqual(only_commit["portable_candidate_items"], 0)
        self.assertEqual(only_commit["unsupported_reference_count"], 1)
        self.assertFalse(only_commit["in_process_exact_search_equivalent"])
        incomplete = product._portable_public_ledger_handoff({
            "status": "SOURCE_LINKAGE_INCOMPLETE_NO_GO",
            "items": [], "returned_count": 0,
        }, limit=5)
        self.assertIsNone(incomplete["consumer_payload"])
        self.assertFalse(incomplete["v1_accepted"])

    def test_p9_version_license_qa_readiness_reuses_real_ucie_public_ledger(self):
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
        files = [runtime / DB_NAME,
                 runtime / "stage12_unverified_review.sqlite3"]
        before = [p.read_bytes() for p in files]
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("P9 evidence gate cannot fetch")):
            out = product.integrated_product_preview(
                self.root, query="", limit=5)
        self.assertEqual([p.read_bytes() for p in files], before)
        gate = out["source_version_rights_qa_readiness"]
        self.assertEqual(gate["schema"],
                         "UCIE_P9_SOURCE_VERSION_RIGHTS_QA_READINESS_V1")
        self.assertTrue(gate["public_reader_source_linked"])
        self.assertFalse(gate["official_reader_available"])
        self.assertGreater(gate["public_window_count"], 0)
        self.assertEqual(gate["official_window_count"], 0)
        self.assertEqual(gate["readiness_record_count"],
                         gate["public_window_count"])
        self.assertTrue(all(row["revision_hint"] and
                            not row["runtime_version_applicability_verified"]
                            and not row["source_rights_for_export_verified"]
                            and not row["export_allowed"] for row in gate["rows"]))
        self.assertIn("W06_OFFICIAL_EVIDENCE_LEDGER_NOT_READY",
                      gate["review_blockers"])
        self.assertIn("PER_REVISION_SOURCE_RIGHTS_NOT_REVIEWED_FOR_EXPORT",
                      out["gates_blocking_product_acceptance"])
        self.assertFalse(gate["all_required_evidence_accepted"])
        self.assertFalse(out["v1_accepted"])
        self.assertEqual(gate["database_writes"], 0)
        self.assertEqual(gate["network_requests"], 0)

    def test_p9_evidence_gate_reports_exact_scope_and_rejects_forged_approval(self):
        sources = product.preview_source_registry(include_research=False)
        public_row = {
            "library_item_id": "1" * 64,
            "kind": "PUBLIC_TECHNICAL_EVIDENCE",
            "source_id": "repo:python/cpython",
            "public_url": "https://github.com/python/cpython/pull/153462",
            "evidence_sha256": "2" * 64, "revision_hint": "3" * 40,
            "version_scope_claim": "UNDETERMINED",
            "license_status": "NOT_ATTESTED_PER_REVISION",
            "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
            "signature_status": "NOT_ATTESTED_BY_THIS_SEARCH",
            "human_approved": False, "export_allowed": False,
        }
        official_row = {
            "kind": "OFFICIAL_RELEASE_EVIDENCE",
            "source_id": "repo:python/cpython",
            "public_url": "https://github.com/python/cpython/releases",
            "reference_scope": "PUBLIC_REPOSITORY_RELEASE_INDEX_NOT_EXACT_RELEASE",
            "content_sha256": "4" * 64,
            "lifecycle": "PUBLIC_METADATA_UNVERIFIED",
            "source_license_reviewed": False,
            "verified_applicability": False,
            "human_approved": False, "export_allowed": False,
        }
        public = {
            "status": "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
            "returned_count": 1, "omitted_count": 5,
            "items": [public_row],
        }
        official = {
            "status": "STAGE14_OFFICIAL_METADATA_READ_ONLY_UNVERIFIED_NO_GO",
            "returned_count": 1, "omitted_count": 1,
            "items": [official_row],
        }
        params = dict(sources=sources, public=public, official=official,
                      limit=5)
        gate = product._evidence_readiness(**params)
        self.assertEqual(gate["readiness_record_count"], 2)
        self.assertTrue(gate["source_window_truncated"])
        self.assertFalse(gate["full_public_universe_inspected"])
        self.assertFalse(gate["all_required_evidence_accepted"])
        self.assertEqual(gate["rows"][1]["reference_scope"],
                         "PUBLIC_REPOSITORY_RELEASE_INDEX_NOT_EXACT_RELEASE")
        self.assertTrue(all(not x["independent_qa_verified"]
                            for x in gate["rows"]))
        self.assertEqual(gate, product._evidence_readiness(**params))
        for field, altered in (
            ("source_id", "repo:unapproved/repo"),
            ("license_status", "LICENSE_APPROVED"),
            ("version_scope_claim", "Python>=3.15"),
            ("human_approved", True),
            ("export_allowed", True),
            ("evidence_sha256", "wrong"),
            ("revision_hint", "not-a-merge-sha"),
        ):
            with self.subTest(public_field=field):
                forged = {**public, "items": [{
                    **public_row, field: altered,
                }]}
                with self.assertRaises(product.ProductIntegrationError):
                    product._evidence_readiness(
                        **{**params, "public": forged})
        for field, altered in (
            ("source_license_reviewed", True),
            ("verified_applicability", True),
            ("human_approved", True),
            ("export_allowed", True),
            ("content_sha256", "wrong"),
            ("reference_scope", "EXACT_RELEASE_VERIFIED"),
        ):
            with self.subTest(official_field=field):
                forged = {**official, "items": [{
                    **official_row, field: altered,
                }]}
                with self.assertRaises(product.ProductIntegrationError):
                    product._evidence_readiness(
                        **{**params, "official": forged})
        absent = product._evidence_readiness(
            sources=sources,
            public={"status": "SOURCE_LINKAGE_INCOMPLETE_NO_GO",
                    "items": [], "returned_count": 0},
            official={"status": "STAGE14_OFFICIAL_LEDGER_ABSENT_NO_GO",
                      "items": [], "returned_count": 0},
            limit=5)
        self.assertEqual(absent["readiness_record_count"], 0)
        self.assertIn("NO_MATCHING_EVIDENCE_IN_BOUNDED_READ_WINDOW",
                      absent["review_blockers"])
        self.assertFalse(absent["v1_accepted"])

    def test_p9_pinned_upstream_pr_repository_license_and_release_divergence(self):
        """Three exact real public identities, not synthetic upstream execution."""
        pinned = [
            ("repo:python/cpython", 153462,
             "999a046b24cff4ba0e72b574196721f66bd08237",
             "20cf39097c68baa17cc566b64e76d34ebf034044",
             "v3.15.0", "d220409a13b77de7a6c30abe16ea90db01528edc"),
            ("repo:PowerShell/PowerShell", 28042,
             "bd8cb01a7d5b86129c45eaa14ab5830a63b1283f",
             "b2f52a2bad4e27e2d9c68a755abb74cb8943f2fa",
             "v7.6.6", "f260eb9c31ec72c5282f98e5ea24d9be4f8d7536"),
            ("repo:PowerShell/PowerShell", 28087,
             "373f6a7b7972a0a4b73bfd9737a0d768d28b347e",
             "b2f52a2bad4e27e2d9c68a755abb74cb8943f2fa",
             "v7.6.6", "f260eb9c31ec72c5282f98e5ea24d9be4f8d7536"),
        ]
        sources = product.preview_source_registry(include_research=False)
        public_rows = []
        for n, (source_id, number, merge, license_blob,
                tag, tag_sha) in enumerate(pinned):
            url = "https://github.com/" + source_id[5:] + f"/pull/{number}"
            inspected = lookup_pinned_review(
                source_id=source_id, public_url=url, merge_sha=merge)
            self.assertEqual(inspected["repository_license_blob_sha"],
                             license_blob)
            self.assertEqual(inspected["release_tag_commit_sha"], tag_sha)
            self.assertEqual(inspected["upstream_release_tag"], tag)
            self.assertEqual(inspected["compare_status"], "diverged")
            checked_source = inspected["examined_tag_source_patch"]
            if number == 28087:
                self.assertEqual(checked_source["status"],
                    "SPECIFIC_PR28087_IMPLEMENTATION_ABSENT_IN_EXAMINED_TAG_SOURCE")
                self.assertEqual(checked_source["fix_commit_blob_git_sha1"],
                                 "e6a89e2a11732dfc0ed36af8194432155265486c")
                self.assertEqual(checked_source["tag_commit_blob_git_sha1"],
                                 "3d1b66933d26f5e55632184e0981c67771c4d853")
                self.assertTrue(checked_source["fixed_helper_present_at_merge"])
                self.assertFalse(checked_source["fixed_helper_present_in_tag"])
                self.assertTrue(checked_source["pre_fix_condition_present_in_tag"])
                self.assertFalse(checked_source["equivalent_backport_excluded"])
                self.assertTrue(checked_source["runtime_bug_reproduced_for_tag"])
                self.assertEqual(checked_source["runtime_bug_reproduction_scope"],
                                 "OFFICIAL_7_6_6_LINUX_X64_AND_WINDOWS_X64_RELEASE_BINARIES")
                self.assertFalse(checked_source["runtime_fix_coverage_verified"])
                released = inspected["official_release_runtime_observation"]
                self.assertEqual(released["status"],
                                 "PINNED_RELEASE_LINUX_X64_BUG_REPRODUCED_NO_GO")
                self.assertEqual(released["runtime_version"], "7.6.6")
                self.assertEqual(released["target_arch"], "linux-x64")
                self.assertEqual(released["dot_prefix_cases_matching_expected"], 0)
                self.assertTrue(released["baseline_case_passed"])
                self.assertTrue(released["guarded_cases_passed"])
                self.assertTrue(released["archive_sha256_verified_against_published_release"])
                self.assertTrue(released["actual_release_binary_executed"])
                self.assertEqual(released["archive_sha256"],
                                 "ddbc4a2d113bbd46d283cfedcbcd117a70caefd7673f41f2b4e0000badf103bc")
                self.assertEqual(released["release_binary_sha256"],
                                 "3c6e4d629571429cf6cc86db94278e2ce17349edbbfe0a0de007bb6bccdbc208")
                self.assertEqual(released["ci_run_id"], 40994655459)
                self.assertFalse(released["windows_release_binary_tested"])
                self.assertFalse(released["same_behavior_on_all_platforms_verified"])
                self.assertFalse(released["equivalent_backports_excluded"])
                self.assertFalse(released["independent_qa_completed"])
                self.assertFalse(released["production_approved"])
                windows = inspected["official_windows_release_runtime_observation"]
                self.assertEqual(windows["status"],
                                 "PINNED_RELEASE_WINDOWS_X64_BUG_REPRODUCED_NO_GO")
                self.assertEqual(windows["runtime_version"], "7.6.6")
                self.assertEqual(windows["target_arch"], "windows-x64")
                self.assertEqual(windows["archive_sha256"],
                    "02fe458be20493fbdf43f61ea20610b811ee6c738ab1676c61b9cfcd1a33c860")
                self.assertEqual(windows["release_binary_sha256"],
                    "bfb46af89433268872ddb43d1ca7a3f433452ee91ed356a9786940f90118e285")
                self.assertEqual(windows["ci_run_id"], 40995356035)
                self.assertTrue(windows["actual_release_binary_executed"])
                self.assertEqual(windows["dot_prefix_cases_matching_expected"], 0)
                self.assertTrue(windows["baseline_case_passed"])
                self.assertTrue(windows["guarded_cases_passed"])
                self.assertFalse(windows["all_platforms_verified"])
                self.assertFalse(windows["independent_qa_completed"])
                self.assertFalse(windows["production_approved"])
                self.assertFalse(windows["auto_promoted"])
            else:
                self.assertIsNone(checked_source)
                self.assertIsNone(inspected["official_release_runtime_observation"])
                self.assertIsNone(inspected["official_windows_release_runtime_observation"])
            self.assertGreater(inspected["release_ahead_by"], 0)
            self.assertGreater(inspected["release_behind_by"], 0)
            self.assertFalse(inspected["release_contains_fix_verified"])
            self.assertFalse(inspected["absence_of_backport_verified"])
            self.assertFalse(inspected["per_file_third_party_license_cleared"])
            self.assertFalse(inspected["legal_signoff_completed"])
            self.assertFalse(inspected["independent_qa_completed"])
            self.assertFalse(inspected["approved_or_exportable"])
            self.assertEqual(inspected["network_requests"], 0)
            self.assertEqual(inspected, lookup_pinned_review(
                source_id=source_id, public_url=url, merge_sha=merge))
            self.assertIsNone(lookup_pinned_review(
                source_id=source_id, public_url=url + "/files", merge_sha=merge))
            self.assertIsNone(lookup_pinned_review(
                source_id=source_id, public_url=url,
                merge_sha="f" * 40))
            public_rows.append({
                "library_item_id": f"{n + 1:064x}",
                "source_id": source_id, "public_url": url,
                "evidence_sha256": f"{n + 11:064x}",
                "revision_hint": merge,
                "version_scope_claim": "UNDETERMINED",
                "license_status": "NOT_ATTESTED_PER_REVISION",
                "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
                "signature_status": "NOT_ATTESTED_BY_THIS_SEARCH",
                "human_approved": False, "export_allowed": False,
            })
        with self.assertRaises(ValueError):
            lookup_pinned_review(
                source_id="repo:unapproved/private",
                public_url="https://github.com/unapproved/private/pull/1",
                merge_sha="1" * 40)
        with self.assertRaises(ValueError):
            lookup_pinned_review(
                source_id="repo:python/cpython",
                public_url="https://github.com/python/cpython/pull/153462",
                merge_sha="garbage")
        preview = product._evidence_readiness(
            sources=sources,
            public={"status": "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
                    "returned_count": 3, "omitted_count": 0,
                    "items": public_rows},
            official={"status": "STAGE14_OFFICIAL_LEDGER_ABSENT_NO_GO",
                      "returned_count": 0, "items": []},
            limit=5)
        self.assertEqual(preview["pinned_public_revision_observations_in_window"], 3)
        self.assertEqual(preview["readiness_record_count"], 3)
        self.assertEqual(preview["rows"][2]["pinned_public_revision_review"][
            "examined_tag_source_patch"]["tag_commit_blob_git_sha1"],
            "3d1b66933d26f5e55632184e0981c67771c4d853")
        self.assertFalse(preview["rows"][2][
            "pinned_public_revision_review"]["release_contains_fix_verified"])
        self.assertTrue(preview["rows"][2]["pinned_public_revision_review"][
            "official_release_runtime_observation"]["actual_release_binary_executed"])
        self.assertTrue(preview["rows"][2]["pinned_public_revision_review"][
            "official_windows_release_runtime_observation"]["actual_release_binary_executed"])
        self.assertFalse(preview["rows"][2]["export_allowed"])
        self.assertFalse(preview["all_required_evidence_accepted"])
        self.assertTrue(all(
            row["repository_license_observed_in_pinned_review"]
            and not row["export_allowed"]
            and not row["pinned_public_revision_review"][
                "release_contains_fix_verified"]
            for row in preview["rows"]))
        self.assertIn("PINNED_RELEASE_ANCESTRY_OR_BACKPORT_NOT_PROVEN",
                      preview["review_blockers"])
        self.assertFalse(preview["all_required_evidence_accepted"])
        altered = dict(public_rows[0], revision_hint="b" * 40)
        # An unreviewed merge SHA must not inherit another revision's evidence.
        unknown = product._evidence_readiness(
            sources=sources,
            public={"status": "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
                    "returned_count": 1, "items": [altered]},
            official={"status": "STAGE14_OFFICIAL_LEDGER_ABSENT_NO_GO",
                      "returned_count": 0, "items": []},
            limit=5)
        self.assertIsNone(unknown["rows"][0]["pinned_public_revision_review"])
        self.assertEqual(unknown["pinned_public_revision_observations_in_window"], 0)

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
        revision = found["library_revision_review_queue"]
        self.assertEqual(revision["candidate_count_in_loaded_window"], 1)
        self.assertEqual(revision["items"][0]["source_shelf"],
                         "UCIE_CANDIDATE_TRIAL_EXPERIENCE")
        self.assertEqual(revision["items"][0][
            "public_candidate_identity_only"]["candidate_id"],
            out["candidate_id"])
        self.assertFalse(revision["items"][0]["library_revision_written"])
        wide = product.integrated_product_preview(
            self.root, query="SKILL_TEST_AUTOMATION", limit=5)
        linked = [item for item in wide["unified_catalog_search"]["items"]
                  if item["shelf"] == "UCIE_CANDIDATE_TRIAL_EXPERIENCE"]
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0]["revision_review_proposal_id"],
                         revision["items"][0]["proposal_id"])
        self.assertEqual(ledger.read_bytes(), before)
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

    def test_p8_review_queue_is_deterministic_bounded_and_rejects_false_promotion(self):
        p8 = {"status": "P8_HASH_CHAIN_EXPERIENCE_SEARCHABLE_NO_GO",
              "recorded_experiments": 1,
              "items": [{
                  "library_item_id": "a" * 64, "kind": "UCIE_EXPERIENCE",
                  "provenance": "LOCAL_P8_HASH_CHAIN_NOT_THIRD_PARTY_ATTESTATION",
                  "real_library_benefit_verified": False,
                  "production_adopted": False, "independent_qa": False,
                  "decision": "REJECT_OR_REVISE_SYNTHETIC_CANDIDATE",
                  "exact_results_equivalent": False,
              }]}
        w05 = {"status": "UCIE_FIRST_PARTY_W05_EXPERIENCE_READ_ONLY",
               "recorded_count": 1, "returned_count": 1,
               "items": [{
                   "experience_id": "b" * 64, "candidate_id": "c" * 64,
                   "source_id": "repo:python/cpython",
                   "public_url": "https://github.com/python/cpython/pull/123",
                   "recipe_id": "TAGGED_TEST_CASE_LOOKUP_V1",
                   "decision": "RETEST_FIRST_PARTY_RECIPE",
                   "equivalent": True, "baseline_operations": 100,
                   "candidate_operations": 20,
                   "first_party_synthetic_only": True,
                   "upstream_capability_verified": False,
                   "approved_or_exportable": False,
               }]}
        view = product._revision_review_queue(p8=p8, w05=w05, limit=2)
        self.assertEqual(view, product._revision_review_queue(
            p8=p8, w05=w05, limit=2))
        self.assertEqual(view["candidate_count_in_loaded_window"], 2)
        self.assertEqual(view["items"][0]["review_state"],
                         "HOLD_FOR_MANUAL_REVIEW_NOT_APPLIED")
        self.assertEqual(view["items"][1]["review_state"],
                         "MORE_UCIE_TESTING_REQUIRED_NOT_APPLIED")
        self.assertEqual(view["items"][1]["public_candidate_identity_only"][
            "source_id"], "repo:python/cpython")
        self.assertTrue(all(not item["export_allowed"] and
                            not item["library_revision_written"]
                            for item in view["items"]))
        bounded = product._revision_review_queue(p8=p8, w05=w05, limit=1)
        self.assertEqual(bounded["returned_count"], 1)
        self.assertEqual(bounded["omitted_from_loaded_window"], 1)
        for field, bad in (
            ("production_adopted", True),
            ("independent_qa", True),
            ("real_library_benefit_verified", True),
            ("provenance", "PRIVATE_PROJECT_TELEMETRY"),
        ):
            wrong = {**p8, "items": [{**p8["items"][0], field: bad}]}
            with self.subTest(field=field):
                with self.assertRaises(product.ProductIntegrationError):
                    product._revision_review_queue(p8=wrong, w05=w05, limit=2)
        for field, bad in (
            ("approved_or_exportable", True),
            ("upstream_capability_verified", True),
            ("first_party_synthetic_only", False),
            ("candidate_operations", 150),
        ):
            wrong = {**w05, "items": [{**w05["items"][0], field: bad}]}
            with self.subTest(field=field):
                with self.assertRaises(product.ProductIntegrationError):
                    product._revision_review_queue(p8=p8, w05=wrong, limit=2)

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
            "product_v1", "--ucie-root", str(self.root),
            "--select-item", "a" * 64, "--consumer-reference"]):
            with patch("builtins.print") as printed:
                self.assertEqual(product.main(), 2)
        no_pack = json.loads(printed.call_args.args[0])
        self.assertEqual(no_pack["status"], "P9_PRODUCT_FAIL_CLOSED")
        with patch("sys.argv", [
            "product_v1", "--ucie-root", str(self.root),
            "--select-item", "a" * 64]):
            with patch("builtins.print") as printed:
                self.assertEqual(product.main(), 0)
        chosen = json.loads(printed.call_args.args[0])
        self.assertEqual(chosen["reuse_eligibility"]["selected_item"]
                         ["selection_status"],
                         "NOT_IN_CURRENT_BOUNDED_QUERY_WINDOW_NO_GO")
        self.assertFalse(chosen["reuse_eligibility"]
                         ["selected_item"]["new_generic_package_export_allowed"])
        with patch("sys.argv", [
            "product_v1", "--ucie-root", str(self.root),
            "--select-item", "../../unsafe"]):
            with patch("builtins.print") as printed:
                self.assertEqual(product.main(), 2)
        invalid = json.loads(printed.call_args.args[0])
        self.assertEqual(invalid["status"], "P9_PRODUCT_FAIL_CLOSED")
        self.assertFalse((self.root / "runtime" / "exports").exists())
        with patch("sys.argv", [
            "product_v1", "--ucie-root", str(self.root),
            "--export-draft", "--consumer-reference"]):
            with patch("builtins.print") as printed:
                self.assertEqual(product.main(), 2)
        self.assertEqual(json.loads(printed.call_args.args[0])["status"],
                         "P9_PRODUCT_FAIL_CLOSED")
        self.assertFalse((self.root / "runtime" / "exports").exists())
        with patch("sys.argv", [
            "product_v1", "--ucie-root", str(self.root), "--export-draft"]):
            with patch("builtins.print") as printed:
                self.assertEqual(product.main(), 0)
        obj = json.loads(printed.call_args.args[0])
        self.assertEqual(obj["status"], "UCIE_ONLY_DRAFT_WRITTEN_NOT_RELEASED")
        self.assertTrue((self.root / obj["relative_path"]).is_file())
        with patch("sys.argv", [
            "product_v1", "--ucie-root", str(self.root), "--verify-draft"]):
            with patch("builtins.print") as printed:
                self.assertEqual(product.main(), 0)
        verified = json.loads(printed.call_args.args[0])
        self.assertEqual(verified["status"],
                         "UCIE_LOCAL_DRAFT_BYTES_VERIFIED_NOT_RELEASED")
        self.assertEqual(verified["sha256"], obj["sha256"])
        self.assertFalse(verified["independent_signature_verified"])
        with patch("sys.argv", [
            "product_v1", "--ucie-root", str(self.root),
            "--verify-draft", "--demo"]):
            with patch("builtins.print") as printed:
                self.assertEqual(product.main(), 2)
        rejected = json.loads(printed.call_args.args[0])
        self.assertEqual(rejected["status"], "P9_PRODUCT_FAIL_CLOSED")
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
