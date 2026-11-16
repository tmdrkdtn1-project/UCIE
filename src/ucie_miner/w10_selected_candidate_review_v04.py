"""UCIE W10 v04: selected P9 proposal to bounded Git candidate static review.

This module never executes a candidate, restores operating sources, signs,
queries the network or promotes an unsigned experience into a product rule.
Source/AST inspection is NOT independent behavior or security acceptance.
Only first-party UCIE exact-index proposals are eligible in this slice.
"""
from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import re

from .w10_revision_rollback_review_v01 import (
    TARGET_INDEX, W10ReviewError, review_w10_revision_and_rollback,
)
from .w10_prechange_archive_attestation_v03 import (
    AttestationError, STATUS_NO_ARCHIVE, assess_prechange_archive,
    _git, _root, _tree_blob,
)

SCHEMA = "UCIE_W10_SELECTED_PROPOSAL_GIT_CANDIDATE_STATIC_REVIEW_V04"
STATUS_MISSING = "W10_SELECTED_PROPOSAL_NO_ACTUAL_CANDIDATE_NO_GO"
STATUS_PREVIEW = "W10_SELECTED_PROPOSAL_GIT_CANDIDATE_STATIC_PREVIEW_NO_GO"
ALLOWED_FILE = "src/ucie_miner/library_exact_index.py"
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_IMPORTS = 32
MAX_AST_NODES = 12000


class CandidateReviewError(ValueError):
    """A source/revision/candidate pin or safety contract failed closed."""


def _imports(tree: ast.AST) -> tuple[str, ...]:
    return tuple(sorted(ast.dump(node, annotate_fields=True,
                                 include_attributes=False)
                        for node in tree.body
                        if isinstance(node, (ast.Import, ast.ImportFrom))))


def _symbols(tree: ast.AST) -> set[str]:
    return {node.name for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def _source_structure(before: bytes, candidate: bytes) -> dict:
    try:
        old = ast.parse(before, filename="UCIE_REVIEW_ONLY_PRECHANGE.py")
        new = ast.parse(candidate, filename="UCIE_REVIEW_ONLY_CANDIDATE.py")
    except (SyntaxError, UnicodeError, ValueError) as exc:
        raise CandidateReviewError("candidate/prechange Python syntax not reviewable") from exc
    if (sum(1 for _ in ast.walk(old)) > MAX_AST_NODES
            or sum(1 for _ in ast.walk(new)) > MAX_AST_NODES):
        raise CandidateReviewError("unbounded candidate syntax tree")
    old_imports, new_imports = _imports(old), _imports(new)
    if (len(old_imports) > MAX_IMPORTS or len(new_imports) > MAX_IMPORTS
            or new_imports != old_imports):
        raise CandidateReviewError("candidate alters existing first-party import contract")
    original_functions = _symbols(old)
    candidate_functions = _symbols(new)
    if not original_functions.issubset(candidate_functions):
        raise CandidateReviewError("candidate drops existing first-party definitions")
    # New top-level calls/with/try are not assumed inert; source remains
    # untrusted even when this tiny preflight accepts its shape.
    for tree in (old, new):
        for ix, node in enumerate(tree.body):
            if isinstance(node, ast.Expr) and not (
                    ix == 0 and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)):
                raise CandidateReviewError("top-level expression is not review-only")
            if isinstance(node, (ast.With, ast.AsyncWith, ast.Try, ast.TryStar,
                                 ast.For, ast.While, ast.If, ast.Match)):
                raise CandidateReviewError("new top-level execution control not permitted")
    return {
        "syntax_parsed_without_execution": True,
        "original_imports_unchanged": True,
        "original_top_level_definitions_preserved": True,
        "added_top_level_definitions": sorted(candidate_functions-original_functions),
        "source_bytes_are_behaviorally_equivalent": False,
        "static_shape_review_is_security_approval": False,
    }


def inspect_selected_candidate(
        root: Path, *,
        proposal_id: str,
        prechange_commit: str,
        expected_prechange_sha256: str,
        expected_prechange_blob_sha1: str,
        candidate_commit: str | None = None,
        expected_candidate_sha256: str | None = None,
        expected_candidate_blob_sha1: str | None = None,
        expected_w09_review_digest: str | None = None,
        queries: int = 8, repeats: int = 1) -> dict:
    """Review one real hash-linked W10 P9 proposal and optional Git candidate.

    Candidate must be ONE DIRECT CHILD commit with a ONE-FILE change from
    its immutable prior commit. The candidate is only read and AST parsed,
    NEVER imported or executed. The existing current source W09/W08
    baseline is independently rechecked through W10 v01.
    """
    if (type(proposal_id) is not str or SHA256.fullmatch(proposal_id) is None
            or type(prechange_commit) is not str or SHA1.fullmatch(prechange_commit) is None
            or type(expected_prechange_sha256) is not str
            or SHA256.fullmatch(expected_prechange_sha256) is None
            or type(expected_prechange_blob_sha1) is not str
            or SHA1.fullmatch(expected_prechange_blob_sha1) is None):
        raise CandidateReviewError("full exact proposal and prior source pins required")
    candidate_fields = (candidate_commit, expected_candidate_sha256,
                        expected_candidate_blob_sha1)
    if any(item is None for item in candidate_fields) and not all(
            item is None for item in candidate_fields):
        raise CandidateReviewError("candidate SHA/commit fields are all-or-none")
    supplied = candidate_commit is not None
    if supplied and (
            type(candidate_commit) is not str or SHA1.fullmatch(candidate_commit) is None
            or type(expected_candidate_sha256) is not str
            or SHA256.fullmatch(expected_candidate_sha256) is None
            or type(expected_candidate_blob_sha1) is not str
            or SHA1.fullmatch(expected_candidate_blob_sha1) is None):
        raise CandidateReviewError("full pinned candidate identities required")
    if (expected_w09_review_digest is not None and (
            type(expected_w09_review_digest) is not str
            or SHA256.fullmatch(expected_w09_review_digest) is None)):
        raise CandidateReviewError("invalid owner W09 review pin")
    try:
        repo = _root(root)
        w10 = review_w10_revision_and_rollback(
            repo, limit=20, select_proposal_id=proposal_id,
            expected_w09_review_digest=expected_w09_review_digest,
            queries=queries, repeats=repeats)
        selected = w10["selected_proposal"]
        if (w10["status"] != "W10_EXACT_REVISION_REQUIRES_MANUAL_REVIEW_NO_GO"
                or type(selected) is not dict
                or selected.get("proposal_id") != proposal_id
                or selected.get("target_ucie_component") != TARGET_INDEX
                or selected.get("source_shelf") != "UCIE_SYNTHETIC_EXPERIENCE"
                or selected.get("status") not in (
                    "MORE_UCIE_TESTING_REQUIRED_NOT_APPLIED",
                    "HOLD_FOR_MANUAL_REVIEW_NOT_APPLIED")
                or selected.get("candidate_code_and_sha_pinned") is not False
                or selected.get("owner_deploy_approved") is not False
                or w10.get("w08_reference_heldout_mismatches") != 0
                or w10.get("runtime_rollback_executed") is not False
                or w10.get("customer_release_authorized") is not False):
            raise CandidateReviewError("candidate lacks original exact P9 proposal lineage")
        old_baseline = selected["old_code_source_pin"]
        if old_baseline.get("source_file") != "library_exact_index.py":
            raise CandidateReviewError("wrong original source component")
        archive = assess_prechange_archive(
            repo, target="library_exact_index.py",
            prechange_commit=prechange_commit,
            expected_prechange_sha256=expected_prechange_sha256,
            expected_prechange_git_blob_sha1=expected_prechange_blob_sha1,
            expected_archive_sha256=expected_prechange_sha256)
    except (AttestationError, W10ReviewError, KeyError, TypeError) as exc:
        raise CandidateReviewError("original W10/V03 trust gate rejected source") from exc
    if (archive["prechange_git_blob_sha1"] != expected_prechange_blob_sha1
            or archive["prechange_source_sha256"] != expected_prechange_sha256
            or archive.get("git_ancestry_and_commit_tree_blob_verified_locally") is not True
            or archive.get("actual_operating_rollback_executed") is not False
            or archive.get("owner_deploy_or_rollback_authorized") is not False
            or archive.get("customer_release_authorized") is not False):
        raise CandidateReviewError("archive preflight contract changed")
    owner_source_same_as_git = (
        old_baseline["current_checked_out_source_sha256"] ==
        archive["current_source_sha256"])
    outcome = {
        "schema": SCHEMA,
        "status": STATUS_MISSING,
        "proposal_id": proposal_id,
        "proposal_state": selected["status"],
        "source_experiment_id": selected["source_experiment_id"],
        "target": selected["target_ucie_component"],
        "w09_review_sha256": w10["w09_owner_review_digest_sha256"],
        "w08_current_heldout_cases": w10["w08_reference_heldout_query_cases"],
        "w08_current_heldout_mismatches": 0,
        "prechange_commit": prechange_commit,
        "prechange_source_sha256": expected_prechange_sha256,
        "prechange_git_blob_sha1": expected_prechange_blob_sha1,
        "owner_current_source_matches_committed_head": owner_source_same_as_git,
        "owner_prechange_archive_present": archive["owner_archive_present"],
        "owner_prechange_archive_historically_authenticated": False,
        "prechange_version_was_deployed_attested": False,
        "candidate_git_commit": None,
        "candidate_git_blob_sha1": None,
        "candidate_source_sha256": None,
        "candidate_delta_files": [],
        "candidate_python_ast_static_only": None,
        "candidate_runtime_executed": False,
        "candidate_behavioral_regression_executed": False,
        "candidate_security_negative_regression_executed": False,
        "post_restore_real_w09_consumer_reverified": False,
        "independent_human_qa_approved": False,
        "owner_deploy_or_rollback_authorized": False,
        "operating_file_modified": False,
        "operating_database_writes": 0,
        "scheduler_modified": False,
        "public_network_gets": 0,
        "git_mutations": 0,
        "actual_operating_rollback_executed": False,
        "auto_promoted": False,
        "customer_release_authorized": False,
    }
    if not supplied:
        return outcome

    # Exact direct-child constraint prevents smuggling an unrelated history
    # between the pinned prechange and review candidate commits.
    try:
        if _git(repo, "cat-file", "-t", candidate_commit) != b"commit\n":
            raise CandidateReviewError("candidate object must be an immutable commit")
        ancestry = _git(repo, "rev-list", "--parents", "-n", "1", candidate_commit)
        if ancestry.decode("ascii").strip().split() != [
                candidate_commit, prechange_commit]:
            raise CandidateReviewError("candidate must be direct child of pinned prior")
        changed = _git(
            repo, "diff-tree", "--no-commit-id", "-r", "--no-renames",
            "--name-only", "-z", candidate_commit)
        changed_paths = [x.decode("utf-8") for x in changed.split(b"\0") if x]
        if changed_paths != [ALLOWED_FILE]:
            raise CandidateReviewError("candidate modifies unexpected first-party path")
        old_blob, before = _tree_blob(repo, prechange_commit, ALLOWED_FILE)
        candidate_blob, candidate_bytes = _tree_blob(
            repo, candidate_commit, ALLOWED_FILE)
    except (AttestationError, OSError, UnicodeError, ValueError) as exc:
        raise CandidateReviewError("candidate Git source proof invalid") from exc
    if (old_blob != expected_prechange_blob_sha1
            or candidate_blob != expected_candidate_blob_sha1
            or sha256(candidate_bytes).hexdigest() != expected_candidate_sha256
            or candidate_blob == old_blob
            or candidate_bytes == before):
        raise CandidateReviewError("candidate source digest/mutation mismatch")
    structural = _source_structure(before, candidate_bytes)
    outcome.update({
        "status": STATUS_PREVIEW,
        "candidate_git_commit": candidate_commit,
        "candidate_git_blob_sha1": candidate_blob,
        "candidate_source_sha256": expected_candidate_sha256,
        "candidate_delta_files": changed_paths,
        "candidate_python_ast_static_only": structural,
    })
    return outcome


def main() -> int:
    ap = argparse.ArgumentParser(description="UCIE W10 v04 exact proposal candidate review")
    ap.add_argument("--ucie-root", required=True, type=Path)
    ap.add_argument("--proposal-id", required=True)
    ap.add_argument("--prechange-commit", required=True)
    ap.add_argument("--prechange-sha256", required=True)
    ap.add_argument("--prechange-blob-sha1", required=True)
    ap.add_argument("--candidate-commit")
    ap.add_argument("--candidate-sha256")
    ap.add_argument("--candidate-blob-sha1")
    ap.add_argument("--expected-w09-review-digest")
    args = ap.parse_args()
    try:
        result = inspect_selected_candidate(
            args.ucie_root, proposal_id=args.proposal_id,
            prechange_commit=args.prechange_commit,
            expected_prechange_sha256=args.prechange_sha256,
            expected_prechange_blob_sha1=args.prechange_blob_sha1,
            candidate_commit=args.candidate_commit,
            expected_candidate_sha256=args.candidate_sha256,
            expected_candidate_blob_sha1=args.candidate_blob_sha1,
            expected_w09_review_digest=args.expected_w09_review_digest)
    except (CandidateReviewError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({
            "schema":SCHEMA, "status":"W10_V04_PROPOSAL_OR_SOURCE_FAIL_CLOSED",
            "reason_type":type(exc).__name__,
            "candidate_runtime_executed":False,
            "operating_database_writes":0,
            "actual_operating_rollback_executed":False,
            "customer_release_authorized":False},sort_keys=True))
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
