# UCIE P10/P11 forward-only failure evidence and recovery decision

Date: 2026-11-15 KST. Isolated UCIE public-metadata-only workroom.

## Actual P10 independent handler proof (owner Windows)

The exact approved P10 process command
\`python -B -m ucie_miner.runtime_pipeline --execute --ucie-root D:/UCIE --kind <kind>\`
was run individually, once per **non-network** allowed kind, through the
owner's one-file UCIE test adapter (not through P10's pending queue):

- PUBLIC_METADATA_REVIEW: child exit 0, HANDLER_READ_ONLY_SUCCESS.
- UCIE_REPORT_PREPARATION: child exit 0, HANDLER_READ_ONLY_SUCCESS.
- Both: child-reported network_requests=0, operating_db_writes=0,
  auto_promoted=false. P10 and P11 snapshots identical before/after.
- The historical P10 queue still contains exactly 3 REVIEW_REQUIRED
  kinds, all attempts 5/5 and last_reason RETRYABLE_ERROR:
  the two non-network kinds above and PUBLIC_INCREMENTAL_MINING.
  Four other kinds have historical SUCCEEDED. Zero pending/running.
- The two handlers WORK NOW; this does NOT establish which exception
  failed their past five leased attempts, nor auto-authorize retry.

## P11 failure-classification repair

Historical last public GET attempt: 2026-11-01T09:03:02Z, failed.
P11 next source index points only to repo:python/cpython, among exactly
five allowlisted independent public repo routes. Previous successful GETs:
450; experience records 91; improvement reviews 26;
production improvements applied = 0.

The old P10 worker suppresses both stdout and stderr of the child and
ultimately stores generic RETRYABLE_ERROR in queue. This cannot be
reinterpreted post hoc as HTTP 429 or malformed JSON.

Source change in \`p11_closed_loop.py\`:
- Once a new P11 public fetch/discovery fails, store ONE bounded
  \`p11_last_public_failure_v02\` row in the ALREADY OPTED-IN isolated
  P11 SQLite file. It contains only source index (0..4), attempt UTC,
  and one closed-vocabulary \`failure_class\`; no raw error message,
  HTTP URL, PR title, response, source file or user data.
- Classify using the previously reviewed first-party
  \`classify_stage10_discovery_error\`, including bounded explicit
  exception causes. Distinguish HTTP_429, HTTP_403, other HTTP,
  network/timeout, invalid JSON, rejected response/validation and
  unknown error. A bare \`DiscoveryError\` with text like "429" is
  **NOT** accepted as HTTP_429 without a real HTTPError cause.
- Verify the cursor still reflects the exact failed source and
  attempted UTC before writing the enum. Retain the 5m failed-attempt
  cooldown, the same source cursor and all existing caps.
- \`status()\` is strictly read-only; it returns
  \`HISTORICAL_CAUSE_NOT_RECORDED\` for an earlier failed attempt that
  predates this new table, rather than inventing a cause. After success,
  current failure category is null. No new public GET to backfill history.
- Owner/synthetic tests:
  \`test_ucie_p11_public_failure_classification_v02.py\` 5/5 PASS,
  existing P11 \`test_ucie_p11_closed_loop.py\` 13/13 PASS,
  exact owner \`test_ucie_p10_exact_handler_process_v02.py\` 2/2 PASS,
  live read-only \`test_ucie_p10_p11_readonly_live_probes_v01.py\`
  1/1 PASS and observed historical cause unavailable.

## Remaining exact task safety gates

P10's \`p10_owner_rearm_v01.py\` is still synthetic-only, cannot mutate
operating \`D:/UCIE\` even with arbitrary Python booleans. Only
two exact non-network held kinds are eligible for a subsequent
per-job OS-owner-attested, source SHA/queue fingerprint-gated live
rearm. P11 public collection requires a separate strict GET/quota and
failure-classification approval; do NOT rearm the network kind together
with either non-network kind. Do not reset all three jobs, start tasks,
call GitHub, or upgrade LLM/Qwen automatically.

The independent UCIE basic PublicMiner 10-minute task has already
been installed on the owner host, proven to run twice with 10.95-minute
start gap and event-to-receipt bindings. This does not unblock P10/P11
or promote any collected public candidates.

STATUS=P10_TWO_EXACT_CHILD_HANDLERS_EXECUTABLE_READ_ONLY__
P11_FORWARD_ERROR_ENUM_STAGED_NOT_HISTORIC_CAUSE__
P10_QUEUE_REARM_NO_GO_P11_GET_REARM_NO_GO_RULE_PROMOTION_OFF.
