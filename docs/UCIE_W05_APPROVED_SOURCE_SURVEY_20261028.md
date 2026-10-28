# UCIE W05 — 기승인 공개 저장소 5개 일괄 조사 V1 (2026-10-28)

## 실제 사용자 PC에서 관측한 문제

- `repo:python/cpython`의 기존 W05 `--live --pages 3`를 **실제로** 실행해 공개 PR 60건 검토.
- 비병합 16, 병합된 오류 수정/회귀 제목 25, 병합됐지만 긍정 기술 제목 단서가 아닌 항목 19, 긍정 기술 제목 단서 **0건**.
- 승인된 원래 공개 GitHub PR URL 총 3회 요청 성공, 운영 DB 쓰기 0, P8 기술별 경험 추가 0.
- 사용한 API는 `state=closed&sort=updated&direction=desc`; 최근 **갱신된 닫힌 PR 표본**이다. 저장소 전체 병합 역사나 코드 원문을 검증하지 않았다. 후보 0을 개발 엔진/스킬 없음으로 확대해석하면 안 된다.

## 이번 기능: 근거 없는 제목 패턴 확대 대신 승인 소스 간 범위 비교

신규 모듈 `src/ucie_miner/public_capability_survey.py`:

- 오직 기존 다섯 승인된 공개 저장소 `python/cpython`, `PowerShell/PowerShell`, `git/git`, `modelcontextprotocol/python-sdk`, `actions/runner-images`의 기존 `public_feed_url(page=1..3)`만 사용.
- 호출자가 **명시적** `--all-approved` 또는 `--source-id repo:...` 중 하나 선택. `--live` 없이는 GET 0회이고 계획만 반환.
- `--pages 1|2|3`로 저장소마다 최대 60개 공개 PR 메타데이터(5개 전체 선택 시 최대 15회의 이미 허용된 GET). 미승인 공급원·추가 소스·임의 웹 검색·PR 원본 대량 수집은 없다.
- 기존 W05 `validate_w05_page_bundle`와 출처/병합 SHA/제목 기반 근거 검증 **그대로 재사용**. 반환은 source_id, 후보 수, 페이지/중복 수, 비병합·오류 수정 제목·모호한 제목·SHA 미고정·병합된 기타 미분류 항목의 개수. 후보 0이면 그대로 0. 제목·본문·패치/코드 원문은 출력하지 않는다.
- 실제 긍정 단서가 있는 소스는 `library_item_id`·공개 PR 링크·근거 SHA·목적코드·**UNVERIFIED** 상태만 반환. 공개 PR의 기술 유효성/실용성/라이선스/보안 검증이 아니다.
- `--try-first-party`를 추가로 명시하면, **전체 표본에서 1건의 제목 단서만** 선택해 UCIE 자체 작성 평가 레시피(증분 개발 엔진, 테스트 자동 선택, 학습 피드백) 하나만 실행. PR의 원본 코드는 다운로드·실행하지 않는다. 이 실기 기록은 디버깅용 반환값일 뿐, 별도 P8 원장/운영 SQLite에 저장하지 않는다.
- `network_requests`는 CLI가 실제 시도한 기존 GET 호출 개수(실패 시 `attempted_public_gets`). `operating_database_writes=0`, `experience_ledger_writes=0`, `auto_promoted=false`.

## 소유자 PC에서의 사용

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
$py = 'D:\UCIE\.venv\Scripts\python.exe'

# 1. 네트워크 없이 선택된 전체 출처/페이지 계획만 보기
& $py -B -m ucie_miner.public_capability_survey --all-approved --pages 3

# 2. 실제 기존 공개 PR 메타데이터 조사를 5개 승인 출처에만 1페이지씩 실행
& $py -B -m ucie_miner.public_capability_survey --all-approved --live

# 3. 실제 전체 승인 범위 5 x 3페이지(최대 15 공개 API GET), 저장 없음
& $py -B -m ucie_miner.public_capability_survey --all-approved --live --pages 3 --limit 10

# 4. 긍정 제목 단서가 발견되면 UCIE 자체 평가 레시피 1건만 추가 실행
& $py -B -m ucie_miner.public_capability_survey --all-approved --live --pages 3 --try-first-party
```

특정 저장소만 선택하려면 `--all-approved` 대신 `--source-id repo:modelcontextprotocol/python-sdk`와 같이 지정. `--source-id`는 복수 지정 가능하며 5개 이외는 차단한다.

## 개발 성격과 다음 단계

이는 **소유자 제공 60건 공개 샘플의 후보 0**이라는 관측을 실행 가능한 발굴 품질 진단으로 연결하는 기능이다. 실제 업스트림 기술 구현을 시험하거나 새 기술을 승인하는 것이 아니다. 현재 5개 승인 저장소 범위에서 소스 적합도를 먼저 확인한 다음, 제목 패턴이 지속적으로 0일 경우 정확 PR 근거가 있는 자료만 선택적으로 자세히 검증한다.

다음 실제 개발은 출력에서 얻은 **근거 있는 공개 기술 후보를 W05 원래 검증기로 재확인하고**, UCIE 자체 실험 결과·실패·지속 가능성·라이선스 상태를 분리해 P8 경험 정책과 W09 패키지 계약에 연결하는 것이다. 기존 P8 두 건, W05 경험 원장, 자동 수집기/스케줄러·서명 Rulepack은 수정하지 않음.

시험 파일 `tests/test_ucie_public_capability_survey.py`는 실제 원래 승인 URL 5×2 호출 경계, 후보 0과 양성 제목 단서 병존, 중복 충돌, 제목 비반출, 무단 GET·과다 페이지 거부 및 최초 UCIE 자체 실기 허용을 확인한다.
