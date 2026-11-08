"""UCIE C0+C1: first-party offline staging capsule, never a customer release.

Builds a bounded tamper-evident inventory around an already-built UCIE wheel
and a real four-pillar synthetic functional receipt. It does not install,
sign, license, export approved SkillBooks, fetch dependencies, or touch runtime.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import stat
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo

from .customer_staging_v01 import PILLARS, SCHEMA as FOUR_PILLAR_SCHEMA
from .customer_staging_v01 import run_four_pillar_staging

SCHEMA = "UCIE_C0_C1_OFFLINE_STAGING_CAPSULE_V01"
STATUS = "FIRST_PARTY_OFFLINE_STAGING_CAPSULE_UNSIGNED_NO_GO"
DIST = "ucie_public_only_demo-0.1.0.dist-info/"
MAX_WHEEL = 32_000_000
MAX_CAPSULE = 36_000_000
MAX_MEMBERS = 500
WHEEL_NAME = re.compile(r"ucie_public_only_demo-0\.1\.0-[A-Za-z0-9_.-]+\.whl\Z")
CAPSULE_NAME = re.compile(r"UCIE_STAGING_[0-9a-f]{12}\.zip\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")
REQUIRED = frozenset({
    "ucie_miner/customer_staging_v01.py",
    "ucie_miner/guarded_scandir.py",
    "ucie_miner/capability_trials.py",
    "ucie_miner/skillbook_product_v01.py",
    "ucie_miner/experience_evolution.py",
    DIST + "METADATA",
    DIST + "WHEEL",
    DIST + "entry_points.txt",
    DIST + "RECORD",
})
README = (
    "UCIE C0+C1 FIRST-PARTY OFFLINE STAGING ONLY\n"
    "NOT a customer deliverable, signed release, or approved SkillBook export.\n"
    "The wheel's declared third-party dependencies are NOT included.\n"
    "No license, entitlement, installer, updater, or rollback is provided.\n"
    "Do not copy or deploy this artifact to customers.\n"
)
BLOCKERS = (
    "DEPENDENCY_WHEELHOUSE_NOT_INCLUDED",
    "FOUR_PILLAR_CUSTOMER_FUNCTIONAL_ACCEPTANCE_NOT_ATTESTED",
    "SKILLBOOK_EDITORIAL_AND_EXPORT_RIGHTS_NOT_APPROVED",
    "INSTALL_UPDATE_ROLLBACK_UNINSTALL_NOT_ACCEPTED",
    "THIRD_PARTY_RIGHTS_AND_SECURITY_QA_NOT_ATTESTED",
    "CUSTOMER_LICENSE_AND_OWNER_SIGNATURE_NOT_PRESENT",
)


class OfflineCapsuleError(ValueError):
    pass


def _canon(item: object) -> bytes:
    return json.dumps(item, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")).encode("utf-8")


def _root(root: Path) -> Path:
    if (not isinstance(root, Path) or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()
            or not (root / ".git").is_dir() or (root / ".git").is_symlink()
            or (root / "dist").is_symlink()):
        raise OfflineCapsuleError("dedicated first-party UCIE checkout required")
    return root


def _member_check(items: list[ZipInfo], maximum: int) -> set[str]:
    if not 1 <= len(items) <= maximum:
        raise OfflineCapsuleError("invalid archive member count")
    names = set()
    total = 0
    for item in items:
        name = item.filename
        parts = name.split("/")
        if (not name or name.startswith("/") or "\\" in name
                or any(part in ("", ".", "..") for part in parts)
                or name in names or item.is_dir()
                or stat.S_ISLNK(item.external_attr >> 16)):
            raise OfflineCapsuleError("unsafe or duplicated archive member")
        if item.file_size < 0 or item.file_size > MAX_WHEEL:
            raise OfflineCapsuleError("oversized archive member")
        total += item.file_size
        if total > MAX_CAPSULE:
            raise OfflineCapsuleError("oversized archive expanded content")
        names.add(name)
    return names


def _check_wheel(raw: bytes) -> None:
    try:
        with ZipFile(io.BytesIO(raw)) as wheel:
            names = _member_check(wheel.infolist(), MAX_MEMBERS)
            if not REQUIRED.issubset(names):
                raise OfflineCapsuleError("four-pillar wheel inventory missing")
            for filename in names:
                if filename.startswith(("runtime/", "tests/", ".github/")):
                    raise OfflineCapsuleError("operating or test payload forbidden")
                if filename.endswith((".pem", ".key", ".pfx", ".env", ".sqlite3")):
                    raise OfflineCapsuleError("sensitive payload forbidden")
            for filename in (DIST + "METADATA", DIST + "entry_points.txt",
                             DIST + "RECORD"):
                if wheel.getinfo(filename).file_size > 64_000:
                    raise OfflineCapsuleError("oversized package metadata")
            metadata = wheel.read(DIST + "METADATA").decode("utf-8", "strict")
            entries = wheel.read(DIST + "entry_points.txt").decode("utf-8", "strict")
            record = wheel.read(DIST + "RECORD").decode("utf-8", "strict")
            if ("\nName: ucie-public-only-demo\n" not in "\n" + metadata
                    or "\nVersion: 0.1.0\n" not in "\n" + metadata
                    or "Requires-Dist: cryptography" not in metadata
                    or "[console_scripts]" not in entries
                    or "ucie-product-preview = ucie_miner.customer_staging_v01:main"
                    not in entries):
                raise OfflineCapsuleError("unexpected wheel identity or entrypoint")
            recorded = {row[0] for row in csv.reader(io.StringIO(record)) if row}
            if not REQUIRED.issubset(recorded):
                raise OfflineCapsuleError("wheel RECORD inventory incomplete")
    except (BadZipFile, UnicodeError, KeyError, OSError) as exc:
        raise OfflineCapsuleError("invalid bounded wheel") from exc


def _zip_write(archive: ZipFile, name: str, content: bytes) -> None:
    item = ZipInfo(name, (2020, 1, 1, 0, 0, 0))
    item.compress_type = ZIP_DEFLATED
    item.create_system = 3
    item.external_attr = 0o100644 << 16
    archive.writestr(item, content)


def _receipt() -> bytes:
    try:
        receipt = run_four_pillar_staging()
    except Exception as exc:
        raise OfflineCapsuleError("UCIE-owned synthetic workflow failed") from exc
    if (receipt.get("schema") != FOUR_PILLAR_SCHEMA
            or receipt.get("pillars_exercised") != list(PILLARS)
            or receipt.get("four_pillars_exercised") is not True
            or receipt.get("product_capabilities_worked_in_staging") is not True
            or set(receipt.get("workflows", {})) != set(PILLARS)
            or any(receipt.get(field) is not False for field in (
                "complete_customer_functional_acceptance",
                "customer_license_issued", "customer_bundle_signed",
                "customer_distribution_authorized", "customer_data_scanned",
                "upstream_source_executed", "operating_ucie_database_written",
                "customer_project_modified", "scheduler_modified",
                "automatic_rule_promotion"))):
        raise OfflineCapsuleError("four-pillar staging contract not met")
    return _canon(receipt)


def _manifest(wheel_name: str, payloads: dict[str, bytes]) -> dict:
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "wheel_name": wheel_name,
        "files": [
            {"name": name, "bytes": len(payloads[name]),
             "sha256": sha256(payloads[name]).hexdigest()}
            for name in sorted(payloads)
        ],
        "pillars_exercised": list(PILLARS),
        "source": "UCIE_FIRST_PARTY_SYNTHETIC_EXECUTION_ONLY",
        "dependencies_bundled": False,
        "installed_customer_application": False,
        "customer_license_issued": False,
        "signature_verified": False,
        "customer_distribution_authorized": False,
        "automatic_rule_promotion": False,
        "blockers": list(BLOCKERS),
    }


def build_staging_capsule(root: Path, wheel_name: str) -> dict:
    """Only read a fixed UCIE dist wheel, only create UCIE/dist/staging file."""
    root = _root(root)
    if type(wheel_name) is not str or WHEEL_NAME.fullmatch(wheel_name) is None:
        raise OfflineCapsuleError("unexpected UCIE product wheel name")
    source = root / "dist" / wheel_name
    stage = root / "dist" / "staging"
    if (source.is_symlink() or not source.is_file()
            or stage.is_symlink() or (stage.exists() and not stage.is_dir())):
        raise OfflineCapsuleError("UCIE wheel/staging path invalid")
    size = source.stat().st_size
    if not 0 < size <= MAX_WHEEL:
        raise OfflineCapsuleError("wheel outside bounded size")
    wheel = source.read_bytes()
    if len(wheel) != size:
        raise OfflineCapsuleError("wheel changed while being read")
    _check_wheel(wheel)
    receipt = _receipt()
    payloads = {
        "STAGING_ONLY.txt": README.encode("utf-8"),
        "four_pillar_receipt.json": receipt,
        "wheelhouse/" + wheel_name: wheel,
    }
    manifest = _manifest(wheel_name, payloads)
    stage.mkdir(exist_ok=True)
    target = stage / ("UCIE_STAGING_" + sha256(wheel).hexdigest()[:12] + ".zip")
    # Exclusive create. Never touch a pre-existing destination, even if empty.
    with ZipFile(target, "x") as output:
        for name in sorted(payloads):
            _zip_write(output, name, payloads[name])
        _zip_write(output, "manifest.json", _canon(manifest))
    verified = verify_staging_capsule(root, target.name)
    return {**verified, "created_under_ucie_dist_only": True}


def verify_staging_capsule(root: Path, capsule_name: str) -> dict:
    root = _root(root)
    if type(capsule_name) is not str or CAPSULE_NAME.fullmatch(capsule_name) is None:
        raise OfflineCapsuleError("invalid exact staging capsule name")
    path = root / "dist" / "staging" / capsule_name
    if ((root / "dist" / "staging").is_symlink() or path.is_symlink()
            or not path.is_file() or not 0 < path.stat().st_size <= MAX_CAPSULE):
        raise OfflineCapsuleError("unsafe or missing first-party capsule")
    try:
        with ZipFile(path) as archive:
            names = _member_check(archive.infolist(), 5)
            if "manifest.json" not in names:
                raise OfflineCapsuleError("missing staging manifest")
            if archive.getinfo("manifest.json").file_size > 16_000:
                raise OfflineCapsuleError("oversized staging manifest")
            manifest = json.loads(archive.read("manifest.json").decode("utf-8", "strict"))
            if (type(manifest) is not dict
                    or manifest.get("schema") != SCHEMA
                    or manifest.get("status") != STATUS
                    or manifest.get("pillars_exercised") != list(PILLARS)
                    or manifest.get("source") !=
                        "UCIE_FIRST_PARTY_SYNTHETIC_EXECUTION_ONLY"
                    or manifest.get("blockers") != list(BLOCKERS)
                    or any(manifest.get(field) is not False for field in (
                        "dependencies_bundled", "installed_customer_application",
                        "customer_license_issued", "signature_verified",
                        "customer_distribution_authorized",
                        "automatic_rule_promotion"))):
                raise OfflineCapsuleError("staging authority/status forged")
            wheel_name = manifest.get("wheel_name")
            if type(wheel_name) is not str or WHEEL_NAME.fullmatch(wheel_name) is None:
                raise OfflineCapsuleError("invalid manifest wheel")
            payload_names = {
                "STAGING_ONLY.txt", "four_pillar_receipt.json",
                "wheelhouse/" + wheel_name,
            }
            if names != (payload_names | {"manifest.json"}):
                raise OfflineCapsuleError("unexpected extra capsule content")
            files = manifest.get("files")
            if type(files) is not list or len(files) != 3:
                raise OfflineCapsuleError("incorrect bounded manifest")
            if [item.get("name") for item in files] != sorted(payload_names):
                raise OfflineCapsuleError("manifest name drift")
            for item in files:
                name = item["name"]
                content = archive.read(name)
                if (type(item.get("bytes")) is not int
                        or item["bytes"] != len(content)
                        or type(item.get("sha256")) is not str
                        or HEX.fullmatch(item["sha256"]) is None
                        or sha256(content).hexdigest() != item["sha256"]):
                    raise OfflineCapsuleError("capsule content integrity mismatch")
            if archive.read("STAGING_ONLY.txt") != README.encode("utf-8"):
                raise OfflineCapsuleError("staging-only disclaimer changed")
            _check_wheel(archive.read("wheelhouse/" + wheel_name))
            functional = json.loads(archive.read("four_pillar_receipt.json"))
            if (functional.get("schema") != FOUR_PILLAR_SCHEMA
                    or functional.get("pillars_exercised") != list(PILLARS)
                    or functional.get("four_pillars_exercised") is not True
                    or functional.get("product_capabilities_worked_in_staging")
                       is not True
                    or set(functional.get("workflows", {})) != set(PILLARS)
                    or functional.get("customer_distribution_authorized") is not False
                    or functional.get("complete_customer_functional_acceptance")
                       is not False):
                raise OfflineCapsuleError("functional staging receipt invalid")
    except (BadZipFile, OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        if isinstance(exc, OfflineCapsuleError):
            raise
        raise OfflineCapsuleError("unsafe offline capsule contents") from exc
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "capsule_name": capsule_name,
        "capsule_sha256": sha256(path.read_bytes()).hexdigest(),
        "payload_sha256_verified": True,
        "four_pillars_synthetically_exercised": True,
        "third_party_dependencies_bundled": False,
        "customer_install_update_rollback_tested": False,
        "customer_distribution_authorized": False,
        "private_signatures_verified": False,
        "operating_database_writes": 0,
        "scheduler_mutated": False,
        "other_projects_accessed": False,
        "blockers": list(BLOCKERS),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE-only unsigned four-pillar offline staging capsule"
    )
    parser.add_argument("--root", required=True, type=Path)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--wheel")
    actions.add_argument("--verify")
    args = parser.parse_args(argv)
    try:
        report = (build_staging_capsule(args.root, args.wheel)
                  if args.wheel is not None
                  else verify_staging_capsule(args.root, args.verify))
    except Exception:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_OFFLINE_STAGING_CAPSULE_FAIL_CLOSED",
            "customer_distribution_authorized": False,
            "operating_database_writes": 0,
        }, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
