# UCIE B3 real documented Python 3.15 behavior change — 2026-11-27

**Evidence scope:** Official Python documentation, not a customer runtime or a reproduced runtime defect. UCIE-only Draft; no source redistribution or operating writes.

- Python 3.14 official `os.scandir` API reference: https://docs.python.org/3.14/library/os.html
- Python 3.15 official `os.scandir` API reference: https://docs.python.org/3.15/library/os.html
- Observed official 3.15 change note: `os.scandir(-1)` now raises `OSError(errno.EBADF)` rather than listing the current directory.
- Source owner: Python Software Foundation / CPython official project; observed 2026-11-27.
- **Important limit:** exact source-page byte SHA-256 and official change-commit lineage have NOT been independently attested here. The note is a documentation observation, not proof that the user’s executable has been tested or that the existing UCIE recipe uses `-1`.
- Previously curated UCIE Python source tag is `v3.15.0` and Git source tag is `v2.51.0`. The official documentation change is NOT treated as a newly observed revision after `v3.15.0`. It is a real, version-scoped documented compatibility change; keep any “new upstream update discovered after previous pin” gate **HOLD**.

## Actual implemented B3 decision logic

`src/ucie_miner/b3_documented_scandir_315_delta_v01.py` uses exactly the two existing first-party case IDs and their existing Capsule hashes. No new source URL can be injected into the evaluator.

| Fixed case | Declared Python version | Explicit -1 call-site declaration | Decision |
| --- | --- | --- | --- |
| Python scandir | 3.15 | True | Propose a targeted call-site review/retest; no execution, no runtime proof |
| Python scandir | 3.15 | Unknown | Ask for call-site verification; do not claim a defect |
| Python scandir | 3.15 | False | No negative-fd risk inferred from this documented change; declaration unverified |
| Python scandir | 3.14 or unknown | True | No 3.15-specific retest candidate; no compatibility PASS |
| Git porcelain | Any supported declaration | Any | Not affected by Python `os.scandir` change; retests 0 |

For a confirmed, explicitly authorized program needing current-directory enumeration, an explicit path is easier to reason about than relying on a sentinel `-1`. This is a **proposed safe-call pattern**, not an automatically applied patch. Never scan owner/customer code to discover such call sites without a separate owner gate.

## What is NOT done

No customer code, private files, local original worktree, actual Python 3.14/3.15 execution on owner PC, official commit SHA verification, rights/license clearance, independent QA, package publication, V04 route change, automatic retest scheduler or DB write. `documentation_delta_observed=True` indicates the official *textual note*, not authenticated immutable original bytes or a newly fetched 3.15 patch.

Targeted offline tests check positive/negative, source isolation, unknown, invalid versions, deterministic proposal digest and false-approval prevention. User-visible preview adoption is separately reviewed; do not claim real browser QA.
