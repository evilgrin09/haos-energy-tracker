# Energy Tracker für Home Assistant

Eine Custom Integration für Home Assistant, mit der du **Zählerstände (Strom, Gas, Wasser, Wärme, Heizöl)** manuell erfasst, deinen **Verbrauch auswertest** und eine **Prognose deiner Jahresabrechnung** bekommst: Nachzahlung oder Erstattung?

Die Idee stammt von der iOS-App „Energy Tracker“. Das hier ist eine eigenständige Umsetzung für Home Assistant und steht in keiner Verbindung zu dieser App.

## Funktionen

- **Zähler verwalten**: Strom, Gas, Wasser, Wärme, Heizöl, Sonstiges; Einheiten kWh, MWh, m³ und L; optional mit Zählernummer.
- **Zählerstände erfassen** über das Seitenleisten-Panel, per Service (`energy_tracker.add_reading`, nutzbar in Automationen, Skripten und Sprachassistenten) oder per CSV-Import.
  - Plausibilitätsprüfung: Ein Stand darf nicht kleiner als der vorherige sein.
  - **Zählerwechsel**: Den Anfangsstand des neuen Zählers als „Zählerwechsel“ markieren.
- **Energie-Dashboard**: Pro Zähler schreibt die Integration eine Statistik (Verbrauch und, mit Vertrag, Kosten), die du im Energie-Dashboard von Home Assistant auswählen kannst (siehe [Energie-Dashboard](#energie-dashboard)).
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
- **Verträge**: Anbieter, Tarif, Kundennummer, Laufzeit (Beginn/Ende), Kündigungsfrist, Abrechnungszeitraum (Monate), Arbeitspreis, Grundpreis, monatlicher Abschlag und Umrechnungsfaktor (Gas m³ → kWh).
- **Abrechnungsprognose** je Abrechnungszeitraum: erwartete Kosten (Arbeits- und Grundpreis), Summe der Abschläge, bisher gezahlt, **erwartete Nachzahlung oder Erstattung** und ein **empfohlener Abschlag**. Frühere Abrechnungszeiträume kannst du ebenfalls ansehen.
- **Sensoren** pro Zähler (ein Gerät je Zähler) für Dashboards und Automationen:

| Sensor | Beschreibung |
| --- | --- |
| Zählerstand | Letzter erfasster Stand. Bewusst ohne `state_class`: Für das Energie-Dashboard sind die Statistiken gedacht, nicht dieser Sensor. |
| Verbrauch aktueller Monat / Vormonat | inkl. Attributen gemessen / geschätzt / Prognose |
| Verbrauch aktuelles Jahr | bis heute |
| Prognose aktuelles Jahr | Hochrechnung für das Kalenderjahr inkl. Kosten |
| Durchschnitt pro Tag | inkl. Datenqualität |
| Prognose Kosten Abrechnungszeitraum | nur mit Vertrag |
| Erwartete Erstattung (+) / Nachzahlung (−) | nur mit Vertrag; Attribute: Abschläge, empfohlener Abschlag usw. |

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

1. **Zähler** anlegen. Optional: Verbrauchsprofil und Referenz-Jahresverbrauch.
2. **Zählerstände** erfassen, am besten mit einem Anfangsstand zum Vertragsbeginn. Historische Werte lassen sich per CSV einfügen:
   ```
   2025-01-01;12345,6
   01.02.2025;12560,1
   15.03.2025;0;wechsel
   ```
3. **Vertrag** anlegen. Mit Preisen und Abschlag zeigen Übersicht und Vertragsseite die erwartete Nachzahlung oder Erstattung.

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
- Wähle im Energie-Dashboard **nicht** den Sensor „Zählerstand“. Er hat deshalb bewusst keine `state_class` mehr.

### CSV-Export

- **Zählerstände eines Zählers:** Reiter „Zählerstände“ → „Import / Export“ → „CSV exportieren“. Die Datei lässt sich über den Import wieder einlesen.
- **Alle Zähler:** an derselben Stelle „Alle Zähler exportieren (CSV)“. Enthält zusätzlich Zählername, Zählernummer, Art, Einheit sowie Verbrauch und Tage seit der vorherigen Ablesung.
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
- Die **Jahresrate** (Hochrechnung auf 12 Monate) ergibt sich aus den Messungen der letzten 2 Jahre. Bei weniger als einem Jahr Messdaten wird sie mit 30 Tagen Gewicht mit dem Referenzwert gemittelt.
- Tage ohne Messung: Jahresrate × Profilgewicht des Tages. Tage nach heute zählen als Prognose.
- Kosten pro Tag: Verbrauch × Umrechnungsfaktor × Arbeitspreis + Grundpreis × 12 / 365.
- Abschläge: ein Abschlag pro Monat des Abrechnungszeitraums, fällig jeweils am Monatsbeginn.
- Saldo = Summe der Abschläge − prognostizierte Kosten. Ein positiver Wert bedeutet Erstattung, ein negativer Nachzahlung.
- Alle Preise sind Bruttopreise (inkl. MwSt.).

## Entwicklung

```bash
pip install -r requirements_test.txt
pytest
```

Die Rechenlogik liegt in `calc.py` und hat keine Abhängigkeit von Home Assistant. Das Panel (`frontend/energy-tracker-panel.js`) ist eine Web Component ohne Build-Schritt und ohne externe Bibliotheken; die Diagramme sind eigenes SVG.

## Ideen für später

- Preisänderungen innerhalb eines Vertrags (mehrere Preisstufen)
- Foto-Erkennung auch als Aktion für Automationen (z. B. mit einer Kamera am Zähler)
- Erinnerung an die Ablesung
- Einspeisezähler (PV) und Zwei-Tarif-Zähler (HT/NT)

## Lizenz

MIT
