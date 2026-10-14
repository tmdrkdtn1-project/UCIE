"""Entrypoint restricted to the standalone D:/UCIE checkout on Windows.

No project access, no GitHub credentials, no global scheduler installation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if os.name == "nt":
    expected = Path("D:/UCIE").resolve()
    if ROOT.resolve() != expected or ROOT.is_symlink():
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "UCIE checkout is not D:/UCIE"}))
        raise SystemExit(2)

sys.path.insert(0, str(ROOT / "src"))
from ucie_miner.worker import run_cycle
from ucie_miner.core import mine_once


def main() -> int:
    try:
        result = run_cycle(ROOT, collect=lambda root: mine_once(root, crosscheck_origin=True), enforce_schedule=True)
    except Exception as exc:
        result = {"status": "FAIL_CLOSED", "error_type": type(exc).__name__}
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0 if result["status"] == "COLLECTED_UNVERIFIED" else (
        3 if result["status"] == "SKIPPED_ALREADY_RUNNING" else (0 if result["status"] == "SKIPPED_NOT_DUE" else 2)
    )


if __name__ == "__main__":
    raise SystemExit(main())
