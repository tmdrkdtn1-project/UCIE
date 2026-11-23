"""Stage ONE owner-approved UCIE source module into the isolated development tree.

Unlike a comparison/audit, --mode apply performs a real local source-only
integration step: exactly one reviewed, original-only first-party module is
written exclusively to the NEW development worktree. It is never git-added,
committed, pushed, imported or executed here. No automatic test/data/Task/C40
migration. Actual owner approval is mandatory for the exact module index.
"""
from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import stat

SCHEMA = "UCIE_OWNER_ONE_SOURCE_MODULE_STAGE_V01"
NEW_ROOT = r"D:\UCIE_PROJECT\UCIE"
OLD_ROOT = r"D:\UCIE"
PACKET = (r"D:\UCIE_PROJECT\UCIE_OWNER_REVIEW"
          r"\UCIE_OWNER_MODULE_REVIEW_deb3393e06aa.json")
APPROVAL_PREFIX = "APPROVE_UCIE_ONE_MODULE_"
MAX_PACKET_BYTES = 2_000_000
OWNER_PACKET_SCHEMA = "UCIE_OWNER_PRIVATE_MODULE_CONTRACT_PACKET_V01"


class StageOneError(ValueError):
    """Fixed fail-closed messages; do not propagate private source names."""


def _load_stage_audit(stage: Path):
    """Load the *trusted new checkout* guard, never an original module."""
    path = stage / "src" / "ucie_miner" / "layout_audit_v01.py"
    spec = importlib.util.spec_from_file_location("_ucie_integrate_layout", path)
    if spec is None or spec.loader is None:
        raise StageOneError("UCIE staged auditor missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _module_path_name(layout, relative: str) -> str:
    if (type(relative) is not str or
            layout._ucie_code_scope(relative) != "src" or
            not relative.endswith(".py")):
        raise StageOneError("UCIE owner packet module outside first-party scope")
    stem = relative[4:-3].replace("/", ".")
    if stem.endswith(".__init__"):
        stem = stem[:-len(".__init__")]
    if stem not in ("ucie_miner", "ucie_public") and not stem.startswith(
            ("ucie_miner.", "ucie_public.")):
        raise StageOneError("UCIE owner packet module name outside scope")
    return stem


def _require_exact_per_module_approval(mode: str, index: int,
                                        approval: str) -> None:
    """Allow preview by default; explicit one-module approval for any write."""
    if (type(mode) is not str or mode not in ("preview", "apply")
            or type(index) is not int or not 1 <= index <= 8
            or type(approval) is not str):
        raise StageOneError("UCIE staging operation outside one-module scope")
    if mode == "apply" and approval != (
            APPROVAL_PREFIX + f"{index:02d}" + "_TO_NEW_DEV_ROOT"):
        raise StageOneError("UCIE selected module owner approval missing")


def _read_priority_packet(path: Path, layout) -> list[dict]:
    """Use only the owner-created private packet, never GitHub or connectors."""
    if (not path.is_file() or layout._indirect(path) or
            layout._indirect(path.parent)):
        raise StageOneError("UCIE private owner packet unavailable")
    st = path.lstat()
    if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1
            or st.st_size > MAX_PACKET_BYTES):
        raise StageOneError("UCIE private owner packet unsafe")
    raw = path.read_bytes()
    if len(raw) != st.st_size:
        raise StageOneError("UCIE private owner packet changed")
    try:
        packet = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise StageOneError("UCIE private packet encoding") from exc
    if (type(packet) is not dict or
            packet.get("schema") != OWNER_PACKET_SCHEMA or
            packet.get("status") != "PRIVATE_LOCAL_REVIEW_ONLY__NO_MIGRATION" or
            packet.get("do_not_upload_or_paste") is not True or
            packet.get("contains_original_code_bodies") is not False):
        raise StageOneError("UCIE private packet identity mismatch")
    cards = packet.get("module_cards")
    if type(cards) is not list or len(cards) != 20:
        raise StageOneError("UCIE private packet source count changed")
    p1, known = [], set()
    for card in cards:
        if type(card) is not dict:
            raise StageOneError("UCIE invalid local module card")
        relative = card.get("original_relative_src_path")
        module = _module_path_name(layout, relative)
        if (module != card.get("original_module_name") or
                relative in known or
                card.get("current_action") != "K0_HOLD"):
            raise StageOneError("UCIE owner module path or hold mismatch")
        known.add(relative)
        if card.get("priority") == "P1_DIRECT_SOURCE_CONTRACT_REVIEW":
            p1.append(card)
        elif card.get("priority") not in (
                "P2_ROOT_SYMBOL_AMBIGUITY_HOLD",
                "P3_UNOBSERVED_HOLD"):
            raise StageOneError("UCIE owner packet priority unknown")
    if len(p1) != 8 or len({c["original_module_name"] for c in p1}) != 8:
        raise StageOneError("UCIE P1 source module count mismatch")
    return sorted(p1, key=lambda c: c["original_module_name"])


def _read_one_source(original: Path, name: str, layout) -> bytes:
    data = layout._read_owner_ucie_code_bounded(original, name)
    if data is None or not data:
        raise StageOneError("UCIE original first-party module unreadable")
    try:
        ast.parse(data.decode("utf-8-sig"), filename="<UCIE-original-private>")
    except (SyntaxError, UnicodeError, ValueError, RecursionError, MemoryError) as exc:
        raise StageOneError("UCIE original module syntax unverified") from exc
    return data


def _validate_absent_target(stage: Path, relative: str, layout) -> Path:
    """Direct parents only, no existing destination, no overwrite or mkdir."""
    target = stage
    parts = relative.split("/")
    for part in parts[:-1]:
        target = target / part
        if not target.is_dir() or layout._indirect(target):
            raise StageOneError("UCIE stage source directory unavailable")
    target = target / parts[-1]
    try:
        target.lstat()
    except FileNotFoundError:
        pass
    else:
        raise StageOneError("UCIE stage module already exists")
    return target


def _exclusive_copy(source_bytes: bytes, target: Path, layout) -> None:
    """One private local staged file; leave any interrupted artifact for review."""
    if not target.parent.is_dir() or layout._indirect(target.parent):
        raise StageOneError("UCIE stage destination directory unsafe")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(target, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(source_bytes)
        stream.flush()
        os.fsync(stream.fileno())
    if (layout._indirect(target) or target.lstat().st_nlink != 1
            or sha256(target.read_bytes()).digest() !=
            sha256(source_bytes).digest()):
        raise StageOneError("UCIE staged source byte verification failed")


def _checks(stage: Path, original: Path, layout,
            expected_head: str, module_index: int) -> tuple[Path, bytes]:
    if (type(expected_head) is not str or
            re.fullmatch(r"[0-9a-f]{40}", expected_head) is None or
            type(module_index) is not int or not 1 <= module_index <= 8):
        raise StageOneError("UCIE exact stage lease or one-module index invalid")

    # Existing proven UCIE Git identity and CRLF-only worktree guard.
    layout.compare_original_ucie_git_to_stage(
        stage, original, platform=os.name)
    sha = layout._git_metadata_bytes(stage, "rev-parse", "HEAD").decode(
        "ascii").strip().casefold()
    if sha != expected_head:
        raise StageOneError("UCIE stage SHA pin mismatch")

    priority = _read_priority_packet(Path(PACKET), layout)
    relative = priority[module_index - 1]["original_relative_src_path"]
    status = layout._parse_original_status_paths(layout._git_metadata_bytes(
        original, "status", "--porcelain=v1", "-z", "--untracked-files=all"))
    if ("untracked", relative) not in status:
        raise StageOneError("UCIE selected module not original-only untracked")

    tracked = layout._parse_tracked_git_paths(
        layout._git_metadata_bytes(stage, "ls-files", "-z"))
    if relative in tracked:
        raise StageOneError("UCIE stage already tracks selected source module")
    target = _validate_absent_target(stage, relative, layout)
    data = _read_one_source(original, relative, layout)
    return target, data


def stage_one(*, expected_head: str, module_index: int,
              mode: str = "preview", approval: str = "") -> dict:
    _require_exact_per_module_approval(mode, module_index, approval)
    if os.name != "nt":
        raise StageOneError("UCIE one-module source stage requires Windows")
    stage, original = Path(NEW_ROOT), Path(OLD_ROOT)
    if str(stage).casefold() != r"d:\ucie_project\ucie":
        raise StageOneError("UCIE stage path mismatch")
    layout = _load_stage_audit(stage)
    target, data = _checks(stage, original, layout, expected_head, module_index)

    result = {
        "schema": SCHEMA,
        "mode": mode,
        "selected_firstparty_module_count": 1,
        "candidate_source_syntax_checked": True,
        "original_content_or_name_returned": False,
        "original_code_imported_or_executed": False,
        "source_transmitted_or_git_pushed": False,
        "operating_original_or_db_changed": False,
        "stage_git_index_modified": False,
        "stage_file_written": False,
        "code_behavior_or_tests_verified": False,
        "source_module_state": "K0_HOLD_UNTIL_LOCAL_SOURCE_REVIEW",
        "live_cutover_authorized": False,
    }
    if mode == "preview":
        result["status"] = "ONE_MODULE_STAGE_PREVIEW__NO_WRITES"
        return result

    before_original = layout._git_metadata_bytes(
        original, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    before_stage = layout._git_metadata_bytes(
        stage, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    # Do not apply after an unobserved source/Git change.
    again_target, again_data = _checks(
        stage, original, layout, expected_head, module_index)
    if (again_target != target or sha256(again_data).digest() !=
            sha256(data).digest() or
            before_original != layout._git_metadata_bytes(
                original, "status", "--porcelain=v1", "-z",
                "--untracked-files=all") or
            before_stage != layout._git_metadata_bytes(
                stage, "status", "--porcelain=v1", "-z",
                "--untracked-files=all")):
        raise StageOneError("UCIE source staging inputs changed")
    _exclusive_copy(data, target, layout)
    result["stage_file_written"] = True
    result["status"] = "ONE_ORIGINAL_MODULE_STAGED_UNTRACKED__REVIEW_REQUIRED"
    result["source_module_state"] = "K0_STAGED_UNTESTED_HOLD"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=(
        "UCIE: stage one owner-approved first-party module, never execute it"))
    parser.add_argument("--mode", choices=("preview", "apply"),
                        default="preview")
    parser.add_argument("--module-index", type=int, default=1)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--approval", default="")
    args = parser.parse_args()
    try:
        result = stage_one(
            expected_head=args.expected_head,
            module_index=args.module_index,
            mode=args.mode,
            approval=args.approval)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (StageOneError, OSError, ValueError, UnicodeError, RuntimeError,
            KeyError, TypeError):
        # Never echo original module paths, secret content or exception text.
        print(json.dumps({
            "schema": SCHEMA, "status": "UCIE_STAGE_ONE_FAIL_CLOSED",
            "original_code_executed": False,
            "source_data_returned": False,
            "live_cutover_authorized": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
