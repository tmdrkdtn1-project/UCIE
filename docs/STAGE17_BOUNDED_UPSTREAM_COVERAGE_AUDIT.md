# UCIE Stage 17 — bounded live public PR identity and file-listing coverage audit

Stage 16 audits ONLY the local Stage13/Stage15 relationship. Stage 17
addresses its most important external uncertainty without touching the
operating miner or changing scheduled work.

## Explicit one-shot read-only command (OFF by default)

This command only works after Stage13 and Stage15 each have their
separately authorized, existing public evidence ledgers. No new local
activation marker is created, no change to Stage11-15 hourly collection
or scheduled task is made. It is **not** in the hourly miner.

~~~powershell
$root = 'D:\UCIE'
$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = "$root\src"
    & "$root\.venv\Scripts\python.exe" -B -m ucie_miner audit-external-evidence-chain
    # Select only an existing Stage15 PR candidate from the approved 5 repositories:
    & "$root\.venv\Scripts\python.exe" -B -m ucie_miner audit-public-pr-coverage --source python/cpython --pr 12345 --live
} finally {
    $env:PYTHONPATH = $prior
}
~~~

The example PR number is a placeholder, **not** a validated or automatically
selected target. Use a number present in the Stage15 ledger. Do not interpret
a fake example as a recommendation to query PR #12345.

## Actual scope

1. In SQLite \`mode=ro\` and \`query_only\`, validate Stage13/15 schema,
   source, PR identity and historical evidence hash and Stage16 integrity.
2. Separately inspect any Stage14 local official evidence metadata, reporting
   only **counts by evidence kind for the same approved source**. Do not claim
   a document, release or GHSA is related to the specific PR.
3. With operator \`--live\`, call exactly one allowed GitHub public PR metadata
   endpoint and validate canonical repository, PR number, merged state, merge
   SHA, and GitHub-reported \`changed_files\` (bounded 0–3000).
4. Only if the merge SHA still matches local pinned history, request at most
   three 30-file PR-file pages. Check page sizes, duplicate file identities,
   coverage vs GitHub's declared file count and stable Stage15 first-page
   feature hints. Never save filenames or patch/body text.
5. Use at most **4 anonymous GETs total per one-shot command**; stop at
   the rate-budget floor or clearly report partial/mismatched evidence.

Statuses are always **NO_GO**, even when the upstream identity and bounded
file listing match:

- \`STAGE17_UPSTREAM_LISTING_RECHECKED_UNVERIFIED_NO_GO\`: up to 90 changed
  files completely enumerated at observation time, and first-page feature
  hints match the existing Stage15 snapshot.
- \`STAGE17_PAGINATION_INCOMPLETE_NO_GO\`: more files exist than the three-page
  cap permits, or the listing cannot be considered complete.
- \`STAGE17_UPSTREAM_MERGE_MISMATCH_NO_GO\`: upstream merge SHA differs; do
  not request patches.
- \`STAGE17_LOCAL_FIRST_PAGE_HINT_MISMATCH_NO_GO\`,
  \`STAGE17_FILE_COUNT_MISMATCH_NO_GO\` or
  \`STAGE17_API_RATE_PAUSED_NO_GO\`: keep candidate unverified and do not
  misrepresent it as complete.
- Invalid remote data, foreign SQLite schemas and unapproved paths fail
  closed without leaking upstream content.

## Critical limits

A complete **file listing** is *not* a complete patch/hunk retrieval: GitHub
can omit patch hunks on large diffs. Rechecking against the same public GitHub
API is not independent reproduction, independent verification, formal security
signoff, an approved license, or an attestation of deployment versions.

Stage14 official data is *source-associated only*: exact PR-to-release,
PR-to-GHSA and PR-to-document-semantic linkage remains unproven. No version
or vulnerability-fix claim is inferred. The prior Stage15 SQLite is not
rewritten to assert full coverage. No public sources beyond the original five
allowlisted upstreams are added. No automatic promotion, rules, model
training, package publication, credentials or unrelated-project access occurs.

The cross-platform CI uses injected inert responses; GitHub Actions success
does not certify the owner's Windows PC. Owner-host inspection and any
separately authorized live one-shot should be reported as distinct receipts.
