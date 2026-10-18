"""One-shot, explicit opt-in Stage16 public CI QA in the existing miner lock.

Only a manually pinned UCIE main CI ID can be queried. At most one attempt
per run ID and one attempt per 24 hours; at most nine public GitHub GETs per
attempt using the existing four UCIE-authored safe recipes. No external
commands, private files, Rulepack signing, approval, new task, or deployment.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile

OPT_IN = "stage16_safe_qa_opt_in.json"
STATE = "stage16_safe_qa_attempt.json"
OPT_IN_SCHEMA = "UCIE_STAGE16_SAFE_QA_OPT_IN_V1"
STATE_SCHEMA = "UCIE_STAGE16_SAFE_QA_ATTEMPT_V1"

DISABLED = "STAGE16_SAFE_QA_DISABLED"
PAUSED = "STAGE16_SAFE_QA_RATE_PAUSED_NO_GO"
ALREADY = "STAGE16_SAFE_QA_ALREADY_ATTEMPTED_NO_GO"
COOLDOWN = "STAGE16_SAFE_QA_24H_BUDGET_PAUSED_NO_GO"
REVIEW = "STAGE16_SAFE_QA_OBSERVED_REVIEW_REQUIRED"
PENDING = "STAGE16_SAFE_QA_LEDGER_INCOMPLETE_NO_GO"
FAILED = "STAGE16_SAFE_QA_FAILED_NO_GO"


def _unique(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ValueError("duplicate Stage16 local control key")
        fields[key] = value
    return fields


def _small_json(path: Path, *, max_bytes: int) -> dict:
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_size > max_bytes):
        raise ValueError("unsafe Stage16 local control path")
    value = json.loads(path.read_text(encoding="utf-8"),
                       object_pairs_hook=_unique)
    if type(value) is not dict:
        raise ValueError("invalid Stage16 local control")
    return value


def _remember_attempt(path: Path, payload: dict) -> None:
    """Persist consumption BEFORE any network GET; crash fails closed."""
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    if not path.exists():
        with path.open("x", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return
    fd, tmp = tempfile.mkstemp(prefix=".ucie_stage16_", suffix=".tmp",
                                dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink():
            raise ValueError("unsafe Stage16 attempt state")
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def optional_pinned_public_qa(root: Path, *, verifier=None,
                              rate_paused: bool = False,
                              now: datetime | None = None) -> dict:
    """Run bounded safe-template public evidence QA, never approve candidates.

    Called inside run_cycle's existing OS-held lock AFTER Stage12 has staged
    unsigned review candidates. Missing marker is zero-read/no-write opt out.
    """
    root = Path(root)
    if root.name.casefold() != "ucie" or root.is_symlink() or not root.is_dir():
        raise ValueError("dedicated UCIE root required")
    runtime = root / "runtime"
    if runtime.is_symlink() or not runtime.is_dir():
        raise ValueError("unsafe UCIE runtime directory")
    marker = runtime / OPT_IN
    if marker.is_symlink():
        raise ValueError("unsafe Stage16 opt-in link")
    if not marker.exists():
        return {"status": DISABLED, "public_gets_upper_bound": 0,
                "approved_rules_added": 0, "production_approved": False}
    cfg = _small_json(marker, max_bytes=160)
    if (set(cfg) != {"schema", "run_id"}
            or cfg["schema"] != OPT_IN_SCHEMA
            or type(cfg["run_id"]) is not int
            or not 1 <= cfg["run_id"] <= 999999999999):
        raise ValueError("invalid pinned Stage16 opt-in")
    run_id = cfg["run_id"]
    stamp = now or datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
        raise ValueError("UTC-aware Stage16 clock required")
    state = runtime / STATE
    if state.is_symlink():
        raise ValueError("unsafe Stage16 attempt link")
    if state.exists():
        previous = _small_json(state, max_bytes=240)
        if (set(previous) != {"schema", "run_id", "attempted_utc"}
                or previous["schema"] != STATE_SCHEMA
                or type(previous["run_id"]) is not int
                or not 1 <= previous["run_id"] <= 999999999999
                or type(previous["attempted_utc"]) is not str):
            raise ValueError("invalid Stage16 prior attempt")
        try:
            prior = datetime.fromisoformat(previous["attempted_utc"])
        except ValueError as exc:
            raise ValueError("invalid Stage16 prior attempt time") from exc
        if (prior.tzinfo is None or prior.utcoffset() != timedelta(0)
                or prior > stamp + timedelta(minutes=5)):
            raise ValueError("invalid Stage16 prior time ordering")
        if previous["run_id"] == run_id:
            return {"status": ALREADY, "public_gets_upper_bound": 0,
                    "approved_rules_added": 0, "production_approved": False}
        if stamp - prior < timedelta(hours=24):
            return {"status": COOLDOWN, "public_gets_upper_bound": 0,
                    "approved_rules_added": 0, "production_approved": False}
    if rate_paused:
        return {"status": PAUSED, "public_gets_upper_bound": 0,
                "approved_rules_added": 0, "production_approved": False}
    _remember_attempt(state, {
        "schema": STATE_SCHEMA, "run_id": run_id,
        "attempted_utc": stamp.isoformat(timespec="seconds"),
    })
    # The existing verifier constructs only exact UCIE public GitHub URLs.
    # It performs no upstream patch downloads or program execution.
    if verifier is None:
        from .automated_candidate_qa import verify_public_candidate_qa
        verifier = verify_public_candidate_qa
    try:
        result = verifier(root, run_id=run_id)
        if (type(result) is not dict
                or result.get("schema") != "UCIE_PUBLIC_SAFE_CANDIDATE_QA_V1"
                or result.get("status") not in {
                    "SAFE_TEMPLATE_QA_REVIEW_READY_NO_NEW_APPROVAL",
                    "CANDIDATE_LEDGER_INCOMPLETE_NO_GO",
                }
                or type(result.get("safe_templates_observed")) is not int
                or not 0 <= result["safe_templates_observed"] <= 4
                or result.get("new_rules_approved") != 0
                or result.get("auto_promoted") is not False
                or result.get("owner_signed") is not False
                or result.get("production_approved") is not False
                or result.get("unsafe_external_code_executed") is not False
                or result.get("persistent_writes") != 0):
            raise ValueError("invalid Stage16 safe public QA verdict")
        status = (REVIEW if result["status"] ==
                  "SAFE_TEMPLATE_QA_REVIEW_READY_NO_NEW_APPROVAL" else PENDING)
        return {"status": status, "public_gets_upper_bound": 9,
                "safe_templates_observed": result["safe_templates_observed"],
                "approved_rules_added": 0, "production_approved": False}
    except Exception as exc:
        # The attempt is spent even after network failure. Do not expose
        # public/untrusted text and do not retry in the next hourly cycle.
        return {"status": FAILED, "error_type": type(exc).__name__,
                "public_gets_upper_bound": 9,
                "approved_rules_added": 0, "production_approved": False}
