"""W01: bounded, read-only public technical-source registry.

Registry metadata is NOT a new network allowlist. The existing collector's
hardcoded host/path restrictions, per-stage owner opt-ins and GET budget remain
the only fetch authority. Research-only sources can never be activated here.
"""
from __future__ import annotations

import json

from .evidence import SOURCES as KNOWN_OWNERS
from .public_discovery import SOURCES as DISCOVERY_SOURCES
from .public_evidence_routes import DOC_ENDPOINTS
from .product_plan import (
    APPROVED_REPOSITORIES, OFFICIAL_PUBLIC_MATERIAL,
    RESEARCH_ONLY_SOURCE_CANDIDATES,
)

SCHEMA = "UCIE_W01_PUBLIC_SOURCE_REGISTRY_V1"
ACTIVE = "ACTIVE_APPROVED"
RESEARCH = "RESEARCH_ONLY"

# All source records are first-party data. These are exact existing
# documentation URLs; do not derive new fetch URLs from user input.
METHODS = ("EXISTING_BOUNDED_GITHUB_API", "EXISTING_PINNED_OFFICIAL_DOC")
SOURCE_KINDS = ("INDEPENDENT_PUBLIC_REPOSITORY", "OFFICIAL_PUBLIC_DOCUMENT")


class SourceRegistryError(ValueError):
    pass


def _ensure_source_scope() -> None:
    """Detect drift; this registry is not permission to expand upstream scope."""
    if (tuple(DISCOVERY_SOURCES) != tuple(APPROVED_REPOSITORIES)
            or set(KNOWN_OWNERS) != set(APPROVED_REPOSITORIES)
            or set(DOC_ENDPOINTS) != set(APPROVED_REPOSITORIES)):
        raise SourceRegistryError("existing UCIE public source scope changed")


def sources() -> tuple[dict, ...]:
    """Return safe copies of already-reviewed source definitions (no IO)."""
    _ensure_source_scope()
    rows = []
    for repo in APPROVED_REPOSITORIES:
        owner = KNOWN_OWNERS[repo]
        doc_url, doc_topic = DOC_ENDPOINTS[repo]
        rows.append({
            "source_id": "repo:" + repo,
            "source_kind": SOURCE_KINDS[0],
            "status": ACTIVE,
            "owner_label": owner,
            "public_url": "https://github.com/" + repo,
            "existing_method": METHODS[0],
            "approved_material_types": ["PUBLIC_MERGED_PR_METADATA"],
            "license_verdict": "NOT_ATTESTED_PER_REVISION",
            "source_revision_verdict": "CHECK_EXACT_PR_OR_COMMIT",
            "fetch_authorized_by_this_registry": False,
            "live_collector_expanded": False,
        })
        rows.append({
            "source_id": "doc:" + repo,
            "source_kind": SOURCE_KINDS[1],
            "status": ACTIVE,
            "owner_label": "OFFICIAL_PUBLISHER_NOT_INDEPENDENTLY_ATTESTED",
            "related_approved_repo": repo,
            "public_url": doc_url,
            "existing_method": METHODS[1],
            "approved_material_types": [OFFICIAL_PUBLIC_MATERIAL[0]],
            "topic_label": doc_topic,
            "license_verdict": "NOT_ATTESTED_PER_REVISION",
            "source_revision_verdict": "CHECK_PUBLIC_DOCUMENT_REVISION",
            "fetch_authorized_by_this_registry": False,
            "live_collector_expanded": False,
        })
    for name in RESEARCH_ONLY_SOURCE_CANDIDATES:
        rows.append({
            "source_id": "research:" + name,
            "source_kind": "UNAPPROVED_DATA_SUPPLIER",
            "status": RESEARCH,
            "public_url": None,
            "existing_method": None,
            "approved_material_types": [],
            "license_verdict": "NOT_REVIEWED",
            "source_revision_verdict": "NOT_REVIEWED",
            "fetch_authorized_by_this_registry": False,
            "live_collector_expanded": False,
        })
    return tuple(rows)


def get_source(source_id: str, *, require_approved: bool = True) -> dict:
    """Exact-ID lookup only. Never resolves arbitrary URLs or remote sources."""
    if type(source_id) is not str or len(source_id) > 128:
        raise SourceRegistryError("invalid bounded source identity")
    for item in sources():
        if item["source_id"] == source_id:
            if require_approved and item["status"] != ACTIVE:
                raise SourceRegistryError("research-only source is not approved")
            return item
    raise SourceRegistryError("source is not explicitly registered")


def preview_source_registry(*, include_research: bool = True) -> dict:
    listed = sources()
    visible = [s for s in listed if include_research or s["status"] == ACTIVE]
    return {
        "schema": SCHEMA,
        "status": "SOURCE_CATALOG_IMPLEMENTED_NO_NEW_FETCH_AUTHORITY",
        "active_source_count": sum(s["status"] == ACTIVE for s in listed),
        "independent_public_repo_count": len(APPROVED_REPOSITORIES),
        "pinned_official_document_count": len(DOC_ENDPOINTS),
        "research_only_count": len(RESEARCH_ONLY_SOURCE_CANDIDATES),
        "official_material_types": list(OFFICIAL_PUBLIC_MATERIAL),
        "sources": visible,
        "network_requests": 0,
        "persistent_writes": 0,
        "auto_activation": False,
        "fetch_allowlist_changed": False,
        "license_signoff": False,
        "future_sources_approved": False,
    }


def main() -> int:
    print(json.dumps(preview_source_registry(), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
