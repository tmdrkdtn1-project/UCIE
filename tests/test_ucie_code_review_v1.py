"""End-to-end UCIE-owned synthetic code review, Python and PowerShell.

No project source files are loaded: tests use only synthetic input strings.
PowerShell tests invoke the original UCIE-authored inert AST scanner.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner.code_review_v1 import (
    CodeReviewError, review_code, _linked_library_for_finding, SCHEMA, MAX_BYTES,
)
from ucie_miner.library_search import search_existing_public_library
from ucie_miner.public_candidate_staging import stage_public_candidates, DB_NAME
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, optional_hourly_review_learning)
from test_ucie_stage11_hourly_stage import fixture_batch

ROOT = Path(__file__).resolve().parents[1]
SCANDIR = """import os
from concurrent.futures import ThreadPoolExecutor
def review(folder, callback):
    iterator = os.scandir(folder)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return pool.submit(callback, iterator).result()
"""
PS_DOT = "Resolve-Path -Relative '.directory'\n"
PS_SAFE = "Write-Output 'safe synthetic example'\n"


class UnifiedCodeReviewV1Tests(unittest.TestCase):
    def test_python_real_existing_scanners_and_safe_empty_control(self):
        result = review_code(SCANDIR, language="python", root=ROOT)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["source_sha256"],
                         sha256(SCANDIR.encode()).hexdigest())
        self.assertEqual(result["finding_count"], 1)
        item = result["findings"][0]
        self.assertEqual(item["rule_id"],
                         "PY_SCANDIR_SHARED_ITERATOR_RACE")
        self.assertGreater(item["line"], 0)
        self.assertIn("scandir", item["safe_fix_guidance"])
        self.assertEqual(item["public_evidence"],
                         "https://github.com/python/cpython/pull/153462")
        self.assertIsNone(item["version_evidence"])
        self.assertEqual(item["authorization"],
                         "UNVERIFIED_STATIC_CANDIDATE_ONLY")
        self.assertFalse(item["source_runtime_bug_confirmed"])
        self.assertFalse(result["source_executed"])
        self.assertFalse(result["auto_applied"])
        self.assertFalse(result["production_approved"])
        self.assertEqual(result["database_writes"], 0)
        self.assertEqual(result["public_library_exact_pr_lookups"], 1)
        self.assertIn(result["findings"][0]["public_library"]["status"], (
            "PUBLIC_SOURCE_LEDGER_INCOMPLETE_NO_GO",
            "NO_EXACT_PUBLIC_PR_IN_CURRENT_LINKED_LEDGER",
            "EXACT_PUBLIC_PR_SOURCE_LINKED_UNVERIFIED",
        ))
        self.assertFalse(result["findings"][0]["public_library"]["approved_or_exportable"])
        empty = review_code("pass\n", language="python", root=ROOT)
        self.assertEqual(empty["status"], "NO_KNOWN_PATTERN_NOT_SAFETY_PASS")
        self.assertFalse(empty["full_code_safety_verified"])
        self.assertEqual(empty["public_library_exact_pr_lookups"], 0)

    @unittest.skipUnless(
        shutil.which("pwsh") or shutil.which("pwsh.exe")
        or shutil.which("powershell.exe"),
        "no actual PowerShell executable on CI")
    def test_powershell_real_existing_ast_scanner_and_version_receipt(self):
        source = "# UCIE_SECRET_SHOULD_NOT_LEAK\n" + PS_DOT
        result = review_code(source, language="powershell", root=ROOT)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["language"], "powershell")
        self.assertEqual(result["finding_count"], 1)
        self.assertEqual(result["source_sha256"],
                         sha256(source.encode()).hexdigest())
        finding = result["findings"][0]
        self.assertEqual(finding["rule_id"], "PS_RESOLVE_PATH_DOT_PREFIX")
        self.assertEqual(finding["line"], 2)
        self.assertGreaterEqual(finding["column"], 1)
        self.assertEqual(finding["public_evidence"],
                         "https://github.com/PowerShell/PowerShell/pull/28087")
        self.assertEqual(finding["authorization"],
                         "UNVERIFIED_STATIC_CANDIDATE_ONLY")
        self.assertFalse(finding["source_runtime_bug_confirmed"])
        version = finding["version_evidence"]
        self.assertEqual(version["tested_release"], "PowerShell 7.6.6")
        self.assertEqual(version["tested_platforms"],
                         ["windows-x64", "linux-x64"])
        self.assertFalse(version["same_bug_confirmed_in_supplied_source"])
        self.assertFalse(version["production_approved"])
        self.assertNotIn("UCIE_SECRET_SHOULD_NOT_LEAK",
                         json.dumps(result))
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["database_writes"], 0)
        safe = review_code(PS_SAFE, language="powershell", root=ROOT)
        self.assertEqual(safe["finding_count"], 0)
        self.assertEqual(safe["status"], "NO_KNOWN_PATTERN_NOT_SAFETY_PASS")
        with self.assertRaises(CodeReviewError):
            review_code("if (", language="powershell", root=ROOT)

    @unittest.skipUnless(
        shutil.which("pwsh") or shutil.which("powershell.exe"),
        "no PowerShell runtime on CI")
    def test_strict_utf8_unicode_crlf_original_bytes_on_actual_powershell_hosts(self):
        # UCIE-authored synthetic sample: harmless Korean/emoji comments and
        # CRLF must survive BOTH PowerShell 7 and Windows PowerShell 5.1.
        source = ("# UCIE 합성 실험: 한글 주석 🐼\\r\\n"
                  "Resolve-Path -Relative '.directory'\\r\\n"
                  "# 유니코드 테스트 끝\\r\\n").replace("\\r\\n", "\r\n")
        encoded = source.encode("utf-8")
        expected_sha = sha256(encoded).hexdigest()
        wrapper = ROOT / "scripts" / "ucie_powershell_review_stdin.ps1"
        shells = []
        for name in ("pwsh", "powershell.exe"):
            executable = shutil.which(name)
            if executable and executable not in shells:
                shells.append(executable)
        self.assertGreater(len(shells), 0)
        for shell in shells:
            with self.subTest(shell=Path(shell).name):
                raw = subprocess.run(
                    [shell, "-NoProfile", "-NonInteractive",
                     "-File", str(wrapper)],
                    input=encoded, capture_output=True,
                    timeout=30, cwd=ROOT, check=False)
                self.assertEqual(raw.returncode, 0,
                                 raw.stderr[-650:].decode("utf-8", "replace"))
                receipt = json.loads(raw.stdout.decode("utf-8-sig"))
                self.assertEqual(receipt["source_sha256"], expected_sha)
                self.assertEqual(len(receipt["findings"]), 1)
                self.assertEqual(receipt["findings"][0]["line"], 2)
                self.assertEqual(receipt["findings"][0]["pattern_code"],
                                 "PS_RESOLVE_PATH_DOT_PREFIX")
                self.assertNotIn("한글", raw.stdout.decode("utf-8", "replace"))
                self.assertNotIn("🐼", raw.stdout.decode("utf-8", "replace"))
                for invalid in (b"\xffResolve-Path", b"x" * (MAX_BYTES + 1)):
                    failed = subprocess.run(
                        [shell, "-NoProfile", "-NonInteractive",
                         "-File", str(wrapper)],
                        input=invalid, capture_output=True,
                        timeout=30, cwd=ROOT, check=False)
                    self.assertEqual(failed.returncode, 2)
                    self.assertNotIn(b"Resolve-Path", failed.stdout)
                    self.assertNotIn(b"Resolve-Path", failed.stderr)
        # The actual user-facing CLI must preserve these bytes too.
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        cmd = [sys.executable, "-B", "-m", "ucie_miner.code_review_v1",
               "--ucie-root", str(ROOT), "--language", "powershell"]
        completed = subprocess.run(cmd, input=encoded, capture_output=True,
                                   timeout=35, cwd=ROOT, env=env, check=False)
        self.assertEqual(completed.returncode, 0,
                         completed.stderr[-650:].decode("utf-8", "replace"))
        report = json.loads(completed.stdout.decode("utf-8-sig"))
        self.assertEqual(report["source_sha256"], expected_sha)
        self.assertEqual(report["findings"][0]["line"], 2)
        self.assertEqual(report["findings"][0]["rule_id"],
                         "PS_RESOLVE_PATH_DOT_PREFIX")
        self.assertFalse(report["source_executed"])
        self.assertFalse(report["auto_applied"])
        self.assertFalse(report["production_approved"])
        self.assertEqual(report["database_writes"], 0)

    @unittest.skipUnless(shutil.which("pwsh") or shutil.which("powershell.exe"),
                         "PowerShell runtime unavailable")
    def test_duplicate_public_pr_findings_do_not_repeat_library_read(self):
        source = ("Resolve-Path -Relative '.directory'\n"
                  "Resolve-Path -Relative '..directory'\n")
        with patch("ucie_miner.code_review_v1._linked_library_for_finding",
                   return_value={
                       "status": "PUBLIC_SOURCE_LEDGER_INCOMPLETE_NO_GO",
                       "approved_or_exportable": False, "items": [],
                   }) as lookup:
            report = review_code(source, language="powershell", root=ROOT)
        self.assertEqual(report["finding_count"], 2)
        self.assertEqual(report["public_library_exact_pr_lookups"], 1)
        lookup.assert_called_once()
        self.assertTrue(all(not x["public_library"]["approved_or_exportable"]
                            for x in report["findings"]))

    def test_real_source_linked_public_ledger_is_read_once_and_never_mutated(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work) / "UCIE"
            runtime = root / "runtime"
            runtime.mkdir(parents=True)
            batch = fixture_batch(
                root=root, sources=(
                    "python/cpython", "PowerShell/PowerShell", "git/git",
                    "modelcontextprotocol/python-sdk",
                    "actions/runner-images"),
                max_enrich=1, include_git_commits=True,
                include_docs=False, include_advisories=False,
                backfill_pages=1)
            stage_public_candidates(batch, root=root, allow_disk_write=True)
            (runtime / OPT_IN_FILENAME).write_text(OPT_IN_TOKEN,
                                                  encoding="ascii")
            self.assertEqual(optional_hourly_review_learning(root)[
                "new_review_proposals"], 2)
            from_ledger = search_existing_public_library(
                root, query="", limit=20, group_revisions=True)
            selected = [row for row in from_ledger["items"]
                        if "/pull/" in row["public_url"]]
            self.assertGreater(len(selected), 0)
            row = selected[0]
            originals = [
                runtime / DB_NAME, runtime / "stage12_unverified_review.sqlite3"
            ]
            before = [p.read_bytes() for p in originals]
            with patch("urllib.request.urlopen",
                       side_effect=AssertionError("review must not fetch")):
                result = _linked_library_for_finding(root, row["public_url"])
            self.assertEqual([p.read_bytes() for p in originals], before)
            self.assertEqual(result["status"],
                             "EXACT_PUBLIC_PR_SOURCE_LINKED_UNVERIFIED")
            self.assertTrue(result["source_linkage_checked"])
            self.assertTrue(any(
                entry["library_item_id"] == row["library_item_id"]
                and entry["evidence_sha256"] == row["evidence_sha256"]
                and not entry["rule_fix_independently_verified"]
                and not entry["rights_for_export_verified"]
                for entry in result["items"]))
            self.assertFalse(result["approved_or_exportable"])
            # No cross-PR evidence inheriting: a different *allowed* PR is
            # not automatically linked to the source-backed library rows.
            different = ("https://github.com/python/cpython/pull/153462"
                         if "153462" not in row["public_url"] else
                         "https://github.com/python/cpython/pull/999999")
            unlinked = _linked_library_for_finding(root, different)
            self.assertEqual(unlinked["matched_public_evidence_count"], 0)
            self.assertEqual(unlinked["items"], [])
            self.assertEqual([p.read_bytes() for p in originals], before)

    def test_library_forged_evidence_and_empty_local_ledger_fail_closed(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work) / "UCIE"
            (root / "runtime").mkdir(parents=True)
            url = "https://github.com/python/cpython/pull/153462"
            absent = _linked_library_for_finding(root, url)
            self.assertEqual(absent["status"],
                             "PUBLIC_SOURCE_LEDGER_INCOMPLETE_NO_GO")
            self.assertFalse(absent["source_linkage_checked"])
            self.assertFalse(absent["approved_or_exportable"])
            for bad in (url + "/files",
                        "https://github.com/unapproved/private/pull/10"):
                with self.subTest(url=bad):
                    with self.assertRaisesRegex(
                            CodeReviewError,
                            "UNAPPROVED_PUBLIC_EVIDENCE_REFERENCE"):
                        _linked_library_for_finding(root, bad)
            row = {
                "library_item_id": "a" * 64,
                "source_id": "repo:python/cpython",
                "public_url": url,
                "evidence_sha256": "b" * 64,
                "revision_hint": "c" * 40,
                "purpose_code": "API_CONTRACT",
                "kind": "PUBLIC_TECHNICAL_EVIDENCE",
                "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
                "signature_status": "NOT_ATTESTED_BY_THIS_SEARCH",
                "human_approved": False,
                "export_allowed": False,
            }
            base = {
                "status": "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
                "items": [row], "returned_count": 1,
                "total_matches": 1, "omitted_count": 0,
                "approved_or_exportable_items": 0,
                "operating_database_writes": 0, "network_requests": 0,
            }
            with patch("ucie_miner.code_review_v1.search_existing_public_library",
                       return_value=base) as search:
                output = _linked_library_for_finding(root, url)
            self.assertEqual(output["status"],
                             "EXACT_PUBLIC_PR_SOURCE_LINKED_UNVERIFIED")
            search.assert_called_once()
            self.assertFalse(output["items"][0]["rule_fix_independently_verified"])
            # A different *unverified but otherwise valid* PR from the same
            # allowed repository is skipped, not incorrectly inherited.
            other = {**base, "items": [{
                **row,
                "public_url": "https://github.com/python/cpython/pull/9999",
            }]}
            with patch("ucie_miner.code_review_v1.search_existing_public_library",
                       return_value=other):
                unrelated = _linked_library_for_finding(root, url)
            self.assertEqual(unrelated["status"],
                             "NO_EXACT_PUBLIC_PR_IN_CURRENT_LINKED_LEDGER")
            self.assertEqual(unrelated["items"], [])
            for modify in (
                {"source_id": "repo:PowerShell/PowerShell"},
                {"human_approved": True}, {"export_allowed": True},
                {"signature_status": "APPROVED"},
                {"evidence_sha256": "garbage"},
            ):
                with self.subTest(modify=modify):
                    corrupt = {**base, "items": [{**row, **modify}]}
                    with patch("ucie_miner.code_review_v1.search_existing_public_library",
                               return_value=corrupt):
                        with self.assertRaises(CodeReviewError):
                            _linked_library_for_finding(root, url)

    def test_bounded_input_and_no_shell_fail_closed(self):
        for source, language in (("", "python"),
                                 ("x" * (MAX_BYTES + 1), "python"),
                                 ("pass", "javascript"),
                                 ("pass", 1)):
            with self.subTest(language=language, length=len(source)):
                with self.assertRaises(CodeReviewError):
                    review_code(source, language=language, root=ROOT)
        with self.assertRaises(CodeReviewError):
            review_code("pass", language="python", root=Path("/tmp/private"))
        with patch("ucie_miner.code_review_v1.shutil.which", return_value=None):
            with self.assertRaisesRegex(CodeReviewError,
                                        "POWERSHELL_RUNTIME_UNAVAILABLE"):
                review_code(PS_DOT, language="powershell", root=ROOT)

    def test_actual_single_command_python_and_failclosed_error(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        cmd = [sys.executable, "-B", "-m", "ucie_miner.code_review_v1",
               "--ucie-root", str(ROOT), "--language", "python"]
        good = subprocess.run(cmd, input=SCANDIR, text=True,
                              capture_output=True, timeout=15, cwd=ROOT,
                              env=env, check=False)
        self.assertEqual(good.returncode, 0, good.stderr[-700:])
        payload = json.loads(good.stdout)
        self.assertEqual(payload["finding_count"], 1)
        self.assertEqual(payload["findings"][0]["rule_id"],
                         "PY_SCANDIR_SHARED_ITERATOR_RACE")
        bad = subprocess.run(cmd, input="def invalid(:", text=True,
                             capture_output=True, timeout=15, cwd=ROOT,
                             env=env, check=False)
        self.assertEqual(bad.returncode, 2, bad.stderr[-700:])
        error = json.loads(bad.stdout)
        self.assertEqual(error["status"], "CODE_REVIEW_FAIL_CLOSED")
        self.assertNotIn("invalid(", bad.stdout)
        self.assertFalse(error["source_executed"])

    @unittest.skipUnless(shutil.which("pwsh") or shutil.which("pwsh.exe")
                         or shutil.which("powershell.exe"), "PowerShell unavailable")
    def test_actual_single_command_powershell(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        cmd = [sys.executable, "-B", "-m", "ucie_miner.code_review_v1",
               "--ucie-root", str(ROOT), "--language", "powershell"]
        got = subprocess.run(cmd, input=PS_DOT, text=True,
                             capture_output=True, timeout=40, cwd=ROOT,
                             env=env, check=False)
        self.assertEqual(got.returncode, 0, got.stderr[-700:])
        result = json.loads(got.stdout)
        self.assertEqual(result["finding_count"], 1)
        self.assertEqual(result["findings"][0]["rule_id"],
                         "PS_RESOLVE_PATH_DOT_PREFIX")
        self.assertEqual(result["source_files_read"], 0)
        self.assertFalse(result["source_executed"])


if __name__ == "__main__":
    unittest.main()
