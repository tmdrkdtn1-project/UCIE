# UCIE bundled roadmap - 2026-11-08 (C0+C1)

Goal: full four-pillar UCIE as a proprietary private product supplied only to specifically designated customers. Synthetic development evidence cannot authorize customer delivery.

| Bundle | Included gates | Exit evidence | Current status |
| --- | --- | --- | --- |
| P0 operations | Hourly public collector, truthful Stage10 errors, Windows task/receipt binding | Two fresh exact TaskScheduler instances with Action201 zero and linked run receipts | TWO-CYCLE OBSERVED on 2026-11-08, not permanent outage proof |
| A product core | C0 four usable operator flows + C1 complete offline installation, update, rollback, uninstall | Four non-draft accepted workflows, complete components/dependencies/scripts/CLI/UI/docs inventory, clean isolated lifecycle | IN PROGRESS: four-pillar synthetic CLI, wheel smoke and staging integrity capsule |
| B independent assurance | C2 rights, security, dependencies + C3 signed customer license | Genuine rightsholder/third-party approval, NOTICE/SBOM, independent security QA, exact signed customer-bound bundle | NOT ACCEPTED |
| C pilot and launch | C4 isolated recipient lifecycle + C5 owner/customer acceptance | Real recipient install, four workflows, update, rollback, removal, same-hash owner GO | NOT ACCEPTED |

## This bundle A increment: C0 + C1 staging capsule

New source module: src/ucie_miner/customer_offline_capsule_v01.py.
It invokes actual first-party UCIE four-pillar *synthetic* workflows, combines the receipt with an existing source-pinned UCIE wheel in a bounded ZIP, verifies an exact first-party module inventory, wheel RECORD entries, preview CLI entrypoint and SHA-256 manifest. It rejects unsafe paths, duplicate archive items, symlinks, missing required modules, unexpected payloads, mismatched hashes and forged customer release states.

Artifacts are written only to UCIE/dist/staging and never overwrite existing capsules. The production UCIE runtime DB and Windows collector/task are untouched.

The disposable tests in tests/test_ucie_customer_offline_capsule_v01.py check tampering, unsafe wheel, forged status, and actual first-party synthetic execution. The dedicated clean GitHub Actions test tests/test_ucie_customer_offline_capsule_ci_smoke_v01.py (exact UCIE repository only) builds a real wheel offline, creates/verifies capsule, installs that wheel into disposable location with --no-deps, then executes all four synthetic product flows.

IMPORTANT: This ZIP is UNSIGNED STAGING ONLY, NOT a deliverable customer product. Third-party dependency wheelhouse is not included. Two SkillBooks remain unapproved. The full UI/scripts/docs/config/installer/updater/rollback/uninstaller and legal NOTICE/SBOM, independent security QA, customer license, signature and actual recipient acceptance are absent. An unsigned manifest hash is not publisher authentication. Do not publish this artifact or distribute it to customers.

## Developer-only invocation

When an approved first-party offline wheel exists in UCIE/dist:

    python -m ucie_miner.customer_offline_capsule_v01 --root D:\UCIE --wheel ucie_public_only_demo-0.1.0-py3-none-any.whl

Verify the real archive name returned by the tool:

    python -m ucie_miner.customer_offline_capsule_v01 --root D:\UCIE --verify UCIE_STAGING_<12-hex-sha>.zip

## Remaining required work to complete bundle A

1. Four genuine operator tasks with authorized inputs, version/source/rights displays, negative cases, and independent customer-style acceptance.
2. Finish, review and explicitly approve human-readable plus machine-readable SkillBooks; never export draft-only material.
3. Complete dependency wheelhouse, exact full-app components/CLI/UI/scripts/docs/config inventory, and real install/update/rollback/uninstall and failure injection with clean Windows acceptance.
4. Independently review rights/security and privately sign and license the exact same release artifact, then proceed through bundle B and C customer pilot.

Owner contract: docs/UCIE_FULL_PRODUCT_PRIVATE_CUSTOMER_RELEASE_V1.md
Issue: https://github.com/tmdrkdtn1-project/UCIE/issues/199
The 09:00 daily report remains PAUSED; hourly public miner policy is unchanged.
