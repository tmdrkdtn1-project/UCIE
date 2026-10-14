"""Public-only UCIE evidence discovery -> adaptive triage -> skill agenda.

No network by default: the caller provides a previously validated public
feed receipt. Only explicit --live mode invokes the bounded GitHub feed
fetcher. No database writes or rule promotion.
"""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3

from .public_discovery import (SOURCES, DiscoveryError,
                               discover_all_feeds)
from .adaptive_priority import prioritize_public_leads
from .skill_profiles import prepare_public_skill_tasks


def read_prior_miner_ids(root: Path) -> tuple[tuple[str, int], ...]:
    """Read only UCIE's existing public miner metadata, if it exists.

    This method never creates a DB or imports Knowledge. The caller supplies
    only the dedicated UCIE checkout. Other project paths are not supported.
    """
    root = Path(root)
    runtime = root / "runtime"
    path = runtime / "public_miner.sqlite3"
    if root.is_symlink() or runtime.is_symlink() or path.is_symlink():
        raise DiscoveryError("symlinked UCIE candidate DB path")
    if not path.exists():
        return ()
    if not path.is_file():
        raise DiscoveryError("invalid UCIE DB path")
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True,
                                     timeout=3)) as conn:
            conn.execute("PRAGMA query_only=ON")
            if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise DiscoveryError("read-only miner DB integrity failure")
            rows = conn.execute(
                "SELECT source,pr_number,status FROM candidates LIMIT 10001"
            ).fetchall()
    except sqlite3.DatabaseError as exc:
        raise DiscoveryError("unavailable UCIE-only read-only candidate DB") from exc
    if len(rows) > 10000:
        raise DiscoveryError("too many historical miner candidates")
    seen = set()
    for source, number, status in rows:
        if (source not in SOURCES or type(number) is not int or number < 1
                or status != "UNVERIFIED_CANDIDATE_ONLY"):
            raise DiscoveryError("invalid historical miner record")
        seen.add((source, number))
    return tuple(sorted(seen))


def public_intelligence_preview(discovery, *, seen_public_prs=(),
                                opted_out_sources=(), opted_out_prs=(),
                                review_feedback=None, limit=12):
    if (not isinstance(discovery, dict)
            or discovery.get("schema") != "UCIE_MULTI_SOURCE_PUBLIC_DISCOVERY_V1"
            or not isinstance(discovery.get("sources_attempted"), list)
            or not isinstance(discovery.get("feeds"), list)
            or discovery["sources_attempted"] != [
                f.get("source") if isinstance(f, dict) else None
                for f in discovery["feeds"]]
            or type(discovery.get("candidate_leads_total")) is not int
            or discovery["candidate_leads_total"] != sum(
                len(f.get("leads", [])) if isinstance(f, dict)
                and isinstance(f.get("leads"), list) else -999
                for f in discovery["feeds"])
            or discovery.get("production_approved") is not False
            or discovery.get("automatic_rule_training") is not False
            or discovery.get("persistent_writes") != 0):
        raise DiscoveryError("untrusted or conflicting discovery receipts")
    priority = prioritize_public_leads(
        discovery, seen_public_prs=seen_public_prs,
        opted_out_sources=opted_out_sources,
        opted_out_prs=opted_out_prs,
        review_feedback=review_feedback, limit=limit,
    )
    skills = prepare_public_skill_tasks(priority)
    if len(skills["tasks"]) != priority["review_queue_count"]:
        raise DiscoveryError("incomplete skills routing")
    return {
        "schema": "UCIE_PUBLIC_INTELLIGENCE_PREVIEW_V1",
        "status": "UNVERIFIED_RESEARCH_AGENDA",
        "sources_scoped": list(SOURCES),
        "sources_observed": discovery["sources_attempted"],
        "public_lead_count": discovery["candidate_leads_total"],
        "priority": priority,
        "skill_tasks": skills,
        "skill_count": len(skills["skills_available"]),
        "manual_review_required": True,
        "model_weight_training": False,
        "persistent_learning": False,
        "source_data_persisted": False,
        "auto_promoted": False,
        "production_approved": False,
    }


def discover_and_prioritize_live(*, fetch, root: Path | None = None,
                                 sources=SOURCES, limit=12,
                                 opted_out_sources=()):
    """Explicit one-shot public metadata discovery; no automatic writes."""
    if root is None:
        seen = ()
    else:
        seen = read_prior_miner_ids(root)
    allowed = tuple(sources)
    opted = tuple(opted_out_sources)
    if any(s not in SOURCES for s in opted):
        raise DiscoveryError("invalid explicit source opt-out")
    remaining = tuple(s for s in allowed if s not in opted)
    if not remaining:
        raise DiscoveryError("all sources opted out")
    result = discover_all_feeds(fetch=fetch, sources=remaining)
    # External metadata is untrusted even when returned by a real GitHub API.
    preview = public_intelligence_preview(
        result, seen_public_prs=seen, opted_out_sources=opted_out_sources,
        limit=limit,
    )
    preview["existing_miner_candidate_count"] = len(seen)
    preview["live_source_claims_are_independently_verified"] = False
    return preview
