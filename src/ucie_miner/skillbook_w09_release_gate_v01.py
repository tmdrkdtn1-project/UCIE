"""UCIE W09 SkillBook 001: first-party receipt verifier, release gate NO_GO.

Consumes a bounded W08 synthetic QA dictionary, not a file, network,
operating DB, project-wide scan or third-party attestation. Verifies receipt
integrity and current first-party source identity. A matching receipt NEVER
approves rights, security, distribution, signing, model training or release.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from . import skillbook_scandir_qa_v01 as w08
from .skillbook_product_v01 import (
    SKILLBOOK_ID, SOURCE_DOCUMENT_SHA256, build_skillbook,
)

SCHEMA = "UCIE_W09_SKILLBOOK_RELEASE_GATE_READONLY_V01"
VALIDATED_STATE = "FIRST_PARTY_RECEIPT_REPRODUCED_RELEASE_NO_GO"
PREVIEW_STATE = "RECEIPT_NOT_PROVIDED_RELEASE_NO_GO"
INVALID_STATE = "RECEIPT_OR_SOURCE_INVALID_NO_GO"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
SUPPORTED_RUNTIMES = frozenset(("3.13", "3.15"))
EXPECTED_CASE_IDS = tuple(item[0] for item in w08.CASES)
SOURCE_FILE = w08.SOURCE_FILE
BLOCKERS = (
    "EXACT_HEAD_COMPLETE_CI_4_OF_4_NOT_ATTESTED_BY_LOCAL_RECEIPT",
    "INDEPENDENT_THIRD_PARTY_QA_NOT_ATTESTED",
    "PLATFORM_SECURITY_REVIEW_NOT_ATTESTED",
    "LICENSE_DISTRIBUTION_RIGHTS_NOT_APPROVED",
    "OWNER_RELEASE_AUTHORIZATION_NOT_PROVIDED",
    "SIGNED_PACKAGE_AND_EXTERNAL_PUBLICATION_NOT_AUTHORIZED",
)
FALSE_CLAIMS = (
    "actual_owner_directory_scanned",
    "real_symlink_privilege_test_performed",
    "toc_tou_race_verified",
    "independent_qa_verified",
    "security_review_approved",
    "license_redistribution_approved",
    "human_approved",
    "signed",
    "export_allowed",
    "model_training_performed",
    "other_project_access",
)
TRUE_CLAIMS = ("temporary_synthetic_fixture_writes",)
ZERO_CLAIMS = ("public_network_requests", "operating_database_writes")
# Fixed W08 v0.1 schema: no extra unknown claims may slip through.
REQUIRED_RECEIPT_FIELDS = frozenset((
    "schema", "skillbook_id", "skillbook_source_document_sha256",
    "recipe_source_sha256", "python_runtime", "status", "test_kind",
    "case_count", "passed_count", "failed_count", "cases",
    "receipt_sha256", *FALSE_CLAIMS, *TRUE_CLAIMS, *ZERO_CLAIMS,
))


class SkillBookReleaseGateError(ValueError):
    """Receipt or first-party source failed fail-closed validation."""


def _hash(value: dict) -> str:
    return sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _source_sha256() -> str:
    """Read exactly our own first-party bounded recipe module, no caller path."""
    path = Path(__file__).with_name(SOURCE_FILE)
    if path.is_symlink() or not path.is_file():
        raise SkillBookReleaseGateError("first-party recipe path not trusted")
    raw = path.read_bytes()
    if not 0 < len(raw) <= 100_000:
        raise SkillBookReleaseGateError("first-party recipe bytes out of range")
    return sha256(raw).hexdigest()


def _source_contract() -> dict:
    book = build_skillbook()
    entry = book.get("library_entry")
    source = book.get("source_evidence")
    gate = book.get("proof_gates")
    machine = book.get("machine_skill_contract")
    if (book.get("skillbook_id") != SKILLBOOK_ID
            or book.get("status") != "FIRST_PARTY_DRAFT_NOT_APPROVED"
            or book.get("export_allowed") is not False
            or type(entry) is not dict
            or entry.get("source_id") != "doc:python/cpython"
            or entry.get("export_allowed") is not False
            or type(source) is not dict
            or source.get("source_document_sha256") != SOURCE_DOCUMENT_SHA256
            or source.get("source_tag") != "v3.15.0"
            or type(gate) is not dict
            or any(gate.get(key) is not False for key in (
                "independent_test_verified", "license_redistribution_approved",
                "security_review_approved", "human_approved",
                "signed", "published"))
            or type(machine) is not dict
            or machine.get("callable") != (
                "ucie_miner.skillbook_scandir_recipe_v01"
                ".bounded_regular_file_names")
            or machine.get("portable_package_state")
            != "DRAFT_SOURCE_ONLY_NOT_APPROVED"):
        raise SkillBookReleaseGateError("source or approval contract drift")
    return book


def preview_release_gate() -> dict:
    """Static gate plan. No synthetic QA is run by this call or the browser."""
    return {
        "schema": SCHEMA,
        "status": PREVIEW_STATE,
        "skillbook_id": SKILLBOOK_ID,
        "candidate_version": "0.1.0-draft",
        "source_registry_id": "doc:python/cpython",
        "receipt_validation_performed": False,
        "blocked_release_requirements": list(BLOCKERS),
        "owner_release_authorized": False,
        "license_redistribution_approved": False,
        "independent_qa_verified": False,
        "security_review_approved": False,
        "package_signed": False,
        "export_allowed": False,
        "package_created": False,
        "source_code_executed": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "other_project_access": False,
    }


def assess_release_readiness(receipt: dict) -> dict:
    """Verify W08 source/receipt in memory without creating package bytes.

    W08 is first-party synthetic evidence; even perfect provenance is never
    independent, legal, security or owner authorization. If input is forged,
    malformed or altered, throw a typed NO_GO (do not return approved data).
    """
    if (type(receipt) is not dict or len(receipt) > 40
            or set(receipt) != REQUIRED_RECEIPT_FIELDS):
        raise SkillBookReleaseGateError("unrecognized W08 receipt shape")
    if (receipt.get("schema") != w08.SCHEMA
            or receipt.get("status") != w08.PASS_STATE
            or receipt.get("skillbook_id") != SKILLBOOK_ID
            or receipt.get("test_kind")
            != "UCIE_FIRST_PARTY_TEMPORARY_SYNTHETIC_FILES_ONLY"
            or receipt.get("python_runtime") not in SUPPORTED_RUNTIMES
            or receipt.get("skillbook_source_document_sha256")
            != SOURCE_DOCUMENT_SHA256
            or type(receipt.get("receipt_sha256")) is not str
            or HEX64.fullmatch(receipt["receipt_sha256"]) is None
            or type(receipt.get("recipe_source_sha256")) is not str
            or HEX64.fullmatch(receipt["recipe_source_sha256"]) is None):
        raise SkillBookReleaseGateError("receipt identity or lifecycle mismatch")
    for key in FALSE_CLAIMS:
        if receipt.get(key) is not False:
            raise SkillBookReleaseGateError("forged safety/approval claim")
    for key in TRUE_CLAIMS:
        if receipt.get(key) is not True:
            raise SkillBookReleaseGateError("missing synthetic scope disclosure")
    for key in ZERO_CLAIMS:
        if type(receipt.get(key)) is not int or receipt[key] != 0:
            raise SkillBookReleaseGateError("unexpected operating side effect")
    if (type(receipt.get("case_count")) is not int
            or receipt["case_count"] != len(EXPECTED_CASE_IDS)
            or type(receipt.get("passed_count")) is not int
            or receipt["passed_count"] != len(EXPECTED_CASE_IDS)
            or type(receipt.get("failed_count")) is not int
            or receipt["failed_count"] != 0
            or type(receipt.get("cases")) is not list
            or len(receipt["cases"]) != len(EXPECTED_CASE_IDS)):
        raise SkillBookReleaseGateError("incomplete synthetic QA coverage")
    for actual, expected_id in zip(receipt["cases"], EXPECTED_CASE_IDS):
        if (type(actual) is not dict or set(actual) != {
                "case_id", "status", "synthetic_only"}
                or actual.get("case_id") != expected_id
                or actual.get("status") != "PASS"
                or actual.get("synthetic_only") is not True):
            raise SkillBookReleaseGateError("unexpected or reordered W08 case")
    unsigned = dict(receipt)
    digest = unsigned.pop("receipt_sha256")
    if _hash(unsigned) != digest:
        raise SkillBookReleaseGateError("modified or noncanonical W08 receipt")
    _source_contract()
    if receipt["recipe_source_sha256"] != _source_sha256():
        raise SkillBookReleaseGateError("recipe source changed since receipt")
    summary = {
        "schema": SCHEMA,
        "status": VALIDATED_STATE,
        "skillbook_id": SKILLBOOK_ID,
        "candidate_version": "0.1.0-draft",
        "source_registry_id": "doc:python/cpython",
        "official_document_sha256": SOURCE_DOCUMENT_SHA256,
        "recipe_source_sha256": receipt["recipe_source_sha256"],
        "validated_first_party_receipt_sha256": digest,
        "receipt_python_runtime": receipt["python_runtime"],
        "synthetic_cases_reported_pass": len(EXPECTED_CASE_IDS),
        "first_party_synthetic_receipt_integrity_pass": True,
        "source_identity_matches_current_checkout": True,
        "blocked_release_requirements": list(BLOCKERS),
        "exact_head_ci_matrix_attested": False,
        "independent_qa_verified": False,
        "security_review_approved": False,
        "license_redistribution_approved": False,
        "owner_release_authorized": False,
        "package_signed": False,
        "export_allowed": False,
        "package_created": False,
        "portable_package_bytes_produced": 0,
        "model_training_performed": False,
        "source_code_executed_by_gate": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "other_project_access": False,
    }
    summary["report_sha256"] = _hash(summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE SkillBook W09 first-party release preflight, never export")
    parser.add_argument("--run-synthetic", action="store_true",
                        help="Run W08 disposable synthetic QA and validate its receipt")
    args = parser.parse_args(argv)
    if not args.run_synthetic:
        print(json.dumps(preview_release_gate(), sort_keys=True,
                         ensure_ascii=True))
        return 0
    try:
        report = assess_release_readiness(w08.evaluate_skillbook_scandir())
    except (SkillBookReleaseGateError, ValueError, TypeError, KeyError, OSError):
        print(json.dumps({
            "schema": SCHEMA, "status": INVALID_STATE,
            "package_created": False, "export_allowed": False,
            "owner_release_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
