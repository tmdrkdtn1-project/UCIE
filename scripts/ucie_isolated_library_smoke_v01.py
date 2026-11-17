"""UCIE first-party code-only relocation smoke under an isolated UCIE_PROJECT/UCIE.

This tool is NOT the live owner cutover program. It never stages or moves
files, starts MCP/Task services, accesses runtime SQLite, calls public GET,
or approves a customer Rulepack. It needs an already prepared code-only stage.
Run with Python -I -B to avoid inherited PYTHONPATH and __pycache__ writes.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from unittest.mock import patch

SCHEMA = "UCIE_CODE_ONLY_RELOCATED_SEARCH_SMOKE_V01"
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
KEY = ("repo:modelcontextprotocol/python-sdk", "MCP/API",
       "PUBLIC_TECHNICAL_EVIDENCE", "EXCEPTION_HANDLING")
ROWS = 27


def _indirect(p: Path) -> bool:
    j = getattr(p, "is_junction", None)
    return p.is_symlink() or (j is not None and j())


def _stage_root() -> Path:
    raw = Path(__file__).absolute().parent.parent
    # The files themselves must be first-party standalone source, not
    # a symlink/junction from a potentially live UCIE tree.
    if (_indirect(Path(__file__)) or _indirect(raw)
            or _indirect(raw.parent) or _indirect(raw / "src")
            or raw.name.casefold() != "ucie"
            or raw.parent.name.casefold() != "ucie_project"
            or not raw.is_dir() or not (raw / "src").is_dir()):
        raise ValueError("direct UCIE_PROJECT/UCIE code-only stage required")
    for name in (".git", ".venv", "runtime", ".ucie_bridge_state"):
        path = raw / name
        if path.exists() or _indirect(path):
            raise ValueError("operating repository/data/bridge path in code-only stage")
    for path in (raw / "src" / "ucie_miner",
                 raw / "src" / "ucie_public",
                 raw / "src" / "ucie_miner" / "library_exact_index.py"):
        if _indirect(path) or not path.exists():
            raise ValueError("source package indirect or missing")
    return raw


def _synthetic_handoff() -> dict:
    """UCIE-authored review-only rows; not retrieved external metadata."""
    tasks = []
    for i in range(ROWS):
        tasks.append({
            "candidate_id_sha256":
                sha256(f"UCIE_RELOCATED_CANDIDATE_{i}".encode("ascii")).hexdigest(),
            "source": "modelcontextprotocol/python-sdk",
            "reference": "pr:3696:" + "a" * 40,
            "skill_id": "mcp-api-compatibility",
            "pattern_code": "EXCEPTION_HANDLING",
            "evidence_sha256":
                sha256(f"UCIE_RELOCATED_REVISION_{i}".encode("ascii")).hexdigest(),
            "stage6_candidate": None,
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "approval": False,
            "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
        })
    return {
        "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
        "status": "LINKED_UNVERIFIED_NO_GO",
        "source_revisions": ROWS,
        "linked_revisions": ROWS,
        "pending_source_revisions": 0,
        "tasks": tasks,
        "auto_promoted": False,
        "production_approved": False,
        "deploy_allowed": False,
    }


def run_smoke(expected_source_sha256: str) -> dict:
    if type(expected_source_sha256) is not str or HEX64.fullmatch(
            expected_source_sha256) is None:
        raise ValueError("immutable first-party source SHA256 lease required")
    root = _stage_root()
    exact_source = root / "src" / "ucie_miner" / "library_exact_index.py"
    digest = sha256(exact_source.read_bytes()).hexdigest()
    if digest != expected_source_sha256:
        raise ValueError("staged first-party source SHA256 mismatch")
    sys.path.insert(0, str(root / "src"))
    from ucie_miner.library_exact_index import (
        ExactLibraryError, exact_search_linked_public_candidates,
    )
    from ucie_public.policy import PolicyError

    handoff = _synthetic_handoff()
    missing = KEY[:3] + ("UCIE_RELOCATION_ABSENT",)
    with patch("urllib.request.urlopen",
               side_effect=AssertionError("external public GET forbidden")), \
         patch("sqlite3.connect",
               side_effect=AssertionError("operating SQLite forbidden")), \
         patch("pathlib.Path.write_bytes",
               side_effect=AssertionError("source/data write forbidden")), \
         patch("pathlib.Path.write_text",
               side_effect=AssertionError("source/data write forbidden")):
        pages = [exact_search_linked_public_candidates(
            handoff, queries=(KEY,), limit=10, offset=i)
            for i in (0, 10, 20)]
        found = [r["library_item_id"]
                 for p in pages for r in p["items"][0]["items"]]
        if (len(found) != ROWS or len(set(found)) != ROWS
                or found != sorted(found)
                or [p["items"][0]["returned_count"] for p in pages] != [10, 10, 7]
                or [p["items"][0]["next_offset"] for p in pages] != [10, 20, None]
                or not all(p["one_pass_source_normalization"] is True
                           and p["validated_source_rows"] == ROWS
                           and p["network_requests"] == 0
                           and p["operating_database_writes"] == 0
                           and p["v1_accepted"] is False
                           and p["auto_promoted"] is False
                           for p in pages)
                or any(row["human_approved"] or row["export_allowed"]
                       for p in pages
                       for row in p["items"][0]["items"])):
            raise AssertionError("relocated first-party exact search behavior mismatch")
        indexed = exact_search_linked_public_candidates(
            handoff, queries=(KEY, missing, KEY), limit=10, offset=20)
        if (indexed["index_built"] is not True
                or indexed["items"][0]["items"] != pages[2]["items"][0]["items"]
                or indexed["items"][1]["total_matches"] != 0
                or indexed["items"][2]["items"] != pages[2]["items"][0]["items"]):
            raise AssertionError("relocated multiquery behavior mismatch")
        tampered = deepcopy(handoff)
        tampered["tasks"][0]["approval"] = True
        try:
            exact_search_linked_public_candidates(
                tampered, queries=(KEY,), limit=10)
        except PolicyError:
            pass
        else:
            raise AssertionError("forged owner approval was not blocked")
        corrupt = deepcopy(handoff)
        corrupt["tasks"][-1]["skill_id"] = "unapproved-skill"
        try:
            exact_search_linked_public_candidates(
                corrupt, queries=(missing,), limit=10)
        except ValueError:
            pass
        else:
            raise AssertionError("unmatched untrusted row escaped validation")
        try:
            exact_search_linked_public_candidates(
                handoff, queries=(KEY,), offset=-1)
        except ExactLibraryError:
            pass
        else:
            raise AssertionError("unbounded offset accepted")
        partial = deepcopy(handoff)
        partial["status"] = "SOURCE_REVISIONS_PENDING_NO_GO"
        partial["pending_source_revisions"] = 1
        disabled = exact_search_linked_public_candidates(
            partial, queries=(KEY,), offset=10)
        if (disabled["status"] != "INCOMPLETE_SOURCE_LINKED_CATALOG_NO_GO"
                or disabled["v1_accepted"] is not False
                or disabled["items"]):
            raise AssertionError("incomplete stage ledger failed open")
    return {
        "schema": SCHEMA,
        "status": "UCIE_CODE_ONLY_STAGE_SEARCH_PASS__LIVE_MIGRATION_NO_GO",
        "code_only_stage": "UCIE_PROJECT/UCIE",
        "exact_source_sha256": digest,
        "source_rows_synthetic": ROWS,
        "results_retrieved": len(found),
        "duplicate_or_missing_results": False,
        "one_pass_search_verified": True,
        "multiquery_page_verified": True,
        "invalid_source_and_approval_rejected": True,
        "incomplete_ledger_remains_no_go": True,
        "no_legacy_git_or_venv_copied": True,
        "operating_database_present": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "source_changes": 0,
        "scheduler_or_c40_tunnel_accessed": False,
        "mcp_live_connection_verified": False,
        "real_owner_windows_drive_migrated": False,
        "customer_release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UCIE code-only staged P3/P6 exact-search smoke")
    parser.add_argument("--source-sha256", required=True)
    args = parser.parse_args()
    try:
        output = run_smoke(args.source_sha256)
    except (OSError, ValueError, AssertionError, ImportError) as exc:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_CODE_ONLY_STAGE_FAIL_CLOSED",
            "reason_type": type(exc).__name__,
            "mcp_live_connection_verified": False,
            "real_owner_windows_drive_migrated": False,
            "customer_release_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
