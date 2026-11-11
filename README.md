# RackClick

**[English](README.md) · [Deutsch](README.de.md) · [Español](README.es.md)**

RackClick documents network infrastructure through an interactive view of racks, devices and physical connections. Select two ports with **Click–Click** to document a cable, then follow its endpoints through the customer's infrastructure.

The server brings the established offline interface to shared, permission-controlled data. The hierarchy is **Systemhaus → customers → sites → buildings → rooms → racks → devices → ports and connections**. Room outlets and end devices also belong to the inventory.

## What is included

- Interactive front and rear views, physical mounting and shelves, port states, cabling and power/PoE documentation.
- A searchable hardware catalogue with **884 profile revisions for 877 distinct commercial models**, including the original 506-model selection, German provider routers and repeaters. A revision is not an additional physical model.
- Shared inventory, customer scopes, user and customer groups, capabilities, audit records and confirmed writes.
- Native MFA enrolment/login and user administration. The policy allows **45 days** before MFA becomes mandatory; global Systemhaus administrators are exempt.
- Application languages **English, German and Spanish**. This repository provides its overview and source-demo guide in those three languages; historical technical records retain their original language.

## Try the sources

Follow the **[Windows source-demo guide](docs/GETTING-STARTED.en.md)**. It covers prerequisites, cloning, official pinned tools, building, checking, login and stopping the demo.

The example contains **10 synthetic customers, 68 racks, 311 devices, 5,408 ports and 623 connections**. It contains inventory only, without accounts, sessions or MFA factors. Each start creates a separate local PostgreSQL lab and random credentials. The demo uses HTTP on loopback and explicitly disables MFA; it is not the Windows service installer or a network deployment.

The optional **[trilingual Demo50](docs/DEMO50.en.md)** contains **17 English, 17 German and 16 Spanish fictitious company names**, with 180 racks, 1,563 devices, 20,665 ports and 2,207 connections. [Browse its HTML viewer](development/examples/demo50-trilingual03/DATOS-DEMO50/VER-50-CLIENTES.html) from your downloaded clone. Its source inventory remains schema43 and covers 868 historical profile/revision pairs; the current catalogue contains 884 revisions. The reviewed loader targets an empty schema48 server and does not import authentication data. The ten-customer source demo remains separate.

## Development status · 12 November 2026

The current source schema is **48**. The Windows test installation in A contains all **50 synthetic customers**, verified after a real reboot with automatic service startup, normal HTTPS validation and a checked backup. A was installed with edition17 followed by a reviewed, bounded completion of missing tasks/receipts. Edition18 fixes that installer issue; a complete cold New18 run remains unexecuted. The first automatic postboot HTTPS check failed; the later official manual verifier passed. **Restore48 remains disabled** and final production acceptance is pending.

MFA recovery codes, local emergency/loss recovery, rotation, backup cataloguing and version retention now have implemented, independently reviewed internal components and bounded laboratory tests. Their individual limits remain in the numbered plan; this does not certify every recovery or maintenance scenario for production.

Offline parity, recovery, performance and final QA continue under the [master roadmap](docs/HOJA-DE-RUTA-MAESTRA.md). Discovery through SNMP/LLDP and real identity federation are future scope. This is a private development source snapshot, not a final accepted production release.

Offline parity, recovery, performance and final QA continue under the [master roadmap](docs/HOJA-DE-RUTA-MAESTRA.md). SNMP/LLDP discovery and real identity federation remain future scope. This is a private development source snapshot, not an accepted production release.

## Technology and repository

**React/JavaScript** frontend; **C# / ASP.NET Core / .NET 10** server; **PostgreSQL 17** through direct Npgsql and SQL migrations.

| Path | Purpose |
|---|---|
| `development/frontend/` | Interface, interactive device profiles and frontend tests |
| `development/server/` | Domain, HTTP server, SQL migrations and server tests |
| `development/hardware/` | Catalogue inputs and model references |
| `development/examples/` | Original ten-customer source-demo inventory |
| `DEMO-50-CLIENTES-01/` | Optional50-customer inventory collection, viewer and coverage matrix |
| `tools/` | Build, validation, demo and Windows operator sources |
| `docs/` | Guides, contracts, decisions and roadmap |
| `reference/` | Adopted offline reference used by the build |

Native installer binaries are retained outside GitHub while redistribution conditions are reviewed. Private databases, credentials, certificates, MFA keys and build logs are excluded. Repository access does not grant a new open-source licence; [third-party notices](THIRD-PARTY-NOTICES.md) remain applicable. Use the committed locks and documented tools rather than changing versions to match a local SDK.
