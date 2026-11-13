"""UCIE C2: owner-only READ-ONLY audit of the five ALREADY-EXPORTED license texts.

Never re-export, import/execute license files, touch C1 wheelhouse, use a
network client, assert legal approval, or copy copyright text off host.
The independently reported review_entries_sha256 is an expected INPUT,
never learned from the untrusted manifest itself. No automatic GO.
"""
from __future__ import annotations

from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import re
import sys

from . import customer_c2_owner_license_review_packet_v01 as original
from .customer_owner_wheelhouse_acquire_v01 import PINNED

SCHEMA = "UCIE_C2_EXISTING_OWNER_LICENSE_TEXT_INTEGRITY_REVIEW_V01"
STATUS = "EXISTING_FIVE_LICENSE_TEXTS_SHA_VERIFIED_HUMAN_REVIEW_REQUIRED_NO_GO"
ROOT = Path("D:/UCIE")
FOLDER = "ucie_c2_owner_only_license_review_v01"
SHA = re.compile(r"[0-9a-f]{64}\Z")
MAX_MANIFEST = 35000
MAX_ALL_BYTES = 1_000_000


class ExistingLicenseReviewError(ValueError):
    """Untrusted original source/manifest may not become a legal approval."""


def _distinct(pairs: list[tuple[str, object]]) -> dict:
    if len({name for name,_ in pairs}) != len(pairs):
        raise ExistingLicenseReviewError("duplicate original manifest key")
    return dict(pairs)


def _safe_originals_dir(packet: Path) -> Path:
    if (not isinstance(packet,Path) or not packet.is_absolute()
            or packet.name != FOLDER or packet.parent.name != "downloaded"
            or packet.parent.parent.name.lower() != "ucie"
            or packet.is_symlink() or packet.parent.is_symlink()
            or packet.parent.parent.is_symlink() or not packet.is_dir()):
        raise ExistingLicenseReviewError("only bounded pre-existing UCIE C2 owner packet")
    return packet


def verify_existing_owner_license_texts(
    packet: Path, *, expected_review_entries_sha256: str,
) -> dict:
    """Read-only file-byte audit (not a legal interpretation or rights grant)."""
    if (type(expected_review_entries_sha256) is not str
            or SHA.fullmatch(expected_review_entries_sha256) is None):
        raise ExistingLicenseReviewError("independent owner review entry digest needed")
    folder=_safe_originals_dir(packet)
    manifest_path=folder/"review_manifest.json"
    if (manifest_path.is_symlink() or not manifest_path.is_file()
            or not 0<manifest_path.stat().st_size<=MAX_MANIFEST):
        raise ExistingLicenseReviewError("missing bounded existing C2 packet manifest")
    try:
        manifest=json.loads(manifest_path.read_bytes().decode("ascii"),
                            object_pairs_hook=_distinct)
    except (ValueError,UnicodeError,TypeError) as exc:
        raise ExistingLicenseReviewError("untrusted original C2 manifest") from exc
    if (type(manifest) is not dict
            or manifest.get("schema")!=original.SCHEMA
            or manifest.get("status")!=original.STATUS
            or manifest.get("source")!="EXISTING_UCIE_C1_SHA_LOCKED_WINDOWS_315_LOCAL_WHEELHOUSE"
            or manifest.get("target")!="WIN_AMD64_PY315_ONLY"
            or manifest.get("review_entries_sha256")!=expected_review_entries_sha256
            or type(manifest.get("parent_c2_evidence_sha256")) is not str
            or SHA.fullmatch(manifest["parent_c2_evidence_sha256"]) is None
            or manifest.get("license_file_count")!=5
            or type(manifest.get("license_total_bytes")) is not int
            or not 0<manifest["license_total_bytes"]<=MAX_ALL_BYTES
            or manifest.get("reviewer_approval") is not False
            or manifest.get("legal_redist_clearance") is not False
            or manifest.get("security_clearance") is not False
            or manifest.get("all_customer_release_gates_passed") is not False
            or manifest.get("customer_distribution_authorized") is not False):
        raise ExistingLicenseReviewError("existing owner packet approval/count drift")
    groups=manifest.get("reviewed_packages")
    if type(groups) is not list or len(groups)!=len(PINNED):
        raise ExistingLicenseReviewError("unexpected owner rights-review packages")
    core=json.dumps(groups,sort_keys=True,ensure_ascii=True,
                    separators=(",",":"),allow_nan=False).encode("ascii")
    if sha256(core).hexdigest()!=expected_review_entries_sha256:
        raise ExistingLicenseReviewError("actual original review entries changed")
    if ({(x.get("distribution"),x.get("version")) for x in groups
         if type(x) is dict}!={v for v in PINNED}):
        raise ExistingLicenseReviewError("unreviewed/duplicate vendor identity")
    seen=set()
    total=0
    report=[]
    for row in sorted(groups,key=lambda x:x["distribution"]):
        name,version=row["distribution"],row["version"]
        if (type(row.get("wheel_sha256")) is not str
                or SHA.fullmatch(row["wheel_sha256"]) is None
                or row.get("vendor_license_reviewed") is not False
                or row.get("redistribution_and_commercial_rights_approved") is not False
                or row.get("NOTICE_absence_does_not_prove_obligations_absent") is not True
                or type(row.get("observed_notice_under_dist_info_licenses_count")) is not int
                or row["observed_notice_under_dist_info_licenses_count"]<0):
            raise ExistingLicenseReviewError("license approval or vendor digest forged")
        license_items=row.get("declared_license_texts")
        if type(license_items) is not list or not license_items:
            raise ExistingLicenseReviewError("no captured license texts")
        for item in license_items:
            if (type(item) is not dict
                    or set(item)!={"relative_review_path","sha256","bytes",
                                   "human_rights_reviewed","notice_obligations_approved"}
                    or item.get("human_rights_reviewed") is not False
                    or item.get("notice_obligations_approved") is not False
                    or type(item.get("sha256")) is not str or
                    SHA.fullmatch(item["sha256"]) is None
                    or type(item.get("bytes")) is not int
                    or not 0<item["bytes"]<=original.MAX_LICENSE_BYTES):
                raise ExistingLicenseReviewError("invalid declared license evidence")
            relative=item["relative_review_path"]
            prefix="license-text/"+name+"-"+version+"/"
            if (type(relative) is not str or not relative.startswith(prefix)
                    or not original._safe_relative_name(relative[len(prefix):])
                    or relative in seen):
                raise ExistingLicenseReviewError("untrusted duplicate/out-of-scope license path")
            seen.add(relative)
            file=folder.joinpath(*relative.split("/"))
            # Reject symlink at every internal parent; no following links to
            # other data/projects, even when an attacker changed a directory.
            current=file.parent
            while current!=folder:
                if current.is_symlink() or not current.is_dir():
                    raise ExistingLicenseReviewError("linked review directory")
                current=current.parent
            if (file.is_symlink() or not file.is_file()
                    or file.stat().st_size!=item["bytes"]):
                raise ExistingLicenseReviewError("changed/corrupt license text file")
            raw=file.read_bytes()
            if (len(raw)!=item["bytes"]
                    or sha256(raw).hexdigest()!=item["sha256"]):
                raise ExistingLicenseReviewError("original license bytes differ from approved receipt")
            total+=len(raw)
            if total>MAX_ALL_BYTES:
                raise ExistingLicenseReviewError("owner original license byte budget exceeded")
        report.append({
            "distribution":name,"version":version,
            "exact_source_wheel_sha256":row["wheel_sha256"],
            "declared_texts_sha_verified":len(license_items),
            "embedded_license_notices_claimed":row["observed_notice_under_dist_info_licenses_count"],
            "human_rights_approval":False,
            "notice_and_redistribution_approved":False,
        })
    if len(seen)!=5 or total!=manifest["license_total_bytes"]:
        raise ExistingLicenseReviewError("owner five original license texts not complete")
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_packet_review_entries_sha256":expected_review_entries_sha256,
        "exact_existing_licenses_files_sha_verified":len(seen),
        "exact_existing_license_bytes_sha_verified":total,
        "source_pkgs":report,
        "owner_originals_exported_again":False,
        "vendor_wheels_reexported_or_installed":False,
        "security_advisories_independently_cleared":False,
        "actual_human_license_notice_review_completed":False,
        "first_party_owner_and_skillbook_rights_approved":False,
        "customer_distribution_authorized":False,
        "operating_database_writes":0,
        "network_requests":0,
    }


def owner_inspect_once(expected_review_entries_sha256:str) -> dict:
    if (os.name!="nt" or sys.version_info[:2]!=(3,15)
            or sys.implementation.name!="cpython"
            or not (ROOT/".git").is_dir()
            or ROOT.is_symlink()):
        raise ExistingLicenseReviewError("actual UCIE owner Windows3.15 only")
    return verify_existing_owner_license_texts(
        ROOT/"downloaded"/FOLDER,
        expected_review_entries_sha256=expected_review_entries_sha256)


def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description="UCIE C2 existing five owner LICENSE texts, read-only")
    parser.add_argument("--inspect-existing-owner-packet",action="store_true")
    parser.add_argument("--expected-review-entries-sha256",required=True)
    args=parser.parse_args(argv)
    try:
        if not args.inspect_existing_owner_packet:
            raise ExistingLicenseReviewError("explicit read-only existing owner mode required")
        report=owner_inspect_once(args.expected_review_entries_sha256)
    except (OSError,TypeError,ValueError) as exc:
        print(json.dumps({
            "schema":SCHEMA,"status":"EXISTING_LICENSE_TEXT_AUDIT_FAIL_CLOSED_NO_GO",
            "failure_type":type(exc).__name__,"customer_distribution_authorized":False,
        },sort_keys=True))
        return 2
    print(json.dumps(report,sort_keys=True))
    # File hashes can be PASS while legal approval intentionally remains NO_GO.
    return 2


if __name__=="__main__":
    raise SystemExit(main())
