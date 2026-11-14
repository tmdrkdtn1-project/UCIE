"""UCIE W04 real public-only read-only search timing baseline; no UI changes.

The owner-only execution reads *only* D:/UCIE's existing source-linked
Stage 10/12/15 public evidence with the existing validated readers.
Measurement is not a performance gain, acceptance of candidates, or release.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from typing import Any, Callable

SCHEMA = "UCIE_W04_OWNER_PUBLIC_ONLY_READONLY_PERF_BASELINE_V01"
QUERIES = ("python", "git", "api")
EXPECTED_OWNER_ROOT = Path("D:/UCIE")
WARMUPS = 1
MEMORY_SAMPLES = 12
END_TO_END_SAMPLES = 4


class BaselineError(ValueError):
    pass


def owner_root() -> Path:
    if os.name != "nt":
        raise BaselineError("WINDOWS_UCIE_OWNER_ONLY")
    root = EXPECTED_OWNER_ROOT
    if root.is_symlink() or not root.is_dir():
        raise BaselineError("EXACT_UCIE_ROOT_REQUIRED")
    if root.resolve() != Path("D:/UCIE").resolve():
        raise BaselineError("UCIE_ROOT_CHANGED")
    if not (root / ".git").is_dir():
        raise BaselineError("UCIE_GIT_REPOSITORY_REQUIRED")
    return root


def checked(result: Any) -> tuple[int, int, int]:
    """Accept only the existing W04 no-go, read-only result shape."""
    if type(result) is not dict:
        raise BaselineError("SEARCH_RESULT_NOT_OBJECT")
    if (result.get("schema") != "UCIE_W04_READ_ONLY_LIBRARY_CANDIDATE_SEARCH_V1"
            or result.get("status") != "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO"
            or result.get("network_requests") != 0
            or result.get("operating_database_writes") != 0
            or result.get("approved_or_exportable_items") != 0
            or result.get("auto_promoted") is not False
            or result.get("v1_library_accepted") is not False):
        raise BaselineError("UNSAFE_OR_INCOMPLETE_W04_RESULT")
    count, total, returned = (result.get(k) for k in (
        "source_linked_count", "total_matches", "returned_count"))
    if (type(count) is not int or not 0 < count <= 20_000
            or type(total) is not int or not 0 <= total <= count
            or type(returned) is not int or not 0 <= returned <= min(total, 10)):
        raise BaselineError("SEARCH_COUNT_MISMATCH")
    rows = result.get("items")
    if type(rows) is not list or len(rows) != returned:
        raise BaselineError("UNSAFE_W04_ITEMS")
    if any(type(row) is not dict or row.get("export_allowed") is not False
           or row.get("human_approved") is not False
           or row.get("lifecycle") != "UNVERIFIED_CANDIDATE_ONLY"
           for row in rows):
        raise BaselineError("UNVERIFIED_ITEM_FLAG_DRIFT")
    return count, total, returned


def _measured(fn: Callable[[], Any], count: int) -> tuple[dict, Any]:
    if type(count) is not int or not 1 <= count <= 20:
        raise BaselineError("INVALID_TIMING_REPEAT_COUNT")
    durations = []
    last = None
    for _ in range(count):
        start = perf_counter_ns()
        last = fn()
        durations.append(perf_counter_ns() - start)
    return {
        "samples": count,
        "median_ms": round(median(durations) / 1_000_000, 3),
        "min_ms": round(min(durations) / 1_000_000, 3),
        "max_ms": round(max(durations) / 1_000_000, 3),
    }, last


def measure_w04(
    root: Path,
    loader: Callable[[Path], Any],
    search: Callable[..., dict],
    full_search: Callable[..., dict],
    *,
    mem_samples: int = MEMORY_SAMPLES,
    full_samples: int = END_TO_END_SAMPLES,
) -> dict[str, Any]:
    if root.name.lower() != "ucie" or root.is_symlink():
        raise BaselineError("INVALID_UCIE_MEASUREMENT_ROOT")
    if type(mem_samples) is not int or not 2 <= mem_samples <= 20:
        raise BaselineError("INVALID_MEMORY_SAMPLE_COUNT")
    if type(full_samples) is not int or not 2 <= full_samples <= 10:
        raise BaselineError("INVALID_FULL_SAMPLE_COUNT")

    handoff = loader(root)
    if (type(handoff) is not dict
            or handoff.get("status") != "LINKED_UNVERIFIED_NO_GO"
            or handoff.get("approved_rules") != 0
            or handoff.get("auto_promoted") is not False
            or handoff.get("production_approved") is not False):
        raise BaselineError("HANDOFF_NOT_FULLY_LINKED")
    before_items = handoff.get("linked_revisions")
    if type(before_items) is not int or not 0 < before_items <= 20_000:
        raise BaselineError("PUBLIC_CANDIDATE_COUNT_INVALID")
    results = []
    for query in QUERIES:
        baseline = search(handoff, query=query, limit=10)
        initial = checked(baseline)
        if initial[0] != before_items:
            raise BaselineError("PUBLIC_LEDGER_COUNT_CHANGED")
        for _ in range(WARMUPS):
            if checked(search(handoff, query=query, limit=10)) != initial:
                raise BaselineError("WARMUP_SEARCH_RESULT_DRIFT")
        memory, last = _measured(
            lambda: search(handoff, query=query, limit=10), mem_samples)
        if checked(last) != initial:
            raise BaselineError("IN_MEMORY_SEARCH_CHANGED")

        end_to_end, last = _measured(
            lambda: full_search(root, query=query, limit=10), full_samples)
        if checked(last) != initial:
            raise BaselineError("END_TO_END_PUBLIC_RESULT_CHANGED")
        results.append({
            "query": query,
            "candidate_revision_matches_not_approved_rules": initial[1],
            "returned_count": initial[2],
            "preloaded_handoff_in_memory_filter": memory,
            "full_readonly_ledger_to_response": end_to_end,
        })
    return {
        "schema": SCHEMA,
        "status": "OWNER_PUBLIC_READONLY_LATENCY_BASELINE_OBSERVED",
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "public_linked_candidate_revisions_not_approved_rules": before_items,
        "query_patterns": list(QUERIES),
        "results": results,
        "performance_improvement_claimed": False,
        "full_browser_page_render_timed": False,
        "backend_memory_peak_measured": False,
        "operating_database_writes_by_measurer": 0,
        "external_network_requests_by_measurer": 0,
        "customer_release_authorized": False,
        "ui_modified": False,
        "source_approval_changed": False,
    }


def run_owner() -> dict[str, Any]:
    root = owner_root()
    from ucie_miner.verification_handoff import prepare_verification_handoff
    from ucie_miner.library_search import (
        search_existing_public_library, search_linked_public_candidates,
    )
    return measure_w04(
        root, prepare_verification_handoff, search_linked_public_candidates,
        search_existing_public_library,
    )


def main() -> int:
    receipt = run_owner()
    print("UCIE_W04_READONLY_OWNER_LATENCY=" + json.dumps(
        receipt, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
