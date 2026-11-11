# RackClick aus dem privaten Repository bauen und ausprobieren

**[English](GETTING-STARTED.en.md) · [Deutsch](GETTING-STARTED.de.md) · [Español](INSTALACION-DESDE-GITHUB.md)**

Stand 12. November 2026 · Quellschema **48**.

Diese Anleitung erzeugt ein **neues lokales Entwicklungslabor** mit dem ursprünglichen synthetischen Inventar für zehn Kunden. Ein installierter RackClick-Server wird nicht verändert. Jeder Start erzeugt eine weitere Datenbank und zufällige Zugangsdaten; frühere Labore bleiben auf dem Datenträger. Änderungen eines früheren Labors werden weder erneut geöffnet noch exportiert.

Die Demo verwendet **HTTP ausschließlich auf Loopback** und deaktiviert den MFA-Anbieter ausdrücklich. Nicht für das Netzwerk freigeben. Windows-Dienstinstallation, HTTPS, geplante Backups und echte MFA sind ein eigener Bereitstellungspfad. Installer-Binärdateien werden während der Prüfung ihrer Weitergabebedingungen nicht über dieses Repository verteilt. Saubere New-/Restore-Installationen und Neustartprüfungen des neuesten nativen Pakets stehen noch aus.

## 1. Voraussetzungen

- Windows x64 und eine normale Benutzersitzung, **keine als Administrator gestartete PowerShell**.
- [Git für Windows](https://git-scm.com/downloads/win), berechtigter Zugriff auf `was-car/RackClick` und [Python ab 3.12](https://www.python.org/downloads/windows/) mit dem Launcher `py`. Python-Pakete sind nicht erforderlich.
- HTTPS-Zugriff auf die offiziellen Werkzeuganbieter, NuGet und npm sowie Speicherplatz für Werkzeuge, Pakete und je einen neuen PostgreSQL-Cluster pro Ausführung.
- Das offizielle [Microsoft Visual C++ x64 Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170) für die Windows-PostgreSQL-Binärdateien. Direkt von Microsoft unter dessen Lizenz installieren und bei Aufforderung neu starten. Im nativen Test wurde 14.51.36247.0 verwendet; die ausführbare Datei ist hier nicht enthalten.
- Eine bestehende PostgreSQL-Datenbank oder ein Windows-Dienstkonto wird nicht benötigt.

Festgelegte Versionen: **.NET SDK 10.0.401**, Runtime **10.0.12**, **PostgreSQL 17.11**, **Node 24.21.0**, **npm 11.19.0**, **esbuild 0.25.10**, **Npgsql 10.0.3** und **Otp.NET 1.4.1**. Maßgeblich sind die Lockdateien. `global.json` nicht an ein anderes installiertes SDK anpassen.

## 2. PowerShell öffnen und klonen

Start öffnen, **Windows PowerShell** eingeben und normal starten. Einen neuen Zielordner wählen; dieses Beispiel verwendet `C:\Work\RackClick`:

```powershell
New-Item -ItemType Directory -Path 'C:\Work' -Force | Out-Null
Set-Location -LiteralPath 'C:\Work'
git clone https://github.com/was-car/RackClick.git RackClick
if ($LASTEXITCODE -ne 0) { throw 'Klonen fehlgeschlagen.' }
Set-Location -LiteralPath 'C:\Work\RackClick'
py -3 --version
```

Bei Aufforderung über GitHub anmelden. Kein Token in URL oder Projektdateien eintragen. Ist der Zielordner vorhanden, einen anderen Namen wählen und die Befehle anpassen; nichts löschen.

## 3. Offizielle Werkzeuge vorbereiten

In derselben Konsole im Repository-Hauptordner:

```powershell
& .\tools\windows\Initialize-Toolchain.ps1 -Component @('dotnet','postgresql','node')
```

Blockiert die Ausführungsrichtlinie das Skript, Folgendes **nur für diese Konsole** setzen und den Befehl wiederholen:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Der Helfer lädt festgelegte offizielle Archive herunter, prüft Hashwerte und entpackt nach `.local`. Er erzeugt keine Datenbanken, Dienste oder Firewallregeln. Bei einem unvollständigen Ordner oder abweichenden Hash stoppen und die Diagnose aufbewahren; keine Pins verändern.

## 4. Bauen

```powershell
py -3 -B .\tools\start_demo.py --build-only
if ($LASTEXITCODE -ne 0) { throw 'Build fehlgeschlagen.' }
```

Abhängigkeiten werden mit Lockdateien wiederhergestellt, der Server ohne Apphost veröffentlicht, der Inventarlader kompiliert und das RC9-Frontend mit `npm ci` gebaut. Das ZIP in `reference/` ist die abgenommene Offline-Buildreferenz, kein Windows-Installer. Protokolle und Binlogs bleiben privat unter `.local\source-demo\logs`; nicht ungeprüft hochladen.

Erwartete Abschlussmeldung: **„Compilacion lista“**. Die Hashwerte der Ausgaben werden gespeichert. Veränderte oder zusätzliche Ausgabedateien lassen die Startprüfung fehlschlagen.

## 5. Automatischen Smoke-Test ausführen

```powershell
py -3 -B .\tools\start_demo.py --smoke
if ($LASTEXITCODE -ne 0) { throw 'Smoke-Test fehlgeschlagen.' }
```

Erwartet werden `success: true`, `customers: 10`, `ports: 5408`, `frontend: served` und `mfaEnabled: false`. Die Prüfung erzeugt ein eigenes Labor, meldet sich an, prüft Daten und beendet ihre eigenen Prozesse. Die Dateien bleiben unter `.local\labs`.

## 6. Oberfläche öffnen

```powershell
py -3 -B .\tools\start_demo.py
```

Die Konsole zeigt eine URL wie `http://127.0.0.1:port` und den Pfad zu **ACCESO-PRIVADO.json**. Diese Datei der aktuellen Ausführung lokal im Editor öffnen: Sie enthält URL, Benutzer `demo-admin` und zufälliges Passwort. Den Inhalt nicht veröffentlichen.

Die angezeigte URL in Edge oder Chrome auf demselben Windows-Rechner öffnen. Nach der Anmeldung Kunden öffnen: Es sollten zehn erscheinen. Standorte, Gebäude, Räume und Racks durchgehen. Eine synthetische Notiz ändern, speichern und neu laden, um die Speicherung während dieser Ausführung zu prüfen.

Das Beispiel enthält 10 Kunden, 15 Standorte, 25 Gebäude, 68 Räume, 68 Racks, 311 Geräte, 633 Portgruppen, 5.408 Ports, 623 Verbindungen und 1.246 Endpunkte. Es ist **nur Inventar**, kein PostgreSQL-Dump, keine installierten Konten, Sitzungen oder MFA-Faktoren und kein vollständiges Wiederherstellungsbackup.

## 7. Beenden

Zur PowerShell wechseln und einmal **Strg+C** drücken. Die Meldung zur Prozessbeendigung abwarten. Nur die durch diese Ausführung gestarteten Server- und PostgreSQL-Prozesse werden beendet. Dateien und andere Datenbanken bleiben erhalten.

Für eine dauerhafte Windows-Bereitstellung das separat geprüfte native Paket und seine passende Operatoranleitung verwenden. Der Quelldemo-Helfer ist kein Backup-/Restore- oder MFA-Aktivierungswerkzeug.

## 8. Fehlerbehebung und MFA-Umfang

| Ergebnis | Vorgehen |
|---|---|
| GitHub 404 oder Anmeldung erforderlich | Berechtigtes Konto prüfen; das Repository ist privat. |
| `py` fehlt | Offizielles Python mit Launcher installieren und PowerShell neu öffnen. |
| SDK fehlt | Festgelegte Werkzeuge dieses Klons vorbereiten; `global.json` unverändert lassen. |
| PostgreSQL startet nicht | Visual C++, angeforderten Neustart und privates Laborprotokoll prüfen. Nicht ersatzweise eine andere Datenbank benutzen. |
| Build- oder Ausgabehashprüfung schlägt fehl | Privates Protokoll lesen, Ursache beheben und Schritt 4 wiederholen. |
| URL antwortet nicht mehr | Konsole geöffnet lassen; jeder neue Start verwendet einen neuen Port. |

Native MFA-Registrierung, Anmeldung und Dashboard wurden separat getestet. Richtlinie: 45 Tage Übergangsfrist für normale Konten, Techniker und Kundenadministratoren; für bestehende Konten ab Richtlinienaktivierung, für neue ab Erstellung. Ausgenommen sind nur globale Systemhausadministratoren mit beiden globalen Verwaltungsberechtigungen. Das Entfernen eines Faktors setzt die Frist nicht zurück. Wiederherstellung, Notfall/Verlust und Rotation besitzen geprüfte interne Implementierungen und begrenzte Labortests; endgültige Produktionsabnahme und verbleibende Szenarien sind noch offen. Siehe [aktuellen Stand und Grenzen](PUBLICACION-GITHUB-12-11-2026.md).

Echte MFA benötigt einen separat geschützten Schlüsselspeicher außerhalb von PostgreSQL, korrekte DPAPI-/ACL-Konfiguration und die Dienstidentität. Schlüssel und Wiederherstellungsumschläge sind von GitHub ausgeschlossen. Keine Konfiguration eines anderen Rechners kopieren und MFA nicht über diese Demo aktivieren.
