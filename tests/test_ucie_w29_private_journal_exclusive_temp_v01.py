"""W29 actual first-party private journal writer on disposable CI temp only.

Extract ONLY W29 Absent/SavePrivate native PowerShell AST and run on a temporary
directory created by this test. Proves exclusive non-overwrite, exact journal
allowlist, and atomic temp->destination move. NEVER touches owner UCIE archive.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "ucie_owner_w29_oldroot_rehearsal_restore_v01.ps1"


class W29DisposablePrivateReceiptTests(unittest.TestCase):
    def test_real_w29_absent_and_saveprivate_on_disposable_temp(self):
        shell = "powershell.exe" if os.name == "nt" else shutil.which("pwsh")
        if not shell:
            self.skipTest("PowerShell unavailable")
        with tempfile.TemporaryDirectory(prefix="ucie_w29_only_mock_archive_") as td:
            work = Path(td)
            ps = work / "w29_only_journal_writer_test.ps1"
            quoted_source = str(SOURCE).replace("'", "''")
            quoted_work = str(work).replace("'", "''")
            ps.write_text(rf"""
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('{quoted_source}',[ref]$tokens,[ref]$errors)
if(@($errors).Count -ne 0){{throw 'UCIE_W29_JOURNAL_SOURCE_PARSE_FAILED'}}
foreach($name in @('Absent','SavePrivate')){{
    $found=@($ast.FindAll({{param($node)
        ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and
         $node.Name -ceq $name)}},$true))
    if($found.Count -ne 1){{throw 'UCIE_W29_JOURNAL_SOURCE_FN_NOT_UNIQUE'}}
    . ([scriptblock]::Create($found[0].Extent.Text))
}}
$archive='{quoted_work}'
$intent=Join-Path $archive 'UCIE_W29_OWNER_OLDROOT_REHEARSAL_INTENT_V01.json'
$recoveryIntent=Join-Path $archive 'UCIE_W29_OWNER_OLDROOT_RECOVERY_INTENT_V01.json'
$restored=Join-Path $archive 'UCIE_W29_OWNER_OLDROOT_RESTORED_V01.json'
$other=Join-Path $archive 'UCIE_W22_OWNER_MAINTENANCE_INTENT_V01.json'
[IO.File]::WriteAllText($other,'HISTORICAL_CANARY')
SavePrivate $intent ([ordered]@{{schema='UCIE_W29_SYNTHETIC';status='INTENT'}})
if(-not (Test-Path -LiteralPath $intent)){{
    throw 'UCIE_W29_INTENT_NOT_DURABLY_WRITTEN'
}}
$before=[IO.File]::ReadAllBytes($intent)
try{{
    SavePrivate $intent ([ordered]@{{schema='OVERWRITE_ATTEMPT'}})
    throw 'UCIE_W29_UNEXPECTED_DUPLICATE_WRITE'
}}catch{{
    if($_.Exception.Message -cne 'UCIE_W29_UNEXPECTED_EXISTING_PRIVATE_OUTPUT_HOLD'){{throw}}
}}
$after=[IO.File]::ReadAllBytes($intent)
if($before.Length -ne $after.Length){{
    throw 'UCIE_W29_DUPLICATE_CHANGED_EXISTING_RECEIPT'
}}
for($idx=0;$idx -lt $before.Length;$idx++){{
    if($before[$idx] -ne $after[$idx]){{
        throw 'UCIE_W29_DUPLICATE_CHANGED_EXISTING_RECEIPT'
    }}
}}
try{{
    SavePrivate $other ([ordered]@{{schema='UNLISTED_WRITE_ATTEMPT'}})
    throw 'UCIE_W29_UNEXPECTED_LEGACY_WRITE'
}}catch{{
    if($_.Exception.Message -cne 'UCIE_W29_UNLISTED_JOURNAL_DESTINATION_DENIED'){{throw}}
}}
if([IO.File]::ReadAllText($other) -cne 'HISTORICAL_CANARY'){{
    throw 'UCIE_W29_HISTORICAL_RECEIPT_CANARY_CHANGED'
}}
$leftover=@(Get-ChildItem -LiteralPath $archive -File -Filter 'UCIE_W29_*.tmp')
if($leftover.Count -ne 0){{throw 'UCIE_W29_ORPHAN_TEMP_LEFT_AFTER_WRITE'}}
Write-Output 'UCIE_W29_REAL_JOURNAL_WRITER_TEMP_EXCLUSIVE_AND_HISTORY_PRESERVED_PASS'
""", encoding="utf-8")
            cmd = [shell, "-NoProfile", "-NonInteractive"]
            if os.name == "nt":
                cmd += ["-ExecutionPolicy", "Bypass"]
            result = subprocess.run(cmd + ["-File", str(ps)],
                                    capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)
            self.assertIn(
                "UCIE_W29_REAL_JOURNAL_WRITER_TEMP_EXCLUSIVE_AND_HISTORY_PRESERVED_PASS",
                result.stdout,
            )
            self.assertEqual(
                (work / "UCIE_W22_OWNER_MAINTENANCE_INTENT_V01.json")
                .read_text(encoding="utf-8"), "HISTORICAL_CANARY")


if __name__ == "__main__":
    unittest.main()
