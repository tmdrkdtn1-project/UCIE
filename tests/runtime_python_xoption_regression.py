"""First UCIE prevention rule: real CPython feature-enabled, isolated subprocess check.

This does not execute upstream code or inspect private files. Run *only* on
disposable CI runners, not from the live hourly miner. Reports a bounded
observation of the three CLI options; does not claim pre/post fix,
upstream release inclusion, sign-off or automatic rule promotion.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys


def observe(arguments):
    # Explicit interpreter and hard-coded inert Python source only. No shell.
    # Isolated -I mode ignores user site and PYTHON* environment settings.
    code = "import sys; print(sys.is_remote_debug_enabled())"
    env = os.environ.copy()
    env.pop("PYTHON_DISABLE_REMOTE_DEBUG", None)
    result = subprocess.run(
        [sys.executable, "-I", *arguments, "-c", code],
        capture_output=True, text=True, check=False, timeout=8, env=env,
    )
    if (result.returncode != 0
            or result.stdout.strip() not in ("True", "False")
            or result.stderr.strip()):
        raise RuntimeError("isolated CPython behavior probe failed")
    return result.stdout.strip() == "True"


def main():
    if (sys.implementation.name != "cpython"
            or sys.version_info[:2] != (3, 15)
            or not hasattr(sys, "is_remote_debug_enabled")):
        raise RuntimeError("supported CPython 3.15 feature-enabled runner required")
    baseline = observe([])
    wrong = observe(["-X", "disable_remote_debug"])
    right = observe(["-X", "disable-remote-debug"])
    if (baseline, wrong, right) != (True, True, False):
        raise AssertionError(
            "security control not independently verified; fail closed")
    print("UCIE_PYTHON_XOPTION_RUNTIME_REGRESSION=" + json.dumps({
        "schema": "UCIE_PYTHON_XOPTION_RUNTIME_OBSERVATION_V1",
        "runtime": "CPython",
        "runtime_version": sys.version.split()[0],
        "platform": sys.platform,
        "case": "python/cpython#159014",
        "baseline_enabled": baseline,
        "misspelled_option_still_enabled": wrong,
        "correct_option_disabled": not right,
        "observed": "ISOLATED_RUNTIME_FLAG_DIFFERENCE_CONFIRMED",
        "safe_call": "-X disable-remote-debug",
        "claim_scope": "EPHEMERAL_CI_RUNNER_ONLY",
        "independent_of_owner_host": True,
        "pinned_before_after_source_binaries_tested": False,
        "rulepack_signed": False,
        "production_approved": False,
        "persistent_writes": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
