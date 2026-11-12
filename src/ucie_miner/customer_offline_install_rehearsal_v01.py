"""UCIE C1: owner-consented OFFLINE dependency install in a throwaway venv.

Default: read-only plan. --apply: exact owner Windows/Python3.15+interactive
gate, pre-existing three-wheel PyPI-hash receipt, and typed second consent.
Creates a NEW venv *only* under UCIE/downloaded/. Calls pip with no-index,
only-binary and REQUIRE-HASHES. Never installs into the owner .venv, runs
public-miner, changes tasks or calls a remote index. This is NOT C4 clean
recipient or C5 customer deployment. Third-party wheel installation can
execute untrusted distribution behavior: --apply requires explicit consent.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
from tempfile import TemporaryDirectory

from . import customer_owner_wheelhouse_acquire_v01 as acquire

SCHEMA = "UCIE_C1_OWNER_OFFLINE_DEPENDENCY_INSTALL_REHEARSAL_V01"
STATUS = "C1_ISOLATED_DEPENDENCY_INSTALL_ONLY_CUSTOMER_NO_GO"
CONSENT = "RUN_UCIE_C1_DISPOSABLE_OFFLINE_INSTALL_ONCE"
RECEIPT = "downloaded/ucie_c1_isolated_install_rehearsal_receipt_v01.json"
ROOT = Path("D:/UCIE")
MAX_RECEIPT_BYTES = 16000
RUN_TIMEOUT = 120
VERSION_CHECK = (
    "import json,sys,importlib.metadata as m;"
    "names=('cryptography','cffi','pycparser');"
    "print(json.dumps({'prefix':sys.prefix,'base_prefix':sys.base_prefix,"
    "'versions':{n:m.version(n) for n in names},"
    "'major':sys.version_info.major,'minor':sys.version_info.minor,"
    "'bits':64 if sys.maxsize>2**32 else 32},sort_keys=True))"
)


class OfflineInstallRehearsalError(ValueError):
    """Never treat a receipt or pip success as a commercial GO."""


def _valid_checkout(root: Path) -> Path:
    try:
        acquire._locked_root(root)
    except (acquire.WheelAcquisitionError, OSError, ValueError) as exc:
        raise OfflineInstallRehearsalError("UCIE source declaration not attested") from exc
    parent = root / "downloaded"
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise OfflineInstallRehearsalError("unsafe Git-ignored quarantine parent")
    gitignore = root / ".gitignore"
    if (gitignore.is_symlink() or not gitignore.is_file()
            or "downloaded/" not in gitignore.read_text(encoding="utf-8").splitlines()):
        raise OfflineInstallRehearsalError("downloaded is not Git-ignored")
    return root


def _wheel_receipt(root: Path) -> tuple[dict, dict[str, str]]:
    """Only fixed source-approved owner receipt; never fetch external data."""
    try:
        result = acquire.verify_local(root)
    except (acquire.WheelAcquisitionError, OSError, ValueError) as exc:
        raise OfflineInstallRehearsalError("offline wheelhouse not integrity-verified") from exc
    if (result.get("wheel_count") != len(acquire.PINNED)
            or result.get("customer_distribution_authorized") is not False):
        raise OfflineInstallRehearsalError("wheelhouse receipt asserts unsafe state")
    f = root / acquire.RECEIPT
    if f.is_symlink() or not f.is_file() or not 0 < f.stat().st_size <= MAX_RECEIPT_BYTES:
        raise OfflineInstallRehearsalError("invalid local wheel capture receipt")
    try:
        document = json.loads(f.read_text("ascii"))
    except (UnicodeError, ValueError, OSError) as exc:
        raise OfflineInstallRehearsalError("captured wheel receipt malformed") from exc
    if (type(document) is not dict
            or document.get("schema") != acquire.SCHEMA
            or document.get("customer_release_authorized") is not False
            or type(document.get("files")) is not list
            or len(document["files"]) != len(acquire.PINNED)):
        raise OfflineInstallRehearsalError("unrecognized captured PyPI receipt")
    pinned = dict(acquire.PINNED)
    hashed = {}
    for entry in document["files"]:
        if type(entry) is not dict:
            raise OfflineInstallRehearsalError("bad pinned package metadata")
        name, version, digest = (
            entry.get("distribution"), entry.get("version"), entry.get("sha256"))
        if (name not in pinned or version != pinned[name]
                or name in hashed or type(digest) is not str
                or len(digest) != 64
                or any(ch not in "0123456789abcdef" for ch in digest)):
            raise OfflineInstallRehearsalError("fixed version or wheel hash mismatch")
        hashed[name] = digest
    if set(hashed) != set(pinned):
        raise OfflineInstallRehearsalError("transitive pinned wheel missing")
    return document, hashed


def _requirements_lines(hashed: dict[str, str]) -> str:
    """All requirements and all transitive fixed versions have SHA256 locks."""
    if (type(hashed) is not dict
            or set(hashed) != set(name for name, _ in acquire.PINNED)):
        raise OfflineInstallRehearsalError("unapproved hash-locked package set")
    rows = []
    for name, version in acquire.PINNED:
        digest = hashed[name]
        if (type(digest) is not str or len(digest) != 64
                or any(ch not in "0123456789abcdef" for ch in digest)):
            raise OfflineInstallRehearsalError("bad SHA256 lock entry")
        rows.append(f"{name}=={version} --hash=sha256:{digest}")
    return "\n".join(rows) + "\n"


def preview(root: Path) -> dict:
    """No network, subprocess, installation, arbitrary files or task changes."""
    root = _valid_checkout(root)
    wheelhouse = root / acquire.WHEELHOUSE
    receipt = root / acquire.RECEIPT
    existing = root / RECEIPT
    state = "WAITING_FOR_OWNER_WHEEL_ACQUISITION"
    verified = False
    if existing.exists() or existing.is_symlink():
        state = "PREVIOUS_REHEARSAL_RECEIPT_PRESENT_DO_NOT_OVERWRITE"
    elif wheelhouse.exists() or receipt.exists():
        try:
            _wheel_receipt(root)
            verified = True
            state = "WHEEL_BYTES_VERIFIED_READY_FOR_SECOND_OWNER_CONSENT"
        except OfflineInstallRehearsalError:
            state = "WHEELHOUSE_OR_RECEIPT_INVALID_FAIL_CLOSED"
    return {
        "schema": SCHEMA, "status": STATUS, "mode": "OFFLINE_PREVIEW",
        "source_project": "UCIE_ONLY",
        "target": "Windows x64 standard CPython 3.15",
        "fixed_requirements": [f"{n}=={v}" for n, v in acquire.PINNED],
        "local_wheelhouse_sha_receipt_verified": verified,
        "readiness": state,
        "owner_apply_requires_exact_interactive_consent": True,
        "owner_consent_phrase": CONSENT,
        "source_wheelhouse_relative_path": acquire.WHEELHOUSE,
        "local_rehearsal_receipt_relative_path": RECEIPT,
        "subprocesses_executed": 0,
        "external_packages_installed_or_imported": False,
        "network_requests": 0,
        "customer_release_authorized": False,
    }


def _owner_gate(root: Path) -> Path:
    """Only exact interactive owner Python, not a CI runner or owner web task."""
    root = _valid_checkout(root)
    try:
        actual_root = root.resolve(strict=True)
        expected_root = ROOT.resolve(strict=True)
        owner_python = (root / ".venv" / "Scripts" / "python.exe").resolve(
            strict=True)
        current_python = Path(sys.executable).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise OfflineInstallRehearsalError("owner Python identity unavailable") from exc
    if (os.name != "nt" or actual_root != expected_root
            or current_python != owner_python or sys.implementation.name != "cpython"
            or sys.version_info[:2] != (3, 15) or sys.maxsize <= 2**32
            or sysconfig.get_config_var("Py_GIL_DISABLED") not in (None, 0)
            or not sys.stdin.isatty() or bool(os.environ.get("CI"))):
        raise OfflineInstallRehearsalError("exact interactive owner Windows Python3.15 required")
    state = preview(root)
    if not state["local_wheelhouse_sha_receipt_verified"]:
        raise OfflineInstallRehearsalError("wheelhouse pending, malformed or rehearsal already recorded")
    return current_python


def _venv_command(owner_python: Path, target: Path) -> list[str]:
    return [str(owner_python), "-I", "-B", "-m", "venv",
            "--copies", "--without-scm-ignore-files", str(target)]


def _pip_command(venv_python: Path, wheelhouse: Path,
                 requirements: Path) -> list[str]:
    """Pip's hash checking applies to ALL pinned dependencies; no index."""
    return [
        str(venv_python), "-I", "-B", "-m", "pip", "--isolated", "install",
        "--no-index", "--find-links", str(wheelhouse),
        "--require-hashes", "--only-binary=:all:",
        "--no-cache-dir", "--disable-pip-version-check", "--no-input",
        "--no-compile", "--retries", "0", "--timeout", "10",
        "-r", str(requirements),
    ]


def _environment() -> dict[str, str]:
    """Explicit no-index for pip plus stripped inherited site/PYTHON paths."""
    kept = ("PATH", "SystemRoot", "SYSTEMROOT", "WINDIR",
            "TEMP", "TMP", "HOME", "USERPROFILE")
    env = {k: os.environ[k] for k in kept if k in os.environ}
    env.update({
        "PIP_NO_INDEX": "1",
        "PIP_CONFIG_FILE": os.devnull,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    return env


def _run_exact(args: list[str], cwd: Path, env: dict[str, str],
               purpose: str) -> str:
    if not args or args[1:3] != ["-I", "-B"]:
        raise OfflineInstallRehearsalError("no isolated Python command")
    try:
        p = subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                           text=True, check=False, timeout=RUN_TIMEOUT,
                           shell=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OfflineInstallRehearsalError(purpose + " failed to complete") from exc
    if (p.returncode != 0 or len(p.stdout) > 20000
            or len(p.stderr) > 20000):
        # Never surface untrusted pip/vendor logs, package paths or commands.
        raise OfflineInstallRehearsalError(purpose + " failed closed")
    return p.stdout.strip()


def _check_versions(output: str, expected_prefix: Path) -> dict:
    try:
        payload = json.loads(output)
    except (ValueError, TypeError) as exc:
        raise OfflineInstallRehearsalError("isolated version check not JSON") from exc
    expected = dict(acquire.PINNED)
    if (type(payload) is not dict or payload.get("versions") != expected
            or payload.get("major") != 3 or payload.get("minor") != 15
            or payload.get("bits") != 64
            or payload.get("prefix") != str(expected_prefix)
            or payload.get("prefix") == payload.get("base_prefix")):
        raise OfflineInstallRehearsalError("new-venv dependency identity mismatch")
    return expected


def run_owner_rehearsal(root: Path, consent: str) -> dict:
    if consent != CONSENT:
        raise OfflineInstallRehearsalError("separate owner install consent missing")
    owner_python = _owner_gate(root)
    document, hashes = _wheel_receipt(root)
    target_receipt = root / RECEIPT
    if target_receipt.exists() or target_receipt.is_symlink():
        raise OfflineInstallRehearsalError("previous rehearsal receipt must be preserved")
    parent = root / "downloaded"
    if parent.is_symlink() or not parent.is_dir():
        raise OfflineInstallRehearsalError("Git-ignored staging directory missing")
    with TemporaryDirectory(prefix="ucie_c1_offline_install_", dir=parent) as folder:
        scratch = Path(folder)
        venv = scratch / "recipient_venv"
        pip_requirements = scratch / "locked-requirements.txt"
        pip_requirements.write_text(_requirements_lines(hashes), encoding="ascii")
        env = _environment()
        _run_exact(_venv_command(owner_python, venv), scratch, env, "offline venv creation")
        child = venv / "Scripts" / "python.exe"
        if child.is_symlink() or not child.is_file():
            raise OfflineInstallRehearsalError("new isolated Python executable not present")
        _run_exact(_pip_command(child, root / acquire.WHEELHOUSE,
                                pip_requirements), scratch, env, "no-index hashlocked pip")
        _run_exact([str(child), "-I", "-B", "-m", "pip", "--isolated",
                    "check", "--disable-pip-version-check"], scratch, env,
                   "offline dependency consistency check")
        versions = _check_versions(_run_exact(
            [str(child), "-I", "-B", "-c", VERSION_CHECK],
            scratch, env, "installed distribution metadata check"
        ), venv)
        # The temporary venv is deleted after the with block, regardless
        # of success or exception. It is NOT an independent Windows host.
    receipt = {
        "schema": SCHEMA, "status": STATUS,
        "utc_at": datetime.now(timezone.utc).isoformat(),
        "evidence": "SAME_OWNER_HOST_DISPOSABLE_VENV_ONLY",
        "pinned_versions": versions,
        "captured_wheel_receipt_sha256": sha256(
            (root / acquire.RECEIPT).read_bytes()).hexdigest(),
        "requirements_sha256": sha256(_requirements_lines(hashes).encode(
            "ascii")).hexdigest(),
        "new_venv_created": True,
        "offline_pip_no_index_and_require_hashes_succeeded": True,
        "pip_dependency_check_succeeded": True,
        "installed_distribution_metadata_version_check_succeeded": True,
        "disposable_venv_removed": True,
        "third_party_vendor_import_runtime_attested": False,
        "operating_owner_venv_modified": False,
        "full_product_installed": False,
        "clean_second_windows_recipient_attested": False,
        "whole_product_update_and_rollback_attested": False,
        "publisher_signature_verified": False,
        "rights_and_sbom_approved": False,
        "public_package_published": False,
        "customer_distribution_authorized": False,
    }
    # No existing receipt overwritten. This is a developer QA receipt only.
    with target_receipt.open("x", encoding="ascii") as stream:
        json.dump(receipt, stream, sort_keys=True, ensure_ascii=True)
        stream.write("\n")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE C1 optional owner-only offline install in disposable venv"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    try:
        if args.apply:
            _owner_gate(root)  # Never prompt a CI/non-owner invocation.
            typed = input("Type " + CONSENT + " to install wheels ONLY in disposable venv: ")
            result = run_owner_rehearsal(root, typed)
        else:
            result = preview(root)
    except (OfflineInstallRehearsalError, OSError, ValueError, EOFError):
        result = {
            "schema": SCHEMA,
            "status": "UCIE_C1_OFFLINE_REHEARSAL_FAILED_CLOSED_CUSTOMER_NO_GO",
            "customer_distribution_authorized": False,
            "owner_venv_modified": False,
        }
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
