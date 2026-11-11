"""UCIE C0/C1: full-component SOURCE inventory + disposable lifecycle exercise.

The existing wheel capsule covers only its installed Python entry point.  This
extends inspection to the fixed first-party UI, Windows owner scripts, policy,
CLI, four product pillars and documentation.  Never a customer installer:
the Windows scripts are owner-path-bound, dependencies/rights are unapproved,
and the two lifecycle generations intentionally use identical source bytes.
NO package publishing, signing, customer inputs, scheduled work or live writes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile

SCHEMA = "UCIE_C0_C1_FULL_COMPONENT_LIFECYCLE_PREVIEW_V01"
STATUS = "FULL_COMPONENT_STAGING_PREVIEW_ONLY_CUSTOMER_NO_GO"
MAX_FILE_BYTES = 256_000
MAX_TOTAL_BYTES = 3_000_000

# This is an auditable *known component census*, NOT an assertion that all
# imported transitive files or third-party runtime wheels are included.
GROUPS = {
    "error_prevention": (
        "src/ucie_miner/rule_candidates.py",
        "src/ucie_miner/regression_plans.py",
        "src/ucie_miner/guarded_scandir.py",
    ),
    "development_engines_and_skills": (
        "src/ucie_miner/capability_trials.py",
        "src/ucie_miner/positive_capability_discovery.py",
    ),
    "virtual_library_and_skillbooks": (
        "src/ucie_miner/skillbook_catalog_union_v01.py",
        "src/ucie_miner/mcp_prompts_guide_v01.py",
        "src/ucie_miner/python_scandir_guide_v01.py",
        "src/ucie_miner/python_scandir_pinned_playbook_v02.py",
    ),
    "continuous_evidence_evolution": (
        "src/ucie_miner/experience_evolution.py",
        "src/ucie_miner/p11_closed_loop.py",
    ),
    "local_ui": (
        "src/ucie_miner/local_v1_app_v01.py",
        "src/ucie_miner/local_v1_design_v04.py",
    ),
    "owner_windows_scripts_not_portable": (
        "scripts/start_ucie_local_v1.ps1",
        "scripts/run_ucie_local_v1_autostart.py",
        "scripts/status_ucie_local_v1_autostart.ps1",
    ),
    "product_cli_and_preview": (
        "src/ucie_miner/customer_staging_v01.py",
        "src/ucie_public/cli.py",
    ),
    "release_documents_and_configuration": (
        "pyproject.toml",
        "SECURITY.md",
        "docs/UCIE_FULL_PRODUCT_PRIVATE_CUSTOMER_RELEASE_V1.md",
        "docs/UCIE_BUNDLED_C0_C1_ROADMAP_20261108.md",
        "docs/UCIE_PYTHON_V315_PINNED_SCANDIR_PLAYBOOK_20261111.md",
    ),
}
PILLARS = (
    "error_prevention",
    "development_engines_and_skills",
    "virtual_library_and_skillbooks",
    "continuous_evidence_evolution",
)
FILES = tuple(sorted({name for names in GROUPS.values() for name in names}))
BLOCKERS = (
    "FIXED_CENSUS_NOT_COMPLETE_TRANSITIVE_PACKAGE_CLOSURE",
    "WINDOWS_OWNER_SCRIPTS_HARDCODED_PATHS_NOT_CUSTOMER_PORTABLE",
    "THIRD_PARTY_DEPENDENCY_WHEELHOUSE_AND_SBOM_NOT_INCLUDED",
    "FOUR_PILLAR_APPROVED_NON_DRAFT_ACCEPTANCE_MISSING",
    "SECURITY_RIGHTS_AND_CUSTOMER_CONTRACT_NOT_SIGNED_OFF",
    "CUSTOMER_LICENSE_AND_PUBLISHER_SIGNATURE_ABSENT",
    "NO_REAL_VERSIONED_CODE_UPDATE_OR_CLEAN_RECIPIENT_INSTALL",
    "NO_DESIGNATED_CUSTOMER_PILOT_OR_RELEASE_AUTHORIZATION",
)


class ComponentLifecycleError(ValueError):
    """Fail closed for a missing, changed, or unsafe first-party component."""


def _canon(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _root(root: Path) -> Path:
    if (not isinstance(root, Path)
            or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()
            or (root / ".git").is_symlink()
            or not (root / ".git").is_dir()):
        raise ComponentLifecycleError("exact first-party UCIE checkout required")
    return root


def _allowed_path(name: str) -> tuple[str, ...]:
    if type(name) is not str or name not in FILES:
        raise ComponentLifecycleError("unknown inventory path")
    parts = tuple(name.split("/"))
    if (not parts or any(x in ("", ".", "..") for x in parts)
            or "\\" in name or name.startswith("/")):
        raise ComponentLifecycleError("unsafe first-party relative path")
    return parts


def _payload(root: Path) -> dict[str, bytes]:
    root = _root(root)
    if len(FILES) != sum(len(xs) for xs in GROUPS.values()) or len(FILES) > 40:
        raise ComponentLifecycleError("duplicate/oversized component census")
    result: dict[str, bytes] = {}
    total = 0
    for relative in FILES:
        current = root
        for part in _allowed_path(relative):
            current = current / part
            if current.is_symlink():
                raise ComponentLifecycleError("symlinked component forbidden")
        if not current.is_file():
            raise ComponentLifecycleError("required first-party component missing")
        size = current.stat().st_size
        if not 0 < size <= MAX_FILE_BYTES:
            raise ComponentLifecycleError("unexpected first-party component size")
        raw = current.read_bytes()
        if len(raw) != size:
            raise ComponentLifecycleError("source size changed during read")
        total += size
        if total > MAX_TOTAL_BYTES:
            raise ComponentLifecycleError("component census read budget exceeded")
        result[relative] = raw
    return result


def _manifest(payload: dict[str, bytes]) -> dict:
    if tuple(sorted(payload)) != FILES:
        raise ComponentLifecycleError("full source census incomplete")
    entries = [
        {"path": name, "size": len(payload[name]),
         "sha256": sha256(payload[name]).hexdigest()}
        for name in FILES
    ]
    source_fingerprint = sha256(_canon(entries)).hexdigest()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "first_party_file_count": len(FILES),
        "first_party_source_fingerprint_sha256": source_fingerprint,
        "source_fingerprint_is_git_commit": False,
        "groups": {group: list(paths) for group, paths in GROUPS.items()},
        "four_pillars_present_in_census": list(PILLARS),
        "entries": entries,
        "includes_local_ui_sources": True,
        "includes_owner_windows_scripts_for_inventory_only": True,
        "windows_owner_scripts_customer_portable": False,
        "transitive_python_package_closure_attested": False,
        "dependencies_included": False,
        "sbom_complete": False,
        "customer_licensing_cleared": False,
        "signed_by_owner": False,
        "customer_distribution_authorized": False,
        "customer_data_read": False,
        "other_project_access": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "task_scheduler_changes": 0,
        "blockers": list(BLOCKERS),
    }


def inspect_component_census(root: Path) -> dict:
    """Read only fixed UCIE files; disclose metadata rather than file bytes."""
    return _manifest(_payload(root))


def _stage(slot: Path, payload: dict[str, bytes], manifest: dict) -> None:
    if slot.exists() or slot.is_symlink():
        raise ComponentLifecycleError("staging slot already exists")
    slot.mkdir()
    for relative in FILES:
        destination = slot.joinpath(*_allowed_path(relative))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload[relative])
    (slot / "manifest.json").write_bytes(_canon(manifest))


def _verify(slot: Path, payload: dict[str, bytes], manifest: dict) -> None:
    if not slot.is_dir() or slot.is_symlink():
        raise ComponentLifecycleError("staging slot absent or unsafe")
    names = set()
    for item in slot.rglob("*"):
        if item.is_symlink():
            raise ComponentLifecycleError("symlink in disposable staging")
        if item.is_file():
            names.add(item.relative_to(slot).as_posix())
    if names != (set(FILES) | {"manifest.json"}):
        raise ComponentLifecycleError("staging files missing or unexpected")
    if (slot / "manifest.json").read_bytes() != _canon(manifest):
        raise ComponentLifecycleError("manifest tampered")
    for relative in FILES:
        destination = slot.joinpath(*_allowed_path(relative))
        raw = destination.read_bytes()
        if raw != payload[relative]:
            raise ComponentLifecycleError("staged first-party content tampered")


def exercise_disposable_lifecycle(root: Path) -> dict:
    """Rehearse copy, detected tampering, update, rollback and removal.

    This is NOT a real version change: both generations share identical
    first-party source content. Each target lives inside a fresh temporary
    UCIE-only scratch directory. Never acts on D:/UCIE/runtime or installed app.
    """
    payload = _payload(root)
    manifest = _manifest(payload)
    with tempfile.TemporaryDirectory(prefix="UCIE_C0_C1_SAFE_PREVIEW_") as folder:
        scratch = Path(folder)
        slot_a, slot_b = scratch / "generation_a", scratch / "generation_b"
        _stage(slot_a, payload, manifest)
        _verify(slot_a, payload, manifest)
        _stage(slot_b, payload, manifest)
        # Corrupt ONLY the staged disposable copy, then fail before activation.
        target = slot_b.joinpath(*_allowed_path(FILES[0]))
        target.write_bytes(target.read_bytes() + b"UCIE_TAMPER_FIXTURE")
        failure_detected = False
        try:
            _verify(slot_b, payload, manifest)
        except ComponentLifecycleError:
            failure_detected = True
        if not failure_detected:
            raise ComponentLifecycleError("tampered staging wrongly accepted")
        _verify(slot_a, payload, manifest)
        shutil.rmtree(slot_b)
        _stage(slot_b, payload, manifest)
        _verify(slot_b, payload, manifest)
        active = slot_b
        _verify(active, payload, manifest)
        active = slot_a
        _verify(active, payload, manifest)
        # Both copies are owned by this isolated TemporaryDirectory only.
        shutil.rmtree(slot_b)
        shutil.rmtree(slot_a)
        clean = not any(scratch.iterdir())
        if not clean:
            raise ComponentLifecycleError("disposable uninstall left files")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "source_fingerprint_sha256":
            manifest["first_party_source_fingerprint_sha256"],
        "source_file_count": len(FILES),
        "install_copy_and_manifest_verified": True,
        "tampered_staging_rejected_before_activation": failure_detected,
        "update_generation_switched_and_verified": True,
        "rollback_generation_restored_and_verified": True,
        "disposable_uninstall_clean": clean,
        "actual_code_version_changed": False,
        "actual_customer_installer_executed": False,
        "customer_release_artifact_created": False,
        "dependencies_included": False,
        "signed_by_owner": False,
        "customer_distribution_authorized": False,
        "customer_data_read": False,
        "other_project_access": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "task_scheduler_changes": 0,
        "blockers": list(BLOCKERS),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE fixed first-party complete component C0/C1 preview"
    )
    parser.add_argument("--ucie-root", type=Path, required=True)
    parser.add_argument("--disposable-lifecycle", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = (exercise_disposable_lifecycle(args.ucie_root)
                  if args.disposable_lifecycle
                  else inspect_component_census(args.ucie_root))
    except (ComponentLifecycleError, OSError, ValueError):
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_C0_C1_FAIL_CLOSED_CUSTOMER_NO_GO",
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0  # technical dry-run success, NEVER a commercial release signal


if __name__ == "__main__":
    raise SystemExit(main())
