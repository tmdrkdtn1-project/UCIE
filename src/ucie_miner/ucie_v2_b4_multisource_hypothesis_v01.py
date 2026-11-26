"""Source-pinned multi-record mechanism comparison for UCIE V2 B4.

Curated UCIE-owned normalized records only; no arbitrary semantic discovery.
A match in mechanism codes proposes a hypothesis; explicit negative controls
prevent universality claims. This is not SDK validation or production review.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

from .local_v1_priority_v01 import require_local_work
from .ucie_v2_transfer_knowledge_evolution_v01 import (
    build_knowledge_index, validate_knowledge_index,
)

SCHEMA = "UCIE_V2_B4_BOUNDED_MULTISOURCE_HYPOTHESIS_V01"
MAX_RECORDS = 12
MAX_MECHANISMS = 5
MECHANISMS = frozenset((
    "CALLER_BOUNDED_SCOPE", "EXPLICIT_PROCESSING_BUDGET",
    "OUTPUT_CONTRACT_VALIDATION", "VERSION_PINNED_TRIAL",
    "FAIL_CLOSED_UNKNOWN",
))
COUNTEREXAMPLES = frozenset((
    "NAMES_MAY_BE_EXPOSED",
    "DIFFERENT_OUTPUT_SHAPES",
    "HISTORICAL_TRIAL_NOT_CURRENT_COMPATIBILITY",
))
CLAIM_RULES = (
    ("BOUNDED_SCOPE_BUDGET", frozenset((
        "CALLER_BOUNDED_SCOPE", "EXPLICIT_PROCESSING_BUDGET"))),
    ("OUTPUT_CONTRACT_VALIDATION", frozenset((
        "OUTPUT_CONTRACT_VALIDATION",))),
    ("VERSION_PINNED_TRIAL", frozenset((
        "VERSION_PINNED_TRIAL",))),
)
ID_RE = re.compile(r"[a-z0-9][a-z0-9_-]{1,47}\Z")
HEX_RE = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}\Z")


class MultiSourceError(ValueError):
    """Reject uncertain external records, synthetic approval or forged pins."""


def _hash(data: object) -> str:
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False
                             ).encode("utf-8")).hexdigest()


def pinned_records() -> list[dict]:
    """UCIE-authored metadata fixtures grounded in the existing three pins."""
    index = build_knowledge_index()
    pins = index["concepts"][0]["source_pins"]
    return [
        {"record_id": "python-scandir", "source_id": "doc:python/cpython",
         "source_pin": pins["doc:python/cpython"], "technology": "Python",
         "mechanisms": ["CALLER_BOUNDED_SCOPE", "EXPLICIT_PROCESSING_BUDGET",
                        "OUTPUT_CONTRACT_VALIDATION"],
         "counterexamples": ["NAMES_MAY_BE_EXPOSED"],
         "review_origin": "UCIE_CURATED_EXISTING_SKILLBOOK"},
        {"record_id": "git-porcelain", "source_id": "doc:git/git",
         "source_pin": pins["doc:git/git"], "technology": "Git",
         "mechanisms": ["CALLER_BOUNDED_SCOPE", "EXPLICIT_PROCESSING_BUDGET",
                        "OUTPUT_CONTRACT_VALIDATION"],
         "counterexamples": ["DIFFERENT_OUTPUT_SHAPES"],
         "review_origin": "UCIE_CURATED_EXISTING_SKILLBOOK"},
        {"record_id": "mcp-prompts", "source_id":
         "repo:modelcontextprotocol/python-sdk",
         "source_pin": pins["repo:modelcontextprotocol/python-sdk"],
         "technology": "MCP",
         "mechanisms": ["CALLER_BOUNDED_SCOPE", "EXPLICIT_PROCESSING_BUDGET",
                        "VERSION_PINNED_TRIAL", "FAIL_CLOSED_UNKNOWN"],
         "counterexamples": ["HISTORICAL_TRIAL_NOT_CURRENT_COMPATIBILITY"],
         "review_origin": "UCIE_AUTHORED_HELDOUT_CONTRACT"},
    ]


def _check_records(records: object) -> list[dict]:
    index = validate_knowledge_index(build_knowledge_index())
    pins = dict(index["concepts"][0]["source_pins"])
    # This fourth source is reviewed through the existing W01/W02/P9 gates.
    # Its historical native negative is not a fixed/current release claim.
    from .ucie_v2_b4_fourth_technology_bridge_v01 import reviewed_powershell_record
    fourth = reviewed_powershell_record()
    pins[fourth["source_id"]] = fourth["source_pin"]
    if type(records) is not list or not 2 <= len(records) <= MAX_RECORDS:
        raise MultiSourceError("bounded list of curated records required")
    unique = set()
    checked = []
    for record in records:
        if type(record) is not dict or set(record) != {
                "record_id", "source_id", "source_pin", "technology",
                "mechanisms", "counterexamples", "review_origin"}:
            raise MultiSourceError("unknown record fields")
        rid = record["record_id"]
        sid = record["source_id"]
        if (type(rid) is not str or not ID_RE.fullmatch(rid)
                or rid in unique or sid not in pins
                or type(record["source_pin"]) is not str
                or not HEX_RE.fullmatch(record["source_pin"])
                or record["source_pin"] != pins[sid]
                or record["technology"] not in ("Python", "Git", "MCP", "PowerShell")
                or (sid, record["technology"]) not in (
                    ("doc:python/cpython", "Python"),
                    ("doc:git/git", "Git"),
                    ("repo:modelcontextprotocol/python-sdk", "MCP"),
                    ("repo:PowerShell/PowerShell", "PowerShell"))
                or record["review_origin"] not in (
                    "UCIE_CURATED_EXISTING_SKILLBOOK",
                    "UCIE_AUTHORED_HELDOUT_CONTRACT",
                    "UCIE_P9_NATIVE_RELEASE_NEGATIVE_CONTROL")):
            raise MultiSourceError("unapproved source, pin or provenance")
        mechanisms = record["mechanisms"]
        negatives = record["counterexamples"]
        if (type(mechanisms) is not list or not 1 <= len(mechanisms) <=
                MAX_MECHANISMS or any(type(x) is not str for x in mechanisms)
                or len(set(mechanisms)) != len(mechanisms)
                or not set(mechanisms) <= MECHANISMS
                or type(negatives) is not list
                or len(negatives) > len(COUNTEREXAMPLES)
                or any(type(x) is not str for x in negatives)
                or len(set(negatives)) != len(negatives)
                or not set(negatives) <= COUNTEREXAMPLES):
            raise MultiSourceError("unreviewed mechanism/counterexample")
        # Avoid inventing facts by accepting only subsets of known exact
        # UCIE-authored metadata, never free-form user or upstream text.
        canonical = next((x for x in pinned_records() + [fourth]
                          if x["record_id"] == rid), None)
        if canonical is None or record != canonical:
            raise MultiSourceError("record not in fixed curated corpus")
        unique.add(rid)
        checked.append(record)
    if len({r["technology"] for r in checked}) < 2:
        raise MultiSourceError("cross-technology comparison requires diversity")
    return sorted(checked, key=lambda x: x["record_id"])


def compose_hypotheses(records: list[dict]) -> dict:
    """Produce traceable review candidates, not a universal product rule."""
    require_local_work("VIRTUAL_LIBRARY")
    normalized = _check_records(records)
    accepted = []
    rejected = []
    for name, required in CLAIM_RULES:
        supporters = [r for r in normalized
                      if required <= set(r["mechanisms"])]
        if len({r["technology"] for r in supporters}) >= 2:
            accepted.append({
                "hypothesis_id": "UCIE-VLIB-HYP-" + _hash({
                    "claim": name, "sources": [r["record_id"]
                                               for r in supporters]})[:20],
                "claim": name,
                "supporting_records": [r["record_id"] for r in supporters],
                "supporting_source_pins": [
                    {"source_id": r["source_id"], "pin": r["source_pin"]}
                    for r in supporters],
                "required_mechanisms": sorted(required),
                "status": "REVIEW_ONLY_UNVERIFIED",
                "retest_contract": {
                    "positive": "UCIE_OWNED_BOUNDED_FIXTURE_REQUIRED",
                    "negative": "TECHNOLOGY_SPECIFIC_COUNTEREXAMPLE_REQUIRED",
                    "control": "UNCHANGED_SOURCE_NO_RETEST",
                    "actual_tests_executed": False},
                "rights_approved": False,
                "export_allowed": False,
            })
        else:
            rejected.append({
                "claim": name,
                "reason": "INSUFFICIENT_INDEPENDENT_TECHNOLOGIES",
                "supporter_count": len(supporters),
                "status": "HOLD_NOT_GENERALIZABLE",
            })
    negatives = sorted({
        negative for row in normalized for negative in row["counterexamples"]
    })
    if not negatives:
        raise MultiSourceError("counterexample-free generalization forbidden")
    original_chapter = (
        "UCIE 원리 후보: 서로 다른 승인 기술의 고정된 메타데이터에서 "
        "공통 메커니즘을 비교했다. 같은 메커니즘 표기는 새 기술의 API "
        "호환성이나 실제 수정 효과를 증명하지 않는다. 반례와 적용 조건을 "
        "함께 보관하고 독립 검증 및 사용권 검토 전 반출하지 않는다."
    )
    result = {
        "schema": SCHEMA,
        "record_count": len(normalized),
        "record_ids": [r["record_id"] for r in normalized],
        "source_pins": [
            {"source_id": r["source_id"], "pin": r["source_pin"]}
            for r in normalized],
        "hypotheses": accepted,
        "held_candidates": rejected,
        "counterexample_codes": negatives,
        "original_human_skillbook_draft": original_chapter,
        "human_draft_sha256": sha256(original_chapter.encode("utf-8")).hexdigest(),
        "machine_contract": {
            "kind": "UCIE_ORIGINAL_MULTISOURCE_HYPOTHESIS_TEST_DRAFT",
            "mechanism_vocabulary": sorted(MECHANISMS),
            "positive_negative_control_required": True,
            "runtime_execution_enabled": False,
            "source_fetch_enabled": False,
            "auto_training_enabled": False,
        },
        "actual_cross_sdk_execution_verified": False,
        "autonomous_semantic_discovery_verified": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "customer_release_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    return {**result, "content_sha256": _hash(result)}


def build_curated_multisource_demo() -> dict:
    return compose_hypotheses(pinned_records())
