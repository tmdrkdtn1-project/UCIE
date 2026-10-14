"""UCIE-only synthetic fixtures: Python AST detection never executes source."""
import hashlib
import textwrap
import unittest

from ucie_miner.static_concurrency import (
    CandidateScanError, inspect_python_scandir_source,
)


def scan(source):
    return inspect_python_scandir_source(textwrap.dedent(source))


class ScandirStaticDetectionTests(unittest.TestCase):
    def test_explicit_executor_argument(self):
        result = scan("""
            import os
            from concurrent.futures import ThreadPoolExecutor
            def worker(it):
                return next(it, None)
            def examine(directory):
                with os.scandir(directory) as it:
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        result = pool.submit(worker, it)
                        return result.result()
        """)
        self.assertEqual(result["finding_count"], 1)
        self.assertEqual(result["findings"][0]["pattern_code"],
                         "PY_SCANDIR_SHARED_ITERATOR_RACE")
        self.assertEqual(result["findings"][0]["thread_boundary"],
                         "EXECUTOR_ARGUMENT")
        self.assertFalse(result["findings"][0]["runtime_bug_reproduced"])
        self.assertFalse(result["parser_executed_supplied_code"])
        self.assertEqual(result["persistent_writes"], 0)

    def test_executor_captured_closure(self):
        result = scan("""
            import os
            def work(path, pool):
                with os.scandir(path) as iterator:
                    def worker():
                        return list(iterator)
                    future = pool.submit(worker)
                    return future.result()
        """)
        self.assertEqual(result["finding_count"], 1)
        self.assertEqual(result["findings"][0]["thread_boundary"],
                         "EXECUTOR_CAPTURED_CLOSURE")

    def test_thread_args(self):
        result = scan("""
            import threading, os
            def f(root, worker):
                raw = os.scandir(root)
                task = threading.Thread(target=worker, args=(raw,))
                task.start()
        """)
        self.assertEqual(result["finding_count"], 1)
        self.assertEqual(result["findings"][0]["thread_boundary"],
                         "THREAD_ARGUMENT")

    def test_thread_captured_closure(self):
        result = scan("""
            import threading, os
            def f(root):
                iterator = os.scandir(root)
                def worker():
                    return next(iterator)
                threading.Thread(target=worker).start()
        """)
        self.assertEqual(result["finding_count"], 1)
        self.assertEqual(result["findings"][0]["thread_boundary"],
                         "THREAD_CAPTURED_CLOSURE")

    def test_ann_assign(self):
        result = scan("""
            import os
            def run(path, pool, consumer):
                iterator: object = os.scandir(path)
                pool.submit(consumer, iterator)
        """)
        self.assertEqual(result["finding_count"], 1)

    def test_executor_map(self):
        result = scan("""
            import os
            def run(path, pool, consumer):
                raw = os.scandir(path)
                pool.map(consumer, raw)
        """)
        self.assertEqual(result["finding_count"], 1)

    def test_single_thread_scandir_not_flagged(self):
        result = scan("""
            import os
            def process(root):
                with os.scandir(root) as it:
                    return [item.name for item in it]
        """)
        self.assertEqual(result["finding_count"], 0)

    def test_guarded_scandir_not_flagged(self):
        result = scan("""
            def process(path, pool, worker):
                with GuardedScandir(path) as guarded:
                    future = pool.submit(worker, guarded)
                    return future.result()
        """)
        self.assertEqual(result["finding_count"], 0)

    def test_nested_separate_scope_not_confused(self):
        result = scan("""
            import os
            def first(root):
                it = os.scandir(root)
                return next(it, None)
            def second(pool, worker):
                it = object()
                pool.submit(worker, it)
        """)
        self.assertEqual(result["finding_count"], 0)

    def test_no_declaration_before_thread_submit(self):
        result = scan("""
            import os
            def f(root, pool, worker):
                pool.submit(worker, raw)
                raw = os.scandir(root)
        """)
        self.assertEqual(result["finding_count"], 0)

    def test_inert_input_cannot_execute(self):
        source = ("import os\n"
                  "__import__('builtins').exec('raise RuntimeError(999)')\n"
                  "def f(directory, pool, worker):\n"
                  "    it = os.scandir(directory)\n"
                  "    pool.submit(worker, it)\n")
        result = inspect_python_scandir_source(source)
        self.assertEqual(result["finding_count"], 1)
        self.assertEqual(result["source_sha256"],
                         hashlib.sha256(source.encode()).hexdigest())
        self.assertFalse(result["parser_executed_supplied_code"])

    def test_syntax_error_fails_closed(self):
        with self.assertRaises(CandidateScanError):
            scan("def broken(:")

    def test_non_string_fails_closed(self):
        with self.assertRaises(CandidateScanError):
            inspect_python_scandir_source(None)

    def test_empty_fails_closed(self):
        with self.assertRaises(CandidateScanError):
            inspect_python_scandir_source("")

    def test_oversized_fails_closed(self):
        with self.assertRaises(CandidateScanError):
            inspect_python_scandir_source("x = 1\n" * 30000)

    def test_rebound_iterator_does_not_trigger_stale_candidate(self):
        result = scan("""
            import os
            def examine(path, pool, worker):
                it = os.scandir(path)
                it = list(it)
                pool.submit(worker, it)
        """)
        self.assertEqual(result["finding_count"], 0)

    def test_reassignment_back_to_raw_scandir_is_detected(self):
        result = scan("""
            import os
            def examine(path, pool, worker):
                it = object()
                it = os.scandir(path)
                pool.submit(worker, it)
        """)
        self.assertEqual(result["finding_count"], 1)

    def test_only_submit_before_rebinding_is_flagged(self):
        result = scan("""
            import os
            def examine(path, pool, worker):
                it = os.scandir(path)
                pool.submit(worker, it)
                it = list(it)
                pool.submit(worker, it)
        """)
        self.assertEqual(result["finding_count"], 1)

    def test_loop_target_rebind_clears_raw_iterator(self):
        result = scan("""
            import os
            def f(path, pool, worker):
                it = os.scandir(path)
                for it in [1, 2]:
                    pool.submit(worker, it)
        """)
        self.assertEqual(result["finding_count"], 0)

    def test_deterministic_findings(self):
        s = """
            import os
            def f(root, pool, worker):
                it = os.scandir(root)
                pool.submit(worker, it)
        """
        self.assertEqual(scan(s), scan(s))

    def test_no_auto_rulepack_or_signing(self):
        result = scan("""
            import os
            def f(root, pool, worker):
                raw = os.scandir(root)
                pool.submit(worker, raw)
        """)
        self.assertEqual(result["approved_rules"], 0)
        self.assertFalse(result["production_approved"])
        self.assertEqual(result["confidence"], "HUMAN_REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
