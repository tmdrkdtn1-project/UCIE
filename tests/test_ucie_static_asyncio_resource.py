"""Offline candidate-only regression for official CPython PR #156401.

The pre/post fragments reproduce the actual changed CPython method statements.
No upstream code execution, production signing, private files, or network.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest

from ucie_miner.static_asyncio_resource import (
    CandidateScanError, EVIDENCE, RULE_ID,
    MAX_BYTES, inspect_asyncio_protocol_factory_source,
)

# The relevant CPython 2026-09-05 pre-fix shape, across all three methods.
# Official pre-fix: e2118b0ac21191bfeecdc97758a87d88ffdda154
PRE = """\
class BaseEventLoop:
    async def create_datagram_endpoint(self, protocol_factory):
        sock = object()
        protocol = protocol_factory()
        waiter = self.create_future()
        transport = self._make_datagram_transport(
            sock, protocol, None, waiter)
        try:
            await waiter
        except:
            transport.close()
            raise

    async def connect_read_pipe(self, protocol_factory, pipe):
        protocol = protocol_factory()
        waiter = self.create_future()
        transport = self._make_read_pipe_transport(pipe, protocol, waiter)
        try:
            await waiter
        except:
            transport.close()
            raise

    async def connect_write_pipe(self, protocol_factory, pipe):
        protocol = protocol_factory()
        waiter = self.create_future()
        transport = self._make_write_pipe_transport(pipe, protocol, waiter)
        try:
            await waiter
        except:
            transport.close()
            raise
"""
# Official post-fix: ba4a0790aa8438ccd847e86910f71c9823849d05.
# Each call is protected by a broad except with resource.close/re-raise.
POST = PRE.replace(
    "sock = object()\n        protocol = protocol_factory()",
    "sock = object()\n        try:\n"
    "            protocol = protocol_factory()\n"
    "        except:\n            sock.close()\n            raise",
)
POST = POST.replace(
    "async def connect_read_pipe(self, protocol_factory, pipe):\n"
    "        protocol = protocol_factory()",
    "async def connect_read_pipe(self, protocol_factory, pipe):\n"
    "        try:\n            protocol = protocol_factory()\n"
    "        except:\n            pipe.close()\n            raise",
)
POST = POST.replace(
    "async def connect_write_pipe(self, protocol_factory, pipe):\n"
    "        protocol = protocol_factory()",
    "async def connect_write_pipe(self, protocol_factory, pipe):\n"
    "        try:\n            protocol = protocol_factory()\n"
    "        except:\n            pipe.close()\n            raise",
)


class FifthAsyncioCandidateTests(unittest.TestCase):
    def test_three_upstream_unsafe_shaped_call_sites(self):
        r = inspect_asyncio_protocol_factory_source(PRE)
        self.assertEqual(r["candidate_count"], 3)
        self.assertEqual([c["function"] for c in r["candidates"]], [
            "create_datagram_endpoint", "connect_read_pipe",
            "connect_write_pipe",
        ])
        self.assertTrue(all(c["rule_id"] == RULE_ID for c in r["candidates"]))
        self.assertTrue(all(c["public_evidence"] == EVIDENCE for c in r["candidates"]))
        self.assertEqual(r["status"], "STATIC_CANDIDATE_REVIEW_REQUIRED")
        self.assertIs(r["auto_promoted"], False)
        self.assertIs(r["owner_signed"], False)
        self.assertIs(r["source_executed"], False)

    def test_three_upstream_fixed_shaped_call_sites(self):
        r = inspect_asyncio_protocol_factory_source(POST)
        self.assertEqual(r["candidate_count"], 0)
        self.assertEqual(r["status"], "NO_PATTERN_DETECTED_NOT_A_SAFETY_PASS")
        self.assertIs(r["released_python_version_fix_coverage_verified"], False)

    def test_exception_handler_must_actually_close_same_resource(self):
        bad = POST.replace("sock.close()", "other.close()", 1)
        result = inspect_asyncio_protocol_factory_source(bad)
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["resource"], "sock")
        only_oserror = POST.replace("except:", "except OSError:", 1)
        self.assertEqual(inspect_asyncio_protocol_factory_source(
            only_oserror)["candidate_count"], 1)

    def test_cleanup_must_run_unconditionally_for_factory_failure(self):
        # The previous detector would suppress these because sock.close()
        # merely appeared somewhere inside a handler.
        close = "            sock.close()"
        unsafe = (
            POST.replace(close, "            if False:\n                sock.close()", 1),
            POST.replace(close, "            def deferred():\n                sock.close()", 1),
            POST.replace("        except:\n" + close,
                         "        except Exception:\n" + close, 1),
            POST.replace(close, "            raise RuntimeError()\n" + close, 1),
        )
        for n, source in enumerate(unsafe):
            with self.subTest(case=n):
                result = inspect_asyncio_protocol_factory_source(source)
                self.assertEqual(result["candidate_count"], 1)
                self.assertEqual(result["candidates"][0]["resource"], "sock")

    def test_cleanup_in_try_own_except_does_not_cover_its_factory(self):
        source = """
class Loop:
    async def connect_read_pipe(self, protocol_factory, pipe):
        try:
            pass
        except BaseException:
            protocol = protocol_factory()
            waiter = self.create_future()
            self._make_read_pipe_transport(pipe, protocol, waiter)
            pipe.close()
"""
        result = inspect_asyncio_protocol_factory_source(source)
        self.assertEqual(result["candidate_count"], 1)

    def test_unrelated_factory_or_no_transport_has_no_finding(self):
        source = """\
async def connect_read_pipe(protocol_factory, pipe):
    protocol = protocol_factory()
    return protocol
"""
        self.assertEqual(inspect_asyncio_protocol_factory_source(
            source)["candidate_count"], 0)
        # Documentation text and comments cannot become executable AST calls.
        source = """\
async def connect_write_pipe(self, protocol_factory, pipe):
    # protocol = protocol_factory()
    value = "protocol_factory()"
    return value
"""
        self.assertEqual(inspect_asyncio_protocol_factory_source(
            source)["candidate_count"], 0)

    def test_boundaries_fail_closed(self):
        for source in ("", "def invalid(:\n", "x" * (MAX_BYTES + 1)):
            with self.subTest(size=len(source)), self.assertRaises(
                CandidateScanError
            ):
                inspect_asyncio_protocol_factory_source(source)
        with self.assertRaises(CandidateScanError):
            inspect_asyncio_protocol_factory_source(None)

    def test_nested_factory_in_unrelated_scope_not_misattributed(self):
        source = """\
class Example:
    async def connect_read_pipe(self, protocol_factory, pipe):
        def inner():
            protocol = protocol_factory()
            waiter = self.create_future()
            return self._make_read_pipe_transport(pipe, protocol, waiter)
        return inner()
"""
        self.assertEqual(inspect_asyncio_protocol_factory_source(
            source)["candidate_count"], 0)

    def test_stdin_cli_is_inert_and_never_claims_rulepack(self):
        p = subprocess.run(
            [sys.executable, "-B", "-m",
             "ucie_miner.static_asyncio_resource"],
            input=PRE.encode("utf-8"),
            capture_output=True, check=False, timeout=15,
        )
        self.assertEqual(p.returncode, 0, p.stderr[:800].decode(errors="replace"))
        output = json.loads(p.stdout)
        self.assertEqual(output["candidate_count"], 3)
        self.assertIs(output["owner_signed"], False)
        self.assertIs(output["auto_fix"], False)
        self.assertEqual(output["persistent_writes"], 0)
        self.assertEqual(output["source_files_read"], 0)


if __name__ == "__main__":
    unittest.main()
