"""Single-purpose exact-root Windows Task Scheduler P10 tick entrypoint.

The scheduler does not inherit the interactive console's PYTHONPATH.
This script resolves D:/UCIE/src explicitly, never another project and never
installs tasks; existing hourly miner is completely independent.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from ucie_owner_root_gate_v01 import OwnerRootError, require_owner_runtime_root

ROOT = Path(__file__).resolve().parents[1]
if os.name == "nt":
    relocated = (__name__ == "__main__"
                 and sys.argv[1:] == ["--owner-relocated-runtime"])
    if __name__ == "__main__" and sys.argv[1:] not in (
            [], ["--owner-relocated-runtime"]):
        print(json.dumps({"status": "P10_UNKNOWN_LAUNCH_ARGUMENTS_FAIL_CLOSED"}))
        raise SystemExit(2)
    try:
        require_owner_runtime_root(ROOT, relocated=relocated, platform=os.name)
    except OwnerRootError:
        print(json.dumps({"status": "P10_WRONG_LOCAL_ROOT_FAIL_CLOSED"}))
        raise SystemExit(2)

sys.path.insert(0, str(ROOT / "src"))

from ucie_miner.runtime_pipeline import dispatch_tick  # noqa: E402


def main() -> int:
    try:
        out = dispatch_tick(ROOT)
    except Exception as exc:
        print(json.dumps({
            "schema": "UCIE_P10_INDEPENDENT_NONBLOCKING_DISPATCH_V1",
            "status": "P10_TICK_FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "operating_db_writes": 0,
            "existing_hourly_miner_modified": False,
            "auto_promoted": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
