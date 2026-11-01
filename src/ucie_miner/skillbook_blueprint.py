"""UCIE first-party metadata-only SkillBook blueprint; NOT an approved skill or book."""
from __future__ import annotations

import hashlib
import json
import re

from .library_entry import build_library_entry, LibraryEntryError

SCHEMA = "UCIE_SKILLBOOK_BLUEPRINT_V1"
TOPIC = re.compile(r"[A-Z][A-Z0-9_]{2,63}\Z")
MAX_ITEMS = 20
INPUT_FIELDS = frozenset({
    "kind", "source_id", "evidence_reference", "evidence_sha256",
    "purpose_code", "version_scope", "dependencies",
})


class SkillBookBlueprintError(ValueError):
    """Untrusted evidence or invalid metadata-only composition."""


def compose_blueprint(topic: str, candidates: list[dict]) -> dict:
    """Build a deterministic, non-exportable metadata index from approved-source records.

    Reconstruct every entry using the source registry, never trust a caller's
    verification claims. No file reads, network, code execution, DB or writes.
    """
    if type(topic) is not str or not TOPIC.fullmatch(topic):
        raise SkillBookBlueprintError("invalid bounded SkillBook topic")
    if type(candidates) is not list or not (1 <= len(candidates) <= MAX_ITEMS):
        raise SkillBookBlueprintError("SkillBook requires 1-20 bounded candidates")
    entries = []
    seen = set()
    for candidate in candidates:
        if type(candidate) is not dict or set(candidate) != INPUT_FIELDS:
            raise SkillBookBlueprintError("untrusted candidate fields or approval claim")
        try:
            entry = build_library_entry(candidate)
        except (LibraryEntryError, TypeError, KeyError, ValueError) as exc:
            raise SkillBookBlueprintError("unapproved or malformed public evidence") from exc
        item_id = entry["library_item_id"]
        if item_id in seen:
            raise SkillBookBlueprintError("duplicate public evidence identity")
        seen.add(item_id)
        entries.append({
            "library_item_id": item_id,
            "kind": entry["kind"],
            "source_id": entry["source_id"],
            "public_url": entry["public_url"],
            "evidence_sha256": entry["evidence_sha256"],
            "purpose_code": entry["purpose_code"],
            "version_scope_claim": entry["version_scope_claim"],
            "version_applicability_verified": False,
            "source_license_status": entry["source_license_status"],
            "independent_qa_status": "NOT_PERFORMED",
            "approval_status": "NOT_APPROVED",
            "export_allowed": False,
        })
    entries.sort(key=lambda e: (e["kind"], e["purpose_code"], e["library_item_id"]))
    canonical = json.dumps([topic, entries], sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "schema": SCHEMA,
        "topic": topic,
        "blueprint_id": digest,
        "status": "UNVERIFIED_METADATA_ONLY",
        "chapters": entries,
        "chapter_count": len(entries),
        "human_readable_skillbook_created": False,
        "machine_readable_skill_implemented": False,
        "cross_source_semantic_synthesis_verified": False,
        "independent_qa_passed": False,
        "rights_cleared": False,
        "human_approved": False,
        "export_allowed": False,
        "auto_promoted": False,
        "model_trained": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "other_project_access": False,
    }
