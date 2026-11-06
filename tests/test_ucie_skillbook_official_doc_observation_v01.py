"""Offline UCIE official-document exact-byte observation, draft-match gate tests.

All HTTP bodies are ORIGINAL SYNTHETIC BYTES. No test contacts upstream,
changes source policy, writes owner files, approves a book or runs external code.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
import json
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

from ucie_miner import skillbook_official_doc_observation_v01 as obs
from ucie_miner import skillbook_editorial_production_v01 as editor
from ucie_miner.public_evidence_routes import DOC_ENDPOINTS


class FakeHTTPResponse:
    def __init__(self, url, raw, *, status=200, content_type="text/html",
                 encoding=None, length=None, redirected_to=None):
        self._url = redirected_to if redirected_to is not None else url
        self._raw = raw
        self.status = status
        self.headers = {
            "Content-Type": content_type,
            "Content-Encoding": encoding if encoding is not None else "identity",
        }
        if length is not None:
            self.headers["Content-Length"] = length
        self.read_calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def geturl(self):
        return self._url

    def read(self, cap):
        self.read_calls.append(cap)
        return self._raw[:cap]


class _Opener:
    def __init__(self, result):
        self.result = result
        self.requests = []

    def open(self, request, *, timeout):
        self.requests.append((request, timeout))
        return self.result


class OfficialDocumentObservationTests(unittest.TestCase):
    def setUp(self):
        self.source = "doc:python/cpython"
        self.url = DOC_ENDPOINTS["python/cpython"][0]
        # UCIE-authored HTML fixture; NOT official source bytes or a real SHA.
        self.body = (b"<!doctype html><html><body>os.scandir "
                     + b"synthetic official marker fixture." * 8
                     + b"</body></html>")
        self.pilot = editor.compose_curated_two_book_pilot()
        self.expected_sha = sha256(self.body).hexdigest()

    def _fake_live(self, fake):
        opener = _Opener(fake)
        self.addCleanup(patch.stopall)
        patch.object(obs.urllib.request, "build_opener",
                     return_value=opener).start()
        return opener

    def _observed(self):
        opener = self._fake_live(
            FakeHTTPResponse(self.url, self.body, length=str(len(self.body))))
        result = obs.observe_official_document_once(self.source, owner_opt_in=True)
        self.assertEqual(len(opener.requests), 1)
        request, timeout = opener.requests[0]
        self.assertEqual(request.full_url, self.url)
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(timeout, 12)
        self.assertEqual(request.get_header("Accept-encoding"), "identity")
        self.assertIsNone(request.get_header("Authorization"))
        return result

    def test_exact_observed_raw_bytes_sha_and_no_source_text_reprint(self):
        r = self._observed()
        self.assertEqual(r["schema"], obs.SCHEMA)
        self.assertEqual(r["source_url"], self.url)
        self.assertEqual(r["source_id"], self.source)
        self.assertEqual(r["observed_raw_sha256"], self.expected_sha)
        self.assertEqual(r["observed_raw_bytes"], len(self.body))
        self.assertTrue(r["exact_url_no_redirect"])
        self.assertTrue(r["topic_marker_found"])
        self.assertEqual(r["http_status"], 200)
        self.assertFalse(r["source_revision_verified"])
        self.assertFalse(r["document_technical_claims_verified"])
        self.assertFalse(r["source_authority_independently_attested"])
        self.assertFalse(r["license_redistribution_approved"])
        self.assertFalse(r["owner_release_approved"])
        self.assertFalse(r["export_allowed"])
        self.assertFalse(r["raw_body_redistributed"])
        self.assertEqual(r["network_requests"], 1)
        self.assertEqual(r["operating_database_writes"], 0)
        self.assertNotIn("synthetic official marker fixture", json.dumps(r))
        self.assertEqual(datetime.fromisoformat(r["observed_at_utc"]).utcoffset(),
                         timezone.utc.utcoffset(None))

    def test_cli_requires_separate_explicit_network_opt_in(self):
        with patch.object(obs, "observe_official_document_once",
                          side_effect=AssertionError("network must not be entered")):
            buffer = StringIO()
            with redirect_stdout(buffer):
                result = obs.main(["--source", self.source])
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(buffer.getvalue())["status"],
                         "OWNER_NETWORK_OPT_IN_REQUIRED_NO_GO")

    def test_manual_cli_one_command_compares_curated_claim_to_observed_bytes(self):
        from io import StringIO
        out = StringIO()
        with patch.object(obs, "_get_raw_official_bytes",
                          return_value=(self.body, "text/html")):
            with redirect_stdout(out):
                code = obs.main(["--source", self.source, "--confirm-network",
                                 "--compare-curated"])
        self.assertEqual(code, 0)
        receipt = json.loads(out.getvalue())
        self.assertEqual(receipt["observation"]["observed_raw_sha256"],
                         self.expected_sha)
        self.assertEqual(receipt["comparison"]["source_id"], self.source)
        self.assertEqual(receipt["comparison"]["status"],
                         "INCOMPARABLE_PINNED_SOURCE_VS_LIVE_HTML_REVIEW_REQUIRED")
        self.assertFalse(receipt["comparison"]["human_approved"])
        self.assertFalse(receipt["comparison"]["export_allowed"])

        with patch.object(obs, "_get_raw_official_bytes",
                          side_effect=AssertionError("cannot read unsupported book")):
            out = StringIO()
            with redirect_stdout(out):
                code = obs.main([
                    "--source", "doc:PowerShell/PowerShell",
                    "--confirm-network", "--compare-curated"])
            self.assertEqual(code, 3)
            self.assertEqual(json.loads(out.getvalue())["status"],
                             "SOURCE_OBSERVATION_FAIL_CLOSED")

    def test_only_exact_registered_official_url_and_scope(self):
        with self.assertRaises(obs.OfficialDocumentObservationError):
            obs._get_raw_official_bytes("https://docs.python.org/3/library/os.html?x=1")
        with self.assertRaises(obs.OfficialDocumentObservationError):
            obs._get_raw_official_bytes("http://127.0.0.1/private")
        with self.assertRaises(obs.OfficialDocumentObservationError):
            obs._get_raw_official_bytes("https://example.com")
        for source in (
            "repo:python/cpython", "doc:unknown/private",
            "research:Software Heritage", "doc:python/cpython/../unknown",
            "doc:OtherProject/Repo", 123,
        ):
            with self.subTest(source=source):
                with self.assertRaises(obs.OfficialDocumentObservationError):
                    obs.observe_official_document_once(
                        source, owner_opt_in=True)
        for value in (False, None, 0, "yes"):
            with self.subTest(approval=value):
                with self.assertRaises(obs.OfficialDocumentObservationError):
                    obs.observe_official_document_once(self.source, owner_opt_in=value)

    def test_redirect_http_error_wrong_mime_compressed_and_oversized_blocked(self):
        variants = [
            {"status": 302},
            {"redirected_to": "https://evil.invalid/capture"},
            {"content_type": "text/plain"},
            {"encoding": "gzip"},
            {"length": str(obs.MAX_SOURCE_BYTES + 1)},
            {"length": "invalid"},
        ]
        for variant in variants:
            with self.subTest(variant=variant):
                resp = FakeHTTPResponse(self.url, self.body, **variant)
                with patch.object(obs.urllib.request, "build_opener",
                                  return_value=_Opener(resp)):
                    with self.assertRaises(obs.OfficialDocumentObservationError):
                        obs.observe_official_document_once(
                            self.source, owner_opt_in=True)

    def test_bounded_single_read_and_malformed_body_rejected(self):
        for body in (b"", b"a" * 127,
                     b"<!doctype html>" + b"x" * 180,
                     b"<html><body>os.scandir" + b"\xff" * 160,
                     b"<!doctype html>os.scandir"
                     + b"A" * (obs.MAX_SOURCE_BYTES + 1)):
            with self.subTest(length=len(body)):
                response = FakeHTTPResponse(self.url, body)
                with patch.object(obs.urllib.request, "build_opener",
                                  return_value=_Opener(response)):
                    with self.assertRaises(obs.OfficialDocumentObservationError):
                        obs.observe_official_document_once(
                            self.source, owner_opt_in=True)
                self.assertTrue(all(n == obs.MAX_SOURCE_BYTES + 1
                                    for n in response.read_calls))

    def test_only_informational_observation_can_match_claimed_sha(self):
        r = self._observed()
        observation = obs.compare_editorial_source_to_observation(self.pilot, r)
        self.assertEqual(observation["status"],
                         "INCOMPARABLE_PINNED_SOURCE_VS_LIVE_HTML_REVIEW_REQUIRED")
        self.assertIsNone(observation["byte_sha_equal"])
        self.assertFalse(observation["digest_material_comparable"])
        self.assertEqual(observation["pinned_source_tag"], "v3.15.0")
        self.assertEqual(observation["pinned_source_path"], "Doc/library/os.rst")
        self.assertFalse(observation["technical_claims_reviewed"])
        self.assertFalse(observation["receipt_authenticity_cryptographically_verified"])
        self.assertFalse(observation["source_revision_verified"])
        self.assertFalse(observation["export_allowed"])

        record = deepcopy(self.pilot["authoring_input"])
        for item in record["sources"]:
            if item["source_id"] == self.source:
                item["evidence_sha256"] = self.expected_sha
        claimed = editor.compile_review_draft(record)
        equal = obs.compare_editorial_source_to_observation(claimed, r)
        self.assertIsNone(equal["byte_sha_equal"])
        self.assertFalse(equal["digest_material_comparable"])
        self.assertEqual(equal["status"],
                         "INCOMPARABLE_UNDECLARED_MATERIAL_REVIEW_REQUIRED")
        self.assertFalse(equal["source_origin_independently_attested"])
        self.assertFalse(equal["receipt_authenticity_cryptographically_verified"])
        self.assertFalse(equal["human_approved"])
        self.assertFalse(equal["source_revision_verified"])
        self.assertFalse(equal["released"])

    def test_manual_check_binds_only_matching_source_after_opt_in(self):
        self._fake_live(FakeHTTPResponse(self.url, self.body))
        result = obs.manual_check_candidate_source(
            self.pilot, self.source, owner_opt_in=True)
        self.assertEqual(result["observation"]["observed_raw_sha256"],
                         self.expected_sha)
        self.assertEqual(result["comparison"]["draft_sha256"],
                         self.pilot["draft_sha256"])
        self.assertEqual(result["comparison"]["status"],
                         "INCOMPARABLE_PINNED_SOURCE_VS_LIVE_HTML_REVIEW_REQUIRED")
        self.assertFalse(result["comparison"]["human_approved"])

    def test_missing_source_fails_before_network(self):
        with patch.object(obs.urllib.request, "build_opener",
                          side_effect=AssertionError("must not fetch unrelated doc")):
            with self.assertRaises(obs.OfficialDocumentObservationError):
                obs.manual_check_candidate_source(
                    self.pilot, "doc:PowerShell/PowerShell",
                    owner_opt_in=True)

    def test_replay_receipt_cannot_assert_signed_or_approved_knowledge(self):
        r = self._observed()
        for key, value in (
            ("source_revision_verified", True),
            ("source_authority_independently_attested", True),
            ("document_technical_claims_verified", True),
            ("license_redistribution_approved", True),
            ("signed", True), ("export_allowed", True),
            ("released", True), ("network_requests", 0),
            ("source_url", "https://evil.invalid"),
            ("observed_raw_sha256", "0"),
        ):
            with self.subTest(key=key):
                edited = dict(r, **{key: value})
                with self.assertRaises(obs.OfficialDocumentObservationError):
                    obs.compare_editorial_source_to_observation(self.pilot, edited)
        extraneous = dict(r)
        extraneous["approved"] = True
        with self.assertRaises(obs.OfficialDocumentObservationError):
            obs.compare_editorial_source_to_observation(self.pilot, extraneous)

    def test_forged_draft_and_wrong_observed_source_denied(self):
        r = self._observed()
        forged = deepcopy(self.pilot)
        forged["export_allowed"] = True
        with self.assertRaises(obs.OfficialDocumentObservationError):
            obs.compare_editorial_source_to_observation(forged, r)
        forged = deepcopy(self.pilot)
        forged["sources"][0]["evidence_sha256"] = self.expected_sha
        with self.assertRaises(obs.OfficialDocumentObservationError):
            obs.compare_editorial_source_to_observation(forged, r)
        valid_other = editor.compose_curated_two_book_pilot()
        record = deepcopy(valid_other["authoring_input"])
        doc = next(s for s in record["sources"] if s["source_id"] != self.source)
        record["sources"] = [doc]
        for ch in record["chapters"]:
            ch["source_ids"] = [doc["source_id"]]
        other = editor.compile_review_draft(record)
        with self.assertRaises(obs.OfficialDocumentObservationError):
            obs.compare_editorial_source_to_observation(other, r)

    def test_body_changes_produce_different_exact_sha(self):
        original = self._observed()
        changed = self.body + b"<p>one extra byte</p>"
        with patch.object(obs.urllib.request, "build_opener",
                          return_value=_Opener(
                              FakeHTTPResponse(self.url, changed))):
            b = obs.observe_official_document_once(
                self.source, owner_opt_in=True)
        self.assertNotEqual(original["observed_raw_sha256"],
                            b["observed_raw_sha256"])
        self.assertNotEqual(original["observed_raw_bytes"],
                            b["observed_raw_bytes"])
        self.assertFalse(b["source_revision_verified"])


if __name__ == "__main__":
    unittest.main()
