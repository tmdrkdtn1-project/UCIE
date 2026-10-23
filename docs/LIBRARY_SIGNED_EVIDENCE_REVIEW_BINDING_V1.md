# UCIE Library review closure boundary V1 — signed claims, provenance and revocation

## Purpose and delivery scope

This change implements the **next read-only integration stage** of the
Library review loop on existing PR #77. It reuses two previously implemented
components rather than replacing them:

- `preview_library_evidence_assessment(current, previous)`: approved five-source
  metadata classification, evidence gaps and incremental review queue.
- `inspect_local_library_review_history(root, ..., expected_head_sha256)`:
  UCIE-only existing SQLite append-only history, serial/chain verification,
  Ed25519 keyholder assertions, expiry and owner revocation.

New module: `src/ucie_miner/public_library_review_binding.py`;
entrypoint: `inspect_library_review_closure(root, current, *,
owner_trust, qa_trust, expected_head_sha256, previous=None, at_time=None)`.

It also calls the existing Stage 16 **Stage13 ↔ Stage15 local identity audit**
`audit_external_evidence_chain(root)`. That check tests UCIE-only stored
metadata consistency, not independent upstream identity or actual QA.
No new database, MCP tool, scheduler, trust key, API exposure or network GET.

## End-to-end read-only decision path

1. Validate a bounded original UCIE five-source batch through existing
   Library graph/assessment validators. Reject forged approvals, unapproved
   sources and untrusted guidance.
2. Require a SHA-256 **expected history head explicitly provided by the
   caller's independently maintained trust process**. Reject missing,
   malformed or mismatched head. The library does not fetch, create, or claim
   independence of this checkpoint.
3. Recompute and inspect all existing signed-review history events, exact
   immutable event bytes, monotonic sequence, Ed25519 keyholder signatures
   using independently supplied, distinct trusted *public* keys, owner-only
   revocations, and valid expiry. Never load private signing keys.
4. Run existing Stage 13↔15 historical SHA chain audit. Record its genuine
   `NO_GO` state. Never elevate the aggregate local digest match to independent
   candidate-specific regression proof.
5. Join current assessment cards against **public URL + exact pinned SHA +
   evidence SHA256** in signed local review history. State machine:
   - No review record → `NO_SIGNED_REVIEW_HISTORY_NO_GO`.
   - Owner revocation → `OWNER_REVOKED_BLOCKED_NO_GO`, including if the
     current selected revision has changed.
   - Old pinned SHA or evidence fingerprint → `REVIEW_FOR_OLDER_PINNED_EVIDENCE_NO_GO`.
   - Expired signed claim → `SIGNED_CLAIMS_EXPIRED_NO_GO`.
   - Valid keyholder-signed, still-current **claim** →
     `KEYHOLDER_SIGNED_CLAIMS_AWAIT_INDEPENDENT_QA_NO_GO`.
6. Every output remains read-only, revocation-aware, and **NO_GO**. Current
   data absence from a bounded batch does not mean deletion or revoked
   status. Repeat unchanged claims do not create a new automatic review alert.

## Critical trust boundary

This links and cryptographically checks **who signed a statement**; it
does not verify that the review actually happened, that the signer is
independent in the human/organizational sense, that the upstream release
contains the purported fix, or that a regression is actually resolved.

The existing signed history ledger notes that a valid local chain does
not prevent entire SQLite-file rollback without a separately retained,
independently authenticated head. Even a supplied matching head is
reported only as `caller_supplied_head_checkpoint_matched=true`, **never**
as proof that such an independent external anchor was established.

No production GO, skill delivery, test execution, Rulepack signing,
automatic learning, or rule promotion is permitted by this function.
Its actual independent QA test count and approved rule count are always 0.

## Regression acceptance

`tests/test_ucie_public_library_review_binding.py` covers:

- Empty ledger: no DB created, all current references pending.
- Synthetic distinct-owner/QA Ed25519 signing plus exact revision join;
  still NO_GO and DB bytes unchanged after read-only inspection.
- Owner revocation: remains blocked, no resurrection via this path.
- Changed pinned merge revision OR evidence fingerprint: stale review is
  not copied to a new candidate.
- Expired claim cannot become QA PASS.
- Missing/incorrect history checkpoint and wrong trusted key fail closed.
- Bounded nonselection never implies deletion.
- Forged batch approval and different project root fail closed.

All signature keys used in tests are freshly generated, ephemeral and
synthetic. No real signing decisions, live verified releases or human QA
are claimed. Windows/Linux Python 3.13/3.15 offline CI success is
**source QA only**, not a locally deployed runtime acceptance.

## Remaining closed-loop development

The following remain separate, explicitly authorized development stages:

1. Acquire approved-source, version/commit-precise evidence and reproduce
   tests in a disposable isolated runner, including negative/security
   cases, without executing untrusted patches on the owner's host.
2. Bind independently confirmed version, license, security and regression
   proof to the exact candidate revision, using independently authenticated
   evidence and reviewer identities rather than just keyholder claims.
3. Ensure review-signed evidence and revocations are checked against
   an externally retained append-only head and a separately approved
   human owner release decision.
4. Only after those gates might separately approved rules be proposed;
   **automatic promotion, export, installation and cross-project access
   remain disabled** until independent owner authorization.

Do not relaunch the UCIE tunnel, migrate the owner PC runtime or update
the operating DB as part of this PR. Keep PR #77 Draft.
