"""UCIE membership recipient: atomic signed subscription snapshot renewal.

Only an independently provisioned PUBLIC owner key and the already verified
four-wheel customer product are trusted; no billing-provider API is claimed.
A new higher Ed25519 renewal sequence replaces the active subscription
pointer only after verification. Customer code/output files are untouched.
The owner serial/min-sequence floors MUST be separately provisioned and
updated, since mutable offline state alone is not secure anti-rollback.
"""
from __future__ import annotations

from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
from tempfile import mkdtemp

from . import customer_private_offline_lifecycle_v01 as life
from . import customer_membership_subscription_v01 as sub

SCHEMA="UCIE_MEMBERSHIP_RECIPIENT_SIGNED_RENEWAL_V01"
CONSENT="IMPORT_EXISTING_OWNER_SIGNED_UCIE_MEMBERSHIP_ONCE"
MEMBER_DIR="membership"
SHA=re.compile(r"[a-f0-9]{64}\Z")


class MembershipRecipientError(ValueError):
    """Offline snapshots are not unverified billing authority."""


def _folder(recipient:Path) -> Path:
    root=life._recipient(recipient)
    return root/MEMBER_DIR


def _pointer(folder:Path) -> dict|None:
    if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
        raise MembershipRecipientError("membership directory is untrusted")
    if not folder.exists():
        return None
    if {p.name for p in folder.iterdir()}-{"current.json","snapshots"}:
        raise MembershipRecipientError("untrusted unknown membership data")
    pointer=folder/"current.json"
    if not pointer.exists() and not pointer.is_symlink():
        return None
    obj=life._parse(life._read(pointer,1000),1000)
    if (set(obj)!={"schema","record_sha256","renewal_sequence"}
            or obj["schema"]!=SCHEMA
            or type(obj["record_sha256"]) is not str
            or SHA.fullmatch(obj["record_sha256"]) is None
            or type(obj["renewal_sequence"]) is not int
            or not 1<=obj["renewal_sequence"]<=sub.MAX_SEQUENCE):
        raise MembershipRecipientError("untrusted membership pointer")
    return obj


def _bytes(folder:Path, sha:str) -> tuple[bytes,bytes]:
    if type(sha) is not str or SHA.fullmatch(sha) is None:
        raise MembershipRecipientError("untrusted membership record slot")
    snap=folder/"snapshots"
    if snap.is_symlink() or not snap.is_dir():
        raise MembershipRecipientError("membership snapshots directory missing")
    slot=snap/sha
    if (slot.is_symlink() or not slot.is_dir()
            or {p.name for p in slot.iterdir()}!={"member.json","member.sig.json"}):
        raise MembershipRecipientError("membership snapshot untrusted")
    body=life._read(slot/"member.json",sub.MAX_RECORD)
    sig=life._read(slot/"member.sig.json",sub.MAX_SIGNATURE)
    if sha256(body).hexdigest()!=sha:
        raise MembershipRecipientError("membership selected record bytes differ")
    return body,sig


def verify_installed_membership(
    recipient:Path,*,public_pem:bytes,expected_owner_key_id:str,
    expected_recipient_token_sha256:str,expected_rights_packet_sha256:str,
    expected_subscription_id_sha256:str,
    min_product_serial:int,min_renewal_sequence:int,
    now:datetime|None=None,
) -> dict:
    root=life._recipient(recipient)
    product=life.verify_selected(
        root,public_pem=public_pem,
        expected_owner_key_id=expected_owner_key_id,
        expected_recipient_token_sha256=expected_recipient_token_sha256,
        expected_rights_packet_sha256=expected_rights_packet_sha256,
        min_serial=min_product_serial,now=now)
    folder=_folder(root)
    current=_pointer(folder)
    if not current:
        raise MembershipRecipientError("no owner-signed active subscription")
    body,sig=_bytes(folder,current["record_sha256"])
    membership=sub.verify_membership(
        body,sig,public_pem,
        expected_owner_key_id=expected_owner_key_id,
        expected_subscription_id_sha256=expected_subscription_id_sha256,
        expected_recipient_token_sha256=expected_recipient_token_sha256,
        expected_rights_packet_sha256=expected_rights_packet_sha256,
        actual_product_serial=product["owner_signed_serial"],
        min_renewal_sequence=min_renewal_sequence,
        now=datetime.now(timezone.utc) if now is None else now)
    if membership["renewal_sequence"]!=current["renewal_sequence"]:
        raise MembershipRecipientError("membership local pointer sequence mismatch")
    return {
        **membership,
        "schema":SCHEMA,
        "existing_signed_product_verified_before_membership":True,
        "real_customer_payment_externally_verified_by_ucie":False,
        "customer_distribution_authorized":False,
    }


def import_owner_signed_membership(
    recipient:Path,record_bytes:bytes,signature_bytes:bytes,*,
    public_pem:bytes,expected_owner_key_id:str,
    expected_recipient_token_sha256:str,expected_rights_packet_sha256:str,
    expected_subscription_id_sha256:str,min_product_serial:int,
    min_renewal_sequence:int,consent:str,now:datetime|None=None,
) -> dict:
    if consent!=CONSENT:
        raise MembershipRecipientError("separate member import consent missing")
    root=life._recipient(recipient)
    product=life.verify_selected(
        root,public_pem=public_pem,
        expected_owner_key_id=expected_owner_key_id,
        expected_recipient_token_sha256=expected_recipient_token_sha256,
        expected_rights_packet_sha256=expected_rights_packet_sha256,
        min_serial=min_product_serial,now=now)
    verified=sub.verify_membership(
        record_bytes,signature_bytes,public_pem,
        expected_owner_key_id=expected_owner_key_id,
        expected_subscription_id_sha256=expected_subscription_id_sha256,
        expected_recipient_token_sha256=expected_recipient_token_sha256,
        expected_rights_packet_sha256=expected_rights_packet_sha256,
        actual_product_serial=product["owner_signed_serial"],
        min_renewal_sequence=min_renewal_sequence,
        now=datetime.now(timezone.utc) if now is None else now)
    folder=_folder(root)
    old=_pointer(folder)
    digest=sha256(record_bytes).hexdigest()
    next_seq=verified["renewal_sequence"]
    if old:
        if next_seq<old["renewal_sequence"]:
            raise MembershipRecipientError("membership renewal sequence rollback denied")
        if next_seq==old["renewal_sequence"]:
            if old["record_sha256"]!=digest:
                raise MembershipRecipientError("same renewal sequence cannot change status")
            existing_body,existing_sig=_bytes(folder,digest)
            if existing_body!=record_bytes or existing_sig!=signature_bytes:
                raise MembershipRecipientError("same renewal sequence signature changed")
            return {
                "schema":SCHEMA,"status":"MEMBERSHIP_EXISTING_IDENTICAL_SNAPSHOT_NO_OP",
                "renewal_sequence":next_seq,
                "customer_distribution_authorized":False,
                "operating_database_writes":0,
            }
    if (folder.exists() and (folder.is_symlink() or not folder.is_dir())):
        raise MembershipRecipientError("unsafe existing membership directory")
    # Safe explicit provision only inside the existing signed recipient.
    folder.mkdir(exist_ok=True)
    snapshots=folder/"snapshots"
    if snapshots.is_symlink() or (snapshots.exists() and not snapshots.is_dir()):
        raise MembershipRecipientError("untrusted membership snapshots root")
    snapshots.mkdir(exist_ok=True)
    destination=snapshots/digest
    if destination.exists() or destination.is_symlink():
        raise MembershipRecipientError("membership signature snapshot already occupied")
    stage=Path(mkdtemp(prefix="ucie_signed_member_stage_",dir=snapshots))
    try:
        (stage/"member.json").write_bytes(record_bytes)
        (stage/"member.sig.json").write_bytes(signature_bytes)
        if (life._read(stage/"member.json",sub.MAX_RECORD)!=record_bytes
                or life._read(stage/"member.sig.json",sub.MAX_SIGNATURE)!=signature_bytes):
            raise MembershipRecipientError("subscription snapshot copy changed")
        stage.rename(destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    pending=folder/"current.pending.json"
    if pending.exists() or pending.is_symlink():
        raise MembershipRecipientError("pending membership recovery requires manual review")
    pointer=life._canon({
        "schema":SCHEMA,"record_sha256":digest,"renewal_sequence":next_seq,
    })
    with pending.open("xb") as f:
        f.write(pointer)
        f.flush()
        os.fsync(f.fileno())
    os.replace(pending,folder/"current.json")
    return {
        "schema":SCHEMA,
        "status":"MEMBERSHIP_SIGNED_SNAPSHOT_IMPORTED_NOT_PAYMENT_PROCESSOR_OR_CUSTOMER_GO",
        "renewal_sequence":next_seq,
        "membership_phase":verified["membership_phase"],
        "plan":verified["plan"],
        "customer_owned_files_preserved":True,
        "payment_provider_event_independently_verified":False,
        "customer_distribution_authorized":False,
        "operating_database_writes":0,
    }


def main(argv:list[str]|None=None)->int:
    import argparse
    ap=argparse.ArgumentParser(description="UCIE private membership signed snapshot import or offline verification")
    ap.add_argument("--action",choices=("import","verify"),required=True)
    ap.add_argument("--recipient-root",type=Path,required=True)
    ap.add_argument("--public-trust-pem",type=Path,required=True)
    ap.add_argument("--member-record",type=Path)
    ap.add_argument("--member-signature",type=Path)
    ap.add_argument("--expected-owner-key-id",required=True)
    ap.add_argument("--expected-subscription-id-sha256",required=True)
    ap.add_argument("--recipient-token-sha256",required=True)
    ap.add_argument("--rights-packet-sha256",required=True)
    ap.add_argument("--min-product-serial",type=int,required=True)
    ap.add_argument("--min-renewal-sequence",type=int,required=True)
    ap.add_argument("--consent",default="")
    a=ap.parse_args(argv)
    try:
        key=life._read(a.public_trust_pem,2000)
        args=dict(public_pem=key,expected_owner_key_id=a.expected_owner_key_id,
            expected_subscription_id_sha256=a.expected_subscription_id_sha256,
            expected_recipient_token_sha256=a.recipient_token_sha256,
            expected_rights_packet_sha256=a.rights_packet_sha256,
            min_product_serial=a.min_product_serial,
            min_renewal_sequence=a.min_renewal_sequence)
        if a.action=="verify":
            report=verify_installed_membership(a.recipient_root,**args)
        else:
            if a.member_record is None or a.member_signature is None:
                raise MembershipRecipientError("two genuine signed member files required")
            report=import_owner_signed_membership(
                a.recipient_root,
                life._read(a.member_record,sub.MAX_RECORD),
                life._read(a.member_signature,sub.MAX_SIGNATURE),
                consent=a.consent,**args)
        print(json.dumps(report,sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print(json.dumps({
            "schema":SCHEMA,"status":"MEMBERSHIP_NO_GO_FAIL_CLOSED",
            "safe_error_type":type(exc).__name__,
            "customer_distribution_authorized":False,
        },sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
