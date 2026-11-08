# UCIE Local V1 Windows auto-start (owner PC, no new paid VPS)

Local V1 is owner-accepted. Online/customer release is not. This is a
convenience and availability repair for the actual owner-local product,
not a new public site or new collector.

## Availability (be precise)

With the PC powered on, awake and the owner signed into Windows, one
Task Scheduler task launches UCIE at a STABLE local address:

    http://127.0.0.1:18767/local

The task uses an at-logon trigger and a five-minute repetition trigger
to recover if the process is stopped; IgnoreNew prevents overlapping
UCIE copies, and Task Scheduler retry-on-failure is configured. It does
not automatically open a PowerShell window or browser. You open a
bookmark whenever you want to use the already running app.

This is NOT proof of 24-hour uptime when the PC sleeps, powers off,
logs out, or loses its power/network. It does not run before user login.
Do not silently install a SYSTEM service or store Windows passwords.

## One-time setup on the actual owner Windows PC

Close the old manually launched Local V1 PowerShell window with Ctrl+C
so there is only one intended server. Run these commands in the current
owner's regular PowerShell session (not Administrator):

PREVIEW (safe, no changes):

    & D:\UCIE\scripts\install_ucie_local_v1_autostart.ps1

EXPLICIT ONE-TIME INSTALL AND START REQUEST:

    & D:\UCIE\scripts\install_ucie_local_v1_autostart.ps1 -Apply

READ-ONLY ACTUAL TASK + HTTP STATUS:

    & D:\UCIE\scripts\status_ucie_local_v1_autostart.ps1

Bookmark:

    http://127.0.0.1:18767/local

The health endpoint is http://127.0.0.1:18767/local/health .
Actual healthy response must have:
  schema = UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01
  status = LOCAL_V1_OWNER_ACCEPTED_LOCAL_GO_NO_ONLINE_RELEASE

Status command must say UCIE_LOCAL_V1_HEALTHY. Task registration alone
is not verified product uptime. Always inspect the actual status.

If port 18767 is already used, the installer fails CLOSED before
registration. No other process is inspected, stopped or overwritten.
Choose another available nonlegacy port using -Port on both installer
and status commands. Never use old 8767 (a different service formerly
returned JSON NOT_FOUND at that address).

If Task Scheduler refuses task creation, preserve its error. Do not
disable security policy, elevate to SYSTEM or alter another Windows task.

## Task scope, crash recovery and reversible opt-out

Exact new Task Scheduler name: \UCIE-LocalV1-Web
Action: owner D:\UCIE venv Python -B on scripts\run_ucie_local_v1_autostart.py
User: current logged-on owner, least privilege, interactive logon.
Triggers: at logon plus once/every five minutes for stopped-job recovery.
Failure recovery: 3 attempts at one-minute intervals.
Multiple-instance handling: IgnoreNew.
Target: fixed 127.0.0.1 port 18767 (configurable when registering).
No customer endpoint, remote access, firewall or Cloudflare changes.
Existing UCIE-PublicMiner-Hourly is completely separate and untouched.

Preview removal, with no changes:

    & D:\UCIE\scripts\remove_ucie_local_v1_autostart.ps1

Remove only the exact owner-matching UCIE task:

    & D:\UCIE\scripts\remove_ucie_local_v1_autostart.ps1 -Apply

Removal does NOT delete UCIE files, public ledgers, Windows services,
any other scheduled tasks, Cloudflare connections or data.

## Existing paid Cloudflare subscription

Cloudflare Tunnel connects traffic to a running local origin. Tunnel
alone does NOT host the current Windows Python UCIE process. Cloudflare
documents running the tunnel connector itself as a Windows service.
That is distinct from starting/restarting this UCIE web server.

Cloudflare Pages/Workers are different hosted execution products and
the current D:\UCIE SQLite/Windows server is not a direct drop-in.

The exact Cloudflare paid product purchased by the owner and any
UCIE-specific tunnel connection have NOT been confirmed. Do not query
other project tunnels, reuse their credentials, alter existing tunnel
services or publish UCIE. Remote access later requires a separately
owner-approved dedicated UCIE Access app (default deny + MFA + verified
identity) BEFORE any public DNS/Tunnel route. Until then localhost only.

Official technical references:
https://developers.cloudflare.com/tunnel/
https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/as-a-service/windows/
https://developers.cloudflare.com/tunnel/troubleshooting/

## Acceptance and no-release boundaries

Local owner acceptance stays GO. Online/customer deployment and
peripheral expansion stay blocked. This source and the local test results
are not evidence that the Windows task is currently installed or that
the PC has been continuously awake. The owner must run the one-time
-Apply command then confirm the live task and app health.

Official UCIE product roadmap and commercial release hold:
https://github.com/tmdrkdtn1-project/UCIE/issues/199
