# UCIE 관리자 MCP 실제 제공 경로 구분 (2026-11-03)

> **정정(2026-11-03 / 과거 Slack 전수 재검토):** 이 문서의 34개
> `D:\UCIE_DATA\library_app` Python 파일 검색에서 관리자 정의를
> 못 찾았다는 사실은 **기존 관리자 배포 경로가 없다는 증거가 아니다.**
> 기존 관리자 구현은 2026-10-23 PR #78의
> `src/ucie_admin/mcp_registration.py`이며 승인형 소유자 실행기는
> `scripts/ucie_owner_admin_mcp_launch.ps1`; Windows staging source는
> `D:\UCIE_PREVIEW\UCIE_ADMIN\src`로 별도 구성돼 있었다.
> 2026-10-25 소유자 실제 `APPROVE` 후 9개 관리도구/검색 검증:
> https://kangsoolnc.slack.com/archives/C0CA4AW06BH/p1792896036978529
> 2026-10-25 별도 보호 루트 생성 영수증:
> https://kangsoolnc.slack.com/archives/C0CA4AW06BH/p1792899889147509
> 따라서 `OWNER_NOT_FOUND`/`DEPLOY_PATH_ABSENT`를 이 검사로
> 확정하는 것은 금지된다. 현재 플러그인 백엔드 소유권·신규 4개
> 도구 등록·원격 요청별 인증은 별도 실증 대상이다.
> **강제 게이트:** `src/ucie_miner/ucie_admin_history_verdict_v1.py`
> (외부 Slack 검색 adapter가 없으면 판단 차단).


## 최소 범위 결론

기존 UCIE Admin 플러그인은 정상이며, `ucie_admin_write_text`(SHA-256 임대,
백업, 원자적 쓰기) 및 `ucie_admin_test_one_file`가 이미 작동한다.
그러므로 일상적인 UCIE 코드 수정은 새로운 네 도구를 기다릴 필요가 없다.

그러나 PR #175의 `ucie_owner_scope_{status,enroll,revoke,apply}`는
14일·12회 제한의 부가적인 일괄 적용/승인 기능이다. 이 기능은 현재
MCP 서버에 등록됐다는 증거가 없다.

실제 UCIE 호스트에서 현재 알려진
`D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py`는
`MCPServer`와 `search_ucie_evidence`만 직접 노출한다.
이 파일이 기존 UCIE Admin 플러그인의 실행 진입점이라고 가정하지 않는다.
`mcp_code` scope의 bounded list가 현재 도구 오류를 반환했으므로,
해당 스코프를 파일 쓰기나 서비스 재시작 경로로 가정하지 않는다.

## 한 번의 안전한 읽기 전용 매핑

`tests/test_ucie_admin_provider_mapping_readonly_v1.py`는 오직
`D:\UCIE_DATA\library_app` 아래의 제한된 Python 파일들을 조사하여
관리 도구 이름이 등장하는 파일의 **상대 경로만** 보고한다.
코드, 프로필, 명령줄, 토큰, 비밀번호는 출력하지 않는다.
최대 400 Python 파일·100 디렉터리까지만 확인하며,
범위를 초과하면 결과를 완전한 인벤토리로 주장하지 않는다.

도구가 이 스캔에서 발견되지 않는다고 해서 원격 관리자 구현이
없다는 뜻은 아니다. 권한이 있는 플러그인 관리자가 실시간 서버
소유/엔트리포인트를 증명해야 한다.

## 실제 등록 게이트

1. 실제 UCIE Admin 도구를 소유한 서버를 독립적으로 식별한다.
2. 요청마다 소유자 권한을 검증하거나, **승인된 정확 SHA의 일회용 티켓**
   및 보호된 ACL을 통해 승인 범위 밖 동작이 불가능하게 한다.
3. 실서버 도구 등록 및 실패 시 원상복구를 격리 시험한다.
4. 기존 C40 작업과 운영 DB는 유지하고 추가 도구를 배포한다.
5. 재연결 후 실제 tools/list와 거부/승인 동작 영수증을 확인한다.

운영 인증·ACL 검증 전에는 새 apply를 활성화하거나 성공으로 표시하지 않는다.
