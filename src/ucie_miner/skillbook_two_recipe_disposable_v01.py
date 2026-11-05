"""UCIE V1: draft-only, deterministic, first-party two-SkillBook consumer ZIP.

Uses the existing exact main-commit recipe sources. Builder is in-memory
only: no installer, signer, public export, source crawl, operating DB, or
outside-project input. Tests may write this draft to an OS temporary fixture.
"""
from __future__ import annotations

from hashlib import sha1, sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

SCHEMA = "UCIE_SKILLBOOK_TWO_RECIPE_DISPOSABLE_DRAFT_V01"
MAIN_COMMIT = "c41460cd708ca911b64330ccded603fae5e552f3"
SOURCE_BLOBS = {
    "skillbook_scandir_recipe_v01.py": "6a26ea59cfebdd8d548fb88fd8a5039c5e16ac38",
    "skillbook_git_porcelain_recipe_v01.py": "aff4375e5fd964edf8e47b46f171e676e768f6b2",
}
ENTRY_NAMES = ("__main__.py", "skillbook_git_porcelain_recipe_v01.py",
               "skillbook_scandir_recipe_v01.py", "MANIFEST.json")
ZIP_DATE = (2020, 1, 1, 0, 0, 0)
MAX_SOURCE_BYTES = 16_000


class DraftBundleError(ValueError):
    """Unknown or changed first-party recipe: stop rather than substitute."""


# No code assembled from upstream documents, user prompts, or other projects.
# The executable accepts only caller-supplied Git bytes or a self-created
# temporary synthetic directory: NEVER an arbitrary local directory path.
RUNNER = r'''"""UCIE first-party isolated SkillBook 001/002 consumer; NOT RELEASED."""
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

BLOBS = {
    "skillbook_scandir_recipe_v01.py": "6a26ea59cfebdd8d548fb88fd8a5039c5e16ac38",
    "skillbook_git_porcelain_recipe_v01.py": "aff4375e5fd964edf8e47b46f171e676e768f6b2",
}
SCHEMA = "UCIE_SKILLBOOK_TWO_RECIPE_DISPOSABLE_DRAFT_V01"


def _git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\\x00" + raw).hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate input key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("nonstandard JSON number")


def _run():
    if len(sys.argv) != 1:
        raise ValueError("no external CLI flags accepted")
    with ZipFile(sys.argv[0], "r") as archive:
        names = archive.namelist()
        if names != ["__main__.py", "skillbook_git_porcelain_recipe_v01.py",
                     "skillbook_scandir_recipe_v01.py", "MANIFEST.json"]:
            raise ValueError("unexpected ZIP entries")
        manifest = json.loads(archive.read("MANIFEST.json"))
        if (type(manifest) is not dict
                or manifest.get("schema") != SCHEMA
                or manifest.get("released") is not False
                or manifest.get("export_approved") is not False
                or manifest.get("signed") is not False
                or manifest.get("independent_qa_verified") is not False
                or manifest.get("sources_git_blob_sha1") != BLOBS):
            raise ValueError("bundle manifest integrity blocked")
        for name, blob in BLOBS.items():
            if _git_blob(archive.read(name)) != blob:
                raise ValueError("modified first-party module")
        for name, digest in manifest["member_sha256"].items():
            if name not in names or hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError("modified archive member")
    raw = sys.stdin.buffer.read(32769)
    if len(raw) > 32768:
        raise ValueError("request exceeds byte budget")
    request = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                         parse_constant=_reject_constant)
    if type(request) is not dict:
        raise ValueError("request must be JSON object")
    action = request.get("action")
    if action == "git-summary" and set(request) == {"action", "payload_hex"}:
        value = request["payload_hex"]
        if (type(value) is not str or len(value) > 16384
                or re.fullmatch("[0-9a-f]*", value) is None):
            raise ValueError("untrusted Git input bytes")
        from skillbook_git_porcelain_recipe_v01 import summarize_porcelain_v1_z
        result = summarize_porcelain_v1_z(bytes.fromhex(value))
        item_id = "UCIE-SKILLBOOK-GIT-PORCELAIN-002"
    elif action == "scandir-synthetic" and set(request) == {"action"}:
        from skillbook_scandir_recipe_v01 import bounded_regular_file_names
        with tempfile.TemporaryDirectory(prefix="UCIE_SB_FIRST_PARTY_") as d:
            folder = Path(d)
            (folder / "zeta.txt").write_bytes(b"synthetic\n")
            (folder / "alpha.txt").write_bytes(b"synthetic\n")
            result = {"names": list(bounded_regular_file_names(folder, max_entries=2)),
                      "synthetic_fixture_only": True}
        item_id = "UCIE-SKILLBOOK-PY-SCANDIR-001"
    else:
        raise ValueError("unsupported action or unauthorized input keys")
    return {"schema": SCHEMA, "status": "FIRST_PARTY_DRAFT_ONLY_NOT_RELEASED",
            "skillbook_id": item_id, "result": result,
            "independent_qa_verified": False, "export_approved": False,
            "other_project_access": False, "operating_database_writes": 0}


try:
    output = _run()
    encoded = json.dumps(output, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("ascii")
    if len(encoded) > 8192:
        raise ValueError("output limit")
    sys.stdout.buffer.write(encoded + b"\n")
except Exception:
    sys.stdout.buffer.write(b'{"status":"UCIE_FIRST_PARTY_DRAFT_FAIL_CLOSED"}\n')
    sys.exit(2)
'''


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()


def _entry(name: str, raw: bytes) -> tuple[ZipInfo, bytes]:
    info = ZipInfo(name, date_time=ZIP_DATE)
    info.create_system = 3
    info.compress_type = ZIP_STORED
    info.external_attr = 0o100644 << 16
    return info, raw


def build_draft_bundle() -> tuple[bytes, dict]:
    """Only package pinned UCIE-authored sources; never write or export."""
    members = {"__main__.py": RUNNER.encode("utf-8")}
    root = Path(__file__).resolve().parent
    for name, expected_blob in sorted(SOURCE_BLOBS.items()):
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise DraftBundleError("first-party source missing or symlinked")
        if path.stat().st_size > MAX_SOURCE_BYTES:
            raise DraftBundleError("first-party source beyond budget")
        raw = path.read_bytes()
        if _git_blob(raw) != expected_blob:
            raise DraftBundleError("first-party source differs from pinned commit")
        members[name] = raw
    manifest = {
        "schema": SCHEMA, "version": "0.1.0-draft",
        "pinned_main_commit": MAIN_COMMIT,
        "sources_git_blob_sha1": SOURCE_BLOBS,
        "member_sha256": {k: sha256(v).hexdigest() for k, v in sorted(members.items())},
        "skillbook_ids": ["UCIE-SKILLBOOK-PY-SCANDIR-001",
                          "UCIE-SKILLBOOK-GIT-PORCELAIN-002"],
        "execution_scope": "UCIE_AUTHORED_SYNTHETIC_ONLY",
        "caller_supplied_git_bytes_max": 8192,
        "external_directory_inputs_allowed": False,
        "upstream_source_bundled": False,
        "independent_qa_verified": False,
        "rights_approved": False, "signed": False,
        "export_approved": False, "released": False,
        "owner_release_authorized": False,
        "automatic_promotion": False,
    }
    members["MANIFEST.json"] = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True).encode("ascii") + b"\n"
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_STORED, allowZip64=False) as archive:
        for name in ENTRY_NAMES:
            info, data = _entry(name, members[name])
            archive.writestr(info, data)
    result = stream.getvalue()
    if len(result) > 60_000:
        raise DraftBundleError("bounded package size exceeded")
    return result, {
        "schema": SCHEMA,
        "status": "FIRST_PARTY_DISPOSABLE_DRAFT_NOT_RELEASED",
        "archive_sha256": sha256(result).hexdigest(),
        "archive_bytes": len(result),
        "entries": list(ENTRY_NAMES),
        "pinned_main_commit": MAIN_COMMIT,
        "release_approved": False,
        "export_allowed": False,
        "independent_qa_verified": False,
        "files_written": 0,
        "network_requests": 0,
        "operating_database_writes": 0,
        "other_project_access": False,
    }


def main() -> int:
    """No file output; safe preview for owner-only diagnostics."""
    _, receipt = build_draft_bundle()
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
