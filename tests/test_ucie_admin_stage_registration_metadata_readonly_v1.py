"""Source-only UCIE Admin staging registration identity, no source disclosure.

Never mutates live MCP server, restarts C40, reads configs/tokens, or scans
any path outside the known UCIE Admin stage. Output hashes and bounded tool
registration names only, preserving historical PR78 owner/deploy evidence.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import unittest

ADMIN = Path(r"D:\UCIE_PREVIEW\UCIE_ADMIN\src\ucie_admin")
REG = ADMIN / "mcp_registration.py"
KNOWN = {
    "ucie_admin_capabilities", "ucie_admin_list_files", "ucie_admin_read_text",
    "ucie_admin_search_text", "ucie_admin_create_directory",
    "ucie_admin_write_text", "ucie_admin_replace_text",
    "ucie_admin_git_status", "ucie_admin_test_one_file",
}
PR78_SHA = "8516baa69e768f2589d5df305200ebcd99b76e0d"
MAX_BYTES = 20000


def static_registration_record() -> dict:
    raw = REG.read_bytes()
    if not raw or len(raw) > MAX_BYTES:
        raise AssertionError("UCIE_ADMIN_REGISTRATION_BOUNDED_SOURCE_INVALID")
    if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
           for p in (REG, *REG.parents)):
        raise AssertionError("UCIE_ADMIN_REPARSE_PATH_DENIED")
    source = raw.decode("utf-8-sig")
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    registration = [
        node for node in functions if node.name == "register_ucie_local_admin_tools"
    ]
    tools = set()
    decorator_count = 0
    if len(registration) == 1:
        for sub in registration[0].body:
            if not isinstance(sub, ast.FunctionDef):
                continue
            for dec in sub.decorator_list:
                if (isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Attribute)
                    and dec.func.attr == "tool"):
                    decorator_count += 1
                    for k in dec.keywords:
                        if (k.arg == "name" and isinstance(k.value, ast.Constant)
                            and isinstance(k.value.value, str)):
                            tools.add(k.value.value)
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    return {
        "schema": "UCIE_ADMIN_STAGE_REGISTRATION_STATIC_METADATA_V1",
        "exists": True,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": blob,
        "matches_original_pr78": blob == PR78_SHA,
        "bytes": len(raw),
        "registration_function_count": len(registration),
        "top_level_function_count": len(functions),
        "registered_tool_decorators": decorator_count,
        "exact_nine_admin_names_preserved": KNOWN <= tools,
        "extra_nonadmin_tool_count": len(tools - KNOWN),
        "known_slack_readonly_tool_present":
            "ucie_slack_history_verify_readonly" in tools,
        "slack_registration_marker_present":
            "# UCIE_SLACK_READONLY_ADMIN_MCP_V1" in source,
        "raw_source_or_secret_exposed": False,
        "c40_or_source_mutated": False,
    }


class UCIEAdminStageMetaReadOnly(unittest.TestCase):
    def test_real_owner_stage_static_metadata(self):
        if os.name != "nt" or not REG.is_file():
            self.skipTest("not UCIE owner Windows admin staging root")
        record = static_registration_record()
        print("UCIE_ADMIN_STAGE_METADATA=" + json.dumps(record, sort_keys=True))
        self.assertEqual(record["registration_function_count"], 1)
        self.assertTrue(record["raw_source_or_secret_exposed"] is False)
        self.assertTrue(record["c40_or_source_mutated"] is False)

    def test_stage_is_not_a_new_mcp_registration(self):
        self.assertTrue(str(REG).startswith(r"D:\UCIE_PREVIEW\UCIE_ADMIN"))
        self.assertTrue(KNOWN)
        self.assertNotIn("ucie_slack_history_verify_readonly", KNOWN)


if __name__ == "__main__":
    unittest.main()
