# UCIE 2026-11-17 — exact, write-once code-only owner stage (PR #307)

Scope: UCIE **only**. Depends on PR #306's merged immutable Git-object manifest and preflight. This is not an operating repository move and not a Task/MCP/C40 switch.

## What's implemented

- The owner CLI targets ONLY D:\UCIE_PROJECT\UCIE on Windows. It is **preview by default**.
- The source must be a separately obtained and reviewed clean UCIE PR #307 (or its eventual merged-main commit) snapshot under an independent directory (for example C:\TEMP\UCIE_PR305_SOURCE), **whose 232 original source files match PR #305's pinned Git commit**. The PR #307 stage tool and PR #306 verifier are not present in the original PR #305 archive: do not claim that archive alone is executable. Never use the dirty D:\UCIE checkout. PR #306's full 232-file Git-blob and SHA-256 leases must pass first.
- D:\UCIE_PROJECT must already exist as a verified direct directory. The UCIE child must **not exist at all** (even empty is rejected). No junction, symlink, reparse ancestor or prior data is overwritten.
- --mode apply additionally requires --owner-approval APPROVE_UCIE_CODE_ONLY_STAGE_ONCE; there is no automatic owner action from ChatGPT or GitHub CI.
- Under that exact new child, only manifest-allowlisted first-party Python and four smoke/StagePreview scripts are written. Each source is re-hashed before copy, the new file is created exclusively, flushed, read back, and the complete 232-file destination is independently reverified before writing the final UCIE_CODE_ONLY_STAGE_VERIFIED_V01.json receipt.
- If interrupted, an incomplete new stage **remains on disk** for explicit owner inspection. The tool does not delete it or retry over it. Receipt absent means not accepted.

## Owner command examples — NOT EXECUTED IN THIS PR

The following is illustrative only after separately source-authenticated snapshot, parent ACL and exact D: stage preflight have been independently verified. The owner one-shot tool and companion verifier must come from reviewed UCIE first-party source.

    & 'C:\Users\user\AppData\Local\Python\pythoncore-3.15-64\python.exe' -I -B 'C:\TEMP\UCIE_PR305_SOURCE\scripts\ucie_owner_code_only_stage_once_v01.py' --snapshot 'C:\TEMP\UCIE_PR305_SOURCE' --manifest 'C:\TEMP\UCIE_PR305_SOURCE\docs\UCIE_PR305_CODE_ONLY_STAGE_MANIFEST_V01.json' --mode preview

After owner approval and only if preview is clean:

    & 'C:\Users\user\AppData\Local\Python\pythoncore-3.15-64\python.exe' -I -B 'C:\TEMP\UCIE_PR305_SOURCE\scripts\ucie_owner_code_only_stage_once_v01.py' --snapshot 'C:\TEMP\UCIE_PR305_SOURCE' --manifest 'C:\TEMP\UCIE_PR305_SOURCE\docs\UCIE_PR305_CODE_ONLY_STAGE_MANIFEST_V01.json' --mode apply --owner-approval APPROVE_UCIE_CODE_ONLY_STAGE_ONCE

The source snapshot may include extra development files, but only the 232 pinned code paths are ever copied. The tool never reads private owner Task arguments, live profiles, SQLite, secrets or another project's data.

A completed code-only staging receipt is NOT live-root cutover. Next isolated owner tests after stage, without -Install or -Setup:

    powershell.exe -NoProfile -NonInteractive -File 'D:\UCIE_PROJECT\UCIE\scripts\bootstrap_local.ps1' -StagePreview
    powershell.exe -NoProfile -NonInteractive -File 'D:\UCIE_PROJECT\UCIE\scripts\install_hourly_task.ps1' -StagePreview
    powershell.exe -NoProfile -NonInteractive -File 'D:\UCIE_PROJECT\UCIE\scripts\install_internal_minute_task.ps1' -StagePreview

Then run the separate PR #304 P3/P6 exact search smoke using the exact source SHA-256. All these checks remain read-only. There is no runtime .venv, .git, SQLite, owner bridge state, C40 profile or Task registration at the new root.

## CI acceptance

The new test_ucie_owner_code_only_stage_once_v01.py reconstructs the exact 232 PR #305 source files using the UCIE Git tree/blob objects into a disposable temporary folder. It then invokes the production byte verifier and a real write-once source copy into a different disposable folder, checks all 232 output blobs, verifies the final receipt, and rejects a repeated apply. Also tests preview no-writes, unauthorized apply, preexisting destination, nonexistent parent, source tamper, symlink parent and nonowner roots. This is real Git bytes, NOT an owner D: test.

Require exact-head Windows/Ubuntu x Python 3.13/3.15 4/4 independent CI success before merging.

## Remaining hold

- Actual D:\UCIE_PROJECT parent ACL and snapshot provenance must be verified by the owner.
- Existing 20 modified/210 untracked owner files remain at D:\UCIE; no local Git pull/reset/clean/gc/prune, no runtime file/database copy, no path rebind, no symlink trick and no Task/C40 restart.
- Four owner Task actions, live C40 PID/SID/profile, owner data backups and a separately reversible operational cutover remain independent gates.
- PublicMiner HTTP403, P11 job6 REVIEW_REQUIRED 5/5, customer V1 release and automatic rule promotion remain HOLD/NO-GO.

STATUS=UCIE_CODE_ONLY_STAGE_CI_DEVELOPMENT__REAL_OWNER_D_DRIVE_NOT_STAGED__LIVE_CUTOVER_NO_GO
