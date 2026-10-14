"""UCIE Stage 4: local candidate knowledge ledger, never automatic rule promotion.

No network, external projects, downloaded patches, or code execution.
The legacy miner database is opened READ ONLY. New data goes to an
independent SQLite database in the same UCIE runtime directory.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import sqlite3

SOURCES = ("python/cpython", "PowerShell/PowerShell")
SCHEMA = "UCIE_KNOWLEDGE_V1"


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_runtime(root: Path) -> Path:
    if root.is_symlink():
        raise ValueError("symlinked checkout denied")
    runtime = root / "runtime"
    if runtime.is_symlink() or (runtime.exists() and not runtime.is_dir()):
        raise ValueError("unsafe runtime directory")
    runtime.mkdir(exist_ok=True)
    return runtime


def open_knowledge(root: Path) -> sqlite3.Connection:
    runtime = _safe_runtime(root)
    path = runtime / "knowledge.sqlite3"
    if path.is_symlink():
        raise ValueError("symlinked knowledge database denied")
    con = sqlite3.connect(path, timeout=10)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("""CREATE TABLE IF NOT EXISTS evidence (
        source TEXT NOT NULL, pr_number INTEGER NOT NULL,
        url TEXT NOT NULL, merge_timestamp TEXT NOT NULL,
        evidence_sha256 TEXT NOT NULL, first_seen_utc TEXT NOT NULL,
        provenance_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
        license_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
        security_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
        disposition TEXT NOT NULL DEFAULT 'CANDIDATE',
        PRIMARY KEY(source,pr_number),
        CHECK(provenance_status='UNVERIFIED'),
        CHECK(license_status='UNVERIFIED'),
        CHECK(security_status='UNVERIFIED'),
        CHECK(disposition IN ('CANDIDATE','QUARANTINED','RETRACTED'))
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS rule_candidates (
        rule_id TEXT PRIMARY KEY, source TEXT NOT NULL,
        pr_number INTEGER NOT NULL, pattern_code TEXT NOT NULL,
        proposal_sha256 TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'UNVERIFIED_CANDIDATE_ONLY',
        created_utc TEXT NOT NULL,
        FOREIGN KEY(source,pr_number) REFERENCES evidence(source,pr_number),
        CHECK(status='UNVERIFIED_CANDIDATE_ONLY')
    )""")
    con.commit()
    return con


def import_miner_candidates(root: Path) -> dict:
    """Idempotently import only proven local miner metadata; never raw patches."""
    runtime = _safe_runtime(root)
    existing = runtime / "public_miner.sqlite3"
    if existing.is_symlink() or not existing.is_file():
        raise ValueError("missing safe legacy DB")
    src = sqlite3.connect(existing.as_uri() + "?mode=ro", uri=True)
    dest = None
    try:
        if src.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("legacy database failed integrity check")
        rows = src.execute("""SELECT source,pr_number,public_url,merged_at,
                                     evidence_sha256,status FROM candidates""").fetchall()
        checked = []
        for source,number,url,merged,sha,status in rows:
            if (source not in SOURCES or type(number) is not int or number < 1
                    or url != f"https://github.com/{source}/pull/{number}"
                    or not isinstance(merged,str) or len(merged)>40
                    or not isinstance(sha,str) or not re.fullmatch(r"[a-f0-9]{64}",sha)
                    or status != "UNVERIFIED_CANDIDATE_ONLY"):
                raise ValueError("legacy candidate outside permitted schema")
            checked.append((source,number,url,merged,sha,_utc()))
        dest = open_knowledge(root)
        with dest:
            before = dest.total_changes
            dest.executemany("""INSERT OR IGNORE INTO evidence
                 (source,pr_number,url,merge_timestamp,evidence_sha256,first_seen_utc)
                 VALUES (?,?,?,?,?,?)""",checked)
            inserted = dest.total_changes - before
        return {"schema":SCHEMA,"status":"IMPORTED_UNVERIFIED",
                "source_rows":len(rows),"new_rows":inserted,
                "knowledge_rows":dest.execute("SELECT COUNT(*) FROM evidence").fetchone()[0],
                "promoted_rules":0}
    finally:
        src.close()
        if dest is not None:
            dest.close()


def propose_rule(root: Path, *, source: str, number: int,
                 pattern_code: str, proposal_digest: str) -> dict:
    """Store a bounded hash-only manual proposal. No verified status exists."""
    if (source not in SOURCES or type(number) is not int or number < 1
            or not isinstance(pattern_code,str)
            or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}",pattern_code)
            or not isinstance(proposal_digest,str)
            or not re.fullmatch(r"[a-f0-9]{64}",proposal_digest)):
        raise ValueError("invalid proposal metadata")
    key = hashlib.sha256(
        f"{source}:{number}:{pattern_code}:{proposal_digest}".encode("utf-8")
    ).hexdigest()
    with open_knowledge(root) as con:
        con.execute("""INSERT OR IGNORE INTO rule_candidates
            (rule_id,source,pr_number,pattern_code,proposal_sha256,created_utc)
            VALUES (?,?,?,?,?,?)""",
            (key,source,number,pattern_code,proposal_digest,_utc()))
    return {"rule_id":key,"status":"UNVERIFIED_CANDIDATE_ONLY","auto_promoted":False}


def backup_knowledge(root: Path, destination: Path) -> Path:
    """Use SQLite online backup. Refuse overwriting any previous backup."""
    runtime = _safe_runtime(root)
    source = runtime / "knowledge.sqlite3"
    if source.is_symlink() or not source.is_file():
        raise ValueError("knowledge database absent")
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError("backup destination already exists")
    if destination.parent.resolve() != runtime.resolve():
        raise ValueError("backup must remain in UCIE runtime")
    with sqlite3.connect(source.as_uri()+"?mode=ro",uri=True) as inp:
        if inp.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("knowledge database corrupt")
        try:
            with sqlite3.connect(destination) as out:
                inp.backup(out)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    return destination
