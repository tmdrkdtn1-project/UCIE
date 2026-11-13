"""UCIE C3: bounded Ed25519 owner-authentication for PUBLIC-ONLY PR metadata.

Not a customer signature, release approval, or independent upstream source
verification. Reuse UCIE's existing Ed25519 Rulepack crypto primitives, but
NEVER generate/read a real owner key automatically or ship a trust anchor.

The owner's private key is only accessed by an explicitly owner-invoked,
interactive, exact-path, no-overwrite Windows action after a separately
approved public capsule already exists. Public recipient verification requires
an expected key fingerprint and minimum serial supplied OUT OF BAND, not
copied from the attacker-controlled capsule/attestation itself.

Module import remains stdlib-only so the existing clean Windows first-party
no-vendor install keeps working; crypto is fail-closed when not installed.
"""
from __future__ import annotations

import argparse
from base64 import b64decode, b64encode
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from .local_public_pr_capsule_v01 import (
    FILE as CAPSULE_FILE, PIN as CAPSULE_PIN, MAX_BYTES as CAPSULE_MAX_BYTES,
    _canonical as canonical_capsule, inspect_capsule,
)

SCHEMA = "UCIE_C3_PUBLIC_PR_METADATA_OWNER_ED25519_ATTESTATION_V01"
STATUS = "OWNER_AUTHENTICATED_PUBLIC_METADATA_ONLY_REVIEW_NOT_RELEASE"
VERIFY_STATUS = "OWNER_KEY_AUTHENTICATED_CAPSULE_UPSTREAM_NOT_REVERIFIED_NO_GO"
SIGN_CONSENT = "UCIE_OWNER_SIGN_PUBLIC_METADATA_LOCAL_ONLY_ONCE"
SCOPE = "UCIE_PUBLIC_PR_METADATA_REVIEW_ONLY"
DOMAIN = b"UCIE_C3_OWNER_PUBLIC_PR_METADATA_V01\x00"
SIGNATURE_FILE = ".ucie_c3_public_pr_owner_attestation_v01.json"
PRIVATE_NAME = "ucie_c3_public_metadata_owner_private.pem"
TRUST_NAME = "ucie_c3_public_metadata_owner_trust.pem"
MAX_ATTESTATION = 1800
MAX_PEM = 8192
MAX_DAYS = 30
MAX_SERIAL = 2**31 - 1
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
KEYID = re.compile(r"[a-f0-9]{32}\Z")
B64 = re.compile(r"[A-Za-z0-9+/]{86}==\Z")
CORE_KEYS = frozenset((
    "schema", "status", "scope", "algorithm", "capsule_sha256",
    "owner_key_id", "serial", "issued_utc", "expires_utc",
))
ALL_KEYS = CORE_KEYS | {"signature_base64"}


class OwnerMetadataAuthError(ValueError):
    """Untrusted signature, key scope, time, or owner-gate violation."""


def _canonical(value: object) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    except (ValueError, TypeError, UnicodeError) as exc:
        raise OwnerMetadataAuthError("invalid canonical owner metadata") from exc


def _distinct(pairs: list[tuple[str, Any]]) -> dict:
    if len({key for key, _ in pairs}) != len(pairs):
        raise OwnerMetadataAuthError("duplicate owner attestation field")
    return dict(pairs)


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise OwnerMetadataAuthError("timezone-aware UTC time required")
    try:
        result = value.astimezone(timezone.utc)
    except (OSError, ValueError) as exc:
        raise OwnerMetadataAuthError("invalid UTC timestamp") from exc
    if result.utcoffset() != timedelta(0):
        raise OwnerMetadataAuthError("invalid UTC offset")
    return result


def _stamp(value: datetime) -> str:
    return _utc(value).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_stamp(value: object) -> datetime:
    if type(value) is not str or not re.fullmatch(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value):
        raise OwnerMetadataAuthError("noncanonical UTC attestation time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OwnerMetadataAuthError("invalid attestation time") from exc
    if _stamp(parsed) != value:
        raise OwnerMetadataAuthError("attestation UTC timestamp changed")
    return parsed


def _crypto():
    """Reuse existing UCIE Ed25519 code. Never silently downgrade to SHA."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey, Ed25519PublicKey,
        )
        from ucie_public.rulepack import key_id
        return InvalidSignature, serialization, Ed25519PrivateKey, Ed25519PublicKey, key_id
    except (ImportError, OSError) as exc:
        raise OwnerMetadataAuthError(
            "reviewed native Ed25519 verifier unavailable; fail closed") from exc


def sign_metadata_bytes(capsule_bytes: bytes, owner_private_key: object, *,
                        serial: int, issued_at: datetime, consent: str) -> bytes:
    """Explicit synthetic/owner signature; no path IO or key generation.

    Signature proves only keyholder possession, NOT actual human review,
    upstream PR truth, redistributability or customer release permission.
    """
    if consent != SIGN_CONSENT:
        raise OwnerMetadataAuthError("separate owner metadata consent missing")
    if type(serial) is not int or not 1 <= serial <= MAX_SERIAL:
        raise OwnerMetadataAuthError("invalid bounded owner metadata serial")
    if type(capsule_bytes) is not bytes or len(capsule_bytes) > CAPSULE_MAX_BYTES:
        raise OwnerMetadataAuthError("invalid metadata payload")
    digest = sha256(capsule_bytes).hexdigest()
    inspected = inspect_capsule(capsule_bytes, digest)
    if inspected["customer_distribution_authorized"] is not False:
        raise OwnerMetadataAuthError("capsule attempted customer release")
    _, _, private_type, _, key_id = _crypto()
    if not isinstance(owner_private_key, private_type):
        raise OwnerMetadataAuthError("not a dedicated Ed25519 private key")
    date = _utc(issued_at)
    public = owner_private_key.public_key()
    core = {
        "schema": SCHEMA,
        "status": STATUS,
        "scope": SCOPE,
        "algorithm": "Ed25519",
        "capsule_sha256": digest,
        "owner_key_id": key_id(public),
        "serial": serial,
        "issued_utc": _stamp(date),
        "expires_utc": _stamp(date + timedelta(days=MAX_DAYS)),
    }
    signature = owner_private_key.sign(DOMAIN + _canonical(core))
    if len(signature) != 64:
        raise OwnerMetadataAuthError("bad Ed25519 signature length")
    envelope = {**core, "signature_base64": b64encode(signature).decode("ascii")}
    packed = _canonical(envelope)
    if len(packed) > MAX_ATTESTATION:
        raise OwnerMetadataAuthError("oversized metadata attestation")
    return packed


def verify_owner_metadata_bytes(capsule_bytes: bytes, attestation: bytes,
                                trusted_public_key_pem: bytes, *,
                                expected_owner_key_id: str,
                                min_serial: int,
                                now: datetime) -> dict:
    """Independent recipient key pin + serial floor + expiration required.

    expected_owner_key_id and min_serial MUST come from an authenticated
    out-of-band owner provisioning/acceptance, not this attestation, package,
    adjacent hash or network. A valid signature authenticates key possession
    only; no upstream origin, legal, QA or customer GO is inferred.
    """
    if (type(expected_owner_key_id) is not str
            or KEYID.fullmatch(expected_owner_key_id) is None
            or type(min_serial) is not int
            or not 1 <= min_serial <= MAX_SERIAL
            or type(trusted_public_key_pem) is not bytes
            or not 0 < len(trusted_public_key_pem) <= MAX_PEM
            or type(attestation) is not bytes
            or not 0 < len(attestation) <= MAX_ATTESTATION):
        raise OwnerMetadataAuthError("untrusted owner key pin or signature size")
    date = _utc(now)
    try:
        raw = json.loads(attestation.decode("ascii"), object_pairs_hook=_distinct,
                         parse_constant=lambda _: (_ for _ in ()).throw(
                             OwnerMetadataAuthError("nonfinite attestation")))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise OwnerMetadataAuthError("invalid owner signature JSON") from exc
    if type(raw) is not dict or set(raw) != ALL_KEYS or _canonical(raw) != attestation:
        raise OwnerMetadataAuthError("noncanonical or unexpected owner attestation")
    core = {k: raw[k] for k in CORE_KEYS}
    if (raw["schema"] != SCHEMA or raw["status"] != STATUS
            or raw["scope"] != SCOPE or raw["algorithm"] != "Ed25519"
            or type(raw["capsule_sha256"]) is not str
            or HEX64.fullmatch(raw["capsule_sha256"]) is None
            or type(raw["owner_key_id"]) is not str
            or raw["owner_key_id"] != expected_owner_key_id
            or type(raw["serial"]) is not int
            or not min_serial <= raw["serial"] <= MAX_SERIAL):
        raise OwnerMetadataAuthError("forged scope, metadata version, key or serial")
    if (type(capsule_bytes) is not bytes
            or not 0 < len(capsule_bytes) <= CAPSULE_MAX_BYTES
            or sha256(capsule_bytes).hexdigest() != raw["capsule_sha256"]):
        raise OwnerMetadataAuthError("signed data digest mismatched")
    inspected = inspect_capsule(capsule_bytes, raw["capsule_sha256"])
    if inspected["signature_verified"] is not False:
        raise OwnerMetadataAuthError("capsule forged a signature state")
    issued, expiry = _parse_stamp(raw["issued_utc"]), _parse_stamp(raw["expires_utc"])
    if (expiry - issued != timedelta(days=MAX_DAYS)
            or issued > date + timedelta(minutes=5)
            or date > expiry):
        raise OwnerMetadataAuthError("future, expired or inconsistent attestation")
    signature_field = raw["signature_base64"]
    if type(signature_field) is not str or B64.fullmatch(signature_field) is None:
        raise OwnerMetadataAuthError("malformed Ed25519 signature encoding")
    try:
        signature = b64decode(signature_field, validate=True)
    except ValueError as exc:
        raise OwnerMetadataAuthError("invalid signature encoding") from exc
    if len(signature) != 64 or b64encode(signature).decode("ascii") != signature_field:
        raise OwnerMetadataAuthError("Ed25519 signature is not canonical")
    bad_sig, serialization, _, public_type, key_id = _crypto()
    try:
        public = serialization.load_pem_public_key(trusted_public_key_pem)
    except (ValueError, TypeError) as exc:
        raise OwnerMetadataAuthError("invalid independent owner trust key") from exc
    if (not isinstance(public, public_type)
            or key_id(public) != expected_owner_key_id
            or public.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo)
                != trusted_public_key_pem):
        raise OwnerMetadataAuthError("trusted public key not the exact pinned owner key")
    try:
        public.verify(signature, DOMAIN + _canonical(core))
    except (bad_sig, ValueError) as exc:
        raise OwnerMetadataAuthError("owner Ed25519 signature invalid") from exc
    return {
        "schema": SCHEMA,
        "status": VERIFY_STATUS,
        "owner_key_id": expected_owner_key_id,
        "metadata_capsule_sha256": raw["capsule_sha256"],
        "signed_serial": raw["serial"],
        "expiry_utc": raw["expires_utc"],
        "signed_metadata_only": True,
        "signature_cryptographically_verified": True,
        "owner_public_key_matches_supplied_trust_pin": True,
        "out_of_band_owner_approval_independently_proven": False,
        "source_linkage_independently_attested_on_recipient": False,
        "independent_upstream_fix_verified": False,
        "human_approved": False,
        "license_cleared": False,
        "customer_distribution_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }


def _safe_small(path: Path, *, max_bytes: int) -> bytes:
    if (not isinstance(path, Path) or path.is_symlink()
            or path.parent.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= max_bytes):
        raise OwnerMetadataAuthError("expected exact local owner file unavailable")
    raw = path.read_bytes()
    if not 0 < len(raw) <= max_bytes:
        raise OwnerMetadataAuthError("owner file mutated during verification")
    return raw


def sign_existing_owner_local_once(root: Path, *, serial: int,
                                   expected_owner_key_id: str,
                                   consent: str) -> dict:
    """Not a general file signer; requires actual owner D:/UCIE + interactive TTY.

    Never creates a key, reads outside the fixed UCIE .build_keys path,
    exports to GitHub, installs a runtime, or calls a collector.
    """
    if consent != SIGN_CONSENT:
        raise OwnerMetadataAuthError("separate owner signature consent missing")
    expected = Path("D:/UCIE")
    try:
        if (not isinstance(root, Path) or root.resolve(strict=True) !=
                expected.resolve(strict=True)
                or os.name != "nt"
                or Path(sys.executable).resolve(strict=True) != (
                    root / ".venv" / "Scripts" / "python.exe").resolve(strict=True)
                or sys.implementation.name != "cpython"
                or sys.version_info[:2] != (3, 15)
                or not sys.stdin.isatty()
                or bool(os.environ.get("CI"))
                or root.is_symlink() or (root / ".git").is_symlink()
                or not (root / ".git").is_dir()):
            raise OwnerMetadataAuthError("real owner interactive Windows UCIE only")
    except (OSError, RuntimeError) as exc:
        raise OwnerMetadataAuthError("real owner UCIE path not available") from exc
    if type(expected_owner_key_id) is not str or KEYID.fullmatch(expected_owner_key_id) is None:
        raise OwnerMetadataAuthError("owner key fingerprint must be pre-approved")
    out = root / "downloaded"
    private = root / ".build_keys" / PRIVATE_NAME
    if (out.is_symlink() or not out.is_dir()
            or private.parent.is_symlink() or not private.parent.is_dir()):
        raise OwnerMetadataAuthError("fixed private key or ignored output unavailable")
    # The real owner capsule lives under downloaded, while reader expects a
    # clean recipient root. Perform the exact same bytes/hash verification
    # directly instead of routing the owner's operating root to recipient.
    src, pin, signed = out / CAPSULE_FILE, out / CAPSULE_PIN, out / SIGNATURE_FILE
    if signed.exists() or signed.is_symlink():
        raise OwnerMetadataAuthError("metadata signature already exists; no overwrite")
    payload = _safe_small(src, max_bytes=CAPSULE_MAX_BYTES)
    receipt = _safe_small(pin, max_bytes=65)
    if len(receipt) != 65 or receipt[-1:] != b"\n":
        raise OwnerMetadataAuthError("owner metadata SHA receipt invalid")
    if sha256(payload).hexdigest() != receipt[:64].decode("ascii"):
        raise OwnerMetadataAuthError("owner public capsule and SHA do not match")
    inspect_capsule(payload, sha256(payload).hexdigest())
    _, serialization, private_type, _, key_id = _crypto()
    pem = _safe_small(private, max_bytes=MAX_PEM)
    try:
        priv = serialization.load_pem_private_key(pem, password=None)
    except (ValueError, TypeError) as exc:
        raise OwnerMetadataAuthError("dedicated owner metadata key not usable") from exc
    if (not isinstance(priv, private_type)
            or key_id(priv.public_key()) != expected_owner_key_id):
        raise OwnerMetadataAuthError("owner private key not independently pre-pinned")
    signed_bytes = sign_metadata_bytes(
        payload, priv, serial=serial,
        issued_at=datetime.now(timezone.utc), consent=consent)
    # sign once ONLY; no rollback/overwrite and never print private key bytes.
    fd = os.open(signed, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fp:
        fp.write(signed_bytes)
    return {
        "schema": SCHEMA,
        "status": "OWNER_LOCAL_ONLY_SIGNED_METADATA_CREATED_NOT_RELEASED",
        "attestation_file": "downloaded/" + SIGNATURE_FILE,
        "owner_key_id": expected_owner_key_id,
        "signature_serial": serial,
        "source_metadata_sha256": sha256(payload).hexdigest(),
        "private_key_exported": False,
        "files_uploaded": False,
        "customer_distribution_authorized": False,
        "operating_database_writes": 0,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="UCIE C3 public metadata signature verifier")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify-recipient", action="store_true")
    mode.add_argument("--owner-sign-once", action="store_true")
    ap.add_argument("--expected-owner-key-id", required=True)
    ap.add_argument("--min-serial", type=int)
    ap.add_argument("--serial", type=int)
    ap.add_argument("--recipient-ucie-root", type=Path)
    args = ap.parse_args(argv)
    # Installed-wheel verifier needs a separately designated recipient UCIE
    # checkout. Owner signing never accepts a user-selected root.
    root = (args.recipient_ucie_root if args.verify_recipient
            else Path(__file__).resolve().parents[2])
    from .local_public_pr_capsule_v01 import _root as checked_root
    try:
        checked_root(root)
        if args.owner_sign_once:
            if (args.recipient_ucie_root is not None
                    or args.min_serial is not None or args.serial is None):
                raise OwnerMetadataAuthError("owner serial or mode invalid")
            consent = input("Separate UCIE C3 metadata signature consent: ").strip()
            result = sign_existing_owner_local_once(
                root, serial=args.serial,
                expected_owner_key_id=args.expected_owner_key_id,
                consent=consent)
        else:
            if (args.serial is not None or args.min_serial is None
                    or args.recipient_ucie_root is None
                    or not args.recipient_ucie_root.is_absolute()):
                raise OwnerMetadataAuthError("absolute UCIE recipient root and minimum serial required")
            # Independent trust key provisioned through dedicated ignored area.
            # Key-ID and floor are passed by owner OUT OF BAND, never read
            # from the copied capsule or signature.
            pem = _safe_small(root / ".build_keys" / TRUST_NAME,
                              max_bytes=MAX_PEM)
            data = _safe_small(root / CAPSULE_FILE, max_bytes=CAPSULE_MAX_BYTES)
            signature = _safe_small(root / SIGNATURE_FILE,
                                    max_bytes=MAX_ATTESTATION)
            result = verify_owner_metadata_bytes(
                data, signature, pem,
                expected_owner_key_id=args.expected_owner_key_id,
                min_serial=args.min_serial,
                now=datetime.now(timezone.utc))
    except (ValueError, OSError, EOFError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "C3_OWNER_METADATA_FAIL_CLOSED_NO_GO",
            "safe_error_type": type(exc).__name__,
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
