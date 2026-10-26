"""UCIE sixth public candidate tests based on approved MCP Python SDK PR #3628.

Only UCIE-authored synthetic snippets are parsed. No SDK import, wire
transport, network requests, foreign code execution, signing or promotion.
"""
from __future__ import annotations
import json
import subprocess
import sys
import unittest

from ucie_miner.static_mcp_empty_meta import (
    MAX_SOURCE_BYTES, RULE_ID, SixthCandidateError,
    inspect_mcp_empty_meta_source,
)

PRE = """\
class JSONRPCDispatcher:
    async def send_raw_request(self, method, params, opts):
        out_params = dict(params or {})
        out_meta = dict(out_params.pop("_meta", {}) or {})
        on_progress = opts.get("on_progress")
        if on_progress is not None:
            out_meta["progressToken"] = 17
        out_params["_meta"] = out_meta
        inject_trace_context(out_meta)
        msg = JSONRPCRequest(jsonrpc="2.0", id=17, method=method, params=out_params)
        return msg
"""

POST = """\
class JSONRPCDispatcher:
    async def send_raw_request(self, method, params, opts):
        out_params = dict(params or {})
        out_meta = dict(out_params.pop("_meta", {}) or {})
        inject_trace_context(out_meta)
        if out_meta:
            out_params["_meta"] = out_meta
        else:
            out_params.pop("_meta", None)
        if out_params:
            msg = JSONRPCRequest(jsonrpc="2.0", id=17, method=method, params=out_params)
        else:
            msg = JSONRPCRequest(jsonrpc="2.0", id=17, method=method)
        return msg
"""


class SixthMcpEmptyMetaTests(unittest.TestCase):
    def test_approved_upstream_prefixed_unsafe_pattern(self):
        r = inspect_mcp_empty_meta_source(PRE)
        self.assertEqual(r["status"], "STATIC_CANDIDATE_REVIEW_REQUIRED")
        self.assertEqual(r["candidate_count"], 1)
        self.assertEqual(r["candidates"][0]["rule_id"], RULE_ID)
        self.assertTrue(r["candidates"][0]["manual_review_required"])
        self.assertFalse(r["candidates"][0]["legacy_peer_failure_confirmed_for_this_input"])
        self.assertFalse(r["auto_promoted"])
        self.assertFalse(r["owner_signed"])
        self.assertFalse(r["source_executed"])

    def test_upstream_fixed_shape_no_match(self):
        r = inspect_mcp_empty_meta_source(POST)
        self.assertEqual(r["candidate_count"], 0)
        self.assertEqual(r["status"], "NO_MATCH_NOT_A_SAFETY_PASS")

    def test_false_guard_must_not_suppress(self):
        src = PRE.replace(
            'out_params["_meta"] = out_meta',
            'if not out_meta:\n            out_params["_meta"] = out_meta',
        )
        r = inspect_mcp_empty_meta_source(src)
        self.assertEqual(r["candidate_count"], 1)

    def test_different_sink_or_unrelated_function_no_match(self):
        src = PRE.replace("JSONRPCRequest(", "SomeOtherRequest(")
        self.assertEqual(inspect_mcp_empty_meta_source(src)["candidate_count"], 0)
        src = PRE.replace("send_raw_request", "unrelated_method")
        self.assertEqual(inspect_mcp_empty_meta_source(src)["candidate_count"], 0)

    def test_nested_function_cannot_supply_request_sink(self):
        src = """\
async def send_raw_request():
    out_params = {}
    out_meta = {}
    out_params["_meta"] = out_meta
    def inner():
        return JSONRPCRequest(params=out_params)
"""
        self.assertEqual(inspect_mcp_empty_meta_source(src)["candidate_count"], 0)

    def test_legacy_wire_compatibility_without_running_sdk(self):
        # These plain Python dicts describe exactly the official PR's wire
        # regression. They are not an actual server/network compatibility test.
        wire_before = {"jsonrpc": "2.0", "id": 2, "method": "ping",
                       "params": {"_meta": {}}}
        wire_after = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
        self.assertIn('"_meta": {}', json.dumps(wire_before))
        self.assertNotIn('"params"', json.dumps(wire_after))

    def test_invalid_source_fails_closed(self):
        for candidate in ("", "def broken(:\n", "x" * (MAX_SOURCE_BYTES + 1)):
            with self.subTest(size=len(candidate)), self.assertRaises(SixthCandidateError):
                inspect_mcp_empty_meta_source(candidate)
        with self.assertRaises(SixthCandidateError):
            inspect_mcp_empty_meta_source(None)

    def test_cli_inert_stdin(self):
        p = subprocess.run(
            [sys.executable, "-B", "-m", "ucie_miner.static_mcp_empty_meta"],
            input=PRE.encode("utf-8"), capture_output=True,
            timeout=12, check=False)
        self.assertEqual(p.returncode, 0, p.stderr[:500].decode(errors="replace"))
        result = json.loads(p.stdout)
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["source_files_read"], 0)
        self.assertEqual(result["external_requests"], 0)
        self.assertFalse(result["owner_signed"])
        self.assertFalse(result["source_executed"])


if __name__ == "__main__":
    unittest.main()
