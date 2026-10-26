# UCIE first signed public Rulepack — grounded case calibration (2026-10-26)

## Fixed release and scope
- Rule: `PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO` (public, manual static review only)
- Already owner-signed source SHA: `81d935b13420b844f7301920e9915a7a3f1a6132`
- Owner-signed CI: [40272296034](https://github.com/tmdrkdtn1-project/UCIE/actions/runs/40272296034) (4/4 success; Windows/Ubuntu)
- Existing signed package SHA-256 reported by owner: `DD057D611E99486E6A6C0DD15E2B2C604AEAF593BFF3D2809167707E87D36AFF`
- This evidence-only change neither resigns nor modifies that immutable package.

## Real public positive *source* and scope limitation
- [CPython issue #159010](https://github.com/python/cpython/issues/159010): the **public console reproducer**, with shell prompt `$ ` removed, shows `python3.14 -X disable_remote_debug`. The report states the unsupported underscore spelling is silently ignored.
- [CPython PR #159014](https://github.com/python/cpython/pull/159014): official documentation correction to `disable-remote-debug`.
- UCIE-host PowerShell AST parser measured **1 finding** for the reported wrong command and **0 findings** for the report's corrected command. Test: `tests/test_ucie_official_issue159010_calibration.py` (local Windows PASS, no source execution).
- These console examples are **not actual PowerShell repository script files**. No genuine public PowerShell source-file positive has been located. The test itself does not repeat a CPython interpreter behavioral experiment.

## Real public negative-file scans (owner-host receipts)
Both sources below come from the approved independent public repository `actions/runner-images`, commit `4f94a804ccf6254bfc5c7fd90a213db4b21794cd`:
- [helpers/CheckJsonSchema.ps1](https://github.com/actions/runner-images/blob/4f94a804ccf6254bfc5c7fd90a213db4b21794cd/helpers/CheckJsonSchema.ps1) — 0 findings.
- [images.CI/shebang-linter.ps1](https://github.com/actions/runner-images/blob/4f94a804ccf6254bfc5c7fd90a213db4b21794cd/images.CI/shebang-linter.ps1) — 0 findings.

The owner reported both as `UCIE_FIRST_REAL_PUBLIC_SCAN_PASS`; these are two observed *negative* examples, not an independently labeled population sample. There is no justified sensitivity, specificity or false-positive-rate estimate.

## Boundaries / next evidence
- Only official CPython issue/PR and explicitly approved public repository files; no private repositories, recipient projects or source retention.
- No auto-apply, auto-promotion, retraining, signing, scheduler changes, public package distribution or independent reviewer claim.
- If an approved public PowerShell file containing the literal wrong option is found, pin repository+commit+path, obtain source-rights review and run the same signed read-only consumer once. Otherwise mark this case as **PUBLIC_POWERSHELL_POSITIVE_NOT_FOUND**, not PASS.
