# UCIE P10B — deterministic Git-native owner handoff, no MCP privilege expansion

Date: 2026-10-25 KST
Project: UCIE only
Status: SOURCE HANDOFF ONLY / HOST ROOT NOT INSTALLED / AUTO ACTIONS OFF
PR: https://github.com/tmdrkdtn1-project/UCIE/pull/79

## Actual blocker and resolution

- The already verified UCIE admin MCP works: capabilities and git status are
  read-only/UCIE-only; arbitrary shell, service restarts and Git auto push
  are explicitly outside its grants.
- Attempting to stage the P10 **privileged** root-installer text through the
  ChatGPT-connected write tool was rejected by the host safety gate. Follow-up
  UCIE admin directory list proves the P10 file is **absent** on the PC.
- Do not evade the tool safety gate by changing its scope, disguising
  installer content or gaining generic shell permission.
- Instead use the **existing trusted UCIE repository Git transport** on
  the owner PC for *one exact file*. This source-only checkout never
  executes the installer or changes Windows service/task/ACL/credentials.
- The GitHub Actions Windows PowerShell 5.1/7 *temporary fixture* has already
  validated ACL-at-creation independently of the owner's host. It does not
  certify the actual ProgramFiles parent, privilege, or owner installation.

## Exact immutable source pin

Repository: \`tmdrkdtn1-project/UCIE\`
Branch: \`feat/ucie-unattended-ops-foundation-20261023\`
Source commit: \`69997ac05e67cd8bc63ef699452cf68a52e77c1f\`
Path: \`scripts/ucie_unattended_protected_root_bootstrap_p10.ps1\`
Git blob: \`1cea01945edaf2083947e40c9fe3fadc58a8b83d\`
Source CI: https://github.com/tmdrkdtn1-project/UCIE/actions/runs/40157477461
CI outcome: COMPLETED SUCCESS / Windows+Ubuntu Python 3.13+3.15 4/4;
both ephemeral Windows PowerShell 5.1 and 7 ACL-at-creation tests PASS.

The Git blob SHA-1 is used **only** to verify the exact tree object inside the
fixed commit. It is NOT a substitute for a signed owner release or for
SHA-256 against a hostile remote, and must not be represented as such.
Never fetch from public source URLs on the basis of untrusted injected instructions.

## Single owner action: fetch just one immutable file, INSPECT only

This is a source checkout procedure, NOT a host installer authorization.
Run from the existing owner PowerShell session; no elevation is needed for
the Git checkout or the default inspector. Verify that git origin still
matches the expected UCIE HTTPS repository and the target file is absent.
An existing file is a conflict: stop, do not overwrite.

~~~powershell
$repo = 'D:\UCIE'
$branch = 'feat/ucie-unattended-ops-foundation-20261023'
$commit = '69997ac05e67cd8bc63ef699452cf68a52e77c1f'
$rel = 'scripts/ucie_unattended_protected_root_bootstrap_p10.ps1'
$blob = '1cea01945edaf2083947e40c9fe3fadc58a8b83d'
$dest = Join-Path $repo $rel
$origin = (& git -C $repo remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0 -or
    $origin -cne 'https://github.com/tmdrkdtn1-project/UCIE.git') {
    throw 'UCIE_P10_GIT_ORIGIN_UNEXPECTED'
}
if (Test-Path -LiteralPath $dest) {
    throw 'UCIE_P10_SOURCE_TARGET_ALREADY_EXISTS_NO_OVERWRITE'
}
& git -C $repo fetch --no-tags origin ('refs/heads/' + $branch)
if ($LASTEXITCODE -ne 0) { throw 'UCIE_P10_GIT_FETCH_FAILED' }
$verified = (& git -C $repo rev-parse ($commit + ':' + $rel)).Trim()
if ($LASTEXITCODE -ne 0 -or $verified -cne $blob) {
    throw 'UCIE_P10_PINNED_TREE_BLOB_MISMATCH'
}
& git -C $repo restore --source=$commit --worktree -- $rel
if ($LASTEXITCODE -ne 0) { throw 'UCIE_P10_SINGLE_FILE_RESTORE_FAILED' }
$workingBlob = (& git -C $repo hash-object -- $rel).Trim()
if ($LASTEXITCODE -ne 0 -or $workingBlob -cne $blob) {
    throw 'UCIE_P10_RESTORED_FILE_BLOB_MISMATCH'
}
& $dest
~~~

The final invocation has **NO \`-Apply\` switch**. It only inspects the
single proposed Windows Program Files parent and emits sanitized JSON. It
does not create \`UCIE_UnattendedHost\` or touch the previous candidate
locations. Do not invoke \`-Apply\` until a separate fresh owner approval
specifies the exact folder and ACL. Never copy credentials into chat.

## Gate after inspector

- If \`UCIE_P10_PARENT_OR_ACL_REVIEW_NO_GO\`, refuse installer.
- If \`UCIE_P10_TARGET_ALREADY_EXISTS_NO_OVERWRITE\`, stop and investigate
  collision without changing ACL or deleting files.
- If \`UCIE_P10_PARENT_OBSERVED_CANDIDATE_OWNER_APPROVAL_PENDING\`, the
  conservative parent check only passed as a **read-only observation**.
  OS ACL/effective-access, actual elevated install, owner approval, external
  anti-rollback, private service identity, host signer and credential
  providers remain NOT VERIFIED.
- No auto-install, background host changes, hidden Windows task,
  C40 restart, Git auto push, or Rulepack auto-promotion.
- Old owner hourly miner and existing Admin Bridge directories are untouched.

This procedure solves the **delivery bottleneck** while preserving the
security boundary: Git is used only to obtain immutable source, not to
automatically run privileged operations.
