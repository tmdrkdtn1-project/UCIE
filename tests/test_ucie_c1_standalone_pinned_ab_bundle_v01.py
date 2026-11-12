"""UCIE-only standalone reviewed Git source QA ZIP verifier safety tests.

No vendor package installs, no Git operations, no network, no customer files.
Synthetic inert first-party wheel ZIP is generated with Python stdlib only.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from ucie_miner import customer_full_product_offline_rehearsal_v01 as full
from ucie_miner import customer_pinned_git_source_v01 as pin


def standalone():
    file = (Path(__file__).resolve().parents[1] / "scripts" /
            "ucie_c1_verify_pinned_ab_qa_bundle_v01.py")
    spec = importlib.util.spec_from_file_location("ucie_c1_standalone_test", file)
    if spec is None or spec.loader is None:
        raise AssertionError("UCIE standalone verification source absent")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def inert_sources(b: bool) -> dict[str, bytes]:
    files = {
        "src/ucie_miner/__init__.py": b"# UCIE inert\n",
        "src/ucie_public/__init__.py": b"# UCIE public inert\n",
        "src/ucie_miner/customer_staging_v01.py": b"# UCIE four pillar inert\n",
        "src/ucie_miner/local_v1_app_v01.py": b"# UCIE V04 inert\n",
        "src/ucie_miner/customer_portable_preview_v01.py":
            b"# UCIE local inert\n",
    }
    if b:
        files[pin.B_ONLY_HEALTH] = b"# UCIE new selfcheck inert\n"
        files[pin.B_ONLY_LIFECYCLE] = b"# UCIE B-only lifecycle inert\n"
    return files


class UCIEStandalonePinnedABBundleV01Tests(unittest.TestCase):
    def setUp(self):
        self.verify_mod = standalone()
        self.tmp = TemporaryDirectory(prefix="UCIE_STANDALONE_QA_TEST_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _wheel(self, b: bool) -> tuple[bytes, dict]:
        source = inert_sources(b)
        slot = "B" if b else "A"
        out = self.root / slot
        out.mkdir(exist_ok=True)
        file = full._build_first_party_wheel(
            out, source, version=pin.VERSION[slot])
        expected = {
            k[4:]: (self.verify_mod._blob(v), len(v))
            for k, v in source.items()
        }
        return file.read_bytes(), expected

    def test_trust_anchor_matches_actual_reviewed_manifest(self):
        real = Path(__file__).resolve().parents[1]
        data = json.loads((real / pin.MANIFEST).read_text("ascii"))
        canonical = json.dumps(
            data, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True).encode("ascii")
        self.assertEqual(sha256(canonical).hexdigest(),
                         self.verify_mod.TRUSTED_MANIFEST_SHA256)
        self.assertEqual(len(data["slots"]["A"]["python_modules"]), 182)
        self.assertEqual(len(data["slots"]["B"]["python_modules"]), 184)

    def test_real_generated_inert_wheel_record_and_git_blob_sha1_pass(self):
        for slot in ("A", "B"):
            with self.subTest(slot=slot):
                contents, rows = self._wheel(slot == "B")
                result = self.verify_mod._wheel(contents, rows, slot)
                self.assertEqual(result["python_module_git_blobs_checked"],
                                 5 if slot == "A" else 7)
                self.assertTrue(result["RECORD_sha256_size_checked"])
                self.assertFalse(result["vendor_wheel_executed_or_installed"])

    def test_wrong_first_party_git_blob_fails_closed(self):
        contents, rows = self._wheel(False)
        wrong = dict(rows)
        target = "ucie_miner/customer_staging_v01.py"
        wrong[target] = ("0"*40, rows[target][1])
        with self.assertRaises(self.verify_mod.VerifyError):
            self.verify_mod._wheel(contents, wrong, "A")

    def test_forged_wheel_record_fails_before_any_code_execution(self):
        contents, rows = self._wheel(False)
        stream = io.BytesIO()
        with ZipFile(io.BytesIO(contents)) as source, ZipFile(
            stream, "w", ZIP_DEFLATED) as dest:
            for entry in source.infolist():
                data = source.read(entry.filename)
                if entry.filename == "ucie_miner/customer_staging_v01.py":
                    data += b"UCIE INERT NEGATIVE TAMPER"
                dest.writestr(entry, data)
        with self.assertRaises(self.verify_mod.VerifyError):
            self.verify_mod._wheel(stream.getvalue(), rows, "A")

    def test_wrong_distribution_version_or_unreviewed_payload_blocked(self):
        contents, rows = self._wheel(False)
        with self.assertRaises(self.verify_mod.VerifyError):
            self.verify_mod._wheel(contents, rows, "B")
        stream = io.BytesIO()
        with ZipFile(io.BytesIO(contents)) as src, ZipFile(
            stream, "w", ZIP_DEFLATED) as out:
            for entry in src.infolist():
                out.writestr(entry, src.read(entry.filename))
            out.writestr("../UNRELATED_PRODUCT.py",
                         b"# UCIE inert unauthorized member")
        with self.assertRaises(self.verify_mod.VerifyError):
            self.verify_mod._wheel(stream.getvalue(), rows, "A")

    def test_outer_traversal_and_missing_file_blocked_without_extraction(self):
        path = self.root / self.verify_mod.FILENAME
        with ZipFile(path, "w", ZIP_DEFLATED) as out:
            out.writestr("../outside.py", b"# UCIE fake")
            out.writestr("README.txt", b"NOT THE QA PRODUCT")
        with self.assertRaises(self.verify_mod.VerifyError):
            self.verify_mod.verify(path)
        wrong = self.root / "unknown.zip"
        wrong.write_bytes(path.read_bytes())
        with self.assertRaises(self.verify_mod.VerifyError):
            self.verify_mod.verify(wrong)

    def test_standalone_cli_wrong_input_no_network_or_install(self):
        fake = self.root / self.verify_mod.FILENAME
        log = io.StringIO()
        with patch("subprocess.run", side_effect=AssertionError("NO PIP")), patch(
            "urllib.request.urlopen", side_effect=AssertionError("NO NETWORK")
        ), redirect_stdout(log):
            code = self.verify_mod.main(["--bundle", str(fake)])
        self.assertEqual(code, 2)
        result = json.loads(log.getvalue())
        self.assertFalse(result["customer_distribution_authorized"])
        self.assertTrue(result["no_vendor_executed"])


if __name__ == "__main__":
    unittest.main()
