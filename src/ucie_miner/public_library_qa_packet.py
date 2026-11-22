"""Strict signed-claim binding for one candidate's external QA evidence packet.

Input bytes are provided explicitly by a reviewer, never downloaded or
executed here. Checks SHA256 of *actual bounded supplied bytes*, exact public
candidate SHA/digest, and matches the packet's canonical digest to the
existing separately authenticated owner+QA signed claim in UCIE's immutable
review history. This proves packet integrity/binding only, NOT that claimed
external QA was honest, independent, run or successful. Everything is NO_GO.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import re

from ucie_public.policy import PolicyError
from ucie_public.rulepack import canonical_json

from .public_discovery import DiscoveryError
from .public_library_review_binding import inspect_library_review_closure
from .skill_profiles import PROFILE

SCHEMA = "UCIE_LIBRARY_CANDIDATE_QA_EVIDENCE_PACKET_V1"
OUTPUT_SCHEMA = "UCIE_LIBRARY_CANDIDATE_QA_PACKET_INSPECTION_V1"
CLAIM_STATE = "KEYHOLDER_SIGNED_CLAIMS_AWAIT_INDEPENDENT_QA_NO_GO"
STATUS = "SIGNED_QA_PACKET_BYTES_BOUND_AUDIT_PENDING_NO_GO"
MAX_BLOB_BYTES = 8192
BLOB_NAMES = (
    "affected_behavior_observation",
    "fixed_behavior_observation",
    "security_negative_case_observation",
    "license_review_observation",
    "published_release_observation",
    "reviewer_identity_observation",
)
FIELDS = frozenset({
    "schema", "public_url", "pinned_revision_sha", "evidence_sha256",
    "claimed_version", "first_party_regression_plan",
    "tested_pinned_revision_sha", "runner_repository", "runner_run_id",
    "runner_commit_sha", "observation_utc", "artifact_sha256",
    "result_claim",
})
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
FIXED_CLAIM = "OBSERVATIONS_SUBMITTED_NOT_INDEPENDENTLY_REPRODUCED"


def _utc(value, *, now):
    if (type(value) is not str or len(value) > 40):
        raise PolicyError("invalid candidate QA observation UTC")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PolicyError("invalid candidate QA observation time") from exc
    if (stamp.tzinfo is None or stamp.utcoffset() != timedelta(0)
            or stamp > now + timedelta(minutes=5)
            or now - stamp > timedelta(days=30)):
        raise PolicyError("untrusted candidate QA observation timestamp")
    return stamp


def inspect_library_candidate_qa_packet(
        root, current, public_url, packet: dict, artifacts: dict, *,
        owner_trust, qa_trust, expected_head_sha256,
        previous=None, at_time=None):
    """Check exact bytes tied to an already authenticated signed QA claim.

    The review history must already be present and hash-bound with a supplied
    externally trusted expected head. A packet alone is not an attestation,
    and signatures authenticate keyholders' claims, not actual QA.
    """
    now = at_time or datetime.now(timezone.utc)
    if (not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset() != timedelta(0)):
        raise PolicyError("UCIE candidate QA requires UTC inspection time")
    if (type(public_url) is not str or type(packet) is not dict
            or set(packet) != FIELDS or type(artifacts) is not dict
            or set(artifacts) != set(BLOB_NAMES)):
        raise PolicyError("unexpected candidate QA packet envelope")

    closure = inspect_library_review_closure(
        root, current, owner_trust=owner_trust, qa_trust=qa_trust,
        expected_head_sha256=expected_head_sha256,
        previous=previous, at_time=now)
    selected = [item for item in closure["review_records"]
                if item["public_url"] == public_url]
    if len(selected) != 1:
        raise PolicyError("candidate not in bounded validated Library")
    card = selected[0]
    if (card["review_state"] != CLAIM_STATE
            or not card["ledger_claim_revision_matches"]
            or type(card.get("signed_review_evidence_sha256")) is not str
            or SHA64.fullmatch(card["signed_review_evidence_sha256"]) is None):
        raise PolicyError("missing current, nonrevoked, unexpired signed QA claim")

    if (packet["schema"] != SCHEMA
            or packet["public_url"] != card["public_url"]
            or packet["pinned_revision_sha"] != card["pinned_revision_sha"]
            or packet["evidence_sha256"] != card["evidence_sha256"]
            or packet["claimed_version"] != card["signed_keyholder_claim_version"]
            or packet["first_party_regression_plan"] !=
               PROFILE[card["skill_id"]]["recommended_action"]
            or packet["tested_pinned_revision_sha"] != card["pinned_revision_sha"]
            or packet["runner_repository"] != "tmdrkdtn1-project/UCIE"
            or type(packet["runner_run_id"]) is not int
            or not 1 <= packet["runner_run_id"] <= 999999999999
            or type(packet["runner_commit_sha"]) is not str
            or SHA40.fullmatch(packet["runner_commit_sha"]) is None
            or packet["result_claim"] != FIXED_CLAIM):
        raise PolicyError("candidate QA packet unbound or forged")
    _utc(packet["observation_utc"], now=now)

    digest_map = packet["artifact_sha256"]
    if (type(digest_map) is not dict or set(digest_map) != set(BLOB_NAMES)):
        raise PolicyError("candidate QA evidence artifact set incomplete")
    if len(canonical_json(packet)) > 4096:
        raise PolicyError("candidate QA packet too large")
    packet_sha = hashlib.sha256(canonical_json(packet)).hexdigest()
    if packet_sha != card["signed_review_evidence_sha256"]:
        raise PolicyError("QA packet digest differs from signed review decision")

    verified_artifacts = 0
    for name in BLOB_NAMES:
        blob = artifacts[name]
        digest = digest_map[name]
        if (type(blob) is not bytes or
                not 1 <= len(blob) <= MAX_BLOB_BYTES
                or type(digest) is not str or SHA64.fullmatch(digest) is None
                or hashlib.sha256(blob).hexdigest() != digest):
            raise PolicyError("evidence artifact bytes absent or digest mismatch")
        verified_artifacts += 1
    if digest_map[BLOB_NAMES[0]] == digest_map[BLOB_NAMES[1]]:
        raise PolicyError("affected/fixed observation artifacts indistinguishable")

    return {
        "schema": OUTPUT_SCHEMA,
        "status": STATUS,
        "public_url": card["public_url"],
        "source": card["source"],
        "skill_id": card["skill_id"],
        "pinned_revision_sha": card["pinned_revision_sha"],
        "evidence_sha256": card["evidence_sha256"],
        "review_id_sha256": card["review_id_sha256"],
        "signed_claim_event_serial": card["ledger_event_serial"],
        "signed_packet_sha256": packet_sha,
        "packet_sha256_matches_signed_review": True,
        "supplied_artifact_digests_match_bytes": verified_artifacts,
        "artifact_set_count": len(BLOB_NAMES),
        "source_release_inclusion_confirmed_by_independent_source": False,
        "license_content_reviewed_independently": False,
        "security_negative_behavior_independently_reproduced": False,
        "regression_affected_and_fixed_behaviors_independently_reproduced": False,
        "runner_run_id": packet["runner_run_id"],
        "runner_workflow_conclusion_checked_live": False,
        "runner_attested_source_sha_independently_checked": False,
        "reviewer_identity_and_independence_verified": False,
        "owner_release_authorization": False,
        "candidate_rule_approval": False,
        "automatic_rule_promotions": 0,
        "external_code_executed": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "source_bytes_persisted": False,
        "other_project_accesses": 0,
        "production_approved": False,
    }
