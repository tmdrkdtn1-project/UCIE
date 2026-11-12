"""Standalone offline verifier for UCIE C1 FIRST-PARTY-only pinned A/B QA ZIP.

Works on a fresh Windows recipient with Python stdlib only: no UCIE install,
no Git, no pip, no network, no extraction, no vendor wheels, no file writes.
The manifest SHA256 is an exact trust-anchor expectation in this SOURCE
script, not a cryptographic publisher signature or customer authorization.
Obtain this verifier itself from a separately reviewed UCIE repository source.
"""
from __future__ import annotations

import argparse
import base64
import csv
from hashlib import sha1, sha256
import io
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile

SCHEMA = "UCIE_C1_PINNED_AB_STANDALONE_RECIPIENT_BYTES_V01"
SOURCE_SCHEMA = "UCIE_C1_TWO_PINNED_PUBLIC_GIT_TREES_V01"
BUNDLE_SCHEMA = "UCIE_C1_PINNED_AB_FIRST_PARTY_ONLY_QA_BUNDLE_V01"
A = "171d56d8af155c70d3dd32a62afda87398330e99"
B = "4242ebe7ae112076d9b3560e85b0babb22bbb713"
TREE_A = "35e7e796deb83435f58c39b83daa984eb22eb30b"
TREE_B = "7f96f430fb5b2f582dbcda8861968e7363055eb4"
TRUSTED_MANIFEST_SHA256 = "f23c50ca7bf6d781b41bd76d109955b8ce91c3179aede594a66d083e617b11e8"
EXPECTED_B_NEW = {
    "src/ucie_miner/customer_installed_health_v01.py",
    "src/ucie_miner/customer_functional_ab_lifecycle_v01.py",
}
FILENAME = "ucie_c1_pinned_git_ab_first_party_qa_only.zip"
MAX_ZIP_BYTES = 20_000_000
MAX_INNER_BYTES = 8_000_000
MAX_MEMBER = 260_000
MAX_ENTRIES = 220
SLOTS = {
    "A": {"version": "0.1.0", "commit": A, "tree": TREE_A,
          "count": 182, "wheel": "ucie_public_only_demo-0.1.0-py3-none-any.whl"},
    "B": {"version": "0.1.1", "commit": B, "tree": TREE_B,
          "count": 184, "wheel": "ucie_public_only_demo-0.1.1-py3-none-any.whl"},
}
OUTER = {
    "README.txt", "git-source-pins.json",
    "reviewed-git-tree-manifest.json",
    "A/ucie_public_only_demo-0.1.0-py3-none-any.whl",
    "B/ucie_public_only_demo-0.1.1-py3-none-any.whl",
}


class VerifyError(ValueError):
    """Bad bytes; never an authorization result."""


def _blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()


def _safe_entries(zipfile: ZipFile, expected: set[str], max_size: int) -> dict:
    entries = zipfile.infolist()
    if (len(entries) != len(expected) or len(entries) > MAX_ENTRIES
            or {e.filename for e in entries} != expected):
        raise VerifyError("ZIP unexpected, missing or duplicate members")
    used = 0
    for entry in entries:
        name = entry.filename
        if (not name.isascii() or name.startswith("/") or chr(92) in name
                or any(part in ("", ".", "..") for part in name.split("/"))
                or entry.is_dir() or entry.file_size > max_size
                or entry.file_size < 0):
            raise VerifyError("ZIP unsafe file name or size")
        if (entry.create_system == 3 and
                ((entry.external_attr >> 16) & 0o170000) not in (0, 0o100000)):
            raise VerifyError("ZIP symlink or nonregular member")
        used += entry.file_size
        if used > MAX_ZIP_BYTES:
            raise VerifyError("ZIP aggregate uncompressed size exceeded")
    return {entry.filename: entry for entry in entries}


def _read(zipfile: ZipFile, member: str, limit: int) -> bytes:
    try:
        with zipfile.open(member) as stream:
            raw = stream.read(limit + 1)
    except (OSError, BadZipFile, RuntimeError, KeyError) as exc:
        raise VerifyError("ZIP member failed safe bounded read") from exc
    if len(raw) > limit:
        raise VerifyError("ZIP decompressed member exceeds bound")
    return raw


def _manifest(raw: bytes) -> tuple[dict, dict[str, dict]]:
    try:
        document = json.loads(raw)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise VerifyError("reviewed source manifest JSON invalid") from exc
    canonical = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    if sha256(canonical).hexdigest() != TRUSTED_MANIFEST_SHA256:
        raise VerifyError("reviewed source manifest SHA256 trust pin drift")
    if (type(document) is not dict or document.get("schema") != SOURCE_SCHEMA
            or document.get("origin") != "github.com/tmdrkdtn1-project/UCIE"
            or document.get("customer_distribution_authorized") is not False
            or document.get("third_party_wheels_included") is not False
            or type(document.get("slots")) is not dict
            or set(document["slots"]) != {"A", "B"}):
        raise VerifyError("reviewed Git origin/NO-GO policy invalid")
    indexed = {}
    for slot in ("A", "B"):
        expected = SLOTS[slot]
        obj = document["slots"][slot]
        if (type(obj) is not dict
                or obj.get("commit_sha") != expected["commit"]
                or obj.get("root_tree_sha1") != expected["tree"]
                or obj.get("qa_wheel_version") != expected["version"]
                or type(obj.get("c0_inventory")) is not list
                or len(obj["c0_inventory"]) != 23
                or type(obj.get("python_modules")) is not list
                or len(obj["python_modules"]) != expected["count"]):
            raise VerifyError("wrong reviewed Git commit/tree/C0/source count")
        files = {}
        prior = ""
        for entry in obj["python_modules"]:
            if (type(entry) is not list or len(entry) != 3
                    or type(entry[0]) is not str or type(entry[1]) is not str
                    or type(entry[2]) is not int):
                raise VerifyError("invalid first-party Git blob manifest row")
            name, digest, length = entry
            if (name <= prior or name.count("/") < 2
                    or not name.startswith(("src/ucie_miner/",
                                           "src/ucie_public/"))
                    or not name.endswith(".py")
                    or chr(92) in name or any(x in ("", ".", "..")
                                              for x in name.split("/"))
                    or len(digest) != 40
                    or any(c not in "0123456789abcdef" for c in digest)
                    or length < 0 or length > MAX_MEMBER):
                raise VerifyError("unsafe reviewed source file metadata")
            files[name[4:]] = (digest, length)
            prior = name
        indexed[slot] = files
    a = set(indexed["A"])
    b = set(indexed["B"])
    if b - a != {name[4:] for name in EXPECTED_B_NEW} or a - b:
        raise VerifyError("functional A/B source delta unexpected")
    return document, indexed


def _check_record(archive: ZipFile, expected: set[str], meta: str) -> None:
    record_name = meta + "RECORD"
    try:
        records = list(csv.reader(io.StringIO(
            _read(archive, record_name, MAX_MEMBER).decode("utf-8"))))
    except (UnicodeError, csv.Error) as exc:
        raise VerifyError("wheel RECORD invalid UTF8/csv") from exc
    if len(records) != len(expected):
        raise VerifyError("wheel RECORD row count inconsistent")
    observed = {}
    for row in records:
        if len(row) != 3 or row[0] in observed or row[0] not in expected:
            raise VerifyError("wheel RECORD missing/duplicate/extra path")
        name, digest, size = row
        observed[name] = True
        if name == record_name:
            if digest or size:
                raise VerifyError("wheel RECORD self hash must be blank")
            continue
        raw = _read(archive, name, MAX_MEMBER)
        sha = base64.urlsafe_b64encode(sha256(raw).digest()).rstrip(
            b"=").decode("ascii")
        if digest != "sha256=" + sha or size != str(len(raw)):
            raise VerifyError("first-party wheel member SHA256/size changed")
    if set(observed) != expected:
        raise VerifyError("wheel RECORD not complete")


def _wheel(raw: bytes, rows: dict[str, tuple[str, int]],
           slot: str) -> dict:
    if len(raw) > MAX_ZIP_BYTES:
        raise VerifyError("nested first-party wheel over budget")
    version = SLOTS[slot]["version"]
    meta = "ucie_public_only_demo-" + version + ".dist-info/"
    extras = {
        meta + "METADATA", meta + "WHEEL",
        meta + "entry_points.txt", meta + "RECORD",
    }
    filenames = set(rows) | extras
    try:
        with ZipFile(io.BytesIO(raw)) as archive:
            _safe_entries(archive, filenames, MAX_MEMBER)
            _check_record(archive, filenames, meta)
            for name, (git_id, length) in rows.items():
                blob = _read(archive, name, MAX_MEMBER)
                if len(blob) != length or _blob(blob) != git_id:
                    raise VerifyError("first-party module diverged from Git object")
            metadata = _read(archive, meta + "METADATA", MAX_MEMBER)
            wheel_info = _read(archive, meta + "WHEEL", MAX_MEMBER)
            entrypoint = _read(archive, meta + "entry_points.txt", MAX_MEMBER)
    except (BadZipFile, OSError) as exc:
        raise VerifyError("first-party wheel ZIP failed integrity parsing") from exc
    if (b"Name: ucie-public-only-demo\n" not in metadata
            or ("Version: " + version + "\n").encode("ascii") not in metadata
            or b"Requires-Dist: cryptography>=50.0.2,<51\n" not in metadata
            or b"Tag: py3-none-any\n" not in wheel_info
            or b"ucie-product-preview = ucie_miner.customer_staging_v01:main" not in entrypoint):
        raise VerifyError("first-party package identity/entrypoint changed")
    return {
        "version": version,
        "sha256": sha256(raw).hexdigest(),
        "python_module_git_blobs_checked": len(rows),
        "RECORD_sha256_size_checked": True,
        "vendor_wheel_executed_or_installed": False,
    }


def verify(path: Path) -> dict:
    """Read ONE explicitly supplied QA file only. Never unpack to filesystem."""
    if (not isinstance(path, Path) or path.name != FILENAME
            or path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= MAX_ZIP_BYTES):
        raise VerifyError("not the approved first-party-only QA ZIP path")
    try:
        with ZipFile(path) as archive:
            _safe_entries(archive, OUTER, MAX_ZIP_BYTES)
            raw_manifest = _read(
                archive, "reviewed-git-tree-manifest.json", 120_000)
            raw_evidence = _read(archive, "git-source-pins.json", 16_000)
            document, rows = _manifest(raw_manifest)
            try:
                evidence = json.loads(raw_evidence)
            except (ValueError, TypeError) as exc:
                raise VerifyError("source provenance metadata JSON malformed") from exc
            canonical = json.dumps(
                document, sort_keys=True, separators=(",", ":"),
                ensure_ascii=True
            ).encode("ascii")
            if (type(evidence) is not dict
                    or evidence.get("schema") != BUNDLE_SCHEMA
                    or evidence.get("pinned_manifest_sha256") !=
                    sha256(canonical).hexdigest()
                    or evidence.get("vendor_wheels_included") is not False
                    or evidence.get("complete_windows_installer") is not False
                    or evidence.get("customer_distribution_authorized") is not False
                    or type(evidence.get("slots")) is not dict
                    or set(evidence["slots"]) != {"A", "B"}):
                raise VerifyError("QA provenance or missing customer NO-GO gate")
            checked = {}
            for slot in ("A", "B"):
                entry = evidence["slots"][slot]
                wanted = SLOTS[slot]
                if (type(entry) is not dict
                        or entry.get("commit_sha") != wanted["commit"]
                        or entry.get("version") != wanted["version"]
                        or entry.get("first_party_python_files") != wanted["count"]):
                    raise VerifyError("QA wheel slot not associated to exact reviewed Git commit")
                name = slot + "/" + wanted["wheel"]
                raw_wheel = _read(archive, name, MAX_ZIP_BYTES)
                if sha256(raw_wheel).hexdigest() != entry.get("wheel_sha256"):
                    raise VerifyError("QA wheel outer SHA256 does not match provenance")
                checked[slot] = _wheel(raw_wheel, rows[slot], slot)
    except (BadZipFile, OSError) as exc:
        raise VerifyError("first-party QA outer ZIP malformed") from exc
    if checked["A"]["sha256"] == checked["B"]["sha256"]:
        raise VerifyError("A/B product bytes unexpectedly identical")
    return {
        "schema": SCHEMA,
        "status": "REVIEWED_GIT_FIRST_PARTY_SOURCE_QA_BYTES_VERIFIED_CUSTOMER_NO_GO",
        "reviewed_manifest_sha256": TRUSTED_MANIFEST_SHA256,
        "outer_QA_bundle_sha256": sha256(path.read_bytes()).hexdigest(),
        "A": checked["A"], "B": checked["B"],
        "vendor_wheels_included": False,
        "vendor_code_executed": False,
        "verified_on_clean_windows_recipient": False,
        "full_product_installed_or_executed": False,
        "publisher_signature_or_license_approved": False,
        "customer_distribution_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE first-party-only reviewed source A/B QA ZIP: stdlib offline verifier"
    )
    parser.add_argument("--bundle", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.bundle)
    except (VerifyError, OSError, ValueError, RuntimeError):
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_C1_INDEPENDENT_QA_BYTES_VERIFIER_FAIL_CLOSED",
            "customer_distribution_authorized": False,
            "no_vendor_executed": True,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
