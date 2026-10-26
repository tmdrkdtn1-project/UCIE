"""UCIE-owned safe runtime observation of CPython gh-156400 resource cleanup.

Runs only first-party asyncio with mock resources, no sockets opened,
no network, upstream code execution, native crash attempt, production changes,
Rulepack signing, source promotion or private-project access.
Official upstream test pattern: python/cpython PR #156401.
"""
from __future__ import annotations

import asyncio
import json
import socket
import sys
import unittest
from unittest import mock


class PythonAsyncioFactoryCleanupObservation(unittest.TestCase):
    def test_local_three_pre_transport_factory_failure_paths(self) -> None:
        if sys.version_info[:3] not in ((3, 15, 0), (3, 15, 1)):
            self.skipTest("Only locally observed Python 3.15.0/3.15.1 baseline; no other-version claims")

        class UCIEControlledError(Exception):
            pass

        def factory() -> None:
            raise UCIEControlledError("UCIE-owned synthetic failure, no external code")

        loop = asyncio.new_event_loop()
        observed = []
        try:
            for label in ("create_datagram_endpoint", "connect_read_pipe",
                          "connect_write_pipe"):
                resource = mock.Mock()
                if label == "create_datagram_endpoint":
                    resource.type = socket.SOCK_DGRAM
                    operation = loop.create_datagram_endpoint(factory, sock=resource)
                else:
                    operation = getattr(loop, label)(factory, resource)

                with self.assertRaises(UCIEControlledError, msg=label):
                    loop.run_until_complete(operation)

                observed.append({
                    "operation": label,
                    "factory_exception_propagated": True,
                    "resource_close_called": bool(resource.close.called),
                    "mock_resource_only": True,
                })
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        result = {
            "schema": "UCIE_FIFTH_RULE_ACTUAL_PYTHON_RUNTIME_OBSERVATION_V1",
            "python_version": ".".join(map(str, sys.version_info[:3])),
            "status": ("UNPATCHED_FACTORY_CLEANUP_GAP_OBSERVED"
                       if not any(x["resource_close_called"] for x in observed)
                       else "MIXED_OR_PATCHED_RUNTIME_BEHAVIOR"),
            "observations": observed,
            "real_sockets_opened": 0,
            "untrusted_code_executed": False,
            "private_files_read": 0,
            "persistent_writes": 0,
            "automatic_rule_approval": False,
            "independent_human_qa": False,
        }
        print("UCIE_FIFTH_RUNTIME_OBSERVATION=" + json.dumps(result, sort_keys=True))
        # A PASS requires all three exceptions actually reached the owner
        # factory and all observations were captured, not a claim of a fix.
        self.assertEqual(len(observed), 3)
        self.assertTrue(all(x["factory_exception_propagated"] for x in observed))


if __name__ == "__main__":
    unittest.main()
