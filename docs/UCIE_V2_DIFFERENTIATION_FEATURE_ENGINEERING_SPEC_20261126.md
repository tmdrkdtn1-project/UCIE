# UCIE V2 사업 차별성 구현 보완 — 기능 개발 명세 / 인수 Gate
2026-11-26 KST | PROJECT=UCIE ONLY
DOCUMENT_STATUS=OWNER_REQUESTED_FINAL_HANDOFF_CORRECTION__DESIGN_SPEC_NOT_IMPLEMENTED
PARENT=docs/UCIE_V2_OWNER_FINAL_DESIGN_DEV_HANDOFF_20261126.md
DESIGN_PR=https://github.com/tmdrkdtn1-project/UCIE/pull/351

## 0. 이전 인계 ZIP의 누락과 이번 수정의 목적

이전 ZIP은 '공식 출처·적용 버전·실제 시험·개정'이라는 **경쟁 전략을 설명**했지만, 그것이 UCIE 코드에서 **어떤 기능/입출력/사용자 경험으로 작동하고 어떻게 완료를 판단할지** 개발 티켓 수준으로 정리하지 못했다. 별도 UX 시안 구현만 먼저 지시하면 완전한 제품 대신 예쁜 안내 화면만 완성되는 위험이 있다.

**최종 개발 순서 변경:** '초보자용 격리 화면 제작'을 단독 첫 산출물로 삼지 않는다. UCIE가 이미 갖춘 source registry/4축 제한 워크벤치/SkillBook/자체 실험 결과에 결속되는 **기술 판단 캡슐(Verified Technology Capsule, 이하 '기술 확인 기록')** 1건을 먼저 실제 코드·테스트로 만들고, 그 결과를 쉬운 UI에서 보여주도록 **엔진+UX 함께 인수**한다.

사업적 기능의 기술 구현이 완성되지 않은 상태에서는 PR 또는 디자인에 '이미 경쟁 우위 확보', '자동 검증·개정 완료', '고객 코드 해결'을 표기하지 않는다. 경쟁 서비스도 skill search/eval/versioning/agent 기능을 제공하므로, **고객 문제에서 확실히 검증된 적용 조건+반례+재검증·권리 상태를 끊김 없이 전달한다는 성과를 정량 실험으로 입증**해야 한다.

## 1. 경쟁 위치: 차별화 가설을 '팔 수 있는 기능'으로 변환

| ID | 경쟁사가 이미 잘하는 영역(단독 차별화 아님) | UCIE가 추가로 입증할 고객 가치 | 고객에게 실제 보여줄 기능 | 내부 현재 상태 |
| --- | --- | --- | --- | --- |
| D1 기술 확인 기록 | Copilot·Cursor 등의 코드·해결책 추천 | 공식 근거와 정확히 시험한 적용 범위를 한 결과로 읽음 | '이 방법이 확인된 상황' / '아직 확인되지 않은 상황' / '공식 자료 보기' | **신규 결속 계층 필요**. 기존 분리형 메타데이터·시험 재사용 |
| D2 내 환경에 맞는지 확인 | 일반 검색·AI 답변과 SDK 버전 조회 | 자기 환경 버전에서 사용할 수 있는지 조건부 판정 | '지금 쓰는 프로그램에서도 될까요?' + '모르겠어요'; 모르면 HOLD | **신규 판정 계층 필요**, 고객 PC 자동 스캔 금지 |
| D3 실패를 미리 막는 확인 순서 | 정적 분석·보안 검사 및 일반 안내 | 이미 알려진 오류를 실제 수정 전 미리 점검하고 위험 행동 방지 | '먼저 확인할 일' 1~2개 + 잘 안 되는 경우 | 기존 4종 제한 /local/ask, B2 제한 사례 연결. 일반 실고객 코드는 미지원 |
| D4 기술서적과 작은 검증 예제 | Tessl 등 스킬 등록·평가·버전 관리 | 원리·단계·안전 제약·UCIE 자체 재현시험을 함께 전달 | '설명 읽기', '준비된 예제 체험', '시험한 범위 보기' | SkillBook 001/002·003 Draft + bounded authored trials; **공통 소비 계약 강화 필요** |
| D5 공식 업데이트 영향 추적 | 플랫폼별 changelog/레지스트리 관리 | 기술 변경 시 어떤 설명·예제의 기존 근거가 더는 유효하지 않은지 표시 | '이 방법은 바뀐 뒤 다시 확인해야 해요' | revision review/P11 일부 존재, **일관된 영향 매핑·자동 재시험 운영 미완** |
| D6 검증 상태·사용권 분리 | 기존 QA·스킬 보안 점수 | 시험 성공과 실제 고객 배포 권한을 구분해 실수를 방지 | 'UCIE 예제에서 확인' vs '고객용 배포 미승인' 별도 문장 | 여러 개별 gate 존재, **일관된 사용자 truth view 추가 필요** |
| D7 기술 정보의 지속적인 재사용 | 단순 Q&A 검색·생성 답변 | 같은 공개 기술의 수십 PR/중복 결과를 하나의 버전별 재사용 가이드로 | '한눈에 설명 읽기' + 출처·변경 이력 펼치기 | 기존 검색·SHA·중복 로직 재사용; **관련성/품질 한계 실증 필요** |
| D8 지정 고객 비공개 완전본 | 사설 배포·기업 보안 기능은 시장에 이미 존재 | 고객 파일을 외부로 보내지 않고, 근거가 남는 로컬 활용·정식 업데이트 | 설치·업데이트·롤백·사용 범위(미승인 시 UI 미노출) | Local V04 owner 인수, 상용 C0–C5/권리/서명/수신 환경은 NO-GO |

특허·독점적 우위는 입증되지 않았다. D1+D2+D3+D4+D5+D6를 **연결한 체험**에 대한 비교시험이 사업 가설이다. D8은 정책/릴리스 이후 기능이지 지금 출시할 상품이 아니다.

## 2. 구현 핵심: 기술 확인 기록 — UCIE_VERIFIED_TECH_CAPSULE_V01 (제안)

중복 원장을 만들지 않고 현재 public metadata, official document SHA, SkillBook authored contract, isolated test receipt를 **읽기 전용 조합 객체**로 묶는다. SQLite 영구 schema migration/운영 DB 쓰기는 별도 승인 전 없음.

**필수 계약 필드 (첫 버전의 합성/고정 출처 시험용):**
- capsule_id, case_id, domain, plain_korean_title, problem_intent
- provenance: approved_source_id, immutable_official_url, exact_release_or_commit, upstream_content_digest_if_verified, observation_at, source_kind (OFFICIAL_FACT/UCIE_INTERPRETATION)
- applicability: supported_os, exact_python_or_sdk_version, preconditions, explicitly_excluded_versions, unknown_version_hold
- ucie_owned_tests: recipe_id, tested_environment_id, first_party_test_sha256, positive/negative/control per-case receipts, actual_test_at, separately independent_qa_receipt if any
- human_help: simple_summary, safe_next_step, not_checked_plain_korean, skillbook_id, authored_recipe_id
- rights: license_review_status, customer_export_permission, owner_approval, revoked_or_stale_reason
- lineage: used_source_revision_ids, linked_skillbook_revision, dependency_ids, affected_by_changed_source; all values bounded, type-checked and provenance-linked.

**Status는 직교(axis) 상태로 관리한다:**
(A) 기술 판단 = PUBLIC_OBSERVED / UCIE_DRAFT / FIRST_PARTY_TESTED / INDEPENDENTLY_VERIFIED / STALE / WITHDRAWN
(B) 고객 사용·재배포 권리 = NOT_REVIEWED / NOT_APPROVED / LICENSED_FOR_SCOPED_RECIPIENT
(C) 실제 설치 환경 적합성 = EXACT_TESTED / KNOWN_MISMATCH / UNKNOWN_NO_PROOF
(D) 실행 결과 = PASS / FAIL / NOT_RUN / BLOCKED
'자체 시험 PASS = 내 문제 해결 = 사용권 인증' 같은 단일 green status는 금지.

**검증할 함수 계약(신규 이름은 제안이며 기존 코드와 중복 여부 재확인):**
- build_capsule_from_known_ucie_evidence(source: read_only, trial: trusted first_party_receipt, recipe: UCIE_owned) -> immutable validated capsule
- evaluate_applicability(capsule, explicit_user_environment_or_unknown) -> EXACT_TESTED | KNOWN_MISMATCH | UNKNOWN_NO_PROOF, safe_explanation
- explain_capsule_for_beginner(capsule, applicability) -> {what_this_might_help, what_was_tested, what_was_not_tested, next_safe_step, optional_evidence_link}
- map_upstream_revision_to_affected_capsules(approved_revision, current_catalog) -> affected_ids, why, required_test_ids, hold_flags; **처음에는 제안·미승인 작업**
- compare_experimental_test_receipts(before, after) -> environment_pinned_diff, failure_controls, truth_change; no automatic release.
- All functions default fail-closed. Input does not contain arbitrary customer source text, file path, token, actual customer environment or unapproved network URLs.

예상 유효 예: MCP SkillBook 003의 검증된 고정 Python SDK 버전, prompts/get의 제한된 memory-integration 성공·실패 통제군. 다른 버전, stdio/HTTP transport, 고객 환경/원본 코드 자동 진단, 라이선스·배포 허가는 명시적으로 UNKNOWN/HOLD. 실제 인수 전에 원본 라이브러리/영수증·테스트가 진짜 어떤 범위였는지 재조회하고, 확인되지 않은 숫자나 버전은 표기하지 않는다.

## 3. 반드시 연결할 4대 기능 사용자 여정 — 처음엔 사례 하나만

고객 첫 화면(P0): '코드가 잘 안 돼요' → 기존 허용된 네 가지 사례 중 하나와만 연결.
(1) **오류 예방:** 증상 선택/안전한 상황 설명 → 알려진 유사 기술 사례. '실제 PC 진단 아님' 표시.
(2) **개발 도구·스킬:** 해당 상황과 이어지는 UCIE 자체 고정 입력 예제/안전 확인 순서. 기존 B2/workbench 등 검증 범위만 사용.
(3) **도서관/SkillBook:** 사람이 이해하는 짧은 설명과 필요 시 '왜 이렇게 안내하나요?'에서 immutable official source와 tested version.
(4) **자체 개선/개정:** 공개 공식 원본에 변경이 생겼을 때 관련 예제/설명만 '다시 확인 필요' 표시 + 별도 격리 재시험 후보. 모형/미실행 상태를 실제 실행된 자동 업데이트처럼 보여주지 않는다.

**최초 end-to-end 사례:** 현재 존재하는 /local/ask의 mcp-prompts 고정 유형과 SkillBook 003의 검증된 SDK 레시피를 검토. B2 synthetic demonstration과 실제 MCP SDK memory trial을 혼동하지 말고, 실증 타입/조건을 분리한 capsule을 구성한다. 실제 환경이 불명확하면 Python scandir 등 기존 source-pinned 독립 레시피로 첫 사례를 축소해도 좋으나 그 선택과 이유를 남긴다.

**첫 단계 완료 판정:** 동일 case_id/capsule_id로 문제 설명·자체 시험/한계·SkillBook·공식 출처·개정 필요 상태가 **한 번의 탐색으로 일관되게 연결되는 실제 시험** 1개. 4개 화면을 단순 링크로 오가는 mock만으로 기능 완료를 주장하지 않는다.

## 4. 실제 개발 작업 백로그와 우선순위 — UX 단독 개발 금지

| 실행 단계 | 작업 항목 / 산출물 | 재사용 가능한 현행 코드 후보 | PASS 증거(조건) | 불가/권한 구분 |
| --- | --- | --- | --- | --- |
| B0 증거 잠금 | PR #351, main, actual owner staging, 4종 질문·001/002/003·P10/P11의 실제 계약 분석, 기존 오류·기술 자산 상태가 무엇인지 모듈별 표 | local_first_use_plain_v01, local_question_intake_v01, local_b2_connected_workbench_v01, skillbook_catalog_union_v01 | baseline_sha, owner original protected, route/tests inventory | 로컬 호스트 최신 상태 없으면 HOST_UNKNOWN, 다른 변경과 분리 |
| B1 Capsule Core | source/version/trial/rights/unknown을 결속한 UCIE-only immutable read-only capsule, typed validate, dedup, exact version hold | source_registry, library_entry/search, skillbook_principle_composer_v01, capability_trials | 1 verified-scope existing case; forged SHA/unapproved source/version unknown/rights missing negative tests; operating DB writes=0 | 사용권·QA 자동 승인 금지 |
| B2 Beginner Evidence Journey | B1의 **실제 같은 id/증거**를 세 단계 초보자 흐름에 연결한 별도 UI 시안; 상세에서 출처·시험·권리 확인 | local_first_use_plain_v01, local_question_intake_v01, local_b2_connected_workbench_v01, V04 isolated renderer | 네 가지 기존 질문 및 미지원·오류 동선; 거짓 '고쳐졌어요' 문구 0; 기존 V04 bytes unchanged | 신규 고객 코드 입력/업로드/다른 POST 금지 |
| B3 Upstream Revision Impact | approved source revision hash vs current capsule deps 비교, affected/unaffected set, stale mark & rerun *proposal* | skillbook_revision_review_v01, p11_closed_loop, library_upstream_review_v11, p11_retest | 바뀐 asset 1개 영향 검출, 무관 자산 1개 재시험0, missing provenance HOLD, negative controls | 실제 자동 job scheduling, DB mutation 없음 |
| B4 Verified reusable output | 사람용 SkillBook 1장+machine recipe contract+실제 UCIE-authored test receipts를 위 B1 같은 capsule으로 배포 준비 미승인 상태로 패키징 | skillbook_product_v01, skillbook_editorial_production_v01, skillbook_catalog_union_v01 | 동일 문서/테스트 버전 pin, replay idempotent, independent QA & rights clearly unavailable when so | 스킬 자동 승격/서명/상품 판매 금지 |
| B5 Measured substitution trial | 기존 공식 문서만으로 작업 vs UCIE로 수행, 실측 완료율/오인/소요시간/재검증 비용/실행 실패율 | 4종 first-use flows, new capsule/UX | 첫 코딩 사용자 5~8명 제안 표본, 기술 검토자 2~3명; 실제 전후 자료 + negative overclaim 0 목표 | 유료 수요·상용 단가 확정은 별도 |
| B6 Customer product gate | C0–C5 별도 owner 승인·rights/SBOM/signatures/installer/rollback/recipient acceptance | existing C1–C4 proof contracts | 실제 clean Windows recipient 4축, 설치·업데이트·되돌리기, 권리/고객 계약 | 현재 NO_GO, 무단 상용 배포/릴리스 금지 |

**첫 우선 개발 묶음은 B0+B1+B2**다. UI 시안만 만들어 끝내면 B1 미완으로 분리하여 FAIL/INCOMPLETE. B3/B4는 B1/B2 기존 기능 회귀 통과 후 병렬 분리 가능. B5는 실제 비기술자 사용성 시험이 가능한 환경에서 수행. 인력·날짜·원가 확정치는 미측정.

## 5. 고유 경제적 성과를 보여주는 측정 설계

기술이 많아졌다는 수집량·skill 숫자·CI 통과 횟수만으로 사업가치 평가 금지.

- 사용자 성공률: **지원된 대표 사례 범위**에서 다음 안전한 확인 방법을 올바르게 고르는 비율; '수정 완료'와 구별.
- 검증 진실성: FIRST_PARTY_TESTED만 있는데 INDEPENDENT나 CUSTOMER_LICENSED로 보이는 UI/JSON 조합 0. UNKNOWN에서 일치·실사용 가능으로 승격 0.
- 버전 적합성: known tested version / known mismatch / unknown 각각의 hold-out; 오탐·미탐 공개.
- 변화 대응 비용: 새로운 공식 revision이 왔을 때 변화 받은 capsule 개수, 재시험한 범위/시간, 무관 asset 재실행 수.
- 개발자/초보자 시간: 같은 문제에 대해 공식 문서·일반 가이드만으로 확인하는 과정과 UCIE one-flow를 비교한 **실제 분 단위 결과**. 느리면 UI/프로세스 다시 설계.
- 라이브러리 사용성: 같은 문제의 중복 공개 변경 기록이 검색결과 수를 부풀리지 않는지; 관련 기술서적·실험·출처로 한 번에 이어지는지.
- 로컬 자원·원가: UCIE 작업 CPU초·peak RAM·재시험 시간, 전체 PC 바쁜 상황에서 신규 작업 보류; **CPU/GPU는 로컬 사용료가 아닌 자원 경합/전기 및 장비 비용**.
- 실제 상업성: 경쟁제품을 이미 쓰는 고객이 '검증 범위/변경 후 재시험'에 돈을 내겠는지, 5~10명 이상 실제 잠재 고객과 비공개 완전본의 구매 조건·도입 장애를 물어보기. 이 숫자는 권장 조사 규모이지 수요 추정량 아님.

## 6. 기술 및 UX 부정시험 표본(개발방 필수)

1) official source URL만 맞고 pinned SHA 불일치 → HOLD.
2) 동일 문서의 최신 버전 미확인 → '현재도 안전/사용 가능' 금지.
3) 첫-party 합성 16/16 PASS만 있는 경우 → 독립 SDK/고객환경 PASS로 표시 금지.
4) SDK/version requested ≠ pinned tested version → UNKNOWN/KNOWN_MISMATCH + 친절한 다음 행동.
5) no-rights/license review → read-only 설명 허용, 배포·실행 CTA 금지.
6) stale/withdrawn public source → 기존 완료 표시 무효화, 판정 보류.
7) unapproved public repository or injected URL/text → 기존 collector allowlist deny, 표시에는 escape.
8) private token/path/customer code/error log → 현재 /local/ask privacy gate로 reject, 원문 반복·저장·Slack 전송 0.
9) duplicated source revision → unique capsule count 유지, 수정 이력만 갱신.
10) upstream changed unrelated feature → unrelated recipe retest not scheduled.
11) failed/timeout test → no automatic retry storm, source/owner tool read-only, no promotion.
12) claim/trial/SkillBook IDs mismatched → false join FAIL-CLOSED.
13) novice user asks “앱 만들어줘” → unimplemented scope clearly stated, no chatbot impersonation or fake generated code.
14) accessibility/UX → 320/390/768/1024/1440px, 200% zoom, keyboard, focus and 3-step flow; real Edge evidence or UX_PENDING.

## 7. 명시적 Next-owner 개발 지시

UCIE통합개발방은 **기존 시스템을 읽고, B0/B1/B2의 실제 기술 기능과 초보자 UI를 같은 source-pinned case로 구현**해야 한다. B2의 격리 UX 시안만 제작하고 '사업 차별성 개발 완료'라고 보고해서는 안 된다.

최초 코드 산출물 최소:
- UCIE 내부 기술 확인 기록 & 판정 모듈 1개 (기존 동등 기능이 있으면 확장·재사용)
- 그 모듈에 입력되는 실제 existing approved source+trial+SkillBook 결과와 시험 고정 fixture
- typed proof/rights/applicability state regression and fail-closed negative tests
- novice-result explanation/optional-proof evidence view integrated isolated prototype
- measured baseline vs UCIE trial methodology and a small real experiment when permissions allow
- no current V04 owner-frozen file changes, no host mutation, no DB/scheduler/auto-promotion/release.

**사업적 핵심 Gate**: ‘코딩 첫 사용자가 이유를 이해한 다음 행동을 선택할 수 있고’, ‘전문가는 실제 버전별 증거·미확인·권리를 검증할 수 있으며’, ‘엔진은 기술 변경 시 관련 자산을 보류/재검증 후보로 식별할 수 있다’의 연결이 **실제 사용 가능한 코드·시험·설명**으로 입증되었는지.

HANDOFF_ID=UCIE-HO-20261126-V2-BEGINNER-FIRST-01
DECISION_SCOPE=PREVIOUSLY_OWNER_LOCKED_STRATEGY_MADE_EXECUTABLE__NO_NEW_RELEASE_AUTHORIZATION
SOURCE_BOUNDS=UCIE_OFFICIAL_DOCS_AND_FIVE_APPROVED_PUBLIC_REPOSITORIES
NEXT_OWNER=UCIE통합개발방
DELIVERY_ACCEPTANCE=ENGINE_B1_AND_UX_B2_LINKED__SOURCE_VERSION_PROOF__NEGATIVE_TESTS__REAL_BROWSER_PENDING_IF_NOT_OBSERVED
