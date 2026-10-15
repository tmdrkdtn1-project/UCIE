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
    batch = batch_builder(
        root=root, sources=SOURCES, max_enrich=1,
        include_git_commits=True, include_docs=False,
        include_advisories=False, backfill_pages=1,
    )
    if (batch.get("sources_fetched") != list(SOURCES)
            or batch.get("overall_gets_upper_bound", 999) > 8
            or type(batch.get("enriched_count")) is not int
            or batch["enriched_count"] > 1
            or batch.get("production_approved") is not False):
        raise ValueError("unsafe or excessive hourly public batch")
    staged = stage_candidate_batch(
        batch, root=root, allow_disk_write=True)
    if (staged.get("status") != "UNVERIFIED_CANDIDATES_STAGED_NO_GO"
            or staged.get("mode") != "OPT_IN_SEPARATE_DISK"
            or staged.get("approved_rules_added") != 0
            or staged.get("production_approved") is not False):
        raise ValueError("invalid Stage 10 unverified-only staging result")
    from .public_candidate_learning import optional_hourly_review_learning
    learning = optional_hourly_review_learning(root)
    if learning.get("status") not in (
            "STAGE12_REVIEW_DISABLED",
            "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO"):
        raise ValueError("invalid candidate-only learning result")
    from .public_external_history import optional_external_history_backfill
    history = optional_external_history_backfill(root)
    if history.get("status") not in (
            "STAGE13_EXTERNAL_HISTORY_DISABLED",
            "EXTERNAL_HISTORY_BACKFILL_OK_NO_GO",
            "EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO",
            "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO"):
        raise ValueError("unexpected external history collection result")
    if history["status"] == "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO":
        raise ValueError("optional historical public upstream unavailable")
    return {
        "status": STATUS_STAGED,
        "operator_opted_in": True,
        "stage13_history_status": history["status"],
        "stage13_history_new_revisions": history.get(
            "new_unverified_evidence_revisions", 0),
        "stage13_history_gets": history.get("external_gets", 0),
        "stage12_review_status": learning["status"],
        "stage12_review_proposals_added": learning.get("new_review_proposals", 0),
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
