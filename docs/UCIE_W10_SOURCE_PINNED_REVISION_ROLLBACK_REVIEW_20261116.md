# UCIE W10 - source-pinned revision / rollback readiness
Date: 2026-11-16 KST
Project: UCIE ONLY
Status: W10_SOURCE_PINNED_REVIEW_LOCAL10PASS__CUSTOMER_RELEASE_NO_GO

## Canonical roadmap

W03-W06 metadata Library, W07/W08 first-party QA, and W09 independent
first-party DRAFT consumer and existing signed manual-reference verifier
are already in main. W10 must not convert them into owner approval or
a real change/restore operation.

The owner Windows W09 read-only receipt was:
schema UCIE_W09_INDEPENDENT_CONSUMER_ACCEPTANCE_READONLY_V01
status W09_NO_EXISTING_SIGNED_RULE_SELECTION_RELEASE_NO_GO
review_digest f08c05ed2dbbdd6cb0e578c4f69f72bf0bbe2ce69022713409758c9da91e903a

No existing owner-signed original serial4/serial5 pack and public trust
was supplied for a genuine owner manual rule selection. That boundary
remains blocked. Full GitHub CI has only proved the UCIE-authored
synthetic genuine cryptographic fixture roundtrip, not actual owner
package release.

## Existing first-party functions REUSED (no duplicate machinery)

- product_v1.integrated_product_preview and its original P8/W05
  hash-chain-backed _revision_review_queue.
- w09_consumer_acceptance_v01.inspect_w09_consumer_acceptance;
  W07/W08 9-case exact-key heldout reference verification and first-party
  standalone DRAFT ZIP QA in isolated Python processes.
- library_exact_index.py and capability_trials.py are the ONLY UCIE
  first-party source targets authorized by original revision queue.
- Separate existing skillbook_revision_review_v01 authoring worksheet
  is not mistaken for a rollback implementation.

## New capability

Source: src/ucie_miner/w10_revision_rollback_review_v01.py

- Enforces original W09 allowed owner root (D:/UCIE or explicitly marked
  disposable TEMP/UCIE test directory), source identity and side-effects.
- Exact source-linked original P9 review records are regenerated fresh;
  validates SHA computed from prior event ID / target / decision and
  original hold state/action. Rejects false QA, production adoption,
  unknown targets, injected selections or modified review digest.
- First-party source SHA computed from exact current UCIE-owned code
  filename only. No outside projects, private files or unapproved source.
  A present-file SHA is NOT a verified prechange restore snapshot.
- Selection is optional: only exact visible 64-char proposal SHA IDs
  are accepted. Optional expected W09 review digest checks owner receipt
  correspondence; stale receipt fails closed.
- Outputs current code snapshot hash, current independent W08 reference
  mismatch count, proposal review identity, bounded unsigned review
  digest, and incomplete rollback preconditions.
- This module cannot execute new source code, restore files, write
  package bytes, alter Git, sign owner rulepacks, change scheduler/DB,
  network GET, auto promote, release or rearm P11.
- Even an unmodified exact-key comparison on current code is NOT a
  proposed revision regression test. No candidate code or archived
  restore bytes exist in this W10 slice, so actual rollback remains
  FALSE (not merely unconfirmed success).

## Owner Windows execution and QA

Fresh test file: tests/test_ucie_w10_revision_rollback_review_v01.py
Result: 10/10 PASS on UCIE owner Windows. Initially input helper
passed repeated keyword arguments in one negative test; corrected
the TEST helper and reran all ten successfully.

Actual read-only D:/UCIE results:
- 2 source-linked revision proposals in the current P9 view.
- Both target ucie_miner.library_exact_index:EXACT_QUERY_POLICY.
- Both are MORE_UCIE_TESTING_REQUIRED_NOT_APPLIED.
- Proposal SHA prefixes 3949f478d3df and 95f1eee2e457.
- Current source file SHA-256: library_exact_index.py
  6e27de83192b066f73b9574d2a591607bcc1bef9512b97f94c5bdd3af528ee7e
- W09 review digest prefix f08c05ed2dbb MATCHES owner provided SHA.
- W08 current first-party heldout cases 9, mismatch count 0.
- P8 source-linked public review metadata 1,335 rows.
- GET=0; operating DB writes=0; git mutations=0; rollout/rollback=0.
- No new source, release, owner signing, consumer adoption or permission.
- Local tests are not independent GitHub CI; CI on new PR required.

Synthetic tests cover original P8 and W05 experience review sources,
hash-chain proposal validation, wrong source target, fabricated
approval, forged W09 state, wrong pinned handoff digest, exact proposal
selection, reproducible review SHA and no operating file modification.

## Owner read-only usage

    cd D:\UCIE
    $env:PYTHONPATH='D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.w10_revision_rollback_review_v01 --ucie-root D:\UCIE --limit 10 --queries 32 --repeats 3 --expected-w09-review-digest f08c05ed2dbbdd6cb0e578c4f69f72bf0bbe2ce69022713409758c9da91e903a

If local evidence has changed since the owner W09 receipt, this
intentionally fails closed. The optional --select-proposal-id is only
for review; it never restores a file.

## Remaining gates

1. Named UCIE first-party proposed code, exact Git revision/SHA,
   independently stored and SHA-verified recoverable PRECHANGE bytes.
2. Independent security/regression/heldout test for candidate and
   separate disposable simulated restoration, no production write.
3. Legal license/version/source rights, independent human QA and
   explicit owner deploy-and-rollback authorization.
4. After any future authorized change, consumer-side W09 re-verification.
5. Customer V1 release NO_GO. PublicMiner 403 and P11 job6
   REVIEW_REQUIRED attempts5/5 are separately held; no GET.

STATUS=W10_REVIEW_SOURCE_AND_OWNER10PASS__REVISION_QUEUE_TWO_HOLD__
REAL_ROLLBACK_NOT_EXERCISED__AUTO_PROMOTION_OFF__
P11_NETWORK_HOLD__V1_RELEASE_NO_GO.
