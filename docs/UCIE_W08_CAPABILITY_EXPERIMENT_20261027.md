# UCIE W08 — 가상도서관 첫 자체 엔진 개선 실기 (2026-10-27)

## 목표와 시작 근거

UCIE 소유자 제공 실호스트 결과:
- W06 공식 공개 기술 근거 **775건** 조회, `PUBLIC_METADATA_UNVERIFIED`, 네트워크 0, 원장 쓰기 0
- W05 긍정 기술 서가 기본 명령 `W05_LIVE_PUBLIC_FETCH_NOT_REQUESTED`, API 요청 0, 후보 0 (정상)
- W04 Python 분야 `source_linked_count=338`, 근거 개정판 262건 → 261개 검색 항목, `PUBLIC_TECHNICAL_EVIDENCE` 구분 확인

위 숫자는 승인/검증된 엔진·스킬 수가 아니다. **W08의 목표는 실제 작성한 두 가지 UCIE 자체 알고리즘을 실행하고 같은 입력에서 효용을 측정**하는 것이다.

## 실제 개발 기능

파일: `src/ucie_miner/capability_evaluator.py`

- UCIE가 직접 만드는 **합성 가상도서관 카탈로그**: 등록된 기술 분야 5개, 개발 엔진/스킬/학습 로직 세 분류, 다섯 목적 코드. 실제 공개 PR의 코드나 메타데이터도 입력으로 사용하지 않는다.
- 기존 방식: 각 조회마다 전체 항목에 대한 정확 비교(선형 순회).
- 개선 후보: 동일한 4중 키 `(source_id, domain, kind, purpose)`의 해시 인덱스를 한 번 만든 후 조회. 인덱스 구축에 소모한 작업량도 **비교 계산에 포함**.
- 같은 검색 요청에 대해 일치 항목 및 미존재 항목을 모두 검증하고, 정확한 결과 일치·서로 다른 조회 결과 수·기준선 비교횟수·개선 후보 구축+조회 작업량·측정 시간(ns)을 기록.
- 전체 수행 시간 측정에는 인덱스 구축 시간을 포함하며 1~5회 반복 측정의 중앙값을 기록. **시간이 빨라진다는 보장 없음**, 다른 실제 데이터/시스템의 성능을 입증하지 않음.
- UCIE 자체 경험 영수증 `ucie_experience_record`: 실험 ID, 합성 자료의 SHA256, 결과, 한계, 재검토 필요 여부 포함. 지금은 JSON 출력에만 포함하며 DB·모델에 자동 기록·학습·승격하지 않는다.
- 전 구간에 외부 API/실제 운영 데이터/다른 프로젝트/임의 코드 실행/서명/배포/스케줄러가 없음.

## 사용 방법

현재 branch/PR 코드가 로컬 UCIE에 반영된 다음, UCIE 전용 경로에서:

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
$py = 'D:\UCIE\.venv\Scripts\python.exe'
& $py -B -m ucie_miner.capability_evaluator
```

옵션: `--rows 1536 --queries 48 --repeats 3` (기본값). 최대 4096개 항목, 96개 조회, 5회 반복; 범위 초과 실패 종료. 한 번 실행으로 완결하며 운영 저장소를 변경하지 않는다.

예상 결과 구조(수치는 실제 실행 환경에서 계산되므로 고정값으로 PASS를 주장하지 않음):

- `status=SYNTHETIC_EQUIVALENCE_AND_OPERATION_REDUCTION_OBSERVED_NO_GO` : 정확히 일치하고 인덱스 구축 작업까지 포함해 합성 조회 작업량이 줄어든 경우
- `status=SYNTHETIC_EVALUATION_REQUIRES_REVIEW_NO_GO` : 불일치나 개선 부재
- `synthetic_item_count`, `query_count`, `reference_comparisons_per_run`, `candidate_build_plus_lookup_operations_per_run`, `operation_reduction`, `mismatched_query_count`, `baseline_median_elapsed_ns`, `candidate_median_elapsed_ns` 등 수치와 영수증 제공

## 품질 확인과 다음 실제 단계

`tests/test_ucie_w08_capability_evaluation.py`: UCIE 합성 정확도, 인덱스 이득(구축 작업 포함), 부정 조회, 결정적 데이터 SHA256, 잘못된 알고리즘 오탐 검출, 크기 제한, 실제 DB/API 차단, CLI 실행 및 비승격 상태를 검사.

**현재 범위는 W08 초기 실험 엔진**이며 W04 실제 SQLite 검색기를 새 인덱스로 교체한 것이 아니다. 실험 결과를 살핀 다음 필요할 때 W04 실제 검색 워크로드에 적용한다. 외부에서 수집한 스킬이나 특정 GitHub PR이 실제로 빠르다고 주장하지 않는다.

다음: W07의 기존 승인된 Rulepack 조회 서가(미서명 후보와 분리), W09의 범용 패키지 계약 및 승인된 내용의 독립 반출, P8 자체 실험/실패 경험의 출처 기반 개정 관리. 중요한 실질 효과 없이 새 검증 계층·새 Stage 번호만 늘리지 않는다.
