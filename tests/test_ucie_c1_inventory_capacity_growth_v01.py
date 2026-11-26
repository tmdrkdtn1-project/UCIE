"""C1 bounded source inventory capacity after UCIE V2 first-party growth."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from ucie_miner import customer_runtime_closure_v01 as c1


class C1CapacityGrowthTests(TestCase):
    def fixture(self, count):
        temp = TemporaryDirectory(prefix="UCIE_C1_SOURCE_CAP_")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "UCIE"
        for package in c1.PACKAGES:
            folder = root / "src" / package
            folder.mkdir(parents=True)
            (folder / "__init__.py").write_text("pass\n", encoding="utf-8")
        (root / ".git").mkdir()
        for number in range(count - len(c1.PACKAGES)):
            path = root / "src" / "ucie_miner" / ("m%04d.py" % number)
            path.write_text("VALUE = 1\n", encoding="utf-8")
        return root

    def test_exact_320_first_party_modules_allowed(self):
        root = self.fixture(320)
        source = c1._src_index(root)
        self.assertEqual(len(source), c1.MAX_SOURCE_FILES)
        self.assertEqual(c1.MAX_SOURCE_FILES, 320)

    def test_321_first_party_modules_still_fail_closed(self):
        root = self.fixture(321)
        with self.assertRaisesRegex(c1.ClosurePreviewError,
                                    "too many/duplicate modules"):
            c1._src_index(root)

    def test_reject_symlink_even_under_new_limit(self):
        root = self.fixture(6)
        path = root / "src" / "ucie_miner" / "m0000.py"
        path.unlink()
        try:
            path.symlink_to(root / "src" / "ucie_public" / "__init__.py")
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaises(c1.ClosurePreviewError):
            c1._src_index(root)

    def test_other_staging_caps_unchanged(self):
        self.assertEqual(c1.MAX_SOURCE_BYTES, 8_000_000)
        self.assertEqual(c1.MAX_FILE_BYTES, 260_000)
        self.assertEqual(c1.MAX_STAGE_BYTES, 11_000_000)
