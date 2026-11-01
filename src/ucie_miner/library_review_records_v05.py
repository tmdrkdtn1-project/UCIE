"""UCIE V0.5: explicit, append-only PUBLIC evidence *claim* intake.

A public URL and user-supplied digest are NOT independently observed evidence,
a passed regression, released-version proof, legal license signoff, or owner
authorization. Receipts stay CLAIM_RECEIVED_UNVERIFIED. No auto-promotion.

Only the UCIE checkout and a new dedicated review receipt directory are used.
The existing operating SQLite databases and scheduled collector are untouched.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

from .library_review_v04 import (
    READY as DOSSIER_READY, dossier_existing_public_candidate,
)
from .public_discovery import SOURCES

SCHEMA = "UCIE_PUBLIC_EVIDENCE_RECEIPT_V05"
VIEW_SCHEMA = "UCIE_PUBLIC_EVIDENCE_RECEIPT_STATUS_V05"
CLAIM_ONLY = "CLAIM_RECEIVED_UNVERIFIED"
GATES = frozenset((
    "VERSION_APPLICABILITY", "LICENSE", "INDEPENDENT_REGRESSION",
    "SECURITY_REVIEW",
))
HEX = re.compile(r"[0-9a-f]{64}\Z")
VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,31}\Z")
UTC = re.compile(r"20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]\+00:00\Z")
FILE = re.compile(r"[0-9a-f]{64}\.json\Z")
PR = re.compile(r"https://github\.com/[^/?#]+/[^/?#]+/pull/[1-9][0-9]{0,9}\Z")
COMMIT = re.compile(r"https://github\.com/[^/?#]+/[^/?#]+/commit/[0-9a-f]{40}\Z")
ACTIONS = re.compile(r"https://github\.com/[^/?#]+/[^/?#]+/actions/runs/[1-9][0-9]{0,15}\Z")
LICENSE_FILE = re.compile(r"https://github\.com/[^/?#]+/[^/?#]+/blob/[0-9a-f]{40}/(?:LICENSE|COPYING)(?:\.[A-Za-z0-9._-]{1,20})?\Z")
PUBLIC_DOC_HOSTS = frozenset((
    "docs.python.org", "learn.microsoft.com", "git-scm.com",
    "modelcontextprotocol.io", "docs.github.com",
))
CORE_FIELDS = frozenset((
    "schema", "item_id", "source_id", "source_sha256", "gate",
    "public_evidence_url", "claimed_document_sha256", "version_hint",
    "status", "independent_verification",
))
MAX_RECEIPTS = 500
MAX_BYTES = 2100


class ClaimError(ValueError):
    pass


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")).encode("ascii")


def _sha(value: dict) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _root(root: Path) -> Path:
    path = Path(root)
    if path.is_symlink() or path.name.casefold() != "ucie" or not path.is_dir():
        raise ClaimError("dedicated UCIE checkout required")
    if os.name == "nt" and path.resolve() != Path("D:/UCIE").resolve():
        raise ClaimError("owner-local D:/UCIE required")
    return path


def _location(root: Path, *, create: bool = False) -> Path:
    runtime = root / "runtime"
    folder = runtime / "public_review_v05"
    receipts = folder / "receipts"
    for part in (runtime, folder, receipts):
        if part.is_symlink():
            raise ClaimError("review path symlink rejected")
        if part.exists() and not part.is_dir():
            raise ClaimError("review path not a directory")
    if create:
        receipts.mkdir(parents=True, exist_ok=True)
    return receipts


def _public_evidence_url(url: object, *, source_id: str) -> str:
    if type(url) is not str or not 20 <= len(url) <= 230:
        raise ClaimError("invalid bounded public citation")
    if any(ord(ch) < 33 or ord(ch) > 126 for ch in url):
        raise ClaimError("non-ASCII/unsafe public citation")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.port is not None
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or not parsed.path.startswith("/")
            or "//" in parsed.path or ".." in parsed.path
            or "%" in parsed.path or "\\" in parsed.path):
        raise ClaimError("unapproved public citation URL shape")
    if source_id not in {"repo:" + name for name in SOURCES}:
        raise ClaimError("candidate source not independently allowlisted")
    if parsed.hostname == "github.com":
        expected = "https://github.com/" + source_id.removeprefix("repo:") + "/"
        if not url.startswith(expected) or not any(pattern.fullmatch(url)
                            for pattern in (PR, COMMIT, ACTIONS, LICENSE_FILE)):
            raise ClaimError("evidence outside approved repository paths")
    elif parsed.hostname in PUBLIC_DOC_HOSTS:
        if not re.fullmatch(r"/[A-Za-z0-9._/~:-]{1,190}", parsed.path):
            raise ClaimError("invalid official-document route")
    else:
        raise ClaimError("unapproved public evidence host")
    return url


def _core(dossier: dict, *, gate: str, url: str,
          claimed_sha: str, version_hint: str) -> dict:
    item = dossier["item"]
    if (dossier["status"] != DOSSIER_READY
            or dossier["source_linkage_checked"] is not True
            or dossier["owner_approved"] is not False
            or dossier["independently_verified"] is not False
            or type(gate) is not str or gate not in GATES
            or type(claimed_sha) is not str or HEX.fullmatch(claimed_sha) is None
            or type(version_hint) is not str or VERSION.fullmatch(version_hint) is None
            or type(item.get("evidence_sha256")) is not str
            or HEX.fullmatch(item["evidence_sha256"]) is None):
        raise ClaimError("candidate not eligible for unverified public claim")
    return {
        "schema": SCHEMA, "item_id": item["library_item_id"],
        "source_id": item["source_id"],
        "source_sha256": item["evidence_sha256"],
        "gate": gate,
        "public_evidence_url": _public_evidence_url(
            url, source_id=item["source_id"]),
        "claimed_document_sha256": claimed_sha,
        "version_hint": version_hint,
        "status": CLAIM_ONLY,
        "independent_verification": False,
    }


def _read_all(receipts: Path) -> list[dict]:
    if not receipts.exists():
        return []
    if receipts.is_symlink() or not receipts.is_dir():
        raise ClaimError("untrusted review receipts directory")
    paths = sorted(receipts.iterdir())
    if len(paths) > MAX_RECEIPTS:
        raise ClaimError("review receipt count limit exceeded")
    records = []
    seen = set()
    for path in paths:
        if (path.is_symlink() or not path.is_file()
                or FILE.fullmatch(path.name) is None
                or path.stat().st_size > MAX_BYTES):
            raise ClaimError("unrecognized or oversized review receipt")
        try:
            obj = json.loads(path.read_bytes().decode("ascii"))
        except (ValueError, UnicodeError, OSError) as exc:
            raise ClaimError("invalid evidence receipt encoding") from exc
        if type(obj) is not dict or set(obj) != CORE_FIELDS | {
                "receipt_id", "recorded_utc", "integrity_sha256"}:
            raise ClaimError("unrecognized receipt metadata fields")
        core = {k: obj[k] for k in CORE_FIELDS}
        rid = _sha(core)
        if (obj["receipt_id"] != rid or path.name != rid + ".json"
                or rid in seen or type(obj["recorded_utc"]) is not str
                or UTC.fullmatch(obj["recorded_utc"]) is None
                or type(obj["integrity_sha256"]) is not str
                or obj["integrity_sha256"] != _sha({
                    **core, "receipt_id": rid, "recorded_utc": obj["recorded_utc"],
                })
                or obj["status"] != CLAIM_ONLY
                or obj["independent_verification"] is not False
                or type(obj["item_id"]) is not str
                or HEX.fullmatch(obj["item_id"]) is None
                or type(obj["source_sha256"]) is not str
                or HEX.fullmatch(obj["source_sha256"]) is None
                or type(obj["claimed_document_sha256"]) is not str
                or HEX.fullmatch(obj["claimed_document_sha256"]) is None
                or obj["gate"] not in GATES
                or type(obj["version_hint"]) is not str
                or VERSION.fullmatch(obj["version_hint"]) is None):
            raise ClaimError("tampered or forged verification receipt")
        _public_evidence_url(obj["public_evidence_url"],
                             source_id=obj["source_id"])
        seen.add(rid)
        records.append(obj)
    return records


def review_claims(root: Path, dossier: dict) -> dict:
    """Read receipts ONLY after the current W04 handoff is revalidated."""
    root = _root(root)
    if (dossier.get("status") != DOSSIER_READY
            or dossier.get("source_linkage_checked") is not True):
        raise ClaimError("source provenance missing")
    existing = _read_all(_location(root))
    item = dossier["item"]
    relevant = []
    for receipt in existing:
        if receipt["item_id"] != item["library_item_id"]:
            continue
        if (receipt["source_id"] != item["source_id"]
                or receipt["source_sha256"] != item["evidence_sha256"]):
            raise ClaimError("review record source SHA is stale or tampered")
        relevant.append(receipt)
    return {
        "schema": VIEW_SCHEMA,
        "status": "SOURCE_LINKED_CLAIMS_UNVERIFIED_ONLY",
        "item_id": item["library_item_id"],
        "claims": relevant,
        "total_claims": len(relevant),
        "gate_counts": {gate: sum(r["gate"] == gate for r in relevant)
                        for gate in sorted(GATES)},
        "independently_verified": False,
        "owner_approved": False,
        "production_approved": False,
        "auto_promoted": False,
        "operating_database_writes": 0,
        "network_requests": 0,
    }


def record_claim(root: Path, *, item_id: str, gate: str,
                 evidence_url: str, claimed_sha256: str,
                 version_hint: str = "UNDETERMINED",
                 clock=None) -> dict:
    """EXPLICIT caller action only; write a dedicated immutable review receipt."""
    root = _root(root)
    if type(item_id) is not str or HEX.fullmatch(item_id) is None:
        raise ClaimError("invalid candidate identity")
    dossier = dossier_existing_public_candidate(root, item_id=item_id)
    if dossier.get("status") != DOSSIER_READY:
        raise ClaimError("source-linked candidate not found")
    core = _core(dossier, gate=gate, url=evidence_url,
                 claimed_sha=claimed_sha256, version_hint=version_hint)
    receipts = _location(root, create=True)
    folder = receipts.parent
    lock = folder / ".record-v05.lock"
    if lock.is_symlink():
        raise ClaimError("symlink lock denied")
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ClaimError("another or interrupted review write is locked") from exc
    temp = None
    try:
        os.close(fd)
        existing = _read_all(receipts)
        rid = _sha(core)
        target = receipts / (rid + ".json")
        for obj in existing:
            if obj["receipt_id"] == rid:
                return {"status": "ALREADY_RECORDED_UNVERIFIED",
                        "receipt_id": rid, "operating_database_writes": 0}
        if len(existing) >= MAX_RECEIPTS or target.exists():
            raise ClaimError("receipt directory at capacity or target conflict")
        now = datetime.now(timezone.utc) if clock is None else clock
        if (not isinstance(now, datetime) or now.tzinfo is None
                or now.utcoffset().total_seconds() != 0):
            raise ClaimError("timestamp must be UTC aware")
        recorded = now.replace(microsecond=0).isoformat()
        data = {**core, "receipt_id": rid, "recorded_utc": recorded}
        data["integrity_sha256"] = _sha(data)
        raw = _canonical(data) + b"\n"
        if len(raw) > MAX_BYTES:
            raise ClaimError("receipt exceeds byte limit")
        with tempfile.NamedTemporaryFile(mode="wb", dir=folder,
                                         prefix=".pending-v05-", suffix=".tmp",
                                         delete=False) as out:
            temp = Path(out.name)
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        if target.exists():
            raise ClaimError("receipt target appeared during exclusive write")
        os.replace(temp, target)
        temp = None
        return {"status": "CLAIM_STORED_UNVERIFIED", "receipt_id": rid,
                "operating_database_writes": 0,
                "candidate_approvals": 0,
                "independently_verified": False}
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="UCIE explicit public proof claim intake ONLY")
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--gate", required=True, choices=sorted(GATES))
    parser.add_argument("--evidence-url", required=True)
    parser.add_argument("--claimed-sha256", required=True)
    parser.add_argument("--version-hint", default="UNDETERMINED")
    parser.add_argument("--record-unverified", action="store_true", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        result = record_claim(root, item_id=args.item_id, gate=args.gate,
                              evidence_url=args.evidence_url,
                              claimed_sha256=args.claimed_sha256,
                              version_hint=args.version_hint)
    except (ClaimError, ValueError, OSError) as exc:
        # Never print raw URLs, filesystem paths or remote strings on failure.
        print(json.dumps({"status": "PUBLIC_CLAIM_INTAKE_NO_GO",
                          "error_type": type(exc).__name__}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
