# UCIE development roadmap

## Stage 1 — offline PUBLIC_ONLY demonstrator
- Curated public-only entries with allowlisted official source URL format.
- Non-executing Python AST parser probe.
- Ed25519 demonstration signing, tamper/expiry/rollback verification.
- Unit tests for private markers, unsafe probe candidates and malicious archives.
- Status: Stage 1 unit tests passed locally on Python 3.13; Python 3.15 compatibility on the user's PC is pending.

## Stage 2 — third-party public-code data mining
- Explicit allowlist of independent third-party repositories; owner, license, URL, revision, deletion and opt-out checks.
- Official public APIs and bounded incremental ingestion with rate limiting and checkpoints.
- Quarantine all downloaded code as untrusted bytes; execute no external code in a privileged host.
- Deduplicate bug-fix patterns, independently reproduce candidates, and save only verified general rules.

## Stage 3 — permanent records and supervision
- SQLite knowledge and checkpoint databases, migrations, audit trail, backup and rollback.
- Dedicated local Windows scheduled worker with singleton guard, bounded retries and alerts.
- Daily and weekly evidence-based reports. Separate observed / inferred / tested / approved.
- Publish only safe code, independently verified knowledge and public reports to GitHub.

## Stage 4 — independently gated distribution
- Isolated security and VM acceptance tests.
- Signed public Rulepack production distribution and recipient-side checks.
- Independently approved project-specific private adapters; never send their data upstream.

**NO-GO:** No project integration, operations-code mutation or unattended mining until the applicable acceptance criteria are satisfied.
