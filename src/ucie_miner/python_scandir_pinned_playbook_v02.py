"""UCIE B1/B2: pinned CPython 3.15 documentation plus selectable safe patterns.

All metadata is fixed from the approved python/cpython v3.15.0 public tag
review. It is NOT a new fetch authority, a license clearance, or proof of an
upstream race fix. Only UCIE-authored example functions are returned as text;
no user path or source code is ever read or executed by this module.
"""
from __future__ import annotations

from .python_scandir_review_v01 import _source_bound_entry

SCHEMA = "UCIE_PYTHON_SCANDIR_PINNED_PLAYBOOK_V02"
STATUS = "OFFICIAL_TAGGED_DOC_AND_UCIE_PATTERN_REVIEW_ONLY"
DOC_URL = "https://docs.python.org/3/library/os.html"
TAG = "v3.15.0"
TAG_COMMIT = "d220409a13b77de7a6c30abe16ea90db01528edc"
DOC_BLOB = "74419ee7f3588f1baec83c85b05716e6388719e3"
LICENSE_BLOB = "20cf39097c68baa17cc566b64e76d34ebf034044"
PINNED_DOC_URL = "https://github.com/python/cpython/blob/v3.15.0/Doc/library/os.rst"
PINNED_LICENSE_URL = "https://github.com/python/cpython/blob/v3.15.0/LICENSE"
CASE_IDS = ("single_owner", "shared_guarded")

_SINGLE = '''import os

def list_directory_names(directory: str) -> list[str]:
    """Only iterate a directory the caller has explicitly selected."""
    with os.scandir(directory) as entries:
        return [entry.name for entry in entries]
'''

_SHARED = '''import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

def list_directory_names_threaded(directory: str) -> list[str]:
    """Keep all workers joined before closing one shared iterator."""
    guard = Lock()
    with os.scandir(directory) as entries:
        def consume() -> list[str]:
            names = []
            while True:
                with guard:
                    item = next(entries, None)
                if item is None:
                    return names
                names.append(item.name)
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(consume) for _ in range(2)]
            return sorted(name for job in jobs for name in job.result())
'''

CASES = {
    "single_owner": {
        "title": "단일 소비자 · with 자동 종료",
        "purpose": "하나의 실행 흐름이 디렉터리 항목을 처리할 때 반복자 종료를 명확히 관리합니다.",
        "safe_example": _SINGLE,
        "avoid": "반복자를 오래 유지하면서 명시적 종료나 with 블록을 생략하지 마세요.",
        "evidence_scope": "CPYTHON_V315_DOC_CONTEXT_MANAGER_AND_EXPLICIT_CLOSE",
    },
    "shared_guarded": {
        "title": "2개 소비자 · 단일 잠금 보호",
        "purpose": "동일 반복자를 여러 스레드가 사용하는 경우 next()를 단일 잠금으로 보호하고 종료 전에 작업자를 합류시킵니다.",
        "safe_example": _SHARED,
        "avoid": "같은 반복자를 서로 다른 잠금 없이 두 스레드가 소비하거나 다른 스레드가 먼저 닫지 않도록 합니다.",
        "evidence_scope": "UCIE_AUTHORED_SYNTHETIC_GUARDED_CONCURRENCY_NOT_UPSTREAM_CERTIFICATION",
    },
}


class PythonPinnedPlaybookError(ValueError):
    """An unrecognized case or source/rights/identity drift must fail closed."""


def _pinned_source() -> dict:
    source, entry = _source_bound_entry()
    if (source.get("source_id") != "doc:python/cpython"
            or source.get("status") != "ACTIVE_APPROVED"
            or source.get("public_url") != DOC_URL
            or source.get("license_verdict") != "NOT_ATTESTED_PER_REVISION"
            or source.get("fetch_authorized_by_this_registry") is not False
            or entry.get("kind") != "TEST_RECIPE"
            or entry.get("revision_hint") != "PUBLIC_DOCUMENT_REVISION_NOT_PINNED"
            or entry.get("human_approved") is not False
            or entry.get("export_allowed") is not False
            or entry.get("auto_promoted") is not False):
        raise PythonPinnedPlaybookError("official Python source contract drift")
    return {
        "source_id": "doc:python/cpython",
        "live_doc_url": DOC_URL,
        "live_doc_revision_pinned": False,
        "source_tag": TAG,
        "tag_commit_sha1": TAG_COMMIT,
        "tagged_doc_url": PINNED_DOC_URL,
        "doc_blob_sha1": DOC_BLOB,
        "tagged_license_url": PINNED_LICENSE_URL,
        "license_blob_sha1": LICENSE_BLOB,
        "tagged_doc_reference_observed": True,
        "context_manager_and_close_documented_at_tag": True,
        "context_manager_since_doc_version": "3.6",
        "documentation_tag_is_first_fixed_race_release": False,
        "upstream_race_behavior_independently_reproduced": False,
        "documentation_license_text_observed": (
            "PYTHON_SOFTWARE_FOUNDATION_LICENSE_VERSION_2"
        ),
        "documentation_examples_license_text_observed": (
            "PSF_LICENSE_VERSION_2_AND_ZERO_CLAUSE_BSD"
        ),
        "per_revision_redistribution_clearance": False,
        "owner_licensing_signoff": False,
        "source_code_copied_from_cpython": False,
        "new_fetch_authority": False,
    }


def pinned_source_snapshot() -> dict:
    """Fixed public source metadata, never a network read or rights grant."""
    return dict(_pinned_source())


def review_case(case: str) -> dict:
    """One fixed illustrative workflow, not an executor for caller paths."""
    if type(case) is not str or case not in CASE_IDS:
        raise PythonPinnedPlaybookError("unregistered Python safe-use case")
    source = _pinned_source()
    item = CASES[case]
    if (tuple(CASES) != CASE_IDS
            or not item["safe_example"].startswith("import os\n")
            or len(item["safe_example"]) > 1800):
        raise PythonPinnedPlaybookError("unexpected UCIE-owned code example")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "case_id": case,
        "allowed_case_ids": list(CASE_IDS),
        "case_title": item["title"],
        "purpose": item["purpose"],
        "safe_example": item["safe_example"],
        "avoid_as_text_only": item["avoid"],
        "evidence_scope": item["evidence_scope"],
        "source_evidence": source,
        "example_authorship": "UCIE_FIRST_PARTY_NOT_CPYTHON_COPY",
        "example_executed_by_view": False,
        "arbitrary_paths_accepted": False,
        "customer_files_read": False,
        "trial_uses_existing_bounded_ucie_synthetic_only": True,
        "selected_case_changes_underlying_trial": False,
        "upstream_code_executed": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "human_approved": False,
        "export_allowed": False,
        "auto_promoted": False,
        "customer_release_authorized": False,
    }
