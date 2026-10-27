# UCIE W04 — P8 실측을 실검색 기능으로 연결: 선택적 정확 일치 인덱스 (2026-10-27)

## 1. 사용자 실호스트 결과 및 개발 결정

**기존 P8 실기:**
- 사용자 PC의 기록된 UCIE 경험 1번: 256×16, SHA `6e6c54d7f0ebe0763528b02ae093bdac2fb24c81aec9921d37d9b11aa370a466`.
- 경험 2번: 4096×16, SHA `35ddd7d51a67720c4ae6aaa169bc0be439115e3452dbe861f43df08d34634d0b`, 정확 일치, 연산 65,536 → 4,112, 시간 중앙값 6,859,500ns → 541,800ns.
- 다음 미실행 합성 부하 1536×96. 기록된 두 개를 다시 반복하거나 이전 원장을 재생성하지 않음.

**실제 UCIE 공개 검토 메타데이터 W04 성능 실기:**
- Stage10→12/15 연결 검증 공개 후보 338건.
- 4중 정확 필터(source_id/domain/kind/purpose) 조회 32회(매치 27, 미매치 5), 정답 불일치 0건.
- 선형 전체 탐색 10,816 비교 / 인덱스 생성+조회 370 작업.
- 호스트 중앙값 1,148,900ns → 110,100ns; 그 실험의 성능 관측일 뿐 다른 환경·다른 질의 보장 불가.
- 자료 SHA256 `f0392e7dfa1d9d68e647a616705de5b039aaa30e96010b9e211647c6253fdd29`.
- 운영 인덱스 교체, 공식 패키지 승인, 외부 스킬 성능 인증을 뜻하지 않음.

### 결정
*실제 도서관에 인덱스를 영구 설치*하지 않고, 유효한 공개 근거의 4중 키로 **한 번의 요청에서 여러 목적코드를 조회할 때만** 메모리 인덱스를 만들 수 있게 선택 옵션을 추가한다. 기본 부분 문자열 검색의 의미·호출·출력은 그대로 보존한다.

## 2. 개발 내용

- 신규: `src/ucie_miner/library_exact_index.py`
  - `exact_search_linked_public_candidates(handoff, queries=(...), limit=10)`
  - `search_exact_existing_public_library(root, queries=(...), limit=10)`
  - 승인된 5개 repo ID/도메인/kind/정형 purpose만 받음. 미승인 데이터 공급원·공식 문서 ID를 Github PR 조회로 위장할 수 없음.
  - 기존 W04 `prepare_verification_handoff`, Stage12 원장 링크·비승인 검증(`_checked_handoff`)과 W02 `build_library_entry`의 근거 SHA·출처·유형 재사용.
  - 인덱스 키 `(source_id, domain, kind, purpose_code)`. 질의당 최대 20개, 한 번에 최대 32개. 조회 중에만 메모리 인덱스를 생성·폐기.
  - 결과는 `library_item_id`, 공개 PR 링크, 원본 증거 SHA, 병합 SHA, `UNVERIFIED_CANDIDATE_ONLY` / `export_allowed=false` 포함.
  - 한 개 질의만 있을 때 구축 작업 때문에 선형보다 비쌀 수 있음. 작업량을 늘렸더라도 무조건 개선됐다고 보고하지 않음.
  - 원장·스케줄러·운영 코드·기존 미검증/서명 경계 변경 없음.

- 수정: `src/ucie_miner/library_search.py` 기존 CLI에 `--exact-purpose` 반복 옵션만 선택적으로 추가. `--query`, `--group-revisions` 등 기본 경로는 수정하지 않고, 두 검색 모드를 동시에 섞으면 명시적으로 실패 처리.

## 3. 소유자 PC에서 읽기전용 실사용

```powershell
$env:PYTHONPATH='D:\UCIE\src'
$py='D:\UCIE\.venv\Scripts\python.exe'

# 지금까지의 일반 W04 검색: 전혀 바뀌지 않음
& $py -B -m ucie_miner.library_search --domain Python --group-revisions --limit 5

# 새 선택적 정확 검색: 인덱스 하나를 생성해 두 목적코드를 일괄 조회
& $py -B -m ucie_miner.library_search --source-id repo:python/cpython --domain Python --kind PUBLIC_TECHNICAL_EVIDENCE --exact-purpose API_CONTRACT --exact-purpose CONCURRENCY --limit 5

# 필요하면 미확인 키 테스트: 결과 0이 정상일 수 있음
& $py -B -m ucie_miner.library_search --source-id repo:python/cpython --domain Python --kind PUBLIC_TECHNICAL_EVIDENCE --exact-purpose NO_MATCHING_PURPOSE --limit 5
```

## 4. 한계와 다음 개발

- 실제 338개 메타데이터에 대한 4중 키 필터에만 적용. **W04 전체 부분 문자열 검색은 성능 시험·최적화 대상이 아님.**
- 이 작업은 P8 실기 결과를 실제 검색 기능에 연결한 첫 실용화이며, 영속 색인/서버 캐시/자동 인덱스 정책/실제 배포 기능은 미구현.
- 원본 `D:\UCIE\runtime\ucie_p8_experience_v1.jsonl`의 두 기록을 수정하거나 외부에서 가져온 데이터의 학습에 활용하지 않는다. 이전 경험과 향후 평가 자료의 출처를 항상 분리한다.
- 다음에는 실제 **반복 질의 빈도와 인덱스 구축 비용**을 비교해 인덱스를 언제 쓰는 것이 합리적인지 자동 정책을 수립하고, W05 유용한 엔진/스킬 후보별 효용 실험 계약으로 확장한다. UCIE 격리 원장 이외의 사용자의 프로젝트 작업내역은 수집하지 않는다.
