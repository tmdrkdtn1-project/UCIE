"""UCIE-owned, offline prompts/get wire contract scanner (not the MCP SDK).

Source pins:
* modelcontextprotocol/python-sdk PR #3696, merge 754254c0...
* 2025-11-25 official MCP prompts specification, Error Handling
* 2026-07-28 behavior as described by approved SDK PR/issue/interaction tests

This module DOES NOT execute the SDK, import upstream code, fetch URLs,
read owner files or promote a rule. It checks bounded caller-supplied JSON.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

SCHEMA = "UCIE_MCP_PROMPTS_GET_WIRE_REGRESSION_V01"
SOURCE_PR = "https://github.com/modelcontextprotocol/python-sdk/pull/3696"
SOURCE_ISSUE = "https://github.com/modelcontextprotocol/python-sdk/issues/3669"
SOURCE_SPEC = "https://modelcontextprotocol.io/specification/2025-11-25/server/prompts#error-handling"
UPSTREAM_MERGE_SHA = "754254c08fe1c3eda18b69da3d336106fe8d72d6"
PRE_FIX_TAG = "v2.3.0"
PRE_FIX_TAG_COMMIT = "2118f14f8a19bc158d8a1cf90af58d85d187f849"
PRE_FIX_MANAGER_BLOB = "01a0823bf74c72c2197b846bf94a5f0ff00dfcea"
FIXED_MERGE_MANAGER_BLOB = "6ad5dfb8c654c2f965c5e25424a588a771e3c858"
FIRST_FIXED_RELEASE = "NOT_VERIFIED"
PROTOCOLS = ("2025-11-25", "2026-07-28")
CASES = (
    "valid_prompt",
    "unknown_prompt",
    "missing_required_argument",
    "prompt_execution_error",
)
MAX_TRANSCRIPT_BYTES = 16_384
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _request(case: str, request_id: int | str = 41) -> dict[str, Any]:
    """UCIE synthetic request, not copied or run from an upstream repository."""
    params: dict[str, Any]
    if case == "valid_prompt":
        params = {"name": "greet", "arguments": {"name": "Ada"}}
    elif case == "unknown_prompt":
        params = {"name": "unknown_prompt", "arguments": {}}
    elif case == "missing_required_argument":
        params = {"name": "greet", "arguments": {}}
    elif case == "prompt_execution_error":
        params = {"name": "explode", "arguments": {}}
    else:
        raise ValueError("unsupported UCIE prompt scenario")
    return {"jsonrpc": "2.0", "id": request_id, "method": "prompts/get", "params": params}


def _response(case: str, request_id: int | str = 41, *,
              before_fix: bool = False, protocol: str = "2025-11-25") -> dict[str, Any]:
    """Authored fixture for contract checks; NOT an SDK response capture."""
    base: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if case == "valid_prompt":
        base["result"] = {
            "messages": [{
                "role": "user",
                "content": {"type": "text", "text": "Hello, Ada"},
            }],
        }
        return base
    if case in ("unknown_prompt", "missing_required_argument"):
        code = INVALID_PARAMS
        if before_fix:
            code = 0 if protocol == "2025-11-25" else INTERNAL_ERROR
        base["error"] = {
            "code": code,
            "message": "Unknown prompt" if case == "unknown_prompt"
            else "Missing required arguments",
        }
        return base
    if case == "prompt_execution_error":
        # This case is a non-input control, not evidence that PR #3696 fixed it.
        base["error"] = {"code": INTERNAL_ERROR, "message": "Internal error"}
        return base
    raise ValueError("unsupported UCIE prompt scenario")


def _receipt(case: str, protocol: str, status: str, reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "case": case,
        "protocol_revision": protocol,
        "status": status,
        "reason": reason,
        "source_pr": SOURCE_PR,
        "upstream_merge_sha": UPSTREAM_MERGE_SHA,
        "sdk_executed": False,
        "independent_upstream_behavior_verified": False,
        "auto_promoted": False,
        "customer_release_authorized": False,
        "network_requests": 0,
        "persistent_writes": 0,
    }


def assess_transcript(value: Any) -> dict[str, Any]:
    """Assess one bounded JSON-RPC transcript using UCIE synthetic prompt names.

    Input shape: {"case", "protocol_revision", "request", "response"}.
    A successful result means only THIS transcript meets the selected wire
    contract, not that a named SDK/build/version was independently tested.
    Never reflect arbitrary response messages to avoid accidental disclosure.
    """
    generic = _receipt("UNSPECIFIED", "UNSPECIFIED",
                       "INPUT_REJECTED_NO_GO", "INVALID_TRANSCRIPT")
    if type(value) is not dict:
        return generic
    try:
        encoded = json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError, UnicodeError):
        return generic
    if len(encoded) > MAX_TRANSCRIPT_BYTES:
        return {**generic, "reason": "INPUT_TOO_LARGE"}
    case, protocol = value.get("case"), value.get("protocol_revision")
    if type(case) is not str or type(protocol) is not str:
        return generic
    if case not in CASES or protocol not in PROTOCOLS:
        return generic
    rejected = lambda why: _receipt(case, protocol, "INPUT_REJECTED_NO_GO", why)
    violation = lambda why: _receipt(case, protocol, "CONTRACT_VIOLATION", why)
    request, response = value.get("request"), value.get("response")
    if type(request) is not dict or type(response) is not dict:
        return rejected("REQUEST_OR_RESPONSE_NOT_OBJECT")
    request_id = request.get("id")
    if not ((type(request_id) is int and 0 <= request_id <= 2**53 - 1)
            or (type(request_id) is str and 1 <= len(request_id) <= 64)):
        return rejected("INVALID_REQUEST_ID")
    if request != _request(case, request_id):
        return rejected("REQUEST_NOT_UCIE_TEST_SCENARIO")
    if response.get("jsonrpc") != "2.0":
        return violation("INVALID_JSON_RPC_VERSION")
    if type(response.get("id")) is not type(request_id) or response.get("id") != request_id:
        return violation("REQUEST_RESPONSE_ID_MISMATCH")
    has_error, has_result = "error" in response, "result" in response
    if has_error == has_result:
        return violation("EXPECTED_EXACTLY_ONE_RESULT_OR_ERROR")
    if case == "valid_prompt":
        if has_error:
            return violation("VALID_PROMPT_REJECTED")
        expected = _response(case, request_id)["result"]
        if response["result"] != expected:
            return violation("UNEXPECTED_VALID_PROMPT_RESULT")
        return _receipt(case, protocol, "CONTRACT_MATCH",
                        "VALID_PROMPT_RESULT_MATCHES_FIXTURE")
    if not has_error or type(response["error"]) is not dict:
        return violation("EXPECTED_JSON_RPC_ERROR")
    code = response["error"].get("code")
    message = response["error"].get("message")
    if type(code) is not int or type(message) is not str or not (1 <= len(message) <= 512):
        return violation("MALFORMED_ERROR_ENVELOPE")
    if case in ("unknown_prompt", "missing_required_argument"):
        if code != INVALID_PARAMS:
            return violation("INPUT_FAILURE_MUST_BE_INVALID_PARAMS_MINUS_32602")
        return _receipt(case, protocol, "CONTRACT_MATCH", "INVALID_PARAMS_MATCHES_SPEC")
    # Differentiate prompt-function exceptions from invalid input; no actual
    # upstream runtime behavior is asserted for this informational control.
    if code == INVALID_PARAMS:
        return violation("PROMPT_EXECUTION_FAILURE_IS_NOT_INVALID_PARAMS")
    if code not in (0, INTERNAL_ERROR):
        return violation("UNEXPECTED_NON_INPUT_ERROR")
    return _receipt(case, protocol, "CONTROL_ONLY",
                    "INTERNAL_ERROR_CANONICAL" if code == INTERNAL_ERROR
                    else "LEGACY_NONCANONICAL_INTERNAL_ERROR")


def synthetic_demonstration() -> dict[str, Any]:
    """Use only hand-authored fixtures and expose this limit in the result."""
    results = []
    prior = []
    for protocol in PROTOCOLS:
        for case in CASES:
            results.append(assess_transcript({
                "case": case,
                "protocol_revision": protocol,
                "request": _request(case),
                "response": _response(case, protocol=protocol),
            }))
        for case in ("unknown_prompt", "missing_required_argument"):
            prior.append(assess_transcript({
                "case": case,
                "protocol_revision": protocol,
                "request": _request(case),
                "response": _response(case, before_fix=True, protocol=protocol),
            }))
    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_WIRE_CONTRACT_ONLY_NO_SDK_EXECUTION",
        "source_pr": SOURCE_PR,
        "source_spec": SOURCE_SPEC,
        "source_tag": PRE_FIX_TAG,
        "source_tag_commit": PRE_FIX_TAG_COMMIT,
        "source_merge_sha": UPSTREAM_MERGE_SHA,
        "first_fixed_release": FIRST_FIXED_RELEASE,
        "protocol_revisions": list(PROTOCOLS),
        "cases": len(results),
        "contract_matches": sum(x["status"] == "CONTRACT_MATCH" for x in results),
        "non_input_controls": sum(x["status"] == "CONTROL_ONLY" for x in results),
        "synthetic_pre_fix_violations_detected": sum(
            x["status"] == "CONTRACT_VIOLATION" for x in prior),
        "independent_sdk_regression": "NOT_EXECUTED",
        "per_revision_rights_approved": False,
        "auto_promoted": False,
        "customer_release_authorized": False,
        "network_requests": 0,
        "persistent_writes": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE offline MCP prompts/get wire checker")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true", help="Run UCIE-authored fixtures only")
    group.add_argument("--stdin", action="store_true", help="Read one bounded JSON transcript")
    args = parser.parse_args(argv)
    if args.demo:
        report = synthetic_demonstration()
        exit_code = 0
    else:
        data = sys.stdin.buffer.read(MAX_TRANSCRIPT_BYTES + 1)
        if len(data) > MAX_TRANSCRIPT_BYTES:
            report = _receipt("UNSPECIFIED", "UNSPECIFIED",
                              "INPUT_REJECTED_NO_GO", "INPUT_TOO_LARGE")
        else:
            try:
                obj = json.loads(data.decode("utf-8"))
            except (UnicodeError, ValueError):
                obj = None
            report = assess_transcript(obj)
        exit_code = 0 if report["status"] in ("CONTRACT_MATCH", "CONTROL_ONLY") else 2
    sys.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
