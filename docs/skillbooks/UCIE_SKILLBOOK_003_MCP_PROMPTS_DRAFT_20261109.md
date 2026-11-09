# UCIE SkillBook 003 (DRAFT) — MCP prompts/get 입력 오류를 올바르게 구분하기

- **자산 ID:** `UCIE-SKILLBOOK-MCP-PROMPTS-003`
- **버전:** `0.1.0-draft`
- **현재 상태:** `ACTUAL_PINNED_SDK_IN_MEMORY_INTEGRATION_VERIFIED__DEPENDENCY_METADATA_OBSERVED__SKILLBOOK_UNAPPROVED` (PR #225의 실제 SDK 클라이언트·서버 메모리 내 호출 16건 검증, 전체 SDK 보안·권리·고객 승인과 별개)
- **관계 프로젝트:** UCIE만
- **고객용 라이브러리 등록:** 미실시; 현재 V4 UI·홈·개선 제안 구성 변경 없음
- **실제 SDK 전후 회귀시험:** 지정된 두 커밋·두 모드의 메모리 내 통합 호출 검증 완료. **라이선스·의존성 보안 심사, 소유자 승인, 서명, 고객 제공:** 미완료.

> **현재 우선 확인 사항 (2026-11-09):** PR #225에서 실제 MCP SDK를 두 버전으로 설치해 메모리 내 Client↔MCPServer 요청·응답을 검증했습니다. 아래에 보존된 "미수행" 문구는 초안 최초 작성 시점의 검증 이력이며, 최신 판정이 아닙니다. 현재 남은 관문은 의존성·라이선스·보안 검토, 공식 최초 수정 포함 출시 버전, 운영/고객 승인입니다. 독립 감사 보고서: [의존성 메타데이터 검토](../UCIE_SKILLBOOK003_DEPENDENCY_LICENSE_SECURITY_METADATA_20261109.md). `uv.lock` 해시와 배포 패키지 메타데이터 확인만으로는 라이선스 허가나 취약점 없음이 증명되지 않습니다.

## 문제를 이해하는 순서

MCP의 `prompts/get`은 프롬프트 이름과 인수를 받아 내용을 반환합니다. 이름이 등록되지 않았거나 필수 인수가 빠진 것은 **호출자 입력 오류**입니다. 반면 정상 인수를 받은 프롬프트 실행 중 예외는 **서버 내부 실행 오류**입니다. 둘을 같은 오류로 처리하면 클라이언트가 입력 수정과 서비스 오류를 구별하기 어렵습니다.

| 상황 | UCIE 자체 테스트 입력 | 검사할 출력 |
|---|---|---|
| 정상 요청 | `greet(name="Ada")` | `result.messages`와 기대 텍스트 |
| 없는 프롬프트 | `unknown_prompt` | JSON-RPC 오류 `-32602` |
| 필수 인수 빠짐 | `greet(arguments={})` | JSON-RPC 오류 `-32602` |
| 프롬프트 실행 실패 | `explode` | 입력 오류 `-32602`로 오분류하지 않을 것; 다른 실행 오류 코드는 통제군으로만 기록 |

오류 메시지 문구는 버전과 구현에 따라 달라질 수 있으므로 **메시지 문자열만으로 수정 여부를 판정하지 않습니다**. 검사는 JSON-RPC `jsonrpc` 버전, `id` 일치, 결과/오류의 단일 존재, 정수형 코드 및 한정된 검증 시나리오를 확인합니다.

## 승인된 공개 근거의 정확한 고정

| 속성 | 검토된 값 |
|---|---|
| 공식 SDK 저장소 | https://github.com/modelcontextprotocol/python-sdk |
| 원본 문제 | https://github.com/modelcontextprotocol/python-sdk/issues/3669 |
| 수정 PR | https://github.com/modelcontextprotocol/python-sdk/pull/3696 |
| PR 병합 일시 (UTC) | `2026-10-13T09:20:59Z` |
| PR 병합 커밋 | `754254c08fe1c3eda18b69da3d336106fe8d72d6` |
| 수정 전 릴리스 | `v2.3.0`, 2026-10-02 공개 |
| `v2.3.0` 태그 커밋 | `2118f14f8a19bc158d8a1cf90af58d85d187f849` |
| `v2.3.0` PromptManager Git blob | `01a0823bf74c72c2197b846bf94a5f0ff00dfcea` |
| 수정 병합 PromptManager Git blob | `6ad5dfb8c654c2f965c5e25424a588a771e3c858` |
| 수정 전 Prompt.render Git blob | `a13b72f1aa0eb4f15dddc42b4442a4246479cf6b` |
| 수정 병합 Prompt.render Git blob | `32372a527a6e9b7d352b5371d524288342fd99b2` |
| 공식 명세 | https://modelcontextprotocol.io/specification/2025-11-25/server/prompts#error-handling |
| 추가 프로토콜 분기 | `2026-07-28`, PR #3696과 #3669 및 SDK 자체 interaction 테스트의 관측 |
| 최초 수정 포함 *배포판* | `NOT_VERIFIED` |

**정확한 판정 범위:** SDK `v2.3.0` 태그의 `PromptManager.render_prompt()`는 미등록 프롬프트에 `ValueError`를 던지고, `Prompt.render()`는 필수 인수 누락에 `ValueError`를 던집니다. PR #3696 병합본은 두 경우에 `MCPError(code=INVALID_PARAMS)`를 사용하도록 소스를 변경합니다. 변경은 `MCPServer.get_prompt()`에도 반영됐습니다. 이는 **원본 코드 차이 확인**이지 이전/이후 SDK 빌드를 실행한 결과가 아닙니다.

공식 2025-11-25 명세는 두 입력 오류에 `-32602`를 권고합니다. 코드 `-32603`은 일반 내부 오류에 대한 권고값입니다. 2026-07-28 모드는 SDK PR/문제의 출처 연결로만 판정하며 해당 명세 원문을 이번 작업에서 따로 고정·검수하지 않았습니다.

수정 PR 병합이 출시된 것과 동일하지 않습니다. 현재 확인된 공식 릴리스 목록의 최신 항목은 `v2.3.0`이며 PR보다 먼저 공개됐습니다. **미래 또는 다른 배포판에 수정이 포함됐다고 단정하거나, 모든 2.x에서 문제를 재현한다고 일반화하지 않습니다.**

## UCIE가 독립적으로 작성한 재사용 레시피

- 코드: `src/ucie_miner/mcp_prompt_regression_v01.py`
- 함수: `assess_transcript({...})` — `case`, `protocol_revision`, `request`, `response`로 구성된 한정형 JSON-RPC 교환에 대해 *해당 계약만* 판정
- 한정 시나리오: `valid_prompt`, `unknown_prompt`, `missing_required_argument`, `prompt_execution_error`
- 버전 분기: `2025-11-25`, `2026-07-28`
- 최대 한 건 입력: 16,384 UTF-8 bytes. JSON-RPC `id` 값·타입 비교, `result/error` 동시 응답 차단, `code` 정수 확인.
- 반환: `CONTRACT_MATCH`, `CONTRACT_VIOLATION`, `CONTROL_ONLY`, `INPUT_REJECTED_NO_GO`. 임의 응답 메시지나 소스 본문을 반환하지 않음.
- 재현 CLI: 합성 시나리오만 표시하거나 표준입력에서 한 건의 JSON 교환만 판정. 파일 경로·외부 주소·SDK 실행·자동 수정·Git 조작 없음.
- 본 SkillBook은 **MCP SDK의 전체 동작을 보증하는 범용 검사기**가 아닙니다. UCIE가 지정한 합성 프롬프트에 대한 전송 응답 계약만 확인합니다.

### 합성 예제 실행

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.mcp_prompt_regression_v01 --demo
```

고정 기대치: 두 프로토콜 × 네 시나리오 8건 중 직접적인 계약 일치 6건, 입력 오류가 아닌 통제군 2건; 수정 전 오류 코드로 만든 **UCIE 자체 합성 반례** 4건은 계약 위반으로 탐지해야 합니다. 이 수치는 `mcp` 패키지를 실행한 시험 건수가 아닙니다.

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_mcp_prompt_regression_v01.py' -v
```

프로그램 내에서 `assess_transcript()`로 임의의 승인된 `request/response` 교환을 평가할 수 있지만, 호출자가 제공하는 JSON은 **외부에서 받은 신뢰할 수 없는 입력**이므로 크기·형식을 제한합니다. 잘못된 형태는 정상 성공으로 승격하지 않고 실패 상태로 반환합니다.

## 독립 검증과 권리 확인 — 별도 관문

- **수행:** UCIE 작성 JSON-RPC 검사 함수의 합성 정상/반례 시험, 공식 SDK의 두 시점 코드와 릴리스 게시일·PR·Git blob 확인.
- **미수행:** SDK `v2.3.0`과 수정 커밋을 격리된 동일 조건에서 실제 실행하여 응답을 캡처하는 전후 독립 시험. 해당 SDK를 현재 PC에 설치하거나 비신뢰 원본 코드를 실행하지 않음.
- **미수행:** 2026-07-28 명세 원문의 별도 버전 고정, 최초 수정 포함 배포판 확인, 공급망 종속성·서명·독립 보안 검토, 예제의 고객 환경 적용성 검증.
- **권리 출처:** SDK `v2.3.0`의 공개 `LICENSE`는 MIT이며 `Copyright (c) 2024 Anthropic, PBC` 표기가 있습니다(공식 원본 https://github.com/modelcontextprotocol/python-sdk/blob/v2.3.0/LICENSE , Git blob `3d48435454b105021b4f777c11b6b07d8d2ffea3`). **이 사실은 해당 PR의 모든 기여자·의존성·재배포 권리에 대한 법률 검토 완료가 아닙니다.** UCIE는 상기 코드 조각을 복제하지 않고 원본 근거만 링크했습니다.
- **릴리스:** `human_approved=false`, `independent_upstream_verified=false`, `license_redistribution_approved=false`, `signed=false`, `published=false`, `export_allowed=false`.
- **기존 4대 기능:** V4 홈·개선 제안 디자인, 기존 도서관의 승인된 SkillBook 001/002, 소스 허용 목록, 로컬 웹서버·수집 DB·예약 작업·클라우드 설정 모두 변경하지 않습니다.

## 다음 실제 검증 관문 (우선순위 유지)

1. 별도 승인된 일회용 샌드박스에서 **정확한 SDK `v2.3.0` 및 PR 병합 SHA**를 같은 테스트 계약으로 비교 실행. CPU·시간·네트워크 제한, 격리, 권리 검토와 원본 실행 허용 여부가 선결 조건입니다.
2. 두 프로토콜 모드에서 정상·미등록·필수 인수 누락·실행 오류에 대한 실제 응답 코드를 증거로 기록.
3. 공급망/라이선스 검토와 출처·버전별 결과를 독립 리뷰한 뒤에만 SkillBook 및 고객용 지식 반영 여부를 별도 승인합니다. 기존 001/002 또는 PR #3696 기반 기존 근거 개정 2건을 중복 규칙으로 자동 등록하지 않습니다.

이 초안의 출처·소스 검증과 UCIE 자체 합성 시험은 사실대로 보고하되, **실제 SDK 독립 동작 PASS·규칙 승인·출시 GO로 치환하지 않습니다.**

## 2026-11-09 — 선별된 공식 SDK 함수 경로의 격리 실행 기록

- **유형:** `PINNED_UPSTREAM_METHOD_PATHS_OBSERVED`, 전체 SDK 통합시험 아님.
- **UCIE PR:** https://github.com/tmdrkdtn1-project/UCIE/pull/224
- **일회용 CI 실행:** https://github.com/tmdrkdtn1-project/UCIE/actions/runs/42582727640
- **공식 원본:** SDK `v2.3.0` 태그 커밋 `2118f14f8a19bc158d8a1cf90af58d85d187f849`과 PR #3696 병합 커밋 `754254c08fe1c3eda18b69da3d336106fe8d72d6`.
- **검증 파일:** 두 시점의 `PromptManager`와 `Prompt.render` 원본 파일 4개를 각각 Git blob SHA-1 전체 일치 확인. 미등록 이름·필수 인수 누락·정상 인수 검사·합성 프롬프트 예외 등 시점별 4개씩 8개 **선택된 함수 경로** 실행 성공.
- **변경 전:** 미등록/인수 누락 모두 `ValueError`.
- **변경 후:** 미등록/인수 누락 모두 `MCPError(-32602)`; 정상 인수 유효성 통과, 합성 프롬프트 예외는 `RuntimeError`로 유지.
- **엄격한 제한:** 원본 SDK 모듈 import 없음, `Client`·`MCPServer` 통신·JSON-RPC 프레이밍·전체 `Prompt.render` 메시지 생성/전달을 실행하지 않음. `MCPError` 객체는 UCIE가 작성한 최소한의 예외 스텁이며, 실제 SDK 의존성도 설치하지 않음. GitHub-hosted Linux 임시 실행기에서만 허용된 AST 경로 실행.
- **제품 의미:** SkillBook의 *소스에 기반한 동작 설명*에 사용할 보조 증거는 확보했지만, 전체 SDK 독립 QA 인증·최초 수정 포함 배포판·권리/보안 승인·고객 제공 가능 여부는 여전히 `NOT_VERIFIED` 또는 `NO_GO`. 이 문서를 기존 가상도서관에 승인된 세 번째 제품으로 자동 등록하지 않음.

## 2026-11-09 — 실제 설치한 SDK 클라이언트·서버의 메모리 내 통합시험

- **실제 실행 영수증:** https://github.com/tmdrkdtn1-project/UCIE/actions/runs/42584866664
- **UCIE 개발 PR:** https://github.com/tmdrkdtn1-project/UCIE/pull/225
- **실험 대상:** 승인 공식 `modelcontextprotocol/python-sdk`의 `v2.3.0` 태그 커밋 `2118f14f8a19bc158d8a1cf90af58d85d187f849`과 PR #3696 병합 커밋 `754254c08fe1c3eda18b69da3d336106fe8d72d6`. 해당 원본의 Git 커밋/잠금 파일/핵심 코드 SHA 확인 후, 각 시점의 잠금 의존성으로 일회용 Linux 가상환경에 **실제 SDK 설치 및 Import**.
- **범위:** 원본 SDK `Client`↔`MCPServer`의 메모리 내 요청·응답. `legacy`(구형)·`2026-07-28`(신형) 모드별 정상 `greet`, 없는 프롬프트, 필수 인수 누락, 프롬프트 예외 **각 4건, 시점별 8건, 총 16건**.
- **직접 관측:** 수정 전 없는 프롬프트/필수 인수 누락은 구형 `0`, 신형 `-32603`; 수정 후 두 모드 모두 `-32602`. 정상 요청은 `Hello, Ada` 성공, 실행 오류 통제군은 수정 전후 구형 `0`, 신형 `-32603`으로 유지. 상세 보고서 `docs/UCIE_MCP_FULL_SDK_INTEGRATION_QA_20261109.md`.
- **정확한 버전:** 수정 전 배포판은 `mcp==2.3.0`; 수정 후 시험 환경 패키지의 버전 문자열은 `2.3.1.dev9+754254c`이며 **커밋에서 빌드한 개발버전, 공식 출시는 아님**.
- **새로 통과한 관문:** `ACTUAL_PINNED_SDK_CLIENT_SERVER_IN_MEMORY_VERIFIED` (제한 범위). 앞선 1차 합성 JSON 검사 및 원본 함수 경로 실행보다 높은 수준이지만, **HTTP/stdio 전송·전체 upstream 테스트·다른 버전의 독립 검증·라이선스/보안·공식 첫 수정 포함 릴리스 확인은 미완료**.
- **권리 상태:** 원본 저장소 MIT 표시와 각 시점 `uv.lock`로 설치한 런타임 종속성 확인은 증거이지 개별 의존성 권리/보안 검토 완료가 아닙니다. 자동 규칙 승격, 외부 배포, SkillBook 최종 승인, 고객 서비스 적용은 여전히 금지합니다.

## 2026-11-09 — 실제 의존성 메타데이터 검토 (P2, 승인 전)

- **공식 잠금 파일 재검증 및 실제 설치 목록:** `v2.3.0` 134개 잠금 항목 중 실제 설치된 배포 패키지는 30개. 수정 커밋 잠금 항목 138개 중 실제 설치 패키지도 30개. 134/138은 **전체 환경·개발 의존성을 포함한 잠금 파일의 항목 수**로, 사용자가 설치하는 패키지 수가 아닙니다.
- **30개 실제 설치 배포 패키지의 버전 및 등록 출처**를 각 원본 잠금 파일과 대조했습니다. 양쪽 결과 모두 SPDX 라이선스 표현 메타데이터 25개, 기존 `License` 필드 4개, 분류 표시만 1개입니다. 불확실성은 법적 허가 여부가 아닌 *표기 형식* 기준입니다.
- **추가 검토할 패키지:** `annotated-types==0.7.0`, `h11==0.16.0`, `pycparser==2.23`, `mcp`, `mcp-types` (후자 두 패키지는 각 시험 시점 버전별).
- **실제 시험 기록:** https://github.com/tmdrkdtn1-project/UCIE/actions/runs/42587044200
- **상세 감사 문서:** [공식 잠금 설치 의존성·라이선스·보안 관문](../UCIE_SKILLBOOK003_DEPENDENCY_LICENSE_SECURITY_METADATA_20261109.md)
- **공식 SDK 보안 권고는 공개 목록으로 별도 검토**했으나, 30개 패키지 전체의 취약점 전수 검사는 실행하지 않았습니다. `v2.3.0`에 알려진 결함이 없다고 인증할 수 없습니다.
- **법적·보안·고객용 결정:** `LICENSE_REDISTRIBUTION=NOT_APPROVED`, `DEPENDENCY_SECURITY=NOT_VERIFIED`, `human_approved=false`, `export_allowed=false`, `published=false`, `customer_release_authorized=false`. 보안·권리 검토 완료로 간주하지 않으며 자동 승격하지 않습니다.
