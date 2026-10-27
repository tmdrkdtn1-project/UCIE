"""P8 experience lineage for UCIE-owned W05-linked synthetic capability trials.

Only approved-public merged PR *metadata identities* can label first-party
experiment receipts. The original upstream code is never used or tested.
An explicit --record writes to a NEW, UCIE-only bounded JSONL ledger; existing
W08/P8 experience, operating SQLite and signed Rulepacks remain untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .capability_trials import (
    SCHEMA as TRIAL_SCHEMA, RECIPES, CapabilityTrialError,
    evaluate_ucie_owned_recipe, verified_w05_cues,
)
from .public_discovery import DiscoveryError, public_feed_get, public_feed_url
from .source_registry import get_source, SourceRegistryError

SCHEMA = "UCIE_P8_W05_LINKED_CAPABILITY_EXPERIENCE_V1"
FILE_NAME = "ucie_p8_w05_capability_experience_v1.jsonl"
GENESIS = "0" * 64
MAX_BYTES = 131072
MAX_EVENTS = 90
WORKLOADS = ((128, 24), (256, 16), (512, 64))
MAX_DISPLAY = 20
RECEIPT_FIELDS = frozenset({
    "candidate_id", "source_id", "public_url", "evidence_sha256",
    "kind", "purpose_code", "recipe_id", "workload_sha256",
    "rows", "queries", "repeats", "baseline_operations", "candidate_operations",
    "baseline_median_ns", "candidate_median_ns",
    "mismatches", "equivalent", "decision", "upstream_tested",
})


class CapabilityExperienceError(ValueError):
    pass


def _encoded(obj: dict) -> bytes:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def _hash(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _file(root: Path) -> Path:
    if (not isinstance(root, Path) or root.is_symlink()
            or root.name.casefold() != "ucie" or not root.is_dir()):
        raise CapabilityExperienceError("dedicated UCIE checkout required")
    runtime = root / "runtime"
    if runtime.is_symlink() or not runtime.is_dir():
        raise CapabilityExperienceError("pre-existing UCIE runtime required")
    p = runtime / FILE_NAME
    if p.is_symlink() or (p.exists() and not p.is_file()):
        raise CapabilityExperienceError("unsafe UCIE experience ledger")
    return p


def _check_receipt(r: object) -> None:
    if type(r) is not dict or set(r) != RECEIPT_FIELDS:
        raise CapabilityExperienceError("unexpected W05 experience fields")
    purpose = r["purpose_code"]
    if purpose not in RECIPES or (r["kind"], r["recipe_id"]) != RECIPES[purpose]:
        raise CapabilityExperienceError("W05 purpose to UCIE-owned recipe mismatch")
    try:
        source = get_source(r["source_id"])
    except (SourceRegistryError, TypeError) as exc:
        raise CapabilityExperienceError("unapproved W05 provenance") from exc
    if source["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY":
        raise CapabilityExperienceError("source must be an approved public repo")
    for item in ("candidate_id", "evidence_sha256", "workload_sha256"):
        value = r[item]
        if (type(value) is not str or len(value) != 64
                or any(c not in "0123456789abcdef" for c in value)):
            raise CapabilityExperienceError("untrusted W05 revision hash")
    if (type(r["public_url"]) is not str or not r["public_url"].startswith(
            source["public_url"] + "/pull/")):
        raise CapabilityExperienceError("unbound public source URL")
    if (type(r["rows"]) is not int or type(r["queries"]) is not int
            or (r["rows"], r["queries"]) not in WORKLOADS
            or type(r["repeats"]) is not int or r["repeats"] != 3):
        raise CapabilityExperienceError("unapproved synthetic experiment")
    expected_workload = _hash(json.dumps(
        ["UCIE_SYNTHETIC_RECIPE_V1", purpose, r["rows"], r["queries"]],
        separators=(",", ":")).encode("ascii"))
    if r["workload_sha256"] != expected_workload:
        raise CapabilityExperienceError("W05 own experiment hash mismatch")
    if (type(r["baseline_operations"]) is not int
            or r["baseline_operations"] != r["rows"] * r["queries"]
            or type(r["candidate_operations"]) is not int
            or not 0 < r["candidate_operations"] <= r["baseline_operations"] * 3
            or type(r["mismatches"]) is not int or r["mismatches"] < 0
            or type(r["equivalent"]) is not bool
            or r["equivalent"] != (r["mismatches"] == 0)):
        raise CapabilityExperienceError("incorrect synthetic cost/correctness claims")
    for field in ("baseline_median_ns", "candidate_median_ns"):
        if type(r[field]) is not int or not 0 <= r[field] <= 10**12:
            raise CapabilityExperienceError("invalid bounded diagnostic timing")
    expected_decision = ("RETEST_FIRST_PARTY_RECIPE" if
                         r["equivalent"] and
                         r["candidate_operations"] < r["baseline_operations"]
                         else "HOLD_FOR_FIRST_PARTY_RECIPE_CORRECTION")
    if r["decision"] != expected_decision or r["upstream_tested"] is not False:
        raise CapabilityExperienceError("false upstream success or improvement claim")


def _load(root: Path) -> tuple[dict, ...]:
    f = _file(root)
    if not f.exists():
        return ()
    if f.stat().st_size > MAX_BYTES:
        raise CapabilityExperienceError("oversized UCIE-only experience ledger")
    events, prev, seen = [], GENESIS, set()
    try:
        lines = f.read_text(encoding="ascii").splitlines()
    except (UnicodeError, ValueError) as exc:
        raise CapabilityExperienceError("invalid experience encoding") from exc
    if len(lines) > MAX_EVENTS:
        raise CapabilityExperienceError("too many W05 experience records")
    for seq, raw in enumerate(lines, start=1):
        try:
            e = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise CapabilityExperienceError("corrupt W05 experience record") from exc
        if (type(e) is not dict or set(e) !=
                {"schema", "seq", "prev_hash", "receipt", "event_sha256"}
                or e["schema"] != SCHEMA or type(e["seq"]) is not int
                or e["seq"] != seq or e["prev_hash"] != prev):
            raise CapabilityExperienceError("broken experience lineage")
        if e["event_sha256"] != _hash(_encoded(
                {k: v for k, v in e.items() if k != "event_sha256"})):
            raise CapabilityExperienceError("changed experience record")
        r = e["receipt"]
        _check_receipt(r)
        key = (r["candidate_id"], r["workload_sha256"])
        if key in seen:
            raise CapabilityExperienceError("duplicate W05 capability trial")
        seen.add(key)
        prev = e["event_sha256"]
        events.append(e)
    return tuple(events)


def read_capability_history(root: Path, *, limit: int = 20) -> dict:
    if type(limit) is not int or not 1 <= limit <= MAX_DISPLAY:
        raise CapabilityExperienceError("invalid bounded experience page")
    events = _load(root)
    items = []
    for e in events[-limit:]:
        r = e["receipt"]
        items.append({
            "experience_id": e["event_sha256"],
            "sequence": e["seq"], "prev_hash": e["prev_hash"],
            "candidate_id": r["candidate_id"], "purpose_code": r["purpose_code"],
            "kind": r["kind"], "recipe_id": r["recipe_id"],
            "source_id": r["source_id"],
            "public_url": r["public_url"],
            "workload_sha256": r["workload_sha256"],
            "rows": r["rows"], "queries": r["queries"],
            "equivalent": r["equivalent"], "decision": r["decision"],
            "first_party_synthetic_only": True,
            "upstream_capability_verified": False,
            "approved_or_exportable": False,
        })
    return {
        "schema": SCHEMA, "status": "UCIE_FIRST_PARTY_W05_EXPERIENCE_READ_ONLY",
        "recorded_count": len(events),
        "last_event_sha256": events[-1]["event_sha256"] if events else GENESIS,
        "returned_count": len(items), "items": items,
        "source_ledger_modified": False,
        "network_requests": 0, "operating_database_writes": 0,
        "new_signatures_created": 0, "auto_promoted": False,
        "v1_accepted": False,
    }


def _write(root: Path, prior: tuple[dict, ...], receipt: dict) -> dict:
    f = _file(root)
    lock = f.with_name(f.name + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise CapabilityExperienceError("concurrent UCIE-only writer blocked") from exc
    try:
        os.close(fd)
        if _load(root) != prior:
            raise CapabilityExperienceError("experience changed since review")
        e = {"schema": SCHEMA, "seq": len(prior) + 1,
             "prev_hash": prior[-1]["event_sha256"] if prior else GENESIS,
             "receipt": receipt}
        _check_receipt(receipt)
        e["event_sha256"] = _hash(_encoded(e))
        original = f.read_bytes() if f.exists() else b""
        replacement = original + _encoded(e) + b"\n"
        if len(replacement) > MAX_BYTES or len(prior) >= MAX_EVENTS:
            raise CapabilityExperienceError("UCIE W05 ledger size limit")
        temp = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="wb", dir=f.parent, prefix=".ucie_w05_p8_", delete=False) as out:
                temp = Path(out.name)
                out.write(replacement)
                out.flush()
                os.fsync(out.fileno())
            if f.is_symlink():
                raise CapabilityExperienceError("unsafe changed ledger path")
            os.replace(temp, f)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
        return e
    finally:
        lock.unlink(missing_ok=True)


def run_capability_cycle(root: Path, *, source_rows: object,
                         source_id: str, record: bool = False,
                         now=None) -> dict:
    """Choose one *new* capability/workload, run own trial, optionally record."""
    if type(record) is not bool:
        raise CapabilityExperienceError("record must be explicit boolean")
    prior = _load(root)
    if prior and prior[-1]["receipt"]["decision"] != "RETEST_FIRST_PARTY_RECIPE":
        return {
            "schema": SCHEMA, "status": "PREVIOUS_FIRST_PARTY_FAILURE_HOLD_NO_GO",
            "recorded_count": len(prior), "new_event_written": False,
            "network_requests": 0, "operating_database_writes": 0,
            "auto_promoted": False,
        }
    cues = verified_w05_cues(source_rows, source_id=source_id, now=now)
    seen = {(e["receipt"]["candidate_id"], e["receipt"]["workload_sha256"])
            for e in prior}
    chosen = None
    for rows, queries in WORKLOADS:
        for cue in cues:
            if cue["purpose_code"] not in RECIPES:
                continue
            purpose = cue["purpose_code"]
            workhash = _hash(json.dumps(
                ["UCIE_SYNTHETIC_RECIPE_V1", purpose, rows, queries],
                separators=(",", ":")).encode("ascii"))
            if (cue["library_item_id"], workhash) not in seen:
                chosen = (cue, rows, queries)
                break
        if chosen:
            break
    if chosen is None:
        return {
            "schema": SCHEMA, "status": "NO_UNTESTED_IMPLEMENTED_W05_RECIPE",
            "recorded_count": len(prior), "source_candidate_count": len(cues),
            "unsupported_recipe_count": sum(
                cue["purpose_code"] not in RECIPES for cue in cues),
            "new_event_written": False, "network_requests": 0,
            "operating_database_writes": 0, "auto_promoted": False,
        }
    cue, rows, queries = chosen
    result = evaluate_ucie_owned_recipe(
        cue["purpose_code"], rows=rows, queries=queries, repeats=3)
    receipt = {
        "candidate_id": cue["library_item_id"],
        "source_id": cue["source_id"],
        "public_url": cue["public_url"],
        "evidence_sha256": cue["evidence_sha256"],
        "kind": result["kind"], "purpose_code": result["purpose_code"],
        "recipe_id": result["recipe_id"],
        "workload_sha256": result["workload_sha256"],
        "rows": rows, "queries": queries, "repeats": 3,
        "baseline_operations": result["baseline_operations"],
        "candidate_operations": result["candidate_operations_including_setup"],
        "baseline_median_ns": result["baseline_median_elapsed_ns"],
        "candidate_median_ns": result["candidate_median_elapsed_ns"],
        "mismatches": result["mismatched_queries_across_repetitions"],
        "equivalent": result["exact_result_equivalence_observed"],
        "decision": ("RETEST_FIRST_PARTY_RECIPE"
                     if result["synthetic_operation_reduction_observed"]
                     else "HOLD_FOR_FIRST_PARTY_RECIPE_CORRECTION"),
        "upstream_tested": False,
    }
    _check_receipt(receipt)
    event = _write(root, prior, receipt) if record else None
    return {
        "schema": SCHEMA,
        "status": ("W05_FIRST_PARTY_EXPERIENCE_RECORDED_NO_GO" if event else
                   "W05_FIRST_PARTY_EXPERIENCE_PREVIEW_ONLY_NO_GO"),
        "source_candidate_count": len(cues),
        "recorded_before": len(prior),
        "candidate_id": cue["library_item_id"],
        "purpose_code": cue["purpose_code"],
        "kind": cue["kind"],
        "trial_receipt": receipt,
        "experiment_outcome": result["status"],
        "next_decision": receipt["decision"],
        "event_sha256": event["event_sha256"] if event else None,
        "new_event_written": event is not None,
        "ucie_isolated_ledger_writes": 1 if event else 0,
        "existing_w08_p8_ledger_changed": False,
        "upstream_code_executed": False,
        "upstream_capability_verified": False,
        "production_code_changed": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "model_weights_changed": False,
        "auto_promoted": False, "v1_accepted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UCIE W05 -> P8 one-shot, bounded, opt-in experience cycle")
    parser.add_argument("--ucie-root", required=True, type=Path)
    parser.add_argument("--source-id", choices=[
        "repo:python/cpython", "repo:PowerShell/PowerShell", "repo:git/git",
        "repo:modelcontextprotocol/python-sdk", "repo:actions/runner-images",
    ])
    parser.add_argument("--live", action="store_true",
                        help="Explicit one original approved GitHub public PR GET")
    parser.add_argument("--record", action="store_true",
                        help="Explicitly persist ONE UCIE-owned synthetic experience")
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    try:
        if args.history:
            if args.live or args.record or args.source_id:
                raise CapabilityExperienceError("read-only history mode only")
            output = read_capability_history(args.ucie_root)
        elif args.live and args.source_id:
            _file(args.ucie_root)  # reject unsupported roots before any public GET
            source = get_source(args.source_id)
            if source["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY":
                raise CapabilityExperienceError("unapproved positive source")
            repo = args.source_id.removeprefix("repo:")
            rows = public_feed_get(public_feed_url(repo))
            output = run_capability_cycle(
                args.ucie_root, source_rows=rows, source_id=args.source_id,
                record=args.record)
            output["explicit_public_gets"] = 1
            output["network_requests"] = 1
        elif args.record or args.live:
            raise CapabilityExperienceError(
                "record requires explicit --live and exact --source-id")
        else:
            output = {
                "schema": SCHEMA, "status": "PUBLIC_REVIEW_GET_NOT_REQUESTED_NO_GO",
                "network_requests": 0, "operating_database_writes": 0,
                "auto_promoted": False,
            }
    except (CapabilityExperienceError, CapabilityTrialError,
            SourceRegistryError, DiscoveryError, OSError, ValueError) as exc:
        output = {
            "schema": SCHEMA, "status": "FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "operating_database_writes": 0, "auto_promoted": False,
        }
        print(json.dumps(output, sort_keys=True))
        return 2
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
