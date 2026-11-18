"""W17 owner staged-offline environment bundle: synthetic tests only.

No official package downloads or owner Git/D: operations run in CI. A real
owner explicitly authorizes any network or new-root Python action separately.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "ucie_owner_newroot_venv_once_v01.py"
W14 = ROOT / "scripts" / "ucie_owner_offline_runtime_prepare_v01.ps1"


def load_w17():
    spec = importlib.util.spec_from_file_location(
        "ucie_w17_owner_env_tests", SOURCE)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class UCIEW17OwnerEnvironmentBundleTests(unittest.TestCase):
    def test_default_contract_never_queries_host(self):
        m = load_w17()
        with patch.object(m, "_subprocess_prepare",
                          side_effect=AssertionError("must not run")):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(m.main([]), 0)
        receipt = json.loads(output.getvalue())
        self.assertEqual(receipt["status"],
                         "UCIE_W17_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(receipt["new_root_modified"])
        self.assertFalse(receipt["operating_root_or_db_modified"])
        self.assertFalse(receipt["c40_or_scheduled_tasks_modified"])

    def test_unauthorized_prepare_never_runs(self):
        m = load_w17()
        with patch.object(m, "_subprocess_prepare",
                          side_effect=AssertionError("must not run")):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(m.main(["--prepare"]), 2)
        self.assertEqual(json.loads(output.getvalue())["status"],
                         "UCIE_W17_EXPLICIT_OWNER_APPROVAL_REQUIRED")

    def test_fixed_four_official_package_releases(self):
        m = load_w17()
        self.assertEqual(m.ALLOWED, {
            "cryptography": "50.0.2",
            "setuptools": "80.9.0",
            "cffi": "2.1.1",
            "pycparser": "2.23",
        })
        code = SOURCE.read_text("utf-8")
        self.assertIn('https://pypi.org/simple', code)
        self.assertIn('f"https://pypi.org/pypi/{name}/{version}/json"', code)
        self.assertIn('"--only-binary=:all:"', code)
        self.assertIn('official.get("digests", {}).get("sha256") != value', code)
        self.assertIn('"--no-cache-dir"', code)
        self.assertIn('"--isolated", "download"', code)

    def test_official_wheel_sha_and_filename_synthetic_evidence(self):
        m = load_w17()
        with tempfile.TemporaryDirectory(prefix="UCIE_W17_WHEELS_") as temp:
            folder = Path(temp)
            records = {}
            for name, version in m.ALLOWED.items():
                filename = f"{name}-{version}-py3-none-any.whl"
                payload = f"UCIE_SYNTHETIC_{name}_{version}".encode()
                (folder / filename).write_bytes(payload)
                records[(name, version)] = {
                    "info": {"name": name, "version": version},
                    "urls": [{
                        "filename": filename,
                        "packagetype": "bdist_wheel",
                        "yanked": False,
                        "size": len(payload),
                        "digests": {"sha256": sha256(payload).hexdigest()},
                    }],
                }
            with patch.object(m, "_pypi_release_metadata",
                              side_effect=lambda n, v: records[(n, v)]):
                rows = m.verify_downloaded_wheels(folder)
                self.assertEqual(len(rows), 4)
                self.assertEqual({r["name"].split("-")[0] for r in rows},
                                 set(m.ALLOWED))
                (folder / "cffi-2.1.1-py3-none-any.whl").write_bytes(b"bad")
                with self.assertRaises(m.OwnerPrepError):
                    m.verify_downloaded_wheels(folder)
            (folder / "extra-1.0-py3-none-any.whl").write_bytes(b"x")
            with self.assertRaises(m.OwnerPrepError):
                m.verify_downloaded_wheels(folder)

    def test_w14_python_launcher_fallback_is_source_compatible(self):
        source = W14.read_text("utf-8")
        self.assertIn("Python\\pythoncore-3.15-64\\python.exe", source)
        self.assertIn("$baseArgs=@('-3.15')", source)
        self.assertIn("& $basePython @baseArgs -m venv $venv", source)
        self.assertIn('UCIE_W14_ALREADY_PARTIALLY_OR_FULLY_PREPARED', source)
        self.assertIn('--no-index --no-cache-dir', source)
        self.assertIn('UCIE_W14_ISOLATED_OFFLINE_PYTHON_RUNTIME_PREPARED',
                      source)

    def test_exact_pinned_git_source_and_no_live_cutover(self):
        code = SOURCE.read_text("utf-8")
        for required in (
            "07aa0970f1ef25dd5a8fbd76d2236e9783ae836c",
            "https://github.com/tmdrkdtn1-project/UCIE.git",
            'git("merge", "--ff-only", target_commit)',
            'f"{target_commit}:{SCRIPT_IN_GIT}"',
            "Path(__file__).read_bytes()",
            "UCIE_W17_PYPI_WHEEL_CHECKSUM_MISMATCH",
            "UCIE_W17_PREEXISTING_INSTALL_STATE_NO_RETRY",
            "UCIE_W17_NEWROOT_OFFLINE_VENV_READY__LIVE_CUTOVER_HOLD",
        ):
            self.assertIn(required, code)
        for forbidden in (
            "Set-ScheduledTask", "Start-ScheduledTask",
            "Stop-ScheduledTask", "cloudflared.exe",
            "sqlite3.connect(", "shutil.rmtree(", "git reset",
            "git clean", "D:\\UCIE_DATA", "D:\\UCIE_PREVIEW",
        ):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
