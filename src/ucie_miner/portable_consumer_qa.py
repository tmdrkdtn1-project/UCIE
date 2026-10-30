"""Isolated first-party portable engine QA, never a distribution authorization.

This module proves canonical draft ZIP consumer behavior using *only* UCIE
authored source code in a disposable interpreter. Public W04 PR rows remain
unverified metadata; no upstream code is downloaded, executed or repackaged.
"""
from __future__ import annotations

from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile, BadZipFile

from .library_search import search_existing_public_library
from .portable_exact import (
    search_public_metadata, PortableLookupError, FIELDS, SCHEMA as LOOKUP_SCHEMA,
    VERSION as LOOKUP_VERSION,
)
from .product_v1 import (
    ProductIntegrationError, _root, _demo_input,
    _portable_public_ledger_handoff, _portable_source, _portable_cli_source,
    build_draft_package_bytes, PACK_SCHEMA,
)

SCHEMA = "UCIE_V1_ISOLATED_PORTABLE_ENGINE_QA_V1"
MAX_INPUT_BYTES = 32768
MAX_OUTPUT_BYTES = 65536
_RUNNER = """import json,sys
sys.path.insert(0,sys.argv[1])
from portable_exact import search_public_metadata
raw=sys.stdin.buffer.read(32769)
if not raw or len(raw)>32768: raise ValueError("bounded first-party QA required")
data=json.loads(raw.decode("ascii"))
if type(data) is not list or len(data)!=3: raise ValueError("QA cases")
answers=[search_public_metadata(case["items"],
    queries=tuple(tuple(key) for key in case["queries"]),
    limit=case["limit"]) for case in data]
sys.stdout.write(json.dumps(answers,sort_keys=True,ensure_ascii=True))
"""


def _validated_draft_bytes(payload: bytes, expected: bytes, expected_manifest: dict) -> bytes:
    if type(payload) is not bytes or payload != expected or len(payload) > 32768:
        raise ProductIntegrationError("noncanonical portable draft bytes")
    try:
        with ZipFile(io.BytesIO(payload)) as pack:
            if pack.namelist() != [
                    "portable_exact.py", "__main__.py",
                    "MANIFEST.json", "README.txt"]:
                raise ProductIntegrationError("portable package contents changed")
            source = pack.read("portable_exact.py")
            cli = pack.read("__main__.py")
            manifest_raw = pack.read("MANIFEST.json")
            if (source != _portable_source()
                    or cli != _portable_cli_source()
                    or sha256(source).hexdigest() != expected_manifest["code_sha256"]
                    or sha256(cli).hexdigest() != expected_manifest["standalone_cli_sha256"]
                    or manifest_raw != json.dumps(
                        expected_manifest, sort_keys=True,
                        separators=(",", ":")).encode("ascii")):
                raise ProductIntegrationError("portable draft source or manifest mismatch")
    except (BadZipFile, KeyError, ValueError, OSError) as exc:
        raise ProductIntegrationError("invalid canonical portable draft") from exc
    manifest = json.loads(manifest_raw.decode("ascii"))
    if (manifest != expected_manifest or manifest.get("schema") != PACK_SCHEMA
            or manifest.get("version") != LOOKUP_VERSION
            or manifest.get("consumer_api_version") != LOOKUP_VERSION
            or manifest.get("code_file") != "portable_exact.py"
            or manifest.get("standalone_cli_file") != "__main__.py"
            or manifest.get("version") != "1.2.0"
            or manifest.get("standalone_command") !=
            "python -I -B <existing-verified-draft.zip>"
            or manifest.get("runtime_dependency") != "PYTHON_STANDARD_LIBRARY_ONLY"
            or manifest.get("status") !=
            "DRAFT_FIRST_PARTY_CONSUMER_NOT_APPROVED_FOR_DISTRIBUTION"
            or manifest.get("signed") is not False
            or manifest.get("source_license_signoff") is not False
            or manifest.get("owner_release_authorized") is not False
            or manifest.get("independent_qa_signed_off") is not False
            or manifest.get("upstream_public_code_included") is not False
            or manifest.get("user_project_data_included") is not False
            or manifest.get("api_keys_or_credentials_included") is not False):
        raise ProductIntegrationError("portable draft authorization boundary changed")
    return source


def _validated_handoff(handoff: dict) -> list[dict]:
    if (type(handoff) is not dict
            or handoff.get("schema") != "UCIE_P9_SOURCE_LINKED_PORTABLE_HANDOFF_V1"
            or handoff.get("status") not in (
                "SOURCE_LINKAGE_INCOMPLETE_NO_GO",
                "SOURCE_LINKED_PUBLIC_PR_METADATA_PORTABLE_PARITY_NO_GO",
                "NO_PORTABLE_PUBLIC_PR_WINDOW_NO_GO")
            or handoff.get("approved_or_exportable_items") != 0
            or handoff.get("package_released") is not False
            or handoff.get("network_requests") != 0
            or handoff.get("operating_database_writes") != 0):
        raise ProductIntegrationError("untrusted public candidate handoff for QA")
    if handoff["status"] == "SOURCE_LINKAGE_INCOMPLETE_NO_GO":
        if handoff.get("consumer_payload") is not None or handoff.get(
                "portable_candidate_items") != 0:
            raise ProductIntegrationError("incomplete W04 source cannot carry candidates")
        return []
    payload = handoff.get("consumer_payload")
    if (type(payload) is not dict or set(payload) != {"items", "queries", "limit"}
            or type(payload["items"]) is not list
            or type(payload["queries"]) is not list
            or type(payload["limit"]) is not int
            or payload["limit"] != 20
            or len(payload["items"]) != handoff.get("portable_candidate_items")
            or len(payload["items"]) > 20
            or len(payload["queries"]) > 20
            or handoff.get("in_process_exact_search_equivalent") is not bool(
                payload["items"])):
        raise ProductIntegrationError("bounded W04 portable cohort mismatch")
    rows = payload["items"]
    if any(type(row) is not dict or set(row) != FIELDS
           or row.get("human_approved") is not False
           or row.get("export_allowed") is not False for row in rows):
        raise ProductIntegrationError("unapproved W04 input cannot be upgraded")
    keys = sorted({(row["source_id"], row["domain"], row["kind"],
                    row["purpose_code"]) for row in rows})
    if payload["queries"] != [list(k) for k in keys]:
        raise ProductIntegrationError("unexpected exact W04 keys")
    if rows:
        try:
            result = search_public_metadata(rows, queries=tuple(keys), limit=20)
        except PortableLookupError as exc:
            raise ProductIntegrationError(
                "W04 candidate source provenance or rights claim rejected") from exc
        if result["approved_or_exportable_items"] != 0:
            raise ProductIntegrationError("candidate marked approved during QA")
    return rows


def check_portable_engine_qa(root: Path, *, draft_bytes: bytes | None = None,
                             public_handoff: dict | None = None) -> dict:
    """Consumer QA; injected arguments are for UCIE-owned negative tests only.

    Normal CLI reads its own W04 linked metadata and builds the deterministic
    UCIE-authored draft in memory. No permanent package is written or signed.
    """
    _root(root)
    expected_zip, manifest = build_draft_package_bytes()
    actual_zip = expected_zip if draft_bytes is None else draft_bytes
    source = _validated_draft_bytes(actual_zip, expected_zip, manifest)
    if public_handoff is None:
        public = search_existing_public_library(
            root, query="", domain=None, limit=20, group_revisions=True)
        public_handoff = _portable_public_ledger_handoff(public, limit=20)
    rows = _validated_handoff(public_handoff)
    sample = _demo_input()
    sample_key = [
        "repo:python/cpython", "Python", "PUBLIC_TECHNICAL_EVIDENCE",
        "API_CONTRACT",
    ]
    miss = sample_key[:3] + ["NO_SUCH_EXPERIENCE"]
    cohort = rows if rows else sample
    key = list((cohort[0]["source_id"], cohort[0]["domain"],
                cohort[0]["kind"], cohort[0]["purpose_code"]))
    keys = sorted({(r["source_id"], r["domain"], r["kind"],
                   r["purpose_code"]) for r in cohort})
    cases = [
        {"items": cohort, "queries": [key], "limit": 20},
        {"items": cohort, "queries": [list(k) for k in keys], "limit": 20},
        {"items": sample, "queries": [sample_key, miss], "limit": 20},
    ]
    anticipated = [search_public_metadata(
        c["items"], queries=tuple(tuple(q) for q in c["queries"]),
        limit=c["limit"]) for c in cases]
    if (anticipated[0]["strategy"] != "LINEAR_EXACT_SCAN"
            or anticipated[2]["strategy"] != "COMPOSITE_INDEX"
            or anticipated[2]["results"][1]["total_matches"] != 0):
        raise ProductIntegrationError("portable regression reference mismatch")
    encoded = json.dumps(cases, ensure_ascii=True, sort_keys=True,
                         separators=(",", ":")).encode("ascii")
    if len(encoded) > MAX_INPUT_BYTES:
        raise ProductIntegrationError("bounded QA metadata input exceeded")
    # Only the byte-identical *first party* Python source is loaded by the
    # child interpreter. No public patches, user projects or candidate scripts.
    with tempfile.TemporaryDirectory(prefix="ucie_v1_portable_qa_") as location:
        place = Path(location)
        (place / "portable_exact.py").write_bytes(source)
        try:
            run = subprocess.run(
                [sys.executable, "-I", "-B", "-c", _RUNNER, str(place)],
                input=encoded, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=30, cwd=place, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProductIntegrationError("isolated first-party consumer unavailable") from exc
        if (run.returncode != 0 or len(run.stdout) > MAX_OUTPUT_BYTES
                or len(run.stderr) > MAX_OUTPUT_BYTES):
            raise ProductIntegrationError("independent portable consumer QA failed")
        try:
            actual = json.loads(run.stdout.decode("ascii"))
        except (ValueError, UnicodeError) as exc:
            raise ProductIntegrationError("consumer did not return bounded JSON") from exc
        # A genuine executable ZIP has to run without any installed UCIE code
        # or extracted source directory. The only bytes exposed to it are the
        # canonical UCIE-authored draft and bounded unapproved metadata.
        zip_file = place / "ucie_portable_exact_DRAFT.zip"
        zip_file.write_bytes(actual_zip)
        standalone = []
        for case in cases:
            case_raw = json.dumps(
                case, ensure_ascii=True, sort_keys=True,
                separators=(",", ":")).encode("ascii")
            if len(case_raw) > MAX_INPUT_BYTES:
                raise ProductIntegrationError("standalone QA case too large")
            try:
                child = subprocess.run(
                    [sys.executable, "-I", "-B", str(zip_file)],
                    input=case_raw, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, timeout=30, cwd=place, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ProductIntegrationError(
                    "standalone ZIP consumer unavailable") from exc
            if (child.returncode != 0 or len(child.stdout) > MAX_OUTPUT_BYTES
                    or child.stderr or len(child.stdout) == 0):
                raise ProductIntegrationError(
                    "standalone ZIP consumer failed or printed diagnostics")
            try:
                standalone.append(json.loads(child.stdout.decode("ascii")))
            except (ValueError, UnicodeError) as exc:
                raise ProductIntegrationError(
                    "standalone ZIP consumer output invalid") from exc
    if (type(actual) is not list or actual != anticipated
            or any(x.get("schema") != LOOKUP_SCHEMA
                   or x.get("approved_or_exportable_items") != 0
                   or x.get("production_release_approved") is not False
                   or x.get("network_requests") != 0
                   or x.get("database_writes") != 0
                   or x.get("original_upstream_code_executed") is not False
                   for x in actual)):
        raise ProductIntegrationError("isolated consumer output diverged or authorized")
    if (len(standalone) != len(anticipated)
            or any(type(record) is not dict
                   or record.get("schema") !=
                   "UCIE_STANDALONE_DRAFT_PUBLIC_METADATA_CLI_V1"
                   or record.get("status") !=
                   "UNVERIFIED_PUBLIC_METADATA_QUERY_DRAFT_NOT_RELEASED"
                   or record.get("engine_version") != LOOKUP_VERSION
                   or record.get("result") != expected
                   or record.get("new_public_candidate_approvals") != 0
                   or record.get("owner_release_approved") is not False
                   or record.get("third_party_code_executed") is not False
                   or record.get("network_requests") != 0
                   or record.get("database_writes") != 0
                   or record.get("package_released") is not False
                   for record, expected in zip(standalone, anticipated))):
        raise ProductIntegrationError(
            "standalone executable ZIP result or approval boundary mismatch")
    return {
        "schema": SCHEMA,
        "status": "FIRST_PARTY_ISOLATED_CONSUMER_QA_PASS_NOT_RELEASED",
        "portable_engine": "UCIE_PORTABLE_EXACT_PUBLIC_METADATA",
        "engine_version": manifest["version"],
        "package_sha256": sha256(actual_zip).hexdigest(),
        "first_party_source_sha256": manifest["code_sha256"],
        "independent_python_process_executed": True,
        "standalone_zip_without_ucie_install_executed": True,
        "standalone_zip_exact_parity_cases": len(standalone),
        "standalone_zip_entrypoint": "__main__.py",
        "standalone_zip_external_qa_attested": False,
        "portable_source_exact_byte_match": True,
        "bounded_query_cases_verified": len(cases),
        "exact_result_parity_verified": True,
        "isolated_single_query_strategy": actual[0]["strategy"],
        "isolated_batch_strategy": actual[2]["strategy"],
        "zero_match_control_verified": True,
        "source_window": (
            "W04_LINKED_PUBLIC_PR_METADATA_STILL_UNVERIFIED"
            if rows else "UCIE_AUTHOR_SYNTHETIC_ONLY_NO_LIVE_SOURCE_QA"),
        "public_candidate_records_tested": len(rows),
        "public_window_truncated": bool(
            public_handoff.get("source_window_truncated", False)),
        "public_reference_unsupported_in_window":
            public_handoff.get("unsupported_reference_count", 0),
        "full_public_universe_covered": False,
        "verified_upstream_applicable_versions": 0,
        "per_revision_redistribution_rights_approved": 0,
        "independent_external_qa_attested": False,
        "owner_release_approved": False,
        "upstream_public_code_included_or_executed": False,
        "user_or_other_project_source_scanned": False,
        "temporary_first_party_module_removed_after_qa": True,
        "operating_database_writes": 0, "network_requests": 0,
        "new_signatures_created": 0, "auto_promoted": False,
        "package_released": False, "v1_accepted": False,
    }
