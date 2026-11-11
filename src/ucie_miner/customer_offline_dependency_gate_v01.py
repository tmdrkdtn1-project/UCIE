"""UCIE C1: offline-only third-party wheelhouse + dynamic-import risk gate.

Only first-party UCIE pyproject.toml and an OPTIONAL fixed UCIE-local preview
wheelhouse are inspected. Third-party archives are UNTRUSTED bytes: never
installed, imported, executed, unpickled, published, downloaded or shipped.
The resulting evidence is NOT an SPDX/SBOM/legal/signature customer approval.
"""
from __future__ import annotations

import ast
import base64
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import stat
import sys
import tomllib
from zipfile import ZipFile, BadZipFile

from .customer_runtime_closure_v01 import (
    inspect_static_runtime_closure, _src_index, _imports, PACKAGES,
)

SCHEMA = "UCIE_C1_OFFLINE_DEPENDENCIES_AND_DYNAMIC_SITES_PREVIEW_V01"
STATUS = "C1_METADATA_ONLY_OFFLINE_NO_CUSTOMER_RELEASE"
WHEELHOUSE = ".ucie_c1_offline_wheelhouse_preview"
MAX_WHEELS = 12
MAX_WHEEL_BYTES = 20_000_000
MAX_ZIP_ENTRIES = 1100
MAX_UNCOMPRESSED = 36_000_000
MAX_MEMBER_BYTES = 12_000_000
EXPECTED_DISTRIBUTION = "cryptography"
EXPECTED_REQ = "cryptography>=50.0.2,<51"
EXPECTED_BUILD_REQ = "setuptools>=68"
VERSION = re.compile(r"\d+(?:\.\d+){1,3}(?:[a-z]+\d+)?\Z", re.I)
DIST_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,90}\Z")
WHL_FILENAME = re.compile(
    r"(?P<name>[A-Za-z0-9_]+)-(?P<version>[A-Za-z0-9_.]+)"
    r"(?:-(?P<build>[0-9][A-Za-z0-9_.]*))?"
    r"-(?P<python>[A-Za-z0-9_.]+)-(?P<abi>[A-Za-z0-9_.]+)"
    r"-(?P<platform>[A-Za-z0-9_.]+)\.whl\Z"
)


class OfflineDependencyError(ValueError):
    """Untrusted archive, unapproved scope, or first-party policy drift."""


def _root(root: Path) -> Path:
    if (not isinstance(root, Path) or root.name.casefold() != "ucie"
            or not root.is_dir() or root.is_symlink()
            or not (root / ".git").is_dir() or (root / ".git").is_symlink()):
        raise OfflineDependencyError("exact UCIE-only checkout required")
    return root


def _project(root: Path) -> dict:
    root = _root(root)
    target = root / "pyproject.toml"
    if target.is_symlink() or not target.is_file() or target.stat().st_size > 12_000:
        raise OfflineDependencyError("UCIE pyproject not safely available")
    try:
        config = tomllib.loads(target.read_text("utf-8"))
    except (UnicodeError, ValueError, OSError) as exc:
        raise OfflineDependencyError("UCIE project metadata invalid") from exc
    project, build = config.get("project"), config.get("build-system")
    if (type(project) is not dict or type(build) is not dict
            or project.get("name") != "ucie-public-only-demo"
            or project.get("version") != "0.1.0"
            or project.get("requires-python") != ">=3.13"
            or project.get("dependencies") != [EXPECTED_REQ]
            or build.get("requires") != [EXPECTED_BUILD_REQ]
            or build.get("build-backend") != "setuptools.build_meta"):
        raise OfflineDependencyError("unreviewed package declaration drift")
    return {
        "declared_project": "ucie-public-only-demo",
        "declared_project_version": project["version"],
        "declared_runtime_requirements": list(project["dependencies"]),
        "declared_build_requirements": list(build["requires"]),
        "declared_python_constraint": project["requires-python"],
        "pyproject_sha256": sha256(target.read_bytes()).hexdigest(),
    }


def _normal_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _entry_name(name: str) -> None:
    if (type(name) is not str or not name or name.startswith("/")
            or chr(92) in name or chr(0) in name
            or any(x in ("", ".", "..") for x in name.rstrip("/").split("/"))
            or len(name) > 210):
        raise OfflineDependencyError("unsafe wheel archive entry")


def _inspect_wheel(path: Path) -> dict:
    if (not path.is_file() or path.is_symlink()
            or not 200 <= path.stat().st_size <= MAX_WHEEL_BYTES):
        raise OfflineDependencyError("untrusted wheel file size or link")
    match = WHL_FILENAME.fullmatch(path.name)
    if not match:
        raise OfflineDependencyError("unsupported wheel filename")
    try:
        with ZipFile(path) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_ZIP_ENTRIES:
                raise OfflineDependencyError("wheel archive entry count")
            names = set()
            total = 0
            for info in infos:
                _entry_name(info.filename)
                if info.filename in names:
                    raise OfflineDependencyError("duplicate wheel archive path")
                names.add(info.filename)
                if info.flag_bits & 0x1:
                    raise OfflineDependencyError("encrypted wheel forbidden")
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise OfflineDependencyError("wheel link forbidden")
                if info.file_size > MAX_MEMBER_BYTES or info.compress_size > MAX_WHEEL_BYTES:
                    raise OfflineDependencyError("oversized wheel member")
                total += info.file_size
                if total > MAX_UNCOMPRESSED:
                    raise OfflineDependencyError("wheel inflated size budget")
            pkg = match.group("name")
            ver = match.group("version")
            if not DIST_NAME.fullmatch(pkg) or not VERSION.fullmatch(ver):
                raise OfflineDependencyError("unsupported distribution identity")
            dist_info = pkg.replace("-", "_") + "-" + ver + ".dist-info/"
            meta = dist_info + "METADATA"
            wheel_meta = dist_info + "WHEEL"
            record = dist_info + "RECORD"
            if not {meta, wheel_meta, record}.issubset(names):
                raise OfflineDependencyError("missing wheel identity, metadata or RECORD")
            def read_small(name: str, limit: int) -> bytes:
                if archive.getinfo(name).file_size > limit:
                    raise OfflineDependencyError("oversized wheel metadata")
                return archive.read(name)
            text_meta = read_small(meta, 100_000).decode("utf-8")
            text_wheel = read_small(wheel_meta, 16_000).decode("utf-8")
            text_record = read_small(record, 200_000).decode("utf-8")
            def header_value(text: str, key: str) -> str | None:
                for line in text.splitlines():
                    if line.startswith(key + ": "):
                        return line.split(": ", 1)[1].strip()
                return None
            name = header_value(text_meta, "Name")
            version = header_value(text_meta, "Version")
            if (_normal_name(name or "") != _normal_name(pkg)
                    or version != ver or
                    header_value(text_wheel, "Wheel-Version") is None):
                raise OfflineDependencyError("wheel filename and METADATA mismatch")
            import csv
            rows = list(csv.reader(io.StringIO(text_record)))
            recorded = set()
            for row in rows:
                if len(row) != 3:
                    raise OfflineDependencyError("malformed RECORD line")
                filename, encoded_hash, size = row
                _entry_name(filename)
                if filename in recorded or filename not in names:
                    raise OfflineDependencyError("duplicate or unknown RECORD path")
                recorded.add(filename)
                if filename == record:
                    if encoded_hash or size:
                        raise OfflineDependencyError("RECORD self-hash forbidden")
                    continue
                if not encoded_hash.startswith("sha256=") or not size.isdecimal():
                    raise OfflineDependencyError("only SHA256 RECORD entries accepted")
                if int(size) != archive.getinfo(filename).file_size:
                    raise OfflineDependencyError("RECORD byte length mismatch")
                actual = base64.urlsafe_b64encode(
                    sha256(archive.read(filename)).digest()).rstrip(b"=").decode("ascii")
                if encoded_hash[7:] != actual:
                    raise OfflineDependencyError("RECORD digest mismatch")
            if recorded != {i.filename for i in infos if not i.is_dir()}:
                raise OfflineDependencyError("RECORD omitted actual wheel members")
            requirements = [line.split(": ", 1)[1].strip()
                            for line in text_meta.splitlines()
                            if line.startswith("Requires-Dist: ")]
            # These are observed dependency strings, NOT a resolved platform graph.
            return {
                "name": _normal_name(pkg),
                "version": ver,
                "wheel_sha256": sha256(path.read_bytes()).hexdigest(),
                "wheel_bytes": path.stat().st_size,
                "python_tag": match.group("python"),
                "abi_tag": match.group("abi"),
                "platform_tag": match.group("platform"),
                "requires_dist": requirements,
                "metadata_record_sha256_verified": True,
                "package_code_executed": False,
                "license_terms_approved": False,
                "wheel_tag_compatibility_attested": False,
                "publisher_signature_verified": False,
            }
    except (BadZipFile, UnicodeError, KeyError, EOFError, OSError, OverflowError) as exc:
        raise OfflineDependencyError("untrusted wheel archive could not be validated") from exc


def dynamic_import_risks(root: Path, closure: dict | None = None) -> dict:
    root = _root(root)
    closure = closure if closure is not None else inspect_static_runtime_closure(root)
    index = _src_index(root)
    risk = []
    for site in closure["dynamic_import_sites"]:
        module, sep, line = site.rpartition(":")
        if not sep or module not in index or not line.isdecimal():
            raise OfflineDependencyError("dynamic import evidence lacks exact source")
        rel, payload, _ = index[module]
        matches = []
        for node in ast.walk(ast.parse(payload)):
            if isinstance(node, ast.Call) and node.lineno == int(line):
                fn = node.func
                if (isinstance(fn, ast.Name) and fn.id in ("__import__", "import_module")
                        or isinstance(fn, ast.Attribute) and fn.attr == "import_module"):
                    matches.append(node)
        if len(matches) != 1:
            raise OfflineDependencyError("dynamic import source expression ambiguous")
        node = matches[0]
        target = (node.args[0].value if node.args and
                  isinstance(node.args[0], ast.Constant) and
                  isinstance(node.args[0].value, str) else None)
        risk.append({
            "source_module": module,
            "source_relative_path": rel,
            "source_sha256": sha256(payload).hexdigest(),
            "line": int(line),
            "constant_target": target if target and len(target) < 100 else None,
            "static_target_known_in_ucie": bool(target in index),
            "literal_stdlib_target": bool(target in sys.stdlib_module_names),
            "runtime_variable_import_requires_review": target is None,
            "source_reaches_dynamic_import": True,
            "dynamic_approval": False,
        })
    return {
        "sites": risk,
        "source_site_count": len(risk),
        "variable_sites": sum(bool(x["runtime_variable_import_requires_review"])
                              for x in risk),
        "fixed_stdlib_import_sites_only": bool(risk) and all(
            x["literal_stdlib_target"] for x in risk
        ),
        "unresolved_dynamic_targets": sum(
            not (x["literal_stdlib_target"] or
                 x["static_target_known_in_ucie"]) for x in risk
        ),
        "runtime_dynamic_imports_fully_resolved": False,
        "first_party_source_only": True,
    }


def _cryptography_constraint_satisfied(version: str) -> bool:
    """Only the reviewed pyproject >=50.0.2,<51 numeric-stable range."""
    if type(version) is not str or re.fullmatch(r"\\d+\\.\\d+\\.\\d+", version) is None:
        return False
    major, minor, patch = (int(x) for x in version.split("."))
    return major == 50 and (minor, patch) >= (0, 2)


def inspect_offline_dependency_gate(root: Path) -> dict:
    """UCIE-only metadata, no pip/network/imports and no customer artifact."""
    root = _root(root)
    project = _project(root)
    closure = inspect_static_runtime_closure(root)
    dynamic = dynamic_import_risks(root, closure)
    if closure["missing_first_party_imports"]:
        raise OfflineDependencyError("missing static first-party modules")
    external = closure["external_import_roots"]
    if any(_normal_name(x) != EXPECTED_DISTRIBUTION for x in external):
        raise OfflineDependencyError("undeclared external import encountered")
    wheel_dir = root / WHEELHOUSE
    wheels = []
    if wheel_dir.exists() or wheel_dir.is_symlink():
        if wheel_dir.is_symlink() or not wheel_dir.is_dir():
            raise OfflineDependencyError("unsafe UCIE wheelhouse path")
        found = list(wheel_dir.iterdir())
        if len(found) > MAX_WHEELS:
            raise OfflineDependencyError("wheelhouse exceeds bounded file count")
        for path in sorted(found):
            if path.is_symlink() or not path.is_file() or path.suffix != ".whl":
                raise OfflineDependencyError("unexpected UCIE wheelhouse entry")
            wheels.append(_inspect_wheel(path))
    names = [v["name"] for v in wheels]
    if len(set(names)) != len(names):
        raise OfflineDependencyError("ambiguous duplicate wheel distributions")
    observed_versions = [x["version"] for x in wheels
                         if x["name"] == EXPECTED_DISTRIBUTION]
    declared_wheel_present = any(
        _cryptography_constraint_satisfied(v) for v in observed_versions)
    blockers = []
    if not observed_versions:
        blockers.append("DECLARED_CRYPTOGRAPHY_WHEEL_NOT_PRESENT")
    elif not declared_wheel_present:
        blockers.append("DECLARED_CRYPTOGRAPHY_VERSION_UNSATISFIED")
    if not wheels:
        blockers.append("NO_OFFLINE_WHEELHOUSE_BUNDLED")
    if dynamic["unresolved_dynamic_targets"]:
        blockers.append("DYNAMIC_IMPORT_RUNTIME_TARGET_UNRESOLVED")
    elif dynamic["source_site_count"]:
        blockers.append("FIXED_DYNAMIC_IMPORTS_RUNTIME_QA_PENDING")
    blockers.extend((
        "THIRD_PARTY_WHEEL_TRANSITIVE_DEPENDENCIES_UNRESOLVED",
        "CROSS_PYTHON_PLATFORM_WHEEL_TAGS_NOT_ATTESTED",
        "RELEASE_DEPENDENCY_SHA_LOCK_NOT_OWNER_APPROVED",
        "THIRD_PARTY_LICENSE_SECURITY_SBOM_REVIEW_PENDING",
        "C1_COMPLETE_CUSTOMER_INSTALL_UPDATE_ROLLBACK_NOT_ACCEPTED",
    ))
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "project": project,
        "source_indexed_python_modules": closure["all_python_modules_indexed"],
        "source_statically_reachable_modules":
            closure["statically_reachable_first_party_modules"],
        "external_import_roots": external,
        "dynamic_import_risk": dynamic,
        "fixed_wheelhouse_relative_path": WHEELHOUSE,
        "wheelhouse_present": wheel_dir.is_dir(),
        "wheel_metadata": wheels,
        "declared_requirement_wheel_observed": declared_wheel_present,
        "observed_requirement_versions": observed_versions,
        "complete_transitive_dependency_closure_attested": False,
        "dependency_wheels_executed_or_installed": False,
        "pip_no_index_install_executed": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "other_project_access": False,
        "customer_release_authorized": False,
        "blockers": blockers,
    }
