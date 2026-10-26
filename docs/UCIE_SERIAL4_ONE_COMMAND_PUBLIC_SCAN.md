# UCIE Serial 4: one-command pinned public source scan

This command replaces long manual copy-and-paste scans. Select exactly one
approved public .ps1 or .py file with a 40-digit commit SHA and Git blob SHA-1.
The receiver verifies an existing Serial 4 signature, downloads one public
pinned file without redirects, checks the actual Git blob, and performs
inert AST analysis without running any downloaded source.

## One-shot Windows use

Run the script from a newly updated clean UCIE checkout; keep the
already signed owner-release checkout and ZIP untouched. Replace the
placeholder codeRoot with the real path to that clean updated checkout.

~~~powershell
$codeRoot = 'D:\UCIE\YOUR_CLEAN_UPDATED_UCIE_CHECKOUT'
$oldRelease = 'D:\UCIE\runtime\owner_release_main_81d935b1'
$py = 'D:\UCIE\.venv\Scripts\python.exe'

$options = @(
    '--repo', 'PowerShell/PowerShell'
    '--commit', 'dad69345f3fae3d0530f87ec73c8441649760483'
    '--path', 'test/powershell/Modules/Microsoft.PowerShell.Utility/Get-Command.Tests.ps1'
    '--blob', '766848c7a721c8724b39643d0e17ba5daa11c4c3'
    '--pack', "$oldRelease\build\UCIE_Selected_Four_Rule_Serial_4.zip"
    '--trust', "$oldRelease\.build_keys\production\public_production.pem"
)
& $py -B "$codeRoot\scripts\ucie_public_pinned_serial4_scan.py" @options
if ($LASTEXITCODE -ne 0) { throw 'UCIE_PUBLIC_SCAN_FAIL_CLOSED' }
~~~

The upstream PowerShell file is a regression TEST. With the exact
commit, Git blob, finding rule and line/column pinned to the observed case
(49:25), the V2 JSON now reports
`status=PINNED_UPSTREAM_TEST_EVIDENCE`, `candidate_count=1`,
`pending_manual_review_count=0`,
`pinned_upstream_test_evidence_count=1` and
`confirmed_new_bug_count=0`.

This is **classification of one already reviewed, exact upstream test**,
not a generic test-folder suppression. Any changed blob, changed position,
other rule or different test file remains
`UNVERIFIED_MANUAL_REVIEW_REQUIRED` pending human review.
The original candidate and provenance remain in the output. This is
neither an upstream bug claim nor evidence of broad scanner accuracy.

## Safety and evidence boundaries

- Only five independent approved repositories: python/cpython,
  PowerShell/PowerShell, git/git, modelcontextprotocol/python-sdk,
  actions/runner-images.
- Exactly one .py or .ps1 file per run, one pinned commit, one exact blob.
  No recursive scans, arbitrary URLs, project files, code execution,
  source storage, automatic fix, scheduler, or owner private key access.
- Source max 128 KiB, strict UTF-8, no URL redirects and exact Git blob
  verification before AST analysis.
- Existing Serial 4 signature and expiry are independently checked. The
  signed Rulepack's source SHA is immutable; this convenience consumer is
  a separate newer script, not part of the original signed code tree.
- Output contains source provenance, candidate positions and flags,
  not source bytes or claims of confirmed runtime defects. Test file
  paths are explicitly marked TEST_PATH. Exact upstream regression
  test evidence is labeled separately; generic test paths are NOT
  silently assumed safe. The additive V2 counts retain the raw finding count.
- Human/legal signoff, real-world accuracy estimates, fixed-release
  applicability, automatic approval, and external distribution remain
  unproven or disabled.
- A signed release expires after seven days. Do not automatically
  re-sign, reset its serial or bypass expiry.

The offline test file tests signatures (mocked), allowlists, Git blob
identity, test-context labeling, AST-only Python inputs, and redirect
rejection without external network requests or owner keys.
