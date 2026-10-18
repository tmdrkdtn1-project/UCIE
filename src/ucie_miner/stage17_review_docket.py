"""Stage17 read-only candidate-by-candidate independent-review handoff.

Stage16 is only aggregate, UCIE-owned synthetic CI evidence. It cannot
certify any candidate revision, independent QA, security, license or owner GO.
Read only bounded UCIE runtime files and the already validated Stage12 ledgers.
Never fetch public APIs, run an upstream command, write or authorize a rule.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from .automated_candidate_qa import KNOWN, SAFE_STEPS, _checked_handoff
from .public_safe_qa_cycle import STATE, STATE_SCHEMA, _small_json, _unique
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_STAGE17_CANDIDATE_REVIEW_DOCKET_V1"
MAX_HISTORY_BYTES = 1048576
MAX_RECEIPTS = 256
MAX_LINE_BYTES = 8192
REVIEW_ACTIONS = (
    "CHECK_PINNED_UPSTREAM_SOURCE_LICENSE_AND_VERSION",
    "REPRODUCE_AFFECTED_RUNTIME_AND_FIXED_BEHAVIOR_IN_ISOLATION",
    "INDEPENDENT_QA_SECURITY_NEGATIVE_CASES_AND_REGRESSION",
    "REVIEW_EVIDENCE_REVISION_AND_REVIEWER_IDENTITY",
    "OBTAIN_SEPARATE_OWNER_RISK_AND_RELEASE_AUTHORIZATION",
)


def _utc(value: object) -> datetime:
    if type(value) is not str or len(value) > 40:
        raise ValueError("invalid UCIE UTC receipt timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid UCIE receipt date") from exc
    if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
        raise ValueError("UCIE receipt must use UTC")
    return stamp


def _no_attestation(reason: str) -> dict:
    return {"status": reason, "ci_run_id": None,
            "observed_utc": None, "synthetic_templates_observed": 0,
            "candidate_snapshot_at_ci_verified": False}


def _read_bounded_history(path: Path) -> list[dict]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("unsafe UCIE miner run history")
    with path.open("rb") as stream:
        stream.seek(0, 2)
        size = stream.tell()
        offset = max(0, size - MAX_HISTORY_BYTES)
        stream.seek(offset)
        raw = stream.read(MAX_HISTORY_BYTES + 1)
    if offset:
        # The first line may be a truncated JSONL record; exclude it.
        split = raw.find(b"\n")
        raw = raw[split + 1:] if split >= 0 else b""
    entries = raw.splitlines()[-MAX_RECEIPTS:]
    receipts = []
    for line in entries:
        if not line.strip():
            continue
        if len(line) > MAX_LINE_BYTES:
            raise ValueError("oversized UCIE run receipt")
        try:
            obj = json.loads(line.decode("utf-8"), object_pairs_hook=_unique)
        except (ValueError, UnicodeError) as exc:
            raise ValueError("untrusted UCIE run history entry") from exc
        if type(obj) is not dict:
            raise ValueError("invalid UCIE miner run record")
        receipts.append(obj)
    return receipts


def attest_stage16_aggregate(root: Path, *, now: datetime | None = None) -> dict:
    """Link durable Stage16 attempt to one exact same-cycle miner receipt.

    This links only *aggregate* synthetic CI, not candidates or human review.
    An attempt-only state or a later cached/disabled receipt is not evidence.
    """
    runtime = root / "runtime"
    if runtime.is_symlink() or not runtime.is_dir():
        raise ValueError("UCIE runtime required")
    state = runtime / STATE
    if state.is_symlink():
        raise ValueError("unsafe Stage16 state link")
    if not state.exists():
        return _no_attestation("STAGE16_ATTEMPT_ABSENT_NO_GO")
    saved = _small_json(state, max_bytes=240)
    if (set(saved) != {"schema", "run_id", "attempted_utc"}
            or saved["schema"] != STATE_SCHEMA
            or type(saved["run_id"]) is not int
            or not 1 <= saved["run_id"] <= 999999999999):
        raise ValueError("invalid Stage16 attempt identity")
    attempted = _utc(saved["attempted_utc"])
    checked_at = now or datetime.now(timezone.utc)
    if checked_at.tzinfo is None or checked_at.utcoffset() != timedelta(0):
        raise ValueError("UTC clock required")
    if attempted > checked_at + timedelta(minutes=5):
        raise ValueError("future Stage16 attempt is untrusted")
    if checked_at - attempted > timedelta(days=7):
        return _no_attestation("STAGE16_ATTESTATION_STALE_NO_GO")
    history = runtime / "run_history.jsonl"
    if history.is_symlink():
        raise ValueError("unsafe Stage16 run history link")
    if not history.exists():
        return _no_attestation("STAGE16_MATCHING_RECEIPT_ABSENT_NO_GO")
    matching = []
    for receipt in _read_bounded_history(history):
        if receipt.get("stage16_safe_qa_status") != (
                "STAGE16_SAFE_QA_OBSERVED_REVIEW_REQUIRED"):
            continue
        started, finished = _utc(receipt.get("started_utc")), _utc(
            receipt.get("finished_utc"))
        if not started <= attempted <= finished:
            continue
        count = receipt.get("stage16_safe_qa_templates")
        if (receipt.get("schema") != "UCIE_MINER_CYCLE_V1"
                or receipt.get("status") != "COLLECTED_UNVERIFIED"
                or receipt.get("stage10_status") not in (
                    "STAGE10_UNVERIFIED_STAGED_NO_GO",
                    "STAGE10_HOURLY_PARTIAL_NO_GO")
                or receipt.get("stage12_review_status") !=
                   "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO"
                or receipt.get("stage16_safe_qa_gets_upper_bound") != 9
                or type(count) is not int or not 0 <= count <= 4
                or receipt.get("verification_pass") != 0
                or receipt.get("production_approved") is not False):
            raise ValueError("inconsistent Stage16 read-only CI receipt")
        matching.append((started, count))
    if len(matching) != 1:
        return _no_attestation("STAGE16_MATCHING_RECEIPT_ABSENT_NO_GO")
    start, count = matching[0]
    return {
        "status": "STAGE16_AGGREGATE_CI_OBSERVED_NOT_INDEPENDENT_QA",
        "ci_run_id": saved["run_id"],
        "observed_utc": start.isoformat(),
        "synthetic_templates_observed": count,
        "candidate_snapshot_at_ci_verified": False,
    }


def build_review_docket(handoff: object, stage16: object) -> dict:
    """Render a deterministic, non-executable review queue. Never classify GO."""
    complete, rows = _checked_handoff(handoff)
    if (type(stage16) is not dict or stage16.get("status") not in {
            "STAGE16_AGGREGATE_CI_OBSERVED_NOT_INDEPENDENT_QA",
            "STAGE16_ATTEMPT_ABSENT_NO_GO",
            "STAGE16_ATTESTATION_STALE_NO_GO",
            "STAGE16_MATCHING_RECEIPT_ABSENT_NO_GO",
        }
            or type(stage16.get("synthetic_templates_observed")) is not int
            or not 0 <= stage16["synthetic_templates_observed"] <= 4
            or stage16.get("candidate_snapshot_at_ci_verified") is not False):
        raise ValueError("invalid Stage16 aggregate input")
    observed = stage16["status"] == (
        "STAGE16_AGGREGATE_CI_OBSERVED_NOT_INDEPENDENT_QA")
    if observed:
        if (type(stage16.get("ci_run_id")) is not int
                or not 1 <= stage16["ci_run_id"] <= 999999999999
                or not isinstance(stage16.get("observed_utc"), str)):
            raise ValueError("invalid Stage16 linked run")
        _utc(stage16["observed_utc"])
    elif (stage16.get("ci_run_id") is not None
          or stage16.get("observed_utc") is not None
          or stage16["synthetic_templates_observed"] != 0):
        raise ValueError("unsupported Stage16 attestation")
    counts = Counter(row["stage6_candidate"]["rule_code"]
                     for row in rows if row["stage6_candidate"] is not None)
    items = []
    summary = Counter()
    for row in sorted(rows, key=lambda x: x["candidate_id_sha256"]):
        preview = row["stage6_candidate"]
        code = preview["rule_code"] if preview is not None else None
        if not complete:
            lane = "INCOMPLETE_REVIEW_LEDGER_NO_GO"
        elif code is None:
            lane = "UNSUPPORTED_SAFE_RECIPE_NO_GO"
        elif counts[code] != 1 or (
                "MULTIPLE_EVIDENCE_REVISIONS_REQUIRE_SELECTION"
                in row["blocking_reasons"]):
            lane = "AMBIGUOUS_SOURCE_REVISION_NO_GO"
        elif not observed:
            lane = "STAGE16_AGGREGATE_EVIDENCE_MISSING_NO_GO"
        else:
            # Aggregate success is NOT candidate-specific. This means
            # precisely "safe pinned template identified; human QA needed".
            lane = "PINNED_TEMPLATE_INDEPENDENT_REVIEW_REQUIRED"
        summary[lane] += 1
        source = row["source"] if row["source"] in (
            "python/cpython", "PowerShell/PowerShell", "git/git",
            "modelcontextprotocol/python-sdk", "actions/runner-images") else None
        public_pr = None
        if code is not None:
            # Source/PR/merge identity already cross-checked by _checked_handoff.
            candidate_source = preview["source"]
            public_pr = ("https://github.com/" + candidate_source + "/pull/"
                         + str(preview["canonical_pr_number"]))
        items.append({
            "candidate_id_sha256": row["candidate_id_sha256"],
            "evidence_sha256": row["evidence_sha256"],
            "source": source,
            "rule_id": code,
            "pinned_public_pr": public_pr,
            "safe_synthetic_test_step": (SAFE_STEPS[code][0]
                                         if code is not None else None),
            "triage": lane,
            "independent_qa": "NOT_PERFORMED",
            "security_review": "NOT_PERFORMED",
            "license_review": "NOT_PERFORMED",
            "version_coverage": "NOT_VERIFIED",
            "reviewer_identity": "NOT_VERIFIED",
            "candidate_level_ci_binding": "NOT_ATTESTED",
            "human_approval": False,
            "deploy_allowed": False,
            "required_next_actions": list(REVIEW_ACTIONS),
        })
    body = {
        "schema": SCHEMA,
        "status": ("CANDIDATES_READY_FOR_INDEPENDENT_REVIEW_NO_APPROVAL"
                   if complete and observed else "EVIDENCE_INCOMPLETE_NO_GO"),
        "stage12_review_status": handoff["status"],
        "stage16_aggregate_status": stage16["status"],
        "stage16_ci_run_id": stage16["ci_run_id"],
        "stage16_synthetic_templates_observed":
            stage16["synthetic_templates_observed"],
        "stage16_candidate_snapshot_at_ci_verified": False,
        "candidate_count": len(items),
        "triage_counts": dict(sorted(summary.items())),
        "items": items,
        "independent_qa_pass_count": 0,
        "independent_security_pass_count": 0,
        "approved_rules_added": 0,
        "auto_promoted": False,
        "rulepack_signed": False,
        "production_approved": False,
        "persistent_writes": 0,
        "new_public_gets": 0,
        "docket_digest_is_signature": False,
    }
    body["docket_sha256"] = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return body


def inspect_stage17_review(root: Path, *, now: datetime | None = None) -> dict:
    """Direct CLI read-only operation: UCIE files only; no network or writes."""
    root = Path(root)
    if root.name.casefold() != "ucie" or root.is_symlink() or not root.is_dir():
        raise ValueError("dedicated UCIE checkout required")
    stage16 = attest_stage16_aggregate(root, now=now)
    handoff = prepare_verification_handoff(root)
    return build_review_docket(handoff, stage16)
