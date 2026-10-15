# UCIE Stage 15 — 외부 공개 오류 수정의 구조화된 증거 분석

Stage 13은 승인 저장소 다섯 곳의 공개 과거 PR 변경 이력을
SHA-256·머지 SHA·PR 번호·발행일 등 메타데이터로 누적합니다.
Stage 14는 공식 공개 문서·릴리스·GHSA의 공개 메타데이터 및
문서 변경 해시를 추적합니다.

Stage 15는 그 위에서 **실제 공개 PR 변경 파일과 공개 릴리스
API를 추가로 조회**하여 오류 예방 검토에 필요한 정형화된
단서(예외·동시성·API 계약·버전·시험, 변경 전후 신호, 테스트
파일 수)를 생성합니다.

## 진짜 외부 자료 분석과 검증 경계

1. Stage 13의 기존 공개 PR 인덱스를 `mode=ro`로 확인하고
   5개 승인 독립 저장소의 `source/pr/merge SHA/metadata digest`
   신원이 올바른 후보만 선택합니다.
2. 이전 분석 여부를 Stage 15 **별도 SQLite**에서 비교하여
   새 과거 이력 또는 증거 수정 후보만 선택합니다.
3. 후보당 최대 2회 익명 GitHub 공개 API:
   해당 PR의 `/pulls/{PR}/files?per_page=30` 및 저장소의
   `/releases?per_page=10`.
   기존 Stage 9.4의 보수적인 패치 신호 감지와 공개 릴리스
   힌트를 그대로 사용합니다. 시간당 최대 **후보 2건/4 GET**.
4. 원문 코드·diff·PR 제목·파일 경로·릴리스 본문·외부 명령은
   저장하지 않습니다. 위험한 외부 코드를 실행하지 않습니다.
   승인된 오차범위/시그널명, 테스트 파일 수, 코딩 오류 패턴,
   출처 및 증거 해시만 저장합니다.
5. 안전한 호출 가이드와 회귀시험 계획은 외부 PR 텍스트로
   새로 만들어 실행하지 않고, **UCIE 내부에 미리 작성된
   제한된 프로필**에서 선택합니다.
6. 영향을 받는 배포 버전은 `UNDETERMINED`, 라이선스와
   독립 검증은 `UNVERIFIED`, 최종 상태는
   `UNVERIFIED_REVIEW_CANDIDATE_ONLY`입니다. 저장소의
   공개 릴리스가 있다는 사실만으로 특정 PR의 릴리스
   포함을 증명하지 않습니다.

새 결과 파일:
`D:\UCIE\runtime\stage15_unverified_fix_evidence.sqlite3`.
Stage 15의 실행은 기존 운영 마이너·Knowledge·Stage 10~14
SQLite를 수정하지 않습니다.

## 안전성·외부 API 예산

기존 UCIE 예약 작업 `UCIE-PublicMiner-Hourly`을 그대로 사용하며
새 스케줄러는 등록하지 않습니다. 각 Stage는 별도 활성화 파일이
없으면 새 외부 조회나 새 DB 기록을 하지 않습니다.

공개 API의 설계상 주기당 상한:
Stage 11 최근 변경 최대 8 GET + Stage 13 과거 PR 최대 5 GET +
Stage 14 공식 문서/릴리스/보안 자료 최대 3 GET +
Stage 15 심층 PR 분석 최대 4 GET = **최대 20 GET/실행 주기**.
동일 PC/IP에서 다른 GitHub 요청이 있으면 익명 API 사용 제한이
더 빠르게 도달할 수 있습니다. 403/429, 페이지 누락,
릴리스 정보 부재 등을 규칙 검증 PASS로 간주하지 않습니다.

## 별도 활성화 (기본 OFF)

Stage 15 활성화 파일은 다른 Stage와 독립입니다.

- 경로: `D:\UCIE\runtime\stage15_fix_evidence_opt_in.txt`
- 정확한 ASCII 내용: `UCIE_STAGE15_FIX_EVIDENCE_OPT_IN_V1`

CI PASS 및 검토된 `main` 로컬 반영 후 **사용자가 승인한
경우에만** 파일을 생성합니다.

```powershell
$root = 'D:\UCIE'
$py = "$root\.venv\Scripts\python.exe"
$marker = "$root\runtime\stage15_fix_evidence_opt_in.txt"

# 다음 두 명령은 외부 API 호출이나 DB 쓰기 없이 상태만 조회
$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = "$root\src"
    & $py -B -m ucie_miner inspect-external-history
    & $py -B -m ucie_miner inspect-fix-evidence
} finally {
    $env:PYTHONPATH = $prior
}
```

수집 실행은 활성화 파일을 명시적으로 생성한 뒤:

```powershell
if (Test-Path -LiteralPath $marker) { throw 'Existing Stage 15 opt-in must be inspected first' }
Set-Content -LiteralPath $marker -Value 'UCIE_STAGE15_FIX_EVIDENCE_OPT_IN_V1' -Encoding Ascii -NoNewline

$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = "$root\src"
    & $py -B -m ucie_miner enrich-public-fix-evidence-once --live
    & $py -B -m ucie_miner inspect-fix-evidence
} finally {
    $env:PYTHONPATH = $prior
}
```

이 명령은 기존 예약 작업을 건드리지 않습니다. 실제 수집 후
외부 근거 후보 수와 실패 여부를 확인해야 운영 동작을 PASS로
볼 수 있습니다. 활성화 파일을 제거하면 후속 수집이 중지되며,
이미 수집된 미검증 후보를 자동 삭제하지 않습니다.

## 남은 필수 검증

- PR 파일 목록 첫 페이지는 최대 30개라서 일부 경로가
  잘릴 수 있습니다. 원본 PR SHA와 수집 시점의 PR 파일
  상태가 독립적으로 일치하는지도 별도 확인이 필요합니다.
- 릴리스 포함 버전, 정식 보안 권고 연결 및 공식 문서
  의미 변화는 현재 추정하지 않습니다.
- 테스트 파일 수가 양수여도 실제 동작의 회귀 시험
  성공/실패를 증명하는 것은 아닙니다.
- 원본 소스 실행·자동 패치 적용·서명된 규칙 승격·모델
  가중치 학습은 허용하지 않습니다.

Stage 15가 하는 일은 *외부 근거를 구조화해 후보로 축적*하는
것이지, 사실 확인이 안 된 수정 제안을 이미 학습된 정식
코딩 규칙으로 승격하는 일이 아닙니다.
