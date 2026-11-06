"""UCIE-only version-pinned official source bytes + isolated review history.

Offline. Uses the existing first-party Python/Git SkillBook frozen source
metadata; no source-list additions, network, private repo scan, code execution,
rule promotion, release, operational DB or scheduler writes.

Review journal is an isolated, owner-opt-in, sha256-chained audit of proposals,
not a signature, expert review or verified source origin.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha1, sha256
import json
import os
from pathlib import Path
import re
import sys
import tempfile

SCHEMA = "UCIE_PINNED_SKILLBOOK_SOURCE_BYTES_V01"
EVENT_SCHEMA = "UCIE_SKILLBOOK_SOURCE_REVIEW_EVENT_V01"
JOURNAL_SCHEMA = "UCIE_SKILLBOOK_REVIEW_JOURNAL_V01"
MAX_SOURCE_BYTES = 512_000
MAX_JOURNAL_BYTES = 128_000
MAX_EVENTS = 128
MAX_NOTE_CHARS = 280
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
INBOX = {
    "doc:python/cpython": "python_cpython_v3_15_0_os.rst",
    "doc:git/git": "git_git_v2_51_0_git-status.adoc",
}
REVIEW_FILE = "skillbook_review_events_v01.jsonl"


class SourceReviewError(ValueError):
    """Fail closed on unverifiable source identity or review history."""


def _canonical_json(data: dict) -> bytes:
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _pinned_book(source_id: str) -> dict:
    if type(source_id) is not str or source_id not in INBOX:
        raise SourceReviewError("source not in the two approved curated books")
    if source_id == "doc:python/cpython":
        from .skillbook_product_v01 import build_skillbook
    else:
        from .skillbook_git_porcelain_product_v01 import build_skillbook
    book = build_skillbook()
    entry, metadata = book["library_entry"], book["source_evidence"]
    digest, blob = (
        metadata.get("source_document_sha256"),
        metadata.get("source_document_git_blob_sha1"),
    )
    if (entry.get("source_id") != source_id
            or entry.get("evidence_sha256") != digest
            or entry.get("approval_status") != "NOT_APPROVED"
            or entry.get("export_allowed") is not False
            or metadata.get("source_tag") not in {"v3.15.0", "v2.51.0"}
            or metadata.get("source_file") not in {
                "Doc/library/os.rst", "Documentation/git-status.adoc"}
            or type(digest) is not str or HEX64.fullmatch(digest) is None
            or type(blob) is not str or HEX40.fullmatch(blob) is None):
        raise SourceReviewError("first-party source pin or approval contract drift")
    expected = (
        "v3.15.0", "Doc/library/os.rst",
    ) if source_id == "doc:python/cpython" else (
        "v2.51.0", "Documentation/git-status.adoc",
    )
    if (metadata["source_tag"], metadata["source_file"]) != expected:
        raise SourceReviewError("source identity changed under a static source id")
    return book


def verify_pinned_raw_bytes(source_id: str, raw: bytes) -> dict:
    """Check raw *source file* bytes, NOT a mutable rendered HTML response.

    Content hash equality is a meaningful integrity match to the recorded
    first-party pin; origin authenticity and technical truth are separate.
    """
    book = _pinned_book(source_id)
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_SOURCE_BYTES:
        raise SourceReviewError("bounded pinned raw source file bytes required")
    source = book["source_evidence"]
    raw_sha = sha256(raw).hexdigest()
    git_sha = sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    expected_raw = source["source_document_sha256"]
    expected_git = source["source_document_git_blob_sha1"]
    matched = raw_sha == expected_raw and git_sha == expected_git
    return {
        "schema": SCHEMA,
        "status": (
            "PINNED_SOURCE_FILE_DIGESTS_MATCH_ORIGIN_REVIEW_PENDING"
            if matched else "PINNED_SOURCE_FILE_DIGESTS_DIFFER_REVALIDATION_REQUIRED"
        ),
        "source_id": source_id,
        "skillbook_id": book["skillbook_id"],
        "source_file": source["source_file"],
        "source_tag": source["source_tag"],
        "source_repository": source["publisher"],
        "source_material_kind": "VERSION_TAGGED_REPO_SOURCE_FILE_RAW_BYTES",
        "source_size_bytes": len(raw),
        "observed_raw_sha256": raw_sha,
        "expected_raw_sha256": expected_raw,
        "observed_git_blob_sha1": git_sha,
        "expected_git_blob_sha1": expected_git,
        "sha256_equal": raw_sha == expected_raw,
        "git_blob_sha1_equal": git_sha == expected_git,
        "pinned_bytes_match": matched,
        "origin_authenticated_independently": False,
        "source_tag_signature_verified": False,
        "technical_claim_reviewed": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "human_approved": False,
        "auto_withdrawn": False,
        "auto_promoted": False,
        "signed": False,
        "export_allowed": False,
        "released": False,
        "operating_database_writes": 0,
        "network_requests": 0,
        "other_project_access": False,
    }


def propose_source_review(verification: dict, *,
                          note: str = "Review pinned source bytes before any skillbook release") -> dict:
    """Advisory decision, not an authenticated action on the product."""
    if (type(verification) is not dict
            or type(verification.get("source_id")) is not str):
        raise SourceReviewError("invalid pinned evidence")
    sid = verification["source_id"]
    # Validate submitted schema strictly, but distinguish matched/mismatched.
    expected = _pinned_book(sid)
    fields = (
        "schema", "source_id", "skillbook_id", "source_file",
        "source_tag", "source_repository", "source_material_kind",
        "source_size_bytes", "observed_raw_sha256", "expected_raw_sha256",
        "observed_git_blob_sha1", "expected_git_blob_sha1",
        "sha256_equal", "git_blob_sha1_equal", "pinned_bytes_match",
        "origin_authenticated_independently", "source_tag_signature_verified",
        "technical_claim_reviewed", "independent_qa_verified", "rights_approved",
        "human_approved", "auto_withdrawn", "auto_promoted", "signed",
        "export_allowed", "released", "operating_database_writes",
        "network_requests", "other_project_access", "status",
    )
    if set(verification) != set(fields):
        raise SourceReviewError("unknown pinned verification field")
    raw, blob = verification["observed_raw_sha256"], verification["observed_git_blob_sha1"]
    if (type(raw) is not str or HEX64.fullmatch(raw) is None
            or type(blob) is not str or HEX40.fullmatch(blob) is None
            or type(verification["source_size_bytes"]) is not int
            or not 1 <= verification["source_size_bytes"] <= MAX_SOURCE_BYTES):
        raise SourceReviewError("invalid pinned raw hash or byte budget")
    meta = expected["source_evidence"]
    calculated_match = (
        raw == meta["source_document_sha256"]
        and blob == meta["source_document_git_blob_sha1"]
    )
    if (verification["schema"] != SCHEMA
            or verification["skillbook_id"] != expected["skillbook_id"]
            or verification["source_file"] != meta["source_file"]
            or verification["source_tag"] != meta["source_tag"]
            or verification["source_repository"] != meta["publisher"]
            or verification["source_material_kind"] != "VERSION_TAGGED_REPO_SOURCE_FILE_RAW_BYTES"
            or verification["expected_raw_sha256"] != meta["source_document_sha256"]
            or verification["expected_git_blob_sha1"] != meta["source_document_git_blob_sha1"]
            or verification["pinned_bytes_match"] is not calculated_match
            or verification["sha256_equal"] is not (
                raw == meta["source_document_sha256"])
            or verification["git_blob_sha1_equal"] is not (
                blob == meta["source_document_git_blob_sha1"])
            or verification["status"] != (
                "PINNED_SOURCE_FILE_DIGESTS_MATCH_ORIGIN_REVIEW_PENDING"
                if calculated_match
                else "PINNED_SOURCE_FILE_DIGESTS_DIFFER_REVALIDATION_REQUIRED")
            or any(verification[x] is not False for x in (
                "origin_authenticated_independently",
                "source_tag_signature_verified", "technical_claim_reviewed",
                "independent_qa_verified", "rights_approved", "human_approved",
                "auto_withdrawn", "auto_promoted", "signed",
                "export_allowed", "released", "other_project_access"))
            or type(verification["network_requests"]) is not int
            or verification["network_requests"] != 0
            or type(verification["operating_database_writes"]) is not int
            or verification["operating_database_writes"] != 0):
        raise SourceReviewError("forged or drifting pinned source proof")
    if (type(note) is not str or not 12 <= len(note) <= MAX_NOTE_CHARS
            or note != note.strip() or any(ord(c) < 32 or ord(c) == 127
                                          for c in note)):
        raise SourceReviewError("bounded plain review note required")
    result = {
        "schema": EVENT_SCHEMA,
        "source_id": sid,
        "skillbook_id": expected["skillbook_id"],
        "source_tag": meta["source_tag"],
        "source_file": meta["source_file"],
        "expected_source_sha256": meta["source_document_sha256"],
        "observed_source_sha256": raw,
        "observed_git_blob_sha1": blob,
        "pinned_bytes_match": calculated_match,
        "recommended_action": (
            "KEEP_CURRENT_PIN_REVIEW_ORIGIN_AND_TECHNICAL_CLAIMS"
            if calculated_match else
            "HOLD_RELEASE_AND_REVALIDATE_INPUT_NO_AUTO_WITHDRAWAL"
        ),
        "review_note": note,
        "independent_origin_review_pending": True,
        "technical_claim_review_pending": True,
        "human_approval_granted": False,
        "release_allowed": False,
        "withdrawal_executed": False,
        "automatic_promotion": False,
    }
    result["event_id"] = sha256(_canonical_json(result)).hexdigest()
    return result


def _validate_event(event: dict) -> None:
    if type(event) is not dict or type(event.get("event_id")) is not str:
        raise SourceReviewError("review proposal contract required")
    sid = event.get("source_id")
    _pinned_book(sid)
    fields = {
        "schema", "source_id", "skillbook_id", "source_tag", "source_file",
        "expected_source_sha256", "observed_source_sha256",
        "observed_git_blob_sha1", "pinned_bytes_match",
        "recommended_action", "review_note",
        "independent_origin_review_pending", "technical_claim_review_pending",
        "human_approval_granted", "release_allowed", "withdrawal_executed",
        "automatic_promotion", "event_id",
    }
    if set(event) != fields or event["schema"] != EVENT_SCHEMA:
        raise SourceReviewError("event fields invalid")
    x = dict(event)
    event_id = x.pop("event_id")
    if sha256(_canonical_json(x)).hexdigest() != event_id:
        raise SourceReviewError("event content hash altered")
    # Recheck against a canonical pinned-source verification. We cannot
    # reconstruct original file bytes from a digest, so this verifies only
    # signed-off schema and digest claims, not the source origin.
    book = _pinned_book(sid)
    source = book["source_evidence"]
    matching = (event["observed_source_sha256"] ==
                source["source_document_sha256"]
                and event["observed_git_blob_sha1"] ==
                source["source_document_git_blob_sha1"])
    if (event["skillbook_id"] != book["skillbook_id"]
            or event["source_tag"] != source["source_tag"]
            or event["source_file"] != source["source_file"]
            or event["expected_source_sha256"] != source["source_document_sha256"]
            or event["pinned_bytes_match"] is not matching
            or event["recommended_action"] != (
                "KEEP_CURRENT_PIN_REVIEW_ORIGIN_AND_TECHNICAL_CLAIMS"
                if matching else
                "HOLD_RELEASE_AND_REVALIDATE_INPUT_NO_AUTO_WITHDRAWAL")
            or type(event["review_note"]) is not str
            or not 12 <= len(event["review_note"]) <= MAX_NOTE_CHARS
            or event["review_note"] != event["review_note"].strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in event["review_note"])
            or type(event["observed_source_sha256"]) is not str
            or HEX64.fullmatch(event["observed_source_sha256"]) is None
            or type(event["observed_git_blob_sha1"]) is not str
            or HEX40.fullmatch(event["observed_git_blob_sha1"]) is None
            or event["independent_origin_review_pending"] is not True
            or event["technical_claim_review_pending"] is not True
            or any(event[k] is not False for k in (
                "human_approval_granted", "release_allowed",
                "withdrawal_executed", "automatic_promotion"))):
        raise SourceReviewError("unsupported manual review or provenance claim")


def inspect_review_journal(data: bytes) -> dict:
    """Validate every bounded hash-linked line; fail on partial/corrupt tails."""
    if type(data) is not bytes or len(data) > MAX_JOURNAL_BYTES:
        raise SourceReviewError("review journal byte budget exceeded")
    if not data:
        return {
            "schema": JOURNAL_SCHEMA, "events": [],
            "last_hash": "0" * 64, "total_events": 0,
        }
    if not data.endswith(b"\n") or len(data.splitlines()) > MAX_EVENTS:
        raise SourceReviewError("uncommitted or oversized journal")
    previous = "0" * 64
    events, ids = [], set()
    for line in data.splitlines():
        if not line or len(line) > 4096:
            raise SourceReviewError("invalid journal entry size")
        try:
            obj = json.loads(line.decode("ascii"))
        except (ValueError, UnicodeError) as exc:
            raise SourceReviewError("corrupt UTF-8 journal") from exc
        if (type(obj) is not dict
                or set(obj) != {
                    "sequence", "previous_sha256", "event", "entry_sha256"}
                or type(obj["sequence"]) is not int
                or obj["sequence"] != len(events) + 1
                or obj["previous_sha256"] != previous):
            raise SourceReviewError("journal sequence or prior entry hash mismatch")
        event = obj["event"]
        _validate_event(event)
        if event["event_id"] in ids:
            raise SourceReviewError("duplicated review event")
        ids.add(event["event_id"])
        material = {key: obj[key] for key in (
            "sequence", "previous_sha256", "event")}
        expected = sha256(_canonical_json(material)).hexdigest()
        if obj["entry_sha256"] != expected:
            raise SourceReviewError("tampered review journal hash chain")
        previous = expected
        events.append(event)
    return {
        "schema": JOURNAL_SCHEMA,
        "events": events,
        "last_hash": previous,
        "total_events": len(events),
    }


def extend_review_journal(existing: bytes, event: dict) -> tuple[bytes, dict]:
    """Pure bounded append proposal; no file changes without owner opt-in."""
    old = inspect_review_journal(existing)
    _validate_event(event)
    if event["event_id"] in {e["event_id"] for e in old["events"]}:
        return existing, {
            "schema": JOURNAL_SCHEMA,
            "status": "ALREADY_RECORDED_NO_DUPLICATE",
            "total_events": old["total_events"],
            "last_hash": old["last_hash"], "operating_db_writes": 0,
            "approved_or_released": False,
        }
    if old["total_events"] >= MAX_EVENTS:
        raise SourceReviewError("audit journal record capacity exceeded")
    obj = {
        "sequence": old["total_events"] + 1,
        "previous_sha256": old["last_hash"],
        "event": event,
    }
    obj["entry_sha256"] = sha256(_canonical_json(obj)).hexdigest()
    new_data = existing + _canonical_json(obj) + b"\n"
    if len(new_data) > MAX_JOURNAL_BYTES:
        raise SourceReviewError("audit journal byte budget exceeded")
    inspect_review_journal(new_data)
    return new_data, {
        "schema": JOURNAL_SCHEMA, "status": "REVIEW_EVENT_PREPARED_NOT_APPROVED",
        "total_events": old["total_events"] + 1,
        "last_hash": obj["entry_sha256"],
        "operating_db_writes": 0, "approved_or_released": False,
    }


def _owner_root(root: Path) -> Path:
    if type(root) is not Path or root.name != "UCIE" or root.is_symlink():
        raise SourceReviewError("isolated UCIE project root required")
    if not root.is_dir():
        raise SourceReviewError("UCIE project root missing")
    result = root.resolve(strict=True)
    if result.name != "UCIE":
        raise SourceReviewError("refusing alias outside UCIE root")
    return result


def _safe_review_dir(root: Path) -> Path:
    base = _owner_root(root)
    runtime = base / "runtime"
    if runtime.is_symlink() or not runtime.is_dir():
        raise SourceReviewError("UCIE runtime must already be a real directory")
    folder = runtime / "skillbook_manual_review"
    if folder.is_symlink():
        raise SourceReviewError("symlinked review directory forbidden")
    folder.mkdir(mode=0o700, exist_ok=True)
    if folder.resolve() != (base / "runtime" / "skillbook_manual_review"):
        raise SourceReviewError("review path escapes UCIE runtime")
    return folder


def verify_ucie_inbox(root: Path, source_id: str) -> dict:
    """Read only one exact named file under UCIE's isolated review inbox."""
    _pinned_book(source_id)
    base = _owner_root(root)
    runtime = base / "runtime"
    folder = runtime / "skillbook_manual_review"
    target = folder / INBOX[source_id]
    if (runtime.is_symlink() or folder.is_symlink() or target.is_symlink()
            or not folder.is_dir() or not target.is_file()
            or target.resolve(strict=True) != folder.resolve() / INBOX[source_id]):
        raise SourceReviewError("only exact non-symlink UCIE inbox file is readable")
    with target.open("rb") as handle:
        raw = handle.read(MAX_SOURCE_BYTES + 1)
    return verify_pinned_raw_bytes(source_id, raw)


def persist_review_event(root: Path, event: dict, *,
                         owner_opt_in: bool = False) -> dict:
    """Owner-requested atomic isolated review write; never the operating DB.

    Interprocess O_EXCL lock, SHA checked current journal, fsync and atomic
    replace; no automatic promotion, rule change, release or deletion.
    """
    if owner_opt_in is not True:
        raise SourceReviewError("separate explicit owner review journal opt-in needed")
    _validate_event(event)
    folder = _safe_review_dir(root)
    target = folder / REVIEW_FILE
    lock = folder / (REVIEW_FILE + ".lock")
    if target.is_symlink() or lock.is_symlink():
        raise SourceReviewError("symlinked review artifact forbidden")
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError as exc:
        raise SourceReviewError("review journal currently locked") from exc
    os.close(fd)
    tmp_path = None
    try:
        if target.is_symlink():
            raise SourceReviewError("review artifact changed to symlink")
        if target.exists():
            with target.open("rb") as handle:
                old = handle.read(MAX_JOURNAL_BYTES + 1)
        else:
            old = b""
        updated, receipt = extend_review_journal(old, event)
        if updated == old:
            return receipt
        with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".ucie-review-", suffix=".tmp",
                dir=folder, delete=False) as handle:
            tmp_path = Path(handle.name)
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        if target.is_symlink():
            raise SourceReviewError("review target changed to symlink")
        os.replace(tmp_path, target)
        tmp_path = None
        return {
            **receipt, "status": "ISOLATED_REVIEW_EVENT_COMMITTED_NOT_APPROVED",
            "journal_path_within_ucie_only": str(
                Path("runtime") / "skillbook_manual_review" / REVIEW_FILE),
            "operating_db_writes": 0,
        }
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline pinned UCIE public source verification and review proposal")
    parser.add_argument("--source", choices=sorted(INBOX), required=True)
    parser.add_argument("--record-review", action="store_true")
    parser.add_argument("--confirm-review-write", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = Path.cwd()
        verified = verify_ucie_inbox(root, args.source)
        proposal = propose_source_review(verified)
        receipt = {
            "verification": verified, "review_proposal": proposal,
            "files_written": 0,
        }
        if args.record_review:
            if not args.confirm_review_write:
                raise SourceReviewError("owner must confirm the isolated journal write")
            receipt["journal"] = persist_review_event(
                root, proposal, owner_opt_in=True)
            receipt["files_written"] = int(
                receipt["journal"]["status"] ==
                "ISOLATED_REVIEW_EVENT_COMMITTED_NOT_APPROVED")
        elif args.confirm_review_write:
            raise SourceReviewError("write consent not applicable without record-review")
    except (SourceReviewError, OSError):
        print(json.dumps({"schema": SCHEMA, "status": "PINNED_SOURCE_REVIEW_NO_GO"}))
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
