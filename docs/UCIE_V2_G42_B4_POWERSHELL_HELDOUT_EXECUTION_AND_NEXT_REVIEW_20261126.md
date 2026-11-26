# UCIE G4.2 + B4 new PowerShell held-out acceptance batch

Date: 2026-11-26 KST. PROJECT: UCIE ONLY.
Disposition: ISOLATED_REVIEW_ONLY. Owner Windows V04 / customer release: HOLD.

## Baselines: checked real read-only evidence

- UCIE public main at f5fbaca6c94f50130941570090c2c555cf92d816.
- Parent G4.1 PR #358 at b1640cf8a14e984515b08a64b63036069f8edac4; actual isolated Windows Edge 20/20 and Windows/Ubuntu Python 3.13/3.15 4/4 PASS on that specific HEAD. No approval of live owner V2 UI.
- Existing B4 parent: source-linked original Python scandir and Git porcelain SkillBooks, a restricted MCP case, not autonomous reasoning. Existing PowerShell local B2 authored synthetic cases were confirmed, with ALIAS_SHADOWS_COMMAND and EXPECTED_CMDLET_CHOSEN.
- Public vendor documentation: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_command_precedence?view=powershell-7.5
  - No path / loaded case precedence: Alias, Function, Cmdlet, External executable.
  - Unknown module load state and path qualification cannot be treated as the same condition.
  - Get-Command -All reveals shadowed commands; Get-Command -CommandType Cmdlet narrows discovery.
- Explicitly approved PowerShell/PowerShell repository: tag v7.5.4, annotated tag object SHA 3c5be61fff97fad6d2daf9c6cf9fc3dcf66aae63 and dereferenced COMMIT 7c8d9e7e0ed2fc1f2caf50746fe9fef720ca2a0a.
  - Inspected original file src/System.Management.Automation/engine/CommandDiscovery.cs Git blob e07520a1238db6c5e511153e06a05103d2fa15f1.
  - Inspected MIT LICENSE.txt Git blob b2f52a2bad4e27e2d9c68a755abb74cb8943f2fa.
  - No bulk source copy; MIT existence is not UCIE customer redistribution clearance. The live Microsoft Learn page is NOT content-hash immutable and is distinct from the pinned implementation file.
- Live owner UCIE-only readonly bridge capabilities: scoped source/document inspection, no arbitrary shell, no automatic service restart/push, no graphical owner Edge interaction.
- Live owner git status: DIRTY; never clean, reset or overwrite. Readonly docs:
  - docs/UCIE_LOCAL_V1_OWNER_EXECUTION_LOCK.md SHA256 e6c92334494e9c4dc3c5c746682a14fa8e8ca9ef20ff125aafe1f86cce201e0c
  - docs/UCIE_V04_PREMIUM_DARK_CUSTOMER_UX_20261109.md SHA256 f8399f24b017ea14797d09d5385203acacba5bf4d1354afe096acaa335f98cdb
  - No writes. Observations are at review time, not perpetual owner PASS.

## Implemented B4 new independent technology case

- First-party bounded module src/ucie_miner/ucie_v2_b4_powershell_heldout_v01.py reuses actual B4 parent hypothesis and existing B2 PowerShell reports, checks their source/status/rights, and creates an original held-out conditional inference.
- New original human SkillBook draft, machine test recipe and source/license/version lineage. The source is approved, the *candidate result is NOT approved*.
- New finite typed-commands resolver on UCIE-authored data only: maximum four from Alias/Function/Cmdlet/Application, optional explicit requested type. Six real Python synthetic trials:
  1. Alias shadows loaded Cmdlet;
  2. explicit Cmdlet type filter selects intended type;
  3. Function shadows Cmdlet;
  4. unknown module loaded state is HOLD;
  5. path-qualified command requires another rule, HOLD;
  6. unavailable requested command type is HOLD.
- It rejects false generalizations such as every name already loaded, first observed command always intended, all paths sharing unqualified precedence, and limited data processing providing a security sandbox. It never invokes user shell commands or owner/customer data, or trains/publishes/promotes skills.
- Regression tests include original provenance, parent B4, rights false claims, mutation/duplicate/unsupported inputs, source replacement, negative controls and first-party limits.
- Disposable Windows native PowerShell smoke: scripts/ucie_v2_b4_powershell_native_heldout.ps1 in new pwsh -NoProfile process, adds one temporary authored Get-Date alias shadowing existing Get-Date Cmdlet, observes default/typed/All discovery, removes alias. Actual runner version reported; source v7.5.4 mismatch keeps exact version QA unverified. This is FIRST-PARTY NATIVE observation, not verified upstream source implementation.
- New dedicated Windows Github workflow and receipt. General four-matrix CI on this PR HEAD is separately required.

## Implemented G4.2 source-only owner gate

- src/ucie_miner/ucie_v2_g42_owner_edge_preflight_v01.py accepts exactly a redacted source-pinned observation shape; anything forged, unrecognized, stale or claimed to authorize V2 live owner UAT fails closed.
- Current actual observation: parent G4.1 GitHub Edge success; dirty owner Windows tree; read-only source bridge; owner V2 handler installation, actual owner Edge walkthrough, rollback, separate V2 activation signature NOT verified.
- Output remains OWNER_EDGE_V2_DEPLOYMENT_AND_UAT_HOLD. No personal files, logs, accounts, passwords, private repository probes, new routes, installer or customer data.
- Separate regression suite covers all approvals, missing/extra fields, bool-as-int, stale SHA, self-attestation and no-go preservation.

## Gates and next development review

- Source/CI first: new PR exact head GitHub Windows native + 4 environment source regression; old parent CI cannot validate this PR.
- Scientific B4: source-pinned proposal + executable first-party bounded experiment is NOT autonomous semantic discovery, independent upstream tests, version-matched PowerShell 7.5.4, legal approval or portable release. Later independent reviewer verifies tagged file and native observed runner-version differences, then approved-source new transfer with additional counterexample.
- Owner G4.2: actual V2 Edge on owner host requires separately authenticated owner V2 approval, installed handler exact SHA/health/port, preserved dirty worktree, reversible backup/rollback, original V04 CSP/POST/four user journeys and native owner Windows Edge screenshot with keyboard/320-1440/zoom 200%; NONE is granted by isolated Edge runner.
- B5 first-time coders and technical experts, and separate buyer interviews remain real-human-observations=0. No fabricated improvement benchmark.
- B6 C0-C5 private customer signing/install/update/rollback/rights and release NO-GO.

No merge, host modification, operating DB/task change, other project access, automatic promotion, model training, C40 change, signing or customer delivery.
