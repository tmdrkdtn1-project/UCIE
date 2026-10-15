"""Stage 14: public official docs, published releases and published security advisories.

One fixed allowlisted upstream/source per opted-in existing UCIE hour:
up to 3 anonymous GETs and bounded, hash-only local metadata. No upstream
source text, prompt, release notes or advisory descriptions are persisted.
Archive of official documents is a history of OBSERVED hashes, not an
attestation of old website versions or exhaustive public historical coverage.
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

from .core import NoRedirect
from .public_discovery import SOURCES, DiscoveryError, _utc
from .public_evidence_routes import DOC_ENDPOINTS

DB_NAME = "stage14_official_public_sources.sqlite3"
OPT_IN_FILE = "stage14_official_opt_in.txt"
OPT_IN_TOKEN = "UCIE_STAGE14_OFFICIAL_OPT_IN_V1"
APP_ID = 0x55433134
SCHEMA = 1
RELEASE_PAGE_CAP = 100
BUDGET_FLOOR = 12
BYTE_CAP = 1_000_000
RECORD_CAP = 20000
SHA256_HEX = re.compile("[a-f0-9]{64}")
GHSA = re.compile("GHSA-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}", re.I)
SEVERITIES = {"low", "moderate", "medium", "high", "critical", "unknown"}


def _path(root):
    root = Path(root)
    if root.name.casefold() != "ucie" or not root.is_dir() or root.is_symlink():
        raise DiscoveryError("UCIE root required")
    runtime = root / "runtime"
    if runtime.is_symlink() or not runtime.is_dir():
        raise DiscoveryError("safe UCIE runtime required")
    file = runtime / DB_NAME
    if file.is_symlink() or (file.exists() and not file.is_file()):
        raise DiscoveryError("unsafe official metadata ledger path")
    return file


def _opted_in(root):
    marker = _path(root).parent / OPT_IN_FILE
    if marker.is_symlink():
        raise DiscoveryError("unsafe official-source opt-in link")
    if not marker.exists():
        return False
    if not marker.is_file() or marker.stat().st_size > 100:
        raise DiscoveryError("invalid official-source opt-in file")
    if marker.read_text("utf-8").strip() != OPT_IN_TOKEN:
        raise DiscoveryError("unapproved official-source marker")
    return True


def official_urls(source, release_page=1):
    if (source not in SOURCES or type(release_page) is not int
            or not 1 <= release_page <= RELEASE_PAGE_CAP):
        raise DiscoveryError("unapproved public source or release page")
    api = f"https://api.github.com/repos/{source}"
    return (
        f"{api}/releases?per_page=10&page={release_page}",
        f"{api}/security-advisories?state=published&per_page=10",
        DOC_ENDPOINTS[source][0],
    )


def fetch_official_public(url):
    """Single fixed public GET; return bytes and inspected rate budget only."""
    allowed = set()
    for source in SOURCES:
        for page in range(1, RELEASE_PAGE_CAP + 1):
            allowed.add(official_urls(source, page)[0])
        _, advisory, doc = official_urls(source)
        allowed.add(advisory)
        allowed.add(doc)
    if not isinstance(url, str) or url not in allowed:
        raise DiscoveryError("official URL outside approved routes")
    req = urllib.request.Request(url, headers={
        "User-Agent": "UCIE-OFFICIAL-PUBLIC-EVIDENCE/0.1",
        "Accept": "application/vnd.github+json" if url.startswith("https://api.github.com/") else "text/html, text/plain",
        "X-GitHub-Api-Version": "2022-11-28",
    }, method="GET")
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=12) as rsp:
            if rsp.status != 200:
                raise DiscoveryError("official upstream response unavailable")
            mime = rsp.headers.get("Content-Type", "").lower()
            expect_json = url.startswith("https://api.github.com/")
            if expect_json and "json" not in mime:
                raise DiscoveryError("non-JSON GitHub public API response")
            if not expect_json and not any(x in mime for x in ("text/html", "text/plain")):
                raise DiscoveryError("unexpected official documentation response type")
            raw = rsp.read(BYTE_CAP + 1)
            rem = rsp.headers.get("X-RateLimit-Remaining")
    except (OSError, TimeoutError, urllib.error.HTTPError,
            urllib.error.URLError) as exc:
        raise DiscoveryError("bounded official public source unavailable") from exc
    if len(raw) > BYTE_CAP:
        raise DiscoveryError("official response too large")
    if rem is not None:
        if len(rem) > 6 or not rem.isascii() or not rem.isdecimal():
            raise DiscoveryError("untrusted upstream API quota header")
        remaining = int(rem)
    else:
        remaining = None
    return raw, remaining


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _json_records(raw, max_rows=10):
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise DiscoveryError("invalid bounded official JSON") from exc
    if not isinstance(value, list) or len(value) > max_rows:
        raise DiscoveryError("invalid official JSON row count")
    return value


def _release_rows(source, raw):
    records = []
    seen = set()
    for release in _json_records(raw):
        if not isinstance(release, dict):
            raise DiscoveryError("invalid published release record")
        ident = release.get("id")
        tag = release.get("tag_name")
        published = release.get("published_at")
        if release.get("draft") is True or release.get("prerelease") is True:
            continue
        if (type(ident) is not int or ident < 1 or ident in seen
                or not isinstance(tag, str) or not 1 <= len(tag) <= 128
                or not isinstance(published, str)):
            raise DiscoveryError("invalid official published release metadata")
        _utc(published)
        seen.add(ident)
        # No release body/title/asset URL or untrusted tag string retained.
        digest = _sha(json.dumps(
            [source, ident, tag, published], ensure_ascii=True,
            separators=(",", ":")).encode("ascii"))
        records.append(("release", source, str(ident), digest, published,
                        "PUBLIC_METADATA_UNVERIFIED"))
    return records


def _advisory_rows(source, raw):
    records = []
    seen = set()
    for advisory in _json_records(raw):
        if not isinstance(advisory, dict):
            raise DiscoveryError("invalid public security advisory metadata")
        ident = advisory.get("ghsa_id")
        published = advisory.get("published_at")
        severity = advisory.get("severity")
        state = advisory.get("state")
        if (not isinstance(ident, str) or not GHSA.fullmatch(ident)
                or ident in seen or state != "published"
                or not isinstance(published, str)
                or not isinstance(severity, str)
                or severity.lower() not in SEVERITIES):
            raise DiscoveryError("invalid published GHSA metadata")
        _utc(published)
        seen.add(ident)
        digest = _sha(json.dumps(
            [source, ident, severity.lower(), published], ensure_ascii=True,
            separators=(",", ":")).encode("ascii"))
        records.append(("advisory", source, ident.upper(), digest, published,
                        "PUBLIC_METADATA_UNVERIFIED"))
    return records


def _schema(db, *, new):
    ident = db.execute("PRAGMA application_id").fetchone()[0]
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if new:
        if ident or version or db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]:
            raise DiscoveryError("unrecognized official public metadata DB")
        db.execute("""CREATE TABLE official_revision (
            evidence_kind TEXT NOT NULL, source TEXT NOT NULL,
            upstream_reference TEXT NOT NULL, content_sha256 TEXT NOT NULL,
            observed_or_published_utc TEXT NOT NULL, review_state TEXT NOT NULL
            CHECK(review_state='PUBLIC_METADATA_UNVERIFIED'),
            PRIMARY KEY(evidence_kind, source, upstream_reference, content_sha256)
        ) WITHOUT ROWID""")
        db.execute("""CREATE TABLE official_cursor (
            source TEXT PRIMARY KEY, release_page INTEGER NOT NULL
                CHECK(release_page BETWEEN 1 AND 101),
            release_state TEXT NOT NULL CHECK(release_state IN
                ('ACTIVE','EXHAUSTED','MAX_DEPTH_REACHED'))
        ) WITHOUT ROWID""")
        db.execute("""CREATE TABLE cycle_state (
            slot INTEGER PRIMARY KEY CHECK(slot=1),
            source_index INTEGER NOT NULL CHECK(source_index BETWEEN 0 AND 4)
        ) WITHOUT ROWID""")
        db.executemany("INSERT INTO official_cursor VALUES (?,1,'ACTIVE')",
                       ((source,) for source in SOURCES))
        db.execute("INSERT INTO cycle_state VALUES (1,0)")
        db.execute(f"PRAGMA application_id={APP_ID}")
        db.execute(f"PRAGMA user_version={SCHEMA}")
    else:
        if ident != APP_ID or version != SCHEMA:
            raise DiscoveryError("wrong official source database identity")
        objects = set(db.execute("""
            SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'
        """).fetchall())
        if objects != {("table", "official_revision"),
                       ("table", "official_cursor"), ("table", "cycle_state")}:
            raise DiscoveryError("extra or missing official DB objects")
        expected = {
            "official_revision": ("evidence_kind", "source", "upstream_reference",
                                  "content_sha256", "observed_or_published_utc", "review_state"),
            "official_cursor": ("source", "release_page", "release_state"),
            "cycle_state": ("slot", "source_index"),
        }
        for table, expected_columns in expected.items():
            got = tuple(x[1] for x in db.execute(f"PRAGMA table_info({table})"))
            if got != expected_columns:
                raise DiscoveryError("official database unexpected columns")
        source_rows = db.execute("SELECT source,release_page,release_state FROM official_cursor").fetchall()
        if (len(source_rows) != len(SOURCES)
                or {row[0] for row in source_rows} != set(SOURCES)
                or any(type(row[1]) is not int or not 1 <= row[1] <= 101
                       or row[2] not in ("ACTIVE", "EXHAUSTED", "MAX_DEPTH_REACHED")
                       for row in source_rows)):
            raise DiscoveryError("official source cursors corrupt")
        slot = db.execute("SELECT slot,source_index FROM cycle_state").fetchall()
        if (len(slot) != 1 or slot[0][0] != 1
                or type(slot[0][1]) is not int or not 0 <= slot[0][1] < len(SOURCES)):
            raise DiscoveryError("invalid official cycle cursor")
    if db.execute("PRAGMA quick_check").fetchone() != ("ok",):
        raise DiscoveryError("official metadata sqlite integrity failure")


def inspect_official_sources(root):
    path = _path(root)
    if not path.exists():
        return {"status": "STAGE14_OFFICIAL_ABSENT", "revisions": 0,
                "approved_rules": 0, "production_approved": False}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro",
                                 uri=True, timeout=3)) as db:
        db.execute("PRAGMA query_only=ON")
        _schema(db, new=False)
        rows = db.execute("""
            SELECT evidence_kind, source, count(*)
            FROM official_revision GROUP BY evidence_kind,source
        """).fetchall()
        count = db.execute("SELECT COUNT(*) FROM official_revision").fetchone()[0]
        index = db.execute("SELECT source_index FROM cycle_state WHERE slot=1").fetchone()[0]
        invalid = db.execute("""
            SELECT count(*) FROM official_revision
            WHERE review_state <> 'PUBLIC_METADATA_UNVERIFIED'
        """).fetchone()[0]
    if count > RECORD_CAP or invalid:
        raise DiscoveryError("invalid official public evidence inventory")
    return {
        "status": "STAGE14_OFFICIAL_METADATA_INSPECTED_NO_GO",
        "revisions": count, "by_kind_source": [
            {"kind": kind, "source": source, "count": n}
            for kind, source, n in rows],
        "next_selected_source": SOURCES[index],
        "approved_rules": 0, "production_approved": False,
    }


def optional_official_evidence_cycle(root, *, fetch=fetch_official_public):
    path = _path(root)
    if not _opted_in(root):
        return {"status": "STAGE14_OFFICIAL_DISABLED",
                "approved_rules": 0, "production_approved": False}
    is_new = not path.exists()
    try:
        with closing(sqlite3.connect(path.as_uri() + ("?mode=rwc" if is_new else "?mode=rw"),
                                     uri=True, timeout=3)) as db:
            db.execute("BEGIN IMMEDIATE")
            _schema(db, new=is_new)
            source_index = db.execute(
                "SELECT source_index FROM cycle_state WHERE slot=1").fetchone()[0]
            source = SOURCES[source_index]
            page, state = db.execute(
                "SELECT release_page,release_state FROM official_cursor WHERE source=?",
                (source,)).fetchone()
            db.commit()
            release_url, advisory_url, doc_url = official_urls(
                source, min(page, RELEASE_PAGE_CAP))
            todo = (("release", release_url), ("advisory", advisory_url),
                    ("document", doc_url))
            requests, changed, failures, paused = 0, 0, [], False
            for kind, url in todo:
                if kind == "release" and state != "ACTIVE":
                    continue
                try:
                    raw, remaining = fetch(url)
                    if (not isinstance(raw, bytes)
                            or len(raw) > BYTE_CAP
                            or (remaining is not None and
                                (type(remaining) is not int or remaining < 0))):
                        raise DiscoveryError("invalid official public transport")
                    if kind == "release":
                        records = _release_rows(source, raw)
                    elif kind == "advisory":
                        records = _advisory_rows(source, raw)
                    else:
                        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
                        records = [("document", source, "pinned-doc-url",
                                    _sha(raw), stamp, "PUBLIC_METADATA_UNVERIFIED")]
                    requests += 1
                    db.execute("BEGIN IMMEDIATE")
                    try:
                        count = db.execute("SELECT COUNT(*) FROM official_revision").fetchone()[0]
                        if count + len(records) > RECORD_CAP:
                            raise DiscoveryError("bounded official metadata ledger full")
                        before = db.total_changes
                        db.executemany("INSERT OR IGNORE INTO official_revision VALUES (?,?,?,?,?,?)",
                                       records)
                        changed += db.total_changes - before
                        if kind == "release":
                            next_page = page + 1
                            next_state = ("EXHAUSTED" if len(_json_records(raw)) < 10 else
                                          "MAX_DEPTH_REACHED" if page == RELEASE_PAGE_CAP
                                          else "ACTIVE")
                            db.execute("""UPDATE official_cursor SET release_page=?,
                                       release_state=? WHERE source=?""",
                                       (next_page, next_state, source))
                        db.commit()
                    except Exception:
                        db.rollback()
                        raise
                    if remaining is not None and remaining < BUDGET_FLOOR:
                        paused = True
                        break
                except (DiscoveryError, ValueError):
                    failures.append(kind)
                    continue
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE cycle_state SET source_index=? WHERE slot=1",
                       ((source_index + 1) % len(SOURCES),))
            db.commit()
    except sqlite3.DatabaseError as exc:
        raise DiscoveryError("isolated official evidence metadata DB failed") from exc
    return {
        "status": ("STAGE14_OFFICIAL_PARTIAL_NO_GO" if failures
                   else "STAGE14_OFFICIAL_RATE_PAUSED_NO_GO" if paused
                   else "STAGE14_OFFICIAL_OBSERVED_NO_GO"),
        "source": source,
        "official_gets": requests,
        "new_metadata_revisions": changed,
        "unavailable_evidence_kinds": failures,
        "rate_budget_paused": paused,
        "source_scope": list(SOURCES),
        "raw_external_text_retained": False,
        "operating_dbs_written": False,
        "rules_promoted": 0,
        "model_weights_updated": False,
        "production_approved": False,
    }
