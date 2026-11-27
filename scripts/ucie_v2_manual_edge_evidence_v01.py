"""Read-only manual Edge screenshot evidence inventory for UCIE V2.

Explicit owner invocation only. Does not launch Edge, access HTTP or copy PNGs.
Checks PNG headers/CRC and records local hashes. NOT a visual/a11y PASS.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct
import zlib

SCHEMA = "UCIE_V2_MANUAL_EDGE_EVIDENCE_V01"
WIDTHS = (320, 390, 768, 1024, 1440)
MAX_BYTES = 16 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
RECEIPT_NAME = "ucie_v2_manual_edge_evidence.json"


class ManualEdgeEvidenceError(ValueError):
    pass


def _is_protected_original(path: Path) -> bool:
    parts = path.absolute().parts
    return len(parts) >= 2 and parts[0].lower() == "d:\\" and parts[1].lower() == "ucie"


def _png_details(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ManualEdgeEvidenceError("SCREENSHOT_MISSING_OR_SYMLINK_" + path.name)
    size = path.stat().st_size
    if not 45 <= size <= MAX_BYTES:
        raise ManualEdgeEvidenceError("SCREENSHOT_SIZE_INVALID_" + path.name)
    raw = path.read_bytes()
    if (not raw.startswith(PNG_SIGNATURE) or raw[12:16] != b"IHDR"
            or struct.unpack(">I", raw[8:12])[0] != 13):
        raise ManualEdgeEvidenceError("INVALID_PNG_HEADER_" + path.name)
    if zlib.crc32(raw[12:29]) & 0xffffffff != struct.unpack(">I", raw[29:33])[0]:
        raise ManualEdgeEvidenceError("PNG_IHDR_CRC_MISMATCH_" + path.name)
    width, height = struct.unpack(">II", raw[16:24])
    if not 1 <= width <= 16384 or not 1 <= height <= 16384:
        raise ManualEdgeEvidenceError("INVALID_PNG_DIMENSIONS_" + path.name)
    return {"png_pixel_width": width, "png_pixel_height": height,
            "sha256": sha256(raw).hexdigest(), "bytes": len(raw),
            "png_header_crc_verified": True,
            "png_full_decode_verified": False}


def inventory_manual_screenshots(source_dir: Path, receipt_dir: Path) -> dict:
    """Read only allowlisted screenshots and save one non-PASS inventory JSON."""
    source_dir = source_dir.absolute()
    receipt_dir = receipt_dir.absolute()
    if (_is_protected_original(source_dir) or _is_protected_original(receipt_dir)
            or source_dir.is_symlink() or receipt_dir.is_symlink()):
        raise ManualEdgeEvidenceError("PROTECTED_OR_SYMLINK_DIRECTORY")
    if not source_dir.is_dir():
        raise ManualEdgeEvidenceError("SCREENSHOT_DIRECTORY_NOT_FOUND")
    images = []
    for width in WIDTHS:
        name = "ucie_" + str(width) + ".png"
        file = source_dir / name
        if not file.exists():
            continue
        meta = _png_details(file)
        images.append({"filename": name, "requested_viewport_css_px": width,
                       "actual_viewport_verified": False,
                       "browser_identity_verified": False,
                       "keyboard_qa": "PENDING", "visual_qa": "PENDING",
                       **meta})
    if not images:
        raise ManualEdgeEvidenceError("NO_ALLOWED_SCREENSHOTS_FOUND")
    result = {
        "schema": SCHEMA, "images": images,
        "captured_widths_count": len(images), "required_widths": list(WIDTHS),
        "all_widths_present": len(images) == len(WIDTHS),
        "evidence_kind": "OWNER_SUPPLIED_SCREENSHOT_UNREVIEWED",
        "edge_process_execution": "NOT_TESTED_BY_THIS_TOOL",
        "csp_review": "SEPARATE",
        "200_percent_zoom": "NOT_VERIFIED",
        "keyboard_focus": "NOT_VERIFIED",
        "responsive_layout": "NOT_VERIFIED",
        "visual_qa": "PENDING",
        "independent_qa": "PENDING",
        "product_release_approved": False,
        "uploads": 0, "operating_db_writes": 0,
    }
    result["receipt_sha256"] = sha256(json.dumps(
        result, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()
    # Never overwrite or delete a prior receipt or any original screenshot.
    if receipt_dir.exists():
        if not receipt_dir.is_dir() or any(receipt_dir.iterdir()):
            raise ManualEdgeEvidenceError("RECEIPT_DIR_MUST_BE_NEW_OR_EMPTY")
    else:
        if receipt_dir.parent.is_symlink() or not receipt_dir.parent.is_dir():
            raise ManualEdgeEvidenceError("RECEIPT_PARENT_INVALID")
        receipt_dir.mkdir()
    (receipt_dir / RECEIPT_NAME).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE manually captured Edge evidence (never auto PASS)")
    parser.add_argument("--screenshots-dir", type=Path, required=True)
    parser.add_argument("--receipt-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = inventory_manual_screenshots(
            args.screenshots_dir, args.receipt_dir)
    except ManualEdgeEvidenceError as exc:
        parser.exit(2, "UCIE_MANUAL_EDGE_HOLD: " + str(exc) + "\n")
    print(json.dumps({
        "status": "EVIDENCE_REGISTERED_VISUAL_QA_PENDING",
        "images": report["captured_widths_count"],
        "receipt_sha256": report["receipt_sha256"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
