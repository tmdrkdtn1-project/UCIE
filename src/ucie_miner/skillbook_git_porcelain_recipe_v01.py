"""UCIE SkillBook 002: strict, bounded Git porcelain v1 -z summary.

Parse *supplied bytes only*. Never invoke git, inspect a repository,
resolve a path, or reveal filenames. This is NOT a safe-command runner,
malware scanner, authorization decision, or repository status oracle.

Official contract: git/git v2.51.0 Documentation/git-status.adoc,
"Porcelain Format Version 1", including -z rename/copy field ordering.
"""
from __future__ import annotations

SCHEMA = "UCIE_SKILLBOOK_GIT_PORCELAIN_V1_Z_SUMMARY_V01"
MAX_ENTRIES = 64
MAX_BYTES = 8192
MAX_PATH_BYTES = 1024
_TRACKED_CHARS = frozenset(b" MADRCUT")


class PorcelainSummaryError(ValueError):
    """Invalid, incomplete, ambiguous, or over-budget Git status bytes."""


def _opaque_relative_name(name: bytes) -> None:
    """Verify the bounded shape without decoding or returning any filename."""
    if (not name or len(name) > MAX_PATH_BYTES
            or name.startswith(b"/") or b"\\" in name
            or b":" in name[:2]
            or any(part in (b"", b".", b"..") for part in name.split(b"/"))):
        raise PorcelainSummaryError("unsafe or ambiguous opaque path component")


def summarize_porcelain_v1_z(
    payload: bytes, *, max_entries: int = MAX_ENTRIES
) -> dict:
    """Count up to 64 supplied porcelain-v1 NUL-terminated entries.

    Each ordinary record: XY + space + opaque path + NUL.
    R/C records: XY + space + DESTINATION + NUL + SOURCE + NUL,
    per Git's documented -z reversed field order. Never print these names.
    No headers (-b), porcelain v2, line output, or unbounded status data.
    """
    if (type(payload) is not bytes
            or len(payload) > MAX_BYTES or type(max_entries) is not int
            or not 1 <= max_entries <= MAX_ENTRIES):
        raise PorcelainSummaryError("invalid supplied bytes or fixed budget")
    counts = {
        "tracked_changed": 0,
        "renamed": 0,
        "copied": 0,
        "conflicted": 0,
        "untracked": 0,
        "ignored": 0,
    }
    if not payload:
        return _report(counts, 0)
    if not payload.endswith(b"\x00"):
        raise PorcelainSummaryError("incomplete NUL-delimited status record")
    fields = payload[:-1].split(b"\x00")
    i, entries = 0, 0
    while i < len(fields):
        record = fields[i]
        i += 1
        if len(record) < 4 or record[2:3] != b" ":
            raise PorcelainSummaryError("invalid porcelain v1 status header")
        xy = record[:2]
        name = record[3:]
        _opaque_relative_name(name)
        if xy == b"??":
            category = "untracked"
        elif xy == b"!!":
            category = "ignored"
        elif (xy == b"  " or any(c not in _TRACKED_CHARS for c in xy)):
            raise PorcelainSummaryError("unknown or unsupported Git XY status")
        elif xy in (b"DD", b"AA") or b"U" in xy:
            category = "conflicted"
        elif b"R" in xy:
            category = "renamed"
        elif b"C" in xy:
            category = "copied"
        else:
            category = "tracked_changed"
        if category in ("renamed", "copied"):
            if i >= len(fields):
                raise PorcelainSummaryError("missing second -z rename/copy path")
            _opaque_relative_name(fields[i])
            i += 1
        counts[category] += 1
        entries += 1
        if entries > max_entries:
            raise PorcelainSummaryError("total Git status entry budget exceeded")
    return _report(counts, entries)


def _report(counts: dict[str, int], entries: int) -> dict:
    return {
        "schema": SCHEMA,
        "total_entries": entries,
        "counts": counts,
        "untrusted_path_bytes_discarded": True,
        "filenames_or_content_returned": False,
        "git_process_executed": False,
        "repository_or_directory_scanned": False,
        "source_code_executed": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "other_project_access": False,
        "security_boundary_certified": False,
    }
