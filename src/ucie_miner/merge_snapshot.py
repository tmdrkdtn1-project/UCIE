"""Stage 7 exact-identity public merge snapshot comparison (read-only).

Pins only public PR numbers, merge times, target branch and merge SHA.
A pinned match does not prove release-tag inclusion, semantic fix, license
permission, human approval or a signed Rulepack.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .patterns import PatternError
from .provenance_review import _validate as validate_rows
from .review import ALLOWED, _check_timestamp, load_manifest

HEX40 = re.compile(r"[a-f0-9]{40}")
MAX_BYTES = 18000
FIELDS = frozenset({"source", "pr_number", "public_url",
                    "merged_at", "base_branch", "merge_commit_sha"})
BRANCHES = {
    "python/cpython": frozenset(("main", "3.14", "3.15")),
    "PowerShell/PowerShell": frozenset(("master",)),
}


def _unique_json_fields(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise PatternError("duplicate snapshot JSON key")
        obj[k] = v
    return obj


def load_merge_snapshot(root: Path, manifest: object = None) -> dict:
    root = Path(root)
    if root.is_symlink():
        raise PatternError("symlinked root denied")
    path = root / "docs" / "evidence" / "public_pr_merge_snapshot_v1.json"
    if ((root / "docs").is_symlink()
            or (root / "docs" / "evidence").is_symlink()
            or path.is_symlink() or not path.is_file()
            or path.stat().st_size > MAX_BYTES):
        raise PatternError("unsafe or missing public snapshot")
    try:
        data = json.loads(path.read_text("utf-8"),
                          object_pairs_hook=_unique_json_fields)
    except (OSError, ValueError, UnicodeError) as exc:
        raise PatternError("invalid public merge snapshot") from exc
    keys = {"schema", "observed_utc_date", "source_basis", "note", "entries"}
    if (not isinstance(data, dict) or set(data) != keys
            or data["schema"] != "UCIE_PUBLIC_PR_MERGE_SNAPSHOT_V1"
            or data["observed_utc_date"] != "2026-10-14"
            or data["source_basis"] != "PUBLIC_UPSTREAM_PR_METADATA_OBSERVED_VIA_GITHUB_CONNECTOR"
            or not isinstance(data["note"], str)
            or not isinstance(data["entries"], list)
            or not 1 <= len(data["entries"]) <= 40):
        raise PatternError("unexpected merge snapshot format")
    expected = manifest if manifest is not None else load_manifest(root)
    if (not isinstance(expected, dict)
            or expected.get("schema") != "UCIE_PR_REVIEW_EVIDENCE_V1"
            or not isinstance(expected.get("entries"), list)):
        raise PatternError("invalid curated PR manifest")
    curated = {}
    for e in expected["entries"]:
        if not isinstance(e, dict):
            raise PatternError("malformed curated entry")
        source, number = e.get("source"), e.get("pr_number")
        if not isinstance(source, str) or type(number) is not int:
            raise PatternError("bad curated PR identity")
        key = source, number
        if key in curated:
            raise PatternError("duplicate curated PR")
        curated[key] = e
    result = {}
    for e in data["entries"]:
        if not isinstance(e, dict) or set(e) != FIELDS:
            raise PatternError("invalid pinned PR schema")
        source, number = e["source"], e["pr_number"]
        if not isinstance(source, str) or type(number) is not int:
            raise PatternError("invalid public identity")
        key = source, number
        if (source not in ALLOWED or key in result or key not in curated
                or e["public_url"] != f"https://github.com/{source}/pull/{number}"
                or e["merged_at"] != curated[key]["merged_at"]
                or e["base_branch"] not in BRANCHES[source]
                or not isinstance(e["merge_commit_sha"], str)
                or not HEX40.fullmatch(e["merge_commit_sha"])):
            raise PatternError("unapproved/stale public merge pin")
        _check_timestamp(e["merged_at"])
        result[key] = e
    if set(result) != set(curated):
        raise PatternError("pinned snapshot does not cover curated PRs")
    return data


def compare_merge_snapshot(root, source_rows, provenance_receipt,
                           manifest=None) -> dict:
    """Compare pinned PRs to local metadata + nonauthoritative observations."""
    manifest = load_manifest(root) if manifest is None else manifest
    snapshot = load_merge_snapshot(root, manifest)
    rows = validate_rows(source_rows)
    pins = {(x["source"], x["pr_number"]): x
            for x in snapshot["entries"]}
    indexed = {(r["source"], r["pr_number"]): r for r in rows}
    if (not isinstance(provenance_receipt, dict)
            or provenance_receipt.get("schema") != "UCIE_PUBLIC_PR_PROVENANCE_INSPECTION_V1"
            or provenance_receipt.get("count") != len(rows)
            or not isinstance(provenance_receipt.get("items"), list)
            or len(provenance_receipt["items"]) != len(rows)):
        raise PatternError("invalid provenance inspection scope")
    pindex = {}
    for result in provenance_receipt["items"]:
        if not isinstance(result, dict):
            raise PatternError("malformed public metadata item")
        key = result.get("source"), result.get("pr_number")
        if (not isinstance(key[0], str) or type(key[1]) is not int
                or key not in indexed or key in pindex
                or result.get("merged_at") != indexed[key]["merged_at"]
                or result.get("miner_evidence_sha256") != indexed[key]["evidence_sha256"]):
            raise PatternError("stale or duplicate public receipt")
        pindex[key] = result
    if set(pindex) != set(indexed):
        raise PatternError("incomplete public receipt")
    comparisons = []
    mismatches = 0
    for key in sorted(set(pins).intersection(indexed)):
        pinned, local, observed = pins[key], indexed[key], pindex[key]
        if (pinned["merged_at"] != local["merged_at"]
                or pinned["public_url"] != local["public_url"]):
            raise PatternError("local public metadata differs from pinned record")
        remote_state = observed.get("source_check")
        remote_sha = observed.get("observed_merge_commit_sha")
        if remote_state in ("PUBLIC_API_METADATA_MATCHED", "SYNTHETIC_METADATA_MATCHED"):
            if remote_sha != pinned["merge_commit_sha"]:
                state = "MERGE_SHA_MISMATCH"
                mismatches += 1
            else:
                state = ("PUBLIC_METADATA_SHA_EQUAL" if remote_state ==
                         "PUBLIC_API_METADATA_MATCHED" else
                         "SYNTHETIC_SHA_EQUAL_NOT_VERIFIED")
        else:
            state = "NOT_INDEPENDENTLY_CHECKED"
        comparisons.append({
            "source": key[0], "pr_number": key[1],
            "merge_commit_sha": pinned["merge_commit_sha"],
            "base_branch": pinned["base_branch"],
            "comparison": state,
            "fixed_release_version": "UNDETERMINED",
            "source_patch_reproduced": False,
        })
    if mismatches:
        raise PatternError("public PR merge SHA mismatch")
    canonical = json.dumps(snapshot["entries"], sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    return {
        "schema": "UCIE_PINNED_PUBLIC_MERGE_COMPARISON_V1",
        "status": "CANDIDATE_METADATA_CHECK_ONLY",
        "snapshot_sha256": hashlib.sha256(canonical).hexdigest(),
        "curated_pr_count": len(pins),
        "local_pinned_pr_count": len(comparisons),
        "extra_unmapped_local_pr_count": len(indexed) - len(comparisons),
        "observations": comparisons,
        "independently_reproduced_fixes": 0,
        "version_inclusion_verified": False,
        "signed": False, "production_approved": False,
        "persistent_writes": 0,
    }
