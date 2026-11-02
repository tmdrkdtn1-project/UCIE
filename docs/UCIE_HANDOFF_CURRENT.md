# UCIE 현행 인계 체크포인트 — 새 채팅방 읽기 시작점

**이 문서는 현재 확보한 증거의 마지막 요약이며 최신 상태의 영구 보증이 아니다.** 새 작업방은 GitHub PR/CI/실제 owner-host 기록과 Slack 관련 스레드를 먼저 재확인한다. 내용이 불일치하거나 관측한 지 오래되었으면 `STALE_RECHECK_REQUIRED`.

```text
PROJECT=UCIE
HANDOFF_ID=UCIE-HO-20261102-LOCAL-FIRST-01
RECORD_TYPE=HANDOFF_REQUIRED
FROM_WORKROOM=UCIE사업방
TO_WORKROOM=UCIE통합개발방
STATUS=HANDOFF_PREPARED_NOT_RECEIVED
BASE_MAIN_SHA=b2941dbe8bb447dec2dd8a179b4b7ea61b9e28dc
DECISION_DOC=docs/UCIE_LOCAL_FIRST_SKILLBOOK_EXECUTION_PLAN_20261102.md
ACTIVE_PRS=#173 OPEN_NOT_MERGED; #174 OPEN_NOT_MERGED
CI_STATE=#173 Windows/Python3.15 1/4 failure; other 3/4 success; exact-head recheck required
OWNER_HOST_STATE=NOT_CURRENTLY_OBSERVED_TUNNEL_OFFLINE; last owner-reported evidence is historical only
APPROVAL_STATE=NO_NEW_OWNER_APPROVAL_FOR_WORKER_SCHEDULER_OR_RELEASE
RELEASE_STATE=SKILLBOOK_NOT_IMPLEMENTED_NOT_PUBLISHED
SLACK_POST_STATE=PENDING_FOR_THIS_HANDOFF
ACK_STATE=NOT_RECEIVED
NEXT_OWNER=UCIE통합개발방
NEXT_ACTION=1) confirm actual UCIE main/PR heads and CI; 2) fix/retest #173 Windows/Python3.15 CI, 3) implement safe UCIE-only heavy-job resource controls; 4) verify owner-host read-only preflight when available, 5) build one actual source-anchored SkillBook+portable recipe
ACCEPTANCE=exact-head CI 4/4 + owner-host resource limit/isolated regression + first real SkillBook and independent test receipts; gates independent
NO_GO=private project/customer data collection; new public source; new scheduler; automatic rule approval/signing/publishing; model training; replacing dirty owner files; local runtime PASS without receipts
PREVIOUS_SLACK=https://kangsoolnc.slack.com/archives/C0CA4AW06BH/p1793589567055009
CURRENT_SLACK=PENDING_POST_CONFIRMATION
```

## 중요 확정 결정과 증거

- UCIE 최종 목표는 공개 근거를 재가공·검증해 사람과 AI가 재사용하는 **스킬서적·개발 엔진·학습 로직**을 생산하고 개정하는 것이다. 단순 오류/PR 검색기 아님. 정본: `docs/UCIE_SKILLBOOK_PRODUCT_MISSION_V1_20261102.md`. [PR #172](https://github.com/tmdrkdtn1-project/UCIE/pull/172) 병합되었음.
- **로컬 우선**: GPU/외부 AI API 기본 OFF, 기존 P10 독립 작업자/SQLite/기존 수집기 재사용. 신규 고부하 업무 1작업, 강제 CPU/RAM 제한과 바쁠 때 보류는 *제안/미구현*.
- PR #173: [내부 메타데이터 배치](https://github.com/tmdrkdtn1-project/UCIE/pull/173) **OPEN**, 2026-11-02 관측 CI 3/4 PASS. Windows/Python 3.15의 기존 `test_ucie_release_review_v11` localhost POST `WinError 10053`로 실패. 새 배치 로직 실패라고 단정하지 않고 원인 격리·전체 회귀시험 후에만 병합. [실패 CI Job](https://github.com/tmdrkdtn1-project/UCIE/actions/runs/41373579920/job/125048973305).
- PR #174: [로컬 우선 통합 구축·인수 계획](https://github.com/tmdrkdtn1-project/UCIE/pull/174) **OPEN**. 여기에 새 채팅방 인계 규약과 현재 체크포인트를 함께 제안. 병합 전에는 `main`이 이 인계 문서를 포함한다고 주장하지 않는다.
- 실제 UCIE 로컬 관리 연결 확인은 `Tunnel-client has not been seen for 300 seconds` 오류. **원격 관측 불가**이며 기존 소유자 PC 수집기/워커가 멈췄다는 증거는 아니다. 예전 Slack의 성공 영수증은 최신 운영 PASS와 구분.
- 제품/사업 결정: 현재 차별화·유료 수요 미입증. **공개 근거 기반 내부 베타 GO, 외부 상품 출시 NO_GO**. 고객 비공개 의뢰·다른 프로젝트 자료를 UCIE 전역 지식으로 수집 금지. 비용 가정은 실비와 구분.

## 지금 새 채팅방으로 이전한다면

1. `AGENTS.md`, `docs/UCIE_SLACK_HANDOFF_PROTOCOL_V1_20261102.md`, 본 문서, 공개 출처/스킬서적 정본을 읽는다. PR #174가 미병합이면 `docs/ucie-local-first-knowledge-engine-plan-20261102` 브랜치에서 읽는다.
2. `#ucie-project`의 최신 `UCIE-HO-20261102-LOCAL-FIRST-01` 인계 메시지 및 스레드를 읽고 기존의 상태/증거와 대조한다. 다른 프로젝트 Slack 자료를 조사하지 않는다.
3. 새 방에서 실제로 재검증한 뒤에만 동일 Slack 스레드에 `HANDOFF_RECEIVED`를 게시한다. 수신 전에는 `ACK_STATE=NOT_RECEIVED`. 담당자 이름만 보고 수용을 추정하지 않는다.
4. 기존 완료 작업 재수행을 금지하고, 정확한 첫 미완 작업과 CI/host의 남은 차단 조건만 처리한다.
5. 중요한 변경이나 다음 방 인계 발생 시 `docs/UCIE_HANDOFF_CURRENT.md`를 최신화하고 실제 Slack permalink + 게시 KST 시각을 기록한다.

## 기록 작성 책임

- PRIMARY_NEXT_OWNER: **UCIE통합개발방** — PR #173 증거 확인·실험 자원 보호·스킬서적 실물 제작.
- BUSINESS_REVIEW_OWNER: **UCIE사업방** — 사업/원가/고객 기여 권리 가설, 새 기능 상업화 판단.
- OWNER-HOST EVIDENCE: 오직 실제 UCIE Windows 호스트에서 발급된 기록이나 사용자가 제공한 동등한 진짜 증거로만 판단.
- RECEIVER_ACK: **아직 없음**; Slack 송신 성공과 별개.
