# UCIE W05 → P8: 개발 엔진·스킬·학습 로직의 검증 가능한 경험 연결 (2026-10-27)

## 무엇을 실제로 개발했는가

기존 사용자 실호스트 W04 자동 검색 정책 최종 관측: 공개 후보 341건에 단일 API_CONTRACT 조회는 `LINEAR_EXACT_SCAN` 341 예상 작업(인덱스 대안 342), 이중 API_CONTRACT + CONCURRENCY 조회는 `BUILD_ONCE_COMPOSITE_INDEX` 343 예상 작업(선형 대안 682). 예상 작업량의 선택 정책이 실제 동작했고, 운영 원장·기존 P8 2건 변경 없음. **이 수치는 실제 수행 시간 벤치마크가 아니다.** P8의 기존 엔진/인덱스 실험은 완료해 중복 개발하지 않는다.

새 P8 실험 대상을 검색 외 **개발·유지보수 기술 3종**으로 확장한다.

| W05 힌트 분류 | UCIE 자체 작성 비교 알고리즘 | 관측 가능한 정확도 |
|---|---|---|
| `DEVELOPMENT_ENGINE` / `ENGINE_INCREMENTAL_BUILD` | 합성 의존성 체인 전체 재계산 vs 변경 뒤 구간만 재계산 | 최종 전체 해시 목록 완전 일치 |
| `REUSABLE_SKILL` / `SKILL_TEST_AUTOMATION` | 테스트 태그별 전체 선형 탐색 vs 한 번 만든 태그 인덱스 | 선택된 테스트 ID 목록 완전 일치 |
| `LEARNING_LOGIC` / `LEARNING_FEEDBACK_LOOP` | 합성 피드백 합계 전체 재계산 vs 증분 합산 | 각 피드백 카테고리 합계 일치 |

`ENGINE_WORKFLOW_ORCHESTRATION`과 `SKILL_RELEASE_AUTOMATION`은 **시험 미구현**으로 표시. 다섯 가지 업스트림 목적코드 전체 구현으로 주장하지 않는다.

## 코드

- `src/ucie_miner/capability_trials.py`의 `evaluate_ucie_owned_recipe`는 두 **UCIE 작성 알고리즘을 실제로 실행**, 일치 여부·처리 작업량(초기 구축비용 포함)·반복 시간 중앙값과 개선 가설을 산출. 기존 W05 `classify_public_capability_metadata`를 그대로 호출하는 `verified_w05_cues`는 정확히 승인된 공개 저장소 PR ID, 병합 SHA, PR 제목 근거에 한정하여 버전 고정 후보를 반환.
- `evaluate_approved_w05_feed`는 PR 제목 기반 후보와 **실제 실행한 UCIE 자체 surrogate 실기**를 연결하지만, 공개 PR 코드·엔진·스킬 자체를 가져오거나 실행하지 않음. 외부 PR의 가치/성능/라이선스/검증 상태는 항상 미확인.
- `src/ucie_miner/capability_experience.py`: 특정 W05 후보의 `library_item_id` 및 근거 SHA에 기반한 **P8 기술별 경험 계보**를 유지. 세 가지 고정 UCIE 합성 부하(128×24, 256×16, 512×64)를 한 번씩 선택하고, 동일 후보·동일 부하를 다시 기록하지 않는다. 정답 불일치·연산상 개선 실패는 다음 평가를 HOLD 처리한다.
- 새로운 독립 파일 `D:\UCIE\runtime\ucie_p8_w05_capability_experience_v1.jsonl`은 `--record`가 명시될 때만 생성, 이벤트 순서·이전 SHA256·현재 SHA256으로 무결성 계보를 검증. 기존 `ucie_p8_experience_v1.jsonl` 및 public miner 운영 SQLite를 읽거나 덮어쓰지 않는다. 해시 체인은 변조 감지용이며 외부 인증·서명은 아님.
- 기록은 `candidate_id`, 공개 PR 출처 URL·근거 해시, `purpose_code`, `recipe_id`, 합성 워크로드 해시, 결과/작업량·시간·실패 결정 등 허용된 최소 기술 메타데이터만 포함. 외부 원문 코드·PR 제목·패치·다른 프로젝트 자료를 넣지 않는다.

## 사용 예시

```powershell
$env:PYTHONPATH='D:\UCIE\src'
$py='D:\UCIE\.venv\Scripts\python.exe'

# 순수 UCIE 합성 레시피 3종을 1회 실행하고 JSON 출력, GET/DB 기록 없음
& $py -B -m ucie_miner.capability_trials --demo

# P8 기술별 저장 기록 조회만 수행, GET/DB 기록 없음
& $py -B -m ucie_miner.capability_experience --ucie-root 'D:\UCIE' --history

# 승인된 기존 GitHub 공개 PR API를 딱 1회 조회해 W05 후보를 실제 분류하고
# 기술별 자체 합성 실험 1건 수행(기본값은 기록하지 않음)
& $py -B -m ucie_miner.capability_experience --ucie-root 'D:\UCIE' --source-id repo:python/cpython --live

# 소유자가 새 W05 기술 경험을 영속 기록하기로 한 경우에만
& $py -B -m ucie_miner.capability_experience --ucie-root 'D:\UCIE' --source-id repo:python/cpython --live --record
```

`--live`는 소유자가 명시적으로 요청한 경우 기존 승인된 공개 PR 목록 경로를 정확히 한 번 호출. `--record`는 동시에 `--live --source-id`가 명시된 경우에만 허용. 긍정 기술 제목 단서가 없으면 `NO_UNTESTED_IMPLEMENTED_W05_RECIPE`이고 원장 기록 없음. 과거 P8 기록 2건을 새로운 기술별 서가로 옮겨 쓴 척하지 않는다.

## 허용/금지와 완료 경계

기존 승인 공개 5개 저장소·공식 자료 범위 고정. 외부 공급원, GitHub PR 원문 대량 수집/재배포, 비공개 저장소, 다른 프로젝트, 서명 개인키, 원래 시스템 작업 기록은 접근하지 않는다. 자동 규칙 승격, 라이선스 승인, 모델 학습, 스케줄러 등록, 운영 인덱스 교체 또는 패키지 배포 없음. 신규 두 모듈과 오프라인 집중 시험 외의 기존 소스 변경 불필요.

이 기능은 **UCIE 자체 설계 알고리즘 세 종류의 합성 실험 결과와 W05 공개 근거 후보를 구분하면서 연결하는 초기 기술별 경험 시스템**이다. 공개 엔진·스킬·학습 로직 자체의 실제 개선과 출고 가능한 범용 패키지, P9 통합 V1은 여전히 미완이다.
