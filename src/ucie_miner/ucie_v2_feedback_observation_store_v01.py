"""UCIE V2 review-only result persistence and measured observation deltas.

No live SQLite, customer data, upstream SDK calls, model training or automatic
approvals. Distinguishes receipt growth from independently proven improvements.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re

from .ucie_v2_feedback_registry_v01 import (
    validate_feedback_registry, prioritize_review_experiments,
)
from .ucie_v2_library_revision_ledger_v01 import validate_review_history

SCHEMA = "UCIE_V2_FEEDBACK_OBSERVATION_DELTA_V01"
STORE_SCHEMA = "UCIE_V2_DETACHED_FEEDBACK_STORE_V01"
MARKER = ".ucie_v2_feedback_review_store"
MARKER_VALUE = "UCIE_V2_FIRST_PARTY_FEEDBACK_REVIEW_ONLY_V01\n"
FOLDER = "ucie_v2_feedback_review_store"
MAX_BYTES = 512_000
MAX_FILES = 32
HEX = re.compile(r"[0-9a-f]{64}\Z")


class FeedbackStoreError(ValueError):
    """Fail closed for stale, unsupported or overbroad review persistence."""


def _digest(x: object) -> str:
    return sha256(json.dumps(x, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def compare_review_observations(history: dict, before: dict, after: dict) -> dict:
    """Compare two review-only registries on ONE pinned library history.

    A newly appended first-party fixture observation is not a measured customer
    benefit. No changing baseline or approved-source SHA is silently accepted.
    """
    parent = validate_review_history(history)
    older = validate_feedback_registry(parent, before)
    newer = validate_feedback_registry(parent, after)
    old_events, new_events = older["events"], newer["events"]
    if new_events[:len(old_events)] != old_events:
        raise FeedbackStoreError("review event chain rewritten or removed")
    added = new_events[len(old_events):]
    old_set = {e["fingerprint"] for e in old_events}
    if any(e["fingerprint"] in old_set for e in added):
        raise FeedbackStoreError("old result counted as fresh")
    queue = prioritize_review_experiments(parent, newer)
    now = new_events[-1]["evidence"] if new_events else None
    decisions = [r["decision"] for r in now["candidate_reviews"]] if now else []
    blocked = any(d.startswith("HOLD_") for d in decisions)
    rejected = any(d == "REJECT_SYNTHETIC_CONTROL_FAILURE" for d in decisions)
    payload = {
        "schema": SCHEMA,
        "history_head_sha256": parent["content_sha256"],
        "before_registry_sha256": older["content_sha256"],
        "after_registry_sha256": newer["content_sha256"],
        "prior_review_receipts": len(old_events),
        "current_review_receipts": len(new_events),
        "new_distinct_review_receipts": len(added),
        "unchanged": not bool(added),
        "current_review_decisions": decisions,
        "source_or_evidence_hold": blocked,
        "failed_control_observed": rejected,
        "experiment_priority_queue": queue["priority_queue"],
        "new_external_evidence_observed": False,
        "real_user_improvement_measured": False,
        "reproducible_customer_benefit_verified": False,
        "technical_adoption_authorized": False,
        "automatic_learning_or_training": False,
        "automatic_job_dispatch": False,
        "independent_qa_verified": False,
        "operating_database_writes": 0,
        "network_requests": 0,
    }
    return {**payload, "content_sha256": _digest(payload)}


def _check_root(path: str | Path) -> Path:
    requested = Path(path)
    if requested.is_symlink():
        raise FeedbackStoreError("symlinked feedback review root denied")
    try:
        root = requested.resolve(strict=True)
    except (OSError, ValueError) as exc:
        raise FeedbackStoreError("review root not present") from exc
    if not root.is_dir() or root.name != FOLDER:
        raise FeedbackStoreError("isolated review directory required")
    marker = root / MARKER
    if (marker.is_symlink() or not marker.is_file()
            or marker.read_text(encoding="utf-8") != MARKER_VALUE):
        raise FeedbackStoreError("feedback-only marker missing")
    return root


def _record_path(root: Path, digest: str) -> Path:
    if type(digest) is not str or HEX.fullmatch(digest) is None:
        raise FeedbackStoreError("invalid receipt fingerprint")
    path = root / ("feedback_" + digest + ".json")
    if path.is_symlink():
        raise FeedbackStoreError("symlinked feedback review receipt denied")
    return path


def read_feedback_receipt(history: dict, directory: str | Path,
                          receipt_sha256: str) -> dict:
    """Read an exact immutable receipt after checking its detached UCIE history."""
    parent = validate_review_history(history)
    root = _check_root(directory)
    path = _record_path(root, receipt_sha256)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise FeedbackStoreError("missing/oversized feedback receipt")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FeedbackStoreError("unreadable feedback receipt") from exc
    if (type(receipt) is not dict or set(receipt) != {
                "schema", "history_head_sha256", "registry", "content_sha256"}
            or receipt["schema"] != STORE_SCHEMA
            or receipt["history_head_sha256"] != parent["content_sha256"]
            or receipt["content_sha256"] != receipt_sha256
            or _digest({k:v for k,v in receipt.items()
                        if k != "content_sha256"}) != receipt_sha256):
        raise FeedbackStoreError("feedback receipt hash/identity mismatch")
    checked = validate_feedback_registry(parent, receipt["registry"])
    if checked["content_sha256"] != receipt["registry"]["content_sha256"]:
        raise FeedbackStoreError("embedded registry changed")
    return receipt


def save_feedback_receipt(history: dict, registry: dict,
                          directory: str | Path, *,
                          approve_write: bool = False) -> dict:
    """Owner opt-in create-only file; never initialize folder or overwrite bytes.

    Caller must provide pre-created dedicated folder + marker. A receipt hash
    proves consistency, not origin authenticity or on-host test execution.
    """
    if type(approve_write) is not bool:
        raise FeedbackStoreError("explicit bool write gate required")
    parent = validate_review_history(history)
    reviewed = validate_feedback_registry(parent, registry)
    root = _check_root(directory)
    payload = {"schema": STORE_SCHEMA,
               "history_head_sha256": parent["content_sha256"],
               "registry": reviewed}
    receipt = {**payload, "content_sha256": _digest(payload)}
    blob = json.dumps(receipt, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(blob) > MAX_BYTES:
        raise FeedbackStoreError("receipt exceeds bounded max")
    path = _record_path(root, receipt["content_sha256"])
    if path.exists():
        found = read_feedback_receipt(parent, root, receipt["content_sha256"])
        if found != receipt:
            raise FeedbackStoreError("existing named receipt conflicts")
        return {"status": "ALREADY_STORED_IMMUTABLE",
                "receipt_sha256": receipt["content_sha256"], "wrote": False}
    if not approve_write:
        return {"status": "PREVIEW_ONLY_NO_WRITE",
                "receipt_sha256": receipt["content_sha256"], "wrote": False}
    files = list(root.glob("feedback_*.json"))
    if len(files) >= MAX_FILES:
        raise FeedbackStoreError("review-only store full; no silent deletion")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        raise FeedbackStoreError("concurrent receipt already exists") from None
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(blob)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        # Do not delete the file: a concurrent reader may already hold it.
        raise
    verified = read_feedback_receipt(parent, root, receipt["content_sha256"])
    if verified != receipt:
        raise FeedbackStoreError("post-write verification mismatch")
    return {"status": "IMMUTABLE_REVIEW_RECEIPT_CREATED_NOT_PRODUCTION",
            "receipt_sha256": receipt["content_sha256"], "wrote": True}
