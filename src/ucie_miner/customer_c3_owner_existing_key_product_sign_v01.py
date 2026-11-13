"""UCIE C3: EXISTING owner Ed25519 key, owner-only real customer signing gate.

This is a dormant, explicitly gated signer; it NEVER generates a key,
reads keys on import, signs in CI, approves contracts, ships wheels,
uploads data or registers a service. Intended only after human C2
LICENSE/NOTICE and embedded OpenSSL security, first-party ownership,
real designated customer contract and separate product-signing purpose
have been approved. A self-reported JSON is NOT legal clearance.

The reviewed PRIVATE product-purpose domain is separate from C3 public
PR metadata and demo signatures. The signer creates only detached
entitlement JSON + signature in an ignored owner-local directory.
"""
from __future__ import annotations

from base64 import b64encode
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import json
import os
import re
import sys

from . import customer_private_entitlement_v01 as c3
from . import customer_owner_wheelhouse_acquire_v01 as c1
from . import customer_offline_dependency_gate_v01 as gate
from . import customer_full_product_offline_rehearsal_v01 as full
from . import local_public_pr_owner_auth_v01 as auth
from .customer_staging_v01 import PILLARS

SCHEMA = "UCIE_C3_OWNER_EXISTING_KEY_PRODUCT_ENTITLEMENT_SIGN_ONCE_V01"
DECISION_SCHEMA = "UCIE_C2_C3_OWNER_HUMAN_RELEASE_DECISION_V01"
CONSENT = "OWNER_SIGN_UCIE_C3_EXISTING_KEY_REAL_CUSTOMER_ENTITLEMENT_ONCE"
HOST_ROOT = Path("D:/UCIE")
KEY_NAME = re.compile(r"ucie_[a-z0-9_]{3,72}_private\.pem\Z")
TRUST_NAME = re.compile(r"ucie_[a-z0-9_]{3,72}_trust\.pem\Z")
DECISION_FILE = "ucie_c2_c3_owner_human_release_decision_v01.json"
OUT_PREFIX = "ucie_c3_owner_private_customer_sign_v01_serial_"
MAX_DECISION = 3300
REQUIRED_DECISION_TRUE = (
    "first_party_rightsholder_and_contributors_human_approved",
    "actual_vendor_license_notice_copyright_human_approved",
    "openssl_4_0_3_five_known_nov10_cve_risk_human_disposition_approved",
    "publisher_provenance_security_policy_human_reviewed",
    "private_product_signing_key_purpose_human_approved",
    "actual_designated_customer_private_contract_signed",
    "four_pillar_product_scope_human_approved",
)


class ExistingOwnerSigningError(ValueError):
    """Real owner signature withheld until independently authorized."""


def _decision_bytes(payload: bytes, *, independently_approved_sha256: str) -> dict:
    if (type(independently_approved_sha256) is not str
            or c3.SHA.fullmatch(independently_approved_sha256) is None
            or type(payload) is not bytes or not 0 < len(payload) <= MAX_DECISION
            or sha256(payload).hexdigest() != independently_approved_sha256):
        raise ExistingOwnerSigningError("independent human decision SHA pin required")
    try:
        data = c3._decode(payload, maximum=MAX_DECISION)
    except (ValueError,TypeError) as exc:
        raise ExistingOwnerSigningError("human decision is not canonical") from exc
    if (set(data) != set(REQUIRED_DECISION_TRUE) | {
            "schema","security_disposition","customer_distribution_authorized"
            } or data["schema"] != DECISION_SCHEMA
            or data["security_disposition"] not in (
                "OFFICIAL_PATCHED_WHEEL_VERIFIED",
                "HUMAN_ACCEPTED_DOCUMENTED_RESTRICTED_5_LOW_CVE_RISK")
            or data["customer_distribution_authorized"] is not False
            or any(data.get(k) is not True for k in REQUIRED_DECISION_TRUE)):
        raise ExistingOwnerSigningError("human approvals absent or security risk unresolved")
    # The exact reviewed C1 pin cryptography==50.0.2 bundles OpenSSL 4.0.3.
    # No new patched vendor version/ABI/SHA was independently pinned.
    # A human checkbox must not falsely declare THIS wheel patched.
    if data["security_disposition"]=="OFFICIAL_PATCHED_WHEEL_VERIFIED":
        raise ExistingOwnerSigningError(
            "existing fixed cryptography 50.0.2 wheel is not verified patched")
    return data


def _owner_gate(root: Path, *, consent: str) -> Path:
    """Must happen BEFORE reading any sensitive local approval or key bytes."""
    if consent != CONSENT:
        raise ExistingOwnerSigningError("separate exact owner production signing consent absent")
    if not isinstance(root, Path) or os.name != "nt":
        raise ExistingOwnerSigningError("actual owner Windows only")
    try:
        if (root.resolve(strict=True) != HOST_ROOT.resolve(strict=True)
                or Path(sys.executable).resolve(strict=True) != (
                    root/".venv"/"Scripts"/"python.exe").resolve(strict=True)
                or sys.implementation.name != "cpython"
                or sys.version_info[:2] != (3,15) or sys.maxsize <= 2**32
                or not sys.stdin.isatty() or bool(os.environ.get("CI"))
                or root.is_symlink() or not (root/".git").is_dir()
                or (root/".git").is_symlink()):
            raise ExistingOwnerSigningError("real D:/UCIE owner TTY CPython3.15 only")
    except (OSError,RuntimeError) as exc:
        raise ExistingOwnerSigningError("owner Windows path/preflight unavailable") from exc
    ignored = root/".gitignore"
    if (ignored.is_symlink() or not ignored.is_file()
            or "downloaded/" not in ignored.read_text(encoding="utf-8").splitlines()
            or ".build_keys/" not in ignored.read_text(encoding="utf-8").splitlines()):
        raise ExistingOwnerSigningError("private key/receipt paths must stay Git-ignored")
    return root


def _within_downloaded(root: Path, path: Path) -> Path:
    downloaded = root/"downloaded"
    if (not isinstance(path, Path) or not path.is_absolute()
            or downloaded.is_symlink() or not downloaded.is_dir()
            or path.is_symlink() or path.parent.is_symlink()
            or not path.is_file()):
        raise ExistingOwnerSigningError("existing approved owner product wheel missing")
    try:
        if not path.resolve(strict=True).is_relative_to(downloaded.resolve(strict=True)):
            raise ExistingOwnerSigningError("only existing UCIE ignored product wheel allowed")
    except (OSError, RuntimeError) as exc:
        raise ExistingOwnerSigningError("owner product wheel path not verified") from exc
    return path


def _real_record_and_detached_signature(
    record: dict, owner_private_key: object, *, consent: str,
) -> tuple[bytes,bytes]:
    """Actual purpose-separated cryptography primitive, no file access."""
    if consent != CONSENT:
        raise ExistingOwnerSigningError("real signature requires exact owner consent")
    _,_,private_type,_,key_id = auth._crypto()
    if not isinstance(owner_private_key,private_type):
        raise ExistingOwnerSigningError("pre-existing Ed25519 owner key required")
    if type(record) is not dict or set(record)!=c3.FIELDS:
        raise ExistingOwnerSigningError("incomplete exact four-pillar record")
    body=c3.canonical(record)
    if (len(body)>c3.MAX_RECORD or record.get("schema")!=c3.SCHEMA
            or record.get("scope")!=c3.SCOPE
            or record.get("owner_key_id")!=key_id(owner_private_key.public_key())):
        raise ExistingOwnerSigningError("wrong purpose or owner key")
    sig=owner_private_key.sign(c3.DOMAIN+body)
    detached=c3.canonical({
        "schema":c3.ATTESTATION_SCHEMA,"scope":c3.SCOPE,
        "algorithm":"Ed25519","owner_key_id":record["owner_key_id"],
        "payload_sha256":sha256(body).hexdigest(),
        "signature_base64":b64encode(sig).decode("ascii"),
    })
    if len(detached)>c3.MAX_ATTESTATION:
        raise ExistingOwnerSigningError("oversized detached signature")
    return body,detached


def owner_sign_once(
    root:Path,*,product_wheel:Path,
    existing_private_filename:str,existing_public_trust_filename:str,
    expected_owner_key_id:str,expected_product_sha256:str,
    expected_vendor_sha256:dict[str,str],
    recipient_token_sha256:str,decision_sha256:str,
    serial:int,consent:str,
) -> dict:
    """One real local signature ONLY when ALL human signoffs are present.

    No actual signing is done by ChatGPT, CI or the caller's project.
    """
    root=_owner_gate(root,consent=consent)
    if (type(existing_private_filename) is not str
            or KEY_NAME.fullmatch(existing_private_filename) is None
            or type(existing_public_trust_filename) is not str
            or TRUST_NAME.fullmatch(existing_public_trust_filename) is None
            or type(expected_owner_key_id) is not str
            or c3.KEYID.fullmatch(expected_owner_key_id) is None
            or type(expected_product_sha256) is not str
            or c3.SHA.fullmatch(expected_product_sha256) is None
            or type(recipient_token_sha256) is not str
            or c3.SHA.fullmatch(recipient_token_sha256) is None
            or type(serial) is not int or not 1<=serial<=c3.MAX_SERIAL
            or type(expected_vendor_sha256) is not dict
            or set(expected_vendor_sha256)!={name for name,_ in c1.PINNED}
            or not all(type(v) is str and c3.SHA.fullmatch(v)
                       for v in expected_vendor_sha256.values())):
        raise ExistingOwnerSigningError("independent owner/recipient/product SHA pins absent")
    downloaded=root/"downloaded"
    destination=downloaded/(OUT_PREFIX+str(serial))
    if destination.exists() or destination.is_symlink():
        raise ExistingOwnerSigningError("owner signature serial already emitted")
    # Authenticate human intent BEFORE owner key read. Hash alone does not
    # make the approval legally independent, so output still claims NO_GO.
    raw_approval=auth._safe_small(downloaded/DECISION_FILE,max_bytes=MAX_DECISION)
    _decision_bytes(raw_approval,independently_approved_sha256=decision_sha256)
    product=_within_downloaded(root,product_wheel)
    product_entry=gate._inspect_wheel(product)
    if (product_entry.get("name")!=full.FIRST_PARTY_NAME
            or product_entry.get("version") not in c3.SUPPORTED_VERSIONS
            or product.name!=("ucie_public_only_demo-"+product_entry["version"]+
                              "-py3-none-any.whl")
            or product_entry.get("metadata_record_sha256_verified") is not True
            or sha256(product.read_bytes()).hexdigest()!=expected_product_sha256):
        raise ExistingOwnerSigningError("first-party actual inspected product SHA/RECORD mismatch")
    c1_receipt=c1.verify_local(root)
    if c1_receipt.get("all_local_bytes_match_captured_pypi_digests") is not True:
        raise ExistingOwnerSigningError("previous C1 owner vendor digest receipt changed")
    wheel_dir=root/c1.WHEELHOUSE
    vend={};
    for name,version in c1.PINNED:
        members=[p for p in wheel_dir.iterdir()
                 if p.is_file() and not p.is_symlink()
                 and p.name.startswith(name+"-"+version+"-") and p.suffix==".whl"]
        if len(members)!=1:
            raise ExistingOwnerSigningError("exact C1 captured vendor missing")
        p=members[0]
        if sha256(p.read_bytes()).hexdigest()!=expected_vendor_sha256[name]:
            raise ExistingOwnerSigningError("owner expected vendor SHA differs from C1 source")
        vend[name]=expected_vendor_sha256[name]
    keys=root/".build_keys"
    if keys.is_symlink() or not keys.is_dir():
        raise ExistingOwnerSigningError("existing owner key directory unavailable")
    pub=auth._safe_small(keys/existing_public_trust_filename,max_bytes=auth.MAX_PEM)
    pem=auth._safe_small(keys/existing_private_filename,max_bytes=auth.MAX_PEM)
    _,serialization,private_type,public_type,key_id = auth._crypto()
    try:
        private=serialization.load_pem_private_key(pem,password=None)
        public=serialization.load_pem_public_key(pub)
    except (ValueError,TypeError) as exc:
        raise ExistingOwnerSigningError("owner preexisting key cannot be loaded") from exc
    if (not isinstance(private,private_type) or not isinstance(public,public_type)
            or key_id(private.public_key())!=expected_owner_key_id
            or key_id(public)!=expected_owner_key_id
            or public.public_bytes(serialization.Encoding.PEM,
                                   serialization.PublicFormat.SubjectPublicKeyInfo)!=pub):
        raise ExistingOwnerSigningError("owner product purpose public trust does not match private")
    issued=datetime.now(timezone.utc).replace(microsecond=0)
    record={
        "schema":c3.SCHEMA,"scope":c3.SCOPE,"product":c3.DIST,
        "product_version":product_entry["version"],
        "product_wheel_sha256":expected_product_sha256,
        "vendor_wheels_sha256":vend,
        "recipient_token_sha256":recipient_token_sha256,
        "rights_packet_sha256":decision_sha256,
        "four_pillars":list(PILLARS),"serial":serial,
        "owner_key_id":expected_owner_key_id,
        "issued_utc":auth._stamp(issued),
        "expires_utc":auth._stamp(issued+timedelta(days=c3.SUBSCRIPTION_PRODUCT_ARTIFACT_DAYS)),
    }
    body,signed=_real_record_and_detached_signature(record,private,consent=consent)
    verified=c3.verify_private_entitlement(
        body,signed,pub,
        expected_owner_key_id=expected_owner_key_id,
        min_serial=serial,
        expected_recipient_token_sha256=recipient_token_sha256,
        expected_product_wheel_sha256=expected_product_sha256,
        expected_vendor_wheels_sha256=vend,
        expected_rights_packet_sha256=decision_sha256,
        now=issued,expected_product_version=product_entry["version"])
    if verified.get("private_product_ed25519_signature_verified") is not True:
        raise ExistingOwnerSigningError("owner detached signature cannot be verified")
    with TemporaryDirectory(prefix="ucie_c3_owner_private_signing_",dir=downloaded) as temp:
        folder=Path(temp)/"signed"
        folder.mkdir()
        for filename,payload in (
            ("entitlement.json",body),("entitlement.sig.json",signed)):
            with (folder/filename).open("xb") as out:
                out.write(payload)
        (folder/"REVIEW_ONLY_NO_CUSTOMER_DISTRIBUTION.txt").write_text(
            "UCIE owner-only C3 signed artifacts. Human approvals must be\n"
            "validated independently by the named recipient. No automatic\n"
            "customer distribution, physical acceptance or C5 GO.\n",
            encoding="ascii")
        # Windows rename onto existing destination is rejected. Never overwrite.
        if destination.exists() or destination.is_symlink():
            raise ExistingOwnerSigningError("signature destination race, refuse overwrite")
        folder.rename(destination)
    return {
        "schema":SCHEMA,
        "status":"OWNER_EXISTING_KEY_GENUINE_LOCAL_PRODUCT_SIGNED_NOT_RELEASED_NO_GO",
        "source_product_version":product_entry["version"],
        "source_product_sha256":expected_product_sha256,
        "actual_vendors_checked_against_existing_C1_receipt":True,
        "entitlement_and_detached_signature_local_only":True,
        "signature_cryptographically_self_checked":True,
        "record_sha256":sha256(body).hexdigest(),
        "detached_signature_sha256":sha256(signed).hexdigest(),
        "owner_key_id":expected_owner_key_id,
        "serial":serial,
        "private_key_exported":False,
        "new_private_key_created":False,
        "customer_identifiers_exported":False,
        "customer_distribution_authorized":False,
        "actual_customer_machine_accepted":False,
        "operating_database_writes":0,
    }


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description="EXISTING UCIE owner key: real purpose-approved PRIVATE signed entitlement, owner only")
    ap.add_argument("--owner-real-sign-once",action="store_true")
    ap.add_argument("--product-wheel",type=Path,required=True)
    ap.add_argument("--existing-private-key-name",required=True)
    ap.add_argument("--existing-public-trust-key-name",required=True)
    ap.add_argument("--expected-owner-key-id",required=True)
    ap.add_argument("--expected-product-sha256",required=True)
    ap.add_argument("--expected-cryptography-sha256",required=True)
    ap.add_argument("--expected-cffi-sha256",required=True)
    ap.add_argument("--expected-pycparser-sha256",required=True)
    ap.add_argument("--recipient-token-sha256",required=True)
    ap.add_argument("--expected-human-decision-sha256",required=True)
    ap.add_argument("--serial",type=int,required=True)
    args=ap.parse_args(argv)
    try:
        if not args.owner_real_sign_once:
            raise ExistingOwnerSigningError("no owner signing without explicit one-shot flag")
        consent=input("UCIE C3 real owner private customer-product signing consent: ").strip()
        result=owner_sign_once(
            HOST_ROOT,product_wheel=args.product_wheel,
            existing_private_filename=args.existing_private_key_name,
            existing_public_trust_filename=args.existing_public_trust_key_name,
            expected_owner_key_id=args.expected_owner_key_id,
            expected_product_sha256=args.expected_product_sha256,
            expected_vendor_sha256={
                "cryptography":args.expected_cryptography_sha256,
                "cffi":args.expected_cffi_sha256,
                "pycparser":args.expected_pycparser_sha256},
            recipient_token_sha256=args.recipient_token_sha256,
            decision_sha256=args.expected_human_decision_sha256,
            serial=args.serial,consent=consent)
    except (OSError,TypeError,ValueError,EOFError) as exc:
        print(json.dumps({
            "schema":SCHEMA,
            "status":"C3_OWNER_REAL_PRODUCT_SIGNING_FAIL_CLOSED_CUSTOMER_NO_GO",
            "safe_error_type":type(exc).__name__,
            "customer_distribution_authorized":False,
        },sort_keys=True))
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
