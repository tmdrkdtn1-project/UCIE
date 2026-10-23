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

    def test_multiple_early_returns_preserve_errors_and_public_success(self):
        original = '''
def search_ucie_evidence(query, category=None, tag=None, top=5):
    if query == "invalid":
        return {"status": "INVALID_QUERY", "results": []}
    if query == "missing":
        return None
    if query == "empty":
        return {"status": "NO_EVIDENCE", "results": []}
    return {"status": "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
            "results": [{"source_key": "python/cpython"}]}
'''
        modified = patch.propose_link(original)
        self.assertEqual(modified.count("UCIE_LIBRARY_BRIDGE_V1"), 1)
        self.assertEqual(modified.count("_ucie_library_bridge(r\"D:"), 3)
        compile(modified, "mcp_stdio_server.py", "exec")
        namespace = {}
        exec(modified, namespace)
        search = namespace["search_ucie_evidence"]
        self.assertEqual(search("invalid"),
                         {"status": "INVALID_QUERY", "results": []})
        self.assertIsNone(search("missing"))
        self.assertEqual(search("empty"),
                         {"status": "NO_EVIDENCE", "results": []})
        # This synthetic environment has no Windows UCIE Stage10/13 index,
        # so optional search returns the original public-success payload.
        success = search("Python")
        self.assertEqual(success["status"],
                         "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY")
        self.assertEqual(success["results"],
                         [{"source_key": "python/cpython"}])

    def test_nested_return_is_not_rewritten(self):
        original = '''
def search_ucie_evidence(query, category=None, tag=None, top=5):
    def internal():
        return "nested"
    if query == "bad":
        return {"status": "INVALID_QUERY", "results": []}
    return {"status": "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
            "results": [], "note": internal()}
'''
        patched = patch.propose_link(original)
        self.assertEqual(patched.count("_ucie_library_bridge(r\"D:"), 2)
        compile(patched, "mcp_stdio_server.py", "exec")

    def test_imported_status_helper_is_allowed_but_signature_must_match(self):
        without_literal = EXAMPLE.replace(
            "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY", "OTHER_STATUS")
        patched = patch.propose_link(without_literal)
        compile(patched, "mcp_stdio_server.py", "exec")
        # Only the actual runtime UCIE public-success status can gain
        # research metadata; all other statuses pass through unchanged.
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
