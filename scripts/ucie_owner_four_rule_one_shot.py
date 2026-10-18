r"""ONE local owner-PC command for UCIE four-rule public-only acceptance.

Only D:\UCIE, clean main, matching live GitHub CI and explicit in-person
consent. No private-project scanning, auto-deploy, scheduler, key export or
untrusted code execution. Existing signed Serial 3 stays immutable.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ucie_owner_two_rule_one_shot import git, ORIGINS, select_exact_ci
from ucie_public.owner_release import (
    REPO, _public_json, validate_live_automated_qa,
)
from ucie_public.selected_release import verify_selected_owner_release
from ucie_public.mixed_release import (
    RULE_ORDER, ELIGIBLE, CONFIRM, FOURTH_ID,
    _fourth_ci, publish_mixed_owner_release, verify_mixed_owner_release,
    scan_mixed_owner_receipt,
)
from ucie_public.multi_owner_release import _postfix_ci
from ucie_public.selected_release import _third_ci
from ucie_public.policy import PolicyError
from ucie_miner.static_concurrency import inspect_python_scandir_source

ROOT = Path(r"D:\UCIE")
SERIAL = 4
PY_POSITIVE = """import os
def unsafe(root, executor, worker):
    iterator = os.scandir(root)
    return executor.submit(worker, iterator).result()
"""
PY_NEGATIVE = """def safe(root, executor, worker):
    with GuardedScandir(root) as iterator:
        return executor.submit(worker, iterator).result()
"""
PS_POSITIVE = (
    "python -I -X disable_remote_debug -\n"
    "Resolve-Path '.directory\\*.txt' -Relative\n"
    "Get-Command Get-FuzzyDuplicat -UseFuzzyMatching -FuzzyMinimumDistance 1\n"
)
PS_NEGATIVE = (
    "python -I -X disable-remote-debug -\n"
    "Resolve-Path '.directory\\*.txt' -ErrorAction Stop\n"
    "Get-Command Get-FuzzyDuplicat\n"
)
PS_COMMAND = r"""
$ErrorActionPreference = 'Stop'
. $env:UCIE_TEST_SCANNER
$src = [System.Text.Encoding]::UTF8.GetString(
    [System.Convert]::FromBase64String($env:UCIE_TEST_SAMPLE))
$receipt = Find-UCIEPowerShellCandidate -SourceText $src
ConvertTo-Json -InputObject $receipt -Compress -Depth 10
"""


def owner_input() -> dict[str, str]:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise PolicyError("four-rule owner acceptance requires a real terminal")
    print("SCOPE: PUBLIC_ONLY_MANUAL_STATIC_SCAN; exactly four pinned rules.")
    print("Python 3.15.0 RELEASE SOURCE LACKS scandir synchronization fix.")
    print("No unsafe native crash retest, human QA or legal-license signoff.")
    print("No released fixed-version coverage, private scan or auto-fix.")
    phrases = [CONFIRM] + [ELIGIBLE[code][2] for code in RULE_ORDER]
    typed = []
    for i, phrase in enumerate(phrases, start=1):
        print(f"OWNER decision {i}/{len(phrases)} -- type EXACT phrase:")
        print(phrase)
        value = input("Explicit decision: ")
        if value != phrase:
            raise PolicyError("owner did not accept every separate rule risk")
        typed.append(value)
    return {rid: accepted for rid, accepted in zip(RULE_ORDER, typed[1:], strict=True)}


def power_shell_receipt(scanner: Path, source: str, root: Path) -> dict:
    if (scanner.is_symlink() or not scanner.is_file()
            or scanner.resolve() !=
            (root / "scripts" / "ucie_powershell_static_candidates.ps1").resolve()):
        raise PolicyError("unexpected first-party AST scanner path")
    env = {
        key: value for key, value in os.environ.items()
        if key.upper() in (
            "SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP",
            "PSMODULEPATH", "USERPROFILE", "COMSPEC")
    }
    env["UCIE_TEST_SCANNER"] = str(scanner)
    env["UCIE_TEST_SAMPLE"] = base64.b64encode(
        source.encode("utf-8")).decode("ascii")
    encoded = base64.b64encode(
        PS_COMMAND.encode("utf-16le")).decode("ascii")
    # Windows PowerShell 5.1 may encode STDERR using the local OEM/code page
    # while STDOUT contains JSON. Never let Python's background pipe-reader
    # silently lose UnicodeDecodeError and still report success.
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive",
         "-EncodedCommand", encoded],
        cwd=root, env=env, capture_output=True, text=False,
        stdin=subprocess.DEVNULL, timeout=45, check=False,
    )
    if (type(proc.stdout) is not bytes
            or type(proc.stderr) is not bytes):
        raise PolicyError("PowerShell capture did not return raw bytes")
    if proc.returncode != 0 or proc.stderr:
        raise PolicyError(
            "synthetic PowerShell AST scanner emitted an error or diagnostic "
            f"(exit={proc.returncode}, stderr_bytes={len(proc.stderr)}, "
            f"stderr_prefix_hex={proc.stderr[:256].hex()})")
    if not proc.stdout or len(proc.stdout) > 131072:
        raise PolicyError("empty or oversized synthetic AST JSON response")
    try:
        receipt = json.loads(proc.stdout.decode("utf-8-sig", errors="strict"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise PolicyError("PowerShell AST receipt is not strict UTF-8 JSON") from exc
    if type(receipt) is not dict:
        raise PolicyError("unexpected PowerShell AST receipt")
    return receipt


def smoke(root: Path, pack: Path, trust: Path) -> tuple[int, int, int, int]:
    scanner = root / "scripts" / "ucie_powershell_static_candidates.ps1"
    results = [
        scan_mixed_owner_receipt(
            pack, trust, power_shell_receipt(scanner, sample, root),
            min_serial=SERIAL)
        for sample in (PS_POSITIVE, PS_NEGATIVE)
    ]
    results += [
        scan_mixed_owner_receipt(
            pack, trust, inspect_python_scandir_source(sample),
            min_serial=SERIAL)
        for sample in (PY_POSITIVE, PY_NEGATIVE)
    ]
    for r in results:
        if (r.get("owner_signature") != "VALID"
                or r.get("pack_serial") != SERIAL
                or r.get("source_executed") is not False
                or r.get("auto_fix_applied") is not False
                or r.get("persistent_writes") != 0
                or r.get("scope") != "PUBLIC_ONLY_MANUAL_STATIC_SCAN"):
            raise PolicyError("mixed static scanner broke owner-approved scope")
    counts = tuple(x["finding_count"] for x in results)
    if (counts != (3, 0, 1, 0)
            or [x["rule_id"] for x in results[0]["findings"]]
               != list(RULE_ORDER[:3])
            or [x["rule_id"] for x in results[2]["findings"]]
               != [FOURTH_ID]):
        raise PolicyError("four-rule synthetic smoke does not match expected limits")
    return counts


def verify_existing(root: Path = ROOT) -> dict:
    """Read-only recovery after interrupted post-signing smoke tests.

    Never re-sign, read the private signing key or request owner approval.
    Preserve existing owner-signed Serial 3 and Serial 4 bytes unchanged.
    """
    if os.name != "nt" or str(root).casefold() != str(ROOT).casefold():
        raise PolicyError("owner verification allowed only in D:\\UCIE on Windows")
    python = root / ".venv" / "Scripts" / "python.exe"
    if (not python.is_file() or python.is_symlink()
            or not os.path.samefile(sys.executable, python)):
        raise PolicyError("must use existing UCIE virtualenv interpreter")
    public = root / ".build_keys" / "production" / "public_production.pem"
    old = root / "build" / "UCIE_Selected_Three_Rule_Serial_3.zip"
    pack = root / "build" / "UCIE_Selected_Four_Rule_Serial_4.zip"
    for path in (public, old, pack):
        if path.is_symlink() or not path.is_file():
            raise PolicyError("existing signed pack or public trust key missing")
    original = verify_selected_owner_release(old, public, min_serial=3)
    if (original.get("result") != "SELECTED_OWNER_RISK_PUBLIC_PACK_VERIFIED"
            or original.get("serial") != 3
            or original.get("owner_signature") != "VALID"
            or original.get("rule_ids") != list(RULE_ORDER[:3])):
        raise PolicyError("previous Serial 3 owner pack no longer verifies")
    signed = verify_mixed_owner_release(pack, public, min_serial=SERIAL)
    if (signed.get("result") != "MIXED_OWNER_PUBLIC_MANUAL_PACK_VERIFIED"
            or signed.get("serial") != SERIAL
            or signed.get("owner_signature") != "VALID"
            or signed.get("rule_ids") != list(RULE_ORDER)
            or signed.get("fixed_python_3_15_0_coverage_proven") is not False
            or signed.get("unsafe_native_race_retested") is not False
            or signed.get("auto_apply") is not False):
        raise PolicyError("existing Serial 4 owner pack no longer verifies")
    counts = smoke(root, pack, public)
    # Verify Serial 3 again after read-only synthetic scanner execution.
    if verify_selected_owner_release(
            old, public, min_serial=3).get("owner_signature") != "VALID":
        raise PolicyError("previous Serial 3 was not preserved")
    return {
        "status": "UCIE_FOUR_RULE_OWNER_READ_ONLY_VERIFIED",
        "pack": str(pack), "serial": SERIAL, "rule_count": len(RULE_ORDER),
        "powershell_positive": counts[0], "powershell_negative": counts[1],
        "python_positive": counts[2], "python_negative": counts[3],
        "serial_3_preserved": True, "owner_signature": "VALID",
        "signing_attempted": False, "owner_approval_requested": False,
        "private_key_read": False, "files_rewritten": False,
        "source_executed": False, "auto_fix": False,
    }


def run(root: Path = ROOT) -> dict:
    if os.name != "nt" or str(root).casefold() != str(ROOT).casefold():
        raise PolicyError("owner execution allowed only in D:\\UCIE on Windows")
    python = root / ".venv" / "Scripts" / "python.exe"
    if (not python.is_file() or python.is_symlink()
            or not os.path.samefile(sys.executable, python)):
        raise PolicyError("must use existing D:\\UCIE virtualenv interpreter")
    private = root / ".build_keys" / "production" / "private_production.pem"
    public = root / ".build_keys" / "production" / "public_production.pem"
    old = root / "build" / "UCIE_Selected_Three_Rule_Serial_3.zip"
    dest = root / "build" / "UCIE_Selected_Four_Rule_Serial_4.zip"
    for path in (private, public, old):
        if path.is_symlink() or not path.is_file():
            raise PolicyError("missing or symlinked local owner evidence")
    if dest.exists() or dest.is_symlink():
        raise PolicyError("Serial 4 already exists; never overwrite or repeat signing")
    if git(root, "remote", "get-url", "origin") not in ORIGINS:
        raise PolicyError("unapproved UCIE origin")
    if git(root, "branch", "--show-current") != "main":
        raise PolicyError("require main branch")
    sha = git(root, "rev-parse", "HEAD")
    if (len(sha) != 40 or any(x not in "0123456789abcdef" for x in sha)
            or git(root, "status", "--porcelain")):
        raise PolicyError("owner checkout not a clean UCIE commit")
    old_ok = verify_selected_owner_release(old, public, min_serial=3)
    if (old_ok.get("result") != "SELECTED_OWNER_RISK_PUBLIC_PACK_VERIFIED"
            or old_ok.get("serial") != 3
            or old_ok.get("rule_ids") != list(RULE_ORDER[:3])
            or old_ok.get("owner_signature") != "VALID"):
        raise PolicyError("previous Serial 3 owner pack not verified")
    url = f"https://api.github.com/repos/{REPO}/actions/runs?branch=main&per_page=10"
    run_id = select_exact_ci(_public_json(url), sha)
    main_ci = validate_live_automated_qa(run_id)
    second = _postfix_ci()
    third = _third_ci()
    fourth = _fourth_ci()
    if (main_ci["head_sha"] != sha or second["result"] != "PASS_ON_PINNED_CI"
            or third["result"] != "PASS_ON_PINNED_CI"
            or fourth["result"] != "SAFE_GUARD_AND_PINNED_SOURCE_PASS"):
        raise PolicyError("four-rule CI evidence mismatch")
    print(f"PRE-FLIGHT PASS: main={sha} CI={run_id} legacy Serial 3 verified")
    accepted = owner_input()
    publish_mixed_owner_release(
        root, private, dest, run_id=run_id, serial=SERIAL,
        rule_ids=list(RULE_ORDER), confirmation=CONFIRM,
        risk_acceptances=accepted,
    )
    signed = verify_mixed_owner_release(dest, public, min_serial=SERIAL)
    if (signed.get("result") != "MIXED_OWNER_PUBLIC_MANUAL_PACK_VERIFIED"
            or signed.get("serial") != SERIAL
            or signed.get("owner_signature") != "VALID"
            or signed.get("rule_ids") != list(RULE_ORDER)
            or signed.get("fixed_python_3_15_0_coverage_proven") is not False
            or signed.get("unsafe_native_race_retested") is not False
            or signed.get("auto_apply") is not False):
        raise PolicyError("signed Serial 4 recipient verification failed")
    positive_ps, negative_ps, positive_py, negative_py = smoke(root, dest, public)
    if verify_selected_owner_release(
            old, public, min_serial=3).get("owner_signature") != "VALID":
        raise PolicyError("Serial 3 signature no longer verifies")
    return {
        "status": "UCIE_FOUR_RULE_OWNER_LOCAL_PASS",
        "pack": str(dest), "serial": SERIAL, "rule_count": 4,
        "main_ci_run_id": run_id,
        "powershell_positive": positive_ps, "powershell_negative": negative_ps,
        "python_positive": positive_py, "python_negative": negative_py,
        "serial_3_preserved": True, "owner_approved": True,
        "source_executed": False, "unsafe_native_race_retested": False,
        "fixed_python_3_15_0_coverage_proven": False,
        "auto_fix": False, "automatic_distribution": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE owner-only four-rule Serial4 one-shot with in-person risk phrases")
    parser.add_argument(
        "--verify-existing", action="store_true",
        help="Verify already-issued Serial 4 without approval or signing")
    args = parser.parse_args(argv)
    try:
        result = verify_existing() if args.verify_existing else run()
        print(json.dumps(result, sort_keys=True))
        return 0
    except (PolicyError, OSError, ValueError, RuntimeError,
            subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "UCIE_FOUR_RULE_OWNER_NO_GO",
                          "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
