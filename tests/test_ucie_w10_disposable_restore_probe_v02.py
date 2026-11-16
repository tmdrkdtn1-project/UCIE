"""UCIE W10 v02: standalone synthetic negatives + exact first-party source pin.

All synthetic bytes are UCIE-authored and inert; nothing from upstream is
executed, downloaded, published, signed or applied. Full source-pin check is
mandatory in the complete UCIE GitHub checkout and skipped only in a
standalone portable test environment that lacks the repository source.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
import subprocess
import unittest

try:
    from ucie_miner.w10_disposable_restore_probe_v02 import (
        ALLOWED_TARGETS, ProbeError, disposable_restore_probe, git_blob_sha1,
    )
except ModuleNotFoundError:
    # Permit standalone development against the exact matching module.
    from w10_disposable_restore_probe_v02 import (
        ALLOWED_TARGETS, ProbeError, disposable_restore_probe, git_blob_sha1,
    )


UCIE_REPO = Path(__file__).resolve().parents[1]
SOURCE_FILE = UCIE_REPO / "src" / "ucie_miner" / "library_exact_index.py"
# Source identity independently observed from GitHub at pinned main W09
# commit aeecc3fc64dc542daba6e40ef29dce66c296ebdf, unchanged in W10 v01.
PINNED_SOURCE_SHA256 = "6e27de83192b066f73b9574d2a591607bcc1bef9512b97f94c5bdd3af528ee7e"
PINNED_GIT_BLOB_SHA1 = "0f92ed46b68685e0edb98f4fc09c3846b5b8d2c6"
PINNED_GIT_COMMIT = "aeecc3fc64dc542daba6e40ef29dce66c296ebdf"


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


class UCIEW10DisposableRestoreProbeTests(unittest.TestCase):
    @staticmethod
    def args() -> dict:
        before = b"UCIE-owned synthetic previous bytes\x00\xff\n"
        candidate = b"UCIE-owned synthetic candidate bytes\x00\xff\n"
        return {
            "target": "library_exact_index.py",
            "prior_bytes": before, "prior_sha256": digest(before),
            "prior_git_blob_sha1": git_blob_sha1(before),
            "candidate_bytes": candidate, "candidate_sha256": digest(candidate),
            "current_bytes": before, "current_sha256": digest(before),
            "claimed_prior_commit": "a" * 40,
        }

    def test_01_inert_temp_roundtrip_never_approves_operating_restore(self):
        output = disposable_restore_probe(**self.args())
        self.assertTrue(output["disposable_candidate_staged_and_prior_bytes_restored"])
        self.assertTrue(output["prior_git_blob_identity_matches_caller_pin"])
        self.assertTrue(output["temporary_files_cleaned_after_test"])
        for key in ("claimed_commit_contains_blob_independently_verified",
                    "prior_bytes_authenticated_as_actual_prechange",
                    "owner_host_restorable_bytes_verified",
                    "candidate_known_from_approved_revision",
                    "candidate_behavior_regression_executed",
                    "independent_security_regression_completed",
                    "post_restore_w09_consumer_verified",
                    "actual_operating_rollback_executed",
                    "customer_release_authorized", "auto_promoted"):
            self.assertFalse(output[key])
        self.assertEqual(output["public_network_gets"], 0)
        self.assertEqual(output["operating_database_writes"], 0)
        self.assertEqual(output["git_mutations"], 0)

    def test_02_prior_sha256_tampered(self):
        a = self.args(); a["prior_bytes"] += b"tampered"
        with self.assertRaises(ProbeError): disposable_restore_probe(**a)

    def test_03_candidate_sha256_tampered(self):
        a = self.args(); a["candidate_sha256"] = "0" * 64
        with self.assertRaises(ProbeError): disposable_restore_probe(**a)

    def test_04_current_sha256_tampered(self):
        a = self.args(); a["current_sha256"] = "f" * 64
        with self.assertRaises(ProbeError): disposable_restore_probe(**a)

    def test_05_git_blob_pin_mismatch(self):
        a = self.args(); a["prior_git_blob_sha1"] = "1" * 40
        with self.assertRaises(ProbeError): disposable_restore_probe(**a)

    def test_06_path_traversal_denied(self):
        a = self.args(); a["target"] = "../../another_project.py"
        with self.assertRaises(ProbeError): disposable_restore_probe(**a)

    def test_07_unapproved_target_denied(self):
        a = self.args(); a["target"] = "private_module.py"
        with self.assertRaises(ProbeError): disposable_restore_probe(**a)

    def test_08_oversized_bytes_denied(self):
        a = self.args(); a["prior_bytes"] = b"X" * 100001
        a["prior_sha256"] = digest(a["prior_bytes"])
        with self.assertRaises(ProbeError): disposable_restore_probe(**a)

    def test_09_candidate_identical_to_prior_denied(self):
        a = self.args(); a["candidate_bytes"] = a["prior_bytes"]
        a["candidate_sha256"] = a["prior_sha256"]
        with self.assertRaises(ProbeError): disposable_restore_probe(**a)

    def test_10_claimed_commit_must_be_full_hex(self):
        a = self.args(); a["claimed_prior_commit"] = "HEAD"
        with self.assertRaises(ProbeError): disposable_restore_probe(**a)

    def test_11_input_bytes_required(self):
        a = self.args(); a["prior_bytes"] = bytearray(a["prior_bytes"])
        with self.assertRaises(ProbeError): disposable_restore_probe(**a)

    def test_12_does_not_touch_nearby_operating_db(self):
        with tempfile.TemporaryDirectory(prefix="UCIE_W10_TEST_") as root:
            guard = Path(root) / "public_miner.sqlite3"
            guard.write_bytes(b"SENTINEL-UNCHANGED")
            before = guard.read_bytes()
            disposable_restore_probe(**self.args())
            self.assertEqual(guard.read_bytes(), before)

    def test_13_second_exact_first_party_basename(self):
        a = self.args(); a["target"] = "capability_trials.py"
        self.assertTrue(disposable_restore_probe(**a)[
            "disposable_candidate_staged_and_prior_bytes_restored"])
        self.assertEqual(ALLOWED_TARGETS,
                         frozenset(("library_exact_index.py", "capability_trials.py")))

    def test_14_git_blob_calculation_includes_binary_header_and_nulls(self):
        before = b"\x00\xff\r\n"
        self.assertEqual(git_blob_sha1(before), __import__("hashlib").sha1(
            b"blob 4\0\x00\xff\r\n").hexdigest())
        with self.assertRaises(ProbeError): git_blob_sha1(b"")

    @unittest.skipUnless(SOURCE_FILE.is_file(),
                         "requires complete UCIE source checkout (CI validates)")
    def test_15_exact_ucie_existing_source_matches_independently_pinned_hashes(self):
        # The checkout may have Windows CRLF smudge; only the committed
        # Git object (never the working-tree bytes) is a Git source pin.
        # All Git invocations are fixed, read-only and repo-scoped.
        git_target = "src/ucie_miner/library_exact_index.py"
        tree = subprocess.run(
            ["git", "rev-parse", "HEAD:" + git_target],
            cwd=UCIE_REPO, check=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=10).stdout.decode("ascii").strip()
        self.assertEqual(tree, PINNED_GIT_BLOB_SHA1)
        data = subprocess.run(
            ["git", "cat-file", "blob", PINNED_GIT_BLOB_SHA1],
            cwd=UCIE_REPO, check=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=10).stdout
        self.assertEqual(digest(data), PINNED_SOURCE_SHA256)
        self.assertEqual(git_blob_sha1(data), PINNED_GIT_BLOB_SHA1)
        # A harmless fabricated candidate can be restored in TEMP from
        # exact UCIE source bytes; it is never a proposed executable patch.
        synthetic_candidate = data + b"\n# UCIE synthetic revision preview only\n"
        out = disposable_restore_probe(
            target="library_exact_index.py",
            prior_bytes=data, prior_sha256=PINNED_SOURCE_SHA256,
            prior_git_blob_sha1=PINNED_GIT_BLOB_SHA1,
            candidate_bytes=synthetic_candidate,
            candidate_sha256=digest(synthetic_candidate),
            current_bytes=data, current_sha256=PINNED_SOURCE_SHA256,
            claimed_prior_commit=PINNED_GIT_COMMIT)
        self.assertTrue(out["prior_git_blob_identity_matches_caller_pin"])
        self.assertFalse(out["claimed_commit_contains_blob_independently_verified"])
        self.assertFalse(out["prior_bytes_authenticated_as_actual_prechange"])
        self.assertFalse(out["customer_release_authorized"])


if __name__ == "__main__":
    unittest.main()
