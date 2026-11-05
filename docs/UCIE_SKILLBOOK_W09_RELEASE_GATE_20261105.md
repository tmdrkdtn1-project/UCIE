# UCIE W09 SkillBook 001 — release readiness (NO_GO), 2026-11-05

PROJECT=UCIE ONLY
LIFECYCLE=FIRST_PARTY_DRAFT_NOT_APPROVED
BROWSER=W09_RELEASE_GATE_PLAN_ONLY_NO_RECEIPT

## Purpose

Validate that the existing W08 first-party **synthetic** nine-case receipt
matches the exact current UCIE-authored \`skillbook_scandir_recipe_v01.py\`
source and Python documentation pin, while explicitly keeping independent QA,
rights, security review, owner approval, signing, release and all exports
**disabled**.

This is a **readiness/denial gate**, not a ZIP/package implementation,
source-code review certificate or authorization. The canonical JSON SHA-256
means a record is unchanged against its declared digest, NOT that a
third party independently proved test execution.

## Fixed checks

- All W08 fields and booleans must match a known bounded contract; extra
  approval flags, missing fields and noncanonical inputs are rejected.
- Recompute the receipt SHA-256 over canonical W08 JSON, excluding
  \`receipt_sha256\`.
- Check nine precisely ordered \`PASS\` synthetic case IDs; no skipped
  tests, bool-as-int counts, or changed test identities accepted.
- Check exact UCIE first-party recipe file SHA-256 against receipt. The verifier
  reads **only that fixed module source file**, not caller paths or private data.
- Verify official documentation digest, source registry, W08 fixed SkillBook
  ID and unapproved product state. A documentation pin is *not* proof of
  future release applicability or whole-system behavior.
- The verifier never accepts user-supplied file paths, never writes a ZIP,
  creates no signing keys, publishes nothing, and cannot self-approve.

## Blockers always stay open

1. Exact-head full 4-environment CI independently confirmed
2. Independent external repeat/functional verification
3. Security review and OS/platform threat-model confirmation
4. Ownership, licensing and redistribution rights
5. Explicit owner release authorization
6. Package signature and publication authorization

Even when receipt verification succeeds, the machine status is
\`FIRST_PARTY_RECEIPT_REPRODUCED_RELEASE_NO_GO\`, not \`APPROVED\`.
\`package_created=false\`, \`export_allowed=false\` and
\`portable_package_bytes_produced=0\` remain immutable.

## Manual on owner Windows PC

Default only displays blocked gates without executing W08:

    & 'D:\UCIE\scripts\ucie_skillbook_w09_preflight_v01.ps1'

Explicitly repeat W08 synthetic test and verify its receipt in memory:

    & 'D:\UCIE\scripts\ucie_skillbook_w09_preflight_v01.ps1' -RunSynthetic

The second command writes and deletes bounded test-only fixtures in the
system temporary directory; it does not scan real user folders or modify
the UCIE operating database. It prints a machine-readable QA provenance
report containing a report SHA-256.

Browse \`/skillbooks/release-gates\` (and \`.json\`) to view the **static**
blocker plan. Browser GET never executes a test or loads an owner receipt;
a browser page must not claim latest local W08/W09 PASS.

## Separate CI issue (must not hide)

The exact PR #177 W08 HEAD \`189fadd4874434cb10ca44480498415178d23d3a\`
failed Windows Python 3.13 CI twice due HTTP POST ConnectionAbortedError
\`WinError 10053\` in two different existing V02/V07 browser tests. W08
synthetic nine probes passed in those logs. The origin of the Windows
HTTP interruption remains unproven. CI complete-matrix signoff stays NO_GO.

No C40, scheduling, public miner, database or non-UCIE project changes.

## 2026-11-05: SkillBook 001 first-product independent review handoff

**Readiness evidence, NOT a third-party PASS.** This handoff reuses the
existing SkillBook code, product JSON, W08/W09 proof gates and W04 browser.
It does not create a separate automatic approval engine.

### Source identity and license evidence to inspect (not a legal verdict)

| Item | Exact official source to inspect | Known limitation |
| --- | --- | --- |
| API behavior | [Python 3.13 os.scandir](https://docs.python.org/3.13/library/os.html#os.scandir) and [Python 3.15 os.scandir](https://docs.python.org/3.15/library/os.html#os.scandir) | API docs describe iterator/context-manager behavior; UCIE's bounds and policy are its own claims |
| Pinned source bytes | `python/cpython` tag `v3.15.0` / `Doc/library/os.rst`; source SHA-256 `9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a` | Do not substitute latest moving online documentation for the pinned version |
| Python upstream license | [python/cpython v3.15.0 LICENSE](https://github.com/python/cpython/blob/v3.15.0/LICENSE), Git blob `20cf39097c68baa17cc566b64e76d34ebf034044` | Reading a license does NOT establish this product's redistribution rights |
| Documentation terms | [python/cpython v3.15.0 Doc/license.rst](https://github.com/python/cpython/blob/v3.15.0/Doc/license.rst), Git blob `47c4fa9d582de3ad794b24a192f4d9d6b6aa106a` | PSF License v2; documentation examples/recipes/code are also Zero-Clause BSD from Python 3.8.6 onward; attribution/rights for UCIE-authored code and any redistributed upstream content still require review |
| UCIE actual reusable implementation | `src/ucie_miner/skillbook_scandir_recipe_v01.py` SHA-256 `5053918a748a8b8ee26ca0ccdf811c11f67d55fd6135d5f9ab22e770463de26c` as previously recorded | Verify SHA independently at the exact PR head; a matching hash is identity evidence, not an approval |

### Independent reviewer reproducibility instructions

A reviewer **independent of the feature's author** should check out the
exact **reviewed commit SHA** from the already-public UCIE repository into
a disposable controlled environment and record the SHA, OS/runtime version,
Python interpreter executable/version, UTC time, relevant file SHA-256 and
the complete first-party unittest command/exit code. Do not scan the
owner's private files, request credentials, or access other projects.

Run the **existing tests**, not a newly invented laboratory, on the intended
matrix: Windows + Ubuntu/Linux, Python 3.13 + 3.15.

~~~text
PYTHONPATH=src python -B -m unittest discover -s tests -p test_ucie_skillbook_product_v01.py -v
PYTHONPATH=src python -B -m unittest discover -s tests -p test_ucie_skillbook_consumer_pilot_v01.py -v
PYTHONPATH=src python -B -m unittest discover -s tests -p test_ucie_skillbook_browser_v01.py -v
PYTHONPATH=src python -B -m unittest discover -s tests -p test_ucie_skillbook_catalog_union_v01.py -v
PYTHONPATH=src python -B -m unittest discover -s tests -p test_ucie_skillbook_w09_release_gate_v01.py -v
~~~

Those are environment-prefixed examples for Linux shell. On Windows set
`$env:PYTHONPATH = 'src'` in PowerShell, then run each
`python -B -m unittest discover ...` command separately. The existing
GitHub Actions offline matrix also executes the same tests via unittest
discovery. The `-p` pattern limits each local command to ONE file.

Required **linked product-flow observation**: the read-only /catalog
search returns `UCIE-SKILLBOOK-PY-SCANDIR-001`, the detail HTML links to
its `.json` contract, both record the same official source hash and
unapproved state, and the explicit CLI call returns `alpha.txt` and
`zeta.txt` from only UCIE's disposable three-entry fixture.
The CLI does not accept a real directory argument; no browser GET executes
the recipe; no live W04 read is required.

| Reviewer risk/negative gate | Acceptable independent evidence | Status pending third party |
| --- | --- | --- |
| 128 inclusive; 129 total entries | Exact result and rejection on both OS/Python versions | NOT_ATTESTED |
| Unicode file name ordering | Stable sorting of fixture names on both OS | NOT_ATTESTED |
| Early failure closes iterator | Test evidence for OSError/overflow closure | NOT_ATTESTED |
| Root symlink and Windows junction | Permission-aware independent attempt with OS details; skipped privilege tests stay UNKNOWN, not PASS | NOT_ATTESTED |
| Directory replacement / TOCTOU | Threat modeling: current recipe is NOT a security sandbox or atomic snapshot; no protection certification | NOT_ATTESTED |
| Origin rights and notice obligations | Reviewer checks tag-pinned PSF/0BSD terms, ownership of UCIE-authored implementation, and notices for any actual redistribution | NOT_APPROVED |
| Source identity and review independence | Reviewer's independently recorded test identity and role; distinct from first-party synthetic W08 receipt | NOT_ATTESTED |
| Human approval, signature, publishing | Explicit owner authorization and separate signing/release procedure | NOT_AUTHORIZED |

### How to record the external verdict

A future independent review receipt **must** identify a real reviewer or
reviewing organization, their independence from the implementation, exact
UCIE commit SHA, recipe and official-source hashes, matrix results, UTC
timestamps, test limitations/skips, reproducible inputs, and link(s) to
inspectable independent evidence. A synthetic self-test or CI run alone
cannot be converted into this receipt.

Do not write `independent_qa_verified=true`,
`license_redistribution_approved=true`, `human_approved=true`,
`security_review_approved=true` or `export_allowed=true` until the
respective independent authorized decision exists.

### CI incidents are not permanent product verdicts

The earlier 2026-11-05 CI incident above refers to an **older W08 head**
only. A later PR #177 head `53a4adf42444957a3673873f832313db9c53d3b8`
completed Windows/Ubuntu Python 3.13/3.15 CI **4/4 after one existing
Windows-3.15 HTTP-test failed-job rerun** (run `41987864443`). This
does not erase the original flaky HTTP incident, verify an independent
review, or attest any later commit. The exact current new head must have
its **own** finished four-platform CI before a current-head CI claim.

**Release remains NO_GO.** Package signature, independent verification,
rights/security approval, external publication and owner release permission
are all unchanged.

