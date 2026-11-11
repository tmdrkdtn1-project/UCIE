# UCIE V3 C1 — Offline wheel metadata and full first-party source staging

**2026-11-11 KST · #199 · UCIE ONLY · source-only C1 acceptance, NOT customer distribution**

## Increment over PR #243

1. Instead of copying only **statically reachable** UCIE modules, C1
   preserves **every bounded indexed first-party .py source** under the
   two approved UCIE package trees (`src/ucie_miner`,
   `src/ucie_public`). Four-pillar source/UI/owner script/docs census
   from #242 remains in the staged snapshot as before.
   - The AST graph still measures reachable imports separately; a
     conservative whole-first-party file copy is NOT proof that every
     optional feature, data asset, platform service or runtime dynamic
     import works, nor proof of a customer-grade complete install.
   - No customer data, external repository, file outside exact UCIE,
     local operating SQLite or owner Windows task is read/modified.
   - The A/B disposable code revision loopback test continues to run
     in isolated `python -I -B` subprocesses and explicitly retains
     `full_product_code_version_upgrade_completed=false`.

2. **New** `customer_offline_dependency_gate_v01.py`: a callable,
   source-bound, read-only offline dependency preflight. Only the
   checkout's own `pyproject.toml` and optional fixed path
    `downloaded/ucie_c1_offline_wheelhouse_preview/` may be inspected.
   - The declaration is currently `cryptography>=50.0.2,<51` and
     `setuptools>=68` for the build system. These are declared
     ranges, NOT platform-specific locked/pinned wheels or SBOM.
   - Wheel archives are UNTRUSTED. The inspector rejects symlinks,
     unknown files, duplicate distributions, forged names, traversal
     entries, oversize/zip-bomb candidates, unsafe RECORD entries,
     mismatched filename vs METADATA identity or SHA256/size mismatch.
   - It does **not** install, import, execute, extract to a
     destination, fetch, sign or publish third-party code. The
     simulated test wheel is *inert first-party generated ZIP bytes*,
     not a redistributable cryptography package.
   - A cryptography wheel version outside the declared
     `>=50.0.2,<51` numeric family is explicitly unsatisfied.
   - Wheel `Requires-Dist` strings are only **observed**. Transitive
     pinning, external `cffi`/platform requirements, wheel tags,
     target Python 3.13/3.15 Windows compatibility, licenses, trust
     roots and security/SBOM review stay NO-GO even when metadata
     integrity validates.

3. Actual UCIE owner source observation at this checkpoint:
   - one declared external import root: `cryptography`;
   - two syntactically dynamic calls: `__import__("os")` in
     `ucie_miner.library_browser` and `__import__("argparse")`
     in `ucie_miner.library_quality_loop_v12`.
     Both are fixed standard-library targets; there is no observed
     variable target among **these two** calls. They still require
     platform/feature runtime acceptance and do not attest absence of
     other dynamic resources, imports, package data or plugin entry
     points.
   - at time of check, the optional bounded UCIE wheelhouse folder under Git-ignored `downloaded/` is
     **absent**. No dependency has been downloaded or silently
     accepted. Exact source snapshot/line numbers may differ between
     historical owner checkout and current GitHub main; each current
     site carries a source SHA256 in the inspection receipt.
   - this analysis does NOT make the installed owner Python environment
     a clean second recipient.

## Safe developer entrypoint

On the owner UCIE checkout only:

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_offline_dependency_gate_v01 --inspect
```

Expected process exit code is **2** regardless of observed wheels:
a metadata preview cannot authorize release. The printed report is
read-only and always `customer_release_authorized=false`.
No `pip install`, `--no-index` install, scheduler or user path input.

## Remaining C1/C2 commercial blockers

- Acquire separately approved, byte-hash-pinned offline third-party
  wheels *through the authorized owner channel*; do not automatically
  download or install from public/unreviewed sources.
- Verify complete dependency graph, target Windows/Python ABI and
  architecture tags, NOTICE/SPDX/license and security evidence,
  Microsoft/Windows recipient portable launcher and all non-code assets.
- Exercise **real versioned full-product** A→B offline install,
  update, rollback and uninstall in a **clean designated rehearsal
  recipient**, then complete independent functional and negative
  four-pillar acceptance.
- C2 rights/security, C3 owner signing/customer license, C4 clean
  recipient rehearsal, C5 owner-approved designated-customer pilot
  still require separate receipts. No customer keys/contracts issued.

Test scope: `tests/test_ucie_c1_offline_dependency_gate_v01.py`
plus expanded `tests/test_ucie_c1_portable_runtime_closure_v01.py`;
source-safe C0/C1 tests and frozen V04 owner tests must pass. Existing
owner tracked dirty files, resident localhost server, C40, PublicMiner,
operating databases, Cloudflare and 09:00 daily report HOLD unchanged.

**Final status: `UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO`.**
