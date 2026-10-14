# UCIE Stage 5–7 — Static calibration and independent-review docket (V1)

This development extends Draft PR #18 and remains **candidate-only**.

## Stage 5: synthetic precision/recall, not real-world performance

`ucie_miner.static_accuracy.measure_python_synthetic_cases` parses a bounded
UCIE-authored set of inert Python source strings (never executes imports,
statements or external patches). It calculates confusion counts and
precision/recall in parts per million. Each receipt identifies a fixture
by ID and SHA-256 only; it does not reproduce or store source text.

The initial fixture set intentionally includes one **known false
negative** (aliased `os.scandir` call not resolved by a lexical scanner)
and one **known false positive** (unreachable branch containing raw
iterator dispatch). These limitations must stay visible rather than being
excluded to claim perfect precision. Labels are **UCIE-authored synthetic**
controls, not independently reviewed ground truth or representative
real-world usage.

The Windows PowerShell CI includes analogous inert `Parser.ParseInput`
fixtures. Its known false negative is a `gcm` alias; its known false
positive is a command in a literal unreachable branch. In both cases,
calibration results are descriptive only: **no production-quality pass
threshold, no approval and no learning/promotion from fixture scores**.

## Stage 7: prepare an agenda, not a signed Rulepack

`ucie_miner.review_docket.prepare_independent_review_docket` joins the
candidate-only Stage 5/6 static-to-regression preview with the Stage 6/8
**untrusted** independent-runner claim inspection receipt. It verifies
bounded schemas, self-consistent fingerprints, case IDs, and explicitly
unverified status fields, then prepares per-finding items containing:

- Pinned public PR identity and the related Stage 6 regression case ID
- The presence/absence and hash of a structurally valid external claim
- Required independent behavioral reproduction and reviewer verification
- Explicit `reviewer_identity_authenticated=false`,
  `regression_independently_verified=false`, and `ready_to_deploy=false`

A synthetic/fabricated before/after result is **not independent evidence**.
A SHA-256 docket fingerprint is a change detector, **not a signature**.
This module cannot accept a self-proclaimed independent reviewer approval
or decide whether a runtime patch fixes the original bug.

`preview-review-docket-stdin` accepts an explicitly provided,
bounded JSON object with keys `static_preview` and `external_review`.
It rejects duplicate JSON keys and emits only the unapproved review agenda.
It does not open a user source file, run a patch, query a private service,
write a database or invoke a scheduler.

The existing Stage 8 `build_readonly_acceptance_preview` optionally
accepts a static preview and displays its review docket SHA and candidate
count, while still returning **NO_GO** regardless of submitted claims.

## Existing verified work and remaining gates

Previous Draft PRs #4 through #18 retain their own proof of CI checks.
This change does not re-import the active Knowledge DB or re-run dangerous
raw `os.scandir` native crashes. All new fixtures are UCIE-authored and
ephemeral.

Still unverified: representative real-world detector accuracy, exact
pre/post upstream fix builds, affected binary version ranges, independent
runner and reviewer identities, file-level licenses/security, production
host acceptance and signing authorization.

**This branch: NO AUTO-PROMOTION / NO PERSISTENT DB / NO SCHEDULER CHANGE /
NO SIGNING / NO DEPLOYMENT / NO MAIN MERGE.**
