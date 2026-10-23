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
