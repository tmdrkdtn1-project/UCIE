"""UCIE B2 one-user-job, four-pillar read-only workbench.

A selected, fixed error type flows into a genuinely evaluated UCIE-authored
synthetic control, then the existing public library and evidence-evolution
views. No customer log, arbitrary command, real SDK, file, Git, PowerShell,
network or customer workflow is executed. A matching synthetic contract is
NEVER a verified real-world fix, approved rule, or commercial release.
"""
from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

from .local_error_actionable_workflow_v01 import CASE_IDS, get_case

SCHEMA = "UCIE_B2_LOCAL_FOUR_PILLAR_CONNECTED_WORKBENCH_V01"
STATUS = "UCIE_FIRST_PARTY_SYNTHETIC_OBSERVATION_REVIEW_ONLY"
SCENARIOS = ("issue", "control")
PURPOSE = "B2_CONNECTED_TRIAGE"

# All public-browsing links use bounded known words, never user text.
PUBLIC_QUERIES = {
    "python-env": "Python",
    "powershell-command": "PowerShell",
    "git-repository": "Git",
    "mcp-prompts": "MCP",
}


def _python_environment(scenario: str) -> tuple[str, str, str]:
    active = PureWindowsPath("C:/UCIE_SYNTHETIC/venv_a/Scripts/python.exe")
    pip_target = (active if scenario == "control"
                  else PureWindowsPath("C:/UCIE_SYNTHETIC/venv_b/Scripts/python.exe"))
    mismatch = active != pip_target
    return (
        "INTERPRETER_MISMATCH" if mismatch else "INTERPRETER_PATHS_MATCH",
        "두 Python 경로가 서로 다름" if mismatch else "예제 Python 경로가 일치",
        "경로가 같아도 패키지 설치·import 성공까지 보장하지 않음",
    )


def _powershell_precedence(scenario: str) -> tuple[str, str, str]:
    # Simplified, UCIE-authored candidate fixture; not the host command table.
    precedence = {"Alias": 0, "Function": 1, "Cmdlet": 2, "Application": 3}
    candidates = ("Application", "Alias") if scenario == "issue" else ("Cmdlet",)
    winner = min(candidates, key=lambda kind: precedence[kind])
    return (
        "ALIAS_SHADOWS_COMMAND" if winner == "Alias" else "EXPECTED_CMDLET_CHOSEN",
        "예제에서 Alias가 Application보다 우선" if winner == "Alias"
        else "예제에서 Cmdlet 하나만 검색됨",
        "현재 PowerShell 세션의 Get-Command 결과는 읽지 않음",
    )


def _git_repository(scenario: str) -> tuple[str, str, str]:
    # Pure virtual path arithmetic. No os.getcwd, git or filesystem probes.
    checkout = PurePosixPath("/UCIE_SYNTHETIC/repo")
    location = (PurePosixPath("/UCIE_SYNTHETIC/outside") if scenario == "issue"
                else checkout / "src")
    inside = location == checkout or checkout in location.parents
    return (
        "OUTSIDE_WORKTREE" if not inside else "INSIDE_WORKTREE",
        "예제 작업 위치가 저장소 바깥" if not inside
        else "예제 작업 위치가 저장소 내부",
        "실제 저장소 인식에는 git rev-parse를 사람이 직접 확인해야 함",
    )


def _mcp_prompt_contract(scenario: str) -> tuple[str, str, str]:
    # Real UCIE first-party wire-contract validator, but synthetic requests only.
    from .mcp_prompt_regression_v01 import (
        SCHEMA as MCP_SCHEMA, _request, _response, assess_transcript,
    )
    report = assess_transcript({
        "case": "missing_required_argument",
        "protocol_revision": "2025-11-25",
        "request": _request("missing_required_argument"),
        "response": _response("missing_required_argument",
                              before_fix=(scenario == "issue")),
    })
    expected = "CONTRACT_VIOLATION" if scenario == "issue" else "CONTRACT_MATCH"
    if (type(report) is not dict
            or report.get("schema") != MCP_SCHEMA
            or report.get("status") != expected
            or report.get("sdk_executed") is not False
            or report.get("independent_upstream_behavior_verified") is not False
            or report.get("auto_promoted") is not False
            or report.get("customer_release_authorized") is not False
            or report.get("network_requests") != 0
            or report.get("persistent_writes") != 0):
        raise ValueError("UCIE synthetic MCP contract must fail closed")
    return (
        expected,
        "합성 입력 누락 응답이 -32602 계약과 다름" if scenario == "issue"
        else "합성 입력 누락 응답이 -32602 계약과 일치",
        "실제 MCP SDK 서버·수정 배포판은 실행하거나 승인하지 않음",
    )


_EVALUATORS = {
    "python-env": _python_environment,
    "powershell-command": _powershell_precedence,
    "git-repository": _git_repository,
    "mcp-prompts": _mcp_prompt_contract,
}
EXPECTED = {
    "python-env": ("INTERPRETER_MISMATCH", "INTERPRETER_PATHS_MATCH"),
    "powershell-command": ("ALIAS_SHADOWS_COMMAND", "EXPECTED_CMDLET_CHOSEN"),
    "git-repository": ("OUTSIDE_WORKTREE", "INSIDE_WORKTREE"),
    "mcp-prompts": ("CONTRACT_VIOLATION", "CONTRACT_MATCH"),
}


def evaluate_case(case_id: str, scenario: str) -> dict:
    """Run one bounded, real first-party algorithm on a fixed synthetic fixture."""
    if (type(case_id) is not str or case_id not in CASE_IDS
            or type(scenario) is not str or scenario not in SCENARIOS
            or set(_EVALUATORS) != set(CASE_IDS)
            or set(EXPECTED) != set(CASE_IDS)):
        raise ValueError("only exact UCIE authored B2 scenarios are allowed")
    case = get_case(case_id)
    result, observation, limitation = _EVALUATORS[case_id](scenario)
    if (result != EXPECTED[case_id][SCENARIOS.index(scenario)]
            or type(observation) is not str or not observation
            or type(limitation) is not str or not limitation):
        raise ValueError("synthetic B2 observation contract drift")
    q = PUBLIC_QUERIES[case_id]
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "case_id": case_id,
        "scenario": scenario,
        "label": case["label"],
        "result_code": result,
        "observed_synthetic_result": observation,
        "limitation": limitation,
        "official_source_url": case["official_url"],
        "official_source_label": case["official_title"],
        "public_library_query": q,
        "evolution_query": q,
        "fixture_origin": "UCIE_AUTHORED_FIXED_SYNTHETIC",
        "fixture_evaluated": True,
        "actual_user_environment_inspected": False,
        "third_party_code_executed": False,
        "arbitrary_command_or_path_accepted": False,
        "independent_fix_validated": False,
        "human_review_approved": False,
        "rule_or_skillbook_promoted": False,
        "customer_distribution_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
