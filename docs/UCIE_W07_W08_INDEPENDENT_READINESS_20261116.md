# UCIE 2026-11-16 - W07/W08 independent QA readiness (READ ONLY)

PROJECT: UCIE ONLY
SOURCES: only five approved independent public GitHub repositories and
official public references. No other user project files, private repos,
tokens, third-party executable instructions or model training.
STATUS=W07_W08_LOCAL_QA9PASS__NEW_RULE_APPROVAL_NO_GO__
P11_NETWORK_HOLD__CUSTOMER_V1_RELEASE_NO_GO

## Canonical roadmap and existing modules reused

This new slice does not create a duplicate Rulepack signer or new
benchmark logic. It reuses:
- W07 signed_rule_library.inspect_signed_library: the original genuine
  Serial4/5 owner signature/public trust/expiry/scope and parent-hash
  verifier, manual signed reference only.
- W08/P8 capability_evidence_trial_board_v01.evaluation_board: actual
  first-party UCIE read-only exact-key index benchmark over the existing
  independently source-linked W04 Stage10/12/15 metadata catalog.
- W08 capability_evaluator.build_exact_index/indexed_search: UCIE
  first-party pure functions checked against a NEW independent
  hand-specified nine-case oracle, covering duplicate composite keys,
  positive matches, three missing-result cases and a source mismatch.

An owner-risk cryptographic signature is NOT independent human QA,
license verification, vulnerability remediation, version fitness or a
customer release permit. W05 upstream PR title cues remain unverified.

## New functionality

Source: src/ucie_miner/w07_w08_independent_readiness_v01.py

The owner runs a bounded READ-ONLY QA readiness board. The first-party
source-linked benchmark must be internally consistent: baseline
operations = row count * query count, indexed operations = rows+queries
(including build), and reduction = baseline-indexed; mismatch count 0.
The result does not certify wall-clock speed or external engines.

If the owner provides existing Serial4 signed ZIP and the owner PUBLIC
trust PEM, the new board calls the ACTUAL original W07 cryptographic
verifier, then cross-checks rule IDs/order, item SHA binding to the
original pack, pack serial and optional Serial5 parent SHA. It accepts
only pre-existing manual scope (no new export, no unattended execution).
The private signing key is never requested or accessed. With absent
pack/trust paths, status is EXACT_SIGNED_PACKS_NOT_SUPPLIED_NO_GO; this
is NOT a crypto PASS.

The board never accepts arbitrary external or caller-provided PASS
JSON as an approval token; all evidence is regenerated from the
first-party modules. An unsigned review digest only tracks an exact
observation and does NOT grant source trust or release rights.

Even if both W07 genuine signature and W08 exact-key checks pass,
the STATUS stays W07_W08_READ_ONLY_QA_REVIEW_REQUIRED_NO_GO, since
independent human QA, rule-specific negative security/regression,
source license/version signoff, explicit owner release authorization,
and production consumer/host verification remain separate NO-GO gates.
There is no --approve, --sign, --deploy, --train or --export action.

## Actual owner Windows test

New tests/test_ucie_w07_w08_independent_readiness_v01.py: 9/9 PASS.
First attempt failed because a historical test module was absent on
the owner machine. The new suite was made independent of that module,
rerun 9/9 PASS, and the failure was not mislabeled as an earlier PASS.

A synthetic mocked verifier result is used ONLY to test contract
boundaries; it is not a real signature verification. A forged Serial4
file fails the actual original verifier. Actual positive synthetic
cryptography is separately tested in original GitHub CI
tests/test_ucie_w07_w09_signed_library.py and requires CI confirmation.

Actual owner D:/UCIE read-only observed:
- heldout hand-specified cases: 9, misses 3, result mismatch 0;
- linked public review metadata rows: 1,335;
- exact-key linear scan operation count: 42,720;
- index build plus lookup operation count: 1,367;
- operation reduction: 41,353;
- exact result mismatch count: 0;
- supplied signed owner package: NO;
- new signed packages, independent human QA approvals, license signoffs,
  network calls, operating DB writes, release authorizations: ZERO.

These numbers do NOT prove any upstream engine/skill benefit or full
W04 substring-search performance. No automatic rule/skill/model promotion.

## Owner READ-ONLY command

PowerShell in D:/UCIE:

    cd D:\UCIE
    $env:PYTHONPATH='D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.w07_w08_independent_readiness_v01 --ucie-root D:\UCIE --queries 32 --repeats 3

Existing genuine signed packs can optionally be checked using
--serial4-pack PATH and --owner-public-trust PATH; --serial5-pack PATH
adds original fifth addendum verification. Never fabricate source paths.

## Remaining roadmap

W07 requires independently verified candidate source SHA, license and
specific-regression/security quality signoff. W08 requires exact
held-out/representative measurements and human QA before approving
production indexing. W09/W10 package, rollback, update and customer
readiness are separate. P11 PUBLIC_INCREMENTAL_MINING job6 remains
REVIEW_REQUIRED 5/5; current base PublicMiner HTTP403 unresolved.

STATUS=FIRST_PARTY_READONLY_QA_IMPLEMENTED_LOCAL_9PASS__
SIGNED_PACKS_MISSING__HUMAN_QA_AND_LICENSE_SIGNOFF_FALSE__
P11_GET_HOLD__AUTO_PROMOTION_OFF__RELEASE_NO_GO.
