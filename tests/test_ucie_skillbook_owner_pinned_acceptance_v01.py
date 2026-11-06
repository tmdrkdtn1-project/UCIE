"""UCIE V1 one-shot pinned source acceptance end-to-end first-party tests.

Uses synthetic public API response bytes and a disposable UCIE review root.
NO live external requests, no real owner runtime DB, no credentials, no
automatic source promotion, no release or access to another project.
"""
from __future__ import annotations

import base64
from contextlib import redirect_stdout
from copy import deepcopy
from hashlib import sha1, sha256
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from ucie_miner import skillbook_owner_pinned_acceptance_v01 as accept
from ucie_miner import skillbook_pinned_source_review_v01 as review
from ucie_miner import skillbook_catalog_union_v01 as catalog


class _Response:
    def __init__(self, url, body, headers=None, status=200, redirect=None):
        self.expected_url = redirect or url
        self.status = status
        self.headers = headers or {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Encoding": "identity",
            "Content-Length": str(len(body)),
        }
        self.body = body
        self.closed = False
    def geturl(self):
        return self.expected_url
    def read(self, length):
        return self.body[:length]
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        self.closed = True


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.sid = "doc:python/cpython"
        self.raw = b"UCIE synthetic public source fixture\nos.scandir\n"
        self.raw_sha256 = sha256(self.raw).hexdigest()
        self.raw_blob_sha1 = sha1(
            b"blob " + str(len(self.raw)).encode("ascii") + b"\0" +
            self.raw).hexdigest()
        book = review._pinned_book(self.sid)
        self.synthetic_book = deepcopy(book)
        self.synthetic_book["source_evidence"][
            "source_document_sha256"] = self.raw_sha256
        self.synthetic_book["source_evidence"][
            "source_document_git_blob_sha1"] = self.raw_blob_sha1
        self.synthetic_book["library_entry"][
            "evidence_sha256"] = self.raw_sha256
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.owner = Path(self.temp.name) / "UCIE"
        self.owner.mkdir()
        (self.owner / "runtime").mkdir()
        self.source_guard = patch.object(
            review, "_pinned_book", return_value=self.synthetic_book)
        self.source_guard.start()
        self.addCleanup(self.source_guard.stop)
        self.root_guard = patch.object(
            review, "_owner_root", return_value=self.owner.resolve(strict=True))
        self.root_guard.start()
        self.addCleanup(self.root_guard.stop)

    def _url(self):
        return accept.exact_blob_url(self.sid)

    def _api(self, raw=None, sha=None, size=None, url=None):
        payload = self.raw if raw is None else raw
        result = {
            "sha": self.raw_blob_sha1 if sha is None else sha,
            "encoding": "base64",
            "size": len(payload) if size is None else size,
            "content": base64.b64encode(payload).decode("ascii"),
            "url": self._url() if url is None else url,
        }
        return json.dumps(result, sort_keys=True).encode("ascii")

    def test_only_two_registered_official_public_repo_blobs(self):
        with patch.stopall if False else patch.object(
            review, "_pinned_book", side_effect=None):
            pass
        for sid in (self.sid, "doc:git/git"):
            # Production pin (no synthetic SHA override) is required.
            real = (
                __import__("ucie_miner.skillbook_product_v01",
                           fromlist=["build_skillbook"]).build_skillbook()
                if sid == self.sid else
                __import__("ucie_miner.skillbook_git_porcelain_product_v01",
                           fromlist=["build_skillbook"]).build_skillbook()
            )
            with patch.object(review, "_pinned_book", return_value=real):
                url = accept.exact_blob_url(sid)
            self.assertTrue(url.startswith("https://api.github.com/repos/"))
            self.assertIn("/git/blobs/", url)
            self.assertTrue(url.endswith(
                real["source_evidence"]["source_document_git_blob_sha1"]))
        for sid in ("", "doc:PowerShell/PowerShell", "repo:python/cpython",
                    "doc:other/repo", "https://example.org", "../private"):
            with self.subTest(sid=sid):
                with self.assertRaises(accept.AcceptanceError):
                    accept.exact_blob_url(sid)

    def test_original_pins_cannot_be_replaced_with_unregistered_url(self):
        with self.assertRaises(accept.AcceptanceError):
            accept._fetch_pinned_blob_json(
                "https://api.github.com/repos/other/private/git/blobs/" + "0"*40)
        with self.assertRaises(accept.AcceptanceError):
            accept._fetch_pinned_blob_json(
                "http://api.github.com/repos/python/cpython/git/blobs/" +
                self.raw_blob_sha1)

    def test_mocked_public_http_fetch_reads_one_exact_limited_response(self):
        url = self._url()
        blob = self._api()
        fake = _Response(url, blob)
        class Opener:
            def __init__(self):
                self.calls = []
            def open(self, req, timeout):
                self.calls.append((req.full_url, req.get_method(), timeout))
                return fake
        opener = Opener()
        with patch.object(accept.urllib.request, "build_opener",
                          return_value=opener):
            data = accept._fetch_pinned_blob_json(url)
        self.assertEqual(data, blob)
        self.assertEqual(opener.calls, [(url, "GET", accept.TIMEOUT_SECONDS)])
        self.assertTrue(fake.closed)
        self.assertEqual(
            accept.decode_exact_blob_response(self.sid, data), self.raw)

    def test_http_redirect_wrong_type_encoding_and_oversized_fail_closed(self):
        url = self._url()
        blob = self._api()
        fixtures = [
            _Response(url, blob, status=304),
            _Response(url, blob, redirect="https://unapproved.invalid"),
            _Response(url, blob, headers={
                "Content-Type": "text/html", "Content-Encoding": "identity",
            }),
            _Response(url, blob, headers={
                "Content-Type": "application/json", "Content-Encoding": "gzip",
            }),
            _Response(url, blob, headers={
                "Content-Type": "application/json",
                "Content-Length": str(accept.MAX_API_RESPONSE_BYTES+1),
            }),
            _Response(url, b"x"*(accept.MAX_API_RESPONSE_BYTES+1)),
        ]
        class Opener:
            def __init__(self, response):
                self.response = response
            def open(self, req, timeout):
                return self.response
        for fake in fixtures:
            with self.subTest(response=fake.expected_url, status=fake.status):
                with patch.object(accept.urllib.request, "build_opener",
                                  return_value=Opener(fake)):
                    with self.assertRaises(accept.AcceptanceError):
                        accept._fetch_pinned_blob_json(url)

    def test_transport_error_is_not_promoted_to_accepted_receipt(self):
        class Opener:
            def open(self, req, timeout):
                raise urllib.error.URLError("simulated offline")
        with patch.object(accept.urllib.request, "build_opener",
                          return_value=Opener()):
            with self.assertRaises(accept.AcceptanceError):
                accept._fetch_pinned_blob_json(self._url())

    def test_invalid_content_raw_sha_unexpected_json_and_duplicate_keys(self):
        bad = [
            b"not json",
            b'{"sha":"a","sha":"b"}',
            self._api(sha="0"*40),
            self._api(size=len(self.raw)+1),
            self._api(url="https://unapproved.invalid"),
            json.dumps({
                "sha": self.raw_blob_sha1, "encoding": "binary",
                "size": len(self.raw), "content": "abc",
            }).encode("ascii"),
            b"x"*(accept.MAX_API_RESPONSE_BYTES+1),
        ]
        for blob in bad:
            with self.subTest(length=len(blob)):
                with self.assertRaises(accept.AcceptanceError):
                    accept.decode_exact_blob_response(self.sid, blob)

    def test_wrong_raw_bytes_with_bogus_recomputed_sha_still_blocked(self):
        corrupted = self.raw + b"tamper"
        payload = self._api(raw=corrupted)
        with patch.object(accept, "_fetch_pinned_blob_json",
                          return_value=payload):
            with self.assertRaises(accept.AcceptanceError):
                accept.accept_one_exact_source(
                    self.sid, owner_root=self.owner, confirm_network=True)
        self.assertFalse(
            (self.owner/"runtime"/"skillbook_manual_review").exists())

    def test_default_network_denied_before_any_request(self):
        with patch.object(accept, "_fetch_pinned_blob_json",
                          side_effect=AssertionError("network prohibited")):
            with self.assertRaises(accept.AcceptanceError):
                accept.accept_one_exact_source(
                    self.sid, owner_root=self.owner)
        self.assertFalse(
            (self.owner/"runtime"/"skillbook_manual_review").exists())

    def test_network_confirmation_and_journal_confirmation_are_separate(self):
        with patch.object(accept, "_fetch_pinned_blob_json",
                          side_effect=AssertionError("GET must not occur")):
            for write, consent in ((True, False), (False, True)):
                with self.subTest(write=write, consent=consent):
                    with self.assertRaises(accept.AcceptanceError):
                        accept.accept_one_exact_source(
                            self.sid, owner_root=self.owner,
                            confirm_network=True, record_review=write,
                            confirm_review_write=consent)

    def test_successful_read_only_network_acceptance_does_not_write(self):
        with patch.object(accept, "_fetch_pinned_blob_json",
                          return_value=self._api()):
            receipt = accept.accept_one_exact_source(
                self.sid, owner_root=self.owner, confirm_network=True)
        self.assertEqual(
            receipt["status"], "RAW_PUBLIC_GIT_BLOB_MATCHES_PIN_NOT_RELEASE_APPROVED")
        self.assertEqual(receipt["sha256"], self.raw_sha256)
        self.assertEqual(receipt["git_blob_sha1"], self.raw_blob_sha1)
        self.assertTrue(receipt["source_bytes_sha256_and_git_blob_match"])
        self.assertFalse(receipt["review_journal_written"])
        self.assertFalse(receipt["catalog_reference_checked"])
        self.assertFalse(receipt["source_origin_independently_attested"])
        self.assertFalse(receipt["human_approved"])
        self.assertFalse(receipt["export_allowed"])
        self.assertFalse(receipt["released"])
        self.assertEqual(receipt["operating_database_writes"], 0)
        self.assertFalse(
            (self.owner/"runtime"/"skillbook_manual_review").exists())

    def test_manual_optin_journal_to_w04_receipt_is_verified(self):
        verified = review.verify_pinned_raw_bytes(self.sid, self.raw)
        event = review.propose_source_review(verified)
        from ucie_miner import skillbook_catalog_union_v01 as catalog
        def linked(*_args, **kwargs):
            snapshot = review.inspect_review_journal(
                kwargs["pinned_review_history"])
            self.assertEqual(snapshot["events"][-1]["event_id"], event["event_id"])
            return {
                "pinned_source_review_statuses": [{
                    "source_id": self.sid,
                    "review_event_id": event["event_id"],
                    "status": "PINNED_RAW_SOURCE_HASHES_MATCH_UNAUTHENTICATED",
                }],
                "export_allowed": False,
            }
        with patch.object(accept, "_fetch_pinned_blob_json",
                          return_value=self._api()):
            with patch.object(catalog, "inspect_review_candidate",
                              side_effect=linked):
                receipt = accept.accept_one_exact_source(
                    self.sid, owner_root=self.owner, confirm_network=True,
                    record_review=True, confirm_review_write=True)
        self.assertEqual(
            receipt["status"], "SOURCE_VERIFIED_REVIEW_JOURNAL_AND_W04_LINKED_NOT_APPROVED")
        self.assertEqual(
            receipt["review_journal_status"],
            "ISOLATED_REVIEW_EVENT_COMMITTED_NOT_APPROVED")
        self.assertTrue(receipt["review_journal_written"])
        self.assertTrue(receipt["catalog_reference_checked"])
        self.assertEqual(receipt["review_event_id"], event["event_id"])
        self.assertEqual(receipt["review_journal_total_events"], 1)
        self.assertFalse(receipt["human_approved"])
        self.assertFalse(receipt["export_allowed"])
        self.assertEqual(receipt["network_requests"], 1)
        self.assertEqual(
            review.inspect_review_journal(
                review.read_isolated_review_journal(self.owner)
            )["total_events"], 1)

    def test_repeated_one_shot_is_idempotent_no_duplicate(self):
        from ucie_miner import skillbook_catalog_union_v01 as catalog
        original = self._api()
        event = review.propose_source_review(
            review.verify_pinned_raw_bytes(self.sid, self.raw))
        with patch.object(accept, "_fetch_pinned_blob_json",
                          return_value=original):
            with patch.object(catalog, "inspect_review_candidate",
                              return_value={
                                  "pinned_source_review_statuses": [{
                                      "source_id": self.sid,
                                      "review_event_id": event["event_id"],
                                      "status":
                                          "PINNED_RAW_SOURCE_HASHES_MATCH_UNAUTHENTICATED",
                                  }],
                                  "export_allowed": False,
                              }):
                first = accept.accept_one_exact_source(
                    self.sid, owner_root=self.owner, confirm_network=True,
                    record_review=True, confirm_review_write=True)
                second = accept.accept_one_exact_source(
                    self.sid, owner_root=self.owner, confirm_network=True,
                    record_review=True, confirm_review_write=True)
        self.assertTrue(first["review_journal_written"])
        self.assertFalse(second["review_journal_written"])
        self.assertEqual(second["review_journal_status"],
                         "ALREADY_RECORDED_NO_DUPLICATE")
        self.assertEqual(second["review_journal_total_events"], 1)

    def test_catalog_ref_disagreement_fails_closed_without_forging_approval(self):
        from ucie_miner import skillbook_catalog_union_v01 as catalog
        with patch.object(accept, "_fetch_pinned_blob_json",
                          return_value=self._api()):
            with patch.object(catalog, "inspect_review_candidate",
                              return_value={
                                  "pinned_source_review_statuses": [],
                                  "export_allowed": False,
                              }):
                with self.assertRaises(accept.AcceptanceError):
                    accept.accept_one_exact_source(
                        self.sid, owner_root=self.owner, confirm_network=True,
                        record_review=True, confirm_review_write=True)
        event_bytes = review.read_isolated_review_journal(self.owner)
        self.assertEqual(review.inspect_review_journal(event_bytes)["total_events"], 1)
        # The event is an unsigned pending advisory and must not be erased or
        # presented as an accepted product when catalog linking fails.

    def test_main_requires_opt_in_and_failure_contains_no_source_material(self):
        with patch.object(accept.Path, "cwd", return_value=self.owner):
            out = StringIO()
            with redirect_stdout(out):
                code = accept.main(["--source", self.sid])
        self.assertEqual(code, 3)
        status = json.loads(out.getvalue())
        self.assertFalse(status["export_allowed"])
        self.assertFalse(status["released"])
        self.assertNotIn("UCIE synthetic public source", out.getvalue())

    def test_original_owner_root_guard_applies_on_windows(self):
        if review.os.name != "nt":
            self.skipTest("Windows D:/UCIE root guard only")
        with patch.stopall if False else patch.object(
                review, "_owner_root", wraps=review._owner_root) as original:
            # Patch explicitly disabled while using this synthetic path.
            original.side_effect = review.SourceReviewError("not D:/UCIE")
            with patch.object(accept, "_fetch_pinned_blob_json",
                              side_effect=AssertionError("network must not start")):
                with self.assertRaises(accept.AcceptanceError):
                    accept.accept_one_exact_source(
                        self.sid, owner_root=self.owner, confirm_network=True)


if __name__ == "__main__":
    unittest.main()
