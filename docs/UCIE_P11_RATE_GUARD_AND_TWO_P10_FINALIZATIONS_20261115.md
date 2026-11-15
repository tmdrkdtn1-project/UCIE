# UCIE P11 public GET rate guard V03 — 2026-11-15

Project: UCIE only. Source scope: approved official GitHub REST API docs
and exactly five existing independently owned public source repositories:
python/cpython, PowerShell/PowerShell, git/git,
modelcontextprotocol/python-sdk, actions/runner-images.

## Owner operating evidence (independently read-only)

An exact Windows UCIE-only SQLite preflight reported:

- P10 PUBLIC_METADATA_REVIEW: owner receipt COMPLETED and separately
  evidenced successful job completion after its exact delayed due time.
- P10 UCIE_REPORT_PREPARATION: owner receipt COMPLETED and independently
  evidenced job success.
- P10 queue: SUCCEEDED 6, REVIEW_REQUIRED 1, PENDING 0, RUNNING 0.
- No active owner rearm operation.
- Only remaining held kind: PUBLIC_INCREMENTAL_MINING, held at
  attempts 5/5 with sanitized RETRYABLE_ERROR.
- P11 isolated opted-in ledger: 450 successful past public GETs,
  91 unverified public leads, 0 approved rules/production improvements.
  Its historical last public attempt failed; there was no historical
  raw HTTP status or authoritative rate reset stored.
  Status MUST remain HISTORICAL_CAUSE_NOT_RECORDED.
- The preflight itself made no GET, worker launch, DB/task change or model
  training and does not authorize a P11 owner rearm.

## Official GitHub API policy

GitHub documents that rate-limit failures can be 403 or 429. Observe
Retry-After before retry, and an exhausted x-ratelimit-remaining=0 must
wait for x-ratelimit-reset. When both server deadlines exist, respect
the later one. When secondary rate-limit information is ambiguous,
pause and exponentially back off rather than blindly retrying.

Official references:
- https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
- https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api

This patch does not query /rate_limit (not an existing UCIE-approved
public repository metadata route) or broaden allowed URLs.

## Exact implementation

New first-party p11_rate_guard_v03 module:
- Traverses only bounded EXPLICIT exception causes to find an actual
  urllib.error.HTTPError with 403 or 429. Strings containing 403/429
  without an HTTPError do not qualify.
- Parses only restricted Retry-After seconds and x-ratelimit-remaining,
  x-ratelimit-reset headers, without retaining headers or URLs.
- Persists a SINGLE bounded rate guard row in the existing opt-in
  P11 SQLite file: approved source index, attempt UTC, a closed reason
  enum, UTC not-before or mandatory owner review, and capped strike count.
  This is in the same transaction as the already-existing sanitized
  public failure category receipt.
- 403 with no authoritative rate deadline or invalid rate header:
  permanent owner-review hold without automatic GET.
- 429 with no rate hint: 1h, 2h, 4h... capped 24h quiet intervals.
- Valid Retry-After and/or primary reset: no GET before the later deadline,
  plus a conservative 60-second buffer.
- Rate guard is checked before P11 reserves an attempt or touches the
  network. During a hold, collect_one returns
  P11_UPSTREAM_RATE_PAUSED_NO_GET with public_api_gets_this_call=0,
  source cursor unchanged; P10 treats that first-party local guard check
  as a successful check, NOT a successful public GET. Only the P11
  separate total_successful_public_gets counts real successful GETs.
- P11 status reports rate_guard_active, rate_guard_reason,
  rate_guard_not_before_utc, rate_guard_owner_review_required and an
  effective next GET timestamp; indefinite owner hold returns no due time.
- A truly successful bounded, allowlisted GET clears the guard inside
  the same transaction as deduping and rotating the source index.
- No external code, raw PR titles, prompts, credentials, response body or
  untrusted instructions are ever executed or persisted.

## Verified local isolated QA

All source tests invoked through the UCIE-only Windows bridge as
independent one-file unittests:
- test_ucie_p11_rate_guard_v03.py: 9/9 PASS (429 retry, 403 primary
  reset, combined later deadline, bad header owner hold, exponential
  fallback, no GET while held, simulated success and privacy).
- test_ucie_p11_public_failure_classification_v02.py: 6/6 PASS.
- test_ucie_p11_closed_loop.py: 13/13 PASS.
- test_ucie_runtime_pipeline.py: 12/12 PASS.
- test_ucie_p10_two_owner_finalized_p11_gate_readonly_v06.py: 2/2 PASS.
Total = 42/42.

No live P11 GET or rearm was executed. No scheduler changed.
All P11 new write tests use disposable synthetic UCIE roots only.
Any GitHub CI result must be independently checked; local 42/42 is
NOT a production validation of network availability or quota.

## Next unblocking gate

Before a live P11 one-GET retry, independently review (1) owner's exact
approved UCIE minute task identity; (2) exact held queue job 6 identity,
(3) last opted-in P11 source/cursor/cooldown and code guard, (4) other
UCIE miners' shared GitHub API request budget, and (5) explicit bounded
operator-only one-shot trial with evidence and rollback. Existing
P10 non-network owner-rearm helper explicitly DENIES this network kind.
Do not apply it to job 6 or retry a historical unknown-403 cause blindly.

STATUS=P10_TWO_FINALIZED_PASS__P11_RATE_GUARD_V03_LOCAL_TEST_42_PASS__
P11_NETWORK_REARM_NO_GO__PUBLIC_CANDIDATES_UNVERIFIED__
AUTO_PROMOTION_AND_CUSTOMER_RELEASE_OFF.
