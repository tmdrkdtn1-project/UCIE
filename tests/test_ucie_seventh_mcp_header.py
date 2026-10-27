"""Offline synthetic regression for UCIE seventh public MCP candidate."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest

from ucie_miner.static_mcp_header import (
    MAX_SOURCE_BYTES, SeventhCandidateError, inspect_mcp_header_source,
)

def scan(schema: str) -> dict:
    return inspect_mcp_header_source(
        "from mcp.types import Tool\n"
        'tool = Tool(name="demo", input_schema=' + schema + ")\n"
    )

def reasons(output: dict) -> set[str]:
    return {f["reason"] for f in output["candidates"]}


class SeventhMcpHeaderTests(unittest.TestCase):
    def test_valid_primitive_headers_not_a_safety_pass(self):
        r = scan('{"type":"object","properties":{'
                 '"a":{"type":"string","x-mcp-header":"Region"},'
                 '"b":{"type":"integer","x-mcp-header":"Copies"},'
                 '"c":{"type":"boolean","x-mcp-header":"Dry-Run"}}}')
        self.assertEqual(r["candidate_count"], 0)
        self.assertEqual(r["status"], "NO_MATCH_NOT_A_SAFETY_PASS")

    def test_array_is_invalid(self):
        r = scan('{"properties":{"tags":{"type":"array","x-mcp-header":"Tags"}}}')
        self.assertIn("HEADER_NOT_STRING_INTEGER_BOOLEAN_PROPERTY", reasons(r))

    def test_number_is_invalid(self):
        r = scan('{"properties":{"ratio":{"type":"number","x-mcp-header":"Ratio"}}}')
        self.assertIn("HEADER_NOT_STRING_INTEGER_BOOLEAN_PROPERTY", reasons(r))

    def test_optional_union_schema_is_invalid(self):
        r = scan('{"properties":{"region":{"anyOf":[{"type":"string"},{"type":"null"}],'
                 '"x-mcp-header":"Region"}}}')
        self.assertIn("HEADER_NOT_STRING_INTEGER_BOOLEAN_PROPERTY", reasons(r))

    def test_invalid_token_and_nonstring(self):
        r = scan('{"properties":{"a":{"type":"string","x-mcp-header":"Region Name"},'
                 '"b":{"type":"string","x-mcp-header":7}}}')
        self.assertEqual(reasons(r), {"HEADER_NAME_NOT_RFC9110_TOKEN", "HEADER_NAME_NOT_STRING"})

    def test_case_insensitive_collision(self):
        r = scan('{"properties":{"a":{"type":"string","x-mcp-header":"Region"},'
                 '"b":{"type":"string","x-mcp-header":"region"}}}')
        self.assertIn("CASE_INSENSITIVE_HEADER_NAME_DUPLICATE", reasons(r))

    def test_root_and_composition_location(self):
        r = scan('{"x-mcp-header":"Root","type":"object","allOf":['
                 '{"properties":{"a":{"type":"string","x-mcp-header":"A"}}}]}')
        self.assertIn("HEADER_OUTSIDE_PURE_PROPERTIES_CHAIN", reasons(r))

    def test_nested_pure_properties_valid(self):
        r = scan('{"properties":{"parent":{"type":"object","properties":'
                 '{"region":{"type":"string","x-mcp-header":"Region"}}}}}')
        self.assertEqual(r["candidate_count"], 0)

    def test_dynamic_schema_review_not_safety_pass(self):
        r = inspect_mcp_header_source('Tool(name="dyn", input_schema=make_schema())')
        self.assertEqual(r["status"], "STATIC_SCHEMA_REVIEW_REQUIRED")
        self.assertEqual(r["unresolved_dynamic_schemas"], 1)

    def test_unrelated_dict_ignored(self):
        r = inspect_mcp_header_source('x = {"x-mcp-header":"Bad Header"}')
        self.assertEqual(r["low_level_tool_calls_inspected"], 0)
        self.assertEqual(r["candidate_count"], 0)

    def test_malformed_and_oversized_fail_closed(self):
        for source in ("", "def broken(", "x" * (MAX_SOURCE_BYTES + 1)):
            with self.subTest(length=len(source)):
                with self.assertRaises(SeventhCandidateError):
                    inspect_mcp_header_source(source)

    def test_no_execution_of_source(self):
        r = inspect_mcp_header_source(
            'raise RuntimeError("should never execute")\n'
            'Tool(name="demo",input_schema={"properties":'
            '{"r":{"type":"float","x-mcp-header":"R"}}})'
        )
        self.assertEqual(r["candidate_count"], 1)
        self.assertFalse(r["source_executed"])
        self.assertFalse(r["auto_promoted"])
        self.assertFalse(r["owner_signed"])

    def test_cli_inert(self):
        source = 'Tool(name="x",input_schema={"properties":{"x":' \
                 '{"type":"array","x-mcp-header":"A"}}})'
        p = subprocess.run(
            [sys.executable, "-B", "-m", "ucie_miner.static_mcp_header"],
            input=source.encode(), capture_output=True, timeout=12, check=False)
        self.assertEqual(p.returncode, 0, p.stderr.decode(errors="replace")[:200])
        r = json.loads(p.stdout)
        self.assertEqual(r["candidate_count"], 1)
        self.assertEqual(r["external_requests"], 0)


if __name__ == "__main__":
    unittest.main()
