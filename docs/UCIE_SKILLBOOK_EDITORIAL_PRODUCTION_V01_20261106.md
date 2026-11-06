# UCIE 1단계 — SkillBook 공개 근거 편집·검토 생산 계약 V0.1

날짜: 2026-11-06. 상태: **실제 코드 구현 / 검토·출시 NO_GO**.
정본: UCIE_V1_RELEASE_EXECUTION_LOCK_20261105.md.
코드: src/ucie_miner/skillbook_editorial_production_v01.py.
시험: tests/test_ucie_skillbook_editorial_production_v01.py.

## 목적과 정확한 증거 수준

기존 Python SkillBook 001과 Git SkillBook 002는 출처·원리·내용이 고정된 두 사례다. 이번 기능은 W01 Source Registry, W02 LibraryEntry, 기존 SkillBook Blueprint를 **그대로 재사용**하여 다른 승인 공개 출처의 후보도 사람용 챕터와 기계용 설계 계약으로 연결하는 **검토 대기 생산 기능**을 구현한다.

공개 출처 **조사 허용**과 개별 근거의 **실제 SHA·버전·내용 검증**은 서로 다르다. 출처가 등록되어 있어도 사용자가 제출한 digest/버전·기술 본문은 독립 검증되지 않는다. 허위 승인 필드를 주입해도 사용·서명·배포 허가로 승격하지 않는다. 새로운 수집기·외부 프로젝트 접근·모델 학습·코드 실행은 없다.

## 동작하는 API

| 함수 | 실제 결과 | 승인 경계 |
|---|---|---|
| compile_review_draft(record) | 등록된 1~4개 출처, 5개 필수 기술 챕터, 기계 계약, 원장 ID/Blueprint ID, 초안 SHA-256 연결 | 사실 검증·승인 전, 자동 승격 OFF |
| render_review_markdown(draft) | 출처/상태 재계산 후 HTML·Markdown 명령을 무해한 텍스트로 이스케이프한 사람용 검토 문서 | 렌더링이 출처 사실 보증 아님 |
| build_review_handoff(record) | 메모리 내 Markdown/JSON 바이트 및 각각 SHA-256 영수증 | 파일 기록·외부 반출·서명 없음 |
| compare_review_revisions(previous,candidate) | 앞선 초안 SHA 참조, 변경 챕터·근거·계약·버전 식별 | 영구 원장/인증된 검토/권리 승인 아님 |
| compose_curated_two_book_pilot() | 기존 두 UCIE 저작 SkillBook의 공통 원리 5개 챕터를 동일한 일반 편집 계약에 통과시킴 | 새 공식 문서의 자동 검색·재검증 아님 |

### 편집자 입력 형식

정확한 입력 키: topic, draft_version, sources, chapters, machine_contract, previous_revision, revision_note.

- topic: 대문자 기술 토큰. draft_version: 0.1.0-draft 같은 초안 전용 버전.
- sources: 기존 W02가 허용하는 정확히 7개 키(kind/source_id/evidence_reference/evidence_sha256/purpose_code/version_scope/dependencies). 반드시 기존 승인 출처 레지스트리 경로에 대응해야 함. 중복 출처·기타 프로젝트·research-only·임의 URL은 거부.
- chapters: MECHANISM, SAFE_PRECONDITIONS, BOUNDED_APPLICATION, COUNTEREXAMPLES, VERSION_AND_QA_LIMITATIONS **정확 5개**. 각 body는 15~1400자의 단일 단락. 각 source_ids는 등록된 출처만 지칭; 중복·미귀속 출처 차단.
- machine_contract: interface_name/input_contract/output_contract/failure_contract/limits. 구조는 **DESIGN_ONLY_NO_EXECUTABLE**. 실제 callable 구현으로 간주하지 않음.
- previous_revision: 최초 null, 개정 시 전 초안 SHA 주장을 기록. 비교 함수가 메모리 내 이전 초안과 일치 확인하지만 외부 승인 이력을 증명하지는 않음.
- revision_note: 편집 변경 이력.

추가 승인 필드(human_approved, signed, export_allowed 등) 삽입은 입력 자체 차단. 본문은 불신 텍스트로 다루며 외부 명령·프롬프트를 실행하지 않는다. 검토 게이트 7개(문서 SHA/원리/버전·시험/보안/권리/독립 QA/소유자 승인)는 **항상 PENDING**.

### 실제 UCIE 내부 사용 예

~~~python
from ucie_miner.skillbook_editorial_production_v01 import (
    compose_curated_two_book_pilot,
    build_review_handoff,
)
draft = compose_curated_two_book_pilot()
handoff = build_review_handoff(draft["authoring_input"])
assert handoff["receipt"]["draft_sha256"] == draft["draft_sha256"]
assert handoff["receipt"]["export_allowed"] is False
~~~

검토자에게 인계할 두 문서 내용과 SHA 영수증을 메모리로 생성할 뿐 설치·실행·서명·발송은 하지 않는다.

## 실물 시험과 시뮬레이션 구분

- **기존 UCIE 저작 실물 기반**: 공식 Python os.scandir와 Git --porcelain=v1 -z 자료의 이전 기록 SHA 및 UCIE 작성 원리 5챕터를 이용해 기계·사람용 결과 생성.
- **미검증 합성 입력**: PowerShell 공식 문서 라우트 및 modelcontextprotocol/python-sdk의 승인 저장소 PR 경로를 이용해 일반화된 출처 검증 로직 시험. 반복된 a/b/c 형태의 SHA와 PR 번호는 **시험 데이터**이며 공식 문서 원본을 확인한 증거가 아니다. 결과의 source_digest_independently_verified=false 유지.
- **부정/회귀**: 미승인 저장소·임의 URL, 중복 출처, 허위 권리·승인 필드, 누락/위조된 챕터와 출처, HTML/Markdown 주입, 제어문자·초과 입력, 잘못된 개정 부모, 임의 서명 및 외부 반출 거부.
- UCIE Windows 로컬 전용 신규 시험 **16/16 PASS**. 정확 HEAD의 4개 GitHub CI 환경 상태는 마지막 변경 커밋에 대해 별도 확인하며, 이전 CI PASS를 유용하지 않은 새 HEAD에 붙이지 않는다.

## 아직 01단계가 완료되지 않은 이유

이번 범용 편집 계약은 **승인 경로의 외부 신규 근거를 입력할 수 있게 하는 데이터·제작 기능**이다. 그러나 신규 원문의 SHA·원리 진실성·실제 기술 효과를 독립 검증한 기록은 없다. 새로운 공개 자료를 알아서 해석·일반화하는 완전 자동 엔진도 아니며 수동 검토·권리·보안·서명·실제 배포 승인은 모두 별도다. 따라서 01=PARTIAL, 02~05=PARTIAL, 06=NO_GO를 유지한다.

다음 작업은 실제 승인 공개 자료 한 건에 대한 독립 근거 검증 영수증 및 수동 검토 인수 경로를 마련하고, 미승인 후보를 가상도서관에서 정확히 분리해 비교하는 기능이다. 6번 종단 간 출시 인수까지 기존 6단계 진행표를 매 작업 종료마다 반복한다.
