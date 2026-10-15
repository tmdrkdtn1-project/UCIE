"""Stage 12: automatic *unverified* public candidate review preparation.

Deterministic rules/verification tasks from previously staged public metadata.
No untrusted source text, network traffic, executable code, model weight
training, signed Rulepack, rule approval, external project or scheduler access.
The separate ledger is ONLY an unsigned human-review queue.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from .public_candidate_staging import (
    _dedicated_path, _initialize as check_stage10,
    SHA40, SHA64, MAX_ROWS,
)
from .public_discovery import CATEGORIES, SOURCES, SOURCE_SKILL, DiscoveryError
from .skill_profiles import PROFILE

REVIEW_FILE = "stage12_unverified_review.sqlite3"
OPT_IN_FILENAME = "stage12_review_opt_in.txt"
OPT_IN_TOKEN = "UCIE_STAGE12_REVIEW_OPT_IN_V1"
REVIEW_APP_ID = 0x55434932
REVIEW_SCHEMA = 1
COLUMNS = (
    "fingerprint", "source", "reference", "skill_id", "pattern_code",
    "safe_guidance", "regression_plan", "evidence_sha", "first_seen_utc",
    "review_state",
)
REVIEW_STATUS = "UNVERIFIED_REVIEW_CANDIDATE_ONLY"


def _valid_tags(text):
    if not isinstance(text, str) or len(text) > 240:
        raise DiscoveryError("invalid staged public pattern tag length")
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise DiscoveryError("invalid staged public pattern tags") from exc
    if (not isinstance(value, list) or len(value) > len(CATEGORIES)
            or len(set(map(str, value))) != len(value)
            or any(type(x) is not str or x not in CATEGORIES for x in value)):
        raise DiscoveryError("untrusted staged public pattern tag")
    return value


def _rows_from_stage10(root):
    source_file = _dedicated_path(root)
    if not source_file.exists():
        raise DiscoveryError("Stage 10 public candidate ledger absent")
    with closing(sqlite3.connect(
            source_file.as_uri() + "?mode=ro", uri=True, timeout=3)) as conn:
        conn.execute("PRAGMA query_only=ON")
        check_stage10(conn, new=False)
        prs = conn.execute("""
            SELECT source,pr_number,merge_sha,evidence_sha,skill_id,
                   tags_json,missing_json,review_state
            FROM public_candidate_stage
        """).fetchall()
        commits = conn.execute("""
            SELECT git_commit_sha,message_sha256,tags_json,review_state
            FROM public_git_commit_stage
        """).fetchall()
    if len(prs) + len(commits) > MAX_ROWS:
        raise DiscoveryError("Stage 10 public candidate ledger too large")
    rows = []
    for source, number, sha, evidence, skill, tags_json, missing_json, state in prs:
        tags = _valid_tags(tags_json)
        if type(missing_json) is not str or len(missing_json) > 240:
            raise DiscoveryError("invalid public evidence omissions")
        try:
            missing = json.loads(missing_json)
        except ValueError as exc:
            raise DiscoveryError("invalid public evidence omissions") from exc
        if (source not in SOURCES or type(number) is not int or number < 1
                or skill != SOURCE_SKILL[source]
                or not isinstance(sha, str) or not SHA40.fullmatch(sha)
                or not isinstance(evidence, str) or not SHA64.fullmatch(evidence)
                or not isinstance(missing, list) or len(missing) > 4
                or any(type(m) is not str or m not in (
                    "patch", "release", "document", "advisory") for m in missing)
                or len(set(missing)) != len(missing)
                or state != "UNVERIFIED_CANDIDATE_ONLY"):
            raise DiscoveryError("unsafe staged public PR identity")
        rows.append((source, f"pr:{number}:{sha}", skill, evidence, tags))
    for sha, digest, tags_json, state in commits:
        tags = _valid_tags(tags_json)
        if (not isinstance(sha, str) or not SHA40.fullmatch(sha)
                or not isinstance(digest, str) or not SHA64.fullmatch(digest)
                or state != "UNVERIFIED_CANDIDATE_ONLY"):
            raise DiscoveryError("unsafe staged public Git commit")
        rows.append(("git/git", f"commit:{sha}", "git-workflow-prevention",
                     digest, tags))
    return sorted(rows)


def _review_path(root):
    _dedicated_path(root)
    path = Path(root) / "runtime" / REVIEW_FILE
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise DiscoveryError("unsafe dedicated candidate review database")
    return path


def _check_review_schema(conn, *, new):
    identity = conn.execute("PRAGMA application_id").fetchone()[0]
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if new:
        if identity or version:
            raise DiscoveryError("unrecognized Stage 12 review database")
        conn.execute("""CREATE TABLE review_queue (
            fingerprint TEXT PRIMARY KEY,
            source TEXT NOT NULL, reference TEXT NOT NULL,
            skill_id TEXT NOT NULL, pattern_code TEXT NOT NULL,
            safe_guidance TEXT NOT NULL, regression_plan TEXT NOT NULL,
            evidence_sha TEXT NOT NULL, first_seen_utc TEXT NOT NULL,
            review_state TEXT NOT NULL
              CHECK(review_state = 'UNVERIFIED_REVIEW_CANDIDATE_ONLY')
        ) WITHOUT ROWID""")
        conn.execute(f"PRAGMA application_id={REVIEW_APP_ID}")
        conn.execute(f"PRAGMA user_version={REVIEW_SCHEMA}")
    else:
        if identity != REVIEW_APP_ID or version != REVIEW_SCHEMA:
            raise DiscoveryError("not a UCIE Stage 12 candidate review ledger")
        objects = conn.execute(
            "SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall()
        columns = tuple(row[1] for row in conn.execute(
            "PRAGMA table_info(review_queue)").fetchall())
        if set(objects) != {("table", "review_queue")} or columns != COLUMNS:
            raise DiscoveryError("unexpected candidate review schema")
    if conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
        raise DiscoveryError("review database integrity failed")


def _review_records(rows):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    proposals = []
    for source, ref, skill, evidence, tags in rows:
        pattern = next((tag for tag in (
            "SECURITY", "CRASH", "REGRESSION", "COMPATIBILITY", "TESTING")
                        if tag in tags), "UNCLASSIFIED")
        safe = PROFILE[skill]["safe_call"]
        regression = PROFILE[skill]["recommended_action"]
        fingerprint = hashlib.sha256(
            json.dumps([source, ref, evidence], separators=(",", ":"),
                       ensure_ascii=True).encode("ascii")).hexdigest()
        proposals.append((fingerprint, source, ref, skill, pattern,
                          safe, regression, evidence, now, REVIEW_STATUS))
    return proposals


def update_unverified_review_queue(root: Path, *, allow_write=False):
    """Classify in read-only mode unless a separate owner opt-in permits writes."""
    if type(allow_write) is not bool:
        raise DiscoveryError("invalid candidate review permit")
    rows = _rows_from_stage10(root)
    entries = _review_records(rows)
    path = _review_path(root)
    if not allow_write:
        return {
            "status": "STAGE12_REVIEW_PREVIEW_ONLY",
            "source_revisions": len(rows),
            "candidate_proposals": len(entries),
            "persistent_writes": 0,
            "approved_rules": 0,
            "model_weights_updated": False,
            "production_approved": False,
        }
    exists = path.exists()
    target = path.as_uri() + ("?mode=rw" if exists else "?mode=rwc")
    try:
        with closing(sqlite3.connect(target, uri=True, timeout=3)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            _check_review_schema(conn, new=not exists)
            existing = conn.execute("SELECT count(*) FROM review_queue").fetchone()[0]
            if existing > MAX_ROWS or existing + len(entries) > MAX_ROWS * 2:
                raise DiscoveryError("bounded candidate review capacity exceeded")
            before = conn.total_changes
            conn.executemany("""
                INSERT OR IGNORE INTO review_queue VALUES
                    (?,?,?,?,?,?,?,?,?,?)
            """, entries)
            added = conn.total_changes - before
            count = conn.execute("SELECT count(*) FROM review_queue").fetchone()[0]
            conn.commit()
    except sqlite3.DatabaseError as exc:
        raise DiscoveryError("isolated candidate review database unavailable") from exc
    return {
        "status": "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO",
        "source_revisions": len(rows),
        "new_review_proposals": added,
        "unchanged_review_proposals": len(rows) - added,
        "total_review_proposals": count,
        "auto_applied_fixes": 0,
        "approved_rules": 0,
        "model_weights_updated": False,
        "production_approved": False,
    }


def optional_hourly_review_learning(root: Path):
    """Stage 12 has a distinct owner opt-in from Stage 11 API collection."""
    runtime = Path(root) / "runtime"
    marker = runtime / OPT_IN_FILENAME
    if marker.is_symlink():
        raise DiscoveryError("unsafe candidate learning opt-in")
    if not marker.exists():
        return {"status": "STAGE12_REVIEW_DISABLED",
                "production_approved": False}
    if not marker.is_file() or marker.stat().st_size > 100:
        raise DiscoveryError("invalid candidate learning opt-in")
    if marker.read_text("utf-8").strip() != OPT_IN_TOKEN:
        raise DiscoveryError("incorrect candidate learning opt-in")
    return update_unverified_review_queue(root, allow_write=True)


def inspect_review_learning(root: Path):
    path = _review_path(root)
    if not path.exists():
        return {"status": "STAGE12_REVIEW_LEDGER_ABSENT",
                "review_proposals": 0, "approved_rules": 0}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro",
                                 uri=True, timeout=3)) as conn:
        conn.execute("PRAGMA query_only=ON")
        _check_review_schema(conn, new=False)
        count = conn.execute("SELECT count(*) FROM review_queue").fetchone()[0]
        rows = conn.execute("""
            SELECT skill_id, COUNT(*) FROM review_queue GROUP BY skill_id
        """).fetchall()
        invalid = conn.execute("""
            SELECT count(*) FROM review_queue
            WHERE review_state <> 'UNVERIFIED_REVIEW_CANDIDATE_ONLY'
        """).fetchone()[0]
    if invalid or count > MAX_ROWS or any(
            skill not in PROFILE or type(n) is not int or n < 0
            for skill, n in rows):
        raise DiscoveryError("invalid unverified candidate review content")
    return {
        "status": "STAGE12_UNVERIFIED_REVIEW_INSPECTED_NO_GO",
        "review_proposals": count,
        "by_skill": dict(rows),
        "approved_rules": 0,
        "model_weights_updated": False,
        "production_approved": False,
    }
