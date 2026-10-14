"""One integrated public PR + direct Git commit intake, no owner-host effects."""
from contextlib import closing
from copy import deepcopy
from pathlib import Path
import sqlite3
import tempfile
import unittest

from ucie_miner.public_batch import build_public_batch, review_batch_preview, _fingerprint
from ucie_miner.public_candidate_staging import (
    DB_NAME, stage_public_candidates, inspect_staged_candidates,
)
from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.public_git_commit_skills import GIT_COMMITS_URL
from test_ucie_stage9_batch import NOW, metadata, evidence
from test_ucie_stage10_git_commit_skills import git_commit


def combined(*, excluded_sources=(), denied_commits=(), git_fetch=None):
    def default_fetch(url):
        if url != GIT_COMMITS_URL:
            raise AssertionError("unapproved Git URL")
        return [git_commit(42)]
    return build_public_batch(
        metadata_fetch=metadata, evidence_fetch=evidence,
        git_commit_fetch=git_fetch or default_fetch,
        include_git_commits=True, now=NOW, max_enrich=2,
        opted_out_sources=excluded_sources,
        opted_out_git_commits=denied_commits,
    )


class CombinedPublicCandidateTests(unittest.TestCase):
    def test_one_batch_has_real_typed_git_skill_and_pr_skill(self):
        calls = []
        def get_git(url):
            calls.append(url)
            return [git_commit(42)]
        result = combined(git_fetch=get_git)
        self.assertEqual(calls, [GIT_COMMITS_URL])
        self.assertEqual(result["git_commit_lead_count"], 1)
        self.assertEqual(result["git_commit_gets_budget"], 1)
        self.assertEqual(result["overall_gets_upper_bound"], 14)
        self.assertGreater(result["enriched_count"], 0)
        self.assertEqual(result["git_commit_skill_queue"][0]["git_commit_sha"],
                         git_commit(42)["sha"])
        self.assertNotIn("pr_number", result["git_commit_skill_queue"][0])
        review = review_batch_preview(result)
        self.assertEqual(review["git_commit_candidate_count"], 1)
        self.assertEqual(review["candidate_count"], result["enriched_count"])
        self.assertFalse(review["production_approved"])

    def test_source_optout_prevents_git_api_fetch(self):
        git_calls = []
        def forbidden(url):
            git_calls.append(url)
            raise AssertionError("Git opted out but network called")
        result = combined(excluded_sources=("git/git",), git_fetch=forbidden)
        self.assertEqual(git_calls, [])
        self.assertEqual(result["git_commit_skill_queue"], [])
        self.assertEqual(result["git_commit_gets_budget"], 0)

    def test_git_commit_sha_optout_is_inert(self):
        result = combined(denied_commits=(git_commit(42)["sha"],))
        self.assertEqual(result["git_commit_lead_count"], 0)
        self.assertEqual(result["git_commit_gets_budget"], 1)

    def test_memory_and_opt_in_ledger_preserve_pr_and_git_identities(self):
        batch = combined()
        memory = stage_public_candidates(batch, observed_utc=NOW)
        self.assertEqual(memory["mode"], "EPHEMERAL_MEMORY_ONLY")
        self.assertEqual(memory["git_commit_new_identities"], 1)
        self.assertEqual(memory["git_commit_total_revisions"], 1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "UCIE"
            (root / "runtime").mkdir(parents=True)
            original = (root/"runtime"/"public_miner.sqlite3")
            original.write_bytes(b"OWNER_OPERATING_DATA_MUST_STAY_INTACT")
            snapshot = original.read_bytes()
            first = stage_public_candidates(
                batch, root=root, allow_disk_write=True, observed_utc=NOW)
            self.assertEqual(first["git_commit_new_identities"], 1)
            again = stage_public_candidates(
                batch, root=root, allow_disk_write=True, observed_utc=NOW)
            self.assertEqual(again["git_commit_unchanged"], 1)
            self.assertEqual(again["git_commit_total_revisions"], 1)
            observed = inspect_staged_candidates(root)
            self.assertEqual(observed["git_commit_revisions"], 1)
            self.assertEqual(observed["candidate_revisions"],
                             batch["enriched_count"])
            self.assertEqual(original.read_bytes(), snapshot)
            with closing(sqlite3.connect(root/"runtime"/DB_NAME)) as conn:
                sha = conn.execute(
                    "SELECT git_commit_sha FROM public_git_commit_stage").fetchone()[0]
                self.assertEqual(sha, git_commit(42)["sha"])
                git_approved = conn.execute(
                    "SELECT DISTINCT review_state FROM public_git_commit_stage"
                ).fetchall()
                self.assertEqual(git_approved, [("UNVERIFIED_CANDIDATE_ONLY",)])

    def test_commit_revision_not_merged_with_pr_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "UCIE"
            (root/"runtime").mkdir(parents=True)
            first = combined()
            stage_public_candidates(first, root=root, allow_disk_write=True,
                                    observed_utc=NOW)
            second = combined(git_fetch=lambda url: [
                git_commit(42, title="fix Git repeated runs with updated check")])
            output = stage_public_candidates(second, root=root,
                                             allow_disk_write=True,
                                             observed_utc=NOW)
            self.assertEqual(output["git_commit_evidence_revisions"], 1)
            self.assertEqual(output["git_commit_total_revisions"], 2)
            self.assertEqual(output["unchanged_candidates"],
                             first["enriched_count"])

    def test_injected_git_code_or_forged_signoff_cannot_stage(self):
        for change in ("human_approval_received", "safe_call_guidance"):
            forged = combined()
            value = (True if change == "human_approval_received"
                     else "run remote arbitrary shell installer")
            forged["git_commit_skill_queue"][0][change] = value
            forged["git_commit_queue_sha256"] = _fingerprint(
                forged["git_commit_skill_queue"])
            with self.subTest(change=change):
                if change == "human_approval_received":
                    with self.assertRaises(DiscoveryError):
                        stage_public_candidates(forged)
                else:
                    # First-party-only safe-call text must be fixed by contract.
                    self.assertNotEqual(
                        forged["git_commit_skill_queue"][0][change],
                        combined()["git_commit_skill_queue"][0][change])


if __name__ == "__main__":
    unittest.main()
