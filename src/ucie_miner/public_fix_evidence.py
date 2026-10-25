"""Stage 15: bounded real external fix-evidence enrichment from Stage 13 leads.

Reads one/two already-indexed approved public historical PRs, retrieves the
allowlisted PR file feature and published-release metadata endpoints, and
produces fixed-schema *unverified* error/safe-call/regression review tasks.
Never saves PR title, patch/source, release notes or remote instructions;
never executes external code or claims release inclusion, human approval,
security signoff, or model training. Requires an INDEPENDENT owner marker.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3

from .public_discovery import SOURCES, SOURCE_SKILL, DiscoveryError
from .public_evidence_routes import (
    TAGS, TRANSITION_SIGNALS, fetch_public_evidence,
)
from .public_external_history import (
    _root_path as historical_path, _schema as check_history,
)
from .public_knowledge_pipeline import (
    collect_public_knowledge_candidate, preview_public_knowledge_receipt,
)
from .skill_profiles import PROFILE

DB_NAME = "stage15_unverified_fix_evidence.sqlite3"
OPT_IN_FILE = "stage15_fix_evidence_opt_in.txt"
OPT_IN_TOKEN = "UCIE_STAGE15_FIX_EVIDENCE_OPT_IN_V1"
APP_ID = 0x55433135
SCHEMA = 1
MAX_ROWS = 20000
MAX_PER_CYCLE = 2
SHA40 = re.compile("[a-f0-9]{40}")
SHA64 = re.compile("[a-f0-9]{64}")
COVERAGE = {"BOUNDED_FIRST_PAGE_ONLY", "TRUNCATED_PAGINATION_POSSIBLE"}
EVIDENCE_STATE = "PUBLIC_PATCH_RELEASE_HINTS_UNVERIFIED"
UNVERIFIED = "UNVERIFIED_REVIEW_CANDIDATE_ONLY"
COLS = (
    "source", "pr_number", "merge_sha", "historical_sha",
    "public_evidence_sha", "skill_id", "pattern_tags_json",
    "removed_signals_json", "added_signals_json", "test_file_count",
    "patch_file_count", "patch_coverage", "published_release_count",
    "missing_evidence_json", "safe_guidance", "regression_plan",
    "affected_versions_state", "license_state", "evidence_state",
    "review_state", "first_seen_utc",
)


def _path(root):
    historical_path(root)   # Restrict to the dedicated UCIE root/runtime.
    runtime = Path(root) / "runtime"
    path = runtime / DB_NAME
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise DiscoveryError("unsafe Stage 15 evidence ledger path")
    return path


def _marker_enabled(root):
    marker = _path(root).parent / OPT_IN_FILE
    if marker.is_symlink():
        raise DiscoveryError("unsafe public evidence enrichment marker")
    if not marker.exists():
        return False
    if not marker.is_file() or marker.stat().st_size > 100:
        raise DiscoveryError("invalid public evidence enrichment marker")
    if marker.read_text("utf-8").strip() != OPT_IN_TOKEN:
        raise DiscoveryError("incorrect public evidence enrichment marker")
    return True


def _check_schema(conn, *, new):
    ident = conn.execute("PRAGMA application_id").fetchone()[0]
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if new:
        if ident or version or conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]:
            raise DiscoveryError("foreign Stage 15 evidence DB not accepted")
        conn.execute("""CREATE TABLE fix_evidence (
            source TEXT NOT NULL, pr_number INTEGER NOT NULL,
            merge_sha TEXT NOT NULL, historical_sha TEXT NOT NULL,
            public_evidence_sha TEXT NOT NULL, skill_id TEXT NOT NULL,
            pattern_tags_json TEXT NOT NULL, removed_signals_json TEXT NOT NULL,
            added_signals_json TEXT NOT NULL, test_file_count INTEGER NOT NULL,
            patch_file_count INTEGER NOT NULL, patch_coverage TEXT NOT NULL,
            published_release_count INTEGER NOT NULL,
            missing_evidence_json TEXT NOT NULL, safe_guidance TEXT NOT NULL,
            regression_plan TEXT NOT NULL,
            affected_versions_state TEXT NOT NULL
                CHECK(affected_versions_state='UNDETERMINED'),
            license_state TEXT NOT NULL CHECK(license_state='UNVERIFIED'),
            evidence_state TEXT NOT NULL
                CHECK(evidence_state='PUBLIC_PATCH_RELEASE_HINTS_UNVERIFIED'),
            review_state TEXT NOT NULL
                CHECK(review_state='UNVERIFIED_REVIEW_CANDIDATE_ONLY'),
            first_seen_utc TEXT NOT NULL,
            PRIMARY KEY(source,pr_number,historical_sha)
        ) WITHOUT ROWID""")
        conn.execute(f"PRAGMA application_id={APP_ID}")
        conn.execute(f"PRAGMA user_version={SCHEMA}")
    else:
        if ident != APP_ID or version != SCHEMA:
            raise DiscoveryError("invalid Stage 15 evidence database identity")
        objects = set(conn.execute(
            "SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall())
        columns = tuple(x[1] for x in conn.execute(
            "PRAGMA table_info(fix_evidence)").fetchall())
        if objects != {("table", "fix_evidence")} or columns != COLS:
            raise DiscoveryError("unrecognized Stage 15 evidence schema")
    if conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
        raise DiscoveryError("Stage 15 SQLite integrity failure")


def _historical_leads(root):
    path = historical_path(root)
    if not path.exists():
        raise DiscoveryError("Stage 13 historical public index not found")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro",
                                 uri=True, timeout=3)) as conn:
        conn.execute("PRAGMA query_only=ON")
        check_history(conn, new=False)
        count = conn.execute("SELECT count(*) FROM upstream_history").fetchone()[0]
        if count > 80000:
            raise DiscoveryError("oversized Stage 13 public history")
        raw = conn.execute("""
            SELECT source,pr_number,merge_sha,evidence_sha256,skill_id,state
            FROM upstream_history
            ORDER BY merged_at DESC,source,pr_number
        """).fetchall()
    leads = []
    for source, n, merge, fingerprint, skill, state in raw:
        if (source not in SOURCES or type(n) is not int or n < 1
                or type(merge) is not str or not SHA40.fullmatch(merge)
                or type(fingerprint) is not str or not SHA64.fullmatch(fingerprint)
                or skill != SOURCE_SKILL[source]
                or state != "UNVERIFIED_CANDIDATE_ONLY"):
            raise DiscoveryError("untrusted Stage 13 candidate identity")
        leads.append((source, n, merge, fingerprint))
    return leads


def _existing(root):
    path = _path(root)
    if not path.exists():
        return set()
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro",
                                     uri=True, timeout=3)) as conn:
            conn.execute("PRAGMA query_only=ON")
            _check_schema(conn, new=False)
            count = conn.execute("SELECT count(*) FROM fix_evidence").fetchone()[0]
            if count > MAX_ROWS:
                raise DiscoveryError("Stage 15 candidate capacity exceeded")
            return set(conn.execute(
                "SELECT source,pr_number,historical_sha FROM fix_evidence"
            ).fetchall())
    except sqlite3.DatabaseError as exc:
        raise DiscoveryError("Stage 15 metadata ledger unavailable") from exc


def _bounded_labels(labels, allowed):
    if (not isinstance(labels, list) or len(labels) > len(allowed)
            or len(set(map(str, labels))) != len(labels)
            or any(type(x) is not str or x not in allowed for x in labels)):
        raise DiscoveryError("invalid pinned public evidence label")
    return json.dumps(sorted(labels), separators=(",", ":"))


def _record(receipt, historical):
    source, number, merge, metadata_sha = historical
    preview_public_knowledge_receipt(receipt)
    proposal = receipt["skill_knowledge_candidate"]
    patch = receipt.get("patch_features")
    release = receipt.get("release_fingerprints")
    if (receipt.get("source") != source or receipt.get("pr_number") != number
            or proposal.get("pinned_merge_commit_sha") != merge
            or proposal.get("skill_id") != SOURCE_SKILL[source]
            or not isinstance(patch, dict)
            or patch.get("source") != source or patch.get("pr_number") != number
            or patch.get("merge_commit_sha") != merge
            or patch.get("external_code_executed") is not False
            or patch.get("code_patch_retained") is not False
            or patch.get("fix_verified") is not False
            or not isinstance(release, dict)
            or release.get("source") != source
            or release.get("release_inclusion_proven") is not False
            or receipt.get("upstream_patch_executed") is not False
            or receipt.get("version_inclusion_verified") is not False
            or receipt.get("license_approved") is not False):
        raise DiscoveryError("required public patch/release evidence unavailable")
    test_n, patch_n = patch.get("test_file_count"), patch.get("patch_file_count")
    rel_n = release.get("record_count")
    if (type(test_n) is not int or not 0 <= test_n <= 30
            or type(patch_n) is not int or not 0 <= patch_n <= 30
            or type(rel_n) is not int or not 0 <= rel_n <= 10
            or patch.get("coverage") not in COVERAGE):
        raise DiscoveryError("invalid bounded patch/release evidence counts")
    tags = _bounded_labels(patch.get("tags"), TAGS)
    removed = _bounded_labels(patch.get("removed_behavior_signals"),
                              TRANSITION_SIGNALS)
    added = _bounded_labels(patch.get("added_behavior_signals"),
                            TRANSITION_SIGNALS)
    missing = receipt.get("missing_evidence_types")
    if (not isinstance(missing, list) or len(missing) > 4
            or len(set(map(str, missing))) != len(missing)
            or any(x not in ("patch", "release", "document", "advisory")
                   for x in missing)):
        raise DiscoveryError("invalid public evidence omissions")
    fingerprint = receipt.get("candidate_evidence_sha256")
    if type(fingerprint) is not str or not SHA64.fullmatch(fingerprint):
        raise DiscoveryError("invalid public evidence fingerprint")
    skill = SOURCE_SKILL[source]
    profile = PROFILE[skill]
    return (
        source, number, merge, metadata_sha, fingerprint, skill,
        tags, removed, added, test_n, patch_n, patch["coverage"], rel_n,
        json.dumps(sorted(missing), separators=(",", ":")),
        profile["safe_call"], profile["recommended_action"],
        "UNDETERMINED", "UNVERIFIED", EVIDENCE_STATE, UNVERIFIED,
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def inspect_fix_evidence(root):
    path = _path(root)
    if not path.exists():
        return {"status": "STAGE15_FIX_EVIDENCE_ABSENT",
                "evidence_records": 0, "approved_rules": 0,
                "production_approved": False}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro",
                                 uri=True, timeout=3)) as conn:
        conn.execute("PRAGMA query_only=ON")
        _check_schema(conn, new=False)
        count = conn.execute("SELECT count(*) FROM fix_evidence").fetchone()[0]
        by_source = conn.execute(
            "SELECT source,count(*) FROM fix_evidence GROUP BY source"
        ).fetchall()
        invalid = conn.execute("""
            SELECT count(*) FROM fix_evidence
            WHERE review_state <> 'UNVERIFIED_REVIEW_CANDIDATE_ONLY'
               OR evidence_state <> 'PUBLIC_PATCH_RELEASE_HINTS_UNVERIFIED'
               OR affected_versions_state <> 'UNDETERMINED'
               OR license_state <> 'UNVERIFIED'
        """).fetchone()[0]
    if count > MAX_ROWS or invalid or any(s not in SOURCES for s, _ in by_source):
        raise DiscoveryError("invalid Stage 15 evidence approval state")
    return {
        "status": "STAGE15_UNVERIFIED_FIX_EVIDENCE_INSPECTED_NO_GO",
        "evidence_records": count,
        "by_source": dict(by_source),
        "unverified_revisions": count,
        "approved_rules": 0,
        "model_weights_updated": False,
        "production_approved": False,
    }


def optional_fix_evidence_enrichment(root, *, fetch=None, max_candidates=2):
    """Fetch at most two pinned PR file+release endpoints (four GETs total)."""
    _path(root)
    if not _marker_enabled(root):
        return {"status": "STAGE15_FIX_EVIDENCE_DISABLED",
                "approved_rules": 0, "production_approved": False}
    if type(max_candidates) is not int or not 1 <= max_candidates <= MAX_PER_CYCLE:
        raise DiscoveryError("unbounded fix evidence enrichment")
    if fetch is None:
        fetch = fetch_public_evidence
    leads = _historical_leads(root)
    prior = _existing(root)
    to_process = [lead for lead in leads
                  if (lead[0], lead[1], lead[3]) not in prior][:max_candidates]
    added = 0
    attempted = 0
    rejected_source = None
    for candidate in to_process:
        attempted += 1
        source, number, merge, _ = candidate
        receipt = collect_public_knowledge_candidate(
            source, number, merge_sha=merge, fetch=fetch,
            include_doc=False, include_advisory=False,
        )
        # Missing or rejected upstream patch/release metadata is NOT a local
        # corruption. Do not insert, advance, approve, or silently retry the
        # rejected candidate; preserve the safe failed-source provenance and
        # let the independent Stage12 review of existing records continue.
        try:
            record = _record(receipt, candidate)
        except DiscoveryError:
            rejected_source = source
            break
        path = _path(root)
        exists = path.exists()
        try:
            with closing(sqlite3.connect(
                    path.as_uri() + ("?mode=rw" if exists else "?mode=rwc"),
                    uri=True, timeout=3)) as conn:
                conn.execute("BEGIN IMMEDIATE")
                _check_schema(conn, new=not exists)
                count = conn.execute("SELECT count(*) FROM fix_evidence").fetchone()[0]
                if count + 1 > MAX_ROWS:
                    raise DiscoveryError("candidate enrichment index full")
                before = conn.total_changes
                conn.execute(
                    "INSERT OR IGNORE INTO fix_evidence VALUES ("
                    + ",".join("?" for _ in COLS) + ")", record)
                added += conn.total_changes - before
                conn.commit()
        except sqlite3.DatabaseError as exc:
            raise DiscoveryError("Stage 15 candidate evidence index failed") from exc
    return {
        "status": ("STAGE15_PUBLIC_EVIDENCE_REJECTED_PARTIAL_NO_GO"
                   if rejected_source is not None
                   else "STAGE15_STRUCTURED_FIX_EVIDENCE_STAGED_NO_GO"),
        "history_leads_available": len(leads),
        "public_prs_enriched": attempted - int(rejected_source is not None),
        "public_prs_attempted": attempted,
        "external_gets_upper_bound": attempted * 2,
        "failure_source": rejected_source,
        "failure_category": ("PUBLIC_PATCH_OR_RELEASE_REJECTED"
                             if rejected_source is not None else None),
        "new_unverified_evidence_records": added,
        "approved_rules": 0,
        "model_weights_updated": False,
        "source_code_retained": False,
        "external_code_executed": False,
        "production_approved": False,
    }
