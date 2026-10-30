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

## V1 재사용 적격성 조회 / 항목 선택 (2026-10-30 추가)

기존 `ucie_miner.product_v1` 명령의 `reuse_eligibility` 항목에서 읽기 전용으로 **공개 후보/합성 경험**과 **실제로 원본 서명 검증기를 통과한 기존 Serial4/5 Rulepack**을 구분한다. 별도 저장소 접근, 승인 체계, 파일 출력, 운영 원장 변경이나 추가 수집은 없다.

- `PUBLIC_CANDIDATE`: 소스 레지스트리 근거는 있어도 정확한 실행 버전과 개정별 배포 사용권이 검증되지 않았다. `selection_status=CANDIDATE_OR_EXPERIENCE_REUSE_BLOCKED`, 반출 불가.
- `SIGNED_MANUAL_RULE`: 사용자가 UCIE 내부의 **실제 Serial4 팩+공개 신뢰키** (선택적으로 Serial5)를 정확히 지정하고 기존 암호학적 원본 검증기가 현재 시점에 통과한 경우에만 `EXISTING_OWNER_SIGNED_MANUAL_REFERENCE_ONLY`. 원래 승인된 소유자 위험 인수/수동 사용 범위만 가리키며, **새로운 범용 반출·독립 QA/법적 사용권 승인·자동 적용을 의미하지 않는다.** 기존 패키지의 SHA-256이 고정된 참조 대상이다.
- `--select-item`에는 첫 조회에서 받은 정확한 64자리 `library_item_id`만 지정한다. 현 `--query`·`--domain`·`--limit`의 **표시된 제한 창** 안에서만 선택한다. 창에 없으면 `NOT_IN_CURRENT_BOUNDED_QUERY_WINDOW_NO_GO`이며 전체 도서관에 없다는 뜻이 아니다.
- `version_evidence_status`와 `rights_verification_status`를 각 항목에 표시한다. `new_generic_package_exportable_count=0`은 현재 구현이 새 범용 패키지의 배포를 승인하거나 실행하지 않음을 뜻한다.

읽기 전용 명령 예시 (이미 격리하여 준비한 UCIE checkout과 **그 checkout 전용 Python 환경** 사용):

```powershell
$env:PYTHONPATH = Join-Path $root 'src'
& $py -B -m ucie_miner.product_v1 --ucie-root $root --limit 20
# 서명팩이 실제 존재하고 UCIE 내부에 있을 때만, 기존 소유자 검증을 선택적으로 추가:
& $py -B -m ucie_miner.product_v1 --ucie-root $root --limit 20 --serial4-pack $serial4 --owner-public-trust $publicTrust
# 위 JSON의 reuse_eligibility.items에서 확인한 정확한 ID만 선택:
& $py -B -m ucie_miner.product_v1 --ucie-root $root --limit 20 --serial4-pack $serial4 --owner-public-trust $publicTrust --select-item $libraryItemId
```

이 조회는 기존 검증된 Rulepack **참조 가능성**만 보여주며 패키지 복사·서명·재배포·다른 프로젝트 스캔은 실행하지 않는다. 전체 UCIE V1 제품 수용 상태는 여전히 `v1_accepted=false`.

## V1 선택 항목 → 기존 W09 소비자 참조 결속 (2026-10-30)

기존 `ucie_miner.product_v1`의 **정확한 항목 선택**을 기존 `signed_rule_library.build_existing_pack_consumer_descriptor`에 연결했다. 별도 재사용/서명 시스템이나 신규 ZIP·API·외부 프로젝트 연계는 없다.

```powershell
# 아래 변수에는 이미 분리·검증된 UCIE 전용 checkout, Python 실행 파일,
# 기존 UCIE Serial4 서명팩, 공개 trust 키, 앞선 조회의 64자리 항목 ID를 사용.
$env:PYTHONPATH = Join-Path $root 'src'
& $py -B -m ucie_miner.product_v1 --ucie-root $root --limit 20 --serial4-pack $serial4 --owner-public-trust $publicTrust --select-item $libraryItemId --consumer-reference
```

요구조건: 선택 항목이 현재 제한된 검색창의 `SIGNED_MANUAL_RULE`이고, 원래 W07 서명·만료·범위·부모 SHA 검증을 통과한 *소유자 위험 인수 수동 규칙*이어야 한다. 이번 소비 참조 생성 시 **기존 W09 검증기를 한 번 더 호출**해 실제 원본 파일 서명과 만료를 재확인한다. W09의 정규 JSON `descriptor_sha256`, 선택한 정확한 `item_id`/규칙 ID/팩 serial/원본 SHA와 명시된 수동 사용 범위를 대조한다. 서명팩을 교체했거나 선택이 달라지면 실패한다.

반환 키 `selected_existing_w09_consumer_reference`는 **선택된 1개 기존 규칙**의 원본 W09 SHA-256 기반 참조 자료이며, 독립 소비자는 **각 실제 사용 시 원래 서명팩·만료·공개 trust·Serial5 부모 결속을 다시 검증**해야 한다. 단순 JSON 영수증만으로 사용 승인을 주장할 수 없다. 공개 후보·미승인 기술·합성 학습 기록, 다른 검색창의 ID 또는 서명팩/키 부재에서 `--consumer-reference`는 `P9_PRODUCT_FAIL_CLOSED`(종료코드 2)로 실패한다.

새 파일 출력·서명·배포·코드 실행·자동 규칙 승격·운영 DB 쓰기는 전혀 없다. 이는 **독립 소비자의 참조 계약을 기존 서명 검증기에 연결**한 것이지 새 범용 패키징이나 소비자 측 실제 실행·서명 재검증까지 완료했다는 뜻이 아니다. 일반 외부 배포/라이선스·독립 QA 승인, UCIE 제품 전체 `v1_accepted`는 여전히 불충족이다.

## V1 독립 프로세스의 W09 소비자 재검증 (2026-10-30)

추가 모듈: `ucie_miner.manual_consumer_v1`. **기존 UCIE 설치에 포함된 별도 Python 프로세스**가 생산자 `--consumer-reference`의 정확한 JSON 참조 하나를 입력받아, 기존 W09 `build_existing_pack_consumer_descriptor` 검증기를 직접 실행한다. 이 검증은 원본 Serial4 서명·소유자 공개 신뢰키·현재 만료 조건과 선택적 Serial5의 부모 결속을 포함한다. 소비자는 앞선 생산자 JSON의 승인/검증 주장만 믿지 않는다.

동일한 UCIE 전용 checkout 및 Python 환경에서 실행하는 **읽기 전용** PowerShell 예시:

```powershell
$env:PYTHONPATH = Join-Path $root 'src'
# $root, $py, $serial4, $publicTrust, $libraryItemId는 UCIE 전용으로 확인된 값
$producerOutput = & $py -B -m ucie_miner.product_v1 --ucie-root $root --limit 20 --serial4-pack $serial4 --owner-public-trust $publicTrust --select-item $libraryItemId --consumer-reference
if ($LASTEXITCODE -ne 0) { throw 'UCIE_W09_PRODUCER_FAILED' }
$selected = ($producerOutput | ConvertFrom-Json).selected_existing_w09_consumer_reference
if (-not $selected) { throw 'UCIE_W09_REFERENCE_MISSING' }
$referenceJson = $selected | ConvertTo-Json -Depth 16 -Compress
$receipt = $referenceJson | & $py -B -m ucie_miner.manual_consumer_v1 --ucie-root $root --serial4-pack $serial4 --owner-public-trust $publicTrust
if ($LASTEXITCODE -ne 0) { throw 'UCIE_W09_CONSUMER_REVERIFY_FAILED' }
$receipt | ConvertFrom-Json
```

Serial5 항목에는 두 명령 모두 확인된 기존 `--serial5-pack $serial5` 인자를 **함께** 지정한다. 새 서명이나 ZIP을 생성하지 않으며 사용자가 지정한 UCIE 내부의 기존 공개 trust 키만 읽는다. 소비자 입력은 최대 4KiB UTF-8 JSON(Windows PowerShell 5.1 BOM 허용); 중복 필드·변조된 서명팩·다른 서명키·잘못된 항목·출력 승인 위조·임의 추가 필드는 모두 실패한다. 실패 시 입력 JSON이나 경로를 출력하지 않는다.

소비 성공 결과 `ORIGINAL_SIGNED_RULE_REVERIFIED_MANUAL_REFERENCE_ONLY`의 의미는 **현재 원본의 서명·키·만료를 소비자 프로세스가 다시 확인하고, 소유자 위험 인수 수동 규칙 ID만 열람했다**는 뜻이다. 그 자체로 사용자 프로그램 코드 검사·규칙 적용·버전 적합성·독립 QA·원본 코드 반출·타 프로젝트 사용을 수행하거나 승인하지 않는다. 외부 범용 배포·자동 규칙 승격·신규 승인·운영 DB 쓰기는 모두 비활성화이며 전체 제품 `v1_accepted=false` 유지. 실제 제품의 독립 설치/배포 QA 및 소유자 PC 검증은 별도 미완료 항목이다.

## V1 통합 수동 서명규칙 검사 — 독립 소비자에서 직접 실행 (2026-10-30)

기존 W09 재검증 소비자 `ucie_miner.manual_consumer_v1`에 `--scan-python`을 추가한다. **새 규칙·서명 승인·스캐너·가상 공개 근거를 만들지 않는다.** 생산자 `product_v1 --consumer-reference`로 만든 단일 W09 참조와 사용자가 명시적으로 제공한 Python 소스 문자열을 `{"reference": ..., "source": ...}` JSON 하나로 전달한다. 소비자는 기존 W09 검증기로 원본 Serial4/선택적 Serial5 팩의 서명·만료·공개 trust·부모 SHA를 재검증한 뒤 기존 `inspect_existing_python()`을 호출한다. 그 결과 가운데 **선택한 하나의 서명된 Python 규칙과 일치하는 정적 수동 검토 후보**만 반환한다.

사용 예 (사전에 승인된 UCIE 전용 checkout의 실제 변수 `$root`, `$py`, `$serial4`, `$publicTrust`, `$libraryItemId` 사용):

```powershell
$env:PYTHONPATH = Join-Path $root 'src'
$producer = & $py -B -m ucie_miner.product_v1 --ucie-root $root --limit 20 --serial4-pack $serial4 --owner-public-trust $publicTrust --select-item $libraryItemId --consumer-reference
if ($LASTEXITCODE -ne 0) { throw 'UCIE_W09_PRODUCER_FAILED' }
$ref = ($producer | ConvertFrom-Json).selected_existing_w09_consumer_reference
if (-not $ref) { throw 'UCIE_W09_REFERENCE_MISSING' }
$pythonSource = @'
import os
from concurrent.futures import ThreadPoolExecutor
def review(folder, callback):
    iterator = os.scandir(folder)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return pool.submit(callback, iterator).result()
'@
$payload = @{ reference = $ref; source = $pythonSource } | ConvertTo-Json -Depth 16 -Compress
$result = $payload | & $py -B -m ucie_miner.manual_consumer_v1 --ucie-root $root --serial4-pack $serial4 --owner-public-trust $publicTrust --scan-python
if ($LASTEXITCODE -ne 0) { throw 'UCIE_SIGNED_MANUAL_PYTHON_SCAN_FAILED' }
$result | ConvertFrom-Json
```

대상은 승인된 기존 Serial4의 `PY_SCANDIR_SHARED_ITERATOR_RACE`, 기존 Serial5가 명시되면 `PY_ASYNCIO_PROTOCOL_FACTORY_PRETRANSPORT_LEAK` **단 두 Python 규칙**이다. 다른 서명 규칙 또는 PowerShell 규칙을 Python 검사로 허위 판단하지 않도록 차단한다. Serial5 선택 시 생산자·소비자 모두 `--serial5-pack`에 동일한 검증된 UCIE 내부 서명팩 경로를 추가해야 한다.

이 모드는 JSON 입력 크기와 내부 Python 소스 16KiB를 제한한다. 경로로 전달받은 사용자 프로젝트 파일을 자동 열람하지 않고, 외부 소스를 실행하거나 네트워크·운영 DB·모델·규칙에 변경을 가하지 않는다. 결과 `SELECTED_SIGNED_STATIC_FINDINGS_REVIEW_REQUIRED`는 **정적 패턴의 수동 검토 후보**이지 실제 런타임 오류의 확정이 아니다. `NO_SELECTED_RULE_PATTERN_NOT_SAFETY_PASS`도 해당 소스의 안전성을 보장하지 않는다. 같은 소스의 다른 규칙 후보와 미승인 규칙의 결과는 승인된 것처럼 합산·출력하지 않는다.

원본 W09 참조·서명·만료·항목 ID·서명 소스 SHA가 달라지면 `MANUAL_CONSUMER_FAIL_CLOSED`로 종료한다. GitHub CI의 임시 테스트용 서명팩 검증은 실제 소유자 호스트의 기존 서명팩에 대한 운영 수용 PASS와 다르다. 전체 `v1_accepted=false`, 새 범용 배포·자동 적용 불가를 유지한다.

## V1 실제 UCIE 운영환경 수용 현황 — 단일 읽기 전용 명령 (2026-10-30)

새 모듈 `ucie_miner.v1_host_readiness`는 기존 Python 3.13/3.15 환경에서 원래 UCIE 전용 운영 경로를 **읽기 전용**으로 관측하는 단일 명령이다. 운영 DB를 마이그레이션하거나 초기화하지 않고, 새 공개 API 요청·권한 등록·자동승격·서명팩 발행·개인/다른 프로젝트 자료 열람을 하지 않는다.

이 명령에서 검사하는 항목은 기존 `runtime/public_miner.sqlite3`의 읽기 전용 SQLite 무결성·후보 상태·허용된 출처·최근 실행 시각·`last_run.json`의 상태, 기존 Stage10 미승인 후보, 별도 P10 대기열, 별도 P11 공개 경험 원장, 공급원 레지스트리, V1 Library 제품 조회 차단 사유이다. **명시적으로 기존 Serial4 서명팩과 소유자의 공개 신뢰키를 제공한 경우에만**, 실제 원본 서명·만료를 재검증하고 UCIE가 작성한 고정 합성 Python `os.scandir` 사례로 기존 수동 스캐너를 실행한다. 사용자 코드나 실제 사용자 파일은 자동으로 열람하지 않는다.

소스 버전이 PR #145의 병합 커밋을 포함하는 별도의 확인된 UCIE 전용 checkout에 있어야 한다. 현재 `D:\UCIE` 작업 트리에 이미 로컬 수정 파일이 있으므로 **강제 checkout, reset, pull 덮어쓰기 금지**. 깨끗한 별도 checkout의 `src`를 `PYTHONPATH`로 지정해 최신 검사기만 불러오고, 실제 운영 루트는 `--ucie-root D:\UCIE`로 그대로 읽는 방법을 사용한다.

```powershell
$releaseRoot = 'D:\UCIE_RELEASE\UCIE' # 실제 설치되어 있고 최신 main을 검증한 별도 checkout에 한정
$runtimeRoot = 'D:\UCIE'
$py = 'D:\UCIE\.venv\Scripts\python.exe'
if (-not (Test-Path (Join-Path $releaseRoot 'src\ucie_miner\v1_host_readiness.py'))) { throw 'UCIE_HOST_OBSERVER_SOURCE_MISSING' }
$env:PYTHONPATH = Join-Path $releaseRoot 'src'
& $py -B -m ucie_miner.v1_host_readiness --ucie-root $runtimeRoot
if ($LASTEXITCODE -ne 0) { throw 'UCIE_HOST_OBSERVER_FAIL_CLOSED' }
```

기존 UCIE 내부에 실제 서명팩·공개 신뢰키가 존재하고 정확한 경로를 알고 있을 때만 동일 명령 뒤에 `--serial4-pack $serial4 --owner-public-trust $publicTrust`를 덧붙인다. Serial5는 `--serial5-pack $serial5`를 추가한다. 개인키는 입력하거나 검사하지 않는다. 발급된 패키지가 이미 만료됐다면 검사기는 실패/미검증으로 보고해야 하며 기존 서명을 조작하거나 갱신하지 않는다.

**Windows 예약 작업 확인은 별도다.** 이 스크립트는 `schtasks`를 실행하거나 Windows 작업 상태를 검증했다고 주장하지 않는다. 운영자 PC에서 별도로 `schtasks /Query /TN UCIE-PublicMiner-Hourly /V /FO LIST`의 최근 실행 결과와 시각을 확인해야 한다. 3시간 이내 완료 기록은 단회 신선도 관측일 뿐 매시간 안정 가동 증명은 아니다. `LAST_CYCLE_RECEIPT_NOT_FOUND`, P11 미활성, 소스 원장 부재, 사용권 미승인 등은 NO_GO로 보존한다.

출력의 `UCIE_V1_LOCAL_OBSERVATIONS_NO_GO`는 정상적인 수용 평가 결과다. GitHub 4환경 CI PASS는 **실제 사용자 PC 운영 DB나 실제 서명팩 PASS가 아니다**. 일반 범용 패키지의 버전·사용권·배포 승인이 완료되지 않았으므로 `real_host_v1_accepted=false` 유지. CLI가 파일을 쓰지 않더라도 실행 환경/SQLite의 OS-level 임시 부수효과를 원리적으로 부정하지 않으며, 기록한 0건은 이 명령의 명시적 DB 변경/스케줄러/자동승격 동작에 한정한다.

## V1 범용 검색 엔진 초안 — 실제 격리 소비자 QA와 버전·권한 경계 (2026-10-30)

기존 UCIE 작성 `portable_exact.py`의 결정적 **초안 ZIP**을 외부 프로젝트에 배포하지 않고, OS 임시 디렉터리의 별도 Python `-I -B` 프로세스로 가져와 실행·결과를 비교하는 `--qa-portable` 옵션을 추가하였다. 새 ZIP 릴리스·서명·실행 스케줄·외부 코드 수집을 만들지 않는다. 검증이 끝나면 임시 UCIE 작성 파일은 정리한다.

```powershell
# 이미 검증한 별도 UCIE RELEASE 체크아웃의 소스와 현재 UCIE 운영 DB만 사용
$env:PYTHONPATH = 'D:\UCIE_RELEASE\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.product_v1 --ucie-root 'D:\UCIE' --qa-portable
```

실제 Stage10/12/15에 연결된 W04 읽기 전용 PR 후보가 있다면 **비승인 공개 메타데이터만** 개수 상한 20건으로 가져와 격리된 first-party 검색 엔진에서 정확 질의 결과를 계산하고 UCIE 내부 기준 결과와 대조한다. 공개 git/git 커밋 항목은 현행 portable PR-only 계약에서 명시적으로 제외·계수한다. W04 원장이 없거나 연결 근거가 미완성이면 자동으로 **UCIE 작성 합성 데이터만** 격리 검사하며 실제 공개 원장 검증이라고 주장하지 않는다. 운영 원장의 DB는 query-only이며, 공개 원본 코드·패치·사용자 프로젝트 파일을 격리 환경으로 반출하지 않는다.

격리 검증은 단일 질의(선형 검색), 복수 질의(인덱스 분기), 없는 결과의 대조군, 압축 ZIP 바이트·매니페스트·소스 SHA-256의 결정성을 검사한다. 승인/라이선스/재배포 플래그 위조, 원본 ZIP 변경, 타 출처 PR 식별자, 격리 소비자 결과 위조는 실패로 처리한다. 제품 `--qa-portable`은 `--export-draft` 및 `--verify-draft`와 동시 실행할 수 없다.

성공 상태 `FIRST_PARTY_ISOLATED_CONSUMER_QA_PASS_NOT_RELEASED`는 **UCIE 자체 작성 메타데이터 검색 엔진의 격리 실행 및 결과 일치**에만 적용된다. 타인의 공개 엔진·스킬·학습 로직이 실제로 실행·검증되었음을 뜻하지 않는다. 후보별 **실제 적용 버전 0건 검증**, **개정별 재배포 사용권 0건 승인**, **외부 독립 QA 미실시**, **소유자 릴리스 미승인**, `v1_accepted=false`를 명시한다. 승격, 영구 학습, 새 패키지 배포, 타 프로젝트 설치는 하지 않는다.

다음 제품 단계는 수집된 공개 엔진/스킬의 개별 릴리스 계보·적용 버전·라이선스/권리와 사용 방법을 명시적으로 검토하고, 승인된 산출물만 외부 소비 계약에 연결하는 것이다. 서명팩의 소유자 위험 인수 수동 사용과 별개로 신규 범용 반출 승인이 필요하다.

## V1 정확한 공개 후보 선택 시 릴리스·권리 검토 — 기존 근거만 사용 (2026-10-30)

기존 P9 `--select-item`가 미검증 W04 공개 후보를 선택한 경우 새 읽기 전용 응답 `selected_public_release_rights_review`를 함께 반환한다. 선택한 `library_item_id`와 W04 근거 SHA/병합 커밋을 원본 `_evidence_readiness`에 다시 연결하고, 이미 소스에 고정한 세 공개 PR의 라이선스/릴리스 관측을 정확한 PR URL 및 병합 SHA와 대조한다. 별도 API 호출·임시 DB·자동승격·범용 패키지 생성이 없다.

선택된 공개 후보 3가지 상태:

- `EXACT_RELEASE_BUG_REPRODUCED_MANUAL_REVIEW_NO_GO`: PowerShell PR #28087처럼 **원래 기록한 특정 PowerShell 7.6.6 Windows x64와 Linux x64 공식 바이너리**에서 오류가 실제로 재현된 경우에만 해당 두 런타임/해시/기존 CI 링크를 표시한다. 모든 버전의 오류, 수정 포함 여부, backport 없음, 배포 사용권은 **증명되지 않았다**.
- `MERGE_LICENSE_PINNED_RUNTIME_APPLICABILITY_UNKNOWN_NO_GO`: 정확한 공개 병합 SHA와 저장소 LICENSE blob이 고정됐어도 특정 런타임 영향·수정 포함 여부는 미확인인 후보.
- `UNPINNED_PUBLIC_MERGE_NEEDS_MANUAL_REVIEW_NO_GO`: 정확한 기존 내부 검토 기록이 없는 공개 후보. 다른 PR이나 부정확한 SHA의 근거를 상속하지 않는다.

예시: 기존 `python -B -m ucie_miner.product_v1 --ucie-root D:\UCIE --query <공개목적검색어> --limit 20 --select-item <W04에서 반환된 64자리 library_item_id>` 결과에서 `selected_public_release_rights_review`를 확인한다. 선택하지 않거나 공개 후보가 아닌 서명된 수동 규칙을 선택하면 이 항목은 `null`로 유지된다. 선택 대상이 현재 제한된 검색창에 없으면 전체 Library에 없다고 단정하지 않는다.

**라이선스 출처를 보았다는 사실과 코드 재배포 허용은 다르다.** PR #28087의 LICENSE.txt Git blob/가족명 관측은 per-file 라이선스, 고지 의무 및 법적 승인 완료를 뜻하지 않는다. 소스 수정·재패키징·사용자/외부 프로젝트 스캔, 모델 변경, 배포 없이 검토할 근거만 제공한다. 모든 후보의 `new_package_export_allowed=false`, `v1_accepted=false` 유지.

## V1 직접 실행형 범용 엔진 독립 소비 ZIP — 1.2.0 DRAFT (2026-10-30)

기존 초안은 `portable_exact.py`를 외부 프로세스에서 별도 import해야 했다. 이제 UCIE 자체 작성 `__main__.py`와 기존 `portable_exact.py`를 하나의 결정적 `ucie_portable_exact_1_2_0_DRAFT.zip`에 포함하여 **UCIE를 설치하지 않은 Python 표준 라이브러리 환경에서도 ZIP을 직접 실행**한다. 이는 사용자 승인 없는 배포/설치가 아닌 소프트웨어 QA를 위한 실행 계약이다. 검색 API는 `1.1.0` 유지, ZIP 포맷/실행 진입점은 `1.2.0`으로 분리하여 과거 1.1.0 초안 SHA를 덮어쓰지 않는다.

`python -I -B <검증된_기존_DRAFT_ZIP>`은 stdin으로 정확한 JSON `{"items": [...], "queries": [["repo:python/cpython","Python","PUBLIC_TECHNICAL_EVIDENCE","API_CONTRACT"]], "limit": 20}`을 받아 JSON을 stdout에 반환한다. 필수 세 필드 외 추가 옵션/CLI 플래그, 입력 32KiB 초과, JSON 중복 키·NaN, 미승인 저장소/개인 경로·사용권/승인 위조·잘못된 PR URL은 종료 2 및 `STANDALONE_DRAFT_FAIL_CLOSED`. 원본 소스 코드를 검색하는 엔진이 아닌, 이미 소스 결속된 **비승인 공개 메타데이터만 검색**하는 엔진이다.

기존 `product_v1 --qa-portable`의 읽기 전용 QA는 ZIP 바이트·매니페스트와 두 퍼스트파티 코드의 SHA를 확인하고, 임시 디렉터리에 실제 ZIP을 작성하여 **그 ZIP만 별도 Python `-I -B` 프로세스로 직접 실행**한 뒤 기존 검색 API 결과와 3개 질의 사례를 대조한다. QA 후 임시 ZIP은 정리한다. 검증된 서명팩처럼 새 패키지를 운영 설치하거나 독립 프로젝트에 반출하지 않는다.

검증 상태 `FIRST_PARTY_ISOLATED_CONSUMER_QA_PASS_NOT_RELEASED`는 이 UCIE 작성 ZIP의 직접 실행·출력 동등성까지만 의미한다. 서명 없음, 소유자 배포 승인 없음, 외부 독립 QA 없음, 제3자 소스 사용권 승인 0건, `package_released=false`, `v1_accepted=false`. **임의의 ZIP을 직접 실행하지 말고** 먼저 신뢰하는 UCIE 코드에서 바이트 단위 무결성을 확인해야 한다. 앞선 1.1.0 초안과 1.2.0 초안의 해시는 다르며 과거 QA 영수증은 변하지 않는다.

## V1 퍼스트파티 릴리스 준비 묶음 — 버전 1.3.0 미배포 초안 (2026-10-30)

이 묶음은 UCIE가 직접 작성한 표준 라이브러리 전용 `portable_exact` 검색기를 제품화하는 데 필요한 남은 **기술/권리 검토**를 하나로 통합한다. 별도 릴리스, 키 발급, 서명, 외부 배포 또는 운영 DB 변경을 수행하지 않는다.

1. **실제 보안 결함 수정:** stdin은 32KiB지만 동일한 결과를 32개 질의로 복제하면 stdout이 크게 늘어날 수 있다. 초안 ZIP의 진입점은 64KiB 초과 출력을 전부 차단하고 짧은 `STANDALONE_DRAFT_FAIL_CLOSED` JSON/exit 2만 출력한다. 부분 결과나 잘린 JSON은 절대 출력하지 않는다.
2. **재현 가능한 아카이브 헤더:** `ZipInfo.create_system = 3`, 고정 UTC ZIP 시각과 일반 파일 0644 모드, 지정된 5개 엔트리만 허용한다. 동일 코드 기준 Windows/Linux의 작성 OS 헤더 차이를 제거한다. 압축 엔진/런타임이 완전히 같다는 별도 주장 없이 동일 프로세스 재생성 ZIP 바이트를 직접 비교한다.
3. **권한·의존성 경계:** `RIGHTS_SECURITY.txt`는 법적 라이선스나 외부 권리 승인이 아님을 밝히고, `MANIFEST.json`은 코드 두 파일과 권한 알림의 각각 SHA-256, stdin/stdout 한도, stdlib만 필요함을 명시한다. UCIE 전체 개발 의존성 `cryptography`는 이 별도 ZIP의 런타임 의존성이 아니다.
4. **실제 배포 장애:** 현재 검토한 UCIE 저장소 루트에 `LICENSE`, `LICENSE.txt`, `COPYING`, `COPYING.txt` 파일은 없다. 이미 공개 저장소라는 사실이나 `SECURITY.md`의 'open-source code' 설명이 라이선스 권리 부여를 대신하지 않는다. 라이선스가 나중에 생겨도 소유자·권리·고지·의무를 검토하지 않으면 승인하지 않는다.

운영 루트 `D:\UCIE`의 변경 파일을 건드리지 않고 별도 RELEASE checkout에서 아래 단회 명령으로 이 QA를 실행한다. 운영 DB, 서명팩, 예약 작업, 외부 코드에는 변경이 없다.

```powershell
$env:PYTHONPATH = 'D:\UCIE_RELEASE\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.portable_release_readiness --ucie-root 'D:\UCIE'
```

응답 `FIRST_PARTY_RELEASE_TECHNICAL_READINESS_REVIEWED_NO_GO`에서 `canonical_zip_sha256`, 5개 엔트리, 정적 import 금지목록 검사, 명시적인 라이선스 상태와 `blocked_release_requirements`를 확인한다. 이 결과는 자체 정적 검사에 불과하며 악성코드 전문 감사, 실제 OS 강제 격리, 외부 독립 QA를 대체하지 않는다. 제품 수용 `v1_accepted=false`, 배포 `package_released=false` 유지.

**남은 결정은 실제 소유자가 해야 한다:** (a) 코드 소유자·기여자·권한과 선택한 LICENSE/COPYING 고지, (b) 독립 보안·패키지 QA 범위, (c) 배포 패키지 서명 신원·비밀키 보관·릴리스 승인, (d) 제3자 후보 코드를 제외하는 첫 배포 범위. 무단으로 오픈소스 라이선스를 결정하거나 서명키를 사용하지 않는다. 1.2.0 및 1.3.0 ZIP은 서로 다른 초안이며 과거 SHA/검증은 그대로 유지된다.

## P8 실제 자동학습·자동개선 판단 연결 — P11 기존 실행 경로 확장 (2026-10-30)

기존 P11 (`p11_closed_loop.learn_one`)은 P10 `EXPERIENCE_CLOSED_LOOP` 워커가 **P11이 이미 활성화된 UCIE 루트**에서 호출하는 실제 경로이다. 이번 변경은 신규 스케줄러·운영 패키지·외부 모델 학습 경로를 만들지 않고 이 진입점을 개선했다.

- **검증 경계:** 새 실험마다 기존에 구현한 UCIE 자체 합성 알고리즘 3종 중 하나의 기본/개선안 결과를 실제 실행하고, 결과 동등성·불일치 수·초기 구축 비용을 포함한 연산 수·외부 코드 미실행/DB 미변경/프로덕션 미적용 플래그를 교차 검증. 단순 '정확도 PASS'만으로 연산 개선이라고 판단하지 않는다.
- **자동 피드백:** P11 경험 원장의 기존 기록을 직접 조회하여 정확성 + 연산 감소가 모두 확인된 경우에만 다음 합성 작업량(128→256→512→128)을 선택한다. 어떤 레시피라도 기존 기록에 오탐/비용 역전/안전 불일치가 있으면 해당 레시피를 자동 `HOLD`하고 다른 공개 후보의 독립 레시피는 계속 처리한다.
- **불변 승인 경계:** `FIRST_PARTY_RETEST_PROPOSAL_NOT_ADOPTED`는 **추가 실험 제안**이지 안전한 코드 자동 생성, 규칙 승인, 운영 채택 또는 모델 재학습을 뜻하지 않는다. 실패 실험은 `FIRST_PARTY_REGRESSION_HOLD_NO_GO`. 원본 PR 코드·프로젝트 코드는 가져오지 않는다.
- **경험/개선 결속:** 선택한 공개 PR 메타데이터 ID, 레시피, 기본/개선 연산량, 불일치, 결과, 영수증 SHA-256을 P11 기존 SQLite 안의 추가 `improvement_review` 테이블에 기존 경험 등록과 **단일 트랜잭션**으로 저장한다. 기존 수십 건의 P11 기록은 자동 소급하여 '개선 성공'으로 꾸미지 않는다. 운영 PublicMiner DB·서명팩은 건드리지 않는다.
- **중복·실패:** 동일 PR의 중복 리뷰를 저장하지 않고, 실패 레시피만 보류하므로 나머지 P10 작업이 계속된다. 새 작업 등록·예약 작업 변경 없음. P11 미활성 루트에서는 기존처럼 동작하지 않는다.

실제 호스트의 P11 read-only 상태 조회:

```powershell
$env:PYTHONPATH = 'D:\UCIE_RELEASE\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.p11_closed_loop --ucie-root 'D:\UCIE' --status
```

신규 `improvement_review_record_count`는 **새 버전이 실제 호스트의 P11 워커에서 실험을 기록한 이후** 증가한다. GitHub CI 합성 시험 PASS나 기존 65건 기록만으로 신규 개선 폐회로 실운영을 PASS로 표시하지 않는다. 외부 독립 QA, 배포 허가, 사용자 프로젝트 자동 적용 및 UCIE V1 최종 수용은 여전히 별도다.

## P8 기존 UCIE 운영 PC로 단회 무손실 적용 — 2026-10-30

PR #150의 P11→P10 첫 실사용 코드를 이중으로 작성하지 않고 정확한 기존 세 파일만 `D:\UCIE_RELEASE\UCIE`에서 `D:\UCIE`로 반영하는 **소유자 실행 단회 동기화**를 추가했다: `src/ucie_miner/p11_improvement_gate.py`, `src/ucie_miner/p11_closed_loop.py`, `src/ucie_miner/runtime_pipeline.py`.

운영 `D:\UCIE`에는 13개 추적 수정과 다수 미추적 파일이 있으므로 `git pull`, `git reset`, `checkout`, 운영 소스 루트 통째 덮어쓰기를 하지 않는다. 소스 Git 체크아웃은 깔끔하고 PR #150 main 병합 `b6a5244925bfe59cd3b64fe2a6bf2f9bedfd9d42`를 조상으로 포함해야 한다. 이 세 대상은 해당 커밋의 `git show` 원본과 정확하게 같아야 한다. 운영 대상은 해당 PR의 이전 main `9f1adce92f1eaf13c306da9fe42538f4e619c907`와 **바이트 단위 동일하거나**, 이미 최신 바이트거나, 새 파일은 없어야 한다. 어느 하나라도 다른 로컬 버전이면 `LOCAL_P8_SOURCE_DRIFT_NO_OVERWRITE`로 중단한다.

```powershell
# 먼저 소스 전용 독립 체크아웃만 최신 병합 main으로 갱신
$src='D:\UCIE_RELEASE\UCIE'
$expected='REPLACE_WITH_VERIFIED_HEAD_FROM_GITHUB_MAIN'
if ((git -C $src status --porcelain --untracked-files=all)) { throw 'UCIE_RELEASE_DIRTY' }
git -C $src fetch --no-tags origin main
if ($LASTEXITCODE -ne 0) { throw 'UCIE_FETCH_FAILED' }
if ((git -C $src rev-parse FETCH_HEAD).Trim() -ne $expected) { throw 'SOURCE_HEAD_CHANGED' }
git -C $src checkout --detach $expected
$old=$env:PYTHONPATH
try {
  $env:PYTHONPATH=Join-Path $src 'src'
  & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.p11_host_sync
  # 승인된 정확 세 파일만 원본 백업 후 원자적 반영. 초안 소스 검증 실패시 미변경
  & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.p11_host_sync --apply
  & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.p11_closed_loop --ucie-root 'D:\UCIE' --status
} finally { $env:PYTHONPATH=$old }
```

단회 적용(`--apply`)은 이미 초기화한 P10 작업 큐가 있고 `RUNNING` 임대 작업이 0이어야 한다. 대상 파일 3개를 `runtime/p8_pinned_sync_backups/` 아래에 백업하고, 원자적 교체 후 바이트 SHA 검증한다. 중간 오류 시 이전 파일을 복원하며, 정상 종결은 `P8_HOST_PINNED_CODE_APPLIED_NOT_LIVE_WORKER_ATTESTED`. `P8_HOST_ALREADY_PINNED_NO_CHANGE`면 재실행 중복 적용 없음. 어느 경우에도 기존 예약 작업·공개 마이너 DB·기타 로컬 파일을 변경하지 않는다. P11 경험 원장은 실제 **다음 성공적인 P10 실험 수행 시점에만** `improvement_review` 판단이 추가된다. 이 명령은 P10 스케줄러를 등록하거나 서비스 기동을 확인하지 않으므로 별도 읽기 전용 예약작업 확인이 필요하다.

기존 P11 로컬 파일이 기존 main과 다를 경우 **강제 적용 금지**. SHA 또는 전체 차이 확인 후 별도 정확 대상 변경만 통합해야 한다. 이 차단은 개발 실패가 아니라 원본 보존 정책이다.

## 완료 방향

새 PR을 무한히 늘리지 않는다. **새 통합 진입점과 독립 소비 실기의 Windows/Ubuntu 3.13/3.15 CI를 먼저 완료**, 로컬 D:\UCIE에는 **신규 Python 모듈 두 개만** 원자적으로 반영(기존 dirty 수정 불변). 사용자 PC 실호스트 위 세 명령 결과에서 실제 수집기/도서관/경험 계보의 자료를 확인하고, 실행되는 명확한 blocker만 보수. 정식 릴리스·권리·신뢰 서명은 허가/근거가 없으면 NO_GO로 별도 표시.
