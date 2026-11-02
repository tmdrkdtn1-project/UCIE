"""UCIE-only bounded source batch delivery. Consent is not identity attestation.

GitHub CI + exact source bytes verified on every bundle; never run downloaded
code, change UCIE scheduler/DB, sign Rulepacks or access another project.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import urllib.request

SCHEMA = "UCIE_OWNER_SCOPED_DEV_QA_V1"
REPO = "tmdrkdtn1-project/UCIE"
WORKFLOW = ".github/workflows/stage1-offline-tests.yml"
GRANT_FILE = "grant.json"
CONSENT = "AUTHORIZE_UCIE_SCOPED_DEV_QA_ONLY"
SHA = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
SOURCE = re.compile(r"src/ucie_miner/[a-z][a-z0-9_]{2,60}\.py\Z")
TEST = re.compile(r"tests/test_ucie_[a-z0-9_]{3,60}\.py\Z")
PROTECTED = {"__init__.py", "__main__.py", "worker.py", "core.py",
             "runtime_pipeline.py", "pending_queue.py", "source_registry.py",
             "owner_scoped_batch_v1.py"}
JOBS = {f"Offline test / {osname} / Python {ver}"
        for osname in ("ubuntu-latest", "windows-latest")
        for ver in ("3.13", "3.15")}
MAX_FILES = 6
MAX_FILE_BYTES = 180000
MAX_TOTAL_BYTES = 600000


class ScopeError(ValueError):
    pass


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _date(value: object) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ScopeError("invalid UTC date")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ScopeError("invalid UTC date") from exc
    if parsed.utcoffset() != timedelta(0):
        raise ScopeError("non-UTC date")
    return parsed


def _safe_relative(path: object) -> str:
    if type(path) is not str or len(path) > 90 or "\\" in path:
        raise ScopeError("invalid relative source path")
    pure = PurePosixPath(path)
    if pure.is_absolute() or any(p in (".", "..") for p in path.split("/")):
        raise ScopeError("path traversal forbidden")
    if not (SOURCE.fullmatch(path) or TEST.fullmatch(path)):
        raise ScopeError("source path not in limited development scope")
    if pure.name in PROTECTED:
        raise ScopeError("protected UCIE operational source")
    return path


def validate_bundle(bundle: object) -> tuple[str, list[tuple[str, str, bytes]]]:
    if (type(bundle) is not dict or set(bundle) != {"schema", "commit_sha", "files"}
            or bundle["schema"] != "UCIE_PINNED_DEV_QA_BUNDLE_V1"
            or type(bundle["commit_sha"]) is not str
            or not COMMIT.fullmatch(bundle["commit_sha"])):
        raise ScopeError("invalid pinned UCIE batch")
    files = bundle["files"]
    if type(files) is not list or not 1 <= len(files) <= MAX_FILES:
        raise ScopeError("invalid bounded file count")
    result = []
    seen = set()
    total = 0
    for rec in files:
        if type(rec) is not dict or set(rec) != {"path", "before_sha256", "after_sha256", "content_b64"}:
            raise ScopeError("invalid source entry fields")
        name = _safe_relative(rec["path"])
        if name in seen:
            raise ScopeError("duplicate target")
        seen.add(name)
        before, after = rec["before_sha256"], rec["after_sha256"]
        if ((before != "ABSENT" and (type(before) is not str or not SHA.fullmatch(before)))
                or type(after) is not str or not SHA.fullmatch(after)
                or type(rec["content_b64"]) is not str
                or len(rec["content_b64"]) > 4 * MAX_FILE_BYTES // 3 + 8):
            raise ScopeError("invalid bounded source digest")
        try:
            data = base64.b64decode(rec["content_b64"], validate=True)
            data.decode("utf-8", "strict")
        except (ValueError, UnicodeError) as exc:
            raise ScopeError("invalid UTF-8 source bytes") from exc
        if (not data or len(data) > MAX_FILE_BYTES
                or b"\x00" in data or sha256(data).hexdigest() != after):
            raise ScopeError("source bytes do not match declared digest")
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise ScopeError("bundle exceeds total bytes")
        result.append((name, before, data))
    return bundle["commit_sha"], result


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ScopeError("GitHub API redirected: fail closed")


def _github_json(endpoint: str) -> dict:
    """Only repo-pinned public GitHub API; bounded bytes, no redirects/retry."""
    if not endpoint.startswith("https://api.github.com/repos/" + REPO + "/"):
        raise ScopeError("unapproved public API endpoint")
    request = urllib.request.Request(
        endpoint, headers={"Accept": "application/vnd.github+json",
                           "User-Agent": "UCIE-owner-scoped-dev-qa-v1"})
    response = urllib.request.build_opener(_NoRedirect()).open(request, timeout=8)
    with response:
        if response.status != 200:
            raise ScopeError("GitHub evidence unavailable")
        data = response.read(350001)
    if len(data) > 350000:
        raise ScopeError("oversized GitHub response")
    obj = json.loads(data)
    if type(obj) is not dict:
        raise ScopeError("unexpected GitHub response")
    return obj


def verify_github_ci_and_source_blobs(commit: str, file_shas: dict[str, str]) -> bool:
    """Live public GitHub CI and exact commit blobs, not a caller-supplied PASS."""
    if type(commit) is not str or not COMMIT.fullmatch(commit):
        raise ScopeError("invalid Git commit")
    if type(file_shas) is not dict or not 1 <= len(file_shas) <= MAX_FILES:
        raise ScopeError("invalid GitHub source list")
    for path, digest in file_shas.items():
        _safe_relative(path)
        if type(digest) is not str or SHA.fullmatch(digest) is None:
            raise ScopeError("invalid source digest")
    api = "https://api.github.com/repos/" + REPO + "/"
    runs = _github_json(api + "actions/runs?head_sha=" + commit + "&event=pull_request&per_page=10")
    eligible = [r for r in runs.get("workflow_runs", [])
                if type(r) is dict and r.get("head_sha") == commit
                and r.get("path") == WORKFLOW and r.get("status") == "completed"
                and r.get("conclusion") == "success"
                and isinstance(r.get("head_repository"), dict)
                and r["head_repository"].get("full_name") == REPO
                and type(r.get("id")) is int and r["id"] > 0]
    if len(eligible) != 1:
        raise ScopeError("exact successful UCIE CI run not uniquely established")
    jobs = _github_json(api + "actions/runs/" + str(eligible[0]["id"]) + "/jobs?per_page=100")
    jobrows = jobs.get("jobs")
    if type(jobrows) is not list or jobs.get("total_count", 0) > 100:
        raise ScopeError("GitHub CI matrix incomplete")
    passed = {j["name"] for j in jobrows if type(j) is dict
              and j.get("name") in JOBS and j.get("conclusion") == "success"
              and j.get("status") == "completed"}
    if passed != JOBS:
        raise ScopeError("four-platform UCIE matrix not fully passed")
    for path, digest in file_shas.items():
        rec = _github_json(api + "contents/" + path + "?ref=" + commit)
        if rec.get("encoding") != "base64" or type(rec.get("content")) is not str:
            raise ScopeError("GitHub source encoding unsupported")
        try:
            content = base64.b64decode(rec["content"], validate=False)
        except ValueError as exc:
            raise ScopeError("invalid GitHub source content") from exc
        if (sha256(content).hexdigest() != digest
                or rec.get("sha") != hashlib.sha1(
                    ("blob " + str(len(content)) + "\x00").encode("ascii") + content
                ).hexdigest()):
            raise ScopeError("GitHub exact commit source mismatch")
    return True


def _inside(root: Path, relative: str) -> Path:
    path = root
    for part in relative.split("/"):
        path = path / part
        if path.is_symlink():
            raise ScopeError("symlink rejected")
    if not path.parent.is_dir():
        raise ScopeError("target parent absent")
    return path


def _read_exact(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ScopeError("unsafe source or state file")
    return path.read_bytes()


def _atomic(path: Path, data: bytes) -> None:
    # Create in destination directory for os.replace atomicity on Windows.
    fd, tmp = tempfile.mkstemp(prefix=".ucie-qa-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _host_paths(root: Path, hub: Path) -> None:
    if os.name != "nt" or str(root).casefold() != "d:\\ucie" or str(hub).casefold() != "d:\\ucie_hub":
        raise ScopeError("owner host mode requires exact UCIE Windows roots")
    if root.is_symlink() or hub.is_symlink() or not root.is_dir() or not hub.is_dir():
        raise ScopeError("UCIE root invalid")


def _grant_path(hub: Path) -> Path:
    base = hub / "04_MIGRATION" / "UCIE_OWNER_SCOPED_QA_V1"
    if (not base.is_dir() or base.is_symlink() or
            base.parent.is_symlink()):
        raise ScopeError("grant directory absent or unsafe")
    return base / GRANT_FILE


def enroll(root: Path, hub: Path, *, consent: str, now: datetime | None = None,
           test_mode: bool = False) -> dict:
    if not test_mode:
        _host_paths(root, hub)
    if consent != CONSENT:
        raise ScopeError("explicit single-owner consent required")
    grant_path = _grant_path(hub)
    if grant_path.exists() or grant_path.is_symlink():
        raise ScopeError("existing grant cannot be silently overwritten")
    current = now or _now()
    grant = {"schema": SCHEMA, "status": "SCOPED_CONSENT_LOCAL_ONLY_NOT_IDENTITY_PROOF",
             "repo": REPO, "start_utc": current.isoformat().replace("+00:00", "Z"),
             "expires_utc": (current + timedelta(days=14)).isoformat().replace("+00:00", "Z"),
             "max_batches": 12, "used_batches": 0, "revoked": False,
             "allowed_class": "ONLY_SRC_AND_TESTS_BOUNDED_GITHUB_CI"}
    # Exclusive create: never replace a previous owner decision.
    fd = os.open(grant_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(_json_bytes(grant) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    return grant


def _grant(hub: Path, *, now: datetime | None = None) -> tuple[Path, dict]:
    path = _grant_path(hub)
    try:
        grant = json.loads(_read_exact(path, 2048))
    except (OSError, ValueError) as exc:
        raise ScopeError("grant unavailable or corrupt") from exc
    required = {"schema", "status", "repo", "start_utc", "expires_utc",
                "max_batches", "used_batches", "revoked", "allowed_class"}
    if (type(grant) is not dict or set(grant) != required or grant["schema"] != SCHEMA
            or grant["repo"] != REPO or grant["status"] != "SCOPED_CONSENT_LOCAL_ONLY_NOT_IDENTITY_PROOF"
            or grant["allowed_class"] != "ONLY_SRC_AND_TESTS_BOUNDED_GITHUB_CI"
            or type(grant["max_batches"]) is not int or grant["max_batches"] != 12
            or type(grant["used_batches"]) is not int or not 0 <= grant["used_batches"] < 12
            or type(grant["revoked"]) is not bool or grant["revoked"]):
        raise ScopeError("grant denied, exhausted or forged")
    current = now or _now()
    if not _date(grant["start_utc"]) <= current < _date(grant["expires_utc"]):
        raise ScopeError("grant not currently valid")
    if _date(grant["expires_utc"]) - _date(grant["start_utc"]) > timedelta(days=14):
        raise ScopeError("grant extended beyond fixed window")
    return path, grant


@contextmanager
def _exclusive_scope_lock(hub: Path):
    """Refuse simultaneous transactions and stale locks; never steal a lease."""
    lock = _grant_path(hub).parent / "apply.lock"
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ScopeError("another batch or unrecovered lock exists") from exc
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def apply_verified_batch(root: Path, hub: Path, bundle: dict,
                         *, verify_ci_and_sources, now: datetime | None = None,
                         test_mode: bool = False, fail_after: int | None = None) -> dict:
    """Protect scoped delivery with an exclusive local one-batch lock."""
    with _exclusive_scope_lock(hub):
        return _apply_locked(root, hub, bundle,
                             verify_ci_and_sources=verify_ci_and_sources,
                             now=now, test_mode=test_mode,
                             fail_after=fail_after)


def _apply_locked(root: Path, hub: Path, bundle: dict,
                  *, verify_ci_and_sources, now: datetime | None = None,
                  test_mode: bool = False, fail_after: int | None = None) -> dict:
    """Apply one reviewed CI-successful commit, rollback on Python exceptions.

    verify_ci_and_sources is a *trusted host/backend callback*, not a boolean
    supplied in the bundle. It MUST independently check GitHub CI's complete
    Windows/Linux 3.13/3.15 matrix AND each path's exact commit blob.
    """
    if not test_mode:
        _host_paths(root, hub)
    commit, files = validate_bundle(bundle)
    gp, grant = _grant(hub, now=now)
    current = []
    for rel, expected, data in files:
        target = _inside(root, rel)
        before = target.read_bytes() if target.is_file() else None
        if (before is None and expected != "ABSENT") or (before is not None and expected == "ABSENT"):
            raise ScopeError("unexpected target existence")
        if before is not None and sha256(before).hexdigest() != expected:
            raise ScopeError("local source drift: no overwrite")
        current.append((target, before, data))
    # No host modification before mandatory non-caller-supplied proof.
    if verify_ci_and_sources(commit, {rel: sha256(data).hexdigest() for rel, _, data in files}) is not True:
        raise ScopeError("trusted exact commit CI and source evidence missing")
    batch_id = sha256(_json_bytes(bundle)).hexdigest()
    backup_dir = gp.parent / ("batch_" + batch_id[:24])
    if backup_dir.exists() or backup_dir.is_symlink():
        raise ScopeError("batch already attempted: manual receipt review required")
    backup_dir.mkdir()
    written = []
    # For recovery after a host crash: copies and manifest are durable before any writes.
    for i, (target, before, data) in enumerate(current):
        if before is not None:
            _atomic(backup_dir / (str(i) + ".bak"), before)
    manifest = {"schema": SCHEMA, "batch_id": batch_id,
                "commit_sha": commit, "files": [t.name for t, _, _ in current],
                "state": "PREPARED_OR_RECOVERY_REQUIRED"}
    _atomic(backup_dir / "journal.json", _json_bytes(manifest) + b"\n")
    try:
        for i, (target, before, data) in enumerate(current):
            _atomic(target, data)
            written.append((target, before, data))
            if fail_after is not None and len(written) == fail_after:
                raise OSError("injected rollback test")
        grant["used_batches"] += 1
        _atomic(gp, _json_bytes(grant) + b"\n")
        manifest["state"] = "APPLIED_UNAPPROVED_CODE_ONLY"
        _atomic(backup_dir / "journal.json", _json_bytes(manifest) + b"\n")
    except Exception:
        for target, before, data in reversed(written):
            if target.read_bytes() != data:
                raise ScopeError("concurrent local edit: manual recovery required")
            if before is None:
                target.unlink()
            else:
                _atomic(target, before)
        manifest["state"] = "ROLLED_BACK_AFTER_EXCEPTION"
        _atomic(backup_dir / "journal.json", _json_bytes(manifest) + b"\n")
        raise
    return {"schema": SCHEMA, "status": "SCOPED_CODE_SYNCED_NO_RUNTIME_OR_DEPLOYMENT_APPROVAL",
            "files_changed": len(files), "batch_id": batch_id, "source_commit": commit,
            "github_ci_verified_by_backend": True, "operating_db_modified": False,
            "scheduler_modified": False, "auto_promoted": False,
            "code_executed_after_sync": False, "owner_identity_attested": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE scoped consent preflight (no live apply CLI)")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if not args.status:
        parser.error("only --status is supported; host bridge must provide verified CI callback")
    print(json.dumps({"schema": SCHEMA, "status": "HOST_BRIDGE_INTEGRATION_REQUIRED_NO_AUTONOMOUS_APPLY",
                      "consent_granted_by_import": False, "host_changed": False,
                      "scheduler_changed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
