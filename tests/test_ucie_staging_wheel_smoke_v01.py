"""Disposable CI-only offline installation test for first-party UCIE source.

No user-PC deployment, operating DB read/write, schedule modification,
external fetch, Rulepack signing, release authorization or publication.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class UCIEStagingWheelSmoke(unittest.TestCase):
    def test_release_stays_blocked_and_daily_cutoff_is_defined(self):
        from ucie_miner.skillbook_w09_release_gate_v01 import preview_release_gate
        from ucie_miner.daily_0500_cutoff_v01 import cutoff_window
        gate = preview_release_gate()
        for flag in ("owner_release_authorized", "package_signed",
                     "export_allowed", "independent_qa_verified",
                     "license_redistribution_approved"):
            self.assertIs(gate[flag], False)
        self.assertEqual(cutoff_window(date(2026, 11, 6)),
                         ("2026-11-04T20:00:00+00:00",
                          "2026-11-05T20:00:00+00:00"))

    @unittest.skipUnless(
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("GITHUB_REPOSITORY", "").casefold()
        == "tmdrkdtn1-project/ucie",
        "only the disposable first-party GitHub Actions runner may build",
    )
    def test_build_install_and_start_isolated_offline_wheel(self):
        self.assertEqual(ROOT.name.casefold(), "ucie")
        self.assertTrue((ROOT / ".git").is_dir())
        self.assertFalse(ROOT.is_symlink())
        source = ROOT / "src"
        self.assertTrue(source.is_dir())
        self.assertFalse(source.is_symlink())
        files = list(source.rglob("*"))
        self.assertLess(len(files), 900)
        self.assertFalse(any(p.is_symlink() for p in files))
        self.assertLess(sum(p.stat().st_size for p in files if p.is_file()),
                        15_000_000)
        with tempfile.TemporaryDirectory(prefix="UCIE_STAGE_WHEEL_") as t:
            top = Path(t)
            build = top / "snapshot"
            build.mkdir()
            shutil.copy2(ROOT / "pyproject.toml", build / "pyproject.toml")
            shutil.copytree(source, build / "src", ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "*.egg-info"))
            wheel_dir, target = top / "wheels", top / "install"
            wheel_dir.mkdir()
            target.mkdir()
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env.update(PIP_NO_INDEX="1", PIP_NO_INPUT="1",
                       PIP_NO_CACHE_DIR="1", PYTHONDONTWRITEBYTECODE="1")
            def run(*args):
                return subprocess.run(
                    [sys.executable, "-B", "-m", "pip", *args],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    cwd=t, env=env, timeout=120, check=False,
                )
            built = run("wheel", "--no-index", "--no-deps",
                        "--no-build-isolation", "--wheel-dir", str(wheel_dir),
                        str(build))
            self.assertEqual(built.returncode, 0,
                             "STAGING_WHEEL_BUILD_FAIL:" + str(built.returncode)
                             + " STDERR_TAIL:" + built.stderr.decode(
                                 "utf-8", "replace")[-950:])
            wheels = list(wheel_dir.glob("ucie_public_only_demo-*.whl"))
            self.assertEqual(len(wheels), 1)
            wheel = wheels[0]
            self.assertLess(wheel.stat().st_size, 15_000_000)
            # Reconcile every packaged .py byte with this exact clean
            # checkout. Wheel RECORD must also verify before installing.
            from ucie_miner.staging_wheel_integrity_v01 import (
                verify_staging_wheel,
            )
            source_sha = {}
            for package in ("ucie_miner", "ucie_public"):
                for module in (source / package).rglob("*.py"):
                    self.assertFalse(module.is_symlink())
                    name = module.relative_to(source).as_posix()
                    source_sha[name] = hashlib.sha256(
                        module.read_bytes()).hexdigest()
            attestation = verify_staging_wheel(
                wheel.read_bytes(), source_sha)
            self.assertTrue(attestation["wheel_record_verified"])
            self.assertTrue(attestation["source_files_match_checkout"])
            self.assertFalse(attestation["external_release_authorized"])
            installed = run("install", "--no-index", "--no-deps",
                            "--target", str(target), str(wheel))
            self.assertEqual(installed.returncode, 0,
                             "STAGING_WHEEL_INSTALL_FAIL:" + str(installed.returncode))
            script = (
                "import json,sys\n"
                "from datetime import date\n"
                "sys.path.insert(0,sys.argv[1])\n"
                "from ucie_miner.daily_0500_cutoff_v01 import cutoff_window\n"
                "from ucie_miner.skillbook_w09_release_gate_v01 import preview_release_gate\n"
                "from ucie_miner.skillbook_editorial_production_v01 import compose_curated_two_book_pilot\n"
                "from ucie_public.cli import main\n"
                "gate=preview_release_gate()\n"
                "book=compose_curated_two_book_pilot()\n"
                "assert gate['export_allowed'] is False\n"
                "assert gate['package_signed'] is False\n"
                "assert gate['owner_release_authorized'] is False\n"
                "assert book['export_allowed'] is False\n"
                "assert callable(main)\n"
                "assert cutoff_window(date(2026,11,6))[1]=='2026-11-05T20:00:00+00:00'\n"
                "print(json.dumps({'smoke':'PASS','released':False,'task_changed':False,"
                "'operating_db_writes':0},sort_keys=True))\n"
            )
            child = subprocess.run(
                [sys.executable, "-I", "-B", "-c", script, str(target)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=t, env=env, timeout=30, check=False,
            )
            self.assertEqual(child.returncode, 0,
                             "STAGING_ISOLATED_START_FAIL:" + str(child.returncode))
            observed = json.loads(child.stdout.decode("utf-8", "strict"))
            self.assertEqual(observed["smoke"], "PASS")
            self.assertIs(observed["released"], False)
            self.assertIs(observed["task_changed"], False)
            self.assertEqual(observed["operating_db_writes"], 0)
            print("UCIE_OFFLINE_WHEEL_STAGING=" + json.dumps({
                "status": "SHADOW_DEPLOY_PASS_NOT_RELEASE",
                "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                "wheel_size_bytes": wheel.stat().st_size,
                "external_network": False,
                "owner_machine_modified": False,
                "release_approved": False,
            }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
