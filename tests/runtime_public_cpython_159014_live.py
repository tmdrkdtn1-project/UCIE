"""ONE selected CPython public documentation fix, real isolated runtime acceptance.

Only on PR #77's explicitly gated GitHub disposable Windows and Ubuntu Python
3.15 jobs. No owner-host execution, no external patch checkout, no agent
instruction from upstream, no DB mutation and no rule promotion. Public PR
and file diff metadata are fetched from two fixed URLs, never from input.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ucie_miner.public_case_cpython_159014 import inspect_cpython_159014_observation
from runtime_python_xoption_regression import observe


def main():
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_REPOSITORY") != "tmdrkdtn1-project/UCIE"
            or os.environ.get("GITHUB_EVENT_NAME") != "pull_request"
            or os.environ.get("GITHUB_HEAD_REF") !=
               "feat/library-public-skill-catalog-preview-20261022"
            or sys.implementation.name != "cpython"
            or sys.version_info[:2] != (3, 15)
            or sys.platform not in ("linux", "win32")
            or not hasattr(sys, "is_remote_debug_enabled")):
        raise RuntimeError("wrong isolated public candidate runner")
    observation = inspect_cpython_159014_observation(
        observe=observe,
        runtime_name="CPython",
        runtime_version=sys.version.split()[0],
        platform=sys.platform)
    if (observation["status"] !=
            "PUBLIC_DOCUMENTATION_AND_CPYTHON_RUNTIME_OBSERVED_NO_GO"
            or observation["public_api_gets"] != 2
            or observation["test_transport_injected"] is not False
            or observation["automatic_rule_promotions"] != 0
            or observation["published_release_inclusion_independently_attested"] is not False
            or observation["production_approved"] is not False):
        raise RuntimeError("unverified candidate acceptance mismatch")
    # Print only reviewed bounded booleans/IDs/digests, not upstream patch text.
    print("UCIE_CPYTHON_159014_REAL_OBSERVATION=" +
          json.dumps(observation, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
