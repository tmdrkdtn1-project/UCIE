"""Standalone UCIE-authored ZIP draft CLI, NOT an approved release.

This module is archived as __main__.py with portable_exact.py. It can run
with python -I -B draft.zip without any installed UCIE dependency. Inputs
are exclusively sanitized public unverified metadata, never source programs.
"""
from __future__ import annotations

import json
import sys
from portable_exact import (
    search_public_metadata, PortableLookupError, VERSION,
)

MAX_INPUT_BYTES = 32768
CLI_SCHEMA = "UCIE_STANDALONE_DRAFT_PUBLIC_METADATA_CLI_V1"


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _bad_constant(value):
    raise ValueError("nonfinite JSON number rejected")


def execute(payload):
    if (type(payload) is not dict
            or set(payload) != {"items", "queries", "limit"}
            or type(payload["items"]) is not list
            or type(payload["queries"]) is not list
            or type(payload["limit"]) is not int
            or not 1 <= len(payload["queries"]) <= 32
            or any(type(q) is not list or len(q) != 4
                   or any(type(x) is not str for x in q)
                   for q in payload["queries"])):
        raise ValueError("strict portable public metadata input required")
    result = search_public_metadata(
        payload["items"], queries=tuple(tuple(q) for q in payload["queries"]),
        limit=payload["limit"],
    )
    if (result.get("approved_or_exportable_items") != 0
            or result.get("production_release_approved") is not False
            or result.get("network_requests") != 0
            or result.get("database_writes") != 0
            or result.get("original_upstream_code_executed") is not False):
        raise ValueError("portable engine trust boundary changed")
    return {
        "schema": CLI_SCHEMA,
        "status": "UNVERIFIED_PUBLIC_METADATA_QUERY_DRAFT_NOT_RELEASED",
        "engine_version": VERSION,
        "result": result,
        "owner_release_approved": False,
        "new_public_candidate_approvals": 0,
        "third_party_code_executed": False,
        "network_requests": 0,
        "database_writes": 0,
        "package_released": False,
    }


def main():
    try:
        if len(sys.argv) != 1:
            raise ValueError("no command line paths or flags allowed")
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if not raw or len(raw) > MAX_INPUT_BYTES:
            raise ValueError("bounded public metadata JSON stdin required")
        payload = json.loads(raw.decode("utf-8-sig"),
                             object_pairs_hook=_unique_pairs,
                             parse_constant=_bad_constant)
        output = execute(payload)
    except (ValueError, UnicodeError, TypeError, KeyError,
            PortableLookupError, OverflowError):
        output = {
            "schema": CLI_SCHEMA, "status": "STANDALONE_DRAFT_FAIL_CLOSED",
            "owner_release_approved": False,
            "new_public_candidate_approvals": 0,
            "third_party_code_executed": False,
            "network_requests": 0, "database_writes": 0,
            "package_released": False,
        }
        print(json.dumps(output, sort_keys=True, ensure_ascii=True))
        return 2
    print(json.dumps(output, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
