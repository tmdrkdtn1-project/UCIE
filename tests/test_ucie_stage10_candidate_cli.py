"""Read-only Stage 10 CLI regression; no operating filesystem modification."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from test_ucie_stage9_batch import evidence, metadata, NOW
from ucie_miner.public_batch import build_public_batch, _fingerprint

ROOT = Path(__file__).resolve().parents[1]


def _cli(args, data=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "ucie_miner", *args],
        input=data, text=True, capture_output=True,
        cwd=ROOT, env=env, timeout=15,
    )


def _synthetic_receipt():
    return build_public_batch(
        metadata_fetch=metadata, evidence_fetch=evidence,
        now=NOW, max_enrich=2)


class Stage10CLI(unittest.TestCase):
    def test_default_cli_stages_only_ephemeral_unverified(self):
        data = json.dumps(_synthetic_receipt())
        result = _cli(["stage-public-candidates-stdin"], data)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(out["mode"], "EPHEMERAL_MEMORY_ONLY")
        self.assertEqual(out["new_identities"], 2)
        self.assertEqual(out["reviewer_signatures_attested"], 0)
        self.assertFalse(out["production_approved"])
        self.assertFalse(out["operating_knowledge_db_written"])

    def test_no_staging_file_written_by_default(self):
        stage = ROOT / "runtime" / "stage10_unverified_public_candidates.sqlite3"
        existed = stage.exists()
        self.assertEqual(
            _cli(["stage-public-candidates-stdin"],
                 json.dumps(_synthetic_receipt())).returncode, 0)
        self.assertEqual(stage.exists(), existed)

    def test_cli_duplicate_untrusted_properties_fail_closed(self):
        result = _cli(["stage-public-candidates-stdin"],
                      '{"status":"a","status":"b"}')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "FAIL_CLOSED")

    def test_cli_forged_approval_is_not_staged(self):
        receipt = _synthetic_receipt()
        receipt["candidate_skill_queue"][0]["human_approval_received"] = True
        receipt["candidate_queue_sha256"] = _fingerprint(
            receipt["candidate_skill_queue"])
        result = _cli(["stage-public-candidates-stdin"], json.dumps(receipt))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "FAIL_CLOSED")

    def test_cli_invalid_source_or_injection_is_not_executed(self):
        receipt = _synthetic_receipt()
        receipt["candidate_skill_queue"][0]["source"] = (
            "private/repository")
        receipt["candidate_queue_sha256"] = _fingerprint(
            receipt["candidate_skill_queue"])
        result = _cli(["stage-public-candidates-stdin"], json.dumps(receipt))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "FAIL_CLOSED")

    def test_cli_oversized_json_fails_closed(self):
        result = _cli(["stage-public-candidates-stdin"], " " * 262145)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
