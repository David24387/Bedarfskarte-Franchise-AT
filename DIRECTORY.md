# Standortverzeichnis und HubSpot-Übergang

Die Karte ergänzt die Bedarfsanalyse um eine durchsuchbare Standortliste, Standortprofile, Bundeslandfilter und Dienstleistungen (UND-Verknüpfung). Bundesland- und Leistungsfilter begrenzen auch Fahrzeitabdeckung und Bedarfsranking. Die Textsuche begrenzt Liste und Punkte.

`daten.csv` bestimmt die veröffentlichten Standorte. `standorte.json` ergänzt Profile ausschließlich anhand identischer HubSpot-Unternehmens-IDs. Veraltete Profile ohne CSV-Eintrag erscheinen nicht. Fehlende Koordinaten werden in der Liste angezeigt; dafür wird kein Kartenpunkt erfunden. Veraltete Fahrzeitpolygone werden beim Laden ausgeschlossen.

Die neue Datenquelle ist ein getrennter privater Export mit festem Public-/Lifecycle-Filter und erlaubten Standortfeldern. Im öffentlichen Kartenrepository sind die früheren HubSpot-Abfrage-, Audit- und My-Maps-Synchronisierungsworkflows entfernt, damit alte Quellen den bereinigten Export nicht überschreiben. Fahrzeit- und Regionaldatenworkflows bleiben erhalten.

Solange der private Export nicht aktiviert ist, zeigt die Karte die vorhandene CSV mit einem Hinweis auf fehlende Details. Telefon/E-Mail sind im Export standardmäßig ausgeschaltet. Ausschließlich ausdrücklich zur Veröffentlichung geprüfte geschäftliche Angaben dürfen aktiviert werden. Freitext, Firmenbezeichnungen und Websites müssen ebenfalls auf personenbezogene Inhalte geprüft werden.

## Noch abzugleichen

Vollständige Gleichheit mit Google My Maps und Airtable ist noch nicht belegt. Dafür werden nur die benötigten Spaltennamen/Felddefinitionen und nicht personenbezogene Beispielspezifikationen benötigt. Nicht vorgesehene Felder werden nicht automatisch übernommen. Geschäftsführer, Verträge, Rechnungsinformationen und Kundendaten gehören nicht zum öffentlichen Export.

## Prüfung

`node --test tests/directory.test.cjs tests/integration.test.cjs`

Alle Testdatensätze sind künstlich. Geprüft werden sichere Darstellung, Links, ID-Zuordnung, Leistungs- und Bundeslandfilter, Fahrzeitzuordnung, fehlende Positionen, entfernte Standorte und leere Ersatzexporte. Kein Test benötigt HubSpot-Zugang oder liest CRM-Daten.
