# Energy Tracker für Home Assistant

Eine Custom Integration für Home Assistant, mit der du **Zählerstände (Strom, Gas, Wasser, Wärme, Heizöl)** manuell erfasst, deinen **Verbrauch auswertest** und eine **Prognose deiner Jahresabrechnung** bekommst: Nachzahlung oder Erstattung?

Die Idee stammt von der iOS-App „Energy Tracker“. Das hier ist eine eigenständige Umsetzung für Home Assistant und steht in keiner Verbindung zu dieser App.

## Funktionen

- **Zähler verwalten**: Strom, Gas, Wasser, Wärme, Heizöl, Sonstiges; Einheiten kWh, MWh, m³ und L; optional mit Zählernummer.
- **Zählerstände erfassen** über das Seitenleisten-Panel, per Service (`energy_tracker.add_reading`, nutzbar in Automationen, Skripten und Sprachassistenten) oder per CSV-Import.
  - Plausibilitätsprüfung: Ein Stand darf nicht kleiner als der vorherige sein.
  - **Zählerwechsel**: Den Anfangsstand des neuen Zählers als „Zählerwechsel“ markieren.
- **Energie-Dashboard**: Pro Zähler schreibt die Integration eine Statistik (Verbrauch und, mit Vertrag, Kosten), die du im Energie-Dashboard von Home Assistant auswählen kannst (siehe [Energie-Dashboard](#energie-dashboard)).
- **Import aus der iOS-App „Energy Tracker“**: Die CSV-Exporte der App lassen sich direkt hochladen, mit Vorschau vor dem Import (siehe [Daten aus der iOS-App Energy Tracker übernehmen](#daten-aus-der-ios-app-energy-tracker-übernehmen)).
- **CSV-Export**: Zählerstände eines Zählers, aller Zähler oder die gerade angezeigte Auswertung (siehe [CSV-Export](#csv-export)).
- **Zählerstand per Foto**: Zähler fotografieren, die Integration liest Zählernummer und Zählerstand aus dem Bild und ordnet das Foto über die Zählernummer automatisch dem richtigen Zähler zu (siehe [Zählerstand per Foto](#zählerstand-per-foto)).
- **Auswertung** mit der Auflösung **Tag / Woche / Monat / Jahr** und freier Navigation durch die Zeiträume.
  - **Verbrauchsdiagramm** (Balken) und **kumulierter Verlauf** (Linie)
  - **Vergleichsdiagramme**: Vorperiode (z. B. Vormonat) oder Vorjahreszeitraum
  - Ansicht als Verbrauch oder als **Kosten**
  - Tabelle mit allen Werten
- **Schätzung bei zu wenig Daten**:
  - Zwischen zwei Ablesungen wird der Verbrauch über die Tage verteilt, gewichtet mit einem **saisonalen Verbrauchsprofil** (Heizung ist winterlastig, Haushaltsstrom folgt grob dem Standardlastprofil H0, Wasser ist gleichmäßig).
  - Vor der ersten und nach der letzten Ablesung rechnet die Integration mit dem **Durchschnittsverbrauch**.
  - Solange weniger als zwei Ablesungen vorliegen, gilt ein **Referenz-Jahresverbrauch**. Den kannst du selbst setzen, sonst nimmt die Integration einen typischen Wert, z. B. 2.500 kWh Strom. Bei wenigen Messtagen werden Messung und Referenzwert gemittelt.
  - In den Diagrammen ist erkennbar, was **gemessen** (voll), **geschätzt** (schraffiert) und **Prognose** (hell) ist.
- **Abrechnungsjahr pro Zähler**: Abrechnungsstichtag je Zähler (Standard 30.09.). Ein Abrechnungsjahr läuft vom Tag nach dem Stichtag bis zum Stichtag, z. B. „2025/26“ = 01.10.2025–30.09.2026.
- **Verträge/Tarife**, auch rückwirkend und lückenlos hintereinander: Anbieter, Tarif, Kundennummer, Laufzeit, Kündigungsfrist, Arbeitspreis, Grundpreis, Umrechnungsfaktor (Gas m³ → kWh), Abschlag mit 11 oder 12 Zahlungen pro Jahr, Fälligkeitstag, erster Zahlung und **Abschlagsänderungen** („ab Datum X: Y €“).
- **Abrechnungsprognose** je Abrechnungsjahr: Zählerstand am Stichtag (interpoliert oder hochgerechnet), Verbrauch, Kosten (bei Preisänderung oder Anbieterwechsel tageweise anteilig), Abschläge, bisher gezahlt, **erwartete Nachzahlung oder Erstattung** und **empfohlener Abschlag**.
- **Preisänderungen innerhalb eines Vertrags** (Arbeitspreis, Grundpreis, Umrechnungsfaktor ab Datum), tageweise anteilig gerechnet, mit Zeitleiste pro Vertrag.
- **Echte Abrechnungen erfassen** und mit der eigenen Berechnung vergleichen (Verbrauch, Kosten, Abschläge, Ergebnis, Abweichung in € und %). Zählerstände aus Abrechnungen können als Ablesungen übernommen werden, auch für Jahre vor der ersten eigenen Ablesung.
- **Kostenentwicklung** über mehrere Jahre, pro Zähler oder als Summe, nach Kalender- oder Abrechnungsjahr, mit Diagramm, Tabelle und CSV-Export.
- **Sensoren** pro Zähler (ein Gerät je Zähler) für Dashboards und Automationen:

| Sensor | Beschreibung |
| --- | --- |
| Zählerstand | Letzter erfasster Stand. Bewusst ohne `state_class`: Für das Energie-Dashboard sind die Statistiken gedacht, nicht dieser Sensor. |
| Verbrauch aktueller Monat / Vormonat | inkl. Attributen gemessen / geschätzt / Prognose |
| Verbrauch aktuelles Jahr | bis heute |
| Prognose aktuelles Jahr | Hochrechnung für das Kalenderjahr inkl. Kosten |
| Durchschnitt pro Tag | inkl. Datenqualität |
| Prognose Kosten Abrechnungszeitraum | aktuelles Abrechnungsjahr; nur wenn ein Tarif im Zeitraum liegt |
| Erwartete Erstattung (+) / Nachzahlung (−) | aktuelles Abrechnungsjahr; Attribute u. a. `billing_year`, Zählerstände, Abschläge, empfohlener Abschlag |
| Letzte Abrechnung (Erstattung + / Nachzahlung −) | Ergebnis der zuletzt erfassten Abrechnung; Attribute: Zeitraum, Abweichung zur eigenen Berechnung |

Kosten-Attribute haben zusätzlich `cost_coverage`: der Anteil der Tage (in %), für die ein Tarif erfasst ist. Unter 100 sind die Kosten unvollständig.

## Installation

### HACS (benutzerdefiniertes Repository)

1. HACS → Integrationen → Menü oben rechts → **Benutzerdefinierte Repositories**
2. `https://github.com/evilgrin09/haos-energy-tracker` als Typ **Integration** hinzufügen
3. **Energy Tracker** installieren und Home Assistant neu starten
4. Einstellungen → Geräte & Dienste → **Integration hinzufügen** → „Energy Tracker“

### Manuell

Den Ordner `custom_components/energy_tracker` nach `config/custom_components/` kopieren, Home Assistant neu starten und die Integration hinzufügen.

Voraussetzung: Home Assistant 2025.11 oder neuer.

Wenn du die Integration entfernst, werden die gespeicherten Zähler, Zählerstände und Verträge sowie die Statistiken gelöscht. Die archivierten Fotos im Medienordner bleiben erhalten.

## Bedienung

Nach der Einrichtung erscheint in der Seitenleiste **Energy Tracker**. Titel und Sichtbarkeit änderst du in den Optionen der Integration.

1. **Zähler** anlegen. Optional: Verbrauchsprofil, Referenz-Jahresverbrauch, Abrechnungsstichtag und Prognosemethode.
2. **Zählerstände** erfassen, am besten mit einem Anfangsstand zum Vertragsbeginn. Historische Werte lassen sich per CSV importieren (Reiter „Zählerstände“ → „Import / Export“), als Datei oder über das Textfeld:
   ```
   2025-01-01;12345,6
   01.02.2025 18:30;12560,1
   15.03.2025;0;wechsel
   ```
3. **Vertrag** anlegen (Reiter „Abrechnung“). Mit Preisen und Abschlag zeigen Übersicht und Abrechnungsseite die erwartete Nachzahlung oder Erstattung.

### Abrechnung

Der Reiter **Abrechnung** zeigt pro Zähler:

- **Das Abrechnungsjahr** mit Blättern durch alle Jahre seit der ersten Ablesung:
  - Zählerstand zu Beginn und am Stichtag. Liegt der Stichtag zwischen zwei Ablesungen, wird interpoliert, so wie der Versorger hochrechnet: Ablesung am 07.09., Stichtag 30.09. Nach der letzten Ablesung gilt die Prognose.
  - Verbrauch (gemessen, geschätzt, Prognose), Arbeitspreis, Grundpreis, Gesamtkosten, Abschläge, bisher gezahlt, Ergebnis und empfohlener Abschlag.
  - Bei mehreren Tarifen im Jahr (Preisänderung, Anbieterwechsel) eine Aufteilung nach Tarif. Der Arbeitspreis gilt für den Verbrauch der jeweiligen Tage, der Grundpreis zeitanteilig.
  - Die Liste der einzelnen Abschläge mit Datum, Betrag und „bezahlt/offen“.
  - Ist für das Jahr eine Abrechnung erfasst: **Eigene Berechnung vs. Abrechnung**.
- **Hinweise zu fehlenden Tarifen**: Lücken zwischen Verträgen, die Zeit vor dem ersten Vertrag und abgelaufene Verträge. Tage ohne Tarif haben keine Kosten. Die Abdeckung wird überall angezeigt.
- **Tarife & Verträge**: Verträge dürfen in der Vergangenheit liegen. Trägst du ältere Verträge nach, werden Kosten, Prognose und die Kostenstatistik im Energie-Dashboard rückwirkend neu berechnet.
- **Abrechnungen des Versorgers**: Zeitraum, abgerechneter Verbrauch (in Zählereinheit oder Abrechnungseinheit, z. B. kWh bei Gas), Gesamtkosten, gezahlte Abschläge, Ergebnis (leer = Abschläge − Kosten), neuer Abschlag ab Datum und Notiz.

**Preisänderung erfassen**

Bleibt der Versorger gleich, ändern sich aber die Preise, legst du keinen neuen Vertrag an. Stattdessen:

1. Reiter **Abrechnung** → beim Vertrag auf den Stift klicken.
2. Unter **Preisänderungen** eine Zeile ausfüllen: Datum, ab dem die neuen Preise gelten, dazu Arbeitspreis, Grundpreis, bei Gas optional der neue Umrechnungsfaktor, und eine Notiz.
   - Leere Felder übernehmen den bisherigen Wert. Ändert sich nur der Grundpreis, trägst du nur diesen ein.
   - Die Preise im Vertrag selbst sind die Startpreise ab Vertragsbeginn.
   - Für weitere Änderungen erscheinen beim nächsten Bearbeiten neue leere Zeilen. Zum Löschen leerst du die Zeile (×).
3. Speichern.

Regeln:

- Das Datum muss nach dem Vertragsbeginn und spätestens am Vertragsende liegen.
- Pro Tag ist nur eine Änderung möglich, und angegebene Preise müssen größer als 0 sein.
- Ab dem Datum gelten die neuen Preise bis zur nächsten Änderung. Im Abrechnungsjahr wird tageweise anteilig gerechnet: Arbeitspreis nach dem Verbrauch der Tage, Grundpreis zeitanteilig.
- Die Aufteilung „Tarife im Zeitraum“ zeigt jeden Preisabschnitt mit Zeitraum und Preisen.
- Die Kostenstatistik im Energie-Dashboard wird ab dem Änderungsdatum neu geschrieben.
- Die **Zeitleiste** beim Vertrag listet Vertragsbeginn, Preisänderungen, Abschlagsänderungen und Vertragsende chronologisch.

**Abschläge**

- Pro Vertrag: Betrag, Anzahl pro Jahr (12 oder 11), Fälligkeitstag und optional das Datum der ersten Zahlung (Standard: erster Fälligkeitstag ab Vertragsbeginn).
- Bei 11 Abschlägen gibt es im Monat des Stichtags keine Zahlung.
- **Abschlagsänderungen** („ab 01.03.2026: 95 €“) trägst du beim Vertrag ein.
- Ein **neuer Abschlag aus einer erfassten Abrechnung** wird automatisch ab dem angegebenen Datum übernommen. Steht für denselben Tag auch eine Änderung beim Vertrag, gilt die vom Vertrag.

**Alte Abrechnungen nachtragen**

Abrechnungen lassen sich für jeden Zeitraum erfassen, auch ohne Ablesungen oder Tarife. So holst du die Jahre vor der ersten eigenen Ablesung nach:

1. Reiter **Abrechnung** → **Abrechnung erfassen**.
2. Zeitraum, abgerechneten Verbrauch, Gesamtkosten und gezahlte Abschläge eintragen. Bei Gas den Verbrauch meist in kWh mit der Einheit „Abrechnungseinheit“.
3. Optional die **Zählerstände laut Abrechnung** (Anfangs- und Endstand) und die **Preise laut Abrechnung** eintragen. Die Preise dienen nur der Kontrolle; gerechnet wird mit den Verträgen.
4. Ist **„Anfangs- und Endstand als Ablesungen übernehmen“** angehakt, legt die Integration Ablesungen an. Sie sind in der Liste der Zählerstände mit **„aus Abrechnung“** markiert (Herkunft `source: bill`):
   - Den Haken setzt das Formular automatisch, wenn für diese Tage noch keine Ablesungen existieren.
   - Der Anfangsstand gehört zum Tag vor Beginn des Zeitraums (Zählerstand bei Beginn), der Endstand zum letzten Tag.
   - Gibt es für einen Tag schon eine Ablesung, bleibt sie unverändert.
   - Hat der Versorger den Endstand nur geschätzt, setzt du **„Endstand ist geschätzt“**. Dann wird nur der Anfangsstand übernommen.
   - Passt ein Stand nicht zu den vorhandenen Ablesungen (z. B. höher als eine spätere Ablesung), wird er nicht übernommen und als Hinweis angezeigt.
5. Ältere **Verträge mit Preisänderungen** nachtragen. Dann rechnet die Integration auch die Jahre ohne erfasste Abrechnung.

In der **Auswertung** gibt es zusätzlich die Auflösung **Abrechnungsjahr**: die Monate eines Abrechnungsjahres (z. B. 2025/26), auf Wunsch mit dem Vorjahreszeitraum zum Vergleich.

### Daten aus der iOS-App Energy Tracker übernehmen

**Export in der iOS-App**

1. In der App den Zähler öffnen.
2. Über Teilen/Export die Zählerstände als **CSV** exportieren und die Datei so ablegen, dass du sie am Gerät mit Home Assistant öffnen kannst (z. B. in „Dateien“ sichern oder per AirDrop/Mail übertragen).
3. Das für jeden Zähler wiederholen. Die App erzeugt eine Datei pro Zähler, z. B. `Nebenkosten / Strom - Zählerstände.csv`.

**Import im Panel**

1. Reiter **Zählerstände** → **Import / Export** → **CSV-Dateien wählen …** und alle Dateien auf einmal auswählen.
2. Die **Import-Vorschau** zeigt pro Datei:
   - den Zielzähler. Vorgeschlagen wird ein bestehender Zähler mit passendem Namen oder passender Art, sonst „Neuen Zähler anlegen“ mit Name, Art und Einheit aus dem Dateinamen (Strom → kWh, Gas → m³, Wasser → m³). Alles ist vor dem Import änderbar.
   - Zeitraum, letzten Stand, Anzahl der Zeilen und der neuen Ablesungen,
   - zusammengefasste Tages-Duplikate, bereits vorhandene (übersprungene) Tage und verworfene Zeilen mit Grund.
3. Optional **„Bestehende Ablesungen dieses Zählers ersetzen“** ankreuzen. Ohne Haken bleiben vorhandene Ablesungen erhalten und Tage, die es schon gibt, werden übersprungen.
4. **Importieren**. Danach wird die Statistik fürs Energie-Dashboard automatisch neu berechnet.

**Was beim Import passiert**

- Die Uhrzeit wird abgeschnitten, gespeichert wird ein Zählerstand pro Tag. Gibt es mehrere Ablesungen an einem Tag, gilt die mit der spätesten Uhrzeit.
- Die Spalte „Beschreibung“ wird als Notiz übernommen.
- Die App exportiert weder Einheit noch Zählerwechsel. Die Einheit legst du beim Zähler fest. Ist ein Wert kleiner als der vorherige Stand, wird er nicht stillschweigend verworfen: Die Vorschau markiert ihn, und du entscheidest pro Wert zwischen „Zählerwechsel“, „Trotzdem übernehmen“ und „Nicht importieren“. Vorher lässt sich nichts importieren.
- Verträge, Preise und Abschläge stehen nicht im Export und müssen im Reiter „Verträge“ neu angelegt werden.

Das Textfeld an derselben Stelle nimmt dieselben Formate an und läuft durch dieselbe Vorschau. Importiert wird dabei in den oben gewählten Zähler.

### Zählerstand per Foto

In der Übersicht und unter „Zählerstände“ gibt es den Knopf **Zählerstand per Foto**. Auf dem Handy öffnet er direkt die Kamera, am PC die Dateiauswahl.

1. Zähler so fotografieren, dass **Zählerstand und Zählernummer** lesbar sind.
2. Die Integration erkennt beides und sucht den Zähler mit dieser Nummer. Leerzeichen, Bindestriche und Groß-/Kleinschreibung spielen keine Rolle. Ist nur ein Teil der Nummer zu sehen oder ein Zeichen falsch gelesen, wird der ähnlichste Zähler vorgeschlagen und als „bitte prüfen“ markiert.
3. Im Dialog stehen der zugeordnete Zähler, der erkannte Wert und der letzte Zählerstand zum Vergleich. Du kannst alles korrigieren und speicherst erst dann. Es wird nie ungefragt gespeichert.
   Beim Speichern wandert das Foto ins **Fotoarchiv** (siehe unten). Brichst du ab, wird es wieder gelöscht.
4. Passt die Nummer zu keinem Zähler, wählst du den Zähler aus und kannst die erkannte Nummer gleich bei ihm hinterlegen. Ab dann klappt die Zuordnung automatisch.

**Voraussetzungen**

- Bei jedem Zähler ist die **Zählernummer** eingetragen (Reiter „Zähler“).
- In Home Assistant ist **AI Task** mit einem KI-Anbieter eingerichtet, der Bilder verarbeiten kann (z. B. OpenAI, Google Gemini, Anthropic oder lokal über Ollama mit einem Vision-Modell). AI Task mit Bild-Anhängen gibt es erst in neueren Home-Assistant-Versionen (getestet mit 2026.2).
- Welche AI-Task-Entität genutzt wird, legst du in den Optionen der Integration fest. Bleibt das Feld leer, gilt die in Home Assistant bevorzugte AI-Task-Entität.

**Fotoarchiv**

Gespeicherte Fotos liegen im Medienordner von Home Assistant, sortiert nach Energieträger, Jahr und Monat:

```
media/energy_tracker/strom/2026/11/20261112-strom.jpg
media/energy_tracker/gas/2026/11/20261112-gas.jpg
media/energy_tracker/wasser/2026/10/20261001-wasser.jpg
```

- Gibt es mehrere Zähler desselben Energieträgers, hängt die Integration den Zählernamen an, z. B. `20261112-strom-haushalt.jpg`.
- Der Anfangsstand nach einem Zählerwechsel bekommt den Zusatz `-wechsel`.
- Ein zweites Foto für denselben Zähler und Tag ersetzt das erste.
- In der Liste der Zählerstände öffnet das Bild-Symbol das zugehörige Foto. Die Fotos findest du auch unter „Medien“ in Home Assistant.
- Löschst du einen Zählerstand, bleibt sein Foto im Archiv liegen.
- Die Ordnernamen sind deutsch, wenn Home Assistant auf Deutsch eingestellt ist, sonst englisch.

**Datenschutz und Kosten:** Das Foto wird im Browser verkleinert (längste Seite 1600 Pixel, JPEG), an Home Assistant geschickt und von dort an den gewählten KI-Anbieter weitergegeben. Bei Cloud-Anbietern verlässt das Bild also dein Netz und die Auswertung kann etwas kosten.

### Energie-Dashboard

Die Integration schreibt pro Zähler eine Langzeitstatistik in den Recorder:

| Statistik | Inhalt |
| --- | --- |
| `energy_tracker:<zähler-id>_consumption` („<Zählername> Verbrauch“) | Verbrauch in der Einheit des Zählers |
| `energy_tracker:<zähler-id>_cost` („<Zählername> Kosten“) | Kosten laut Vertrag (Arbeitspreis × Umrechnungsfaktor + Grundpreis); nur wenn ein Vertrag existiert |

So bindest du sie ein:

1. **Einstellungen → Dashboards → Energie** öffnen.
2. Im passenden Abschnitt (Stromnetz, Gasverbrauch oder Wasserverbrauch) eine Verbrauchsquelle hinzufügen. Die genauen Bezeichnungen können je nach Home-Assistant-Version leicht abweichen.
3. Im Auswahlfeld nach dem Zählernamen suchen und die Statistik **„<Zählername> Verbrauch“** wählen (ID `energy_tracker:…_consumption`).
4. Für die Kosten die Option wählen, bei der eine Entität bzw. Statistik die **Gesamtkosten** erfasst, und dort **„<Zählername> Kosten“** eintragen.
5. Speichern. Die Werte erscheinen nach kurzer Zeit im Energie-Dashboard, auch rückwirkend.

Wie die Werte entstehen:

- Grundlage sind die Tageswerte der Auswertung, gemessen und geschätzt. Prognosen für die Zukunft werden nicht geschrieben.
- Jeder Tageswert wird gleichmäßig auf die Stunden des Tages verteilt. Eine genauere Verteilung über den Tag lässt sich aus manuellen Ablesungen nicht ableiten.
- Die Statistik beginnt am Tag nach der ersten Ablesung und reicht bis zur letzten vollen Stunde. Sie wird stündlich fortgeschrieben.
- Tage seit der letzten Ablesung sind zunächst Schätzwerte. Sobald du einen neuen Zählerstand erfasst, werden sie durch die gemessenen Werte ersetzt. Dasselbe gilt für rückwirkende oder korrigierte Ablesungen, Zählerwechsel und CSV-Importe: Die Statistik wird ab dem ersten betroffenen Tag neu geschrieben.
- Kosten: Tage mit erfasster Abrechnung bekommen die Tageskosten aus der Abrechnung (dieselbe Verteilung wie in der Kostenentwicklung), alle anderen Tage die Kosten laut Tarif. Nach dem Speichern oder Löschen einer Abrechnung wird die Kostenstatistik ab dem betroffenen Tag neu geschrieben.
- Wähle im Energie-Dashboard **nicht** den Sensor „Zählerstand“. Er hat deshalb bewusst keine `state_class` mehr.

### Kostenentwicklung

Der Reiter **Kosten** zeigt die Kosten über alle Jahre, für einen Zähler oder als **Summe aller Zähler**:

- Umschaltbar zwischen **Kalenderjahr** und **Abrechnungsjahr** (z. B. „2025/26“).
- Gestapelte Balken pro Jahr: **Arbeitspreis-Anteil** (kräftig) und **Grundpreis-Anteil** (heller). Das laufende Jahr ist eine **Prognose**: heller und gestrichelt umrandet.
- Bei einem einzelnen Zähler auf Wunsch der **Verbrauch als Linie** mit eigener Achse rechts.
- **Tabelle** pro Jahr: Quelle, Verbrauch, Kosten gesamt, Grundkosten, Durchschnittspreis inkl. Grundpreis (ct/kWh bei Strom, Gas und Wärme, €/m³ bei Wasser), Veränderung zum Vorjahr in € und %, Abschläge und Ergebnis.
- **Quelle je Jahr**:
  - „berechnet“: aus Ablesungen und Tarifen
  - „laut Abrechnung“: aus einer erfassten Abrechnung
  - „gemischt“: beides, z. B. im Kalenderjahr, wenn die Abrechnung nur Januar bis September abdeckt
- **Vorrang der Abrechnung:** Liegt für einen Zeitraum eine Abrechnung mit Gesamtkosten vor, gelten deren Werte, in der Kostenentwicklung und in der Kostenstatistik fürs Energie-Dashboard. Die Kosten werden dafür auf die Tage verteilt: der Arbeitspreis-Anteil nach dem Verbrauchsprofil, der Grundpreis gleichmäßig.
- **Aufteilung Arbeits-/Grundpreis:** Den Grundpreis-Anteil nimmt die Integration aus dem Grundpreis der Abrechnung, sonst aus dem Tarif, wenn er den ganzen Zeitraum abdeckt. Ist beides nicht vorhanden, bleibt die Aufteilung **unbekannt**: Das Diagramm zeigt dann einen einfarbigen Balken „Gesamt“, die Tabelle beim Grundpreis „?“.
- **Lücken statt 0 €:** Jahre ohne Daten (vor der ersten Ablesung bzw. Abrechnung) oder ohne Tarif erscheinen als gestrichelter, leerer Balken mit „keine Daten“ bzw. „kein Tarif“.
- **Kleine Lücken am Rand eines Jahres:** Fehlen am Anfang oder Ende eines Jahres höchstens 7 Tage (z. B. erste Ablesung am 01.01.), werden diese Tage mit dem Tagesdurchschnitt der benachbarten 7 Tage geschätzt. Das Jahr gilt dann als vollständig, mit dem Hinweis „x Tage geschätzt“.
- **Unvollständige Jahre** (größere Lücken oder Lücken mitten im Jahr) sind mit „!“ und dem abgedeckten Anteil markiert. Für sie gibt es keinen Durchschnittspreis und keinen Vorjahresvergleich.
- **Ergebnis** (Erstattung/Nachzahlung) gibt es nur beim Abrechnungsjahr: aus der Abrechnung oder, für vollständig berechnete Jahre, als Abschläge − Kosten.
- In der Summe aller Zähler werden nur Kosten addiert, nicht der Verbrauch (unterschiedliche Einheiten). Jahre, in denen ein Zähler fehlt, sind als unvollständig markiert.
- **CSV-Export** der Tabelle über „Tabelle als CSV exportieren“.

Dieselben Daten liefert der Websocket-Befehl `energy_tracker/cost_history` (Parameter: `meter_id` optional, `mode`: `calendar` oder `billing`).

### CSV-Export

- **Zählerstände eines Zählers:** Reiter „Zählerstände“ → „Import / Export“ → „CSV exportieren“. Die Datei lässt sich über den Import wieder einlesen.
- **Alle Zähler:** an derselben Stelle „Alle Zähler exportieren (CSV)“. Enthält zusätzlich Zählername, Zählernummer, Art, Einheit, Verbrauch und Tage seit der vorherigen Ablesung sowie die Herkunft (`manual` oder `bill`).
- **Auswertung:** Reiter „Auswertung“ → „Tabelle als CSV exportieren“. Enthält den gerade angezeigten Zeitraum mit gemessenem, geschätztem und prognostiziertem Verbrauch, Kosten und, falls gewählt, den Vergleichswerten.

Die Dateien nutzen Semikolon als Trennzeichen und bei deutscher Spracheinstellung das Dezimalkomma, sodass Excel sie direkt öffnet.

### Rechte

Lesen und Auswerten kann jeder angemeldete Benutzer. Zähler, Zählerstände und Verträge ändern sowie Fotos hochladen können nur Administratoren.

### Zählerstand per Automation oder Sprachassistent

```yaml
action: energy_tracker.add_reading
data:
  meter: "Strom Haushalt"   # Name, Zählernummer oder ID
  value: 12345.6
  date: "2025-07-01"        # optional, Standard: heute
  reset: false              # true = Anfangsstand eines neuen Zählers
```

## Wie gerechnet wird

- Ein Zählerstand gilt als Stand **am Ende des Ablesetags**.
- Der Verbrauch zwischen zwei Ständen wird nach dem Monatsfaktor des Verbrauchsprofils auf die Tage verteilt.
- Die **Jahresrate** (Hochrechnung auf 12 Monate) ist die Grundlage aller Schätzungen und Prognosen. Pro Zähler stehen zwei Methoden zur Wahl:
  - **Letzte 365 Tage** (Standard): gemessener Verbrauch der 365 Tage bis zur letzten Ablesung, saisonal gewichtet. Reagiert schnell auf ein geändertes Verbrauchsverhalten.
  - **Durchschnitt der letzten 2 Jahre** (bisherige Methode): gleicht einzelne Ausreißerjahre stärker aus.
  - Bei weniger als einem Jahr Messdaten wird die Rate mit 30 Tagen Gewicht mit dem Referenzwert gemittelt.
- Tage ohne Messung: Jahresrate × Profilgewicht des Tages. Tage nach heute zählen als Prognose.
- Kosten pro Tag: Verbrauch × Umrechnungsfaktor × Arbeitspreis + Grundpreis × 12 / 365.
- Gelten an einem Tag mehrere Verträge, zählt der mit dem spätesten Beginn.
- Abschläge: monatlich am Fälligkeitstag (bei Tag 31 am Monatsende), Betrag laut Abschlagsänderungen. Gezählt werden alle Zahlungen, deren Datum im Abrechnungsjahr liegt.
- Saldo = Summe der Abschläge − Kosten. Ein positiver Wert bedeutet Erstattung, ein negativer Nachzahlung.
- Empfohlener Abschlag = Kosten des ganzen Abrechnungsjahres ÷ Anzahl Abschläge pro Jahr. Tage ohne Tarif werden dafür mit dem zeitlich nächsten Tarif gerechnet.
- Alle Preise sind Bruttopreise (inkl. MwSt.).

## Entwicklung

```bash
pip install -r requirements_test.txt
pytest
```

Die Rechenlogik liegt in `calc.py` und hat keine Abhängigkeit von Home Assistant. Das Panel (`frontend/energy-tracker-panel.js`) ist eine Web Component ohne Build-Schritt und ohne externe Bibliotheken; die Diagramme sind eigenes SVG.

## Ideen für später

- Saisonprofil aus den eigenen Messdaten lernen statt eines Standardprofils
- Foto-Erkennung auch als Aktion für Automationen (z. B. mit einer Kamera am Zähler)
- Erinnerung an die Ablesung
- Einspeisezähler (PV) und Zwei-Tarif-Zähler (HT/NT)

## Lizenz

MIT
