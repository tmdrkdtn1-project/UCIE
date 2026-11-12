"""CI-only: reconstruct TWO exact UCIE Git-commit source wheels without checkout.

Uses git archive for A and B from the *public UCIE repo's own* fetched
history and validates every SHA1 blob and first-party wheel SHA256 RECORD.
No pip, vendor wheel, API, customer contents, git fetch, signing or release.
CI must checkout this repository with fetch-depth: 0 first.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    if repo.name.casefold() != "ucie" or not (repo / ".git").is_dir():
        raise SystemExit("UCIE exact public repository checkout required")
    sys.path.insert(0, str(repo / "src"))
    from ucie_miner import customer_pinned_git_source_v01 as pin
    from ucie_miner import customer_full_product_offline_rehearsal_v01 as full

    doc, manifests = pin._load_manifest(repo)
    receipts = {}
    with TemporaryDirectory(prefix="UCIE_C1_PINNED_GIT_OBJECT_BUILD_") as scratch:
        for label in ("A", "B"):
            # Reads only immutable Git blobs; no worktree source or remote URL.
            source = pin._git_clean_source(repo, manifests, label)
            destination = Path(scratch) / label
            destination.mkdir()
            file = full._build_first_party_wheel(
                destination, source, version=pin.VERSION[label])
            checks = full._inspect_first_party_wheel(
                file, source, version=pin.VERSION[label])
            if (checks["file_count"] != len(manifests[label]["python"])
                    or not checks["wheel_record_verified"]
                    or not checks["source_code_bytes_match"]):
                raise SystemExit("exact UCIE Git-first-party wheel source mismatch")
            receipts[label] = {
                "commit": pin.PINNED[label][0],
                "tree": pin.PINNED[label][1],
                "qa_only_wheel_version": pin.VERSION[label],
                "python_source_members": checks["file_count"],
                "first_party_wheel_sha256": checks["sha256"],
            }
        if (receipts["A"]["python_source_members"] != 182
                or receipts["B"]["python_source_members"] != 184
                or receipts["A"]["first_party_wheel_sha256"]
                    == receipts["B"]["first_party_wheel_sha256"]):
            raise SystemExit("reviewed Git A/B source difference not reproduced")
    print(json.dumps({
        "schema": "UCIE_C1_PINNED_GIT_TWO_COMMIT_REPRODUCTION_CI_V01",
        "status": "EXACT_GIT_BLOB_FIRST_PARTY_WHEELS_VERIFIED_NOT_CUSTOMER_RELEASE",
        "source_sha256_of_reviewed_manifest": sha256(json.dumps(
            doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")).hexdigest(),
        "Git_exact_first_party_reproduced": True,
        "external_vendor_packages_executed": False,
        "vendor_wheels_uploaded": False,
        "customer_release_authorized": False,
        "A": receipts["A"],
        "B": receipts["B"],
    }, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
