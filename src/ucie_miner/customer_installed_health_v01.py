"""UCIE C1 B-side installed-product self-check: real NEW first-party capability.

This module is deliberately missing from disposable product version A (0.1.0)
and included in disposable B (0.1.1). It performs the existing real UCIE
four-pillar workflows exclusively on synthetic UCIE-owned input; never
inspects project/customer paths, installs packages or approves a customer.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json

from .customer_staging_v01 import PILLARS, run_four_pillar_staging

SCHEMA = "UCIE_C1_INSTALLED_FOUR_PILLAR_SELF_CHECK_V01"
TEST_ONLY_B_VERSION = "0.1.1"
PRODUCT_DISTRIBUTION = "ucie-public-only-demo"


class InstalledHealthError(ValueError):
    """No automatic product, policy or customer approval."""


def run_installed_self_check() -> dict:
    """A real B-only product function, not merely an A/B revision marker."""
    try:
        installed_version = version(PRODUCT_DISTRIBUTION)
    except PackageNotFoundError as exc:
        raise InstalledHealthError("first-party wheel is not installed") from exc
    if installed_version != TEST_ONLY_B_VERSION:
        raise InstalledHealthError("disposable B version is not installed")
    observed = run_four_pillar_staging(pillar="all", query="")
    if (type(observed) is not dict
            or observed.get("schema") != "UCIE_FOUR_PILLAR_INSTALLED_STAGING_V01"
            or observed.get("four_pillars_exercised") is not True
            or observed.get("product_capabilities_worked_in_staging") is not True
            or observed.get("customer_distribution_authorized") is not False
            or observed.get("automatic_rule_promotion") is not False
            or observed.get("customer_data_scanned") is not False
            or observed.get("operating_ucie_database_written") is not False
            or observed.get("complete_customer_functional_acceptance") is not False
            or set(observed.get("workflows", {})) != set(PILLARS)):
        raise InstalledHealthError("one or more installed UCIE pillars failed closed")
    digest = sha256(json.dumps(
        observed, sort_keys=True, ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")).hexdigest()
    return {
        "schema": SCHEMA,
        "status": "B_ONLY_REAL_INSTALLED_SYNTHETIC_HEALTH_NOT_CUSTOMER_APPROVED",
        "installed_distribution": PRODUCT_DISTRIBUTION,
        "installed_version": installed_version,
        "new_in_functional_version_b": True,
        "four_pillars": list(PILLARS),
        "four_pillar_synthetic_workflow_sha256": digest,
        "installed_four_pillar_workflows_checked": True,
        "customer_code_read": False,
        "customer_directory_scanned": False,
        "external_network_requests": 0,
        "operating_database_writes": 0,
        "auto_promoted": False,
        "independent_customer_acceptance": False,
        "customer_distribution_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE disposable B-only installed four-pillar health check"
    )
    parser.add_argument("--self-check", action="store_true", required=True)
    parser.parse_args(argv)
    try:
        receipt = run_installed_self_check()
    except (InstalledHealthError, ValueError, RuntimeError):
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_C1_B_ONLY_SELF_CHECK_FAIL_CLOSED",
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(receipt, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
