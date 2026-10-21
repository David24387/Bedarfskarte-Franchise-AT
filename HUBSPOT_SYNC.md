# HubSpot → öffentliche AT-Partnerdaten

`sync-centers.yml` ersetzt den stündlichen Google-Sheet-Import durch einen vollständigen HubSpot-Snapshot. GitHub Actions benötigt das Secret `HUBSPOT_TOKEN` mit Lesezugriff auf Unternehmen und deren Felddefinitionen. Der Token bleibt ausschließlich in Actions.

Aufnahmekriterien (alle Bedingungen erforderlich):

- Lifecycle-Phase entspricht exakt einer der Optionen Partner (FRP-Franchise), Partner (FRPL–Franchise Partner Light), Partner (EFR), Partner (PLP).
- Public_Status entspricht exakt der Option Public.


Interne Feld- und Optionswerte werden aus den HubSpot-Felddefinitionen ermittelt. Fehlende oder mehrdeutige Definitionen brechen den Export ab. Es gibt keinen zusätzlichen Filter auf Aktiv: Die Freigabe richtet sich nach den vorgegebenen Kriterien.

`daten.csv` enthält ausschließlich freigegebene Unternehmensstandorte mit Geschäftsadresse, Netzwerk, HubSpot-Unternehmens-ID als stabiler KST-Schlüssel, Partnerkennung und verfügbaren Koordinaten. FRPL wird für die bestehenden Kartenfilter der Gruppe Franchise zugeordnet. Bestehende KST-Codes werden durch die HubSpot-ID ersetzt; die Partnerkennung bleibt unter Netzkennung suchbar.

Jeder erfolgreiche Lauf erstellt die vollständige aktuelle Liste: neue Unternehmen kommen hinzu, Änderungen werden übernommen, nicht mehr freigegebene oder archivierte Unternehmen entfallen. Auch eine leere Freigabeliste wird übernommen. Bei API-, Mapping- oder Adressfehlern wird die bestehende Datei nicht ersetzt. Es werden keine alten CSV-Datensätze als Freigabe oder Positionsquelle übernommen.

Partner ohne gültige HubSpot-Koordinaten bleiben im Verzeichnis, erscheinen jedoch nicht auf der Karte. Der Lauf meldet ihre Anzahl ohne einzelne Datensätze zu protokollieren. Fehlende Koordinaten müssen in HubSpot ergänzt werden.

Die Karte verwirft alte Fahrzeitflächen, die keinem aktuell sichtbaren Standort mit gleichem Netzwerk und gleicher Position entsprechen. Neue Fahrzeitflächen ergänzt der bestehende Isochronen-Workflow spätestens nach seinem nächsten geplanten Lauf (alle sechs Stunden); bis dahin kann die Abdeckung für neue Standorte fehlen. Bot-Commits des Imports lösen keinen weiteren Push-Workflow aus.

Vor Aktivierung: Import auf dem Branch manuell ausführen und aggregierte Anzahl sowie Koordinatenlücken prüfen. Der Branch-Workflow muss dabei denselben Branch auschecken. Erst nach Prüfung zusammenführen. Der bisherige Datenbestand bleibt bis zum ersten erfolgreichen Lauf bestehen; die öffentliche Datei kann weiterhin historische Daten in der Git-Historie enthalten.

Validierung: `python -m unittest discover -s scripts -p 'test_sync_hubspot_at.py'`.

## Korrektur nach Detailprüfung am 21.10.2026

Alle 27 bisher ungeklärten Altstandorte wurden in HubSpot gefunden. Der zusätzlich eingeführte Länderfilter war ungeeignet: Österreichische Partner haben teils leere oder falsche Länderwerte (US, DE, GB). Der Export folgt deshalb ausschließlich den vorgegebenen Lifecycle- und Public-Status-Kriterien. Er korrigiert keine CRM-Daten.

Von den 27 gefundenen Standorten erfüllen 23 die Lifecycle-/Public-Kriterien. Reifen Jais Koblach, Reifen Jais Bischofshofen und Diewo Buchkirchen sind Not public; Czeczelits Wiener Neustadt ist ebenfalls Not public und hat eine andere Lifecycle-Phase. Mehrere Unternehmen an gleicher Adresse erklären die früheren mehrdeutigen Treffer. Abweichende Koordinaten bleiben separat zu prüfen.
