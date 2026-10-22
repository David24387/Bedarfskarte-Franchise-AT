# Bedarfskarte AT: alle aktiven Partner, auch Non Public

Der Workflow sync-centers.yml nutzt den vorhandenen HUBSPOT_TOKEN dieses Repositorys.
Die HubSpot-Unternehmenssuche filtert vor dem Abruf auf kundenstatus = Aktiv UND
Lifecycle FRP/FRPL/EFR/PLP. Public_Status ist für die Bedarfskarte keine Aufnahmebedingung.
Die bisherige Public-only-Sperre wurde auch im eigentlichen Exportskript entfernt.
Andere Unternehmensdaten, Kontakte und Deals werden nicht abgefragt.

Vollständiger Snapshot stündlich zur Minute 17 und bei manueller Ausführung.
Inaktive, archivierte und aus dem Netzwerk ausgeschiedene Partner werden entfernt.
Auch ein leerer Bestand ersetzt die alten Daten; API- oder Mappingfehler dagegen nicht.

ORS_API_KEY bleibt hier als Secret. Nach Standortänderungen werden fehlende Fahrzeitflächen
schrittweise ergänzt. Neue Standorte sind sofort sichtbar; die Bedarfsanalyse bleibt bis
zur vollständigen Flächenberechnung vorübergehend unvollständig.

Die öffentliche Verzeichniskarte euromaster-at-partnerverzeichnis erhält weiterhin ausschließlich
Public + Aktiv und keine Bedarfsermittlung oder internen Firmenfelder.
Der private zentrale Export ist ebenfalls vorbereitet, aber ohne hinterlegten HUBSPOT_TOKEN
und MAP_PUBLISH_TOKEN nicht produktiv. Der direkte Bedarfskarten-Sync funktioniert davon unabhängig.
