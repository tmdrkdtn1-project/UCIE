"""UCIE-only explicit MCP registration; no listener, filesystem or scheduled task."""
import unittest
from unittest.mock import Mock, patch

from ucie_miner import owner_scoped_mcp_tools_v1 as reg
from ucie_miner import owner_scoped_bridge_v1 as bridge


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self, *, name):
        def decorated(fn):
            if name in self.tools:
                raise ValueError("duplicate registration")
            self.tools[name] = fn
            return fn
        return decorated


class UCIEScopedMCPRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.server = FakeMCP()
        self.authorize = Mock(return_value=True)
        self.boundary = bridge.UCIEOwnerBridgeBoundary(
            authenticated_session_action=self.authorize)

    def test_register_four_handlers_no_server_created(self):
        state = reg.register_ucie_owner_scope_tools(self.server, boundary=self.boundary)
        self.assertEqual(state["tool_count"], 4)
        self.assertEqual(set(state["tool_names"]), set(self.server.tools))
        self.assertFalse(state["new_server"])
        self.assertFalse(state["new_tunnel"])
        self.assertFalse(state["owner_grant_created"])
        self.authorize.assert_not_called()

    def test_existing_legacy_tools_are_untouched(self):
        self.server.tools["search_ucie_evidence"] = lambda: "existing"
        self.server.tools["ucie_admin_capabilities"] = lambda: "existing"
        reg.register_ucie_owner_scope_tools(self.server, boundary=self.boundary)
        self.assertEqual(self.server.tools["search_ucie_evidence"](), "existing")
        self.assertEqual(self.server.tools["ucie_admin_capabilities"](), "existing")

    def test_status_routes_to_readonly_backend(self):
        with patch.object(bridge.engine, "inspect_scope",
                          return_value={"status": "NOT_ENROLLED"}) as check:
            reg.register_ucie_owner_scope_tools(self.server, boundary=self.boundary)
            result = self.server.tools["ucie_owner_scope_status"]()
        self.assertEqual(result["status"], "NOT_ENROLLED")
        check.assert_called_once_with(bridge.ROOT, bridge.HUB)
        self.authorize.assert_called_once_with("status")

    def test_enroll_passes_exact_consent_only(self):
        reg.register_ucie_owner_scope_tools(self.server, boundary=self.boundary)
        with patch.object(bridge.engine, "enroll",
                          return_value={"status": "ENROLLED"}) as called:
            got = self.server.tools["ucie_owner_scope_enroll"](bridge.engine.CONSENT)
        self.assertEqual(got["status"], "ENROLLED")
        called.assert_called_once_with(bridge.ROOT, bridge.HUB,
                                       consent=bridge.engine.CONSENT)

    def test_revoke_routes_to_bounded_backend(self):
        reg.register_ucie_owner_scope_tools(self.server, boundary=self.boundary)
        with patch.object(bridge.engine, "revoke_scope",
                          return_value={"status": "REVOKED"}) as called:
            got = self.server.tools["ucie_owner_scope_revoke"](bridge.engine.REVOKE)
        self.assertEqual(got["status"], "REVOKED")
        called.assert_called_once_with(bridge.ROOT, bridge.HUB,
                                       confirmation=bridge.engine.REVOKE)

    def test_apply_binds_pinned_github_backend(self):
        reg.register_ucie_owner_scope_tools(self.server, boundary=self.boundary)
        fake = {"schema": "UCIE_PINNED_DEV_QA_BUNDLE_V1"}
        with patch.object(bridge.engine, "validate_bundle",
                          return_value=("a" * 40, [])) as check:
            with patch.object(bridge.engine, "apply_verified_batch",
                              return_value={"status": "NO_EXECUTION"}) as applied:
                got = self.server.tools["ucie_owner_scope_apply"](fake)
        self.assertEqual(got["status"], "NO_EXECUTION")
        check.assert_called_once_with(fake)
        self.assertIs(applied.call_args.kwargs["verify_ci_and_sources"],
                      bridge.engine.verify_github_ci_and_source_blobs)
        self.assertNotIn("test_mode", applied.call_args.kwargs)

    def test_bad_consent_rejected_before_backend(self):
        reg.register_ucie_owner_scope_tools(self.server, boundary=self.boundary)
        with patch.object(bridge.engine, "enroll") as called:
            with self.assertRaises(bridge.BridgeContractError):
                self.server.tools["ucie_owner_scope_enroll"]("APPROVE")
        called.assert_not_called()

    def test_missing_authorization_denies_every_operation(self):
        deny = bridge.UCIEOwnerBridgeBoundary(
            authenticated_session_action=lambda _op: False)
        reg.register_ucie_owner_scope_tools(self.server, boundary=deny)
        with self.assertRaises(bridge.BridgeContractError):
            self.server.tools["ucie_owner_scope_status"]()

    def test_no_owner_boundary_or_fake_instance(self):
        for value in (None, object(), True, "approved"):
            with self.subTest(value=value), self.assertRaises(
                    bridge.BridgeContractError):
                reg.register_ucie_owner_scope_tools(FakeMCP(), boundary=value)

    def test_no_tool_decorator_denied(self):
        with self.assertRaises(bridge.BridgeContractError):
            reg.register_ucie_owner_scope_tools(object(), boundary=self.boundary)

    def test_double_registration_does_not_replace_tools(self):
        reg.register_ucie_owner_scope_tools(self.server, boundary=self.boundary)
        before = dict(self.server.tools)
        with self.assertRaises(ValueError):
            reg.register_ucie_owner_scope_tools(self.server, boundary=self.boundary)
        for key in before:
            self.assertIs(self.server.tools[key], before[key])


if __name__ == "__main__":
    unittest.main()
