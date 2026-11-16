"""UCIE W10 v04 original P9 queue + immutable source/commit candidate preview QA.

All test Git mutations are confined to fresh TEMP/UCIE synthetic roots.
No upstream code execution, owner D:/UCIE writes, public GET, P11 rearm,
real prior-version deployment, operating rollback, or approval.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from test_ucie_stage11_hourly_stage import fixture_batch
from ucie_miner import experience_evolution as evo
from ucie_miner import w10_selected_candidate_review_v04 as v04
from ucie_miner.product_v1 import integrated_product_preview
from ucie_miner.public_candidate_staging import stage_public_candidates
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, optional_hourly_review_learning,
)
from ucie_miner.w10_disposable_restore_probe_v02 import git_blob_sha1

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "src" / "ucie_miner" / "library_exact_index.py"
REPOS = ("python/cpython", "PowerShell/PowerShell", "git/git",
         "modelcontextprotocol/python-sdk", "actions/runner-images")


class W10SelectedProposalCandidateReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="UCIE_W10_V04_SYNTH_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        (self.root / "runtime" / "UCIE_W09_CONSUMER_SYNTH_ONLY.marker").write_text(
            "UCIE_W09_CONSUMER_SYNTHETIC_ONLY_V01", encoding="ascii")
        self.relative = "src/ucie_miner/library_exact_index.py"
        self.source = self.root / self.relative
        self.source.parent.mkdir(parents=True)
        self.git("init", "-q")
        self.git("config", "user.email", "review-only@ucie.invalid")
        self.git("config", "user.name", "UCIE Synthetic Only")
        self.git("config", "core.autocrlf", "false")
        self.prior = SOURCE.read_bytes()
        self.source.write_bytes(self.prior)
        self.git("add", "--", self.relative)
        self.git("commit", "-qm", "UCIE prior first-party source")
        self.prior_commit = self.git("rev-parse", "HEAD").decode().strip()
        self.candidate = self.prior + b"\n# UCIE first-party inert candidate STATIC ONLY\n"
        self.source.write_bytes(self.candidate)
        self.git("add", "--", self.relative)
        self.git("commit", "-qm", "UCIE inert candidate source change")
        self.candidate_commit = self.git("rev-parse", "HEAD").decode().strip()
        self._seed_source_review()

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args], check=True,
            timeout=12, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    def _seed_source_review(self):
        batch = fixture_batch(
            root=self.root, sources=REPOS, max_enrich=1,
            include_git_commits=True, include_docs=False,
            include_advisories=False, backfill_pages=1)
        stage_public_candidates(batch, root=self.root, allow_disk_write=True)
        (self.root / "runtime" / OPT_IN_FILENAME).write_text(
            OPT_IN_TOKEN, encoding="ascii")
        proposal = optional_hourly_review_learning(self.root)
        self.assertEqual(proposal["new_review_proposals"], 2)
        result = evo.run_evolution_cycle(self.root, record=True)
        self.assertTrue(result["new_event_written"])
        product = integrated_product_preview(
            self.root, query="", limit=20, include_demo=False)
        queue = product["library_revision_review_queue"]
        self.assertGreaterEqual(len(queue["items"]), 1)
        self.proposal_id = next(
            q["proposal_id"] for q in queue["items"]
            if q["target_ucie_component"] == v04.TARGET_INDEX)

    def args(self, *, include_candidate=True):
        obj = {
            "root": self.root,
            "proposal_id": self.proposal_id,
            "prechange_commit": self.prior_commit,
            "expected_prechange_sha256": sha256(self.prior).hexdigest(),
            "expected_prechange_blob_sha1": git_blob_sha1(self.prior),
            "queries": 8, "repeats": 1,
        }
        if include_candidate:
            obj.update({
                "candidate_commit": self.candidate_commit,
                "expected_candidate_sha256": sha256(self.candidate).hexdigest(),
                "expected_candidate_blob_sha1": git_blob_sha1(self.candidate),
            })
        return obj

    def inspect(self, **kw):
        data = self.args(**kw)
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("W10 v04 must never GET")):
            return v04.inspect_selected_candidate(**data)

    def test_01_real_p9_exact_proposal_no_candidate_is_no_go(self):
        r = self.inspect(include_candidate=False)
        self.assertEqual(r["status"], v04.STATUS_MISSING)
        self.assertEqual(r["proposal_id"], self.proposal_id)
        self.assertEqual(r["w08_current_heldout_cases"], 9)
        self.assertEqual(r["w08_current_heldout_mismatches"], 0)
        self.assertIsNone(r["candidate_git_commit"])
        self.assertFalse(r["candidate_runtime_executed"])
        self.assertFalse(r["actual_operating_rollback_executed"])
        self.assertFalse(r["customer_release_authorized"])

    def test_02_real_p9_exact_proposal_direct_child_static_git_candidate(self):
        before = self.source.read_bytes()
        r = self.inspect()
        self.assertEqual(r["status"], v04.STATUS_PREVIEW)
        self.assertEqual(r["candidate_git_commit"], self.candidate_commit)
        self.assertEqual(r["candidate_delta_files"], [self.relative])
        self.assertEqual(r["candidate_git_blob_sha1"], git_blob_sha1(self.candidate))
        self.assertTrue(r["candidate_python_ast_static_only"][
            "syntax_parsed_without_execution"])
        self.assertTrue(r["candidate_python_ast_static_only"][
            "original_imports_unchanged"])
        self.assertTrue(r["candidate_python_ast_static_only"][
            "original_top_level_definitions_preserved"])
        self.assertFalse(r["candidate_behavioral_regression_executed"])
        self.assertFalse(r["candidate_security_negative_regression_executed"])
        self.assertFalse(r["post_restore_real_w09_consumer_reverified"])
        self.assertFalse(r["owner_prechange_archive_historically_authenticated"])
        self.assertFalse(r["owner_deploy_or_rollback_authorized"])
        self.assertFalse(r["auto_promoted"])
        self.assertEqual(r["public_network_gets"], 0)
        self.assertEqual(r["operating_database_writes"], 0)
        self.assertEqual(self.source.read_bytes(), before)

    def test_03_invalid_original_proposal_id_denied(self):
        a = self.args()
        a["proposal_id"] = "f" * 64
        with self.assertRaises(v04.CandidateReviewError):
            v04.inspect_selected_candidate(**a)

    def test_04_wrong_baseline_commit_and_source_sha_denied(self):
        for key, value in (
            ("prechange_commit", "f"*40),
            ("expected_prechange_sha256", "f"*64),
            ("expected_prechange_blob_sha1", "f"*40),
        ):
            with self.subTest(key=key):
                a = self.args()
                a[key] = value
                with self.assertRaises(v04.CandidateReviewError):
                    v04.inspect_selected_candidate(**a)

    def test_05_wrong_candidate_pin_denied(self):
        for key in ("expected_candidate_sha256", "expected_candidate_blob_sha1"):
            a = self.args()
            a[key] = "f" * (64 if key.endswith("sha256") else 40)
            with self.subTest(key=key):
                with self.assertRaises(v04.CandidateReviewError):
                    v04.inspect_selected_candidate(**a)

    def test_06_partial_candidate_arguments_fail_before_source_read(self):
        for key in ("candidate_commit", "expected_candidate_sha256",
                    "expected_candidate_blob_sha1"):
            with self.subTest(key=key):
                a = self.args()
                a[key] = None
                with self.assertRaises(v04.CandidateReviewError):
                    v04.inspect_selected_candidate(**a)

    def test_07_owner_w09_digest_is_exact_lease(self):
        a = self.args()
        a["expected_w09_review_digest"] = "f"*64
        with self.assertRaises(v04.CandidateReviewError):
            v04.inspect_selected_candidate(**a)

    def test_08_unapproved_extra_file_in_candidate_denied(self):
        # One child of prior with two files changed instead of exact target.
        self.git("checkout", "-q", "--detach", self.prior_commit)
        self.source.write_bytes(self.candidate)
        other = self.root / "src" / "ucie_miner" / "unapproved.py"
        other.write_text("X = 42\n", encoding="ascii")
        self.git("add", "--", self.relative, "src/ucie_miner/unapproved.py")
        self.git("commit", "-qm", "synthetic candidate plus unauthorized file")
        bad = self.git("rev-parse", "HEAD").decode().strip()
        a = self.args()
        a["candidate_commit"] = bad
        with self.assertRaises(v04.CandidateReviewError):
            v04.inspect_selected_candidate(**a)

    def test_09_candidate_must_be_direct_child_not_multiparent_or_2deep(self):
        self.source.write_bytes(self.candidate + b"# second commit\n")
        self.git("add", "--", self.relative)
        self.git("commit", "-qm", "second hop is not a direct child")
        a = self.args()
        a["candidate_commit"] = self.git("rev-parse", "HEAD").decode().strip()
        a["expected_candidate_sha256"] = sha256(self.source.read_bytes()).hexdigest()
        a["expected_candidate_blob_sha1"] = git_blob_sha1(self.source.read_bytes())
        with self.assertRaises(v04.CandidateReviewError):
            v04.inspect_selected_candidate(**a)

    def test_10_candidate_import_delta_static_denial(self):
        self.git("checkout", "-q", "--detach", self.prior_commit)
        changed = self.prior + b"\nimport os  # synthetic NEW import\n"
        self.source.write_bytes(changed)
        self.git("add", "--", self.relative)
        self.git("commit", "-qm", "synthetic import drift")
        a = self.args()
        a["candidate_commit"] = self.git("rev-parse", "HEAD").decode().strip()
        a["expected_candidate_sha256"] = sha256(changed).hexdigest()
        a["expected_candidate_blob_sha1"] = git_blob_sha1(changed)
        with self.assertRaises(v04.CandidateReviewError):
            v04.inspect_selected_candidate(**a)

    def test_11_invalid_candidate_syntax_denied_without_execution(self):
        self.git("checkout", "-q", "--detach", self.prior_commit)
        changed = self.prior + b"\ndef broken(:\n"
        self.source.write_bytes(changed)
        self.git("add", "--", self.relative)
        self.git("commit", "-qm", "synthetic syntax error")
        a = self.args()
        a["candidate_commit"] = self.git("rev-parse", "HEAD").decode().strip()
        a["expected_candidate_sha256"] = sha256(changed).hexdigest()
        a["expected_candidate_blob_sha1"] = git_blob_sha1(changed)
        with self.assertRaises(v04.CandidateReviewError):
            v04.inspect_selected_candidate(**a)

    def test_12_candidate_added_top_level_expression_denied(self):
        self.git("checkout", "-q", "--detach", self.prior_commit)
        changed = self.prior + b"\nprint('synthetic do-not-run')\n"
        self.source.write_bytes(changed)
        self.git("add", "--", self.relative)
        self.git("commit", "-qm", "synthetic top-level behavior")
        a = self.args()
        a["candidate_commit"] = self.git("rev-parse", "HEAD").decode().strip()
        a["expected_candidate_sha256"] = sha256(changed).hexdigest()
        a["expected_candidate_blob_sha1"] = git_blob_sha1(changed)
        with self.assertRaises(v04.CandidateReviewError):
            v04.inspect_selected_candidate(**a)

    def test_13_no_actual_owner_archive_is_not_rollback_ready(self):
        r = self.inspect()
        self.assertFalse(r["owner_prechange_archive_present"])
        self.assertFalse(r["candidate_runtime_executed"])
        self.assertFalse(r["owner_prechange_archive_historically_authenticated"])
        self.assertFalse(r["prechange_version_was_deployed_attested"])
        self.assertFalse(r["actual_operating_rollback_executed"])

    def test_14_wrong_root_project_denied(self):
        wrong = self.root.parent / "AnotherProject"
        wrong.mkdir()
        a = self.args()
        a["root"] = wrong
        with self.assertRaises(v04.CandidateReviewError):
            v04.inspect_selected_candidate(**a)

    def test_15_injected_false_p9_approval_denied(self):
        from ucie_miner import w10_revision_rollback_review_v01 as original
        true = original.review_w10_revision_and_rollback(
            self.root, select_proposal_id=self.proposal_id, limit=20,
            queries=8, repeats=1)
        fake = dict(true)
        fake["customer_release_authorized"] = True
        with patch.object(v04, "review_w10_revision_and_rollback",
                          return_value=fake):
            with self.assertRaises(v04.CandidateReviewError):
                v04.inspect_selected_candidate(**self.args())

    def test_16_first_party_source_working_tree_smudge_not_a_candidate(self):
        # A Git object's content does not change with working-tree CRLF.
        content = self.source.read_bytes()
        self.source.write_bytes(content.replace(b"\n", b"\r\n"))
        r = self.inspect()
        self.assertEqual(r["status"], v04.STATUS_PREVIEW)
        self.assertFalse(r["candidate_runtime_executed"])
        self.assertFalse(r["customer_release_authorized"])


if __name__ == "__main__":
    unittest.main()
