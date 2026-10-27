# UCIE W07 + W09 — 검증된 기존 Rulepack 서가와 독립 소비자 설명서 (2026-10-27)

## 1. 실제 사용자 Windows W08 실험 기록

UCIE 자체 작성 합성 조회 엔진 실행 영수증(사용자 직접 제공):

| 측정 | 관측값 |
|---|---:|
| 실험 ID | `UCIE_LIBRARY_EXACT_KEY_INDEX_EXPERIMENT_V1` |
| 합성 항목 및 조회 | 1,536건 / 48회 (성공 조회 42, 없는 키 6) |
| 측정 반복 | 3 |
| 검색 결과 일치 | **48/48, 불일치 0** |
| 기준선 순차 검색 | 73,728회 비교, 실행시간 중앙값 6,409,500ns |
| 인덱스 생성 + 조회 | 1,584회 합산 연산, 실행시간 중앙값 218,100ns |
| 개선 비교량 | 72,144회 감소(약 97.85%) |
| 관측 시간 비율 | 약 29.39배 (해당 합성 실험에만 적용) |
| 자료 SHA256 | `cd68799042a9c6c57b15100947541f16731d4cfd18efe6088db85264e92227f7` |
| 운영 적용·실사용 데이터 검증 | **미수행** |
| DB/네트워크/모델변경·자동승격 | 0 / 0 / false / false |

이 수치는 **사용자가 실제 PC에서 실행한 UCIE 자체 합성 알고리즘 비교 관측**이다. 현실의 도서관 검색 속도, 승인된 외부 기술의 성능, 신규 스킬 생산, 운영 시스템 개선 성공으로 확대 해석하지 않는다. 원본 운영 DB나 다른 프로젝트의 자료를 사용하지 않았으며, 이 문서화는 자동 영구 학습/모델 가중치 갱신이 아니다.

## 2. 실제 W07 코드 — 기존 서명 패키지 서가

모듈: `src/ucie_miner/signed_rule_library.py`

새로운 서명/검증 체계 대신 기존 구현을 **매 조회 시 그대로** 재사용:

- `verify_mixed_owner_release`: 소유자가 수동 승인한 기존 **Serial4 (4규칙)** ZIP, 공개 신뢰키, 원본 규칙 순서, 범위, SHA 및 만료 검증.
- `verify_fifth_addendum`: 별도 수동 서명한 **Serial5 다섯째 규칙 추가분**을 기존 Serial4 부모 ZIP과 함께 검증. 부모 ZIP SHA256 결속·동일 신뢰키·일주일 만료 조건 등 **기존 검증기에 이미 존재하는 검사만** 재사용.
- 원래 원본 서명 패키지 bytes는 수정하지 않고 rule ID, pack serial, SHA256 및 `OWNER_RISK_ACCEPTED_CI_ONLY` 승인 **근거 수준**을 출력. 독립 QA·법적 라이선스 서명은 **없음**으로 명시.
- 원본 서명 PACK이 실제 검증되지 않으면 단 한 건의 **'signed' Library 항목도 만들지 않음**. Stage12 미검증 PR/6·7번째 미서명 후보를 서명 서가에 포함하지 않음.
- 소유자가 제공한 **UCIE 내부의 서명 ZIP 경로와 공개 trust 키 경로만** 검증. 임의 사용자 프로젝트 파일·외부 앱·비공개 소스/서명 개인키·네트워크 접근 금지.
- 만료된 기존 패키지는 조회 시 서명 서가에서 **거부**. 과거 서명이 있었다는 기록과 현재 유효하다는 판단을 구분.

## 3. W09 초기 기능 — 소비자 설명서 (신규 Rulepack 발행 아님)

`build_existing_pack_consumer_descriptor`는 같은 서명 검증기 통과 후 **기존 팩의 SHA256, 직렬번호, rule ID, 명시된 수동 소비 범위, 불충분한 독립 QA/라이선스 확인** 정보를 읽기 전용 JSON으로 제공. 새로운 ZIP 제작·서명·자동 배포·타 프로젝트 코드 읽기·스킬 엔진 실행 기능은 포함하지 않는다.

**이 설명서는 출시 가능한 범용 스킬/엔진 패키지가 아니다.** W09 전체 개발 완료가 아니라 기존 서명 규칙의 버전 고정된 독립 소비 계약을 안내하는 작은 첫 단계이다.

## 4. 실행방법 (실제 UCIE 경로만 사용)

명령 예시에서 사용자가 **기존에 보유한 실제 UCIE 서명 파일 경로**를 변수에 넣는다. 임의 파일명·키 경로를 추측하거나 개인키를 입력하지 않는다.

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
$py = 'D:\UCIE\.venv\Scripts\python.exe'
$serial4 = '<실제 UCIE Serial4 서명 ZIP 전체 경로>'
$publicTrust = '<실제 UCIE 소유자 공개 trust PEM 전체 경로>'
$serial5 = '<실제 UCIE Serial5 추가 서명 ZIP 전체 경로>'

# 4개 서명 규칙: 원본 서명·만료·트러스트 검증 (GET0, DB 쓰기0)
& $py -B -m ucie_miner.signed_rule_library --ucie-root 'D:\UCIE' --serial4-pack $serial4 --owner-public-trust $publicTrust

# 기존 4+1 서명을 묶어 조회 (Serial5 추가분은 Serial4 SHA까지 다시 확인)
& $py -B -m ucie_miner.signed_rule_library --ucie-root 'D:\UCIE' --serial4-pack $serial4 --serial5-pack $serial5 --owner-public-trust $publicTrust

# 새 서명 팩이 아닌 버전 고정 참조 설명서 조회
& $py -B -m ucie_miner.signed_rule_library --ucie-root 'D:\UCIE' --serial4-pack $serial4 --owner-public-trust $publicTrust --descriptor
```

별도 네트워크 요청/운영 데이터 변경/자동 승격은 없으며, 실제 서명 ZIP과 신뢰키를 찾는 행위는 소유자의 UCIE 로컬 권한 내에서만 실시한다.

## 5. 개발 중 상태·다음 개발 묶음

- **W07**: 기존 서명 패키지의 실서명 검증 후 검색 서가 — 이번 개발. 독립 QA/라이선스 확인을 자동 추론하지 않음.
- **W09**: 기존 서명 규칙 기반 읽기 전용 소비 설명서 — 첫 기능만 구현. 범용 스킬·학습 엔진 패키징 및 대외 배포 미완료.
- **P8**: W08처럼 UCIE 자체 실기 경험을 정규화·버전 계보로 연결. 지금은 영수증·문서만 있고 운영 원장 자동 기록/안전한 재평가·자동개선 루프 미완.
- **P9**: 통합 제품 불완성. 원본 signed Rulepack 파일 및 운영 수집기·DB·스케줄러·6/7 미서명 후보 그대로 보존.

근거/시험: `tests/test_ucie_w07_w09_signed_library.py`의 **UCIE 자체 임시 Serial4 서명 패키지 실제 생성/원본 검증 및 새 설명서 조회**, 불법 경로·개인키·다른 trust 키·만료·위조 ZIP 거부, Serial5 원본 검증기 호출 경계. 원래 Serial5 실제 암호학적 시험은 기존 `tests/test_ucie_fifth_owner_addendum.py`를 재사용; 중복 개발 안 함.
