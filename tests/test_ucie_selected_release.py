"""Synthetic-only tests for dynamic owner-selected release, no real key use."""
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
from ucie_public.policy import PolicyError
from ucie_public.rulepack import (
    generate_keys, canonical_json, _private_key, digest,
)
from ucie_public.multi_owner_release import (
    verify_two_rule_owner_release,
)
from ucie_public.selected_release import (
    CONFIRM, ELIGIBLE, RULE_ORDER, EXPECTED_SECOND_CI, EXPECTED_THIRD_CI,
    THIRD_RUN, THIRD_SHA, THIRD_BRANCH, THIRD_STEP, THIRD_BASELINE_STEP,
    _third_ci, selected_payload, publish_selected_owner_release,
    verify_selected_owner_release, scan_selected_owner_receipt,
)
from ucie_public.owner_release import JOBS


def three_receipt():
    sample = scanner_receipt()
    sample["findings"].append({
        "pattern_code": "PS_FUZZY_GET_COMMAND_DUPLICATES",
        "line": 3, "column": 1,
        "confidence": "STATIC_HEURISTIC_REVIEW_REQUIRED",
        "safe_fix_guidance": "Inspect fuzzy matches for duplicate Name/CommandType/Source identities before using results",
        "public_evidence": "https://github.com/PowerShell/PowerShell/pull/28042",
        "runtime_bug_reproduced": False,
    })
    sample["finding_count"] = len(sample["findings"])
    return sample


def fake_third():
    run = {
        "id": THIRD_RUN, "head_sha": THIRD_SHA,
        "repository": {"full_name": "tmdrkdtn1-project/UCIE"},
        "event": "pull_request", "head_branch": THIRD_BRANCH,
        "status": "completed", "conclusion": "success",
    }
    jobs = []
    for name in sorted(JOBS):
        steps = []
        if name.endswith("Python 3.15"):
            steps.append({"name": THIRD_BASELINE_STEP, "status": "completed",
                          "conclusion": "success"})
        if name == "Offline test / ubuntu-latest / Python 3.15":
            steps.append({"name": THIRD_STEP, "status": "completed",
                          "conclusion": "success"})
        jobs.append({"run_id": THIRD_RUN, "name": name,
                     "status": "completed", "conclusion": "success",
                     "steps": steps})
    return run, {"total_count": 4, "jobs": jobs}



class SelectedOwnerReleaseTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "build").mkdir()
        self.private, self.trust = generate_keys(
            self.root / "synthetic", purpose="production")
        self.pack = self.root / "build" / "selected.zip"
        self.main, self.jobs = fake_api()

    def publish(self, ids=None, **changes):
        ids = list(RULE_ORDER) if ids is None else ids
        params = {
            "run_id": RUN, "serial": 8, "rule_ids": ids,
            "confirmation": CONFIRM,
            "risk_acceptances": {
                code: ELIGIBLE[code][2] for code in ids if code in ELIGIBLE
            },
        }
        params.update(changes)
        with (
            patch("ucie_public.selected_release._local_clean_sha",
                  return_value=SHA),
            patch("ucie_public.owner_release._public_json",
                  side_effect=[self.main, self.jobs]),
            patch("ucie_public.selected_release._postfix_ci",
                  return_value=EXPECTED_SECOND_CI) as second,
            patch("ucie_public.selected_release._third_ci",
                  return_value=EXPECTED_THIRD_CI),
        ):
            result = publish_selected_owner_release(
                self.root, self.private, self.pack, **params)
        return result, second.call_count

    def test_three_rules_explicitly_selected_and_scanned(self):
        _, calls = self.publish()
        self.assertEqual(calls, 1)
        verified = verify_selected_owner_release(self.pack, self.trust,
                                                 min_serial=8)
        self.assertEqual(verified["rule_ids"], list(RULE_ORDER))
        self.assertEqual(verified["owner_signature"], "VALID")
        self.assertEqual(verified["rule_count"], 3)
        self.assertFalse(verified["independent_human_qa_approved"])
        self.assertFalse(verified["auto_apply"])
        result = scan_selected_owner_receipt(
            self.pack, self.trust, three_receipt(), min_serial=8)
        self.assertEqual(result["finding_count"], 3)
        self.assertEqual([i["rule_id"] for i in result["findings"]],
                         list(RULE_ORDER))
        self.assertFalse(result["auto_fix_applied"])
        self.assertFalse(result["source_executed"])
        self.assertEqual(result["persistent_writes"], 0)
        # Existing signed Serial-2 receiver must never accept a V2 envelope.
        with self.assertRaises(PolicyError):
            verify_two_rule_owner_release(self.pack, self.trust)

    def test_first_only_does_not_claim_second_rule_verified(self):
        _, calls = self.publish(ids=[RULE_ORDER[0]])
        self.assertEqual(calls, 0)
        result = verify_selected_owner_release(self.pack, self.trust)
        self.assertEqual(result["rule_ids"], [RULE_ORDER[0]])
        scan = scan_selected_owner_receipt(
            self.pack, self.trust, scanner_receipt())
        self.assertEqual(scan["finding_count"], 1)
        self.assertEqual(scan["findings"][0]["rule_id"], RULE_ORDER[0])

    def test_unapproved_candidate_or_duplicate_or_misordered_selection(self):
        for ids in (
            [], list(reversed(RULE_ORDER)), [RULE_ORDER[0]] * 2,
            ["PS_FUZZY_GET_COMMAND_DUPLICATES"],
            [RULE_ORDER[0], "PY_SCANDIR_SHARED_ITERATOR_RACE"],
        ):
            with self.subTest(ids=ids), self.assertRaises(PolicyError):
                selected_payload(ids)
        self.assertFalse(self.pack.exists())

    def test_owner_consent_required_for_every_rule(self):
        for changed in (
            {"confirmation": "AUTOMATIC"},
            {"risk_acceptances": {RULE_ORDER[0]: ELIGIBLE[RULE_ORDER[0]][2]}},
            {"risk_acceptances": {**{
                code: ELIGIBLE[code][2] for code in RULE_ORDER},
                RULE_ORDER[1]: "I_DID_NOT_ACCEPT"}},
            {"risk_acceptances": {**{
                code: ELIGIBLE[code][2] for code in RULE_ORDER},
                RULE_ORDER[2]: "I_DID_NOT_ACCEPT"}},
            {"serial": True}, {"serial": 2},
        ):
            with self.subTest(changed=changed), self.assertRaises(PolicyError):
                self.publish(**changed)
            self.assertFalse(self.pack.exists())

    def test_falsified_second_ci_and_main_sha_rejected(self):
        wrong_second = dict(EXPECTED_SECOND_CI, head_sha="f" * 40)
        with (
            patch("ucie_public.selected_release._local_clean_sha",
                  return_value=SHA),
            patch("ucie_public.owner_release._public_json",
                  side_effect=[self.main, self.jobs]),
            patch("ucie_public.selected_release._postfix_ci",
                  return_value=wrong_second),
            self.assertRaises(PolicyError),
        ):
            publish_selected_owner_release(
                self.root, self.private, self.pack, run_id=RUN, serial=8,
                rule_ids=list(RULE_ORDER), confirmation=CONFIRM,
                risk_acceptances={
                    rid: ELIGIBLE[rid][2] for rid in RULE_ORDER})
        self.assertFalse(self.pack.exists())
        with (
            patch("ucie_public.selected_release._local_clean_sha",
                  return_value="f" * 40),
            patch("ucie_public.owner_release._public_json",
                  side_effect=[self.main, self.jobs]),
            self.assertRaises(PolicyError),
        ):
            publish_selected_owner_release(
                self.root, self.private, self.pack, run_id=RUN, serial=8,
                rule_ids=[RULE_ORDER[0]], confirmation=CONFIRM,
                risk_acceptances={RULE_ORDER[0]: ELIGIBLE[RULE_ORDER[0]][2]})
        self.assertFalse(self.pack.exists())

    def test_live_third_ci_pinning_fails_for_bad_identity_or_missing_proof(self):
        good, jobs = fake_third()
        with patch("ucie_public.selected_release._public_json",
                   side_effect=[good, jobs]):
            self.assertEqual(_third_ci(), EXPECTED_THIRD_CI)
        for kind in ("wrong_sha", "wrong_branch", "failed", "missing_fix",
                     "missing_windows_observation"):
            run = deepcopy(good)
            matrix = deepcopy(jobs)
            if kind == "wrong_sha":
                run["head_sha"] = "f" * 40
            elif kind == "wrong_branch":
                run["head_branch"] = "unapproved-branch"
            elif kind == "failed":
                run["conclusion"] = "failure"
            elif kind == "missing_fix":
                name = "Offline test / ubuntu-latest / Python 3.15"
                next(j for j in matrix["jobs"] if j["name"] == name)["steps"] = [
                    {"name": THIRD_BASELINE_STEP, "status": "completed",
                     "conclusion": "success"}]
            else:
                name = "Offline test / windows-latest / Python 3.15"
                next(j for j in matrix["jobs"] if j["name"] == name)["steps"] = []
            with self.subTest(kind=kind), patch(
                "ucie_public.selected_release._public_json",
                side_effect=[run, matrix],
            ), self.assertRaises(PolicyError):
                _third_ci()

    def test_third_rule_requires_independent_owner_risk(self):
        first_two = list(RULE_ORDER[:2])
        _, _ = self.publish(ids=first_two)
        result = verify_selected_owner_release(self.pack, self.trust)
        self.assertEqual(result["rule_ids"], first_two)
        self.assertNotIn(RULE_ORDER[2], result["rule_ids"])
        scan = scan_selected_owner_receipt(
            self.pack, self.trust, three_receipt())
        self.assertEqual(scan["finding_count"], 2)

    def test_third_rule_ci_not_claimed_when_unselected(self):
        self.publish(ids=[RULE_ORDER[0]])
        with zipfile.ZipFile(self.pack) as z:
            evidence = json.loads(z.read("evidence/automated_ci.json"))
        self.assertIsNone(evidence["third_ci"])

    def test_rollback_expiry_untrusted_key_no_overwrite(self):
        self.publish()
        with self.assertRaises(PolicyError):
            verify_selected_owner_release(self.pack, self.trust,
                                          min_serial=9)
        with self.assertRaises(PolicyError):
            verify_selected_owner_release(
                self.pack, self.trust,
                at_time=datetime.now(timezone.utc) + timedelta(days=8))
        _, other = generate_keys(self.root / "other", purpose="production")
        with self.assertRaises(PolicyError):
            verify_selected_owner_release(self.pack, other)
        with self.assertRaises(PolicyError):
            self.publish()

    def test_re_signed_tampering_never_approves_extra_rule(self):
        self.publish()
        with zipfile.ZipFile(self.pack) as z:
            base = {name: z.read(name) for name in z.namelist()}
        for mutation in ("unsigned_rule", "decisions", "missing_ci",
                         "auto_apply", "wrong_source"):
            blobs = dict(base)
            man = json.loads(blobs["manifest.json"])
            if mutation == "unsigned_rule":
                rules = json.loads(blobs["rules/prevention.json"])
                rules.append({**rules[0], "rule_id": "PS_FUZZY_GET_COMMAND_DUPLICATES"})
                blobs["rules/prevention.json"] = canonical_json(rules)
                man["rule_ids"] = [*man["rule_ids"], "PS_FUZZY_GET_COMMAND_DUPLICATES"]
                man["rule_count"] = 3
                man["rules_sha256"] = digest(blobs["rules/prevention.json"])
            elif mutation == "decisions":
                d = json.loads(blobs["evidence/rule_decisions.json"])
                d[1]["owner_risk_accepted"] = False
                blobs["evidence/rule_decisions.json"] = canonical_json(d)
                man["decisions_sha256"] = digest(blobs["evidence/rule_decisions.json"])
            elif mutation == "missing_ci":
                e = json.loads(blobs["evidence/automated_ci.json"])
                e["second_ci"] = None
                blobs["evidence/automated_ci.json"] = canonical_json(e)
                man["evidence_sha256"] = digest(blobs["evidence/automated_ci.json"])
            elif mutation == "wrong_source":
                rules = json.loads(blobs["rules/prevention.json"])
                rules[1]["upstream_merge_sha"] = "f" * 40
                blobs["rules/prevention.json"] = canonical_json(rules)
                man["rules_sha256"] = digest(blobs["rules/prevention.json"])
            else:
                man["auto_apply"] = True
            blobs["manifest.json"] = canonical_json(man)
            blobs["signatures/owner.sig"] = _private_key(self.private).sign(
                blobs["manifest.json"])
            path = self.root / "build" / f"forged-{mutation}.zip"
            with zipfile.ZipFile(path, "w") as z:
                for name, data in blobs.items():
                    z.writestr(name, data)
            with self.subTest(mutation=mutation), self.assertRaises(PolicyError):
                verify_selected_owner_release(path, self.trust)

    def test_static_receipt_forgery_blocked(self):
        self.publish()
        sample = scanner_receipt()
        sample["findings"][1]["public_evidence"] = (
            "https://github.com/PowerShell/PowerShell/pull/28042")
        with self.assertRaises(PolicyError):
            scan_selected_owner_receipt(self.pack, self.trust, sample)


if __name__ == "__main__":
    unittest.main()
