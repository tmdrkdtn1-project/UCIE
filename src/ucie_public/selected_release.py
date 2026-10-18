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
    MODE, RISK, JOBS, _public_json, _step_ok, _check_evidence,
    _local_clean_sha, validate_live_automated_qa,
)
from .production_release import SCOPE, _parse_date
from .multi_owner_release import (
    SECOND_RISK, SECOND_RUN, SECOND_SHA, POSTFIX_STEP, REPO,
    RELEASE_RULES, DECISIONS, _postfix_ci, _archive, _decode,
)
from .rule_matcher import match_signed_static_rules

SCHEMA = "UCIE_PUBLIC_SELECTED_OWNER_RELEASE_V1"
CONFIRM = "AUTHORIZE_UCIE_SELECTED_RULES_PUBLIC_MANUAL_OWNER_RISK_RELEASE"
# The third candidate is eligible for owner REVIEW AND RISK ACCEPTANCE only
# after the exact before/after PowerShell #28042 behavior was observed by CI.
# This does NOT sign the rule, enable automatic promotion or license claims.
THIRD_RUN = 39107766637
THIRD_SHA = "9dfbae4df7e23f3ebd2d78427f513c8194a300ab"
THIRD_BRANCH = "core/third-rule-real-fuzzy-regression-20261018"
THIRD_STEP = "Third rule fixed fuzzy behavior in official post-fix developer build (one-shot PR)"
THIRD_BASELINE_STEP = "Third rule Get-Command fuzzy duplicates behavioral observation (disposable runner, no approval)"
THIRD_RISK = "I_ACCEPT_POWERSHELL_FUZZY_DUPLICATES_OBSERVED_7_6_6_AND_NO_VERIFIED_RELEASE_COVERAGE"
THIRD_RULE = {
    "rule_id": "PS_FUZZY_GET_COMMAND_DUPLICATES",
    "pattern": "PowerShell Get-Command -UseFuzzyMatching may return duplicate command identities",
    "problem": "PowerShell 7.6.6 returned two matching copies of the same module command in disposable Windows and Ubuntu CI",
    "safe_guidance": "Inspect fuzzy matches for duplicate Name/CommandType/Source identities before using results",
    "affected_observation": "PowerShell 7.6.6 Windows/Linux; corrected 7.7.0-preview.6 development artifact; released versions not verified",
    "upstream": "https://github.com/PowerShell/PowerShell/pull/28042",
    "upstream_merge_sha": "bd8cb01a7d5b86129c45eaa14ab5830a63b1283f",
    "runtime_ci": "https://github.com/tmdrkdtn1-project/UCIE/actions/runs/39107766637",
    "scanner": "ucie_powershell_static_candidates.ps1",
    "automation": "NEVER_AUTO_APPLY", "risk": "DUPLICATE_FUZZY_COMMAND_RESULT",
    "approval": MODE,
}
THIRD_DECISION = {
    "rule_id": THIRD_RULE["rule_id"],
    "upstream_merge_sha": THIRD_RULE["upstream_merge_sha"],
    "observed_runtime": "PowerShell 7.6.6 Windows/Linux",
    "postfix_dev_build": "PowerShell 7.7.0-preview.6 development CI build",
    "runtime_evidence": THIRD_RULE["runtime_ci"],
    "fixed_dev_build_evidence": THIRD_RULE["runtime_ci"],
    "release_version_coverage_proven": False,
    "owner_risk_accepted": True,
    "independent_human_qa": False, "legal_license_signoff": False,
    "auto_apply": False,
}
RELEASE_PROFILES = [
    *zip(RELEASE_RULES, DECISIONS, (RISK, SECOND_RISK), strict=True),
    (THIRD_RULE, THIRD_DECISION, THIRD_RISK),
]
RULE_ORDER = tuple(rule["rule_id"] for rule, _, _ in RELEASE_PROFILES)
# Only three exactly pinned and tested profiles; all other miner candidates
# remain unverified. Explicit owner phrase is still required per rule.
ELIGIBLE = {
    rule["rule_id"]: (rule, decision, risk)
    for rule, decision, risk in RELEASE_PROFILES
}
EXPECTED_SECOND_CI = {
    "schema": "UCIE_SECOND_RULE_CI_OWNER_CHECK_V1",
    "repository": REPO, "run_id": SECOND_RUN, "head_sha": SECOND_SHA,
    "patch_ci_step": POSTFIX_STEP, "result": "PASS_ON_PINNED_CI",
    "release_version_coverage_proven": False,
    "independent_human_qa": False,
}
EXPECTED_THIRD_CI = {
    "schema": "UCIE_THIRD_RULE_CI_OWNER_CHECK_V1",
    "repository": REPO, "run_id": THIRD_RUN, "head_sha": THIRD_SHA,
    "patch_ci_step": THIRD_STEP, "baseline_ci_step": THIRD_BASELINE_STEP,
    "result": "PASS_ON_PINNED_CI",
    "released_version_coverage_proven": False,
    "independent_human_qa": False,
}


def _third_ci() -> dict:
    """Pin public GitHub CI identity and exact baseline plus patched run steps."""
    base = f"https://api.github.com/repos/{REPO}/actions/runs/{THIRD_RUN}"
    run, payload = _public_json(base), _public_json(base + "/jobs?per_page=100")
    if (run.get("id") != THIRD_RUN
            or run.get("head_sha") != THIRD_SHA
            or run.get("repository", {}).get("full_name") != REPO
            or run.get("event") != "pull_request"
            or run.get("head_branch") != THIRD_BRANCH
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
            or payload.get("total_count") != 4
            or type(payload.get("jobs")) is not list
            or len(payload["jobs"]) != 4):
        raise PolicyError("third-rule CI identity not verified")
    by_name = {}
    for job in payload["jobs"]:
        if (type(job) is not dict or job.get("name") in by_name
                or job.get("run_id") != THIRD_RUN
                or job.get("status") != "completed"
                or job.get("conclusion") != "success"):
            raise PolicyError("third-rule CI job rejected")
        by_name[job["name"]] = job
    if set(by_name) != JOBS:
        raise PolicyError("third-rule CI matrix mismatch")
    for runner in ("windows-latest", "ubuntu-latest"):
        if not _step_ok(
                by_name[f"Offline test / {runner} / Python 3.15"],
                THIRD_BASELINE_STEP):
            raise PolicyError("missing third-rule baseline runtime probe")
    if not _step_ok(
            by_name["Offline test / ubuntu-latest / Python 3.15"],
            THIRD_STEP):
        raise PolicyError("missing third-rule patched binary execution")
    return dict(EXPECTED_THIRD_CI)


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
    # Rule-specific LIVE CI gates, independently of the standard main CI.
    second = _postfix_ci() if RULE_ORDER[1] in rule_ids else None
    if second is not None and second != EXPECTED_SECOND_CI:
        raise PolicyError("second rule CI proof differs from pinned result")
    third = _third_ci() if RULE_ORDER[2] in rule_ids else None
    if third is not None and third != EXPECTED_THIRD_CI:
        raise PolicyError("third rule CI proof differs from pinned result")

    signer = _private_key(Path(private_path))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    rules_bytes = canonical_json(rules)
    decisions_bytes = canonical_json(decisions)
    evidence_bytes = canonical_json({
        "main_ci": main, "second_ci": second, "third_ci": third})
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
            or set(evidence) != {"main_ci", "second_ci", "third_ci"}):
        raise PolicyError("unexpected per-rule CI proof")
    _check_evidence(evidence["main_ci"])
    expected_second = (EXPECTED_SECOND_CI if RULE_ORDER[1] in man["rule_ids"]
                       else None)
    expected_third = (EXPECTED_THIRD_CI if RULE_ORDER[2] in man["rule_ids"]
                      else None)
    if (evidence["second_ci"] != expected_second
            or evidence["third_ci"] != expected_third
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
