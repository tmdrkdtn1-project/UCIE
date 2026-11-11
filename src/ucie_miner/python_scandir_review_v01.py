"""UCIE B1/B2 Python case: official source -> LibraryEntry -> safe first-party trial.

Only the PREVIOUSLY approved official Python os.scandir documentation URL is
referenced; it is NOT downloaded, parsed as instructions, or claimed to be a
version-pinned evidence snapshot. Only UCIE-authored disposable files are
opened. The trial exercises GuardedScandir, not an unsafe upstream race.
No user-supplied path, source URL, application data, project file or approval.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from threading import Barrier

from .guarded_scandir import GuardedScandir
from .library_entry import build_library_entry
from .public_evidence_routes import DOC_ENDPOINTS
from .source_registry import get_source

SCHEMA = "UCIE_B1B2_PYTHON_SCANDIR_REVIEW_V01"
SOURCE_ID = "doc:python/cpython"
PURPOSE = "SCANDIR_SERIALIZED_ITERATION"
FILE_NAMES = ("alpha.txt", "beta.txt", "gamma.txt", "delta.txt")
MAX_RESULTS = len(FILE_NAMES)


class PythonScandirReviewError(ValueError):
    """A public-source or synthetic-test gate failed; no approval allowed."""


def _source_bound_entry() -> tuple[dict, dict]:
    source = get_source(SOURCE_ID)
    official = DOC_ENDPOINTS["python/cpython"][0]
    if (source.get("status") != "ACTIVE_APPROVED"
            or source.get("source_kind") != "OFFICIAL_PUBLIC_DOCUMENT"
            or source.get("public_url") != official
            or official != "https://docs.python.org/3/library/os.html"
            or source.get("license_verdict") != "NOT_ATTESTED_PER_REVISION"
            or source.get("fetch_authorized_by_this_registry") is not False):
        raise PythonScandirReviewError("UCIE_OFFICIAL_SOURCE_CONTRACT_CHANGED")
    # This fingerprints UCIE's stable reference string, NOT remote HTML.
    # In particular, it is NOT proof the documentation revision is pinned.
    reference_digest = sha256(
        ("UCIE_DOC_REFERENCE_ONLY_V01\x1f" + official).encode("ascii")
    ).hexdigest()
    entry = build_library_entry({
        "kind": "TEST_RECIPE",
        "source_id": SOURCE_ID,
        "evidence_reference": official,
        "evidence_sha256": reference_digest,
        "purpose_code": PURPOSE,
        "version_scope": "UNDETERMINED",
        "dependencies": ["python-stdlib"],
    })
    if (entry.get("entry_status") != "UNVERIFIED_CANDIDATE_ONLY"
            or entry.get("approval_status") != "NOT_APPROVED"
            or entry.get("version_applicability_verified") is not False
            or entry.get("human_approved") is not False
            or entry.get("export_allowed") is not False
            or entry.get("auto_promoted") is not False
            or entry.get("revision_hint") != "PUBLIC_DOCUMENT_REVISION_NOT_PINNED"
            or entry.get("public_url") != official):
        raise PythonScandirReviewError("UCIE_LIBRARY_ENTRY_APPROVAL_BOUNDARY_CHANGED")
    return source, entry


def _evaluate_only_ucie_synthetic_inputs() -> dict:
    # Neither the caller nor public material can select any filesystem path.
    with tempfile.TemporaryDirectory(prefix="ucie-scandir-owned-v01-") as temp:
        root = Path(temp)
        for name in FILE_NAMES:
            (root / name).write_text("UCIE FIRST-PARTY SYNTHETIC\n",
                                     encoding="ascii")
        expected = tuple(sorted(FILE_NAMES))
        with GuardedScandir(root) as shared:
            rendezvous = Barrier(2)

            def consume() -> tuple[str, ...]:
                rendezvous.wait(timeout=6)
                seen = []
                while True:
                    try:
                        item = next(shared)
                    except StopIteration:
                        break
                    if item.name not in FILE_NAMES:
                        raise PythonScandirReviewError("UNKNOWN_SYNTHETIC_ENTRY")
                    seen.append(item.name)
                    if len(seen) > MAX_RESULTS:
                        raise PythonScandirReviewError("SCANDIR_RESULT_OVERFLOW")
                return tuple(seen)

            with ThreadPoolExecutor(max_workers=2,
                                    thread_name_prefix="ucie-scandir") as pool:
                futures = (pool.submit(consume), pool.submit(consume))
                found = futures[0].result(timeout=8) + futures[1].result(timeout=8)
            if tuple(sorted(found)) != expected or len(set(found)) != MAX_RESULTS:
                raise PythonScandirReviewError("SCANDIR_GUARDED_ENUMERATION_MISMATCH")
            shared.close()  # Idempotent close is an explicit contract.
            try:
                next(shared)
            except StopIteration:
                after_close_stops = True
            else:
                raise PythonScandirReviewError("SCANDIR_AFTER_CLOSE_MUST_STOP")

        # A second safe, sequential UCIE-owned control detects omissions.
        with GuardedScandir(root) as reader:
            control = tuple(sorted(entry.name for entry in reader))
        if control != expected or not after_close_stops:
            raise PythonScandirReviewError("SCANDIR_FIRST_PARTY_CONTROL_MISMATCH")
    return {
        "synthetic_file_count": MAX_RESULTS,
        "concurrent_guarded_consumers": 2,
        "unique_entries_match": True,
        "sequential_control_match": True,
        "closed_iterator_stops": True,
        "temporary_synthetic_files_removed": True,
        "unsafe_raw_iterator_race_executed": False,
        "external_repository_source_executed": False,
        "customer_or_other_project_files_opened": False,
    }


def run_python_scandir_review() -> dict:
    """An actual user-facing UCIE experiment, strictly review-only."""
    source, entry = _source_bound_entry()
    experiment = _evaluate_only_ucie_synthetic_inputs()
    return {
        "schema": SCHEMA,
        "status": "UCIE_OWNED_SYNTHETIC_SCANDIR_TRIAL_PASS_NOT_APPROVED",
        "source_id": SOURCE_ID,
        "official_document_url": source["public_url"],
        "documentation_revision_status": "PUBLIC_DOCUMENT_REVISION_NOT_PINNED",
        "source_license_status": source["license_verdict"],
        "library_item_id": entry["library_item_id"],
        "library_kind": entry["kind"],
        "purpose_code": entry["purpose_code"],
        "domain": entry["domain"],
        "skill_profile": entry["skill_profile"],
        "version_scope": entry["version_scope_claim"],
        "version_applicability_verified": False,
        "evidence_fingerprint_scope": "UCIE_REFERENCE_STRING_ONLY_NOT_DOCUMENT_BYTES",
        "safe_call": "Serialize next() and close() through a single lock; close the iterator.",
        "review_limitation": "Does not certify CPython releases, upstream race fixes, or customer use.",
        "synthetic_trial": experiment,
        "candidate_status": "UNVERIFIED_CANDIDATE_ONLY",
        "human_approved": False,
        "export_allowed": False,
        "auto_promoted": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "scheduler_changes": 0,
        "source_executed": False,
        "customer_release_authorized": False,
    }


def main() -> int:
    try:
        data = run_python_scandir_review()
    except (PythonScandirReviewError, OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "UCIE_PYTHON_SCANDIR_REVIEW_FAIL_CLOSED",
            "error_type": type(exc).__name__, "auto_promoted": False,
            "operating_database_writes": 0, "customer_release_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(data, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
