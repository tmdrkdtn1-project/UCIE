"""UCIE V1 single manual, read-only code review command.

One *explicit* UCIE-authored synthetic or approved-public source from stdin.
Reuses existing Python static scanners and the existing PowerShell AST scanner.
Never executes supplied source, discovers private files, auto-fixes, approves,
signs, sends network requests or modifies the UCIE miner/scheduler/DB.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys

from .existing_rule_inspection import inspect_existing_python, InspectionError
from .static_rule_bridge import _check_receipt, SOURCE_BINDINGS
from .patterns import PatternError
from .p9_pinned_public_review import lookup_pinned_review
from .library_search import search_existing_public_library, LibrarySearchError
from .public_discovery import DiscoveryError
from .source_registry import get_source, SourceRegistryError

SCHEMA = "UCIE_V1_MANUAL_CODE_REVIEW_V1"
MAX_BYTES = 16384
MAX_FINDINGS = 100
PS_DOTPATH_PR = "https://github.com/PowerShell/PowerShell/pull/28087"
PS_DOTPATH_MERGE = "373f6a7b7972a0a4b73bfd9737a0d768d28b347e"


class CodeReviewError(ValueError):
    pass


def _ucie_root(root: Path) -> Path:
    if (not isinstance(root, Path) or root.name.casefold() != "ucie"
            or not root.is_dir() or root.is_symlink()):
        raise CodeReviewError("UCIE_ROOT_INVALID")
    return root.resolve()


def _scan_powershell(root: Path, source: str, expected_sha: str) -> list[dict]:
    scanner = root / "scripts" / "ucie_powershell_static_candidates.ps1"
    wrapper = root / "scripts" / "ucie_powershell_review_stdin.ps1"
    if (scanner.is_symlink() or wrapper.is_symlink()
            or not scanner.is_file() or not wrapper.is_file()
            or scanner.parent.resolve() != root / "scripts"
            or wrapper.parent.resolve() != root / "scripts"):
        raise CodeReviewError("UCIE_SCANNER_UNAVAILABLE")
    shell = shutil.which("pwsh") or shutil.which("pwsh.exe") or shutil.which("powershell.exe")
    if shell is None:
        raise CodeReviewError("POWERSHELL_RUNTIME_UNAVAILABLE")
    # Run only a pinned, UCIE-owned wrapper. Supplied source is *data* on stdin,
    # never a PowerShell command argument or script file.
    try:
        proc = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-File", str(wrapper)],
            # Binary stdin preserves exact LF/CRLF bytes on Windows; text
            # mode would silently rewrite newlines and break SHA validation.
            input=source.encode("utf-8"), capture_output=True,
            cwd=root, timeout=25, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CodeReviewError("UCIE_POWERSHELL_SCANNER_FAILED") from exc
    if proc.returncode != 0 or len(proc.stdout) > 196608:
        raise CodeReviewError("UCIE_POWERSHELL_SCANNER_FAILED")
    try:
        # Reject duplicate JSON keys and opaque PowerShell stdout banners.
        def unique_object(pairs):
            out = {}
            for name, value in pairs:
                if name in out:
                    raise CodeReviewError("UCIE_POWERSHELL_RECEIPT_DUPLICATED")
                out[name] = value
            return out
        receipt = json.loads(proc.stdout.decode("utf-8-sig", errors="strict"),
                             object_pairs_hook=unique_object)
        if (_check_receipt(receipt) != "powershell"
                or receipt["source_sha256"] != expected_sha):
            raise CodeReviewError("UCIE_POWERSHELL_RECEIPT_INVALID")
    except (ValueError, TypeError, KeyError, PatternError) as exc:
        raise CodeReviewError("UCIE_POWERSHELL_RECEIPT_INVALID") from exc
    return [{
        "rule_id": row["pattern_code"],
        "line": row["line"],
        "column": row["column"],
        "guidance": row["safe_fix_guidance"],
        "public_evidence": row["public_evidence"],
        "authorization": "UNVERIFIED_STATIC_CANDIDATE_ONLY",
    } for row in receipt["findings"]]


def _version_evidence(rule_id: str, source_url: str) -> dict | None:
    if rule_id != "PS_RESOLVE_PATH_DOT_PREFIX" or source_url != PS_DOTPATH_PR:
        return None
    # Exact approved-public PR and original merge SHA: no generalization to
    # untested PowerShell versions or to the user's supplied code.
    pinned = lookup_pinned_review(
        source_id="repo:PowerShell/PowerShell",
        public_url=source_url, merge_sha=PS_DOTPATH_MERGE)
    if pinned is None:
        raise CodeReviewError("UCIE_PINNED_VERSION_EVIDENCE_UNAVAILABLE")
    windows = pinned["official_windows_release_runtime_observation"]
    linux = pinned["official_release_runtime_observation"]
    if (windows is None or linux is None
            or windows["runtime_version"] != "7.6.6"
            or linux["runtime_version"] != "7.6.6"
            or not windows["actual_release_binary_executed"]
            or not linux["actual_release_binary_executed"]
            or windows["dot_prefix_cases_matching_expected"] != 0
            or linux["dot_prefix_cases_matching_expected"] != 0
            or windows["production_approved"] is not False
            or linux["production_approved"] is not False):
        raise CodeReviewError("UCIE_PINNED_VERSION_EVIDENCE_UNVERIFIED")
    return {
        "tested_release": "PowerShell 7.6.6",
        "tested_platforms": ["windows-x64", "linux-x64"],
        "public_release_behavior": "DOT_PREFIX_BUG_REPRODUCED_IN_UCIE_SYNTHETIC_CASES",
        "windows_ci_job_url": windows["ci_job_url"],
        "linux_ci_job_url": linux["ci_job_url"],
        "same_bug_confirmed_in_supplied_source": False,
        "other_versions_checked": False,
        "fix_available_in_unknown_versions": None,
        "production_approved": False,
    }


_PUBLIC_PR = re.compile(
    r"https://github[.]com/(python/cpython|PowerShell/PowerShell|git/git|"
    r"modelcontextprotocol/python-sdk|actions/runner-images)/pull/([1-9][0-9]*)\Z"
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")


MAX_RELATED_PUBLIC = 3


def _related_public_comparison(*, source_id: str, exact_url: str,
                               linked: list[dict], rows: list[dict],
                               source_window_omitted: int) -> dict:
    """Compare only candidate metadata with same approved source/kind/purpose.

    These are nearby review leads, NOT equivalently validated fixes. Uses
    the already loaded W04 source window; no new DB read or HTTP request.
    """
    keys = {(item["source_candidate_kind"], item["purpose_code"])
            for item in linked}
    related = {}
    if keys:
        for row in rows:
            if (row["public_url"] == exact_url
                    or (row["kind"], row["purpose_code"]) not in keys):
                continue
            if type(row["public_url"]) is not str:
                raise CodeReviewError("RELATED_PUBLIC_SOURCE_REFERENCE_INVALID")
            match = _PUBLIC_PR.fullmatch(row["public_url"])
            if match is None:
                # A git/git commit can be a legitimate W04 record, but this
                # comparison has an exact public PR-only contract.
                if (source_id == "repo:git/git"
                        and type(row["public_url"]) is str
                        and re.fullmatch(
                            r"https://github[.]com/git/git/commit/[a-f0-9]{40}",
                            row["public_url"])):
                    continue
                raise CodeReviewError("RELATED_PUBLIC_SOURCE_REFERENCE_INVALID")
            if "repo:" + match.group(1) != source_id:
                raise CodeReviewError("RELATED_PUBLIC_SOURCE_REFERENCE_INVALID")
            # One candidate per *other PR*, even if W04 has multiple
            # revisions or purpose-linked entries for that PR.
            candidate = {
                "public_url": row["public_url"],
                "library_item_id": row["library_item_id"],
                "evidence_sha256": row["evidence_sha256"],
                "revision_hint": row["revision_hint"],
                "kind": row["kind"], "purpose_code": row["purpose_code"],
                "match_basis": "SAME_APPROVED_SOURCE_KIND_AND_PURPOSE_ONLY",
                "rule_fix_equivalence_verified": False,
                "version_applicability_verified": False,
                "rights_for_export_verified": False,
                "human_approved": False, "export_allowed": False,
            }
            url = row["public_url"]
            if (url not in related or
                    (candidate["library_item_id"], candidate["evidence_sha256"])
                    < (related[url]["library_item_id"],
                       related[url]["evidence_sha256"])):
                related[url] = candidate
    ordered = [related[url] for url in sorted(related)]
    return {
        "status": ("NO_EXACT_ANCHOR_NO_COMPARISON" if not keys
                   else "RELATED_PUBLIC_CANDIDATES_UNVERIFIED" if ordered
                   else "NO_RELATED_PUBLIC_PR_IN_BOUNDED_WINDOW"),
        "related_candidate_count_in_loaded_window": len(ordered),
        "items": ordered[:MAX_RELATED_PUBLIC],
        "limit": MAX_RELATED_PUBLIC,
        "source_window_truncated": source_window_omitted > 0,
        "comparison_truncated": (source_window_omitted > 0
                                 or len(ordered) > MAX_RELATED_PUBLIC),
        "full_source_coverage_verified": False,
        "fix_equivalence_verified": False,
        "approved_or_exportable": False,
    }


def _linked_library_for_finding(root: Path, public_url: str) -> dict:
    """Match exact public PR identity using existing W04 source-linked readers.

    A public PR match is NOT an assertion that the static rule, runtime
    applicability, signed status, license or production fix has been approved.
    """
    found = _PUBLIC_PR.fullmatch(public_url)
    if found is None:
        raise CodeReviewError("UNAPPROVED_PUBLIC_EVIDENCE_REFERENCE")
    source_id = "repo:" + found.group(1)
    runtime = root / "runtime"
    if runtime.is_symlink() or (runtime.exists() and not runtime.is_dir()):
        raise CodeReviewError("PUBLIC_RUNTIME_DIR_UNSAFE")
    # A clean checkout is valid input for manual code review. Missing UCIE
    # runtime is a transparent NO_GO, not an integrity error or a reason to
    # create a ledger/directories during read-only inspection.
    if not runtime.is_dir():
        return {
            "status": "PUBLIC_SOURCE_LEDGER_INCOMPLETE_NO_GO",
            "exact_public_pr_url": public_url,
            "matched_public_evidence_count": 0,
            "source_linkage_checked": False,
            "items": [], "truncated": False,
            "rule_verification": False,
            "approved_or_exportable": False,
            "related_public_evidence": _related_public_comparison(
                source_id=source_id, exact_url=public_url,
                linked=[], rows=[], source_window_omitted=0),
        }
    try:
        source = get_source(source_id)
        if (source["status"] != "ACTIVE_APPROVED"
                or source["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY"):
            raise CodeReviewError("PUBLIC_SOURCE_NOT_ACTIVE")
        # The W04 index searches source reference text, not necessarily its
        # normalized public_url. Use a bounded SOURCE window and compare
        # returned canonical PR URLs *exactly*; do not claim full coverage
        # when W04 omits rows beyond the bounded window.
        result = search_existing_public_library(
            root, query="", source_id=source_id,
            limit=20, group_revisions=True)
    except (LibrarySearchError, DiscoveryError, SourceRegistryError,
            OSError, ValueError, KeyError) as exc:
        raise CodeReviewError("PUBLIC_LIBRARY_INTEGRITY_CHECK_FAILED") from exc
    status = result["status"]
    if status == "SOURCE_LINKAGE_INCOMPLETE_NO_GO":
        if result["returned_count"] != 0 or result["items"]:
            raise CodeReviewError("PUBLIC_LIBRARY_INCOMPLETE_RESULT_INVALID")
        return {
            "status": "PUBLIC_SOURCE_LEDGER_INCOMPLETE_NO_GO",
            "exact_public_pr_url": public_url,
            "matched_public_evidence_count": 0,
            "source_linkage_checked": False,
            "items": [], "truncated": False,
            "rule_verification": False,
            "approved_or_exportable": False,
            "related_public_evidence": _related_public_comparison(
                source_id=source_id, exact_url=public_url,
                linked=[], rows=[], source_window_omitted=0),
        }
    if (status != "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO"
            or result["approved_or_exportable_items"] != 0
            or result["operating_database_writes"] != 0
            or result["network_requests"] != 0
            or type(result["returned_count"]) is not int
            or type(result["total_matches"]) is not int
            or result["returned_count"] != len(result["items"])
            or result["total_matches"] < result["returned_count"]
            or type(result["omitted_count"]) is not int
            or result["omitted_count"] != (result["total_matches"]-
                                           result["returned_count"])):
        raise CodeReviewError("PUBLIC_LIBRARY_READ_RECEIPT_INVALID")
    linked = []
    for row in result["items"]:
        if (row["source_id"] != source_id
                or row["lifecycle"] != "UNVERIFIED_CANDIDATE_ONLY"
                or row["signature_status"] != "NOT_ATTESTED_BY_THIS_SEARCH"
                or row["human_approved"] is not False
                or row["export_allowed"] is not False
                or not _SHA256.fullmatch(row["library_item_id"])
                or not _SHA256.fullmatch(row["evidence_sha256"])
                or not _SHA40.fullmatch(row["revision_hint"])):
            raise CodeReviewError("PUBLIC_LIBRARY_SOURCE_ROW_INVALID")
        if row["public_url"] != public_url:
            # Other *approved-public* PRs on the same source are not evidence
            # for the user's finding. Ignore their records after validation.
            continue
        linked.append({
            "library_item_id": row["library_item_id"],
            "source_id": source_id,
            "public_url": public_url,
            "evidence_sha256": row["evidence_sha256"],
            "source_revision_hint": row["revision_hint"],
            "purpose_code": row["purpose_code"],
            "source_candidate_kind": row["kind"],
            "rule_fix_independently_verified": False,
            "source_version_applicability_verified": False,
            "rights_for_export_verified": False,
            "human_approved": False,
            "export_allowed": False,
        })
    return {
        "status": ("EXACT_PUBLIC_PR_SOURCE_LINKED_UNVERIFIED" if linked
                   else "NO_EXACT_PUBLIC_PR_IN_BOUNDED_SOURCE_WINDOW"
                   if result["omitted_count"] else
                   "NO_EXACT_PUBLIC_PR_IN_CURRENT_LINKED_LEDGER"),
        "exact_public_pr_url": public_url,
        "matched_public_evidence_count": len(linked),
        "total_public_source_records_in_window": result["total_matches"],
        "source_linkage_checked": True,
        "items": linked,
        "truncated": result["omitted_count"] > 0,
        "rule_verification": False,
        "approved_or_exportable": False,
        "related_public_evidence": _related_public_comparison(
            source_id=source_id, exact_url=public_url, linked=linked,
            rows=result["items"], source_window_omitted=result["omitted_count"]),
    }


def review_code(source: str, *, language: str, root: Path) -> dict:
    """Return practical findings by reusing existing scanners, no new rules."""
    base = _ucie_root(root)
    if language not in ("python", "powershell") or type(language) is not str:
        raise CodeReviewError("LANGUAGE_UNSUPPORTED")
    if type(source) is not str:
        raise CodeReviewError("SOURCE_MUST_BE_UTF8_TEXT")
    try:
        raw = source.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise CodeReviewError("SOURCE_ENCODING_INVALID") from exc
    if not 0 < len(raw) <= MAX_BYTES:
        raise CodeReviewError("SOURCE_SIZE_INVALID")
    digest = sha256(raw).hexdigest()
    if language == "python":
        # Existing four scanners and their original validity/approval gates.
        try:
            original = inspect_existing_python(source, root=base)
        except (InspectionError, ValueError, SyntaxError) as exc:
            raise CodeReviewError("PYTHON_SOURCE_OR_SCANNER_REJECTED") from exc
        if (original["source_sha256"] != digest
                or original["source_executed"] is not False
                or original["source_files_read"] != 0
                or original["database_writes"] != 0
                or original["existing_signed_manual_matches"] != 0):
            raise CodeReviewError("PYTHON_SCAN_TRUST_BOUNDARY_FAILED")
        matches = original["findings"]
    else:
        matches = _scan_powershell(base, source, digest)
    if len(matches) > MAX_FINDINGS:
        raise CodeReviewError("FINDINGS_LIMIT_EXCEEDED")
    findings = []
    for finding in matches:
        rule_id = finding["rule_id"]
        if (rule_id not in SOURCE_BINDINGS
                and language == "powershell"):
            raise CodeReviewError("UNRECOGNIZED_POWERSHELL_RULE")
        if (finding["authorization"] != "UNVERIFIED_STATIC_CANDIDATE_ONLY"
                or type(finding["line"]) is not int
                or type(finding["column"]) is not int
                or finding["line"] < 1 or finding["column"] < 0
                or type(finding["guidance"]) is not str
                or not finding["guidance"]
                or type(finding["public_evidence"]) is not str
                or not finding["public_evidence"].startswith(
                    "https://github.com/")):
            raise CodeReviewError("INVALID_REVIEW_FINDING")
        findings.append({
            "rule_id": rule_id,
            "line": finding["line"],
            "column": finding["column"],
            "safe_fix_guidance": finding["guidance"],
            "public_evidence": finding["public_evidence"],
            "version_evidence": _version_evidence(
                rule_id, finding["public_evidence"]),
            "confidence": "STATIC_HEURISTIC_REVIEW_REQUIRED",
            "authorization": "UNVERIFIED_STATIC_CANDIDATE_ONLY",
            "manual_review_required": True,
            "source_runtime_bug_confirmed": False,
            "auto_fix_applied": False,
        })
    findings.sort(key=lambda row: (row["line"], row["column"], row["rule_id"]))
    # One read-only W04 lookup per distinct approved public PR, not per line.
    # Empty or missing ledgers are explicitly NO_GO, never silent PASS.
    library_cache = {}
    for item in findings:
        url = item["public_evidence"]
        if url not in library_cache:
            library_cache[url] = _linked_library_for_finding(base, url)
        item["public_library"] = library_cache[url]
    return {
        "schema": SCHEMA,
        "status": ("REVIEW_FINDINGS_UNVERIFIED" if findings
                   else "NO_KNOWN_PATTERN_NOT_SAFETY_PASS"),
        "language": language,
        "source_sha256": digest,
        "findings": findings,
        "finding_count": len(findings),
        "public_library_exact_pr_lookups": len(library_cache),
        "public_library_linked_findings": sum(
            item["public_library"]["status"] ==
            "EXACT_PUBLIC_PR_SOURCE_LINKED_UNVERIFIED" for item in findings),
        "public_library_no_approval_inferred": True,
        "related_public_pr_candidates_in_loaded_windows": sum(
            len(value.get("related_public_evidence", {}).get("items", ()))
            for value in library_cache.values()),
        "related_public_evidence_not_fix_equivalence": True,
        "approved_reusable_artifacts_from_this_lookup": 0,
        "covered_scanners": (
            "EXISTING_FOUR_PYTHON_STATIC_SCANNERS" if language == "python"
            else "EXISTING_POWERSHELL_AST_STATIC_SCANNER"),
        "manual_review_required": bool(findings),
        "full_code_safety_verified": False,
        "source_executed": False,
        "source_files_read": 0,
        "network_requests": 0,
        "database_writes": 0,
        "auto_applied": False,
        "auto_promoted": False,
        "production_approved": False,
        "v1_accepted": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="One UCIE-owned synthetic/approved-public code review from stdin")
    parser.add_argument("--ucie-root", type=Path, required=True)
    parser.add_argument("--language", choices=("python", "powershell"),
                        required=True)
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES+1)
        if not 0 < len(raw) <= MAX_BYTES:
            raise CodeReviewError("SOURCE_SIZE_INVALID")
        # Windows PowerShell 5.1 native pipelines may prefix UTF-8 BOM.
        # Parse without the transport prefix, but never claim that the
        # parsed-source digest identifies the raw stdin bytes.
        bom = raw.startswith(b"\xef\xbb\xbf")
        source = raw.decode("utf-8-sig" if bom else "utf-8",
                            errors="strict")
        result = review_code(source, language=args.language,
                             root=args.ucie_root)
        if bom:
            parsed_digest = sha256(source.encode("utf-8")).hexdigest()
            if result["source_sha256"] != parsed_digest:
                raise CodeReviewError("SOURCE_PARSE_DIGEST_MISMATCH")
            result["parsed_source_sha256"] = parsed_digest
            result["source_sha256"] = sha256(raw).hexdigest()
        result["source_byte_encoding"] = ("UTF8_BOM_PARSED_WITH_RAW_HASH"
                                          if bom else "UTF8_NO_BOM")
    except (CodeReviewError, UnicodeError) as exc:
        result = {
            "schema": SCHEMA,
            "status": "CODE_REVIEW_FAIL_CLOSED",
            "reason_code": (str(exc) if type(exc) is CodeReviewError
                            else "SOURCE_ENCODING_INVALID"),
            "source_executed": False, "network_requests": 0,
            "database_writes": 0, "auto_promoted": False,
            "production_approved": False, "v1_accepted": False,
        }
    print(json.dumps(result, sort_keys=True))
    return 2 if result["status"] == "CODE_REVIEW_FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
