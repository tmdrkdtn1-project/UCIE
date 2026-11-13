"""C4 exact clean Windows: real installed first-party V04 browser + four pillars.

Only UCIE source in a disposable GitHub-hosted Windows Python 3.15 runner.
No third-party wheels, keys, customer data, upload, DB, schedulers or owner PC.
A CI-local preview isn't customer rights/security/second-recipient GO.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from ucie_miner import customer_runtime_closure_v01 as runtime
from ucie_miner import customer_full_product_offline_rehearsal_v01 as full

SCHEMA = "UCIE_C4_CLEAN_WIN315_INSTALLED_CURRENT_SOURCE_V04_NO_VENDOR_V01"
CHILD = """import importlib.util,json,sys
from pathlib import Path
if importlib.util.find_spec("cryptography") is not None:
 print(json.dumps({"status":"VENDOR_PRESENT_DENIED","customer_release_authorized":False}))
else:
 try:
  from ucie_miner.customer_portable_preview_v01 import probe_preview_root
  root=Path(sys.argv[1])
  result=probe_preview_root(root)
  from ucie_miner.local_v1_app_v01 import make_handler,LOCAL_SERVER_CLASS
  from ucie_miner.local_portable_official_reference_v01 import NOTE
  from http.client import HTTPConnection
  from threading import Thread
  from contextlib import closing
  assert not (root/"runtime").exists(), "CI source must not contain owner DB"
  routes=(
    ("/local/library?q=Python","docs.python.org"),
    ("/local/library?q=PowerShell","learn.microsoft.com"),
    ("/local/library?q=Git","git-scm.com"),
    ("/local/library?q=MCP","modelcontextprotocol.io"),
    ("/local/evolution?q=Python","docs.python.org"),
    ("/local/evolution?q=PowerShell","learn.microsoft.com"),
    ("/local/evolution?q=Git","git-scm.com"),
    ("/local/evolution?q=MCP","modelcontextprotocol.io"),
  )
  from ucie_miner.local_portable_official_reference_v01 import STATUS as REF_STATUS
  with LOCAL_SERVER_CLASS(("127.0.0.1",0),make_handler(root)) as server:
   thread=Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    for route,marker in routes:
     with closing(HTTPConnection("127.0.0.1",server.server_port,timeout=6)) as c:
      c.request("GET",route,headers={"Host":"127.0.0.1:"+str(server.server_port)})
      response=c.getresponse();data=response.read(400001).decode("utf-8","replace")
      if (response.status!=200 or marker not in data or NOTE not in data
          or 'data-offline-reference-only="true"' not in data
          or len(data)>400000):
       raise ValueError("installed offline docs route fail closed")
    with closing(HTTPConnection("127.0.0.1",server.server_port,timeout=6)) as c:
     c.request("GET","/local/library?q=Git&page=2",
               headers={"Host":"127.0.0.1:"+str(server.server_port)})
     response=c.getresponse();response.read(1024)
     if response.status!=400:raise ValueError("offline PR pagination admitted")
   finally:
    server.shutdown();thread.join(timeout=5)
    if thread.is_alive():raise ValueError("offline docs server remained running")
  # Genuine installed wheel code consumes one newly generated PUBLIC-ONLY
  # synthetic metadata capsule. No owner ledger, external code or vendor.
  from ucie_miner.local_public_pr_capsule_v01 import (
   FILE as CAP_FILE,PIN as CAP_PIN,build_capsule,inspect_capsule,RECEIVER_STATUS
  )
  from hashlib import sha256
  from ucie_miner.public_discovery import SOURCE_SKILL
  synthetic={
   "schema":"UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
   "status":"LINKED_UNVERIFIED_NO_GO",
   "source_revisions":1,"linked_revisions":1,"pending_source_revisions":0,
   "auto_promoted":False,"production_approved":False,"deploy_allowed":False,
   "tasks":[{
    "source":"git/git","reference":"pr:45984:"+("c"*40),
    "pattern_code":"GIT_PORCELAIN_SAFE",
    "skill_id":SOURCE_SKILL["git/git"],"evidence_sha256":"c"*64,
    "candidate_id_sha256":"d"*64,"stage6_candidate":None,
    "status":"UNVERIFIED_CANDIDATE_ONLY","approval":False,
    "blocking_reasons":["VERIFICATION_NOT_PERFORMED"]
   }]
  }
  payload=build_capsule(synthetic)
  digest=sha256(payload).hexdigest()
  check=inspect_capsule(payload,digest)
  if check["selected_count"]!=1 or check["signature_verified"] is not False:
   raise ValueError("synthetic capsule did not remain unapproved")
  (root/CAP_FILE).write_bytes(payload)
  (root/CAP_PIN).write_bytes((digest+"\\n").encode("ascii"))
  imported_routes=(
   "/local/library?q=Git","/local/evolution?q=Git","/local/error?q=Git")
  with LOCAL_SERVER_CLASS(("127.0.0.1",0),make_handler(root)) as server:
   thread=Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    for route in imported_routes:
     with closing(HTTPConnection("127.0.0.1",server.server_port,timeout=6)) as c:
      c.request("GET",route,headers={"Host":"127.0.0.1:"+str(server.server_port)})
      response=c.getresponse();page=response.read(400001).decode("utf-8","replace")
      if (response.status!=200 or "github.com/git/git/pull/45984" not in page
          or 'data-public-snapshot-unsigned="true"' not in page
          or "독립 출처 확인 전 검토 보류" not in page
          or "개선 방향 살펴보기<span" in page):
       raise ValueError("installed unsigned public PR metadata page rejected")
    from urllib.parse import quote
    first=check["items"][0]["library_item_id"]
    with closing(HTTPConnection("127.0.0.1",server.server_port,timeout=6)) as c:
     c.request("GET","/local/review?q=Git&id="+quote(first,safe=""),
               headers={"Host":"127.0.0.1:"+str(server.server_port)})
     response=c.getresponse();response.read(4096)
     if response.status!=400:
      raise ValueError("unsigned imported PR accepted as verified owner review")
    (root/CAP_PIN).write_bytes(("f"*64+"\\n").encode("ascii"))
    with closing(HTTPConnection("127.0.0.1",server.server_port,timeout=6)) as c:
     c.request("GET","/local/library?q=Git",
               headers={"Host":"127.0.0.1:"+str(server.server_port)})
     response=c.getresponse();response.read(4096)
     if response.status!=400:
      raise ValueError("tampered unsigned PR metadata accepted")
   finally:
    server.shutdown();thread.join(timeout=5)
    if thread.is_alive():raise ValueError("public capsule server did not shut down")
  print(json.dumps({"status":"V04_LOCALHOST_HTTP_PASS","ui":result,
                    "installed_synthetic_public_PR_capsule_routes":len(imported_routes),
                    "installed_unsigned_PR_review_denied":True,
                    "installed_corrupt_public_capsule_denied":True,
                    "installed_offline_reference_routes_verified":len(routes),
                    "offline_reference_status":REF_STATUS,
                    "installed_no_public_pr_database":True,
                    "offline_PR_page2_rejected":True,
                    "vendor_distribution_absent":True,
                    "customer_release_authorized":False},sort_keys=True))
 except ModuleNotFoundError as err:
  print(json.dumps({"status":"IMPORT_BLOCKED","missing_module":err.name or "UNKNOWN",
                    "customer_release_authorized":False},sort_keys=True))
 except Exception as err:
  print(json.dumps({"status":"V04_OTHER_FAIL_CLOSED",
                    "failure_class":type(err).__name__[:70],
                    "customer_release_authorized":False},sort_keys=True))
"""


class InstalledUIError(ValueError):
    pass


def check_ci(root: Path, env: dict) -> Path:
    if (not isinstance(root, Path) or root.name != "UCIE"
            or root.is_symlink() or not (root / ".git").is_dir()
            or env.get("GITHUB_ACTIONS") != "true"
            or env.get("CI") != "true"
            or env.get("RUNNER_OS") != "Windows"
            or env.get("GITHUB_REPOSITORY") != "tmdrkdtn1-project/UCIE"
            or env.get("GITHUB_EVENT_NAME") not in ("pull_request", "push")
            or env.get("UCIE_C4_CLEAN_V04_ONLY") != "1"
            or sys.platform != "win32"
            or sys.version_info[:2] != (3, 15)):
        raise InstalledUIError("UCIE exact clean Windows GitHub CI required")
    scratch = Path(env.get("RUNNER_TEMP", ""))
    if (not scratch.is_dir() or scratch.is_symlink()
            or root.resolve().is_relative_to(scratch.resolve())
            or scratch.resolve().is_relative_to(root.resolve())):
        raise InstalledUIError("CI scratch/root boundary invalid")
    return scratch


def run(root: Path, env: dict) -> dict:
    tmp_parent = check_ci(root, env)
    safe_env = {k: env[k] for k in (
        "PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP",
        "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "COMSPEC",
    ) if k in env}
    safe_env.update(PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1",
                    PYTHONDONTWRITEBYTECODE="1")
    closure = runtime.inspect_static_runtime_closure(root)
    if closure.get("missing_first_party_imports"):
        raise InstalledUIError("exact source static first-party closure incomplete")
    payload = runtime._copy_payload(root, closure)
    with TemporaryDirectory(prefix="UCIE_C4_ONLY_NO_VENDOR_V04_", dir=tmp_parent) as work:
        scratch = Path(work)
        staging = scratch / "source" / "UCIE"
        staging.parent.mkdir()
        manifest = runtime._stage(staging, payload, runtime.REVISION_A)
        runtime._verify(staging, manifest)
        wheel_dir = scratch / "wheels"
        wheel_dir.mkdir()
        wheel = full._build_first_party_wheel(wheel_dir, payload)
        info = full._inspect_first_party_wheel(wheel, payload)
        if info.get("wheel_record_verified") is not True or info.get("source_code_bytes_match") is not True:
            raise InstalledUIError("current first-party package integrity failed")
        target = scratch / "only_recipient_venv"
        full._run([sys.executable, "-I", "-B", "-m", "venv", str(target)],
                  scratch, safe_env, "clean disposable Windows UI recipient")
        child = target / "Scripts" / "python.exe"
        if child.is_symlink() or not child.is_file():
            raise InstalledUIError("disposable recipient Python unavailable")
        full._run([
            str(child), "-I", "-B", "-m", "pip", "--isolated", "install",
            "--no-index", "--no-deps", "--only-binary=:all:",
            "--no-cache-dir", "--no-input", "--no-compile",
            "--disable-pip-version-check", "--timeout", "8", "--retries", "0",
            str(wheel)
        ], scratch, safe_env, "only current UCIE first-party offline install")
        four = full._check_four_pillars(full._run([
            str(child), "-I", "-B", "-m", "ucie_miner.customer_staging_v01",
            "--pillar", "all"
        ], scratch, safe_env, "four first-party synthetic workflows"))
        ui_result = json.loads(full._run([
            str(child), "-I", "-B", "-c", CHILD, str(staging)
        ], scratch, safe_env, "first-party installed Local V04 no-vendor probe"))
        if ui_result.get("status") != "V04_LOCALHOST_HTTP_PASS":
            missing = str(ui_result.get("missing_module", "UNKNOWN"))
            if not re.fullmatch(r"[A-Za-z0-9_.]{1,80}", missing):
                missing = "UNSAFE_NAME_REDACTED"
            raise InstalledUIError("UI_BLOCKER_" + str(ui_result.get("status"))[:40]
                                   + "_MISSING_" + missing)
        ui = full._check_ui(json.dumps(ui_result["ui"], sort_keys=True))
        if (ui_result.get("installed_synthetic_public_PR_capsule_routes") != 3
                or ui_result.get("installed_unsigned_PR_review_denied") is not True
                or ui_result.get("installed_corrupt_public_capsule_denied") is not True
                or ui_result.get("installed_offline_reference_routes_verified") != 8
                or ui_result.get("offline_reference_status")
                    != "OFFICIAL_DOCUMENT_REFERENCES_ONLY_NO_CAPTURED_PR_LEDGER_NO_GO"
                or ui_result.get("installed_no_public_pr_database") is not True
                or ui_result.get("offline_PR_page2_rejected") is not True
                or ui_result.get("vendor_distribution_absent") is not True
                or ui_result.get("customer_release_authorized") is not False
                or ui.get("installed_local_ui_loopback_routes_verified") != 5
                or four.get("first_party_four_pillars_synthetic_worked") is not True):
            raise InstalledUIError("UCIE clean UI or missing-vendor fail closed")
        outcome = {
            "schema": SCHEMA, "status": "C4_CLEAN_WINDOWS_INSTALLED_FOUR_PILLAR_LOCAL_V04_FIRST_PARTY_ONLY_PASS",
            "installed_first_party_wheel_sha256": info["sha256"],
            "installed_source_manifest_sha256": manifest["source_sha256"],
            "installed_python_module_count": info["file_count"],
            "installed_four_pillar_uci_synthetic": True,
            "installed_V04_real_127_0_0_1_GET_routes": 5,
            "installed_offline_official_reference_HTTP_GET_routes": 8,
            "installed_synthetic_public_PR_capsule_GET_routes": 3,
            "installed_unsigned_public_PR_review_denied": True,
            "installed_tampered_public_PR_capsule_denied": True,
            "installed_public_PR_captured_database_present": False,
            "installed_offline_PR_page2_denied": True,
            "installed_V04_real_POST_denied": True,
            "vendor_packages_included_or_executed": False,
            "native_vendor_ABI_attested": False,
            "external_packages_license_or_security_cleared": False,
            "customer_signing_or_rights_approved": False,
            "independent_owner_controlled_windows_PC_accepted": False,
            "complete_customer_installer_approved": False,
            "customer_distribution_authorized": False,
            "operations_on_owner_host_or_database": False,
        }
    return outcome


def main() -> int:
    try:
        result = run(REPO, dict(os.environ))
    except Exception as exc:
        label = str(exc) if isinstance(exc, InstalledUIError) else type(exc).__name__
        print(json.dumps({"schema": SCHEMA, "status": "C4_CLEAN_WINDOWS_INSTALLED_V04_NO_GO",
                          "safe_failure_label": label[:150], "customer_distribution_authorized":False}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
