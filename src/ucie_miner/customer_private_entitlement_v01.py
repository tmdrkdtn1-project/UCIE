"""UCIE C3/C4 full-product private customer ENTITLEMENT verifier, offline only.

This is NOT owner entitlement issuance, not an auto-approver, and never creates
or reads an owner private key. Existing pre-approved owner PUBLIC Ed25519
trust is supplied by an independent recipient. A cryptographic signature
can bind one anonymous recipient token to exact checked first-party and
three pinned vendor wheel digests, 4 pillars, rights-review receipt digest,
version, serial and expiry. Real legal rights/owner business/customer approval
remain separate, explicitly false. No service, installation, user data or
network is accessed by this module.

Purpose separation: PUBLIC PR C3 signatures and Rulepack/demo signatures
must NEVER be accepted as private customer product entitlements.
"""
from __future__ import annotations

from base64 import b64decode, b64encode
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re

from . import local_public_pr_owner_auth_v01 as owner_auth
from .customer_owner_wheelhouse_acquire_v01 import PINNED
from .customer_staging_v01 import PILLARS

SCHEMA = "UCIE_C3_DESIGNATED_CUSTOMER_FOUR_PILLAR_ENTITLEMENT_V01"
ATTESTATION_SCHEMA = "UCIE_C3_CUSTOMER_RELEASE_ENTITLEMENT_SIGNATURE_V01"
SCOPE = "UCIE_PRIVATE_DESIGNATED_CUSTOMER_COMPLETE_FOUR_PILLAR_PRODUCT"
DOMAIN = b"UCIE_C3_PRIVATE_FOUR_PILLAR_CUSTOMER_ENTITLEMENT_V01\x00"
MAX_RECORD = 3500
MAX_ATTESTATION = 1300
MAX_DAYS = 30
MAX_SERIAL = 2**31 - 1
SHA = re.compile(r"[a-f0-9]{64}\Z")
KEYID = re.compile(r"[a-f0-9]{32}\Z")
VERSION = "0.1.0"
DIST = "ucie-public-only-demo"
FIELDS = frozenset({
    "schema", "scope", "product", "product_version", "product_wheel_sha256",
    "vendor_wheels_sha256", "recipient_token_sha256", "rights_packet_sha256",
    "four_pillars", "serial", "owner_key_id", "issued_utc", "expires_utc",
})
SIG_FIELDS = frozenset({
    "schema", "scope", "payload_sha256", "owner_key_id", "algorithm",
    "signature_base64",
})


class PrivateEntitlementError(ValueError):
    """Signer identity, customer binding or release integrity not established."""


def _distinct(pairs: list[tuple[str, object]]) -> dict:
    if len({k for k, _ in pairs}) != len(pairs):
        raise PrivateEntitlementError("duplicate private entitlement field")
    return dict(pairs)


def canonical(value: dict) -> bytes:
    if type(value) is not dict:
        raise PrivateEntitlementError("entitlement must be an object")
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise PrivateEntitlementError("noncanonical entitlement fields") from exc


def _decode(raw: bytes, *, maximum: int) -> dict:
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        raise PrivateEntitlementError("invalid private entitlement length")
    try:
        obj = json.loads(
            raw.decode("ascii"), object_pairs_hook=_distinct,
            parse_constant=lambda _: (_ for _ in ()).throw(
                PrivateEntitlementError("nonfinite private entitlement")))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise PrivateEntitlementError("invalid private entitlement JSON") from exc
    if type(obj) is not dict or canonical(obj) != raw:
        raise PrivateEntitlementError("noncanonical private entitlement")
    return obj


def _hex64(value: object) -> bool:
    return type(value) is str and SHA.fullmatch(value) is not None


def verify_private_entitlement(
    record_bytes: bytes, signature_bytes: bytes,
    independently_provisioned_public_pem: bytes, *,
    expected_owner_key_id: str, min_serial: int,
    expected_recipient_token_sha256: str,
    expected_product_wheel_sha256: str,
    expected_vendor_wheels_sha256: dict[str, str],
    expected_rights_packet_sha256: str,
    now: datetime,
) -> dict:
    """Verify true Ed25519 and expected artifact hashes; NEVER authorize shipping.

    All expected values come from separate owner-recipient provisioning and
    checked actual artifacts, not self-asserted package claims. This function
    NEVER installs, signs, issues or accesses a private key.
    """
    if (not isinstance(now, datetime) or now.tzinfo is None
            or type(expected_owner_key_id) is not str
            or KEYID.fullmatch(expected_owner_key_id) is None
            or type(min_serial) is not int or not 1 <= min_serial <= MAX_SERIAL
            or not all(_hex64(x) for x in (
                expected_recipient_token_sha256, expected_product_wheel_sha256,
                expected_rights_packet_sha256))
            or type(expected_vendor_wheels_sha256) is not dict
            or set(expected_vendor_wheels_sha256) != {n for n, _ in PINNED}
            or not all(_hex64(v) for v in expected_vendor_wheels_sha256.values())
            or type(independently_provisioned_public_pem) is not bytes
            or not 0 < len(independently_provisioned_public_pem) <= owner_auth.MAX_PEM):
        raise PrivateEntitlementError("independent owner, wheel or recipient policy required")
    try:
        current = owner_auth._utc(now)
        record = _decode(record_bytes, maximum=MAX_RECORD)
        signature = _decode(signature_bytes, maximum=MAX_ATTESTATION)
        if set(record) != FIELDS or set(signature) != SIG_FIELDS:
            raise PrivateEntitlementError("unexpected private release entitlement fields")
        if (record["schema"] != SCHEMA or record["scope"] != SCOPE
                or record["product"] != DIST or record["product_version"] != VERSION
                or record["product_wheel_sha256"] != expected_product_wheel_sha256
                or record["recipient_token_sha256"] != expected_recipient_token_sha256
                or record["rights_packet_sha256"] != expected_rights_packet_sha256
                or record["four_pillars"] != list(PILLARS)
                or type(record["vendor_wheels_sha256"]) is not dict
                or record["vendor_wheels_sha256"] != expected_vendor_wheels_sha256
                or type(record["serial"]) is not int
                or not min_serial <= record["serial"] <= MAX_SERIAL
                or type(record["owner_key_id"]) is not str
                or record["owner_key_id"] != expected_owner_key_id):
            raise PrivateEntitlementError("wrong product, recipient, wheel or serial")
        if (signature["schema"] != ATTESTATION_SCHEMA
                or signature["scope"] != SCOPE
                or signature["algorithm"] != "Ed25519"
                or signature["owner_key_id"] != expected_owner_key_id
                or signature["payload_sha256"] != sha256(record_bytes).hexdigest()):
            raise PrivateEntitlementError("mismatched or wrong-purpose attestation")
        issued = owner_auth._parse_stamp(record["issued_utc"])
        expiry = owner_auth._parse_stamp(record["expires_utc"])
        if (expiry - issued != timedelta(days=MAX_DAYS)
                or issued > current + timedelta(minutes=5) or current > expiry):
            raise PrivateEntitlementError("entitlement issued in future or expired")
        encoded = signature["signature_base64"]
        if (type(encoded) is not str or owner_auth.B64.fullmatch(encoded) is None):
            raise PrivateEntitlementError("invalid detached Ed25519 signature encoding")
        sig = b64decode(encoded, validate=True)
        if len(sig) != 64 or b64encode(sig).decode("ascii") != encoded:
            raise PrivateEntitlementError("noncanonical Ed25519 signature")
        badsig, serialization, _, pubtype, get_key_id = owner_auth._crypto()
        pub = serialization.load_pem_public_key(independently_provisioned_public_pem)
        if (not isinstance(pub, pubtype)
                or get_key_id(pub) != expected_owner_key_id
                or pub.public_bytes(serialization.Encoding.PEM,
                                    serialization.PublicFormat.SubjectPublicKeyInfo)
                   != independently_provisioned_public_pem):
            raise PrivateEntitlementError("public owner key not independent expected identity")
        try:
            pub.verify(sig, DOMAIN + record_bytes)
        except badsig as exc:
            raise PrivateEntitlementError("private release signature invalid") from exc
    except (PrivateEntitlementError, owner_auth.OwnerMetadataAuthError):
        raise
    except (ValueError, TypeError, KeyError, UnicodeError, OSError) as exc:
        raise PrivateEntitlementError("untrusted release entitlement") from exc

    return {
        "schema": SCHEMA,
        "status": "CUSTOMER_ENTITLEMENT_CRYPTO_BOUND_TECHNICAL_ONLY_NO_GO",
        "release_serial": record["serial"],
        "product_version": VERSION,
        "product_wheel_sha256": expected_product_wheel_sha256,
        "vendor_wheel_count": len(PINNED),
        "four_pillars_bound": list(PILLARS),
        "private_product_ed25519_signature_verified": True,
        "expected_recipient_binding_matches": True,
        "expected_product_and_pinned_vendor_digests_match": True,
        "expiry_utc": record["expires_utc"],
        "owner_key_matches_independent_expected_pin": True,
        "out_of_band_owner_approval_independently_proven": False,
        "rights_packet_sha256_bound_but_legal_approval_not_proven": True,
        "independent_legal_and_notice_approval": False,
        "independent_customer_contract_approved": False,
        "real_owner_signing_proven": False,
        "actual_customer_machine_accepted": False,
        "customer_entitlement_issued": False,
        "customer_distribution_authorized": False,
        "keys_generated_or_private_material_accessed": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }


def synthetic_fixture_signing_bytes(record: dict, ephemeral_private: object) -> tuple[bytes, bytes]:
    """Test-only purpose-separated primitive. Not a production signer or key loader.

    Accepts caller-supplied in-memory key ONLY, no filesystem IO.
    No owner TTY/captured key path, no entitlement issued in customer service.
    """
    _, _, privtype, _, get_id = owner_auth._crypto()
    if not isinstance(ephemeral_private, privtype):
        raise PrivateEntitlementError("synthetic Ed25519 key object required")
    body = canonical(record)
    if len(body) > MAX_RECORD or record.get("owner_key_id") != get_id(ephemeral_private.public_key()):
        raise PrivateEntitlementError("invalid synthetic owner-key binding")
    sig = ephemeral_private.sign(DOMAIN + body)
    detached = canonical({
        "schema": ATTESTATION_SCHEMA, "scope": SCOPE,
        "algorithm": "Ed25519", "owner_key_id": record["owner_key_id"],
        "payload_sha256": sha256(body).hexdigest(),
        "signature_base64": b64encode(sig).decode("ascii"),
    })
    return body, detached
