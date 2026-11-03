# Build and try RackClick from the private repository

**[English](GETTING-STARTED.en.md) · [Deutsch](GETTING-STARTED.de.md) · [Español](INSTALACION-DESDE-GITHUB.md)**

Updated 3 November 2026 · source schema **45**.

This walkthrough creates a **new local development lab**, with the original 10-customer synthetic inventory. It does not modify an installed RackClick server. Every start creates another database and random credentials; previous labs remain on disk. It does not reopen or export changes from a previous lab.

The demo uses **HTTP on loopback only** and explicitly disables the MFA provider. Do not expose it to the network. Native Windows service installation, HTTPS, scheduled backups and real MFA are a separate deployment path. Installer binaries are not distributed through this repository while redistribution conditions are under review; clean New/Restore and post-reboot checks of the latest native package remain pending.

## 1. Requirements

- Windows x64 and a normal user session, **not an elevated administrator PowerShell**.
- [Git for Windows](https://git-scm.com/downloads/win), authorized access to `was-car/RackClick`, and [Python 3.12 or later](https://www.python.org/downloads/windows/) with the `py` launcher. No Python packages are required.
- HTTPS access to official tool providers, NuGet and npm, plus disk space for the toolchain, packages and a new PostgreSQL cluster per run.
- The official [Microsoft Visual C++ x64 redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170), required by the Windows PostgreSQL binaries. Install it from Microsoft under its licence and restart if requested. The native test environment used 14.51.36247.0; the executable is not included here.
- No existing PostgreSQL database or Windows service account is needed.

Pinned versions: **.NET SDK 10.0.401**, runtime **10.0.12**, **PostgreSQL 17.11**, **Node 24.21.0**, **npm 11.19.0**, **esbuild 0.25.10**, **Npgsql 10.0.3** and **Otp.NET 1.4.1**. Repository locks are authoritative. Do not edit `global.json` to match a different SDK.

## 2. Open PowerShell and clone

Open Start, type **Windows PowerShell**, and open it normally. Choose a new destination; the following example uses `C:\Work\RackClick`:

```powershell
New-Item -ItemType Directory -Path 'C:\Work' -Force | Out-Null
Set-Location -LiteralPath 'C:\Work'
git clone https://github.com/was-car/RackClick.git RackClick
if ($LASTEXITCODE -ne 0) { throw 'Clone failed.' }
Set-Location -LiteralPath 'C:\Work\RackClick'
py -3 --version
```

Authenticate through GitHub if requested. Never put a token in the URL or project files. If the destination exists, choose another folder and adjust the commands; do not delete it.

## 3. Prepare the official tools

In the same console, from the repository root:

```powershell
& .\tools\windows\Initialize-Toolchain.ps1 -Component @('dotnet','postgresql','node')
```

If the execution policy blocks this script, apply the following **only to this console**, then repeat the command:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

The helper downloads pinned official archives, validates their hashes and extracts into `.local`. It does not create databases, services or firewall rules. A partial directory or hash mismatch is a stop condition; keep the diagnostic rather than changing pins.

## 4. Build

```powershell
py -3 -B .\tools\start_demo.py --build-only
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
```

This restores locked dependencies, publishes the server without an apphost, builds the inventory loader and the RC9 frontend with `npm ci`. The ZIP in `reference/` is the adopted offline build input, not a Windows installer. Logs and binlogs remain private under `.local\source-demo\logs`; do not upload them without review.

Expect **“Compilacion lista”**. Output hashes are recorded; changed or extra output files cause startup validation to fail.

## 5. Run the automatic smoke check

```powershell
py -3 -B .\tools\start_demo.py --smoke
if ($LASTEXITCODE -ne 0) { throw 'Smoke check failed.' }
```

Expect `success: true`, `customers: 10`, `ports: 5408`, `frontend: served` and `mfaEnabled: false`. This creates its own lab, signs in, checks the data and stops its own processes. Files remain under `.local\labs`.

## 6. Open the interface

```powershell
py -3 -B .\tools\start_demo.py
```

The console prints a URL such as `http://127.0.0.1:port` and the path to **ACCESO-PRIVADO.json**. Open that execution's file locally in Notepad to read the URL, `demo-admin` username and random password. Do not publish its contents.

Open the printed URL in Edge or Chrome on the same Windows computer. After login, open Customers: there should be 10. Browse sites, buildings, rooms and racks. Edit a synthetic note, save and reload to check persistence during this run.

The example contains 10 customers, 15 sites, 25 buildings, 68 rooms, 68 racks, 311 devices, 633 port groups, 5,408 ports, 623 connections and 1,246 endpoints. It contains **inventory only**, not a PostgreSQL dump, installed accounts, sessions, MFA factors or a full recovery backup.

## 7. Stop

Return to PowerShell and press **Ctrl+C** once. Wait for the stopped-process message. Only the server and PostgreSQL processes created by this run are stopped. Files and other databases are preserved.

For a persistent Windows deployment, use its separately reviewed native package and matching operator guide. The source-demo helper is not a backup/restore or MFA activation tool.

## 8. Troubleshooting and MFA scope

| Result | Action |
|---|---|
| GitHub 404 or authentication prompt | Check the authorized account; this repository is private. |
| `py` missing | Install official Python with the launcher, then reopen PowerShell. |
| SDK missing | Prepare this clone's pinned tools; keep `global.json` unchanged. |
| PostgreSQL does not start | Check Visual C++, any required restart and the private lab log. Do not use another database as a workaround. |
| Build/output hash check fails | Read the private log, correct the cause and repeat step 4. |
| URL stops responding | Keep the console open; each new run uses a new port. |

Native MFA enrolment/login and its dashboard were tested separately. Policy: 45-day grace for ordinary accounts, technicians and customer administrators; existing accounts count from policy activation, new accounts from creation. Only global Systemhaus administrators with both global management capabilities are exempt. Removing a factor does not restart the grace period. Portable recovery, emergency procedures, key rotation and final acceptance remain pending.

Real MFA requires a separately protected keystore outside PostgreSQL, correct DPAPI/ACL configuration and the service identity. Keys and recovery envelopes are excluded from GitHub. Do not copy another machine's configuration or enable MFA through this demo.
