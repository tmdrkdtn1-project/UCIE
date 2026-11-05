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
PRODUCT_BLOBS = {
    "skillbook_product_v01.py": "666d4c3bd1549b353748f6ada6dc4eb8f9924e98",
    "skillbook_git_porcelain_product_v01.py": "eb92f23cd6865ca55e11e491d968f10f00220b0f",
}
COMPOSER_BLOB = "a22a5278f716234e19661525d1b51c90043ad04e"
PRINCIPLE_SCHEMA = "UCIE_SKILLBOOK_CROSS_SOURCE_PRINCIPLE_V01"
PRINCIPLE_ID = "UCIE-PRINCIPLE-PYTHON-GIT-BOUNDED-METADATA-001"
ENTRY_NAMES = ("__main__.py", "skillbook_git_porcelain_recipe_v01.py",
               "skillbook_scandir_recipe_v01.py", "PRINCIPLE.json",
               "PRINCIPLE.md", "SKILLBOOKS.json", "SKILLBOOKS.md",
               "MANIFEST.json")
CONTENT_SCHEMA = "UCIE_TWO_AUTHORED_SKILLBOOKS_V01"
PINNED_BOOKS = {
    "UCIE-SKILLBOOK-PY-SCANDIR-001": (
        "doc:python/cpython",
        "9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a",
        "v3.15.0",
        "ucie_miner.skillbook_scandir_recipe_v01.bounded_regular_file_names",
    ),
    "UCIE-SKILLBOOK-GIT-PORCELAIN-002": (
        "doc:git/git",
        "1cdd1c7339dfc64093687b6e072d59feee584b8639c0203ece0a1150ce23d325",
        "v2.51.0",
        "ucie_miner.skillbook_git_porcelain_recipe_v01.summarize_porcelain_v1_z",
    ),
}
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
CONTENT_SCHEMA = "UCIE_TWO_AUTHORED_SKILLBOOKS_V01"
PRODUCT_BLOBS = {
    "skillbook_product_v01.py": "666d4c3bd1549b353748f6ada6dc4eb8f9924e98",
    "skillbook_git_porcelain_product_v01.py": "eb92f23cd6865ca55e11e491d968f10f00220b0f",
}


def _git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()


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
                     "skillbook_scandir_recipe_v01.py", "PRINCIPLE.json",
                     "PRINCIPLE.md", "SKILLBOOKS.json",
                     "SKILLBOOKS.md", "MANIFEST.json"]:
            raise ValueError("unexpected ZIP entries")
        if any(i.file_size > 16000 or i.compress_size > 16000
               for i in archive.infolist()):
            raise ValueError("oversize archive member")
        manifest = json.loads(archive.read("MANIFEST.json"))
        if (type(manifest) is not dict
                or manifest.get("schema") != SCHEMA
                or manifest.get("content_schema") != CONTENT_SCHEMA
                or manifest.get("principle_schema") != "UCIE_SKILLBOOK_CROSS_SOURCE_PRINCIPLE_V01"
                or type(manifest.get("principle_content_sha256")) is not str
                or len(manifest["principle_content_sha256"]) != 64
                or manifest.get("composer_git_blob_sha1")
                   != "a22a5278f716234e19661525d1b51c90043ad04e"
                or manifest.get("released") is not False
                or manifest.get("export_approved") is not False
                or manifest.get("signed") is not False
                or manifest.get("independent_qa_verified") is not False
                or manifest.get("sources_git_blob_sha1") != BLOBS
                or manifest.get("authored_product_git_blob_sha1") != PRODUCT_BLOBS
                or type(manifest.get("member_sha256")) is not dict
                or set(manifest["member_sha256"]) != set(names) - {"MANIFEST.json"}):
            raise ValueError("bundle manifest integrity blocked")
        for name, blob in BLOBS.items():
            if _git_blob(archive.read(name)) != blob:
                raise ValueError("modified first-party module")
        for name, digest in manifest["member_sha256"].items():
            if (type(digest) is not str or len(digest) != 64
                    or hashlib.sha256(archive.read(name)).hexdigest() != digest):
                raise ValueError("modified archive member")
        principle = json.loads(archive.read("PRINCIPLE.json"))
        if (type(principle) is not dict
                or principle.get("schema")
                   != "UCIE_SKILLBOOK_CROSS_SOURCE_PRINCIPLE_V01"
                or principle.get("principle_id")
                   != "UCIE-PRINCIPLE-PYTHON-GIT-BOUNDED-METADATA-001"
                or principle.get("content_sha256")
                   != manifest["principle_content_sha256"]
                or principle.get("export_allowed") is not False
                or principle.get("independent_qa_verified") is not False
                or principle.get("rights_approved") is not False
                or principle.get("released") is not False
                or type(principle.get("sources")) is not list
                or len(principle["sources"]) != 2):
            raise ValueError("cross-source authored principle not attested")
        books = json.loads(archive.read("SKILLBOOKS.json"))
        if (type(books) is not dict
                or books.get("schema") != CONTENT_SCHEMA
                or books.get("blueprint_id") != manifest.get("blueprint_id")
                or books.get("export_allowed") is not False
                or type(books.get("items")) is not list
                or len(books["items"]) != 2
                or {b.get("skillbook_id") for b in books["items"]
                    if type(b) is dict} != set(manifest.get("skillbook_ids", []))):
            raise ValueError("authored SkillBook contract not attested")
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
    elif action == "principle-synthetic" and set(request) == {"action"}:
        from skillbook_scandir_recipe_v01 import bounded_regular_file_names
        from skillbook_git_porcelain_recipe_v01 import summarize_porcelain_v1_z
        with tempfile.TemporaryDirectory(prefix="UCIE_PRINCIPLE_SYNTHETIC_") as d:
            folder = Path(d)
            (folder / "alpha.txt").write_bytes(b"self-authored fixture\n")
            (folder / "beta.txt").write_bytes(b"self-authored fixture\n")
            scanned = bounded_regular_file_names(folder, max_entries=2)
        parsed = summarize_porcelain_v1_z(
            b" M fake-a.txt\x00?? fake-b.txt\x00", max_entries=2)
        if (len(scanned) != 2 or parsed["total_entries"] != 2
                or parsed["filenames_or_content_returned"] is not False):
            raise ValueError("cross-source synthetic results drift")
        result = {
            "scandir_file_count": len(scanned),
            "scandir_names_exported": False,
            "git_entry_count": parsed["total_entries"],
            "git_counts": parsed["counts"],
            "git_names_exported": False,
            "synthetic_sources_only": True,
        }
        item_id = "UCIE-PRINCIPLE-PYTHON-GIT-BOUNDED-METADATA-001"
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


def _canonical_source_bytes(raw: bytes, expected_blob: str) -> bytes:
    """Normalize only Windows checkout CRLF, then verify exact pinned Git blob.

    Git autocrlf checkout must not make the same verified source unusable.
    Lone CR, unrelated source changes, oversized or non-byte input still fail.
    All ZIPs contain canonical LF source, regardless of checkout OS.
    """
    if type(raw) is not bytes or not (0 < len(raw) <= MAX_SOURCE_BYTES):
        raise DraftBundleError("invalid bounded first-party source")
    canonical = raw.replace(b"\r\n", b"\n")
    if b"\r" in canonical or _git_blob(canonical) != expected_blob:
        raise DraftBundleError("first-party source differs from pinned commit")
    return canonical


def _authored_book_assets() -> tuple[bytes, bytes, str]:
    """Compose existing W02/W03 books into human and machine draft artifacts.

    Source facts and separately authored chapter text are preserved as distinct
    claims. Rebuild the known source Registry blueprint; never trust external
    chapter claims or promote a candidate to approved/released.
    """
    from .skillbook_blueprint import compose_blueprint
    from .skillbook_product_v01 import build_skillbook as python_book
    from .skillbook_git_porcelain_product_v01 import build_skillbook as git_book

    root = Path(__file__).resolve().parent
    for filename, expected_blob in PRODUCT_BLOBS.items():
        path = root / filename
        if path.is_symlink() or not path.is_file():
            raise DraftBundleError("authored chapter source missing or redirected")
        _canonical_source_bytes(path.read_bytes(), expected_blob)
    books = (python_book(), git_book())
    if {book.get("skillbook_id") for book in books} != set(PINNED_BOOKS):
        raise DraftBundleError("unknown or duplicate SkillBook identity")
    candidates = []
    rows = []
    markdown = [
        "# UCIE 기술 SkillBook 001·002 — 내부 미승인 초안",
        "",
        "> 공식 공개 출처의 API 사실과 UCIE 작성 설명·레시피는 서로 다릅니다.",
        "> 이 파일은 독립 QA·라이선스/권리 검토·소유자 승인·서명·배포를 뜻하지 않습니다.",
        "",
    ]
    for book in books:
        book_id = book["skillbook_id"]
        source_id, source_sha, source_tag, callable_name = PINNED_BOOKS[book_id]
        entry = book.get("library_entry")
        evidence = book.get("source_evidence")
        gates = book.get("proof_gates")
        contract = book.get("machine_skill_contract")
        chapters = book.get("ucie_authored_chapters")
        history = book.get("revision_history")
        if (book.get("status") != "FIRST_PARTY_DRAFT_NOT_APPROVED"
                or book.get("export_allowed") is not False
                or type(entry) is not dict
                or entry.get("source_id") != source_id
                or entry.get("entry_status") != "UNVERIFIED_CANDIDATE_ONLY"
                or entry.get("approval_status") != "NOT_APPROVED"
                or entry.get("export_allowed") is not False
                or entry.get("evidence_sha256") != source_sha
                or type(evidence) is not dict
                or evidence.get("source_document_sha256") != source_sha
                or evidence.get("source_tag") != source_tag
                or type(gates) is not dict
                or any(gates.get(key) is not False for key in (
                    "independent_test_verified", "license_redistribution_approved",
                    "security_review_approved", "human_approved", "signed", "published"))
                or type(contract) is not dict
                or contract.get("callable") != callable_name
                or type(chapters) is not tuple or len(chapters) != 4
                or any(type(ch) is not dict
                       or set(ch) != {"heading", "claim_type", "text"}
                       or any(type(v) is not str or not 1 <= len(v) <= 1800
                              for v in ch.values()) for ch in chapters)
                or type(history) is not list or len(history) != 1
                or type(history[0]) is not dict
                or history[0].get("evidence_sha256") != source_sha
                or history[0].get("published") is not False
                or history[0].get("independently_verified") is not False):
            raise DraftBundleError("unreviewed or forged SkillBook chapter/rights claim")
        candidates.append({
            "kind": entry["kind"],
            "source_id": source_id,
            "evidence_reference": entry["evidence_reference"],
            "evidence_sha256": source_sha,
            "purpose_code": entry["purpose_code"],
            "version_scope": entry["version_scope_claim"],
            "dependencies": list(entry["dependencies"]),
        })
        rows.append({
            "skillbook_id": book_id,
            "title": book["title"],
            "library_item_id": entry["library_item_id"],
            "source_id": source_id,
            "source_tag": source_tag,
            "source_sha256": source_sha,
            "source_public_url": evidence["official_document_url"],
            "source_license_status": entry["source_license_status"],
            "chapter_claims": list(chapters),
            "machine_skill_contract": contract,
            "revision_history": history,
            "proof_gates": gates,
            "export_allowed": False,
        })
        markdown.extend([
            "## " + str(book["title"]),
            "",
            "출처: " + str(evidence["official_document_url"]),
            " · 공개 근거 태그: " + source_tag,
            "",
            "출처 SHA-256: `" + source_sha + "`",
            "",
        ])
        for chapter in chapters:
            markdown.extend([
                "### " + chapter["heading"],
                "",
                "근거 구분: `" + chapter["claim_type"] + "`",
                "",
                chapter["text"], "",
            ])
        markdown.extend([
            "실행 계약: `" + callable_name + "`",
            "",
            "승인 상태: NOT_APPROVED / 반출 불가 / 자체 시험 범위 한정",
            "",
        ])
    blueprint = compose_blueprint("UCIE_TWO_SKILLBOOKS_DRAFT_V01", candidates)
    if (blueprint.get("status") != "UNVERIFIED_METADATA_ONLY"
            or blueprint.get("chapter_count") != 2
            or {item["library_item_id"] for item in blueprint["chapters"]}
               != {row["library_item_id"] for row in rows}
            or blueprint.get("export_allowed") is not False):
        raise DraftBundleError("original public evidence blueprint mismatched")
    structured = {
        "schema": CONTENT_SCHEMA,
        "blueprint_id": blueprint["blueprint_id"],
        "items": rows,
        "human_document_kind": "UCIE_AUTHORED_FIRST_PARTY_DRAFT_CHAPTERS",
        "source_approval_preserved": True,
        "external_semantic_synthesis_verified": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "human_approved": False,
        "signed": False,
        "export_allowed": False,
        "released": False,
        "model_trained": False,
    }
    machine = (json.dumps(structured, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":")) + "\n").encode("ascii")
    human = ("\n".join(markdown).rstrip() + "\n").encode("utf-8")
    if max(len(machine), len(human)) > MAX_SOURCE_BYTES:
        raise DraftBundleError("bounded authored document size exceeded")
    return machine, human, blueprint["blueprint_id"]


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
        members[name] = _canonical_source_bytes(raw, expected_blob)
    authored_json, authored_markdown, blueprint_id = _authored_book_assets()
    members["SKILLBOOKS.json"] = authored_json
    members["SKILLBOOKS.md"] = authored_markdown
    manifest = {
        "schema": SCHEMA, "version": "0.1.0-draft",
        "content_schema": CONTENT_SCHEMA, "blueprint_id": blueprint_id,
        "pinned_main_commit": MAIN_COMMIT,
        "sources_git_blob_sha1": SOURCE_BLOBS,
        "authored_product_git_blob_sha1": PRODUCT_BLOBS,
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
        "blueprint_id": blueprint_id,
        "human_skillbook_chapters_included": True,
        "machine_skill_contracts_included": True,
        "automatic_semantic_synthesis_claimed": False,
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
