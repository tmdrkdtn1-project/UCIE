# UCIE P11: 공개 근거 증분 수집 ↔ 자체 실험 경험 ↔ 다음 실행 개선 (2026-10-28)

## 기존 운영 상태·승인 범위

사용자 실제 호스트: P10 `UCIE-Internal-Minute` PT1M Windows Task 활성화, 2회 연속 TaskResult=0, 큐 5/5 `SUCCEEDED`. 기존 `UCIE-PublicMiner-Hourly`는 별도 시간당 수집기. **P11 활성화 전에는 1분 P10이 기존 5종만 실행한다.**

P11은 기존 P10 Worker·비차단 `PENDING` 재시도 엔진을 재사용하면서, 소유자 UCIE 프로젝트 내부의 소스-기반 경험 축적 기능 2종을 **명시적 opt-in 후에만** 추가한다. 타 프로젝트 연결·개인 저장소·비공개 코드·원본 패치·외부 도구 자동 설치/코드 실행/모델 가중치 훈련/Rulepack 서명/배포/규칙 자동 승격 금지.

## 연결 단계

1. **증분 공개 수집 (`PUBLIC_INCREMENTAL_MINING`)**: 5분마다 최대 **1 익명 GitHub API GET**. 승인된 다섯 저장소 `python/cpython`, `PowerShell/PowerShell`, `git/git`, `modelcontextprotocol/python-sdk`, `actions/runner-images`를 정확하게 순환. 개별 저장소는 전체 순회 조건에서 최소 약 25분마다 점검. 기존 수집기의 동일 API 예산을 침해하지 않도록 5곳을 5분마다 한꺼번에 호출하지 않는다. 429/403/타임아웃 시 source cursor를 이동하지 않고 마지막 시도 시각을 남겨 최소 5분 호출 간격을 유지. 실패한 worker만 PENDING으로 가고 다른 P10 작업은 진행한다.
2. **원천 검증 및 격리**: 기존 `public_discovery.discover_public_leads`의 merge 시간, 정확한 승인 출처, canonical URL, SHA, 카테고리 검증을 재사용. 신뢰되지 않는 title은 **SHA256만** 기록하고 raw PR/코드/HTML은 저장하지 않는다. 후보는 `UNVERIFIED_PUBLIC_LEAD`일 뿐, 승인된 오류 패턴이나 실사용 기술이 아니다. 별도 UCIE SQLite `runtime/ucie_p11_public_experience.sqlite3`에 출처-PR 중복키 및 bounded 2,400행으로 저장. 기존 `runtime/public_miner.sqlite3`, Stage 10~16, P8 experience 등은 변경하지 않는다.
3. **경험 연결 (`EXPERIENCE_CLOSED_LOOP`)**: 10분마다 **신규 미실험 후보 1개**를 선택해 고정된 UCIE 자체 합성 알고리즘만 시험. 보안/크래시/회귀/호환성/시험 태그를 3개 허용된 첫-party 실험 유형에 매핑하고, 기존 `evaluate_ucie_owned_recipe`의 baseline/candidate 정확 동치성과 연산 수를 비교. 소스 ID, PR 번호, 검증된 SHA, 실험 증거 SHA, 부정/긍정 가설, 유한 작업량을 별도 원장에 기록. **앞선 실험에서 정확히 일치했던 결과 수에 따라 다음 workload를 128→256→512로 조정**하므로 다음 실험이 기록을 재사용한다. 실사용 코드나 기존 알고리즘을 자동 바꾸는 것은 아님.
4. **비차단/실패 격리**: 기존 P10 최대 3 독립 프로세스, 15초 heartbeat, 180초 supervisor timeout, 오류별 PENDING/retry를 유지. 원장이 가득 차거나 검증에 실패하면 해당 P11 작업만 fail closed. 기존 5종 P10 내부 처리는 계속한다.

## 운영 주기 및 제한

| 작업 | 주기 | API GET |
|---|---:|---:|
| 기존 P10 Dispatcher | 1분 | 0 |
| P11 공개 수집 (5개 소스 순환) | 5분 | 최대 1 / 실행 |
| P11 검증된 자체 실험 및 경험 저장 | 10분 | 0 |
| 기존 P10 조회·QA·실험·보고 | 기존 1/5/5/15/60분 | 0 |
| 기존 PublicMiner | 기존 60분 | 기존 정책대로 |

P11 익명 GET은 최대 12회/시간(실제 동작 및 P10 타이밍에 따라 감소)이나, **GitHub의 IP 공유 제한은 외부 상태**이므로 실제 rate-limits에 따라 403/429가 발생할 수 있다. 발견된 후보가 없어도 empty cycle은 성공. **매 5분마다 5개 저장소를 모두 확인하는 것은 아님.**

## 명시적 활성화 절차 (소유자 Windows)

기존 P10 OS 작업은 건드리지 않는다. 새로운 스케줄러도 등록하지 않는다. 최신 코드가 `D:\UCIE\src`에 있고 P10이 이미 활성화되어 있다는 전제.

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
$py = 'D:\UCIE\.venv\Scripts\python.exe'

# 먼저 현재 상태만 조회 — P11 미가동이면 P11_NOT_ENABLED_READ_ONLY
& $py -B -m ucie_miner.p11_closed_loop --ucie-root 'D:\UCIE' --status

# 명시적 활성화: P11 전용 격리 SQLite + opt-in, 기존 P10이 다음 1분 tick에서
# 신규 2종을 스케줄링. Windows Task 등록 또는 기존 Task 변경 없음.
& $py -B -m ucie_miner.p11_closed_loop --ucie-root 'D:\UCIE' --activate

# 두 번의 예약 실행 후 결과 확인
& $py -B -m ucie_miner.p11_closed_loop --ucie-root 'D:\UCIE' --status
& $py -B -m ucie_miner.pending_queue --ucie-root 'D:\UCIE'
Get-ScheduledTaskInfo -TaskName 'UCIE-Internal-Minute' |
    Select-Object LastRunTime, NextRunTime, LastTaskResult
```

`--activate`는 주어진 경로를 삭제/덮어쓰지 않고 안전한 신규 marker/DB를 준비한다. 첫 연속 운영까지는 `P11_CODE_AND_SYNTHETIC_TEST_PASS`만 인정하며, **실제 첫 5분 GET 또는 10분 경험 축적은 호스트의 별도 증거가 있어야만 PASS**다.

## 미완성 부분 — 성능과 승인 구분

P11은 첫-party 코드 실험의 **경험 기반 작업량 선택과 소스 기반 실험 결과 축적**을 제공한다. 외부 패치가 실제 문제를 수정했다는 독립 QA가 아니며 실제 모델 학습, 자동 코드/스킬 배포, 운영 알고리즘 자동 승격도 아니다. 장기 저장(2,400행 이후) 정책, 소스별 요청 예산의 실측/동적 조절, owner license/human QA, 실전 장애 회복 확인이 별도 게이트다.

### 인수 항목

신규 `tests/test_ucie_p11_closed_loop.py`: 비활성 무변경, 정확 승인 5소스 순환, 5분당 GET 1회, 429 대기, 잘못된 메타데이터 거부, PR 원문 미저장, 출처 기반 자체 실험/중복 방지, 다음 workload 변경, P10 작업별 PENDING 격리, 기존 시간당 마이너/P8 원장 보호. 기존 P10과 pending queue 회귀 테스트 **동시 수행**, Windows/Linux Python 3.13/3.15 4/4 CI 및 로컬 Windows 시험 전에는 운영 PASS 표시하지 않는다.
