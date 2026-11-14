"""One-shot read-only UCIE-owned GitHub Actions run metadata recheck.

A runner's generic SUCCESS is NOT candidate-specific regression evidence.
This code only corroborates an existing signed QA packet's asserted CI
run ID, commit identity and official UCIE workflow path. No job executes,
no logs/artifacts or private repos are downloaded, no release is approved.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import urllib.error
import urllib.request

from ucie_public.policy import PolicyError

from .core import NoRedirect, MiningError
from .public_discovery import DiscoveryError, _utc
from .public_library_qa_packet import inspect_library_candidate_qa_packet
from .public_library_upstream_recheck import _no_duplicate

SCHEMA = "UCIE_LIBRARY_SIGNED_PACKET_RUNNER_CI_RECHECK_V1"
REPO = "tmdrkdtn1-project/UCIE"
WORKFLOW_PATH = REPO + "/.github/workflows/stage1-offline-tests.yml@"
MAX_RESPONSE = 180_000
MIN_REMAINING = 12
_ALLOWED_RUN_STATES = frozenset({
    "completed", "queued", "in_progress", "requested", "waiting", "pending",
})
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")
_URL = re.compile(
    r"https://api\.github\.com/repos/tmdrkdtn1-project/UCIE/"
    r"actions/runs/([1-9][0-9]{0,11})\Z"
)


def _url(run_id: int) -> str:
    if type(run_id) is not int or not 1 <= run_id <= 999999999999:
        raise PolicyError("invalid UCIE runner CI run ID")
    return f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}"


def _fetch_exact_ucie_ci_run(url: str):
    """One approved public UCIE GitHub Actions metadata JSON request."""
    if type(url) is not str or _URL.fullmatch(url) is None:
        raise PolicyError("foreign or noncanonical UCIE CI API URL")
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "UCIE-LIBRARY-CI-METADATA-READONLY/1",
    }, method="GET")
    try:
        with urllib.request.build_opener(NoRedirect).open(
                request, timeout=12) as response:
            if (response.status != 200
                    or "json" not in response.headers.get(
                        "Content-Type", "").lower()):
                raise PolicyError("unexpected public runner metadata response")
            body = response.read(MAX_RESPONSE + 1)
            remaining = response.headers.get("X-RateLimit-Remaining")
    except (OSError, TimeoutError, urllib.error.HTTPError,
            urllib.error.URLError, MiningError) as exc:
        raise PolicyError("UCIE public runner metadata unavailable") from exc
    if len(body) > MAX_RESPONSE:
        raise PolicyError("runner CI metadata response too large")
    if remaining is not None:
        if (type(remaining) is not str or len(remaining) > 6
                or not remaining.isascii() or not remaining.isdecimal()):
            raise PolicyError("invalid public GitHub API rate header")
        remaining = int(remaining)
    try:
        data = json.loads(body.decode("utf-8"),
                          object_pairs_hook=_no_duplicate)
    except (ValueError, UnicodeError) as exc:
        raise PolicyError("untrusted CI metadata JSON") from exc
    return data, remaining


def recheck_signed_packet_runner_ci(
        root, current, public_url, packet, artifacts, *,
        owner_trust, qa_trust, expected_head_sha256,
        previous=None, at_time=None, live=False, fetch=None):
    """Recheck a current signed packet's generic UCIE CI metadata once.

    Only an already valid and currently signed packet can select the run ID.
    A verified generic CI run is NEVER evidence of an affected/fixed
    candidate-specific regression without separate independently audited
    steps and immutable artefacts. An injected transport is not live proof.
    """
    if live is not True:
        raise PolicyError("explicit one-shot UCIE public runner audit required")
    bound = inspect_library_candidate_qa_packet(
        root, current, public_url, packet, artifacts,
        owner_trust=owner_trust, qa_trust=qa_trust,
        expected_head_sha256=expected_head_sha256,
        previous=previous, at_time=at_time)
    run_id = bound["runner_run_id"]
    url = _url(run_id)
    transport = _fetch_exact_ucie_ci_run if fetch is None else fetch
    outcome = transport(url)
    if (type(outcome) is not tuple or len(outcome) != 2
            or type(outcome[0]) is not dict
            or (outcome[1] is not None and
                (type(outcome[1]) is not int or outcome[1] < 0))):
        raise PolicyError("malformed UCIE runner metadata transport")
    meta, remaining = outcome
    repo = meta.get("repository")
    status = meta.get("status")
    conclusion = meta.get("conclusion")
    observed_sha = meta.get("head_sha")
    if (type(meta.get("id")) is not int
            or meta["id"] != run_id
            or type(repo) is not dict
            or repo.get("full_name") != REPO
            or meta.get("html_url") !=
               f"https://github.com/{REPO}/actions/runs/{run_id}"
            or type(meta.get("path")) is not str
            or not meta["path"].startswith(WORKFLOW_PATH)
            or type(observed_sha) is not str
            or _SHA40.fullmatch(observed_sha) is None
            or type(status) is not str
            or status not in _ALLOWED_RUN_STATES
            or (status != "completed" and conclusion is not None)
            or (status == "completed" and conclusion not in (
                "success", "failure", "cancelled", "skipped", "timed_out",
                "action_required", "neutral", "stale"))):
        raise PolicyError("unexpected or foreign UCIE workflow metadata")
    updated_at = _utc(meta.get("updated_at"))
    now = at_time if at_time is not None else datetime.now(timezone.utc)
    if (not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset().total_seconds() != 0
            or updated_at > now.replace(microsecond=0)):
        raise PolicyError("future or non-UTC CI observation time")

    match = observed_sha == packet["runner_commit_sha"]
    success = status == "completed" and conclusion == "success"
    rate_paused = remaining is not None and remaining < MIN_REMAINING
    if rate_paused:
        verdict = "PUBLIC_RUNNER_API_RATE_PAUSED_NO_GO"
    elif not match:
        verdict = "UCIE_RUNNER_CI_SHA_MISMATCH_NO_GO"
    elif not success:
        verdict = "UCIE_RUNNER_CI_NOT_COMPLETED_SUCCESSFULLY_NO_GO"
    elif fetch is not None:
        verdict = "SYNTHETIC_CI_METADATA_MATCH_NOT_LIVE_NO_GO"
    else:
        verdict = "UCIE_GENERAL_CI_METADATA_OBSERVED_CANDIDATE_QA_PENDING_NO_GO"
    return {
        "schema": SCHEMA,
        "status": verdict,
        "public_url": bound["public_url"],
        "pinned_public_revision_sha": bound["pinned_revision_sha"],
        "signed_packet_sha256": bound["signed_packet_sha256"],
        "signed_packet_artifacts_integrity_checked": True,
        "runner_repo": REPO,
        "runner_run_id": run_id,
        "runner_commit_sha_in_signed_packet": packet["runner_commit_sha"],
        "runner_commit_sha_observed": observed_sha,
        "runner_commit_sha_matches": match,
        "runner_completed_success_claim_matches_metadata": success,
        "public_api_response_retrieved_live":
            fetch is None and not rate_paused,
        "test_transport_injected": fetch is not None,
        "transport_invocations": 1,
        "http_get_attempts": 1 if fetch is None else 0,
        "candidate_specific_test_steps_observed": False,
        "upstream_candidate_revision_tested_by_runner_proven": False,
        "affected_vs_fixed_behavior_reproduced_independently": False,
        "release_license_and_security_independently_reviewed": False,
        "human_reviewer_independence_verified": False,
        "owner_release_approval": False,
        "rulepack_release_authorized": False,
        "automatic_rule_promotions": 0,
        "database_writes": 0,
        "external_source_code_executed": False,
        "other_project_accesses": 0,
        "production_approved": False,
    }
