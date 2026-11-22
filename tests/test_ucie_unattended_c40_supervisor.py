"""UCIE C40 watchdog policy tests: synthetic functional signals only."""
from datetime import datetime, timezone
import unittest

from ucie_public.policy import PolicyError
from ucie_public.unattended_c40_supervisor import (
    bind_owner_recovery_plan, decide_c40_recovery_need,
)

NOW = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)


def obs(time="2026-10-23T09:59:00Z", *, healthy=False):
    return {
        "observed_at": time, "c40_process_count": 1,
        "client_binary_and_profile_match": True,
        "process_owner_verified": True,
        "mcp_initialize_ok": True,
        "tools_list_ok": True,
        "legacy_library_search_ok": healthy,
        "admin_capabilities_ok": healthy,
    }


def history():
    return {
        "restarts_last_hour": 0, "last_restart_utc": None,
        "supervisor_lock_held": True, "scheduler_miner_idle": True,
        "external_rollback_anchor_ok": True,
    }


def readings(*, old=False, new=False):
    return [obs("2026-10-23T09:57:00Z", healthy=old),
            obs("2026-10-23T09:59:00Z", healthy=new)]


def grant():
    return {
        "status": "SIGNED_SCOPE_VERIFIED_EXECUTION_NOT_AUTHORIZED",
        "operation": "C40_RECOVERY", "target": "UCIE_C40_TUNNEL",
        "task_id": "UCIE-C40-RECOVERY-20261023", "grant_sha256": "a"*64,
    }


def shutdown():
    return {
        "service_identity": "UCIE_C40_TUNNEL",
        "exact_binary_and_profile_sha_match": True,
        "owner_process_identity_verified": True,
        "single_owner_lock_held": True,
        "functional_mcp_probe_failed": True,
        "old_process_exited": True,
        "active_miner_jobs_zero": True,
        "cooldown_elapsed": True, "prior_attempts": 0,
    }


class C40WatchdogTests(unittest.TestCase):
    def test_healthy_and_transient_failure_not_restarted(self):
        for a, expected in (
            (readings(old=True, new=True), "UCIE_C40_HEALTHY_NO_RECOVERY"),
            (readings(old=False, new=True), "UCIE_C40_HEALTHY_NO_RECOVERY"),
            (readings(old=True, new=False), "UCIE_C40_SINGLE_PROBE_FAILURE_CONFIRM_FIRST"),
        ):
            with self.subTest(expected=expected):
                d = decide_c40_recovery_need(a, history(), at_time=NOW)
                self.assertEqual(d["status"], expected)
                self.assertFalse(d["restart_performed"])
                self.assertFalse(d["supervisor_owner_grant_required"])

    def test_two_functional_failures_require_owner_grant(self):
        d = decide_c40_recovery_need(readings(), history(), at_time=NOW)
        self.assertEqual(d["status"], "UCIE_C40_OWNER_SIGNED_RECOVERY_REQUIRED")
        self.assertTrue(d["supervisor_owner_grant_required"])
        self.assertFalse(d["host_functionality_authenticated"])
        plan = bind_owner_recovery_plan(d, grant(), shutdown())
        self.assertFalse(plan["restart_performed"])
        self.assertTrue(plan["requires_trusted_windows_owner_and_external_checkpoint"])

    def test_attempt_limits_and_missing_rollback_anchor(self):
        for edit, status in (
            ({"restarts_last_hour": 2}, "UCIE_C40_RECOVERY_RATE_BLOCKED"),
            ({"last_restart_utc": "2026-10-23T09:49:00Z"}, "UCIE_C40_RECOVERY_RATE_BLOCKED"),
            ({"external_rollback_anchor_ok": False}, "UCIE_C40_RECOVERY_TRUST_GATE_BLOCKED"),
            ({"supervisor_lock_held": False}, "UCIE_C40_RECOVERY_TRUST_GATE_BLOCKED"),
            ({"scheduler_miner_idle": False}, "UCIE_C40_RECOVERY_TRUST_GATE_BLOCKED"),
        ):
            h = {**history(), **edit}
            with self.subTest(edit=edit):
                self.assertEqual(decide_c40_recovery_need(
                    readings(), h, at_time=NOW)["status"], status)

    def test_duplicate_clients_and_untrusted_types_fail_closed(self):
        two = readings()
        two[0]["c40_process_count"] = 2
        with self.assertRaises(PolicyError):
            decide_c40_recovery_need(two, history(), at_time=NOW)
        one = readings()
        one[0]["client_binary_and_profile_match"] = "true"
        with self.assertRaises(PolicyError):
            decide_c40_recovery_need(one, history(), at_time=NOW)
        for v in (True, -1, 101):
            h = {**history(), "restarts_last_hour": v}
            with self.assertRaises(PolicyError):
                decide_c40_recovery_need(readings(), h, at_time=NOW)

    def test_stale_reordered_future_and_invalid_grant_blocked(self):
        bad = readings()
        bad.reverse()
        with self.assertRaises(PolicyError):
            decide_c40_recovery_need(bad, history(), at_time=NOW)
        old = readings()
        old[0]["observed_at"] = "2026-10-22T08:00:00Z"
        with self.assertRaises(PolicyError):
            decide_c40_recovery_need(old, history(), at_time=NOW)
        future = readings()
        future[1]["observed_at"] = "2026-10-23T10:02:00Z"
        with self.assertRaises(PolicyError):
            decide_c40_recovery_need(future, history(), at_time=NOW)
        d = decide_c40_recovery_need(readings(), history(), at_time=NOW)
        with self.assertRaises(PolicyError):
            bind_owner_recovery_plan(d, {}, shutdown())
        h = shutdown()
        h["old_process_exited"] = False
        with self.assertRaises(PolicyError):
            bind_owner_recovery_plan(d, grant(), h)
        with self.assertRaises(PolicyError):
            bind_owner_recovery_plan(decide_c40_recovery_need(
                readings(old=True, new=True), history(), at_time=NOW),
                grant(), shutdown())


if __name__ == "__main__":
    unittest.main()
