# HubSpot → AT-Bedarfskarte: ausschließlich Public-Partner

Maßgeblich ist ausschließlich der aktuelle HubSpot-Bestand mit diesen kombinierten Filtern:

- Lifecycle-Phase: Partner (FRP-Franchise), Partner (FRPL–Franchise Partner Light), Partner (EFR) oder Partner (PLP).
- Public_Status: Public.

Andere oder leere Public-Statuswerte werden nie übernommen. Es gibt keine internen Ausnahmen und keinen Modus zum Umgehen der Public-Freigabe. Die vorherige Excel-/CSV-Liste ist weder Referenz noch Aufnahmebedingung. Kein zusätzlicher Länderfilter, da das HubSpot-Länderfeld teilweise falsch gepflegt ist. Kein zusätzlicher Aktiv-Filter; der Lifecycle-/Public-Filter entspricht der abschließend bestätigten Auswahl.

Der Workflow liest stündlich HubSpot mit HUBSPOT_TOKEN und ersetzt daten.csv durch einen vollständigen Snapshot. Neue freigegebene Partner kommen automatisch hinzu; Änderungen werden übernommen. Bei Entzug von Public, Verlassen der erlaubten Lifecycle-Phasen, Archivierung oder Löschung entfallen Partner im nächsten erfolgreichen Lauf. Auch eine leere Freigabeliste ersetzt den vorherigen Bestand. API-, Mapping- oder Adressfehler ersetzen keine bestehende Datei. HubSpot-Feld-/Optionswerte werden aus den Metadaten aufgelöst.

Nur benötigte Unternehmensstandortfelder werden exportiert. Die stabile HubSpot-Unternehmens-ID ersetzt KST, Partnerkennungen bleiben unter Netzkennung suchbar. FRPL erscheint im Kartenfilter Franchise. Fehlende HubSpot-Koordinaten werden gemeldet und ermöglichen noch keinen Kartenpunkt.

Die Standortliste wird vor der Routingberechnung veröffentlicht. Die Karte lädt aktuelle Standort- und Fahrzeitdaten direkt aus dem Repository, unabhängig von einem erneuten Pages-Build. Die Routingberechnung läuft höchstens drei Minuten pro Versuch und speichert bereits erfolgreiche Ergebnisse; noch fehlende Flächen werden bei Folgeläufen ergänzt. Der gleiche Workflow aktualisiert die 30-Minuten-Fahrzeitflächen mit ORS_API_KEY. Die Karte verwirft Flächen für entfernte oder verschobene Standorte. Bei Routingfehlern werden Standortänderungen gespeichert; fehlende Flächen werden erneut versucht. Die Analyse für neu hinzugefügte Standorte bleibt bis zur erfolgreichen Flächenberechnung unvollständig.

Der Read-only-Prüfworkflow führt den echten Export in einem leeren temporären Ordner aus. Er bestätigt damit, dass keine Excel-Referenz benötigt wird, und meldet ausschließlich Mengen und Koordinatenlücken. Tests: `python -m unittest discover -s scripts -p 'test_sync_hubspot_at.py'`.
