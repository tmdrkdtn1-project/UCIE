# UCIE Evidence Workbench V03 — operator UI direction (2026-11-09)

## Why V02 was not acceptable

The owner supplied the actual running V02 screenshot. The visual problem was structural, not a lack of polish: a generic gradient marketing hero with concentric "AI" decoration, oversized 2×2 rounded action cards, repeated release disclaimers and English micro-labels competing with short Korean tasks. The headline visibly wrapped into an orphan syllable ("로."). Entering a feature exposed more severe reading problems: source URL, version claim, SHA-256, verification status and human review guidance were crowded into consecutive prose paragraphs; SkillBooks, editorial drafts and public candidate revisions looked too similar.

**The workbench intentionally rejects** gradient/orbit AI decoration, decorative KPI dashboards, faux-live verification percentages, fake approval badges, icon-only navigation and multiple-card walls. This is a UCIE-only design, not a copied aesthetic from another project.

## Chosen visual identity — engineering editorial / evidence ledger

- **Materials:** warm technical-paper background (`#f0efe9`), dark charcoal/evergreen navigation rail (`#1c2927`), near-black typography (`#202a28`), ruled off-white data surfaces and limited oxidized-copper accent (`#a33e26`). Strong contrast; no rounded pills, gradients, remote fonts, external images, client-side JavaScript or tracking.
- **Typography:** Korean system body at 15 px / 1.7; work titles 30–49 px with intentional line wrapping (`word-break: keep-all`), monospaced tiny *record numbers and technical codes only*. Avoid making technical paragraphs all monospace.
- **Information order:** user action first, then actual data, then evidence & validation limits. The main index is a four-row catalog, not four unrelated cards. Every row opens an existing real route.
- **Home:** meaningful read-only GET query to the existing error search, 4 equal numbered product areas, then compact LOCAL/EVIDENCE/RELEASE trust ledger. Preserve old owner-local acceptance but do not imply customer release.
- **Error prevention & evolution:** a single search toolbar followed by a bounded results ledger. Each candidate groups source/domain, version *claim*, public URL, exact SHA, UNVERIFIED status, optional UCIE-authored review plan and a single manual-review action. Do not confuse many revisions against one PR with unique verified defects.
- **Engine:** stacked selectable technique rows with readable descriptions; selected results use a simple two-column `dl` of operation counts and precise boundaries. No invented performance claims.
- **Virtual Library:** explicit `SHELF / 01` SkillBook drafts, `02` editorial review candidates, `03` public source candidate revisions; keep different approval domains separate, not merged into one total.
- **Manual review:** source identity and exact version/sha claims as a short evidence ledger; safe-fix proposal, regression plan, owner tasks and NOT_VERIFIED gates each form a distinct visual section.
- **Nested catalog/SkillBooks:** purely CSS restyle the already-produced safe HTML envelope. Existing data validation and link schemes unchanged; tables are horizontally scrollable with readable cells and long SHA/URLs wrap. Keep the `v02` skin attribute for existing acceptance-test compatibility, but replace its visual CSS through the V03 implementation.

## Safe implementation and compatibility

- New isolated module `src/ucie_miner/local_v1_design_v03.py` is the single visual source. Prior V02 module remains intact and importable for deterministic rollback. Only the UCIE-owned `local_v1_app_v01.py` presentation source connects V03; **no new routes, POST actions, external fetch, source allowlist or approval mutations**.
- All data values continue being HTML-escaped by the established `_e` function; all public review URLs are still source validated and bounded upstream. Keep exact `/local/*` route paths, GET query max lengths, paging limits, host/CSP/no-store, nested safe envelope and parent catalog replies.
- Parent/legacy nested pages still undergo only a static CSS insertion; no arbitrary HTML rewrite of candidate text or source content.
- Do not hardcode 1,008 into live UI: the owner-visible source count changes over time and different ledgers are not interchangeable.
- Keep local running service, scheduled task, collector DB and all other owner files untouched until exact PR-head CI and SHA-based owner code deployment approval.
- `tests/test_ucie_local_v1_design_v03.py` checks indexed rows, no marketing decoration, source ledger semantic grouping, bounded GET-only search, safe nested parity and mobile CSS contracts. Existing V01/V02 regression tests must also pass.

## Visual acceptance gates not established by CI

The code and synthetic tests are necessary but do **not** demonstrate that browser text, line height or interactive targets actually appear correctly. Before V03 owner acceptance, obtain screenshots in the *running* Edge instance at:
1. Dashboard: 1440×900 and 928px-wide owner view. No orphan headline, obvious direct actions and balanced white space; 4 task rows distinguishable without overdecorated cards.
2. Error results: search query `python` with 10 results, original URL/hashes readable, UNVERIFIED clear, review action visible.
3. Unified Library: `/local/library?q=Git` with the three shelves and one multi-record list; no repeated generic box walls.
4. Manual review, engine, evidence evolution and nested `/catalog` / `/skillbooks` detail, preferably long hashes / tables.
5. Responsive viewport at 390×844 and 320×568, 200% browser zoom, tab/shift-tab/keyboard-only and 1.5x text/contrast. No unexpected horizontal page overflow; nested tables can scroll within their own container.

**No browser screenshot or visual acceptance is automatically implied by GitHub CI or localhost HTTP responses.** Record failures as actionable CSS/markup changes; do not invent acceptance evidence.

## Release boundary

LOCAL_OWNER_ACCEPTED for the *existing* Local V1 product only; V03 owner GUI design acceptance remains PENDING. Technical candidate source-linked status is not independent testing. Automatic rule promotion, licensing/re-distribution approval, security signoff, code signing, online/customer publication all remain NO_GO. The existing 09:00 report hold remains in force.
