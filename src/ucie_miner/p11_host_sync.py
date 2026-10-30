"""One-shot owner UCIE host P8 sync, exact source pin and no overwrite.

Only three first-party P11/P10 code paths from already-tested PR #150.
No checkout, git pull/reset, OS task registration, operational SQLite writes,
public network requests, signing, approval, or other project traversal.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile

BASE = "9f1adce92f1eaf13c306da9fe42538f4e619c907"
PIN = "b6a5244925bfe59cd3b64fe2a6bf2f9bedfd9d42"
# First-party P11 merged program is validated by exact Git *blob identity*;
# a subsequent docs-only/main commit cannot silently substitute a new engine.
P11_MERGED_BLOB = "45b753e1066fcaff10c35958cf05166ed00ab0f4"
FILES = (
    "src/ucie_miner/p11_improvement_gate.py",
    "src/ucie_miner/p11_closed_loop.py",
    "src/ucie_miner/runtime_pipeline.py",
)
STATUS = "UCIE_P8_PINNED_LOCAL_SURGICAL_SYNC_V1"


class P8SyncError(ValueError):
    pass


def _git(source: Path, *argv: str, content: bool = False) -> bytes:
    p = subprocess.run(
        ["git", "-C", str(source), *argv],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        timeout=20, check=False,
    )
    if p.returncode != 0:
        raise P8SyncError("pinned UCIE source git validation failed")
    return p.stdout if content else p.stdout.strip()


def _hex(data: bytes) -> str:
    return sha256(data).hexdigest()


def _same_python_source(actual: bytes | None, pinned: bytes) -> bool:
    """Accept only CRLF/LF transport spelling; never source-code drift.

    Git stores the canonical blob bytes while Windows core.autocrlf can
    materialize CRLF in a clean checkout. Keep the ORIGINAL actual bytes
    for backup/rollback; compare only narrowly normalized line endings.
    """
    if type(actual) is not bytes or type(pinned) is not bytes:
        return False
    if b"\x00" in actual or b"\x00" in pinned:
        return False
    if b"\r" in actual.replace(b"\r\n", b""):
        return False
    return actual.replace(b"\r\n", b"\n") == pinned



def _legacy_owner_quiet_source(original: bytes) -> bytes:
    """Reconstruct the user's exact five-hunk P11 quiet-backoff local delta.

    Reconstructing from the exact BASE Git blob, instead of trusting
    keywords or modifying user files, enables a safe three-way source merge.
    No fuzzy matching or arbitrary local-content promotion.
    """
    if type(original) is not bytes or b"\r" in original or b"\x00" in original:
        raise P8SyncError("unexpected historical P11 base bytes")
    edits = (
        (b"MIN_GET_INTERVAL = timedelta(minutes=5)\nRECIPES = {",
         b"MIN_GET_INTERVAL = timedelta(minutes=5)\n"
         b"# No new evidence for 30 minutes after >=10 successful GETs: cap redundant\n"
         b"# collection at one GET every 20 minutes; rotate approved sources unchanged.\n"
         b"# Any fetch failure retains the original 5-minute retry cooldown.\n"
         b"QUIET_AFTER = timedelta(minutes=30)\n"
         b"QUIET_GET_INTERVAL = timedelta(minutes=20)\n"
         b"QUIET_MIN_GETS = 10\nRECIPES = {"),
        (b'        previous = cursor["last_attempt_at"]\n'
         b'        if previous and now < _parse(previous) + MIN_GET_INTERVAL:',
         b'        previous = cursor["last_attempt_at"]\n'
         b'        # Source-neutral, no-new-evidence idle backoff. Reuse the existing\n'
         b'        # ledger/cursor only: NO schema migration, no extra API request.\n'
         b'        # Pending experiments and failed sources always use the base cadence.\n'
         b'        latest_new = conn.execute(\n'
         b'            "SELECT MAX(observed_at) FROM leads").fetchone()[0]\n'
         b'        pending = conn.execute(\n'
         b'            "SELECT COUNT(*) FROM leads WHERE reviewed=0").fetchone()[0]\n'
         b'        quiet = (\n'
         b'            cursor["last_attempt_failed"] == 0\n'
         b'            and cursor["total_public_gets"] >= QUIET_MIN_GETS\n'
         b'            and pending == 0\n'
         b'            and (latest_new is None or now >= _parse(latest_new) + QUIET_AFTER)\n'
         b'        )\n'
         b'        interval = QUIET_GET_INTERVAL if quiet else MIN_GET_INTERVAL\n'
         b'        if previous and now < _parse(previous) + interval:'),
        (b'                "public_api_gets_this_call": 0,\n'
         b'                "unverified_new_leads": 0, "auto_promoted": False,',
         b'                "public_api_gets_this_call": 0,\n'
         b'                "unverified_new_leads": 0,\n'
         b'                "quiet_collection_backoff": quiet,\n'
         b'                "interval_minutes": int(interval.total_seconds() // 60),\n'
         b'                "auto_promoted": False,'),
        (b'        good = conn.execute(\n'
         b'            "SELECT COUNT(*) FROM experience WHERE exact_equal=1").fetchone()[0]\n'
         b'    return {',
         b'        good = conn.execute(\n'
         b'            "SELECT COUNT(*) FROM experience WHERE exact_equal=1").fetchone()[0]\n'
         b'        last_new = conn.execute(\n'
         b'            "SELECT MAX(observed_at) FROM leads").fetchone()[0]\n'
         b'    now = datetime.now(timezone.utc)\n'
         b'    quiet = (\n'
         b'        cursor[2] == 0 and cursor[3] >= QUIET_MIN_GETS\n'
         b'        and unchecked == 0\n'
         b'        and (last_new is None or now >= _parse(last_new) + QUIET_AFTER)\n'
         b'    )\n'
         b'    interval = QUIET_GET_INTERVAL if quiet else MIN_GET_INTERVAL\n'
         b'    next_due = (\n'
         b'        _stamp(_parse(cursor[1]) + interval) if cursor[1] else None\n'
         b'    )\n'
         b'    return {'),
        (b'        "last_public_attempt_failed": bool(cursor[2]),\n'
         b'        "total_successful_public_gets": cursor[3],',
         b'        "last_public_attempt_failed": bool(cursor[2]),\n'
         b'        "quiet_collection_backoff": quiet,\n'
         b'        "effective_interval_minutes": int(interval.total_seconds() // 60),\n'
         b'        "next_public_get_due_utc": next_due,\n'
         b'        "total_successful_public_gets": cursor[3],'),
    )
    output = original
    for before, after in edits:
        if output.count(before) != 1:
            raise P8SyncError("historical P11 quiet patch no longer exact")
        output = output.replace(before, after, 1)
    return output

def _pinned(source: Path, path: str, rev: str) -> bytes:
    return _git(source, "show", f"{rev}:{path}", content=True)


def _safe_parent(root: Path, rel: str) -> Path:
    path = root
    for part in Path(rel).parts:
        path = path / part
        if path.is_symlink():
            raise P8SyncError("symbolic link in UCIE protected source path")
    return path


def _running(root: Path) -> int:
    target = _safe_parent(
        root, "runtime/ucie_internal_pending_queue_v1.sqlite3")
    if not target.exists():
        raise P8SyncError("P10 queue absent: no deployment proof")
    try:
        uri = target.as_uri() + "?mode=ro"
        # sqlite3.Connection context manager commits/rolls back but does
        # NOT close the OS handle. Closing is essential for Windows P10.
        with closing(sqlite3.connect(uri, uri=True, timeout=2)) as conn:
            conn.execute("PRAGMA query_only=ON")
            rows = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status='RUNNING'").fetchone()
            return rows[0]
    except sqlite3.Error as exc:
        raise P8SyncError("cannot verify idle P10 worker leases") from exc


def plan(source: Path, root: Path, *, allow_test_root: bool = False) -> tuple[list, dict]:
    source, root = source.resolve(), root.resolve()
    if not allow_test_root:
        if os.name != "nt":
            raise P8SyncError("real host mode requires Windows")
        if (str(source).casefold() != "d:\\ucie_release\\ucie"
                or str(root).casefold() != "d:\\ucie"):
            raise P8SyncError("dedicated UCIE Windows paths required")
    if (source == root or not (source / ".git").exists()
            or root.name.casefold() != "ucie"
            or not (root / "runtime").is_dir()):
        raise P8SyncError("release checkout and isolated UCIE runtime required")
    if _git(source, "status", "--porcelain", "--untracked-files=all"):
        raise P8SyncError("release checkout dirty: no overwrite")
    # HEAD can be the later PR with this installer; the exact PR #150 source
    # must remain its unchanged ancestor.
    _git(source, "merge-base", "--is-ancestor", PIN, "HEAD")
    pieces = []
    for rel in FILES:
        owner_quiet = None
        if rel.endswith("p11_closed_loop.py"):
            # Only this path contains the independently observed owner's
            # quiet-backoff delta. HEAD must have the exact combined blob;
            # the other two PR #150 code paths remain pinned separately.
            if (_git(source, "rev-parse", "HEAD:" + rel).decode("ascii")
                    != P11_MERGED_BLOB):
                raise P8SyncError("P11_MERGED_SOURCE_BLOB_CHANGED_NO_OVERWRITE")
            upstream = _pinned(source, rel, "HEAD")
        else:
            upstream = _pinned(source, rel, PIN)
        candidate = _safe_parent(source, rel)
        if not candidate.is_file() or not _same_python_source(
                candidate.read_bytes(), upstream):
            raise P8SyncError("source at pinned PR differs from checkout: " + rel)
        live = _safe_parent(root, rel)
        current = live.read_bytes() if live.is_file() else None
        if rel.endswith("p11_improvement_gate.py"):
            base = None
        else:
            base = _pinned(source, rel, BASE)
        if rel.endswith("p11_closed_loop.py"):
            owner_quiet = _legacy_owner_quiet_source(base)
        if (current is not None and
                not _same_python_source(current, upstream) and
                not (base is not None and _same_python_source(current, base)) and
                not (owner_quiet is not None and
                     _same_python_source(current, owner_quiet))):
            raise P8SyncError("LOCAL_P8_SOURCE_DRIFT_NO_OVERWRITE: " + rel)
        pieces.append((rel, live, current, upstream))
    result = {
        "schema": STATUS,
        "status": "EXACT_P8_HOST_SYNC_READY_NO_CHANGE",
        "pinned_main_source": PIN,
        "files_pinned": len(FILES),
        "owner_quiet_p11_base_merged_with_feedback": True,
        "p11_combined_source_git_blob": P11_MERGED_BLOB,
        "already_current_files": sum(_same_python_source(current, target)
                                     for _, _, current, target in pieces),
        "files_needing_update": sum(not _same_python_source(current, target)
                                    for _, _, current, target in pieces),
        "source_worktree_crlf_normalization_allowed": True,
        "only_eol_equivalent_local_files_preserved": [
            rel for rel, _, original, target in pieces
            if original is not None and original != target
            and _same_python_source(original, target)
        ],
        "files_to_update": [
            {"file": rel, "from_sha256": _hex(current)
             if current is not None else None,
             "to_sha256": _hex(target)}
            for rel, _, current, target in pieces
            if not _same_python_source(current, target)
        ],
        "outside_p8_files_modified": 0, "scheduler_modified": False,
        "public_miner_modified": False, "auto_promoted": False,
        "production_improvements_auto_applied": 0,
        "operating_db_writes": 0,
    }
    return pieces, result


def sync(source: Path, root: Path, *, apply: bool = False,
         allow_test_root: bool = False) -> dict:
    pieces, report = plan(source, root, allow_test_root=allow_test_root)
    if not apply:
        return report
    if all(_same_python_source(current, target)
           for _, _, current, target in pieces):
        return {**report, "status": "P8_HOST_ALREADY_PINNED_NO_CHANGE"}
    if _running(root):
        raise P8SyncError("P10_RUNNING_JOBS_RETRY_WHEN_IDLE_NO_CHANGE")
    # Read-only preflight before creating anything: source and all three
    # original files must still match the exact pinned bytes.
    for _, path, current, _ in pieces:
        if (path.read_bytes() if path.is_file() else None) != current:
            raise P8SyncError("concurrent UCIE source change: no overwrite")
    runtime = root / "runtime"
    label = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = _safe_parent(runtime, "p8_pinned_sync_backups")
    backup.mkdir(mode=0o700, exist_ok=True)
    receipt = Path(tempfile.mkdtemp(prefix=label + "_", dir=backup))
    # Backup existing files without ever deleting or replacing their originals.
    for rel, _, original, _ in pieces:
        if original is not None:
            (receipt / (Path(rel).name + ".previous")).write_bytes(original)
    updated = []
    try:
        for rel, path, original, target in pieces:
            if _same_python_source(original, target):
                continue
            if (path.read_bytes() if path.is_file() else None) != original:
                raise P8SyncError("concurrent change while applying")
            fd, temporary = tempfile.mkstemp(prefix=".ucie_p8_sync_", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(target)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
                updated.append((path, original))
            finally:
                Path(temporary).unlink(missing_ok=True)
        # Check installed files are exactly source-pinned; rollback otherwise.
        if any(not _same_python_source(path.read_bytes(), target)
               for _, path, _, target in pieces):
            raise P8SyncError("postflight source mismatch")
        audit = {
            "schema": STATUS,
            "status": "P8_HOST_PINNED_CODE_APPLIED_NOT_LIVE_WORKER_ATTESTED",
            "source_main_commit": PIN,
            "changed_files": [rel for rel, _, before, after
                              in pieces if not _same_python_source(before, after)],
            "backup_dir": str(receipt),
            "new_p11_learning_events_not_yet_observed": True,
            "task_registration_changed": False,
            "public_miner_modified": False,
            "production_code_auto_promoted": False,
            "existing_p11_experiences_rewritten": False,
            "existing_operating_miner_database_changed": False,
            "p8_source_sha256s": {rel: _hex(target)
                                  for rel, _, _, target in pieces},
        }
        (receipt / "receipt.json").write_text(
            json.dumps(audit, sort_keys=True, ensure_ascii=True) + "\n",
            encoding="utf-8")
    except BaseException:
        for path, original in reversed(updated):
            if original is None:
                path.unlink(missing_ok=True)
            else:
                fd, temporary = tempfile.mkstemp(
                    prefix=".ucie_p8_rollback_", dir=path.parent)
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(original)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, path)
                finally:
                    Path(temporary).unlink(missing_ok=True)
        raise

    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Explicit owner opt-in, exact three-file backup/sync")
    args = parser.parse_args()
    try:
        output = sync(
            Path(r"D:\UCIE_RELEASE\UCIE"), Path(r"D:\UCIE"), apply=args.apply)
    except (P8SyncError, OSError, subprocess.TimeoutExpired) as exc:
        output = {
            "schema": STATUS, "status": "P8_HOST_SYNC_BLOCKED_NO_CHANGE",
            "reason": str(exc).split(":")[0][:80],
            "blocked_file": (
                str(exc).split(": ", 1)[1]
                if str(exc).startswith(("source at pinned PR differs from checkout: ",
                                        "LOCAL_P8_SOURCE_DRIFT_NO_OVERWRITE: "))
                else None),
            "operating_db_writes": 0, "scheduler_modified": False,
            "production_auto_approval": False,
        }
        print(json.dumps(output, sort_keys=True, ensure_ascii=True))
        return 2
    print(json.dumps(output, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
