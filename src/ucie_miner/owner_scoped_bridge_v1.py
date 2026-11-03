"""UCIE-only bounded bridge interface. No server, scheduler or autonomous apply.

The hosting UCIE bridge MUST provide an independently attested local-session
authorizer. A caller-supplied boolean, claimed identity or consent phrase is
not authentication. This module never enrolls or deploys on import or CLI.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from . import owner_scoped_batch_v1 as engine
from . import ucie_admin_history_verdict_v1 as historical_gate

SCHEMA = "UCIE_OWNER_SCOPED_BRIDGE_CONTRACT_V1"
ROOT = Path(r"D:\UCIE")
HUB = Path(r"D:\UCIE_HUB")
ALLOWED = {
    "status": frozenset(("schema", "operation")),
    "enroll": frozenset(("schema", "operation", "consent")),
    "revoke": frozenset(("schema", "operation", "confirmation")),
    "apply": frozenset(("schema", "operation", "bundle")),
}
MAX_REQUEST_BYTES = 850_000


class BridgeContractError(ValueError):
    """Sanitized denial by UCIE-only bridge boundary."""


def _request(payload: object) -> tuple[str, dict]:
    if type(payload) is not dict:
        raise BridgeContractError("invalid UCIE bridge request")
    op = payload.get("operation")
    if type(op) is not str or op not in ALLOWED:
        raise BridgeContractError("operation not allowlisted")
    if payload.get("schema") != SCHEMA or set(payload) != ALLOWED[op]:
        raise BridgeContractError("UCIE bridge request fields mismatch")
    try:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True,
                             allow_nan=False, separators=(",", ":"))
    except (ValueError, TypeError, RecursionError) as exc:
        raise BridgeContractError("invalid UCIE bridge request data") from exc
    if len(encoded) > MAX_REQUEST_BYTES:
        raise BridgeContractError("UCIE bridge request too large")
    # Freeze the entire request before authentication. The caller's dict may
    # be mutated while the trusted backend checks the session; never apply a
    # payload different from the one that passed allowlist/size validation.
    request = json.loads(encoded)
    if op == "enroll" and request["consent"] != engine.CONSENT:
        raise BridgeContractError("local scoped consent missing")
    if op == "revoke" and request["confirmation"] != engine.REVOKE:
        raise BridgeContractError("exact revocation confirmation missing")
    if op == "apply":
        engine.validate_bundle(request["bundle"])
    return op, request


class UCIEOwnerBridgeBoundary:
    """Host-only contract: credential checks MUST live in the bridge service.

    authenticated_session_action is a server-owned trusted callback, never
    parsed from payload. No test_mode, root override, shell or custom verifier
    can be supplied by a remote caller. This class is not itself an identity
    provider or a remote endpoint.
    """

    def __init__(self, *, authenticated_session_action: Callable[[str], bool]):
        if not callable(authenticated_session_action):
            raise BridgeContractError("trusted local authorizer required")
        self._authenticated_session_action = authenticated_session_action

    def handle(self, payload: object) -> dict:
        op, request = _request(payload)
        try:
            authorized = self._authenticated_session_action(op)
        except Exception as exc:
            raise BridgeContractError("UCIE owner session gate unavailable") from exc
        if authorized is not True:
            raise BridgeContractError("UCIE owner session not authenticated")
        if op == "status":
            return engine.inspect_scope(ROOT, HUB)
        if op == "enroll":
            return engine.enroll(ROOT, HUB, consent=request["consent"])
        if op == "revoke":
            return engine.revoke_scope(ROOT, HUB,
                                       confirmation=request["confirmation"])
        if op == "apply":
            return engine.apply_verified_batch(
                ROOT, HUB, request["bundle"],
                verify_ci_and_sources=engine.verify_github_ci_and_source_blobs,
            )
        raise BridgeContractError("operation not allowlisted")


def classify_admin_deploy_absence(*, search_provider=None) -> dict:
    """A negative UCIE Admin deployment judgment MUST re-search prior Slack.

    Never interpret an unavailable adapter as evidence that PR #78 or the
    owner-installed nine UCIE admin tools did not exist.
    """
    return historical_gate.judge_negative_ucie_admin_claim(
        "ADMIN_DEPLOYMENT_PATH_ABSENT", search_provider=search_provider
    )


def main() -> int:
    """Inert status only: no local trusted bridge enrollment is claimed."""
    prior = classify_admin_deploy_absence()
    print(json.dumps({"schema": SCHEMA,
                      "status": "TRUSTED_UCIE_BRIDGE_INTEGRATION_REQUIRED",
                      "admin_deployment_absence_gate": prior["status"],
                      "admin_deployment_absence_verdict_allowed": False,
                      "operations": sorted(ALLOWED),
                      "host_changed": False,
                      "identity_attested": False,
                      "scheduler_modified": False,
                      "operating_database_modified": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
