"""Run one bounded UCIE-only B5 internal technical pilot and print JSON.

Invocation from an isolated UCIE review checkout only:
  PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -B scripts/ucie_v2_b5_disposable_probe.py
No customer data, network calls, filesystem scans, DB writes, or task changes.
"""
from __future__ import annotations

import json

from ucie_miner.ucie_v2_b5_internal_probe_v01 import run_internal_probe


def main() -> int:
    result = run_internal_probe(repeats=4)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
