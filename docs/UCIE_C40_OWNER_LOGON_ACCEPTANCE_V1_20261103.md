# UCIE C40 owner logon acceptance: manual-only two-phase gate

This checks the **existing** \UCIE-C40-Recover owner logon trigger. It does not
create tasks, log off Windows, reboot, change clients, or approve other UCIE rules.

## Before signout

1. Save open Windows work and ensure the owner knows Windows credentials.
   This may close local apps, including the ChatGPT browser and tunnel.
2. On owner **elevated** PowerShell:
   \`& 'D:\UCIE\scripts\ucie_c40_owner_logon_acceptance_once.ps1' -Mode Preview\`
3. Only if the Preview reports exactly one UCIE client and a Running/Highest
   owner task with an AtLogOn trigger:
   \`& 'D:\UCIE\scripts\ucie_c40_owner_logon_acceptance_once.ps1' -Mode Prepare -OwnerOnlyConfirmed\`
   This creates only a single-use UCIE JSON baseline marker. It does NOT
   sign out and it does NOT terminate the client.

## Owner action

Perform a **real Windows account sign out** from the local PC, then sign back
in as the same owner. Lock/unlock, closing a browser tab, switching users
without signing out, or refreshing ChatGPT are NOT substitutes.

## After owner signs back in

Launch elevated PowerShell again and run:
\`& 'D:\UCIE\scripts\ucie_c40_owner_logon_acceptance_once.ps1' -Mode Verify -OwnerOnlyConfirmed -OwnerSignedOutAndBackInConfirmed\`

The test fails closed unless the same exact owner task is Running/Highest,
its last run occurred after the marker, the matching UCIE C40 client is
a *new* process created after the marker, its PID changed, and a fresh
CYCLE_OK/client_count=1 receipt is present after that marker.

A successful owner-local Verify is not evidence of plugin connectivity.
Independently call \`ucie_admin_capabilities\` and recheck exact PID/task
through the connected UCIE tool after returning to ChatGPT.

The original C40 loss drill receipt stays untouched. Never rerun its
\`-Mode Apply\`. Never run the Disabled-only activation Apply when the task
is already Running. Do not erase the single-use logon marker merely to retry;
review observed failure and create a new scoped procedure only if necessary.

**Release gate:** live loss restore PASSED 1 owner trial. Owner logon recovery
remains NOT_RUN until the above owner action, post-login Verify and independent
bridge check all succeed. PR #175 stays DRAFT; automatic rule promotion OFF.
