"""UCIE B2 owner-gated portable PUBLIC-ONLY PR metadata capsule.

Read-only Stage10/15 -> Stage12 source-linked handoff is the ONLY input.
Never copy SQLite, public source text, PR titles, patches, commands, paths,
credentials, or customer/other-project data. Receiver rederives every W02
library identity, checks exact bytes and owner-supplied SHA256, and treats it
as UNSIGNED, UNVERIFIED candidate metadata, not an authentic upstream fix.

No snapshot is generated automatically from a miner or scheduler. A separate
explicit local owner consent is mandatory for file creation; the default CLI
prints only a bounded preview, never the metadata payload.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re

from .library_entry import build_library_entry
from .library_search import (
    ALLOWED_KINDS, MAX_PAGE_OFFSET, SCHEMA as W04_SCHEMA,
    _filters,
)
from .product_plan import APPROVED_REPOSITORIES
from .verification_handoff import _checked_handoff, prepare_verification_handoff

SCHEMA = "UCIE_B2_PORTABLE_PUBLIC_PR_METADATA_CAPSULE_V01"
STATUS = "PUBLIC_ONLY_SOURCE_LINKED_AT_CAPTURE_UNSIGNED_REVIEW_ONLY_NO_GO"
RECEIVER_STATUS = "SELF_HASH_MATCHED_SOURCE_NOT_INDEPENDENTLY_ATTESTED_NO_GO"
FILE = ".ucie_b2_public_pr_metadata_v01.json"
PIN = ".ucie_b2_public_pr_metadata_v01.sha256"
MAX_ITEMS = 48
MAX_BYTES = 140_000
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
CONSENT = "UCIE_OWNER_PUBLIC_METADATA_LOCAL_EXPORT_ONCE"
ROW_KEYS = frozenset({
    "library_item_id", "review_candidate_sha256", "kind", "source_id",
    "public_url", "evidence_reference", "domain", "purpose_code",
    "skill_profile", "revision_hint", "evidence_sha256",
    "version_scope_claim", "lifecycle", "signature_status",
    "license_status", "human_approved", "export_allowed",
})
CAPSULE_KEYS = frozenset({
    "schema", "status", "source_handoff_status", "source_linkage_at_capture",
    "source_linkage_reverified_on_recipient", "source_text_included",
    "snapshot_signed", "human_approved", "export_allowed",
    "customer_distribution_authorized", "network_requests",
    "operating_database_writes", "limit", "selected_count",
    "source_linked_count", "omitted_count", "items_sha256", "items",
})


class PublicCapsuleError(ValueError):
    """Strict public-only metadata contract, never a customer import GO."""


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def _row(task: dict) -> dict:
    if type(task) is not dict:
        raise PublicCapsuleError("source-linked public review task required")
    origin, reference = task.get("source"), task.get("reference")
    if origin not in APPROVED_REPOSITORIES:
        raise PublicCapsuleError("review task from unapproved source")
    if (task.get("status") != "UNVERIFIED_CANDIDATE_ONLY"
            or task.get("approval") is not False):
        raise PublicCapsuleError("review task falsely approved")
    kind = ("PREVENTION_RULE" if task.get("stage6_candidate") is not None
            else "PUBLIC_TECHNICAL_EVIDENCE")
    entry = build_library_entry({
        "kind": kind,
        "source_id": "repo:" + origin,
        "evidence_reference": reference,
        "evidence_sha256": task.get("evidence_sha256"),
        "purpose_code": task.get("pattern_code"),
        "version_scope": "UNDETERMINED",
        "dependencies": [],
    })
    candidate_id = task.get("candidate_id_sha256")
    if (type(candidate_id) is not str or HEX64.fullmatch(candidate_id) is None
            or task.get("skill_id") != entry["skill_profile"]
            or entry["human_approved"] is not False
            or entry["export_allowed"] is not False
            or entry["entry_status"] != "UNVERIFIED_CANDIDATE_ONLY"
            or entry["source_license_status"] != "NOT_ATTESTED_PER_REVISION"):
        raise PublicCapsuleError("invalid source-bound public-only metadata")
    return {
        "library_item_id": entry["library_item_id"],
        "review_candidate_sha256": candidate_id,
        "kind": entry["kind"],
        "source_id": entry["source_id"],
        "public_url": entry["public_url"],
        "evidence_reference": entry["evidence_reference"],
        "domain": entry["domain"],
        "purpose_code": entry["purpose_code"],
        "skill_profile": entry["skill_profile"],
        "revision_hint": entry["revision_hint"],
        "evidence_sha256": entry["evidence_sha256"],
        "version_scope_claim": entry["version_scope_claim"],
        "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
        "signature_status": "NOT_ATTESTED_BY_THIS_SEARCH",
        "license_status": entry["source_license_status"],
        "human_approved": False,
        "export_allowed": False,
    }


def build_capsule(handoff: dict, *, limit: int = MAX_ITEMS) -> bytes:
    """Sanitize ONLY the existing read-only validated complete handoff."""
    if type(limit) is not int or not 1 <= limit <= MAX_ITEMS:
        raise PublicCapsuleError("public metadata limit outside bounds")
    complete, tasks = _checked_handoff(handoff)
    if not complete or not tasks:
        raise PublicCapsuleError("absent or incomplete public source linkage")
    all_rows = [_row(task) for task in tasks]
    all_rows.sort(key=lambda r: (
        r["source_id"], r["evidence_reference"], r["evidence_sha256"],
        r["library_item_id"], r["review_candidate_sha256"],
    ))
    if (len({r["review_candidate_sha256"] for r in all_rows}) != len(all_rows)
            or len({(r["source_id"], r["evidence_reference"],
                     r["evidence_sha256"], r["purpose_code"])
                    for r in all_rows}) != len(all_rows)):
        raise PublicCapsuleError("duplicate public revision metadata")
    # Balance a partial owner-preview across all existing approved sources.
    # No source gets all 48 slots just because of ASCII sort order.
    buckets = {source: [] for source in APPROVED_REPOSITORIES}
    for row in all_rows:
        buckets[row["source_id"].removeprefix("repo:")].append(row)
    picked = []
    for index in range(limit):
        source = APPROVED_REPOSITORIES[index % len(APPROVED_REPOSITORIES)]
        if buckets[source]:
            picked.append(buckets[source].pop(0))
        elif any(buckets.values()):
            # If this source is exhausted, take from the first still-present.
            next_source = next(k for k in APPROVED_REPOSITORIES if buckets[k])
            picked.append(buckets[next_source].pop(0))
        else:
            break
    selected = sorted(picked, key=lambda r: (
        r["source_id"], r["evidence_reference"], r["evidence_sha256"],
        r["library_item_id"], r["review_candidate_sha256"],
    ))
    result = {
        "schema": SCHEMA,
        "status": STATUS,
        "source_handoff_status": "LINKED_UNVERIFIED_NO_GO",
        "source_linkage_at_capture": True,
        "source_linkage_reverified_on_recipient": False,
        "source_text_included": False,
        "snapshot_signed": False,
        "human_approved": False,
        "export_allowed": False,
        "customer_distribution_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "limit": limit,
        "selected_count": len(selected),
        "source_linked_count": len(all_rows),
        "omitted_count": len(all_rows) - len(selected),
        "items_sha256": sha256(_canonical(selected)).hexdigest(),
        "items": selected,
    }
    data = _canonical(result)
    if len(data) > MAX_BYTES:
        raise PublicCapsuleError("portable public metadata capsule too large")
    return data


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict:
    if len({key for key, _ in pairs}) != len(pairs):
        raise PublicCapsuleError("duplicate JSON fields in portable metadata")
    return dict(pairs)


def inspect_capsule(data: bytes, expected_sha256: str) -> dict:
    """Recipient checks exact owner supplied bytes, NOT upstream authenticity."""
    if (type(data) is not bytes or not 0 < len(data) <= MAX_BYTES
            or type(expected_sha256) is not str
            or HEX64.fullmatch(expected_sha256) is None
            or sha256(data).hexdigest() != expected_sha256):
        raise PublicCapsuleError("untrusted portable public metadata bytes or digest")
    try:
        content = json.loads(data.decode("ascii"),
                             object_pairs_hook=_no_duplicates,
                             parse_constant=lambda _: (_ for _ in ()).throw(
                                 PublicCapsuleError("non-finite metadata")))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise PublicCapsuleError("invalid portable public metadata JSON") from exc
    if type(content) is not dict or set(content) != CAPSULE_KEYS:
        raise PublicCapsuleError("unexpected portable source metadata fields")
    if data != _canonical(content):
        raise PublicCapsuleError("noncanonical portable source bytes")
    if (content.get("schema") != SCHEMA or content.get("status") != STATUS
            or content.get("source_handoff_status") != "LINKED_UNVERIFIED_NO_GO"
            or content.get("source_linkage_at_capture") is not True
            or any(content.get(flag) is not False for flag in (
                "source_linkage_reverified_on_recipient",
                "source_text_included", "snapshot_signed", "human_approved",
                "export_allowed", "customer_distribution_authorized"))
            or content.get("network_requests") != 0
            or content.get("operating_database_writes") != 0):
        raise PublicCapsuleError("forged public capsule approval/provenance")
    rows = content.get("items")
    limit = content.get("limit")
    count = content.get("selected_count")
    total = content.get("source_linked_count")
    missing = content.get("omitted_count")
    if (type(rows) is not list or type(limit) is not int
            or not 1 <= limit <= MAX_ITEMS
            or type(count) is not int or not 1 <= count <= limit
            or type(total) is not int or not count <= total <= 10_000
            or type(missing) is not int or missing != total - count
            or len(rows) != count
            or content.get("items_sha256") != sha256(_canonical(rows)).hexdigest()):
        raise PublicCapsuleError("portable public metadata counts or hash drift")
    for row in rows:
        if type(row) is not dict or set(row) != ROW_KEYS:
            raise PublicCapsuleError("public metadata row contains forbidden fields")
        if (type(row.get("review_candidate_sha256")) is not str
                or HEX64.fullmatch(row["review_candidate_sha256"]) is None
                or row.get("kind") not in ALLOWED_KINDS
                or row.get("lifecycle") != "UNVERIFIED_CANDIDATE_ONLY"
                or row.get("signature_status") != "NOT_ATTESTED_BY_THIS_SEARCH"
                or row.get("license_status") != "NOT_ATTESTED_PER_REVISION"
                or row.get("human_approved") is not False
                or row.get("export_allowed") is not False):
            raise PublicCapsuleError("untrusted portable public review row")
        origin = row.get("source_id")
        if (type(origin) is not str or not origin.startswith("repo:")
                or origin.removeprefix("repo:") not in APPROVED_REPOSITORIES):
            raise PublicCapsuleError("portable row outside approved public source")
        # Rebuild every W02 identity from the exact approved public reference.
        derived = build_library_entry({
            "kind": row["kind"], "source_id": origin,
            "evidence_reference": row.get("evidence_reference"),
            "evidence_sha256": row.get("evidence_sha256"),
            "purpose_code": row.get("purpose_code"),
            "version_scope": "UNDETERMINED", "dependencies": [],
        })
        for field, from_derived in (
            ("library_item_id", "library_item_id"),
            ("source_id", "source_id"), ("kind", "kind"),
            ("public_url", "public_url"),
            ("evidence_reference", "evidence_reference"),
            ("domain", "domain"), ("purpose_code", "purpose_code"),
            ("skill_profile", "skill_profile"),
            ("revision_hint", "revision_hint"),
            ("evidence_sha256", "evidence_sha256"),
            ("version_scope_claim", "version_scope_claim"),
        ):
            if type(row.get(field)) is not str or row[field] != derived[from_derived]:
                raise PublicCapsuleError("portable revision not bound to W02 identity")
    if (len({r["review_candidate_sha256"] for r in rows}) != len(rows)
            or len({r["library_item_id"] for r in rows}) != len(rows)
            or rows != sorted(rows, key=lambda r: (
                r["source_id"], r["evidence_reference"], r["evidence_sha256"],
                r["library_item_id"], r["review_candidate_sha256"],
            ))):
        raise PublicCapsuleError("duplicate or reordered portable source revisions")
    # Important: this checksum is NOT a signature and cannot prove that an
    # attacker did not replace both capsule and its adjacent hash receipt.
    return {
        "schema": SCHEMA, "status": RECEIVER_STATUS,
        "items": rows, "selected_count": count, "omitted_count": missing,
        "self_sha256": expected_sha256,
        "source_linkage_independently_attested_on_recipient": False,
        "signature_verified": False, "human_approved": False,
        "customer_distribution_authorized": False,
        "operating_database_writes": 0, "network_requests": 0,
    }


def _root(root: Path) -> Path:
    if (not isinstance(root, Path) or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()
            or (root / ".git").is_symlink() or not (root / ".git").is_dir()):
        raise PublicCapsuleError("dedicated UCIE checkout root required")
    return root


def read_optional_capsule(root: Path) -> dict | None:
    """Read only the exact two UCIE-named files in an otherwise empty runtime.

    This does not grant either file official provenance/authentication.
    The caller must already have checked the root's empty-runtime policy.
    """
    root = _root(root)
    src, pin = root / FILE, root / PIN
    if not src.exists() and not pin.exists():
        return None
    if (src.is_symlink() or pin.is_symlink() or not src.is_file()
            or not pin.is_file() or src.stat().st_size > MAX_BYTES
            or pin.stat().st_size != 65):
        raise PublicCapsuleError("incomplete or symlinked portable PR candidate files")
    expected = pin.read_text("ascii")
    if len(expected) != 65 or expected[-1] != "\n":
        raise PublicCapsuleError("invalid adjacent hash receipt")
    return inspect_capsule(src.read_bytes(), expected[:-1])


def search_capsule(capsule: dict, *, query: str = "",
                   source_id: str | None = None, limit: int = 10,
                   offset: int = 0) -> dict:
    """Pure bounded existing-W04-shaped search over validated public metadata."""
    if (type(capsule) is not dict or capsule.get("schema") != SCHEMA
            or capsule.get("status") != RECEIVER_STATUS
            or capsule.get("signature_verified") is not False
            or capsule.get("human_approved") is not False
            or capsule.get("customer_distribution_authorized") is not False
            or type(offset) is not int or not 0 <= offset <= MAX_PAGE_OFFSET):
        raise PublicCapsuleError("not a source-bounded unsigned capsule")
    q, kind, domain, source, bounded_limit, group = _filters(
        query=query, kind=None, domain=None, source_id=source_id,
        limit=limit, group_revisions=False,
    )
    if ".." in query or query.startswith("/"):
        raise PublicCapsuleError("portable query cannot be a path")
    if source is not None and source.removeprefix("repo:") not in APPROVED_REPOSITORIES:
        raise PublicCapsuleError("unapproved portable source filter")
    if kind is not None or domain is not None or group:
        raise PublicCapsuleError("unexpected portable filter")
    items = capsule["items"]
    matched = []
    for row in items:
        if source is not None and row["source_id"] != source:
            continue
        searchable = " ".join((row["kind"], row["source_id"], row["domain"],
                               row["skill_profile"], row["purpose_code"],
                               row["evidence_reference"])).casefold()
        if not q or q in searchable:
            matched.append(row)
    page = [dict(row) for row in matched[offset:offset + limit]]
    result = {
        "schema": W04_SCHEMA,
        "status": "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
        "portable_reference_mode":
            "OFFICIAL_DOCUMENT_REFERENCES_ONLY_NO_CAPTURED_PR_LEDGER_NO_GO",
        "portable_snapshot_status": RECEIVER_STATUS,
        "query": q, "total_matches": len(matched),
        "returned_count": len(page), "items": page,
        "source_filter": source,
        "network_requests": 0, "operating_database_writes": 0,
        "approved_or_exportable_items": 0,
        "auto_promoted": False, "v1_library_accepted": False,
        "snapshot_signed": False,
        "independent_upstream_source_attested": False,
        "unreviewed_source_revisions_omitted": capsule["omitted_count"],
    }
    if offset:
        result["page_offset"] = offset
    return result


def capture_preview(root: Path) -> dict:
    """Owner-only read of existing Stage10/15/12; no payload printed or written."""
    root = _root(root)
    capsule = build_capsule(prepare_verification_handoff(root))
    attested = inspect_capsule(capsule, sha256(capsule).hexdigest())
    return {
        "schema": SCHEMA,
        "status": "OWNER_READONLY_PUBLIC_METADATA_PREVIEW_NO_GO",
        "candidate_metadata_rows": attested["selected_count"],
        "unselected_source_revisions": attested["omitted_count"],
        "local_snapshot_sha256_if_owner_consents": attested["self_sha256"],
        "original_pr_text_or_code_included": False,
        "operating_database_writes": 0, "local_capsule_written": False,
        "customer_distribution_authorized": False,
    }


def export_once(root: Path, *, consent: str) -> dict:
    """Separate, explicit OWNER LOCAL-ONLY one-time file generation.

    Never callable from the web server, miner schedule or any import handler.
    No overwrite, DB copy or transfer. A partial pair fails closed on import.
    """
    if consent != CONSENT:
        raise PublicCapsuleError("specific explicit owner-local export consent required")
    root = _root(root)
    # OWNER export is confined to the pre-existing Git-ignored downloaded/
    # directory. The separate recipient must explicitly place a reviewed copy
    # at its own root. No implicit repo upload, install or transfer occurs.
    out = root / "downloaded"
    if out.is_symlink() or not out.is_dir():
        raise PublicCapsuleError("existing ignored UCIE downloaded directory required")
    src, pin = out / FILE, out / PIN
    if src.exists() or pin.exists() or src.is_symlink() or pin.is_symlink():
        raise PublicCapsuleError("immutable one-time capsule already present")
    payload = build_capsule(prepare_verification_handoff(root))
    digest = sha256(payload).hexdigest()
    inspect_capsule(payload, digest)
    # Destination is strictly inside this UCIE root, never an owner-supplied
    # path. O_EXCL prevents overwrite; pin committed LAST.
    fd = os.open(src, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)
    fd = os.open(pin, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write((digest + "\n").encode("ascii"))
    return {
        "schema": SCHEMA,
        "status": "OWNER_LOCAL_ONLY_UNSIGNED_METADATA_FILES_CREATED_NO_GO",
        "capsule_sha256": digest,
        "file_names": ["downloaded/" + FILE, "downloaded/" + PIN],
        "operating_database_writes": 0,
        "customer_distribution_authorized": False,
        "files_distributed_or_uploaded": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE private owner public metadata capsule")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--preview-owner", action="store_true")
    actions.add_argument("--export-once", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    try:
        if args.preview_owner:
            report = capture_preview(root)
        else:
            typed = input("UCIE one-time local-only public metadata consent: ").strip()
            report = export_once(root, consent=typed)
    except (ValueError, OSError, EOFError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED_NO_EXPORT",
                          "error_type": type(exc).__name__,
                          "customer_distribution_authorized": False}))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
