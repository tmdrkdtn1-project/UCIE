"""Stage 4: offline-first PUBLIC_ONLY candidate review. No automatic approval.

Input: existing UCIE miner database and manually curated independent upstream PR
metadata. Network verification (explicit opt-in) fetches only allowlisted public
PR metadata and pinned release-tag source files; no credentials or project data.
"""
from __future__ import annotations

from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import urllib.error
import urllib.request

SCHEMA = "UCIE_PR_REVIEW_EVIDENCE_V1"
RESULT_SCHEMA = "UCIE_PR_REVIEW_RESULT_V1"
ALLOWED = {
    "python/cpython": {
        "license": "PSF-2.0",
        "tags": frozenset({"v3.15.0", "v3.14.8"}),
        "files": frozenset({
            "Modules/posixmodule.c", "Python/pystate.c", "Python/codegen.c",
            "Python/Python-ast.c", "Python/initconfig.c", "Objects/typeobject.c",
        }),
    },
    "PowerShell/PowerShell": {
        "license": "MIT",
        "tags": frozenset({"v7.5.12", "v7.6.7"}),
        "files": frozenset({
            "src/System.Management.Automation/engine/remoting/common/RunspaceConnectionInfo.cs",
            "src/System.Management.Automation/engine/GetCommandCommand.cs",
            "src/Microsoft.PowerShell.Commands.Management/commands/management/ResolvePathCommand.cs",
        }),
    },
}
MAX_MANIFEST = 65536
MAX_CANDIDATES = 10000
MAX_RESPONSE = 1_500_000
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
SAFE_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{5,63}\Z")


class ReviewError(ValueError):
    """Fail-closed public review failure (never a production claim)."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ReviewError("redirect rejected")


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _check_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ReviewError("timestamp must be UTC Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewError("invalid timestamp") from exc
    if parsed.utcoffset().total_seconds() != 0:
        raise ReviewError("timestamp must be UTC")
    return value


def _repo_paths(root: Path) -> tuple[Path, Path]:
    # Never follow a symlink out to an unrelated project or database.
    if root.is_symlink() or not root.is_dir():
        raise ReviewError("UCIE root must be an existing, nonsymlink directory")
    runtime = root / "runtime"
    if runtime.is_symlink() or not runtime.is_dir():
        raise ReviewError("UCIE runtime must be an existing, nonsymlink directory")
    miner = runtime / "public_miner.sqlite3"
    if miner.is_symlink() or not miner.is_file():
        raise ReviewError("UCIE candidate DB not found or unsafe")
    return runtime, miner


def _no_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ReviewError("duplicate manifest JSON key")
        obj[key] = value
    return obj


def load_manifest(root: Path) -> dict:
    target = root / "curated_public" / "pr_review_evidence_v1.json"
    if (root / "curated_public").is_symlink() or target.is_symlink():
        raise ReviewError("curated evidence symlink denied")
    if not target.is_file() or target.stat().st_size > MAX_MANIFEST:
        raise ReviewError("missing/oversized review evidence")
    try:
        data = json.loads(target.read_text("utf-8"), object_pairs_hook=_no_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReviewError("invalid curated evidence JSON") from exc
    if not isinstance(data, dict) or set(data) != {"schema", "entries", "basis"}:
        raise ReviewError("unexpected manifest layout")
    if data["schema"] != SCHEMA or data["basis"] != "MANUAL_PUBLIC_PR_AND_TAG_SOURCE_REVIEW_ONLY":
        raise ReviewError("unapproved review evidence type")
    entries = data["entries"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 40:
        raise ReviewError("review evidence size outside bounds")
    by_key = {}
    fields = {"source", "pr_number", "merged_at", "pattern_id", "canonical_pr_number", "release_tag",
              "release_file", "release_marker", "license", "risk_category"}
    for e in entries:
        if not isinstance(e, dict) or set(e) != fields:
            raise ReviewError("review entry has unexpected fields")
        source = e["source"]
        if source not in ALLOWED:
            raise ReviewError("public source outside review allowlist")
        policy = ALLOWED[source]
        n = e["pr_number"]
        canonical = e["canonical_pr_number"]
        if type(n) is not int or type(canonical) is not int or not (0 < n < 1000000 and 0 < canonical < 1000000):
            raise ReviewError("invalid PR identifiers")
        if not isinstance(e["pattern_id"], str) or not SAFE_PATTERN.fullmatch(e["pattern_id"]):
            raise ReviewError("invalid stable pattern ID")
        if e["release_tag"] not in policy["tags"] or e["release_file"] not in policy["files"]:
            raise ReviewError("release check outside pinned allowlist")
        marker = e["release_marker"]
        if not isinstance(marker, str) or not 8 <= len(marker) <= 130 or "\n" in marker or "\r" in marker:
            raise ReviewError("invalid release signature marker")
        if e["license"] != policy["license"]:
            raise ReviewError("license inconsistent with allowed public repository")
        if e["risk_category"] not in {"API_USAGE", "PATH_BEHAVIOR", "THREAD_SAFETY", "RESOURCE_CLEANUP", "COMPILER_INTERNAL"}:
            raise ReviewError("unapproved risk category")
        _check_timestamp(e["merged_at"])
        key = (source, n)
        if key in by_key:
            raise ReviewError("duplicate PR in review evidence")
        by_key[key] = e
    for e in entries:
        origin = by_key.get((e["source"], e["canonical_pr_number"]))
        if origin is None or origin["pattern_id"] != e["pattern_id"]:
            raise ReviewError("canonical PR missing or pattern mismatch")
    return data


def _read_candidates(root: Path) -> list[dict]:
    _, db_file = _repo_paths(root)
    db_uri = db_file.resolve(strict=True).as_uri() + "?mode=ro"
    with closing(sqlite3.connect(db_uri, uri=True)) as db:
        status = db.execute("PRAGMA quick_check").fetchone()
        if status != ("ok",):
            raise ReviewError("candidate DB integrity failure")
        rows = db.execute("SELECT source, pr_number, public_url, merged_at, evidence_sha256, status FROM candidates ").fetchmany(MAX_CANDIDATES + 1)
    if len(rows) > MAX_CANDIDATES:
        raise ReviewError("too many public candidates")
    result = []
    for source, n, url, merged, digest, status in rows:
        if (source not in ALLOWED or type(n) is not int or n < 1 or n >= 1000000 or
            url != f"https://github.com/{source}/pull/{n}" or
            not isinstance(digest, str) or not SHA256.fullmatch(digest) or
            status != "UNVERIFIED_CANDIDATE_ONLY"):
            raise ReviewError("invalid or out-of-scope DB candidate")
        _check_timestamp(merged)
        result.append({"source": source, "pr_number": n, "public_url": url,
                       "merged_at": merged, "evidence_sha256": digest})
    return sorted(result, key=lambda c: (c["source"], c["pr_number"]))


def public_read_only_get(url: str) -> object:
    """Anonymous, no redirects. Caller supplies only URLs constructed from allowlists."""
    if not (url.startswith("https://api.github.com/repos/python/cpython/pulls/") or
            url.startswith("https://api.github.com/repos/PowerShell/PowerShell/pulls/") or
            url.startswith("https://raw.githubusercontent.com/python/cpython/") or
            url.startswith("https://raw.githubusercontent.com/PowerShell/PowerShell/")):
        raise ReviewError("unapproved public URL")
    request = urllib.request.Request(url, method="GET", headers={
        "User-Agent": "UCIE-PUBLIC-REVIEW/0.1", "Accept": "application/vnd.github+json"})
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=12) as stream:
            if stream.status != 200:
                raise ReviewError("upstream did not return 200")
            raw = stream.read(MAX_RESPONSE + 1)
            content_type = stream.headers.get("Content-Type", "")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ReviewError("public source temporarily unavailable") from exc
    if len(raw) > MAX_RESPONSE:
        raise ReviewError("public response too large")
    try:
        content = raw.decode("utf-8")
        if url.startswith("https://api.github.com/"):
            if "json" not in content_type:
                raise ReviewError("unexpected API content type")
            return json.loads(content)
        return content
    except (UnicodeError, ValueError) as exc:
        raise ReviewError("invalid public source encoding or JSON") from exc


def _verify_live(row: dict, evidence: dict, fetch) -> tuple[str, str]:
    """Check PR metadata and a recognizable marker at *exactly one* pinned release tag.

    A marker is not a full semantic patch check or independent regression PASS.
    """
    source, number = row["source"], row["pr_number"]
    api = f"https://api.github.com/repos/{source}/pulls/{number}"
    try:
        pr = fetch(api)
        if (not isinstance(pr, dict) or pr.get("merged_at") != row["merged_at"] or
            pr.get("html_url") != row["public_url"] or
            pr.get("merged") is not True or pr.get("number") != number):
            return "SOURCE_MISMATCH", "NOT_CHECKED"
    except (ReviewError, TimeoutError, OSError, ValueError):
        return "SOURCE_UNAVAILABLE", "NOT_CHECKED"
    raw_url = (f"https://raw.githubusercontent.com/{source}/"
               f"{evidence['release_tag']}/{evidence['release_file']}")
    try:
        body = fetch(raw_url)
        if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_RESPONSE:
            raise ReviewError("invalid tag source text")
        return "SOURCE_MATCHED", "TAG_MARKER_PRESENT" if evidence["release_marker"] in body else "TAG_MARKER_ABSENT"
    except (ReviewError, TimeoutError, OSError, ValueError):
        return "SOURCE_MATCHED", "TAG_CHECK_UNAVAILABLE"


def analyze(root: Path, *, verify_live: bool = False, fetch=public_read_only_get) -> dict:
    """Never imports/executes upstream code; never approves or publishes a rule."""
    manifest = load_manifest(root)
    entries = {(e["source"], e["pr_number"]): e for e in manifest["entries"]}
    observed = _read_candidates(root)
    result = []
    for row in observed:
        e = entries.get((row["source"], row["pr_number"]))
        if e is None or e["merged_at"] != row["merged_at"]:
            result.append({"source": row["source"], "pr_number": row["pr_number"],
                           "public_url": row["public_url"], "pattern_id": None,
                           "canonical_pr_number": None, "review_state": "MAPPING_REQUIRED",
                           "source_check": "NOT_CHECKED", "release_check": "NOT_CHECKED",
                           "release_tag": None, "license": None, "approval": False})
            continue
        source_status, release_status = ("CURATED_ONLY", "NOT_CHECKED")
        if verify_live:
            source_status, release_status = _verify_live(row, e, fetch)
        is_candidate = source_status not in {"SOURCE_MISMATCH", "SOURCE_UNAVAILABLE"}
        result.append({"source": row["source"], "pr_number": row["pr_number"],
                       "public_url": row["public_url"], "pattern_id": e["pattern_id"] if is_candidate else None,
                       "canonical_pr_number": e["canonical_pr_number"] if is_candidate else None,
                       "review_state": "RULE_CANDIDATE_ONLY" if is_candidate else "SOURCE_RECHECK_REQUIRED",
                       "source_check": source_status, "release_check": release_status,
                       "release_tag": e["release_tag"], "license": e["license"],
                       "risk_category": e["risk_category"], "approval": False})
    groups = defaultdict(list)
    for rec in result:
        if rec["review_state"] == "RULE_CANDIDATE_ONLY":
            groups[f"{rec['source']}#{rec['canonical_pr_number']}"].append(rec["pr_number"])
    return {"schema": RESULT_SCHEMA, "generated_utc": _utc(),
            "source_scope": list(ALLOWED), "candidate_pr_count": len(result),
            "unique_mapped_patterns": len(groups), "groups": dict(sorted(groups.items())),
            "rules_promoted": 0, "patches_independently_tested": 0,
            "production_approved": False, "live_checked": verify_live, "items": result}


def _persist(root: Path, result: dict) -> dict:
    runtime, _ = _repo_paths(root)
    dest = runtime / "reviews"
    if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
        raise ReviewError("unsafe reviews directory")
    dest.mkdir(exist_ok=True)
    db_path = runtime / "review_candidates.sqlite3"
    out = dest / "candidate_review_v1.json"
    if out.is_symlink():
        raise ReviewError("unsafe review output symlink")
    if db_path.is_symlink() or (db_path.exists() and not db_path.is_file()):
        raise ReviewError("unsafe review database")
    # Separate DB: the existing public_miner.sqlite3 is never mutated here.
    with closing(sqlite3.connect(db_path, timeout=10)) as db:
        with db:
            db.execute("""CREATE TABLE IF NOT EXISTS review_candidates (
                source TEXT NOT NULL, pr_number INTEGER NOT NULL,
                pattern_id TEXT, canonical_pr_number INTEGER,
                source_check TEXT NOT NULL, release_tag TEXT,
                release_check TEXT NOT NULL, review_state TEXT NOT NULL,
                checked_utc TEXT NOT NULL, approval INTEGER NOT NULL CHECK(approval = 0),
                PRIMARY KEY(source, pr_number)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS review_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, checked_utc TEXT NOT NULL,
                candidate_count INTEGER NOT NULL, unique_patterns INTEGER NOT NULL,
                live_checked INTEGER NOT NULL, rules_promoted INTEGER NOT NULL CHECK(rules_promoted = 0)
            )""")
            for item in result["items"]:
                db.execute("""INSERT INTO review_candidates
                    (source, pr_number, pattern_id, canonical_pr_number, source_check,
                     release_tag, release_check, review_state, checked_utc, approval)
                    VALUES (?,?,?,?,?,?,?,?,?,0)
                    ON CONFLICT(source, pr_number) DO UPDATE SET
                    pattern_id=excluded.pattern_id,
                    canonical_pr_number=excluded.canonical_pr_number,
                    source_check=excluded.source_check, release_tag=excluded.release_tag,
                    release_check=excluded.release_check, review_state=excluded.review_state,
                    checked_utc=excluded.checked_utc, approval=0""",
                    (item["source"], item["pr_number"], item["pattern_id"],
                     item["canonical_pr_number"], item["source_check"],
                     item["release_tag"], item["release_check"],
                     item["review_state"], result["generated_utc"]))
            db.execute("INSERT INTO review_runs (checked_utc, candidate_count, unique_patterns, live_checked, rules_promoted) VALUES (?,?,?,?,0)",
                       (result["generated_utc"], result["candidate_pr_count"],
                        result["unique_mapped_patterns"], int(result["live_checked"])))
    # Atomic replacement of generated review receipt, with no upstream raw code.
    data = (json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=".ucie_review_", suffix=".tmp", dir=dest)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, out)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {"schema": RESULT_SCHEMA, "state": "REVIEW_CANDIDATE_ONLY",
            "source_prs": result["candidate_pr_count"], "mapped_unique_patterns": result["unique_mapped_patterns"],
            "live_checked": result["live_checked"], "rules_promoted": 0, "production_approved": False,
            "receipt": "runtime/reviews/candidate_review_v1.json", "review_db": "runtime/review_candidates.sqlite3"}


def review_and_store(root: Path, *, verify_live: bool = False, fetch=public_read_only_get) -> dict:
    return _persist(root, analyze(root, verify_live=verify_live, fetch=fetch))
