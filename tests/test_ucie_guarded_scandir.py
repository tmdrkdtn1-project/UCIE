"""Synthetic, disposable, first-party tests for the scandir ownership guard."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.guarded_scandir import GuardedScandir


class GuardedScandirTests(unittest.TestCase):
    def test_concurrent_next_returns_every_entry_exactly_once(self):
        for _ in range(8):
            with tempfile.TemporaryDirectory(prefix="ucie-guard-") as directory:
                expected = [f"entry{i:03d}" for i in range(100)]
                for name in expected:
                    Path(directory, name).touch()
                barrier = threading.Barrier(4)
                def worker(it):
                    barrier.wait(timeout=4)
                    return [e.name for e in it]
                with GuardedScandir(directory) as it:
                    with ThreadPoolExecutor(max_workers=4) as pool:
                        tasks = [pool.submit(worker, it) for _ in range(4)]
                        found = [name for future in tasks for name in future.result(timeout=8)]
                    self.assertEqual(sorted(found), expected)
                    with self.assertRaises(StopIteration):
                        next(it)

    def test_close_concurrent_with_next_is_serialized(self):
        for _ in range(8):
            with tempfile.TemporaryDirectory(prefix="ucie-guard-") as directory:
                for n in range(80):
                    Path(directory, f"n{n}").touch()
                it = GuardedScandir(directory)
                barrier = threading.Barrier(5)
                def reader():
                    barrier.wait(timeout=4)
                    return sum(1 for _ in it)
                def closer():
                    barrier.wait(timeout=4)
                    it.close()
                try:
                    with ThreadPoolExecutor(max_workers=5) as pool:
                        tasks = [pool.submit(reader) for _ in range(3)]
                        tasks += [pool.submit(closer) for _ in range(2)]
                        for future in tasks:
                            future.result(timeout=8)
                finally:
                    it.close()
                with self.assertRaises(StopIteration):
                    next(it)

    def test_idempotent_close_and_missing_directory(self):
        with tempfile.TemporaryDirectory(prefix="ucie-guard-") as directory:
            with GuardedScandir(directory) as it:
                it.close()
                it.close()
                with self.assertRaises(StopIteration):
                    next(it)
            with self.assertRaises(OSError):
                GuardedScandir(str(Path(directory) / "absent"))


if __name__ == "__main__":
    unittest.main()
