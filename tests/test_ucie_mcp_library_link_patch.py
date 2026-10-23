"""Focused synthetic guardrails for one-time UCIE MCP handler patch preparation."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = (Path(__file__).resolve().parents[1]
          / "scripts" / "prepare_ucie_mcp_library_link.py")
spec = importlib.util.spec_from_file_location(
    "ucie_mcp_handler_link_testonly", SCRIPT)
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)

EXAMPLE = '''
import json

def search_ucie_evidence(query, category=None, tag=None, top=5):
    return json.dumps({
        "status": "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
        "results": [],
        "limitations": "first-party public metadata only",
    })
'''


class OneTimeMcpLibraryLinkTests(unittest.TestCase):
    def test_patches_one_handler_and_preserves_original_return(self):
        result = patch.propose_link(EXAMPLE)
        self.assertIn("UCIE_LIBRARY_BRIDGE_V1", result)
        self.assertIn("extend_existing_ucie_mcp_wire_response", result)
        self.assertIn("json.dumps({", result)
        self.assertIn('"results": []', result)
        compile(result, "mcp_stdio_server.py", "exec")
        self.assertEqual(EXAMPLE.count("UCIE_LIBRARY_BRIDGE_V1"), 0)
        self.assertEqual(result.count("UCIE_LIBRARY_BRIDGE_V1"), 1)
        with self.assertRaises(patch.LinkError):
            patch.propose_link(result)

    def test_existing_handler_with_ambiguous_returns_never_patched(self):
        original = '''
def search_ucie_evidence(query, category=None, tag=None, top=5):
    if query:
        return {"status":"UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
                "results":[]}
    return {"status":"UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
            "results":[]}
'''
        with self.assertRaises(patch.LinkError):
            patch.propose_link(original)

    def test_missing_status_or_different_parameters_fails_closed(self):
        without_status = EXAMPLE.replace(
            "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY", "OTHER_STATUS")
        with self.assertRaises(patch.LinkError):
            patch.propose_link(without_status)
        with self.assertRaises(patch.LinkError):
            patch.propose_link(
                EXAMPLE.replace("query, category=None, tag=None, top=5",
                                "query, category=None"))

    def test_duplicate_handler_fails_closed(self):
        with self.assertRaises(patch.LinkError):
            patch.propose_link(EXAMPLE + EXAMPLE)

    def test_rejects_inline_return_source(self):
        source = '''
def search_ucie_evidence(query, category=None, tag=None, top=5):
    if query: return {"status":"UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
                      "results":[]}
'''
        with self.assertRaises(patch.LinkError):
            patch.propose_link(source)

    def test_nested_async_handler_syntax_preserved(self):
        source = '''
def app():
    async def search_ucie_evidence(query, category=None, tag=None, top=5):
        return {"status": "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
                "results": []}
    return search_ucie_evidence
'''
        patched = patch.propose_link(source)
        compile(patched, "mcp_stdio_server.py", "exec")
        self.assertIn("async def search_ucie_evidence", patched)


if __name__ == "__main__":
    unittest.main()
