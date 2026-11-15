# UCIE P11 — owner one public GET diagnostic, V01 (2026-11-15)

Project boundary: D:\UCIE only. This is an isolated source-and-synthetic
trial design, NOT a running P11 collection job. No private GitHub user
data, credentials, non-allowlisted repos, models, rule promotion or
other projects are accessed.

## Why P11 remains held

Current owner public_miner last_run.json on 2026-11-15T09:18:24Z
showed COLLECTION_FAILED, HTTP403, consecutive_failures=1,
approved public repo python/cpython, FETCH_PR_LIST. The original
failed request did not retain authoritative rate remaining/reset headers.
An HTTP403 may be exhausted primary/secondary rate capacity or permission
denial. Do not assume an exact reset time. P11's older failure cause
remains HISTORICAL_CAUSE_NOT_RECORDED.

The existing UCIE base PublicMiner (10-minute scheduler) shares local
unauthenticated GitHub REST API exposure with P11. P11 owner preview
must fail closed on the current PublicMiner HTTP403 and may not
repeatedly query or clear this condition automatically. The safe
owner exception is an explicitly approved, one-off diagnostic at a
later point once the base miner is independently healthy.

## First-party implementation (separate from P10 rearm)

- New module src/ucie_miner/p11_owner_one_get_trial_v01.py.
- Fixed public metadata source: repo:python/cpython only, same
  exact URL produced by the existing allowlisted public_feed_url.
  No additional pages, repos, endpoints, arbitrary user URL or
  authentication headers are admitted.
- P11 P10-queue row id 6 must be exact REVIEW_REQUIRED 5/5 with
  original dedupe, no lease, no running P10 workers, and zero ACTIVE
  owner P10 rearm receipts; P11 opt-in/cursor must be source index 0,
  last attempt failed, 5-minute cooldown expired and rate guard idle.
  Other non-network P10 kinds are not rearmed.
- Live execution requires exact D:\UCIE checkout + Windows owner/task
  SID/action/Interactive/Limited/PT1M/IgnoreNew event attestation
  from the reviewed P10 owner module. Synthetic tests are constrained
  to marked disposable TemporaryDirectory/UCIE only.
- A recent healthy base PublicMiner last_run.json <=30min is required,
  without a recent 403/429, Stage10 partial/failure, Stage13 history
  rate pause, Stage16 rate pause, or consecutive failure.
  This is a health guard, NOT an authoritative shared quota count.
- The existing PublicMiner OS-held single-instance lock is acquired
  while performing the diagnostic so the two first-party UCIE miners
  cannot issue overlapping GETs; if the lock is already held, refuse.
- Prior to ANY GET, commit exactly one bounded first-party P11
  operation receipt with state PREPARED (single slot; replay and
  interruption fail closed). During the attempt, a first-party
  counter allows at most one call to the exact approved GitHub URL.
  A success seals the receipt SUCCESS, a 403/429/network/validation
  error seals FAILED with existing sanitized P11 failure enum, and
  a local guard skip seals NO_GET. No automatic retries or reset.
- With explicit owner approval, the P11 collector may update only
  its existing opt-in P11 metadata ledger, following the original
  hash-only candidate validation and V03 403/429 protection.
  It NEVER changes the P10 job 6 from REVIEW_REQUIRED. One success
  is a diagnostic, NOT approval to start its recurring worker.
- Only X-RateLimit-Remaining / X-RateLimit-Reset integers from the
  *same exact successful public GET* can be observed. No raw HTTP
  headers, URL, body, untrusted PR title or secret persisted in the
  one-shot receipt. The sample does NOT prove globally shared quota
  headroom for other applications or future attempts.
- Source CLI requires exact held-job SHA-256 and owner consent literal
  UCIE_OWNER_APPROVES_ONE_PUBLIC_GET_ACCEPTING_UNKNOWN_SHARED_QUOTA.
  The PowerShell wrapper requires BOTH -Approve and
  -AcceptUnknownSharedQuota. Neither runs automatically. Its default
  invocation is strictly read-only.

## Current safe owner preview

    cd D:\UCIE
    .\scripts\p11_owner_exact_one_get_trial_v01.ps1

During the observed HTTP403 the expected result is a fail-closed
UCIE_P11_OWNER_READONLY_PREFLIGHT_DENIED, public GETs=0.
Do NOT pass -Approve while that base PublicMiner 403 is unresolved.

The one-shot command form exists in source for separate future owner
review; it deliberately is not included here as a present operational
instruction. It must not be used as a workaround for GitHub 403.

## Verified source-local owner tests

- tests/test_ucie_p11_owner_one_get_trial_v01.py: 10/10 PASS.
  Disposable synthetic success, HTTP429 Retry-After, HTTP403 indefinite
  hold, replay denial, SHA drift, source cursor drift, overlapping
  first-party miner lock, stale or failed PublicMiner, same-GET
  numeric rate header observation, and real owner read-only preflight.
  Real preview was BLOCKED_NO_GO, GET count 0.
- tests/test_ucie_p11_owner_one_get_ps_wrapper_v01.py: 3/3 PASS.
  Static single-source and two-consent gate; real Windows PowerShell
  parser; actual owner DEFAULT preview fails closed on base HTTP403.
  No -Approve was issued. P11 queue unchanged.
- Source-local 13/13 PASS; independent cross-platform GitHub CI
  must be separately reviewed. No live GET, rule/skill auto promotion
  or scheduler modification occurred during tests.

Official GitHub REST references:
https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api

STATUS=P11_ONE_EXACT_GET_OWNER_DIAGNOSTIC_CODE_READY_SYNTH_ONLY__
BASE_PUBLIC_MINER_HTTP403_BLOCKED_NO_GO__P11_NETWORK_GET_NOT_RUN__
P10_JOB6_STILL_REVIEW_REQUIRED__AUTO_PROMOTION_OFF.
