# UCIE SHA 대상 식별 오류 수정 및 실제 소유자 관측 영수증 재분류 — 2026-11-06

**대상 프로젝트: UCIE ONLY · 소유자 승인 범위 내 공식 공개 자료만 사용 · 출시 NO_GO**

## 실제 사용자 제시 관측

2026-11-06T03:21:39Z(한국시간 12:21:39)에 사용자가 출력한 수동 공식 사이트 관측 메타데이터:

- 승인된 정확 문서 라우트: `doc:python/cpython`, `https://docs.python.org/3/library/os.html` (공식 HTML은 버전 불변 파일이 아님)
- 응답 상태 200 / content-type text/html / 원시 본문 크기 791,358바이트 / 표시 마커 os.scandir
- **사용자 보고 원본 HTML SHA-256** `c447c03a759513fa8f5d084954511235e6add13c6784d9b0894a033397c9a51c`
- **기존 서적에 제출된 SHA-256** `9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a`
- 당시 출력: `OBSERVED_BODY_SHA_MISMATCH_BLOCKED`. 사용자 제공 영수증이 실제 실행 로그라는 주장은 사용자의 관측에 근거하며, 영수증 서명과 원본 HTML 전체 791,358바이트를 이 도구에서 독립적으로 확인한 것은 아니다.

## 중요한 원인: 다른 원문을 해시한 값 비교

기존 `skillbook_product_v01.py`의 SHA는 **python/cpython v3.15.0 태그의 `Doc/library/os.rst` 파일 원본 221,596바이트**이고, HTML 응답 SHA가 아니다. 반대로 사용자가 받은 c447...는 **가변 주소의 웹 HTML 응답 791,358바이트**다. 따라서 두 digest를 무조건 `==` 비교하고 불일치를 문서 변경으로 판단한 이전 검증 로직은 잘못됐다.

이번 응답에서 허용된 **공개 공식 GitHub 원본 리비전**을 실제 재조회하여 원시 파일을 디코딩하고 SHA-256을 재계산했다.

| 승인 공개 태그 파일 | 원시 크기 | 재계산 SHA-256 | 기존 저장 SHA | Git blob SHA-1 |
|---|---:|---|---|---|
| [python/cpython v3.15.0 os.rst](https://github.com/python/cpython/blob/v3.15.0/Doc/library/os.rst) | 221,596 | `9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a` | 일치 | `74419ee7f3588f1baec83c85b05716e6388719e3` |
| [git/git v2.51.0 git-status.adoc](https://github.com/git/git/blob/v2.51.0/Documentation/git-status.adoc) | 20,380 | `1cdd1c7339dfc64093687b6e072d59feee584b8639c0203ece0a1150ce23d325` | 일치 | `9a376886a5867a63d173d85162c57027f336f915` |

이 확인은 **정확한 승인 공개 저장소와 태그에서 조회된 bytes의 해시 일치**이며, 태그 소유권에 대한 외부 서명 인증·기술 내용 검토·재배포 라이선스 인수·제3자 독립 QA·출시는 아니다. 웹 HTML이 변경됐다는 사실도 이 비교만으로 증명하지 않는다.

## 고친 코드 계약

- `skillbook_official_doc_observation_v01.py`: `_submitted_source_material`이 원래 두 SkillBook 빌더의 고정 `source_tag`, `source_file`, `source_document_sha256`, `Git blob SHA1`을 기준으로 submitted digest의 **바이트 대상과 원본 유형**을 확인.
- pinned RST/AsciiDoc와 HTML은 항상 **`INCOMPARABLE_PINNED_SOURCE_VS_LIVE_HTML_REVIEW_REQUIRED`**. 아직 출처별 바이트 대상 선언이 없는 새 편집 후보는 **`INCOMPARABLE_UNDECLARED_MATERIAL_REVIEW_REQUIRED`**.
- 양쪽 모두 `byte_sha_equal=null`, `digest_material_comparable=false`, `source_revision_verified=false`, `human_approved=false`, `export_allowed=false`, `released=false`. 문자열 비교만으로 버전·기술 내용·라이선스 승인을 하지 않는다. 기존 서적의 정확 SHA나 원본 코드 자체는 **교체하지 않는다**.
- `skillbook_catalog_union_v01.py`: 기존 로컬 `/catalog`, `/catalog/review`, JSON에서 **잘못된 '원문 변경·해시 불일치' 메시지 대신** '버전 고정 원문과 웹 HTML 비교 불가·재검토 필요'를 표시하며 출처 태그·RST/AsciiDoc 파일 경로도 표시.
- **실사용 기능 추가**: `--recheck-receipt-stdin`으로 이미 발급된 JSON의 `observation` 또는 전체 `{"comparison":..., "observation":...}`를 표준입력으로 전달하면 **네트워크 GET 없이** 당시 SHA/초안 ID/원본 자료 유형을 다시 검증하고 수정 판정 JSON을 돌려준다. 최대 8 KiB, 중복 JSON 키·위조 승인·다른 source/draft는 차단. 이전 comparison.status는 버리고 `previous_verdict_replaced=true`로 기록. 여전히 **기존 서명 없는 영수증**이며 실 사이트를 재조회한 것으로 보고하지 않는다.

소유자가 원본 JSON을 본인 UCIE 작업범위에 저장한 경우의 **선택적** 오프라인 명령 (파일 존재는 보장하지 않음):

```powershell
Get-Content -Raw -Encoding UTF8 .\runtime\reports\manual_observation.json | & .\.venv\Scripts\python.exe -m ucie_miner.skillbook_official_doc_observation_v01 --source doc:python/cpython --compare-curated --recheck-receipt-stdin
```

위 명령은 네트워크 옵트인 옵션을 받지 않으며, 운영 원장·스케줄·Rulepack·다른 프로젝트 접근은 없다.

## 실현 범위와 다음 검증

- 사용자 제공 관측을 보수적으로 재분류하는 회귀 테스트 `test_ucie_owner_receipt_hash_basis_regression_v01.py`: 실제 보고 SHA·초안 ID·관측 시간/길이로 구성하되, 미서명/미인증 원천임을 그대로 유지.
- 기존 소유자 Windows `test_ucie_skillbook_official_doc_observation_v01.py`, `test_ucie_skillbook_catalog_doc_observation_v01.py`, 실제 loopback 검증, W09 게이트 및 여러 관련 제품·원리 시험은 별도 수행 기록으로만 PASS. 새로운 SHA 대상 판정이 실원문 검증 완료나 외부 인수로 격상되지 않는다.
- **다음 실제 제품 과제**: 이미 알려진 불변 태그 원본과 가변 웹 HTML을 구분해 서가·승인 게이트에 명시하고, 공식 공개 원본 파일을 *같은 바이트 대상*으로 확인한 버전별 증거 영수증과 사람의 기술 원리 검토·개정/철회 연결을 추가해야 한다.

**현재 출시 단계:** 01 PARTIAL, 02 PARTIAL, 03 PARTIAL, 04 PARTIAL, 05 PARTIAL, 06 NO_GO. PR #182 Draft·main 미병합.
