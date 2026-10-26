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

## Stage 4 — two explicitly separated, evidence-gated QA lanes
- **Default PUBLIC_ONLY manual scan: AUTOMATED_QA_OWNER_RISK_ACCEPTED.** Requires the existing owner-release contract: clean UCIE `main` checkout; current passing Windows/Linux GitHub CI for the exact commit, including pinned runtime and PowerShell tests; explicit master risk acceptance; distinct manual owner signature; recipient verification of signature, serial, expiry and scope. This first-party QA is *not* an independent human audit or legal license signoff.
- **Optional stronger assurance: INDEPENDENT_QA_AND_OWNER_SIGNED.** A genuine external reviewer independently verifies evidence and signs an attestation. The existing separate QA/owner trust-anchor verifier is unchanged and must not be bypassed or represented as first-party QA.
- Neither route allows automatic rule promotion, unattended signing, auto-fix, private-project inspection or cross-project information sharing. Source-version applicability and license obligations remain explicit evidence conditions; unknowns remain NO_GO for unsupported uses.
- Source of approved policy: `docs/STAGE4_AUTOMATED_QA_OWNER_APPROVAL.md` (2026-10-18).

**NO-GO:** No project integration, operations-code mutation or unattended mining until the applicable acceptance criteria are satisfied.
