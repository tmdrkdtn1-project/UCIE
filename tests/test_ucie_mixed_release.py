"""Synthetic-only mixed-language signature and source/approval regression."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from test_ucie_owner_risk_release import RUN, SHA, fake_api
from test_ucie_multi_review import scanner_receipt
from ucie_miner.static_concurrency import inspect_python_scandir_source
from ucie_public.policy import PolicyError
from ucie_public.rulepack import generate_keys, _private_key, canonical_json, digest
from ucie_public.selected_release import (
    verify_selected_owner_release, EXPECTED_SECOND_CI, EXPECTED_THIRD_CI,
)
from ucie_public.owner_release import JOBS
from ucie_public.rule_matcher import match_signed_static_rules
from ucie_public.mixed_release import (
    CONFIRM, FOURTH_ID, FOURTH_CI, FOURTH_RUN, FOURTH_SHA,
    FOURTH_BRANCH, SAFE_STEP, SOURCE_STEP,
    ELIGIBLE, RULE_ORDER, selected_payload, _fourth_ci,
    publish_mixed_owner_release, verify_mixed_owner_release,
    scan_mixed_owner_receipt,
)


PY_BAD = """import os
from concurrent.futures import ThreadPoolExecutor
def run(folder, f):
    iterator = os.scandir(folder)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return pool.submit(f, iterator).result()
"""
PY_GOOD = """def run(folder, pool, f):
    with GuardedScandir(folder) as it:
        return pool.submit(f, it).result()
"""


def fake_fourth():
    run = {
        "id": FOURTH_RUN, "head_sha": FOURTH_SHA,
        "repository": {"full_name": "tmdrkdtn1-project/UCIE"},
        "path": ".github/workflows/stage1-offline-tests.yml@branch",
        "event": "pull_request", "head_branch": FOURTH_BRANCH,
        "status": "completed", "conclusion": "success",
    }
    jobs = []
    for name in sorted(JOBS):
        steps = [{"name": SAFE_STEP, "status": "completed",
                  "conclusion": "success"}]
        if name == "Offline test / ubuntu-latest / Python 3.15":
            steps.append({"name": SOURCE_STEP, "status": "completed",
                          "conclusion": "success"})
        jobs.append({
            "run_id": FOURTH_RUN, "name": name, "status": "completed",
            "conclusion": "success", "steps": steps,
        })
    return run, {"total_count": 4, "jobs": jobs}


class MixedOwnerSigningTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "build").mkdir()
        self.priv, self.trust = generate_keys(
            self.root / "synthetic", purpose="production")
        self.pack = self.root / "build" / "mixed-four.zip"
        self.main, self.jobs = fake_api()

    def publish(self, ids=None, **overrides):
        ids = list(RULE_ORDER) if ids is None else ids
        kwargs = {
            "run_id": RUN, "serial": 4, "rule_ids": ids,
            "confirmation": CONFIRM,
            "risk_acceptances": {
                rid: ELIGIBLE[rid][2] for rid in ids if rid in ELIGIBLE},
        }
        kwargs.update(overrides)
        with (
            patch("ucie_public.mixed_release._local_clean_sha",
                  return_value=SHA),
            patch("ucie_public.owner_release._public_json",
                  side_effect=[self.main, self.jobs]),
            patch("ucie_public.mixed_release._postfix_ci",
                  return_value=EXPECTED_SECOND_CI),
            patch("ucie_public.mixed_release._third_ci",
                  return_value=EXPECTED_THIRD_CI),
            patch("ucie_public.mixed_release._fourth_ci",
                  return_value=FOURTH_CI),
        ):
            return publish_mixed_owner_release(
                self.root, self.priv, self.pack, **kwargs)

    def test_four_signed_rules_power_shell_and_python_inert_receipts(self):
        self.publish()
        verified = verify_mixed_owner_release(
            self.pack, self.trust, min_serial=4)
        self.assertEqual(verified["rule_count"], 4)
        self.assertEqual(verified["rule_ids"], list(RULE_ORDER))
        self.assertFalse(verified["auto_apply"])
        self.assertFalse(verified["fixed_python_3_15_0_coverage_proven"])
        self.assertFalse(verified["unsafe_native_race_retested"])
        ps = scan_mixed_owner_receipt(
            self.pack, self.trust, scanner_receipt())
        self.assertEqual(ps["finding_count"], 2)
        self.assertEqual(
            [x["rule_id"] for x in ps["findings"]], list(RULE_ORDER[:2]))
        py = scan_mixed_owner_receipt(
            self.pack, self.trust,
            inspect_python_scandir_source(PY_BAD))
        self.assertEqual(py["finding_count"], 1)
        self.assertEqual(py["findings"][0]["rule_id"], FOURTH_ID)
        self.assertEqual(py["findings"][0]["thread_boundary"],
                         "EXECUTOR_ARGUMENT")
        self.assertEqual(py["persistent_writes"], 0)
        self.assertFalse(py["source_executed"])
        clean = scan_mixed_owner_receipt(
            self.pack, self.trust,
            inspect_python_scandir_source(PY_GOOD))
        self.assertEqual(clean["finding_count"], 0)
        # Old Serial 3 envelope must remain a DIFFERENT immutable format.
        with self.assertRaises(PolicyError):
            verify_selected_owner_release(self.pack, self.trust)

    def test_unsigned_python_never_activates_in_subset(self):
        self.publish(ids=list(RULE_ORDER[:3]))
        verified = verify_mixed_owner_release(self.pack, self.trust)
        self.assertEqual(verified["rule_count"], 3)
        py = scan_mixed_owner_receipt(
            self.pack, self.trust,
            inspect_python_scandir_source(PY_BAD))
        self.assertEqual(py["finding_count"], 0)
        with zipfile.ZipFile(self.pack) as archive:
            ev = json.loads(archive.read("evidence/automated_ci.json"))
        self.assertIsNone(ev["fourth_ci"])

    def test_legacy_matcher_rejects_python_receipts(self):
        rule = deepcopy(ELIGIBLE[FOURTH_ID][0])
        with self.assertRaises(PolicyError):
            match_signed_static_rules(
                inspect_python_scandir_source(PY_BAD), [rule],
                expected_approval="AUTOMATED_QA_OWNER_RISK_ACCEPTED")
        found = match_signed_static_rules(
            inspect_python_scandir_source(PY_BAD), [rule],
            expected_approval="AUTOMATED_QA_OWNER_RISK_ACCEPTED",
            allow_python=True)
        self.assertEqual(len(found), 1)

    def test_unapproved_or_out_of_order_fifth_rule_rejected(self):
        for ids in (
            [], list(reversed(RULE_ORDER)), list(RULE_ORDER) + [FOURTH_ID],
            [*RULE_ORDER, "PY_QSBR_THREADSTATE_SLOT_LEAK"],
        ):
            with self.subTest(ids=ids), self.assertRaises(PolicyError):
                selected_payload(ids)

    def test_requires_separate_owner_consent_and_clean_main(self):
        for overrides in (
            {"confirmation": "AUTO_APPROVED"},
            {"risk_acceptances": {
                rid: ELIGIBLE[rid][2] for rid in RULE_ORDER[:3]}},
            {"risk_acceptances": {
                **{rid: ELIGIBLE[rid][2] for rid in RULE_ORDER},
                FOURTH_ID: "I_DONT_ACCEPT_UNPATCHED_RELEASE"}},
            {"serial": 3}, {"serial": True},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(PolicyError):
                self.publish(**overrides)
            self.assertFalse(self.pack.exists())

    def test_exact_live_fourth_ci_and_negative_claims(self):
        good, jobs = fake_fourth()
        with patch("ucie_public.mixed_release._public_json",
                   side_effect=[good, jobs]):
            self.assertEqual(_fourth_ci(), FOURTH_CI)
        for change in ("branch", "sha", "failed", "missing_safe",
                       "missing_source"):
            r, j = deepcopy(good), deepcopy(jobs)
            if change == "branch":
                r["head_branch"] = "unknown"
            elif change == "sha":
                r["head_sha"] = "f" * 40
            elif change == "failed":
                r["conclusion"] = "failure"
            elif change == "missing_safe":
                j["jobs"][0]["steps"] = []
            else:
                target = next(x for x in j["jobs"] if
                    x["name"] == "Offline test / ubuntu-latest / Python 3.15")
                target["steps"] = [
                    x for x in target["steps"] if x["name"] != SOURCE_STEP]
            with self.subTest(change=change), patch(
                "ucie_public.mixed_release._public_json",
                side_effect=[r, j],
            ), self.assertRaises(PolicyError):
                _fourth_ci()

    def test_signature_tamper_even_after_resigning_not_approved(self):
        self.publish()
        with zipfile.ZipFile(self.pack) as z:
            original = {name: z.read(name) for name in z.namelist()}
        for mutation in ("extra", "no_source", "pretend_fixed",
                         "changed_guidance", "auto_apply"):
            blobs = dict(original)
            m = json.loads(blobs["manifest.json"])
            if mutation == "extra":
                m["rule_ids"].append("PY_QSBR_THREADSTATE_SLOT_LEAK")
                m["rule_count"] += 1
            elif mutation == "no_source":
                ev = json.loads(blobs["evidence/automated_ci.json"])
                ev["fourth_ci"] = None
                blobs["evidence/automated_ci.json"] = canonical_json(ev)
                m["evidence_sha256"] = digest(blobs["evidence/automated_ci.json"])
            elif mutation == "pretend_fixed":
                d = json.loads(blobs["evidence/rule_decisions.json"])
                d[-1]["fixed_released_version_coverage_proven"] = True
                blobs["evidence/rule_decisions.json"] = canonical_json(d)
                m["decisions_sha256"] = digest(blobs["evidence/rule_decisions.json"])
            elif mutation == "changed_guidance":
                rr = json.loads(blobs["rules/prevention.json"])
                rr[-1]["safe_guidance"] = "AUTO_REWRITE"
                blobs["rules/prevention.json"] = canonical_json(rr)
                m["rules_sha256"] = digest(blobs["rules/prevention.json"])
            else:
                m["auto_apply"] = True
            blobs["manifest.json"] = canonical_json(m)
            blobs["signatures/owner.sig"] = _private_key(self.priv).sign(
                blobs["manifest.json"])
            where = self.root / "build" / f"forged-{mutation}.zip"
            with zipfile.ZipFile(where, "w") as z:
                for name, payload in blobs.items():
                    z.writestr(name, payload)
            with self.subTest(mutation=mutation), self.assertRaises(PolicyError):
                verify_mixed_owner_release(where, self.trust)

    def test_rollbacks_expiry_wrong_key_and_no_overwrite(self):
        self.publish()
        with self.assertRaises(PolicyError):
            verify_mixed_owner_release(self.pack, self.trust, min_serial=5)
        with self.assertRaises(PolicyError):
            verify_mixed_owner_release(
                self.pack, self.trust,
                at_time=datetime.now(timezone.utc) + timedelta(days=8))
        _, other = generate_keys(self.root / "other", purpose="production")
        with self.assertRaises(PolicyError):
            verify_mixed_owner_release(self.pack, other)
        with self.assertRaises(PolicyError):
            self.publish()


if __name__ == "__main__":
    unittest.main()
