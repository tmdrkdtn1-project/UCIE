# UCIE Local Library Browser V0.1 (2026-11-01)

## 범위

기존 W04 library_search.search_existing_public_library 및 Stage10/12/15
원장 연결 검증을 그대로 사용하는 UCIE 전용 Windows 로컬 검색 웹 화면.
공개 기술 근거 후보 메타데이터를 찾아보는 독립 UI이며 전체 Virtual Library
V1 완료를 의미하지 않는다.

- 바인딩: 127.0.0.1 전용, 포트 0으로 사용 가능한 로컬 포트 자동 선택.
- 화면: 검색어(현재 영문 메타데이터), 기술 분야, 승인된 공개 저장소, 후보 종류, 건수.
- 결과: 출처, 목적 코드, 개정, 근거 SHA-256, 공개 PR 링크(허용 형식만).
- 원장 불일치 시 결과 표시 차단. 후보는 미검증으로 명시. 검증 승인·내보내기 불가.
- 금지: 자동 승격, 외부 코드 실행, 새로운 수집, 신규 스케줄러 등록,
  UCIE 외부 파일/프로젝트 접근, 저장된 검색어 로깅, 공개 네트워크 서버 노출.
- 서버는 GET 검색과 GET /health만 지원. POST는 405.
  외부 JavaScript, CDN, 텔레메트리 없음.
- 실제 Windows root는 정확히 D:\UCIE에만 허용.

## 소유자 로컬 사용

기존 D:\UCIE 작업 트리에 미커밋 파일이 다수 있음.
전체 git pull/reset/clean 하지 말 것. 신규 UI 소스 1개와 신규 실행 스크립트
1개만 별도로 반영하는 것이 안전하다.

Windows PowerShell:

    & 'D:\UCIE\scripts\ucie_library_browser.ps1'

콘솔에서 LOCAL_READ_ONLY_UI_LISTENING 및
http://127.0.0.1:<할당된포트>/ 주소가 나타나면,
같은 PC의 브라우저에서 해당 URL을 열어 검색한다.
종료: Ctrl+C. 별도의 예약 작업 등록이나 서비스 설치는 하지 않는다.

Python stdlib만 추가 사용한다. 기존 UCIE 가상환경과 검색 모듈은 필요하다.
실제 표시 결과는 기존 Stage12 검토 원장과 출처 연결 검증 상태에 따라 달라진다.
SOURCE_LINKAGE_INCOMPLETE_NO_GO를 검색 성공으로 보지 않는다.

## 합성 회귀시험

    $env:PYTHONPATH = 'D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_library_browser.py' -v

합성 시험은 승인된 공개 후보 형식의 가짜 메타데이터를 로컬 127.0.0.1
임시 서버에 제공한다. 운영 SQLite, 수집 스케줄러, 공개 API 및 다른 프로젝트를
사용하지 않는다.

운영 승인, 서명, 독립 PC 설치 검증, 전체 V1 제품 완성은 별도 작업이다.
