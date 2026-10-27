# UCIE W05 Library Shelf + W06 Official Metadata Shelf (2026-10-27)

**근거:** 사용자 실제 W04 Windows 결과: `source_linked_count=338`, Python 분야의 `raw_evidence_revision_matches=262`, 개정판 그룹화 `total_matches=261`; 네트워크/DB 쓰기 0. W05 기본 명령 `W05_LIVE_DISCOVERY_NOT_AUTHORIZED`, 후보 0, GET 0은 올바른 보수적 동작.

## 이번 기능

1. `src/ucie_miner/library_shelves.py`의 **W05 긍정적 개발 능력 후보 서가**:
   - 기존 공개 PR 제목의 기술 개선 단서를 W05 `classify_public_capability_metadata`로 재검사하고, 승인된 소스·병합 SHA·근거 해시를 갖춘 `DEVELOPMENT_ENGINE`, `REUSABLE_SKILL`, `LEARNING_LOGIC` *미검증 후보*를 검색/종류별 필터링.
   - 후보의 실작동·성능·라이선스·승인·반출 모두 확인하지 않았다는 상태를 유지. 역사 자료(365일 초과)는 HISTORY로 구분.
   - 기본 명령은 **GET 0회**, 명시적 `--live`만 기존 승인 GitHub PR API 한 페이지 **1회** 호출. 새 외부 공급원, 자동 스케줄러, DB 생성/쓰기 없음.

2. **W06 공식 근거 서가**:
   - 별도 신규 크롤러를 만들지 않고 기존 `public_official_evidence.py` Stage14 공개 메타데이터 SQLite의 `application_id/user_version/schema/quick_check`를 검증 후 `mode=ro`로 `document`, `release`, `advisory` 해시·날짜·출처를 조회.
   - 공식 문서의 고정 URL만 사용. 기존 Stage14가 보관하지 않는 릴리스 태그/정확 릴리스 URL을 역추측하지 않고 **릴리스 목록 URL**로 안내. 문서·릴리스·권고 원문, 실행 코드, 외부 프로젝트 자료는 조회하지 않음.
   - 부재한 Stage14 원장은 `ABSENT_NO_GO`이며 생성하지 않음. 증거 품질은 **PUBLIC_METADATA_UNVERIFIED**, 서명·배포 불가.

3. 기존 W04의 **의미 분류 정정**:
   - 범용 오류 검토 후보를 근거도 없이 `REUSABLE_SKILL`로 표시하던 문제를 정정.
   - Stage6 정확 규칙 템플릿이 있는 행만 `PREVENTION_RULE`, 나머지는 **`PUBLIC_TECHNICAL_EVIDENCE`**로 구분. W02에 새 근거 유형만 추가하며 승인 가능한 스킬로 자동 승격하지 않는다.
   - 기존 후보 원장과 SHA는 변경하지 않고 검색 시 표현만 정확히 교정.

## 소유자 PC 읽기 전용 실행 예시

```powershell
$env:PYTHONPATH='D:\UCIE\src'
$py='D:\UCIE\.venv\Scripts\python.exe'

# 실 저장된 공식 근거 원장 조회: GET 0, DB 수정 0
& $py -B -m ucie_miner.library_shelves --shelf official --limit 5
& $py -B -m ucie_miner.library_shelves --shelf official --kind document --limit 5

# 긍정 기술 후보 서가 기본 조회: GET 0
& $py -B -m ucie_miner.library_shelves --shelf positive --source-id repo:python/cpython

# 오직 소유자가 원할 때, 기존 승인 GitHub PR 목록 1회 GET
& $py -B -m ucie_miner.library_shelves --shelf positive --source-id repo:python/cpython --live

# 수정된 기존 검토 증거(미검증 기술 근거) 검색
& $py -B -m ucie_miner.library_search --domain Python --group-revisions --limit 5
```

## 인수 및 한계

- `tests/test_ucie_library_w05_w06_shelves.py`: 개발 엔진/스킬/학습 로직 세 종류 서가, 후보 불승인, 명시적 요청 전 GET 차단, 기존 고정 소스 경로 단 1회, Stage14 합성 원장 실제 조회·바이트 보존, 오류 메타데이터 스킬 오분류 교정, 미승인 자료/부정확한 row 차단.
- W05의 현재 긍정 신호는 **제목 기반 정형 단서**이며 유용성·구체 구현·성능을 입증하지 않는다. W06는 저장된 근거 해시를 검색할 뿐 새 외부 데이터를 자동 수집하지 않는다.
- P3 통합 영구 인덱스, W07 승인 Rulepack 서가, W08 독립적인 UCIE 자체 스킬 평가와 W09 재사용 패키지는 미완성.
- W01~W04와 운영 공개 수집기/시간당 스케줄러, Serial4·5를 변경하거나 재시작하지 않는다.

## 바로 다음 실제 개발 작업

**W08 — 유용한 스킬/엔진의 효용 실험:** UCIE가 직접 작성한 안전한 합성 시나리오 하나에 대해 기존 방식과 개선 방식을 동등 입력에서 비교하고 정확성·실행 시간·자원 측정값·실패 사례를 기록. W05 후보의 PR 제목만으로 효과를 인정하지 않음. W07 승인된 Rulepack도 신뢰된 별도 서가로 연결, 이후 W09 범용 패키지 선택/내보내기 개발. 동일 기능 중복 개발 금지.
