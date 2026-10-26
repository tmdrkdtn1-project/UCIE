"""Offline acceptance for the single-command approved public Serial 4 scanner.

All remote bytes and signature-verification results are mock inputs. No
network, private code, owner key, fresh signature, or external code execution.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import ucie_public_pinned_serial4_scan as scanner
from ucie_public.policy import PolicyError


def _signed():
    return {
        "result": "MIXED_OWNER_PUBLIC_MANUAL_PACK_VERIFIED",
        "owner_signature": "VALID",
        "scope": "PUBLIC_ONLY_MANUAL_STATIC_SCAN",
        "serial": 4,
        "rule_count": 4,
        "rule_ids": list(scanner.RULE_ORDER),
        "auto_apply": False,
    }


def _scan(receipt, findings):
    return {
        "schema": "UCIE_MIXED_PUBLIC_MANUAL_STATIC_SCAN_V2",
        "owner_signature": "VALID",
        "pack_serial": 4,
        "source_sha256": receipt["source_sha256"],
        "source_executed": False,
        "source_files_read": 0,
        "persistent_writes": 0,
        "auto_fix_applied": False,
        "auto_apply": False,
        "finding_count": len(findings),
        "findings": findings,
    }


class PublicPinnedSerial4Tests(unittest.TestCase):
    def test_allowed_public_test_file_manual_candidate_not_bug(self):
        raw = b"Get-Command Get-FuzzyDuplicat -UseFuzzyMatching\n"
        blob = scanner._git_blob(raw)
        source_hash = hashlib.sha256(raw).hexdigest()
        seen = []

        def ps_parse(path, source, root):
            seen.append((path, source, root))
            return {"source_sha256": source_hash}

        candidate = {"rule_id": "PS_FUZZY_GET_COMMAND_DUPLICATES",
                     "line": 1, "column": 1}

        with (
            patch.object(scanner, "verify_mixed_owner_release",
                         return_value=_signed()),
            patch.object(scanner, "scan_mixed_owner_receipt",
                         side_effect=lambda p, t, receipt, **kw:
                         _scan(receipt, [candidate])),
        ):
            result = scanner.scan_pinned_source(
                repo="PowerShell/PowerShell",
                commit="a" * 40,
                path="test/powershell/Get-Command.Tests.ps1",
                blob=blob,
                pack=Path("owner-signed-pack.zip"),
                trust=Path("public-key.pem"),
                fetch_source=lambda url: raw,
                ps_parse=ps_parse,
            )

        self.assertEqual(result["status"], "MANUAL_REVIEW_CANDIDATES")
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["pending_manual_review_count"], 1)
        self.assertEqual(result["pinned_upstream_test_evidence_count"], 0)
        self.assertIs(result["candidates"][0]["manual_review_required"], True)
        self.assertIs(result["candidates"][0]["runtime_bug_confirmed"], False)
        self.assertEqual(result["source"]["role"], "TEST_PATH")
        self.assertEqual(result["source"]["git_blob_sha1"], blob)
        self.assertFalse(result["source_executed"])
        self.assertFalse(result["auto_fix"])
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][1], raw.decode("utf-8"))

    def test_exact_upstream_regression_evidence_is_not_new_bug(self):
        identity = (
            "PowerShell/PowerShell",
            "dad69345f3fae3d0530f87ec73c8441649760483",
            "test/powershell/Modules/Microsoft.PowerShell.Utility/Get-Command.Tests.ps1",
            "766848c7a721c8724b39643d0e17ba5daa11c4c3",
        )
        finding = {"rule_id": "PS_FUZZY_GET_COMMAND_DUPLICATES",
                   "line": 49, "column": 25}
        triaged, pending = scanner._triage_pinned_findings(
            *identity, [finding])
        self.assertEqual(pending, 0)
        self.assertEqual(
            triaged[0]["triage_status"],
            "PINNED_UPSTREAM_REGRESSION_TEST_EVIDENCE")
        self.assertIs(triaged[0]["manual_review_required"], False)
        self.assertIs(triaged[0]["runtime_bug_confirmed"], False)

        # A moved line, changed Git blob, or unrelated rule must remain
        # pending for manual review: no generic test-folder exemptions.
        changes = [
            (*identity[:3], "a" * 40, finding),
            (*identity, {**finding, "line": 50}),
            (*identity, {**finding, "rule_id": "PS_RESOLVE_PATH_DOT_PREFIX"}),
        ]
        for repo, commit, path, blob, other in changes:
            with self.subTest(blob=blob, finding=other):
                found, pending = scanner._triage_pinned_findings(
                    repo, commit, path, blob, [other])
                self.assertEqual(pending, 1)
                self.assertEqual(found[0]["triage_status"],
                                 "UNVERIFIED_MANUAL_REVIEW_REQUIRED")
                self.assertIs(found[0]["manual_review_required"], True)

    def test_pinned_upstream_test_pipeline_separates_raw_vs_pending(self):
        raw = b"Get-Command Get-FuzzyDuplicat -UseFuzzyMatching\n"
        blob = "766848c7a721c8724b39643d0e17ba5daa11c4c3"
        source_hash = hashlib.sha256(raw).hexdigest()
        finding = {"rule_id": "PS_FUZZY_GET_COMMAND_DUPLICATES",
                   "line": 49, "column": 25}
        # This test isolates classification; Git-blob mismatches are tested
        # separately with the genuine _git_blob function.
        with (
            patch.object(scanner, "_git_blob", return_value=blob),
            patch.object(scanner, "verify_mixed_owner_release",
                         return_value=_signed()),
            patch.object(scanner, "scan_mixed_owner_receipt",
                         side_effect=lambda p, t, receipt, **kw:
                         _scan(receipt, [finding])),
        ):
            result = scanner.scan_pinned_source(
                repo="PowerShell/PowerShell",
                commit="dad69345f3fae3d0530f87ec73c8441649760483",
                path="test/powershell/Modules/Microsoft.PowerShell.Utility/Get-Command.Tests.ps1",
                blob=blob,
                pack=Path("pack.zip"), trust=Path("public.pem"),
                fetch_source=lambda url: raw,
                ps_parse=lambda p, text, root: {
                    "source_sha256": source_hash},
            )
        self.assertEqual(result["schema"],
                         "UCIE_SERIAL4_PINNED_PUBLIC_SOURCE_SCAN_V2")
        self.assertEqual(result["status"], "PINNED_UPSTREAM_TEST_EVIDENCE")
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["pending_manual_review_count"], 0)
        self.assertEqual(result["pinned_upstream_test_evidence_count"], 1)
        self.assertEqual(result["confirmed_new_bug_count"], 0)
        self.assertIs(result["candidates"][0]["runtime_bug_confirmed"], False)

    def test_real_first_party_python_parser_no_thread_boundary(self):
        raw = (
            b"import os\n"
            b"def collect(path):\n"
            b"    with os.scandir(path) as entries:\n"
            b"        return list(entries)\n"
        )
        with (
            patch.object(scanner, "verify_mixed_owner_release",
                         return_value=_signed()),
            patch.object(scanner, "scan_mixed_owner_receipt",
                         side_effect=lambda p, t, receipt, **kw:
                         _scan(receipt, [] if receipt["finding_count"] == 0
                               else [{"rule_id": "UNEXPECTED",
                                      "line": 1, "column": 0}])),
        ):
            result = scanner.scan_pinned_source(
                repo="python/cpython", commit="b" * 40,
                path="Lib/glob.py", blob=scanner._git_blob(raw),
                pack=Path("owner-signed-pack.zip"),
                trust=Path("public-key.pem"),
                fetch_source=lambda url: raw,
            )
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["status"], "NO_SIGNED_RULE_MATCH")

    def test_reject_unapproved_repository_and_noncanonical_paths_before_fetch(self):
        values = (
            ("owner/private-repository", "test.py"),
            ("python/cpython", "../secret.py"),
            ("python/cpython", "a//b.py"),
            ("python/cpython", "sub\folder.py"),
            ("python/cpython", "tests/file.txt"),
            ("python/cpython", "tests/../file.py"),
        )
        for repo, path in values:
            with self.subTest(repo=repo, path=path):
                with self.assertRaises(PolicyError):
                    scanner._identity(repo, "a" * 40, path, "b" * 40)

    def test_git_blob_mismatch_and_invalid_signature_block(self):
        raw = b"import os\n"
        args = dict(
            repo="python/cpython", commit="a" * 40,
            path="Lib/os.py", blob="b" * 40,
            pack=Path("pack.zip"), trust=Path("public.pem"))
        with patch.object(scanner, "verify_mixed_owner_release",
                          return_value=_signed()):
            with self.assertRaises(PolicyError):
                scanner.scan_pinned_source(
                    **args, fetch_source=lambda url: raw)
        calls = []
        bad = {**_signed(), "owner_signature": "INVALID"}
        with patch.object(scanner, "verify_mixed_owner_release",
                          return_value=bad):
            with self.assertRaises(PolicyError):
                scanner.scan_pinned_source(
                    **args, fetch_source=lambda url: calls.append(url))
        self.assertEqual(calls, [])

    def test_no_redirects_or_missing_blob_identity(self):
        handler = scanner._NoRedirect()
        self.assertIsNone(handler.redirect_request(
            None, None, 302, "found", {}, "https://example.invalid/"))
        with self.assertRaises(PolicyError):
            scanner._identity(
                "python/cpython", "a" * 39 + "!", "Lib/os.py", "b" * 40)


if __name__ == "__main__":
    unittest.main()
