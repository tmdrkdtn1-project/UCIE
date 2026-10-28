# UCIE P9 — 기존 기능 통합 제품 진입점 및 독립 소비 기술 첫 실사용 인수 (2026-10-28)

## 개발 원칙

사용자는 P9 완성을 요구하며 W05의 공개 PR 페이지 추가 조사만 반복하는 데 문제를 지적함. 사용자 실제 조사 `--all-approved --live --pages 3`은 **5개 승인 공개 저장소 총300건에서 긍정 제목 후보0**, 공개 메타데이터 GET15, 운영 DB 쓰기0. 현재 실증된 것은 엄격한 W05 제목 패턴의 표본 0이라는 사실이지 기술/스킬의 부재가 아니다. 이 단계에서 W05 확대를 중단하고 **이미 기능이 있는 검색·자료·경험·규칙·기술 실기를 실제 제품 사용 흐름으로 연결한다.**

## 이번 코드의 실제 산출물

1. `src/ucie_miner/product_v1.py`: **하나의 read-only P9 CLI**가 W01 승인 소스 등록 10개(공개 repo5+고정 공식문서5), W04 기존 Stage10/12/15 검증 연결 근거 검색(원래 W04 search/그룹화 그대로), W06 Stage14 공식 공개 메타데이터, W08/P8 원본 합성 경험의 SHA 계보, W05/P8 별도 기술별 경험을 **한 번에 인수**한다. 필요한 경우 사용자 지정 원래 Serial4·공개 신뢰증거·Serial5 검증 패키지로 W07 서명 상태도 별도 검증할 수 있다. 없는 자료는 거짓 PASS 없이 `NOT_READY/NOT_INSPECTED`로 표시.
2. `--demo`를 선택하면 **UCIE 자체** 엔진·테스트 스킬·학습 로직 합성 알고리즘 3종을 실제 실행하여 정확도/작업량과 패키지용 가상 데이터의 단건/배치 검색 결과 동등성을 반환. 기존 P8 경험 원장에 재기록하지 않음. 외부 공개 PR/모델 가중치 실행 없음.
3. `src/ucie_miner/portable_exact.py`: **UCIE가 직접 작성한** Python 3 stdlib 전용 1.0.0 검색 알고리즘. UCIE 라이브러리 패키지 import 없이 독립 소비 환경에서 `search_public_metadata` 수행. 5개 승인 공개 repo/5개 정확 분야/미검증 근거만 받아 결과에 출처·SHA·반출금지 상태를 유지. 신원 위조·미승인 저장소·임의 승인 flag·과다 입력 차단. 단건 선형/다건 일회 인덱스 사용.
4. **실제 독립 소비 시험** `tests/test_ucie_p9_product_v1.py`: 분리된 임시 디렉터리에서 표준 라이브러리 Python `-I`로 `portable_exact.py`를 *독립적으로 실행*하고 정답/미승인 상태 확인. 기존 UCIE Stage10/12 실제 합성 SQLite 연계 fixture와 P8 경험 기록 1건을 만들어 원본 원장 바이트 불변인 통합 조회 시나리오 시험. HTTP 금지, source/approval/키 거부, 서명·공식 원장 부재 시 보류, draft zip 결정적 해시, overwrite 방지 시험.
5. **선택적 W09 초안 작성** `--export-draft`: 오직 UCIE 자체 runtime/exports 안에 `ucie_portable_exact_1_0_0_DRAFT.zip` 생성. 내용은 `portable_exact.py` + 버전/소스 SHA/의존성/승인 미완 상태를 고정한 `MANIFEST.json` + 경고 `README.txt`만. 실제 공개 원본 코드, 사용자의 다른 프로젝트 자료, 서명/개인키, 원장, GitHub API 토큰 미포함. 패키지는 SHA가 같으면 재생성하지 않고, 다른 파일이 있으면 덮어쓰기 거부. 일반 실행에서는 **출력물 파일도 쓰지 않음**.

## 사용자 PC 명령

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
$py = 'D:\UCIE\.venv\Scripts\python.exe'

# 1. 처음부터 끝까지 UCIE 공개 원장/공식 메타데이터/기존 경험을 한 진입점에서 조회
# 읽기 전용, 외부 API 요청/DB/경험 원장/파일 기록 없음
& $py -B -m ucie_miner.product_v1 --ucie-root 'D:\UCIE' --query API_CONTRACT --limit 5

# 2. 동일 통합 제품에서 UCIE 자체 합성 기술 3종·이식 가능한 모듈 기능 실기
& $py -B -m ucie_miner.product_v1 --ucie-root 'D:\UCIE' --demo

# 3. 진짜로 별도 소비용 코드를 시험할 때만 UCIE 전용 드래프트 ZIP 작성(정식 배포 아님)
& $py -B -m ucie_miner.product_v1 --ucie-root 'D:\UCIE' --export-draft
```

원래 서명팩 검증이 필요할 때 사용자 소유 파일 위치가 실제 검증된 경우에만 `--serial4-pack`, `--owner-public-trust`, 필요하면 `--serial5-pack`을 추가. **이 경로를 추측하거나 파일을 임의 열람하지 않는다.**

## 증명과 미완을 명시적으로 구분

- 이번 배치는 "P9 수집→검색→평가→독립소비 가능성 실기"의 **통합 코드/CI 증명**이다. GitHub CI와 소유자 PC 실제 실행 결과는 별개의 증거다.
- `--export-draft` ZIP은 기술의 독립 실행 예시를 갖춘 **UCIE authored unapproved DRAFT**. 사용자/법적 사용권 승인, 독립 QA, 서명·릴리스 승인, 다른 프로젝트로 실제 반출이나 배포는 없음.
- 서명 규칙 Serial4/5는 원래 검증기와 사용자 제공 정확한 경로를 필요로 하고, 기존 소유자 위험 인수는 독립 QA·라이선스 승인이 아니다.
- W05 외부 "양성 기술" 후보는 300건 중 제목 단서0, **실제 업스트림 엔진·스킬 구현/성능 검증 없음**. 이 0건을 이유로 UCIE 자체 P9 엔진 연동을 더 미루지 않는다.
- P9 V1 인수 조건(독립 QA, 버전/라이선스, 서명 승인, 실제 소유자 PC end-to-end, 운영 V1 소유자 인수)이 증명되기 전에는 `v1_accepted=false`. 이 코드는 임의 생산 배포/자동 승격/스케줄러 등록을 하지 않으며, 정확히 불충족 조건을 출력한다.

## 완료 방향

새 PR을 무한히 늘리지 않는다. **새 통합 진입점과 독립 소비 실기의 Windows/Ubuntu 3.13/3.15 CI를 먼저 완료**, 로컬 D:\UCIE에는 **신규 Python 모듈 두 개만** 원자적으로 반영(기존 dirty 수정 불변). 사용자 PC 실호스트 위 세 명령 결과에서 실제 수집기/도서관/경험 계보의 자료를 확인하고, 실행되는 명확한 blocker만 보수. 정식 릴리스·권리·신뢰 서명은 허가/근거가 없으면 NO_GO로 별도 표시.
