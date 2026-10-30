"""UCIE first-party portable engine: isolated child QA and fake approval denials."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

from ucie_miner import product_v1 as product
from ucie_miner import portable_exact as portable
from ucie_miner.portable_consumer_qa import check_portable_engine_qa


class PortableIndependentConsumerQATests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)

    def _public_handoff(self):
        kinds = ("DEVELOPMENT_ENGINE", "REUSABLE_SKILL", "LEARNING_LOGIC")
        rows = []
        for n, kind in enumerate(kinds, 1):
            rows.append({
                "source_id": "repo:python/cpython", "domain": "Python",
                "kind": kind, "purpose_code": "SKILL_TEST_AUTOMATION",
                "public_url": f"https://github.com/python/cpython/pull/{n}",
                "library_item_id": f"{n:064x}",
                "evidence_sha256": f"{n+100:064x}",
                "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
                "signature_status": "NOT_ATTESTED_BY_THIS_SEARCH",
                "human_approved": False, "export_allowed": False,
            })
        rows.append({
            **rows[0], "source_id": "repo:git/git",
            "public_url": "https://github.com/git/git/commit/" + "f" * 40,
            "library_item_id": "d" * 64,
        })
        return product._portable_public_ledger_handoff({
            "status": "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
            "items": rows, "returned_count": len(rows),
            "omitted_count": 2,
        }, limit=20)

    def test_no_local_ledger_independent_consumer_is_synthetic_only(self):
        preexisting = sorted(str(f.relative_to(self.root)) for f in self.root.rglob("*"))
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("offline QA must not fetch")):
            result = check_portable_engine_qa(self.root)
        self.assertEqual(result["status"],
                         "FIRST_PARTY_ISOLATED_CONSUMER_QA_PASS_NOT_RELEASED")
        self.assertTrue(result["independent_python_process_executed"])
        self.assertTrue(result["standalone_zip_without_ucie_install_executed"])
        self.assertEqual(result["standalone_zip_exact_parity_cases"], 3)
        self.assertTrue(result["portable_source_exact_byte_match"])
        self.assertEqual(result["bounded_query_cases_verified"], 3)
        self.assertEqual(result["isolated_single_query_strategy"], "LINEAR_EXACT_SCAN")
        self.assertEqual(result["isolated_batch_strategy"], "COMPOSITE_INDEX")
        self.assertEqual(result["source_window"],
                         "UCIE_AUTHOR_SYNTHETIC_ONLY_NO_LIVE_SOURCE_QA")
        self.assertEqual(result["public_candidate_records_tested"], 0)
        self.assertTrue(result["zero_match_control_verified"])
        self.assertFalse(result["independent_external_qa_attested"])
        self.assertFalse(result["owner_release_approved"])
        self.assertFalse(result["package_released"])
        self.assertFalse(result["v1_accepted"])
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(sorted(str(f.relative_to(self.root))
                                for f in self.root.rglob("*")), preexisting)

    def test_linked_w04_unverified_skill_engine_learning_metadata_in_child(self):
        handoff = self._public_handoff()
        self.assertEqual(handoff["portable_candidate_items"], 3)
        self.assertEqual(handoff["unsupported_reference_count"], 1)
        self.assertTrue(handoff["in_process_exact_search_equivalent"])
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("public code must not fetch")):
            report = check_portable_engine_qa(self.root, public_handoff=handoff)
        self.assertEqual(report["public_candidate_records_tested"], 3)
        self.assertTrue(report["public_window_truncated"])
        self.assertEqual(report["public_reference_unsupported_in_window"], 1)
        self.assertEqual(report["source_window"],
                         "W04_LINKED_PUBLIC_PR_METADATA_STILL_UNVERIFIED")
        self.assertTrue(report["exact_result_parity_verified"])
        self.assertEqual(report["verified_upstream_applicable_versions"], 0)
        self.assertEqual(report["per_revision_redistribution_rights_approved"], 0)
        self.assertFalse(report["full_public_universe_covered"])
        self.assertFalse(report["owner_release_approved"])
        self.assertFalse(report["v1_accepted"])

    def test_modified_zip_source_rights_or_approval_cannot_pass(self):
        handoff = self._public_handoff()
        canonical, _ = product.build_draft_package_bytes()
        for forged in (canonical[:-1] + b"x", b"not-a-zip", b"", canonical + b"x"):
            with self.subTest(length=len(forged)):
                with self.assertRaises(product.ProductIntegrationError):
                    check_portable_engine_qa(
                        self.root, public_handoff=handoff, draft_bytes=forged)
        for field in ("human_approved", "export_allowed"):
            forged = deepcopy(handoff)
            forged["consumer_payload"]["items"][0][field] = True
            with self.subTest(field=field):
                with self.assertRaises(product.ProductIntegrationError):
                    check_portable_engine_qa(self.root, public_handoff=forged)
        for change in (
            {"approved_or_exportable_items": 1},
            {"status": "APPROVED_FOR_DISTRIBUTION"},
            {"in_process_exact_search_equivalent": False},
            {"network_requests": 1},
        ):
            forged = {**handoff, **change}
            with self.subTest(change=change):
                with self.assertRaises(product.ProductIntegrationError):
                    check_portable_engine_qa(self.root, public_handoff=forged)
        forged = deepcopy(handoff)
        forged["consumer_payload"]["items"][0]["public_url"] = (
            "https://github.com/private/secret/pull/42")
        with self.assertRaises(product.ProductIntegrationError):
            check_portable_engine_qa(self.root, public_handoff=forged)

    def test_isolated_runner_forged_success_or_error_fails_closed(self):
        handoff = self._public_handoff()
        with patch("ucie_miner.portable_consumer_qa.subprocess.run",
                   return_value=Mock(
                       returncode=0, stdout=b'{"approved":true}', stderr=b"")):
            with self.assertRaises(product.ProductIntegrationError):
                check_portable_engine_qa(self.root, public_handoff=handoff)
        with patch("ucie_miner.portable_consumer_qa.subprocess.run",
                   return_value=Mock(
                       returncode=1, stdout=b"", stderr=b"some uncaught error")):
            with self.assertRaises(product.ProductIntegrationError):
                check_portable_engine_qa(self.root, public_handoff=handoff)

    def test_zip_is_directly_executable_without_ucie_install_or_network(self):
        from hashlib import sha256
        payload, manifest = product.build_draft_package_bytes()
        dest = Path(self.folder.name) / "independent_consumer"
        dest.mkdir()
        package = dest / "ucie_exact_DRAFT.zip"
        package.write_bytes(payload)
        root_files = sorted(self.root.rglob("*"))
        rows = product._demo_input()
        key = ["repo:python/cpython", "Python",
               "PUBLIC_TECHNICAL_EVIDENCE", "API_CONTRACT"]
        def invoke(raw: bytes, *args: str):
            return subprocess.run(
                [sys.executable, "-I", "-B", str(package), *args],
                input=raw, capture_output=True, cwd=dest,
                timeout=30, check=False)
        request = {"items": rows, "queries": [key], "limit": 20}
        original = json.dumps(request, sort_keys=True).encode("ascii")
        good = invoke(original)
        self.assertEqual(good.returncode, 0, good.stderr[-500:])
        self.assertFalse(good.stderr)
        record = json.loads(good.stdout)
        self.assertEqual(record["schema"],
                         "UCIE_STANDALONE_DRAFT_PUBLIC_METADATA_CLI_V1")
        self.assertEqual(record["status"],
                         "UNVERIFIED_PUBLIC_METADATA_QUERY_DRAFT_NOT_RELEASED")
        self.assertEqual(record["engine_version"], "1.1.0")
        self.assertEqual(record["result"],
                         portable.search_public_metadata(
                             rows, queries=(tuple(key),), limit=20))
        self.assertFalse(record["owner_release_approved"])
        self.assertFalse(record["package_released"])
        self.assertEqual(record["new_public_candidate_approvals"], 0)
        self.assertFalse(record["third_party_code_executed"])
        self.assertEqual(sha256(package.read_bytes()).hexdigest(),
                         sha256(payload).hexdigest())
        self.assertEqual(manifest["version"], "1.3.0")
        self.assertEqual(sorted(self.root.rglob("*")), root_files)

        invalid = (
            b"", b"not-json", b" " * 33000,
            b'{"items":[],"queries":[],"limit":2}',
            b'{"items":[],"queries":[["repo:python/cpython","Python",'
            b'"PUBLIC_TECHNICAL_EVIDENCE","API_CONTRACT"]],"limit":true}',
            original[:-1] + b',"owner_release_approved":true}',
            original.replace(b'"limit": 20', b'"limit": 20, "limit": 20'),
            original.replace(b'https://github.com/python/cpython',
                             b'https://github.com/private/secret'),
            original.replace(b'"human_approved": false',
                             b'"human_approved": true'),
            original.replace(b'"export_allowed": false',
                             b'"export_allowed": true'),
            b'{"items":[],"queries":[],"limit":NaN}',
        )
        for raw in invalid:
            with self.subTest(raw=raw[:100]):
                denied = invoke(raw)
                self.assertEqual(denied.returncode, 2, denied.stderr[-500:])
                self.assertFalse(denied.stderr)
                rejected = json.loads(denied.stdout)
                self.assertEqual(rejected["status"], "STANDALONE_DRAFT_FAIL_CLOSED")
                self.assertFalse(rejected["owner_release_approved"])
                self.assertFalse(rejected["package_released"])
        # Response size expands with repeated exact queries even with a
        # bounded <=32KiB input. Hard fail instead of emitting oversized data.
        base_row = product._demo_input()[0]
        many_rows = [{
            **base_row,
            "library_item_id": f"{i+1:064x}",
            "public_url": f"https://github.com/python/cpython/pull/{i+1}",
            "evidence_sha256": f"{i+200:064x}",
        } for i in range(20)]
        amplified = json.dumps({
            "items": many_rows, "queries": [key] * 32, "limit": 20,
        }, sort_keys=True).encode("ascii")
        self.assertLess(len(amplified), 32768)
        overflow = invoke(amplified)
        self.assertEqual(overflow.returncode, 2, overflow.stderr[-500:])
        self.assertFalse(overflow.stderr)
        self.assertEqual(json.loads(overflow.stdout)["status"],
                         "STANDALONE_DRAFT_FAIL_CLOSED")
        self.assertLess(len(overflow.stdout), 1024)

        denied = invoke(original, "--export", "external")
        self.assertEqual(denied.returncode, 2)
        self.assertEqual(json.loads(denied.stdout)["status"],
                         "STANDALONE_DRAFT_FAIL_CLOSED")
        self.assertEqual(sorted(self.root.rglob("*")), root_files)

    def test_real_product_cli_opt_in_only_and_read_only(self):
        with patch("sys.argv", [
            "product_v1", "--ucie-root", str(self.root), "--qa-portable"]):
            with patch("builtins.print") as printed:
                self.assertEqual(product.main(), 0)
        actual = json.loads(printed.call_args.args[0])
        self.assertTrue(actual["independent_python_process_executed"])
        self.assertFalse(actual["owner_release_approved"])
        for flag in ("--export-draft", "--verify-draft", "--consumer-reference"):
            with self.subTest(flag=flag):
                with patch("sys.argv", [
                    "product_v1", "--ucie-root", str(self.root),
                    "--qa-portable", flag]):
                    with patch("builtins.print") as printed:
                        self.assertEqual(product.main(), 2)
                self.assertEqual(json.loads(
                    printed.call_args.args[0])["status"], "P9_PRODUCT_FAIL_CLOSED")
        self.assertFalse((self.root / "runtime" / "exports").exists())


if __name__ == "__main__":
    unittest.main()
