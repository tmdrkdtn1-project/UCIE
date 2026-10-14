"""Stage 10: separate, append-only *unverified* public evidence candidate staging.

Default connection is in-memory: zero persistent writes. Explicitly opted-in
disk staging is confined to a dedicated UCIE-only file. It does not read or
write the operational miner/Knowledge databases, promote rules, or learn
weights. Public patches, filenames, titles and executable text are excluded.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import sqlite3

from .public_skill_digest import _map_candidate_batch
from .public_discovery import CATEGORIES
from .public_discovery import SOURCES, SOURCE_SKILL, DiscoveryError

DB_NAME = "stage10_unverified_public_candidates.sqlite3"
APPLICATION_ID = 0x55434945
SCHEMA_VERSION = 2
MAX_ROWS = 10_000
SHA40 = re.compile(r"[a-f0-9]{40}")
SHA64 = re.compile(r"[a-f0-9]{64}")
COLUMNS = (
    "source", "pr_number", "merge_sha", "evidence_sha",
    "skill_id", "tags_json", "missing_json", "first_seen_utc",
    "review_state",
)


GIT_COLUMNS = (
    "git_commit_sha", "message_sha256", "tags_json",
    "first_seen_utc", "review_state",
)


def _validated_git_items(batch):
    items = batch.get("git_commit_skill_queue", [])
    if not isinstance(items, list) or len(items) > 3:
        raise DiscoveryError("invalid Git commit queue")
    output = {}
    for item in items:
        if not isinstance(item, dict):
            raise DiscoveryError("malformed Git commit lead")
        sha, digest, tags = (item.get("git_commit_sha"),
                             item.get("message_sha256"),
                             item.get("error_category_tags"))
        if (not isinstance(sha, str) or not SHA40.fullmatch(sha)
                or not isinstance(digest, str) or not SHA64.fullmatch(digest)
                or sha in output
                or item.get("source") != "git/git"
                or item.get("public_url") !=
                    f"https://github.com/git/git/commit/{sha}"
                or item.get("skill_id") != "git-workflow-prevention"
                or item.get("knowledge_review_status") != "MANUAL_REVIEW_ONLY_NO_GO"
                or item.get("human_approval_received") is not False
                or item.get("source_commit_verified_behavior") is not False
                or item.get("released_version_inclusion_verified") is not False
                or not isinstance(tags, list) or not tags
                or len(tags) > len(CATEGORIES)
                or len(set(tags)) != len(tags)
                or any(t not in CATEGORIES for t in tags)):
            raise DiscoveryError("untrusted Git commit stage identity")
        output[sha] = item
    return output


def _utc_stamp(value):
    if value is None:
        value = datetime.now(timezone.utc)
    if (not isinstance(value, datetime) or value.tzinfo is None):
        raise DiscoveryError("UTC observation timestamp required")
    if value.utcoffset() is None:
        raise DiscoveryError("UTC observation timestamp required")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _dedicated_path(root, *, allow_absent_runtime=False):
    if not isinstance(root, (str, Path)):
        raise DiscoveryError("invalid dedicated UCIE root")
    base = Path(root)
    if (base.name.casefold() != "ucie" or base.is_symlink()
            or not base.is_dir()):
        raise DiscoveryError("dedicated UCIE project root required")
    runtime = base / "runtime"
    if runtime.is_symlink() or (runtime.exists() and not runtime.is_dir()):
        raise DiscoveryError("unsafe UCIE runtime directory")
    if not runtime.is_dir() and not allow_absent_runtime:
        raise DiscoveryError("existing non-symlink UCIE runtime dir required")
    file = runtime / DB_NAME
    if file.is_symlink() or (file.exists() and not file.is_file()):
        raise DiscoveryError("unsafe candidate staging file")
    return file


def _initialize(conn, *, new):
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=3000")
    ident = conn.execute("PRAGMA application_id").fetchone()[0]
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if new:
        if ident or version:
            raise DiscoveryError("existing sqlite file misidentified as new")
    elif ident != APPLICATION_ID or version != SCHEMA_VERSION:
        raise DiscoveryError("not a UCIE Stage 10 staging database")
    objects = conn.execute(
        "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
    ).fetchall()
    if not new:
        # Reject arbitrary externally created triggers or unrelated tables;
        # a forged staging file must not redirect inserts into other objects.
        if set(objects) != {("table", "public_candidate_stage"),
                            ("table", "public_git_commit_stage")}:
            raise DiscoveryError("unexpected existing staging schema objects")
        columns = tuple(x[1] for x in conn.execute(
            "PRAGMA table_info(public_candidate_stage)").fetchall())
        if columns != COLUMNS:
            raise DiscoveryError("unexpected staging table columns")
        git_columns = tuple(x[1] for x in conn.execute(
            "PRAGMA table_info(public_git_commit_stage)").fetchall())
        if git_columns != GIT_COLUMNS:
            raise DiscoveryError("unexpected Git commit staging columns")
    else:
        conn.execute("""
            CREATE TABLE public_candidate_stage (
              source TEXT NOT NULL,
              pr_number INTEGER NOT NULL CHECK(pr_number > 0),
              merge_sha TEXT NOT NULL,
              evidence_sha TEXT NOT NULL,
              skill_id TEXT NOT NULL,
              tags_json TEXT NOT NULL,
              missing_json TEXT NOT NULL,
              first_seen_utc TEXT NOT NULL,
              review_state TEXT NOT NULL
                  CHECK(review_state = 'UNVERIFIED_CANDIDATE_ONLY'),
              PRIMARY KEY (source, pr_number, merge_sha, evidence_sha)
            ) WITHOUT ROWID
        """)
        conn.execute("""
            CREATE TABLE public_git_commit_stage (
              git_commit_sha TEXT NOT NULL,
              message_sha256 TEXT NOT NULL,
              tags_json TEXT NOT NULL,
              first_seen_utc TEXT NOT NULL,
              review_state TEXT NOT NULL
                  CHECK(review_state = 'UNVERIFIED_CANDIDATE_ONLY'),
              PRIMARY KEY (git_commit_sha, message_sha256)
            ) WITHOUT ROWID
        """)
        conn.execute(f"PRAGMA application_id={APPLICATION_ID}")
        conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise DiscoveryError("staging sqlite integrity check failed")


def stage_public_candidates(batch, *, root=None, allow_disk_write=False,
                            observed_utc=None):
    """Append metadata-only candidates; no promotion and no implicit disk IO.

    With root=None, staging uses an isolated ephemeral in-memory database.
    Disk use requires BOTH a project root and an explicit write permit; this
    function is never invoked automatically by the public batch collector.
    """
    if type(allow_disk_write) is not bool:
        raise DiscoveryError("explicit disk write choice required")
    if root is None and allow_disk_write:
        raise DiscoveryError("disk permit without dedicated UCIE root")
    if root is not None and not allow_disk_write:
        raise DiscoveryError("disk staging requires separate explicit permit")
    entries = _map_candidate_batch(batch)  # strict structural NO-GO receipt
    git_entries = _validated_git_items(batch)
    stamp = _utc_stamp(observed_utc)
    disk_path = _dedicated_path(root) if root is not None else None
    if disk_path is not None:
        exists = disk_path.exists()
        db_target = disk_path.as_uri() + "?mode=" + ("rw" if exists else "rwc")
    else:
        exists = False
        db_target = ":memory:"
    try:
        with closing(sqlite3.connect(db_target, uri=disk_path is not None,
                                     timeout=3)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            _initialize(conn, new=not exists)
            existing = conn.execute(
                "SELECT count(*) FROM public_candidate_stage").fetchone()[0]
            existing_git = conn.execute(
                "SELECT count(*) FROM public_git_commit_stage").fetchone()[0]
            if existing + existing_git > MAX_ROWS:
                raise DiscoveryError("staging DB exceeds candidate limit")
            newly_added, unchanged, changed = 0, 0, 0
            for (source, pr), item in sorted(entries.items()):
                if source not in SOURCES or item["skill_id"] != SOURCE_SKILL[source]:
                    raise DiscoveryError("unapproved staged skill identity")
                sha, proof = item["pinned_merge_commit_sha"], item["evidence_sha256"]
                if not SHA40.fullmatch(sha) or not SHA64.fullmatch(proof):
                    raise DiscoveryError("invalid public evidence digest")
                prior = conn.execute("""
                    SELECT merge_sha, evidence_sha
                    FROM public_candidate_stage
                    WHERE source=? AND pr_number=?
                """, (source, pr)).fetchall()
                if (sha, proof) in prior:
                    unchanged += 1
                    continue
                if existing + existing_git + newly_added + changed >= MAX_ROWS:
                    raise DiscoveryError("candidate staging capacity reached")
                if prior:
                    changed += 1
                else:
                    newly_added += 1
                conn.execute("""
                    INSERT INTO public_candidate_stage
                    (source, pr_number, merge_sha, evidence_sha,
                     skill_id, tags_json, missing_json, first_seen_utc,
                     review_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    source, pr, sha, proof, item["skill_id"],
                    json.dumps(item["error_pattern_tags"], separators=(",", ":")),
                    json.dumps(item["missing_evidence_types"], separators=(",", ":")),
                    stamp, "UNVERIFIED_CANDIDATE_ONLY",
                ))
            final = conn.execute(
                "SELECT count(*) FROM public_candidate_stage").fetchone()[0]
            if final != existing + newly_added + changed:
                raise DiscoveryError("staging count mismatch")
            git_new, git_unchanged, git_changed = 0, 0, 0
            for sha, item in sorted(git_entries.items()):
                digest = item["message_sha256"]
                prior_commits = conn.execute("""
                    SELECT message_sha256 FROM public_git_commit_stage
                    WHERE git_commit_sha=?
                """, (sha,)).fetchall()
                if (digest,) in prior_commits:
                    git_unchanged += 1
                    continue
                if final + existing_git + git_new + git_changed >= MAX_ROWS:
                    raise DiscoveryError("Git commit staging capacity reached")
                if prior_commits:
                    git_changed += 1
                else:
                    git_new += 1
                conn.execute("""
                    INSERT INTO public_git_commit_stage
                    (git_commit_sha, message_sha256, tags_json,
                     first_seen_utc, review_state)
                    VALUES (?, ?, ?, ?, ?)
                """, (sha, digest,
                      json.dumps(item["error_category_tags"],
                                 separators=(",", ":")),
                      stamp, "UNVERIFIED_CANDIDATE_ONLY"))
            git_final = conn.execute(
                "SELECT count(*) FROM public_git_commit_stage").fetchone()[0]
            if git_final != existing_git + git_new + git_changed:
                raise DiscoveryError("Git commit staging count mismatch")
            conn.commit()
    except sqlite3.DatabaseError as exc:
        raise DiscoveryError("candidate-only SQLite staging failed") from exc
    return {
        "schema": "UCIE_STAGE10_PUBLIC_CANDIDATE_STAGING_V1",
        "status": "UNVERIFIED_CANDIDATES_STAGED_NO_GO",
        "mode": "OPT_IN_SEPARATE_DISK" if disk_path else "EPHEMERAL_MEMORY_ONLY",
        "input_candidate_count": len(entries),
        "new_identities": newly_added,
        "evidence_revisions": changed,
        "unchanged_candidates": unchanged,
        "total_staged_revisions": final,
        "git_commit_new_identities": git_new,
        "git_commit_evidence_revisions": git_changed,
        "git_commit_unchanged": git_unchanged,
        "git_commit_total_revisions": git_final,
        "reviewable_skill_ids": sorted({item["skill_id"] for item in entries.values()}),
        "approved_rules_added": 0,
        "reviewer_signatures_attested": 0,
        "model_weights_updated": False,
        "operating_miner_db_written": False,
        "operating_knowledge_db_written": False,
        "scheduler_changed": False,
        "source_code_retained": False,
        "production_approved": False,
    }


def inspect_staged_candidates(root):
    """Inspect only the separately named Stage 10 SQLite file with mode=ro."""
    path = _dedicated_path(root, allow_absent_runtime=True)
    if not path.exists():
        return {
            "status": "STAGING_FILE_ABSENT",
            "candidate_revisions": 0,
            "git_commit_revisions": 0,
            "review_queue_by_skill": {SOURCE_SKILL[source]: 0
                                      for source in SOURCES},
            "approved_rules": 0,
            "persistent_writes": 0,
            "production_approved": False,
        }
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro",
                                     uri=True, timeout=3)) as conn:
            conn.execute("PRAGMA query_only=ON")
            _initialize(conn, new=False)
            count = conn.execute(
                "SELECT count(*) FROM public_candidate_stage").fetchone()[0]
            git_count = conn.execute(
                "SELECT count(*) FROM public_git_commit_stage").fetchone()[0]
            git_invalid = conn.execute("""
                SELECT count(*) FROM public_git_commit_stage
                WHERE review_state <> 'UNVERIFIED_CANDIDATE_ONLY'
            """).fetchone()[0]
            invalid = conn.execute("""
                SELECT count(*) FROM public_candidate_stage
                WHERE review_state <> 'UNVERIFIED_CANDIDATE_ONLY'
            """).fetchone()[0]
            by_source = conn.execute("""
                SELECT source, skill_id, COUNT(*)
                FROM public_candidate_stage
                GROUP BY source, skill_id
            """).fetchall()
    except sqlite3.DatabaseError as exc:
        raise DiscoveryError("read-only candidate staging inspect failed") from exc
    if invalid or git_invalid or count + git_count > MAX_ROWS:
        raise DiscoveryError("invalid unverified candidate ledger state")
    skill_counts = {SOURCE_SKILL[source]: 0 for source in SOURCES}
    for source, skill_id, entries in by_source:
        if (source not in SOURCES or skill_id != SOURCE_SKILL[source]
                or type(entries) is not int or entries < 0):
            raise DiscoveryError("invalid public-only staged skill identity")
        skill_counts[skill_id] += entries
    if sum(skill_counts.values()) != count:
        raise DiscoveryError("inconsistent public skill inventory")
    return {
        "status": "UNVERIFIED_CANDIDATE_STAGING_INSPECTED_NO_GO",
        "candidate_revisions": count,
        "git_commit_revisions": git_count,
        "review_queue_by_skill": skill_counts,
        "approved_rules": 0,
        "persistent_writes": 0,
        "production_approved": False,
    }
