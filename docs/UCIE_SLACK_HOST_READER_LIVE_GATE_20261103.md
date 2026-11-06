# UCIE Slack 서버 읽기 콜백 — 실호스트 결정 게이트 (2026-11-03 KST)

범위: UCIE ONLY. Slack `#ucie-project` 공개 채널 이력은 이미
ChatGPT 연결 Slack 도구를 통해 조회했으며, 기존 소유/배포
PR #78 및 2026-10-25 소유자 승인 사실을 확인했다.

현재 UCIE Windows 엔진의 `ucie_slack_history_adapter_v1.py`는
**서버 소유** `read_history_page(channel_id, cursor, limit)`에
의존한다. ChatGPT Slack 도구 연결만으로 Windows 호스트에
Slack 사용자 OAuth 토큰/권한이 제공되는 것은 아니다.

## 일회성 실호스트 정적 검사

`tests/test_ucie_slack_host_reader_capability_readonly_v1.py`는
기존 Slack 권한 기록을 무시하고 "미배포" 결론을 내리지 않도록
다음 UCIE-only 소스에 국한해 안전한 기능 표식만 확인한다.

- `D:\UCIE_PREVIEW\UCIE_ADMIN\src\ucie_admin`
- `D:\UCIE_DATA\library_app\private_lib`
- `D:\UCIE\src\ucie_miner`

토큰, 환경변수 내용, 프로필, 명령줄, 원본 코드, 다른 프로젝트,
일반 사용자 파일 및 실행 중 프로세스를 조회하지 않는다.
Python 파일 180개/디렉터리 40개씩 제한하고, 없는 경로와
불완전한 조사는 제한 사실을 영수증에 보존한다.

이 검사에서 Slack 관련 코드 표식이 발견돼도 **실제 Slack
인증/권한 및 조회 성공이 증명되는 것은 아니다**.

## 운영 활성화의 마지막 인수 게이트

1. 기존 UCIE 관리 서버의 승인된 Slack 읽기 구현과 접근 정책을
   서버 소유자가 제공할 것. 기존 권한이 없다면 별도 OAuth
   연결/승인 절차를 통해서만 제공할 것.
2. 호출자는 정확 UCIE 채널과 페이지 요청만 지정해야 하며,
   토큰/채널 ID/콜백 코드를 MCP 사용자 인자로 받아서는 안 된다.
3. 실제 Windows 서버에서 2026-10-21/25 기준 3개 Slack
   앵커와 페이지 종료를 조회하고, 기존 history verdict와
   동일한 결과가 나오는지 재현할 것.
4. 서버 소유 콜백이 없으면 `HISTORY_RECHECK_REQUIRED_BLOCK_VERDICT`.
   ChatGPT가 수동 검색한 결과/합성 테스트를 "서버 자동연동 PASS"로
   대체하지 말 것.
5. 기존 C40, 운영 DB, 예약 작업, 기존 관리자 9도구,
   별도 승인형 4개 쓰기 도구는 변경하지 않는다.

`CHATGPT_SLACK_CONNECTED`는 확인된 사실이다.
`WINDOWS_SLACK_READER_LIVE`는 독립 실호스트 통과 전까지
`NOT_VERIFIED`로 유지한다.
