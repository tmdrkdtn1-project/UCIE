# UCIE 2026-11-15 — PublicMiner HTTP 403 fail-closed owner incident

Project boundary: only D:\UCIE, current first-party public-code miner,
GitHub's official public REST metadata from approved independent repos.
No other project data or credentials.

## Real owner Windows observation

The exact UCIE-only read-only receipt test observed:
- latest first-party runtime/last_run.json
- finished_utc = 2026-11-15T09:18:24+00:00
- status = COLLECTION_FAILED, consecutive_failures = 1
- error_http_status = 403
- error_public_source = python/cpython (approved independent public repo)
- error_public_operation = FETCH_PR_LIST
- operating DB modifications, public API GETs by audit, scheduler changes = 0

This is evidence of a NEW failure in the 10-minute base PublicMiner;
it is **not** evidence that P11's 2026-11-01 historical failure had
HTTP 403. No authoritative Retry-After or X-RateLimit-Reset header from
the original failed call was retained. Therefore we cannot distinguish
an exhausted quota from access denial, nor prove current remaining
shared unauthenticated API budget.

The existing Windows hourly-named task continues to be registered with
the exact 10-minute cadence. Task success and successful collection
MUST be reported as distinct facts.

## Source repair

- In first-party worker.run_cycle(enforce_schedule=True), examine the
  already-existing bounded local last_run.json *before any new collection*.
  If the prior cycle contains HTTP 403/429 or a sanitized Stage10/Stage13/
  Stage16 rate-limit condition, fail closed:
  * Unknown rate reset or bare historical 403/429 => return
    SKIPPED_PUBLIC_RATE_OWNER_REVIEW_NO_GET, public GET count 0,
    production_approved=false.
  * Known, valid Retry-After or exhausted primary reset deadline =>
    SKIPPED_PUBLIC_RATE_PAUSED_NO_GET before the appropriate deadline.
  * After an authoritative bounded deadline expires, normal prior
    scheduler backoff logic may evaluate the next cycle.
- On a NEW first-party HTTP 403/429 with a bounded explicit HTTPError
  cause chain, derive only sanctioned reason enum, not-before UTC and
  bounded strike count using the already-reviewed P11 rate parsing
  module. Append to the existing last_run.json receipt as first-party
  sanitized fields; never persist exception text, headers, PR titles,
  URL, patches, secrets or personal content.
- The same shared UCIE public_miner.lock is retained. No new Windows
  Scheduled Task or automatic promotion. Existing 10-minute task
  executes and returns an explicit safe-skip outcome without a GET.
- scripts/public_miner_cycle.py treats safe rate PAUSE/OWNER_REVIEW
  skips as benign exit 0 *without* labeling them collections.

## Owner Windows test evidence

- New test_ucie_public_miner_http_rate_hold_v01.py: 9/9 PASS,
  including simulated 403 without headers, 429 Retry-After, 403
  primary reset, historical 403 lacking rate evidence, unrelated 404,
  independent Stage10/Stage13 rate holds, and real owner last_run
  read-only 403 gate observation. No public API calls.
- Existing test_ucie_hourly_stage10_failure_reconciliation_v01.py:
  9/9 PASS.
- Existing test_ucie_hourly_public_study_loop.py: 11/11 PASS.
- Combined 27/27 on the source-local owner adapter, with only
  disposable synthetic GET failures and real owner read-only
  observation. No claim that actual upstream API availability is fixed.

## Connection with P11

Both P10 recovered non-network jobs remain independently finalized.
Remaining P11 PUBLIC_INCREMENTAL_MINING is REVIEW_REQUIRED 5/5,
historical last failure cause unavailable. P11 rate guard V03 on main
protects a future P11 403/429, but it cannot retroactively clear the
base PublicMiner's new 403 or prove a shared unauthenticated quota.
A separate one-source one-request P11 diagnostic must remain blocked
until this rate/authorization incident is explicitly reviewed. The
P10 non-network rearm helper must NEVER be used for P11.

Official GitHub REST policy evidence:
https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api

STATUS=PUBLIC_MINER_HTTP403_OWNER_REVIEW_NO_GET__LOCAL_SOURCE_TESTS_25_PASS__
P11_NETWORK_HOLD__NO_AUTO_PROMOTION__NO_PRODUCTION_APPROVAL.
