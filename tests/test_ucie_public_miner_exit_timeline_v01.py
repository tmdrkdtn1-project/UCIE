"""UCIE exact-task exit timeline synthetic regression, no owner data reads."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest import TestCase

from ucie_miner import public_miner_exit_timeline_v01 as t

UTC = timezone.utc
BASE = datetime(2026, 11, 5, 4, 37, 10, tzinfo=UTC)


def ts(offset_seconds):
    return (BASE + timedelta(seconds=offset_seconds)).isoformat()


def make_receipt(offset_seconds):
    return {
        "schema": "UCIE_MINER_CYCLE_V1",
        "status": "COLLECTED_UNVERIFIED",
        "started_utc": ts(offset_seconds),
        "finished_utc": ts(offset_seconds + 9),
        "verification_pass": 0,
        "production_approved": False,
    }


def make_event(offset_seconds, *, exit_after_seconds=9.8, code=0):
    return {
        "event_100_utc": ts(offset_seconds + .150),
        "event_200_utc": ts(offset_seconds + .151),
        "event_201_utc": ts(offset_seconds + exit_after_seconds),
        "event_102_utc": ts(offset_seconds + exit_after_seconds + .001),
        "action_is_exact_python": True,
        "result_code_201": code,
        "event_duplicated": False,
    }


def fixture(*, second_code=2147943691, second_exit_s=600.168):
    return {
        "schema": t.INPUT_SCHEMA,
        "source": "OWNER_EXACT_TASK_XPATH_READONLY",
        "task_writes": False,
        "receipts": [make_receipt(0), make_receipt(3600)],
        "instances": [
            make_event(0),
            make_event(3600, exit_after_seconds=second_exit_s,
                       code=second_code),
        ],
    }


class PublicMinerExitTimelineTests(TestCase):
    def test_known_synthetic_replay_matches_one_zero_one_timeout_like(self):
        report = t.compare_post_receipt_exit(fixture())
        self.assertEqual(report["status"], t.NONZERO)
        self.assertEqual(report["matched_receipt_count"], 2)
        self.assertEqual(report["observed_nonzero_action_events"], 1)
        self.assertEqual(report["receipts"][0]["action_result"], 0)
        self.assertEqual(report["receipts"][1]["action_result_hex"], "0x8007050B")
        self.assertAlmostEqual(
            report["receipts"][1]["post_receipt_exit_lag_seconds"],
            591.168, places=3)
        self.assertAlmostEqual(
            report["receipts"][1]["action_elapsed_seconds"],
            600.017, places=3)
        self.assertFalse(report["exact_windows_task_healthy_attested"])
        self.assertFalse(report["production_termination_root_cause_proven"])
        self.assertFalse(report["termination_at_task_time_limit_confirmed"])
        self.assertFalse(report["task_scheduler_mutated"])
        self.assertFalse(report["event_instance_guid_disclosed"])

    def test_two_good_task_actions_does_not_mean_scheduler_go(self):
        data = fixture(second_code=0, second_exit_s=9.8)
        report = t.compare_post_receipt_exit(data)
        self.assertEqual(report["status"], t.OBSERVED)
        self.assertEqual(report["observed_nonzero_action_events"], 0)
        self.assertFalse(report["exact_windows_task_healthy_attested"])
        self.assertFalse(report["production_termination_root_cause_proven"])

    def test_missing_201_instance_not_forged(self):
        data = fixture()
        data["instances"].pop()
        result = t.compare_post_receipt_exit(data)
        self.assertEqual(result["status"], t.FAIL)
        self.assertEqual(result["matched_receipt_count"], 1)
        self.assertIsNone(result["receipts"][1]["action_result"])

    def test_duplicate_possible_instances_fail_closed(self):
        data = fixture()
        data["instances"].append(deepcopy(data["instances"][-1]))
        report = t.compare_post_receipt_exit(data)
        self.assertEqual(report["status"], t.FAIL)

    def test_duplicate_event_flag_blocks_affected_receipt(self):
        data = fixture()
        data["instances"][-1]["event_duplicated"] = True
        report = t.compare_post_receipt_exit(data)
        self.assertEqual(report["matched_receipt_count"], 1)

    def test_forged_action_identity_not_credited(self):
        data = fixture()
        data["instances"][-1]["action_is_exact_python"] = False
        report = t.compare_post_receipt_exit(data)
        self.assertEqual(report["status"], t.FAIL)

    def test_source_and_task_writes_must_be_exact(self):
        data = fixture()
        data["source"] = "ANOTHER_PROJECT"
        with self.assertRaises(t.ExitTimelineError):
            t.compare_post_receipt_exit(data)
        data = fixture()
        data["task_writes"] = True
        with self.assertRaises(t.ExitTimelineError):
            t.compare_post_receipt_exit(data)

    def test_unknown_extra_keys_and_status_tamper_rejected(self):
        for key, value in (("production_approved", True),
                           ("verification_pass", True),
                           ("status", "APPROVED")):
            data = fixture()
            data["receipts"][0][key] = value
            with self.subTest(key=key), self.assertRaises(t.ExitTimelineError):
                t.compare_post_receipt_exit(data)
        data = fixture()
        data["instances"][0]["approval"] = True
        with self.assertRaises(t.ExitTimelineError):
            t.compare_post_receipt_exit(data)

    def test_unbounded_or_invalid_codes_rejected(self):
        for code in (-1, 0x100000000, True, "0", None):
            data = fixture()
            data["instances"][1]["result_code_201"] = code
            with self.subTest(code=code), self.assertRaises(t.ExitTimelineError):
                t.compare_post_receipt_exit(data)

    def test_bad_event_order_not_binding(self):
        data = fixture()
        data["instances"][1]["event_201_utc"] = ts(3590)
        report = t.compare_post_receipt_exit(data)
        self.assertEqual(report["status"], t.FAIL)
        self.assertEqual(report["matched_receipt_count"], 1)

    def test_future_and_non_utc_timestamp_rejected(self):
        data = fixture()
        data["receipts"][1]["started_utc"] = "2026-11-05T14:37:10"
        with self.assertRaises(t.ExitTimelineError):
            t.compare_post_receipt_exit(data)

    def test_overlapping_receipts_fail_closed(self):
        data = fixture()
        data["receipts"][1] = make_receipt(7)
        with self.assertRaises(t.ExitTimelineError):
            t.compare_post_receipt_exit(data)

    def test_event_list_bounded(self):
        data = fixture()
        data["instances"] = data["instances"] * 10
        with self.assertRaises(t.ExitTimelineError):
            t.compare_post_receipt_exit(data)

    def test_no_network_no_db_migration(self):
        r = t.compare_post_receipt_exit(fixture())
        self.assertEqual(r["public_network_requests"], 0)
        self.assertEqual(r["operating_database_writes"], 0)
        self.assertFalse(r["other_project_access"])
        self.assertFalse(r["model_training_performed"])

    def test_owner_event_wrapper_is_readonly_fixed_task(self):
        from pathlib import Path
        code = (Path(__file__).resolve().parents[1] / "scripts" /
                "ucie_public_miner_exit_timeline_v01.ps1").read_text(
                    encoding="utf-8")
        self.assertIn("TaskName']='\\UCIE-PublicMiner-Hourly'", code)
        self.assertIn("Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational'", code)
        self.assertIn("-MaxEvents 80", code)
        self.assertIn("Get-Content -LiteralPath $history -Tail 2", code)
        self.assertIn("public_miner_exit_timeline_v01", code)
        self.assertNotIn("$event.Message", code)
        for prohibited in ("Start-ScheduledTask", "Stop-ScheduledTask",
                           "Register-ScheduledTask", "Unregister-ScheduledTask",
                           "Stop-Process", "Start-Process", "Set-ScheduledTask"):
            self.assertNotIn(prohibited + " ", code)

    def test_synthetic_owner_wrapper_is_preview_default(self):
        from pathlib import Path
        code = (Path(__file__).resolve().parents[1] / "scripts" /
                "ucie_public_miner_exit_probe_v01.ps1").read_text(
                    encoding="utf-8")
        self.assertIn("param([switch]$RunSynthetic)", code)
        self.assertIn("if ($RunSynthetic.IsPresent)", code)
        self.assertIn("--run-synthetic", code)
        self.assertIn("D:\\UCIE", code)
        self.assertNotIn("public_miner_cycle.py", code)


if __name__ == "__main__":
    import unittest
    unittest.main()
