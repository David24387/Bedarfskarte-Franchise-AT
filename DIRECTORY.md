# Standortverzeichnis aus HubSpot

HubSpot ist die einzige Quelle für Partnerstandorte und Standortprofile. Airtable, Google My Maps und das separate private Exportrepository werden nicht für den Abruf benötigt. Der Browser erhält keinen HubSpot-Token.

Der Workflow `sync-centers.yml` läuft stündlich, manuell und bei Änderungen am Export. Er verwendet `HUBSPOT_TOKEN` aus GitHub Actions Secrets und veröffentlicht `daten.csv`, `standorte.json` und `export_status.json` gemeinsam in einem Commit. Diese Dateien sind die automatisch erzeugte Datenkopie für die Karte, keine manuell gepflegte Referenzliste.

Es gelten ausschließlich die Partnerphasen FRP, FRPL, EFR und PLP sowie Public_Status = Public. Es gibt keinen zusätzlichen Länder- oder Aktivfilter. Neue freigegebene Partner kommen hinzu, entzogene Freigaben und entfernte Partner entfallen. API-, Mapping- und Adressfehler lassen den letzten erfolgreichen Stand unverändert. Ein leerer erfolgreicher Export entfernt auch alle bisherigen Standorte.

Die Standortprofile übernehmen vorhandene Unternehmensfelder für Bundesland, Dienstleistungen, Kernöffnungszeiten, Website, Standortlink und OEM. Exakte Feldnamen oder Labels werden aufgelöst, nicht verfügbare Felder werden im Exportstatus gemeldet. Telefon und E-Mail werden nicht exportiert. Keine Kontakte, Deals oder Notizen werden angefordert. Die Token-Berechtigungen sind davon unabhängig und müssen in HubSpot eingeschränkt werden.

Die Liste und Profile werden anhand der Unternehmens-ID verknüpft. Fehlende Koordinaten bleiben als Listeneintrag sichtbar. Bundesland- und Leistungsfilter begrenzen auch die Fahrzeitabdeckung. Die Fahrzeitberechnung verwendet weiterhin OpenRouteService und läuft nach Veröffentlichung der Standortdaten. Ein Routingfehler verhindert keine Standortaktualisierung; fehlende Flächen werden erneut berechnet. Die bisherigen Regionaldaten bleiben bestehen.

## Prüfung

`python -m unittest discover -s scripts -p 'test_sync_hubspot_at.py'`

`node --test tests/directory.test.cjs tests/integration.test.cjs`

Alle Tests verwenden künstliche Daten. Der echte Export benötigt das Secret und läuft ausschließlich in GitHub Actions. `export_status.json` meldet Zeitpunkt, Mengen, Koordinatenlücken und Feldzuordnung ohne CRM-Einzelwerte.
