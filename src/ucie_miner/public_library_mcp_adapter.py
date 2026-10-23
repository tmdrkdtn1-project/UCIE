"""UCIE-only public Library lookup contracts for the existing read-only MCP.

Pure handlers: an existing UCIE MCP runtime may call these functions, but
importing this module does not register tools or modify a running tunnel.
The handlers never see recipient identities or private code and never
interpret untrusted query text as executable instructions.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .public_discovery import SOURCES, SOURCE_SKILL, DiscoveryError
from .public_library_search import search_public_library
from .skill_profiles import PROFILE
from .public_discovery import CATEGORIES
from .public_evidence_routes import TAGS

SEARCH_SCHEMA = "UCIE_LIBRARY_MCP_PUBLIC_SEARCH_CONTRACT_V1"
FEED_SCHEMA = "UCIE_LIBRARY_PUBLIC_SKILL_FEED_PREVIEW_V1"
MAX_QUERY = 160
MAX_TOP = 20
DOMAIN_TERMS = {
    "python": "python-runtime-safety",
    "파이썬": "python-runtime-safety",
    "powershell": "powershell-safe-calls",
    "파워셸": "powershell-safe-calls",
    "git": "git-workflow-prevention",
    "깃": "git-workflow-prevention",
    "mcp": "mcp-api-compatibility",
    "runner": "runner-environment-drift",
    "러너": "runner-environment-drift",
}
DOMAIN_NAMES = {
    "python": "python-runtime-safety",
    "powershell": "powershell-safe-calls",
    "git": "git-workflow-prevention",
    "mcp/api": "mcp-api-compatibility",
    "mcp": "mcp-api-compatibility",
    "runner": "runner-environment-drift",
    "github actions runner": "runner-environment-drift",
}
TAG_TERMS = {
    "security": "SECURITY",
    "보안": "SECURITY",
    "crash": "CRASH",
    "충돌": "CRASH",
    "regression": "REGRESSION",
    "회귀": "REGRESSION",
    "compatibility": "COMPATIBILITY",
    "호환성": "COMPATIBILITY",
    "testing": "TESTING",
    "테스트": "TESTING",
}
ALLOWED_TAGS = frozenset(CATEGORIES) | frozenset(TAGS)


def _digest(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def _parse_query(query, category, tag, top):
    if (type(query) is not str or not query.strip() or len(query) > MAX_QUERY
            or any(ord(char) < 32 or ord(char) == 127 for char in query)
            or type(top) is not int or not 1 <= top <= MAX_TOP):
        raise DiscoveryError("bounded public technical query required")
    if category is not None and (
            type(category) is not str or category.casefold() not in DOMAIN_NAMES):
        raise DiscoveryError("unapproved public technical category")
    if tag is not None and (
            type(tag) is not str or tag.upper() not in ALLOWED_TAGS):
        raise DiscoveryError("unapproved public technical tag")

    # Words are examined only for fixed taxonomy matches. Never forward
    # user-supplied free text to SQL, the web, upstream code or a log.
    words = set(re.findall(r"[^\W_]+", query.casefold(), flags=re.UNICODE))
    domains = {DOMAIN_TERMS[word] for word in words if word in DOMAIN_TERMS}
    implied_tags = {TAG_TERMS[word] for word in words if word in TAG_TERMS}
    explicit_domain = DOMAIN_NAMES[category.casefold()] if category else None
    explicit_tag = tag.upper() if tag else None

    if len(domains) > 1 or len(implied_tags) > 1:
        return None, None, "AMBIGUOUS_PUBLIC_TECHNICAL_TAXONOMY_NO_GO"
    if explicit_domain and domains and explicit_domain not in domains:
        return None, None, "CATEGORY_QUERY_SCOPE_CONFLICT_NO_GO"
    if explicit_tag and implied_tags and explicit_tag not in implied_tags:
        return None, None, "TAG_QUERY_SCOPE_CONFLICT_NO_GO"
    skill_id = explicit_domain or next(iter(domains), None)
    tag_key = explicit_tag or next(iter(implied_tags), None)
    if skill_id is None and tag_key is None:
        return None, None, "NO_SUPPORTED_PUBLIC_TAXONOMY_MATCH_NO_GO"
    return skill_id, tag_key, None


def search_ucie_public_library_for_mcp(
        root: Path, *, query: str, category: str | None = None,
        tag: str | None = None, top: int = 5) -> dict:
    """Adapter for the installed search_ucie_evidence(query,category,tag,top).

    Does not replace the existing MCP server or change its registration.
    Only fixed technical taxonomies are supported, not arbitrary free-text
    search. Explicit ambiguity returns no results rather than guessing.
    """
    skill_id, tag_key, blocked = _parse_query(query, category, tag, top)
    if blocked:
        return {
            "schema": SEARCH_SCHEMA,
            "status": blocked,
            "results": [],
            "result_count": 0,
            "search_capability": "FIXED_PUBLIC_TAXONOMY_ONLY",
            "query_text_retained": False,
            "independent_qa": "NOT_ESTABLISHED",
            "auto_install": False,
            "production_approved": False,
        }
    index = search_public_library(
        root, skill_id=skill_id, tag=tag_key, limit=top)
    if index["schema"] != "UCIE_PUBLIC_LIBRARY_SEARCH_V1" or (
            index["production_approved"] is not False or
            index["network_gets"] != 0 or
            index["operating_database_writes"] != 0 or
            index["project_reads_or_writes"] != 0):
        raise DiscoveryError("unexpected public Library index contract")
    return {
        "schema": SEARCH_SCHEMA,
        "status": "PUBLIC_TECHNICAL_EVIDENCE_METADATA_REVIEW_ONLY_NO_GO",
        "capability": "FIXED_PUBLIC_TAXONOMY_ONLY",
        "selected_skill_id": skill_id,
        "selected_tag": tag_key,
        "results": index["results"],
        "result_count": index["result_count"],
        "bounded_selection_not_exhaustive": True,
        "stage10_recent_present": index["stage10_recent_present"],
        "stage13_history_present": index["stage13_history_present"],
        "query_text_retained": False,
        "independent_qa": "NOT_ESTABLISHED",
        "skill_installable_count": 0,
        "auto_install": False,
        "project_reads_or_writes": 0,
        "production_approved": False,
    }


def preview_public_skill_feed(root: Path, *, references_per_domain: int = 3) -> dict:
    """Pull-oriented knowledge digest: five *first-party* review profiles.

    This is not an agent SKILL.md, executable payload, signed release,
    periodically scheduled task, or recipient-specific project injection.
    """
    if (type(references_per_domain) is not int
            or not 1 <= references_per_domain <= 5):
        raise DiscoveryError("invalid bounded public skill feed size")
    topics = []
    for source in SOURCES:
        skill_id = SOURCE_SKILL[source]
        profile = PROFILE[skill_id]
        index = search_public_library(
            root, source=source, limit=references_per_domain)
        if (index["production_approved"] is not False
                or index["project_reads_or_writes"] != 0
                or index["network_gets"] != 0):
            raise DiscoveryError("untrusted public skill feed index")
        topics.append({
            "skill_id": skill_id,
            "domain": profile["domain"],
            "approved_public_source": source,
            "first_party_review_question": profile["review_question"],
            "safe_call_guidance": profile["safe_call"],
            "manual_review_plan": profile["recommended_action"],
            "public_research_reference_count": index["result_count"],
            "public_research_references": [{
                "public_url": row["public_url"],
                "revision_sha": row["revision_sha"],
                "evidence_sha256": row["evidence_sha256"],
                "technical_tags": row["technical_tags"],
                "status": "UNVERIFIED_RESEARCH_REFERENCE",
            } for row in index["results"]],
            "actual_skill_release_version": None,
            "source_fix_independently_verified": False,
            "skill_installable": False,
        })
    payload = {
        "schema": FEED_SCHEMA,
        "status": "PUBLIC_RESEARCH_SKILL_FEED_PREVIEW_NO_GO",
        "topic_count": len(topics),
        "topics": topics,
        "version_strategy": "DETERMINISTIC_CONTENT_DIGEST_NOT_SIGNED_RELEASE",
        "distribution_mode": "OPT_IN_READ_ONLY_PULL_AFTER_SEPARATE_APPROVAL",
        "published_to_recipient": False,
        "scheduler_registered": False,
        "signed_skill_package_count": 0,
        "installable_skills": [],
        "auto_inject_into_projects": False,
        "cross_project_information_collected": False,
        "operating_database_writes": 0,
        "network_gets": 0,
        "production_approved": False,
    }
    payload["content_sha256"] = _digest(payload)
    payload["content_sha256_is_signature"] = False
    return payload


def extend_existing_ucie_mcp_evidence_response(
        root: Path, existing_response: dict, *,
        query: str, category: str | None = None,
        tag: str | None = None, top: int = 5) -> dict:
    """Opt-in additive integration for the EXISTING UCIE MCP search handler.

    Preserve its authoritative, old read-only search response as-is; attach
    new indexed PUBLIC_ONLY research as a clearly separate UNVERIFIED field.
    This must be called from the existing UCIE-only server handler after
    that handler completes, never as a new plugin or a server replacement.
    No fallback guessing of a foreign response schema is allowed.
    """
    if (type(existing_response) is not dict
            or existing_response.get("status") !=
                "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY"
            or type(existing_response.get("results")) is not list
            or "ucie_public_research_index" in existing_response):
        raise DiscoveryError("unexpected existing UCIE MCP evidence response")
    additional = search_ucie_public_library_for_mcp(
        root, query=query, category=category, tag=tag, top=top)
    if (additional.get("production_approved") is not False
            or additional.get("auto_install") is not False
            or additional.get("result_count", -1) > MAX_TOP):
        raise DiscoveryError("unsafe public Library MCP extension")
    return {**existing_response, "ucie_public_research_index": additional}


def extend_existing_ucie_mcp_wire_response(
        root: Path, existing_response: dict | str, *,
        query: str, category: str | None = None,
        tag: str | None = None, top: int = 5) -> dict | str:
    """Keep existing MCP wire return type while adding public-only results.

    A FastMCP tool may return a dict or an already JSON-serialized string.
    Preserve the legacy response fields, validate the exact existing UCIE
    public-metadata contract and attach only a segregated unverified index.
    This never writes, records queries, executes code or contacts projects.
    """
    serialized = type(existing_response) is str
    if serialized:
        if len(existing_response.encode("utf-8")) > 131072:
            raise DiscoveryError("oversized existing UCIE MCP wire response")

        def _unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise DiscoveryError("duplicate existing UCIE MCP JSON property")
                result[key] = value
            return result

        try:
            parsed = json.loads(existing_response, object_pairs_hook=_unique_pairs)
        except (UnicodeError, ValueError) as exc:
            raise DiscoveryError("invalid existing UCIE MCP wire JSON") from exc
    else:
        parsed = existing_response
    extended = extend_existing_ucie_mcp_evidence_response(
        root, parsed, query=query, category=category, tag=tag, top=top)
    if serialized:
        return json.dumps(extended, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    return extended
