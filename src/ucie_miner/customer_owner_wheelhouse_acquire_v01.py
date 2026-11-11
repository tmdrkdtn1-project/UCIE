"""UCIE C1 owner-gated acquisition of exact Windows CPython 3.15 wheels.

Default is OFFLINE PREVIEW. Apply is STRICTLY interactive on the owner's
D:/UCIE Windows 64-bit CPython3.15 venv with exact typed consent.
The only network authority after consent is official PyPI package delivery
and its versioned JSON release metadata (not a public-evidence source miner).
Never runs/installs external wheel code or changes any running UCIE service.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
from tempfile import TemporaryDirectory
import urllib.request

from .customer_offline_dependency_gate_v01 import (
    WHEELHOUSE, _inspect_wheel, _normal_name, _project, _root,
    OfflineDependencyError,
)

SCHEMA = "UCIE_C1_OWNER_GATE_PYPI_WIN315_WHEELHOUSE_V01"
STATUS = "THIRD_PARTY_WHEELS_QUARANTINE_ONLY_CUSTOMER_NO_GO"
PINNED = (
    ("cryptography", "50.0.2"),
    ("cffi", "2.1.1"),
    ("pycparser", "3.12"),
)
PINNED_NAMES = tuple(name for name, _ in PINNED)
PYPI = "https://pypi.org"
RECEIPT = "downloaded/ucie_c1_wheelhouse_receipt_preview.json"
CONSENT = "ACQUIRE_UCIE_C1_WIN315_WHEELS_ONCE"
HOST_ROOT = Path("D:/UCIE")
MAX_PYPI_JSON = 2_500_000
MAX_OUTPUT_CHARS = 32_000


class WheelAcquisitionError(ValueError):
    """Package acquisition only; never a customer release authority."""


def _locked_root(root: Path) -> Path:
    if not isinstance(root, Path):
        raise WheelAcquisitionError("UCIE root must be Path")
    try:
        _root(root)
        project = _project(root)
    except (OfflineDependencyError, OSError) as exc:
        raise WheelAcquisitionError("current UCIE pyproject not verified") from exc
    if (project["declared_runtime_requirements"]
            != ["cryptography>=50.0.2,<51"]):
        raise WheelAcquisitionError("reviewed UCIE dependency contract changed")
    return root


def _requirements() -> tuple[str, ...]:
    return tuple(name + "==" + version for name, version in PINNED)


def _command(python: Path, staging: Path) -> list[str]:
    """No shell or user-supplied flags: exact isolated binary-only pip download."""
    return [
        str(python), "-I", "-B", "-m", "pip", "--isolated", "download",
        "--only-binary=:all:", "--no-cache-dir", "--disable-pip-version-check",
        "--no-input", "--retries", "1", "--timeout", "12",
        "--index-url", "https://pypi.org/simple",
        "--implementation", "cp", "--python-version", "3.15",
        "--platform", "win_amd64", "--abi", "cp315", "--abi", "abi3",
        "--abi", "none", "--dest", str(staging), *_requirements(),
    ]


def plan(root: Path) -> dict:
    """Offline only. No downloading, environment change, install or pip calls."""
    root = _locked_root(root)
    destination = root / WHEELHOUSE
    receipt = root / RECEIPT
    if (destination.is_symlink() or receipt.is_symlink()
            or destination.parent.is_symlink()
            or (destination.parent.exists() and not destination.parent.is_dir())):
        raise WheelAcquisitionError("UCIE quarantine path symlink forbidden")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "mode": "OFFLINE_PREVIEW",
        "target": "Windows x86-64 / standard CPython 3.15",
        "pinned_packages": list(_requirements()),
        "wheelhouse_relative": WHEELHOUSE,
        "receipt_relative": RECEIPT,
        "wheelhouse_exists": destination.exists(),
        "receipt_exists": receipt.exists(),
        "owner_apply_available_only_after_interactive_confirmation": True,
        "owner_consent_phrase": CONSENT,
        "only_official_index": PYPI + "/simple",
        "index_metadata": PYPI + "/pypi/<fixed-package>/<fixed-version>/json",
        "no_source_distributions": True,
        "downloads_executed": False,
        "packages_imported_or_installed": False,
        "customer_distribution_authorized": False,
        "commercial_rights_approved": False,
        "software_signatures_verified": False,
        "dependency_closure_independently_attested": False,
    }


def _pypi_index(name: str, version: str) -> dict[str, str]:
    """Fetch bounded official metadata ONLY after an explicit owner Apply."""
    if (name, version) not in PINNED:
        raise WheelAcquisitionError("unapproved PyPI release metadata target")
    endpoint = PYPI + "/pypi/" + name + "/" + version + "/json"
    request = urllib.request.Request(
        endpoint, headers={"User-Agent": "UCIE-C1-owner-wheelhouse/1.0",
                           "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=12) as reply:
            if reply.geturl() != endpoint or reply.status != 200:
                raise WheelAcquisitionError("unexpected PyPI metadata redirect/status")
            raw = reply.read(MAX_PYPI_JSON + 1)
            if len(raw) > MAX_PYPI_JSON:
                raise WheelAcquisitionError("PyPI release metadata too large")
    except (OSError, ValueError) as exc:
        raise WheelAcquisitionError("official PyPI release metadata unavailable") from exc
    try:
        payload = json.loads(raw)
        info = payload.get("info")
        files = payload.get("urls")
        if (not isinstance(info, dict) or not isinstance(files, list)
                or _normal_name(info.get("name", "")) != name
                or info.get("version") != version
                or len(files) > 180):
            raise WheelAcquisitionError("PyPI version/package identity drift")
        hashes: dict[str, str] = {}
        for row in files:
            if not isinstance(row, dict) or row.get("packagetype") != "bdist_wheel":
                continue
            filename, digests = row.get("filename"), row.get("digests")
            if (not isinstance(filename, str) or not filename.endswith(".whl")
                    or len(filename) > 160 or not isinstance(digests, dict)):
                raise WheelAcquisitionError("PyPI wheel metadata malformed")
            expected = digests.get("sha256")
            if (not isinstance(expected, str) or len(expected) != 64
                    or any(c not in "0123456789abcdef" for c in expected)
                    or filename in hashes):
                raise WheelAcquisitionError("PyPI wheel checksum malformed")
            hashes[filename] = expected
        if not hashes:
            raise WheelAcquisitionError("no official wheel hashes for fixed release")
        return hashes
    except (TypeError, KeyError, AttributeError) as exc:
        raise WheelAcquisitionError("invalid PyPI metadata representation") from exc


def validate_candidate(stage: Path, official: dict[str, dict[str, str]]) -> dict:
    """Read only staged untrusted bytes; hash each against official PyPI index."""
    if (not stage.is_dir() or stage.is_symlink()
            or set(official) != set(PINNED_NAMES)):
        raise WheelAcquisitionError("candidate directory/official pins invalid")
    found = sorted(stage.iterdir())
    if len(found) != len(PINNED):
        raise WheelAcquisitionError("missing/extra wheel candidate count")
    receipts = []
    names: set[str] = set()
    for file in found:
        if file.is_symlink() or not file.is_file() or file.suffix != ".whl":
            raise WheelAcquisitionError("unexpected downloaded wheelhouse entry")
        try:
            row = _inspect_wheel(file)
        except (OfflineDependencyError, OSError, ValueError) as exc:
            raise WheelAcquisitionError("untrusted wheel internal integrity failed") from exc
        name, version = row["name"], row["version"]
        if ((name, version) not in PINNED or name in names
                or not row.get("metadata_record_sha256_verified")):
            raise WheelAcquisitionError("wheel identity/version not fixed")
        names.add(name)
        actual = sha256(file.read_bytes()).hexdigest()
        if official[name].get(file.name) != actual:
            raise WheelAcquisitionError("downloaded wheel differs from PyPI SHA256")
        receipts.append({
            "distribution": name, "version": version,
            "filename": file.name, "sha256": actual,
            "size": file.stat().st_size,
            "origin": "official PyPI per-version JSON SHA256",
            "wheel_RECORD_verified": True,
            "tags": {
                "python": row["python_tag"], "abi": row["abi_tag"],
                "platform": row["platform_tag"],
            },
            "requires_dist_observed": row["requires_dist"],
            "source_code_executed": False,
            "third_party_rights_approved": False,
            "publisher_provenance_independently_verified": False,
        })
    if names != set(PINNED_NAMES):
        raise WheelAcquisitionError("incomplete pinned third-party dependency set")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "target": "win_amd64-cp315-standard",
        "pinned_versions": list(_requirements()),
        "files": receipts,
        "all_wheel_sha256_equal_official_pypi_metadata": True,
        "wheel_content_installed_or_executed": False,
        "pip_download_performed_only_after_owner_consent": True,
        "transitive_dependency_compatibility_independently_verified": False,
        "wheel_abi_execution_tested": False,
        "license_and_SPDX_approved": False,
        "publisher_signature_independently_verified": False,
        "private_customer_distribution_authorized": False,
        "customer_release_authorized": False,
    }


def verify_local(root: Path) -> dict:
    """No network. Receipt is recorded metadata, not a signature."""
    root = _locked_root(root)
    store, manifest_file = root / WHEELHOUSE, root / RECEIPT
    if (store.is_symlink() or not store.is_dir() or manifest_file.is_symlink()
            or not manifest_file.is_file() or manifest_file.stat().st_size > 15_000):
        raise WheelAcquisitionError("wheelhouse and bounded receipt not both available")
    try:
        receipt = json.loads(manifest_file.read_text(encoding="ascii"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise WheelAcquisitionError("wheelhouse receipt unreadable") from exc
    if (not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA
            or receipt.get("status") != STATUS
            or receipt.get("target") != "win_amd64-cp315-standard"
            or receipt.get("pinned_versions") != list(_requirements())
            or receipt.get("customer_release_authorized") is not False
            or receipt.get("license_and_SPDX_approved") is not False
            or type(receipt.get("files")) is not list
            or len(receipt["files"]) != len(PINNED)):
        raise WheelAcquisitionError("wheelhouse receipt contract drift")
    expected_names = set()
    for entry in receipt["files"]:
        if type(entry) is not dict:
            raise WheelAcquisitionError("bad wheel record")
        name, version, filename = (
            entry.get("distribution"), entry.get("version"), entry.get("filename"))
        if (type(filename) is not str or "/" in filename or chr(92) in filename
                or (name, version) not in PINNED or filename in expected_names
                or not filename.endswith(".whl")):
            raise WheelAcquisitionError("unknown wheel receipt file")
        expected_names.add(filename)
        file = store / filename
        if file.is_symlink() or not file.is_file():
            raise WheelAcquisitionError("missing or linked pinned wheel")
        row = _inspect_wheel(file)
        if (row["name"] != name or row["version"] != version
                or entry.get("sha256") != sha256(file.read_bytes()).hexdigest()):
            raise WheelAcquisitionError("offline wheelhouse hash does not match receipt")
    if set(x.name for x in store.iterdir()) != expected_names:
        raise WheelAcquisitionError("extra files in pinned quarantine")
    return {
        "schema": SCHEMA, "status": STATUS,
        "mode": "OFFLINE_VERIFIED_AGAINST_UNTRUSTED_UNSIGNED_CAPTURE_RECEIPT",
        "wheel_count": len(expected_names),
        "all_local_bytes_match_captured_pypi_digests": True,
        "packages_installed_or_executed": False,
        "complete_customer_install_acceptance": False,
        "third_party_licenses_approved": False,
        "customer_distribution_authorized": False,
    }


def _owner_gate(root: Path) -> Path:
    """Never run acquisition from synthetic/CI/other project locations."""
    root = _locked_root(root)
    try:
        expected_root = HOST_ROOT.resolve(strict=True)
        expected_python = (root / ".venv" / "Scripts" / "python.exe").resolve(
            strict=True)
        current_python = Path(sys.executable).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise WheelAcquisitionError("owner root/venv not verified") from exc
    if (os.name != "nt" or root.resolve() != expected_root
            or current_python != expected_python
            or sys.implementation.name != "cpython"
            or sys.version_info[:2] != (3, 15) or sys.maxsize <= 2**32
            or sysconfig.get_config_var("Py_GIL_DISABLED") not in (None, 0)
            or not sys.stdin.isatty() or os.environ.get("CI")):
        raise WheelAcquisitionError("interactive exact owner Windows x64 Python3.15 venv required")
    if importlib.util.find_spec("pip") is None:
        raise WheelAcquisitionError("owner venv pip not present")
    destination, receipt = root / WHEELHOUSE, root / RECEIPT
    if (destination.parent.is_symlink()
            or (destination.parent.exists() and not destination.parent.is_dir())):
        raise WheelAcquisitionError("UCIE quarantine parent unsafe")
    ignore = root / ".gitignore"
    if (ignore.is_symlink() or not ignore.is_file()
            or "downloaded/" not in ignore.read_text(encoding="utf-8").splitlines()):
        raise WheelAcquisitionError("downloaded/ must be Git-ignored before any vendor fetch")
    if (destination.exists() or destination.is_symlink()
            or receipt.exists() or receipt.is_symlink()):
        raise WheelAcquisitionError("existing quarantine/receipt will never be overwritten")
    return current_python


def acquire_once(root: Path, *, typed: str) -> dict:
    """Consent-bound network action; no downloads without owner approval."""
    if typed != CONSENT:
        raise WheelAcquisitionError("owner explicit consent was not provided")
    python = _owner_gate(root)
    parent = root / "downloaded"
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise WheelAcquisitionError("UCIE downloaded directory cannot be linked")
    parent.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="ucie_c1_wheel_stage_", dir=parent) as tmp:
        scratch = Path(tmp) / "wheels"
        scratch.mkdir()
        args = _command(python, scratch)
        env = {
            key: os.environ[key] for key in (
                "PATH", "SystemRoot", "SYSTEMROOT", "WINDIR",
                "TEMP", "TMP", "HOME", "USERPROFILE",
            ) if key in os.environ
        }
        try:
            process = subprocess.run(args, shell=False, cwd=root,
                                     env=env, capture_output=True, text=True,
                                     timeout=180, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise WheelAcquisitionError("bounded pip binary download failed") from exc
        if (process.returncode != 0
                or len(process.stdout) > MAX_OUTPUT_CHARS
                or len(process.stderr) > MAX_OUTPUT_CHARS):
            raise WheelAcquisitionError("official PyPI binary-only resolve/download not verified")
        official = {name: _pypi_index(name, version) for name, version in PINNED}
        receipt = validate_candidate(scratch, official)
        # Atomic promotion is only to the preapproved UCIE-local quarantine;
        # no customer files, installed packages, service or task are touched.
        target = root / WHEELHOUSE
        if target.exists() or target.is_symlink():
            raise WheelAcquisitionError("wheelhouse unexpectedly appeared before publish")
        os.rename(scratch, target)
        receipt_file = root / RECEIPT
        with receipt_file.open("x", encoding="ascii") as stream:
            json.dump(receipt, stream, sort_keys=True, ensure_ascii=True)
            stream.write("\n")
    result = verify_local(root)
    if result["wheel_count"] != len(PINNED):
        raise WheelAcquisitionError("post-acquisition offline acceptance failed")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE C1 pinned wheel acquisition: default preview, never install"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    try:
        if args.apply:
            # Check FIRST so an invalid owner cannot get an actionable prompt.
            _owner_gate(root)
            typed = input("Type " + CONSENT + " to download official wheels ONLY: ")
            result = acquire_once(root, typed=typed)
        elif args.verify:
            result = verify_local(root)
        else:
            result = plan(root)
    except (WheelAcquisitionError, OSError, ValueError, EOFError):
        result = {
            "schema": SCHEMA,
            "status": "UCIE_C1_WHEELHOUSE_NO_GO_OR_OWNER_GATE_FAILED",
            "customer_distribution_authorized": False,
            "packages_installed_or_executed": False,
        }
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0  # Technical quarantine success never implies customer GO.


if __name__ == "__main__":
    raise SystemExit(main())
