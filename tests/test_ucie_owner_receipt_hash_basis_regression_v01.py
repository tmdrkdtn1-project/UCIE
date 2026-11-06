"""UCIE: reconcile the owner's supplied 2026-11-06 Python public-doc receipt.

This is a user-provided observation, *not* independently signed evidence.
No HTTP, files, OS environment, unknown repository or approval is accessed.
"""
from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from ucie_miner import skillbook_editorial_production_v01 as editorial
from ucie_miner import skillbook_official_doc_observation_v01 as source
from ucie_miner import skillbook_catalog_union_v01 as catalog
from ucie_miner.skillbook_product_v01 import SOURCE_DOCUMENT_SHA256


OWNER_REPORTED_OBSERVATION = {
    "schema": "UCIE_OFFICIAL_DOC_RAW_BYTES_OBSERVATION_V01",
    "status": "MANUAL_EXACT_HTTPS_BYTE_OBSERVATION_NO_REVISION_ATTESTATION",
    "source_id": "doc:python/cpython",
    "source_url": "https://docs.python.org/3/library/os.html",
    "required_topic": "os.scandir",
    "observed_raw_sha256":
        "c447c03a759513fa8f5d084954511235e6add13c6784d9b0894a033397c9a51c",
    "observed_raw_bytes": 791358,
    "observed_at_utc": "2026-11-06T03:21:39+00:00",
    "http_status": 200,
    "response_content_type": "text/html",
    "exact_url_no_redirect": True,
    "topic_marker_found": True,
    "content_encoding": "identity",
    "source_revision_status": "MUTABLE_URL_NO_IMMUTABLE_VERSION_ATTESTED",
    "source_revision_verified": False,
    "source_authority_independently_attested": False,
    "document_technical_claims_verified": False,
    "license_redistribution_approved": False,
    "independent_qa_verified": False,
    "owner_release_approved": False,
    "signed": False,
    "export_allowed": False,
    "released": False,
    "owner_manual_network_opt_in": True,
    "raw_text_retained": False,
    "raw_body_redistributed": False,
    "network_requests": 1,
    "operating_database_writes": 0,
    "other_project_access": False,
}


class OwnerReceiptHashBasisRegression(unittest.TestCase):
    def test_supplied_receipt_is_reconciled_without_network_or_approval(self):
        with patch.object(source, "observe_official_document_once",
                          side_effect=AssertionError("offline only")):
            draft = editorial.compose_curated_two_book_pilot()
            self.assertEqual(
                draft["draft_sha256"],
                "fbe539590dea7b0d3bf124abe0165571b35e56bf55510e37c6f46521b39f0be0")
            result = source.compare_editorial_source_to_observation(
                draft, OWNER_REPORTED_OBSERVATION)
        self.assertEqual(
            result["status"],
            "INCOMPARABLE_PINNED_SOURCE_VS_LIVE_HTML_REVIEW_REQUIRED")
        self.assertIsNone(result["byte_sha_equal"])
        self.assertFalse(result["digest_material_comparable"])
        self.assertTrue(result["legacy_mismatch_verdict_invalidated"])
        self.assertEqual(result["submitted_evidence_sha256"], SOURCE_DOCUMENT_SHA256)
        self.assertEqual(result["observed_raw_sha256"],
                         OWNER_REPORTED_OBSERVATION["observed_raw_sha256"])
        self.assertEqual(result["submitted_digest_material"],
                         "VERSION_TAG_PINNED_REPOSITORY_DOC_SOURCE_BYTES")
        self.assertEqual(result["observed_digest_material"],
                         "LIVE_RENDERED_HTML_RESPONSE_BODY_BYTES")
        self.assertEqual(result["pinned_source_tag"], "v3.15.0")
        self.assertEqual(result["pinned_source_path"], "Doc/library/os.rst")
        self.assertEqual(result["pinned_git_blob_sha1"],
                         "74419ee7f3588f1baec83c85b05716e6388719e3")
        self.assertFalse(result["source_file_digest_verified_by_this_receipt"])
        self.assertFalse(result["source_revision_verified"])
        self.assertFalse(result["receipt_authenticity_cryptographically_verified"])
        self.assertFalse(result["human_approved"])
        self.assertFalse(result["export_allowed"])

    def test_owner_receipt_observation_in_existing_catalog_is_not_sha_drift(self):
        draft = editorial.compose_curated_two_book_pilot()
        detail = catalog.inspect_review_candidate(
            draft["draft_sha256"],
            editorial_observations=(OWNER_REPORTED_OBSERVATION,))
        py = next(s for s in detail["source_observation_statuses"]
                  if s["source_id"] == "doc:python/cpython")
        self.assertEqual(
            py["status"], "INCOMPARABLE_PINNED_SOURCE_VS_LIVE_HTML_REVIEW_REQUIRED")
        self.assertIsNone(py["byte_sha_equal"])
        self.assertEqual(py["pinned_source_tag"], "v3.15.0")
        html = catalog.render_review_candidate(detail)
        self.assertIn("버전 고정 원문과 웹 HTML 비교 불가", html)
        self.assertIn("Doc/library/os.rst", html)
        self.assertFalse(detail["source_content_independently_verified"])
        self.assertFalse(detail["export_allowed"])

    def test_tampered_or_promoted_user_receipt_still_fails_closed(self):
        draft = editorial.compose_curated_two_book_pilot()
        for key, altered_value in (
            ("signed", True), ("source_revision_verified", True),
            ("observed_raw_sha256", "0" * 64),
            ("source_id", "doc:other/unknown"),
            ("source_url", "https://unapproved.invalid"),
        ):
            altered = deepcopy(OWNER_REPORTED_OBSERVATION)
            altered[key] = altered_value
            with self.subTest(key=key):
                if key == "observed_raw_sha256":
                    # Any well-formed unsigned SHA remains *untrusted*, not
                    # independently authenticated, even if syntactically valid.
                    result = source.compare_editorial_source_to_observation(
                        draft, altered)
                    self.assertFalse(result["receipt_authenticity_cryptographically_verified"])
                    self.assertIsNone(result["byte_sha_equal"])
                else:
                    with self.assertRaises(source.OfficialDocumentObservationError):
                        source.compare_editorial_source_to_observation(
                            draft, altered)


if __name__ == "__main__":
    unittest.main()
