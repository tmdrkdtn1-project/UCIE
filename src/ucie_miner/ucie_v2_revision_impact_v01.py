"""UCIE V2 B3: bounded, source-linked, affected-only retest proposals.

This is an inert review engine. It never fetches new evidence, executes a test,
modifies an operating DB, automatically promotes a skill, or schedules work.
An incoming candidate digest is an UNVERIFIED signal, never an authenticated
official revision. Real source identity must be checked separately before QA.
"""
from __future__ import annotations

import re

SCHEMA = "UCIE_V2_REVISION_IMPACT_REVIEW_V01"
MAX_SIGNALS = 8
# Source identity pins come from the exact existing UCIE authored products.
# A changed source contract requires a reviewed update, not silent adoption.
PINS = {
    "repo:modelcontextprotocol/python-sdk":
        "754254c08fe1c3eda18b69da3d336106fe8d72d6",
    "doc:python/cpython":
        "9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a",
    "doc:git/git":
        "1cdd1c7339dfc64093687b6e072d59feee584b8639c0203ece0a1150ce23d325",
}
MCP_ASSET = "UCIE-CAPSULE-MCP-PROMPTS-GET-20261126-01"
MCP_SKILLBOOK = "UCIE-SKILLBOOK-MCP-PROMPTS-003"
PY_BOOK = "UCIE-SKILLBOOK-PY-SCANDIR-001"
GIT_BOOK = "UCIE-SKILLBOOK-GIT-PORCELAIN-002"
PRINCIPLE = "UCIE-PRINCIPLE-PYTHON-GIT-BOUNDED-METADATA-001"
# Explicit whitelisted test names. No signal is ever allowed to choose
# a filename, command, executable, path or additional network endpoint.
ASSETS = {
    MCP_ASSET: {
        "sources": ("repo:modelcontextprotocol/python-sdk",),
        "depends_on": (),
        "tests": ("test_ucie_v2_capsule_v01.py",),
    },
    MCP_SKILLBOOK: {
        "sources": ("repo:modelcontextprotocol/python-sdk",),
        "depends_on": (),
        "tests": ("test_ucie_mcp_guide_local_reader_v01.py",
                  "test_ucie_mcp_prompt_regression_v01.py"),
    },
    PY_BOOK: {
        "sources": ("doc:python/cpython",),
        "depends_on": (),
        "tests": ("test_ucie_skillbook_product_v01.py",),
    },
    GIT_BOOK: {
        "sources": ("doc:git/git",),
        "depends_on": (),
        "tests": ("test_ucie_skillbook_002_git_porcelain_v01.py",),
    },
    PRINCIPLE: {
        "sources": (),
        "depends_on": (PY_BOOK, GIT_BOOK),
        "tests": ("test_ucie_skillbook_principle_composer_v01.py",),
    },
}
HEX_PIN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


class RevisionImpactError(ValueError):
    """Invalid input or drift: no output/scheduling and no source-text echo."""


def _exact(actual: object, expected: object) -> bool:
    return type(actual) is type(expected) and actual == expected


def build_current_graph() -> dict:
    """Read *actual* UCIE authored contracts, check their frozen source pins."""
    from .source_registry import get_source, SourceRegistryError, ACTIVE
    from .ucie_v2_capsule_v01 import build_from_existing_ucie
    from .skillbook_product_v01 import build_skillbook as build_py
    from .skillbook_git_porcelain_product_v01 import build_skillbook as build_git
    from .skillbook_principle_composer_v01 import (
        compose_bounded_metadata_principle,
    )
    try:
        for sid in PINS:
            record = get_source(sid)
            if (record.get("status") != ACTIVE or
                    record.get("fetch_authorized_by_this_registry") is not False):
                raise RevisionImpactError("approved registry drift")
        capsule, py, git, principle = (
            build_from_existing_ucie(), build_py(), build_git(),
            compose_bounded_metadata_principle(),
        )
    except (SourceRegistryError, KeyError, TypeError, ValueError) as exc:
        raise RevisionImpactError("existing UCIE source/asset contracts unavailable") from exc
    if (capsule.capsule_id != MCP_ASSET
            or capsule.skillbook_id != MCP_SKILLBOOK
            or capsule.fixed_commit != PINS["repo:modelcontextprotocol/python-sdk"]
            or capsule.independent_qa != "NOT_VERIFIED"
            or capsule.rights != "NOT_APPROVED"
            or capsule.customer_release != "NOT_AUTHORIZED"):
        raise RevisionImpactError("B1 capsule source or authority drift")
    for book, identifier, sid in (
        (py, PY_BOOK, "doc:python/cpython"),
        (git, GIT_BOOK, "doc:git/git"),
    ):
        entry = book.get("library_entry")
        src = book.get("source_evidence")
        if (type(entry) is not dict or type(src) is not dict
                or book.get("skillbook_id") != identifier
                or entry.get("source_id") != sid
                or entry.get("evidence_sha256") != PINS[sid]
                or src.get("source_document_sha256") != PINS[sid]
                or entry.get("approval_status") != "NOT_APPROVED"
                or entry.get("export_allowed") is not False
                or book.get("export_allowed") is not False
                or book.get("status") != "FIRST_PARTY_DRAFT_NOT_APPROVED"):
            raise RevisionImpactError("SkillBook source or rights drift")
    if (principle.get("principle_id") != PRINCIPLE
            or principle.get("generalization_method") !=
                    "FIRST_PARTY_CURATED_EXPLICIT_COMPARISON"
            or principle.get("status") !=
                    "UCIE_CURATED_CROSS_SOURCE_CHAPTER_DRAFT_NO_GO"
            or principle.get("export_allowed") is not False
            or principle.get("automatic_promotion") is not False
            or principle.get("model_trained") is not False
            or principle.get("independent_qa_verified") is not False):
        raise RevisionImpactError("curated cross-source principle drift")
    rows = principle.get("sources")
    if (type(rows) is not list or len(rows) != 2
            or {r.get("skillbook_id") for r in rows if type(r) is dict}
                    != {PY_BOOK, GIT_BOOK}):
        raise RevisionImpactError("principle lineage missing")
    if any(row.get("source_id") not in PINS
           or row.get("document_sha256") != PINS[row["source_id"]]
           for row in rows):
        raise RevisionImpactError("principle source pin mismatch")
    if (set(ASSETS) != {MCP_ASSET, MCP_SKILLBOOK, PY_BOOK, GIT_BOOK, PRINCIPLE}
            or any((set(v["sources"]) - set(PINS)
                    or set(v["depends_on"]) - set(ASSETS)
                    or not v["tests"]) for v in ASSETS.values())):
        raise RevisionImpactError("unreviewed asset graph")
    return {
        "schema": SCHEMA,
        "status": "READ_ONLY_SOURCE_AND_SKILLBOOK_GRAPH_REVIEW",
        "source_pins": dict(sorted(PINS.items())),
        "assets": tuple(sorted(ASSETS)),
        "first_party_curated_principle_only": True,
        "autonomous_generalization_verified": False,
        "source_network_requests": 0,
        "operating_database_writes": 0,
    }


def assess_revision_impacts(signals: tuple[dict, ...]) -> dict:
    """Plan only affected tests, validating ALL input before generating advice.

    Signal fields: source_id, previous_pin, candidate_pin.
    candidate_pin is a claimed SHA, not authenticated/newly fetched evidence.
    Unlinked approved sources do not spuriously schedule unrelated testing.
    """
    from .source_registry import get_source, SourceRegistryError, ACTIVE
    graph = build_current_graph()
    if type(signals) is not tuple or len(signals) > MAX_SIGNALS:
        raise RevisionImpactError("bounded tuple of source signals required")
    seen = set()
    changed, unlinked, unchanged = set(), set(), set()
    for signal in signals:
        if type(signal) is not dict or set(signal) != {
                "source_id", "previous_pin", "candidate_pin"}:
            raise RevisionImpactError("invalid source signal fields")
        sid, previous, candidate = (
            signal["source_id"], signal["previous_pin"], signal["candidate_pin"])
        if type(sid) is not str or sid in seen:
            raise RevisionImpactError("duplicate or invalid source")
        seen.add(sid)
        try:
            source = get_source(sid)
        except SourceRegistryError as exc:
            raise RevisionImpactError("unapproved or unknown source") from exc
        if source.get("status") != ACTIVE:
            raise RevisionImpactError("research-only source rejected")
        known = PINS.get(sid)
        if (known is None and previous is not None or
                known is not None and not _exact(previous, known)):
            raise RevisionImpactError("missing or stale original source pin")
        if (type(candidate) is not str or HEX_PIN.fullmatch(candidate) is None
                or known is not None and len(candidate) != len(known)):
            raise RevisionImpactError("candidate pin must be a bounded digest")
        if known is None:
            unlinked.add(sid)
        elif candidate == known:
            unchanged.add(sid)
        else:
            changed.add(sid)
    impacted = {
        asset_id for asset_id, definition in ASSETS.items()
        if set(definition["sources"]) & changed
    }
    # Bounded dependency closure, with no whole-repository fallback.
    for _ in range(len(ASSETS)):
        next_impacted = set(impacted)
        for asset_id, definition in ASSETS.items():
            if set(definition["depends_on"]) & impacted:
                next_impacted.add(asset_id)
        if next_impacted == impacted:
            break
        impacted = next_impacted
    files = sorted({name for key in impacted for name in ASSETS[key]["tests"]})
    return {
        "schema": SCHEMA,
        "status": ("REVIEW_ONLY_AFFECTED_RETEST_PROPOSAL"
                   if impacted else "NO_RETEST_FOR_UNCHANGED_OR_UNLINKED_SOURCE"),
        "affected_assets": sorted(impacted),
        "unaffected_assets": sorted(set(ASSETS) - impacted),
        "candidate_changed_source_ids": sorted(changed),
        "unlinked_approved_source_ids": sorted(unlinked),
        "unchanged_source_ids": sorted(unchanged),
        "proposed_test_files": files,
        "candidate_pin_independently_authenticated": False,
        "tests_executed": False,
        "independent_qa_verified": False,
        "customer_release_authorized": False,
        "automatic_scheduling": False,
        "auto_promoted": False,
        "model_trained": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "graph_asset_count": len(graph["assets"]),
    }
