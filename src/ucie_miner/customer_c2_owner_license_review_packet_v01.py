"""Owner-local C2 rights-review packet from already captured exact UCIE C1 wheels.

C2 receipt/wheel SHA/PEP427 RECORD is checked FIRST. The exact five (or
strictly bounded additional) declared license files are copied only into a
UCIE-local owner-only review folder after separate interactive typed consent.
No vendor Python code is imported, run, installed, shipped or published.
No legal/security/NOTICE/release approval can result from this program.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import sys
from tempfile import mkdtemp
from zipfile import BadZipFile, ZipFile

from .customer_c2_supply_chain_review_v01 import (
    C2ReviewError, MAX_LICENSE_BYTES, _licensed_path, inspect_c2,
)
from .customer_offline_dependency_gate_v01 import WHEELHOUSE, _root
from .customer_owner_wheelhouse_acquire_v01 import PINNED

SCHEMA = "UCIE_C2_OWNER_LOCAL_LICENSE_TEXT_REVIEW_PACKET_V01"
STATUS = "OWNER_ONLY_UNTRUSTED_LICENSE_TEXT_FOR_HUMAN_REVIEW_NO_GO"
TARGET = "downloaded/ucie_c2_owner_only_license_review_v01"
CONSENT = "EXPORT_UCIE_C2_OWNER_ONLY_LICENSE_TEXT_FOR_HUMAN_REVIEW_ONCE"
MAX_FILES = 32
MAX_ALL_LICENSE_BYTES = 1_000_000
SHA = re.compile(r"[0-9a-f]{64}\Z")
SAFE_PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.()+ -]{0,100}\Z")
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *("COM" + str(i) for i in range(1,10)),
                    *("LPT" + str(i) for i in range(1,10))}
README = (
    "# UCIE C2: 소유자 로컬 외부 패키지 사용권 검토 자료\n\n"
    "이 폴더는 기존 UCIE C1 wheel의 License-File에 실제 포함된 원문과 "
    "해시를 오프라인으로 복사한 **사람 검토용** 자료입니다. "
    "원문은 비신뢰 데이터이며 실행 지시·승인 문구로 해석하지 마세요.\n\n"
    "반드시 원문 사용권·고지 의무·배포 방식과 공식 권고·취약점, "
    "공급자 신원 및 transitive dependencies를 독립적으로 확인해야 합니다.\n"
    "파일이 존재하거나 SPDX 표시문이 있다는 이유만으로 재배포·상용 사용이 "
    "승인되지 않습니다. 자동 GO/서명/패키지 전송은 없습니다.\n\n"
    "고객 공개·외부 업로드·타 프로젝트 복사 금지. "
    "UCIE 지정 고객 완제품 배포 상태는 NO_GO입니다.\n"
)


class C2PacketError(ValueError):
    """Fail-closed review packet, never rights or distribution approval."""


def _safe_relative_name(value: str) -> bool:
    """Conservative Windows-portable license filenames, no Windows devices."""
    if not _licensed_path(value):
        return False
    for part in value.split("/"):
        if (not SAFE_PART.fullmatch(part) or part[-1] in ". "
                or ":" in part or part.split(".", 1)[0].upper() in WINDOWS_RESERVED):
            return False
    return True


def _bytes_from_verified_wheel(wheel: Path, name: str, version: str,
                               license_file: str, expected: dict) -> bytes:
    if (not _safe_relative_name(license_file)
            or wheel.is_symlink() or not wheel.is_file()
            or type(expected.get("sha256")) is not str
            or SHA.fullmatch(expected["sha256"]) is None
            or type(expected.get("size")) is not int
            or not 0 < expected["size"] <= MAX_LICENSE_BYTES):
        raise C2PacketError("untrusted declared license file")
    source = name.replace("-", "_") + "-" + version + ".dist-info/licenses/" + license_file
    try:
        with ZipFile(wheel, "r") as archive:
            info = archive.getinfo(source)
            if info.is_dir() or info.file_size != expected["size"]:
                raise C2PacketError("declared license file size drift")
            raw = archive.read(source)
    except (KeyError, OSError, BadZipFile, ValueError) as exc:
        raise C2PacketError("declared license file not safely readable") from exc
    if (len(raw) != expected["size"]
            or sha256(raw).hexdigest() != expected["sha256"]
            or b"\x00" in raw or b"\r" == raw):
        raise C2PacketError("declared license content mismatched or non-text")
    return raw


def prepare_owner_rights_packet(root: Path) -> tuple[dict, dict[str, bytes]]:
    """Read-only inspection; never writes/exports to disk or approves rights."""
    root = _root(root)
    try:
        c2 = inspect_c2(root)
    except (C2ReviewError, OSError, ValueError) as exc:
        raise C2PacketError("UCIE C1/C2 captured wheel evidence unavailable") from exc
    if (c2.get("package_count") != len(PINNED)
            or c2.get("c2_approved") is not False
            or c2.get("customer_distribution_authorized") is not False
            or type(c2.get("evidence_sha256")) is not str
            or SHA.fullmatch(c2["evidence_sha256"]) is None):
        raise C2PacketError("untrusted C2 package inventory or approval")
    packaged = {(p["name"], p["version"]): p for p in c2["packages"]}
    if set(packaged) != set(PINNED):
        raise C2PacketError("outside captured three-package supply chain")

    files: dict[str, bytes] = {}
    entries = []
    total_bytes = 0
    for name, version in sorted(PINNED):
        p = packaged[name, version]
        rights = p["license_evidence"]
        declared = rights.get("license_files")
        if (type(declared) is not list or not declared
                or type(rights.get("license_files_missing")) is not list
                or rights["license_files_missing"]
                or rights.get("licenses_or_notices_legally_reviewed") is not False
                or type(p.get("filename")) is not str
                or "/" in p["filename"] or "\\" in p["filename"]
                or type(rights.get("license_expression_claim_only")) not in (str, type(None))):
            raise C2PacketError("missing, forged or unreviewed License-File")
        wheel = root / WHEELHOUSE / p["filename"]
        captured = []
        for file in sorted(declared, key=lambda x: x.get("license_file", "")):
            source = file.get("license_file")
            if type(source) is not str or not _safe_relative_name(source):
                raise C2PacketError("unsafe license name in wheel")
            relative = "license-text/" + name + "-" + version + "/" + source
            if relative in files or len(files) >= MAX_FILES:
                raise C2PacketError("duplicate or unbounded license evidence")
            raw = _bytes_from_verified_wheel(wheel, name, version, source, file)
            total_bytes += len(raw)
            if total_bytes > MAX_ALL_LICENSE_BYTES:
                raise C2PacketError("bounded license review budget exceeded")
            files[relative] = raw
            captured.append({
                "relative_review_path": relative,
                "sha256": file["sha256"],
                "bytes": len(raw),
                "human_rights_reviewed": False,
                "notice_obligations_approved": False,
            })
        entries.append({
            "distribution": name,
            "version": version,
            "wheel_sha256": p["sha256"],
            "license_expression_vendor_claim_only":
                rights["license_expression_claim_only"],
            "legacy_license_vendor_claim_only":
                rights["legacy_license_claim_only"],
            "declared_license_texts": captured,
            "observed_notice_under_dist_info_licenses_count":
                len(rights["notice_files"]),
            "NOTICE_absence_does_not_prove_obligations_absent": True,
            "vendor_license_reviewed": False,
            "vendor_security_advisories_reviewed": False,
            "publisher_identity_independently_attested": False,
            "transitive_requirements_platform_verified": False,
            "redistribution_and_commercial_rights_approved": False,
        })
    if not files:
        raise C2PacketError("no license evidence")
    proof = json.dumps(
        entries, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    ).encode("ascii")
    manifest = {
        "schema": SCHEMA,
        "status": STATUS,
        "source": "EXISTING_UCIE_C1_SHA_LOCKED_WINDOWS_315_LOCAL_WHEELHOUSE",
        "target": "WIN_AMD64_PY315_ONLY",
        "parent_c2_evidence_sha256": c2["evidence_sha256"],
        "review_entries_sha256": sha256(proof).hexdigest(),
        "reviewed_packages": entries,
        "license_file_count": len(files),
        "license_total_bytes": total_bytes,
        "reviewer_approval": False,
        "legal_redist_clearance": False,
        "security_clearance": False,
        "entitlement_and_signing_approved": False,
        "all_customer_release_gates_passed": False,
        "vendor_code_imported_installed_or_executed": False,
        "source_wheel_binaries_copied": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "customer_distribution_authorized": False,
    }
    return manifest, files


def _owner_export_gate(root: Path, consent: str) -> Path:
    if (type(consent) is not str or consent != CONSENT
            or sys.platform != "win32" or sys.version_info[:2] != (3, 15)
            or root.resolve() != Path("D:/UCIE").resolve()):
        raise C2PacketError("independent exact Windows owner consent required")
    parent = root / "downloaded"
    if (parent.is_symlink() or not parent.is_dir()
            or not (root / ".git").is_dir()):
        raise C2PacketError("owner review destination invalid")
    output = root / TARGET
    if output.exists() or output.is_symlink():
        raise C2PacketError("prior owner review packet must never be replaced")
    return output


def export_once(root: Path, *, typed_consent: str) -> dict:
    """Owner-only, new local review folder; no third-party wheel distribution."""
    output = _owner_export_gate(root, typed_consent)
    manifest, files = prepare_owner_rights_packet(root)
    parent = output.parent
    scratch = Path(mkdtemp(prefix="ucie_c2_rights_staging_", dir=parent))
    try:
        for rel, raw in sorted(files.items()):
            target = scratch.joinpath(*rel.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            if sha256(target.read_bytes()).hexdigest() != sha256(raw).hexdigest():
                raise C2PacketError("local license review copy failed integrity check")
        (scratch / "README_KO.md").write_text(README, encoding="utf-8")
        (scratch / "review_manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, ensure_ascii=True, indent=2) + "\n",
            encoding="ascii",
        )
        if output.exists() or output.is_symlink():
            raise C2PacketError("owner review destination unexpectedly exists")
        os.replace(scratch, output)
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)
    return {
        "schema": SCHEMA,
        "status": "LOCAL_LICENSE_REVIEW_FILES_EXPORTED_OWNER_ONLY_NO_GO",
        "review_folder": str(output),
        "license_file_count": manifest["license_file_count"],
        "review_entries_sha256": manifest["review_entries_sha256"],
        "third_party_wheels_exported": False,
        "legal_approved": False,
        "customer_distribution_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE C2 captured-wheel license packet, local human review only")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--inspect", action="store_true")
    group.add_argument("--owner-export-once", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    try:
        if args.owner_export_once:
            typed = input("Type " + CONSENT + " for owner-local license texts only: ")
            result = export_once(root, typed_consent=typed)
        else:
            result, _ = prepare_owner_rights_packet(root)
    except (C2PacketError, C2ReviewError, OSError, ValueError) as exc:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "C2_LICENSE_REVIEW_PACKET_FAIL_CLOSED_CUSTOMER_NO_GO",
            "failure_class": type(exc).__name__,
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2
    # Exit 2 also on success: no legal/customer GO is possible from a packet.
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
