# RackClick

**[English](README.md) · [Deutsch](README.de.md) · [Español](README.es.md)**

RackClick documents network infrastructure through an interactive view of racks, devices and physical connections. Select two ports with **Click–Click** to document a cable, then follow its endpoints through the customer's infrastructure.

The server brings the established offline interface to shared, permission-controlled data. The hierarchy is **Systemhaus → customers → sites → buildings → rooms → racks → devices → ports and connections**. Room outlets and end devices also belong to the inventory.

## What is included

- Interactive front and rear views, physical mounting and shelves, port states, cabling and power/PoE documentation.
- A searchable hardware catalogue with **884 profile revisions for 877 distinct commercial models**, including the original 506-model selection, German provider routers and repeaters. A revision is not an additional physical model.
- Shared inventory, customer scopes, user and customer groups, capabilities, audit records and confirmed writes.
- Native MFA enrolment/login and user administration. The policy allows **45 days** before MFA becomes mandatory; global Systemhaus administrators are exempt. Portable recovery, emergency procedures, rotation and full acceptance remain pending.
- Application languages **English, German and Spanish**. This repository provides its overview and source-demo guide in those three languages; historical technical records retain their original language.

## Try the sources

Follow the **[Windows source-demo guide](docs/GETTING-STARTED.en.md)**. It covers prerequisites, cloning, official pinned tools, building, checking, login and stopping the demo.

The example contains **10 synthetic customers, 68 racks, 311 devices, 5,408 ports and 623 connections**. It contains inventory only, without accounts, sessions or MFA factors. Each start creates a separate local PostgreSQL lab and random credentials. The demo uses HTTP on loopback and explicitly disables MFA; it is not the Windows service installer or a network deployment.

## Development status · 3 November 2026

The current source schema is **45**. The application has been updated on an existing Windows test installation with HTTPS, automatic service startup and backup checks; its inventory and security data were preserved. A clean New/Restore installation and post-reboot verification of this latest package are still pending. Previous Windows tests do not replace those checks.

Offline parity, recovery, performance and final QA continue under the [master roadmap](docs/HOJA-DE-RUTA-MAESTRA.md). Discovery through SNMP/LLDP and real identity federation are future scope. This is a private development source snapshot, not a final accepted production release.

## Technology and repository

**React/JavaScript** frontend; **C# / ASP.NET Core / .NET 10** server; **PostgreSQL 17** through direct Npgsql and SQL migrations.

| Path | Purpose |
|---|---|
| `development/frontend/` | Interface, interactive device profiles and frontend tests |
| `development/server/` | Domain, HTTP server, SQL migrations and server tests |
| `development/hardware/` | Catalogue inputs and model references |
| `development/examples/` | Synthetic inventory examples |
| `tools/` | Build, validation, demo and Windows operator sources |
| `docs/` | Guides, contracts, decisions and roadmap |
| `reference/` | Adopted offline reference used by the build |

Native installer binaries are retained outside GitHub while redistribution conditions are reviewed. Private databases, credentials, certificates, MFA keys and build logs are excluded. Repository access does not grant a new open-source licence; [third-party notices](THIRD-PARTY-NOTICES.md) remain applicable. Use the committed locks and documented tools rather than changing versions to match a local SDK.
