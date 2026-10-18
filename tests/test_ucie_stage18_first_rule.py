"""Stage18 bounded first-rule offline dossier and inert local behavior tests."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import sys
import unittest
from unittest.mock import patch

from test_ucie_automated_candidate_qa import handoff
from test_ucie_stage17_review_docket import evidence
from ucie_miner.__main__ import main as miner_main
from ucie_miner.stage17_review_docket import build_review_docket
from ucie_miner.stage18_first_rule import (
    MERGE_SHA, PR_URL, RULE_ID, SCHEMA, STATUS_CONFIRMED, STATUS_FAILED,
    STATUS_MISSING, STATUS_PENDING, _observe_xoption, build_first_rule_report,
    inspect_first_rule, reproduce_local_xoption,
)


def docket():
    return build_review_docket(handoff(), evidence())


def local_observation():
    return {
        "status": STATUS_CONFIRMED,
        "runtime_version": "3.15.0",
        "platform": "win32",
        "baseline_enabled": True,
        "wrong_option_enabled": True,
        "correct_option_enabled": False,
    }


class Stage18DossierTests(unittest.TestCase):
    def test_exact_first_rule_links_stage17_identity_without_go(self):
        d = docket()
        expected = next(x for x in d["items"] if x["rule_id"] == RULE_ID)
        report = build_first_rule_report(d, local_observation())
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["status"], STATUS_CONFIRMED)
        self.assertEqual(report["candidate_id_sha256"],
                         expected["candidate_id_sha256"])
        self.assertEqual(report["evidence_sha256"], expected["evidence_sha256"])
        self.assertEqual(report["pinned_official_metadata"]["upstream_pr_url"],
                         PR_URL)
        self.assertEqual(report["pinned_official_metadata"]["upstream_merge_sha"],
                         MERGE_SHA)
        self.assertTrue(report["local_probe_is_operator_host_observation"])
        self.assertFalse(report["local_probe_independent_of_owner"])
        self.assertFalse(report["candidate_specific_ci_attested"])
        self.assertFalse(report["source_facts_rechecked_by_this_offline_command"])
        self.assertEqual(report["independent_qa"], "NOT_PERFORMED")
        self.assertEqual(report["independent_security_qa"], "NOT_PERFORMED")
        self.assertEqual(report["approved_rules_added"], 0)
        self.assertFalse(report["rulepack_signed"])
        self.assertFalse(report["production_approved"])
        self.assertFalse(report["digest_is_signature"])
        self.assertEqual(report["new_public_gets"], 0)
        self.assertEqual(report["persistent_writes"], 0)

    def test_no_probe_no_new_runtime_claim(self):
        result = build_first_rule_report(docket())
        self.assertEqual(result["status"], STATUS_PENDING)
        self.assertFalse(result["local_probe_is_operator_host_observation"])
        self.assertEqual(result["local_probe"]["status"], STATUS_PENDING)

    def test_missing_ambiguous_or_incomplete_candidate_no_go(self):
        d = docket()
        d["items"] = [x for x in d["items"] if x["rule_id"] != RULE_ID]
        d["candidate_count"] = len(d["items"])
        self.assertEqual(build_first_rule_report(d)["status"], STATUS_MISSING)
        d = docket()
        first = next(x for x in d["items"] if x["rule_id"] == RULE_ID)
        d["items"].append(deepcopy(first))
        d["candidate_count"] += 1
        with self.assertRaises(ValueError):
            build_first_rule_report(d)
        d = docket()
        d["status"] = "EVIDENCE_INCOMPLETE_NO_GO"
        self.assertEqual(build_first_rule_report(d)["status"], STATUS_MISSING)

    def test_forged_go_and_candidate_fields_rejected(self):
        for field, value in (
                ("approved_rules_added", 1),
                ("production_approved", True),
                ("independent_qa_pass_count", 1),
                ("stage16_candidate_snapshot_at_ci_verified", True)):
            d = docket()
            d[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                build_first_rule_report(d)
        d = docket()
        next(x for x in d["items"] if x["rule_id"] == RULE_ID)["candidate_id_sha256"] = (
            "not-a-hash")
        with self.assertRaises(ValueError):
            build_first_rule_report(d)

    def test_candidate_url_or_review_flag_change_denied(self):
        for change in (
                {"pinned_public_pr": "https://github.com/unknown/other"},
                {"source": "unapproved/private"},
                {"triage": "UNSUPPORTED_SAFE_RECIPE_NO_GO"},
                {"independent_qa": "PASS"},
                {"human_approval": True},
                {"deploy_allowed": True}):
            d = docket()
            row = next(x for x in d["items"] if x["rule_id"] == RULE_ID)
            row.update(change)
            self.assertEqual(build_first_rule_report(d)["status"], STATUS_MISSING)

    def test_forged_local_behavior_rejected(self):
        observation = local_observation()
        observation["wrong_option_enabled"] = False
        with self.assertRaises(ValueError):
            build_first_rule_report(docket(), observation)
        observation = local_observation()
        observation["runtime_version"] = "3.14.0"
        with self.assertRaises(ValueError):
            build_first_rule_report(docket(), observation)

    def test_negative_local_repro_does_not_claim_success(self):
        observation = local_observation()
        observation["status"] = STATUS_FAILED
        observation["wrong_option_enabled"] = False
        result = build_first_rule_report(docket(), observation)
        self.assertEqual(result["status"], STATUS_FAILED)
        self.assertFalse(result["production_approved"])

    def test_no_local_execution_without_explicit_probe_flag(self):
        with patch("ucie_miner.stage18_first_rule.inspect_stage17_review",
                   return_value=docket()), patch(
                       "ucie_miner.stage18_first_rule.reproduce_local_xoption",
                       side_effect=AssertionError("unexpected execution")):
            report = inspect_first_rule("D:/UCIE", local_probe=False)
        self.assertEqual(report["status"], STATUS_PENDING)

    def test_no_execution_when_candidate_not_ready(self):
        d = docket()
        d["status"] = "EVIDENCE_INCOMPLETE_NO_GO"
        with patch("ucie_miner.stage18_first_rule.inspect_stage17_review",
                   return_value=d), patch(
                       "ucie_miner.stage18_first_rule.reproduce_local_xoption",
                       side_effect=AssertionError("must not execute")):
            report = inspect_first_rule("D:/UCIE", local_probe=True)
        self.assertEqual(report["status"], STATUS_MISSING)

    def test_cli_requires_local_probe_explicitly(self):
        with patch("ucie_miner.__main__.inspect_first_rule",
                   return_value={"status": STATUS_PENDING}) as f:
            out = io.StringIO()
            with redirect_stdout(out):
                code = miner_main(["inspect-stage18-first-rule"])
            self.assertEqual(code, 0)
            f.assert_called_once()
            self.assertFalse(f.call_args.kwargs["local_probe"])
            self.assertEqual(json.loads(out.getvalue())["status"], STATUS_PENDING)


class Stage18ProbeTests(unittest.TestCase):
    def test_probe_rejects_unrecognized_switch_before_subprocess(self):
        with patch("ucie_miner.stage18_first_rule.subprocess.run",
                   side_effect=AssertionError("unexpected subprocess")):
            with self.assertRaises(ValueError):
                _observe_xoption("candidate-provided-shell-or-switch")

    def test_synthetic_subprocess_argument_is_fixed_and_shell_free(self):
        class Result:
            returncode = 0
            stdout = "False\\n"
            stderr = ""
        # Use a representative fully synthetic subprocess result.
        with patch("ucie_miner.stage18_first_rule.subprocess.run",
                   return_value=Result()) as fake:
            self.assertFalse(_observe_xoption("disable-remote-debug"))
        argv = fake.call_args.args[0]
        self.assertEqual(argv[1:3], ["-I", "-B"])
        self.assertEqual(argv[3:5], ["-X", "disable-remote-debug"])
        self.assertEqual(argv[-2], "-c")
        self.assertEqual(argv[-1],
                         "import sys; print(sys.is_remote_debug_enabled())")
        self.assertNotIn("shell", fake.call_args.kwargs)
        self.assertEqual(fake.call_args.kwargs["timeout"], 8)

    @unittest.skipUnless(
        sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 15),
        "Only on CPython 3.15 with feature-enabled runtime")
    def test_real_existing_runner_315_behavior_without_upstream_code(self):
        evidence = reproduce_local_xoption()
        self.assertEqual(evidence["status"], STATUS_CONFIRMED)
        self.assertTrue(evidence["baseline_enabled"])
        self.assertTrue(evidence["wrong_option_enabled"])
        self.assertFalse(evidence["correct_option_enabled"])
        self.assertTrue(evidence["runtime_version"].startswith("3.15."))


if __name__ == "__main__":
    unittest.main()
