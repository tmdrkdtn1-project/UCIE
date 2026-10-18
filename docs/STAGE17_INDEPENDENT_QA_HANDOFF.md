# Stage 17: candidate-by-candidate independent QA / security handoff

Stage16 has already established **aggregate UCIE-owned public CI safe-template
observation**. It did **not** establish independent verification of any new
candidate, license signoff, source-version applicability, owner approval, or
permission to deploy. Stage17 prepares the missing review handoff without
changing that boundary.

## Offline read-only command

On the already opted-in UCIE Windows checkout, after an ordinary Stage16
cycle has recorded its result:

```powershell
Set-Location 'D:\UCIE'
& '.\.venv\Scripts\python.exe' -B -m ucie_miner inspect-stage17-review
```

The JSON contains a deterministic review digest, candidate IDs and
source-evidence SHA-256s, optional exact pinned upstream PR links, static safe
template names, per-candidate triage, and independent reviewer action items.

- `PINNED_TEMPLATE_INDEPENDENT_REVIEW_REQUIRED`: the current Stage12
  candidate has exactly one pinned UCIE-authored safe template, and a bounded
  Stage16 **aggregate** CI receipt exists. **Not a candidate-specific CI pass.**
- `AMBIGUOUS_SOURCE_REVISION_NO_GO`: more than one revision of a fixed
  rule or a Stage12 ambiguous evidence warning exists; explicit independent
  review and source revision selection required.
- `UNSUPPORTED_SAFE_RECIPE_NO_GO`: unknown source revision or unsupported
  candidate with no UCIE-owned executable safe recipe. Never execute or
  synthesize a candidate-supplied test.
- `STAGE16_AGGREGATE_EVIDENCE_MISSING_NO_GO`: Stage16 aggregate attempt
  cannot be linked to a valid successful same-cycle miner receipt.
- `INCOMPLETE_REVIEW_LEDGER_NO_GO`: Stage12 ledger is not fully synchronized
  with its Stage10/15 source ledgers.

Stage17 reads the **existing** Stage16 attempt file, bounded recent UCIE
miner history (up to 1 MiB and 256 entries), and the preexisting Stage12
validated source/queue ledgers. Only an exact same-cycle successful Stage16
receipt is accepted as aggregate evidence; later hourly cached results do
not erase prior observation. Evidence older than seven days is stale. The
attempt file is not a signing key, and the generated docket SHA-256 is **not
a signature**.

Every candidate keeps `independent_qa=NOT_PERFORMED`,
`security_review=NOT_PERFORMED`, `license_review=NOT_PERFORMED`,
`candidate_level_ci_binding=NOT_ATTESTED`, `human_approval=false`,
and `deploy_allowed=false`. Even a 4/4 passing GitHub CI matrix does not
override these gates. Stage17 reads no outside/private project, performs
**zero** network API requests, executes **zero** untrusted commands, and
writes **zero** files. It runs only on explicit CLI invocation; it is **not**
an additional scheduled process or recurring API call.

## Who must do the next work

Independent reviewer: authenticate approved public source/merge identity,
select a single revision, independently reproduce the vulnerable/fixed
behavior in an isolated owned test fixture, establish positive and
security-negative regressions, verify runtime/version and license scope,
and record reviewer provenance in the future independently approved
evidence process.

UCIE owner: evaluate the independently obtained QA, security and licensing
claims and separately authorize any future signed Rulepack and release.
**No Stage17 output itself authorizes production.**

The existing Windows Task Scheduler timestamp/provenance operational NO-GO
is orthogonal and remains unchanged by this read-only review command.
