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

## 완료 방향

새 PR을 무한히 늘리지 않는다. **새 통합 진입점과 독립 소비 실기의 Windows/Ubuntu 3.13/3.15 CI를 먼저 완료**, 로컬 D:\UCIE에는 **신규 Python 모듈 두 개만** 원자적으로 반영(기존 dirty 수정 불변). 사용자 PC 실호스트 위 세 명령 결과에서 실제 수집기/도서관/경험 계보의 자료를 확인하고, 실행되는 명확한 blocker만 보수. 정식 릴리스·권리·신뢰 서명은 허가/근거가 없으면 NO_GO로 별도 표시.
