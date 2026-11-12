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

from ucie_public.policy import PolicyError
from .patterns import PatternError, group_patterns
from .public_candidate_learning import (
    COLUMNS, REVIEW_STATUS, _check_review_schema, _review_path,
    _review_records, _rows_from_stage10, _rows_from_stage15,
)
from .public_candidate_staging import MAX_ROWS
from .public_discovery import SOURCES, DiscoveryError
from .rule_candidates import candidate_rulepack

PR_REF = re.compile(r"pr:([1-9][0-9]*):([a-f0-9]{40})\Z")
FIX_PR_REF = re.compile(r"fix-pr:([1-9][0-9]*):([a-f0-9]{40}):([a-f0-9]{64})\Z")
# Only these four publicly pinned, already-reviewed PR identities may yield
# specific Stage 6 templates. This does not grant execution or approval.
PINNED_RULES = {
    ("python/cpython", 159014, "91248026c8a41910098032dd23f9a05ad2d9b513"):
        "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO",
    ("python/cpython", 153462, "999a046b24cff4ba0e72b574196721f66bd08237"):
        "PY_SCANDIR_SHARED_ITERATOR_RACE",
    ("PowerShell/PowerShell", 28042, "bd8cb01a7d5b86129c45eaa14ab5830a63b1283f"):
        "PS_FUZZY_GET_COMMAND_DUPLICATES",
    ("PowerShell/PowerShell", 28087, "373f6a7b7972a0a4b73bfd9737a0d768d28b347e"):
        "PS_RESOLVE_PATH_DOT_PREFIX",
}


def _pinned_rule(source: str, reference: str):
    match = PR_REF.fullmatch(reference) or FIX_PR_REF.fullmatch(reference)
    if not match or source not in SOURCES:
        return None
    number = int(match.group(1))
    if number > 999999999:
        raise DiscoveryError("PR identity out of range")
    code = PINNED_RULES.get((source, number, match.group(2)))
    return (number, code) if code is not None else None

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
        # Generic Stage 12 tags are NOT prevention-rule identities.
        # Only the exact approved source, PR and immutable merge SHA
        # can select a specific existing non-executable Stage 6 template.
        pinned = _pinned_rule(source, reference)
        rule = None
        if pinned is not None:
            number, rule_code = pinned
            preview = candidate_rulepack(group_patterns([{
                "source": source,
                "pr_number": number,
                "canonical_pr_number": number,
                "pattern_code": rule_code,
                "evidence_sha256": evidence,
                "status": "UNVERIFIED_CANDIDATE_ONLY",
            }]))
            rule = preview["proposals"][0]
            template_count += 1
        issues = ["VERIFICATION_NOT_PERFORMED"]
        if counts[(source, reference)] > 1:
            issues.append("MULTIPLE_EVIDENCE_REVISIONS_REQUIRE_SELECTION")
        if rule is None:
            issues.append("NO_EXACT_PINNED_RULE_TEMPLATE")
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


# Pure read-only candidate ledger gate, independent of optional vendor signing.
HEX64 = re.compile(r"[a-f0-9]{64}\Z")

def _checked_handoff(handoff: object) -> tuple[bool, list[dict]]:
    """Reject forged candidate approvals; no signed verifier is needed to READ."""
    from .static_rule_bridge import SOURCE_BINDINGS
    if (type(handoff) is not dict
            or handoff.get("schema") !=
               "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1"
            or handoff.get("status") not in {
                "LINKED_UNVERIFIED_NO_GO",
                "SOURCE_REVISIONS_PENDING_NO_GO",
                "REVIEW_LEDGER_ABSENT_NO_GO",
            }
            or handoff.get("auto_promoted") is not False
            or handoff.get("production_approved") is not False
            or handoff.get("deploy_allowed") is not False
            or type(handoff.get("tasks")) is not list
            or len(handoff["tasks"]) > MAX_ROWS):
        raise PolicyError("invalid public candidate review ledger")
    complete = handoff["status"] == "LINKED_UNVERIFIED_NO_GO"
    if complete:
        if (type(handoff.get("source_revisions")) is not int
                or type(handoff.get("linked_revisions")) is not int
                or handoff["source_revisions"] != handoff["linked_revisions"]
                or handoff.get("pending_source_revisions") != 0):
            raise PolicyError("inconsistent public review ledger counts")
    elif handoff.get("status") == "REVIEW_LEDGER_ABSENT_NO_GO":
        if handoff["tasks"]:
            raise PolicyError("missing ledger cannot contain trusted tasks")
    seen = set()
    for row in handoff["tasks"]:
        if (type(row) is not dict
                or row.get("status") != "UNVERIFIED_CANDIDATE_ONLY"
                or row.get("approval") is not False
                or type(row.get("blocking_reasons")) is not list
                or "VERIFICATION_NOT_PERFORMED"
                   not in row["blocking_reasons"]
                or type(row.get("candidate_id_sha256")) is not str
                or HEX64.fullmatch(row["candidate_id_sha256"]) is None
                or type(row.get("evidence_sha256")) is not str
                or HEX64.fullmatch(row["evidence_sha256"]) is None
                or row["candidate_id_sha256"] in seen):
            raise PolicyError("forged or repeated public review evidence")
        seen.add(row["candidate_id_sha256"])
        candidate = row.get("stage6_candidate")
        if candidate is None:
            continue
        if (type(candidate) is not dict
                or candidate.get("status") != "UNVERIFIED_CANDIDATE_ONLY"
                or candidate.get("executable_command") is not None
                or type(candidate.get("required_gates")) is not dict
                or not candidate["required_gates"]
                or any(flag != "NOT_VERIFIED"
                       for flag in candidate["required_gates"].values())):
            raise PolicyError("stage 6 candidate attempted privilege escalation")
        code = candidate.get("rule_code")
        if code not in SOURCE_BINDINGS:
            raise PolicyError("unrecognized candidate used an executable recipe ID")
        source, number = SOURCE_BINDINGS[code]
        reference = row.get("reference")
        found = ((PR_REF.fullmatch(reference) or FIX_PR_REF.fullmatch(reference))
                 if type(reference) is str else None)
        pinned_shas = [sha for (s, n, sha), pinned_code in PINNED_RULES.items()
                       if pinned_code == code and s == source and n == number]
        if (found is None or int(found.group(1)) != number
                or len(pinned_shas) != 1
                or found.group(2) != pinned_shas[0]
                or row.get("source") != source
                or candidate.get("source") != source
                or candidate.get("canonical_pr_number") != number
                or PINNED_RULES.get((source, number, found.group(2))) != code):
            raise PolicyError("public candidate not bound to exact known source")
    return complete, handoff["tasks"]
