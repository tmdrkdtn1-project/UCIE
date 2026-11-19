# UCIE W25 — W21 nested error evidence and original service recovery review

Date: 2026-11-19. Scope: UCIE first-party repo and UCIE-only protected owner archive. Other projects, private connected apps, tunnel restart, cross-project code, unapproved external repositories and private operator data out of scope.

## Owner Windows evidence (real owner-provided receipt, not independently accessed)

```json
{
  "schema":"UCIE_W24_PRE_REBIND_OWNER_RECOVERY_V01",
  "status":"UCIE_W24_PRE_REBIND_ORIGINAL_SERVICE_RESTORED",
  "localv1_http_healthy":true,
  "original_writer_schedules_enabled":2,
  "c40_action_unchanged":true,
  "original_sqlite_overwritten_by_recovery":false,
  "full_cutover_authorized":false
}
```

Old task actions remain on `D:\UCIE`; LocalV1 is healthy by the owner-provided health receipt; both old collector schedules re-enabled, with normal future writes to old SQLite possible. This was a targeted recovery from W24/W21 partial maintenance, not a new-root cutover or C40 MCP/tunnel acceptance.

The preceding, owner-provided read-only triage found original 3 UCIE task actions `OLD_EXACT` and all `Disabled`, 18767 port free, and W24/W21 intents present. Critically W19_STAGE, W13_REBIND and W20_PILOT private journals, W19 final SQLite private data and new-root runtime were all absent. W24's generic `-ResumeOld` delegates W21 rollback, which explicitly refuses rollback without a W13/W20 journal. Thus the separately guarded owner-approved pre-rebind recovery restored old LocalV1 then the two old collectors, without deleting original W22/W24/W21 intents or SQLite.

## Underlying error still NOT identified

W21's `-ApplyLocal` catches nested errors and previously emitted only the stable `UCIE_W21_LOCAL_ONCE_FAILED_PRESERVE_RECEIPTS_EXPLICIT_ROLLBACK_ONLY` error. Source proves nested W19 `-Apply` was attempted, but missing W19 stage receipt means the failure happened before W19 persisted its stage journal, or during W21's immediate check for that journal. We cannot decide whether an exact-path, ACL, Git, original Scheduled Task action/state or another pre-journal guard failed based on existing evidence.

Source ancestry for W19 expected W18 base `853736a0c82c0c348665b6b8acb99e3c3a6d4825` was checked in first-party GitHub and is an ancestor of W24 main; this narrows *only* the source version concern. It does not prove Windows owner's on-host prejournal checks passed.

## W25 non-mutating source improvements

1. Existing `scripts/ucie_owner_w21_single_local_maintenance_v01.ps1` has a stable error ID, but now additionally prints a JSON `UCIE_W25_W21_SANITIZED_CHILD_FAILURE_V01` with the last nested stage (`W19_OWNER_APPLY`, `W19_STAGE_JOURNAL_REQUIRED`, etc.), exactly matching canonical first-party UCIE error identifiers when present and otherwise a generic noncanonical exception class. It does **not** emit raw exception text, command line, stack trace, private archive path, private task arguments, or secrets. Keeps one-shot journal and fail-closed behavior.
2. New `scripts/ucie_owner_w25_w19_prejournal_probe_v01.ps1` defaults to `UCIE_W25_CONTRACT_ONLY_NO_HOST_ACCESS`. Its explicitly owner-approved `-CheckLocal` mode is **read-only**: verifies same-user elevated Windows identity, owner-protected archive ACL, canonical first-party Git ancestry and clean checkout, direct W19 Python/PowerShell/rebinder source files, W22/W24/W21 historical intent+prior restore receipts and C40 action hash, three original task actions/owner and current operating states, absence of W19/W13/W20 stage outputs, and old LocalV1 HTTP health. Does not open operating SQLite, write journals, mutate Task Scheduler, start/stop processes or alter C40.
3. New `tests/test_ucie_w25_w21_failure_visibility_readonly_v01.py` checks PowerShell parser and no-host contract/denied approval on CI, exact read-only behavior, redacted nested failure reporting and source guard order. CI does **not** exercise Windows Task Scheduler live effects or owner-run `-CheckLocal`.

### Suggested owner commands AFTER source PR merge and pinned clean source synchronization

The owner must not invoke W21/W24 Apply again against existing private journals. W25 read-only check is independent of applying any migration.

```powershell
# No-host contract.
& 'D:\UCIE_PROJECT\UCIE\scripts\ucie_owner_w25_w19_prejournal_probe_v01.ps1' -ContractOnly

# Read-only owner check in same-user UAC-elevated Windows PowerShell:
& 'D:\UCIE_PROJECT\UCIE\scripts\ucie_owner_w25_w19_prejournal_probe_v01.ps1' -CheckLocal -OwnerApproval 'AUTHORIZE_UCIE_W25_READONLY_POSTRECOVERY_W19_PREREQUISITES'
```

Even a passing W25 `-CheckLocal` checks the **currently running old-root state**, not the previously disabled task state. It MUST return `root_cause_verified=false` and `prior_w21_nested_error_reason=NOT_CAPTURED`. A status saying recovered old-root prerequisites are consistent is NOT a proof that W19 can apply during another maintenance window.

### Invariant boundaries

No automatic process kill, unknown Python 18767 process identity inference, task DACL changes, C40/tunnel restart, credentials, old DB overwrite, stale W16 snapshot restore, scheduler registration, W19/W21 journal deletion, automatic rule promotion, customer release or full cutover. W19 fresh ten-SQLite copy, W20 new-root pilot, and two-writer activation remain HOLD pending root-cause verification and owner-approved recovery-tested maintenance design.

Issue: https://github.com/tmdrkdtn1-project/UCIE/issues/199.
