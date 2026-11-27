"""UCIE B4: bounded cross-technology transfer hypothesis, REVIEW ONLY.

Uses the existing pinned Python/Git principle. A third case is explicitly a
UCIE-authored synthetic counterexample, not independently sourced technology.
No public fetch, external execution, customer data, auto-learning or export.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .skillbook_principle_composer_v01 import compose_bounded_metadata_principle

SCHEMA = "UCIE_B4_TRANSFER_BOUNDARY_V01"
HYPOTHESIS_ID = "UCIE-B4-HYP-BOUNDED-METADATA-001"
ALLOWED_CONTEXTS = frozenset({"BOUNDED_SCANDIR", "BOUNDED_GIT_PORCELAIN"})
FACT_KIND = "UCIE_AUTHORED_INFERENCE_NOT_UPSTREAM_FACT"


class TransferBoundaryError(ValueError):
    pass


def _canonical_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")).encode("ascii")


def evaluate_transfer_case(case: dict) -> dict:
    """Evaluate an explicit machine-checkable candidate; no dynamic execution."""
    if type(case) is not dict or set(case) != {
        "case_id", "technology", "caller_authorized", "bounded_input",
        "fail_closed", "disclosure_documented", "evidence_pinned",
    }:
        raise TransferBoundaryError("INVALID_CASE_SHAPE")
    if (type(case["case_id"]) is not str or not 1 <= len(case["case_id"]) <= 80
            or not case["case_id"].isascii()
            or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in case["case_id"])):
        raise TransferBoundaryError("INVALID_CASE_ID")
    if type(case["technology"]) is not str or len(case["technology"]) > 64:
        raise TransferBoundaryError("INVALID_TECHNOLOGY")
    for key in ("caller_authorized", "bounded_input", "fail_closed",
                "disclosure_documented", "evidence_pinned"):
        if type(case[key]) is not bool:
            raise TransferBoundaryError("NON_BOOLEAN_GATE")
    if case["technology"] not in ALLOWED_CONTEXTS:
        return {"case_id": case["case_id"], "decision": "REJECT",
                "reason": "UNSUPPORTED_TECHNOLOGY_OR_SYNTHETIC_TRANSFER",
                "release_approved": False}
    if not all(case[k] for k in (
            "caller_authorized", "bounded_input", "fail_closed",
            "disclosure_documented", "evidence_pinned")):
        return {"case_id": case["case_id"], "decision": "REJECT",
                "reason": "MISSING_PRECONDITION",
                "release_approved": False}
    return {"case_id": case["case_id"], "decision": "CANDIDATE_WITHIN_TESTED_BOUNDARY",
            "reason": "STATIC_GATES_ONLY_NOT_INDEPENDENT_QA",
            "release_approved": False}


def build_transfer_hypothesis() -> dict:
    """Create a deterministic, lineage-pinned review artifact."""
    source = compose_bounded_metadata_principle()
    sources = source["sources"]
    if (len(sources) != 2 or
            {s["source_id"] for s in sources} != {"doc:python/cpython", "doc:git/git"}
            or any(s["provenance_status"] != "SOURCE_ID_PINNED_NOT_INDEPENDENT_QA"
                   for s in sources)):
        raise TransferBoundaryError("SOURCE_LINEAGE_NOT_PINNED")
    candidate = {
        "schema": SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_principle_id": source["principle_id"],
        "parent_principle_sha256": source["content_sha256"],
        "parent_source_refs": [
            {"source_id": s["source_id"], "tag": s["source_tag"],
             "sha256": s["document_sha256"]}
            for s in sources
        ],
        "claim_kind": FACT_KIND,
        "principle": "Bound metadata observations with explicit authority, budgets, failure and disclosure gates.",
        "transfer_target": "Only pre-authorized bounded metadata observations; no generalized safety guarantee.",
        "expected_benefit": "Reject a proposed transfer without required authority or bounded input.",
        "exclusions": [
            "unbounded service discovery", "customer or private project scanning",
            "execution of downloaded content", "redistribution or certification",
        ],
        "risk": "A structured gate does not establish actual runtime isolation or transfer correctness.",
        "test_plan": {
            "positive": "Pinned Python/Git cases with all gates true",
            "negative": "Missing permissions or budget and unsupported third synthetic case",
            "controls": "Reordered input and exact lineage checks",
            "independent_qa": "NOT_RUN",
        },
        "status": "REVIEW_ONLY_UNVERIFIED",
        "source_facts_separated_from_hypothesis": True,
        "third_example": {
            "case_id": "UCIE_SYNTHETIC_UNBOUNDED_001",
            "technology": "SYNTHETIC_UNBOUNDED_SERVICE_ENUMERATION",
            "classification": "UCIE_AUTHORED_COUNTEREXAMPLE_NOT_UPSTREAM_EVIDENCE",
            "expected_decision": "REJECT",
        },
        "machine_contract": {
            "input_schema": "UCIE_B4_STATIC_TRANSFER_CASE_V01",
            "output_decisions": ["CANDIDATE_WITHIN_TESTED_BOUNDARY", "REJECT"],
            "executes_code": False,
            "accesses_other_projects": False,
        },
        "rights_approved": False,
        "independent_qa_verified": False,
        "owner_approved": False,
        "export_allowed": False,
        "automatic_promotion": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    return {**candidate, "content_sha256": sha256(_canonical_bytes(candidate)).hexdigest()}
