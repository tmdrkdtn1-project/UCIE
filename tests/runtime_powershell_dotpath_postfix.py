"""One-shot patched PowerShell CI-artifact runtime check on disposable Linux.

Only a fixed public PowerShell/PowerShell upstream Actions artifact is accepted
by the calling workflow. This code never downloads or runs private project
content. The upstream binary is UNTRUSTED; run only on ephemeral public CI,
never the owner host, miner, scheduler, or production runtime.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import zipfile

SOURCE = "PowerShell/PowerShell"
MERGE_SHA = "373f6a7b7972a0a4b73bfd9737a0d768d28b347e"
BUILD_RUN = 37965704591
ARTIFACT_ID = 11634185748
MAX_INNER_ARCHIVE_BYTES = 120_000_000
MAX_EXPANDED_BYTES = 650_000_000
MAX_ENTRIES = 3000


def _extract_checked(archive: Path, destination: Path) -> None:
    if (archive.is_symlink() or not archive.is_file()
            or not 0 < archive.stat().st_size <= MAX_INNER_ARCHIVE_BYTES):
        raise RuntimeError("missing or unsafe upstream build.zip")
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        if not 1 <= len(infos) <= MAX_ENTRIES:
            raise RuntimeError("unexpected upstream build entry count")
        seen = set()
        total = 0
        for info in infos:
            item = PurePosixPath(info.filename)
            components = item.parts
            mode = (info.external_attr >> 16) & 0o170000
            if (not components or item.is_absolute() or
                    any(x in ("", ".", "..") for x in components) or
                    "\\" in info.filename or ":" in info.filename or
                    mode == stat.S_IFLNK or info.flag_bits & 1 or
                    info.file_size < 0 or info.file_size > 200_000_000):
                raise RuntimeError("unsafe upstream build archive path")
            key = info.filename.rstrip("/").casefold()
            if key in seen:
                raise RuntimeError("duplicate upstream build archive entry")
            seen.add(key)
            total += info.file_size
        if total > MAX_EXPANDED_BYTES:
            raise RuntimeError("oversized upstream build archive")
        z.extractall(destination)


def main() -> int:
    if len(sys.argv) != 2 or sys.platform != "linux":
        raise RuntimeError("disposable Linux CI only")
    artifact_dir = Path(sys.argv[1]).resolve(strict=True)
    source_zip = artifact_dir / "build.zip"
    options = artifact_dir / "psoptions.json"
    if (options.is_symlink() or not options.is_file()
            or options.stat().st_size > 65536
            or source_zip.is_symlink()):
        raise RuntimeError("missing upstream official CI build manifest")
    # This is only an artifact metadata consistency check, NOT a signature.
    raw_options = options.read_bytes()
    try:
        parsed_options = json.loads(raw_options)
    except (UnicodeError, ValueError) as exc:
        raise RuntimeError("unrecognized upstream build metadata") from exc
    if not isinstance(parsed_options, dict):
        raise RuntimeError("invalid upstream CI build options")

    dest = artifact_dir / "isolated"
    dest.mkdir(exist_ok=False)
    _extract_checked(source_zip, dest)
    candidates = [p for p in dest.rglob("pwsh")
                  if p.is_file() and not p.is_symlink()]
    if len(candidates) != 1:
        raise RuntimeError("expected exactly one upstream Linux pwsh binary")
    binary = candidates[0]
    binary.chmod(0o700)

    # Preserve only necessary runtime settings; no CI token, proxy, user data,
    # credentials or access to the owner machine are passed to the process.
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(dest),
        "LANG": "C.UTF-8",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "POWERSHELL_TELEMETRY_OPTOUT": "1",
        "GITHUB_SHA": os.environ.get("GITHUB_SHA", ""),
    }
    test = Path(__file__).with_name("runtime_powershell_dotpath_probe.ps1")
    proc = subprocess.run(
        [str(binary), "-NoProfile", "-NonInteractive", "-NoLogo",
         "-File", str(test)],
        cwd=str(dest), env=env, text=True, capture_output=True,
        timeout=60, check=False,
    )
    lines = [line.split("UCIE_PS_DOTPATH_RUNTIME_EVIDENCE=", 1)[1]
             for line in proc.stdout.splitlines()
             if line.startswith("UCIE_PS_DOTPATH_RUNTIME_EVIDENCE=")]
    if proc.returncode or len(lines) != 1:
        raise RuntimeError("patched CI binary did not complete the bounded probe")
    try:
        observed = json.loads(lines[0])
    except ValueError as exc:
        raise RuntimeError("non-JSON upstream runtime result") from exc
    if (observed.get("schema") != "UCIE_PS_DOTPATH_RUNTIME_EVIDENCE_V1"
            or observed.get("source") != SOURCE
            or observed.get("pinned_upstream_merge_sha") != MERGE_SHA
            or observed.get("rule_id") != "PS_RESOLVE_PATH_DOT_PREFIX"
            or observed.get("native_behavior") !=
               "FIXED_LIKE_BEHAVIOR_NOT_UPSTREAM_COMMIT_PROOF"
            or observed.get("dot_prefix_cases_matching_expected") != 2
            or observed.get("baseline_case_passed") is not True
            or observed.get("guarded_cases_passed") is not True
            or observed.get("independent_before_after_verified") is not False
            or observed.get("production_approved") is not False):
        raise RuntimeError("patched CI runtime behavior is not verified")
    print("UCIE_PS_DOTPATH_POSTFIX_CI=" + json.dumps({
        "schema": "UCIE_PS_DOTPATH_POSTFIX_CI_V1",
        "status": "PATCHED_DEVELOPMENT_BUILD_BEHAVIOR_OBSERVED",
        "upstream_repository": SOURCE,
        "upstream_merge_sha": MERGE_SHA,
        "upstream_ci_run": BUILD_RUN,
        "upstream_artifact_id": ARTIFACT_ID,
        "artifact_build_zip_sha256": hashlib.sha256(source_zip.read_bytes()).hexdigest(),
        "actual_pwsh_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "pwsh_version": observed["runtime_version"],
        "dot_prefix_cases_matched": 2,
        "platform": observed["platform"],
        "actual_patched_binary_executed": True,
        "release_tag_inclusion_verified": False,
        "independent_before_after_revision_builds_verified": False,
        "license_review_approved": False,
        "production_approved": False,
        "rule_auto_promoted": False,
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile,
            subprocess.TimeoutExpired) as exc:
        print("UCIE_PATCHED_BUILD_VERIFICATION_NO_GO: " + str(exc),
              file=sys.stderr)
        sys.exit(1)
