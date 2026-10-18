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
                or proposal.get("executable_command") is not None):
            raise PolicyError("unsafe or executable staged rule proposal")
        if proposal.get("rule_code") not in signed:
            continue  # An unsigned/not-approved rule cannot be activated.
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


def reconcile_mixed_signed_candidates(
        root: Path, pack: Path, trust: Path, *,
        min_serial: int = 4) -> dict:
    """End-to-end read-only pipeline: authenticated N-rule pack vs miner queue.

    Signed rule truth comes ONLY from the verified owner Rulepack. Staged
    candidate metadata is untrusted and is NEVER a substitute for owner QA,
    consent or signing. A missing/incomplete miner queue cannot downgrade or
    revoke a previously signed pack; it blocks the fresh-miner handoff.
    Future additional rules are obtained from authenticated release profiles,
    not a hard-coded first/two-rule list.
    """
    from ucie_miner.verification_handoff import (
        PINNED_RULES, PR_REF, FIX_PR_REF, prepare_verification_handoff,
    )
    from ucie_miner.static_rule_bridge import SOURCE_BINDINGS
    from .mixed_release import (
        selected_payload, verify_mixed_owner_release,
    )

    verified = verify_mixed_owner_release(
        Path(pack), Path(trust), min_serial=min_serial)
    ids = verified.get("rule_ids")
    if (verified.get("result") != "MIXED_OWNER_PUBLIC_MANUAL_PACK_VERIFIED"
            or verified.get("owner_signature") != "VALID"
            or verified.get("scope") != "PUBLIC_ONLY_MANUAL_STATIC_SCAN"
            or type(ids) is not list or not ids
            or verified.get("rule_count") != len(ids)
            or verified.get("auto_apply") is not False):
        raise PolicyError("mixed owner-signed release not authenticated")
    rules, _ = selected_payload(ids)
    by_id = {x["rule_id"]: x for x in rules}
    if len(by_id) != len(rules) or set(by_id) != set(ids):
        raise PolicyError("signed release selection has conflicting identities")
    for rule_id, rule in by_id.items():
        pair = SOURCE_BINDINGS.get(rule_id)
        if (pair is None or PINNED_RULES.get(
                (pair[0], pair[1], rule["upstream_merge_sha"])) != rule_id
                or rule["upstream"] !=
                    f"https://github.com/{pair[0]}/pull/{pair[1]}"):
            raise PolicyError("signed source cannot be bound to miner candidate")

    report = prepare_verification_handoff(Path(root))
    if (type(report) is not dict
            or report.get("schema") !=
               "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1"
            or report.get("auto_promoted") is not False
            or report.get("production_approved") is not False
            or report.get("deploy_allowed") is not False
            or type(report.get("tasks")) is not list):
        raise PolicyError("untrusted public candidate handoff")
    linked = (report.get("status") == "LINKED_UNVERIFIED_NO_GO"
              and report.get("pending_source_revisions") == 0
              and type(report.get("linked_revisions")) is int
              and type(report.get("source_revisions")) is int
              and report["linked_revisions"] == report["source_revisions"])
    # Fail closed on a completely unexpected state even if row counts agree.
    if report.get("status") not in (
            "LINKED_UNVERIFIED_NO_GO", "REVIEW_LEDGER_ABSENT_NO_GO",
            "SOURCE_REVISIONS_PENDING_NO_GO"):
        raise PolicyError("unexpected miner review-queue state")

    matches = {rid: [] for rid in ids}
    unmatched = 0
    fingerprints = set()
    for entry in report["tasks"]:
        if (type(entry) is not dict
                or entry.get("status") != "UNVERIFIED_CANDIDATE_ONLY"
                or entry.get("approval") is not False
                or type(entry.get("blocking_reasons")) is not list
                or "VERIFICATION_NOT_PERFORMED"
                   not in entry["blocking_reasons"]):
            raise PolicyError("candidate ledger forged an approval")
        fp = entry.get("candidate_id_sha256")
        evidence = entry.get("evidence_sha256")
        if (type(fp) is not str or SHA64.fullmatch(fp) is None
                or type(evidence) is not str
                or SHA64.fullmatch(evidence) is None
                or fp in fingerprints):
            raise PolicyError("invalid/duplicate candidate evidence identity")
        fingerprints.add(fp)
        proposal = entry.get("stage6_candidate")
        if proposal is None:
            unmatched += 1
            continue
        if (type(proposal) is not dict
                or proposal.get("status") != "UNVERIFIED_CANDIDATE_ONLY"
                or proposal.get("executable_command") is not None
                or type(proposal.get("required_gates")) is not dict
                or not proposal["required_gates"]
                or any(value != "NOT_VERIFIED"
                       for value in proposal["required_gates"].values())):
            raise PolicyError("staged public candidate is executable or promoted")
        code = proposal.get("rule_code")
        if code not in by_id:
            unmatched += 1
            continue
        ref = entry.get("reference")
        found = (PR_REF.fullmatch(ref) or FIX_PR_REF.fullmatch(ref)
                 if type(ref) is str else None)
        source, number = SOURCE_BINDINGS[code]
        if (found is None
                or int(found.group(1)) != number
                or found.group(2) != by_id[code]["upstream_merge_sha"]
                or entry.get("source") != source
                or proposal.get("source") != source
                or proposal.get("canonical_pr_number") != number
                or PINNED_RULES.get((source, number, found.group(2))) != code):
            raise PolicyError("staged candidate claims wrong signed source")
        matches[code].append({
            "candidate_id_sha256": fp,
            "evidence_sha256": evidence,
            "duplicate_revision_flag": (
                "MULTIPLE_EVIDENCE_REVISIONS_REQUIRE_SELECTION"
                in entry["blocking_reasons"]),
        })
    states = []
    count = 0
    for code in ids:
        rows = matches[code] if linked else []
        unique = len(rows) == 1 and not rows[0]["duplicate_revision_flag"]
        if unique:
            count += 1
        states.append({
            "rule_id": code,
            "existing_owner_signature_verified": True,
            "miner_provenance": (
                "EXACT_SINGLE_REVISION_UNVERIFIED"
                if unique else "DUPLICATE_REVISIONS_NO_GO"
                if len(rows) > 1
                or any(x["duplicate_revision_flag"] for x in rows)
                else "NOT_LINKED_NO_GO"),
            "candidate_id_sha256": (
                rows[0]["candidate_id_sha256"] if unique else None),
            "new_candidate_qa_passed": False,
            "new_candidate_owner_approved": False,
        })
    return {
        "schema": "UCIE_SIGNED_MIXED_MINER_PIPELINE_V1",
        "status": ("SIGNED_PACK_AND_LEDGER_RECONCILED_NO_NEW_APPROVAL"
                   if linked else "SIGNED_PACK_VALID_MINER_LEDGER_NO_GO"),
        "owner_pack_serial": verified["serial"],
        "signed_rule_count": len(ids),
        "signed_rule_ids": list(ids),
        "owner_signature": "VALID",
        "miner_handoff_status": report["status"],
        "matched_signed_rule_revisions": count,
        "unmatched_unsigned_candidate_revisions": unmatched,
        "new_rules_approved": 0,
        "results": states,
        "auto_promoted": False,
        "new_production_approval_granted": False,
        "automatic_deployment": False,
        "persistent_writes": 0,
    }
