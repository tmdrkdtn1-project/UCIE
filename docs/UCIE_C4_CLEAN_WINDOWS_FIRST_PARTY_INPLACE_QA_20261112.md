# UCIE V3 C4 — 깨끗한 Windows 단일 환경 A→B→A 실제 설치 QA (소스 전용)

날짜: 2026-11-12. 범위: **UCIE만**. 기준 로드맵: https://github.com/tmdrkdtn1-project/UCIE/issues/199

## 이전 시험과 실질적 차이

- PR #248은 **소유자 PC의 별도 가상환경 두 개**에 A/B를 설치한 후 선택기만 전환했다. 이는 하나의 고객 설치를 실제 업데이트/롤백한 것은 아니다.
- PR #249는 A/B **공개 Git 고정 소스**를 Windows/Ubuntu에서 바이트 일치하는 QA wheel/ZIP으로 재현했으나 설치/업그레이드는 없었다.
- 이번 신규 워크플로는 **깨끗한 Windows GitHub Actions VM 한 대의 단일 가상환경**에서 Git 고정 A→B→A wheel을 실제 pip로 설치·업데이트·롤백·제거한다. 처음 A로 돌아왔을 때 4축과 V04 임시 localhost 결과가 동일한지 비교한다.

## 직접 실행하는 프로그램과 증거

- 테스트: tests/runtime_ucie_c4_clean_windows_first_party_lifecycle_v01.py
- CI-only 안전 회귀: tests/test_ucie_c4_clean_windows_first_party_lifecycle_v01.py
- 독립 워크플로: .github/workflows/ucie-c4-clean-windows-first-party-lifecycle.yml

1. UCIE 공개 Git A 커밋 171d56d8af155c70d3dd32a62afda87398330e99 / B 커밋 4242ebe7ae112076d9b3560e85b0babb22bbb713 원본 객체를 기존 source manifest의 Git blob SHA-1 / 크기 / C0 23경로와 대조한다. 로컬 소유자 변경파일과 고객 코드를 전혀 읽지 않는다.
2. A 182개/B 184개 공개 UCIE Python 모듈에서 2개 실제 first-party wheel을 빌드하여 C1 고정 wheel SHA256과 PEP427 RECORD/원본 바이트 동일성을 검사한다. 외부 wheel을 가져오지 않는다.
3. CI VM 임시 폴더에 정확히 1개 venv를 만들고 pip --isolated install --no-index --no-deps로 A 실제 설치 → 4축 합성 기능 및 임시 Local V04 localhost HTTP GET/POST 거부 검증.
4. 변조 B 복사본 해시를 pip 실행 전에 차단하고 정상 B wheel만 같은 venv에 실제 in-place 설치. B 전용 real installed four-pillar self-check와 CLI/UI를 실행한다.
5. 같은 환경에 A wheel 실제 pip 롤백 → B만의 모듈 소멸 검사 및 최초 A 사용결과와 비교.
6. pip uninstall 실제 수행 및 모듈/메타데이터 제거 확인. 모든 임시 venv/소스/wheel 삭제. CI artifact/release 업로드, 패키지 외부 배포, 키/계약 생성 없음.

## 승인 범위와 미완료

이 시험은 **first-party source-only, 깨끗한 Windows CI VM, 실제 단일 venv 업그레이드/롤백 기술시험**에 한정한다. 다음을 PASS로 보지 않는다.

- cryptography/cffi/pycparser 실제 외부 wheel **미포함**. no-deps이므로 전체 의존성 설치나 pip check/native ABI/NOTICE·재배포·보안심사 미완.
- 전체 4축 **합성 입력**만 사용. 실제 완성 SkillBook 원고, 고객 워크플로, 생산 서비스 설치/Windows 서명 MSI/EXE 및 고객별 라이선스 미승인.
- GitHub-hosted Windows VM은 고객이나 소유자가 관리하는 **두 번째 독립 수신 PC가 아님**. 실제 customer C4 최종 인수는 계속 NO_GO.
- GitHub가 checkout/setup-python을 위해 네트워크를 사용하는 것은 별도다. UCIE 제품 pip 실행은 --no-index --no-deps로 차단하며, 외부 코드 실행/업로드 없음.
- D:\UCIE 소유자 PC에는 CI-only 본 실행을 하지 않는다. 소유자 Windows에서는 안전 계약 단일 테스트만 수행한다. 기존 운영 DB, 스케줄러, C40, Local V1, Cloudflare 및 09:00 보고 HOLD 무변경.

결과가 실제 CI에서 성공한 후에만 FIRST_PARTY_INPLACE_QA_PASS라는 기술 게이트로 표시. 전체 **UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO** 유지. 다음 C2 실제 라이선스/NOTICE 원문 권리 검토 및 보안, C3 서명, 독립 소유자 관리 C4 고객용 전체 번들 인수는 별도 승인 필요.
