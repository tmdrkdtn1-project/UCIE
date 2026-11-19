# UCIE Evidence Reader — 소유자 Windows Slack 봇 연결 V1 (2026-11-03)

범위: **UCIE ONLY**. 기존 UCIE C40, 관리자 9도구, Slack 과거 영수증 보존.
ChatGPT Slack 앱 권한과 Windows용 `UCIE Evidence Reader` 봇 권한은
서로 다르다. 이 프로그램은 Slack 앱 토큰을 채팅/파일/환경변수/명령줄
인자로 받지 않는다.

## 현재 관측

2026-11-03 ChatGPT Slack `slack_list_channel_members`를
`include_bots=true`로 호출했을 때 `#ucie-project`은 멤버
1명만 반환했고, 새 `UCIE Evidence Reader` 봇은 조회되지 않았다.
Slack 앱 생성이 끝났더라도 **Install to Workspace** 및
`/invite @UCIE Evidence Reader` 단계는 별도 확인이 필요하다.
단, 이는 ChatGPT가 조회한 시점의 상태이다.

## 소유자가 한 번만 해야 하는 작업

1. Slack https://api.slack.com/apps 에서 `UCIE Evidence Reader` 선택.
   OAuth & Permissions → Bot Token Scopes의 `channels:history`
   최소 권한 확인. 불필요한 `chat:write`, `groups:history`,
   `im:history` 등은 추가하지 않는다. 이미 설치한 앱의 범위가
   변경됐다면 **Reinstall to Workspace**.
2. Slack `#ucie-project`에 봇 초대. 다른 채널/DM 초대 금지.
   Bot User OAuth Token은 `xoxb-`로 시작한다.
3. **D:\UCIE**의 실제 소유자 Windows 계정에서 PowerShell 실행
   (새 C40 작업 등록·서비스 재시작 없이):
   
   ```powershell
   & 'D:\UCIE\scripts\ucie_slack_owner_connect.ps1' -Mode Preview
   & 'D:\UCIE\scripts\ucie_slack_owner_connect.ps1' -Mode Enroll
   & 'D:\UCIE\scripts\ucie_slack_owner_connect.ps1' -Mode Verify
   ```

   `enroll`은 **현장 대화형 터미널**에서만 실행되며
   `UCIE_SLACK_OWNER_ENROLL`을 한 번 입력한 후,
   Windows `getpass`의 숨김 입력으로 토큰을 받는다.
   코드를 복사해 토큰을 인자/명령문/PowerShell history/채팅에
   넣지 말 것. 첫 등록만 허용, 기존 자격증명 덮어쓰기 금지.
   비밀정보 원문 출력 금지.

   토큰은 Windows Credential Manager의 현 소유자
   `UCIE:EvidenceReader:SlackBot:v1`(generic credential,
   LocalMachine persistence)이라는 **고정 키**에 저장한다.
   다른 Windows 소유자 계정이나 별도 서비스 SID로 실행하면
   해당 자격증명을 못 읽을 수 있다. Windows 로그인 계정 및
   UCIE 서비스 실행 주체를 확인한 뒤 같은 사용자 컨텍스트에서
   검증한다. Credential Manager는 완전한 컴퓨터 악성코드
   차단 수단이 아니므로 PC 보안도 유지해야 한다.

## 안전한 시험과 보안 경계

`status`: 고정 키의 존재만 검사, Slack API 접속 없음.
`enroll`: 명시적 소유자 동의로 **그 키 하나**를 생성; 기존
운영 DB·스케줄러·C40·기타 프로젝트 변경 없음.
`verify`: 해당 토큰으로 Slack
`GET https://slack.com/api/conversations.history`
읽기 전용 요청을 **고정 채널 C0CA4AW06BH에 한정**해 수행.
HTTPS 인증서 검증, 리다이렉트 거부, 12초 타임아웃,
한 페이지 최대 100개, 응답 최대 2MiB,
토큰이 Authorization 헤더에만 들어가는 것을 코드로 제한.
Slack 오류/토큰 없음/앵커 불일치는
`HISTORY_RECHECK_REQUIRED_BLOCK_VERDICT`.
성공 조건은 2026-10-21/25의 고정 3개 영수증을
모두 다시 읽은 경우이며, 원본 Slack 메시지는 출력하지 않는다.

`verify` 성공은 Windows에서 Slack 읽기 API에 직접 접근하고
기존 근거를 확인했다는 **읽기 전용 인수**이다. 이 모듈을
기존 C40/UCIE 관리자 MCP의 실제 실행 서버에서 자동 호출하도록
등록한 것은 아니므로 `server_mcp_runtime_hook_wired=false`를
유지한다. 신규 owner 4도구 `apply` 권한도 부여하지 않는다.

## 주요 결과 및 실패 코드

- `UCIE_SLACK_TOKEN_NOT_ENROLLED`: 아직 소유자 입력 전
- `UCIE_SLACK_LOCAL_CREDENTIAL_STORED`: 로컬 저장 완료(원격 조회는 별도)
- `UCIE_SLACK_WINDOWS_READ_ONLY_HISTORY_VERIFIED`: 실제 검증 통과
- `CREDENTIAL_NOT_ENROLLED`: 저장소에 없음
- `SLACK_BOT_NOT_IN_UCIE_CHANNEL`: 채널 초대 필요
- `SLACK_MISSING_CHANNELS_HISTORY_SCOPE`: 봇 권한/재설치 필요
- `SLACK_TOKEN_NOT_AUTHORIZED`: 토큰 재발급/설치 상태 확인
- `PREVIOUS_SLACK_PROOFS_NOT_RECONCILED`: 과거 기록 미조회·불일치
- `HISTORY_RECHECK_REQUIRED_BLOCK_VERDICT`: **최종 부재 판정 금지**

토큰을 사용하지 않게 되면 Slack 앱 관리에서 토큰을 폐기하고
Windows 자격 증명 관리자에서 고정 항목
`UCIE:EvidenceReader:SlackBot:v1`을 소유자가 직접 삭제한다.
본 코드의 로컬 비밀정보와 GitHub/Slack 기록은 절대 교환하지 않는다.

참고:
https://docs.slack.dev/reference/methods/conversations.history/
https://docs.slack.dev/authentication/tokens/
https://learn.microsoft.com/windows/win32/api/wincred/nf-wincred-credreadw
https://learn.microsoft.com/windows/win32/api/wincred/nf-wincred-credwritew
