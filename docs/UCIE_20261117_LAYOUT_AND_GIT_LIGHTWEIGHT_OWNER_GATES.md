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


## 2026-11-20 owner exact-stage crosswalk first-run hold (diagnosis, no mutation)

After owner successfully fast-forwarded staged main to
af0f00fc238f439a1685e9a0012f054218e24e5b, executing the new
--compare-original-git operation returned only
UCIE_LAYOUT_PREVIEW_FAIL_CLOSED. It did not output by-area results;
it is NOT a completed overlap comparison, not a data loss signal, and
does not grant cleanup/cutover. The earlier --observe-original-git run
did complete with original 20 tracked-modified and 1566 untracked.

The original crosswalk implementation incorrectly collapsed all
validation/metadata/query failures into one generic JSON without
the safe failing stage. The next patch reports only fixed classifications
(STAGED_ROOT, STAGED_BRANCH_QUERY, STAGED_BRANCH_NOT_MAIN,
STAGED_REMOTE_QUERY, STAGED_REMOTE_MISMATCH, STAGED_STATUS_QUERY,
STAGED_NOT_CLEAN, ORIGINAL_ROOT, INDEPENDENT_ROOTS,
STAGED_TRACKED_QUERY, STAGED_TRACKED_PARSE, ORIGINAL_STATUS_QUERY,
ORIGINAL_STATUS_PARSE, PRECHECK_OR_UNCLASSIFIED). It NEVER prints
original paths, Git stderr or file bytes. The specific root cause
remains NOT OBSERVED until a fixed-classification receipt is available.
Synthetic unit tests do not substitute for actual owner-host Git behavior.

No original source, protected bridge state, runtime SQLite, task, C40
or external project was read outside the bounded Git status operation,
edited, removed, moved or restarted by this owner attempt. Do NOT try
git clean/reset, force staging or global ignore rules to mask the hold.

## 2026-11-22: owner actual Windows Git-config-sensitive stage check

Owner fast-forwarded the isolated stage to main 5d3ae904, then the crosswalk
returned `failure_phase=STAGED_NOT_CLEAN` without reading operating Git
paths or computing any overlap counts. An additional scoped local read-only
diagnostic observed **normal Git status: 0 changed** versus **strict audit
Git status: 3 tracked modifications, 0 untracked**. The specific owner
Git setting and changed file contents were NOT exported or independently
proved to be solely EOL changes.

The source-side resolution adds a **strict CR-at-EOL-only evidence gate**.
If strict Git reports only unstaged tracked ` M` records, perform an
independent bounded `git diff --ignore-cr-at-eol --no-ext-diff
--no-textconv --quiet --exit-code` under the SAME isolated Git settings.
Only exit 0 with that narrow status shape may continue the crosswalk;
any index/staged edit, untracked entry, actual changed line, changed
trailing spaces, mode change, rename, deletion, query error or timeout
fails closed as STAGED_NOT_CLEAN. The success report explicitly marks
`stage_crlf_only_difference_verified`; it does NOT claim equal file bytes.

This is a source-only candidate fix pending independent Windows owner
execution and tested CI; it does not change global/local Git configs,
.gitattributes, source files on the owner Windows host, the original
D:\\UCIE, SQLite, tasks, C40, bridge state or cutover authorization.

## 2026-11-22: source-integration metadata triage, original contents remain held

After owner-host `--compare-original-git` PASS on merged main `a17eae0d`,
the observed crosswalk counted 711 review-area Git status records:
480 same relative paths in stage, **231 without a matching tracked
stage path**; 874 protected bridge records and 1 root-level unknown were
not compared. The 231 are *path metadata*, NOT proven missing functionality,
not byte-different files, not safe cleanup candidates.

Opt-in follow-on from the **exact same approved staged Windows checkout**:

    D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe -I -B D:\UCIE_PROJECT\UCIE\src\ucie_miner\layout_audit_v01.py --compare-original-git --classify-unmatched

This runs the same pinned-root, branch, remote, staging-clean-or-verified
CRLF-only check as the existing crosswalk. It uses **only already obtained
Git status and tracked-path metadata**; it does not access UCIE-only original
file bytes or compute hashes. It categorizes unmatched paths by fixed
area/extension labels, tracked-versus-untracked and whether the **same
filename exists at a different tracked stage path**. It reports counts ONLY
(no source filenames, private paths, original content or executable code),
and still excludes 874 protected bridge-state records, unknown roots and
unapproved .github subdirectories. Unknown extensions remain `other_or_unknown`.

All 231 start `K0_HOLD_FOR_SOURCE_REVIEW` until source provenance,
reference/dependency, retention and functional equivalence are independently
established. Filename reuse elsewhere is *not* functional parity; no
automatic promotion, import, overwrite, cleanup, migration or release is
granted. This section and the code are first-party development only;
owner Windows count distribution remains UNVERIFIED until the actual
host executes the command. No need to move operating `D:\UCIE`,
task/C40/SQLite or backups.

## 2026-11-22: owner-local code content review (source-only candidate)

Following exact Windows owner metadata triage on staged main 86c96dc,
231 unmatched path records were all untracked; 176 are Python/PowerShell
code or tests (src 20 .py, scripts 7 .py + 20 .ps1, tests 129 .py),
50 docs/JSON and 5 .bak remain held. Same-basename candidates inside
each review area: 0. This is NOT proof of source functional absence.

A separately opt-in content review is added to the EXISTING first-party
layout audit. Source must execute locally from the exact Windows
D:\UCIE_PROJECT\UCIE staged checkout, on main and origin, passing the
clean-or-strict-CRLF-only Git guard. It reads only direct regular
UCIE-owned Python/PowerShell code under src/ucie_miner, src/ucie_public,
scripts and tests. No imports or execution of original code; no
source files are uploaded, copied, written, printed or published.
The result exposes only fixed category counts, never filenames, file
contents, AST text, SHA-256 digests, or protected paths.

    D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe -I -B D:\UCIE_PROJECT\UCIE\src\ucie_miner\layout_audit_v01.py --compare-original-git --review-local-code

Local-only comparison distinguishes same-relative-path exact-byte
identity, CRLF-only differences, genuine content differences and
unreadable/unsafe files. For original-only code paths it compares
in-memory exact-byte, normalized-EOL, and static Python AST fingerprints
to the approved stage-tracked code index. These are REFERENCES TO
REVIEW, not proof that renamed files can replace an original module.
Excludes docs/JSON, all .bak, secrets, Git metadata, runtime, bridge,
SQLite, venv, unapproved source folders, symlinks/junctions, hard links,
oversized files and foreign roots. Skipped files are counted as held.
Per-file read is capped at 512KiB and total data at 128MB; source
identity and Git status are rechecked after review. All originals remain
K0/HOLD and no cleanup, automatic import, production rule promotion,
runtime task/tunnel changes, customer release or cutover is approved.

An actual owner-machine content-review receipt is NOT yet observed.
A code review count or equal AST never proves functional equivalence.
Runtime regression, import graph and approved historical evidence
still require separate verification. Public GitHub stores this audit
mechanism and synthetic tests only, no original source bytes or hashes.

## 2026-11-22: owner content-review real receipt and next static syntax gate

Owner observed staging HEAD `2d9c4192` and local-only code review:
656 stage code files indexed; 582 original code status files read, zero
unsafe/unreadable. The 406 same-relative-path code files classified as
56 byte-exact, 318 CRLF/LF-only and 32 actual byte-content differences.
The 176 original-only code/test paths yielded one EOL-normalized match
elsewhere in the stage and 175 without a static byte/EOL/Python AST match.
These are NOT 175 proven missing functions, and the existing 32 changed
files are NOT automatically semantic behavior changes.

The next additive review subdivides **only the 32 same-path, non-EOL
content-changed records** into Python `same_path_changed_ast_identical`,
Python `same_path_changed_ast_different` and
`same_path_changed_ast_unavailable` (e.g., PowerShell, syntax-invalid
or AST parse cap). Every record must be assigned to exactly one
subcategory; other original/status counts are unchanged. AST equality
means syntax-tree equality under this bounded Python parser, NOT
equivalent imports, effects, packaging, runtime, API, or type comments.
AST difference is a review lead, not proof of regression.

Nothing is executed or uploaded from original source, no protected
state or docs are opened, no original paths or raw digests leak to the
report. All source remains K0/HOLD. An actual Windows execution of
this additive subcategorization is required after CI and pinned
fast-forward of clean stage, and is NOT yet observed.

## 2026-11-22: owner actual Python AST delta receipt and first-party import-reference gate

Owner staged-only fast-forward to `118252e5` and actual Windows code-review
reported 32 same-path non-EOL changed source/test files:
`src` 15 = 3 AST-equal + 11 AST-different + 1 unavailable;
`scripts` 6 = 0 equal + 3 different + 3 unavailable;
`tests` 11 = 1 equal + 10 different + 0 unavailable.
Overall 32 = **4 AST equal + 24 AST different + 4 AST unavailable**.
AST parity is only a static syntax fingerprint and cannot prove behavior.

The next bounded additive **first-party import index** reads only code that
the approved local-only scanner ALREADY read under `--compare-original-git`
`--review-local-code`; it applies ONLY to original-only code files that had
no byte/EOL/AST candidate anywhere in tracked-stage code (175 observed
previously). Source Python is parsed statically with the same 120KiB AST
limit, never imported or executed. Indexed module targets are built solely
from staged-tracked `src/ucie_miner/**` and `src/ucie_public/**` paths.
Aggregate counts separate indexed direct UCIE module import targets,
targets not present in that exact staged module *index*, ambiguous
`from ucie_miner import SYMBOL`, relative/dynamic imports, no observed
UCIE imports and AST-unavailable files. `tests` also counts files with
syntactically test-like nodes, which is NOT proof that pytest/unittest
collected, ran or passed those tests. PowerShell stays explicitly
unparsed/held; its import/call graph is NOT verified.

Crucially, `unindexed` does not prove a broken import or missing feature:
external import hooks, dynamic loading, moved/refactored APIs, namespace
packages and re-exports require further source/behavioral evidence.
`no direct UCIE import` does not prove an unused test. All counters are
fixed categories without original file names, strings, bytes or hashes;
there is no code transfer, runtime change, cleanup, source publication,
dependency install, test execution of owner code, or cutover.
The code still rechecks exact Windows roots and pre/post Git status.
All 175 original-only no-static-match records remain K0/HOLD.
Actual owner-machine reference counts are NOT known until separately run.

## 2026-11-22: owner's no-static-match import census and source-only dependency crosswalk

Actual Windows owner locally ran main cdef79e with the previous read-only
review after a stage-only FF and returned 175 original-only code/test paths:
34 files with indexed first-party module references, 14 with explicit
module path not indexed in stage (scripts 1, tests 13), 31 with ambiguous
relative/dynamic/root-symbol imports, 76 without direct first-party module
imports, 20 PowerShell held, 0 AST unavailable. All 129 original-only test
files have test-like AST nodes but were not executed.

The new incremental crosswalk, **within the same opt-in local code scan**,
matches explicit module targets not indexed in stage to source-module paths
observed among the 20 original-only src Python Git-status records, and
separately identifies ambiguous root-symbol candidates with same names as
original-only source modules. For direct unindexed files it partitions
"matches original-only source module path candidate" versus "no such observed
original-only module candidate", requiring both to add to the prior unindexed
file count. It also exposes numeric relative/dynamic/root-symbol ambiguity
counts (flags may overlap, and are not an exhaustive import interpreter).
No extra source bytes are read beyond the already approved local scan; only
original Git-status path metadata and syntactic import strings are compared
locally. Nothing is returned except fixed enum keys and aggregate counts.

A path candidate is NOT proof that the import resolves, that code is safe
to execute, or that the original module is the correct integration target.
No source import/exec, original filename/path/hash/text export, protected
bridge/SQLite/task/C40 access, migration, cleanup, rule promotion or cutover.
All original and staged sources remain K0/HOLD; owner-machine crosswalk
counts require an actual post-CI and pinned-FF execution to be accepted.
