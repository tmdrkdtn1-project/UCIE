"""Internal read-only matcher for already VERIFIED signed Rulepack contents.

Callers MUST first check the complete Rulepack signature, expiry, trusted
key, owner approval and immutable rule payload. This matcher does not sign,
approve, verify an owner, execute source, or read any user files.
"""
from __future__ import annotations

import re

from .policy import PolicyError

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
MAX_RULES = 64


def match_signed_static_rules(scan: object, signed_rules: object, *,
                              expected_approval: str, allow_python: bool = False) -> list[dict]:
    """Match any bounded subset of trusted and signed pinned scan rules.

    This is not an approval API. The signed rules must originate from a prior
    successful signature/scope verification, never from arbitrary JSON.
    """
    from ucie_miner.static_rule_bridge import (
        _check_receipt, SCANNER_GUIDANCE, SOURCE_BINDINGS,
    )
    from ucie_miner.verification_handoff import PINNED_RULES
    from ucie_miner.patterns import PatternError

    if expected_approval not in (
            "HUMAN_REVIEW_REQUIRED", "AUTOMATED_QA_OWNER_RISK_ACCEPTED"):
        raise PolicyError("unsupported signed-rule approval contract")
    if (type(signed_rules) is not list
            or not 1 <= len(signed_rules) <= MAX_RULES):
        raise PolicyError("invalid signed prevention rule count")
    by_id = {}
    for rule in signed_rules:
        if not isinstance(rule, dict):
            raise PolicyError("invalid signed prevention rule")
        identifier = rule.get("rule_id")
        pair = SOURCE_BINDINGS.get(identifier) if isinstance(identifier, str) else None
        if identifier in by_id or pair is None:
            raise PolicyError("unrecognized or duplicate signed rule")
        source, number = pair
        sha = rule.get("upstream_merge_sha")
        if (type(sha) is not str or HEX40.fullmatch(sha) is None
                or PINNED_RULES.get((source, number, sha)) != identifier
                or rule.get("upstream") !=
                    f"https://github.com/{source}/pull/{number}"
                or rule.get("approval") != expected_approval
                or rule.get("scanner") != (
                    "ucie_miner.static_concurrency.inspect_python_scandir_source"
                    if identifier == "PY_SCANDIR_SHARED_ITERATOR_RACE"
                    else "ucie_powershell_static_candidates.ps1")
                or rule.get("automation") != "NEVER_AUTO_APPLY"
                or type(rule.get("safe_guidance")) is not str
                or not rule["safe_guidance"]):
            raise PolicyError("signed rule lacks an exact approved source identity")
        by_id[identifier] = rule
    try:
        language = _check_receipt(scan)
    except (PatternError, ValueError, TypeError) as exc:
        raise PolicyError("untrusted static scanner receipt") from exc
    if language not in (("powershell", "python") if allow_python
                        else ("powershell",)):
        raise PolicyError("scanner receipt language not allowed by this release")
    findings = []
    for item in scan["findings"]:
        rule = by_id.get(item["pattern_code"])
        if rule is None:
            continue  # A valid but unsigned rule is NOT activated.
        if (language == "python") != rule["rule_id"].startswith("PY_"):
            raise PolicyError("signed rule and receipt language mismatch")
        if (item["public_evidence"] != rule["upstream"]
                or item["safe_fix_guidance"] !=
                    SCANNER_GUIDANCE[rule["rule_id"]]):
            raise PolicyError("inconsistent static finding evidence")
        finding = {
            "rule_id": rule["rule_id"],
            "line": item["line"], "column": item["column"],
            "public_evidence": rule["upstream"],
            "guidance": rule["safe_guidance"],
            "manual_review_required": True,
            "runtime_bug_confirmed_for_this_input": False,
        }
        if language == "python":
            finding["iterator_binding"] = item["iterator_binding"]
            finding["thread_boundary"] = item["thread_boundary"]
        findings.append(finding)
    return findings
