"""UCIE SkillBook 001: first-party bounded, non-recursive scandir recipe.

This is a reusable code example, not a UCIE private-file collection worker.
Only callers who independently authorize the target directory may invoke it.
The UCIE browser/catalog never calls this function; tests use temp fixtures.
"""
from __future__ import annotations

import os
from pathlib import Path

MAX_ENTRIES = 128


class BoundedScandirError(ValueError):
    """Invalid or over-budget owner-selected directory, fail-closed."""


def bounded_regular_file_names(approved_directory: str | Path,
                               *, max_entries: int = MAX_ENTRIES) -> tuple[str, ...]:
    """Return sorted regular-file *names*, never file contents or paths.

    - A caller-selected absolute directory is mandatory; no implicit cwd.
    - No recursion, no child symlink traversal, and no opening file contents.
    - Count ALL observed entries against a fixed budget, including links/dirs.
    - The context manager closes the iterator on success, error or early exit.
    - Not a security sandbox: concurrent replacement/TOCTOU is outside scope.
    """
    if (not isinstance(approved_directory, (str, Path))
            or isinstance(approved_directory, str)
            and (not approved_directory or len(approved_directory) > 4096)
            or type(max_entries) is not int or not 1 <= max_entries <= MAX_ENTRIES):
        raise BoundedScandirError("invalid owner-selected directory or scan budget")
    directory = Path(approved_directory)
    if not directory.is_absolute():
        raise BoundedScandirError("absolute owner-selected directory required")
    # A symlinked ancestor would undermine the caller's choice of location.
    if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
           for p in (directory, *directory.parents)):
        raise BoundedScandirError("redirected directory path blocked")
    if not directory.is_dir():
        raise BoundedScandirError("owner-selected directory unavailable")
    names = []
    seen = 0
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                seen += 1
                if seen > max_entries:
                    raise BoundedScandirError("directory entry budget exhausted")
                if not entry.is_symlink() and entry.is_file(follow_symlinks=False):
                    # DirEntry metadata may be stale after a filesystem race.
                    names.append(entry.name)
    except OSError as exc:
        raise BoundedScandirError("directory enumeration unavailable") from exc
    return tuple(sorted(names))
