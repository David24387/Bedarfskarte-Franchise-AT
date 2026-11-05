# Standortverzeichnis aus HubSpot

HubSpot ist die einzige Quelle für Partnerstandorte und Standortprofile. Airtable, Google My Maps und das separate private Exportrepository werden nicht für den Abruf benötigt. Der Browser erhält keinen HubSpot-Token.

Der Workflow `sync-centers.yml` läuft stündlich, manuell und bei Änderungen am Export. Er verwendet `HUBSPOT_TOKEN` aus GitHub Actions Secrets und veröffentlicht `daten.csv`, `standorte.json` und `export_status.json` gemeinsam in einem Commit. Diese Dateien sind die automatisch erzeugte Datenkopie für die Karte, keine manuell gepflegte Referenzliste.

Es gelten ausschließlich die Partnerphasen FRP, FRPL, EFR und PLP sowie Public_Status = Public. Es gibt keinen zusätzlichen Länder- oder Aktivfilter. Neue freigegebene Partner kommen hinzu, entzogene Freigaben und entfernte Partner entfallen. API-, Mapping- und Adressfehler lassen den letzten erfolgreichen Stand unverändert. Ein leerer erfolgreicher Export entfernt auch alle bisherigen Standorte.

Die Standortprofile übernehmen vorhandene Unternehmensfelder für Bundesland, Dienstleistungen, Kernöffnungszeiten, Website, Standortlink und OEM. Exakte Feldnamen oder Labels werden aufgelöst, nicht verfügbare Felder werden im Exportstatus gemeldet. Zusätzlich werden Geschäftstelefon, geschäftliche E-Mail, Partnerstatus, die konkrete Lifecycle-Phase (FRP/FRPL/EFR/PLP), Firmenbuchnummer, USt-ID, Vertragsstart und Geschäftsführung aus den Unternehmensfeldern übernommen. Diese zusätzlichen Profileigenschaften werden erst nach Anwendung der Public-/Lifecycle-Auswahl per Batch-API für die freigegebenen Partner geladen. Es werden keine separaten Kontaktobjekte gelesen. Die Ausgabe enthält damit auch die ausdrücklich gewünschten Personenangaben aus dem Unternehmensfeld Geschäftsführung. Keine Kontakte, Deals oder Notizen werden angefordert. Die Token-Berechtigungen sind davon unabhängig und müssen in HubSpot eingeschränkt werden.

Die Liste und Profile werden anhand der Unternehmens-ID verknüpft. Fehlende Koordinaten bleiben als Listeneintrag sichtbar. Bundesland- und Leistungsfilter begrenzen auch die Fahrzeitabdeckung. Die Fahrzeitberechnung verwendet weiterhin OpenRouteService und läuft nach Veröffentlichung der Standortdaten. Ein Routingfehler verhindert keine Standortaktualisierung; fehlende Flächen werden erneut berechnet. Die bisherigen Regionaldaten bleiben bestehen.

## Prüfung

`python -m unittest discover -s scripts -p 'test_sync_hubspot_at.py'`

`node --test tests/directory.test.cjs tests/integration.test.cjs`

Alle Tests verwenden künstliche Daten. Der echte Export benötigt das Secret und läuft ausschließlich in GitHub Actions. `export_status.json` meldet Zeitpunkt, Mengen, Koordinatenlücken und Feldzuordnung sowie Befüllungszahlen ohne CRM-Einzelwerte.

## Ortssuche und Fahrzeitabdeckung

Die Suchzeile findet weiterhin direkte Treffer in Ort, PLZ, Firma, Straße, Netzkennung und KST. Bei Gemeindenamen werden zusätzlich die vorhandenen Gemeindegrenzen aus regionaldaten.json mit den gespeicherten 30-Minuten-Isochronen geschnitten. Ein Betrieb bleibt in Liste und Karte sichtbar, wenn seine Fahrzeitfläche die gesuchte Gemeinde erreicht, auch wenn der Betrieb in einem anderen Ort liegt. Das ist eine Gemeindeflächen-Abfrage; sie behauptet keine exakte Fahrzeit für jede Adresse innerhalb der Gemeinde. Die Flächen werden nicht durch Luftlinienradien ersetzt.

Netzwerk-, Bundesland- und Leistungsfilter sowie der Schalter für Standortpunkte bleiben maßgeblich. Die Bedarfsberechnung selbst wird durch den Suchtext nicht verändert. Abdeckung und Betrieb werden über Koordinaten und Netzwerk verknüpft. Standort-/Isochronenänderungen verwerfen den Suchcache. Ungültige Geometrien erzeugen keinen Treffer. Bei identischen Ortsnamen wird ein exakter Gemeindename gegenüber Teiltreffern bevorzugt. Ohne passende Gemeinde bleiben reine Texttreffer möglich.

Regression: Bei Jennersdorf erreicht die gespeicherte Fläche von Nestelbach im Ilztal die Gemeinde. Der Betrieb darf durch die fehlende Zeichenfolge „Jennersdorf“ in seiner eigenen Adresse nicht verschwinden. Dieser Fall wurde mit den realen GeoJSON-Daten und derselben Turf-Version wie in der Karte nachgerechnet. Synthetische Tests prüfen Nachbargemeinde, entfernte Fläche, Grenzberührung, Netzwerk-/Dienstleistungsfilter und unveränderte Firmen-/KST-Suche. Mobile-Smoke-Test enthält zusätzlich die Jennersdorf-Suche.

Prüfung: node --test tests/directory.test.cjs tests/integration.test.cjs tests/search.test.cjs
