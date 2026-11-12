"""Bounded PUBLIC_ONLY Stage 12 candidate safe-regression evidence verifier.

Only four UCIE-authored, already known safe test recipes exist. An upstream
PR or Stage12 metadata is NEVER a trusted executable test. Future unrecognized
candidates require a separately reviewed and committed safe test recipe.
Reads current Stage12 ledgers and exact public GitHub Actions evidence only.
No signing, network-controlled instructions, candidate promotion, DB writes,
private sources, new scheduler or automatic deployment.
"""
from __future__ import annotations

from pathlib import Path

from ucie_public.owner_release import (
    JOBS, REPO, _public_json, _step_ok, validate_live_automated_qa,
)
from ucie_public.multi_owner_release import _postfix_ci
from ucie_public.selected_release import (
    _third_ci, EXPECTED_SECOND_CI, EXPECTED_THIRD_CI,
)
from ucie_public.mixed_release import (
    PROFILES, FOURTH_CI, _fourth_ci,
)
from ucie_public.policy import PolicyError
from .verification_handoff import (
    PINNED_RULES, _checked_handoff, prepare_verification_handoff,
)

SCHEMA = "UCIE_PUBLIC_SAFE_CANDIDATE_QA_V1"
# Each step below executes UCIE-owned synthetic inputs only. No arbitrary
# candidate-provided file path, shell command, Python module or URL.
SAFE_STEPS = {
    "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO":
        ("First rule real CPython 3.15 -X runtime regression (ephemeral runner only)",
         ("Offline test / ubuntu-latest / Python 3.15",
          "Offline test / windows-latest / Python 3.15")),
    "PS_RESOLVE_PATH_DOT_PREFIX":
        ("Second rule actual Resolve-Path dot-prefix behavior (disposable runner, no approval)",
         ("Offline test / ubuntu-latest / Python 3.15",
          "Offline test / windows-latest / Python 3.15")),
    "PS_FUZZY_GET_COMMAND_DUPLICATES":
        ("Third rule Get-Command fuzzy duplicates behavioral observation (disposable runner, no approval)",
         ("Offline test / ubuntu-latest / Python 3.15",
          "Offline test / windows-latest / Python 3.15")),
    "PY_SCANDIR_SHARED_ITERATOR_RACE":
        ("Fourth rule safe scandir guarded runtime and inert AST positives and negatives",
         tuple(sorted(JOBS))),
}
KNOWN = {rule["rule_id"]: rule for rule, _, _ in PROFILES}
if (set(KNOWN) != set(SAFE_STEPS) or len(KNOWN) != len(PROFILES)
        or any(
            sum(1 for (_, _, sha), rule_id in PINNED_RULES.items()
                if rule_id == code and sha == known["upstream_merge_sha"]) != 1
            for code, known in KNOWN.items()
        )):
    raise RuntimeError("safe candidate test recipe registry and signed rule identities differ")


def _checked_safe_steps(jobs: object, *, run_id: int) -> None:
    if (type(jobs) is not dict
            or jobs.get("total_count") != 4
            or type(jobs.get("jobs")) is not list
            or len(jobs["jobs"]) != 4):
        raise PolicyError("automated candidate QA missing full CI matrix")
    by_name = {}
    for job in jobs["jobs"]:
        if (type(job) is not dict or type(job.get("name")) is not str
                or job["name"] in by_name
                or job.get("run_id") != run_id
                or job.get("status") != "completed"
                or job.get("conclusion") != "success"):
            raise PolicyError("candidate QA matrix job identity mismatch")
        by_name[job["name"]] = job
    if set(by_name) != JOBS:
        raise PolicyError("candidate QA OS/runtime matrix scope mismatch")
    for step, names in SAFE_STEPS.values():
        for name in names:
            if not _step_ok(by_name[name], step):
                raise PolicyError("candidate QA executable safe test missing")


def assess_safe_candidate_qa(
        handoff: object, main_qa: object,
        matrix_jobs: object, pinned_ci: object) -> dict:
    """Pure assessment of checked evidence; NEVER accepts a new rule."""
    complete, tasks = _checked_handoff(handoff)
    # If no linked ledger, do not let a successful CI authorize an unknown
    # or staged-but-unlinked candidate.
    if not complete:
        return {
            "schema": SCHEMA, "status": "CANDIDATE_LEDGER_INCOMPLETE_NO_GO",
            "candidate_count": len(tasks), "safe_templates_observed": 0,
            "ambiguous_revisions": 0, "unknown_or_unmatched": len(tasks),
            "results": [], "new_rules_approved": 0, "auto_promoted": False,
            "owner_signed": False, "production_approved": False,
            "license_signoff": False, "unsafe_external_code_executed": False,
            "persistent_writes": 0,
        }
    if (type(main_qa) is not dict
            or main_qa.get("schema") !=
               "UCIE_OWNER_RELEASE_AUTOMATED_QA_EVIDENCE_V1"
            or main_qa.get("repository") != REPO
            or main_qa.get("event") != "push"
            or main_qa.get("branch") != "main"
            or main_qa.get("conclusion") != "success"
            or main_qa.get("independent_human_qa") is not False
            or main_qa.get("legal_license_signoff") is not False):
        raise PolicyError("live main automated QA evidence missing")
    _checked_safe_steps(matrix_jobs, run_id=main_qa["run_id"])
    if (type(pinned_ci) is not dict
            or set(pinned_ci) != set(SAFE_STEPS)):
        raise PolicyError("incomplete rule-specific CI pin set")
    for code in SAFE_STEPS:
        expected = (None if code == "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO"
                    else EXPECTED_SECOND_CI if code == "PS_RESOLVE_PATH_DOT_PREFIX"
                    else EXPECTED_THIRD_CI if code == "PS_FUZZY_GET_COMMAND_DUPLICATES"
                    else FOURTH_CI)
        if pinned_ci[code] != expected:
            raise PolicyError("unverified or forged rule-specific CI evidence")
    matched = {code: [] for code in SAFE_STEPS}
    unknown = 0
    for row in tasks:
        preview = row.get("stage6_candidate")
        if preview is None:
            unknown += 1
        else:
            matched[preview["rule_code"]].append(row)
    results = []
    safe = 0
    ambiguous = 0
    for code, step in SAFE_STEPS.items():
        revisions = matched[code]
        if not revisions:
            continue
        if (len(revisions) > 1
                or any("MULTIPLE_EVIDENCE_REVISIONS_REQUIRE_SELECTION"
                       in r["blocking_reasons"] for r in revisions)):
            status = "AMBIGUOUS_SOURCE_REVISION_NO_GO"
            ambiguous += len(revisions)
        else:
            status = "PINNED_SAFE_QA_OBSERVED_REVIEW_REQUIRED"
            safe += 1
        results.append({
            "rule_id": code,
            "candidate_evidence_sha256": (
                revisions[0]["evidence_sha256"] if len(revisions) == 1
                else None),
            "candidate_revision_count": len(revisions),
            "status": status,
            "public_ci_run_id": main_qa["run_id"],
            "public_ci_head_sha": main_qa["head_sha"],
            "checked_synthetic_step": step[0],
            "upstream_merge_sha": KNOWN[code]["upstream_merge_sha"],
            "safe_runtime_template_passed": status.startswith("PINNED_"),
            "new_candidate_independent_fix_verified": False,
            "full_release_version_coverage_verified": False,
            "human_license_review": False,
            "owner_approved_new_candidate": False,
        })
    return {
        "schema": SCHEMA,
        "status": "SAFE_TEMPLATE_QA_REVIEW_READY_NO_NEW_APPROVAL",
        "candidate_count": len(tasks),
        "safe_templates_observed": safe,
        "ambiguous_revisions": ambiguous,
        "unknown_or_unmatched": unknown,
        "results": results,
        "new_rules_approved": 0, "auto_promoted": False,
        "owner_signed": False, "production_approved": False,
        "license_signoff": False, "unsafe_external_code_executed": False,
        "persistent_writes": 0,
    }


def verify_public_candidate_qa(root: Path, *, run_id: int) -> dict:
    """Live bounded evidence verification; zero output writes or scheduling."""
    handoff = prepare_verification_handoff(Path(root))
    complete, _ = _checked_handoff(handoff)
    if not complete:
        return assess_safe_candidate_qa(handoff, None, None, None)
    main_qa = validate_live_automated_qa(run_id)
    base = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}"
    jobs = _public_json(base + "/jobs?per_page=100")
    # Test recipes are UCIE-owned pinned code; these checks do not download
    # or execute any upstream patch, binary or task-supplied command.
    pinned = {
        "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO": None,
        "PS_RESOLVE_PATH_DOT_PREFIX": _postfix_ci(),
        "PS_FUZZY_GET_COMMAND_DUPLICATES": _third_ci(),
        "PY_SCANDIR_SHARED_ITERATOR_RACE": _fourth_ci(),
    }
    return assess_safe_candidate_qa(handoff, main_qa, jobs, pinned)
