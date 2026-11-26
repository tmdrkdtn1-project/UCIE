"""UCIE V2 original reusable engine/SkillBook review package from REAL loop.

Recomputes the first-party iterative cycle: never accepts an unchecked or
user-forged release report. Produces one human original and one machine recipe
per source-pinned candidate, with exact first-party synthetic receipt, version
lineage, negative contracts and explicit export/rights/QA HOLD flags.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .ucie_v2_iterative_learning_cycle_v01 import (
    advance_virtual_library_review_cycle,
)
from .ucie_v2_library_revision_ledger_v01 import (
    validate_review_history, _validate_bundle,
)
from .ucie_v2_feedback_registry_v01 import validate_feedback_registry
from .ucie_v2_revision_review_history_v01 import validate_revision_history
from .ucie_v2_hypothesis_reassessment_v01 import ALLOWED_TESTS, REJECTED_CLAIM

SCHEMA = "UCIE_V2_ORIGINAL_REUSABLE_REVIEW_PACKAGE_V01"
VERSION = "0.1.0-review-only"
MAX_ASSETS = 2


class ReviewPackageError(ValueError):
    """Unsigned first-party synthetic output cannot gain deployment rights."""


def _hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def build_original_review_packages(history: dict, feedback: dict, previous: dict,
                                   before_cases: dict, after_cases: dict,
                                   *, fixture_sha256: str,
                                   expected_revision_head_sha256: str) -> dict:
    """Bind actual evidence -> paired retest -> original text + machine recipe.

    No files, imports of arbitrary modules, network, source execution, signing,
    training or changes to protected owner originals. Version is pre-release.
    """
    pinned = validate_review_history(history)
    validate_feedback_registry(pinned, feedback)
    validate_revision_history(pinned, previous)
    cycle = advance_virtual_library_review_cycle(
        pinned, feedback, previous, before_cases, after_cases,
        fixture_sha256=fixture_sha256,
        expected_revision_head_sha256=expected_revision_head_sha256,
    )
    source = pinned["events"][-1]["bundle"] if pinned["events"] else None
    if source is None:
        raise ReviewPackageError("missing original library evidence")
    _validate_bundle(source)
    latest = cycle["next_generation_draft"]
    candidates = {c["candidate_id"]: c for c in latest["next_candidates"]}
    addenda = cycle["original_skillbook_addenda"]
    if (len(candidates) not in (1,2)
            or len(addenda) != len(candidates) or len(addenda) > MAX_ASSETS
            or cycle["original_source_history_sha256"] != pinned["content_sha256"]
            or cycle["original_feedback_registry_sha256"] != feedback["content_sha256"]
            or cycle["customer_release_authorized"] is not False
            or cycle["rights_approved"] is not False):
        raise ReviewPackageError("mismatched source or review execution")
    packages = []
    for addendum in addenda:
        cid = addendum["candidate_id"]
        candidate = candidates.get(cid)
        if (candidate is None
                or addendum["new_next_draft_sha256"] != candidate["next_draft_sha256"]
                or addendum["original_candidate_sha256"] != candidate["source_candidate_sha256"]
                or REJECTED_CLAIM not in candidate["reusable_negative_constraints"]
                or candidate["source_change_hold_active"] !=
                    addendum["previous_source_revision_hold_preserved"]
                or candidate["actual_external_test_pass"] is not False
                or candidate["owner_approved"] is not False
                or type(addendum["proposed_test_names"]) is not list
                or not set(addendum["proposed_test_names"]).issubset(ALLOWED_TESTS)):
            raise ReviewPackageError("candidate source contract mismatch")
        prose = addendum["original_human_skillbook_addendum"]
        if (not isinstance(prose, str) or not prose.strip()
                or sha256(prose.encode("utf-8")).hexdigest()
                    != addendum["addendum_sha256"]):
            raise ReviewPackageError("original chapter changed")
        machine = source["machine"]
        recipe = {
            "kind": "UCIE_FIRST_PARTY_REUSABLE_ENGINE_TEST_RECIPE_DRAFT",
            "candidate_id": cid,
            "parent_hypothesis_id": machine["hypothesis_id"],
            "original_bundle_sha256": source["content_sha256"],
            "new_draft_sha256": candidate["next_draft_sha256"],
            "supported_protocol": machine["input_contract"]["protocol"],
            "source_lineage": source["chapter"]["source_lineage"],
            "target_capsule_id": machine["transfer_target_capsule_id"],
            "target_upstream_commit": machine["target_upstream_commit"],
            "input_contract": machine["input_contract"],
            "expected_synthetic_controls": machine["expected_fixtures"],
            "explicit_negative_constraint": REJECTED_CLAIM,
            "test_names_review_only": addendum["proposed_test_names"],
            "next_test_kind": candidate["next_test_kind"],
            "runtime_execution_enabled": False,
            "external_sdk_tested": False,
            "independent_qa_verified": False,
            "rights_approved": False,
            "approved_export_enabled": False,
        }
        core = {
            "package_version": VERSION,
            "human_skillbook_text": prose,
            "human_text_sha256": addendum["addendum_sha256"],
            "engine_test_contract": recipe,
            "source_history_sha256": pinned["content_sha256"],
            "feedback_registry_sha256": feedback["content_sha256"],
            "revision_report_sha256": cycle["revision_report_sha256"],
            "revision_history_sha256": cycle["next_revision_history_sha256"],
            "candidate_review_status": candidate["next_review_status"],
            "prior_source_hold_preserved": candidate["source_change_hold_active"],
            "first_party_synthetic_only": True,
            "independent_qa_verified": False,
            "rights_approved": False,
            "customer_export_authorized": False,
            "signed": False,
            "installed": False,
            "model_trained": False,
        }
        package_sha = _hash(core)
        packages.append({
            **core,
            "package_id": "UCIE-V2-REVIEW-PKG-" + package_sha[:24],
            "content_sha256": package_sha,
        })
    packages.sort(key=lambda x: x["package_id"])
    result = {
        "schema": SCHEMA,
        "source_history_sha256": pinned["content_sha256"],
        "feedback_registry_sha256": feedback["content_sha256"],
        "cycle_sha256": cycle["content_sha256"],
        "review_packages": packages,
        "package_count": len(packages),
        "review_only": True,
        "independent_source_verification": False,
        "external_execution_pass": False,
        "rights_approved": False,
        "customer_distribution_authorized": False,
        "automatic_rule_promotion": False,
        "automatic_model_training": False,
        "operating_database_writes": 0,
        "network_requests": 0,
    }
    return {**result, "content_sha256": _hash(result)}
