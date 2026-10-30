"""One-shot pinned PowerShell 7.6.6 *release binary* behavioral probe.

ONLY execute on disposable GitHub Linux runner; not UCIE's owner Windows host.
Downloads one approved public PowerShell release file, enforces the official
release page's pinned SHA-256 before bounded safe extraction, and executes
the existing UCIE-authored synthetic dot-path probe under restricted env.

All external bytes are UNTRUSTED before the digest check. Passing the check
does not assert a signature, independent QA, absent backports, or that Windows
PowerShell binaries have the same behavior.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile
from urllib.parse import urlparse
from urllib.request import build_opener, HTTPRedirectHandler, Request

VERSION = "7.6.6"
ARCHIVE = "powershell-7.6.6-linux-x64.tar.gz"
SOURCE = "https://github.com/PowerShell/PowerShell/releases/download/v7.6.6/" + ARCHIVE
# Official PowerShell/PowerShell v7.6.6 GitHub release asset's published SHA-256.
ARCHIVE_SHA256 = "ddbc4a2d113bbd46d283cfedcbcd117a70caefd7673f41f2b4e0000badf103bc"
RELEASE_TAG_COMMIT = "f260eb9c31ec72c5282f98e5ea24d9be4f8d7536"
UPSTREAM_PR = "https://github.com/PowerShell/PowerShell/pull/28087"
MAX_ARCHIVE_BYTES = 85_000_000
MAX_EXTRACTED_BYTES = 650_000_000
MAX_MEMBERS = 4500
ALLOW_HOSTS = frozenset({
    "github.com",
    "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
})


class SafeRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        if parsed.scheme != "https" or parsed.hostname not in ALLOW_HOSTS:
            raise RuntimeError("release download redirected off approved GitHub asset hosts")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_verified(destination: Path) -> tuple[str, int]:
    if destination.exists() or destination.is_symlink():
        raise RuntimeError("nonempty archive destination")
    opener = build_opener(SafeRedirects)
    digest = hashlib.sha256()
    total = 0
    request = Request(SOURCE, headers={"User-Agent": "UCIE-pinned-release-verifier"})
    with opener.open(request, timeout=55) as response:
        if response.geturl().split(":", 1)[0] != "https":
            raise RuntimeError("non-HTTPS release response")
        if urlparse(response.geturl()).hostname not in ALLOW_HOSTS:
            raise RuntimeError("release response from unapproved asset host")
        with destination.open("xb") as file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_ARCHIVE_BYTES:
                    raise RuntimeError("oversized upstream release archive")
                digest.update(chunk)
                file.write(chunk)
    if total < 1_000_000 or digest.hexdigest() != ARCHIVE_SHA256:
        raise RuntimeError("official published release archive digest MISMATCH")
    return digest.hexdigest(), total


def extract_checked(archive: Path, directory: Path) -> Path:
    with tarfile.open(archive, mode="r:gz") as tf:
        members = tf.getmembers()
        if not 1 <= len(members) <= MAX_MEMBERS:
            raise RuntimeError("upstream release archive member cap exceeded")
        if sum(max(0, x.size) for x in members) > MAX_EXTRACTED_BYTES:
            raise RuntimeError("upstream release archive expanded bytes cap exceeded")
        if any(not (x.isfile() or x.isdir() or x.issym() or x.islnk())
               or x.name.startswith("/") or ".." in Path(x.name).parts
               for x in members):
            raise RuntimeError("upstream release archive contains unsafe entries")
        # Python 3.15: data filter denies unsafe absolute links, escaping
        # paths and dangerous extraction metadata. No custom path bypass.
        tf.extractall(path=directory, filter="data")
    binary = directory / "pwsh"
    if not binary.is_file() or binary.is_symlink():
        raise RuntimeError("expected one regular PowerShell release executable")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    return binary


def verify_release_runtime(binary: Path, tempdir: Path) -> dict:
    source = Path(__file__).resolve().with_name("runtime_powershell_dotpath_probe.ps1")
    if source.is_symlink() or not source.is_file():
        raise RuntimeError("UCIE-owned PowerShell probe unavailable")
    home = tempdir / "home"
    home.mkdir()
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "POWERSHELL_TELEMETRY_OPTOUT": "1",
    }
    proc = subprocess.run(
        [str(binary), "-NoProfile", "-NonInteractive", "-NoLogo",
         "-File", str(source)],
        cwd=tempdir, env=env, text=True, capture_output=True,
        timeout=90, check=False,
    )
    prefix = "UCIE_PS_DOTPATH_RUNTIME_EVIDENCE="
    lines = [line.removeprefix(prefix) for line in proc.stdout.splitlines()
             if line.startswith(prefix)]
    if proc.returncode != 0 or len(lines) != 1:
        raise RuntimeError("pinned release runtime probe rejected: "
                           + proc.stderr[-900:])
    try:
        result = json.loads(lines[0])
    except ValueError as exc:
        raise RuntimeError("malformed pinned release runtime observation") from exc
    if (result.get("schema") != "UCIE_PS_DOTPATH_RUNTIME_EVIDENCE_V1"
            or result.get("runtime_version") != VERSION
            or result.get("source") != "PowerShell/PowerShell"
            or result.get("public_pr") != UPSTREAM_PR
            or result.get("pinned_upstream_merge_sha") !=
               "373f6a7b7972a0a4b73bfd9737a0d768d28b347e"
            or result.get("baseline_case_passed") is not True
            or result.get("guarded_cases_passed") is not True
            or result.get("production_approved") is not False
            or result.get("auto_promoted") is not False
            or result.get("native_behavior") not in (
                "DOT_PREFIX_BUG_OBSERVED_ON_RUNNER",
                "FIXED_LIKE_BEHAVIOR_NOT_UPSTREAM_COMMIT_PROOF",
                "MIXED_NATIVE_BEHAVIOR_REVIEW_REQUIRED",
            )
            or len(result.get("observations", [])) != 3
            or sorted(x["case_id"] for x in result["observations"]) !=
               [".directory", "..directory", "directory"]):
        raise RuntimeError("incorrect or incomplete release behavior observation")
    return result


def main() -> None:
    if (sys.platform != "linux"
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_OS") != "Linux"
            or sys.version_info[:2] != (3, 15)):
        raise RuntimeError("explicit ephemeral Linux GitHub CI Python 3.15 only")
    with tempfile.TemporaryDirectory(prefix="ucie-official-ps766-") as temp:
        td = Path(temp)
        archive_path = td / ARCHIVE
        digest, downloaded = download_verified(archive_path)
        extracted = td / "extracted"
        extracted.mkdir()
        binary = extract_checked(archive_path, extracted)
        observed = verify_release_runtime(binary, td)
        binary_sha = hashlib.sha256(binary.read_bytes()).hexdigest()
        report = {
            "schema": "UCIE_PS_766_PINNED_RELEASE_BINARY_DOTPATH_OBSERVATION_V1",
            "status": "PINNED_RELEASE_BEHAVIOR_OBSERVED_NOT_PRODUCTION_APPROVED",
            "official_public_artifact": SOURCE,
            "official_release_tag_commit": RELEASE_TAG_COMMIT,
            "archive_sha256": digest,
            "published_sha256_matched": digest == ARCHIVE_SHA256,
            "archive_bytes": downloaded,
            "binary_sha256": binary_sha,
            "verified_runtime_version": observed["runtime_version"],
            "actual_release_binary_executed": True,
            "runtime_platform": observed["platform"],
            "native_behavior": observed["native_behavior"],
            "dot_prefix_cases_matching_expected":
                observed["dot_prefix_cases_matching_expected"],
            "baseline_case_passed": observed["baseline_case_passed"],
            "guarded_cases_passed": observed["guarded_cases_passed"],
            "observations": observed["observations"],
            "examined_os": "linux-x64",
            "windows_release_binary_tested": False,
            "same_behavior_on_all_platforms_verified": False,
            "upstream_implementation_backport_absent_verified": False,
            "independent_qa_completed": False,
            "source_copyright_relicensing_done": False,
            "production_approved": False,
            "auto_promoted": False,
            "operating_database_writes": 0,
        }
        print("UCIE_PS_766_OFFICIAL_RELEASE_RUNTIME=" +
              json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("UCIE_PS_766_RELEASE_RUNTIME_NO_GO: " + str(exc),
              file=sys.stderr)
        sys.exit(1)
