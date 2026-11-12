# Energy Tracker für Home Assistant

Eine Custom Integration für Home Assistant, mit der du **Zählerstände (Strom, Gas, Wasser, Wärme, Heizöl)** manuell erfasst, deinen **Verbrauch auswertest** und eine **Prognose deiner Jahresabrechnung** bekommst: Nachzahlung oder Erstattung?

Die Idee stammt von der iOS-App „Energy Tracker“. Das hier ist eine eigenständige Umsetzung für Home Assistant und steht in keiner Verbindung zu dieser App.

## Funktionen

- **Zähler verwalten**: Strom, Gas, Wasser, Wärme, Heizöl, Sonstiges; Einheiten kWh, MWh, m³ und L; optional mit Zählernummer.
- **Zählerstände erfassen** über das Seitenleisten-Panel, per Service (`energy_tracker.add_reading`, nutzbar in Automationen, Skripten und Sprachassistenten) oder per CSV-Import.
  - Plausibilitätsprüfung: Ein Stand darf nicht kleiner als der vorherige sein.
  - **Zählerwechsel**: Den Anfangsstand des neuen Zählers als „Zählerwechsel“ markieren.
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
| Zählerstand | Letzter erfasster Stand (`total_increasing`, damit auch im Energie-Dashboard nutzbar) |
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

Voraussetzung: Home Assistant 2025.2 oder neuer.

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
4. Passt die Nummer zu keinem Zähler, wählst du den Zähler aus und kannst die erkannte Nummer gleich bei ihm hinterlegen. Ab dann klappt die Zuordnung automatisch.

**Voraussetzungen**

- Bei jedem Zähler ist die **Zählernummer** eingetragen (Reiter „Zähler“).
- In Home Assistant ist **AI Task** mit einem KI-Anbieter eingerichtet, der Bilder verarbeiten kann (z. B. OpenAI, Google Gemini, Anthropic oder lokal über Ollama mit einem Vision-Modell). AI Task mit Bild-Anhängen gibt es erst in neueren Home-Assistant-Versionen (getestet mit 2026.2).
- Welche AI-Task-Entität genutzt wird, legst du in den Optionen der Integration fest. Bleibt das Feld leer, gilt die in Home Assistant bevorzugte AI-Task-Entität.

**Datenschutz und Kosten:** Das Foto wird im Browser verkleinert, an Home Assistant geschickt und von dort an den gewählten KI-Anbieter weitergegeben. Bei Cloud-Anbietern verlässt das Bild also dein Netz und die Auswertung kann etwas kosten. Die Integration löscht das Foto direkt nach der Auswertung wieder aus dem Medienverzeichnis.

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
- Import der interpolierten Werte in die HA-Langzeitstatistik (Energie-Dashboard)
- Foto-Erkennung auch als Aktion für Automationen (z. B. mit einer Kamera am Zähler)
- Erinnerung an die Ablesung
- Einspeisezähler (PV) und Zwei-Tarif-Zähler (HT/NT)

## Lizenz

MIT
