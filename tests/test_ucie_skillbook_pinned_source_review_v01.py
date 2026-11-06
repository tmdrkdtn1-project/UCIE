"""UCIE-only offline source pin, revision proposals and safe persistent review.

No network, no release, no operating database, no third-party sources.
All writable fixtures use a disposable directory literally named UCIE.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import skillbook_pinned_source_review_v01 as review


class PinnedSourceReviewTests(unittest.TestCase):
    def setUp(self):
        self.source_id = "doc:python/cpython"
        self.raw = b"hello world\n"
        self.expected_sha256 = sha256(self.raw).hexdigest()
        self.expected_git_blob = "3b18e512dba79e4c8300dd08aeb37f8e728b8dad"
        self.assertEqual(
            sha1(b"blob 12\0" + self.raw).hexdigest(),
            self.expected_git_blob)
        original = review._pinned_book(self.source_id)
        self.synthetic = deepcopy(original)
        source = self.synthetic["source_evidence"]
        source["source_document_sha256"] = self.expected_sha256
        source["source_document_git_blob_sha1"] = self.expected_git_blob
        self.synthetic["library_entry"]["evidence_sha256"] = self.expected_sha256

    def _build(self):
        with patch.object(review, "_pinned_book", return_value=self.synthetic):
            verified = review.verify_pinned_raw_bytes(self.source_id, self.raw)
            proposed = review.propose_source_review(verified)
        return verified, proposed

    def test_existing_python_git_pins_are_exact_and_disallowed_to_promote(self):
        for sid, tag, source_file, source_sha, git_sha in (
            ("doc:python/cpython", "v3.15.0", "Doc/library/os.rst",
             "9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a",
             "74419ee7f3588f1baec83c85b05716e6388719e3"),
            ("doc:git/git", "v2.51.0", "Documentation/git-status.adoc",
             "1cdd1c7339dfc64093687b6e072d59feee584b8639c0203ece0a1150ce23d325",
             "9a376886a5867a63d173d85162c57027f336f915"),
        ):
            with self.subTest(sid=sid):
                book = review._pinned_book(sid)
                evidence = book["source_evidence"]
                self.assertEqual(evidence["source_tag"], tag)
                self.assertEqual(evidence["source_file"], source_file)
                self.assertEqual(evidence["source_document_sha256"], source_sha)
                self.assertEqual(evidence["source_document_git_blob_sha1"], git_sha)
                self.assertFalse(book["export_allowed"])
                self.assertEqual(book["library_entry"]["approval_status"],
                                 "NOT_APPROVED")

    def test_synthetic_known_git_blob_and_sha_produces_only_proposal(self):
        verified, proposed = self._build()
        self.assertEqual(verified["status"],
                         "PINNED_SOURCE_FILE_DIGESTS_MATCH_ORIGIN_REVIEW_PENDING")
        self.assertEqual(verified["source_size_bytes"], len(self.raw))
        self.assertEqual(verified["observed_raw_sha256"], self.expected_sha256)
        self.assertEqual(verified["observed_git_blob_sha1"], self.expected_git_blob)
        self.assertTrue(verified["sha256_equal"])
        self.assertTrue(verified["git_blob_sha1_equal"])
        self.assertTrue(verified["pinned_bytes_match"])
        self.assertFalse(verified["origin_authenticated_independently"])
        self.assertFalse(verified["source_tag_signature_verified"])
        self.assertFalse(verified["technical_claim_reviewed"])
        self.assertFalse(verified["human_approved"])
        self.assertFalse(verified["export_allowed"])
        self.assertFalse(verified["released"])
        self.assertEqual(proposed["recommended_action"],
                         "KEEP_CURRENT_PIN_REVIEW_ORIGIN_AND_TECHNICAL_CLAIMS")
        self.assertFalse(proposed["release_allowed"])
        self.assertFalse(proposed["withdrawal_executed"])
        self.assertFalse(proposed["human_approval_granted"])
        self.assertEqual(len(proposed["event_id"]), 64)

    def test_wrong_tag_file_contents_require_revalidation_not_auto_withdraw(self):
        original = review.verify_pinned_raw_bytes(self.source_id, self.raw)
        self.assertEqual(original["source_tag"], "v3.15.0")
        self.assertEqual(original["source_file"], "Doc/library/os.rst")
        self.assertFalse(original["pinned_bytes_match"])
        self.assertFalse(original["export_allowed"])
        self.assertFalse(original["auto_withdrawn"])
        self.assertFalse(original["auto_promoted"])
        proposed = review.propose_source_review(original)
        self.assertEqual(proposed["recommended_action"],
                         "HOLD_RELEASE_AND_REVALIDATE_INPUT_NO_AUTO_WITHDRAWAL")
        self.assertFalse(proposed["withdrawal_executed"])
        self.assertFalse(proposed["release_allowed"])

    def test_never_accept_html_version_as_tagged_source(self):
        raw = b"<html><body>os.scandir " + b"rendered content " * 12 + b"</body></html>"
        report = review.verify_pinned_raw_bytes("doc:python/cpython", raw)
        self.assertEqual(report["source_material_kind"],
                         "VERSION_TAGGED_REPO_SOURCE_FILE_RAW_BYTES")
        self.assertNotEqual(report["observed_raw_sha256"],
                            report["expected_raw_sha256"])
        self.assertFalse(report["pinned_bytes_match"])
        self.assertFalse(report["human_approved"])
        self.assertFalse(report["export_allowed"])

    def test_unknown_source_and_unbounded_bytes_fail_closed(self):
        for value in ("doc:other/unknown", "repo:python/cpython", "",
                      "../offlimits", "doc:PowerShell/PowerShell"):
            with self.subTest(value=value):
                with self.assertRaises(review.SourceReviewError):
                    review.verify_pinned_raw_bytes(value, self.raw)
        for value in (b"", b"x" * (review.MAX_SOURCE_BYTES + 1), "hello"):
            with self.subTest(size=len(value)):
                with self.assertRaises(review.SourceReviewError):
                    review.verify_pinned_raw_bytes(self.source_id, value)

    def test_approval_forgery_or_raw_digest_mutation_rejected_in_proposal(self):
        verified, _ = self._build()
        for k, value in (
            ("export_allowed", True), ("human_approved", True),
            ("source_tag_signature_verified", True),
            ("pinned_bytes_match", False),
            ("expected_git_blob_sha1", "0" * 40),
            ("observed_raw_sha256", "0" * 64),
            ("network_requests", 1),
            ("source_tag", "v9.9.9"),
        ):
            forged = deepcopy(verified)
            forged[k] = value
            with self.subTest(field=k):
                with patch.object(review, "_pinned_book", return_value=self.synthetic):
                    with self.assertRaises(review.SourceReviewError):
                        review.propose_source_review(forged)

    def test_journal_append_and_replay_idempotence(self):
        verified = review.verify_pinned_raw_bytes(self.source_id, self.raw)
        event = review.propose_source_review(verified)
        empty = review.inspect_review_journal(b"")
        self.assertEqual(empty["total_events"], 0)
        first, receipt = review.extend_review_journal(b"", event)
        self.assertEqual(receipt["status"], "REVIEW_EVENT_PREPARED_NOT_APPROVED")
        self.assertFalse(receipt["approved_or_released"])
        decoded = review.inspect_review_journal(first)
        self.assertEqual(decoded["total_events"], 1)
        self.assertEqual(decoded["events"], [event])
        self.assertEqual(decoded["last_hash"], receipt["last_hash"])
        same, repeat = review.extend_review_journal(first, event)
        self.assertEqual(first, same)
        self.assertEqual(repeat["status"], "ALREADY_RECORDED_NO_DUPLICATE")
        self.assertEqual(repeat["total_events"], 1)

        observed = deepcopy(verified)
        observed["observed_raw_sha256"] = "b" * 64
        observed["sha256_equal"] = False
        observed["status"] = "PINNED_SOURCE_FILE_DIGESTS_DIFFER_REVALIDATION_REQUIRED"
        other = review.propose_source_review(
            observed, note="An extra observed source digest for manual review.")
        second, result = review.extend_review_journal(first, other)
        self.assertEqual(result["total_events"], 2)
        final = review.inspect_review_journal(second)
        self.assertEqual(final["events"], [event, other])
        self.assertNotEqual(final["last_hash"], decoded["last_hash"])

    def test_hash_chain_detects_tampering_truncation_and_reordering(self):
        verified = review.verify_pinned_raw_bytes(self.source_id, self.raw)
        event = review.propose_source_review(verified)
        saved, receipt = review.extend_review_journal(b"", event)
        self.assertEqual(saved[-1:], b"\n")
        for tampered in (
            saved[:-1], saved.replace(b"review_note", b"review_forged"),
            saved.replace(event["event_id"].encode(), b"0" * 64),
            saved + saved,
            b'{"sequence":1}\n',
            b"x" * (review.MAX_JOURNAL_BYTES + 1),
        ):
            with self.subTest(length=len(tampered)):
                with self.assertRaises(review.SourceReviewError):
                    review.inspect_review_journal(tampered)

    def test_event_forged_release_and_approval_flags_blocked(self):
        source = review.verify_pinned_raw_bytes(self.source_id, self.raw)
        event = review.propose_source_review(source)
        for key in ("release_allowed", "withdrawal_executed",
                    "human_approval_granted", "automatic_promotion"):
            forged = deepcopy(event)
            forged[key] = True
            forged.pop("event_id")
            forged["event_id"] = sha256(review._canonical_json(forged)).hexdigest()
            with self.subTest(key=key):
                with self.assertRaises(review.SourceReviewError):
                    review.extend_review_journal(b"", forged)

    def test_ucie_named_isolated_inbox_and_atomic_journal_write(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "UCIE"
            root.mkdir()
            runtime = root / "runtime"
            runtime.mkdir()
            folder = runtime / "skillbook_manual_review"
            folder.mkdir()
            fixture = folder / review.INBOX[self.source_id]
            fixture.write_bytes(self.raw)
            with patch.object(review, "_pinned_book", return_value=self.synthetic):
                verified = review.verify_ucie_inbox(root, self.source_id)
                proposed = review.propose_source_review(verified)
                self.assertTrue(verified["pinned_bytes_match"])
                with self.assertRaises(review.SourceReviewError):
                    review.persist_review_event(root, proposed)
                self.assertFalse((folder / review.REVIEW_FILE).exists())
                committed = review.persist_review_event(
                    root, proposed, owner_opt_in=True)
                self.assertEqual(
                    committed["status"],
                    "ISOLATED_REVIEW_EVENT_COMMITTED_NOT_APPROVED")
                target = folder / review.REVIEW_FILE
                decoded = review.inspect_review_journal(target.read_bytes())
                self.assertEqual(decoded["total_events"], 1)
                repeated = review.persist_review_event(
                    root, proposed, owner_opt_in=True)
                self.assertEqual(repeated["status"], "ALREADY_RECORDED_NO_DUPLICATE")
                self.assertEqual(
                    review.inspect_review_journal(target.read_bytes())["total_events"], 1)
            self.assertFalse((folder / (review.REVIEW_FILE + ".lock")).exists())

    def test_ucie_only_path_rejects_alias_and_non_inbox_read(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "UCIE"
            (root / "runtime" / "skillbook_manual_review").mkdir(parents=True)
            other = Path(td) / "other-project"
            other.mkdir()
            with self.assertRaises(review.SourceReviewError):
                review.persist_review_event(other, {}, owner_opt_in=True)
            with self.assertRaises(review.SourceReviewError):
                review.verify_ucie_inbox(root, self.source_id)
            file_path = root / "runtime" / "skillbook_manual_review" / review.INBOX[self.source_id]
            file_path.write_bytes(self.raw)
            with self.assertRaises(review.SourceReviewError):
                review.verify_ucie_inbox(root, "doc:another/source")

    def test_symlinked_source_input_and_journal_are_rejected(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unsupported")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "UCIE"
            box = root / "runtime" / "skillbook_manual_review"
            box.mkdir(parents=True)
            unrelated = Path(td) / "other.txt"
            unrelated.write_bytes(self.raw)
            link = box / review.INBOX[self.source_id]
            try:
                link.symlink_to(unrelated)
            except (OSError, NotImplementedError):
                self.skipTest("cannot create symlink under this OS policy")
            with self.assertRaises(review.SourceReviewError):
                review.verify_ucie_inbox(root, self.source_id)
            verified = review.verify_pinned_raw_bytes(self.source_id, self.raw)
            event = review.propose_source_review(verified)
            target = box / review.REVIEW_FILE
            target.symlink_to(unrelated)
            with self.assertRaises(review.SourceReviewError):
                review.persist_review_event(root, event, owner_opt_in=True)

    def test_cli_requires_explicit_authorization_for_write(self):
        # The CLI only reads the exact UCIE inbox; it cannot fetch the internet.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "UCIE"
            box = root / "runtime" / "skillbook_manual_review"
            box.mkdir(parents=True)
            (box / review.INBOX[self.source_id]).write_bytes(self.raw)
            with patch.object(review.Path, "cwd", return_value=root):
                with patch.object(review, "_pinned_book", return_value=self.synthetic):
                    from contextlib import redirect_stdout
                    from io import StringIO
                    out = StringIO()
                    with redirect_stdout(out):
                        code = review.main(["--source", self.source_id])
                    self.assertEqual(code, 0)
                    receipt = json.loads(out.getvalue())
                    self.assertEqual(receipt["files_written"], 0)
                    self.assertFalse((box / review.REVIEW_FILE).exists())
                    with redirect_stdout(StringIO()):
                        exit_code = review.main([
                            "--source", self.source_id, "--record-review"])
                    self.assertEqual(exit_code, 2)
                    self.assertFalse((box / review.REVIEW_FILE).exists())


if __name__ == "__main__":
    unittest.main()
