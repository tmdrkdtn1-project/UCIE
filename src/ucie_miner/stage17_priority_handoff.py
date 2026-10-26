"""Stage17 human-review queue ranked by Stage12 evidence signals, never GO.

Read already verified UCIE-only Stage10/15 ledgers and the exact Stage12
candidate review handoff. A review urgency rank is NOT trust in upstream
behavior, security QA, release inclusion, license clearance or owner consent.
No external GETs, code execution, model updates, writes or rule promotions.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path

from .automated_candidate_qa import _checked_handoff
from .public_candidate_learning import _rows_from_stage10, _rows_from_stage15
from .public_review_triage import (
    triage_unverified_review_rows, REVIEW_WEIGHTS, EVIDENCE_LEVELS,
    ALLOWED_HINTS,
)
from .skill_profiles import PROFILE
from .public_discovery import SOURCE_SKILL
from .stage17_review_docket import (
    attest_stage16_aggregate, build_review_docket,
)
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_STAGE17_RANKED_PUBLIC_REVIEW_HANDOFF_V1"
MAX_SELECTED = 12


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False
    ).encode("ascii")).hexdigest()


def build_ranked_stage17_handoff(handoff: dict, docket: dict,
                                  triage: dict | None) -> dict:
    """Cross-link a complete Stage12 queue to its exact unverified revisions.

    The Stage12 handoff is already re-derived from its SQLite source ledgers
    by prepare_verification_handoff. The Stage17 docket is a pure, unsigned
    review result. Reject mismatch or forged GO before any ranked output.
    """
    complete, tasks = _checked_handoff(handoff)
    if (type(docket) is not dict
            or docket.get("schema") != "UCIE_STAGE17_CANDIDATE_REVIEW_DOCKET_V1"
            or type(docket.get("items")) is not list
            or docket.get("candidate_count") != len(docket["items"])
            or len(docket["items"]) != len(tasks)
            or docket.get("approved_rules_added") != 0
            or docket.get("independent_qa_pass_count") != 0
            or docket.get("production_approved") is not False
            or docket.get("auto_promoted") is not False
            or docket.get("new_public_gets") != 0
            or docket.get("persistent_writes") != 0
            or docket.get("stage12_review_status") != handoff["status"]
            or type(docket.get("docket_sha256")) is not str):
        raise ValueError("invalid Stage17 candidate review docket")
    original = dict(docket)
    digest = original.pop("docket_sha256")
    if digest != _digest(original):
        raise ValueError("altered Stage17 candidate docket digest")
    if not complete:
        # An incomplete review ledger cannot be used to claim that a source
        # revision was already entered into the operator's review queue.
        return {
            "schema": SCHEMA,
            "status": "STAGE12_REVIEW_LEDGER_INCOMPLETE_NO_GO",
            "stage12_handoff_status": handoff["status"],
            "stage16_aggregate_status": docket["stage16_aggregate_status"],
            "source_revisions": handoff.get("source_revisions", 0),
            "linked_revisions": len(tasks),
            "priority_selected_count": 0,
            "priority_selected_for_manual_review": [],
            "independent_fix_verified": False,
            "priority_is_confidence": False,
            "candidate_specific_ci_attested": False,
            "human_approval_required": True,
            "approved_rules_added": 0, "auto_promoted": False,
            "production_approved": False,
            "external_api_gets": 0, "persistent_writes": 0,
        }
    if (type(triage) is not dict
            or triage.get("schema") != "UCIE_PUBLIC_MULTIAXIS_REVIEW_TRIAGE_V1"
            or triage.get("status") != "UNVERIFIED_REVIEW_AGENDA_ONLY"
            or triage.get("production_approved") is not False
            or triage.get("auto_promoted") is not False
            or triage.get("priority_is_confidence") is not False
            or triage.get("source_origin_independently_attested") is not False
            or triage.get("upstream_fix_verified") is not False
            or triage.get("external_api_gets") != 0
            or triage.get("persistent_writes") != 0
            or type(triage.get("triaged_revisions")) is not int
            or triage["triaged_revisions"] != handoff["source_revisions"]
            or type(triage.get("selected_count")) is not int
            or not 0 <= triage["selected_count"] <= MAX_SELECTED
            or type(triage.get("selected_for_review")) is not list
            or triage["selected_count"] != len(triage["selected_for_review"])):
        raise ValueError("untrusted or incomplete Stage12 multiaxis triage")
    by_id = {}
    for entry in docket["items"]:
        key = entry.get("candidate_id_sha256") if type(entry) is dict else None
        if (type(key) is not str or key in by_id
                or entry.get("human_approval") is not False
                or entry.get("deploy_allowed") is not False
                or entry.get("independent_qa") != "NOT_PERFORMED"):
            raise ValueError("forged Stage17 candidate identity")
        by_id[key] = entry
    by_revision = {}
    for item in tasks:
        key = (
            item.get("source"), item.get("reference"),
            item.get("evidence_sha256"),
        )
        if key in by_revision:
            raise ValueError("duplicate Stage12 candidate revision")
        by_revision[key] = item
        if item["candidate_id_sha256"] not in by_id:
            raise ValueError("unbound Stage17 candidate revision")
        docket_item = by_id[item["candidate_id_sha256"]]
        if (docket_item.get("source") != item["source"]
                or docket_item.get("evidence_sha256") != item["evidence_sha256"]):
            raise ValueError("Stage17 candidate source or evidence mismatch")

    ranked = []
    chosen = set()
    for choice in triage["selected_for_review"]:
        if (type(choice) is not dict
                or choice.get("independent_fix_verified") is not False
                or choice.get("rule_approved") is not False
                or choice.get("license_approved") is not False
                or choice.get("release_inclusion_verified") is not False
                or type(choice.get("review_priority_score")) is not int
                or not 0 <= choice["review_priority_score"] <= 5
                or choice.get("review_priority_band") not in {
                    "REVIEW_FIRST", "NORMAL_REVIEW", "LOW_SIGNAL_REVIEW"
                }
                or type(choice.get("error_pattern_tags")) is not list
                or len(choice["error_pattern_tags"]) > len(REVIEW_WEIGHTS)
                or any(type(tag) is not str or tag not in REVIEW_WEIGHTS
                       for tag in choice["error_pattern_tags"])
                or choice["error_pattern_tags"] != sorted(
                    set(choice["error_pattern_tags"]))
                or choice.get("evidence_level") not in EVIDENCE_LEVELS
                or (choice.get("patch_transition_hint") is not None
                    and choice["patch_transition_hint"] not in ALLOWED_HINTS)):
            raise ValueError("untrusted Stage12 selected review metadata")
        expected_weight = max(
            (REVIEW_WEIGHTS[tag] for tag in choice["error_pattern_tags"]),
            default=0)
        expected_band = ("REVIEW_FIRST" if expected_weight >= 4 else
                         "NORMAL_REVIEW" if expected_weight >= 2 else
                         "LOW_SIGNAL_REVIEW")
        if (choice["review_priority_score"] != expected_weight
                or choice["review_priority_band"] != expected_band):
            raise ValueError("forged Stage12 review priority")
        ref = (choice.get("source"), choice.get("reference"),
               choice.get("evidence_sha256"))
        if ref in chosen or ref not in by_revision:
            raise ValueError("Stage12 ranked revision not linked to Stage17")
        chosen.add(ref)
        source = by_revision[ref]
        if (choice.get("human_review_action")
                != PROFILE[SOURCE_SKILL[ref[0]]]["recommended_action"]):
            raise ValueError("Stage12 review action mismatch")
        docket_item = by_id[source["candidate_id_sha256"]]
        ranked.append({
            "candidate_id_sha256": source["candidate_id_sha256"],
            "source": ref[0], "reference": ref[1],
            "evidence_sha256": ref[2],
            "error_pattern_tags": choice["error_pattern_tags"],
            "evidence_level": choice["evidence_level"],
            "review_priority_score": choice["review_priority_score"],
            "review_priority_band": choice["review_priority_band"],
            "candidate_rule_id": docket_item.get("rule_id"),
            "stage17_review_lane": docket_item["triage"],
            "required_next_actions": docket_item["required_next_actions"],
            "independent_fix_verified": False,
            "license_approved": False,
            "candidate_specific_ci_attested": False,
            "human_approved": False,
            "deploy_allowed": False,
        })
    return {
        "schema": SCHEMA,
        "status": "RANKED_HUMAN_REVIEW_AGENDA_NO_GO",
        "stage12_handoff_status": handoff["status"],
        "stage16_aggregate_status": docket["stage16_aggregate_status"],
        "stage17_docket_sha256": digest,
        "source_revisions": handoff["source_revisions"],
        "linked_revisions": len(tasks),
        "priority_selected_count": len(ranked),
        "priority_selected_for_manual_review": ranked,
        "independent_fix_verified": False,
        "priority_is_confidence": False,
        "candidate_specific_ci_attested": False,
        "human_approval_required": True,
        "approved_rules_added": 0, "auto_promoted": False,
        "production_approved": False,
        "external_api_gets": 0, "persistent_writes": 0,
    }


def inspect_stage17_ranked_review(root: Path, *,
                                  now: datetime | None = None) -> dict:
    """Actual UCIE-host read-only entry point; never register a new timer."""
    root = Path(root)
    if root.name.casefold() != "ucie" or root.is_symlink() or not root.is_dir():
        raise ValueError("dedicated UCIE checkout required")
    handoff = prepare_verification_handoff(root)
    stage16 = attest_stage16_aggregate(root, now=now)
    docket = build_review_docket(handoff, stage16)
    complete, _ = _checked_handoff(handoff)
    triage = None
    if complete:
        triage = triage_unverified_review_rows(
            _rows_from_stage10(root) + _rows_from_stage15(root))
    return build_ranked_stage17_handoff(handoff, docket, triage)
