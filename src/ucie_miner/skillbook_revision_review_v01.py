"""UCIE source-linked revision review worksheet.

Keeps the existing owner editorial compiler untouched. Reads only already
validated UCIE authored draft objects and the isolated, untrusted pinned
review journal; produces inert advice, never a release/QA/run/withdrawal.
"""
from __future__ import annotations

from .skillbook_editorial_production_v01 import (
    compare_review_revisions, ORDER, EditorialDraftError,
)

from pathlib import Path
import json

from .skillbook_editorial_production_v01 import compile_review_draft
from . import skillbook_pinned_source_review_v01 as pinned_review

REVISION_PAIR_NAME = "editorial_revision_pair_v01.json"
MAX_REVISION_PAIR_BYTES = 48_000


def read_review_pair(root: Path) -> tuple[dict, dict]:
    """Load an opt-in UCIE-only manuscript pair without modifying anything.

    A named, local-only, non-symlink review input is required. Two source
    bound *authoring inputs* are compiled to exact canonical drafts. The
    next revision must be explicitly linked to the previous SHA.
    """
    try:
        base = pinned_review._owner_root(root)
    except pinned_review.SourceReviewError as exc:
        raise EditorialDraftError("review pair outside owner UCIE") from exc
    runtime = base / "runtime"
    folder = runtime / "skillbook_manual_review"
    target = folder / REVISION_PAIR_NAME
    if (runtime.is_symlink() or not runtime.is_dir()
            or folder.is_symlink() or target.is_symlink()
            or not folder.is_dir() or not target.is_file()
            or target.resolve(strict=True) != folder.resolve() / REVISION_PAIR_NAME):
        raise EditorialDraftError("only exact UCIE revision pair review file")
    with target.open("rb") as stream:
        raw = stream.read(MAX_REVISION_PAIR_BYTES + 1)
    if not 1 <= len(raw) <= MAX_REVISION_PAIR_BYTES:
        raise EditorialDraftError("bounded UCIE revision pair required")

    def unique_keys(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise EditorialDraftError("duplicate revision JSON field")
            obj[key] = value
        return obj

    try:
        request = json.loads(raw.decode("utf-8", "strict"),
                             object_pairs_hook=unique_keys)
    except (UnicodeError, ValueError) as exc:
        raise EditorialDraftError("malformed UCIE revision pair") from exc
    if type(request) is not dict or set(request) != {"previous", "candidate"}:
        raise EditorialDraftError("exact previous/candidate authoring pair required")
    previous = compile_review_draft(request["previous"])
    candidate = compile_review_draft(request["candidate"])
    compare_review_revisions(previous, candidate)
    return previous, candidate


REVISION_IMPACT_SCHEMA = "UCIE_SKILLBOOK_REVISION_IMPACT_REVIEW_V01"
REVISION_RETEST_FILES = (
    "test_ucie_skillbook_product_v01.py",
    "test_ucie_skillbook_002_git_porcelain_v01.py",
    "test_ucie_skillbook_editorial_production_v01.py",
    "test_ucie_skillbook_w09_release_gate_v01.py",
)


def assess_revision_review_impact(previous: dict, candidate: dict,
                                  *, pinned_review_history: bytes = b"") -> dict:
    """Link an authored revision to an isolated *advisory* source review journal.

    Returns a real per-chapter/retest review worksheet, never a signed verdict,
    source authentication, executable skill update or automatic withdrawal.
    """
    from . import skillbook_pinned_source_review_v01 as pinned

    changes = compare_review_revisions(previous, candidate)
    try:
        journal = pinned.inspect_review_journal(pinned_review_history)
    except pinned.SourceReviewError as exc:
        raise EditorialDraftError("invalid UCIE review chain") from exc
    recent = {event["source_id"]: event for event in journal["events"]}
    sources = []
    affected = set(changes["changed_chapter_ids"])
    for item in candidate["sources"]:
        source_id = item["source_id"]
        prior_item = next(
            (old for old in previous["sources"] if old["source_id"] == source_id),
            None,
        )
        changed_source = (
            prior_item is None
            or prior_item["library_item_id"] != item["library_item_id"]
        )
        event = recent.get(source_id)
        relevant = (
            event is not None
            and event["expected_source_sha256"] == item["evidence_sha256"]
        )
        if relevant and event["pinned_bytes_match"]:
            source_state = "PIN_MATCH_RECORDED_ORIGIN_AND_QA_UNVERIFIED"
        elif relevant:
            source_state = "PIN_MISMATCH_REVALIDATION_REQUIRED"
        else:
            source_state = "NO_MATCHING_SOURCE_REVIEW_RECORD"
        source_chapters = sorted(
            chapter["chapter_id"] for chapter in candidate["chapters"]
            if source_id in chapter["source_ids"]
        )
        if changed_source or source_state != "PIN_MATCH_RECORDED_ORIGIN_AND_QA_UNVERIFIED":
            affected.update(source_chapters)
        sources.append({
            "source_id": source_id,
            "source_digest": item["evidence_sha256"],
            "source_ledger_state": source_state,
            "source_evidence_changed": changed_source,
            "associated_chapter_ids": source_chapters,
            "review_event_id": event["event_id"] if relevant else None,
            "publisher_origin_independently_verified": False,
            "technical_claims_verified": False,
            "human_approved": False,
            "export_allowed": False,
        })
    if changes["removed_public_evidence_ids"]:
        # Removed source means earlier text/attribution may require fresh
        # revalidation even if the surviving chapters appear unchanged.
        affected.update(ORDER)
    if changes["machine_contract_changed"]:
        affected.update(("SAFE_PRECONDITIONS", "BOUNDED_APPLICATION",
                         "COUNTEREXAMPLES", "VERSION_AND_QA_LIMITATIONS"))
    if changes["version_changed"]:
        affected.add("VERSION_AND_QA_LIMITATIONS")
    affected = sorted(affected, key=ORDER.index)
    return {
        "schema": REVISION_IMPACT_SCHEMA,
        "status": "AUTHORING_REVISION_REQUIRES_EXPERT_REVIEW_NO_GO",
        "topic": candidate["topic"],
        "old_draft_sha256": previous["draft_sha256"],
        "new_draft_sha256": candidate["draft_sha256"],
        "old_and_new_identity_checked": True,
        "changed_chapter_ids": changes["changed_chapter_ids"],
        "recheck_chapter_ids": affected,
        "public_evidence_added": changes["added_public_evidence_ids"],
        "public_evidence_removed": changes["removed_public_evidence_ids"],
        "machine_contract_changed": changes["machine_contract_changed"],
        "version_changed": changes["version_changed"],
        "sources": sources,
        "journal_event_count": journal["total_events"],
        "journal_head_sha256": journal["last_hash"],
        "journal_cryptographically_signed": False,
        "required_retests": [{
            "filename": name, "execution_status": "NOT_RUN_BY_REVISION_ASSESSMENT"
        } for name in REVISION_RETEST_FILES],
        "manual_decisions_required": [
            "VERIFY_SOURCE_FILE_REVISION_AND_ORIGIN",
            "REVIEW_CHANGED_CHAPTER_TECHNICAL_CLAIMS",
            "EXECUTE_RELEVANT_REGRESSION_AND_NEGATIVE_TESTS",
            "REVIEW_SECURITY_AND_LICENSE_FOR_REUSE",
            "OWNER_APPROVE_OR_REJECT_REVISION_AND_WITHDRAWAL",
        ],
        "technical_claim_review_completed": False,
        "independent_qa_completed": False,
        "owner_approval_granted": False,
        "withdrawal_executed": False,
        "review_journal_written": False,
        "running_skill_mutated": False,
        "operating_database_writes": 0,
        "external_network_requests": 0,
        "signed": False,
        "export_allowed": False,
        "released": False,
    }


