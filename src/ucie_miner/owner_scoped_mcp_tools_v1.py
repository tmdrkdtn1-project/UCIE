"""Register four narrow UCIE owner-scoped MCP handlers on an EXISTING server.

No runtime/server/tunnel created by import. The existing UCIE owner-authenticated
server must construct the boundary with its own authenticated-session callback.
A username, static marker, secret from an MCP argument, or blanket True is NOT
a trusted session callback. The server host remains responsible for proving it.
"""
from __future__ import annotations

from .owner_scoped_bridge_v1 import (
    SCHEMA, UCIEOwnerBridgeBoundary, BridgeContractError,
)


def register_ucie_owner_scope_tools(fastmcp, *, boundary: UCIEOwnerBridgeBoundary) -> dict:
    """Explicit integration only, never installed just because module exists.

    The boundary is created by the trusted UCIE host; cannot come from caller
    payloads. Existing search / nine admin tool registrations are untouched.
    """
    if type(boundary) is not UCIEOwnerBridgeBoundary:
        raise BridgeContractError("trusted UCIE owner boundary required")
    if fastmcp is None or not callable(getattr(fastmcp, "tool", None)):
        raise BridgeContractError("existing UCIE FastMCP tool decorator required")

    @fastmcp.tool(name="ucie_owner_scope_status")
    def ucie_owner_scope_status() -> dict:
        """Read-only 14-day UCIE development grant status. Not an identity proof."""
        return boundary.handle({"schema": SCHEMA, "operation": "status"})

    @fastmcp.tool(name="ucie_owner_scope_enroll")
    def ucie_owner_scope_enroll(consent: str) -> dict:
        """Record exact bounded UCIE owner consent; only authenticated session."""
        return boundary.handle({"schema": SCHEMA, "operation": "enroll",
                                "consent": consent})

    @fastmcp.tool(name="ucie_owner_scope_revoke")
    def ucie_owner_scope_revoke(confirmation: str) -> dict:
        """Cancel UCIE scoped consent without touching other runtime permissions."""
        return boundary.handle({"schema": SCHEMA, "operation": "revoke",
                                "confirmation": confirmation})

    @fastmcp.tool(name="ucie_owner_scope_apply")
    def ucie_owner_scope_apply(bundle: dict) -> dict:
        """Apply ONLY exact-GitHub-CI verified bounded UCIE Python source batch."""
        return boundary.handle({"schema": SCHEMA, "operation": "apply",
                                "bundle": bundle})

    return {
        "status": "UCIE_OWNER_SCOPED_HANDLERS_REGISTERED_ON_PROVIDED_SERVER_ONLY",
        "scope": "UCIE_ONLY",
        "tool_names": ["ucie_owner_scope_status", "ucie_owner_scope_enroll",
                       "ucie_owner_scope_revoke", "ucie_owner_scope_apply"],
        "tool_count": 4,
        "new_server": False,
        "new_tunnel": False,
        "host_identity_attested_by_registration": False,
        "owner_grant_created": False,
        "scheduler_changed": False,
        "operating_database_modified": False,
    }
