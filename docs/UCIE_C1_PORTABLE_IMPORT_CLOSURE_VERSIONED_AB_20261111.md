# UCIE V3 C1 — portable UCIE-only preview, bounded AST import closure and A/B code-revision rehearsal

**2026-11-11 KST · Owner roadmap #199 · Source-only product engineering · NOT a customer installer or release.**

## Why

PR #242 closed a real **23-file selected component census** and a copy/tamper
lifecycle of two *identical* UCIE source snapshots. It did not cover the
transitive Python imports, external dependencies, recipient-compatible
localhost execution or code-different update/rollback.

This increment adds new first-party modules, without changing the frozen
`/local` home, `/local/evolution`, owner task, public collector or
`D:\\UCIE` Local V1 server.

## 1. Source closure beyond fixed 23 components

`customer_runtime_closure_v01.inspect_static_runtime_closure()`:

- Only scans Python files under exact `UCIE/src/ucie_miner/**` and
  `UCIE/src/ucie_public/**` in a UCIE Git checkout. Never scans customer
  source, sibling project repositories, user home, `.venv`, `runtime`,
  external network or linked services.
- Indexes bounded, non-symlinked first-party Python files using `ast`
  parsing; never imports/executes the examined source during census.
- Traverses static local imports from **the actual C1 portable preview,
  Local V04 app, four-pillar CLI staging and UCIE public CLI** entry modules.
  Includes required package `__init__` modules.
- Records reachable files, external library import roots, unresolvable
  first-party imports and importlib/`__import__` call sites. Missing
  first-party static imports **block the executable preview**.
- Unresolved optional/dynamic imports, dependency versions, resources
  reached through string-based loading, and third-party wheelhouses
  **are not declared closed**. A source SHA256 is not a signed artifact.

The selected 23 first-party components remain included for the C0 census
but are NOT conflated with the computed runtime import closure.

## 2. Portable path independent loopback preview

`customer_portable_preview_v01` is NEW and separate from the existing
owner-bound Local V1 `main()`. It requires a new **UCIE-named disposable
folder**, an exact `.ucie_c1_staging_only` marker and a strictly empty synthetic `.git` directory (no owner Git
history). Existing V04 handlers require this checkout-shaped marker.
A populated `.git` is rejected by the portable entrypoint.
It therefore will not launch on the operational owner `D:\\UCIE`.

- The module locates its own UCIE root from `__file__`, not a hardcoded
  drive or provided project source path.
- It binds only `127.0.0.1` on OS-assigned port `0` and shuts down
  after a bounded, local HTTP self-probe.
- The probe exercises actual V04 home navigation, health, Python guide
  JSON, both selectable `os.scandir` engine examples with UCIE disposable
  synthetic inputs, and POST rejection. There is **no browser launch,
  background daemon, TaskScheduler work, public tunnel, customer scanning
  or user-provided paths**.
- It explicitly does not inherit the existing owner Local V1 approval as
  a customer/recipient acceptance. Other source-backed UI flows that require
  operating evidence ledgers are not claimed as standalone validated.

## 3. Actual distinct executable source A/B rehearsal

`exercise_real_revision_ab_preview()` creates two *new* UCIE-named
directories under one temporary folder. Both start from the same source
closure and fixed approved-first-party file census.

- **A:** the real source `customer_portable_preview_v01.py` contains
  `UCIE_C1_DISPOSABLE_GENERATION_A`.
- **B:** only a freshly copied A source is modified to contain
  `UCIE_C1_DISPOSABLE_GENERATION_B`. It is actual different runnable
  first-party Python source bytes, NOT a separately reviewed/released
  product commit. The SHA256 digests must differ.
- A and B each run in a fresh `python -I -B` child process with only
  the staged `UCIE/src` inserted for first-party imports. The actual
  V04-local HTTP routes must respond and the child must output the
  *correct version marker*.
- Before B can be used, one staged B source copy is deliberately
  altered and the manifest verification must reject it; A must remain
  intact. The correct B copy is restored and launched, then an isolated
  A child is re-launched to confirm rollback behavior.
- All temporary files are automatically removed; no actual installed
  customer product, signed package, wheelhouse, contract, recipient,
  TaskScheduler task, persistent DB or deployed service is modified.

**Exact claim:** A/B source *bytes and the executable preview revision
marker* differ and the isolated staging transition is tested. **This
does NOT validate a full-product different-Git-commit A→B upgrade or
customer installer/update/uninstall in a clean second Windows recipient.**

## 4. Genuine remaining C1–C5 blockers

The following stay **NO-GO**: optional/dynamic package closure and
runtime data assets, declared third-party wheelhouse and hashes, SBOM,
portable Windows service startup and actual user/UI release packaging,
reviewed rights/NOTICE, approved customer SkillBooks, signing/key custody,
private entitlement, real whole-product version upgrades, clean recipient
acceptance and actual designated-customer contract/pilot.

Run only source-only tests:
`tests/test_ucie_c1_portable_runtime_closure_v01.py`.
Local owner test isolation uses a fresh UCIE temporary directory and
does not require or permit a restart of the running owner
`UCIE-LocalV1-Web` task. Failure is **FAIL**, never auto-promotion.
The 09:00 daily report remains on HOLD; the hourly public miner is
unchanged.

Roadmap: https://github.com/tmdrkdtn1-project/UCIE/issues/199
