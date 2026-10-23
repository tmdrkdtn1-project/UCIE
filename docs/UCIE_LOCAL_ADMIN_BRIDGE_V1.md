# UCIE Local Admin Bridge — source implementation

This is a UCIE-only local developer bridge. Committing source to GitHub
**does not** install or register new ChatGPT MCP tools.

## Available operations (9 tools)

| MCP tool | Supported action |
|---|---|
| ucie_admin_capabilities | Show local UCIE-only scope and limits |
| ucie_admin_list_files | List bounded UCIE source directories |
| ucie_admin_read_text | Read bounded UTF-8 source with SHA-256 |
| ucie_admin_search_text | Search fixed literal within bounded UCIE source |
| ucie_admin_create_directory | Make one UCIE directory |
| ucie_admin_write_text | Preview/create/update UTF-8 file, SHA lease, backup |
| ucie_admin_replace_text | Replace exactly one text occurrence with SHA lease |
| ucie_admin_git_status | Read UCIE Git working-tree status |
| ucie_admin_test_one_file | Run one UCIE unittest file with explicit approval |

Write/edit default is `preview=True`, never implicit. Existing file mutation
requires the SHA-256 returned by `ucie_admin_read_text`. For a new file the
expected SHA is `ABSENT`. Previous file content goes to a separately named
local backup in `D:\UCIE\.ucie_bridge_state` and only operation metadata goes
to the audit journal.

## Exact filesystem scopes

- `repo` -> `D:\UCIE`: UTF-8 UCIE source/docs/test/config files.
- `mcp_code` -> `D:\UCIE_DATA\library_app\private_lib`: UCIE MCP Python
  implementation, limited to Python/text docs.

Path traversal, junction/symlink traversal, credentials/secret-named files,
binary databases, Git internal objects and unrelated projects are forbidden.
Limits: <=200 KB per read, <=256 KB per write, bounded listing and searching.
There is no unrestricted shell, git push, file deletion, task registration,
scheduler change, tunnel setup or automatic service restart.

Even when security hardening is deferred, **root scoping, symlink checks,
expected hashes and backups stay mandatory**. Writing Python/PowerShell
source can indirectly execute code upon a later restart, so tools must only
be registered on an authorized UCIE owner-specific MCP connection.

## Registration in existing UCIE MCP server — single-use handoff

The UCIE owner observed the following via read-only AST inspection:

- `mcp_stdio_server.py` has exactly one `search_ucie_evidence` handler.
- The handler uses `@server.tool`.
- `make_server` starts on line 24 and creates local `server` at line 30.
- Existing UCIE Library PR #77 handler file was backed up and patched;
  SHA-256 after that patch:
  `1a9ce892cbbf17d11078082150cea2b286528ef113935a28b254b511cd1b5304`.
- No MCP process restart or tunnel ID change was observed.

Use the dedicated **one-time AST patcher**
`scripts/prepare_ucie_admin_mcp_registration.py`. It inserts **one gated
registration** immediately after the local `server` assignment inside
`make_server`, before the existing `@server.tool` decorators. It preserves
the PR #77 Library source patch, all existing read-only tools and original
`server` identity.

### Stage PR #78 without touching operating D:\UCIE checkout

```powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\UCIE'
$preview = 'D:\UCIE_PREVIEW\UCIE_ADMIN'

if (Test-Path $preview) {
    throw 'UCIE Admin staging folder already exists; inspect it first'
}

git -C $repo fetch --no-tags origin pull/78/head
if ($LASTEXITCODE -ne 0) { throw 'UCIE Admin fetch failed' }

git -C $repo worktree add --detach $preview FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'UCIE Admin worktree creation failed' }

$env:UCIE_ADMIN_SOURCE_DIR = "$preview\src"
& 'D:\UCIE\.venv\Scripts\python.exe' -B "$preview\scripts\prepare_ucie_admin_mcp_registration.py"
if ($LASTEXITCODE -ne 0) { throw 'UCIE Admin static preflight failed' }
```

The expected output begins
`READY_FOR_UCIE_ADMIN_REGISTRATION`, and shows the real source SHA before
and after. This does not modify the MCP server.

After the owner explicitly approves modifying that **one UCIE-only server
file**, a separate optional command applies the patch and retains another
hash-named backup:

```powershell
$env:UCIE_ADMIN_SOURCE_DIR = 'D:\UCIE_PREVIEW\UCIE_ADMIN\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B 'D:\UCIE_PREVIEW\UCIE_ADMIN\scripts\prepare_ucie_admin_mcp_registration.py' --apply --approval APPROVE_UCIE_ADMIN_MCP_HANDLER_REGISTRATION_ONCE
```

Output `UCIE_ADMIN_REGISTRATION_FILE_PATCHED_GATED` means **source only**
was changed. The 9 admin tools are deliberately OFF by default: the
authorized process environment must explicitly set
`UCIE_ADMIN_TOOLS_ENABLED=1` before the *next authorized server launch*.
Never set it on a broadly shared/anonymous MCP endpoint; use a separate
owner-only admin context when necessary.

The patcher does NOT restart UCIE, alter Cloudflare tunnel configuration,
register any ChatGPT plugin, change Windows scheduled tasks, or grant any
outside-project access. Do not claim the local ChatGPT tools are live until
an authorized server refresh, ChatGPT tool discovery and one
`ucie_admin_capabilities` read-only call actually succeed.

**Known blocker:** the actual server process launch/refresh owner remains
unobserved; `UCIE_MCP_PROCESS=NOT_FOUND_BY_COMMANDLINE` was only an
unsuccessful process-name/command-line filter, not evidence of downtime.
Do not blindly terminate processes or restart the tunnel.

## Synthetic developer acceptance (no host write)

```powershell
Set-Location D:\UCIE
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p test_ucie_local_write_bridge.py -v
```

**Current status:** SOURCE_ONLY / NOT_INSTALLED / NO_CHATGPT_LOCAL_WRITE.


## 2026-10-23: Source patch completed, ChatGPT still shows one tool

The owner reported the two source patches were actually applied with
hash-named backups. The **current UCIE MCP server source SHA256** is
`83b58b68ad0c15a32991e03e82b3c309a5e045da1d4c9a4c8ca3101d8b010d8e`.
Previous READONLY query tool name: `search_ucie_evidence`.
ChatGPT currently discovers just **one read-only UCIE tool**, not the nine
UCIE admin tools. The admin environment flag is not proven active in the
actual running UCIE MCP server. Previous ad hoc import tests did NOT establish
a local 9/9 PASS and should not be repeated.

### One fixed UCIE-only activation checkpoint

To inspect the existing tunnel/profile and local source registration in one
bounded, redacted, **read-only** pass:

```powershell
$ErrorActionPreference = 'Stop'
$preview = 'D:\UCIE_PREVIEW\UCIE_ADMIN'
if (-not (Test-Path "$preview\.git")) {
    # Git worktrees commonly use a .git FILE, not a directory.
    if (-not (Test-Path "$preview\scripts\prepare_ucie_admin_mcp_registration.py")) {
        throw 'Existing UCIE Admin worktree is unavailable'
    }
}
$changes = @(git -C $preview status --porcelain)
if ($LASTEXITCODE -ne 0 -or $changes.Count -ne 0) {
    throw 'UCIE Admin worktree has uncommitted changes; stop before updating'
}
git -C $preview fetch --no-tags origin pull/78/head
if ($LASTEXITCODE -ne 0) { throw 'PR78 fetch failed' }
git -C $preview switch --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'PR78 checkout failed' }
& "$preview\scripts\inspect_ucie_mcp_activation.ps1"
```

This checkpoint checks the exact expected UCIE MCP SHA, the known UCIE
tunnel profile without printing its contents, **UCIE-named** tasks and
process command lines without printing arguments, and attempts a one-process
read-only local tool-name discovery under a *temporary* admin environment
flag. The environment change is restored in `finally`. No operation restarts
the real tunnel, rewrites a profile, modifies the server, or calls write tools.

The result distinguishes `LOCAL_MCP_TOOL_REGISTRATION_OBSERVED` from
`CHATGPT_ADMIN_TOOLS_NOT_YET_DISCOVERED`. It deliberately reports neither
as a live operational PASS.

### Activation path — no new tunnel

1. **Confirm app audience is owner-only.** The fixed registration flag exposes
   nine write tools to **any** client authorized for that same UCIE MCP server.
   If the existing READONLY plugin is shared to a Business workspace, do not
   enable the admin flag on that shared endpoint. Owner-only admin access
   must be separated first; do not claim plugin-level confirmation prompts
   alone provide a server authorization boundary.
2. Identify the UCIE-only task/service or interactive terminal launching
   `tunnel-client run --profile ...` and its exact UCIE-only stdio command.
   Secure MCP Tunnel `tunnel-client` remains the existing transport; do not
   alter its ID or create additional tunnels.
3. On **the authorized owner-only UCIE server launcher**, arrange the
   process environment `UCIE_ADMIN_TOOLS_ENABLED=1` before the MCP process
   launches. A variable set in an unrelated PowerShell window is NOT
   inherited by the running tunnel client. Perform **one controlled UCIE-only
   refresh** using the actual verified launcher. Do not kill unknown PIDs or
   restart scheduled public-miner jobs.
4. Business workspace owners/admins can **refresh the existing custom MCP app
   tool list from workspace app settings**, retaining the existing app
   identity. In the legacy Apps UI, after workspace selection open
   `Workspace settings > Apps`, the existing UCIE app's `Action control`,
   then `Refresh` and review the new tool definitions (UI wording can vary).
   No plugin or tunnel deletion is required.
5. Only after ChatGPT actually shows `ucie_admin_capabilities` and a harmless
   invocation succeeds, report admin tool connection LIVE. If the existing
   plugin was shared or a plugin-scoped owner-only connection cannot be
   established, leave the gate OFF and record the blocking condition; do not
   expand the general read-only plugin's privileges.

Official references:
- https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
  (the pre-approved tool list is a frozen snapshot until admin refresh)
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
  (the running tunnel-client forwards to the configured local stdio
  command; tunnel role and ChatGPT app access are separate)

**Status:** host file patched; local registration and true runtime launch
pending observation; ChatGPT still displays only the legacy tool.


### Observed permission denial before server initialization

On 2026-10-23 the owner ran the consolidated UCIE-only local
checkpoint at PR #78 SHA e26ba54 and supplied:

- expected server SHA matched
- one UCIE tunnel ID was present in the expected UCIE-only profile
- profile mentions both the existing stdio server and Python runtime
- no UCIE matching process or UCIE tunnel scheduled task was found by
  the bounded filters (not proof that a tunnel never runs)
- calling make_server from an *untrusted ad hoc Python import* failed
  with PermissionError at mcp_stdio_server.py line 21, called from
  make_server line 25, before the local server assignment at line 30.

This is a meaningful **startup authorization gate**, not evidence of a
broken MCP decorator or of the 9 admin tool declarations being absent.
Do not patch away or fake this gate. An MCP launched from an authenticated
runtime may satisfy the original guard and work normally; that has not
been observed yet.

The next observation must be **static**, not another unapproved direct
import or test invocation of make_server. A fixed script
`scripts/inspect_ucie_mcp_permission_gate.py` was added: it reads only
the exact UCIE MCP source with owner-reported SHA, parses its AST, and
reports the guard function name, initial call order, UCIE-prefixed
environment *names* plus boolean presence, and symbolic error codes
where safe. It does not execute server code or print variable values,
tokens, raw source, process commands, or other projects.

Use the already-created detached PR #78 UCIE_ADMIN worktree (no new
worktree, no service modification):

```powershell
$ErrorActionPreference = 'Stop'
$preview = 'D:\UCIE_PREVIEW\UCIE_ADMIN'
if ((git -C $preview status --porcelain)) {
    throw 'UCIE Admin preview has uncommitted changes; stop'
}
git -C $preview fetch --no-tags origin pull/78/head
if ($LASTEXITCODE -ne 0) { throw 'UCIE PR fetch failed' }
git -C $preview switch --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'UCIE worktree update failed' }
& 'D:\UCIE\.venv\Scripts\python.exe' -B "$preview\scripts\inspect_ucie_mcp_permission_gate.py"
if ($LASTEXITCODE -ne 0) { throw 'UCIE permission-gate static inspection incomplete' }
```

After the true UCIE guard is understood, preserve it and use the
**documented existing owner-authorized tunnel-client profile** for
server launch. Never blindly set arbitrary environmental permissions,
run the server in an untrusted context, start a second client, or
grant the already-shared readonly consumer write access by accident.

**Current evidence state:** HOST_SOURCE_PATCHED, MCP_RUNTIME_PERMISSION_GATE,
LOCAL_ADMIN_9_NOT_OBSERVED, CHATGPT_ADMIN_0_OF_9, NO_LIVE_PASS.

### 2026-10-23: Conditional operator HOLD — indirect environment getter

Owner supplied a read-only, static UCIE host observation of
`require_runtime_approval()`, which `make_server()` invokes **before**
constructing its real `MCPServer` object. The guard body contains an assignment
and conditional `If`, raises `PermissionError("UCIE_MCP_OPERATOR_GATE_HOLD")`
on the failed branch, and calls `e.get`. The guard is **NOT** an unconditional
HOLD. Existing static probe initially reported no directly referenced UCIE
environment keys because it did not resolve indirect mapping aliases.

To avoid blind changes or repeated runtime failures, the single static
diagnostic `scripts/inspect_ucie_mcp_permission_gate.py` now recognizes
local aliases of `os.environ` or its copy (for example `e = os.environ`,
`e.get("UCIE_...")`). It reports **only** safe UCIE-prefixed key names with
presence booleans, alias names, comparison operator types and a censored
fixed-literal hint. It never prints approval values, environment values,
credentials or source code, and does not execute the server.

Use the existing detached UCIE_ADMIN worktree and re-run this **one static
diagnostic** after fetching the current PR #78 head. On a discovered
`operator_gate_ucie_variable_presence_only` mapping, the next operational
step must honor the owner's approved launch procedure, not fake or disable
the original gate. If no alias/key is identified, report the unknown gate
source rather than guessing variables. Do not activate admin privileges on
a shared read-only plugin.

**Known state:** PR #77 Library patch and PR #78 gated admin registration
are installed in the UCIE MCP source (the previously owner-observed hash
matches); host launcher and approved execution context still unverified.
Current ChatGPT UCIE tools: one read-only search, admin tools 0/9.


## Final activation design: UCIE operator approval + exact C40 tunnel identity

The most recent owner-supplied static result **positively identifies both**
`UCIE_MCP_OWNER_APPROVAL` and `UCIE_MCP_TUNNEL_ID` as literal lookups
inside the original `require_runtime_approval()` guard. Its local mapping
`e` uses an `IfExp` which conditionally references `os.environ`.
The prior empty direct-environment probe was a static-analysis limitation,
not evidence that no environment prerequisites exist. Actual expected
operator approval content is **not** collected or published.

**Stop extending AST diagnostics.** Use
`scripts/ucie_owner_admin_mcp_launch.ps1` as the single operator gate
and local admin-tool discovery acceptance. It:
1. verifies the exact previously owner-observed MCP source SHA, UCIE-only
   stdio C40 profile and exactly one tunnel ID without printing secrets;
2. asks the owner for their already-approved UCIE operator approval using
   a masked PowerShell secure input, never reading source approval literals;
3. supplies the original two guard inputs and admin-enabled flag as
   **process-scoped environment only**, including PR77 and PR78 imports;
4. invokes original `make_server()` without modifying the guard and
   checks for **9 actual local admin tool names** and the original read-only
   search tool; never calls a file-writing admin tool;
5. in explicit owner-attested Launch mode ONLY, uses an installed
   `tunnel-client run --profile D:\\UCIE_DATA\\mcp_tunnel_profiles\\ucie-private-c40.yaml`
   client and the already-existing tunnel. No extra tunnel, new service,
   task, profile editing, plugin creation or source patch occurs.

**Prerequisites and safety:**
- The operator MUST possess the original approved
  `UCIE_MCP_OWNER_APPROVAL` value. Do not manufacture a new approval
  phrase or extract an embedded expected value into a token.
- Before enabling write-capable tools, the operator MUST verify the
  ChatGPT UCIE tunnel/app audience is owner-only. The switch
  `-OwnerOnlyConfirmed` means the owner has verified that; it is NOT a
  technical server-authentication mechanism. A shared readonly app using
  the same tunnel must NOT receive those admin tools.
- A successful `Probe` is **local process registration only**, not proof
  of an active tunnel or a ChatGPT tool snapshot refresh. Successful
  `Launch` also does NOT by itself prove ChatGPT has discovered/approved
  the new admin tools.
- The `Launch` script runs the client in the operator's foreground
  PowerShell session; stopping that process stops the tunnel client.
  There is no permanent service or task installation.
- This script cannot establish whether *another* non-C40 or protected
  process already serves the tunnel; do not attempt a second instance
  if platform/tunnel runtime status indicates the tunnel is active.

**Single local gate-preserving acceptance:**

```powershell
$ErrorActionPreference = 'Stop'
$preview = 'D:\\UCIE_PREVIEW\\UCIE_ADMIN'
if (@(git -C $preview status --porcelain).Count -ne 0) {
    throw 'UCIE_ADMIN worktree dirty; do not overwrite'
}
git -C $preview fetch --no-tags origin pull/78/head
if ($LASTEXITCODE -ne 0) { throw 'UCIE fetch failed' }
git -C $preview switch --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'UCIE checkout failed' }
& "$preview\\scripts\\ucie_owner_admin_mcp_launch.ps1" -Mode Probe
```

The owner enters the existing operator approval **locally**, not in ChatGPT.
On `UCIE_OWNER_LOCAL_ADMIN_9_REGISTERED`, evaluate owner-only connection
access. Then Launch separately with explicit attestation:

```powershell
& 'D:\\UCIE_PREVIEW\\UCIE_ADMIN\\scripts\\ucie_owner_admin_mcp_launch.ps1' -Mode Launch -OwnerOnlyConfirmed
```

After the existing tunnel is healthy, refresh tools on the existing
custom MCP app in ChatGPT workspace app settings, review each newly
discovered write-capable action and confirm `ucie_admin_capabilities`
is usable. Never claim live 9/9 PASS without that final tool discovery.

Official references:
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt

**Current operator status:** gate key names verified; runtime approval value,
owner-only audience, local nine-tool PASS, tunnel uptime, and ChatGPT action
snapshot are pending actual owner-side evidence.
