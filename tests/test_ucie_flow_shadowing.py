"""Inert, UCIE-authored flow/alias regression controls, not real-world proof."""
import textwrap
import unittest

from ucie_miner.static_concurrency import inspect_python_scandir_source
from ucie_miner.static_accuracy import measure_python_synthetic_cases
from test_ucie_static_accuracy import SYNTHETIC


def scan(s):
    return inspect_python_scandir_source(textwrap.dedent(s))


CONTROLS = [
    {"case_id": "flow-module-import", "expected_flag": True, "source": """
from os import scandir as scan
def run(path, pool, work):
    iterator = scan(path)
    pool.submit(work, iterator)
"""},
    {"case_id": "flow-module-alias", "expected_flag": True, "source": """
import os as filesystem
def run(path, pool, work):
    iterator = filesystem.scandir(path)
    pool.submit(work, iterator)
"""},
    {"case_id": "flow-iterator-copy", "expected_flag": True, "source": """
import os
def run(path, pool, work):
    iterator = os.scandir(path)
    copied = iterator
    pool.submit(work, copied)
"""},
    {"case_id": "flow-two-step-function-alias", "expected_flag": True, "source": """
import os
def run(path, pool, work):
    first = os.scandir
    second = first
    iterator = second(path)
    pool.submit(work, iterator)
"""},
    {"case_id": "flow-shadowed-parameter", "expected_flag": False, "source": """
def run(os, path, pool, work):
    iterator = os.scandir(path)
    pool.submit(work, iterator)
"""},
    {"case_id": "flow-module-symbol-rebound", "expected_flag": False, "source": """
import os
def run(path, pool, work):
    os = object()
    iterator = os.scandir(path)
    pool.submit(work, iterator)
"""},
    {"case_id": "flow-late-func-alias", "expected_flag": False, "source": """
import os
def run(path, pool, work):
    iterator = future(path)
    future = os.scandir
    pool.submit(work, iterator)
"""},
    {"case_id": "flow-cleared-copied-iterator", "expected_flag": False, "source": """
import os
def run(path, pool, work):
    iterator = os.scandir(path)
    copied = iterator
    copied = list(copied)
    pool.submit(work, copied)
"""},
]


class PythonFlowShadowingTests(unittest.TestCase):
    def test_expanded_independent_synthetic_controls(self):
        for item in CONTROLS:
            with self.subTest(case=item["case_id"]):
                observed = scan(item["source"])
                self.assertEqual(observed["finding_count"] > 0,
                                 item["expected_flag"])
                self.assertFalse(observed["production_approved"])
        report = measure_python_synthetic_cases(SYNTHETIC + CONTROLS)
        self.assertEqual(report["fixture_count"], 22)
        self.assertEqual(report["true_positive"], 11)
        self.assertEqual(report["true_negative"], 11)
        self.assertEqual(report["false_positive"], 0)
        self.assertEqual(report["false_negative"], 0)
        self.assertFalse(report["real_world_accuracy_verified"])

    def test_late_alias_does_not_backdate_findings(self):
        out = scan("""
            import os
            def run(path, pool, work):
                iterator = future(path)
                pool.submit(work, iterator)
                future = os.scandir
        """)
        self.assertEqual(out["finding_count"], 0)

    def test_local_alias_to_other_function_is_not_reported(self):
        out = scan("""
            import os
            def run(path, pool, work):
                alias = os.scandir
                alias = list
                iterator = alias(path)
                pool.submit(work, iterator)
        """)
        self.assertEqual(out["finding_count"], 0)

    def test_no_evaluation_of_untrusted_source(self):
        code = ("raise RuntimeError('SHOULD NEVER EXECUTE')\n"
                "import os as fs\n"
                "def run(path, pool, work):\n"
                "    it = fs.scandir(path)\n"
                "    pool.submit(work, it)\n")
        out = inspect_python_scandir_source(code)
        self.assertEqual(out["finding_count"], 1)
        self.assertFalse(out["parser_executed_supplied_code"])
        self.assertEqual(out["source_files_read"], 0)
        self.assertEqual(out["persistent_writes"], 0)


if __name__ == "__main__":
    unittest.main()
