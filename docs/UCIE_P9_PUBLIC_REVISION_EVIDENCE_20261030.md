# UCIE P9 — 공개 PR·라이선스·릴리스 계보 직접 확인 (2026-10-30)

- 범위: 공개 승인 저장소 `python/cpython`, `PowerShell/PowerShell`만.
- 자료: 정확한 GitHub PR 병합 메타데이터, 병합 커밋에서 읽은 저장소 루트 라이선스 파일, 비교 대상 공개 릴리스 태그의 실제 커밋 SHA 및 Git compare 결과.
- 재현 출처: 아래 모든 `github.com` URL은 승인된 공개 저장소 자체의 원본이다.
- 판정 강도: **저장소 수준 LICENSE 파일 존재·계보 관측**. 개별 변경 코드의 라이선스 적합성 법률 검토도 아니고, 수정된 버전이 실제로 배포·실행됐다는 증거도 아니다.
- 외부 소스 원문/패치/리포지토리 대량 수집 없음. 자동 규칙 승격·배포·운영 DB 기록 없음.

| 공개 PR (병합 UTC) | 병합 SHA | 해당 SHA의 루트 LICENSE Git blob | 비교한 출시 태그 및 SHA | Git 비교 |
|---|---|---|---|---|
| [CPython #153462](https://github.com/python/cpython/pull/153462) (2026-08-21T17:02:24Z) | `999a046b24cff4ba0e72b574196721f66bd08237` | [LICENSE](https://github.com/python/cpython/blob/999a046b24cff4ba0e72b574196721f66bd08237/LICENSE): `20cf39097c68baa17cc566b64e76d34ebf034044` | [v3.15.0](https://github.com/python/cpython/releases/tag/v3.15.0): `d220409a13b77de7a6c30abe16ea90db01528edc` | diverged; merge base `f31a89bb901067dd105b00cfa90523cf7ffdbbdd`; ahead 1225 / behind 1556 |
| [PowerShell #28042](https://github.com/PowerShell/PowerShell/pull/28042) (2026-10-09T16:35:49Z) | `bd8cb01a7d5b86129c45eaa14ab5830a63b1283f` | [LICENSE.txt](https://github.com/PowerShell/PowerShell/blob/bd8cb01a7d5b86129c45eaa14ab5830a63b1283f/LICENSE.txt): `b2f52a2bad4e27e2d9c68a755abb74cb8943f2fa` | [v7.6.6](https://github.com/PowerShell/PowerShell/releases/tag/v7.6.6): `f260eb9c31ec72c5282f98e5ea24d9be4f8d7536` | diverged; merge base `8a723f8b19ed5ae387aaf1a8cc106d6111dee6f1`; ahead 207 / behind 425 |
| [PowerShell #28087](https://github.com/PowerShell/PowerShell/pull/28087) (2026-10-09T17:21:35Z) | `373f6a7b7972a0a4b73bfd9737a0d768d28b347e` | [LICENSE.txt](https://github.com/PowerShell/PowerShell/blob/373f6a7b7972a0a4b73bfd9737a0d768d28b347e/LICENSE.txt): `b2f52a2bad4e27e2d9c68a755abb74cb8943f2fa` | [v7.6.6](https://github.com/PowerShell/PowerShell/releases/tag/v7.6.6): `f260eb9c31ec72c5282f98e5ea24d9be4f8d7536` | diverged; merge base `8a723f8b19ed5ae387aaf1a8cc106d6111dee6f1`; ahead 207 / behind 428 |

## 라이선스 관측

- CPython 병합 SHA의 저장소 LICENSE에는 Python Software Foundation License Version 2가 포함되며, 일부 배포 구성 요소에 별도 라이선스가 있을 수 있다. *개별 PR의 코드/자료 반출 승인으로 자동 변환 금지.*
- PowerShell 병합 SHA들의 루트 `LICENSE.txt`는 MIT License 텍스트를 포함한다. *저장소 루트 라이선스 관측만으로 개별 제3자 코드/의존성의 권리 검토 완료 주장 금지.*
- 표에 적힌 40자리 `blob` 해시는 **Git blob ID**이며 SHA-256으로 호칭하거나 법적 서명이라고 표현하면 안 된다.

## 버전 계보 해석

- 비교 요청: `GET /repos/{owner}/{repo}/compare/{exact_merge_sha}...{exact_tag_commit_sha}`.
- 모두 `diverged`이므로 해당 병합 SHA가 비교 출시 태그의 조상이라는 근거가 없다.
- 그 자체로 **백포트가 없거나 수정이 출시 버전에 없다는 사실을 입증하지 않는다**. 같은 코드가 다른 커밋으로 들어갔을 가능성, 기능별 파일 diff, 출시 아티팩트 실행·회귀시험은 별도의 검증 문제이다.
- 따라서 세 건 모두 `release_contains_fix_verified=false`, `absence_of_backport_verified=false`, `affected_runtime_version_verified=false`.

## 제품 연계

`src/ucie_miner/p9_pinned_public_review.py`는 정확한 `source_id + PR URL + merge SHA`가 모두 맞을 때만 관측 근거를 반환한다. P9의 기존 `source_version_rights_qa_readiness.rows`에 `pinned_public_revision_review`를 추가하지만 원장의 `UNVERIFIED_CANDIDATE_ONLY` 및 `NOT_ATTESTED_PER_REVISION`을 유지한다.

이 기록은 **일부 공개 증거 확인의 제한된 첫 단계**이다. 새 출처 허용, 자동 법률 판단, 독립 QA 완료, 운영 데이터 변경, 자동 승격, 패키지 배포, V1 인수 승인이 아니다.


## PR #28087 — 출시 태그의 실제 수정 대상 파일 비교 (추가 확인)

단순 Git merge 계보가 아니라 **같은 파일의 두 고정 커밋 원문**을 읽어 비교했다.

- 수정 PR: [ResolvePathCommand.cs @ merge 373f6a7](https://github.com/PowerShell/PowerShell/blob/373f6a7b7972a0a4b73bfd9737a0d768d28b347e/src/Microsoft.PowerShell.Commands.Management/commands/management/ResolvePathCommand.cs)
  - Git blob ID `e6a89e2a11732dfc0ed36af8194432155265486c`
  - `StartsWithRelativePathToken` 도우미 함수와 새 조건 호출 **있음**
- 출시 태그: [ResolvePathCommand.cs @ 7.6.6 tag commit f260eb9](https://github.com/PowerShell/PowerShell/blob/f260eb9c31ec72c5282f98e5ea24d9be4f8d7536/src/Microsoft.PowerShell.Commands.Management/commands/management/ResolvePathCommand.cs)
  - Git blob ID `3d1b66933d26f5e55632184e0981c67771c4d853`
  - `StartsWithRelativePathToken` 도우미 함수 **없음**, 이전의 `!adjustedPath.StartsWith('.')` 조건 **있음**

**허용되는 결론:** PR #28087의 *특정 소스 구현*은 검사한 PowerShell 7.6.6 태그 소스 파일에 포함되지 않았다.

**허용되지 않는 결론:** 다른 백포트 구현이나 대체 수정이 전혀 없다 / 7.6.6 바이너리에서 결함이 반드시 재현된다 / 수정이 포함된 첫 릴리스가 무엇이다 / 해당 PR의 코드 반출이 승인됐다. 해당 항목은 별도 공개 소스 및 재현 근거가 필요하다. 외부 소스 코드는 UCIE에 복사하지 않았으며 위 비교는 코드 실행이 아니다.

제품 조회에서는 정확한 `source_id=repo:PowerShell/PowerShell`, `PR URL=#28087`, `merge SHA=373f6a7...`가 모두 일치할 때에만 이 한정 판정을 표시한다. 원장/패키지/승인 상태는 변경하지 않는다.


## PR #28087 — 공식 PowerShell 7.6.6 릴리스 바이너리 직접 실행 (추가 확인)

이전의 소스 비교와 구분하여 공식 **7.6.6 Linux x64 릴리스 바이너리**를 SHA-256으로 검사한 뒤, UCIE 소유 합성 `Resolve-Path -Relative` 재현 스크립트를 일회성 격리 GitHub Actions에서 실행했다.

- 공식 릴리스: [PowerShell/PowerShell v7.6.6](https://github.com/PowerShell/PowerShell/releases/tag/v7.6.6)
- 공식 아티팩트: [powershell-7.6.6-linux-x64.tar.gz](https://github.com/PowerShell/PowerShell/releases/download/v7.6.6/powershell-7.6.6-linux-x64.tar.gz)
- 릴리스 게시 SHA-256 (다운로드 원본과 **일치**): `ddbc4a2d113bbd46d283cfedcbcd117a70caefd7673f41f2b4e0000badf103bc`
- 격리 환경에서 실행한 `pwsh` 파일 SHA-256: `3c6e4d629571429cf6cc86db94278e2ce17349edbbfe0a0de007bb6bccdbc208`
- 실제 확인 버전: `7.6.6` / 플랫폼: `Ubuntu 24.04.5 LTS, Linux x64`
- 원본 실행 결과: `.directory`와 `..directory` 케이스 모두 예상 경로와 **불일치**, 일반 `directory` 케이스 **일치**
- UCIE 기존 안전 함수 `Resolve-UCIESafeRelativePath`: 3개 케이스 모두 예상 결과 일치
- GitHub Actions CI 영수증: [Run 40994655459, Job 123864860275](https://github.com/tmdrkdtn1-project/UCIE/actions/runs/40994655459/job/123864860275), 정확한 커밋 `c8cf6335cd1cbb9b10d9ff39a405d64ced9c39cd`, 첫 런타임 검증 단계 **success**
- 출력 상태: `UCIE_PS_766_PINNED_RELEASE_BINARY_DOTPATH_OBSERVATION_V1` / `DOT_PREFIX_BUG_OBSERVED_ON_RUNNER` / `dot_prefix_cases_matching_expected=0`.

**판정:** 공식 해시가 일치하는 **PowerShell 7.6.6 Linux x64 실제 바이너리에서 PR #28087 관련 점 접두어 상대 경로 결함이 재현됐다.** 앞 절의 동일 소스 비교와 합쳐 해당 출시·플랫폼의 취약 동작 관측을 강화한다.

**Linux 검증 시점에 미확인:** Windows용 7.6.6 릴리스 바이너리의 동작(아래 Windows 공식 바이너리 후속 검증으로 확인), 그 뒤 어떤 릴리스에서 고쳐졌는지, 다른 백포트·대체 구현의 존재 여부, 모든 환경에서의 수정 포함 여부, 독립 QA 및 법적 승인, 제품 배포. 실제 원본 PowerShell 바이너리는 사용자 PC나 UCIE 운영 서버에서 실행하지 않았고 임시 CI에서만 실행했다. 운영 DB·스케줄러·승인 상태·자동 규칙 승격을 변경하지 않았다.

이 검증에서 사용한 프로그램은 공식 공개 배포 아티팩트이지만 다운로드 단계까지 외부 코드는 신뢰하지 않으며, 게시된 릴리스 SHA-256 검증을 통과한 다음 격리 CI에서만 실행했다. 게시 SHA-256의 일치가 코드 서명이나 독립 출처 인증을 대체하지는 않는다.

## PR #28087 — Windows x64 7.6.6 공식 출시 바이너리 직접 재현 (추가 확인)

Linux 근거를 반복하지 않고, **공식 Windows x64 ZIP의 SHA-256을 검증한 후 실제 Windows GitHub Actions 호스트에서 UCIE의 기존 합성 경로 시험을 실행**했다.

- 공식 출처: [PowerShell/PowerShell v7.6.6](https://github.com/PowerShell/PowerShell/releases/tag/v7.6.6)
- 릴리스 ZIP: [PowerShell-7.6.6-win-x64.zip](https://github.com/PowerShell/PowerShell/releases/download/v7.6.6/PowerShell-7.6.6-win-x64.zip)
- 릴리스에 게시된 ZIP SHA-256: `02fe458be20493fbdf43f61ea20610b811ee6c738ab1676c61b9cfcd1a33c860`, 다운로드 ZIP과 정확히 일치
- 실제 격리 실행 `pwsh.exe` SHA-256: `bfb46af89433268872ddb43d1ca7a3f433452ee91ed356a9786940f90118e285`
- 실제 실행 버전: PowerShell `7.6.6`; Windows x64 `Microsoft Windows 10.0.26100`
- 정확한 UCIE 실행 증거: [Run 40995356035 / Job 123867089278](https://github.com/tmdrkdtn1-project/UCIE/actions/runs/40995356035/job/123867089278), PR 헤드 `b4452971a0975a6049adbfb9cc1e91d8c83a9958`, 검증 단계 `success`
- 동작: 일반 `directory` 케이스는 정상. `.directory`, `..directory`는 원래 `Resolve-Path -Relative` 결과가 예상과 다름 (`dot_prefix_cases_matching_expected=0`).
- 기존 UCIE 안전 경로 처리 함수: 세 케이스 모두 예상 결과와 일치. 시험 실행 성공은 승인이나 수정 코드 포함을 의미하지 않음.

**검증 결론:** PowerShell **7.6.6 Windows x64 및 Linux x64 공식 릴리스 바이너리 양쪽에서** PR #28087 관련 점 접두어 상대 경로 동작 결함을 재현했다. 파일 해시와 출력값은 원격 CI 영수증으로 확인된다.

**여전히 확인되지 않은 범위:** ARM64/x86, 실제 사용자 운영 PC, 이후 버전에서의 해결 여부 및 첫 수정 출시 버전, 대체 백포트 구현, 독립 QA/권리 검토, 자동 승인·배포·학습 효과. ZIP의 릴리스 SHA-256 일치는 서명이나 별도의 공급망 인증이 아니며, 이 바이너리는 격리된 공식 CI 호스트에서만 실행됐다. 사용자 로컬 저장소·운영 DB·스케줄러에는 쓰지 않았다.

재실행을 줄이기 위해 임시 원샷 CI 트리거는 검증 후 제거하고, UCIE 작성 검증 스크립트와 정확한 SHA·CI 영수증만 보존한다.
