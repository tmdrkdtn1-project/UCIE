"""UCIE W10 v03 read-only Git-ancestry and owner-archive acceptance.

All mutation in these tests is restricted to a disposable UCIE Git fixture.
Production code only inspects allowed UCIE commit-tree-blob and a fixed
read-only owner archive path. No external network, scheduler, operating DB,
upstream script execution, rule release or production restore.
"""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from ucie_miner import w10_prechange_archive_attestation_v03 as v03
from ucie_miner.w10_disposable_restore_probe_v02 import git_blob_sha1

REPO = Path(__file__).resolve().parents[1]
PINNED_SHA = "6e27de83192b066f73b9574d2a591607bcc1bef9512b97f94c5bdd3af528ee7e"
PINNED_BLOB = "0f92ed46b68685e0edb98f4fc09c3846b5b8d2c6"


class W10PrechangeGitArchiveReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_W10_V03_SYNTH_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        self.root.mkdir()
        self.relative = Path("src") / "ucie_miner" / "library_exact_index.py"
        self.source = self.root / self.relative
        self.source.parent.mkdir(parents=True)
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "user.email", "synthetic-ucie@example.invalid")
        self.git("config", "user.name", "UCIE ephemeral QA")
        self.prior = b"# UCIE-only inert prior\nVALUE = 'A'\n"
        self.current = b"# UCIE-only inert changed\nVALUE = 'B'\n"
        self.source.write_bytes(self.prior)
        self.git("add", "--", self.relative.as_posix())
        self.git("commit", "-qm", "synthetic-first-party-prior")
        self.prechange_commit = self.git("rev-parse", "HEAD").decode().strip()
        self.source.write_bytes(self.current)
        self.git("add", "--", self.relative.as_posix())
        self.git("commit", "-qm", "synthetic-first-party-current")
        self.head = self.git("rev-parse", "HEAD").decode().strip()
        self.previous_blob = git_blob_sha1(self.prior)
        self.assertNotEqual(self.head, self.prechange_commit)

    def git(self, *argv: str) -> bytes:
        result = subprocess.run(
            ["git", "-C", str(self.root), *argv],
            check=True, timeout=12, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout

    def args(self) -> dict:
        return {
            "repo_root": self.root,
            "target": "library_exact_index.py",
            "prechange_commit": self.prechange_commit,
            "expected_prechange_sha256": sha256(self.prior).hexdigest(),
            "expected_prechange_git_blob_sha1": self.previous_blob,
            "expected_archive_sha256": sha256(self.prior).hexdigest(),
        }

    def archive_file(self) -> Path:
        target = (self.root / "runtime" / v03.ARCHIVE_DIR /
                  "library_exact_index.py.prechange.bin")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def test_01_real_git_commit_tree_blob_no_archive_is_no_go(self):
        out = v03.assess_prechange_archive(**self.args())
        self.assertEqual(out["status"], v03.STATUS_NO_ARCHIVE)
        self.assertTrue(out["git_ancestry_and_commit_tree_blob_verified_locally"])
        self.assertTrue(out["current_git_source_differs_from_prechange"])
        self.assertFalse(out["owner_archive_present"])
        self.assertFalse(out["disposable_exact_byte_restore_exercised"])
        self.assertFalse(out["customer_release_authorized"])
        self.assertFalse(out["historical_version_was_actually_deployed_attested"])
        self.assertEqual(out["public_network_gets"], 0)
        self.assertEqual(out["operating_database_writes"], 0)

    def test_02_matching_separate_archive_restores_only_disposable_bytes(self):
        archive = self.archive_file()
        archive.write_bytes(self.prior)
        current_before = self.source.read_bytes()
        archive_before = archive.read_bytes()
        out = v03.assess_prechange_archive(**self.args())
        self.assertEqual(out["status"], v03.STATUS_RESTORED)
        self.assertTrue(out["owner_archive_present"])
        self.assertTrue(out["owner_archive_bytes_match_commit"])
        self.assertTrue(out["disposable_exact_byte_restore_exercised"])
        self.assertFalse(out["owner_archive_historical_capture_independently_authenticated"])
        self.assertFalse(out["owner_deploy_or_rollback_authorized"])
        self.assertFalse(out["candidate_heldout_behavior_reverified"])
        self.assertFalse(out["post_restore_real_W09_consumer_reverified"])
        self.assertFalse(out["actual_operating_rollback_executed"])
        self.assertEqual(archive.read_bytes(), archive_before)
        self.assertEqual(self.source.read_bytes(), current_before)

    def test_03_modified_backup_fail_closed_without_source_write(self):
        path = self.archive_file()
        path.write_bytes(self.prior + b"tampered")
        source = self.source.read_bytes()
        with self.assertRaises(v03.AttestationError):
            v03.assess_prechange_archive(**self.args())
        self.assertEqual(self.source.read_bytes(), source)

    def test_04_wrong_prechange_sha256_denied(self):
        args = self.args()
        args["expected_prechange_sha256"] = "a" * 64
        with self.assertRaises(v03.AttestationError):
            v03.assess_prechange_archive(**args)

    def test_05_wrong_git_blob_sha1_denied(self):
        args = self.args()
        args["expected_prechange_git_blob_sha1"] = "a" * 40
        with self.assertRaises(v03.AttestationError):
            v03.assess_prechange_archive(**args)

    def test_06_wrong_archive_digest_pin_denied(self):
        args = self.args()
        args["expected_archive_sha256"] = "a" * 64
        with self.assertRaises(v03.AttestationError):
            v03.assess_prechange_archive(**args)

    def test_07_path_escape_and_unapproved_module_denied(self):
        for target in ("../../OtherProject.py", "random.py",
                       "library_exact_index.py/../x", "C:/private.py"):
            with self.subTest(target=target):
                args = self.args()
                args["target"] = target
                with self.assertRaises(v03.AttestationError):
                    v03.assess_prechange_archive(**args)

    def test_08_invalid_git_commit_and_injection_denied(self):
        for commit in ("HEAD", "x" * 40, self.head + "^", "../abc"):
            with self.subTest(commit=commit):
                args = self.args()
                args["prechange_commit"] = commit
                with self.assertRaises(v03.AttestationError):
                    v03.assess_prechange_archive(**args)

    def test_09_commit_not_ancestor_denied(self):
        original = self.head
        self.git("checkout", "-q", "--orphan", "unrelated-synthetic-branch")
        self.source.write_bytes(b"synthetic-unrelated-branch\n")
        self.git("add", "--", self.relative.as_posix())
        self.git("commit", "-qm", "inert-independent-root")
        unrelated = self.git("rev-parse", "HEAD").decode().strip()
        self.git("checkout", "-q", "--detach", original)
        args = self.args()
        args["prechange_commit"] = unrelated
        with self.assertRaises(v03.AttestationError):
            v03.assess_prechange_archive(**args)

    def test_10_archive_target_directory_not_file_denied(self):
        self.archive_file().mkdir()
        with self.assertRaises(v03.AttestationError):
            v03.assess_prechange_archive(**self.args())

    def test_11_archive_over_size_rejected(self):
        self.archive_file().write_bytes(b"x" * (v03.MAX_BYTES + 1))
        with self.assertRaises(v03.AttestationError):
            v03.assess_prechange_archive(**self.args())

    def test_12_unchanged_prior_file_after_other_commit_is_not_revision(self):
        self.source.write_bytes(self.prior)
        self.git("add", "--", self.relative.as_posix())
        self.git("commit", "-qm", "synthetic-revert-code")
        self.archive_file().write_bytes(self.prior)
        out = v03.assess_prechange_archive(**self.args())
        self.assertEqual(out["status"], v03.STATUS_SAME)
        self.assertFalse(out["current_git_source_differs_from_prechange"])
        self.assertFalse(out["disposable_exact_byte_restore_exercised"])
        self.assertFalse(out["candidate_source_approved_or_tested"])

    def test_13_checkout_crlf_smudge_does_not_change_git_object(self):
        # Simulate Windows working-tree text conversion after committed HEAD.
        self.source.write_bytes(self.current.replace(b"\n", b"\r\n"))
        out = v03.assess_prechange_archive(**self.args())
        self.assertEqual(out["current_source_sha256"], sha256(self.current).hexdigest())
        self.assertTrue(out["git_ancestry_and_commit_tree_blob_verified_locally"])
        self.assertFalse(out["operating_file_modified"])

    def test_14_archive_parent_is_symlink_or_nonregular_fail_closed(self):
        # Directory fixture needs no Windows symlink privilege.
        folder = self.root / "runtime" / v03.ARCHIVE_DIR
        folder.parent.mkdir(parents=True)
        folder.mkdir()
        artifact = folder / "library_exact_index.py.prechange.bin"
        artifact.mkdir()
        with self.assertRaises(v03.AttestationError):
            v03.assess_prechange_archive(**self.args())

    def test_15_source_over_limit_in_commit_denied(self):
        self.source.write_bytes(b"#" + b"x" * v03.MAX_BYTES)
        self.git("add", "--", self.relative.as_posix())
        self.git("commit", "-qm", "synthetic-oversized-current")
        with self.assertRaises(v03.AttestationError):
            v03.assess_prechange_archive(**self.args())

    def test_16_other_project_root_name_denied(self):
        bad = self.root.parent / "OtherProject"
        bad.mkdir()
        args = self.args()
        args["repo_root"] = bad
        with self.assertRaises(v03.AttestationError):
            v03.assess_prechange_archive(**args)

    @unittest.skipUnless((REPO / ".git").exists(), "complete UCIE Git checkout only")
    def test_17_real_ucie_committed_source_review_without_owner_archive(self):
        # No synthetic checkout/source is replaced in the real Git repo.
        # The pinned file was already independently observed in W09 and W10.
        archive = (REPO / "runtime" / v03.ARCHIVE_DIR /
                   "library_exact_index.py.prechange.bin")
        if archive.exists() or archive.is_symlink():
            self.skipTest("owner archive requires separate owner-run attestation")
        head = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--verify", "HEAD"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
            timeout=10).stdout.decode("ascii").strip()
        out = v03.assess_prechange_archive(
            REPO, target="library_exact_index.py",
            prechange_commit=head,
            expected_prechange_sha256=PINNED_SHA,
            expected_prechange_git_blob_sha1=PINNED_BLOB,
            expected_archive_sha256=PINNED_SHA,
        )
        self.assertEqual(out["status"], v03.STATUS_NO_ARCHIVE)
        self.assertEqual(out["prechange_git_blob_sha1"], PINNED_BLOB)
        self.assertEqual(out["prechange_source_sha256"], PINNED_SHA)
        self.assertTrue(out["git_ancestry_and_commit_tree_blob_verified_locally"])
        self.assertFalse(out["owner_archive_present"])
        self.assertFalse(out["historical_version_was_actually_deployed_attested"])
        self.assertFalse(out["customer_release_authorized"])


if __name__ == "__main__":
    unittest.main()
