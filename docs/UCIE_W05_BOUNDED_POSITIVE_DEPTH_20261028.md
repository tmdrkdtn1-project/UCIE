# UCIE W05/P8 — 공개 기술 후보 0건 진단 및 승인 경로 내 3페이지 심화 조사 (2026-10-28)

## 소유자 PC 실측 인수

2026-10-28 소유자가 전달한 W05 실기:

- UCIE 자체 `capability_trials --demo`: 엔진 증분 빌드, 테스트 자동 선택, 학습 피드백 증분 계산 **3종 모두 합성 실험 결과 일치, 불일치 0**. 기준선 비교량 3,072, 개선 알고리즘 작업량 236/152/152. 시간 중앙값은 각각 3,528,300→327,600ns, 128,200→18,200ns, 157,200→20,700ns. **외부 PR 코드를 실행한 실적은 아니다.**
- `capability_experience --history`: 신규 W05-P8 전용 경험 원장 항목 **0**, 읽기 전용 정상. 기존 별도 P8 W08 경험 두 건은 이 신규 원장에 복사하지 않는다.
- `capability_experience --source-id repo:python/cpython --live`: **승인된 원래 GitHub 공개 PR 목록 1회 요청 성공**, 양성 제목 단서 0, `NO_UNTESTED_IMPLEMENTED_W05_RECIPE`, 기록 0. 이는 HTTP 실패나 W05 분류기 충돌을 뜻하지 않는다.

## 진단·수집 설계

이전 `public_feed_url(source,page=1..3)`과 기존 `public_feed_get`만 재사용한다. 신규 API 경로, 무제한 페이지네이션, 웹 전체 검색, 새로운 독립 소스, 대량 원문 복제를 추가하지 않는다.

- 기본 호출 `--live`는 **기존과 똑같이 1페이지, 정확히 1회 공개 GET**.
- 소유자가 명시적으로 `--pages 2` 또는 `--pages 3`을 지정할 때만 기존 승인 경로 `page=1..N`을 순차 호출한다. 4 이상 거부, `--live` 없으면 심화 호출 금지.
- 페이지별 기존 `classify_public_capability_metadata`와 `verified_w05_cues` 검증기를 그대로 사용한다. 페이지당 최대 20개 PR 메타데이터, 3페이지 최대 60개 입력. 정규화에 실패한 페이지가 있으면 결과를 사용하지 않는다.
- 진단 `source_scan_diagnostics`: 페이지별 `source_rows_examined`, `positive_title_cues`, `nonmerged_count`, `repair_title_count`, `ambiguous_positive_cue_count`, `unpinned_positive_cue_count`, `unclassified_or_repair_count`, 중복 건수 제공. **원래 PR 제목·본문·코드는 응답이나 경험 원장에 저장하지 않는다.**
- 동일 PR이 공개 API 정렬 변동으로 페이지 사이에 중복되면 **정확히 같은 메타데이터**인 경우 1회로 합친다. 병합 SHA·제목 등 다른 충돌 메타데이터는 실패 처리한다.
- 분류된 후보가 0이면 **0을 그대로 보고** 원장 미기록. 후보가 있다면 **UCIE 자체 합성 기술 평가 1건만** 실행하고, 명시적 `--record`가 없으면 저장하지 않는다.
- 실험은 W05 PR의 코드/스킬 자체를 검증하지 않으며 원래 W05 후보도 `UPSTREAM_TITLE_CUE_ONLY_UNVERIFIED`; 라이선스 사후 승인이나 자동 배포·승격 없음.
- 요청 수 보고: `--pages 1` → `network_requests=1`, `--pages 3` → `network_requests=3` (각 성공 호출에 대해). 외부 API 장애는 별도 FAIL_CLOSED.

## 명령

```powershell
$env:PYTHONPATH='D:\UCIE\src'
$py='D:\UCIE\.venv\Scripts\python.exe'

# 변경 없음: 기본 1페이지 조사, 원장 비기록
& $py -B -m ucie_miner.capability_experience --ucie-root 'D:\UCIE' --source-id repo:python/cpython --live

# 심화 조사: 동일 승인 repo 공개 PR 페이지 1~3, 최대 3 GET, 기록 없음
& $py -B -m ucie_miner.capability_experience --ucie-root 'D:\UCIE' --source-id repo:python/cpython --live --pages 3

# 순수 조회: 신규 P8 후보 경험 서가 (0건일 수 있음)
& $py -B -m ucie_miner.capability_experience --ucie-root 'D:\UCIE' --history
```

**이번 개발은 0건의 수집 현상을 이유 없이 스킬로 승격하지 않도록 진단하고, 승인된 기존 소스에서 안전하게 더 검색하는 첫 단계**다. 세 페이지에서도 유의미한 후보가 없으면 다른 승인된 공개 저장소를 소유자가 지정해 동일 기능으로 조사하거나, 실제 공개 근거가 뒷받침되는 새 분류 가설을 별도로 리뷰한다. 임의로 패턴을 느슨하게 하여 건수만 늘리지 않는다.

## 범위·검증

시험: `tests/test_ucie_w05_bounded_depth.py`에서 첫 페이지 0건/두 번째·세 번째에서 실제 승인 형식의 3개 긍정 제목 단서, 중복 원문·충돌 거부, 미승인 소스·과다 페이지 거부, 실제 승인 URL 호출 순서 1-3 확인, 원래 P8 독립 경험 파일 불변, 실기/기록 분리 및 문서상 허위 승인 방지.

**미완**: 실제 업스트림 기술 평가·안전성/라이선스 최종 확인, 진짜 사용 가능한 범용 스킬·엔진 배포, 자동 규칙 승격/코드교체, P9 제품 전체 통합. 기존 시간당 마이너와 운영 SQLite는 변경하지 않는다.
