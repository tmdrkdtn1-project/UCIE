"""One-time UCIE first-party code-only staging, never an operating root cutover.

Default mode is preview. The CLI can only write the absent
D:\UCIE_PROJECT\UCIE folder on Windows after explicit owner authorization.
It never writes to D:\UCIE, accesses owner SQLite, or starts any UCIE Task/MCP.
A failed write leaves an incomplete nonoperating folder for owner review;
there is deliberately no automatic delete/rollback action.
"""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

SCHEMA = "UCIE_PR305_OWNER_CODE_ONLY_STAGE_ONCE_V01"
OWNER_TARGET = r"D:\UCIE_PROJECT\UCIE"
OWNER_APPROVAL = "APPROVE_UCIE_CODE_ONLY_STAGE_ONCE"
RECEIPT = "UCIE_CODE_ONLY_STAGE_VERIFIED_V01.json"


class StageCopyRejected(ValueError):
    """Owner-safe no-go: do not apply or retry into a partial destination."""


def _load_verifier():
    source = Path(__file__).absolute().with_name(
        "ucie_owner_code_only_stage_preflight_v01.py")
    if source.is_symlink() or not source.is_file():
        raise StageCopyRejected("first-party verifier missing or indirect")
    spec = importlib.util.spec_from_file_location("ucie_pr305_source_verifier", source)
    if spec is None or spec.loader is None:
        raise StageCopyRejected("first-party verifier unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _safe_target(target: Path, *, owner_only: bool) -> Path:
    candidate = target.absolute()
    if owner_only and (
            os.name != "nt"
            or str(candidate).casefold() != OWNER_TARGET.casefold()):
        raise StageCopyRejected("exact Windows UCIE owner code-only root required")
    if candidate.exists() or candidate.is_symlink():
        raise StageCopyRejected("destination already exists; never overwrite or retry")
    if not candidate.parent.is_dir():
        raise StageCopyRejected("owner parent missing; never create D: parent")
    verifier = _load_verifier()
    if not verifier._direct_chain(candidate.parent):
        raise StageCopyRejected("target parent is indirect, inaccessible or reparse")
    if candidate.name.casefold() != "ucie" and owner_only:
        raise StageCopyRejected("unexpected owner stage name")
    return candidate


def _git_blob(content: bytes) -> str:
    return sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()


def stage_once(snapshot: Path, manifest: Path, target: Path, *,
               mode: str = "preview", owner_approval: str = "",
               owner_only: bool = True) -> dict:
    if mode not in {"preview", "apply"}:
        raise StageCopyRejected("unsupported mode")
    if mode == "apply" and owner_approval != OWNER_APPROVAL:
        raise StageCopyRejected("missing explicit owner one-shot approval")
    verifier = _load_verifier()
    # The original clean source is verified first; never use dirty D:\UCIE.
    pre = verifier.preflight(snapshot, manifest)
    meta, files = verifier.load_manifest(manifest)
    destination = _safe_target(target, owner_only=owner_only)
    source = snapshot.absolute()
    if (destination in source.parents or source in destination.parents
            or source == destination
            or (owner_only and destination.parent in source.parents)):
        raise StageCopyRejected("source/destination tree overlap forbidden")
    lease = pre["file_sha256"]
    if set(lease) != {row["path"] for row in files}:
        raise StageCopyRejected("preflight lease and allowlist differ")
    result = {
        "schema": SCHEMA,
        "status": "UCIE_CODE_ONLY_STAGE_PREVIEW_NO_WRITES",
        "source_commit_sha": meta["source_commit_sha"],
        "manifest_sha256": pre["manifest_sha256"],
        "planned_files": len(files),
        "planned_source_bytes": pre["total_bytes"],
        "owner_only_target": bool(owner_only),
        "live_task_mcp_tunnel_or_database_changed": False,
        "original_owner_root_moved_or_modified": False,
        "live_cutover_authorized": False,
        "customer_release_authorized": False,
        "destination_written": False,
    }
    if mode == "preview":
        return result

    # Only create a completely absent, direct, new folder. No parent creation.
    destination.mkdir()
    if not verifier._direct_chain(destination):
        raise StageCopyRejected("new destination became indirect")
    for entry in files:
        name = entry["path"]
        parts = name.split("/")
        source_file = source.joinpath(*parts)
        if (not verifier._direct_chain(source_file.parent)
                or verifier._indirect(source_file) or not source_file.is_file()):
            raise StageCopyRejected("source changed during stage")
        data = source_file.read_bytes()
        if (len(data) != entry["bytes"] or _git_blob(data) != entry["git_blob_sha1"]
                or sha256(data).hexdigest() != lease[name]):
            raise StageCopyRejected("source changed after successful preflight")
        target_file = destination.joinpath(*parts)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        if not verifier._direct_chain(target_file.parent) or target_file.exists() or target_file.is_symlink():
            raise StageCopyRejected("stage destination redirected or preexisting")
        with target_file.open("xb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        actual = target_file.read_bytes()
        if len(actual) != len(data) or sha256(actual).hexdigest() != lease[name]:
            raise StageCopyRejected("staged bytes did not survive write verification")

    # Only after the complete set is checked, write the single completion receipt.
    count = 0
    for entry in files:
        target_file = destination.joinpath(*entry["path"].split("/"))
        if (verifier._indirect(target_file) or not target_file.is_file()
                or target_file.stat().st_size != entry["bytes"]
                or _git_blob(target_file.read_bytes()) != entry["git_blob_sha1"]):
            raise StageCopyRejected("staged code verification failed before receipt")
        count += 1
    if count != pre["file_count"]:
        raise StageCopyRejected("incomplete copied source")
    result.update({
        "status": "UCIE_CODE_ONLY_STAGE_232_FILES_VERIFIED__LIVE_CUTOVER_NO_GO",
        "verified_files": count,
        "destination_written": True,
        "requires_pr304_p3p6_and_pr305_powershell_smokes": True,
        "rollback_or_operating_path_rebinding_performed": False,
    })
    receipt = destination / RECEIPT
    if receipt.exists() or receipt.is_symlink():
        raise StageCopyRejected("unexpected preexisting stage receipt")
    with receipt.open("xb") as out:
        out.write((json.dumps(result, sort_keys=True, indent=2) + "\n").encode("utf-8"))
        out.flush()
        os.fsync(out.fileno())
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE-only exact-root code-stage one-shot")
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--mode", choices=("preview", "apply"), default="preview")
    parser.add_argument("--owner-approval", default="")
    args = parser.parse_args()
    try:
        report = stage_once(
            args.snapshot, args.manifest, Path(OWNER_TARGET),
            mode=args.mode, owner_approval=args.owner_approval, owner_only=True)
        print(json.dumps(report, sort_keys=True))
        return 0
    except (StageCopyRejected, OSError, ValueError, UnicodeError) as exc:
        # An apply failure MAY have left a partial inactive folder. Never claim
        # no writes occurred or automatically delete files in that situation.
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_CODE_ONLY_STAGE_NO_GO",
            "reason_type": type(exc).__name__,
            "partial_destination_requires_owner_review": args.mode == "apply",
            "live_cutover_authorized": False,
            "automatic_rollback_or_cleanup": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
