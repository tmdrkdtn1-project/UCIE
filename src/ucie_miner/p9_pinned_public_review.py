"""Pinned public PR/merge and repository LICENSE observations for UCIE P9.

These facts were independently *looked up from source metadata* on
2026-10-30, NOT independently quality-assured, legally cleared, or
proven present in a released runtime. No network, file reads or execution.
One known merge and one known release tag are compared by exact Git SHA.
A diverged history NEVER proves absence of a fix (backports may exist).
"""
from __future__ import annotations

import re

from .source_registry import get_source, SourceRegistryError

SCHEMA = "UCIE_P9_PINNED_PUBLIC_REVISION_SOURCE_REVIEW_V1"
OBSERVED_UTC_DATE = "2026-10-30"
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_PINNED = (
    {
        "source_id": "repo:python/cpython",
        "pr_number": 153462,
        "merge_sha": "999a046b24cff4ba0e72b574196721f66bd08237",
        "merged_at_utc": "2026-08-21T17:02:24Z",
        "license_file": "LICENSE",
        "license_blob_sha": "20cf39097c68baa17cc566b64e76d34ebf034044",
        "repository_license_family": "PSF-2.0_WITH_COMPONENT_EXCEPTIONS",
        "release_tag": "v3.15.0",
        "release_tag_commit_sha": "d220409a13b77de7a6c30abe16ea90db01528edc",
        "merge_base_sha": "f31a89bb901067dd105b00cfa90523cf7ffdbbdd",
        "ahead_by": 1225, "behind_by": 1556,
    },
    {
        "source_id": "repo:PowerShell/PowerShell",
        "pr_number": 28042,
        "merge_sha": "bd8cb01a7d5b86129c45eaa14ab5830a63b1283f",
        "merged_at_utc": "2026-10-09T16:35:49Z",
        "license_file": "LICENSE.txt",
        "license_blob_sha": "b2f52a2bad4e27e2d9c68a755abb74cb8943f2fa",
        "repository_license_family": "MIT",
        "release_tag": "v7.6.6",
        "release_tag_commit_sha": "f260eb9c31ec72c5282f98e5ea24d9be4f8d7536",
        "merge_base_sha": "8a723f8b19ed5ae387aaf1a8cc106d6111dee6f1",
        "ahead_by": 207, "behind_by": 425,
    },
    {
        "source_id": "repo:PowerShell/PowerShell",
        "pr_number": 28087,
        "merge_sha": "373f6a7b7972a0a4b73bfd9737a0d768d28b347e",
        "merged_at_utc": "2026-10-09T17:21:35Z",
        "license_file": "LICENSE.txt",
        "license_blob_sha": "b2f52a2bad4e27e2d9c68a755abb74cb8943f2fa",
        "repository_license_family": "MIT",
        "release_tag": "v7.6.6",
        "release_tag_commit_sha": "f260eb9c31ec72c5282f98e5ea24d9be4f8d7536",
        "merge_base_sha": "8a723f8b19ed5ae387aaf1a8cc106d6111dee6f1",
        "ahead_by": 207, "behind_by": 428,
        # Direct read-only inspection of SAME source path on exact commit
        # versus exact release tag commit; Git blob IDs are NOT SHA-256.
        "tag_source_comparison": {
            "path": "src/Microsoft.PowerShell.Commands.Management/commands/management/ResolvePathCommand.cs",
            "fix_commit_blob_git_sha1": "e6a89e2a11732dfc0ed36af8194432155265486c",
            "tag_commit_blob_git_sha1": "3d1b66933d26f5e55632184e0981c67771c4d853",
            "fix_helper_identifier": "StartsWithRelativePathToken",
            "old_branch_condition": "!adjustedPath.StartsWith('.')",
            "fix_helper_found_in_merge_source": True,
            "fix_helper_found_in_tag_source": False,
            "old_condition_found_in_tag_source": True,
        },
    },
)


def lookup_pinned_review(*, source_id: str, public_url: str,
                         merge_sha: str) -> dict | None:
    """Pure exact-match public provenance lookup, never any approval grant.

    Accepts only W04-derived identity fields, not untrusted upstream content.
    No result = not covered by this tiny first-party observation sample.
    """
    if (type(source_id) is not str or type(public_url) is not str
            or type(merge_sha) is not str or _HEX40.fullmatch(merge_sha) is None):
        raise ValueError("invalid pinned public review lookup")
    try:
        source = get_source(source_id)
    except SourceRegistryError as exc:
        raise ValueError("source outside UCIE public allowlist") from exc
    if source["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY":
        return None
    for pinned in _PINNED:
        if (source_id != pinned["source_id"]
                or merge_sha != pinned["merge_sha"]):
            continue
        repo = source_id.removeprefix("repo:")
        expected_pr = f"https://github.com/{repo}/pull/{pinned['pr_number']}"
        if public_url != expected_pr:
            return None
        # GitHub compare of pinned merge SHA vs pinned release tag SHA was
        # DIVERGED. This is not equivalent to 'fix absent in release'.
        if (pinned["ahead_by"] <= 0 or pinned["behind_by"] <= 0
                or pinned["merge_base_sha"] == pinned["merge_sha"]
                or pinned["merge_base_sha"] == pinned["release_tag_commit_sha"]):
            raise ValueError("invalid pinned divergence evidence")
        license_url = (f"https://github.com/{repo}/blob/"
                       f"{merge_sha}/{pinned['license_file']}")
        inspection = pinned.get("tag_source_comparison")
        if inspection is not None:
            if (inspection["fix_commit_blob_git_sha1"]
                    == inspection["tag_commit_blob_git_sha1"]
                    or inspection["fix_helper_found_in_merge_source"] is not True
                    or inspection["fix_helper_found_in_tag_source"] is not False
                    or inspection["old_condition_found_in_tag_source"] is not True):
                raise ValueError("invalid exact-tag source comparison evidence")
        return {
            "examined_tag_source_patch": (
                {
                    "status": "SPECIFIC_PR28087_IMPLEMENTATION_ABSENT_IN_EXAMINED_TAG_SOURCE",
                    "scope": "ONE_EXACT_C_SHARP_SOURCE_FILE",
                    "path": inspection["path"],
                    "fix_commit_blob_git_sha1": inspection["fix_commit_blob_git_sha1"],
                    "tag_commit_blob_git_sha1": inspection["tag_commit_blob_git_sha1"],
                    "fixed_helper_identifier": inspection["fix_helper_identifier"],
                    "pre_fix_condition_identifier": inspection["old_branch_condition"],
                    "fixed_helper_present_at_merge": True,
                    "fixed_helper_present_in_tag": False,
                    "pre_fix_condition_present_in_tag": True,
                    "equivalent_backport_excluded": False,
                    "all_alternate_fix_paths_reviewed": False,
                    "runtime_bug_reproduced_for_tag": False,
                    "runtime_fix_coverage_verified": False,
                    "release_artifact_binaries_examined": False,
                    "source_was_executed": False,
                } if inspection is not None else None
            ),
            "schema": SCHEMA,
            "status": "PINNED_REPOSITORY_LICENSE_AND_DIVERGENT_RELEASE_OBSERVED_NO_GO",
            "source_id": source_id,
            "public_pr_url": expected_pr,
            "merge_sha": merge_sha,
            "merged_at_utc": pinned["merged_at_utc"],
            "observed_date_utc": OBSERVED_UTC_DATE,
            "repository_license_family_observed": pinned["repository_license_family"],
            "repository_license_blob_sha": pinned["license_blob_sha"],
            "repository_license_url": license_url,
            "repo_license_observed_at_merge_sha": True,
            "upstream_release_tag": pinned["release_tag"],
            "release_tag_commit_sha": pinned["release_tag_commit_sha"],
            "compare_base_merge_sha": merge_sha,
            "compare_merge_base_sha": pinned["merge_base_sha"],
            "compare_status": "diverged",
            "release_ahead_by": pinned["ahead_by"],
            "release_behind_by": pinned["behind_by"],
            "merge_ancestor_of_examined_release": False,
            "release_contains_fix_verified": False,
            "absence_of_backport_verified": False,
            "affected_runtime_version_verified": False,
            "per_file_third_party_license_cleared": False,
            "legal_signoff_completed": False,
            "independent_qa_completed": False,
            "upstream_source_code_executed": False,
            "approved_or_exportable": False,
            "production_ready": False,
            "network_requests": 0,
            "operating_database_writes": 0,
            "auto_promoted": False,
        }
    return None
