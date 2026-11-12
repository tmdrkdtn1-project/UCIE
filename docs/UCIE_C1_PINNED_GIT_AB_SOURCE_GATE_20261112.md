# UCIE V3 B3/C1 — 두 검토 완료 Git 커밋 원본 고정 및 독립 Windows 수신 준비

**기준:** 2026-11-12 KST / <https://github.com/tmdrkdtn1-project/UCIE/issues/199>  
**범위:** UCIE 자체 공개 저장소만 사용. 고객 자료·타 프로젝트·외부 wheel 실행/전송 없음.  
**출시 판정:** `UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO`

## 현재 완료된 기술적 사실과 아직 구분할 사항

소유자가 2026-11-12 14:05 KST에 보고한 PR #248 실물 실행 영수증은 **동일 소유자 Windows의 두 임시 venv**에 대해 A 0.1.0 → B 0.1.1 선택, 네 기능 합성시험·Local V04 HTTP 시험, A 복귀, 두 버전 제거가 수행됐음을 나타냅니다. 그때 사용한 A 197개 / B 198개는 소유자 PC의 현 시점 소스에 기반한 임시 QA 패키지입니다. **서로 다른 정식 Git 서명 릴리스**나 **독립 Windows 수신자**라는 증거는 아닙니다.

다음 두 개의 검토된 **UCIE 자체 공개 Git 커밋**을 *이동하지 않는 해시*로 고정했습니다.

| 임시 QA 슬롯 | 전체 커밋 SHA | Git 트리 SHA | 검토된 Python 모듈 수 |
| --- | --- | --- | --- |
| A = `0.1.0` | `171d56d8af155c70d3dd32a62afda87398330e99` | `35e7e796deb83435f58c39b83daa984eb22eb30b` | 182 |
| B = `0.1.1` | `4242ebe7ae112076d9b3560e85b0babb22bbb713` | `7f96f430fb5b2f582dbcda8861968e7363055eb4` | 184 |

B에는 실행 가능한 `customer_installed_health_v01.py`와 이를 사용하는 A/B 수명주기 코드가 실제로 추가되어 있습니다. 각 커밋의 검토된 Python 파일, Git blob SHA1, 바이트 수와 기존 C0 선택 구성품 **23개**를 다음 정적 매니페스트에 고정했습니다.

`docs/UCIE_C1_TWO_PINNED_GIT_TREES_20261112.json`

Git SHA1 객체 ID는 저장소 원본 식별자일 뿐 **서명이나 독립적인 권리·보안 승인 증거가 아닙니다**. 패키지 제작 시에는 개별 파일 바이트를 원본 blob SHA1과 대조하고 생성 wheel의 SHA256/RECORD까지 다시 검사합니다.

### 실제 소유자 PC 소스 차이 — 격리 필요

2026-11-12의 UCIE 브리지 읽기 전용 시험에서 로컬 파일 기준으로 확인한 차이입니다.

- 검토된 B 커밋: **184개 Python 모듈**.
- 소유자 PC: **199개 Python 모듈**.
- 원본 B와 비교해 **20개는 추가**, **5개는 누락**.
- 검토된 파일 중 **75개는 CRLF ↔ LF 줄바꿈 차이만 존재**, **14개는 줄바꿈만으로 설명되지 않는 바이트 차이**.
- C0 핵심 구성품 23개 중 Python 원본 중복을 제외한 **3개에 차이**.
- 기존 소유자 Git 추적 변경 **17개를 삭제·복구·덮어쓰지 않았습니다**. 단순 줄바꿈 차이를 임의 코드 결함으로 판단하지 않습니다.

따라서 현재 작업 폴더의 파일을 그대로 고객 제품 원본이라고 주장하지 않습니다. 새 도구는 소유자의 수정 파일을 복사하지 않고 **해당 Git 커밋에 실제로 저장된 객체**만 사용하도록 고정했습니다.

## 새 구현 기능

`src/ucie_miner/customer_pinned_git_source_v01.py`:

1. 기본 동작은 **UCIE 전용 읽기 전용 원본 차이 보고**입니다. 네트워크·Git 변경·pip 실행이 없습니다.
2. `--probe-git-objects`는 **로컬 Git 객체**만 읽어 두 고정 SHA와 트리의 바이트·Git blob 해시를 재확인합니다. `git fetch`, `git pull`, `checkout`, `reset`은 **절대 자동 수행하지 않습니다**.
3. `--apply`는 별도 소유자 승인 후에만 작동합니다. 두 Git 커밋의 소스 객체가 **이미 로컬에 있을 때**, `git archive`로 실제 검토된 코드만 임시 디렉터리로 읽습니다. 허용되지 않은 파일·심볼릭 링크·누락·변조를 차단하고, Python 표준 라이브러리만 사용해 **QA용 A/B UCIE 자체 wheel** 두 개를 만든 뒤 원본과 RECORD/SHA256을 검증합니다.
4. 오직 첫 번째 프로젝트의 Git 무시 폴더 `D:\UCIE\downloaded\`에 **외부 패키지가 없는** 두 버전 소스 검증용 ZIP을 일회성으로 기록합니다. 기존 파일 덮어쓰기를 금지하며 결과 영수증을 분리합니다. `--verify-bundle`은 그 ZIP을 다시 오프라인 검증합니다.
5. 실행에 필요한 **외부 wheel(cryptography/cffi/pycparser)과 고객 실행·설치 파일은 ZIP에 포함하지 않습니다**. 서명·사용권·독립 Windows 인수는 별도 C2/C3/C4 게이트입니다.

별도의 `.github/workflows/ucie-c1-pinned-git-source-wheels.yml`은 Windows/Ubuntu GitHub CI의 **완전한 UCIE Git 히스토리**를 읽어 A/B 소스 전체와 두 QA wheel을 생성·검증하고, 완성 ZIP이나 외부 패키지를 **업로드·배포하지 않습니다**. 이것은 소유자 PC 작업 트리를 그대로 옮기는 방식과 다릅니다.

## 소유자 PC의 단계별 안전 명령

**1. 읽기 전용 현황 확인:**

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_pinned_git_source_v01
```

**2. 로컬 Git에 검토된 A/B 커밋 객체가 존재하는지만 확인:**

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_pinned_git_source_v01 --probe-git-objects
```

이 문서 작성 시 소유자 Windows 읽기 전용 테스트의 관측값은 **A=false, B=false**였습니다. 검토된 두 커밋 객체가 아직 소유자 로컬 Git에 없는 상황이며 이것은 파일 장애가 아니라 **예정된 안전 차단**입니다.

소유자가 명시적으로 허용하면 다음과 같이 **Git 객체만 가져올 수 있습니다**(현재 이 작업방은 소유자 PC에 실행하지 않았음).

```powershell
git -C D:\UCIE -c gc.auto=0 fetch --no-tags --no-write-fetch-head origin 4242ebe7ae112076d9b3560e85b0babb22bbb713
```

B 커밋의 부모에는 A가 있습니다. 이 호출은 Git 객체 데이터베이스를 변경하지만 작업 폴더를 체크아웃하지는 않습니다. 회사 보안·Git 원격·추적 차이 정책과 승인 범위 내에서만 사용해야 합니다. 원격 서버에서 커밋 해시 직접 가져오기를 거부한다면, 사용자 승인 하에서 `origin main`으로부터 가져오는 대안을 별도로 검토해야 하며 무작정 `pull/reset/clean` 하지 않습니다.

**3. A/B 커밋 모두 객체 검증이 끝난 경우에만 일회성 QA 소스 ZIP 내보내기:**

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_pinned_git_source_v01 --apply
```

입력할 독립 승인 문구:

`EXPORT_UCIE_C1_PINNED_PUBLIC_SOURCE_WHEELS_ONCE`

성공 시 첫 번째 프로젝트 전용 로컬 위치:

`D:\UCIE\downloaded\ucie_c1_pinned_git_ab_first_party_qa_only.zip`

`D:\UCIE\downloaded\ucie_c1_pinned_git_ab_source_receipt_v01.json`

재검증:

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_pinned_git_source_v01 --verify-bundle
```

**금지:** 사용자 운영 DB·현재 .venv·상주 Local V1 서비스·C40·PublicMiner·TaskScheduler·Cloudflare·기존 성공 영수증·09:00 HOLD·타 프로젝트에 변경을 가하지 않습니다. 고객용 실제 설치·권리 검토 없이 ZIP을 외부에 전달하지 않습니다.

## 깨끗한 Windows에서의 **독립 바이트 검증기** (설치·실행 아님)

`scripts/ucie_c1_verify_pinned_ab_qa_bundle_v01.py`는 UCIE 제품, Git,
외부 라이브러리가 **전혀 설치되지 않은 별도의 Windows 실험 환경**에서도
Python 표준 라이브러리만으로 소스 전용 ZIP을 검사할 수 있도록 작성했습니다.

검증기는 **GitHub에서 신뢰 경로로 별도로 취득·검토한 원본 스크립트**
여야 합니다. ZIP에 동봉된 코드나 임의 출처의 스크립트로 자신을 검증하지
않습니다. 스크립트 내부에는 승인된 공개 Git 소스 매니페스트의
SHA256 `f23c50ca7bf6d781b41bd76d109955b8ce91c3179aede594a66d083e617b11e8`
이 고정되어 있습니다.

검증 내용: 정확한 A/B 전체 커밋/트리, A 182개/B 184개 Python 소스,
23개 C0 목록, B 전용 새 기능, 각각의 Git blob 해시, 내부 PEP427
wheel의 모든 RECORD SHA256·파일 크기, 두 wheel 전체 SHA256,
서명·고객 배포 미승인 상태와 외부 vendor 파일 **미포함 여부**입니다.
ZIP을 해제·설치·실행하지 않고 네트워크 접속도 하지 않습니다.

소유자 통제하에 격리된 Windows 시험 PC로 **소스만** 이동한 경우의
확인 명령(실행은 별도 인수 단계에서만):

```powershell
py -3.15 -B .\ucie_c1_verify_pinned_ab_qa_bundle_v01.py --bundle .\ucie_c1_pinned_git_ab_first_party_qa_only.zip
```

여기서 PASS가 나와도 **독립 고객용 전체 제품 설치/네 기능 실제 실행,
고객 PC의 업데이트·롤백·제거, 외부 wheel 재배포 권리 및 서명**은
검증하지 않았으므로 C4/C5 NO-GO를 유지합니다. 새 GitHub CI는
동일한 독립 검증기를 Windows·Ubuntu에서 실제 원본 두 wheel에
적용하지만, 이 사실만으로 **사용자가 관리하는 두 번째 수신 PC에
접속하거나 검사했다는 뜻은 아닙니다**.

## 다음 진짜 출시 게이트

**C1/C4:** 완전한 자체 구성품과 승인된 외부 wheel을 구분·공급한 뒤, 별도 **깨끗한 Windows 수신 PC/VM**에서 온라인 접속 없이 검증·설치·실제 업그레이드·롤백·제거할 것. 여기의 소스 전용 QA ZIP 검증은 C4 PASS가 아닙니다.

**C2:** 외부 패키지 SPDX/SBOM, 라이선스/NOTICE, 공급자 진본성 및 보안 검증. **C3:** 고객별 서명·라이선스·권한. **C5:** 소유자 승인·지정 고객 최종 인수.

**판정: `UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO`.**
