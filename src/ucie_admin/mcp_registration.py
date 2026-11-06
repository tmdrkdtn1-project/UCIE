"""Attach UCIE-only file maintenance capabilities to an existing FastMCP app.

No server or plugin is created by importing this module. Explicit
registration is required from the existing UCIE MCP server startup, under
its currently authenticated UCIE-only tunnel and operator configuration.
"""
from __future__ import annotations

from .local_write_bridge import UCIEFileBridge, BridgeError


def register_ucie_local_admin_tools(fastmcp, bridge: UCIEFileBridge | None = None):
    """Register bounded admin tools once. Call only inside trusted UCIE MCP."""
    if bridge is None:
        bridge = UCIEFileBridge.for_ucie_windows_host()

    @fastmcp.tool(name="ucie_admin_capabilities")
    def ucie_admin_capabilities() -> dict:
        """Describe UCIE-only code roots, limits and available operations."""
        return {
            "status": "UCIE_LOCAL_ADMIN_BRIDGE_READY",
            "scopes": ["repo", "mcp_code"],
            "max_read_bytes": 200000,
            "max_write_bytes": 256000,
            "file_writes_use_expected_sha256": True,
            "backup_and_metadata_audit": True,
            "other_projects_access": False,
            "arbitrary_shell": False,
            "automatic_service_restart": False,
            "automatic_git_push": False,
        }

    @fastmcp.tool(name="ucie_admin_list_files")
    def ucie_admin_list_files(scope: str, directory: str = "src",
                              max_items: int = 50) -> dict:
        """List bounded UCIE source directories in repo or mcp_code scope."""
        return bridge.list_directory(scope, directory, max_items)

    @fastmcp.tool(name="ucie_admin_read_text")
    def ucie_admin_read_text(scope: str, path: str) -> dict:
        """Read UTF-8 source/document text from one UCIE-only path."""
        return bridge.read_text(scope, path)

    @fastmcp.tool(name="ucie_admin_search_text")
    def ucie_admin_search_text(scope: str, directory: str,
                                literal: str, max_matches: int = 20) -> dict:
        """Search a bounded UCIE directory for literal text; no regex or shell."""
        return bridge.search_text(scope, directory, literal, max_matches)

    @fastmcp.tool(name="ucie_admin_create_directory")
    def ucie_admin_create_directory(scope: str, directory: str) -> dict:
        """Make one UCIE source directory, never outside the configured roots."""
        return bridge.create_directory(scope, directory)

    @fastmcp.tool(name="ucie_admin_write_text")
    def ucie_admin_write_text(scope: str, path: str, content: str,
                               expected_sha256: str,
                               preview: bool = True) -> dict:
        """Preview or atomically write one UCIE UTF-8 file with SHA lease.

        Existing file: pass the SHA256 returned by ucie_admin_read_text.
        New file: pass expected_sha256='ABSENT'. To actually write, set
        preview=False. Before replacing a file, back up its old content.
        """
        return bridge.write_text(scope, path, content, expected_sha256,
                                 preview=preview)

    @fastmcp.tool(name="ucie_admin_replace_text")
    def ucie_admin_replace_text(scope: str, path: str,
                                 old_text: str, new_text: str,
                                 expected_sha256: str,
                                 preview: bool = True) -> dict:
        """Preview/replace exactly one text occurrence; SHA lease and backup."""
        return bridge.replace_once(scope, path, old_text, new_text,
                                   expected_sha256, preview=preview)

    @fastmcp.tool(name="ucie_admin_git_status")
    def ucie_admin_git_status() -> dict:
        """Observe only UCIE repository Git working tree status, no mutation."""
        return bridge.git_status()

    @fastmcp.tool(name="ucie_admin_test_one_file")
    def ucie_admin_test_one_file(filename: str, approved: bool = False) -> dict:
        """Run exactly one UCIE unittest file, only with explicit approval."""
        return bridge.run_one_test_file(filename, approved=approved)

    return {
        "status": "UCIE_ADMIN_TOOLS_REGISTERED_WITH_EXISTING_FASTMCP_INSTANCE",
        "tool_count": 9,
        "write_scopes": ["repo", "mcp_code"],
        "server_restarted": False,
        "additional_tunnel_installed": False,
    }
