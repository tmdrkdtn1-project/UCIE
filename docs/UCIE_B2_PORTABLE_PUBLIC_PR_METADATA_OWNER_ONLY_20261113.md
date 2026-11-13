# UCIE B2 — 승인 공개 PR 메타데이터 포터블 캡슐 v0.1

## 정확한 사용 범위

PR #258 구현 기능은 UCIE 자체 공개 근거 Stage10/15 → Stage12의 완전하게 연결된 미검증 자료(UNVERIFIED_CANDIDATE_ONLY)만 읽기 전용으로 요약하는 기능입니다. 한 번에 최대 **48개**의 서로 다른 공개 PR 개정 메타데이터를 기존 승인 5개 저장소에서 균형 있게 선택합니다. 수집 총량이 48건인 것처럼 주장하지 않으며 미포함 건수도 명시합니다.

소스에 포함되는 항목: UCIE 후보 해시, 승인 저장소 ID, 정확 공개 PR·merge SHA 참조, 공식 GitHub URL, 공개 근거 SHA256, 분류 코드와 W02 재계산 가능한 엔트리 ID, 미승인·사용권 미확인 표기. PR 제목·본문·패치·원본 코드·로그·개인정보·로컬 경로·의존성 바이너리·타 프로젝트 데이터는 포함하지 않습니다.

## 기존 소유자 PC에서 안전한 확인

공개 메타데이터 **읽기 전용 사전검사만** 수행:

~~~powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.local_public_pr_capsule_v01 --preview-owner
~~~

- 출력은 건수·미포함 건수·예상 SHA256·고객 NO_GO만 포함합니다. JSON 본문을 화면이나 Slack으로 내보내지 않습니다.
- 기존 prepare_verification_handoff와 _checked_handoff가 출처 연결, 중복, 위조 상태를 검증합니다. 불완전하면 캡슐 생성이 차단됩니다.
- 기존 운영 SQLite·Stage10/12/15·공개 마이너·예약 작업·상주 Local V1을 변경하지 않습니다.

소유자가 **별도로 승인**하는 로컬 1회 파일 생성만 허용됩니다. 같은 모듈에 --export-once 옵션을 주고 정확한 문구 UCIE_OWNER_PUBLIC_METADATA_LOCAL_EXPORT_ONCE를 직접 입력해야 합니다. 프로그램은 소유자 기존 Git-무시 디렉터리 D:\UCIE\downloaded 내부에만 O_EXCL로 덮어쓰기 없이 생성합니다. 소유자 저장소 루트나 운영 SQLite 디렉터리에는 쓰지 않습니다.

- downloaded/.ucie_b2_public_pr_metadata_v01.json
- downloaded/.ucie_b2_public_pr_metadata_v01.sha256

소유자 원본 저장소의 기존 .gitignore는 downloaded/ 전체를 무시합니다. 별도 수신 저장소의 루트에 수동 배치하는 정확한 두 파일 이름도 새 .gitignore에 추가했지만, 수신 경로 반입은 별도 소유자 검토·권한이 필요합니다. 파일 생성은 고객 배포나 외부 전달 승인이 아닙니다.

## 별도 검토된 깨끗한 UCIE 환경에서 사용

수신 경로는 정확히 UCIE 디렉터리, 일반 .git 디렉터리, 비어 있는 운영 runtime 원장이 전제입니다. 위 두 파일을 승인된 경로로 직접 배치한 경우 프로그램은 다음을 수행합니다.

1. 두 파일 동시 존재 여부, 크기·심볼릭 링크·JSON 중복 키·SHA256을 검사합니다.
2. JSON의 모든 필드와 승인된 W01 공개 저장소, W02 출처→URL/PR SHA→라이브러리 ID 계약을 재계산합니다. 조작된 승인, 원문 코드 필드, 허용 외 저장소가 있으면 차단됩니다.
3. 기존 /local/error, /local/library, /local/evolution에서 공개 PR **미검증 메타데이터 후보**를 조회합니다. 기존 공식문서·SkillBook 참조 화면은 유지합니다.
4. 서명 없는 이식 후보에는 출처 독립 검증이 없으므로 /local/review의 수동 검토 진입 자체가 차단됩니다.
5. 자동 규칙 반영, 운영 코드 변경, 고객 배포와 최초 수정 포함 릴리스 판정은 하지 않습니다.

**핵심 보안 한계:** JSON과 같은 위치의 .sha256이 일치해도 자기 일관성만 검증합니다. 둘을 함께 바꾸는 공격자에 대한 소유자 서명/독립 원본 인증은 아닙니다. C2 라이선스/보안/NOTICE, C3 개인키 서명·권한, 별도 Windows 수신 기기 C4와 C5 고객 인수가 끝나기 전 상용 배포는 NO_GO입니다.

## 실측 및 회귀 수락 조건

- 소유자 UCIE 현재 공개 원장에서 읽기 전용 사전검사 PASS; 건수 및 SHA만 관측, 파일 내보내기·전송 없음
- 승인 5개 저장소 합성 PR 입력으로 실제 JSON 생성/검색, 48건 균형 선택, 잘못된 소스·변조·위장 승인·중복 차단
- 진짜 임시 127.0.0.1 HTTP에서 문제 예방/도서관/개선 제안 조회, 별도 검토 URL 차단
- GitHub clean Windows Python3.15 새 wheel로 CI 전용 합성 캡슐을 임시 수신 디렉터리에 만들고 실제 GET 3개 및 변조·검토 차단, 기존 공식 참조 GET 8개 유지
- 운영 DB·서비스·스케줄러·C40·다른 프로젝트 변경 없음
