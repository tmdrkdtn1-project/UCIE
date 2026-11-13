"""UCIE B3/B4: real current four-pillar wheel + all 3 pinned vendor wheels on CLEAN Windows.

Actual hash-locked no-index product install, dependency check, native ABI,
four-pillar CLI, Local V04 loopback and uninstall on an ephemeral GitHub VM.
Reuses existing reviewed C1/C2 checks, wheel builder and UI probes; strictly
no owner host/keys/data and no customer distribution or independent owner
physical receiver acceptance. Public PyPI is ONLY the existing approved
dependency distribution channel, never a UCIE code-learning source.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from ucie_miner import customer_owner_wheelhouse_acquire_v01 as vendor
from ucie_miner import customer_full_product_offline_rehearsal_v01 as full
from ucie_miner import customer_runtime_closure_v01 as runtime
from ucie_miner import customer_private_entitlement_v01 as license_gate
from ucie_miner import customer_functional_ab_lifecycle_v01 as ab

SCHEMA = "UCIE_B3_B4_CLEAN_WINDOWS_CURRENT_FULL_VENDOR_FOUR_PILLAR_V01"
PASS = "B3_B4_CLEAN_WINDOWS_CURRENT_NATIVE_VENDOR_INSTALLED_PASS_CUSTOMER_NO_GO"
FAIL = "B3_B4_FULL_VENDOR_INDEPENDENT_CI_FAIL_CLOSED_CUSTOMER_NO_GO"
REQUIRED_ENV = "UCIE_B3_B4_CURRENT_FULL_VENDOR_CI_ONLY"

# First-party-only synthetic verified license: REAL native Ed25519 provider
# in installed wheel context; no owner's private key or customer identity.
ENTITLEMENT_CHILD = r"""
import json,sys
from datetime import datetime,timedelta,timezone
from hashlib import sha256
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from ucie_public.rulepack import key_id
from ucie_miner import customer_private_entitlement_v01 as gate
from ucie_miner import local_public_pr_owner_auth_v01 as auth
from ucie_miner.customer_staging_v01 import PILLARS
from importlib.metadata import version
import ucie_miner,cryptography,cffi,pycparser
root=Path(sys.argv[1]).resolve()
wheel_sha=sys.argv[2]
vendor_hashes=json.loads(sys.argv[3])
assert Path(ucie_miner.__file__).resolve().is_relative_to(root)
assert Path(cryptography.__file__).resolve().is_relative_to(root)
assert version("ucie-public-only-demo")=="0.1.0"
assert version("cryptography")=="50.0.2"
assert version("cffi")=="2.1.1"
assert version("pycparser")=="3.12"
now=datetime.now(timezone.utc).replace(microsecond=0)
ephemeral=Ed25519PrivateKey.generate()
pub=ephemeral.public_key().public_bytes(
 serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
owner_pin=key_id(ephemeral.public_key())
recipient=sha256(b"UCIE-FICTITIOUS-LICENSED-RECIPIENT-CI-ONLY").hexdigest()
rights=sha256(b"UCIE-NOT-A-LEGAL-SIGNOFF-CI-ONLY").hexdigest()
record={
 "schema":gate.SCHEMA,"scope":gate.SCOPE,"product":gate.DIST,
 "product_version":gate.VERSION,
 "product_wheel_sha256":wheel_sha,
 "vendor_wheels_sha256":vendor_hashes,
 "recipient_token_sha256":recipient,
 "rights_packet_sha256":rights,
 "four_pillars":list(PILLARS),"serial":17,"owner_key_id":owner_pin,
 "issued_utc":auth._stamp(now),
 "expires_utc":auth._stamp(now+timedelta(days=30))}
body,signature=gate.synthetic_fixture_signing_bytes(record,ephemeral)
fixed={
 "record_bytes":body,"signature_bytes":signature,
 "independently_provisioned_public_pem":pub,
 "expected_owner_key_id":owner_pin,"min_serial":17,
 "expected_recipient_token_sha256":recipient,
 "expected_product_wheel_sha256":wheel_sha,
 "expected_vendor_wheels_sha256":vendor_hashes,
 "expected_rights_packet_sha256":rights,
 "now":now+timedelta(seconds=2)}
verified=gate.verify_private_entitlement(**fixed)
assert verified["private_product_ed25519_signature_verified"] is True
assert verified["customer_distribution_authorized"] is False
assert verified["independent_customer_contract_approved"] is False
assert verified["customer_entitlement_issued"] is False
for changed in [
 {"expected_recipient_token_sha256":"f"*64},
 {"expected_product_wheel_sha256":"f"*64},
 {"expected_vendor_wheels_sha256":dict(vendor_hashes,cffi="f"*64)},
 {"min_serial":18},
 {"now":now+timedelta(days=31)}
]:
 try:
  gate.verify_private_entitlement(**dict(fixed,**changed))
  raise AssertionError("untrusted release entitlement accepted")
 except gate.PrivateEntitlementError:
  pass
print(json.dumps({
 "status":"B3_INSTALLED_NATIVE_PRIVATE_ENTITLEMENT_SYNTHETIC_PASS",
 "genuine_ed25519_verified":True,
 "bound_to_exact_checked_product_wheel":True,
 "bound_to_exact_three_pinned_vendor_wheels":True,
 "all_four_pillars_bound":True,
 "wrong_recipient_sha_denied":True,"wheel_tamper_denied":True,
 "wrong_vendor_digest_denied":True,
 "old_serial_denied":True,"expiry_denied":True,
 "actual_owner_private_key_used":False,
 "real_customer_license_issued":False,
 "independent_legal_approval":False,
 "customer_distribution_authorized":False},sort_keys=True))
"""

# Run the entire 18-case real Ed25519 suite INSIDE the newly installed
# SHA/RECORD-verified first-party + native-vendor recipient. Any skip is FAIL.
# Never count an all-skipped unittest suite as an acceptable CI success.
ENTITLEMENT_UNIT_CHILD = r"""
import io,json,sys,unittest
from pathlib import Path
import ucie_miner,cryptography
venv=Path(sys.argv[2]).resolve()
assert Path(ucie_miner.__file__).resolve().is_relative_to(venv)
assert Path(cryptography.__file__).resolve().is_relative_to(venv)
suite=unittest.defaultTestLoader.discover(
 start_dir=str(Path(sys.argv[1])),pattern="test_ucie_customer_private_entitlement_v01.py",
 top_level_dir=str(Path(sys.argv[1])))
output=io.StringIO()
result=unittest.TextTestRunner(stream=output,verbosity=1).run(suite)
if result.testsRun!=18 or len(result.skipped)!=0 or not result.wasSuccessful():
 raise AssertionError("native customer entitlement unit tests did not all run and pass")
print(json.dumps({"status":"C3_REAL_NATIVE_INSTALLED_ENTITLEMENT_TESTS_PASS",
  "executed":result.testsRun,"skipped":len(result.skipped),
  "tests_from_installed_ucie_wheel":True,
  "owner_private_key_used":False,
  "customer_distribution_authorized":False},sort_keys=True))
"""


PRIVATE_SLOTS_CHILD = r"""
import json,sys,os,subprocess
from datetime import datetime,timedelta,timezone
from hashlib import sha256
from pathlib import Path
from http.client import HTTPConnection
from contextlib import closing
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from ucie_public.rulepack import key_id
from ucie_miner import customer_private_entitlement_v01 as c3
from ucie_miner import customer_private_offline_lifecycle_v01 as life
from ucie_miner import local_public_pr_owner_auth_v01 as auth
from ucie_miner.customer_staging_v01 import PILLARS
from importlib.metadata import version
assert version("cryptography")=="50.0.2"
assert version("cffi")=="2.1.1"
assert version("pycparser")=="3.12"
# All 16 lifecycle / genuine A0.1.0/B0.1.1 Ed25519 tests MUST execute
# inside installed first-party + all pinned native vendor wheels.
import unittest,io
tests=unittest.defaultTestLoader.discover(
 start_dir=str(Path(sys.argv[6])),pattern="test_ucie_customer_private_offline_lifecycle_v01.py",
 top_level_dir=str(Path(sys.argv[6])))
executed=unittest.TextTestRunner(stream=io.StringIO()).run(tests)
if executed.testsRun!=16 or executed.skipped or not executed.wasSuccessful():
 raise AssertionError("16 signed customer lifecycle tests skipped or failed")
print("UCIE_STAGE_NATIVE_UNIT_PASS",flush=True)
scratch=Path(sys.argv[1])
product_A=Path(sys.argv[2])
product_B=Path(sys.argv[3])
vendors=Path(sys.argv[4])
vendor_hashes=json.loads(sys.argv[5])
private=Ed25519PrivateKey.generate()  # disposable MEMORY only, never persisted
pub=private.public_key().public_bytes(
 serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
keyid=key_id(private.public_key())
recipient=sha256(b"UCIE-EPHEMERAL-NOT-A-REAL-CUSTOMER").hexdigest()
rights=sha256(b"UCIE-SYNTHETIC-C2-LEGAL-NOT-APPROVED").hexdigest()
now=datetime.now(timezone.utc).replace(microsecond=0)
owner_args={
 "public_pem":pub,"expected_owner_key_id":keyid,
 "expected_recipient_token_sha256":recipient,
 "expected_rights_packet_sha256":rights,"min_serial":60}
bundles=[]
print("UCIE_STAGE_BUNDLE_START",flush=True)
for label,product,version,serial in (
 ("A",product_A,"0.1.0",60),("B",product_B,"0.1.1",61)
):
 rec={
  "schema":c3.SCHEMA,"scope":c3.SCOPE,"product":c3.DIST,
  "product_version":version,
  "product_wheel_sha256":sha256(product.read_bytes()).hexdigest(),
  "vendor_wheels_sha256":vendor_hashes,
  "recipient_token_sha256":recipient,
  "rights_packet_sha256":rights,
  "four_pillars":list(PILLARS),"serial":serial,"owner_key_id":keyid,
  "issued_utc":auth._stamp(now),
  "expires_utc":auth._stamp(now+timedelta(days=30))
 }
 body,sig=c3.synthetic_fixture_signing_bytes(rec,private)
 release=scratch/("private_version_"+label)/life.RELEASE_NAME
 release.parent.mkdir()
 built=life.build_private_qa_bundle(release,product,vendors,body,sig)
 assert built["exact_wheel_count"]==4
 proof=life.verify_private_qa_bundle(release,**owner_args)
 assert proof["real_ed25519_verified"] and proof["product_version"]==version
 assert not proof["customer_distribution_authorized"]
 bundles.append(release)
 print("UCIE_STAGE_BUNDLE_"+label+"_PASS",flush=True)
root=scratch/"separate_disposable_customer"/life.RECIPIENT_NAME
root.parent.mkdir()
print("UCIE_STAGE_INSTALL_A_START",flush=True)
try:
 a=life.install_or_update(root,bundles[0],python=Path(sys.executable),
  consent=life.CONSENT,**owner_args)
except Exception as e:
 # Only static first-party failure strings converted to stage labels.
 tag=type(e).__name__.upper()
 reason=(
  str(e).upper().replace(" ","_")[:60]
  if type(e).__name__ in ("OfflineFullProductError",
                           "OfflineProductLifecycleError") else "NO_DETAIL")
 print("UCIE_STAGE_INSTALL_A_FAILURE_"+tag+"_"+reason,flush=True)
 raise
assert a["previous_slot"] is None and a["real_offline_pip_installed"]
assert root.joinpath(life.LAUNCHER_NAME).read_bytes()==life.LAUNCHER.encode("utf-8")
print("UCIE_STAGE_INSTALL_A_PASS",flush=True)
check=life.verify_selected(root,**owner_args)
assert check["product_version"]=="0.1.0"
# Real version-0.1.0 active installed Python: no reuse of owner D:/UCIE.
trust=scratch/"synthetic_approved_public_only.pem"
trust.write_bytes(pub)
active=root/"slots"/a["active_slot"]
exe=active/"venv"/"Scripts"/"python.exe"
cmd=[str(exe),"-I","-B","-m",
     "ucie_miner.customer_private_offline_lifecycle_v01",
     "--action","serve","--recipient-root",str(root),
     "--public-trust-pem",str(trust),
     "--expected-owner-key-id",keyid,"--recipient-token-sha256",recipient,
     "--rights-packet-sha256",rights,"--min-serial","60","--port","0"]
print("UCIE_STAGE_SERVE_A_START",flush=True)
p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                   text=True,encoding="utf-8",env=dict(os.environ,
                   PYTHONDONTWRITEBYTECODE="1"))
try:
 line=p.stdout.readline()
 status=json.loads(line)
 assert status["status"]=="SIGNED_CUSTOMER_LOCAL_TECHNICAL_PREVIEW_NO_GO"
 assert status["customer_distribution_authorized"] is False
 port=int(status["url"].split(":")[-1].split("/")[0])
 def get(url):
  with closing(HTTPConnection("127.0.0.1",port,timeout=8)) as c:
   c.request("GET",url,headers={"Host":"127.0.0.1:"+str(port)})
   r=c.getresponse()
   return r.status,r.read(400001).decode("utf-8","replace")
 code,health=get("/local/health")
 assert code==200 and json.loads(health)["private_entitlement_reverified_per_request"]
 assert get("/local")[0]==200
 assert get("/local/library?q=Git")[0]==200
 # Actual post-install signature change must DENY the existing UI per request.
 sigfile=active/life.RELEASE_NAME/"entitlement.sig.json"
 original=sigfile.read_bytes()
 sigfile.write_bytes(b"forged signed customer entitlement")
 try:
  code,message=get("/local")
  assert code==403 and "ENTITLEMENT_REVOKED" in message
 finally:
  sigfile.write_bytes(original)
 assert get("/local")[0]==200
 print("UCIE_STAGE_SIGNED_HTTP_PASS",flush=True)
finally:
 p.terminate()
 p.wait(timeout=10)
 if p.poll() is None:
  p.kill();p.wait(timeout=5)
print("UCIE_STAGE_INSTALL_B_START",flush=True)
try:
 b=life.install_or_update(root,bundles[1],python=Path(sys.executable),
  consent=life.CONSENT,**owner_args)
except Exception as e:
 tag=type(e).__name__.upper()
 reason=(str(e).upper().replace(" ","_")[:60]
         if type(e).__name__ in ("OfflineFullProductError",
                                  "OfflineProductLifecycleError") else "NO_DETAIL")
 print("UCIE_STAGE_INSTALL_B_FAILURE_"+tag+"_"+reason,flush=True)
 raise
assert b["active_slot"]!=a["active_slot"]
assert b["previous_slot"]==a["active_slot"]
assert life.verify_selected(root,**owner_args)["product_version"]=="0.1.1"
print("UCIE_STAGE_INSTALL_B_PASS",flush=True)
# Replay floor independent of signed payload blocks legacy rollback.
try:
 life.rollback(root,consent=life.ROLLBACK_CONSENT,
               **dict(owner_args,min_serial=61))
 raise AssertionError("stale A entitlement erroneously rolled back")
except ValueError:
 pass
assert life.verify_selected(root,**owner_args)["product_version"]=="0.1.1"
print("UCIE_STAGE_ROLLBACK_START",flush=True)
rollback=life.rollback(root,consent=life.ROLLBACK_CONSENT,**owner_args)
assert rollback["active_slot"]==a["active_slot"]
assert life.verify_selected(root,**owner_args)["product_version"]=="0.1.0"
# Switching back to signed B remains allowed with the same independent pin.
life.rollback(root,consent=life.ROLLBACK_CONSENT,**owner_args)
assert life.verify_selected(root,**owner_args)["product_version"]=="0.1.1"
print("UCIE_STAGE_REMOVE_START",flush=True)
removed=life.remove_technical_install(root,consent=life.REMOVE_CONSENT)
assert removed["removed_registered_slots"]==2
assert root.is_dir() and list(root.iterdir())==[]
assert not (root/"runtime").exists()
assert not (root/".git").exists()
print(json.dumps({
 "status":"B3_B4_REAL_SIGNED_A_TO_B_TO_A_TO_B_WINDOWS_PRIVATE_SLOT_PASS",
 "product_versions":["0.1.0","0.1.1"],
 "installed_lifecycle_unit_cases_executed":executed.testsRun,
 "installed_lifecycle_unit_cases_skipped":len(executed.skipped),
 "release_candidate_wheels_per_version":4,
 "local_spdx_noassertion_packages":4,
 "product_source_versions_distinct":True,
 "offline_two_installed_native_vendor_slots":True,
 "per_get_signed_recipient_http200_and_after_tamper_http403":True,
 "signed_serial_floor_blocks_stale_rollback":True,
 "real_backward_and_forward_pointer_switching":True,
 "real_private_product_slots_uninstalled":2,
 "launcher_generated_with_zero_embedded_customer_ids_or_private_keys":True,
 "ephemeral_in_memory_ed25519_only":True,
 "real_owner_private_key_used":False,
 "real_owner_license_issued":False,
 "customer_distribution_authorized":False,
},sort_keys=True))
"""


EXTRA_UI_CHILD = r"""
import json
from pathlib import Path
from threading import Thread
from contextlib import closing
from http.client import HTTPConnection
from ucie_miner.local_v1_app_v01 import LOCAL_SERVER_CLASS,make_handler
from ucie_miner.local_portable_official_reference_v01 import NOTE
import sys
root=Path(sys.argv[1])
checks=0
with LOCAL_SERVER_CLASS(("127.0.0.1",0),make_handler(root)) as server:
 t=Thread(target=server.serve_forever,daemon=True);t.start()
 try:
  for section in ("library","evolution"):
   for query,marker in (("Python","docs.python.org"),
                        ("PowerShell","learn.microsoft.com"),
                        ("Git","git-scm.com"),
                        ("MCP","modelcontextprotocol.io")):
    with closing(HTTPConnection("127.0.0.1",server.server_port,timeout=6)) as c:
     c.request("GET","/local/"+section+"?q="+query,
      headers={"Host":"127.0.0.1:"+str(server.server_port)})
     result=c.getresponse()
     body=result.read(400001).decode("utf-8","replace")
     if result.status!=200 or marker not in body or NOTE not in body:
      raise ValueError("installed official-reference Local V04 route mismatch")
     checks+=1
  with closing(HTTPConnection("127.0.0.1",server.server_port,timeout=6)) as c:
   c.request("GET","/local/review?q=Git",
    headers={"Host":"127.0.0.1:"+str(server.server_port)})
   r=c.getresponse();r.read(1024)
   if r.status!=400:raise ValueError("unapproved public PR review admitted")
 finally:
  server.shutdown();t.join(timeout=6)
  if t.is_alive():raise ValueError("UCIE test server leaked")
print(json.dumps({
 "status":"B4_CLEAN_VENDOR_INCLUDED_LOCAL_V04_PASS",
 "installed_official_reference_http_gets":checks,
 "unapproved_public_PR_review_http400":True,
 "customer_release_authorized":False},sort_keys=True))
"""


class FullRecipientQAFailure(ValueError):
    """No customer release from any synthetic install/test result."""


def _scope(root: Path, env: dict[str, str]) -> Path:
    if (type(env) is not dict or not isinstance(root, Path)
            or root.name != "UCIE" or root.is_symlink()
            or not (root / ".git").is_dir() or (root / ".git").is_symlink()
            or sys.platform != "win32" or sys.version_info[:2] != (3, 15)
            or env.get(REQUIRED_ENV) != "1"
            or env.get("GITHUB_ACTIONS") != "true" or env.get("CI") != "true"
            or env.get("RUNNER_OS") != "Windows"
            or env.get("GITHUB_REPOSITORY") != "tmdrkdtn1-project/UCIE"
            or env.get("GITHUB_EVENT_NAME") not in ("pull_request","push")
            or root.resolve() == Path("D:/UCIE").resolve()):
        raise FullRecipientQAFailure("ephemeral GitHub UCIE Windows only")
    tmp = Path(env.get("RUNNER_TEMP", ""))
    if (not tmp.is_dir() or tmp.is_symlink()
            or tmp.resolve().is_relative_to(root.resolve())
            or root.resolve().is_relative_to(tmp.resolve())):
        raise FullRecipientQAFailure("disjoint Windows ephemeral scratch required")
    return tmp


def _pinned_download_command(python: Path, dest: Path) -> list[str]:
    """No source packages, no undeclared dependency names or custom index."""
    if not isinstance(python, Path) or not isinstance(dest, Path):
        raise FullRecipientQAFailure("invalid disposable wheels")
    return [
        str(python), "-I", "-B", "-m", "pip", "--isolated", "download",
        "--only-binary=:all:", "--no-deps", "--no-cache-dir", "--no-input",
        "--disable-pip-version-check", "--timeout", "12", "--retries", "1",
        "--index-url", "https://pypi.org/simple", "--dest", str(dest),
        *(name+"=="+version for name,version in vendor.PINNED)
    ]


def run_clean_vendor_recipient(root: Path, env: dict[str, str]) -> dict:
    parent = _scope(root, env)
    closure = runtime.inspect_static_runtime_closure(root)
    if closure.get("missing_first_party_imports"):
        raise FullRecipientQAFailure("current UCIE source closure incomplete")
    sources = runtime._copy_payload(root, closure)
    safe = {k: env[k] for k in (
        "PATH","SystemRoot","SYSTEMROOT","WINDIR","TEMP","TMP",
        "HOME","USERPROFILE","HOMEDRIVE","HOMEPATH","COMSPEC")
        if k in env}
    safe.update(PYTHONDONTWRITEBYTECODE="1",PIP_DISABLE_PIP_VERSION_CHECK="1")
    scratch_path = None
    observed = {}
    with TemporaryDirectory(prefix="UCIE_B3_B4_REAL_FULL_VENDOR_CI_",dir=parent) as scratch_str:
        scratch=Path(scratch_str)
        scratch_path=scratch
        stage=scratch/"source"/"UCIE"
        stage.parent.mkdir()
        manifest=runtime._stage(stage,sources,runtime.REVISION_A)
        runtime._verify(stage,manifest)
        product_dir=scratch/"product"
        product_dir.mkdir()
        product=full._build_first_party_wheel(product_dir,sources)
        checked=full._inspect_first_party_wheel(product,sources)
        if (checked.get("wheel_record_verified") is not True
                or checked.get("source_code_bytes_match") is not True):
            raise FullRecipientQAFailure("current product source wheel mismatch")
        vendor_dir=scratch/"approved_external_wheels"
        vendor_dir.mkdir()
        # Only network-bearing step: fixed public PyPI dependency distribution.
        full._run(_pinned_download_command(Path(sys.executable),vendor_dir),
                  scratch,safe,"fixed existing C1 vendor PyPI wheels download")
        official={n:vendor._pypi_index(n,v) for n,v in vendor.PINNED}
        capture=vendor.validate_candidate(vendor_dir,official)
        if capture.get("all_wheel_sha256_equal_official_pypi_metadata") is not True:
            raise FullRecipientQAFailure("official PyPI SHA/RECORD mismatch")
        hashes={v["distribution"]:v["sha256"] for v in capture["files"]}
        if set(hashes)!={n for n,_ in vendor.PINNED}:
            raise FullRecipientQAFailure("incomplete 3 dependency hashes")
        # Corrupt one local vendor copy BEFORE any pip install and reject it.
        sample=(vendor_dir/capture["files"][0]["filename"])
        original=sha256(sample.read_bytes()).hexdigest()
        corrupt=scratch/"corrupt_vendor_copy.whl"
        corrupt.write_bytes(sample.read_bytes()+b"UCIE_B3_KNOWN_BAD_APPEND")
        corrupt_rejected=sha256(corrupt.read_bytes()).hexdigest()!=original
        if not corrupt_rejected:
            raise FullRecipientQAFailure("modified external wheel accepted")
        corrupt.unlink()
        required=scratch/"all_four_pillar_hash_locked.txt"
        required.write_text(full._requirements(hashes,checked["sha256"]),encoding="ascii")
        venv=scratch/"fresh_windows_recipient_venv"
        safe_install={**safe,"PIP_NO_INDEX":"1"}
        full._run([sys.executable,"-I","-B","-m","venv",str(venv)],
                  scratch,safe_install,"clean dedicated Windows full product venv")
        child=venv/"Scripts"/"python.exe"
        if child.is_symlink() or not child.is_file():
            raise FullRecipientQAFailure("isolated recipient Python absent")
        full._run(full._install_cmd(child,vendor_dir,product_dir,required),
                  scratch,safe_install,"true resolver hash-locked offline full install")
        full._run([str(child),"-I","-B","-m","pip","--isolated","check",
                   "--disable-pip-version-check"],
                  scratch,safe_install,"full dependency check")
        unit=json.loads(full._run([
            str(child),"-I","-B","-c",ENTITLEMENT_UNIT_CHILD,
            str(root/"tests"),str(venv)],
            scratch,safe_install,"all 18 real installed Ed25519 entitlement tests"))
        if (unit.get("status")!="C3_REAL_NATIVE_INSTALLED_ENTITLEMENT_TESTS_PASS"
                or unit.get("executed")!=18 or unit.get("skipped")!=0
                or unit.get("tests_from_installed_ucie_wheel") is not True):
            raise FullRecipientQAFailure("native installed entitlement tests missing/skipped")
        # Actual installed cryptography and all 3 native vendor package checks.
        native=full._check_native(full._run(
            [str(child),"-I","-B","-c",full.NATIVE_PROBE],
            scratch,safe_install,"installed native cryptography CFFI pycparser smoke"))
        license_probe=json.loads(full._run(
            [str(child),"-I","-B","-c",ENTITLEMENT_CHILD,str(venv),
             checked["sha256"],json.dumps(hashes,sort_keys=True)],
            scratch,safe_install,"installed product Ed25519 license gate synthetic"))
        if (license_probe.get("genuine_ed25519_verified") is not True
                or license_probe.get("wrong_recipient_sha_denied") is not True
                or license_probe.get("wheel_tamper_denied") is not True
                or license_probe.get("customer_distribution_authorized") is not False):
            raise FullRecipientQAFailure("installed product entitlement gate changed")
        # License preview is tested BEFORE launching installed application.
        four=full._check_four_pillars(full._run(
            [str(child),"-I","-B","-m","ucie_miner.customer_staging_v01",
             "--pillar","all"],scratch,safe_install,
            "installed current four complete synthetic product pillars"))
        ui=full._check_ui(full._run([
            str(child),"-I","-B","-c",full.UI_PROBE,str(stage)],
            scratch,safe_install,"installed product Local V04 real localhost"))
        extras=json.loads(full._run([
            str(child),"-I","-B","-c",EXTRA_UI_CHILD,str(stage)],
            scratch,safe_install,"installed 8 real official reference route GETs"))
        if (extras.get("installed_official_reference_http_gets") != 8
                or extras.get("unapproved_public_PR_review_http400") is not True
                or extras.get("customer_release_authorized") is not False):
            raise FullRecipientQAFailure("full vendor included read-only UI misbehaved")
        # Genuine pip uninstall and absence check, then remove entire scratch.
        ab._uninstall(child,scratch,safe_install)
        removed=json.loads(full._run(
            [str(child),"-I","-B","-c",ab.ABSENCE_PROBE],
            scratch,safe_install,"actual installed product uninstall absence"))
        if (removed.get("installed") is not False
                or removed.get("ucie_module_still_present") is not False):
            raise FullRecipientQAFailure("first-party uninstall or cleanup missing")
        # Reinstall the CURRENT whole UCIE product from the very same
        # pinned local wheelhouse; no network or different source accepted.
        full._run(full._install_cmd(child,vendor_dir,product_dir,required),
                  scratch,safe_install,"verified first-party reinstall in same clean venv")
        full._run([str(child),"-I","-B","-m","pip","--isolated","check",
                   "--disable-pip-version-check"],
                  scratch,safe_install,"reinstalled full dependency consistency")
        four_reinstalled=full._check_four_pillars(full._run(
            [str(child),"-I","-B","-m","ucie_miner.customer_staging_v01",
             "--pillar","all"],scratch,safe_install,
            "reinstalled synthetic full UCIE four pillars"))
        if (four_reinstalled["workflow_receipt_sha256"]
                != four["workflow_receipt_sha256"]):
            raise FullRecipientQAFailure("full-product reinstall changed four-pillar behavior")
        # THIS is the new release-critical integration: two genuinely distinct
        # customer product wheels, individually signed and PINNED, each fully
        # installed offline in a NEW independent slot. Observe actual HTTP.
        source_A,source_B=ab._two_sources(sources)
        wheel_A_dir=scratch/"private_release_A_wheel"
        wheel_B_dir=scratch/"private_release_B_wheel"
        wheel_A_dir.mkdir()
        wheel_B_dir.mkdir()
        product_A=full._build_first_party_wheel(
            wheel_A_dir,source_A,version="0.1.0")
        product_B=full._build_first_party_wheel(
            wheel_B_dir,source_B,version="0.1.1")
        full._inspect_first_party_wheel(product_A,source_A,version="0.1.0")
        full._inspect_first_party_wheel(product_B,source_B,version="0.1.1")
        if (sha256(product_A.read_bytes()).hexdigest()
                ==sha256(product_B.read_bytes()).hexdigest()):
            raise FullRecipientQAFailure("A and B product sources not distinct")
        # Bounded CI-only execution with private-key-safe stage-class diagnostics.
        # full._run normally hides failing child stdout/stderr, so a genuine
        # regression could not be fixed without observing this fixed marker.
        run=subprocess.run([
            str(child),"-I","-B","-c",PRIVATE_SLOTS_CHILD,
            str(scratch),str(product_A),str(product_B),str(vendor_dir),
            json.dumps(hashes,sort_keys=True),str(root/"tests")],
            cwd=scratch,env=safe_install,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,text=True,encoding="utf-8",
            errors="replace",timeout=300,check=False)
        if run.returncode!=0:
            stages=[line.strip() for line in run.stdout.splitlines()
                    if re.fullmatch("UCIE_STAGE_[A-Z0-9_]{1,150}",line.strip())]
            last_stage=stages[-1] if stages else "UCIE_STAGE_IMPORT_NOT_COMPLETED"
            error_types=re.findall(r"\b([A-Za-z][A-Za-z0-9_]{0,60}(?:Error|Exception))(?=:|$)",
                                   run.stderr)
            last_error=error_types[-1] if error_types else "UnhandledChild"
            raise FullRecipientQAFailure("technical signed slots "+last_stage+" "+last_error)
        slots=json.loads(run.stdout.strip().splitlines()[-1])
        if (slots.get("status") !=
                "B3_B4_REAL_SIGNED_A_TO_B_TO_A_TO_B_WINDOWS_PRIVATE_SLOT_PASS"
                or slots.get("installed_lifecycle_unit_cases_executed")!=16
                or slots.get("installed_lifecycle_unit_cases_skipped")!=0
                or slots.get("product_source_versions_distinct") is not True
                or slots.get("per_get_signed_recipient_http200_and_after_tamper_http403") is not True
                or slots.get("signed_serial_floor_blocks_stale_rollback") is not True
                or slots.get("real_private_product_slots_uninstalled") != 2
                or slots.get("customer_distribution_authorized") is not False):
            raise FullRecipientQAFailure("real independently signed private slot QA failed")
        ab._uninstall(child,scratch,safe_install)
        observed={
            "official_pypi_sha256_vendor_wheels":hashes,
            "product_wheel_sha256":checked["sha256"],
            "first_party_wheel_sources_exact":True,
            "installed_module_count":checked["file_count"],
            "corrupt_vendor_wheel_rejected_before_install":corrupt_rejected,
            "hash_locked_four_wheel_offline_install":True,
            "pip_dependency_check":True,
            "actual_three_vendor_native_probes":native,
            "real_18_customer_entitlement_unit_tests":unit,
            "signed_four_pillar_entitlement_synthetic":license_probe,
            "four_pillar_installed_cli":four,
            "installed_local_v04":ui,
            "installed_extra_official_route_gets":8,
            "full_signed_product_A_to_B_rollback_uninstall":slots,
            "real_pip_uninstall_first_party":True,
            "current_product_real_reinstall_then_second_uninstall":True,
        }
    if scratch_path is None or scratch_path.exists():
        raise FullRecipientQAFailure("ephemeral Windows recipient not destroyed")
    return {
        "schema": SCHEMA,"status":PASS,
        "scope":"DISPOSABLE_UNRELATED_GITHUB_WINDOWS_VM_CURRENT_GIT_SOURCE_ONLY",
        "observed":observed,
        "current_first_party_and_all_three_vendor_wheels_installed":True,
        "native_vendor_code_ran_in_isolated_recipient":True,
        "synthetic_four_pillars_real_installed":True,
        "same_hash_current_product_reinstall_workflow_unchanged":True,
        "real_signed_source_distinct_A_B_customer_slot_lifecycle_verified":True,
        "signed_anonymous_test_recipient_entitlement_verified_before_cli":True,
        "installed_genuine_crypto_customer_entitlement_unit_tests_18_executed_zero_skips":True,
        "owner_real_private_key_accessed":False,
        "actual_owner_c1_captured_wheels_used":False,
        "actual_physical_owner_controlled_second_windows_recipient_accepted":False,
        "publisher_signature_independently_verified":False,
        "independent_third_party_license_notice_or_security_clearance":False,
        "customer_contract_or_entitlement_issued":False,
        "customer_release_or_distribution_authorized":False,
        "operating_database_writes":0,
        "owner_windows_services_tasks_changed":False,
        "disposable_ci_wheelhouse_and_recipient_removed":True,
    }


def main() -> int:
    try:
        report=run_clean_vendor_recipient(REPO,dict(os.environ))
    except Exception as exc:
        label=type(exc).__name__[:64]
        # No traceback, filesystem paths, key bytes, downloaded wheel or
        # customer data. Only whitelisted first-party hardcoded step labels.
        safe_reason=(str(exc)[:170] if isinstance(
            exc,(FullRecipientQAFailure,full.OfflineFullProductError))
            else "exception_type_only")
        print(json.dumps({
            "schema":SCHEMA,"status":FAIL,
            "failure_type":label,
            "safe_first_party_stage":safe_reason,
            "customer_release_or_distribution_authorized":False,
        },sort_keys=True))
        return 2
    print(json.dumps(report,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
