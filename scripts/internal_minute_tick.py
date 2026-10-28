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

ROOT = Path(__file__).resolve().parents[1]
if os.name == "nt":
    expected = Path("D:/UCIE").resolve()
    if ROOT != expected or ROOT.is_symlink():
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
