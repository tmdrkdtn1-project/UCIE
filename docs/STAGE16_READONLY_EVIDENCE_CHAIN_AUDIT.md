# UCIE Stage 16 — read-only historical/fix evidence chain audit

Stage 13's retained historical metadata digest and Stage 15's structured,
unsigned fix review records are **not independently verified upstream fixes**.
Stage 16 provides a deliberately narrow *local* consistency check without
adding collection APIs, activation markers, scheduler changes, or rule promotion.

## Run (offline; does not mutate any SQLite database)

~~~powershell
$prior = $env:PYTHONPATH
try {
  $env:PYTHONPATH = 'D:\UCIE\src'
  & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner audit-external-evidence-chain
} finally {
  $env:PYTHONPATH = $prior
}
~~~

It opens the Stage 13 and Stage 15 isolated databases using SQLite
\`mode=ro\` and \`PRAGMA query_only=ON\`. Neither missing database is created.
For each Stage 15 review candidate, match its approved source, PR number and
historical evidence SHA256 to Stage 13's exact historical revision, then compare
merge SHA and expected skill. Validate bounded structural metadata and fixed
UCIE-authored safe-call/regression guidance. Corrupt ledgers fail closed.
No upstream code, untrusted commands, new GitHub GETs or file-scanning occurs.

Only counts and fixed identifiers are emitted:

- \`STAGE16_INCOMPLETE_LOCAL_EVIDENCE_NO_GO\`: one or both required DBs absent.
- \`STAGE16_LOCAL_EVIDENCE_MISMATCH_NO_GO\`: orphaned revision, merge SHA
  mismatch, or invalid Stage 15 review field.
- \`STAGE16_LOCALLY_LINKED_BUT_UNVERIFIED_NO_GO\`: all available Stage 15 rows
  are internally consistent. **If there are zero rows, this is a vacuous
  consistency check, not evidence that any fix exists.**

## Boundaries and remaining gaps

Stage 15 inspects only the first up-to-30 PR files; a 30-file result can have
additional pages. Stage 16 does not compensate for missing PR pages or
independently attest the currently published upstream merge identity. Stage 14
published release/advisory/doc inventory has no causal PR linkage. A document
hash difference is not a semantic change assessment. Hence even a complete
local match is **NO-GO** for independent fixes, exact affected versions,
license approval, regression PASS, automatic promotion, signing or deployment.

Run the unit tests in CI, then separately check the owner Windows host after
updating reviewed code. CI success is not owner-host operational attestation.
