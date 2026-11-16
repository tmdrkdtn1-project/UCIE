"""UCIE W10 v03: fail-closed historical Git object and owner-archive review.

This is a read-only provenance *review*. It never deploys, rolls back, signs,
rearms P11, accesses external source or invokes untrusted candidate code.
Git tree provenance and matching owner-local bytes do NOT prove the prior
version was actually deployed, backed up at the correct prechange time, or
approved by independent human QA. Outputs keep these gates explicitly false.

The only temporary write is v02's disposable exact-byte roundtrip; even that
runs only if a separate, fixed-path UCIE archive matches the pinned Git blob
and the checked-out Git HEAD's committed source differs from that blob.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess

from .w10_disposable_restore_probe_v02 import (
    ALLOWED_TARGETS, MAX_BYTES, disposable_restore_probe, git_blob_sha1,
)

SCHEMA = "UCIE_W10_PRECHANGE_GIT_ARCHIVE_ATTESTATION_V03"
ARCHIVE_DIR = "w10_owner_restoration_archive"
SHA1 = re.compile(r"[a-f0-9]{40}\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
STATUS_NO_ARCHIVE = "W10_OWNER_PRECHANGE_ARCHIVE_MISSING_NO_GO"
STATUS_SAME = "W10_SAME_COMMITTED_SOURCE_NO_CANDIDATE_DELTA_NO_GO"
STATUS_RESTORED = "W10_DISPOSABLE_ARCHIVE_BYTES_RESTORED_ONLY_NO_GO"
_GIT_MAX_CAPTURE = MAX_BYTES + 4096


class AttestationError(ValueError):
    """No trusted W10 v03 provenance or bounded restoration review."""


def _root(value: Path) -> Path:
    if (type(value) is not Path
            or value.is_symlink() or not value.is_dir()
            or value.name.casefold() != "ucie"):
        raise AttestationError("exact dedicated UCIE repository directory required")
    resolved = value.resolve(strict=True)
    if resolved.name.casefold() != "ucie" or resolved != value.absolute():
        raise AttestationError("aliased or untrusted UCIE root")
    if not (resolved / ".git").exists():
        raise AttestationError("exact local UCIE Git repository required")
    if (resolved / ".git").is_symlink():
        raise AttestationError("indirect Git directory forbidden")
    return resolved


def _git(root: Path, *argv: str, accept: tuple[int, ...] = (0,)) -> bytes:
    # These subcommands only read local immutable objects / ancestry.
    # The caller supplies only full hex commit IDs and a literal file path.
    env = dict(os.environ)
    env.update({
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_EXTERNAL_DIFF": "0",
        "GIT_ATTR_NOSYSTEM": "1",
    })
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *argv],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=12, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AttestationError("bounded read-only Git query unavailable") from exc
    if result.returncode not in accept or len(result.stdout) > _GIT_MAX_CAPTURE:
        raise AttestationError("local Git ancestry/object query failed closed")
    return result.stdout if result.returncode == 0 else b""


def _tree_blob(root: Path, commit: str, relative: str) -> tuple[str, bytes]:
    # Enforce Git object mode 100644: a symbolic link is an ordinary blob,
    # but must not be interpreted as a restorable Python source file.
    row = _git(root, "ls-tree", commit, "--", relative)
    try:
        meta, recorded_path = row.rstrip(b"\n").split(b"\t", 1)
        mode, kind, blob_raw = meta.split(b" ")
        blob = blob_raw.decode("ascii")
    except (ValueError, UnicodeError) as exc:
        raise AttestationError("exact immutable tree entry required") from exc
    if (mode != b"100644" or kind != b"blob"
            or recorded_path != relative.encode("ascii")
            or SHA1.fullmatch(blob) is None):
        raise AttestationError("unknown, symlink, or non-regular Git tree entry")
    ref = _git(root, "rev-parse", "--verify", commit + ":" + relative)
    if ref.strip().decode("ascii") != blob:
        raise AttestationError("inconsistent Git commit-to-tree-to-blob binding")
    size_raw = _git(root, "cat-file", "-s", blob)
    if not size_raw.strip().isdigit() or not 0 < int(size_raw) <= MAX_BYTES:
        raise AttestationError("Git source blob exceeds first-party byte limit")
    data = _git(root, "cat-file", "blob", blob)
    if len(data) != int(size_raw) or git_blob_sha1(data) != blob:
        raise AttestationError("Git object content does not match object ID")
    return blob, data


def _read_owner_archive(root: Path, target: str) -> bytes | None:
    # No caller-defined paths. Never read operating DB or another project.
    runtime = root / "runtime"
    folder = runtime / ARCHIVE_DIR
    artifact = folder / (target + ".prechange.bin")
    if (runtime.is_symlink() or folder.is_symlink()
            or artifact.is_symlink()):
        raise AttestationError("symlink in owner archive route")
    if not artifact.exists():
        return None
    if not artifact.is_file():
        raise AttestationError("prechange archive is not a regular file")
    if artifact.resolve(strict=True) != folder.resolve() / artifact.name:
        raise AttestationError("archive escaped exact UCIE path")
    with artifact.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if not 0 < len(raw) <= MAX_BYTES:
        raise AttestationError("owner archive absent, empty or oversized")
    return raw


def assess_prechange_archive(
        repo_root: Path, *, target: str, prechange_commit: str,
        expected_prechange_sha256: str,
        expected_prechange_git_blob_sha1: str,
        expected_archive_sha256: str) -> dict:
    """Review exact UCIE commit/path/blob versus a fixed-path owner archive.

    The independently known source hashes and archive digest must be
    supplied by the owner. A matching local file proves byte availability,
    not owner provenance/signature or a historical deployment.
    """
    if (type(target) is not str or target not in ALLOWED_TARGETS
            or type(prechange_commit) is not str
            or SHA1.fullmatch(prechange_commit) is None
            or any(type(x) is not str or SHA256.fullmatch(x) is None
                   for x in (expected_prechange_sha256, expected_archive_sha256))
            or type(expected_prechange_git_blob_sha1) is not str
            or SHA1.fullmatch(expected_prechange_git_blob_sha1) is None):
        raise AttestationError("only exact UCIE target and full immutable pins")
    root = _root(repo_root)
    top = _git(root, "rev-parse", "--show-toplevel").strip().decode("utf-8")
    if Path(top).resolve(strict=True) != root:
        raise AttestationError("Git top-level is not the bounded UCIE checkout")
    if _git(root, "cat-file", "-t", prechange_commit) != b"commit\n":
        raise AttestationError("historical source must be a full Git commit")
    head = _git(root, "rev-parse", "--verify", "HEAD").strip().decode("ascii")
    if SHA1.fullmatch(head) is None:
        raise AttestationError("invalid current Git HEAD")
    if _git(root, "merge-base", "--is-ancestor",
            prechange_commit, head, accept=(0, 1)) != b"":
        raise AttestationError("unexpected ancestry output")
    # merge-base returns no stdout on success OR false. Explicitly require
    # successful 0 status separately, using a marker command below.
    # _git(accept=(0,)) independently rejects a nonancestor exit=1.
    _git(root, "merge-base", "--is-ancestor", prechange_commit, head)
    relative = "src/ucie_miner/" + target
    prior_blob, prior = _tree_blob(root, prechange_commit, relative)
    current_blob, current = _tree_blob(root, head, relative)
    if (prior_blob != expected_prechange_git_blob_sha1
            or sha256(prior).hexdigest() != expected_prechange_sha256):
        raise AttestationError("trusted prechange commit/path/source pins mismatch")
    if expected_archive_sha256 != expected_prechange_sha256:
        raise AttestationError("owner archive pin differs from prechange source")
    archive = _read_owner_archive(root, target)
    archive_present = archive is not None
    if archive_present and (
            sha256(archive).hexdigest() != expected_archive_sha256
            or git_blob_sha1(archive) != prior_blob
            or archive != prior):
        raise AttestationError("owner archive bytes are not exact pinned Git bytes")
    differs = prior_blob != current_blob
    temp_roundtrip = False
    if archive_present and differs:
        proof = disposable_restore_probe(
            target=target,
            prior_bytes=archive, prior_sha256=expected_prechange_sha256,
            prior_git_blob_sha1=prior_blob,
            candidate_bytes=current, candidate_sha256=sha256(current).hexdigest(),
            current_bytes=current, current_sha256=sha256(current).hexdigest(),
            claimed_prior_commit=prechange_commit,
        )
        if (proof.get("disposable_candidate_staged_and_prior_bytes_restored") is not True
                or proof.get("actual_operating_rollback_executed") is not False):
            raise AttestationError("temporary restore proof contract changed")
        temp_roundtrip = True
    status = (STATUS_NO_ARCHIVE if not archive_present else
              STATUS_SAME if not differs else STATUS_RESTORED)
    return {
        "schema": SCHEMA,
        "status": status,
        "target": target,
        "source_relative_path": relative,
        "prechange_commit_sha1": prechange_commit,
        "current_head_sha1": head,
        "prechange_git_blob_sha1": prior_blob,
        "prechange_source_sha256": sha256(prior).hexdigest(),
        "current_git_blob_sha1": current_blob,
        "current_source_sha256": sha256(current).hexdigest(),
        "git_ancestry_and_commit_tree_blob_verified_locally": True,
        "git_remote_owner_authenticity_independently_verified": False,
        "owner_archive_relative_path":
            "runtime/" + ARCHIVE_DIR + "/" + target + ".prechange.bin",
        "owner_archive_present": archive_present,
        "owner_archive_bytes_match_commit": archive_present,
        "owner_archive_historical_capture_independently_authenticated": False,
        "historical_version_was_actually_deployed_attested": False,
        "current_git_source_differs_from_prechange": differs,
        "disposable_exact_byte_restore_exercised": temp_roundtrip,
        "candidate_source_approved_or_tested": False,
        "candidate_heldout_behavior_reverified": False,
        "independent_negative_security_regression_pass": False,
        "post_restore_real_W09_consumer_reverified": False,
        "independent_human_qa_approved": False,
        "owner_deploy_or_rollback_authorized": False,
        "operating_file_modified": False,
        "operating_database_writes": 0,
        "scheduler_modified": False,
        "git_mutations": 0,
        "public_network_gets": 0,
        "actual_operating_rollback_executed": False,
        "auto_promoted": False,
        "customer_release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE W10 v03 read-only Git/archive review")
    parser.add_argument("--ucie-root", required=True, type=Path)
    parser.add_argument("--target", required=True, choices=sorted(ALLOWED_TARGETS))
    parser.add_argument("--prechange-commit", required=True)
    parser.add_argument("--expected-prechange-sha256", required=True)
    parser.add_argument("--expected-prechange-blob-sha1", required=True)
    parser.add_argument("--expected-archive-sha256", required=True)
    args = parser.parse_args()
    try:
        result = assess_prechange_archive(
            args.ucie_root, target=args.target,
            prechange_commit=args.prechange_commit,
            expected_prechange_sha256=args.expected_prechange_sha256,
            expected_prechange_git_blob_sha1=args.expected_prechange_blob_sha1,
            expected_archive_sha256=args.expected_archive_sha256,
        )
    except (AttestationError, OSError, UnicodeError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "W10_V03_SOURCE_ARCHIVE_FAIL_CLOSED",
            "reason_type": type(exc).__name__,
            "actual_operating_rollback_executed": False,
            "operating_database_writes": 0,
            "public_network_gets": 0, "customer_release_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
