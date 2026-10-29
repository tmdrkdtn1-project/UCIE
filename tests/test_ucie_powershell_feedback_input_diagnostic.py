"""Actual Windows PowerShell JSON conversion -> UCIE CLI inert input test."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

class PowerShellFeedbackInputDiagnostic(unittest.TestCase):
    def test_windows_powershell_json_to_inspector(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(root.name.casefold(), "ucie")
        shell=shutil.which("powershell.exe") or shutil.which("pwsh.exe")
        if not shell:
            self.skipTest("PowerShell not available")
        command = r"""
$ErrorActionPreference='Stop'
$source = @'
import os
from concurrent.futures import ThreadPoolExecutor
def run(folder, callback):
    iterator = os.scandir(folder)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return pool.submit(callback, iterator).result()
'@
$feedbackJson = ConvertTo-Json -InputObject @(
    @{
        case_id = 'risk'
        source = $source
        expected_rule_ids = @('PY_SCANDIR_SHARED_ITERATOR_RACE')
    },
    @{
        case_id = 'safe'
        source = 'pass'
        expected_rule_ids = @()
    }
) -Depth 5
$feedbackJson
"""
        got=subprocess.run([shell,"-NoProfile","-NonInteractive","-Command",command],
            cwd=root,capture_output=True,text=True,timeout=12,
            encoding="utf-8",errors="replace")
        self.assertEqual(got.returncode,0,got.stderr[-700:])
        raw=got.stdout.strip().lstrip("\ufeff")
        doc=json.loads(raw)
        cases=doc if isinstance(doc,list) else [doc]
        info={"root_kind":type(doc).__name__,"case_count":len(cases),
              "fields":[{"case_id":x.get("case_id"),
                         "keys":sorted(x.keys()),
                         "rule_ids_type":type(x.get("expected_rule_ids")).__name__,
                         "rule_ids":x.get("expected_rule_ids")}
                        for x in cases]}
        print("UCIE_PWSH_FEEDBACK_BOUNDARY="+json.dumps(info,sort_keys=True))
        env=os.environ.copy()
        env["PYTHONPATH"]=str(root/"src")
        proc=subprocess.run(
            [sys.executable,"-B","-m","ucie_miner.existing_rule_inspection",
             "--ucie-root",str(root),"--feedback-synthetic"],
            cwd=root,input=raw,text=True,capture_output=True,timeout=10,env=env)
        receipt=json.loads(proc.stdout)
        print("UCIE_PWSH_FEEDBACK_RESULT="+json.dumps({
            "exit_code":proc.returncode,
            "status":receipt.get("status"),
            "reason_code":receipt.get("reason_code"),
            "error_type":receipt.get("error_type"),
            "case_count":receipt.get("case_count"),
            "true_positive_rules":receipt.get("true_positive_rules"),
        },sort_keys=True))
        self.assertEqual(proc.returncode,0,proc.stderr[-700:])
        self.assertEqual(receipt["case_count"],2)
        self.assertEqual(receipt["true_positive_rules"],1)

if __name__=="__main__":
    unittest.main()
