"""UCIE-only host Slack reader capability survey. READ ONLY.

Checks only approved UCIE Python code directories, never config/env/token,
user files, other projects, system directories, imports or network calls.
Reports marker categories and bounded counts, not raw code or credentials.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import unittest

ROOTS = (
    ("admin_staged_src", Path(r"D:\UCIE_PREVIEW\UCIE_ADMIN\src\ucie_admin")),
    ("library_mcp_src", Path(r"D:\UCIE_DATA\library_app\private_lib")),
    ("ucie_development_src", Path(r"D:\UCIE\src\ucie_miner")),
)
MAX_DIRS_PER_ROOT = 40
MAX_FILES_PER_ROOT = 180
MAX_FILE_BYTES = 200_000
SKIP_DIRS = frozenset({
    "__pycache__", ".git", ".venv", "venv", "site-packages",
    "node_modules", "dist", "build", "private", "secrets",
})
MARKERS = {
    "slack_sdk_client": ("slack_sdk", "WebClient("),
    "slack_history_api": ("conversations.history", "conversations_history("),
    "history_adapter_contract": ("read_history_page", "UCIESlackHistoryAdapter"),
    "ucie_admin_registration": ("register_ucie_local_admin_tools",),
}


def summarize_python_only(path: Path) -> dict:
    found = {
        "root_exists": path.is_dir() and not path.is_symlink(),
        "directories_scanned": 0,
        "python_files_scanned": 0,
        "scan_truncated": False,
        "slack_sdk_client_files": 0,
        "slack_history_api_files": 0,
        "history_adapter_contract_files": 0,
        "ucie_admin_registration_files": 0,
        "parse_errors": 0,
    }
    if not found["root_exists"]:
        return found
    for folder, subdirs, filenames in os.walk(path, topdown=True, followlinks=False):
        current = Path(folder)
        if current.is_symlink() or not current.resolve().is_relative_to(path.resolve()):
            raise AssertionError("UCIE fixed-root survey escaped its source boundary")
        found["directories_scanned"] += 1
        if found["directories_scanned"] > MAX_DIRS_PER_ROOT:
            found["scan_truncated"] = True
            break
        subdirs[:] = sorted(
            sub for sub in subdirs
            if sub not in SKIP_DIRS and not (current / sub).is_symlink()
        )
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            file = current / name
            if file.is_symlink() or not file.is_file():
                continue
            found["python_files_scanned"] += 1
            if found["python_files_scanned"] > MAX_FILES_PER_ROOT:
                found["scan_truncated"] = True
                break
            if file.stat().st_size > MAX_FILE_BYTES:
                found["scan_truncated"] = True
                continue
            raw = file.read_bytes()
            try:
                source = raw.decode("utf-8-sig")
                ast.parse(source, filename="UCIE_SOURCE_ONLY")
            except (UnicodeError, SyntaxError):
                found["parse_errors"] += 1
                continue
            for marker, needles in MARKERS.items():
                if any(needle in source for needle in needles):
                    found[marker + "_files"] += 1
        if found["scan_truncated"]:
            break
    return found


def observe_ucie_slack_host() -> dict:
    rows = [
        {"label": label, **summarize_python_only(root)}
        for label, root in ROOTS
    ]
    # This survey deliberately cannot infer active credentials, API scopes,
    # remote principal, process-to-source mapping or live Slack capability.
    return {
        "schema": "UCIE_SLACK_HOST_READER_STATIC_PREFLIGHT_V1",
        "status": "SOURCE_CAPABILITY_SURVEY_NOT_LIVE_SLACK",
        "roots": rows,
        "installed_slack_auth_proven": False,
        "host_read_history_page_live_call_proven": False,
        "chatgpt_connected_slack_is_windows_credential": False,
        "code_or_process_modified": False,
        "credentials_or_source_contents_exposed": False,
        "outside_ucie_project_access": False,
    }


class UCIESlackHostReaderReadOnlyTests(unittest.TestCase):
    def test_fixed_ucie_roots_and_no_secrets_or_network(self):
        import inspect
        source = inspect.getsource(summarize_python_only)
        for forbidden in (
            "subprocess", "urllib", "requests.", "httpx", "os.environ",
            "open(", "eval(", "exec(", ".write_text(", ".write_bytes(",
            "D:\\OFFICE_AGENT", "D:\\MYGAME", "credential", "getenv(",
        ):
            with self.subTest(marker=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertTrue(all(str(root).startswith("D:\\UCIE")
                            for _, root in ROOTS))

    def test_owner_host_readonly_capability_classification(self):
        if os.name != "nt" or not Path(r"D:\UCIE").is_dir():
            self.skipTest("UCIE Windows owner host only")
        result = observe_ucie_slack_host()
        print("UCIE_SLACK_HOST_READER_PREFLIGHT=" +
              json.dumps(result, sort_keys=True))
        self.assertEqual(result["schema"],
                         "UCIE_SLACK_HOST_READER_STATIC_PREFLIGHT_V1")
        self.assertFalse(result["installed_slack_auth_proven"])
        self.assertFalse(result["host_read_history_page_live_call_proven"])
        self.assertFalse(result["code_or_process_modified"])
        self.assertFalse(result["credentials_or_source_contents_exposed"])
        self.assertFalse(result["outside_ucie_project_access"])
        self.assertEqual(len(result["roots"]), len(ROOTS))


if __name__ == "__main__":
    unittest.main()
