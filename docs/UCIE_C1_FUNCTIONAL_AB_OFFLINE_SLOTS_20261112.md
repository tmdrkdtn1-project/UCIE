# UCIE V3 B3/C1 — Functional A/B Product Slots, Rollback and Uninstall

**Date:** 2026-11-12 KST  
**Roadmap:** https://github.com/tmdrkdtn1-project/UCIE/issues/199  
**Status:** First-party source-backed **same-owner-host** A/B development and QA. **NOT a signed pair of customer releases and NOT C4 second-host acceptance.**

## Why this is not merely changing a string

PR #247 plus the owner's 2026-11-12 13:04 KST successful real
same-host full-product receipt established: source-matched UCIE wheel,
three offline external dependency wheels, cryptography AES-GCM smoke,
four first-party installed synthetic workflows, and Local V04 loopback
HTTP (all customer GO flags false).

This increment defines two **different executable first-party product
packages**, tested on entirely new isolated Windows venv slots:

| | Product A | Product B |
| --- | --- | --- |
| QA-only distribution version | `ucie-public-only-demo==0.1.0` | `ucie-public-only-demo==0.1.1` |
| Existing 4 UCIE pillar modules & Local V04 UI | Included | Included |
| Real new callable installed health function | **Absent** | **Present**: `ucie_miner.customer_installed_health_v01 --self-check` |
| New capability behavior | Four-pillar CLI only | Self-check **executes actual four-pillar first-party synthetic workflows** and issues bounded machine-read health proof |
| Wheel metadata, internal RECORD and SHA | Individually verified | Individually verified |
| Customer status | NO-GO | NO-GO |

The B-only `customer_installed_health_v01` source file is actually
added to the UCIE project in this PR. The A source variant is the bounded
UCIE owner-local package source inventory with this new module excluded.
The B source variant includes it. **A/B are temporary source-derived QA
variants**, not two independently tagged Git commit releases, not signed
software updates, and not customer-deliverable binaries. Their source
SHA256 values are retained in the owner-only receipt, not marketed as
reproducible official release tree identifiers.

## Strict lifecycle, when separately authorized

1. Recheck previously stored wheel capture/dependency installation and
   **actual full-product rehearsal** receipts. The prior receipts remain
   immutable; a missing/changed/falsely approved receipt fails closed.
2. Copy only the current bounded UCIE source inventory into **two
   separate UCIE-named disposable roots** under existing Git-ignored
   `D:\UCIE\downloaded\ucie_c1_ab_slots_*`.
3. Build two first-party PEP 427 wheels using Python standard library
   only; metadata is A=0.1.0 and B=0.1.1. Verify byte-for-byte all
   first-party members, SHA256 `RECORD` and the exact B-only added module.
4. Make a **separate corrupted copy** of the B candidate; its digest
   MUST fail verification before any slot activation. The actual B
   wheel remains intact. A candidate is never executed on failure.
5. In each newly disposable isolated Windows virtual environment,
   install exactly 3 previously captured official-PyPI SHA256-locked
   dependency wheels **plus its first-party A or B wheel**, using
   `pip --isolated install --no-index --require-hashes
   --only-binary=:all:`. Run `pip check`, confirm installed
   distribution version and the B-only module's absence/presence.
6. Run actual installed UCIE 4-pillar synthetic CLI and 127.0.0.1
   ephemeral Local V04 HTTP in each slot. Run **B's new installed
   self-check** and check its version, pillar evidence and all NO-GO flags.
7. Select A initially. Only when B tests PASS, atomically switch
   the **temporary selector** A→B. Then switch back B→A and re-run
   A's four-pillar and Local V04 smoke to verify safe rollback.
8. Actually run `pip uninstall -y ucie-public-only-demo` in **both
   disposable recipient environments**. Verify distribution METADATA
   and `ucie_miner` product module are no longer importable, then
   delete the entire temporary roots, wheels, requirements and venvs.
   A bounded **owner-local unsigned developer QA receipt** is written
   only after total success, without altering any prior receipt.

No owner Local V1 resident web server, scheduled task, public miner,
operating SQLite, unrelated project, external customer source, Cloudflare,
Git worktree/commits or customer license is touched.

**Security boundary:** The default preview is read-only and executes no
pip or external code. `--apply` would actually install/import approved
vendor wheels **inside disposable venvs on the same owner Windows
host**, and needs independent human opt-in. Disabling pip indexes is
not a substitute for a network-restricted guest OS or trusted vendor
signature/license approval.

## Safe owner PowerShell instructions

Read-only preview (no network/install):

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_functional_ab_lifecycle_v01
```

Expected readiness on the currently reported successful full-product
receipt: `READY_FOR_OWNER_FUNCTIONAL_AB_CONSENT`.

Only if the owner separately authorizes this full source-distinct A/B
product execution:

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_functional_ab_lifecycle_v01 --apply
```

The new independent typed phrase is:

`RUN_UCIE_C1_FUNCTIONAL_AB_SLOTS_ONCE`

Do **not** repeat successful earlier download, PR246 dependency Apply
or PR247 full-product Apply. A/B cannot overwrite a prior successful
A/B receipt.

Successful user-only receipt path:
`D:\UCIE\downloaded\ucie_c1_functional_ab_lifecycle_receipt_v01.json`

## Source parity observation — important release blocker

The owner UCIE source tree deliberately contains additional owner-local
workroom files. With the exact source index and bounded build recipe used
here, **owner Windows** constructed test wheels **A=197 / B=198** first-party
Python modules; **clean GitHub Ubuntu CI** initially observed **A=183 /
B=184** modules. These are not contradictory product functional results:
the first-party source inventory is deliberately dynamic and the owner
worktree includes additional modules. The original CI failure was an
incorrect hardcoded module-count minimum; the repaired test requires
**A count + 1 = B count = current environment's exact bounded source index**
and independently checks the full wheel member hash/RECORD manifest.
No local UCIE files were reset or deleted to make these numbers match.

**Do not use the extra owner-local modules to represent a clean, reviewed
customer version.** C1 technical rehearsal is not a substitute for two
pinned Git commit trees, source rights/lineage reconciliation and clean
recipient acceptance. Any 17 tracked owner modifications remain intact
and are not silently assigned production provenance.

## Verification levels / remaining blockers

Tests use **real UCIE first-party source** and build BOTH complete
temporary A/B wheels, verifying per-file source parity, distinct hashes,
B functionality and negative tamper. Test subprocesses are MOCKED:
GitHub/UCIE bridge tests do **NOT** execute pip, third-party vendor code
or actual Windows A/B venv switching. The new first-party installed
self-check function has synthetic behavior unit tests; real
A/B process tests require separate owner `--apply` as above.

Even if Apply succeeds, the result is **disposable same-owner-host
blue/green slot selection**, NOT an in-place customer upgrade, no
portable customer launcher/OS service install, and no complete
customer source/resource rights audit. The main `pyproject.toml`
is still version `0.1.0`; B `0.1.1` is a QA-only generated variant.

**Next V3 gates:** C1/C4 independent clean second Windows recipient,
reproducible **two reviewed source/commit release versions**, complete
install→upgrade→rollback→uninstall with recipient OS handling,
C2 security/SBOM/third-party license/NOTICE and publisher provenance,
C3 private signing/entitlement, C5 designated customer acceptance.

**Commercial verdict: `UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO`.**
