# UCIE V1 manual code review — one command, two languages

**Result:** One explicitly supplied UCIE-owned synthetic or approved-public code snippet → JSON with known static pattern, line/column, source-linked public PR, safe manual correction guidance, and narrowly verified release version. Reuses existing scanners; not a new Stage or miner.

## Run — isolated clone (do not change your operating UCIE checkout)

This example is a **preparation runbook**, not a claim the owner's computer was changed or verified. Use only an empty, separately named directory and the approved public UCIE repository. Existing working-tree modifications and local runtime databases remain untouched.

```powershell
$root = Join-Path $env:TEMP 'UCIE_V1_VERIFY\UCIE'
if (Test-Path -LiteralPath $root) { throw 'Choose a NEW isolated folder; never overwrite' }
git clone --depth 1 --branch main https://github.com/tmdrkdtn1-project/UCIE.git $root
if ($LASTEXITCODE -ne 0) { throw 'Isolated checkout failed' }
$basePython = (Get-Command python -ErrorAction Stop).Source
& $basePython -m venv (Join-Path $root '.venv')
if ($LASTEXITCODE -ne 0) { throw 'Isolated venv failed' }
$py = Join-Path $root '.venv\Scripts\python.exe'
& $py -m pip install -r (Join-Path $root 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Isolated requirements failed' }

# Critical for native pipes on Windows PowerShell 5.1 and PowerShell 7:
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:PYTHONPATH = Join-Path $root 'src'
$commit = git -C $root rev-parse HEAD
$source = @'
import os
from concurrent.futures import ThreadPoolExecutor
def work(folder, callback):
    iterator = os.scandir(folder)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return pool.submit(callback, iterator).result()
'@
$source | & $py -B -m ucie_miner.code_review_v1 --ucie-root $root --language python
```

For PowerShell source, use the *same isolated interpreter*, explicit UTF-8 pipe and CLI:

```powershell
$source = "# UCIE 자체 합성 예제" + [char]10 + "Resolve-Path -Relative '.directory'"
$source | & $py -B -m ucie_miner.code_review_v1 --ucie-root $root --language powershell
```

**Do not** combine the live `D:\UCIE` virtual environment with a different source checkout. A clean isolated clone's Python environment must be used only with that clone. This is an optional manual host follow-up; CI performs its own separate clean-checkout test without accessing the owner's PC.

Input must be explicitly supplied UCIE-authored synthetic or authorized approved-public source. **Do not scan unrelated/private project code or other user files.** Never executes source, scans files, fetches a network resource, writes runtime DB, applies fixes, signs or promotes rules.

## Output and trust

- `findings[]` contains `rule_id`, `line`, `column`, `safe_fix_guidance`, `public_evidence`, `version_evidence`, `authorization`, `manual_review_required`.
- For `PS_RESOLVE_PATH_DOT_PREFIX` only, `version_evidence` refers to actual CI observations for the official **PowerShell 7.6.6 Windows x64 and Linux x64** release binaries, not the caller's source, other releases or architectures. All other version coverage remains explicitly unknown.
- The unified manual entry point always keeps findings `UNVERIFIED_STATIC_CANDIDATE_ONLY`. Existing signed owner Rulepacks are separately verified and are **not** silently inherited.
- `NO_KNOWN_PATTERN_NOT_SAFETY_PASS` does not assert safe code. `CODE_REVIEW_FAIL_CLOSED` uses exit 2 with a sanitized reason, never echoes supplied source.
- 16 KiB UTF-8 cap. Static heuristics have false positives/negatives. No automatic fixes, auto-promotion, quality PASS or product V1 acceptance.

## Existing code reused

Python: `existing_rule_inspection.inspect_existing_python` (four scanners).
PowerShell: original `scripts/ucie_powershell_static_candidates.ps1`, passed inert text from a small trusted adapter.
Exact known-version evidence: `p9_pinned_public_review.lookup_pinned_review`.

The CLI and real PowerShell AST tests run on the existing GitHub Windows/Ubuntu Python 3.13/3.15 CI matrix. Only the final exact head CI may justify a merge.


## Integrated Virtual Library evidence (automatic, no extra command)

Each detected finding now includes `public_library`. UCIE reuses the original W04 read-only Stage10/12/15 source-linked public ledger reader, searching by the exact approved public PR URL and source repository, without network calls or private-project access.

- `EXACT_PUBLIC_PR_SOURCE_LINKED_UNVERIFIED`: exact public PR identity matched a source-validated UCIE ledger row. Returned library ID, source revision hint and evidence SHA-256 are still unverified.
- `PUBLIC_SOURCE_LEDGER_INCOMPLETE_NO_GO`: local Stage12 ledger missing or source linkage incomplete; no assertion is made.
- `NO_EXACT_PUBLIC_PR_IN_CURRENT_LINKED_LEDGER`: a fully returned source window has no exact public PR row; UCIE will not substitute another PR.
- `NO_EXACT_PUBLIC_PR_IN_BOUNDED_SOURCE_WINDOW`: a partial 20-row source window has no exact PR row; later rows may still exist, so this is not proof of absence.
- Corrupt/forged provenance fails closed rather than inheriting approvals or release coverage.

The query is performed once per distinct PR in the inspected snippet. Top-level metrics `public_library_exact_pr_lookups` and `public_library_linked_findings` describe this bounded source lookup. A match is **public source identity**, not proof the rule fixes input code, licensing, independent QA, or export approval. A partial 20-record window reports `truncated`.

The same single command and both languages remain unchanged. No new miner, API collection, DB writes, source execution, automatic rule approval, package release or V1 acceptance.

## UTF-8 input integrity

PowerShell code review preserves the original strict UTF-8 bytes, including Korean comments, emoji and CRLF line endings, through the UCIE-owned stdin adapter. It does not rely on the machine's console codepage (including Windows PowerShell 5.1). The adapter rejects malformed UTF-8 and inputs over 16 KiB, and verifies the original source digest. The Python CLI also rejects UTF-8 BOM-prefixed stdin with `SOURCE_UTF8_BOM_UNSUPPORTED` instead of silently dropping the three BOM bytes and reporting the wrong original-source SHA-256. Remove the BOM only in an explicitly authorized source preparation step and treat the resulting bytes as a different input. Inputs are still parsed as inert AST data, never executed or echoed. CI exercises the real CLI and both available PowerShell engines with first-party synthetic Unicode samples; this does not grant new source permissions or product approval.


## V1 manual CLI acceptance verdict (bounded)

The clean GitHub Windows Python 3.15 job executes `tests/runtime_ucie_v1_real_shell_acceptance.ps1` through both native **Windows PowerShell 5.1** (`powershell.exe`) and **PowerShell 7** (`pwsh`). This replays the *documented native PowerShell pipe* with explicit UTF-8, two different Unicode source comments, Python and PowerShell positive findings, correct line numbers, source-linked evidence remaining unapproved, empty clean control, invalid syntax fail-closed, and elapsed milliseconds. It prints an inspectable `UCIE_V1_DUAL_WINDOWS_SHELL_ACCEPTANCE` receipt in GitHub Actions. Ubuntu/Windows Python 3.13/3.15 existing full tests still run.

A green bounded shell test means **manual CLI GO in isolated CI**, not the UCIE V1 project GO. User-host deployment, operating hourly schedule, independent QA/license review, approved export and autonomous learning/promotion remain separate and unverified by this job. It does not execute arbitrary caller source or read private code. Never report a local host PASS without a separate actual local receipt.
