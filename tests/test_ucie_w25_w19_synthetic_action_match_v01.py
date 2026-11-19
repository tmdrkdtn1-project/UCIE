"""W25 synthetic Windows PowerShell W19 action-matching regression.

Execute W19's ACTUAL first-party pure Same/ConfirmThree function bodies against
disposable in-memory ScheduledTask-shaped objects. Mocks TaskItem; NEVER
imports ScheduledTasks, reads a host task, opens SQLite or writes anything.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
W19 = ROOT / "scripts" / "ucie_owner_w19_data_task_stage_v01.ps1"


def function_source() -> str:
    text = W19.read_text("utf-8")
    beginning = text.index("function Same(")
    ending = text.index("function C40Hash", beginning)
    code = text[beginning:ending]
    if ("function Same(" not in code or "function ConfirmThree(" not in code
            or "Get-ScheduledTask" in code or "Set-ScheduledTask" in code):
        raise AssertionError("Unexpected first-party W19 helper source")
    return code


class W25OriginalW19SyntheticTaskActionTests(unittest.TestCase):
    def test_w19_real_function_bodies_accept_exact_disabled_old_actions(self):
        shell = "powershell.exe" if os.name == "nt" else shutil.which("pwsh")
        if not shell:
            self.skipTest("Native PowerShell unavailable")
        code = function_source()
        with tempfile.TemporaryDirectory(prefix="ucie_w25_w19_mock_") as td:
            file = Path(td) / "mock_w19_original_actions.ps1"
            file.write_text(
                "Set-StrictMode -Version Latest\n"
                "$ErrorActionPreference='Stop'\n"
                "$old='D:\\UCIE'\n"
                "$root='D:\\UCIE_PROJECT\\UCIE'\n"
                "$specs=@(\n"
                "  [pscustomobject]@{Name='UCIE-PublicMiner-Hourly';OldExe='D:\\UCIE\\.venv\\Scripts\\python.exe';OldArgs='\"D:\\UCIE\\scripts\\public_miner_cycle.py\"'},\n"
                "  [pscustomobject]@{Name='UCIE-Internal-Minute';OldExe='D:\\UCIE\\.venv\\Scripts\\python.exe';OldArgs='-B \"D:\\UCIE\\scripts\\internal_minute_tick.py\"'},\n"
                "  [pscustomobject]@{Name='UCIE-LocalV1-Web';OldExe='D:\\UCIE\\.venv\\Scripts\\pythonw.exe';OldArgs='-B \"D:\\UCIE\\scripts\\run_ucie_local_v1_autostart.py\" --port 18767'}\n"
                ")\n"
                "function TaskItem([string]$name){\n"
                "  $s=$specs | Where-Object {$_.Name -eq $name}\n"
                "  if(@($s).Count -ne 1){throw 'UCIE_W25_FIXTURE_UNKNOWN_TASK'}\n"
                "  return [pscustomobject]@{State='Disabled';Actions=@([pscustomobject]@{Execute=$s.OldExe;Arguments=$s.OldArgs;WorkingDirectory=$old})}\n"
                "}\n"
                + code + "\n"
                "ConfirmThree $false\n"
                "Write-Output 'UCIE_W25_W19_SYNTHETIC_OLD_ACTIONS_MATCH_PASS'\n",
                encoding="utf-8",
            )
            cmd = [shell, "-NoProfile", "-NonInteractive"]
            if os.name == "nt":
                cmd.extend(["-ExecutionPolicy", "Bypass"])
            cmd.extend(["-File", str(file)])
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=30, check=False)
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)
            self.assertIn("UCIE_W25_W19_SYNTHETIC_OLD_ACTIONS_MATCH_PASS",
                          result.stdout)

    def test_w19_actual_functions_contain_no_host_access(self):
        code = function_source()
        self.assertIn("Same ($t.Actions[0]) $s.OldExe $s.OldArgs $old", code)
        self.assertIn("function Same($action,[string]$exe,[string]$expectedArguments,", code)
        self.assertNotIn("[string]$args,", code)
        self.assertNotIn("Get-ScheduledTask", code)
        self.assertNotIn("Set-ScheduledTask", code)
        self.assertNotIn("Get-Content", code)
        self.assertNotIn("Stop-Process", code)


if __name__ == "__main__":
    unittest.main()
