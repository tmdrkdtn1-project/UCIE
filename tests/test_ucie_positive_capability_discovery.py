"""W05 positive engine/skill/learning-logic discovery + useful W04 search precision.

Use only UCIE-authored synthetic public metadata and in-memory handoff rows.
No source execution, external HTTP, operating database writes or promotion.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import unittest
from unittest.mock import patch

from ucie_miner.positive_capability_discovery import (
    SCHEMA, classify_public_capability_metadata,
    discover_positive_capabilities,
)
from ucie_miner.library_search import (
    search_linked_public_candidates, LibrarySearchError,
)
from ucie_miner.public_discovery import DiscoveryError, public_feed_url

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
MERGE = "a" * 40
SOURCE = "python/cpython"


def public_pr(number: int, title: str, *, source: str = SOURCE,
              merged_at: str = "2026-10-20T12:00:00Z",
              merge_sha: str = MERGE):
    return {
        "number": number, "title": title, "merged_at": merged_at,
        "html_url": f"https://github.com/{source}/pull/{number}",
        "base": {"repo": {"full_name": source}},
        "merge_commit_sha": merge_sha,
    }


def handoff_two_evidence_revisions():
    # Two evidence digests on the same immutable public PR. Not two skills.
    tasks = []
    for i, proof in enumerate(("1" * 64, "2" * 64)):
        tasks.append({
            "candidate_id_sha256": str(i + 3) * 64,
            "source": "modelcontextprotocol/python-sdk",
            "reference": "pr:3696:" + "a" * 40,
            "skill_id": "mcp-api-compatibility",
            "pattern_code": "EXCEPTION_HANDLING",
            "evidence_sha256": proof,
            "stage6_candidate": None,
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "approval": False,
            "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
        })
    return {
        "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
        "status": "LINKED_UNVERIFIED_NO_GO",
        "source_revisions": 2, "linked_revisions": 2,
        "pending_source_revisions": 0,
        "tasks": tasks, "auto_promoted": False,
        "production_approved": False, "deploy_allowed": False,
    }


class PositiveCapabilitiesTests(unittest.TestCase):
    def test_distinct_engine_skill_and_learning_logic_candidates(self):
        rows = [
            public_pr(100, "Add incremental build cache for compilation"),
            public_pr(101, "Introduce test automation and test helper"),
            public_pr(102, "Implement adaptive learning feedback loop"),
            public_pr(103, "Fix regression in incremental build cache"),
            public_pr(104, "Add missing error handling for endpoint"),
        ]
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no new external network")):
            out = classify_public_capability_metadata(
                rows, source_id="repo:python/cpython", now=NOW)
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(out["candidate_count"], 3)
        self.assertEqual({x["kind"] for x in out["candidates"]},
                         {"DEVELOPMENT_ENGINE", "REUSABLE_SKILL", "LEARNING_LOGIC"})
        self.assertEqual(out["repair_title_count"], 2)
        self.assertFalse(out["untrusted_source_titles_retained"])
        self.assertNotIn(rows[0]["title"], json.dumps(out))
        self.assertEqual(out["database_writes"], 0)
        self.assertFalse(out["auto_promoted"])
        for item in out["candidates"]:
            self.assertEqual(item["evidence_strength"], "MERGED_PR_TITLE_CUE_ONLY")
            self.assertFalse(item["actual_capability_verified"])
            self.assertFalse(item["benefit_measured"])
            self.assertFalse(item["export_allowed"])
            self.assertEqual(item["freshness_bucket"], "RECENT_UPSTREAM_MERGE")

    def test_same_public_metadata_has_deterministic_entry_identity(self):
        rows = [public_pr(100, "Add incremental build cache for compilation")]
        one = classify_public_capability_metadata(
            rows, source_id="repo:python/cpython", now=NOW)
        two = classify_public_capability_metadata(
            deepcopy(rows), source_id="repo:python/cpython", now=NOW)
        self.assertEqual(one, two)
        changed = deepcopy(rows)
        changed[0]["merge_commit_sha"] = "b" * 40
        three = classify_public_capability_metadata(
            changed, source_id="repo:python/cpython", now=NOW)
        self.assertNotEqual(one["candidates"][0]["library_item_id"],
                            three["candidates"][0]["library_item_id"])

    def test_old_public_capabilities_are_historical_not_recent(self):
        rows = [public_pr(100, "Add incremental build cache", 
                          merged_at="2023-11-06T12:00:00Z")]
        out = classify_public_capability_metadata(
            rows, source_id="repo:python/cpython", now=NOW)
        self.assertEqual(out["candidate_count"], 1)
        self.assertEqual(out["candidates"][0]["freshness_bucket"],
                         "HISTORICAL_PUBLIC_EVIDENCE")

    def test_multiple_categories_are_not_falsely_selected(self):
        rows = [public_pr(100, "Add incremental build cache for test automation")]
        out = classify_public_capability_metadata(
            rows, source_id="repo:python/cpython", now=NOW)
        self.assertEqual(out["ambiguous_positive_cue_count"], 1)
        self.assertEqual(out["candidate_count"], 0)

    def test_unpinned_or_unmerged_public_data_does_not_become_skill(self):
        rows = [
            public_pr(100, "Add incremental build cache", merge_sha=None),
            dict(public_pr(101, "Add test automation"), merged_at=None),
        ]
        out = classify_public_capability_metadata(
            rows, source_id="repo:python/cpython", now=NOW)
        self.assertEqual(out["candidate_count"], 0)
        self.assertEqual(out["unpinned_positive_cue_count"], 1)
        self.assertEqual(out["nonmerged_count"], 1)

    def test_public_source_identity_bounded_before_any_fetch(self):
        called = []
        def fake_get(url):
            called.append(url)
            return [public_pr(100, "Add incremental build cache")]
        for ids in (("research:GH Archive",), ("repo:other/private",),
                    ("doc:python/cpython",),
                    ("repo:python/cpython", "repo:python/cpython")):
            with self.subTest(ids=ids):
                with self.assertRaises(DiscoveryError):
                    discover_positive_capabilities(
                        source_ids=ids, fetch=fake_get, now=NOW)
        self.assertEqual(called, [])

    def test_explicit_callback_existing_approved_route_only(self):
        called = []
        def fake_get(url):
            called.append(url)
            return [public_pr(100, "Add incremental build cache")]
        out = discover_positive_capabilities(
            source_ids=("repo:python/cpython",), fetch=fake_get, now=NOW)
        self.assertEqual(called, [public_feed_url("python/cpython")])
        self.assertEqual(out["existing_feed_callback_calls"], 1)
        self.assertEqual(out["candidate_count"], 1)
        self.assertFalse(out["new_api_route_added"])
        self.assertFalse(out["auto_promoted"])

    def test_forged_url_future_merge_duplicate_and_oversized_input_rejected(self):
        bad_url = public_pr(100, "Add incremental build cache")
        bad_url["html_url"] = "https://example.com/private"
        future = public_pr(100, "Add incremental build cache",
                           merged_at="2026-10-28T00:00:00Z")
        for rows in (
            [bad_url], [future],
            [public_pr(100, "Add incremental build cache")] * 2,
            [public_pr(i + 1, "Add incremental build cache") for i in range(21)],
        ):
            with self.subTest(rows=len(rows)):
                with self.assertRaises(DiscoveryError):
                    classify_public_capability_metadata(
                        rows, source_id="repo:python/cpython", now=NOW)

    def test_no_actual_positive_candidates_in_bugfix_only_fixture(self):
        rows = [public_pr(100, "Fix missing API arguments")]
        out = classify_public_capability_metadata(
            rows, source_id="repo:python/cpython", now=NOW)
        self.assertEqual(out["candidate_count"], 0)
        self.assertEqual(out["repair_title_count"], 1)


class PreciseVirtualLibrarySearchTests(unittest.TestCase):
    def test_domain_filter_removes_python_sdk_false_language_matches(self):
        handoff = handoff_two_evidence_revisions()
        broad = search_linked_public_candidates(
            handoff, query="python", limit=10)
        exact = search_linked_public_candidates(
            handoff, query="python", domain="Python", limit=10)
        mcp = search_linked_public_candidates(
            handoff, query="python", domain="MCP/API", limit=10)
        self.assertEqual(broad["total_matches"], 2)
        self.assertEqual(exact["total_matches"], 0)
        self.assertEqual(mcp["total_matches"], 2)
        self.assertEqual(mcp["domain_filter"], "MCP/API")

    def test_grouping_pr_evidence_revisions_preserves_all_hashes(self):
        handoff = handoff_two_evidence_revisions()
        out = search_linked_public_candidates(
            handoff, query="python", domain="MCP/API",
            group_revisions=True, limit=10)
        self.assertEqual(out["raw_evidence_revision_matches"], 2)
        self.assertEqual(out["total_matches"], 1)
        self.assertEqual(out["returned_count"], 1)
        self.assertEqual(out["items"][0]["evidence_revision_count"], 2)
        self.assertEqual(out["items"][0]["evidence_revision_sha256s"],
                         ["1" * 64, "2" * 64])
        self.assertFalse(out["items"][0]["export_allowed"])

    def test_bad_domain_and_boolean_group_type_rejected(self):
        handoff = handoff_two_evidence_revisions()
        with self.assertRaises(LibrarySearchError):
            search_linked_public_candidates(handoff, domain="private")
        with self.assertRaises(LibrarySearchError):
            search_linked_public_candidates(handoff, group_revisions="yes")


if __name__ == "__main__":
    unittest.main()
