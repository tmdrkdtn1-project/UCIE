"""UCIE C4 actual independent Windows recipient: no-copy READ-ONLY acceptance.

The separate OWNER-CONTROLLED real device requires an existing signed
UCIE_PRIVATE_RECIPIENT installed product. This module does NOT install,
upgrade, rollback, uninstall, sign, publish, copy keys, expose customer
identifiers, alter UCIE operating data or certify physical independence.
It runs 4 installed product pillar workflows and bounded localhost V04
smoke tests *only after* verifying the actual private Ed25519 entitlement.
No CI or source-checkout bypass.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from . import customer_private_offline_lifecycle_v01 as life
from . import customer_private_entitlement_v01 as c3
from .customer_staging_v01 import PILLARS

SCHEMA="UCIE_C4_SEPARATE_OWNER_CONTROLLED_PHYSICAL_WINDOWS_READONLY_ACCEPTANCE_V01"
CONSENT="VERIFY_EXISTING_UCIE_OWNER_CONTROLLED_PHYSICAL_RECIPIENT_ONCE"
STATUS="C4_SIGNED_INSTALLED_FOUR_PILLAR_LOCAL_SMOKE_WITNESS_PENDING_CUSTOMER_NO_GO"


class PhysicalRecipientAcceptanceError(ValueError):
    """Any unverified recipient/context must fail closed."""


def _host_gate(root:Path,*,consent:str) -> Path:
    if type(consent) is not str or consent!=CONSENT:
        raise PhysicalRecipientAcceptanceError("explicit recipient-local witness consent required")
    if (not isinstance(root,Path) or not root.is_absolute()
            or root.name!=life.RECIPIENT_NAME or os.name!="nt"
            or sys.implementation.name!="cpython" or sys.version_info[:2]!=(3,15)
            or sys.maxsize<=2**32
            or not sys.stdin.isatty() or os.environ.get("CI")
            or os.environ.get("GITHUB_ACTIONS")
            or root.is_symlink() or root.parent.is_symlink()):
        raise PhysicalRecipientAcceptanceError("actual separate interactive Windows3.15 recipient required")
    try:
        # Never accept a UCIE checkout or a child of D:/UCIE as a separate recipient.
        parent=Path("D:/UCIE")
        if parent.is_dir() and root.resolve().is_relative_to(parent.resolve()):
            raise PhysicalRecipientAcceptanceError("owner source checkout is not a recipient")
    except (OSError,RuntimeError) as exc:
        raise PhysicalRecipientAcceptanceError("Windows recipient path unsafe") from exc
    return life._recipient(root)


def _validated_public_key(path:Path) -> bytes:
    if (not isinstance(path,Path) or not path.is_absolute()
            or path.is_symlink() or path.parent.is_symlink()):
        raise PhysicalRecipientAcceptanceError("owner approved separate PUBLIC trust path required")
    return life._read(path,2000)


def _verified_installed_local_smoke(root:Path,*,public_pem:bytes,
                                    expected_owner_key_id:str,
                                    recipient_token_sha256:str,
                                    rights_packet_sha256:str,min_serial:int) -> dict:
    """Requires actual selected customer wheel and prints non-identifying receipt."""
    result=life.verify_selected(
        root,public_pem=public_pem,
        expected_owner_key_id=expected_owner_key_id,
        expected_recipient_token_sha256=recipient_token_sha256,
        expected_rights_packet_sha256=rights_packet_sha256,
        min_serial=min_serial)
    if (result.get("real_ed25519_verified") is not True
            or result.get("runtime_owner_license_reverified") is not True
            or result.get("exact_wheel_count")!=4
            or result.get("customer_distribution_authorized") is not False
            or not all(x in result.get("four_pillars_bound",[]) for x in PILLARS)):
        raise PhysicalRecipientAcceptanceError("customer-bound installed signature not verified")
    slot=result["active_slot"]
    child=root/"slots"/slot/"venv"/"Scripts"/"python.exe"
    ui=root/"slots"/slot/"ui"/"UCIE"
    # Actual tests MUST run from the selected installed slot, not a
    # development owner venv with different code and/or different trust.
    if (Path(sys.executable).resolve()!=child.resolve()
            or child.is_symlink() or not child.is_file()
            or ui.is_symlink() or not ui.is_dir()
            or (ui/"runtime").exists()
            or {p.name for p in ui.iterdir()}!={".git"}
            or (ui/".git").is_symlink()
            or not (ui/".git").is_dir()):
        raise PhysicalRecipientAcceptanceError("untrusted physical recipient active interpreter or UI root")
    four,local=life._installed_smoke(child,ui,child.parent.parent.parent)
    if (four.get("pillar_count")!=4
            or local.get("verified_local_V04_GET_count")!=4
            or local.get("denied_POST") is not True):
        raise PhysicalRecipientAcceptanceError("actual physical device signed four pillars or V04 failed")
    receipt_fingerprint=sha256(json.dumps({
        "signed_product_sha256":result["product_sha256"],
        "signed_serial":result["owner_signed_serial"],
        "active_slot":slot,
        "four_pillar_receipt_sha256":four["workflow_receipt_sha256"],
        "local_v04_gets":4,
    },sort_keys=True,separators=(",",":")).encode("ascii")).hexdigest()
    return {
        "schema":SCHEMA,
        "status":STATUS,
        "real_private_product_ed25519_verified_on_recipient":True,
        "installed_signed_exact_four_wheels_verified":True,
        "active_product_version":result["product_version"],
        "bound_four_pillars_executed":4,
        "local_V04_actual_HTTP_200_GETs":4,
        "local_V04_POST_405_denied":True,
        "native_signing_serial_observed":result["owner_signed_serial"],
        "non_secret_acceptance_receipt_sha256":receipt_fingerprint,
        "approval_owner_hardware_is_independent_proven_cryptographically":False,
        "owner_physical_witness_approval_present":False,
        "physical_upgrade_rollback_uninstall_accepted":False,
        "independent_security_and_legal_clearance_approved":False,
        "designated_customer_contract_and_pilot_accepted":False,
        "customer_distribution_authorized":False,
        "owner_private_signing_key_accessed":False,
        "operating_database_writes":0,
        "recipient_install_update_rollback_uninstall_executed":False,
        "background_service_registered":False,
    }


def actual_physical_recipient_readonly(
    recipient:Path,*,public_trust_pem:Path,
    expected_owner_key_id:str,recipient_token_sha256:str,
    rights_packet_sha256:str,min_serial:int,consent:str,
) -> dict:
    root=_host_gate(recipient,consent=consent)
    if (type(expected_owner_key_id) is not str or c3.KEYID.fullmatch(expected_owner_key_id) is None
            or type(recipient_token_sha256) is not str
            or c3.SHA.fullmatch(recipient_token_sha256) is None
            or type(rights_packet_sha256) is not str
            or c3.SHA.fullmatch(rights_packet_sha256) is None
            or type(min_serial) is not int or not 1<=min_serial<=c3.MAX_SERIAL):
        raise PhysicalRecipientAcceptanceError("separate trusted owner public policy pin required")
    public=_validated_public_key(public_trust_pem)
    return _verified_installed_local_smoke(
        root,public_pem=public,expected_owner_key_id=expected_owner_key_id,
        recipient_token_sha256=recipient_token_sha256,
        rights_packet_sha256=rights_packet_sha256,min_serial=min_serial)


def main(argv:list[str]|None=None) -> int:
    parser=argparse.ArgumentParser(description="UCIE C4 owner-controlled second physical Windows read-only technical QA")
    parser.add_argument("--real-recipient-readonly-once",action="store_true")
    parser.add_argument("--recipient-root",type=Path,required=True)
    parser.add_argument("--public-trust-pem",type=Path,required=True)
    parser.add_argument("--expected-owner-key-id",required=True)
    parser.add_argument("--recipient-token-sha256",required=True)
    parser.add_argument("--rights-packet-sha256",required=True)
    parser.add_argument("--min-serial",type=int,required=True)
    args=parser.parse_args(argv)
    try:
        if not args.real_recipient_readonly_once:
            raise PhysicalRecipientAcceptanceError("explicit physical recipient inspect mode required")
        consent=input("UCIE C4 owner-control of actual separate Windows device consent: ").strip()
        result=actual_physical_recipient_readonly(
            args.recipient_root,public_trust_pem=args.public_trust_pem,
            expected_owner_key_id=args.expected_owner_key_id,
            recipient_token_sha256=args.recipient_token_sha256,
            rights_packet_sha256=args.rights_packet_sha256,
            min_serial=args.min_serial,consent=consent)
    except (OSError,ValueError,TypeError,EOFError,KeyError) as exc:
        print(json.dumps({
            "schema":SCHEMA,"status":"C4_PHYSICAL_RECIPIENT_FAIL_CLOSED_NO_GO",
            "safe_error_type":type(exc).__name__,
            "customer_distribution_authorized":False,
        },sort_keys=True))
        return 2
    print(json.dumps(result,sort_keys=True))
    # Technical read-only local verification != signed physical witness/customer GO.
    return 2


if __name__=="__main__":
    raise SystemExit(main())
