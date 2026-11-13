"""UCIE one-file Python3.15 Windows offline bootstrap — PRIVATE technical QA only.

Standalone stdlib script, packaged from the SHA-pinned first-party wheel as
Start-UCIE-Private-Install.py. It requires independently received exact hashes
for the product and EACH approved third-party wheel and owner PUBLIC trust.
It installs only the three hash-verified native dependencies into a disposable
local verifier venv. Only then it imports the byte-pinned first-party wheel
directly from its ZIP via zipimport, verifies the signed recipient entitlement
and runs the reviewed four-wheel private slot installer. Neither key issuance
nor customer release approval is provided or inferred.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

STATUS = "UCIE_PRIVATE_BOOTSTRAP_TECHNICAL_INSTALL_ONLY_CUSTOMER_NO_GO"
PRODUCT = "ucie_public_only_demo"
DIST = "ucie-public-only-demo"
SUPPORTED_VERSIONS = ("0.1.0", "0.1.1")
VENDORS = (("cryptography", "50.0.2"),
           ("cffi", "2.1.1"), ("pycparser", "3.12"))
BUNDLE_NAME = "UCIE_PRIVATE_BUNDLE"
RECIPIENT_NAME = "UCIE_PRIVATE_RECIPIENT"
CONSENT = "UCIE_PRIVATE_OFFLINE_TECHNICAL_RECIPIENT_INSTALL_ONCE"
SHA = re.compile(r"[0-9a-f]{64}\Z")
KEY = re.compile(r"[0-9a-f]{32}\Z")
WHEEL_NAME = re.compile(r"[A-Za-z0-9_.+-]+\.whl\Z")


class BootstrapError(ValueError):
    """Unknown or unapproved binary source / recipient context."""


def _size_hash(path: Path) -> str:
    if (path.is_symlink() or not path.is_file()
            or not 200 <= path.stat().st_size <= 32_000_000):
        raise BootstrapError("untrusted or missing wheel")
    size=path.stat().st_size
    h=sha256()
    with path.open("rb") as reader:
        while True:
            chunk=reader.read(131072)
            if not chunk:
                break
            h.update(chunk)
    if path.stat().st_size!=size:
        raise BootstrapError("wheel changed during bootstrap")
    return h.hexdigest()


def _args(argv: list[str] | None) -> argparse.Namespace:
    p=argparse.ArgumentParser(description="UCIE offline private technical installer, NOT release permission")
    p.add_argument("--bundle",type=Path,required=True)
    p.add_argument("--recipient-root",type=Path,required=True)
    p.add_argument("--product-version",choices=SUPPORTED_VERSIONS,required=True)
    p.add_argument("--expected-product-sha256",required=True)
    for name,_ in VENDORS:
        p.add_argument("--expected-"+name+"-sha256",required=True)
    p.add_argument("--public-trust-pem",type=Path,required=True)
    p.add_argument("--expected-owner-key-id",required=True)
    p.add_argument("--recipient-token-sha256",required=True)
    p.add_argument("--rights-packet-sha256",required=True)
    p.add_argument("--min-serial",type=int,required=True)
    p.add_argument("--consent",required=True)
    return p.parse_args(argv)


def _preflight(args:argparse.Namespace) -> tuple[Path, dict[str,str]]:
    if (os.name!="nt" or sys.version_info[:2]!=(3,15)
            or args.consent!=CONSENT or type(args.min_serial) is not int
            or not 1<=args.min_serial<=2**31-1
            or KEY.fullmatch(args.expected_owner_key_id) is None
            or any(SHA.fullmatch(value) is None for value in (
                args.expected_product_sha256,args.recipient_token_sha256,
                args.rights_packet_sha256))
            or not args.bundle.is_absolute() or not args.recipient_root.is_absolute()
            or args.bundle.name!=BUNDLE_NAME
            or args.recipient_root.name!=RECIPIENT_NAME
            or args.recipient_root.resolve()==Path("D:/UCIE").resolve()
            or args.bundle.is_symlink() or not args.bundle.is_dir()
            or args.recipient_root.is_symlink()
            or (args.recipient_root/".git").exists()
            or (args.recipient_root/"runtime").exists()
            or not args.recipient_root.parent.is_dir()
            or args.recipient_root.parent.is_symlink()):
        raise BootstrapError("approved isolated Windows3.15 install context required")
    wheel_dir=args.bundle/"wheels"
    if wheel_dir.is_symlink() or not wheel_dir.is_dir():
        raise BootstrapError("wheelhouse missing or linked")
    filenames=list(wheel_dir.iterdir())
    if len(filenames)!=4:
        raise BootstrapError("exactly four fixed wheelhouse files required")
    product=PRODUCT+"-"+args.product_version+"-py3-none-any.whl"
    hashes={DIST:args.expected_product_sha256}
    expected_names={product}
    if _size_hash(wheel_dir/product)!=args.expected_product_sha256:
        raise BootstrapError("first-party product not independently SHA pinned")
    for name,version in VENDORS:
        digest=getattr(args,"expected_"+name+"_sha256")
        if type(digest) is not str or SHA.fullmatch(digest) is None:
            raise BootstrapError("vendor SHA pin missing")
        names=[f for f in filenames
               if f.name.startswith(name+"-"+version+"-")
               and f.name.endswith(".whl")
               and WHEEL_NAME.fullmatch(f.name) is not None]
        if len(names)!=1 or _size_hash(names[0])!=digest:
            raise BootstrapError("vendor wheel not independently SHA pinned")
        hashes[name]=digest
        expected_names.add(names[0].name)
    if (set(f.name for f in filenames)!=expected_names
            or any(f.is_symlink() for f in filenames)):
        raise BootstrapError("extra/unapproved offline wheel found")
    pub=args.public_trust_pem
    if (pub.is_symlink() or not pub.is_file() or
            not 0<pub.stat().st_size<=2000):
        raise BootstrapError("owner PUBLIC trust PEM missing")
    return wheel_dir,hashes


def _run(argv:list[str],cwd:Path,env:dict[str,str],label:str) -> str:
    child=subprocess.run(
        argv,cwd=cwd,env=env,capture_output=True,text=True,
        encoding="utf-8",errors="replace",timeout=300,check=False)
    if child.returncode!=0 or len(child.stdout)>18000:
        raise BootstrapError(label+" failed closed")
    return child.stdout.strip()


# Runs in the verified ephemeral cryptography-native verifier venv. It
# imports first-party PURE Python bytes from the ZIP wheel BEFORE installing
# any customer first-party package, after checking its independently supplied
# SHA256 in the trusted stdlib bootstrap.
VERIFY_AND_STAGE = r"""
import sys
from pathlib import Path
product=Path(sys.argv[1])
sys.path.insert(0,str(product))
from ucie_miner.customer_private_offline_lifecycle_v01 import main
argv=[
 "--action","stage","--bundle",sys.argv[2],
 "--recipient-root",sys.argv[3],"--python",sys.executable,
 "--public-trust-pem",sys.argv[4],
 "--expected-owner-key-id",sys.argv[5],
 "--recipient-token-sha256",sys.argv[6],
 "--rights-packet-sha256",sys.argv[7],
 "--min-serial",sys.argv[8],"--consent",sys.argv[9],
]
raise SystemExit(main(argv))
"""


def install_once(argv:list[str]|None=None) -> dict:
    args=_args(argv)
    wheels,hashes=_preflight(args) # NO writes or code until all 4 SHA match.
    env={key:os.environ[key] for key in (
        "PATH","SystemRoot","SYSTEMROOT","WINDIR","TEMP","TMP",
        "HOME","USERPROFILE","HOMEDRIVE","HOMEPATH","COMSPEC")
        if key in os.environ}
    env.update(PIP_NO_INDEX="1",PYTHONDONTWRITEBYTECODE="1",
               PIP_DISABLE_PIP_VERSION_CHECK="1",PYTHONNOUSERSITE="1")
    with TemporaryDirectory(
            prefix="UCIE_PRIVATE_AUTHENTICATED_BOOTSTRAP_",
            dir=args.recipient_root.parent) as tmp:
        stage=Path(tmp)
        venv=stage/"verifier"
        _run([sys.executable,"-I","-B","-m","venv",str(venv)],
             stage,env,"disposable Windows verifier setup")
        child=venv/"Scripts"/"python.exe"
        if child.is_symlink() or not child.is_file():
            raise BootstrapError("disposable verifier interpreter unavailable")
        req=stage/"vendor_only_hash_locked.txt"
        req.write_text("\n".join(name+"=="+version+" --hash=sha256:"+
                        hashes[name] for name,version in VENDORS)+"\n",
                       encoding="ascii")
        _run([
            str(child),"-I","-B","-m","pip","--isolated","install",
            "--no-index","--find-links",str(wheels),
            "--require-hashes","--only-binary=:all:",
            "--no-cache-dir","--no-input","--no-compile",
            "--disable-pip-version-check","--timeout","10","--retries","0",
            "-r",str(req)],
            stage,env,"offline hash-locked native verifier install")
        _run([str(child),"-I","-B","-m","pip","--isolated","check",
              "--disable-pip-version-check"],
             stage,env,"offline native verifier dependencies")
        product=wheels/(PRODUCT+"-"+args.product_version+"-py3-none-any.whl")
        payload=_run([
            str(child),"-I","-B","-c",VERIFY_AND_STAGE,
            str(product),str(args.bundle),str(args.recipient_root),
            str(args.public_trust_pem),args.expected_owner_key_id,
            args.recipient_token_sha256,args.rights_packet_sha256,
            str(args.min_serial),args.consent],
            stage,env,"genuine signed four-wheel recipient install")
        try:
            receipt=json.loads(payload.splitlines()[-1])
        except (ValueError,IndexError,KeyError,TypeError) as exc:
            raise BootstrapError("installed full recipient receipt missing") from exc
        if (receipt.get("status")!="PRIVATE_TECHNICAL_INSTALL_SELECTED_NO_GO"
                or receipt.get("real_offline_pip_installed") is not True
                or receipt.get("customer_distribution_authorized") is not False):
            raise BootstrapError("offline release technical receipt drift")
    return {
        "status":STATUS,"schema":"UCIE_B3_B4_STANDALONE_WINDOWS_BOOTSTRAP_V01",
        "installed_active_slot":receipt["active_slot"],
        "source_product_version":args.product_version,
        "verified_all_four_external_SHA_pins_before_any_import":True,
        "installed_disposable_bootstrap_native_provider_removed":True,
        "owner_private_key_used_or_generated":False,
        "customer_distribution_authorized":False,
    }


def main(argv:list[str]|None=None) -> int:
    try:
        result=install_once(argv)
        print(json.dumps(result,sort_keys=True),flush=True)
        return 0
    except (ValueError,TypeError,OSError,subprocess.TimeoutExpired):
        print(json.dumps({
            "schema":"UCIE_B3_B4_STANDALONE_WINDOWS_BOOTSTRAP_V01",
            "status":"PRIVATE_BOOTSTRAP_FAIL_CLOSED_CUSTOMER_NO_GO",
            "customer_distribution_authorized":False,
        },sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
