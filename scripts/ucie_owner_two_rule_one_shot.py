"""ONE owner-PC command for UCIE's two-rule manual public-only acceptance.

Preflight -> three IN-PERSON decisions -> local signing -> offline receiver
verification -> two synthetic public-only AST scans. NO auto-approval.
No scheduler, no source-file scanning, no private data, no key upload.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

# Allow a direct D:\UCIE\.venv\Scripts\python.exe scripts\... invocation
# without relying on package installation or inheriting arbitrary PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ucie_public.owner_release import (
    REPO, WORKFLOW, _public_json, validate_live_automated_qa,
    verify_owner_risk_release,
)
from ucie_public.multi_owner_release import (
    CONFIRM, RISK, SECOND_RISK, SECOND_RUN,
    _postfix_ci, publish_two_rule_owner_release,
    verify_two_rule_owner_release,
)
from ucie_public.policy import PolicyError

EXPECTED_ROOT = r"D:\UCIE"
ORIGINS = frozenset({
    "https://github.com/tmdrkdtn1-project/UCIE",
    "https://github.com/tmdrkdtn1-project/UCIE.git",
})
RULE_IDS = [
    "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO",
    "PS_RESOLVE_PATH_DOT_PREFIX",
]


def git(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True,
        text=True, timeout=12, check=True,
    )
    return process.stdout.strip()


def select_exact_ci(runs: object, sha: str) -> int:
    """Choose only a completed PASS on exact checked-out main, never latest blindly."""
    if not isinstance(runs, dict) or not isinstance(runs.get("workflow_runs"), list):
        raise PolicyError("missing public GitHub CI run listing")
    matches = [
        item["id"] for item in runs["workflow_runs"]
        if isinstance(item, dict)
        and type(item.get("id")) is int
        and item.get("head_sha") == sha
        and item.get("event") == "push"
        and item.get("head_branch") == "main"
        and item.get("status") == "completed"
        and item.get("conclusion") == "success"
        and isinstance(item.get("path"), str)
        and item["path"].split("@", 1)[0] == WORKFLOW
    ]
    if not matches:
        raise PolicyError("no completed PASS for exact local main")
    return max(matches)


def owner_input() -> tuple[str, str, str]:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise PolicyError("three explicit owner consents require an interactive PC terminal")
    print("SCOPE: PUBLIC_ONLY_MANUAL_STATIC_SCAN; exactly two fixed rules.")
    print("PowerShell impact observed on 7.6.6 Windows/Linux; patched build")
    print("7.7.0-preview.6 is DEVELOPMENT CI, not verified released-version coverage.")
    print("Independent human QA and legal license signoff are NOT claimed.")
    print("No automatic deployment, code modification, or private-code scan.")
    responses = []
    for number, phrase in enumerate((CONFIRM, RISK, SECOND_RISK), start=1):
        print(f"Owner decision {number}/3: enter this EXACT phrase yourself:")
        print(phrase)
        typed = input("Explicit decision: ")
        if typed != phrase:
            raise PolicyError("owner did not expressly accept all three conditions")
        responses.append(typed)
    return tuple(responses)


def synthetic_scan(script: Path, pack: Path, trust: Path,
                   python: Path, sample: str, serial: int) -> dict:
    """ONLY a UCIE-authored inert sample, not any user file or private project."""
    command = [
        "powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(script),
        "-SourceText", sample, "-PackPath", str(pack),
        "-OwnerTrustPath", str(trust), "-PythonPath", str(python),
        "-MinSerial", str(serial),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60,
                            check=False)
    if result.returncode != 0 or len(result.stdout.encode("utf-8")) > 131072:
        raise PolicyError("manual synthetic PowerShell scan failed")
    try:
        parsed = json.loads(result.stdout)
    except (ValueError, UnicodeError) as exc:
        raise PolicyError("invalid manual scan output") from exc
    if (
        not isinstance(parsed, dict)
        or parsed.get("schema") != "UCIE_TWO_RULE_OWNER_PUBLIC_MANUAL_SCAN_V1"
        or parsed.get("owner_signature") != "VALID"
        or parsed.get("rule_ids") != RULE_IDS
        or parsed.get("pack_serial") != serial
        or parsed.get("source_executed") is not False
        or parsed.get("source_files_read") != 0
        or parsed.get("auto_fix_applied") is not False
        or parsed.get("auto_apply") is not False
        or parsed.get("release_version_coverage_proven") is not False
        or parsed.get("independent_human_qa_approved") is not False
        or parsed.get("legal_license_signoff") is not False
        or parsed.get("persistent_writes") != 0
    ):
        raise PolicyError("scan result outside approved manual scope")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ONE manual UCIE owner acceptance; prompts for explicit risk.")
    parser.add_argument("--serial", type=int, default=2)
    args = parser.parse_args(argv)
    if type(args.serial) is not int or not 2 <= args.serial <= 10000000:
        raise PolicyError("new two-rule serial must be at least 2")
    if os.name != "nt":
        raise PolicyError("owner acceptance is Windows-only")
    root = Path(__file__).resolve().parents[1]
    if str(root).casefold() != EXPECTED_ROOT.casefold():
        raise PolicyError("owner acceptance allowed only at D:\\UCIE")
    python = root / ".venv" / "Scripts" / "python.exe"
    if not python.is_file() or not os.path.samefile(sys.executable, python):
        raise PolicyError("run only with the existing D:\\UCIE virtualenv Python")
    private = root / ".build_keys" / "production" / "private_production.pem"
    trust = root / ".build_keys" / "production" / "public_production.pem"
    first = root / "build" / "UCIE_First_Owner_Risk_Public_v1.zip"
    output = root / "build" / f"UCIE_Two_Rule_Owner_Manual_Serial_{args.serial}.zip"
    scan_script = root / "scripts" / "ucie_signed_two_rule_owner_scan.ps1"
    for file in (private, trust, first, scan_script):
        if file.is_symlink() or not file.is_file():
            raise PolicyError("required local owner input missing or unsafe")
    if output.exists() or output.is_symlink():
        raise PolicyError("refuse existing two-rule release; never overwrite")

    if git(root, "remote", "get-url", "origin") not in ORIGINS:
        raise PolicyError("unexpected Git origin")
    if git(root, "branch", "--show-current") != "main":
        raise PolicyError("requires clean local main")
    sha = git(root, "rev-parse", "HEAD")
    if len(sha) != 40 or not all(x in "0123456789abcdef" for x in sha):
        raise PolicyError("invalid local main SHA")
    if git(root, "status", "--porcelain"):
        raise PolicyError("dirty UCIE worktree; do not auto-modify")
    legacy = verify_owner_risk_release(first, trust, min_serial=1)
    if (
        legacy.get("result") != "OWNER_RISK_ACCEPTED_PUBLIC_RULEPACK_VERIFIED"
        or legacy.get("rule_id") != RULE_IDS[0]
        or legacy.get("serial") != 1
        or legacy.get("owner_signature") != "VALID"
        or legacy.get("scope") != "PUBLIC_ONLY_MANUAL_STATIC_SCAN"
    ):
        raise PolicyError("first owner release identity mismatch")
    url = f"https://api.github.com/repos/{REPO}/actions/runs?branch=main&per_page=10"
    run_id = select_exact_ci(_public_json(url), sha)
    qa = validate_live_automated_qa(run_id)
    second = _postfix_ci()
    if qa["head_sha"] != sha or second["run_id"] != SECOND_RUN:
        raise PolicyError("main or pinned post-fix CI does not match")
    print(f"PRE-FLIGHT PASS: clean main={sha}, CI run={run_id}, pinned fix CI={SECOND_RUN}")
    consent, risk, second_risk = owner_input()

    # This is the ONLY production signing call. It itself re-verifies live CI
    # and clean main, and refuses duplicate target paths.
    publish_two_rule_owner_release(
        root, private, output, run_id=run_id, serial=args.serial,
        confirmation=consent, risk_acceptance=risk,
        second_risk_acceptance=second_risk,
    )
    accepted = verify_two_rule_owner_release(output, trust, min_serial=args.serial)
    if (
        accepted.get("result") != "OWNER_RISK_TWO_RULE_PUBLIC_PACK_VERIFIED"
        or accepted.get("rule_ids") != RULE_IDS
        or accepted.get("serial") != args.serial
        or accepted.get("owner_signature") != "VALID"
        or accepted.get("release_version_coverage_proven") is not False
        or accepted.get("auto_apply") is not False
        or accepted.get("scope") != "PUBLIC_ONLY_MANUAL_STATIC_SCAN"
    ):
        raise PolicyError("new owner-signed pack receiver verification failed")
    positive = (
        "python -I -X disable_remote_debug -\n"
        "Resolve-Path '.directory\\*.txt' -Relative\n"
    )
    negative = (
        "python -I -X disable-remote-debug -\n"
        "Resolve-Path '.directory\\*.txt' -ErrorAction Stop\n"
    )
    positive_result = synthetic_scan(
        scan_script, output, trust, python, positive, args.serial)
    negative_result = synthetic_scan(
        scan_script, output, trust, python, negative, args.serial)
    if (
        positive_result.get("finding_count") != 2
        or [x["rule_id"] for x in positive_result.get("findings", [])] != RULE_IDS
        or negative_result.get("finding_count") != 0
        or negative_result.get("findings") != []
    ):
        raise PolicyError("two-rule synthetic smoke test failed")
    if verify_owner_risk_release(first, trust, min_serial=1).get(
        "result") != "OWNER_RISK_ACCEPTED_PUBLIC_RULEPACK_VERIFIED":
        raise PolicyError("first release regression")
    print(json.dumps({
        "status": "UCIE_TWO_RULE_OWNER_LOCAL_PASS",
        "source_commit_sha": sha,
        "main_ci_run_id": run_id,
        "pinned_postfix_ci_run_id": SECOND_RUN,
        "pack_path": str(output), "pack_serial": args.serial, "rule_count": 2,
        "synthetic_positive_findings": 2, "synthetic_negative_findings": 0,
        "old_release_still_verified": True,
        "approval": "EXPLICIT_OWNER_ACCEPTANCE_ON_PC",
        "public_only_manual": True, "auto_fix": False,
        "automatic_distribution": False, "private_project_scanned": False,
        "released_version_fix_coverage_proven": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PolicyError, OSError, ValueError, subprocess.SubprocessError,
            EOFError, KeyboardInterrupt) as exc:
        # A signature may already exist on disk when a later smoke-test
        # fails; NEVER call it PASS or silently delete it.
        print("UCIE_TWO_RULE_OWNER_LOCAL_NO_GO: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
