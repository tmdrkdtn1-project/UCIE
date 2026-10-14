"""Small, constrained public GitHub fix miner. NEVER uses user GitHub credentials.

Only two immutable, independently owned upstream sources are examined.
Upstream text is untrusted; never executed, stored as private telemetry, or published.
Knowledge entries generated here are UNVERIFIED_CANDIDATE_ONLY.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable

PUBLIC_SOURCES = ("python/cpython", "PowerShell/PowerShell")
FIX_TERMS = re.compile(r"\b(fix|fixed|bug|regression|correct|repair|crash|exception)\b", re.I)
KST = timezone(timedelta(hours=9))
MAX_BODY = 1_000_000
MAX_FILES = 30


class MiningError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise MiningError("external API redirect rejected")


def _api_url(source: str, endpoint: str) -> str:
    if source not in PUBLIC_SOURCES:
        raise MiningError("source outside immutable third-party allowlist")
    if not re.fullmatch(r"(?:pulls\?state=closed&sort=updated&direction=desc&per_page=20|pulls/[1-9][0-9]*/files\?per_page=30)", endpoint):
        raise MiningError("endpoint outside limited read-only GitHub API")
    return "https://api.github.com/repos/" + source + "/" + endpoint


def fetch_public_json(url: str) -> object:
    if not isinstance(url, str) or not any(re.fullmatch(
            r"https://api\.github\.com/repos/" + re.escape(source) +
            r"/(?:pulls\?state=closed&sort=updated&direction=desc&per_page=20|"
            r"pulls/[1-9][0-9]*/files\?per_page=30|pulls/[1-9][0-9]*)", url)
            for source in PUBLIC_SOURCES):
        raise MiningError("request outside approved exact public API routes")
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "UCIE-PUBLIC-READ-ONLY/0.2"},
        method="GET",
    )
    # No project token or Authorization header; do not redirect to another host.
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=12) as response:
            if response.status != 200:
                raise MiningError("public API returned non-200")
            if "application/json" not in response.headers.get("Content-Type", ""):
                raise MiningError("unexpected API content type")
            data = response.read(MAX_BODY + 1)
            if len(data) > MAX_BODY:
                raise MiningError("API response exceeded hard size limit")
    except urllib.error.HTTPError as exc:
        raise MiningError("upstream HTTP error " + str(exc.code)) from exc
    except urllib.error.URLError as exc:
        raise MiningError("upstream communication error") from exc
    try:
        return json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise MiningError("invalid API JSON") from exc


def _db(repo_root: Path) -> sqlite3.Connection:
    """Only local UCIE runtime data; never an external path or user-project database."""
    runtime = repo_root / "runtime"
    if runtime.is_symlink():
        raise MiningError("runtime symlinks forbidden")
    if runtime.exists() and not runtime.is_dir():
        raise MiningError("runtime is not a directory")
    runtime.mkdir(exist_ok=True)
    target = runtime / "public_miner.sqlite3"
    if target.is_symlink():
        raise MiningError("database symlinks forbidden")
    conn = sqlite3.connect(str(target), timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS candidates (
        source TEXT NOT NULL,
        pr_number INTEGER NOT NULL,
        public_url TEXT NOT NULL,
        merged_at TEXT NOT NULL,
        evidence_sha256 TEXT NOT NULL,
        tags_json TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status = 'UNVERIFIED_CANDIDATE_ONLY'),
        PRIMARY KEY(source, pr_number)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS runs (
        run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        at_utc TEXT NOT NULL,
        sources_count INTEGER NOT NULL,
        added_candidates INTEGER NOT NULL,
        status TEXT NOT NULL
    )""")
    conn.commit()
    return conn


def _classify_changes(files: object) -> tuple[str, list[str]]:
    if not isinstance(files, list) or not 0 < len(files) <= MAX_FILES:
        raise MiningError("malformed or excessive files response")
    tags: set[str] = set()
    hashes = hashlib.sha256()
    for file in files:
        if not isinstance(file, dict):
            raise MiningError("invalid file metadata")
        filename, patch = file.get("filename"), file.get("patch", "")
        if not isinstance(filename, str) or len(filename) > 300:
            raise MiningError("invalid filename")
        if not isinstance(patch, str) or len(patch) > 50000:
            raise MiningError("oversized or malformed patch")
        hashes.update(hashlib.sha256(patch.encode("utf-8")).digest())
        lower = filename.lower().replace("\\", "/")
        if lower.endswith(".py"):
            tags.add("PYTHON_CHANGE")
        if lower.endswith((".ps1", ".psm1", ".psd1")):
            tags.add("POWERSHELL_CHANGE")
        if re.search(r"(?:^|/)(test|tests|testing)(?:/|_|\.|$)", lower):
            tags.add("TEST_CHANGE")
        plus_minus = [line for line in patch.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]
        if any(re.search(r"\b(?:except|finally|catch|throw|raise|erroraction)\b", line, re.I) for line in plus_minus):
            tags.add("ERROR_HANDLING_CHANGE")
        if any(re.search(r"^[+-]\s*(?:async\s+)?(?:def |function )", line) for line in plus_minus):
            tags.add("FUNCTION_SIGNATURE_CHANGE")
        if any(re.search(r"^[+-]\s*(?:import |from |using |require)", line) for line in plus_minus):
            tags.add("IMPORT_DEPENDENCY_CHANGE")
    if not tags:
        tags.add("UNCLASSIFIED_FIX")
    return hashes.hexdigest(), sorted(tags)


def mine_once(
    repo_root: Path,
    *,
    fetch: Callable[[str], object] = fetch_public_json,
    sources: tuple[str, ...] = PUBLIC_SOURCES,
    max_new_per_source: int = 2,
    crosscheck_origin: bool = False,
) -> dict:
    if type(crosscheck_origin) is not bool:
        raise MiningError("invalid provenance crosscheck flag")
    if any(source not in PUBLIC_SOURCES for source in sources) or not sources:
        raise MiningError("unapproved source")
    if type(max_new_per_source) is not int or not 1 <= max_new_per_source <= 5:
        raise MiningError("candidate cap outside 1..5")
    conn = _db(repo_root)
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    added = 0
    incomplete_provenance = 0
    public_pr_crosschecked = 0
    try:
        with conn:
            for source in sources:
                endpoint = "pulls?state=closed&sort=updated&direction=desc&per_page=20"
                results = fetch(_api_url(source, endpoint))
                if not isinstance(results, list) or len(results) > 20:
                    raise MiningError("malformed pull list")
                per_source = 0
                for item in results:
                    if not isinstance(item, dict):
                        raise MiningError("invalid pull record")
                    number = item.get("number")
                    title = item.get("title")
                    merged_at = item.get("merged_at")
                    if type(number) is not int or number < 1 or not isinstance(title, str) or len(title) > 1000:
                        raise MiningError("unexpected public pull record")
                    if not isinstance(merged_at, str) or not merged_at or not FIX_TERMS.search(title):
                        continue
                    if conn.execute("SELECT 1 FROM candidates WHERE source=? AND pr_number=?",
                                    (source, number)).fetchone():
                        continue
                    files = fetch(_api_url(source, "pulls/" + str(number) + "/files?per_page=30"))
                    # Local-only metadata gate. Never treats missing upstream facts as PASS.
                    from .adapter import inspect_collected_pr
                    evidence = inspect_collected_pr(source, item, files)
                    if evidence["status"] == "INCOMPLETE_PROVENANCE":
                        incomplete_provenance += 1
                    if crosscheck_origin:
                        from .public_provenance import crosscheck_pr_metadata
                        crosscheck_pr_metadata(source, item, fetch=fetch)
                        public_pr_crosschecked += 1
                    digest, tags = _classify_changes(files)
                    conn.execute(
                        "INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)",
                        (source, number, "https://github.com/" + source + "/pull/" + str(number),
                         merged_at, digest, json.dumps(tags), observed_at, "UNVERIFIED_CANDIDATE_ONLY"))
                    added += 1
                    per_source += 1
                    if per_source >= max_new_per_source:
                        break
            conn.execute(
                "INSERT INTO runs (at_utc, sources_count, added_candidates, status) VALUES (?,?,?,?)",
                (observed_at, len(sources), added, "COLLECTED_UNVERIFIED"))
    finally:
        conn.close()
    return {"status": "COLLECTED_UNVERIFIED", "sources_checked": len(sources),
            "new_candidates": added, "incomplete_provenance": incomplete_provenance,
            "public_pr_crosschecked": public_pr_crosschecked,
            "verification_pass": 0, "production_approved": False}


def report(repo_root: Path) -> Path:
    conn = _db(repo_root)
    try:
        total = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        group = conn.execute("SELECT source, COUNT(*) FROM candidates GROUP BY source ORDER BY source").fetchall()
        last = conn.execute("SELECT at_utc, added_candidates, status FROM runs ORDER BY run_id DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    now = datetime.now(KST)
    directory = repo_root / "runtime" / "reports"
    if directory.is_symlink():
        raise MiningError("report directory symlink forbidden")
    directory.mkdir(exist_ok=True)
    path = directory / (now.date().isoformat() + ".md")
    if path.is_symlink():
        raise MiningError("report symlink forbidden")
    lines = [
        "# UCIE public-source miner daily snapshot",
        "", "Date (KST): " + now.date().isoformat(),
        "Source class: independently owned public third-party repositories ONLY",
        "Validation status: UNVERIFIED_CANDIDATE_ONLY",
        "Promoted knowledge rules: 0",
        "Independent runtime tests of collected patches: 0",
        "Total candidate PRs (all time): " + str(total),
        "",
        "## Candidates per public source",
    ]
    lines.extend("- " + source + ": " + str(count) for source, count in group)
    lines += ["", "## Latest run",
              "No run yet" if last is None else "Time UTC: " + last[0] + "; newly observed: " + str(last[1]) + "; status: " + last[2],
              "", "No user projects, code, logs, credentials, or private data are read by this collector.",
              "No data is sent from any recipient project back to UCIE.",
              ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
