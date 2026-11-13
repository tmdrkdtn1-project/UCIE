"""UCIE C2: one-shot official PyPI *metadata* advisory/provenance review.

Exactly the three existing C1-pinned dependencies. PyPI is used ONLY as the
owner-approved dependency distribution/index, NEVER as an added mining source.
No wheel download, package install, source execution, scheduler, operating DB,
private key or customer data. A PyPI-served attestation is *not* independently
cryptographically verified here and cannot authorize distribution.

The live network mode is EXPLICITLY selected; default is inert offline plan.
"""
from __future__ import annotations

import argparse
from base64 import b64decode, b64encode
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .customer_owner_wheelhouse_acquire_v01 import PINNED, RECEIPT, HOST_ROOT, verify_local
from .customer_offline_dependency_gate_v01 import WHEELHOUSE

SCHEMA = "UCIE_C2_PINNED_OFFICIAL_PYPI_ADVISORY_PROVENANCE_V01"
STATUS = "C2_PINNED_PUBLIC_METADATA_REVIEW_ONLY_CUSTOMER_NO_GO"
CONSENT = "REVIEW_UCIE_C2_FIXED_PYPI_METADATA_ONCE"
OFFLINE_STATUS = "C2_OFFLINE_FIXED_PYPI_REVIEW_PLAN_NO_NETWORK_NO_GO"
FAIL_STATUS = "C2_PINNED_PYPI_METADATA_UNAVAILABLE_OR_INVALID_NO_GO"
PYPI = "https://pypi.org"
MAX_RELEASE_BYTES = 2_500_000
MAX_ATTESTATION_BYTES = 1_800_000
MAX_ITEMS = 180
SHA = re.compile(r"[0-9a-f]{64}\Z")
VULN_ID = re.compile(r"[A-Za-z0-9_.-]{1,90}\Z")
# Bounded CI public-only examples; no assumption that these are the actual
# selected owner wheel filenames (owner mode uses verified C1 receipt instead).
PUBLIC_TEST_ONLY = {
    "cryptography": "cryptography-50.0.2-cp315-abi3.abi3t-win_amd64.whl",
    "cffi": "cffi-2.1.1-cp315-cp315-win_amd64.whl",
    "pycparser": "pycparser-3.12-py3-none-any.whl",
}


class C2PublicReviewError(ValueError):
    """Never convert malformed/unsupported public claims into release GO."""


def _distinct(pairs):
    if len({k for k, _ in pairs}) != len(pairs):
        raise C2PublicReviewError("ambiguous external JSON fields")
    return dict(pairs)


def _parse(data: bytes, maximum: int) -> dict:
    if type(data) is not bytes or not 0 < len(data) <= maximum:
        raise C2PublicReviewError("invalid bounded official metadata bytes")
    try:
        obj = json.loads(data.decode("utf-8"), object_pairs_hook=_distinct,
                         parse_constant=lambda _: (_ for _ in ()).throw(
                             C2PublicReviewError("nonfinite official JSON")))
    except (TypeError, UnicodeError, ValueError) as exc:
        raise C2PublicReviewError("untrusted official JSON") from exc
    if type(obj) is not dict:
        raise C2PublicReviewError("official JSON must be an object")
    return obj


def _official_release_url(name: str, version: str) -> str:
    if (name, version) not in PINNED:
        raise C2PublicReviewError("unapproved PyPI dependency version")
    return PYPI + "/pypi/" + name + "/" + version + "/json"


def _provenance_url(name: str, version: str, filename: str) -> str:
    if (name, version) not in PINNED or not _filename(name, version, filename):
        raise C2PublicReviewError("unapproved per-file PyPI integrity endpoint")
    return PYPI + "/integrity/" + name + "/" + version + "/" + filename + "/provenance"


def _filename(name: str, version: str, filename: str) -> bool:
    return (type(filename) is str and len(filename) <= 170
            and filename.startswith(name + "-" + version + "-")
            and filename.endswith(".whl")
            and re.fullmatch(r"[A-Za-z0-9_.+-]+\.whl", filename) is not None
            and ".." not in filename)


class _NoRedirect(HTTPRedirectHandler):
    """Fail before following redirects to any unapproved host or endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _allowed_endpoint(url: str, *, integrity: bool) -> bool:
    if type(url) is not str:
        return False
    for name, version in PINNED:
        if not integrity and url == _official_release_url(name, version):
            return True
        if integrity:
            prefix = PYPI + "/integrity/" + name + "/" + version + "/"
            suffix = "/provenance"
            if url.startswith(prefix) and url.endswith(suffix):
                filename = url[len(prefix):-len(suffix)]
                if _filename(name, version, filename):
                    return True
    return False


def _get_json(url: str, *, integrity: bool = False) -> dict | None:
    """Only fixed release/approved wheel routes, never follow redirects."""
    if not _allowed_endpoint(url, integrity=integrity):
        raise C2PublicReviewError("unapproved official metadata endpoint denied")
    headers = {
        "Accept": "application/vnd.pypi.integrity.v1+json" if integrity
                  else "application/json",
        "User-Agent": "UCIE-C2-owner-pinned-metadata-review/1.0",
    }
    try:
        with build_opener(_NoRedirect).open(Request(url, headers=headers), timeout=12) as reply:
            if reply.status != 200 or reply.geturl() != url:
                raise C2PublicReviewError("unexpected PyPI redirect/status")
            payload = reply.read(
                (MAX_ATTESTATION_BYTES if integrity else MAX_RELEASE_BYTES) + 1)
    except HTTPError as exc:
        if integrity and exc.code == 404 and exc.geturl() == url:
            return None
        raise C2PublicReviewError("required official PyPI metadata unavailable") from exc
    except (URLError, OSError, ValueError) as exc:
        raise C2PublicReviewError("official PyPI network metadata unavailable") from exc
    return _parse(payload, MAX_ATTESTATION_BYTES if integrity else MAX_RELEASE_BYTES)


def _parse_vulnerabilities(release: dict) -> tuple[list[str], int]:
    vulns = release.get("vulnerabilities")
    if type(vulns) is not list or len(vulns) > 80:
        raise C2PublicReviewError("official PyPI advisory snapshot is incomplete")
    ids = []
    withdrawn = 0
    seen = set()
    for entry in vulns:
        if type(entry) is not dict or not isinstance(entry.get("id"), str):
            raise C2PublicReviewError("malformed official advisory entry")
        ident = entry["id"]
        if VULN_ID.fullmatch(ident) is None or ident in seen:
            raise C2PublicReviewError("invalid or duplicate advisory identifier")
        seen.add(ident)
        field = entry.get("withdrawn")
        if field is not None:
            if type(field) is not str or len(field) > 80:
                raise C2PublicReviewError("untrusted advisory withdrawal")
            withdrawn += 1
        else:
            ids.append(ident)
    return sorted(ids), withdrawn


def _parse_pypi_provenance(blob: dict | None, *, filename: str,
                           expected_sha256: str) -> dict:
    """Check a *claimed* PEP740 subject digest, NOT Sigstore cryptography."""
    if blob is None:
        return {
            "pypi_integrity_endpoint_has_attestation": False,
            "pypi_attestation_subject_digest_matches": False,
            "publisher_signature_cryptographically_verified_by_ucie": False,
            "pypi_publisher_claim": None,
            "attestation_absent_or_unavailable_at_query": True,
        }
    if (type(blob.get("version")) is not int
            or blob["version"] != 1
            or type(blob.get("attestation_bundles")) is not list
            or not 1 <= len(blob["attestation_bundles"]) <= 4):
        raise C2PublicReviewError("unsupported PyPI provenance object")
    matching = []
    claimed_publisher = []
    for bundle in blob["attestation_bundles"]:
        if type(bundle) is not dict or type(bundle.get("publisher")) is not dict:
            raise C2PublicReviewError("invalid provenance publisher")
        publisher = bundle["publisher"]
        kind, repo = publisher.get("kind"), publisher.get("repository")
        if (type(kind) is not str or len(kind) > 35
                or type(repo) is not str or len(repo) > 160
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)):
            raise C2PublicReviewError("unsafe provenance publisher claim")
        entries = bundle.get("attestations")
        if type(entries) is not list or not 1 <= len(entries) <= 2:
            raise C2PublicReviewError("invalid provenance attestations")
        claimed_publisher.append(kind + ":" + repo)
        for att in entries:
            if type(att) is not dict or type(att.get("envelope")) is not dict:
                raise C2PublicReviewError("unsupported provenance envelope")
            statement = att["envelope"].get("statement")
            if type(statement) is not str or not 0 < len(statement) <= 500_000:
                raise C2PublicReviewError("oversized provenance statement")
            try:
                decoded = b64decode(statement, validate=True)
            except (ValueError, UnicodeError) as exc:
                raise C2PublicReviewError("bad provenance statement encoding") from exc
            if b64encode(decoded).decode("ascii") != statement:
                raise C2PublicReviewError("noncanonical provenance statement")
            data = _parse(decoded, 300_000)
            subjects = data.get("subject")
            if type(subjects) is not list or not 1 <= len(subjects) <= 8:
                raise C2PublicReviewError("unbounded provenance subjects")
            for sub in subjects:
                if type(sub) is not dict or type(sub.get("digest")) is not dict:
                    raise C2PublicReviewError("malformed provenance digest")
                digest = sub["digest"].get("sha256")
                if type(digest) is not str or SHA.fullmatch(digest) is None:
                    raise C2PublicReviewError("provenance digest invalid")
                if sub.get("name") == filename and digest == expected_sha256:
                    matching.append(True)
                elif sub.get("name") == filename:
                    raise C2PublicReviewError("PyPI provenance SHA differs from wheel SHA")
    if not matching:
        raise C2PublicReviewError("provenance has no exact matching wheel subject")
    return {
        "pypi_integrity_endpoint_has_attestation": True,
        "pypi_attestation_subject_digest_matches": True,
        "publisher_signature_cryptographically_verified_by_ucie": False,
        "pypi_publisher_claim": sorted(set(claimed_publisher))[:4],
        "attestation_absent_or_unavailable_at_query": False,
    }


def assess_pinned_release(name: str, version: str, filename: str,
                          digest: str, release: dict,
                          provenance: dict | None) -> dict:
    """Strict identity/SHA/advisory/provenance separation. Always customer NO_GO."""
    if ((name, version) not in PINNED or not _filename(name, version, filename)
            or type(digest) is not str or SHA.fullmatch(digest) is None):
        raise C2PublicReviewError("untrusted wheel release identity or digest")
    info = release.get("info")
    files = release.get("urls")
    if (type(info) is not dict or info.get("name", "").lower() != name
            or info.get("version") != version
            or type(files) is not list or not 1 <= len(files) <= MAX_ITEMS):
        raise C2PublicReviewError("PyPI release identity or file list changed")
    selected = [f for f in files if type(f) is dict and f.get("filename") == filename]
    if len(selected) != 1:
        raise C2PublicReviewError("exact pinned wheel absent/duplicated in PyPI release")
    row = selected[0]
    official = row.get("digests")
    if (row.get("packagetype") != "bdist_wheel"
            or type(official) is not dict
            or official.get("sha256") != digest
            or row.get("yanked") is True):
        raise C2PublicReviewError("PyPI wheel SHA mismatch or yanked release")
    active_ids, withdrawn = _parse_vulnerabilities(release)
    proof = _parse_pypi_provenance(
        provenance, filename=filename, expected_sha256=digest)
    return {
        "distribution": name,
        "version": version,
        "pypi_release_url": _official_release_url(name, version),
        "wheel_filename": filename,
        "official_pypi_sha256_matches_supplied_pin": True,
        "pypi_versioned_advisory_count": len(active_ids),
        "pypi_versioned_advisory_ids": active_ids,
        "withdrawn_advisory_count": withdrawn,
        "no_reported_vulnerabilities_does_not_prove_security": True,
        **proof,
        "vendor_license_legal_review_completed": False,
        "customer_distribution_authorized": False,
    }


def _public_release_filenames() -> dict[str, str]:
    if set(PUBLIC_TEST_ONLY) != {n for n, _ in PINNED}:
        raise C2PublicReviewError("unexpected public PyPI pin plan")
    return dict(PUBLIC_TEST_ONLY)


def review_once(*, owner_capture: dict[str, dict] | None = None) -> dict:
    """Only explicit one-shot calls, three official release JSONs (+ provenance)."""
    if owner_capture is None:
        files = {n: {"filename": fn} for n, fn in _public_release_filenames().items()}
        captured = False
    else:
        if type(owner_capture) is not dict or set(owner_capture) != {n for n, _ in PINNED}:
            raise C2PublicReviewError("owner C1 capture scope changed")
        files = owner_capture
        captured = True
    result = []
    for name, version in PINNED:
        filename = files[name].get("filename")
        if not _filename(name, version, filename):
            raise C2PublicReviewError("unsupported Windows-target owner wheel")
        release = _get_json(_official_release_url(name, version))
        if release is None:
            raise C2PublicReviewError("missing official PyPI release")
        rows = release.get("urls")
        if type(rows) is not list or len(rows) > MAX_ITEMS:
            raise C2PublicReviewError("invalid official release files")
        matches = [x for x in rows if type(x) is dict and x.get("filename") == filename]
        if len(matches) != 1 or type(matches[0].get("digests")) is not dict:
            raise C2PublicReviewError("public wheel name/digest not found in versioned metadata")
        external_digest = matches[0]["digests"].get("sha256")
        if not isinstance(external_digest, str):
            raise C2PublicReviewError("missing official SHA")
        selected_digest = files[name].get("sha256") if captured else external_digest
        provenance = _get_json(_provenance_url(name, version, filename), integrity=True)
        result.append(assess_pinned_release(
            name, version, filename, selected_digest, release, provenance))
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "evaluated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "THREE_PREEXISTING_C1_PINS_PYPI_METADATA_ONLY",
        "actual_owner_wheel_captured_and_crosschecked": captured,
        "packages": result,
        "packages_checked": len(result),
        "pypi_versioned_advisories_observed": sum(
            x["pypi_versioned_advisory_count"] for x in result),
        "pypi_published_attestation_objects_observed": sum(
            x["pypi_integrity_endpoint_has_attestation"] for x in result),
        "signatures_cryptographically_independently_verified": False,
        "separate_security_and_legal_review_completed": False,
        "private_customer_rights_verified": False,
        "customer_distribution_authorized": False,
        "external_python_code_downloaded_or_executed": False,
        "operating_database_writes": 0,
        "scheduler_modified": False,
    }


def _owner_capture(*, consent: str) -> dict[str, dict]:
    """Require exact owner consent BEFORE reading any C1 wheel or receipt."""
    if consent != CONSENT:
        raise C2PublicReviewError("owner C2 public review consent missing")
    root = HOST_ROOT
    expected_python = root / ".venv" / "Scripts" / "python.exe"
    if (os.name != "nt" or sys.version_info[:2] != (3, 15)
            or bool(os.environ.get("CI"))
            or not sys.stdin.isatty()
            or not (root / ".git").is_dir()
            or root.is_symlink()
            or Path(sys.executable).resolve(strict=True) !=
                expected_python.resolve(strict=True)):
        raise C2PublicReviewError("exact interactive owner Windows UCIE required")
    receipt = verify_local(root)
    if receipt.get("all_local_bytes_match_captured_pypi_digests") is not True:
        raise C2PublicReviewError("C1 captured wheel bytes fail local re-verification")
    path = root / RECEIPT
    if path.is_symlink() or path.stat().st_size > 15_000:
        raise C2PublicReviewError("C1 captured receipt not bounded")
    parsed = _parse(path.read_bytes(), 15_000)
    entries = parsed.get("files")
    if type(entries) is not list or len(entries) != len(PINNED):
        raise C2PublicReviewError("C1 receipt identities not strict")
    files = {}
    for e in entries:
        if type(e) is not dict or (e.get("distribution"), e.get("version")) not in PINNED:
            raise C2PublicReviewError("unexpected captured PyPI distribution")
        name=e["distribution"]
        if name in files or not _filename(name, e["version"], e.get("filename")):
            raise C2PublicReviewError("duplicate or unsafe C1 owner wheel")
        sha=e.get("sha256")
        if type(sha) is not str or SHA.fullmatch(sha) is None:
            raise C2PublicReviewError("invalid captured wheel SHA")
        files[name]={"filename":e["filename"], "sha256":sha}
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="UCIE C2 existing pinned PyPI advisory/provenance read-only review")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--public-one-shot", action="store_true")
    mode.add_argument("--owner-existing-c1-once", action="store_true")
    args = ap.parse_args(argv)
    if not (args.public_one_shot or args.owner_existing_c1_once):
        print(json.dumps({
            "schema": SCHEMA, "status": OFFLINE_STATUS,
            "pinned": [n + "==" + v for n, v in PINNED],
            "network_requests": 0,
            "owner_private_files_accessed": False,
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 0
    try:
        if args.owner_existing_c1_once:
            typed = input("UCIE C2 exact public metadata-only consent: ").strip()
            capture = _owner_capture(consent=typed)
            result = review_once(owner_capture=capture)
        else:
            result = review_once()
    except (ValueError, OSError, EOFError, TypeError, KeyError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": FAIL_STATUS,
            "safe_error_type": type(exc).__name__,
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
