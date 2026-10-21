# HubSpot-Synchronisierung für die interne AT-Bedarfskarte

Die interne Karte verwendet `sync_hubspot_at.py --audience internal`:

- Lifecycle ist FRP, FRPL, EFR oder PLP.
- Status (`kundenstatus`) ist Aktiv. Feld und Aktiv-Optionswert werden aus den HubSpot-Metadaten aufgelöst.
- Public_Status ist für diese interne Auswahl unerheblich.
- Archivierte/gelöschte Unternehmen werden nicht übernommen. Ein vollständiger erfolgreicher Snapshot ersetzt die vorherige Liste: neue Partner kommen hinzu, ausgeschiedene Partner verschwinden. Es gibt keine festen Aufnahmeausnahmen.

Die Auswahl `--audience public` behält die ursprünglichen Lifecycle-/Public-Kriterien für eine spätere öffentliche Partnerliste. Der derzeitige Workflow verwendet ausschließlich `internal`.

GitHub Actions liest stündlich HubSpot. Neue/aktualisierte Unternehmen werden anhand der stabilen HubSpot-Unternehmens-ID exportiert, ohne CSV-Referenzliste. Der bisherige Google-Sheet-Import wird ersetzt. Ein fehlerhafter API-/Mapping-/Adresslauf ersetzt keine Bestandsdaten. Ohne HubSpot-Koordinaten ist kein Kartenpunkt möglich; fehlende Koordinaten werden gezählt.

Der Sync-Workflow ergänzt anschließend die 30-Minuten-Fahrzeitflächen. Die Karte verwirft veraltete Flächen für entfernte oder verschobene Standorte. Falls der Routingdienst ausfällt, werden Standortänderungen gespeichert und fehlende Flächen im nächsten Lauf erneut versucht. Die regionale Analyse kann bis zur erfolgreichen Nachberechnung für neue Standorte unvollständig sein.

Erforderliche Actions-Secrets: HUBSPOT_TOKEN (Unternehmen/Felddefinitionen lesen), ORS_API_KEY (Fahrzeitflächen).

## Offener fachlicher Widerspruch

Gewünscht ist die Aufnahme der bisherigen acht Public-Filter-Ausschlüsse sowie das automatische Entfernen ausgeschiedener Partner. Czeczelits Neunkirchen und Czeczelits Wiener Neustadt haben in HubSpot jedoch bereits Status Inaktiv/Ausgeschieden und eine ausgeschlossene Lifecycle-Phase. Sie werden nach der Austrittsregel nicht exportiert. Falls sie weiterhin Partner sind, müssen Status und Lifecycle in HubSpot fachlich korrigiert werden. Eine dauerhafte Code-Ausnahme würde spätere Austritte umgehen und ist daher entfernt.

Die Umstellung ist bis zur Klärung dieser beiden Standorte nicht produktiv zusammengeführt. Tests: `python -m unittest discover -s scripts -p 'test_sync_hubspot_at.py'`.
