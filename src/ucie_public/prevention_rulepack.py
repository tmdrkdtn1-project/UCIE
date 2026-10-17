"""Manually signed, portable PUBLIC_ONLY prevention review pack.

First rule only; no unattended signing, auto-approval, code execution or
installation. The recipient verifies an offline fixed-rule payload against
an explicitly trusted public key. Signing does NOT mean production approval.
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
from .rulepack import (canonical_json, digest, key_id, _private_key,
                       _public_key, _valid_outpath)

SCHEMA = "UCIE_PUBLIC_PREVENTION_REVIEW_PACK_V1"
CHANNEL = "MANUAL_REVIEW_ONLY"
CONFIRM = "AUTHORIZE_FIRST_PUBLIC_PREVENTION_REVIEW_PACK"
FILES = frozenset({
    "manifest.json", "rules/prevention.json", "signatures/manifest.sig",
})
MAX_BYTES = 131072

# All content is UCIE-authored metadata and manual guidance, never
# downloaded third-party source code, a script or an executable patch.
RULE = {
    "rule_id": "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO",
    "pattern": "literal PowerShell Python -X disable_remote_debug argument",
    "problem": "The underscore option is ignored on tested CPython 3.15.0",
    "safe_guidance": "Use -X disable-remote-debug and verify the actual target interpreter",
    "affected_observation": "CPython 3.15.0 Windows and Linux ephemeral runner behavior",
    "upstream": "https://github.com/python/cpython/pull/159014",
    "upstream_merge_sha": "91248026c8a41910098032dd23f9a05ad2d9b513",
    "runtime_ci": "https://github.com/tmdrkdtn1-project/UCIE/actions/runs/39041236769",
    "scanner": "ucie_powershell_static_candidates.ps1",
    "automation": "NEVER_AUTO_APPLY",
    "risk": "SECURITY_CONFIGURATION",
    "approval": "HUMAN_REVIEW_REQUIRED",
}


def _pack_metadata(key, serial: int, now: datetime, rules_bytes: bytes):
    return {
        "schema": SCHEMA,
        "channel": CHANNEL,
        "scope": "PUBLIC_ONLY",
        "serial": serial,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "key_id": key_id(key),
        "rules_sha256": digest(rules_bytes),
        "rule_count": 1,
        "owner_action": "EXPLICIT_SIGNING_INVOCATION_ONLY",
        "production_approved": False,
        "deploy_allowed": False,
    }


def publish_prevention_review(root: Path, key_path: Path, output: Path,
                              *, serial: int, confirmation: str) -> Path:
    if confirmation != CONFIRM:
        raise PolicyError("owner has not explicitly authorized review-pack signing")
    if type(serial) is not int or not 1 <= serial <= 10_000_000:
        raise PolicyError("invalid release serial")
    root = Path(root)
    output = Path(output)
    private = _private_key(Path(key_path))
    rule_bytes = canonical_json([RULE])
    now = datetime.now(timezone.utc).replace(microsecond=0)
    manifest = _pack_metadata(private.public_key(), serial, now, rule_bytes)
    man_bytes = canonical_json(manifest)
    signature = private.sign(man_bytes)
    target = _valid_outpath(root, output)
    fd, staging = tempfile.mkstemp(
        dir=str(target.parent), prefix=".ucie_prevention_", suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as dest:
            with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("manifest.json", man_bytes)
                z.writestr("rules/prevention.json", rule_bytes)
                z.writestr("signatures/manifest.sig", signature)
        os.link(staging, target)
    finally:
        Path(staging).unlink(missing_ok=True)
    return target


def verify_prevention_review(path: Path, trust: Path, *, min_serial: int = 1,
                             at_time: datetime | None = None) -> dict:
    path = Path(path)
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_size > MAX_BYTES):
        raise PolicyError("missing, unsafe, or oversized review pack")
    if type(min_serial) is not int or min_serial < 1:
        raise PolicyError("invalid rollback threshold")
    trusted_key = _public_key(Path(trust))
    try:
        with zipfile.ZipFile(path, "r") as z:
            entries = z.infolist()
            names = [i.filename for i in entries]
            if (len(names) != len(FILES) or set(names) != FILES
                    or any(i.file_size > MAX_BYTES or i.flag_bits & 1
                           or ((i.external_attr >> 16) & 0o170000) == 0o120000
                           for i in entries)):
                raise PolicyError("unsafe or unexpected review pack contents")
            content = {name: z.read(name) for name in names}
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise PolicyError("invalid review pack archive") from exc
    try:
        manifest = json.loads(content["manifest.json"].decode("utf-8"))
        rules = json.loads(content["rules/prevention.json"].decode("utf-8"))
        if (canonical_json(manifest) != content["manifest.json"]
                or canonical_json(rules) != content["rules/prevention.json"]):
            raise PolicyError("noncanonical manifest or rule")
    except (ValueError, UnicodeDecodeError, TypeError) as exc:
        raise PolicyError("invalid review pack data") from exc
    expected = {
        "schema", "channel", "scope", "serial", "created_at",
        "expires_at", "key_id", "rules_sha256", "rule_count",
        "owner_action", "production_approved", "deploy_allowed",
    }
    if (not isinstance(manifest, dict) or set(manifest) != expected
            or manifest["schema"] != SCHEMA or manifest["channel"] != CHANNEL
            or manifest["scope"] != "PUBLIC_ONLY"
            or type(manifest["serial"]) is not int
            or manifest["serial"] < min_serial
            or manifest["rule_count"] != 1
            or manifest["owner_action"] != "EXPLICIT_SIGNING_INVOCATION_ONLY"
            or manifest["production_approved"] is not False
            or manifest["deploy_allowed"] is not False
            or manifest["key_id"] != key_id(trusted_key)
            or manifest["rules_sha256"] != digest(content["rules/prevention.json"])
            or rules != [RULE]):
        raise PolicyError("unapproved, altered or rollback-prone rulepack")
    try:
        trusted_key.verify(
            content["signatures/manifest.sig"], content["manifest.json"])
    except (InvalidSignature, ValueError) as exc:
        raise PolicyError("untrusted or changed review pack") from exc
    try:
        created = datetime.fromisoformat(manifest["created_at"].replace("Z", "+00:00"))
        expiry = datetime.fromisoformat(manifest["expires_at"].replace("Z", "+00:00"))
        now = at_time or datetime.now(timezone.utc)
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise PolicyError("invalid rulepack time claims") from exc
    if (any(x.tzinfo is None for x in (created, expiry, now))
            or created > now + timedelta(minutes=5)
            or now >= expiry
            or expiry <= created or expiry - created > timedelta(days=7)):
        raise PolicyError("not-yet-valid or expired review pack")
    return {
        "result": "SIGNED_PUBLIC_PREVENTION_REVIEW_PACK_VERIFIED",
        "rule_id": RULE["rule_id"],
        "serial": manifest["serial"],
        "signature": "VALID",
        "safe_guidance": RULE["safe_guidance"],
        "trust_key_id": manifest["key_id"],
        "production_approved": False,
        "deploy_allowed": False,
        "auto_promoted": False,
    }
