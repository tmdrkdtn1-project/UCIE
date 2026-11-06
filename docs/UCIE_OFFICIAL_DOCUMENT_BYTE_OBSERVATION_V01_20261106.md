# UCIE V1 — 공식 공개 문서 원본 바이트 수동 관측·SkillBook 근거 결속 V0.1

기준일: 2026-11-06. 범위: UCIE ONLY. 상태: **실제 코드 개발 / 소유자 자체 합성 테스트 / 공식 사이트 실원본 영수증 미수집 / 출시 NO_GO**.

## 해결하려는 실제 제품 결함

SkillBook 편집 후보의 제출된 evidence_sha256은 이전까지 단순 입력 값이어서, 승인된 공식 공개 출처라도 그 시점 실제 HTML 응답의 SHA와 일치한다고 단정할 수 없었다. 특히 기존 `https://docs.python.org/3/library/os.html` 및 `https://git-scm.com/docs/git`는 URL 경로가 고정돼 있을 뿐 **특정 콘텐츠 리비전/버전에 고정된 불변 주소가 아니다**. 2026-11-06 공식 웹 열람에는 각각 Python 3.15.2 및 Git 2.56.0 최신 표시가 확인됐다. 기존 서적의 Python 3.15.0 및 Git 2.51.0 주장을 현재 최신 URL의 정확한 버전 증거로 자동 취급하면 안 된다.

## 기존 승인 수집 범위의 수동 1회 실행

`src/ucie_miner/skillbook_official_doc_observation_v01.py`는 기존 `source_registry.get_source`와 `public_evidence_routes.DOC_ENDPOINTS`에 **동시에 정확히 등록된 공식 문서 5개**의 기존 HTTPS 주소만 사용할 수 있다. 새 공개 출처나 GitHub API 라우트를 허용하지 않는다. 기존 `core.NoRedirect`, 비인증 GET, 12초 제한, HTML MIME, identity 인코딩, 본문 최대 1,500,000바이트, URI exact-match, HTML 주제 마커를 확인한다. HTML을 **원문 바이트 그대로 SHA-256** 처리하고 길이·조회 시각·출처 ID·정확 URL·마커 확인 결과만 반환한다. 원문을 출력·재배포·저장하지 않는다. 본문 텍스트는 실 코드로 해석·실행하지 않는다.

실제 소유자 Windows에서 수동 실행하는 명령(자동 실행/등록 아님):

```powershell
Set-Location D:\UCIE
& .\.venv\Scripts\python.exe -m ucie_miner.skillbook_official_doc_observation_v01 --source doc:python/cpython --confirm-network --compare-curated
```

`--confirm-network`가 없으면 네트워크 조회 **전** FAIL_CLOSED로 종료한다. `--compare-curated`는 UCIE가 이미 작성한 Python/Git 두 SkillBook의 현재 검토 후보와 위 문서 바이트 해시를 비교한다. 이 예시에서 기존 기록된 SHA가 바이트 기준의 HTML 원문 해시와 다르면 **OBSERVED_BODY_SHA_MISMATCH_BLOCKED**가 나온다. 같은 SHA라도 **OBSERVED_BODY_SHA_MATCH_REVISION_UNVERIFIED**로 기록하여 문서 버전·기술 사실·권리·보안·독립 QA·출시 승인을 수행했다고 주장하지 않는다. 사용자 정의 URL·새 수집 경로·자동 스케줄 실행은 지원하지 않는다.

## 실제 가상도서관 연동

기존 `src/ucie_miner/skillbook_catalog_union_v01.py`의 `/catalog` 및 `/catalog/review?id=<draft SHA>` `/catalog/review.json?id=<draft SHA>`는 **인메모리로 전달한, 서명되지 않은 수동 관측 영수증**을 해당 후보 공식 출처와 비교해 다음을 구분한다.

- NO_MANUAL_RAW_BYTE_OBSERVATION: 원문 바이트 관측 영수증 없음
- NOT_AN_OFFICIAL_DOCUMENT_ROUTE: 공식 HTML 관측 대상이 아닌 승인 저장소 근거
- OBSERVED_BODY_SHA_MATCH_REVISION_UNVERIFIED: 제출 SHA와 관측 SHA 일치, 콘텐츠 리비전/진위·기술 검토 미완
- OBSERVED_BODY_SHA_MISMATCH_BLOCKED: 제출 SHA와 관측 SHA 불일치, 후보 차단

로컬 GET은 **절대 새 공식 URL을 조회하지 않는다**. 네트워크 수동 호출에서 얻은 메타데이터는 `make_handler(..., editorial_observations=(receipt,))`처럼 UCIE 로컬 코드의 인메모리 인자로 전달한다. 사용자가 HTTP query에 승인, URL, 네트워크 실행 인자를 추가하는 경로는 없다. 영수증 JSON 자체는 **서명되지 않았고 재생 가능**하므로 데이터 비교 정보로만 표기하며 independent_authenticated/verified/reviewed/exportable 등 출고 판단을 true로 바꾸지 않는다. 비교 화면에서는 기존 두 기술서적과 편집 검토 후보의 실행 가능 상태도 계속 구분한다.

## 중요한 검증 범위

- 테스트 `tests/test_ucie_skillbook_official_doc_observation_v01.py`: 기존 승인 경로·opt-in 요구, HTML MIME/리다이렉트/초과/압축/인코딩/주제 마커 실패 차단, 응답 본문 SHA, 제출 SHA 일치/불일치, 수동 CLI, 허위 승인/영수증 변조 거부. **모든 외부 HTTP는 UCIE가 직접 만든 합성 HTML/모의 응답**이다.
- 테스트 `tests/test_ucie_skillbook_catalog_doc_observation_v01.py`: 관측 미실시·불일치·일치 상태를 실제 127.0.0.1 HTTP UI/JSON에서 확인, GET 중 공식 사이트 네트워크 요청이 없음을 시험, 위조 승인과 외부 Host 차단.
- 기존 `test_ucie_skillbook_catalog_editorial_integration_v01.py`·`test_ucie_skillbook_catalog_union_v01.py` 등 회귀 검사로 기존 도서관, W04 분리, 콘텐츠 이스케이프/승인 차단 유지.
- **본 개발 수행 환경에서는 소유자 Windows에서 공식 사이트로 실제 1회 GET을 실행할 권한 있는 원격 도구가 없다**. 브라우저로 현재 공식 페이지 버전 표시는 확인했으나 그 본문 바이트 SHA의 소유자 호스트 영수증을 취득했다고 주장하지 않는다. 실제 GET은 소유자 Windows에서 위 명시 수동 명령을 실행한 뒤에만 별도 증거로 기록할 수 있다.

## 6단계 로드맵 인수 경계

01 PARTIAL: 공식 문서 바이트 검증·편집 후보 SHA 결속 기능 구현, 실제 소유자 실원문 영수증 및 사실/전문가 검토 미완.
02 PARTIAL: 검토 후보 목록/상세에 바이트 관측 상태 표시 작동, 범용 승인형 기술 도서관 인수 미완.
03 PARTIAL: 미승인 메모리 내부 초안, 외부 패키지/서명 미완.
04 PARTIAL: 소유자 자체 테스트와 CI 별도 증거, 독립 소스 검증자·효능 비교 미완.
05 PARTIAL: 개정 비교는 구현, 영구 검증 영수증·사후 철회/회귀 연동 미완.
06 NO_GO: 실제 운영 안정성·보안/권리·독립 QA·소유자 출시 승인·통합 사용 검증 미완.

다음 실제 작업은 **정확 소유자 호스트 공식 원문 바이트 영수증 확보 후** 제출된 과거 근거 SHA의 차이를 판별하고, 독립 사람 검토 결과를 영구 보존 가능한 버전/서명 승인 게이트와 분리해 연결하는 것이다.
