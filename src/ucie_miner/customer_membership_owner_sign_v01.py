"""Owner-only genuine Ed25519 UCIE MEMBERSHIP issuance, not product-key replacement.

Uses already existing owner PEM ONLY after exact new interactive consent,
a pre-existing SHA-pinned C2/C3 human legal/security/customer contract
decision, and a separately SHA-pinned owner-reviewed payment event. This
cannot verify a payment processor that has not been connected; booleans
are HUMAN attestations, not independently proven external transactions.
No customer data or keys go to GitHub, no key generation, no pricing,
automatic charges, recurring scheduler or customer deployment occurs.
"""
from __future__ import annotations

from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import json
import os
import sys

from . import customer_c3_owner_existing_key_product_sign_v01 as existing
from . import customer_private_entitlement_v01 as product
from . import customer_membership_subscription_v01 as membership
from . import local_public_pr_owner_auth_v01 as owner

SCHEMA="UCIE_MEMBERSHIP_EXISTING_OWNER_KEY_SIGNING_V01"
PAYMENT_REVIEW_SCHEMA="UCIE_MEMBERSHIP_OWNER_REVIEWED_EXTERNAL_BILLING_EVENT_V01"
CONSENT="OWNER_SIGN_UCIE_MEMBERSHIP_EXISTING_KEY_ONCE"
PAYMENT_FILE="ucie_membership_owner_reviewed_payment_v01.json"
MAX_PAYMENT_REVIEW=2800
OUT_PREFIX="ucie_membership_owner_signed_sequence_"
REVIEW_FIELDS=frozenset((
    "schema","subscription_id_sha256","recipient_token_sha256",
    "payment_receipt_sha256","billing_interval","billing_status","plan",
    "period_start_utc","lease_issued_utc","customer_contract_signed_confirmed",
    "recurring_billing_disclosure_and_customer_consent_confirmed",
    "owner_verified_actual_provider_event",
    "customer_cancellation_intent_confirmed",
))


class MemberSignerError(ValueError):
    """No real owner membership rights or billing review approved."""


def _payment_review(raw:bytes,*,expected_sha256:str,record:dict) -> dict:
    if not product._hex64(expected_sha256) or sha256(raw).hexdigest()!=expected_sha256:
        raise MemberSignerError("owner payment event independent SHA is required")
    data=product._decode(raw,maximum=MAX_PAYMENT_REVIEW)
    if (set(data)!=REVIEW_FIELDS or data["schema"]!=PAYMENT_REVIEW_SCHEMA
            or data["subscription_id_sha256"]!=record["subscription_id_sha256"]
            or data["recipient_token_sha256"]!=record["recipient_token_sha256"]
            or data["payment_receipt_sha256"]!=record["payment_receipt_sha256"]
            or data["billing_interval"]!=record["billing_interval"]
            or data["billing_status"]!=record["billing_status"]
            or data["plan"]!=record["plan"]
            or data["period_start_utc"]!=record["period_start_utc"]
            or data["lease_issued_utc"]!=record["issued_utc"]
            or data["customer_contract_signed_confirmed"] is not True
            or data["recurring_billing_disclosure_and_customer_consent_confirmed"] is not True
            or data["owner_verified_actual_provider_event"] is not True
            or data["customer_cancellation_intent_confirmed"] is not (
                record["billing_status"]=="CANCEL_AT_PERIOD_END")):
        raise MemberSignerError("real owner billing/recurring consent/customer review missing")
    return data


def _owner_gate(root:Path,consent:str) -> Path:
    # Consent MUST be checked BEFORE any .build_keys/downloaded read.
    if consent!=CONSENT:
        raise MemberSignerError("distinct explicit membership signing consent missing")
    if (os.name!="nt" or not isinstance(root,Path)
            or sys.implementation.name!="cpython" or sys.version_info[:2]!=(3,15)
            or sys.maxsize<=2**32 or os.environ.get("CI")
            or not sys.stdin.isatty() or root.is_symlink()):
        raise MemberSignerError("real interactive owner Windows 3.15 only")
    try:
        if (root.resolve(strict=True)!=existing.HOST_ROOT.resolve(strict=True)
                or Path(sys.executable).resolve(strict=True)!=
                  (root/".venv"/"Scripts"/"python.exe").resolve(strict=True)
                or (root/".git").is_symlink() or not (root/".git").is_dir()):
            raise MemberSignerError("actual owner checkout and Python do not match")
    except (OSError,RuntimeError) as exc:
        raise MemberSignerError("owner executable could not be validated") from exc
    ignored=root/".gitignore"
    if (ignored.is_symlink() or not ignored.is_file()
            or not {"downloaded/",".build_keys/"}.issubset(
                set(ignored.read_text(encoding="utf-8").splitlines()))):
        raise MemberSignerError("owner private key/materials not Git-ignored")
    return root


def owner_membership_sign_once(
    root:Path,*,record:dict,private_filename:str,public_filename:str,
    expected_owner_key_id:str,decision_sha256:str,
    approved_payment_review_sha256:str,consent:str,
) -> dict:
    root=_owner_gate(root,consent)
    if (not isinstance(record,dict) or type(private_filename) is not str
            or existing.KEY_NAME.fullmatch(private_filename) is None
            or type(public_filename) is not str
            or existing.TRUST_NAME.fullmatch(public_filename) is None
            or type(expected_owner_key_id) is not str
            or product.KEYID.fullmatch(expected_owner_key_id) is None
            or not product._hex64(decision_sha256)
            or not product._hex64(approved_payment_review_sha256)
            or record.get("owner_key_id")!=expected_owner_key_id
            or record.get("rights_packet_sha256")!=decision_sha256):
        raise MemberSignerError("independent existing owner/purpose/rights pins absent")
    # Validate all record fields before anything private is read.
    membership._record_checks(record)
    data=product.canonical(record)
    if len(data)>membership.MAX_RECORD:
        raise MemberSignerError("membership record exceeds bounded size")
    downloaded=root/"downloaded"
    if downloaded.is_symlink() or not downloaded.is_dir():
        raise MemberSignerError("owner-only downloaded folder unavailable")
    destination=downloaded/(OUT_PREFIX+str(record["renewal_sequence"]))
    if destination.exists() or destination.is_symlink():
        raise MemberSignerError("owner membership issue sequence already used")
    legal=owner._safe_small(downloaded/existing.DECISION_FILE,max_bytes=existing.MAX_DECISION)
    existing._decision_bytes(legal,independently_approved_sha256=decision_sha256)
    payment=owner._safe_small(downloaded/PAYMENT_FILE,max_bytes=MAX_PAYMENT_REVIEW)
    _payment_review(payment,expected_sha256=approved_payment_review_sha256,record=record)

    keys=root/".build_keys"
    if keys.is_symlink() or not keys.is_dir():
        raise MemberSignerError("pre-existing owner key folder required")
    pub=owner._safe_small(keys/public_filename,max_bytes=owner.MAX_PEM)
    pem=owner._safe_small(keys/private_filename,max_bytes=owner.MAX_PEM)
    _,serialization,private_type,public_type,get_id=owner._crypto()
    try:
        private=serialization.load_pem_private_key(pem,password=None)
        public=serialization.load_pem_public_key(pub)
    except (ValueError,TypeError) as exc:
        raise MemberSignerError("owner existing key cannot be loaded") from exc
    if (not isinstance(private,private_type) or not isinstance(public,public_type)
            or get_id(private.public_key())!=expected_owner_key_id
            or get_id(public)!=expected_owner_key_id
            or public.public_bytes(serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo)!=pub):
        raise MemberSignerError("existing owner private/public key identity mismatch")
    signature=membership._sig(data,private,consent=CONSENT)
    verified=membership.verify_membership(
        data,signature,pub,expected_owner_key_id=expected_owner_key_id,
        expected_subscription_id_sha256=record["subscription_id_sha256"],
        expected_recipient_token_sha256=record["recipient_token_sha256"],
        expected_rights_packet_sha256=decision_sha256,
        actual_product_serial=record["product_entitlement_min_serial"],
        min_renewal_sequence=record["renewal_sequence"],
        now=datetime.now(timezone.utc))
    if verified.get("owner_membership_signature_verified") is not True:
        raise MemberSignerError("fresh membership signature self-check failed")
    with TemporaryDirectory(prefix="ucie_membership_sign_stage_",dir=downloaded) as stage:
        output=Path(stage)/"signed"
        output.mkdir()
        for name,bytes_ in (("member.json",data),("member.sig.json",signature)):
            with (output/name).open("xb") as f:
                f.write(bytes_)
        (output/"READ_THIS_NOT_A_PAYMENT_PROCESSOR_RECEIPT.txt").write_text(
            "Human owner assertions and an Ed25519 signature do not independently"
            " certify processor collection or customer distribution approval.\n",
            encoding="ascii")
        if destination.exists() or destination.is_symlink():
            raise MemberSignerError("membership signed output already exists")
        output.rename(destination)
    return {
        "schema":SCHEMA,
        "status":"OWNER_EXISTING_KEY_MEMBERSHIP_SIGNATURE_ISSUED_LOCALLY_NOT_CUSTOMER_DEPLOYED",
        "plan":record["plan"],"billing_interval":record["billing_interval"],
        "membership_phase":verified["membership_phase"],
        "renewal_sequence":record["renewal_sequence"],
        "record_sha256":sha256(data).hexdigest(),
        "signature_sha256":sha256(signature).hexdigest(),
        "existing_key_used_without_key_export":True,
        "new_private_key_generated":False,
        "external_payment_processor_verified_by_ucie":False,
        "actual_customer_subscription_activated_by_ucie":False,
        "customer_distribution_authorized":False,
    }


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description="UCIE real owner existing-key reviewed membership signed snapshot")
    ap.add_argument("--owner-sign-reviewed-membership-once",action="store_true")
    ap.add_argument("--record-input",type=Path,required=True)
    ap.add_argument("--existing-private-key-name",required=True)
    ap.add_argument("--existing-public-key-name",required=True)
    ap.add_argument("--expected-owner-key-id",required=True)
    ap.add_argument("--approved-rights-decision-sha256",required=True)
    ap.add_argument("--approved-payment-review-sha256",required=True)
    a=ap.parse_args(argv)
    try:
        if not a.owner_sign_reviewed_membership_once:
            raise MemberSignerError("real owner-sign mode not selected")
        consent=input("UCIE reviewed real owner membership signing consent: ").strip()
        _owner_gate(existing.HOST_ROOT,consent)
        path=existing._within_downloaded(existing.HOST_ROOT,a.record_input)
        record=product._decode(owner._safe_small(path,max_bytes=membership.MAX_RECORD),
                               maximum=membership.MAX_RECORD)
        report=owner_membership_sign_once(
            existing.HOST_ROOT,record=record,
            private_filename=a.existing_private_key_name,
            public_filename=a.existing_public_key_name,
            expected_owner_key_id=a.expected_owner_key_id,
            decision_sha256=a.approved_rights_decision_sha256,
            approved_payment_review_sha256=a.approved_payment_review_sha256,
            consent=consent)
        print(json.dumps(report,sort_keys=True))
        return 0
    except (OSError,TypeError,ValueError,EOFError) as exc:
        print(json.dumps({
            "schema":SCHEMA,
            "status":"OWNER_MEMBERSHIP_SIGNING_FAIL_CLOSED_NO_CUSTOMER_GO",
            "safe_error_type":type(exc).__name__,
            "customer_distribution_authorized":False,
        },sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
