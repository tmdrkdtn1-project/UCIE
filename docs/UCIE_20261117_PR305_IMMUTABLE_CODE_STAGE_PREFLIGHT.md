# UCIE 2026-11-17 — PR305 immutable first-party code snapshot preflight (development only)

This is the successor to merged PR #305, **not** a Windows owner cutover. It makes a read-only file-by-file exact-byte verifier for a *separately obtained clean UCIE source snapshot*. It does NOT copy or move the owner's `D:\UCIE` checkout and does not write `D:\UCIE_PROJECT`.

## Immutable source lease

- Source Git commit: `96c6187430fc126214e93f57cfcd0b86331dc1a4`, PR #305 merged `main`.
- The manifest `docs/UCIE_PR305_CODE_ONLY_STAGE_MANIFEST_V01.json` enumerates exactly **232** UCIE first-party files (**2,934,205 bytes**) under `src/ucie_miner/*.py`, `src/ucie_public/*.py` plus precisely four Python/PowerShell smoke/preview entrypoints.
- Source identity is checked by Git blob SHA-1 calculated over `blob <byte count>\0<content>` and file byte count; results include SHA-256 for downstream source pinning. Git blob SHA-1 is not represented as a modern collision-resistant signature. Source commit SHA must come from a trusted separately authenticated GitHub checkout/archive, not from untrusted metadata alone.
- Manifest is pinned to the exact known commit by the script, and tree traversal, duplicates, unknown paths, file reparse and modified bytes fail closed.
- Verify first-party bytes from a clean **independent snapshot**, never the live `D:\UCIE` dirty tree. The snapshot directory must not be named `UCIE` to reduce the risk of mistakenly using the owner root.

## Verification command (no owner host mutation)

```powershell
& 'C:\Users\user\AppData\Local\Python\pythoncore-3.15-64\python.exe' -I -B scripts\ucie_owner_code_only_stage_preflight_v01.py --snapshot 'C:\TEMP\UCIE_PR305_SOURCE' --manifest docs\UCIE_PR305_CODE_ONLY_STAGE_MANIFEST_V01.json
```

Here `C:\TEMP\UCIE_PR305_SOURCE` is an example **separately acquired trusted extraction**. It is not created by the script. There is no `--apply`, `--copy`, `--delete`, task, C40 or MCP operation. Successful offline preflight is not authorization to stage or cut over. A manifest in the repository is public code metadata only; never put private DB, owner-modified files, bridge state, credentials, cache or operating archive in Git.

## Strict remaining gates

1. Obtain clean snapshot through an owner-reviewed, source-pinned channel; independently verify the source commit authenticity.
2. Run full manifest byte checks against that isolated snapshot, and deny all mismatches.
3. Owner PC preflight for exact `D:\UCIE_PROJECT` ACL/path and reparse-point constraints, original owner dirty tree backup, the four UCIE Task action bindings, one-client C40 SID/PID, tunnel profile and live database backup; preserve the old paths and running state.
4. Only after explicit separate owner approval, use a new reversible staging mechanism that writes **only into a verified empty new directory**. Do not use automatic rename/move, junctions/symlinks or `git pull/reset/clean/gc` on live `D:\UCIE`.
5. Execute PR #304 isolated P3/P6 exact-search smoke and PR #305 three Windows `-StagePreview` commands on the new code-only stage. Live Task/MCP cutover and rollback require a different plan with on-host evidence.

**HOLD unchanged:** P11 job6 REVIEW_REQUIRED 5/5, PublicMiner HTTP403, autonomous rule promotion OFF, C40 outage/logon recovery not fully accepted, customer product V1 NO-GO. No unrelated project paths or data accessed.

STATUS=UCIE_PR305_IMMUTABLE_CODE_ONLY_SOURCE_PREFLIGHT_DEVELOPMENT__OWNER_D_DRIVE_UNCHANGED__STAGING_NOT_APPLIED__CUTOVER_NO_GO
