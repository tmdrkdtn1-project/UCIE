# UCIE 1단계 개발 인수 — 두 승인 근거의 교차 기술 원리 생산 초안 (2026-11-05)

- PROJECT: UCIE ONLY / WORKROOM: UCIE통합개발방
- 출시 로드맵 정본: [UCIE_V1_RELEASE_EXECUTION_LOCK_20261105.md](UCIE_V1_RELEASE_EXECUTION_LOCK_20261105.md)
- 상태: **PHASE_01_PARTIAL / CURATED_FIRST_PARTY_CROSS_SOURCE_CHAPTER_DRAFT / RELEASE_NO_GO**
- 목적: 이미 승인된 공식 공개 Python·Git 문서 및 UCIE가 직접 작성한 두 SkillBook의 근거를 **안전한 하나의 비교 원리와 검증 가능한 기술 자산**으로 재분류·재가공. 새로운 네트워크 수집, 임의 공개 텍스트 요약, 모델 학습, 타 프로젝트 경험 재사용은 없음.

## 승인 공개 근거 → 직접 작성 원리 → 실제 자산 흐름

1. Python 공식 자료: `doc:python/cpython`, `v3.15.0`, 고정 원문 SHA-256 `9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a`; 기존 Python SkillBook 001(`os.scandir` 수명과 최대 128개 관측).
2. Git 공식 자료: `doc:git/git`, `v2.51.0`, 고정 원문 SHA-256 `1cdd1c7339dfc64093687b6e072d59feee584b8639c0203ece0a1150ce23d325`; 기존 Git SkillBook 002(`status --porcelain=v1 -z` 형식, 8192바이트/64 레코드).
3. `src/ucie_miner/skillbook_principle_composer_v01.py`: 기존 두 SkillBook 객체·승인 출처 레지스트리에서 생성한 W02 `LibraryEntry`의 정확한 ID/태그/문서 SHA/실제 callable/승인 미완 상태를 비교 검증한다. **임의의 새 서적이나 사용자 제공 본문을 수용하지 않는다**. 입력 순서는 결과에 영향을 미치지 않으며, 출처/내용/허위 승인 변조는 실패한다.
4. 결과: `UCIE-PRINCIPLE-PYTHON-GIT-BOUNDED-METADATA-001` — 두 기술에 공통으로 적용되는 **명시적 입력 권한**, **예산·중단 조건**, **출력 정보 최소화**, **반례**, **버전·독립 시험 한계**를 다룬 **새로운 UCIE 자체 작성 교차 기술 원리 5개 챕터**. 각 챕터는 `UCIE_AUTHORED_...` 저작·추론 구분을 갖고, 공식 문서의 직접 진술과 혼동하지 않는다.
5. 중요한 실제 차이: Python 레시피는 정렬한 **파일명**을 호출자에게 반환하지만 Git 레시피는 검증한 경로를 버리고 **변경사항 개수만** 반환한다. 본 원리를 '둘 다 이름을 노출하지 않는다'고 잘못 일반화하지 않는다.
6. `src/ucie_miner/skillbook_two_recipe_disposable_v01.py`는 4개 원본 저작 모듈+신규 composer 원본을 **고정 Git blob SHA**와 비교해 원본이 다르면 중단. Windows Git CRLF만 LF로 정규화하며 단독 CR/코드 변경은 거부한다.

## 실물 기술서적/기계 자산

UCIE 전용 인메모리 8멤버 `DRAFT_NOT_RELEASED` ZIP:
- `__main__.py`: 두 기존 레시피 + 새 비교 합성 시나리오의 일회용 소비 인터페이스
- `skillbook_scandir_recipe_v01.py`, `skillbook_git_porcelain_recipe_v01.py`: 원본 그대로 정합성을 검증한 UCIE 자체 코드
- `SKILLBOOKS.md`, `SKILLBOOKS.json`: 기존 두 서적 각각 실제 4개 챕터, 출처/실행 계약/개정/미승인 상태
- **`PRINCIPLE.md`, `PRINCIPLE.json`: 새 교차 원리 5개 챕터, 두 원본 근거·버전·출력 공개 차이, 설명의 자체 추론 상태, 개정 본문 SHA, 승인지연 상태**
- `MANIFEST.json`: 8개 이름 및 비매니페스트 7개 SHA-256, 원리 본문 SHA, composer Git blob, 두 기술 원본 소스/서적 authorship blob, 승인 미완 표시.

## 실제 안전 실행 및 사전 검증

- `verify_draft_bundle_before_execution(raw, expected_sha256)`: **신뢰할 수 있는 별도 발급 원본 해시**로 전체 ZIP 바이트 일치/한도/정확 8멤버/각 SHA/출처·권리 상태를 먼저 확인. `__main__.py`는 Python이 먼저 실행하므로 **ZIP 내부의 자가검증만으로 악성 실행 파일을 막을 수 없다**. 독립 소비자는 검증된 UCIE 확인자에서 출처가 별도로 신뢰되는 SHA를 사용해야 한다. 이 검증은 서명이나 외부 실행 허가가 아니다.
- `{"action":"principle-synthetic"}`: 임시 자체 생성 폴더 두 파일과 별도로 작성한 Git `-z` 가상 바이트로 기존 두 레시피를 **실제 호출**, 파일명은 결과로 보내지 않고 처리량/분류별 개수만 내보낸다. 외부 디렉터리 또는 저장소 경로 매개변수 없음.
- `{"action":"scandir-synthetic"}`과 `{"action":"git-summary","payload_hex":"..."}` 기존 명시 호출은 유지하되 사용자 승인 없는 외부 프로젝트 접근은 없음.
- 필드·동작·바이트·ZIP 본문 변조·가짜 승인 플래그 거부, 임의 CLI 실행 인자 거부. 공식 공개 소스 코드 자체는 실행하지 않고 외부 저장소 스캔·운영 원장·배포·서명·모델 훈련은 수행하지 않는다.

## 실제 시험/인수 상태

2026-11-05 소유자 Windows `D:\UCIE`, UCIE 승인 단일 파일 시험:
- 새 `test_ucie_skillbook_principle_composer_v01.py`: **10/10 PASS** (근거 정확성, 원본 비교·정규화, 출력 노출 차이, 모방 승인 거부, 합성 두 레시피 실행).
- 확장 `test_ucie_skillbook_two_recipe_disposable_v01.py`: **19/19 PASS** (원문 출처/챕터/본체 고정, 실제 독립 프로세스 실행, 교차 합성 실행, 변조·초과 거부, Windows CRLF, 사전 ZIP 검증).
- 이전 기능의 소유자 Windows 단일 파일 6종: 기존 제품 16, 통합 도서관 17, Git002 20, SkillBook UI 6, W09 게이트 10, disposable 실제 Git 4 = **73/73 PASS**.
- 합계: **102/102 대상 자체 회귀 PASS**. 기존 블루프린트·제품 로드맵 두 테스트 파일은 소유자 UCIE 단일 시험 도구에서 호출 오류로 **이번 실행은 미검증**; 위 수에 포함하지 않는다.
- **GitHub Actions 정확 HEAD** Windows/Ubuntu × Python3.13/3.15은 해당 마지막 커밋의 실제 결과를 별도 확인해야 한다. 미확인이면 CI PASS라고 하지 않는다.

## 남은 필수 게이트

1단계에서 아직 **안 되는 일**: 임의의 승인 공개 근거에 대한 새로운 자체 원리·챕터 자동 추론, 독립 검증된 실제 기술 효용/고객 업무 성능, 외부 권리·보안/소유자 승인/서명·배포. 지금의 생산기는 승인된 기존 두 저작물을 고정 정책에 따라 **새 원리로 수작업 설계·결정적으로 재구성**한 구현이다. **범용 자동 SkillBook 생성 엔진, 외부 독립 QA, 출시 완료라고 주장하지 않는다.**

2~5단계 제품 통합·승인형 패키징·실제 동등 조건 성능 비교·개정 폐회로는 부분/미완, 6단계 V1 실제 출시 인수는 **NO_GO**다. 소유자 `D:\UCIE`의 15개 기존 Git tracked 수정, 운영 공개 마이너 DB·TaskScheduler/C40, 기존 승인 규칙, 타 프로젝트에는 변경 없음. PR은 **Draft**로 유지하고 리뷰/정확 CI가 없는 병합 금지.
