# RackClick

**[English](README.md) · [Deutsch](README.de.md) · [Español](README.es.md)**

RackClick dokumentiert Netzwerkinfrastruktur mit einer interaktiven Ansicht von Racks, Geräten und physischen Verbindungen. Mit **Click–Click** zwei Ports auswählen, ein Kabel dokumentieren und seine Endpunkte durch die Kundeninfrastruktur verfolgen.

Der Server verbindet die bewährte Offline-Oberfläche mit gemeinsam genutzten Daten und serverseitigen Berechtigungen. Die Hierarchie lautet **Systemhaus → Kunden → Standorte → Gebäude → Räume → Racks → Geräte → Ports und Verbindungen**. Datendosen und Endgeräte im Raum gehören ebenfalls zum Inventar.

## Enthaltene Funktionen

- Interaktive Vorder- und Rückansichten, physische Montage und Fachböden, Portzustände, Verkabelung sowie Stromversorgung und PoE-Dokumentation.
- Durchsuchbarer Hardwarekatalog mit **884 Profilrevisionen für 877 unterschiedliche kommerzielle Modelle**, einschließlich der ursprünglichen Auswahl von 506 Modellen sowie deutscher Providerrouter und Repeater. Eine Revision ist kein zusätzliches physisches Modell.
- Gemeinsames Inventar, Kundenbereiche, Benutzer- und Kundengruppen, Berechtigungen, Auditprotokoll und bestätigte Schreibvorgänge.
- Native MFA-Registrierung, MFA-Anmeldung und Benutzerverwaltung. Die Richtlinie sieht **45 Tage** bis zur MFA-Pflicht vor; globale Systemhausadministratoren sind ausgenommen.
- Anwendungssprachen **Englisch, Deutsch und Spanisch**. Projektübersicht und Anleitung zur Quelldemo liegen in diesen drei Sprachen vor; historische technische Aufzeichnungen behalten ihre ursprüngliche Sprache.

## Quellen ausprobieren

Die **[Windows-Anleitung zur Quelldemo](docs/GETTING-STARTED.de.md)** beschreibt Voraussetzungen, Klonen, offiziell bezogene und festgelegte Werkzeuge, Build, Prüfung, Anmeldung und Beenden.

Das Beispiel enthält **10 synthetische Kunden, 68 Racks, 311 Geräte, 5.408 Ports und 623 Verbindungen**. Es enthält ausschließlich Inventar, keine Konten, Sitzungen oder MFA-Faktoren. Jeder Start erzeugt ein separates lokales PostgreSQL-Labor und zufällige Zugangsdaten. Die Demo verwendet HTTP auf Loopback und deaktiviert MFA ausdrücklich. Sie ist weder der Windows-Dienstinstaller noch eine Bereitstellung im Netzwerk.

Die optionale **[dreisprachige Demo50](docs/DEMO50.de.md)** enthält **17 englische, 17 deutsche und 16 spanische fiktive Firmennamen** sowie 180 Racks, 1.563 Geräte, 20.665 Ports und 2.207 Verbindungen. [HTML-Betrachter](development/examples/demo50-trilingual03/DATOS-DEMO50/VER-50-CLIENTES.html) aus dem heruntergeladenen Klon öffnen. Das Quellinventar bleibt Schema43 und deckt 868 historische Profil-/Revisionspaare ab; der aktuelle Katalog enthält 884 Revisionen. Der geprüfte Lader benötigt einen leeren Server mit Schema48 und importiert keine Anmeldedaten. Die Quelldemo mit zehn Kunden bleibt getrennt.

## Entwicklungsstand · 12. November 2026

Das aktuelle Quellschema ist **48**. Die Windows-Testinstallation A enthält alle **50 synthetischen Kunden**. Nach einem echten Neustart wurden automatischer Dienststart, reguläre HTTPS-Prüfung, Datenbestand und eine Sicherung geprüft. A wurde mit Edition17 installiert und anschließend mit einer gesondert geprüften, begrenzten Fertigstellung fehlender Aufgaben/Belege abgeschlossen. Edition18 behebt den Installerfehler; eine vollständige Neuinstallation18 ist noch nicht ausgeführt. Die erste automatische HTTPS-Prüfung nach dem Start schlug fehl, die spätere offizielle manuelle Prüfung war erfolgreich. **Restore48 bleibt gesperrt**; die endgültige Produktionsabnahme steht aus.

MFA-Wiederherstellungscodes, lokale Notfall-/Verlustwiederherstellung, Rotation, Sicherungskatalog und Versionsaufbewahrung besitzen implementierte, unabhängig geprüfte interne Komponenten mit begrenzten Labortests. Die Grenzen bleiben im nummerierten Plan dokumentiert; damit sind nicht alle Wiederherstellungs- und Wartungsszenarien produktiv abgenommen.



Offline-Parität, Wiederherstellung, Leistung und abschließende QA folgen der [Master-Roadmap](docs/HOJA-DE-RUTA-MAESTRA.md). SNMP/LLDP-Erkennung und echte Identitätsföderation bleiben spätere Vorhaben. Dies ist ein privater Entwicklungsstand, keine abgenommene Produktionsversion.

## Technik und Repository

**React/JavaScript** im Frontend; **C# / ASP.NET Core / .NET 10** im Server; **PostgreSQL 17** mit direktem Npgsql-Zugriff und SQL-Migrationen.

| Pfad | Zweck |
|---|---|
| `development/frontend/` | Oberfläche, interaktive Geräteprofile und Frontendtests |
| `development/server/` | Domäne, HTTP-Server, SQL-Migrationen und Servertests |
| `development/hardware/` | Katalogeingaben und Modellreferenzen |
| `development/examples/` | Ursprüngliches Inventar der Quelldemo mit zehn Kunden |
| `DEMO-50-CLIENTES-01/` | Optionale50-Kunden-Sammlung, Betrachter und Abdeckungsmatrix |
| `tools/` | Build-, Prüf-, Demo- und Windows-Operatorquellen |
| `docs/` | Anleitungen, Verträge, Entscheidungen und Planung |
| `reference/` | Abgenommene Offline-Referenz als Build-Eingabe |

Native Installer-Binärdateien bleiben außerhalb von GitHub, solange die Weitergabebedingungen geprüft werden. Private Datenbanken, Zugangsdaten, Zertifikate, MFA-Schlüssel und Buildprotokolle sind ausgeschlossen. Der Repositoryzugang erteilt keine neue Open-Source-Lizenz; [Hinweise zu Drittanbieterkomponenten](THIRD-PARTY-NOTICES.md) gelten weiterhin. Die festgeschriebenen Abhängigkeiten und dokumentierten Werkzeuge verwenden, statt Versionen an ein lokales SDK anzupassen.
