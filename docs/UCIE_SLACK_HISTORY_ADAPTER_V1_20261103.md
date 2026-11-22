# UCIE Slack 이력 게이트의 실제 서버 읽기 연동 V1

범위: UCIE 전용 `#ucie-project` 채널. **실제 사용자/토큰/타 프로젝트를
읽거나 저장하지 않는 소스 구현**. PR #78 소유자 승인 이력은 이미 확인됨.

## 실제 서버 연동 계약

`src/ucie_miner/ucie_slack_history_adapter_v1.py`의
`UCIESlackHistoryAdapter`는 **서버 소유의 인증된**
`read_history_page(channel_id, cursor, limit)` 콜백을 받아,
Slack Web API `conversations.history`의 `ok/messages/response_metadata.next_cursor`
결과를 검증해 기존 `ucie_admin_history_verdict_v1.py`의 검색 함수
인터페이스로 변환한다.

`owner_scoped_bridge_v1.classify_admin_deploy_absence(read_history_page=...)`
에서 읽기 전용 경로가 실제 연결되도록 했다. 한 판정 안에서는
한 번의 채널 전체 스냅샷을 4개 검색어에 재사용하고, **다음 판정은
새 어댑터를 만들어 반드시 다시 읽는다**. DB/디스크 캐시 없음.
예상보다 많은 메시지, 누락 페이지, 누락 앵커, 인증/권한 오류,
잘못된 커서, 다른 채널, 중복 TS는 결론을 **차단**한다.

**서버가 콜백을 제공할 때만 동작한다.** 현재 ChatGPT Slack
연결 도구를 Windows `D:\UCIE` Python 프로세스가 자동으로
호출할 수 있는 것은 아니다. 연결된 ChatGPT 계정의 Slack 토큰을
파일에 복사하거나 ChatGPT 대화/도구 결과를 서버 인증정보로
간주하지 않는다. 사용자 MCP 요청에 `callback`, `token`,
`channel_id`를 추가해주는 방식도 금지한다.

서버 소유의 비공개 Slack API 클라이언트에 기존 승인된
`conversations.history` 권한이 제공돼 있으면, 그 클라이언트를
고정 채널 `C0CA4AW06BH`로 호출하는 얇은 읽기 전용 함수만
주입하면 된다. 그렇지 않으면 현재 함수는
`HISTORY_RECHECK_REQUIRED_BLOCK_VERDICT`를 반환한다.
신규 토큰 발급·Slack 워크스페이스 권한 변경은 이번 패치에 포함하지
않는다.

## 분리된 보안/판정

- 2026-10-25 기존 UCIE 관리자 9도구 소유자 승인·배포 영수증은
  현재 **확인된 과거 사실**이며 부재 주장 금지
- 현재 ChatGPT 플러그인 backend 소유권, 원격 요청별 owner 인증,
  신규 승인형 도구 4개의 실제 서버 등록·쓰기 grant 활성화는
  별도 증명이 필요
- 승인 저장소 ACL·운영 DB·C40 작업·타 프로젝트·MCP 서버
  실행/재시작을 변경하지 않는다
- 이 어댑터는 증거를 보강할 뿐 owner 권한을 부여하지 않는다

## 수용시험

`tests/test_ucie_slack_history_adapter_v1.py`의 합성 JSON
데이터로 2페이지 정상 처리, 단일 판정 재사용, 매번 새 조회,
missing_scope, 커서 루프, 채널 혼합, 앵커 누락, 중복 영수증,
프롬프트 주입, 원격 인자 권한 확대 거부 등을 테스트한다.
`tests/test_ucie_admin_history_verdict_v1.py` 및
`tests/test_ucie_owner_scoped_bridge_v1.py` 기존 회귀도 실행한다.

**배포/연동 상태:** Python adapter/기존 bridge 호출부 코드 개발만
완료됐을 때도 `LIVE_SLACK_CALLBACK_NOT_WIRED`를 유지한다.
GitHub CI 통과와 실제 서버 Slack 호출의 성공을 혼동하지 않는다.

공식 참고:
https://docs.slack.dev/reference/methods/conversations.history/
https://docs.slack.dev/apis/web-api/pagination/

기존 역사 출처:
https://github.com/tmdrkdtn1-project/UCIE/pull/78
https://kangsoolnc.slack.com/archives/C0CA4AW06BH/p1792896036978529
