# UCIE W30 — separately journaled secondary recovery after FAILED W29 restoration

Date: 2026-11-19. This implementation is **source-only + synthetic CI**. No owner Windows W29 rehearsal has been run; therefore its failure-recovery prerequisites **do not exist on the currently healthy owner PC**. Do NOT invoke any W29 or W30 mutation mode, and do not create fake private receipts to make the W30 gate pass.

## Real owner evidence in chronological order

- W24 pre-rebind emergency restoration receipt: original D:\UCIE LocalV1 HTTP and two original collector schedules restored; historical W22/W24/W21 owner intents and all emergency recovery records remain private, immutable, one-shot.
- W26 actual owner Windows pinned W19 pure Same function compared three actual old Scheduled Task Actions/owners: PASS (PublicMiner Ready, InternalMinute Ready, LocalV1 Running). It did not test disabled-state W19 stage; prior W21 child exception masked.
- W27 actual owner Windows source SQLite metadata: ten exact historical names, direct non-reparse paths, bounded sizes, total observed 5,656,576 bytes. Writers not paused; no SQLite content/lock/quickcheck/fresh global snapshot.
- W29 PR #326 merged main ddcbb9ebc02b6908ab5f7a558f81b01a1e09d831, source-only old-root stop-and-immediate-restore rehearsal core. CI 4/4 mock/native tests PASS, but **no owner host service stop, rehearsal, or W29 recovery execution**. If real W29 restore fails after writing its recovery intent, W29 cannot be blindly retried.

## W30 design: recover only the actual failed W29 one-shot

New file: scripts/ucie_owner_w30_secondary_oldroot_restore_v01.ps1.

Four modes:
- Default no-host contract: UCIE_W30_CONTRACT_ONLY_NO_HOST_ACCESS; no host files, TaskScheduler, C40, port, SQLite or journal touched.
- Future -InspectReadOnly: exact same Windows owner with UAC elevation and separate READONLY approval. Requires **both** valid W29 original rehearsal and recovery intents, with original W29 restored receipt ABSENT, matching same owner SID and original C40 action hash. Refuses any W19/W13/W20/W28 stage output, foreign listener, modified original old task actions or unsupported state. Provides a no-write candidate classification only.
- Future -RecoverPartial: separately authorized second-chance old-root restoration, requires valid prior failed W29 lineage; W30 records absent. Writes NEW W30 protected recovery intent BEFORE any original task mutation; restores old LocalV1 (when needed) and verifies exact one-loopback/old HTTP health, then enables only original two writer schedules, never force-starts writers. Verifies C40, task states, no newroot stage; only then writes W30 restored receipt.
- Future -ResumePartial: if W30 first attempt failed after its own intent and no W30 restored receipt exists, separately approved ONE bounded retry. Requires W30 first intent valid and new W30 retry intent absent; revalidates same host/old Actions, port/local health, all prior receipts, C40 hash, and no stage files. Writes fresh W30 retry intent BEFORE touching any Task state. If retry fails, preserves both attempts and holds; there is no automatic third try.

Three new protected W30 one-shot receipt filenames, distinct from historical W22/W24/W21, W29, and reserved W28:
- UCIE_W30_OWNER_SECONDARY_RECOVERY_INTENT_V01.json
- UCIE_W30_OWNER_SECONDARY_RETRY_INTENT_V01.json
- UCIE_W30_OWNER_SECONDARY_RESTORED_V01.json

The W30 script checks an exact first-party Git ancestor (W29 main ddcbb9eb...), a clean checkout and the immutable W29 PS Git blob 848cb03f50dc455fc61935a484c3d71e82506c90. It uses a PowerShell parser to extract ONLY the approved first-party W29 helper function bodies including the actual InvokeW29RestoreOld. It does NOT dot-source or invoke W29 -RehearseOld or -RecoverOld, and never runs W19/W21/W22/W24 Apply or rollback. W30 writes only its three new receipts, through an exclusive no-overwrite atomic move. Prior W29 and historic recovery receipts remain untouched.

### Strict safety boundaries

- Requires same account/UAC, owner-protected private archive, historical six W22/W24/W21/emergency receipts valid, W29 failed recovery intent evidence, exact OLD executable/args/working directories and unchanged running C40 action hash.
- A FREE port is allowed only when original LocalV1 task is Disabled/Ready and old HTTP health is not responding; a single 127.0.0.1 listener is allowed only if original task is Running and exact old LocalV1 health responds. Any other/multiple/unknown listener is a HOLD, never kills unknown Python.
- If local old HTTP is already healthy and both writers Ready, W30 may record the restoration proof without gratuitous task restart (the W29 prior restored receipt must still be absent).
- If an unrelated task Action or task owner differs, if W19/W13/W20 stage/marker/newroot runtime is present, if C40 changed or owner/ACL/source pin fails, no task enable/start operation is permitted.
- W30 cannot prove local listener PID matches the Scheduled Task process, C40 MCP/tunnel roundtrip, global SQLite consistency or full migration acceptance, and claims none. A second-level restoration failure remains a genuine manual-review HOLD, not guaranteed self-healing.

## CI failure-injection scope

- tests/test_ucie_w30_secondary_restore_native_fixtures_v01.py executes actual W30 recovery candidate/lineage/receipt core and ACTUAL pinned W29 InvokeW29RestoreOld PowerShell function against in-memory mock TaskScheduler, HTTP, port and C40. Positive scenarios: full disabled state, already healthy local+partially enabled writer, completed-but-W29-final-receipt-missing state. Negative: foreign/multiple listener, wrong task owner/action, staged output, C40 drift, missing or changed W29 records, mid-second-writer enable failure, receipt ordering and one separately journaled bounded retry; no third blind attempt.
- tests/test_ucie_w30_secondary_journal_exclusive_temp_v01.py uses actual W30 Absent/SaveW30 PowerShell AST with a disposable CI temporary directory, proving no duplicate W30 intent overwrites, legacy W29 canary bytes unchanged, retry/restore intent files created only at whitelisted paths, and no orphan temp.
- Full Windows/Ubuntu Python3.13+3.15 CI must PASS. These tests have NO permission to contact any owner Windows host, live SQLite, installed Task Scheduler, C40/tunnel, or private archive.

## Remaining next gate

W30 is one layer of bounded recovery after W29; it is NOT authorization for a real W29 outage. Its actual Windows-host behavior, task DACL/ACL, port listener-to-task PID mapping and C40 MCP roundtrip still have not been accepted. The migration transaction still needs separately tested write-barrier/live SQLite handoff and a reliable operational/manual recovery runbook for beyond-bounded failures before owner maintenance GO.

Current owner service: D:\UCIE remains the accepted old-root operation. No PC instructions are required for W30.
