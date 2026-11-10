"""UCIE B1 SkillBook 003: readable, review-only MCP prompts/get guide.

One first-party, fixed public-evidence learning item for the already approved
official modelcontextprotocol/python-sdk source. No fetch, SDK import, arbitrary
user code, source parsing, auto-promotion, package export or runtime write.
The actual SDK integration receipts exist ONLY for the two pinned builds and
two observed protocol modes; they are not generalized runtime guarantees.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .mcp_prompt_regression_v01 import (
    SOURCE_PR, SOURCE_ISSUE, SOURCE_SPEC, UPSTREAM_MERGE_SHA,
    PRE_FIX_TAG, PRE_FIX_TAG_COMMIT, PROTOCOLS,
)

SCHEMA = "UCIE_SKILLBOOK003_MCP_PROMPTS_READONLY_REVIEW_V01"
SKILLBOOK_ID = "UCIE-SKILLBOOK-MCP-PROMPTS-003"
STATUS = "SOURCE_PINNED_FIRST_PARTY_DRAFT_NOT_APPROVED"
TITLE = "MCP prompts/get 입력 오류와 실행 오류 구분"
SEARCH = re.compile(r"[\w .-]{0,80}\Z", re.UNICODE)
SEARCH_TERMS = (
    "mcp", "prompts", "prompt", "sdk", "json-rpc", "-32602", "invalid_params",
    "프롬프트", "필수", "인수", "입력", "오류", "예외", "호출", "에러",
)
CHAPTERS = (
    ("문제가 발생하는 조건",
     "prompts/get에서 미등록 프롬프트 이름 또는 누락된 필수 인수는 호출자의 입력 오류입니다. "
     "정상 인수로 프롬프트를 실행하는 도중 발생한 예외는 입력 오류와 구분해야 합니다.",
     "OFFICIAL_PROTOCOL_PLUS_PINNED_PUBLIC_SDK"),
    ("수정 전후에 실제 확인된 동작",
     "공식 Python SDK v2.3.0과 수정 PR #3696 병합 커밋을 별도 격리 환경에 설치한 뒤 "
     "두 프로토콜 모드에서 네 가지 요청을 비교했습니다. 수정 전의 미등록 프롬프트/필수 인수 누락 "
     "오류는 구형 모드 0, 신형 모드 -32603이었고, 수정 병합본에서는 모두 -32602였습니다. "
     "이것은 지정한 두 소스 시점과 시험 시나리오의 결과입니다.",
     "EXACT_PINNED_SDK_IN_MEMORY_OBSERVATION"),
    ("안전한 확인 절차",
     "요청 JSON-RPC 버전, 요청과 응답 id, 결과 또는 오류의 배타적 존재, 오류 코드의 정수형 여부를 "
     "확인합니다. 미등록 프롬프트와 필수 인수 누락은 -32602를 기대합니다. "
     "메시지 문자열만 비교하거나 서버 실행 오류를 입력 오류로 바꾸면 안 됩니다.",
     "UCIE_AUTHORED_FIRST_PARTY_GUIDANCE"),
    ("재사용 가능한 검사 계약",
     "UCIE 자체 assess_transcript()는 호출자가 직접 제공한 16,384바이트 이하의 제한된 "
     "JSON-RPC 교환 한 건을 네 가지 합성 시나리오와 두 프로토콜 모드에서 검사합니다. "
     "이 함수는 외부 MCP SDK를 실행하거나 프로젝트 파일을 읽지 않으며, "
     "검사 결과만으로 실제 SDK 버전의 수정 여부를 인증하지 않습니다.",
     "FIRST_PARTY_BOUNDED_MACHINE_CONTRACT"),
    ("적용 한계와 미승인 범위",
     "HTTP/stdio 전송, 모든 SDK 버전, 공식 최초 수정 포함 배포판, 전체 의존성 권리와 취약점은 "
     "검증되지 않았습니다. 개발 빌드 식별자 2.3.1.dev9+754254c는 공개 릴리스가 아닙니다. "
     "SkillBook의 소유자 승인, 재배포 사용권, 고객용 서명과 제품 출시는 아직 허용되지 않습니다.",
     "LIMITATIONS_RELEASE_NO_GO"),
)


class MCPGuideError(ValueError):
    """Public guide contract or search input is invalid."""


def matches(query: str) -> bool:
    if type(query) is not str or SEARCH.fullmatch(query) is None:
        raise MCPGuideError("invalid bounded public guide query")
    parts = tuple(x.casefold() for x in query.strip().split())
    hay = " ".join((TITLE, SKILLBOOK_ID, *SEARCH_TERMS)).casefold()
    return all(p in hay for p in parts)


def build_readonly_guide() -> dict:
    """Return caller-owned content with exact public evidence and NO-GO gates."""
    if (SOURCE_PR != "https://github.com/modelcontextprotocol/python-sdk/pull/3696"
            or UPSTREAM_MERGE_SHA != "754254c08fe1c3eda18b69da3d336106fe8d72d6"
            or PRE_FIX_TAG != "v2.3.0"
            or PRE_FIX_TAG_COMMIT != "2118f14f8a19bc158d8a1cf90af58d85d187f849"
            or PROTOCOLS != ("2025-11-25", "2026-07-28")):
        raise MCPGuideError("official source pin or local regression contract drift")
    return {
        "schema": SCHEMA, "skillbook_id": SKILLBOOK_ID,
        "title": TITLE, "status": STATUS,
        "chapters": [
            {"heading": h, "text": text, "claim_scope": scope}
            for h, text, scope in CHAPTERS
        ],
        "source_evidence": {
            "official_repository": "modelcontextprotocol/python-sdk",
            "issue_url": SOURCE_ISSUE,
            "pr_url": SOURCE_PR, "protocol_spec_url": SOURCE_SPEC,
            "pre_fix_tag": PRE_FIX_TAG,
            "pre_fix_commit": PRE_FIX_TAG_COMMIT,
            "patch_merge_commit": UPSTREAM_MERGE_SHA,
            "isolated_real_sdk_in_memory_ci":
                "https://github.com/tmdrkdtn1-project/UCIE/actions/runs/42585148478",
            "observed_cases": 16,
            "first_published_fixed_version": "NOT_VERIFIED",
            "source_code_redistributed": False,
        },
        "machine_skill_contract": {
            "callable": "ucie_miner.mcp_prompt_regression_v01.assess_transcript",
            "inputs": "UCIE_DEFINED_CASE_PROTOCOL_REQUEST_RESPONSE_ONE_JSON_OBJECT_UP_TO_16384_BYTES",
            "cases": [
                "valid_prompt", "unknown_prompt",
                "missing_required_argument", "prompt_execution_error",
            ],
            "protocols": list(PROTOCOLS),
            "expected_input_error": -32602,
            "output": "CONTRACT_MATCH_OR_CONTRACT_VIOLATION_OR_CONTROL_ONLY_OR_INPUT_REJECTED_NO_GO",
            "browser_execution_allowed": False,
            "upstream_sdk_executed_by_guide": False,
            "arbitrary_project_code_access": False,
        },
        "review_gates": {
            "human_approved": False,
            "license_redistribution_approved": False,
            "dependency_security_cleared": False,
            "independent_all_versions_verified": False,
            "signed": False, "published": False,
            "customer_release_authorized": False,
        },
        "export_allowed": False,
        "auto_promoted": False, "other_project_access": False,
        "network_requests": 0, "operating_database_writes": 0,
    }
