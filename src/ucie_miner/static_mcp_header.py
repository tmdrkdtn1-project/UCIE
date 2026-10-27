"""Inert seventh UCIE candidate: unsafe MCP low-level x-mcp-header schemas.

Public evidence: modelcontextprotocol/python-sdk PR #3620 (MIT).
Only parses caller-provided source. Never imports or executes that source.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys

RULE_ID = "MCP_LOW_LEVEL_X_MCP_HEADER_SCHEMA"
UPSTREAM = "https://github.com/modelcontextprotocol/python-sdk/pull/3620"
UPSTREAM_MERGE = "3d0c40d8aafb37304635d75dbcafc2379b38b975"
MAX_SOURCE_BYTES = 131072
MAX_AST_NODES = 20000
MAX_SCHEMA_POSITIONS = 1024
MAX_SCHEMA_DEPTH = 32
MAX_FINDINGS = 20
_TOKEN = re.compile(r"[!#$%&'*+.^_\x60|~0-9A-Za-z-]+\Z", re.ASCII)
_ALLOWED = frozenset(("string", "integer", "boolean"))
_SINGLE = ("items", "additionalProperties", "not", "if", "then", "else", "contains", "propertyNames")
_ARRAYS = ("allOf", "anyOf", "oneOf", "prefixItems")
_MAPS = ("$defs", "definitions", "patternProperties")


class SeventhCandidateError(ValueError):
    pass


def _tool_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (isinstance(func, ast.Name) and func.id == "Tool") or (
        isinstance(func, ast.Attribute) and func.attr == "Tool"
    )


def _walk_schema(schema: object):
    """Yield annotated schema positions and whether each has a pure properties path."""
    pending = [(schema, (), True, 0)]
    seen = 0
    while pending:
        obj, path, reachable, depth = pending.pop()
        seen += 1
        if seen > MAX_SCHEMA_POSITIONS or depth > MAX_SCHEMA_DEPTH:
            raise SeventhCandidateError("schema traversal limit exceeded")
        if not isinstance(obj, dict):
            continue
        if "x-mcp-header" in obj:
            yield path, reachable, obj
        props = obj.get("properties")
        if isinstance(props, dict):
            for name, child in props.items():
                key = name if isinstance(name, str) and len(name) <= 80 else "<nonliteral-property>"
                pending.append((child, (*path, key), reachable, depth + 1))
        for key in _SINGLE:
            if key in obj:
                pending.append((obj[key], (*path, key), False, depth + 1))
        for key in _ARRAYS:
            value = obj.get(key)
            if isinstance(value, list):
                for idx, child in enumerate(value):
                    pending.append((child, (*path, f"{key}[{idx}]"), False, depth + 1))
        for key in _MAPS:
            value = obj.get(key)
            if isinstance(value, dict):
                for name, child in value.items():
                    ident = name if isinstance(name, str) and len(name) <= 80 else "<nonliteral-key>"
                    pending.append((child, (*path, key, ident), False, depth + 1))


def inspect_mcp_header_source(source: str) -> dict:
    """Find literal low-level Tool(input_schema=...) issues; not a runtime verdict."""
    if type(source) is not str:
        raise SeventhCandidateError("expected inert Python text")
    raw = source.encode("utf-8", "surrogatepass")
    if not raw or len(raw) > MAX_SOURCE_BYTES:
        raise SeventhCandidateError("empty or oversized source")
    try:
        tree = ast.parse(source, filename="<ucie-mcp-header-inert>")
        nodes = list(ast.walk(tree))
    except (SyntaxError, MemoryError, RecursionError, ValueError) as exc:
        raise SeventhCandidateError("invalid source or syntax") from exc
    if len(nodes) > MAX_AST_NODES:
        raise SeventhCandidateError("AST node limit exceeded")
    findings: list[dict] = []
    unresolved = 0
    inspected = 0
    for node in nodes:
        if not _tool_call(node):
            continue
        schema_kw = next((k for k in node.keywords if k.arg == "input_schema"), None)
        if schema_kw is None:
            continue
        inspected += 1
        try:
            schema = ast.literal_eval(schema_kw.value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError, OverflowError):
            unresolved += 1
            continue
        if not isinstance(schema, dict):
            unresolved += 1
            continue
        tool_kw = next((k for k in node.keywords if k.arg == "name"), None)
        tool = (tool_kw.value.value if tool_kw is not None
                and isinstance(tool_kw.value, ast.Constant)
                and isinstance(tool_kw.value.value, str)
                and len(tool_kw.value.value) <= 80 else "<dynamic>")
        header_names: dict[str, str] = {}
        try:
            for path, reachable, entry in _walk_schema(schema):
                prop = ".".join(path) if path else "<root>"
                header = entry["x-mcp-header"]
                if not path or not reachable:
                    reason = "HEADER_OUTSIDE_PURE_PROPERTIES_CHAIN"
                elif not isinstance(header, str):
                    reason = "HEADER_NAME_NOT_STRING"
                elif _TOKEN.fullmatch(header) is None:
                    reason = "HEADER_NAME_NOT_RFC9110_TOKEN"
                elif not isinstance(entry.get("type"), str) or entry["type"] not in _ALLOWED:
                    reason = "HEADER_NOT_STRING_INTEGER_BOOLEAN_PROPERTY"
                elif header.lower() in header_names:
                    reason = "CASE_INSENSITIVE_HEADER_NAME_DUPLICATE"
                else:
                    header_names[header.lower()] = prop
                    continue
                findings.append({
                    "rule_id": RULE_ID,
                    "line": node.lineno,
                    "column": node.col_offset,
                    "tool": tool,
                    "schema_path": prop,
                    "reason": reason,
                    "manual_review_required": True,
                    "actual_client_rejection_verified": False,
                })
                if len(findings) > MAX_FINDINGS:
                    raise SeventhCandidateError("finding limit exceeded")
        except RecursionError as exc:
            raise SeventhCandidateError("schema recursion limit") from exc
    findings.sort(key=lambda r: (r["line"], r["column"], r["schema_path"], r["reason"]))
    status = ("STATIC_CANDIDATE_REVIEW_REQUIRED" if findings else
              "STATIC_SCHEMA_REVIEW_REQUIRED" if unresolved else
              "NO_MATCH_NOT_A_SAFETY_PASS")
    return {
        "schema": "UCIE_SEVENTH_MCP_LOW_LEVEL_HEADER_STATIC_V1",
        "status": status, "rule_id": RULE_ID,
        "public_evidence": UPSTREAM, "upstream_merge": UPSTREAM_MERGE,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "low_level_tool_calls_inspected": inspected,
        "unresolved_dynamic_schemas": unresolved,
        "candidate_count": len(findings), "candidates": findings,
        "source_executed": False, "source_files_read": 0,
        "external_requests": 0, "persistent_writes": 0,
        "auto_fix": False, "auto_promoted": False, "owner_signed": False,
        "independent_qa_verified": False,
        "sdk_runtime_compatibility_verified": False,
    }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_SOURCE_BYTES + 1)
    try:
        if not raw or len(raw) > MAX_SOURCE_BYTES:
            raise SeventhCandidateError("stdin outside limits")
        result = inspect_mcp_header_source(raw.decode("utf-8-sig", "strict"))
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except (SeventhCandidateError, UnicodeError) as exc:
        print(json.dumps({
            "status": "FAIL_CLOSED", "reason": type(exc).__name__,
            "source_executed": False, "auto_promoted": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
