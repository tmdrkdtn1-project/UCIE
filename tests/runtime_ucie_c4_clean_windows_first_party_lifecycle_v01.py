"""C4 boundary: real in-place A->B->A FIRST-PARTY ONLY on a clean Windows CI VM.

The pinned sources come only from two immutable UCIE Git commits and every
source byte is verified. Two actual offline wheels install into ONE disposable
Windows venv, run all four existing first-party workflows and Local V04 loopback,
upgrade in-place, roll back in-place and uninstall. No vendor wheels are
downloaded, installed, executed, bundled or approved.

This cannot claim full customer installation, true C2/C3 rights/security/signing,
a customer-approved SkillBook, or a separately controlled recipient machine.
Never invoke on the owner's D:/UCIE host or enable production services.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

# This script lives inside the UCIE first-party CI checkout only.
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from ucie_miner import customer_pinned_git_source_v01 as pin
from ucie_miner import customer_full_product_offline_rehearsal_v01 as full
from ucie_miner import customer_functional_ab_lifecycle_v01 as ab
from ucie_miner import customer_runtime_closure_v01 as runtime

SCHEMA = "UCIE_C4_CLEAN_WINDOWS_FIRST_PARTY_INPLACE_QA_V01"
STATUS = "C4_CLEAN_WINDOWS_CI_FIRST_PARTY_INPLACE_PASS_FULL_CUSTOMER_NO_GO"
REQUIRED_REPOSITORY = "tmdrkdtn1-project/UCIE"
SAFE_ENV = (
    "PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP",
    "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "COMSPEC",
)
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class CleanRecipientError(ValueError):
    """Fail-closed CI scope, installation evidence or product-lifecycle drift."""


def validate_ci_scope(root: Path, env: dict[str, str], *,
                      platform: str, python: tuple[int, int]) -> Path:
    """Prevent an accidental owner/local/foreign/PR-source mutation."""
    if (not isinstance(root, Path) or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()
            or (root / ".git").is_symlink()
            or not (root / ".git").is_dir()
            or type(env) is not dict
            or env.get("GITHUB_ACTIONS") != "true"
            or env.get("CI") != "true"
            or env.get("RUNNER_OS") != "Windows"
            or env.get("GITHUB_REPOSITORY") != REQUIRED_REPOSITORY
            or env.get("GITHUB_EVENT_NAME") not in ("pull_request", "push")
            or env.get("UCIE_C4_FIRST_PARTY_CI_ONLY") != "1"
            or platform != "win32" or tuple(python) != (3, 15)
            or not Path(sys.executable).is_file()):
        raise CleanRecipientError("exact clean Windows GitHub CI-only context required")
    try:
        folder = Path(env["RUNNER_TEMP"])
        if (folder.is_symlink() or not folder.is_dir()
                or folder.resolve() == root.resolve()
                or folder.resolve().is_relative_to(root.resolve())
                or root.resolve().is_relative_to(folder.resolve())
                or root.resolve().drive.casefold() != folder.resolve().drive.casefold()):
            raise CleanRecipientError("safe disjoint Windows runner scratch required")
    except (KeyError, OSError, RuntimeError) as exc:
        raise CleanRecipientError("Windows runner scratch untrusted") from exc
    return folder


def _safe_environment(env: dict[str, str]) -> dict[str, str]:
    allowed = {key: env[key] for key in SAFE_ENV if key in env}
    # pip is isolated and offline, and installed Python always uses -I.
    allowed["PIP_NO_INDEX"] = "1"
    allowed["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    allowed["PYTHONDONTWRITEBYTECODE"] = "1"
    return allowed


def _verify_state(raw: str, version: str, recipient: Path) -> dict:
    try:
        state = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise CleanRecipientError("installed version probe malformed") from exc
    if (type(state) is not dict or state.get("version") != version
            or state.get("b_only_health_present") is not (version == "0.1.1")
            or state.get("isolated") is not True
            or state.get("bits") != 64
            or Path(str(state.get("prefix"))).resolve() != recipient.resolve()):
        raise CleanRecipientError("actual in-place installed version/feature drift")
    return {"installed_version": version,
            "B_only_module_present": version == "0.1.1",
            "recipient_venv_isolated": True}


def _installed_probe(child: Path, recipient: Path, cwd: Path, env: dict) -> dict:
    raw = full._run(
        [str(child), "-I", "-B", "-c", ab.VERSION_PROBE],
        cwd, env, "CI one-recipient in-place distribution version")
    parsed = json.loads(raw)
    return _verify_state(raw, parsed.get("version"), recipient)


def _offline_install_command(child: Path, wheel: Path, scratch: Path) -> list[str]:
    if (not isinstance(child, Path) or not isinstance(wheel, Path)
            or not isinstance(scratch, Path) or scratch.is_symlink()
            or wheel.is_symlink() or not wheel.is_file()
            or not wheel.resolve().is_relative_to(scratch.resolve())
            or wheel.name not in (
                "ucie_public_only_demo-0.1.0-py3-none-any.whl",
                "ucie_public_only_demo-0.1.1-py3-none-any.whl")
            or not child.resolve().is_relative_to(scratch.resolve())):
        raise CleanRecipientError("non UCIE disposable first-party wheel candidate")
    return [
        str(child), "-I", "-B", "-m", "pip", "--isolated", "install",
        "--no-index", "--no-deps", "--only-binary=:all:",
        "--no-cache-dir", "--no-input", "--no-compile",
        "--disable-pip-version-check", "--timeout", "8", "--retries", "0",
        str(wheel),
    ]


def _stage_and_build(root: Path, manifest: dict, scratch: Path) -> dict:
    prepared = {}
    for label in ("A", "B"):
        # All bytes are from reviewed Git objects, NEVER the owner's worktree.
        source = pin._git_clean_source(root, manifest, label)
        destination = scratch / ("candidate_" + label)
        destination.mkdir()
        stage = destination / "source" / "UCIE"
        stage.parent.mkdir()
        staged_receipt = runtime._stage(stage, source, runtime.REVISION_A)
        runtime._verify(stage, staged_receipt)
        out = destination / "wheel"
        out.mkdir()
        wheel = full._build_first_party_wheel(
            out, source, version=pin.VERSION[label])
        pin._canonical_first_party_wheel(wheel)
        digest = sha256(wheel.read_bytes()).hexdigest()
        expected = pin.CANONICAL_QA_SHA256[label]
        checked = full._inspect_first_party_wheel(
            wheel, source, version=pin.VERSION[label])
        if (digest != expected or checked["sha256"] != expected
                or checked["file_count"] != len(manifest[label]["python"])
                or checked["wheel_record_verified"] is not True
                or checked["source_code_bytes_match"] is not True):
            raise CleanRecipientError("Git pinned first-party source or QA wheel mismatch")
        prepared[label] = {
            "version": pin.VERSION[label],
            "wheel": wheel,
            "source": stage,
            "modules": checked["file_count"],
            "sha256": digest,
            "commit": pin.PINNED[label][0],
        }
    if (prepared["A"]["sha256"] == prepared["B"]["sha256"]
            or prepared["A"]["modules"] != 182
            or prepared["B"]["modules"] != 184):
        raise CleanRecipientError("reviewed A/B first-party changes not present")
    return prepared


def run_clean_windows_ci(root: Path, env: dict[str, str]) -> dict:
    runner_temp = validate_ci_scope(
        root, env, platform=sys.platform, python=sys.version_info[:2])
    doc, manifest = pin._load_manifest(root)
    if doc.get("third_party_wheels_included") is not False:
        raise CleanRecipientError("vendor or unreviewed source may not be executed")
    clean = _safe_environment(env)
    tempfile_path: Path | None = None
    evidence = {}
    with tempfile.TemporaryDirectory(
        prefix="UCIE_C4_FIRST_PARTY_ONLY_", dir=runner_temp
    ) as temp:
        scratch = Path(temp)
        tempfile_path = scratch
        slots = _stage_and_build(root, manifest, scratch)
        recipient = scratch / "clean_single_recipient"
        full._run([sys.executable, "-I", "-B", "-m", "venv", str(recipient)],
                  scratch, clean, "clean Windows CI disposable venv")
        child = recipient / "Scripts" / "python.exe"
        if child.is_symlink() or not child.is_file():
            raise CleanRecipientError("clean Windows CI recipient Python unavailable")
        # An intentionally corrupted copy must be rejected BEFORE pip sees it.
        corrupt_dir = scratch / "corrupt"
        corrupt_dir.mkdir()
        candidate = corrupt_dir / slots["B"]["wheel"].name
        shutil.copyfile(slots["B"]["wheel"], candidate)
        with candidate.open("ab") as handle:
            handle.write(b"UCIE_C4_KNOWN_BAD_CANDIDATE_NOT_FOR_EXECUTION\n")
        tamper_blocked = (sha256(candidate.read_bytes()).hexdigest()
                          != slots["B"]["sha256"])
        if not tamper_blocked:
            raise CleanRecipientError("tampered B wheel not rejected before execution")
        candidate.unlink()
        corrupt_dir.rmdir()

        # Exactly one actual installed recipient environment: A -> B -> A.
        observations = {}
        for label, phase in (("A", "A_install"),
                             ("B", "B_inplace_update"),
                             ("A", "A_inplace_rollback")):
            slot = slots[label]
            if sha256(slot["wheel"].read_bytes()).hexdigest() != slot["sha256"]:
                raise CleanRecipientError("wheel bytes changed before CI install")
            command = _offline_install_command(child, slot["wheel"], scratch)
            full._run(command, scratch, clean, phase + " no-index no-deps pip")
            state = _installed_probe(child, recipient, scratch, clean)
            if state["installed_version"] != slot["version"]:
                raise CleanRecipientError("install/update/rollback version not observed")
            # Reuse existing real installed-product smoke assertions, not a
            # fabricated four-pillar or browser receipt.
            try:
                smoke = ab._smoke(label, child, slot["source"], scratch, clean)
            except full.OfflineFullProductError as exc:
                if str(exc) != "A/B installed localhost UI failed closed":
                    raise
                # Capture only a fixed, bounded UCIE first-party route reason.
                # Never expose installed wheel contents or stderr paths.
                wrapper = (
                    "import json,sys\n"
                    "from pathlib import Path\n"
                    "from ucie_miner.customer_portable_preview_v01 "
                    "import probe_preview_root,PortablePreviewError\n"
                    "try:\n"
                    " print(json.dumps(probe_preview_root(Path(sys.argv[1]))))\n"
                    "except Exception as err:\n"
                    " reason=str(err)[:160] if isinstance(err,PortablePreviewError) "
                    "else type(err).__name__\n"
                    " print(json.dumps({'status':'C4_UI_FAIL_CLOSED',"
                    "'failure_class':type(err).__name__,'reason':reason}))\n"
                )
                output = full._run(
                    [str(child), "-I", "-B", "-c", wrapper, str(slot["source"])],
                    scratch, clean, "C4 UCIE-only bounded UI diagnostic")
                try:
                    diag = json.loads(output)
                except ValueError as error:
                    raise CleanRecipientError("C4_UI_DIAGNOSTIC_NOT_JSON") from error
                if diag.get("status") != "C4_UI_FAIL_CLOSED":
                    raise CleanRecipientError("C4_UI_RETRY_INCONSISTENT")
                reason = str(diag.get("reason", "UNKNOWN"))
                allowed_prefix = ("disposable UCIE", "exact ", "unauthorized",
                                  "invalid", "unmarked", "incomplete",
                                  "HTTP", "ModuleNotFoundError",
                                  "KeyError", "FileNotFoundError",
                                  "PermissionError", "RecursionError")
                if not reason.startswith(allowed_prefix):
                    reason = str(diag.get("failure_class", "UNKNOWN"))
                raise CleanRecipientError("C4_UI_PROBE: " + reason[:120]) from None
            observations[phase] = {
                "installed_version": state["installed_version"],
                "four_pillars_exercised": (
                    smoke["four_pillars"]["pillars_exercised"]),
                "local_v04_routes_checked": (
                    smoke["local_V04"]["installed_local_ui_loopback_routes_verified"]),
                "b_only_workflow_sha256": smoke["B_only_workflow_sha256"],
                "customer_distribution_authorized": False,
            }
        if observations["A_install"] != observations["A_inplace_rollback"]:
            raise CleanRecipientError("rollback changed A installed first-party behavior")
        # Genuine pip removal and installed module absence, not merely selector
        # simulation or a second clean slot.
        ab._uninstall(child, scratch, clean)
        check = json.loads(full._run(
            [str(child), "-I", "-B", "-c", ab.ABSENCE_PROBE],
            scratch, clean, "post-uninstall independent recipient state"))
        if check.get("installed") is not False or (
            check.get("ucie_module_still_present") is not False
        ):
            raise CleanRecipientError("first-party uninstall did not clear distribution")
        evidence = {
            "reviewed_git_commits": {label: v["commit"] for label, v in slots.items()},
            "first_party_wheel_sha256": {
                label: v["sha256"] for label, v in slots.items()},
            "module_count": {label: v["modules"] for label, v in slots.items()},
            "observations": observations,
            "tampered_B_rejected_before_install": tamper_blocked,
            "installed_in_one_real_venv_A_B_A": True,
            "real_pip_uninstall_confirmed": True,
        }
    if tempfile_path is None or tempfile_path.exists():
        raise CleanRecipientError("temporary CI recipient/QA wheels not removed")
    return {
        "schema": SCHEMA, "status": STATUS,
        "observed_environment": "EPHEMERAL_INDEPENDENT_GITHUB_WINDOWS_315_RUNNER_ONLY",
        "evidence": evidence,
        "verified_clean_windows_first_party_inplace_lifecycle": True,
        "vendor_dependency_wheels_included_or_executed": False,
        "no_index_no_deps_first_party_only": True,
        "four_pillars_using_ucie_synthetic_input_only": True,
        "private_customer_data_used": False,
        "signed_windows_installer_created": False,
        "independent_second_owner_controlled_recipient_accepted": False,
        "complete_c1_or_c4_full_customer_product_accepted": False,
        "c2_vendor_rights_security_approved": False,
        "c3_customer_signing_licensed": False,
        "c5_customer_pilot_approved": False,
        "customer_distribution_authorized": False,
        "operating_database_writes": 0,
        "owner_services_or_tasks_modified": False,
        "ci_ephemeral_files_removed": True,
    }


def main() -> int:
    try:
        result = run_clean_windows_ci(REPO, dict(os.environ))
    except Exception as exc:
        # Do not emit absolute paths, third-party bytes, secrets or raw traces.
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_C4_CLEAN_WINDOWS_FIRST_PARTY_INPLACE_FAIL_CLOSED",
            "failure_class": type(exc).__name__[:70],
            "safe_failure_stage": (str(exc)[:140]
                if isinstance(exc, (full.OfflineFullProductError, CleanRecipientError))
                else type(exc).__name__[:70]),
            "complete_c4_customer_product_accepted": False,
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
