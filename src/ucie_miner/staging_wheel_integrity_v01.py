"""UCIE-only first-party wheel staging inventory and RECORD attestation.

This validates content identity for a temporary CI build, not external origin,
independent security, third-party licensing, signing, or release approval.
No filesystem/network writes and no arbitrary code execution.
"""
from __future__ import annotations

import base64
import csv
from hashlib import sha256
import io
import re
import stat
from zipfile import BadZipFile, ZipFile

SCHEMA = "UCIE_STAGING_WHEEL_CONTENT_ATTESTATION_V01"
DIST = "ucie_public_only_demo-0.1.0.dist-info/"
ENTRY_POINT = DIST + "entry_points.txt"
CUSTOMER_PREVIEW_MODULE = "ucie_miner/customer_staging_v01.py"
EXPECTED_ENTRY_POINT = (
    "[console_scripts]\n"
    "ucie-product-preview = ucie_miner.customer_staging_v01:main"
)
ALLOWED_DIST = frozenset({
    DIST + "METADATA", DIST + "WHEEL", DIST + "RECORD",
    DIST + "top_level.txt", ENTRY_POINT,
})
ALLOWED_PACKAGES = ("ucie_miner/", "ucie_public/")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
MAX_WHEEL_BYTES = 8_000_000
MAX_FILES = 900
MAX_MEMBER_BYTES = 300_000
MAX_TOTAL_BYTES = 15_000_000


class WheelAttestationError(ValueError):
    """A staging wheel diverged from the pinned source-only contract."""


def _reject(reason: str) -> None:
    raise WheelAttestationError(reason)


def _member_name(name: str) -> bool:
    if (not name or len(name) > 220 or name.startswith("/")
            or "\\" in name or "//" in name or ":" in name
            or any(x in ("", ".", "..") for x in name.split("/"))):
        return False
    if name in ALLOWED_DIST:
        return True
    return name.endswith(".py") and any(
        name.startswith(prefix) for prefix in ALLOWED_PACKAGES
    )


def verify_staging_wheel(raw: bytes, source_digests: dict[str, str]) -> dict:
    """Check packaged Python bytes and every wheel RECORD digest.

    source_digests must be derived from the exact ephemeral first-party source
    checkout by the caller, never from a wheel-supplied manifest.
    """
    if type(raw) is not bytes or not 200 <= len(raw) <= MAX_WHEEL_BYTES:
        _reject("wheel bytes missing or out of range")
    if (type(source_digests) is not dict or not source_digests
            or len(source_digests) > MAX_FILES
            or any(type(k) is not str or type(v) is not str
                   or not _member_name(k) or k in ALLOWED_DIST
                   or not HEX64.fullmatch(v)
                   for k, v in source_digests.items())):
        _reject("invalid trusted first-party source map")
    try:
        with ZipFile(io.BytesIO(raw), "r") as wheel:
            infos = wheel.infolist()
            names = [i.filename for i in infos]
            if (not infos or len(infos) > MAX_FILES
                    or len(names) != len(set(names))
                    or any(not _member_name(n) for n in names)
                    or not {DIST+"METADATA", DIST+"WHEEL", DIST+"RECORD"} <= set(names)):
                _reject("unexpected wheel inventory")
            code = {n for n in names if n.endswith(".py")}
            if code != set(source_digests):
                _reject("packaged first-party source set drift")
            total = 0
            actual = {}
            for info in infos:
                mode = info.external_attr >> 16
                kind = stat.S_IFMT(mode)
                if (info.is_dir() or (info.flag_bits & 1)
                        or kind not in (0, stat.S_IFREG)
                        or mode & 0o111
                        or info.file_size <= 0
                        or info.file_size > MAX_MEMBER_BYTES):
                    _reject("unsafe archive entry attributes")
                total += info.file_size
                if total > MAX_TOTAL_BYTES:
                    _reject("archive expanded size limit")
                payload = wheel.read(info)
                if len(payload) != info.file_size:
                    _reject("archive entry size mismatch")
                digest = sha256(payload).digest()
                actual[info.filename] = (digest, len(payload))
                if info.filename in source_digests:
                    if digest.hex() != source_digests[info.filename]:
                        _reject("packaged source does not match first-party checkout")
            metadata = wheel.read(DIST+"METADATA")
            headers = metadata.decode("utf-8", "strict").splitlines()
            if (not any(x.strip() == "Name: ucie-public-only-demo" for x in headers)
                    or not any(x.strip() == "Version: 0.1.0" for x in headers)):
                _reject("unexpected package identity/version")
            wheel_metadata = wheel.read(DIST+"WHEEL").decode("utf-8", "strict")
            if ("Tag: py3-none-any" not in wheel_metadata.splitlines()
                    or "Root-Is-Purelib: true" not in wheel_metadata.splitlines()):
                _reject("wheel is not pure Python")
            # Console scripts are executable entrypoint metadata. The
            # first-party UCIE preview is the ONLY executable label allowed.
            has_preview_module = CUSTOMER_PREVIEW_MODULE in code
            has_entrypoint = ENTRY_POINT in names
            if has_entrypoint != has_preview_module:
                _reject("customer preview entrypoint/source mismatch")
            if has_entrypoint:
                entrypoint = wheel.read(ENTRY_POINT).decode(
                    "utf-8", "strict").replace("\r\n", "\n").strip()
                if entrypoint != EXPECTED_ENTRY_POINT:
                    _reject("unexpected executable console entry point")
            records = list(csv.reader(
                io.StringIO(wheel.read(DIST+"RECORD").decode("utf-8", "strict"))
            ))
            if len(records) != len(infos):
                _reject("wheel RECORD count mismatch")
            seen = set()
            for row in records:
                if len(row) != 3:
                    _reject("bad wheel RECORD field count")
                name, digest_field, byte_count = row
                if name not in actual or name in seen:
                    _reject("unknown or duplicated RECORD path")
                seen.add(name)
                if name == DIST+"RECORD":
                    if digest_field or byte_count:
                        _reject("RECORD self hash must be omitted")
                    continue
                if not digest_field.startswith("sha256="):
                    _reject("wheel RECORD SHA256 missing")
                try:
                    b64 = digest_field[7:]
                    original = base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4))
                except (ValueError, base64.binascii.Error) as exc:
                    raise WheelAttestationError("invalid RECORD base64") from exc
                if len(original) != 32 or original != actual[name][0]:
                    _reject("wheel RECORD digest mismatch")
                if not byte_count.isdecimal() or int(byte_count) != actual[name][1]:
                    _reject("wheel RECORD byte count mismatch")
            if seen != set(names):
                _reject("incomplete wheel RECORD")
            return {
                "schema": SCHEMA,
                "status": "STAGING_CONTENT_VERIFIED_RELEASE_NO_GO",
                "wheel_sha256": sha256(raw).hexdigest(),
                "first_party_source_modules": len(code),
                "wheel_member_count": len(names),
                "wheel_record_verified": True,
                "source_files_match_checkout": True,
                "package_version": "0.1.0",
                "pure_python_wheel": True,
                "customer_preview_entrypoint_verified": has_entrypoint,
                "external_release_authorized": False,
                "independent_security_or_license_attested": False,
                "operating_db_writes": 0,
                "task_scheduler_mutations": 0,
            }
    except (BadZipFile, UnicodeError, OSError, EOFError, RuntimeError) as exc:
        raise WheelAttestationError("invalid wheel archive") from exc
