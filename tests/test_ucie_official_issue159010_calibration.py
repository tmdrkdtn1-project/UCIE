"""UCIE source-grounded, nonexecuting first-rule calibration.

Only the console REPRODUCER published in official python/cpython issue
#159010 is used here, with the leading "$ " shell prompt removed.
This is NOT a claimed real-world PowerShell script file, external QA,
population accuracy measurement, or a fresh CPython runtime experiment.
No untrusted source is evaluated. Never use signer keys or private files.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
ISSUE = "https://github.com/python/cpython/issues/159010"
FIX = "https://github.com/python/cpython/pull/159014"
RULE = "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO"
# Verbatim issue console commands, excluding only the printed "$ " prompt.
REPORTED_WRONG = 'python3.14 -X disable_remote_debug -c "import sys; print(sys.is_remote_debug_enabled())"'
REPORTED_FIXED = 'python3.14 -X disable-remote-debug -c "import sys; print(sys.is_remote_debug_enabled())"'


@unittest.skipUnless(os.name == "nt", "Windows PowerShell AST required")
class OfficialCPythonIssue159010Calibration(unittest.TestCase):
    def parse_literal_without_execution(self, source: str) -> dict:
        scanner = ROOT / "scripts" / "ucie_powershell_static_candidates.ps1"
        self.assertTrue(scanner.is_file() and not scanner.is_symlink())
        encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
        escaped_path = str(scanner).replace("'", "''")
        # Only UCIE-authored code executes; base64 is decoded to inert
        # SourceText passed to Parser.ParseInput, never a scriptblock.
        program = (
            ". '" + escaped_path + "'\n"
            "$source = [Text.Encoding]::UTF8.GetString("
            "[Convert]::FromBase64String('" + encoded + "'))\n"
            "$receipt = Find-UCIEPowerShellCandidate -SourceText $source\n"
            "$receipt | ConvertTo-Json -Depth 8 -Compress\n"
        )
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-Command", program],
            cwd=str(ROOT), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=18, check=False,
        )
        self.assertEqual(p.returncode, 0, "UCIE inert parser process failed")
        return json.loads(p.stdout.decode("utf-8-sig"))

    def test_real_upstream_reported_console_reproducer(self):
        positive = self.parse_literal_without_execution(REPORTED_WRONG)
        negative = self.parse_literal_without_execution(REPORTED_FIXED)
        self.assertEqual(positive["finding_count"], 1)
        self.assertEqual(negative["finding_count"], 0)
        match = positive["findings"][0]
        self.assertEqual(match["pattern_code"], RULE)
        self.assertEqual(match["public_evidence"], FIX)
        for receipt in (positive, negative):
            self.assertIs(receipt["parser_executed_supplied_code"], False)
            self.assertEqual(receipt["source_files_read"], 0)
            self.assertEqual(receipt["persistent_writes"], 0)
            self.assertEqual(receipt["approved_rules"], 0)
            self.assertIs(receipt["production_approved"], False)
        print("UCIE_OFFICIAL_ISSUE_CALIBRATION=" + json.dumps({
            "schema": "UCIE_OFFICIAL_ISSUE_159010_CALIBRATION_V1",
            "source": ISSUE, "fix": FIX,
            "case_kind": "PUBLIC_CONSOLE_REPRODUCER_PARSE_AS_POWERSHELL",
            "positive_findings": positive["finding_count"],
            "negative_findings": negative["finding_count"],
            "source_executed": False,
            "source_files_read": 0,
            "persistent_writes": 0,
            "independent_human_qa": False,
            "real_powershell_repository_positive_found": False,
        }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
