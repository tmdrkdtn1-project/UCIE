"""Opt-in Windows Edge screenshot capture for UCIE V2 isolated preview only.

NEVER a browser visual PASS by itself. No external origins, user project scans,
uploads, production service modifications, scheduled jobs or screenshot publish.
Run manually with a *running, isolated* UCIE V2 loopback preview server.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

SCHEMA = "UCIE_V2_EDGE_VISUAL_CAPTURE_V01"
SIZES = (320, 390, 768, 1024, 1440)
HEIGHT = 900
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_SCREENSHOT_BYTES = 16 * 1024 * 1024
EDGE_REL = (
    ("PROGRAMFILES(X86)", "Microsoft/Edge/Application/msedge.exe"),
    ("PROGRAMFILES", "Microsoft/Edge/Application/msedge.exe"),
)
URL_PATH = "/v2/truth"
_ALLOWED_SELECTOR = re.compile(r"[A-Za-z0-9._-]{1,96}\Z")


class EdgePreviewError(ValueError):
    pass


def validate_url(url: str) -> str:
    if type(url) is not str or len(url) > 200 or any(ord(c) < 32 for c in url):
        raise EdgePreviewError("INVALID_URL")
    try:
        p = urlsplit(url)
        port = p.port
    except ValueError as exc:
        raise EdgePreviewError("INVALID_PORT_OR_URL") from exc
    if (p.scheme != "http" or p.hostname != "127.0.0.1"
            or p.username is not None or p.password is not None
            or port is None or not 1024 <= port <= 65535
            or p.path != URL_PATH or p.fragment):
        raise EdgePreviewError("ONLY_EXACT_LOOPBACK_PREVIEW_ALLOWED")
    if p.query:
        # Only the exact bounded selector; no raw query fan-out/duplicate keys.
        from urllib.parse import parse_qs
        try:
            values = parse_qs(p.query, strict_parsing=True,
                              keep_blank_values=True, max_num_fields=1)
        except ValueError as exc:
            raise EdgePreviewError("INVALID_QUERY") from exc
        if (set(values) != {"case"} or len(values["case"]) != 1
                or not _ALLOWED_SELECTOR.fullmatch(values["case"][0])):
            raise EdgePreviewError("UNAPPROVED_SELECTOR")
    return url


def find_edge() -> Path:
    if os.name != "nt":
        raise EdgePreviewError("WINDOWS_EDGE_ONLY")
    for key, relative in EDGE_REL:
        root = os.environ.get(key)
        if root:
            candidate = Path(root) / relative
            if candidate.is_file():
                return candidate
    raise EdgePreviewError("EDGE_EXECUTABLE_NOT_FOUND")


def capture_edge(url: str, output: Path, edge: Path, *,
                 timeout_seconds: int = 35) -> dict:
    """Capture 5 real Edge screenshots; record hashes, not visual acceptance.

    Preview server must already be running on loopback. Edge creates disposable
    browser profiles inside a private OS temporary directory, not owner profile.
    """
    validate_url(url)
    if os.name != "nt":
        raise EdgePreviewError("WINDOWS_EDGE_ONLY")
    if type(timeout_seconds) is not int or not 5 <= timeout_seconds <= 120:
        raise EdgePreviewError("INVALID_TIMEOUT")
    edge = edge.resolve()
    if not edge.is_file() or edge.name.lower() != "msedge.exe":
        raise EdgePreviewError("NOT_MICROSOFT_EDGE")
    # Explicit opt-in output directory. Refuse symlink and prior files;
    # never delete existing evidence or write into original D:\UCIE.
    output = output.expanduser().absolute()
    if str(output).lower().startswith("d:\\ucie\\") or str(output).lower() == "d:\\ucie":
        raise EdgePreviewError("PROTECTED_ORIGINAL_ROOT")
    if output.exists():
        if output.is_symlink() or any(output.iterdir()):
            raise EdgePreviewError("OUTPUT_MUST_BE_NEW_OR_EMPTY")
    else:
        if output.parent.is_symlink():
            raise EdgePreviewError("SYMLINK_PARENT_NOT_ALLOWED")
        output.mkdir(parents=True, exist_ok=False)
    artifacts = []
    with TemporaryDirectory(prefix="UCIE_EDGE_ISOLATED_") as scratch:
        root = Path(scratch)
        for width in SIZES:
            dest = output / ("ucie_v2_truth_" + str(width) + ".png")
            profile = root / ("profile_" + str(width))
            argv = [
                str(edge), "--headless=new", "--disable-gpu",
                "--no-first-run", "--no-default-browser-check",
                "--disable-extensions", "--disable-background-networking",
                "--user-data-dir=" + str(profile),
                "--window-size=" + str(width) + "," + str(HEIGHT),
                "--screenshot=" + str(dest), url,
            ]
            try:
                run = subprocess.run(argv, timeout=timeout_seconds,
                                     capture_output=True, check=False)
            except subprocess.TimeoutExpired as exc:
                raise EdgePreviewError("EDGE_SCREENSHOT_TIMEOUT") from exc
            if run.returncode != 0 or not dest.is_file():
                raise EdgePreviewError("EDGE_SCREENSHOT_FAILED_" + str(width))
            payload = dest.read_bytes()
            if (not payload.startswith(PNG_MAGIC) or
                    not 64 <= len(payload) <= MAX_SCREENSHOT_BYTES):
                raise EdgePreviewError("INVALID_PNG_" + str(width))
            artifacts.append({
                "width_requested_css_px": width, "height_requested_css_px": HEIGHT,
                "filename": dest.name, "sha256": sha256(payload).hexdigest(),
                "bytes": len(payload),
                "image_dimensions_verified": False,
                "no_horizontal_overflow_verified": False,
                "keyboard_focus_verified": False,
                "visual_review": "NOT_REVIEWED",
            })
    result = {
        "schema": SCHEMA, "target_origin": "http://127.0.0.1",
        "target_path": URL_PATH, "observed_edge_version": "NOT_RECORDED",
        "screenshot_captures": artifacts,
        "edge_process_executed": True,
        "edge_200_percent_page_zoom_verified": False,
        "actual_browser_keyboard_qa": "PENDING",
        "actual_visual_qa": "PENDING",
        "source_attestation": "NOT_VERIFIED",
        "release_approved": False,
        "uploads": 0, "production_database_writes": 0,
    }
    digest = sha256(json.dumps(result, sort_keys=True,
                               separators=(",", ":")).encode()).hexdigest()
    result["receipt_sha256"] = digest
    (output / "ucie_edge_capture_receipt.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="UCIE isolated Windows Edge screenshots")
    p.add_argument("--url", required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args(argv)
    result = capture_edge(args.url, Path(args.output_dir), find_edge())
    print(json.dumps({"status": "SCREENSHOTS_CAPTURED_VISUAL_QA_PENDING",
                      "receipt_sha256": result["receipt_sha256"],
                      "screenshots": len(result["screenshot_captures"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
