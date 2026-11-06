# UCIE V1 — 편집 개정 영향·근거 원장·재시험 인수 연결

**날짜 2026-11-06 · UCIE ONLY · 코드/단일 파일 실제 Windows 시험 확인 · 출시 NO_GO**

## 기능 목적

기존 2권 Python/Git SkillBook 및 5챕터 편집 원리는 이미 있지만, 사람이 수정한 차기 초안의 변경 챕터·출처·실패 조건을 과거 검토 원장과 비교해 **무엇을 다시 검증할지** 인수 경로가 없었다. 이번 기능은 기존 편집기 파일을 바꾸지 않고, 별도의 좁은 UCIE 전용 모듈 `src/ucie_miner/skillbook_revision_review_v01.py`를 기존 W04 로컬 도서관 `src/ucie_miner/skillbook_catalog_union_v01.py`에 연결한다.

실제 사용자 워크플로:

1. 기존 `compose_curated_two_book_pilot()`이 만드는 승인 전 원본 편집 `authoring_input`을 `previous`로 보관한다.
2. 수정한 `candidate`에도 5개의 사람 작성 챕터와 원래의 W01 승인 공개 근거를 넣는다. `previous_revision`은 기존 실제 초안 SHA와 정확히 같게 하고, `draft_version`을 명시적으로 수정한다. **이 입력은 기술 사실 증명이 아니라 편집자 주장**이다.
3. UCIE 전용 폴더 `D:\UCIE\runtime\skillbook_manual_review`의 **정확한 고정 이름** `editorial_revision_pair_v01.json`에 JSON 객체 `{"previous": <기존 authoring_input>, "candidate": <새 authoring_input>}` 형태로 저장한다. 서로 다른 프로젝트·사용자 개인 자료는 입력하지 않는다. 운영 DB, SkillBook 제품 원본, 기존 작업 파일을 수정하지 않는다.
4. 아래 실행 옵션으로 검토 전용 원고를 **명시적으로 선택**한다. 이 옵션이 없으면 기존 통합 도서관 동작은 변경되지 않는다.

```powershell
Set-Location D:\UCIE
& .\.venv\Scripts\python.exe -m ucie_miner.skillbook_catalog_union_v01 --port 0 --revision-review-file
```

5. 도서관이 출력한 127.0.0.1 주소 `/catalog`에서 새 편집 후보를 검색해 선택한다. `/catalog/review?id=<정확한초안SHA>` 및 `/catalog/review.json?id=<동일SHA>`에 **개정 영향과 필요한 재시험**이 표시된다.

## 입력·출력과 차단 기준

- **입력 정책:** D:/UCIE 루트와 그 내부 `runtime/skillbook_manual_review/editorial_revision_pair_v01.json`만, 명시적 `--revision-review-file` 입력, symlink/탈출 차단, 파일 최대 48KB, UTF-8 JSON 중복 키 거부, 정확 previous/candidate 키만 수용. 모든 개별 입력은 기존 `compile_review_draft`를 거쳐 다시 검증한다.
- **실제 선행조건:** 부모 초안 SHA, 동일 주제, 새로운 초안의 정확 연결, 미승인 원고·W01 승인된 출처 범위가 성립해야 한다. 비교 자료가 누락되면 `PREVIOUS_REVISION_NOT_SUPPLIED_REVIEW_BLOCKED`; 거짓 부모/위조된 필드/원장 손상이면 FAIL_CLOSED.
- **영향 분석:** 변경 5챕터 목록, 출처 추가/삭제, 기계 계약 차이, 버전 변화, 원본 검토 원장의 출처별 최근 상태를 연결한다. 출처 변경/기술 검토 이력 없음/불일치는 관련 챕터를 재검토 대상으로 지정하고, 원본 출처 제거가 있으면 5개 챕터 전체를 다시 보게 한다.
- **회귀 계획:** 기존 UCIE 대상 제품·Git porcelain·편집·W09 출시 게이트의 실파일 이름을 반환하며 `execution_status=NOT_RUN_BY_REVISION_ASSESSMENT`. 분석이 아무 시험도 직접 실행하지 않는다.
- **사람 인수:** 출처 원본·기술 본문·부정 시험·보안·사용권·개정 또는 철회 승인의 독립 검토 항목을 함께 반환한다. 원장 이벤트는 작성하지 않으며 `owner_approval_granted=false`, `withdrawal_executed=false`, `running_skill_mutated=false`, `export_allowed=false`.
- **기존 SHA-연결 검토 원장:** `skillbook_review_events_v01.jsonl`을 가상도서관 시작 시 읽기 전용으로 사용. 이는 자체 생성할 수 있는 **미서명 검토 권고의 이력**으로 제3자 진위 인증/사용자 승인 원장 또는 외부 배포 서명 증거가 아니다. 사용자가 추후 합법적으로 승인하기 전엔 기술을 자동 개정·철회하지 않는다.

## 실제 시험과 환경 경계

- 신규 `tests/test_ucie_skillbook_revision_impact_v01.py` **7/7 PASS**: 변경 챕터/계약, 서로 다른 버전 부모, 해시 불일치 원장 영향, 재시험 미실행, 수정·승인 없음, 실제 로컬 HTTP 상세와 JSON.
- 신규 `tests/test_ucie_revision_pair_loader_v01.py` **7/7 PASS**: 실제 고정 입력 파일을 통한 로더, 추가/중복 JSON 키·거짓 승인·부모 SHA·symlink 차단, 명시적 CLI 로딩, 실제 W04 로컬 HTTP 검색/상세/JSON.
- 기존 출시 관련 15개 시험 파일을 함께 재실행하여 **총 17개 파일, 185/185 소유자 Windows 대상 자체 시험 PASS**. 정확 최신 GitHub Actions 4개 환경의 결과는 최종 HEAD에서 별도 확인. 이 자체 시험은 독립 3자 검증·실사용 보안 인수 또는 출시 승인이 아니다.
- **호스트 충돌 보존:** 기존 `skillbook_editorial_production_v01.py` 소유자 로컬 SHA가 원격 HEAD의 이전 내용과 다르므로 덮어쓰지 않았다. GitHub에서 편집기 수정 시도도 **이전 exact Git blob로 복원**했다. 신규 좁은 `skillbook_revision_review_v01.py`를 별도 추가해 기존 편집기를 import하고 W04에 연결한다. 기존 소유자 추적 수정 15파일 유지, DB/수집기/스케줄/C40/타 프로젝트 접근/공개 배포 변경 없음.

## 남은 실제 출시 인수

버전별 공식 소스의 독립 인증과 기술 사실 QA, 원본·반례·효과 비교를 마친 뒤 검토자/소유자 승인 및 서명된 개정·철회 이력을 구성해야 한다. 이 분석기는 검토 대상을 정확히 안내하지만 사람의 결정을 대신하지 않는다. PR은 Draft/미병합, 6단계 마지막 06=NO_GO.
