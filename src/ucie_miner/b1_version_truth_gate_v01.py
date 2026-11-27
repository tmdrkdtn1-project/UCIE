"""UCIE B1 explicit source-revision and execution-proof truth gate.

Read-only preview of existing pinned B1 first-party capsules. A source tag is NOT
proof that the customer's Python/SDK runtime works. No customer environment
discovery, imported code, persistence, source retrieval or release.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

from .b1_b4_skillbook_capsule_link_v01 import build_pinned_b1_capsules
from .local_v1_priority_v01 import require_local_work

SCHEMA = "UCIE_B1_VERSION_AND_RIGHTS_TRUTH_GATE_V01"
_VALID_TAG = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")
_VERSION_STATES = frozenset({"UNKNOWN_NO_PROOF", "SOURCE_REVISION_MISMATCH_HOLD"})
_RIGHTS_STATE = "NOT_APPROVED"


class B1TruthGateError(ValueError):
    pass


def evaluate_b1_source_revision(case_id: str, requested_source_tag: str | None) -> dict:
    """Validate the *declared source revision* only, never claim runtime support.

    Unknown requested version -> hold. Different source tag -> explicit source
    mismatch hold. Exact source tag -> source pin match, but runtime applicability
    is still UNKNOWN_NO_PROOF until separate trial/version proof is supplied.
    """
    require_local_work("VIRTUAL_LIBRARY")
    if type(case_id) is not str or not case_id or len(case_id) > 96:
        raise B1TruthGateError("INVALID_CASE_ID")
    if (requested_source_tag is not None
            and (type(requested_source_tag) is not str
                 or _VALID_TAG.fullmatch(requested_source_tag) is None)):
        raise B1TruthGateError("INVALID_DECLARED_SOURCE_TAG")
    capsules = build_pinned_b1_capsules()
    matches = [x for x in capsules if x["case_id"] == case_id]
    if len(matches) != 1:
        raise B1TruthGateError("CASE_NOT_SOURCE_PINNED")
    cap = matches[0]
    if (cap["upstream_authenticity"] != "NOT_INDEPENDENTLY_ATTESTED"
            or cap["rights_approved"] is not False
            or cap["independent_qa_verified"] is not False
            or cap["export_allowed"] is not False
            or cap["owner_approved"] is not False):
        raise B1TruthGateError("SOURCE_RIGHTS_OR_PROOF_STATUS_DRIFT")
    match = requested_source_tag == cap["source_tag"]
    status = ("UNKNOWN_NO_PROOF"
              if requested_source_tag is None or match
              else "SOURCE_REVISION_MISMATCH_HOLD")
    if status not in _VERSION_STATES:
        raise B1TruthGateError("UNEXPECTED_STATE")
    explanation = (
        "공개 문서 버전이 다릅니다. 현재 자료로는 적용할 수 있다고 안내하지 않습니다."
        if status == "SOURCE_REVISION_MISMATCH_HOLD"
        else "문서 버전을 확인했지만 실제 사용 환경에서 작동하는지는 아직 시험하지 않았습니다."
        if match else
        "사용 중인 문서 버전이 확인되지 않아 적용 가능 여부를 판단하지 않습니다."
    )
    receipt = {
        "schema": SCHEMA,
        "case_id": cap["case_id"],
        "capsule_id": cap["capsule_id"],
        "capsule_sha256": cap["content_sha256"],
        "source_id": cap["source_id"],
        "pinned_source_tag": cap["source_tag"],
        "source_document_sha256": cap["source_document_sha256"],
        "requested_source_tag": requested_source_tag,
        "source_revision_match_only": match,
        "source_revision_decision": status,
        "runtime_version_applicability": "UNKNOWN_NO_PROOF",
        "tested_runtime_version": None,
        "first_party_runtime_receipt": None,
        "independent_qa": "NOT_VERIFIED",
        "rights": _RIGHTS_STATE,
        "owner_approved": False,
        "export_allowed": False,
        "release_approved": False,
        "human_next_step": explanation,
        "source_fetches": 0,
        "customer_project_reads": 0,
        "operating_database_writes": 0,
        "test_execution": "NOT_RUN",
    }
    digest = sha256(json.dumps(receipt, ensure_ascii=True, allow_nan=False,
                               sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()
    return {**receipt, "receipt_sha256": digest}
