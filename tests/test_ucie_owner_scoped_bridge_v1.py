"""UCIE-only bridge boundary; fake backend, no host/network access."""
from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

from ucie_miner import owner_scoped_bridge_v1 as b


def payload(op, **extra):
    return {"schema": b.SCHEMA, "operation": op, **extra}


class UCIEOwnerBridgeContractTests(unittest.TestCase):
    def setUp(self):
        self.allow = Mock(return_value=True)
        self.bridge = b.UCIEOwnerBridgeBoundary(
            authenticated_session_action=self.allow)

    def test_status_passes_real_roots_without_test_mode(self):
        with patch.object(b.engine, "inspect_scope",
                          return_value={"active": False}) as run:
            self.assertEqual(self.bridge.handle(payload("status")),
                             {"active": False})
        run.assert_called_once_with(b.ROOT, b.HUB)
        self.allow.assert_called_once_with("status")

    def test_enroll_requires_exact_phrase_and_no_extra_fields(self):
        with self.assertRaises(b.BridgeContractError):
            self.bridge.handle(payload("enroll", consent="yes"))
        with self.assertRaises(b.BridgeContractError):
            self.bridge.handle(payload("enroll", consent=b.engine.CONSENT,
                                       test_mode=True))
        with patch.object(b.engine, "enroll",
                          return_value={"status": "GRANT"}) as run:
            self.bridge.handle(payload("enroll", consent=b.engine.CONSENT))
        run.assert_called_once_with(b.ROOT, b.HUB, consent=b.engine.CONSENT)

    def test_revocation_requires_exact_phrase_and_uses_engine(self):
        with self.assertRaises(b.BridgeContractError):
            self.bridge.handle(payload("revoke", confirmation="revoke all"))
        with patch.object(b.engine, "revoke_scope",
                          return_value={"status": "REVOKED"}) as run:
            self.bridge.handle(payload("revoke",
                                       confirmation=b.engine.REVOKE))
        run.assert_called_once_with(b.ROOT, b.HUB,
                                    confirmation=b.engine.REVOKE)

    def test_apply_validates_then_binds_real_verifier_without_test_mode(self):
        candidate = {"schema": "UCIE_PINNED_DEV_QA_BUNDLE_V1"}
        with patch.object(b.engine, "validate_bundle",
                          return_value=("x" * 40, [])) as validate:
            with patch.object(b.engine, "apply_verified_batch",
                              return_value={"status": "NO_DEPLOY"}) as apply:
                got = self.bridge.handle(payload("apply", bundle=candidate))
        self.assertEqual(got["status"], "NO_DEPLOY")
        validate.assert_called_once_with(candidate)
        args, kwargs = apply.call_args
        self.assertEqual(args, (b.ROOT, b.HUB, candidate))
        self.assertIs(kwargs["verify_ci_and_sources"],
                      b.engine.verify_github_ci_and_source_blobs)
        self.assertNotIn("test_mode", kwargs)

    def test_untrusted_request_cannot_supply_root_or_callback(self):
        for name, value in (("root", "D:/OTHER"), ("owner", True),
                            ("verify_ci_and_sources", "pass"),
                            ("test_mode", True),
                            ("source_url", "https://example.com")):
            with self.subTest(name=name), self.assertRaises(
                    b.BridgeContractError):
                self.bridge.handle(payload("status", **{name: value}))

    def test_false_and_truthy_nonboolean_session_denied(self):
        for value in (False, 1, "yes", {}, None):
            with self.subTest(value=value):
                bridge = b.UCIEOwnerBridgeBoundary(
                    authenticated_session_action=lambda _: value)
                with self.assertRaises(b.BridgeContractError):
                    bridge.handle(payload("status"))

    def test_authentication_exception_is_sanitized(self):
        def fail(_):
            raise RuntimeError("private-token-shall-not-leak")
        bridge = b.UCIEOwnerBridgeBoundary(
            authenticated_session_action=fail)
        with self.assertRaises(b.BridgeContractError) as ctx:
            bridge.handle(payload("status"))
        self.assertNotIn("private-token", str(ctx.exception))

    def test_missing_authenticator_denied(self):
        for auth in (None, True, 1):
            with self.subTest(auth=auth), self.assertRaises(
                    b.BridgeContractError):
                b.UCIEOwnerBridgeBoundary(
                    authenticated_session_action=auth)

    def test_unknown_operation_denied(self):
        for op in ("delete", "shell", "scheduler", "train",
                   "publish", "", None):
            with self.subTest(op=op), self.assertRaises(
                    b.BridgeContractError):
                self.bridge.handle(payload(op))

    def test_wrong_schema_and_payload_type_denied(self):
        cases = ({"schema": "OTHER", "operation": "status"}, [], None, 1,
                 {"schema": b.SCHEMA, "operation": "status", "bundle": {}})
        for data in cases:
            with self.subTest(data=data), self.assertRaises(
                    b.BridgeContractError):
                self.bridge.handle(data)

    def test_missing_consent_field_denied(self):
        with self.assertRaises(b.BridgeContractError):
            self.bridge.handle(payload("enroll"))

    def test_missing_revocation_confirmation_denied(self):
        with self.assertRaises(b.BridgeContractError):
            self.bridge.handle(payload("revoke"))

    def test_apply_requires_bundle(self):
        with self.assertRaises(b.BridgeContractError):
            self.bridge.handle(payload("apply"))

    def test_apply_invalid_bundle_rejected_before_identity_gate(self):
        with self.assertRaises(b.engine.ScopeError):
            self.bridge.handle(payload("apply", bundle={"fake": True}))
        self.allow.assert_not_called()

    def test_oversized_envelope_denied(self):
        with self.assertRaises(b.BridgeContractError):
            self.bridge.handle(payload("enroll", consent="x" * b.MAX_REQUEST_BYTES))

    def test_unserializable_object_denied(self):
        with self.assertRaises(b.BridgeContractError):
            self.bridge.handle(payload("apply", bundle=object()))

    def test_no_authority_callback_on_invalid_request(self):
        with self.assertRaises(b.BridgeContractError):
            self.bridge.handle(payload("sudo"))
        self.allow.assert_not_called()

    def test_main_only_describes_inert_bridge(self):
        with patch("builtins.print") as output:
            self.assertEqual(b.main(), 0)
        result = json.loads(output.call_args.args[0])
        self.assertEqual(result["status"],
                         "TRUSTED_UCIE_BRIDGE_INTEGRATION_REQUIRED")
        self.assertFalse(result["host_changed"])
        self.assertFalse(result["identity_attested"])


    def test_request_snapshot_is_independent_of_caller_mutation(self):
        request = payload("apply", bundle={"schema": "FIRST"})
        seen = []
        def authorize(op):
            self.assertEqual(op, "apply")
            request["bundle"]["schema"] = "MODIFIED_AFTER_VALIDATION"
            return True
        bridge = b.UCIEOwnerBridgeBoundary(
            authenticated_session_action=authorize)
        with patch.object(b.engine, "validate_bundle",
                          side_effect=lambda bundle: seen.append(bundle["schema"])):
            with patch.object(b.engine, "apply_verified_batch",
                              return_value={"status": "PASS"}) as apply:
                result = bridge.handle(request)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(seen, ["FIRST"])
        self.assertEqual(apply.call_args.args[2], {"schema": "FIRST"})
        self.assertEqual(request["bundle"], {"schema": "MODIFIED_AFTER_VALIDATION"})

    def test_valid_request_is_snapshot_not_same_object(self):
        value = payload("enroll", consent=b.engine.CONSENT)
        op, frozen = b._request(value)
        self.assertEqual(op, "enroll")
        self.assertEqual(frozen, value)
        self.assertIsNot(frozen, value)
        value["consent"] = "MODIFIED"
        self.assertEqual(frozen["consent"], b.engine.CONSENT)

    def test_serialization_cannot_inject_untrusted_object(self):
        class Untrusted:
            pass
        with self.assertRaises(b.BridgeContractError):
            self.bridge.handle(payload("apply", bundle=Untrusted()))
        self.allow.assert_not_called()


if __name__ == "__main__":
    unittest.main()
