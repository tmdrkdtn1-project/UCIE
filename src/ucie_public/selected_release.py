"""Owner-selected, evidence-gated PUBLIC_ONLY manual Rulepack contract.

This is a new versioned release format; existing Serial 1/2 verifiers,
signatures, scanner and releases are unchanged. Only previously independently
observed and separately owner-consentable rules are eligible. All other
Stage12 candidates stay unverified. No signing without fresh live public CI
and explicit per-rule owner risk text. No automatic rule approval or fixes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
import zipfile

from cryptography.exceptions import InvalidSignature

from .policy import PolicyError
from .rulepack import (
    canonical_json, digest, key_id, _private_key, _public_key, _valid_outpath,
)
from .owner_release import (
    MODE, RISK, _check_evidence, _local_clean_sha, validate_live_automated_qa,
)
from .production_release import SCOPE, _parse_date
from .multi_owner_release import (
    SECOND_RISK, SECOND_RUN, SECOND_SHA, POSTFIX_STEP, REPO,
    RELEASE_RULES, DECISIONS, _postfix_ci, _archive, _decode,
)
from .rule_matcher import match_signed_static_rules

SCHEMA = "UCIE_PUBLIC_SELECTED_OWNER_RELEASE_V1"
CONFIRM = "AUTHORIZE_UCIE_SELECTED_RULES_PUBLIC_MANUAL_OWNER_RISK_RELEASE"
RULE_ORDER = tuple(r["rule_id"] for r in RELEASE_RULES)
# ONLY the two previously verified rules are currently release-eligible.
# New public-miner candidates are never added automatically.
ELIGIBLE = {
    r["rule_id"]: (r, decision, risk)
    for r, decision, risk in zip(
        RELEASE_RULES, DECISIONS, (RISK, SECOND_RISK), strict=True)
}
EXPECTED_SECOND_CI = {
    "schema": "UCIE_SECOND_RULE_CI_OWNER_CHECK_V1",
    "repository": REPO, "run_id": SECOND_RUN, "head_sha": SECOND_SHA,
    "patch_ci_step": POSTFIX_STEP, "result": "PASS_ON_PINNED_CI",
    "release_version_coverage_proven": False,
    "independent_human_qa": False,
}
FIELDS = frozenset({
    "schema", "channel", "scope", "serial", "created_utc", "expires_utc",
    "owner_key_id", "source_commit_sha", "rule_count", "rule_ids",
    "rules_sha256", "decisions_sha256", "evidence_sha256",
    "owner_risk_accepted", "automated_qa_verified",
    "independent_human_qa_approved", "legal_license_signoff",
    "production_approved", "deploy_allowed", "auto_apply",
    "private_project_access",
})


def selected_payload(ids: object) -> tuple[list[dict], list[dict]]:
    """Require nonempty canonical selection of exact eligible public rules."""
    if (type(ids) is not list or not 1 <= len(ids) <= 64
            or any(type(item) is not str for item in ids)
            or len(set(ids)) != len(ids)
            or ids != [name for name in RULE_ORDER if name in ids]):
        raise PolicyError("duplicate, unsupported or unordered rule selection")
    if any(name not in ELIGIBLE for name in ids):
        raise PolicyError("candidate lacks separately verified QA and owner risk contract")
    return (
        [dict(ELIGIBLE[name][0]) for name in ids],
        [dict(ELIGIBLE[name][1]) for name in ids],
    )


def publish_selected_owner_release(
    root: Path, private_path: Path, output: Path, *,
    run_id: int, serial: int, rule_ids: list[str],
    confirmation: str, risk_acceptances: dict[str, str],
) -> Path:
    """Explicit owner-only publish; synthetic CI passes no real owner signature."""
    rules, decisions = selected_payload(rule_ids)
    if (confirmation != CONFIRM
            or type(risk_acceptances) is not dict
            or set(risk_acceptances) != set(rule_ids)
            or any(risk_acceptances[name] != ELIGIBLE[name][2] for name in rule_ids)):
        raise PolicyError("missing separate explicit risk acceptance per selected rule")
    if type(serial) is not int or not 3 <= serial <= 10000000:
        raise PolicyError("selected release must use new serial 3 or above")
    root = Path(root)
    local_sha = _local_clean_sha(root)
    main = validate_live_automated_qa(run_id)
    if main["head_sha"] != local_sha:
        raise PolicyError("owner main checkout and QA commit do not match")
    # An exact successful patched-binary CI is independently required if and
    # ONLY if the second PowerShell rule is included.
    second = _postfix_ci() if RULE_ORDER[1] in rule_ids else None
    if second is not None and second != EXPECTED_SECOND_CI:
        raise PolicyError("second rule CI proof differs from pinned result")

    signer = _private_key(Path(private_path))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    rules_bytes = canonical_json(rules)
    decisions_bytes = canonical_json(decisions)
    evidence_bytes = canonical_json({"main_ci": main, "second_ci": second})
    manifest = {
        "schema": SCHEMA, "channel": MODE, "scope": SCOPE,
        "serial": serial, "rule_count": len(rules), "rule_ids": rule_ids,
        "created_utc": now.isoformat().replace("+00:00", "Z"),
        "expires_utc": (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "owner_key_id": key_id(signer.public_key()),
        "source_commit_sha": local_sha,
        "rules_sha256": digest(rules_bytes),
        "decisions_sha256": digest(decisions_bytes),
        "evidence_sha256": digest(evidence_bytes),
        "owner_risk_accepted": True, "automated_qa_verified": True,
        "independent_human_qa_approved": False, "legal_license_signoff": False,
        "production_approved": True, "deploy_allowed": True,
        "auto_apply": False, "private_project_access": False,
    }
    manifest_bytes = canonical_json(manifest)
    target = _valid_outpath(root, Path(output))
    fd, temp = tempfile.mkstemp(
        dir=str(target.parent), prefix=".ucie_selected_owner_", suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as handle:
            with zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("manifest.json", manifest_bytes)
                z.writestr("rules/prevention.json", rules_bytes)
                z.writestr("evidence/automated_ci.json", evidence_bytes)
                z.writestr("evidence/rule_decisions.json", decisions_bytes)
                z.writestr("signatures/owner.sig", signer.sign(manifest_bytes))
        os.link(temp, target)  # never overwrite existing Rulepack
    finally:
        Path(temp).unlink(missing_ok=True)
    return target


def verify_selected_owner_release(
    pack: Path, trust: Path, *,
    min_serial: int = 3, at_time: datetime | None = None,
) -> dict:
    """Offline: exact signed selection, CI claims, consent scope and rollback."""
    if type(min_serial) is not int or not 3 <= min_serial <= 10000000:
        raise PolicyError("invalid selected owner Rulepack serial threshold")
    blobs = _archive(Path(pack))  # reuse existing exact-five-entry zip guard
    key = _public_key(Path(trust))
    man = _decode(blobs["manifest.json"])
    rules = _decode(blobs["rules/prevention.json"])
    decisions = _decode(blobs["evidence/rule_decisions.json"])
    evidence = _decode(blobs["evidence/automated_ci.json"])
    if (type(man) is not dict or set(man) != FIELDS
            or man["schema"] != SCHEMA or man["channel"] != MODE
            or man["scope"] != SCOPE or man["owner_key_id"] != key_id(key)
            or type(man["serial"]) is not int or man["serial"] < min_serial
            or type(man["rule_count"]) is not int
            or type(man["rule_ids"]) is not list
            or man["rule_count"] != len(man["rule_ids"])
            or man["owner_risk_accepted"] is not True
            or man["automated_qa_verified"] is not True
            or man["independent_human_qa_approved"] is not False
            or man["legal_license_signoff"] is not False
            or man["production_approved"] is not True
            or man["deploy_allowed"] is not True
            or man["auto_apply"] is not False
            or man["private_project_access"] is not False
            or man["rules_sha256"] != digest(blobs["rules/prevention.json"])
            or man["decisions_sha256"] != digest(blobs["evidence/rule_decisions.json"])
            or man["evidence_sha256"] != digest(blobs["evidence/automated_ci.json"])):
        raise PolicyError("unapproved/altered selected owner release")
    expected_rules, expected_decisions = selected_payload(man["rule_ids"])
    if rules != expected_rules or decisions != expected_decisions:
        raise PolicyError("rule proof, decisions or order differs from owner-eligible pins")
    if (type(evidence) is not dict
            or set(evidence) != {"main_ci", "second_ci"}):
        raise PolicyError("unexpected per-rule CI proof")
    _check_evidence(evidence["main_ci"])
    expected_second = (EXPECTED_SECOND_CI if RULE_ORDER[1] in man["rule_ids"]
                       else None)
    if (evidence["second_ci"] != expected_second
            or evidence["main_ci"]["head_sha"] != man["source_commit_sha"]):
        raise PolicyError("owner-reported CI evidence does not match selected rules")
    try:
        key.verify(blobs["signatures/owner.sig"], blobs["manifest.json"])
    except (InvalidSignature, ValueError) as exc:
        raise PolicyError("owner signature invalid") from exc
    now = at_time or datetime.now(timezone.utc)
    created, expiry = _parse_date(man["created_utc"]), _parse_date(man["expires_utc"])
    if (now.tzinfo is None or created > now + timedelta(minutes=5)
            or now >= expiry or expiry <= created
            or expiry - created > timedelta(days=7)):
        raise PolicyError("selected owner pack outside signed expiry")
    return {
        "result": "SELECTED_OWNER_RISK_PUBLIC_PACK_VERIFIED",
        "serial": man["serial"], "owner_signature": "VALID",
        "rule_count": len(rules), "rule_ids": list(man["rule_ids"]),
        "scope": SCOPE, "approval_mode": MODE,
        "source_commit_sha": man["source_commit_sha"],
        "independent_human_qa_approved": False,
        "legal_license_signoff": False,
        "released_version_fix_coverage_proven": False,
        "auto_apply": False, "production_approved": True,
        "deploy_allowed": True,
    }


def scan_selected_owner_receipt(
    pack: Path, trust: Path, scan: object, *, min_serial: int = 3,
) -> dict:
    """Only signed/verified allowlisted rule IDs can match inert AST receipts."""
    verified = verify_selected_owner_release(
        pack, trust, min_serial=min_serial)
    # The receiver reconstructs ONLY the verified signed selection; it never
    # accepts rule metadata directly from an untrusted scan receipt.
    rules, _ = selected_payload(verified["rule_ids"])
    matched = match_signed_static_rules(
        scan, rules, expected_approval=MODE)
    return {
        "schema": "UCIE_SELECTED_OWNER_PUBLIC_MANUAL_SCAN_V1",
        "status": "CANDIDATES_FOR_MANUAL_REVIEW" if matched
                  else "NO_SIGNED_RULE_MATCH",
        "rule_ids": verified["rule_ids"],
        "rule_count": verified["rule_count"],
        "pack_serial": verified["serial"],
        "owner_signature": "VALID",
        "source_sha256": scan["source_sha256"],
        "finding_count": len(matched),
        "findings": matched,
        "source_authentication_verified": False,
        "source_executed": False, "source_files_read": 0,
        "auto_fix_applied": False, "auto_apply": False,
        "production_approved": True, "deploy_allowed": True,
        "persistent_writes": 0,
    }
