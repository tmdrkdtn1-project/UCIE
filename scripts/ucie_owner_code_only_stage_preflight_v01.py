"""UCIE PR305 immutable code-only stage verifier. No host operation is performed.

Use a separately obtained trusted clean snapshot whose file bytes match
docs/UCIE_PR305_CODE_ONLY_STAGE_MANIFEST_V01.json. This tool deliberately
does not create folders on owner D:, move live paths, or control Tasks/MCP.
"""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
from pathlib import Path
import re
import stat

SCHEMA = "UCIE_PR305_CODE_ONLY_STAGE_PREFLIGHT_V01"
EXPECTED_COMMIT = "96c6187430fc126214e93f57cfcd0b86331dc1a4"
EXPECTED_MANIFEST_BLOB = "7932913bc45875639d3bdf7caf7f31f279c2a0fb"
EXPECTED_COUNT = 232
EXPECTED_BYTES = 2934205
ALLOWED_SCRIPTS = frozenset({
    "scripts/bootstrap_local.ps1",
    "scripts/install_hourly_task.ps1",
    "scripts/install_internal_minute_task.ps1",
    "scripts/ucie_isolated_library_smoke_v01.py",
})
FORBIDDEN_COMPONENTS = frozenset({
    ".git", ".venv", "runtime", ".ucie_bridge_state", "__pycache__",
})
MAX_FILE_BYTES = 200000


class StageRejected(ValueError):
    """A path, manifest, or source lease cannot safely be trusted."""


def _indirect(path: Path) -> bool:
    if path.is_symlink():
        return True
    if not path.exists():
        return False
    try:
        return bool(path.stat(follow_symlinks=False).st_file_attributes &
                    stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except AttributeError:
        return False


def _direct_chain(path: Path, *, must_exist: bool = True) -> bool:
    absolute = path.absolute()
    if not absolute.is_absolute():
        return False
    for item in (absolute, *absolute.parents):
        if _indirect(item):
            return False
    return not must_exist or absolute.is_dir()


def _allowed_path(value: object) -> bool:
    if type(value) is not str or not value or "\\" in value or "//" in value:
        return False
    p = Path(value)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:
        return False
    if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in p.parts):
        return False
    if any(part.casefold() in FORBIDDEN_COMPONENTS for part in p.parts):
        return False
    return ((len(p.parts) == 3 and p.parts[0] == "src"
             and p.parts[1] in ("ucie_miner", "ucie_public")
             and p.suffix == ".py")
            or value in ALLOWED_SCRIPTS)


def load_manifest(path: Path) -> tuple[dict, list[dict]]:
    if not path.is_file() or not _direct_chain(path.parent) or _indirect(path):
        raise StageRejected("manifest must be direct regular file")
    if path.stat().st_size > 60000:
        raise StageRejected("manifest too large")
    raw = path.read_bytes()
    digest = sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if digest != EXPECTED_MANIFEST_BLOB:
        raise StageRejected("immutable manifest Git blob lease mismatch")
    try:
        obj = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise StageRejected("invalid manifest") from exc
    if (type(obj) is not dict
            or obj.get("schema") != "UCIE_PR305_IMMUTABLE_CODE_ONLY_STAGE_MANIFEST_V01"
            or obj.get("source_commit_sha") != EXPECTED_COMMIT
            or obj.get("code_only_file_count") != EXPECTED_COUNT
            or obj.get("code_only_total_bytes") != EXPECTED_BYTES
            or obj.get("copy_policy") != "ONLY_LISTED_UCIE_FIRST_PARTY_FILES_NO_LIVE_REPO_RUNTIME_DB_GIT_MCP_TUNNEL"):
        raise StageRejected("manifest identity mismatch")
    files = obj.get("files")
    if type(files) is not list or len(files) != EXPECTED_COUNT:
        raise StageRejected("manifest count mismatch")
    names = []
    total = 0
    for row in files:
        if (type(row) is not dict
                or set(row) != {"path", "git_blob_sha1", "bytes"}
                or not _allowed_path(row["path"])
                or type(row["bytes"]) is not int
                or not 0 <= row["bytes"] <= MAX_FILE_BYTES
                or type(row["git_blob_sha1"]) is not str
                or re.fullmatch(r"[a-f0-9]{40}", row["git_blob_sha1"]) is None):
            raise StageRejected("unapproved manifest entry")
        names.append(row["path"])
        total += row["bytes"]
    if len(set(names)) != len(names) or total != EXPECTED_BYTES:
        raise StageRejected("duplicate paths or byte count mismatch")
    if not ALLOWED_SCRIPTS.issubset(names):
        raise StageRejected("required owner preview scripts missing")
    return obj, files


def preflight(snapshot: Path, manifest: Path) -> dict:
    # Snapshot is the user-supplied clean source extraction, never the live checkout.
    src = snapshot.absolute()
    if not _direct_chain(src) or src.name.casefold() == "ucie":
        raise StageRejected("snapshot must be an independent nonlive source root")
    if str(src).casefold().rstrip("\\/") in {
            r"d:\ucie", r"d:\ucie_project\ucie", r"d:\ucie_data",
            r"d:\ucie_preview"}:
        raise StageRejected("live or destination root forbidden")
    obj, files = load_manifest(manifest)
    hashes = []
    for row in files:
        source = src.joinpath(*row["path"].split("/"))
        if (not _direct_chain(source.parent) or _indirect(source)
                or not source.is_file()
                or source.stat().st_size != row["bytes"]):
            raise StageRejected("missing, redirected or changed first-party source")
        data = source.read_bytes()
        git_blob = sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        if git_blob != row["git_blob_sha1"]:
            raise StageRejected("source Git blob lease mismatch")
        hashes.append((row["path"], sha256(data).hexdigest()))
    return {
        "schema": SCHEMA,
        "status": "UCIE_CODE_ONLY_SOURCE_BYTES_VERIFIED__OWNER_STAGE_NOT_APPLIED",
        "source_commit_sha": obj["source_commit_sha"],
        "manifest_sha256": sha256(manifest.read_bytes()).hexdigest(),
        "file_count": len(hashes),
        "total_bytes": EXPECTED_BYTES,
        "file_sha256": dict(hashes),
        "destination_written": False,
        "original_owner_checkout_touched": False,
        "live_task_or_mcp_changed": False,
        "db_or_secret_profile_accessed": False,
        "release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify PR305 isolated UCIE code-only snapshot")
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = preflight(args.snapshot, args.manifest)
        # Do not print private host file paths; only hashes and safe metadata.
        print(json.dumps({k: v for k, v in report.items() if k != "file_sha256"},
                         sort_keys=True))
        return 0
    except (StageRejected, OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"schema": SCHEMA,
                          "status": "UCIE_CODE_ONLY_SOURCE_PREFLIGHT_NO_GO",
                          "reason_type": type(exc).__name__,
                          "destination_written": False,
                          "live_task_or_mcp_changed": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
