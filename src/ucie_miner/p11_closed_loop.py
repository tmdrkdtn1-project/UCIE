"""P11 UCIE public-evidence -> first-party experience, opt-in closed loop.

This is bounded *experience-based experiment selection*, not model-weight
training or trusted third-party code ingestion. Only one anonymous GET per
5-minute collector opportunity, rotating exactly the 5 approved public GitHub
repos. Keep title HASH, merge identity and allowlisted tags, never source code,
PR title, payload text or private project data.

Public evidence is NOT a proven fix/usable skill. Local synthetic experiments
measure UCIE-authored alternatives, attach to an UNVERIFIED lead label and
feed only the next experiment/workload choice. No automatic rule approval,
signing, code deployment or production algorithm swap.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from .public_discovery import (
    SOURCES, public_feed_url, public_feed_get, discover_public_leads,
    DiscoveryError, CATEGORIES,
)
from .capability_trials import evaluate_ucie_owned_recipe
from .p11_improvement_gate import (
    classify_existing, assess_new, ImprovementGateError,
    GOOD as IMPROVEMENT_GOOD, PROPOSAL as IMPROVEMENT_PROPOSAL,
)
from . import pending_queue as queue

SCHEMA = "UCIE_P11_PUBLIC_EXPERIENCE_CLOSED_LOOP_V1"
DB_NAME = "ucie_p11_public_experience.sqlite3"
OPT_IN = "ucie_p11_closed_loop_opt_in.txt"
TOKEN = "UCIE_P11_PUBLIC_EXPERIENCE_OPT_IN_V1"
MAX_LEADS = 2400
MIN_GET_INTERVAL = timedelta(minutes=5)
# No new evidence for 30 minutes after >=10 successful GETs: cap redundant
# collection at one GET every 20 minutes; rotate approved sources unchanged.
# Any fetch failure retains the original 5-minute retry cooldown.
QUIET_AFTER = timedelta(minutes=30)
QUIET_GET_INTERVAL = timedelta(minutes=20)
QUIET_MIN_GETS = 10
RECIPES = {
    "SECURITY": "SKILL_TEST_AUTOMATION",
    "CRASH": "ENGINE_INCREMENTAL_BUILD",
    "REGRESSION": "LEARNING_FEEDBACK_LOOP",
    "COMPATIBILITY": "SKILL_TEST_AUTOMATION",
    "TESTING": "LEARNING_FEEDBACK_LOOP",
}
PRIORITIES = ("SECURITY", "CRASH", "REGRESSION", "COMPATIBILITY", "TESTING")
WORKLOADS = (128, 256, 512)


class P11Error(ValueError):
    pass


def _paths(root: Path) -> tuple[Path, Path]:
    root = Path(root)
    if (root.name.casefold() != "ucie" or root.is_symlink()
            or not root.is_dir()):
        raise P11Error("UCIE-only root required")
    runtime = root / "runtime"
    if not runtime.is_dir() or runtime.is_symlink():
        raise P11Error("UCIE runtime directory required")
    db, marker = runtime / DB_NAME, runtime / OPT_IN
    if db.is_symlink() or marker.is_symlink():
        raise P11Error("unsafe P11 file link")
    if db.exists() and not db.is_file():
        raise P11Error("unsafe P11 database")
    return db, marker


def _stamp(t: datetime) -> str:
    if not isinstance(t, datetime) or t.tzinfo is None:
        raise P11Error("timezone-aware timestamp required")
    if t.utcoffset() != timedelta(0):
        raise P11Error("UTC only")
    return t.isoformat(timespec="microseconds")


def _parse(stamp: str) -> datetime:
    if type(stamp) is not str or len(stamp) > 55:
        raise P11Error("invalid observed time")
    try:
        value = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        _stamp(value)
    except ValueError as exc:
        raise P11Error("invalid observed time") from exc
    return value


def enabled(root: Path) -> bool:
    db, marker = _paths(root)
    if not marker.exists():
        return False
    if not marker.is_file() or marker.stat().st_size > 100:
        raise P11Error("invalid P11 opt-in marker")
    if marker.read_text(encoding="utf-8").strip() != TOKEN:
        raise P11Error("invalid opt-in token")
    if not db.is_file():
        raise P11Error("P11 enabled without initialized database")
    return True


def _conn(root: Path, *, create: bool = False) -> sqlite3.Connection:
    db, _ = _paths(root)
    if not create and not enabled(root):
        raise P11Error("P11 not activated")
    conn = sqlite3.connect(str(db), isolation_level=None, timeout=0.25)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=250")
    return conn


def activate(root: Path) -> dict:
    """Idempotent explicit activation; not a scheduled task installation.

    If SQLite schema initialization fails, no opt-in marker is created.
    """
    db, marker = _paths(root)
    if marker.exists():
        if not enabled(root):
            raise P11Error("bad preexisting P11 marker")
        return status(root)
    if not queue._root(Path(root)).exists():
        raise P11Error("P10 queue must already be initialized")
    with closing(_conn(root, create=True)) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS cursor (
            slot INTEGER PRIMARY KEY CHECK(slot=1),
            source_index INTEGER NOT NULL CHECK(source_index BETWEEN 0 AND 4),
            last_attempt_at TEXT,
            last_attempt_failed INTEGER NOT NULL DEFAULT 0 CHECK(last_attempt_failed IN (0,1)),
            total_public_gets INTEGER NOT NULL CHECK(total_public_gets>=0)
        );
        INSERT OR IGNORE INTO cursor(slot,source_index,total_public_gets)
            VALUES(1,0,0);
        CREATE TABLE IF NOT EXISTS leads (
            source TEXT NOT NULL,
            pr_number INTEGER NOT NULL,
            merged_at TEXT NOT NULL,
            commit_sha TEXT,
            title_sha256 TEXT NOT NULL,
            tags TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            reviewed INTEGER NOT NULL DEFAULT 0 CHECK(reviewed IN (0,1)),
            PRIMARY KEY(source,pr_number)
        );
        CREATE TABLE IF NOT EXISTS experience (
            source TEXT NOT NULL,
            pr_number INTEGER NOT NULL,
            recipe TEXT NOT NULL,
            workload INTEGER NOT NULL,
            baseline_ops INTEGER NOT NULL,
            candidate_ops INTEGER NOT NULL,
            exact_equal INTEGER NOT NULL CHECK(exact_equal IN (0,1)),
            hypothesis_status TEXT NOT NULL CHECK(hypothesis_status IN (
                'SYNTHETIC_UNVERIFIED_PROMISING','NEEDS_REVIEW')),
            observed_at TEXT NOT NULL,
            receipt_sha256 TEXT NOT NULL,
            PRIMARY KEY(source,pr_number),
            FOREIGN KEY(source,pr_number)
                REFERENCES leads(source,pr_number)
        );
        CREATE INDEX IF NOT EXISTS leads_unreviewed
            ON leads(reviewed,observed_at,source,pr_number);
        """)
    fd, tmp = tempfile.mkstemp(prefix=".p11_optin_", suffix=".tmp",
                                dir=marker.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(TOKEN + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Existing P11 marker cannot be replaced without an explicit
        # operator choosing this mode. We checked absence above.
        if marker.exists():
            raise P11Error("concurrent opt-in marker appeared")
        os.replace(tmp, marker)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return {
        "schema": SCHEMA, "status": "P11_OPTED_IN_ISOLATED_LEDGER",
        "public_api_gets_this_call": 0,
        "scheduler_modified": False, "legacy_miner_modified": False,
        "auto_promoted": False, "model_weights_changed": False,
    }


def collect_one(root: Path, *, fetch=public_feed_get,
                now: datetime | None = None) -> dict:
    """One GET maximum, one source per 5-minute opportunity, round robin.

    A failed or malformed source does not advance the cursor; recorded attempt
    throttles repeated 429s. Any exception is surfaced to P10's per-job
    PENDING retry handler rather than blocking a different worker.
    """
    now = datetime.now(timezone.utc) if now is None else now
    time_value = _stamp(now)
    if not enabled(root):
        raise P11Error("P11 explicit opt-in required")
    # Under the P10 single-job lease there is one collector at a time;
    # the first tiny transaction reserves the last attempt, including 429.
    with closing(_conn(root)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            "SELECT source_index,last_attempt_at,last_attempt_failed,total_public_gets FROM cursor "
            "WHERE slot=1").fetchone()
        if cursor is None:
            raise P11Error("missing P11 cursor")
        previous = cursor["last_attempt_at"]
        # Source-neutral, no-new-evidence idle backoff. Reuse the existing
        # ledger/cursor only: NO schema migration, no extra API request.
        # Pending experiments and failed sources always use the base cadence.
        latest_new = conn.execute(
            "SELECT MAX(observed_at) FROM leads").fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE reviewed=0").fetchone()[0]
        quiet = (
            cursor["last_attempt_failed"] == 0
            and cursor["total_public_gets"] >= QUIET_MIN_GETS
            and pending == 0
            and (latest_new is None or now >= _parse(latest_new) + QUIET_AFTER)
        )
        interval = QUIET_GET_INTERVAL if quiet else MIN_GET_INTERVAL
        if previous and now < _parse(previous) + interval:
            conn.execute("COMMIT")
            # Never acknowledge a failed API fetch as a completed job only
            # because the retry cooldown has not elapsed. P10 keeps this
            # source job PENDING; other independent jobs still proceed.
            return {
                "schema": SCHEMA,
                "status": ("P11_FAILED_SOURCE_REMAINS_PENDING" if
                           cursor["last_attempt_failed"] else
                           "P11_RATE_WINDOW_NOT_DUE"),
                "public_api_gets_this_call": 0,
                "unverified_new_leads": 0,
                "quiet_collection_backoff": quiet,
                "interval_minutes": int(interval.total_seconds() // 60),
                "auto_promoted": False,
            }
        selected = cursor["source_index"]
        conn.execute("UPDATE cursor SET last_attempt_at=?,last_attempt_failed=1 "
                     "WHERE slot=1", (time_value,))
        conn.execute("COMMIT")
    source = SOURCES[selected]
    # Existing first-party exact allowlisted route and redirect-denying GET.
    payload = fetch(public_feed_url(source))
    extracted = discover_public_leads(payload, source=source, now=now)
    if (extracted.get("schema") != "UCIE_APPROVED_PUBLIC_DISCOVERY_V1"
            or extracted.get("source") != source
            or type(extracted.get("leads")) is not list
            or extracted.get("raw_text_retained") is not False
            or extracted.get("proposals_promoted") != 0):
        raise P11Error("original discovery contract changed")
    leads = extracted["leads"]
    for row in leads:
        if (row["source"] != source or row["status"] != "UNVERIFIED_PUBLIC_LEAD"
                or not isinstance(row["tags"], list)
                or any(tag not in CATEGORIES for tag in row["tags"])
                or len(row["title_sha256"]) != 64):
            raise P11Error("untrusted candidate outside source contract")
    added = 0
    with closing(_conn(root)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        before = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        known = {(r["source"], r["pr_number"]) for r in conn.execute(
            "SELECT source,pr_number FROM leads WHERE source=?", (source,))}
        if before + sum((source, r["pr_number"]) not in known for r in leads) > MAX_LEADS:
            raise P11Error("P11 bounded candidate ledger full")
        for lead in leads:
            try:
                result = conn.execute(
                    "INSERT OR IGNORE INTO leads"
                    "(source,pr_number,merged_at,commit_sha,title_sha256,"
                    "tags,observed_at) VALUES(?,?,?,?,?,?,?)",
                    (source, lead["pr_number"], lead["merged_at"],
                     lead["merge_commit_sha"], lead["title_sha256"],
                     json.dumps(lead["tags"], separators=(",", ":")),
                     time_value))
            except sqlite3.Error as exc:
                raise P11Error("failed first-party metadata insert") from exc
            added += result.rowcount
        # Advance only after the validated metadata and deduping have committed.
        conn.execute("UPDATE cursor SET source_index=?,last_attempt_failed=0,"
                     "total_public_gets=total_public_gets+1 WHERE slot=1",
                     ((selected + 1) % len(SOURCES),))
        conn.execute("COMMIT")
    return {
        "schema": SCHEMA, "status": "P11_PUBLIC_HASH_METADATA_STAGED_UNVERIFIED",
        "source_id": "repo:" + source,
        "public_api_gets_this_call": 1, "public_api_gets_upper_bound": 1,
        "new_unverified_leads": added,
        "titles_or_upstream_code_retained": False,
        "original_miner_modified": False, "auto_promoted": False,
    }


def learn_one(root: Path, *, now: datetime | None = None) -> dict:
    """Pick one source-bound unreviewed lead and *only* test UCIE own code.

    Experience from previous exact-equivalent experiments is reused to select
    next synthetic workload for this recipe (128->256->512). No external code
    is loaded, trained or executed. Repeatable no-work cycles do not write.
    """
    now = datetime.now(timezone.utc) if now is None else now
    moment = _stamp(now)
    if not enabled(root):
        raise P11Error("P11 explicit opt-in required")
    with closing(_conn(root)) as conn:
        rows = conn.execute(
            "SELECT source,pr_number,merged_at,commit_sha,title_sha256,tags "
            "FROM leads WHERE reviewed=0 ORDER BY observed_at,source,pr_number "
            "LIMIT 60").fetchall()
        if not rows:
            return {
                "schema": SCHEMA, "status": "P11_NO_NEW_UNVERIFIED_LEADS",
                "new_experiments": 0, "network_requests": 0,
                "auto_promoted": False,
            }
        # Reuse the actual P11 experiment history instead of counting
        # parity-only results as a successful improvement. One failed
        # recipe is held while unrelated recipes may continue.
        history = [dict(r) for r in conn.execute(
            "SELECT recipe,workload,baseline_ops,candidate_ops,"
            "exact_equal,hypothesis_status FROM experience"
        ).fetchall()]
        passed, held = classify_existing(history)
        ordered = sorted(rows, key=lambda r: (
            min((PRIORITIES.index(t) for t in json.loads(r["tags"])
                 if t in PRIORITIES), default=99),
            r["source"], r["pr_number"]))
        best = recipe = None
        for row in ordered:
            tags = json.loads(row["tags"])
            choice = next((RECIPES[t] for t in PRIORITIES if t in tags), None)
            if choice is None:
                raise P11Error("unapproved or empty validated tag")
            if choice not in held:
                best, recipe = row, choice
                break
        if best is None:
            return {
                "schema": SCHEMA,
                "status": "P11_IMPROVEMENT_REVIEW_HOLD_NO_GO",
                "held_first_party_recipes": sorted(held),
                "new_experiments": 0, "improvement_proposals_written": 0,
                "network_requests": 0, "auto_promoted": False,
                "production_algorithm_changed": False,
            }
        earlier = passed[recipe]
    rows_count = WORKLOADS[earlier % len(WORKLOADS)]
    outcome = evaluate_ucie_owned_recipe(
        recipe, rows=rows_count, queries=24, repeats=2)
    gate = assess_new(outcome, recipe=recipe, workload=rows_count)
    equal = outcome["exact_result_equivalence_observed"] is True
    improvement = gate["decision"] == IMPROVEMENT_PROPOSAL
    hyp = gate["hypothesis_status"]
    canonical = json.dumps({
        "source": best["source"], "pr_number": best["pr_number"],
        "merge_sha": best["commit_sha"], "title_sha256": best["title_sha256"],
        "recipe_id": outcome["recipe_id"], "workload_sha256": outcome["workload_sha256"],
        "exact_equal": equal, "baseline_ops": outcome["baseline_operations"],
        "candidate_ops": outcome["candidate_operations_including_setup"],
        "review_status": hyp,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = sha256(canonical.encode("ascii")).hexdigest()
    with closing(_conn(root)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT reviewed FROM leads WHERE source=? AND pr_number=?",
            (best["source"], best["pr_number"])).fetchone()
        if row is None or row["reviewed"] != 0:
            raise P11Error("lead changed during isolated experiment")
        conn.execute(
            "INSERT INTO experience(source,pr_number,recipe,workload,"
            "baseline_ops,candidate_ops,exact_equal,hypothesis_status,"
            "observed_at,receipt_sha256) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (best["source"], best["pr_number"], recipe, rows_count,
             outcome["baseline_operations"],
             outcome["candidate_operations_including_setup"], int(equal),
             hyp, moment, digest))
        # Atomic with P11 experiment + reviewed state. Existing opt-in P11
        # roots migrate lazily on the next NEW trial; 65 historical trials
        # remain historical, never backfilled as new improvement evidence.
        conn.execute("""CREATE TABLE IF NOT EXISTS improvement_review (
            source TEXT NOT NULL, pr_number INTEGER NOT NULL,
            receipt_sha256 TEXT NOT NULL,
            recipe TEXT NOT NULL, workload INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN (
                'FIRST_PARTY_RETEST_PROPOSAL_NOT_ADOPTED',
                'FIRST_PARTY_REGRESSION_HOLD_NO_GO')),
            mismatches INTEGER NOT NULL CHECK(mismatches>=0),
            operation_reduction_ppm INTEGER NOT NULL
                CHECK(operation_reduction_ppm BETWEEN 0 AND 1000000),
            observed_at TEXT NOT NULL,
            PRIMARY KEY(source,pr_number)
        )""")
        conn.execute(
            "INSERT INTO improvement_review VALUES (?,?,?,?,?,?,?,?,?)",
            (best["source"], best["pr_number"], digest,
             recipe, rows_count, gate["decision"],
             gate["mismatched_queries"],
             gate["relative_operation_reduction_ppm"], moment))
        conn.execute(
            "UPDATE leads SET reviewed=1 WHERE source=? AND pr_number=?",
            (best["source"], best["pr_number"]))
        conn.execute("COMMIT")
    return {
        "schema": SCHEMA, "status": "P11_FIRST_PARTY_EXPERIENCE_RECORDED_NO_GO",
        "source_id": "repo:" + best["source"],
        "experiment_receipt_sha256": digest,
        "recipe": recipe, "workload": rows_count,
        "exact_result_equivalence": equal,
        "synthetic_operations_reduced": improvement,
        "next_run_uses_prior_experience": True,
        "improvement_gate_decision": gate["decision"],
        "improvement_proposal_created": improvement,
        "improvement_review_records_written": 1,
        "improvement_operation_reduction_ppm":
            gate["relative_operation_reduction_ppm"],
        "production_algorithm_changed": False,
        "experience_ledger_writes": 1, "network_requests": 0,
        "original_miner_modified": False,
        "model_weights_changed": False, "auto_promoted": False,
        "approved_skill_count": 0, "v1_accepted": False,
    }


def status(root: Path) -> dict:
    """Read only; do not create P11 marker or SQLite DB."""
    db, _ = _paths(root)
    if not enabled(root):
        return {
            "schema": SCHEMA, "status": "P11_NOT_ENABLED_READ_ONLY",
            "new_experiences": 0, "api_calls_this_request": 0,
            "auto_promoted": False,
        }
    with closing(sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True,
                                 timeout=0.25)) as conn:
        cursor = conn.execute(
            "SELECT source_index,last_attempt_at,last_attempt_failed,total_public_gets FROM cursor"
        ).fetchone()
        leads = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        unchecked = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE reviewed=0").fetchone()[0]
        events = conn.execute("SELECT COUNT(*) FROM experience").fetchone()[0]
        good = conn.execute(
            "SELECT COUNT(*) FROM experience WHERE exact_equal=1").fetchone()[0]
        last_new = conn.execute(
            "SELECT MAX(observed_at) FROM leads").fetchone()[0]
        has_reviews = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
            "AND name='improvement_review'").fetchone()[0] == 1
        if has_reviews:
            review_rows = conn.execute(
                "SELECT decision,COUNT(*) FROM improvement_review "
                "GROUP BY decision").fetchall()
            review_counts = {r[0]: r[1] for r in review_rows}
        else:
            review_counts = {}
    now = datetime.now(timezone.utc)
    quiet = (
        cursor[2] == 0 and cursor[3] >= QUIET_MIN_GETS
        and unchecked == 0
        and (last_new is None or now >= _parse(last_new) + QUIET_AFTER)
    )
    interval = QUIET_GET_INTERVAL if quiet else MIN_GET_INTERVAL
    next_due = (
        _stamp(_parse(cursor[1]) + interval) if cursor[1] else None
    )
    return {
        "schema": SCHEMA,
        "status": "P11_PUBLIC_EVIDENCE_EXPERIENCE_READ_ONLY",
        "sources": len(SOURCES), "next_source_id": "repo:" + SOURCES[cursor[0]],
        "last_public_attempt_utc": cursor[1],
        "last_public_attempt_failed": bool(cursor[2]),
        "quiet_collection_backoff": quiet,
        "effective_interval_minutes": int(interval.total_seconds() // 60),
        "next_public_get_due_utc": next_due,
        "total_successful_public_gets": cursor[3],
        "unverified_leads": leads, "awaiting_synthetic_experiment": unchecked,
        "first_party_experiences": events, "synthetic_equivalence_observed": good,
        "improvement_review_record_count": sum(review_counts.values()),
        "first_party_retest_proposals_not_adopted":
            review_counts.get("FIRST_PARTY_RETEST_PROPOSAL_NOT_ADOPTED", 0),
        "first_party_regression_holds":
            review_counts.get("FIRST_PARTY_REGRESSION_HOLD_NO_GO", 0),
        "prior_experience_auto_backfilled": False,
        "production_improvements_auto_applied": 0,
        "approved_rules": 0, "approved_skills": 0,
        "network_requests": 0, "auto_promoted": False,
        "production_algorithm_changed": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="UCIE P11 source metadata + synthetic experience")
    p.add_argument("--ucie-root", required=True, type=Path)
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--status", action="store_true")
    modes.add_argument("--activate", action="store_true")
    modes.add_argument("--collect", action="store_true")
    modes.add_argument("--learn", action="store_true")
    args = p.parse_args()
    try:
        if args.status:
            result = status(args.ucie_root)
        elif args.activate:
            result = activate(args.ucie_root)
        elif args.collect:
            result = collect_one(args.ucie_root)
        else:
            result = learn_one(args.ucie_root)
    except (P11Error, ImprovementGateError, DiscoveryError,
            sqlite3.Error, OSError, ValueError) as exc:
        result = {
            "schema": SCHEMA, "status": "P11_FAIL_CLOSED",
            "error_type": type(exc).__name__, "auto_promoted": False,
            "scheduler_modified": False,
        }
    print(json.dumps(result, sort_keys=True))
    return 2 if result["status"] == "P11_FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
