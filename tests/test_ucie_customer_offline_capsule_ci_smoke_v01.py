"""Clean first-party CI: build wheel, create capsule, install and run 4 pillars.

Guarded to GitHub Actions exact UCIE repo; no owner-machine deployment.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from ucie_miner.customer_offline_capsule_v01 import (
    STATUS, build_staging_capsule, verify_staging_capsule,
)

ROOT = Path(__file__).resolve().parents[1]


class CleanCapsuleSmoke(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("GITHUB_REPOSITORY", "").casefold()
        == "tmdrkdtn1-project/ucie",
        "clean UCIE GitHub Actions runner only",
    )
    def test_real_offline_wheel_capsule_and_isolated_four_pillars(self):
        self.assertEqual(ROOT.name.casefold(), "ucie")
        self.assertTrue((ROOT / ".git").is_dir())
        self.assertFalse(ROOT.is_symlink())
        source = ROOT / "src"
        files = list(source.rglob("*"))
        self.assertLess(len(files), 950)
        self.assertFalse(any(p.is_symlink() for p in files))
        self.assertLess(sum(p.stat().st_size for p in files if p.is_file()),
                        20_000_000)
        with tempfile.TemporaryDirectory(prefix="UCIE_C0_C1_") as temp:
            top = Path(temp)
            root = top / "UCIE"
            root.mkdir()
            (root / ".git").mkdir()
            (root / "dist").mkdir()
            shutil.copy2(ROOT / "pyproject.toml", root / "pyproject.toml")
            shutil.copytree(source, root / "src",
                            ignore=shutil.ignore_patterns(
                                "__pycache__", "*.pyc", "*.egg-info"))
            target = top / "installed"
            target.mkdir()
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env.update(PIP_NO_INDEX="1", PIP_NO_INPUT="1",
                       PIP_NO_CACHE_DIR="1", PYTHONDONTWRITEBYTECODE="1")

            def pip(*args):
                return subprocess.run(
                    [sys.executable, "-B", "-m", "pip", *args],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    cwd=temp, env=env, timeout=120, check=False)

            wheel_result = pip(
                "wheel", "--no-index", "--no-deps", "--no-build-isolation",
                "--wheel-dir", str(root / "dist"), str(root))
            self.assertEqual(wheel_result.returncode, 0,
                             "UCIE_OFFLINE_WHEEL_BUILD_NO_GO")
            wheels = list((root / "dist").glob(
                "ucie_public_only_demo-0.1.0-*.whl"))
            self.assertEqual(len(wheels), 1)
            report = build_staging_capsule(root, wheels[0].name)
            self.assertEqual(report["status"], STATUS)
            self.assertTrue(report["payload_sha256_verified"])
            self.assertFalse(report["customer_distribution_authorized"])
            checked = verify_staging_capsule(root, report["capsule_name"])
            self.assertEqual(checked["capsule_sha256"], report["capsule_sha256"])
            installed = pip("install", "--no-index", "--no-deps",
                            "--target", str(target), str(wheels[0]))
            self.assertEqual(installed.returncode, 0,
                             "UCIE_OFFLINE_WHEEL_INSTALL_NO_GO")
            smoke = (
                "import json,sys\n"
                "sys.path.insert(0,sys.argv[1])\n"
                "from ucie_miner.customer_staging_v01 import run_four_pillar_staging\n"
                "x=run_four_pillar_staging()\n"
                "assert x['four_pillars_exercised'] is True\n"
                "assert len(x['workflows'])==4\n"
                "assert x['customer_distribution_authorized'] is False\n"
                "assert x['complete_customer_functional_acceptance'] is False\n"
                "print(json.dumps({'pillars':4,'released':False}))\n")
            trial = subprocess.run(
                [sys.executable, "-I", "-B", "-c", smoke, str(target)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=temp, env=env, timeout=30, check=False)
            self.assertEqual(trial.returncode, 0,
                             "UCIE_OFFLINE_INSTALLED_4_PILLAR_NO_GO")
            observed = json.loads(trial.stdout.decode("utf-8", "strict"))
            self.assertEqual(observed, {"pillars": 4, "released": False})
            print("UCIE_C0_C1_CLEAN_CI=" + json.dumps({
                "status": "OFFLINE_CAPSULE_AND_4_PILLARS_STAGING_OBSERVED",
                "customer_distribution_authorized": False,
                "dependency_wheelhouse_included": False,
                "operating_db_writes": 0,
            }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
