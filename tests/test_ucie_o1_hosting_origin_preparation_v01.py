"""O1 standalone hosting preparation checks; zero customer or operating data.

Validates a dedicated origin's loopback boundary and permanent release hold,
not a live cloud server, Cloudflare configuration or customer acceptance.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
import http.client
import io
import json
import threading
import unittest
from unittest.mock import patch

from ucie_miner import hosting_origin_v01 as origin
from ucie_miner import local_v1_priority_v01 as priority


class O1HostingOriginContractTests(unittest.TestCase):
    def test_owner_local_acceptance_does_not_grant_customer_service(self):
        status = origin.readiness()
        self.assertEqual(status["schema"], origin.SCHEMA)
        self.assertEqual(status["status"], origin.STATUS)
        self.assertEqual(status["bind_host"], "127.0.0.1")
        self.assertTrue(status["owner_local_v1_accepted"])
        self.assertFalse(status["online_release_authorized"])
        self.assertFalse(status["customer_distribution_authorized"])
        self.assertFalse(status["customer_routes_enabled"])
        self.assertFalse(status["customer_authentication_implemented_here"])
        self.assertTrue(status["access_gateway_required"])
        self.assertFalse(status["serves_source_code_or_local_database"])
        self.assertEqual(status["operating_database_writes"], 0)
        self.assertEqual(status["network_fetches_by_origin"], 0)

    def test_hosting_origin_fails_if_source_release_gate_changes(self):
        for name, value in (
            ("LOCAL_V1_ACCEPTED_BY_OWNER", False),
            ("ONLINE_RELEASE_AUTHORIZED", True),
            ("PERIPHERAL_EXPANSION_AUTHORIZED", True),
        ):
            with self.subTest(flag=name), patch.object(priority, name, value):
                with self.assertRaises(origin.HostingPreparationError):
                    origin.assert_preparation_gate()
                with self.assertRaises(origin.HostingPreparationError):
                    origin.make_handler()

    def test_cli_requires_ack_and_valid_port_without_binding(self):
        for args in ([], ["--port", "8811"], [
                "--internal-preparation-only", "--port", "0"], [
                "--internal-preparation-only", "--port", "80"], [
                "--internal-preparation-only", "--port", "65536"]):
            with self.subTest(args=args), redirect_stdout(io.StringIO()) as out:
                self.assertEqual(origin.main(args), 2)
                text = json.loads(out.getvalue())
                self.assertFalse(text["online_release_authorized"])
                self.assertEqual(
                    text["status"],
                    "INTERNAL_PREPARATION_ACK_AND_VALID_PORT_REQUIRED")

    def test_fixed_loopback_host_not_caller_configurable(self):
        self.assertEqual(origin.HOST, "127.0.0.1")
        self.assertEqual(origin.DEFAULT_PORT, 8811)


class O1HostingOriginHttpTests(unittest.TestCase):
    def setUp(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), origin.make_handler())
        server.daemon_threads = True
        self.server = server
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(worker.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

    def request(self, path, method="GET", host=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, path, headers={
                "Host": host or "127.0.0.1:" + str(self.server.server_port)})
            result = connection.getresponse()
            body = result.read()
            return result.status, body, dict(result.getheaders())
        finally:
            connection.close()

    def test_health_alive_but_never_customer_ready(self):
        code, body, headers = self.request("/internal/healthz")
        self.assertEqual(code, 200)
        payload = json.loads(body)
        self.assertEqual(payload["schema"], origin.SCHEMA)
        self.assertEqual(payload["status"], origin.STATUS)
        self.assertFalse(payload["online_release_authorized"])
        self.assertFalse(payload["customer_routes_enabled"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("application/json", headers["Content-Type"])
        self.assertIn("none", headers["Content-Security-Policy"])

    def test_all_customer_and_private_routes_are_closed(self):
        for path in ("/", "/local", "/local/error?q=python",
                     "/skillbooks", "/catalog", "/admin",
                     "/internal/healthz?approved=true",
                     "/internal/healthz/extra"):
            with self.subTest(path=path):
                code, body, _ = self.request(path)
                self.assertEqual(code, 503)
                payload = json.loads(body)
                self.assertFalse(payload["online_release_authorized"])
                self.assertEqual(
                    payload["status"],
                    "CUSTOMER_APPLICATION_NOT_DEPLOYED_OR_AUTHORIZED")

    def test_forged_host_and_write_methods_fail_closed(self):
        code, body, _ = self.request("/internal/healthz",
                                     host="public.example")
        self.assertEqual(code, 403)
        self.assertEqual(json.loads(body)["status"], "LOOPBACK_ORIGIN_ONLY")
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                code, body, _ = self.request("/internal/healthz",
                                             method=method)
                self.assertEqual(code, 405)
                self.assertEqual(json.loads(body)["status"],
                                 "WRITE_METHOD_DISABLED")

    def test_head_is_bodyless_and_host_checks_still_apply(self):
        code, body, headers = self.request("/internal/healthz", method="HEAD")
        self.assertEqual(code, 200)
        self.assertEqual(body, b"")
        self.assertIn("Content-Length", headers)
        code, body, _ = self.request(
            "/internal/healthz", method="HEAD", host="attacker.example")
        self.assertEqual(code, 403)
        self.assertEqual(body, b"")


if __name__ == "__main__":
    unittest.main()
