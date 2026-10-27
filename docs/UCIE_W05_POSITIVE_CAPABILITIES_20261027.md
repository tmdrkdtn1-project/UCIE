# UCIE W05 — 유용한 개발 엔진·스킬·학습 로직 발굴 (2026-10-27)

## 목표와 수집 범위

코딩 오류 수정 전용 수집의 다음 단계. **승인된 공개 저장소 5곳의 기존 GitHub PR 메타데이터 경로**에서 오류 수정이 아닌 개발 생산성·유지보수·학습 방법의 *후보*를 찾는다. 새 저장소, 외부 비공개 프로젝트, 별도 API, 스케줄러는 열지 않는다.

- `src/ucie_miner/positive_capability_discovery.py`: W05.
- `src/ucie_miner/library_search.py`: W04 검색 품질 개선. 넓은 문자열 검색의 `python-sdk`와 실제 Python 언어 분야를 구분하고 같은 PR의 근거 개정 기록을 한 번에 묶어 조회.

## W05 자동 발굴은 무엇을 할 수 있는가?

1. `repo:python/cpython`처럼 기존 W01의 *정확한 승인 소스 ID* 확인.
2. 기존 승인 `public_feed_url`을 한 페이지(최대 20 PR)만 조회. **명시적 `--live` 옵션이 없는 기본 명령은 네트워크를 호출하지 않는다.**
3. 공개 PR 제목의 한정된 긍정 기술 신호만 분류. 학습/피드백 루프, 점진 빌드 캐시, 워크플로 오케스트레이션, 테스트 자동화, 릴리스 자동화 등의 정형적 단서. `fix/bug/regression/error` 등의 오류 수정 제목은 W05 긍정 발굴에서 제외하고 기존 오류 예방 트랙에 남긴다.
4. 제목·본문·코드·패치 원문을 보관하거나 재배포하지 않고 PR 번호·병합 SHA·병합일·제목 SHA256·도서관 후보 ID·기술 유형만 반환.
5. `DEVELOPMENT_ENGINE`, `REUSABLE_SKILL`, `LEARNING_LOGIC`의 **미검증 후보**를 기존 W02 `build_library_entry`로 통합. 실제 성능/효과·코드 동작은 **미검증**. 모호한 다중 분류, 병합 SHA 부재, 미승인 소스는 추측하지 않는다.
6. 365일 이내 병합 자료와 역사 자료를 구분. 역사 자료는 삭제하지 않고 후보 여부와 별개로 우선순위를 구분한다.

### 명령

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
$py = 'D:\UCIE\.venv\Scripts\python.exe'

# 0 GET, 원본으로부터 생성 가능한 기술 후보 종류만 표시
& $py -B -m ucie_miner.positive_capability_discovery --source-id repo:python/cpython

# 소유자가 필요시 명시적으로 선택: 기존 승인 공개 GitHub GET 정확히 1회
& $py -B -m ucie_miner.positive_capability_discovery --source-id repo:python/cpython --live
```

위 `--live`는 기존 공개 GET 경로 하나만 사용. 결과에 후보가 0건일 수도 있으며 이는 정상임. 자동 예약 실행, DB 쓰기, 스킬 자동 등록·승인·반출을 수행하지 않는다.

## W04 도서관 검색 정확도

기존 `--query python`은 공개 저장소 이름 `modelcontextprotocol/python-sdk`도 검색하기 때문에 276건을 Python 언어 기술 후보 개수로 읽으면 안 된다.

```powershell
& $py -B -m ucie_miner.library_search --domain Python --limit 5
& $py -B -m ucie_miner.library_search --query python --domain Python --group-revisions --limit 5
& $py -B -m ucie_miner.library_search --domain 'MCP/API' --group-revisions --limit 5
```

`--domain`은 기존 `skill_profiles.PROFILE`의 기술 도메인과 **정확히 일치**시킨다. `--group-revisions`는 같은 공개 PR/병합 SHA/목적/종류의 서로 다른 근거 개정 기록을 조회 시 그룹화하며, 개별 원본 해시와 후보 ID는 배열로 유지한다. 원본 원장은 수정하지 않고, 중복 개정판을 새로운 독립 스킬로 계산하지 않는다.

## 정확한 기능 완료 경계

- W05는 **긍정적 기술 개선 후보 분류**의 첫 실제 모듈이다. 아직 일반적인 코드·스킬을 자동 제작하고 실행하는 엔진이 아니고 AI 모델 학습도 수행하지 않는다.
- W04는 미검증 근거 중심의 일부 서가. 전체 가상도서관 검색·승인 Rulepack·엔진/학습 로직 영구 저장/반출은 아직 미완성.
- W05 현재 기존 GitHub 메타데이터의 **PR 제목에 나타난 제한된 신호만** 판단. 실제 유용성과 라이선스는 별도 근거·승인·UCIE 자체 실험이 필요.
- 다음 개발: W05에서 생성된 후보를 승인된 공개 메타데이터와 도서관 카탈로그의 **지속 저장 없이 검색 가능한 리뷰 서가**에 연결하고, W06 공식 기술문서·릴리스 수집의 기존 승인 경로를 재사용. W08 첫 UCIE 자체 안전한 비교 시험 계획으로 진행.

## 증거

`tests/test_ucie_positive_capability_discovery.py`: 긍정 후보 세 분류·오류 수정 제외·명시적 공개 GET 콜백·미승인 소스 거부·미병합/날짜/명령 주입 입력 제외·역사 자료·같은 PR 복수 근거의 정확한 그룹 조회. 기존 합성 시험 및 GitHub CI는 **변경된 정확 SHA의 오프라인 동작**만 입증한다.
