"""Two-rule signed PUBLIC_ONLY *review* pack and inert multi-rule consumer.

This extends the existing first-rule review path without modifying production
signatures or granting approval. Only exact UCIE-authored pinned rules can
appear; no miner/CI input can auto-select, authorize or publish rules.
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
from .prevention_rulepack import RULE as FIRST
from .rulepack import canonical_json, digest, key_id, _private_key, _public_key, _valid_outpath

SCHEMA = "UCIE_PUBLIC_MULTI_RULE_REVIEW_V1"
CONFIRM = "AUTHORIZE_UCIE_TWO_RULE_MANUAL_REVIEW_ONLY"
FILES = frozenset({"manifest.json", "rules/prevention.json",
                   "signatures/manifest.sig"})
MAX_BYTES = 131072
SECOND = {
    "rule_id": "PS_RESOLVE_PATH_DOT_PREFIX",
    "pattern": "literal PowerShell Resolve-Path -Relative use; dot-prefixed path",
    "problem": "PowerShell 7.6.6 returned ambiguous dot-prefixed relative paths on disposable CI",
    "safe_guidance": "Review dot-prefixed relative paths and use an anchored base-directory conversion if needed",
    "affected_observation": "PowerShell 7.6.6 Windows/Linux; fixed-like behavior in 7.7.0-preview.6 development CI build; release applicability not verified",
    "upstream": "https://github.com/PowerShell/PowerShell/pull/28087",
    "upstream_merge_sha": "373f6a7b7972a0a4b73bfd9737a0d768d28b347e",
    "runtime_ci": "https://github.com/tmdrkdtn1-project/UCIE/actions/runs/39101087404",
    "scanner": "ucie_powershell_static_candidates.ps1",
    "automation": "NEVER_AUTO_APPLY",
    "risk": "PATH_OUTPUT_COMPATIBILITY",
    "approval": "HUMAN_REVIEW_REQUIRED",
}
RULES = [FIRST, SECOND]
RULE_BYTES = canonical_json(RULES)


def _valid_archive(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise PolicyError("missing or unsafe review archive")
    try:
        with zipfile.ZipFile(path, "r") as z:
            entries = z.infolist()
            if (len(entries) != len(FILES)
                    or {i.filename for i in entries} != FILES
                    or any(i.file_size > MAX_BYTES or i.flag_bits & 1
                           or ((i.external_attr >> 16) & 0o170000) == 0o120000
                           for i in entries)):
                raise PolicyError("unsafe or additional review archive entries")
            return {i.filename: z.read(i.filename) for i in entries}
    except (OSError, RuntimeError, zipfile.BadZipFile, EOFError) as exc:
        raise PolicyError("review archive could not be opened") from exc


def _date(value: object) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise PolicyError("non-UTC review time")
    try:
        stamp = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PolicyError("invalid review time") from exc
    if stamp.utcoffset() != timedelta(0):
        raise PolicyError("non-UTC review time")
    return stamp


def publish_multi_review(root: Path, private_path: Path, output: Path, *,
                         serial: int, confirmation: str) -> Path:
    """Owner-initiated REVIEW ONLY; no production signing or rule approval."""
    if confirmation != CONFIRM or type(serial) is not int or not 1 <= serial <= 10_000_000:
        raise PolicyError("explicit two-rule review authorization required")
    key = _private_key(Path(private_path))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    manifest = {
        "schema": SCHEMA, "channel": "MANUAL_REVIEW_ONLY",
        "scope": "PUBLIC_ONLY_MANUAL_STATIC_SCAN",
        "serial": serial,
        "created_utc": now.isoformat().replace("+00:00", "Z"),
        "expires_utc": (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "key_id": key_id(key.public_key()), "rules_sha256": digest(RULE_BYTES),
        "rule_count": 2, "auto_apply": False,
        "production_approved": False, "deploy_allowed": False,
        "owner_action": "EXPLICIT_MANUAL_REVIEW_SIGNING_ONLY",
    }
    raw = canonical_json(manifest)
    target = _valid_outpath(Path(root), Path(output))
    fd, temp = tempfile.mkstemp(dir=str(target.parent), prefix=".ucie_multi_review_",
                                suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as handle:
            with zipfile.ZipFile(handle, "w", compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("manifest.json", raw)
                z.writestr("rules/prevention.json", RULE_BYTES)
                z.writestr("signatures/manifest.sig", key.sign(raw))
        os.link(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)
    return target


def verify_multi_review(path: Path, trusted_public: Path, *,
                        min_serial: int = 1,
                        at_time: datetime | None = None) -> dict:
    """Offline signature, exact-two-rule allowlist, expiry and rollback gate."""
    if type(min_serial) is not int or not 1 <= min_serial <= 10_000_000:
        raise PolicyError("invalid review serial threshold")
    blobs = _valid_archive(Path(path))
    trusted = _public_key(Path(trusted_public))
    try:
        man = json.loads(blobs["manifest.json"])
        rules = json.loads(blobs["rules/prevention.json"])
    except (UnicodeError, ValueError) as exc:
        raise PolicyError("non-JSON signed review contents") from exc
    fields = {
        "schema", "channel", "scope", "serial", "created_utc", "expires_utc",
        "key_id", "rules_sha256", "rule_count", "auto_apply",
        "production_approved", "deploy_allowed", "owner_action",
    }
    if (type(man) is not dict or set(man) != fields
            or canonical_json(man) != blobs["manifest.json"]
            or rules != RULES
            or canonical_json(rules) != RULE_BYTES
            or man["schema"] != SCHEMA or man["channel"] != "MANUAL_REVIEW_ONLY"
            or man["scope"] != "PUBLIC_ONLY_MANUAL_STATIC_SCAN"
            or type(man["serial"]) is not int or man["serial"] < min_serial
            or man["rule_count"] != 2
            or man["key_id"] != key_id(trusted)
            or man["rules_sha256"] != digest(blobs["rules/prevention.json"])
            or man["owner_action"] != "EXPLICIT_MANUAL_REVIEW_SIGNING_ONLY"
            or man["auto_apply"] is not False
            or man["production_approved"] is not False
            or man["deploy_allowed"] is not False):
        raise PolicyError("unapproved or inconsistent two-rule review payload")
    try:
        trusted.verify(blobs["signatures/manifest.sig"], blobs["manifest.json"])
    except (InvalidSignature, ValueError) as exc:
        raise PolicyError("review signature invalid") from exc
    now = at_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise PolicyError("timezone-aware verification required")
    created, expires = _date(man["created_utc"]), _date(man["expires_utc"])
    if (created > now + timedelta(minutes=5) or now >= expires
            or expires <= created or expires - created > timedelta(days=7)):
        raise PolicyError("review pack expired or not yet valid")
    return {
        "result": "SIGNED_TWO_RULE_REVIEW_ONLY_VERIFIED",
        "serial": man["serial"],
        "rule_ids": [r["rule_id"] for r in RULES],
        "rules_verified": 2, "signature": "VALID",
        "scope": man["scope"], "production_approved": False,
        "deploy_allowed": False, "auto_apply": False,
    }


def scan_multi_review_receipt(path: Path, trusted_public: Path,
                              scan: object, *, min_serial: int = 1) -> dict:
    """Classify inert PowerShell scanner receipt against BOTH signed review rules.

    A scanner receipt can be user-supplied and is NOT source authentication.
    This NEVER authorizes a real production scan, code execution, or fix.
    """
    trusted = verify_multi_review(path, trusted_public, min_serial=min_serial)
    from ucie_miner.static_rule_bridge import _check_receipt, SCANNER_GUIDANCE
    from ucie_miner.patterns import PatternError

    try:
        language = _check_receipt(scan)
    except (PatternError, TypeError, ValueError) as exc:
        raise PolicyError("untrusted scanner receipt") from exc
    if language != "powershell":
        raise PolicyError("only PowerShell inert receipts can be consumed")
    mapping = {rule["rule_id"]: rule for rule in RULES}
    findings = []
    for item in scan["findings"]:
        rule = mapping.get(item["pattern_code"])
        if rule is None:
            continue
        if (item["safe_fix_guidance"] != SCANNER_GUIDANCE[rule["rule_id"]]
                or item["public_evidence"] != rule["upstream"]):
            raise PolicyError("scanner finding does not match pinned rule")
        findings.append({
            "rule_id": rule["rule_id"], "line": item["line"],
            "column": item["column"], "public_evidence": rule["upstream"],
            "guidance": rule["safe_guidance"],
            "confidence": "STATIC_HEURISTIC_REVIEW_REQUIRED",
            "approved": False,
        })
    return {
        "schema": "UCIE_TWO_RULE_SIGNED_REVIEW_CONSUMER_V1",
        "status": "REVIEW_CANDIDATES_ONLY",
        "pack_serial": trusted["serial"], "signature": "VALID",
        "rule_count": 2, "finding_count": len(findings), "findings": findings,
        "source_sha256": scan["source_sha256"],
        "parser_executed_supplied_code": False,
        "source_authentication_verified": False,
        "production_approved": False, "deploy_allowed": False,
        "auto_apply": False, "persistent_writes": 0,
    }
