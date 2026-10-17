"""UCIE Stage 13: bounded historical public upstream metadata intake.

Actual external backfill beyond the latest-page miner: five *approved* public
repositories, one older PR page/source/cycle, capped at 500 pages/source.
Anonymous GitHub API GET only; no private repositories, auth, third-party
execution, raw patches, full upstream text or auto-approved rules.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import urllib.error
import urllib.request

from .core import NoRedirect, MiningError
from .public_discovery import (
    SOURCES, SOURCE_SKILL, CATEGORIES, DiscoveryError, PR_CAP, SHA40,
    MAX_TITLE, _utc,
)

DB_NAME = "stage13_external_public_history.sqlite3"
OPT_IN_FILE = "stage13_history_opt_in.txt"
OPT_IN_TOKEN = "UCIE_STAGE13_HISTORY_OPT_IN_V1"
SCHEMA = 1
APP_ID = 0x55433133
MAX_PAGES = 500
MAX_STORED = 80000
MAX_BYTES = 900_000
MIN_REMAINING = 12
ALLOWED_TAGS = tuple(CATEGORIES)
SHA64 = re.compile(r"[a-f0-9]{64}")


def _root_path(root: Path) -> Path:
    root = Path(root)
    if root.name.casefold() != "ucie" or not root.is_dir() or root.is_symlink():
        raise DiscoveryError("dedicated UCIE checkout required")
    runtime = root / "runtime"
    if not runtime.is_dir() or runtime.is_symlink():
        raise DiscoveryError("safe existing UCIE runtime required")
    path = runtime / DB_NAME
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise DiscoveryError("unsafe dedicated public history DB")
    return path


def _marker_enabled(root: Path) -> bool:
    runtime = _root_path(root).parent
    marker = runtime / OPT_IN_FILE
    if marker.is_symlink():
        raise DiscoveryError("unsafe history collector opt-in")
    if not marker.exists():
        return False
    if not marker.is_file() or marker.stat().st_size > 100:
        raise DiscoveryError("unsafe history collector marker")
    if marker.read_text("utf-8").strip() != OPT_IN_TOKEN:
        raise DiscoveryError("incorrect history collector opt-in")
    return True


def public_history_url(source: str, page: int) -> str:
    if (source not in SOURCES or type(page) is not int
            or not 1 <= page <= MAX_PAGES):
        raise DiscoveryError("out-of-scope public history source/page")
    return (f"https://api.github.com/repos/{source}/pulls?"
            f"state=closed&sort=updated&direction=desc&per_page=20&page={page}")


def fetch_public_history_page(url: str) -> tuple[list, int | None]:
    """One anonymous GET to exact pinned five-repo historical PR route."""
    if not isinstance(url, str) or url not in {
        public_history_url(source, page)
        for source in SOURCES for page in range(1, MAX_PAGES + 1)
    }:
        raise DiscoveryError("non-approved historical GitHub API URL")
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "UCIE-PUBLIC-HISTORY-READONLY/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }, method="GET")
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=12) as resp:
            if resp.status != 200 or "json" not in resp.headers.get("Content-Type", ""):
                raise DiscoveryError("unexpected historical feed status/content")
            raw = resp.read(MAX_BYTES + 1)
            rem = resp.headers.get("X-RateLimit-Remaining")
    except (urllib.error.HTTPError, urllib.error.URLError,
            TimeoutError, OSError, MiningError) as exc:
        raise DiscoveryError("approved historical feed unavailable or rate-limited") from exc
    if len(raw) > MAX_BYTES:
        raise DiscoveryError("oversized historical public feed")
    try:
        rows = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise DiscoveryError("invalid historical public feed JSON") from exc
    if not isinstance(rows, list) or len(rows) > PR_CAP:
        raise DiscoveryError("unexpected historical PR page size")
    if rem is None:
        remaining = None
    elif not rem.isascii() or not rem.isdecimal() or len(rem) > 6:
        raise DiscoveryError("invalid GitHub rate limit header")
    else:
        remaining = int(rem)
    return rows, remaining


def _metadata(source: str, rows: list, *, now: datetime) -> list[tuple]:
    if source not in SOURCES or not isinstance(rows, list) or len(rows) > PR_CAP:
        raise DiscoveryError("unsupported approved historical PR feed")
    out = []
    seen = set()
    for raw in rows:
        if not isinstance(raw, dict):
            raise DiscoveryError("invalid upstream PR metadata")
        n = raw.get("number")
        if type(n) is not int or not 1 <= n <= 999999999 or n in seen:
            raise DiscoveryError("invalid or duplicate upstream PR")
        seen.add(n)
        # The public closed-PR feed contains unmerged PRs. They are not
        # candidates and their unbounded titles must not poison an otherwise
        # valid historical page (git/git PR #1774 had 419 title characters).
        # Keep the strict title limit for *merged* evidence admitted below.
        if raw.get("merged_at") is None:
            continue
        title = raw.get("title")
        if type(title) is not str or not 1 <= len(title) <= MAX_TITLE:
            raise DiscoveryError("invalid merged upstream PR title")
        merged_at = raw["merged_at"]
        merged = _utc(merged_at)
        base = raw.get("base")
        repo = base.get("repo") if isinstance(base, dict) else None
        sha = raw.get("merge_commit_sha")
        url = f"https://github.com/{source}/pull/{n}"
        if (merged > now or raw.get("html_url") != url
                or not isinstance(repo, dict) or repo.get("full_name") != source
                or not isinstance(sha, str) or not SHA40.fullmatch(sha)):
            raise DiscoveryError("untrusted merge identity in upstream page")
        tags = sorted(name for name, rex in CATEGORIES.items() if rex.search(title))
        if not tags:
            continue
        title_hash = hashlib.sha256(title.encode("utf-8")).hexdigest()
        # Only fixed labels and cryptographic digests leave the parser.
        evidence = hashlib.sha256(json.dumps(
            [source, n, sha, merged_at, title_hash, tags],
            separators=(",", ":"), ensure_ascii=True,
        ).encode("ascii")).hexdigest()
        out.append((source, n, sha, merged_at, title_hash, evidence,
                    SOURCE_SKILL[source], json.dumps(tags, separators=(",", ":")),
                    "UNVERIFIED_CANDIDATE_ONLY"))
    return out


def _schema(conn: sqlite3.Connection, *, new: bool) -> None:
    ident = conn.execute("PRAGMA application_id").fetchone()[0]
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if new:
        if ident or version or conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]:
            raise DiscoveryError("foreign database cannot be used as UCIE history")
        conn.execute("""CREATE TABLE upstream_history(
            source TEXT NOT NULL, pr_number INTEGER NOT NULL,
            merge_sha TEXT NOT NULL, merged_at TEXT NOT NULL,
            title_sha256 TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,
            skill_id TEXT NOT NULL, tags_json TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state='UNVERIFIED_CANDIDATE_ONLY'),
            PRIMARY KEY(source,pr_number,evidence_sha256)
        ) WITHOUT ROWID""")
        conn.execute("""CREATE TABLE history_cursor(
            source TEXT PRIMARY KEY, next_page INTEGER NOT NULL,
            scan_state TEXT NOT NULL CHECK(scan_state IN
                ('ACTIVE','EXHAUSTED','MAX_DEPTH_REACHED')),
            CHECK(next_page BETWEEN 1 AND 501)
        ) WITHOUT ROWID""")
        conn.execute(f"PRAGMA application_id={APP_ID}")
        conn.execute(f"PRAGMA user_version={SCHEMA}")
        conn.executemany(
            "INSERT INTO history_cursor VALUES (?,1,'ACTIVE')",
            ((source,) for source in SOURCES))
    else:
        if ident != APP_ID or version != SCHEMA:
            raise DiscoveryError("not a UCIE historical-public index")
        objects = conn.execute(
            "SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall()
        if set(objects) != {("table", "upstream_history"),
                            ("table", "history_cursor")}:
            raise DiscoveryError("unexpected public-history schema objects")
        expected = {
            "upstream_history": (
                "source", "pr_number", "merge_sha", "merged_at", "title_sha256",
                "evidence_sha256", "skill_id", "tags_json", "state"),
            "history_cursor": ("source", "next_page", "scan_state"),
        }
        for table, columns in expected.items():
            found = tuple(row[1] for row in conn.execute(
                f"PRAGMA table_info({table})").fetchall())
            if found != columns:
                raise DiscoveryError("unrecognized historical index columns")
        rows = conn.execute(
            "SELECT source,next_page,scan_state FROM history_cursor"
        ).fetchall()
        if (len(rows) != len(SOURCES) or set(source for source, _, _ in rows)
                != set(SOURCES)
                or any(type(page) is not int or not 1 <= page <= MAX_PAGES + 1
                       or state not in ("ACTIVE", "EXHAUSTED", "MAX_DEPTH_REACHED")
                       for _, page, state in rows)):
            raise DiscoveryError("invalid public-history cursors")
    if conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
        raise DiscoveryError("public-history sqlite integrity failure")


def inspect_external_history(root: Path) -> dict:
    path = _root_path(root)
    if not path.exists():
        return {"status": "EXTERNAL_PUBLIC_HISTORY_ABSENT",
                "indexed_evidence_revisions": 0, "by_source": {},
                "pages_scanned": 0, "approved_rules": 0,
                "persistent_writes": 0, "production_approved": False}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro",
                                 uri=True, timeout=3)) as conn:
        conn.execute("PRAGMA query_only=ON")
        _schema(conn, new=False)
        cursors = conn.execute(
            "SELECT source,next_page,scan_state FROM history_cursor ORDER BY source"
        ).fetchall()
        counts = conn.execute(
            "SELECT source,count(*) FROM upstream_history GROUP BY source"
        ).fetchall()
        total = conn.execute("SELECT count(*) FROM upstream_history").fetchone()[0]
        invalid = conn.execute("""
            SELECT count(*) FROM upstream_history
            WHERE state <> 'UNVERIFIED_CANDIDATE_ONLY'
        """).fetchone()[0]
    if invalid or total > MAX_STORED:
        raise DiscoveryError("untrusted candidate index content")
    return {"status": "EXTERNAL_PUBLIC_HISTORY_INDEX_INSPECTED_NO_GO",
            "indexed_evidence_revisions": total, "by_source": dict(counts),
            "source_cursors": {src: {"next_page": page, "state": state}
                               for src, page, state in cursors},
            "approved_rules": 0, "persistent_writes": 0,
            "production_approved": False}


def optional_external_history_backfill(root: Path, *, fetch=None) -> dict:
    """One strictly opt-in cursor-bounded five-source public archive cycle.

    Each successful page and its next-page cursor commit atomically. A remote
    failure stops the cycle immediately and leaves that page unchanged.
    """
    path = _root_path(root)
    if not _marker_enabled(root):
        return {"status": "STAGE13_EXTERNAL_HISTORY_DISABLED",
                "approved_rules": 0, "production_approved": False}
    if fetch is None:
        fetch = fetch_public_history_page
    new = not path.exists()
    now = datetime.now(timezone.utc)
    requests, added, examined, scanned = 0, 0, 0, []
    status = "EXTERNAL_HISTORY_BACKFILL_OK_NO_GO"
    failure_source, failure_category = None, None
    try:
        with closing(sqlite3.connect(path.as_uri() + ("?mode=rwc" if new else "?mode=rw"),
                                     uri=True, timeout=3)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            _schema(conn, new=new)
            conn.commit()
            for source in SOURCES:
                page, state = conn.execute(
                    "SELECT next_page,scan_state FROM history_cursor WHERE source=?",
                    (source,)).fetchone()
                if state != "ACTIVE":
                    continue
                url = public_history_url(source, page)
                try:
                    remote = fetch(url)
                    if (not isinstance(remote, tuple) or len(remote) != 2
                            or (remote[1] is not None and
                                (type(remote[1]) is not int or remote[1] < 0))):
                        raise DiscoveryError("invalid bounded public history transport receipt")
                    rows, remaining = remote
                except (DiscoveryError, ValueError):
                    status = "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO"
                    failure_source = source
                    failure_category = "FETCH_OR_RESPONSE_REJECTED"
                    break
                try:
                    candidates = _metadata(source, rows, now=now)
                except (DiscoveryError, ValueError):
                    # Never silently skip untrusted PR metadata or advance
                    # that source cursor past a rejected page.
                    status = "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO"
                    failure_source = source
                    failure_category = "PUBLIC_METADATA_REJECTED"
                    break
                conn.execute("BEGIN IMMEDIATE")
                try:
                    before = conn.total_changes
                    count = conn.execute("SELECT count(*) FROM upstream_history").fetchone()[0]
                    if count + len(candidates) > MAX_STORED:
                        raise DiscoveryError("bounded historical public index full")
                    conn.executemany("""INSERT OR IGNORE INTO upstream_history
                        VALUES (?,?,?,?,?,?,?,?,?)""", candidates)
                    delta = conn.total_changes - before
                    next_page = page + 1
                    next_state = ("EXHAUSTED" if len(rows) < PR_CAP else
                                  "MAX_DEPTH_REACHED" if page == MAX_PAGES else
                                  "ACTIVE")
                    conn.execute(
                        "UPDATE history_cursor SET next_page=?,scan_state=? WHERE source=?",
                        (next_page, next_state, source))
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                requests += 1
                added += delta
                examined += len(rows)
                scanned.append(source)
                if remaining is not None and remaining < MIN_REMAINING:
                    status = "EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO"
                    break
    except sqlite3.DatabaseError as exc:
        raise DiscoveryError("isolated historical-public index DB failure") from exc
    return {"status": status, "external_gets": requests,
            "failure_source": failure_source,
            "failure_category": failure_category,
            "public_pr_records_examined": examined,
            "new_unverified_evidence_revisions": added,
            "sources_scanned": scanned,
            "source_scope": list(SOURCES),
            "max_pages_per_source": MAX_PAGES,
            "raw_titles_or_patches_retained": False,
            "operating_miner_or_knowledge_written": False,
            "approved_rules": 0, "production_approved": False}
