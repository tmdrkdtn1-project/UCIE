"""Scope-only regression tests. No pip, venv, Git, vendor execution or live data."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SOURCE = Path(__file__).with_name("runtime_ucie_c4_clean_windows_first_party_lifecycle_v01.py")
spec = importlib.util.spec_from_file_location("ucie_c4_ci_contract", SOURCE)
if spec is None or spec.loader is None:
    raise RuntimeError("UCIE C4 CI contract unavailable")
c4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c4)


class CleanWindowsC4ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_C4_CI_CONTRACT_ONLY_")
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = base / "UCIE"
        self.repo.mkdir()
        (self.repo / ".git").mkdir()
        self.runner = base / "runner_scratch"
        self.runner.mkdir()
        self.env = {
            "CI": "true", "GITHUB_ACTIONS": "true",
            "RUNNER_OS": "Windows",
            "GITHUB_REPOSITORY": "tmdrkdtn1-project/UCIE",
            "GITHUB_EVENT_NAME": "pull_request",
            "UCIE_C4_FIRST_PARTY_CI_ONLY": "1",
            "RUNNER_TEMP": str(self.runner),
        }

    def check(self, **overrides):
        kwargs = {"platform": "win32", "python": (3, 15)}
        kwargs.update(overrides)
        return c4.validate_ci_scope(self.repo, self.env, **kwargs)

    def test_exact_isolated_ci_scope_only(self):
        self.assertEqual(self.check(), self.runner)

    def test_refuse_unmarked_ci_user_host(self):
        self.env.pop("UCIE_C4_FIRST_PARTY_CI_ONLY")
        with self.assertRaises(c4.CleanRecipientError):
            self.check()

    def test_refuse_foreign_project(self):
        self.env["GITHUB_REPOSITORY"] = "example/OTHER"
        with self.assertRaises(c4.CleanRecipientError):
            self.check()

    def test_refuse_unreviewed_windows_or_python(self):
        for attrs in ({"platform": "linux"}, {"python": (3, 13)}, {"python": (3, 16)}):
            with self.assertRaises(c4.CleanRecipientError):
                self.check(**attrs)

    def test_refuse_owner_forged_checkout_without_git(self):
        (self.repo / ".git").rmdir()
        with self.assertRaises(c4.CleanRecipientError):
            self.check()

    def test_refuse_nested_scratch_in_checkout(self):
        nested = self.repo / "scratch"
        nested.mkdir()
        self.env["RUNNER_TEMP"] = str(nested)
        with self.assertRaises(c4.CleanRecipientError):
            self.check()

    def test_offline_first_party_command_flags_and_scope(self):
        slot = self.runner / "candidate_A" / "wheel"
        slot.mkdir(parents=True)
        wheel = slot / "ucie_public_only_demo-0.1.0-py3-none-any.whl"
        wheel.write_bytes(b"UCIE synthetic path-only test; never pip installed")
        child = self.runner / "recipient" / "Scripts" / "python.exe"
        command = c4._offline_install_command(child, wheel, self.runner)
        for expected in ("--no-index", "--no-deps", "--isolated",
                         "--no-cache-dir", "--no-input", "--no-compile"):
            self.assertIn(expected, command)
        for denied in ("--index-url", "--find-links", "--trusted-host"):
            self.assertNotIn(denied, command)

    def test_refuse_foreign_or_unsupported_wheel_path(self):
        foreign = self.repo / "ucie_public_only_demo-0.1.0-py3-none-any.whl"
        foreign.write_bytes(b"UCIE forged synthetic")
        child = self.runner / "recipient" / "Scripts" / "python.exe"
        with self.assertRaises(c4.CleanRecipientError):
            c4._offline_install_command(child, foreign, self.runner)
        extra = self.runner / "cryptography-50.0.2-py3-none-any.whl"
        extra.write_bytes(b"UCIE fake third-party")
        with self.assertRaises(c4.CleanRecipientError):
            c4._offline_install_command(child, extra, self.runner)

    def test_actual_version_parser_checks_venv_and_feature(self):
        state = {
            "version": "0.1.1", "b_only_health_present": True,
            "isolated": True, "bits": 64, "prefix": str(self.runner),
        }
        observed = c4._verify_state(json.dumps(state), "0.1.1", self.runner)
        self.assertTrue(observed["B_only_module_present"])
        state["b_only_health_present"] = False
        with self.assertRaises(c4.CleanRecipientError):
            c4._verify_state(json.dumps(state), "0.1.1", self.runner)
        state["b_only_health_present"] = True
        state["prefix"] = str(self.repo)
        with self.assertRaises(c4.CleanRecipientError):
            c4._verify_state(json.dumps(state), "0.1.1", self.runner)

    def test_public_first_party_no_vendor_python_environment(self):
        safe = c4._safe_environment({
            "PATH": "test", "PYTHONPATH": "DISALLOWED",
            "PIP_INDEX_URL": "https://not-needed.invalid",
            "GITHUB_TOKEN": "DISALLOWED",
        })
        self.assertEqual(safe["PIP_NO_INDEX"], "1")
        for denied in ("PYTHONPATH", "PIP_INDEX_URL", "GITHUB_TOKEN"):
            self.assertNotIn(denied, safe)


if __name__ == "__main__":
    unittest.main()
