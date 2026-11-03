"""UCIE-only live MCP wiring metadata inventory. READ-ONLY, no private code output.

Parses only known UCIE server files with Python AST. Never imports/executes
the server, enumerates other projects, reads profiles/tokens, or alters runtime.
"""
from __future__ import annotations

import ast
from pathlib import Path
import json
import os
import unittest

PROFILE=Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")
SERVER_ROOT=Path(r"D:\UCIE_DATA\library_app\private_lib")
SERVER_FILES=("mcp_stdio_server.py","mcp_readonly_facade.py")
OWNER_NAMES=("ucie_owner_scope_status","ucie_owner_scope_enroll",
             "ucie_owner_scope_revoke","ucie_owner_scope_apply")
HOOK="register_ucie_owner_scope_tools"


def inventory(path: Path) -> dict:
    result={
        "file_label":path.name,
        "exists":False,"ast_parsed":False,
        "fastmcp_mentions":False,
        "existing_admin_symbol":False,
        "ucie_scoped_hook_present":False,
        "owner_four_tool_names_present":False,
        "auth_context_symbol_present":False,
        "static_owner_marker_symbol_present":False,
        "auth_candidate_function_names":[],
        "ucie_registration_function_names":[],
        "ucie_owner_module_imported":False,
    }
    if not path.is_file() or path.is_symlink():
        return result
    if path.stat().st_size>250_000:
        raise AssertionError("UCIE server source too large for bounded probe")
    source=path.read_bytes().decode("utf-8-sig")
    tree=ast.parse(source, filename="UCIE_SERVER_METADATA")
    result["exists"]=True
    result["ast_parsed"]=True
    # No source text, tokens, names outside approved prefixes, or arbitrary
    # import/module/file contents are printed.
    result["fastmcp_mentions"]=("FastMCP" in source)
    result["existing_admin_symbol"]=("ucie_admin_capabilities" in source)
    result["ucie_scoped_hook_present"]=HOOK in source
    result["owner_four_tool_names_present"]=all(t in source for t in OWNER_NAMES)
    result["auth_context_symbol_present"]=any(
       x in source for x in ("request_context","get_access_token",
          "get_current_user","authenticated_session_action","auth_context")
    )
    result["static_owner_marker_symbol_present"]="UCIE_MCP_OWNER_APPROVAL" in source
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            module=(node.module or "") if isinstance(node,ast.ImportFrom) else ""
            full=[module] if module else []
            if isinstance(node,ast.Import):
                full=[a.name for a in node.names]
            if any("owner_scoped" in m for m in full):
                result["ucie_owner_module_imported"]=True
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            if ("auth" in node.name.lower() or "session" in node.name.lower()) and \
                len(result["auth_candidate_function_names"])<12:
                # Identifiers only; no function bodies or signatures.
                if node.name.startswith(("ucie_","_ucie_","authorize","verify","assert","_assert")):
                    result["auth_candidate_function_names"].append(node.name)
            if node.name.startswith(("register_ucie","ucie_admin","_ucie_admin")) and \
                len(result["ucie_registration_function_names"])<15:
                result["ucie_registration_function_names"].append(node.name)
    return result


class UCIEOnlyLiveServerHookInventory(unittest.TestCase):
    def test_static_probe_readonly_contract(self):
        import inspect
        body=inspect.getsource(inventory)
        for forbidden in ("subprocess.run","os.system","exec(","eval(","importlib",
                          ".write_text(", ".write_bytes(","unlink(","chmod("):
            self.assertNotIn(forbidden,body)

    def test_live_owner_host_static_inventory_without_code_disclosure(self):
        if os.name!="nt" or not PROFILE.is_file():
            self.skipTest("UCIE owner Windows host only")
        rows=[inventory(SERVER_ROOT/name) for name in SERVER_FILES]
        self.assertTrue(rows[0]["exists"])
        self.assertTrue(rows[0]["ast_parsed"])
        self.assertFalse(any(t.endswith(".json") for t in SERVER_FILES))
        output={
            "schema":"UCIE_LIVE_MCP_HOOK_INVENTORY_READONLY_V1",
            "status":"WIRING_METADATA_ONLY_NOT_AUTHORIZATION",
            "sources":rows,
            "remote_owner_session_verified":False,
            "new_mcp_tools_registered_by_this_test":False,
            "new_service_or_tunnel_created":False,
            "task_process_acl_or_grant_changed":False,
            "credentials_or_raw_source_exposed":False,
        }
        print("UCIE_MCP_HOOK_STATIC_INVENTORY="+json.dumps(output,sort_keys=True))
        self.assertFalse(output["remote_owner_session_verified"])
        self.assertFalse(output["task_process_acl_or_grant_changed"])


if __name__=="__main__":
    unittest.main()
