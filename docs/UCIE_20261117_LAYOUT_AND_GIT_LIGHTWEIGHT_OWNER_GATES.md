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
