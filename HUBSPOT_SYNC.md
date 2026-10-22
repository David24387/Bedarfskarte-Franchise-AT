# AT-Bedarfskarte: alle aktiven Partner

Quelle: David24387/hubspot-standort-export-private, Workflow export.yml.
HubSpot-Filter: kundenstatus = Aktiv UND Lifecycle FRP, FRPL, EFR oder PLP.
Public_Status ist für diese Karte keine Aufnahmebedingung. Auch aktive Non-Public-Partner sind enthalten.
Die Karte und ihre Standortdaten bleiben nach ausdrücklicher Freigabe öffentlich.

Der zentrale Export erzeugt zwei getrennte Bestände:
- data/internal → Bedarfskarte-Franchise-AT: alle aktiven Partner, einschließlich Non Public.
- data/public → euromaster-at-partnerverzeichnis: nur aktive Public-Partner, reduzierte Standortfelder.

Nur das private Quell-Repository benötigt HUBSPOT_TOKEN und MAP_PUBLISH_TOKEN.
MAP_PUBLISH_TOKEN: fine-grained GitHub-Token, ausschließlich die beiden Karten-Repositories,
Contents: Read and write. Keine Workflow- oder Verwaltungsberechtigungen erforderlich.
Der Publisher schreibt ausschließlich daten.csv, standorte.json und export_status.json.

Stündlicher Export zur Minute 17 und manuell per Run workflow. Jeder Lauf ersetzt den vollständigen Bestand.
Inaktive, archivierte oder aus dem Netzwerk ausgeschiedene Standorte werden entfernt.
API-, Mapping- und Validierungsfehler veröffentlichen keinen unvollständigen Datenbestand.

ORS_API_KEY bleibt ausschließlich als Actions-Secret in dieser Bedarfskarte.
Der Fahrzeit-Workflow reagiert auf daten.csv-Änderungen und ergänzt die 30-Minuten-Flächen.
Bis zur erfolgreichen ORS-Berechnung neuer Standorte ist die Bedarfsanalyse dort unvollständig.
Die externe Verzeichniskarte verwendet keine Fahrzeit-, Regional- oder Bedarfsdaten.
