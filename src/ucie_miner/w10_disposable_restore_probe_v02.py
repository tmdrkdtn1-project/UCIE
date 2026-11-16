"""UCIE W10 v02: offline Git-blob byte identity and disposable restore proof.

NEVER an operating rollback, endorsement of untrusted source, or proof that
prior bytes were once deployed. The caller must separately authenticate that
the advertised Git blob belongs to a specific immutable commit/path.

No arbitrary path input, Git checkout, network access, source execution,
original/operating file write, OS task modification, signing or release.
Only caller-provided bounded UCIE first-party byte sequences are staged in
stdlib's ephemeral temporary directory and discarded on exit.
"""
from __future__ import annotations

from hashlib import sha1, sha256
from pathlib import Path
import re
from tempfile import TemporaryDirectory

SCHEMA = "UCIE_W10_DISPOSABLE_GIT_BLOB_RESTORE_PROBE_V02"
STATUS = "GIT_BLOB_BYTES_AND_TEMP_ROUNDTRIP_ONLY_OPERATIONAL_ROLLBACK_NO_GO"
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
SHA1 = re.compile(r"[a-f0-9]{40}\Z")
# These basenames are the exact original first-party W10 v01 source targets.
ALLOWED_TARGETS = frozenset(("library_exact_index.py", "capability_trials.py"))
MAX_BYTES = 100_000


class ProbeError(ValueError):
    """Reject malformed, substituted, unauthorized or unbounded evidence."""


def _validate_blob(name: str, data: bytes, expected_sha256: str) -> str:
    if (type(data) is not bytes or not 0 < len(data) <= MAX_BYTES
            or type(expected_sha256) is not str
            or SHA256.fullmatch(expected_sha256) is None):
        raise ProbeError("bounded exact bytes and SHA-256 required: " + name)
    observed = sha256(data).hexdigest()
    if observed != expected_sha256:
        raise ProbeError("SHA-256 mismatch: " + name)
    return observed


def git_blob_sha1(data: bytes) -> str:
    """Compute Git's canonical blob object ID, with binary byte fidelity."""
    if type(data) is not bytes or not 0 < len(data) <= MAX_BYTES:
        raise ProbeError("bounded bytes required for Git blob identity")
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def disposable_restore_probe(*, target: str,
                             prior_bytes: bytes, prior_sha256: str,
                             prior_git_blob_sha1: str,
                             candidate_bytes: bytes, candidate_sha256: str,
                             current_bytes: bytes, current_sha256: str,
                             claimed_prior_commit: str | None = None) -> dict:
    """Stage candidate, restore prior bytes and compare, entirely in TEMP.

    Verifies supplied byte digests and a *supplied* Git blob object ID.
    It does NOT verify that GitHub or a specific commit contains that object;
    that independent repository provenance check must be separately supplied.
    """
    if type(target) is not str or target not in ALLOWED_TARGETS:
        raise ProbeError("only exact UCIE first-party basenames allowed")
    if (type(prior_git_blob_sha1) is not str
            or SHA1.fullmatch(prior_git_blob_sha1) is None):
        raise ProbeError("full expected original Git blob SHA-1 required")
    if claimed_prior_commit is not None and (
            type(claimed_prior_commit) is not str
            or SHA1.fullmatch(claimed_prior_commit) is None):
        raise ProbeError("full immutable Git commit SHA required")

    before = _validate_blob("prior", prior_bytes, prior_sha256)
    candidate = _validate_blob("candidate", candidate_bytes, candidate_sha256)
    current = _validate_blob("current", current_bytes, current_sha256)
    blob = git_blob_sha1(prior_bytes)
    if blob != prior_git_blob_sha1:
        raise ProbeError("prior Git blob mismatch")
    if before == candidate:
        raise ProbeError("candidate must differ from pinned prior bytes")

    with TemporaryDirectory(prefix="UCIE_W10_DISPOSABLE_") as directory:
        # Filename has been checked against the two literal UCIE basenames.
        # The caller cannot supply a directory, symlink or output path.
        staged = Path(directory) / target
        staged.write_bytes(candidate_bytes)
        candidate_readback = staged.read_bytes()
        if (candidate_readback != candidate_bytes
                or sha256(candidate_readback).hexdigest() != candidate):
            raise ProbeError("disposable candidate staging mismatch")
        staged.write_bytes(prior_bytes)
        restored = staged.read_bytes()
        if (restored != prior_bytes or sha256(restored).hexdigest() != before
                or git_blob_sha1(restored) != blob):
            raise ProbeError("disposable exact-byte restore mismatch")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "source_target_filename": target,
        "prior_sha256": before,
        "prior_git_blob_sha1": blob,
        "candidate_sha256": candidate,
        "current_sha256": current,
        "claimed_prior_commit": claimed_prior_commit,
        "prior_git_blob_identity_matches_caller_pin": True,
        "claimed_commit_contains_blob_independently_verified": False,
        "prior_bytes_authenticated_as_actual_prechange": False,
        "owner_host_restorable_bytes_verified": False,
        "candidate_known_from_approved_revision": False,
        "candidate_behavior_regression_executed": False,
        "independent_security_regression_completed": False,
        "disposable_candidate_staged_and_prior_bytes_restored": True,
        "temporary_files_cleaned_after_test": True,
        "post_restore_w09_consumer_verified": False,
        "actual_operating_rollback_executed": False,
        "operating_source_modified": False,
        "operating_database_writes": 0,
        "public_network_gets": 0,
        "git_mutations": 0,
        "scheduler_modified": False,
        "owner_signature_created": False,
        "independent_human_qa_approved": False,
        "owner_release_approved": False,
        "auto_promoted": False,
        "customer_release_authorized": False,
    }
