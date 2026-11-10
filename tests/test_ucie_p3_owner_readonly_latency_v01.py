"""One-shot owner Windows P3 read-only public-catalog latency acceptance.

Only the *exact* D:/UCIE checkout runs this test; CI and other roots skip.
No customer HTTP request, external fetch, scheduler operation, DB write,
persistent index, private data or upstream code execution. Results aggregate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from ucie_miner.p3_readonly_latency_v01 import SCHEMA, measure_baseline


class OwnerP3ReadOnlyLatencyAcceptance(unittest.TestCase):
    def test_owner_public_catalog_w04_and_engine_timing(self):
        root = Path(__file__).resolve().parents[1]
        if (os.name != "nt" or root.is_symlink()
                or root.resolve() != Path("D:/UCIE").resolve()):
            self.skipTest("OWNER_D_UCIE_WINDOWS_ONLY")
        try:
            result = measure_baseline(root, samples=2, warmups=1)
        except Exception as exc:
            # Fail closed; do not print raw paths, private data, records,
            # exception messages or any partial measurement as a PASS.
            print("UCIE_P3_OWNER_READONLY_LATENCY_V01="
                  + json.dumps({"schema": SCHEMA,
                                "status": "FAIL_CLOSED_NO_MEASUREMENT",
                                "error_type": type(exc).__name__,
                                "owner_host_verified": False},
                               sort_keys=True))
            self.fail("OWNER_READONLY_LATENCY_ACCEPTANCE_NO_GO")
        receipt = {
            "schema": result["schema"],
            "status": result["status"],
            "owner_host_verified": True,
            "owner_host_scope": "EXACT_D_UCIE_WINDOWS_SINGLE_TEST_FILE",
            "python_version": result["python_version"],
            "os_family": result["os_family"],
            "source_linked_public_rows": result["source_linked_public_rows"],
            "in_run_public_catalog_sha256": result[
                "in_run_public_catalog_sha256"],
            "samples": result["samples"],
            "warmups": result["warmups"],
            "read_and_validate_handoff": result[
                "read_and_validate_handoff"],
            "w04_substring_search_on_loaded_handoff": result[
                "w04_substring_search_on_loaded_handoff"],
            "p8_exact_public_catalog_engine_on_loaded_handoff": result[
                "p8_exact_public_catalog_engine_on_loaded_handoff"],
            "customer_http_latency_measured": False,
            "performance_root_cause_proven": False,
            "production_index_applied": False,
            "operating_database_writes": 0,
            "network_requests": 0,
            "v1_accepted": False,
        }
        print("UCIE_P3_OWNER_READONLY_LATENCY_V01="
              + json.dumps(receipt, sort_keys=True, ensure_ascii=True))
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["status"],
                         "OBSERVATIONAL_BASELINE_ONLY_NO_OPTIMIZATION")
        self.assertEqual(result["samples"], 2)
        self.assertEqual(result["warmups"], 1)
        self.assertGreater(result["source_linked_public_rows"], 0)
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertFalse(result["auto_promoted"])
        self.assertFalse(result["v1_accepted"])


if __name__ == "__main__":
    unittest.main()
