"""UCIE-only administrator MCP provider mapping: host-observed read-only evidence.

Inspects only bounded Python source metadata under the explicit UCIE library
app root. No private credentials/config, raw source, environment, network,
process control, or other-project access. This test cannot grant owner rights.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import unittest

UCIE_LIBRARY_APP = Path(r"D:\UCIE_DATA\library_app")
UCIE_SEARCH_MCP = UCIE_LIBRARY_APP / "private_lib" / "mcp_stdio_server.py"
LIMIT_DIRECTORIES = 100
LIMIT_PY_FILES = 400
MAX_BYTES_PER_FILE = 200_000
LOOKUPS = ("ucie_admin_capabilities", "ucie_admin_write_text",
           "ucie_admin_test_one_file", "register_ucie_owner_scope_tools")


def scan_ucie_host():
    result = {
        "schema": "UCIE_ADMIN_PROVIDER_HOST_MAPPING_READONLY_V1",
        "status": "UCIE_ONLY_LOCAL_SOURCE_SURVEY",
        "library_app_exists": UCIE_LIBRARY_APP.is_dir(),
        "search_mcp_exists": UCIE_SEARCH_MCP.is_file(),
        "scanned_directories": 0,
        "scanned_python_files": 0,
        "scan_truncated": False,
        "found_admin_source_files": [],
        "owner_hook_source_files": [],
        "known_search_source_has_admin_names": False,
        "owner_mcp_registration_proven": False,
        "remote_owner_identity_proven": False,
        "no_source_or_secret_exposed": True,
        "changed_files_or_processes": False,
    }
    if not UCIE_LIBRARY_APP.is_dir() or UCIE_LIBRARY_APP.is_symlink():
        return result
    root = UCIE_LIBRARY_APP.resolve()
    known_file = UCIE_SEARCH_MCP.resolve()
    if known_file.is_file() and not UCIE_SEARCH_MCP.is_symlink():
        known_raw = known_file.read_bytes()
        if len(known_raw) <= MAX_BYTES_PER_FILE:
            result["known_search_source_has_admin_names"] = (
                LOOKUPS[0].encode() in known_raw
                or LOOKUPS[1].encode() in known_raw
            )

    # Refuse traversal outside the exact approved UCIE library-app root.
    def on_error(err):
        raise AssertionError("UCIE bounded source inventory unavailable") from err

    stop = False
    for folder, dirs, names in os.walk(root, topdown=True, followlinks=False,
                                      onerror=on_error):
        p = Path(folder)
        if not p.resolve().is_relative_to(root):
            raise AssertionError("UCIE source inventory escaped approved root")
        result["scanned_directories"] += 1
        if result["scanned_directories"] > LIMIT_DIRECTORIES:
            result["scan_truncated"] = True
            break
        dirs[:] = sorted(d for d in dirs
                         if d not in {"__pycache__", ".git", ".venv", "node_modules",
                                      "site-packages", "venv", "build", "dist"}
                         and not (p / d).is_symlink())
        for fname in sorted(names):
            if not fname.endswith(".py"):
                continue
            result["scanned_python_files"] += 1
            if result["scanned_python_files"] > LIMIT_PY_FILES:
                result["scan_truncated"] = True
                stop = True
                break
            file = p / fname
            if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_BYTES_PER_FILE:
                continue
            raw = file.read_bytes()
            if not any(word.encode() in raw for word in LOOKUPS):
                continue
            try:
                ast.parse(raw.decode("utf-8-sig"), filename="UCIE_PY_META")
            except (UnicodeError, SyntaxError):
                continue
            rel = file.relative_to(root).as_posix()
            if any(word.encode() in raw for word in LOOKUPS[:3]):
                result["found_admin_source_files"].append(rel)
            if LOOKUPS[3].encode() in raw:
                result["owner_hook_source_files"].append(rel)
        if stop:
            break
    result["found_admin_source_files"] = sorted(set(result["found_admin_source_files"]))[:25]
    result["owner_hook_source_files"] = sorted(set(result["owner_hook_source_files"]))[:25]
    # Source text presence is not proof of active tool registration.
    return result


class UCIEAdminProviderMappingReadOnlyTests(unittest.TestCase):
    def test_no_mutating_capabilities_in_probe(self):
        import inspect
        code = inspect.getsource(scan_ucie_host)
        for prohibited in ("subprocess", "requests.", "urllib.", "os.system(",
                           "Popen(", ".write_text(", ".write_bytes(", ".unlink(",
                           ".chmod(", "shutil.rmtree(", "os.environ"):
            self.assertNotIn(prohibited, code)
        self.assertTrue(str(UCIE_LIBRARY_APP).startswith("D:\\UCIE_DATA\\"))

    def test_ucie_only_windows_host_provider_map(self):
        if os.name != "nt" or not UCIE_SEARCH_MCP.is_file():
            self.skipTest("Only the UCIE owner Windows host has this server root")
        result = scan_ucie_host()
        print("UCIE_ADMIN_PROVIDER_MAP=" + json.dumps(result, sort_keys=True))
        self.assertEqual(result["schema"], "UCIE_ADMIN_PROVIDER_HOST_MAPPING_READONLY_V1")
        self.assertTrue(result["no_source_or_secret_exposed"])
        self.assertFalse(result["changed_files_or_processes"])
        self.assertFalse(result["remote_owner_identity_proven"])
        self.assertFalse(result["owner_mcp_registration_proven"])


if __name__ == "__main__":
    unittest.main()
