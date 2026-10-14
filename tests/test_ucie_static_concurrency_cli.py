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

    def test_stdin_preview_links_pinned_nonexecuting_candidate(self):
        text = ("import os\n"
                "def f(directory, executor, worker):\n"
                "    raw = os.scandir(directory)\n"
                "    executor.submit(worker, raw)\n")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run(
            [sys.executable, "-m", "ucie_miner", "scan-python-stdin",
             "--preview-candidates"], input=text, capture_output=True,
            text=True, timeout=12, env=env, cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        obj = json.loads(result.stdout)
        self.assertEqual(obj["finding_count"], 1)
        self.assertEqual(obj["proposals"][0]["canonical_pr_number"], 153462)
        self.assertEqual(obj["proposals"][0]["stage6_regression_case"]
                         ["actual_test_result"], "NOT_EXECUTED")
        self.assertFalse(obj["source_digest_is_authoritative"])
        self.assertFalse(obj["production_approved"])
        self.assertFalse(obj["deploy_allowed"])

    def test_stdin_untrusted_json_preview_fails_closed_on_duplicate_keys(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run(
            [sys.executable, "-m", "ucie_miner", "preview-static-json-stdin"],
            input='{"schema":"good","schema":"overridden"}',
            capture_output=True, text=True, timeout=12, env=env, cwd=ROOT,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "FAIL_CLOSED")

    def test_stdin_untrusted_powershell_json_links_only_candidates(self):
        from ucie_miner.static_rule_bridge import SCANNER_GUIDANCE
        import hashlib
        data = {
            "schema": "UCIE_POWERSHELL_STATIC_CANDIDATES_V1",
            "source_sha256": hashlib.sha256(b"public-synthetic").hexdigest(),
            "finding_count": 1,
            "findings": [{
                "pattern_code": "PS_FUZZY_GET_COMMAND_DUPLICATES",
                "line": 1, "column": 1,
                "confidence": "STATIC_HEURISTIC_REVIEW_REQUIRED",
                "public_evidence":
                    "https://github.com/PowerShell/PowerShell/pull/28042",
                "safe_fix_guidance":
                    SCANNER_GUIDANCE["PS_FUZZY_GET_COMMAND_DUPLICATES"],
                "runtime_bug_reproduced": False,
            }],
            "parser_executed_supplied_code": False,
            "confidence": "HUMAN_REVIEW_REQUIRED",
            "approved_rules": 0, "source_files_read": 0,
            "persistent_writes": 0, "production_approved": False,
        }
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run(
            [sys.executable, "-m", "ucie_miner", "preview-static-json-stdin"],
            input=json.dumps(data), capture_output=True, text=True,
            timeout=12, env=env, cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        obj = json.loads(result.stdout)
        self.assertEqual(obj["finding_count"], 1)
        self.assertEqual(obj["proposals"][0]["canonical_pr_number"], 28042)
        self.assertEqual(obj["proposals"][0]["stage6_regression_case"]
                         ["actual_test_result"], "NOT_EXECUTED")
        self.assertFalse(obj["auto_promoted"])

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
