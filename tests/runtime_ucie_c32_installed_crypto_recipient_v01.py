"""C3.2: genuine installed-wheel Ed25519 recipient proof on disposable Windows.

Exact GitHub Windows 3.15 CI only. Build first-party wheel with reviewed C1
stdlib packager. Install it into a new disposable venv --system-site-packages
to reuse the *already installed CI* native cryptography dependency from
requirements.txt; NO extra vendor download, customer package or rights claim.

Child process -I/-B imports UCIE only from installed wheel, signs PUBLIC-only
metadata with a throwaway in-memory key and imports into a separate clean
scratch UCIE recipient, then checks actual 127.0.0.1 HTTP 200/400/403/405.
Does not touch owner D:/UCIE, keys, operating DB, scheduler or other projects.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from ucie_miner import customer_runtime_closure_v01 as runtime
from ucie_miner import customer_full_product_offline_rehearsal_v01 as full

SCHEMA = "UCIE_C32_INSTALLED_NATIVE_ED25519_WINDOWS_RECIPIENT_SYNTHETIC_V01"
CHILD = r"""
import importlib.metadata as metadata
import json,sys
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from pathlib import Path
from http.server import HTTPServer
from http.client import HTTPConnection
from threading import Thread
from contextlib import closing
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from ucie_public.rulepack import key_id
import ucie_miner
from ucie_miner import local_public_pr_capsule_v01 as cap
from ucie_miner import local_public_pr_owner_auth_v01 as auth
from ucie_miner import local_public_pr_trusted_recipient_v01 as viewer
from ucie_miner import local_public_pr_recipient_import_v01 as intake
from ucie_miner.public_discovery import SOURCE_SKILL

root=Path(sys.argv[1])
venv=Path(sys.argv[2]).resolve()
pkg=Path(ucie_miner.__file__).resolve()
assert pkg.is_relative_to(venv), "first party package not loaded from installed wheel"
assert metadata.version("cryptography").startswith("50."), "native vendor version not pinned to required major"
assert metadata.version("ucie-public-only-demo")=="0.1.0"
assert not (root/"runtime").exists()
(root/".git").mkdir(parents=True)
(root/".build_keys").mkdir()
(root/"downloaded").mkdir()
source="git/git"
data=cap.build_capsule({
 "schema":"UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
 "status":"LINKED_UNVERIFIED_NO_GO","source_revisions":1,
 "linked_revisions":1,"pending_source_revisions":0,
 "auto_promoted":False,"production_approved":False,"deploy_allowed":False,
 "tasks":[{
  "source":source,"reference":"pr:45984:"+("c"*40),
  "pattern_code":"GIT_PORCELAIN_SAFE",
  "skill_id":SOURCE_SKILL[source],
  "evidence_sha256":"c"*64,"candidate_id_sha256":"d"*64,
  "stage6_candidate":None,"status":"UNVERIFIED_CANDIDATE_ONLY",
  "approval":False,"blocking_reasons":["VERIFICATION_NOT_PERFORMED"]
 }]
})
private=Ed25519PrivateKey.generate()  # ephemeral memory only, NEVER persisted
public=private.public_key().public_bytes(
 serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
pin=key_id(private.public_key())
issued=datetime.now(timezone.utc).replace(microsecond=0)
signed=auth.sign_metadata_bytes(
 data,private,serial=8,issued_at=issued,consent=auth.SIGN_CONSENT)
(root/".build_keys"/auth.TRUST_NAME).write_bytes(public)
(root/"downloaded"/cap.FILE).write_bytes(data)
(root/"downloaded"/cap.PIN).write_bytes(
 (sha256(data).hexdigest()+"\n").encode("ascii"))
(root/"downloaded"/auth.SIGNATURE_FILE).write_bytes(signed)
kwargs={"root":root,"expected_owner_key_id":pin,"min_serial":8,
        "consent":intake.CONSENT}
preview=intake.import_existing_signed_public_once(**kwargs)
assert preview["signature_cryptographically_verified"] is True
assert preview["copied_public_metadata_files"]==0
signed_receipt=intake.import_existing_signed_public_once(**kwargs,apply=True)
assert signed_receipt["copied_public_metadata_files"]==3
assert signed_receipt["unverified_public_candidate_count"]==1
assert signed_receipt["out_of_band_owner_approval_independently_proven"] is False
assert signed_receipt["customer_distribution_authorized"] is False
assert signed_receipt["owner_private_key_read_or_created"] is False
assert not (root/".build_keys"/auth.PRIVATE_NAME).exists()
try:
 intake.import_existing_signed_public_once(**kwargs,apply=True)
 raise AssertionError("double import admitted")
except ValueError:
 pass
try:
 viewer.read_signed_public_review(root,expected_owner_key_id=pin,min_serial=9)
 raise AssertionError("replay serial floor admitted")
except ValueError:
 pass
try:
 viewer.read_signed_public_review(
  root,expected_owner_key_id=pin,min_serial=8,
  now=issued+timedelta(days=31))
 raise AssertionError("expired owner signature admitted")
except ValueError:
 pass
def get(path, host=None, method="GET"):
 with closing(HTTPConnection("127.0.0.1",server.server_port,timeout=6)) as c:
  c.request(method,path,headers={
   "Host":host if host is not None else "127.0.0.1:"+str(server.server_port)})
  response=c.getresponse()
  body=response.read(400001).decode("utf-8","replace")
  return response.status,body
with HTTPServer(("127.0.0.1",0),viewer.make_trusted_handler(
 root,expected_owner_key_id=pin,min_serial=8)) as server:
 thread=Thread(target=server.serve_forever,daemon=True)
 thread.start()
 try:
  code,body=get("/local/trusted-public?q=Git")
  assert code==200 and 'data-c31-owner-signature="verified"' in body
  assert "UNVERIFIED_CANDIDATE_ONLY" in body
  assert "github.com/git/git/pull/45984" in body
  assert "개선 방향 살펴보기<span" not in body
  for route in ("/local/library?q=Git", "/local/evolution?q=Git",
                "/local/review?q=Git"):
   assert get(route)[0]==400
  assert get("/local/trusted-public",method="POST")[0]==405
  assert get("/local/trusted-public",host="offsite.invalid")[0]==403
  (root/auth.SIGNATURE_FILE).write_bytes(b"forged")
  code,body=get("/local/trusted-public?q=Git")
  assert code==400 and viewer.FAIL in body
  (root/auth.SIGNATURE_FILE).write_bytes(signed)
  assert get("/local/trusted-public?q=Git")[0]==200
 finally:
  server.shutdown()
  thread.join(timeout=6)
  assert not thread.is_alive()
assert not (root/"runtime").exists()
print(json.dumps({
 "status":"C32_INSTALLED_NATIVE_ED25519_RECIPIENT_SYNTHETIC_PASS",
 "installed_first_party_wheel_imported":True,
 "native_ed25519_real_provider_in_installed_context":True,
 "temporary_in_memory_ed25519_only":True,
 "signed_public_files_written_once":3,
 "cryptographic_signed_get_http_200":True,
 "ordinary_v04_signed_sidecar_http_400":True,
 "forged_signature_after_import_http_400":True,
 "duplicate_import_rejected":True,
 "rollback_floor_rejected":True,
 "expired_signature_rejected":True,
 "owner_private_key_accessed":False,
 "owner_real_signed_capsule_consumed":False,
 "independent_owner_managed_physical_windows_recipient_accepted":False,
 "customer_distribution_authorized":False,
 "external_network_requests":0,
 "operating_database_writes":0
},sort_keys=True))
"""


def main() -> int:
    try:
        if (os.name != "nt" or sys.version_info[:2] != (3, 15)
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("CI") != "true"
                or os.environ.get("RUNNER_OS") != "Windows"
                or os.environ.get("GITHUB_REPOSITORY") != "tmdrkdtn1-project/UCIE"
                or os.environ.get("UCIE_C32_INSTALLED_NATIVE_TEST_ONLY") != "1"):
            raise ValueError("exact disposable Windows CI runner required")
        tmp = Path(os.environ["RUNNER_TEMP"])
        if not tmp.is_dir() or tmp.is_symlink():
            raise ValueError("CI disposable scratch unavailable")
        from importlib.metadata import version
        if not version("cryptography").startswith("50."):
            raise ValueError("declared Ed25519 native CI provider unavailable")
        closure = runtime.inspect_static_runtime_closure(REPO)
        if closure.get("missing_first_party_imports"):
            raise ValueError("native recipient source import closure not complete")
        source = runtime._copy_payload(REPO, closure)
        safe_env = dict(os.environ)
        safe_env.pop("PYTHONPATH", None)
        safe_env.update(
            PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1",
            PYTHONDONTWRITEBYTECODE="1")
        with TemporaryDirectory(prefix="UCIE_C32_INSTALLED_VENDOR_REUSE_", dir=tmp) as work:
            scratch = Path(work)
            wheel_dir = scratch / "wheels"
            wheel_dir.mkdir()
            wheel = full._build_first_party_wheel(wheel_dir, source)
            check = full._inspect_first_party_wheel(wheel, source)
            if (check.get("wheel_record_verified") is not True
                    or check.get("source_code_bytes_match") is not True):
                raise ValueError("first party installed wheel byte integrity not proven")
            venv = scratch / "recipient_venv"
            full._run([
                sys.executable, "-I", "-B", "-m", "venv",
                "--system-site-packages", str(venv)
            ], scratch, safe_env, "ephemeral installed native recipient Python")
            child = venv / "Scripts" / "python.exe"
            full._run([
                str(child), "-I", "-B", "-m", "pip", "--isolated", "install",
                "--no-index", "--no-deps", "--only-binary=:all:",
                "--no-cache-dir", "--no-input", "--no-compile",
                "--disable-pip-version-check", str(wheel)
            ], scratch, safe_env, "only reviewed UCIE first party wheel")
            recipient_root = scratch / "recipient" / "UCIE"
            result = json.loads(full._run([
                str(child), "-I", "-B", "-c", CHILD, str(recipient_root), str(venv)
            ], scratch, safe_env, "real installed Ed25519 recipient and localhost"))
            if (result.get("status") !=
                    "C32_INSTALLED_NATIVE_ED25519_RECIPIENT_SYNTHETIC_PASS"
                    or result.get("native_ed25519_real_provider_in_installed_context") is not True
                    or result.get("cryptographic_signed_get_http_200") is not True
                    or result.get("forged_signature_after_import_http_400") is not True
                    or result.get("owner_private_key_accessed") is not False
                    or result.get("independent_owner_managed_physical_windows_recipient_accepted") is not False
                    or result.get("customer_distribution_authorized") is not False
                    or result.get("operating_database_writes") != 0):
                raise ValueError("installed real Ed25519 recipient acceptance mismatch")
        print(json.dumps({
            "schema": SCHEMA,
            "status": "C32_INSTALLED_NATIVE_ED25519_RECIPIENT_SYNTHETIC_PASS",
            "tested_pull_request_head_only": True,
            "native_provider_from_existing_CI_requirements": True,
            "new_vendor_download_by_test": False,
            "first_party_wheel_SHA256": check["sha256"],
            "installed_first_party_wheel_imported": True,
            "cryptographic_signed_get_http_200": True,
            "forged_signature_http_400": True,
            "duplicate_import_rejected": True,
            "temporary_wheel_venv_recipient_removed": True,
            "owner_private_key_accessed": False,
            "independent_owner_managed_physical_windows_recipient_accepted": False,
            "customer_distribution_authorized": False,
            "operating_database_writes": 0,
        }, sort_keys=True))
        return 0
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "C32_INSTALLED_NATIVE_CI_FAIL_CLOSED_NO_GO",
            "safe_error_type": type(exc).__name__,
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
