"""C2 draft: bounded, offline vendor wheel rights/SBOM evidence (NEVER an approval).

Inspects only the existing UCIE C1 SHA-captured, Git-ignored wheelhouse.
Reuses C1 ZIP/RECORD/receipt verification. No third-party code execution,
network, installation, unpacking, customer data, or operating DB writes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from hashlib import sha256
import json
from pathlib import Path
import re
from zipfile import ZipFile

from .customer_offline_dependency_gate_v01 import (
    OfflineDependencyError, WHEELHOUSE, _inspect_wheel, _root,
)
from .customer_owner_wheelhouse_acquire_v01 import (
    PINNED, RECEIPT, WheelAcquisitionError, verify_local,
)

SCHEMA = "UCIE_C2_OFFLINE_VENDOR_SPDX_REVIEW_V01"
STATUS = "C2_VENDOR_METADATA_REVIEW_ONLY_CUSTOMER_NO_GO"
HEX = re.compile(r"[0-9a-f]{64}\Z")
CLAIM = re.compile(r"[A-Za-z0-9.+_() \-/]{1,160}\Z")
MAX_LICENSE_BYTES = 250_000
BLOCKERS = (
    "C2_FIRST_PARTY_RIGHTSHOLDER_ATTESTATION_MISSING",
    "C2_VENDOR_LICENSE_NOTICE_LEGAL_REVIEW_MISSING",
    "C2_CAPTURED_PYPI_DIGEST_NOT_INDEPENDENT_PUBLISHER_SIGNATURE",
    "C2_VENDOR_SECURITY_ADVISORY_REVIEW_MISSING",
    "C2_TRANSITIVE_DEPENDENCY_GRAPH_AND_PLATFORM_REVIEW_MISSING",
    "C2_PRIVATE_CUSTOMER_SIGNING_AND_ENTITLEMENT_MISSING",
    "C4_INDEPENDENT_CLEAN_WINDOWS_RECIPIENT_NOT_ACCEPTED",
)


class C2ReviewError(ValueError):
    """Untrusted local metadata or incomplete UCIE-only C1 evidence."""


def _licensed_path(value: str) -> bool:
    return (type(value) is str and 0 < len(value) <= 160
            and not value.startswith(("/", "."))
            and "\\" not in value and "\x00" not in value
            and all(p not in ("", ".", "..") for p in value.split("/")))


def inspect_license_evidence(path: Path, identity: dict) -> dict:
    """Only inspect C1-integrity-checked wheel metadata; never execute files."""
    if identity.get("metadata_record_sha256_verified") is not True:
        raise C2ReviewError("C1 RECORD evidence is missing")
    dist = path.name.split("-", 2)
    if len(dist) < 2:
        raise C2ReviewError("wheel identity malformed")
    prefix = dist[0].replace("-", "_") + "-" + dist[1] + ".dist-info/"
    try:
        with ZipFile(path) as archive:
            meta = prefix + "METADATA"
            if archive.getinfo(meta).file_size > 100_000:
                raise C2ReviewError("wheel METADATA exceeds review limit")
            headers = BytesParser(policy=policy.default).parsebytes(
                archive.read(meta), headersonly=True
            )
            expressions = headers.get_all("License-Expression", [])
            legacy = headers.get_all("License", [])
            declared_files = headers.get_all("License-File", [])
            if any(len(x) > 160 for x in (*expressions, *legacy, *declared_files)):
                raise C2ReviewError("vendor license declaration too long")
            if len(expressions) > 1 or len(legacy) > 1 or len(declared_files) > 32:
                raise C2ReviewError("ambiguous license metadata headers")
            expression = str(expressions[0]) if expressions else None
            if expression is not None and not CLAIM.fullmatch(expression):
                raise C2ReviewError("invalid declared license expression")
            inventory = []
            missing = []
            names = {x.filename for x in archive.infolist()}
            for value in sorted(set(str(x) for x in declared_files)):
                if not _licensed_path(value):
                    raise C2ReviewError("unsafe License-File metadata path")
                location = prefix + "licenses/" + value
                if location not in names:
                    missing.append(value)
                    continue
                info = archive.getinfo(location)
                if info.is_dir() or info.file_size > MAX_LICENSE_BYTES:
                    raise C2ReviewError("license evidence file invalid or oversized")
                inventory.append({
                    "license_file": value,
                    "sha256": sha256(archive.read(location)).hexdigest(),
                    "size": info.file_size,
                })
            notice_files = [
                x.filename for x in archive.infolist()
                if x.filename.startswith(prefix + "licenses/")
                and x.filename.rsplit("/", 1)[-1].lower().startswith("notice")
                and not x.is_dir()
            ]
            if len(notice_files) > 16:
                raise C2ReviewError("unbounded NOTICE evidence")
            notice = []
            for name in sorted(notice_files):
                item = archive.getinfo(name)
                if item.file_size > MAX_LICENSE_BYTES:
                    raise C2ReviewError("NOTICE file exceeds bounded review")
                notice.append({
                    "path": name.removeprefix(prefix + "licenses/"),
                    "sha256": sha256(archive.read(name)).hexdigest(),
                    "size": item.file_size,
                })
    except (KeyError, OSError, ValueError, UnicodeError) as exc:
        raise C2ReviewError("wheel license metadata could not be verified") from exc
    return {
        "license_expression_claim_only": expression,
        "legacy_license_claim_only": str(legacy[0]) if legacy else None,
        "license_files": inventory,
        "license_files_missing": missing,
        "notice_files": notice,
        "licenses_or_notices_legally_reviewed": False,
    }


def _spdx_draft(packages: list[dict], digest: str) -> dict:
    """SPDX 2.3 structural inventory; NOASSERTION is intentional."""
    entries = []
    relations = []
    for item in packages:
        name, version = item["name"], item["version"]
        ref = "SPDXRef-Package-" + name
        entries.append({
            "SPDXID": ref,
            "name": name,
            "versionInfo": version,
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION",
            "checksums": [{"algorithm": "SHA256", "checksumValue": item["sha256"]}],
            "externalRefs": [{
                "referenceCategory": "PACKAGE-MANAGER",
                "referenceType": "purl",
                "referenceLocator": "pkg:pypi/" + name + "@" + version,
            }],
            "comment": "Unreviewed C1 captured PyPI receipt; NOTICE and rights not attested.",
        })
        relations.append({
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": ref,
        })
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "UCIE C2 offline vendor review - UNSIGNED NO_GO",
        "documentNamespace": "https://github.com/tmdrkdtn1-project/UCIE/c2-review/" + digest,
        "creationInfo": {
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "creators": ["Tool: UCIE-C2-offline-vendor-review-v01"],
            "comment": "Draft metadata inventory, NOT independent provenance or rights review.",
        },
        "packages": entries,
        "relationships": relations,
    }


def inspect_c2(root: Path) -> dict:
    root = _root(root)
    try:
        c1 = verify_local(root)
    except (WheelAcquisitionError, OfflineDependencyError, ValueError, OSError) as exc:
        raise C2ReviewError("C1 local captured wheelhouse not verified") from exc
    if c1.get("all_local_bytes_match_captured_pypi_digests") is not True:
        raise C2ReviewError("C1 wheelhouse capture is not byte-verified")
    receipt = root / RECEIPT
    if receipt.is_symlink() or receipt.stat().st_size > 15_000:
        raise C2ReviewError("C1 receipt path invalid")
    try:
        captured = json.loads(receipt.read_text(encoding="ascii"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise C2ReviewError("C1 capture receipt malformed") from exc
    if type(captured) is not dict or type(captured.get("files")) is not list:
        raise C2ReviewError("C1 capture entries invalid")
    indexed = {x["distribution"]: x for x in captured["files"]}
    if set(indexed) != {name for name, _ in PINNED} or len(indexed) != len(PINNED):
        raise C2ReviewError("C1 capture scope drift")
    products = []
    gaps = []
    for name, version in sorted(PINNED):
        item = indexed[name]
        if (item.get("version") != version
                or type(item.get("sha256")) is not str
                or not HEX.fullmatch(item["sha256"])):
            raise C2ReviewError("C1 captured release pin mismatch")
        filename = item.get("filename")
        if (type(filename) is not str or "/" in filename or "\\" in filename
                or not filename.endswith(".whl")):
            raise C2ReviewError("C1 captured filename invalid")
        wheel = root / WHEELHOUSE / filename
        if wheel.is_symlink() or not wheel.is_file():
            raise C2ReviewError("C1 wheel missing/linked")
        record = _inspect_wheel(wheel)
        if (record["name"] != name or record["version"] != version
                or record["wheel_sha256"] != item["sha256"]):
            raise C2ReviewError("wheel metadata differs from C1 captured pin")
        rights = inspect_license_evidence(wheel, record)
        if not rights["license_files"]:
            gaps.append("LICENSE_FILE_NOT_OBSERVED:" + name)
        if rights["license_files_missing"]:
            gaps.append("DECLARED_LICENSE_FILE_MISSING:" + name)
        if not rights["license_expression_claim_only"]:
            gaps.append("SPDX_EXPRESSION_NOT_DECLARED:" + name)
        products.append({
            "name": name,
            "version": version,
            "filename": filename,
            "sha256": item["sha256"],
            "size": record["wheel_bytes"],
            "tags": [record["python_tag"], record["abi_tag"], record["platform_tag"]],
            "requires_dist_metadata": record["requires_dist"],
            "license_evidence": rights,
            "binary_executed": False,
            "publisher_signed_identity_attested": False,
            "rights_cleared": False,
        })
    evidence = json.dumps(products, sort_keys=True, ensure_ascii=True,
                          separators=(",", ":")).encode("ascii")
    digest = sha256(evidence).hexdigest()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "source": "EXISTING_UCIE_C1_LOCAL_CAPTURED_WHEELHOUSE_ONLY",
        "target": "win_amd64-cp315-standard",
        "packages": products,
        "evidence_sha256": digest,
        "spdx_2_3_draft_noassertion": _spdx_draft(products, digest),
        "blockers": sorted(set(BLOCKERS + tuple(gaps))),
        "package_count": len(products),
        "network_requests": 0,
        "vendor_code_executed_or_installed": False,
        "other_project_access": False,
        "operating_database_writes": 0,
        "signing_or_release_performed": False,
        "customer_distribution_authorized": False,
        "c2_approved": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE C2 offline vendor review only")
    parser.add_argument("--inspect", action="store_true")
    parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    try:
        result = inspect_c2(root)
    except (C2ReviewError, OfflineDependencyError, OSError, ValueError):
        result = {
            "schema": SCHEMA,
            "status": "C2_SOURCE_OR_VENDOR_EVIDENCE_UNAVAILABLE_NO_GO",
            "c2_approved": False,
            "customer_distribution_authorized": False,
            "vendor_code_executed_or_installed": False,
        }
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 2  # A review draft never constitutes legal/security/customer GO.


if __name__ == "__main__":
    raise SystemExit(main())
