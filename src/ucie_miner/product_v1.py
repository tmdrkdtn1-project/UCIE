"""UCIE P9 one-command *integration preview* and independent draft consumer.

Closes the previous W01/W04/W06/W07/W08/P8/W09 fragmentation for honest
inspection, source-bound search, testable UCIE-authored consumer packaging,
and experience-readback. A preview or draft package is NOT a production
release/owner sign-off/independent QA approval or P9 V1 acceptance.

No network, operating DB writes, auto-promotion, scheduler, external/private
project data, new source route, model learning or signing key use.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

from .source_registry import preview_source_registry
from .library_search import search_existing_public_library
from .library_shelves import search_official_metadata_shelf
from .experience_application import experience_library_preview
from .capability_experience import read_capability_history
from .portable_exact import search_public_metadata, SCHEMA as CONSUMER_SCHEMA
from .capability_trials import evaluate_ucie_owned_recipe
from .signed_rule_library import inspect_signed_library

SCHEMA = "UCIE_P9_PRODUCT_INTEGRATION_PREVIEW_V1"
PACK_SCHEMA = "UCIE_W09_DRAFT_INDEPENDENT_CONSUMER_V1"
PACKAGE_NAME = "ucie_portable_exact_1_0_0_DRAFT.zip"
MAX_SOURCE_BYTES = 16384
MAX_ZIP_BYTES = 32768


class ProductIntegrationError(ValueError):
    pass


def _root(root: Path) -> Path:
    if (not isinstance(root, Path) or root.is_symlink()
            or root.name.casefold() != "ucie" or not root.is_dir()):
        raise ProductIntegrationError("dedicated UCIE checkout required")
    runtime = root / "runtime"
    if runtime.is_symlink() or not runtime.is_dir():
        raise ProductIntegrationError("existing UCIE-only runtime required")
    return root


def _demo_input() -> list[dict]:
    """Never export any actual public PR data to a consumer draft."""
    rows = []
    for n, purpose in enumerate(("API_CONTRACT", "CONCURRENCY", "API_CONTRACT")):
        rows.append({
            "source_id": "repo:python/cpython", "domain": "Python",
            "kind": "PUBLIC_TECHNICAL_EVIDENCE", "purpose_code": purpose,
            "library_item_id": sha256(f"UCIE-DEMO-ID:{n}".encode()).hexdigest(),
            "public_url": "https://github.com/python/cpython/pull/" + str(n + 1),
            "evidence_sha256": sha256(f"UCIE-DEMO-EVIDENCE:{n}".encode()).hexdigest(),
            "human_approved": False, "export_allowed": False,
        })
    return rows


def portable_consumer_check() -> dict:
    """UCIE-authored sample: search parity, miss, single-vs-batch execution."""
    rows = _demo_input()
    key = ("repo:python/cpython", "Python",
           "PUBLIC_TECHNICAL_EVIDENCE", "API_CONTRACT")
    miss = key[:3] + ("NO_SUCH_EXPERIENCE",)
    first = search_public_metadata(rows, queries=(key,))
    second = search_public_metadata(rows, queries=(key, miss))
    expected = tuple(row["library_item_id"] for row in rows
                     if tuple(row[field] for field in (
                         "source_id", "domain", "kind", "purpose_code")) == key)
    got_single = tuple(x["library_item_id"] for x in first["results"][0]["items"])
    got_batch = tuple(x["library_item_id"] for x in second["results"][0]["items"])
    valid = (set(expected) == set(got_single) == set(got_batch)
             and first["strategy"] == "LINEAR_EXACT_SCAN"
             and second["strategy"] == "COMPOSITE_INDEX"
             and second["results"][1]["total_matches"] == 0)
    return {
        "status": ("FIRST_PARTY_PORTABLE_CONSUMER_DEMO_EQUIVALENT"
                   if valid else "FIRST_PARTY_PORTABLE_CONSUMER_DEMO_MISMATCH"),
        "consumer_schema": CONSUMER_SCHEMA,
        "input": "UCIE_AUTHOR_SYNTHETIC_ONLY",
        "standalone_import_independently_tested_here": False,
        "single_query_strategy": first["strategy"],
        "batch_strategy": second["strategy"],
        "positive_exact_match_count": len(expected),
        "zero_match_checked": second["results"][1]["total_matches"] == 0,
        "all_queries_equivalent": valid,
        "original_upstream_code_executed": False,
        "approved_or_exportable_public_candidates": 0,
    }


def integrated_product_preview(root: Path, *, query: str = "",
                               domain: str | None = None,
                               limit: int = 5,
                               include_demo: bool = False,
                               signed_serial4: Path | None = None,
                               owner_public_trust: Path | None = None,
                               signed_serial5: Path | None = None) -> dict:
    """Read all UCIE-owned shelves without assuming any one shelf is V1 PASS."""
    _root(root)
    if type(include_demo) is not bool:
        raise ProductIntegrationError("invalid demo request")
    if (signed_serial4 is None) != (owner_public_trust is None):
        raise ProductIntegrationError("existing signed pack and public trust must be paired")
    if signed_serial5 is not None and signed_serial4 is None:
        raise ProductIntegrationError("signed serial5 cannot stand alone")
    sources = preview_source_registry(include_research=False)
    public = search_existing_public_library(
        root, query=query, domain=domain, limit=limit, group_revisions=True)
    official = search_official_metadata_shelf(root, limit=limit)
    p8 = experience_library_preview(root)
    w05 = read_capability_history(root, limit=limit)
    signed = (inspect_signed_library(
        root, serial4_pack=signed_serial4, owner_public_trust=owner_public_trust,
        serial5_pack=signed_serial5)
        if signed_serial4 is not None else None)
    standalone_demo = portable_consumer_check() if include_demo else None
    synthetic_trials = (
        [evaluate_ucie_owned_recipe(purpose) for purpose in (
            "ENGINE_INCREMENTAL_BUILD", "SKILL_TEST_AUTOMATION",
            "LEARNING_FEEDBACK_LOOP")] if include_demo else None)
    public_ok = public["status"] == "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO"
    official_ok = official["status"] == "STAGE14_OFFICIAL_METADATA_READ_ONLY_UNVERIFIED_NO_GO"
    # A missing local official ledger remains a transparent blocker, never a
    # silent success. Passing the synthetic demo does NOT release a package.
    blockers = []
    if not public_ok:
        blockers.append("SOURCE_LINKED_W04_LEDGER_UNAVAILABLE_OR_UNVERIFIED")
    if not official_ok:
        blockers.append("STAGE14_OFFICIAL_METADATA_NOT_READY")
    if signed is None:
        blockers.append("SIGNED_RULEPACK_OR_PUBLIC_TRUST_NOT_SUPPLIED")
    blockers.extend((
        "INDEPENDENT_PACKAGE_QA_NOT_ATTESTED",
        "PORTABLE_DRAFT_NOT_OWNER_APPROVED_FOR_RELEASE",
        "W05_UPSTREAM_CAPABILITY_NOT_VERIFIED",
        "P9_FULL_ACCEPTANCE_NOT_OBSERVED",
    ))
    return {
        "schema": SCHEMA, "status": "P9_INTEGRATED_READ_ONLY_PRODUCT_PREVIEW_NO_GO",
        "product": "UCIE_PRIVATE_FIRST_PARTY_PREVIEW",
        "source_registry": {
            "schema": sources["schema"],
            "approved_source_count": sources["active_source_count"],
            "source_allowlist_changed": False,
        },
        "public_candidate_library": public,
        "official_public_metadata_library": official,
        "signed_rules": {
            "status": ("EXISTING_OWNER_SIGNED_VERIFIED_READ_ONLY"
                       if signed is not None else "NOT_INSPECTED_NO_GO"),
            "verified_signed_rule_count": (
                signed["signed_rule_count"] if signed is not None else 0),
            "independent_qa_signed_off": False,
            "source_pack_metadata": (
                signed["source_pack_sha256s"] if signed is not None else {}),
        },
        "p8_owned_synthetic_experience": {
            "status": p8["status"],
            "recorded_experiments": p8["recorded_experiments"],
            "last_event_sha256": p8["last_event_sha256"],
            "next_unexecuted_workload": p8["next_unexecuted_workload"],
        },
        "w05_candidate_linked_experience": {
            "status": w05["status"],
            "recorded_count": w05["recorded_count"],
            "last_event_sha256": w05["last_event_sha256"],
        },
        "portable_first_party_consumer_demo": standalone_demo,
        "first_party_synthetic_experiments": synthetic_trials,
        "gates_blocking_product_acceptance": blockers,
        "default_live_public_fetch_enabled": False,
        "operating_database_writes": 0,
        "new_experience_writes": 0,
        "network_requests": 0, "new_signatures_created": 0,
        "scheduler_registered": False, "model_weights_changed": False,
        "candidate_auto_promoted": False,
        "package_released": False, "v1_accepted": False,
    }


def _portable_source() -> bytes:
    path = Path(__file__).with_name("portable_exact.py")
    if path.is_symlink() or not path.is_file():
        raise ProductIntegrationError("unsafe first-party portable source")
    source = path.read_bytes()
    if not 0 < len(source) <= MAX_SOURCE_BYTES:
        raise ProductIntegrationError("portable source changed or too large")
    if not source.startswith(b'"""UCIE-authored portable exact metadata lookup V1.'):
        raise ProductIntegrationError("unrecognized first-party portable source")
    return source


def build_draft_package_bytes() -> tuple[bytes, dict]:
    """No write. Produce deterministic UCIE-authored DRAFT, never a signed release."""
    source = _portable_source()
    fingerprint = sha256(source).hexdigest()
    manifest = {
        "schema": PACK_SCHEMA,
        "package_id": "UCIE_PORTABLE_EXACT_PUBLIC_METADATA",
        "version": "1.0.0",
        "code_file": "portable_exact.py",
        "code_sha256": fingerprint,
        "runtime_dependency": "PYTHON_STANDARD_LIBRARY_ONLY",
        "tested_platform_claim": "NOT_INDEPENDENTLY_ATTESTED",
        "upstream_public_code_included": False,
        "user_project_data_included": False,
        "api_keys_or_credentials_included": False,
        "source_license_signoff": False,
        "owner_release_authorized": False,
        "independent_qa_signed_off": False,
        "signed": False,
        "status": "DRAFT_FIRST_PARTY_CONSUMER_NOT_APPROVED_FOR_DISTRIBUTION",
    }
    readme = (
        "UCIE AUTHORED DRAFT - NOT RELEASED, NOT LICENSE ATTESTED\n"
        "Python standard library only. This bundle contains no third-party\n"
        "PR code, user project data, keys, or verified upstream skills.\n"
        "Only sanitized approved public-source metadata accepted by\n"
        "search_public_metadata(items, queries=tuple_of_exact_four_field_keys).\n"
        "This draft cannot claim package release/signature/third-party QA.\n"
    ).encode("ascii")
    in_mem = io.BytesIO()
    with ZipFile(in_mem, "w", compression=ZIP_DEFLATED) as z:
        for name, data in (
            ("portable_exact.py", source),
            ("MANIFEST.json", json.dumps(
                manifest, sort_keys=True, separators=(",", ":")).encode("ascii")),
            ("README.txt", readme),
        ):
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    payload = in_mem.getvalue()
    if len(payload) > MAX_ZIP_BYTES:
        raise ProductIntegrationError("draft package exceeds bound")
    return payload, manifest


def explicitly_export_draft(root: Path) -> dict:
    """Explicit local-only draft, NO production install or third-party distribution."""
    _root(root)
    payload, manifest = build_draft_package_bytes()
    dest = root / "runtime" / "exports"
    if dest.is_symlink():
        raise ProductIntegrationError("unsafe exports path")
    if not dest.exists():
        dest.mkdir(mode=0o700)
    if not dest.is_dir():
        raise ProductIntegrationError("exports path must be a UCIE directory")
    target = dest / PACKAGE_NAME
    if target.is_symlink():
        raise ProductIntegrationError("unsafe package link")
    content_hash = sha256(payload).hexdigest()
    if target.exists():
        if not target.is_file() or target.read_bytes() != payload:
            raise ProductIntegrationError("cannot overwrite existing draft package")
        written = False
    else:
        try:
            with target.open("xb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
        except FileExistsError as exc:
            raise ProductIntegrationError("draft created by another writer") from exc
        written = True
    return {
        "schema": PACK_SCHEMA,
        "status": "UCIE_ONLY_DRAFT_WRITTEN_NOT_RELEASED" if written else
                  "SAME_UCIE_ONLY_DRAFT_ALREADY_PRESENT_NOT_RELEASED",
        "relative_path": "runtime/exports/" + PACKAGE_NAME,
        "sha256": content_hash,
        "code_sha256": manifest["code_sha256"],
        "created": written, "production_release_approved": False,
        "standalone_consumer_qa_attested": False,
        "upstream_source_code_copied": False, "other_project_data_accessed": False,
        "operating_database_writes": 0, "network_requests": 0,
        "new_signatures_created": 0, "auto_promoted": False,
        "v1_accepted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UCIE P9 single read-only product entrypoint and opt-in UCIE-owned draft export")
    parser.add_argument("--ucie-root", type=Path, required=True)
    parser.add_argument("--query", default="")
    parser.add_argument("--domain")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--serial4-pack", type=Path)
    parser.add_argument("--owner-public-trust", type=Path)
    parser.add_argument("--serial5-pack", type=Path)
    parser.add_argument("--export-draft", action="store_true",
                        help="Explicitly write ONE UCIE-only draft zip (not a release)")
    args = parser.parse_args()
    try:
        if args.export_draft:
            if (args.query or args.domain or args.demo or args.serial4_pack or
                    args.owner_public_trust or args.serial5_pack or args.limit != 5):
                raise ProductIntegrationError("draft export cannot combine search or pack flags")
            out = explicitly_export_draft(args.ucie_root)
        else:
            out = integrated_product_preview(
                args.ucie_root, query=args.query, domain=args.domain,
                limit=args.limit, include_demo=args.demo,
                signed_serial4=args.serial4_pack,
                owner_public_trust=args.owner_public_trust,
                signed_serial5=args.serial5_pack)
    except (ValueError, OSError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "P9_PRODUCT_FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "network_requests": 0, "operating_database_writes": 0,
            "package_released": False, "v1_accepted": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(out, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
