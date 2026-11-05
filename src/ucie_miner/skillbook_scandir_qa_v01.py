"""UCIE W08 SkillBook 001: bounded first-party synthetic recipe QA.

Executes ONLY the UCIE-authored scandir recipe against newly created
temporary synthetic fixtures. Never scans an arbitrary caller directory,
reads another project, calls a public API, modifies UCIE SQLite, runs
untrusted upstream code, approves a package or trains a model.

A passing synthetic receipt is NOT independent QA or release approval.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from .skillbook_product_v01 import (
    SKILLBOOK_ID, SOURCE_DOCUMENT_SHA256, build_skillbook,
)
from .skillbook_scandir_recipe_v01 import (
    MAX_ENTRIES, BoundedScandirError, bounded_regular_file_names,
)

SCHEMA = "UCIE_W08_SCANDIR_SKILLBOOK_SYNTHETIC_QA_V01"
PASS_STATE = "FIRST_PARTY_SYNTHETIC_PASS_NO_RELEASE"
FAIL_STATE = "SYNTHETIC_REGRESSION_FAILED_NO_GO"
SOURCE_FILE = "skillbook_scandir_recipe_v01.py"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class SkillBookQAError(ValueError):
    """The fixed first-party source identity or QA setup is untrusted."""


class _FakeEntry:
    def __init__(self, name: str, *, error: bool = False):
        self.name = name
        self.error = error

    def is_symlink(self):
        return False

    def is_file(self, *, follow_symlinks=False):
        if self.error:
            raise OSError("synthetic DirEntry metadata failure")
        return True


class _FakeScandir:
    def __init__(self, entries):
        self.entries = tuple(entries)
        self.entered = False
        self.closed = False

    def __enter__(self):
        self.entered = True
        return iter(self.entries)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.closed = True
        return False


def _denied(action) -> bool:
    try:
        action()
    except BoundedScandirError:
        return True
    return False


def _fixture_dir(root: Path, name: str) -> Path:
    directory = root / name
    directory.mkdir()
    return directory


def _case_sorted_names(root: Path) -> bool:
    directory = _fixture_dir(root, "sorted_names")
    (directory / "zeta.txt").write_bytes(b"UCIE SYNTHETIC")
    (directory / "alpha.txt").write_bytes(b"UCIE SYNTHETIC")
    (directory / "nested").mkdir()
    return bounded_regular_file_names(directory, max_entries=3) == (
        "alpha.txt", "zeta.txt")


def _case_empty_dir(root: Path) -> bool:
    return bounded_regular_file_names(
        _fixture_dir(root, "empty"), max_entries=1) == ()


def _case_limit_inclusive(root: Path) -> bool:
    directory = _fixture_dir(root, "exact_budget")
    for i in range(3):
        (directory / f"synthetic_{i}.txt").write_bytes(b"UCIE")
    return bounded_regular_file_names(directory, max_entries=3) == tuple(
        f"synthetic_{i}.txt" for i in range(3))


def _case_budget_counts_all_entries(root: Path) -> bool:
    directory = _fixture_dir(root, "budget_with_subdirectory")
    (directory / "a.txt").write_bytes(b"UCIE")
    (directory / "b.txt").write_bytes(b"UCIE")
    (directory / "nested").mkdir()
    return _denied(lambda: bounded_regular_file_names(
        directory, max_entries=2))


def _case_bad_input_rejected(root: Path) -> bool:
    directory = _fixture_dir(root, "bad_input")
    return all((
        _denied(lambda: bounded_regular_file_names("relative/path")),
        _denied(lambda: bounded_regular_file_names(directory, max_entries=0)),
        _denied(lambda: bounded_regular_file_names(directory, max_entries=129)),
        _denied(lambda: bounded_regular_file_names(directory, max_entries=True)),
        _denied(lambda: bounded_regular_file_names(directory, max_entries=1.0)),
        _denied(lambda: bounded_regular_file_names("")),
    ))


def _case_mocked_redirect_precheck(root: Path) -> bool:
    directory = _fixture_dir(root, "mocked_link_precheck")
    with patch.object(Path, "is_symlink",
                      lambda self: self == directory):
        return _denied(lambda: bounded_regular_file_names(directory))


def _case_iterator_closed_on_overflow(root: Path) -> bool:
    directory = _fixture_dir(root, "iterator_limit")
    fake = _FakeScandir([_FakeEntry("a.txt"), _FakeEntry("b.txt")])
    with patch.object(os, "scandir", return_value=fake):
        denied = _denied(lambda: bounded_regular_file_names(
            directory, max_entries=1))
    return denied and fake.entered and fake.closed


def _case_iterator_closed_on_metadata_failure(root: Path) -> bool:
    directory = _fixture_dir(root, "iterator_error")
    fake = _FakeScandir([_FakeEntry("bad.txt", error=True)])
    with patch.object(os, "scandir", return_value=fake):
        denied = _denied(lambda: bounded_regular_file_names(directory))
    return denied and fake.entered and fake.closed


def _case_scandir_open_error_fail_closed(root: Path) -> bool:
    directory = _fixture_dir(root, "scandir_open_error")
    with patch.object(os, "scandir",
                      side_effect=OSError("synthetic unavailable")):
        return _denied(lambda: bounded_regular_file_names(directory))


CASES = (
    ("SORTED_NAMES_NO_RECURSION", _case_sorted_names),
    ("EMPTY_DIRECTORY", _case_empty_dir),
    ("INCLUSIVE_LIMIT", _case_limit_inclusive),
    ("ALL_ENTRY_TYPES_COUNT_TOWARD_LIMIT", _case_budget_counts_all_entries),
    ("MALFORMED_INPUTS_BLOCKED", _case_bad_input_rejected),
    ("MOCKED_LINK_PRECHECK", _case_mocked_redirect_precheck),
    ("ITERATOR_CLOSED_OVERFLOW", _case_iterator_closed_on_overflow),
    ("ITERATOR_CLOSED_METADATA_ERROR", _case_iterator_closed_on_metadata_failure),
    ("OPEN_ERROR_FAIL_CLOSED", _case_scandir_open_error_fail_closed),
)


def evaluate_skillbook_scandir() -> dict:
    """One bounded on-demand experiment, returning a deterministic receipt.

    No caller pathname is accepted. Synthetic fixture files are created in
    an owned TemporaryDirectory and removed on exit; source pin is our own
    first-party recipe module, not private project code or an operating DB.
    """
    book = build_skillbook()
    evidence = book["source_evidence"]
    if (book["skillbook_id"] != SKILLBOOK_ID
            or book["status"] != "FIRST_PARTY_DRAFT_NOT_APPROVED"
            or book.get("export_allowed") is not False
            or book["proof_gates"].get("independent_test_verified") is not False
            or evidence.get("source_document_sha256") != SOURCE_DOCUMENT_SHA256
            or HEX64.fullmatch(SOURCE_DOCUMENT_SHA256) is None):
        raise SkillBookQAError("source identity or release gate drift")
    source_path = Path(__file__).with_name(SOURCE_FILE)
    if source_path.is_symlink() or not source_path.is_file():
        raise SkillBookQAError("first-party source not found")
    source_bytes = source_path.read_bytes()
    if not 0 < len(source_bytes) <= 100_000:
        raise SkillBookQAError("source size out of bounds")
    recipe_sha = hashlib.sha256(source_bytes).hexdigest()
    cases = []
    with TemporaryDirectory(prefix="UCIE_SKILLBOOK_SYNTH_QA_") as folder:
        root = Path(folder)
        for case_id, action in CASES:
            try:
                observed = action(root)
                passed = observed is True
            except Exception:
                # Do not leak host paths or exception text into a receipt.
                passed = False
            cases.append({
                "case_id": case_id,
                "status": "PASS" if passed else "FAIL",
                "synthetic_only": True,
            })
    count = sum(row["status"] == "PASS" for row in cases)
    result = {
        "schema": SCHEMA,
        "skillbook_id": SKILLBOOK_ID,
        "skillbook_source_document_sha256": SOURCE_DOCUMENT_SHA256,
        "recipe_source_sha256": recipe_sha,
        "python_runtime": f"{sys.version_info.major}.{sys.version_info.minor}",
        "status": PASS_STATE if count == len(cases) else FAIL_STATE,
        "test_kind": "UCIE_FIRST_PARTY_TEMPORARY_SYNTHETIC_FILES_ONLY",
        "case_count": len(cases),
        "passed_count": count,
        "failed_count": len(cases) - count,
        "cases": cases,
        "actual_owner_directory_scanned": False,
        "real_symlink_privilege_test_performed": False,
        "toc_tou_race_verified": False,
        "independent_qa_verified": False,
        "security_review_approved": False,
        "license_redistribution_approved": False,
        "human_approved": False,
        "signed": False,
        "export_allowed": False,
        "model_training_performed": False,
        "public_network_requests": 0,
        "operating_database_writes": 0,
        "temporary_synthetic_fixture_writes": True,
        "other_project_access": False,
    }
    canonical = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    result["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    return result


def main() -> int:
    try:
        receipt = evaluate_skillbook_scandir()
    except (SkillBookQAError, ValueError, TypeError, OSError, KeyError):
        print(json.dumps({
            "schema": SCHEMA, "status": FAIL_STATE,
            "receipt_created": False, "export_allowed": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
    return 0 if receipt["status"] == PASS_STATE else 2


if __name__ == "__main__":
    raise SystemExit(main())
