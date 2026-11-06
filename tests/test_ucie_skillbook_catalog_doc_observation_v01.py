"""UCIE-only synthetic byte observations in actual local read-only catalog.

No upstream fetch, owner project filesystem inspection, credentials, approval,
DB writes or release. Observation bytes are synthetic and NOT official evidence.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from http.server import HTTPServer
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ucie_miner import skillbook_catalog_union_v01 as catalog
from ucie_miner import skillbook_editorial_production_v01 as editor
from ucie_miner import skillbook_official_doc_observation_v01 as obs


class CatalogDocumentObservationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("/UCIE_SYNTHETIC_ONLY")
        self.pilot = editor.compose_curated_two_book_pilot()
        self.raw = b"<html><body>os.scandir " + b"synthetic doc byte. " * 9 + b"</body></html>"

    def _observation(self):
        with patch.object(obs, "_get_raw_official_bytes",
                          return_value=(self.raw, "text/html")):
            return obs.observe_official_document_once(
                "doc:python/cpython", owner_opt_in=True)

    def test_default_source_not_observed_on_browser_get(self):
        report = catalog.inspect_review_candidate(self.pilot["draft_sha256"])
        self.assertEqual(
            {row["status"] for row in report["source_observation_statuses"]},
            {"NO_MANUAL_RAW_BYTE_OBSERVATION"})
        self.assertFalse(report["browser_performs_official_network_fetch"])
        self.assertFalse(report["source_content_independently_verified"])
        self.assertIn("원문 바이트 관측 미실시",
                      catalog.render_review_candidate(report))

    def test_raw_observation_mismatch_is_visible_and_blocked(self):
        receipt = self._observation()
        report = catalog.inspect_review_candidate(
            self.pilot["draft_sha256"], editorial_observations=(receipt,))
        states = {x["source_id"]: x for x in report["source_observation_statuses"]}
        self.assertEqual(states["doc:python/cpython"]["status"],
                         "OBSERVED_BODY_SHA_MISMATCH_BLOCKED")
        self.assertEqual(states["doc:git/git"]["status"],
                         "NO_MANUAL_RAW_BYTE_OBSERVATION")
        self.assertFalse(report["observation_receipts_cryptographically_authenticated"])
        self.assertFalse(report["manual_editorial_review_completed"])
        self.assertFalse(report["export_allowed"])
        html = catalog.render_review_candidate(report)
        self.assertIn("제출 SHA와 관측 SHA 불일치 · 차단", html)
        self.assertNotIn("synthetic doc byte", html)

    def test_matching_bytes_still_require_version_and_independent_review(self):
        receipt = self._observation()
        record = deepcopy(self.pilot["authoring_input"])
        for source in record["sources"]:
            if source["source_id"] == "doc:python/cpython":
                source["evidence_sha256"] = sha256(self.raw).hexdigest()
        draft = editor.compile_review_draft(record)
        report = catalog.inspect_review_candidate(
            draft["draft_sha256"], editorial_records=(record,),
            editorial_observations=(receipt,))
        states = {x["source_id"]: x for x in report["source_observation_statuses"]}
        self.assertTrue(states["doc:python/cpython"]["byte_sha_equal"])
        self.assertFalse(states["doc:python/cpython"]["source_revision_verified"])
        self.assertFalse(states["doc:python/cpython"]
                         ["receipt_authenticity_cryptographically_verified"])
        self.assertFalse(report["source_content_independently_verified"])
        self.assertFalse(report["export_allowed"])
        self.assertIn("관측 SHA 일치",
                      catalog.render_review_candidate(report))

    def test_catalog_search_shows_mismatch_but_w04_stays_unread(self):
        r = self._observation()
        report = catalog.search_federated(
            self.root, filters=dict(catalog.parse_filters(""),
                                    query="BOUNDED_METADATA"),
            public_reader=lambda *_a, **_kw: self.fail("unrequested W04"),
            editorial_observations=(r,))
        self.assertEqual(len(report["editorial_review_candidates"]), 1)
        self.assertIn("원문 바이트 SHA 불일치 후보 · 차단",
                      catalog.render_federated(report))
        self.assertFalse(report["export_allowed"])
        self.assertEqual(report["network_requests"], 0)

    def test_forged_receipt_approval_fields_rejected(self):
        r = self._observation()
        for field, value in (("signed", True),
                             ("source_revision_verified", True),
                             ("export_allowed", True),
                             ("observed_raw_sha256", "wrong"),
                             ("source_url", "https://evil.invalid"),
                             ("human_approved", True)):
            with self.subTest(field=field):
                altered = deepcopy(r)
                altered[field] = value
                with self.assertRaises(catalog.FederationError):
                    catalog.inspect_review_candidate(
                        self.pilot["draft_sha256"],
                        editorial_observations=(altered,))
        with self.assertRaises(catalog.FederationError):
            catalog.inspect_review_candidate(
                self.pilot["draft_sha256"], editorial_observations=(r,r))

    def test_local_http_index_detail_json_never_fetches_official_document(self):
        r = self._observation()
        handler = catalog.make_handler(
            self.root, editorial_observations=(r,),
            public_reader=lambda *_a, **_kw: self.fail("no W04 reads"))
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            base = "http://127.0.0.1:" + str(server.server_port)
            def fetch(path, host=None):
                req = Request(base+path,
                    headers={} if host is None else {"Host": host})
                try:
                    with urlopen(req, timeout=6) as response:
                        return response.status, response.read().decode("utf-8")
                except HTTPError as error:
                    with error:
                        return error.code, error.read().decode("utf-8")
            try:
                with patch.object(obs, "observe_official_document_once",
                    side_effect=AssertionError("GET must not fetch source")):
                    status, page = fetch("/catalog?q=BOUNDED_METADATA")
                    self.assertEqual(status, 200)
                    self.assertIn("SHA 불일치", page)
                    status, page = fetch("/catalog/review?id=" +
                                         self.pilot["draft_sha256"])
                    self.assertEqual(status, 200)
                    self.assertIn("불일치 · 차단", page)
                    status, raw = fetch("/catalog/review.json?id=" +
                                        self.pilot["draft_sha256"])
                    self.assertEqual(status, 200)
                    data = json.loads(raw)
                    self.assertFalse(data["browser_performs_official_network_fetch"])
                    self.assertEqual(data["network_requests"], 0)
                    self.assertFalse(data["source_content_independently_verified"])
                    self.assertEqual(len(data["source_observation_statuses"]), 2)
                    self.assertEqual(fetch("/catalog?verify=true")[0], 400)
                    self.assertEqual(fetch("/catalog/review?network=true")[0], 400)
                    self.assertEqual(fetch("/catalog/review.json?id=" +
                                     self.pilot["draft_sha256"],
                                     host="invalid.invalid")[0], 403)
            finally:
                server.shutdown()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
