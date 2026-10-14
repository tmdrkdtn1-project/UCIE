"""Bounded adapter between legacy public miner records and offline evidence gate.

No new network access, credentials, persistent raw patches, or auto-promotion.
Missing provenance is reported as incomplete instead of fabricated.
"""
from __future__ import annotations

from .core import MiningError, PUBLIC_SOURCES
from .evidence import SOURCES, evaluate

CATEGORY = {"python/cpython": "python", "PowerShell/PowerShell": "powershell"}


def inspect_collected_pr(source: str, pr: object, files: object) -> dict:
    """Evaluate a fetched PR only when full evidence metadata exists.

    Older/minimal collector fixtures may omit merge SHA and license information:
    such records remain unverified, never implicitly pass.
    """
    if source not in PUBLIC_SOURCES or source not in SOURCES:
        raise MiningError("unapproved collector source")
    if not isinstance(pr, dict):
        raise MiningError("invalid collected PR")
    number = pr.get("number")
    if type(number) is not int or number < 1:
        raise MiningError("invalid collected PR number")
    if not isinstance(files, list) or not 1 <= len(files) <= 30:
        raise MiningError("invalid collected file list")
    if any(not isinstance(file, dict) or not isinstance(file.get("filename"), str) or not isinstance(file.get("patch", ""), str) for file in files):
        raise MiningError("malformed collected file metadata")
    # Never persist or return patches. The underlying collector separately
    # stores only a patch digest and non-sensitive tags.
    required = ("merged_at", "updated_at", "merge_commit_sha", "license", "license_url")
    missing = [field for field in required if not pr.get(field)]
    if missing:
        return {"status": "INCOMPLETE_PROVENANCE", "source": source,
                "pr_number": number, "missing_fields": missing,
                "verification_pass": 0, "rule_promoted": False}
    record = {
        "source": source, "number": number,
        "url": "https://github.com/" + source + "/pull/" + str(number),
        "category": CATEGORY[source], "merged_at": pr["merged_at"],
        "updated_at": pr["updated_at"], "commit": pr["merge_commit_sha"],
        "license": pr["license"], "license_url": pr["license_url"],
        "files": [{"filename": f.get("filename"), "patch": f.get("patch", "")}
                  for f in files if isinstance(f, dict)],
    }
    if len(record["files"]) != len(files):
        raise MiningError("malformed collected file metadata")
    result = evaluate(record)
    result["verification_pass"] = 0
    return result
