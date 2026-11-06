# UCIE automatic public collection inventory — on-demand read-only report V0.1

Date: 2026-11-05 / PROJECT=UCIE ONLY
Status: independent aggregation of public-only ledgers, NOT release approval.

## User problem and implemented solution

The existing ChatGPT UCIE administrator plugin can edit approved UCIE source
and run a single owner-approved unittest, but has **no general purpose
read-only runtime database count endpoint**. Before this change, counts had
to be inferred from old Slack receipts or user screenshots. Historical counts
are not an answer to "how many are stored NOW?"

This implementation adds a narrowly scoped aggregate-only snapshot from the
owner's *actual* UCIE public collection ledgers. It does not read private
source code or other project files, and it never calls GitHub or the miner.

## Data units MUST stay distinct

- \`legacy_miner.candidates\`: public PR rows in the **original** two-source
  \`runtime/public_miner.sqlite3\`. Source identities are only
  \`python/cpython\` and \`PowerShell/PowerShell\`.
- \`legacy_miner.runs\`: completed ledger run entries, not all operating
  system TaskScheduler invocations.
- \`stage10_public_candidate_staging.candidate_revisions\`: revisions in
  dedicated \`runtime/stage10_unverified_public_candidates.sqlite3\`.
- \`stage10_public_candidate_staging.git_commit_revisions\`: separate public
  commit revisions (distinct row grain).
- \`stage12_unverified_review.review_proposals\`: separate human-review
  queue in \`runtime/stage12_unverified_review.sqlite3\`; may overlap the
  original Stage10 revisions, and therefore NEVER added to the PR count.
- \`recent_hourly_activity\`: two recent local receipts, with freshness and
  gap checks from the already-existing V12 proof code. **This does not
  authenticate Windows Scheduled Task events.**

Do not equate these counts with W04 **search matches** or approved/usable
skills. Unknown/missing/corrupt files return null or NO_GO, never a fake zero.
No status implies external source validity, rights, independent QA, model
training, deployment or rules promotion.

## Owner local commands

On demand, for raw JSON:

    & 'D:\UCIE\scripts\ucie_public_collection_report_v01.ps1'

This combines the new SQLite read-only snapshot with the existing
\`scripts/task_status.ps1 -Evidence\` (TaskScheduler event linkage) in a
single bounded JSON report. It checks exact owner identity, task action and
two TaskScheduler event-linked runs. It does not register or run a task.

For the simple Korean Markdown report (no scheduled-task attestation):

    $env:PYTHONPATH = 'D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.public_collection_inventory_v01 --format markdown

The Markdown command prints to stdout; no file is created automatically.
PowerShell callers may explicitly redirect the text into an owner-chosen
UCIE-only report file as a distinct approved operation.

## ChatGPT self-check integration boundary

An owner-approved **single UCIE unittest file**
\`test_ucie_public_collection_inventory_owner_live_v01.py\` reads only these
fixed UCIE-owned public ledgers and prints **aggregate-only counts**.
It runs only when the checkout is exactly \`D:\UCIE\`; ordinary Actions
checkouts skip. This is a manually approved on-demand owner test using the
existing UCIE Admin bridge; it is not a live always-on MCP admin count tool.

For a permanently callable UCIE Admin count tool without tests, a separate
owner-controlled plugin/server registration and authentication gate would
need to be implemented and approved. Merely adding a Python source file
does not register or deploy a ChatGPT MCP tool.

## Verification and security gates

- SQLite URI \`mode=ro\`, \`query_only=ON\`, \`trusted_schema=OFF\`.
- No SQLite schema creation/migration or write statements.
- Fixed path UCIE/root and symlink protection; rejects unexpected source IDs.
- Counts and status checked against known schemas and allowed values.
- Stage10 and Stage12 are inspected using *existing* UCIE read-only
  inspector functions, not any new collection loops.
- Any invalid ledger or stale/missing receipt is NO_GO, with the successful
  independent counts still separately visible when safe.
- No public HTTP, new scheduled job, C40 mutation, data export, signing,
  cross-project access, approval or model-training.
