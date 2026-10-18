"""Synthetic contract tests for the one-command local owner handoff.

No actual owner key, GitHub network call, signing, file scan or deployment.
"""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from scripts.ucie_owner_two_rule_one_shot import (
    owner_input, select_exact_ci, WORKFLOW,
)
from ucie_public.policy import PolicyError


class LocalOwnerOneShotTests(TestCase):
    def test_exact_main_ci_must_pass_at_same_commit(self):
        sha = "a" * 40
        runs = {"workflow_runs": [
            {"id": 31, "head_sha": sha, "event": "push",
             "head_branch": "main", "status": "completed",
             "conclusion": "success", "path": WORKFLOW},
            {"id": 35, "head_sha": sha, "event": "push",
             "head_branch": "main", "status": "completed",
             "conclusion": "success", "path": WORKFLOW},
            {"id": 99, "head_sha": "b" * 40, "event": "push",
             "head_branch": "main", "status": "completed",
             "conclusion": "success", "path": WORKFLOW},
        ]}
        self.assertEqual(select_exact_ci(runs, sha), 35)

    def test_failed_or_different_ci_is_not_accepted(self):
        sha = "a" * 40
        base = {"id": 1, "head_sha": sha, "event": "push",
                "head_branch": "main", "status": "completed",
                "conclusion": "success", "path": WORKFLOW}
        for field, value in [
            ("head_sha", "b" * 40), ("event", "pull_request"),
            ("head_branch", "feature"), ("status", "in_progress"),
            ("conclusion", "failure"), ("path", "fake.yml"),
        ]:
            entry = {**base, field: value}
            with self.subTest(field=field), self.assertRaises(PolicyError):
                select_exact_ci({"workflow_runs": [entry]}, sha)
        with self.assertRaises(PolicyError):
            select_exact_ci({"workflow_runs": []}, sha)

    def test_noninteractive_cannot_imply_owner_risk_acceptance(self):
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaises(PolicyError):
                owner_input()

    def test_three_separate_exact_interactive_approvals(self):
        from ucie_public.multi_owner_release import CONFIRM, RISK, SECOND_RISK
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("sys.stdout.isatty", return_value=True),
            patch("builtins.input", side_effect=[CONFIRM, RISK, SECOND_RISK]),
        ):
            self.assertEqual(owner_input(), (CONFIRM, RISK, SECOND_RISK))
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("sys.stdout.isatty", return_value=True),
            patch("builtins.input", side_effect=[CONFIRM, RISK, "YES"]),
            self.assertRaises(PolicyError),
        ):
            owner_input()
