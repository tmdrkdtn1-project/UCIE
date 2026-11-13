"""UCIE C3.2: verify existing signed PUBLIC-only inbox, then import exactly once.

Real recipient-facing functionality. It consumes an ALREADY provided C3 signed
public PR metadata capsule and a separately provisioned public trust key.
It NEVER creates, reads or exports any owner private key; it cannot enroll
a trust key from the untrusted inbox, attest upstream patches, or grant
customer entitlement.

Recipient root: a distinct clean UCIE checkout, .git present, runtime absent
or empty. Source: exactly three fixed filenames under its already ignored
downloaded/ directory, supplied by an explicitly owner-controlled transfer.
Recipient trust: existing .build_keys public PEM and independently accepted
expected key-id/serial. No arbitrary source/destination path option.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path

from . import local_public_pr_capsule_v01 as cap
from . import local_public_pr_owner_auth_v01 as auth
from . import local_public_pr_trusted_recipient_v01 as viewer
from .local_portable_official_reference_v01 import reference_only
from .local_v1_priority_v01 import require_local_work

SCHEMA = "UCIE_C32_VERIFIED_PUBLIC_METADATA_RECIPIENT_IMPORT_ONCE_V01"
CONSENT = "UCIE_C32_IMPORT_EXISTING_SIGNED_PUBLIC_METADATA_READONLY_ONCE"
STATUS = "C32_OFFLINE_PUBLIC_METADATA_IMPORTED_OWNER_KEY_MATCH_ONLY_NO_GO"
PREFLIGHT_STATUS = "C32_VERIFIED_PUBLIC_INBOX_READONLY_NOT_IMPORTED_NO_GO"
FAIL_STATUS = "C32_UNTRUSTED_OR_INCOMPLETE_PUBLIC_INBOX_FAIL_CLOSED_NO_GO"
FILES = (
    (cap.FILE, cap.MAX_BYTES),
    (cap.PIN, 65),
    (auth.SIGNATURE_FILE, auth.MAX_ATTESTATION),
)


class RecipientImportError(ValueError):
    """Missing independently approved public trust or unsafe recipient state."""


def _recipient(root: Path, *, expected_owner_key_id: str, min_serial: int) -> Path:
    if (not isinstance(root, Path) or not root.is_absolute()
            or type(expected_owner_key_id) is not str
            or auth.KEYID.fullmatch(expected_owner_key_id) is None
            or type(min_serial) is not int or not 1 <= min_serial <= auth.MAX_SERIAL):
        raise RecipientImportError("explicit trusted recipient policy required")
    cap._root(root)
    if reference_only(root) is not True:
        raise RecipientImportError("existing recipient operating runtime must not be changed")
    return root


def _verified_inbox(root: Path, *, expected_owner_key_id: str,
                    min_serial: int, now: datetime) -> tuple[dict[str, bytes], dict]:
    """No operations outside four fixed UCIE-relative PUBLIC file paths."""
    inbox = root / "downloaded"  # already gitignored; never scan unrelated files
    if inbox.is_symlink() or not inbox.is_dir():
        raise RecipientImportError("preexisting UCIE-only public inbox required")
    # Public trust is independent: NEVER read a trust key from the inbox.
    pem = auth._safe_small(root / ".build_keys" / auth.TRUST_NAME,
                           max_bytes=auth.MAX_PEM)
    contents = {
        name: auth._safe_small(inbox / name, max_bytes=max_bytes)
        for name, max_bytes in FILES
    }
    raw = contents[cap.FILE]
    digest = sha256(raw).hexdigest()
    if contents[cap.PIN] != (digest + "\n").encode("ascii"):
        raise RecipientImportError("public metadata source hash mismatch")
    verified = auth.verify_owner_metadata_bytes(
        raw, contents[auth.SIGNATURE_FILE], pem,
        expected_owner_key_id=expected_owner_key_id,
        min_serial=min_serial, now=now)
    inspected = cap.inspect_capsule(raw, digest)
    if (verified.get("signature_cryptographically_verified") is not True
            or verified.get("owner_public_key_matches_supplied_trust_pin") is not True
            or verified.get("out_of_band_owner_approval_independently_proven") is not False
            or verified.get("customer_distribution_authorized") is not False
            or inspected.get("status") != cap.RECEIVER_STATUS
            or inspected.get("human_approved") is not False
            or inspected.get("signature_verified") is not False
            or inspected.get("customer_distribution_authorized") is not False):
        raise RecipientImportError("owner review was improperly promoted")
    return contents, verified


def import_existing_signed_public_once(
        root: Path, *, expected_owner_key_id: str, min_serial: int,
        consent: str, apply: bool = False,
        now: datetime | None = None) -> dict:
    """Same verification for non-mutating preview and explicit O_EXCL commit.

    Apply NEVER overwrites existing files or mutates the operating database.
    A mid-write failure can leave incomplete fixed public files but remains
    fail-closed; no unsafe deletion/rollback or automatic retry is performed.
    """
    if consent != CONSENT or type(apply) is not bool:
        raise RecipientImportError("specific public inbox import consent required")
    require_local_work("LOCAL_APP")
    root = _recipient(root, expected_owner_key_id=expected_owner_key_id,
                      min_serial=min_serial)
    checked_time = datetime.now(timezone.utc) if now is None else now
    contents, proof = _verified_inbox(
        root, expected_owner_key_id=expected_owner_key_id,
        min_serial=min_serial, now=checked_time)
    # Detect ALL name collisions *before* any writes. An existing file is
    # never automatically overwritten, even when checksum is identical.
    targets = [root / name for name, _ in FILES]
    if any(p.exists() or p.is_symlink() for p in targets):
        raise RecipientImportError("recipient already has a public metadata file")
    report = {
        "schema": SCHEMA,
        "status": PREFLIGHT_STATUS if not apply else STATUS,
        "signed_serial": proof["signed_serial"],
        "owner_key_id": proof["owner_key_id"],
        "metadata_capsule_sha256": proof["metadata_capsule_sha256"],
        "signature_cryptographically_verified": True,
        "owner_public_key_matches_supplied_trust_pin": True,
        "out_of_band_owner_approval_independently_proven": False,
        "source_linkage_independently_attested_on_recipient": False,
        "independent_upstream_fix_verified": False,
        "human_approved": False,
        "customer_distribution_authorized": False,
        "operating_database_writes": 0,
        "external_network_requests": 0,
        "owner_private_key_read_or_created": False,
        "copied_public_metadata_files": 0,
    }
    if not apply:
        return report
    # All bytes and trust verified first; fail closed without cleanup upon
    # interruption. Use binary/no-follow/exclusive-create file flags.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    for path, (name, _) in zip(targets, FILES):
        with os.fdopen(os.open(path, flags, 0o600), "wb") as f:
            f.write(contents[name])
            f.flush()
            os.fsync(f.fileno())
    # Re-open exact recipient bytes and reverify: no optimistic "PASS"
    # receipt if files are altered or partially written.
    received, reverified = viewer.read_signed_public_review(
        root, expected_owner_key_id=expected_owner_key_id,
        min_serial=min_serial, now=checked_time)
    if (received.get("selected_count", 0) < 1
            or reverified.get("metadata_capsule_sha256") !=
                proof["metadata_capsule_sha256"]
            or reverified.get("signed_serial") != proof["signed_serial"]):
        raise RecipientImportError("post-copy trusted source recheck failed")
    report["copied_public_metadata_files"] = len(FILES)
    report["unverified_public_candidate_count"] = received["selected_count"]
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE C3.2 signed public inbox import into a clean UCIE recipient")
    parser.add_argument("--recipient-ucie-root", type=Path, required=True)
    parser.add_argument("--expected-owner-key-id", required=True)
    parser.add_argument("--min-serial", type=int, required=True)
    parser.add_argument("--apply-once", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        if (args.serve and not args.apply_once
                or args.port != 0 and not 1024 <= args.port <= 65535):
            raise RecipientImportError("explicit apply and bounded loopback port required")
        receipt = import_existing_signed_public_once(
            args.recipient_ucie_root,
            expected_owner_key_id=args.expected_owner_key_id,
            min_serial=args.min_serial, consent=CONSENT,
            apply=args.apply_once)
        print(json.dumps(receipt, sort_keys=True), flush=True)
        if args.serve:
            handler = viewer.make_trusted_handler(
                args.recipient_ucie_root,
                expected_owner_key_id=args.expected_owner_key_id,
                min_serial=args.min_serial)
            from .local_v1_app_v01 import LOCAL_SERVER_CLASS
            with LOCAL_SERVER_CLASS(("127.0.0.1", args.port), handler) as server:
                print(json.dumps({
                    "schema": SCHEMA, "status": "C32_READONLY_LOCAL_PREVIEW_RUNNING_NO_GO",
                    "local_url": "http://127.0.0.1:" + str(server.server_port) +
                                 viewer.ROUTE,
                    "customer_distribution_authorized": False,
                    "owner_private_key_read_or_created": False,
                }, sort_keys=True), flush=True)
                server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        return 0
    except (ValueError, TypeError, KeyError, OSError):
        print(json.dumps({
            "schema": SCHEMA, "status": FAIL_STATUS,
            "customer_distribution_authorized": False,
            "owner_private_key_read_or_created": False,
            "operating_database_writes": 0,
        }, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
