"""UCIE C1: first-party full-product wheel + four-pillar offline rehearsal.

Default preview is read-only. Owner --apply requires a *third*, distinct typed
consent, verified offline wheels and previous dependency-only install receipt.
All first-party source is copied into a new disposable UCIE folder; product
wheel is built there, never in the dirty owner worktree. Third-party wheels
are installed ONLY in a disposable new venv using exact captured SHA256 locks.
The owner venv, running localhost app, scheduler and database remain untouched.
This is NOT a clean second recipient, signed bundle or customer release.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import sysconfig
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from . import customer_offline_install_rehearsal_v01 as dependency
from . import customer_owner_wheelhouse_acquire_v01 as acquire
from . import customer_runtime_closure_v01 as runtime
from . import customer_offline_dependency_gate_v01 as gate
from .customer_staging_v01 import PILLARS

SCHEMA = "UCIE_C1_FULL_FIRST_PARTY_OFFLINE_PRODUCT_REHEARSAL_V01"
STATUS = "UCIE_C1_SAME_OWNER_HOST_WHOLE_PRODUCT_PREVIEW_CUSTOMER_NO_GO"
CONSENT = "RUN_UCIE_C1_FULL_PRODUCT_LOCAL_ONLY_ONCE"
RECEIPT = "downloaded/ucie_c1_full_product_rehearsal_receipt_v01.json"
OWNER_ROOT = Path("D:/UCIE")
FIRST_PARTY_NAME = "ucie-public-only-demo"
FIRST_PARTY_VERSION = "0.1.0"
FIRST_PARTY_WHEEL = "ucie_public_only_demo-0.1.0-py3-none-any.whl"
MAX_RECEIPT = 16000
MAX_STDOUT = 22000
TIMEOUT = 150
_ALLOWED_FIRST_PARTY = ("ucie_miner/", "ucie_public/")
WHEEL_META = "ucie_public_only_demo-0.1.0.dist-info/"

NATIVE_PROBE = """import json,cryptography,cffi,pycparser
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
k=AESGCM.generate_key(bit_length=128)
nonce=bytes(range(12))
message=b'UCIE C1 disposable cryptography check'
encrypted=AESGCM(k).encrypt(nonce,message,None)
if AESGCM(k).decrypt(nonce,encrypted,None)!=message:
    raise RuntimeError('native AEAD roundtrip failed')
ffi=cffi.FFI()
ffi.cdef('int ucie_inert(int x);')
tree=pycparser.CParser().parse('int ucie_inert(int x);')
if not tree.ext:
    raise RuntimeError('UCIE C grammar parse failed')
print(json.dumps({'versions':{
    'cryptography':cryptography.__version__,
    'cffi':cffi.__version__,'pycparser':pycparser.__version__},
    'cryptography_aesgcm_roundtrip':True,
    'cffi_declaration_parsed':True,
    'pycparser_c_declaration_parsed':True,
    'synthetic_only':True},sort_keys=True))
"""
UI_PROBE = """import json,sys
from pathlib import Path
from ucie_miner.customer_portable_preview_v01 import probe_preview_root
print(json.dumps(probe_preview_root(Path(sys.argv[1])),sort_keys=True))
"""


class OfflineFullProductError(ValueError):
    """C1 fail-closed state; never a customer delivery authorization."""


def _receipt_file(root: Path, name: str) -> Path:
    if name not in (dependency.RECEIPT, RECEIPT):
        raise OfflineFullProductError("unapproved receipt path")
    target = root / name
    if (target.parent.is_symlink() or target.is_symlink()
            or not target.is_file() or not 0 < target.stat().st_size <= MAX_RECEIPT):
        raise OfflineFullProductError("required owner C1 receipt absent or unsafe")
    return target


def _dependency_evidence(root: Path) -> tuple[dict[str, str], str]:
    """Locally recheck unsigned capture + existing owner dependency test receipt."""
    try:
        dependency._valid_checkout(root)
        capture, hashes = dependency._wheel_receipt(root)
    except (dependency.OfflineInstallRehearsalError,
            acquire.WheelAcquisitionError, OSError, ValueError) as exc:
        raise OfflineFullProductError("wheelhouse hash-capture gate not met") from exc
    receipt_file = _receipt_file(root, dependency.RECEIPT)
    try:
        report = json.loads(receipt_file.read_text(encoding="ascii"))
    except (ValueError, UnicodeError, OSError) as exc:
        raise OfflineFullProductError("previous C1 install receipt unreadable") from exc
    if (type(report) is not dict
            or report.get("schema") != dependency.SCHEMA
            or report.get("status") != dependency.STATUS
            or report.get("evidence") != "SAME_OWNER_HOST_DISPOSABLE_VENV_ONLY"
            or report.get("pinned_versions") != dict(acquire.PINNED)
            or report.get("captured_wheel_receipt_sha256") != sha256(
                (root / acquire.RECEIPT).read_bytes()).hexdigest()
            or report.get("offline_pip_no_index_and_require_hashes_succeeded") is not True
            or report.get("pip_dependency_check_succeeded") is not True
            or report.get("installed_distribution_metadata_version_check_succeeded") is not True
            or report.get("disposable_venv_removed") is not True
            or report.get("full_product_installed") is not False
            or report.get("customer_distribution_authorized") is not False):
        raise OfflineFullProductError("prior owner dependency rehearsal not attested")
    return hashes, sha256(receipt_file.read_bytes()).hexdigest()


def preview(root: Path) -> dict:
    """Read-only preflight; absolutely no build, pip, external import or install."""
    try:
        dependency._valid_checkout(root)
    except (dependency.OfflineInstallRehearsalError, ValueError, OSError) as exc:
        raise OfflineFullProductError("exact UCIE checkout required") from exc
    already = root / RECEIPT
    state = "DEPENDENCY_WHEELHOUSE_OR_INSTALL_RECEIPT_PENDING"
    hash_state = False
    if already.exists() or already.is_symlink():
        state = "FULL_PRODUCT_PREVIEW_RECEIPT_ALREADY_PRESENT_NO_OVERWRITE"
    else:
        try:
            _dependency_evidence(root)
            hash_state = True
            state = "HASH_LOCKED_DEPENDENCIES_READY_FOR_OWNER_FULL_PRODUCT_CONSENT"
        except OfflineFullProductError:
            pass
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "mode": "OFFLINE_READONLY_PREVIEW",
        "readiness": state,
        "existing_verified_dependency_rehearsal": hash_state,
        "new_owner_consent_phrase": CONSENT,
        "fixed_dependent_wheels": [name + "==" + ver for name, ver in acquire.PINNED],
        "first_party_product": FIRST_PARTY_NAME + "==" + FIRST_PARTY_VERSION,
        "first_party_package_source": "UCIE_ONLY_DISPOSABLE_SOURCE_SNAPSHOT",
        "native_vendor_import_during_apply": True,
        "four_pillar_installed_cli_during_apply": True,
        "portable_local_ui_http_during_apply": True,
        "second_clean_windows_recipient": False,
        "download_or_pip_executed": False,
        "owner_running_service_modified": False,
        "operating_database_writes": 0,
        "customer_distribution_authorized": False,
    }


def _owner_gate(root: Path) -> Path:
    dependency._valid_checkout(root)
    try:
        actual = root.resolve(strict=True)
        expected = OWNER_ROOT.resolve(strict=True)
        current = Path(sys.executable).resolve(strict=True)
        owner_python = (root / ".venv" / "Scripts" / "python.exe").resolve(
            strict=True)
    except (OSError, RuntimeError) as exc:
        raise OfflineFullProductError("owner Python or root unavailable") from exc
    if (os.name != "nt" or actual != expected or current != owner_python
            or sys.implementation.name != "cpython"
            or sys.version_info[:2] != (3, 15) or sys.maxsize <= 2**32
            or sysconfig.get_config_var("Py_GIL_DISABLED") not in (None, 0)
            or not sys.stdin.isatty() or bool(os.environ.get("CI"))):
        raise OfflineFullProductError("interactive owner Windows CPython3.15 x64 required")
    dest = root / RECEIPT
    if dest.exists() or dest.is_symlink():
        raise OfflineFullProductError("prior C1 full-product receipt cannot be overwritten")
    _dependency_evidence(root)
    return current


def _run(args: list[str], cwd: Path, env: dict[str, str], what: str) -> str:
    if (type(args) is not list or len(args) < 5
            or args[1:3] != ["-I", "-B"]):
        raise OfflineFullProductError("non-isolated Python execution blocked")
    try:
        p = subprocess.run(args, shell=False, cwd=cwd, env=env,
                           check=False, capture_output=True, text=True,
                           timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OfflineFullProductError(what + " failed to complete") from exc
    if (p.returncode != 0 or len(p.stdout) > MAX_STDOUT or len(p.stderr) > MAX_STDOUT):
        # Never pass untrusted vendor/build logs and local paths to receipts.
        raise OfflineFullProductError(what + " failed closed")
    return p.stdout.strip()


def _build_cmd(python: Path, source: Path, out: Path) -> list[str]:
    return [
        str(python), "-I", "-B", "-m", "pip", "--isolated", "wheel",
        "--no-index", "--no-deps", "--no-build-isolation",
        "--disable-pip-version-check", "--no-cache-dir", "--no-input",
        "--wheel-dir", str(out), str(source)
    ]


def _install_cmd(venv_python: Path, vendor: Path,
                 product_wheel_folder: Path, requirements: Path) -> list[str]:
    return [
        str(venv_python), "-I", "-B", "-m", "pip", "--isolated", "install",
        "--no-index", "--find-links", str(vendor),
        "--find-links", str(product_wheel_folder), "--require-hashes",
        "--only-binary=:all:", "--no-cache-dir", "--no-input",
        "--no-compile", "--disable-pip-version-check",
        "--timeout", "10", "--retries", "0", "-r", str(requirements)
    ]


def _inspect_first_party_wheel(wheel: Path, source: dict[str, bytes]) -> dict:
    """Check actual wheel RECORD and exact UCIE source bytes, no code execution."""
    if (wheel.is_symlink() or not wheel.is_file()
            or wheel.name != FIRST_PARTY_WHEEL
            or not 100 < wheel.stat().st_size <= gate.MAX_WHEEL_BYTES):
        raise OfflineFullProductError("unexpected first-party wheel filename or size")
    try:
        info = gate._inspect_wheel(wheel)
    except (gate.OfflineDependencyError, OSError, ValueError) as exc:
        raise OfflineFullProductError("first-party wheel RECORD not validated") from exc
    if (info["name"] != FIRST_PARTY_NAME
            or info["version"] != FIRST_PARTY_VERSION
            or not info["metadata_record_sha256_verified"]
            or not any("cryptography" in req.lower() and "50.0.2" in req
                       for req in info["requires_dist"])):
        raise OfflineFullProductError("built UCIE package identity/runtime requirement drift")
    expected = {}
    for name, raw in source.items():
        if name.endswith(".py") and name.startswith(("src/ucie_miner/",
                                                     "src/ucie_public/")):
            expected[name[4:]] = raw
    if not expected or "ucie_miner/customer_staging_v01.py" not in expected:
        raise OfflineFullProductError("four-pillar first-party source absent")
    with ZipFile(wheel) as archive:
        members = set(archive.namelist())
        if not set(expected).issubset(members):
            raise OfflineFullProductError("package omitted approved Python modules")
        for name in members:
            if (name.startswith(_ALLOWED_FIRST_PARTY)
                    and name.endswith(".py")):
                if name not in expected:
                    raise OfflineFullProductError("unexpected first-party Python module")
            elif not name.startswith(WHEEL_META):
                raise OfflineFullProductError("wheel bundled unreviewed non-UCIE payload")
        for name, raw in expected.items():
            if archive.read(name) != raw:
                raise OfflineFullProductError("installed wheel did not preserve exact UCIE source")
        entry = archive.read(WHEEL_META + "entry_points.txt").decode("utf-8")
        if "ucie-product-preview" not in entry or "customer_staging_v01:main" not in entry:
            raise OfflineFullProductError("four-pillar installed entrypoint unavailable")
    return {
        "sha256": info["wheel_sha256"],
        "file_count": len(expected),
        "wheel_record_verified": True,
        "source_code_bytes_match": True,
        "customer_distribution_authorized": False,
    }


def _requirements(vendor_hashes: dict[str, str], product_sha: str) -> str:
    if (type(product_sha) is not str or
            re.fullmatch("[0-9a-f]{64}", product_sha) is None):
        raise OfflineFullProductError("first-party product wheel digest not attested")
    return (dependency._requirements_lines(vendor_hashes) +
            FIRST_PARTY_NAME + "==" + FIRST_PARTY_VERSION +
            " --hash=sha256:" + product_sha + "\n")


def _check_native(output: str) -> dict:
    try:
        data = json.loads(output)
    except (ValueError, TypeError) as exc:
        raise OfflineFullProductError("native runtime probe not machine-readable") from exc
    if (type(data) is not dict or data.get("versions") != dict(acquire.PINNED)
            or any(data.get(flag) is not True for flag in (
                "cryptography_aesgcm_roundtrip",
                "cffi_declaration_parsed", "pycparser_c_declaration_parsed",
                "synthetic_only"))):
        raise OfflineFullProductError("third-party native/synthetic probe contract failed")
    return {
        "versions": data["versions"],
        "cryptography_aesgcm_roundtrip": True,
        "cffi_declaration_parsed": True,
        "pycparser_c_declaration_parsed": True,
        "vendor_origin_approved": False,
    }


def _check_four_pillars(output: str) -> dict:
    try:
        obj = json.loads(output)
    except (ValueError, TypeError) as exc:
        raise OfflineFullProductError("installed four-pillar preview not JSON") from exc
    if (type(obj) is not dict or obj.get("schema") !=
            "UCIE_FOUR_PILLAR_INSTALLED_STAGING_V01"
            or obj.get("four_pillars_exercised") is not True
            or obj.get("product_capabilities_worked_in_staging") is not True
            or obj.get("customer_distribution_authorized") is not False
            or obj.get("operating_ucie_database_written") is not False
            or obj.get("customer_data_scanned") is not False
            or obj.get("automatic_rule_promotion") is not False
            or set(obj.get("pillars_exercised", [])) != set(PILLARS)
            or set(obj.get("workflows", {})) != set(PILLARS)):
        raise OfflineFullProductError("installed four-pillar workflow/guardrail drift")
    return {"first_party_four_pillars_synthetic_worked": True,
            "pillars_exercised": list(PILLARS),
            "customer_product_accepted": False,
            "workflow_receipt_sha256": sha256(
                json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()}


def _check_ui(output: str) -> dict:
    try:
        obj = json.loads(output)
    except (ValueError, TypeError) as exc:
        raise OfflineFullProductError("installed UCIE local UI probe not JSON") from exc
    if (type(obj) is not dict
            or obj.get("schema") != "UCIE_C1_PORTABLE_LOCALHOST_PREVIEW_V01"
            or obj.get("loopback_http_routes_checked") != 5
            or obj.get("negative_post_checked") is not True
            or obj.get("bound_host") != "127.0.0.1"
            or obj.get("task_scheduler_modified") is not False
            or obj.get("customer_distribution_authorized") is not False):
        raise OfflineFullProductError("installed UCIE local HTML/JSON contract failed")
    return {"installed_local_ui_loopback_routes_verified": 5,
            "negative_post_denial_checked": True,
            "customer_ui_acceptance_attested": False}


def run_owner_full_product(root: Path, consent: str) -> dict:
    """Explicit third consent; scratch source/wheel/venv never leave UCIE."""
    if consent != CONSENT:
        raise OfflineFullProductError("independent owner full-product consent missing")
    python = _owner_gate(root)
    hashes, dep_receipt_sha = _dependency_evidence(root)
    if (root / RECEIPT).exists() or (root / RECEIPT).is_symlink():
        raise OfflineFullProductError("previous full-product receipt cannot be replaced")
    closure = runtime.inspect_static_runtime_closure(root)
    if closure["missing_first_party_imports"]:
        raise OfflineFullProductError("incomplete first-party static import graph")
    sources = runtime._copy_payload(root, closure)
    if len(sources) < 23:
        raise OfflineFullProductError("incomplete UCIE full-component source snapshot")
    parent = root / "downloaded"
    if parent.is_symlink() or not parent.is_dir():
        raise OfflineFullProductError("Git-ignored UCIE scratch directory unavailable")
    environment = dependency._environment()  # no inherited external pip indexes
    with TemporaryDirectory(prefix="ucie_c1_full_product_", dir=parent) as folder:
        scratch = Path(folder)
        source = scratch / "source" / "UCIE"
        source.parent.mkdir()
        manifest = runtime._stage(source, sources, runtime.REVISION_A)
        runtime._verify(source, manifest)
        wheels = scratch / "first_party_wheel"
        wheels.mkdir()
        _run(_build_cmd(python, source, wheels), scratch, environment,
             "first-party UCIE wheel build")
        built = list(wheels.iterdir())
        if len(built) != 1:
            raise OfflineFullProductError("exactly one UCIE wheel required")
        wheel_info = _inspect_first_party_wheel(built[0], sources)
        requirements = scratch / "full-product-hash-locked.txt"
        require_text = _requirements(hashes, wheel_info["sha256"])
        requirements.write_text(require_text, encoding="ascii")
        venv = scratch / "recipient_venv"
        _run(dependency._venv_command(python, venv), scratch, environment,
             "disposable full-product venv creation")
        child = venv / "Scripts" / "python.exe"
        if child.is_symlink() or not child.is_file():
            raise OfflineFullProductError("isolated recipient Python missing")
        _run(_install_cmd(child, root / acquire.WHEELHOUSE, wheels,
                          requirements), scratch, environment,
             "hash-locked offline full-product install")
        _run([str(child), "-I", "-B", "-m", "pip", "--isolated",
              "check", "--disable-pip-version-check"], scratch, environment,
             "offline product dependency consistency")
        native = _check_native(_run([str(child), "-I", "-B", "-c", NATIVE_PROBE],
                                    scratch, environment, "native ABI trial"))
        four = _check_four_pillars(_run(
            [str(child), "-I", "-B", "-m", "ucie_miner.customer_staging_v01",
             "--pillar", "all"], scratch, environment,
            "installed four-pillar first-party CLI"))
        ui = _check_ui(_run([str(child), "-I", "-B", "-c", UI_PROBE, str(source)],
                            scratch, environment, "installed Local V04 UI"))
        # The wheel, installed venv and synthetic source are ephemeral.
    receipt = {
        "schema": SCHEMA, "status": STATUS,
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "observed_scope": "SAME_OWNER_WINDOWS_HOST_ISOLATED_PRODUCT_VENV",
        "dependency_only_receipt_sha256": dep_receipt_sha,
        "first_party_source_inventory_sha256": manifest["source_sha256"],
        "first_party_wheel_sha256": wheel_info["sha256"],
        "first_party_source_member_count": wheel_info["file_count"],
        "wheel_RECORD_verified": wheel_info["wheel_record_verified"],
        "first_party_wheel_source_bytes_equal": wheel_info["source_code_bytes_match"],
        "offline_install_requires_four_sha256_hashes": True,
        "offline_pip_check_succeeded": True,
        "native_probe": native,
        "four_pillar_installed_workflow": four,
        "local_v04_installed_ui": ui,
        "temporary_first_party_wheel_and_venv_removed": True,
        "owner_existing_venv_modified": False,
        "owner_resident_web_service_modified": False,
        "third_party_rights_or_signatures_approved": False,
        "complete_product_portability_attested": False,
        "different_full_product_version_update_rollback_attested": False,
        "second_clean_windows_host_accepted": False,
        "signed_customer_package_created": False,
        "customer_distribution_authorized": False,
        "operating_database_writes": 0,
        "scheduler_changes": 0,
    }
    dest = root / RECEIPT
    if dest.is_symlink() or dest.exists():
        raise OfflineFullProductError("C1 product receipt appeared during rehearsal")
    with dest.open("x", encoding="ascii") as stream:
        json.dump(receipt, stream, sort_keys=True, ensure_ascii=True)
        stream.write("\n")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE C1 owner-only full first-party offline product QA"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    try:
        if args.apply:
            _owner_gate(root)
            typed = input("Type " + CONSENT + " to run isolated full-product QA: ")
            result = run_owner_full_product(root, typed)
        else:
            result = preview(root)
    except (OfflineFullProductError, OSError, RuntimeError, ValueError, EOFError):
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_C1_FULL_PRODUCT_PREVIEW_FAIL_CLOSED_NO_GO",
            "owner_environment_modified": False,
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
