"""UCIE SkillBook 001: actual consumer walk-through on DISPOSABLE files only.

The production-quality recipe is imported and *called* (not mocked).
The CLI never accepts a directory from the host/user. It is not a
redistributable, approved or signed skill package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from .skillbook_product_v01 import (
    SKILLBOOK_ID, SOURCE_DOCUMENT_SHA256, build_skillbook,
)
from .skillbook_scandir_recipe_v01 import (
    BoundedScandirError, bounded_regular_file_names,
)

SCHEMA = "UCIE_SKILLBOOK_001_DISPOSABLE_CONSUMER_PILOT_V01"
PREVIEW = "CONSUMER_PILOT_NOT_RUN_DRAFT_ONLY"
OBSERVED = "FIRST_PARTY_CONSUMER_EXECUTION_OBSERVED_NO_RELEASE"
NO_GO = "FIRST_PARTY_CONSUMER_CONTRACT_NO_GO"
EXPECTED_FILES = ("alpha.txt", "zeta.txt")
EXPECTED_BASELINE = ("alpha.txt", "nested", "zeta.txt")
RECIPE_NAME = "skillbook_scandir_recipe_v01.py"


class ConsumerPilotError(ValueError):
    """UCIE source, consumer contract or first-party pilot not satisfied."""


def preview() -> dict:
    return {
        "schema": SCHEMA,
        "status": PREVIEW,
        "skillbook_id": SKILLBOOK_ID,
        "run_mode": "MANUAL_DISPOSABLE_FIXTURE_ONLY",
        "demo_executed": False,
        "actual_recipe_executed": False,
        "approved_directory_used": False,
        "temporary_fixture_writes": False,
        "operating_database_writes": 0,
        "network_requests": 0,
        "external_project_access": False,
        "independent_qa_verified": False,
        "license_redistribution_approved": False,
        "owner_release_approved": False,
        "export_allowed": False,
        "model_training_performed": False,
    }


def _check_source() -> str:
    path = Path(__file__).with_name(RECIPE_NAME)
    if path.is_symlink() or not path.is_file():
        raise ConsumerPilotError("UCIE recipe module unavailable")
    data = path.read_bytes()
    if not 0 < len(data) <= 100_000:
        raise ConsumerPilotError("UCIE recipe bytes outside fixed bounds")
    return hashlib.sha256(data).hexdigest()


def _is_blocked(action) -> bool:
    try:
        action()
    except BoundedScandirError:
        return True
    return False


def demonstrate_synthetic_consumer() -> dict:
    """Demonstrate a consumer's actual results with UCIE-authored test input.

    A baseline standard-library listdir result is reported ONLY for the same
    three synthetic directory entries; no security/performance superiority
    claim is inferred from this illustration.
    """
    book = build_skillbook()
    contract = book.get("machine_skill_contract")
    gates = book.get("proof_gates")
    if (book.get("skillbook_id") != SKILLBOOK_ID
            or book.get("status") != "FIRST_PARTY_DRAFT_NOT_APPROVED"
            or book.get("export_allowed") is not False
            or type(contract) is not dict
            or contract.get("callable") != (
                "ucie_miner.skillbook_scandir_recipe_v01"
                ".bounded_regular_file_names")
            or type(gates) is not dict
            or any(gates.get(key) is not False for key in (
                "independent_test_verified", "license_redistribution_approved",
                "security_review_approved", "human_approved",
                "signed", "published"))
            or book.get("source_evidence", {}).get(
                "source_document_sha256") != SOURCE_DOCUMENT_SHA256):
        raise ConsumerPilotError("UCIE draft source or approval contract drift")
    recipe_sha256 = _check_source()
    with TemporaryDirectory(prefix="UCIE_SKILLBOOK_001_CONSUMER_") as temporary:
        fixture = Path(temporary) / "owned_synthetic_fixture"
        fixture.mkdir()
        (fixture / "zeta.txt").write_bytes(b"UCIE DEMO ONLY\n")
        (fixture / "alpha.txt").write_bytes(b"UCIE DEMO ONLY\n")
        (fixture / "nested").mkdir()
        baseline = tuple(sorted(os.listdir(fixture)))
        names = bounded_regular_file_names(fixture, max_entries=3)
        overflow = _is_blocked(
            lambda: bounded_regular_file_names(fixture, max_entries=2))
        bad_budget = _is_blocked(
            lambda: bounded_regular_file_names(fixture, max_entries=0))
        relative = _is_blocked(
            lambda: bounded_regular_file_names("ucie-not-an-absolute-directory"))
        empty_fixture = Path(temporary) / "empty_fixture"
        empty_fixture.mkdir()
        empty_names = bounded_regular_file_names(empty_fixture, max_entries=1)
    valid = (baseline == EXPECTED_BASELINE
             and names == EXPECTED_FILES
             and overflow and bad_budget and relative
             and empty_names == ())
    result = {
        "schema": SCHEMA,
        "status": OBSERVED if valid else NO_GO,
        "skillbook_id": SKILLBOOK_ID,
        "version": "0.1.0-draft",
        "source_document_sha256": SOURCE_DOCUMENT_SHA256,
        "recipe_sha256": recipe_sha256,
        "run_mode": "MANUAL_DISPOSABLE_FIXTURE_ONLY",
        "baseline_method": "os.listdir_on_same_UCIE_synthetic_fixture",
        "baseline_entry_count": len(baseline),
        "bounded_regular_file_names": list(names),
        "bounded_regular_file_name_count": len(names),
        "directory_entry_budget": 3,
        "budget_overflow_blocked": overflow,
        "invalid_budget_blocked": bad_budget,
        "relative_path_blocked": relative,
        "empty_directory_returns_empty_tuple": empty_names == (),
        "nested_directory_skipped": "nested" not in names,
        "no_performance_superiority_claimed": True,
        "real_ucie_authored_recipe_executed": True,
        "only_temporary_synthetic_fixture_used": True,
        "temporary_fixture_cleaned": True,
        "real_owner_directory_scanned": False,
        "file_contents_read": False,
        "source_contents_disclosed": False,
        "independent_qa_verified": False,
        "license_redistribution_approved": False,
        "security_review_approved": False,
        "owner_release_approved": False,
        "export_allowed": False,
        "package_created": False,
        "model_training_performed": False,
        "operating_database_writes": 0,
        "task_scheduler_mutations": 0,
        "network_requests": 0,
        "other_project_access": False,
    }
    if not valid:
        raise ConsumerPilotError("first-party consumer demonstration failed")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE SkillBook 001 first-party disposable consumer pilot")
    parser.add_argument("--run-synthetic-demo", action="store_true")
    args = parser.parse_args(argv)
    if not args.run_synthetic_demo:
        print(json.dumps(preview(), ensure_ascii=True, sort_keys=True))
        return 0
    try:
        report = demonstrate_synthetic_consumer()
    except (ConsumerPilotError, ValueError, TypeError, KeyError, OSError):
        print(json.dumps({"schema": SCHEMA, "status": NO_GO,
                          "export_allowed": False,
                          "operating_database_writes": 0,
                          "task_scheduler_mutations": 0},
                         ensure_ascii=True, sort_keys=True))
        return 2
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
