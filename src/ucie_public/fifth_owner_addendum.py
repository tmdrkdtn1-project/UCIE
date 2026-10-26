"""Manual owner-risk Serial >=5 addendum for *only* the fifth asyncio rule.

The immutable four-rule V2 pack remains separately verified. This V3 addendum
binds its SHA256 and owner key to one newly signed fifth-rule profile; it does
not repackage, silently approve, execute external code, or auto-apply rules.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import tempfile
import zipfile

from cryptography.exceptions import InvalidSignature

from .policy import PolicyError
from .rulepack import (
    canonical_json, digest, key_id, _private_key, _public_key, _valid_outpath,
)
from .production_release import SCOPE, _parse_date
from .owner_release import (
    MODE, _local_clean_sha, validate_live_automated_qa, _check_evidence,
)
from .mixed_release import RULE_ORDER, verify_mixed_owner_release
from .multi_owner_release import _decode
from ucie_miner.static_asyncio_resource import (
    RULE_ID, EVIDENCE as UPSTREAM, UPSTREAM_MERGE,
    inspect_asyncio_protocol_factory_source,
)

SCHEMA = "UCIE_FIFTH_OWNER_RISK_ADDENDUM_V1"
CONFIRM = "AUTHORIZE_UCIE_FIFTH_RULE_MANUAL_OWNER_RISK_SERIAL5"
RISK = (
    "I_ACCEPT_FIFTH_ASYNCIO_MOCK_RUNTIME_AND_NO_INDEPENDENT_QA_"
    "LICENSE_SIGNOFF_OR_FIXED_RELEASE_COVERAGE"
)
BASE_SOURCE_SHA = "81d935b13420b844f7301920e9915a7a3f1a6132"
FILES = frozenset({
    "manifest.json", "rules/fifth.json", "evidence/automated_ci.json",
    "signatures/owner.sig",
})
MAX_PACK_BYTES = 131072
RULE = {
    "rule_id": RULE_ID,
    "pattern": "asyncio protocol_factory exception before a socket/pipe transport owns its resource",
    "upstream": UPSTREAM,
    "upstream_merge_sha": UPSTREAM_MERGE,
    "scanner": "ucie_miner.static_asyncio_resource.inspect_asyncio_protocol_factory_source",
    "affected_observation": "Python 3.15.0 host mocks: three close omissions; v3.15.1 and v3.14.9 official source unpatched",
    "safe_guidance": "Handle protocol_factory failure by closing an acquired socket/pipe and re-raising; verify ownership and exact runtime version",
    "auto_fix": False,
    "owner_approval_mode": MODE,
    "independent_human_qa": False,
    "legal_license_signoff": False,
    "real_os_socket_leak_measured": False,
    "fixed_released_version_verified": False,
}
MANIFEST_KEYS = frozenset({
    "schema", "scope", "approval_mode", "serial",
    "created_utc", "expires_utc", "owner_key_id", "source_commit_sha",
    "parent_serial", "parent_rule_count", "parent_pack_sha256",
    "rule_id", "rule_sha256", "evidence_sha256",
    "owner_risk_accepted", "automated_qa_verified",
    "independent_human_qa_approved", "legal_license_signoff",
    "auto_apply", "external_deployment", "private_project_access",
})


def _parent(base_pack: Path, trust: Path) -> tuple[str, dict]:
    original = verify_mixed_owner_release(base_pack, trust, min_serial=4)
    if (original.get("owner_signature") != "VALID"
            or original.get("serial") != 4
            or original.get("rule_ids") != list(RULE_ORDER)
            or original.get("rule_count") != 4
            or original.get("source_commit_sha") != BASE_SOURCE_SHA
            or original.get("auto_apply") is not False):
        raise PolicyError("not the immutable, exact signed Serial4 parent")
    parent_path = Path(base_pack)
    if parent_path.is_symlink() or not parent_path.is_file():
        raise PolicyError("unsafe parent pack")
    return hashlib.sha256(parent_path.read_bytes()).hexdigest(), original


def _read_pack(path: Path) -> dict[str, bytes]:
    path = Path(path)
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_size > MAX_PACK_BYTES):
        raise PolicyError("unsafe fifth-rule addendum")
    try:
        with zipfile.ZipFile(path, "r") as z:
            infos = z.infolist()
            if (len(infos) != len(FILES)
                    or {x.filename for x in infos} != FILES
                    or any(x.file_size > MAX_PACK_BYTES or x.flag_bits & 1
                           or ((x.external_attr >> 16) & 0o170000) == 0o120000
                           for x in infos)):
                raise PolicyError("noncanonical fifth-rule archive")
            return {x.filename: z.read(x.filename) for x in infos}
    except (OSError, RuntimeError, zipfile.BadZipFile, EOFError) as exc:
        raise PolicyError("unreadable fifth-rule archive") from exc


def publish_fifth_addendum(
        root: Path, owner_private: Path, base_pack: Path,
        owner_trust: Path, output: Path, *,
        run_id: int, serial: int, confirmation: str,
        risk_acceptance: str) -> Path:
    """The only signing entrypoint; fresh explicit consent, no automation."""
    if confirmation != CONFIRM or risk_acceptance != RISK:
        raise PolicyError("fifth rule is not owner-approved for release")
    if type(serial) is not int or not 5 <= serial <= 10000000:
        raise PolicyError("fifth addendum requires Serial 5 or later")
    root = Path(root)
    parent_hash, _ = _parent(base_pack, owner_trust)
    current = _local_clean_sha(root)
    main_ci = validate_live_automated_qa(run_id)
    if main_ci["head_sha"] != current:
        raise PolicyError("signer checkout and live passing main CI differ")
    signer = _private_key(Path(owner_private))
    trust = _public_key(Path(owner_trust))
    if key_id(signer.public_key()) != key_id(trust):
        raise PolicyError("parent and addendum owner keys differ")
    dest = _valid_outpath(root, Path(output))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    rb = canonical_json(RULE)
    eb = canonical_json({
        "main_ci": main_ci,
        "upstream": UPSTREAM,
        "merged_patch_commit": UPSTREAM_MERGE,
        "observed_owner_runtime": "Python 3.15.0 mocked close omitted in three paths",
        "unfixed_official_source_tags": ["v3.14.9", "v3.15.0", "v3.15.1"],
        "independent_human_qa": False,
        "real_os_handle_leak_measured": False,
        "fixed_release_version_verified": False,
    })
    manifest = {
        "schema": SCHEMA, "scope": SCOPE, "approval_mode": MODE,
        "serial": serial,
        "created_utc": now.isoformat().replace("+00:00", "Z"),
        "expires_utc": (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "owner_key_id": key_id(trust), "source_commit_sha": current,
        "parent_serial": 4, "parent_rule_count": 4,
        "parent_pack_sha256": parent_hash,
        "rule_id": RULE_ID,
        "rule_sha256": digest(rb), "evidence_sha256": digest(eb),
        "owner_risk_accepted": True, "automated_qa_verified": True,
        "independent_human_qa_approved": False, "legal_license_signoff": False,
        "auto_apply": False, "external_deployment": False,
        "private_project_access": False,
    }
    mb = canonical_json(manifest)
    fd, temp = tempfile.mkstemp(
        dir=str(dest.parent), prefix=".ucie_fifth_", suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as handle:
            with zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, payload in (
                    ("manifest.json", mb), ("rules/fifth.json", rb),
                    ("evidence/automated_ci.json", eb),
                    ("signatures/owner.sig", signer.sign(mb)),
                ):
                    archive.writestr(name, payload)
        os.link(temp, dest)  # fail closed: never overwrite an issued pack
    finally:
        Path(temp).unlink(missing_ok=True)
    return dest


def verify_fifth_addendum(
        pack: Path, base_pack: Path, trust: Path, *,
        min_serial: int = 5, at_time: datetime | None = None) -> dict:
    if type(min_serial) is not int or not 5 <= min_serial <= 10000000:
        raise PolicyError("invalid minimum fifth rule serial")
    parent_hash, _ = _parent(base_pack, trust)
    blobs = _read_pack(pack)
    pub = _public_key(Path(trust))
    man = _decode(blobs["manifest.json"])
    rule = _decode(blobs["rules/fifth.json"])
    evidence = _decode(blobs["evidence/automated_ci.json"])
    if (type(man) is not dict or set(man) != MANIFEST_KEYS
            or man["schema"] != SCHEMA or man["scope"] != SCOPE
            or man["approval_mode"] != MODE
            or man["owner_key_id"] != key_id(pub)
            or type(man["serial"]) is not int or man["serial"] < min_serial
            or man["parent_serial"] != 4 or man["parent_rule_count"] != 4
            or man["parent_pack_sha256"] != parent_hash
            or man["rule_id"] != RULE_ID
            or man["rule_sha256"] != digest(blobs["rules/fifth.json"])
            or man["evidence_sha256"] != digest(blobs["evidence/automated_ci.json"])
            or man["owner_risk_accepted"] is not True
            or man["automated_qa_verified"] is not True
            or man["independent_human_qa_approved"] is not False
            or man["legal_license_signoff"] is not False
            or man["auto_apply"] is not False
            or man["external_deployment"] is not False
            or man["private_project_access"] is not False
            or rule != RULE):
        raise PolicyError("unapproved or changed fifth-rule addendum")
    if type(evidence) is not dict or set(evidence) != {
        "main_ci", "upstream", "merged_patch_commit",
        "observed_owner_runtime", "unfixed_official_source_tags",
        "independent_human_qa", "real_os_handle_leak_measured",
        "fixed_release_version_verified",
    }:
        raise PolicyError("fifth evidence shape mismatch")
    _check_evidence(evidence["main_ci"])
    if (evidence["upstream"] != UPSTREAM
            or evidence["merged_patch_commit"] != UPSTREAM_MERGE
            or evidence["observed_owner_runtime"] !=
               "Python 3.15.0 mocked close omitted in three paths"
            or evidence["unfixed_official_source_tags"] !=
               ["v3.14.9", "v3.15.0", "v3.15.1"]
            or evidence["independent_human_qa"] is not False
            or evidence["real_os_handle_leak_measured"] is not False
            or evidence["fixed_release_version_verified"] is not False
            or evidence["main_ci"]["head_sha"] != man["source_commit_sha"]):
        raise PolicyError("fifth evidence overclaim or altered source")
    try:
        pub.verify(blobs["signatures/owner.sig"], blobs["manifest.json"])
    except (InvalidSignature, ValueError) as exc:
        raise PolicyError("fifth owner signature invalid") from exc
    now = at_time or datetime.now(timezone.utc)
    created = _parse_date(man["created_utc"])
    expires = _parse_date(man["expires_utc"])
    if (now.tzinfo is None or created > now + timedelta(minutes=5)
            or now >= expires or expires <= created
            or expires - created > timedelta(days=7)):
        raise PolicyError("fifth addendum outside signed expiry")
    return {
        "result": "FIFTH_OWNER_RISK_ADDENDUM_VERIFIED",
        "serial": man["serial"], "parent_serial": 4,
        "parent_rule_count": 4, "additional_signed_rules": 1,
        "rule_id": RULE_ID, "owner_signature": "VALID",
        "scope": SCOPE, "source_commit_sha": man["source_commit_sha"],
        "independent_human_qa_approved": False,
        "legal_license_signoff": False, "auto_apply": False,
        "external_deployment": False,
    }


def scan_fifth_addendum(
        pack: Path, base_pack: Path, trust: Path, source: str, *,
        min_serial: int = 5) -> dict:
    verified = verify_fifth_addendum(
        pack, base_pack, trust, min_serial=min_serial)
    result = inspect_asyncio_protocol_factory_source(source)
    return {
        "schema": "UCIE_FIFTH_SIGNED_MANUAL_SCAN_V1",
        "status": result["status"],
        "owner_signature": verified["owner_signature"],
        "pack_serial": verified["serial"],
        "parent_serial": 4, "rule_id": RULE_ID,
        "source_sha256": result["source_sha256"],
        "finding_count": result["candidate_count"],
        "findings": result["candidates"],
        "source_executed": False, "source_files_read": 0,
        "persistent_writes": 0, "auto_fix_applied": False,
        "independent_human_qa_approved": False,
        "runtime_bug_confirmed_for_input": False,
    }
