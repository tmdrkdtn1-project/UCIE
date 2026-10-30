"""P9 safe retest of UCIE-authored P11 improvement-review proposals.

A replay of existing, unapproved P11 decisions; NOT autonomous production
code adoption, external source evaluation, model training, or promotion.
The operator can inspect a bounded number of existing review rows without
writing any UCIE operating database, code, task, or release artifact.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from . import p11_closed_loop as p11
from .capability_trials import RECIPES, evaluate_ucie_owned_recipe
from .p11_improvement_gate import (
    assess_new, ImprovementGateError, PROPOSAL, STOP, GOOD, HOLD,
)
from .public_discovery import SOURCES

SCHEMA = "UCIE_P9_FIRST_PARTY_IMPROVEMENT_RETEST_V1"
WORKLOADS = (128, 256, 512)
MAX_RETEST_ITEMS = 3
DIGITS = frozenset("0123456789abcdef")


class P9RetestError(ValueError):
    pass


def _digest(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(c in DIGITS for c in value))


def _rows(db: Path, limit: int, source: str | None,
          pr_number: int | None) -> list[sqlite3.Row]:
    uri = db.as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=0.25)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('improvement_review','experience','leads')")}
        if not {"leads", "experience"}.issubset(tables):
            raise P9RetestError("P11 provenance tables missing")
        if "improvement_review" not in tables:
            return []  # 65 old experiences are NOT auto-backfilled P8 reviews.
        selector = ""
        args: list[object] = []
        if source is not None:
            selector = "WHERE r.source=? AND r.pr_number=?"
            args.extend((source, pr_number))
        args.append(limit)
        return conn.execute(
            "SELECT r.source,r.pr_number,r.receipt_sha256 AS review_sha,"
            "r.recipe AS review_recipe,r.workload AS review_workload,"
            "r.decision,r.mismatches,r.operation_reduction_ppm,"
            "r.observed_at AS reviewed_at,"
            "e.receipt_sha256 AS experience_sha,e.recipe,e.workload,"
            "e.baseline_ops,e.candidate_ops,e.exact_equal,e.hypothesis_status,"
            "l.commit_sha,l.title_sha256,l.reviewed,l.merged_at "
            "FROM improvement_review AS r "
            "LEFT JOIN experience AS e USING(source,pr_number) "
            "LEFT JOIN leads AS l USING(source,pr_number) "
            + selector +
            " ORDER BY r.observed_at DESC,r.source,r.pr_number LIMIT ?",
            tuple(args),
        ).fetchall()


def _validate_record(row: dict) -> None:
    if (row["source"] not in SOURCES
            or type(row["pr_number"]) is not int
            or not 1 <= row["pr_number"] <= 999999999
            or not _digest(row["review_sha"])
            or row["review_sha"] != row["experience_sha"]
            or row["review_recipe"] not in RECIPES
            or row["recipe"] != row["review_recipe"]
            or row["review_workload"] not in WORKLOADS
            or row["workload"] != row["review_workload"]
            or type(row["baseline_ops"]) is not int
            or type(row["candidate_ops"]) is not int
            or not 0 < row["baseline_ops"] <= 100000
            or not 0 < row["candidate_ops"] <= 100000
            or row["exact_equal"] not in (0, 1)
            or row["hypothesis_status"] not in (GOOD, HOLD)
            or row["decision"] not in (PROPOSAL, STOP)
            or row["reviewed"] != 1
            or not _digest(row["title_sha256"])
            or (row["commit_sha"] is not None
                and (type(row["commit_sha"]) is not str
                     or len(row["commit_sha"]) != 40
                     or any(c not in DIGITS for c in row["commit_sha"])))
            or type(row["mismatches"]) is not int
            or not 0 <= row["mismatches"] <= 48
            or type(row["operation_reduction_ppm"]) is not int
            or not 0 <= row["operation_reduction_ppm"] <= 1000000):
        raise P9RetestError("P11 review/experience/source linkage invalid")
    try:
        p11._parse(row["reviewed_at"])
        p11._parse(row["merged_at"])
    except (ValueError, TypeError) as exc:
        raise P9RetestError("P11 review chronology invalid") from exc

    good = (row["exact_equal"] == 1 and
            row["candidate_ops"] < row["baseline_ops"])
    ppm = (max(0, (row["baseline_ops"] - row["candidate_ops"])
                * 1000000 // row["baseline_ops"]) if good else 0)
    if ((row["decision"] == PROPOSAL) != good
            or (row["hypothesis_status"] == GOOD) != good
            or row["operation_reduction_ppm"] != ppm
            or (row["mismatches"] == 0) != (row["exact_equal"] == 1)):
        raise P9RetestError("P11 historical gate data contradicts metrics")


def _original_receipt(row: dict, evaluation: dict) -> str:
    body = json.dumps({
        "source": row["source"], "pr_number": row["pr_number"],
        "merge_sha": row["commit_sha"],
        "title_sha256": row["title_sha256"],
        "recipe_id": evaluation["recipe_id"],
        "workload_sha256": evaluation["workload_sha256"],
        "exact_equal": evaluation["exact_result_equivalence_observed"] is True,
        "baseline_ops": evaluation["baseline_operations"],
        "candidate_ops": evaluation["candidate_operations_including_setup"],
        "review_status": GOOD if evaluation["synthetic_operation_reduction_observed"]
                         else HOLD,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(body.encode("ascii")).hexdigest()


def _retest_one(record: sqlite3.Row) -> dict:
    row = dict(record)
    _validate_record(row)
    recipe, original = row["recipe"], row["workload"]
    attempts = []
    for workload in (original,) + tuple(w for w in WORKLOADS if w != original):
        result = evaluate_ucie_owned_recipe(
            recipe, rows=workload, queries=24, repeats=2)
        # Reuse original strict first-party gate: any forged assertion or
        # upstream-code/network/side effect must fail CLOSED.
        gate = assess_new(result, recipe=recipe, workload=workload)
        same_metrics = (
            workload != original or (
                row["baseline_ops"] == result["baseline_operations"]
                and row["candidate_ops"] == result["candidate_operations_including_setup"]
                and row["exact_equal"] == int(
                    result["exact_result_equivalence_observed"])
                and row["review_sha"] == _original_receipt(row, result)
            )
        )
        attempts.append({
            "workload": workload,
            "decision": gate["decision"],
            "exact_result_equivalence": result[
                "exact_result_equivalence_observed"],
            "mismatched_queries": gate["mismatched_queries"],
            "operation_reduction_ppm": gate["relative_operation_reduction_ppm"],
            "historical_receipt_reproduced": (
                same_metrics if workload == original else None),
            "workload_sha256": result["workload_sha256"],
        })
    # A previous STOP cannot be silently cleared by later synthetic results.
    all_good = (row["decision"] == PROPOSAL and all(
        item["decision"] == PROPOSAL
        and item["exact_result_equivalence"]
        and item["historical_receipt_reproduced"] is not False
        for item in attempts))
    decision = (
        "FIRST_PARTY_RETEST_PASS_MANUAL_REVIEW_ONLY" if all_good else
        "FIRST_PARTY_RETEST_REGRESSION_HOLD_NO_GO"
    )
    canonical = json.dumps({
        "source": row["source"], "pr_number": row["pr_number"],
        "original_receipt_sha256": row["review_sha"],
        "decision": decision, "attempts": attempts,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {
        "source_id": "repo:" + row["source"],
        "pr_number": row["pr_number"],
        "original_receipt_sha256": row["review_sha"],
        "retest_decision": decision,
        "retest_receipt_sha256": sha256(canonical.encode("ascii")).hexdigest(),
        "workloads_checked": len(attempts),
        "trials": attempts,
        "original_regression_hold_preserved": row["decision"] == STOP,
        "production_code_adopted": False,
        "automatically_approved": False,
        "upstream_fix_validated": False,
    }


def retest(root: Path, *, limit: int = MAX_RETEST_ITEMS,
           source: str | None = None, pr_number: int | None = None) -> dict:
    if (type(limit) is not int or not 1 <= limit <= MAX_RETEST_ITEMS
            or (source is None) != (pr_number is None)
            or (source is not None and
                (source not in SOURCES or type(pr_number) is not int
                 or not 1 <= pr_number <= 999999999))):
        raise P9RetestError("only bounded approved P11 retest selectors")
    db, _ = p11._paths(Path(root))
    if not p11.enabled(Path(root)):
        return {
            "schema": SCHEMA, "status": "P9_P11_NOT_ENABLED_READ_ONLY",
            "review_rows_checked": 0, "items": [],
            "production_code_adopted": False, "auto_promoted": False,
            "operating_database_writes": 0, "network_requests": 0,
        }
    rows = _rows(db, limit, source, pr_number)
    items = [_retest_one(record) for record in rows]
    return {
        "schema": SCHEMA,
        "status": ("P9_FIRST_PARTY_RETEST_COMPLETE_UNADOPTED" if items
                   else "P9_NO_NEW_IMPROVEMENT_REVIEW_READ_ONLY"),
        "review_rows_checked": len(items),
        "eligible_for_manual_review_only": sum(
            x["retest_decision"] == "FIRST_PARTY_RETEST_PASS_MANUAL_REVIEW_ONLY"
            for x in items),
        "regression_holds": sum(
            x["retest_decision"] == "FIRST_PARTY_RETEST_REGRESSION_HOLD_NO_GO"
            for x in items),
        "items": items,
        "all_workloads_first_party_synthetic": True,
        "historical_experiences_backfilled": False,
        "production_code_adopted": False,
        "auto_promoted": False,
        "rule_signed": False,
        "model_weights_changed": False,
        "operating_database_writes": 0,
        "scheduler_modified": False,
        "network_requests": 0,
    }


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--ucie-root", required=True, type=Path)
    cli.add_argument("--limit", type=int, default=MAX_RETEST_ITEMS)
    cli.add_argument("--source", choices=SOURCES)
    cli.add_argument("--pr-number", type=int)
    args = cli.parse_args()
    try:
        outcome = retest(
            args.ucie_root, limit=args.limit,
            source=args.source, pr_number=args.pr_number)
    except (P9RetestError, p11.P11Error, ImprovementGateError,
            sqlite3.Error, OSError, ValueError, KeyError, TypeError) as exc:
        outcome = {
            "schema": SCHEMA, "status": "P9_RETEST_FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "review_rows_checked": 0,
            "operating_database_writes": 0, "auto_promoted": False,
        }
    print(json.dumps(outcome, ensure_ascii=True, sort_keys=True))
    return 2 if outcome["status"] == "P9_RETEST_FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
