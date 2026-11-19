# UCIE — Universal Coding Intelligence Engine

**Release target (owner instruction, 2026-11-07): complete four-pillar UCIE product for specifically designated customers under a private proprietary commercial license — NOT a standalone first rule or an open-source/public package release. Current readiness: INCOMPLETE / commercial production NO-GO.**

This PUBLIC repository is a development surface, not a customer download channel. No customer identities, contracts, tokens, license keys, or private customer code belong here. Four-pillar functional acceptance, rights/security review, complete installer, customer-specific signing, isolated recipient QA, update/rollback, and owner release authorization are required. See [complete private-customer release contract](docs/UCIE_FULL_PRODUCT_PRIVATE_CUSTOMER_RELEASE_V1.md) and [owner release issue #199](https://github.com/tmdrkdtn1-project/UCIE/issues/199).

**Legacy Stage 1 demonstrator remains limited; full-product customer delivery has NOT occurred.**

UCIE is being developed as an independent public-source coding intelligence system. The intended future flow is approved third-party public documentation and open-source bug fixes → provenance review → independent tests → versioned general-purpose guidance.


## Permanent product mission: SkillBooks and reusable technical knowledge

UCIE's four equal product goals include coding-error prevention; development/maintenance engine, reusable-skill and learning-logic discovery/improvement; a classified Virtual Library that **reprocesses approved public evidence into human-readable SkillBooks and separately reviewed machine-readable reusable capabilities**; and continual library evolution using only UCIE-owned authorized experiments. Mere collection, summarization, tagging and PR indexing do not satisfy the SkillBook goal. See [canonical SkillBook contract](docs/UCIE_SKILLBOOK_PRODUCT_MISSION_V1_20261102.md), [four-pillar roadmap](docs/ROADMAP.md) and [repository guidance](AGENTS.md).

The current `ucie_miner.skillbook_blueprint` builds **non-exportable, unverified metadata-only blueprints**, not finished SkillBooks. It does not authorize new sources, run external code, modify schedules, retrain models, grant licenses, publish packages or change the operating DB.

## UCIE 작업방 인계·Slack 기록

UCIE의 새 채팅방·업무 담당 전환에서는 먼저 [현재 인계 상태](docs/UCIE_HANDOFF_CURRENT.md)를 읽고, [Slack 기록·수신 확인 규약](docs/UCIE_SLACK_HANDOFF_PROTOCOL_V1_20261102.md)에 따라 GitHub PR/CI 및 실제 호스트 증거를 재확인합니다. 중요한 설계 결정·분기·차단·완료 상태는 `#ucie-project`에 근거와 다음 담당자를 기록하며, 메시지 전송과 새 방 인계 수신을 별도 상태로 관리합니다. 새 채팅이 문서를 자동 로드하거나 Slack에 자동 게시하는 기능은 아직 없습니다. 자세한 규칙은 [AGENTS.md](AGENTS.md)를 따릅니다.

## Hard security boundaries

1. The global collector must not access any user project repository, code, database, logs, conversation, credentials, model memory, or project metadata — including publicly visible user projects.
2. Knowledge may move outward only as approved PUBLIC_ONLY Rulepacks. No private-to-global feedback, project-to-project transfer, or shared private-knowledge index.
3. Do not commit secrets, local datasets, telemetry, runtime databases or imported corpora.
4. Public source requires ownership, license, opt-out and removal review. A public URL alone is not proof of origin.
5. Unit tests and demo signing are not proof of operating-system isolation or a running 24-hour miner.

## Current implementation

The standalone Stage 1 CLI validates curated public-only JSON, performs a non-executing Python AST syntax probe and demonstrates Ed25519-signed DEMO_ONLY Rulepacks. It has no network crawler, scheduler, private project adapter or production signing authority.

### Windows PowerShell / Python 3.15

~~~powershell
git clone https://github.com/tmdrkdtn1-project/UCIE.git D:\UCIE
Set-Location D:\UCIE
py -3.15 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
New-Item -ItemType Directory -Path build -Force | Out-Null
.\.venv\Scripts\python.exe -m ucie_public.cli keygen-demo --out .build_keys
.\.venv\Scripts\python.exe -m ucie_public.cli publish-demo --private-key .build_keys/private_demo.pem
.\.venv\Scripts\python.exe -m ucie_public.cli verify-demo --pack build/demo_rulepack.zip --trust .build_keys/public_demo.pem
~~~

Clone only into a new, empty location. Never use demo keys for production. Existing Stage 1 unit tests were run on Python 3.13; Python 3.15 on the user's actual PC is **not yet verified**.

See [security](SECURITY.md), [Windows setup](docs/SETUP_WINDOWS.md), and [roadmap](docs/ROADMAP.md).
