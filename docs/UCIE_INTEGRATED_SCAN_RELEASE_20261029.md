# UCIE manual integrated scan — isolated change (2026-10-29)

**Scope:** UCIE only. **Status:** Existing static scanner/feedback integration; no new production rule authorization.

This change integrates four EXISTING bounded Python static detectors into the manual inspector and the existing UCIE CLI. It does not execute supplied Python text, automatically apply fixes, collect other projects, sign rules, install a service, write an operating database, or edit the hourly scheduler.

## Exact files in this change

- `src/ucie_miner/existing_rule_inspection.py` — single first-party Python manual inspector, signed-pack checks, synthetic feedback prioritization, bounded parsing/fast-path and explicit fail-closed diagnostics.
- `src/ucie_miner/p13_decimal_unbounded_guard.py` — bounded AST-only Decimal review candidate (not an approved auto-rule).
- `src/ucie_miner/__main__.py` — minimally adds `--all-existing-rules` and `feedback-python-synthetic-stdin` without changing default `scan-python-stdin` behavior.
- `tests/test_ucie_existing_rule_inspection.py`, `tests/test_ucie_p13_decimal_unbounded_guard.py`, `tests/test_ucie_inspection_perf_profile.py`, `tests/test_ucie_powershell_feedback_input_diagnostic.py` — existing detector integration, signed-pack test-key verification, failure modes, Windows PowerShell JSON, and bounded performance regressions.

No local P10/P11/worker/schedule code or other pending uncommitted changes are included.

## Manual PowerShell usage

The caller must provide first-party UCIE synthetic text or authorized approved public Python source, never private files or cross-project data.

```powershell
$root = 'D:\UCIE'
$py = "$root\.venv\Scripts\python.exe"
$env:PYTHONPATH = "$root\src"
$source = @'
import os
from concurrent.futures import ThreadPoolExecutor
def run(folder, cb):
    iterator = os.scandir(folder)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return pool.submit(cb, iterator).result()
'@
$source | & $py -B -m ucie_miner.existing_rule_inspection --ucie-root $root
```

For labeled synthetic feedback, pass JSON with 2–20 entries, each containing exactly `case_id`, `source`, and `expected_rule_ids` (a JSON array). Include positive and negative controls, then invoke:

```powershell
$json | & $py -B -m ucie_miner.existing_rule_inspection --ucie-root $root --feedback-synthetic
```

The existing `python -m ucie_miner scan-python-stdin --all-existing-rules` and `python -m ucie_miner feedback-python-synthetic-stdin` work through the original CLI but are slower to start because they load the broader miner CLI. Neither command reads other code files or writes the runtime database.

## Trust and limits

Previously signed Serial4/Serial5 rules require explicit original UCIE-local signed-pack and owner PUBLIC trust paths, original signature/expiry/scope checks, and manual review. Unsigned scanner findings remain `UNVERIFIED_STATIC_CANDIDATE_ONLY`. Output from first-party synthetic calibration cannot be used as an independent production quality or upstream fixed-version claim.

The first-party local Windows suite previously passed 145/145 before the final input diagnostics change, and related input/PowerShell/speed regressions subsequently passed. **A new branch does not inherit that result**: its own GitHub CI and final suite results must be checked before merge.
