"""UCIE V1.0: explicit public observation receipts with source-pinned replay.

Owner opt-in only. An observed merge SHA or matching official HTTP-body SHA
does NOT verify the upstream fix, release version, legal license, regression,
security, owner signoff or rule approval. The original V0.9 public probe is
reused as-is. Stored receipts contain ONLY bounded, hardcoded status fields,
never original external code, arbitrary prose or PR body.

SHA-256 self-integrity detects accidental/inadmissible receipt modification;
it is NOT an authenticated digital signature. No operating DB writes,
cross-project lookup, task scheduling, external code execution or promotion.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile

from .library_explore import _candidate_rows
from .library_public_proof_v09 import perform_public_probe_batch
from .library_review_records_v05 import _root
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_PUBLIC_OBSERVATION_RECEIPT_V10"
AUDIT_SCHEMA = "UCIE_PUBLIC_OBSERVATION_REPLAY_V10"
MAX_RECORDS = 100
MAX_FILE_BYTES = 2600
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
UTC = re.compile(r"20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]\+00:00\Z")
METADATA_CODES = frozenset((
    "PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED",
    "PUBLIC_COMMIT_IDENTITY_MATCHED_NOT_FIX_VERIFIED",
    "PUBLIC_REVISION_MISMATCH_NO_GO",
    "PUBLIC_METADATA_UNAVAILABLE_NO_GO",
    "UNSUPPORTED_PUBLIC_IDENTITY_NO_GO",
))
DOC_CODES = frozenset((
    "OFFICIAL_RESPONSE_BYTES_SHA_MATCH_NOT_TRUST_SIGNOFF",
    "OFFICIAL_RESPONSE_BYTES_SHA_MISMATCH_NO_GO",
    "PUBLIC_DOCUMENT_UNAVAILABLE_NO_GO",
))
STORED_KEYS = frozenset((
    "schema", "item_id", "source_id", "public_url", "revision_hint",
    "v09_report_sha256", "metadata_status", "metadata_observed",
    "identity_matched", "documents", "fix_verified", "rule_approved",
    "auto_promoted", "source_code_executed", "approval_state",
))


class ObservationError(ValueError):
    pass


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def _digest(value: dict) -> str:
    return sha256(_canonical(value)).hexdigest()


def _directory(root: Path, *, create: bool = False) -> Path:
    root = _root(root)
    runtime = root / "runtime"
    folder = runtime / "public_observations_v10"
    records = folder / "receipts"
    for part in (runtime, folder, records):
        if part.is_symlink() or (part.exists() and not part.is_dir()):
            raise ObservationError("unsafe observation storage path")
    if create:
        records.mkdir(parents=True, exist_ok=True)
    return records


def _snapshot(report: dict) -> dict:
    if (type(report) is not dict or report.get("schema") !=
            "UCIE_PUBLIC_EVIDENCE_OPT_IN_BATCH_V09"
            or report.get("status") != "PUBLIC_SOURCE_OBSERVATION_REVIEW_REQUIRED_NO_GO"
            or report.get("auto_promoted") is not False
            or report.get("approved_rule_count") != 0
            or report.get("deployed_rule_count") != 0
            or report.get("external_source_code_executed") is not False
            or report.get("operating_database_writes") != 0
            or type(report.get("results")) is not list
            or len(report["results"]) != 1
            or type(report.get("audit_report_sha256")) is not str
            or HEX64.fullmatch(report["audit_report_sha256"]) is None):
        raise ObservationError("untrusted public probe report")
    if report["audit_report_sha256"] != _digest({
            key: value for key, value in report.items()
            if key != "audit_report_sha256"}):
        raise ObservationError("public probe report hash mismatch")
    item = report["results"][0]
    meta = item.get("source_revision_metadata")
    if (type(item) is not dict or type(meta) is not dict
            or type(item.get("item_id")) is not str
            or HEX64.fullmatch(item["item_id"]) is None
            or type(item.get("source_id")) is not str
            or not item["source_id"].startswith("repo:")
            or type(item.get("public_url")) is not str
            or len(item["public_url"]) > 240
            or meta.get("status") not in METADATA_CODES
            or meta.get("identity_matched") not in (True, False)
            or meta.get("metadata_observed") not in (True, False)
            or meta.get("fix_verified") is not False
            or type(meta.get("revision_hint")) is not str
            or HEX40.fullmatch(meta["revision_hint"]) is None):
        raise ObservationError("invalid bounded source metadata")
    if meta["identity_matched"] and not (
            meta["metadata_observed"] and meta["status"] in {
                "PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED",
                "PUBLIC_COMMIT_IDENTITY_MATCHED_NOT_FIX_VERIFIED"}):
        raise ObservationError("impossible public source identity status")
    documents = item.get("official_document_checks")
    if type(documents) is not list or len(documents) > 2:
        raise ObservationError("invalid bounded document observations")
    docs = []
    for doc in documents:
        if (type(doc) is not dict or doc.get("status") not in DOC_CODES
                or doc.get("fix_verified") is not False
                or type(doc.get("receipt_id")) is not str
                or HEX64.fullmatch(doc["receipt_id"]) is None
                or doc.get("claimed_sha_matched") not in (True, False)
                or doc.get("public_content_checked") not in (True, False)):
            raise ObservationError("unsafe official document observation")
        observed = doc["public_content_checked"]
        matched = doc["claimed_sha_matched"]
        digest = doc.get("actual_http_body_sha256")
        if (observed != (doc["status"] != "PUBLIC_DOCUMENT_UNAVAILABLE_NO_GO")
                or (matched and (not observed or doc["status"] !=
                    "OFFICIAL_RESPONSE_BYTES_SHA_MATCH_NOT_TRUST_SIGNOFF"))
                or (observed and (
                    type(digest) is not str or HEX64.fullmatch(digest) is None))
                or (not observed and digest is not None)):
            raise ObservationError("inconsistent official byte comparison status")
        docs.append({
            "v05_claim_receipt_id": doc["receipt_id"],
            "status": doc["status"],
            "response_body_sha256": digest if observed else None,
            "response_bytes_observed": observed,
            "claim_sha_matched_response": matched,
        })
    if len({d["v05_claim_receipt_id"] for d in docs}) != len(docs):
        raise ObservationError("same claim included more than once")
    return {
        "schema": SCHEMA, "item_id": item["item_id"],
        "source_id": item["source_id"],
        "public_url": item["public_url"],
        "revision_hint": meta["revision_hint"],
        "v09_report_sha256": report["audit_report_sha256"],
        "metadata_status": meta["status"],
        "metadata_observed": meta["metadata_observed"],
        "identity_matched": meta["identity_matched"],
        "documents": docs,
        "fix_verified": False, "rule_approved": False,
        "auto_promoted": False, "source_code_executed": False,
        "approval_state": "OBSERVED_PUBLIC_METADATA_NOT_FIX_VERIFIED",
    }


def _check_basis(value: dict) -> dict:
    if type(value) is not dict or set(value) != STORED_KEYS:
        raise ObservationError("unexpected observation record fields")
    if (value.get("schema") != SCHEMA
            or type(value.get("item_id")) is not str
            or HEX64.fullmatch(value["item_id"]) is None
            or type(value.get("source_id")) is not str
            or not value["source_id"].startswith("repo:")
            or type(value.get("public_url")) is not str
            or len(value["public_url"]) > 240
            or type(value.get("revision_hint")) is not str
            or HEX40.fullmatch(value["revision_hint"]) is None
            or type(value.get("v09_report_sha256")) is not str
            or HEX64.fullmatch(value["v09_report_sha256"]) is None
            or value.get("metadata_status") not in METADATA_CODES
            or value.get("metadata_observed") not in (True, False)
            or value.get("identity_matched") not in (True, False)
            or value.get("fix_verified") is not False
            or value.get("rule_approved") is not False
            or value.get("auto_promoted") is not False
            or value.get("source_code_executed") is not False
            or value.get("approval_state") !=
                "OBSERVED_PUBLIC_METADATA_NOT_FIX_VERIFIED"
            or type(value.get("documents")) is not list
            or len(value["documents"]) > 2):
        raise ObservationError("invalid unapproved observation basis")
    for doc in value["documents"]:
        if (type(doc) is not dict or set(doc) != {
                "v05_claim_receipt_id", "status", "response_body_sha256",
                "response_bytes_observed", "claim_sha_matched_response"}
                or doc["status"] not in DOC_CODES
                or type(doc["v05_claim_receipt_id"]) is not str
                or HEX64.fullmatch(doc["v05_claim_receipt_id"]) is None
                or doc["response_bytes_observed"] not in (True, False)
                or doc["claim_sha_matched_response"] not in (True, False)):
            raise ObservationError("invalid document summary")
        seen = doc["response_bytes_observed"]
        digest = doc["response_body_sha256"]
        if (seen != (doc["status"] != "PUBLIC_DOCUMENT_UNAVAILABLE_NO_GO")
                or (seen and (
                    type(digest) is not str or HEX64.fullmatch(digest) is None))
                or (not seen and digest is not None)
                or (doc["claim_sha_matched_response"] != (
                    doc["status"] ==
                    "OFFICIAL_RESPONSE_BYTES_SHA_MATCH_NOT_TRUST_SIGNOFF"))):
            raise ObservationError("untrusted document summary flags")
    if value["identity_matched"] != (
            value["metadata_observed"] and value["metadata_status"] in {
                "PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED",
                "PUBLIC_COMMIT_IDENTITY_MATCHED_NOT_FIX_VERIFIED"}):
        raise ObservationError("untrusted metadata status flags")
    return value


def _read_records(folder: Path) -> list[dict]:
    if not folder.exists():
        return []
    if folder.is_symlink() or not folder.is_dir():
        raise ObservationError("unsafe records folder")
    paths = sorted(folder.iterdir())
    if len(paths) > MAX_RECORDS:
        raise ObservationError("observation records bound exceeded")
    out = []
    seen = set()
    for path in paths:
        if (path.is_symlink() or not path.is_file()
                or HEX64.fullmatch(path.stem) is None
                or path.suffix != ".json"
                or path.stat().st_size > MAX_FILE_BYTES):
            raise ObservationError("unexpected observation file")
        try:
            obj = json.loads(path.read_bytes().decode("ascii"))
        except (ValueError, UnicodeError, OSError) as exc:
            raise ObservationError("invalid observation encoding") from exc
        if (type(obj) is not dict or set(obj) != STORED_KEYS | {
                "receipt_id", "recorded_utc", "integrity_sha256"}):
            raise ObservationError("invalid receipt envelope")
        basis = _check_basis({k: obj[k] for k in STORED_KEYS})
        rid = _digest(basis)
        if (rid != obj["receipt_id"] or path.stem != rid or rid in seen
                or type(obj["recorded_utc"]) is not str
                or UTC.fullmatch(obj["recorded_utc"]) is None
                or type(obj["integrity_sha256"]) is not str
                or obj["integrity_sha256"] != _digest({
                    **basis, "receipt_id": rid,
                    "recorded_utc": obj["recorded_utc"]})):
            raise ObservationError("observation receipt hash mismatch")
        seen.add(rid)
        out.append(obj)
    return out


def _source_index(handoff: object) -> dict[str, dict]:
    complete, rows = _candidate_rows(handoff)
    if not complete:
        raise ObservationError("source handoff incomplete")
    index = {}
    for row in rows:
        ident = row["library_item_id"]
        if ident in index:
            raise ObservationError("duplicate source candidate")
        if (row.get("human_approved") is not False
                or row.get("export_allowed") is not False
                or row.get("lifecycle") != "UNVERIFIED_CANDIDATE_ONLY"):
            raise ObservationError("forged source approval")
        index[ident] = row
    return index


def _linked(record: dict, row: dict) -> bool:
    return (record["source_id"] == row["source_id"]
            and record["public_url"] == row["public_url"]
            and record["revision_hint"] == row["revision_hint"])


def replay_observations(root: Path, *, handoff_factory=None) -> dict:
    """Read-only, fail closed on changed source link or any corrupt record."""
    root = _root(root)
    factory = prepare_verification_handoff if handoff_factory is None else handoff_factory
    index = _source_index(factory(root))
    records = _read_records(_directory(root))
    per_item = {}
    for obj in records:
        row = index.get(obj["item_id"])
        if row is None or not _linked(obj, row):
            raise ObservationError("stale or misbound public source observation")
        per_item[obj["item_id"]] = per_item.get(obj["item_id"], 0) + 1
    return {
        "schema": AUDIT_SCHEMA,
        "status": "PUBLIC_OBSERVATIONS_INTEGRITY_ONLY_NOT_FIX_VERIFIED",
        "source_linked_candidates": len(index),
        "integrity_checked_observation_count": len(records),
        "items_with_observations": len(per_item),
        "items_without_observations": len(index) - len(per_item),
        "source_linkage_valid": True,
        "observations": [{
            "item_id": obj["item_id"],
            "source_id": obj["source_id"],
            "revision_hint": obj["revision_hint"],
            "metadata_status": obj["metadata_status"],
            "identity_matched": obj["identity_matched"],
            "document_sha_checks": len(obj["documents"]),
            "receipt_id": obj["receipt_id"],
            "recorded_utc": obj["recorded_utc"],
            "independently_verified_fix": False,
            "owner_approved": False,
        } for obj in records],
        "actual_independent_fix_regressions": 0,
        "verified_version_ranges": 0,
        "verified_legal_licenses": 0,
        "signed_rules": 0,
        "production_approved": False,
        "automatic_promotions": 0,
        "operating_db_writes": 0,
        "scheduler_changes": 0,
    }


def record_explicit_observation(root: Path, *, item_id: str,
                                probe=None, clock=None) -> dict:
    """One explicit owner command invokes V0.9, then atomically stores receipt."""
    root = _root(root)
    if type(item_id) is not str or HEX64.fullmatch(item_id) is None:
        raise ObservationError("exact candidate SHA required")
    run = perform_public_probe_batch if probe is None else probe
    report = run(root, item_id=item_id, top=1)
    basis = _check_basis(_snapshot(report))
    if basis["item_id"] != item_id:
        raise ObservationError("probe returned wrong source candidate")
    folder = _directory(root, create=True)
    lock = folder.parent / ".record-v10.lock"
    if lock.is_symlink():
        raise ObservationError("untrusted observation writer lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ObservationError("observation writer already locked") from exc
    temp = None
    try:
        os.close(fd)
        _read_records(folder)
        rid = _digest(basis)
        dest = folder / (rid + ".json")
        if dest.exists():
            return {"status": "ALREADY_OBSERVED_NOT_FIX_VERIFIED",
                    "receipt_id": rid, "fix_verified": False,
                    "operating_db_writes": 0}
        if len(list(folder.iterdir())) >= MAX_RECORDS:
            raise ObservationError("observation storage full")
        now = datetime.now(timezone.utc) if clock is None else clock
        if not isinstance(now, datetime) or now.tzinfo is None or (
                now.utcoffset().total_seconds() != 0):
            raise ObservationError("observation clock must be UTC")
        stamp = now.replace(microsecond=0).isoformat()
        receipt = {**basis, "receipt_id": rid, "recorded_utc": stamp}
        receipt["integrity_sha256"] = _digest(receipt)
        raw = _canonical(receipt) + b"\n"
        if len(raw) > MAX_FILE_BYTES:
            raise ObservationError("bounded observation size exceeded")
        with tempfile.NamedTemporaryFile(dir=folder.parent, mode="wb",
                                         prefix=".stage-observation-", suffix=".tmp",
                                         delete=False) as f:
            temp = Path(f.name)
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        if dest.exists():
            raise ObservationError("observation target changed during commit")
        os.replace(temp, dest)
        temp = None
        return {"status": "PUBLIC_OBSERVATION_STORED_NOT_FIX_VERIFIED",
                "receipt_id": rid, "fix_verified": False,
                "approved_rules": 0, "operating_db_writes": 0}
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(
        description="UCIE explicit public observation receipt, never fix approval")
    p.add_argument("--record-public", action="store_true", required=True)
    p.add_argument("--item-id", required=True)
    args = p.parse_args()
    try:
        result = record_explicit_observation(
            Path(__file__).resolve().parents[2], item_id=args.item_id)
    except (ObservationError, ValueError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "PUBLIC_OBSERVATION_NO_GO",
                          "error_type": type(exc).__name__}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
