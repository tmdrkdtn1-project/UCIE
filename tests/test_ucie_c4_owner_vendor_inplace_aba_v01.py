"""C4 owner-only vendor-inclusive same-venv A/B/A: synthetic-only safety QA.

No pip, vendor import, owner Python subprocess or product distribution is run.
Positive full lifecycle requires a separate interactive owner consent.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner import customer_c4_owner_vendor_inplace_aba_v01 as c4
from ucie_miner import customer_full_product_offline_rehearsal_v01 as full


class UCIEC4OwnerVendorInplaceABATests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_C4_INERT_CONTRACT_")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "UCIE"
        self.root.mkdir()
        self.venv = self.base / "recipient"
        self.venv.mkdir()
        (self.root / "downloaded").mkdir()

    def test_wrong_owner_consent_rejected_before_all_calls(self):
        with patch.object(c4, "_owner_gate", side_effect=AssertionError("must not run")):
            with self.assertRaises(c4.C4OwnerTrialError):
                c4.run_owner_once(self.root, typed_consent="")
            with self.assertRaises(c4.C4OwnerTrialError):
                c4.run_owner_once(self.root, typed_consent=c4.CONSENT + " ")

    def test_synthetic_root_cannot_run_real_owner_vendor_code(self):
        with self.assertRaises(c4.C4OwnerTrialError):
            c4._owner_gate(self.root)

    def test_preview_is_offline_and_exactly_non_approving(self):
        with patch.object(c4.dep, "_valid_checkout", return_value=self.root), \
             patch.object(c4, "_verified_capture", return_value={
                 "cffi": "a"*64, "cryptography": "b"*64, "pycparser": "c"*64}), \
             patch.object(c4.pin, "probe_git_objects", return_value={
                 "pinned_both_git_trees_verified": True}):
            before = list(self.root.rglob("*"))
            report = c4.inspect_readonly(self.root)
            self.assertEqual(before, list(self.root.rglob("*")))
        self.assertEqual(report["readiness"],
                         "READY_FOR_EXPLICIT_OWNER_CONSENT_LOCAL_TEST_ONLY")
        self.assertTrue(all(report["gates"].values()))
        self.assertFalse(report["third_party_code_executed"])
        self.assertFalse(report["customer_distribution_authorized"])
        self.assertEqual(report["external_network_calls"], 0)

    def test_receipt_presence_denies_replay(self):
        file = self.root / c4.RECEIPT
        file.write_text('{"untrusted":true}')
        with patch.object(c4.dep, "_valid_checkout", return_value=self.root), \
             patch.object(c4, "_verified_capture", return_value={
                 "cffi": "a"*64, "cryptography": "b"*64, "pycparser": "c"*64}), \
             patch.object(c4.pin, "probe_git_objects", return_value={
                 "pinned_both_git_trees_verified": True}):
            report = c4.inspect_readonly(self.root)
        self.assertFalse(report["gates"]["new_one_time_receipt_destination"])
        self.assertEqual(report["readiness"], "PREREQUISITES_MISSING_NO_GO")

    def test_missing_offline_vendor_proof_is_no_go(self):
        with patch.object(c4.dep, "_valid_checkout", return_value=self.root), \
             patch.object(c4, "_verified_capture",
                          side_effect=c4.C4OwnerTrialError("missing")), \
             patch.object(c4.pin, "probe_git_objects", return_value={
                 "pinned_both_git_trees_verified": True}):
            report = c4.inspect_readonly(self.root)
        self.assertFalse(report["gates"][
            "three_existing_owner_captured_vendor_wheels_and_prior_C1"])
        self.assertFalse(report["customer_distribution_authorized"])

    def test_inplace_version_checks_real_prefix_and_B_only_feature(self):
        candidate = {"version": "0.1.0", "b_only_health_present": False,
                     "isolated": True, "bits": 64, "prefix": str(self.venv)}
        a = c4._checked_venv_version(json.dumps(candidate), "0.1.0", self.venv)
        self.assertTrue(a["same_installed_venv"])
        candidate["version"], candidate["b_only_health_present"] = "0.1.1", True
        b = c4._checked_venv_version(json.dumps(candidate), "0.1.1", self.venv)
        self.assertTrue(b["B_only_feature_present"])
        candidate["prefix"] = str(self.base / "some_other_venv")
        with self.assertRaises(c4.C4OwnerTrialError):
            c4._checked_venv_version(json.dumps(candidate), "0.1.1", self.venv)
        candidate["prefix"] = str(self.venv)
        candidate["b_only_health_present"] = False
        with self.assertRaises(c4.C4OwnerTrialError):
            c4._checked_venv_version(json.dumps(candidate), "0.1.1", self.venv)
        with self.assertRaises(c4.C4OwnerTrialError):
            c4._checked_venv_version("invalid-json", "0.1.1", self.venv)

    def test_reject_non_hash_bound_pip_even_in_synthetic_trial(self):
        wheel = self.base / "ucie_public_only_demo-0.1.0-py3-none-any.whl"
        wheel.write_bytes(b"UCIE inert synthetic wheel path only")
        slot = {"wheel": wheel, "digest": sha256(wheel.read_bytes()).hexdigest(),
                "version": "0.1.0", "source": self.root}
        with patch.object(full, "_install_cmd", return_value=["pip", "--no-index"]), \
             patch.object(full, "_run", side_effect=AssertionError("must not run")):
            with self.assertRaises(c4.C4OwnerTrialError):
                c4._phase("A", self.base/"python.exe", self.venv, slot,
                          self.root, self.base,
                          {"cryptography": "a"*64, "cffi": "b"*64,
                           "pycparser": "c"*64}, {})

    def test_actual_phase_contract_uses_one_venv_and_offline_hash_command(self):
        wheel = self.base / "ucie_public_only_demo-0.1.0-py3-none-any.whl"
        wheel.write_bytes(b"UCIE inert synthetic wheel path only")
        slot = {"wheel": wheel, "digest": sha256(wheel.read_bytes()).hexdigest(),
                "version": "0.1.0", "source": self.root}
        called = []
        def fake_run(args, cwd, env, what):
            called.append((list(args), str(what)))
            if "version" in str(what):
                return json.dumps({
                    "version": "0.1.0", "b_only_health_present": False,
                    "isolated": True, "bits": 64, "prefix": str(self.venv)})
            return "{}"
        smoke = {
            "local_V04": {"installed_local_ui_loopback_routes_verified": 5,
                          "negative_post_denial_checked": True},
            "four_pillars": {
                "first_party_four_pillars_synthetic_worked": True,
                "workflow_receipt_sha256": "c"*64},
            "B_only_workflow_sha256": None,
            "customer_distribution_authorized": False,
        }
        native = {
            "cryptography_aesgcm_roundtrip": True,
            "cffi_declaration_parsed": True,
            "pycparser_c_declaration_parsed": True,
        }
        with patch.object(full, "_run", side_effect=fake_run), \
             patch.object(full, "_check_native", return_value=native), \
             patch.object(c4.ab, "_smoke", return_value=smoke):
            outcome = c4._phase(
                "A", self.base / "python.exe", self.venv, slot,
                self.root, self.base,
                {"cryptography": "a"*64, "cffi": "b"*64,
                 "pycparser": "c"*64}, {"PIP_NO_INDEX": "1"})
        self.assertEqual(outcome["installed_version"], "0.1.0")
        self.assertEqual(outcome["local_V04_real_GET_routes"], 5)
        self.assertFalse(outcome["customer_distribution_authorized"])
        pip_command = called[0][0]
        for requirement in ("--require-hashes", "--no-index", "--find-links",
                            "--no-input", "-r"):
            self.assertIn(requirement, pip_command)
        self.assertEqual(len(called), 4)

    def test_first_party_current_worktree_cannot_be_used_in_gated_build(self):
        from ucie_miner.customer_pinned_git_source_v01 import PINNED
        self.assertEqual(set(PINNED), {"A", "B"})
        self.assertEqual(set(c4.STAGES),
                         {"A_initial", "B_inplace_update", "A_inplace_rollback"})
        self.assertNotEqual(c4.STATUS, "CUSTOMER_GO")
        self.assertEqual(set(c4.pin.CANONICAL_QA_SHA256), {"A", "B", "bundle"})


if __name__ == "__main__":
    unittest.main()
