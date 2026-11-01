"""UCIE V1.0: fixed local guard regressions, NOT upstream-fix regressions.

Every case is a UCIE-authored deterministic fixture. No third-party source
file or shell command is executed, no arbitrary test paths accepted, and
no public fixes are marked independently verified. Only UCIE error-prevention
boundary behavior is actually tested.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .library_observation_receipts_v10 import (
    ObservationError, _check_basis, SCHEMA as RECEIPT_SCHEMA,
)
from .library_browser_v09 import _audit_listing_query
from .library_public_probe_v08 import _public_get, ProbeError
from .library_review_records_v05 import _public_evidence_url, ClaimError

SCHEMA = "UCIE_OWNED_OFFLINE_GUARD_REGRESSION_V10"

def _rejected(call, error) -> bool:
    try:
        call()
    except error:
        return True
    return False


def run_owner_guard_regressions() -> dict:
    """Run real fixed UCIE safety checks; never claim upstream bug-fix proof."""
    basis = {
        "schema": RECEIPT_SCHEMA,
        "item_id": "a"*64,
        "source_id": "repo:python/cpython",
        "public_url": "https://github.com/python/cpython/pull/123",
        "revision_hint": "b"*40,
        "v09_report_sha256": "c"*64,
        "metadata_status": "PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED",
        "metadata_observed": True, "identity_matched": True,
        "documents": [], "fix_verified": False, "rule_approved": False,
        "auto_promoted": False, "source_code_executed": False,
        "approval_state": "OBSERVED_PUBLIC_METADATA_NOT_FIX_VERIFIED",
    }
    checks = (
        ("NON_ALLOWLIST_REPO_API_REJECTED",
         lambda: _rejected(
             lambda: _public_get(
                 "https://api.github.com/repos/unknown/private/pulls/1",
                 max_bytes=128, json_only=True), ProbeError)),
        ("LOOPBACK_PUBLIC_URL_REJECTED",
         lambda: _rejected(
             lambda: _public_get(
                 "https://127.0.0.1/secrets",
                 max_bytes=128, json_only=False), ProbeError)),
        ("THIRD_PARTY_CLAIM_REJECTED",
         lambda: _rejected(
             lambda: _public_evidence_url(
                 "https://github.com/unknown/private/pull/1",
                 source_id="repo:python/cpython"), ClaimError)),
        ("DUPLICATE_QUERY_REJECTED",
         lambda: _rejected(
             lambda: _audit_listing_query("page=1&page=2"), ValueError)),
        ("FORGED_APPROVAL_REJECTED",
         lambda: _rejected(
             lambda: _check_basis(dict(basis, rule_approved=True)),
             ObservationError)),
        ("UNVERIFIED_SNAPSHOT_ACCEPTS_ONLY_UNVERIFIED",
         lambda: _check_basis(dict(basis)) == basis),
    )
    results = []
    for label, verify in checks:
        passed = bool(verify())
        results.append({"case": label, "passed": passed,
                        "source": "UCIE_AUTHORED_OFFLINE_FIXED_FIXTURE"})
    good = all(x["passed"] for x in results)
    result = {
        "schema": SCHEMA,
        "status": ("UCIE_GUARD_FIXTURE_PASS_NOT_UPSTREAM_FIX_VERIFIED"
                   if good else "UCIE_GUARD_FIXTURE_NO_GO"),
        "tested_fixture_count": len(results),
        "passed_fixture_count": sum(x["passed"] for x in results),
        "cases": results,
        "upstream_fix_verified": False,
        "independent_upstream_regressions_passed": 0,
        "version_applicability_verified": False,
        "license_legally_approved": False,
        "approved_rules": 0,
        "operating_db_writes": 0,
        "external_network_calls": 0,
    }
    result["report_sha256"] = sha256(json.dumps(
        result, ensure_ascii=True, sort_keys=True,
        separators=(",", ":")).encode("ascii")).hexdigest()
    return result


def main() -> int:
    report = run_owner_guard_regressions()
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0 if report["status"] == (
        "UCIE_GUARD_FIXTURE_PASS_NOT_UPSTREAM_FIX_VERIFIED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
