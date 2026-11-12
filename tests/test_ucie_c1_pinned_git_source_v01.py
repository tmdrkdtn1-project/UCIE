"""UCIE C1 reviewed Git commit source provenance and offline QA ZIP tests.

All fixtures and wheel bytes are FIRST-PARTY inert tests. NEVER git fetch,
checkout/reset, pip install, customer reads, real vendor imports or publishing.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha1, sha256
import io
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from ucie_miner import customer_pinned_git_source_v01 as pin
from ucie_miner import customer_full_product_offline_rehearsal_v01 as full
from ucie_miner.customer_component_lifecycle_v01 import FILES as C0_FILES


def tar_bytes(records: dict[str, bytes], *, linked: str = "",
              extra: str = "") -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, contents in sorted(records.items()):
            info = tarfile.TarInfo(name)
            info.mode = 0o644
            if name == linked:
                info.type = tarfile.SYMTYPE
                info.linkname = "../outside"
                info.size = 0
                archive.addfile(info)
            else:
                info.size = len(contents)
                archive.addfile(info, io.BytesIO(contents))
        if extra:
            info = tarfile.TarInfo(extra)
            info.size = 1
            archive.addfile(info, io.BytesIO(b"X"))
    return stream.getvalue()


def tiny_snapshot(b: bool) -> dict[str, bytes]:
    files = {
        "src/ucie_miner/__init__.py": b"# UCIE synthetic init\n",
        "src/ucie_public/__init__.py": b"# UCIE synthetic public\n",
        "src/ucie_miner/customer_staging_v01.py": b"# UCIE synthetic pillars\n",
        "src/ucie_miner/local_v1_app_v01.py": b"# UCIE synthetic localhost\n",
        "src/ucie_miner/customer_portable_preview_v01.py":
            b"# UCIE synthetic preview\n",
    }
    if b:
        files[pin.B_ONLY_HEALTH] = b"# UCIE B only inert health code\n"
        files[pin.B_ONLY_LIFECYCLE] = b"# UCIE B only inert A/B logic\n"
    return files


class UCIEPinnedGitSourceV01Tests(unittest.TestCase):
    def setUp(self):
        t = TemporaryDirectory(prefix="UCIE_C1_GIT_PIN_TEST_")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name) / "UCIE"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        (self.root / ".gitignore").write_text("downloaded/\n")
        for folder in ("src/ucie_miner", "src/ucie_public"):
            (self.root / folder).mkdir(parents=True)
            (self.root / folder / "__init__.py").write_text("# UCIE fixture\n")

    def test_real_repo_manifest_has_182_184_exact_commits_and_c0(self):
        real = Path(__file__).resolve().parents[1]
        if real.name.casefold() != "ucie" or not (real / ".git").is_dir():
            self.skipTest("first-party UCIE checkout only")
        doc, slots = pin._load_manifest(real)
        self.assertFalse(doc["customer_distribution_authorized"])
        self.assertEqual(set(slots), {"A", "B"})
        self.assertEqual(len(slots["A"]["python"]), 182)
        self.assertEqual(len(slots["B"]["python"]), 184)
        self.assertEqual(set(slots["A"]["c0"]), set(C0_FILES))
        self.assertEqual(set(slots["B"]["c0"]), set(C0_FILES))
        self.assertEqual(
            set(slots["B"]["python"]) - set(slots["A"]["python"]),
            {pin.B_ONLY_HEALTH, pin.B_ONLY_LIFECYCLE}
        )
        self.assertEqual(doc["slots"]["A"]["root_tree_sha1"], pin.TREE_A)
        self.assertEqual(doc["slots"]["B"]["root_tree_sha1"], pin.TREE_B)

    def test_real_owner_readonly_source_parity_counts_no_git_process(self):
        real = Path(__file__).resolve().parents[1]
        if real.name.casefold() != "ucie" or not (real / ".git").is_dir():
            self.skipTest("UCIE-only checkout")
        with patch("subprocess.run",
                   side_effect=AssertionError("NO GIT PIP OR PROCESS")), patch(
            "urllib.request.urlopen",
            side_effect=AssertionError("NO NETWORK")
        ):
            receipt = pin.preview(real)
        self.assertFalse(receipt["customer_distribution_authorized"])
        self.assertFalse(receipt["external_network_requests"])
        self.assertEqual(receipt["B_reviewed_first_party_python_files"], 184)
        self.assertEqual(receipt["C0_selected_components_per_commit"], 23)
        report = receipt["owner_worktree_reconciliation"]
        self.assertGreaterEqual(report["current_local_python_module_count"], 184)
        self.assertEqual(
            report["pinned_reviewed_b_python_module_count"], 184
        )
        print("UCIE_C1_REVIEWED_SOURCE_PARITY_COUNTS=" + json.dumps(
            {k: report[k] for k in (
                "current_local_python_module_count",
                "pinned_reviewed_b_python_module_count",
                "owner_local_python_files_changed",
                "owner_local_python_files_missing",
                "owner_local_extra_python_files_NOT_approved_for_export",
                "owner_selected_c0_components_changed",
                "owner_selected_c0_components_missing",
                "owner_current_worktree_exactly_reviewed_B",
            )}, sort_keys=True))

    def test_manifest_gate_rejects_forged_version_tree_policy_or_extra(self):
        real = Path(__file__).resolve().parents[1]
        if real.name.casefold() != "ucie" or not (real / ".git").is_dir():
            self.skipTest("first-party UCIE source required")
        baseline = json.loads((real / pin.MANIFEST).read_text("ascii"))
        dest = self.root / pin.MANIFEST
        dest.parent.mkdir(parents=True)
        mutations = (
            lambda d: d["slots"]["A"].__setitem__(
                "commit_sha", "0" * 40),
            lambda d: d["slots"]["B"].__setitem__(
                "root_tree_sha1", "f" * 40),
            lambda d: d.__setitem__("customer_distribution_authorized", True),
            lambda d: d["slots"]["B"]["python_modules"][0].__setitem__(
                0, "../UNCHECKED_REMOTE.py"),
            lambda d: d["slots"]["B"]["python_modules"].append(
                d["slots"]["B"]["python_modules"][-1].copy()),
            lambda d: d["slots"]["B"]["c0_inventory"].pop(),
        )
        for action in mutations:
            with self.subTest(action=str(action)):
                fake = json.loads(json.dumps(baseline))
                action(fake)
                dest.write_text(json.dumps(fake), encoding="ascii")
                with self.assertRaises(pin.PinnedSourceError):
                    pin._load_manifest(self.root)

    def test_git_blob_sha1_is_framed_not_raw_file_sha1(self):
        sample = b"UCIE-only audited synthetic content"
        expected = sha1(b"blob " + str(len(sample)).encode() +
                        b"\x00" + sample).hexdigest()
        self.assertEqual(pin._git_blob_sha1(sample), expected)
        self.assertNotEqual(pin._git_blob_sha1(sample), sha1(sample).hexdigest())

    def test_tar_archive_verified_without_extracting_or_executing(self):
        src = {
            "src/ucie_miner/__init__.py": b"# UCIE ONLY\n",
            "pyproject.toml": b"[project]\nname='ucie-test'\n",
        }
        expected = {
            "python": {"src/ucie_miner/__init__.py": (
                pin._git_blob_sha1(src["src/ucie_miner/__init__.py"]),
                len(src["src/ucie_miner/__init__.py"])
            )},
            "c0": {"pyproject.toml": (
                pin._git_blob_sha1(src["pyproject.toml"]),
                len(src["pyproject.toml"])
            )},
        }
        out = pin._validate_archived_source(tar_bytes(src), expected)
        self.assertEqual(out, src)
        with self.assertRaises(pin.PinnedSourceError):
            pin._validate_archived_source(tar_bytes(src, extra="outside.txt"), expected)
        with self.assertRaises(pin.PinnedSourceError):
            pin._validate_archived_source(
                tar_bytes(src, linked="pyproject.toml"), expected)
        corrupt = dict(src)
        corrupt["pyproject.toml"] += b"CHANGED"
        with self.assertRaises(pin.PinnedSourceError):
            pin._validate_archived_source(tar_bytes(corrupt), expected)
        with self.assertRaises(pin.PinnedSourceError):
            pin._validate_archived_source(
                tar_bytes({"pyproject.toml": src["pyproject.toml"]}), expected)

    def test_tar_archive_blocks_unknown_git_paths_and_duplicate(self):
        src = {"src/ucie_miner/__init__.py": b"A"}
        expected = {"python": {next(iter(src)): (
            pin._git_blob_sha1(b"A"), 1)}, "c0": {}}
        bad = tar_bytes(src, extra="../../unapproved.txt")
        with self.assertRaises(pin.PinnedSourceError):
            pin._validate_archived_source(bad, expected)
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            for _ in range(2):
                info = tarfile.TarInfo("src/ucie_miner/__init__.py")
                info.size = 1
                archive.addfile(info, io.BytesIO(b"A"))
        with self.assertRaises(pin.PinnedSourceError):
            pin._validate_archived_source(stream.getvalue(), expected)

    def test_git_command_restricts_read_only_objects_no_fetch(self):
        with patch("subprocess.run", side_effect=AssertionError("NO PROCESS")):
            for args in (
                ["fetch", "origin", "main"],
                ["reset", "--hard"],
                ["checkout", "main"],
                ["archive", "SPOOFED"],
            )[:3]:
                with self.assertRaises(pin.PinnedSourceError):
                    pin._git(self.root, args, ceiling=1000)

    def test_pinned_git_commit_tree_identity_must_match(self):
        calls = []
        class Fake:
            returncode = 0
            stderr = b""
            def __init__(self, stdout):
                self.stdout = stdout
        def fake_run(args, **kwargs):
            calls.append(args)
            if "cat-file" in args:
                return Fake(b"commit\n")
            if "rev-parse" in args:
                return Fake((pin.TREE_B + "\n").encode())
            raise AssertionError("only Git read allowed")
        with patch("subprocess.run", side_effect=fake_run):
            pin._git_object_roots(self.root, "B")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], "git")
        self.assertIn("--no-optional-locks", calls[0])
        with patch("subprocess.run", return_value=Fake(b"WRONG_TREE\n")):
            with self.assertRaises(pin.PinnedSourceError):
                pin._git_object_roots(self.root, "B")

    def test_qa_bundle_two_actual_inert_first_party_wheels_and_source_hashes(self):
        with TemporaryDirectory(prefix="UCIE_INERT_PINNED_BUNDLE_") as temp:
            tmp = Path(temp)
            versions = {}
            for slot in ("A", "B"):
                where = tmp / slot
                where.mkdir()
                source = tiny_snapshot(slot == "B")
                wheel = full._build_first_party_wheel(
                    where, source, version=pin.VERSION[slot])
                inspected = full._inspect_first_party_wheel(
                    wheel, source, version=pin.VERSION[slot])
                versions[slot] = {
                    "version": pin.VERSION[slot],
                    "path": wheel,
                    "sha256": inspected["sha256"],
                    "file_count": inspected["file_count"],
                    "wheel_name": wheel.name,
                }
            result = pin._bundle(tmp / "FIRST_PARTY_ONLY.zip",
                                 {"schema": pin.SCHEMA}, versions)
            self.assertEqual(
                set(result["slots"]), {"A", "B"})
            self.assertFalse(result["vendor_wheels_included"])
            self.assertTrue(pin._verify_bundle(
                tmp / "FIRST_PARTY_ONLY.zip", result
            )["qa_bundle_bytes_verified"])
            with ZipFile(tmp / "FIRST_PARTY_ONLY.zip") as zipped:
                self.assertEqual(len(zipped.namelist()), 4)
                self.assertNotIn("cffi", " ".join(zipped.namelist()))
                self.assertNotIn("cryptography", " ".join(zipped.namelist()))
            altered = dict(result)
            altered["customer_distribution_authorized"] = True
            with self.assertRaises(pin.PinnedSourceError):
                pin._verify_bundle(tmp / "FIRST_PARTY_ONLY.zip", altered)

    def test_owner_apply_denied_on_fixture_even_with_valid_consent(self):
        with patch("subprocess.run",
                   side_effect=AssertionError("NO OWNER GIT OR NETWORK")):
            with self.assertRaises(pin.PinnedSourceError):
                pin._owner_apply(self.root)
            with self.assertRaises(pin.PinnedSourceError):
                pin.export_once(self.root, "WRONG_CONSENT")

    def test_cli_default_preview_rejects_missing_manifest_without_network(self):
        fakefile = (self.root / "src" / "ucie_miner" /
                    "customer_pinned_git_source_v01.py")
        output = io.StringIO()
        with patch.object(pin, "__file__", str(fakefile)), patch(
            "subprocess.run", side_effect=AssertionError("NO GIT")
        ), redirect_stdout(output):
            result = pin.main([])
        self.assertEqual(result, 2)
        parsed = json.loads(output.getvalue())
        self.assertFalse(parsed["customer_distribution_authorized"])
        self.assertEqual(parsed["status"],
                         "UCIE_C1_PINNED_GIT_SOURCE_GATE_FAILED_CLOSED")


if __name__ == "__main__":
    unittest.main()
