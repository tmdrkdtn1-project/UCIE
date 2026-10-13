# UCIE — Universal Coding Intelligence Engine

**Status: Stage 1 PUBLIC_ONLY offline demonstrator; production NO-GO.**

UCIE is being developed as an independent public-source coding intelligence system. The intended future flow is approved third-party public documentation and open-source bug fixes → provenance review → independent tests → versioned general-purpose guidance.

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
