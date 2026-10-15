# Stage 13: 외부 공개 기술 변경이력 장기 백필 엔진

**목표:** 기존 시간당 수집의 최근 20개 PR 수준을 넘어, 허용된
5개 독립 제3자 오픈소스 저장소에서 수년 전부터 누적된 공개
오류 수정 PR 메타데이터를 페이지별로 점진 수집하여 UCIE
전용 독립 SQLite에 축적한다. 공개 원문 코드와 PR 제목을
저장하거나 실행하지 않는다.

## 실제 외부 수집 범위

- `python/cpython`
- `PowerShell/PowerShell`
- `git/git`
- `modelcontextprotocol/python-sdk`
- `actions/runner-images`

GitHub REST API `GET /repos/{owner}/{repo}/pulls?state=closed&sort=updated&direction=desc&per_page=20&page=N`만
호출하며, 각각 정확한 저장소·공개 PR URL·merge SHA·UTC 병합일을
검사한다. 병합되지 않은 폐쇄 PR과 미분류 PR은 지식 후보로
저장하지 않는다.

- 실행당 최대 **5회 공개 GET** (출처당 이전/다음 페이지 1회),
  최대 페이지 **500/저장소** 및 페이지당 20개 메타데이터.
  최대 탐색 분량은 5개 저장소 합산 **50,000 PR 메타데이터 조회**;
  실제 누적 지식 후보는 필터에 따라 훨씬 적을 수 있다.
- SQLite `runtime/stage13_external_public_history.sqlite3`에
  저장소별 `next_page`, 스캔 상태, 원본 없는 SHA-256, 정규화
  태그, PR 번호, 머지 SHA 및 병합시각만 유지한다.
- 각 페이지 저장과 다음 페이지 커서 업데이트는 한 SQLite
  트랜잭션으로 처리된다. 동일 기록은 중복 저장하지 않는다.
  다음 실행은 각 출처의 커서에서 계속한다. 짧은 페이지는
  EXHAUSTED, 최대 500페이지 도달 시 MAX_DEPTH_REACHED로
  종료한다. **모든 GitHub 역사를 완전히 수집했다는 의미는 아니다.**
- 원격 데이터 필드가 비정상적이면 해당 페이지 커서를 넘기지
  않는다. 요청 실패 시 해당 페이지 재시도 가능 상태를 유지한다.
  `X-RateLimit-Remaining`이 12 미만이면 추가 호출을 중지한다.
  이는 IP 공유 상황에서 보장된 제한 회피가 아니며, 외부 API
  403/429는 실패·중단 상태로 보고한다.
- GitHub의 `sort=updated` 목록은 스캔 중 변할 수 있어,
  오래된 페이지로 넘어가는 동안 일부 PR이 누락될 수 있다.
  따라서 탐색 범위와 건수를 보고하며 **완전성 보증은 하지 않는다.**

GitHub API의 익명 기본 한도는 통상 IP 기준 60회/시간이다.
Stage 11의 최근 메타데이터 수집과 본 백필은 요청 예산을
공유하므로 임의 병렬 실행·강제 반복 실행은 금지한다.
권한 토큰을 사용하거나 다른 저장소를 허용 목록에 넣지 않는다.

## 자동 실행은 별도 승인 후 활성화

Stage 13은 Stage 11/12와 **독립적인 로컬 승인 파일**로 동작하며,
없으면 네트워크 조회 또는 신규 저장소 변경 없이 기존 동작 유지:

- 경로: `D:\UCIE\runtime\stage13_history_opt_in.txt`
- 정확한 ASCII 내용: `UCIE_STAGE13_HISTORY_OPT_IN_V1`

운영자 수동 명령 (검토된 코드 병합 및 로컬 갱신 후):

```powershell
$prior = $env:PYTHONPATH
try {
  $env:PYTHONPATH = 'D:\UCIE\src'
  & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner inspect-external-history
  # 명시적 활성화는 별도로 결정:
  # Set-Content 'D:\UCIE\runtime\stage13_history_opt_in.txt' -Value 'UCIE_STAGE13_HISTORY_OPT_IN_V1' -Encoding Ascii -NoNewline
  # 이후 일회성 검증을 하려면 --live 필요:
  # & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner backfill-external-history-once --live
} finally {
  $env:PYTHONPATH = $prior
}
```

운영자 승인 후 기존 `UCIE-PublicMiner-Hourly` 시간당 실행 안에서
Stage 11 최신 후보 → Stage 12 검토 준비 → Stage 13 공개 과거
이력 백필을 **순차 실행**한다. 새 예약 작업은 등록하지 않는다.
운영자가 Stage 13만 중지하려면 승인 파일을 지우면 된다.
기존 DB나 기존 후보를 자동 삭제하지 않는다.

## 외부 빅데이터의 확장 경계

이 Stage는 오직 **공개 GitHub PR 변경 이력의 장기 수집 기반**이다.
공식 문서·보안 권고·릴리스 노트의 장기 히스토리 백필,
버전별 행동 회귀 검증, 독립 검토와 규칙 승격은 별도 단계다.
전체 원본 데이터를 미러링하거나 무차별 크롤링하지 않으며,
원문 재배포·외부 코드 실행·개인 데이터 수집은 금지한다.

후보 상태는 계속 UNVERIFIED_CANDIDATE_ONLY.
영구 신경망 모델 재훈련 / 자동 규칙 적용 / 서명 / 배포는 모두 0.
CI 통과는 소유자 Windows 예약 작업에서의 실제 백필 성공을
증명하지 않는다.
