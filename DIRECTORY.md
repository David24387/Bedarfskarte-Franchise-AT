# Standortverzeichnis und HubSpot-Übergang

Die Karte ergänzt die Bedarfsanalyse um eine durchsuchbare Standortliste, Standortprofile, Bundeslandfilter und Dienstleistungen (UND-Verknüpfung). Bundesland- und Leistungsfilter begrenzen auch Fahrzeitabdeckung und Bedarfsranking. Die Textsuche begrenzt Liste und Punkte.

`daten.csv` bestimmt die veröffentlichten Standorte. `standorte.json` ergänzt Profile ausschließlich anhand identischer HubSpot-Unternehmens-IDs. Veraltete Profile ohne CSV-Eintrag erscheinen nicht. Fehlende Koordinaten werden in der Liste angezeigt; dafür wird kein Kartenpunkt erfunden. Veraltete Fahrzeitpolygone werden beim Laden ausgeschlossen.

Die maßgebliche Datenquelle ist ein separates privates Repository. Dort wird ein vollständiger, bereinigter Standortbestand in `data/` gespeichert und versioniert, mit festem Public-/Lifecycle-Filter und erlaubten Standortfeldern. Erst nach erfolgreicher Speicherung übernimmt ein separater Job genau diese Commit-Version als öffentliche Kopie in die drei Dateien `daten.csv`, `standorte.json` und `export_status.json` dieses Karten-Repositorys. Die Karte selbst erhält weder HubSpot-Zugang noch einen Leseschlüssel für das private Repository. Der Datenbestand bleibt privat; ausschließlich die ausdrücklich freigegebene Ausgabekopie wird öffentlich. Bei einem Abruf-/Speicherfehler bleibt die zuletzt erfolgreiche öffentliche Kopie erhalten. Im öffentlichen Kartenrepository sind die früheren HubSpot-Abfrage-, Audit- und My-Maps-Synchronisierungsworkflows entfernt, damit alte Quellen den bereinigten Export nicht überschreiben. Fahrzeit- und Regionaldatenworkflows bleiben erhalten.

Solange der private Export nicht aktiviert ist, zeigt die Karte die vorhandene CSV mit einem Hinweis auf fehlende Details. Telefon/E-Mail sind im Export standardmäßig ausgeschaltet. Ausschließlich ausdrücklich zur Veröffentlichung geprüfte geschäftliche Angaben dürfen aktiviert werden. Freitext, Firmenbezeichnungen und Websites müssen ebenfalls auf personenbezogene Inhalte geprüft werden.

## Feldabgleich und offene Punkte

Die freigegebene Airtable-Ansicht und ein Google-My-Maps-Standortprofil wurden auf Felder geprüft. Name, Partnerkennung, Adresse, Bundesland, Koordinaten, Leistungen, Kernöffnungszeiten und Website-/Euromaster-Links sind im Export vorgesehen. Telefon/E-Mail bleiben bis zur ausdrücklichen Freigabe deaktiviert. Der echte HubSpot-Partnerstatus und eine getrennte FRP-/FRPL-Anzeige fehlen noch; die Legacy-CSV verwendet technisch „geöffnet“. Geschäftsführung, Firmenbuchnummer, USt-ID und Vertragsstart sind nicht Teil des aktuellen Exports. Die Freigabe zum Lesen der bisherigen Ansichten ist keine automatische Veröffentlichungsfreigabe dieser zusätzlichen Felder. Ein vollständiger produktiver Inhaltsabgleich ist erst nach Aktivierung durch den Eigentümer möglich.

## Prüfung

`node --test tests/directory.test.cjs tests/integration.test.cjs`

Alle Testdatensätze sind künstlich. Geprüft werden sichere Darstellung, Links, ID-Zuordnung, Leistungs- und Bundeslandfilter, Fahrzeitzuordnung, fehlende Positionen, entfernte Standorte und leere Ersatzexporte. Kein Test benötigt HubSpot-Zugang oder liest CRM-Daten.
