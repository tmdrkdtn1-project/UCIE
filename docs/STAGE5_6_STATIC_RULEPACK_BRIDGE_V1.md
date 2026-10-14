# UCIE Stage 5 → Stage 6 static candidate bridge V1

This Draft extends PR #17 (inert Python/PowerShell risk-pattern detection) and
PR #16 (UCIE-controlled safe-call mitigations). No other repositories,
connected apps, private code, host PC files or operating database are accessed.

## Verified contract vs unverified claims

**New API:** `preview_static_rule_candidates(root, scan, existing_rulepack=None)`
accepts bounded untrusted static scanner metadata, checks exact allowed
field sets/types, canonical PR URLs and known pinned merge SHA identities
via the already-reviewed Stage 4 public manifest/snapshot, and generates:

- Source line/column, pattern, SHA-256 candidate fingerprint
- Non-executable Stage 6 safe-fix *guidance* and a regression *plan*
- A fixed public canonical PR with `merge_commit_sha` (PR identity only)
- Explicit `NOT_EXECUTED` and `NOT_RECEIVED` test/reviewer statuses
- `NOT_VERIFIED` for each independent Rulepack gate
- `deploy_allowed=false`, `production_approved=false`,
  `persistent_writes=0`, `auto_promoted=false`

Allowed bindings are **only** `python/cpython#153462`,
`PowerShell/PowerShell#28042` and `PowerShell/PowerShell#28087`,
all already present in Stage 4's pinned, approved public evidence.
No automatic source expansion.

Scanner-reported source hashes are **not authenticated source provenance**.
A public PR merge SHA is **not** an affected-version/release-inclusion proof.
These are heuristic findings; they may be false positives/negatives.
An empty scan output does **not** establish safe code.

The optional `existing_rulepack` path accepts only a valid unsigned,
unapproved Stage 6 candidate Rulepack: it validates the full synthetic
regression matrix, the matching source/PR/pattern ID and ensures the
regression remains NOT_EXECUTED. Even a match produces only
`STRUCTURALLY_LINKED_UNVERIFIED` — never a validated or deployable pack.

## Read-only CLI

For user-supplied **approved public or UCIE-authored synthetic** text:

```powershell
@'
import os
def run(path, pool, consumer):
    raw = os.scandir(path)
    pool.submit(consumer, raw)
'@ | .\.venv\Scripts\python.exe -m ucie_miner scan-python-stdin --preview-candidates
```

PowerShell's inert `Find-UCIEPowerShellCandidate -SourceText` can emit a
JSON receipt; after a separate, explicitly controlled transfer to stdin:

```powershell
# Supply a reviewed synthetic/public JSON receipt through stdin:
# python -m ucie_miner preview-static-json-stdin
```

The JSON CLI enforces a 128-KiB input limit and rejects duplicate JSON
properties, unexpected fields, forged approvals, noncanonical URLs,
mismatched Rulepack identities and unsupported patterns. It does not
read an external source filename, invoke the submitted program,
use eval, retrieve an upstream patch, write SQLite, or register a task.

## Detector accuracy improvement

The Python AST scanner now clears a raw-scandir iterator candidate after
local lexical rebinding, reducing false positives from e.g.
`it = os.scandir(path); it = list(it); pool.submit(worker, it)`.
The implementation remains **lexical/heuristic**: it does not prove path
conditions, aliasing, cross-function lifetimes or the actual identity
of an arbitrary `.submit` receiver.

All tests are synthetic, using the existing Windows/Ubuntu Python 3.13/3.15
CI. None retries the historically crashed **raw native** iterator race.
Protected UCIE-owned `GuardedScandir` behavior is distinct from a fixed
upstream CPython runtime.

## Operational gates

`STAGE5_6_STATIC_BRIDGE_CI` is assessed only after the exact PR CI matrix.
`INDEPENDENT_UPSTREAM_BEFORE_AFTER=NOT_VERIFIED`.
`RULEPACK_SIGNATURE=NONE`.
`AUTOMATIC_PROMOTION=DISABLED`.
`WINDOWS_HOST_ACCEPTANCE=NO_GO`.

The PR must remain Draft until approved. No merge, live Knowledge DB
import/migration, scheduler change, Rulepack signing or package release
is performed by this change.
