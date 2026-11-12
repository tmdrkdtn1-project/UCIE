# UCIE V3 C2 — 오프라인 외부 의존성 라이선스·SPDX 검토 초안 (2026-11-12)

**범위:** UCIE 프로젝트만. #199 C2의 *증거 확보 도구*이며 법적 승인, C2 보안 검증 PASS, 고객용 배포 승인 또는 표준 SPDX 검증 인증이 아니다. C1의 PR #249에서 검토한 A/B 자체 코드 출처 고정은 유지한다.

## 개발 완료 범위

- 기존 C1의 \`verify_local\`, \`_inspect_wheel\`을 재사용해 공식 PyPI 해시 수집 영수증에 결속된 UCIE 전용 Git 무시 폴더의 **세 가지 고정 외부 wheel**만 오프라인 검사한다: cryptography 50.0.2, cffi 2.1.1, pycparser 3.12.
- 각 wheel SHA256, PEP427 RECORD SHA256/크기, Python/ABI/platform 태그, METADATA의 Requires-Dist, 라이선스 표시문, wheel 안의 License-File/NOTICE 바이트 해시만 추출한다. 서드파티 원문을 공개하거나 실행하지 않는다.
- **SPDX 2.3 초안** 패키지 세 개의 \`NOASSERTION\` 권리/라이선스 상태, purl, wheel SHA256, DOCUMENT-DESCRIBES 관계를 만든다. 표준 검사·배포 권한·공급자 서명 검증을 통과했다는 뜻이 아니다.
- 소유자 권한, 외부 라이선스/NOTICE, 출처 인증 서명, 보안 권고, 종속성 전이 및 플랫폼 호환, 별도 수신 Windows 시험, 고객별 서명/자격은 **항상 미승인 차단**한다. 증거가 부족하거나 영수증/RECORD가 변조되면 읽기 전용으로 실패한다.
- GitHub용 테스트는 UCIE 자체 합성 ZIP 세 개만 생성하며 외부 binary 설치·실행이 없다.

## 사용

기존 \`D:\UCIE\downloaded\ucie_c1_offline_wheelhouse_preview\`와 그 C1 기록이 이미 존재하는 소유자 PC에서만:

\`\`\`powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_c2_supply_chain_review_v01 --inspect
\`\`\`

출력은 JSON이며 \`spdx_2_3_draft_noassertion\` 항목으로 초안 재료를 분리한다. 종료코드 **2**는 증거를 얻었더라도 C2/고객 출시를 차단하기 위한 의도된 결과다. 출력이나 수집 영수증을 독립 공급자 인증·권리 판단 대신 사용하면 안 된다.

## 실제 남은 관문

1. 소유자/기여자와 외부 패키지 원문 라이선스·NOTICE 및 배포 의무를 **사람이 검토**.
2. 알려진 보안 권고를 정확한 공개 버전 및 수신 플랫폼과 대조하고 독립 검사 영수증 확보.
3. 전체 서드파티 전이 종속성, native ABI, 재배포/업데이트 경로를 실제 깨끗한 Windows 수신 환경에서 검증.
4. 고객별 개인 정보 없는 서명·권한 정책과 소유자 승인 후 C3/C4/C5 각각 별도 인수.

**절대 금지:** 고객 비밀, 타 프로젝트, 자동 Rule/SkillBook 승인, 신규 자동 수집, 외부 PyPI 다운로드, 네트워크·pip·프로세스 실행, 운영 DB/예약 작업/C40/Cloudflare/09:00 HOLD 변경, 고객 공개/배포, owner dirty-tree 무단 덮어쓰기.

상태: \`UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO\`.
