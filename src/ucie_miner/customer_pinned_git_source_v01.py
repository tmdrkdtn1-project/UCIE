"""UCIE C1: pinned, offline, reviewed-Git-source-only A/B candidate gate.

Two immutable, reviewed public UCIE commit trees are enumerated in a fixed
first-party manifest. Default preview reads ONLY the UCIE checkout's bounded
first-party files and reports SHA-1 Git blob source divergence; never builds,
fetches, installs, publishes or changes the worktree. Separate owner-authorized
export can retrieve the two pinned trees ONLY from LOCAL Git objects, verify
every blob against its pinned GitHub-public manifest, and package ONLY two
QA first-party wheels (no external vendor wheels) into Git-ignored local ZIP.
This is NOT signed or complete customer-ready product distribution.
"""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import io
import json
import os
from pathlib import Path
from zipfile import BadZipFile
import subprocess
import sys
import sysconfig
import tarfile
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from . import customer_full_product_offline_rehearsal_v01 as product
from . import customer_runtime_closure_v01 as runtime
from .customer_component_lifecycle_v01 import FILES as C0_FILES

SCHEMA = "UCIE_C1_TWO_PINNED_PUBLIC_GIT_TREES_V01"
BUNDLE_SCHEMA = "UCIE_C1_PINNED_AB_FIRST_PARTY_ONLY_QA_BUNDLE_V01"
MANIFEST = "docs/UCIE_C1_TWO_PINNED_GIT_TREES_20261112.json"
A_SHA = "171d56d8af155c70d3dd32a62afda87398330e99"
B_SHA = "4242ebe7ae112076d9b3560e85b0babb22bbb713"
TREE_A = "35e7e796deb83435f58c39b83daa984eb22eb30b"
TREE_B = "7f96f430fb5b2f582dbcda8861968e7363055eb4"
B_ONLY_HEALTH = "src/ucie_miner/customer_installed_health_v01.py"
B_ONLY_LIFECYCLE = "src/ucie_miner/customer_functional_ab_lifecycle_v01.py"
FINAL_ZIP = "downloaded/ucie_c1_pinned_git_ab_first_party_qa_only.zip"
RECEIPT = "downloaded/ucie_c1_pinned_git_ab_source_receipt_v01.json"
CONSENT = "EXPORT_UCIE_C1_PINNED_PUBLIC_SOURCE_WHEELS_ONCE"
ROOT = Path("D:/UCIE")
MAX_MANIFEST = 120_000
MAX_ARCHIVE = 20_000_000
MAX_BUNDLE = 20_000_000
VERSION = {"A": "0.1.0", "B": "0.1.1"}
PINNED = {"A": (A_SHA, TREE_A, 182), "B": (B_SHA, TREE_B, 184)}
README = (
    "UCIE-only FIRST-PARTY reviewed-Git-commit A/B QA artifacts.\n"
    "NO vendor wheels, signed customer releases, personal/customer data,\n"
    "runtime installation, external access or C2/C3/C4/C5 approvals.\n"
    "Do NOT publish/redistribute as a commercial package.\n"
    "See manifest and QA provenance for exact reviewed Git tree pins.\n"
)


class PinnedSourceError(ValueError):
    """A closed technical release gate; never customer GO."""


def _root(root: Path) -> Path:
    if (not isinstance(root, Path) or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()
            or (root / ".git").is_symlink()
            or not (root / ".git").is_dir()):
        raise PinnedSourceError("exact UCIE first-party checkout required")
    return root


def _rows(raw: object, *, package: bool) -> dict[str, tuple[str, int]]:
    if type(raw) is not list or not raw:
        raise PinnedSourceError("missing pinned Git source rows")
    rows = {}
    prior = ""
    for entry in raw:
        if (type(entry) is not list or len(entry) != 3
                or not all(type(v) is str for v in entry[:2])
                or type(entry[2]) is not int):
            raise PinnedSourceError("malformed Git source row")
        path, git_hash, size = entry
        bits = path.split("/")
        if package and not path.startswith(("src/ucie_miner/", "src/ucie_public/")):
            raise PinnedSourceError("non-UCIE package in source manifest")
        if (not path.isascii() or not path or chr(92) in path
                or path.startswith("/") or any(x in ("", ".", "..") for x in bits)
                or path <= prior or len(git_hash) != 40
                or any(c not in "0123456789abcdef" for c in git_hash)
                or size < 0 or size > runtime.MAX_FILE_BYTES):
            raise PinnedSourceError("untrusted Git path/blob/size")
        if package and not path.endswith(".py"):
            raise PinnedSourceError("non-Python file in source inventory")
        if not package and path not in C0_FILES:
            raise PinnedSourceError("unapproved C0 component")
        rows[path] = (git_hash, size)
        prior = path
    return rows


def _load_manifest(root: Path) -> tuple[dict, dict]:
    root = _root(root)
    path = root / MANIFEST
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= MAX_MANIFEST):
        raise PinnedSourceError("pinned public Git tree manifest absent/unsafe")
    try:
        document = json.loads(path.read_text(encoding="ascii"))
    except (UnicodeError, OSError, ValueError) as exc:
        raise PinnedSourceError("pinned Git source manifest malformed") from exc
    if (type(document) is not dict or document.get("schema") != SCHEMA
            or document.get("origin") != "github.com/tmdrkdtn1-project/UCIE"
            or document.get("scope") != "UCIE_FIRST_PARTY_ONLY"
            or document.get("customer_distribution_authorized") is not False
            or document.get("third_party_wheels_included") is not False
            or document.get("owner_dirty_files_included") is not False
            or document.get("c2_legal_and_signature_approved") is not False
            or type(document.get("slots")) is not dict
            or set(document["slots"]) != {"A", "B"}):
        raise PinnedSourceError("pinned Git source manifest policy mismatch")
    slots = {}
    for label in ("A", "B"):
        slot = document["slots"][label]
        commit, tree, count = PINNED[label]
        if (type(slot) is not dict or slot.get("commit_sha") != commit
                or slot.get("root_tree_sha1") != tree
                or slot.get("qa_wheel_version") != VERSION[label]):
            raise PinnedSourceError("unpinned or moving Git commit metadata")
        pkg = _rows(slot.get("python_modules"), package=True)
        c0 = _rows(slot.get("c0_inventory"), package=False)
        if (len(pkg) != count or set(c0) != set(C0_FILES)
                or any(pkg[path] != c0[path] for path in c0 if path in pkg)
                or not all(f"src/{p}/__init__.py" in pkg
                           for p in runtime.PACKAGES)):
            raise PinnedSourceError("incomplete pinned C0/product source census")
        slots[label] = {"python": pkg, "c0": c0}
    a, b = slots["A"]["python"], slots["B"]["python"]
    if (set(b) - set(a) != {B_ONLY_HEALTH, B_ONLY_LIFECYCLE}
            or set(a) - set(b) or a.get(
                "src/ucie_miner/customer_staging_v01.py"
            ) != b.get("src/ucie_miner/customer_staging_v01.py")):
        raise PinnedSourceError("unexpected functional Git A/B source delta")
    return document, slots


def _git_blob_sha1(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()


def _safe_file(root: Path, name: str) -> bytes | None:
    parts = name.split("/")
    target = root
    for component in parts[:-1]:
        target = target / component
        if target.is_symlink() or not target.is_dir():
            raise PinnedSourceError("untrusted local source directory")
    file = target / parts[-1]
    if file.is_symlink():
        raise PinnedSourceError("local source symlink blocked")
    if not file.is_file():
        return None
    if file.stat().st_size > runtime.MAX_FILE_BYTES:
        raise PinnedSourceError("owner source exceeded bounded file budget")
    return file.read_bytes()


def _local_comparison(root: Path, rows: dict) -> dict:
    """No Git subprocess. Never sends owner-only file names to public logs."""
    # Existing UCIE-only bounded AST and symlink-aware source index.
    source = runtime._src_index(root)
    actual = {path: value for path, value, _ in source.values()}
    expected = rows["B"]["python"]
    changed = missing = eol_only = 0
    for path, (git_hash, size) in expected.items():
        raw = actual.get(path)
        if raw is None:
            missing += 1
        elif len(raw) != size or _git_blob_sha1(raw) != git_hash:
            # Classify Windows LF-vs-CRLF conversion; a line-ending
            # difference is NOT identical release bytes, but neither
            # is it a semantic/code-edit divergence.
            normalized = raw.replace(b"\r\n", b"\n")
            if (normalized != raw and len(normalized) == size
                    and _git_blob_sha1(normalized) == git_hash):
                eol_only += 1
            else:
                changed += 1
    extra = len(set(actual) - set(expected))
    changed_c0 = missing_c0 = c0_eol_only = 0
    for path, (git_hash, size) in rows["B"]["c0"].items():
        if path in expected:
            continue
        raw = _safe_file(root, path)
        if raw is None:
            missing_c0 += 1
        elif len(raw) != size or _git_blob_sha1(raw) != git_hash:
            normalized = raw.replace(b"\r\n", b"\n")
            if (normalized != raw and len(normalized) == size
                    and _git_blob_sha1(normalized) == git_hash):
                c0_eol_only += 1
            else:
                changed_c0 += 1
    return {
        "current_local_python_module_count": len(actual),
        "pinned_reviewed_b_python_module_count": len(expected),
        "owner_local_python_files_non_eol_changed": changed,
        "owner_local_python_files_EOL_only_different_bytes": eol_only,
        "owner_local_python_files_missing": missing,
        "owner_local_extra_python_files_NOT_approved_for_export": extra,
        "owner_selected_c0_components_non_eol_changed": changed_c0,
        "owner_selected_c0_components_EOL_only_different_bytes": c0_eol_only,
        "owner_selected_c0_components_missing": missing_c0,
        "owner_current_worktree_exactly_reviewed_B": all(
            n == 0 for n in (
                changed, missing, extra, eol_only,
                changed_c0, missing_c0, c0_eol_only
            )
        ),
    }


def preview(root: Path) -> dict:
    """Read-only source comparison against GitHub blob inventory; no fetch."""
    doc, rows = _load_manifest(root)
    metrics = _local_comparison(root, rows)
    return {
        "schema": SCHEMA,
        "status": "C1_REVIEWED_PUBLIC_GIT_SOURCE_PINS_ONLY_CUSTOMER_NO_GO",
        "mode": "LOCAL_FIRST_PARTY_READONLY_NO_GIT_COMMAND_NO_NETWORK",
        "pinned_commit_A": A_SHA,
        "pinned_commit_B": B_SHA,
        "pinned_tree_A": TREE_A,
        "pinned_tree_B": TREE_B,
        "A_reviewed_first_party_python_files": len(rows["A"]["python"]),
        "B_reviewed_first_party_python_files": len(rows["B"]["python"]),
        "C0_selected_components_per_commit": len(C0_FILES),
        "B_specific_new_real_features": [
            B_ONLY_HEALTH, B_ONLY_LIFECYCLE,
        ],
        "owner_worktree_reconciliation": metrics,
        "build_only_git_objects_never_owner_worktree": True,
        "git_fetch_performed": False,
        "third_party_packages_copied_or_imported": False,
        "external_network_requests": 0,
        "customer_distribution_authorized": False,
    }


def _git(root: Path, args: list[str], *, ceiling: int) -> bytes:
    """Fixed git READ operations only. Disable git object lazy fetch."""
    if not args or args[0] not in ("cat-file", "rev-parse", "archive"):
        raise PinnedSourceError("non-read-only git operation blocked")
    env_keep = ("PATH", "SystemRoot", "SYSTEMROOT", "WINDIR",
                "TEMP", "TMP", "HOME", "USERPROFILE")
    env = {k: os.environ[k] for k in env_keep if k in os.environ}
    env.update({
        "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
        "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    })
    try:
        result = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(root), *args],
            capture_output=True, check=False, timeout=45, shell=False,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PinnedSourceError("local Git object read unavailable") from exc
    if (result.returncode or len(result.stdout) > ceiling
            or len(result.stderr) > 8_000):
        raise PinnedSourceError("pinned Git object unavailable locally; NO AUTO FETCH")
    return result.stdout


def _git_object_roots(root: Path, label: str) -> None:
    sha, expected_tree, _ = PINNED[label]
    if _git(root, ["cat-file", "-t", sha], ceiling=100).strip() != b"commit":
        raise PinnedSourceError("pinned SHA is not a Git commit")
    tree = _git(root, ["rev-parse", "--verify", sha + "^{tree}"],
                ceiling=100).decode("ascii").strip()
    if tree != expected_tree:
        raise PinnedSourceError("actual Git tree differs from pinned public SHA")


def _validate_archived_source(tar_bytes: bytes, desired: dict) -> dict[str, bytes]:
    """Verify ALL package+C0 bytes from Git archive, reject any extras."""
    if type(tar_bytes) is not bytes or len(tar_bytes) > MAX_ARCHIVE:
        raise PinnedSourceError("Git archive exceeds budget")
    expected = {**desired["python"], **desired["c0"]}
    assembled = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as archive:
            if len(archive.getmembers()) > len(expected) + 60:
                raise PinnedSourceError("unbounded Git archive entries")
            for item in archive:
                if item.isdir():
                    continue
                name = item.name
                if (not item.isfile() or item.issym() or item.islnk()
                        or name not in expected or name in assembled
                        or item.size != expected[name][1]
                        or item.size > runtime.MAX_FILE_BYTES):
                    raise PinnedSourceError("unsafe, extra or changed Git blob entry")
                stream = archive.extractfile(item)
                if stream is None:
                    raise PinnedSourceError("missing Git source stream")
                raw = stream.read(runtime.MAX_FILE_BYTES + 1)
                if len(raw) != item.size or _git_blob_sha1(raw) != expected[name][0]:
                    raise PinnedSourceError("pinned Git blob SHA-1 identity mismatch")
                total += len(raw)
                if total > runtime.MAX_STAGE_BYTES:
                    raise PinnedSourceError("pinned Git source exceeds source budget")
                assembled[name] = raw
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise PinnedSourceError("pinned Git archive malformed") from exc
    if set(assembled) != set(expected):
        raise PinnedSourceError("pinned Git source missing expected files")
    return assembled


def _git_clean_source(root: Path, rows: dict, label: str) -> dict[str, bytes]:
    """Read ONLY commit objects. Neither fetch nor checkout nor owner M."""
    _git_object_roots(root, label)
    requested = [
        "src/ucie_miner", "src/ucie_public",
        *sorted(set(rows[label]["c0"]) -
                set(rows[label]["python"])),
    ]
    output = _git(root, ["archive", "--format=tar",
                         PINNED[label][0], "--", *requested],
                  ceiling=MAX_ARCHIVE)
    return _validate_archived_source(output, rows[label])


def _owner_apply(root: Path) -> None:
    root = _root(root)
    try:
        expected = ROOT.resolve(strict=True)
        actual = root.resolve(strict=True)
        python = Path(sys.executable).resolve(strict=True)
        owner = (root / ".venv" / "Scripts" / "python.exe").resolve(
            strict=True)
    except (OSError, RuntimeError) as exc:
        raise PinnedSourceError("exact owner Python unavailable") from exc
    if (os.name != "nt" or actual != expected or python != owner
            or sys.implementation.name != "cpython"
            or sys.version_info[:2] != (3, 15) or sys.maxsize <= 2**32
            or sysconfig.get_config_var("Py_GIL_DISABLED") not in (None, 0)
            or bool(os.environ.get("CI")) or not sys.stdin.isatty()):
        raise PinnedSourceError("exact interactive owner Windows Python3.15 required")
    parent = root / "downloaded"
    ignore = root / ".gitignore"
    if (parent.is_symlink() or not parent.is_dir()
            or ignore.is_symlink() or not ignore.is_file()
            or "downloaded/" not in ignore.read_text("utf-8").splitlines()
            or (root / FINAL_ZIP).exists() or (root / FINAL_ZIP).is_symlink()
            or (root / RECEIPT).exists() or (root / RECEIPT).is_symlink()):
        raise PinnedSourceError("local Git-ignored output must be new/isolated")


def _member(name: str, raw: bytes, archive: ZipFile) -> None:
    item = ZipInfo(name, (2020, 1, 1, 0, 0, 0))
    item.compress_type = ZIP_DEFLATED
    item.create_system = 3
    item.external_attr = 0o100644 << 16
    archive.writestr(item, raw)


def _bundle(src: Path, doc: dict, wheels: dict) -> dict:
    expected_names = {"README.txt", "git-source-pins.json",
                      "A/" + product.FIRST_PARTY_WHEEL,
                      "B/ucie_public_only_demo-0.1.1-py3-none-any.whl"}
    versions = {}
    for slot in ("A", "B"):
        data = wheels[slot]
        if type(data) is not dict or data.get("version") != VERSION[slot]:
            raise PinnedSourceError("unexpected QA slot version")
        if data.get("wheel_name") not in (
            product.FIRST_PARTY_WHEEL,
            "ucie_public_only_demo-0.1.1-py3-none-any.whl",
        ):
            raise PinnedSourceError("unexpected QA wheel name")
        versions[slot] = {
            "version": VERSION[slot],
            "commit_sha": PINNED[slot][0],
            "wheel_sha256": data["sha256"],
            "first_party_python_files": data["file_count"],
        }
    result = {
        "schema": BUNDLE_SCHEMA,
        "status": "UCIE_FIRST_PARTY_QA_ONLY_NO_CUSTOMER_RELEASE",
        "pinned_manifest_schema": SCHEMA,
        "pinned_manifest_sha256": sha256(json.dumps(
            doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")).hexdigest(),
        "vendor_wheels_included": False,
        "complete_windows_installer": False,
        "customer_distribution_authorized": False,
        "slots": versions,
    }
    with ZipFile(src, "x", compression=ZIP_DEFLATED) as zipfile:
        _member("README.txt", README.encode("ascii"), zipfile)
        _member("git-source-pins.json", json.dumps(
            result, sort_keys=True, separators=(",", ":")
        ).encode("ascii"), zipfile)
        for slot in ("A", "B"):
            filename = "A/" + product.FIRST_PARTY_WHEEL if slot == "A" else (
                "B/ucie_public_only_demo-0.1.1-py3-none-any.whl")
            _member(filename, wheels[slot]["path"].read_bytes(), zipfile)
    _verify_bundle(src, result)
    return result


def _verify_bundle(path: Path, evidence: dict) -> dict:
    if (path.is_symlink() or not path.is_file()
            or not 100 < path.stat().st_size <= MAX_BUNDLE):
        raise PinnedSourceError("QA bundle missing/oversize")
    expected = {
        "README.txt", "git-source-pins.json",
        "A/" + product.FIRST_PARTY_WHEEL,
        "B/ucie_public_only_demo-0.1.1-py3-none-any.whl",
    }
    try:
        zipped = ZipFile(path)
    except (BadZipFile, OSError) as exc:
        raise PinnedSourceError("QA bundle ZIP malformed") from exc
    with zipped:
        names = zipped.namelist()
        if len(names) != len(expected) or set(names) != expected:
            raise PinnedSourceError("QA bundle missing/extra members")
        for item in zipped.infolist():
            if (item.file_size > MAX_BUNDLE or item.is_dir()
                    or (item.external_attr >> 16) & 0o170000 != 0o100000):
                raise PinnedSourceError("unsafe QA bundle archive metadata")
        try:
            metadata = json.loads(zipped.read("git-source-pins.json"))
        except (ValueError, UnicodeError, KeyError) as exc:
            raise PinnedSourceError("QA bundle provenance invalid") from exc
        if metadata != evidence or metadata.get("customer_distribution_authorized") is not False:
            raise PinnedSourceError("QA bundle source metadata mismatch")
        for slot in ("A", "B"):
            name = "A/" + product.FIRST_PARTY_WHEEL if slot == "A" else (
                "B/ucie_public_only_demo-0.1.1-py3-none-any.whl")
            raw = zipped.read(name)
            if sha256(raw).hexdigest() != evidence["slots"][slot]["wheel_sha256"]:
                raise PinnedSourceError("QA bundle first-party wheel SHA mismatch")
    return {"qa_bundle_bytes_verified": True,
            "vendor_wheels_excluded": True,
            "customer_distribution_authorized": False}


def export_once(root: Path, typed: str) -> dict:
    if typed != CONSENT:
        raise PinnedSourceError("owner source-only export consent missing")
    _owner_apply(root)
    doc, rows = _load_manifest(root)
    with TemporaryDirectory(prefix="ucie_pinned_git_a_b_", dir=root / "downloaded") as folder:
        scratch = Path(folder)
        wheels = {}
        for slot in ("A", "B"):
            src = _git_clean_source(root, rows, slot)
            out = scratch / slot
            out.mkdir()
            wheel = product._build_first_party_wheel(
                out, src, version=VERSION[slot])
            proof = product._inspect_first_party_wheel(
                wheel, src, version=VERSION[slot])
            if proof["file_count"] != len(rows[slot]["python"]):
                raise PinnedSourceError("Git archived wheel module count differs from exact manifest")
            wheels[slot] = {
                "version": VERSION[slot],
                "path": wheel, "sha256": proof["sha256"],
                "file_count": proof["file_count"],
                "wheel_name": wheel.name,
            }
        if (wheels["B"]["file_count"] != wheels["A"]["file_count"] + 2
                or wheels["A"]["sha256"] == wheels["B"]["sha256"]):
            raise PinnedSourceError("pinned A/B full source difference missing")
        staged = scratch / "two-commit-first-party-qa.zip"
        meta = _bundle(staged, doc, wheels)
        target = root / FINAL_ZIP
        if target.exists() or target.is_symlink():
            raise PinnedSourceError("QA source bundle output already exists")
        # Same-volume hard link is atomic and refuses overwrites. Scratch
        # cleanup drops only its own link; final UCIE-local QA bytes remain.
        try:
            os.link(staged, target)
        except OSError as exc:
            raise PinnedSourceError("atomic UCIE-local QA bundle promotion unavailable") from exc
        _verify_bundle(target, meta)
    receipt = {
        "schema": BUNDLE_SCHEMA,
        "status": "SOURCE_ONLY_TWO_EXACT_PUBLIC_GIT_COMMITS_STAGED_NOT_CUSTOMER_GO",
        "first_party_qa_bundle_sha256": sha256((root / FINAL_ZIP).read_bytes()).hexdigest(),
        "relative_bundle_path": FINAL_ZIP,
        "pinned_sha_A": A_SHA, "pinned_sha_B": B_SHA,
        "A_first_party_python_modules": 182, "B_first_party_python_modules": 184,
        "local_owner_modified_source_excluded": True,
        "vendor_wheels_included": False,
        "source_history_downloaded": False,
        "pip_install_or_vendor_execution": False,
        "rights_sbom_signing_and_clean_recipient_approved": False,
        "customer_distribution_authorized": False,
    }
    with (root / RECEIPT).open("x", encoding="ascii") as out:
        json.dump(receipt, out, ensure_ascii=True, sort_keys=True)
        out.write("\n")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE two reviewed Git commits: read-only source audit or consented source-only QA export"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    try:
        if args.apply:
            _owner_apply(root)
            typed = input("Type " + CONSENT + " to export first-party QA wheels ONLY: ")
            result = export_once(root, typed)
        else:
            result = preview(root)
    except (PinnedSourceError, OSError, ValueError, RuntimeError, EOFError):
        result = {
            "schema": SCHEMA,
            "status": "UCIE_C1_PINNED_GIT_SOURCE_GATE_FAILED_CLOSED",
            "customer_distribution_authorized": False,
            "owner_worktree_modified": False,
        }
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
