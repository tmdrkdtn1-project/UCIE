"""Independent, bounded UCIE-only first-party P6 before/after diagnostic.

Run from a UCIE checkout using:
  python -I -B scripts/p6_library_one_pass_benchmark.py --rows 3000 --repeats 5

No external public source, operating ledger or scheduled task is accessed.
This does not approve deployment. Output is JSON to stdout only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if ROOT.name.casefold() != "ucie" or ROOT.is_symlink():
    raise SystemExit(2)
# -I deliberately ignores PYTHONPATH. Bind only exact first-party UCIE source
# and test helpers from this same repository, without third-party package code.
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "tests"))

from test_ucie_p6_one_pass_library_before_after_v01 import measured_comparison


def main() -> int:
    p = argparse.ArgumentParser(description="Read-only UCIE P6 first-party benchmark")
    p.add_argument("--rows", type=int, default=3000)
    p.add_argument("--repeats", type=int, default=5)
    args = p.parse_args()
    try:
        report = measured_comparison(rows=args.rows, repeats=args.repeats)
    except (ValueError, OSError, RuntimeError, AssertionError) as exc:
        print(json.dumps({
            "schema": "UCIE_P6_FIRST_PARTY_ONE_PASS_EXACT_LIBRARY_V01",
            "status": "FIRST_PARTY_P6_BENCHMARK_FAIL_CLOSED",
            "reason_type": type(exc).__name__,
            "operating_database_writes": 0,
            "customer_release_approved": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
