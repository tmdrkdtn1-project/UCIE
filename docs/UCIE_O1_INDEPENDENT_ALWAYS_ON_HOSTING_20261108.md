# UCIE O1 — Independent 24/7 Hosting Preparation (2026-11-08)

**Owner roadmap:** Local V1 owner-accepted -> independent always-on designated-customer online product -> separate owner commercial release decision -> optional extensions last. **This file does NOT authorize any live deployment.**

## Architecture and isolation

First proposed host: independent small Linux virtual machine in the AWS Seoul region (ap-northeast-2), provisionally 2 vCPU and 4 GB RAM. Keep account, operating system, backups, credentials and customer authorization separate from the Windows D:\UCIE public-miner/development machine. A single virtual machine is always-running process hosting, NOT high availability.

Future access path, ONLY after a separate reviewed owner decision:

    Designated customer (HTTPS + MFA)
      -> Cloudflare Access self-hosted application, deny by default
      -> Cloudflare Tunnel dedicated ONLY to UCIE, Protect with Access enabled
      -> Linux VM localhost 127.0.0.1:8811, non-root service
      -> separately reviewed hosted four-pillar UCIE product (not yet deployed)
      -> approved immutable public-only snapshot, per-customer isolation

Do not mount/proxy the owner Windows operating SQLite, private workstation, .git, development tunnel or other-project files. No arbitrary upstream code execution. Any hosted source material requires evidence, rights, license, source-version, approval and per-tenant access review before inclusion. Two authored SkillBooks and public error candidates remain unapproved for individual export.

## Current implementation: O1 internal origin only

- src/ucie_miner/hosting_origin_v01.py binds only 127.0.0.1, defaults to port 8811 and needs an explicit --internal-preparation-only flag.
- GET /internal/healthz returns HTTP 200 with schema UCIE_O1_INDEPENDENT_HOSTING_ORIGIN_PREPARATION_V01 and status HOSTING_PREPARATION_ONLY_NO_CUSTOMER_RELEASE. It proves process health, NOT online product readiness.
- Every customer path, including /, /local, /catalog and /skillbooks, returns HTTP 503. Unsupported write methods return 405. Non-loopback or forged Host returns 403. No operating DB reads/writes, miner/scheduler changes or network fetches.
- Owner Local V1 acceptance stays true, online/customer authorization and peripheral authorization stay false.
- tests/test_ucie_o1_hosting_origin_preparation_v01.py covers source release gate, loopback-only behavior, no-customer-route response and write-method refusal.
- No cloud VM, domain, Cloudflare Access, Tunnel or systemd unit was created/installed in this task.

The real UCIE Local V1 code currently depends on D:\UCIE and localhost. Do not directly expose it. O2 must port the product to a reviewed immutable Linux customer runtime with approved data and real access isolation.

## Continuous service template (for manual host review; NOT installed)

Future VM operator prerequisites: separate approved account and billing, Ubuntu LTS/verified Linux, Python >=3.13 isolated virtualenv, dedicated unprivileged ucie-host user, encrypted off-host backup, patch procedure, restart monitor and SSH key/MFA. Never open port 8811 on public ingress; if using Cloudflare Tunnel, no inbound public HTTP(S) port is required.

Future operator-only command after staging host authorization:

    cd /opt/ucie-release
    export PYTHONPATH=/opt/ucie-release/src
    /opt/ucie-release/.venv/bin/python -B -m ucie_miner.hosting_origin_v01 --port 8811 --internal-preparation-only

Internal checks ON THAT LINUX HOST ONLY:

    curl --fail --silent http://127.0.0.1:8811/internal/healthz
    curl --include http://127.0.0.1:8811/local
    # Expected second request: HTTP 503, never a live customer page.

A proposed systemd unit, to be manually audited and installed after owner host approval:

    [Unit]
    Description=UCIE O1 internal hosting origin (NO CUSTOMER RELEASE)
    After=network.target
    [Service]
    Type=simple
    User=ucie-host
    Group=ucie-host
    WorkingDirectory=/opt/ucie-release
    Environment=PYTHONPATH=/opt/ucie-release/src
    ExecStart=/opt/ucie-release/.venv/bin/python -B -m ucie_miner.hosting_origin_v01 --port 8811 --internal-preparation-only
    Restart=always
    RestartSec=10
    UMask=0077
    NoNewPrivileges=true
    ProtectSystem=strict
    ProtectHome=true
    PrivateTmp=true
    RestrictAddressFamilies=AF_INET AF_UNIX
    IPAddressDeny=any
    IPAddressAllow=localhost
    CapabilityBoundingSet=
    AmbientCapabilities=
    MemoryMax=512M
    TasksMax=64
    LimitNOFILE=4096
    [Install]
    WantedBy=multi-user.target

The above is a source template, not an installed or executed service. Verify actual systemd support, permissions, sandbox and Python environment on the target Linux host before enabling. A future host owner/operator must demonstrate reboot restarts, restart loops, monitoring, backup restore and fail-safe maintenance before claiming 24/7 operational acceptance.

## Dedicated customer authentication — no tunnel yet

Create a new UCIE-only Cloudflare Access self-hosted application with strictly scoped customer Allow policy, identity provider, MFA, session expiration and default-deny. **Do this BEFORE creating any tunnel public hostname**; without an Access application a tunnel route can make an origin publicly reachable.

Use a NEW UCIE-only Cloudflare Tunnel, not an existing project tunnel. Once authorized, route exactly to http://127.0.0.1:8811, configure HTTP Host Header to 127.0.0.1:8811, and enable Protect with Access (signed Access JWT verification at cloudflared with exact UCIE AUD tag). Do not add an unrestricted ingress rule. Do not commit tunnel tokens, keys, Access audience IDs or real customer names to Git.

Before any real product route is enabled, independently prove: unauthorized user denied, authorized user can sign in, expired token rejected, direct VM/origin unreachable, tenant A cannot reach B, access revocation works, tunnel-down route fails closed. The current O1 origin intentionally returns 503 even after successful identity login.

Official reference documentation:
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/
- https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/origin-parameters/
- https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/configuration-file/
- https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-regions-and-availability-zones-in-amazon-lightsail.html
- https://aws.amazon.com/lightsail/pricing/

## Ordered online commercial gates

| Stage | Acceptance evidence | Current state |
| --- | --- | --- |
| O1 always-on independent server | Actual Linux VM, locked-down host and service, reboot test, monitoring, off-host backup | PREPARATION CODE TESTED; VM NOT PROVISIONED |
| O2 hosted working product | Four-pillar parity from approved immutable source snapshots, no direct Windows SQLite mount, no customer project scanning | NOT COMPLETED |
| O3 legal/security/quality | Rights and source review, SBOM/NOTICE, independent vulnerability and negative case tests | NOT COMPLETED |
| O4 private identity/tenant licensing | HTTPS, authenticated designated users, tenant boundaries, per-customer rights, token expiry and revocation | NOT COMPLETED |
| O5 pilot and online GO | Owner-approved isolated customer pilot, service restart, backup/restore/rollback and explicit signed release decision | NOT COMPLETED |

**Status boundaries:** UCIE_LOCAL_V1_OWNER_ACCEPTED_GO; UCIE_O1_HOSTING_PREPARATION_CODE_ONLY; UCIE_ONLINE_RELEASE_NO_GO; UCIE_CUSTOMER_DISTRIBUTION_NO_GO; UCIE_PERIPHERAL_EXPANSION_NOT_AUTHORIZED. No live hosting instance or public endpoint exists as a result of this work.

Commercial issue: https://github.com/tmdrkdtn1-project/UCIE/issues/199
