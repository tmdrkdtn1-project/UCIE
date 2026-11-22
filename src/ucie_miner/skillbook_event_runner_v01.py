"""UCIE-only first-party Event runner for SkillBook resource snapshot.

Actual threading synchronization on tiny UCIE-authored synthetic counts.
Never reads OS file descriptors, imports source patches, fetches network,
runs commands, or asserts upstream fix validity.
"""
from __future__ import annotations

from threading import Event, Lock, Thread
from time import monotonic

SCHEMA = "UCIE_SKILLBOOK_EVENT_RUNNER_V01"
MODES = frozenset({"benign_cleanup", "changed_count", "timeout"})
MAX_TIMEOUT_SECONDS = 0.5


def run_event_scenario(mode: str) -> dict:
    """Exercise a bounded real Event wait in a UCIE-only synthetic scenario."""
    if type(mode) is not str or mode not in MODES:
        raise ValueError("unsupported UCIE first-party scenario")
    state = {"count": 7}
    mutex, complete, allow_cleanup = Lock(), Event(), Event()
    old_count = 7

    def cleanup():
        # The thread is wholly authored by UCIE; no external callable input.
        if not allow_cleanup.wait(MAX_TIMEOUT_SECONDS):
            return
        with mutex:
            state["count"] = 6
        complete.set()

    child = Thread(target=cleanup, name="UCIE_SkillBook_SyntheticCleanup",
                   daemon=True)
    child.start()
    try:
        start = monotonic()
        if mode != "timeout":
            allow_cleanup.set()
            finished = complete.wait(MAX_TIMEOUT_SECONDS)
        else:
            finished = complete.wait(0)
        wait_seconds = monotonic() - start
        if finished:
            with mutex:
                stable_baseline = state["count"]
                if mode == "changed_count":
                    state["count"] += 1
                after_trial = state["count"]
            status = ("STABLE_NO_CHANGE" if after_trial == stable_baseline
                      else "DIFFERENCE_DETECTED")
        else:
            stable_baseline = None
            after_trial = None
            status = "BLOCKED_NO_COMPLETION"
    finally:
        allow_cleanup.set()
        child.join(timeout=MAX_TIMEOUT_SECONDS)
    if child.is_alive():
        raise RuntimeError("UCIE synthetic worker did not stop")
    expected = {
        "benign_cleanup": "STABLE_NO_CHANGE",
        "changed_count": "DIFFERENCE_DETECTED",
        "timeout": "BLOCKED_NO_COMPLETION",
    }[mode]
    return {
        "schema": SCHEMA, "mode": mode, "status": status,
        "expected_matches": status == expected,
        "naive_early_baseline": old_count,
        "stabilized_baseline": stable_baseline,
        "after_trial": after_trial,
        "real_event_wait_executed": True,
        "event_wait_seconds": round(wait_seconds, 6),
        "worker_joined": True,
        "synthetic_only": True,
        "real_fd_count_measured": False,
        "upstream_code_executed": False,
        "source_api_called": False,
        "operating_database_writes": 0,
        "c40_or_scheduled_tasks_modified": False,
    }


def evaluate_first_party_event_suite() -> dict:
    trials = [run_event_scenario(x) for x in
              ("benign_cleanup", "changed_count", "timeout")]
    return {
        "schema": SCHEMA,
        "status": ("UCIE_EVENT_SYNTHETIC_PASS_NOT_UPSTREAM_QA"
                   if all(row["expected_matches"] for row in trials)
                   else "UCIE_EVENT_SYNTHETIC_FAILED"),
        "passed": sum(row["expected_matches"] for row in trials),
        "total": len(trials),
        "cases": trials,
        "independent_upstream_verified": False,
        "installable_skill_approved": False,
    }
