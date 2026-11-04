# UCIE SkillBook 001 — Python os.scandir 자원 수명과 제한된 열거

- 자산 ID: `UCIE-SKILLBOOK-PY-SCANDIR-001`
- 상태: **UCIE가 작성한 재사용 레시피 초안** — `FIRST_PARTY_DRAFT_NOT_APPROVED`
- 발행 예정: 없음 (미서명, 미승인, 외부 배포 불가)
- 기준일: 2026-11-04 KST
- 기술 분야: Python 3.13/3.15 대상 UCIE 자체 합성 시험 (별도 CI 필요)
- 소스 범위: 승인된 공식 문서와 독립 소유 저장소 `python/cpython`만

## 1. 이 기술이 해결하려는 문제

디렉터리 엔트리 반복기를 사용하는 코드가 예외 또는 조기 종료 시
운영체제 자원을 해제하지 못하거나, 열거 순서를 항상 일정하다고 잘못
가정하거나, 호출자 허용 없이 다른 경로로 탐색 범위를 확대하는 위험을
줄이는 것이 목표다. UCIE의 제품 기능에 포함된 범용 파일시스템 기술
사례지만 UCIE가 다른 프로젝트의 실제 파일을 조사하도록 허가하지 않는다.

## 2. 출처 검증과 UCIE 해석을 분리

**공식 Python 문서가 명시한 사실**

- `os.scandir()`는 순서가 보장되지 않는 `os.DirEntry` 반복자를
  돌려준다. 디렉터리가 열거 도중 변하면 어떤 항목이 포함되는지도
  보장되지 않는다.
- `scandir()` 반복자는 `close()`와 `with` 컨텍스트 관리자를
  지원한다. 일찍 중단하거나 오류가 발생할 수 있는 경우에는
  명시적으로 닫거나 `with`를 쓰는 것이 권장된다.
- `DirEntry`의 타입·메타데이터는 파일시스템 변경 후 오래된 값이
  될 수 있다. 독립 보안 경계나 원자적 스냅샷을 뜻하지 않는다.

**고정된 공개 소스** (UCIE 기존 Source Registry `doc:python/cpython`):

| 근거 속성 | 고정 값 |
|---|---|
| 공식 문서 | https://docs.python.org/3/library/os.html |
| 공개 저장소 | https://github.com/python/cpython |
| 검증 기준 태그 | `v3.15.0` |
| 태그가 가리키는 커밋 | `d220409a13b77de7a6c30abe16ea90db01528edc` |
| 문서 소스 | `Doc/library/os.rst` |
| Git blob SHA-1 | `74419ee7f3588f1baec83c85b05716e6388719e3` |
| 문서 소스 전체 SHA-256 | `9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a` |

위 Git SHA-1과 SHA-256은 서로 다른 종류의 지문이며,
SHA-256은 *해당 Git 커밋의 문서 소스 전체 UTF-8 바이트*에 대한
지문이다. 현재 변경 가능한 공식 문서 URL을 스냅샷 지문으로
오인하지 않는다. 소스 본문을 SkillBook에 복제하지 않으며
원본 문서는 열람·인용 대상으로만 사용한다.

**UCIE가 독자적으로 작성한 제안**

원본의 API 약속을 근거로 다음과 같은 *새로운* 계약을 만든다.
이는 Python 공식문서의 공식 예제나 보안 인증 제품이 아니다.

1. 호출자는 접근 권한이 있는 **절대 로컬 디렉터리**를 명시한다.
   파일·심볼릭 링크·정션 디렉터리 입력을 차단한다.
2. 총 엔트리 수 1–128개를 포함하는 예산을 둔다. 일반 파일뿐 아니라
   디렉터리·링크를 포함해 모두 센다. 예산 초과는 실패로 판정한다.
3. `with os.scandir(directory) as entries:`를 사용해 정상 종료와
   예외 시 반복자를 닫는다.
4. 링크를 따라가거나 재귀 탐색하지 않고, 정규 파일의 **이름**만
   반환한다. 파일 내용·ACL·환경변수·외부 프로젝트 데이터는 읽지 않는다.
5. 결과는 `tuple(sorted(names))`으로 반환하여 여러 환경에서의
   임의 열거 순서와 결과 순서를 분리한다.

### 실제 호출 예제

다음 코드는 *해당 호출자의 명시적 권한이 있는 파일 경로*에만
사용해야 한다. UCIE 도서관 조회에서는 실행되지 않는다.

```python
from pathlib import Path
from ucie_miner.skillbook_scandir_recipe_v01 import (
    bounded_regular_file_names,
    BoundedScandirError,
)

approved_directory = Path("/absolute/path/to/authorized/test-fixture")
try:
    names = bounded_regular_file_names(approved_directory, max_entries=32)
except BoundedScandirError as exc:
    raise RuntimeError("AUTHORIZED_DIRECTORY_SCAN_NOT_VERIFIED") from exc
```

**주의:** 오류가 나도 빈 튜플을 성공으로 간주하면 안 됩니다. 실제 제품에서는
`BoundedScandirError`를 정상의 빈 목록과 구분되는 상태로 반환해야 합니다.
외부 인가 없는 경로를 UCIE 시험 입력으로 사용하지 않습니다.

## 3. 기계 판독 계약 / 검색 연결

- 구현 코드: `src/ucie_miner/skillbook_scandir_recipe_v01.py`
- 출처 결속·SkillBook 문서 계약: `src/ucie_miner/skillbook_product_v01.py`
- 기존 W01+W02 `build_library_entry()`을 통과해야만 구성된다.
- `REUSABLE_SKILL` 항목 및 `BOUNDED_SCANDIR_RESOURCE_LIFECYCLE` 목적 코드
  (분야 Python / Python3.15 문서 근거)를 도서관에 보인다.
- 기존 W04 공개 후보 DB는 건드리지 않는다.
- `GET /skillbooks`, `GET /skillbooks?q=scandir&language=Python`,
  `GET /skillbooks/<asset-id>`, `GET /skillbooks/<asset-id>.json`
  은 고정된 UCIE 작성 초안만 보여준다.
- JSON도 **승인된 배포 패키지가 아니다**. `export_allowed:false`,
  `published:false`를 유지한다.

실행 환경:

```powershell
& 'D:\UCIE\scripts\ucie_skillbook_library_v01.ps1'
```

정상 동작 시 출력되는 `http://127.0.0.1:PORT/skillbooks`를
**같은 Windows PC**에서 연다. 종료는 Ctrl+C이며 예약 작업·서비스
자동 등록은 하지 않는다. 기존 V1.1 도서관 브라우저를 상속해 V0.9 공개 근거 조회,
V1.0 관측 이력, V1.1 독립 검토 준비 기능도 보존한다.
원래의 V0.9/V1.0/V1.1 파일은 변경하지 않는다.

## 4. UCIE 자체 시험과 반례

실제 효과 측정은 UCIE가 작성한 일회용 합성 디렉터리로 제한한다.

| 테스트 | 기대 결과 |
|---|---|
| 임시 일반 파일 2개·폴더 1개 | 파일명 정렬 반환 2건 |
| 조기 중단·항목 예산 초과 | 명시적 실패, 반복자 닫힘 |
| 파일 타입 검사 중 합성 OSError | 명시적 실패, 반복자 닫힘 |
| 파일/디렉터리/심볼릭 링크 처리 | 링크 무시, 직접 링크 루트 차단 |
| 상대 경로·미존재 경로 | 실패 차단 |
| 0, 129, bool, 부동소수 예산 | 실패 차단 |
| 검색·상세·JSON·호스트 필터 | 공개 GET 0, 원장/운영 DB 쓰기 0 |

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_skillbook_product_v01.py' -v
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_skillbook_browser_v01.py' -v
```

성능 우수성(예: listdir 대비 실제 운영 절감 시간)을 한 번의
합성 시험으로 주장하지 않는다. 예제의 *자원 정리 여부·출력 경계*
같은 재현 가능 검증만 이번 수용 범위에 포함한다.

## 5. 미완료 근거와 다음 생산 게이트

- 공식문서 API 사실 vs UCIE 작성 알고리즘의 동작 시험은 별도.
- Python 3.13/3.15에서의 **UCIE 자체 CI PASS**를 얻어도, 제3자
  독립 QA나 일반 사용자 환경에서의 위험 제거를 증명하지 않는다.
- 윈도우 정션·링크 경합·변경 중인 디렉터리·권한 재검증·POSIX
  파일 디스크립터 수명·심볼릭 링크/TOCTOU 공격은 보안 차단
  보증 범위가 아니다. 원자적 파일시스템 스냅샷을 만들지 않는다.
- Python 문서 사용권/표시의 법적 검토, 제품 재배포에 필요한 권리
  확인, 보안 검토·소유자 서명·배포 승인은 **NOT_VERIFIED/NO_GO**.
- UCIE 전용 모의 데이터만 활용하며, 다른 프로젝트 코드·로그·
  사용자 파일을 수집·분석·실행하지 않는다.
- 공인된 일반화 SkillBook 자동 제작기, 무인 자동학습,
  외부 패키지 배포 또는 UCIE V1 전체 합격은 주장하지 않는다.

다음 발전 단계는 동일한 공개 근거와 UCIE 자체 테스트의 개정
이력을 연결하고, 진짜 독립 시험·권리 승인 후 재사용 패키지
승인 여부를 결정하는 것이다.
