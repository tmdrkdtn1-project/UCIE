"""W38: prevent generic UCIE bridge reachability from silently becoming C40 proof.

This suite reads first-party source files only. It never invokes a Windows
host, C40, connectors, tunnel, service, tasks, private data, or SQLite.
No test in this file provides C40 endpoint, session or route attestation.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DOC = ROOT / "docs" / "UCIE_20261118_W21_ONE_LOCAL_MAINTENANCE_OWNER_GATES.md"
SCOPED = (
    "ucie_owner_w20_activation_integrity_v01.py",
    "ucie_owner_w20_local_pilot_v01.ps1",
    "ucie_owner_w21_single_local_maintenance_v01.ps1",
    "ucie_owner_w29_oldroot_rehearsal_restore_v01.ps1",
    "ucie_owner_w30_secondary_oldroot_restore_v01.ps1",
    "ucie_owner_w31_local_listener_pid_readonly_v01.ps1",
    "ucie_owner_w36_task129_parent_event_readonly_v01.ps1",
)
PROVEN_TRUE = re.compile(
    r"""(?ix)
    ['"]?c40_mcp_round_trip_verified['"]?\s*[:=]\s*
    (?: \$true \b | True \b | true \b | 1 \b )
    """
)
PROVEN_FALSE = re.compile(
    r"""(?ix)
    ['"]?c40_mcp_round_trip_verified['"]?\s*[:=]\s*
    (?: \$false \b | False \b | false \b )
    """
)


class TestW38NoUnboundC40EvidencePromotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.files = {name: (SCRIPTS / name).read_text(encoding="utf-8")
                     for name in SCOPED}

    def test_existing_operational_gates_never_claim_c40_roundtrip(self) -> None:
        for name, source in self.files.items():
            with self.subTest(file=name):
                self.assertRegex(source, PROVEN_FALSE)
                self.assertIsNone(
                    PROVEN_TRUE.search(source),
                    f"{name}: an existing task/HTTP/bridge receipt is not "
                    "a C40-authenticated MCP route proof",
                )

    def test_bridge_status_not_a_shortcut_to_c40_proof(self) -> None:
        for name, source in self.files.items():
            with self.subTest(file=name):
                self.assertNotIn("UCIE_LOCAL_ADMIN_BRIDGE_READY", source)
        w21 = self.files["ucie_owner_w21_single_local_maintenance_v01.ps1"]
        self.assertIn("UCIE_W21_LOCAL_ONLY_HEALTHY__WRITERS_AND_C40_HOLD", w21)
        self.assertIn("full_operating_cutover_authorized=$false", w21)

    def test_task_event_is_not_silent_process_launch_attestation(self) -> None:
        w36 = self.files["ucie_owner_w36_task129_parent_event_readonly_v01.ps1"]
        self.assertIn("UCIE_W37_TASK129_NO_MATCH_HOLD", w36)
        self.assertIn("listener_pid_launched_by_task_scheduler_verified=$false", w36)
        self.assertIn("full_cutover_authorized=$false", w36)
        self.assertNotIn("listener_pid_launched_by_task_scheduler_verified=$true", w36)

    def test_existing_gate_documentation_requires_independent_c40_proof(self):
        text = DOC.read_text(encoding="utf-8")
        self.assertIn("issues/334", text)
        self.assertIn("UCIE_LOCAL_ADMIN_BRIDGE_READY", text)
        self.assertIn("C40 MCP", text)
        self.assertIn("W38", text)
        self.assertIn("full cutover", text.lower())

    def test_regression_examples_detect_claimed_pass_even_with_bridge_ready(self):
        snippet = (
            'status="UCIE_LOCAL_ADMIN_BRIDGE_READY"\n'
            'c40_mcp_round_trip_verified=$true\n'
        )
        self.assertRegex(snippet, PROVEN_TRUE)
        self.assertIsNone(PROVEN_FALSE.search(snippet))
        safe = 'c40_mcp_round_trip_verified=$false'
        self.assertRegex(safe, PROVEN_FALSE)
        self.assertIsNone(PROVEN_TRUE.search(safe))


if __name__ == "__main__":
    unittest.main()
