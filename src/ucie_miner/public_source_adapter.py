"""UCIE W03: connect the existing bounded public discovery miner to a
source-registry aware adapter contract; no new fetcher or scheduler.

The adapter REQUIRES an explicit caller-provided fetch callback. The old
discovery URL validator, metadata caps and Source Registry are reused. This is
not automatic permission to add any API, repository, document, or network call.
"""
from __future__ import annotations

from datetime import datetime

from .public_discovery import (
    DiscoveryError, discover_all_feeds, public_feed_url,
)
from .source_registry import get_source, SourceRegistryError

SCHEMA = "UCIE_W03_PUBLIC_DISCOVERY_ADAPTER_V1"
MAX_SOURCES = 5
MAX_PAGES = 3


def adapter_plan(source_id: str, *, page: int = 1) -> dict:
    """Pure preview for one exact existing GitHub PR API route."""
    try:
        src = get_source(source_id)
    except SourceRegistryError as exc:
        raise DiscoveryError("unapproved source registry entry") from exc
    if src["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY":
        raise DiscoveryError("official documents use existing document adapter")
    if type(page) is not int:
        raise DiscoveryError("invalid adapter page")
    repo = source_id.removeprefix("repo:")
    url = public_feed_url(repo, page=page)
    return {
        "schema": SCHEMA,
        "source_id": source_id,
        "source_kind": src["source_kind"],
        "existing_collector_route": url,
        "cursor": {"page": page},
        "fetch_budget_for_this_page": 1,
        "record_kind": "PUBLIC_MERGED_PR_METADATA",
        "revision_hash_status": "FETCH_NOT_PERFORMED",
        "license_scope": "NOT_ATTESTED_PER_REVISION",
        "result_status": "PLANNED_EXISTING_APPROVED_ROUTE_ONLY",
        "transport_invoked": False,
        "registry_grants_network_permission": False,
        "persistent_writes": 0,
    }


def adapt_existing_public_discovery(*, source_ids: tuple[str, ...],
                                    fetch, now: datetime | None = None,
                                    backfill_pages: int = 1) -> dict:
    """Real existing data flow, with explicitly injected transport callback.

    Does not change the hourly worker, bypass existing source URL allowlists,
    or claim a synthetic callback actually contacted GitHub. The caller is
    responsible for the existing higher-level opt-in and scheduling policy.
    """
    if (type(source_ids) is not tuple or not source_ids
            or len(source_ids) > MAX_SOURCES or len(set(source_ids)) != len(source_ids)
            or type(backfill_pages) is not int
            or not 1 <= backfill_pages <= MAX_PAGES
            or not callable(fetch)):
        raise DiscoveryError("invalid bounded adapter request")
    repos = []
    for source_id in source_ids:
        if type(source_id) is not str:
            raise DiscoveryError("invalid source registry identity")
        try:
            source = get_source(source_id)
        except SourceRegistryError as exc:
            raise DiscoveryError("source not activated or unknown") from exc
        if source["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY":
            raise DiscoveryError("only existing GitHub PR adapter in W03")
        repos.append(source_id.removeprefix("repo:"))
    discovery = discover_all_feeds(
        fetch=fetch, sources=tuple(repos), now=now,
        backfill_pages=backfill_pages)
    if (discovery.get("schema") != "UCIE_MULTI_SOURCE_PUBLIC_DISCOVERY_V1"
            or discovery.get("production_approved") is not False
            or discovery.get("automatic_rule_training") is not False
            or discovery.get("persistent_writes") != 0
            or len(discovery.get("feeds", [])) != len(repos)):
        raise DiscoveryError("existing public discovery contract changed")
    feeds = []
    for repo, feed in zip(repos, discovery["feeds"]):
        if (feed.get("schema") != "UCIE_APPROVED_PUBLIC_DISCOVERY_V1"
                or feed.get("source") != repo
                or feed.get("production_approved") is not False
                or feed.get("persistent_writes") != 0
                or type(feed.get("leads")) is not list
                or feed.get("lead_count") != len(feed["leads"])):
            raise DiscoveryError("untrusted legacy public feed result")
        feeds.append({
            "source_id": "repo:" + repo,
            "content_kind": "PUBLIC_MERGED_PR_METADATA",
            "source_result_status": "PUBLIC_LEADS_UNVERIFIED",
            "cursor": {"pages_requested_max": backfill_pages},
            "records_examined": feed["records_examined"],
            "leads": feed["leads"],
            "lead_count": feed["lead_count"],
            "license_scope": "NOT_ATTESTED_PER_REVISION",
            "owner_approved_release": False,
        })
    return {
        "schema": SCHEMA,
        "status": "APPROVED_SOURCE_ADAPTER_EXECUTED_UNVERIFIED_NO_GO",
        "sources": feeds,
        "source_count": len(feeds),
        "candidate_leads_total": sum(x["lead_count"] for x in feeds),
        "transport_callback_invocations": discovery["public_reads_max"],
        "fetch_upper_bound": discovery["public_reads_upper_bound"],
        "actually_contacted_remote": "UNKNOWN_CALLBACK_CONTROLLED",
        "persistent_writes": 0,
        "auto_promoted": False,
        "production_approved": False,
        "scheduler_registered": False,
    }
