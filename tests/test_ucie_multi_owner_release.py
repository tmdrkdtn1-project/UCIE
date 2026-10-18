"""Synthetic-only tests of explicit two-rule owner-risk release controls."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from test_ucie_owner_risk_release import RUN, SHA, fake_api
from ucie_public.owner_release import JOBS
from ucie_public.policy import PolicyError
from ucie_public.rulepack import canonical_json, generate_keys, _private_key
from ucie_public.multi_owner_release import (
    CONFIRM, SECOND_RISK, RISK, SECOND_RUN, SECOND_SHA,
    SECOND_PR_BRANCH, POSTFIX_STEP, RULE_IDS, DECISIONS,
    publish_two_rule_owner_release, verify_two_rule_owner_release,
    _postfix_ci,
)


def fake_second():
    run = {
        "id": SECOND_RUN, "head_sha": SECOND_SHA,
        "repository": {"full_name": "tmdrkdtn1-project/UCIE"},
        "event": "pull_request", "head_branch": SECOND_PR_BRANCH,
        "status": "completed", "conclusion": "success",
    }
    jobs = []
    for name in sorted(JOBS):
        steps = []
        if name == "Offline test / ubuntu-latest / Python 3.15":
            steps.append({"name": POSTFIX_STEP, "status": "completed",
                          "conclusion": "success"})
        jobs.append({"run_id": SECOND_RUN, "name": name,
                     "status": "completed", "conclusion": "success",
                     "steps": steps})
    return run, {"total_count": 4, "jobs": jobs}


class TwoRuleOwnerGateTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "build").mkdir()
        self.private, self.public = generate_keys(
            self.root / "synthetic-owner", purpose="production")
        self.pack = self.root / "build" / "synthetic-two-rule.zip"
        self.main, self.main_jobs = fake_api()
        self.second, self.second_jobs = fake_second()

    def publish(self, **overrides):
        params = {
            "run_id": RUN, "serial": 9,
            "confirmation": CONFIRM, "risk_acceptance": RISK,
            "second_risk_acceptance": SECOND_RISK,
        }
        params.update(overrides)
        with (
            patch("ucie_public.multi_owner_release._local_clean_sha",
                  return_value=SHA),
            patch("ucie_public.owner_release._public_json",
                  side_effect=[self.main, self.main_jobs]),
            patch("ucie_public.multi_owner_release._public_json",
                  side_effect=[self.second, self.second_jobs]),
        ):
            return publish_two_rule_owner_release(
                self.root, self.private, self.pack, **params)

    def test_publisher_requires_three_distinct_owner_decisions(self):
        for values in [
            {"confirmation": "AUTO"},
            {"risk_acceptance": "YES"},
            {"second_risk_acceptance": "AUTO"},
            {"serial": True}, {"serial": 0},
        ]:
            with self.subTest(values=values), self.assertRaises(PolicyError):
                self.publish(**values)
            self.assertFalse(self.pack.exists())

    def test_first_v1_unchanged_two_rules_both_pinned_and_owner_signed(self):
        self.publish()
        result = verify_two_rule_owner_release(self.pack, self.public,
                                                min_serial=9)
        self.assertEqual(result["rule_ids"], list(RULE_IDS))
        self.assertEqual(result["rule_count"], 2)
        self.assertEqual(result["owner_signature"], "VALID")
        self.assertFalse(result["release_version_coverage_proven"])
        self.assertFalse(result["legal_license_signoff"])
        self.assertFalse(result["auto_apply"])
        self.assertFalse(result["independent_human_qa_approved"])
        with self.assertRaises(PolicyError):
            self.publish()   # no overwrite of any owner output

    def test_fail_closed_second_ci_missing_step_or_changed_sha(self):
        for change in ("missing_step", "wrong_sha", "wrong_branch", "failed"):
            run, jobs = fake_second()
            if change == "missing_step":
                jobs["jobs"][2]["steps"] = []
                for job in jobs["jobs"]:
                    job["steps"] = []
            elif change == "wrong_sha":
                run["head_sha"] = "0" * 40
            elif change == "wrong_branch":
                run["head_branch"] = "another-branch"
            else:
                run["conclusion"] = "failure"
            with self.subTest(change=change), patch(
                "ucie_public.multi_owner_release._public_json",
                side_effect=[run, jobs],
            ), self.assertRaises(PolicyError):
                _postfix_ci()

    def test_ci_must_match_clean_owner_main(self):
        with patch("ucie_public.multi_owner_release._local_clean_sha",
                   return_value="c" * 40), patch(
                "ucie_public.owner_release._public_json",
                side_effect=[self.main, self.main_jobs]):
            with self.assertRaises(PolicyError):
                publish_two_rule_owner_release(
                    self.root, self.private, self.pack, run_id=RUN,
                    serial=9, confirmation=CONFIRM, risk_acceptance=RISK,
                    second_risk_acceptance=SECOND_RISK)
        self.assertFalse(self.pack.exists())

    def test_expiry_min_serial_and_wrong_trust(self):
        self.publish()
        with self.assertRaises(PolicyError):
            verify_two_rule_owner_release(self.pack, self.public,
                                          min_serial=10)
        with self.assertRaises(PolicyError):
            verify_two_rule_owner_release(
                self.pack, self.public,
                at_time=datetime.now(timezone.utc) + timedelta(days=8))
        _, other = generate_keys(self.root / "other", purpose="production")
        with self.assertRaises(PolicyError):
            verify_two_rule_owner_release(self.pack, other)

    def test_forged_decision_or_escalation_even_resigned_is_denied(self):
        self.publish()
        with zipfile.ZipFile(self.pack) as z:
            files = {n: z.read(n) for n in z.namelist()}
        for change in ("swap_rules", "false_release", "remove_second_decision",
                       "promote_automation", "evidence_replace"):
            files2 = dict(files)
            m = json.loads(files2["manifest.json"])
            if change == "swap_rules":
                values = json.loads(files2["rules/prevention.json"])
                values.reverse()
                files2["rules/prevention.json"] = canonical_json(values)
                m["rule_sha256"] = __import__("hashlib").sha256(
                    files2["rules/prevention.json"]).hexdigest()
            elif change == "false_release":
                decisions = deepcopy(DECISIONS)
                decisions[1]["release_version_coverage_proven"] = True
                files2["evidence/rule_decisions.json"] = canonical_json(decisions)
                m["decisions_sha256"] = __import__("hashlib").sha256(
                    files2["evidence/rule_decisions.json"]).hexdigest()
            elif change == "remove_second_decision":
                files2["evidence/rule_decisions.json"] = canonical_json(DECISIONS[:1])
                m["decisions_sha256"] = __import__("hashlib").sha256(
                    files2["evidence/rule_decisions.json"]).hexdigest()
            elif change == "promote_automation":
                m["auto_apply"] = True
            else:
                evidence = json.loads(files2["evidence/automated_ci.json"])
                evidence["second_ci"]["head_sha"] = "f" * 40
                files2["evidence/automated_ci.json"] = canonical_json(evidence)
                m["evidence_sha256"] = __import__("hashlib").sha256(
                    files2["evidence/automated_ci.json"]).hexdigest()
            files2["manifest.json"] = canonical_json(m)
            files2["signatures/owner.sig"] = _private_key(self.private).sign(
                files2["manifest.json"])
            path = self.root / "build" / f"forged-{change}.zip"
            with zipfile.ZipFile(path, "w") as z:
                for name, contents in files2.items():
                    z.writestr(name, contents)
            with self.subTest(change=change), self.assertRaises(PolicyError):
                verify_two_rule_owner_release(path, self.public)

    def test_legacy_one_rule_pack_cannot_be_verified_as_new_pack(self):
        self.publish()
        with zipfile.ZipFile(self.pack) as z:
            names = set(z.namelist())
        self.assertEqual(len(names), 5)
        self.assertIn("evidence/rule_decisions.json", names)


if __name__ == "__main__":
    unittest.main()
