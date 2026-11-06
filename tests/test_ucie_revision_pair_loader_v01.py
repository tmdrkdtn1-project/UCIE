"""Owner opt-in, read-only manuscript pair loader for an actual local W04 UI.

All inputs and filesystem writes are in a disposable synthetic UCIE root.
Tests never read the real D:/UCIE runtime or contact external endpoints.
"""
from __future__ import annotations

from copy import deepcopy
from http.server import HTTPServer
from contextlib import redirect_stdout
from io import StringIO
import json
import sys
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

from ucie_miner import skillbook_catalog_union_v01 as catalog
from ucie_miner import skillbook_editorial_production_v01 as editorial
from ucie_miner import skillbook_revision_review_v01 as revision
from ucie_miner import skillbook_pinned_source_review_v01 as pinned


class ExactRevisionPairLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        self.folder = self.root / "runtime" / "skillbook_manual_review"
        self.folder.mkdir(parents=True)
        self.path = self.folder / revision.REVISION_PAIR_NAME
        self.before = editorial.compose_curated_two_book_pilot()
        self.a = deepcopy(self.before["authoring_input"])
        self.b = deepcopy(self.a)
        self.b["previous_revision"] = self.before["draft_sha256"]
        self.b["draft_version"] = "0.1.1-draft"
        self.b["revision_note"] = (
            "Owner-only review of a new bounded technical claim.")
        self.b["chapters"][3]["body"] += (
            " This altered failure mode needs a new negative test.")
        self.body = {"previous": self.a, "candidate": self.b}
        self.root_guard = patch.object(
            pinned, "_owner_root", return_value=self.root.resolve(strict=True))
        self.root_guard.start()
        self.addCleanup(self.root_guard.stop)

    def _write(self, data=None):
        self.path.write_bytes(json.dumps(
            self.body if data is None else data,
            ensure_ascii=True, sort_keys=True).encode("ascii"))

    def test_exact_root_filename_is_loaded_without_any_change(self):
        self._write()
        old_bytes = self.path.read_bytes()
        previous, candidate = revision.read_review_pair(self.root)
        self.assertEqual(previous["draft_sha256"], self.before["draft_sha256"])
        self.assertEqual(candidate["revision"]["previous_draft_sha256_claim"],
                         previous["draft_sha256"])
        self.assertEqual(candidate["draft_version"], "0.1.1-draft")
        self.assertEqual(self.path.read_bytes(), old_bytes)
        self.assertEqual(
            editorial.compare_review_revisions(
                previous, candidate)["changed_chapter_ids"],
            ["COUNTEREXAMPLES"])
        self.assertFalse(candidate["export_allowed"])

    def test_missing_named_file_and_alias_fail_closed(self):
        with self.assertRaises(editorial.EditorialDraftError):
            revision.read_review_pair(self.root)
        self._write()
        moved = self.folder / "different.json"
        self.path.rename(moved)
        with self.assertRaises(editorial.EditorialDraftError):
            revision.read_review_pair(self.root)

    def test_reject_extra_keys_approval_and_wrong_parent(self):
        for mutate in (
            lambda p: p.update({"approval": True}),
            lambda p: p["candidate"].update({"signed": True}),
            lambda p: p["candidate"].update({"previous_revision": "0"*64}),
            lambda p: p["candidate"]["sources"][0].update({"admin_key": "yes"}),
        ):
            content = deepcopy(self.body)
            mutate(content)
            self._write(content)
            with self.assertRaises(editorial.EditorialDraftError):
                revision.read_review_pair(self.root)

    def test_reject_duplicate_json_fields_and_overlarge_payload(self):
        self.path.write_bytes(b'{"previous":{},"candidate":{},"candidate":{}}')
        with self.assertRaises(editorial.EditorialDraftError):
            revision.read_review_pair(self.root)
        self.path.write_bytes(b"x" * (revision.MAX_REVISION_PAIR_BYTES+1))
        with self.assertRaises(editorial.EditorialDraftError):
            revision.read_review_pair(self.root)

    def test_symlink_input_to_unrelated_file_rejected(self):
        other = Path(self.temp.name) / "other-source.json"
        other.write_text(json.dumps(self.body), encoding="utf-8")
        try:
            self.path.symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest("cannot create symlink under local policy")
        with self.assertRaises(editorial.EditorialDraftError):
            revision.read_review_pair(self.root)

    def test_actual_catalog_cli_flag_selects_exact_review_pair(self):
        """No HTTP bind: exercise CLI routing and owner opt-in switch."""
        previous = self.before
        candidate = editorial.compile_review_draft(self.b)
        seen = {}
        class FakeServer:
            server_port = 49152
            def __init__(self, bind, handler):
                seen["bind"] = bind
                seen["handler"] = handler
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def serve_forever(self, **_kwargs):
                raise KeyboardInterrupt()
        with patch.object(sys, "argv", [
                "catalog", "--port", "0", "--revision-review-file"]):
            with patch.object(catalog.revision_review, "read_review_pair",
                              return_value=(previous, candidate)) as loader:
                with patch.object(catalog.pinned_review,
                                  "read_isolated_review_journal",
                                  return_value=b""):
                    with patch.object(catalog, "HTTPServer", FakeServer):
                        buf = StringIO()
                        with redirect_stdout(buf):
                            result = catalog.main()
        actual = Path(catalog.__file__).resolve().parents[2]
        owner_root_allowed = (
            actual.name.casefold() == "ucie"
            and not actual.is_symlink() and actual.is_dir()
            and (catalog.os.name != "nt"
                 or actual.resolve() == Path("D:/UCIE").resolve()))
        text = json.loads(buf.getvalue())
        if owner_root_allowed:
            self.assertEqual(result, 0)
            self.assertEqual(seen["bind"], ("127.0.0.1", 0))
            self.assertTrue(loader.called)
            self.assertTrue(text["revision_review_file_loaded"])
            self.assertEqual(text["approved_packages"], 0)
            self.assertFalse(text["export_allowed"])
        else:
            # GitHub Windows runners use D:/a/UCIE/UCIE, NOT the owner's D:/UCIE.
            # Refusal is the security feature, not a failed launch regression.
            self.assertEqual(result, 3)
            self.assertEqual(text["status"], "FAIL_CLOSED")
            self.assertFalse(loader.called)
            self.assertEqual(seen, {})

    def test_browsing_explicit_pair_returns_w09_retest_no_release(self):
        self._write()
        old, candidate = revision.read_review_pair(self.root)
        handler = catalog.make_handler(
            self.root, editorial_records=(candidate["authoring_input"],),
            previous_editorial_draft=old,
            public_reader=lambda *_a, **_k: self.fail("unexpected W04 read"))
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            base = "http://127.0.0.1:" + str(server.server_port)
            try:
                with urlopen(base + "/catalog?q=BOUNDED_METADATA", timeout=6) as response:
                    html = response.read().decode("utf-8")
                self.assertIn("/catalog/review?id=" + candidate["draft_sha256"], html)
                with urlopen(base + "/catalog/review.json?id=" +
                             candidate["draft_sha256"], timeout=6) as response:
                    report = json.loads(response.read())
                impact = report["revision_review_impact"]
                self.assertEqual(impact["changed_chapter_ids"], ["COUNTEREXAMPLES"])
                self.assertIn("COUNTEREXAMPLES", impact["recheck_chapter_ids"])
                self.assertFalse(impact["owner_approval_granted"])
                self.assertEqual(impact["journal_event_count"], 0)
                self.assertFalse(report["export_allowed"])
            finally:
                server.shutdown()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
