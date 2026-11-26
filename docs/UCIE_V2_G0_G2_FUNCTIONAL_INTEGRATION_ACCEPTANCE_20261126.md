# UCIE V2 G0-G2 Functional First-Use Integration and Next Review

Date: 2026-11-26 KST. UCIE ONLY. Status: DRAFT_ISOLATED_NOT_OWNER_DEPLOYED.

## G0: Source and route pins

- Base: PR #355 HEAD 8f612bb25fd441b8d7b42c68440d11bc9f71baca, CI run 45747119138 completed/success on 4 Linux/Windows Python 3.13/3.15 jobs. Never reuse that CI result for this PR.
- Old Local first-use model: src/ucie_miner/local_first_use_plain_v01.py Git blob 91b2b59262516894c2f9e9fcd99abf1ca76ec20a.
- Existing symptom intake: src/ucie_miner/local_question_intake_v01.py blob 7f6d5ac986075afe36815f87fa6f3a32e2f55a26; only /local/ask accepts a same-origin bounded 12-360 character POST for four fixed cases.
- Existing four-case guidance: src/ucie_miner/local_error_actionable_workflow_v01.py blob 2347602ed4b03198509c7bfd77f067c6388544c1.
- Existing real UCIE authored synthetic evaluator: src/ucie_miner/local_b2_connected_workbench_v01.py blob ee16a14b6447766e32487e82de533ea69a6ccd33.
- Existing GET handlers: src/ucie_miner/local_v1_app_v01.py blob c29fa4cc53c2d7a18e341a84139b92a9c8b51127.
- Design baseline PR #351, B1/B2 PR #352, B3 PR #353, B4 PR #354 and B5 PR #355 are all Draft and not merged. Owner original Windows worktree remains dirty; do not modify it.

## G1: Implemented source-only review functions

- New src/ucie_miner/ucie_v2_first_use_linked_v01.py: joins actual old three first-use destinations and 4-case issue/control UCIE synthetic results. For MCP case only, binds the same B1 capsule ID, SkillBook 003 source and state, B3 revision non-reauthentication status and bounded B4 original hypothesis. Other cases do not inherit the MCP capsule.
- Modified src/ucie_miner/ucie_v2_beginner_preview_v01.py: three-stage standalone preview now has actual fixed Local GET links for problem guidance, read-only safe examples, guide, public library and evolution. Its script does not POST, fetch arbitrary URLs, upload files or access personal code. Static file previews disable the existing-host links instead of constructing broken file paths.
- The existing Local V04 handlers, premium theme, routes, /local/ask POST policy, operating DB, scheduled tasks, signed rulepacks, C40/Tunnel and customer data are unchanged.

## G2: Exact-head acceptance

- New tests/test_ucie_v2_first_use_linked_v01.py asserts real B1-B4 identity/rights, four scenarios' actual synthetic results, fixed GET URL allowlist, truthful unsupported path, forged rights/source/revision rejection and basic keyboard/mobile markup.
- The test suite starts only a disposable 127.0.0.1 HTTPServer with an empty temporary UCIE .git root, then exercises existing local GET handler destinations and rejects foreign Host/Origin, unapproved POST and URL question data. It never connects to owner resident services.
- PASS only after this PR HEAD has completed GitHub CI on Ubuntu/Windows Python 3.13/3.15. Static HTML/CI cannot substitute for native owner Edge, 320/390/768/1024/1440 responsive review, actual browser 200 percent zoom, Korean-long-copy readability, screenreader or real first-user action.

## Next-work review: no B6 shortcut

1. If the exact-head G2 CI fails, repair only the observed failing contract and rerun CI on its new head.
2. If CI passes, conduct isolated real browser keyboard/zoom/route QA before any user success claim; actual owner Windows Edge requires separately authorized acceptance.
3. Then run consented 5-8 first-time coders and 2-3 technical reviewers on equivalent official-docs, ordinary-tool and UCIE tasks; record real correct-safe-action, time and wrong-confidence rates. Synthetic B5 reports are not actual human performance or buyer willingness.
4. Independently extend B4 generalization to a held-out approved-public technology case with negative controls and revision/rights lineage. The existing bounded source-linked prototype is not universal autonomous reasoning.
5. B6 C0-C5 rights, SBOM, signing, distribution, installer/update/rollback and actual clean-Windows customer acceptance stay NO-GO without owner approval.

DISPOSITION=G0_G1_IMPLEMENTED_REVIEW_ONLY__G2_PR_HEAD_CI_REQUIRED__OWNER_EDGE_AND_HUMAN_UAT_PENDING__B6_NO_GO
