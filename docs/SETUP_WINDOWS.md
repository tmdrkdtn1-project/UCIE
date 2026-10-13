# Standalone Stage 1 installation on Windows

Use a new UCIE directory on the local PC, without changing any existing project.

### Preflight — read only

~~~powershell
git --version
py -3.15 --version
Test-Path 'D:\UCIE'
~~~

If the folder does not already exist:

~~~powershell
git clone https://github.com/tmdrkdtn1-project/UCIE.git D:\UCIE
~~~

If it exists, stop and inspect first; never delete, reset or force-clone over it.

### Offline test

~~~powershell
Set-Location D:\UCIE
py -3.15 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
~~~

There is no need to weaken PowerShell execution policy or activate the venv: invoke its Python directly.

### Demo-only package

~~~powershell
New-Item -ItemType Directory -Path build -Force | Out-Null
.\.venv\Scripts\python.exe -m ucie_public.cli keygen-demo --out .build_keys
.\.venv\Scripts\python.exe -m ucie_public.cli publish-demo --private-key .build_keys/private_demo.pem
.\.venv\Scripts\python.exe -m ucie_public.cli verify-demo --pack build/demo_rulepack.zip --trust .build_keys/public_demo.pem
~~~

The local .build_keys directory and build outputs are git-ignored. Demo keys are **never** production keys.

### Future persistent learning

Reserve D:\UCIE\runtime and D:\UCIE\raw_quarantine for local state, not git history. The collector, mining database, scheduling service and project adapters do not yet exist in this Stage 1 repository.
