# UCIE — 비차단 자동 처리 대기열 V1: BLOCKED → PENDING, 다른 작업 계속 (2026-10-28)

## 소유자가 확정한 실제 요구

> 자동 스케줄 작업이 막히면 그 작업은 PENDING으로 두고, 다른 작업이 계속 진행돼야 한다.

**1분 주기란 스케줄러가 1분마다 실행 가능한 작업을 확인한다는 뜻**이다. 1분 안에 처리하지 못한 작업을 무조건 죽이거나 PENDING으로 강등하는 뜻이 아니다. 건강하게 실행 중인 작업은 `RUNNING`으로 남아 heartbeat/lease를 연장하고 **다음 다른 작업**은 별도 임대·worker에서 이어서 진행한다.

### 실제 상태 전이

```text
             [PENDING due] ---lease---> [RUNNING]
                  ^                      |      |
                  | blocked/rate limit   |      +---success--> [SUCCEEDED]
                  | retry backoff        |
                  +----------------------+---heartbeat------> [RUNNING]
                  ^
                  +---expired lease(retry budget left; old token fenced)
                                  |
                                  +---max attempts--> [REVIEW_REQUIRED]
```

예시: A가 외부 API rate-limit로 막히면 `PENDING`(retry due 10분 뒤)으로 기록하고 즉시 B를 lease하여 진행. A가 정상적으로 3분 작업 중이라면 `RUNNING`에 그대로 두고 B를 별도로 lease. A가 heartbeat 없이 임대 만료되면 기록된 횟수와 최소 지연에 따라 PENDING/REVIEW_REQUIRED로 넘어감. 오래된 A worker가 나중에 성공을 보고해도 **임대 토큰 불일치**로 commit 거절. DB는 여러 worker가 짧은 트랜잭션으로 job 상태만 수정한다.

## 코드의 실제 제공 범위

신규 `src/ucie_miner/pending_queue.py`:

- UCIE 전용 `runtime/ucie_internal_pending_queue_v1.sqlite3` **독립 DB**; 기존 `public_miner.sqlite3`, Stage10-16 데이터, P8 경험, Serial4/5, hourly scheduler를 변경하지 않는다. DB 생성은 별도 `initialize_queue(root)`를 명시 호출할 때만. **CLI 기본은 읽기 전용**.
- 작업 종류는 정해진 UCIE 자체 단계 5종만 허용: `PUBLIC_METADATA_REVIEW`, `UCIE_LIBRARY_INDEX_CHECK`, `UCIE_FIRST_PARTY_EXPERIMENT`, `UCIE_QA_REVIEW`, `UCIE_REPORT_PREPARATION`. 외부 문자열 명령·파일 경로·任意 스크립트 저장/실행 금지.
- 중복 작업 ID/키 거부, DB 행 제한 1000개, 한 번에 최대 8개만 임대, 트랜잭션 `BEGIN IMMEDIATE`과 짧은 DB 대기(250ms). 스케줄러 callback에서 직접 무거운 실행을 하지 않는다.
- 각 작업의 `PENDING → RUNNING` 임대 토큰(opaque), 기한, heartbeat. 막히면 **이유 코드만** 기록(예: `DEPENDENCY_NOT_READY`, `UPSTREAM_RATE_LIMIT`, `WORKER_TIMEOUT`)하고 60초~60분 이내의 재시도 시각을 지정. 횟수 초과 시 해당 작업만 `REVIEW_REQUIRED`; 다른 작업은 계속.
- 임대 만료 시 스테일 worker의 성공 보고를 막는 **토큰 fencing**, 타임아웃 backoff. 다만 외부 시스템에 이미 발생한 side effect를 자동 취소할 수는 없으므로 **실제 외부 쓰기 작업/승격/서명/배포는 절대 이 V1 queue에 연결하지 않는다**. 향후 production adapter는 별도로 멱등성 및 충돌 회귀 시험이 필요.
- 안전한 합성 실험 `demo_pending_no_head_of_line_block()`은 실제 독립 임시 UCIE SQLite에 작업 A·B를 만들어 A를 BLOCKED→PENDING, B를 같은 1분에 처리→SUCCEEDED. 사용자 기존 원장에는 파일을 만들지 않는다.
- 상태 조회 `inspect_queue(root)`: pending/running/success/review 카운트, 다음 대기 시각·표준 이유 코드. 임대 토큰/비공개 코드 출력 안 함.

### 실제 즉시 확인 가능한 명령

```powershell
$env:PYTHONPATH='D:\UCIE\src'
$py='D:\UCIE\.venv\Scripts\python.exe'

# A가 막혀도 B가 같은 분 안에 진행되는 직접 SQLite 합성 실기
& $py -B -m ucie_miner.pending_queue --demo

# 현재 UCIE 전용 queue 등록 상태 확인, 없다면 QUEUE_NOT_INSTALLED_READ_ONLY
& $py -B -m ucie_miner.pending_queue --ucie-root 'D:\UCIE'
```

**이 명령들은 OS 예약 작업을 설치하거나 public miner를 바꾸지 않는다.** 기존 시간당 수집기는 `scripts/install_hourly_task.ps1`에서 OS `PT1H`로 등록되고 `src/ucie_miner/schedule_policy.py`에서 1시간 cadence/실패 backoff와 단일 인스턴스 잠금을 사용한다. 본 패치는 그 작업을 변경하지 않는다.

### 실제 도입 전 남은 필수 작업

1. 승인된 기존 UCIE worker를 작업 유형별 **독립 프로세스 executor**로 연결하되, 1분 dispatcher는 claim/상태 전환만 수행하도록 한다. 실제 실행 중인 작업 heartbeat, 강제 종료 대신 유한 예산/격리·복구, 종료/성공 commit의 idempotency를 검증한다.
2. 처리 기록의 1000행 한도를 넘는 지속 운전은 **별도 보존·압축·역추적 규약**이 필요하다. 현재는 용량 초과 시 안전하게 enqueue를 거절하고 다른 작업 기록을 손실하지 않는다.
3. 운영 사용 전 예약 작업 간격 변경/신규 Task 등록 여부는 명시적 별도 승인 및 Windows 실호스트 인수 시험이 필요. **1분 scheduler·자동 학습·수집 가동을 했다고 주장 금지.**
4. 수집은 운영 API 한도와 승인된 원본 근거 제한을 준수. 1분 진입 확인과 5분 공개 GET은 독립; 이미 운영 중인 시간당 마이너를 덮어쓰지 않는다.

## 시험 및 인수

신규 `tests/test_ucie_pending_queue.py`: 차단된 A가 PENDING인데 B 성공, 정상 장기 A heartbeat/동시 B 진행, stale 임대 복구/기존 토큰 fencing, 다중 dispatcher에서 한 job 두 번 claim 금지, 작업별 재시도 상한과 HOLD, 원장 격리·권한 밖 경로 거부, 기본 CLI 무변경을 오프라인 시험. GitHub Windows/Ubuntu Python 3.13/3.15 정확 SHA CI를 통과해야 병합. 소유자 PC에서도 **합성 demo**의 실제 실행 결과를 확인하기 전에는 host PASS라고 주장하지 않는다.
