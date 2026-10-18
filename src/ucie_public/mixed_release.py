"""Explicit, versioned mixed Python/PowerShell public-only owner Rulepack.

This V2 format never alters existing V1 Serial 1/2/3 signatures. It permits
only four immutable UCIE-authored public rules, all requiring exact live QA
and separate interactive owner risk acceptance before a new serial >=4 can
be signed. Static receipts NEVER execute the supplied source. No automation.
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
    MODE, JOBS, REPO, WORKFLOW, _public_json, _step_ok, _check_evidence,
    _local_clean_sha, validate_live_automated_qa,
)
from .production_release import SCOPE, _parse_date
from .multi_owner_release import _postfix_ci, _archive, _decode
from .selected_release import (
    RELEASE_PROFILES, EXPECTED_SECOND_CI, EXPECTED_THIRD_CI, _third_ci,
)
from .rule_matcher import match_signed_static_rules

SCHEMA = "UCIE_PUBLIC_SELECTED_MIXED_OWNER_RELEASE_V2"
CONFIRM = "AUTHORIZE_UCIE_FOUR_RULE_PUBLIC_MANUAL_OWNER_RISK_RELEASE"
FOURTH_RUN = 39110134534
FOURTH_SHA = "a676a72c6a30710c6437c0dc635f97db1068a20d"
FOURTH_BRANCH = "core/fourth-rule-scandir-source-and-safe-regression-20261018"
SAFE_STEP = "Fourth rule safe scandir guarded runtime and inert AST positives and negatives"
SOURCE_STEP = "Fourth rule exact official release-versus-patch source proof (one-shot PR only)"
FOURTH_RISK = "I_ACCEPT_PYTHON_3_15_0_SCANDIR_FIX_ABSENT_AND_NO_NATIVE_CRASH_REPRODUCTION"
FOURTH_ID = "PY_SCANDIR_SHARED_ITERATOR_RACE"
FOURTH_RULE = {
    "rule_id": FOURTH_ID,
    "pattern": "Sharing raw os.scandir iterator between Python threads can race with next/close",
    "problem": "Official CPython v3.15.0 source lacks the protection added in approved main PR #153462",
    "safe_guidance": "Avoid sharing raw os.scandir between threads; use a single owned lock across next() and close().",
    "affected_observation": "Python v3.15.0 release source unpatched; 3.13/3.15 guarded mitigation tested; native crash not retested",
    "upstream": "https://github.com/python/cpython/pull/153462",
    "upstream_merge_sha": "999a046b24cff4ba0e72b574196721f66bd08237",
    "runtime_ci": "https://github.com/tmdrkdtn1-project/UCIE/actions/runs/39110134534",
    "scanner": "ucie_miner.static_concurrency.inspect_python_scandir_source",
    "automation": "NEVER_AUTO_APPLY",
    "risk": "UNFIXED_CPYTHON_SCANDIR_NATIVE_RACE",
    "approval": MODE,
}
FOURTH_DECISION = {
    "rule_id": FOURTH_ID,
    "upstream_merge_sha": FOURTH_RULE["upstream_merge_sha"],
    "unfixed_release": "v3.15.0",
    "unfixed_release_source_blob": "0b42b059541d351423bb604586058363f7d0f35f",
    "patched_main_merge_source_blob": "bec305a4042c49d23410bf0c55c976ed78fe3fc1",
    "runtime_evidence": FOURTH_RULE["runtime_ci"],
    "safe_guarded_runtime_and_ast_verified": True,
    "unsafe_native_race_retested": False,
    "independent_before_after_binary_verified": False,
    "fixed_released_version_coverage_proven": False,
    "owner_risk_accepted": True,
    "independent_human_qa": False,
    "legal_license_signoff": False,
    "auto_apply": False,
}
PROFILES = [*RELEASE_PROFILES, (FOURTH_RULE, FOURTH_DECISION, FOURTH_RISK)]
RULE_ORDER = tuple(rule["rule_id"] for rule, _, _ in PROFILES)
ELIGIBLE = {r["rule_id"]: (r, d, risk) for r, d, risk in PROFILES}
FOURTH_CI = {
    "schema": "UCIE_SCANDIR_FOURTH_RULE_CI_OWNER_CHECK_V1",
    "repository": REPO, "run_id": FOURTH_RUN, "head_sha": FOURTH_SHA,
    "source_diff_step": SOURCE_STEP, "guarded_runtime_step": SAFE_STEP,
    "source_release_version": "v3.15.0",
    "released_fix_coverage_proven": False,
    "raw_native_crash_retested": False, "independent_human_qa": False,
    "result": "SAFE_GUARD_AND_PINNED_SOURCE_PASS",
}
FIELDS = {
    "schema", "channel", "scope", "serial", "created_utc", "expires_utc",
    "owner_key_id", "source_commit_sha", "rule_count", "rule_ids",
    "rules_sha256", "decisions_sha256", "evidence_sha256",
    "owner_risk_accepted", "automated_qa_verified",
    "independent_human_qa_approved", "legal_license_signoff",
    "production_approved", "deploy_allowed", "auto_apply",
    "private_project_access",
}


def _fourth_ci() -> dict:
    """Live public CI check. Never trust a candidate's own status string."""
    url = f"https://api.github.com/repos/{REPO}/actions/runs/{FOURTH_RUN}"
    run = _public_json(url)
    jobs = _public_json(url + "/jobs?per_page=100")
    if (run.get("id") != FOURTH_RUN
            or run.get("head_sha") != FOURTH_SHA
            or run.get("repository", {}).get("full_name") != REPO
            or run.get("path", "").split("@")[0] != WORKFLOW
            or run.get("event") != "pull_request"
            or run.get("head_branch") != FOURTH_BRANCH
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
            or jobs.get("total_count") != 4
            or type(jobs.get("jobs")) is not list or len(jobs["jobs"]) != 4):
        raise PolicyError("fourth rule CI run is not exact source proof")
    by_name = {}
    for job in jobs["jobs"]:
        name = job.get("name") if isinstance(job, dict) else None
        if (type(name) is not str or name in by_name
                or job.get("run_id") != FOURTH_RUN
                or job.get("status") != "completed"
                or job.get("conclusion") != "success"):
            raise PolicyError("fourth rule matrix job incomplete")
        by_name[name] = job
    if set(by_name) != JOBS:
        raise PolicyError("fourth rule CI job set mismatch")
    if any(not _step_ok(job, SAFE_STEP) for job in by_name.values()):
        raise PolicyError("missing guarded Python runtime and AST evidence")
    if not _step_ok(
            by_name["Offline test / ubuntu-latest / Python 3.15"],
            SOURCE_STEP):
        raise PolicyError("missing exact tagged-release source comparison")
    return dict(FOURTH_CI)


def selected_payload(ids: object) -> tuple[list[dict], list[dict]]:
    if (type(ids) is not list or not 1 <= len(ids) <= 64
            or any(type(name) is not str for name in ids)
            or len(set(ids)) != len(ids)
            or ids != [name for name in RULE_ORDER if name in ids]
            or any(name not in ELIGIBLE for name in ids)):
        raise PolicyError("unapproved or duplicated mixed-rule selection")
    return (
        [dict(ELIGIBLE[name][0]) for name in ids],
        [dict(ELIGIBLE[name][1]) for name in ids],
    )


def publish_mixed_owner_release(
    root: Path, private_path: Path, output: Path, *,
    run_id: int, serial: int, rule_ids: list[str],
    confirmation: str, risk_acceptances: dict[str, str],
) -> Path:
    rules, decisions = selected_payload(rule_ids)
    if (confirmation != CONFIRM or type(risk_acceptances) is not dict
            or set(risk_acceptances) != set(rule_ids)
            or any(risk_acceptances[name] != ELIGIBLE[name][2]
                   for name in rule_ids)):
        raise PolicyError("explicit per-rule owner risk acceptance required")
    if type(serial) is not int or not 4 <= serial <= 10000000:
        raise PolicyError("mixed release requires Serial 4 or later")
    root = Path(root)
    current_sha = _local_clean_sha(root)
    main_ci = validate_live_automated_qa(run_id)
    if main_ci["head_sha"] != current_sha:
        raise PolicyError("owner checkout differs from complete live main CI")
    second = _postfix_ci() if RULE_ORDER[1] in rule_ids else None
    third = _third_ci() if RULE_ORDER[2] in rule_ids else None
    fourth = _fourth_ci() if FOURTH_ID in rule_ids else None
    if ((second is not None and second != EXPECTED_SECOND_CI)
            or (third is not None and third != EXPECTED_THIRD_CI)
            or (fourth is not None and fourth != FOURTH_CI)):
        raise PolicyError("per-rule CI evidence differs from exact pinned proof")
    signer = _private_key(Path(private_path))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    rb = canonical_json(rules)
    db = canonical_json(decisions)
    eb = canonical_json({
        "main_ci": main_ci, "second_ci": second,
        "third_ci": third, "fourth_ci": fourth,
    })
    manifest = {
        "schema": SCHEMA, "channel": MODE, "scope": SCOPE, "serial": serial,
        "rule_count": len(rule_ids), "rule_ids": list(rule_ids),
        "created_utc": now.isoformat().replace("+00:00", "Z"),
        "expires_utc": (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "owner_key_id": key_id(signer.public_key()),
        "source_commit_sha": current_sha,
        "rules_sha256": digest(rb), "decisions_sha256": digest(db),
        "evidence_sha256": digest(eb),
        "owner_risk_accepted": True, "automated_qa_verified": True,
        "independent_human_qa_approved": False, "legal_license_signoff": False,
        "production_approved": True, "deploy_allowed": True,
        "auto_apply": False, "private_project_access": False,
    }
    mb = canonical_json(manifest)
    dest = _valid_outpath(root, Path(output))
    fd, temp = tempfile.mkstemp(dir=str(dest.parent), prefix=".ucie_mixed_", suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as handle:
            with zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as out:
                out.writestr("manifest.json", mb)
                out.writestr("rules/prevention.json", rb)
                out.writestr("evidence/automated_ci.json", eb)
                out.writestr("evidence/rule_decisions.json", db)
                out.writestr("signatures/owner.sig", signer.sign(mb))
        os.link(temp, dest)  # no overwrite of Serial 3 or other artifacts
    finally:
        Path(temp).unlink(missing_ok=True)
    return dest


def verify_mixed_owner_release(
    pack: Path, trust: Path, *, min_serial: int = 4,
    at_time: datetime | None = None,
) -> dict:
    if type(min_serial) is not int or not 4 <= min_serial <= 10000000:
        raise PolicyError("invalid mixed rulepack minimum serial")
    blobs = _archive(Path(pack))
    pub = _public_key(Path(trust))
    man = _decode(blobs["manifest.json"])
    rules = _decode(blobs["rules/prevention.json"])
    decisions = _decode(blobs["evidence/rule_decisions.json"])
    evidence = _decode(blobs["evidence/automated_ci.json"])
    if (type(man) is not dict or set(man) != FIELDS
            or man["schema"] != SCHEMA or man["channel"] != MODE
            or man["scope"] != SCOPE or man["owner_key_id"] != key_id(pub)
            or type(man["serial"]) is not int or man["serial"] < min_serial
            or type(man["rule_ids"]) is not list
            or type(man["rule_count"]) is not int
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
        raise PolicyError("unapproved or altered mixed-rule manifest")
    expected_rules, expected_decisions = selected_payload(man["rule_ids"])
    if rules != expected_rules or decisions != expected_decisions:
        raise PolicyError("unrecognized public rule or changed consent evidence")
    if type(evidence) is not dict or set(evidence) != {
            "main_ci", "second_ci", "third_ci", "fourth_ci"}:
        raise PolicyError("mixed CI evidence schema mismatch")
    _check_evidence(evidence["main_ci"])
    for code, field, expected in (
        (RULE_ORDER[1], "second_ci", EXPECTED_SECOND_CI),
        (RULE_ORDER[2], "third_ci", EXPECTED_THIRD_CI),
        (FOURTH_ID, "fourth_ci", FOURTH_CI),
    ):
        if evidence[field] != (expected if code in man["rule_ids"] else None):
            raise PolicyError("per-rule approval evidence mismatch")
    if evidence["main_ci"]["head_sha"] != man["source_commit_sha"]:
        raise PolicyError("main CI commit does not match signed source")
    try:
        pub.verify(blobs["signatures/owner.sig"], blobs["manifest.json"])
    except (InvalidSignature, ValueError) as exc:
        raise PolicyError("mixed Rulepack owner signature invalid") from exc
    now = at_time or datetime.now(timezone.utc)
    created = _parse_date(man["created_utc"])
    expiry = _parse_date(man["expires_utc"])
    if (now.tzinfo is None or created > now + timedelta(minutes=5)
            or now >= expiry or expiry <= created
            or expiry - created > timedelta(days=7)):
        raise PolicyError("mixed Rulepack outside signed expiry")
    return {
        "result": "MIXED_OWNER_PUBLIC_MANUAL_PACK_VERIFIED",
        "serial": man["serial"], "rule_count": len(rules),
        "rule_ids": list(man["rule_ids"]),
        "owner_signature": "VALID", "scope": SCOPE, "approval_mode": MODE,
        "source_commit_sha": man["source_commit_sha"],
        "fixed_python_3_15_0_coverage_proven": False,
        "unsafe_native_race_retested": False,
        "independent_human_qa_approved": False,
        "legal_license_signoff": False,
        "auto_apply": False,
        "production_approved": True, "deploy_allowed": True,
    }


def scan_mixed_owner_receipt(
    pack: Path, trust: Path, receipt: object, *, min_serial: int = 4,
) -> dict:
    verified = verify_mixed_owner_release(pack, trust, min_serial=min_serial)
    rules, _ = selected_payload(verified["rule_ids"])
    findings = match_signed_static_rules(
        receipt, rules, expected_approval=MODE, allow_python=True)
    return {
        "schema": "UCIE_MIXED_PUBLIC_MANUAL_STATIC_SCAN_V2",
        "status": "CANDIDATES_FOR_MANUAL_REVIEW" if findings
                  else "NO_SIGNED_RULE_MATCH",
        "rule_ids": verified["rule_ids"],
        "rule_count": verified["rule_count"],
        "owner_signature": "VALID",
        "pack_serial": verified["serial"],
        "source_sha256": receipt["source_sha256"],
        "finding_count": len(findings), "findings": findings,
        "scope": SCOPE, "source_authentication_verified": False,
        "source_executed": False, "source_files_read": 0,
        "unsafe_native_race_retested": False,
        "auto_fix_applied": False, "auto_apply": False,
        "persistent_writes": 0,
    }
