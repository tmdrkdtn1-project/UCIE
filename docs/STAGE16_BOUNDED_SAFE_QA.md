# Stage 16: bounded, explicitly opted-in public safe-candidate QA

This Stage16 hook is inside the **existing** UCIE hourly collector (after Stage12, under its existing OS byte lock). **No additional Windows task, daemon, CI workflow or trigger is installed.** The hourly miner and Stage13/14 keep their existing independent public-read budgets and database protections.

## Default operation

With no `D:\UCIE\runtime\stage16_safe_qa_opt_in.json`, Stage16 returns `STAGE16_SAFE_QA_DISABLED` without making any extra public GETs or writing a Stage16 state file. Do **not** equate a disabled Stage16 hook with a successful QA run.

After a separate owner decision, the operator may place a UTF-8 JSON marker with **exactly** these two fields into the existing UCIE runtime:

```json
{"schema":"UCIE_STAGE16_SAFE_QA_OPT_IN_V1","run_id":39115340824}
```

The example is a specific previously completed UCIE **main push** CI run; verify the live run before using it. The marker is an authorization to perform *one bounded verification of a pinned public run*, **not** a Rulepack approval, independent human verification or an authorization to inspect another repository.

When the next ordinary Stage10/12 cycle runs with the marker:

- Stage13 rate-budget pause or Stage14 rate-budget pause defers Stage16 with **zero** additional GETs.
- Stage16 consumes a durable local **attempt** marker `runtime/stage16_safe_qa_attempt.json` **before** network access. Same run ID is never automatically queried twice, including after a crash or failed request.
- A *new* explicit run ID may be attempted only after a minimum 24-hour interval from the previous attempted ID. At most **nine** additional public GitHub GETs may be used for one pinned CI evidence check, via the existing UCIE-only verifier (one main run and one jobs list twice in the existing code, plus three previously pinned two-request CI proofs).
- Known UCIE-authored synthetic safe templates may become `STAGE16_SAFE_QA_OBSERVED_REVIEW_REQUIRED`, and the integer number of safely observed recipes may be recorded in the existing **unverified** miner receipt.
- Missing/unlinked Stage12 source records remain `STAGE16_SAFE_QA_LEDGER_INCOMPLETE_NO_GO`. Invalid, incomplete, failed, altered or unavailable CI remains `STAGE16_SAFE_QA_FAILED_NO_GO`. No automatic retries or rate-quota storms.
- Raw upstream code, candidate-provided shell/Python commands, unknown recipes, arbitrary URLs, private material, Rulepack signature keys, and deployment credentials are never accepted as CI inputs.
- `verification_pass=0`, `new_rules_approved=0`, `auto_promoted=false`, `production_approved=false` remain fixed. The existing owner authorization and independent reviews are distinct steps.

## Testing and activation boundary

The new hook has no owner-PC opt-in when merged. CI uses only mocked temporary UCIE files and in-memory synthetic checks; it never creates owner-runtime markers or activates hourly Stage16 automatically. After a separate operator-controlled opt-in, check actual local receipts before claiming Stage16 *operational* success.

Existing Task Scheduler operational evidence can still be `NO_GO` even when a synthetic CI test passes. This patch does not alter task identity, trigger timing, service state or execution provenance. Avoid running the real UCIE miner by hand just to test the hook.
