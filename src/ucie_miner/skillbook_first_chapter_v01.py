"""First UCIE-authored SkillBook chapter; inert public evidence draft only."""
from __future__ import annotations

from hashlib import sha256
import json
import re

from .library_entry import build_library_entry
from .skillbook_blueprint import compose_blueprint

SCHEMA = "UCIE_SKILLBOOK_V01_FIRST_CHAPTER"
CATALOG_SCHEMA = "UCIE_W04_SKILLBOOK_CATALOG_V01"
MERGE_SHA = "af79f49308f8f87896d1c09419db3f5ff67185af"
SOURCE_URL = "https://github.com/python/cpython/pull/160930"
SOURCE_METADATA = {
    "repository": "python/cpython",
    "pr": 160930,
    "merge_commit_sha": MERGE_SHA,
    "merged_utc": "2026-10-30T06:46:19Z",
    "title": "gh-160561: Fix race in test_socket testFromFdError",
}
CHAPTER = """# Background cleanup before a resource snapshot

Status: UCIE-authored draft, not independently verified or approved.

A test can mistake a concurrent background cleanup for a resource leak:
the resource count may change between an early baseline and the trial.
The safe general pattern is to wait for the relevant cleanup completion
signal (with a bounded timeout) before collecting a baseline, then perform
only an isolated, authorized test and compare the final count. Timeout must
block the verdict. Equality is not a general proof that all leaks are absent.

Illustrative first-party synthetic cases: early baseline 7 versus final 6
is a naive false alarm when cleanup correctly changes the baseline to 6.
A stabilized 6-to-6 comparison shows no change. A stabilized 6-to-7
comparison detects a difference. Missing completion means no verdict.

Public context: https://github.com/python/cpython/pull/160930
Merge SHA: af79f49308f8f87896d1c09419db3f5ff67185af
This UCIE-authored chapter neither executes upstream changes nor asserts
that backports, versions, security, rights or independent QA are verified.
"""
CASES = (
    ("benign_cleanup", 7, 6, 6, True, "STABLE_NO_CHANGE"),
    ("changed_count", 7, 6, 7, True, "DIFFERENCE_DETECTED"),
    ("no_completion", 7, 6, 6, False, "BLOCKED_NO_COMPLETION"),
)
NON_APPROVAL = {
    "independent_upstream_qa": False, "license_cleared": False,
    "version_verified": False, "security_signoff": False,
    "owner_approved": False, "signed": False, "export_allowed": False,
    "model_trained": False, "other_project_access": False,
    "operating_database_writes": 0,
}
QUERY = re.compile(r"[A-Za-z0-9_ -]{0,80}\Z")


def evaluate_synthetic_case(case: tuple) -> dict:
    """Inert, bounded UCIE synthetic count oracle, never an upstream runner."""
    if type(case) is not tuple or len(case) != 6:
        raise ValueError("invalid synthetic case shape")
    name, early, stable, after, done, expected = case
    if type(name) is not str or not re.fullmatch(r"[a-z_]{1,32}", name):
        raise ValueError("invalid case name")
    if any(type(n) is not int or not 0 <= n <= 4096 for n in (early, stable, after)):
        raise ValueError("invalid synthetic counts")
    if type(done) is not bool or expected not in (
        "STABLE_NO_CHANGE", "DIFFERENCE_DETECTED", "BLOCKED_NO_COMPLETION"
    ):
        raise ValueError("invalid scenario expectation")
    status = ("BLOCKED_NO_COMPLETION" if not done else
              "STABLE_NO_CHANGE" if stable == after else "DIFFERENCE_DETECTED")
    return {
        "case": name, "status": status, "expected_matches": status == expected,
        "naive_early_compare_flags_change": early != after,
        "gated_compare_flags_change": (stable != after if done else None),
        "real_upstream_code_executed": False,
    }


def build_first_skillbook() -> dict:
    source_digest = sha256(json.dumps(SOURCE_METADATA, sort_keys=True,
                        separators=(",", ":")).encode("utf-8")).hexdigest()
    candidate = {
        "kind": "REUSABLE_SKILL", "source_id": "repo:python/cpython",
        "evidence_reference": "pr:160930:" + MERGE_SHA,
        "evidence_sha256": source_digest,
        "purpose_code": "STABLE_RESOURCE_SNAPSHOT",
        "version_scope": "UNDETERMINED", "dependencies": [],
    }
    entry = build_library_entry(candidate)
    blueprint = compose_blueprint("STABLE_RESOURCE_SNAPSHOT", [candidate])
    trials = [evaluate_synthetic_case(x) for x in CASES]
    if not all(t["expected_matches"] for t in trials):
        raise ValueError("first-party synthetic acceptance failed")
    return {
        "schema": SCHEMA,
        "status": "UCIE_AUTHORED_DRAFT_SYNTHETIC_ONLY_NO_GO",
        "title": "Background cleanup before a resource snapshot",
        "skillbook_id": blueprint["blueprint_id"],
        "library_entry": entry,
        "human_readable_chapter": CHAPTER,
        "machine_contract": {
            "schema": "UCIE_MACHINE_SKILL_CONTRACT_DRAFT_V01",
            "skill_id": "ucie.python.stable_resource_snapshot.v0_1",
            "language": "Python", "supported_version": "UNDETERMINED",
            "preconditions": ["WAIT_FOR_CLEANUP_WITH_TIMEOUT",
                              "MEASURE_AFTER_COMPLETION",
                              "ISOLATED_UCIE_OWNED_SYNTHETIC_CONTEXT"],
            "inputs": ["early", "stable", "after", "completion_observed"],
            "outputs": ["STABLE_NO_CHANGE", "DIFFERENCE_DETECTED",
                        "BLOCKED_NO_COMPLETION"],
            "installable": False, "upstream_code_executed": False,
        },
        "evidence_manifest": {
            "source_url": SOURCE_URL, "merge_commit_sha": MERGE_SHA,
            "merged_utc": SOURCE_METADATA["merged_utc"],
            "ucie_public_metadata_sha256": source_digest,
            "digest_scope": "UCIE_AUTHORED_METADATA_NOT_UPSTREAM_CONTENT",
            "upstream_content_hashed": False,
            "version_status": "UNVERIFIED",
            "license_status": "NOT_CLEARED",
        },
        "synthetic_evaluation": {
            "status": "FIRST_PARTY_SYNTHETIC_ONLY",
            "passed": sum(x["expected_matches"] for x in trials),
            "total": len(trials), "cases": trials,
        },
        "revision_history": [
            {"version": "0.1", "status": "DRAFT_NOT_RELEASED",
             "reason": "SYNTHETIC_ONLY_RIGHTS_AND_INDEPENDENT_QA_PENDING"},
        ],
        "gates": dict(NON_APPROVAL),
    }


def search_first_skillbook(query: str = "", *,
                           kind: str | None = None,
                           source_id: str | None = None) -> dict:
    """First W04-linked in-memory catalog search; no V0.9 UI mutation."""
    if type(query) is not str or QUERY.fullmatch(query) is None:
        raise ValueError("invalid bounded query")
    if kind is not None and kind != "REUSABLE_SKILL":
        raise ValueError("unsupported kind")
    if source_id is not None and source_id != "repo:python/cpython":
        raise ValueError("source outside approved first chapter")
    book = build_first_skillbook()
    texts = (book["title"], book["machine_contract"]["language"],
             book["library_entry"]["purpose_code"], SOURCE_URL)
    included = all(any(term in text.casefold() for text in texts)
                   for term in query.casefold().split())
    item = {
        "skillbook_id": book["skillbook_id"],
        "library_item_id": book["library_entry"]["library_item_id"],
        "title": book["title"], "kind": "REUSABLE_SKILL",
        "source_id": "repo:python/cpython", "source_url": SOURCE_URL,
        "version": "UNDETERMINED", "approval": "NOT_APPROVED",
        "synthetic_test_status": "FIRST_PARTY_SYNTHETIC_ONLY",
        "export_allowed": False,
    }
    return {
        "schema": CATALOG_SCHEMA, "status": "IN_MEMORY_DRAFT_CATALOG_ONLY",
        "total_matches": int(included), "items": [item] if included else [],
        "index_persisted": False, "browser_v09_modified": False,
        "operating_database_writes": 0, "network_requests": 0,
    }


def main() -> int:
    book = build_first_skillbook()
    print(json.dumps({
        "schema": SCHEMA, "status": book["status"],
        "skillbook_id": book["skillbook_id"],
        "synthetic_evaluation": book["synthetic_evaluation"],
        "evidence_manifest": book["evidence_manifest"],
        "gates": book["gates"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
