"""UCIE W17: one owner-approved staged Git + official wheel + W14 venv action.

Default is NO-HOST contract. An explicit interactive owner operation only
updates D:/UCIE_PROJECT/UCIE (a new W15 Git stage), fetches exactly four
fixed Python packages from official PyPI, verifies each local wheel's
SHA-256 and length against the official PyPI release JSON, then calls the
existing W14 offline venv installer. Public-miner scope is unchanged.

No D:/UCIE, SQLite, C40, scheduler, tunnel or owner private snapshot action.
No auto-retry, auto-clean, rollback of unrelated Git paths, or release.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import urlopen

SCHEMA = "UCIE_W17_OWNER_NEWROOT_VENV_ONCE_V01"
APPROVAL = "AUTHORIZE_UCIE_W17_OFFICIAL_PYPI_WHEELS_AND_ISOLATED_VENV"
ROOT = Path(r"D:\UCIE_PROJECT\UCIE")
ARCHIVE = Path(r"D:\UCIE_PROJECT\ARCHIVE")
PENDING = ARCHIVE / "UCIE_W17_PYPI_WHEELS_PENDING_V01"
WHEELHOUSE = ARCHIVE / "UCIE_W14_OWNER_APPROVED_WHEELS"
W14_RECEIPT = ARCHIVE / "UCIE_W14_OFFLINE_RUNTIME_RECEIPT_V01.json"
VENV = ROOT / ".venv"
W14 = ROOT / "scripts" / "ucie_owner_offline_runtime_prepare_v01.ps1"
W16_ANCESTOR = "07aa0970f1ef25dd5a8fbd76d2236e9783ae836c"
REPO = "https://github.com/tmdrkdtn1-project/UCIE.git"
SCRIPT_IN_GIT = "scripts/ucie_owner_newroot_venv_once_v01.py"
REQUIREMENTS = (
    "cryptography==50.0.2", "setuptools==80.9.0",
    "cffi==2.1.1", "pycparser==2.23",
)
ALLOWED = {
    "cryptography": "50.0.2", "setuptools": "80.9.0",
    "cffi": "2.1.1", "pycparser": "2.23",
}
MAX_PACKAGE_BYTES = 15_000_000
MAX_METADATA_BYTES = 3_000_000
HEX40 = re.compile(r"[a-f0-9]{40}\Z")


class OwnerPrepError(ValueError):
    pass


def direct(path: Path, directory: bool | None = None) -> bool:
    try:
        meta = path.lstat()
        if directory is True and not stat.S_ISDIR(meta.st_mode):
            return False
        if directory is False and not stat.S_ISREG(meta.st_mode):
            return False
        for segment in (path, *path.parents):
            s = segment.lstat()
            if stat.S_ISLNK(s.st_mode) or (
                    getattr(s, "st_file_attributes", 0) & 0x400):
                return False
        return True
    except OSError:
        return False


def private_owner_archive() -> bool:
    command = (
        "$ErrorActionPreference='Stop';"
        "$acl=Get-Acl -LiteralPath 'D:\\UCIE_PROJECT\\ARCHIVE';"
        "$owner=$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value;"
        "$self=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value;"
        "if(-not $acl.AreAccessRulesProtected -or $owner -ne $self){exit 3};"
        "exit 0"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=25, check=False)
    return result.returncode == 0


def git(*args: str) -> str:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0",
           "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"}
    p = subprocess.run(
        ["git", "-c", "core.hooksPath=NUL", "-C", str(ROOT), *args],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=90, check=False)
    if p.returncode:
        raise OwnerPrepError("UCIE_W17_GIT_OPERATION_FAILED")
    return p.stdout.decode("utf-8", "strict").strip()


def _git_assert_clean_main() -> str:
    if git("branch", "--show-current") != "main":
        raise OwnerPrepError("UCIE_W17_EXPECTED_MAIN_BRANCH")
    if git("remote", "get-url", "origin") != REPO:
        raise OwnerPrepError("UCIE_W17_UNAPPROVED_REPO_ORIGIN")
    if Path(git("rev-parse", "--show-toplevel")).resolve() != ROOT.resolve():
        raise OwnerPrepError("UCIE_W17_UNEXPECTED_GIT_ROOT")
    if git("status", "--porcelain=v1", "--untracked-files=all"):
        raise OwnerPrepError("UCIE_W17_GIT_STAGE_NOT_CLEAN")
    return git("rev-parse", "HEAD")


def _pypi_release_metadata(name: str, version: str) -> dict:
    # Immutable, fixed first-party package distribution origin. This is an
    # owner opt-in acquisition, NOT an expansion of the UCIE public miner.
    if ALLOWED.get(name) != version:
        raise OwnerPrepError("UCIE_W17_UNAPPROVED_WHEEL_RELEASE")
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    with urlopen(url, timeout=18) as response:
        if urlsplit(response.geturl()).hostname != "pypi.org":
            raise OwnerPrepError("UCIE_W17_PYPI_JSON_REDIRECT_DENIED")
        raw = response.read(MAX_METADATA_BYTES + 1)
    if len(raw) > MAX_METADATA_BYTES:
        raise OwnerPrepError("UCIE_W17_PYPI_METADATA_TOO_LARGE")
    result = json.loads(raw)
    if result.get("info", {}).get("name", "").lower().replace("-", "_") != name:
        raise OwnerPrepError("UCIE_W17_PYPI_PACKAGE_IDENTITY_MISMATCH")
    if result.get("info", {}).get("version") != version:
        raise OwnerPrepError("UCIE_W17_PYPI_VERSION_MISMATCH")
    return result


def verify_downloaded_wheels(path: Path) -> list[dict]:
    """Verify exact allowlist, bounded wheel contents, PyPI hashes and size."""
    files = sorted(path.iterdir())
    if len(files) != len(ALLOWED):
        raise OwnerPrepError("UCIE_W17_WHEEL_COUNT_NOT_FOUR")
    seen: set[str] = set()
    receipt: list[dict] = []
    for wheel in files:
        if not direct(wheel, directory=False) or not wheel.name.endswith(".whl"):
            raise OwnerPrepError("UCIE_W17_NONWHEEL_OR_INDIRECT_DOWNLOAD")
        parts = wheel.name.split("-")
        if len(parts) < 5:
            raise OwnerPrepError("UCIE_W17_INVALID_WHEEL_FILENAME")
        name, version = parts[0].lower(), parts[1]
        if (ALLOWED.get(name) != version or name in seen
                or not 0 < wheel.stat().st_size <= MAX_PACKAGE_BYTES):
            raise OwnerPrepError("UCIE_W17_UNAPPROVED_PACKAGE_VERSION_OR_SIZE")
        seen.add(name)
        metadata = _pypi_release_metadata(name, version)
        matches = [
            item for item in metadata.get("urls", [])
            if item.get("filename") == wheel.name
            and item.get("packagetype") == "bdist_wheel"
            and not item.get("yanked", False)
        ]
        if len(matches) != 1:
            raise OwnerPrepError("UCIE_W17_PYPI_WHEEL_NOT_LISTED")
        official = matches[0]
        digest = sha256()
        with wheel.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        value = digest.hexdigest()
        if (official.get("digests", {}).get("sha256") != value
                or official.get("size") != wheel.stat().st_size):
            raise OwnerPrepError("UCIE_W17_PYPI_WHEEL_CHECKSUM_MISMATCH")
        receipt.append({
            "name": wheel.name, "sha256": value,
            "bytes": wheel.stat().st_size,
        })
    if seen != set(ALLOWED):
        raise OwnerPrepError("UCIE_W17_WHEEL_ALLOWLIST_INCOMPLETE")
    return receipt


def _subprocess_prepare(target_commit: str) -> dict:
    if (os.name != "nt" or not sys.stdin.isatty()
            or sys.version_info[:2] != (3, 15)
            or sys.prefix != sys.base_prefix
            or not HEX40.fullmatch(target_commit)):
        raise OwnerPrepError("UCIE_W17_INTERACTIVE_BASE_PY315_AND_COMMIT_REQUIRED")
    if (not direct(ROOT, True) or not direct(ROOT / ".git", True)
            or not direct(ARCHIVE, True) or not private_owner_archive()
            or not direct(W14, False)):
        raise OwnerPrepError("UCIE_W17_CANONICAL_STAGE_OR_ARCHIVE_INVALID")
    if any(p.exists() or p.is_symlink() for p in
           (PENDING, WHEELHOUSE, W14_RECEIPT, VENV)):
        raise OwnerPrepError("UCIE_W17_PREEXISTING_INSTALL_STATE_NO_RETRY")
    original_head = _git_assert_clean_main()
    # Only the newly created W15 source checkout can fast-forward.
    git("fetch", "--no-tags", "origin", "main")
    git("merge-base", "--is-ancestor", original_head, target_commit)
    git("merge-base", "--is-ancestor", W16_ANCESTOR, target_commit)
    content = subprocess.run(
        ["git", "-C", str(ROOT), "show",
         f"{target_commit}:{SCRIPT_IN_GIT}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=15, check=False,
    )
    if content.returncode or content.stdout != Path(__file__).read_bytes():
        raise OwnerPrepError("UCIE_W17_IMMUTABLE_SCRIPT_COMMIT_MISMATCH")
    git("merge", "--ff-only", target_commit)
    if _git_assert_clean_main() != target_commit:
        raise OwnerPrepError("UCIE_W17_POST_FF_ONLY_HEAD_MISMATCH")
    # No Python packages are imported from the downloaded material. Pip only
    # fetches wheels to private quarantine. No sdist or backend build is run.
    PENDING.mkdir(mode=0o700)
    p = subprocess.run(
        [sys.executable, "-I", "-B", "-m", "pip", "--isolated", "download",
         "--no-cache-dir", "--disable-pip-version-check",
         "--only-binary=:all:", "--index-url", "https://pypi.org/simple",
         "--dest", str(PENDING), *REQUIREMENTS],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=240, check=False,
    )
    if p.returncode:
        raise OwnerPrepError("UCIE_W17_PYPI_WHEEL_DOWNLOAD_HOLD")
    wheels = verify_downloaded_wheels(PENDING)
    manifest = {
        "schema": "UCIE_W14_WHEEL_SHA256_V01",
        "wheels": wheels,
        "package_source": "OWNER_OPT_IN_OFFICIAL_PYPI_VERIFIED_SHA256",
        "installer_auto_promotion_authorized": False,
    }
    (PENDING / "UCIE_W14_WHEEL_SHA256_V01.json").write_text(
        json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    # After hash validation, move the whole wheelhouse into its final
    # ACL-protected location. Never overwrite or delete an existing one.
    PENDING.rename(WHEELHOUSE)
    run = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(W14), "-Prepare",
         "-OwnerApproval", "AUTHORIZE_UCIE_W14_OFFLINE_VENV_PREPARATION"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=300, check=False, text=True, encoding="utf-8", errors="replace",
    )
    if run.returncode:
        # Only first-party bounded status tokens are exposed. Do not print
        # stderr, paths, package filenames or private archive details.
        codes = re.findall(r"UCIE_W14_[A-Z0-9_]{3,90}", run.stderr)
        code = codes[-1] if codes else "UCIE_W17_W14_VENV_PREPARATION_FAILED_HOLD"
        raise OwnerPrepError(code)
    try:
        w14 = json.loads(run.stdout.strip())
    except (ValueError, TypeError) as exc:
        raise OwnerPrepError("UCIE_W17_W14_SUCCESS_RECEIPT_UNPARSEABLE_HOLD") from exc
    if (w14.get("status") != "UCIE_W14_ISOLATED_OFFLINE_PYTHON_RUNTIME_PREPARED"
            or w14.get("git_head") != target_commit
            or w14.get("offline_dependency_import_ok") is not True
            or w14.get("runtime_database_migrated") is not False):
        raise OwnerPrepError("UCIE_W17_W14_RECEIPT_DID_NOT_PROVE_VENV_READY")
    return {
        "schema": SCHEMA,
        "status": "UCIE_W17_NEWROOT_OFFLINE_VENV_READY__LIVE_CUTOVER_HOLD",
        "canonical_staged_git_head": target_commit,
        "offline_wheels_verified_against_official_pypi": len(wheels),
        "new_python_315_environment": "PREPARED",
        "operating_root_moved_or_deleted": False,
        "w16_sqlite_rehearsal_reopened_or_promoted": False,
        "c40_or_scheduled_tasks_modified": False,
        "live_cutover_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE W17 owner-only venv bundle")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--owner-approval", default="")
    parser.add_argument("--target-commit", default="")
    args = parser.parse_args(argv)
    if not args.prepare:
        print(json.dumps({
            "schema": SCHEMA, "status": "UCIE_W17_CONTRACT_ONLY_NO_HOST_ACCESS",
            "network_requests": 0, "new_root_modified": False,
            "operating_root_or_db_modified": False,
            "c40_or_scheduled_tasks_modified": False,
            "live_cutover_authorized": False,
        }, sort_keys=True))
        return 0
    if args.owner_approval != APPROVAL:
        print(json.dumps({
            "schema": SCHEMA, "status": "UCIE_W17_EXPLICIT_OWNER_APPROVAL_REQUIRED",
            "live_cutover_authorized": False,
        }, sort_keys=True))
        return 2
    try:
        result = _subprocess_prepare(args.target_commit)
    except (OwnerPrepError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        safe_reason = (
            str(exc) if isinstance(exc, OwnerPrepError)
            and re.fullmatch(r"UCIE_W(?:14|17)_[A-Z0-9_]{3,90}", str(exc))
            else type(exc).__name__
        )
        print(json.dumps({
            "schema": SCHEMA, "status": "UCIE_W17_NEWROOT_ENV_PREPARATION_HOLD",
            "reason_code": safe_reason,
            "reason_type": type(exc).__name__,
            "do_not_retry_or_remove_partial_files": True,
            "c40_or_scheduled_tasks_modified": False,
            "live_cutover_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
