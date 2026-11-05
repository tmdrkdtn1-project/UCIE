# UCIE SkillBook 001/002 — first-party isolated consumer draft V0.1

- Release-gate execution contract: [UCIE V1 six-gate development lock](UCIE_V1_RELEASE_EXECUTION_LOCK_20261105.md).
- Source pin: GitHub `main` `c41460cd708ca911b64330ccded603fae5e552f3`.
- **Status: FIRST_PARTY_DISPOSABLE_DRAFT_NOT_RELEASED. Phase 01 PARTIAL.**
- Not an external product, public ZIP, export approval, signed item, independent QA, license grant or finished SkillBook authoring pipeline.

## Actual implementation (reusing existing two chapters and recipes)

`src/ucie_miner/skillbook_two_recipe_disposable_v01.py` reads only the two **existing, first-party** Python recipe files pinned to the above source tree. For each it verifies its exact Git blob SHA-1 identity before packing. `build_draft_bundle()` creates a reproducible in-memory, four-entry ZIP (`__main__.py`, two originals, `MANIFEST.json`). The manifest includes source blob SHA-1 and each included member's SHA-256, version and unapproved release flags. The builder returns ZIP **bytes and a receipt**, but does not save, sign, publish or install anything. Calling its default CLI outputs a preview JSON receipt, **not a ZIP**.

The ZIP can execute via a **disposable first-party test fixture**:
- `{"action":"git-summary","payload_hex":"204d2073796e7468657469632e74787400"}`: the existing Git `--porcelain=v1 -z` parser receives only supplied bytes (hex), never runs Git or inspects a repository. It returns only bounded counts, no names.
- `{"action":"scandir-synthetic"}`: self-creates a temporary directory containing two small UCIE-authored test files, invokes the original `bounded_regular_file_names` recipe and cleans up. The external caller cannot specify a directory.
- Only these two exact JSON contracts are accepted. Reject duplicate keys, extra fields, approval/export forgery, noncanonical hex, >32 KiB input, modified source/package, unknown action and CLI options. Fail closed with exit code 2. No user/private path is opened.

Both methods are intentionally **synthetic/self-owned**, not permission to inspect an external project. The independent process tests actual Python `-I -B` ZIP invocation but still count as **UCIE first-party functional QA only**, not external independent approval.

## Windows owner-host test and current verification boundary

`tests/test_ucie_skillbook_two_recipe_disposable_v01.py` executes real Python subprocesses only in a freshly created `TemporaryDirectory`; no external network, live Git invocation or operating DB. The owner-host result of the first test run was **8/8 PASS** on 2026-11-05. Changing the pinned recipes fails closed rather than silently accepting unrelated source.

Current older SkillBook source consumers / W04 / W09 are unchanged. This branch neither runs an automated collector nor attempts to reconcile the owner's existing 15 modified tracked files.

## Remaining requirements to declare phase 01 COMPLETE

The two manual SkillBook chapters and runnable demos work, but phase 01 is still **PARTIAL** until the approved evidence-to-original-principle-to-chapter production contract, multiple-book version lineage, and actual accepted consumer hand-off are verified for the bounded publication scope. Independent QA, risk/license/security review, owner authorization and versioned distribution still block phase 03/04/06.

For any owner-local test, use only this one file via the existing approved UCIE test tool, or on an isolated, already approved UCIE checkout:

```text
python -B -m unittest discover -s tests -p test_ucie_skillbook_two_recipe_disposable_v01.py -v
```

Do **not** upload generated ZIPs, pass another project's directory, modify the public miner, add new scheduler jobs, auto-promote candidates or label this artifact approved.
