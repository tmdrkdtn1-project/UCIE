# UCIE Stage 7 public evidence provenance audit (candidate-only)

This change extends the **Draft Stage 4-8 integration branch** and does
**not** modify the scheduled collector, live Knowledge database, other
projects, private accounts, or `main`.

## Scope and authority

The Stage 7 source inspection operates only on the **two sources already
implemented by the pinned Stage 4 reviewer**:

- `python/cpython`
- `PowerShell/PowerShell`

The overall UCIE public research policy also permits `git/git`,
`modelcontextprotocol/python-sdk`, and `actions/runner-images`. This
reviewer does not silently extend its implemented source adapter.

`audit-provenance` validates the canonical PR URL and metadata digest
from the existing UCIE miner ledger. With an explicit `--verify-live`,
it makes anonymous HTTPS GET requests to exactly constructed public GitHub
REST pull-request endpoints and compares the PR number, merge state,
merged-at timestamp, canonical URL, target/base repository identity and
40-digit merge commit SHA. It does **not** download or execute patches,
load arbitrary URLs, follow redirects, contact project connectors,
persist results, or require credentials.

The source check is about public *metadata identity*. A matching API
record is **not** a reproduced fix, security approval, pinned-license
verification, production Rulepack signature or permission to deploy.

## Read-only commands

Only after installing the reviewed branch in an **isolated UCIE test
checkout**, these commands may be used against approved public miner data:

```powershell
.\.venv\Scripts\python.exe -m ucie_miner audit-provenance
.\.venv\Scripts\python.exe -m ucie_miner audit-provenance --verify-live
```

The first form only validates local metadata and returns `NOT_CHECKED`
for source authenticity; it **never contacts the network**. The second
form is explicitly opt-in and reads anonymous public PR metadata only.
It is **not** an authorized live-host operation or production rollout.

The audit emits only bounded public metadata identities, SHA-256
fingerprints and unverified results. An injected synthetic fetcher in tests
returns `SYNTHETIC_METADATA_MATCHED`, never a real source-validation PASS.

The Stage 7/8 `preapproval_readiness` combines a Stage 4-7 Knowledge
preview with a provenance receipt and enforces the coverage and
non-approval boundary. Even a complete, caller-supplied positive
metadata receipt produces `NO_GO`; the independent licensing/security
review, behavioral regression reproduction, owner approval, authorized
signature and real Windows acceptance all remain pending.

## Validation

- Offline synthetic tests check mismatched owner, unmerged PRs, malformed
  merge commits, unreachable public API, unauthorized sources, duplicate
  records, absent coverage and forged signatures/approvals.
- Existing Windows/Ubuntu Python 3.13 and 3.15 test matrix must run on
  the exact new commit.
- This code is an **unapproved candidate** until the new PR is reviewed.
- There has been **no** real public API verification, Windows owner-PC
  test, main branch merge, scheduled task modification, permanent DB
  import, Rulepack signature, deployment or package distribution.

**Status:** `DRAFT_CANDIDATE_ONLY / NO_GO / NO_PROMOTION`.
