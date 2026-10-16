"""Stage 16: no-network read-only audit of Stage 13 -> Stage 15 evidence identity.

Only previously stored PUBLIC_ONLY, unverified UCIE metadata is inspected.
A matching local digest is not an independent upstream attestation, a
verified fix, a license decision, or permission to promote a rule.
"""
from __future__ import annotations

from contextlib import closing
import json
import re
import sqlite3

from .public_discovery import SOURCES, SOURCE_SKILL, DiscoveryError
from .public_external_history import (
    _root_path as history_path, _schema as history_schema, MAX_STORED,
)
from .public_fix_evidence import (
    _path as fix_path, _check_schema as fix_schema, MAX_ROWS, COVERAGE,
    EVIDENCE_STATE, UNVERIFIED,
)
from .public_evidence_routes import TAGS, TRANSITION_SIGNALS
from .skill_profiles import PROFILE

_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_MISSING = {"patch", "release", "document", "advisory"}


def _digest(value, pattern):
    return type(value) is str and pattern.fullmatch(value) is not None


def _labels(raw, allow):
    """No untrusted label text is ever returned or logged."""
    if type(raw) is not str or len(raw) > 512:
        return False
    try:
        labels = json.loads(raw)
    except (ValueError, TypeError):
        return False
    return (type(labels) is list and len(labels) <= len(allow)
            and all(type(item) is str and item in allow for item in labels)
            and labels == sorted(set(labels)))


def _history(root):
    path = history_path(root)
    if not path.exists():
        return None
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro",
                                     uri=True, timeout=3)) as db:
            db.execute("PRAGMA query_only=ON")
            history_schema(db, new=False)
            rows = db.execute("""
                SELECT source,pr_number,merge_sha,evidence_sha256,skill_id,state
                FROM upstream_history
            """).fetchall()
    except sqlite3.DatabaseError as exc:
        raise DiscoveryError("Stage 13 history read-only audit unavailable") from exc
    if len(rows) > MAX_STORED:
        raise DiscoveryError("Stage 13 history is oversized")
    indexed = {}
    for source, number, merge, sha, skill, state in rows:
        if (source not in SOURCES or type(number) is not int
                or not 1 <= number <= 999999999
                or not _digest(merge, _HEX40) or not _digest(sha, _HEX64)
                or skill != SOURCE_SKILL[source]
                or state != "UNVERIFIED_CANDIDATE_ONLY"):
            raise DiscoveryError("invalid Stage 13 evidence identity")
        key = source, number, sha
        if key in indexed:
            raise DiscoveryError("duplicate historical revision")
        indexed[key] = merge, skill
    return indexed


def _fix(root):
    path = fix_path(root)
    if not path.exists():
        return None
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro",
                                     uri=True, timeout=3)) as db:
            db.execute("PRAGMA query_only=ON")
            fix_schema(db, new=False)
            rows = db.execute("""
                SELECT source,pr_number,merge_sha,historical_sha,
                       public_evidence_sha,skill_id,pattern_tags_json,
                       removed_signals_json,added_signals_json,test_file_count,
                       patch_file_count,patch_coverage,published_release_count,
                       missing_evidence_json,safe_guidance,regression_plan,
                       affected_versions_state,license_state,evidence_state,
                       review_state FROM fix_evidence
            """).fetchall()
    except sqlite3.DatabaseError as exc:
        raise DiscoveryError("Stage 15 evidence read-only audit unavailable") from exc
    if len(rows) > MAX_ROWS:
        raise DiscoveryError("Stage 15 evidence is oversized")
    return rows


def _valid_fix(row):
    (source, number, merge, history_sha, evidence_sha, skill,
     tags, removed, added, tests, patches, coverage, releases, missing,
     safe_call, regression, versions, license_state, evidence_state,
     review_state) = row
    if source not in SOURCES:
        return False
    profile = PROFILE[SOURCE_SKILL[source]]
    return (
        type(number) is int and 1 <= number <= 999999999
        and _digest(merge, _HEX40)
        and _digest(history_sha, _HEX64)
        and _digest(evidence_sha, _HEX64)
        and skill == SOURCE_SKILL[source]
        and _labels(tags, TAGS)
        and _labels(removed, TRANSITION_SIGNALS)
        and _labels(added, TRANSITION_SIGNALS)
        and _labels(missing, _MISSING)
        and type(tests) is int and 0 <= tests <= 30
        and type(patches) is int and 0 <= patches <= 30
        and type(releases) is int and 0 <= releases <= 10
        and coverage in COVERAGE
        and safe_call == profile["safe_call"]
        and regression == profile["recommended_action"]
        and versions == "UNDETERMINED"
        and license_state == "UNVERIFIED"
        and evidence_state == EVIDENCE_STATE
        and review_state == UNVERIFIED
    )


def audit_external_evidence_chain(root):
    """Cross-check exact Stage 13 fingerprints; do not query any remote API.

    An index match can only establish internal provenance consistency. Stage
    15 captured at most 30 files, did not attest the upstream merge a second
    time and never proved a published-release inclusion or a regression.
    """
    history = _history(root)
    fixes = _fix(root)
    missing = [
        stage for stage, rows in (("stage13", history), ("stage15", fixes))
        if rows is None
    ]
    counts = {"linked": 0, "orphaned": 0, "merge_mismatch": 0,
              "invalid_review_rows": 0}
    by_source = {}
    for row in fixes or ():
        if not _valid_fix(row):
            counts["invalid_review_rows"] += 1
            continue
        source, number, merge, historical_sha = row[:4]
        parent = (history or {}).get((source, number, historical_sha))
        if parent is None:
            counts["orphaned"] += 1
        elif parent != (merge, SOURCE_SKILL[source]):
            counts["merge_mismatch"] += 1
        else:
            counts["linked"] += 1
            by_source[source] = by_source.get(source, 0) + 1

    mismatched = any(counts[k] for k in (
        "orphaned", "merge_mismatch", "invalid_review_rows"))
    status = ("STAGE16_INCOMPLETE_LOCAL_EVIDENCE_NO_GO" if missing
              else "STAGE16_LOCAL_EVIDENCE_MISMATCH_NO_GO" if mismatched
              else "STAGE16_LOCALLY_LINKED_BUT_UNVERIFIED_NO_GO")
    return {
        "status": status,
        "missing_ledgers": missing,
        "stage13_unverified_revisions": len(history or ()),
        "stage15_unverified_revisions": len(fixes or ()),
        "local_identity_links": counts["linked"],
        "orphaned_revision_refs": counts["orphaned"],
        "merge_sha_mismatches": counts["merge_mismatch"],
        "invalid_review_rows": counts["invalid_review_rows"],
        "linked_by_approved_source": {source: by_source[source]
                                      for source in SOURCES if source in by_source},
        "external_gets": 0, "persistent_writes": 0,
        "upstream_merge_independently_attested": False,
        "pr_file_pagination_complete": False,
        "official_release_inclusion_proven": False,
        "independent_regression_verified": False,
        "license_approved": False, "approved_rules": 0,
        "model_weights_updated": False, "production_approved": False,
    }
