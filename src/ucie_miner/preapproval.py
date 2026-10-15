"""Stage 7/8: fail-closed readiness summary over untrusted candidate receipts.

This component cannot approve, sign, deploy, execute code, or install tasks.
Caller-supplied metadata (even marked LIVE) is *never* an authorization token.
"""
from __future__ import annotations

from .patterns import PatternError

ALLOWED_STATES = frozenset({
    "NOT_CHECKED", "SOURCE_UNAVAILABLE", "SOURCE_MISMATCH",
    "PUBLIC_API_METADATA_MATCHED", "SYNTHETIC_METADATA_MATCHED",
})


def preapproval_readiness(chain: object, provenance: object) -> dict:
    if not isinstance(chain, dict) or not isinstance(provenance, dict):
        raise PatternError("missing integration or provenance receipt")
    gate = chain.get("approval_gate")
    preview = chain.get("rulepack_preview")
    patterns = chain.get("pattern_preview")
    if (chain.get("schema") != "UCIE_STAGE4_7_INTEGRATION_PREVIEW_V1"
            or chain.get("database_writes") != 0
            or chain.get("production_approved") is not False
            or not isinstance(gate, dict)
            or gate.get("deploy_allowed") is not False
            or not isinstance(preview, dict)
            or preview.get("approval") is not False
            or preview.get("signed") is not False
            or preview.get("published") is not False
            or not isinstance(patterns, dict)
            or not isinstance(patterns.get("families"), list)
            or provenance.get("schema") != "UCIE_PUBLIC_PR_PROVENANCE_INSPECTION_V1"
            or provenance.get("persistent_writes") != 0
            or provenance.get("production_approved") is not False
            or not isinstance(provenance.get("items"), list)):
        raise PatternError("unsafe stage receipt")
    audit = provenance["items"]
    if (type(provenance.get("count")) is not int
            or provenance["count"] != len(audit)
            or type(chain.get("miner_count")) is not int
            or len(audit) != chain["miner_count"]):
        raise PatternError("incomplete provenance scope")
    seen = set()
    matched = 0
    for item in audit:
        if not isinstance(item, dict):
            raise PatternError("malformed provenance item")
        key = (item.get("source"), item.get("pr_number"))
        if (not isinstance(key[0], str) or type(key[1]) is not int
                or key in seen or item.get("source_check") not in ALLOWED_STATES
                or item.get("approved") is not False
                or item.get("license_verified") is not False
                or item.get("fix_independently_reproduced") is not False):
            raise PatternError("invalid provenance claim")
        seen.add(key)
        if item["source_check"] == "PUBLIC_API_METADATA_MATCHED":
            matched += 1
    for family in patterns["families"]:
        if not isinstance(family, dict):
            raise PatternError("invalid pattern family")
        source, numbers = family.get("source"), family.get("pr_numbers")
        if not isinstance(source, str) or not isinstance(numbers, list):
            raise PatternError("invalid pattern identity")
        for number in numbers:
            if (type(number) is not int or (source, number) not in seen):
                raise PatternError("provenance coverage gap")
    pending = []
    if (matched != len(audit)
            or provenance.get("live_checked") is not True):
        pending.append("PUBLIC_METADATA_RECHECK_REQUIRED")
    pending.extend((
        "PINNED_LICENSE_AND_SECURITY_REVIEW_REQUIRED",
        "INDEPENDENT_FIX_AND_REGRESSION_REPRODUCTION_REQUIRED",
        "OWNER_APPROVAL_AND_AUTHORIZED_SIGNING_REQUIRED",
        "WINDOWS_PRODUCTION_HOST_ACCEPTANCE_REQUIRED",
    ))
    return {
        "schema": "UCIE_PREAPPROVAL_READINESS_V1",
        "status": "NO_GO",
        "observed_public_metadata_matches": matched,
        "candidate_count": len(audit),
        "pending": pending,
        "input_receipts_are_not_authorizations": True,
        "production_approved": False,
        "rulepack_signed": False,
        "package_deployed": False,
        "scheduler_registered": False,
    }
