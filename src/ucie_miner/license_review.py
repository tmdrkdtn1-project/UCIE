"""Stage 7 bounded read-only license-file marker audit.

Official documentation confirms top-level cpython PSF-2.0 and PowerShell
MIT declarations. Presence at a pinned public tag is only a *marker*,
never a commit-level file license audit, legal opinion, or approval.

No network by default. The only optional network reads are pinned public
files in the previously approved Stage 4 source and tag allowlist.
"""
from __future__ import annotations

import hashlib

from .review import ALLOWED, ReviewError, load_manifest, public_read_only_get

# Each path and marker is a deliberately fixed, independently reviewable
# public upstream document, not a path chosen by untrusted input.
LICENSE_DOCS = {
    "python/cpython": ("Doc/license.rst",
                       "PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2",
                       "PSF-2.0"),
    "PowerShell/PowerShell": ("LICENSE.txt",
                             "MIT License", "MIT"),
}
MAX_LICENSE_BYTES = 500_000


def inspect_pinned_licenses(root, *, verify_live=False, fetch=None):
    """Metadata-only receipt; never promote license claims to approval."""
    if type(verify_live) is not bool:
        raise ReviewError("verify_live must be Boolean")
    manifest = load_manifest(root)  # bounded Stage 4 vetted manifest
    fetcher = public_read_only_get if fetch is None else fetch
    if not callable(fetcher):
        raise ReviewError("invalid public document fetcher")
    pairs = set()
    for entry in manifest["entries"]:
        source, tag = entry["source"], entry["release_tag"]
        if (source not in LICENSE_DOCS or source not in ALLOWED or
                tag not in ALLOWED[source]["tags"] or
                entry["license"] != LICENSE_DOCS[source][2]):
            raise ReviewError("unexpected public license metadata")
        pairs.add((source, tag))
    if len(pairs) > 16:
        raise ReviewError("too many pinned license documents")
    items = []
    for source, tag in sorted(pairs):
        file_path, marker, license_id = LICENSE_DOCS[source]
        url = (f"https://raw.githubusercontent.com/{source}/"
               f"{tag}/{file_path}")
        state, digest = "NOT_CHECKED", None
        if verify_live:
            try:
                body = fetcher(url)
                if (not isinstance(body, str) or
                        len(body.encode("utf-8")) > MAX_LICENSE_BYTES):
                    state = "UNAVAILABLE_OR_OVERSIZED"
                else:
                    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                    if marker not in body:
                        state = "MARKER_ABSENT"
                    else:
                        state = ("PUBLIC_TAG_MARKER_PRESENT" if fetch is None
                                 else "SYNTHETIC_TAG_MARKER_PRESENT")
            except (ReviewError, OSError, TimeoutError, ValueError,
                    TypeError, UnicodeError):
                state = "UNAVAILABLE_OR_OVERSIZED"
        items.append({
            "source": source, "release_tag": tag,
            "document_url": url, "declared_license": license_id,
            "marker_status": state, "body_sha256": digest,
            "tag_is_not_merge_commit": True,
            "independent_commit_license_reviewed": False,
            "legal_approval": False,
        })
    return {
        "schema": "UCIE_PINNED_LICENSE_MARKER_AUDIT_V1",
        "count": len(items), "items": items,
        "live_checked": bool(verify_live and fetch is None),
        "license_approved": False, "rules_promoted": 0,
        "persistent_writes": 0, "production_approved": False,
    }
