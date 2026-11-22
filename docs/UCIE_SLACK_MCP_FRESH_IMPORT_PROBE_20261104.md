# UCIE MCP 새 도구 미노출 — 소유자 PC PowerShell 읽기 전용 진단 V1

시점: 2026-11-04 KST. UCIE 이외의 모든 프로젝트·파일·비밀정보 접근 금지.

**관측된 사실:** `D:\UCIE_PREVIEW\UCIE_ADMIN\src\ucie_admin\mcp_registration.py`
SHA256 `f75a9780...` 등록 데코레이터 10개(기존 관리자 9개 + Slack 읽기 도구 1개).
C40 Owner Task Running / Highest / Interactive / 단일 클라이언트.
반면 ChatGPT 연결 UCIE 플러그인 `tools/list` 노출 목록에는 새 도구
`ucie_slack_history_verify_readonly`이 아직 없다.

**설명 가능한 원인 후보**: (A) C40 실행 중 Python 서버가 이전 등록 모듈을
캐싱, (B) C40가 다른 UCIE Python 실행 파일 또는 구버전 모듈을 읽음,
(C) ChatGPT 플러그인 도구 메타데이터가 이전 목록으로 유지됨.
소스 파일만 수정한 사실로 어느 원인인지 단정할 수 없다.

## Windows PowerShell 검사 (읽기 전용)

```powershell
& 'D:\UCIE\scripts\ucie_slack_mcp_power_shell_probe_v1.ps1' -Mode Status
& 'D:\UCIE\scripts\ucie_slack_mcp_power_shell_probe_v1.ps1' -Mode FreshImport
```

- Status는 원본 파일 SHA와 **기존 C40 정확 Task**를 검사하며
  서비스/프로세스/작업/토큰을 변경하지 않는다.
- FreshImport는 **기존 C40 MCP 전용** `D:\UCIE_DATA\.venv_mcp\Scripts\python.exe`에서
  SHA-pinned UCIE Admin staging 모듈을 새로 import하고,
  실제 FastMCP 대신 기능 없는 FakeFastMCP에 10개 도구명만 등록한다.
  WinCred 토큰·Slack API·원본 메시지 접근과 도구 실행을 하지 않는다.
- `UCIE_FRESH_PROCESS_TEN_TOOLS_PASS`이면 **디스크의 신규 모듈을 새 Python이
  정상 import해 도구를 등록할 수 있음**이 증명되나, 실행 중 C40 및
  ChatGPT 플러그인 도구 캐시가 갱신되었다는 증거는 아니다.
- 반대로 import가 실패하면 기존 C40을 재시작하지 말고
  SHA/경로/등록 원인을 고쳐야 한다.

`UCIE_FRESH_PROCESS_TEN_TOOLS_PASS` 후에도 ChatGPT에서 신규 도구가 보이지
않으면, 먼저 서버의 현재 프로세스/실제 모듈 import origin과 ChatGPT 플러그인
tool discovery 갱신을 별도 확인한다. 무작정 기존 C40 프로세스를 종료하거나
두 번째 C40을 시작하지 않는다.

관련 이전 승인: https://github.com/tmdrkdtn1-project/UCIE/pull/78,
https://github.com/tmdrkdtn1-project/UCIE/pull/175.
