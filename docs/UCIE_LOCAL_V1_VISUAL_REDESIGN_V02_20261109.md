# UCIE Local V1 — four-pillar visual redesign V02 (2026-11-09)

## Scope and source pin

Design owner: UCIE 통합개발방. Product surface: existing owner-operated `http://127.0.0.1:18767/local` (port may change if owner chooses auto-port). User requested a UI overhaul **before** customer release preparation. Design source starts from `main` commit `7a5ee4832f4247648c308c5a28f3f882de748d3c`; no other project's visual assets, data, conventions or private files may enter UCIE.

**This is a scoped product UI redesign, not evidence of customer release readiness or independent browser acceptance.** The owner-operated Local V1 is already accepted within its existing local-only gates; the UI redesign needs its own acceptance separately before replacing a running instance.

## New design system

- **Navigation:** persistent dark desktop sidebar, 4 equal product routes + dashboard + governance; responsive horizontal navigation on smaller viewports; current-route indication and skip-to-content keyboard link.
- **Dashboard:** concise benefit-led headline and direct search/library actions; 2×2 task cards for *error prevention, development engines/skills, Virtual Library/SkillBooks, and evidence-backed revision*; separate trust/release-state strip.
- **Secondary routes:** consistent page header, typography, surface cards, focus states, highlighted source count/paging panels, and evenly sized, labeled search forms. Existing detail/review pages share the same shell.
- **Visual tokens:** warm near-white workspace (#f4f7fc), ink (#162640), midnight side navigation (#111d34), action blue (#255cd8), restrained turquoise highlighting, and warm-orange release HOLD signaling.
- **Desktop/mobility:** responsive breakpoints at 1100/880/640 px, touch-friendly inputs and links, CSS-only decorative graphic, readable long hashes/URLs, reduced-motion CSS. No external fonts, icon CDN, image requests, JavaScript, service workers or cookies.
- **Semantics:** HTML `lang="ko"`, page-specific `h1`, primary navigation labels, current-page markers, `main` landmark with skip target, explicit search labels and focus-visible outlines. The local-only and unverified/release-HOLD warnings remain legible rather than being hidden inside an icon.

Implementation:
`src/ucie_miner/local_v1_design_v02.py` (one static CSS and shell renderer),
`src/ucie_miner/local_v1_app_v01.py` (same routes/handlers and 4-pillar content presentation),
`tests/test_ucie_local_v1_design_v02.py` (first-party bounded HTML/UX contract tests).

## Invariants that this UI work MUST NOT weaken

- Exact existing `/local`, `/local/error`, `/local/engine`, `/local/library`, `/local/evolution`, `/local/policy`, `/local/review` and `/local/skillbook-run` semantics; no changed links to unapproved backends.
- GET-only local product handlers, bounded params, valid source URL checks, source-rederived public metadata and existing `UNVERIFIED_CANDIDATE_ONLY` labels; no POST/write/auto-correction/export.
- Existing CSP, strict `Host: 127.0.0.1:<port>`, local-only socket binding, cache-control/no-store, X-Frame-Options and no external assets.
- Existing 4-pillar owner product acceptance does not authorize a customer launch, code signing, permanent learning, automatic rule promotion, rulepack release or any project data transfer.
- Do not display a fixed 1,008 candidates as a live-changing dashboard metric. Snapshot counts remain source-ledger-dependent within existing read-only query screens.

## Acceptance plan, before replacement of running owner process

1. **Code:** exact GitHub PR HEAD 4-run CI (Windows/Ubuntu × Python 3.13/3.15), existing local product/route/safety tests plus new design contract tests, no changes to DB/task/collector. Avoid claiming unrelated HTTP test flakiness is resolved by CSS.
2. **Desktop UX:** owner browser opens existing Local V1 landing and searches 4 routes at 1440×900 and 1024×768; nav links, active state, safe source pages, distinct unverified labels and search/pagination/review actions all function. Screenshot/manual observation required: no screenshot was made by code-only CI.
3. **Mobile UX:** emulate 390×844 and 320×568; every route reachable by keyboard and horizontal navigation, no clipped buttons/headers, cards become one column, forms remain tappable, no horizontal page overflow. Confirm at 200% zoom.
4. **Accessibility:** keyboard skip link, focus ring, contrast, zoom, voice-control navigation labels and reduced motion reviewed with a real browser. CSS contracts are not substitutes for accessibility acceptance.
5. **Owner deployment:** `D:\UCIE` has known dirty tracked/untracked files. Do NOT `git pull`, `reset`, `clean`, overwrite `local_v1_app_v01.py` blindly or restart `UCIE-LocalV1-Web` until exact local file SHA/backups plus owner-safe activation are confirmed. CSS module/new tests can be staged independently but do not change the running `pythonw.exe` process on their own.
6. **Customer gate:** `ONLINE_RELEASE_AUTHORIZED=false`, `CUSTOMER_RELEASE_AUTHORIZED=false`, source QA/rights approval independent, existing 09:00 report HOLD.

Additional nested old catalog/SkillBook routes owned by the base renderer may use a different legacy page shell. They are a separate UI-completion acceptance item; do **not** treat the four local routes' new shell as proof that every nested page in the product has been visually migrated. Keep any follow-up migration scoped to UCIE and preserve its route/security contracts.
