# UCIE W04 / P8 — 검색 알고리즘 비용 기반 자동 선택 (2026-10-27)

## 실제 소유자 PC에서 관측된 입력

기존 선택적 정확 검색 기능에 대해 사용자 제공 출력:

| 항목 | 실측 |
|---|---:|
| 기존 UCIE 공개 근거 원장 연결 항목 | 341 |
| source/domain/kind/purpose 조합 | 26 |
| 정확 일치 질의 | 2개 (Python API_CONTRACT, CONCURRENCY) |
| 조회 가능한 전체 일치 개수 | 8건 + 12건 |
| 선형 완전 탐색 추정 비교 | 341×2 = 682 |
| 인덱스 생성+정확 조회 추정 작업 | 341+2 = 343 |
| 추정 작업량 차이 | 339회 감소, 약 49.71% |
| 네트워크 요청 / 운영 DB 쓰기 / 승인된 스킬 | 0 / 0 / 0 |

두 출력은 미검증 공개 **기술 근거**이며 20개가 실사용 스킬로 검증됐다는 의미가 아니다. 사용자 출력에 실행시간 측정은 없으므로 실행속도 증가·지연 감소를 주장하지 않는다.

## 이번 실제 기능 변경

`src/ucie_miner/library_exact_index.py`의 선택적 정확 검색에, **P8 비용 모델 기반의 자동 실행 전략**을 도입한다.

- 검증된 연결 원장 항목 수 `N`, 정확 일치 질의 수 `Q`를 확인.
- 모델상 선형 탐색 비교 = `N × Q`.
- 모델상 인덱스 구축+조회 = `N + Q`.
- **`N + Q < N × Q`일 때만** 호출 단위로 메모리 인덱스를 한번 구축한다. 동일 비용이면 추가 구조가 없는 선형 전체 검색을 선택한다.
- 두 방식은 **동일한** 기존 UCIE Stage10→12/15 출처 연결 검증과 W02 `LibraryEntry` 정규화를 거친다. 공개 증거 `library_item_id`, 원본 해시·리비전·반출 금지 플래그를 똑같이 반환한다. 결과 정렬과 결과당 최대 `limit` 보존.
- `selected_strategy`, `index_built`, `strategy_reason`, `executed_strategy_estimated_operations`, `alternative_strategy_estimated_operations`, `cost_metric` 필드를 기존 출력에 추가.
- 기존 `index_build_plus_lookup_operations`과 `linear_scan_comparisons_for_same_queries`은 **항상 두 전략의 비교 모델**이다. `selected_strategy`가 `LINEAR_EXACT_SCAN`일 때 `index_build_plus_lookup_operations`은 실제 실행된 작업이 아닌 계산상 대안이다. 실제 실행 선택값은 `executed_strategy_estimated_operations`.
- 인덱스 생성 / 선형 선택을 한 번의 읽기 전용 요청마다 결정한다. 운영 저장소에 인덱스를 영구 반영하거나 스케줄러·원래 수집기·서명 Rulepack을 수정하지 않음.
- W04 일반 부분 문자열 `--query`와 `--group-revisions` 경로는 **변경하지 않는다**.

## 작업량과 시간은 다르다

인덱스 생성과 Python 객체 정규화·정렬·메모리 배치·해시 함수의 실제 비용은 단일한 비교/조회 횟수만으로 완벽히 설명되지 않는다. 특히 `Q=1`일 때 `N+1`은 `N`보다 크므로 선형 조회를 선택한다. `Q=2, N=2`는 동일 예상 작업량이므로 선형, `Q=3, N=2`는 인덱스를 선택한다. 실제 성능이 빠르다는 추가 보장은 없고, 데이터 크기·조회 패턴별 P8 반복 측정이 필요하다.

### 로컬에서 실제 사용

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
$py = 'D:\UCIE\.venv\Scripts\python.exe'

# 실제 사용자 PC의 341건 원장에서 두 목적코드 조회:
# 비용 모델에 따라 인덱스가 선택될 것으로 예상(실행 확인은 별도)
& $py -B -m ucie_miner.library_search --source-id repo:python/cpython --domain Python --kind PUBLIC_TECHNICAL_EVIDENCE --exact-purpose API_CONTRACT --exact-purpose CONCURRENCY --limit 5

# 동일 목록에서 단일 목적코드: 선형 탐색을 선택
& $py -B -m ucie_miner.library_search --source-id repo:python/cpython --domain Python --kind PUBLIC_TECHNICAL_EVIDENCE --exact-purpose API_CONTRACT --limit 5

# 이전 일반 검색 경로 그대로
& $py -B -m ucie_miner.library_search --domain Python --group-revisions --limit 5
```

## 검증 및 다음 지식 진화 단계

`tests/test_ucie_w04_exact_index.py`에 한 건 조회·비용 동률·묶음 조회의 자동 전략 선택, 두 알고리즘에서 동일한 원본 응답, 0건 조회, 미확인 소스 차단과 기존 원장 불변 기능시험 추가. GitHub Windows/Ubuntu Py3.13/3.15 정확 SHA 통과 여부와 소유자 호스트 실행 결과를 구분한다.

다음 개발은 **W05 엔진·스킬·학습 로직별 P8 실기 계약**이다. 현재 비용 모델은 W04의 특정 정확 일치 인덱스 질의만 판정하며, 긍정적 외부 스킬이 실제로 개선됐다는 주장이나 운영 코드 자동 승격을 하지 않는다. 이미 두 번 기록한 P8 합성 경험 `256×16`, `4096×16`은 보존하고 다음 미실행 조건 `1536×96`을 그대로 유지한다.
