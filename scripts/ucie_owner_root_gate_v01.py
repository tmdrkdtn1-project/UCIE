"""Single fail-closed owner Windows root gate for a future, explicit relocation.

This module never creates an opt-in, changes a task or moves operating data.
Existing D:/UCIE launch behaviour remains the default. The relocated root
requires an exact owner-installed marker AND full runtime before any import.
"""
from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath
import stat

LEGACY = PureWindowsPath(r"D:\UCIE")
TARGET = PureWindowsPath(r"D:\UCIE_PROJECT\UCIE")
MARKER = ".ucie_owner_runtime_opt_in_v01"
MARKER_BYTES = b"UCIE_OWNER_RELOCATED_RUNTIME_OPT_IN_V01\n"


class OwnerRootError(ValueError):
    pass


def classify_root(value: str, *, platform: str, relocated: bool) -> str:
    """Pure path policy; neither existence nor an active C40 is implied."""
    if platform != "nt":
        if relocated:
            raise OwnerRootError("RELOCATION_NOT_WINDOWS")
        return "LEGACY_NONWINDOWS_TEST_ONLY"
    path = PureWindowsPath(value)
    if path == LEGACY and not relocated:
        return "LEGACY"
    if path == TARGET and relocated:
        return "RELOCATED_CONDITIONALLY"
    raise OwnerRootError("ROOT_NOT_APPROVED")


def _direct(path: Path, *, directory: bool | None = None) -> bool:
    """Every ancestor must also be direct: no junctioned venv or runtime."""
    try:
        meta0 = path.lstat()
        for node in (path, *path.parents):
            meta = node.lstat()
            if (stat.S_ISLNK(meta.st_mode)
                    or getattr(meta, "st_file_attributes", 0) & 0x400):
                return False
        if directory is True:
            return stat.S_ISDIR(meta0.st_mode)
        if directory is False:
            return stat.S_ISREG(meta0.st_mode)
        return True
    except OSError:
        return False


def require_owner_runtime_root(root: Path, *, relocated: bool = False,
                               platform: str | None = None) -> str:
    """Allow legacy by default; relocated only after owner runtime readiness.

    Neither function modifies the filesystem. The opt-in marker must be created
    separately by the owner after an offline recovery/Task/C40 plan is approved.
    The marker is a local explicit-consent gate, NOT proof of tunnel health.
    """
    platform = os.name if platform is None else platform
    mode = classify_root(str(root), platform=platform, relocated=relocated)
    if platform != "nt":
        return mode
    if not _direct(root, directory=True):
        raise OwnerRootError("OWNER_ROOT_INDIRECT_OR_MISSING")
    if mode == "LEGACY":
        return mode
    if not _direct(root.parent, directory=True):
        raise OwnerRootError("RELOCATED_PARENT_INDIRECT_OR_MISSING")
    requirements = (
        (root / ".git", True),
        (root / ".venv" / "Scripts" / "python.exe", False),
        (root / "src" / "ucie_miner", True),
        (root / "scripts", True),
        (root / "runtime", True),
        (root / MARKER, False),
    )
    if any(not _direct(p, directory=d) for p, d in requirements):
        raise OwnerRootError("RELOCATED_RUNTIME_INCOMPLETE")
    marker = root / MARKER
    try:
        if marker.stat().st_size != len(MARKER_BYTES) or marker.read_bytes() != MARKER_BYTES:
            raise OwnerRootError("RELOCATION_MARKER_INVALID")
    except OSError as exc:
        raise OwnerRootError("RELOCATION_MARKER_UNREADABLE") from exc
    return "RELOCATED_CONDITIONALLY"
