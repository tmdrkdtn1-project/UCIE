# UCIE V1 manual code review — one command, two languages

**Result:** One explicitly supplied UCIE-owned synthetic or approved-public code snippet → JSON with known static pattern, line/column, source-linked public PR, safe manual correction guidance, and narrowly verified release version. Reuses existing scanners; not a new Stage or miner.

## Run

In a clean UCIE-only checkout, with that checkout's Python environment:

```powershell
$root = 'D:\UCIE_RELEASE\UCIE'
$py = 'D:\UCIE\.venv\Scripts\python.exe'
$env:PYTHONPATH = "$root\src"
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

For PowerShell, installed PowerShell is needed but the same unified command is used:

```powershell
$source = "Resolve-Path -Relative '.directory'"
$source | & $py -B -m ucie_miner.code_review_v1 --ucie-root $root --language powershell
```

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
