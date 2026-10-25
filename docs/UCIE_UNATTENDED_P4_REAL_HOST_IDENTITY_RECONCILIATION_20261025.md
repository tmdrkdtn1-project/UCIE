# UCIE unattended P4 — first real Windows preflight and identity reconciliation

Date: 2026-10-25 KST
Project: UCIE only
PR: https://github.com/tmdrkdtn1-project/UCIE/pull/79
State: OWNER HOST OBSERVED / INSTALLATION NO_GO / LEARNING AUTO-PROMOTION OFF

## User-supplied actual read-only Windows inspection

\`UCIE_WINDOWS_HOST_READONLY_PREFLIGHT_V1\` reported:
- Exact UCIE root, GitHub origin, clean tracked worktree, Python/worker: true.
- One valid C40 profile/executable pair; hashes measured by owner PC but
  intentionally not copied into this public PR.
- Existing \`UCIE-PublicMiner-Hourly\` present with exact action and \`Ready\`;
  \`existing_hourly_miner_principal_matches_current_user=false\`.
- Proposed \`UCIE-C40-Supervisor\` task name not occupied.
- Existing \`D:\UCIE\.ucie_bridge_state\` exists but has owner SID different
  from current Windows shell, ACL inheritance enabled, broad-write ACE check
  not passed.
- Independent host ACL trust, external rollback/revocation anchor, GitHub
  installation credential, real C40 functional postprobe, actual service/task
  installation, real Git push and automated rule promotion remain unverified.

A task principal name may resolve to the same user SID despite different
display text; the old name-string comparison alone cannot establish identity
mismatch. It is also incorrect to treat the existing UCIE admin bridge state
as the newly proposed unattended-operations journal. **Do not claim that
changing the existing bridge ACL or task principal is required.**

## P4 correction

\`scripts/ucie_unattended_identity_acl_readonly_v2.ps1\`:
- Reads ONLY exact UCIE current user SID (never outputs SID/name), exact
  \`UCIE-PublicMiner-Hourly\` task principal (translates display name or SID to
  a comparable SID), and proposed supervisor task-name collision.
- Summarizes existing \`D:\UCIE\.ucie_bridge_state\` ACL separately from
  proposed \`D:\UCIE_DATA\ucie_unattended_state\` ACL. Proposed path is
  **outside the source Git checkout**. No new directory created.
- Records only minimal ACL/owner classification booleans (known built-in
  System/Admin versus current user, inheritance, broad allow-write flags).
- Does **not** fix/delete/move existing bridge state, touch scheduler, read
  user secrets, create keys, restart C40, push Git, or sign/promote any rule.
- CI Windows stage syntax parses the file without executing it; offline
  tests prohibit mutating PowerShell cmdlets.

This is a **targeted read-only follow-up observation**, not a license to
register a Windows task or widen the existing Admin MCP tool scopes.
The report remains untrusted pending owner PC origin and independent OS trust.

## Correct owner acceptance sequence

1. Deploy only this read-only P4 diagnostic through UCIE admin bridge
   \`ucie_admin_write_text\` with \`expected_sha256=ABSENT\` after exact HEAD CI;
   verify \`written=true\` and subsequent directory listing.
2. Owner PC runs only after SHA256 match:
   \`& 'D:\UCIE\scripts\ucie_unattended_identity_acl_readonly_v2.ps1'\`.
   Return resulting non-identifying JSON; do not paste raw account SID,
   Windows username, full ACE list, tokens or private keys.
3. If existing task principal resolves to same SID, retain task unchanged;
   if a genuinely distinct SID, determine whether it is an authorized
   independent UCIE runner, without blindly reassigning ownership.
4. Preserve \`.ucie_bridge_state\` as existing bridge-private state. Do not
   change its ACL or copy it into the new journal; inspect only for exposure
   risks and escalate separately if its ACL is unsafe.
5. For future approved unattended operations, owner creates a dedicated
   protected \`D:\UCIE_DATA\ucie_unattended_state\` under verified SID,
   explicit ACL, no broad-write ACE and separate externally authenticated
   monotonic anti-rollback anchor. Setup not yet implemented or approved.
6. Only after owner-signed restricted host policy, token scope and actual
   supervisor acceptance may Git Draft PR and C40 recovery be activated.
   No main push or auto merge, no Rulepack auto promotion without distinct
   independent QA and per-rule owner release signing.

## Safety and evidence boundary

An offline PASS proves the script parses and safety fixtures pass; it
does not mean the local Windows host actually ran the diagnostic.
Creating the diagnostic file through the UCIE-admin bridge is a source-file
write only, not service installation. The first P4 report was supplied by
the owner; its flags should not be reinterpreted as a fresh authenticated
host process-level acceptance without corroboration.
