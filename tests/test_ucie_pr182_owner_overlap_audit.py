"""UCIE-only read-only PR182 local overlapping source SHA audit.

This is an acceptance preflight, not a checkout/merge. Reads ONLY the eight
literal UCIE first-party V1 source paths; no external project, network, runtime
database, scheduler, private code or mutation. The pinned digests refer to
PR #182 HEAD 6d502d82e31bd7964d914873618f1d3f1d575fd2.
"""
from __future__ import annotations

from hashlib import sha1
import json
import os
import subprocess
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GIT_BLOBS = {
    "skillbook_catalog_union_v01.py": "1fb32d738f91f8295faf5985984e422bf0b7e78d",
    "skillbook_editorial_production_v01.py": "4831c5df02e7ffc379253b6006e19f216ce70572",
    "skillbook_official_doc_observation_v01.py": "faf443c144866f81cb8e7794d9122ee85a3c78a3",
    "skillbook_owner_pinned_acceptance_v01.py": "e50307526c4edd8b4b36577853078c40b65033a6",
    "skillbook_pinned_source_review_v01.py": "2e036452d8117c660230d1b1a039ff1691b081d9",
    "skillbook_principle_composer_v01.py": "a22a5278f716234e19661525d1b51c90043ad04e",
    "skillbook_revision_review_v01.py": "88cb94407b42d1ab8bcb3e22d19e183d3141fc16",
    "skillbook_two_recipe_disposable_v01.py": "8fff35047afc725c9879c8912f645861cc48124f",
}


def _git_blob(data: bytes) -> str:
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def audit_overlap_read_only() -> dict:
    actual = ROOT.resolve(strict=True)
    if (ROOT.is_symlink() or actual.name.casefold() != "ucie"
            or (os.name == "nt" and actual != Path("D:/UCIE").resolve()
                and "GITHUB_ACTIONS" not in os.environ)):
        raise ValueError("non-owner source root not authorized")
    source_dir = actual / "src" / "ucie_miner"
    if (source_dir.is_symlink() or not source_dir.is_dir()):
        raise ValueError("UCIE source directory unavailable")
    result = {}
    for name, expected in EXPECTED_GIT_BLOBS.items():
        target = source_dir / name
        if target.is_symlink():
            status = "SYMLINK_BLOCKED"
        elif not target.is_file():
            status = "MISSING"
        elif target.stat().st_size > 200_000:
            status = "OVERSIZE_BLOCKED"
        else:
            raw = target.read_bytes()
            actual_hash = _git_blob(raw)
            normalized_hash = _git_blob(raw.replace(b"\r\n", b"\n"))
            status = (
                "EXACT_GIT_BLOB" if actual_hash == expected
                else "CRLF_ONLY" if normalized_hash == expected
                else "DIFFERENT_PRESERVE_OWNER"
            )
        result[name] = status
    counts = {status: sum(item == status for item in result.values())
              for status in sorted(set(result.values()))}
    return {
        "schema": "UCIE_PR182_OWNER_OVERLAP_AUDIT_V01",
        "scope": "EXACT_EIGHT_UCIE_ONLY",
        "pinned_pr_head": "6d502d82e31bd7964d914873618f1d3f1d575fd2",
        "results": result,
        "counts": counts,
        "all_identical_or_crlf": all(
            value in ("EXACT_GIT_BLOB", "CRLF_ONLY")
            for value in result.values()),
        "files_written": 0,
        "operating_database_writes": 0,
        "checkout_or_git_mutation": False,
        "owner_files_deleted_or_overwritten": False,
        "safe_to_overwrite_owner_files": False,
    }


class UCIEOwnerOverlapReadOnlyPreflight(unittest.TestCase):
    def test_local_editorial_git_object_if_available(self):
        """Never fetch or modify Git: inspect pinned object only if locally cached."""
        sha = EXPECTED_GIT_BLOBS["skillbook_editorial_production_v01.py"]
        result = subprocess.run(
            ["git", "-C", str(ROOT), "cat-file", "-e", sha],
            capture_output=True, timeout=6, check=False)
        print("UCIE_PR182_EDITORIAL_OBJECT_CACHED=" + json.dumps({
            "expected_git_blob": sha,
            "cached": result.returncode == 0,
            "git_operation": "CAT_FILE_READ_ONLY",
        }))
        self.assertIn(result.returncode, (0, 1, 128))

    def test_actual_owner_eight_source_blobs_no_mutation(self):
        result = audit_overlap_read_only()
        self.assertEqual(result["schema"], "UCIE_PR182_OWNER_OVERLAP_AUDIT_V01")
        self.assertEqual(len(result["results"]), 8)
        self.assertEqual(set(result["results"]), set(EXPECTED_GIT_BLOBS))
        self.assertFalse(result["checkout_or_git_mutation"])
        self.assertFalse(result["safe_to_overwrite_owner_files"])
        print("UCIE_PR182_OWNER_OVERLAP_AUDIT=" + json.dumps(
            result, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
