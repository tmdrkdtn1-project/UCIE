"""Synthetic UCIE single-tunnel recovery; never any real process."""
import unittest

from ucie_public.policy import PolicyError
from ucie_public.unattended_c40_recovery_runner import synthetic_one_c40_recovery
from ucie_public.unattended_c40_supervisor import SCHEMA


def decision():
    return {
        "schema": SCHEMA,
        "status": "UCIE_C40_OWNER_SIGNED_RECOVERY_REQUIRED",
    }


def plan():
    return {
        "status": "UCIE_C40_OWNER_RECOVERY_PLAN_BOUND_NO_RESTART",
        "restart_performed": False,
    }


def healthy_probe(value):
    return {
        "initialize": True, "tools_list": True,
        "public_search": value, "admin_capabilities": value,
    }


def health(count):
    return {
        "c40_client_count": count, "pinned_binary_sha256_matched": True,
        "pinned_profile_sha256_matched": True, "owner_sid_matched": True,
        "single_owner_lock_held": True, "public_miner_idle": True,
    }


class FixtureC40:
    ucie_synthetic_only = True

    def __init__(self, *, healthy_now=False, after_restart_ok=True,
                 old_exits=True, start_ok=True):
        self.count = 1
        self.started = False
        self.healthy_now = healthy_now
        self.after_restart_ok = after_restart_ok
        self.old_exits = old_exits
        self.start_ok = start_ok
        self.events = []

    def observe(self):
        self.events.append("observe")
        return health(self.count)

    def probe(self):
        self.events.append("probe")
        return healthy_probe(self.after_restart_ok if self.started else self.healthy_now)

    def stop_one_pinned(self):
        self.events.append("stop")
        if self.old_exits:
            self.count = 0
        return True

    def start_one_pinned(self):
        self.events.append("start")
        if self.start_ok:
            self.count = 1
            self.started = True
        return self.start_ok


class RecoverySequenceTests(unittest.TestCase):
    def test_single_good_recovery_sequence(self):
        sim = FixtureC40()
        result = synthetic_one_c40_recovery(decision(), plan(), sim)
        self.assertEqual(result["status"], "UCIE_SYNTHETIC_C40_RECOVERY_SEQUENCE_PASS")
        self.assertFalse(result["actual_windows_process_touched"])
        self.assertFalse(result["real_live_mcp_verified"])
        self.assertFalse(result["production_approved"])
        self.assertEqual(sim.events, [
            "observe", "probe", "stop", "observe", "start", "observe", "probe",
        ])

    def test_healthy_tunnel_must_not_be_restarted(self):
        sim = FixtureC40(healthy_now=True)
        with self.assertRaises(PolicyError):
            synthetic_one_c40_recovery(decision(), plan(), sim)
        self.assertEqual(sim.events, ["observe", "probe"])

    def test_lingering_old_process_prevents_duplicate(self):
        sim = FixtureC40(old_exits=False)
        with self.assertRaises(PolicyError):
            synthetic_one_c40_recovery(decision(), plan(), sim)
        self.assertNotIn("start", sim.events)

    def test_failed_postprobe_does_not_retry(self):
        sim = FixtureC40(after_restart_ok=False)
        result = synthetic_one_c40_recovery(decision(), plan(), sim)
        self.assertEqual(result["status"], "UCIE_SYNTHETIC_C40_POSTPROBE_FAILURE_HOLD")
        self.assertTrue(result["requires_human_reconciliation"])
        self.assertFalse(result["retry_allowed_without_new_grant"])
        self.assertEqual(sim.events.count("start"), 1)

    def test_malicious_mock_or_foreign_plan_denied(self):
        with self.assertRaises(PolicyError):
            synthetic_one_c40_recovery(decision(), plan(), object())
        with self.assertRaises(PolicyError):
            synthetic_one_c40_recovery({"schema": SCHEMA, "status": "HEALTHY"}, plan(), FixtureC40())
        with self.assertRaises(PolicyError):
            synthetic_one_c40_recovery(decision(), {"status": "UNVERIFIED"}, FixtureC40())


if __name__ == "__main__":
    unittest.main()
