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
import unittest
from unittest.mock import patch

from ucie_miner.code_review_v1 import (
    CodeReviewError, review_code, SCHEMA, MAX_BYTES,
)

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
        empty = review_code("pass\n", language="python", root=ROOT)
        self.assertEqual(empty["status"], "NO_KNOWN_PATTERN_NOT_SAFETY_PASS")
        self.assertFalse(empty["full_code_safety_verified"])

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
