# UCIE layout / Git-lightweight execution roadmap — 2026-11-17

UCIE ONLY. This is a source-anchored owner-safe migration proposal and preview tool, NOT an approved Windows service relocation or cleanup.

## Observed local state

- D:\UCIE Git status: 230 entries, including 20 modified tracked files and 210 untracked entries. Counts by top-level directory: docs=120, scripts=78, src=25, tests=4, .github=2, .ucie_bridge_state=1. An untracked source, script, QA test or receipt is NOT automatically a cache or trash.
- Existing UCIE runtime includes SQLite DBs (public_miner, knowledge, Stage10-15, P11), opt-in receipts, git_worktrees, locks, reports and backup directories. Runtime database contents were NOT opened or modified by this work.
- Fixed source references to D:\UCIE, D:\UCIE_DATA and D:\UCIE_PREVIEW exist in scripts and tests. Only references were read inside the UCIE repository. Existence or active service state of sibling UCIE paths was not verified. No D:\ root-wide scan, no other-project access.
- The existing bootstrap/install_hourly_task scripts reject any root other than D:\UCIE. Local V1 autostart and C40 profile/tunnel scripts also use absolute paths. A simple folder move would break these dependencies.
- GitHub P6 PR301 has already merged and passed main CI 4/4, but owner D:\UCIE was not synced and its dirty working tree must not be overwritten.

## Proposed future hierarchy (not yet created)

    D:\UCIE_PROJECT\
      UCIE\             first-party repository and one canonical Git metadata directory
      UCIE_DATA\        UCIE-only external data, runtime and MCP profiles
      UCIE_PREVIEW\     isolation-only QA and code review
      ARCHIVE\          owner-reviewed backups and receipts

Start with a non-operating staging/QA directory under this parent. Keep live D:\UCIE, D:\UCIE_DATA and D:\UCIE_PREVIEW in place until path compatibility, service bindings, backup evidence, and owner approval are complete. Do not create symlinks/junctions to disguise the old path: owner scripts intentionally reject them.

## New first-party audit command

After the module is separately present in a safe UCIE checkout, the full read-only report runs with:

    python -I -B -m ucie_miner.layout_audit_v01

For a lighter day-to-day tracked-only Git check:

    python -I -B -m ucie_miner.layout_audit_v01 --fast-git

The fast mode skips Git enumeration of untracked files and ALWAYS labels the result incomplete; it cannot certify a clean working tree. The full mode uses read-only Git porcelain; no status call runs clean/reset/prune, takes locks, or mutates Git history. Source scanning is limited to UCIE-owned code directories and fixed literal path names. No private data, sibling directories or SQLite contents are inspected.

The cache section only counts standard Python cache folders: __pycache__, .pytest_cache, .ruff_cache and .mypy_cache under known UCIE code locations. It does NOT remove or quarantine anything. Symbolic links and external Gitdir indirection are rejected or flagged. Tests run in independent synthetic UCIE checkouts, not the operating owner repository.

.gitignore now protects /.ucie_bridge_state/ from accidentally committing local bridge health/token state; this file is NOT deleted. Existing ignores for runtime, DBs, venv, secrets and datasets remain.

## Critical path without another gate-only development loop

| Stage | Deliverable | Mandatory safety condition |
|---|---|---|
| A. Read-only census | Full/fast Git report, path references, known cache size | Incomplete scan or unknown process bindings mean NO-GO |
| B. Owner source audit | Categorize 20 modified + 210 untracked, hash/backup approved business files | Never blanket-delete unknown scripts/docs/receipts |
| C. New workspace stage | Create empty UCIE_PROJECT and its empty QA/ARCHIVE, after checking exact destination ACLs | Never move a running DB, .venv, C40 or scheduled task |
| D. Root compatibility | Replace each old absolute path in first-party code and Windows Task/MCP configs under separate PRs and tests | Test Python3.15, live task action bindings, one-client C40, SQLite and rollback |
| E. Separate dry run | Restore a verified isolated snapshot, check full path equality, ACLs, timing, independent acceptance | No service restart or live source move |
| F. Owner cutover | Explicit owner authorization, controlled UCIE-only downtime and rollback image | Abort on missing backup, locks, PID/task/bridge mismatch |
| G. Reviewed cleanup | Quarantine only verified transient caches, revalidate, then separate retention approval | No git clean -fdx, reset --hard, forced gc/prune or DB deletion |

Git history must not be rewritten or blindly shallow-cloned: W09/W10 independent tests depend on actual prior Git commit ancestry. Keep a single canonical repository, avoid duplicate long-lived clones/worktrees, and retain CI first-party history until a tested equivalent source pin strategy exists.

## Status and nonclaims

Code/dev checks are distinct from owner-host migration. No folder under D:\UCIE_PROJECT was created, no operating file moved, no data or cache deleted, no runtime speedup or disk recovery measured, no owner task/MCP rebind, no PublicMiner GET, no P11 job6 rearm, no auto promotion and no customer V1 release.

STATUS=UCIE_LAYOUT_READONLY_PREVIEW_ONLY__OWNER_PATH_CUTOVER_NO_GO__PUBLIC_P11_HOLD__RELEASE_NO_GO


## 2026-11-20: exact dirty-file inventory from the already staged UCIE source

The approved UCIE-only read-only admin bridge returned actual original
D:\UCIE Git status with **230 path records: 20 tracked modifications and
210 untracked entries**. These are status metadata observations, not byte
duplicates, not a completed backup, and not permission to discard files.
Existing operational D:\UCIE, its SQLite, C40 and four UCIE tasks remain in
place. The existing clean D:\UCIE_PROJECT\UCIE source was already fast-forwarded
through W39 without overwriting original dirty source.

Prior layout_audit_v01 _git_status mistakenly used Git
--untracked-files=normal, which folds a directory with numerous new files
into a single ?? dir/ record. It could silently undercount the 210 files
that require individual review. This now uses --untracked-files=all in the
full mode, while --fast-git explicitly skips untracked entries and never
certifies cleanliness.

The same first-party module also adds --observe-original-git, callable
**only from exact D:\UCIE_PROJECT\UCIE on Windows**. It reads the original
D:\UCIE Git status metadata without importing or executing original dirty
Python/source scripts. The report contains only counts grouped by UCIE
subdirectory; root-level filenames are masked as
_ROOT_LEVEL_REVIEW_REQUIRED_. It does not display or export original file
contents (Git status may examine working-tree bytes to detect changes),
archive any file, run the miner, touch Task Scheduler/C40, open SQLite,
reset/clean/prune Git or perform a live cutover. Any indirect source root,
missing original .git, incorrect source location or fast+original mode is
denied. The test uses two disposable synthetic UCIE Git repos.

After the reviewed PR is tested and the staged source is synchronised, the
owner can run this **READ ONLY** command using the exact approved staged
Python 3.15 interpreter:

    D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe -I -B D:\UCIE_PROJECT\UCIE\src\ucie_miner\layout_audit_v01.py --observe-original-git

The action is an inventory only. The owner must still classify each of the
20 modified and 210 untracked original items, preserve historical proofs,
verify source/ACL/backups and separately approve any reversible archive.
No deletion, automatic relocation, or false disk-speed claims follow from it.


## 2026-11-20: owner-confirmed file types; exact old-vs-stage PATH crosswalk

The owner ran the original-first Git inventory (PR #337) and the bounded
extension-only local classification. Source-derived observed snapshot:
- 20 original tracked modifications (HOLD)
- 1,566 original untracked files, 874 of which belong to the protected
  .ucie_bridge_state (K0/HOLD)
- Remaining 692 untracked file path records: 504 .py, 59 .ps1,
  118 .md, 5 .bak, 3 .json, 2 .yml and 1 unclassified root-level item.
- No duplicate bytes/unused source/unused QA tests, retention clearance,
  source backup, disk savings or authorized deletion were established.

This source change extends the ALREADY EXISTING first-party layout audit
rather than introducing another process, new task or tunnel dependency:

    D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe -I -B D:\UCIE_PROJECT\UCIE\src\ucie_miner\layout_audit_v01.py --compare-original-git

Source code execution remains pinned to clean first-party staged
D:\UCIE_PROJECT\UCIE on Windows. The audit verifies branch=main,
exact origin, and clean staged Git metadata; original root D:\UCIE is
also fixed. It compares staged Git tracked **relative paths** with original
Git status path records (Git NUL format and --untracked-files=all). It does
NOT import code from the original dirty checkout, read original file contents
in Python, output ANY original filenames, open SQLite, modify Git index,
move/delete/archive anything, reconfigure task/tunnel or traverse other
projects. Git status may inspect operating-tree bytes internally; these
contents are never returned by the audit.

The JSON separates for each approved area docs/scripts/src/tests/.github:
- original untracked vs tracked-modified records
- same relative pathname in staged tracked Git vs not tracked in stage

Bridge state is only counted, with NO file names exposed and no stage
comparison. Other sensitive/unknown roots are similarly held separately;
neither path collisions nor unmatched paths are declared duplicates or
disposable. A same-relative-path result is **NOT a byte match** and a
Git-tracked change is NOT permission to overwrite the operating copy.
Explicit results: byte_duplicate_count_verified=null,
path_overlap_proves_identical_file_bytes=false,
cleanup_approved=false, full_cutover_authorized=false.

This command is a nonmutating owner classification step; any subsequent
SHA-256 content comparison would require separate UCIE-only source rights,
reference/retention review and bounded consent. Do NOT import or publish
private source, secrets, tokens, owner bridge state or original file paths.
