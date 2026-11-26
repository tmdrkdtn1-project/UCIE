"""UCIE V2 B4: bounded source-linked principle transfer hypothesis and test.

Rule-based structured inference over TWO existing UCIE-authored approved-public
source-linked draft SkillBooks, with a third UCIE MCP synthetic control.
Not arbitrary semantic discovery, model training, independent upstream QA,
an approved portable skill, or autonomous customer code access.
"""
from __future__ import annotations

from hashlib import sha256
import json

SCHEMA = "UCIE_V2_B4_BOUNDED_STRUCTURED_GENERALIZATION_V01"
METHOD = "FIRST_PARTY_STRUCTURED_CROSS_SOURCE_HYPOTHESIS_NOT_AUTONOMOUS_MODEL"
FACETS = (
    "EXPLICIT_CALLER_INPUT",
    "BOUNDED_MAX_ENTRIES",
    "FAIL_CLOSED_NEGATIVE_CONTROLS",
    "NO_IMPLICIT_CATALOG_EXECUTION",
    "NOT_A_SECURITY_SANDBOX",
)
TARGET = "UCIE-MCP-PROMPTS-GET-BOUNDED-TRANSCRIPT-TRANSFER"
REJECTED_SCOPE = "AUTOMATIC_CUSTOMER_CODE_EXECUTION_IS_SAFE"
POSITIVE_CASE = "missing_required_argument"


class B4HypothesisError(ValueError):
    """No false generalization, client approval or unreviewed source output."""


def _valid_book(book: dict, source_id: str, digest: str,
                skillbook_id: str, expected_callable: str) -> dict:
    if type(book) is not dict:
        raise B4HypothesisError("invalid source-linked SkillBook")
    entry = book.get("library_entry")
    source = book.get("source_evidence")
    gates = book.get("proof_gates")
    machine = book.get("machine_skill_contract")
    if any(type(v) is not dict for v in (entry, source, gates, machine)):
        raise B4HypothesisError("incomplete source, rights or machine contract")
    if (book.get("skillbook_id") != skillbook_id
            or book.get("status") != "FIRST_PARTY_DRAFT_NOT_APPROVED"
            or book.get("export_allowed") is not False
            or book.get("model_training_performed") is not False
            or book.get("auto_promoted") is not False
            or book.get("network_requests") != 0
            or book.get("operating_database_writes") != 0
            or book.get("other_project_access") is not False
            or book.get("upstream_source_executed") is not False
            or entry.get("source_id") != source_id
            or entry.get("evidence_sha256") != digest
            or source.get("source_document_sha256") != digest
            or entry.get("approval_status") != "NOT_APPROVED"
            or entry.get("export_allowed") is not False
            or machine.get("callable") != expected_callable):
        raise B4HypothesisError("SkillBook identity, source or approval drift")
    for key in ("independent_test_verified", "license_redistribution_approved",
                "security_review_approved", "human_approved", "signed", "published"):
        if gates.get(key) is not False:
            raise B4HypothesisError("unapproved SkillBook elevated")
    inputs, outputs = machine.get("inputs"), machine.get("outputs")
    pres, negative = machine.get("preconditions"), machine.get("negative_tests")
    if (type(inputs) is not dict or not inputs
            or type(outputs) is not dict
            or type(pres) is not list or type(negative) is not list
            or len(negative) < 3
            or type(inputs.get("max_entries")) is not str
            or "INTEGER_1_TO_" not in inputs["max_entries"]
            or type(outputs.get("on_failure")) is not str
            or not outputs["on_failure"].endswith("_FAIL_CLOSED")
            or "NOT_A_SECURITY_SANDBOX" not in pres
            or machine.get("runtime_execution_by_catalog") is not False
            or machine.get("external_code_execution") is not False):
        raise B4HypothesisError("missing structural transfer precondition")
    # Extract transfer facts from the actual pinned machine-contract fields;
    # do not assign universal facets to every book without checking its input,
    # budget, error and disclosure semantics.
    contracts = {
        "doc:python/cpython": (
            "approved_directory", "EXPLICIT_OWNER_AUTHORIZED_ABSOLUTE_LOCAL_DIRECTORY",
            "INTEGER_1_TO_128_INCLUSIVE", "SORTED_TUPLE_OF_REGULAR_FILENAMES_ONLY",
            "FILE_NAMES_DISCLOSED_TO_AUTHORIZED_CALLER",
        ),
        "doc:git/git": (
            "payload", "CALLER_SUPPLIED_GIT_PORCELAIN_V1_Z_BYTES_ONLY",
            "INTEGER_1_TO_64_INCLUSIVE", "BOUNDED_INTEGER_COUNTS_WITH_NO_PATH_BYTES",
            "COUNTS_ONLY_NO_PATH_NAMES",
        ),
    }
    if source_id not in contracts:
        raise B4HypothesisError("unreviewed principle transfer source")
    input_key, input_contract, limit, output_contract, privacy = contracts[source_id]
    if (inputs.get(input_key) != input_contract
            or inputs.get("max_entries") != limit
            or outputs.get("on_success") != output_contract):
        raise B4HypothesisError("source-specific input/output contract drift")
    extracted = []
    if inputs.get(input_key) == input_contract:
        extracted.append("EXPLICIT_CALLER_INPUT")
    if inputs.get("max_entries") == limit:
        extracted.append("BOUNDED_MAX_ENTRIES")
    if (outputs["on_failure"].endswith("_FAIL_CLOSED")
            and len(negative) >= 3):
        extracted.append("FAIL_CLOSED_NEGATIVE_CONTROLS")
    if (machine.get("runtime_execution_by_catalog") is False
            and machine.get("external_code_execution") is False):
        extracted.append("NO_IMPLICIT_CATALOG_EXECUTION")
    if "NOT_A_SECURITY_SANDBOX" in pres:
        extracted.append("NOT_A_SECURITY_SANDBOX")
    if set(extracted) != set(FACETS):
        raise B4HypothesisError("cannot derive shared bounded mechanism")
    return {
        "source_id": source_id, "document_sha256": digest,
        "skillbook_id": skillbook_id,
        "original_machine_callable": expected_callable,
        "facets": tuple(sorted(extracted)),
        "input_budget_contract": limit,
        "observed_output_contract": output_contract,
        "data_disclosure_boundary": privacy,
        "first_party_structured_annotation_only": True,
        "independent_qa": False,
        "rights_approved": False,
    }


def build_hypothesis() -> dict:
    """Derive ONE candidate from real Python/Git input+failure contracts."""
    from .ucie_v2_revision_impact_v01 import (
        build_current_graph, PINS, PY_BOOK, GIT_BOOK, PRINCIPLE,
    )
    from .ucie_v2_capsule_v01 import build_from_existing_ucie
    from .skillbook_product_v01 import build_skillbook as build_py
    from .skillbook_git_porcelain_product_v01 import build_skillbook as build_git
    from .skillbook_principle_composer_v01 import (
        compose_bounded_metadata_principle, SUPPORT,
    )
    from .mcp_prompt_regression_v01 import MAX_TRANSCRIPT_BYTES

    graph = build_current_graph()
    principle = compose_bounded_metadata_principle()
    capsule = build_from_existing_ucie()
    if (graph.get("global_asset_coverage_verified") is not False
            or principle.get("principle_id") != PRINCIPLE
            or principle.get("status") != "UCIE_CURATED_CROSS_SOURCE_CHAPTER_DRAFT_NO_GO"
            or principle.get("generalization_method") !=
                    "FIRST_PARTY_CURATED_EXPLICIT_COMPARISON"
            or principle.get("export_allowed") is not False
            or capsule.rights != "NOT_APPROVED"
            or capsule.independent_qa != "NOT_VERIFIED"
            or capsule.customer_release != "NOT_AUTHORIZED"
            or type(MAX_TRANSCRIPT_BYTES) is not int
            or MAX_TRANSCRIPT_BYTES != 16384):
        raise B4HypothesisError("curated original evidence or target scope drift")
    examples = []
    for book, book_id, source_id in (
        (build_py(), PY_BOOK, "doc:python/cpython"),
        (build_git(), GIT_BOOK, "doc:git/git"),
    ):
        examples.append(_valid_book(
            book, source_id, PINS[source_id], book_id,
            SUPPORT[book_id]["callable"],
        ))
    if ({x["source_id"] for x in examples} !=
            {"doc:python/cpython", "doc:git/git"}
            or {x["skillbook_id"] for x in examples} != {PY_BOOK, GIT_BOOK}):
        raise B4HypothesisError("cross-source independence missing")
    examples.sort(key=lambda x: x["skillbook_id"])
    shared = sorted(set(examples[0]["facets"]) & set(examples[1]["facets"]))
    if shared != sorted(FACETS):
        raise B4HypothesisError("incomplete common premise")
    base = {
        "schema": SCHEMA,
        "method": METHOD,
        "parents": examples,
        "shared_candidate_facets": shared,
        "target_capsule_id": capsule.capsule_id,
        "target_upstream_commit": capsule.fixed_commit,
        "target_ucie_recipe": capsule.machine_recipe,
        "target_case": TARGET,
        "hypothesis": (
            "명시적으로 승인된 입력과 처리 예산을 분리하고, 형식 오류를 제한된 "
            "반례로 검증하는 구조는 서로 다른 메타데이터 파서 사이에서 "
            "재사용할 수 있는 UCIE 작성 설계 후보입니다."
        ),
        "transfer_expected": (
            "MCP의 UCIE 자체 최대 16384바이트 제한 JSON-RPC 합성 검사에서는 "
            "정상 응답이 계약 일치를, 구형 잘못된 오류 응답이 계약 위반을 보여야 합니다."
        ),
        "explicit_exclusions": [
            "실제 MCP SDK 또는 네트워크 전송의 범용 호환성",
            "개인 저장소·고객 코드 실행 또는 자동 수정",
            "모든 언어·버전·보안 환경으로의 무조건적 일반화",
        ],
        "rejected_overgeneralization": REJECTED_SCOPE,
        "nontransferable_privacy_claim": {
            "claim": "ALL_BOUNDED_METADATA_PROCESSES_HIDE_SOURCE_NAMES",
            "status": "REJECTED_BY_EXPLICIT_DIFFERING_OUTPUT_CONTRACTS",
            "counterexample_skillbook_id": PY_BOOK,
            "counterexample_output_contract": "SORTED_TUPLE_OF_REGULAR_FILENAMES_ONLY",
            "contrasting_skillbook_id": GIT_BOOK,
            "contrasting_output_contract": "BOUNDED_INTEGER_COUNTS_WITH_NO_PATH_BYTES",
        },
    }
    fingerprint = sha256(json.dumps(
        base, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    return {
        **base, "hypothesis_id": "UCIE-B4-HYP-" + fingerprint[:20],
        "content_sha256": fingerprint,
        "human_skillbook_chapter_status": "UCIE_ORIGINAL_HYPOTHESIS_DRAFT_ONLY",
        "machine_test_recipe": {
            "callable": capsule.machine_recipe,
            "positive_case": POSITIVE_CASE,
            "negative_control": "OLD_NONCOMPLIANT_ERROR_CODE",
            "execution_error_control": "prompt_execution_error",
            "protocol": "2025-11-25",
            "target_runtime_import_or_network_allowed": False,
            "customer_data_input_allowed": False,
        },
        "source_facts_independently_verified": False,
        "cross_source_model_generalization_verified": False,
        "model_trained": False, "owner_approved": False,
        "license_redistribution_approved": False, "published": False,
        "export_allowed": False, "auto_promoted": False,
        "network_requests": 0, "operating_database_writes": 0,
    }


def run_bounded_transfer(hypothesis: dict) -> dict:
    """Execute three UCIE-authored in-memory fixtures, NEVER the upstream SDK."""
    if type(hypothesis) is not dict or hypothesis != build_hypothesis():
        raise B4HypothesisError("untrusted hypothesis or approval flags changed")
    from .mcp_prompt_regression_v01 import (
        assess_transcript, _request, _response, SCHEMA as WIRE_SCHEMA,
    )
    def check(case: str, *, before_fix: bool = False) -> dict:
        report = assess_transcript({
            "case": case, "protocol_revision": "2025-11-25",
            "request": _request(case),
            "response": _response(case, before_fix=before_fix),
        })
        if (type(report) is not dict
                or report.get("schema") != WIRE_SCHEMA
                or report.get("sdk_executed") is not False
                or report.get("independent_upstream_behavior_verified") is not False
                or report.get("auto_promoted") is not False
                or report.get("customer_release_authorized") is not False
                or report.get("network_requests") != 0
                or report.get("persistent_writes") != 0):
            raise B4HypothesisError("real SDK or approval evidence forged")
        return report
    positive = check(POSITIVE_CASE)
    negative = check(POSITIVE_CASE, before_fix=True)
    control = check("prompt_execution_error")
    statuses = (positive.get("status"), negative.get("status"),
                control.get("status"))
    if statuses != ("CONTRACT_MATCH", "CONTRACT_VIOLATION", "CONTROL_ONLY"):
        raise B4HypothesisError("transfer validation or negative control failed")
    return {
        "schema": SCHEMA,
        "status": "FIRST_PARTY_BOUNDED_SYNTHETIC_TRANSFER_REVIEW_ONLY",
        "hypothesis_id": hypothesis["hypothesis_id"],
        "content_sha256": hypothesis["content_sha256"],
        "parent_skillbooks": [x["skillbook_id"] for x in hypothesis["parents"]],
        "target_capsule_id": hypothesis["target_capsule_id"],
        "positive_negative_control": list(statuses),
        "overbroad_output_privacy_claim_rejected": True,
        "nontransferable_privacy_status":
            hypothesis["nontransferable_privacy_claim"]["status"],
        "synthetic_cases_executed": 3,
        "real_upstream_sdk_rerun": False,
        "independent_qa_verified": False,
        "candidate_automatically_approved": False,
        "general_purpose_autonomous_reasoning_proven": False,
        "export_allowed": False, "model_trained": False,
        "network_requests": 0, "operating_database_writes": 0,
    }
