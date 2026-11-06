"""UCIE V1 owner-only one-shot public pinned Git blob source acceptance.

One explicitly authorized HTTPS GET of *content-addressed* bytes from one
of the two already curated official public GitHub repositories. This adds
no general crawler/allowlist. All output is bounded metadata, not source.
Optional explicit owner-only review journal append is separate from the
network opt-in; no approval, signature, distribution or operating DB writes.
"""
from __future__ import annotations

import argparse
import base64
import binascii
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

from .core import MiningError, NoRedirect
from . import skillbook_pinned_source_review_v01 as pinned

SCHEMA = "UCIE_OWNER_PINNED_SOURCE_ONE_SHOT_ACCEPTANCE_V01"
MAX_API_RESPONSE_BYTES = 900_000
TIMEOUT_SECONDS = 15
MIME = frozenset(("application/json", "application/vnd.github+json"))
REPOS = {
    "doc:python/cpython": ("python/cpython", "v3.15.0", "Doc/library/os.rst"),
    "doc:git/git": ("git/git", "v2.51.0", "Documentation/git-status.adoc"),
}
SHA1_HEX = re.compile(r"[0-9a-f]{40}\Z")


class AcceptanceError(ValueError):
    """Fail closed for unpinned sources, bad transport or drifted bytes."""


def exact_blob_url(source_id: str) -> str:
    if type(source_id) is not str or source_id not in REPOS:
        raise AcceptanceError("only two previously approved public SkillBooks")
    book = pinned._pinned_book(source_id)
    origin = book["source_evidence"]
    repo, tag, path = REPOS[source_id]
    blob_sha = origin["source_document_git_blob_sha1"]
    if (origin["publisher"] != repo
            or origin["source_tag"] != tag
            or origin["source_file"] != path
            or type(blob_sha) is not str
            or SHA1_HEX.fullmatch(blob_sha) is None):
        raise AcceptanceError("first-party immutable source identity drift")
    return "https://api.github.com/repos/" + repo + "/git/blobs/" + blob_sha


def _unique_object(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise AcceptanceError("duplicate source response JSON key")
        data[key] = value
    return data


def _fetch_pinned_blob_json(url: str) -> bytes:
    # No caller-supplied URL. Content-addressed endpoint for exactly two
    # approved public repositories and first-party pinned Git blob hashes.
    if url not in {exact_blob_url(source) for source in REPOS}:
        raise AcceptanceError("GitHub route not one of the exact pinned blobs")
    req = urllib.request.Request(
        url, method="GET", headers={
            "Accept": "application/vnd.github+json",
            "Accept-Encoding": "identity",
            "User-Agent": "UCIE-PUBLIC-PINNED-SOURCE-ONE-SHOT/0.1",
        })
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=TIMEOUT_SECONDS) as response:
            content_type = response.headers.get(
                "Content-Type", "").split(";", 1)[0].lower().strip()
            encoding = response.headers.get(
                "Content-Encoding", "").lower().strip()
            declared = response.headers.get("Content-Length")
            if (response.status != 200 or response.geturl() != url
                    or content_type not in MIME
                    or encoding not in ("", "identity")
                    or (declared is not None and (
                        not declared.isdecimal()
                        or int(declared) > MAX_API_RESPONSE_BYTES))):
                raise AcceptanceError("unexpected GitHub blob HTTP response")
            payload = response.read(MAX_API_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, urllib.error.HTTPError,
            MiningError, OSError, TimeoutError) as exc:
        raise AcceptanceError("exact public pinned GitHub request failed") from exc
    if not 1 <= len(payload) <= MAX_API_RESPONSE_BYTES:
        raise AcceptanceError("source API response exceeds budget")
    return payload


def decode_exact_blob_response(source_id: str, payload: bytes) -> bytes:
    """Validate GitHub blob API envelope before extracting bounded raw bytes."""
    url = exact_blob_url(source_id)
    book = pinned._pinned_book(source_id)
    expected_sha = book["source_evidence"]["source_document_git_blob_sha1"]
    if type(payload) is not bytes or not 2 <= len(payload) <= MAX_API_RESPONSE_BYTES:
        raise AcceptanceError("bounded public blob JSON required")
    try:
        response = json.loads(
            payload.decode("utf-8", "strict"), object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError) as exc:
        raise AcceptanceError("invalid public pinned GitHub blob JSON") from exc
    if (type(response) is not dict
            or response.get("sha") != expected_sha
            or response.get("encoding") != "base64"
            or type(response.get("content")) is not str
            or type(response.get("size")) is not int
            or not 1 <= response["size"] <= pinned.MAX_SOURCE_BYTES):
        raise AcceptanceError("GitHub blob API identity, encoding or size drift")
    if "url" in response and response["url"] != url:
        raise AcceptanceError("GitHub blob self URL mismatch")
    compact = response["content"].replace("\n", "").replace("\r", "")
    if len(compact) > (4 * ((pinned.MAX_SOURCE_BYTES + 2) // 3)):
        raise AcceptanceError("base64 blob body budget exceeded")
    try:
        raw = base64.b64decode(compact, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise AcceptanceError("invalid raw blob base64") from exc
    if len(raw) != response["size"]:
        raise AcceptanceError("GitHub blob source size mismatch")
    return raw


def accept_one_exact_source(source_id: str, *,
                            owner_root: Path,
                            confirm_network: bool = False,
                            record_review: bool = False,
                            confirm_review_write: bool = False) -> dict:
    """One bounded source GET -> source SHA check -> optional journal -> W04.

    A *mismatch* aborts before optional disk writes and never promotes a
    SkillBook. On successful owner-opt-in journal append, the existing W04
    catalog view must resolve the exact event ID or return NO_GO.
    """
    if (confirm_network is not True
            or type(record_review) is not bool
            or type(confirm_review_write) is not bool
            or record_review != confirm_review_write):
        raise AcceptanceError("separate explicit network and journal options")
    if not isinstance(owner_root, Path):
        raise AcceptanceError("UCIE owner root Path required")
    # Enforces D:/UCIE on Windows; tests may substitute a disposable UCIE
    # fixture with a narrowly scoped _owner_root patch.
    try:
        root = pinned._owner_root(owner_root)
        url = exact_blob_url(source_id)
        raw = decode_exact_blob_response(
            source_id, _fetch_pinned_blob_json(url))
        verified = pinned.verify_pinned_raw_bytes(source_id, raw)
        if verified["pinned_bytes_match"] is not True:
            raise AcceptanceError("public pinned source SHA256/blob SHA1 mismatch")
        proposal = pinned.propose_source_review(verified)
        if proposal["pinned_bytes_match"] is not True:
            raise AcceptanceError("source verification review draft drift")
        result = {
            "schema": SCHEMA,
            "status": "RAW_PUBLIC_GIT_BLOB_MATCHES_PIN_NOT_RELEASE_APPROVED",
            "source_id": source_id,
            "verified_source_tag": verified["source_tag"],
            "verified_source_file": verified["source_file"],
            "source_content_address_url": url,
            "observed_at_utc": datetime.now(timezone.utc).isoformat(
                timespec="seconds"),
            "raw_source_bytes": verified["source_size_bytes"],
            "sha256": verified["observed_raw_sha256"],
            "git_blob_sha1": verified["observed_git_blob_sha1"],
            "expected_sha256": verified["expected_raw_sha256"],
            "source_bytes_sha256_and_git_blob_match": True,
            "source_tag_signature_verified": False,
            "source_origin_independently_attested": False,
            "technical_claims_reviewed": False,
            "independent_qa_verified": False,
            "license_redistribution_approved": False,
            "human_approved": False,
            "review_event_id": proposal["event_id"],
            "review_journal_written": False,
            "review_journal_status": "NOT_REQUESTED",
            "review_journal_is_signed": False,
            "catalog_reference_checked": False,
            "network_requests": 1,
            "source_raw_bytes_saved_or_redistributed": False,
            "operating_database_writes": 0,
            "other_project_access": False,
            "auto_promoted": False, "auto_withdrawn": False,
            "export_allowed": False, "released": False,
        }
        if record_review:
            # Permission for this single isolated advisory event is distinct
            # from permission for the single public GET.
            journal_result = pinned.persist_review_event(
                root, proposal, owner_opt_in=True)
            history = pinned.read_isolated_review_journal(root)
            checked = pinned.inspect_review_journal(history)
            if (checked["total_events"] < 1
                    or not checked["events"]
                    or checked["events"][-1]["event_id"] != proposal["event_id"]
                    and not any(event["event_id"] == proposal["event_id"]
                                for event in checked["events"])):
                raise AcceptanceError("persisted event not in verified journal")
            from . import skillbook_catalog_union_v01 as catalog
            dossier = catalog.inspect_review_candidate(
                pinned_review_history=history)
            matching = [
                row for row in dossier["pinned_source_review_statuses"]
                if row["source_id"] == source_id
            ]
            if (len(matching) != 1
                    or matching[0]["review_event_id"] != proposal["event_id"]
                    or matching[0]["status"] !=
                    "PINNED_RAW_SOURCE_HASHES_MATCH_UNAUTHENTICATED"
                    or dossier["export_allowed"] is not False):
                raise AcceptanceError(
                    "journal event not current in W04 catalog; manual review required")
            result.update({
                "status": "SOURCE_VERIFIED_REVIEW_JOURNAL_AND_W04_LINKED_NOT_APPROVED",
                "review_journal_written": (
                    journal_result["status"] ==
                    "ISOLATED_REVIEW_EVENT_COMMITTED_NOT_APPROVED"),
                "review_journal_status": journal_result["status"],
                "review_journal_total_events": checked["total_events"],
                "review_journal_head_sha256": checked["last_hash"],
                "catalog_reference_checked": True,
                "catalog_source_status": matching[0]["status"],
            })
        return result
    except pinned.SourceReviewError as exc:
        raise AcceptanceError("UCIE-only source review gate rejected") from exc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="One shot exact UCIE public Git blob -> verify -> optional W04 review journal")
    p.add_argument("--source", choices=sorted(REPOS), required=True)
    p.add_argument("--confirm-network", action="store_true")
    p.add_argument("--record-review", action="store_true")
    p.add_argument("--confirm-review-write", action="store_true")
    args = p.parse_args(argv)
    try:
        receipt = accept_one_exact_source(
            args.source, owner_root=Path.cwd(),
            confirm_network=args.confirm_network,
            record_review=args.record_review,
            confirm_review_write=args.confirm_review_write)
    except (AcceptanceError, OSError, ValueError):
        print(json.dumps({
            "schema": SCHEMA,
            "status": "PINNED_SOURCE_ONE_SHOT_FAIL_CLOSED",
            "export_allowed": False, "released": False,
        }))
        return 3
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
