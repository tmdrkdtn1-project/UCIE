"""UCIE-only MCP prompts/get wire contract regressions; no upstream SDK execution."""
from __future__ import annotations

import contextlib
import io
import json
import unittest
from unittest.mock import patch

from ucie_miner import mcp_prompt_regression_v01 as m


class MCPPromptGetWireRegressionTests(unittest.TestCase):
    def receipt(self, case: str, protocol: str = "2025-11-25", *,
                before: bool = False, request_id: int | str = 41):
        return m.assess_transcript({
            "case": case,
            "protocol_revision": protocol,
            "request": m._request(case, request_id),
            "response": m._response(
                case, request_id, before_fix=before, protocol=protocol),
        })

    def test_both_protocol_revisions_correct_unknown_and_missing_errors(self):
        for protocol in m.PROTOCOLS:
            for case in ("unknown_prompt", "missing_required_argument"):
                with self.subTest(protocol=protocol, case=case):
                    self.assertEqual(self.receipt(case, protocol)["status"], "CONTRACT_MATCH")

    def test_both_protocol_revisions_reject_tagged_pre_fix_error_codes(self):
        for protocol in m.PROTOCOLS:
            for case in ("unknown_prompt", "missing_required_argument"):
                with self.subTest(protocol=protocol, case=case):
                    report = self.receipt(case, protocol, before=True)
                    self.assertEqual(report["status"], "CONTRACT_VIOLATION")
                    self.assertEqual(
                        report["reason"], "INPUT_FAILURE_MUST_BE_INVALID_PARAMS_MINUS_32602")

    def test_valid_prompt_succeeds_with_original_request_id(self):
        for protocol in m.PROTOCOLS:
            with self.subTest(protocol=protocol):
                report = self.receipt("valid_prompt", protocol, request_id="mcp-7")
                self.assertEqual(report["status"], "CONTRACT_MATCH")
                self.assertFalse(report["sdk_executed"])

    def test_prompt_exception_is_control_not_fixed_by_pr(self):
        for protocol in m.PROTOCOLS:
            with self.subTest(protocol=protocol):
                self.assertEqual(
                    self.receipt("prompt_execution_error", protocol)["status"],
                    "CONTROL_ONLY")
        payload = {
            "case": "prompt_execution_error", "protocol_revision": "2025-11-25",
            "request": m._request("prompt_execution_error"),
            "response": m._response("prompt_execution_error"),
        }
        payload["response"]["error"]["code"] = 0
        out = m.assess_transcript(payload)
        self.assertEqual(out["status"], "CONTROL_ONLY")
        self.assertEqual(out["reason"], "LEGACY_NONCANONICAL_INTERNAL_ERROR")
        payload["response"]["error"]["code"] = -32602
        self.assertEqual(m.assess_transcript(payload)["status"], "CONTRACT_VIOLATION")

    def test_no_false_pass_for_missing_or_mismatched_json_rpc_id(self):
        for invalid_id in (None, 40, True, "41"):
            with self.subTest(invalid_id=invalid_id):
                payload = {
                    "case": "unknown_prompt", "protocol_revision": "2026-07-28",
                    "request": m._request("unknown_prompt"),
                    "response": m._response("unknown_prompt"),
                }
                payload["response"]["id"] = invalid_id
                self.assertEqual(m.assess_transcript(payload)["status"], "CONTRACT_VIOLATION")

    def test_both_result_and_error_is_violation(self):
        payload = {
            "case": "valid_prompt", "protocol_revision": "2026-07-28",
            "request": m._request("valid_prompt"),
            "response": m._response("valid_prompt"),
        }
        payload["response"]["error"] = {"code": -32603, "message": "broken"}
        self.assertEqual(m.assess_transcript(payload)["status"], "CONTRACT_VIOLATION")
        del payload["response"]["error"]
        del payload["response"]["result"]
        self.assertEqual(m.assess_transcript(payload)["status"], "CONTRACT_VIOLATION")

    def test_valid_prompt_cannot_be_approved_by_an_error(self):
        payload = {
            "case": "valid_prompt", "protocol_revision": "2025-11-25",
            "request": m._request("valid_prompt"),
            "response": m._response("unknown_prompt"),
        }
        self.assertEqual(m.assess_transcript(payload)["status"], "CONTRACT_VIOLATION")

    def test_bad_request_and_protocol_fail_closed(self):
        payload = {
            "case": "unknown_prompt", "protocol_revision": "2026-07-28",
            "request": m._request("unknown_prompt"),
            "response": m._response("unknown_prompt"),
        }
        for change in (
            {"case": "external_project"},
            {"protocol_revision": "2099-01-01"},
            {"request": {"method": "rm", "id": 41}},
            {"request": {**payload["request"], "id": True}},
            {"request": {**payload["request"], "params": {"name": "untrusted"}}},
            {"request": {**payload["request"], "params": {"name": "unknown_prompt", "arguments": {"injection": "go"}}}},
        ):
            with self.subTest(change=change):
                item = dict(payload)
                item.update(change)
                self.assertEqual(
                    m.assess_transcript(item)["status"], "INPUT_REJECTED_NO_GO")

    def test_error_type_message_and_structure_are_bounded(self):
        payload = {
            "case": "missing_required_argument",
            "protocol_revision": "2025-11-25",
            "request": m._request("missing_required_argument"),
            "response": m._response("missing_required_argument"),
        }
        for wrong_code in (True, "-32602", None):
            with self.subTest(wrong_code=wrong_code):
                item = {**payload, "response": {
                    **payload["response"], "error": {
                        "code": wrong_code, "message": "message",
                    },
                }}
                self.assertEqual(
                    m.assess_transcript(item)["status"], "CONTRACT_VIOLATION")
        item = {**payload, "response": {
            **payload["response"], "error": {"code": -32602, "message": "x" * 1000},
        }}
        self.assertEqual(m.assess_transcript(item)["status"], "CONTRACT_VIOLATION")
        item["response"]["error"]["message"] = "SENSITIVE_FIXTURE_SECRET"
        self.assertNotIn("SENSITIVE_FIXTURE_SECRET", json.dumps(m.assess_transcript(item)))

    def test_reject_non_json_oversize_and_recursive_values(self):
        self.assertEqual(m.assess_transcript(None)["status"], "INPUT_REJECTED_NO_GO")
        self.assertEqual(m.assess_transcript({"value": "X" * 17000})["reason"], "INPUT_TOO_LARGE")
        self.assertEqual(m.assess_transcript({"value": object()})["status"],
                         "INPUT_REJECTED_NO_GO")
        self.assertEqual(m.assess_transcript({"value": float("nan")})["status"],
                         "INPUT_REJECTED_NO_GO")

    def test_demo_counts_are_transcript_fixtures_not_sdk_qa(self):
        out = m.synthetic_demonstration()
        self.assertEqual(out["status"], "SYNTHETIC_WIRE_CONTRACT_ONLY_NO_SDK_EXECUTION")
        self.assertEqual(out["cases"], 8)
        self.assertEqual(out["contract_matches"], 6)
        self.assertEqual(out["non_input_controls"], 2)
        self.assertEqual(out["synthetic_pre_fix_violations_detected"], 4)
        self.assertEqual(out["first_fixed_release"], "NOT_VERIFIED")
        self.assertEqual(out["independent_sdk_regression"], "NOT_EXECUTED")
        self.assertIs(out["customer_release_authorized"], False)
        self.assertIs(out["auto_promoted"], False)
        self.assertEqual(out["network_requests"], 0)
        self.assertEqual(out["persistent_writes"], 0)

    def test_cli_demo_prints_only_local_json(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = m.main(["--demo"])
        self.assertEqual(code, 0)
        out = json.loads(buffer.getvalue())
        self.assertEqual(out["source_merge_sha"], m.UPSTREAM_MERGE_SHA)
        self.assertEqual(out["contract_matches"], 6)

    def test_cli_stdin_pass_and_violation_exit_codes(self):
        for before, expected_exit in ((False, 0), (True, 2)):
            item = {
                "case": "unknown_prompt", "protocol_revision": "2025-11-25",
                "request": m._request("unknown_prompt"),
                "response": m._response(
                    "unknown_prompt", before_fix=before, protocol="2025-11-25"),
            }
            stdin = io.TextIOWrapper(
                io.BytesIO(json.dumps(item).encode("utf-8")), encoding="utf-8")
            out = io.StringIO()
            with patch("sys.stdin", stdin), contextlib.redirect_stdout(out):
                self.assertEqual(m.main(["--stdin"]), expected_exit)
            self.assertEqual(
                json.loads(out.getvalue())["status"],
                "CONTRACT_MATCH" if not before else "CONTRACT_VIOLATION")


if __name__ == "__main__":
    unittest.main()
