# UCIE P9 최종 인수 중 Serial5 원본 모듈 복구 및 호스트 사전시험 (2026-10-28)

## 이미 관측된 실제 소유자 PC 결과

- `python -B -m ucie_miner.product_v1 --ucie-root D:\UCIE --query API_CONTRACT --limit 5`: 정상 읽기 전용 통합 응답, 연결 공개 후보 **390**, Stage14 공식 메타데이터 **824**.
- `--demo`: UCIE 작성 엔진·스킬·피드백의 합성 알고리즘 3종 정확 출력 동등성, portable 검색 데모 정확. 외부 PR 구현을 실행·검증한 것은 아님.
- P8 원래 SHA 계보 경험 **2건**, W05 공개 후보 연결 경험 **0건**. 운영 DB 쓰기0, 네트워크0, 서명0.
- `v1_accepted=false`: 단일 진입점의 로컬 정상 실행은 확인됐지만 서명팩 실검증·독립 QA·릴리스 권한은 확인되지 않음.

## Serial5 복구

초기 P9 import 크래시 `ModuleNotFoundError: ucie_public.fifth_owner_addendum`는 PR #117의 선택적 서명 검증 지연 로딩으로 일반 P9 조회/데모 실행을 복구했다. 추가로 실제 로컬에 누락되어 있던 **UCIE GitHub main 원본** `src/ucie_public/fifth_owner_addendum.py`를 신규 파일 ABSENT SHA lease로 정확히 복구하였다. 의존 `src/ucie_miner/static_asyncio_resource.py`는 로컬에 존재. 기존 원본 파일·운영 원장·서명팩·개인키·스케줄러는 변경하지 않았다.

## 현재 배치 테스트

`tests/test_ucie_p9_serial5_host_preflight.py`는 다음 세 개만 검증한다.

1. 실행 중인 Python 환경에서 `ucie_public.fifth_owner_addendum`, `ucie_miner.signed_rule_library`, `ucie_miner.static_asyncio_resource`를 **실제로 import**하고 Serial5 Rule ID/검증 함수가 서로 결속돼 있는지 확인.
2. 임시 UCIE 합성 디렉터리의 **없는** Serial4 ZIP·공개 신뢰 키·Serial5 ZIP에 대해 원래 검증기가 반드시 실패하는지 검사. 실제 소유자 서명팩·키 접근 없음.
3. 서명팩 없이 통합 P9 `--demo`가 작동하고 서명 검증을 했다고 거짓 보고하지 않으며, API 요청·운영 DB·P8 경험 원장 기록이 없는지 검사.

이 시험은 **모듈 존재·경계 검증**일 뿐, 실제 소유자 Serial4/5 pack의 현재 유효기간/서명/법적 라이선스/독립 QA 검증이 아니다. 패키지 배포·자동승격/재서명/모델 가중치 변경 없음.

## 소유자 Windows에서 단 한 번 읽기 전용 시험

```powershell
$env:PYTHONPATH='D:\UCIE\src'
$py='D:\UCIE\.venv\Scripts\python.exe'
& $py -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_p9_serial5_host_preflight.py' -v
```

출력에서 `Ran 3 tests` / `OK`는 호스트 의존성 사전시험만 PASS. 원래 Serial4 ZIP과 owner **공개** trust key 및 (선택적) Serial5 addendum의 실제 경로가 정확히 확인됐을 때만 `ucie_miner.signed_rule_library`의 기존 read-only 검증 CLI로 현재 효력을 평가한다. **경로/키 추측·원본 수정·새 서명은 금지.**

### 최종 분리 판정

- P9 자료 검색/경험/UCIE 자체 합성 실기: 실호스트 정상 관측.
- P9 Serial5 원본 import: 본 테스트의 실제 소유자 호스트 결과 수령 전 **미관측**.
- 실제 서명팩의 현재 신뢰·유효기간: **미관측**, 서명 갱신 없음.
- 독립 소비 QA: GitHub 격리 Python 테스트는 PASS지만 별도 독립 QA 서명은 미완.
- 소스 배포 사용권: UCIE GitHub 루트에서 `LICENSE` 파일을 찾지 못했고 `pyproject.toml`에도 라이선스 메타데이터가 없음. 코드 소유자와 배포 사용권을 자동 추정하지 않음.
- `UCIE_V1_ACCEPTED=false` 유지.

W05 공개 PR 제목 0건 추가 조사는 당장의 통합 릴리스를 막는 문제의 해결책이 아니므로 반복하지 않는다.
