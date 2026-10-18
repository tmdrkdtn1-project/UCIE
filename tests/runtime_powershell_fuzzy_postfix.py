"""Run the exact pinned official PowerShell post-fix CI artifact in disposable Linux.

The build is untrusted input: extraction inherits UCIE's existing bounded
ZIP checks; execution is CI-only with a minimal environment, an inert UCIE
test fixture and timeout. This DOES NOT approve a third rule.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import os
import subprocess
import sys

from runtime_powershell_dotpath_postfix import _extract_checked

UPSTREAM_REPO = "PowerShell/PowerShell"
UPSTREAM_MERGE = "bd8cb01a7d5b86129c45eaa14ab5830a63b1283f"
BUILT_AT_COMMIT = "373f6a7b7972a0a4b73bfd9737a0d768d28b347e"
UPSTREAM_RUN = 37965704591
ARTIFACT_ID = 11634185748


def main() -> int:
    if len(sys.argv) != 2 or sys.platform != "linux":
        raise RuntimeError("disposable Linux CI only")
    root = Path(sys.argv[1]).resolve(strict=True)
    zip_path = root / "build.zip"
    meta = root / "psoptions.json"
    if (meta.is_symlink() or not meta.is_file()
            or meta.stat().st_size > 65536
            or zip_path.is_symlink()):
        raise RuntimeError("untrusted upstream build package")
    if not isinstance(json.loads(meta.read_bytes()), dict):
        raise RuntimeError("invalid upstream build metadata")
    output = root / "fuzzy_patched_extracted"
    output.mkdir(exist_ok=False)
    _extract_checked(zip_path, output)
    exe = [p for p in output.rglob("pwsh")
           if p.is_file() and not p.is_symlink()]
    if len(exe) != 1:
        raise RuntimeError("upstream archive must contain exactly one pwsh")
    binary = exe[0]
    binary.chmod(0o700)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(output),
        "LANG": "C.UTF-8",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "POWERSHELL_TELEMETRY_OPTOUT": "1",
        "GITHUB_SHA": os.environ.get("GITHUB_SHA", ""),
    }
    script = Path(__file__).with_name("runtime_powershell_fuzzy_probe.ps1")
    run = subprocess.run([
        str(binary), "-NoProfile", "-NonInteractive", "-NoLogo",
        "-File", str(script),
    ], env=env, cwd=output, capture_output=True, text=True,
        timeout=75, check=False)
    lines = [
        x.partition("UCIE_PS_FUZZY_RUNTIME_EVIDENCE=")[2]
        for x in run.stdout.splitlines()
        if x.startswith("UCIE_PS_FUZZY_RUNTIME_EVIDENCE=")
    ]
    if run.returncode != 0 or len(lines) != 1:
        raise RuntimeError("patched executable could not finish synthetic fuzzy probe: "
                           + run.stderr[-1200:])
    observed = json.loads(lines[0])
    if (observed.get("schema") != "UCIE_PS_FUZZY_RUNTIME_EVIDENCE_V1"
            or observed.get("pinned_merge_sha") != UPSTREAM_MERGE
            or observed.get("source") != UPSTREAM_REPO
            or observed.get("native_behavior") != "FIXED_LIKE_DUPLICATE_FILTERING"
            or observed.get("exactly_one_result_with_score_one") is not True
            or observed.get("fuzzy_result_count") != 1
            or observed.get("distinct_identity_count") != 1
            or observed.get("owner_approved") is not False):
        raise RuntimeError("post-fix fuzzy duplicate filtering was NOT observed")
    print("UCIE_PS_FUZZY_PINNED_POSTFIX=" + json.dumps({
        "schema": "UCIE_PS_FUZZY_PINNED_POSTFIX_V1",
        "status": "FIXED_BEHAVIOR_OBSERVED_ON_PINNED_DEVELOPMENT_BUILD",
        "source": UPSTREAM_REPO,
        "upstream_merge_sha": UPSTREAM_MERGE,
        "upstream_build_commit_sha": BUILT_AT_COMMIT,
        "upstream_ci_run": UPSTREAM_RUN,
        "upstream_artifact_id": ARTIFACT_ID,
        "build_zip_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "executed_pwsh_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "runtime_version": observed["runtime_version"],
        "fuzzy_results": observed["fuzzy_result_count"],
        "owner_approved": False,
        "released_version_coverage_proven": False,
        "production_approved": False,
        "auto_promoted": False,
        "private_project_scanned": False,
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("UCIE_THIRD_RULE_POSTFIX_NO_GO=" + str(exc), file=sys.stderr)
        raise SystemExit(1)
