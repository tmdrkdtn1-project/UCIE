"""UCIE-authored synthetic fixtures, *not* a real-world benchmark."""
import copy
import unittest

from ucie_miner.static_accuracy import (
    AccuracyInputError, measure_python_synthetic_cases,
)

SYNTHETIC = [
    {"case_id": "p-submit", "expected_flag": True, "source": """
import os
def run(path, pool, worker):
    it = os.scandir(path)
    pool.submit(worker, it)
"""},
    {"case_id": "p-map", "expected_flag": True, "source": """
import os
def run(path, pool, worker):
    it = os.scandir(path)
    pool.map(worker, it)
"""},
    {"case_id": "p-thread-args", "expected_flag": True, "source": """
import os, threading
def run(path, worker):
    it = os.scandir(path)
    threading.Thread(target=worker, args=(it,)).start()
"""},
    {"case_id": "p-captured", "expected_flag": True, "source": """
import os
def run(path, pool):
    with os.scandir(path) as it:
        def work():
            return next(it)
        pool.submit(work)
"""},
    {"case_id": "p-annotated", "expected_flag": True, "source": """
import os
def run(path, pool, worker):
    it: object = os.scandir(path)
    pool.submit(worker, it)
"""},
    {"case_id": "p-closure-thread", "expected_flag": True, "source": """
import os, threading
def run(path):
    it = os.scandir(path)
    def worker():
        return next(it)
    threading.Thread(target=worker).start()
"""},
    # Known heuristic blind spot: aliases of os.scandir are not resolved.
    {"case_id": "p-alias-known-fn", "expected_flag": True, "source": """
import os
def run(path, pool, worker):
    alias = os.scandir
    it = alias(path)
    pool.submit(worker, it)
"""},
    {"case_id": "n-sequential", "expected_flag": False, "source": """
import os
def run(path):
    with os.scandir(path) as it:
        return [entry.name for entry in it]
"""},
    {"case_id": "n-rebound", "expected_flag": False, "source": """
import os
def run(path, pool, worker):
    it = os.scandir(path)
    it = list(it)
    pool.submit(worker, it)
"""},
    {"case_id": "n-guarded", "expected_flag": False, "source": """
def run(path, pool, worker):
    with GuardedScandir(path) as guarded:
        pool.submit(worker, guarded)
"""},
    {"case_id": "n-unrelated", "expected_flag": False, "source": """
import os
def first(path):
    it = os.scandir(path)
    return next(it)
def second(pool, worker):
    it = [1, 2]
    pool.submit(worker, it)
"""},
    {"case_id": "n-before-assign", "expected_flag": False, "source": """
import os
def run(path, pool, worker):
    pool.submit(worker, it)
    it = os.scandir(path)
"""},
    {"case_id": "n-list-wrapper", "expected_flag": False, "source": """
import os
def run(path, pool, worker):
    it = list(os.scandir(path))
    pool.submit(worker, it)
"""},
    # Known control-flow blind spot: unreachable branch remains in AST.
    {"case_id": "n-unreachable-known-fp", "expected_flag": False, "source": """
import os
def run(path, pool, worker):
    if False:
        it = os.scandir(path)
        pool.submit(worker, it)
"""},
]


class SyntheticAccuracyTests(unittest.TestCase):
    def test_known_false_positive_and_false_negative_remain_visible(self):
        outcome = measure_python_synthetic_cases(SYNTHETIC)
        self.assertEqual(outcome["fixture_count"], 14)
        self.assertEqual(outcome["positive_controls"], 7)
        self.assertEqual(outcome["negative_controls"], 7)
        self.assertEqual(outcome["true_positive"], 6)
        self.assertEqual(outcome["false_negative"], 1)
        self.assertEqual(outcome["false_positive"], 1)
        self.assertEqual(outcome["true_negative"], 6)
        self.assertEqual(outcome["precision_ppm"], 857142)
        self.assertEqual(outcome["recall_ppm"], 857142)
        self.assertFalse(outcome["real_world_accuracy_verified"])
        self.assertFalse(outcome["independently_validated_labels"])
        self.assertFalse(outcome["production_approved"])
        self.assertEqual(outcome["persistent_writes"], 0)
        self.assertEqual(outcome["rules_promoted"], 0)
        self.assertFalse(any("source" in x for x in outcome["observations"]))

    def test_reproducible_observation_digest(self):
        self.assertEqual(measure_python_synthetic_cases(SYNTHETIC),
                         measure_python_synthetic_cases(copy.deepcopy(SYNTHETIC)))

    def test_reject_malformed_label(self):
        altered = copy.deepcopy(SYNTHETIC)
        altered[0]["expected_flag"] = 1
        with self.assertRaises(AccuracyInputError):
            measure_python_synthetic_cases(altered)

    def test_reject_extra_executable_field(self):
        altered = copy.deepcopy(SYNTHETIC)
        altered[0]["executable_command"] = "no commands accepted"
        with self.assertRaises(AccuracyInputError):
            measure_python_synthetic_cases(altered)

    def test_duplicate_case_rejected(self):
        altered = copy.deepcopy(SYNTHETIC)
        altered[1]["case_id"] = altered[0]["case_id"]
        with self.assertRaises(AccuracyInputError):
            measure_python_synthetic_cases(altered)

    def test_one_class_only_is_not_accuracy(self):
        with self.assertRaises(AccuracyInputError):
            measure_python_synthetic_cases(SYNTHETIC[:2])

    def test_oversized_batch_is_not_inspected(self):
        with self.assertRaises(AccuracyInputError):
            measure_python_synthetic_cases(SYNTHETIC * 3)

    def test_no_source_execution_during_calibration(self):
        cases = copy.deepcopy(SYNTHETIC[:2])
        cases[0]["source"] = ("raise RuntimeError('must stay inert')\n"
                              + cases[0]["source"])
        result = measure_python_synthetic_cases(
            cases + copy.deepcopy([SYNTHETIC[7], SYNTHETIC[8]]))
        self.assertEqual(result["fixture_count"], 4)
        self.assertFalse(result["production_approved"])


if __name__ == "__main__":
    unittest.main()
