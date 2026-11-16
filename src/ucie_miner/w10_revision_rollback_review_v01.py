"""UCIE W10: source-pinned first-party revision/rollback readiness, READ-ONLY.

Reuses the already source-linked P9 revision proposal queue and the genuine
first-party W09/W07/W08 QA. Never edits, restores or executes a candidate,
creates a backup, grants release rights, touches the scheduler, does a GET,
or upgrades a signed owner-risk manual rule into a customer product.

A SHA of present bytes is NOT a preserved pre-upgrade restore artifact.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from .capability_trials import RECIPES
from .product_v1 import SCHEMA as P9_SCHEMA, integrated_product_preview
from .w09_consumer_acceptance_v01 import (
    SCHEMA as W09_SCHEMA, NO_SIGNED, inspect_w09_consumer_acceptance,
)

SCHEMA = "UCIE_W10_PINNED_REVISION_ROLLBACK_REVIEW_V01"
QUEUE_SCHEMA = "UCIE_P8_LIBRARY_REVISION_REVIEW_QUEUE_V1"
STATUS_SELECTED = "W10_EXACT_REVISION_REQUIRES_MANUAL_REVIEW_NO_GO"
STATUS_EMPTY = "W10_NO_IN_SCOPE_PENDING_REVISION_NO_GO"
STATUS_PENDING = "W10_UNAPPROVED_REVISION_WINDOW_REVIEW_NO_GO"
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
TARGET_INDEX = "ucie_miner.library_exact_index:EXACT_QUERY_POLICY"
TARGET_RECIPE = "ucie_miner.capability_trials:"
MAX_SOURCE_BYTES = 100_000
MAX_PAGE = 20
BLOCKERS = (
    "PROPOSED_SOURCE_BYTES_AND_EXACT_GIT_COMMIT_NOT_PINNED",
    "REVIEWED_PRECHANGE_RESTORABLE_BYTES_NOT_ARCHIVED",
    "CANDIDATE_BEHAVIOR_AND_NEGATIVE_SECURITY_RETEST_NOT_EXECUTED",
    "INDEPENDENT_HUMAN_QA_AND_LICENSE_RIGHTS_NOT_APPROVED",
    "EXPLICIT_OWNER_DEPLOY_AND_ROLLBACK_APPROVAL_NOT_GRANTED",
    "POST_RESTORE_CONSUMER_REVERIFICATION_NOT_ATTESTED",
)


class W10ReviewError(ValueError):
    """Source, lineage, QA or safe rollback prerequisite not satisfied."""


def _json_hash(obj: dict) -> str:
    return sha256(json.dumps(
        obj, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()


def _target_source(target: str) -> tuple[str, str]:
    if type(target) is not str:
        raise W10ReviewError("unexpected target type")
    if target == TARGET_INDEX:
        return "library_exact_index.py", "INDEX_EXACT_QUERY_POLICY"
    if target.startswith(TARGET_RECIPE):
        recipe_id = target.removeprefix(TARGET_RECIPE)
        allowed_ids = {value[1] for value in RECIPES.values()}
        if recipe_id in allowed_ids:
            return "capability_trials.py", "UCIE_OWNED_FIRST_PARTY_RECIPE"
    raise W10ReviewError("only original UCIE-owned review targets allowed")


def _source_sha(target: str) -> dict:
    file_name, scope = _target_source(target)
    folder = Path(__file__).resolve().parent
    source = folder / file_name
    if (folder.is_symlink() or source.is_symlink()
            or not source.is_file() or source.parent != folder):
        raise W10ReviewError("untrusted first-party source file")
    data = source.read_bytes()
    if not 0 < len(data) <= MAX_SOURCE_BYTES:
        raise W10ReviewError("bounded first-party source bytes required")
    return {
        "target": target, "source_file": file_name,
        "source_scope": scope,
        "current_checked_out_source_sha256": sha256(data).hexdigest(),
        "current_source_bytes_observed": len(data),
        "source_snapshot_copied_or_restored": False,
        "pre_update_restore_artifact_independently_verified": False,
        "candidate_implementation_read_or_executed": False,
    }


def _checked_revision_queue(product: dict, limit: int) -> tuple[dict, list[dict]]:
    if (type(product) is not dict
            or product.get("schema") != P9_SCHEMA
            or product.get("status") != "P9_INTEGRATED_READ_ONLY_PRODUCT_PREVIEW_NO_GO"
            or product.get("network_requests") != 0
            or product.get("operating_database_writes") != 0
            or product.get("new_signatures_created") != 0
            or product.get("candidate_auto_promoted") is not False
            or product.get("package_released") is not False
            or product.get("v1_accepted") is not False):
        raise W10ReviewError("P9 product read-only lineage changed")
    queue = product.get("library_revision_review_queue")
    if (type(queue) is not dict
            or queue.get("schema") != QUEUE_SCHEMA
            or queue.get("status") !=
                "UNAPPROVED_REPRODUCIBLE_REVIEW_CANDIDATES_ONLY"
            or queue.get("source") !=
                "ORIGINAL_UCIE_VERIFIED_EXPERIENCE_READERS"
            or type(queue.get("items")) is not list
            or type(queue.get("returned_count")) is not int
            or queue["returned_count"] != len(queue["items"])
            or queue["returned_count"] > limit
            or type(queue.get("candidate_count_in_loaded_window")) is not int
            or queue["candidate_count_in_loaded_window"] < queue["returned_count"]
            or type(queue.get("omitted_from_loaded_window")) is not int
            or queue["omitted_from_loaded_window"] !=
                queue["candidate_count_in_loaded_window"]-queue["returned_count"]
            or queue.get("new_revision_persisted") is not False
            or queue.get("reviewer_approved") is not False
            or queue.get("learning_model_changed") is not False
            or queue.get("network_requests") != 0
            or queue.get("operating_database_writes") != 0
            or queue.get("auto_promoted") is not False
            or queue.get("v1_accepted") is not False):
        raise W10ReviewError("existing review queue contract drift")
    entries=[]
    seen=set()
    for row in queue["items"]:
        if type(row) is not dict:
            raise W10ReviewError("invalid review proposal shape")
        target=row.get("target_ucie_component")
        source=row.get("source_library_item_id")
        proposal=row.get("proposal_id")
        state=row.get("review_state")
        action=row.get("review_action")
        decision=row.get("original_experiment_decision")
        shelf=row.get("source_shelf")
        if (type(proposal) is not str or SHA64.fullmatch(proposal) is None
                or type(source) is not str or SHA64.fullmatch(source) is None
                or proposal in seen
                or type(target) is not str
                or type(decision) is not str
                or type(action) is not str
                or type(state) is not str
                or shelf not in (
                    "UCIE_SYNTHETIC_EXPERIENCE",
                    "UCIE_CANDIDATE_TRIAL_EXPERIENCE")
                or row.get("evidence_scope") != "UCIE_FIRST_PARTY_SYNTHETIC_ONLY"
                or row.get("independent_quality_assurance") is not False
                or row.get("production_improvement_verified") is not False
                or row.get("source_code_changed") is not False
                or row.get("library_revision_written") is not False
                or row.get("auto_promoted") is not False
                or row.get("export_allowed") is not False):
            raise W10ReviewError("unverified revision treated as accepted")
        if shelf == "UCIE_SYNTHETIC_EXPERIENCE":
            if (target != TARGET_INDEX
                    or decision not in (
                        "SYNTHETIC_CANDIDATE_WORTH_MORE_TESTING",
                        "REJECT_OR_REVISE_SYNTHETIC_CANDIDATE")
                    or row.get("public_candidate_identity_only") is not None):
                raise W10ReviewError("invalid original P8 index revision")
            hold = decision == "REJECT_OR_REVISE_SYNTHETIC_CANDIDATE"
            expected_action = ("HOLD_INDEX_POLICY_FOR_CORRECTION" if hold
                               else "RETEST_INDEX_POLICY_ON_DIVERSE_UCIE_WORKLOADS")
        else:
            _, scope=_target_source(target)
            if (scope != "UCIE_OWNED_FIRST_PARTY_RECIPE"
                    or decision not in (
                        "RETEST_FIRST_PARTY_RECIPE",
                        "HOLD_FOR_FIRST_PARTY_RECIPE_CORRECTION")
                    or type(row.get("public_candidate_identity_only")) is not dict
                    or row["public_candidate_identity_only"].get(
                        "upstream_code_executed") is not False):
                raise W10ReviewError("invalid original W05 recipe revision")
            hold = decision == "HOLD_FOR_FIRST_PARTY_RECIPE_CORRECTION"
            expected_action = ("HOLD_UCIE_OWNED_RECIPE_FOR_CORRECTION" if hold
                               else "RETEST_UCIE_OWNED_RECIPE_WITH_INDEPENDENT_WORKLOAD")
        expected_state = ("HOLD_FOR_MANUAL_REVIEW_NOT_APPLIED" if hold
                          else "MORE_UCIE_TESTING_REQUIRED_NOT_APPLIED")
        # Recompute the original first-party list hash, not a wrapper
        # object, to prevent source-experiment proposal substitution.
        original_hash=sha256(json.dumps(
            ["UCIE_P8_LIBRARY_REVISION_REVIEW_V1",source,target,decision],
            separators=(",",":"),ensure_ascii=True).encode("ascii")).hexdigest()
        if (proposal != original_hash or state != expected_state
                or action != expected_action):
            raise W10ReviewError("review proposal hash/state/action mismatch")
        seen.add(proposal)
        pin = _source_sha(target)
        entries.append({
            "proposal_id": proposal,
            "source_experiment_id": source,
            "source_shelf": shelf,
            "target_ucie_component": target,
            "old_code_source_pin": pin,
            "status": expected_state,
            "review_action": action,
            "reported_change_currently_applied": False,
            "candidate_code_and_sha_pinned": False,
            "candidate_regression_evaluated": False,
            "independent_human_qa_approved": False,
            "owner_deploy_approved": False,
            "reversible_bytes_or_snapshot_attested": False,
            "rollback_executed": False,
        })
    return queue, entries


def review_w10_revision_and_rollback(
        root: Path, *, limit: int=10,
        select_proposal_id: str | None=None,
        expected_w09_review_digest: str | None=None,
        queries: int=32, repeats: int=3) -> dict:
    if (type(limit) is not int or not 1<=limit<=MAX_PAGE
            or select_proposal_id is not None and (
                type(select_proposal_id) is not str
                or SHA64.fullmatch(select_proposal_id) is None)
            or expected_w09_review_digest is not None and (
                type(expected_w09_review_digest) is not str
                or SHA64.fullmatch(expected_w09_review_digest) is None)
            or type(queries) is not int or not 8<=queries<=96
            or type(repeats) is not int or not 1<=repeats<=5):
        raise W10ReviewError("strict bounded W10 review only")
    # W09 enforces the EXACT D:/UCIE owner checkout or isolated marked
    # TEMP/UCIE test root, original consumer source and no network.
    w09=inspect_w09_consumer_acceptance(root,queries=queries,repeats=repeats)
    if (w09.get("schema")!=W09_SCHEMA
            or w09.get("status")!=NO_SIGNED
            or w09.get("owner_signed_original_supplied") is not False
            or w09.get("signed_rule_manual_consumer") is not None
            or w09.get("manual_selection_present") is not False
            or w09.get("portable_first_party_draft_independent_QA",{}).get(
                "standalone_zip_without_ucie_install_executed") is not True
            or w09.get("w08_heldout_query_count")!=9
            or w09.get("w08_heldout_mismatched_results")!=0
            or w09.get("customer_release_authorized") is not False
            or w09.get("independent_human_qa_approved") is not False
            or w09.get("network_requests")!=0
            or w09.get("operating_database_writes")!=0
            or w09.get("auto_promoted") is not False
            or w09.get("new_package_created_or_exported") is not False
            or w09.get("review_digest_is_release_authorization") is not False
            or type(w09.get("review_digest_sha256")) is not str
            or SHA64.fullmatch(w09["review_digest_sha256"]) is None):
        raise W10ReviewError("W09 true source and nonrelease scope changed")
    if (expected_w09_review_digest is not None and
            expected_w09_review_digest != w09["review_digest_sha256"]):
        raise W10ReviewError("W09 review digest changed since owner observation")
    product=integrated_product_preview(
        root,query="",limit=limit,include_demo=False)
    queue, entries=_checked_revision_queue(product,limit)
    selected=None
    if select_proposal_id is not None:
        matches=[row for row in entries
                 if row["proposal_id"]==select_proposal_id]
        if len(matches)!=1:
            raise W10ReviewError("selected proposal is outside current bounded window")
        selected=matches[0]
    result={
        "schema":SCHEMA,
        "status":(STATUS_SELECTED if selected is not None else
                  STATUS_PENDING if entries else STATUS_EMPTY),
        "w09_owner_review_digest_sha256":w09["review_digest_sha256"],
        "w09_real_signed_manual_pack_consumed":False,
        "w09_portable_draft_parity_pass":
            w09["portable_first_party_draft_independent_QA"][
                "standalone_parity_cases"],
        "w08_reference_heldout_query_cases":9,
        "w08_reference_heldout_mismatches":0,
        "w08_first_party_real_metadata_rows":
            w09["w08_first_party_real_metadata_rows"],
        "proposal_window_total":queue["candidate_count_in_loaded_window"],
        "proposal_window_returned":len(entries),
        "proposal_window_truncated":bool(
            queue["omitted_from_loaded_window"] or
            queue["source_window_truncated"]),
        "proposals":entries,
        "selected_proposal":selected,
        "rollback_readiness":{
            "status":"ROLLBACK_PRECONDITIONS_NOT_ATTESTED_NO_ACTION",
            "protected_current_baseline_source_sha256": (
                selected["old_code_source_pin"][
                    "current_checked_out_source_sha256"]
                if selected is not None else None),
            "actual_prechange_recoverable_bytes_attested":False,
            "candidate_exact_source_and_commit_attested":False,
            "candidate_behavior_equivalence_tested":False,
            "negative_security_regression_tested":False,
            "rollback_restore_exercised":False,
            "post_rollback_W09_consumer_reverified":False,
            "rollback_performed":False,
        },
        "remaining_manual_gates":list(BLOCKERS),
        "unapproved_experiment_revision_is_release":False,
        "actual_revision_applied":False,
        "git_branch_or_commit_modified":False,
        "operating_code_modified":False,
        "runtime_rollback_executed":False,
        "new_source_or_owner_signing_key_accessed":False,
        "network_requests":0,"operating_database_writes":0,
        "scheduler_modified":False,"model_weights_changed":False,
        "auto_promoted":False,"customer_release_authorized":False,
        "v1_accepted":False,
    }
    result["review_sha256"]=_json_hash({
        "schema":SCHEMA,"w09":result["w09_owner_review_digest_sha256"],
        "queue":sorted(item["proposal_id"] for item in entries),
        "source":sorted((item["target_ucie_component"],
                         item["old_code_source_pin"]["current_checked_out_source_sha256"])
                        for item in entries),
        "selected":selected["proposal_id"] if selected else None,
    })
    result["review_sha256_is_owner_approval"]=False
    return result


def main()->int:
    parser=argparse.ArgumentParser(
        description="UCIE W10 pinned revision/rollback impact READONLY review")
    parser.add_argument("--ucie-root",type=Path,required=True)
    parser.add_argument("--limit",type=int,default=10)
    parser.add_argument("--select-proposal-id")
    parser.add_argument("--expected-w09-review-digest")
    parser.add_argument("--queries",type=int,default=32)
    parser.add_argument("--repeats",type=int,default=3)
    a=parser.parse_args()
    try:
        result=review_w10_revision_and_rollback(
            a.ucie_root,limit=a.limit,select_proposal_id=a.select_proposal_id,
            expected_w09_review_digest=a.expected_w09_review_digest,
            queries=a.queries,repeats=a.repeats)
    except (W10ReviewError,ValueError,KeyError,OSError,TypeError) as exc:
        print(json.dumps({
            "schema":SCHEMA,"status":"W10_REVIEW_FAIL_CLOSED",
            "error_type":type(exc).__name__,
            "network_requests":0,"operating_database_writes":0,
            "runtime_rollback_executed":False,
            "customer_release_authorized":False,
        },sort_keys=True))
        return 2
    print(json.dumps(result,ensure_ascii=True,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
