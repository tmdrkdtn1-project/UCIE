# UCIE 2026-11-16 — W05 candidate vs P8 first-party measured work

Project: UCIE only; approved public independent repo metadata only.
No connected account, private repo, other project, runtime secret or
external executable was read, copied, queried or trained.

## Why this matters in the V1 roadmap

W05 can collect hypotheses for DEVELOPMENT_ENGINE, REUSABLE_SKILL and
LEARNING_LOGIC from bounded merged PR metadata on the five approved
public source repositories. These are title-cue hints, NOT an actual
working/benchmark-proven upstream engine or reusable skill.

W08 / existing P8 first-party benchmark can safely compare two
UCIE-authored exact-key search algorithms over the *already linked,
unverified* W04 public review metadata. It measures first-party
operations and exact-result equivalence, NOT any upstream PR candidate.

New src/ucie_miner/capability_evidence_trial_board_v01.py integrates
these two **separate** evidence strata in one owner-review summary:
- Optional W05 offline in-memory, at-most-20 approved-source public
  PR metadata snapshots only; reuses the current W03 source adapter
  source/URL gate and existing positive cue classifier, never GET.
  Retains only source-bound IDs, public URLs, commit SHA and
  bounded fingerprints (never PR titles, patch, code, raw text).
  Each candidate has false benefit_measured, license_verified,
  ready_for_adoption and promotion.
- Existing P8 read-only benchmark_linked_public_catalog is reused on
  the exact Stage10/12/15 source linkage (not reimplemented). The
  baseline linear scan and indexed lookup are actually executed on
  first-party UCIE metadata, with deterministic same queries and
  an exact-answer mismatch count. Index build cost is included.
- The summary makes its own operational limits explicit:
  exact source/domain/kind/purpose key lookup only; not whole W04
  substring/Unicode search; not a guaranteed faster wall time;
  not a benchmark of external engines/skills or external source code.
- For a real candidate to be eligible for technical evaluation, require
  exact revision/source SHA, license rights, reviewed local candidate
  implementation, same-workload baseline and candidate QA, negative
  security/regression checks, and independent QA plus owner approval.
  No such external candidate has been demonstrated or approved here.
- All outputs are read-only; no new external routes, task registration,
  production index, rules, model weights, W05 promotion or export.

## Actual Windows owner test (D:/UCIE)

New tests/test_ucie_w05_first_party_evidence_board_v01.py:
**7/7 PASS** including synthetic Stage10/12 linked metadata, offline W05
three signal kinds, wrong source/forged URL/duplicate PR/invalid bounds
negative tests, P8 forged scope fail-closed, and **real owner D:/UCIE
read-only benchmark**.

Actual owner bench with queries=32 repeats=3:
- Real source-linked public review metadata rows = **1,335**.
- Baseline exact-key linear scan = **42,720** estimated elementary
  comparisons (1,335 * 32).
- UCIE proposed index build + exact lookup = **1,367** operations
  (1,335 + 32).
- Reduction in algorithmic operation count = **41,353**.
- Exact-query answer mismatches across repeat workload = **0**.
- Public GET=0, operating DB writes=0, production index applied=false,
  upstream candidate effect measured=false, source code executed=false,
  model training=false, auto promotion=false.

This is NOT a 96.8% proven real-world speedup or validated external
skill improvement. The W04 795 grouped search matches from earlier
queries are a different grain than the 1,335 ungrouped metadata rows
used by this exact-key algorithm benchmark; do not aggregate or
conflate those numbers.

## Owner read-only operator mode

    cd D:\UCIE
    $env:PYTHONPATH='D:\UCIE\src'
    .\.venv\Scripts\python.exe -B -m ucie_miner.capability_evidence_trial_board_v01 --queries 32 --repeats 3

Current P11 network job6 remains REVIEW_REQUIRED. Base PublicMiner
HTTP403 remains unresolved; none of this implementation attempts
another GitHub GET or rearm, and it must not alter Windows tasks.

## Next W05 validation work (not claimed complete)

1. Pin real candidate source/merge SHA and confirm bounded metadata
   provenance in its exact approved source repository.
2. Verify version applicability, license and reproduction rights
   separately. Never execute a fetched third-party PR automatically.
3. Build UCIE-owned isolation-first candidate test harness and held-out
   baseline with regression and security tests.
4. Measure candidate functional correctness on the SAME workload and
   repeated samples; separate operations from wall-time claims.
5. Independent QA, human approval, signed controlled package/export
   only after W07-W10 gates.

STATUS=W05_LOCAL_FIRST_PARTY_INDEX_BENCHMARK_7PASS__
REAL_UCIE_METADATA_ROWS1335__EXACT_KEY_MISMATCH0__
UPSTREAM_ENGINE_SKILL_BENEFIT_NOT_MEASURED__
NO_NETWORK_GET_NO_AUTO_PROMOTION_NO_CUSTOMER_RELEASE.
