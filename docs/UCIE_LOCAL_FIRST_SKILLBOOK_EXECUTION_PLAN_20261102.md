# UCIE 로컬 우선 지식 생산 엔진 — 통합 구축 및 구동 인수 계획

- 작성: 2026-11-02 KST / UCIE ONLY
- 상태: 제안·기술 근거 확인 완료, **운영 PC 직접 인수 미확인 / 신규 스킬서적 자동 생산 NOT_IMPLEMENTED / 유료 출시 NO_GO**
- 목적: 기존 Windows PC의 UCIE 엔진/작업 대기열과 기존 공개자료 원장을 최대한 재사용하여 **외부 AI API 기본 호출 0, GPU 기본 OFF, 다른 PC 작업 우선, 증분 지식 생산**의 안전한 내부 베타를 구축한다.
- 작성 기준 GitHub main: b2941dbe8bb447dec2dd8a179b4b7ea61b9e28dc (PR #172 SkillBook mission merged)
- 대상 신규 배치 PR: https://github.com/tmdrkdtn1-project/UCIE/pull/173 (OPEN; must fix/recheck CI before merge)
- 제품 정본: docs/UCIE_SKILLBOOK_PRODUCT_MISSION_V1_20261102.md, docs/ROADMAP.md
- 이 문서는 **계획이며 구현/운영 승인, scheduler 설치, 모델 훈련, 외부 자료 추가의 허가가 아니다.**

## 결정: 지금 시작 가능한가?

| 구분 | 결정 및 근거 |
| --- | --- |
| GitHub에서 UCIE 자체 코드 개발·별도 합성 시험 | **GO NOW**. 공개 저장소 접근 가능, 기존 P10/P11·스킬서적 메타 계약 및 CI 존재 |
| 기존 승인 범위 안의 읽기 전용 라이브러리 조회·기존 수집기 유지 | **CONDITIONAL GO**. 실제 owner Windows scheduler/receipt 및 현지 SHA 상태를 다시 확인해야 함 |
| 새 로컬 스킬서적 메타데이터 배치의 실PC 연결 | **HOLD**. PR #173 4개 CI 중 Windows Python 3.15 1개 실패, 브랜치 미병합, owner-host 미검증 |
| 새로운 무거운 자율 작업·자동 규칙 승인·고객 의뢰 편입 | **NO_GO**. 실PC 자원 격리·검증·고객 데이터 정책 미구현 |
| 유료 고객 서비스/상용 SkillBook 공개 | **NO_GO**. 독립 시험, 사용권, 콘텐츠 품질, 고객 결제/보안/복구 미검증 |

UCIE 로컬 전용 관리 연결 점검 시 "Tunnel-client has not been seen for 300 seconds" 오류가 발생했다. 이 오류는 **원격 관측 불능**이지 실제 Windows 작업 중지의 증거가 아니다. 클라우드 GitHub CI PASS도 PC에서 동작한다는 증거가 아니다.

## 재사용할 현재 코드 자산

1. src/ucie_miner/runtime_pipeline.py: P10 1분 검사, 기존 고정된 5개 업무와 owner opt-in P11 2개 추가 유형, 최대 3개의 독립 워커, 180초 작업 예산·heartbeat·lease fencing. **현재의 3개는 가벼운 기존 작업의 최대치**이고, 새 고부하 작업까지 3개 돌리자는 뜻이 아니다.
2. src/ucie_miner/pending_queue.py: 한 업무가 막혀도 다른 업무 진행, dedupe key 및 backoff; 운영 원장과 별도 UCIE 대기열 DB.
3. src/ucie_miner/source_registry.py + library_entry.py + library_search.py: 승인된 공개 기술 근거 출처/버전/기초 메타데이터.
4. src/ucie_miner/product_v1.py + portable_exact.py: 읽기 전용 통합 검색, UCIE 자체 검색 모듈, 합성 검증, 미승인 초안.
5. src/ucie_miner/skillbook_blueprint.py: PR #172에서 병합된 미검증 공개 기술 메타데이터 초안 구성.
6. src/ucie_miner/internal_skillbook_batch.py: PR #173의 **미병합** 8작업/80후보 인메모리 배치, 로컬 0 AI 호출 경로. 생산형 SkillBook 또는 독립 worker 실행이 아님.
7. docs/UCIE_V12_HOURLY_PROOF_AND_QUALITY_LOOP_20261101.md: 기존 Windows 시간당 수집기의 진짜 태스크 이벤트 + 영수증을 함께 검증하는 읽기 전용 절차.

기존 외부 공개 데이터 수집 승인: 공식 기술 문서·릴리스·보안 권고와 python/cpython, PowerShell/PowerShell, git/git, modelcontextprotocol/python-sdk, actions/runner-images만. 고객 프로젝트, 다른 프로젝트, 대화, 앱, 비공개 파일을 전역 지식으로 수집하지 않는다.

## 최종 엔진 분업

- **Public Intake (기존)**: 허용된 공식 자료만 bounded fetch, revision/SHA provenance, dedupe. 기존 hourly를 그대로 보존하고 스케줄러 신규 등록 없음.
- **P10 Task Control (기존)**: job 상태, 임대, 우선순위, 작업 중단/재시도, 고부하 종류별 한도, CPU·메모리 예산. 신규 작업 연결은 별도 심사 후 고정 타입만.
- **Metadata Processor (기존 + PR #173)**: 분류, 소스 검증, 버전/의존성, 내용 주소 식별, 동등 입력 재사용. 이 구간은 외부 모델 호출 불필요.
- **Knowledge Value Engine (추가)**: 유사 기술 병합·새로움과 반복 가치 평가, 오류·반례·제약 추출. 단순 제목 분류나 SHA 일치만으로 품질/권리 인증 불가.
- **SkillBook Author (추가)**: UCIE 자체 작성 설명과 예제·전제·금지 조건, 챕터/머신 계약, 테스트 레시피. 우선 규칙+템플릿으로 실물 1권 제작. 고급 의미적 추론이 필요하면 별도 로컬 모델 선택 평가.
- **Evidence QA (기존 + 추가)**: 실제 환경에 맞는 UCIE-authored 합성 및 독립 양성/음성 시험, 출처·버전·권리 제한, fail-closed HOLD. 외부 코드를 신뢰하거나 실행하지 않는다.
- **Library Evolution (기존 + 추가)**: 라이브러리의 후보/시험/검증/승인/배포 상태를 분리, dependency impact-based 재시험, 변경·폐기/정정 provenance.
- **Consumer Layer (나중)**: 승인된 버전 고정 스킬만 독립 소비/반출. 고객 결제·고객별 코드 처리·대외 API는 별도 인증·법적 사용권·사업 인수 이후.

## 로컬 PC 자원 보호 설계 — 기술 요구사항

중요: 현재 P10의 3-worker 제한/180초 timeout은 **PC CPU·RAM 사용량을 강제로 제한하지 않는다**. 낮은 프로세스 우선순위만으로도 상한을 보장하지 않는다.

- 저부하 모드는 기본값 OFFLINE_TEST_ONLY; 기존 P10 경량 job은 변경하지 않는다.
- **신규 고부하 작업만 1개 실행**, 모델/GPU OFF, 외부 생성형 API OFF. 작업자 자신과 자식 프로세스만 UCIE 전용 Windows Job Object로 묶어 진짜 자원 격리. Job Object로 CPU hard cap/가중치 및 process/job memory limit 가능하나 구현·자체 Windows 회귀 시험 전에는 기능이 존재한다고 주장하지 않는다.
- 초기 제안 CPU 사용량 상한 10% of host 총 CPU time(개발 실험 가정), 작업 메모리 상한 min(2GiB, 실제 호스트 총 RAM 10%)부터 시험. 현재 RAM 불명이라 설치 정책을 즉시 강제하지 않는다. 스로틀 계측 및 정상 작업 지연 비교 후 값 조정.
- 전체 PC CPU 총 사용률이 75% 초과 또는 실제 가용 RAM이 25% 미만인 상태가 3회 연속 관측되면 **신규 고부하 잡만 PENDING**. 전체 시스템 수치만 확인한다. 외부 프로젝트 이름·코드·로그·프로세스를 상세 조회하지 않는다. 계측 불가 시 새 고부하 잡은 시작하지 않는다.
- 기존 hourly/P10 안전 작업·사용자 입력 반응·기존 DB와 원장 우선. job이 중단되어도 임대·원장 일관성 및 다시 시작 검증. CPU quota와 PENDING 구동을 구분한다.
- Windows 공식 자료: https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_cpu_rate_control_information ; https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information
- PC 온도, 스토리지 쓰기/온디바이스 원본 보존, 부하 급상승은 차기 보조 지표. 원장 수정/기존 예약작업 변경 없음.

## 단계별 구현, 인수 기준, 소유

| 단계 | 개발 노력 참고(전담 2~3명 가정) | 실제 할 일 | FAIL-CLOSED 인수 기준 | 다음 작업 담당 |
| --- | --- | --- | --- | --- |
| A. Owner-host 사전관측 | 착수 직후 수일 | 운영 UCIE 원장/예약작업 영수증, Python 경로/CPU-RAM-디스크 총량, 로컬 소스 SHA·수정 파일 안전 검사 | 운영 원본 쓰기0, 기존 사용자 dirty 파일 보호, 현재 호스트 PASS 근거 명시 | UCIE 통합개발방 + owner Windows |
| B. 신규 배치 CI/자원 보호 | 1~2주 | PR #173 3/4 CI 이슈 원인 분리 및 해결, 새 고부하 워커 1 슬롯·Windows Job Object/모니터 가드, 독립 temp 테스트 | exact-SHA Windows/Linux Python 3.13/3.15 CI 4/4; CPU/메모리 제한 증거; blocked A가 B에 영향 없음 | UCIE 통합개발방 |
| C. 자동 후보 가치 평가 | 착수 후 2~6주 | 소스 고정·중복/변경·관련 버전·재검증 가치/비용 추정, NOT_VERIFIED 후보 원장 | 새 출처0, 고객 비공개 소스0, 위조/중복 입력 거부, 미검증을 PASS로 승격0 | UCIE 통합개발방 |
| D. 실제 SkillBook 제작 | 착수 후 6~16주 | 제한 분야 기술서적의 실제 본문과 재사용 모듈, 긍정/부정 시험, 로컬 추론 필요성 분리 판정 | **실제 스킬서적 1권+단독 기술 모듈 1개** 독립 재현; 출처/버전/라이선스/오류율 기록 | UCIE 통합개발방 |
| E. 지속 개선·원가 | 착수 후 12~20주 | 변경 의존성 기반 증분 재시험, 폐기, 리비전 기록, 주간 CPU/시간/실효성 측정 | 수동 대량 검토 가정 없이 국소 재실행, 인덱스/원장 불변성, 온디바이스 부하 수치 | UCIE 통합개발방 |
| F. 별도 유료 파일럿 | 내부 품질·권리 인수 이후 | 테넌트 분리, 권리 계약, 자원 과금, 외부 API·인증·복구, 구매 실증 | 고객 동의/소유권 증거, 유료 계약, 외부 품질·보안·법적 GO | UCIE사업방 + 별도 운영 승인 |

이 기간은 특정 작업반의 확정 납기 또는 자동 완성 약속이 아니라 **개발 인력 규모를 가정한 계획 시나리오**이다. 로컬 단독 개발 시 더 길어질 수 있다.

## 현 PC 안전한 READ-ONLY 사전 점검 — 실행 요청이 아님

실제 Windows 작업은 소유자가 원격 연결을 복구하거나 로컬에서 명시적으로 실행할 때만 관측한다. 아래 명령은 다른 프로젝트 파일을 건드리지 않도록 UCIE/전체 OS 기본 메모리 수치만 대상으로 한다. UCIE 파일 설치/수정, scheduler 등록, DB migration, broad git reset/pull, 임의 자동 학습 활성화 금지.

~~~powershell
$ucie='D:\UCIE'
$py=Join-Path $ucie '.venv\Scripts\python.exe'
[pscustomobject]@{
    PythonPresent = Test-Path $py
    SourcePresent = Test-Path (Join-Path $ucie 'src\ucie_miner\runtime_pipeline.py')
    HourlyProofPresent = Test-Path (Join-Path $ucie 'scripts\ucie_library_hourly_proof_v12.ps1')
}
Get-CimInstance Win32_Processor | Select-Object NumberOfCores,NumberOfLogicalProcessors
Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory
Get-ScheduledTask -TaskName 'UCIE-PublicMiner-Hourly','UCIE-Internal-Minute' -ErrorAction SilentlyContinue | Select-Object TaskName,State
if(Test-Path (Join-Path $ucie 'scripts\ucie_library_hourly_proof_v12.ps1')) {
  & (Join-Path $ucie 'scripts\ucie_library_hourly_proof_v12.ps1')
}
~~~

실제 작업이 설계와 다르면 **새 작업 설치 금지**. 이전에 보호된 UCIE tracked dirty files를 검증 없이 덮어쓰지 않는다. 실제 작업 스케줄러 상태는 최근 실행 성공 영수증+OS TaskScheduler 이벤트를 같이 확인한다.

## 이번 PR #173 Windows/Python 3.15 CI 장애

- CI exact head b43f858fc135443e78c1efd5f688243fb0b02279, job https://github.com/tmdrkdtn1-project/UCIE/actions/runs/41373579920/job/125048973305
- 4개 matrix 중 Ubuntu 3.13, Ubuntu 3.15, Windows 3.13 성공; Windows 3.15 실패.
- 구체적인 실패는 test_ucie_release_review_v11.UcieOfficialPublicReleaseTests.test_live_local_ui_links_and_strict_get_only 에서 localhost POST의 ConnectionAbortedError WinError 10053. **스킬서적 batch 신규 테스트가 실패했다고 관측한 것은 아니며**, 전체 CI는 미통과 상태. 해당 테스트/Windows 환경 문제를 재현·수정 후 exact head 전체 재검증 필수.
- 이 PR을 로컬 운영에 연결하거나 병합했다고 보고하지 않는다.

## 비용과 확장 기준

- 로컬 기존 PC CPU/GPU는 클라우드 시간당 사용료가 청구되지 않는다. 실비는 추가 전력, 장비·SSD 수명, 백업, 장애/개발 관리와 경우에 따라 외부 AI/클라우드. **GPU·유료 AI API가 실제로 필요한지 측정 전 구매 금지.**
- 이전 9,070건/초 등 숫자는 synthetic/부분 mock 메타데이터 실험, 실제 Windows/제품의 semantic SkillBook 처리량이 아니다. 10만 고객용 서버 용량 확정에 사용하지 않는다.
- 첫 달은 UCIE 내부 합성 공개 metadata 100/1000/10000건 단계별 정확성·wall-time·CPU sec/건·메모리 peak·처리 실패율·서적 품질·유지비를 직접 계측한다.
- 수집량보다 **검증된 신규 내용 1건당 엔진 시간**, 재사용률, 개정으로 재시험한 기술 수, 정확도·신뢰도, 기존 PC의 다른 작업에 미치는 전역 자원 영향이 중요하다.
- 스킬서적 의미적 품질이 템플릿으로 충분하지 않으면 우선 시간제 GPU나 격리된 로컬 모델을 연구하는 별도 제안만 제출한다; 무단 네트워크/모델 학습 불가.

## 운영 권한/격리

- 이 문서·PR은 계획만 기록한다. 운영 Task 등록, 소유자 marker 변경, 모델 추론 도입, 새 public source 활성화, 자동 승인/서명/배포는 수행하지 않는다.
- 실험의 대상 자료는 UCIE가 직접 만든 합성 입력 또는 기존 허용 공개 기술 메타데이터만. 다른 사용자 관련 프로젝트·파일·연결앱·대화·텔레메트리 접근/자료 공유 금지.
- 공개 자료도 임의 원본 대량 재배포·외부 코드 실행·Prompt injection 수용 금지. 출처·권리·버전/수용 근거 없는 기술은 UNVERIFIED 또는 HOLD.
- 고객 의뢰 결과가 공용 UCIE 자산이 되려면 별도의 고객별 데이터 소유/명시적 opt-in/소스 권한 정책이 필요. 현행 UCIE에는 경로가 없고 이 계획은 이를 자동 허가하지 않는다.

## 최종 Gate

- **GO NOW:** 저장소 기반 UCIE-only 개발, 격리 테스트, 허용 공개 source metadata의 읽기 전용 분석.
- **GO ONLY AFTER LOCAL PROOF:** owner Windows 로컬 기존 작업의 최근 영수증·리소스 기준 확인 후 low-load 신규 실험.
- **HOLD:** PR173 CI 4/4 통과 및 exact-SHA 안전 인수가 없는 자동 배치 연결.
- **NO_GO:** 실제 검증 없는 자동 SkillBook 승인/반출, 무제한 고객 작업, 고객 코드의 전역 학습/축적, 로컬 GPU 설치/구매, 신규 스케줄러.

다음 담당: **UCIE 통합개발방** — 실PC preflight 결과 확인, PR #173 CI 문제 분리, 저부하 Job Object 보호, 실제 SkillBook 1권 실증. **UCIE사업방** — 비용·고객 지불 검증, 권리/고객 기여 정책은 후속 정식 검토.
