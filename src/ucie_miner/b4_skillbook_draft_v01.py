"""UCIE B4 review-only SkillBook chapter and machine-readable contract.

Composes existing source-pinned curated principle, static transfer hypothesis,
and optional affected-only revision proposal. No file output or publication.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .skillbook_principle_composer_v01 import compose_bounded_metadata_principle
from .b4_transfer_boundary_v01 import build_transfer_hypothesis
from .b4_revision_impact_v01 import propose_affected_retests

SCHEMA = "UCIE_B4_ORIGINAL_SKILLBOOK_DRAFT_V01"
BOOK_ID = "UCIE-SKILLBOOK-B4-TRANSFER-BOUNDARY-004"
VERSION = "0.1.0-draft"


class B4SkillBookError(ValueError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")).encode("ascii")


def build_b4_skillbook(changes: list[dict] | None = None) -> dict:
    """Produce a bounded original text chapter and executable-interface spec.

    An optional change list is treated as unauthenticated proposal data.
    """
    principle = compose_bounded_metadata_principle()
    hypothesis = build_transfer_hypothesis()
    if hypothesis["parent_principle_id"] != principle["principle_id"]:
        raise B4SkillBookError("PARENT_PRINCIPLE_ID_DRIFT")
    if hypothesis["parent_principle_sha256"] != principle["content_sha256"]:
        raise B4SkillBookError("PARENT_PRINCIPLE_SHA_DRIFT")
    if type(changes) is not list and changes is not None:
        raise B4SkillBookError("INVALID_CHANGE_LIST")
    impact = propose_affected_retests(changes) if changes is not None else None
    if impact is not None and (impact["hypothesis_id"] != hypothesis["hypothesis_id"]
                               or impact["hypothesis_sha256"] != hypothesis["content_sha256"]):
        raise B4SkillBookError("IMPACT_PARENT_DRIFT")

    sections = [
        {
            "heading": "Why bounded metadata observation matters",
            "claim_kind": "UCIE_ORIGINAL_DERIVED_HYPOTHESIS",
            "text": (
                "First confirm that the caller controls the input and is allowed to observe "
                "the chosen metadata. Fix an item or byte budget and a fail-closed error "
                "boundary. A plausible transfer is not proof of isolation or safety."
            ),
        },
        {
            "heading": "Compare the two pinned techniques",
            "claim_kind": "UCIE_ORIGINAL_CURATED_COMPARISON",
            "text": (
                "The Python scandir recipe enumerates sorted regular filenames from "
                "an explicitly approved directory with an entry budget. The Git "
                "porcelain parser accepts caller-supplied NUL-delimited bytes with "
                "record and byte budgets, then returns counts only. Their output "
                "disclosure differs, and their numeric budgets are not interchangeable."
            ),
        },
        {
            "heading": "When not to transfer",
            "claim_kind": "UCIE_ORIGINAL_COUNTEREXAMPLE",
            "text": (
                "Do not apply this candidate to arbitrary service discovery, unknown "
                "technologies, private repositories, customer code, unbounded input, "
                "untrusted source execution, or rights and release decisions. An "
                "invented third scenario remains a synthetic negative control."
            ),
        },
        {
            "heading": "Revisions and affected-only verification",
            "claim_kind": "UCIE_ORIGINAL_REVISION_WORKFLOW",
            "text": (
                "Compare a proposed source revision against exact parent source IDs, "
                "tags and SHA-256 pins. A changed tag or digest creates a review and "
                "retest proposal for dependent artifacts only; unchanged sources do "
                "not trigger retests. An asserted observation never authenticates "
                "the upstream revision or approves its transfer."
            ),
        },
    ]
    contract = {
        "schema": "UCIE_B4_TRANSFER_SKILL_CONTRACT_V01",
        "version": VERSION,
        "input_contract": {
            "transfer_case_required_fields": [
                "case_id", "technology", "caller_authorized", "bounded_input",
                "fail_closed", "disclosure_documented", "evidence_pinned",
            ],
            "source_revision_input": "optional bounded proposed changes, never trusted",
        },
        "callables": [
            "ucie_miner.b4_transfer_boundary_v01.evaluate_transfer_case",
            "ucie_miner.b4_revision_impact_v01.propose_affected_retests",
        ],
        "allowed_contexts": ["BOUNDED_GIT_PORCELAIN", "BOUNDED_SCANDIR"],
        "decisions": ["REJECT", "CANDIDATE_WITHIN_TESTED_BOUNDARY"],
        "retest_execution": False,
        "source_fetching": False,
        "customer_project_access": False,
        "machine_executable_contract_only": True,
        "review_status": "REVIEW_ONLY_UNVERIFIED",
        "independent_qa_verified": False,
        "rights_approved": False,
        "owner_approved": False,
        "export_allowed": False,
        "released": False,
    }
    body = {
        "schema": SCHEMA, "skillbook_id": BOOK_ID, "version": VERSION,
        "title": "Bounded metadata transfer and revision-aware review",
        "status": "DRAFT_NOT_APPROVED",
        "human_chapters": sections,
        "machine_contract": contract,
        "source_provenance": hypothesis["parent_source_refs"],
        "parent_principle_id": principle["principle_id"],
        "parent_principle_sha256": principle["content_sha256"],
        "parent_hypothesis_id": hypothesis["hypothesis_id"],
        "parent_hypothesis_sha256": hypothesis["content_sha256"],
        "impact_proposal": impact,
        "capsule_ids": [],
        "capsule_link_status": "NOT_AVAILABLE_DO_NOT_INVENT",
        "test_receipts": [],
        "independent_qa_verified": False,
        "rights_approved": False, "owner_approved": False,
        "export_allowed": False, "released": False,
        "automatic_promotion": False, "network_requests": 0,
        "operating_database_writes": 0, "other_project_access": False,
        "revision_history": [{
            "version": VERSION,
            "reason": "ORIGINAL_DRAFT_FROM_CURATED_PINNED_PARENTS",
            "previous_version": None, "approved": False,
        }],
    }
    if len(_canonical(body)) > 24576:
        raise B4SkillBookError("DRAFT_SIZE_BUDGET_EXCEEDED")
    return {**body, "content_sha256": sha256(_canonical(body)).hexdigest()}


def render_b4_skillbook_markdown(book: dict,
                                 changes: list[dict] | None = None) -> str:
    """Render only an exact draft rebuilt from the same bounded inputs."""
    if type(book) is not dict:
        raise B4SkillBookError("BOOK_INVALID")
    expected = build_b4_skillbook(changes)
    if book != expected:
        raise B4SkillBookError("BOOK_CONTENT_MISMATCH")
    lines = [
        "# UCIE SkillBook B4 004 — Bounded metadata transfer",
        "",
        "> REVIEW_ONLY_UNVERIFIED. Original UCIE inference, not upstream fact,",
        "> independent QA, security certification, rights approval or release.",
        "",
        "## Source lineage",
        "",
        "- Parent principle: " + book["parent_principle_id"],
        "- Parent hypothesis: " + book["parent_hypothesis_id"],
        "- Capsule IDs: unavailable; no capsule linkage claimed",
        "",
    ]
    for row in book["source_provenance"]:
        lines.append("- " + row["source_id"] + " / " + row["tag"]
                     + " / SHA-256 " + row["sha256"])
    lines.append("")
    for row in book["human_chapters"]:
        lines.extend(["## " + row["heading"], "", row["text"], "",
                      "Claim kind: " + row["claim_kind"], ""])
    if book["impact_proposal"] is not None:
        lines.extend([
            "## Proposed source revision review",
            "",
            "Affected source count: " + str(book["impact_proposal"]["retests_proposed"]),
            "Test execution: NOT_RUN; proposed source changes are not authenticated.",
            "",
        ])
        for item in book["impact_proposal"]["affected_sources"]:
            lines.extend([
                "- " + item["source_id"] + " (" + item["before_tag"] + " -> "
                + item["proposed_tag"] + "): REVIEW_AND_RETEST_DEPENDENTS",
            ])
        lines.append("")
    lines.extend([
        "## Machine-readable contract",
        "",
        "```json",
        json.dumps(book["machine_contract"], indent=2, ensure_ascii=True,
                   sort_keys=True),
        "```",
        "",
        "Export: prohibited. Tests: separate bounded first-party checks only.",
        "",
    ])
    rendered = "\n".join(lines)
    if len(rendered.encode("utf-8")) > 20000:
        raise B4SkillBookError("RENDER_SIZE_EXCEEDED")
    return rendered
