# UCIE V2 B4 closed-loop original review learning cycle — 2026-11-26

This review-only development is UCIE-only and STACKED on Draft PR #368 exact parent a8b60a4d0c912c1f251b8f231f8f4a987ebd6376. It does not mutate owner Windows D:\UCIE, operating SQLite, source miner, V04, signed pack, 05:00 Task Scheduler or customer code.

This batch adds a **real UCIE-authored in-memory three-control experiment** to the history -> hypothesis candidate -> experiment -> feedback cycle. The executable is the already present `run_bounded_transfer(build_hypothesis())` which runs 3 self-authored synthetic MCP fixtures. The experiment is NOT the real upstream SDK, independent QA or validated customer outcome. Original cross-source privacy claim remains REJECTED even when bounded input transfers pass.

States:
- Empty history: 0 invented candidates, no test executed.
- Preview-only: zero fixtures and HOLD_NOT_RUN; no shell, no networking.
- Valid source-pinned history with no upstream-change alerts: run exactly 3 UCIE-authored tests once per cycle and attach `REVIEW_ONLY_SYNTHETIC_CONTROLS_MATCH` to 2 proposed bounded original hypotheses (NOT automatic approval).
- Source-change HOLD at ANY earlier history entry: no silent clearing despite a later synthetic success. The 3 fixtures can run but both draft candidates remain `HOLD_UNRESOLVED_SOURCE_REVISION`.
- Latest incomplete B5 paired synthetic fixture: `HOLD_INCOMPLETE_SYNTHETIC_PAIR`.
- Failure or mismatched test provenance: raises or explicit rejected control drift, never marks a PASS or adopts a rule.

A SHA-256 feedback report contains the exact history head, candidate proposal SHA and three observed control statuses. A digest is not an independent signature. No persistent effect, no automatic experiment schedule, no model training, no human study, no rights/release or production rule promotion. 14 focused first-party regression tests target source/receipt forgery, incomplete arms, synthetic HOLD, permission claims, and determinism. Draft CI should run zero paid runners until an explicit original full exact-head 4-OS/Python checkpoint. Parent CI success is not inherited.
