# UCIE C40 — 11번째 Slack MCP 도구 로드용 소유자 1회 재연결 (2026-11-04)

**현 상태**: ChatGPT UCIE Plugin에 기존 관리자 9개 + 기존 Search 1개만 보이며 신규
`ucie_slack_history_verify_readonly`가 Action control에도 미표시.

현재 C40 PID 49180은 11월 3일 정상 Windows 로그인 복구 때 시작된 클라이언트이며
등록 파일은 11월 4일 변경됨. 기존 실행 중 프로세스는 새 소스를 다시 로드하지 않을
수 있음. 별도 fresh C40 MCP Python 프로세스에서 기존 9개 관리자 도구와 신규 1개
등록 성공, 실제 Slack Windows API 고정 앵커 3건 PASS, CI 4/4 PASS.
등록 소스를 **다시 설치하지 않는다**.

## 실행 전 확인 (무중단)

```powershell
& 'D:\UCIE\scripts\ucie_c40_slack_mcp_reload_owner_once.ps1' -Mode Preview
```

예상 성공: `UCIE_C40_MCP_RELOAD_PREVIEW_READY`, task Running,
owner/Highest/Interactive, 정확한 UCIE C40 한 개, 최신 `CYCLE_OK`,
기존 서버 및 **등록 소스 + 신규 Reader SHA** 일치.

## 변경을 수반하는 소유자 승인형 1회 재연결

사전에 저장되지 않은 작업과 연결 단절에 대비해 **Windows 소유자 관리자 권한
PowerShell**을 열고, 안전한 별도 복구 수단이 유지되는지 확인한다.
원격 ChatGPT MCP에서는 실행하지 않는다.

```powershell
& 'D:\UCIE\scripts\ucie_c40_slack_mcp_reload_owner_once.ps1' -Mode Apply -OwnerOnlyConfirmed
```

프롬프트: `UCIE_C40_MCP_RELOAD_ONCE`.

- 지정된 기존 UCIE C40 클라이언트의 경로/PID/생성시각/소유자/작업/최신
  감시 로그를 **승인 직전과 직후** 두 번 검증한다. 실행 중 한 개가 아니거나
  다른 실행 경로가 감지되면 중단한다.
- 새 파일 `D:\UCIE\.ucie_bridge_state\c40_slack_mcp_reload_once_v1.json`을
  **CreateNew**로 만든 뒤, 오직 확인한 기존 UCIE C40 클라이언트 한 개를
  종료한다. 재시작·재등록·프로필 변경 명령은 실행하지 않는다.
- 이미 실행 중인 정확한 `UCIE-C40-Recover` 소유자 Highest supervisor가
  자연스럽게 새로운 클라이언트 한 개를 시작하도록 두고 최대 450초 관측한다.
  새 PID/생성시각/최신 `CYCLE_OK + UCIE_C40_CHILD_STARTED/clients=1` 영수증
  모두 일치해야 `UCIE_C40_MCP_CLIENT_RESTARTED_ONE`을 출력한다.
- 실패 시 두 번째 클라이언트를 임의 실행하지 말고 정확한 복구 작업 상태만
  확인한다. 기존 Windows 재로그인 자동복구 경로는 별도 확보되어 있다.
- 기존 관리자 도구/운영 DB/타 예약 작업·프로젝트/토큰은 변경하지 않음.
- 이는 **C40 클라이언트 재생성 증명**이며 새 도구가 ChatGPT에 표시됐다는
  증명은 아님. 연결 재개 후 ChatGPT 기존 플러그인 Action control > Refresh,
  새 도구 **명시적으로 사용 승인**, 새로운 대화에서 11개 도구 확인 후
  고정 인자 없는 도구 실제 호출로 Slack 앵커 3건을 확인한다.

## 기타

이 스크립트는 과거 이미 소비된 단발성 장애실험 영수증
`c40_owner_loss_drill_v1.json`을 재사용하거나 덮어쓰지 않는다.
CI에서 PowerShell 문법·안전 범위를 검사하고 Windows 호스트에서는
**Preview만 실행**한다. Apply를 자동 시험하지 않는다.

코드 정본 PR #175 및 GitHub Issue #176의 최신 증거와 함께 점검한다.
