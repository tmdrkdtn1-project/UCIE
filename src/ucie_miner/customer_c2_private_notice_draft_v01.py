"""UCIE C2 owner-local original-license NOTICE DRAFT; NEVER a customer release.

Reads only the already exported five owner C2 license texts after the existing
SHA-pinned owner auditor passes, then makes ONE private, O_EXCL review copy.
Does not inspect wheel binaries, fetch files, approve rights, or attach a
customer distribution packet. Missing upstream OpenSSL NOTICE and human
decisions remain explicit blockers.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys

from . import customer_c2_existing_owner_license_integrity_v01 as audit
from . import customer_c2_owner_license_review_packet_v01 as original
from .customer_owner_wheelhouse_acquire_v01 import PINNED

SCHEMA = "UCIE_C2_OWNER_PRIVATE_NOTICE_DRAFT_V01"
STATUS = "FIVE_ORIGINAL_LICENSE_COPIES_PRIVATE_REVIEW_ONLY_NO_GO"
DRAFT_NAME = "ucie_c2_private_notice_draft_v01"
CONSENT = "UCIE_C2_PRIVATE_NOTICE_DRAFT_ONLY"
REQUIRED_BLOCKERS = (
    "ORIGINAL_VENDOR_LICENSE_AND_NOTICE_HUMAN_REVIEW_REQUIRED",
    "OPENSSL_LICENSE_AND_EMBEDDED_NOTICE_NOT_ASSEMBLED",
    "UCIE_AND_SKILLBOOK_RIGHTSHOLDER_APPROVAL_REQUIRED",
    "OPENSSL_4_0_3_RISK_DISPOSITION_REQUIRED",
    "CUSTOMER_CONTRACT_AND_OWNER_SIGNATURE_NOT_PRESENT",
)
HOLD_TEXT = (
    "UCIE PRIVATE REVIEW DRAFT - NOT A CUSTOMER LICENSE/NOTICE APPENDIX\n"
    "These five bytes-preserved originals are UNTRUSTED inputs for a human.\n"
    "No legal or security rights have been approved by this technical step.\n"
    "OpenSSL statically embedded license/NOTICE, first-party and SkillBook\n"
    "rights, third-party notices, customer contract and owner signature\n"
    "are NOT assembled, verified or granted by this draft.\n"
    "Do not distribute, publish, sign or advertise a customer GO.\n"
)
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
MAX_MANIFEST = 35_000
MAX_FILE = original.MAX_LICENSE_BYTES


class NoticeDraftError(ValueError):
    """Fail-closed; technical copy cannot become human rights approval."""


def _unique(pairs: list[tuple[str, object]]) -> dict:
    if len({k for k, _ in pairs}) != len(pairs):
        raise NoticeDraftError("duplicate review metadata field")
    return dict(pairs)


def _json(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_MANIFEST:
        raise NoticeDraftError("invalid bounded review metadata")
    try:
        data = json.loads(raw.decode("ascii"), object_pairs_hook=_unique)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise NoticeDraftError("untrusted owner review metadata") from exc
    if type(data) is not dict:
        raise NoticeDraftError("review metadata object required")
    return data


def _canonical(data: dict) -> bytes:
    return (json.dumps(data, sort_keys=True, ensure_ascii=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("ascii")


def _read_originals(packet: Path) -> list[tuple[str, bytes]]:
    manifest_path = packet / "review_manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise NoticeDraftError("existing owner review manifest missing")
    manifest = _json(manifest_path.read_bytes())
    groups = manifest.get("reviewed_packages")
    if type(groups) is not list or len(groups) != len(PINNED):
        raise NoticeDraftError("unexpected reviewed vendor groups")
    if {(r.get("distribution"), r.get("version")) for r in groups
        if type(r) is dict} != set(PINNED):
        raise NoticeDraftError("pinned vendor identity drift")
    found: dict[str, bytes] = {}
    total = 0
    for row in groups:
        name, version = row["distribution"], row["version"]
        entries = row.get("declared_license_texts")
        if type(entries) is not list or not entries:
            raise NoticeDraftError("missing original license list")
        for item in entries:
            if type(item) is not dict:
                raise NoticeDraftError("invalid original license item")
            relative = item.get("relative_review_path")
            prefix = "license-text/" + name + "-" + version + "/"
            if (type(relative) is not str or not relative.startswith(prefix)
                    or not original._safe_relative_name(relative[len(prefix):])
                    or relative in found or type(item.get("bytes")) is not int
                    or not 0 < item["bytes"] <= MAX_FILE
                    or type(item.get("sha256")) is not str
                    or HEX64.fullmatch(item["sha256"]) is None):
                raise NoticeDraftError("original license path/digest not bounded")
            file_path = packet.joinpath(*relative.split("/"))
            parent = file_path.parent
            while parent != packet:
                if parent.is_symlink() or not parent.is_dir():
                    raise NoticeDraftError("linked original license directory")
                parent = parent.parent
            if (file_path.is_symlink() or not file_path.is_file()
                    or file_path.stat().st_size != item["bytes"]):
                raise NoticeDraftError("original license missing or changed")
            raw = file_path.read_bytes()
            if len(raw) != item["bytes"] or sha256(raw).hexdigest() != item["sha256"]:
                raise NoticeDraftError("original license SHA changed")
            found[relative] = raw
            total += len(raw)
            if total > audit.MAX_ALL_BYTES:
                raise NoticeDraftError("too many original license bytes")
    if len(found) != 5 or total != manifest.get("license_total_bytes"):
        raise NoticeDraftError("exact original five-license inventory required")
    return sorted(found.items())


def _private_target(folder: Path) -> Path:
    if (not isinstance(folder, Path) or not folder.is_absolute()
            or folder.name != DRAFT_NAME or folder.parent.name != "downloaded"
            or folder.parent.parent.name.lower() != "ucie"
            or folder.parent.is_symlink() or folder.parent.parent.is_symlink()):
        raise NoticeDraftError("draft must remain in UCIE owner-private downloaded folder")
    return folder


def _manifest(source_sha: str, entries: list[tuple[str, bytes]]) -> dict:
    return {
        "schema": SCHEMA, "status": STATUS,
        "source_review_entries_sha256": source_sha,
        "original_licenses": [
            {"source_relative_review_path": rel,
             "private_review_filename": f"LICENSE_ORIGINAL_{i:02d}.txt",
             "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
            for i, (rel, raw) in enumerate(entries, 1)
        ],
        "original_count": 5, "open_ssl_embedded_notice_included": False,
        "actual_human_vendor_notice_review_completed": False,
        "first_party_skillbook_rights_approved": False,
        "openssl_security_risk_approved": False,
        "owner_customer_contract_signed": False,
        "customer_distribution_authorized": False,
        "release_package_created": False,
        "network_requests": 0, "operating_database_writes": 0,
        "release_blockers": list(REQUIRED_BLOCKERS),
    }


def verify_private_notice_draft(folder: Path, expected_review_entries_sha256: str) -> dict:
    """Verify the locally staged copy. Never asserts rights or external trust."""
    _private_target(folder)
    if (folder.is_symlink() or not folder.is_dir()
            or type(expected_review_entries_sha256) is not str
            or HEX64.fullmatch(expected_review_entries_sha256) is None):
        raise NoticeDraftError("untrusted owner draft or independent SHA")
    manifest_file = folder / "review_manifest.json"
    if manifest_file.is_symlink() or not manifest_file.is_file():
        raise NoticeDraftError("private review manifest missing")
    data = _json(manifest_file.read_bytes())
    rows = data.get("original_licenses")
    if (type(rows) is not list or len(rows) != 5
            or data.get("source_review_entries_sha256") != expected_review_entries_sha256):
        raise NoticeDraftError("original review binding differs")
    expected_names = {"review_manifest.json", "NOTICE_REVIEW_REQUIRED.txt"}
    for i, row in enumerate(rows, 1):
        name = f"LICENSE_ORIGINAL_{i:02d}.txt"
        if (type(row) is not dict
                or set(row) != {"source_relative_review_path", "private_review_filename",
                               "sha256", "bytes"}
                or row.get("private_review_filename") != name
                or type(row.get("source_relative_review_path")) is not str
                or not row["source_relative_review_path"].startswith("license-text/")
                or type(row.get("sha256")) is not str
                or HEX64.fullmatch(row["sha256"]) is None
                or type(row.get("bytes")) is not int
                or not 0 < row["bytes"] <= MAX_FILE):
            raise NoticeDraftError("invalid private notice file metadata")
        file = folder / name
        if file.is_symlink() or not file.is_file() or file.stat().st_size != row["bytes"]:
            raise NoticeDraftError("private notice original missing/linked")
        if sha256(file.read_bytes()).hexdigest() != row["sha256"]:
            raise NoticeDraftError("private notice original was modified")
        expected_names.add(name)
    note = folder / "NOTICE_REVIEW_REQUIRED.txt"
    if note.is_symlink() or not note.is_file() or note.read_bytes() != HOLD_TEXT.encode("ascii"):
        raise NoticeDraftError("release HOLD notice removed or modified")
    if any(p.is_symlink() or not p.is_file() for p in folder.iterdir()):
        raise NoticeDraftError("linked/unexpected private draft content")
    if {p.name for p in folder.iterdir()} != expected_names:
        raise NoticeDraftError("unexpected private draft content")
    expected = _manifest(expected_review_entries_sha256, [
        (row["source_relative_review_path"], (folder / row["private_review_filename"]).read_bytes())
        for row in rows
    ])
    if data != expected:
        raise NoticeDraftError("NO_GO review contract or untrusted metadata modified")
    return {"schema": SCHEMA, "status": STATUS,
            "exact_existing_original_license_copies": 5,
            "exact_source_review_sha": expected_review_entries_sha256,
            "open_ssl_notice_absent": True,
            "human_legal_approved": False,
            "security_approved": False,
            "customer_distribution_authorized": False,
            "private_output_verified": True}


def stage_owner_private_notice_draft(packet: Path, expected_review_entries_sha256: str) -> dict:
    """Create ONE owner-local draft from already exported originals; no release."""
    result = audit.verify_existing_owner_license_texts(
        packet, expected_review_entries_sha256=expected_review_entries_sha256)
    if (result.get("status") != audit.STATUS
            or result.get("exact_existing_licenses_files_sha_verified") != 5
            or result.get("customer_distribution_authorized") is not False):
        raise NoticeDraftError("owner source integrity is not verified")
    entries = _read_originals(packet)
    target = _private_target(packet.parent / DRAFT_NAME)
    if target.exists() or target.is_symlink():
        raise NoticeDraftError("existing private draft must never be overwritten")
    payload = _manifest(expected_review_entries_sha256, entries)
    # No external binary or OpenSSL license data is invented. No customer bundle.
    target.mkdir(mode=0o700)
    for i, (_, raw) in enumerate(entries, 1):
        with (target / f"LICENSE_ORIGINAL_{i:02d}.txt").open("xb") as handle:
            handle.write(raw)
    with (target / "NOTICE_REVIEW_REQUIRED.txt").open("xb") as handle:
        handle.write(HOLD_TEXT.encode("ascii"))
    with (target / "review_manifest.json").open("xb") as handle:
        handle.write(_canonical(payload))
    return verify_private_notice_draft(target, expected_review_entries_sha256)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE C2 private NOTICE review draft, never release")
    parser.add_argument("--owner-stage-private-review-only", action="store_true")
    parser.add_argument("--expected-review-entries-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if (not args.owner_stage_private_review_only or os.name != "nt"
                or sys.version_info[:2] != (3, 15)
                or not (audit.ROOT / ".git").is_dir()
                or not sys.stdin.isatty()):
            raise NoticeDraftError("only explicit interactive owner Windows3.15 local staging")
        typed = input("Type " + CONSENT + " to stage PRIVATE review draft: ")
        if typed != CONSENT:
            raise NoticeDraftError("owner consent absent")
        result = stage_owner_private_notice_draft(
            audit.ROOT / "downloaded" / audit.FOLDER,
            args.expected_review_entries_sha256)
    except (ValueError, OSError, TypeError) as exc:
        print(json.dumps({"schema": SCHEMA,
                          "status": "PRIVATE_C2_NOTICE_DRAFT_FAIL_CLOSED_NO_GO",
                          "failure_type": type(exc).__name__,
                          "customer_distribution_authorized": False},
                         sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 2  # Intentional NO_GO even on valid private staging.


if __name__ == "__main__":
    raise SystemExit(main())
