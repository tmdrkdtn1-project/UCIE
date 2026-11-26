# UCIE V2 최종 설계 확정 및 통합개발방 인계서

작성: 2026-11-26 KST | PROJECT=UCIE ONLY
HANDOFF_ID=UCIE-HO-20261126-V2-BEGINNER-FIRST-01
FROM_WORKROOM=UCIE사업방
TO_WORKROOM=UCIE통합개발방
RECORD_TYPE=DECISION_LOCKED_AND_HANDOFF_REQUIRED
STATUS=OWNER_APPROVED_DESIGN_BASELINE__NOT_IMPLEMENTED__NOT_DEPLOYED
ACK_STATE=NOT_RECEIVED
SLACK_POST_STATE=PENDING_ACTUAL_RECEIPT
SLACK_HANDOFF_URL=PENDING_ACTUAL_RECEIPT
DESIGN_PR=https://github.com/tmdrkdtn1-project/UCIE/pull/351
DESIGN_BRANCH=design/ucie-v2-evidence-first-product-ux-20261126
OBSERVED_MAIN_SHA=f5fbaca6c94f50130941570090c2c555cf92d816

## 1. 소유자 확정 범위

2026-11-26 사용자 지시: "오케이. 여기까지 내용을 최종 설계안으로 설정하고, UCIE 개발방에 넘길 명령어와 근거 자료 정리해줘".

이 발언은 **UCIE V2 제품 경쟁력·리스크 대응·초보자용 UX와 모든 고객용 문구를 최종 설계 기준으로 확정**한 것이다. 운영 PC 코드 교체, 실제 UI 출시, 고객 사용권·서명·상용 배포, 자동 규칙 승격, 운영 DB/예약 작업 변경까지 승인한 것은 아니다. 소유자 기존 승인 Premium Dark V04 디자인과 /local, /local/evolution 화면의 동결 규칙은 그대로 유지된다.

**최종 효력 순서:** 이번 인계서 > 업데이트된 바이브 코딩 초보자 UX 계약 및 쉬운 말 사전 > 초기에 작성한 3열 기술 작업대 초안. 최신 PR #351은 Draft/미병합 상태이므로 이 설계 문서가 main에 이미 있다고 가정 금지.

## 2. 정본 근거 자료 — 순서대로 읽기

1. 아키텍처·사업 차별화·리스크·4대 기능:
https://github.com/tmdrkdtn1-project/UCIE/blob/design/ucie-v2-evidence-first-product-ux-20261126/docs/UCIE_V2_EVIDENCE_FIRST_PRODUCT_RISK_UX_FINAL_PROPOSAL_20261126.md

2. 최종 초보자 기준 UX/정보 배치·단계별 동선/미지원 상황:
https://github.com/tmdrkdtn1-project/UCIE/blob/design/ucie-v2-evidence-first-product-ux-20261126/docs/UCIE_V2_EVIDENCE_FIRST_UX_SCREEN_CONTRACT_20261126.md

3. 모든 메뉴·버튼·도움말·입력·오류·제약 설명의 고객용 쉬운 한국말 사전:
https://github.com/tmdrkdtn1-project/UCIE/blob/design/ucie-v2-evidence-first-product-ux-20261126/docs/UCIE_V2_BEGINNER_COPY_DICTIONARY_20261126.md

4. UCIE 4축/소스·권리 규칙:
https://github.com/tmdrkdtn1-project/UCIE/blob/main/AGENTS.md
https://github.com/tmdrkdtn1-project/UCIE/blob/main/docs/ROADMAP.md

5. 로컬 제품/화면 소유자 동결·인수/상용 출시 미승인:
https://github.com/tmdrkdtn1-project/UCIE/blob/main/docs/UCIE_V04_PREMIUM_DARK_CUSTOMER_UX_20261109.md
https://github.com/tmdrkdtn1-project/UCIE/blob/main/docs/UCIE_LOCAL_V1_OWNER_EXECUTION_LOCK.md
https://github.com/tmdrkdtn1-project/UCIE/blob/main/docs/UCIE_LOCAL_V1_OWNER_ACCEPTANCE_20261108.md
https://github.com/tmdrkdtn1-project/UCIE/issues/199

6. 기존 첫 방문 및 질문/기능 구현과 관련 테스트 (중복 생성 금지):
src/ucie_miner/local_v1_design_v04.py
src/ucie_miner/local_v1_app_v01.py
src/ucie_miner/local_first_use_plain_v01.py
src/ucie_miner/local_question_intake_v01.py
docs/UCIE_LOCAL_OWNER_QUESTION_INTAKE_V01_20261115.md
tests/test_ucie_first_use_plain_v01.py
tests/test_ucie_local_question_intake_v01.py
tests/test_ucie_local_question_denied_transport_v02.py

7. 기존 Slack 설계·정정 기록:
https://kangsoolnc.slack.com/archives/C0CA4AW06BH/p1795655585269739
https://kangsoolnc.slack.com/archives/C0CA4AW06BH/p1795655912447919?thread_ts=1795655585.269739&cid=C0CA4AW06BH

## 3. 잠긴 제품·사용자 요구

4대 기능은 동등하게 보존: (1) 오류 예방, (2) 실제 유용한 개발 엔진/스킬, (3) 가상도서관·사람이 읽는 SkillBook, (4) UCIE 자체 기술 증거/실험을 통한 개선. 핵심 차별화는 공식 공개 자료의 정확한 버전·원본/테스트·한계/권리·개정 근거를 하나의 신뢰 가능한 기술 자산으로 연결하는 것이다. 단순 에이전트나 스킬 목록 제작이 목표가 아니다.

**P0 고객은 코딩 경험이 전혀 없는 바이브 코딩 첫 사용자**다. 기술자는 2차 사용자. 초보자 기본 화면에 기술 검토·호환성·검증 증거·SHA·SDK·MCP 등 불필요한 용어와 3열 증거 대시보드를 노출하지 않는다. 고객에게 '초보자'라고 부르거나 능력을 평가하는 표현도 쓰지 않는다.

기본 세 가지 시작 버튼:
- 코드가 잘 안 돼요 → 문제 살펴보기
- 간단한 예제를 보고 싶어요 → 예제 체험하기
- 차근차근 배우고 싶어요 → 설명 읽기

향후 일관된 단일열·3단계:
(1) 지금 어떤 도움이 필요하세요? / 어떤 일이 있었나요?
(2) 비슷한 문제를 찾았어요 / 아직 이 문제에 맞는 안내가 없어요
(3) 지금 확인해 볼 일 + 단 하나의 안전한 다음 행동

출처·실제 시험·버전·권리/배포 허가는 선택적 '왜 이렇게 안내하나요?'에서 확인할 수 있게 하되 **미검증/무허가는 기본 결과에도 쉬운 말로 분명하게** 표현한다. 실제 원인 조사, AI 자동 고침, 앱 자동 제작, 실고객 코드 실행/검사가 이미 가능하다고 오인시키지 않는다.

'만들고 싶은 게 있어요'는 미래 제품에서 중요한 아이디어 우선 동선이지만 현행 범용 AI 앱 제작 기능은 없다. **현재 UI에 가짜 구현 버튼으로 넣지 말 것.**

## 4. 인수해야 할 현행 기능/위험

- src/ucie_miner/local_first_use_plain_v01.py에는 이미 3개 선택 진입점이 있다. 동일 기능 중복 개발하지 말고 계약 고정.
- /local/ask는 실제로 기존 승인된 동일-origin 제한 POST를 사용한다. 12~360자, 네 가지 고정 증상 유형의 인메모리 분류만 지원한다. *모든 로컬 화면 GET-only*라는 이전 설계 표현은 오류였고 정정됨. 그 외 GET 전용 검색/도서관 등 보안 계약 유지. 임의 POST·파일 업로드·프로젝트 디렉터리 스캔/외부 AI 호출 금지.
- 질문에 코드·원본 로그·파일 경로·암호·API 키·개인정보를 넣으라고 안내하지 않는다. 입력은 기존 계약처럼 메모리에서만 처리하고 원문 외부 출력/공유/학습 금지. 예제는 UCIE 작성 합성 예제이지 고객 코드 수정이 아니다.
- 승인된 공식 기술문서·릴리스/보안 권고와 5개 저장소 python/cpython, PowerShell/PowerShell, git/git, modelcontextprotocol/python-sdk, actions/runner-images 경계 유지. 다른 프로젝트/고객 비공개 코드·연결앱·대화 접근 금지.
- 기존 owner Windows 원본 D:\UCIE의 미커밋 파일·보호 브리지/운영 SQLite/TaskScheduler/C40/Tunnel/기존 Local V04 서비스에 접근·변경·재시작 금지. 기능별 코드 통합은 기존 별도 owner gate의 승인에 따른다.
- 로컬 V04 소유자 인수 성공이 사용자용 V2 초보자 UX 승인 또는 상용 출시를 증명하지 않는다. CI/브라우저 테스트/소유자 승인/고객 배포 단계 독립.

## 5. 통합개발방이 수행할 실무 작업

A. MAIN·PR #351·CI 최신 HEAD, 현재 owner-host 근거·기존 V04/첫 이용/질문 기능 계약을 읽기 전용으로 확인. 본 인계서가 main에 없으면 design 브랜치에서 로드.

B. 기존 UCIE-only 구성요소를 재사용해 **별도 격리 초보자 UI 시안**과 관련 정적·제한 기능 검증 코드를 개발. V04 동결 원본/운영 앱에는 아직 적용하지 말 것. 단일열 3단계 및 쉬운 문구, 미지원·민감정보·오류 상태를 구현. 실제 버튼은 반드시 지원되는 기존 작동 경로를 연결, 가짜 AI 안내 금지.

C. 정확한 변경 HEAD로 기존 로컬 제품/신규 UX 회귀·부정 테스트 수행. 질문 4유형/미지원/입력 길이/민감정보·원문 반사/Origin/Host/CSP/승인 위조/빈 결과/오래된 버전 포함. Ubuntu/Windows Python 3.13/3.15 CI 상태는 실제 수신증으로 확인.

D. 실제 Windows Edge 브라우저에서 320·390·768·1024·1440 폭, 200% 확대, 키보드/포커스, 한국어 길게 줄바꿈, 좁은 화면/장문 출처와 빈 결과·오프라인을 확인. 브라우저 증거 없으면 VISUAL_QA_PENDING.

E. 실제 첫 바이브 코딩 이용자 5~8명(초기 제안 표본)과 기술 사용자 2~3명으로 현행 V04 대비 과제를 평가. 10초 내 첫 행동 이해 80%+와 심각한 기능 오인 0건은 목표이며 **실제 관측 전 PASS 금지**. 일반화된 통계적 결론 주장 금지.

F. 코드 시안·기존 V04와 비교·회귀 영수증·실사용 시험 결과·남은 불확실성과 제약을 모아서 **별도 소유자 UI 적용 승인** 요청. 기존 서비스 교체나 지정 고객 배포는 그때까지 보류.

G. 새 개발방이 실제로 PR/Slack/CI/host 증거를 조회하여 인수하면 Slack 원 인계 스레드에 HANDOFF_RECEIVED + 근거 SHA + NEXT_ACTION을 게시. 송신만으로 인수/완료 표시 금지.

## 6. UCIE 개발방에 바로 보낼 명령어

/UCIE통합개발방
PROJECT=UCIE ONLY
TASK=V2_FINAL_DESIGN_HANDOFF_RESUME
HANDOFF_ID=UCIE-HO-20261126-V2-BEGINNER-FIRST-01

소유자가 이번 UCIE V2 사업·기술·리스크·UI/UX 최종 설계를 확정했습니다.
GitHub tmdrkdtn1-project/UCIE의 Draft PR #351과
docs/UCIE_V2_OWNER_FINAL_DESIGN_DEV_HANDOFF_20261126.md를 먼저 읽으세요.
main에 없으면 design/ucie-v2-evidence-first-product-ux-20261126 브랜치에서 읽으세요.
같은 브랜치의 통합 제품 설계서/초보자 UX 계약/쉬운 말 사전과
main의 AGENTS.md, V04 소유자 동결 규칙, 기존 첫 화면 3선택지,
/local/ask의 실제 4종 질문 분류 기능을 대조하세요.

P0 고객은 코딩을 처음 하는 바이브 코딩 이용자입니다.
기본 UI는 단일열·3단계이며 '지금 어떤 도움이 필요하세요?'
→ '비슷한 문제를 찾았어요/안내가 없어요'
→ '지금 확인해 볼 일'로 구성합니다.
세 가지 선택지 및 현재 가능한 실제 기능을 재사용하고
설명/버튼/지원불가·안전 고지 모두 쉬운 말 사전을 적용하세요.
기술적 증거/버전/권리는 선택적 상세에서 정확히 확인 가능하게 하세요.
'만들고 싶은 게 있어요'는 미래 기능이지 현행 자동 앱 제작 버튼이 아닙니다.

계획만 다시 쓰지 말고 기존 main/CI/호스트 증거를 확인한 뒤
원본 V04 동결 화면과 별도인 UCIE-only 초보자 시안과 긍정·부정
회귀시험을 실제 구현하세요. 안전한 기존 /local/ask POST 외에
새 POST/업로드/외부 API/고객 코드 스캔을 추가하지 마세요.
실 Edge 320~1440px/200%/키보드/오류 화면 및 진짜 초보자 사용성
평가 없이는 UX PASS로 보고하지 마세요.

기존 V04/운영 원장·Task·C40/Tunnel·원본 dirty 파일/다른 프로젝트·고객
비공개 자료·자동 승격/서명/상용 배포 금지. 실제 V04 적용·운영 변경은
별도 소유자 승인 이후에만 하세요.
다음 실행 결과는 스크린샷 근거·테스트·실제 기능 범위·남은 차단 조건을
하나로 묶어 보고하고, 중요 의사결정/실패/다음 인계를 Slack에 남기세요.
이 인계의 Slack 원문을 확인한 뒤 HANDOFF_RECEIVED를 같은 스레드에 남기세요.

## 7. 인수 상태

DESIGN_APPROVED=TRUE (이번 2026-11-26 대화의 명시적 설계 확정)
UI_IMPLEMENTED=FALSE (V2 새 UI 기준)
UI_BROWSER_QA=NOT_VERIFIED
UI_OWNER_INSTALL_ACCEPTANCE=NOT_GRANTED
CUSTOMER_DISTRIBUTION_AUTHORIZED=FALSE
ACK_STATE=NOT_RECEIVED
SLACK_POST_STATE=PENDING_ACTUAL_RECEIPT
