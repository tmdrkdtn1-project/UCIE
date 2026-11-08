"""UCIE Local V1: actionable, source-bound manual review of an existing public candidate.

Turns one owner-selected W04 public evidence row into a concrete safe-fix and
independent regression worksheet. No approval, writes, network or code execution.
Never interprets upstream PR text as executable instructions.
"""
from __future__ import annotations

import re

from .local_v1_priority_v01 import require_local_work
from .regression_plans import TEST_FAMILIES
from .rule_candidates import GUIDANCE, REQUIRED_GATES

SCHEMA = "UCIE_LOCAL_V1_PUBLIC_CANDIDATE_REVIEW_WORKSHEET_V01"
ALLOWED_SOURCES = frozenset((
    "repo:python/cpython",
    "repo:PowerShell/PowerShell",
    "repo:git/git",
    "repo:modelcontextprotocol/python-sdk",
    "repo:actions/runner-images",
))
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
PATTERN = re.compile(r"[A-Z][A-Z0-9_]{2,95}\Z")
VERSION = re.compile(r"[A-Za-z0-9_.+ -]{1,100}\Z")

class ReviewWorksheetError(ValueError):
    """Source, provenance, status or identity is not suitable for display."""


def create_review_worksheet(row: dict) -> dict:
    """Only source-linked W04 candidates are eligible, never approved fixes.

    A caller must select this row from a freshly read bounded W04 page.
    The worksheet is NOT a new trusted source, standalone approver or editor.
    """
    require_local_work("ERROR_PREVENTION")
    if type(row) is not dict:
        raise ReviewWorksheetError("review must use a W04 candidate row")
    item_id, digest = row.get("library_item_id"), row.get("evidence_sha256")
    source, url = row.get("source_id"), row.get("public_url")
    pattern, version = row.get("purpose_code"), row.get("version_scope_claim")
    if (type(item_id) is not str or DIGEST.fullmatch(item_id) is None
            or type(digest) is not str or DIGEST.fullmatch(digest) is None
            or type(source) is not str or source not in ALLOWED_SOURCES
            or type(url) is not str
            or not url.startswith("https://github.com/" + source[5:] + "/")
            or len(url) > 320 or any(c in url for c in '<>"\\')
            or type(pattern) is not str or PATTERN.fullmatch(pattern) is None
            or type(version) is not str or VERSION.fullmatch(version) is None
            or row.get("lifecycle") != "UNVERIFIED_CANDIDATE_ONLY"
            or row.get("human_approved") is not False
            or row.get("export_allowed") is not False):
        raise ReviewWorksheetError("public evidence identity, scope or status not acceptable")

    guidance = GUIDANCE.get(pattern)
    test = TEST_FAMILIES.get(pattern)
    if test is not None and source not in (
            "repo:python/cpython", "repo:PowerShell/PowerShell"):
        # A test design for a different source family is not applicable.
        test = None
    if test is not None and (
            pattern.startswith("PY_") and source != "repo:python/cpython"
            or pattern.startswith("PS_") and source not in (
                "repo:PowerShell/PowerShell", "repo:python/cpython")):
        test = None

    return {
        "schema": SCHEMA,
        "status": "SOURCE_BOUND_MANUAL_REVIEW_DRAFT_NOT_APPROVED",
        "library_item_id": item_id,
        "source_id": source,
        "public_url": url,
        "evidence_sha256": digest,
        "pattern_code": pattern,
        "version_scope_claim": version,
        "safe_fix_guidance": guidance[0] if guidance else None,
        "regression_plan": guidance[1] if guidance else None,
        "fixture_design": test[0] if test else None,
        "expected_invariant": test[1] if test else None,
        "target_environment": test[2] if test else None,
        "required_gates": {key: "NOT_VERIFIED" for key in REQUIRED_GATES},
        "manual_actions": (
            "허용된 공개 원본 링크를 열어 PR·커밋의 출처 및 변경 내용부터 대조합니다.",
            "공식 릴리스와 원본 기술 문서에서 영향 버전·수정 버전을 확인합니다. PR 제목만으로 호환을 단정하지 않습니다.",
            "실제 오류를 재현할 수 있는 독립·격리 시험과 반례를 설계합니다. 외부 코드를 그대로 실행하지 않습니다.",
            "회귀·보안·라이선스 검토와 사람의 명시적 승인 전에는 규칙으로 채택하거나 배포하지 않습니다.",
        ),
        "regression_executed": False,
        "source_fix_independently_verified": False,
        "owner_approval_recorded": False,
        "automatic_rule_promotion": False,
        "operating_database_writes": 0,
        "network_requests": 0,
        "upstream_code_executed": False,
        "customer_or_other_project_inspected": False,
        "export_allowed": False,
    }
