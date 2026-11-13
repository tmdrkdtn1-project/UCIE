"""UCIE C2: exact original LICENSE copies inside a PRIVATE technical QA bundle.

This is a real file-inclusion path, not a rights approval. The already exported
owner source must pass its independent source SHA audit before any bundle write.
It never downloads dependencies, re-exports wheels, signs, publishes, or
pretends to include unknown OpenSSL native-component notices.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

from . import customer_c2_existing_owner_license_integrity_v01 as original_audit
from . import customer_c2_private_notice_draft_v01 as existing_draft

SCHEMA = "UCIE_C2_PRIVATE_BUNDLE_ORIGINAL_LICENSE_COPY_V01"
STATUS = "ORIGINAL_FIVE_LICENSE_TEXTS_INCLUDED_REVIEW_NOT_APPROVED"
DIR = "ORIGINAL_LICENSES_REVIEW_ONLY"
NOTE = (
    "UCIE PRIVATE TECHNICAL QA: FIVE ORIGINAL LICENSE TEXTS, NOT APPROVED.\n"
    "These byte-exact source texts do not constitute a legal review.\n"
    "The embedded OpenSSL component's exact license/NOTICE and any further\n"
    "copyright/attribution obligations are NOT fully assembled here.\n"
    "First-party/SkillBook rights, human security/NOTICE decisions, product\n"
    "signing, merchant and customer distribution are NOT approved.\n"
    "DO NOT DISTRIBUTE OR TREAT THIS FOLDER AS A RELEASE APPENDIX.\n"
)
SHA = re.compile(r"[0-9a-f]{64}\Z")
MAX_MANIFEST = 20000


class OriginalLicenseCopyError(ValueError):
    """A technical file copy must not imply redistribution approval."""


def _canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("ascii")


def _unique(pairs):
    if len({key for key, _ in pairs}) != len(pairs):
        raise OriginalLicenseCopyError("duplicate license manifest fields")
    return dict(pairs)


def prepare_originals(packet: Path, *, independent_sha256: str) -> list[tuple[str, bytes]]:
    """Only previously captured five LICENSE files; no C1 wheel re-extraction."""
    report = original_audit.verify_existing_owner_license_texts(
        packet, expected_review_entries_sha256=independent_sha256)
    if (report.get("status") != original_audit.STATUS
            or report.get("exact_existing_licenses_files_sha_verified") != 5
            or report.get("customer_distribution_authorized") is not False):
        raise OriginalLicenseCopyError("owner original five-license source unverified")
    originals = existing_draft._read_originals(packet)
    if len(originals) != 5:
        raise OriginalLicenseCopyError("source exact five-license count required")
    return originals


def _manifest(originals: list[tuple[str, bytes]], independent_sha256: str) -> dict:
    if (type(independent_sha256) is not str or SHA.fullmatch(independent_sha256) is None
            or type(originals) is not list or len(originals) != 5):
        raise OriginalLicenseCopyError("independent five-file pin required")
    if len({rel for rel, _ in originals}) != 5:
        raise OriginalLicenseCopyError("duplicate original source path")
    files = []
    for idx, (rel, raw) in enumerate(originals, 1):
        if (type(rel) is not str or not rel.startswith("license-text/")
                or type(raw) is not bytes or not 0 < len(raw) <= 1_000_000):
            raise OriginalLicenseCopyError("source license bytes/path invalid")
        files.append({
            "source_relative_path": rel,
            "filename": f"ORIGINAL_LICENSE_{idx:02d}.txt",
            "sha256": sha256(raw).hexdigest(),
            "bytes": len(raw),
        })
    return {
        "schema": SCHEMA, "status": STATUS,
        "owner_originals_source_review_sha256": independent_sha256,
        "license_files": files,
        "license_file_count": 5,
        "openssl_embedded_license_and_notice_completed": False,
        "human_license_notice_approved": False,
        "first_party_skillbook_rights_approved": False,
        "security_risk_approved": False,
        "customer_distribution_authorized": False,
    }


def stage_originals_into_technical_bundle(
    bundle_root: Path, originals: list[tuple[str, bytes]], independent_sha256: str,
) -> dict:
    """Write ONLY inside an existing private QA bundle, never to an owner source."""
    if (not isinstance(bundle_root, Path) or not bundle_root.is_absolute()
            or bundle_root.name != "UCIE_PRIVATE_BUNDLE"
            or bundle_root.is_symlink() or not bundle_root.is_dir()):
        raise OriginalLicenseCopyError("exact existing private QA bundle required")
    output = bundle_root / DIR
    if output.exists() or output.is_symlink():
        raise OriginalLicenseCopyError("existing license appendix never overwritten")
    content = _manifest(originals, independent_sha256)
    output.mkdir()
    for row, (_, raw) in zip(content["license_files"], originals):
        with (output / row["filename"]).open("xb") as handle:
            handle.write(raw)
    with (output / "NOTICE_REVIEW_REQUIRED.txt").open("xb") as handle:
        handle.write(NOTE.encode("ascii"))
    manifest_bytes = _canonical(content)
    with (output / "original_license_manifest.json").open("xb") as handle:
        handle.write(manifest_bytes)
    expected = {
        "schema": SCHEMA,
        "manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "owner_originals_source_review_sha256": independent_sha256,
        "license_file_count": 5,
        "openssl_embedded_license_and_notice_completed": False,
        "human_license_notice_approved": False,
        "customer_distribution_authorized": False,
    }
    verify_staged_originals(output, expected)
    return expected


def verify_staged_originals(folder: Path, expected: dict) -> dict:
    """Validate exact files, hashes, no fake approval; not legal authenticity."""
    if (not isinstance(folder, Path) or folder.name != DIR
            or folder.is_symlink() or not folder.is_dir()
            or type(expected) is not dict):
        raise OriginalLicenseCopyError("original license review folder invalid")
    path = folder / "original_license_manifest.json"
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= MAX_MANIFEST):
        raise OriginalLicenseCopyError("original license copy manifest absent")
    raw = path.read_bytes()
    try:
        info = json.loads(raw.decode("ascii"), object_pairs_hook=_unique)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise OriginalLicenseCopyError("original license copy metadata invalid") from exc
    if type(info) is not dict or _canonical(info) != raw:
        raise OriginalLicenseCopyError("original license manifest noncanonical")
    files = info.get("license_files")
    if (type(files) is not list or len(files) != 5
            or type(info.get("owner_originals_source_review_sha256")) is not str
            or SHA.fullmatch(info["owner_originals_source_review_sha256"]) is None):
        raise OriginalLicenseCopyError("source review linkage invalid")
    originals = []
    expected_files = {"original_license_manifest.json", "NOTICE_REVIEW_REQUIRED.txt"}
    for idx, item in enumerate(files, 1):
        name = f"ORIGINAL_LICENSE_{idx:02d}.txt"
        if (type(item) is not dict
                or set(item) != {"source_relative_path","filename","sha256","bytes"}
                or item.get("filename") != name
                or type(item.get("source_relative_path")) is not str
                or not item["source_relative_path"].startswith("license-text/")
                or type(item.get("sha256")) is not str
                or SHA.fullmatch(item["sha256"]) is None
                or type(item.get("bytes")) is not int
                or not 0 < item["bytes"] <= 1_000_000):
            raise OriginalLicenseCopyError("untrusted exact license filename/digest")
        file = folder / name
        if (file.is_symlink() or not file.is_file()
                or file.stat().st_size != item["bytes"]):
            raise OriginalLicenseCopyError("license copy missing/linked/changed")
        data = file.read_bytes()
        if sha256(data).hexdigest() != item["sha256"]:
            raise OriginalLicenseCopyError("license copy digest differs")
        originals.append((item["source_relative_path"], data))
        expected_files.add(name)
    note = folder / "NOTICE_REVIEW_REQUIRED.txt"
    if note.is_symlink() or not note.is_file() or note.read_bytes() != NOTE.encode("ascii"):
        raise OriginalLicenseCopyError("unapproved review notice missing")
    if ({p.name for p in folder.iterdir()} != expected_files
            or any(p.is_symlink() or not p.is_file() for p in folder.iterdir())):
        raise OriginalLicenseCopyError("unexpected license appendix file")
    expected_content = _manifest(originals, info["owner_originals_source_review_sha256"])
    if info != expected_content:
        raise OriginalLicenseCopyError("original license approval status or content forged")
    required = {
        "schema": SCHEMA,
        "manifest_sha256": sha256(raw).hexdigest(),
        "owner_originals_source_review_sha256": info["owner_originals_source_review_sha256"],
        "license_file_count": 5,
        "openssl_embedded_license_and_notice_completed": False,
        "human_license_notice_approved": False,
        "customer_distribution_authorized": False,
    }
    if expected != required:
        raise OriginalLicenseCopyError("bundle cannot claim legal clearance")
    return {"schema": SCHEMA, "status": STATUS, "original_license_files_verified": 5,
            "source_hash_bound_to_existing_owner_receipt": True,
            "openssl_embedded_notice_complete": False,
            "human_license_notice_approved": False,
            "customer_distribution_authorized": False}
