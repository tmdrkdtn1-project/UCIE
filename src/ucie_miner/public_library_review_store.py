"""UCIE-only, opt-in signed public-review history and revocation ledger.

Uses existing signed-review validation, canonical JSON and Ed25519 helpers.
No automatic release approval, project inspection, scheduled I/O or exports.
The hash chain detects local edits, not rollback of the entire SQLite file:
callers must pin/check an independently retained trusted head checkpoint.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ucie_public.policy import PolicyError
from ucie_public.production_release import _parse_date
from ucie_public.rulepack import canonical_json, key_id

from .public_discovery import SOURCES, DiscoveryError
from .public_library_signed_review import (
    ENTRY_FIELDS, EVENT_FIELDS, EVENT_SCHEMA, REVIEW_FIELDS,
    SHA40, SHA64, SIGNATURE, VERSION,
    inspect_library_signed_review_ledger,
)

DB_NAME = "library_signed_review_history.sqlite3"
SCHEMA = "UCIE_LIBRARY_SIGNED_REVIEW_HISTORY_V1"
APP_ID = 0x55434C42
VERSION_NUMBER = 1
ZERO_HEAD = "0" * 64
MAX_STORED_EVENTS = 10000
MAX_INSERT_EVENTS = 24
URL_PR = re.compile(r"[1-9][0-9]{0,8}\Z")


def _path(root: Path) -> Path:
    root = Path(root)
    # Restrict this tool to an explicitly selected UCIE checkout namespace.
    if root.name.casefold() != "ucie" or root.is_symlink() or not root.is_dir():
        raise PolicyError("explicit UCIE-only directory is required")
    runtime = root / "runtime"
    if runtime.is_symlink() or not runtime.is_dir():
        raise PolicyError("existing UCIE runtime directory is required")
    db = runtime / DB_NAME
    if db.is_symlink() or (db.exists() and not db.is_file()):
        raise PolicyError("unsafe UCIE signed-review history path")
    return db


def _validate_trust(owner_trust, qa_trust):
    if (not isinstance(owner_trust, Ed25519PublicKey)
            or not isinstance(qa_trust, Ed25519PublicKey)
            or key_id(owner_trust) == key_id(qa_trust)):
        raise PolicyError("distinct independently verified Ed25519 trust keys required")


def _utc(now):
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise PolicyError("timezone-aware inspection required")
    return now.astimezone(timezone.utc)


def _head_required(value):
    if not isinstance(value, str) or not SHA64.fullmatch(value):
        raise PolicyError("independent expected head SHA256 required")


def _source_url(claim):
    url = claim["public_url"]
    if type(url) is not str:
        raise PolicyError("invalid public research URL")
    for source in SOURCES:
        prefix = "https://github.com/" + source + "/pull/"
        if url.startswith(prefix):
            number = url[len(prefix):]
            if URL_PR.fullmatch(number):
                return url
            raise PolicyError("noncanonical approved public PR identity")
    prefix = "https://github.com/git/git/commit/"
    if url.startswith(prefix) and SHA40.fullmatch(url[len(prefix):]):
        return url
    raise PolicyError("public source outside UCIE allowlist")


def _pairs_unique(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise PolicyError("duplicate JSON event property")
        obj[key] = value
    return obj


def _decode_and_verify(record_blob, owner_trust, qa_trust, now):
    if (type(record_blob) is not bytes or len(record_blob) > 8192):
        raise PolicyError("oversized or invalid review history event")
    try:
        entry = json.loads(record_blob.decode("utf-8"),
                           object_pairs_hook=_pairs_unique)
    except (ValueError, UnicodeError) as exc:
        raise PolicyError("invalid signed review history JSON") from exc
    if type(entry) is not dict or set(entry) != ENTRY_FIELDS:
        raise PolicyError("unexpected review history record")
    if canonical_json(entry) != record_blob:
        raise PolicyError("noncanonical review history record")
    claim = entry["claim"]
    if (type(claim) is not dict or set(claim) != EVENT_FIELDS
            or claim["schema"] != EVENT_SCHEMA
            or claim["action"] not in ("REVIEW_ATTESTED", "REVOKE")
            or type(claim["serial"]) is not int
            or not 1 <= claim["serial"] <= 10000000
            or type(claim["pinned_revision_sha"]) is not str
            or not SHA40.fullmatch(claim["pinned_revision_sha"])
            or type(claim["evidence_sha256"]) is not str
            or not SHA64.fullmatch(claim["evidence_sha256"])):
        raise PolicyError("invalid pinned signed review identity")
    _source_url(claim)
    issued = _parse_date(claim["issued_utc"])
    if issued > now:
        raise PolicyError("future-dated persisted review event")
    owner_sig = entry["owner_signature_hex"]
    if type(owner_sig) is not str or not SIGNATURE.fullmatch(owner_sig):
        raise PolicyError("missing signed owner decision")
    claim_bytes = canonical_json(claim)
    try:
        owner_trust.verify(bytes.fromhex(owner_sig), claim_bytes)
    except (InvalidSignature, ValueError) as exc:
        raise PolicyError("persisted owner decision signature invalid") from exc

    if claim["action"] == "REVIEW_ATTESTED":
        if (type(claim["version_claim"]) is not str
                or not VERSION.fullmatch(claim["version_claim"])
                or type(claim["review_evidence_sha256"]) is not str
                or not SHA64.fullmatch(claim["review_evidence_sha256"])
                or type(claim["review_claims"]) is not dict
                or set(claim["review_claims"]) != REVIEW_FIELDS
                or any(claim["review_claims"][k] is not True
                       for k in REVIEW_FIELDS)):
            raise PolicyError("invalid signed independent-review claims")
        qa_sig = entry["qa_signature_hex"]
        if type(qa_sig) is not str or not SIGNATURE.fullmatch(qa_sig):
            raise PolicyError("missing independent QA signature")
        try:
            qa_trust.verify(bytes.fromhex(qa_sig), claim_bytes)
        except (InvalidSignature, ValueError) as exc:
            raise PolicyError("persisted QA signature invalid") from exc
        expiry = _parse_date(claim["expires_utc"])
        if expiry <= issued or expiry - issued > timedelta(days=30):
            raise PolicyError("invalid signed review claim lifetime")
        state = ("EXPIRED_REVIEW_CLAIM_NO_GO" if expiry <= now else
                 "SIGNED_REVIEW_CLAIM_NO_GO")
    else:
        if (claim["version_claim"] is not None
                or claim["review_evidence_sha256"] is not None
                or claim["review_claims"] is not None
                or claim["expires_utc"] is not None
                or entry["qa_signature_hex"] is not None):
            raise PolicyError("invalid owner-only revocation tombstone")
        state = "OWNER_REVOKED_NO_GO"
    return entry, state


def _event_hash(previous, record_blob):
    # Signed record is kept byte-identical; previous_head binds ordering.
    return hashlib.sha256(
        b"UCIE_LIBRARY_REVIEW_HISTORY_V1\n" +
        previous.encode("ascii") + b"\n" + record_blob).hexdigest()


def _schema(conn, *, create=False):
    if create:
        conn.execute(f"PRAGMA application_id={APP_ID}")
        conn.execute(f"PRAGMA user_version={VERSION_NUMBER}")
        conn.execute("""CREATE TABLE review_history (
            seq INTEGER PRIMARY KEY,
            serial INTEGER NOT NULL UNIQUE,
            public_url TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('REVIEW_ATTESTED','REVOKE')),
            signed_event BLOB NOT NULL,
            previous_hash TEXT NOT NULL,
            event_hash TEXT NOT NULL UNIQUE
        )""")
        conn.execute("""CREATE TRIGGER deny_review_history_update
            BEFORE UPDATE ON review_history
            BEGIN SELECT RAISE(ABORT, 'append_only'); END""")
        conn.execute("""CREATE TRIGGER deny_review_history_delete
            BEFORE DELETE ON review_history
            BEGIN SELECT RAISE(ABORT, 'append_only'); END""")
    app = conn.execute("PRAGMA application_id").fetchone()[0]
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    cols = [r[1] for r in conn.execute("PRAGMA table_info(review_history)")]
    triggers = {r[0]: r[1] for r in conn.execute(
        "SELECT name,sql FROM sqlite_master WHERE type='trigger'")}
    if (app != APP_ID or version != VERSION_NUMBER
            or cols != ["seq", "serial", "public_url", "action",
                        "signed_event", "previous_hash", "event_hash"]
            or set(triggers) != {
                "deny_review_history_update", "deny_review_history_delete"}
            or any("RAISE(ABORT" not in sql for sql in triggers.values())):
        raise PolicyError("wrong UCIE signed-review history schema")


def _scan(conn, *, owner_trust, qa_trust, now):
    if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise PolicyError("UCIE review history DB integrity failed")
    rows = conn.execute(
        "SELECT seq,serial,public_url,action,signed_event,"
        "previous_hash,event_hash FROM review_history ORDER BY seq"
    ).fetchall()
    if len(rows) > MAX_STORED_EVENTS:
        raise PolicyError("UCIE signed-review history capacity exceeded")
    prev = ZERO_HEAD
    high = 0
    latest = {}
    for index, (seq, serial, url, action, raw, previous, event_sha) in enumerate(rows, 1):
        if (type(seq) is not int or seq != index
                or type(serial) is not int or serial <= high
                or type(previous) is not str or previous != prev
                or type(event_sha) is not str or not SHA64.fullmatch(event_sha)
                or type(url) is not str or type(action) is not str):
            raise PolicyError("review history has a gap, rollback, or broken order")
        entry, state = _decode_and_verify(raw, owner_trust, qa_trust, now)
        claim = entry["claim"]
        if (serial != claim["serial"] or url != claim["public_url"]
                or action != claim["action"]
                or _event_hash(previous, raw) != event_sha
                or (url in latest and latest[url]["revoked"] and action != "REVOKE")):
            raise PolicyError("signed review history diverges or resurrects revocation")
        high = serial
        prev = event_sha
        latest[url] = {"public_url": url, "serial": serial, "state": state,
                       "revoked": action == "REVOKE",
                       "pinned_revision_sha": claim["pinned_revision_sha"],
                       "evidence_sha256": claim["evidence_sha256"],
                       "version_claim": claim["version_claim"],
                       "review_evidence_sha256": claim["review_evidence_sha256"],
                       "distribution_authorized": False}
    return {"count": len(rows), "highest_serial": high,
            "head_sha256": prev, "latest": latest}


def _summary(state, *, existed, wrote, checkpoint_matched):
    latest = list(sorted(state["latest"].values(),
                         key=lambda item: item["public_url"]))
    return {
        "schema": SCHEMA,
        "status": ("LOCAL_SIGNED_REVIEW_HISTORY_APPENDED_NO_GO" if wrote
                   else "LOCAL_SIGNED_REVIEW_HISTORY_INSPECTED_NO_GO"
                   if existed else "LOCAL_SIGNED_REVIEW_HISTORY_ABSENT_NO_GO"),
        "head_sha256": state["head_sha256"],
        "highest_serial": state["highest_serial"],
        "event_count": state["count"],
        "latest_reference_states": latest,
        "owner_revoked_reference_count": sum(x["revoked"] for x in latest),
        "hash_chain_and_signatures_checked": True,
        "caller_checkpoint_matched": checkpoint_matched,
        "external_rollback_protection_proven": False,
        "operating_miner_or_knowledge_db_modified": False,
        "approved_installable_skills": 0,
        "production_approved": False,
        "distribution_authorized": False,
        "automatic_skill_injection": False,
        "scheduler_registered": False,
        "sqlite_writes": wrote,
    }


def inspect_local_library_review_history(
        root: Path, *, owner_trust: Ed25519PublicKey,
        qa_trust: Ed25519PublicKey, expected_head_sha256=None, at_time=None):
    """Read-only scan. External head checkpoint is optional but recommended."""
    _validate_trust(owner_trust, qa_trust)
    now = _utc(at_time)
    if expected_head_sha256 is not None:
        _head_required(expected_head_sha256)
    path = _path(root)
    if not path.exists():
        if expected_head_sha256 is not None and expected_head_sha256 != ZERO_HEAD:
            raise PolicyError("missing UCIE history violates trusted checkpoint")
        state = {"count": 0, "head_sha256": ZERO_HEAD, "highest_serial": 0,
                 "latest": {}}
        return _summary(state, existed=False, wrote=0,
                        checkpoint_matched=expected_head_sha256 is not None)
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro",
                                     uri=True, timeout=3)) as conn:
            conn.execute("PRAGMA query_only=ON")
            _schema(conn)
            state = _scan(conn, owner_trust=owner_trust, qa_trust=qa_trust,
                          now=now)
    except sqlite3.DatabaseError as exc:
        raise PolicyError("UCIE review history read failed") from exc
    if expected_head_sha256 is not None and state["head_sha256"] != expected_head_sha256:
        raise PolicyError("trusted UCIE head checkpoint mismatch")
    return _summary(state, existed=True, wrote=0,
                    checkpoint_matched=expected_head_sha256 is not None)


def append_local_library_review_history(
        root: Path, current: dict, entries: list, *,
        owner_trust: Ed25519PublicKey, qa_trust: Ed25519PublicKey,
        expected_head_sha256: str, allow_disk_write=False,
        at_time=None):
    """Operator-opt-in atomic append of authenticated review assertions.

    The expected head is a compare-and-swap lease, not an independent anchor
    by itself. No signing keys are loaded or ever stored, no candidate is
    promoted. An existing revoked public reference cannot be reapproved.
    """
    _validate_trust(owner_trust, qa_trust)
    now = _utc(at_time)
    _head_required(expected_head_sha256)
    if (allow_disk_write is not True or type(entries) is not list
            or not 1 <= len(entries) <= MAX_INSERT_EVENTS):
        raise PolicyError("explicit bounded UCIE-only append approval required")
    # Reuse existing source/pinned-evidence validation and signature gate.
    inspect_library_signed_review_ledger(
        current, entries, owner_trust=owner_trust, qa_trust=qa_trust,
        at_time=now)
    path = _path(root)
    existed = path.exists()
    try:
        with closing(sqlite3.connect(
                path.as_uri() + ("?mode=rw" if existed else "?mode=rwc"),
                uri=True, timeout=5)) as conn:
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("BEGIN IMMEDIATE")
            _schema(conn, create=not existed)
            before = _scan(conn, owner_trust=owner_trust, qa_trust=qa_trust,
                           now=now)
            if before["head_sha256"] != expected_head_sha256:
                raise PolicyError("expected head changed or history was rolled back")
            if before["count"] + len(entries) > MAX_STORED_EVENTS:
                raise PolicyError("UCIE review history full")
            previous = before["head_sha256"]
            serial = before["highest_serial"]
            latest = before["latest"]
            for entry in entries:
                claim = entry["claim"]
                url = claim["public_url"]
                if (claim["serial"] <= serial
                        or (url in latest and latest[url]["revoked"]
                            and claim["action"] != "REVOKE")):
                    raise PolicyError("serial replay or revoked public reference")
                raw = canonical_json(entry)
                new_head = _event_hash(previous, raw)
                conn.execute(
                    "INSERT INTO review_history "
                    "(seq,serial,public_url,action,signed_event,previous_hash,event_hash) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (before["count"] + 1,
                     claim["serial"], url, claim["action"], raw, previous,
                     new_head))
                previous = new_head
                serial = claim["serial"]
                latest[url] = {"revoked": claim["action"] == "REVOKE"}
                before["count"] += 1
            # Verify final chain and signatures before committing.
            after = _scan(conn, owner_trust=owner_trust, qa_trust=qa_trust,
                          now=now)
            if after["head_sha256"] != previous:
                raise PolicyError("post-append chain mismatch")
            conn.commit()
    except sqlite3.DatabaseError as exc:
        raise PolicyError("UCIE review history append failed") from exc
    return _summary(after, existed=True, wrote=len(entries),
                    checkpoint_matched=True)
