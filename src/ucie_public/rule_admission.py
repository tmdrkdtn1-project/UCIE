"""Read-only candidate-to-owner-signed-rule admission reconciliation.

The Stage12 review queue alone can NEVER approve a new prevention rule.
Only a separately and fully verified pre-existing signed owner release is
trusted. This records exact public-PR matches, not fresh owner acceptance.
It never signs, alters the miner DB, deploys, or changes a review status.
"""
from __future__ import annotations

from pathlib import Path
import re

from .multi_owner_release import (
    RELEASE_RULES, RULE_IDS, verify_two_rule_owner_release,
)
from .policy import PolicyError

SHA64 = re.compile(r"[a-f0-9]{64}\Z")


def reconcile_existing_signed_rules(
        root: Path, pack: Path, trust: Path, *,
        min_serial: int = 2) -> dict:
    """Reconcile candidate evidence ONLY against an already-owner-signed pack.

    An existing signed rule is not evidence that a newly mined candidate
    passed tests, license review, or was individually approved for a NEW
    release. New-rule promotion is always disabled by this read-only API.
    """
    from ucie_miner.verification_handoff import (
        PINNED_RULES, PR_REF, FIX_PR_REF, prepare_verification_handoff,
    )
    from ucie_miner.static_rule_bridge import SOURCE_BINDINGS

    verified = verify_two_rule_owner_release(
        Path(pack), Path(trust), min_serial=min_serial)
    if (verified.get("result") != "OWNER_RISK_TWO_RULE_PUBLIC_PACK_VERIFIED"
            or verified.get("owner_signature") != "VALID"
            or verified.get("scope") != "PUBLIC_ONLY_MANUAL_STATIC_SCAN"
            or verified.get("rule_ids") != list(RULE_IDS)
            or verified.get("auto_apply") is not False):
        raise PolicyError("owner-signed rule release not authenticated")

    handoff = prepare_verification_handoff(Path(root))
    if (handoff.get("schema") !=
            "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1"
            or handoff.get("auto_promoted") is not False
            or handoff.get("production_approved") is not False
            or handoff.get("deploy_allowed") is not False
            or type(handoff.get("tasks")) is not list):
        raise PolicyError("untrusted candidate handoff")
    rows = handoff["tasks"]
    if (handoff["status"] != "LINKED_UNVERIFIED_NO_GO"
            or handoff.get("pending_source_revisions") != 0):
        return {
            "schema": "UCIE_EXISTING_SIGNED_RULE_RECONCILIATION_V1",
            "status": "CANDIDATE_LEDGER_INCOMPLETE_NO_GO",
            "owner_pack_serial": verified["serial"],
            "previously_signed_rule_count": len(RULE_IDS),
            "matched_existing_rules": 0, "new_rules_approved": 0,
            "results": [], "auto_promoted": False,
            "production_approved_for_new_candidates": False,
            "deploy_allowed": False, "persistent_writes": 0,
        }

    signed = {r["rule_id"]: r for r in RELEASE_RULES}
    if set(signed) != set(RULE_IDS):
        raise PolicyError("duplicate or missing signed rule definition")
    candidates = {rid: [] for rid in RULE_IDS}
    seen_fingerprints = set()
    for entry in rows:
        if (type(entry) is not dict
                or entry.get("status") != "UNVERIFIED_CANDIDATE_ONLY"
                or entry.get("approval") is not False
                or not isinstance(entry.get("blocking_reasons"), list)
                or "VERIFICATION_NOT_PERFORMED"
                   not in entry["blocking_reasons"]):
            raise PolicyError("source candidate falsely marked verified")
        fp = entry.get("candidate_id_sha256")
        evidence = entry.get("evidence_sha256")
        if (type(fp) is not str or not SHA64.fullmatch(fp)
                or type(evidence) is not str or not SHA64.fullmatch(evidence)
                or fp in seen_fingerprints):
            raise PolicyError("invalid or repeated candidate provenance")
        seen_fingerprints.add(fp)
        proposal = entry.get("stage6_candidate")
        if proposal is None:
            continue
        if (type(proposal) is not dict
                or proposal.get("status") != "UNVERIFIED_CANDIDATE_ONLY"
                or proposal.get("executable_command") is not None
                or proposal.get("rule_code") not in signed):
            continue  # Any unsigned or not yet approved rule remains blocked.
        code = proposal["rule_code"]
        source = entry.get("source")
        ref = entry.get("reference")
        binding = SOURCE_BINDINGS.get(code)
        match = (PR_REF.fullmatch(ref) or FIX_PR_REF.fullmatch(ref)
                 if type(ref) is str else None)
        if match is None or binding is None:
            raise PolicyError("candidate does not carry a public PR pin")
        number, merge_sha = int(match.group(1)), match.group(2)
        if (merge_sha != signed[code]["upstream_merge_sha"]
                or binding != (source, number)
                or PINNED_RULES.get((source, number, merge_sha)) != code
                or proposal.get("source") != source
                or proposal.get("canonical_pr_number") != number
                or not isinstance(proposal.get("required_gates"), dict)
                or any(value != "NOT_VERIFIED"
                       for value in proposal["required_gates"].values())):
            raise PolicyError("staged candidate differs from signed source")
        candidates[code].append({
            "candidate_id_sha256": fp,
            "source_evidence_sha256": evidence,
            "source": source, "reference": ref,
            "duplicate_revision": (
                "MULTIPLE_EVIDENCE_REVISIONS_REQUIRE_SELECTION"
                in entry["blocking_reasons"]),
        })

    results = []
    matched = 0
    for code in RULE_IDS:
        found = candidates[code]
        # Multiple revisions, even with the same PR, are NOT silently merged.
        unique = len(found) == 1 and not found[0]["duplicate_revision"]
        if unique:
            matched += 1
        results.append({
            "rule_id": code,
            "existing_owner_signed": True,
            "staged_match": "SINGLE_SOURCE_REVISION" if unique else (
                "AMBIGUOUS_REVISIONS_NO_GO" if len(found) > 1
                or any(x["duplicate_revision"] for x in found)
                else "NOT_IN_CANDIDATE_LEDGER_NO_GO"),
            "candidate_id_sha256": (
                found[0]["candidate_id_sha256"] if unique else None),
            "new_candidate_qa_verified": False,
            "new_candidate_owner_approved": False,
        })
    return {
        "schema": "UCIE_EXISTING_SIGNED_RULE_RECONCILIATION_V1",
        "status": "EXISTING_PACK_METADATA_RECONCILED_NO_NEW_APPROVAL",
        "owner_pack_serial": verified["serial"],
        "previously_signed_rule_count": len(RULE_IDS),
        "matched_existing_rules": matched, "new_rules_approved": 0,
        "results": results, "auto_promoted": False,
        "production_approved_for_new_candidates": False,
        "deploy_allowed": False, "persistent_writes": 0,
    }
