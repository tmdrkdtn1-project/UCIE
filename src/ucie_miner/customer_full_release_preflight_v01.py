"""UCIE complete four-pillar proprietary customer-release READ-ONLY preflight.

Only fixed first-party UCIE code/test paths are inspected. This inventory is
NOT code QA, a contract, a license, signed artifact, customer acceptance or
permission to send anything. It always fails closed until real independent
product and commercial approvals exist outside this report.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

SCHEMA = "UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_READINESS_V01"
NO_GO = "UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO"
DISTRIBUTION = "PRIVATE_DESIGNATED_CUSTOMERS_PROPRIETARY"
MAX_FILE_BYTES = 200_000
# Exactly four equal product pillars: code+tests existence alone is not QA.
PILLAR_FILES = {
    "error_prevention": (
        "src/ucie_miner/rule_candidates.py",
        "src/ucie_miner/regression_plans.py",
        "tests/test_ucie_guarded_scandir.py",
    ),
    "development_engines_and_skills": (
        "src/ucie_miner/positive_capability_discovery.py",
        "src/ucie_miner/capability_trials.py",
        "tests/test_ucie_capability_trials.py",
    ),
    "virtual_library_and_skillbooks": (
        "src/ucie_miner/skillbook_editorial_production_v01.py",
        "src/ucie_miner/skillbook_catalog_union_v01.py",
        "tests/test_ucie_v1_integrated_product_acceptance.py",
    ),
    "continuous_evidence_evolution": (
        "src/ucie_miner/experience_evolution.py",
        "src/ucie_miner/p11_closed_loop.py",
        "tests/test_ucie_p11_closed_loop.py",
    ),
}
REQUIRED_FOUNDATION = (
    "src/ucie_miner/source_registry.py",
    "src/ucie_miner/public_source_adapter.py",
    "src/ucie_miner/product_v1.py",
    "src/ucie_public/cli.py",
    "pyproject.toml",
    "SECURITY.md",
)
PENDING_GATES = (
    "FOUR_PILLARS_REAL_CUSTOMER_END_TO_END_NOT_ATTESTED",
    "HUMAN_AND_MACHINE_SKILLBOOKS_NOT_APPROVED_FOR_CUSTOMER_EXPORT",
    "COMPLETE_PRIVATE_CUSTOMER_INSTALLER_AND_ROLLBACK_NOT_ATTESTED",
    "COPYRIGHT_DEPENDENCY_LICENSE_AND_CUSTOMER_CONTRACT_NOT_ATTESTED",
    "PRODUCT_SECURITY_AND_TARGET_PLATFORM_QA_NOT_ATTESTED",
    "CUSTOMER_BOUND_SIGNED_RELEASE_MANIFEST_NOT_ATTESTED",
    "ISOLATED_CUSTOMER_PILOT_ACCEPTANCE_NOT_ATTESTED",
)


def _first_party_file(root: Path, relative: str) -> tuple[str | None, str | None]:
    """No directory traversal, no symlinks and no files outside exact UCIE."""
    if not relative.startswith(("src/ucie_miner/", "src/ucie_public/",
                                "tests/", "pyproject.toml", "SECURITY.md")):
        return None, "UNAPPROVED_PATH"
    target = root.joinpath(*relative.split("/"))
    try:
        if not target.is_relative_to(root):
            return None, "OUTSIDE_ROOT"
        if any(p.is_symlink() for p in (target, *tuple(target.parents)[:3])):
            return None, "SYMLINK_NOT_ALLOWED"
        if not target.is_file():
            return None, "FILE_NOT_AVAILABLE"
        if target.stat().st_size > MAX_FILE_BYTES or target.stat().st_size == 0:
            return None, "UNSAFE_FIRST_PARTY_FILE_SIZE"
        data = target.read_bytes()
        if not data or len(data) > MAX_FILE_BYTES:
            return None, "UNSAFE_FIRST_PARTY_FILE_SIZE"
        return sha256(data).hexdigest(), None
    except (OSError, ValueError):
        return None, "UNREADABLE_FIRST_PARTY_FILE"


def inspect_customer_full_release(root: Path) -> dict:
    """Surface exact technical evidence without ever claiming release GO."""
    # No customer names, IDs, addresses, license keys, or customer source
    # are inputs to this public-repository preflight.
    report = {
        "schema": SCHEMA,
        "status": NO_GO,
        "distribution": DISTRIBUTION,
        "complete_product_required": True,
        "single_rule_release_is_not_full_product": True,
        "pillar_count_required": 4,
        "pillars": {},
        "foundations": {},
        "blocker_codes": list(PENDING_GATES),
        "customer_license_issued": False,
        "customer_bundle_signed": False,
        "actual_customer_receipt_verified": False,
        "private_distribution_executed": False,
        "public_package_published": False,
        "approved_skillbook_export_executed": False,
        "runtime_database_writes": 0,
        "task_scheduler_changes": 0,
        "customer_data_read": False,
        "other_project_access": False,
    }
    if not isinstance(root, Path) or root.is_symlink() or root.name.casefold() != "ucie":
        report["blocker_codes"].append("NOT_EXACT_UCIE_CHECKOUT")
        return report
    try:
        resolved = root.resolve(strict=True)
        if resolved != root.resolve() or not (root / ".git").is_dir():
            report["blocker_codes"].append("UCIE_GIT_CHECKOUT_UNVERIFIED")
            return report
    except (OSError, ValueError):
        report["blocker_codes"].append("UCIE_GIT_CHECKOUT_UNVERIFIED")
        return report
    for pillar, members in PILLAR_FILES.items():
        files = {}
        for path in members:
            digest, failure = _first_party_file(root, path)
            files[path] = {"sha256": digest, "file_problem": failure}
        complete = all(entry["sha256"] is not None for entry in files.values())
        report["pillars"][pillar] = {
            "first_party_file_inventory_present": complete,
            "test_file_present_not_test_execution": complete,
            "real_customer_end_to_end_accepted": False,
            "rights_security_and_signing_approved": False,
            "files": files,
        }
        if not complete:
            report["blocker_codes"].append(
                "MISSING_OR_UNSAFE_FIRST_PARTY_SURFACE:" + pillar
            )
    for path in REQUIRED_FOUNDATION:
        digest, failure = _first_party_file(root, path)
        report["foundations"][path] = {
            "sha256": digest, "file_problem": failure,
        }
        if digest is None:
            report["blocker_codes"].append(
                "MISSING_OR_UNSAFE_FOUNDATION:" + path
            )
    # This is a policy marker, NOT a legal conclusion. No external source,
    # customer contract or third-party legal document is read.
    report["proprietary_license_and_recipient_terms_approved"] = False
    report["four_pillar_source_inventory_present"] = (
        len(report["pillars"]) == 4 and all(
            row["first_party_file_inventory_present"]
            for row in report["pillars"].values()
        )
    )
    report["first_party_file_sha256_count"] = sum(
        entry["sha256"] is not None for row in report["pillars"].values()
        for entry in row["files"].values()
    ) + sum(
        entry["sha256"] is not None for entry in report["foundations"].values()
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE complete product designated-customer NO-GO preview"
    )
    parser.add_argument("--ucie-root", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(
        inspect_customer_full_release(args.ucie_root),
        sort_keys=True, ensure_ascii=True,
    ))
    return 2  # Never auto-authorize commercial delivery.


if __name__ == "__main__":
    raise SystemExit(main())
