"""Focused offline regression for MCP empty _meta compatibility candidate.

Only UCIE-written snippets and standard-library AST/JSON. No upstream
source execution, real MCP server, account data, external network or signing.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest

from ucie_miner.static_mcp_empty_meta import (
    EVIDENCE, MAX_SOURCE_BYTES, RULE_ID, SourceRejected,
    inspect_mcp_empty_meta_source,
)

# Shape pinned to approved modelcontextprotocol/python-sdk PR #3628,
# before parent cdf7d332d7f417ed7199fea303a17426d4dc4d07.
BEFORE = """\
async def send_raw_request(self, method, params, opts):
    out_params = dict(params) if params is not None else {}
    out_meta = dict(out_params.get("_meta") or {})
    on_progress = opts.get("on_progress")
    if on_progress is not None:
        out_meta["progressToken"] = 1
    out_params["_meta"] = out_meta
    with otel_span("outbound"):
        inject_trace_context(out_meta)
        msg = JSONRPCRequest(jsonrpc="2.0", id=1, method=method, params=out_params)
    return msg
"""

# Shape of official merged 0b2fd3ea60efb16b349e8c887cf91bf2f9f773fc.
AFTER = """\
async def send_raw_request(self, method, params, opts):
    out_params = dict(params) if params is not None else {}
    out_meta = dict(out_params.get("_meta") or {})
    on_progress = opts.get("on_progress")
    if on_progress is not None:
        out_meta["progressToken"] = 1
    with otel_span("outbound"):
        inject_trace_context(out_meta)
        if out_meta:
            out_params["_meta"] = out_meta
        else:
            out_params.pop("_meta", None)
        if out_params:
            msg = JSONRPCRequest(jsonrpc="2.0", id=1, method=method, params=out_params)
        else:
            msg = JSONRPCRequest(jsonrpc="2.0", id=1, method=method)
    return msg
"""


class SixthMCPEmptyMetaTests(unittest.TestCase):
    def test_approved_upstream_before_candidate(self):
        found = inspect_mcp_empty_meta_source(BEFORE)
        self.assertEqual(found["candidate_count"], 1)
        self.assertEqual(found["rule_id"], RULE_ID)
        self.assertEqual(found["status"], "STATIC_CANDIDATES_FOR_MANUAL_REVIEW")
        self.assertEqual(found["candidates"][0]["public_evidence"], EVIDENCE)
        self.assertTrue(found["candidates"][0]["manual_review_required"])
        self.assertFalse(found["candidates"][0]["runtime_bug_confirmed_for_input"])
        self.assertFalse(found["owner_signed"])
        self.assertFalse(found["auto_fix"])

    def test_approved_upstream_after_no_pattern_not_safety_pass(self):
        fixed = inspect_mcp_empty_meta_source(AFTER)
        self.assertEqual(fixed["candidate_count"], 0)
        self.assertEqual(fixed["status"], "NO_MATCH_NOT_A_SAFETY_PASS")
        self.assertFalse(fixed["released_sdk_version_fix_verified"])

    def test_explicit_guard_preserves_progress_metadata(self):
        guarded = BEFORE.replace(
            '    out_params["_meta"] = out_meta',
            '    if out_meta:\n        out_params["_meta"] = out_meta',
        )
        self.assertEqual(inspect_mcp_empty_meta_source(
            guarded)["candidate_count"], 0)
        # The source-only detector does not run progress handlers.
        self.assertIn('out_meta["progressToken"] = 1', guarded)

    def test_unrelated_meta_and_nested_builder_not_misattributed(self):
        unused = BEFORE.replace(
            "msg = JSONRPCRequest(", "msg = NotAnOutboundRequest(")
        self.assertEqual(inspect_mcp_empty_meta_source(
            unused)["candidate_count"], 0)
        nested = """\
async def send_raw_request(self, method):
    out_meta = {}
    out_params = {}
    out_params["_meta"] = out_meta
    def another_scope():
        return JSONRPCRequest(jsonrpc="2.0", id=1, method=method, params=out_params)
"""
        self.assertEqual(inspect_mcp_empty_meta_source(
            nested)["candidate_count"], 0)

    def test_plain_dictionary_empty_meta_candidate_and_no_forged_pass(self):
        example = """\
def send(method):
    out_meta = {}
    out_params = {}
    out_params["_meta"] = out_meta
    request = JSONRPCRequest(jsonrpc="2.0", id=1, method=method, params=out_params)
    return request
"""
        output = inspect_mcp_empty_meta_source(example)
        self.assertEqual(output["candidate_count"], 1)
        self.assertFalse(output["source_executed"])
        self.assertFalse(output["auto_promoted"])
        self.assertEqual(output["source_files_read"], 0)

    def test_controlled_json_wire_difference_not_real_sdk_execution(self):
        # Pure standard-library fixture illustrates optional params behavior;
        # not a claim of executing the original SDK or a legacy MCP peer.
        old = {"jsonrpc": "2.0", "id": 1, "method": "ping",
               "params": {"_meta": {}}}
        new = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        self.assertIn('"_meta": {}', json.dumps(old))
        self.assertNotIn('"params"', json.dumps(new))

    def test_fail_closed_size_syntax_and_inert_stdin(self):
        for text in ("", "def invalid(:", "x" * (MAX_SOURCE_BYTES + 1)):
            with self.subTest(size=len(text)), self.assertRaises(SourceRejected):
                inspect_mcp_empty_meta_source(text)
        with self.assertRaises(SourceRejected):
            inspect_mcp_empty_meta_source(None)
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "ucie_miner.static_mcp_empty_meta"],
            input=BEFORE.encode("utf-8"), capture_output=True, timeout=15,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[:400])
        result = json.loads(proc.stdout)
        self.assertEqual(result["candidate_count"], 1)
        self.assertFalse(result["owner_signed"])
        self.assertFalse(result["source_executed"])


if __name__ == "__main__":
    unittest.main()
