"""Independent-process, read-only consumer of an existing UCIE W09 manual reference.

The caller-provided JSON is untrusted. Revalidate original signed Rulepack,
public owner trust, expiry, exact rule identity and W09 descriptor in THIS
process before returning a non-executable manual-scope consumption receipt.
No source scanning, auto-application, network, pack export, or DB writes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

from .signed_rule_library import (
    SignedLibraryError, build_existing_pack_consumer_descriptor,
)

SCHEMA = "UCIE_V1_MANUAL_W09_CONSUMER_REVERIFICATION_V1"
MAX_INPUT_BYTES = 4096
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
INPUT_KEYS = frozenset({
    "schema", "status", "selected_library_item_id", "rule_id", "pack_serial",
    "source_package_sha256", "parent_serial4_sha256",
    "existing_w09_descriptor_sha256", "original_pack_reverified_at_handoff",
    "consumer_instruction", "manual_scope", "approval_basis",
    "independent_qa_approved", "legal_license_signoff",
    "consumer_signature_verified_after_handoff",
    "new_generic_package_export_allowed", "automatic_rule_application_allowed",
    "source_code_executed", "pack_bytes_copied", "new_signature_created",
    "network_requests", "operating_database_writes", "package_released",
    "v1_accepted",
})


class ManualConsumerError(ValueError):
    pass


def _canonical(data: dict) -> bytes:
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def consume_existing_manual_reference(
    root: Path, *, reference: dict, serial4_pack: Path,
    owner_public_trust: Path, serial5_pack: Path | None = None,
) -> dict:
    """Reverify original W09 and match a single reference exactly.

    No time override is exposed: original signature expiry is checked now.
    The returned record is a manual *read* of signed rule identity, NOT
    proof of safe applicability, rule execution, or distributable licensing.
    """
    if (type(reference) is not dict or set(reference) != INPUT_KEYS
            or type(reference["selected_library_item_id"]) is not str
            or HEX64.fullmatch(reference["selected_library_item_id"]) is None):
        raise ManualConsumerError("invalid bounded W09 selection reference")
    try:
        descriptor = build_existing_pack_consumer_descriptor(
            root, serial4_pack=serial4_pack,
            owner_public_trust=owner_public_trust, serial5_pack=serial5_pack)
    except (SignedLibraryError, ValueError, OSError) as exc:
        raise ManualConsumerError("original signed W09 verification required") from exc
    if (descriptor.get("schema") !=
            "UCIE_W09_EXISTING_OWNER_PACK_CONSUMER_DESCRIPTOR_V1"
            or descriptor.get("status") !=
            "READ_ONLY_REFERENCE_DESCRIPTOR_NOT_A_NEW_RELEASE"
            or descriptor.get("package_type") !=
            "REFERENCE_TO_EXISTING_SIGNED_RULEPACKS_ONLY"
            or descriptor.get("new_package_export_allowed") is not False
            or descriptor.get("new_signature_or_approval_created") is not False
            or descriptor.get("existing_manual_pack_distribution_scope_unchanged")
               is not True
            or descriptor.get("network_requests") != 0
            or descriptor.get("database_writes") != 0
            or type(descriptor.get("rules")) is not list
            or type(descriptor.get("source_pack_sha256s")) is not dict
            or type(descriptor.get("descriptor_sha256")) is not str
            or HEX64.fullmatch(descriptor["descriptor_sha256"]) is None):
        raise ManualConsumerError("W09 descriptor is not a manual-scope reference")
    if sha256(_canonical({
            k: v for k, v in descriptor.items() if k != "descriptor_sha256"
    })).hexdigest() != descriptor["descriptor_sha256"]:
        raise ManualConsumerError("W09 canonical descriptor digest mismatch")

    matching = [row for row in descriptor["rules"] if
                type(row) is dict
                and row.get("item_id") == reference["selected_library_item_id"]]
    if len(matching) != 1:
        raise ManualConsumerError("exact verified signed rule not found")
    record = matching[0]
    if (record.get("pack_serial") not in (4, 5)
            or type(record["pack_serial"]) is not int
            or record.get("approval_basis") != "OWNER_RISK_ACCEPTED_CI_ONLY"
            or record.get("independent_qa_approved") is not False
            or type(record.get("rule_id")) is not str):
        raise ManualConsumerError("verified owner-risk manual scope required")
    hashes = descriptor["source_pack_sha256s"]
    pack_key = "serial5_addendum" if record["pack_serial"] == 5 else "serial4"
    if (type(hashes.get(pack_key)) is not str
            or HEX64.fullmatch(hashes[pack_key]) is None
            or type(hashes.get("serial4")) is not str
            or HEX64.fullmatch(hashes["serial4"]) is None):
        raise ManualConsumerError("W09 source-pack identity absent")

    # Reconstruct producer's exact, intentionally non-authorizing shape.
    # A forged approval, changed parent, different pack or extra field is
    # rejected even when the selected ID points to a genuine signed rule.
    expected = {
        "schema": "UCIE_V1_SELECTED_EXISTING_W09_MANUAL_CONSUMER_REFERENCE_V1",
        "status": "EXISTING_SIGNED_MANUAL_REFERENCE_VERIFIED_NOT_RELEASED",
        "selected_library_item_id": record["item_id"],
        "rule_id": record["rule_id"],
        "pack_serial": record["pack_serial"],
        "source_package_sha256": hashes[pack_key],
        "parent_serial4_sha256": hashes["serial4"],
        "existing_w09_descriptor_sha256": descriptor["descriptor_sha256"],
        "original_pack_reverified_at_handoff": True,
        "consumer_instruction": descriptor["consumer_instructions"],
        "manual_scope": descriptor["approval_scope"],
        "approval_basis": "OWNER_RISK_ACCEPTED_CI_ONLY",
        "independent_qa_approved": False,
        "legal_license_signoff": False,
        "consumer_signature_verified_after_handoff": False,
        "new_generic_package_export_allowed": False,
        "automatic_rule_application_allowed": False,
        "source_code_executed": False,
        "pack_bytes_copied": False,
        "new_signature_created": False,
        "network_requests": 0, "operating_database_writes": 0,
        "package_released": False, "v1_accepted": False,
    }
    if reference != expected:
        raise ManualConsumerError("handed-off reference does not match verified originals")
    return {
        "schema": SCHEMA,
        "status": "ORIGINAL_SIGNED_RULE_REVERIFIED_MANUAL_REFERENCE_ONLY",
        "selected_library_item_id": record["item_id"],
        "rule_id": record["rule_id"],
        "pack_serial": record["pack_serial"],
        "source_pack_sha256": hashes[pack_key],
        "parent_serial4_sha256": hashes["serial4"],
        "w09_descriptor_sha256": descriptor["descriptor_sha256"],
        "handoff_reference_sha256": sha256(_canonical(reference)).hexdigest(),
        "original_signature_trust_and_expiry_reverified_in_consumer": True,
        "manual_scope": descriptor["approval_scope"],
        "owner_risk_only": True,
        "consumer_action": "INSPECT_EXISTING_SIGNED_RULE_IDENTITY_ONLY",
        "actual_rule_scan_executed": False,
        "runtime_version_applicability_verified": False,
        "independent_qa_approved": False,
        "legal_license_signoff": False,
        "new_generic_package_export_allowed": False,
        "automatic_rule_application_allowed": False,
        "pack_bytes_copied": False,
        "external_project_files_read": False,
        "network_requests": 0, "operating_database_writes": 0,
        "new_signature_created": False,
        "package_released": False, "v1_accepted": False,
    }


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise ManualConsumerError("duplicate reference JSON field")
        out[key] = value
    return out


def _invalid_constant(value: str) -> None:
    raise ManualConsumerError("nonfinite reference JSON value")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently reverify an existing W09 manual reference, stdin JSON")
    parser.add_argument("--ucie-root", type=Path, required=True)
    parser.add_argument("--serial4-pack", type=Path, required=True)
    parser.add_argument("--owner-public-trust", type=Path, required=True)
    parser.add_argument("--serial5-pack", type=Path)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if not raw or len(raw) > MAX_INPUT_BYTES:
            raise ManualConsumerError("bounded reference JSON required")
        ref = json.loads(raw.decode("utf-8", errors="strict"),
                         object_pairs_hook=_unique_pairs,
                         parse_constant=_invalid_constant)
        receipt = consume_existing_manual_reference(
            args.ucie_root, reference=ref,
            serial4_pack=args.serial4_pack,
            owner_public_trust=args.owner_public_trust,
            serial5_pack=args.serial5_pack)
    except (ManualConsumerError, SignedLibraryError, UnicodeError,
            ValueError, OSError, TypeError, KeyError, OverflowError):
        print(json.dumps({
            "schema": SCHEMA, "status": "MANUAL_CONSUMER_FAIL_CLOSED",
            "original_signature_reverified": False,
            "new_generic_package_export_allowed": False,
            "automatic_rule_application_allowed": False,
            "network_requests": 0, "operating_database_writes": 0,
            "package_released": False, "v1_accepted": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
