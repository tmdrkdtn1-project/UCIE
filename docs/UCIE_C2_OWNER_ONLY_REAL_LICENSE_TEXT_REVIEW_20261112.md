# UCIE C2: 소유자 로컬 외부 라이선스 원문 검토 패키지

기준: 2026-11-12, UCIE 전용, 로드맵 #199. 이 개발 자체는 고객 배포 승인이 아니다.

## 실질적 목적
이전 PR #250은 3개 외부 wheel의 라이선스 표시·파일 개수·해시를 검증했다. 이제 소유자의 C1 SHA256/PEP427 RECORD 고정 저장소에서 License-File로 선언된 **실제 원문 텍스트**를 재검증하고, 사람이 검토할 수 있는 신규 소유자 로컬 폴더로 옮길 수 있도록 한다.

- 대상: cryptography 50.0.2, cffi 2.1.1, pycparser 3.12.
- 기본 inspect는 읽기 전용. wheel 해시, RECORD, 선언된 라이선스 파일 bytes/hash, 비신뢰 경로 검증. 파일 출력 없음.
- owner-export-once는 별도 소유자 정확한 대화형 동의가 있어야 한다. Windows D:/UCIE만 허용하며, downloaded/ucie_c2_owner_only_license_review_v01 신규 폴더에만 원문 라이선스 5개(실측 대상; 증거가 바뀌면 다시 검사)와 리뷰 manifest 및 한국어 사용안내를 작성한다. 기존 패킷은 덮어쓰지 않는다.
- 다른 프로젝트 접근, 외부 API, 패키지 바이너리 복사, vendor 코드 import/실행/pip 설치, 운영 DB, C40, Local V1, TaskScheduler, Cloudflare 및 일일 09:00 HOLD 변경 없음. GitHub CI는 합성 원문으로만 시험한다.

## PowerShell 사용

기본 읽기 전용:
~~~powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_c2_owner_license_review_packet_v01 --inspect
~~~

별도 소유자 승인 후 실제 신규 로컬 검토 폴더 생성:
~~~powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_c2_owner_license_review_packet_v01 --owner-export-once
~~~

정확한 동의 구문: EXPORT_UCIE_C2_OWNER_ONLY_LICENSE_TEXT_FOR_HUMAN_REVIEW_ONCE

이 패키지는 소유자 PC 내부 **사람 검토용**이다. 외부 전송, 고객 전달, 제3자 원문 재배포·상용 사용 허가를 제공하지 않는다. 원문 파일 내용은 신뢰할 수 없는 입력이므로 지시로 실행하지 않는다.

## 사람 검토와 출시 차단

모든 패키지별 리뷰 상태는 false: 권리자/약관의 상용 재배포 허가, 원문 NOTICE·배포 의무, 공급자·출처 신원 확인, 정확 버전의 공개 보안 권고, Windows native 호환 및 전이 종속성 검토, C3 고객별 서명·권한, C4 별도 수신 PC 설치·업데이트·롤백·제거, C5 고객 파일럿.

원문 라이선스 존재를 보고 이 단계를 승인하면 안 된다. 성공한 텍스트 검사도 CLI 종료코드 2로 GO 차단을 유지한다. C4 최초 clean Windows source-only Local V04 UI는 ModuleNotFoundError로 실패했고, 권리 검토 없이 vendor를 실행해 우회하지 않는다. 고객용 완제품 상태는 UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO.
