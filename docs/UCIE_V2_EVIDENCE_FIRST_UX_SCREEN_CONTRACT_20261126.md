# UCIE V2 Evidence-first UX Screen Contract — 2026-11-26

STATUS=DESIGN_ONLY_NOT_IMPLEMENTED_NOT_VISUALLY_ACCEPTED
PARENT=docs/UCIE_V2_EVIDENCE_FIRST_PRODUCT_RISK_UX_FINAL_PROPOSAL_20261126.md
PROJECT=UCIE ONLY

## 1. Product identity and frozen baseline

The owner-fixed Premium Dark V04 visual direction remains unchanged. Actual V04 palette: canvas #08090c, surface #14161b, ink #f4f5f8, muted #a6abb7, line #2a2d37, restrained silver-lilac #b8c6f9, focus #b6c8ff; Korean system typography; satin rounded panels, no external assets or downloaded fonts. Never reintroduce the previously rejected gradient SaaS hero, orbit AI decorations, tiny technical paragraphs or decorative fake KPI dashboards.

Preserve existing navigation and routes: /local 홈; /local/error 문제 예방; /local/engine 개발 도구; /local/library 라이브러리; /local/evolution 개선 제안; /local/policy 이용 안내. Existing /local homepage and /local/evolution improvements are owner-frozen. This proposal does not change their bytes, approved functions or security rules. A separate isolated opt-in prototype and explicit acceptance must come before any replacement.

## 2. Five questions UX must answer

1. What specific coding, compatibility or maintenance problem am I dealing with?
2. Which language, OS, installed runtime or SDK version is it relevant to?
3. What can be trusted: official upstream fact, UCIE inference, actual first-party test, independent test, owner approval, customer distribution permission?
4. Which bounded technique, SkillBook chapter and test recipe could help, and where would they be inappropriate?
5. When technology versions change, what is no longer proven and needs rechecking?

The four UCIE pillars become one task path: search/problem → candidate & version → grounded explanation → test/negative example → safe reusable recipe and SkillBook → source and limitations → version-linked change review. The user may still enter each original pillar independently.

## 3. Desktop conceptual wireframe, 1440 px

+--------------------------------------------------------------------------+
| V04 sidebar | existing top bar / breadcrumb        search          help    |
| Home        |-------------------------------------------------------------|
| Prevention  | Which technology and version are you checking?              |
| Tools       | [specific problem or technology__________] [version] [find] |
| Library     |-------------------------------------------------------------|
| Improvements| result list 25% | selected result 47% | evidence panel 28%  |
| Guide       | tech / title   | one-line answer     | upstream source      |
|             | version        | applicability       | exact commit/sha     |
|             | actual status  | missing proof       | tests & negative     |
|             | relevant book  | next safe action    | rights / stale date  |
|             |-------------------------------------------------------------|
|             | related SkillBook / impact of changes / revision status     |
+--------------------------------------------------------------------------+

This is NOT a screenshot nor an implemented UI. Reuse V04 left navigation and top bar; construct the three-panel workbench only in a separately approved preview route. At 1024px show result/content with expandable lower evidence. Below 768px use a single-column sequence: search → result → evidence; on 390/320px never require page-wide horizontal scrolling. A long data table may scroll inside its own bounded container. No sticky panel may conceal keyboard focus.

## 4. Above-the-fold content and progressive disclosure

Priority: problem search and tech/version selector → one-sentence verdict → version/preconditions → uncertainty and missing test → one main action → collapsible proof. Never lead with SHA, machine enum, licensing jargon or candidate count. The user selects the version explicitly; UCIE may not inspect unrelated projects to detect it. Unavailable version must show '해당 버전은 아직 확인되지 않았습니다', not an invented supported range.

Search result card/row:
- Title in ordinary Korean phrasing; technical domain and *exact* version.
- Two distinct truth axes: '기술 검증: 검토 전 / UCIE 시험 / 독립 검증' and '배포 가능 여부: 미승인 / 승인된 지정 고객 범위'.
- One-line suitability and missing proof.
- A link to SkillBook, bounded recipe and reproducible test only where such objects actually exist.
- '근거 보기' exposes exact allowed upstream document URL, immutable commit or blob, source ownership/license, claim-vs-inference wording, test environment and digest.
- Group many revisions of one upstream topic instead of falsely counting each revision as an independent verified capability.

Basic view should show result, scope and next safe action. Expanded engineering view reveals complete test receipts, source hashes, supported and excluded environments, risk statements, positive/negative/control cases, revision lineage and input/output contract. This is progressive disclosure, not hiding a verification failure.

## 5. Detailed workbench tabs

A. 판단 요약: what the technique is, when it helps, required preconditions, cases not supported, exactly which version was tested. Explicitly distinguish official source facts from first-party UCIE authored hypotheses.

B. 시험 결과: first-party synthetic PASS is separate from actual upstream integration and independent outside QA. Show pass/fail/not-run, positive/negative/control counts, installed package/version and last timestamp. Do not summarize tests as 'safe' or score model hallucinations as certification. Running tests is a separately approved bounded local job; read-only GET must not execute tests or mutate local state.

C. 기술 자산: readable SkillBook chapters and distinct machine-readable contract (type, callable, input/output, failure, limits, dependencies, version). Show draft/unapproved correctly. No automatic export/publish/install of draft.

D. 원본 근거: source owner, immutable SHA, source release, license state, visible contradiction, original primary proof vs UCIE authored interpretation. Provide full digest for copying in detailed view but no customer paths/files/IDs.

E. 변경 영향: last tested date, upstream changes, affected recipes, next required re-test, deprecated or withdrawn cases. Future notices/subscriptions may appear only after a real approved delivery mechanism exists, never a decorative 'watching' switch.

## 6. Three real user stories to validate

New developer: 'os.scandir를 어떻게 안전하게 사용하나요?' Search → view Python 3.15 context → resource lifecycle and bounded directory enumeration → warnings about TOCTOU, symlinks and no atomic snapshot guarantee → SkillBook 001 → optionally inspect UCIE-authored synthetic demonstration. No access to their actual directories.

Maintenance engineer: 'MCP prompts/get errors after an SDK upgrade'. Select pinned versions v2.3.0 and the verified merged revision → distinguish missing prompt, missing argument, server internal error → inspect 16 actual in-memory SDK cases and their limits (no transport or full version-wide guarantee) → SkillBook 003 draft, exact evidence and next manual verification. No false declaration of released fix version.

Buyer/reviewer: 'Has this skill been independently tested and licensed for customer export?' Show four independent columns: technical applicability, first-party test, independent QA, distribution rights. No raw owner signing key or secret/customer identity in UI.

## 7. Trust-state language, not a single fake score

| Machine condition | Customer Korean text | Permitted action |
| --- | --- | --- |
| UNVERIFIED_CANDIDATE_ONLY | 공개 기술 사례 · 검토 전 | 공식 근거 보기 |
| UCIE-authored tests only | UCIE 자체 시험 완료 (시험된 범위) | 세부 시험 보기 |
| actual upstream tests but no independent QA | 지정된 버전 실시험 확인 · 독립 검토 전 | 테스트 한계 확인 |
| INDEPENDENTLY_VERIFIED with actual evidence | 독립 검증 기록 있음 (버전 표시) | 근거 보기 |
| STALE or unknown runtime | 현재 버전 적용 여부 미확인 | 재검증 필요 |
| RIGHTS_NOT_APPROVED | 재배포 권리 미승인 | 참고만 |
| RETRACTED or DEPRECATED | 철회됨 / 오래된 기술 | 신규 적용 금지 |
| CUSTOMER_LICENSED after C0-C5 | 지정 고객 사용권 승인 (범위 표시) | 범위 내 이용 |

A test pass is never a license; a source match is never an independent test; an owner-approved Local V1 shell is never a customer-exported SkillBook. Use textual explanation plus optional icon, not status color alone.

## 8. Accessibility and responsive design acceptance

- WCAG 2.2 AA target, normal text contrast >=4.5:1, non-text/status focus visibility, no keyboard trap, tab order follows reading order; lang=ko, main landmark, skip-to-content and visible aria-current navigation.
- Usable touch targets, real labels and error feedback; avoid icon-only controls. Use 2px visible focus perimeter with adequate state contrast as an enhanced design target rather than incorrectly labelling every AAA rule as AA.
- Validate 1440, 1024, 768, 390, 320 pixel widths; browser zoom 200%, Korean long titles without orphan fragments, long hashes without page overflow, reduced motion, text enlargement, screen reader basic route names.
- No external JavaScript/fonts/assets, no GET-based side effects or new POST unless separate security+owner approval. Preserve Host/localhost pinning, CSP, no-store, escaped HTML, bounded inputs, exact route semantics.
- Loading / no results / stale source / missing rights / blocked API / unsupported version require truthful explanatory copy and one next action. Never show an empty list as verification success.

Offline UI/UX Pro Max lookup was conducted for domain=ux queries 'dashboard navigation', 'status', 'data tables', 'contrast focus', 'responsive mobile table' and style design-system 'technical evidence developer knowledge dashboard'. Dataset suggestions are advisory, not applied; current UCIE V04 fixed palette and product decisions override external proposal colors.

## 9. UX validation plan and acceptance states

P0 STATIC_SPEC_ONLY (this document). No product source or CSS changed.
P1 ISOLATED_PREVIEW: one opt-in static mock with UCIE-owned approved public/first-party data, without modifying any frozen V04 route.
P2 SOURCE_TESTED: escaping/route/Host/CSP/no-store, statuses, empty/stale/long content, unsupported version and consent negative tests. Existing Local V04 regression must remain equal.
P3 REAL_BROWSER_REVIEW: actual Edge screenshots and keyboard navigation on 1440/1024/768/390/320, zoom 200%, nested SkillBook/evidence views, no clipped status or focus.
P4 SMALL_USER_TRIAL: proposed >=5 representative participants per iteration, covering junior/mid developer and reviewer. Compare same tasks against existing V04 baseline. Measure:
- Correctly understood applicability and missing proof: target >=80%, baseline measured first.
- False independent-test or commercial-approval interpretation: target 0 occurrences.
- Successful task completion and time to trusted evidence; no hard latency claims until real measurements.
- All critical tasks keyboard reachable, no page-wide horizontal overflow at named widths.
P5 OWNER_UI_APPROVAL: independent owner signoff and exact-source CI, then separately approved deployment. Browser UI approval is NOT commercial release or security/rights approval.

Current status: only P0 written; P1-P5 NOT_PERFORMED. No changes to existing V04, operator runtime, 3 old UCIE tasks, operating DB, C40/tunnel, other projects, customer code, auto promotion, owner release gates.
