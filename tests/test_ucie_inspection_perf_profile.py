"""Read-only UCIE integrated-scan performance profile, fixed first-party text.

Run before and after focused optimization; assertion checks equality of findings
so speedups may never come from losing a detector. No other-project access.
"""
from __future__ import annotations

import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from ucie_miner import existing_rule_inspection as target


class UCIEIntegratedInspectionProfile(unittest.TestCase):
    def test_cli_startup_cost_for_existing_vs_lightweight_entrypoint(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(root.name.casefold(), "ucie")
        source = "def benign():\n    return 42\n"
        calls = {
            "main_cli": [sys.executable, "-B", "-m", "ucie_miner",
                         "scan-python-stdin", "--all-existing-rules"],
            "light_cli": [sys.executable, "-B", "-m",
                          "ucie_miner.existing_rule_inspection",
                          "--ucie-root", str(root)],
        }
        for name, argv in calls.items():
            times = []
            for _ in range(4):
                start = time.perf_counter()
                result = subprocess.run(
                    argv, cwd=root, input=source,
                    capture_output=True, text=True, timeout=12,
                )
                times.append((time.perf_counter()-start)*1000)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["finding_count"], 0)
            print("UCIE_CLI_PROFILE="+json.dumps({
                "entrypoint":name, "iterations":4,
                "median_ms":round(statistics.median(times),2),
                "min_ms":round(min(times),2),
                "max_ms":round(max(times),2),
            }, sort_keys=True))

    def test_feedback_cli_startup_cost_for_existing_vs_lightweight_entrypoint(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(root.name.casefold(), "ucie")
        rows = [
            {"case_id": "positive", "source": (
                "import _pydecimal as d\n"
                "with d.localcontext() as ctx:\n"
                "    ctx.prec = d.MAX_PREC\n"
                "    value = d.Decimal('1')\n"
                "    result = value % 1\n"),
             "expected_rule_ids": ["PY_DECIMAL_UNBOUNDED_PURE_PYTHON_REVIEW"]},
            {"case_id": "negative", "source": "def clean():\n    return 7\n",
             "expected_rule_ids": []},
        ]
        calls = {
            "main_feedback": [sys.executable, "-B", "-m", "ucie_miner",
                              "feedback-python-synthetic-stdin"],
            "light_feedback": [sys.executable, "-B", "-m",
                               "ucie_miner.existing_rule_inspection",
                               "--ucie-root", str(root), "--feedback-synthetic"],
        }
        for name, argv in calls.items():
            times = []
            for _ in range(4):
                start = time.perf_counter()
                result = subprocess.run(
                    argv, cwd=root, input=json.dumps(rows),
                    capture_output=True, text=True, timeout=12,
                )
                times.append((time.perf_counter()-start)*1000)
                self.assertEqual(result.returncode, 0, result.stderr)
                outcome = json.loads(result.stdout)
                self.assertEqual(outcome["true_positive_rules"], 1)
                self.assertEqual(outcome["false_positive_rules"], 0)
            print("UCIE_CLI_PROFILE="+json.dumps({
                "entrypoint":name, "iterations":4,
                "median_ms":round(statistics.median(times),2),
                "min_ms":round(min(times),2),
                "max_ms":round(max(times),2),
            }, sort_keys=True))

    def test_fixed_source_profile_and_detector_counters(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(root.name.casefold(), "ucie")
        cases = {
            "plain": "\n".join(
                f"def func_{i}(n):\n    return n + {i}\n"
                for i in range(55)
            ),
            "scandir": (
                "import os\nfrom concurrent.futures import ThreadPoolExecutor\n"
                "def run(folder, cb):\n"
                "    iterator = os.scandir(folder)\n"
                "    with ThreadPoolExecutor(max_workers=2) as pool:\n"
                "        return pool.submit(cb, iterator).result()\n"
            ),
            "decimal": (
                "import _pydecimal as d\n"
                "with d.localcontext() as c:\n"
                "    c.prec = d.MAX_PREC\n"
                "    x = d.Decimal('1')\n"
                "    y = x % 1\n"
            ),
        }
        for label, code in cases.items():
            counters = {"scandir":0, "asyncio":0, "mcp":0, "decimal":0}
            originals = {
                "scandir": target.inspect_python_scandir_source,
                "asyncio": target.inspect_asyncio_protocol_factory_source,
                "mcp": target.inspect_mcp_empty_meta_source,
                "decimal": target.inspect_decimal_source,
            }
            patches = []
            try:
                for short, func in originals.items():
                    def wrap(s, *, func=func, key=short):
                        counters[key] += 1
                        return func(s)
                    patches.append(patch.object(
                        target, {
                            "scandir":"inspect_python_scandir_source",
                            "asyncio":"inspect_asyncio_protocol_factory_source",
                            "mcp":"inspect_mcp_empty_meta_source",
                            "decimal":"inspect_decimal_source",
                        }[short], side_effect=wrap,
                    ))
                for part in patches:
                    part.start()
                times = []
                results = []
                for i in range(40):
                    start = time.perf_counter()
                    result = target.inspect_existing_python(code)
                    times.append((time.perf_counter()-start)*1000)
                    results.append(tuple(x["rule_id"] for x in result["findings"]))
                self.assertEqual(len(set(results)), 1)
                self.assertFalse(result["auto_promoted"])
                self.assertEqual(result["database_writes"], 0)
                expected = 0 if label=="plain" else 1
                self.assertEqual(result["finding_count"], expected)
                print("UCIE_INSPECTION_PROFILE="+json.dumps({
                    "case":label, "source_bytes":len(code.encode("utf-8")),
                    "iterations":40,
                    "median_ms":round(statistics.median(times),4),
                    "max_ms":round(max(times),4),
                    "scan_calls":counters,
                    "finding_count":result["finding_count"],
                }, sort_keys=True))
            finally:
                for part in reversed(patches):
                    part.stop()


if __name__ == "__main__":
    unittest.main()
