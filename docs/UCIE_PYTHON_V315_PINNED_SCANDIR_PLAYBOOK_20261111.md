# UCIE B1/B2 — Python os.scandir official tag + selectable safety playbook (2026-11-11 KST)

## Product increment (not another diagnostic-only PR)

The existing V04 Python workflow can now present **two useful UCIE-authored
safe-call patterns** from the same real four-pillar product without running,
reading or modifying a caller's project. The selectable URL is:

- `/local/engine?purpose=PYTHON_SCANDIR_SAFE&case=single_owner`: one consumer with `with os.scandir(...)` and explicit lifetime
- `/local/engine?purpose=PYTHON_SCANDIR_SAFE&case=shared_guarded`: two consumers, one lock on `next()`, workers joined before iterator close

Both cases show **original UCIE example source text** and a practical
"avoid" explanation. The existing user-initiated engine action continues
to run the **same** four-file UCIE-owned temporary synthetic fixture for
both scenarios. Case selection changes the **guidance, not the test**.
This does **not** execute the displayed snippet, a caller path or any
upstream code. The existing `/local/guide/python-scandir[.json]` now
shows machine-readable allowed case names and source/rights provenance.

## Primary official public source — separate evidence grains

1. Publisher/source: approved `python/cpython`.
2. Exact annotated `v3.15.0` tag resolves to commit
   `d220409a13b77de7a6c30abe16ea90db01528edc`.
3. Official tagged `Doc/library/os.rst`:
   https://github.com/python/cpython/blob/v3.15.0/Doc/library/os.rst
   Git **blob SHA-1** `74419ee7f3588f1baec83c85b05716e6388719e3`.
   The section documents `scandir()`, context-manager protocol,
   explicit `close()`, and version-added context manager 3.6. It notes
   a distinct change to `scandir(-1)` in 3.15, which this feature
   **does not run or certify**.
4. Official tagged root `LICENSE`:
   https://github.com/python/cpython/blob/v3.15.0/LICENSE
   Git **blob SHA-1** `20cf39097c68baa17cc566b64e76d34ebf034044`.
   The license text describes PSF License Version 2 for Python and
   documentation and dual PSF/Zero-Clause BSD for documentation examples
   starting 3.8.6.
5. The existing `https://docs.python.org/3/library/os.html` URL is a
   **moving reference**. Its HTML byte snapshot or revision is **NOT**
   pinned by the Git blob above. The tagged RST source is independently
   identifiable, but that does not imply current site HTML equals it.

**Critical evidence distinction:** the CPython documentation attests
`with` / `close()` behavior at a particular source tag. The suggestion
to use one guard around concurrent `next()` calls and join all workers
before closing is an **UCIE-authored defensive usage pattern**, not an
upstream race-fix claim or proof that a given interpreter release has a
specific race/patch. The version applicability of any concrete upstream
concurrency fix remains unknown.

## Licenses, security and approval gates

- A tagged LICENSE text was read, **NOT** reviewed and approved for a
  specific commercial customer derivative or dependency inventory.
- UCIE sample source is first-party; no upstream example text was copied
  to the code snippets. License notices and third-party attribution are
  required to be evaluated separately before any private commercial release.
- No automatic SkillBook promotion, execution of untrusted public code,
  persistent index, new collector, source allowlist, task/scheduler/C40
  modification, runtime DB write, external API fetch, paid hosting, customer
  data or unrelated-project access.
- `human_approved=false`, `export_allowed=false`,
  `auto_promoted=false`, `customer_release_authorized=false` persist.
- Source SHA-1 here refers to the **Git object**, not SHA-256 of
  current website HTML, nor a signed license clearance receipt.

## Acceptance / rejection cases

Run first-party regression
`tests/test_ucie_python_scandir_pinned_playbook_v02.py` and the existing
`test_ucie_python_scandir_guide_integration_v01.py`,
`test_ucie_w03_w04_local_library_flow_v01.py`,
`test_ucie_local_v1_product_v01.py` and
`test_ucie_local_v1_design_v04.py`.

- Positive: both exact selector values in fresh isolated Local V04;
  source tag/hash and owner-written sample code visible; guide JSON
  retains unapproved and missing-license/independent-QA gates.
- Negative: unknown case, case parameter for MCP engine, forged source
  approval/license signoff, HTTP POST, invalid query and forged Host
  fail closed.
- Owner D:/UCIE: install source only after exact local SHA comparison,
  new-file ABSENT leases and backup; **do not restart resident task
  automatically**. GitHub Windows/Ubuntu Python 3.13/3.15 4/4 CI
  and local source tests are not resident server acceptance. Any live
  resident reload must be separately owner-controlled and observed.

Related roadmap: https://github.com/tmdrkdtn1-project/UCIE/issues/199
