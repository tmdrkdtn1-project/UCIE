# UCIE V1 — 공식 태그 원본 1회 실검증 → 격리 검토 원장 → 가상도서관 인수

**2026-11-06 · PROJECT=UCIE ONLY · 구현/자체 시험 완료 · 소유자 PC 실제 공개 HTTPS 요청 및 운영 원장 영수증은 아직 없음 · 출시 NO_GO**

## 해결한 제품 통합 결손

기존 UCIE에는 SkillBook 001 Python 및 SkillBook 002 Git의 `tag/source_file/source_sha256/git_blob_sha1`이 고정되어 있었으나, 소유자 PC에서 두 파일 중 하나를 다시 받아 검증하고, 수동 검토 권고를 별도 원장에 기록하고, 가상도서관 상세에 반영되었는지 확인하는 **한 번의 수동 인수 호출**이 없었다. 이전 HTML 대 RST 해시 비교 오류의 재발을 방지하기 위해 **GitHub의 콘텐츠 주소형 Git blob API**를 사용하고 기존 공개 저장소만 다룬다.

## 실제 코드와 검증 범위

- 신규 파일 `src/ucie_miner/skillbook_owner_pinned_acceptance_v01.py`의 `accept_one_exact_source()`와 CLI. 기존 `skillbook_pinned_source_review_v01.py`, `skillbook_catalog_union_v01.py`에 연결할 뿐 신규 크롤러·출처 자동 확장·비공개 시스템 접근을 추가하지 않는다.
- 허용 ID는 **정확히 `doc:python/cpython` 및 `doc:git/git` 두 기존 SkillBook**. URI는 소유자 입력에서 받지 않고 기존 고정 publisher + `source_document_git_blob_sha1`로 구성한 `https://api.github.com/repos/{approved-repo}/git/blobs/{fixed-blob-sha}`만 허용. Python v3.15.0 `Doc/library/os.rst` 및 Git v2.51.0 `Documentation/git-status.adoc` 원본 Git blob SHA에 대응한다.
- 명시적 `--confirm-network` 없이는 네트워크를 시작하지 않는다. HTTPS GET 1회(응답 제한 900KB/15초), 리다이렉트·비JSON·압축·인코딩/길이/경로 불일치·Base64·중복 JSON 키·Git blob SHA 차이를 거부. 본문 원문 최대 512KiB를 메모리에서만 디코딩해 기존 파일 **SHA-256 + Git blob SHA-1**과 둘 다 대조하고, 실제 일치하지 않으면 기록 전 FAIL_CLOSED.
- API 결과는 원본 HTML이 아니라 **버전 고정 소스 파일의 raw bytes**이다. URL은 고정 blob 내용을 지정하지만, upstream Git 태그 서명/소유권·작성 내용 사실·권리 검토가 완료됐다는 증거는 아니다.
- 원본 바이트는 출력·디스크 보관·재배포하지 않는다. 응답에는 크기·조회 시각·source ID/tag/path·두 SHA·결과만 포함하며 owner/rights/security/QA 승인, 서명·외부 반출·자동 승격·실제 철회는 모두 false.
- 별도 동의 `--record-review --confirm-review-write`가 **모두** 있어야 UCIE 전용 `D:\UCIE\runtime\skillbook_manual_review\skillbook_review_events_v01.jsonl`에 해당 출처의 미승인 검토 권고 1건을 기록할 수 있다. 먼저 현재 UCIE 원장과 **가상도서관 연결을 메모리에서 사전검증**하여 잘못된 참조일 때 원장 쓰기 전 차단한다. 기록 후 실제 원장 해시 체인과 동일 이벤트의 W04 표시를 재조회하고 일치 여부를 반환한다. 이 원장은 미서명·자체 작성 가능하며 법적/기술 인수 영수증으로 격상하지 않는다.

## 소유자 PC의 수동 인수 명령

먼저 **조회·검증만** 하는 읽기 전용 명령:

```powershell
Set-Location D:\UCIE
& .\.venv\Scripts\python.exe -m ucie_miner.skillbook_owner_pinned_acceptance_v01 --source doc:python/cpython --confirm-network
```

검증 결과를 확인한 후 소유자가 **격리 원장 기록까지 명시적으로 선택한 경우에만**:

```powershell
Set-Location D:\UCIE
& .\.venv\Scripts\python.exe -m ucie_miner.skillbook_owner_pinned_acceptance_v01 --source doc:python/cpython --confirm-network --record-review --confirm-review-write
```

Git 원본 선택 시 `--source doc:git/git`로 교체할 수 있다. 한 호출에서 source 하나만 조회·검증한다. 실행 환경의 인증된 사용자와 권한을 독립 증명하지 않으며, GitHub API 가용성·접속 정책·레이트리밋에 따라 네트워크가 실패하면 거부한다. 실제 소유자 D:\UCIE 이외의 Windows 디렉터리에서는 FAIL_CLOSED. 운영 원장, 수집기, TaskScheduler, C40, 외부 프로젝트는 사용하지 않는다.

성공 판정의 예시는 `RAW_PUBLIC_GIT_BLOB_MATCHES_PIN_NOT_RELEASE_APPROVED` (네트워크 공개 원본만 검증), 소유자 원장 승인 사용 시 `SOURCE_VERIFIED_REVIEW_JOURNAL_AND_W04_LINKED_NOT_APPROVED`. 둘 모두 **외부 QA·출시/배포 NO_GO**. 원장 기록 성공 시 `review_journal_total_events`, `review_event_id`, `catalog_reference_checked=true`, `catalog_source_status=PINNED_RAW_SOURCE_HASHES_MATCH_UNAUTHENTICATED`를 반환한다. 원래의 가상도서관 서버는 다음 시작 시 해당 원장을 읽기 전용으로 표시한다.

## 시험 근거와 구분

- 신규 `tests/test_ucie_skillbook_owner_pinned_acceptance_v01.py`: 합성 Base64 응답·가짜 정확 공개 주소, 요청 opt-in 분리, MIME/redirect/byte budget/불법 JSON·위조 경로 거부, 잘못된 바이트 해시 차단, 원장 안전 선검사·중복 기록 억제, W04 후검사. 모든 HTTP 요청은 모의 응답이며 실제 Github 네트워크는 실행하지 않는다.
- 소유자 Windows 해당 신규 시험 **15/15 PASS**, 기존 다른 17개 관련 파일 시험까지 합계 **18개 파일 201/201 PASS**. 별도 정확 PR HEAD GitHub Actions Windows/Ubuntu Python3.13/3.15 성공 여부는 최신 실행을 별도 확인해야 한다.
- 이전 작업에서 공개 `python/cpython` v3.15.0 `os.rst` **221,596바이트** 및 공개 `git/git` v2.51.0 `git-status.adoc` **20,380바이트**를 GitHub connector로 직접 읽어 기존 SHA256과 일치함을 확인한 적은 있다. 하지만 **이번 새 content-addressed API URL의 실네트워크 GET은 소유자 Windows에서 아직 수행하지 않았다**. 실제 원장 기록 0건(이번 개발에서 운영 원장 쓰지 않음). 공개 GitHub API가 코드에 따라 작동하는지 실제 소유자 실행 전까지 LIVE PASS로 표시하지 않는다.

**다음 출시 장벽:** 위 명령을 소유자가 실행한 실제 1건의 source+journal+catalog 영수증, 문서 원문 근거의 사람 기술/보안·라이선스 검토, 독립 QA 및 실제 사용성·효과 비교, 기존 PR #182의 코드 검토·통합/서명과 운영 collector 안정성 확인.

**1~6 단계:** 01 PARTIAL(동일 source byte 검증+기술서적 생산 경로 연결), 02 PARTIAL(기존 W04 연동), 03 PARTIAL(배포 승인/서명 미완), 04 PARTIAL(자체 테스트/CI; 외부 QA 미완), 05 PARTIAL(기술 변경 이력과 1회 실원본 검증 연결 실행 경로, 실제 owner 영수증 미완), 06 NO_GO.
