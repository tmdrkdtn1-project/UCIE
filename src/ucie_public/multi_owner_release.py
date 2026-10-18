"""Two-rule owner-risk production contract. No unattended release or scan.

This is a new, opt-in V1 envelope; the first-rule owner release V1 stays
unchanged. Both rules are fixed UCIE-authored metadata. Public CI metadata
is checked live during an EXPLICIT owner signing action, not by a scheduler.
The owner expressly accepts: no independent human QA, no legal license
signoff, and second rule applicability limited to observed runtimes. None of
these checks independently prove a production PowerShell release contains the
fix. Never auto-apply or inspect files/projects.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import zipfile

from cryptography.exceptions import InvalidSignature

from .policy import PolicyError
from .multi_review import FIRST, SECOND
from .owner_release import (
    MODE, RISK, JOBS, REPO, _public_json, _step_ok, _check_evidence,
    _local_clean_sha, validate_live_automated_qa,
)
from .production_release import SCOPE, _parse_date
from .rulepack import canonical_json, digest, key_id, _private_key, _public_key, _valid_outpath

SCHEMA = "UCIE_PUBLIC_TWO_RULE_OWNER_RISK_RELEASE_V1"
CONFIRM = "AUTHORIZE_UCIE_TWO_RULE_PUBLIC_MANUAL_OWNER_RISK_RELEASE"
SECOND_RISK = "I_ACCEPT_POWERSHELL_7_6_6_ONLY_OBSERVED_AND_NO_VERIFIED_RELEASE_COVERAGE"
SECOND_RUN = 39101087404
SECOND_SHA = "0620cfc9ca8c337fe9a252b22ffa493705d94918"
SECOND_PR_BRANCH = "core/powershell-dotpath-postfix-evidence-20261018"
POSTFIX_STEP = "Verify upstream patched Resolve-Path behavior in disposable CI (single PR trial)"
RULE_IDS = (FIRST["rule_id"], SECOND["rule_id"])
RELEASE_RULES = [
    {**FIRST, "approval": MODE},
    {**SECOND, "approval": MODE},
]
RULE_BYTES = canonical_json(RELEASE_RULES)
FILES = frozenset({
    "manifest.json", "rules/prevention.json", "evidence/automated_ci.json",
    "evidence/rule_decisions.json", "signatures/owner.sig",
})
MAX_BYTES = 131072
DECISIONS = [
    {
        "rule_id": FIRST["rule_id"],
        "upstream_merge_sha": FIRST["upstream_merge_sha"],
        "observed_runtime": "CPython 3.15.0 Windows/Linux",
        "runtime_evidence": FIRST["runtime_ci"],
        "owner_risk_accepted": True,
        "independent_human_qa": False, "legal_license_signoff": False,
        "auto_apply": False,
    },
    {
        "rule_id": SECOND["rule_id"],
        "upstream_merge_sha": SECOND["upstream_merge_sha"],
        "observed_runtime": "PowerShell 7.6.6 Windows/Linux",
        "postfix_dev_build": "PowerShell 7.7.0-preview.6 development CI build",
        "runtime_evidence": SECOND["runtime_ci"],
        "fixed_dev_build_evidence": (
            "https://github.com/tmdrkdtn1-project/UCIE/actions/runs/39101087404"),
        "release_version_coverage_proven": False,
        "owner_risk_accepted": True,
        "independent_human_qa": False, "legal_license_signoff": False,
        "auto_apply": False,
    },
]
DECISION_BYTES = canonical_json(DECISIONS)


def _strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError("duplicate signed JSON key")
        result[key] = value
    return result


def _decode(blob: bytes):
    try:
        result = json.loads(blob.decode("utf-8"), object_pairs_hook=_strict_pairs)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise PolicyError("invalid release JSON") from exc
    if canonical_json(result) != blob:
        raise PolicyError("noncanonical signed JSON")
    return result


def _postfix_ci() -> dict:
    """Verify the one fixed, published CI run and exact patched-binary step."""
    base = f"https://api.github.com/repos/{REPO}/actions/runs/{SECOND_RUN}"
    run, jobs = _public_json(base), _public_json(base + "/jobs?per_page=100")
    if (run.get("id") != SECOND_RUN or run.get("head_sha") != SECOND_SHA
            or run.get("repository", {}).get("full_name") != REPO
            or run.get("event") != "pull_request"
            or run.get("head_branch") != SECOND_PR_BRANCH
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
            or jobs.get("total_count") != 4
            or type(jobs.get("jobs")) is not list
            or len(jobs["jobs"]) != 4):
        raise PolicyError("pinned second-rule CI run not verified")
    by_name = {}
    for job in jobs["jobs"]:
        if (type(job) is not dict or job.get("name") in by_name
                or job.get("run_id") != SECOND_RUN
                or job.get("status") != "completed"
                or job.get("conclusion") != "success"):
            raise PolicyError("invalid second-rule CI job")
        by_name[job["name"]] = job
    if (set(by_name) != JOBS
            or not _step_ok(by_name["Offline test / ubuntu-latest / Python 3.15"],
                            POSTFIX_STEP)):
        raise PolicyError("patched development build execution missing")
    return {
        "schema": "UCIE_SECOND_RULE_CI_OWNER_CHECK_V1",
        "repository": REPO, "run_id": SECOND_RUN, "head_sha": SECOND_SHA,
        "patch_ci_step": POSTFIX_STEP, "result": "PASS_ON_PINNED_CI",
        "release_version_coverage_proven": False,
        "independent_human_qa": False,
    }


def _archive(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise PolicyError("unsafe owner release file")
    try:
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            if (len(infos) != len(FILES) or {i.filename for i in infos} != FILES
                    or any(i.file_size > MAX_BYTES or i.flag_bits & 1
                           or ((i.external_attr >> 16) & 0o170000) == 0o120000
                           for i in infos)):
                raise PolicyError("unsafe two-rule archive")
            return {i.filename: z.read(i.filename) for i in infos}
    except (OSError, RuntimeError, zipfile.BadZipFile, EOFError) as exc:
        raise PolicyError("invalid two-rule archive") from exc


def publish_two_rule_owner_release(
    root: Path, private_path: Path, output: Path, *,
    run_id: int, serial: int, confirmation: str,
    risk_acceptance: str, second_risk_acceptance: str,
) -> Path:
    """Never called by CI. Requires both separate explicit owner decisions."""
    if (confirmation != CONFIRM or risk_acceptance != RISK
            or second_risk_acceptance != SECOND_RISK):
        raise PolicyError("missing explicit two-rule risk acceptance")
    if type(serial) is not int or not 1 <= serial <= 10000000:
        raise PolicyError("invalid serial")
    root = Path(root)
    sha = _local_clean_sha(root)
    main_ci = validate_live_automated_qa(run_id)
    if main_ci["head_sha"] != sha:
        raise PolicyError("main CI SHA does not match clean owner checkout")
    secondary = _postfix_ci()
    key = _private_key(Path(private_path))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    evidence = {"main_ci": main_ci, "second_ci": secondary}
    ev_bytes = canonical_json(evidence)
    manifest = {
        "schema": SCHEMA, "channel": MODE, "scope": SCOPE,
        "serial": serial,
        "created_utc": now.isoformat().replace("+00:00", "Z"),
        "expires_utc": (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "owner_key_id": key_id(key.public_key()),
        "rule_count": 2, "rule_sha256": digest(RULE_BYTES),
        "evidence_sha256": digest(ev_bytes),
        "decisions_sha256": digest(DECISION_BYTES),
        "source_commit_sha": sha,
        "owner_risk_accepted": True, "second_rule_risk_accepted": True,
        "automated_qa_verified": True,
        "independent_human_qa_approved": False, "legal_license_signoff": False,
        "production_approved": True, "deploy_allowed": True,
        "auto_apply": False, "private_project_access": False,
    }
    man_bytes = canonical_json(manifest)
    target = _valid_outpath(root, Path(output))
    fd, staging = tempfile.mkstemp(
        dir=str(target.parent), prefix=".ucie_two_rule_owner_", suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as dest:
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("manifest.json", man_bytes)
                z.writestr("rules/prevention.json", RULE_BYTES)
                z.writestr("evidence/automated_ci.json", ev_bytes)
                z.writestr("evidence/rule_decisions.json", DECISION_BYTES)
                z.writestr("signatures/owner.sig", key.sign(man_bytes))
        os.link(staging, target)
    finally:
        Path(staging).unlink(missing_ok=True)
    return target


def verify_two_rule_owner_release(
    pack: Path, owner_trust: Path, *, min_serial: int = 1,
    at_time: datetime | None = None,
) -> dict:
    if type(min_serial) is not int or not 1 <= min_serial <= 10000000:
        raise PolicyError("invalid minimum serial")
    blobs = _archive(Path(pack))
    owner = _public_key(Path(owner_trust))
    man = _decode(blobs["manifest.json"])
    rule = _decode(blobs["rules/prevention.json"])
    evidence = _decode(blobs["evidence/automated_ci.json"])
    decisions = _decode(blobs["evidence/rule_decisions.json"])
    fields = {
        "schema", "channel", "scope", "serial", "created_utc", "expires_utc",
        "owner_key_id", "rule_count", "rule_sha256", "evidence_sha256",
        "decisions_sha256", "source_commit_sha", "owner_risk_accepted",
        "second_rule_risk_accepted", "automated_qa_verified",
        "independent_human_qa_approved", "legal_license_signoff",
        "production_approved", "deploy_allowed", "auto_apply",
        "private_project_access",
    }
    if (type(man) is not dict or set(man) != fields
            or man["schema"] != SCHEMA or man["channel"] != MODE
            or man["scope"] != SCOPE or man["owner_key_id"] != key_id(owner)
            or type(man["serial"]) is not int or man["serial"] < min_serial
            or man["rule_count"] != 2
            or rule != RELEASE_RULES or canonical_json(rule) != RULE_BYTES
            or decisions != DECISIONS or canonical_json(decisions) != DECISION_BYTES
            or man["rule_sha256"] != digest(blobs["rules/prevention.json"])
            or man["evidence_sha256"] != digest(blobs["evidence/automated_ci.json"])
            or man["decisions_sha256"] != digest(blobs["evidence/rule_decisions.json"])
            or man["owner_risk_accepted"] is not True
            or man["second_rule_risk_accepted"] is not True
            or man["automated_qa_verified"] is not True
            or man["independent_human_qa_approved"] is not False
            or man["legal_license_signoff"] is not False
            or man["production_approved"] is not True
            or man["deploy_allowed"] is not True
            or man["auto_apply"] is not False
            or man["private_project_access"] is not False):
        raise PolicyError("invalid second-rule owner risk approval or signed scope")
    if type(evidence) is not dict or set(evidence) != {"main_ci", "second_ci"}:
        raise PolicyError("incorrect rule CI evidence")
    _check_evidence(evidence["main_ci"])
    expected_second = {
        "schema": "UCIE_SECOND_RULE_CI_OWNER_CHECK_V1",
        "repository": REPO, "run_id": SECOND_RUN, "head_sha": SECOND_SHA,
        "patch_ci_step": POSTFIX_STEP, "result": "PASS_ON_PINNED_CI",
        "release_version_coverage_proven": False,
        "independent_human_qa": False,
    }
    if (evidence["second_ci"] != expected_second
            or evidence["main_ci"]["head_sha"] != man["source_commit_sha"]):
        raise PolicyError("CI SHA or second-rule attestation mismatch")
    try:
        owner.verify(blobs["signatures/owner.sig"], blobs["manifest.json"])
    except (InvalidSignature, ValueError) as exc:
        raise PolicyError("owner signature mismatch") from exc
    now = at_time or datetime.now(timezone.utc)
    created = _parse_date(man["created_utc"])
    expires = _parse_date(man["expires_utc"])
    if (now.tzinfo is None or created > now + timedelta(minutes=5)
            or now >= expires or expires <= created
            or expires - created > timedelta(days=7)):
        raise PolicyError("expired/not-yet-valid two-rule owner release")
    return {
        "result": "OWNER_RISK_TWO_RULE_PUBLIC_PACK_VERIFIED",
        "rule_ids": list(RULE_IDS), "rule_count": 2,
        "serial": man["serial"], "owner_signature": "VALID",
        "approval_mode": MODE, "scope": SCOPE,
        "source_commit_sha": man["source_commit_sha"],
        "automated_qa_claim": "OWNER_SIGNED_LIVE_GITHUB_CI_CHECK",
        "second_ci_run": SECOND_RUN,
        "release_version_coverage_proven": False,
        "independent_human_qa_approved": False,
        "legal_license_signoff": False,
        "owner_risk_accepted": True, "production_approved": True,
        "deploy_allowed": True, "auto_apply": False,
    }


def scan_two_rule_owner_receipt(
    pack: Path, owner_trust: Path, scan: object, *, min_serial: int = 1,
) -> dict:
    """Filter a bounded inert AST receipt against exactly two owner-signed rules.

    Source text is never accepted/executed here. Receipts do NOT prove
    provenance; actual manual scan caller must create one from explicit input.
    """
    signed = verify_two_rule_owner_release(
        pack, owner_trust, min_serial=min_serial)
    from ucie_miner.static_rule_bridge import _check_receipt, SCANNER_GUIDANCE
    from ucie_miner.patterns import PatternError

    try:
        language = _check_receipt(scan)
    except (PatternError, TypeError, ValueError) as exc:
        raise PolicyError("untrusted or malformed scanner receipt") from exc
    if language != "powershell":
        raise PolicyError("manual two-rule receiver requires PowerShell AST")
    allowed = {r["rule_id"]: r for r in RELEASE_RULES}
    findings = []
    for item in scan["findings"]:
        rule = allowed.get(item["pattern_code"])
        if rule is None:
            continue
        if (item["public_evidence"] != rule["upstream"]
                or item["safe_fix_guidance"] != SCANNER_GUIDANCE[rule["rule_id"]]):
            raise PolicyError("finding and owner-approved rule identity mismatch")
        findings.append({
            "rule_id": rule["rule_id"],
            "line": item["line"], "column": item["column"],
            "public_evidence": rule["upstream"],
            "safe_guidance": rule["safe_guidance"],
            "manual_review_required": True,
            "runtime_bug_confirmed_for_this_input": False,
        })
    return {
        "schema": "UCIE_TWO_RULE_OWNER_PUBLIC_MANUAL_SCAN_V1",
        "status": ("PUBLIC_PREVENTION_CANDIDATES_FOR_MANUAL_REVIEW"
                   if findings else "NO_SIGNED_RULE_MATCH_IN_SUPPLIED_INPUT"),
        "rule_ids": list(RULE_IDS), "rule_count": 2,
        "pack_serial": signed["serial"], "owner_signature": "VALID",
        "source_sha256": scan["source_sha256"],
        "source_authentication_verified": False,
        "finding_count": len(findings), "findings": findings,
        "scope": SCOPE, "approval_mode": MODE,
        "independent_human_qa_approved": False,
        "legal_license_signoff": False,
        "release_version_coverage_proven": False,
        "source_executed": False, "source_files_read": 0,
        "auto_fix_applied": False, "auto_apply": False,
        "production_approved": True, "deploy_allowed": True,
        "persistent_writes": 0,
    }
