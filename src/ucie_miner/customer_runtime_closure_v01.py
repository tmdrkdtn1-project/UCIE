"""UCIE C1: bounded first-party import closure and A/B disposable preview.

Static AST inspection of ONLY src/ucie_miner and src/ucie_public inside the
explicit UCIE checkout. Tracks reachable Python modules and other imports;
does not execute scanned imports or claim complete optional/dynamic closure.
A/B generations are real DIFFERENT runnable first-party PREVIEW code bytes,
not a signed product change, approved update, customer installer or export.
"""
from __future__ import annotations

import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from .customer_component_lifecycle_v01 import FILES as CENSUS_FILES
from .customer_portable_preview_v01 import (
    MARKER_BYTES, MARKER_NAME, REVISION as REVISION_A,
)

SCHEMA = "UCIE_C1_SOURCE_IMPORT_CLOSURE_AND_PORTABLE_AB_STAGING_V01"
STATE = "FIRST_PARTY_DISPOSABLE_VERSIONED_PREVIEW_CUSTOMER_NO_GO"
PACKAGES = ("ucie_miner", "ucie_public")
ENTRY_MODULES = (
    "ucie_miner.customer_portable_preview_v01",
    "ucie_miner.local_v1_app_v01",
    "ucie_miner.customer_staging_v01",
    "ucie_public.cli",
)
PREVIEW_SOURCE = "src/ucie_miner/customer_portable_preview_v01.py"
REVISION_B = "UCIE_C1_DISPOSABLE_GENERATION_B"
MAX_SOURCE_FILES = 250
MAX_SOURCE_BYTES = 8_000_000
MAX_FILE_BYTES = 260_000
MAX_STAGE_BYTES = 11_000_000
CHILD_TIMEOUT = 35
MAX_CHILD_STDOUT = 16_000


class ClosurePreviewError(ValueError):
    """Missing or unsafe source, tamper, or isolated preview failed."""


def _digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")).encode("ascii")


def _source_root(root: Path) -> Path:
    if (not isinstance(root, Path) or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()
            or (root / ".git").is_symlink()
            or not (root / ".git").is_dir()
            or (root / "src").is_symlink()):
        raise ClosurePreviewError("exact standalone first-party UCIE checkout required")
    return root


def _src_index(root: Path) -> dict[str, tuple[str, bytes, bool]]:
    root = _source_root(root)
    found: dict[str, tuple[str, bytes, bool]] = {}
    total = 0
    for name in PACKAGES:
        pkg = root / "src" / name
        if not pkg.is_dir() or pkg.is_symlink():
            raise ClosurePreviewError("first-party package missing or symlinked")
        for path in pkg.rglob("*"):
            if path.is_symlink():
                raise ClosurePreviewError("source package symlink blocked")
            if not path.is_file() or path.suffix != ".py":
                continue
            relative = path.relative_to(root).as_posix()
            parts = list(path.relative_to(root / "src").with_suffix("").parts)
            is_init = parts[-1] == "__init__"
            if is_init:
                parts.pop()
            if not parts:
                raise ClosurePreviewError("empty first-party module")
            module = ".".join(parts)
            if (module in found or len(found) >= MAX_SOURCE_FILES
                    or any(p in (".", "..", "") for p in parts)):
                raise ClosurePreviewError("too many/duplicate modules")
            size = path.stat().st_size
            if not 0 <= size <= MAX_FILE_BYTES:
                raise ClosurePreviewError("oversized module")
            payload = path.read_bytes()
            if len(payload) != size:
                raise ClosurePreviewError("changed first-party source")
            total += size
            if total > MAX_SOURCE_BYTES:
                raise ClosurePreviewError("source tree read budget exceeded")
            # Parse only. Never import or execute public/owner-local modules.
            try:
                ast.parse(payload, filename=relative)
            except (SyntaxError, UnicodeError, ValueError) as exc:
                raise ClosurePreviewError("unsafe or unparseable source") from exc
            found[module] = (relative, payload, is_init)
    for name in PACKAGES:
        if name not in found or not found[name][2]:
            raise ClosurePreviewError("first-party package init missing")
    return found


def _imports(module: str, payload: bytes, is_init: bool,
             index: dict) -> tuple[set[str], set[str], set[str], set[str]]:
    deps: set[str] = set()
    external: set[str] = set()
    missing: set[str] = set()
    dynamic: set[str] = set()
    tree = ast.parse(payload, filename=module)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name
                root = target.split(".", 1)[0]
                if root in PACKAGES:
                    if target in index:
                        deps.add(target)
                    else:
                        missing.add(target)
                elif root not in sys.stdlib_module_names and root != "__future__":
                    external.add(root)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = module if is_init else module.rsplit(".", 1)[0]
                parts = base.split(".")
                if node.level > len(parts):
                    missing.add("RELATIVE_IMPORT_OUTSIDE_PACKAGE")
                    continue
                parts = parts[:len(parts) - node.level + 1]
                target = ".".join(parts + (node.module.split(".") if node.module else []))
            else:
                target = node.module or ""
            root = target.split(".", 1)[0]
            if root in PACKAGES:
                if target in index:
                    deps.add(target)
                elif target in PACKAGES:
                    deps.add(target)
                else:
                    missing.add(target)
                for alias in node.names:
                    child = target + "." + alias.name
                    if child in index:
                        deps.add(child)
            elif root and root not in sys.stdlib_module_names and root != "__future__":
                external.add(root)
        elif isinstance(node, ast.Call):
            fn = node.func
            if ((isinstance(fn, ast.Name) and fn.id in (
                    "__import__", "import_module"))
                or (isinstance(fn, ast.Attribute) and fn.attr in (
                    "import_module",))):
                dynamic.add(module + ":" + str(node.lineno))
                if node.args and isinstance(node.args[0], ast.Constant):
                    name = node.args[0].value
                    if isinstance(name, str) and name in index:
                        deps.add(name)
    return deps, external, missing, dynamic


def inspect_static_runtime_closure(root: Path) -> dict:
    """Read bounded UCIE first-party source only, never the operating DB."""
    index = _src_index(root)
    visited: set[str] = set()
    pending = list(ENTRY_MODULES)
    external: set[str] = set()
    missing: set[str] = set()
    dynamic: set[str] = set()
    while pending:
        mod = pending.pop()
        if mod in visited:
            continue
        if mod not in index:
            missing.add(mod)
            continue
        visited.add(mod)
        relative, payload, is_init = index[mod]
        # Include package-level init imports and initialization in stage.
        parts = mod.split(".")
        for j in range(1, len(parts)):
            parent = ".".join(parts[:j])
            if parent in index and parent not in visited:
                pending.append(parent)
        deps, extra, unresolved, dynamic_sites = _imports(mod, payload,
                                                          is_init, index)
        pending.extend(dep for dep in deps if dep not in visited)
        external.update(extra)
        missing.update(unresolved)
        dynamic.update(dynamic_sites)
    paths = sorted(index[x][0] for x in visited)
    if not paths or len(paths) > MAX_SOURCE_FILES:
        raise ClosurePreviewError("invalid runtime closure size")
    if any(x not in index for x in ENTRY_MODULES):
        raise ClosurePreviewError("missing actual product entry module")
    return {
        "schema": SCHEMA,
        "status": STATE,
        "entry_modules": list(ENTRY_MODULES),
        "all_python_modules_indexed": len(index),
        "statically_reachable_first_party_modules": len(visited),
        "reachable_files": paths,
        "external_import_roots": sorted(external),
        "missing_first_party_imports": sorted(missing),
        "dynamic_import_sites": sorted(dynamic),
        "first_party_static_scan_completed": True,
        "full_runtime_import_closure_attested": False,
        "external_dependency_wheelhouse_included": False,
        "runtime_capability_behavior_approved": False,
        "customer_distribution_authorized": False,
        "other_project_files_read": False,
        "operating_database_writes": 0,
        "external_network_requests": 0,
        "task_scheduler_changes": 0,
    }


def _copy_payload(root: Path, closure: dict) -> dict[str, bytes]:
    """Exact first-party fixed file set + only statically referenced Python."""
    candidates = sorted(set(CENSUS_FILES) | set(closure["reachable_files"]))
    data: dict[str, bytes] = {}
    total = 0
    for name in candidates:
        parts = name.split("/")
        if (not name or name.startswith("/") or "\\" in name
                or any(x in ("", ".", "..") for x in parts)
                or not (name.startswith(("src/ucie_miner/",
                                         "src/ucie_public/"))
                        or name in CENSUS_FILES)):
            raise ClosurePreviewError("unsafe external staging file")
        target = root
        for part in parts:
            target = target / part
            if target.is_symlink():
                raise ClosurePreviewError("source symlink not allowed")
        if not target.is_file() or not 0 < target.stat().st_size <= MAX_FILE_BYTES:
            raise ClosurePreviewError("missing or oversized source for stage")
        raw = target.read_bytes()
        if len(raw) != target.stat().st_size:
            raise ClosurePreviewError("source changed while staged")
        total += len(raw)
        if total > MAX_STAGE_BYTES:
            raise ClosurePreviewError("stage exceeds first-party budget")
        data[name] = raw
    if PREVIEW_SOURCE not in data:
        raise ClosurePreviewError("portable preview source missing from stage")
    return data


def _version_payload(source: dict[str, bytes], revision: str) -> dict[str, bytes]:
    if revision not in (REVISION_A, REVISION_B):
        raise ClosurePreviewError("unregistered preview revision")
    out = dict(source)
    if revision == REVISION_B:
        original = out[PREVIEW_SOURCE]
        needle = ('REVISION = "' + REVISION_A + '"').encode("ascii")
        if original.count(needle) != 1:
            raise ClosurePreviewError("first-party A revision anchor changed")
        out[PREVIEW_SOURCE] = original.replace(
            needle, ('REVISION = "' + REVISION_B + '"').encode("ascii"))
        if out[PREVIEW_SOURCE] == original:
            raise ClosurePreviewError("no executable source delta")
    return out


def _stage_path(root: Path, name: str) -> Path:
    """Disallow traversal or extra-file writes even by private staging helper."""
    if (type(name) is not str or not name or name.startswith("/")
            or "\\\\" in name or "\\x00" in name
            or any(p in ("", ".", "..") for p in name.split("/"))
            or not (name in CENSUS_FILES or
                    (name.startswith(("src/ucie_miner/", "src/ucie_public/"))
                     and name.endswith(".py")))):
        raise ClosurePreviewError("unauthorized C1 first-party stage path")
    return root.joinpath(*name.split("/"))


def _stage(root: Path, payloads: dict[str, bytes], revision: str) -> dict:
    if (root.exists() or root.is_symlink() or root.name.casefold() != "ucie"
            or revision not in (REVISION_A, REVISION_B)
            or type(payloads) is not dict or not payloads
            or len(payloads) > MAX_SOURCE_FILES + len(CENSUS_FILES)):
        raise ClosurePreviewError("invalid UCIE preview generation")
    total = 0
    for name, raw in payloads.items():
        _stage_path(root, name)
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_FILE_BYTES:
            raise ClosurePreviewError("invalid first-party stage file bytes")
        total += len(raw)
    if total > MAX_STAGE_BYTES:
        raise ClosurePreviewError("oversized first-party staging")
    root.mkdir()
    # Existing V04 handlers require a checkout-shaped root. The only .git
    # artifact here is an EMPTY throwaway directory, never repository history.
    (root / ".git").mkdir()
    entries = []
    for name in sorted(payloads):
        file = _stage_path(root, name)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(payloads[name])
        entries.append({"name": name, "sha256": _digest(payloads[name]),
                        "bytes": len(payloads[name])})
    marker = root / MARKER_NAME
    marker.write_bytes(MARKER_BYTES)
    manifest = {
        "schema": SCHEMA, "status": STATE, "revision": revision,
        "entries": entries,
        "source_sha256": _digest(_json(entries)),
        "customer_distribution_authorized": False,
        "full_product_customer_install_accepted": False,
        "approved_skillbooks_included": False,
        "external_dependency_wheelhouse_included": False,
        "signed_by_owner": False,
    }
    (root / "c1-preview-manifest.json").write_bytes(_json(manifest))
    return manifest


def _verify(root: Path, manifest: dict) -> None:
    if (not root.is_dir() or root.is_symlink()
            or root.name.casefold() != "ucie"
            or type(manifest) is not dict
            or manifest.get("status") != STATE
            or manifest.get("customer_distribution_authorized") is not False
            or manifest.get("signed_by_owner") is not False):
        raise ClosurePreviewError("invalid C1 staging identity")
    git_marker = root / ".git"
    if (git_marker.is_symlink() or not git_marker.is_dir()
            or any(git_marker.iterdir())):
        raise ClosurePreviewError("staging git marker must be empty")
    if (type(manifest.get("entries")) is not list
            or len(manifest["entries"]) > MAX_SOURCE_FILES + len(CENSUS_FILES)
            or not manifest["entries"]):
        raise ClosurePreviewError("invalid first-party stage entries")
    names = set()
    for entry in manifest["entries"]:
        if (type(entry) is not dict or set(entry) != {"name", "bytes", "sha256"}
                or type(entry["bytes"]) is not int
                or not 0 < entry["bytes"] <= MAX_FILE_BYTES
                or type(entry["sha256"]) is not str or
                len(entry["sha256"]) != 64):
            raise ClosurePreviewError("malformed staged source receipt")
        _stage_path(root, entry["name"])
        names.add(entry["name"])
    if (len(names) != len(manifest["entries"])
            or manifest.get("source_sha256") != _digest(_json(manifest["entries"]))):
        raise ClosurePreviewError("invalid C1 content manifest")
    expected = names | {MARKER_NAME, "c1-preview-manifest.json"}
    observed = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ClosurePreviewError("staged symlink rejected")
        if path.is_file():
            observed.add(path.relative_to(root).as_posix())
    if observed != expected:
        raise ClosurePreviewError("unexpected, hidden or missing staged component")
    if (root / MARKER_NAME).read_bytes() != MARKER_BYTES:
        raise ClosurePreviewError("C1 marker changed")
    if (root / "c1-preview-manifest.json").read_bytes() != _json(manifest):
        raise ClosurePreviewError("C1 manifest tampered")
    for entry in manifest["entries"]:
        target = _stage_path(root, entry["name"])
        raw = target.read_bytes()
        if len(raw) != entry["bytes"] or _digest(raw) != entry["sha256"]:
            raise ClosurePreviewError("C1 file content or length mismatch")


def _probe_child(root: Path, revision: str) -> dict:
    """Real isolated Python -I subprocess; imports only the staged UCIE src."""
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "root=Path(sys.argv[1])\n"
        "sys.path.insert(0,str(root/'src'))\n"
        "from ucie_miner.customer_portable_preview_v01 import main\n"
        "raise SystemExit(main(['--self-probe']))\n"
    )
    env = {k: os.environ[k] for k in (
        "PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP",
        "TMPDIR", "HOME", "USERPROFILE",
    ) if k in os.environ}
    process = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code, str(root)],
        cwd=root, env=env, capture_output=True, text=True,
        timeout=CHILD_TIMEOUT, check=False,
    )
    if (process.returncode != 0 or len(process.stdout) > MAX_CHILD_STDOUT):
        tail = process.stderr.strip().splitlines()[-1:] or ["NO_CHILD_STDERR"]
        status = "FAIL_CLOSED"
        try:
            payload = json.loads(process.stdout)
            status = (str(payload.get("status", "NON_JSON")) + " " +
                      str(payload.get("reason", "UNKNOWN"))[:170])
        except (ValueError, AttributeError):
            status = "NON_JSON"
        raise ClosurePreviewError(
            "isolated UCIE portable localhost probe failed: RC=" +
            str(process.returncode) + " STATUS=" + str(status)[:90] +
            " EXC=" + str(tail[0])[-200:]
        )
    try:
        result = json.loads(process.stdout)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ClosurePreviewError("non-machine-readable isolated UCIE probe") from exc
    if (result.get("status") !=
            "UCIE_C1_DISPOSABLE_LOOPBACK_SMOKE_PASS_NOT_CUSTOMER_GO"
            or result.get("revision") != revision
            or result.get("bound_host") != "127.0.0.1"
            or result.get("loopback_http_routes_checked") != 5
            or result.get("negative_post_checked") is not True
            or result.get("owner_local_v1_acceptance_inherited") is not False
            or result.get("customer_distribution_authorized") is not False
            or result.get("task_scheduler_modified") is not False
            or result.get("operating_database_writes") != 0):
        raise ClosurePreviewError("isolated preview overstated product readiness")
    return result


def exercise_real_revision_ab_preview(root: Path) -> dict:
    """Different runnable first-party A/B preview source, no customer install.

    Versions differ in source bytes and executable revision marker. This
    purposefully is NOT a different tagged UCIE full-product release: it
    tests control logic on disposable staging snapshots only.
    """
    closure = inspect_static_runtime_closure(root)
    if closure["missing_first_party_imports"]:
        raise ClosurePreviewError("first-party import closure missing modules")
    src = _copy_payload(root, closure)
    one = _version_payload(src, REVISION_A)
    two = _version_payload(src, REVISION_B)
    if _digest(one[PREVIEW_SOURCE]) == _digest(two[PREVIEW_SOURCE]):
        raise ClosurePreviewError("no real A/B source revision delta")
    with TemporaryDirectory(prefix="UCIE_C1_PORTABLE_AB_") as temp:
        top = Path(temp)
        a = top / "A" / "UCIE"
        b = top / "B" / "UCIE"
        a.parent.mkdir()
        b.parent.mkdir()
        ma = _stage(a, one, REVISION_A)
        _verify(a, ma)
        observed_a = _probe_child(a, REVISION_A)
        mb = _stage(b, two, REVISION_B)
        _verify(b, mb)
        # Failure injection cannot change selected installed generation A.
        victim = b.joinpath(*PREVIEW_SOURCE.split("/"))
        original = victim.read_bytes()
        victim.write_bytes(original + b"\n# UCIE C1 TAMPER REJECTED\n")
        tampered_blocked = False
        try:
            _verify(b, mb)
        except ClosurePreviewError:
            tampered_blocked = True
        if not tampered_blocked:
            raise ClosurePreviewError("tampered revision B accepted")
        _verify(a, ma)
        victim.write_bytes(original)
        _verify(b, mb)
        observed_b = _probe_child(b, REVISION_B)
        _verify(a, ma)
        observed_rollback = _probe_child(a, REVISION_A)
        if (observed_a["revision"] == observed_b["revision"]
                or observed_rollback["revision"] != observed_a["revision"]):
            raise ClosurePreviewError("A/B smoke not different or rollback failed")
    return {
        "schema": SCHEMA,
        "status": STATE,
        "first_party_static_closure": closure,
        "staged_total_first_party_files": len(src),
        "staged_python_module_files":
            sum(name.endswith(".py") for name in src),
        "revision_a_source_sha256": _digest(one[PREVIEW_SOURCE]),
        "revision_b_source_sha256": _digest(two[PREVIEW_SOURCE]),
        "first_party_preview_executable_bytes_differ": True,
        "a_portable_loopback_probe_pass": True,
        "b_portable_loopback_probe_pass": True,
        "tampered_b_rejected": tampered_blocked,
        "rollback_to_a_portable_probe_pass": True,
        "staging_temp_removed": True,
        "full_product_code_version_upgrade_completed": False,
        "first_party_source_only": True,
        "external_dependency_wheelhouse_included": False,
        "four_pillar_customer_end_to_end_accepted": False,
        "customer_license_issued": False,
        "signed_by_owner": False,
        "customer_distribution_authorized": False,
        "owner_resident_service_modified": False,
        "scheduler_modified": False,
        "operating_database_writes": 0,
        "other_project_access": False,
        "external_network_requests": 0,
    }
