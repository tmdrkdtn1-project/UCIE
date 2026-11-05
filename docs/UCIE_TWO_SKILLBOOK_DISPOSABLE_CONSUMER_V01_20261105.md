# UCIE SkillBook 001/002 — first-party isolated consumer draft V0.1

- Release-gate execution contract: [UCIE V1 six-gate development lock](UCIE_V1_RELEASE_EXECUTION_LOCK_20261105.md).
- Source pin: GitHub `main` `c41460cd708ca911b64330ccded603fae5e552f3`.
- **Status: FIRST_PARTY_DISPOSABLE_DRAFT_NOT_RELEASED. Phase 01 PARTIAL.**
- Not an external product, public ZIP, export approval, signed item, independent QA, license grant or finished SkillBook authoring pipeline.

## Actual implementation (reusing existing two chapters and recipes)

`src/ucie_miner/skillbook_two_recipe_disposable_v01.py` reuses existing **first-party** Python/Git recipes and their matching SkillBook 001/002 product builders. Each of the 4 source files is verified against its exact pinned main-commit Git blob SHA-1 (both original recipes **and both authored chapter/contract modules**). It then reuses the existing W01/W02-backed `compose_blueprint` to reconstruct the approved-public-source **candidate** metadata, checks IDs and evidence SHA against both authored books, and composes two honest draft artifacts: `SKILLBOOKS.md` (human-readable actual original chapters, claim categories, limitations and attribution) and `SKILLBOOKS.json` (source IDs/tags/digests, 4 chapters per book, callable/input/output contract, revision lineage, unapproved gates). This is a bounded recomposition of **existing UCIE-authored chapter content**, not new semantic synthesis or bulk upstream source copying.

`build_draft_bundle()` creates a deterministic **eight-entry ZIP** (`__main__.py`, two exact existing recipe modules, `SKILLBOOKS.json`, `SKILLBOOKS.md`, newly UCIE-authored `PRINCIPLE.json`, `PRINCIPLE.md`, and `MANIFEST.json`) **in memory only**. The new principle composer `skillbook_principle_composer_v01.py` is itself pinned to an exact first-party Git blob, verifies the existing two approved-public-source Library entries and original books, and **reclassifies/generalizes them into five new cross-technique chapters**, with Python's filename-return versus Git's count-only output explicitly distinguished. Manifest includes version/blueprint/principle IDs, composer identity, original product-source and recipe blobs, and every non-manifest member's SHA-256. Builder returns ZIP bytes plus a receipt; it never saves, signs, publishes or installs the ZIP. Its default CLI outputs a preview **receipt**, not a ZIP. The independently trusted caller must run `verify_draft_bundle_before_execution(raw, trusted_receipt_sha256)` **before** executing the ZIP; an executable cannot establish its own integrity from inside `__main__.py` before Python loads it.

**Windows CRLF compatibility and real integrity:** the initial exact PR#182 GitHub Actions run #42007051905 passed Ubuntu 2/2 and failed Windows 2/2 because Windows Git `autocrlf` checkout converts LF source to CRLF before the strict blob check. Source canonicalization was corrected to normalize *only* CRLF to LF **before comparing exact pinned Git blob identities** and to include canonical LF bytes in the ZIP. Bare CR, changed source, wrong hashes and larger files remain blocked. This is a corrected source validation defect, not a reduction in integrity requirements.

The ZIP can execute via a **disposable first-party test fixture**:
- `{"action":"git-summary","payload_hex":"204d2073796e7468657469632e74787400"}`: the existing Git `--porcelain=v1 -z` parser receives only supplied bytes (hex), never runs Git or inspects a repository. It returns only bounded counts, no names.
- `{"action":"scandir-synthetic"}`: self-creates a temporary directory containing two small UCIE-authored test files, invokes the original `bounded_regular_file_names` recipe and cleans up. The external caller cannot specify a directory.
- `{"action":"principle-synthetic"}`: runs **both original UCIE recipes** in the disposable independent process against UCIE-authored synthetic files/bytes and returns separate bounded counts **without filenames**. No caller path or Git command execution.
- Only these three exact JSON contracts are accepted. Reject duplicate keys, extra fields, approval/export forgery, noncanonical hex, >32 KiB input, modified source/package, unknown action and CLI options. Fail closed with exit code 2. No user/private path is opened.

Both methods are intentionally **synthetic/self-owned**, not permission to inspect an external project. The independent process tests actual Python `-I -B` ZIP invocation but still count as **UCIE first-party functional QA only**, not external independent approval.

## Windows owner-host test and current verification boundary

`tests/test_ucie_skillbook_two_recipe_disposable_v01.py` executes real Python subprocesses only in a freshly created `TemporaryDirectory`; no external network, live Git invocation or operating DB. The owner-host baseline first run was **8/8 PASS** on 2026-11-05, then **13/13 PASS** after CRLF and book/manifest integration. The current expanded package test is **19/19 PASS**, and the new authored principle composer has **10/10 PASS**. Six original Product/Library/Git/UI/W09/real-Git targeted test files returned **73/73 PASS**, for **102/102 bounded first-party tests**. Cases cover real isolated Python consumers, reproducible ZIP/manifest, canonical Windows checkout, source/claim drift, source-linked original cross-technique chapters, altered human/machine artifact, approval forgery, pre-execution whole-archive SHA checks and tampered `__main__.py` rejection **before it can be run**. Exact-head GitHub CI is checked separately; earlier branch head `dbc01b6` was 4/4 PASS but must not be applied to the newer code.

Current older SkillBook source consumers / W04 / W09 are unchanged. This branch neither runs an automated collector nor attempts to reconcile the owner's existing 15 modified tracked files.

## Remaining requirements to declare phase 01 COMPLETE

The two real authored SkillBooks, machine contracts, original approved-public-source identities, revision lineage and **one new original UCIE-authored cross-technique design principle with five chapters** now have a single source-anchored product compilation path. But Phase 01 remains **PARTIAL**: this is fixed curated deterministic technical generalization of two already-reviewed inputs, **not open-ended automatic inference on arbitrary newly collected evidence**; actual independent editorial review and an approved hand-off are missing. External independent QA, commercial rights/security review, owner release authorization and signed/versioned distribution still block Phase 03/04/06. No approval state has been promoted.

For any owner-local test, use only this one file via the existing approved UCIE test tool, or on an isolated, already approved UCIE checkout:

```text
python -B -m unittest discover -s tests -p test_ucie_skillbook_two_recipe_disposable_v01.py -v
```

Do **not** upload generated ZIPs, pass another project's directory, modify the public miner, add new scheduler jobs, auto-promote candidates or label this artifact approved.
