"""UCIE V1.1: opt-in approved-public release/tag ancestry observation.

A GitHub release object plus compare merge base is an observation of public
Git history, NOT independent proof of a fix, runtime version applicability,
source license terms, security behavior, or permission to promote a rule.
No external code execution, packages, files, scheduler, or DB writes.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import urllib.error
import urllib.request
from .core import NoRedirect, MiningError

from .library_explore import _candidate_rows
from .library_public_probe_v08 import _identity_preflight, ProbeError
from .library_observation_receipts_v10 import _root, _source_index, replay_observations
from .public_discovery import SOURCES
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_PUBLIC_RELEASE_ANCESTRY_OBSERVATION_V11"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
TAG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,42}\Z")
GATES = {name: "NOT_VERIFIED" for name in (
    "UPSTREAM_FIX_REGRESSION", "RELEASE_RUNTIME_APPLICABILITY",
    "LEGAL_LICENSE_REVIEW", "SECURITY_REVIEW", "OWNER_SIGNOFF",
)}


class ReleaseEvidenceError(ValueError):
    pass


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def _sha(value: dict) -> str:
    return sha256(_canonical(value)).hexdigest()


def _official_release_json(url: str) -> dict:
    """No redirects, proxies or credentials; ONLY the exact approved paths."""
    if type(url) is not str or len(url) > 230:
        raise ReleaseEvidenceError("unapproved official release endpoint")
    allowed = re.fullmatch(
        r"https://api\.github\.com/repos/([^/?#]+/[^/?#]+)/"
        r"(?:releases/tags/[A-Za-z0-9][A-Za-z0-9._-]{0,42}|"
        r"compare/[0-9a-f]{40}\.\.\.tags/[A-Za-z0-9][A-Za-z0-9._-]{0,42})",
        url)
    if allowed is None or allowed.group(1) not in SOURCES:
        raise ReleaseEvidenceError("API path outside five approved public repos")
    request = urllib.request.Request(
        url, method="GET", headers={
            "Accept": "application/vnd.github+json",
            "Accept-Encoding": "identity",
            "User-Agent": "UCIE-PUBLIC-RELEASE-CHECK/1.1",
        })
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect)
    try:
        with opener.open(request, timeout=10) as response:
            if response.status != 200:
                raise ReleaseEvidenceError("unexpected release response status")
            mime = response.headers.get("Content-Type", "").split(";", 1)[0].lower().strip()
            if (mime not in ("application/json", "application/vnd.github+json")
                    or response.headers.get("Content-Encoding", "identity") != "identity"):
                raise ReleaseEvidenceError("non-JSON or compressed release data")
            length = response.headers.get("Content-Length")
            if (length is not None and
                    (not length.isascii() or not length.isdecimal()
                     or int(length) > 262144)):
                raise ReleaseEvidenceError("release metadata body too large")
            raw = response.read(262145)
    except (OSError, TimeoutError, urllib.error.URLError,
            MiningError) as exc:
        raise ReleaseEvidenceError("approved release endpoint unreachable") from exc
    if len(raw) > 262144:
        raise ReleaseEvidenceError("public release response size exceeded")
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ReleaseEvidenceError("malformed public release metadata") from exc
    if type(obj) is not dict:
        raise ReleaseEvidenceError("unexpected release object")
    return obj


def _date(value: object) -> bool:
    if type(value) is not str or not 10 <= len(value) <= 35:
        return False
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0


def _selected_source(root: Path, item_id: str, *,
                     source_reader=None, replay_reader=None) -> dict:
    if type(item_id) is not str or HEX64.fullmatch(item_id) is None:
        raise ReleaseEvidenceError("exact public candidate SHA required")
    root = _root(root)
    handoff = (prepare_verification_handoff if source_reader is None
               else source_reader)(root)
    index = _source_index(handoff)
    row = index.get(item_id)
    if row is None:
        raise ReleaseEvidenceError("no current source-linked candidate")
    repo, kind, value = _identity_preflight(row)
    # A release check MUST be chained to a previously recorded, checked
    # observation of an exact public merge identity; not an arbitrary PR.
    replay = (replay_observations if replay_reader is None else replay_reader)(root)
    matches = [o for o in replay["observations"]
               if o["item_id"] == item_id
               and o["source_id"] == row["source_id"]
               and o["revision_hint"] == row["revision_hint"]
               and o["identity_matched"] is True
               and o["metadata_status"] in (
                   "PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED",
                   "PUBLIC_COMMIT_IDENTITY_MATCHED_NOT_FIX_VERIFIED")]
    if not matches:
        raise ReleaseEvidenceError("prior source identity observation required")
    return row


def inspect_release_ancestry(row: dict, *, release_tag: str,
                             fetch_json=None) -> dict:
    """Two bounded allowlisted public calls; fail closed on inconsistent refs.

    release tags use exact GitHub release resource and compare base commit
    against the tag. Observed source membership is NOT a fix PASS.
    """
    if type(release_tag) is not str or TAG.fullmatch(release_tag) is None:
        raise ReleaseEvidenceError("invalid exact release tag")
    repo, kind, value = _identity_preflight(row)
    commit = row["revision_hint"]
    if repo not in SOURCES or HEX40.fullmatch(commit) is None:
        raise ReleaseEvidenceError("source not bound to approved commit")
    base = "https://api.github.com/repos/" + repo
    release_url = base + "/releases/tags/" + release_tag
    compare_url = base + "/compare/" + commit + "...tags/" + release_tag
    fetch = _official_release_json if fetch_json is None else fetch_json
    status = "PUBLIC_RELEASE_ANCESTRY_UNAVAILABLE_NO_GO"
    observed = False
    ancestry = False
    release_id = None
    head_sha = None
    published = None
    try:
        release = fetch(release_url)
        if type(release) is not dict:
            raise ReleaseEvidenceError("invalid release metadata shape")
        if (release.get("tag_name") != release_tag
                or type(release.get("id")) is not int
                or release.get("draft") is not False
                or release.get("prerelease") not in (True, False)
                or not _date(release.get("published_at"))
                or release.get("html_url") !=
                "https://github.com/" + repo + "/releases/tag/" + release_tag):
            return _result(row, release_tag, status="INVALID_RELEASE_METADATA_NO_GO",
                           observed=True, ancestry=False)
        release_id = release["id"]
        published = release["published_at"]
        compared = fetch(compare_url)
        if type(compared) is not dict:
            raise ReleaseEvidenceError("invalid public compare data")
        base_commit = compared.get("base_commit")
        merge_base = compared.get("merge_base_commit")
        head_commit = compared.get("head_commit")
        if not all(type(v) is dict for v in (base_commit, merge_base, head_commit)):
            return _result(row, release_tag, status="INVALID_COMPARE_GRAPH_NO_GO",
                           observed=True, ancestry=False, release_id=release_id,
                           published=published)
        head_sha = head_commit.get("sha")
        same_base = base_commit.get("sha") == commit
        same_merge_base = merge_base.get("sha") == commit
        valid_head = type(head_sha) is str and HEX40.fullmatch(head_sha) is not None
        behind = compared.get("behind_by")
        ahead = compared.get("ahead_by")
        graph_ok = (type(behind) is int and type(ahead) is int
                    and behind == 0 and ahead >= 0 and same_base
                    and same_merge_base and valid_head
                    and compared.get("status") in ("ahead", "identical"))
        observed = True
        ancestry = bool(graph_ok)
        status = ("RELEASE_TAG_CONTAINS_SOURCE_COMMIT_NOT_FIX_VERIFIED"
                  if ancestry else "RELEASE_TAG_NOT_PROVEN_TO_CONTAIN_COMMIT_NO_GO")
    except (ProbeError, OSError, ValueError, TypeError, KeyError, ReleaseEvidenceError):
        status = "PUBLIC_RELEASE_ANCESTRY_UNAVAILABLE_NO_GO"
    return _result(row, release_tag, status=status, observed=observed,
                   ancestry=ancestry, release_id=release_id,
                   head_sha=head_sha, published=published)


def _result(row: dict, tag: str, *, status: str, observed: bool,
            ancestry: bool, release_id=None, head_sha=None,
            published=None) -> dict:
    result = {
        "schema": SCHEMA, "status": status,
        "item_id": row["library_item_id"],
        "source_id": row["source_id"],
        "source_commit_sha": row["revision_hint"],
        "release_tag_claimed": tag,
        "release_id": release_id,
        "release_published_at": published,
        "release_tag_head_commit_sha": head_sha,
        "public_metadata_observed": observed,
        "tag_contains_exact_source_commit": ancestry,
        "runtime_version_fix_verified": False,
        "independent_upstream_regression": False,
        "gates": dict(GATES),
        "rule_approved": False,
        "auto_promoted": False,
        "source_code_executed": False,
        "local_writes": 0,
    }
    result["result_sha256"] = _sha(result)
    return result


def check_current_public_release(root: Path, *, item_id: str, release_tag: str,
                                 source_reader=None, replay_reader=None,
                                 fetch_json=None) -> dict:
    row = _selected_source(root, item_id, source_reader=source_reader,
                           replay_reader=replay_reader)
    return inspect_release_ancestry(row, release_tag=release_tag,
                                    fetch_json=fetch_json)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="UCIE explicit public release ancestry observation; no rule approval")
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--check-public", action="store_true", required=True)
    args = parser.parse_args()
    try:
        output = check_current_public_release(
            Path(__file__).resolve().parents[2], item_id=args.item_id,
            release_tag=args.release_tag)
    except (ReleaseEvidenceError, ProbeError, ValueError, OSError):
        print(json.dumps({"schema": SCHEMA, "status": "RELEASE_CHECK_NO_GO"}))
        return 2
    print(json.dumps(output, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
