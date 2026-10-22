"""Read-only UCIE Library search across EXISTING public metadata indexes.

No new storage, crawler, receiver identities, external-source execution,
project access, rule promotion or automatic distribution. Only indexed,
source-pinned PUBLIC_ONLY metadata is returned, never upstream text/code.
"""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import json
import re
import sqlite3

from .public_discovery import SOURCES, SOURCE_SKILL, CATEGORIES, DiscoveryError
from .public_evidence_routes import TAGS
from .public_external_history import _root_path, _schema as history_schema, MAX_STORED
from .public_candidate_staging import (
    _dedicated_path, _initialize as candidate_schema, MAX_ROWS,
)
from .skill_profiles import PROFILE

SCHEMA = "UCIE_PUBLIC_LIBRARY_SEARCH_V1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
ALL_TAGS = frozenset(CATEGORIES) | frozenset(TAGS)
MAX_RESULTS = 50


def _terms(source, skill_id, tag, limit):
    if (source is not None and
            (type(source) is not str or source not in SOURCES)
            or skill_id is not None and
            (type(skill_id) is not str or skill_id not in PROFILE)
            or tag is not None and
            (type(tag) is not str or tag not in ALL_TAGS)
            or type(limit) is not int or not 1 <= limit <= MAX_RESULTS):
        raise DiscoveryError("library query must use approved public taxonomy")
    if (source is not None and skill_id is not None
            and SOURCE_SKILL[source] != skill_id):
        raise DiscoveryError("incompatible approved source and skill")
    return (source, skill_id, tag, limit)


def _decode_tags(blob, *, taxonomy):
    try:
        tags = json.loads(blob)
    except (TypeError, ValueError) as exc:
        raise DiscoveryError("invalid indexed technical tag JSON") from exc
    if (type(tags) is not list or not tags
            or len(tags) > len(taxonomy)
            or any(type(t) is not str or t not in taxonomy for t in tags)
            or len(set(tags)) != len(tags)):
        raise DiscoveryError("untrusted indexed technical tags")
    return sorted(tags)


def _connect_readonly(path, checker):
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)
    try:
        conn.execute("PRAGMA query_only=ON")
        checker(conn)
        return conn
    except Exception:
        conn.close()
        raise


def _historical(path, *, source, skill_id, tag, cap):
    if not path.exists():
        return [], False
    with closing(_connect_readonly(path, lambda db: history_schema(db, new=False))) as conn:
        clause = ["state='UNVERIFIED_CANDIDATE_ONLY'"]
        params = []
        if source is not None:
            clause.append("source=?")
            params.append(source)
        if skill_id is not None:
            clause.append("skill_id=?")
            params.append(skill_id)
        if tag is not None:
            if tag not in CATEGORIES:
                return [], True
            clause.append("tags_json LIKE ?")
            params.append('%"' + tag + '"%')
        statement = ("SELECT source,pr_number,merge_sha,evidence_sha256,"
                     "skill_id,tags_json,merged_at FROM upstream_history WHERE "
                     + " AND ".join(clause) +
                     " ORDER BY source,pr_number DESC,evidence_sha256 LIMIT ?")
        rows = conn.execute(statement, (*params, cap)).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM upstream_history").fetchone()[0]
        bad = conn.execute("SELECT COUNT(*) FROM upstream_history "
                           "WHERE state<>'UNVERIFIED_CANDIDATE_ONLY'").fetchone()[0]
        if bad or total > MAX_STORED:
            raise DiscoveryError("invalid historical PUBLIC_ONLY library index")
    result = []
    for src, number, sha, proof, skill, tags_json, merged_at in rows:
        if (src not in SOURCES or type(number) is not int
                or not 1 <= number <= 999999999
                or skill != SOURCE_SKILL[src]
                or type(sha) is not str or not SHA40.fullmatch(sha)
                or type(proof) is not str or not SHA64.fullmatch(proof)
                or type(merged_at) is not str or not merged_at.endswith("Z")):
            raise DiscoveryError("untrusted historical public research row")
        result.append({
            "source": src, "skill_id": skill,
            "public_url": f"https://github.com/{src}/pull/{number}",
            "kind": "PUBLIC_MERGED_PR",
            "revision_sha": sha, "evidence_sha256": proof,
            "technical_tags": _decode_tags(tags_json, taxonomy=CATEGORIES),
            "record_origin": "STAGE13_PUBLIC_HISTORY",
            "public_merged_at": merged_at,
        })
    return result, True


def _recent(path, *, source, skill_id, tag, cap):
    if not path.exists():
        return [], False
    with closing(_connect_readonly(path, lambda db: candidate_schema(db, new=False))) as conn:
        clause = ["review_state='UNVERIFIED_CANDIDATE_ONLY'"]
        params = []
        if source is not None:
            clause.append("source=?")
            params.append(source)
        if skill_id is not None:
            clause.append("skill_id=?")
            params.append(skill_id)
        if tag is not None:
            if tag in TAGS:
                clause.append("tags_json LIKE ?")
                params.append('%"' + tag + '"%')
            else:
                clause.append("1=0")
        statement = ("SELECT source,pr_number,merge_sha,evidence_sha,"
                     "skill_id,tags_json FROM public_candidate_stage WHERE "
                     + " AND ".join(clause) +
                     " ORDER BY source,pr_number DESC,evidence_sha LIMIT ?")
        rows = conn.execute(statement, (*params, cap)).fetchall()
        git_rows = []
        if (tag is None or tag in CATEGORIES) and (
                source is None or source == "git/git") and (
                skill_id is None or skill_id == "git-workflow-prevention"):
            git_clause = ["review_state='UNVERIFIED_CANDIDATE_ONLY'"]
            git_params = []
            if tag is not None:
                git_clause.append("tags_json LIKE ?")
                git_params.append('%"' + tag + '"%')
            git_rows = conn.execute(
                "SELECT git_commit_sha,message_sha256,tags_json "
                "FROM public_git_commit_stage WHERE " +
                " AND ".join(git_clause) +
                " ORDER BY git_commit_sha DESC,message_sha256 LIMIT ?",
                (*git_params, cap)).fetchall()
        total = sum(conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                    for table in ("public_candidate_stage", "public_git_commit_stage"))
        if total > MAX_ROWS or any(conn.execute(
                "SELECT COUNT(*) FROM " + table +
                " WHERE review_state<>'UNVERIFIED_CANDIDATE_ONLY'").fetchone()[0]
                for table in ("public_candidate_stage", "public_git_commit_stage")):
            raise DiscoveryError("invalid recent PUBLIC_ONLY library index")
    records = []
    for src, number, sha, proof, skill, tags_json in rows:
        if (src not in SOURCES or type(number) is not int
                or not 1 <= number <= 999999999
                or skill != SOURCE_SKILL[src]
                or type(sha) is not str or not SHA40.fullmatch(sha)
                or type(proof) is not str or not SHA64.fullmatch(proof)):
            raise DiscoveryError("untrusted recent public research row")
        records.append({
            "source": src, "skill_id": skill,
            "public_url": f"https://github.com/{src}/pull/{number}",
            "kind": "PUBLIC_MERGED_PR",
            "revision_sha": sha, "evidence_sha256": proof,
            "technical_tags": _decode_tags(tags_json, taxonomy=TAGS),
            "record_origin": "STAGE10_UNVERIFIED_RESEARCH",
            "public_merged_at": None,
        })
    for sha, proof, tags_json in git_rows:
        if (type(sha) is not str or not SHA40.fullmatch(sha)
                or type(proof) is not str or not SHA64.fullmatch(proof)):
            raise DiscoveryError("untrusted public git commit research row")
        records.append({
            "source": "git/git", "skill_id": "git-workflow-prevention",
            "public_url": f"https://github.com/git/git/commit/{sha}",
            "kind": "PUBLIC_DIRECT_GIT_COMMIT",
            "revision_sha": sha, "evidence_sha256": proof,
            "technical_tags": _decode_tags(tags_json, taxonomy=CATEGORIES),
            "record_origin": "STAGE10_UNVERIFIED_RESEARCH",
            "public_merged_at": None,
        })
    return records, True


def search_public_library(root: Path, *, source=None, skill_id=None, tag=None,
                          limit=20):
    """Search existing UCIE-only public metadata; no filesystem writes.

    Bounded first page by source/PR metadata, not semantic or exhaustive
    corpus search. Stage10 evidence supersedes a same-source same-SHA
    historical PR observation in this preview; distinct revisions remain.
    """
    source, skill_id, tag, limit = _terms(source, skill_id, tag, limit)
    root = Path(root)
    runtime = root / "runtime"
    if (root.name.casefold() != "ucie" or root.is_symlink()
            or not root.is_dir() or runtime.is_symlink()
            or (runtime.exists() and not runtime.is_dir())):
        raise DiscoveryError("UCIE-only public library directory required")
    # A fresh UCIE checkout has no runtime folder. An empty query does not
    # create one, and never changes an existing checkout.
    if runtime.is_dir():
        history_path = _root_path(root)
        recent_path = _dedicated_path(root, allow_absent_runtime=False)
    else:
        history_path = runtime / "missing-stage13.sqlite3"
        recent_path = runtime / "missing-stage10.sqlite3"
    try:
        history, has_history = _historical(
            history_path, source=source, skill_id=skill_id,
            tag=tag, cap=limit)
        recent, has_recent = _recent(
            recent_path, source=source, skill_id=skill_id,
            tag=tag, cap=limit)
    except sqlite3.DatabaseError as exc:
        raise DiscoveryError("UCIE public library metadata query unavailable") from exc
    # Favor the newer independently staged metadata when the same upstream
    # PR/revision is observed by both existing index systems.
    keyed = {}
    for record in history + recent:
        key = (record["public_url"], record["revision_sha"])
        if key not in keyed or record["record_origin"] == "STAGE10_UNVERIFIED_RESEARCH":
            keyed[key] = record
    selected = sorted(keyed.values(), key=lambda row: (
        SOURCES.index(row["source"]), row["kind"],
        row["public_url"], row["revision_sha"],
    ))[:limit]
    for item in selected:
        skill = PROFILE[item["skill_id"]]
        item["domain"] = skill["domain"]
        item["first_party_review_question"] = skill["review_question"]
        item["first_party_safe_call_guidance"] = skill["safe_call"]
        item["review_plan"] = skill["recommended_action"]
        item["status"] = "UNVERIFIED_PUBLIC_RESEARCH_ONLY_NO_GO"
        item["independently_verified_fix"] = False
        item["installable_skill"] = False
    return {
        "schema": SCHEMA,
        "status": ("PUBLIC_LIBRARY_INDEX_SEARCH_PREVIEW_NO_GO"
                   if has_recent or has_history
                   else "PUBLIC_LIBRARY_INDEXES_ABSENT_NO_GO"),
        "filters": {"source": source, "skill_id": skill_id, "tag": tag},
        "result_limit": limit, "result_count": len(selected),
        "bounded_selection_not_exhaustive": True,
        "stage13_history_present": has_history,
        "stage10_recent_present": has_recent,
        "results": selected,
        "research_cannot_be_installed": True,
        "upstream_source_code_retained": False,
        "operating_database_writes": 0,
        "network_gets": 0,
        "project_reads_or_writes": 0,
        "approved_rules_added": 0,
        "production_approved": False,
    }
