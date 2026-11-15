# UCIE — one-shot public 403 owner diagnostic V01 (2026-11-15)

## Owner-observed incident and hard boundary

The existing UCIE base PublicMiner (the 10-minute Windows task) produced
a first-party sanitized last_run.json receipt:
- 2026-11-15T09:18:24Z; status COLLECTION_FAILED;
- HTTP status 403, approved independent public repo python/cpython,
  operation FETCH_PR_LIST, consecutive_failures=1.
- No authentic Retry-After / X-RateLimit-Reset headers were persisted,
  so **we do not know** whether this was primary/secondary rate limiting,
  authorization, or abuse throttling.
- A separate older P11 error remains historical cause unknown.
- Current P10 isolated queue's two nonnetwork recovery jobs have
  already been independently SUCCEEDED/finalized. P11 public-network
  job 6 remains REVIEW_REQUIRED, 5/5 attempts.

PR #288's 403 fail-closed base miner source is merged to main; the
next scheduled collector safe-skips an unknown 403 without further GET.
This is NOT proof that the upstream service recovered. PR #289's
P11 one-source diagnostic source is also merged but requires a
RECENT HEALTHY base-miner receipt, so owner read-only preflight
correctly BLOCKS on the current base HTTP403. Do not bypass it.

## Isolated diagnostic — not an automated P11 restart

File: src/ucie_miner/public_owner_one_403_probe_v01.py
PowerShell owner wrapper: scripts/public_owner_one_403_probe_v01.ps1.

- Exact D:/UCIE checkout, current Windows SID, approved one-minute UCIE
  task action/SID/Interactive/Limited and exact successful task-event
  observations. No other OS scheduler tasks queried or changed.
- EXACT first-party prior 403 receipt SHA, source python/cpython,
  FETCH_PR_LIST only, official unchanged public URL, and only after
  60-minute hard cooldown from the failed receipt; reject stale >48h
  or shifted/overwritten last_run.json.
- Shared OS-held UCIE PublicMiner lock prevents this one-shot GET
  overlapping the existing hourly-named 10-minute collector.
- BEFORE network, creates a single bounded, non-replayable first-party
  receipt in runtime/public_miner_http403_owner_probe_v01.json using
  exclusive creation (PREPARED). Crash, timeout, interrupted run,
  malformed response and full success all consume the one-only slot.
- One approved public GitHub PR-list GET at most; redirect-denying,
  anonymous, fixed headers, no credentials. No additional queries,
  branches or repositories, patches, file contents, private source,
  or downloaded code execution.
- Parses only numeric X-RateLimit-Remaining / X-RateLimit-Reset from
  the SAME exact successful GET, or sanitized HTTP 403/429 failure
  category and bounded rate pause enum. Raw headers, body, URI,
  token, PR text or personal information are not stored.
- Original last_run.json stays byte-for-byte intact; any outcome
  NEVER changes P10 queue/P11 ledger/Windows task or automatically
  clears a 403 or rearms the P11 worker. The one-shot result cannot
  be used as unqualified proof of future shared quota availability.

## Operator command rules

Default preview only (no API GET, no queue/task mutation):

    cd D:\UCIE
    .\scripts\public_owner_one_403_probe_v01.ps1

If original 403 cooldown has not elapsed or owner/task/receipt diverges,
preview fails closed; no network request is authorized.

A future EXACT one-off diagnostic needs BOTH owner switches:
- -Approve
- -AcceptUnknownSharedQuota

These switches authorize at most one GET only after full code/CI review
and the 60-minute minimum pause, and do not approve a schedule reset,
P11 rearm, package release or any automatic rule promotion.
For the 2026-11-15T09:18:24Z event, the minimum first eligible time is
2026-11-15T10:18:24Z (19:18:24 KST), NOT an instruction to execute
at that exact time. A later owner investigation may still require
more cooldown or may prohibit a new request.

## QA

- tests/test_ucie_public_owner_one_403_probe_v01.py:
  7/7 UCIE owner Windows one-file PASS, disposable synthetic one-source
  success and HTTP403/429, earliest-cooldown and wrong-SHA denial,
  PublicMiner overlap lock, one-time receipt no replay, source refusal
  and REAL owner **READ-ONLY** current preview fail closed. No real GET.
- tests/test_ucie_public_owner_one_403_probe_ps_v01.py:
  3/3 UCIE owner Windows PASS, static explicit dual-consent check,
  real PowerShell parser, default owner read-only wrapper with expected
  no-GET deny; first-party last_run bytes and P11 held queue unchanged.
- Combined 10/10 local PASS, not an independent CI or authority
  to run a public GET. GitHub branch CI must be verified separately.

Approved external references (metadata only):
- https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api

STATUS=BASE_403_ONE_SHOT_SOURCE_AND_LOCAL_QA_PREVIEW_ONLY__
403_ROOT_CAUSE_UNKNOWN__ONE_PUBLIC_GET_NOT_EXECUTED__
P11_HELD_NO_GO__AUTOMATIC_PROMOTION_OFF.
