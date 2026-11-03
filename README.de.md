# RackClick

**[English](README.md) · [Deutsch](README.de.md) · [Español](README.es.md)**

RackClick dokumentiert Netzwerkinfrastruktur mit einer interaktiven Ansicht von Racks, Geräten und physischen Verbindungen. Mit **Click–Click** zwei Ports auswählen, ein Kabel dokumentieren und seine Endpunkte durch die Kundeninfrastruktur verfolgen.

Der Server verbindet die bewährte Offline-Oberfläche mit gemeinsam genutzten Daten und serverseitigen Berechtigungen. Die Hierarchie lautet **Systemhaus → Kunden → Standorte → Gebäude → Räume → Racks → Geräte → Ports und Verbindungen**. Datendosen und Endgeräte im Raum gehören ebenfalls zum Inventar.

## Enthaltene Funktionen

- Interaktive Vorder- und Rückansichten, physische Montage und Fachböden, Portzustände, Verkabelung sowie Stromversorgung und PoE-Dokumentation.
- Durchsuchbarer Hardwarekatalog mit **884 Profilrevisionen für 877 unterschiedliche kommerzielle Modelle**, einschließlich der ursprünglichen Auswahl von 506 Modellen sowie deutscher Providerrouter und Repeater. Eine Revision ist kein zusätzliches physisches Modell.
- Gemeinsames Inventar, Kundenbereiche, Benutzer- und Kundengruppen, Berechtigungen, Auditprotokoll und bestätigte Schreibvorgänge.
- Native MFA-Registrierung, MFA-Anmeldung und Benutzerverwaltung. Die Richtlinie sieht **45 Tage** bis zur MFA-Pflicht vor; globale Systemhausadministratoren sind ausgenommen. Portable Wiederherstellung, Notfallverfahren, Rotation und vollständige Abnahme stehen noch aus.
- Anwendungssprachen **Englisch, Deutsch und Spanisch**. Projektübersicht und Anleitung zur Quelldemo liegen in diesen drei Sprachen vor; historische technische Aufzeichnungen behalten ihre ursprüngliche Sprache.

## Quellen ausprobieren

Die **[Windows-Anleitung zur Quelldemo](docs/GETTING-STARTED.de.md)** beschreibt Voraussetzungen, Klonen, offiziell bezogene und festgelegte Werkzeuge, Build, Prüfung, Anmeldung und Beenden.

Das Beispiel enthält **10 synthetische Kunden, 68 Racks, 311 Geräte, 5.408 Ports und 623 Verbindungen**. Es enthält ausschließlich Inventar, keine Konten, Sitzungen oder MFA-Faktoren. Jeder Start erzeugt ein separates lokales PostgreSQL-Labor und zufällige Zugangsdaten. Die Demo verwendet HTTP auf Loopback und deaktiviert MFA ausdrücklich. Sie ist weder der Windows-Dienstinstaller noch eine Bereitstellung im Netzwerk.

## Entwicklungsstand · 3. November 2026

Das aktuelle Quellschema ist **45**. Die Anwendung wurde auf einer bestehenden Windows-Testinstallation aktualisiert; HTTPS, automatischer Dienststart und Backups wurden geprüft. Inventar- und Sicherheitsdaten blieben erhalten. Eine saubere New-/Restore-Installation und die Prüfung nach einem Windows-Neustart mit dem neuesten Paket stehen noch aus. Frühere Windows-Tests ersetzen diese Prüfungen nicht.

Offline-Funktionsumfang, Wiederherstellung, Leistung und abschließende QA werden anhand des [Masterplans](docs/HOJA-DE-RUTA-MAESTRA.md) weiterbearbeitet. SNMP-/LLDP-Erkennung und echte Identitätsföderation sind spätere Vorhaben. Dies ist ein privater Entwicklungsstand der Quellen, keine endgültig abgenommene Produktionsversion.

## Technik und Repository

**React/JavaScript** im Frontend; **C# / ASP.NET Core / .NET 10** im Server; **PostgreSQL 17** mit direktem Npgsql-Zugriff und SQL-Migrationen.

| Pfad | Zweck |
|---|---|
| `development/frontend/` | Oberfläche, interaktive Geräteprofile und Frontendtests |
| `development/server/` | Domäne, HTTP-Server, SQL-Migrationen und Servertests |
| `development/hardware/` | Katalogeingaben und Modellreferenzen |
| `development/examples/` | Synthetische Inventarbeispiele |
| `tools/` | Build-, Prüf-, Demo- und Windows-Operatorquellen |
| `docs/` | Anleitungen, Verträge, Entscheidungen und Planung |
| `reference/` | Abgenommene Offline-Referenz als Build-Eingabe |

Native Installer-Binärdateien bleiben außerhalb von GitHub, solange die Weitergabebedingungen geprüft werden. Private Datenbanken, Zugangsdaten, Zertifikate, MFA-Schlüssel und Buildprotokolle sind ausgeschlossen. Der Repositoryzugang erteilt keine neue Open-Source-Lizenz; [Hinweise zu Drittanbieterkomponenten](THIRD-PARTY-NOTICES.md) gelten weiterhin. Die festgeschriebenen Abhängigkeiten und dokumentierten Werkzeuge verwenden, statt Versionen an ein lokales SDK anzupassen.
