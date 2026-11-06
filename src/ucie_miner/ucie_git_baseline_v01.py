"""UCIE-only read-only Git intake baseline; no staging, file reads, or release."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SCHEMA = "UCIE_GIT_BASELINE_V01"
MAX_STATUS_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 50000
CATEGORIES = (
    "source_review",
    "test_review",
    "script_review",
    "documentation_review",
    "sensitive_or_runtime_hold",
    "other_hold",
)


class BaselineError(ValueError):
    """A fail-closed read-only baseline error."""


def _path(raw: bytes) -> str:
    if not raw:
        raise BaselineError("EMPTY_PATH")
    value = raw.decode("utf-8", errors="surrogateescape").replace("\\", "/")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise BaselineError("ABSOLUTE_PATH")
    if any(segment in ("", ".", "..") for segment in value.split("/")):
        raise BaselineError("UNSAFE_RELATIVE_PATH")
    return value


def parse_porcelain_v1_z(data: bytes) -> list[tuple[str, str]]:
    """Parse fixed Git porcelain -z, including the extra source of R/C records."""
    if not isinstance(data, bytes) or len(data) > MAX_STATUS_BYTES:
        raise BaselineError("INVALID_OR_OVERSIZED_STATUS")
    if not data:
        return []
    if not data.endswith(b"\0"):
        raise BaselineError("TRUNCATED_STATUS")
    fields = data[:-1].split(b"\0")
    result: list[tuple[str, str]] = []
    index = 0
    while index < len(fields):
        record = fields[index]
        if len(record) < 4 or record[2:3] != b" ":
            raise BaselineError("BAD_PORCELAIN_RECORD")
        try:
            state = record[:2].decode("ascii")
        except UnicodeDecodeError as exc:
            raise BaselineError("BAD_STATE") from exc
        if state != "??" and state != "!!" and not all(
            char in " MADRCUT?!"
            for char in state
        ):
            raise BaselineError("BAD_STATE")
        path = _path(record[3:])
        if "R" in state or "C" in state:
            index += 1
            if index >= len(fields):
                raise BaselineError("MISSING_RENAME_OR_COPY_ORIGIN")
            _path(fields[index])
        result.append((state, path))
        if len(result) > MAX_RECORDS:
            raise BaselineError("TOO_MANY_STATUS_RECORDS")
        index += 1
    return result


def classify_untracked(path: str) -> str:
    segments = path.casefold().replace("\\", "/").split("/")
    name = segments[-1]
    if (
        any(s in (".ucie_bridge_state", ".venv", ".git", "runtime",
                  "__pycache__", ".pytest_cache", ".mypy_cache") for s in segments)
        or name.startswith(".env")
        or name.endswith((".bak", ".tmp", ".temp", ".log", ".pem", ".key",
                          ".pfx", ".p12", ".sqlite", ".sqlite3", ".db"))
        or any(keyword in name for keyword in
               ("credential", "secret", "password", "private_key", "token"))
    ):
        return "sensitive_or_runtime_hold"
    if segments[0] == "src" and name.endswith(".py"):
        return "source_review"
    if segments[0] == "tests" and name.endswith((".py", ".ps1")):
        return "test_review"
    if segments[0] == "scripts" and name.endswith((".py", ".ps1")):
        return "script_review"
    if segments[0] == "docs" and name.endswith((".md", ".json")):
        return "documentation_review"
    return "other_hold"


def summarize(data: bytes) -> dict[str, object]:
    records = parse_porcelain_v1_z(data)
    categories = {key: 0 for key in CATEGORIES}
    tracked = 0
    staged = 0
    untracked = 0
    ignored = 0
    for state, path in records:
        if state == "??":
            untracked += 1
            categories[classify_untracked(path)] += 1
        elif state == "!!":
            ignored += 1
        else:
            tracked += 1
            if state[0] not in (" ", "?", "!"):
                staged += 1
    return {
        "schema": SCHEMA,
        "status": "UCIE_GIT_BASELINE_REVIEW_ONLY",
        "tracked_changes": tracked,
        "staged_changes": staged,
        "untracked_total": untracked,
        "ignored_records": ignored,
        "untracked_categories": categories,
        "status_fingerprint_sha256": hashlib.sha256(data).hexdigest(),
        "file_contents_read": False,
        "git_mutations": 0,
        "auto_stage": False,
        "production_release_allowed": False,
    }


def scan_ucie_repo(repo: Path | None = None) -> dict[str, object]:
    root = (repo or Path(__file__).resolve().parents[2]).resolve()
    if root.name.casefold() != "ucie" or not (root / ".git").exists():
        raise BaselineError("UCIE_ROOT_NOT_VERIFIED")
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        run = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "-C", str(root),
             "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BaselineError("GIT_STATUS_UNAVAILABLE") from exc
    if run.returncode != 0:
        raise BaselineError("GIT_STATUS_FAILED")
    result = summarize(run.stdout)
    result["repo_scope_verified"] = True
    return result


def main() -> int:
    try:
        report = scan_ucie_repo()
    except BaselineError as exc:
        print(json.dumps({"schema": SCHEMA, "status": "NO_GO", "error": str(exc)}))
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
