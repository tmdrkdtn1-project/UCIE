"""W07 + first W09 slice: read-only signed Rulepack Virtual Library shelf.

There is no trust in manifest strings, PR rows, user-supplied 'verified'
receipts, or approval flags. Read genuine existing UCIE signed packages only
through the original Serial4 and Serial5 cryptographic verifiers, including
scope, expiry, owner trust key and the fifth addendum parent SHA pin.

This module DOES NOT sign, issue, repackage, export, execute, install, or
touch consumer project source. W09 is a non-executable reference descriptor to
the *existing verified packs*, not a newly approved general-purpose skill.
"""
from __future__ import annotations

from datetime import datetime
import argparse
import hashlib
import json
from pathlib import Path
import re

from ucie_public.policy import PolicyError
from ucie_public.mixed_release import verify_mixed_owner_release, RULE_ORDER
from ucie_public.fifth_owner_addendum import verify_fifth_addendum, RULE_ID
from ucie_public.production_release import SCOPE

SCHEMA = "UCIE_W07_W09_VERIFIED_RULEPACK_LIBRARY_V1"
MAX_PACK_BYTES = 131072
ALLOWED_RULES = frozenset((*RULE_ORDER, RULE_ID))
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class SignedLibraryError(ValueError):
    pass


def _ucie_file(root: Path, path: Path, *, max_size: int) -> Path:
    """Caller has to explicitly supply paths inside the dedicated UCIE root."""
    if not isinstance(path, Path) or not isinstance(root, Path):
        raise SignedLibraryError("UCIE file paths must be explicit Path values")
    if root.is_symlink() or not root.is_dir() or root.name.casefold() != "ucie":
        raise SignedLibraryError("dedicated UCIE checkout required")
    if path.is_symlink() or not path.is_file():
        raise SignedLibraryError("missing or unsafe signed package or trust file")
    absolute_root, absolute_file = root.resolve(), path.resolve()
    if not absolute_file.is_relative_to(absolute_root):
        raise SignedLibraryError("file is outside the dedicated UCIE checkout")
    size = path.stat().st_size
    if size < 1 or size > max_size:
        raise SignedLibraryError("bounded UCIE artifact required")
    return path


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_verified_receipts(base: dict, fifth: dict | None) -> None:
    if (type(base) is not dict or base.get("result") != "MIXED_OWNER_PUBLIC_MANUAL_PACK_VERIFIED"
            or base.get("owner_signature") != "VALID"
            or base.get("serial") != 4 or base.get("rule_ids") != list(RULE_ORDER)
            or base.get("rule_count") != 4 or base.get("scope") != SCOPE
            or base.get("auto_apply") is not False
            or base.get("independent_human_qa_approved") is not False
            or base.get("legal_license_signoff") is not False):
        raise SignedLibraryError("Serial4 full original verifier result required")
    if fifth is None:
        return
    if (type(fifth) is not dict
            or fifth.get("result") != "FIFTH_OWNER_RISK_ADDENDUM_VERIFIED"
            or fifth.get("serial") != 5 or fifth.get("parent_serial") != 4
            or fifth.get("parent_rule_count") != 4
            or fifth.get("additional_signed_rules") != 1
            or fifth.get("rule_id") != RULE_ID
            or fifth.get("scope") != SCOPE
            or fifth.get("owner_signature") != "VALID"
            or fifth.get("auto_apply") is not False
            or fifth.get("independent_human_qa_approved") is not False
            or fifth.get("legal_license_signoff") is not False):
        raise SignedLibraryError("exact verified Serial5 addendum required")


def inspect_signed_library(root: Path, *, serial4_pack: Path,
                           owner_public_trust: Path,
                           serial5_pack: Path | None = None,
                           at_time: datetime | None = None) -> dict:
    """Reverify original signed packs at query time before exposing rule IDs.

    User provides existing pack and owner PUBLIC trust path; private signing
    key is never accessed. Existing signoffs stay qualified as owner-risk.
    """
    original = _ucie_file(root, serial4_pack, max_size=MAX_PACK_BYTES)
    pub = _ucie_file(root, owner_public_trust, max_size=8192)
    addendum = (_ucie_file(root, serial5_pack, max_size=MAX_PACK_BYTES)
                if serial5_pack is not None else None)
    try:
        base = verify_mixed_owner_release(
            original, pub, min_serial=4, at_time=at_time)
        fifth = (verify_fifth_addendum(
            addendum, original, pub, min_serial=5, at_time=at_time)
                 if addendum is not None else None)
    except (PolicyError, OSError, ValueError) as exc:
        raise SignedLibraryError("signed owner Rulepack verification failed") from exc
    _valid_verified_receipts(base, fifth)
    records = []
    hashes = {"serial4": _digest(original)}
    if addendum is not None:
        hashes["serial5_addendum"] = _digest(addendum)
    for rule_id in RULE_ORDER:
        records.append({
            "item_id": hashlib.sha256(
                (rule_id + ":" + hashes["serial4"]).encode("ascii")
            ).hexdigest(),
            "kind": "PREVENTION_RULE",
            "rule_id": rule_id,
            "pack_serial": 4,
            "source_package_sha256": hashes["serial4"],
            "verification": "OWNER_SIGNED_VERIFIED_AT_INSPECTION_TIME",
            "approval_basis": "OWNER_RISK_ACCEPTED_CI_ONLY",
            "independent_qa_approved": False,
            "license_signoff": False,
            "signed_pack_manual_scope": SCOPE,
            "unattended_execution_allowed": False,
            "new_package_export_allowed": False,
        })
    if fifth is not None:
        records.append({
            "item_id": hashlib.sha256(
                (RULE_ID + ":" + hashes["serial5_addendum"]).encode("ascii")
            ).hexdigest(),
            "kind": "PREVENTION_RULE",
            "rule_id": RULE_ID,
            "pack_serial": 5,
            "parent_serial": 4,
            "source_package_sha256": hashes["serial5_addendum"],
            "parent_package_sha256": hashes["serial4"],
            "verification": "OWNER_SIGNED_VERIFIED_AT_INSPECTION_TIME",
            "approval_basis": "OWNER_RISK_ACCEPTED_CI_ONLY",
            "independent_qa_approved": False,
            "license_signoff": False,
            "signed_pack_manual_scope": SCOPE,
            "unattended_execution_allowed": False,
            "new_package_export_allowed": False,
        })
    if len(records) != len(set(x["rule_id"] for x in records)):
        raise SignedLibraryError("duplicate signed rule identity")
    return {
        "schema": SCHEMA,
        "status": "EXISTING_OWNER_SIGNED_RULEPACKS_VERIFIED_READ_ONLY",
        "signed_rule_count": len(records),
        "source_pack_sha256s": hashes,
        "items": records,
        "unsigned_candidate_records_imported": 0,
        "source_code_executed": False,
        "private_signing_key_accessed": False,
        "other_project_sources_accessed": False,
        "network_requests": 0,
        "database_writes": 0,
        "new_signatures_created": 0,
        "new_release_approved": False,
        "v1_library_accepted": False,
    }


def build_existing_pack_consumer_descriptor(root: Path, *,
                                            serial4_pack: Path,
                                            owner_public_trust: Path,
                                            serial5_pack: Path | None = None,
                                            at_time: datetime | None = None) -> dict:
    """W09: a machine-readable package *reference*, never a new signed ZIP.

    In-process cryptographic verification must run immediately before use.
    No plain/untrusted receipt can produce a descriptor.
    """
    signed = inspect_signed_library(
        root, serial4_pack=serial4_pack, owner_public_trust=owner_public_trust,
        serial5_pack=serial5_pack, at_time=at_time)
    payload = {
        "schema": "UCIE_W09_EXISTING_OWNER_PACK_CONSUMER_DESCRIPTOR_V1",
        "package_type": "REFERENCE_TO_EXISTING_SIGNED_RULEPACKS_ONLY",
        "approval_scope": SCOPE,
        "source_pack_sha256s": signed["source_pack_sha256s"],
        "rules": [
            {"rule_id": row["rule_id"], "pack_serial": row["pack_serial"],
             "item_id": row["item_id"],
             "approval_basis": row["approval_basis"],
             "independent_qa_approved": False}
            for row in signed["items"]
        ],
        "consumer_instructions": "VERIFY_ORIGINAL_PACK_SIGNATURE_EXPIRY_AND_OWNER_TRUST_EACH_USE",
        "status": "READ_ONLY_REFERENCE_DESCRIPTOR_NOT_A_NEW_RELEASE",
        "new_package_export_allowed": False,
        "existing_manual_pack_distribution_scope_unchanged": True,
        "new_signature_or_approval_created": False,
        "w09_generic_skill_engine_packaging_complete": False,
        "network_requests": 0,
        "database_writes": 0,
    }
    canonical = json.dumps(
        payload, ensure_ascii=True, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("ascii")
    payload["descriptor_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only UCIE signed-rule Library index or existing consumer descriptor")
    parser.add_argument("--ucie-root", required=True, type=Path)
    parser.add_argument("--serial4-pack", required=True, type=Path)
    parser.add_argument("--owner-public-trust", required=True, type=Path)
    parser.add_argument("--serial5-pack", type=Path)
    parser.add_argument("--descriptor", action="store_true")
    args = parser.parse_args()
    try:
        kw = dict(
            serial4_pack=args.serial4_pack,
            owner_public_trust=args.owner_public_trust,
            serial5_pack=args.serial5_pack)
        result = (build_existing_pack_consumer_descriptor(args.ucie_root, **kw)
                  if args.descriptor
                  else inspect_signed_library(args.ucie_root, **kw))
    except (SignedLibraryError, OSError) as exc:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "SIGNED_LIBRARY_VERIFICATION_REQUIRED_NO_GO",
            "error_type": type(exc).__name__,
            "items": [], "network_requests": 0, "database_writes": 0,
            "new_package_export_allowed": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
