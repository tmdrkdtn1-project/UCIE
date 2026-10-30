"""One-shot pinned Windows x64 PowerShell 7.6.6 release behavior observation.

CI-only probe of APPROVED PUBLIC PowerShell/PowerShell official release ZIP.
No host installation, user-worktree interaction, external scripts, secrets,
or production approval. Reuses the existing UCIE-owned synthetic dotpath probe.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
import zipfile
from urllib.parse import urlparse
from urllib.request import build_opener, Request

from runtime_powershell_766_official_release import SafeRedirects, ALLOW_HOSTS

ARCHIVE_NAME = "PowerShell-7.6.6-win-x64.zip"
SOURCE_URL = (
    "https://github.com/PowerShell/PowerShell/releases/download/v7.6.6/"
    + ARCHIVE_NAME
)
# Public upstream PowerShell/PowerShell v7.6.6 release's SHA-256.
ARCHIVE_SHA256 = "02fe458be20493fbdf43f61ea20610b811ee6c738ab1676c61b9cfcd1a33c860"
UPSTREAM_MERGE = "373f6a7b7972a0a4b73bfd9737a0d768d28b347e"
UPSTREAM_TAG_COMMIT = "f260eb9c31ec72c5282f98e5ea24d9be4f8d7536"
MAX_ARCHIVE_BYTES = 115_000_000
MAX_UNCOMPRESSED_BYTES = 900_000_000
MAX_MEMBERS = 6500


def fetch_exact_official_archive(dest: Path) -> tuple[str, int]:
    if dest.exists() or dest.is_symlink():
        raise RuntimeError("release archive destination already exists")
    opener = build_opener(SafeRedirects)
    request = Request(SOURCE_URL, headers={"User-Agent": "UCIE-release-runtime-CI"})
    digest = hashlib.sha256()
    count = 0
    with opener.open(request, timeout=60) as resp:
        target = urlparse(resp.geturl())
        if target.scheme != "https" or target.hostname not in ALLOW_HOSTS:
            raise RuntimeError("release download redirected off approved GitHub hosts")
        with dest.open("xb") as file:
            while True:
                data = resp.read(1024 * 1024)
                if not data:
                    break
                count += len(data)
                if count > MAX_ARCHIVE_BYTES:
                    raise RuntimeError("release archive exceeds download cap")
                digest.update(data)
                file.write(data)
    if not 1_000_000 < count <= MAX_ARCHIVE_BYTES:
        raise RuntimeError("invalid release archive size")
    sha = digest.hexdigest()
    if sha != ARCHIVE_SHA256:
        raise RuntimeError("official published release archive SHA256 mismatch")
    return sha, count


def extract_bounded_zip(archive: Path, dest: Path) -> Path:
    with zipfile.ZipFile(archive) as zf:
        info = zf.infolist()
        if not 1 <= len(info) <= MAX_MEMBERS:
            raise RuntimeError("unexpected archive entries")
        total = 0
        seen = set()
        for entry in info:
            raw = entry.filename
            parts = raw.rstrip("/").split("/")
            posix = PurePosixPath(raw)
            mode = (entry.external_attr >> 16) & 0o170000
            if (not raw or posix.is_absolute() or "\\" in raw
                    or ":" in raw or any(p in ("", ".", "..") for p in parts)
                    or mode == stat.S_IFLNK
                    or (mode not in (0, stat.S_IFREG, stat.S_IFDIR))
                    or entry.flag_bits & 1
                    or entry.file_size < 0 or entry.file_size > 350_000_000):
                raise RuntimeError("unsafe release archive entry")
            lowered = raw.rstrip("/").casefold()
            if lowered in seen:
                raise RuntimeError("duplicate release archive entry")
            seen.add(lowered)
            total += entry.file_size
        if total > MAX_UNCOMPRESSED_BYTES:
            raise RuntimeError("release archive exceeds expansion cap")
        zf.extractall(dest)
    binary = dest / "pwsh.exe"
    if not binary.is_file() or binary.is_symlink():
        raise RuntimeError("missing release pwsh.exe")
    return binary


def execute_ucie_owned_probe(binary: Path, scratch: Path) -> dict:
    script = Path(__file__).resolve().with_name("runtime_powershell_dotpath_probe.ps1")
    if script.is_symlink() or not script.is_file():
        raise RuntimeError("UCIE-only test source unavailable")
    profile = scratch / "isolated-profile"
    profile.mkdir()
    # Never pass runner GitHub token, workflow credentials, proxy or owner data
    # to the untrusted-but-SHA-checked public release executable.
    environment = {
        key: os.environ[key] for key in
        ("SystemRoot", "WINDIR") if key in os.environ
    }
    root = environment.get("SystemRoot", "C:\\Windows")
    environment.update({
        "PATH": root + "\\System32;" + root,
        "TEMP": str(scratch),
        "TMP": str(scratch),
        "USERPROFILE": str(profile),
        "APPDATA": str(profile / "AppData" / "Roaming"),
        "LOCALAPPDATA": str(profile / "AppData" / "Local"),
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "POWERSHELL_TELEMETRY_OPTOUT": "1",
        "POWERSHELL_UPDATECHECK": "Off",
        "PSModulePath": str(binary.parent / "Modules"),
    })
    proc = subprocess.run([
        str(binary), "-NoProfile", "-NonInteractive", "-NoLogo",
        "-File", str(script),
    ], cwd=scratch, env=environment, text=True, capture_output=True,
       timeout=100, check=False)
    prefix = "UCIE_PS_DOTPATH_RUNTIME_EVIDENCE="
    lines = [x.removeprefix(prefix) for x in proc.stdout.splitlines()
             if x.startswith(prefix)]
    if proc.returncode != 0 or len(lines) != 1:
        raise RuntimeError("release binary failed isolated UCIE probe: "
                           + proc.stderr[-1000:])
    try:
        result = json.loads(lines[0])
    except ValueError as exc:
        raise RuntimeError("invalid JSON behavior receipt") from exc
    if (result.get("schema") != "UCIE_PS_DOTPATH_RUNTIME_EVIDENCE_V1"
            or result.get("runtime_version") != "7.6.6"
            or result.get("source") != "PowerShell/PowerShell"
            or result.get("pinned_upstream_merge_sha") != UPSTREAM_MERGE
            or result.get("native_behavior") not in (
                "DOT_PREFIX_BUG_OBSERVED_ON_RUNNER",
                "FIXED_LIKE_BEHAVIOR_NOT_UPSTREAM_COMMIT_PROOF",
                "MIXED_NATIVE_BEHAVIOR_REVIEW_REQUIRED",
            )
            or result.get("baseline_case_passed") is not True
            or result.get("guarded_cases_passed") is not True
            or result.get("production_approved") is not False
            or result.get("auto_promoted") is not False
            or len(result.get("observations", [])) != 3
            or sorted(x["case_id"] for x in result["observations"]) !=
               ["..directory", ".directory", "directory"]):
        raise RuntimeError("release behavior receipt rejected")
    return result


def main() -> None:
    if (sys.platform != "win32"
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_OS") != "Windows"
            or sys.version_info[:2] != (3, 15)):
        raise RuntimeError("disposable Windows GitHub CI Python 3.15 only")
    with tempfile.TemporaryDirectory(prefix="ucie-ps766-win-") as temp:
        root = Path(temp)
        archive = root / ARCHIVE_NAME
        sha, downloaded = fetch_exact_official_archive(archive)
        dest = root / "isolated-release"
        dest.mkdir()
        binary = extract_bounded_zip(archive, dest)
        observation = execute_ucie_owned_probe(binary, root)
        report = {
            "schema": "UCIE_PS_766_PINNED_RELEASE_WINDOWS_BINARY_DOTPATH_V1",
            "status": "OFFICIAL_WINDOWS_RELEASE_RUNTIME_OBSERVED_NO_GO",
            "official_public_artifact": SOURCE_URL,
            "official_tag_commit": UPSTREAM_TAG_COMMIT,
            "published_archive_sha256": ARCHIVE_SHA256,
            "archive_sha256": sha,
            "published_hash_matched": sha == ARCHIVE_SHA256,
            "archive_bytes": downloaded,
            "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "runtime_version": observation["runtime_version"],
            "runtime_platform": observation["platform"],
            "target": "windows-x64",
            "native_behavior": observation["native_behavior"],
            "dot_prefix_cases_matching_expected":
                observation["dot_prefix_cases_matching_expected"],
            "baseline_case_passed": observation["baseline_case_passed"],
            "guarded_cases_passed": observation["guarded_cases_passed"],
            "observations": observation["observations"],
            "release_binary_executed": True,
            "other_windows_architectures_tested": False,
            "all_platforms_verified": False,
            "equivalent_backports_excluded": False,
            "independent_qa_completed": False,
            "package_export_approved": False,
            "production_approved": False,
            "auto_promoted": False,
            "operating_database_writes": 0,
        }
        print("UCIE_PS_766_OFFICIAL_WINDOWS_RUNTIME=" +
              json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("UCIE_PS_766_WINDOWS_RELEASE_RUNTIME_NO_GO: " + str(exc),
              file=sys.stderr)
        sys.exit(1)
