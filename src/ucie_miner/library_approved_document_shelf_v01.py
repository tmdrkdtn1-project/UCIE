"""W03/W04: four additional approved official-document pointers, not fixes.

In-memory catalog derived ONLY from the five W01-approved public sources.
The Python os.scandir TEST_RECIPE remains an independent existing shelf.
No crawler, generic import, indexed database, source code, or auto-approval.
"""
from __future__ import annotations

from hashlib import sha256
import re

from .library_entry import build_library_entry
from .library_search import SCHEMA as W04_SCHEMA
from .product_plan import APPROVED_REPOSITORIES
from .public_evidence_routes import DOC_ENDPOINTS
from .source_registry import get_source

SCHEMA = "UCIE_W03_W04_APPROVED_OFFICIAL_DOC_SHELF_V01"
STATUS = "APPROVED_SOURCE_UNVERIFIED_DOCUMENT_REFERENCES"
NONE = "NO_OFFICIAL_DOCUMENT_REFERENCES_MATCH"
PR_PAGE = "SAME_APPROVED_SOURCE_PUBLIC_PR_PAGE_NOT_SAME_FIX"
INCOMPLETE = "PUBLIC_PR_SOURCE_LINKAGE_INCOMPLETE_NO_COMPARISON"
UNREQUESTED = "NO_PUBLIC_PR_COMPARISON_REQUESTED"
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
QUERY = re.compile(r"[\w .-]{0,80}\Z", re.UNICODE)

# Five W01 repo/doc pairs are already approved, but only the Python pointer
# has a UCIE-owned runnable TEST_RECIPE. Other entries are metadata pointers.
# Exact URLs are independently pinned to detect W01 registry/source drift.
REFERENCES = (
    ("PowerShell/PowerShell",
     "https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/resolve-path?view=powershell-7.6",
     "PowerShell Resolve-Path · 공식 문서 참조",
     "POWERSHELL_RESOLVE_PATH_DOC_REFERENCE",
     ("powershell", "resolve-path", "경로", "파워셸")),
    ("git/git", "https://git-scm.com/docs/git",
     "Git 명령과 버전 관리 · 공식 문서 참조",
     "GIT_GENERAL_DOC_REFERENCE",
     ("git", "version control", "버전", "명령")),
    ("modelcontextprotocol/python-sdk",
     "https://modelcontextprotocol.io/specification/2025-11-25",
     "MCP 프로토콜 사양 · 공식 문서 참조",
     "MCP_SPECIFICATION_DOC_REFERENCE",
     ("mcp", "protocol", "api", "프로토콜", "사양")),
    ("actions/runner-images",
     "https://docs.github.com/en/actions/reference/runners",
     "GitHub Actions 러너 · 공식 문서 참조",
     "ACTIONS_RUNNER_DOC_REFERENCE",
     ("runner", "actions", "windows", "ci", "러너", "실행 환경")),
)
SHA_PREFIX = "UCIE_OFFICIAL_DOC_URL_REFERENCE_ONLY_V01\x1f"


class ApprovedDocumentShelfError(ValueError):
    """Unknown or forged official source reference: fail closed."""


def approved_source_filter(source: str) -> str:
    """Validate a URI-query exact repo identity. Empty = all approved."""
    if type(source) is not str or len(source) > 80:
        raise ApprovedDocumentShelfError("invalid bounded source selector")
    if source and source not in APPROVED_REPOSITORIES:
        raise ApprovedDocumentShelfError("public source is not approved")
    if source:
        item = get_source("repo:" + source)
        if (item.get("status") != "ACTIVE_APPROVED"
                or item.get("source_kind") != "INDEPENDENT_PUBLIC_REPOSITORY"
                or item.get("fetch_authorized_by_this_registry") is not False):
            raise ApprovedDocumentShelfError("W01 source selector drift")
    return source


def _check_source_contract() -> None:
    if (len(APPROVED_REPOSITORIES) != 5
            or set(DOC_ENDPOINTS) != set(APPROVED_REPOSITORIES)
            or {x[0] for x in REFERENCES} != set(APPROVED_REPOSITORIES) - {
                "python/cpython"}):
        raise ApprovedDocumentShelfError("UCIE W01 official scope changed")
    for repo, url, _title, _purpose, _terms in REFERENCES:
        if DOC_ENDPOINTS[repo][0] != url:
            raise ApprovedDocumentShelfError("official reference URL changed")


def _matches(query: str, terms: tuple[str, ...]) -> bool:
    needle = query.casefold().strip()
    return not needle or (len(needle) >= 2 and any(
        needle in term.casefold() or term.casefold() in needle
        for term in terms
    ))


def search_approved_document_references(query: str,
                                        *, source: str = "") -> dict:
    """Four W01/W02 public reference entries; zero IO and no trial execution."""
    if type(query) is not str or QUERY.fullmatch(query) is None:
        raise ApprovedDocumentShelfError("invalid bounded catalog query")
    source = approved_source_filter(source)
    _check_source_contract()
    items = []
    for repo, url, title, purpose, terms in REFERENCES:
        if (source and source != repo) or not _matches(query, terms):
            continue
        approved = get_source("doc:" + repo)
        if (approved.get("status") != "ACTIVE_APPROVED"
                or approved.get("source_kind") != "OFFICIAL_PUBLIC_DOCUMENT"
                or approved.get("public_url") != url
                or approved.get("related_approved_repo") != repo
                or approved.get("fetch_authorized_by_this_registry") is not False
                or approved.get("license_verdict") != "NOT_ATTESTED_PER_REVISION"):
            raise ApprovedDocumentShelfError("W01 official doc permission drift")
        digest = sha256((SHA_PREFIX + url).encode("ascii")).hexdigest()
        w02 = build_library_entry({
            "kind": "PUBLIC_TECHNICAL_EVIDENCE",
            "source_id": "doc:" + repo,
            "evidence_reference": url,
            "evidence_sha256": digest,
            "purpose_code": purpose,
            "version_scope": "UNDETERMINED",
            "dependencies": [],
        })
        if (w02.get("source_id") != "doc:" + repo
                or w02.get("public_url") != url
                or w02.get("kind") != "PUBLIC_TECHNICAL_EVIDENCE"
                or w02.get("entry_status") != "UNVERIFIED_CANDIDATE_ONLY"
                or w02.get("approval_status") != "NOT_APPROVED"
                or w02.get("revision_hint") != "PUBLIC_DOCUMENT_REVISION_NOT_PINNED"
                or w02.get("source_license_status") != "NOT_ATTESTED_PER_REVISION"
                or w02.get("version_scope_claim") != "UNDETERMINED"
                or w02.get("version_applicability_verified") is not False
                or w02.get("human_approved") is not False
                or w02.get("export_allowed") is not False
                or w02.get("auto_promoted") is not False
                or w02.get("owner_signed") is not False
                or w02.get("source_text_retained") is not False
                or type(w02.get("library_item_id")) is not str
                or SHA64.fullmatch(w02["library_item_id"]) is None):
            raise ApprovedDocumentShelfError("W02 entry approval drift")
        items.append({
            "library_item_id": w02["library_item_id"],
            "source_id": "doc:" + repo,
            "related_repo": repo,
            "public_url": url,
            "title": title,
            "kind": "PUBLIC_TECHNICAL_EVIDENCE",
            "purpose_code": purpose,
            "domain": w02["domain"],
            "revision_hint": "PUBLIC_DOCUMENT_REVISION_NOT_PINNED",
            "version_scope_claim": "UNDETERMINED",
            "source_license_status": "NOT_ATTESTED_PER_REVISION",
            "reference_sha256": digest,
            "reference_digest_scope": "UCIE_REFERENCE_STRING_ONLY_NOT_DOCUMENT_BYTES",
            "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
            "human_approved": False,
            "export_allowed": False,
            "trial_executed": False,
        })
    return {
        "schema": SCHEMA,
        "status": STATUS if items else NONE,
        "query": query.casefold().strip(),
        "source_filter": source,
        "items": items,
        "returned_count": len(items),
        "total_matches": len(items),
        "source_count_covered": len(REFERENCES),
        "approved_source_set_unchanged": True,
        "different_evidence_types": True,
        "network_requests": 0,
        "operating_database_writes": 0,
        "source_executed": False,
        "trial_executed_during_search": False,
        "human_approved": False,
        "export_allowed": False,
        "auto_promoted": False,
        "customer_release_authorized": False,
    }


def compare_public_prs_by_source(catalog: dict, public: dict | None) -> dict:
    """Same-source metadata coexistence, NOT subject or fix equivalence."""
    if (type(catalog) is not dict or catalog.get("schema") != SCHEMA
            or catalog.get("status") not in (STATUS, NONE)
            or type(catalog.get("items")) is not list
            or len(catalog["items"]) != catalog.get("returned_count")
            or len(catalog["items"]) > 4
            or catalog.get("network_requests") != 0
            or catalog.get("operating_database_writes") != 0
            or catalog.get("human_approved") is not False
            or catalog.get("export_allowed") is not False
            or catalog.get("auto_promoted") is not False):
        raise ApprovedDocumentShelfError("forged official document catalog")
    base = {
        "schema": SCHEMA,
        "status": UNREQUESTED,
        "public_pr_items_per_source": {},
        "same_source_is_same_fix": False,
        "independent_version_or_licence_verified": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "auto_promoted": False,
    }
    if public is None or not catalog["items"]:
        return base
    if (type(public) is not dict or public.get("schema") != W04_SCHEMA
            or public.get("network_requests") != 0
            or public.get("operating_database_writes") != 0
            or public.get("approved_or_exportable_items") != 0
            or public.get("auto_promoted") is not False
            or type(public.get("items")) is not list
            or type(public.get("returned_count")) is not int
            or len(public["items"]) != public["returned_count"]
            or len(public["items"]) > 10
            or type(public.get("total_matches")) is not int
            or public["total_matches"] < public["returned_count"]):
        raise ApprovedDocumentShelfError("untrusted W04 public evidence page")
    if public.get("status") == "SOURCE_LINKAGE_INCOMPLETE_NO_GO":
        if public["items"] or public["returned_count"] != 0:
            raise ApprovedDocumentShelfError("incomplete source must not yield PRs")
        return dict(base, status=INCOMPLETE)
    if public.get("status") != "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO":
        raise ApprovedDocumentShelfError("unexpected W04 candidate source status")
    sources = {row["related_repo"] for row in catalog["items"]}
    matched = {repo: [] for repo in sources}
    for row in public["items"]:
        if (type(row) is not dict
                or row.get("lifecycle") != "UNVERIFIED_CANDIDATE_ONLY"
                or row.get("human_approved") is not False
                or row.get("export_allowed") is not False):
            raise ApprovedDocumentShelfError("unverified PR promoted")
        source_id = row.get("source_id")
        if source_id not in {"repo:" + repo for repo in sources}:
            continue
        repo = source_id.removeprefix("repo:")
        url = row.get("public_url")
        candidate_id = row.get("library_item_id")
        prefix = "https://github.com/" + repo + "/"
        if (type(url) is not str or not url.startswith(prefix)
                or type(candidate_id) is not str
                or SHA64.fullmatch(candidate_id) is None
                or row.get("kind") not in (
                    "PREVENTION_RULE", "PUBLIC_TECHNICAL_EVIDENCE")):
            raise ApprovedDocumentShelfError("invalid W04 same-source PR candidate")
        tail = url[len(prefix):]
        valid_pr = re.fullmatch(r"pull/[1-9][0-9]{0,8}", tail) is not None
        valid_git = (repo == "git/git"
                     and re.fullmatch(r"commit/[a-f0-9]{40}", tail) is not None)
        if not valid_pr and not valid_git:
            raise ApprovedDocumentShelfError("unapproved W04 public revision URL")
        if len(matched[repo]) < 3:
            matched[repo].append({
                "source_id": source_id,
                "public_url": url,
                "library_item_id": candidate_id,
                "kind": row["kind"],
                "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
                "human_approved": False,
                "export_allowed": False,
            })
    return dict(base, status=PR_PAGE, public_pr_items_per_source=matched)
