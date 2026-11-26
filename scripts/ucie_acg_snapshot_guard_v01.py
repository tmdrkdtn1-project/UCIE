#!/usr/bin/env python3
"""Repository-scoped Git recovery checkpoints. Offline, no workflow or network access.

Creates an immutable-by-convention local ref for an ALREADY committed and clean HEAD.
It never stages, commits, resets, checks out, stashes, pushes, or captures dirty files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

HEX = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,63}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ZERO = "0" * 40


class SnapshotDenied(ValueError):
    pass


def git(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args], timeout=15,
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", "strict").strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, UnicodeError) as e:
        raise SnapshotDenied("GIT_OPERATION_UNAVAILABLE_OR_INVALID") from e


def bound_repo(root: str | Path, repository: str, project_id: str) -> Path:
    if not isinstance(repository, str) or not REPO.fullmatch(repository):
        raise SnapshotDenied("REPOSITORY_SCOPE_INVALID")
    if not isinstance(project_id, str) or not TOKEN.fullmatch(project_id):
        raise SnapshotDenied("PROJECT_SCOPE_INVALID")
    folder = Path(root).resolve(strict=True)
    if not folder.is_dir() or Path(git(folder, "rev-parse", "--show-toplevel")).resolve() != folder:
        raise SnapshotDenied("GIT_ROOT_MISMATCH")
    remote = git(folder, "remote", "get-url", "origin")
    canonical = repository + ".git"
    approved = {
        "https://github.com/" + repository,
        "https://github.com/" + canonical,
        "git@github.com:" + canonical,
        "ssh://git@github.com/" + canonical,
    }
    if remote not in approved:
        raise SnapshotDenied("ORIGIN_REPOSITORY_MISMATCH")
    return folder


def snapshot_ref(project_id: str, checkpoint_id: str) -> str:
    if not TOKEN.fullmatch(project_id) or not TOKEN.fullmatch(checkpoint_id):
        raise SnapshotDenied("SNAPSHOT_ID_INVALID")
    return f"refs/acg/snapshots/{project_id}/{checkpoint_id}"


def inspect(root: str | Path, repository: str, project_id: str) -> dict:
    folder = bound_repo(root, repository, project_id)
    head = git(folder, "rev-parse", "--verify", "HEAD")
    if not HEX.fullmatch(head) or git(folder, "cat-file", "-t", head) != "commit":
        raise SnapshotDenied("HEAD_NOT_COMMIT")
    # Include untracked files; never call a dirty tree a complete recovery snapshot.
    dirty = bool(git(folder, "status", "--porcelain=v1", "--untracked-files=all"))
    return {
        "schema": "ACG_LOCAL_GIT_SNAPSHOT_V01", "repository": repository,
        "project_id": project_id, "head_sha": head,
        "worktree_clean": not dirty,
        "includes_uncommitted_files": False,
        "captures_operating_database_or_services": False,
        "cloud_backup_performed": False,
        "github_actions_triggered": False,
        "release_authorized": False,
    }


def checkpoint(root: str | Path, repository: str, project_id: str,
               checkpoint_id: str, expected_head: str, approve_write: bool = False) -> dict:
    report = inspect(root, repository, project_id)
    if not isinstance(expected_head, str) or not HEX.fullmatch(expected_head):
        raise SnapshotDenied("EXPECTED_HEAD_INVALID")
    if report["head_sha"] != expected_head:
        raise SnapshotDenied("HEAD_CHANGED")
    if not report["worktree_clean"]:
        raise SnapshotDenied("UNCOMMITTED_OR_UNTRACKED_CHANGES_NOT_CAPTURED")
    ref = snapshot_ref(project_id, checkpoint_id)
    folder = bound_repo(root, repository, project_id)
    # A ref is not a validation receipt, not a backup on another machine.
    try:
        existing = git(folder, "rev-parse", "--verify", ref)
    except SnapshotDenied:
        existing = None
    if existing is not None:
        raise SnapshotDenied("SNAPSHOT_ALREADY_EXISTS_NO_OVERWRITE")
    if not approve_write:
        return {**report, "checkpoint_ref": ref, "status": "PREVIEW_ONLY_NO_WRITE"}
    git(folder, "update-ref", "--create-reflog", ref, expected_head, ZERO)
    if git(folder, "rev-parse", "--verify", ref) != expected_head:
        raise SnapshotDenied("REF_VERIFICATION_FAILED")
    return {**report, "checkpoint_ref": ref,
            "status": "LOCAL_COMMITTED_HEAD_REF_CREATED_NOT_CI_VERIFIED"}


def recover_preview(root: str | Path, repository: str, project_id: str,
                    checkpoint_id: str) -> dict:
    folder = bound_repo(root, repository, project_id)
    ref = snapshot_ref(project_id, checkpoint_id)
    commit = git(folder, "rev-parse", "--verify", ref)
    if not HEX.fullmatch(commit) or git(folder, "cat-file", "-t", commit) != "commit":
        raise SnapshotDenied("SNAPSHOT_REF_NOT_A_COMMIT")
    return {"schema": "ACG_LOCAL_GIT_SNAPSHOT_V01", "repository": repository,
            "checkpoint_ref": ref, "checkpoint_sha": commit,
            "status": "RECOVERY_PREVIEW_NO_MUTATION",
            "next_step": "Review current changes, then create a separate recovery branch from the pinned SHA using authorized Git workflow; never reset the operating tree automatically.",
            "snapshot_is_ci_pass": False, "operating_state_restored": False}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("inspect", "checkpoint", "recover-preview"))
    p.add_argument("--repo-root", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--project-id", required=True)
    p.add_argument("--checkpoint-id")
    p.add_argument("--expected-head")
    p.add_argument("--approve-write", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect(args.repo_root, args.repository, args.project_id)
        elif args.command == "checkpoint":
            if not args.checkpoint_id or not args.expected_head:
                raise SnapshotDenied("CHECKPOINT_ID_AND_HEAD_REQUIRED")
            result = checkpoint(args.repo_root, args.repository, args.project_id,
                                args.checkpoint_id, args.expected_head, args.approve_write)
        else:
            if not args.checkpoint_id:
                raise SnapshotDenied("CHECKPOINT_ID_REQUIRED")
            result = recover_preview(args.repo_root, args.repository,
                                     args.project_id, args.checkpoint_id)
        ok = True
    except (SnapshotDenied, OSError, ValueError) as exc:
        result = {"status": "DENIED_OR_UNKNOWN", "reason": str(exc)}
        ok = False
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
