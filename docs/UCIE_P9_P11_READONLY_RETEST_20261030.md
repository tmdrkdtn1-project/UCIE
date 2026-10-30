# UCIE P9 — P11 개선 판단의 안전한 재시험 (2026-10-30)

## 실제 구현

새 모듈 src/ucie_miner/p11_retest.py는 **기존 P11 improvement_review 기록**을 대상으로 UCIE 자체 합성 알고리즘을 재실행한다. 공개 PR 제목/코드/패치 원문과 타 프로젝트 자료는 실행·수집하지 않는다.

- 기존 source + PR 번호 + 병합 SHA + 제목 SHA256와 first-party 실험의 SHA256 영수증을 재계산하고, 원장 수치와 비교한다.
- 원래의 합성 워크로드 및 다른 두 워크로드, 총 128/256/512의 정답 일치와 설정 비용을 포함한 연산량 감소를 재검증한다.
- 기록 원본이 재현되지 않거나 어느 워크로드든 회귀가 발생하면 FIRST_PARTY_RETEST_REGRESSION_HOLD_NO_GO.
- 기존 회귀 HOLD는 새 실험이 우수해도 자동 해제하지 않는다.
- 모두 통과해도 FIRST_PARTY_RETEST_PASS_MANUAL_REVIEW_ONLY: **업스트림 결함 개선·실 운영 성능·코드 승격·서명·릴리스 승인과 무관**하다.
- 기존 65건을 신규 P8 review로 소급 계산하지 않는다. 신규 review가 없으면 P9_NO_NEW_IMPROVEMENT_REVIEW_READ_ONLY가 정상.

## 호출(운영 PC에 별도 적용된 이후에만)

~~~powershell
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.p11_retest --ucie-root 'D:\UCIE' --limit 3
~~~

원장을 mode=ro / PRAGMA query_only=ON으로 열고, 새 테이블·로그·예약 작업·운영 코드·공개 자료를 생성하지 않는다. 이 새 모듈을 GitHub main에 병합한다고 실제 D:\UCIE에 배포된 것처럼 보고하지 않는다. 기존 P8 3파일 정확 소스 PIN, 백업 및 로컬 변경 보호는 그대로 유지한다.

tests/test_ucie_p9_readonly_retest.py: 새 원장 없음, 정상 원장 3워크로드 재시험, 원본 SHA256 재현, 교차 워크로드 회귀, 과거 HOLD 유지, 위조된 네트워크/코드 사용 주장 거부, 기록 위변조 거부 및 출처 범위를 검증한다. CI 성공은 코딩 경로 확인이고 **운영 PC에서 새로운 실증이 발생했다는 뜻은 아니다.**

## 다음

신규 P8 개선 판단이 실제 공개 근거의 자연 유입으로 운영 원장에 생성되기 전에는 실운영 P9 자동재시험이나 채택을 PASS로 선언하지 않는다. 별도 운영 배포와 무인 연결은 정확한 소스 경로·권한을 검증한 뒤 수행한다. 원본 코드 채택 및 규칙 승인/배포는 별도의 명시적 신뢰 근거가 필요하다.
