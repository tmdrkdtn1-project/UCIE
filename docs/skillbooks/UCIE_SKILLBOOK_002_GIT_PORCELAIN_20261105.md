# UCIE SkillBook 002 — Git porcelain v1 -z 변경 개수 요약

PROJECT=UCIE ONLY. ID=`UCIE-SKILLBOOK-GIT-PORCELAIN-002`.
VERSION=0.1.0-draft. STATUS=FIRST_PARTY_DRAFT_NOT_APPROVED.
독립 QA·보안 검토·재배포 권리·소유자 승인·서명·배포 모두 미승인.

## 1. 공식 근거와 기술의 출처

기존 승인된 공개 `git/git` 저장소의 **v2.51.0** 태그에서
`Documentation/git-status.adoc`의 *Porcelain Format Version 1*와
`-z` 형식을 고정 근거로 사용한다. 공식 문서에 따르면 Porcelain v1은
스크립트용 기계 판독 형식이고, NUL 종료 레코드에서는 rename/copy
경로 둘의 순서가 바뀌며 각 경로를 NUL로 구분한다.

| 항목 | 식별자 |
| --- | --- |
| 공식 저장소 | https://github.com/git/git |
| 고정 공식 원본 | https://github.com/git/git/blob/v2.51.0/Documentation/git-status.adoc |
| 문서 설명 | https://git-scm.com/docs/git-status |
| 기존 W01 근거 ID | `doc:git/git`, `https://git-scm.com/docs/git` |
| 공식 문서 Git blob SHA-1 | `9a376886a5867a63d173d85162c57027f336f915` |
| 공식 문서 전체 SHA-256 | `1cdd1c7339dfc64093687b6e072d59feee584b8639c0203ece0a1150ce23d325` |
| 사용권 검토 원본 | https://github.com/git/git/blob/v2.51.0/COPYING |
| 공개 COPYING Git blob SHA-1 | `536e55524db72bd2acf175208aef4f3dfc148d42` |

공식 문서는 API·상태 형식의 **기술 근거**이고, 나머지 입력 제한과
요약 알고리즘은 **UCIE 작성물**이다. Git 공개 COPYING에 GPL v2
본문이 있다고 해서 UCIE 기술서적·코드·재배포 권리가 자동 승인되는
것은 아니다. 별도 법적·보안 검토가 완료돼야 한다.

## 2. 실제 재사용 레시피

기존 W01 공급원 레지스트리, W02 `build_library_entry()`, SkillBook
제품 계약, `/catalog`·`/skillbooks` 도서관과 기존 출시 게이트를
**재사용**한다. 새 네트워크 수집기, 새 브라우저 서비스, 새 승인
엔진, 별도 자동 패키저는 추가하지 않는다.

- 파일: `src/ucie_miner/skillbook_git_porcelain_recipe_v01.py`
- 호출: `summarize_porcelain_v1_z(payload: bytes, *, max_entries=64)`
- 입력: 이미 확보한 Git Porcelain v1 -z 형식의 **bytes만**
- 제한: 총 8192 bytes, 상태 엔트리 최대 64개, 경로당 최대 1024 bytes
- 정상 결과: 수정·rename·copy·충돌·미추적·무시된 파일 상태의
  개수와 안전한 고정 스키마만. 원본 경로·파일 내용 반환 없음.
- 실패: NUL 누락, 깨진 XY 상태, rename/copy 원본 경로 누락,
  초과 입력·경로 탈출 형태는 `PorcelainSummaryError`로 차단
- 경로는 처리 직후 버리며 **실제 git 실행이나 저장소 조회는 없음**.
- 유효한 특수 Git 경로도 보수적 정책 때문에 거부할 수 있다.
  따라서 Git 출력 전체를 수용하는 범용 파서나 보안 인증 제품이 아니다.

## 3. 도서관 → 계약 → 명시적 소비자 사용

1. 기존 `/catalog`에서 `git` 또는 `porcelain`을 검색한다.
2. 새 SkillBook의 공식 출처 태그·SHA 및 미승인 상태를 확인한다.
3. `/skillbooks/UCIE-SKILLBOOK-GIT-PORCELAIN-002.json`에서
   기계 판독 계약을 확인한다.
4. 브라우저는 어떤 외부 코드를 실행하지 않는다. 사용자는
   아래 **UCIE 작성 메모리 데이터** 시험을 명시적으로 실행한다.

```powershell
Set-Location 'D:\UCIE'
$env:PYTHONPATH = 'D:\UCIE\src'

# 미리보기만, 레시피를 실행하지 않음
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.skillbook_git_porcelain_product_v01

# Git 명령이나 저장소를 열지 않고 4개 합성 항목만 실제 함수로 처리
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.skillbook_git_porcelain_product_v01 --run-synthetic-demo
```

예상 결과: 수정 1, rename 1, 충돌 1, 미추적 1 (총 4개).
`max_entries=3`는 해당 4개 데이터에서 오류로 거부해야 한다.
원본 파일명·사용자 파일·타 프로젝트 코드가 노출돼서는 안 된다.

## 4. SkillBook 001과의 범용 계약 재사용

| 항목 | 001 Python os.scandir | 002 Git status |
| --- | --- | --- |
| W01 공식 출처 | `doc:python/cpython` | `doc:git/git` |
| W02 공개 출처 후보 모델 | 기존 `build_library_entry` | **동일 함수** |
| 도서관 | `/catalog` 및 `/skillbooks` | **동일 경로** |
| 공식 고정 근거 | CPython v3.15.0 os 문서 | git/git v2.51.0 git-status 문서 |
| 실제 UCIE 레시피 | 제한형 일반 파일명 목록 | 제한형 Git 상태 **개수** 목록 |
| 수동 소비 | UCIE 임시 디렉터리 | UCIE 메모리 내 바이트 |
| 제3자 독립 검증 | 미검증 | 미검증 |
| 외부 패키지 권리·보안·출시 | 미승인 | 미승인 |

공통화가 검증된다면 제품 계약·검색·문서의 **기존 코드 재사용**
으로 충분하며, 두 번째 전용 도서관이나 별도 학습 엔진은 불필요하다.

## 5. 기존 시험 체계에서 재현

```powershell
Set-Location 'D:\UCIE'
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p test_ucie_skillbook_002_git_porcelain_v01.py -v
```

Windows/Ubuntu의 Python 3.13/3.15 호환성은 **정확한 개발 PR
커밋**의 CI 작업으로 별도 검증한다. 이는 UCIE 자체 기능 시험이지
제3자 인증이 아니다. Git 바이너리 실제 버전별 출력 시험,
경로 인코딩의 모든 합법적 조합, 악성 데이터 위협 모델, GPL/문서
사용권 검토와 외부 재배포 승인은 아직 수행하지 않았다.

## 6. 제품 상태와 제한

`independent_test_verified=false`,
`license_redistribution_approved=false`,
`security_review_approved=false`,
`human_approved=false`, `signed=false`, `published=false`,
`export_allowed=false`.

실제 Git 리포지터리·사용자 디렉터리·타 프로젝트를 탐색하지 않았고,
운영 수집 DB·Windows 예약 작업·공개 수집 허용 출처도 변경하지 않았다.
자동 규칙 승격·영구 학습·외부 배포도 수행하지 않았다.
