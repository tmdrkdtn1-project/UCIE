# UCIE Stage 7-8 — Public merge identity and candidate evidence chain V1

## Purpose

Stage 4-8 currently generates candidate-only metadata and regression plans.
This development closes a critical integrity gap: receipts from independent
components must refer to **the same public PR, miner SHA, pinned merge SHA,
release tag and regression family**. Mixing observations from different runs
or silently changing an upstream merge identity now fails closed.

No code from third parties is downloaded or executed by this verifier.

## Pinned public evidence (2026-10-14 UTC)

The nine PR merge identities in
`docs/evidence/public_pr_merge_snapshot_v1.json` were inspected directly
from public PR metadata in approved repositories:

- `python/cpython` PRs 153462, 155365, 156962, 159232, 159364, 159365
- `PowerShell/PowerShell` PRs 25780, 28042, 28087

Each entry contains the canonical source URL, exact merge time, merge commit
SHA and target/base branch. The pinned snapshot is **source metadata only**:
it is not a signed attestation, independent behavioral regression result or
a claim that a specific binary/release tag contains the fix.

Important: branches `3.14` and `3.15` denote upstream target branches,
**not fixed or vulnerable version ranges**. In particular a release-tag
marker alone is not proof that all changes from a later PR were included.
Every generated result therefore retains
`fixed_release_version = UNDETERMINED`.

Pinned public license documents from the approved upstream repositories
were inspected at the four existing curated release tags. This validates
the existence of a license document and its known marker only; it does not
constitute legal or file-by-file licensing approval.

## Offline candidate receipt binding

`ucie_miner.evidence_binding.bind_candidate_receipts` verifies:

1. Exact source/PR identity, miner SHA and merge timestamp across source rows
   and public metadata inspection.
2. Comparisons protected by the SHA-256 calculated in the originating
   provenance receipt; even a matching synthetic/mock receipt remains
   `UNVERIFIED`.
3. License coverage by **all** curated (source, release tag) pairs.
4. Canonical/backport family membership and independently recomputed family
   fingerprints from all member evidence digests.
5. Candidate Rulepack guidance/digest and synthetic regression matrix
   exactly reconstructed from matching Stage 5 family receipts.
6. Zero persistent writes, approval, signatures, deployment or promotion.

The returned `receipt_sha256` is a reproducible fingerprint, **not a
cryptographic signature**. A fingerprint mismatch is a reason to stop.
Even a complete match remains
`STRUCTURALLY_CONSISTENT_CANDIDATES`, not `VERIFIED` or `PASS`.

The Stage 8 `preview-acceptance` now includes both this binding digest and
the pinned-public-merge snapshot digest; status remains `NO_GO`.

## Read-only audit command (only in independently reviewed UCIE test checkout)

```powershell
.\.venv\Scripts\python.exe -m ucie_miner audit-merge-snapshot
```

This reads local public metadata and the committed pinned snapshot without
any network. It can detect stale local merge times, missing pins and duplicate
PR identities. Additional local candidates beyond the curated nine remain
unmapped/unverified; they are not silently promoted.

```powershell
.\.venv\Scripts\python.exe -m ucie_miner audit-merge-snapshot --verify-live
```

**Only when the user separately authorizes this live read**, the second
command makes bounded anonymous public GitHub PR metadata GET requests and
compares observed merge SHA to pinned public identity. No patch application,
raw external code execution, database migration or scheduler change occurs.
Source metadata equality alone does not authorize operational acceptance.

## Independent verification still required

The following have not been demonstrated:

- independently reproduced error and safe-fix regression for an actual
  affected runtime, across relevant version ranges
- file-specific legal and security approval
- verified release inclusion/affected version interval for every fix
- authorized independent reviewer identity and Rulepack signature
- real Windows host full acceptance; no OS scheduler state was modified

All production-gate statuses remain `NO_GO`. Stage 4-8 Draft PR stack is
unchanged; the new changes belong only to another Draft and CI are
**required on the exact new commit**. No `main` merge or live DB import
is performed.
