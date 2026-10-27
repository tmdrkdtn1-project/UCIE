"""P8: bounded UCIE-owned experiment -> observation -> next experiment loop.

Runs W08 code on *first-party synthetic only* inputs. Keeps a tamper-evident
small local experience log when explicitly requested, chooses the next
previously untested workload and produces a reviewable improvement hypothesis.

No external project telemetry, PR text, model training, scheduler, production
index swap, owner approval, rule signing or unattended distribution.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .capability_evaluator import (
    EXPERIMENT_ID, evaluate_synthetic_library_index,
    synthetic_catalog, CapabilityEvaluationError,
)

SCHEMA = "UCIE_P8_EXPERIENCE_EVOLUTION_V1"
LEDGER_SCHEMA = "UCIE_P8_EXPERIENCE_LEDGER_EVENT_V1"
FILE_NAME = "ucie_p8_experience_v1.jsonl"
MAX_BYTES = 65536
GENESIS = "0" * 64
# Workload changes are the first feedback questions, not assumed improvements.
WORKLOADS = ((256, 16), (4096, 16), (1536, 96), (4096, 96))
REPEATS = 3
# Owner-provided *observed*, not independently authenticated, W08 result.
OWNER_OBSERVED_REFERENCE = {
    "experiment_id": EXPERIMENT_ID,
    "rows": 1536, "queries": 48, "repeats": 3,
    "dataset_sha256": "cd68799042a9c6c57b15100947541f16731d4cfd18efe6088db85264e92227f7",
    "baseline_operations": 73728, "candidate_operations": 1584,
    "baseline_median_ns": 6409500, "candidate_median_ns": 218100,
    "result_equivalent": True,
    "provenance": "OWNER_OBSERVED_RECEIPT_NOT_INDEPENDENTLY_AUTHENTICATED",
}

RESULT_FIELDS = frozenset({
    "experiment_id", "dataset_sha256", "rows", "queries", "repeats",
    "baseline_operations", "candidate_operations",
    "baseline_median_ns", "candidate_median_ns",
    "result_equivalent", "decision", "source_kind",
})
DECISIONS = frozenset({
    "SYNTHETIC_CANDIDATE_WORTH_MORE_TESTING",
    "REJECT_OR_REVISE_SYNTHETIC_CANDIDATE",
})


class EvolutionError(ValueError):
    pass


def _digest_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _canonical(obj: dict) -> bytes:
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=True, allow_nan=False,
        separators=(",", ":")).encode("ascii")


def _workload_id(rows: int, queries: int) -> str:
    return f"ROWS_{rows}_QUERIES_{queries}"


def _catalog_hash(rows: int) -> str:
    dataset = [
        [r.synthetic_id, r.source_id, r.domain, r.kind, r.purpose]
        for r in synthetic_catalog(rows)
    ]
    return _digest_bytes(json.dumps(
        dataset, separators=(",", ":"), ensure_ascii=True).encode("ascii"))


def _check_receipt(row: object) -> None:
    if type(row) is not dict or set(row) != RESULT_FIELDS:
        raise EvolutionError("unexpected synthetic experience receipt schema")
    if row["experiment_id"] != EXPERIMENT_ID:
        raise EvolutionError("experiment lineage does not match W08")
    rows, queries, repeats = row["rows"], row["queries"], row["repeats"]
    if ((rows, queries) not in WORKLOADS or type(rows) is not int
            or type(queries) is not int or type(repeats) is not int
            or repeats != REPEATS):
        raise EvolutionError("unapproved or duplicate workload parameters")
    if row["dataset_sha256"] != _catalog_hash(rows):
        raise EvolutionError("synthetic dataset provenance digest mismatch")
    if (type(row["baseline_operations"]) is not int
            or row["baseline_operations"] != rows * queries
            or type(row["candidate_operations"]) is not int
            or row["candidate_operations"] != rows + queries):
        raise EvolutionError("reference/index operation counts do not reconcile")
    for field in ("baseline_median_ns", "candidate_median_ns"):
        if type(row[field]) is not int or row[field] < 0 or row[field] > 10**12:
            raise EvolutionError("invalid bounded timing observation")
    if type(row["result_equivalent"]) is not bool:
        raise EvolutionError("invalid correctness evidence")
    expected = ("SYNTHETIC_CANDIDATE_WORTH_MORE_TESTING"
                if row["result_equivalent"] and rows * queries > rows + queries
                else "REJECT_OR_REVISE_SYNTHETIC_CANDIDATE")
    if row["decision"] != expected or row["decision"] not in DECISIONS:
        raise EvolutionError("inconsistent experiment decision")
    if row["source_kind"] != "UCIE_FIRST_PARTY_SYNTHETIC_EXECUTION":
        raise EvolutionError("private or external inputs must not enter P8")


def _ledger_path(root: Path) -> Path:
    if not isinstance(root, Path) or root.is_symlink() or (
            root.name.casefold() != "ucie" or not root.is_dir()):
        raise EvolutionError("dedicated UCIE checkout required")
    runtime = root / "runtime"
    if runtime.is_symlink() or not runtime.is_dir():
        raise EvolutionError("existing dedicated UCIE runtime directory required")
    ledger = runtime / FILE_NAME
    if ledger.is_symlink() or (ledger.exists() and not ledger.is_file()):
        raise EvolutionError("unsafe UCIE evolution ledger path")
    return ledger


def _load_events(root: Path) -> tuple[dict, ...]:
    ledger = _ledger_path(root)
    if not ledger.exists():
        return ()
    if ledger.stat().st_size > MAX_BYTES:
        raise EvolutionError("bounded UCIE evolution ledger exceeded")
    lines = ledger.read_text(encoding="ascii").splitlines()
    if len(lines) > len(WORKLOADS) or any(not s for s in lines):
        raise EvolutionError("invalid append-only experience event count")
    events, parent = [], GENESIS
    seen = set()
    for seq, raw in enumerate(lines, start=1):
        try:
            event = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise EvolutionError("malformed experience ledger") from exc
        if (type(event) is not dict or set(event) != {
                "schema", "seq", "prev_hash", "receipt", "event_sha256"}
                or event["schema"] != LEDGER_SCHEMA
                or type(event["seq"]) is not int or event["seq"] != seq
                or event["prev_hash"] != parent):
            raise EvolutionError("experience event chain/order mismatch")
        body = {k: v for k, v in event.items() if k != "event_sha256"}
        if event["event_sha256"] != _digest_bytes(_canonical(body)):
            raise EvolutionError("experience event integrity failure")
        _check_receipt(event["receipt"])
        case = (event["receipt"]["rows"], event["receipt"]["queries"])
        if case in seen:
            raise EvolutionError("duplicate experiment scenario in UCIE experience ledger")
        seen.add(case)
        parent = event["event_sha256"]
        events.append(event)
    return tuple(events)


def _capture_w08(result: dict) -> dict:
    """Only local W08 runtime results; no arbitrary JSON import permitted."""
    if (type(result) is not dict
            or result.get("schema") != "UCIE_W08_OWNED_SYNTHETIC_CAPABILITY_EVALUATION_V1"
            or result.get("experiment_id") != EXPERIMENT_ID
            or result.get("public_source_data_used") is not False
            or result.get("project_data_accessed") is not False
            or result.get("database_writes") != 0
            or result.get("network_requests") != 0
            or result.get("auto_promoted") is not False
            or result.get("model_weights_changed") is not False
            or result.get("production_approved") is not False
            or result.get("owner_approved") is not False):
        raise EvolutionError("W08 local synthetic experiment contract changed")
    receipt = {
        "experiment_id": result["experiment_id"],
        "dataset_sha256": result["dataset_sha256"],
        "rows": result["synthetic_item_count"],
        "queries": result["query_count"],
        "repeats": result["measurement_repetitions"],
        "baseline_operations": result["reference_comparisons_per_run"],
        "candidate_operations": result["candidate_build_plus_lookup_operations_per_run"],
        "baseline_median_ns": result["baseline_median_elapsed_ns"],
        "candidate_median_ns": result["candidate_median_elapsed_ns"],
        "result_equivalent": result["exact_result_equivalence_observed"],
        "decision": (
            "SYNTHETIC_CANDIDATE_WORTH_MORE_TESTING"
            if result["exact_result_equivalence_observed"]
            and result["operation_reduction"] > 0
            else "REJECT_OR_REVISE_SYNTHETIC_CANDIDATE"),
        "source_kind": "UCIE_FIRST_PARTY_SYNTHETIC_EXECUTION",
    }
    _check_receipt(receipt)
    if (result["mismatched_query_count"] != 0) == receipt["result_equivalent"]:
        raise EvolutionError("W08 correctness counters disagree")
    return receipt


def _write_event(root: Path, prior: tuple[dict, ...], receipt: dict) -> dict:
    """Atomically replace one small UCIE-only ledger under an exclusive lock."""
    ledger = _ledger_path(root)
    lock = ledger.with_name(ledger.name + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise EvolutionError("concurrent UCIE evolution writer refused") from exc
    try:
        os.close(fd)
        # Detect any unexpected file changes after preview/history replay.
        if _load_events(root) != prior:
            raise EvolutionError("experience ledger changed during evaluation")
        if any((e["receipt"]["rows"], e["receipt"]["queries"]) ==
               (receipt["rows"], receipt["queries"]) for e in prior):
            raise EvolutionError("duplicate experiment not recorded")
        event = {
            "schema": LEDGER_SCHEMA,
            "seq": len(prior) + 1,
            "prev_hash": prior[-1]["event_sha256"] if prior else GENESIS,
            "receipt": receipt,
        }
        event["event_sha256"] = _digest_bytes(_canonical(event))
        previous = ledger.read_bytes() if ledger.exists() else b""
        new_bytes = previous + _canonical(event) + b"\n"
        if len(new_bytes) > MAX_BYTES:
            raise EvolutionError("UCIE evolution ledger limit exceeded")
        tmpname = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="wb", dir=ledger.parent, prefix=".ucie_p8_",
                    delete=False) as fh:
                tmpname = Path(fh.name)
                fh.write(new_bytes)
                fh.flush()
                os.fsync(fh.fileno())
            if ledger.is_symlink():
                raise EvolutionError("unsafe ledger changed to symlink")
            os.replace(tmpname, ledger)
        finally:
            if tmpname is not None:
                tmpname.unlink(missing_ok=True)
        return event
    finally:
        lock.unlink(missing_ok=True)


def run_evolution_cycle(root: Path, *, record: bool = False) -> dict:
    """Execute exactly one *new* synthetic experiment, optionally persist.

    The next experiment is selected from not-yet-run scenarios. A negative
    result holds future iterations until reviewed; no auto-repair/auto-apply.
    """
    if type(record) is not bool:
        raise EvolutionError("explicit recording flag required")
    prior = _load_events(root)
    observed = {(e["receipt"]["rows"], e["receipt"]["queries"]) for e in prior}
    prev = prior[-1]["receipt"] if prior else None
    if prev and prev["decision"] != "SYNTHETIC_CANDIDATE_WORTH_MORE_TESTING":
        status, selected = "NEGATIVE_EXPERIENCE_HOLD_FOR_REVIEW", None
    else:
        selected = next((case for case in WORKLOADS if case not in observed), None)
        status = ("NEXT_SYNTHETIC_EXPERIMENT_SELECTED" if selected
                  else "NO_UNTESTED_SYNTHETIC_SCENARIOS")
    if selected is None:
        return {
            "schema": SCHEMA,
            "status": status,
            "owner_observed_reference": OWNER_OBSERVED_REFERENCE,
            "local_recorded_experiments": len(prior),
            "last_event_sha256": prior[-1]["event_sha256"] if prior else GENESIS,
            "new_experiment_executed": False, "new_event_written": False,
            "network_requests": 0, "operating_database_writes": 0,
            "auto_promoted": False, "v1_accepted": False,
        }
    rows, queries = selected
    evaluated = evaluate_synthetic_library_index(
        rows=rows, queries=queries, repeats=REPEATS)
    receipt = _capture_w08(evaluated)
    event = _write_event(root, prior, receipt) if record else None
    positive = receipt["decision"] == "SYNTHETIC_CANDIDATE_WORTH_MORE_TESTING"
    next_case = next((case for case in WORKLOADS
                      if case not in observed and case != selected), None) if positive else None
    return {
        "schema": SCHEMA,
        "status": ("EXPERIENCE_RECORDED_SYNTHETIC_NO_GO" if event else
                   "EXPERIENCE_PREVIEW_SYNTHETIC_NOT_PERSISTED_NO_GO"),
        "experiment_id": EXPERIMENT_ID,
        "current_workload": _workload_id(rows, queries),
        "owner_observed_reference": OWNER_OBSERVED_REFERENCE,
        "local_recorded_experiments_before": len(prior),
        "receipt": receipt,
        "hypothesis": (
            "HASH_INDEX_REDUCES_EXACT_QUERY_OPERATIONS_BUT_NEEDS_DIVERSE_WORKLOADS"
            if positive else "EXACT_RESULT_MISMATCH_OR_OPERATION_REGRESSION_REQUIRES_FIX"),
        "next_experiment": (
            {"rows": next_case[0], "queries": next_case[1],
             "purpose": "TEST_DIFFERENT_SYNTHETIC_WORKLOAD_AND_CHECK_CORRECTNESS"}
            if next_case else None),
        "next_decision": ("RETAIN_ONLY_AS_UNAPPROVED_SYNTHETIC_HYPOTHESIS"
                          if positive else "HOLD_FOR_MANUAL_DIAGNOSIS"),
        "measured_real_library_benefit": False,
        "new_experiment_executed": True,
        "new_event_written": event is not None,
        "event_sha256": event["event_sha256"] if event else None,
        "next_cycle_requires_new_explicit_invocation": True,
        "model_weights_changed": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "ucie_isolated_ledger_writes": 1 if event is not None else 0,
        "other_projects_accessed": False,
        "auto_promoted": False,
        "owner_approved": False,
        "production_algorithm_changed": False,
        "v1_accepted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UCIE P8 synthetic knowledge evolution: one bounded experiment")
    parser.add_argument("--ucie-root", type=Path, required=True)
    parser.add_argument("--record", action="store_true",
                        help="Explicitly append first-party metrics to isolated UCIE runtime ledger")
    args = parser.parse_args()
    try:
        result = run_evolution_cycle(args.ucie_root, record=args.record)
    except (EvolutionError, CapabilityEvaluationError, OSError, ValueError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "P8_EVOLUTION_FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "auto_promoted": False, "operating_database_writes": 0,
            "v1_accepted": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
