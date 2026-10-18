"""Owner Serial-4 local handoff: synthetic-only tests; no real key/signing."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.ucie_owner_four_rule_one_shot import (
    CONFIRM, RULE_ORDER, ELIGIBLE, FOURTH_ID, ROOT,
    owner_input, power_shell_receipt, PS_POSITIVE, PS_NEGATIVE,
    run, main,
)
from ucie_public.policy import PolicyError
from ucie_miner.static_rule_bridge import _check_receipt


class FourRuleOwnerOneShotTests(unittest.TestCase):
    def test_noninteractive_requires_real_owner(self):
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaises(PolicyError):
                owner_input()

    def test_five_separate_owner_consent_phrases(self):
        phrases = [CONFIRM] + [ELIGIBLE[rule][2] for rule in RULE_ORDER]
        self.assertEqual(len(phrases), 5)
        self.assertEqual(RULE_ORDER[-1], FOURTH_ID)
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("sys.stdout.isatty", return_value=True),
            patch("builtins.input", side_effect=phrases),
        ):
            accepted = owner_input()
        self.assertEqual(
            accepted, {rid: ELIGIBLE[rid][2] for rid in RULE_ORDER})
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("sys.stdout.isatty", return_value=True),
            patch("builtins.input", side_effect=phrases[:-1] + ["YES"]),
            self.assertRaises(PolicyError),
        ):
            owner_input()

    def test_non_owner_platform_cannot_execute(self):
        if os.name != "nt":
            with self.assertRaises(PolicyError):
                run()

    def test_powershell_pipe_encoding_error_never_silent_pass(self):
        root = Path(__file__).resolve().parents[1]
        scanner = root / "scripts" / "ucie_powershell_static_candidates.ps1"
        cases = (
            (b'{"ok":true}', bytes([0xc0, 0xc1]), 0),
            (b'{"ok":true}', b"", 1),
            (bytes([0xc0, 0xc1]), b"", 0),
        )
        for stdout, stderr, rc in cases:
            with self.subTest(stdout=stdout, stderr=stderr, rc=rc):
                with patch(
                    "scripts.ucie_owner_four_rule_one_shot.subprocess.run",
                    return_value=subprocess.CompletedProcess(
                        ["powershell.exe"], rc, stdout, stderr),
                ) as invoked, self.assertRaises(PolicyError):
                    power_shell_receipt(scanner, PS_POSITIVE, root)
                kwargs = invoked.call_args.kwargs
                self.assertIs(kwargs["text"], False)
                self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)

    def test_raw_utf8_json_stdout_without_stderr_is_accepted(self):
        root = Path(__file__).resolve().parents[1]
        scanner = root / "scripts" / "ucie_powershell_static_candidates.ps1"
        with patch(
            "scripts.ucie_owner_four_rule_one_shot.subprocess.run",
            return_value=subprocess.CompletedProcess(
                ["powershell.exe"], 0, b'{"ok":true}', b""),
        ):
            self.assertEqual(power_shell_receipt(
                scanner, PS_POSITIVE, root), {"ok": True})

    def test_verify_existing_cli_never_calls_signing_path(self):
        with (
            patch("scripts.ucie_owner_four_rule_one_shot.verify_existing",
                  return_value={"status": "READ_ONLY_TEST"}) as verified,
            patch("scripts.ucie_owner_four_rule_one_shot.run") as signed,
        ):
            self.assertEqual(main(["--verify-existing"]), 0)
            verified.assert_called_once_with()
            signed.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "native Windows PowerShell 5.1 only")
    def test_first_party_powershell_51_ast_bridge_real_synthetic_samples(self):
        # Only harmless inert synthetic strings, no signed production keys.
        root = Path(__file__).resolve().parents[1]
        scanner = root / "scripts" / "ucie_powershell_static_candidates.ps1"
        good = power_shell_receipt(scanner, PS_POSITIVE, root)
        bad = power_shell_receipt(scanner, PS_NEGATIVE, root)
        self.assertEqual(_check_receipt(good), "powershell")
        self.assertEqual(_check_receipt(bad), "powershell")
        self.assertEqual(good["finding_count"], 3)
        self.assertEqual(bad["finding_count"], 0)
        self.assertFalse(good["parser_executed_supplied_code"])
        self.assertEqual(good["source_files_read"], 0)
        self.assertEqual(good["persistent_writes"], 0)


if __name__ == "__main__":
    unittest.main()
