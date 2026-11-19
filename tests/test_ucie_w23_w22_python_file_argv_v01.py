"""W23 regression: no PowerShell 5.1 nested -c Python quote forwarding.

Default contract and denied approval are no-host. Synthetic W19 helpers prove
the Python file imports preserved nested quotes; native PowerShell uses only
file/ASCII args, not source passed as argv. No live Windows task operations.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "ucie_owner_w23_w19_lineage_gate_v01.py"
W22 = ROOT / "scripts" / "ucie_owner_w22_quiesce_resume_local_v01.ps1"


def load_gate():
    spec = importlib.util.spec_from_file_location("ucie_w23_argv_guard_fixture", GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load_gate()


class W23QuoteSafeLineageTests(unittest.TestCase):
    def test_contract_default_and_exact_approval_denied(self):
        cmd = [sys.executable, "-I", "-B", str(GATE)]
        no_host = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        self.assertEqual(no_host.returncode, 0, no_host.stderr)
        status = json.loads(no_host.stdout)
        self.assertEqual(status["status"], "UCIE_W23_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(status["private_receipts_read"])
        self.assertFalse(status["tasks_queried_or_modified"])
        self.assertFalse(status["operating_sqlite_opened"])
        missing = subprocess.run(cmd + ["--check-owner"], capture_output=True,
                                 text=True, timeout=25)
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(json.loads(missing.stdout)["reason_code"],
                         "UCIE_W23_EXPLICIT_OWNER_READONLY_APPROVAL_REQUIRED")

    def test_synthetic_lineage_accepts_exact_ten_names_with_quoted_import(self):
        with tempfile.TemporaryDirectory(prefix="ucie_w23_lineage_") as td:
            fixture = Path(td) / "w19_owner_fixture.py"
            names = ["public_miner.sqlite3"] + [
                f"synthetic_{i:02d}.sqlite3" for i in range(9)
            ]
            fixture.write_text(
                "def _private_prerequisites():\n"
                f"    return set({names!r})\n",
                encoding="utf-8",
            )
            verified = gate.verify_lineage(fixture)
            self.assertEqual(verified, set(names))

    def test_bad_names_or_wrong_count_hold_without_host(self):
        with tempfile.TemporaryDirectory(prefix="ucie_w23_bad_") as td:
            fixture = Path(td) / "w19_invalid_fixture.py"
            for rows in ({"public_miner.sqlite3"},
                         {"public_miner.sqlite3", "../bad.sqlite3"}):
                with self.subTest(rows=rows):
                    fixture.write_text(
                        "def _private_prerequisites():\n"
                        f"    return set({sorted(rows)!r})\n",
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(gate.GateHold, "EXPECTED_TEN"):
                        gate.verify_lineage(fixture)

    def test_missing_or_symlinked_fixture_is_denied(self):
        with tempfile.TemporaryDirectory(prefix="ucie_w23_symlink_") as td:
            d = Path(td)
            self.assertFalse(gate.direct(d / "absent.py", directory=False))
            target = d / "real.py"
            target.write_text("def _private_prerequisites(): return set()\n",
                              encoding="utf-8")
            link = d / "linked.py"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks prohibited in this Windows CI context")
            with self.assertRaisesRegex(gate.GateHold, "SOURCE_NOT_DIRECT"):
                gate.verify_lineage(link)

    def test_w22_runtime_uses_python_file_not_multiline_c(self):
        source = W22.read_text("utf-8")
        invocation = "& $python -I -B $w23Lineage --check-owner --owner-approval $w23Approval"
        self.assertIn(invocation, source)
        self.assertIn("ucie_owner_w23_w19_lineage_gate_v01.py", source)
        self.assertNotIn("& $python -I -B -c $preflight", source)
        self.assertNotIn("$preflight=@", source)
        self.assertLess(
            source.index(invocation),
            source.index("SavePrivate $intent")
        )
        self.assertLess(
            source.index(invocation),
            source.index("Disable-ScheduledTask -TaskPath '\\' -TaskName $names[$i]")
        )

    def test_native_powershell_runs_python_file_with_nested_quotes_intact(self):
        ps = "powershell.exe" if os.name == "nt" else shutil.which("pwsh")
        if not ps:
            self.skipTest("PowerShell not installed")
        with tempfile.TemporaryDirectory(prefix="ucie_w23_ps_quote_") as td:
            root = Path(td)
            code = root / "quote_probe.py"
            code.write_text(
                "from importlib.util import spec_from_file_location\n"
                "from pathlib import Path\n"
                "assert spec_from_file_location('ucie_w19_private_gate', __file__) is not None\n"
                'assert "public_miner.sqlite3" == \'public_miner.sqlite3\'\n'
                "print('UCIE_W23_PYTHON_FILE_QUOTE_PRESERVED')\n",
                encoding="utf-8",
            )
            launcher = root / "launch_file.ps1"
            quote = lambda path: str(path).replace("'", "''")
            launcher.write_text(
                "$ErrorActionPreference='Stop'\n"
                f"& '{quote(sys.executable)}' -I -B '{quote(code)}'\n"
                "if ($LASTEXITCODE -ne 0) {throw 'UCIE_W23_NATIVE_FILE_ARG_FAILED'}\n",
                encoding="utf-8",
            )
            cmd = [ps, "-NoProfile", "-NonInteractive"]
            if os.name == "nt":
                cmd.extend(["-ExecutionPolicy", "Bypass"])
            cmd.extend(["-File", str(launcher)])
            outcome = subprocess.run(cmd, capture_output=True, text=True,
                                     timeout=30)
            self.assertEqual(outcome.returncode, 0,
                             outcome.stderr + outcome.stdout)
            self.assertIn("UCIE_W23_PYTHON_FILE_QUOTE_PRESERVED",
                          outcome.stdout)
            self.assertNotIn("NameError", outcome.stderr + outcome.stdout)


if __name__ == "__main__":
    unittest.main()
