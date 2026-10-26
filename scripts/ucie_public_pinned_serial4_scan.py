"""One-command, exact-commit public source scan with existing signed Serial 4.

Only approved public GitHub repositories and one explicitly selected .py/.ps1
file. No recursion, private inputs, external source execution, source storage,
automatic fixes, promotions, scheduling or release signing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from ucie_public.mixed_release import (  # noqa: E402
    RULE_ORDER, scan_mixed_owner_receipt, verify_mixed_owner_release,
)
from ucie_public.policy import PolicyError  # noqa: E402
from ucie_miner.static_concurrency import inspect_python_scandir_source  # noqa: E402

APPROVED = frozenset({
    "python/cpython", "PowerShell/PowerShell", "git/git",
    "modelcontextprotocol/python-sdk", "actions/runner-images",
})
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
SEGMENT = re.compile(r"[A-Za-z0-9_.-]+\Z")
MAX_SOURCE_BYTES = 131072


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _identity(repo: str, commit: str, path: str, git_blob: str) -> str:
    """Fail closed before making ANY public GET."""
    if (repo not in APPROVED or type(commit) is not str
            or HEX40.fullmatch(commit) is None
            or type(git_blob) is not str or HEX40.fullmatch(git_blob) is None
            or type(path) is not str or len(path) > 240):
        raise PolicyError("unapproved or unpinned public GitHub source")
    segments = path.split("/")
    if (not segments or any(
        seg in ("", ".", "..") or SEGMENT.fullmatch(seg) is None
        for seg in segments
    ) or not path.endswith((".py", ".ps1"))):
        raise PolicyError("noncanonical public source path")
    return f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"


def _fetch_exact(url: str) -> bytes:
    # No redirects to unapproved hosts. Only _identity constructs the URL.
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(
        url, headers={"User-Agent": "UCIE-signed-public-manual-source-v1"})
    with opener.open(request, timeout=20) as response:
        if response.status != 200 or response.geturl() != url:
            raise PolicyError("public source HTTP identity mismatch")
        raw = response.read(MAX_SOURCE_BYTES + 1)
    if not raw or len(raw) > MAX_SOURCE_BYTES:
        raise PolicyError("empty or oversized public source")
    return raw


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def scan_pinned_source(*, repo: str, commit: str, path: str,
                       blob: str, pack: Path, trust: Path,
                       fetch_source=None, ps_parse=None) -> dict:
    """Review exactly one pinned public source; never interpret its code."""
    url = _identity(repo, commit, path, blob)
    verified = verify_mixed_owner_release(pack, trust, min_serial=4)
    if (verified.get("result") != "MIXED_OWNER_PUBLIC_MANUAL_PACK_VERIFIED"
            or verified.get("owner_signature") != "VALID"
            or verified.get("scope") != "PUBLIC_ONLY_MANUAL_STATIC_SCAN"
            or verified.get("serial") != 4
            or verified.get("rule_count") != 4
            or verified.get("rule_ids") != list(RULE_ORDER)
            or verified.get("auto_apply") is not False):
        raise PolicyError("not the approved, signed four-rule manual pack")

    fetch = _fetch_exact if fetch_source is None else fetch_source
    raw = fetch(url)
    if (type(raw) is not bytes or not raw
            or len(raw) > MAX_SOURCE_BYTES
            or _git_blob(raw) != blob):
        raise PolicyError("pinned Git blob mismatch or invalid public bytes")
    try:
        source = raw.decode("utf-8-sig", errors="strict")
    except UnicodeError as exc:
        raise PolicyError("public source is not UTF-8") from exc

    if path.endswith(".py"):
        receipt = inspect_python_scandir_source(source)
    else:
        if ps_parse is None:
            from scripts.ucie_owner_four_rule_one_shot import power_shell_receipt
            ps_parse = power_shell_receipt
        receipt = ps_parse(
            ROOT / "scripts" / "ucie_powershell_static_candidates.ps1",
            source, ROOT,
        )
    matched = scan_mixed_owner_receipt(pack, trust, receipt, min_serial=4)
    if (matched.get("schema") != "UCIE_MIXED_PUBLIC_MANUAL_STATIC_SCAN_V2"
            or matched.get("owner_signature") != "VALID"
            or matched.get("pack_serial") != 4
            or matched.get("source_sha256") != receipt["source_sha256"]
            or matched.get("source_executed") is not False
            or matched.get("source_files_read") != 0
            or matched.get("persistent_writes") != 0
            or matched.get("auto_fix_applied") is not False
            or matched.get("auto_apply") is not False
            or matched.get("finding_count") != len(matched.get("findings", []))):
        raise PolicyError("signed public scan receipt outside safe scope")
    findings = matched["findings"]
    return {
        "schema": "UCIE_SERIAL4_PINNED_PUBLIC_SOURCE_SCAN_V1",
        "status": ("MANUAL_REVIEW_CANDIDATES" if findings
                   else "NO_SIGNED_RULE_MATCH"),
        "source": {"repository": repo, "commit": commit, "path": path,
                   "git_blob_sha1": blob, "source_sha256": receipt["source_sha256"],
                   "role": ("TEST_PATH" if
                            any(x.lower() in ("test", "tests") or
                                x.lower().startswith("test_")
                                for x in path.split("/"))
                            else "UNCLASSIFIED_PUBLIC_SOURCE")},
        "serial": 4,
        "owner_signature": "VALID",
        "rule_count": 4,
        "candidate_count": len(findings),
        "candidates": [
            {"rule_id": x["rule_id"], "line": x["line"],
             "column": x["column"], "manual_review_required": True,
             "runtime_bug_confirmed": False}
            for x in findings
        ],
        "source_executed": False,
        "auto_fix": False,
        "private_project_access": False,
        "new_signing": False,
        "external_deployment": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan one Git-blob-pinned approved public file with existing signed Serial 4")
    parser.add_argument("--repo", required=True, choices=sorted(APPROVED))
    parser.add_argument("--commit", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--blob", required=True,
                        help="Exact Git blob SHA-1 for the source at this commit")
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--trust", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = scan_pinned_source(
            repo=args.repo, commit=args.commit, path=args.path,
            blob=args.blob, pack=args.pack, trust=args.trust)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except (PolicyError, OSError, ValueError, TypeError,
            UnicodeError, TimeoutError) as exc:
        print(json.dumps({
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__,
            "source_executed": False, "auto_fix": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
