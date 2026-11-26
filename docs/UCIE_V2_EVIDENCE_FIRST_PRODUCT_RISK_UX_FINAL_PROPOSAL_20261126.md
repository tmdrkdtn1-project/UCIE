# UCIE V2 — Evidence-to-Action 통합 제품·리스크·UI/UX 최종 개선 설계 제안
2026-11-26 KST | PROJECT=UCIE ONLY | STATUS=FINAL_PROPOSAL_OWNER_REVIEW_REQUIRED

**이 문서는 검토용 설계안이지 이미 구현된 제품/최종 소유자 승인/실제 배포를 뜻하지 않는다.** 현재 승인된 4대 동등 목표(오류 예방, 엔진·스킬·학습 로직, 가상도서관/SkillBook, UCIE 자체 개선)를 모두 보존한다. 고객 지정 비공개 상용 완전본만을 목표로 하는 기존 출시 정책은 변경하지 않는다.


## 2026-11-26 고객 관점 재정의 — 최우선 사용자: 바이브 코딩 첫 이용자

**사용자 의견을 반영해 이전의 개발자·유지보수 전문가 중심 UI 방향을 철회한다.** 최우선 고객은 Python·Git·MCP·SDK·버전을 몰라도 AI를 이용해 무언가 만들어 보려고 시작한 사람이다. 이 고객은 기술의 SHA와 호환성 증명보다 **'무엇을 눌러야 할지', '내가 막힌 곳에서 무엇을 확인해야 할지', '지금 못하는 것은 무엇인지'**를 먼저 알아야 한다. 전문 엔지니어·기술 감사자는 세부 자료를 여는 **2차 사용자**다.

제품 제공 범위는 바꾸지 않는다: 현행 /local/ask는 12~360자 입력과 **네 가지 대표 문제의 제한된 분류**를 수행하며, 자유형 AI 상담/코드 자동 생성·수정이 아니다. /local/ask의 기존 제한적인 동일 출처 POST는 구현되어 있다. 이전 UX 초안의 모든 경로 GET-only 표현을 **정정**한다. 질문 입력과 개인 코드/비밀정보의 공용 축적 금지는 그대로. 첫 사용자 UX는 기존 local_first_use_plain_v01.py의 세 가지 안전한 진입점과 기존 질문/예제/가이드 링크를 우선 재사용한다.

**초보자 기본 경로는 세 열의 전문 기술 검토 작업대가 아니라 1열·3단계:** '어떤 도움이 필요하세요?' → '비슷한 문제를 찾았어요/찾지 못했어요' → '지금 확인해 볼 일'. 출처/시험/라이선스는 '왜 이렇게 안내하나요?'로 접어두되 미검증과 무허가 내용은 상단에서 숨기지 않는다. 코드 자동 수정/자유 AI 대화가 가능하다고 암시하는 문구나 실행 버튼을 만들지 않는다.

사용자에게 보여주는 용어·실제 문장과 상세 화면 구조는 다음 두 문서를 정본으로 한다.
- docs/UCIE_V2_EVIDENCE_FIRST_UX_SCREEN_CONTRACT_20261126.md — **초보자 전용 1열 UX 계약으로 수정**
- docs/UCIE_V2_BEGINNER_COPY_DICTIONARY_20261126.md — **UI 모든 핵심 메뉴/버튼/입력/결과/예외/주의문구의 쉬운 말 사전**

기존 소유자 승인 Premium Dark V04, /local과 /local/evolution의 frozen source/route/nav는 **별도 프로토타입 → 실제 초보자 사용성 시험 → 소유자 승인** 전까지 변경하지 않는다. 쉬운 말 시안이 기존 제품 4축 중 하나를 누락시키면 실패다. 이번 PR은 문서만 수정하며 실제 GUI 개선·브라우저 QA·운영 설치 성공을 주장하지 않는다.

## 0. 검토에 사용한 현재 상태·고정 조건

- 2026-11-25 확인 main f5fbaca6c94f50130941570090c2c555cf92d816: CORE REST 요청 레이트 예산을 실제 HTTP opener에 결속한 소스 병합, Windows/Ubuntu Python 3.13/3.15 CI 4/4 성공. **운영 호스트에 배포 또는 활성화됐다는 주장 아님**.
- 로컬 관리자 연결 응답(2026-11-26): UCIE_LOCAL_ADMIN_BRIDGE_READY. 원본 UCIE 작업 트리에는 추적 수정·많은 미추적 파일이 남아 있다. 해당 원본을 reset/clean/force pull/덮어쓰기 금지. 새 개발 루트의 단일 원본 모듈 인계 성공 기록은 있으나 기능 동등성/실운영 cutover는 HOLD.
- 제품: Local V1 owner local acceptance(2026-11-08), 4개 실제 로컬 사용자 경로 /local/error, /local/engine, /local/library, /local/evolution. Premium Dark V04 외관과 /local 홈 및 개선 제안 UX는 기승인·동결 경계. 아직 지정 고객 완전본 상용 출시 NO_GO.
- 스킬서적: 001 Python scandir·002 Git porcelain은 UCIE 작성된 제한형 레시피/설명/계약, 003 MCP prompts는 고정 SDK 실제 메모리 내 상호운용 검증을 포함한 DRAFT. 모두 고객용 독립 QA·사용권·서명·배포는 별도.
- 2026-11-25 로컬 기록: 출처 연결 공개 후보 1,447개, 64개 4분야 합성 사례 시험, 자체 관측과 수집 건수는 승인된 기술/성능 통과량과 다르다. 후보 재사용·자동 개정과 현업 정확도는 미검증.
- 소스 경계: 공식 Python/PowerShell/Git/Windows/MCP 기술 문서·릴리스·보안 권고 및 승인 5개 repo python/cpython, PowerShell/PowerShell, git/git, modelcontextprotocol/python-sdk, actions/runner-images. 고객 비공개 코드/다른 프로젝트/연결앱/대화/원시 데이터는 UCIE 전역 지식으로 수집 금지.
- 기존 고정: owner 지정 고객에게만 완전본을 비공개 상용 라이선스로 배포(별도 계약·권리·보안·서명·수신 검증); V04 외관은 무단 변경하지 않음; 권한 없는 자동 규칙 승격/모델 훈련/배포/신규 스케줄러/수집 범위 확장 NO_GO.

## 1. 차별화를 만드는 제품 주장과 피해야 할 주장

### 차별화 가설: Version-Specific Evidence-to-Action Assurance

고객에게 단순한 'AI가 생성한 코드/스킬'이 아닌 **한 기술 판단에 대해 공개 원본·정확한 버전·유효 조건·재현 가능 테스트·반례·미확인 범위·후속 변경 시 재검증 대상**을 함께 제공한다. 사람이 읽는 SkillBook과 기계가 읽는 독립된 안전 실행 계약을 같은 claim/test/evidence lineage에 연결한다. 고객은 적합 환경 확인 → 원리 이해 → 허용된 재현 시험 → 배포 가능 상태를 명확히 알 수 있다.

초점: **기술이 여전히 맞는가 / 그 버전에서 작동하는가 / 실패 시 무엇이 위험한가 / 업데이트하면 무엇을 재검증해야 하는가**.

경쟁사 중복 인정: GitHub Copilot은 Skills+MCP 코드 리뷰; Cursor는 이벤트/스케줄 기반 에이전트; Tessl은 스킬 품질·보안 평가·버전/회귀 평가; Sonar는 AI 코드 품질 보증을 이미 제공. 단순 스킬 목록·보안 점수·LLM 요약·자동 코딩·버전 기록만으로 독보성 주장 금지. 그들이 '전혀 하지 못한다'고 단정하지 않으며, **공식 upstream change + 실제 전후 실행 증거 + 기존 skill/호환성/권리의 유지의무 + 모델 독립 로컬 소비를 통합한 경험**을 품질·재현성으로 비교해야 한다.

고객 가치 가설:
1) Python·PowerShell·Windows·Git·MCP 혼합 환경의 마이그레이션/운영 담당자: 새 API/버전의 실사용 전 검증.
2) AI 코드 생성/리뷰를 쓰는 개발팀: 잘못된 코드 제안보다 '기술 적용 가능 조건 + 테스트 가능한 계약'을 얻음.
3) 승인/규정 증거가 필요한 작은 엔지니어링 팀: 출처, 시험, 검증 주체, 보류 이유를 독립 확인.
제품 제공 형태는 별도 단일 규칙 판매가 아닌 **지정 고객용 UCIE 4축 완전본**의 핵심 사용자 여정이며, 계약상의 범위·지원·업데이트는 분리 과금 여부를 검증한다.

## 2. 개선된 엔진 아키텍처: 7개 부품·하나의 공통 증거 그래프

전체 파이프라인(고객 코드 업로드 없음):
승인 공개 소스 → 출처/라이선스 레지스트리 → 정규화·SHA 중복·공식 버전 → CLAIM/EVIDENCE/TEST 그래프 → 의미·가치 후보 평가 → UCIE 소유의 bounded 재현시험 → SkillBook 원고/기계 계약 → independent QA/rights/security/owner gate → 버전 고정된 로컬 소비 → upstream 변경 영향 그래프 → 재시험/개정/보류.

### 구성요소와 재사용

| 구성 | 기존 UCIE 기능 활용 | 개선(신설은 최소화) | 보장할 경계 |
| --- | --- | --- | --- |
| A. 공개 소스 게이트 | source_registry, public miner, shared_core_quota | 원본 revision SHA·권리 상태·API rate budget 실제 fetch 경계 단일화 | 5개 승인 repo+공식 자료 외 deny |
| B. Canonical Evidence Store | SQLite public ledgers, library_entry, library_exact_index, source audit | claim_id / source revision / source SHA / parser version / retention/retraction 관계 인덱스 | 관측=승인 아님; 원본 본문 대량 복사 금지 |
| C. Knowledge Discovery | positive_capability_discovery, operation_prevention, P11 | 오류 패턴 외 긍정 기술/유사·모순/고유성/적용 가치 분류 | 제안=기술 진실 아님; 자동 권리 승격 금지 |
| D. Controlled Test Lab | capability_trials, P10 worker, disposable tests | 동일 테스트의 전후/양성/음성/미지원 버전/실패 삽입. 환경 SHA·Python/Git/MCP 설치판 고정 | 외부 원본 코드 임의 실행 금지, UCIE-authored fixture 우선 |
| E. SkillBook Composer | skillbook_blueprint, editorial, 001/002/003, principle composer | 사람이 읽는 단계별 원리+제약+적용 절차와 기계 계약을 단일 원본 증거로 결속 | 초안은 고객에게 승인 자산처럼 보이지 않음 |
| F. Local Evidence Workbench | frozen Local V04 routes /local/* | 옵트인 독립 경로/제안형 화면, task-first 내비·접기형 근거·비교 | 기존 GET/Host/CSP/미승인 경계 유지; no silent re-theme |
| G. Evolution & Distribution Gate | P11 evolution, revision review, owner C0–C5 | dependency impact graph, stale/not-applicable 판정, 서명·라이선스/고객별 별도 소비 가드 | 데이터 유입과 고객 전용 상용 배포/권한은 분리 |

**초기에는 신규 DB를 만들지 않는다.** 기존 원장/검색에 identity/mapping/quality view를 읽기 전용으로 덧씌우며, 운영 DB 마이그레이션은 분리된 증거·승인 후에만 시행한다. 무거운 별도 message broker, vector DB, Kubernetes, GPU 서버도 초기 필수 아님.

### Claim-Evidence-Test 최소 원장 계약(제안 스키마)

- identity: claim_id, topic/tech, safe technique, use_case, issue_family, stable artifact ID.
- provenance: allowlisted source_id, owner, immutable URL, original Git tag/commit/blob SHA256, publication/merge time, license/attribution status, primary-vs-synthesized claim label.
- applicability: language, installed runtime/library/git/SDK version, OS, expected protocol version, input contract, precondition, prohibited/unknown situations, dependencies.
- proof: evidence_sha, UCIE-owned test recipe ID, positive/negative/control cases, exact environment, actual stdout/status/digest sanitized receipt, verified by whom, test run date and test freshness.
- decision: PUBLIC_OBSERVED / UCIE_DRAFT / FIRST_PARTY_TESTED / INDEPENDENTLY_VERIFIED / OWNER_APPROVED / CUSTOMER_LICENSED states **distinct**, with orthogonal HOLD/DEPRECATED/RETRACTED reason. No auto promotion.
- evolution: parent version, affected asset ids, changed source, impact score **heuristic only**, rerun budget, last test date, next required proof.
- safety: no customer data fields, no cross-project link, no claimed source rights from URL alone.

Truth claim and release permission are 2 orthogonal axes: independently tested data may still be unlicensed; owner-approved library metadata is not permission to execute code. REST/JSON flags and UI semantics must never imply otherwise.

## 3. 리스크 및 실패 시나리오: 예방책과 인수 게이트

| 주요 위험 | 현실 위험 | 설계상 예방 | 사용자 UI에 표시 | 인수시험 |
| --- | --- | --- | --- | --- |
| 잘못된 기술 권고 | 미검증 공개 PR/합성시험을 진짜 수정으로 오인 | claim-source-version-test 삼중 결속; negative tests; false-positive/false-negative 별도 기록 | '검토 전', 'UCIE 자체 시험', '독립 검증', '권리 미승인' 각각 글자로 구분 | 잘못된 승인 조합 0/전체 부정 fixture |
| 경쟁사 기능 중복 | 보통 스킬/에이전트 레지스트리로는 유료 차별화 안 됨 | upstream 전후 적용성+비용 절감 비교; 4축 실사용 workflow | 기술 적용 가능/불가능 이유, 비교 결과를 우선 | 기존 무료 도구 대비 task success, elapsed, incorrect guidance, retention |
| 소스/사용권/보안 | 공개 코드는 무조건 재배포 가능하지 않음, prompt injection | allowlist, exact SHA, secure parser, rights manifest, publication gate | '출처 검토', '배포 승인' 분리 | 미승인/철회 출처 배포 0 |
| 정보 노후화·검증 부채 | 자산이 쌓일수록 전수 재처리/버전 시험 폭증 | content hash dedupe + impact dependency graph + 변경 영향만 test | '마지막 시험일', '버전별 적용', '재시험 필요' | 동일 원본 중복 비용 감소, 무관 자산 재시험 0 |
| 로컬 PC 자원 경합 | CPU·RAM·디스크가 다른 작업에 영향 | 기존 P10 활용, 신규 무거운 작업 1슬롯, GPU 기본 OFF, 윈도우 Job Object hard cap은 구현·검증 후 적용, 바쁜 PC에서 신규 작업 보류 | 내부 관리에 '대기·시험·보류'만, 고객에게 허위 uptime 수치 금지 | 실제 Windows 부하/반응성·중단·재개·기존 hourly 불변 |
| API 쿼터 및 403 | 새 작업이 무차별 API 호출해 기존 수집기 방해 | existing shared CORE quota + fetch admission, backoff, no duplicate scheduler | 수집 신선도/추가 조회 보류의 사실 상태 | 403/429/no token/pending fail-closed·중복 조회 금지 |
| 로컬 원본/개발본 충돌 | owner dirty original vs clean staged main, 보호 파일 덮어쓰기 | owner-scoped one-file source review, per-module functional regression, no bulk pull/reset/clean | 개발 도구 관리 면에 소스 상태 (고객 화면 미노출) | owner staging source parity+test+cutover separate owner acceptance |
| UX 정보 과밀·오인 | raw SHA/중복 뱃지 때문에 무엇을 할지 모름 | task first, result→scope→test→source progressive disclosure | 짧은 결론 + 적용/불가/불확실 사유 | 사용성 시험에서 상태 오인 0 목표 |
| 로컬 테스트와 고객 환경 불일치 | local synthetic PASS != customer PASS | actual recipient clean Windows install, signing, rollback, C0–C5 | 고객 검증 전 '외부 배포 없음' | independent recipient + security/rights/license signoff |
| 고객 의뢰 지식의 소유권 | 고객 코드로 무단 학습/전역 자산화 | 공용 UCIE public-only 유지, 미래 opt-in 계약과 tenant/local isolation 별도 제품/권리 승인 | '공개 기술만 사용, 고객 자료 미수집' | 침투/데이터 누출/권한/철회 부정 시험 |
| 운영비 허위 추정 | 로컬 CPU 시간을 사용료로 계산하거나 인력 후보 검토비를 과장 | real power/backup/CPU seconds per verified asset, human independent approval 별도 | 고객에게 측정된 실제 자산 처리/업데이트 상태만 공개 | 정량 기준 실제 owner host receipts |

## 4. 비용/자체 엔진 우선 정책

일상적인 공개 기술 후보 분류, 중복·신규성 추정, source SHA 비교, 단순 템플릿 작성, 재시험 작업은 UCIE 자체 Python 엔진을 기본으로 한다. 그 작업에는 외부 생성형 API 호출이 필수 아님. 'CPU/GPU 호출료 0'은 **기존 로컬 PC에서 유료 클라우드 연산 청구 없음**을 뜻하며 전기·장비 수명·저장장치·백업·개발·권리 검토의 전체 원가 0을 의미하지 않는다.

복잡한 의미적 재가공은 (1) deterministic extraction, (2) curated first-party composer, (3) explicit owner-approved local model test 중 성능과 재현성을 비교 후 선택. 현재 승인된 로컬 LLM 학습·운영은 없음; 모델이 반드시 필요하다고 또는 완전 자동 추론이 이미 성공했다고 주장하지 않는다.

기존 P10 최대 3 경량 작업은 보호하며 신규 무거운 평가/생산은 1개 슬롯으로 시작. CPU cap 10–20%, 메모리 상한 등은 host 사양과 실제 Windows Job Object 시험으로 수치 보정하는 **시험 가설**. hard cap 구현 전에는 '저부하 보장'을 말하지 않는다. 증거가 없는 작업은 진행 대신 안전 보류.

단위경제는 (신규 승인 가능한 asset 수, asset 생성 engine 시간, test/권리비, 버전 변경당 재시험 시간, 고객의 실제 재사용·지원 티켓 감소)로 계측한다. 숫자를 임의 GPU 시급으로 가공해 청구비로 보여주지 않는다.

## 5. 고객 UX 목표와 V04 보존 — 초보자 우선으로 교체

**P0 고객은 비기술자/바이브 코딩 첫 사용자, P1 고객은 고급 기술 검토자**다. 기존 '검증 증거 3열 작업대'는 P0 기본 화면으로 **사용하지 않는다**. 기존 V04 홈과 개선 제안 페이지의 시각/기능은 동결 유지하고, 동일하게 승인된 Premium Dark 블랙·그라파이트/실버·라일락 스타일에서 **별도의 초보자 시작/문제 안내 opt-in 시안**을 비교한다.

- 사용자 첫 질문: '**지금 어떤 도움이 필요하세요?**' + '코드가 잘 안 돼요', '간단한 예제를 보고 싶어요', '차근차근 배우고 싶어요'. 현재 3개 시작 경로를 재사용.
- 초기 설명: 실제 할 수 있는 것(현재 4종의 제한된 문제 분류, 미리 준비된 UCIE 예제, 공개 기술 설명)과 할 수 없는 것(자유형 AI 상담·앱 자동 제작·고객 코드 자동 수정)을 분리해 짧고 솔직하게 밝힌다.
- 상황을 묻는 1열 UX: 대표 사례 선택 우선, 필요 시 12~360자 일반 증상 입력. **코드·로그·파일 경로·비밀정보 입력 금지**, 현재 POST는 동일 Host/Origin의 /local/ask에서만. 사용자가 프로그램 버전을 모르면 모른다고 답할 수 있지만 해당 환경 '적용 가능'을 주장하지 않는다.
- 결과는 '비슷한 사례를 찾았어요' → '**실제 원인인지 아직 몰라요**' → '지금 확인해 볼 일' 순서. 고급 상세만 원본 SHA/버전/독립 QA/권리와 SkillBook machine contract 노출.
- 모든 메뉴·버튼·설명에 **docs/UCIE_V2_BEGINNER_COPY_DICTIONARY_20261126.md**의 쉬운 말 사전을 적용하는 설계. 기술 이름·원본 정보는 삭제하지 않고 선택적 상세에 보존. 기술 상태·권리 상태 두 축은 섞지 않는다.
- 실제 사용성 판정은 코딩 경험이 없는 5~8명(초기 시험 계획)과 보조 전문가 2~3명으로 현행 V04 대조 UX와 비교: 첫 행동 이해, 정상/미지원 상황 대응, 데이터 보안/자동 수정 오해 없음, 320–1440 너비, 200% 확대, 키보드 접근. 시안이나 CSS 자체 검토만으로 UX PASS 금지.

시각 스타일/소유자 V04 frozen guard 그대로. 실제 코드/라우트 적용은 별도 owner scope/CI/브라우저 회귀 후에만 한다. UX의 목적은 '기술을 다 안다는 인상'이 아니라 **초보자가 안전하고 알기 쉬운 다음 단계를 찾는 경험**이다.

## 6. 현 단계에선 하지 않을 것

- 새로운 메타 원장·스케줄러·클라우드 기반 서버·로컬 GPU의 선구매
- 유료 AI 모델을 모든 요청에 넣는 사업 구조
- 외부 고객 코드 분석·고객별 telemetry를 UCIE 공용 지식 모델로 자동 편입
- 발행/승인되지 않은 SkillBook을 '인증'으로 표현
- 모든 사용자의 문제를 해결하는 범용 코딩 에이전트, 고객 자동 리포지토리 스캔, 사용자 프로젝트 일괄 수정
- 기존 V04 디자인의 무단 전면 수정, 다른 프로젝트 그래픽/데이터 참조
- 메타데이터 후보 1,000건을 승인 기술 1,000개로 해석하거나 CI PASS를 고객 릴리스 증명으로 사용

## 7. 단계별 개발·평가 및 GO/NO-GO

| 순서 | 개발/시험 작업 | 완료 판정 조건 | 이 단계 종료 시 사업적 의미 |
| --- | --- | --- | --- |
| P0 소스/운영 기준 | 기존 owner-original vs clean staged source 기능별 통합, P10/P11/Local V04 회귀 및 source QA | 원본/개발본 증거 분리, 4축 기존 owner-accepted 동작 보존, 운영 권한 위반 0 | 제품 안정성 전제 |
| P1 핵심 기술 실증 | MCP SDK prompts/get 또는 Python scandir의 정확한 official version 전후 positive+negative 시험 및 claim graph | 원본 pinned, 실제 설치 버전, UCIE authored recipe, independent QA 부족하면 HOLD | 구체적 차별화 증거 첫 사례 |
| P2 초보자 UX 샌드박스 | 기존 3개 첫 방문 선택지와 네 가지 대표 문제를 1열·3단계로 연결한 **별도 미적용 prototype**, 쉬운 말 사전·단계별 진실상태 | V04 시각/원래 route 및 /local/ask 기존 제한 POST·Host/CSP 불변, 초보자 실브라우저/사용성 시험 | 고객 사용성 실증 |
| P3 증분 지식 개정 | upstream change별 affected asset만 재검증, failure/retract/stale 기록 | 연결 없는 자산 대량 재처리 금지, 이전 vs 이후 재검증 비용/품질 입증 | 유지형 서비스 경쟁력 실증 |
| P4 C0–C4 고객 검증 | 지정 고객용 서명/비공개 라이선스/정식 패키지, 설치·업데이트·롤백·보안·권리 | clean recipient에서 4축 실제 업무, 개별 승인/권리 확인 | 상용 출시 준비 |
| P5 C5 | 소유자 승인 지정 고객 1곳 유료 파일럿 | 계약·고객 설치·독립 검증·롤백·실사용 기록 | 유료 수요 입증 후 확대 |

P0/P1은 현재 승인된 UCIE-only 개발 범위만. P2의 UI 적용, P3의 새로운 자동 운용, P4/P5의 라이선스/배포는 별도 소유자 승인과 사실 기반 게이트를 요구한다. 기간/비용은 owner PC·고객 합의와 생산실측 없이 확정하지 않는다.

### 측정 KPI (처음에는 목표·가설, 실제 성과 아님)

- product task success: 지정된 사용자가 하나의 호환성 문제에 대해 *실제 적용 조건과 불확실성*을 올바로 파악한 비율 (목표 80% 이상, 통제 비교).
- verification honesty: 잘못된 승인/권리/실시험 단계 표시 0건; 명시적 UNKNOWN/HOLD에서 안전하게 보류 100%.
- evidence-to-action: 첫 유효 검색에서 테스트 범위·버전·결과를 확인하는 데 걸린 시간, 기존 4분리 메뉴 대비 감소 목표 (기준선 먼저 측정).
- version fitness: 실제 기술 버전 A/B 양성/음성 hold-out confusion matrix, false positive/false negative 별도 기록.
- update economics: 검증된 자산 1개당 CPU 초, 증분 재시험 횟수, 무관한 자산 재시험 수, 변경 후 재검증 대기 시간.
- local safety: 다른 작업명/파일은 읽지 않고 host 전체 load 및 UCIE 프로세스 리소스만; 기존 LocalV1/user hourly 영향 없음을 host에서 측정.
- usability/accessibility: 320/390/768/1024/1440 폭, 200% zoom, 화면낭독·keyboard, 긴 SHA/URL 포함 가로 overflow 0, 검증/승인 상태 오인 0. 기준 충족 전 UX PASS 금지.

## 8. 참고 근거(경쟁사 조사용, UCIE 공개 마이너 신규 승인 아님)

- UCIE 4대 목표: docs/ROADMAP.md
- 지정 고객용 상용 출시 계약: docs/UCIE_FULL_PRODUCT_PRIVATE_CUSTOMER_RELEASE_V1.md, GitHub issue #199
- UCIE V04 고정: docs/UCIE_V04_PREMIUM_DARK_CUSTOMER_UX_20261109.md, src/ucie_miner/local_v1_design_v04.py
- UCIE Local V1 소유자 인수: docs/UCIE_LOCAL_V1_OWNER_ACCEPTANCE_20261108.md
- GitHub Copilot Skills/MCP 2026-07-29: https://github.blog/changelog/2026-07-29-copilot-code-review-agent-skills-and-mcp-now-generally-available/
- Cursor automations: https://cursor.com/docs/cloud-agent/automations
- Tessl Registry skills/QA/version/policies: https://tessl.io/product/registry
- SonarQube AI Code Assurance: https://docs.sonarsource.com/sonarqube-server/2026.1/ai-capabilities/ai-code-assurance
- W3C WCAG 2.2: https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- UI/UX Pro Max 오프라인 검색: style/design-system('technical evidence developer knowledge dashboard'), ux('dashboard navigation','status','data tables','contrast focus','responsive mobile table'). 제안 DB는 검증된 배포 디자인이 아니며 컬러 등은 기존 UCIE V04 고정 규칙이 우선.

## 9. 의사결정 및 인계

STATUS=FINAL_PROPOSAL_OWNER_REVIEW_REQUIRED
OWNER_EXISTING_FIXED_RULES=UNCHANGED
DEVELOPMENT_OWNER=UCIE통합개발방
BUSINESS_OWNER=UCIE사업방
NEXT_ACTION=기존 초보자 시작 3개 및 4종 질문 UI를 먼저 인수하고 실제 가능한 능력만 보여주는 1열·3단계 시안 비교; MCP 003은 선택적 기술 상세에서 4축 검증·개정 근거를 보여주는 전문 사용자 실증으로 분리
ACCEPTANCE=code/CI/owner host/independent QA/rights/customer distribution separate receipts
NO_GO=existing LocalV04 shell/owner original dirty changes/worker schedule/collector DB/C40/customer private code/other projects modifications
SLACK_RECORD=UCIE 설계 기록 https://kangsoolnc.slack.com/archives/C0CA4AW06BH/p1795655585269739 ; 초보자 기준 중요 수정 https://kangsoolnc.slack.com/archives/C0CA4AW06BH/p1795655912447919?thread_ts=1795655585.269739&cid=C0CA4AW06BH ; 작성시각 2026-11-26 10:18:32 KST ; 상태=SLACK_POST_CONFIRMED__HANDOFF_RECEIVER_ACK_NOT_OBSERVED. 새 작업방이 실제 인계 확인한 것은 아님.
