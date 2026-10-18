"""Stage4 owner-risk-accepted public-only release using VERIFIED GitHub CI.

This is NOT independent human QA. Owner accepts that limitation explicitly.
Publisher confirms four actual GitHub Actions jobs on the EXACT local clean
commit, plus the required per-job steps, using anonymous public API reads.
No project/source ingestion, auto-fix, unattended signing, or private access.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature

from .policy import PolicyError
from .prevention_rulepack import RULE
from .production_release import _parse_date, SCOPE
from .rulepack import (canonical_json, digest, key_id, _private_key,
                       _public_key, _valid_outpath)

SCHEMA = "UCIE_PUBLIC_OWNER_RISK_ACCEPTED_RELEASE_V1"
MODE = "AUTOMATED_QA_OWNER_RISK_ACCEPTED"
CONFIRM = "AUTHORIZE_UCIE_PUBLIC_MANUAL_OWNER_RISK_RELEASE"
RISK = "I_ACCEPT_NO_INDEPENDENT_HUMAN_QA_AND_NO_LEGAL_LICENSE_SIGNOFF"
REPO = "tmdrkdtn1-project/UCIE"
WORKFLOW = ".github/workflows/stage1-offline-tests.yml"
RELEASE_RULE = {**RULE, "approval": MODE}
RULE_BYTES = canonical_json([RELEASE_RULE])
FILES = frozenset({
    "manifest.json", "rules/prevention.json",
    "evidence/automated_ci.json", "signatures/owner.sig",
})
MAX_BYTES = 131072
HEX40 = re.compile(r"[0-9a-f]{40}")
JOBS = frozenset({
    f"Offline test / {os_name} / Python {ver}"
    for os_name in ("ubuntu-latest", "windows-latest")
    for ver in ("3.13", "3.15")
})
STEP_RUNTIME = "First rule real CPython 3.15 -X runtime regression (ephemeral runner only)"
STEP_STAGE4 = "Stage4 QA plus owner signed production consumer (synthetic only)"
STEP_PS51 = "Signed review consumer on Windows PowerShell 5.1 (ephemeral synthetic)"
EVIDENCE_FIELDS = frozenset({
    "schema", "repository", "workflow", "run_id", "run_url",
    "head_sha", "event", "branch", "conclusion", "job_names",
    "runtime_platforms", "windows_ps51_verified", "stage4_synthetic_verified",
    "independent_human_qa", "legal_license_signoff", "evidence_kind",
})


def _public_json(url: str) -> dict:
    # Caller cannot select hosts or paths: all URLs are constructed below.
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "UCIE-public-stage4-owner-risk-gate",
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.geturl() != url or resp.status != 200:
                raise PolicyError("GitHub API redirect or wrong status")
            raw = resp.read(1048577)
            if len(raw) > 1048576:
                raise PolicyError("GitHub QA evidence oversized")
    except (OSError, TimeoutError, ValueError) as exc:
        raise PolicyError("GitHub QA evidence unavailable") from exc
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise PolicyError("invalid GitHub QA metadata") from exc
    if not isinstance(obj, dict):
        raise PolicyError("unexpected GitHub QA metadata")
    return obj


def _step_ok(job: dict, step_name: str) -> bool:
    return sum(1 for step in job.get("steps", [])
               if isinstance(step, dict) and step.get("name") == step_name
               and step.get("status") == "completed"
               and step.get("conclusion") == "success") == 1


def validate_live_automated_qa(run_id: int) -> dict:
    """Fetch exactly two fixed public GitHub API endpoints; NO caller JSON."""
    if type(run_id) is not int or not 1 <= run_id <= 999999999999:
        raise PolicyError("invalid CI run ID")
    base = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}"
    run = _public_json(base)
    jobs = _public_json(base + "/jobs?per_page=100")
    sha = run.get("head_sha")
    if (run.get("id") != run_id
            or run.get("repository", {}).get("full_name") != REPO
            or run.get("path", "").split("@")[0] != WORKFLOW
            or run.get("event") != "push"
            or run.get("head_branch") != "main"
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
            or not isinstance(sha, str) or not HEX40.fullmatch(sha)
            or jobs.get("total_count") != 4
            or not isinstance(jobs.get("jobs"), list)
            or len(jobs["jobs"]) != 4):
        raise PolicyError("CI is not a completed passing main push of UCIE")
    by_name = {}
    for job in jobs["jobs"]:
        if (not isinstance(job, dict) or not isinstance(job.get("name"), str)
                or job["name"] in by_name or job.get("status") != "completed"
                or job.get("conclusion") != "success"
                or job.get("run_id") != run_id):
            raise PolicyError("incomplete, duplicate or failed matrix job")
        by_name[job["name"]] = job
    if frozenset(by_name) != JOBS:
        raise PolicyError("unexpected CI matrix scope")
    for os_name in ("ubuntu-latest", "windows-latest"):
        if not _step_ok(by_name[f"Offline test / {os_name} / Python 3.15"], STEP_RUNTIME):
            raise PolicyError("missing actual CPython 3.15 behavior check")
    for version in ("3.13", "3.15"):
        job = by_name[f"Offline test / windows-latest / Python {version}"]
        if not _step_ok(job, STEP_PS51) or not _step_ok(job, STEP_STAGE4):
            raise PolicyError("missing signed-pack consumer or PS5.1 regression")
    return {
        "schema": "UCIE_OWNER_RELEASE_AUTOMATED_QA_EVIDENCE_V1",
        "repository": REPO, "workflow": WORKFLOW,
        "run_id": run_id,
        "run_url": f"https://github.com/{REPO}/actions/runs/{run_id}",
        "head_sha": sha, "event": "push", "branch": "main",
        "conclusion": "success", "job_names": sorted(JOBS),
        "runtime_platforms": ["ubuntu-latest", "windows-latest"],
        "windows_ps51_verified": True, "stage4_synthetic_verified": True,
        "independent_human_qa": False, "legal_license_signoff": False,
        "evidence_kind": "LIVE_PUBLIC_GITHUB_ACTIONS_CHECKED_AT_SIGNING",
    }


def _local_clean_sha(root: Path) -> str:
    if (root.is_symlink() or not root.is_dir()
            or not (root / ".git").exists()):
        raise PolicyError("missing UCIE Git worktree")
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=8, check=True,
        )
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True, text=True, timeout=8, check=True,
        )
        branch = subprocess.run(
            ["git", "-C", str(root), "branch", "--show-current"],
            capture_output=True, text=True, timeout=8, check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise PolicyError("unable to attest clean UCIE worktree") from exc
    sha = head.stdout.strip()
    if (not HEX40.fullmatch(sha) or status.stdout.strip()
            or branch.stdout.strip() != "main"):
        raise PolicyError("owner release requires clean main and exact commit")
    return sha


def _check_evidence(ev: object) -> None:
    if (not isinstance(ev, dict) or set(ev) != EVIDENCE_FIELDS
            or ev.get("schema") != "UCIE_OWNER_RELEASE_AUTOMATED_QA_EVIDENCE_V1"
            or ev.get("repository") != REPO or ev.get("workflow") != WORKFLOW
            or type(ev.get("run_id")) is not int or ev["run_id"] < 1
            or ev.get("run_url") !=
               f"https://github.com/{REPO}/actions/runs/{ev['run_id']}"
            or not isinstance(ev.get("head_sha"), str)
            or not HEX40.fullmatch(ev["head_sha"])
            or ev.get("event") != "push" or ev.get("branch") != "main"
            or ev.get("conclusion") != "success"
            or ev.get("job_names") != sorted(JOBS)
            or ev.get("runtime_platforms") != ["ubuntu-latest", "windows-latest"]
            or ev.get("windows_ps51_verified") is not True
            or ev.get("stage4_synthetic_verified") is not True
            or ev.get("independent_human_qa") is not False
            or ev.get("legal_license_signoff") is not False
            or ev.get("evidence_kind") !=
               "LIVE_PUBLIC_GITHUB_ACTIONS_CHECKED_AT_SIGNING"):
        raise PolicyError("invalid or overclaimed CI evidence")


def publish_owner_risk_release(
    root: Path, owner_private: Path, output: Path, *,
    run_id: int, serial: int, confirmation: str, risk_acceptance: str,
) -> Path:
    """Explicit owner action; signing is NEVER triggered by the miner/CI."""
    if confirmation != CONFIRM or risk_acceptance != RISK:
        raise PolicyError("missing separate explicit owner risk acceptance")
    if type(serial) is not int or not 1 <= serial <= 10000000:
        raise PolicyError("invalid owner release serial")
    root = Path(root)
    sha = _local_clean_sha(root)
    evidence = validate_live_automated_qa(run_id)
    if evidence["head_sha"] != sha:
        raise PolicyError("CI does not cover exact owner release checkout")
    owner = _private_key(Path(owner_private))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    ev_bytes = canonical_json(evidence)
    manifest = {
        "schema": SCHEMA, "channel": MODE, "scope": SCOPE,
        "serial": serial,
        "created_utc": now.isoformat().replace("+00:00", "Z"),
        "expires_utc": (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "owner_key_id": key_id(owner.public_key()),
        "rule_sha256": digest(RULE_BYTES),
        "ci_evidence_sha256": digest(ev_bytes),
        "source_commit_sha": sha, "rule_count": 1,
        "owner_risk_accepted": True, "automated_qa_verified": True,
        "independent_human_qa_approved": False,
        "legal_license_signoff": False,
        "production_approved": True, "deploy_allowed": True,
        "auto_apply": False, "private_project_access": False,
    }
    man_bytes = canonical_json(manifest)
    sig = owner.sign(man_bytes)
    target = _valid_outpath(root, Path(output))
    fd, staging = tempfile.mkstemp(
        dir=str(target.parent), prefix=".ucie_owner_risk_", suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as handle:
            with zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("manifest.json", man_bytes)
                z.writestr("rules/prevention.json", RULE_BYTES)
                z.writestr("evidence/automated_ci.json", ev_bytes)
                z.writestr("signatures/owner.sig", sig)
        os.link(staging, target)
    finally:
        Path(staging).unlink(missing_ok=True)
    return target


def verify_owner_risk_release(pack: Path, owner_trust: Path, *,
                              min_serial: int = 1,
                              at_time: datetime | None = None) -> dict:
    """Offline receiver: authenticated OWNER claim about live CI check.

    Recipient does NOT independently query GitHub; caller should understand
    that automated QA details are attested by the OWNER signature, not by
    GitHub cryptographic attestations or an independent human reviewer.
    """
    if type(min_serial) is not int or min_serial < 1:
        raise PolicyError("invalid minimum serial")
    pack = Path(pack)
    if pack.is_symlink() or not pack.is_file() or pack.stat().st_size > MAX_BYTES:
        raise PolicyError("invalid owner risk release archive")
    owner = _public_key(Path(owner_trust))
    try:
        with zipfile.ZipFile(pack, "r") as z:
            info = z.infolist()
            names = [i.filename for i in info]
            if (len(names) != len(FILES) or set(names) != FILES
                    or any(i.file_size > MAX_BYTES or i.flag_bits & 1
                           or ((i.external_attr >> 16) & 0o170000) == 0o120000
                           for i in info)):
                raise PolicyError("unsafe or unexpected owner release archive")
            blobs = {n: z.read(n) for n in names}
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise PolicyError("invalid owner release archive") from exc
    try:
        man = json.loads(blobs["manifest.json"].decode("utf-8"))
        rule = json.loads(blobs["rules/prevention.json"].decode("utf-8"))
        evidence = json.loads(blobs["evidence/automated_ci.json"].decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise PolicyError("invalid owner risk release data") from exc
    fields = {
        "schema", "channel", "scope", "serial", "created_utc",
        "expires_utc", "owner_key_id", "rule_sha256", "ci_evidence_sha256",
        "source_commit_sha", "rule_count", "owner_risk_accepted",
        "automated_qa_verified", "independent_human_qa_approved",
        "legal_license_signoff", "production_approved", "deploy_allowed",
        "auto_apply", "private_project_access",
    }
    if (not isinstance(man, dict) or set(man) != fields
            or canonical_json(man) != blobs["manifest.json"]
            or man["schema"] != SCHEMA or man["channel"] != MODE
            or man["scope"] != SCOPE or man["owner_key_id"] != key_id(owner)
            or type(man["serial"]) is not int or man["serial"] < min_serial
            or man["rule_count"] != 1
            or man["owner_risk_accepted"] is not True
            or man["automated_qa_verified"] is not True
            or man["independent_human_qa_approved"] is not False
            or man["legal_license_signoff"] is not False
            or man["production_approved"] is not True
            or man["deploy_allowed"] is not True
            or man["auto_apply"] is not False
            or man["private_project_access"] is not False
            or rule != [RELEASE_RULE]
            or canonical_json(rule) != blobs["rules/prevention.json"]
            or man["rule_sha256"] != digest(blobs["rules/prevention.json"])
            or man["ci_evidence_sha256"] != digest(blobs["evidence/automated_ci.json"])):
        raise PolicyError("invalid owner approval, scope or signed data")
    _check_evidence(evidence)
    if (canonical_json(evidence) != blobs["evidence/automated_ci.json"]
            or evidence["head_sha"] != man["source_commit_sha"]):
        raise PolicyError("CI evidence source commit mismatch")
    try:
        owner.verify(blobs["signatures/owner.sig"], blobs["manifest.json"])
    except (InvalidSignature, ValueError) as exc:
        raise PolicyError("invalid owner release signature") from exc
    now = at_time or datetime.now(timezone.utc)
    created, expiry = _parse_date(man["created_utc"]), _parse_date(man["expires_utc"])
    if (now.tzinfo is None or created > now + timedelta(minutes=5)
            or now >= expiry or expiry <= created
            or expiry - created > timedelta(days=7)):
        raise PolicyError("owner-risk release expired/not yet valid")
    return {
        "result": "OWNER_RISK_ACCEPTED_PUBLIC_RULEPACK_VERIFIED",
        "rule_id": RULE["rule_id"], "serial": man["serial"],
        "owner_signature": "VALID", "approval_mode": MODE,
        "automated_qa_claim": "OWNER_SIGNED_LIVE_GITHUB_CI_CHECK",
        "ci_run_url": evidence["run_url"], "source_commit_sha": evidence["head_sha"],
        "independent_human_qa_approved": False,
        "legal_license_signoff": False,
        "owner_risk_accepted": True, "production_approved": True,
        "deploy_allowed": True, "auto_apply": False,
        "safe_guidance": RELEASE_RULE["safe_guidance"],
        "scope": SCOPE,
    }
