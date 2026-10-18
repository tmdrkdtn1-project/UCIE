"""Synthetic-only checks for owner-risk release policy and CI evidence gate.

Mocked GitHub data must NEVER be treated as real CI or independent QA.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from ucie_public.policy import PolicyError
from ucie_public.prevention_rulepack import verify_prevention_review
from ucie_public.rulepack import generate_keys, canonical_json, _private_key
from ucie_public.owner_release import (
    CONFIRM, RISK, JOBS, REPO, WORKFLOW, STEP_RUNTIME,
    STEP_PS51, STEP_STAGE4, _check_evidence, validate_live_automated_qa,
    publish_owner_risk_release, verify_owner_risk_release,
)

SHA = "a" * 40
RUN = 777777


def fake_api():
    run = {
        "id": RUN, "head_sha": SHA,
        "repository": {"full_name": REPO},
        "path": WORKFLOW,
        "event": "push", "head_branch": "main",
        "status": "completed", "conclusion": "success",
    }
    jobs = []
    for name in sorted(JOBS):
        steps = []
        if name.endswith("3.15"):
            steps.append({"name": STEP_RUNTIME, "status": "completed",
                          "conclusion": "success"})
        if "windows-latest" in name:
            steps.extend([
                {"name": STEP_PS51, "status": "completed", "conclusion": "success"},
                {"name": STEP_STAGE4, "status": "completed", "conclusion": "success"},
            ])
        jobs.append({
            "run_id": RUN, "name": name,
            "status": "completed", "conclusion": "success",
            "steps": steps,
        })
    return run, {"total_count": 4, "jobs": jobs}


class OwnerRiskApprovalTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "build").mkdir()
        self.private, self.public = generate_keys(
            self.root / "owner", purpose="production")
        self.pack = self.root / "build" / "owner-only.zip"
        self.run, self.jobs = fake_api()

    def publish(self, **overrides):
        params = dict(run_id=RUN, serial=7,
                      confirmation=CONFIRM, risk_acceptance=RISK)
        params.update(overrides)
        with (patch("ucie_public.owner_release._local_clean_sha", return_value=SHA),
              patch("ucie_public.owner_release._public_json",
                    side_effect=[self.run, self.jobs])):
            return publish_owner_risk_release(
                self.root, self.private, self.pack, **params)

    def test_requires_separate_explicit_risk_consent(self):
        with self.assertRaises(PolicyError):
            self.publish(risk_acceptance="YES")
        with self.assertRaises(PolicyError):
            self.publish(confirmation="AUTOMATIC")
        self.assertFalse(self.pack.exists())

    def test_owner_public_only_signed_channel_and_receiver(self):
        self.publish()
        receipt = verify_owner_risk_release(self.pack, self.public,
                                           min_serial=7)
        self.assertEqual(receipt["result"],
                         "OWNER_RISK_ACCEPTED_PUBLIC_RULEPACK_VERIFIED")
        self.assertEqual(receipt["approval_mode"],
                         "AUTOMATED_QA_OWNER_RISK_ACCEPTED")
        self.assertEqual(receipt["source_commit_sha"], SHA)
        self.assertEqual(receipt["owner_signature"], "VALID")
        self.assertFalse(receipt["independent_human_qa_approved"])
        self.assertFalse(receipt["legal_license_signoff"])
        self.assertTrue(receipt["owner_risk_accepted"])
        self.assertTrue(receipt["production_approved"])
        self.assertFalse(receipt["auto_apply"])
        self.assertEqual(receipt["scope"], "PUBLIC_ONLY_MANUAL_STATIC_SCAN")
        with self.assertRaises(PolicyError):
            verify_prevention_review(self.pack, self.public)
        with self.assertRaises(PolicyError):
            self.publish()  # no overwrite

    def test_missing_or_forged_ci_matrix_rejected(self):
        self.jobs["jobs"][0]["conclusion"] = "failure"
        with self.assertRaises(PolicyError):
            self.publish()
        self.assertFalse(self.pack.exists())
        self.run, self.jobs = fake_api()
        self.jobs["jobs"][2]["steps"] = []
        with self.assertRaises(PolicyError):
            self.publish()
        self.run, self.jobs = fake_api()
        self.run["event"] = "pull_request"
        with self.assertRaises(PolicyError):
            self.publish()
        self.run, self.jobs = fake_api()
        self.run["repository"]["full_name"] = "unapproved/project"
        with self.assertRaises(PolicyError):
            self.publish()

    def test_ci_run_must_match_clean_owner_main_checkout(self):
        with (patch("ucie_public.owner_release._local_clean_sha",
                    return_value="b"*40),
              patch("ucie_public.owner_release._public_json",
                    side_effect=[self.run, self.jobs])):
            with self.assertRaises(PolicyError):
                publish_owner_risk_release(
                    self.root, self.private, self.pack, run_id=RUN,
                    serial=7, confirmation=CONFIRM, risk_acceptance=RISK)
        self.assertFalse(self.pack.exists())

    def test_signature_tamper_replay_and_expiry(self):
        self.publish()
        with self.assertRaises(PolicyError):
            verify_owner_risk_release(self.pack, self.public, min_serial=8)
        with self.assertRaises(PolicyError):
            verify_owner_risk_release(
                self.pack, self.public,
                at_time=datetime.now(timezone.utc) + timedelta(days=10))
        _, different_pub = generate_keys(
            self.root / "another", purpose="production")
        with self.assertRaises(PolicyError):
            verify_owner_risk_release(self.pack, different_pub)
        with zipfile.ZipFile(self.pack) as original:
            blobs = {n: original.read(n) for n in original.namelist()}
        claim = json.loads(blobs["manifest.json"])
        claim["independent_human_qa_approved"] = True
        blobs["manifest.json"] = canonical_json(claim)
        # Re-signing a FAKE independent human claim with a valid OWNER key
        # still cannot make it pass the separated automated-QA channel.
        blobs["signatures/owner.sig"] = _private_key(self.private).sign(
            blobs["manifest.json"])
        changed = self.root / "build" / "changed.zip"
        with zipfile.ZipFile(changed, "w") as archive:
            for name, data in blobs.items():
                archive.writestr(name, data)
        with self.assertRaises(PolicyError):
            verify_owner_risk_release(changed, self.public)

    def test_signed_evidence_cannot_claim_independent_qa(self):
        self.publish()
        with zipfile.ZipFile(self.pack) as z:
            evidence = json.loads(z.read("evidence/automated_ci.json"))
        self.assertEqual(evidence["run_id"], RUN)
        self.assertIs(evidence["independent_human_qa"], False)
        self.assertIs(evidence["legal_license_signoff"], False)
        _check_evidence(evidence)
        evidence["independent_human_qa"] = True
        with self.assertRaises(PolicyError):
            _check_evidence(evidence)


if __name__ == "__main__":
    unittest.main()
