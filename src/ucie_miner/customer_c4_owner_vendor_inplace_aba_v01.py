"""C4 single-venv real vendor-inclusive A->B->A trial; UCIE OWNER ONLY.

This is not a Windows installer, signed distribution, second-recipient test,
license/NOTICE clearance or customer launch. A strict separate interactive
owner consent is required before ANY pip or vendor import. Only three already
SHA/RECORD-captured local wheels and two immutable UCIE Git commits are used.
No network/fetch, new collector, other project, owner service, DB or task writes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sys
import sysconfig
from tempfile import TemporaryDirectory

from . import customer_c2_supply_chain_review_v01 as c2
from . import customer_functional_ab_lifecycle_v01 as ab
from . import customer_full_product_offline_rehearsal_v01 as full
from . import customer_offline_install_rehearsal_v01 as dep
from . import customer_owner_wheelhouse_acquire_v01 as vendor
from . import customer_pinned_git_source_v01 as pin
from . import customer_runtime_closure_v01 as runtime

SCHEMA = "UCIE_C4_OWNER_ONLY_VENDOR_INPLACE_ABA_V01"
CONSENT = "RUN_UCIE_C4_OWNER_DISPOSABLE_VENDOR_ABA_ONCE"
RECEIPT = "downloaded/ucie_c4_owner_vendor_inplace_aba_receipt_v01.json"
ROOT = Path("D:/UCIE")
STATUS = "C4_SAME_OWNER_VENDOR_INPLACE_ABA_TEST_ONLY_CUSTOMER_NO_GO"
STAGES = ("A_initial", "B_inplace_update", "A_inplace_rollback")


class C4OwnerTrialError(ValueError):
    """A local technical QA gate that cannot authorize any customer release."""


def _checked_venv_version(raw: str, expected: str, venv: Path) -> dict:
    if expected not in pin.VERSION.values() or not isinstance(venv, Path):
        raise C4OwnerTrialError("unexpected tested version or recipient type")
    try:
        data = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise C4OwnerTrialError("installed version probe is not JSON") from exc
    if (type(data) is not dict or data.get("version") != expected
            or data.get("b_only_health_present") is not (
                expected == pin.VERSION["B"]
            )
            or data.get("isolated") is not True
            or data.get("bits") != 64
            or type(data.get("prefix")) is not str
            or Path(data["prefix"]).resolve() != venv.resolve()):
        raise C4OwnerTrialError("installed recipient/version/B-only feature drift")
    return {
        "installed_version": expected,
        "B_only_feature_present": expected == pin.VERSION["B"],
        "same_installed_venv": True,
    }


def _verified_capture(root: Path) -> dict[str, str]:
    try:
        captured = vendor.verify_local(root)
        c2report = c2.inspect_c2(root)
        hashes, _ = full._dependency_evidence(root)
        ab._previous_full_receipt(root)
    except (vendor.WheelAcquisitionError, c2.C2ReviewError,
            full.OfflineFullProductError, ab.ABRehearsalError,
            OSError, ValueError) as exc:
        raise C4OwnerTrialError("prior UCIE owner C1/C2 vendor byte proof absent") from exc
    if (captured.get("all_local_bytes_match_captured_pypi_digests") is not True
            or c2report.get("c2_approved") is not False
            or c2report.get("customer_distribution_authorized") is not False
            or c2report.get("package_count") != len(vendor.PINNED)
            or set(hashes) != {name for name, _ in vendor.PINNED}
            or any(type(val) is not str or ab.SHA.fullmatch(val) is None
                   for val in hashes.values())):
        raise C4OwnerTrialError("C2 vendor exact captured pin gate mismatch")
    return hashes


def inspect_readonly(root: Path) -> dict:
    """Read UCIE-only evidence; no wheel build, venv/pip, vendor import or write."""
    try:
        dep._valid_checkout(root)
    except (dep.OfflineInstallRehearsalError, ValueError, OSError) as exc:
        raise C4OwnerTrialError("exact UCIE checkout required") from exc
    gates = {
        "three_existing_owner_captured_vendor_wheels_and_prior_C1": False,
        "two_pinned_public_UCIE_Git_object_trees": False,
        "new_one_time_receipt_destination": False,
    }
    dest = root / RECEIPT
    gates["new_one_time_receipt_destination"] = (
        not dest.exists() and not dest.is_symlink()
        and not dest.parent.is_symlink() and dest.parent.is_dir()
    )
    try:
        _verified_capture(root)
        gates["three_existing_owner_captured_vendor_wheels_and_prior_C1"] = True
    except C4OwnerTrialError:
        pass
    try:
        proof = pin.probe_git_objects(root)
        gates["two_pinned_public_UCIE_Git_object_trees"] = (
            proof.get("pinned_both_git_trees_verified") is True
        )
    except (pin.PinnedSourceError, OSError, ValueError):
        pass
    ready = all(gates.values())
    return {
        "schema": SCHEMA, "status": STATUS,
        "readiness": ("READY_FOR_EXPLICIT_OWNER_CONSENT_LOCAL_TEST_ONLY"
                      if ready else "PREREQUISITES_MISSING_NO_GO"),
        "gates": gates,
        "pinned_source_commits": {x: pin.PINNED[x][0] for x in ("A", "B")},
        "pinned_vendor_versions": {n: v for n, v in vendor.PINNED},
        "one_recipient_inplace_A_B_A_actual_vendor_test_executed": False,
        "external_network_calls": 0, "third_party_code_executed": False,
        "operating_database_writes": 0, "owner_service_or_task_changed": False,
        "third_party_legal_or_security_approved": False,
        "customer_distribution_authorized": False,
    }


def _owner_gate(root: Path) -> Path:
    try:
        dep._valid_checkout(root)
        approved_root = ROOT.resolve(strict=True)
        owner = (root / ".venv" / "Scripts" / "python.exe").resolve(strict=True)
        running = Path(sys.executable).resolve(strict=True)
    except (dep.OfflineInstallRehearsalError, OSError, RuntimeError) as exc:
        raise C4OwnerTrialError("owner root/Python identity unavailable") from exc
    if (os.name != "nt" or root.resolve() != approved_root
            or owner != running or sys.implementation.name != "cpython"
            or sys.version_info[:2] != (3, 15)
            or sys.maxsize <= 2**32
            or sysconfig.get_config_var("Py_GIL_DISABLED") not in (None, 0)
            or not sys.stdin.isatty() or bool(os.environ.get("CI"))):
        raise C4OwnerTrialError("exact interactive owner Windows Python3.15 required")
    if (root / RECEIPT).exists() or (root / RECEIPT).is_symlink():
        raise C4OwnerTrialError("previous C4 owner trial receipt may not be overwritten")
    if not (root / "downloaded").is_dir() or (root / "downloaded").is_symlink():
        raise C4OwnerTrialError("UCIE-only temp parent unavailable")
    return owner


def _build_two_pinned(root: Path, scratch: Path) -> dict:
    try:
        _, rows = pin._load_manifest(root)
        slots = {}
        for label in ("A", "B"):
            # Source pinned to literal reviewed Git commits, never owner dirty files.
            source = pin._git_clean_source(root, rows, label)
            folder = scratch / ("slot_" + label)
            stage = folder / "source" / "UCIE"
            stage.parent.mkdir(parents=True)
            proof = runtime._stage(stage, source, runtime.REVISION_A)
            runtime._verify(stage, proof)
            out = folder / "wheels"
            out.mkdir()
            wheel = full._build_first_party_wheel(
                out, source, version=pin.VERSION[label])
            pin._canonical_first_party_wheel(wheel)
            result = full._inspect_first_party_wheel(
                wheel, source, version=pin.VERSION[label])
            expected_digest = pin.CANONICAL_QA_SHA256[label]
            if (result.get("sha256") != expected_digest
                    or sha256(wheel.read_bytes()).hexdigest() != expected_digest
                    or result.get("source_code_bytes_match") is not True
                    or result.get("wheel_record_verified") is not True
                    or result.get("file_count") != pin.PINNED[label][2]):
                raise C4OwnerTrialError("reviewed pinned source/wheel byte mismatch")
            slots[label] = {
                "source": stage, "wheel": wheel, "version": pin.VERSION[label],
                "digest": expected_digest, "modules": result["file_count"],
            }
    except (pin.PinnedSourceError, full.OfflineFullProductError,
            runtime.ClosurePreviewError, OSError, ValueError) as exc:
        raise C4OwnerTrialError("two pinned first-party source build failed") from exc
    if (slots["A"]["digest"] == slots["B"]["digest"]
            or slots["A"]["modules"] != 182 or slots["B"]["modules"] != 184):
        raise C4OwnerTrialError("meaningful A/B pinned source changes not observed")
    return slots


def _phase(label: str, child: Path, venv: Path, slot: dict,
           root: Path, scratch: Path, vendor_hashes: dict, env: dict) -> dict:
    if label not in ("A", "B") or sha256(slot["wheel"].read_bytes()).hexdigest() != slot["digest"]:
        raise C4OwnerTrialError("candidate wheel identity drift before pip")
    requirements = scratch / "pinned_current_phase_requirements.txt"
    if requirements.is_symlink():
        raise C4OwnerTrialError("requirements path is symlink")
    requirements.write_text(
        full._requirements(
            vendor_hashes, slot["digest"], version=slot["version"]),
        encoding="ascii"
    )
    command = full._install_cmd(
        child, root / vendor.WHEELHOUSE, slot["wheel"].parent, requirements)
    if ("--require-hashes" not in command or "--no-index" not in command
            or "--find-links" not in command or "--no-input" not in command):
        raise C4OwnerTrialError("missing offline hash-bound vendor install gate")
    full._run(command, scratch, env, "owner C4 offline vendor-inclusive in-place pip")
    full._run(
        [str(child), "-I", "-B", "-m", "pip", "--isolated", "check",
         "--disable-pip-version-check"],
        scratch, env, "owner C4 vendor transitive pip dependency check")
    state = _checked_venv_version(
        full._run([str(child), "-I", "-B", "-c", ab.VERSION_PROBE],
                  scratch, env, "owner C4 installed version"),
        slot["version"], venv)
    native = full._check_native(full._run(
        [str(child), "-I", "-B", "-c", full.NATIVE_PROBE],
        scratch, env, "owner C4 native vendor isolated probe"))
    smoke = ab._smoke(label, child, slot["source"], scratch, env)
    if (native.get("cryptography_aesgcm_roundtrip") is not True
            or native.get("cffi_declaration_parsed") is not True
            or native.get("pycparser_c_declaration_parsed") is not True
            or smoke["local_V04"]["installed_local_ui_loopback_routes_verified"] != 5
            or smoke["four_pillars"]["first_party_four_pillars_synthetic_worked"] is not True
            or smoke["customer_distribution_authorized"] is not False):
        raise C4OwnerTrialError("installed UI/four-pillar/native vendor mismatch")
    return {
        "installed_version": state["installed_version"],
        "B_only_feature_present": state["B_only_feature_present"],
        "native_AEAD_cffi_pycparser_checked": True,
        "four_pillar_synthetic": smoke["four_pillars"]["workflow_receipt_sha256"],
        "local_V04_real_GET_routes": 5,
        "local_V04_POST_denied": smoke["local_V04"]["negative_post_denial_checked"],
        "B_only_workflow_sha256": smoke["B_only_workflow_sha256"],
        "customer_distribution_authorized": False,
    }


def run_owner_once(root: Path, *, typed_consent: str) -> dict:
    """Actual vendor install requires exact typed owner consent, always local."""
    if type(typed_consent) is not str or typed_consent != CONSENT:
        raise C4OwnerTrialError("independent explicit C4 vendor execution consent absent")
    owner = _owner_gate(root)
    plan = inspect_readonly(root)
    if plan["readiness"] != "READY_FOR_EXPLICIT_OWNER_CONSENT_LOCAL_TEST_ONLY":
        raise C4OwnerTrialError("C4 owner exact existing evidence gates not ready")
    hashes = _verified_capture(root)
    env = dep._environment()
    parent = root / "downloaded"
    with TemporaryDirectory(prefix="ucie_c4_owner_vendor_inplace_aba_", dir=parent) as temp:
        scratch = Path(temp)
        slots = _build_two_pinned(root, scratch)
        # Corrupt candidate rejected BEFORE any pip/vendor execution.
        bad = scratch / "bad_B"
        bad.mkdir()
        candidate = bad / slots["B"]["wheel"].name
        shutil.copyfile(slots["B"]["wheel"], candidate)
        with candidate.open("ab") as stream:
            stream.write(b"UCIE_FORGED_B_NEVER_INSTALL\n")
        try:
            ab._verified_wheel(candidate, pin._git_clean_source(
                root, pin._load_manifest(root)[1], "B"),
                pin.VERSION["B"], pin.CANONICAL_QA_SHA256["B"])
        except ab.ABRehearsalError:
            rejected = True
        else:
            rejected = False
        if not rejected:
            raise C4OwnerTrialError("tampered B candidate not blocked before pip")
        candidate.unlink()
        bad.rmdir()
        recipient = scratch / "single_real_vendor_recipient"
        full._run(dep._venv_command(owner, recipient), scratch, env,
                  "owner C4 new one-shot isolated recipient")
        child = recipient / "Scripts" / "python.exe"
        if child.is_symlink() or not child.is_file():
            raise C4OwnerTrialError("new isolated vendor recipient Python unavailable")
        runs = {}
        for stage, label in zip(STAGES, ("A", "B", "A")):
            runs[stage] = _phase(
                label, child, recipient, slots[label], root, scratch, hashes, env)
        if runs["A_initial"] != runs["A_inplace_rollback"]:
            raise C4OwnerTrialError("actual vendor-inclusive A rollback not equivalent")
        if not runs["B_inplace_update"]["B_only_feature_present"]:
            raise C4OwnerTrialError("real B-only feature absent after in-place update")
        ab._uninstall(child, scratch, env)
        result = {
            "schema": SCHEMA,
            "status": "C4_SAME_OWNER_DISPOSABLE_VENDOR_INPLACE_ABA_TECHNICAL_PASS_NO_GO",
            "pinned_source_commits": {x: pin.PINNED[x][0] for x in ("A", "B")},
            "first_party_qa_wheel_sha256": {
                x: slots[x]["digest"] for x in ("A", "B")},
            "vendor_versions": {n: v for n, v in vendor.PINNED},
            "observations": runs,
            "same_real_windows_venv_A_B_A_and_actual_uninstall": True,
            "corrupt_B_rejected_before_install": True,
            "all_3_vendor_wheels_used_from_existing_C1_local_capture": True,
            "external_downloads": 0,
            "first_party_and_vendor_binary_artifacts_copied_for_customer": False,
            "separate_owner_managed_clean_windows_recipient_tested": False,
            "first_party_private_release_signed": False,
            "vendor_redistribution_security_and_NOTICE_cleared": False,
            "full_commercial_customer_accepted": False,
            "customer_distribution_authorized": False,
            "operating_database_writes": 0,
            "owner_running_service_or_schedulers_modified": False,
            "disposable_venv_removed": True,
        }
    dest = root / RECEIPT
    if dest.exists() or dest.is_symlink():
        raise C4OwnerTrialError("one-time owner receipt appeared during test")
    with dest.open("x", encoding="ascii") as file:
        json.dump(result, file, sort_keys=True, ensure_ascii=True)
        file.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE owner-only true vendor A/B/A")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--inspect", action="store_true")
    group.add_argument("--owner-run-once", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    try:
        if args.owner_run_once:
            typed = input("Type exact " + CONSENT + ": ")
            outcome = run_owner_once(root, typed_consent=typed)
        else:
            outcome = inspect_readonly(root)
    except (C4OwnerTrialError, OSError, ValueError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "C4_OWNER_VENDOR_INPLACE_FAIL_CLOSED",
            "failure_class": type(exc).__name__,
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(outcome, sort_keys=True, ensure_ascii=True))
    return 0 if args.owner_run_once else 2


if __name__ == "__main__":
    raise SystemExit(main())
