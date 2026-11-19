"""W30 native exclusive receipt writer on disposable CI temporary directory.

AST-extract real first-party W30 Absent / SaveW30, execute only those
against temp paths owned by test. No live owner archives, Tasks, C40 or SQLite.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "ucie_owner_w30_secondary_oldroot_restore_v01.ps1"


class W30DisposableOneShotJournalTests(unittest.TestCase):
    def test_original_w29_receipts_immutable_and_w30_attempts_exclusive(self):
        shell = "powershell.exe" if os.name == "nt" else shutil.which("pwsh")
        if not shell:
            self.skipTest("Native PowerShell unavailable")
        with tempfile.TemporaryDirectory(prefix="ucie_w30_journal_only_") as td:
            work = Path(td)
            script = work / "w30_real_writer_temp.ps1"
            source = str(SOURCE).replace("'", "''")
            directory = str(work).replace("'", "''")
            script.write_text(rf"""
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tok=$null;$err=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('{source}',[ref]$tok,[ref]$err)
if(@($err).Count -ne 0){{throw 'UCIE_W30_SOURCE_PARSE_INVALID'}}
foreach($fn in @('Absent','SaveW30')){{
    $hits=@($ast.FindAll({{param($n)
        ($n -is [Management.Automation.Language.FunctionDefinitionAst] -and
         $n.Name -ceq $fn)}},$true))
    if($hits.Count -ne 1){{throw 'UCIE_W30_WRITER_FUNCTION_MISSING'}}
    . ([scriptblock]::Create($hits[0].Extent.Text))
}}
$archive='{directory}'
$w30Intent=Join-Path $archive 'UCIE_W30_OWNER_SECONDARY_RECOVERY_INTENT_V01.json'
$w30Retry=Join-Path $archive 'UCIE_W30_OWNER_SECONDARY_RETRY_INTENT_V01.json'
$w30Restored=Join-Path $archive 'UCIE_W30_OWNER_SECONDARY_RESTORED_V01.json'
$w29=Join-Path $archive 'UCIE_W29_OWNER_OLDROOT_RECOVERY_INTENT_V01.json'
[IO.File]::WriteAllText($w29,'HISTORIC_W29_CANARY')
SaveW30 $w30Intent ([ordered]@{{schema='W30_TEST';status='FIRST'}})
$before=[IO.File]::ReadAllBytes($w30Intent)
try{{
    SaveW30 $w30Intent ([ordered]@{{schema='W30_TEST';status='REPLAY'}})
    throw 'UCIE_W30_WRITER_ALLOWED_REPLAY'
}}catch{{
    if($_.Exception.Message -cne 'UCIE_W30_ALREADY_EXISTS_NO_BLIND_RETRY'){{throw}}
}}
$after=[IO.File]::ReadAllBytes($w30Intent)
if($before.Length -ne $after.Length){{throw 'UCIE_W30_REPLAY_CHANGED_BYTES'}}
for($idx=0;$idx -lt $before.Length;$idx++){{
    if($before[$idx] -ne $after[$idx]){{throw 'UCIE_W30_REPLAY_CHANGED_BYTES'}}
}}
try{{
    SaveW30 $w29 ([ordered]@{{status='MUTATE_W29'}})
    throw 'UCIE_W30_UNAUTHORIZED_LEGACY_DESTINATION'
}}catch{{
    if($_.Exception.Message -cne 'UCIE_W30_UNLISTED_DESTINATION_DENIED'){{throw}}
}}
if([IO.File]::ReadAllText($w29) -cne 'HISTORIC_W29_CANARY'){{
    throw 'UCIE_W30_LEGACY_W29_CANARY_CHANGED'
}}
SaveW30 $w30Retry ([ordered]@{{status='BOUNDED_RETRY'}})
SaveW30 $w30Restored ([ordered]@{{status='RESTORED'}})
$temps=@(Get-ChildItem -LiteralPath $archive -File -Filter 'UCIE_W30_*.tmp')
if($temps.Count -ne 0){{throw 'UCIE_W30_ORPHAN_WRITER_TMP'}}
Write-Output 'UCIE_W30_REAL_WRITER_DISPOSABLE_EXCLUSIVE_AND_W29_CANARY_PASS'
""", encoding="utf-8")
            cmd = [shell, "-NoProfile", "-NonInteractive"]
            if os.name == "nt":
                cmd += ["-ExecutionPolicy", "Bypass"]
            result = subprocess.run(cmd + ["-File", str(script)],
                                    capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)
            self.assertIn(
                "UCIE_W30_REAL_WRITER_DISPOSABLE_EXCLUSIVE_AND_W29_CANARY_PASS",
                result.stdout,
            )
            self.assertEqual(
                (work / "UCIE_W29_OWNER_OLDROOT_RECOVERY_INTENT_V01.json")
                .read_text(encoding="utf-8"), "HISTORIC_W29_CANARY")


if __name__ == "__main__":
    unittest.main()
