"""UCIE V1: one-shot original-byte official document observation and binding.

This is NOT a new source allowlist or miner. An owner explicitly opts into
one HTTPS GET of an exact already-allowlisted official documentation URL.
Only bounded, non-reprinted raw-body SHA-256 metadata is retained. Source
version, content truth, origin authenticity, license and QA remain unapproved.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
import urllib.error
import urllib.request

from .core import MiningError, NoRedirect
from .public_evidence_routes import (
    DOC_ENDPOINTS, MAX_DOC_BYTES, PublicEvidenceError, inspect_official_document,
)
from .source_registry import get_source, SourceRegistryError
from .skillbook_editorial_production_v01 import (
    compile_review_draft, EditorialDraftError,
)

SCHEMA = "UCIE_OFFICIAL_DOC_RAW_BYTES_OBSERVATION_V01"
BINDING_SCHEMA = "UCIE_SKILLBOOK_DOC_BYTE_COMPARISON_V01"
OBSERVED = "MANUAL_EXACT_HTTPS_BYTE_OBSERVATION_NO_REVISION_ATTESTATION"
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
MAX_SOURCE_BYTES = MAX_DOC_BYTES
GET_TIMEOUT_SECONDS = 12


class OfficialDocumentObservationError(ValueError):
    """Fail closed on unauthorised routes and unverifiable byte responses."""


def _registered_official_url(source_id: str) -> tuple[str, str, str]:
    """Never derive host or path from a caller-supplied URL."""
    if type(source_id) is not str or not source_id.startswith("doc:"):
        raise OfficialDocumentObservationError("only registered official document ids")
    try:
        source = get_source(source_id)
    except SourceRegistryError as exc:
        raise OfficialDocumentObservationError("unapproved or unknown source") from exc
    repo = source_id[4:]
    route = DOC_ENDPOINTS.get(repo)
    if (type(route) is not tuple or len(route) != 2
            or source["status"] != "ACTIVE_APPROVED"
            or source["source_kind"] != "OFFICIAL_PUBLIC_DOCUMENT"
            or source["existing_method"] != "EXISTING_PINNED_OFFICIAL_DOC"
            or source["fetch_authorized_by_this_registry"] is not False
            or source["public_url"] != route[0]
            or not route[0].startswith("https://")):
        raise OfficialDocumentObservationError("official endpoint or scope drift")
    return repo, route[0], route[1]


def _get_raw_official_bytes(url: str) -> tuple[bytes, str]:
    """Existing exact official-document route. No redirection, auth or upload."""
    if url not in {item[0] for item in DOC_ENDPOINTS.values()}:
        raise OfficialDocumentObservationError("URL outside existing approved routes")
    req = urllib.request.Request(
        url, method="GET", headers={
            "Accept": "text/html",
            "Accept-Encoding": "identity",
            "User-Agent": "UCIE-PUBLIC-EVIDENCE/0.1",
        },
    )
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=GET_TIMEOUT_SECONDS) as response:
            if response.status != 200 or response.geturl() != url:
                raise OfficialDocumentObservationError(
                    "HTTP status or redirected URL invalid")
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
            content_type = content_type.strip().lower()
            if content_type != "text/html":
                raise OfficialDocumentObservationError(
                    "unexpected official document MIME type")
            encoding = response.headers.get("Content-Encoding", "").strip().lower()
            if encoding not in ("", "identity"):
                raise OfficialDocumentObservationError(
                    "compressed response would change wire byte identity")
            length = response.headers.get("Content-Length")
            if length is not None:
                if (not length.isdigit()
                        or int(length) > MAX_SOURCE_BYTES):
                    raise OfficialDocumentObservationError(
                        "declared document length exceeds budget")
            body = response.read(MAX_SOURCE_BYTES + 1)
    except (urllib.error.URLError, urllib.error.HTTPError, MiningError,
            OSError, TimeoutError, ValueError) as exc:
        if isinstance(exc, OfficialDocumentObservationError):
            raise
        raise OfficialDocumentObservationError(
            "approved official document request failed or redirected") from exc
    if type(body) is not bytes or not 128 <= len(body) <= MAX_SOURCE_BYTES:
        raise OfficialDocumentObservationError(
            "empty, truncated or oversized official document")
    return body, content_type


def observe_official_document_once(source_id: str, *, owner_opt_in: bool = False) -> dict:
    """One bounded manual network request; returns ONLY raw-byte digest metadata."""
    if owner_opt_in is not True:
        raise OfficialDocumentObservationError("explicit per-request opt-in required")
    repo, url, required_topic = _registered_official_url(source_id)
    raw, content_type = _get_raw_official_bytes(url)
    try:
        text = raw.decode("utf-8", errors="strict")
        inspected = inspect_official_document(repo, text)
    except (UnicodeError, PublicEvidenceError) as exc:
        raise OfficialDocumentObservationError(
            "unsupported encoding or malformed official document") from exc
    digest = sha256(raw).hexdigest()
    if (inspected["official_url"] != url
            or inspected["required_topic"].casefold() != required_topic.casefold()
            or inspected["topic_marker_found"] is not True
            or inspected["sha256"] != digest
            or inspected["document_authenticity_attested"] is not False):
        raise OfficialDocumentObservationError(
            "document topic/byte fingerprint contract failed")
    return {
        "schema": SCHEMA, "status": OBSERVED,
        "source_id": source_id, "source_url": url,
        "required_topic": required_topic,
        "observed_raw_sha256": digest,
        "observed_raw_bytes": len(raw),
        "observed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "http_status": 200, "response_content_type": content_type,
        "exact_url_no_redirect": True, "topic_marker_found": True,
        "content_encoding": "identity",
        "source_revision_status": "MUTABLE_URL_NO_IMMUTABLE_VERSION_ATTESTED",
        "source_revision_verified": False,
        "source_authority_independently_attested": False,
        "document_technical_claims_verified": False,
        "license_redistribution_approved": False,
        "independent_qa_verified": False, "owner_release_approved": False,
        "signed": False, "export_allowed": False, "released": False,
        "owner_manual_network_opt_in": True,
        "raw_text_retained": False, "raw_body_redistributed": False,
        "network_requests": 1, "operating_database_writes": 0,
        "other_project_access": False,
    }


def _check_receipt(receipt: dict) -> dict:
    """Check shape and scope, but do NOT authenticate an unsigned receipt."""
    if type(receipt) is not dict:
        raise OfficialDocumentObservationError("unknown receipt object")
    source_id = receipt.get("source_id")
    _, url, topic = _registered_official_url(source_id)
    try:
        at = datetime.fromisoformat(receipt["observed_at_utc"])
    except (ValueError, TypeError, KeyError) as exc:
        raise OfficialDocumentObservationError("invalid observation timestamp") from exc
    if (set(receipt) != {
            "schema", "status", "source_id", "source_url", "required_topic",
            "observed_raw_sha256", "observed_raw_bytes", "observed_at_utc",
            "http_status", "response_content_type", "exact_url_no_redirect",
            "topic_marker_found", "content_encoding", "source_revision_status",
            "source_revision_verified", "source_authority_independently_attested",
            "document_technical_claims_verified",
            "license_redistribution_approved", "independent_qa_verified",
            "owner_release_approved", "signed", "export_allowed", "released",
            "owner_manual_network_opt_in", "raw_text_retained",
            "raw_body_redistributed", "network_requests",
            "operating_database_writes", "other_project_access",
        }
            or receipt.get("schema") != SCHEMA
            or receipt.get("status") != OBSERVED
            or receipt.get("source_url") != url
            or receipt.get("required_topic") != topic
            or type(receipt.get("observed_raw_sha256")) is not str
            or DIGEST.fullmatch(receipt["observed_raw_sha256"]) is None
            or type(receipt.get("observed_raw_bytes")) is not int
            or not 128 <= receipt["observed_raw_bytes"] <= MAX_SOURCE_BYTES
            or at.utcoffset() is None or at.utcoffset().total_seconds() != 0
            or receipt.get("http_status") != 200
            or receipt.get("response_content_type") != "text/html"
            or receipt.get("exact_url_no_redirect") is not True
            or receipt.get("topic_marker_found") is not True
            or receipt.get("content_encoding") != "identity"
            or receipt.get("source_revision_status")
               != "MUTABLE_URL_NO_IMMUTABLE_VERSION_ATTESTED"
            or any(receipt.get(k) is not False for k in (
                "source_revision_verified",
                "source_authority_independently_attested",
                "document_technical_claims_verified",
                "license_redistribution_approved",
                "independent_qa_verified", "owner_release_approved",
                "signed", "export_allowed", "released", "raw_text_retained",
                "raw_body_redistributed", "other_project_access"))
            or receipt.get("owner_manual_network_opt_in") is not True
            or type(receipt.get("network_requests")) is not int
            or receipt["network_requests"] != 1
            or type(receipt.get("operating_database_writes")) is not int
            or receipt["operating_database_writes"] != 0):
        raise OfficialDocumentObservationError(
            "unknown, altered or claimed-promoted public observation")
    return receipt


def compare_editorial_source_to_observation(draft: dict, receipt: dict) -> dict:
    """Observe supplied SHA equality only; do not assert signed provenance."""
    if (type(draft) is not dict
            or type(draft.get("authoring_input")) is not dict):
        raise OfficialDocumentObservationError("untrusted editorial draft")
    try:
        canonical = compile_review_draft(draft["authoring_input"])
    except (EditorialDraftError, KeyError, TypeError) as exc:
        raise OfficialDocumentObservationError(
            "invalid editorial draft identity") from exc
    if draft != canonical:
        raise OfficialDocumentObservationError("edited or promoted draft rejected")
    r = _check_receipt(receipt)
    matches = [s for s in draft["sources"]
               if s["source_id"] == r["source_id"]]
    if len(matches) != 1 or matches[0]["public_url"] != r["source_url"]:
        raise OfficialDocumentObservationError(
            "receipt source not part of candidate's official document evidence")
    item = matches[0]
    equal = item["evidence_sha256"] == r["observed_raw_sha256"]
    return {
        "schema": BINDING_SCHEMA,
        "status": ("OBSERVED_BODY_SHA_MATCH_REVISION_UNVERIFIED"
                   if equal else "OBSERVED_BODY_SHA_MISMATCH_BLOCKED"),
        "draft_sha256": draft["draft_sha256"],
        "source_id": r["source_id"], "official_url": r["source_url"],
        "submitted_evidence_sha256": item["evidence_sha256"],
        "observed_raw_sha256": r["observed_raw_sha256"],
        "observed_at_utc": r["observed_at_utc"],
        "observed_raw_bytes": r["observed_raw_bytes"],
        "byte_sha_equal": equal,
        "exact_endpoint_route_checked": True,
        "source_revision_verified": False,
        "source_origin_independently_attested": False,
        "technical_claims_reviewed": False,
        "receipt_authenticity_cryptographically_verified": False,
        "manual_editorial_review_completed": False,
        "independent_qa_verified": False, "human_approved": False,
        "license_redistribution_approved": False, "security_approved": False,
        "signed": False, "export_allowed": False, "released": False,
        "external_source_code_executed": False,
        "operating_database_writes": 0,
    }


def manual_check_candidate_source(
        draft: dict, source_id: str, *, owner_opt_in: bool = False) -> dict:
    """Connect actual manual HTTPS observation to a particular draft source."""
    if (type(draft) is not dict or type(draft.get("authoring_input")) is not dict):
        raise OfficialDocumentObservationError("untrusted source-bound draft")
    try:
        expected = compile_review_draft(draft["authoring_input"])
    except (EditorialDraftError, KeyError, TypeError) as exc:
        raise OfficialDocumentObservationError("invalid candidate") from exc
    if (draft != expected
            or not any(s["source_id"] == source_id for s in draft["sources"])):
        raise OfficialDocumentObservationError(
            "candidate source not authorized for manual read")
    observation = observe_official_document_once(
        source_id, owner_opt_in=owner_opt_in)
    result = compare_editorial_source_to_observation(draft, observation)
    return {"observation": observation, "comparison": result}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE manual exact approved official document raw SHA observation")
    parser.add_argument("--source", choices=["doc:" + x for x in DOC_ENDPOINTS],
                        required=True)
    parser.add_argument("--confirm-network", action="store_true")
    parser.add_argument("--compare-curated", action="store_true")
    args = parser.parse_args(argv)
    if not args.confirm_network:
        print(json.dumps({"schema": SCHEMA, "status": "OWNER_NETWORK_OPT_IN_REQUIRED_NO_GO"}))
        return 2
    try:
        if args.compare_curated:
            from .skillbook_editorial_production_v01 import compose_curated_two_book_pilot
            result = manual_check_candidate_source(
                compose_curated_two_book_pilot(), args.source,
                owner_opt_in=True)
        else:
            result = observe_official_document_once(
                args.source, owner_opt_in=True)
    except OfficialDocumentObservationError:
        print(json.dumps({"schema": SCHEMA, "status": "SOURCE_OBSERVATION_FAIL_CLOSED"}))
        return 3
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
