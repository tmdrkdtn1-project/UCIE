# UCIE Slack 결정·분기·새 채팅방 인계 운영 규약 V1
- PROJECT=UCIE ONLY
- STATUS=PROPOSED_PROTOCOL_RECORD_CREATED_NOT_AUTOMATICALLY_ENFORCED
- 정본 위치: `docs/UCIE_SLACK_HANDOFF_PROTOCOL_V1_20261102.md` (규약), `docs/UCIE_HANDOFF_CURRENT.md` (최신 인계 체크포인트)
- Slack: `#ucie-project` (channel ID `C0CA4AW06BH`), 공개할 수 있는 UCIE 프로젝트 상태와 링크만 게시
- 시행 조건: PR 검수·병합, 이후 이 규약을 사용하는 채팅방의 기록/인계 작업. **ChatGPT 새 채팅이 자동으로 이 문서를 읽거나 Slack에 쓰는 것은 보장되지 않음.**
- 근거: UCIE의 제품 정본 `docs/UCIE_SKILLBOOK_PRODUCT_MISSION_V1_20261102.md`와 종합 구축 계획 `docs/UCIE_LOCAL_FIRST_SKILLBOOK_EXECUTION_PLAN_20261102.md`. 기존 P10·시간당 수집기를 재구축/재설정하지 않는다.

## A. 기록의 세 계층 — 역할을 혼동하지 않음
1. **실제 근거(원천):** UCIE GitHub 커밋·PR·CI Job·허용된 원본 URL/SHA 및 실제 owner-host 실행 영수증. 코드/CI/호스트/승인/배포 결과는 서로 독립이다. Slack 메시지가 PASS의 원본 증거가 되지 않는다.
2. **GitHub 정본:** 각 중요 결정은 관련 UCIE 문서에 날짜·의사결정 이유·적용 범위·승인 상태를 기록한다. 채팅방 인계의 읽기 시작점은 항상 `docs/UCIE_HANDOFF_CURRENT.md` 하나다. 해당 문서에는 관련 작업의 최종 상태/PR/근거 링크만 적고 원시 비공개 데이터는 넣지 않는다.
3. **Slack 통보·수신증:** `#ucie-project`의 새 최상위 게시물은 중요한 결정/인계/차단·해제를 알리는 색인이다. 동일한 사안의 CI 진행·보완 정보는 기존 게시물 스레드에 답글. 게시 성공 시 실제 메시지 permalink, Slack `message_ts`와 Asia/Seoul 표시시간을 GitHub 체크포인트에 기록한다.

## B. 누락되면 안 되는 게시 사건(트리거)
| Event type | 즉시 기록할 조건 | 알림의 취지 |
| --- | --- | --- |
| `DECISION_LOCKED` | 제품 목표·경영 방향·승인 범위·자원/기술 정책 변경을 최종 결정 | 다른 방이 과거 판단을 재논의하거나 반대로 구현하지 않게 함 |
| `HANDOFF_REQUIRED` | 다음 담당 방이 바뀜, 방 분리, 새 채팅방 생성·이전, 대화 종료 전에 이어갈 일이 있음 | 재개 지점·담당자·증거/막힘 고정 |
| `GATE_CHANGED` | 실제 CI 4/4, PR merge, owner-host 검증, 안전·권리·배포 승인 상태가 변함 | `CI_PASS`를 `HOST_PASS`로 오해하지 않게 함 |
| `BLOCKER_NEW_OR_RESOLVED` | 작업 불능·충돌·원인 확정 또는 해제 | 실제 막힌 범위와 별도 계속 가능한 작업 구분 |
| `DESIGN_CHANGE` | 새로운 실행 파이프라인/작업자의 권한·소스·스케줄러·원장 구조를 바꿀 계획 확정 | 운영 원장·기존 큐·출처 범위 무단 변경 예방 |
| `CORRECTION_OR_RETRACTION` | 기존 보고가 과장·오판·오래된 증거로 판정됨 | 이전 링크와 정정된 사실을 연결해 허위 상태 전파 방지 |
| `HANDOFF_RECEIVED` | 새 방에서 실제 GitHub/Slack/CI·호스트 증거를 읽고 인계 수용 | 보내기와 읽어서 수용한 것을 구분 |

일반적인 잡담, 무변경 반복 보고, 동일 CI 실행 중이라는 사실만으로 매번 새 최상위 Slack 글을 올리지 않는다. 중요도가 높은 결정은 *다음 응답을 마치기 전*, 새 방으로 넘어가는 인계는 *새 방으로 전환하기 전에* 기록하는 것을 목표로 한다. 도구가 불능이면 실패를 보고하고 GitHub 체크포인트에 `SLACK_POST_PENDING`을 명시한다. **게시하지 않은 내용을 게시했다고 말하지 않는다.**

## C. 표준 Slack 기록 필드 (상태 조작 방지)
모든 중요 메시지는 다음 필드를 반드시 포함한다.

```text
[UCIE | RECORD_TYPE=<DECISION_LOCKED|HANDOFF_REQUIRED|GATE_CHANGED|BLOCKER_NEW_OR_RESOLVED|DESIGN_CHANGE|CORRECTION_OR_RETRACTION|HANDOFF_RECEIVED>]
HANDOFF_ID=UCIE-HO-YYYYMMDD-<TOPIC>-<NN> (인계가 아니면 DECISION_ID 사용)
PROJECT=UCIE ONLY
FROM_WORKROOM=...
TO_WORKROOM=...
DECISION=... (확정된 사실/계획/제안 구분)
STATUS=... (IN_PROGRESS/BLOCKED/HOLD/REVIEW_REQUIRED/RECEIVED 등)
EVIDENCE=Github commit SHA/PR/CI job 링크, 허용된 원본 근거, 실제 owner-host 결과 링크(있을 때만)
CI_STATE=... ; OWNER_HOST_STATE=... ; APPROVAL_STATE=... ; RELEASE_STATE=...
BLOCKERS=...
NEXT_OWNER=<하나의 실제 주요 실행 담당 방>
NEXT_ACTION=<정확한 다음 작업 1~3개 및 실행조건>
ACCEPTANCE=<PASS가 될 객관적 증거>
DO_NOT_TOUCH=<UCIE 경계/원장/스케줄러/타 비공개자료 보호>
DOC=<정본 문서 커밋/브랜치 URL>
PREVIOUS=<기존 관련 Slack/PR 링크>
```

시간은 기록을 보내는 서버에서 발급된 `message_ts`를 KST로 변환해 기록한다. Slack 본문에 작성 전 임의로 실제 발송 시간을 꾸며 넣지 않는다. 커밋/상태는 관측 시점만 확정하며, 나중에는 반드시 **새 증거와 함께 별도 업데이트**한다.

권한·성격이 다른 상태는 분리한다: `PLANNED`, `CODE_WRITTEN`, `CI_PASS`, `OWNER_HOST_OBSERVED`, `INDEPENDENT_QA_PASS`, `OWNER_APPROVED`, `PUBLISHED`. 하나의 PASS가 다음 PASS로 전이하는 것은 금지. `SENT`만으로 `RECEIVED`/작업 완료 주장 금지.

## D. 전달 완료·수신 완료의 2단계 프로토콜
1. **보내는 방:** 최신 UCIE repo·PR·CI·기존 Slack 스레드를 먼저 확인하고, 기존 결정과 중복인지 판단한다.
2. 의사결정/실제 결과를 관련 문서 및 `docs/UCIE_HANDOFF_CURRENT.md`에 기록한다. PR은 열려 있으면 반드시 `OPEN_NOT_MERGED`; 정본 main 미반영이라고 표시한다. 증거 없는 결과는 `UNKNOWN` 또는 `HOLD`.
3. Slack `#ucie-project`에 처음 발생한 중요 사건은 최상위 글로, 같은 사안의 업데이트는 원본 스레드에 게시. **응답에서 실제 permalink와 timestamp를 받은 뒤에만** `SLACK_POST_CONFIRMED`로 체크포인트를 갱신한다. 실패 시 `SLACK_POST_PENDING` 유지.
4. 사용자에게 다음 담당 방 이름·인계 문서 링크·Slack permalink·게시 시각 KST·차단 요인을 보고한다.
5. **받는 새 방:** 작업 시작 전에 `AGENTS.md` → 제품 정본 → `docs/UCIE_HANDOFF_CURRENT.md` → 최신 관련 PR/CI/증거 → `#ucie-project` 최근 관련 Slack 및 스레드 순서로 읽는다. 첫 메시지가 과거 기록을 대체하지는 않는다.
6. **차이 대조:** GitHub main/PR head·CI 최신 상태·host 수신증의 출처/시간을 비교한다. 충돌이 있으면 `CONFLICT_HOLD`로 표시하고 원인을 정리한 후 변경. 새 방에서 인계가 실제로 수용되면 관련 스레드에 `HANDOFF_RECEIVED`(새 담당 방, 재검증 링크, 다음 작업, 제한) 답글을 게시한다.
7. 수신 확인이 실제로 올라오기 전까지 체크포인트에 `ACK_STATE=NOT_RECEIVED`를 유지한다. 이전 방의 `HANDOFF_SENT`만으로 새 방의 작업 시작이나 승인/출시를 주장할 수 없다.

## E. 단일 현재 인계 문서 갱신 규칙
`docs/UCIE_HANDOFF_CURRENT.md`의 필수 필드:
`PROJECT`, `HANDOFF_ID`, `FROM_WORKROOM`, `TO_WORKROOM`, `STATUS`, `BASE_MAIN_SHA`, `DECISION_DOC`, `ACTIVE_PRS`, `CI_STATE`, `OWNER_HOST_STATE`, `APPROVAL_STATE`, `RELEASE_STATE`, `SLACK_POST_STATE`, `ACK_STATE`, `NEXT_OWNER`, `NEXT_ACTION`, `ACCEPTANCE`, `NO_GO`, `PREVIOUS_SLACK`, `CURRENT_SLACK`.

- 새 방 전환 전 **가장 최신 사실**로 한번 갱신하고, 남은 미완 작업을 과거 완료 업무와 구분한다.
- 기록에 GitHub URL/PR만 있으면 해당 GitHub 페이지에서 실제 최신 상태 재조회. 스레드의 최근 시각만으로 기존 결정이 승격되었다고 판단하지 않는다.
- 같은 `HANDOFF_ID`와 사실/증거 SHA가 같으면 중복 게시하지 않고 기존 메시지 permalink를 사용. 새로운 결정/상태 전이가 있으면 새 회차를 기록한다.
- 오래된 체크포인트를 새 채팅이 발견하면 **자동 PASS 대신 STALE_RECHECK_REQUIRED**. 마지막 접근/성공 시각은 이번 관측이 아닌 과거 기록일 수 있다.
- 게시물이나 문서 삭제/수정 요청은 소유자 지시와 기존 데이터 보존/삭제 정책에 따라 처리한다.

## F. 새 채팅방 첫 메시지 (복사해 사용)
```text
/UCIE통합개발방
PROJECT=UCIE ONLY
TASK=UCIE_HANDOFF_RESUME
먼저 GitHub tmdrkdtn1-project/UCIE의 AGENTS.md,
docs/UCIE_SLACK_HANDOFF_PROTOCOL_V1_20261102.md,
docs/UCIE_HANDOFF_CURRENT.md 및 PR #173/#174 최신 상태를 읽고,
Slack #ucie-project의 최신 관련 인계 스레드와 대조하라.
작업 시작 전에 현재 HEAD/CI/owner-host 증거를 분리해 정리하고,
중복 개발은 피하고 NEXT_OWNER가 명시된 최우선 미완 작업부터 진행하라.
실제 수신이 확인된 경우에만 원 인계 스레드에 HANDOFF_RECEIVED와
다음 실행 단계/증거를 게시하고, 이후 중요 결정/블로커/완료/재인계는
본 규약에 따라 Slack URL·발송 시각 KST까지 남겨라.
현재 권한 범위 밖의 PC 작업·scheduler 변경·규칙 승격·배포 금지.
```

사업 검토 방으로 이동할 때는 첫 줄만 `/UCIE사업방`으로 바꾸고, 본문 속 `NEXT_OWNER`와 실제 업무 구분을 재검증한다.

## G. 현실적 한계와 수용 기준
- 이 문서는 **기록 규약이지 ChatGPT가 대화 종료/새 채팅 개설 이벤트를 자동 감지하는 프로그램은 아니다**. Slack 연결이 없는 새 채팅이 내용을 자동 게시할 수 없다.
- 향후 누락 예방 기능을 자동화하려면 (a) 명시적으로 승인된 UCIE-only 인계 사건 생성, (b) 자체 체크포인트/중복키 검증, (c) Slack 게시 성공 영수증 검증, (d) 실패 재시도/기록 보류, (e) 사용자 공개 정보만 게시하는 최소권한 Slack 연계가 별도 필요. **현재 구현·운영 중이라고 주장하지 않는다**.
- 이번에 구현하는 저장소 문서/AGENTS/정적 테스트는 **프로세스 누락 방지 장치**일 뿐 자동으로 새 대화를 감시하지 않는다.
- 외부 공개 수집 범위, 원본 서명, 실제 PC 작업, 운영 DB, 다른 프로젝트 격리 제한은 변화가 없다.
