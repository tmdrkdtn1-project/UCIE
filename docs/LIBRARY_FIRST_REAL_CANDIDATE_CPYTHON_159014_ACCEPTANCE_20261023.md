# UCIE first real approved-source candidate: CPython #159014 — evidence checkpoint

## Scope and result

**Date of observation:** 2026-10-23 UTC (same day as the CI run).
**Status:** `PUBLIC_DOCUMENTATION_AND_CPYTHON_RUNTIME_OBSERVED_NO_GO`.
**Acceptance claim:** One UCIE-owned disposable CI test actually fetched two
approved public GitHub metadata endpoints, compared one fixed CPython PR
revision and its *documentation-only* patch, and executed three **inert
CPython 3.15.1 option probes** independently of the owner's Windows host
on both Ubuntu and Windows.

This is a **real one-candidate observation**, not a test of untrusted
external source code, source binaries before/after the fix, independent human
QA, legal license clearance, release-inclusion evidence, or a rule approval.

## Source and pinned identity

- Approved public source: `python/cpython` only.
- Official PR: https://github.com/python/cpython/pull/159014
- Merged at: `2026-10-14T13:18:20Z`
- Merge SHA: `91248026c8a41910098032dd23f9a05ad2d9b513`
- Exactly two official documentation paths:
  - `Doc/howto/remote_debugging.rst`, bounded GitHub diff SHA256
    `a6f144702f500115340e81d795c9b7f566101bb790f413621a09a9607477cfdd`
  - `Doc/using/cmdline.rst`, bounded GitHub diff SHA256
    `9f25cab54dafda20e19d89682e0268c1fd4ee5146e8f1b39ad9284e2318c6a61`
- Reviewed documentation correction:
  `-X disable_remote_debug` (invalid/ineffective spelling)
  → `-X disable-remote-debug` (effective runtime spelling).

The diff hashes are inspection fingerprints for two untrusted public
GitHub API `patch` strings, **not** proof of legal provenance or a signed
upstream source archive. PR metadata, exact file listing and text were
compared against fixed first-party bounds without retaining or executing
upstream patch content.

## Actual disposable runner observation

- [UCIE GitHub Actions run #39934496986](https://github.com/tmdrkdtn1-project/UCIE/actions/runs/39934496986)
  completed **SUCCESS 4/4** at reviewed branch SHA
  `1ca330280cc785c60c32a265438bc9f2278ae7a7`.
  Matrix: Ubuntu/Windows × CPython 3.13/3.15.
- The *special case-specific live step* runs only on PR #77 and CPython
  3.15, once per 3.15 job; the Python 3.13 jobs correctly skip it.
- Ubuntu CPython **3.15.1** job `120350594392`: special step SUCCESS.
  Canonical bounded observed receipt SHA256:
  `dde53a6039262717059aa9eef7d9d179d931c47f7bd87dc73961699f09ccc03d`.
- Windows CPython **3.15.1** job `120350594344`: special step SUCCESS.
  Canonical bounded observed receipt SHA256:
  `93f53ef9d92b72e2114095401ed563d5d4395ac15c14549cc2043c06dc8197ad`.
- Both run logs contain a single scoped
  `UCIE_CPYTHON_159014_REAL_OBSERVATION=` JSON record with:
  `baseline_remote_debug_enabled=true`,
  `old_documented_option_still_enabled=true`,
  `corrected_documented_option_disabled_remote_debug=true`,
  `public_api_gets=2`,
  `test_transport_injected=false`,
  `untrusted_patch_executed=false`,
  `production_approved=false`,
  `automatic_rule_promotions=0`.
- The two platform-specific receipt SHA256 values intentionally differ
  because each report binds the observed runner platform. The **two official
  document diff hashes and pinned source commit match across platforms**.

The authenticated GitHub CI job and log records were read back after the
run. The receipt SHA256 is a normal canonical-data checksum, **not a
cryptographic signature**, independent QA attestation, or anti-rollback
checkpoint.

## How the implementation is bounded

- `src/ucie_miner/public_case_cpython_159014.py`: strict fixed PR URL and
  merge SHA, no redirect, exactly two approved GitHub metadata endpoints,
  exact two RST document paths and patch option spelling; accepts only the
  hard-coded typed CPython 3.15 behavior invariant. No external patch is run.
- `tests/test_ucie_public_case_cpython_159014.py`: synthetic negative
  regression tests (forged repo/commit, incorrect document paths/patch,
  abnormal API/low quota, incorrect runtime and negative case).
- `tests/runtime_public_cpython_159014_live.py`: strict UCIE Actions /
  pull-request branch / 3.15 runner gate, imports the existing first-party
  isolated subprocess option observer and prints a bounded receipt.
- `.github/workflows/stage1-offline-tests.yml`: only activates this special
  live step for PR #77 on the approved development branch when the matrix
  version is 3.15. It does **not** register a scheduler or create a service.

No new private store, C40 tunnel modification, operating DB rewrite,
release-signing key, auto-rule promotion, user-file inspection, or external
project access occurred in this acceptance.

## Independent QA and release gates still missing

These MUST be distinct and explicitly checked before any UCIE rule GO:

1. Actual older affected/fixed revision **source binary** comparison was
   **not performed**. The PR corrects two documentation files; the current
   CPython runtime behavior observation does not prove historical releases.
2. Official per-version release inclusion and applicability beyond the
   observed runner CPython 3.15.1 runtime are **not established**.
3. No independent legal license assessment or human security review
   has been authenticated; normal CI cannot silently substitute for these.
4. No independent reviewer identity or signed owner authorization was
   received. There is no genuine signed candidate QA packet currently
   ingested into the Library history.
5. No production Rulepack, automatic learning/signed rules, tool install,
   change to live miner, or dispatch to any other project.

**Final gate:** `ONE_CANDIDATE_OFFICIAL_DOCS_AND_REAL_RUNTIME_OBSERVED`,
`UNVERIFIED_INDEPENDENT_QA_NO_GO`, `AUTO_PROMOTION_OFF`. All actual
QA/approval domains not specifically established by this document remain
pending. Do not broaden the five approved upstream sources.
