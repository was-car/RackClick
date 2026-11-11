# Optional50-customer synthetic inventory

This repository includes [DEMO-50-CLIENTES-01](../DEMO-50-CLIENTES-01/), with 50 fictitious customers and their sites, rooms, racks, devices, ports and physical connections. Download or clone the repository, then open `DEMO-50-CLIENTES-01/VER-50-CLIENTES.html` in a browser. Use its search/details controls to inspect each customer and its downloadable JSON. The viewer works locally; no database access is required.

`manifest.json` identifies each customer's file, byte length and SHA256. `SHA256SUMS.txt` pins all collection files except itself. `coverage-matrix.json` maps the historical 868 profile/revision pairs to inventory instances and connections. The current application catalogue has884 revisions for 877 commercial models, so this dataset does not demonstrate all current profiles. The original506-model selection remains included in the catalogue.

The collection is inventory only: no users, passwords, sessions, MFA factors or database connection strings. It is not a PostgreSQL dump or a full security backup. Do not copy JSON files into a database directory or load them over an existing installation. The ten-customer [source demo](GETTING-STARTED.en.md) remains the default, with fresh local credentials and MFA explicitly disabled. Demo50 reproduction/import is a separate isolated-laboratory workflow, documented in Spanish in [LABORATORIO-50-CLIENTES.md](LABORATORIO-50-CLIENTES.md) and [CARGADOR-DEMO50-02.md](CARGADOR-DEMO50-02.md); availability in installed packages is described there, not implied by this source publication.

Vendor photographs and third-party reference repositories are excluded. Device drawings are interactive application code. Resource names remain as authored and are not automatically translated.

`development/examples/demo50-replay43.json` is the inventory-only API replay (2,553 commands), pinned to SHA256 `a3b44a37d8ca81f2f13d515d26905a520af8f09ffb2cfe498f97d06367bf423a`. The historical Windows importer explicitly requires an empty **schema43** server; it rejects schema45. This publication does not adapt that importer or authorize loading an existing server.

## Trilingual edition03 · 12 November 2026

The current optional set is [development/examples/demo50-trilingual03](../development/examples/demo50-trilingual03/): 17 English, 17 German and 16 Spanish fictitious company names. Open `DATOS-DEMO50/VER-50-CLIENTES.html` locally. `CARGAR-50-CLIENTES` contains the reviewed HTTPS loader, its pinned replay and instructions. It only loads a **new, empty schema48 server** after explicit operator confirmation; it is separate from the ten-customer source demo. On rejection or uncertainty, preserve the partial result and do not retry automatically. No users, sessions, passwords or MFA factors are imported.

The schema43 source structure, its 50 inventory files and all connections remain unchanged. The count is 180 racks, 1,563 devices, 20,665 ports and 2,207 connections; coverage remains 868 historical revisions, not every current catalogue revision. The set was loaded and reread after a Windows reboot in test VM A. Earlier sections describe the preserved edition01. Native installers remain outside GitHub.
