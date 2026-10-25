"""UCIE Stage12 multiaxis review triage: fully synthetic, offline and inert."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.public_review_triage import triage_unverified_review_rows
from ucie_miner.public_candidate_staging import stage_public_candidates
from ucie_miner.public_candidate_learning import (
    update_unverified_review_queue, optional_hourly_review_learning,
    OPT_IN_FILENAME, OPT_IN_TOKEN, REVIEW_FILE,
)
from test_ucie_stage11_hourly_stage import fixture_batch

SHA_A = "a" * 40
SHA_B = "b" * 40
DIGEST_A = "c" * 64
DIGEST_B = "d" * 64


def sample_rows():
    return [
        ("python/cpython", "pr:17:" + SHA_A, "python-runtime-safety",
         DIGEST_A, ["API_CONTRACT", "TEST_REGRESSION"], None),
        ("git/git", "commit:" + SHA_B, "git-workflow-prevention",
         DIGEST_B, ["SECURITY", "REGRESSION"], None),
        ("python/cpython", "fix-pr:17:" + SHA_A + ":" + DIGEST_A,
         "python-runtime-safety", DIGEST_B,
         ["CONCURRENCY", "EXCEPTION_HANDLING"],
         "PATCH_OBSERVED_DELTA_GENERIC_EXCEPTION_PROTOCOL_ERROR_CODE"),
    ]


class PublicMultiAxisTriageTests(unittest.TestCase):
    def test_preserves_multiple_categories_and_evidence_depth_without_approval(self):
        out = triage_unverified_review_rows(sample_rows())
        self.assertEqual(out["status"], "UNVERIFIED_REVIEW_AGENDA_ONLY")
        self.assertEqual(out["triaged_revisions"], 3)
        self.assertEqual(out["selected_count"], 3)
        self.assertEqual(out["source_counts"]["python/cpython"], 2)
        self.assertEqual(out["source_counts"]["git/git"], 1)
        self.assertEqual(out["pattern_signal_counts"]["API_CONTRACT"], 1)
        self.assertEqual(out["pattern_signal_counts"]["TEST_REGRESSION"], 1)
        self.assertEqual(out["evidence_level_counts"][
            "STRUCTURED_PATCH_SIGNAL_UNVERIFIED"], 1)
        self.assertEqual(out["evidence_level_counts"][
            "PUBLIC_GIT_COMMIT_METADATA_UNVERIFIED"], 1)
        self.assertFalse(out["priority_is_confidence"])
        self.assertFalse(out["source_origin_independently_attested"])
        self.assertTrue(out["human_approval_required"])
        self.assertFalse(out["production_approved"])
        self.assertFalse(out["auto_promoted"])
        self.assertEqual(out["external_api_gets"], 0)
        self.assertEqual(out["persistent_writes"], 0)
        for row in out["selected_for_review"]:
            self.assertFalse(row["independent_fix_verified"])
            self.assertFalse(row["release_inclusion_verified"])
            self.assertFalse(row["license_approved"])
            self.assertFalse(row["rule_approved"])
        pr = next(r for r in out["selected_for_review"]
                  if r["reference"].startswith("pr:"))
        self.assertEqual(pr["error_pattern_tags"],
                         ["API_CONTRACT", "TEST_REGRESSION"])
        self.assertEqual(pr["evidence_level"],
                         "PUBLIC_PR_METADATA_UNVERIFIED")

    def test_stable_preview_permutation_and_review_limit(self):
        items = sample_rows()
        a = triage_unverified_review_rows(items, limit=2)
        b = triage_unverified_review_rows(list(reversed(items)), limit=2)
        self.assertEqual(a, b)
        self.assertEqual(a["triaged_revisions"], 3)
        self.assertEqual(a["selected_count"], 2)
        self.assertEqual(a["selected_for_review"][0]["source"], "git/git")
        self.assertEqual(a["selected_for_review"][0]["review_priority_band"],
                         "REVIEW_FIRST")

    def test_reject_forged_sources_ids_tags_and_transition_hints(self):
        for changed in (
            ("OTHER/private", sample_rows()[0][1],
             "python-runtime-safety", DIGEST_A,
             ["API_CONTRACT"], None),
            ("python/cpython", "pr:1:" + SHA_A,
             "git-workflow-prevention", DIGEST_A,
             ["API_CONTRACT"], None),
            ("python/cpython", "pr:17:" + SHA_A,
             "python-runtime-safety", DIGEST_A,
             ["REMOTE_EXECUTE_CODE"], None),
            ("python/cpython", "pr:17:" + SHA_A,
             "python-runtime-safety", DIGEST_A,
             ["API_CONTRACT"], "PATCH_OBSERVED_ADD_GENERIC_EXCEPTION"),
            ("git/git", "commit:" + SHA_B,
             "git-workflow-prevention", DIGEST_B, ["API_CONTRACT"], None),
            ("python/cpython", "fix-pr:17:" + SHA_A + ":" + DIGEST_A,
             "python-runtime-safety", DIGEST_B,
             ["CONCURRENCY"], "USER_DATA_HERE"),
        ):
            with self.subTest(ref=changed[1]), self.assertRaises(DiscoveryError):
                triage_unverified_review_rows([changed])
        with self.assertRaises(DiscoveryError):
            triage_unverified_review_rows([sample_rows()[0]] * 2)
        for invalid_limit in (0, 13, True, 1.5, "12"):
            with self.subTest(limit=invalid_limit), self.assertRaises(DiscoveryError):
                triage_unverified_review_rows([], limit=invalid_limit)
        with self.assertRaises(DiscoveryError):
            triage_unverified_review_rows([None] * 20001)

    def test_existing_stage12_preview_integrates_without_extra_disk_writes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "UCIE"
            runtime = root / "runtime"
            runtime.mkdir(parents=True)
            batch = fixture_batch(
                root=root,
                sources=("python/cpython", "PowerShell/PowerShell", "git/git",
                         "modelcontextprotocol/python-sdk", "actions/runner-images"),
                max_enrich=1, include_git_commits=True,
                include_docs=False, include_advisories=False, backfill_pages=1)
            stage_public_candidates(batch, root=root, allow_disk_write=True)
            stage_file = runtime / "stage10_unverified_public_candidates.sqlite3"
            before = stage_file.read_bytes()
            result = update_unverified_review_queue(root)
            self.assertEqual(result["status"], "STAGE12_REVIEW_PREVIEW_ONLY")
            triage = result["triage_preview"]
            self.assertEqual(triage["triaged_revisions"], 2)
            self.assertEqual(triage["selected_count"], 2)
            self.assertEqual(triage["external_api_gets"], 0)
            self.assertEqual(triage["persistent_writes"], 0)
            self.assertEqual(stage_file.read_bytes(), before)
            self.assertFalse((runtime / REVIEW_FILE).exists())

            (runtime / OPT_IN_FILENAME).write_text(OPT_IN_TOKEN, encoding="ascii")
            enabled = optional_hourly_review_learning(root)
            self.assertEqual(enabled["status"],
                             "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO")
            self.assertEqual(enabled["triage_preview"], triage)
            self.assertEqual(enabled["new_review_proposals"], 2)
            self.assertEqual(stage_file.read_bytes(), before)
            self.assertTrue((runtime / REVIEW_FILE).is_file())
            again = optional_hourly_review_learning(root)
            self.assertEqual(again["new_review_proposals"], 0)
            self.assertEqual(again["triage_preview"], triage)


if __name__ == "__main__":
    unittest.main()
