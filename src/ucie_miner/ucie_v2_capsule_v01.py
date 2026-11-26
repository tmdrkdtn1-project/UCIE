"""UCIE V2 B1: read-only proof capsule assembled from existing first-party modules.

Links a source-pinned SkillBook003 guide, its historic real SDK in-memory CI
receipt and UCIE's real synthetic workbench issue/control evaluators.
No network, private code, operating DB or owner V04 access; no auto-promotion.
"""
from __future__ import annotations

from dataclasses import dataclass

SCHEMA = "UCIE_VERIFIED_TECH_CAPSULE_V01_REVIEW_ONLY"
CASE_ID = "mcp-prompts"
CAPSULE_ID = "UCIE-CAPSULE-MCP-PROMPTS-GET-20261126-01"
SKILLBOOK_ID = "UCIE-SKILLBOOK-MCP-PROMPTS-003"
GUIDE_SCHEMA = "UCIE_SKILLBOOK003_MCP_PROMPTS_READONLY_REVIEW_V01"
B2_SCHEMA = "UCIE_B2_LOCAL_FOUR_PILLAR_CONNECTED_WORKBENCH_V01"
PR = "https://github.com/modelcontextprotocol/python-sdk/pull/3696"
SPEC = "https://modelcontextprotocol.io/specification/2025-11-25/server/prompts#error-handling"
BASE_COMMIT = "2118f14f8a19bc158d8a1cf90af58d85d187f849"
FIX_COMMIT = "754254c08fe1c3eda18b69da3d336106fe8d72d6"
REAL_SDK_CI = "https://github.com/tmdrkdtn1-project/UCIE/actions/runs/42585148478"
RECIPE = "ucie_miner.mcp_prompt_regression_v01.assess_transcript"
SDK_BUILDS = ("2.3.0", "2.3.1.dev9+754254c")
SDK_MODES = ("legacy", "2026-07-28")


class CapsuleContractError(ValueError):
    """Fail closed on a broken source/test/rights join without echoing input."""


@dataclass(frozen=True, slots=True)
class Capsule:
    capsule_id: str
    case_id: str
    skillbook_id: str
    official_source_url: str
    official_spec_url: str
    old_commit: str
    fixed_commit: str
    first_party_sdk_ci_url: str
    historic_sdk_calls: int
    synthetic_issue: str
    synthetic_control: str
    independent_qa: str
    rights: str
    customer_release: str
    fixed_published_version: str
    source_revision_status: str
    machine_recipe: str
    safe_next_step: str


def _same(got: object, value: object) -> bool:
    return type(got) is type(value) and got == value


def build_capsule(guide: dict, issue: dict, control: dict) -> Capsule:
    """Validate exact existing UCIE guide and synthetic receipts; no new facts."""
    if any(type(obj) is not dict for obj in (guide, issue, control)):
        raise CapsuleContractError("invalid UCIE source or receipt")
    src = guide.get("source_evidence")
    gates = guide.get("review_gates")
    recipe = guide.get("machine_skill_contract")
    if any(type(x) is not dict for x in (src, gates, recipe)):
        raise CapsuleContractError("missing source, rights or recipe")
    expected = (
        (guide.get("schema"), GUIDE_SCHEMA),
        (guide.get("skillbook_id"), SKILLBOOK_ID),
        (guide.get("export_allowed"), False),
        (src.get("official_repository"), "modelcontextprotocol/python-sdk"),
        (src.get("pr_url"), PR),
        (src.get("protocol_spec_url"), SPEC),
        (src.get("pre_fix_commit"), BASE_COMMIT),
        (src.get("patch_merge_commit"), FIX_COMMIT),
        (src.get("isolated_real_sdk_in_memory_ci"), REAL_SDK_CI),
        (src.get("observed_cases"), 16),
        (src.get("first_published_fixed_version"), "NOT_VERIFIED"),
        (recipe.get("callable"), RECIPE),
        (recipe.get("browser_execution_allowed"), False),
        (recipe.get("upstream_sdk_executed_by_guide"), False),
    )
    if any(not _same(actual, good) for actual, good in expected):
        raise CapsuleContractError("source, version or test pin mismatch")
    if (recipe.get("protocols") != ["2025-11-25", "2026-07-28"]
            or recipe.get("cases") != ["valid_prompt", "unknown_prompt",
                                        "missing_required_argument",
                                        "prompt_execution_error"]):
        raise CapsuleContractError("unreviewed MCP recipe")
    for key in ("human_approved", "license_redistribution_approved",
                "dependency_security_cleared", "independent_all_versions_verified",
                "signed", "published", "customer_release_authorized"):
        if gates.get(key) is not False:
            raise CapsuleContractError("unapproved rights claimed as granted")
    for record, scenario, code in ((issue, "issue", "CONTRACT_VIOLATION"),
                                   (control, "control", "CONTRACT_MATCH")):
        checked = (
            ("schema", B2_SCHEMA), ("case_id", CASE_ID),
            ("scenario", scenario), ("result_code", code),
            ("fixture_origin", "UCIE_AUTHORED_FIXED_SYNTHETIC"),
            ("fixture_evaluated", True),
            ("actual_user_environment_inspected", False),
            ("third_party_code_executed", False),
            ("independent_fix_validated", False),
            ("human_review_approved", False),
            ("rule_or_skillbook_promoted", False),
            ("customer_distribution_authorized", False),
            ("network_requests", 0), ("operating_database_writes", 0),
        )
        if any(not _same(record.get(k), value) for k, value in checked):
            raise CapsuleContractError("invalid first-party synthetic receipt")
    return Capsule(
        capsule_id=CAPSULE_ID, case_id=CASE_ID,
        skillbook_id=SKILLBOOK_ID,
        official_source_url=PR, official_spec_url=SPEC,
        old_commit=BASE_COMMIT, fixed_commit=FIX_COMMIT,
        first_party_sdk_ci_url=REAL_SDK_CI, historic_sdk_calls=16,
        synthetic_issue=issue["result_code"],
        synthetic_control=control["result_code"],
        independent_qa="NOT_VERIFIED", rights="NOT_APPROVED",
        customer_release="NOT_AUTHORIZED", fixed_published_version="NOT_VERIFIED",
        source_revision_status="HISTORIC_PIN_REVIEWED_FRESH_REVALIDATION_PENDING",
        machine_recipe=RECIPE,
        safe_next_step="사용 중인 MCP SDK 버전과 요청 상황부터 확인해 보세요. 코드는 보내지 마세요.",
    )


def build_from_existing_ucie() -> Capsule:
    """Consume UCIE's ACTUAL prior guide + bounded synthetic B2 engine."""
    from .mcp_prompts_guide_v01 import build_readonly_guide
    from .local_b2_connected_workbench_v01 import evaluate_case
    return build_capsule(
        build_readonly_guide(),
        evaluate_case(CASE_ID, "issue"),
        evaluate_case(CASE_ID, "control"),
    )


def evaluate_applicability(capsule: Capsule, *, version: str | None = None,
                           transport: str | None = None,
                           protocol_mode: str | None = None) -> dict:
    if type(capsule) is not Capsule or capsule.capsule_id != CAPSULE_ID:
        raise CapsuleContractError("unknown capsule")
    vals = (version, transport, protocol_mode)
    if any(v is not None and (type(v) is not str or len(v) > 64) for v in vals):
        raise CapsuleContractError("invalid declared environment")
    exact = (version in SDK_BUILDS and transport == "in_memory"
             and protocol_mode in SDK_MODES)
    return {
        "capsule_id": CAPSULE_ID, "case_id": CASE_ID,
        "declared_environment": {"version": version, "transport": transport,
                                 "protocol_mode": protocol_mode},
        "applicability": "EXACT_TESTED" if exact else "UNKNOWN_NO_PROOF",
        "decision": "REFERENCE_ONLY_NOT_CUSTOMER_APPROVED" if exact else "HOLD",
        "independent_qa": "NOT_VERIFIED", "rights": "NOT_APPROVED",
        "customer_release": "NOT_AUTHORIZED",
        "customer_pc_tested": False, "may_claim_fixed": False,
        "message": (
            "지정된 옛 메모리 내 시험 조건과 일치하더라도 고객 PC의 동작은 확인하지 않았어요."
            if exact else "지금 사용하는 환경과 버전에서 작동하는지는 아직 몰라요."
        ),
    }


def explain_for_beginner(capsule: Capsule, applicability: dict) -> dict:
    if type(applicability) is not dict or type(capsule) is not Capsule:
        raise CapsuleContractError("invalid explanation inputs")
    params = applicability.get("declared_environment")
    if (type(params) is not dict
            or set(params) != {"version", "transport", "protocol_mode"}):
        raise CapsuleContractError("missing environment proof scope")
    expected = evaluate_applicability(capsule, **params)
    if (set(expected) != set(applicability)
            or any(type(applicability[k]) is not type(v) or applicability[k] != v
                   for k, v in expected.items() if k != "declared_environment")):
        raise CapsuleContractError("forged applicability or rights")
    return {
        "schema": SCHEMA, "case_id": capsule.case_id,
        "capsule_id": capsule.capsule_id,
        "title": "MCP 프롬프트 요청에서 입력 오류를 구분해요",
        "applicability": expected["applicability"], "decision": expected["decision"],
        "message": expected["message"],
        "what_was_tested": "UCIE의 이전 독립 CI 환경에서 두 고정 SDK 시점의 메모리 내 호출 16건을 시험했습니다. 현재 합성 예제의 실패·통제군도 연결됩니다.",
        "what_is_unknown": "고객 PC, 다른 버전, HTTP/stdio, 최초 수정 포함 정식 출시 버전, 독립 QA, 의존성 보안과 배포 권리는 미확인입니다.",
        "safe_next_step": capsule.safe_next_step,
        "official_source_url": capsule.official_source_url,
        "official_spec_url": capsule.official_spec_url,
        "source_revision": capsule.fixed_commit,
        "first_party_sdk_ci_url": capsule.first_party_sdk_ci_url,
        "skillbook_id": capsule.skillbook_id,
        "machine_recipe": capsule.machine_recipe,
        "revision_status": capsule.source_revision_status,
        "independent_qa": capsule.independent_qa,
        "rights": capsule.rights, "customer_release": capsule.customer_release,
        "customer_pc_tested": False, "sdk_reexecuted_now": False,
        "auto_promoted": False, "actual_code_repaired": False,
    }


def read_only_default() -> dict:
    """One original existing-UCIE case. Unknown customer version => HOLD."""
    capsule = build_from_existing_ucie()
    return explain_for_beginner(capsule, evaluate_applicability(capsule))
