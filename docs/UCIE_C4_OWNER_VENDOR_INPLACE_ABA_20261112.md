# UCIE C4 | 단일 Windows 설치환경에서 외부 의존성 포함 A→B→A 실제 시험

기준: 2026-11-12, UCIE 전용. 로드맵: https://github.com/tmdrkdtn1-project/UCIE/issues/199

## 새 기능

PR #248은 외부 vendor를 포함한 A/B를 소유자 PC의 서로 다른 가상환경 둘에서 선택기만 전환했다. PR #251은 깨끗한 Windows CI의 동일 가상환경에서 A→B→A 실제 업데이트·롤백을 수행했지만 vendor가 없고 Local V04 UI 검증은 제외됐다.

이번 첫-party C4 모듈 customer_c4_owner_vendor_inplace_aba_v01.py는 정확 Git 고정 A(0.1.0, 182개 Python 모듈)/B(0.1.1, 184개)와 기존 UCIE 소유자 C1 SHA/RECORD 고정 wheel cryptography 50.0.2, cffi 2.1.1, pycparser 3.12만 사용한다. 동일한 신규 임시 Windows venv에서 hash-locked, no-index pip로 A 설치 → B 실제 in-place 업데이트 → A 롤백 → 실제 제거한다. 각 단계에서 pip check, 설치형 4축 합성 워크플로, native AES-GCM/cffi/pycparser, Local V04 실제 localhost 5 GET와 POST 405, 버전과 B-only 기능 존재를 검증한다. 의도적으로 변조한 B 사본은 pip 실행 전에 SHA 검증으로 차단한다.

## 안전/권한

- 기본 --inspect 는 읽기 전용. 기존 wheel 3종, C1 실설치 영수증, 고정 Git 원본 A/B 및 신규 결과 경로 준비를 조회한다. 외부 코드 실행이나 다운로드 없다.
- 실제 --owner-run-once 는 D:\UCIE, 정확 owner .venv CPython3.15 x64, 대화형 Windows 터미널, 별도 입력된 고정 동의 문구만 허용한다.
- 실행 시 필요한 Git 원본은 정확 공개 UCIE 두 커밋만 로컬에 존재해야 한다. 다른 repo/소유자 dirty tree는 설치하지 않고 Git fetch·checkout을 자동으로 실행하지 않는다.
- 성공 시에만 downloaded/ucie_c4_owner_vendor_inplace_aba_receipt_v01.json 을 한 번 작성하고 재실행 시 덮어쓰기를 거부한다. 임시 휠/소스/venv는 제거한다.
- 고객 데이터, 타 프로젝트, 외부 패키지 업로드, 새 수집기, 운영 DB·상주 Local V1·C40·스케줄러·Cloudflare·09시 HOLD는 건드리지 않는다.

## 실제 소유자 PC 사전검사 결과 (2026-11-12)

로컬 Windows read-only 사전검사를 실행해 다음을 확인했다.

1. 기존 C1의 외부 wheel 3개, SHA·RECORD, 이전 설치 증거: VERIFIED.
2. 신규 C4 영수증 경로 미사용: VERIFIED.
3. A/B 정확 고정 Git 원본 171d56d8af155c70d3dd32a62afda87398330e99, 4242ebe7ae112076d9b3560e85b0babb22bbb713: OWNER LOCAL UNAVAILABLE.
4. 별도 기존 canonical A/B QA ZIP: OWNER LOCAL UNAVAILABLE.

따라서 실제 vendor-inclusive A→B→A 시험은 아직 실행하지 않았고 PASS로 보고하지 않는다. GitHub CI의 synthetic 4축/first-party smoke 결과도 이 소유자 실제 외부 설치 시험 대신 사용할 수 없다. 정확 pinned 공개 UCIE Git 커밋 두 개가 이미 로컬에 존재해야만 다음 단계를 시작할 수 있다. Git fetch/pull/reset을 현재 명령에서 자동 수행하지 않는다.

## 사용

읽기 전용:
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_c4_owner_vendor_inplace_aba_v01 --inspect

실제 외부 패키지 실행은 별도 소유자 권한과 원본 준비 후:
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_c4_owner_vendor_inplace_aba_v01 --owner-run-once

대화형 정확 입력문: RUN_UCIE_C4_OWNER_DISPOSABLE_VENDOR_ABA_ONCE

## 미완료 고객 인수

이 코드는 실제 외부 의존성을 포함한 같은 소유자 PC의 설치 교체 기술시험 기능이지 완제품 배포가 아니다. 별도 소유자 관리 Windows 수신 PC, 서명된 설치파일, 외부 벤더 라이선스·NOTICE/보안 독립 심사, 실제 완전 4축 고객 인수, C3 고객별 entitlement·서명, C5 지정 고객 승인 모두 NO_GO다. 라이선스 메타데이터로 자동 재배포 승인하지 않는다.

고객 출시 상태: UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO.
