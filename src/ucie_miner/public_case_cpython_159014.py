"""UCIE first genuinely observed approved public candidate: CPython PR #159014.

A one-candidate bounded *documentation correction* and runtime option behavior
observation, not an upstream source-binary before/after test or independent
human QA. The original official PR was merged 2026-10-14. Input patch text
is untrusted and is NEVER run or retained. Runs only on disposable CI.

Do not interpret an observed current CPython runtime flag as proof of the
patch's release inclusion, source-build coverage, human security/license QA,
or permission to install a rule. Keep all release/Rulepack gates NO_GO.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re

from .public_discovery import DiscoveryError
from .public_pr_coverage_audit import (
    _upstream_identity, _transport, _approved_url, fetch_stage17_public,
    public_pr_audit_url,
)

SCHEMA = "UCIE_CPYTHON_159014_PUBLIC_DOCUMENTATION_RUNTIME_RECEIPT_V1"
SOURCE = "python/cpython"
PR = 159014
URL = f"https://github.com/{SOURCE}/pull/{PR}"
PINNED_MERGE_SHA = "91248026c8a41910098032dd23f9a05ad2d9b513"
MERGED_UTC = "2026-10-14T13:18:20Z"
FILES = (
    "Doc/howto/remote_debugging.rst",
    "Doc/using/cmdline.rst",
)
WRONG = "-X disable_remote_debug"
RIGHT = "-X disable-remote-debug"
FILE_REQUEST = public_pr_audit_url(SOURCE, PR, page=1)
API_REQUEST = public_pr_audit_url(SOURCE, PR)
_SHA64 = re.compile(r"[0-9a-f]{64}\Z")


def _checked_source_patch(record):
    if (type(record) is not dict
            or type(record.get("filename")) is not str
            or type(record.get("patch")) is not str
            or len(record["patch"]) > 16_384
            or record.get("status") != "modified"):
        raise DiscoveryError("missing bounded official document diff")
    patch = record["patch"]
    # Compare only exact documented option spelling on removed/added lines.
    old = "-* Use the :option:`" + WRONG + "` command-line option."
    new = "+* Use the :option:`" + RIGHT + "` command-line option."
    old_cli = '-   * ``' + WRONG + '`` disables the remote debugging support'
    new_cli = '+   * ``' + RIGHT + '`` disables the remote debugging support'
    if record["filename"] == FILES[0]:
        ok = old in patch and new in patch
    elif record["filename"] == FILES[1]:
        ok = old_cli in patch and new_cli in patch
    else:
        raise DiscoveryError("out-of-scope upstream changed file")
    if not ok:
        raise DiscoveryError("public documentation spelling correction not established")
    return hashlib.sha256(patch.encode("utf-8")).hexdigest()


def inspect_cpython_159014_observation(*, fetch=None, observe=None,
                                      runtime_name=None, runtime_version=None,
                                      platform=None) -> dict:
    """One fixed official PR, at most two bounded anonymous public GETs.

    `observe` must be a locally authored, isolated runtime callback. Actual
    CI evidence is the public workflow step/log that called this function,
    not a blind trust in any external or injected Python callback.
    """
    if observe is None or not callable(observe):
        raise DiscoveryError("bounded UCIE authored runtime observer required")
    if (runtime_name != "CPython" or runtime_version is None
            or type(runtime_version) is not str
            or re.fullmatch(r"3\.15\.[0-9]{1,3}", runtime_version) is None
            or platform not in ("linux", "win32")):
        raise DiscoveryError("unsupported candidate-specific CPython CI runtime")

    transport = fetch_stage17_public if fetch is None else fetch
    if not _approved_url(API_REQUEST) or not _approved_url(FILE_REQUEST):
        raise DiscoveryError("unexpected public allowlist expansion")
    raw, remaining = _transport(transport, API_REQUEST)
    if type(raw) is not dict:
        raise DiscoveryError("untrusted approved PR metadata")
    sha, file_count = _upstream_identity(SOURCE, PR, raw)
    if (sha != PINNED_MERGE_SHA
            or raw.get("merged_at") != MERGED_UTC
            or file_count != len(FILES)):
        raise DiscoveryError("public PR changed or not exact candidate")
    if remaining is not None and remaining < 12:
        raise DiscoveryError("public source rate budget too low")
    page, remaining = _transport(transport, FILE_REQUEST)
    if (type(page) is not list or len(page) != len(FILES)
            or remaining is not None and remaining < 12):
        raise DiscoveryError("untrusted or incomplete public documentation file list")
    names = [p.get("filename") for p in page if type(p) is dict]
    if set(names) != set(FILES) or len(names) != len(set(names)):
        raise DiscoveryError("changed files do not match pinned documentation-only PR")
    digest_map = {}
    for item in page:
        digest_map[item["filename"]] = _checked_source_patch(item)

    try:
        baseline = observe([])
        misspelled = observe(["-X", "disable_remote_debug"])
        corrected = observe(["-X", "disable-remote-debug"])
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        raise DiscoveryError("isolated CPython option observation failed") from exc
    if ((baseline, misspelled, corrected) != (True, True, False)
            or any(type(x) is not bool
                   for x in (baseline, misspelled, corrected))):
        raise DiscoveryError("current runtime flag invariant not observed")
    body = {
        "schema": SCHEMA,
        "status": ("SYNTHETIC_PUBLIC_TRANSPORT_RUNTIME_OBSERVATION_NO_GO"
                   if fetch is not None else
                   "PUBLIC_DOCUMENTATION_AND_CPYTHON_RUNTIME_OBSERVED_NO_GO"),
        "candidate_public_url": URL,
        "approved_source": SOURCE,
        "pinned_merge_sha": PINNED_MERGE_SHA,
        "merged_utc": MERGED_UTC,
        "document_paths": list(FILES),
        "document_patch_sha256_by_path": dict(sorted(digest_map.items())),
        "documentation_correction_observed": True,
        "runtime_product": runtime_name,
        "runtime_version_observed": runtime_version,
        "runner_platform": platform,
        "baseline_remote_debug_enabled": baseline,
        "old_documented_option_still_enabled": misspelled,
        "corrected_documented_option_disabled_remote_debug": not corrected,
        "option_runtime_behavior_observed_on_ephemeral_runner": True,
        "source_binaries_before_after_revision_built_and_tested": False,
        "public_api_gets": 2 if fetch is None else 0,
        "test_transport_injected": fetch is not None,
        "public_diff_text_stored": False,
        "untrusted_patch_executed": False,
        "version_3_15_1_behaviour_observed_only": True,
        "all_affected_versions_tested": False,
        "published_release_inclusion_independently_attested": False,
        "license_independently_signed_off": False,
        "security_independent_human_review": False,
        "independent_reviewers_attested": False,
        "owner_release_authorized": False,
        "automatic_rule_promotions": 0,
        "rules_approved": 0,
        "model_or_knowledge_db_writes": 0,
        "other_project_accesses": 0,
        "production_approved": False,
    }
    body["receipt_sha256"] = hashlib.sha256(json.dumps(
        body, sort_keys=True, ensure_ascii=True, allow_nan=False,
        separators=(",", ":")).encode("ascii")).hexdigest()
    body["receipt_sha256_is_signature"] = False
    return body
