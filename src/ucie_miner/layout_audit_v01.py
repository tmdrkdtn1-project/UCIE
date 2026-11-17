"""UCIE-only read-only layout, Git and cache audit (migration is NEVER performed).

Only inspects a confirmed UCIE checkout. It does not look in D:\\ root,
UCIE_DATA, UCIE_PREVIEW, any unrelated project, or any operating SQLite
contents. No cleanup, shell commands, task edits, network, or Git mutation.
Owner must separately review absolute-path services before moving live roots.
"""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess

SCHEMA = "UCIE_LAYOUT_GIT_LIGHTWEIGHT_READONLY_V01"
TARGET_PARENT = r"D:\UCIE_PROJECT"
TARGET_CODE = r"D:\UCIE_PROJECT\UCIE"
SOURCE_FOLDERS = ("scripts", "src/ucie_miner", "tests", ".github/workflows")
SCANNABLE_SUFFIXES = frozenset((".py", ".ps1", ".psm1", ".cmd", ".bat", ".yml", ".yaml"))
CANDIDATE_CACHES = ("__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache")
PROTECTED = (".git", ".venv", "runtime", ".ucie_bridge_state", "docs",
             "scripts", "src", "tests")
MAX_SOURCE_FILES = 900
MAX_SOURCE_BYTES = 16_000_000
MAX_CACHE_FILES = 8000
MAX_STATUS_BYTES = 2_000_000
PATTERNS = {
    "live_root": re.compile(r"D:\\UCIE(?![A-Z0-9_])", re.IGNORECASE),
    "data_root": re.compile(r"D:\\UCIE_DATA\b", re.IGNORECASE),
    "preview_root": re.compile(r"D:\\UCIE_PREVIEW\b", re.IGNORECASE),
}


class LayoutAuditError(ValueError):
    """The UCIE-only read-only audit cannot safely certify this checkout."""


def _indirect(path: Path) -> bool:
    junction = getattr(path, "is_junction", None)
    return path.is_symlink() or (junction is not None and junction())


def _checked_root(root: Path) -> Path:
    if not isinstance(root, Path) or not root.is_dir() or _indirect(root):
        raise LayoutAuditError("direct UCIE repository directory required")
    resolved = root.resolve(strict=True)
    if resolved.name.casefold() != "ucie" or _indirect(resolved):
        raise LayoutAuditError("UCIE-only repository name required")
    meta = resolved / ".git"
    if _indirect(meta) or not meta.is_dir():
        raise LayoutAuditError("in-root non-indirect .git directory required")
    # Owner runtime safety: inspect these path types, never their contents.
    for basename in (".venv", "runtime", ".ucie_bridge_state"):
        item = resolved / basename
        if _indirect(item):
            raise LayoutAuditError("indirected owner state path blocked")
    return resolved


def _git_status(root: Path, *, fast: bool) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0",
                "GIT_EXTERNAL_DIFF": "0", "GIT_ATTR_NOSYSTEM": "1"})
    cmd = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
           "-c", "core.untrackedCache=false", "-C", str(root), "status",
           "--porcelain=v1", "-z",
           "--untracked-files=no" if fast else "--untracked-files=normal"]
    try:
        p = subprocess.run(cmd, check=False, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=25, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LayoutAuditError("bounded first-party Git status unavailable") from exc
    if p.returncode or len(p.stdout) > MAX_STATUS_BYTES:
        raise LayoutAuditError("Git status failed closed or exceeded byte limit")
    parts = p.stdout.split(b"\0")
    groups: Counter[str] = Counter()
    modified = untracked = other = 0
    i = 0
    while i < len(parts):
        raw = parts[i]
        i += 1
        if not raw:
            continue
        if len(raw) < 4 or raw[2:3] != b" ":
            raise LayoutAuditError("unexpected Git porcelain v1 output")
        code = raw[:2].decode("ascii")
        path = raw[3:].decode("utf-8", "surrogateescape")
        if path.startswith(("/", "\\")) or ".." in path.replace("\\", "/").split("/"):
            raise LayoutAuditError("path escaped UCIE checkout")
        group = path.replace("\\", "/").split("/")[0]
        groups[group] += 1
        if code == "??":
            untracked += 1
        elif "M" in code or "A" in code or "D" in code:
            modified += 1
        else:
            other += 1
        if "R" in code or "C" in code:
            # In -z format Git reports the second rename/copy path separately.
            if i >= len(parts) or not parts[i]:
                raise LayoutAuditError("missing Git rename/copy peer path")
            i += 1
    return {
        "mode": "FAST_TRACKED_ONLY" if fast else "FULL_STATUS",
        "tracked_changed_records": modified,
        "other_tracked_records": other,
        "untracked_records": None if fast else untracked,
        "untracked_scan_skipped": bool(fast),
        "counts_by_ucie_subdir": dict(sorted(groups.items())),
        "working_tree_clean_certified": not fast and (modified + other + untracked == 0),
        "git_history_compacted_or_rewritten": False,
        "git_index_written": False,
    }


def _source_dependencies(root: Path) -> dict:
    counts: Counter[str] = Counter()
    files: dict[str, list[str]] = {name: [] for name in PATTERNS}
    scanned = used_bytes = 0
    truncated = False
    for folder in SOURCE_FOLDERS:
        base = root / folder
        if _indirect(base):
            raise LayoutAuditError("indirect source folder forbidden")
        if not base.exists():
            continue
        if not base.is_dir():
            raise LayoutAuditError("source folder must be a directory")
        for p in sorted(base.iterdir()):
            if _indirect(p):
                truncated = True
                continue
            if not p.is_file() or p.suffix.casefold() not in SCANNABLE_SUFFIXES:
                continue
            size = p.stat().st_size
            if (scanned >= MAX_SOURCE_FILES or size > 200_000
                    or used_bytes + size > MAX_SOURCE_BYTES):
                truncated = True
                continue
            used_bytes += size
            scanned += 1
            try:
                source = p.read_text("utf-8")
            except (OSError, UnicodeError):
                truncated = True
                continue
            rel = p.relative_to(root).as_posix()
            for label, pattern in PATTERNS.items():
                n = len(pattern.findall(source))
                if n:
                    counts[label] += n
                    files[label].append(rel)
    return {
        "scanned_ucie_source_files": scanned,
        "source_scan_truncated_or_unreadable": truncated,
        "literal_path_reference_counts": {k: counts[k] for k in PATTERNS},
        "affected_ucie_source_files": {k: sorted(v) for k, v in files.items()},
        "scheduled_task_and_mcp_binding_verified": False,
        "safe_to_move_live_root": False,
    }


def _cache_dir_stats(path: Path) -> tuple[int, int, bool]:
    """Count only well-known cache subtrees; never follow any symlink."""
    if _indirect(path) or not path.is_dir():
        return 0, 0, True
    stack = [path]
    files = bytes_total = 0
    safe = True
    while stack:
        current = stack.pop()
        for item in current.iterdir():
            if _indirect(item):
                safe = False
                continue
            if item.is_dir():
                stack.append(item)
            elif item.is_file():
                files += 1
                bytes_total += item.stat().st_size
            else:
                safe = False
            if files > MAX_CACHE_FILES:
                return files, bytes_total, False
    return files, bytes_total, safe


def _cache_preview(root: Path) -> dict:
    # Only opt-in cache classifications inside UCIE, never runtime/venv/git.
    bases = [root, root / "scripts", root / "tests",
             root / "src" / "ucie_miner"]
    proposed = []
    for base in bases:
        if _indirect(base):
            raise LayoutAuditError("indirect source/cache parent blocked")
        if not base.is_dir():
            continue
        for name in CANDIDATE_CACHES:
            d = base / name
            if not d.exists() and not _indirect(d):
                continue
            n, size, safe = _cache_dir_stats(d)
            proposed.append({"ucie_relative_path": d.relative_to(root).as_posix(),
                             "file_count": n, "estimated_bytes": size,
                             "direct_regular_files_only": safe,
                             "approved_for_deletion": False})
    return {
        "read_only_cache_candidates": proposed,
        "cache_files_observed": sum(x["file_count"] for x in proposed),
        "cache_bytes_observed": sum(x["estimated_bytes"] for x in proposed),
        "cache_removed_or_quarantined": False,
        "cache_delete_approval_granted": False,
    }


def inspect_ucie_layout(root: Path, *, fast_git: bool = False) -> dict:
    """Read-only UCIE checkout inventory, no D:\\ sibling discovery or writes."""
    if type(fast_git) is not bool:
        raise LayoutAuditError("fast_git must be exact boolean")
    repo = _checked_root(root)
    git = _git_status(repo, fast=fast_git)
    refs = _source_dependencies(repo)
    caches = _cache_preview(repo)
    return {
        "schema": SCHEMA,
        "status": "UCIE_LAYOUT_PREVIEW_ONLY__LIVE_MIGRATION_BLOCKED",
        "source_root": str(repo),
        "proposed_parent": TARGET_PARENT,
        "proposed_source_repo": TARGET_CODE,
        "other_drive_roots_or_projects_scanned": False,
        "ucie_data_or_preview_presence_verified": False,
        "operating_sqlite_opened": False,
        "owner_runtime_moved": False,
        "source_files_modified": False,
        "operating_db_writes": 0,
        "network_requests": 0,
        "scheduler_changed": False,
        "mcp_tunnel_restarted": False,
        "git_mutations": 0,
        "customer_release_authorized": False,
        "plan": [
            "KEEP D:\\UCIE, UCIE_DATA and UCIE_PREVIEW at original paths until owner task and MCP binding inventories are approved",
            "CREATE D:\\UCIE_PROJECT only after an owner-path rights check; initially use it for isolated QA and owner-reviewed archives",
            "PIN active scheduler/MCP scripts, runtime databases and opt-in receipts, virtualenv and working source hashes",
            "REVIEW 230 existing dirty source and untracked files individually; never mistake untracked files for disposable caches",
            "MAKE path-compatibility patches and independent Windows regression tests before a single coordinated cutover",
            "MIGRATE only by owner-approved atomic cutover with service stop, backup, rollback, independent task/bridge/DB validation",
        ],
        "git": git,
        "path_dependencies": refs,
        "cache": caches,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="UCIE-only read-only workspace/Git/cache inventory")
    parser.add_argument("--fast-git", action="store_true",
                        help="Skip untracked scan; NEVER certifies clean working tree")
    args = parser.parse_args()
    # The source-controlled entrypoint itself determines the checkout, not an
    # arbitrary caller path. On Windows the only authorized live root is D:\UCIE;
    # after a separately approved cutover D:\UCIE_PROJECT\UCIE also qualifies.
    repo = Path(__file__).resolve().parents[2]
    if os.name == "nt" and str(repo).casefold() not in (
            r"d:\ucie", TARGET_CODE.casefold()):
        print(json.dumps({"schema": SCHEMA,
                          "status": "UCIE_LAYOUT_ROOT_NOT_APPROVED_FAIL_CLOSED"}))
        return 2
    try:
        out = inspect_ucie_layout(repo, fast_git=args.fast_git)
    except (LayoutAuditError, OSError, UnicodeError, ValueError):
        print(json.dumps({"schema": SCHEMA,
                          "status": "UCIE_LAYOUT_PREVIEW_FAIL_CLOSED",
                          "operating_db_writes": 0,
                          "migration_executed": False}, sort_keys=True))
        return 2
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
