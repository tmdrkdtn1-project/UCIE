"""UCIE V2 isolated owner Local B1-B5 one-command acceptance preflight.

Run --check for source-bound verification without writes, or --open for an
EXPLICIT, fixed-name UTF-8 HTML file in the operating-system temp directory
and an owner-visible local browser opening. This is NOT an Edge QA receipt,
human trial, server, new route or approval. No arbitrary paths/input allowed.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit

from .local_v1_priority_v01 import require_local_work
from .ucie_v2_capsule_v01 import build_from_existing_ucie
from .ucie_v2_local_readonly_preview_v01 import EXAMPLE_IDS, render_all_cases_page

SCHEMA = "UCIE_V2_OWNER_LOCAL_B1_B5_PREFLIGHT_V01"
ALLOWED_FLAGS = ("--check", "--open")
PAGE_PREFIX = "ucie_v2_owner_review_"


class PreflightError(ValueError):
    """No caller inputs, file paths, or private strings are echoed on failure."""


class _PageScanner(HTMLParser):
    """Count product sections, reject active resources, inspect exact link scope."""

    FORBIDDEN_TAGS = frozenset({
        "script", "iframe", "form", "input", "textarea", "select",
        "button", "object", "embed", "audio", "video", "img", "link",
        "base", "meta-refresh", "frame", "frameset",
    })

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.counts = {}
        self.ids = set()
        self.links = []
        self.violations = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.counts[tag] = self.counts.get(tag, 0) + 1
        if tag in self.FORBIDDEN_TAGS:
            self.violations.append("active element")
        for name, value in attrs:
            if name.lower().startswith("on") or name in ("src", "srcdoc"):
                self.violations.append("active attribute")
            if name == "id":
                if value in self.ids:
                    self.violations.append("duplicate id")
                self.ids.add(value)
            if tag == "a" and name == "href":
                self.links.append(value)
            if name == "style" and value and ("url(" in value.lower()
                                            or "@import" in value.lower()):
                self.violations.append("external CSS")
        if tag == "meta":
            pairs = dict(attrs)
            if pairs.get("http-equiv", "").lower() == "refresh":
                self.violations.append("redirect")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def build_owner_preflight() -> tuple[dict, str]:
    require_local_work("LOCAL_ACCEPTANCE")
    html = render_all_cases_page()
    if not html.startswith('<!doctype html><html lang="ko">'):
        raise PreflightError("not a UTF-8 local user journey")
    if len(html) < 3000 or len(html) > 500_000:
        raise PreflightError("unexpected product preview size")
    scanner = _PageScanner()
    scanner.feed(html)
    scanner.close()
    required_ids = {
        *(f"case-{case}" for case in EXAMPLE_IDS),
        "source-revision-study", "revision-lifecycle",
        "owner-acceptance", "b5-first-use-evaluation",
    }
    capsule = build_from_existing_ucie()
    expected_urls = {
        capsule.official_source_url,
        capsule.official_spec_url,
        capsule.first_party_sdk_ci_url,
    }
    expected_anchors = {f"#case-{case}" for case in EXAMPLE_IDS}
    links = scanner.links
    if (scanner.violations
            or scanner.counts.get("html") != 1
            or scanner.counts.get("head") != 1
            or scanner.counts.get("body") != 1
            or scanner.counts.get("main") != 1
            or not required_ids.issubset(scanner.ids)
            or any(not isinstance(u, str) for u in links)
            or set(links) != expected_urls | expected_anchors
            or len(links) != len(expected_urls | expected_anchors)
            or any(urlsplit(url).scheme != "https" for url in expected_urls)
            or any(not urlsplit(url).hostname for url in expected_urls)):
        raise PreflightError("preview structure or source proof scope changed")
    if (html.count('class="case-panel"') != 4
            or html.count('class="lifecycle-step"') != 3
            or html.count('class="impact-case"') != 3
            or html.count('class="review-card"') != 2
            or html.count('id="b5-first-use-evaluation"') != 1
            or "실제 비교시험은 아직 수행하지 않았습니다" not in html
            or "고객 배포 미승인" not in html):
        raise PreflightError("B1-B5 scope or truth claims missing")
    digest = sha256(html.encode("utf-8")).hexdigest()
    receipt = {
        "schema": SCHEMA,
        "status": "OFFLINE_B1_B5_STATIC_CONTRACT_VERIFIED_ONLY",
        "case_count": 4,
        "scenario_count": 3,
        "new_revision_check_scenarios": 3,
        "b5_comparison_arms": 3,
        "official_links_count": len(expected_urls),
        "page_sha256": digest,
        "owner_edge_browser_viewed_new_head": False,
        "actual_keyboard_responsive_qa_pass": False,
        "actual_novice_trials": 0,
        "actual_comparison_trials": 0,
        "actual_source_change_authenticated": False,
        "source_qa_verified": False,
        "rights_approved": False,
        "customer_release_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "file_written_by_preflight": False,
    }
    return receipt, html


def save_fixed_temp_preview(html: str, digest: str) -> Path:
    """Explicit --open only, collision-safe deterministic temp file.

    No caller-selected path, no overwriting files, no private data export.
    This is only rendered first-party offline public demonstration HTML.
    """
    if (type(html) is not str or type(digest) is not str
            or len(digest) != 64
            or sha256(html.encode("utf-8")).hexdigest() != digest):
        raise PreflightError("generated preview integrity mismatch")
    target = Path(tempfile.gettempdir()) / (PAGE_PREFIX + digest[:16] + ".html")
    raw = html.encode("utf-8")
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file() or target.read_bytes() != raw:
            raise PreflightError("existing local preview differs; no overwrite")
        return target
    try:
        with target.open("xb") as stream:
            stream.write(raw)
    except FileExistsError as exc:
        raise PreflightError("local preview path race; no overwrite") from exc
    return target


def main(argv: list[str] | None = None) -> int:
    values = sys.argv[1:] if argv is None else argv
    if type(values) is not list or len(values) != 1 or values[0] not in ALLOWED_FLAGS:
        print("UCIE_USAGE: --check OR --open (owner local review only)",
              file=sys.stderr)
        return 2
    try:
        receipt, html = build_owner_preflight()
        if values[0] == "--check":
            print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
            return 0
        if os.name != "nt" or not callable(getattr(os, "startfile", None)):
            print("UCIE_HOLD: --open requires owner Windows interactive session",
                  file=sys.stderr)
            return 2
        path = save_fixed_temp_preview(html, receipt["page_sha256"])
        # The user explicitly chose --open; OS opens a LOCAL file in its
        # configured HTML application. No Edge-only QA assertion is possible.
        os.startfile(str(path))
        print("UCIE_OWNER_PREVIEW_OPEN_REQUESTED")
        print("FILE:", str(path))
        print("SHA256:", receipt["page_sha256"])
        print("STATUS: browser display and owner acceptance NOT verified")
        return 0
    except (PreflightError, KeyError, TypeError, ValueError, OSError):
        print("UCIE_HOLD: preview contract, source or local file check failed",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
