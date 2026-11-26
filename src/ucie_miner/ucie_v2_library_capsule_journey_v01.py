"""UCIE V2 isolated B1/B2 product bridge for reviewed Virtual Library output.

The existing MCP evidence Capsule is the sole technical-truth source for the
beginner journey. The original B4 reusable review packages are attached ONLY
as separately labelled, unapproved learning materials with pinned MCP target.
No new routes, user input, private access, browser execution or live V04 edits.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
import json

from .ucie_v2_capsule_v01 import (
    CAPSULE_ID, CASE_ID, SKILLBOOK_ID, FIX_COMMIT, Capsule,
    build_from_existing_ucie, evaluate_applicability, explain_for_beginner,
)
from .ucie_v2_original_reusable_review_package_v01 import (
    build_original_review_packages, VERSION as PACKAGE_VERSION,
)
from .ucie_v2_revision_impact_v01 import MCP_ASSET, MCP_SKILLBOOK, PINS

SCHEMA = "UCIE_V2_B1_B2_VIRTUAL_LIBRARY_BRIDGE_V01"


class LibraryJourneyError(ValueError):
    """Fail closed on false joins, version assertions or approval promotion."""


def _sha(obj: object) -> str:
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def build_review_journey(history: dict, feedback: dict, previous: dict,
                         before: dict, after: dict, *, fixture_sha256: str,
                         expected_revision_head_sha256: str,
                         version: str | None = None,
                         transport: str | None = None,
                         protocol_mode: str | None = None) -> dict:
    """Produce one truthful case/capsule journey plus *related* review assets.

    A cross-source B4 derived asset is never misrepresented as the same
    independent proof as the historic MCP SDK first-party CI receipt.
    """
    capsule = build_from_existing_ucie()
    if (type(capsule) is not Capsule
            or capsule.capsule_id != CAPSULE_ID
            or capsule.case_id != CASE_ID
            or capsule.skillbook_id != SKILLBOOK_ID
            or capsule.fixed_commit != FIX_COMMIT
            or capsule.customer_release != "NOT_AUTHORIZED"
            or capsule.rights != "NOT_APPROVED"
            or capsule.independent_qa != "NOT_VERIFIED"):
        raise LibraryJourneyError("original B1 evidence/approval mismatch")
    applicability = evaluate_applicability(
        capsule, version=version, transport=transport, protocol_mode=protocol_mode)
    explanation = explain_for_beginner(capsule, applicability)
    if (explanation["case_id"] != capsule.case_id
            or explanation["capsule_id"] != capsule.capsule_id
            or explanation["customer_release"] != "NOT_AUTHORIZED"
            or explanation["customer_pc_tested"] is not False
            or explanation["sdk_reexecuted_now"] is not False
            or explanation["actual_code_repaired"] is not False):
        raise LibraryJourneyError("beginner explanation misstates evidence")
    packaged = build_original_review_packages(
        history, feedback, previous, before, after,
        fixture_sha256=fixture_sha256,
        expected_revision_head_sha256=expected_revision_head_sha256,
    )
    if (package_VERSION := PACKAGE_VERSION) != "0.1.0-review-only":
        raise LibraryJourneyError("unexpected package version")
    related = []
    for record in packaged["review_packages"]:
        recipe = record["engine_test_contract"]
        if (record["package_version"] != package_VERSION
                or recipe["target_capsule_id"] != MCP_ASSET
                or MCP_ASSET != CAPSULE_ID
                or recipe["target_upstream_commit"] != PINS[
                    "repo:modelcontextprotocol/python-sdk"]
                or recipe["target_upstream_commit"] != capsule.fixed_commit
                or record["candidate_review_status"] not in (
                    "HOLD_UNRESOLVED_SOURCE_REVISION",
                    "HOLD_INCOMPLETE_SYNTHETIC_EVIDENCE",
                    "HOLD_NO_REVISION_RETEST_EVIDENCE",
                    "REJECT_LATEST_CHALLENGER_REVIEW_ONLY",
                    "HOLD_PRIOR_RETEST",
                    "NEXT_REVISION_DRAFT_REQUIRES_INDEPENDENT_REVIEW",
                    "RETAIN_DRAFT_AWAIT_INDEPENDENT_EVIDENCE")
                or recipe["runtime_execution_enabled"] is not False
                or recipe["approved_export_enabled"] is not False
                or recipe["independent_qa_verified"] is not False
                or record["customer_export_authorized"] is not False
                or record["rights_approved"] is not False
                or record["signed"] is not False):
            raise LibraryJourneyError("false capsule/library join or rights")
        # Cross-technology candidate != exact historical SDK test.
        related.append({
            "review_package_id": record["package_id"],
            "package_sha256": record["content_sha256"],
            "kind": recipe["kind"],
            "related_capsule_id": capsule.capsule_id,
            "connected_via": "MCP_TARGET_AND_PIN_ONLY_NOT_SAME_EXPERIMENT",
            "source_history_sha256": record["source_history_sha256"],
            "next_test_kind": recipe["next_test_kind"],
            "review_status": record["candidate_review_status"],
            "independent_sdk_compatibility_proven": False,
            "rights_approved": False,
            "export_allowed": False,
        })
    related.sort(key=lambda item:item["review_package_id"])
    if not related or len(related) > 2:
        raise LibraryJourneyError("no bounded related learning evidence")
    data = {
        "schema": SCHEMA,
        "case_id": capsule.case_id,
        "capsule_id": capsule.capsule_id,
        "skillbook_id": capsule.skillbook_id,
        "requested_environment": applicability["declared_environment"],
        "applicability": applicability["applicability"],
        "decision": applicability["decision"],
        "plain_title": explanation["title"],
        "safe_next_step": explanation["safe_next_step"],
        "what_was_tested": explanation["what_was_tested"],
        "what_is_unknown": explanation["what_is_unknown"],
        "official_source_url": capsule.official_source_url,
        "fixed_commit": capsule.fixed_commit,
        "historic_first_party_sdk_ci_url": capsule.first_party_sdk_ci_url,
        "related_review_packages": related,
        "related_packages_sha256": packaged["content_sha256"],
        "actual_customer_machine_tested": False,
        "actual_source_fix_independently_verified": False,
        "rights_approved": False,
        "customer_distribution_authorized": False,
        "export_button_enabled": False,
        "new_post_endpoint_created": False,
        "private_question_text_retained": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    return {**data, "content_sha256": _sha(data)}


def render_isolated_journey(journey: dict) -> str:
    """Static single-column three-step evidence journey, no new route."""
    if (type(journey) is not dict or journey.get("schema") != SCHEMA
            or journey.get("case_id") != CASE_ID
            or journey.get("capsule_id") != CAPSULE_ID
            or journey.get("skillbook_id") != SKILLBOOK_ID
            or journey.get("fixed_commit") != FIX_COMMIT
            or journey.get("content_sha256") != _sha({
                k:v for k,v in journey.items() if k != "content_sha256"})
            or journey.get("actual_customer_machine_tested") is not False
            or journey.get("actual_source_fix_independently_verified") is not False
            or journey.get("rights_approved") is not False
            or journey.get("customer_distribution_authorized") is not False
            or journey.get("export_button_enabled") is not False
            or journey.get("new_post_endpoint_created") is not False
            or journey.get("private_question_text_retained") is not False
            or journey.get("network_requests") != 0
            or journey.get("operating_database_writes") != 0
            or type(journey.get("related_review_packages")) is not list
            or not 1 <= len(journey["related_review_packages"]) <= 2):
        raise LibraryJourneyError("unsafe or forged journey")
    capsule = build_from_existing_ucie()
    if journey["official_source_url"] != capsule.official_source_url:
        raise LibraryJourneyError("official source mismatch")
    declared = journey.get("requested_environment")
    if type(declared) is not dict:
        raise LibraryJourneyError("invalid requested environment")
    expected = evaluate_applicability(capsule, **declared)
    if (journey.get("applicability") != expected["applicability"]
            or journey.get("decision") != expected["decision"]
            or journey.get("safe_next_step") != capsule.safe_next_step):
        raise LibraryJourneyError("version or action mismatch")
    for row in journey["related_review_packages"]:
        if (type(row) is not dict
                or row.get("related_capsule_id") != CAPSULE_ID
                or row.get("connected_via") !=
                  "MCP_TARGET_AND_PIN_ONLY_NOT_SAME_EXPERIMENT"
                or row.get("independent_sdk_compatibility_proven") is not False
                or row.get("rights_approved") is not False
                or row.get("export_allowed") is not False):
            raise LibraryJourneyError("related asset cannot claim SDK approval")
    e=lambda value:escape(value,quote=True)
    return (
        '<main data-ucie-v2-isolated-journey="review-only">'
        '<section aria-labelledby="v2-step-1"><h2 id="v2-step-1">1. 어떤 도움이 필요하세요?</h2>'
        '<p>' + e(journey["plain_title"]) + '</p>'
        '<p>이 예제는 실제 PC나 비공개 코드를 검사하지 않아요.</p></section>'
        '<section aria-labelledby="v2-step-2"><h2 id="v2-step-2">2. 확인된 범위는 어디까지인가요?</h2>'
        '<p>' + e(journey["what_was_tested"]) + '</p>'
        '<p>' + e(journey["what_is_unknown"]) + '</p>'
        '<p>현재 상태: ' + e(journey["applicability"]) + ' / '
        + e(journey["decision"]) + '</p></section>'
        '<section aria-labelledby="v2-step-3"><h2 id="v2-step-3">3. 지금 확인할 일</h2>'
        '<p>' + e(journey["safe_next_step"]) + '</p>'
        '<p>고객 환경에서 수정 효과와 재배포 권리는 아직 확인되지 않았어요.</p></section>'
        '<details><summary>왜 이렇게 안내하나요?</summary>'
        '<p>기술 확인 기록: ' + e(journey["capsule_id"]) + '</p>'
        '<p>원본 버전: ' + e(journey["fixed_commit"]) + '</p>'
        '<p>기존 기술 안내: ' + e(journey["skillbook_id"]) + '</p>'
        '<p>추가 검토 중인 기술 가이드: ' +
        str(len(journey["related_review_packages"])) + '건 (배포 미승인)</p>'
        '</details></main>'
    )
