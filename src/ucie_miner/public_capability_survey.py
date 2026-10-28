"""W05: bounded survey of ONLY the five already approved public PR metadata feeds.

The one-page python/cpython title-cue zero did not establish absence of positive
capabilities. Explicitly survey selected approved sources, reusing their
original immutable GitHub metadata route and W05 source/merge verification.

No upstream code execution, raw title retention, automatic signing, project
data, operating database, scheduling or approval. An optional one-shot
experiment runs only an independently implemented UCIE synthetic algorithm.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json

from .capability_trials import (
    RECIPES, CapabilityTrialError, evaluate_ucie_owned_recipe,
    validate_w05_page_bundle,
)
from .public_discovery import (
    SOURCES, MAX_BACKFILL_PAGES, DiscoveryError, public_feed_url,
    public_feed_get,
)
from .source_registry import get_source, SourceRegistryError

SCHEMA = "UCIE_W05_APPROVED_PUBLIC_SOURCE_SURVEY_V1"
MAX_SOURCES = len(SOURCES)
MAX_RETURNED = 10
ALLOWED = tuple("repo:" + source for source in SOURCES)


class PublicSourceSurveyError(ValueError):
    pass


def _validate_plan(source_ids: object, pages: object, limit: object,
                   try_first_party: object) -> tuple[tuple[str, str], ...]:
    if (type(source_ids) is not tuple or not 1 <= len(source_ids) <= MAX_SOURCES
            or len(set(source_ids)) != len(source_ids)
            or type(pages) is not int or not 1 <= pages <= MAX_BACKFILL_PAGES
            or type(limit) is not int or not 1 <= limit <= MAX_RETURNED
            or type(try_first_party) is not bool):
        raise PublicSourceSurveyError("bounded explicit approved survey required")
    planned = []
    for source_id in source_ids:
        if type(source_id) is not str or source_id not in ALLOWED:
            raise PublicSourceSurveyError("unapproved source in survey")
        try:
            source = get_source(source_id)
        except SourceRegistryError as exc:
            raise PublicSourceSurveyError("unapproved source in registry") from exc
        if source["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY":
            raise PublicSourceSurveyError("only public approved PR metadata allowed")
        repo = source_id.removeprefix("repo:")
        for page in range(1, pages + 1):
            # Validate every URL before making any callback call.
            public_feed_url(repo, page=page)
        planned.append((source_id, repo))
    return tuple(planned)


def survey_approved_public_sources(*, source_ids: tuple[str, ...],
                                   fetch, pages: int = 3,
                                   limit: int = 5, try_first_party: bool = False,
                                   now=None) -> dict:
    """Scan up to 5*3 existing exact GitHub routes, with zero-hit explanations.

    A callback is injected for deterministic offline tests; only the CLI's
    --live path provides real HTTP. Each original W05 per-page check remains
    strict; no broadening of patterns just to increase counts.
    """
    planned = _validate_plan(source_ids, pages, limit, try_first_party)
    if not callable(fetch):
        raise PublicSourceSurveyError("explicit approved fetch callback required")
    summaries = []
    all_cues = []
    callback_calls = 0
    for source_id, repo in planned:
        rows = []
        for page in range(1, pages + 1):
            callback_calls += 1
            rows.append(fetch(public_feed_url(repo, page=page)))
        checked = validate_w05_page_bundle(
            tuple(rows), source_id=source_id, now=now)
        diagnostic = checked["diagnostics"]
        cues = checked["cues"]
        counters = {
            "nonmerged": sum(p["nonmerged_count"] for p in diagnostic["pages"]),
            "repair_title": sum(p["repair_title_count"] for p in diagnostic["pages"]),
            "ambiguous_positive": sum(
                p["ambiguous_positive_cue_count"] for p in diagnostic["pages"]),
            "unpinned_positive": sum(
                p["unpinned_positive_cue_count"] for p in diagnostic["pages"]),
        }
        raw_positive = sum(p["positive_title_cues"] for p in diagnostic["pages"])
        other = (diagnostic["public_rows_examined"] - counters["nonmerged"]
                 - counters["repair_title"] - counters["ambiguous_positive"]
                 - counters["unpinned_positive"] - raw_positive)
        if other < 0:
            raise PublicSourceSurveyError("W05 title exclusion counters inconsistent")
        summaries.append({
            "source_id": source_id,
            "pages_scanned": pages,
            "public_rows_examined": diagnostic["public_rows_examined"],
            "duplicate_public_rows": diagnostic["overlapping_rows_deduplicated"],
            "unique_positive_title_cues": len(cues),
            "positive_title_cues_in_page_rows": raw_positive,
            "excluded_nonmerged": counters["nonmerged"],
            "excluded_repair_title": counters["repair_title"],
            "excluded_ambiguous_positive": counters["ambiguous_positive"],
            "excluded_unpinned_positive": counters["unpinned_positive"],
            "merged_nonrepair_without_positive_cue": other,
            "diagnostic_scope": "LATEST_UPDATED_CLOSED_PRS_NOT_FULL_REPOSITORY",
            "no_positive_cues_proves_no_capability": False,
        })
        all_cues.extend(cues)
    # Sort deterministically and explicitly distinguish a title cue from a
    # verified external implementation or approved usable skill.
    all_cues.sort(key=lambda row: (
        row["upstream_age_days"], row["source_id"],
        row["public_url"], row["purpose_code"]))
    purpose_counts = Counter(cue["purpose_code"] for cue in all_cues)
    preview = [
        {
            "library_item_id": cue["library_item_id"],
            "source_id": cue["source_id"],
            "public_url": cue["public_url"],
            "evidence_sha256": cue["evidence_sha256"],
            "merge_commit_sha": cue["merge_commit_sha"],
            "kind": cue["kind"], "purpose_code": cue["purpose_code"],
            "evidence_strength": "MERGED_PR_TITLE_CUE_ONLY",
            "upstream_tested": False, "approved": False,
            "export_allowed": False,
        }
        for cue in all_cues[:limit]
    ]
    trial = None
    if try_first_party:
        testable = next((cue for cue in all_cues if cue["purpose_code"] in RECIPES),
                        None)
        if testable is not None:
            trial = {
                "public_cue_library_item_id": testable["library_item_id"],
                "public_source_id": testable["source_id"],
                "public_purpose_code": testable["purpose_code"],
                "ucie_owned_synthetic_trial": evaluate_ucie_owned_recipe(
                    testable["purpose_code"]),
                "upstream_code_executed": False,
                "upstream_benefit_verified": False,
                "experience_recorded": False,
            }
    return {
        "schema": SCHEMA,
        "status": ("W05_PUBLIC_TITLE_CUES_FOUND_UNVERIFIED_NO_GO"
                   if all_cues else "W05_NO_POSITIVE_TITLE_CUES_IN_BOUNDED_SAMPLE"),
        "sources_scanned": len(planned),
        "pages_per_source": pages,
        "approved_public_routes_requested": callback_calls,
        "network_requests": "CALLER_CALLBACK_CONTROLLED",
        "total_public_rows_examined": sum(x["public_rows_examined"] for x in summaries),
        "total_positive_title_cues": len(all_cues),
        "positive_cue_purpose_counts": dict(sorted(purpose_counts.items())),
        "sources": summaries,
        "returned_count": len(preview),
        "omitted_count": max(0, len(all_cues) - len(preview)),
        "items": preview,
        "first_party_trial": trial,
        "all_repository_history_exhaustively_searched": False,
        "candidate_title_cues_are_verified_capabilities": False,
        "public_source_code_executed": False,
        "license_reviewed": False,
        "operating_database_writes": 0,
        "experience_ledger_writes": 0,
        "scheduler_registered": False,
        "auto_promoted": False,
        "v1_accepted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UCIE W05 bounded survey on five approved public GitHub sources")
    parser.add_argument("--source-id", choices=ALLOWED, action="append")
    parser.add_argument("--all-approved", action="store_true",
                        help="Explicitly scan exactly all five approved GitHub repos")
    parser.add_argument("--pages", type=int, default=1,
                        help="1-3 of the original allowlisted closed-PR pages per repo")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--live", action="store_true",
                        help="Explicit approved public PR metadata GET; otherwise inert")
    parser.add_argument("--try-first-party", action="store_true",
                        help="At most one UCIE-authored synthetic trial, no persistence")
    args = parser.parse_args()
    attempted = 0
    try:
        if args.source_id and args.all_approved:
            raise PublicSourceSurveyError("choose sources OR all approved")
        sources = ALLOWED if args.all_approved else tuple(args.source_id or ())
        # Fail closed before any public HTTP; even in the inert path.
        _validate_plan(sources, args.pages, args.limit, args.try_first_party)
        if not args.live:
            result = {
                "schema": SCHEMA,
                "status": "W05_PUBLIC_SURVEY_EXPLICIT_LIVE_REQUIRED",
                "planned_sources": list(sources),
                "planned_pages_per_source": args.pages,
                "network_requests": 0, "operating_database_writes": 0,
                "experience_ledger_writes": 0, "auto_promoted": False,
            }
        else:
            def counted_fetch(url: str):
                nonlocal attempted
                attempted += 1
                return public_feed_get(url)
            result = survey_approved_public_sources(
                source_ids=sources, fetch=counted_fetch, pages=args.pages,
                limit=args.limit, try_first_party=args.try_first_party)
            result["network_requests"] = attempted
    except (PublicSourceSurveyError, CapabilityTrialError, DiscoveryError,
            SourceRegistryError, OSError, ValueError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "W05_SURVEY_FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "attempted_public_gets": attempted,
            "operating_database_writes": 0,
            "experience_ledger_writes": 0,
            "auto_promoted": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
