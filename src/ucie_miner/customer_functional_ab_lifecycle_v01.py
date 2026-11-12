"""UCIE C1 functional A/B slot transition, rollback and uninstall.

A (0.1.0): four-pillar UCIE wheel; B (0.1.1): same product PLUS real
installed four-pillar self-check. Both versions are SOURCE-DISTINCT.
Owner-only --apply installs third-party code in TWO throwaway offline venvs.
Neither a signed customer upgrade nor an independent recipient acceptance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import sys
import sysconfig
from tempfile import TemporaryDirectory

from . import customer_full_product_offline_rehearsal_v01 as full
from . import customer_offline_install_rehearsal_v01 as dep
from . import customer_owner_wheelhouse_acquire_v01 as vendor
from . import customer_runtime_closure_v01 as runtime
from .customer_staging_v01 import PILLARS

SCHEMA = "UCIE_C1_FUNCTIONAL_AB_DISPOSABLE_SLOTS_V01"
STATE = "C1_OWNER_HOST_PRODUCT_AB_CUSTOMER_NO_GO"
CONSENT = "RUN_UCIE_C1_FUNCTIONAL_AB_SLOTS_ONCE"
RECEIPT = "downloaded/ucie_c1_functional_ab_lifecycle_receipt_v01.json"
OWNER_ROOT = Path("D:/UCIE")
A_VERSION, B_VERSION = "0.1.0", "0.1.1"
B_SOURCE = "src/ucie_miner/customer_installed_health_v01.py"
SHA = re.compile("[0-9a-f]{64}\\Z")
VERSION_PROBE = """import json,sys,importlib.util,importlib.metadata
print(json.dumps({
 'version':importlib.metadata.version('ucie-public-only-demo'),
 'b_only_health_present':importlib.util.find_spec('ucie_miner.customer_installed_health_v01') is not None,
 'prefix':sys.prefix,
 'isolated':sys.prefix!=sys.base_prefix,
 'bits':64 if sys.maxsize>2**32 else 32},sort_keys=True))
"""
ABSENCE_PROBE = """import json,importlib.metadata,importlib.util
try: importlib.metadata.version('ucie-public-only-demo'); installed=True
except importlib.metadata.PackageNotFoundError: installed=False
package_present=importlib.util.find_spec('ucie_miner') is not None
print(json.dumps({'installed':installed,'ucie_module_still_present':package_present}))
"""


class ABRehearsalError(ValueError):
    """Never turn disposable A/B evidence into a customer release."""


def _previous_full_receipt(root: Path) -> str:
    file = root / full.RECEIPT
    if (file.parent.is_symlink() or file.is_symlink() or not file.is_file()
            or not 0 < file.stat().st_size <= full.MAX_RECEIPT):
        raise ABRehearsalError("prior full-product owner receipt absent")
    try:
        raw = file.read_bytes()
        doc = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise ABRehearsalError("prior full-product receipt invalid") from exc
    if (type(doc) is not dict or doc.get("schema") != full.SCHEMA
            or doc.get("status") != full.STATUS
            or doc.get("observed_scope") !=
            "SAME_OWNER_WINDOWS_HOST_ISOLATED_PRODUCT_VENV"
            or doc.get("first_party_wheel_source_bytes_equal") is not True
            or doc.get("wheel_RECORD_verified") is not True
            or doc.get("offline_install_requires_four_sha256_hashes") is not True
            or doc.get("offline_pip_check_succeeded") is not True
            or doc.get("temporary_first_party_wheel_and_venv_removed") is not True
            or doc.get("owner_existing_venv_modified") is not False
            or doc.get("customer_distribution_authorized") is not False
            or doc.get("second_clean_windows_host_accepted") is not False
            or type(doc.get("first_party_source_member_count")) is not int
            or doc["first_party_source_member_count"] < 190
            or type(doc.get("native_probe")) is not dict
            or doc["native_probe"].get("cryptography_aesgcm_roundtrip") is not True
            or type(doc.get("four_pillar_installed_workflow")) is not dict
            or doc["four_pillar_installed_workflow"].get(
                "first_party_four_pillars_synthetic_worked") is not True
            or type(doc.get("local_v04_installed_ui")) is not dict
            or doc["local_v04_installed_ui"].get(
                "installed_local_ui_loopback_routes_verified") != 5):
        raise ABRehearsalError("prior C1 technical gates not satisfied")
    earlier = root / dep.RECEIPT
    if (earlier.is_symlink() or not earlier.is_file()
            or doc.get("dependency_only_receipt_sha256") !=
            sha256(earlier.read_bytes()).hexdigest()):
        raise ABRehearsalError("dependency receipt evidence changed")
    return sha256(raw).hexdigest()


def preview(root: Path) -> dict:
    """Read-only, no pip, venv, wheel build, vendor import or network."""
    try:
        dep._valid_checkout(root)
    except (dep.OfflineInstallRehearsalError, OSError, ValueError) as exc:
        raise ABRehearsalError("exact UCIE-only checkout required") from exc
    state = "PREVIOUS_FULL_PRODUCT_RECEIPT_PENDING"
    verified = False
    target = root / RECEIPT
    if target.exists() or target.is_symlink():
        state = "PREVIOUS_AB_RECEIPT_PRESERVED"
    else:
        try:
            full._dependency_evidence(root)
            _previous_full_receipt(root)
            verified = True
            state = "READY_FOR_OWNER_FUNCTIONAL_AB_CONSENT"
        except (full.OfflineFullProductError, ABRehearsalError):
            pass
    return {
        "schema": SCHEMA, "status": STATE,
        "mode": "OFFLINE_READONLY_PREVIEW",
        "readiness": state, "prior_owner_product_verified": verified,
        "A": A_VERSION, "B": B_VERSION,
        "B_adds_real_installed_feature": "four_pillar_self_check",
        "source": "UCIE_LOCAL_SNAPSHOT_NOT_SIGNED_GIT_RELEASE",
        "owner_consent_phrase": CONSENT,
        "network_requests": 0, "subprocesses_executed": 0,
        "customer_distribution_authorized": False,
        "second_clean_windows_host_accepted": False,
    }


def _owner_gate(root: Path) -> Path:
    try:
        dep._valid_checkout(root)
        owner = (root / ".venv" / "Scripts" / "python.exe").resolve(strict=True)
        actual = Path(sys.executable).resolve(strict=True)
        correct = OWNER_ROOT.resolve(strict=True)
    except (OSError, ValueError, RuntimeError) as exc:
        raise ABRehearsalError("owner Python identity unavailable") from exc
    if (os.name != "nt" or root.resolve() != correct or actual != owner
            or sys.implementation.name != "cpython"
            or sys.version_info[:2] != (3, 15) or sys.maxsize <= 2**32
            or sysconfig.get_config_var("Py_GIL_DISABLED") not in (None, 0)
            or not sys.stdin.isatty() or bool(os.environ.get("CI"))):
        raise ABRehearsalError("interactive exact owner Windows x64 CPython3.15 required")
    if (root / RECEIPT).exists() or (root / RECEIPT).is_symlink():
        raise ABRehearsalError("previous A/B receipt cannot be overwritten")
    _previous_full_receipt(root)
    full._dependency_evidence(root)
    return actual


def _two_sources(source: dict[str, bytes]) -> tuple[dict, dict]:
    """One meaningful B-only callable; A is not a cosmetic marker."""
    if type(source) is not dict or B_SOURCE not in source:
        raise ABRehearsalError("B-only installed feature source absent")
    b_source = source[B_SOURCE]
    if (type(b_source) is not bytes or
            b"def run_installed_self_check()" not in b_source
            or b"customer_distribution_authorized" not in b_source
            or b"TEST_ONLY_B_VERSION" not in b_source):
        raise ABRehearsalError("B-only feature not source-attested")
    a, b = dict(source), dict(source)
    a.pop(B_SOURCE)
    if (len(a) + 1 != len(b) or B_SOURCE in a
            or "src/ucie_miner/customer_staging_v01.py" not in a):
        raise ABRehearsalError("A/B source delta incomplete")
    return a, b


def _verified_wheel(wheel: Path, source: dict, version: str, digest: str) -> dict:
    if (type(digest) is not str or SHA.fullmatch(digest) is None
            or wheel.is_symlink() or not wheel.is_file()
            or sha256(wheel.read_bytes()).hexdigest() != digest):
        raise ABRehearsalError("wheel candidate SHA256 mismatch")
    result = full._inspect_first_party_wheel(wheel, source, version=version)
    if result["sha256"] != digest or result["version"] != version:
        raise ABRehearsalError("first-party wheel version/RECORD mismatch")
    return result


def _select(scratch: Path, slot: str, hashes: dict[str, str]) -> None:
    """Atomic JSON pointer only in disposable scratch, never owner service."""
    if (slot not in ("A", "B") or set(hashes) != {"A", "B"}
            or any(SHA.fullmatch(v) is None for v in hashes.values())
            or scratch.is_symlink() or not scratch.is_dir()):
        raise ABRehearsalError("unsafe A/B selector or wheel hashes")
    item = scratch / "active-slot.new"
    active = scratch / "active-slot.json"
    if item.exists() or item.is_symlink() or active.is_symlink():
        raise ABRehearsalError("A/B selection path changed")
    payload = {"schema": SCHEMA, "status": STATE, "slot": slot,
               "wheel_sha256": hashes[slot], "customer_distribution_authorized": False}
    with item.open("x", encoding="ascii") as fd:
        json.dump(payload, fd, sort_keys=True)
    os.replace(item, active)
    _selected(scratch, slot, hashes)


def _selected(scratch: Path, slot: str, hashes: dict[str, str]) -> None:
    item = scratch / "active-slot.json"
    if item.is_symlink() or not item.is_file() or item.stat().st_size > 1024:
        raise ABRehearsalError("A/B pointer absent or symlinked")
    try:
        found = json.loads(item.read_text("ascii"))
    except (OSError, ValueError) as exc:
        raise ABRehearsalError("A/B active pointer unreadable") from exc
    if (type(found) is not dict or found != {
            "schema": SCHEMA, "status": STATE, "slot": slot,
            "wheel_sha256": hashes[slot], "customer_distribution_authorized": False}):
        raise ABRehearsalError("A/B active pointer tampered")


def _install(owner: Path, root: Path, folder: Path, wheel: Path,
             version: str, digest: str, hashes: dict, env: dict) -> Path:
    venv = folder / "recipient_venv"
    full._run(dep._venv_command(owner, venv), folder, env, "A/B new venv")
    child = venv / "Scripts" / "python.exe"
    if child.is_symlink() or not child.is_file():
        raise ABRehearsalError("A/B venv Python absent")
    req = folder / "full_hash_locks.txt"
    req.write_text(full._requirements(hashes, digest, version=version),
                   encoding="ascii")
    full._run(full._install_cmd(child, root / vendor.WHEELHOUSE,
                               wheel.parent, req),
              folder, env, "A/B offline hash-locked four wheel install")
    full._run([str(child), "-I", "-B", "-m", "pip", "--isolated",
               "check", "--disable-pip-version-check"],
              folder, env, "A/B pip dependency check")
    output = full._run([str(child), "-I", "-B", "-c", VERSION_PROBE],
                       folder, env, "A/B installed version")
    try:
        state = json.loads(output)
    except (ValueError, TypeError) as exc:
        raise ABRehearsalError("installed A/B version probe not JSON") from exc
    if (type(state) is not dict or state.get("version") != version
            or state.get("b_only_health_present") is not (version == B_VERSION)
            or state.get("isolated") is not True
            or state.get("bits") != 64 or state.get("prefix") != str(venv)):
        raise ABRehearsalError("A/B installed version or feature mismatch")
    return child


def _smoke(slot: str, child: Path, root: Path, folder: Path,
           env: dict) -> dict:
    """Run real installed UCIE four pillars and loopback V04 on both slots."""
    pillars = full._check_four_pillars(full._run(
        [str(child), "-I", "-B", "-m", "ucie_miner.customer_staging_v01",
         "--pillar", "all"], folder, env, "A/B four-pillar installed CLI"))
    ui = full._check_ui(full._run(
        [str(child), "-I", "-B", "-c", full.UI_PROBE, str(root)],
        folder, env, "A/B installed localhost UI"))
    feature_sha = None
    if slot == "B":
        try:
            data = json.loads(full._run(
                [str(child), "-I", "-B", "-m",
                 "ucie_miner.customer_installed_health_v01", "--self-check"],
                folder, env, "B-only installed four-pillar self-check"))
        except (ValueError, TypeError) as exc:
            raise ABRehearsalError("B-only self-check not JSON") from exc
        feature_sha = (data.get("four_pillar_synthetic_workflow_sha256")
                       if type(data) is dict else None)
        if (type(data) is not dict
                or data.get("schema") != "UCIE_C1_INSTALLED_FOUR_PILLAR_SELF_CHECK_V01"
                or data.get("installed_version") != B_VERSION
                or data.get("new_in_functional_version_b") is not True
                or data.get("installed_four_pillar_workflows_checked") is not True
                or data.get("customer_distribution_authorized") is not False
                or data.get("auto_promoted") is not False
                or data.get("customer_code_read") is not False
                or type(feature_sha) is not str or SHA.fullmatch(feature_sha) is None
                or type(data.get("four_pillars")) is not list
                or len(data["four_pillars"]) != len(PILLARS)
                or set(data["four_pillars"]) != set(PILLARS)):
            raise ABRehearsalError("B-only functional capability failed")
    return {"slot": slot, "four_pillars": pillars,
            "local_V04": ui, "B_only_workflow_sha256": feature_sha,
            "customer_distribution_authorized": False}


def _uninstall(child: Path, folder: Path, env: dict) -> None:
    full._run([str(child), "-I", "-B", "-m", "pip", "--isolated",
               "uninstall", "--yes", full.FIRST_PARTY_NAME],
              folder, env, "disposable UCIE product pip uninstall")
    try:
        state = json.loads(full._run(
            [str(child), "-I", "-B", "-c", ABSENCE_PROBE],
            folder, env, "confirm UCIE distribution absent"))
    except (ValueError, TypeError) as exc:
        raise ABRehearsalError("post-uninstall state invalid") from exc
    if (type(state) is not dict
            or state.get("installed") is not False
            or state.get("ucie_module_still_present") is not False):
        raise ABRehearsalError("UCIE product uninstall or module cleanup not verified")


def run_once(root: Path, typed_consent: str) -> dict:
    if typed_consent != CONSENT:
        raise ABRehearsalError("independent A/B owner consent not provided")
    owner = _owner_gate(root)
    previous_sha = _previous_full_receipt(root)
    vendor_sha = full._dependency_evidence(root)[0]
    graph = runtime.inspect_static_runtime_closure(root)
    if graph["missing_first_party_imports"]:
        raise ABRehearsalError("first-party static closure incomplete")
    a_src, b_src = _two_sources(runtime._copy_payload(root, graph))
    parent = root / "downloaded"
    if parent.is_symlink() or not parent.is_dir():
        raise ABRehearsalError("UCIE Git-ignored temporary parent absent")
    env = dep._environment()
    with TemporaryDirectory(prefix="ucie_c1_ab_slots_", dir=parent) as temp:
        scratch = Path(temp)
        slots = {}
        for slot, version, src in (("A", A_VERSION, a_src),
                                   ("B", B_VERSION, b_src)):
            folder = scratch / ("slot_" + slot)
            staged = folder / "source" / "UCIE"
            staged.parent.mkdir(parents=True)
            manifest = runtime._stage(staged, src, runtime.REVISION_A)
            runtime._verify(staged, manifest)
            out = folder / "wheel"
            out.mkdir()
            wheel = full._build_first_party_wheel(out, src, version=version)
            digest = sha256(wheel.read_bytes()).hexdigest()
            proof = _verified_wheel(wheel, src, version, digest)
            slots[slot] = {"folder": folder, "staged": staged, "wheel": wheel,
                           "version": version, "digest": digest,
                           "modules": proof["file_count"],
                           "source_sha256": manifest["source_sha256"]}
        hashes = {key: v["digest"] for key, v in slots.items()}
        if (hashes["A"] == hashes["B"] or
                slots["B"]["modules"] != slots["A"]["modules"] + 1):
            raise ABRehearsalError("A/B versions not actually source-distinct")
        # Negative candidate is a THROWAWAY copy; no live/approved wheel touched.
        damaged_dir = scratch / "tamper"
        damaged_dir.mkdir()
        damaged = damaged_dir / slots["B"]["wheel"].name
        shutil.copyfile(slots["B"]["wheel"], damaged)
        with damaged.open("ab") as fd:
            fd.write(b"UCIE_TAMPERED_CANDIDATE_NOT_TO_EXECUTE\n")
        rejected = False
        try:
            _verified_wheel(damaged, b_src, B_VERSION, hashes["B"])
        except ABRehearsalError:
            rejected = True
        if not rejected:
            raise ABRehearsalError("tampered B wheel was accepted")
        damaged.unlink()
        damaged_dir.rmdir()
        for slot in ("A", "B"):
            v = slots[slot]
            v["python"] = _install(owner, root, v["folder"], v["wheel"],
                                   v["version"], v["digest"], vendor_sha, env)
        _select(scratch, "A", hashes)
        a_initial = _smoke("A", slots["A"]["python"], slots["A"]["staged"],
                           slots["A"]["folder"], env)
        _selected(scratch, "A", hashes)
        b_candidate = _smoke("B", slots["B"]["python"], slots["B"]["staged"],
                             slots["B"]["folder"], env)
        _select(scratch, "B", hashes)
        _selected(scratch, "B", hashes)
        _select(scratch, "A", hashes)
        _selected(scratch, "A", hashes)
        a_rollback = _smoke("A", slots["A"]["python"], slots["A"]["staged"],
                            slots["A"]["folder"], env)
        for slot in ("B", "A"):
            _uninstall(slots[slot]["python"], slots[slot]["folder"], env)
        (scratch / "active-slot.json").unlink()
        evidence = {
            "A_wheel_sha256": hashes["A"], "B_wheel_sha256": hashes["B"],
            "A_source_sha256": slots["A"]["source_sha256"],
            "B_source_sha256": slots["B"]["source_sha256"],
            "A_first_party_modules": slots["A"]["modules"],
            "B_first_party_modules": slots["B"]["modules"],
            "A_initial": a_initial, "B_candidate": b_candidate,
            "A_rollback": a_rollback,
        }
    receipt = {
        "schema": SCHEMA, "status": STATE,
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "observed_scope": "SAME_OWNER_WINDOWS_TWO_DISPOSABLE_PRODUCT_VENVS",
        "previous_full_product_owner_receipt_sha256": previous_sha,
        "A": A_VERSION, "B": B_VERSION,
        "B_adds_real_installed_four_pillar_self_check": True,
        "two_first_party_product_wheels_functionally_distinct": True,
        "two_exact_vendor_and_product_sha_locked_offline_installs": True,
        "A_then_B_activation_then_A_rollback_tested": True,
        "tampered_B_candidate_rejected_before_activation": rejected,
        "four_pillars_and_local_UI_checked_in_both_versions": True,
        "two_first_party_pip_uninstalls_confirmed": True,
        "disposable_venvs_source_and_wheels_removed": True,
        "evidence": evidence,
        "signed_two_git_tagged_product_releases": False,
        "second_clean_windows_recipient_tested": False,
        "in_place_customer_upgrade_tested": False,
        "complete_signed_windows_installer_attested": False,
        "vendor_rights_or_SPDX_approved": False,
        "operating_database_writes": 0,
        "owner_resident_service_modified": False,
        "customer_distribution_authorized": False,
    }
    target = root / RECEIPT
    if target.exists() or target.is_symlink():
        raise ABRehearsalError("earlier A/B completion receipt cannot be overwritten")
    with target.open("x", encoding="ascii") as fd:
        json.dump(receipt, fd, sort_keys=True, ensure_ascii=True)
        fd.write("\n")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE C1 functional A/B local-only offline slot rehearsal"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    try:
        if args.apply:
            _owner_gate(root)
            consent = input("Type " + CONSENT + " for disposable A/B slot QA: ")
            result = run_once(root, consent)
        else:
            result = preview(root)
    except (ABRehearsalError, full.OfflineFullProductError,
            OSError, RuntimeError, ValueError, EOFError):
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_C1_AB_FAIL_CLOSED_CUSTOMER_NO_GO",
            "customer_distribution_authorized": False,
            "owner_service_modified": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
