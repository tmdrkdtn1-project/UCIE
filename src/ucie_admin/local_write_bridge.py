"""UCIE-only local read/write core for a separately authorized MCP admin tool.

No network server, shell, scheduler, service restart, token extraction or
unrestricted disk access. The process owner controls OS-level write rights.
The root boundaries and optimistic file-hash checks are non-optional.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid

MAX_READ = 200_000
MAX_WRITE = 256_000
MAX_SEARCH_FILES = 80
MAX_LIST = 150
MAX_RUN_OUTPUT = 12_000
MAX_TEST_SECONDS = 120
DENIED = frozenset({
    ".git", ".venv", ".venv_mcp", "__pycache__", "node_modules",
    ".ucie_bridge_state", ".env", ".ssh", "secrets",
})
SENSITIVE = re.compile(
    r"(?:secret|credential|private[_-]?key|api[_-]?key|token|password|"
    r"auth[_-]?key|tunnel[_-]?profile)", re.I
)
TEXT_SUFFIXES = frozenset({
    ".py", ".pyi", ".ps1", ".psm1", ".psd1", ".md", ".txt", ".json",
    ".toml", ".yaml", ".yml", ".cfg", ".ini", ".xml", ".csv",
    ".gitignore", ".editorconfig", ".sh",
})
SHA = re.compile(r"[0-9a-f]{64}\Z")
TEST_NAME = re.compile(r"test_[A-Za-z0-9_]{1,110}\.py\Z")


class BridgeError(ValueError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _special(path: Path) -> bool:
    return path.is_symlink() or (
        hasattr(path, "is_junction") and path.is_junction()
    )


class UCIEFileBridge:
    """Two explicitly configured UCIE code roots, never sibling projects."""

    def __init__(self, repo_root: Path, mcp_code_root: Path,
                 *, python_exe: Path | None = None):
        self.roots = {
            "repo": Path(repo_root),
            "mcp_code": Path(mcp_code_root),
        }
        for key, root in self.roots.items():
            if not root.is_dir() or _special(root):
                raise BridgeError("UCIE " + key + " root must exist and not be linked")
        self.python_exe = Path(python_exe) if python_exe else Path(sys.executable)
        self.audit_root = self.roots["repo"] / ".ucie_bridge_state"

    @classmethod
    def for_ucie_windows_host(cls):
        """No caller-controlled root argument in the exported MCP tools."""
        if os.name != "nt":
            raise BridgeError("UCIE host bridge requires Windows")
        return cls(
            Path(r"D:\UCIE"),
            Path(r"D:\UCIE_DATA\library_app\private_lib"),
            python_exe=Path(r"D:\UCIE\.venv\Scripts\python.exe"),
        )

    @staticmethod
    def _relative(path: str):
        if (type(path) is not str or not path or len(path) > 260
                or "\x00" in path or "\\" in path or path.startswith("/")):
            raise BridgeError("relative forward-slash path required")
        if re.match(r"^[A-Za-z]:", path):
            raise BridgeError("absolute paths not accepted")
        parts = path.split("/")
        if (any(x in ("", ".", "..") or x in DENIED
                or SENSITIVE.search(x) for x in parts)
                or any(x.startswith(".") and x not in (
                    ".github", ".gitignore", ".editorconfig")
                       for x in parts)):
            raise BridgeError("restricted UCIE path")
        return parts

    def _locate(self, scope: str, relative: str, *, file=False) -> Path:
        if type(scope) is not str or scope not in self.roots:
            raise BridgeError("only repo and mcp_code UCIE roots are available")
        base = self.roots[scope]
        pieces = self._relative(relative)
        # The MCP code root is intentionally narrower than UCIE_DATA:
        # no tunnel profiles, service keys or unrelated database folders.
        dest = base.joinpath(*pieces)
        if not dest.resolve(strict=False).is_relative_to(
                base.resolve(strict=True)):
            raise BridgeError("UCIE path escapes approved root")
        for part in [base, *[base.joinpath(*pieces[:i])
                              for i in range(1, len(pieces) + 1)]]:
            if part.exists() or part.is_symlink():
                if _special(part):
                    raise BridgeError("symbolic link or junction refused")
        if file:
            if Path(relative).suffix.lower() not in TEXT_SUFFIXES:
                raise BridgeError("only approved text/source file types")
            if scope == "mcp_code" and Path(relative).suffix.lower() not in {
                    ".py", ".md", ".toml", ".txt"}:
                raise BridgeError("MCP runtime code scope accepts source/docs only")
        return dest

    def _audit(self, operation: str, scope: str, relative: str,
               before: str | None, after: str | None):
        folder = self.audit_root
        if folder.exists() and (_special(folder) or not folder.is_dir()):
            raise BridgeError("UCIE audit folder cannot be trusted")
        folder.mkdir(exist_ok=True)
        payload = json.dumps({
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "action": operation, "scope": scope, "path": relative,
            "before_sha256": before, "after_sha256": after,
        }, separators=(",", ":"), sort_keys=True)
        with open(folder / "audit.jsonl", "a", encoding="utf-8") as handle:
            handle.write(payload + "\n")

    def list_directory(self, scope: str, relative: str = "src",
                       max_items: int = 50) -> dict:
        if type(max_items) is not int or not 1 <= max_items <= MAX_LIST:
            raise BridgeError("invalid bounded listing size")
        if relative == "":
            if scope not in self.roots:
                raise BridgeError("unknown UCIE scope")
            folder = self.roots[scope]
        else:
            folder = self._locate(scope, relative)
        if not folder.is_dir() or _special(folder):
            raise BridgeError("directory is absent or linked")
        items = []
        for child in sorted(folder.iterdir(), key=lambda x: x.name.casefold()):
            try:
                rel = child.relative_to(self.roots[scope]).as_posix()
                self._locate(scope, rel)
            except BridgeError:
                continue
            items.append({
                "name": child.name,
                "kind": "directory" if child.is_dir() else "file",
            })
            if len(items) >= max_items:
                break
        return {"scope": scope, "directory": relative, "items": items,
                "bounded_listing": True, "writes": 0}

    def read_text(self, scope: str, relative: str) -> dict:
        path = self._locate(scope, relative, file=True)
        if not path.is_file() or path.stat().st_size > MAX_READ:
            raise BridgeError("text file absent or exceeds read limit")
        raw = path.read_bytes()
        if len(raw) > MAX_READ or b"\x00" in raw:
            raise BridgeError("oversized or binary file")
        try:
            body = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BridgeError("file is not UTF-8 text") from exc
        return {"scope": scope, "path": relative, "sha256": _sha(raw),
                "content": body, "bytes": len(raw), "writes": 0}

    def search_text(self, scope: str, directory: str, literal: str,
                    max_matches: int = 20) -> dict:
        if (type(literal) is not str or not 1 <= len(literal) <= 100
                or any(ord(c) < 32 for c in literal)
                or type(max_matches) is not int or not 1 <= max_matches <= 50):
            raise BridgeError("bounded literal search required")
        folder = self._locate(scope, directory)
        if not folder.is_dir() or _special(folder):
            raise BridgeError("missing UCIE search directory")
        matches = []
        scanned = 0
        for candidate in sorted(folder.rglob("*")):
            if scanned >= MAX_SEARCH_FILES or len(matches) >= max_matches:
                break
            if candidate.is_dir():
                continue
            try:
                rel = candidate.relative_to(self.roots[scope]).as_posix()
                target = self._locate(scope, rel, file=True)
                if not target.is_file() or target.stat().st_size > MAX_READ:
                    continue
                scanned += 1
                with open(target, "r", encoding="utf-8") as handle:
                    for lineno, line in enumerate(handle, 1):
                        if literal in line:
                            matches.append({"path": rel, "line": lineno,
                                            "preview": line.strip()[:160]})
                            if len(matches) >= max_matches:
                                break
            except (BridgeError, OSError, UnicodeError):
                continue
        return {"scope": scope, "directory": directory, "literal": literal,
                "scanned_files": scanned, "matches": matches,
                "bounded_search": True, "writes": 0}

    def create_directory(self, scope: str, relative: str):
        dest = self._locate(scope, relative)
        if dest.exists() or not dest.parent.is_dir():
            raise BridgeError("directory exists or parent missing")
        self._audit("mkdir", scope, relative, None, None)
        dest.mkdir()
        return {"action": "mkdir", "scope": scope, "path": relative}

    def write_text(self, scope: str, relative: str, content: str,
                   expected_sha256: str, *, preview=False) -> dict:
        if type(preview) is not bool:
            raise BridgeError("preview must be boolean")
        if (type(content) is not str
                or len(content.encode("utf-8")) > MAX_WRITE
                or "\x00" in content):
            raise BridgeError("invalid or oversized source content")
        target = self._locate(scope, relative, file=True)
        if not target.parent.is_dir() or _special(target.parent):
            raise BridgeError("existing nonlinked parent directory required")
        exists = target.exists()
        if exists and (not target.is_file() or target.stat().st_size > MAX_WRITE):
            raise BridgeError("existing file oversized or not regular")
        old = target.read_bytes() if exists else None
        prev = _sha(old) if old is not None else "ABSENT"
        if (type(expected_sha256) is not str
                or (expected_sha256 != "ABSENT" and
                    not SHA.fullmatch(expected_sha256))
                or expected_sha256 != prev):
            raise BridgeError("concurrent modification / expected SHA mismatch")
        raw = content.encode("utf-8")
        new_hash = _sha(raw)
        result = {"scope": scope, "path": relative, "before_sha256": prev,
                  "after_sha256": new_hash, "written": False,
                  "backup": None}
        if preview or (old is not None and old == raw):
            return result
        # Exact caller-controlled UCIE source file mutation. Save the previous
        # UTF-8 code in local UCIE-only state before replacing anything.
        state = self.audit_root
        if state.exists() and (_special(state) or not state.is_dir()):
            raise BridgeError("UCIE audit directory unsafe")
        state.mkdir(exist_ok=True)
        backup = None
        if old is not None:
            backup_name = uuid.uuid4().hex + "-" + prev[:16] + ".bak"
            backup = state / backup_name
            with open(backup, "xb") as handle:
                handle.write(old)
                handle.flush()
                os.fsync(handle.fileno())
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="wb", dir=target.parent, delete=False,
                    prefix=".ucie-write-", suffix=".tmp") as handle:
                temporary = Path(handle.name)
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            current = target.read_bytes() if target.exists() else None
            if current != old:
                raise BridgeError("file changed before atomic replace")
            os.replace(temporary, target)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self._audit("write", scope, relative, prev, new_hash)
        result["written"] = True
        result["backup"] = backup.name if backup else None
        return result

    def replace_once(self, scope: str, relative: str, old_text: str,
                     new_text: str, expected_sha256: str,
                     *, preview=False) -> dict:
        if type(old_text) is not str or not old_text:
            raise BridgeError("exact original text required")
        if type(new_text) is not str:
            raise BridgeError("replacement must be text")
        original = self.read_text(scope, relative)
        if original["sha256"] != expected_sha256:
            raise BridgeError("file changed before exact replacement")
        if original["content"].count(old_text) != 1:
            raise BridgeError("replacement must match exactly once")
        updated = original["content"].replace(old_text, new_text, 1)
        return self.write_text(scope, relative, updated,
                               expected_sha256, preview=preview)

    def git_status(self) -> dict:
        proc = subprocess.run(
            ["git", "-C", str(self.roots["repo"]), "status", "--short"],
            text=True, capture_output=True, timeout=15, check=False)
        return {"exit_code": proc.returncode,
                "status": proc.stdout[:MAX_RUN_OUTPUT],
                "error": proc.stderr[:1000], "writes": 0}

    def run_one_test_file(self, filename: str, *, approved=False) -> dict:
        if type(filename) is not str or not TEST_NAME.fullmatch(filename):
            raise BridgeError("only one UCIE test_*.py is accepted")
        if approved is not True:
            raise BridgeError("explicit UCIE test execution approval required")
        test = self._locate("repo", "tests/" + filename, file=True)
        if not test.is_file() or not self.python_exe.is_file():
            raise BridgeError("test file or UCIE interpreter missing")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(self.roots["repo"] / "src")
        proc = subprocess.run(
            [str(self.python_exe), "-B", "-m", "unittest", "discover",
             "-s", "tests", "-p", filename],
            cwd=self.roots["repo"], env=env,
            text=True, capture_output=True,
            timeout=MAX_TEST_SECONDS, check=False)
        return {"filename": filename, "exit_code": proc.returncode,
                "stdout": proc.stdout[-MAX_RUN_OUTPUT:],
                "stderr": proc.stderr[-MAX_RUN_OUTPUT:],
                "command_scope": "ONE_UCIE_TEST_FILE_NO_SHELL"}

