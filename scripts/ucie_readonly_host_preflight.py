"""UCIE-only owner-PC read-only preflight, never run by CI or scheduler.

Execute manually only after separate authorization to inspect D:/UCIE.
This tool never registers tasks, imports candidates or writes to SQLite.
"""
from pathlib import Path
import json
import os
import sys

ROOT = Path("D:/UCIE")
if os.name != "nt" or ROOT.is_symlink() or not ROOT.is_dir():
    print(json.dumps({"status": "FAIL_CLOSED", "error": "UCIE_WINDOWS_ROOT_UNAVAILABLE"}))
    raise SystemExit(2)

sys.path.insert(0, str(ROOT / "src"))
from ucie_miner.host_preflight import inspect_ucie_host


if __name__ == "__main__":
    try:
        report = inspect_ucie_host(
            ROOT, is_windows=os.name == "nt",
            python_version=tuple(sys.version_info[:2]))
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED",
                          "error_type": type(exc).__name__}))
        raise SystemExit(2)
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(0 if report["status"] == "READ_ONLY_PRECHECK_COMPLETE" else 2)
