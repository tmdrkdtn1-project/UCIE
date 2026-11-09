"""UCIE-only installed MCP dependency license-marker inventory.

Reads only distribution METADATA and exact approved SDK uv.lock in a
disposable, source-SHA-pinned CI virtualenv. This is evidence gathering,
NOT a license clearance, CVE scan, package integrity proof or release gate.
No package imports, network requests, subprocesses, personal files, writes.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import sys
import tomllib
from typing import Any

SCHEMA = "UCIE_MCP_INSTALLED_DEPENDENCY_METADATA_AUDIT_V01"
COMMIT_BY_STAGE = {
    "before": "2118f14f8a19bc158d8a1cf90af58d85d187f849",
    "after": "754254c08fe1c3eda18b69da3d336106fe8d72d6",
}
LOCK_BLOB_BY_STAGE = {
    "before": "73fcc3331a93fc9442d8c2b2f85312d7cb389fbd",
    "after": "fd2dcb85f9923798334ea6259522ae4ae84185f8",
}
WORKSPACE_SOURCE = {"mcp": ".", "mcp-types": "src/mcp-types"}
REGISTRY = "https://pypi.org/simple"
MAX_LOCK_BYTES = 600_000
MAX_PACKAGES = 100
NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_.-]{0,110}[a-z0-9])?$")
SPDX_TEXT_RE = re.compile(r"^[A-Za-z0-9.()+\- /&|:]{1,150}$")


class MetadataAuditError(ValueError):
    """Safety or provenance mismatch: report no success."""


def normalized(name: object) -> str:
    if type(name) is not str or not NAME_RE.fullmatch(name.lower()):
        raise MetadataAuditError("INVALID_DISTRIBUTION_NAME")
    return re.sub(r"[-_.]+", "-", name.lower())


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw,
        usedforsecurity=False,
    ).hexdigest()


def parse_lock(raw: bytes, stage: str) -> dict[str, list[dict[str, Any]]]:
    if stage not in LOCK_BLOB_BY_STAGE or type(raw) is not bytes:
        raise MetadataAuditError("UNRECOGNIZED_LOCK_STAGE")
    if not (0 < len(raw) <= MAX_LOCK_BYTES):
        raise MetadataAuditError("LOCK_SIZE_INVALID")
    if git_blob_sha(raw) != LOCK_BLOB_BY_STAGE[stage]:
        raise MetadataAuditError("PINNED_LOCK_BLOB_MISMATCH")
    try:
        doc = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise MetadataAuditError("LOCK_PARSE_FAILED") from exc
    if doc.get("version") != 1 or type(doc.get("package")) is not list:
        raise MetadataAuditError("UNEXPECTED_LOCK_SCHEMA")
    result: dict[str, list[dict[str, Any]]] = {}
    for pkg in doc["package"]:
        if type(pkg) is not dict or type(pkg.get("source")) is not dict:
            raise MetadataAuditError("LOCK_PACKAGE_MALFORMED")
        result.setdefault(normalized(pkg.get("name")), []).append(pkg)
    if not (WORKSPACE_SOURCE.keys() <= result.keys()):
        raise MetadataAuditError("WORKSPACE_PACKAGES_MISSING")
    for name, relative in WORKSPACE_SOURCE.items():
        variants = result[name]
        if len(variants) != 1 or variants[0]["source"] != {"editable": relative}:
            raise MetadataAuditError("WORKSPACE_SOURCE_NOT_PINNED")
    return result


def read_license_marker(metadata_fields: Any) -> tuple[str, str | None, int]:
    """Only bounded declarative metadata; never return a full license text."""
    expression = str(metadata_fields.get("License-Expression", "") or "").strip()
    files = metadata_fields.get_all("License-File") or []
    license_file_count = min(len(files), 99)
    if expression:
        if SPDX_TEXT_RE.fullmatch(expression):
            return "SPDX_EXPRESSION_DECLARED", expression, license_file_count
        return "MALFORMED_OR_UNREVIEWED_SPDX", None, license_file_count
    legacy = str(metadata_fields.get("License", "") or "").strip()
    if legacy:
        if len(legacy) <= 150 and "\n" not in legacy:
            return "LEGACY_LICENSE_FIELD_ONLY", None, license_file_count
        return "LONG_LICENSE_TEXT_UNREVIEWED", None, license_file_count
    classifiers = metadata_fields.get_all("Classifier") or []
    if any(str(c).startswith("License :: ") for c in classifiers):
        return "LICENSE_CLASSIFIER_ONLY", None, license_file_count
    return "NO_LICENSE_DECLARATION_IN_METADATA", None, license_file_count


def validate_inventory(
    lock: dict[str, list[dict[str, Any]]],
    installed: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if type(installed) is not list or not 2 <= len(installed) <= MAX_PACKAGES:
        raise MetadataAuditError("INSTALLED_DISTRIBUTION_COUNT_INVALID")
    seen: set[str] = set()
    rows = []
    for row in installed:
        if type(row) is not dict:
            raise MetadataAuditError("INSTALLED_DISTRIBUTION_INVALID")
        name = normalized(row.get("name"))
        version = row.get("version")
        if name in seen or type(version) is not str or not (1 <= len(version) <= 120):
            raise MetadataAuditError("DUPLICATE_OR_INVALID_INSTALLED_DISTRIBUTION")
        seen.add(name)
        variants = lock.get(name, [])
        if not variants:
            raise MetadataAuditError("INSTALLED_DISTRIBUTION_ABSENT_IN_LOCK")
        if name in WORKSPACE_SOURCE:
            source = "PINNED_SDK_WORKSPACE"
        else:
            if not any(
                v.get("version") == version
                and v.get("source") == {"registry": REGISTRY}
                for v in variants
            ):
                raise MetadataAuditError("INSTALLED_VERSION_OR_REGISTRY_NOT_IN_LOCK")
            source = "PYPI_REGISTRY_PINNED_IN_UPSTREAM_LOCK"
        license_status = row.get("license_status")
        license_expr = row.get("spdx_expression")
        if license_status not in (
            "SPDX_EXPRESSION_DECLARED", "MALFORMED_OR_UNREVIEWED_SPDX",
            "LEGACY_LICENSE_FIELD_ONLY", "LONG_LICENSE_TEXT_UNREVIEWED",
            "LICENSE_CLASSIFIER_ONLY", "NO_LICENSE_DECLARATION_IN_METADATA",
        ):
            raise MetadataAuditError("INVALID_LICENSE_MARKER_STATUS")
        if license_status == "SPDX_EXPRESSION_DECLARED":
            if type(license_expr) is not str or not SPDX_TEXT_RE.fullmatch(license_expr):
                raise MetadataAuditError("INVALID_SPDX_METADATA")
        elif license_expr is not None:
            raise MetadataAuditError("SPDX_FIELD_MISCLASSIFIED")
        digest = row.get("metadata_sha256")
        if type(digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise MetadataAuditError("METADATA_HASH_REQUIRED")
        file_count = row.get("license_file_count")
        if type(file_count) is not int or not 0 <= file_count <= 99:
            raise MetadataAuditError("INVALID_LICENSE_FILE_COUNT")
        rows.append({
            "name": name,
            "installed_version": version,
            "source_marker": source,
            "license_metadata_status": license_status,
            "spdx_expression_if_declared": license_expr,
            "license_file_markers": file_count,
            "distribution_metadata_sha256": digest,
            "legal_approval": False,
            "security_advisories_checked": False,
        })
    if not set(WORKSPACE_SOURCE).issubset(seen):
        raise MetadataAuditError("INSTALLED_SDK_COMPONENTS_MISSING")
    return sorted(rows, key=lambda r: r["name"])


def installed_metadata_rows(root: Path) -> list[dict[str, Any]]:
    rows = []
    for dist in metadata.distributions():
        try:
            loc = Path(dist.locate_file("")).resolve(strict=True)
        except (OSError, ValueError):
            raise MetadataAuditError("INSTALLED_DISTRIBUTION_LOCATION_UNAVAILABLE")
        if not loc.is_relative_to(root):
            # Some system distribution may be visible in site import paths;
            # it was not installed into the pinned upstream SDK virtualenv.
            continue
        fields = dist.metadata
        status, expression, files_count = read_license_marker(fields)
        raw = dist.read_text("METADATA")
        if type(raw) is not str or len(raw.encode("utf-8")) > 2_000_000:
            raise MetadataAuditError("INSTALLED_METADATA_MISSING_OR_OVERSIZED")
        rows.append({
            "name": fields.get("Name"),
            "version": dist.version,
            "license_status": status,
            "spdx_expression": expression,
            "license_file_count": files_count,
            "metadata_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        })
    return rows


def audit_installed(stage: str, checkout: Path) -> dict[str, Any]:
    if (
        stage not in COMMIT_BY_STAGE or os.name != "posix"
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("UCIE_DISPOSABLE_SDK_GATE") != "1"
        or not sys.flags.isolated
        or os.environ.get("UCIE_EXACT_UPSTREAM_COMMIT") != COMMIT_BY_STAGE[stage]
    ):
        raise MetadataAuditError("DISPOSABLE_EXACT_COMMIT_RUNNER_REQUIRED")
    root = checkout.resolve(strict=True)
    if not root.is_dir() or checkout.is_symlink():
        raise MetadataAuditError("INVALID_UPSTREAM_ROOT")
    env = root / ".venv"
    if (Path(sys.prefix).resolve() != env.resolve()
            or sys.prefix == sys.base_prefix
            or not Path(sys.executable).absolute().is_relative_to(env)):
        raise MetadataAuditError("WRONG_UPSTREAM_VIRTUAL_ENV")
    raw = (root / "uv.lock").read_bytes()
    lock = parse_lock(raw, stage)
    rows = validate_inventory(lock, installed_metadata_rows(env.resolve()))
    statuses: dict[str, int] = {}
    for row in rows:
        key = row["license_metadata_status"]
        statuses[key] = statuses.get(key, 0) + 1
    return {
        "schema": SCHEMA,
        "status": "PINNED_INSTALLED_METADATA_OBSERVED_NOT_APPROVED",
        "stage": stage,
        "upstream_commit": COMMIT_BY_STAGE[stage],
        "upstream_lock_git_blob": LOCK_BLOB_BY_STAGE[stage],
        "lock_entries_all_platforms_including_dev": sum(map(len, lock.values())),
        "installed_distributions_audited": len(rows),
        "license_metadata_summary": dict(sorted(statuses.items())),
        "installed_distributions": rows,
        "package_versions_matched_original_lock": True,
        "origin_is_declared_registry_not_independent_proof": True,
        "actual_download_artifact_hashes_independently_verified": False,
        "installer_uv_wheel_hash_verified": False,
        "dependency_license_texts_reviewed": False,
        "license_redistribution_approved": False,
        "security_vulnerability_advisory_scan_executed": False,
        "security_vulnerability_status": "NOT_VERIFIED",
        "license_review_status": "NOT_APPROVED",
        "skillbook_003_published": False,
        "customer_release_authorized": False,
        "network_requests_by_auditor": 0,
        "operating_data_writes": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE exact SDK dependency metadata")
    parser.add_argument("--stage", choices=tuple(COMMIT_BY_STAGE), required=True)
    parser.add_argument("--checkout", required=True)
    args = parser.parse_args(argv)
    receipt = audit_installed(args.stage, Path(args.checkout))
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
