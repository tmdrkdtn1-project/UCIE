"""UCIE-only owner MCP bridge host-readiness inventory; strictly read-only.

No bridge registration, credentials, connection changes, ACL changes, grants,
batch application, scheduler/process control, or non-UCIE file access.
A passing test means survey COMPLETE, never owner authority APPROVED.
"""
from __future__ import annotations

import ast
from hashlib import sha1, sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

UCIE_ROOT = Path(r"D:\UCIE")
OWNER_PROFILE = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")
LIVE_MCP_SERVER = Path(r"D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py")
HUB = Path(r"D:\UCIE_HUB")
OWNER_SCOPE_DIR = HUB / "04_MIGRATION" / "UCIE_OWNER_SCOPED_QA_V1"
EXPECTED_BLOBS = {
    "owner_scoped_batch_v1.py": "1272173b4378cd088ab07225499e6d805ff94bbc",
    "owner_scoped_bridge_v1.py": "ea4b9941dbb3ba4c3c4f7f354c694c146bf3a17d",
    "owner_scoped_mcp_tools_v1.py": "98eb8c70895a49fcd421b5e9886671e2efdc6f4d",
}
TOOLS = (
    "ucie_owner_scope_status",
    "ucie_owner_scope_enroll",
    "ucie_owner_scope_revoke",
    "ucie_owner_scope_apply",
)


def bounded_file_bytes(path: Path, max_size=250_000) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("UCIE pinned file missing, linked, or not regular")
    if path.stat().st_size > max_size:
        raise ValueError("UCIE pinned file too large")
    return path.read_bytes()


def git_blob_sha(data: bytes) -> str:
    return sha1(("blob " + str(len(data)) + "\x00").encode("ascii") + data).hexdigest()


def check_owner_acl() -> dict:
    """PowerShell reads only the explicit UCIE owner directory ACL, not others.

    Never prints usernames, SIDs, ACEs or filesystem contents. The directory
    may not yet exist, in which case no protection is claimed.
    """
    shell = shutil.which("powershell.exe")
    if not shell:
        return {"acl_observation": "NO_WINDOWS_POWERSHELL", "grant_dir_exists": False,
                "broad_write_allow": None, "owner_or_admin_acl_owner": None,
                "current_process_elevated": None}
    script = r'''
$ErrorActionPreference='Stop'
$path='D:\UCIE_HUB\04_MIGRATION\UCIE_OWNER_SCOPED_QA_V1'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($identity)
$elevated=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$exists=Test-Path -LiteralPath $path -PathType Container
$broad=$null
$ownerGood=$null
if($exists){
    $acl=Get-Acl -LiteralPath $path -ErrorAction Stop
    $ownerSid=$identity.User.Value
    $builtInAdmin='S-1-5-32-544'
    try{
        $aclOwner=([Security.Principal.NTAccount]::new([string]$acl.Owner)).Translate(
            [Security.Principal.SecurityIdentifier]).Value
    } catch {
        $aclOwner=if([string]$acl.Owner -match '^S-1-') {[string]$acl.Owner} else {''}
    }
    $ownerGood=($aclOwner -eq $ownerSid -or $aclOwner -eq $builtInAdmin)
    $broadSids=@('S-1-1-0','S-1-5-11','S-1-5-32-545','S-1-5-7')
    $mask=([Security.AccessControl.FileSystemRights]::Write -bor
        [Security.AccessControl.FileSystemRights]::Modify -bor
        [Security.AccessControl.FileSystemRights]::FullControl -bor
        [Security.AccessControl.FileSystemRights]::Delete -bor
        [Security.AccessControl.FileSystemRights]::ChangePermissions -bor
        [Security.AccessControl.FileSystemRights]::TakeOwnership)
    $broad=$false
    foreach($ace in @($acl.Access)){
        if([string]$ace.AccessControlType -ne 'Allow'){continue}
        $sid=''
        try{
            $sid=$ace.IdentityReference.Translate(
                [Security.Principal.SecurityIdentifier]).Value
        } catch { }
        if($sid -in $broadSids -and (([int]$ace.FileSystemRights -band [int]$mask) -ne 0)){
            $broad=$true
        }
    }
}
[pscustomobject]@{
 schema='UCIE_OWNER_SCOPE_ACL_READONLY_V1'
 grant_dir_exists=[bool]$exists
 current_process_elevated=[bool]$elevated
 owner_or_admin_acl_owner=$ownerGood
 broad_write_allow=$broad
 acl_observation='READ_ONLY'
} | ConvertTo-Json -Compress
'''
    result = subprocess.run(
        [shell, "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, errors="replace", timeout=30, check=False,
    )
    if result.returncode != 0:
        return {"acl_observation": "ACL_QUERY_UNAVAILABLE",
                "grant_dir_exists": OWNER_SCOPE_DIR.is_dir(),
                "broad_write_allow": None, "owner_or_admin_acl_owner": None,
                "current_process_elevated": None}
    try:
        observation = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise AssertionError("UCIE owner ACL query malformed")
    if observation.get("schema") != "UCIE_OWNER_SCOPE_ACL_READONLY_V1":
        raise AssertionError("UCIE owner ACL schema mismatch")
    return observation


class UCIEOwnerScopedLiveHostPreflight(unittest.TestCase):
    def test_no_mutation_in_preflight_contract(self):
        # Check only the fixed Windows ACL probe, not this test's own literals.
        script = next(part for part in check_owner_acl.__code__.co_consts
                      if isinstance(part, str) and "$ErrorActionPreference" in part)
        for forbidden in ("Set-Acl", "Register-ScheduledTask", "Stop-Process",
                          "Start-Process", "Unregister-ScheduledTask",
                          "UCIE_MCP_TUNNEL_ID=", "UCIE_ADMIN_TOOLS_ENABLED="):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)

    def test_python_blob_pin_implementation(self):
        self.assertEqual(git_blob_sha(b"hello\n"),
                         "ce013625030ba8dba906f756967f9e9ca394464a")
        self.assertNotEqual(sha256(b"hello\n").hexdigest(), git_blob_sha(b"hello\n"))

    def test_owner_host_live_server_is_an_observation_not_an_authorization(self):
        if os.name != "nt" or not OWNER_PROFILE.is_file():
            self.skipTest("Not exact UCIE owner Windows host")
        server_summary = {
            "server_at_pinned_ucie_path": LIVE_MCP_SERVER.is_file(),
            "server_ast_valid": False,
            "legacy_ucie_admin_registration_present": False,
            "four_owner_tools_present_in_running_server_source": False,
            "owner_registration_hook_source_present": False,
            "server_static_owner_marker_present": False,
        }
        if server_summary["server_at_pinned_ucie_path"]:
            raw = bounded_file_bytes(LIVE_MCP_SERVER)
            code = raw.decode("utf-8-sig", "strict")
            ast.parse(code, filename="UCIE_MCP_SERVER")
            server_summary.update({
                "server_ast_valid": True,
                "legacy_ucie_admin_registration_present":
                    "ucie_admin_capabilities" in code,
                "four_owner_tools_present_in_running_server_source":
                    all(tool in code for tool in TOOLS),
                "owner_registration_hook_source_present":
                    "register_ucie_owner_scope_tools" in code,
                "server_static_owner_marker_present":
                    "UCIE_MCP_OWNER_APPROVAL" in code,
            })
        local = {}
        for name, expected_git_blob in EXPECTED_BLOBS.items():
            path = UCIE_ROOT / "src" / "ucie_miner" / name
            try:
                local[name] = git_blob_sha(bounded_file_bytes(path)) == expected_git_blob
            except (OSError, ValueError):
                local[name] = False
        acl = check_owner_acl()
        root_ok = (UCIE_ROOT.is_dir() and not UCIE_ROOT.is_symlink()
                   and HUB.is_dir() and not HUB.is_symlink())
        # Deliberately not set true from environment variables, local Windows
        # principal, or a static marker. MCP-session authentication is separate.
        remote_session_owner_authenticated = False
        registered = server_summary["four_owner_tools_present_in_running_server_source"]
        grant_acl_ready = (acl["grant_dir_exists"] is True
                           and acl["broad_write_allow"] is False
                           and acl["owner_or_admin_acl_owner"] is True)
        # A host survey cannot independently vouch for remote transport auth.
        go = bool(registered and grant_acl_ready
                  and all(local.values()) and root_ok
                  and remote_session_owner_authenticated)
        report = {
            "schema": "UCIE_OWNER_SCOPED_HOST_READINESS_SURVEY_V1",
            "status": "READ_ONLY_SURVEY_NO_OWNER_MUTATION",
            "ucie_roots_present": root_ok,
            "source_blob_pins_match": local,
            "server": server_summary,
            "grant_storage": {
                "directory_exists": acl["grant_dir_exists"],
                "acl_observation": acl["acl_observation"],
                "no_broad_write_observed": (acl["broad_write_allow"] is False),
                "acl_owner_is_owner_or_admin": acl["owner_or_admin_acl_owner"],
                "owner_process_elevated": acl["current_process_elevated"],
            },
            "remote_mcp_owner_session_auth_verified": remote_session_owner_authenticated,
            "four_mutating_tools_host_approved": go,
            "other_projects_read": False,
            "credentials_output": False,
            "task_or_process_changed": False,
            "grant_or_operating_db_changed": False,
        }
        print("UCIE_OWNER_SCOPED_HOST_SURVEY=" + json.dumps(report, sort_keys=True))
        self.assertEqual(report["schema"], "UCIE_OWNER_SCOPED_HOST_READINESS_SURVEY_V1")
        self.assertTrue(server_summary["server_at_pinned_ucie_path"])
        self.assertTrue(server_summary["server_ast_valid"])
        self.assertTrue(server_summary["legacy_ucie_admin_registration_present"])
        self.assertFalse(go, "Survey cannot independently authorize remote MCP operation")


if __name__ == "__main__":
    unittest.main()
