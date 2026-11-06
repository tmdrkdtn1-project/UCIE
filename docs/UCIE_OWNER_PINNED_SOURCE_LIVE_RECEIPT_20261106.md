# UCIE V1 — 소유자 공식 Python 고정 원본 실조회 영수증 001

**관측 2026-11-06T04:59:41+00:00 (KST 2026-11-06 13:59:41) · USER_REPORTED_OWNER_TERMINAL_OUTPUT · PROJECT=UCIE ONLY**

> 이 기록은 사용자가 UCIE `PS D:\UCIE>` 터미널에서 직접 제공한 1회 공개 원본 검증 JSON을, 운영 DB나 별도 검토 원장에 쓰지 않고 **출시 진척 증거**로 보존한 것이다. 터미널 실행 기원·신원·전자서명은 제3자가 확인한 것이 아니다. 데이터 최소화: 공개 메타데이터만 기록, 본문 원본 221,596바이트는 저장하지 않음.

## 관측된 실제 코드 응답

| 필드 | 실제 사용자 제공 값 |
|---|---|
| schema | `UCIE_OWNER_PINNED_SOURCE_ONE_SHOT_ACCEPTANCE_V01` |
| status | `RAW_PUBLIC_GIT_BLOB_MATCHES_PIN_NOT_RELEASE_APPROVED` |
| source_id | `doc:python/cpython` |
| source_content_address_url | `https://api.github.com/repos/python/cpython/git/blobs/74419ee7f3588f1baec83c85b05716e6388719e3` |
| verified_source_tag / file | `v3.15.0` / `Doc/library/os.rst` |
| raw_source_bytes | `221596` |
| expected_sha256 / sha256 | `9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a` / **동일** |
| git_blob_sha1 | `74419ee7f3588f1baec83c85b05716e6388719e3` |
| source_bytes_sha256_and_git_blob_match | `true` |
| network_requests | `1` |
| operating_database_writes | `0` |
| review_event_id | `88978c947cd80607c3f8b90222143f2354cd888db41cae46515851401ff8c9ae` |
| review_journal_status | `NOT_REQUESTED` |
| review_journal_written / catalog_reference_checked | `false` / `false` |
| auto_promoted / auto_withdrawn / released | `false` / `false` / `false` |
| human_approved / independent_qa_verified / technical_claims_reviewed | `false` / `false` / `false` |
| source_origin_independently_attested / source_tag_signature_verified | `false` / `false` |
| license_redistribution_approved / export_allowed | `false` / `false` |
| source_raw_bytes_saved_or_redistributed / other_project_access | `false` / `false` |

## 확인 결과 및 실제 인수 범위

- UCIE의 기존 공개 `python/cpython` **v3.15.0 `Doc/library/os.rst`** Git blob SHA-1은 정확하다. 이 기록 작업에서도 해당 **공개 저장소의 고정 태그 파일**을 조회하여 API가 반환한 Git blob ID `74419ee7...`와 **일치**함을 확인했다. 사용자가 제공한 `sha256`과 `expected_sha256`의 동등성은 검증 CLI의 출력에서 확인되며, 이전 원본 파일 바이트 재계산과도 일치한다.
- 이 결과로 **실제 소유자 PC의 1회 네트워크 원문 바이트 검증 단계는 Python 001에 한해 관측**됐다. 과거의 RST vs HTML 직접 비교 오류는 이번 관측에서 발생하지 않았다.
- 그러나 **검토 원장과 가상도서관 연결은 아직 실호스트 인수 전**이다. `review_journal_status=NOT_REQUESTED`, `review_journal_written=false`, `catalog_reference_checked=false`; 이 기록을 운영 검토 원장의 이벤트로 허위 표시하지 않는다.
- 출력은 **미서명**이다. 공식 Git 태그 서명/출처 소유권 독립 인증/기술 사실 심사/부정 시험 효과/재배포 사용권/보안/제3자 독립 QA/소유자 출시 승인은 증명하지 않는다. 자동 Rulepack 승격, 실제 SkillBook 철회, 서명, 외부 출시 **0건**.

## 다음 실인수 경계

사용자가 **별도로 원장 기록을 명시적으로 선택하는 경우에만** 기존 실행형 수동 명령을 사용한다.

```powershell
Set-Location D:\UCIE
& .\.venv\Scripts\python.exe -m ucie_miner.skillbook_owner_pinned_acceptance_v01 --source doc:python/cpython --confirm-network --record-review --confirm-review-write
```

이 호출은 기존 영수증을 신뢰해 바로 원장에 올리는 것이 아니라 **승인된 동일 고정 공개 Git blob을 다시 1회 조회·검증**하고, 원장 기록 전 W04 인메모리 연결검사를 거친다. 조건이 맞으면 사용자 승인 범위 내에서 격리된 미승인 검토 이벤트 1건을 기록하고 실제 원장/도서관을 확인한다. 이번 대화에서 그 실행·원장 기록 승인은 자동으로 추정하지 않으며 실제 성공 출력이 있어야 완료로 표시한다.

**6단계 상태**: 01 PARTIAL(실호스트 pinned source 001 바이트 관측 추가, 전문가 기술 검토 미완); 02 PARTIAL(원장 연동 실제 인수 미완); 03 PARTIAL(서명/승인 패키지 미완); 04 PARTIAL(자체 CI + 실원본 1건, 독립 QA/효과 비교 미완); 05 PARTIAL(실원본 GET은 관측, journal/W04 실기록 미완); 06 NO_GO(운영 안정/보안/권리/독립 QA/최종 출시 승인 미완).
