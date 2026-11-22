"""Offline UCIE publisher crash/retry reconciliation regressions."""
from copy import deepcopy
import unittest

from ucie_public.policy import PolicyError
from ucie_public.unattended_github_reconcile import inspect_partial_github_publication

BASE = "a" * 40
HEAD = "b" * 40
BRANCH = "automation/ucie-crash-safe-20261023"
MANIFEST = "c" * 64


def signed():
    return {
        "status": "UCIE_SIGNED_GITHUB_BUNDLE_VERIFIED_NO_NETWORK",
        "repository": "tmdrkdtn1-project/UCIE", "base_sha": BASE,
        "branch": BRANCH, "manifest_sha256": MANIFEST,
    }


def observed():
    return {
        "repository": "tmdrkdtn1-project/UCIE",
        "base_sha": BASE, "branch": BRANCH, "main_ref_sha": BASE,
        "branch_ref_sha": None, "branch_commit_parent_shas": [],
        "expected_written_commit_sha": None, "pr_number": None,
        "pr_head_sha": None, "pr_head_ref": None,
        "pr_base_ref": None, "pr_draft": None, "pr_state": "absent",
        "expected_manifest_sha256": MANIFEST,
    }


def branch_written(o):
    o["branch_ref_sha"] = HEAD
    o["expected_written_commit_sha"] = HEAD
    o["branch_commit_parent_shas"] = [BASE]
    return o


def pr_exists(o):
    o["pr_number"] = 105
    o["pr_head_sha"] = HEAD
    o["pr_head_ref"] = BRANCH
    o["pr_base_ref"] = "main"
    o["pr_draft"] = True
    o["pr_state"] = "open"
    return o


class UCIEGithubReconcileTests(unittest.TestCase):
    def test_no_branch_requires_new_approval(self):
        result = inspect_partial_github_publication(signed(), observed())
        self.assertEqual(result["status"], "UCIE_PUBLISH_NO_BRANCH_PRESENT_NEW_APPROVAL_REQUIRED")
        self.assertFalse(result["new_git_write_performed"])
        self.assertFalse(result["github_evidence_authentication_performed"])

    def test_existing_branch_with_missing_pr_never_blind_retry(self):
        status = inspect_partial_github_publication(signed(), branch_written(observed()))
        self.assertEqual(status["status"], "UCIE_PUBLISH_BRANCH_WITHOUT_PR_MANUAL_RECONCILIATION_REQUIRED")
        self.assertIsNone(status["pr_number"])

    def test_existing_draft_pr_not_conflated_with_ci_pass(self):
        result = inspect_partial_github_publication(signed(), pr_exists(branch_written(observed())))
        self.assertEqual(result["status"], "UCIE_PUBLISH_DRAFT_PR_METADATA_MATCH_CI_PENDING")
        self.assertEqual(result["pr_number"], 105)
        self.assertFalse(result["production_approved"])

    def test_wrong_commit_parent_missing_ledger_and_main_motion_stop(self):
        for change in (
            {"branch_ref_sha": HEAD},
            {"expected_written_commit_sha": HEAD},
            {"main_ref_sha": "d"*40},
            {"branch_ref_sha": HEAD, "expected_written_commit_sha": "e"*40},
            {"branch_ref_sha": HEAD, "expected_written_commit_sha": HEAD,
             "branch_commit_parent_shas": ["e"*40]},
        ):
            o = observed()
            o.update(change)
            with self.subTest(change=change):
                result = inspect_partial_github_publication(signed(), o)
                self.assertIn("NO_GO", result["status"])

    def test_wrong_pr_state_never_accepted(self):
        for change in (
            {"pr_draft": False},
            {"pr_state": "closed"},
            {"pr_head_sha": "d"*40},
            {"pr_head_ref": "main"},
            {"pr_base_ref": "release"},
        ):
            o = pr_exists(branch_written(observed()))
            o.update(change)
            with self.subTest(change=change):
                result = inspect_partial_github_publication(signed(), o)
                self.assertEqual(result["status"], "UCIE_PUBLISH_PR_MISMATCH_NO_GO")

    def test_foreign_and_malformed_inputs_fail_closed(self):
        for key, value in (
            ("repository", "other/project"), ("base_sha", "d"*40),
            ("branch", "automation/other-project"),
            ("expected_manifest_sha256", "0"*64),
            ("pr_number", True), ("pr_state", "merged"),
            ("branch_commit_parent_shas", ["not-a-sha"]),
        ):
            o = observed()
            o[key] = value
            with self.subTest(key=key), self.assertRaises(PolicyError):
                inspect_partial_github_publication(signed(), o)
        with self.assertRaises(PolicyError):
            inspect_partial_github_publication({}, observed())
        with self.assertRaises(PolicyError):
            inspect_partial_github_publication(signed(), {**observed(), "unsafe": True})


if __name__ == "__main__":
    unittest.main()
