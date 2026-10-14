# UCIE Stage 6-8 — Isolated regression evidence intake V1 (draft)

## Problem and boundary

UCIE now has eight pinned public error-pattern families, exact merged-PR
identities and *proposed* negative/regression checks. No upstream reproducer
has been independently executed. A synthetic test that a receipt validator
accepts **does not** establish that an upstream bug was reproduced.

This stage adds an **offline, pure-data** validator for a future,
**separately authorized** independent runner's before/after regression
evidence. The validator never executes a command, downloads upstream
code, contacts a private account, writes to the Knowledge database,
signs a Rulepack, installs a scheduler or claims a PASS.

## Untrusted claim format

A claim must contain exactly the following fields:

- `schema = UCIE_EXTERNAL_REGRESSION_CLAIM_V1`
- `case_id`, `source`, `rule_code`, `evidence_fingerprint`
- `merge_commit_sha`, `runtime_product`, `runtime_version`, `platform`
- `fixture_sha256` — digest of a separately maintained reproducible fixture
- `pre_fix` — `revision_sha`, `observation_sha256` and
  `result = FAILURE_OBSERVED_CLAIM`
- `post_fix` — `revision_sha`, `observation_sha256` and
  `result = SUCCESS_OBSERVED_CLAIM`
- `recorded_utc` — UTC ISO timestamp, no future claim
- `independent_attestation = null` — **any self-asserted approval is rejected**

The pre/post revision SHA values must be different; the post revision must
match the *exact* canonical merge commit pinned by the publicly inspected
PR snapshot. Each claim must refer to one Stage 6 case, and duplicates
are rejected. The fixture, environment/runtime, source and case digest
must agree. This is strict **structural** checking of untrusted text, not
evidence authenticity or a binary release inclusion proof.

Only the previously approved CPython and PowerShell Stage 4 sources
are recognized by the current adapter. A claim cannot introduce another
repository, arbitrary executable command, raw log, script, URL, signature
or a new Rulepack rule.

## API and integration

`inspect_regression_claims(regression_plan, pinned_snapshot,
external_claims=None)` returns:

- `AWAITING_EXTERNAL_CLAIMS` with zero independent verifications when no
  claims are supplied;
- `UNTRUSTED_CLAIMS_PRESENT` when claimed before/after fields are
  structurally consistent (still no independent verification);
- fail-closed exception on contradictory, stale, modified or forged
  metadata.

`build_readonly_acceptance_preview` optionally accepts
`external_regression_claims` in memory and includes the claim count,
missing cases and digest in the existing Stage 8 `NO_GO` result. The
ordinary CLI does **not** accept arbitrary external files, command lines,
test scripts, internet URLs or direct production-execution requests.

SHA-256 is only an integrity fingerprint, **not a digital signature**.
An independent reviewer must later verify runner ownership, environment,
test logs by hash, pre-fix failure, post-fix success, exact version
applicability, isolation and provenance through a separately authorized
process. This stage cannot produce that approval.

## Negative tests

Offline tests deliberately reject forged `PASS`, altered merge SHA,
altered family fingerprint, mismatching post revision, identical before
and after revision, unauthorized source, unsupported platform, injected
command fields, future timestamps, duplicate case and claimed self
attestation. Integration tests cover the full Stage 4-8 candidate-only
bundle and preserve `NO_GO` even for a structurally valid claim.

The code is eligible for CI against Python 3.13/3.15 on Windows/Ubuntu
using *synthetic data only*. **CI PASS is not upstream error-reproduction
PASS or owner-PC acceptance.**

All Draft stages remain unmerged, and no permanent DB import, new OS
scheduler registration, package release, signing or auto-promotion is
authorized by this change.
