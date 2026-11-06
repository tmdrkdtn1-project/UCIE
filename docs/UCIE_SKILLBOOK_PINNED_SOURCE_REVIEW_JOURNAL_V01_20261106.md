# UCIE V1 — 버전 고정 공식 근거 검증과 수동 개정·철회 검토 원장

**2026-11-06 · UCIE ONLY · 실제 코드/소유자 Windows 자체 시험 · 제품 출시 NO_GO**

## 실제 개선된 제품 경로

기존 SkillBook 001·002에 이미 고정된 공식 Python/Git 태그와 해당 소스 파일을 검증한다. 이 모듈은 **원문 RST/AsciiDoc 바이트의 SHA-256 + Git `blob <size>\0` SHA-1** 두 값을 각각 기존 원본 기록과 비교한다. 버전이 바뀌는 HTML 페이지의 SHA를 잘못 비교하지 않는다. 한 글자라도 다른 원문이면 **재검증·출시 보류 후보**로 남기고 자동 철회·승격·배포하지 않는다.

**입력 자산은 오직 기존 승인 공개 근거 2개**다.

| 기존 승인 저장소/태그 | 검증할 원본 파일 | UCIE 전용 임시 검토함 파일명 |
|---|---|---|
| `python/cpython` `v3.15.0` | `Doc/library/os.rst` | `python_cpython_v3_15_0_os.rst` |
| `git/git` `v2.51.0` | `Documentation/git-status.adoc` | `git_git_v2_51_0_git-status.adoc` |

원본은 소유자 프로젝트 `D:\UCIE\runtime\skillbook_manual_review\`에서 **정확 파일명**의 일반 파일만 읽을 수 있다. 심볼릭 링크, 다른 프로젝트, 사용자 임의 입력 경로, 거짓 출처, 512KB 이상 입력은 차단한다. GitHub API·웹사이트 자동 조회 기능 없음. 특정 태그 원본을 소유자가 **명시적으로 준비한 경우에만** 검증한다.

### 수동으로 한 파일 검증 (쓰기 없음)

아래 예시는 승인 저장소 한 파일의 *원문을 확인 목적*으로 UCIE 전용 검토함에 저장한다. 해당 자료의 원본 대량 재배포나 타 프로젝트 공유는 하지 않는다. 현재 진행 중인 기존 공개 마이너 스케줄과 무관하다.

```powershell
Set-Location D:\UCIE
New-Item -ItemType Directory -Force .\runtime\skillbook_manual_review | Out-Null
$u = 'https://raw.githubusercontent.com/python/cpython/v3.15.0/Doc/library/os.rst'
Invoke-WebRequest -Uri $u -OutFile '.\runtime\skillbook_manual_review\python_cpython_v3_15_0_os.rst'
& .\.venv\Scripts\python.exe -m ucie_miner.skillbook_pinned_source_review_v01 --source doc:python/cpython
```

출력 `PINNED_SOURCE_FILE_DIGESTS_MATCH_ORIGIN_REVIEW_PENDING`이면 **해당 입력 원본 바이트가 기존 버전 고정 두 해시와 일치**함을 의미한다. 출처 신원·태그 서명·기술 사실·라이선스·외부 QA가 검증된 것은 아니다. `...DIFFER_REVALIDATION_REQUIRED`이면 입력 파일·태그·출처를 수동 재확인해야 한다. 정상 소스 파일 자체를 수정하거나 해당 SkillBook을 자동 철회하지 않는다.

### 소유자 선택: UCIE 전용 검토 원장에 기록

```powershell
Set-Location D:\UCIE
& .\.venv\Scripts\python.exe -m ucie_miner.skillbook_pinned_source_review_v01 --source doc:python/cpython --record-review --confirm-review-write
```

명시된 두 옵션이 모두 있어야만 `runtime\skillbook_manual_review\skillbook_review_events_v01.jsonl`에 **검토 권고 이벤트**를 추가한다. 이전 기록과 같으면 새로 중복하지 않는다. 원장 이벤트는 차례·이전 항목 SHA·현 항목 SHA를 연결하고 불완전 파일, 내용/순서 변경을 검사한다. 단독 해시 체인은 서명·공증이 아니며 관리자가 전체 파일과 해시를 다시 작성하는 공격까지 막는 증거는 **아니다**.

원장 쓰기는 UCIE 전용 경로에서만 별도 명시 승인 후 진행된다. Windows에서 실제 절대 경로 `D:\UCIE` 이외의 이름만 같은 `UCIE` 폴더로는 실행하지 않는다. 원자적 파일 교체·잠금·제한된 크기(128개 이벤트/128KiB)로 기존 운영 SQLite 원장과 분리한다. 사용자 파일·비밀정보·다른 프로젝트는 읽지 않고 수동 검토 내용에 개인정보를 넣지 않는다.

### 기존 가상도서관에서 읽기

```powershell
Set-Location D:\UCIE
& .\.venv\Scripts\python.exe -m ucie_miner.skillbook_catalog_union_v01 --port 0
```

반환되는 로컬 `/catalog` 화면에서 SkillBook 검토 후보를 클릭한다. 서버는 시작할 때 **UCIE 검토 원장만 읽기 전용으로 한 번 확인**하고, 검토 이벤트가 있으면 아래 상태를 별도 표시한다.

- `NO_MATCHING_PINNED_REVIEW_EVENT`: 해당 원본 검토 기록 없음
- `PINNED_RAW_SOURCE_HASHES_MATCH_UNAUTHENTICATED`: 버전 고정 원본 해시 일치·출처 신원 및 QA 미검증
- `PINNED_RAW_SOURCE_MISMATCH_REVIEW_REQUIRED`: 해당 태그 원본 검증 불일치·재검토 필요·자동 철회 없음

`/catalog/review.json` 기계 조회도 동일 상태를 포함한다. GET은 네트워크 조회·파일 쓰기·자동 기술 검증을 시작하지 않는다. **기록 변경 후 화면을 갱신하려면 로컬 도서관을 새로 실행**해야 한다. 원장 변조·손상·알 수 없는 상태면 서버 시작 또는 검토 후보 조회를 FAIL_CLOSED 처리한다.

## 시험·승인 구분

- 새 원본 검증/분리 원장 단일 파일 시험 **14/14 PASS**: Git blob 헤더 포함 SHA-1 예제, SHA-256·2개 기존 소스 메타데이터·유효하지 않은 입력, 원장 기록·재실행 중복 차단·변조/원자적 저장·소유자 D:\UCIE 경로 제한
- 가상도서관 HTTP 원장 통합 **6/6 PASS**: 검색/상세/JSON, 재검증·기록 없음 구분, GET에서 원문·원장 쓰기 없음, 손상 원장 차단
- 그 밖의 이전 원리/SkillBook/공식 HTML 관측/W09 출시 차단 등 기존 관련 테스트는 별도 실행 결과로 관리. 실제 승인 공식 저장소 태그 파일의 SHA는 이전 작업에서 공개 저장소 바이트로 각각 재계산해 일치 확인했으나 **이번 소유자 Windows 검증 모듈의 정식 태그 원본 다운로드·원장 실제 커밋은 수행하지 않았다**. 새 검증 알고리즘의 호스트 테스트는 합성 입력 기반이다.

**리뷰 상태 및 권리**: 출력의 matched 값은 사전에 작성한 해시와 입력 파일의 내용 일치 확인이다. 파일을 누가 어디서 받아왔는지에 대한 독립 인증, 공식 태그 전자서명, 기술 주장의 실효성, 전문가 승인, 라이선스·보안·서명·외부 배포 등은 별도 근거가 있어야 한다. 모든 자동 승격·실제 철회·서명·공개 출시 플래그는 false. 운영 공개 마이너 DB, TaskScheduler/C40, Rulepack 원장은 변경하지 않는다.

**로드맵 1~6**: 01 PARTIAL(같은 바이트 대상의 버전 고정 검증 API가 생김; 독립 신원/전문가 QA 미완), 02 PARTIAL(가상도서관에서 원장 상태 표시), 03 PARTIAL(외부 승인 패키징 미완), 04 PARTIAL(자체 QA 수행·독립 QA/실사용 비교 미완), **05 PARTIAL(검토 이벤트의 격리된 영구 원장/중복·무결성 검사와 UI 연결 구현; 실제 승인형 개정·철회는 미완)**, **06 NO_GO**(운영 안정·보안/권리/독립인수·서명/출시 승인 미완).
