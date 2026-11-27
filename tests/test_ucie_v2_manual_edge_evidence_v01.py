"""Offline regression: manual UCIE Edge evidence never implies browser QA PASS."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import struct
import unittest
import zlib

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ucie_v2_manual_edge_evidence_v01.py"
spec = spec_from_file_location("ucie_v2_manual_edge_evidence_v01", SCRIPT)
assert spec and spec.loader
probe = module_from_spec(spec)
spec.loader.exec_module(probe)


def png_header(width=320, height=900):
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunk = struct.pack(">I", 13) + b"IHDR" + ihdr
    chunk += struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))
    end = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND"))
    return probe.PNG_SIGNATURE + chunk + end


class ManualEdgeEvidenceTests(unittest.TestCase):
    def test_partial_screenshot_is_inventory_only(self):
        with TemporaryDirectory(prefix="UCIE_MANUAL_TEST_") as tmp:
            base = Path(tmp)
            images = base / "screenshots"
            images.mkdir()
            (images / "ucie_320.png").write_bytes(png_header())
            output = base / "receipt"
            result = probe.inventory_manual_screenshots(images, output)
            self.assertEqual(result["captured_widths_count"], 1)
            self.assertFalse(result["all_widths_present"])
            self.assertEqual(result["visual_qa"], "PENDING")
            self.assertEqual(result["keyboard_focus"], "NOT_VERIFIED")
            self.assertFalse(result["product_release_approved"])
            self.assertTrue((output / probe.RECEIPT_NAME).is_file())
            loaded = json.loads((output / probe.RECEIPT_NAME).read_text())
            self.assertEqual(loaded["receipt_sha256"], result["receipt_sha256"])
            self.assertFalse(result["images"][0]["actual_viewport_verified"])

    def test_all_five_are_still_not_visual_pass(self):
        with TemporaryDirectory(prefix="UCIE_MANUAL_TEST_") as tmp:
            base = Path(tmp)
            images = base / "screenshots"
            images.mkdir()
            for width in probe.WIDTHS:
                (images / f"ucie_{width}.png").write_bytes(png_header(width))
            result = probe.inventory_manual_screenshots(images, base / "receipt")
            self.assertTrue(result["all_widths_present"])
            self.assertEqual(result["visual_qa"], "PENDING")
            self.assertEqual(result["independent_qa"], "PENDING")

    def test_reject_invalid_png_crc_and_no_allowed_images(self):
        with TemporaryDirectory(prefix="UCIE_MANUAL_TEST_") as tmp:
            base = Path(tmp)
            images = base / "screenshots"
            images.mkdir()
            with self.assertRaisesRegex(
                probe.ManualEdgeEvidenceError, "NO_ALLOWED"):
                probe.inventory_manual_screenshots(images, base / "receipt")
            raw = bytearray(png_header())
            raw[29] ^= 0xFF
            (images / "ucie_390.png").write_bytes(raw)
            with self.assertRaisesRegex(
                probe.ManualEdgeEvidenceError, "CRC_MISMATCH"):
                probe.inventory_manual_screenshots(images, base / "receipt")

    def test_no_overwrite_existing_receipt(self):
        with TemporaryDirectory(prefix="UCIE_MANUAL_TEST_") as tmp:
            base = Path(tmp)
            images = base / "screenshots"
            images.mkdir()
            (images / "ucie_320.png").write_bytes(png_header())
            receipt = base / "receipt"
            probe.inventory_manual_screenshots(images, receipt)
            with self.assertRaisesRegex(
                probe.ManualEdgeEvidenceError, "RECEIPT_DIR_MUST"):
                probe.inventory_manual_screenshots(images, receipt)

    def test_protected_original_root_denied(self):
        # Windows host path safety is enforced on actual Windows paths.
        if probe.Path("D:\\UCIE").anchor.lower() != "d:\\":
            self.skipTest("Windows drive path semantics only")
        self.assertTrue(probe._is_protected_original(probe.Path("D:\\UCIE")))
        self.assertFalse(probe._is_protected_original(probe.Path("D:\\UCIE_V2_QA")))


if __name__ == "__main__":
    unittest.main()
