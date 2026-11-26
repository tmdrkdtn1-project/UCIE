# UCIE V2 Virtual Library revision-feedback learning candidate v01

Scope: UCIE-only review branch stacked on PR #367 exact head c7d976e3f02ddc429c15d0dfc9be086a6d930ed8, main remains untouched.

## New owner-original bounded feedback engine
`src/ucie_miner/ucie_v2_hypothesis_reassessment_v01.py` reads the **actual** 32-entry maximum, existing source-pinned, hash-checked original SkillBook/engine ledger through `validate_review_history`. No arbitrary web sources, customer inputs or model-generated texts. It can produce two conservative, explicit first-party **review proposals** from the original negative lesson: (1) transfer bounded inputs only with **source-specific output privacy guards**, and (2) re-test only MCP synthetic in-memory target with positive, negative and control fixtures. These are falsifiable human-authored templates with deterministic candidate IDs, not AI-discovered universal principles.

For each history event, validate exact revision status, fixed approved source IDs, changed/affected assets, allowlisted test filenames and review-only status. If **any older entry** shows unverified changed-source HOLD, do not clear the HOLD because a later synthetic success has arrived. A later incomplete paired fixture is a separate HOLD if no older source-change HOLD exists. The engine proposes affected-only tests, never executes/schedules them. History and negative lessons remain unmodified; output is a SHA-linked proposal containing history head and candidate derivation.

Data/rights/QA boundary: no GitHub access, operating SQLite writes, live task changes, network, trained weights, independent QA claim, source revision authentication, automatic rule promotion, owner Edge browser check or B6 release. Actual source revisions need external independent approval before invalidation can be cleared. Source-specific output privacy difference is an explicit counterexample that prevents over-generalization.

Regression tests include empty, duplicate, active, incomplete, unresolved old HOLD, affected-only tests, deterministic SHA, fake source SHA and fake test commands, forged lifecycle and source IDs, and absence of user/private or production claims. Ordinary ACG Draft push should allocate 0 Stage1 runners; one exact-head 4-environment acceptance is required. Existing parent CI passes cannot be carried onto this SHA.
