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

## Registration in existing UCIE MCP server — owner-managed action

1. Bring this reviewed UCIE source into the existing MCP Python import path
   without accessing other local projects or resetting the current tunnel.
2. Locate the actual `FastMCP` application object in the existing
   UCIE-only `mcp_stdio_server.py`.
3. Register once, immediately after that object is initialized:

   ```python
   from ucie_admin.mcp_registration import register_ucie_local_admin_tools
   register_ucie_local_admin_tools(existing_fastmcp_instance)
   ```

   The variable `existing_fastmcp_instance` is a placeholder; use the actual
   UCIE server variable, and never make a new server to register the tools.
4. Give these elevated tools a separately authorized UCIE Admin permission
   or plugin context. **Do not silently turn a general readonly consumer
   into a host file editor.** If the existing ChatGPT plugin does not support
   this separation, plan a distinct UCIE Admin connection backed by the
   same trusted host infrastructure.
5. A separately approved controlled MCP server restart/refresh might be
   needed. Do not change the tunnel profile/ID. Verify one harmless
   `ucie_admin_capabilities` call, then an ordinary `ucie_admin_read_text`
   call before any actual write.

## Synthetic developer acceptance (no host write)

```powershell
Set-Location D:\UCIE
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p test_ucie_local_write_bridge.py -v
```

**Current status:** SOURCE_ONLY / NOT_INSTALLED / NO_CHATGPT_LOCAL_WRITE.
