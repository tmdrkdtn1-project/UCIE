# UCIE Stage 10 — Public candidate staging and operator read-only trial

## Improvement beyond Stage 9

UCIE now has a separate candidate-only staging ledger for public skill evidence.
A verified public PR identity is not a verified fix or approved Rulepack.

The first-party Stage 10 module takes only a structurally validated Stage 9
batch, up to three records, and extracts approved public source and PR number,
merge SHA, evidence digest, UCIE skill category, fixed error tags, missing
evidence types, and UTC observation timestamp. No full patch, public title,
path, executable snippet, or arbitrary outside text is retained.

Staging defaults to an in-memory SQLite database and does not write any files.
An explicit, separately opted-in write mode targets ONLY the dedicated
UCIE runtime/stage10_unverified_public_candidates.sqlite3 file, never
runtime/public_miner.sqlite3 or the existing Knowledge DB. The staging file
contains only UNVERIFIED_CANDIDATE_ONLY rows. Repeating an identical public
PR and evidence digest is idempotent; an evidence change appends a revision.
Existing foreign schemas, unexpected triggers and symlinks are rejected.

## CLI controls

In a reviewed UCIE development checkout, pass a bounded Stage 9 public
batch JSON receipt through stdin:

    python -m ucie_miner stage-public-candidates-stdin

This stages into temporary memory only. The additional
--write-separate-ledger flag authorizes a separate UCIE candidate-only
SQLite write, and must never be used without a deliberate host decision.

    python -m ucie_miner inspect-public-candidate-ledger

The inventory command opens only the candidate DB in SQLite mode=ro and
query_only=ON. If it does not exist, it returns STAGING_FILE_ABSENT and
never creates the directory/file. Inventory totals and five skill counts
are not approval signals. No command alters scheduler registration, model
weights, operating miner, package installation or Rulepack signing.

## Windows operator read-only acceptance

The UCIE-owned script
scripts/ucie_stage10_operator_readonly_trial.ps1
is a manual operator tool, never a registered scheduler task.

It pins D:\UCIE and its .venv Python interpreter, runs the existing host
preflight and the candidate-only inventory, and checks before/after SHA-256
of only the dedicated UCIE miner, Knowledge and candidate-stage DBs.
It prints compact JSON with READ_ONLY_OPERATOR_TRIAL_NO_GO. By default
it does not access any external API.

Explicit -AllowPublicReads additionally requests one approved public
MCP Python SDK metadata feed and up to one public code/document/release
enrichment, without writing the response to disk. An API failure does
not turn into success. A changed DB hash can also arise from another
concurrently running authorized task, so the operator must investigate;
this script does not attribute a concurrent write to itself.

Example (only after local owner reviews a separately deployed branch):

    powershell -NoProfile -File D:\UCIE\scripts\ucie_stage10_operator_readonly_trial.ps1

Optional one-shot public-only request:

    powershell -NoProfile -File D:\UCIE\scripts\ucie_stage10_operator_readonly_trial.ps1 -AllowPublicReads

The current development environment has not performed these commands
on the owner's Windows host.

## Evidence and operating boundary

Only approved public GitHub repositories and official documentation
are in scope. Outside code is untrusted, never executed, silently
expanded or bulk-persisted. The history inventory stores no model
training state and never creates approved rules. CI is first-party
synthetic, and any detached reviewer receipt remains untrusted without
independent attestation.

Actual upstream bug fix before/after = NOT VERIFIED.
Human independent reviewer authorization = NOT RECEIVED.
Rulepack signing and automatic promotion = DISABLED.
Owner-PC host acceptance = NOT EXECUTED.
Operating database writes or scheduler change = NONE.
Main-branch merge, distribution and production GO = NONE / NO_GO.
