"""Offline DEMO_ONLY signed Rulepack, with no project ingestion or networking."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import secrets
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from .policy import PolicyError, load_curated, validate_entry

SCHEMA = "UCIE_PUBLIC_RULEPACK_V0"
CHANNEL = "DEMO_ONLY"
EXPECTED_FILES = frozenset({
    "manifest.json", "knowledge/items.json", "verification/probes.json", "signatures/manifest.sig"
})
MAX_ARCHIVE_BYTES = 1048576


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def generate_keys(directory: Path, *, purpose: str = "demo") -> tuple[Path, Path]:
    if purpose not in ("demo", "prevention", "production", "qa"):
        raise PolicyError("unsupported key purpose")
    if directory.is_symlink():
        raise PolicyError("key directory cannot be symlink")
    directory.mkdir(parents=True, exist_ok=True)
    private_path = directory / f"private_{purpose}.pem"
    public_path = directory / f"public_{purpose}.pem"
    if private_path.exists() or public_path.exists():
        raise PolicyError("refusing key overwrite")
    private = Ed25519PrivateKey.generate()
    priv_bytes = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption())
    pub_bytes = private.public_key().public_bytes(serialization.Encoding.PEM,
                                                   serialization.PublicFormat.SubjectPublicKeyInfo)
    fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(priv_bytes)
    try:
        public_path.write_bytes(pub_bytes)
    except Exception:
        private_path.unlink(missing_ok=True)
        raise
    return private_path, public_path


def _private_key(path: Path) -> Ed25519PrivateKey:
    if path.is_symlink():
        raise PolicyError("key path cannot be symlink")
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise PolicyError("not an Ed25519 key")
    return key


def _public_key(path: Path) -> Ed25519PublicKey:
    if path.is_symlink():
        raise PolicyError("trust key path cannot be symlink")
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise PolicyError("not an Ed25519 trust anchor")
    return key


def key_id(key: Ed25519PublicKey) -> str:
    raw = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return digest(raw)[:32]


def run_probe(item: dict) -> dict:
    """Only parse the AST. Never exec/eval/import/open/network or invoke a shell."""
    validate_entry(item)
    try:
        tree = ast.parse(item["probe"]["snippet"], mode="exec")
        nodes = sum(1 for _ in ast.walk(tree))
        if nodes > 500:
            raise PolicyError("too many AST nodes")
        allowed_nodes = (ast.Module, ast.Import, ast.alias, ast.Assign, ast.Name,
                         ast.Store, ast.Load, ast.Call, ast.Attribute, ast.Constant,
                         ast.Expr)
        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise PolicyError("disallowed AST probe element")
            if isinstance(node, ast.Import) and any(n.name != "ast" or n.asname for n in node.names):
                raise PolicyError("AST probe imports only the ast module")
            if isinstance(node, ast.Name) and node.id.startswith("__"):
                raise PolicyError("dunder in probe")
            if isinstance(node, ast.Call):
                f = node.func
                if (not isinstance(f, ast.Attribute) or f.attr != "parse" or
                    not isinstance(f.value, ast.Name) or f.value.id != "ast" or
                    len(node.args) != 1 or node.keywords or
                    not isinstance(node.args[0], ast.Constant) or
                    not isinstance(node.args[0].value, str)):
                    raise PolicyError("only ast.parse(constant) allowed in probe")
    except (SyntaxError, ValueError) as exc:
        raise PolicyError("AST syntax probe FAILED") from exc
    return {"id": item["id"], "probe": "python_ast_parse", "result": "PASS_SYNTAX_ONLY", "ast_nodes": nodes}


def _valid_outpath(repo_root: Path, output: Path) -> Path:
    allowed = (repo_root / "build").resolve(strict=True)
    target = output.absolute()
    if target.is_symlink() or target.resolve().parent != allowed or target.suffix != ".zip":
        raise PolicyError("output must be a new .zip directly inside dedicated build directory")
    if target.exists():
        raise PolicyError("refusing package overwrite")
    return target


def publish_demo(repo_root: Path, key_path: Path, output: Path, *, serial: int = 1,
                 duration_days: int = 7) -> Path:
    if isinstance(serial, bool) or not (isinstance(serial, int) and 1 <= serial <= 10000000):
        raise PolicyError("bad serial")
    if not (1 <= duration_days <= 30):
        raise PolicyError("bad expiry duration")
    entries = load_curated(repo_root)
    evidence = [run_probe(item) for item in entries]
    knowledge_bytes = canonical_json(entries)
    evidence_bytes = canonical_json(evidence)
    private = _private_key(key_path)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    manifest = {
        "schema": SCHEMA,
        "scope": "PUBLIC_ONLY",
        "channel": CHANNEL,
        "mode": "OFFLINE_TEST_ONLY",
        "serial": serial,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(days=duration_days)).isoformat().replace("+00:00", "Z"),
        "items_count": len(entries),
        "knowledge_sha256": digest(knowledge_bytes),
        "probes_sha256": digest(evidence_bytes),
        "key_id": key_id(private.public_key()),
        "limitations": "syntax/provenance schema only; not production-approved",
    }
    man_bytes = canonical_json(manifest)
    sig = private.sign(man_bytes)
    target = _valid_outpath(repo_root, output)
    fd, staged = tempfile.mkstemp(dir=str(target.parent), prefix=".ucie_staging_", suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as f:
            with zipfile.ZipFile(f, "w", compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("manifest.json", man_bytes)
                z.writestr("knowledge/items.json", knowledge_bytes)
                z.writestr("verification/probes.json", evidence_bytes)
                z.writestr("signatures/manifest.sig", sig)
        os.link(staged, target)
    finally:
        Path(staged).unlink(missing_ok=True)
    return target


def verify_demo(pack_path: Path, trust_path: Path, *, min_serial: int = 1,
                at_time: datetime | None = None) -> dict:
    if pack_path.is_symlink():
        raise PolicyError("symlinked pack not allowed")
    if pack_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise PolicyError("oversized archive")
    key = _public_key(trust_path)
    try:
        with zipfile.ZipFile(pack_path, "r") as z:
            infos = z.infolist()
            names = [i.filename for i in infos]
            if len(names) != len(EXPECTED_FILES) or set(names) != EXPECTED_FILES:
                raise PolicyError("unrecognized files, duplicates, or missing files in package")
            if any(i.file_size > MAX_ARCHIVE_BYTES for i in infos):
                raise PolicyError("oversized entry")
            if any(i.flag_bits & 1 or ((i.external_attr >> 16) & 0o170000) == 0o120000 for i in infos):
                raise PolicyError("encrypted/symlink archive entries forbidden")
            data = {n: z.read(n) for n in names}
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise PolicyError("invalid archive") from exc
    try:
        man = json.loads(data["manifest.json"].decode("utf-8"))
        items = json.loads(data["knowledge/items.json"].decode("utf-8"))
        probes = json.loads(data["verification/probes.json"].decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise PolicyError("invalid package JSON") from exc
    if canonical_json(man) != data["manifest.json"]:
        raise PolicyError("non-canonical signed manifest")
    if man.get("schema") != SCHEMA or man.get("scope") != "PUBLIC_ONLY" or man.get("channel") != CHANNEL:
        raise PolicyError("unexpected schema/scope/channel")
    if man.get("mode") != "OFFLINE_TEST_ONLY":
        raise PolicyError("unexpected mode")
    if type(man.get("serial")) is not int or man["serial"] < min_serial:
        raise PolicyError("rollback/stale serial rejected")
    if man.get("key_id") != key_id(key):
        raise PolicyError("untrusted signer")
    if digest(data["knowledge/items.json"]) != man.get("knowledge_sha256"):
        raise PolicyError("knowledge digest mismatch")
    if digest(data["verification/probes.json"]) != man.get("probes_sha256"):
        raise PolicyError("probe digest mismatch")
    try:
        key.verify(data["signatures/manifest.sig"], data["manifest.json"])
    except (InvalidSignature, ValueError) as exc:
        raise PolicyError("invalid signature") from exc
    try:
        created = datetime.fromisoformat(man["created_at"].replace("Z", "+00:00"))
        expires = datetime.fromisoformat(man["expires_at"].replace("Z", "+00:00"))
        now = at_time or datetime.now(timezone.utc)
    except (ValueError, KeyError) as exc:
        raise PolicyError("bad timestamps") from exc
    if any(x.tzinfo is None for x in (created, expires, now)) or now < created - timedelta(minutes=5) or now >= expires:
        raise PolicyError("not-yet-valid/expired manifest")
    if expires - created > timedelta(days=30):
        raise PolicyError("expiry too long")
    if not isinstance(items, list) or not items or len(items) != man.get("items_count"):
        raise PolicyError("entry count mismatch")
    if len(set(i.get("id", "") for i in items if isinstance(i, dict))) != len(items):
        raise PolicyError("duplicate knowledge ids")
    for i in items:
        validate_entry(i)
    computed_probes = [run_probe(i) for i in items]
    if probes != computed_probes:
        raise PolicyError("probe evidence is not reproducible")
    return {"result": "DEMO_VERIFIED", "scope": "PUBLIC_ONLY", "channel": CHANNEL,
            "serial": man["serial"], "knowledge_count": len(items),
            "signature": "VALID", "probe": "SYNTAX_ONLY", "production_approved": False}
