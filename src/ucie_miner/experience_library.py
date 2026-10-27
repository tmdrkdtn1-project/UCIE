"""P8: append-only UCIE-owned synthetic experiment experience catalog.

The only writer runs the existing W08 first-party evaluator itself. No user
JSON, upstream PR payload, source code, external project or model training
enters the catalog. Writes require an explicit --record flag. By default every
query is read-only and creates nothing.

Records are self-hashed immutable files with a same-workload parent link.
SHA256 checks detect accidental edits but are NOT cryptographic signatures or
independent approval. A working filesystem administrator can rewrite a ledger.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from .capability_evaluator import (
    SCHEMA as W08_SCHEMA, EXPERIMENT_ID, CapabilityEvaluationError,
    evaluate_synthetic_library_index,
)

SCHEMA = "UCIE_P8_OWNED_EXPERIENCE_LIBRARY_V1"
RECORD_SCHEMA = "UCIE_P8_SYNTHETIC_EXPERIMENT_RECORD_V1"
FOLDER = "ucie_experience_v1"
MAX_RECORDS = 128
MAX_BYTES = 8192
HEX = re.compile(r"[0-9a-f]{64}\Z")
FILE_NAME = re.compile(r"r_([0-9a-f]{64})\.json\Z")
STATUS_GOOD = "SYNTHETIC_EQUIVALENCE_AND_OPERATION_REDUCTION_OBSERVED_NO_GO"
STATUS_REVIEW = "SYNTHETIC_EVALUATION_REQUIRES_REVIEW_NO_GO"
RECORD_FIELDS = frozenset({
    "schema", "kind", "experiment_id", "provenance", "created_utc",
    "dataset_sha256", "synthetic_item_count", "query_count",
    "measurement_repetitions", "baseline_algorithm", "candidate_algorithm",
    "exact_result_equivalence_observed", "mismatched_query_count",
    "matching_query_count", "no_match_query_count",
    "reference_comparisons_per_run",
    "candidate_build_plus_lookup_operations_per_run",
    "operation_reduction", "baseline_median_elapsed_ns",
    "candidate_median_elapsed_ns", "outcome", "parent_record_id",
    "revision_number", "limitations", "human_review_required",
    "production_adopted", "owner_approved",
})


class ExperienceLibraryError(ValueError):
    pass


def _canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _root(root: Path) -> Path:
    root = Path(root)
    if root.is_symlink() or not root.is_dir() or root.name.casefold() != "ucie":
        raise ExperienceLibraryError("dedicated UCIE checkout root required")
    runtime = root / "runtime"
    if runtime.is_symlink():
        raise ExperienceLibraryError("unsafe UCIE runtime directory")
    if runtime.exists() and not runtime.is_dir():
        raise ExperienceLibraryError("UCIE runtime is not a directory")
    path = runtime / FOLDER
    if path.is_symlink() or path.exists() and not path.is_dir():
        raise ExperienceLibraryError("unsafe experience catalog directory")
    return path


def _valid_record(record: object) -> None:
    if type(record) is not dict or set(record) != RECORD_FIELDS:
        raise ExperienceLibraryError("untrusted experience record fields")
    if (record["schema"] != RECORD_SCHEMA or record["kind"] != "UCIE_EXPERIENCE"
            or record["experiment_id"] != EXPERIMENT_ID
            or record["provenance"] != "UCIE_AUTHORED_SYNTHETIC_LOCAL_EXECUTION"
            or record["baseline_algorithm"] != "LINEAR_EXACT_MATCH_SCAN_V1"
            or record["candidate_algorithm"] != "COMPOSITE_HASH_LOOKUP_V1"
            or record["limitations"] != "SYNTHETIC_ONLY_NOT_REAL_USER_WORKLOAD"
            or record["human_review_required"] is not True
            or record["production_adopted"] is not False
            or record["owner_approved"] is not False):
        raise ExperienceLibraryError("non-UCIE experience or false approval")
    digest = record["dataset_sha256"]
    if type(digest) is not str or HEX.fullmatch(digest) is None:
        raise ExperienceLibraryError("invalid synthetic dataset fingerprint")
    try:
        when = datetime.fromisoformat(record["created_utc"].replace("Z", "+00:00"))
        if when.utcoffset() is None or when.utcoffset().total_seconds() != 0:
            raise ValueError("UTC time required")
    except (ValueError, TypeError, AttributeError) as exc:
        raise ExperienceLibraryError("invalid UTC experience time") from exc
    ints = ("synthetic_item_count", "query_count", "measurement_repetitions",
            "mismatched_query_count", "matching_query_count",
            "no_match_query_count", "reference_comparisons_per_run",
            "candidate_build_plus_lookup_operations_per_run",
            "operation_reduction", "baseline_median_elapsed_ns",
            "candidate_median_elapsed_ns", "revision_number")
    if any(type(record[k]) is not int for k in ints):
        raise ExperienceLibraryError("invalid experience integer fields")
    rows, q, repeats = (record["synthetic_item_count"], record["query_count"],
                        record["measurement_repetitions"])
    if not (256 <= rows <= 4096 and 16 <= q <= 96 and 1 <= repeats <= 5
            and 1 <= record["revision_number"] <= MAX_RECORDS
            and 0 <= record["mismatched_query_count"] <= q
            and 0 <= record["matching_query_count"] <= q
            and 0 <= record["no_match_query_count"] <= q
            and record["matching_query_count"] + record["no_match_query_count"] == q
            and record["reference_comparisons_per_run"] == rows * q
            and record["candidate_build_plus_lookup_operations_per_run"] == rows + q
            and record["operation_reduction"] == rows * q - rows - q
            and record["baseline_median_elapsed_ns"] >= 0
            and record["candidate_median_elapsed_ns"] >= 0):
        raise ExperienceLibraryError("inconsistent synthetic W08 metrics")
    if type(record["exact_result_equivalence_observed"]) is not bool:
        raise ExperienceLibraryError("invalid result equivalence flag")
    expected_status = (STATUS_GOOD
                       if (record["exact_result_equivalence_observed"]
                           and record["mismatched_query_count"] == 0
                           and record["operation_reduction"] > 0)
                       else STATUS_REVIEW)
    if record["outcome"] != expected_status:
        raise ExperienceLibraryError("synthetic evaluation status overclaim")
    parent = record["parent_record_id"]
    if parent is not None and (type(parent) is not str or HEX.fullmatch(parent) is None):
        raise ExperienceLibraryError("invalid parent record")
    if (parent is None) != (record["revision_number"] == 1):
        raise ExperienceLibraryError("experience ancestry revision mismatch")


def _list_verified(root: Path) -> list[dict]:
    folder = _root(root)
    if not folder.exists():
        return []
    files = []
    for entry in folder.iterdir():
        if entry.name.startswith(".ucie_tmp_"):
            continue  # incomplete atomic write; no published record
        if (FILE_NAME.fullmatch(entry.name) is None or entry.is_symlink()
                or not entry.is_file()):
            raise ExperienceLibraryError("unexpected file in experience catalog")
        files.append(entry)
        if len(files) > MAX_RECORDS:
            raise ExperienceLibraryError("experience storage limit reached")
    records = {}
    for file in files:
        if file.stat().st_size < 10 or file.stat().st_size > MAX_BYTES:
            raise ExperienceLibraryError("experience record size invalid")
        data = file.read_bytes()
        try:
            payload = json.loads(data.decode("ascii"),
                                 object_pairs_hook=_no_duplicate_fields)
        except (UnicodeError, ValueError) as exc:
            raise ExperienceLibraryError("invalid canonical experience JSON") from exc
        _valid_record(payload)
        if _canonical(payload) != data:
            raise ExperienceLibraryError("non-canonical experience record")
        digest = hashlib.sha256(data).hexdigest()
        if file.name != "r_" + digest + ".json":
            raise ExperienceLibraryError("experience fingerprint mismatch")
        records[digest] = payload
    for digest, row in records.items():
        parent = row["parent_record_id"]
        if parent is None:
            continue
        prior = records.get(parent)
        if (prior is None or prior["revision_number"] + 1 != row["revision_number"]
                or prior["dataset_sha256"] != row["dataset_sha256"]
                or prior["query_count"] != row["query_count"]
                or prior["synthetic_item_count"] != row["synthetic_item_count"]
                or prior["measurement_repetitions"] != row["measurement_repetitions"]
                or prior["created_utc"] > row["created_utc"]):
            raise ExperienceLibraryError("broken same-workload experience lineage")
    # Multiple leaves/branches may be present; disclose them, do not silently
    # rewrite history. De-duplication and head selection are deterministic.
    return [
        {"record_id": digest, **row}
        for digest, row in sorted(
            records.items(), key=lambda pair: (
                pair[1]["created_utc"], pair[1]["revision_number"], pair[0]))
    ]


def _no_duplicate_fields(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _comparison(previous: dict, current: dict) -> dict:
    same = (previous["dataset_sha256"] == current["dataset_sha256"]
            and previous["query_count"] == current["query_count"]
            and previous["synthetic_item_count"] == current["synthetic_item_count"]
            and previous["measurement_repetitions"] == current["measurement_repetitions"])
    if not same:
        raise ExperienceLibraryError("cannot compare different synthetic workloads")
    safe = (previous["outcome"] == STATUS_GOOD
            and current["outcome"] == STATUS_GOOD)
    return {
        "prior_record_id": previous["record_id"],
        "current_record_id": current["record_id"],
        "same_synthetic_workload": True,
        "both_runs_exact_and_operation_reduced": safe,
        "baseline_median_ns_delta": (
            current["baseline_median_elapsed_ns"] - previous["baseline_median_elapsed_ns"]),
        "candidate_median_ns_delta": (
            current["candidate_median_elapsed_ns"] - previous["candidate_median_elapsed_ns"]),
        "operation_reduction_delta": (
            current["operation_reduction"] - previous["operation_reduction"]),
        "decision": ("FURTHER_UCIE_SYNTHETIC_REVIEW_ONLY"
                     if safe else "REGRESSION_OR_UNCERTAINTY_REVIEW_REQUIRED"),
        "promote_to_production": False,
    }


def inspect_experience_library(root: Path, *, limit: int = 10) -> dict:
    """Read-only catalog; never create directories or execute a test."""
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ExperienceLibraryError("invalid bounded experience query")
    records = _list_verified(root)
    recent = list(reversed(records))
    parent_map = {r["record_id"]: r for r in records}
    comparisons = []
    for row in recent[:limit]:
        prev = parent_map.get(row["parent_record_id"])
        if prev is not None:
            comparisons.append(_comparison(prev, row))
    return {
        "schema": SCHEMA,
        "status": ("UCIE_OWNED_EXPERIENCES_READ_ONLY_UNAPPROVED"
                   if records else "UCIE_EXPERIENCE_LEDGER_EMPTY_NO_GO"),
        "total_records": len(records),
        "returned_count": min(limit, len(records)),
        "records": recent[:limit],
        "comparisons": comparisons,
        "dedicated_ledger_only": True,
        "hash_integrity_verified": True,
        "cryptographic_signatures_verified": False,
        "actual_production_improvement_verified": False,
        "network_requests": 0,
        "database_writes": 0,
        "model_weights_changed": False,
        "auto_promoted": False,
        "v1_accepted": False,
    }


def _build_record(w08: dict, *, parent: dict | None,
                  at_time: datetime | None) -> dict:
    """Extract strictly limited metrics from a locally run W08 experiment."""
    if (type(w08) is not dict or w08.get("schema") != W08_SCHEMA
            or w08.get("experiment_id") != EXPERIMENT_ID
            or w08.get("test_kind") != "UCIE_AUTHORED_SYNTHETIC_LIBRARY_SEARCH"
            or any(w08.get(k) is not False for k in (
                "performance_on_real_catalog_measured",
                "upstream_capability_implemented_or_verified",
                "public_source_data_used", "project_data_accessed",
                "model_weights_changed", "auto_promoted",
                "owner_approved", "production_approved", "v1_accepted"))):
        raise ExperienceLibraryError("untrusted or non-UCIE evaluation")
    now = datetime.now(timezone.utc) if at_time is None else at_time
    if type(now) is not datetime or now.tzinfo is None:
        raise ExperienceLibraryError("aware experiment observation time required")
    record = {
        "schema": RECORD_SCHEMA,
        "kind": "UCIE_EXPERIENCE",
        "experiment_id": EXPERIMENT_ID,
        "provenance": "UCIE_AUTHORED_SYNTHETIC_LOCAL_EXECUTION",
        "created_utc": now.astimezone(timezone.utc).isoformat(),
        "dataset_sha256": w08["dataset_sha256"],
        "synthetic_item_count": w08["synthetic_item_count"],
        "query_count": w08["query_count"],
        "measurement_repetitions": w08["measurement_repetitions"],
        "baseline_algorithm": w08["baseline_algorithm"],
        "candidate_algorithm": w08["candidate_algorithm"],
        "exact_result_equivalence_observed": w08["exact_result_equivalence_observed"],
        "mismatched_query_count": w08["mismatched_query_count"],
        "matching_query_count": w08["matching_query_count"],
        "no_match_query_count": w08["no_match_query_count"],
        "reference_comparisons_per_run": w08["reference_comparisons_per_run"],
        "candidate_build_plus_lookup_operations_per_run":
            w08["candidate_build_plus_lookup_operations_per_run"],
        "operation_reduction": w08["operation_reduction"],
        "baseline_median_elapsed_ns": w08["baseline_median_elapsed_ns"],
        "candidate_median_elapsed_ns": w08["candidate_median_elapsed_ns"],
        "outcome": w08["status"],
        "parent_record_id": parent["record_id"] if parent else None,
        "revision_number": parent["revision_number"] + 1 if parent else 1,
        "limitations": "SYNTHETIC_ONLY_NOT_REAL_USER_WORKLOAD",
        "human_review_required": True,
        "production_adopted": False,
        "owner_approved": False,
    }
    _valid_record(record)
    return record


def record_owned_experiment(root: Path, *, rows: int = 1536,
                            queries: int = 48, repeats: int = 3,
                            allow_write: bool = False,
                            at_time: datetime | None = None) -> dict:
    """One new W08 measurement; only explicit consent may persist metadata.

    The root never imports caller-supplied metrics: it *runs* W08 itself.
    Previous records are validated before any filesystem mutation.
    """
    catalog = _list_verified(root)
    result = evaluate_synthetic_library_index(
        rows=rows, queries=queries, repeats=repeats)
    parents = [x for x in catalog
               if x["dataset_sha256"] == result["dataset_sha256"]
               and x["query_count"] == queries
               and x["synthetic_item_count"] == rows
               and x["measurement_repetitions"] == repeats]
    # Highest numbered ancestor is selected, not the latest fastest wall time.
    previous = max(parents, key=lambda x: (
        x["revision_number"], x["created_utc"], x["record_id"]
    )) if parents else None
    row = _build_record(result, parent=previous, at_time=at_time)
    serialized = _canonical(row)
    if len(serialized) > MAX_BYTES:
        raise ExperienceLibraryError("unbounded experience payload")
    digest = hashlib.sha256(serialized).hexdigest()
    receipt = {
        "schema": SCHEMA,
        "record_id": digest,
        "record": row,
        "status": ("UCIE_EXPERIENCE_RECORDED_UNAPPROVED"
                   if allow_write else "EXPERIENCE_PREVIEW_NOT_SAVED"),
        "metadata_saved": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "model_weights_changed": False,
        "auto_promoted": False,
        "production_approved": False,
    }
    if not allow_write:
        return receipt
    if len(catalog) >= MAX_RECORDS:
        raise ExperienceLibraryError("experience catalog bounded capacity reached")
    folder = _root(root)
    if folder.parent.is_symlink():
        raise ExperienceLibraryError("unsafe runtime parent")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ("r_" + digest + ".json")
    fd, temporary = tempfile.mkstemp(prefix=".ucie_tmp_", dir=folder)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, target)  # atomic no-replace on Windows/Linux
        except FileExistsError:
            if target.is_symlink() or target.read_bytes() != serialized:
                raise ExperienceLibraryError("existing experience hash collision")
    finally:
        Path(temporary).unlink(missing_ok=True)
    receipt["metadata_saved"] = True
    receipt["separate_experience_files_written"] = 1
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UCIE-only P8 append-only synthetic experiment history")
    parser.add_argument("--ucie-root", type=Path,
                        default=Path(__file__).resolve().parents[2])
    parser.add_argument("--record", action="store_true",
                        help="Explicitly execute W08 and persist one UCIE-only receipt")
    parser.add_argument("--rows", type=int, default=1536)
    parser.add_argument("--queries", type=int, default=48)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    try:
        output = (record_owned_experiment(
            args.ucie_root, rows=args.rows, queries=args.queries,
            repeats=args.repeats, allow_write=True)
                  if args.record else inspect_experience_library(
                      args.ucie_root, limit=args.limit))
    except (ExperienceLibraryError, CapabilityEvaluationError, OSError,
            KeyError, TypeError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "P8_EXPERIENCE_FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "network_requests": 0, "operating_database_writes": 0,
            "production_approved": False, "auto_promoted": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(output, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
