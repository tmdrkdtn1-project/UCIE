"""W05 multi-source survey: only original approved routes and first-party trial."""
from __future__ import annotations

from copy import deepcopy
import json
import sys
import unittest
from unittest.mock import patch

from test_ucie_positive_capability_discovery import NOW, public_pr
from ucie_miner import public_capability_survey as survey
from ucie_miner.public_discovery import public_feed_url
from ucie_miner.capability_trials import CapabilityTrialError


def fixture(source: str, page: int) -> list[dict]:
    if page == 1:
        return [
            public_pr(40001, "Fix exception regression in tests",
                      source=source),
            dict(public_pr(40002, "Enhance runtime internals",
                           source=source), merged_at=None),
            public_pr(40003, "Refactor argument handling", source=source),
        ]
    if page == 2:
        if source == "modelcontextprotocol/python-sdk":
            return [
                public_pr(40003, "Refactor argument handling", source=source),
                public_pr(40004, "Introduce test automation helper",
                          source=source),
            ]
        return [public_pr(40005, "Refactor public API", source=source)]
    if page == 3:
        return [public_pr(40006, "Modernize setup instructions", source=source)]
    raise AssertionError("unapproved fixture page")


class ApprovedPublicSurveyTests(unittest.TestCase):
    def test_single_approved_source_zero_preserved_with_correct_exclusions(self):
        called = []
        def fetch(url):
            called.append(url)
            return fixture("python/cpython", 1)
        result = survey.survey_approved_public_sources(
            source_ids=("repo:python/cpython",),
            fetch=fetch, pages=1, now=NOW)
        self.assertEqual(called, [public_feed_url("python/cpython")])
        self.assertEqual(result["total_public_rows_examined"], 3)
        self.assertEqual(result["total_positive_title_cues"], 0)
        self.assertEqual(result["status"],
                         "W05_NO_POSITIVE_TITLE_CUES_IN_BOUNDED_SAMPLE")
        summary = result["sources"][0]
        self.assertEqual(summary["excluded_nonmerged"], 1)
        self.assertEqual(summary["excluded_repair_title"], 1)
        self.assertEqual(summary["merged_nonrepair_without_positive_cue"], 1)
        self.assertFalse(summary["no_positive_cues_proves_no_capability"])
        self.assertEqual(result["approved_public_routes_requested"], 1)
        self.assertFalse(result["all_repository_history_exhaustively_searched"])
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertEqual(result["experience_ledger_writes"], 0)
        self.assertFalse(result["auto_promoted"])

    def test_exactly_five_approved_repos_page2_and_no_upstream_execution(self):
        visited = []
        def fetch(url):
            visited.append(url)
            for source in survey.ALLOWED:
                repo = source.removeprefix("repo:")
                for page in (1, 2):
                    if public_feed_url(repo, page=page) == url:
                        return fixture(repo, page)
            raise AssertionError("unexpected public source URL")
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no direct network")):
            result = survey.survey_approved_public_sources(
                source_ids=survey.ALLOWED, fetch=fetch, pages=2,
                limit=2, try_first_party=True, now=NOW)
        self.assertEqual(len(visited), 10)
        self.assertEqual(len(set(visited)), 10)
        self.assertEqual(result["sources_scanned"], 5)
        self.assertEqual(result["total_positive_title_cues"], 1)
        self.assertEqual(result["positive_cue_purpose_counts"],
                         {"SKILL_TEST_AUTOMATION": 1})
        self.assertEqual(result["status"],
                         "W05_PUBLIC_TITLE_CUES_FOUND_UNVERIFIED_NO_GO")
        self.assertEqual(result["items"][0]["source_id"],
                         "repo:modelcontextprotocol/python-sdk")
        self.assertEqual(result["items"][0]["kind"], "REUSABLE_SKILL")
        self.assertEqual(result["items"][0]["evidence_strength"],
                         "MERGED_PR_TITLE_CUE_ONLY")
        self.assertFalse(result["items"][0]["approved"])
        self.assertFalse(result["items"][0]["export_allowed"])
        self.assertEqual(result["sources"][3]["duplicate_public_rows"], 1)
        trial = result["first_party_trial"]
        self.assertIsNotNone(trial)
        self.assertTrue(
            trial["ucie_owned_synthetic_trial"]["exact_result_equivalence_observed"])
        self.assertFalse(trial["upstream_code_executed"])
        self.assertFalse(trial["upstream_benefit_verified"])
        self.assertFalse(trial["experience_recorded"])
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertEqual(result["experience_ledger_writes"], 0)

    def test_limits_and_unapproved_sources_refused_without_get(self):
        attempted = []
        def fetch(url):
            attempted.append(url)
            return []
        for source_ids, pages, limit in (
            (("repo:unapproved/private",), 1, 5),
            (("research:GH Archive",), 1, 5),
            (("doc:python/cpython",), 1, 5),
            (("repo:python/cpython",) * 2, 1, 5),
            (survey.ALLOWED, 4, 5),
            (survey.ALLOWED, 0, 5),
            (survey.ALLOWED, True, 5),
            (survey.ALLOWED, 1, 0),
            (survey.ALLOWED, 1, 11),
            ((), 1, 5),
        ):
            with self.subTest(source_ids=source_ids, pages=pages, limit=limit):
                with self.assertRaises(survey.PublicSourceSurveyError):
                    survey.survey_approved_public_sources(
                        source_ids=source_ids, fetch=fetch,
                        pages=pages, limit=limit)
        self.assertEqual(attempted, [])

    def test_conflicting_cross_page_public_pr_metadata_is_not_survey_candidate(self):
        def fetch(url):
            source = "modelcontextprotocol/python-sdk"
            if url == public_feed_url(source, page=1):
                return fixture(source, 1)
            altered = deepcopy(fixture(source, 2))
            altered[0]["title"] = "New allegedly better test automation"
            return altered
        with self.assertRaises(CapabilityTrialError):
            survey.survey_approved_public_sources(
                source_ids=("repo:modelcontextprotocol/python-sdk",),
                fetch=fetch, pages=2, now=NOW)

    def test_original_upstream_title_not_leaked_in_survey_json(self):
        sensitive_text = "Introduce test automation helper"
        result = survey.survey_approved_public_sources(
            source_ids=("repo:modelcontextprotocol/python-sdk",),
            fetch=lambda url: fixture("modelcontextprotocol/python-sdk", 2),
            pages=1, now=NOW)
        self.assertNotIn(sensitive_text, json.dumps(result))
        self.assertEqual(result["total_positive_title_cues"], 1)

    def test_explicit_cli_all_five_count_and_inert_default(self):
        args = ["survey", "--all-approved", "--pages", "2"]
        with (
            patch.object(sys, "argv", args),
            patch("ucie_miner.public_capability_survey.public_feed_get",
                  side_effect=AssertionError("must not call external GET")),
            patch("builtins.print") as printed,
        ):
            self.assertEqual(survey.main(), 0)
        before = json.loads(printed.call_args.args[0])
        self.assertEqual(before["status"],
                         "W05_PUBLIC_SURVEY_EXPLICIT_LIVE_REQUIRED")
        self.assertEqual(before["network_requests"], 0)
        urls = []
        def mock_get(url):
            urls.append(url)
            for source in survey.ALLOWED:
                repo = source.removeprefix("repo:")
                for page in (1, 2):
                    if public_feed_url(repo, page=page) == url:
                        return fixture(repo, page)
            raise AssertionError("unknown URL")
        with (
            patch.object(sys, "argv", args + ["--live", "--try-first-party"]),
            patch("ucie_miner.public_capability_survey.public_feed_get",
                  side_effect=mock_get),
            patch("builtins.print") as printed,
        ):
            self.assertEqual(survey.main(), 0)
        got = json.loads(printed.call_args.args[0])
        self.assertEqual(got["network_requests"], 10)
        self.assertEqual(got["approved_public_routes_requested"], 10)
        self.assertEqual(len(urls), 10)
        self.assertEqual(got["experience_ledger_writes"], 0)

    def test_cli_network_failure_counts_attempts_without_false_success(self):
        args = ["survey", "--source-id", "repo:python/cpython",
                "--pages", "2", "--live"]
        with (
            patch.object(sys, "argv", args),
            patch("ucie_miner.public_capability_survey.public_feed_get",
                  side_effect=[fixture("python/cpython", 1),
                               OSError("synthetic API failure")]),
            patch("builtins.print") as printed,
        ):
            self.assertEqual(survey.main(), 2)
        out = json.loads(printed.call_args.args[0])
        self.assertEqual(out["status"], "W05_SURVEY_FAIL_CLOSED")
        self.assertEqual(out["attempted_public_gets"], 2)
        self.assertEqual(out["operating_database_writes"], 0)
        self.assertFalse(out["auto_promoted"])

    def test_cli_rejects_missing_selection_or_conflicting_flags(self):
        for args in (
            ["survey", "--live"],
            ["survey", "--live", "--all-approved",
             "--source-id", "repo:python/cpython"],
            ["survey", "--source-id", "repo:python/cpython", "--pages", "4"],
            ["survey", "--source-id", "repo:python/cpython", "--pages", "0"],
        ):
            with (
                patch.object(sys, "argv", args),
                patch("ucie_miner.public_capability_survey.public_feed_get",
                      side_effect=AssertionError("must not GET")),
                patch("builtins.print") as printed,
            ):
                self.assertEqual(survey.main(), 2)
            out = json.loads(printed.call_args.args[0])
            self.assertEqual(out["attempted_public_gets"], 0)
            self.assertEqual(out["status"], "W05_SURVEY_FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
