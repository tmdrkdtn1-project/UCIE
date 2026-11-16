# UCIE W10 v02 — pinned Git blob / disposable byte-restore probe

Date: 2026-11-16 KST
Scope: UCIE ONLY; first-party tests and approved UCIE GitHub source. NO OPERATING ROLLBACK.

## Provenance and inherited gates

- W10 v01 PR #296 was merged into main as `a8be4639ca38eb6ff03d3b90d2e6ad86a14abf20` after four successful Windows/Ubuntu Python 3.13/3.15 CI matrix jobs; this is source-reviewed functionality, not a release.
- Pin observed from the UCIE repository at W09 main commit `aeecc3fc64dc542daba6e40ef29dce66c296ebdf`: path `src/ucie_miner/library_exact_index.py`, Git blob `0f92ed46b68685e0edb98f4fc09c3846b5b8d2c6`, owner W10 source SHA-256 `6e27de83192b066f73b9574d2a591607bcc1bef9512b97f94c5bdd3af528ee7e`.
- Those pinned bytes are **currently unchanged first-party source**. They are not proven actual prechange backup bytes, a customer executable release, or a verified restore archive.

## New additive offline module

`src/ucie_miner/w10_disposable_restore_probe_v02.py` is a standalone helper; not wired into automatic product, scheduler, worker or P11 network flows.

- Requires explicit bounded prior, candidate, and current *bytes* with SHA-256 for each. Additionally recomputes the canonical Git blob SHA-1 for prior bytes using the Git blob header; rejects a mismatched caller-pinned Git object ID.
- Only two literal UCIE first-party filenames are accepted, matching W10 v01 source scope. No caller-supplied paths, URLs, shell commands, public network GET, source import/exec or Git checkout.
- Creates a fresh stdlib TEMP directory, stages inert candidate bytes, reads them back, overwrites the disposable file with prior bytes, verifies exact bytes and SHA/Git blob, then removes the directory.
- The optional claimed Git commit is syntax-checked only. The probe **never authenticates commit-to-tree-to-path membership or proves the bytes were a deployed prior version**. It does not attest a real owner backup, candidate regression, human QA, consumer W09 pass, owner release or operational rollback.
- Synthetic test bytes are UCIE-authored. The real pinned source byte test in a full repository checkout uses a fabricated inert appended comment as its *disposable* candidate; that is NOT a proposed first-party software revision.

## Tests and promotion boundary

- Local Python 3.13.5 standalone independent invocation: 14 tests PASS, one source-check test SKIP because the complete UCIE Git checkout is absent in the isolated development container. Do not count this skip as pass.
- The 15th test uses fixed **read-only Git object commands** (`git rev-parse HEAD:src/ucie_miner/library_exact_index.py` and `git cat-file blob <pinned SHA-1>`), not Windows checkout bytes. This verifies the committed first-party tree/blob and canonical LF bytes against both pinned SHA-256 and Git blob SHA-1 before an inert disposable roundtrip. GitHub's separately retrieved historical W09 commit path is a distinct source observation; neither test proves a real owner-retained prechange backup. Require full Actions CI 4/4 PASS before merge.
- No operating SQLite, source file, Windows task, model weights, rule signature, P11 job6, source collection permissions, deployment or customer release may be changed by this branch.

## Remaining requirements (all NO-GO)

1. Independently bind original immutable Git commit + path + blob to a genuine PRECHANGE owner-retained restoration artifact (not merely current or unchanged historical code).
2. Select exactly one source-linked P9/W10 revision proposal, independently review a bounded candidate source and verify its license/version/security provenance.
3. Execute candidate-vs-prior regression and negative security suites in isolation, then independent restore-to-prior regression (not only byte identity).
4. Obtain independent human QA and explicit separate owner deployment/rollback authorizations.
5. If ever deployed under approval, reverify actual consumer W09 behavior and preserve fail-closed rollback controls.
6. Base PublicMiner HTTP403 and P11 job6 REVIEW_REQUIRED attempts5/5 remain separately held: no rearm or new public GET.

STATUS=W10_V02_DISPOSABLE_BLOB_BYTES_PROBE__LOCAL14PASS_ONE_FULL_REPO_SKIPPED__CI_REQUIRED__OWNER_ROLLBACK_NOT_PERFORMED__CUSTOMER_RELEASE_NO_GO
