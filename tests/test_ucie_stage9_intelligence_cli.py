"""Stage 9 offline CLI tests: no network unless --live explicitly selected."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from test_ucie_stage9_intelligence import NOW, fake_fetch
from ucie_miner.public_discovery import discover_all_feeds

ROOT = Path(__file__).resolve().parents[1]


def call(args, data=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "ucie_miner", *args],
        input=data, text=True, capture_output=True,
        cwd=ROOT, env=env, timeout=15,
    )


class PublicIntelligenceCLI(unittest.TestCase):
    def test_live_requires_explicit_opt_in(self):
        out = call(["discover-public"])
        self.assertEqual(out.returncode, 2)
        self.assertEqual(json.loads(out.stdout)["status"], "FAIL_CLOSED")

    def test_live_rejects_unknown_private_source_without_network(self):
        out = call(["discover-public", "--live", "--source", "private/repository"])
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("invalid choice", out.stderr)

    def test_offline_public_receipt_routes_to_skill_tasks(self):
        snapshot = discover_all_feeds(fetch=fake_fetch, now=NOW)
        out = call(["preview-intelligence-stdin"], json.dumps(snapshot))
        self.assertEqual(out.returncode, 0, out.stderr)
        agenda = json.loads(out.stdout)
        self.assertEqual(agenda["status"], "UNVERIFIED_RESEARCH_AGENDA")
        self.assertEqual(agenda["skill_count"], 5)
        self.assertEqual(agenda["skill_tasks"]["task_count"], 5)
        self.assertFalse(agenda["model_weight_training"])
        self.assertFalse(agenda["production_approved"])

    def test_duplicate_json_keys_fail_closed(self):
        out = call(["preview-intelligence-stdin"],
                   '{"schema":"fake","schema":"override","feeds":[]}')
        self.assertEqual(out.returncode, 2)
        self.assertEqual(json.loads(out.stdout)["status"], "FAIL_CLOSED")

    def test_oversized_json_fail_closed(self):
        out = call(["preview-intelligence-stdin"], " " * 262145)
        self.assertEqual(out.returncode, 2)
        self.assertEqual(json.loads(out.stdout)["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
