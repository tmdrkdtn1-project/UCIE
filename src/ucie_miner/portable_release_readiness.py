"""Read-only first-party portable ZIP release *readiness*, never approval.

This is deliberately not a signature, legal opinion or third-party security
attestation. It inspects only the current first-party UCIE source checkout,
the canonical in-memory DRAFT ZIP, and a dedicated UCIE runtime root.
"""
from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from .product_v1 import (
    ProductIntegrationError, _root, _portable_source, _portable_cli_source,
    _portable_rights_security_text, build_draft_package_bytes, PACK_SCHEMA,
)
from .portable_consumer_qa import _validated_draft_bytes

SCHEMA = "UCIE_V1_FIRST_PARTY_RELEASE_READINESS_V1"
ENTRIES = (
    "portable_exact.py", "__main__.py", "RIGHTS_SECURITY.txt",
    "MANIFEST.json", "README.txt",
)
IMPORTS = frozenset({"__future__", "typing", "json", "sys", "portable_exact"})
FORBIDDEN_CALLS = frozenset({
    "eval", "exec", "compile", "open", "__import__", "breakpoint",
    "input", "getattr", "setattr", "delattr",
})
MAX_ENTRY_BYTES = 16384


def _first_party_static_review(source: bytes, name: str) -> dict:
    """Small allowlist control; *never* claims holistic security review."""
    try:
        parsed = ast.parse(source.decode("utf-8", errors="strict"), filename=name)
    except (SyntaxError, UnicodeError) as exc:
        raise ProductIntegrationError("first-party ZIP code is not valid Python") from exc
    imports = []
    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
        elif isinstance(node, ast.Call):
            target = node.func
            if (isinstance(target, ast.Name) and target.id in FORBIDDEN_CALLS):
                raise ProductIntegrationError("forbidden dynamic execution or filesystem call")
            if isinstance(target, ast.Attribute) and target.attr in {
                    "system", "popen", "Popen", "run", "urlopen", "request",
                    "connect", "write_text", "write_bytes", "unlink", "remove"}:
                raise ProductIntegrationError("unexpected execution, network or file write")
    if any(type(item) is not str or item not in IMPORTS for item in imports):
        raise ProductIntegrationError("standalone ZIP import list expanded")
    return {"entry": name, "imports": sorted(imports),
            "source_sha256": sha256(source).hexdigest(),
            "first_party_import_allowlist_checked": True,
            "full_security_audit_or_sandbox_attested": False}


def _source_checkout() -> Path:
    return Path(__file__).resolve().parents[2]


def inspect_first_party_release(root: Path) -> dict:
    """One-shot source rights & artifact technical readiness, no writes."""
    _root(root)
    canonical, manifest = build_draft_package_bytes()
    independent, other_manifest = build_draft_package_bytes()
    if canonical != independent or manifest != other_manifest:
        raise ProductIntegrationError("nonreproducible first-party draft in same interpreter")
    _validated_draft_bytes(canonical, independent, manifest)
    if manifest.get("schema") != PACK_SCHEMA or manifest.get("version") != "1.3.0":
        raise ProductIntegrationError("unexpected first-party release candidate version")
    with ZipFile(io.BytesIO(canonical)) as archive:
        info = archive.infolist()
        if [entry.filename for entry in info] != list(ENTRIES):
            raise ProductIntegrationError("noncanonical ZIP file inventory")
        for entry in info:
            if (entry.is_dir() or entry.create_system != 3
                    or entry.date_time != (2026, 1, 1, 0, 0, 0)
                    or entry.compress_type != ZIP_DEFLATED
                    or entry.external_attr >> 16 != 0o100644
                    or not 0 < entry.file_size <= MAX_ENTRY_BYTES
                    or entry.flag_bits & 1
                    or entry.filename.startswith("/")
                    or ".." in entry.filename
                    or "\\" in entry.filename):
                raise ProductIntegrationError("ZIP entry privileges or content unsafe")
    static = [
        _first_party_static_review(_portable_source(), "portable_exact.py"),
        _first_party_static_review(_portable_cli_source(), "__main__.py"),
    ]
    source_root = _source_checkout()
    security = source_root / "SECURITY.md"
    gitignore = source_root / ".gitignore"
    if (security.is_symlink() or not security.is_file()
            or gitignore.is_symlink() or not gitignore.is_file()):
        raise ProductIntegrationError("first-party security policy not present")
    policy = security.read_text(encoding="utf-8")
    exclusions = gitignore.read_text(encoding="utf-8")
    if ("PUBLIC_ONLY" not in policy or "No project" not in policy
            and "project-to-project" not in policy
            or "runtime/" not in exclusions or "*.pem" not in exclusions):
        raise ProductIntegrationError("first-party public-only security scope drift")
    license_paths = tuple(source_root / n for n in (
        "LICENSE", "LICENSE.txt", "COPYING", "COPYING.txt"))
    if any(path.is_symlink() for path in license_paths):
        raise ProductIntegrationError("license declaration symlink is unsafe")
    available = sorted(p.name for p in license_paths if p.is_file())
    # Existence is not permission, legal review or owner attribution.
    license_state = ("DECLARATION_PRESENT_NOT_LEGALLY_CLEARED"
                     if available else "NO_REPOSITORY_LICENSE_DECLARATION")
    blockers = [
        ("REPOSITORY_LICENSE_DECLARATION_REQUIRES_OWNER_DECISION"
         if not available else "SOURCE_LICENSE_DECLARATION_REQUIRES_OWNER_REVIEW"),
        "FIRST_PARTY_CODE_OWNERSHIP_AND_NOTICES_NOT_ATTESTED",
        "OWNER_GENERIC_RELEASE_AUTHORIZATION_NOT_PROVIDED",
        "INDEPENDENT_EXTERNAL_SECURITY_AND_PACKAGE_QA_NOT_ATTESTED",
        "DISTRIBUTION_SIGNING_AND_PUBLISHING_NOT_AUTHORIZED",
    ]
    return {
        "schema": SCHEMA,
        "status": "FIRST_PARTY_RELEASE_TECHNICAL_READINESS_REVIEWED_NO_GO",
        "package": "UCIE_PORTABLE_EXACT_PUBLIC_METADATA",
        "candidate_version": manifest["version"],
        "consumer_api_version": manifest["consumer_api_version"],
        "canonical_zip_sha256": sha256(canonical).hexdigest(),
        "zip_layout_entries": list(ENTRIES),
        "zip_headers_normalized_for_windows_linux": True,
        "twice_built_bytes_identical": True,
        "first_party_python_source_sha256": manifest["code_sha256"],
        "first_party_entrypoint_sha256": manifest["standalone_cli_sha256"],
        "included_rights_security_notice_sha256": manifest[
            "rights_security_sha256"],
        "zip_executable_code_import_review": static,
        "portable_zip_third_party_runtime_packages": 0,
        "main_repo_dependencies_are_separate_from_zip": True,
        "source_checkout_security_policy_present": True,
        "source_checkout_ignore_runtime_and_keys": True,
        "repository_license_declaration_status": license_state,
        "repository_license_declaration_filenames": available,
        "owner_license_signoff": False,
        "external_independent_security_qa": False,
        "owner_release_authorized": False,
        "package_signed": False,
        "blocked_release_requirements": blockers,
        "only_current_first_party_zip_reviewed": True,
        "source_from_user_or_other_projects_examined": False,
        "network_requests": 0, "operating_database_writes": 0,
        "new_signatures_created": 0,
        "package_released": False, "v1_accepted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="First-party UCIE draft technical/rights preflight, never release")
    p.add_argument("--ucie-root", type=Path, required=True)
    args = p.parse_args()
    try:
        report = inspect_first_party_release(args.ucie_root)
    except (ProductIntegrationError, ValueError, OSError):
        report = {
            "schema": SCHEMA,
            "status": "FIRST_PARTY_RELEASE_REVIEW_FAIL_CLOSED",
            "owner_release_authorized": False,
            "package_signed": False,
            "package_released": False,
            "v1_accepted": False,
        }
        print(json.dumps(report, sort_keys=True, ensure_ascii=True))
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
