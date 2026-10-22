"""Bounded UCIE Library signed-review / revocation ledger *inspection*.

Reuses existing UCIE Ed25519 helpers; never signs, persists, installs, or
publishes. Signatures authenticate keyholder claims, not human QA quality.
Candidate cards remain non-distributable even when claims authenticate.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ucie_public.policy import PolicyError
from ucie_public.production_release import _parse_date
from ucie_public.rulepack import canonical_json, digest, key_id

from .public_library_graph import preview_library_knowledge_graph

SCHEMA = "UCIE_LIBRARY_SIGNED_REVIEW_LEDGER_INSPECTION_V1"
EVENT_SCHEMA = "UCIE_LIBRARY_SIGNED_REVIEW_DECISION_V1"
REVIEW_FIELDS = frozenset({"source_license", "security", "regression", "release_version"})
EVENT_FIELDS = frozenset({
    "schema", "action", "public_url", "pinned_revision_sha",
    "evidence_sha256", "version_claim", "review_evidence_sha256",
    "review_claims", "serial", "issued_utc", "expires_utc",
})
ENTRY_FIELDS = frozenset({"claim", "qa_signature_hex", "owner_signature_hex"})
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
SIGNATURE = re.compile(r"[0-9a-f]{128}\Z")
VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+\-]{0,31}\Z")
MAX_RECORDS = 24


def inspect_library_signed_review_ledger(
        current: dict, entries: list, *,
        owner_trust: Ed25519PublicKey,
        qa_trust: Ed25519PublicKey,
        previous: dict | None = None,
        at_time: datetime | None = None,
        min_serial: int = 1) -> dict:
    """Inspect signed review *claims* for currently selected public items.

    Caller supplies independently trusted owner and QA public keys. This
    function does not read trust files and cannot ascertain real human
    independence, honest QA, release coverage, or a complete revocation log.
    Signed review is NEVER an authorization to distribute/auto-inject.
    """
    if (not isinstance(owner_trust, Ed25519PublicKey)
            or not isinstance(qa_trust, Ed25519PublicKey)
            or key_id(owner_trust) == key_id(qa_trust)):
        raise PolicyError("independent trusted keyholders are required")
    if (type(min_serial) is not int or not 1 <= min_serial <= 10000000
            or type(entries) is not list or len(entries) > MAX_RECORDS):
        raise PolicyError("invalid bounded signed review ledger")
    now = at_time if at_time is not None else datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise PolicyError("timezone-aware review inspection required")
    now = now.astimezone(timezone.utc)
    # Recompute from strictly validated upstream candidate receipts. Never
    # accept a caller-supplied graph checksum or a self-declared PASS.
    graph = preview_library_knowledge_graph(current, previous)
    cards = {
        node["public_url"]: node
        for node in graph["nodes"]
        if node["kind"] == "UNVERIFIED_PUBLIC_RESEARCH_REFERENCE"
    }
    ledger = {}
    seen_serials = set()
    for entry in entries:
        if type(entry) is not dict or set(entry) != ENTRY_FIELDS:
            raise PolicyError("unexpected signed review entry")
        claim = entry["claim"]
        if type(claim) is not dict or set(claim) != EVENT_FIELDS:
            raise PolicyError("unexpected signed review claim fields")
        url = claim["public_url"]
        card = cards.get(url) if type(url) is str else None
        serial = claim["serial"]
        action = claim["action"]
        if (card is None or claim["schema"] != EVENT_SCHEMA
                or action not in ("REVIEW_ATTESTED", "REVOKE")
                or type(serial) is not int
                or not min_serial <= serial <= 10000000
                or serial in seen_serials
                or type(claim["pinned_revision_sha"]) is not str
                or not SHA40.fullmatch(claim["pinned_revision_sha"])
                or type(claim["evidence_sha256"]) is not str
                or not SHA64.fullmatch(claim["evidence_sha256"])
                or claim["pinned_revision_sha"] != card["pinned_revision_sha"]
                or claim["evidence_sha256"] !=
                    card["evidence_fingerprint_sha256"]):
            raise PolicyError("review claim not bound to approved public revision")
        seen_serials.add(serial)
        earlier = ledger.get(url)
        if earlier is not None and serial <= earlier["serial"]:
            raise PolicyError("nonmonotonic per-reference decision serial")
        if earlier is not None and earlier["state"] == "OWNER_REVOKED" and (
                action != "REVOKE"):
            raise PolicyError("reapproval requires a separate approved recovery gate")

        issued = _parse_date(claim["issued_utc"])
        if issued > now + timedelta(minutes=5):
            raise PolicyError("future signed review decision")

        if (type(entry["owner_signature_hex"]) is not str or
                not SIGNATURE.fullmatch(entry["owner_signature_hex"])):
            raise PolicyError("missing owner signature")
        signed_bytes = canonical_json(claim)
        try:
            owner_trust.verify(bytes.fromhex(entry["owner_signature_hex"]),
                               signed_bytes)
        except (InvalidSignature, ValueError) as exc:
            raise PolicyError("owner signed review claim verification failed") from exc

        if action == "REVIEW_ATTESTED":
            version = claim["version_claim"]
            claimed = claim["review_claims"]
            evidence = claim["review_evidence_sha256"]
            if (type(version) is not str or not VERSION.fullmatch(version)
                    or type(evidence) is not str or not SHA64.fullmatch(evidence)
                    or type(claimed) is not dict
                    or set(claimed) != REVIEW_FIELDS
                    or any(claimed[k] is not True for k in REVIEW_FIELDS)
                    or type(entry["qa_signature_hex"]) is not str
                    or not SIGNATURE.fullmatch(entry["qa_signature_hex"])):
                raise PolicyError("unsigned or incomplete independent-review claim")
            try:
                qa_trust.verify(bytes.fromhex(entry["qa_signature_hex"]),
                                signed_bytes)
            except (InvalidSignature, ValueError) as exc:
                raise PolicyError("QA review signature invalid") from exc
            if type(claim["expires_utc"]) is not str:
                raise PolicyError("signed review expiration required")
            expiry = _parse_date(claim["expires_utc"])
            if expiry <= issued or expiry - issued > timedelta(days=30):
                raise PolicyError("invalid signed review expiration")
            state = ("EXPIRED_SIGNED_REVIEW_CLAIM" if now >= expiry else
                     "SIGNED_REVIEW_CLAIMS_REQUIRE_INDEPENDENT_AUDIT")
            qa_signature_valid = True
        else:
            if (claim["version_claim"] is not None
                    or claim["review_evidence_sha256"] is not None
                    or claim["review_claims"] is not None
                    or claim["expires_utc"] is not None
                    or entry["qa_signature_hex"] is not None):
                raise PolicyError("revocation must be an owner-only tombstone")
            state = "OWNER_REVOKED"
            version = None
            qa_signature_valid = False

        ledger[url] = {
            "serial": serial,
            "state": state,
            "public_url": url,
            "pinned_revision_sha": card["pinned_revision_sha"],
            "evidence_sha256": card["evidence_fingerprint_sha256"],
            "source_version_claim": version,
            "release_version_independently_confirmed": False,
            "owner_signature_valid": True,
            "qa_signature_valid": qa_signature_valid,
            "human_review_independently_confirmed": False,
            "can_publish": False,
            "can_install": False,
        }

    decisions = []
    for url in sorted(cards):
        if url in ledger:
            decisions.append(ledger[url])
        else:
            card = cards[url]
            decisions.append({
                "serial": None,
                "state": "NO_SIGNED_REVIEW_RECORD",
                "public_url": url,
                "pinned_revision_sha": card["pinned_revision_sha"],
                "evidence_sha256": card["evidence_fingerprint_sha256"],
                "source_version_claim": None,
                "release_version_independently_confirmed": False,
                "owner_signature_valid": False,
                "qa_signature_valid": False,
                "human_review_independently_confirmed": False,
                "can_publish": False,
                "can_install": False,
            })
    return {
        "schema": SCHEMA,
        "status": "READ_ONLY_ATTESTATION_LEDGER_INSPECTION_NO_GO",
        "catalog_sha256": graph["catalog_sha256"],
        "reviewed_public_candidate_count": len(decisions),
        "received_signed_event_count": len(entries),
        "signed_review_claim_count": sum(
            x["state"] == "SIGNED_REVIEW_CLAIMS_REQUIRE_INDEPENDENT_AUDIT"
            for x in decisions),
        "signed_revoked_count": sum(x["state"] == "OWNER_REVOKED"
                                    for x in decisions),
        "decisions": decisions,
        "signature_validation_scope": "KEYHOLDER_CLAIMS_ONLY_NOT_HUMAN_QA_PROOF",
        "ledger_is_durable_or_complete": False,
        "rollback_protection_persisted": False,
        "independent_release_coverage_verified": False,
        "distribution_eligible_count": 0,
        "approved_installable_skill_count": 0,
        "distribution_authorized": False,
        "auto_inject_into_projects": False,
        "scheduler_registered": False,
        "operating_database_writes": 0,
        "production_approved": False,
    }
