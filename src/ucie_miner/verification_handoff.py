"""Read-only, evidence-bound Stage 12 candidate -> Stage 6 verification handoff.

This does NOT verify upstream behavior, run regression tests, authorize rules,
change operational databases, sign a Rulepack or approve deployment. The Stage
12 SQLite queue is UNTRUSTED and each row must be rederived from the existing
Stage 10 / opted-in Stage 15 source ledgers before it can become a task.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sqlite3

from .patterns import PatternError, group_patterns
from .public_candidate_learning import (
    COLUMNS, REVIEW_STATUS, _check_review_schema, _review_path,
    _review_records, _rows_from_stage10, _rows_from_stage15,
)
from .public_candidate_staging import MAX_ROWS
from .public_discovery import SOURCES, DiscoveryError
from .rule_candidates import GUIDANCE, candidate_rulepack

PR_REF = re.compile(r"pr:([1-9][0-9]*):([a-f0-9]{40})\Z")
REQUIRED_VERIFICATION = (
    "PINNED_PUBLIC_SOURCE_AND_LICENSE_REVIEW",
    "AFFECTED_RUNTIME_VERSION_VALIDATION",
    "INDEPENDENT_REGRESSION_AND_SECURITY_EVIDENCE",
    "EXPLICIT_OWNER_RISK_ACCEPTANCE",
    "SEPARATE_RULEPACK_RELEASE_AUTHORIZATION",
)


def _utc(value: object) -> None:
    if not isinstance(value, str):
        raise DiscoveryError("invalid review timestamp")
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise DiscoveryError("invalid review timestamp") from exc
    now = datetime.now(timezone.utc)
    if (stamp.tzinfo is None or stamp.utcoffset() != timedelta(0)
            or stamp > now + timedelta(minutes=5)):
        raise DiscoveryError("non-UTC or future review timestamp")


def _expected_record_map(root: Path) -> dict:
    # These existing readers validate source identities, DB application IDs,
    # schemas, metadata allowlists and SQLite integrity without writing.
    rows = _rows_from_stage10(root) + _rows_from_stage15(root)
    if len(rows) > MAX_ROWS:
        raise DiscoveryError("verification source capacity exceeded")
    expected = {}
    for record in _review_records(rows):
        fingerprint = record[0]
        if fingerprint in expected:
            raise DiscoveryError("duplicate source review fingerprint")
        expected[fingerprint] = record
    return expected


def prepare_verification_handoff(root: Path) -> dict:
    """Link previously staged PUBLIC_ONLY metadata to unsigned rule tasks.

    A missing queue or a queue lagging its source is NO_GO. Tampered rows and
    unknown historical/opted-out source revisions fail closed. Stage 6 templates
    are created only for exact supported PR identities; they remain unverified.
    """
    path = _review_path(root)
    if not path.exists():
        return {
            "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
            "status": "REVIEW_LEDGER_ABSENT_NO_GO",
            "source_revisions": 0, "linked_revisions": 0,
            "pending_source_revisions": 0, "template_candidates": 0,
            "tasks": [], "approved_rules": 0, "auto_promoted": False,
            "persistent_writes": 0, "production_approved": False,
            "deploy_allowed": False,
        }
    expected = _expected_record_map(Path(root))
    try:
        with closing(sqlite3.connect(
                path.as_uri() + "?mode=ro", uri=True, timeout=3)) as conn:
            conn.execute("PRAGMA query_only=ON")
            _check_review_schema(conn, new=False)
            rows = conn.execute(
                "SELECT " + ",".join(COLUMNS) +
                " FROM review_queue ORDER BY fingerprint"
            ).fetchall()
    except sqlite3.DatabaseError as exc:
        raise DiscoveryError("review handoff ledger unavailable") from exc
    if len(rows) > MAX_ROWS:
        raise DiscoveryError("verification queue capacity exceeded")
    observed = set()
    for row in rows:
        fingerprint = row[0]
        if (fingerprint in observed or fingerprint not in expected
                or len(row) != len(COLUMNS) or row[-1] != REVIEW_STATUS):
            raise DiscoveryError("unlinked or forged review candidate")
        observed.add(fingerprint)
        original = expected[fingerprint]
        # first_seen_utc is the only non-derivable field; compare everything
        # else against the validated upstream ledgers and recheck UTC time.
        _utc(row[8])
        if row[:8] != original[:8] or row[9] != original[9]:
            raise DiscoveryError("review candidate differs from source ledger")
    counts = Counter((row[1], row[2]) for row in rows)
    tasks = []
    template_count = 0
    for row in rows:
        fingerprint, source, reference, skill, pattern, safe, regression, evidence = row[:8]
        match = PR_REF.fullmatch(reference)
        # No generic tag is misrepresented as a verified failure signature.
        # Only supported Stage 6 templates with pinned PR-style identities
        # become structured proposals; all other inputs remain review tasks.
        rule = None
        if match and source in SOURCES and pattern in GUIDANCE:
            number = int(match.group(1))
            if number > 999999999:
                raise DiscoveryError("PR identity out of range")
            preview = candidate_rulepack(group_patterns([{
                "source": source,
                "pr_number": number,
                "canonical_pr_number": number,
                "pattern_code": pattern,
                "evidence_sha256": evidence,
                "status": "UNVERIFIED_CANDIDATE_ONLY",
            }]))
            rule = preview["proposals"][0]
            template_count += 1
        issues = ["VERIFICATION_NOT_PERFORMED"]
        if counts[(source, reference)] > 1:
            issues.append("MULTIPLE_EVIDENCE_REVISIONS_REQUIRE_SELECTION")
        if rule is None:
            issues.append("NO_EXACT_STAGE6_RULE_TEMPLATE")
        tasks.append({
            "candidate_id_sha256": fingerprint,
            "source": source, "reference": reference,
            "skill_id": skill, "pattern_code": pattern,
            "evidence_sha256": evidence, "evidence_is_signature": False,
            "safe_guidance_for_review": safe,
            "regression_plan_for_review": regression,
            "stage6_candidate": rule,
            "verification_requirements": list(REQUIRED_VERIFICATION),
            "blocking_reasons": issues,
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "approval": False,
        })
    missing = len(expected) - len(observed)
    if missing < 0:
        raise DiscoveryError("review source count inconsistent")
    return {
        "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
        "status": ("SOURCE_REVISIONS_PENDING_NO_GO" if missing
                   else "LINKED_UNVERIFIED_NO_GO"),
        "source_revisions": len(expected),
        "linked_revisions": len(rows),
        "pending_source_revisions": missing,
        "template_candidates": template_count,
        "tasks": tasks,
        "approved_rules": 0, "auto_promoted": False,
        "persistent_writes": 0, "production_approved": False,
        "deploy_allowed": False,
    }
