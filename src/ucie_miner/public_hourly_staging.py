"""Optional Stage 11 public skill candidate staging in EXISTING UCIE hourly cycle.

No new Windows task, no automatic activation, no Rulepack or model learning.
A human-created UCIE-only opt-in marker is required; existing legacy miner
remains unchanged with no marker. No background threads or external auth.
"""
from __future__ import annotations

from pathlib import Path

OPT_IN_FILENAME = "stage10_hourly_opt_in.txt"
OPT_IN_TOKEN = "UCIE_STAGE10_HOURLY_OPT_IN_V1"
STATUS_DISABLED = "STAGE10_HOURLY_DISABLED"
STATUS_STAGED = "STAGE10_UNVERIFIED_STAGED_NO_GO"
STATUS_PARTIAL = "STAGE10_HOURLY_PARTIAL_NO_GO"


def _phase_call(phase: str, callback, *args, **kwargs):
    """Annotate only the exception object; never persist untrusted messages."""
    try:
        return callback(*args, **kwargs)
    except Exception as exc:
        # Preserve the original class and __cause__ for the classifier.
        try:
            exc.ucie_stage10_phase = phase
        except (AttributeError, TypeError):
            pass
        raise


def _reject_phase(phase: str, message: str) -> None:
    error = ValueError(message)
    error.ucie_stage10_phase = phase
    raise error


def optional_public_skill_staging(root: Path, *, batch_builder=None,
                                  stage_candidate_batch=None) -> dict:
    """Run one bounded public five-source batch only on explicit local opt-in.

    Called from the existing worker's already-held single-instance lock after
    legacy collection succeeds. The operating miner/Knowledge DBs are never
    opened for writing by this stage.
    """
    root = Path(root)
    if root.name.casefold() != "ucie" or not root.is_dir() or root.is_symlink():
        raise ValueError("dedicated UCIE checkout required")
    runtime = root / "runtime"
    if not runtime.is_dir() or runtime.is_symlink():
        raise ValueError("safe existing UCIE runtime directory required")
    marker = runtime / OPT_IN_FILENAME
    if marker.is_symlink():
        raise ValueError("unsafe hourly opt-in file")
    if not marker.exists():
        return {
            "status": STATUS_DISABLED,
            "operator_opted_in": False,
            "scheduled_task_changed": False,
            "approved_rules_added": 0,
            "production_approved": False,
        }
    if not marker.is_file() or marker.stat().st_size > 100:
        raise ValueError("invalid hourly opt-in marker")
    if marker.read_text(encoding="utf-8").strip() != OPT_IN_TOKEN:
        raise ValueError("incorrect hourly candidate staging opt-in")
    # Import only when opted in. Existing legacy collector behaves exactly as
    # before when the marker is missing.
    from .public_discovery import SOURCES
    if batch_builder is None:
        from .public_batch import build_public_batch
        batch_builder = build_public_batch
    if stage_candidate_batch is None:
        from .public_candidate_staging import stage_public_candidates
        stage_candidate_batch = stage_public_candidates
    batch = _phase_call("STAGE10_BATCH", batch_builder,
        root=root, sources=SOURCES, max_enrich=1,
        include_git_commits=True, include_docs=False,
        include_advisories=False, backfill_pages=1,
    )
    if (batch.get("sources_fetched") != list(SOURCES)
            or batch.get("overall_gets_upper_bound", 999) > 8
            or type(batch.get("enriched_count")) is not int
            or batch["enriched_count"] > 1
            or batch.get("production_approved") is not False):
        _reject_phase("STAGE10_BATCH", "unsafe or excessive hourly public batch")
    staged = _phase_call("STAGE10_STAGING", stage_candidate_batch,
        batch, root=root, allow_disk_write=True)
    if (staged.get("status") != "UNVERIFIED_CANDIDATES_STAGED_NO_GO"
            or staged.get("mode") != "OPT_IN_SEPARATE_DISK"
            or staged.get("approved_rules_added") != 0
            or staged.get("production_approved") is not False):
        _reject_phase("STAGE10_STAGING", "invalid Stage 10 unverified-only staging result")
    from .public_external_history import optional_external_history_backfill
    history = _phase_call("STAGE13_HISTORY", optional_external_history_backfill, root)
    if history.get("status") not in (
            "STAGE13_EXTERNAL_HISTORY_DISABLED",
            "EXTERNAL_HISTORY_BACKFILL_OK_NO_GO",
            "EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO",
            "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO"):
        _reject_phase("STAGE13_HISTORY", "unexpected external history collection result")
    # Stage13 may reject one upstream page or encounter a temporary
    # public API failure. It already preserves the rejected source cursor.
    # Do not block independent Stage14/15 reads or Stage12 review learning;
    # surface a PARTIAL receipt and nonzero task result instead.
    history_failed = (
        history["status"] == "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO"
    )
    if history_failed and (
            history.get("failure_source") not in SOURCES
            or history.get("failure_category") not in (
                "FETCH_OR_RESPONSE_REJECTED", "PUBLIC_METADATA_REJECTED")):
        _reject_phase("STAGE13_HISTORY", "invalid Stage 13 failure provenance")
    from .public_official_evidence import optional_official_evidence_cycle
    official = _phase_call("STAGE14_OFFICIAL", optional_official_evidence_cycle, root)
    if official.get("status") not in (
            "STAGE14_OFFICIAL_DISABLED", "STAGE14_OFFICIAL_OBSERVED_NO_GO",
            "STAGE14_OFFICIAL_RATE_PAUSED_NO_GO",
            "STAGE14_OFFICIAL_PARTIAL_NO_GO"):
        _reject_phase("STAGE14_OFFICIAL", "invalid official public metadata status")
    from .public_fix_evidence import optional_fix_evidence_enrichment
    fix_review = _phase_call("STAGE15_FIX_EVIDENCE", optional_fix_evidence_enrichment, root)
    if fix_review.get("status") not in (
            "STAGE15_FIX_EVIDENCE_DISABLED",
            "STAGE15_STRUCTURED_FIX_EVIDENCE_STAGED_NO_GO",
            "STAGE15_PUBLIC_EVIDENCE_REJECTED_PARTIAL_NO_GO"):
        _reject_phase("STAGE15_FIX_EVIDENCE", "invalid external structured fix evidence status")
    fix_failed = (
        fix_review["status"] == "STAGE15_PUBLIC_EVIDENCE_REJECTED_PARTIAL_NO_GO"
    )
    if fix_failed and (
            fix_review.get("failure_source") not in SOURCES
            or fix_review.get("failure_category")
            != "PUBLIC_PATCH_OR_RELEASE_REJECTED"):
        _reject_phase("STAGE15_FIX_EVIDENCE", "invalid Stage15 failure provenance")
    # The next review pass reads only pre-existing, linked public candidate
    # revisions. A rejected new Stage15 receipt must not starve that pass.
    # Final stage of the *existing* hourly cycle: Stage12 now reviews both
    # Stage10 metadata and already-committed Stage15 fix hints, if and only
    # if their independent owner markers exist. Reuse the same unverified
    # append-only review ledger; never schedule a separate learner.
    from .public_candidate_learning import optional_hourly_review_learning
    learning = _phase_call("STAGE12_REVIEW", optional_hourly_review_learning, root)
    if learning.get("status") not in (
            "STAGE12_REVIEW_DISABLED",
            "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO"):
        _reject_phase("STAGE12_REVIEW", "invalid candidate-only learning result")
    # Stage16 shares this hourly invocation and its existing OS-held lock.
    # Explicit pinned-run marker required; otherwise ZERO extra public GETs.
    # If upstream API quota is already limited, defer Stage16 entirely.
    from .public_safe_qa_cycle import optional_pinned_public_qa
    safe_qa = _phase_call("STAGE16_SAFE_QA", optional_pinned_public_qa,
        root, rate_paused=(
            history["status"] == "EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO"
            or official["status"] == "STAGE14_OFFICIAL_RATE_PAUSED_NO_GO"
            or fix_failed
        ))
    if (safe_qa.get("approved_rules_added") != 0
            or safe_qa.get("production_approved") is not False
            or safe_qa.get("status") not in {
                "STAGE16_SAFE_QA_DISABLED",
                "STAGE16_SAFE_QA_RATE_PAUSED_NO_GO",
                "STAGE16_SAFE_QA_ALREADY_ATTEMPTED_NO_GO",
                "STAGE16_SAFE_QA_24H_BUDGET_PAUSED_NO_GO",
                "STAGE16_SAFE_QA_OBSERVED_REVIEW_REQUIRED",
                "STAGE16_SAFE_QA_LEDGER_INCOMPLETE_NO_GO",
                "STAGE16_SAFE_QA_FAILED_NO_GO",
            }):
        _reject_phase("STAGE16_SAFE_QA", "invalid Stage16 unverified QA outcome")
    return {
        "status": STATUS_PARTIAL if (history_failed or fix_failed) else STATUS_STAGED,
        "operator_opted_in": True,
        "stage15_fix_evidence_status": fix_review["status"],
        "stage15_failure_source": (
            fix_review.get("failure_source") if fix_failed else None),
        "stage15_failure_category": (
            fix_review.get("failure_category") if fix_failed else None),
        "stage15_fix_evidence_new_records": fix_review.get(
            "new_unverified_evidence_records", 0),
        "stage15_fix_evidence_gets_upper_bound": fix_review.get(
            "external_gets_upper_bound", 0),
        "stage14_official_status": official["status"],
        "stage14_official_new_revisions": official.get("new_metadata_revisions", 0),
        "stage14_official_gets": official.get("official_gets", 0),
        "stage13_history_status": history["status"],
        "stage13_failure_source": history.get("failure_source") if history_failed else None,
        "stage13_failure_category": history.get("failure_category") if history_failed else None,
        "stage13_history_new_revisions": history.get(
            "new_unverified_evidence_revisions", 0),
        "stage13_history_gets": history.get("external_gets", 0),
        "stage12_review_status": learning["status"],
        "stage12_review_proposals_added": learning.get("new_review_proposals", 0),
        "stage16_safe_qa_status": safe_qa["status"],
        "stage16_safe_qa_templates": safe_qa.get("safe_templates_observed", 0),
        "stage16_safe_qa_gets_upper_bound": safe_qa["public_gets_upper_bound"],
        "stage12_fix_evidence_input_revisions": learning.get(
            "stage15_unverified_fix_input_revisions", 0),
        "metadata_source_count": len(SOURCES),
        "candidate_pr_rows_added": staged["new_identities"],
        "candidate_pr_revisions_added": staged["evidence_revisions"],
        "candidate_git_rows_added": staged["git_commit_new_identities"],
        "candidate_git_revisions_added": staged["git_commit_evidence_revisions"],
        "public_gets_upper_bound": batch["overall_gets_upper_bound"],
        "scheduled_task_changed": False,
        "approved_rules_added": 0,
        "production_approved": False,
    }
