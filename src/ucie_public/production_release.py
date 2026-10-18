"""Stage 4 first public-rule production distribution, ONLY after two keyholders.

Independent QA's Ed25519 detached attestation and owner's DISTINCT
production Ed25519 signature are mandatory. Trust anchors must be supplied
independently by recipients; no key or credentials go into the package.
This distribution is for explicit PUBLIC_ONLY manual static scanning,
never unattended private-project access or auto-fix. A valid signature
authenticates a keyholder's declaration; it cannot by itself prove that
a genuine human review occurred.
"""
from __future__ import annotations

import json
import os
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature

from .policy import PolicyError
from .prevention_rulepack import RULE
from .rulepack import (canonical_json, digest, key_id, _private_key,
                       _public_key, _valid_outpath)

SCHEMA = "UCIE_PUBLIC_PREVENTION_PRODUCTION_V1"
QA_SCHEMA = "UCIE_STAGE4_INDEPENDENT_QA_ATTESTATION_V1"
CHANNEL = "OWNER_AUTHORIZED_PRODUCTION"
SCOPE = "PUBLIC_ONLY_MANUAL_STATIC_SCAN"
OWNER_CONFIRM = "AUTHORIZE_UCIE_FIRST_RULE_PRODUCTION_SIGNING"
FILES = frozenset({
    "manifest.json", "rules/prevention.json", "qa/attestation.json",
    "qa/attestation.sig", "signatures/owner.sig",
})
MAX_SIZE = 131072
RULE_ID = "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO"
PRODUCTION_RULE = {**RULE, "approval": "INDEPENDENT_QA_AND_OWNER_SIGNED"}
RULE_BYTES = canonical_json([PRODUCTION_RULE])

# These identities are deterministic and refer only to first-party CI and the
# single pinned approved upstream source. No arbitrary URLs/commands allowed.
EXPECTED_QA = {
    "schema": QA_SCHEMA,
    "rule_id": RULE_ID,
    "rule_sha256": digest(RULE_BYTES),
    "public_source": RULE["upstream"],
    "public_merge_sha": RULE["upstream_merge_sha"],
    "independent_runtime_ci": RULE["runtime_ci"],
    "consumer_acceptance_ci":
        "https://github.com/tmdrkdtn1-project/UCIE/actions/runs/39094501811",
    "scope": SCOPE,
    "independent_security_review": "PASS",
    "public_source_license_review": "PASS",
    "runtime_regression_review": "PASS",
    "recipient_acceptance_review": "PASS",
    "independent_reviewer_decision": "APPROVED",
}


def _parse_date(stamp: object) -> datetime:
    if not isinstance(stamp, str) or not stamp.endswith("Z"):
        raise PolicyError("QA/release UTC timestamp missing")
    try:
        result = datetime.fromisoformat(stamp[:-1] + "+00:00")
    except ValueError as exc:
        raise PolicyError("invalid QA/release UTC timestamp") from exc
    if result.utcoffset() != timedelta(0):
        raise PolicyError("non-UTC timestamp rejected")
    return result


def _read_small_file(path: Path, *, limit: int = 8192) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise PolicyError("invalid or unsafe attestation input")
    return path.read_bytes()


def validate_qa_attestation(raw: bytes, signature: bytes, qa_trust: Path,
                            *, now: datetime | None = None) -> tuple[dict, str]:
    """Authenticate an external QA keyholder's EXACT, time-bounded claim."""
    if len(raw) > 8192 or len(signature) != 64:
        raise PolicyError("oversized or malformed QA attestation")
    key = _public_key(qa_trust)
    try:
        key.verify(signature, raw)
    except (InvalidSignature, ValueError) as exc:
        raise PolicyError("independent QA signature invalid") from exc
    try:
        item = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise PolicyError("malformed QA JSON") from exc
    if (not isinstance(item, dict)
            or set(item) != set(EXPECTED_QA) | {"reviewed_utc", "qa_key_id"}
            or any(item.get(k) != v for k, v in EXPECTED_QA.items())
            or item["qa_key_id"] != key_id(key)
            or canonical_json(item) != raw):
        raise PolicyError("missing independent QA approval or incorrect evidence scope")
    review_time = _parse_date(item["reviewed_utc"])
    today = now if now is not None else datetime.now(timezone.utc)
    if (today.tzinfo is None or review_time > today + timedelta(minutes=5)
            or today - review_time > timedelta(days=30)):
        raise PolicyError("stale or future QA attestation")
    return item, key_id(key)


def publish_production(root: Path, owner_private: Path, qa_claim: Path,
                       qa_sig: Path, qa_trust: Path, output: Path,
                       *, serial: int, confirmation: str) -> Path:
    """Owner-invoked only, never called by a scheduler or PR workflow."""
    if confirmation != OWNER_CONFIRM:
        raise PolicyError("explicit owner production authorization missing")
    if type(serial) is not int or not 1 <= serial <= 10000000:
        raise PolicyError("invalid production serial")
    qa_raw = _read_small_file(Path(qa_claim))
    qa_signature = _read_small_file(Path(qa_sig), limit=256)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _, qa_id = validate_qa_attestation(qa_raw, qa_signature, Path(qa_trust), now=now)
    owner = _private_key(Path(owner_private))
    owner_id = key_id(owner.public_key())
    if owner_id == qa_id:
        raise PolicyError("independent QA and owner keys must be distinct")
    manifest = {
        "schema": SCHEMA, "channel": CHANNEL, "scope": SCOPE,
        "serial": serial,
        "created_utc": now.isoformat().replace("+00:00", "Z"),
        "expires_utc": (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "owner_key_id": owner_id, "qa_key_id": qa_id,
        "rule_sha256": digest(RULE_BYTES),
        "qa_claim_sha256": digest(qa_raw),
        "qa_signature_sha256": digest(qa_signature),
        "rule_count": 1, "production_approved": True,
        "deploy_allowed": True, "auto_apply": False,
    }
    man = canonical_json(manifest)
    owner_sig = owner.sign(man)
    target = _valid_outpath(Path(root), Path(output))
    fd, tmp = tempfile.mkstemp(
        dir=str(target.parent), prefix=".ucie_production_", suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as handle:
            with zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("manifest.json", man)
                z.writestr("rules/prevention.json", RULE_BYTES)
                z.writestr("qa/attestation.json", qa_raw)
                z.writestr("qa/attestation.sig", qa_signature)
                z.writestr("signatures/owner.sig", owner_sig)
        os.link(tmp, target)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return target


def verify_production(path: Path, owner_trust: Path, qa_trust: Path,
                      *, min_serial: int = 1,
                      at_time: datetime | None = None) -> dict:
    """Recipient-side independent QA+owner authenticated, no code execution."""
    if type(min_serial) is not int or min_serial < 1:
        raise PolicyError("invalid minimum serial")
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SIZE:
        raise PolicyError("invalid production archive")
    owner = _public_key(Path(owner_trust))
    qa = _public_key(Path(qa_trust))
    if key_id(owner) == key_id(qa):
        raise PolicyError("QA and production signer identities must differ")
    try:
        with zipfile.ZipFile(path) as z:
            info = z.infolist()
            names = [i.filename for i in info]
            if (len(names) != len(FILES) or set(names) != FILES
                    or any(i.file_size > MAX_SIZE or i.flag_bits & 1
                           or ((i.external_attr >> 16) & 0o170000) == 0o120000
                           for i in info)):
                raise PolicyError("unexpected or unsafe production archive")
            raw = {n: z.read(n) for n in names}
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise PolicyError("production archive read failed") from exc
    try:
        man = json.loads(raw["manifest.json"].decode("utf-8"))
        rule = json.loads(raw["rules/prevention.json"].decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise PolicyError("invalid production manifest") from exc
    keys = {"schema", "channel", "scope", "serial", "created_utc",
            "expires_utc", "owner_key_id", "qa_key_id", "rule_sha256",
            "qa_claim_sha256", "qa_signature_sha256", "rule_count",
            "production_approved", "deploy_allowed", "auto_apply"}
    if (not isinstance(man, dict) or set(man) != keys
            or canonical_json(man) != raw["manifest.json"]
            or man["schema"] != SCHEMA or man["channel"] != CHANNEL
            or man["scope"] != SCOPE or man["owner_key_id"] != key_id(owner)
            or man["qa_key_id"] != key_id(qa)
            or type(man["serial"]) is not int or man["serial"] < min_serial
            or man["rule_count"] != 1
            or man["production_approved"] is not True
            or man["deploy_allowed"] is not True
            or man["auto_apply"] is not False
            or rule != [PRODUCTION_RULE]
            or canonical_json(rule) != raw["rules/prevention.json"]
            or man["rule_sha256"] != digest(raw["rules/prevention.json"])
            or man["qa_claim_sha256"] != digest(raw["qa/attestation.json"])
            or man["qa_signature_sha256"] != digest(raw["qa/attestation.sig"])):
        raise PolicyError("unapproved release scope, serial, rules or hashes")
    try:
        owner.verify(raw["signatures/owner.sig"], raw["manifest.json"])
    except (InvalidSignature, ValueError) as exc:
        raise PolicyError("owner production signature invalid") from exc
    now = at_time or datetime.now(timezone.utc)
    start, expiry = _parse_date(man["created_utc"]), _parse_date(man["expires_utc"])
    if (now.tzinfo is None or start > now + timedelta(minutes=5)
            or now >= expiry or expiry <= start
            or expiry - start > timedelta(days=7)):
        raise PolicyError("expired or not-yet-valid production pack")
    validate_qa_attestation(
        raw["qa/attestation.json"], raw["qa/attestation.sig"],
        Path(qa_trust), now=now)
    return {
        "result": "DUAL_SIGNED_PUBLIC_PRODUCTION_RULEPACK_VERIFIED",
        "rule_id": RULE_ID, "serial": man["serial"],
        "owner_signature": "VALID", "independent_qa_signature": "VALID",
        "scope": SCOPE, "safe_guidance": PRODUCTION_RULE["safe_guidance"],
        "auto_apply": False, "production_approved": True, "deploy_allowed": True,
        "qualifier": "SIGNED_APPROVAL_ATTESTATIONS_NOT_INDEPENDENT_HUMAN_IDENTITY_PROOF",
    }
