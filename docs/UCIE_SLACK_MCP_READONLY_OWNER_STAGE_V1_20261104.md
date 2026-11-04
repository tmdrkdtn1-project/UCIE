# UCIE Slack 이력 MCP 읽기 전용 도구 설치 V1 (2026-11-04)

## 이미 확인된 사실

- 소유자 Windows `-Mode Verify` 결과 `UCIE_SLACK_WINDOWS_READ_ONLY_HISTORY_VERIFIED`.
  검증 앵커 3개 모두 일치하고 `@ucie_evidence_reader`가
  Slack `#ucie-project`에 참여함.
- 기존 관리자 FastMCP 9도구 배포 등록 정본: PR #78
  `src/ucie_admin/mcp_registration.py`. 실제 UCIE C40은 한 개
  클라이언트로 정상 동작 중.
- GitHub PR #175의 owner-local WinCred reader가 이미
  `D:\UCIE\src\ucie_miner\ucie_slack_windows_reader_v1.py`에 설치됨.

## 통합 방식과 보안 경계

신규 `src/ucie_miner/ucie_slack_mcp_owner_dispatch_v1.py`는
**인자 없는** 고정 결과 검증 함수이다. 기존 소유자 WinCred를
직접 읽지 않고, 다음 명령 한 가지만 지정된
`D:\UCIE\.venv\Scripts\python.exe`로 실행한다.

`-B -m ucie_miner.ucie_slack_windows_reader_v1 verify`

네 핵심 UCIE Python 소스의 Git blob을 고정해 코드 변경 시 실패
차단하고, 사용자 호출에서 경로·채널·토큰·명령·실행 옵션을 받지
않는다. Python child는 `D:\UCIE\src`만 PYTHONPATH로 받으며
실패 로그와 원본 Slack 메시지는 반환하지 않는다. 성공 응답도
고정 앵커 3개 및 불변의 보안 상태만 노출한다.

신규 `scripts/ucie_owner_stage_slack_mcp_readonly_v1.py`는
**기본 Preview, `--apply`는 별도 소유자 로컬 대화형 승인**
방식이다. PR #78의 관리자 등록 소스 원본 Git blob
`8516baa69e768f2589d5df305200ebcd99b76e0d`를
및 2026-11-04 실호스트에서 독립 확인한 **기존 9도구 보존 등록본**
Git blob `c26be40528d421bf384acbccd1501a1c522cc666` 중
하나와 정확히 일치하는 경우에만 단일 UCIE staging 폴더
`D:\UCIE_PREVIEW\UCIE_ADMIN\src\ucie_admin`에 두 파일을
배치한다.

1. `slack_history_readonly_mcp_v1.py` 새 파일 복사
2. `mcp_registration.py`에
   `@fastmcp.tool(name="ucie_slack_history_verify_readonly")` 추가

기존 `ucie_admin_*` **정확히 9개는 불변**이다.
새 이름에 `ucie_admin_` 접두어를 쓰지 않아 기존 owner-launcher의
`admin_count == 9` 검증을 그대로 유지한다.
프로세스/스케줄러/터널/운영 DB·기존 tool 등록을 바꾸지 않고,
기존 등록 파일은 백업 후 원자 교체한다.

## 소유자 Windows 수용 절차

운영 C40을 건드리기 전에 먼저 Preview만 실행한다.

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' 'D:\UCIE\scripts\ucie_owner_stage_slack_mcp_readonly_v1.py'
```

`UCIE_SLACK_READONLY_STAGE_PREVIEW_READY`이면 신규 슬랙 기능
정적 준비와 기존 PR #78 등록 파일의 버전 일치가 통과한 것이다.
그때만 소유자가 별도로 다음 명령을 대화형 PowerShell에서
실행할 수 있다.

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' 'D:\UCIE\scripts\ucie_owner_stage_slack_mcp_readonly_v1.py' --apply
```

프롬프트에 `UCIE_SLACK_MCP_READONLY_STAGE_ONLY` 입력.
이 작업은 **서버 소스를 배치할 뿐**, 실행 중 C40 프로세스에서
도구가 나타났다는 뜻은 아니다. 설치 전 정확한 git blob이
변경돼 있었다면 중단하고 과거 PR #78 및 소유자 승인 이력을
재검토한다. 기존 ACL을 약화해 설치하지 않는다.

적용 후에는 별도 승인된 C40 시작/재접속 시점에
`tools/list`로 `ucie_slack_history_verify_readonly` 존재,
기존 9개 `ucie_admin_*` 및 `search_ucie_evidence` 보존,
읽기 전용 새 도구 실호출의 앵커 3개 PASS를 독립 검증한다.
현재 UCIE Admin bridge에는 C40 재시작 권한이 없으므로
**재시작을 자동 실행하지 않는다.**

## 실행 보증 경계

- 과거 소유자 승인, 기존 관리자 배포 경로 확인: **PASS**
- WinCred 소유자 Windows Slack 실제 조회: **PASS**
- 단독 read-only MCP 디스패처의 격리 테스트: **CI/호스트 시험 후 판정**
- 기존 관리자 서버 스테이징: **소유자 --apply 및 실제 영수증 전 PENDING**
- 실제 원격 MCP 도구 등록·실호출: **별도 실측 전 PENDING**
- 신규 `status/enroll/revoke/apply` 소유자 쓰기 도구: **NO-GO 유지**

관련 과거 정본: https://github.com/tmdrkdtn1-project/UCIE/pull/78
관련 현재 코드: https://github.com/tmdrkdtn1-project/UCIE/pull/175
