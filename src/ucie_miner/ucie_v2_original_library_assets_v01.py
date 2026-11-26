"""UCIE V2: produce original, revision-aware library assets for human and machine review.

Produces first-party content, test contract and review disposition solely from
already source-pinned UCIE products. No external content execution, customer
inspection, model training, automatic export, promotion or persistent write.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .ucie_v2_b3_b4_b5_revision_review_v01 import (
    SCHEMA as REVISION_SCHEMA, review_revision_sensitive_study,
)
from .ucie_v2_generalization_review_v01 import render_hypothesis_chapter
from .ucie_v2_generalization_transfer_v01 import (
    FACETS, SCHEMA as HYPOTHESIS_SCHEMA, build_hypothesis,
    run_bounded_transfer,
)

SCHEMA = "UCIE_V2_VIRTUAL_LIBRARY_ORIGINAL_ASSET_BUNDLE_V01"
BUNDLE_ID = "UCIE-V2-VLIB-BOUNDED-METADATA-MCP-TRANSFER-001"
SOURCE_IDS = frozenset(("doc:python/cpython", "doc:git/git"))
CONTROL_STATUSES = ("CONTRACT_MATCH", "CONTRACT_VIOLATION", "CONTROL_ONLY")
COUNTEREXAMPLE_STATUS = "REJECTED_BY_EXPLICIT_DIFFERING_OUTPUT_CONTRACTS"


class LibraryAssetError(ValueError):
    """Reject incompatible provenance, authority, tests, or existing receipts."""


def _digest(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False
                             ).encode("utf-8")).hexdigest()


def assemble_original_library_assets(records: tuple[dict, ...],
                                     signals: tuple[dict, ...]) -> dict:
    """Create reproducible structured assets; no side effects or trusted promotion.

    An upstream candidate SHA is only a hypothetical revision signal.
    Review status does not authorize using this package as a release artifact.
    """
    revision = review_revision_sensitive_study(records, signals)
    h = build_hypothesis()
    trial = run_bounded_transfer(h)
    chapter = render_hypothesis_chapter()
    parents = h.get("parents")
    counterexample = h.get("nontransferable_privacy_claim")
    recipe = h.get("machine_test_recipe")
    if (revision.get("schema") != REVISION_SCHEMA
            or revision.get("hypothesis_id") != h.get("hypothesis_id")
            or revision.get("previous_hypothesis_sha256") != h.get("content_sha256")
            or revision.get("target_capsule_id") != h.get("target_capsule_id")
            or revision.get("candidate_source_sha_authenticated") is not False
            or revision.get("candidate_b4_generalization_verified") is not False
            or revision.get("real_competitive_advantage_verified") is not False
            or revision.get("customer_release_authorized") is not False
            or revision.get("network_requests") != 0
            or revision.get("operating_database_writes") != 0
            or h.get("schema") != HYPOTHESIS_SCHEMA
            or h.get("shared_candidate_facets") != sorted(FACETS)
            or type(parents) is not list or len(parents) != 2
            or any(type(p) is not dict for p in parents)
            or {p.get("source_id") for p in parents} != SOURCE_IDS
            or {p.get("document_sha256") for p in parents}
                   != {x.get("document_sha256")
                       for x in revision["previous_source_lineage"]}
            or any(p.get("independent_qa") is not False
                   or p.get("rights_approved") is not False for p in parents)
            or type(counterexample) is not dict
            or counterexample.get("status") != COUNTEREXAMPLE_STATUS
            or counterexample.get("counterexample_output_contract")
                   == counterexample.get("contrasting_output_contract")
            or type(recipe) is not dict
            or recipe.get("target_runtime_import_or_network_allowed") is not False
            or recipe.get("customer_data_input_allowed") is not False
            or recipe.get("positive_case") != "missing_required_argument"
            or recipe.get("negative_control") != "OLD_NONCOMPLIANT_ERROR_CODE"
            or recipe.get("execution_error_control") != "prompt_execution_error"
            or recipe.get("protocol") != "2025-11-25"
            or trial.get("schema") != HYPOTHESIS_SCHEMA
            or trial.get("hypothesis_id") != h.get("hypothesis_id")
            or trial.get("content_sha256") != h.get("content_sha256")
            or trial.get("positive_negative_control") != list(CONTROL_STATUSES)
            or trial.get("synthetic_cases_executed") != 3
            or trial.get("real_upstream_sdk_rerun") is not False
            or trial.get("candidate_automatically_approved") is not False
            or trial.get("independent_qa_verified") is not False
            or trial.get("export_allowed") is not False
            or h.get("auto_promoted") is not False
            or h.get("owner_approved") is not False
            or h.get("license_redistribution_approved") is not False
            or h.get("published") is not False
            or h.get("export_allowed") is not False
            or h.get("model_trained") is not False
            or h.get("source_facts_independently_verified") is not False
            or "가상도서관" not in chapter
            or h["hypothesis_id"] not in chapter
            or h["content_sha256"] not in chapter
            or "배포 불가" not in chapter):
        raise LibraryAssetError("source lineage, original chapter, controls or authority drift")

    sources = sorted(({
        "source_id": p["source_id"],
        "document_sha256": p["document_sha256"],
        "skillbook_id": p["skillbook_id"],
        "input_budget_contract": p["input_budget_contract"],
        "observed_output_contract": p["observed_output_contract"],
        "data_disclosure_boundary": p["data_disclosure_boundary"],
    } for p in parents), key=lambda p: p["source_id"])
    chapter_asset = {
        "asset_kind": "UCIE_ORIGINAL_HUMAN_SKILLBOOK_CHAPTER_DRAFT",
        "hypothesis_id": h["hypothesis_id"],
        "text": chapter,
        "text_sha256": sha256(chapter.encode("utf-8")).hexdigest(),
        "source_lineage": sources,
        "publication_status": "REVIEW_ONLY_NOT_APPROVED",
    }
    machine_asset = {
        "asset_kind": "UCIE_FIRST_PARTY_MACHINE_ENGINE_TEST_CONTRACT",
        "hypothesis_id": h["hypothesis_id"],
        "source_hypothesis_sha256": h["content_sha256"],
        "transfer_target_capsule_id": h["target_capsule_id"],
        "target_upstream_commit": h["target_upstream_commit"],
        "runtime_recipe_identifier": h["target_ucie_recipe"],
        "input_contract": {
            "caller_owned_bounded_synthetic_transcript_only": True,
            "maximum_transcript_bytes": 16384,
            "protocol": recipe["protocol"],
            "no_customer_data": True,
        },
        "shared_candidate_facets": sorted(FACETS),
        "expected_fixtures": [
            {"fixture": "missing_required_argument", "expected": "CONTRACT_MATCH"},
            {"fixture": "OLD_NONCOMPLIANT_ERROR_CODE", "expected": "CONTRACT_VIOLATION"},
            {"fixture": "prompt_execution_error", "expected": "CONTROL_ONLY"},
        ],
        "counterexample": {
            "claim": counterexample["claim"],
            "result": counterexample["status"],
            "different_output_contracts": sorted((
                counterexample["counterexample_output_contract"],
                counterexample["contrasting_output_contract"],
            )),
        },
        "runtime_execution_enabled": False,
        "external_code_execution_allowed": False,
        "autonomous_training_enabled": False,
        "rights_approved": False,
        "independent_qa_verified": False,
        "export_allowed": False,
    }

    affected = bool(revision["impacted_existing_assets"])
    incomplete = not revision["original_b5_synthetic_study_complete"]
    expected_status = ("SOURCE_CHANGE_CANDIDATE_HOLD_PAIRED_STUDY_STALE"
                       if affected else "SYNTHETIC_PAIR_INCOMPLETE_HOLD"
                       if incomplete else "UNCHANGED_PINNED_SYNTHETIC_REVIEW_ONLY")
    if revision["status"] != expected_status:
        raise LibraryAssetError("invalid B3/B4/B5 lifecycle transition")
    disposition = {
        "asset_kind": "UCIE_BOUNDED_REVISION_DISPOSITION_NOT_PRODUCTION",
        "hypothesis_id": h["hypothesis_id"],
        "previous_hypothesis_sha256": h["content_sha256"],
        "candidate_hypothesis_sha256": "NOT_COMPUTED",
        "revision_candidate_signal_sha256": _digest(signals),
        "changed_source_ids": revision["candidate_changed_source_ids"],
        "affected_assets": revision["impacted_existing_assets"],
        "proposed_affected_only_tests": revision["proposed_affected_only_test_files"],
        "prior_synthetic_study_complete": not incomplete,
        "prior_synthetic_study_valid_for_candidate": (
            revision["b5_synthetic_evidence_current_for_candidate"]
        ),
        "review_status": (
            "REVIEW_HOLD_CANDIDATE_SOURCE_CHANGE" if affected
            else "REVIEW_HOLD_INCOMPLETE_PAIRED_FIXTURE" if incomplete
            else "REVIEW_ACTIVE_UNVERIFIED"
        ),
        "candidate_source_authenticated": False,
        "actual_tests_executed_by_disposition": False,
        "retest_scheduled": False,
        "history_persisted": False,
    }
    payload = {
        "schema": SCHEMA,
        "bundle_id": BUNDLE_ID,
        "chapter": chapter_asset,
        "machine": machine_asset,
        "revision": disposition,
        "synthetic_transfer_status": trial["status"],
        "source_facts_independently_verified": False,
        "real_upstream_tested": False,
        "actual_human_evidence": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "release_authorized": False,
        "automatic_training": False,
        "automatic_promotion": False,
        "automatic_distribution": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    return {**payload, "content_sha256": _digest(payload)}
