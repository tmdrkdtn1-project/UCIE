"""UCIE pure internal metadata processing: no external AI, IO or runtime mutation."""
from __future__ import annotations

import copy
import socket
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from ucie_miner.internal_skillbook_batch import (
    process_metadata_batch, InternalSkillBookEngineError,
)

FIRST = {
    "kind": "REUSABLE_SKILL",
    "source_id": "repo:python/cpython",
    "evidence_reference": "pr:2024:" + "a" * 40,
    "evidence_sha256": "c" * 64,
    "purpose_code": "SKILL_TEST_AUTOMATION",
    "version_scope": "3.15",
    "dependencies": [],
}
SECOND = {
    "kind": "LEARNING_LOGIC",
    "source_id": "repo:PowerShell/PowerShell",
    "evidence_reference": "pr:2025:" + "b" * 40,
    "evidence_sha256": "d" * 64,
    "purpose_code": "LEARNING_FEEDBACK_LOOP",
    "version_scope": "7.4",
    "dependencies": [],
}


class InternalSkillbookBatchTests(unittest.TestCase):
    def test_local_execution_deduplicates_requests_without_ai_or_io(self):
        tasks = [
            {"topic": "AUTOMATION_TECHNIQUES", "candidates": [FIRST, SECOND]},
            {"topic": "AUTOMATION_TECHNIQUES", "candidates": [FIRST, SECOND]},
            {"topic": "TEST_RECIPES", "candidates": [FIRST]},
        ]
        with patch.object(socket, "socket", side_effect=AssertionError("network prohibited")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("process prohibited")), \
             patch.object(Path, "open", side_effect=AssertionError("filesystem prohibited")):
            result = process_metadata_batch(tasks)
        self.assertEqual(result["jobs_processed"], 3)
        self.assertEqual(result["distinct_job_inputs"], 2)
        self.assertEqual(result["local_cache_hits"], 1)
        self.assertEqual(result["external_ai_api_calls"], 0)
        self.assertEqual(result["local_language_model_calls"], 0)
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertFalse(result["task_queue_mutated"])
        self.assertFalse(result["skillbook_verified_or_published"])
        self.assertEqual(result["results"][0]["blueprint_id"],
                         result["results"][1]["blueprint_id"])

    def test_never_accepts_unauthorized_public_sources_or_fake_approval(self):
        for forged in (
            dict(FIRST, source_id="repo:unknown/unknown"),
            dict(FIRST, approval_status="OWNER_APPROVED"),
            dict(FIRST, export_allowed=True),
        ):
            with self.assertRaises(InternalSkillBookEngineError):
                process_metadata_batch([{"topic": "TEST_RECIPES", "candidates": [forged]}])

    def test_rejects_private_task_fields_unbounded_and_invalid_types(self):
        samples = [
            [],
            [{"topic": "AAA", "candidates": [FIRST]}] * 9,
            [{"topic": "AAA", "candidates": [FIRST], "private_project": "secret"}],
            [{"topic": "AAA", "candidates": [FIRST] * 81}],
            [{"topic": "../private", "candidates": [FIRST]}],
            [{"topic": "TEST_RECIPES", "candidates": [copy.deepcopy(FIRST)] * 2}],
            [{"topic": "TEST_RECIPES", "candidates": [{"kind": "SKILL"}]}],
        ]
        for tasks in samples:
            with self.subTest(tasks=len(tasks)), self.assertRaises(InternalSkillBookEngineError):
                process_metadata_batch(tasks)

    def test_deterministic_output_and_no_input_mutation(self):
        tasks = [{"topic": "TEST_RECIPES", "candidates": [FIRST, SECOND]}]
        before = copy.deepcopy(tasks)
        self.assertEqual(process_metadata_batch(tasks), process_metadata_batch(tasks))
        self.assertEqual(tasks, before)


if __name__ == "__main__":
    unittest.main()
