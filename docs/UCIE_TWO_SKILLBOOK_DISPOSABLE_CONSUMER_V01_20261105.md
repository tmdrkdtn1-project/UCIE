# UCIE SkillBook 001/002 — first-party isolated consumer draft V0.1

- Release-gate execution contract: [UCIE V1 six-gate development lock](UCIE_V1_RELEASE_EXECUTION_LOCK_20261105.md).
- Source pin: GitHub `main` `c41460cd708ca911b64330ccded603fae5e552f3`.
- **Status: FIRST_PARTY_DISPOSABLE_DRAFT_NOT_RELEASED. Phase 01 PARTIAL.**
- Not an external product, public ZIP, export approval, signed item, independent QA, license grant or finished SkillBook authoring pipeline.

## Actual implementation (reusing existing two chapters and recipes)

`src/ucie_miner/skillbook_two_recipe_disposable_v01.py` reuses existing **first-party** Python/Git recipes and their matching SkillBook 001/002 product builders. Each of the 4 source files is verified against its exact pinned main-commit Git blob SHA-1 (both original recipes **and both authored chapter/contract modules**). It then reuses the existing W01/W02-backed `compose_blueprint` to reconstruct the approved-public-source **candidate** metadata, checks IDs and evidence SHA against both authored books, and composes two honest draft artifacts: `SKILLBOOKS.md` (human-readable actual original chapters, claim categories, limitations and attribution) and `SKILLBOOKS.json` (source IDs/tags/digests, 4 chapters per book, callable/input/output contract, revision lineage, unapproved gates). This is a bounded recomposition of **existing UCIE-authored chapter content**, not new semantic synthesis or bulk upstream source copying.

`build_draft_bundle()` creates a deterministic **six-entry ZIP** (`__main__.py`, two exact existing recipe modules, `SKILLBOOKS.json`, `SKILLBOOKS.md`, `MANIFEST.json`) **in memory only**. Manifest includes version/blueprint ID, both product-source blob identities, recipe blobs and every non-manifest member's SHA-256. The consumer independently checks complete file list, bounded sizes, SHA hashes, source identities, two SkillBook IDs, blueprint link and denial gates **before** executing the original recipe. Builder returns ZIP bytes plus a receipt; it never saves, signs, publishes or installs the ZIP. Its default CLI outputs a preview **receipt**, not a ZIP.

**Windows CRLF compatibility and real integrity:** the initial exact PR#182 GitHub Actions run #42007051905 passed Ubuntu 2/2 and failed Windows 2/2 because Windows Git `autocrlf` checkout converts LF source to CRLF before the strict blob check. Source canonicalization was corrected to normalize *only* CRLF to LF **before comparing exact pinned Git blob identities** and to include canonical LF bytes in the ZIP. Bare CR, changed source, wrong hashes and larger files remain blocked. This is a corrected source validation defect, not a reduction in integrity requirements.

The ZIP can execute via a **disposable first-party test fixture**:
- `{"action":"git-summary","payload_hex":"204d2073796e7468657469632e74787400"}`: the existing Git `--porcelain=v1 -z` parser receives only supplied bytes (hex), never runs Git or inspects a repository. It returns only bounded counts, no names.
- `{"action":"scandir-synthetic"}`: self-creates a temporary directory containing two small UCIE-authored test files, invokes the original `bounded_regular_file_names` recipe and cleans up. The external caller cannot specify a directory.
- Only these two exact JSON contracts are accepted. Reject duplicate keys, extra fields, approval/export forgery, noncanonical hex, >32 KiB input, modified source/package, unknown action and CLI options. Fail closed with exit code 2. No user/private path is opened.

Both methods are intentionally **synthetic/self-owned**, not permission to inspect an external project. The independent process tests actual Python `-I -B` ZIP invocation but still count as **UCIE first-party functional QA only**, not external independent approval.

## Windows owner-host test and current verification boundary

`tests/test_ucie_skillbook_two_recipe_disposable_v01.py` executes real Python subprocesses only in a freshly created `TemporaryDirectory`; no external network, live Git invocation or operating DB. The owner-host baseline first run was **8/8 PASS** on 2026-11-05, and after CRLF correction plus original human/machine artifact integration, the updated single-file test was **13/13 PASS on Windows**. Cases include two actual isolated Python consumers, reproducible archive/manifest, source CRLF invariance, mutated/bare-CR source rejection, chapter metadata/revision/rights consistency, modified authorship source refusal, tampered `SKILLBOOKS.json` refusal and untrusted path/approval flags. CI must be checked on the **final exact branch HEAD**, not the earlier failed commit; no all-OS CI PASS is inferred from the Windows owner result.

Current older SkillBook source consumers / W04 / W09 are unchanged. This branch neither runs an automated collector nor attempts to reconcile the owner's existing 15 modified tracked files.

## Remaining requirements to declare phase 01 COMPLETE

The two real human-authored chapters, machine contracts, original approved-public evidence identity and limited draft revision lineage **now have a single audited first-party packaging/consumer linkage**. But Phase 01 remains **PARTIAL**: the upstream evidence-to-*new* independently reviewed, genuinely generalized technical chapter pipeline has not been demonstrated across more than these two curated examples, nor has actual user-facing independent approved hand-off been granted. External independent QA, commercial rights/security review, owner release authorization and signed/versioned distribution still block Phase 03/04/06. No approval state has been promoted.

For any owner-local test, use only this one file via the existing approved UCIE test tool, or on an isolated, already approved UCIE checkout:

```text
python -B -m unittest discover -s tests -p test_ucie_skillbook_two_recipe_disposable_v01.py -v
```

Do **not** upload generated ZIPs, pass another project's directory, modify the public miner, add new scheduler jobs, auto-promote candidates or label this artifact approved.
