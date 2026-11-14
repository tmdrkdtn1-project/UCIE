# UCIE 관리자 소유·배포·신원 증거 필수 재검토 규칙 V1

작성: 2026-11-03 (KST) · 범위: **UCIE ONLY** · 코드 게이트:
`src/ucie_miner/ucie_admin_history_verdict_v1.py`

## 실제로 다시 확인한 과거 근거

이번 재검토에서 Slack의 UCIE 공개 채널 전체 이력(2026-10-20
개설부터 2026-11-03, 총 4개 페이지)을 점검하고, 과거 메시지 검색
및 GitHub PR 원본을 교차 검증했다.

1. 2026-10-25 11:40 KST
   https://kangsoolnc.slack.com/archives/C0CA4AW06BH/p1792896036978529
   - PR #78 소유자 승인 실행기에서 `APPROVE`를 입력한 후
     `UCIE_OWNER_LOCAL_ADMIN_AND_LEGACY_SEARCH_VERIFIED` 보고,
     기존 관리자 도구 **9개 + 검색 도구** 로컬 확인.
   - 같은 시점 ChatGPT `ucie_admin_capabilities`와 Git 상태 조회도
     실제 성공. 당시 PID와 ChatGPT 연결의 일대일 매핑까지 증명한
     영수증은 아니었음.
2. 2026-10-25 12:44 KST
   https://kangsoolnc.slack.com/archives/C0CA4AW06BH/p1792899889147509
   - 소유자 Windows에서 ProgramFiles 하위 `UCIE_UnattendedHost`
     보호 폴더 생성 및 관리자/SYSTEM ACL 자체검증 보고.
   - 해당 경로의 존재 이력은 확인됐으나 이후 독립 OS AccessCheck,
     서비스 설치, **신규 owner-scoped grant 저장소 배포**를 자동으로
     증명하지는 않음.
3. 2026-10-21 01:19 KST
   https://kangsoolnc.slack.com/archives/C0CA4AW06BH/p1792513195589169
   - C45 Auth0 사용자 `ucie:read` 검증과 C41 로컬 stdio
     플러그인 등록 미완료라는 **당시 별개 상태** 기록.
4. 원본 코드와 배포 정본:
   https://github.com/tmdrkdtn1-project/UCIE/pull/78
   `docs/UCIE_LOCAL_ADMIN_BRIDGE_V1.md`
   `scripts/prepare_ucie_admin_mcp_registration.py`
   `scripts/ucie_owner_admin_mcp_launch.ps1`
   `src/ucie_admin/mcp_registration.py`.
   소스 위치 `D:\UCIE_PREVIEW\UCIE_ADMIN\src`,
   기존 MCP 서버 `D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py`,
   소유자 실행기의 기존 C40 프로필을 구별해 기록.

이 사실 때문에 “UCIE 관리자 소유자 승인 이력 없음”,
“기존 관리자 배포 경로 없음”, “기존 인증 근거 전무”는 **잘못된
부재 주장**이다. 반면 정확한 ChatGPT 플러그인 백엔드 소유권,
신규 owner-scoped MCP 도구 4개의 운영 등록, 현재 요청별 원격
사용자 신원은 이 과거 근거만으로 인증된 사실이 아니다.

## 엄격한 판정 절차 — 누락 결론 금지

UCIE 관리자 **소유·배포·신원·도구 등록**에 관하여
`ABSENT`, `MISSING`, `UNKNOWN`, `NOT_FOUND`, `UNVERIFIED`
등의 부정 판정을 내리기 **직전에**:

1. 기존 UCIE Slack #ucie-project 기록을 읽고, 코드에 고정된
   네 검색어 `PR #78`, `UCIE_OWNER_LOCAL_ADMIN_AND_LEGACY_SEARCH_VERIFIED`,
   `UCIE_UnattendedHost`, `Auth0`를 **다시 검색**한다.
2. 모든 페이지를 끝까지 순회한다. 중단/오류/누락/삭제/이전
   출처와 불일치 시 즉시 `HISTORY_RECHECK_REQUIRED_BLOCK_VERDICT`.
   Slack 부재·조회 오류는 운영 배포 부재의 증거가 아니다.
3. 과거 고정 Slack permalink/타임스탬프/핵심 영수증 문구와
   PR #78 소스 정본을 교차 확인한다.
4. 과거 성공과 **현 시점** runtime 상태는 분리한다.
   과거 소유자 로컬 승인과 현재 플러그인 backend 소유권,
   로컬 인증과 원격 요청별 인증, 기존 9개 도구와 신규 4개 도구,
   P10 보호 폴더와 신규 grant 저장소를 서로 대체하지 않는다.
5. 최종 판정에는 검색일시, 원본 permalink, 정확한 관측 범위,
   과거 확정 사실, 현재 검증이 필요한 사항을 반드시 함께 기록한다.
   부족하면 `PENDING/UNVERIFIED_IN_SCOPE`이지
   `DOES_NOT_EXIST`가 아니다.

## 코드 강제 경계

`judge_negative_ucie_admin_claim`은 항상
`recheck_ucie_history`를 호출한다. 호스트에서 제공하는 신뢰된
Slack 검색 어댑터가 없거나 질의/페이지/과거 증거가 불완전하면
**절대 최종 부재 판정하지 않는다**. 원격 MCP 사용자의 입력값에
`reviewed=true`를 넣는 것으로 통과할 수 없다. 이미 만들어 둔
오프라인 JSON 영수증도 '방금 재검토'를 대체하지 않는다.

코드는 독립 Slack 네트워크 연결/토큰을 내장하지 않는다. 따라서
현재 CLI에서 검색 어댑터가 제공되지 않으면 반드시 RECHECK_REQUIRED
상태로 종료하며, “Slack 재검토 자동 연결 완료”라고 주장하면 안 된다.
향후 승인된 UCIE Slack 연동 주체가 서버 소유의 adapter를 연결해야
실시간 검색 검증이 가능하다. 테스트는 해당 adapter의 fake만 사용한다.

**이 게이트는 판단 증거 규칙일 뿐 원격 MCP 권한 인증이 아니다.**
정상 통과해도 신규 4개 도구의 `apply` 활성화, grant 생성,
서비스 재시작, ACL 수정, 규칙 승격을 승인하지 않는다.

## 운영 사용

`PYTHONPATH=D:\UCIE\src` 환경에서
`python -m ucie_miner.ucie_admin_history_verdict_v1` 실행 시 실제
Slack adapter가 없는 한 종료 코드 3,
`HISTORY_RECHECK_REQUIRED_BLOCK_VERDICT`로 실패 차단된다.

배포된 UCIE 관리 기능을 없다고 결론 내리기 전에 도구를 연결해
필수 Slack 재검색 후 결론을 받아야 한다. GitHub PR에만 작성했다고
ChatGPT/Slack 자체의 전역 규칙이 자동으로 변경되는 것은 아니며,
본 모듈을 실제 판단·보고 엔드포인트에서 호출하도록 연결하는 일이
별도 배포 게이트다.
