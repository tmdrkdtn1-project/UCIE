# UCIE V3 C1 — Owner-gated official PyPI wheelhouse acquisition (2026-11-11 KST)

**Project: UCIE ONLY. Roadmap: issue #199. Status: external dependencies not downloaded; customer full release NO-GO.**

## The blocker and the factual candidate

The source-bound UCIE `pyproject.toml` requires `cryptography>=50.0.2,<51`.
For the owner’s existing **standard Windows x64 CPython 3.15** development
target, official PyPI currently publishes a cryptography **50.0.2**
`cp315-abi3.abi3t-win_amd64` wheel. This is not an attribution of
cryptography's code to any of UCIE's five approved code-mining repositories.
PyPI is permitted here **only as an owner-approved dependency distribution
channel**, never a new UCIE public-evidence mining source.

The *fixed initial candidate set* (not approved redistribution rights):
- `cryptography==50.0.2` — direct UCIE runtime dependency.
- `cffi==2.1.1` — candidate native dependency for CPython 3.15.
- `pycparser==3.12` — candidate dependency of CFFI.

PyPI/cryptography public reference:
https://pypi.org/project/cryptography/50.0.2/
https://pypi.org/project/cffi/2.1.1/
https://pypi.org/project/pycparser/3.12/
Official pip download documentation:
https://pip.pypa.io/en/stable/cli/pip_download/

External package names and versions are pinned by UCIE source. This
**does not substitute** the externally sourced SHA256 values for owner
review. The acquisition compares downloaded wheel SHA-256 to the exact
official **versioned PyPI JSON** metadata, records hashes and the wheel
internal `RECORD` evidence. This is not an independent signature,
cryptographic publisher provenance, license/NOTICE signoff, SBOM,
malware audit, or complete dependency/ABI execution QA.

## Safe owner Windows commands

Run from any PowerShell directory; all actions are constrained to exact
`D:\\UCIE`, its existing `.venv`, Python 3.15 x64 and the fixed
approved quarantine. **No Python package is ever installed by this tool.**

### 1. Offline preview (default, NO NETWORK)

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_owner_wheelhouse_acquire_v01
```

Look for `OFFLINE_PREVIEW`. The command never downloads, runs pip,
inspects unrelated projects, touches the collector DB or starts a task.

### 2. One-time owner-authorized official PyPI DOWNLOAD only

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_owner_wheelhouse_acquire_v01 --apply
```

The tool refuses CI, other roots, non-owner Python executables, wrong
Python versions/architectures, noninteractive input, symlinked paths,
nonignored download storage, or existing wheelhouse/receipt. It prompts
for this exact phrase:

`ACQUIRE_UCIE_C1_WIN315_WHEELS_ONCE`

Only after that explicit owner input:
- `python -I -B -m pip --isolated download`, `--only-binary=:all:`,
  fixed target `cp315/win_amd64`, fixed 3 requirements, exact
  `https://pypi.org/simple` index, no cache, no input, no installation.
- Downloads are **temporary**, then bounded ZIP/WHEEL/METADATA/RECORD
  checks and exact PyPI official per-release SHA-256 comparison must all
  succeed. Any mismatch refuses promotion. Nothing is executed.
- Only matching wheel bytes are promoted to
  `D:\UCIE\downloaded\ucie_c1_offline_wheelhouse_preview\`.
- The locally generated UNSIGNED proof-of-bytes receipt is written to
  `D:\UCIE\downloaded\ucie_c1_wheelhouse_receipt_preview.json`.
- `downloaded/` is already ignored by the UCIE repo `.gitignore`.
  No vendor wheel should be committed or uploaded to public GitHub.

### 3. Offline byte-for-byte local re-verification

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_owner_wheelhouse_acquire_v01 --verify
```

The verification has **zero network and zero installation**; it compares
the quarantine contents and `RECORD` against the captured hashes and
rejects extra, missing, changed or linked files. Successful verification
only means local bytes still match an **unsigned PyPI metadata capture**.
Customer release remains false.

## What remains after acquisition

The acquired package bundle **must not** be called a complete customer
installer. Owner release authority must separately review the PyPI
provenance and all third-party license/NOTICE/SPDX records, platform
wheel tags and runtime compatibility, full transitive dependencies,
offline `pip --no-index --find-links` install in a newly isolated clean
Windows recipient, complete product resource closure, true different
full-product version A-to-B upgrade/rollback/uninstall, C2 security,
C3 signing/private customer entitlement, C4 recipient QA and C5
designated customer authorization.

We have **not** executed `--apply` on the user PC through the UCIE
admin bridge: that bridge explicitly does not allow arbitrary shell
execution. The owner must choose the one-time consent in PowerShell.
No automatic task restart, public miner, C40, Cloudflare, operating DB
or 09:00 report changes occur here. Two source-registry concepts remain
separate: acquiring a third-party runtime wheel for installation is
**not** approving a new technical evidence mining repository.

**Product verdict: UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO.**
