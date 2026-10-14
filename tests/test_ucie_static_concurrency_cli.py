"""Only an explicitly supplied synthetic text stream is parsed by UCIE CLI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CandidateScanCLITests(unittest.TestCase):
    @staticmethod
    def invoke(source):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "ucie_miner", "scan-python-stdin"],
            input=source, capture_output=True, text=True, timeout=12,
            env=env, cwd=ROOT,
        )

    def test_stdin_scan_returns_only_review_candidates(self):
        source = ("import os\n"
                  "def candidate(p, executor, consumer):\n"
                  "    it = os.scandir(p)\n"
                  "    executor.submit(consumer, it)\n")
        result = self.invoke(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        obj = json.loads(result.stdout)
        self.assertEqual(obj["finding_count"], 1)
        self.assertEqual(obj["approved_rules"], 0)
        self.assertFalse(obj["production_approved"])
        self.assertEqual(obj["source_files_read"], 0)
        self.assertEqual(obj["persistent_writes"], 0)
        self.assertNotIn(source, result.stdout)

    def test_invalid_snippet_fails_closed_without_executing(self):
        result = self.invoke("def unfinished(:\n")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"],
                         "FAIL_CLOSED")

    def test_oversized_snippet_fails_closed(self):
        result = self.invoke("x = 1\n" * 30000)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"],
                         "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
