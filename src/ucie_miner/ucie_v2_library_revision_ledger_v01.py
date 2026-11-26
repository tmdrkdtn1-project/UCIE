"""UCIE V2 review-only immutable-by-contract Virtual Library revision history.

Bounded, independently hash-checked snapshots of UCIE original library bundles.
A chain is tamper-evident against accidental changes, NOT authenticated proof
of origin. A separately owner-designated scratch store can persist snapshots;
never touch the operating SQLite, customer data, scheduler or source registry.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile

from .ucie_v2_original_library_assets_v01 import (
    SCHEMA as ASSET_SCHEMA, BUNDLE_ID, _digest as asset_digest,
)

SCHEMA = "UCIE_V2_REVIEW_HISTORY_LEDGER_V01"
ENTRY_SCHEMA = "UCIE_V2_REVIEW_HISTORY_EVENT_V01"
MAX_ENTRIES = 32
MAX_JSON_BYTES = 512_000
STORE_FILENAME = "ucie_v2_review_history.json"
STORE_MARKER = ".ucie_v2_review_store"
STORE_MARKER_VALUE = "UCIE_V2_REVIEW_STORE_ONLY_V01\n"
STATES = (
    "REVIEW_ACTIVE_UNVERIFIED",
    "REVIEW_HOLD_CANDIDATE_SOURCE_CHANGE",
    "REVIEW_HOLD_INCOMPLETE_PAIRED_FIXTURE",
)
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class ReviewHistoryError(ValueError):
    """Never interpret a changed review receipt as approved evidence."""


def _hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False
                             ).encode("utf-8")).hexdigest()


def new_review_history() -> dict:
    base = {"schema": SCHEMA, "bundle_id": BUNDLE_ID, "events": [],
            "record_count": 0, "latest_hash": None, "history_persisted": False,
            "rights_approved": False, "customer_release_authorized": False,
            "independent_qa_verified": False}
    return {**base, "content_sha256": _hash(base)}


def _validate_bundle(bundle: object) -> None:
    if type(bundle) is not dict or set(bundle) != {
        "schema", "bundle_id", "chapter", "machine", "revision",
        "synthetic_transfer_status", "source_facts_independently_verified",
        "real_upstream_tested", "actual_human_evidence",
        "independent_qa_verified", "rights_approved", "release_authorized",
        "automatic_training", "automatic_promotion", "automatic_distribution",
        "network_requests", "operating_database_writes", "content_sha256",
    }:
        raise ReviewHistoryError("unapproved or incomplete library bundle")
    chapter, machine, revision = (bundle.get("chapter"),
                                   bundle.get("machine"), bundle.get("revision"))
    if any(type(x) is not dict for x in (chapter, machine, revision)):
        raise ReviewHistoryError("library assets missing")
    digest = bundle.get("content_sha256")
    if (type(digest) is not str or not HEX64.fullmatch(digest)
            or digest != asset_digest({k:v for k,v in bundle.items()
                                      if k != "content_sha256"})
            or bundle.get("schema") != ASSET_SCHEMA
            or bundle.get("bundle_id") != BUNDLE_ID
            or chapter.get("asset_kind") !=
                "UCIE_ORIGINAL_HUMAN_SKILLBOOK_CHAPTER_DRAFT"
            or type(chapter.get("text")) is not str
            or sha256(chapter["text"].encode("utf-8")).hexdigest()
                  != chapter.get("text_sha256")
            or chapter.get("publication_status") != "REVIEW_ONLY_NOT_APPROVED"
            or machine.get("asset_kind") !=
                "UCIE_FIRST_PARTY_MACHINE_ENGINE_TEST_CONTRACT"
            or machine.get("runtime_execution_enabled") is not False
            or machine.get("external_code_execution_allowed") is not False
            or machine.get("rights_approved") is not False
            or machine.get("independent_qa_verified") is not False
            or machine.get("export_allowed") is not False
            or machine.get("autonomous_training_enabled") is not False
            or machine.get("source_hypothesis_sha256") !=
                revision.get("previous_hypothesis_sha256")
            or chapter.get("hypothesis_id") != machine.get("hypothesis_id")
            or machine.get("hypothesis_id") != revision.get("hypothesis_id")
            or revision.get("asset_kind") !=
                "UCIE_BOUNDED_REVISION_DISPOSITION_NOT_PRODUCTION"
            or revision.get("review_status") not in STATES
            or revision.get("candidate_source_authenticated") is not False
            or revision.get("actual_tests_executed_by_disposition") is not False
            or revision.get("retest_scheduled") is not False
            or revision.get("history_persisted") is not False
            or any(bundle.get(key) is not False for key in (
                "source_facts_independently_verified", "real_upstream_tested",
                "actual_human_evidence", "independent_qa_verified",
                "rights_approved", "release_authorized", "automatic_training",
                "automatic_promotion", "automatic_distribution"))
            or bundle.get("network_requests") != 0
            or bundle.get("operating_database_writes") != 0):
        raise ReviewHistoryError("review bundle hash or authority contract drift")
    sources = chapter.get("source_lineage")
    counterexample = machine.get("counterexample")
    if (type(counterexample) is not dict
            or type(sources) is not list or len(sources) != 2
            or {p.get("source_id") for p in sources if type(p) is dict}
                != {"doc:python/cpython", "doc:git/git"}
            or any(type(p) is not dict or
                   type(p.get("document_sha256")) is not str or
                   HEX64.fullmatch(p["document_sha256"]) is None for p in sources)
            or counterexample.get("result") !=
                "REJECTED_BY_EXPLICIT_DIFFERING_OUTPUT_CONTRACTS"):
        raise ReviewHistoryError("source lineage or negative lesson missing")


def validate_review_history(history: object) -> dict:
    if type(history) is not dict or set(history) != {
        "schema", "bundle_id", "events", "record_count", "latest_hash",
        "history_persisted", "rights_approved", "customer_release_authorized",
        "independent_qa_verified", "content_sha256",
    } or history["schema"] != SCHEMA or history["bundle_id"] != BUNDLE_ID:
        raise ReviewHistoryError("invalid history schema")
    entries = history["events"]
    if type(entries) is not list or len(entries) > MAX_ENTRIES:
        raise ReviewHistoryError("unbounded history")
    prior = None
    seen = set()
    for index, entry in enumerate(entries):
        if type(entry) is not dict or set(entry) != {
            "schema", "sequence", "previous_hash", "bundle", "event_hash",
        }:
            raise ReviewHistoryError("invalid event fields")
        if (entry["schema"] != ENTRY_SCHEMA
                or type(entry["sequence"]) is not int
                or entry["sequence"] != index + 1
                or entry["previous_hash"] != prior):
            raise ReviewHistoryError("history chain or order drift")
        _validate_bundle(entry["bundle"])
        digest = entry["bundle"]["content_sha256"]
        if digest in seen:
            raise ReviewHistoryError("duplicate bundle replay")
        seen.add(digest)
        payload = {k: v for k,v in entry.items() if k != "event_hash"}
        if type(entry["event_hash"]) is not str or _hash(payload) != entry["event_hash"]:
            raise ReviewHistoryError("event hash mismatch")
        prior = entry["event_hash"]
    if (history["record_count"] != len(entries)
            or history["latest_hash"] != prior
            or history["history_persisted"] is not False
            or history["rights_approved"] is not False
            or history["customer_release_authorized"] is not False
            or history["independent_qa_verified"] is not False
            or type(history["content_sha256"]) is not str
            or _hash({k:v for k,v in history.items()
                      if k != "content_sha256"}) != history["content_sha256"]):
        raise ReviewHistoryError("history summary or approval forged")
    return deepcopy(history)


def append_review_bundle(history: dict, bundle: dict) -> dict:
    current = validate_review_history(history)
    _validate_bundle(bundle)
    existing = {e["bundle"]["content_sha256"] for e in current["events"]}
    if bundle["content_sha256"] in existing:
        return current
    if len(current["events"]) >= MAX_ENTRIES:
        raise ReviewHistoryError("history capacity reached: no automatic pruning")
    prior = current["latest_hash"]
    payload = {"schema": ENTRY_SCHEMA, "sequence": len(current["events"]) + 1,
               "previous_hash": prior, "bundle": deepcopy(bundle)}
    event = {**payload, "event_hash": _hash(payload)}
    base = {k: v for k,v in current.items() if k != "content_sha256"}
    base["events"].append(event)
    base["record_count"] = len(base["events"])
    base["latest_hash"] = event["event_hash"]
    return validate_review_history({**base, "content_sha256": _hash(base)})


def review_negative_lessons(history: dict) -> dict:
    """Do not erase failed hypotheses: index counterexamples and current HOLDs."""
    state = validate_review_history(history)
    lessons = []
    for event in state["events"]:
        bundle = event["bundle"]
        review = bundle["revision"]
        counter = bundle["machine"]["counterexample"]
        lessons.append({
            "sequence": event["sequence"],
            "bundle_sha256": bundle["content_sha256"],
            "hypothesis_id": review["hypothesis_id"],
            "review_status": review["review_status"],
            "rejected_claim": counter["claim"],
            "counterexample_disposition": counter["result"],
            "affected_assets": list(review["affected_assets"]),
            "proposed_affected_only_tests":
                list(review["proposed_affected_only_tests"]),
            "usable_as_proven_rule": False,
        })
    return {
        "schema": "UCIE_V2_REVIEW_NEGATIVE_LESSONS_V01",
        "history_head": state["latest_hash"],
        "reusable_review_only_lessons": lessons,
        "negative_lessons_preserved": len(lessons),
        "independent_qa_verified": False,
        "automatic_promotion": False,
    }


def _designated_path(directory: str | Path) -> Path:
    original = Path(directory)
    if original.is_symlink():
        raise ReviewHistoryError("symlinked review root denied")
    root = original.resolve(strict=True)
    if not root.is_dir() or root.name != "ucie_v2_review_store":
        raise ReviewHistoryError("dedicated review-only store directory required")
    marker = root / STORE_MARKER
    if marker.is_symlink() or not marker.is_file() or marker.read_text(
            encoding="utf-8") != STORE_MARKER_VALUE:
        raise ReviewHistoryError("UCIE-only review store marker missing")
    target = root / STORE_FILENAME
    if target.is_symlink():
        raise ReviewHistoryError("symlinked review ledger denied")
    return target


def read_review_store(directory: str | Path) -> dict:
    target = _designated_path(directory)
    if not target.exists():
        return new_review_history()
    if not target.is_file() or target.stat().st_size > MAX_JSON_BYTES:
        raise ReviewHistoryError("invalid or oversized review store")
    try:
        return validate_review_history(json.loads(target.read_text(encoding="utf-8")))
    except (UnicodeError, OSError, json.JSONDecodeError, ValueError) as exc:
        raise ReviewHistoryError("stored review ledger invalid") from exc


def write_review_store(directory: str | Path, candidate: dict, *,
                       expected_previous_sha256: str,
                       approve_write: bool = False) -> dict:
    """Opt-in CAS review-store write, never operating DB; default preview.

    Local tamper detection is not a signed authoritative upstream receipt.
    External concurrent writers must use a separate file lock.
    """
    target = _designated_path(directory)
    current = read_review_store(directory)
    validated = validate_review_history(candidate)
    if (type(expected_previous_sha256) is not str
            or current["content_sha256"] != expected_previous_sha256):
        raise ReviewHistoryError("stale review-store head")
    prefix = current["events"]
    if (validated["events"][:len(prefix)] != prefix
            or validated["record_count"] < current["record_count"]):
        raise ReviewHistoryError("non-append review history denied")
    if validated["content_sha256"] == current["content_sha256"]:
        return {"status": "UNCHANGED_NO_WRITE",
                "history_head": validated["content_sha256"]}
    if not approve_write:
        return {"status": "PREVIEW_ONLY_NO_WRITE",
                "history_head": validated["content_sha256"]}
    content = json.dumps(validated, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(content) > MAX_JSON_BYTES:
        raise ReviewHistoryError("review store payload exceeds limit")
    # One bounded atomic replacement, same folder and same filesystem.
    path = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".ucie_review_",
                                         suffix=".tmp", delete=False) as handle:
            path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if read_review_store(directory)["content_sha256"] != expected_previous_sha256:
            raise ReviewHistoryError("store changed during prepared write")
        os.replace(path, target)
        return {"status": "REVIEW_STORE_WRITTEN_NOT_PRODUCTION",
                "history_head": validated["content_sha256"],
                "entries": validated["record_count"]}
    finally:
        if path is not None and path.exists():
            path.unlink()
