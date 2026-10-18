"""Owner Serial-4 local handoff: synthetic-only tests; no real key/signing."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from scripts.ucie_owner_four_rule_one_shot import (
    CONFIRM, RULE_ORDER, ELIGIBLE, FOURTH_ID, ROOT,
    owner_input, power_shell_receipt, PS_POSITIVE, PS_NEGATIVE,
    run,
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
