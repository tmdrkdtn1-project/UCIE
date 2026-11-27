"""B3 real documented Python 3.15 scandir(-1) delta, source-truth separated.

Official Python 3.14/3.15 docs checked 2026-11-27. The docs describe
the behavior change, but have not been immutable-content SHA attested here.
This is an owner-review proposal, not a proof of tested customer runtime,
automatic upstream monitoring or approval to alter the existing SkillBook.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .b1_b4_skillbook_capsule_link_v01 import build_pinned_b1_capsules
from .local_v1_priority_v01 import require_local_work

SCHEMA = "UCIE_B3_DOCUMENTED_SCANDIR_315_DELTA_V01"
SOURCE_OLD = "https://docs.python.org/3.14/library/os.html"
SOURCE_NEW = "https://docs.python.org/3.15/library/os.html"
DOCUMENTED_CHANGE = "os.scandir(-1) raises OSError(errno.EBADF) in Python 3.15"
PYTHON_CASE = "UCIE-SKILLBOOK-PY-SCANDIR-001"
GIT_CASE = "UCIE-SKILLBOOK-GIT-PORCELAIN-002"


class DocumentedDeltaError(ValueError):
    pass


def evaluate_documented_scandir_delta(case_id: str, *,
                                      proposed_runtime: str | None = None,
                                      uses_negative_one: bool | None = None) -> dict:
    """Safe version-specific risk recommendation for exactly two pinned cases.

    The exact -1 call-site condition must be expressly declared, not guessed.
    An actual Python 3.15 fix cannot be inferred for the existing UCIE
    bounded directory recipe, whose calls have not been audited here.
    """
    require_local_work("VIRTUAL_LIBRARY")
    if type(case_id) is not str or case_id not in (PYTHON_CASE, GIT_CASE):
        raise DocumentedDeltaError("UNKNOWN_PINNED_CASE")
    if proposed_runtime is not None and (type(proposed_runtime) is not str
                                          or proposed_runtime not in ("3.14", "3.15")):
        raise DocumentedDeltaError("UNSUPPORTED_DECLARED_VERSION")
    if uses_negative_one is not None and type(uses_negative_one) is not bool:
        raise DocumentedDeltaError("INVALID_CALLSITE_DECLARATION")
    caps = build_pinned_b1_capsules()
    match = [c for c in caps if c["case_id"] == case_id]
    if len(match) != 1:
        raise DocumentedDeltaError("CAPSULE_NOT_PRESENT")
    capsule = match[0]
    if (capsule["source_id"] !=
            ("doc:python/cpython" if case_id == PYTHON_CASE else "doc:git/git")
            or capsule["export_allowed"] is not False
            or capsule["rights_approved"] is not False):
        raise DocumentedDeltaError("CAPSULE_PROVENANCE_DRIFT")

    relevant_source = case_id == PYTHON_CASE
    # Never use a source tag to assert actual code-path usage or environment.
    changed_callsite_risk = (relevant_source and proposed_runtime == "3.15"
                             and uses_negative_one is True)
    unknown_callsite = (relevant_source and proposed_runtime == "3.15"
                        and uses_negative_one is None)
    affected_sources = ["doc:python/cpython"] if relevant_source else []
    recommended = (
        "REVIEW_NEGATIVE_FD_CALLSITE_BEFORE_UPGRADE" if changed_callsite_risk else
        "CHECK_CALLSITE_FIRST_NO_EXECUTION" if unknown_callsite else
        "NO_RETEST_FROM_THIS_DELTA" if not relevant_source else
        "NO_NEGATIVE_FD_RISK_DECLARED_OR_VERSION_UNKNOWN"
    )
    result = {
        "schema": SCHEMA,
        "case_id": case_id,
        "capsule_id": capsule["capsule_id"],
        "capsule_sha256": capsule["content_sha256"],
        "source_id": capsule["source_id"],
        "pinned_source_tag": capsule["source_tag"],
        "documented_change": DOCUMENTED_CHANGE,
        "older_official_document": SOURCE_OLD,
        "newer_official_document": SOURCE_NEW,
        "documentation_observation_date": "2026-11-27",
        "documentation_delta_observed": True,
        "documentation_content_sha256_attested": False,
        "official_revision_commit_verified": False,
        "customer_runtime_version_verified": False,
        "declared_runtime_version": proposed_runtime,
        "declared_negative_fd_callsite": uses_negative_one,
        "relevant_curated_source": relevant_source,
        "affected_source_ids": affected_sources,
        "affected_only": True,
        "retest_candidate": changed_callsite_risk,
        "retest_executed": False,
        "retest_status": "NOT_RUN",
        "callsite_analysis_status": (
            "DECLARED_NOT_INDEPENDENTLY_VERIFIED" if uses_negative_one is not None
            else "UNKNOWN_NO_PROOF"),
        "recommendation": recommended,
        "independent_qa": "NOT_VERIFIED",
        "rights_approved": False,
        "owner_approved": False,
        "released": False,
        "customer_project_reads": 0,
        "network_fetches_at_runtime": 0,
        "operating_database_writes": 0,
    }
    digest = sha256(json.dumps(result, sort_keys=True, ensure_ascii=True,
                               separators=(",", ":")).encode("ascii")).hexdigest()
    return {**result, "proposal_sha256": digest}
