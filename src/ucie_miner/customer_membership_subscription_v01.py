"""UCIE membership subscriptions: purpose-separated signed ACCESS, not a sale.

This is an offline subscription-capability gate for the already signed
UCIE four-wheel private product. The existing C3 product entitlement
authenticates software integrity/recipient; it is NEVER a paid membership.
Customer identities are opaque SHA256 tokens. No payment API, key generation,
billing charge, personal data deletion, online revocation or legal GO occurs.
No file IO or clock reads in the verifier. Offline signed access is bounded
by the subscription period and a separately provided renewal serial floor.
"""
from __future__ import annotations

from base64 import b64decode,b64encode
import calendar
from datetime import datetime,timedelta,timezone
from hashlib import sha256

from . import customer_private_entitlement_v01 as product
from . import local_public_pr_owner_auth_v01 as owner
from .customer_staging_v01 import PILLARS

SCHEMA = "UCIE_MEMBERSHIP_SUBSCRIPTION_ACCESS_V01"
SIG_SCHEMA = "UCIE_MEMBERSHIP_SUBSCRIPTION_ED25519_ATTESTATION_V01"
SCOPE = "UCIE_PAID_MEMBERSHIP_SIGNED_FEATURE_ACCESS"
DOMAIN = b"UCIE_MEMBERSHIP_SUBSCRIPTION_ACCESS_V01\x00"
MAX_RECORD = 2700
MAX_SIGNATURE = 1300
MAX_GRACE_DAYS = 7
MAX_OFFLINE_LEASE_DAYS = 35
MAX_SEQUENCE = 2**31-1
TIERS = {
    "standard": ("error_prevention","virtual_library_and_skillbooks"),
    "complete": tuple(PILLARS),
}
BILLING = frozenset(("monthly","annual"))
STATES = frozenset(("ACTIVE","CANCEL_AT_PERIOD_END","PAST_DUE","SUSPENDED","REVOKED"))
FIELDS = frozenset((
    "schema","scope","service","subscription_id_sha256",
    "recipient_token_sha256","rights_packet_sha256","owner_key_id",
    "plan","billing_interval","billing_status","payment_receipt_sha256",
    "renewal_sequence","product_entitlement_min_serial",
    "issued_utc","period_start_utc","period_end_utc","grace_until_utc",
    "access_lease_expires_utc",
))
SIG_FIELDS = frozenset((
    "schema","scope","owner_key_id","algorithm","payload_sha256","signature_base64",
))
ROUTE_TO_PILLAR={
    "/local/error":"error_prevention",
    "/local/engine":"development_engines_and_skills",
    "/local/library":"virtual_library_and_skillbooks",
    "/local/books":"virtual_library_and_skillbooks",
    "/local/skillbook-run":"virtual_library_and_skillbooks",
    "/local/review":"virtual_library_and_skillbooks",
    "/local/guide/mcp-prompts":"virtual_library_and_skillbooks",
    "/local/guide/mcp-prompts.json":"virtual_library_and_skillbooks",
    "/local/guide/python-scandir":"virtual_library_and_skillbooks",
    "/local/guide/python-scandir.json":"virtual_library_and_skillbooks",
    "/local/evolution":"continuous_evidence_evolution",
}
NON_FEATURE_ROUTES = frozenset(("/","/local","/local/","/local/health","/local/policy"))


class MembershipError(ValueError):
    """No unverified user, payment, product or term can grant membership."""


def _period_end(start:datetime, interval:str) -> datetime:
    """Billing intervals are calendar months/years, never hardcoded 30/365 days."""
    if interval=="monthly":
        year=start.year+(start.month//12)
        month=start.month%12+1
    elif interval=="annual":
        year=start.year+1
        month=start.month
    else:
        raise MembershipError("unknown membership billing cadence")
    if not 1<=year<=9999:
        raise MembershipError("membership calendar overflow")
    day=min(start.day,calendar.monthrange(year,month)[1])
    return start.replace(year=year,month=month,day=day)


def _record_checks(record:dict) -> tuple[datetime,datetime,datetime,datetime,datetime]:
    if type(record) is not dict or set(record)!=FIELDS:
        raise MembershipError("unknown membership fields")
    if (record.get("schema")!=SCHEMA or record.get("scope")!=SCOPE
            or record.get("service")!="UCIE"
            or record.get("plan") not in TIERS
            or record.get("billing_interval") not in BILLING
            or record.get("billing_status") not in STATES
            or type(record.get("renewal_sequence")) is not int
            or not 1<=record["renewal_sequence"]<=MAX_SEQUENCE
            or type(record.get("product_entitlement_min_serial")) is not int
            or not 1<=record["product_entitlement_min_serial"]<=product.MAX_SERIAL
            or type(record.get("owner_key_id")) is not str
            or product.KEYID.fullmatch(record["owner_key_id"]) is None
            or any(not product._hex64(record.get(k)) for k in (
                "subscription_id_sha256","recipient_token_sha256",
                "rights_packet_sha256","payment_receipt_sha256"))
            or record["payment_receipt_sha256"]=="0"*64):
        raise MembershipError("unsigned customer billing or plan assumptions")
    try:
        start=owner._parse_stamp(record["period_start_utc"])
        end=owner._parse_stamp(record["period_end_utc"])
        grace=owner._parse_stamp(record["grace_until_utc"])
        issued=owner._parse_stamp(record["issued_utc"])
        lease=owner._parse_stamp(record["access_lease_expires_utc"])
    except (owner.OwnerMetadataAuthError,ValueError,TypeError) as exc:
        raise MembershipError("invalid canonical membership UTC timestamps") from exc
    if (_period_end(start,record["billing_interval"])!=end
            or issued>grace+timedelta(days=1)
            or grace<end
            or grace>end+timedelta(days=MAX_GRACE_DAYS)
            or record["billing_status"]!="PAST_DUE" and grace!=end
            or lease<=issued
            or lease>issued+timedelta(days=MAX_OFFLINE_LEASE_DAYS)
            or lease>grace):
        raise MembershipError("membership period, grace or short offline access lease invalid")
    return issued,start,end,grace,lease


def _sig(record_bytes:bytes, private:object, *, consent:str) -> bytes:
    """Purpose-separated signer primitive; real owner TTY guard is elsewhere."""
    if consent!="OWNER_SIGN_UCIE_MEMBERSHIP_EXISTING_KEY_ONCE":
        raise MembershipError("separate exact owner membership consent required")
    _,_,private_type,_,get_id=owner._crypto()
    if not isinstance(private,private_type):
        raise MembershipError("existing in-memory Ed25519 private key required")
    record=product._decode(record_bytes,maximum=MAX_RECORD)
    _record_checks(record)
    if get_id(private.public_key())!=record["owner_key_id"]:
        raise MembershipError("owner key purpose identity mismatch")
    signature=private.sign(DOMAIN+record_bytes)
    data=product.canonical({
        "schema":SIG_SCHEMA,"scope":SCOPE,
        "owner_key_id":record["owner_key_id"],
        "algorithm":"Ed25519",
        "payload_sha256":sha256(record_bytes).hexdigest(),
        "signature_base64":b64encode(signature).decode("ascii"),
    })
    if len(data)>MAX_SIGNATURE:
        raise MembershipError("membership detached signature too large")
    return data


def verify_membership(
    record_bytes:bytes,signature_bytes:bytes,public_pem:bytes,*,
    expected_owner_key_id:str,expected_subscription_id_sha256:str,
    expected_recipient_token_sha256:str,expected_rights_packet_sha256:str,
    actual_product_serial:int,min_renewal_sequence:int,now:datetime,
) -> dict:
    """Cryptographically verified membership rights; no payment/network claims.

    Requires independent subscription ID, same recipient/rights and an actual
    verified signed product serial supplied by a caller. Never rely on the
    member's own record as the source of any expected key/recipient/serial.
    """
    if (type(expected_owner_key_id) is not str
            or product.KEYID.fullmatch(expected_owner_key_id) is None
            or not all(product._hex64(x) for x in (
                expected_subscription_id_sha256,expected_recipient_token_sha256,
                expected_rights_packet_sha256))
            or type(actual_product_serial) is not int
            or not 1<=actual_product_serial<=product.MAX_SERIAL
            or type(min_renewal_sequence) is not int
            or not 1<=min_renewal_sequence<=MAX_SEQUENCE
            or type(public_pem) is not bytes
            or not 0<len(public_pem)<=owner.MAX_PEM
            or not isinstance(now,datetime) or now.tzinfo is None):
        raise MembershipError("independent signed-product and membership policies required")
    try:
        raw=product._decode(record_bytes,maximum=MAX_RECORD)
        sig=product._decode(signature_bytes,maximum=MAX_SIGNATURE)
        issued,start,end,grace,lease=_record_checks(raw)
        current=owner._utc(now)
        if (set(sig)!=SIG_FIELDS or sig["schema"]!=SIG_SCHEMA
                or sig["scope"]!=SCOPE or sig["algorithm"]!="Ed25519"
                or sig["owner_key_id"]!=expected_owner_key_id
                or sig["payload_sha256"]!=sha256(record_bytes).hexdigest()
                or raw["owner_key_id"]!=expected_owner_key_id
                or raw["subscription_id_sha256"]!=expected_subscription_id_sha256
                or raw["recipient_token_sha256"]!=expected_recipient_token_sha256
                or raw["rights_packet_sha256"]!=expected_rights_packet_sha256
                or raw["renewal_sequence"]<min_renewal_sequence
                or raw["product_entitlement_min_serial"]>actual_product_serial
                or issued>current+timedelta(minutes=5)):
            raise MembershipError("membership is not owner-approved for this recipient/product")
        encoded=sig.get("signature_base64")
        if type(encoded) is not str or owner.B64.fullmatch(encoded) is None:
            raise MembershipError("invalid membership signature base64")
        data=b64decode(encoded,validate=True)
        if len(data)!=64 or b64encode(data).decode("ascii")!=encoded:
            raise MembershipError("noncanonical membership Ed25519 bytes")
        badsig,serialization,_,public_type,get_id=owner._crypto()
        trust=serialization.load_pem_public_key(public_pem)
        if (not isinstance(trust,public_type)
                or get_id(trust)!=expected_owner_key_id
                or trust.public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo)!=public_pem):
            raise MembershipError("incorrect independent membership public trust")
        try:
            trust.verify(data,DOMAIN+record_bytes)
        except badsig as exc:
            raise MembershipError("invalid membership owner signature") from exc
    except (MembershipError,owner.OwnerMetadataAuthError,product.PrivateEntitlementError):
        raise
    except (ValueError,TypeError,KeyError,UnicodeError,OSError) as exc:
        raise MembershipError("untrusted membership evidence") from exc

    state=raw["billing_status"]
    if state in ("REVOKED","SUSPENDED"):
        phase=state
        allowed=()
    elif current<start:
        phase="NOT_STARTED"
        allowed=()
    elif current<end:
        if current>=lease:
            phase="LEASE_REFRESH_REQUIRED"
            allowed=()
        else:
            phase="ENDING" if state=="CANCEL_AT_PERIOD_END" else "ACTIVE"
            allowed=TIERS[raw["plan"]]
    elif state=="PAST_DUE" and current<grace and current<lease:
        phase="GRACE_READ_ONLY"
        allowed=("virtual_library_and_skillbooks",)
    else:
        phase="EXPIRED"
        allowed=()

    return {
        "schema":SCHEMA,
        "status":"SIGNED_MEMBERSHIP_POLICY_VERIFIED_NOT_PAYMENT_PROVIDER_CERTIFIED",
        "owner_membership_signature_verified":True,
        "membership_phase":phase,
        "plan":raw["plan"],
        "billing_interval":raw["billing_interval"],
        "billing_status":state,
        "renewal_sequence":raw["renewal_sequence"],
        "paid_period_ends_utc":raw["period_end_utc"],
        "grace_until_utc":raw["grace_until_utc"],
        "offline_access_lease_expires_utc":raw["access_lease_expires_utc"],
        "offline_lease_must_be_refreshed_without_rebilling":True,
        "cancel_at_period_end":state=="CANCEL_AT_PERIOD_END",
        "allowed_pillars":list(allowed),
        "seat_or_recipient_bound_to_signed_product":True,
        "independent_payment_provider_event_verified":False,
        "owner_asserted_payment_receipt_sha256_is_not_billing_api_proof":True,
        "membership_is_sale_of_perpetual_install":False,
        "customer_owned_work_products_not_deleted":True,
        "automatic_customer_code_collection":False,
        "customer_distribution_authorized":False,
        "owner_private_key_accessed":False,
        "network_requests":0,
        "operating_database_writes":0,
    }


def route_access(route:str,report:dict) -> bool:
    """All application routes use the SAME verified membership grant."""
    if type(route) is not str or type(report) is not dict:
        return False
    if report.get("owner_membership_signature_verified") is not True:
        return False
    phase=report.get("membership_phase")
    # Signed member may view status/renewal guidance even AFTER expiry
    # or owner revocation; no paid pillar is unlocked by this endpoint.
    if route=="/local/membership":
        return True
    if phase=="GRACE_READ_ONLY":
        # No SkillBook run, source review, code execution or evolution during
        # payment grace. The existing library listing remains accessible.
        return route in ("/", "/local","/local/","/local/health",
                         "/local/policy","/local/library","/local/books")
    pillar=ROUTE_TO_PILLAR.get(route)
    if pillar is not None:
        return phase in ("ACTIVE","ENDING") and pillar in report.get("allowed_pillars",[])
    if route in NON_FEATURE_ROUTES:
        return phase in ("ACTIVE","ENDING")
    return False
