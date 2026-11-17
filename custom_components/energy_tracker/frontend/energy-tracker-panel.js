/*
 * Energy Tracker panel for Home Assistant.
 *
 * Plain web component without build step or external dependencies.
 * All calculations happen in the backend, this file renders data and charts.
 */

const DOMAIN = "energy_tracker";

/* ------------------------------------------------------------------ i18n */

const STRINGS = {
  de: {
    title: "Energy Tracker",
    tab_overview: "Übersicht",
    tab_analysis: "Auswertung",
    tab_readings: "Zählerstände",
    tab_contracts: "Abrechnung",
    tab_costs: "Kosten",
    total_unsplit: "Gesamt (Aufteilung unbekannt)",
    split_unknown: "Aufteilung in Arbeits- und Grundpreis unbekannt",
    days_estimated: "{n} Tage geschätzt",
    from_bill: "aus Abrechnung",
    reading_end_estimated: "Endstand ist geschätzt (wird nicht als Ablesung übernommen)",
    estimated_short: "geschätzt",
    price_changes: "Preisänderungen",
    unit_price_short: "Arbeitspreis/Einheit",
    base_price_short: "Grundpreis/Monat",
    price_changes_hint: "Ab dem Datum gelten die neuen Preise bis zur nächsten Änderung. Leere Felder übernehmen den bisherigen Wert. Zum Löschen das Datum leeren.",
    clear_row: "Zeile leeren",
    timeline: "Zeitleiste",
    timeline_start: "Vertragsbeginn",
    timeline_price: "Preisänderung",
    timeline_advance: "Abschlag",
    timeline_end: "Vertragsende",
    factor_short: "Faktor",
    err_price_change_outside: "Eine Preisänderung muss nach dem Vertragsbeginn und spätestens am Vertragsende liegen.",
    err_price_change_duplicate: "Pro Tag ist nur eine Preisänderung möglich.",
    err_price_change_invalid: "Preise müssen größer als 0 sein.",
    err_price_change_empty: "Eine Preisänderung braucht mindestens einen Preis.",
    bill_readings: "Zählerstände laut Abrechnung",
    reading_bill_start: "Anfangsstand",
    reading_bill_end: "Endstand",
    bill_prices: "Preise laut Abrechnung (nur zur Kontrolle)",
    take_readings: "Anfangs- und Endstand als Ablesungen übernehmen, falls für diese Tage keine existieren (Notiz „aus Abrechnung“). Der Anfangsstand gilt für den Tag vor Beginn des Zeitraums.",
    readings_imported: "{added} Zählerstand/-stände aus der Abrechnung übernommen",
    readings_conflict: "Nicht übernommen: {date} ({value}) – {message}",
    costs_title: "Kostenentwicklung",
    all_meters: "Alle Zähler (Summe)",
    mode_calendar: "Kalenderjahr",
    mode_billing: "Abrechnungsjahr",
    show_consumption: "Verbrauch als Linie",
    year: "Jahr",
    source: "Quelle",
    source_calculated: "berechnet",
    source_bill: "laut Abrechnung",
    source_mixed: "gemischt",
    gap_no_tariff: "kein Tarif",
    gap_no_data: "keine Daten",
    avg_price: "Ø Preis",
    change_prev: "Δ Vorjahr",
    covered: "{p} % abgedeckt",
    forecast_year_note: "Prognose",
    costs_note: "Liegt für einen Zeitraum eine erfasste Abrechnung vor, gelten deren Werte. Durchschnittspreis inkl. Grundpreis. Das laufende Jahr ist eine Prognose (heller).",
    sum_note: "Summe der Kosten aller Zähler. Unvollständige Jahre sind markiert; der Verbrauch wird nicht summiert (unterschiedliche Einheiten).",
    incomplete_meters: "unvollständig: {names}",
    no_cost_data: "Noch keine Kosten: Lege Verträge an oder erfasse Abrechnungen.",
    billing_year: "Abrechnungsjahr",
    calculated_refund: "Berechnete Erstattung",
    calculated_payment: "Berechnete Nachzahlung",
    gran_billing: "Abrechnungsjahr",
    billing_date: "Abrechnungsstichtag",
    billing_date_short: "Stichtag",
    billing_date_hint: "Abrechnungszeiträume laufen vom Tag nach dem Stichtag bis zum Stichtag, unabhängig vom Vertragsbeginn.",
    day: "Tag",
    month: "Monat",
    forecast_method: "Prognosemethode",
    forecast_last_year: "Letzte 365 Tage (saisonal gewichtet)",
    forecast_average: "Durchschnitt der letzten 2 Jahre",
    forecast_method_hint: "Grundlage für Schätzungen und die Hochrechnung bis zum Stichtag.",
    reading_start: "Zählerstand Beginn",
    reading_end: "Zählerstand Stichtag",
    kind_reading: "abgelesen",
    kind_interpolated: "interpoliert",
    kind_estimated: "geschätzt",
    kind_forecast: "Prognose",
    coverage_none: "Für diesen Zeitraum ist kein Tarif erfasst. Es werden nur Verbräuche gerechnet.",
    coverage_partial: "Nur {p} % der Tage haben einen Tarif. Kosten und Ergebnis sind unvollständig.",
    cost_partial_short: "Kosten nur für {p} % der Tage",
    tariff_gap: "Kein Tarif vom {start} bis {end}.",
    tariff_before: "Für die Zeit vom {start} bis {end} ist kein Tarif erfasst. Ältere Verträge kannst du nachtragen, dann werden auch die Kosten dieser Zeit berechnet.",
    tariff_after: "Seit {start} ist kein Tarif mehr gültig.",
    segments: "Tarife im Zeitraum",
    days: "Tage",
    payments: "Abschläge",
    paid: "bezahlt",
    open_payment: "offen",
    payments_per_year: "Abschläge pro Jahr",
    payments_12: "12",
    payments_11: "11 (keine Zahlung im Monat des Stichtags)",
    payment_day: "Fälligkeitstag",
    first_payment: "Erste Zahlung (optional)",
    advance_changes: "Abschlagsänderungen",
    advance_from: "ab",
    advance_changes_hint: "Ab dem Datum gilt der neue Betrag. Leere Zeilen werden ignoriert. Ein neuer Abschlag aus einer erfassten Abrechnung wird automatisch berücksichtigt.",
    tariffs_title: "Tarife & Verträge",
    add_bill: "Abrechnung erfassen",
    bills_title: "Abrechnungen des Versorgers",
    no_bills: "Noch keine Abrechnung erfasst.",
    period_from: "Zeitraum von",
    period_to: "bis",
    bill_consumption: "Abgerechneter Verbrauch",
    unit_meter: "{unit} (Zählereinheit)",
    unit_billing: "Abrechnungseinheit (z. B. kWh)",
    bill_total_cost: "Gesamtkosten",
    bill_advances: "Gezahlte Abschläge",
    bill_result: "Ergebnis",
    result_auto: "berechnen (Abschläge − Kosten)",
    result_refund: "Erstattung",
    result_payment: "Nachzahlung",
    amount: "Betrag",
    new_advance: "Neuer Abschlag",
    new_advance_from: "gültig ab",
    bill_hint: "Der neue Abschlag fließt ab dem Datum automatisch in die Prognose ein.",
    comparison: "Eigene Berechnung vs. Abrechnung",
    own_calc: "Eigene Berechnung",
    bill_col: "Abrechnung",
    deviation: "Abweichung",
    advances: "Abschläge",
    last_bill: "Letzte Abrechnung",
    confirm_delete_bill: "Abrechnung löschen?",
    no_tariff_period: "Kein Tarif im Abrechnungszeitraum",
    refund_x: "Erstattung {v}",
    payment_x: "Nachzahlung {v}",
    times: "×",
    tab_meters: "Zähler",
    loading: "Lade …",
    no_meters: "Noch keine Zähler angelegt.",
    add_first_meter: "Ersten Zähler anlegen",
    type_electricity: "Strom",
    type_gas: "Gas",
    type_water: "Wasser",
    type_heat: "Wärme",
    type_oil: "Heizöl",
    type_other: "Sonstiges",
    profile_auto: "Automatisch (nach Zählerart)",
    profile_flat: "Gleichmäßig",
    profile_heating: "Heizung (Winter-lastig)",
    profile_electricity: "Haushaltsstrom (H0)",
    last_reading: "Letzter Zählerstand",
    none_yet: "noch keiner",
    quality_none: "Nur Schätzwerte",
    quality_low: "Wenige Daten",
    quality_good: "Gute Datenbasis",
    quality_hint_none:
      "Es liegen weniger als zwei Zählerstände vor. Alle Werte basieren auf dem Referenz-Jahresverbrauch.",
    quality_hint_low:
      "Es liegen erst wenige Tage Messdaten vor. Schätzungen werden mit dem Referenz-Jahresverbrauch gemittelt.",
    this_month: "Dieser Monat",
    previous_month: "Vormonat",
    this_year: "Dieses Jahr",
    forecast_year: "Prognose Jahr",
    forecast_year_cost: "Kosten Prognose Jahr",
    previous_year: "Vorjahr",
    per_day: "Ø pro Tag",
    per_year: "pro Jahr",
    so_far: "bisher",
    forecast: "Prognose",
    billing: "Abrechnung",
    billing_period: "Abrechnungszeitraum",
    expected_refund: "Erwartete Erstattung",
    expected_payment: "Erwartete Nachzahlung",
    expected_even: "Ausgeglichen",
    recommended_advance: "Empfohlener Abschlag",
    advance: "Abschlag",
    per_month: "/ Monat",
    total_cost: "Kosten gesamt",
    energy_cost: "Arbeitspreis",
    base_cost: "Grundpreis",
    advance_total: "Abschläge gesamt",
    paid_to_date: "Bisher gezahlt",
    consumption: "Verbrauch",
    cost: "Kosten",
    measured: "gemessen",
    estimated: "geschätzt",
    forecasted: "Prognose",
    measured_share: "Anteil gemessen",
    add_reading: "Zählerstand erfassen",
    save: "Speichern",
    update: "Aktualisieren",
    cancel: "Abbrechen",
    edit: "Bearbeiten",
    delete: "Löschen",
    date: "Datum",
    value: "Zählerstand",
    note: "Notiz",
    meter_replaced: "Zählerwechsel (Anfangsstand neuer Zähler)",
    replaced_short: "Wechsel",
    meter: "Zähler",
    since_previous: "Verbrauch seit vorher",
    readings_chart: "Verlauf Zählerstand",
    no_readings: "Noch keine Zählerstände erfasst.",
    import_export: "Import / Export",
    import_hint:
      "CSV-Export der iOS-App „Energy Tracker“ (eine Datei pro Zähler) oder eigenes Format: eine Ablesung pro Zeile als Datum;Zählerstand[;Wechsel][;Notiz]. Datum als JJJJ-MM-TT oder TT.MM.JJJJ, auch mit Uhrzeit. Eine Kopfzeile wird erkannt.",
    import: "Importieren",
    import_files: "CSV-Dateien wählen …",
    import_text_preview: "Text prüfen …",
    import_title: "Import-Vorschau",
    import_textfield: "Textfeld",
    import_analysing: "Dateien werden geprüft …",
    import_target: "Importieren in",
    import_new_meter: "+ Neuen Zähler anlegen",
    import_replace: "Bestehende Ablesungen dieses Zählers ersetzen ({n})",
    import_period: "Zeitraum",
    import_lines: "Zeilen",
    import_new: "Neue Ablesungen",
    import_merged: "Zusammengefasste Tages-Duplikate",
    import_skipped: "Bereits vorhanden (übersprungen)",
    import_rejected: "Verworfene Zeilen",
    import_last: "Letzter Stand",
    import_merged_item: "{date}: {count} Ablesungen, übernommen {kept} (späteste Uhrzeit), nicht übernommen: {dropped}",
    import_rejected_item: "Zeile {line}: „{text}“ – {reason}",
    import_flagged_title: "Bitte entscheiden: Diese Werte passen nicht zu den benachbarten Zählerständen",
    import_decide: "– bitte wählen –",
    import_decision_reset: "Zählerwechsel (neuer Zähler)",
    import_decision_keep: "Trotzdem übernehmen",
    import_decision_skip: "Nicht importieren",
    import_undecided: "Bitte zuerst für alle markierten Werte entscheiden.",
    import_name_missing: "Bitte einen Namen für den neuen Zähler eingeben.",
    import_nothing: "Keine gültigen Ablesungen gefunden.",
    import_nothing_new: "Alle Ablesungen sind bereits vorhanden.",
    import_done: "{added} Ablesungen in {meters} Zähler importiert",
    import_item_done: "Importiert: {added} neu, {skipped} bereits vorhanden",
    flag_lower_than_previous: "kleiner als der Stand vom {date} ({value})",
    flag_higher_than_next: "größer als der spätere Stand vom {date} ({value})",
    reason_too_few_columns: "zu wenige Spalten",
    reason_invalid_date: "Datum nicht erkannt",
    reason_missing_value: "Zählerstand fehlt",
    reason_invalid_value: "Zählerstand ist keine Zahl",
    reason_negative_value: "negativer Zählerstand",
    err_import_empty: "Keine gültigen Ablesungen gefunden.",
    err_import_undecided: "Bitte zuerst für alle markierten Werte entscheiden.",
    granularity: "Auflösung",
    gran_day: "Tag",
    gran_week: "Woche",
    gran_month: "Monat",
    gran_year: "Jahr",
    compare: "Vergleich",
    compare_none: "Kein Vergleich",
    compare_prev_period: "Vorperiode",
    compare_prev_year: "Vorjahreszeitraum",
    show: "Anzeige",
    show_estimates: "Schätzwerte anzeigen",
    today: "Heute",
    total: "Summe",
    difference: "Differenz",
    cumulative: "Kumulierter Verlauf",
    details: "Details",
    period: "Zeitraum",
    week_short: "KW",
    estimate_note:
      "Schraffierte Balken sind geschätzt (Durchschnitt), helle Balken sind Prognosen.",
    no_cost: "Für Kosten bitte einen Vertrag anlegen.",
    contracts_for: "Verträge",
    add_contract: "Vertrag anlegen",
    no_contracts: "Noch keine Verträge erfasst.",
    provider: "Anbieter",
    tariff: "Tarif",
    customer_number: "Kundennummer",
    start_date: "Vertragsbeginn",
    end_date: "Vertragsende (optional)",
    unit_price: "Arbeitspreis ({currency} pro {unit})",
    base_price: "Grundpreis ({currency} pro Monat)",
    advance_payment: "Abschlag ({currency} pro Zahlung)",
    conversion_factor: "Umrechnungsfaktor ({unit} → Abrechnungseinheit)",
    conversion_hint:
      "Für Gas in m³ und Preis pro kWh: Brennwert × Zustandszahl (steht auf der Rechnung, ca. 10–11). Sonst 1.",
    notice_period: "Kündigungsfrist",
    open_end: "unbefristet",
    runs_until: "Laufzeit bis",
    period_of: "Zeitraum {n} von {total}",
    previous: "Zurück",
    next: "Weiter",
    finished: "abgeschlossen",
    elapsed: "{p} % vergangen",
    add_meter: "Zähler anlegen",
    name: "Name",
    meter_type: "Art",
    unit: "Einheit",
    meter_number: "Zählernummer",
    profile: "Verbrauchsprofil",
    profile_hint:
      "Verteilt den Verbrauch zwischen zwei Ablesungen und für Schätzungen über das Jahr.",
    annual_estimate: "Referenz-Jahresverbrauch ({unit})",
    annual_hint:
      "Wird genutzt, solange zu wenige Zählerstände vorliegen. Leer = typischer Wert ({value}).",
    confirm_delete_meter:
      "Zähler \"{name}\" inklusive aller Zählerstände und Verträge löschen?",
    confirm_delete_reading: "Zählerstand vom {date} löschen?",
    confirm_delete_contract: "Vertrag löschen?",
    saved: "Gespeichert",
    deleted: "Gelöscht",
    force_question: "{message}\n\nTrotzdem speichern?",
    err_value_too_low:
      "Der Wert ist kleiner als der vorherige Zählerstand. Bei einem Zählerwechsel bitte „Zählerwechsel“ aktivieren.",
    err_value_too_high: "Der Wert ist größer als der nachfolgende Zählerstand.",
    err_duplicate_date: "Für dieses Datum gibt es bereits einen Zählerstand.",
    err_invalid_dates: "Das Enddatum liegt vor dem Startdatum.",
    reference: "Referenzwert",
    average_basis: "Durchschnitt basiert auf",
    days_measured: "{n} Tagen Messdaten",
    last_12_months: "Letzte 12 Monate",
    export_all: "Alle Zähler exportieren (CSV)",
    export_table: "Tabelle als CSV exportieren",
    view_photo: "Foto anzeigen",
    close: "Schließen",
    read_only: "Nur Administratoren können Zählerstände, Zähler und Verträge ändern.",
    dashboard_hint: "Energie-Dashboard: Statistik „{name}“",
    stat_consumption: "Verbrauch",
    stat_cost: "Kosten",
    err_unauthorized: "Dafür sind Administratorrechte nötig.",
    photo_button: "Zählerstand per Foto",
    photo_title: "Zählerstand aus Foto",
    photo_loading: "Foto wird ausgewertet …",
    photo_match_exact: "Zähler „{name}“ anhand der Zählernummer {number} erkannt.",
    photo_match_similar: "Die erkannte Zählernummer {number} ähnelt dem Zähler „{name}“ ({stored}). Bitte prüfen.",
    photo_match_single: "Die Zählernummer konnte nicht zugeordnet werden. Der einzige Zähler ist vorausgewählt.",
    photo_match_none: "Kein Zähler mit der Nummer {number} gefunden. Bitte Zähler auswählen.",
    photo_no_number: "Keine Zählernummer erkannt. Bitte Zähler auswählen.",
    photo_no_value: "Der Zählerstand konnte nicht gelesen werden. Bitte von Hand eintragen.",
    photo_check: "Bitte den erkannten Wert mit dem Foto vergleichen.",
    photo_save_number: "Erkannte Zählernummer {number} beim gewählten Zähler speichern",
    photo_retry: "Neues Foto",
    photo_last: "Letzter Stand: {value} ({date})",
    choose: "– bitte wählen –",
    meter_number_hint: "Über die Zählernummer werden Fotos automatisch dem Zähler zugeordnet.",
    err_ai_task_missing:
      "Für die Fotoerkennung muss in Home Assistant „AI Task“ mit einem KI-Anbieter eingerichtet sein, der Bilder verarbeiten kann.",
    err_no_ai_entity:
      "Es ist keine passende AI-Task-Entität festgelegt. Wähle sie in den Optionen von Energy Tracker oder lege in Home Assistant eine bevorzugte AI-Task-Entität fest.",
    err_recognition_failed: "Das Foto konnte nicht ausgewertet werden.",
    err_no_media_dir: "In Home Assistant ist kein Medienverzeichnis eingerichtet.",
    err_invalid_image: "Die Datei ist kein gültiges Bild oder zu groß.",
  },
  en: {
    title: "Energy Tracker",
    tab_overview: "Overview",
    tab_analysis: "Analysis",
    tab_readings: "Readings",
    tab_contracts: "Billing",
    tab_costs: "Costs",
    total_unsplit: "Total (split unknown)",
    split_unknown: "Split into energy and base cost unknown",
    days_estimated: "{n} days estimated",
    from_bill: "from bill",
    reading_end_estimated: "End reading is estimated (not taken over as reading)",
    estimated_short: "estimated",
    price_changes: "Price changes",
    unit_price_short: "Unit price",
    base_price_short: "Base price/month",
    price_changes_hint: "The new prices apply from the date until the next change. Empty fields keep the previous value. Clear the date to delete a change.",
    clear_row: "Clear row",
    timeline: "Timeline",
    timeline_start: "Contract start",
    timeline_price: "Price change",
    timeline_advance: "Advance payment",
    timeline_end: "Contract end",
    factor_short: "Factor",
    err_price_change_outside: "A price change must be after the contract start and not after the contract end.",
    err_price_change_duplicate: "Only one price change per day is possible.",
    err_price_change_invalid: "Prices must be greater than 0.",
    err_price_change_empty: "A price change needs at least one price.",
    bill_readings: "Meter readings according to the bill",
    reading_bill_start: "Start reading",
    reading_bill_end: "End reading",
    bill_prices: "Prices according to the bill (for checking only)",
    take_readings: "Store start and end reading as readings if there are none for these days (note “aus Abrechnung”). The start reading belongs to the day before the period.",
    readings_imported: "{added} reading(s) taken from the bill",
    readings_conflict: "Not taken: {date} ({value}) – {message}",
    costs_title: "Cost development",
    all_meters: "All meters (total)",
    mode_calendar: "Calendar year",
    mode_billing: "Billing year",
    show_consumption: "Consumption as line",
    year: "Year",
    source: "Source",
    source_calculated: "calculated",
    source_bill: "from bill",
    source_mixed: "mixed",
    gap_no_tariff: "no tariff",
    gap_no_data: "no data",
    avg_price: "Ø price",
    change_prev: "Δ previous year",
    covered: "{p} % covered",
    forecast_year_note: "Forecast",
    costs_note: "Where a bill is recorded for a period, its values are used. Average price incl. base price. The current year is a forecast (lighter).",
    sum_note: "Total cost of all meters. Incomplete years are marked; consumption is not added up (different units).",
    incomplete_meters: "incomplete: {names}",
    no_cost_data: "No costs yet: add contracts or record bills.",
    billing_year: "Billing year",
    calculated_refund: "Calculated refund",
    calculated_payment: "Calculated additional payment",
    gran_billing: "Billing year",
    billing_date: "Billing date",
    billing_date_short: "Billing date",
    billing_date_hint: "Billing periods run from the day after the billing date to the billing date, independent of the contract start.",
    day: "Day",
    month: "Month",
    forecast_method: "Forecast method",
    forecast_last_year: "Last 365 days (seasonally weighted)",
    forecast_average: "Average of the last 2 years",
    forecast_method_hint: "Basis for estimates and the extrapolation to the billing date.",
    reading_start: "Reading at start",
    reading_end: "Reading at billing date",
    kind_reading: "read",
    kind_interpolated: "interpolated",
    kind_estimated: "estimated",
    kind_forecast: "forecast",
    coverage_none: "No tariff is recorded for this period. Only consumption is calculated.",
    coverage_partial: "Only {p} % of the days have a tariff. Costs and result are incomplete.",
    cost_partial_short: "Costs only for {p} % of the days",
    tariff_gap: "No tariff from {start} to {end}.",
    tariff_before: "No tariff is recorded from {start} to {end}. You can add older contracts to calculate the costs of that time as well.",
    tariff_after: "No tariff is valid since {start}.",
    segments: "Tariffs in this period",
    days: "Days",
    payments: "Advance payments",
    paid: "paid",
    open_payment: "open",
    payments_per_year: "Advance payments per year",
    payments_12: "12",
    payments_11: "11 (no payment in the month of the billing date)",
    payment_day: "Due day",
    first_payment: "First payment (optional)",
    advance_changes: "Changes of the advance payment",
    advance_from: "from",
    advance_changes_hint: "The new amount applies from the date. Empty rows are ignored. A new advance payment from a recorded bill is applied automatically.",
    tariffs_title: "Tariffs & contracts",
    add_bill: "Add bill",
    bills_title: "Bills of the utility",
    no_bills: "No bills recorded yet.",
    period_from: "Period from",
    period_to: "to",
    bill_consumption: "Billed consumption",
    unit_meter: "{unit} (meter unit)",
    unit_billing: "Billing unit (e.g. kWh)",
    bill_total_cost: "Total cost",
    bill_advances: "Advance payments made",
    bill_result: "Result",
    result_auto: "calculate (payments − cost)",
    result_refund: "Refund",
    result_payment: "Additional payment",
    amount: "Amount",
    new_advance: "New advance payment",
    new_advance_from: "valid from",
    bill_hint: "The new advance payment is used in the forecast from that date.",
    comparison: "Own calculation vs. bill",
    own_calc: "Own calculation",
    bill_col: "Bill",
    deviation: "Deviation",
    advances: "Advance payments",
    last_bill: "Last bill",
    confirm_delete_bill: "Delete bill?",
    no_tariff_period: "No tariff in the billing period",
    refund_x: "Refund {v}",
    payment_x: "Additional payment {v}",
    times: "×",
    tab_meters: "Meters",
    loading: "Loading …",
    no_meters: "No meters yet.",
    add_first_meter: "Add first meter",
    type_electricity: "Electricity",
    type_gas: "Gas",
    type_water: "Water",
    type_heat: "Heat",
    type_oil: "Heating oil",
    type_other: "Other",
    profile_auto: "Automatic (by meter type)",
    profile_flat: "Even",
    profile_heating: "Heating (winter heavy)",
    profile_electricity: "Household electricity (H0)",
    last_reading: "Last reading",
    none_yet: "none yet",
    quality_none: "Estimates only",
    quality_low: "Little data",
    quality_good: "Good data",
    quality_hint_none:
      "There are fewer than two readings. All values are based on the reference annual consumption.",
    quality_hint_low:
      "There are only a few days of measured data. Estimates are blended with the reference annual consumption.",
    this_month: "This month",
    previous_month: "Previous month",
    this_year: "This year",
    forecast_year: "Year forecast",
    forecast_year_cost: "Year forecast cost",
    previous_year: "Previous year",
    per_day: "Ø per day",
    per_year: "per year",
    so_far: "so far",
    forecast: "Forecast",
    billing: "Billing",
    billing_period: "Billing period",
    expected_refund: "Expected refund",
    expected_payment: "Expected additional payment",
    expected_even: "Balanced",
    recommended_advance: "Recommended advance payment",
    advance: "Advance payment",
    per_month: "/ month",
    total_cost: "Total cost",
    energy_cost: "Energy cost",
    base_cost: "Base price",
    advance_total: "Advance payments total",
    paid_to_date: "Paid so far",
    consumption: "Consumption",
    cost: "Cost",
    measured: "measured",
    estimated: "estimated",
    forecasted: "forecast",
    measured_share: "Measured share",
    add_reading: "Add reading",
    save: "Save",
    update: "Update",
    cancel: "Cancel",
    edit: "Edit",
    delete: "Delete",
    date: "Date",
    value: "Reading",
    note: "Note",
    meter_replaced: "Meter replaced (start value of new meter)",
    replaced_short: "Replaced",
    meter: "Meter",
    since_previous: "Consumption since previous",
    readings_chart: "Meter reading history",
    no_readings: "No readings yet.",
    import_export: "Import / Export",
    import_hint:
      "CSV export of the iOS app “Energy Tracker” (one file per meter) or simple format: one reading per line as date;value[;replaced][;note]. Date as YYYY-MM-DD or DD.MM.YYYY, optionally with time. A header line is recognised.",
    import: "Import",
    import_files: "Choose CSV files …",
    import_text_preview: "Check text …",
    import_title: "Import preview",
    import_textfield: "Text field",
    import_analysing: "Checking files …",
    import_target: "Import into",
    import_new_meter: "+ Create new meter",
    import_replace: "Replace existing readings of this meter ({n})",
    import_period: "Period",
    import_lines: "Lines",
    import_new: "New readings",
    import_merged: "Combined same-day duplicates",
    import_skipped: "Already present (skipped)",
    import_rejected: "Rejected lines",
    import_last: "Last reading",
    import_merged_item: "{date}: {count} readings, used {kept} (latest time), not used: {dropped}",
    import_rejected_item: "Line {line}: “{text}” – {reason}",
    import_flagged_title: "Please decide: these values do not fit the neighbouring readings",
    import_decide: "– please choose –",
    import_decision_reset: "Meter replaced (new meter)",
    import_decision_keep: "Import anyway",
    import_decision_skip: "Do not import",
    import_undecided: "Please decide for all marked values first.",
    import_name_missing: "Please enter a name for the new meter.",
    import_nothing: "No valid readings found.",
    import_nothing_new: "All readings are already present.",
    import_done: "{added} readings imported into {meters} meters",
    import_item_done: "Imported: {added} new, {skipped} already present",
    flag_lower_than_previous: "lower than the reading of {date} ({value})",
    flag_higher_than_next: "higher than the later reading of {date} ({value})",
    reason_too_few_columns: "too few columns",
    reason_invalid_date: "date not recognised",
    reason_missing_value: "reading missing",
    reason_invalid_value: "reading is not a number",
    reason_negative_value: "negative reading",
    err_import_empty: "No valid readings found.",
    err_import_undecided: "Please decide for all marked values first.",
    granularity: "Resolution",
    gran_day: "Day",
    gran_week: "Week",
    gran_month: "Month",
    gran_year: "Year",
    compare: "Compare",
    compare_none: "No comparison",
    compare_prev_period: "Previous period",
    compare_prev_year: "Same period last year",
    show: "Show",
    show_estimates: "Show estimates",
    today: "Today",
    total: "Total",
    difference: "Difference",
    cumulative: "Cumulative",
    details: "Details",
    period: "Period",
    week_short: "W",
    estimate_note: "Hatched bars are estimated (average), light bars are forecasts.",
    no_cost: "Add a contract to see costs.",
    contracts_for: "Contracts",
    add_contract: "Add contract",
    no_contracts: "No contracts yet.",
    provider: "Provider",
    tariff: "Tariff",
    customer_number: "Customer number",
    start_date: "Contract start",
    end_date: "Contract end (optional)",
    unit_price: "Unit price ({currency} per {unit})",
    base_price: "Base price ({currency} per month)",
    advance_payment: "Advance payment ({currency} per payment)",
    conversion_factor: "Conversion factor ({unit} → billing unit)",
    conversion_hint:
      "For gas measured in m³ but billed per kWh: calorific value × correction factor (see your bill, approx. 10–11). Otherwise 1.",
    notice_period: "Notice period",
    open_end: "open-ended",
    runs_until: "Runs until",
    period_of: "Period {n} of {total}",
    previous: "Previous",
    next: "Next",
    finished: "finished",
    elapsed: "{p} % elapsed",
    add_meter: "Add meter",
    name: "Name",
    meter_type: "Type",
    unit: "Unit",
    meter_number: "Meter number",
    profile: "Consumption profile",
    profile_hint: "Distributes consumption between readings and for estimates over the year.",
    annual_estimate: "Reference annual consumption ({unit})",
    annual_hint: "Used while there are not enough readings. Empty = typical value ({value}).",
    confirm_delete_meter: "Delete meter \"{name}\" including all readings and contracts?",
    confirm_delete_reading: "Delete reading of {date}?",
    confirm_delete_contract: "Delete contract?",
    saved: "Saved",
    deleted: "Deleted",
    force_question: "{message}\n\nSave anyway?",
    err_value_too_low:
      "The value is lower than the previous reading. If the meter was replaced, tick “Meter replaced”.",
    err_value_too_high: "The value is higher than the following reading.",
    err_duplicate_date: "There is already a reading for this date.",
    err_invalid_dates: "The end date is before the start date.",
    reference: "Reference value",
    average_basis: "Average based on",
    days_measured: "{n} days of measured data",
    last_12_months: "Last 12 months",
    export_all: "Export all meters (CSV)",
    export_table: "Export table as CSV",
    view_photo: "Show photo",
    close: "Close",
    read_only: "Only administrators can change readings, meters and contracts.",
    dashboard_hint: "Energy dashboard: statistic “{name}”",
    stat_consumption: "consumption",
    stat_cost: "cost",
    err_unauthorized: "Administrator rights are required for this.",
    photo_button: "Reading from photo",
    photo_title: "Reading from photo",
    photo_loading: "Analysing photo …",
    photo_match_exact: "Meter “{name}” recognised by its meter number {number}.",
    photo_match_similar: "The recognised meter number {number} is similar to meter “{name}” ({stored}). Please check.",
    photo_match_single: "The meter number could not be matched. The only meter is preselected.",
    photo_match_none: "No meter with number {number} found. Please choose a meter.",
    photo_no_number: "No meter number recognised. Please choose a meter.",
    photo_no_value: "The reading could not be read. Please enter it manually.",
    photo_check: "Please compare the recognised value with the photo.",
    photo_save_number: "Store recognised meter number {number} for the chosen meter",
    photo_retry: "New photo",
    photo_last: "Last reading: {value} ({date})",
    choose: "– please choose –",
    meter_number_hint: "Photos are assigned to the meter automatically by its meter number.",
    err_ai_task_missing:
      "Photo recognition needs “AI Task” set up in Home Assistant with an AI provider that can process images.",
    err_no_ai_entity:
      "No suitable AI Task entity is set. Choose one in the Energy Tracker options or set a preferred AI Task entity in Home Assistant.",
    err_recognition_failed: "The photo could not be analysed.",
    err_no_media_dir: "No media directory is configured in Home Assistant.",
    err_invalid_image: "The file is not a valid image or too large.",
  },
};

const METER_TYPES = ["electricity", "gas", "water", "heat", "oil", "other"];
const PROFILES = ["auto", "flat", "heating", "electricity"];
const UNITS = ["kWh", "MWh", "m³", "L"];
const DEFAULT_UNIT = { electricity: "kWh", gas: "m³", water: "m³", heat: "kWh", oil: "L", other: "kWh" };
const DEFAULT_ANNUAL = {
  "electricity|kWh": 2500,
  "gas|m³": 1200,
  "gas|kWh": 12000,
  "heat|kWh": 9000,
  "heat|MWh": 9,
  "water|m³": 90,
  "water|L": 90000,
  "oil|L": 1500,
};
const TYPE_COLOR = {
  electricity: "#f9a825",
  gas: "#ef6c00",
  water: "#1e88e5",
  heat: "#e53935",
  oil: "#6d4c41",
  other: "#8e24aa",
};
const TYPE_ICON = {
  electricity: "mdi:flash",
  gas: "mdi:fire",
  water: "mdi:water",
  heat: "mdi:radiator",
  oil: "mdi:barrel",
  other: "mdi:counter",
};

/* ------------------------------------------------------------ date utils */

const DAY_MS = 86400000;
const parseDate = (iso) => {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
};
const isoDate = (date) => date.toISOString().slice(0, 10);
const addDays = (iso, days) => isoDate(new Date(parseDate(iso).getTime() + days * DAY_MS));
const addMonths = (iso, months) => {
  const d = parseDate(iso);
  const target = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + months, 1));
  const last = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate();
  target.setUTCDate(Math.min(d.getUTCDate(), last));
  return isoDate(target);
};
const startOfMonth = (iso) => iso.slice(0, 8) + "01";
const endOfMonth = (iso) => addDays(addMonths(startOfMonth(iso), 1), -1);
const startOfWeek = (iso) => addDays(iso, -((parseDate(iso).getUTCDay() + 6) % 7));
const daysBetween = (a, b) => Math.round((parseDate(b) - parseDate(a)) / DAY_MS);
const isoWeek = (iso) => {
  const d = parseDate(iso);
  const day = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - day + 3);
  const firstThursday = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
  return 1 + Math.round(((d - firstThursday) / DAY_MS - 3 + ((firstThursday.getUTCDay() + 6) % 7)) / 7);
};

/** Parse "25.600,5", "25600,5" or "25600.5" into a number. */
const parseNum = (value) => {
  let text = String(value ?? "").trim().replace(/\s/g, "");
  if (text === "") return undefined;
  if (text.includes(",")) text = text.replace(/\./g, "").replace(",", ".");
  else if ((text.match(/\./g) || []).length > 1) text = text.replace(/\./g, "");
  const num = Number(text);
  return Number.isFinite(num) ? num : NaN;
};

/** Billing date ("Stichtag") of a year, clamped to the month length. */
const billingDate = (year, day, month) => {
  const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return `${year}-${String(month).padStart(2, "0")}-${String(Math.min(day, last)).padStart(2, "0")}`;
};
/** Billing period containing a day: day after the previous billing date .. billing date. */
const billingPeriod = (iso, day = 30, month = 9) => {
  const year = Number(iso.slice(0, 4));
  let end = billingDate(year, day, month);
  if (iso > end) end = billingDate(year + 1, day, month);
  const start = addDays(billingDate(Number(end.slice(0, 4)) - 1, day, month), 1);
  return { start, end };
};
const periodLabel = (start, end) =>
  start.slice(0, 4) === end.slice(0, 4) ? start.slice(0, 4) : `${start.slice(0, 4)}/${end.slice(2, 4)}`;

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

/* ---------------------------------------------------------------- charts */

function niceScale(max, ticks = 4) {
  if (!(max > 0)) return { max: 1, step: 0.25 };
  const raw = max / ticks;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10) * mag;
  return { max: Math.ceil(max / step) * step, step };
}

/**
 * Bar chart.  groups: [{label, segments:[{value, kind}], compare:number|null}]
 * kind: measured | estimated | forecast
 */
function renderBarChart(width, height, groups, opts) {
  const pad = { l: 52, r: 8, t: 12, b: 26 };
  const w = Math.max(width - pad.l - pad.r, 50);
  const h = height - pad.t - pad.b;
  const totals = groups.map((g) => g.segments.reduce((s, x) => s + x.value, 0));
  const max = Math.max(0, ...totals, ...groups.map((g) => g.compare ?? 0));
  const scale = niceScale(max);
  const y = (v) => pad.t + h - (v / scale.max) * h;
  const n = groups.length || 1;
  const gw = w / n;
  const hasCompare = groups.some((g) => g.compare !== null && g.compare !== undefined);
  const bw = Math.max(1, hasCompare ? gw * 0.36 : gw * 0.66);
  const labelEvery = Math.max(1, Math.ceil(n / Math.max(1, w / 44)));
  const color = opts.color;
  let svg = `<svg width="${width}" height="${height}" class="chart">
    <defs><pattern id="hatch-${opts.id}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect width="6" height="6" fill="${color}" opacity="0.35"></rect>
      <line x1="0" y1="0" x2="0" y2="6" stroke="${color}" stroke-width="3" opacity="0.8"></line>
    </pattern></defs>`;
  for (let v = 0; v <= scale.max + 1e-9; v += scale.step) {
    svg += `<line x1="${pad.l}" x2="${pad.l + w}" y1="${y(v)}" y2="${y(v)}" class="grid"></line>
      <text x="${pad.l - 6}" y="${y(v) + 4}" class="axis" text-anchor="end">${esc(opts.formatAxis(v, scale.step))}</text>`;
  }
  groups.forEach((g, i) => {
    const x0 = pad.l + i * gw + (gw - (hasCompare ? bw * 2 + 2 : bw)) / 2;
    let acc = 0;
    for (const seg of g.segments) {
      if (!(seg.value > 0)) continue;
      const top = y(acc + seg.value);
      const bottom = y(acc);
      const fill =
        seg.kind === "measured" ? color : seg.kind === "estimated" ? `url(#hatch-${opts.id})` : color;
      const opacity = seg.kind === "forecast" ? 0.25 : 1;
      svg += `<rect x="${x0}" y="${top}" width="${bw}" height="${Math.max(0, bottom - top)}" fill="${fill}" opacity="${opacity}" rx="1.5"></rect>`;
      acc += seg.value;
    }
    if (hasCompare && g.compare > 0) {
      const top = y(g.compare);
      svg += `<rect x="${x0 + bw + 2}" y="${top}" width="${bw}" height="${y(0) - top}" class="cmp-bar" rx="1.5"></rect>`;
    }
    if (i % labelEvery === 0) {
      svg += `<text x="${pad.l + i * gw + gw / 2}" y="${height - 8}" class="axis" text-anchor="middle">${esc(g.label)}</text>`;
    }
    svg += `<rect x="${pad.l + i * gw}" y="${pad.t}" width="${gw}" height="${h}" fill="transparent" class="hover" data-idx="${i}"></rect>`;
  });
  svg += `<line x1="${pad.l}" x2="${pad.l + w}" y1="${y(0)}" y2="${y(0)}" class="baseline"></line></svg>`;
  return svg;
}

/**
 * Line chart.  series: [{points:[{x, y, dashed}], color, cls}]
 * x values are numbers; xLabel formats them.
 */
function renderLineChart(width, height, series, opts) {
  const pad = { l: 60, r: 12, t: 12, b: 26 };
  const w = Math.max(width - pad.l - pad.r, 50);
  const h = height - pad.t - pad.b;
  const all = series.flatMap((s) => s.points);
  if (!all.length) return "";
  const xs = all.map((p) => p.x);
  const ys = all.map((p) => p.y);
  const xMin = opts.xMin ?? Math.min(...xs);
  const xMax = opts.xMax ?? Math.max(...xs);
  let yMin = opts.zero ? 0 : Math.min(...ys);
  const yMaxRaw = Math.max(...ys);
  let scale = niceScale(yMaxRaw - yMin || Math.abs(yMaxRaw) || 1);
  if (!opts.zero) {
    // align the lower bound to the tick step so that ticks are round numbers
    yMin = Math.max(0, Math.floor(yMin / scale.step) * scale.step);
    scale = niceScale(yMaxRaw - yMin);
    yMin = Math.max(0, Math.floor(Math.min(...ys) / scale.step) * scale.step);
  }
  const yMax = Math.max(yMin + scale.max, Math.ceil(yMaxRaw / scale.step) * scale.step);
  const x = (v) => pad.l + (xMax === xMin ? w / 2 : ((v - xMin) / (xMax - xMin)) * w);
  const y = (v) => pad.t + h - ((v - yMin) / (yMax - yMin || 1)) * h;
  let svg = `<svg width="${width}" height="${height}" class="chart">`;
  for (let v = yMin; v <= yMax + 1e-9; v += scale.step) {
    svg += `<line x1="${pad.l}" x2="${pad.l + w}" y1="${y(v)}" y2="${y(v)}" class="grid"></line>
      <text x="${pad.l - 6}" y="${y(v) + 4}" class="axis" text-anchor="end">${esc(opts.formatAxis(v, scale.step))}</text>`;
  }
  for (const tick of opts.xTicks(xMin, xMax, w)) {
    svg += `<text x="${x(tick.x)}" y="${height - 8}" class="axis" text-anchor="middle">${esc(tick.label)}</text>`;
  }
  for (const s of series) {
    const solid = s.points.filter((p, i) => !p.dashed || (s.points[i - 1] && !s.points[i - 1].dashed));
    const dashedStart = s.points.findIndex((p) => p.dashed);
    const dashed = dashedStart >= 0 ? s.points.slice(Math.max(0, dashedStart - 1)) : [];
    const path = (pts) => pts.map((p, i) => `${i ? "L" : "M"}${x(p.x).toFixed(1)},${y(p.y).toFixed(1)}`).join(" ");
    if (solid.length) svg += `<path d="${path(solid)}" fill="none" stroke="${s.color}" stroke-width="2" class="${s.cls || ""}"></path>`;
    if (dashed.length > 1)
      svg += `<path d="${path(dashed)}" fill="none" stroke="${s.color}" stroke-width="2" stroke-dasharray="5 4" opacity="0.7"></path>`;
    if (s.markers) {
      for (const p of s.points) {
        svg += `<circle cx="${x(p.x)}" cy="${y(p.y)}" r="${p.marker === "reset" ? 5 : 3}" fill="${p.marker === "reset" ? "var(--error-color)" : s.color}"><title>${esc(p.title || "")}</title></circle>`;
      }
    }
  }
  svg += `</svg>`;
  return svg;
}

/**
 * Cost chart: stacked bars (energy + base cost) per year, gaps with a label,
 * forecast years lighter, optional consumption line on a second axis.
 * spec.years: [{label, energy, base, gap, forecast, consumption}]
 */
function renderCostChart(width, height, spec, opts) {
  const line = spec.showLine && spec.years.some((y) => y.consumption > 0);
  const pad = { l: 64, r: line ? 64 : 12, t: line ? 28 : 14, b: 28 };
  const w = Math.max(width - pad.l - pad.r, 50);
  const h = height - pad.t - pad.b;
  const n = spec.years.length || 1;
  const max = Math.max(0, ...spec.years.map((y) => (y.split ? (y.energy || 0) + (y.base || 0) : y.total || 0)));
  const scale = niceScale(max);
  const y = (v) => pad.t + h - (v / scale.max) * h;
  const gw = w / n;
  const bw = Math.max(4, Math.min(gw * 0.6, 90));
  const color = spec.color;
  let svg = `<svg width="${width}" height="${height}" class="chart">`;
  for (let v = 0; v <= scale.max + 1e-9; v += scale.step) {
    svg += `<line x1="${pad.l}" x2="${pad.l + w}" y1="${y(v)}" y2="${y(v)}" class="grid"></line>
      <text x="${pad.l - 6}" y="${y(v) + 4}" class="axis" text-anchor="end">${esc(opts.formatMoney(v, scale.step))}</text>`;
  }
  spec.years.forEach((yr, i) => {
    const cx = pad.l + i * gw + gw / 2;
    const x0 = cx - bw / 2;
    if (yr.gap) {
      svg += `<rect x="${x0}" y="${pad.t + h * 0.35}" width="${bw}" height="${h * 0.65}" class="gap-bar" rx="3"></rect>
        <text x="${cx}" y="${pad.t + h * 0.35 + 16}" class="axis gap-text" text-anchor="middle">${esc(yr.gapText)}</text>`;
    } else {
      const op = yr.forecast ? 0.45 : 1;
      let top2;
      if (yr.split) {
        const top1 = y(yr.energy);
        svg += `<rect x="${x0}" y="${top1}" width="${bw}" height="${Math.max(0, y(0) - top1)}" fill="${color}" opacity="${op}"></rect>`;
        top2 = y(yr.energy + yr.base);
        svg += `<rect x="${x0}" y="${top2}" width="${bw}" height="${Math.max(0, top1 - top2)}" fill="${color}" opacity="${op * 0.45}"></rect>`;
      } else {
        // split into energy and base cost unknown: one bar for the total
        top2 = y(yr.total);
        svg += `<rect x="${x0}" y="${top2}" width="${bw}" height="${Math.max(0, y(0) - top2)}" fill="${color}" opacity="${op * 0.75}" class="unsplit-bar"></rect>`;
      }
      if (yr.forecast) {
        svg += `<rect x="${x0}" y="${top2}" width="${bw}" height="${Math.max(0, y(0) - top2)}" fill="none" stroke="${color}" stroke-dasharray="4 3" stroke-width="1.5"></rect>`;
      }
      if (yr.partial) {
        svg += `<text x="${cx}" y="${top2 - 4}" class="axis warn-fill" text-anchor="middle">!</text>`;
      }
    }
    svg += `<text x="${cx}" y="${height - 8}" class="axis" text-anchor="middle">${esc(yr.label)}</text>`;
  });
  if (line) {
    const values = spec.years.map((yr) => yr.consumption ?? null);
    const lscale = niceScale(Math.max(...values.filter((v) => v !== null)));
    const ly = (v) => pad.t + h - (v / lscale.max) * h;
    for (let v = 0; v <= lscale.max + 1e-9; v += lscale.step) {
      svg += `<text x="${pad.l + w + 6}" y="${ly(v) + 4}" class="axis">${esc(opts.formatUnit(v, lscale.step))}</text>`;
    }
    let path = "";
    let dashed = "";
    values.forEach((v, i) => {
      if (v === null) return;
      const px = pad.l + i * gw + gw / 2;
      const cmd = `${path ? "L" : "M"}${px.toFixed(1)},${ly(v).toFixed(1)}`;
      if (spec.years[i].forecast) {
        const prev = values[i - 1];
        if (prev !== null && prev !== undefined && !dashed) dashed = `M${(pad.l + (i - 1) * gw + gw / 2).toFixed(1)},${ly(prev).toFixed(1)}`;
        dashed += `${dashed ? " L" : "M"}${px.toFixed(1)},${ly(v).toFixed(1)}`;
      } else {
        path += (path ? " " : "") + cmd;
      }
      svg += `<circle cx="${px}" cy="${ly(v)}" r="3.5" class="line-dot"></circle>`;
    });
    if (path) svg += `<path d="${path}" fill="none" class="cons-line"></path>`;
    if (dashed) svg += `<path d="${dashed}" fill="none" class="cons-line" stroke-dasharray="5 4"></path>`;
    svg += `<text x="${pad.l + w + 6}" y="${pad.t - 14}" class="axis">${esc(spec.unit)}</text>`;
  }
  spec.years.forEach((_, i) => {
    svg += `<rect x="${pad.l + i * gw}" y="${pad.t}" width="${gw}" height="${h}" fill="transparent" class="hover" data-idx="${i}"></rect>`;
  });
  svg += `<line x1="${pad.l}" x2="${pad.l + w}" y1="${y(0)}" y2="${y(0)}" class="baseline"></line></svg>`;
  return svg;
}

/* ----------------------------------------------------------------- panel */

class EnergyTrackerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._state = {
      tab: "overview",
      meterId: null,
      gran: "month",
      anchor: null,
      compare: "prev_year",
      mode: "consumption",
      estimates: true,
      editReading: null,
      editContract: null,
      editMeter: null,
      showMeterForm: false,
      showContractForm: false,
      billingIndex: {},
    };
    this._data = null;
    this._overview = null;
    this._sparks = {};
    this._stats = null;
    this._billing = {};
    this._charts = {};
    this._loaded = false;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (this._menuButton) this._menuButton.hass = hass;
    if (first) {
      this._setup();
      this._reload();
    }
  }

  get hass() {
    return this._hass;
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menuButton) this._menuButton.narrow = narrow;
  }

  set panel(panel) {
    this._panel = panel;
  }

  connectedCallback() {
    if (!this._resizeObserver) {
      this._resizeObserver = new ResizeObserver(() => {
        clearTimeout(this._resizeTimer);
        this._resizeTimer = setTimeout(() => this._drawCharts(), 100);
      });
    }
    this._resizeObserver.observe(this);
  }

  disconnectedCallback() {
    this._resizeObserver?.disconnect();
  }

  /* ---------------------------------------------------------- helpers */

  _t(key, params = {}) {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").startsWith("de") ? "de" : "en";
    let text = STRINGS[lang][key] ?? STRINGS.en[key] ?? key;
    for (const [k, v] of Object.entries(params)) text = text.replaceAll(`{${k}}`, v);
    return text;
  }

  get _lang() {
    return this._hass?.locale?.language || this._hass?.language || "en";
  }

  _num(value, digits = 1) {
    if (value === null || value === undefined || Number.isNaN(value)) return "–";
    return new Intl.NumberFormat(this._lang, { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
  }

  /** Number for input fields: no grouping, locale decimal separator. */
  _plain(value) {
    return new Intl.NumberFormat(this._lang, { useGrouping: false, maximumFractionDigits: 4 }).format(value);
  }

  _auto(value) {
    const abs = Math.abs(value);
    return this._num(value, abs >= 1000 ? 0 : abs >= 100 ? 1 : 2);
  }

  _axis(value, step, costAware, money = false) {
    const digits = step >= 1 ? 0 : step >= 0.1 ? 1 : 2;
    if (money || (costAware && this._state.mode === "cost")) {
      return new Intl.NumberFormat(this._lang, {
        style: "currency",
        currency: this._data?.currency || "EUR",
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      }).format(value);
    }
    return this._num(value, digits);
  }

  _money(value) {
    if (value === null || value === undefined) return "–";
    return new Intl.NumberFormat(this._lang, { style: "currency", currency: this._data?.currency || "EUR" }).format(value);
  }

  _date(iso, opts = { day: "2-digit", month: "2-digit", year: "numeric" }) {
    if (!iso) return "–";
    return new Intl.DateTimeFormat(this._lang, { ...opts, timeZone: "UTC" }).format(parseDate(iso));
  }

  _monthName(iso, style = "short") {
    return new Intl.DateTimeFormat(this._lang, { month: style, timeZone: "UTC" }).format(parseDate(iso));
  }

  _meter(id) {
    return this._data?.meters.find((m) => m.id === id);
  }

  get _currencySymbol() {
    try {
      return (
        new Intl.NumberFormat(this._lang, { style: "currency", currency: this._data?.currency || "EUR" })
          .formatToParts(0)
          .find((p) => p.type === "currency")?.value || "€"
      );
    } catch (e) {
      return "€";
    }
  }

  async _ws(type, data = {}) {
    return this._hass.callWS({ type: `${DOMAIN}/${type}`, ...data });
  }

  _toast(message, error = false) {
    const el = this.shadowRoot.querySelector(".toast");
    el.textContent = message;
    el.className = `toast show ${error ? "error" : ""}`;
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => (el.className = "toast"), error ? 6000 : 2500);
  }

  _errorText(err) {
    const key = `err_${err?.code}`;
    const text = this._t(key);
    if (text === key) return err?.message || String(err);
    return err?.code === "recognition_failed" && err.message ? `${text}\n${err.message}` : text;
  }

  /* -------------------------------------------------------- data flow */

  async _reload() {
    try {
      const [data, overview] = await Promise.all([this._ws("data"), this._ws("overview")]);
      this._data = data;
      this._overview = overview;
      this._loaded = true;
      if (!this._state.anchor) this._state.anchor = data.today;
      if (!this._state.meterId || !this._meter(this._state.meterId)) {
        this._state.meterId = data.meters[0]?.id || null;
      }
      this._render();
      await this._loadTabData();
    } catch (err) {
      this._loaded = true;
      this._render();
      this._toast(this._errorText(err), true);
    }
  }

  async _loadTabData() {
    const tab = this._state.tab;
    try {
      if (tab === "overview") await this._loadSparks();
      if (tab === "analysis") await this._loadStats();
      if (tab === "contracts") await this._loadBilling();
      if (tab === "costs") await this._loadCosts();
    } catch (err) {
      this._toast(this._errorText(err), true);
    }
  }

  async _loadSparks() {
    const today = this._data.today;
    const start = addMonths(startOfMonth(today), -11);
    const end = endOfMonth(today);
    const results = await Promise.all(
      this._data.meters.map((m) =>
        this._ws("statistics", { meter_id: m.id, start, end, granularity: "month" }).then((r) => [m.id, r])
      )
    );
    this._sparks = Object.fromEntries(results);
    this._drawCharts();
  }

  _range() {
    const { gran, anchor } = this._state;
    if (gran === "billing") {
      const meter = this._meter(this._state.meterId) || {};
      const day = meter.billing_day || 30;
      const month = meter.billing_month || 9;
      const period = billingPeriod(anchor, day, month);
      const prev = billingPeriod(addDays(period.start, -1), day, month);
      return {
        ...period,
        granularity: "month",
        label: `${this._t("billing_year")} ${periodLabel(period.start, period.end)}`,
        prev_period: prev,
        prev_year: prev,
      };
    }
    if (gran === "day") {
      const start = startOfMonth(anchor);
      const end = endOfMonth(anchor);
      return {
        start,
        end,
        label: this._date(start, { month: "long", year: "numeric" }),
        prev_period: { start: addMonths(start, -1), end: endOfMonth(addMonths(start, -1)) },
        prev_year: { start: addMonths(start, -12), end: endOfMonth(addMonths(start, -12)) },
      };
    }
    if (gran === "week") {
      const end = addDays(startOfWeek(anchor), 6);
      const start = addDays(end, -12 * 7 + 1);
      return {
        start,
        end,
        label: `${this._t("week_short")} ${isoWeek(start)} – ${this._t("week_short")} ${isoWeek(end)} ${end.slice(0, 4)}`,
        prev_period: { start: addDays(start, -84), end: addDays(end, -84) },
        prev_year: { start: addDays(start, -364), end: addDays(end, -364) },
      };
    }
    if (gran === "month") {
      const year = anchor.slice(0, 4);
      const start = `${year}-01-01`;
      const end = `${year}-12-31`;
      const prev = { start: `${year - 1}-01-01`, end: `${year - 1}-12-31` };
      return { start, end, label: year, prev_period: prev, prev_year: prev };
    }
    const year = Number(anchor.slice(0, 4));
    return {
      start: `${year - 4}-01-01`,
      end: `${year}-12-31`,
      label: `${year - 4} – ${year}`,
      prev_period: { start: `${year - 9}-01-01`, end: `${year - 5}-12-31` },
      prev_year: { start: `${year - 5}-01-01`, end: `${year - 1}-12-31` },
    };
  }

  _shiftAnchor(direction) {
    const { gran, anchor } = this._state;
    if (direction === 0) this._state.anchor = this._data.today;
    else if (gran === "day") this._state.anchor = addMonths(anchor, direction);
    else if (gran === "week") this._state.anchor = addDays(anchor, direction * 84);
    else this._state.anchor = addMonths(anchor, direction * 12);
  }

  async _loadStats() {
    if (!this._state.meterId) return;
    const range = this._range();
    const req = {
      meter_id: this._state.meterId,
      start: range.start,
      end: range.end,
      granularity: range.granularity || this._state.gran,
    };
    if (this._state.compare !== "none") {
      req.compare_start = range[this._state.compare].start;
      req.compare_end = range[this._state.compare].end;
    }
    this._stats = await this._ws("statistics", req);
    if (this._state.tab === "analysis") this._render();
  }

  async _loadCosts() {
    const s = this._state;
    s.costMeter = s.costMeter || "all";
    s.costMode = s.costMode || "calendar";
    const req = { mode: s.costMode };
    if (s.costMeter !== "all") req.meter_id = s.costMeter;
    this._costs = await this._ws("cost_history", req);
    this._costs.key = `${s.costMeter}|${s.costMode}`;
    if (s.tab === "costs") this._render();
  }

  async _loadBilling() {
    const meterId = this._state.meterId;
    if (!meterId) return;
    const req = { meter_id: meterId };
    if (this._state.billingIndex[meterId] !== undefined) req.period_index = this._state.billingIndex[meterId];
    this._billing[meterId] = await this._ws("billing", req);
    if (this._state.tab === "contracts") this._render();
  }

  /* ----------------------------------------------------------- render */

  _setup() {
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <div class="header">
        <div class="toolbar"><span class="menu"></span><div class="main-title">${esc(this._t("title"))}</div></div>
        <div class="tabs"></div>
      </div>
      <div class="content"></div>
      <div class="tooltip"></div>
      <div class="modal-host"></div>
      <div class="import-host"></div>
      <input class="csv-input" type="file" accept=".csv,.txt,text/csv,text/plain" multiple hidden>
      <input class="photo-input" type="file" accept="image/*" capture="environment" hidden>
      <div class="toast"></div>`;
    this.shadowRoot.querySelector(".photo-input").addEventListener("change", (ev) => {
      const file = ev.target.files?.[0];
      ev.target.value = "";
      if (file) this._onPhotoSelected(file);
    });
    this.shadowRoot.querySelector(".csv-input").addEventListener("change", async (ev) => {
      const files = [...(ev.target.files || [])];
      ev.target.value = "";
      if (!files.length) return;
      const sources = await Promise.all(files.map(async (f) => ({ name: f.name, text: await f.text() })));
      this._startImport(sources);
    });
    const menu = document.createElement("ha-menu-button");
    menu.hass = this._hass;
    menu.narrow = this._narrow;
    this._menuButton = menu;
    this.shadowRoot.querySelector(".menu").appendChild(menu);
    const root = this.shadowRoot;
    root.addEventListener("click", (ev) => this._onClick(ev));
    root.addEventListener("change", (ev) => this._onChange(ev));
    root.addEventListener("submit", (ev) => this._onSubmit(ev));
    root.addEventListener("mousemove", (ev) => this._onHover(ev));
    root.addEventListener("mouseleave", () => this._hideTooltip(), true);
  }

  _render() {
    if (!this.shadowRoot.querySelector(".content")) return;
    const tabs = ["overview", "analysis", "readings", "contracts", "costs", "meters"];
    this.shadowRoot.querySelector(".tabs").innerHTML = tabs
      .map(
        (tab) =>
          `<button class="tab ${tab === this._state.tab ? "active" : ""}" data-action="tab" data-tab="${tab}">${esc(this._t(`tab_${tab}`))}</button>`
      )
      .join("");
    const content = this.shadowRoot.querySelector(".content");
    if (!this._loaded) {
      content.innerHTML = `<div class="empty">${esc(this._t("loading"))}</div>`;
      return;
    }
    if (!this._data) {
      content.innerHTML = "";
      return;
    }
    this._charts = {};
    const admin = this._hass?.user?.is_admin !== false;
    content.classList.toggle("readonly", !admin);
    let html = "";
    if (!this._data.meters.length && this._state.tab !== "meters") {
      html = `<div class="card empty">${esc(this._t("no_meters"))}<br><br>
        <button class="primary admin-only" data-action="tab" data-tab="meters" data-new="1">${esc(this._t("add_first_meter"))}</button>
        <button class="flat admin-only" data-action="import-files">${esc(this._t("import_files"))}</button>
        <p class="hint admin-only">${esc(this._t("import_hint"))}</p></div>`;
    } else {
      html = this[`_render_${this._state.tab}`]();
    }
    content.innerHTML = (admin ? "" : `<div class="notice">${esc(this._t("read_only"))}</div>`) + html;
    this._drawCharts();
  }

  _meterSelect() {
    return `<label class="field inline"><span>${esc(this._t("meter"))}</span>
      <select data-bind="meterId">${this._data.meters
        .map((m) => `<option value="${m.id}" ${m.id === this._state.meterId ? "selected" : ""}>${esc(m.name)} (${esc(this._t(`type_${m.type}`))})</option>`)
        .join("")}</select></label>`;
  }

  _photoButton() {
    return `<button class="primary with-icon admin-only" data-action="photo"><ha-icon icon="mdi:camera"></ha-icon>${esc(this._t("photo_button"))}</button>`;
  }

  /* photo recognition */

  async _prepareImage(file) {
    // Downscale in the browser: faster upload and cheaper recognition.
    try {
      const bitmap = await createImageBitmap(file);
      const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(bitmap.width * scale);
      canvas.height = Math.round(bitmap.height * scale);
      canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.88));
      if (blob) return blob;
    } catch (e) {
      // fall through: send the original file
    }
    return file;
  }

  async _onPhotoSelected(file) {
    this._closePhoto();
    const photo = { url: URL.createObjectURL(file), status: "loading" };
    this._photo = photo;
    this._renderPhoto();
    try {
      const blob = await this._prepareImage(file);
      const resp = await this._hass.fetchWithAuth(`/api/${DOMAIN}/recognize`, {
        method: "POST",
        body: blob,
        headers: { "Content-Type": blob.type || "image/jpeg" },
      });
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok) throw body.code ? body : { message: `HTTP ${resp.status}` };
      photo.status = "ready";
      photo.result = body;
    } catch (err) {
      photo.status = "error";
      photo.error = this._errorText(err);
    }
    if (this._photo === photo) this._renderPhoto();
  }

  _closePhoto() {
    const photo = this._photo;
    if (photo?.url && !photo.viewer) URL.revokeObjectURL(photo.url);
    // an uploaded photo that was not saved with a reading is removed again
    if (photo?.result?.photo_id && !photo.saved) {
      this._ws("photo/discard", { photo_id: photo.result.photo_id }).catch(() => {});
    }
    this._photo = null;
    this._renderPhoto();
  }

  async _viewPhoto(readingId) {
    const reading = this._data.readings.find((r) => r.id === readingId);
    if (!reading?.photo) return;
    try {
      const media = await this._hass.callWS({ type: "media_source/resolve_media", media_content_id: reading.photo });
      const meter = this._meter(reading.meter_id);
      this._photo = {
        viewer: true,
        url: media.url,
        caption: `${meter?.name || ""} · ${this._date(reading.date)} · ${this._num(reading.value, 2)} ${meter?.unit || ""}`,
      };
      this._renderPhoto();
    } catch (err) {
      this._toast(this._errorText(err), true);
    }
  }

  _photoInfo(result) {
    const meter = result.meter_id ? this._meter(result.meter_id) : null;
    const number = result.meter_number;
    if (meter && result.match === "exact") {
      return { cls: "good", text: this._t("photo_match_exact", { name: meter.name, number }) };
    }
    if (meter && ["partial", "fuzzy"].includes(result.match)) {
      return { cls: "warn", text: this._t("photo_match_similar", { name: meter.name, number, stored: meter.number }) };
    }
    if (meter && result.match === "single") return { cls: "warn", text: this._t("photo_match_single") };
    return { cls: "warn", text: number ? this._t("photo_match_none", { number }) : this._t("photo_no_number") };
  }

  _photoLastText(meterId) {
    const ov = this._overview?.find((o) => o.meter.id === meterId);
    if (!ov?.last_reading) return "";
    return this._t("photo_last", {
      value: `${this._num(ov.last_reading.value, 2)} ${ov.meter.unit}`,
      date: this._date(ov.last_reading.date),
    });
  }

  _renderPhoto() {
    const host = this.shadowRoot?.querySelector(".modal-host");
    if (!host) return;
    const p = this._photo;
    if (!p) {
      host.innerHTML = "";
      return;
    }
    if (p.viewer) {
      host.innerHTML = `<div class="modal-backdrop"><div class="modal card">
        <div class="card-title">${esc(p.caption)}</div>
        <img class="photo-preview large" src="${esc(p.url)}" alt="">
        <div class="buttons end"><button type="button" class="primary" data-action="photo-close">${esc(this._t("close"))}</button></div>
      </div></div>`;
      return;
    }
    let body;
    if (p.status === "loading") {
      body = `<div class="photo-status"><div class="spinner"></div>${esc(this._t("photo_loading"))}</div>
        <div class="buttons end"><button type="button" class="flat" data-action="photo-close">${esc(this._t("cancel"))}</button></div>`;
    } else if (p.status === "error") {
      body = `<div class="notice bad">${esc(p.error)}</div>
        <div class="buttons end"><button type="button" class="flat" data-action="photo-close">${esc(this._t("cancel"))}</button>
        <button type="button" class="primary" data-action="photo">${esc(this._t("photo_retry"))}</button></div>`;
    } else {
      const r = p.result;
      const info = this._photoInfo(r);
      const offerNumber = r.meter_number && r.match !== "exact";
      body = `<div class="notice ${info.cls}">${esc(info.text)}</div>
        ${r.value === null ? `<div class="notice warn">${esc(this._t("photo_no_value"))}</div>` : ""}
        <form data-form="photo" class="form-grid">
          <label class="field wide"><span>${esc(this._t("meter"))}</span>
            <select name="meter_id" data-bind="photoMeter" required>
              <option value="">${esc(this._t("choose"))}</option>
              ${this._data.meters
                .map((m) => `<option value="${m.id}" ${m.id === r.meter_id ? "selected" : ""}>${esc(m.name)} (${esc(this._t(`type_${m.type}`))}${m.number ? `, ${esc(m.number)}` : ""})</option>`)
                .join("")}
            </select><small class="photo-last">${esc(this._photoLastText(r.meter_id))}</small></label>
          <label class="field"><span>${esc(this._t("value"))}${r.unit ? ` (${esc(r.unit)})` : ""}</span>
            <input type="text" name="value" inputmode="decimal" pattern="[0-9]+([.,][0-9]+)*" autocomplete="off" required value="${r.value === null ? "" : esc(this._plain(r.value))}">
            <small>${esc(this._t("photo_check"))}</small></label>
          <label class="field"><span>${esc(this._t("date"))}</span><input type="date" name="date" required value="${esc(this._data.today)}"></label>
          <label class="check wide"><input type="checkbox" name="reset"> ${esc(this._t("meter_replaced"))}</label>
          ${offerNumber ? `<label class="check wide"><input type="checkbox" name="save_number" ${r.match === "none" || r.match === "single" ? "checked" : ""}> ${esc(this._t("photo_save_number", { number: r.meter_number }))}</label>` : ""}
          <div class="buttons wide end"><button type="button" class="flat" data-action="photo-close">${esc(this._t("cancel"))}</button>
            <button type="button" class="flat" data-action="photo">${esc(this._t("photo_retry"))}</button>
            <button class="primary" type="submit">${esc(this._t("save"))}</button></div>
        </form>`;
    }
    host.innerHTML = `<div class="modal-backdrop"><div class="modal card">
      <div class="card-title">${esc(this._t("photo_title"))}</div>
      <img class="photo-preview" src="${p.url}" alt="">
      ${body}</div></div>`;
  }

  async _saveReading(payload) {
    try {
      await this._ws("reading/save", payload);
      return true;
    } catch (err) {
      const forceable = ["value_too_low", "value_too_high"].includes(err.code);
      if (!forceable || !confirm(this._t("force_question", { message: this._errorText(err) }))) {
        this._toast(this._errorText(err), true);
        return false;
      }
    }
    try {
      await this._ws("reading/save", { ...payload, force: true });
      return true;
    } catch (err) {
      this._toast(this._errorText(err), true);
      return false;
    }
  }

  /* csv import */

  async _startImport(sources) {
    this._import = {
      busy: true,
      items: sources.map((src) => ({
        name: src.name,
        label: src.label || src.name,
        text: src.text,
        meterId: src.meterId || null,
        target: src.meterId || "new",
        newMeter: { name: "", type: "electricity", unit: "kWh" },
        replace: false,
        decisions: {},
        preview: null,
        error: null,
        done: null,
      })),
    };
    this._renderImport();
    for (const item of this._import.items) await this._previewItem(item, true);
    if (!this._import) return;
    this._import.busy = false;
    this._renderImport();
  }

  async _previewItem(item, initial) {
    const req = { name: item.name, text: item.text, replace: item.replace };
    if (initial) {
      if (item.meterId) req.meter_id = item.meterId;
      else req.suggest = true;
    } else if (item.target !== "new") {
      req.meter_id = item.target;
    }
    try {
      const preview = await this._ws("import/preview", req);
      item.preview = preview;
      item.error = null;
      if (initial) {
        item.target = preview.meter_id || "new";
        const sug = preview.suggestion;
        item.newMeter = { name: sug.name, type: sug.type, unit: sug.unit };
      }
      const flagged = new Set(preview.flagged.map((f) => f.date));
      for (const day of Object.keys(item.decisions)) if (!flagged.has(day)) delete item.decisions[day];
    } catch (err) {
      item.error = this._errorText(err);
    }
  }

  async _onImportChange(el) {
    const item = this._import?.items[Number(el.dataset.idx)];
    if (!item) return;
    const field = el.dataset.field;
    if (field === "decision") {
      if (el.value) item.decisions[el.dataset.date] = el.value;
      else delete item.decisions[el.dataset.date];
      return;
    }
    if (field === "name") {
      item.newMeter.name = el.value;
      return;
    }
    if (field === "unit") {
      item.newMeter.unit = el.value;
      return;
    }
    if (field === "type") {
      item.newMeter.type = el.value;
      item.newMeter.unit = DEFAULT_UNIT[el.value];
    } else if (field === "target") {
      item.target = el.value;
      if (el.value === "new") item.replace = false;
      await this._previewItem(item, false);
    } else if (field === "replace") {
      item.replace = el.checked;
      await this._previewItem(item, false);
    }
    this._renderImport();
  }

  async _commitImport() {
    const imp = this._import;
    if (!imp || imp.busy) return;
    const todo = imp.items.filter((item) => !item.done && item.preview && item.preview.days > 0);
    for (const item of todo) {
      if (item.preview.flagged.some((f) => !item.decisions[f.date])) {
        this._toast(this._t("import_undecided"), true);
        return;
      }
      if (item.target === "new" && !item.newMeter.name.trim()) {
        this._toast(this._t("import_name_missing"), true);
        return;
      }
    }
    imp.busy = true;
    this._renderImport();
    let failed = false;
    for (const item of todo) {
      const req = { text: item.text, replace: item.replace, decisions: item.decisions };
      if (item.target === "new") {
        req.new_meter = { name: item.newMeter.name.trim(), meter_type: item.newMeter.type, unit: item.newMeter.unit };
      } else {
        req.meter_id = item.target;
      }
      try {
        item.done = await this._ws("import/commit", req);
        item.error = null;
        // a retry must not create the meter a second time
        item.target = item.done.meter_id;
      } catch (err) {
        item.error = this._errorText(err);
        failed = true;
      }
    }
    imp.busy = false;
    const done = imp.items.filter((item) => item.done);
    if (done.length) {
      this._state.meterId = done[0].done.meter_id;
      this._toast(
        this._t("import_done", {
          added: done.reduce((sum, item) => sum + item.done.added, 0),
          meters: new Set(done.map((item) => item.done.meter_id)).size,
        })
      );
    }
    if (!failed) this._import = null;
    this._renderImport();
    if (done.length) await this._reload();
  }

  _importItemHtml(item, idx) {
    const p = item.preview;
    const title = `<div class="card-title">${esc(item.label || this._t("import_textfield"))}</div>`;
    if (item.done) {
      return `<div class="import-item">${title}<div class="notice good">${esc(this._t("import_item_done", item.done))}</div></div>`;
    }
    if (!p) {
      return `<div class="import-item">${title}${item.error ? `<div class="notice bad">${esc(item.error)}</div>` : `<div class="photo-status"><div class="spinner"></div>${esc(this._t("import_analysing"))}</div>`}</div>`;
    }
    const attr = (field) => `data-bind="imp" data-idx="${idx}" data-field="${field}"`;
    const isNew = item.target === "new";
    const existingCount = isNew ? 0 : this._data.readings.filter((r) => r.meter_id === item.target).length;
    const fact = (label, value, cls = "") => `<div class="${cls}"><span>${esc(label)}</span><strong>${value}</strong></div>`;
    const list = (label, entries) =>
      entries.length
        ? `<details><summary>${esc(label)} (${entries.length})</summary><ul>${entries.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></details>`
        : "";
    let html = `<div class="import-item">${title}
      ${item.error ? `<div class="notice bad">${esc(item.error)}</div>` : ""}
      <div class="form-grid">
        <label class="field"><span>${esc(this._t("import_target"))}</span>
          <select ${attr("target")}>
            ${this._data.meters.map((m) => `<option value="${m.id}" ${m.id === item.target ? "selected" : ""}>${esc(m.name)} (${esc(this._t(`type_${m.type}`))}, ${esc(m.unit)})</option>`).join("")}
            <option value="new" ${isNew ? "selected" : ""}>${esc(this._t("import_new_meter"))}</option>
          </select></label>
        ${isNew ? `<label class="field"><span>${esc(this._t("name"))}</span><input ${attr("name")} maxlength="100" value="${esc(item.newMeter.name)}"></label>
        <label class="field"><span>${esc(this._t("meter_type"))}</span><select ${attr("type")}>${METER_TYPES.map((t) => `<option value="${t}" ${t === item.newMeter.type ? "selected" : ""}>${esc(this._t(`type_${t}`))}</option>`).join("")}</select></label>
        <label class="field"><span>${esc(this._t("unit"))}</span><select ${attr("unit")}>${UNITS.map((u) => `<option ${u === item.newMeter.unit ? "selected" : ""}>${u}</option>`).join("")}</select></label>` : ""}
        ${!isNew && existingCount ? `<label class="check wide"><input type="checkbox" ${attr("replace")} ${item.replace ? "checked" : ""}> ${esc(this._t("import_replace", { n: existingCount }))}</label>` : ""}
      </div>`;
    if (!p.days) {
      html += `<div class="notice warn">${esc(this._t("import_nothing"))}</div>`;
    } else {
      html += `<div class="billing-facts import-facts">
        ${fact(this._t("import_period"), `${this._date(p.start)} – ${this._date(p.end)}`)}
        ${fact(this._t("import_last"), `${this._num(p.last_value, 2)} (${this._date(p.end)})`)}
        ${fact(this._t("import_lines"), p.data_lines)}
        ${fact(this._t("import_new"), p.new, "strong")}
        ${fact(this._t("import_merged"), p.merged_lines)}
        ${fact(this._t("import_skipped"), p.skipped_existing.length)}
        ${fact(this._t("import_rejected"), p.rejected.length, p.rejected.length ? "bad" : "")}
      </div>`;
      if (!p.new) html += `<div class="notice">${esc(this._t("import_nothing_new"))}</div>`;
    }
    html += list(
      this._t("import_merged"),
      p.merged.map((m) =>
        this._t("import_merged_item", {
          date: this._date(m.date),
          count: m.count,
          kept: this._num(m.kept, 2),
          dropped: m.dropped.map((v) => this._num(v, 2)).join(" / "),
        })
      )
    );
    html += list(this._t("import_skipped"), p.skipped_existing.map((d) => this._date(d)));
    html += list(
      this._t("import_rejected"),
      p.rejected.map((r) => this._t("import_rejected_item", { line: r.line, text: r.text, reason: this._t(`reason_${r.reason}`) }))
    );
    if (p.flagged.length) {
      html += `<div class="notice warn">${esc(this._t("import_flagged_title"))}
        <div class="table-wrap"><table><tbody>${p.flagged
          .map(
            (f) => `<tr><td>${this._date(f.date)}</td><td class="num"><strong>${this._num(f.value, 2)}</strong></td>
            <td class="wrap">${esc(this._t(`flag_${f.reason}`, { date: this._date(f.other_date), value: this._num(f.other_value, 2) }))}</td>
            <td><select ${attr("decision")} data-date="${f.date}">
              <option value="">${esc(this._t("import_decide"))}</option>
              ${["reset", "keep", "skip"].map((d) => `<option value="${d}" ${item.decisions[f.date] === d ? "selected" : ""}>${esc(this._t(`import_decision_${d}`))}</option>`).join("")}
            </select></td></tr>`
          )
          .join("")}</tbody></table></div></div>`;
    }
    return html + `</div>`;
  }

  _renderImport() {
    const host = this.shadowRoot?.querySelector(".import-host");
    if (!host) return;
    const imp = this._import;
    if (!imp) {
      host.innerHTML = "";
      return;
    }
    const scroll = host.querySelector(".modal")?.scrollTop || 0;
    const importable = imp.items.some((item) => !item.done && item.preview && item.preview.days > 0);
    host.innerHTML = `<div class="modal-backdrop"><div class="modal wide-modal card">
      <div class="card-title">${esc(this._t("import_title"))}</div>
      ${imp.items.map((item, idx) => this._importItemHtml(item, idx)).join("")}
      <div class="buttons end">
        ${imp.busy ? `<div class="spinner"></div>` : ""}
        <button type="button" class="flat" data-action="import-close">${esc(this._t(importable ? "cancel" : "close"))}</button>
        <button type="button" class="primary" data-action="import-commit" ${imp.busy || !importable ? "disabled" : ""}>${esc(this._t("import"))}</button>
      </div></div></div>`;
    const modal = host.querySelector(".modal");
    if (modal) modal.scrollTop = scroll;
  }

  _icon(type) {
    return `<ha-icon icon="${TYPE_ICON[type] || "mdi:counter"}" style="color:${TYPE_COLOR[type]}"></ha-icon>`;
  }

  _qualityBadge(quality) {
    return `<span class="badge q-${quality}" title="${esc(quality === "good" ? "" : this._t(`quality_hint_${quality}`))}">${esc(this._t(`quality_${quality}`))}</span>`;
  }

  /* overview */

  _render_overview() {
    return `<div class="actions-row">${this._photoButton()}</div>
      <div class="grid">${this._overview.map((ov) => this._overviewCard(ov)).join("")}</div>`;
  }

  _figure(label, value, sub = "") {
    return `<div class="figure"><div class="label">${esc(label)}</div><div class="value">${value}</div>${sub ? `<div class="sub">${sub}</div>` : ""}</div>`;
  }

  _delta(current, previous) {
    if (!previous) return "";
    const pct = ((current - previous) / previous) * 100;
    if (Math.abs(pct) < 0.5) return `<span class="delta">±0 %</span>`;
    const cls = pct > 0 ? "up" : "down";
    return `<span class="delta ${cls}">${pct > 0 ? "+" : ""}${this._num(pct, 0)} %</span>`;
  }

  _overviewCard(ov) {
    const m = ov.meter;
    const u = esc(m.unit);
    const last = ov.last_reading;
    const billing = ov.billing;
    this._charts[`spark-${m.id}`] = () => this._sparkChart(m);
    return `<div class="card meter-card" style="--accent:${TYPE_COLOR[m.type]}">
      <div class="card-head">
        ${this._icon(m.type)}
        <div class="grow"><div class="card-title">${esc(m.name)}</div>
          <div class="muted">${esc(this._t(`type_${m.type}`))}${m.number ? " · " + esc(m.number) : ""}</div></div>
        ${this._qualityBadge(ov.quality)}
      </div>
      <div class="last-reading">
        <div><div class="muted">${esc(this._t("last_reading"))}</div>
          <div class="big">${last ? `${this._num(last.value, 2)} ${u}` : esc(this._t("none_yet"))}</div>
          ${last ? `<div class="muted">${this._date(last.date)}</div>` : ""}</div>
        <button class="primary admin-only" data-action="quick-reading" data-meter="${m.id}">${esc(this._t("add_reading"))}</button>
      </div>
      <div class="figures">
        ${this._figure(this._t("this_month"), `${this._auto(ov.month_to_date.total)} ${u}`,
          `${esc(this._t("forecast"))}: ${this._auto(ov.month_forecast.total)} ${u}`)}
        ${this._figure(this._t("previous_month"), `${this._auto(ov.previous_month.total)} ${u}`,
          this._delta(ov.month_forecast.total, ov.previous_month.total))}
        ${this._figure(this._t("this_year"), `${this._auto(ov.year_to_date.total)} ${u}`,
          `${esc(this._t("forecast"))}: ${this._auto(ov.year_forecast.total)} ${u}`)}
        ${this._figure(this._t("previous_year"), `${this._auto(ov.previous_year.total)} ${u}`,
          this._delta(ov.year_forecast.total, ov.previous_year.total))}
        ${this._figure(this._t("per_day"), `${this._num(ov.average_daily, 2)} ${u}`,
          `≈ ${this._auto(ov.annual_rate)} ${u} ${esc(this._t("per_year"))}`)}
        ${this._figure(this._t("forecast_year_cost"), this._money(ov.year_forecast.cost), ov.year_forecast.cost === null ? esc(this._t("no_cost")) : this._coverageShort(ov.year_forecast.cost_coverage))}
      </div>
      <div class="spark-title muted">${esc(this._t("last_12_months"))}</div>
      <div class="chart-box spark" data-chart="spark-${m.id}"></div>
      ${billing ? this._billingSummary(billing) : ""}
      ${ov.last_bill ? this._lastBillLine(ov.last_bill) : ""}
    </div>`;
  }

  _sparkChart(meter) {
    const stats = this._sparks[meter.id];
    if (!stats) return null;
    return {
      type: "bar",
      height: 110,
      groups: stats.buckets.map((b) => ({
        label: this._monthName(b.key, "narrow"),
        segments: [
          { value: b.measured, kind: "measured" },
          { value: b.estimated, kind: "estimated" },
          { value: b.forecast, kind: "forecast" },
        ],
        compare: null,
        bucket: b,
      })),
      color: TYPE_COLOR[meter.type],
      unit: meter.unit,
      gran: "month",
    };
  }

  _resultBox(billing) {
    const cls = billing.result === "refund" ? "good" : billing.result === "additional_payment" ? "bad" : "";
    const prefix = billing.finished ? "calculated" : "expected";
    const label =
      billing.result === "refund"
        ? this._t(`${prefix}_refund`)
        : billing.result === "additional_payment"
          ? this._t(`${prefix}_payment`)
          : this._t("expected_even");
    return `<div class="result ${cls}">
      <div class="label">${esc(label)}</div>
      <div class="amount">${this._money(Math.abs(billing.balance))}</div>
    </div>`;
  }

  _coverageShort(coverage) {
    if (coverage === undefined || coverage === null || coverage >= 0.9995) return "";
    return `<span class="warn-text">${esc(this._t("cost_partial_short", { p: this._num(coverage * 100, 0) }))}</span>`;
  }

  _coverageNotice(billing) {
    if (billing.cost_coverage >= 0.9995) return "";
    if (billing.cost_coverage <= 0) return `<div class="notice">${esc(this._t("coverage_none"))}</div>`;
    return `<div class="notice warn">${esc(this._t("coverage_partial", { p: this._num(billing.cost_coverage * 100, 0) }))}</div>`;
  }

  _signedResult(value) {
    if (value === null || value === undefined) return "–";
    if (Math.abs(value) < 0.005) return esc(this._t("expected_even"));
    return esc(this._t(value > 0 ? "refund_x" : "payment_x", { v: this._money(Math.abs(value)) }));
  }

  _billingSummary(billing) {
    const pct = Math.round(billing.progress * 100);
    const providers = [...new Set(billing.segments.map((seg) => seg.provider).filter(Boolean))].join(", ");
    let body;
    if (billing.result === "no_tariff") {
      body = `<div class="muted">${esc(this._t("no_tariff_period"))}</div>`;
    } else {
      body = `<div class="billing-row">
        ${this._resultBox(billing)}
        <div class="billing-facts">
          <div><span>${esc(this._t("total_cost"))}</span><strong>${this._money(billing.total_cost)}</strong></div>
          <div><span>${esc(this._t("advance_total"))} (${billing.payments_count})</span><strong>${this._money(billing.advance_total)}</strong></div>
          <div><span>${esc(this._t("recommended_advance"))}</span><strong>${this._money(billing.recommended_advance)} ${esc(this._t("times"))} ${billing.payments_per_year}</strong></div>
        </div>
      </div>${billing.cost_coverage < 0.9995 ? `<div class="hint warn-text">${esc(this._t("coverage_partial", { p: this._num(billing.cost_coverage * 100, 0) }))}</div>` : ""}`;
    }
    return `<div class="billing">
      <div class="billing-head"><strong>${esc(this._t("billing_year"))} ${esc(billing.label)}</strong>
        <span class="muted">${providers ? `${esc(providers)} · ` : ""}${this._date(billing.start)} – ${this._date(billing.end)}</span></div>
      <div class="progress" title="${esc(this._t("elapsed", { p: pct }))}"><div style="width:${pct}%"></div></div>
      ${body}
    </div>`;
  }

  _lastBillLine(details) {
    const dev = details.comparison.balance;
    return `<div class="billing-head last-bill"><span>${esc(this._t("last_bill"))} ${esc(details.label)}</span>
      <span><strong>${this._signedResult(details.result)}</strong>${dev ? ` <span class="muted">(${esc(this._t("deviation"))} ${dev.diff > 0 ? "+" : ""}${this._money(dev.diff)})</span>` : ""}</span></div>`;
  }

  /* analysis */

  _render_analysis() {
    const s = this._state;
    const meter = this._meter(s.meterId);
    const range = this._range();
    const grans = ["day", "week", "month", "year", "billing"];
    const compares = ["none", "prev_period", "prev_year"];
    let html = `<div class="card controls">
      ${this._meterSelect()}
      <div class="segmented">${grans
        .map((g) => `<button class="${g === s.gran ? "active" : ""}" data-action="gran" data-gran="${g}">${esc(this._t(`gran_${g}`))}</button>`)
        .join("")}</div>
      <div class="nav">
        <button class="icon" data-action="shift" data-dir="-1" title="${esc(this._t("previous"))}">‹</button>
        <span class="range-label">${esc(range.label)}</span>
        <button class="icon" data-action="shift" data-dir="1" title="${esc(this._t("next"))}">›</button>
        <button class="flat" data-action="shift" data-dir="0">${esc(this._t("today"))}</button>
      </div>
      <label class="field inline"><span>${esc(this._t("compare"))}</span>
        <select data-bind="compare">${compares
          .map((c) => `<option value="${c}" ${c === s.compare ? "selected" : ""}>${esc(this._t(`compare_${c}`))}</option>`)
          .join("")}</select></label>
      <div class="segmented">
        <button class="${s.mode === "consumption" ? "active" : ""}" data-action="mode" data-mode="consumption">${esc(this._t("consumption"))}</button>
        <button class="${s.mode === "cost" ? "active" : ""}" data-action="mode" data-mode="cost">${esc(this._t("cost"))}</button>
      </div>
      <label class="check"><input type="checkbox" data-bind="estimates" ${s.estimates ? "checked" : ""}> ${esc(this._t("show_estimates"))}</label>
    </div>`;
    const stats = this._stats;
    if (!stats || stats.meter_id !== s.meterId || stats.start !== range.start || stats.granularity !== (range.granularity || s.gran)) {
      return html + `<div class="card empty">${esc(this._t("loading"))}</div>`;
    }
    const value = (b) => this._bucketValue(b);
    const total = stats.buckets.reduce((acc, b) => acc + (value(b) ?? 0), 0);
    const cmpTotal = stats.compare ? stats.compare.buckets.reduce((acc, b) => acc + (value(b) ?? 0), 0) : null;
    const fmt = (v) => (s.mode === "cost" ? this._money(v) : `${this._auto(v)} ${esc(meter.unit)}`);
    const days = stats.summary.days || 1;
    const hasCost = stats.buckets.some((b) => b.cost !== null);
    html += `<div class="card">
      <div class="figures wide">
        ${this._figure(this._t("total"), fmt(total), s.estimates ? `${esc(this._t("measured"))}: ${this._auto(stats.summary.measured)} ${esc(meter.unit)}` : "")}
        ${cmpTotal !== null ? this._figure(this._t(`compare_${s.compare}`), fmt(cmpTotal), this._delta(total, cmpTotal)) : ""}
        ${cmpTotal !== null ? this._figure(this._t("difference"), fmt(total - cmpTotal)) : ""}
        ${this._figure(this._t("per_day"), s.mode === "cost" ? this._money(total / days) : `${this._num(total / days, 2)} ${esc(meter.unit)}`)}
      </div>
      ${s.mode === "cost" && !hasCost ? `<div class="hint">${esc(this._t("no_cost"))}</div>` : ""}
      <div class="chart-box" data-chart="main"></div>
      <div class="legend">
        <span><i style="background:${TYPE_COLOR[meter.type]}"></i>${esc(this._t("measured"))}</span>
        ${s.estimates ? `<span><i class="hatched" style="--c:${TYPE_COLOR[meter.type]}"></i>${esc(this._t("estimated"))}</span>
        <span><i style="background:${TYPE_COLOR[meter.type]};opacity:.25"></i>${esc(this._t("forecasted"))}</span>` : ""}
        ${stats.compare ? `<span><i class="cmp"></i>${esc(this._t(`compare_${s.compare}`))}</span>` : ""}
      </div>
      ${s.estimates ? `<div class="hint">${esc(this._t("estimate_note"))}</div>` : ""}
    </div>
    ${s.gran !== "year" ? `<div class="card"><div class="card-title">${esc(this._t("cumulative"))}</div>
      <div class="chart-box" data-chart="cumulative"></div></div>` : ""}
    <div class="card"><details><summary>${esc(this._t("details"))}</summary>${this._statsTable(stats, meter)}</details>
      <div class="buttons"><button type="button" class="flat" data-action="export-stats">${esc(this._t("export_table"))}</button></div></div>`;
    this._charts.main = () => this._mainChart(stats, meter);
    this._charts.cumulative = () => this._cumulativeChart(stats, meter);
    return html;
  }

  _bucketValue(b) {
    if (this._state.mode === "cost") return b.cost;
    return this._state.estimates ? b.total : b.measured;
  }

  _bucketLabel(b, gran, long = false) {
    if (gran === "day") return long ? this._date(b.start, { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric" }) : String(Number(b.start.slice(8)));
    if (gran === "week") return long ? `${this._t("week_short")} ${isoWeek(b.key)} (${this._date(b.start)} – ${this._date(b.end)})` : `${isoWeek(b.key)}`;
    if (gran === "month") return long ? this._date(b.key, { month: "long", year: "numeric" }) : this._monthName(b.key);
    return b.key.slice(0, 4);
  }

  _mainChart(stats, meter) {
    const s = this._state;
    return {
      type: "bar",
      height: 280,
      groups: stats.buckets.map((b, i) => {
        const cmp = stats.compare?.buckets[i];
        const segments =
          s.mode === "cost"
            ? [{ value: b.cost ?? 0, kind: b.forecast > b.measured + b.estimated ? "forecast" : b.measured >= b.estimated ? "measured" : "estimated" }]
            : s.estimates
              ? [
                  { value: b.measured, kind: "measured" },
                  { value: b.estimated, kind: "estimated" },
                  { value: b.forecast, kind: "forecast" },
                ]
              : [{ value: b.measured, kind: "measured" }];
        return {
          label: this._bucketLabel(b, stats.granularity),
          segments,
          compare: cmp ? this._bucketValue(cmp) ?? 0 : null,
          bucket: b,
          cmpBucket: cmp,
        };
      }),
      color: TYPE_COLOR[meter.type],
      unit: meter.unit,
      gran: stats.granularity,
    };
  }

  _cumulativeChart(stats, meter) {
    const today = this._data.today;
    const cumulate = (buckets, markFuture) => {
      let acc = 0;
      return buckets.map((b, i) => {
        acc += this._bucketValue(b) ?? 0;
        return { x: i, y: acc, dashed: markFuture && b.start > today };
      });
    };
    const series = [];
    if (stats.compare) series.push({ points: cumulate(stats.compare.buckets, false), color: "var(--secondary-text-color)", cls: "cmp-line" });
    series.push({ points: cumulate(stats.buckets, true), color: TYPE_COLOR[meter.type] });
    const labels = stats.buckets.map((b) => this._bucketLabel(b, stats.granularity));
    return {
      type: "line",
      height: 220,
      series,
      zero: true,
      xTicks: (min, max, w) => {
        const every = Math.max(1, Math.ceil(labels.length / Math.max(1, w / 44)));
        return labels.map((label, i) => ({ x: i, label })).filter((_, i) => i % every === 0);
      },
      xMin: 0,
      xMax: Math.max(1, labels.length - 1),
    };
  }

  _statsTable(stats, meter) {
    const u = esc(meter.unit);
    const rows = stats.buckets
      .map((b, i) => {
        const cmp = stats.compare?.buckets[i];
        return `<tr><td>${esc(this._bucketLabel(b, stats.granularity, true))}</td>
          <td class="num">${this._num(b.measured, 2)}</td><td class="num">${this._num(b.estimated + b.forecast, 2)}</td>
          <td class="num"><strong>${this._num(b.total, 2)}</strong></td>
          ${stats.compare ? `<td class="num">${cmp ? this._num(cmp.total, 2) : "–"}</td><td class="num">${cmp ? this._delta(b.total, cmp.total) : ""}</td>` : ""}
          <td class="num">${b.cost !== null ? this._money(b.cost) : "–"}</td></tr>`;
      })
      .join("");
    return `<div class="table-wrap"><table><thead><tr><th>${esc(this._t("period"))}</th>
      <th class="num">${esc(this._t("measured"))} (${u})</th><th class="num">${esc(this._t("estimated"))} (${u})</th>
      <th class="num">${esc(this._t("total"))} (${u})</th>
      ${stats.compare ? `<th class="num">${esc(this._t(`compare_${this._state.compare}`))}</th><th class="num">%</th>` : ""}
      <th class="num">${esc(this._t("cost"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  /* readings */

  _render_readings() {
    const s = this._state;
    const meter = this._meter(s.meterId);
    const readings = this._data.readings.filter((r) => r.meter_id === s.meterId).sort((a, b) => (a.date + (a.reset ? 1 : 0) < b.date + (b.reset ? 1 : 0) ? -1 : 1));
    const editing = s.editReading ? readings.find((r) => r.id === s.editReading) : null;
    const u = esc(meter.unit);
    let html = `<div class="card controls">${this._meterSelect()}${this._photoButton()}</div>
      <div class="card admin-only"><div class="card-title">${esc(editing ? this._t("edit") : this._t("add_reading"))}</div>
      <form data-form="reading" class="form-row">
        <label class="field"><span>${esc(this._t("date"))}</span><input type="date" name="date" required value="${esc(editing?.date || this._data.today)}"></label>
        <label class="field"><span>${esc(this._t("value"))} (${u})</span><input type="text" name="value" inputmode="decimal" pattern="[0-9]+([.,][0-9]+)*" autocomplete="off" required value="${editing ? esc(editing.value) : ""}" autofocus></label>
        <label class="field grow"><span>${esc(this._t("note"))}</span><input type="text" name="note" value="${esc(editing?.note || "")}"></label>
        <label class="check"><input type="checkbox" name="reset" ${editing?.reset ? "checked" : ""}> ${esc(this._t("meter_replaced"))}</label>
        <div class="buttons"><button class="primary" type="submit">${esc(editing ? this._t("update") : this._t("save"))}</button>
        ${editing ? `<button type="button" class="flat" data-action="cancel-edit">${esc(this._t("cancel"))}</button>` : ""}</div>
      </form></div>`;
    if (readings.length > 1) {
      html += `<div class="card"><div class="card-title">${esc(this._t("readings_chart"))}</div><div class="chart-box" data-chart="readings"></div></div>`;
      this._charts.readings = () => this._readingsChart(readings, meter);
    }
    if (!readings.length) {
      html += `<div class="card empty">${esc(this._t("no_readings"))}</div>`;
    } else {
      const rows = [];
      for (let i = readings.length - 1; i >= 0; i--) {
        const r = readings[i];
        const prev = readings[i - 1];
        let since = "";
        if (prev && !r.reset && r.date > prev.date) {
          const diff = r.value - prev.value;
          const days = daysBetween(prev.date, r.date);
          since = `${this._num(diff, 2)} ${u} <span class="muted">(${this._num(diff / days, 2)} ${u}/d)</span>`;
        }
        rows.push(`<tr class="${r.id === s.editReading ? "editing" : ""}"><td>${this._date(r.date)}</td>
          <td class="num"><strong>${this._num(r.value, 2)}</strong> ${r.reset ? `<span class="badge q-low">${esc(this._t("replaced_short"))}</span>` : ""}${r.source === "bill" ? ` <span class="badge source-bill" title="${esc(r.note || "")}">${esc(this._t("from_bill"))}</span>` : ""}</td>
          <td class="num">${since}</td><td>${esc(r.note || "")}</td>
          <td class="actions">${r.photo ? `<button class="icon" data-action="view-photo" data-id="${r.id}" title="${esc(this._t("view_photo"))}"><ha-icon icon="mdi:image"></ha-icon></button>` : ""}<button class="icon admin-only" data-action="edit-reading" data-id="${r.id}" title="${esc(this._t("edit"))}"><ha-icon icon="mdi:pencil"></ha-icon></button>
          <button class="icon admin-only" data-action="delete-reading" data-id="${r.id}" title="${esc(this._t("delete"))}"><ha-icon icon="mdi:delete"></ha-icon></button></td></tr>`);
      }
      html += `<div class="card"><div class="table-wrap"><table><thead><tr><th>${esc(this._t("date"))}</th><th class="num">${esc(this._t("value"))} (${u})</th>
        <th class="num">${esc(this._t("since_previous"))}</th><th>${esc(this._t("note"))}</th><th></th></tr></thead><tbody>${rows.join("")}</tbody></table></div></div>`;
    }
    html += `<div class="card"><details><summary>${esc(this._t("import_export"))}</summary>
      <p class="hint admin-only">${esc(this._t("import_hint"))}</p>
      <form data-form="import"><div class="buttons admin-only"><button type="button" class="primary with-icon" data-action="import-files"><ha-icon icon="mdi:file-upload"></ha-icon>${esc(this._t("import_files"))}</button></div>
      <textarea class="admin-only" name="csv" rows="5" placeholder="2025-01-01;12345,6"></textarea>
      <div class="buttons"><button class="flat admin-only" type="submit">${esc(this._t("import_text_preview"))}</button>
      <button type="button" class="flat" data-action="export">${esc(this._t("export"))}</button>
      <button type="button" class="flat" data-action="export-all">${esc(this._t("export_all"))}</button></div></form></details></div>`;
    return html;
  }

  _readingsChart(readings, meter) {
    return {
      type: "line",
      height: 220,
      series: [
        {
          color: TYPE_COLOR[meter.type],
          markers: true,
          points: readings.map((r) => ({
            x: parseDate(r.date).getTime(),
            y: r.value,
            marker: r.reset ? "reset" : null,
            title: `${this._date(r.date)}: ${this._num(r.value, 2)} ${meter.unit}`,
          })),
        },
      ],
      xTicks: (min, max, w) => {
        const count = Math.max(2, Math.floor(w / 90));
        const ticks = [];
        for (let i = 0; i < count; i++) {
          const x = min + ((max - min) * i) / (count - 1);
          ticks.push({ x, label: this._date(isoDate(new Date(x)), { month: "short", year: "2-digit" }) });
        }
        return ticks;
      },
    };
  }

  /* contracts */

  _render_contracts() {
    const s = this._state;
    const meter = this._meter(s.meterId);
    const data = this._billing[s.meterId];
    const contracts = this._data.contracts.filter((c) => c.meter_id === s.meterId).sort((a, b) => (a.start_date < b.start_date ? -1 : 1));
    const bills = this._data.bills.filter((b) => b.meter_id === s.meterId);
    let html = `<div class="card controls">${this._meterSelect()}
      <button class="primary admin-only" data-action="new-contract">${esc(this._t("add_contract"))}</button>
      <button class="flat admin-only" data-action="new-bill">${esc(this._t("add_bill"))}</button></div>`;
    if (s.showContractForm) html += this._contractForm(meter, contracts.find((c) => c.id === s.editContract));
    if (s.showBillForm) html += this._billForm(meter, bills.find((b) => b.id === s.editBill), data);
    if (!data || data.meter_id !== s.meterId) return html + `<div class="card empty">${esc(this._t("loading"))}</div>`;
    html += this._gapsNotice(data.tariff_gaps);
    html += this._periodCard(data, meter);
    html += `<h3 class="section-title">${esc(this._t("tariffs_title"))}</h3>`;
    if (!contracts.length) html += `<div class="card empty">${esc(this._t("no_contracts"))}</div>`;
    for (const c of contracts) html += this._contractCard(c, meter);
    html += `<h3 class="section-title">${esc(this._t("bills_title"))}</h3>`;
    if (!data.bills.length) html += `<div class="card empty">${esc(this._t("no_bills"))}</div>`;
    for (const details of data.bills) html += this._billCard(details, meter);
    return html;
  }

  _gapsNotice(gaps) {
    const lines = [];
    for (const gap of gaps.gaps) lines.push(this._t("tariff_gap", { start: this._date(gap.start), end: this._date(gap.end) }));
    if (gaps.after) lines.push(this._t("tariff_after", { start: this._date(gaps.after.start) }));
    let html = lines.length ? `<div class="notice warn">${lines.map((l) => esc(l)).join("<br>")}</div>` : "";
    if (gaps.before) {
      html += `<div class="notice">${esc(this._t("tariff_before", { start: this._date(gaps.before.start), end: this._date(gaps.before.end) }))}</div>`;
    }
    return html;
  }

  _readingFact(label, value, kind, unit) {
    if (value === null || value === undefined) return "";
    return `<div><span>${esc(label)}${kind ? ` <em>(${esc(this._t(`kind_${kind}`))})</em>` : ""}</span><strong>${this._num(value, 2)} ${esc(unit)}</strong></div>`;
  }

  _periodCard(data, meter) {
    const b = data.selected;
    const idx = data.selected_index;
    const periods = data.periods;
    const cons = b.consumption;
    const u = esc(meter.unit);
    const pct = Math.round(b.progress * 100);
    const share = (v) => (cons.total ? (v / cons.total) * 100 : 0);
    const billed = Math.abs(b.consumption_billing_unit - cons.total) > 0.01 ? ` (${this._auto(b.consumption_billing_unit)} kWh)` : "";
    let html = `<div class="card" style="--accent:${TYPE_COLOR[meter.type]}">
      <div class="billing-head">
        <button class="icon" data-action="period" data-idx="${idx - 1}" ${idx <= 0 ? "disabled" : ""}>‹</button>
        <div class="grow center"><div class="card-title">${esc(this._t("billing_year"))} ${esc(b.label)}</div>
          <div class="muted">${this._date(b.start)} – ${this._date(b.end)} · ${esc(this._t("period_of", { n: idx + 1, total: periods.length }))} · ${b.finished ? esc(this._t("finished")) : esc(this._t("elapsed", { p: pct }))}</div></div>
        <button class="icon" data-action="period" data-idx="${idx + 1}" ${idx >= periods.length - 1 ? "disabled" : ""}>›</button>
      </div>
      <div class="progress"><div style="width:${pct}%"></div></div>
      ${this._coverageNotice(b)}
      <div class="billing-row">
        ${b.result !== "no_tariff" ? this._resultBox(b) : ""}
        <div class="billing-facts">
          ${this._readingFact(this._t("reading_start"), b.reading_start, b.reading_start_kind, meter.unit)}
          ${this._readingFact(this._t("reading_end"), b.reading_end, b.reading_end_kind, meter.unit)}
          <div><span>${esc(this._t("consumption"))}</span><strong>${this._auto(cons.total)} ${u}${billed}</strong></div>
          ${b.cost_coverage > 0 ? `
          <div><span>${esc(this._t("energy_cost"))}</span><strong>${this._money(b.energy_cost)}</strong></div>
          <div><span>${esc(this._t("base_cost"))}</span><strong>${this._money(b.base_cost)}</strong></div>
          <div><span>${esc(this._t("total_cost"))}</span><strong>${this._money(b.total_cost)}</strong></div>` : ""}
          ${b.payments_count ? `
          <div><span>${esc(this._t("advance_total"))} (${b.payments_count})</span><strong>${this._money(b.advance_total)}</strong></div>
          <div><span>${esc(this._t("paid_to_date"))}</span><strong>${this._money(b.paid_to_date)}</strong></div>` : ""}
          ${b.cost_coverage > 0 && !b.finished ? `<div><span>${esc(this._t("recommended_advance"))}</span><strong>${this._money(b.recommended_advance)} ${esc(this._t("times"))} ${b.payments_per_year}</strong></div>` : ""}
        </div>
      </div>
      <div class="stack-bar" title="${esc(this._t("measured_share"))}: ${this._num(b.measured_share * 100, 0)} %">
        <div style="width:${share(cons.measured)}%;background:var(--accent)"></div>
        <div class="hatched" style="width:${share(cons.estimated)}%;--c:var(--accent)"></div>
        <div style="width:${share(cons.forecast)}%;background:var(--accent);opacity:.25"></div>
      </div>
      <div class="legend">
        <span><i style="background:var(--accent)"></i>${esc(this._t("measured"))} ${this._auto(cons.measured)} ${u}</span>
        <span><i class="hatched" style="--c:var(--accent)"></i>${esc(this._t("estimated"))} ${this._auto(cons.estimated)} ${u}</span>
        <span><i style="background:var(--accent);opacity:.25"></i>${esc(this._t("forecasted"))} ${this._auto(cons.forecast)} ${u}</span>
      </div>`;
    if (b.segments.length) {
      html += `<details ${b.segments.length > 1 ? "open" : ""}><summary>${esc(this._t("segments"))} (${b.segments.length})</summary><div class="table-wrap"><table>
        <thead><tr><th>${esc(this._t("tariff"))}</th><th>${esc(this._t("period"))}</th><th class="num">${esc(this._t("days"))}</th>
        <th class="num">${esc(this._t("consumption"))}</th><th class="num">${esc(this._t("unit_price_short"))}</th><th class="num">${esc(this._t("base_price_short"))}</th><th class="num">${esc(this._t("energy_cost"))}</th><th class="num">${esc(this._t("base_cost"))}</th></tr></thead><tbody>
        ${b.segments.map((seg) => `<tr><td>${esc([seg.provider, seg.tariff].filter(Boolean).join(" · ") || "–")}${seg.note ? `<div class="muted small">${esc(seg.note)}</div>` : ""}</td>
          <td>${this._date(seg.start)} – ${this._date(seg.end)}</td><td class="num">${seg.days}</td>
          <td class="num">${this._auto(seg.consumption)} ${u}</td>
          <td class="num">${this._num(seg.unit_price, 4)} ${esc(this._currencySymbol)}${seg.conversion_factor !== 1 ? ` <span class="muted">(${esc(this._t("factor_short"))} ${this._num(seg.conversion_factor, 4)})</span>` : ""}</td>
          <td class="num">${this._money(seg.base_price)}</td><td class="num">${this._money(seg.energy_cost)}</td><td class="num">${this._money(seg.base_cost)}</td></tr>`).join("")}
        </tbody></table></div></details>`;
    }
    if (b.payments.length) {
      html += `<details><summary>${esc(this._t("payments"))} (${b.payments.length})</summary><div class="table-wrap"><table><tbody>
        ${b.payments.map((p) => `<tr><td>${this._date(p.date)}</td><td class="num">${this._money(p.amount)}</td><td class="muted">${esc(this._t(p.paid ? "paid" : "open_payment"))}</td></tr>`).join("")}
        </tbody></table></div></details>`;
    }
    if (data.bill) html += this._comparisonHtml(data.bill, meter);
    return html + `</div>`;
  }

  _comparisonHtml(details, meter) {
    const c = details.comparison;
    const unit = details.bill.consumption_unit === "billing" ? "kWh" : meter.unit;
    const row = (label, item, fmt) => {
      if (!item) return "";
      const pct = item.pct === null || item.pct === undefined ? "" : ` (${item.pct > 0 ? "+" : ""}${this._num(item.pct, 1)} %)`;
      const cls = Math.abs(item.diff) < 0.005 ? "" : "warn-text";
      return `<tr><td>${esc(label)}</td><td class="num">${fmt(item.own)}</td><td class="num">${fmt(item.bill)}</td>
        <td class="num ${cls}">${item.diff > 0 ? "+" : ""}${fmt(item.diff)}${pct}</td></tr>`;
    };
    const vol = (v) => `${this._num(v, 2)} ${esc(unit)}`;
    const money = (v) => this._money(v);
    return `<div class="comparison"><div class="card-title">${esc(this._t("comparison"))}</div>
      <div class="table-wrap"><table><thead><tr><th></th><th class="num">${esc(this._t("own_calc"))}</th><th class="num">${esc(this._t("bill_col"))}</th><th class="num">${esc(this._t("deviation"))}</th></tr></thead><tbody>
      ${row(this._t("consumption"), c.consumption, vol)}
      ${row(this._t("total_cost"), c.total_cost, money)}
      ${row(this._t("advances"), c.advances, money)}
      ${c.balance ? `<tr><td>${esc(this._t("bill_result"))}</td><td class="num">${this._signedResult(c.balance.own)}</td><td class="num">${this._signedResult(c.balance.bill)}</td>
        <td class="num ${Math.abs(c.balance.diff) < 0.005 ? "" : "warn-text"}">${c.balance.diff > 0 ? "+" : ""}${this._money(c.balance.diff)}</td></tr>` : ""}
      </tbody></table></div>
      ${c.cost_coverage < 0.9995 ? `<div class="hint">${esc(c.cost_coverage > 0 ? this._t("coverage_partial", { p: this._num(c.cost_coverage * 100, 0) }) : this._t("coverage_none"))}</div>` : ""}
    </div>`;
  }

  _billCard(details, meter) {
    const bill = details.bill;
    const unit = bill.consumption_unit === "billing" ? "kWh" : meter.unit;
    const dev = details.comparison;
    const result = details.result;
    const cls = result === null ? "" : result >= 0 ? "good" : "bad";
    return `<div class="card">
      <div class="card-head"><div class="grow"><div class="card-title">${esc(this._t("billing_year"))} ${esc(details.label)}</div>
        <div class="muted">${this._date(bill.start_date)} – ${this._date(bill.end_date)}${bill.note ? ` · ${esc(bill.note)}` : ""}</div></div>
        <span class="badge result-badge ${cls}">${this._signedResult(result)}</span>
        <button class="icon admin-only" data-action="edit-bill" data-id="${bill.id}" title="${esc(this._t("edit"))}"><ha-icon icon="mdi:pencil"></ha-icon></button>
        <button class="icon admin-only" data-action="delete-bill" data-id="${bill.id}" title="${esc(this._t("delete"))}"><ha-icon icon="mdi:delete"></ha-icon></button></div>
      <div class="chips">
        ${bill.consumption !== null && bill.consumption !== undefined ? `<span>${esc(this._t("consumption"))}: <strong>${this._num(bill.consumption, 2)} ${esc(unit)}</strong></span>` : ""}
        ${bill.total_cost !== null && bill.total_cost !== undefined ? `<span>${esc(this._t("total_cost"))}: <strong>${this._money(bill.total_cost)}</strong></span>` : ""}
        ${bill.advances_paid !== null && bill.advances_paid !== undefined ? `<span>${esc(this._t("advances"))}: <strong>${this._money(bill.advances_paid)}</strong></span>` : ""}
        ${bill.reading_start !== null && bill.reading_start !== undefined ? `<span>${esc(this._t("reading_bill_start"))}: <strong>${this._num(bill.reading_start, 2)}</strong></span>` : ""}
        ${bill.reading_end !== null && bill.reading_end !== undefined ? `<span>${esc(this._t("reading_bill_end"))}: <strong>${this._num(bill.reading_end, 2)}</strong>${bill.reading_end_estimated ? ` (${esc(this._t("estimated_short"))})` : ""}</span>` : ""}
        ${bill.unit_price ? `<span>${esc(this._t("energy_cost"))}: <strong>${this._num(bill.unit_price, 4)} ${esc(this._currencySymbol)}</strong></span>` : ""}
        ${bill.base_price ? `<span>${esc(this._t("base_cost"))}: <strong>${this._money(bill.base_price)} ${esc(this._t("per_month"))}</strong></span>` : ""}
        ${bill.new_advance !== null && bill.new_advance !== undefined ? `<span>${esc(this._t("new_advance"))}: <strong>${this._money(bill.new_advance)}</strong>${bill.new_advance_from ? ` ${esc(this._t("advance_from"))} ${this._date(bill.new_advance_from)}` : ""}</span>` : ""}
        ${dev.consumption ? `<span>${esc(this._t("deviation"))} ${esc(this._t("consumption"))}: <strong>${dev.consumption.diff > 0 ? "+" : ""}${this._num(dev.consumption.pct ?? 0, 1)} %</strong></span>` : ""}
        ${dev.total_cost ? `<span>${esc(this._t("deviation"))} ${esc(this._t("cost"))}: <strong>${dev.total_cost.diff > 0 ? "+" : ""}${this._money(dev.total_cost.diff)}</strong></span>` : ""}
      </div></div>`;
  }

  _contractCard(c, meter) {
    const cur = this._currencySymbol;
    const billingUnit = c.conversion_factor && c.conversion_factor !== 1 ? "kWh" : meter.unit;
    const changes = c.advance_changes || [];
    return `<div class="card" style="--accent:${TYPE_COLOR[meter.type]}">
      <div class="card-head"><div class="grow"><div class="card-title">${esc(c.provider || this._t("tab_contracts"))}${c.tariff ? ` · ${esc(c.tariff)}` : ""}</div>
        <div class="muted">${this._date(c.start_date)} – ${c.end_date ? this._date(c.end_date) : esc(this._t("open_end"))}${c.customer_number ? ` · ${esc(this._t("customer_number"))} ${esc(c.customer_number)}` : ""}${c.notice_period ? ` · ${esc(this._t("notice_period"))}: ${esc(c.notice_period)}` : ""}</div></div>
        <button class="icon admin-only" data-action="edit-contract" data-id="${c.id}" title="${esc(this._t("edit"))}"><ha-icon icon="mdi:pencil"></ha-icon></button>
        <button class="icon admin-only" data-action="delete-contract" data-id="${c.id}" title="${esc(this._t("delete"))}"><ha-icon icon="mdi:delete"></ha-icon></button></div>
      <div class="chips">
        <span>${esc(this._t("energy_cost"))}: <strong>${this._num(c.unit_price || 0, 4)} ${esc(cur)}/${esc(billingUnit)}</strong></span>
        <span>${esc(this._t("base_cost"))}: <strong>${this._money(c.base_price || 0)} ${esc(this._t("per_month"))}</strong></span>
        <span>${esc(this._t("advance"))}: <strong>${this._money(c.advance_payment || 0)}</strong> · ${c.payments_per_year || 12}× · ${esc(this._t("payment_day"))} ${c.payment_day || 1}.</span>
        ${c.conversion_factor && c.conversion_factor !== 1 ? `<span>${esc(this._t("conversion_factor", { unit: meter.unit }))}: <strong>${this._num(c.conversion_factor, 4)}</strong></span>` : ""}
      </div>
      ${(c.price_changes || []).length || changes.length ? this._contractTimeline(c, meter, billingUnit) : ""}</div>`;
  }

  _contractTimeline(c, meter, billingUnit) {
    const cur = this._currencySymbol;
    const factor = meter.type === "gas" || (c.conversion_factor && c.conversion_factor !== 1);
    const priceText = (unit, base, conv) =>
      [
        unit !== null && unit !== undefined ? `${this._num(unit, 4)} ${esc(cur)}/${esc(billingUnit)}` : null,
        base !== null && base !== undefined ? `${this._money(base)} ${esc(this._t("per_month"))}` : null,
        factor && conv !== null && conv !== undefined ? `${esc(this._t("factor_short"))} ${this._num(conv, 4)}` : null,
      ]
        .filter(Boolean)
        .join(" · ");
    const events = [
      { date: c.start_date, order: 0, kind: "start", text: priceText(c.unit_price, c.base_price, c.conversion_factor) + ` · ${esc(this._t("advance"))} ${this._money(c.advance_payment || 0)}` },
      ...(c.price_changes || []).map((pc) => ({ date: pc.date, order: 1, kind: "price", text: priceText(pc.unit_price, pc.base_price, pc.conversion_factor) + (pc.note ? ` · ${esc(pc.note)}` : "") })),
      ...(c.advance_changes || []).map((ch) => ({ date: ch.date, order: 2, kind: "advance", text: this._money(ch.amount) })),
    ];
    if (c.end_date) events.push({ date: c.end_date, order: 3, kind: "end", text: "" });
    events.sort((a, b) => (a.date === b.date ? a.order - b.order : a.date < b.date ? -1 : 1));
    return `<details class="timeline"><summary>${esc(this._t("timeline"))} (${events.length})</summary><ol>
      ${events.map((e) => `<li class="tl-${e.kind}"><span class="tl-date">${this._date(e.date)}</span><span class="tl-kind">${esc(this._t(`timeline_${e.kind}`))}</span><span>${e.text}</span></li>`).join("")}
      </ol></details>`;
  }

  _contractForm(meter, c) {
    const cur = this._currencySymbol;
    const v = (key, def = "") => {
      const value = c?.[key] ?? def;
      return esc(typeof value === "number" ? this._plain(value) : value);
    };
    const showFactor = meter.type === "gas" || (c?.conversion_factor && c.conversion_factor !== 1);
    const priceUnit = showFactor && meter.unit === "m³" ? "kWh" : meter.unit;
    const dec = 'type="text" inputmode="decimal" pattern="[0-9]+([.,][0-9]+)*" autocomplete="off"';
    const changes = [...(c?.advance_changes || []), { date: "", amount: "" }, { date: "", amount: "" }];
    const prices = [...(c?.price_changes || []), {}, {}];
    const pcVal = (value) => (value === null || value === undefined || value === "" ? "" : esc(this._plain(value)));
    const perYear = Number(c?.payments_per_year || 12);
    return `<div class="card"><div class="card-title">${esc(c ? this._t("edit") : this._t("add_contract"))} – ${esc(meter.name)}</div>
      <form data-form="contract" class="form-grid">
        <label class="field"><span>${esc(this._t("provider"))}</span><input name="provider" value="${v("provider")}"></label>
        <label class="field"><span>${esc(this._t("tariff"))}</span><input name="tariff" value="${v("tariff")}"></label>
        <label class="field"><span>${esc(this._t("customer_number"))}</span><input name="customer_number" value="${v("customer_number")}"></label>
        <label class="field"><span>${esc(this._t("start_date"))}</span><input type="date" name="start_date" required value="${v("start_date", startOfMonth(this._data.today))}"></label>
        <label class="field"><span>${esc(this._t("end_date"))}</span><input type="date" name="end_date" value="${v("end_date")}"></label>
        <label class="field"><span>${esc(this._t("notice_period"))}</span><input name="notice_period" value="${v("notice_period")}" placeholder="1 Monat"></label>
        <label class="field"><span>${esc(this._t("unit_price", { currency: cur, unit: priceUnit }))}</span><input ${dec} name="unit_price" value="${v("unit_price")}" placeholder="0,32"></label>
        <label class="field"><span>${esc(this._t("base_price", { currency: cur }))}</span><input ${dec} name="base_price" value="${v("base_price")}" placeholder="12,50"></label>
        ${showFactor ? `<label class="field"><span>${esc(this._t("conversion_factor", { unit: meter.unit }))}</span><input ${dec} name="conversion_factor" value="${v("conversion_factor", meter.unit === "m³" ? 10.5 : 1)}"><small>${esc(this._t("conversion_hint"))}</small></label>` : ""}
        <label class="field"><span>${esc(this._t("advance_payment", { currency: cur }))}</span><input ${dec} name="advance_payment" value="${v("advance_payment")}" placeholder="85"></label>
        <label class="field"><span>${esc(this._t("payments_per_year"))}</span><select name="payments_per_year">
          <option value="12" ${perYear === 12 ? "selected" : ""}>${esc(this._t("payments_12"))}</option>
          <option value="11" ${perYear === 11 ? "selected" : ""}>${esc(this._t("payments_11"))}</option></select></label>
        <label class="field"><span>${esc(this._t("payment_day"))}</span><input type="number" name="payment_day" min="1" max="31" step="1" value="${v("payment_day", 1)}"></label>
        <label class="field"><span>${esc(this._t("first_payment"))}</span><input type="date" name="first_payment" value="${v("first_payment")}"></label>
        <fieldset class="wide changes"><legend>${esc(this._t("advance_changes"))}</legend>
          ${changes.map((ch, i) => `<div class="change-row"><span>${esc(this._t("advance_from"))}</span><input type="date" name="chg_date_${i}" value="${esc(ch.date)}">
            <input ${dec} name="chg_amount_${i}" value="${ch.amount === "" ? "" : esc(this._plain(ch.amount))}" placeholder="${esc(this._t("amount"))}"><span>${esc(cur)}</span></div>`).join("")}
          <small>${esc(this._t("advance_changes_hint"))}</small></fieldset>
        <fieldset class="wide changes"><legend>${esc(this._t("price_changes"))}</legend>
          ${prices.map((pc, i) => `<div class="change-row"><span>${esc(this._t("advance_from"))}</span><input type="date" name="pc_date_${i}" value="${esc(pc.date || "")}">
            <input ${dec} name="pc_unit_${i}" value="${pcVal(pc.unit_price)}" placeholder="${esc(this._t("energy_cost"))}" title="${esc(this._t("unit_price", { currency: cur, unit: priceUnit }))}">
            <input ${dec} name="pc_base_${i}" value="${pcVal(pc.base_price)}" placeholder="${esc(this._t("base_cost"))}" title="${esc(this._t("base_price", { currency: cur }))}">
            ${showFactor ? `<input ${dec} name="pc_factor_${i}" value="${pcVal(pc.conversion_factor)}" placeholder="${esc(this._t("factor_short"))}" title="${esc(this._t("conversion_factor", { unit: meter.unit }))}">` : ""}
            <input name="pc_note_${i}" class="note-input" value="${esc(pc.note || "")}" placeholder="${esc(this._t("note"))}">
            <button type="button" class="icon" data-action="clear-row" title="${esc(this._t("clear_row"))}"><ha-icon icon="mdi:close"></ha-icon></button></div>`).join("")}
          <small>${esc(this._t("price_changes_hint"))}</small></fieldset>
        <label class="field wide"><span>${esc(this._t("note"))}</span><input name="note" value="${v("note")}"></label>
        <div class="buttons wide"><button class="primary" type="submit">${esc(this._t("save"))}</button>
          <button type="button" class="flat" data-action="cancel-contract">${esc(this._t("cancel"))}</button></div>
      </form></div>`;
  }

  _billForm(meter, bill, data) {
    const cur = this._currencySymbol;
    const dec = 'type="text" inputmode="decimal" pattern="-?[0-9]+([.,][0-9]+)*" autocomplete="off"';
    const num = (key) => (bill?.[key] === null || bill?.[key] === undefined ? "" : esc(this._plain(bill[key])));
    // default period: the last finished billing period
    let start = bill?.start_date;
    let end = bill?.end_date;
    if (!bill && data && data.meter_id === meter.id) {
      const finished = data.periods.filter((p) => p.end < this._data.today);
      const period = finished[finished.length - 1] || data.periods[data.selected_index];
      start = period.start;
      end = period.end;
    }
    const resultType = bill?.balance === null || bill?.balance === undefined ? "auto" : bill.balance >= 0 ? "refund" : "payment";
    // suggest taking over the readings if there are none on these days
    const hasReading = (day) => this._data.readings.some((r) => r.meter_id === meter.id && r.date === day && !r.reset);
    const takeDefault = !bill && start && end && !hasReading(addDays(start, -1)) && !hasReading(end);
    return `<div class="card"><div class="card-title">${esc(bill ? this._t("edit") : this._t("add_bill"))} – ${esc(meter.name)}</div>
      <form data-form="bill" class="form-grid">
        <label class="field"><span>${esc(this._t("period_from"))}</span><input type="date" name="start_date" required value="${esc(start || "")}"></label>
        <label class="field"><span>${esc(this._t("period_to"))}</span><input type="date" name="end_date" required value="${esc(end || "")}"></label>
        <label class="field"><span>${esc(this._t("bill_consumption"))}</span><input ${dec} name="consumption" value="${num("consumption")}"></label>
        <label class="field"><span>${esc(this._t("unit"))}</span><select name="consumption_unit">
          <option value="meter" ${bill?.consumption_unit !== "billing" ? "selected" : ""}>${esc(this._t("unit_meter", { unit: meter.unit }))}</option>
          <option value="billing" ${bill?.consumption_unit === "billing" ? "selected" : ""}>${esc(this._t("unit_billing"))}</option></select></label>
        <label class="field"><span>${esc(this._t("bill_total_cost"))} (${esc(cur)})</span><input ${dec} name="total_cost" value="${num("total_cost")}"></label>
        <label class="field"><span>${esc(this._t("bill_advances"))} (${esc(cur)})</span><input ${dec} name="advances_paid" value="${num("advances_paid")}"></label>
        <label class="field"><span>${esc(this._t("bill_result"))}</span><select name="result_type">
          ${["auto", "refund", "payment"].map((t) => `<option value="${t}" ${t === resultType ? "selected" : ""}>${esc(this._t(`result_${t}`))}</option>`).join("")}</select></label>
        <label class="field"><span>${esc(this._t("amount"))} (${esc(cur)})</span><input ${dec} name="result_amount" value="${resultType === "auto" ? "" : esc(this._plain(Math.abs(bill.balance)))}"></label>
        <label class="field"><span>${esc(this._t("new_advance"))} (${esc(cur)})</span><input ${dec} name="new_advance" value="${num("new_advance")}"></label>
        <label class="field"><span>${esc(this._t("new_advance_from"))}</span><input type="date" name="new_advance_from" value="${esc(bill?.new_advance_from || "")}"><small>${esc(this._t("bill_hint"))}</small></label>
        <fieldset class="wide changes"><legend>${esc(this._t("bill_readings"))} (${esc(meter.unit)})</legend>
          <div class="change-row">
            <span>${esc(this._t("reading_bill_start"))}</span><input ${dec} name="reading_start" value="${num("reading_start")}">
            <span>${esc(this._t("reading_bill_end"))}</span><input ${dec} name="reading_end" value="${num("reading_end")}">
          </div>
          <label class="check"><input type="checkbox" name="reading_end_estimated" ${bill?.reading_end_estimated ? "checked" : ""}> <small>${esc(this._t("reading_end_estimated"))}</small></label>
          <label class="check"><input type="checkbox" name="take_readings" ${takeDefault ? "checked" : ""}> <small>${esc(this._t("take_readings"))}</small></label>
        </fieldset>
        <fieldset class="wide changes"><legend>${esc(this._t("bill_prices"))}</legend>
          <div class="change-row">
            <span>${esc(this._t("energy_cost"))}</span><input ${dec} name="unit_price" value="${num("unit_price")}" title="${esc(this._t("unit_price", { currency: cur, unit: meter.type === "gas" ? "kWh" : meter.unit }))}">
            <span>${esc(this._t("base_cost"))}</span><input ${dec} name="base_price" value="${num("base_price")}" title="${esc(this._t("base_price", { currency: cur }))}">
            ${meter.type === "gas" ? `<span>${esc(this._t("factor_short"))}</span><input ${dec} name="conversion_factor" value="${num("conversion_factor")}">` : ""}
          </div>
        </fieldset>
        <label class="field wide"><span>${esc(this._t("note"))}</span><input name="note" value="${esc(bill?.note || "")}"></label>
        <div class="buttons wide"><button class="primary" type="submit">${esc(this._t("save"))}</button>
          <button type="button" class="flat" data-action="cancel-bill">${esc(this._t("cancel"))}</button></div>
      </form></div>`;
  }

  /* cost development */

  _render_costs() {
    const s = this._state;
    s.costMeter = s.costMeter || "all";
    s.costMode = s.costMode || "calendar";
    if (s.costLine === undefined) s.costLine = true;
    let html = `<div class="card controls">
      <label class="field inline"><span>${esc(this._t("meter"))}</span><select data-bind="costMeter">
        <option value="all" ${s.costMeter === "all" ? "selected" : ""}>${esc(this._t("all_meters"))}</option>
        ${this._data.meters.map((m) => `<option value="${m.id}" ${m.id === s.costMeter ? "selected" : ""}>${esc(m.name)} (${esc(this._t(`type_${m.type}`))})</option>`).join("")}
      </select></label>
      <div class="segmented">${["calendar", "billing"].map((m) => `<button class="${m === s.costMode ? "active" : ""}" data-action="cost-mode" data-mode="${m}">${esc(this._t(`mode_${m}`))}</button>`).join("")}</div>
      ${s.costMeter !== "all" ? `<label class="check"><input type="checkbox" data-bind="costLine" ${s.costLine ? "checked" : ""}> ${esc(this._t("show_consumption"))}</label>` : ""}
    </div>`;
    const data = this._costs;
    if (!data || data.key !== `${s.costMeter}|${s.costMode}`) return html + `<div class="card empty">${esc(this._t("loading"))}</div>`;
    const single = s.costMeter !== "all";
    const meter = single ? data.meters[0] : null;
    const years = single ? meter.years : data.total;
    if (!years.length || years.every((y) => y.total_cost === null)) {
      html += `<div class="card empty">${esc(this._t("no_cost_data"))}</div>`;
    }
    const color = single ? TYPE_COLOR[meter.type] : "var(--primary-color)";
    html += `<div class="card"><div class="card-title">${esc(this._t("costs_title"))}${single ? ` – ${esc(meter.name)}` : ""}</div>
      <div class="chart-box" data-chart="costs"></div>
      <div class="legend">
        <span><i style="background:${color}"></i>${esc(this._t("energy_cost"))}</span>
        <span><i style="background:${color};opacity:.45"></i>${esc(this._t("base_cost"))}</span>
        ${years.some((y) => y.total_cost !== null && y.split_known === false) ? `<span><i class="unsplit-swatch" style="--c:${color}"></i>${esc(this._t("total_unsplit"))}</span>` : ""}
        <span><i class="forecast-swatch" style="--c:${color}"></i>${esc(this._t("forecast_year_note"))}</span>
        ${single && s.costLine ? `<span><i class="line-swatch"></i>${esc(this._t("consumption"))} (${esc(meter.unit)})</span>` : ""}
      </div>
      <div class="hint">${esc(this._t(single ? "costs_note" : "sum_note"))}</div></div>
      <div class="card">${this._costTable(years, meter)}
        <div class="buttons"><button type="button" class="flat" data-action="export-costs">${esc(this._t("export_table"))}</button></div></div>`;
    this._charts.costs = () => ({
      type: "cost",
      height: 300,
      color,
      unit: meter?.unit || "",
      showLine: single && s.costLine,
      years: years.map((y) => ({
        label: y.label,
        energy: y.energy_cost || 0,
        base: y.base_cost || 0,
        total: y.total_cost || 0,
        split: y.split_known !== false,
        gap: y.total_cost === null,
        gapText: this._t(`gap_${y.gap_reason || "no_data"}`),
        forecast: y.forecast,
        partial: y.status === "partial",
        consumption: single ? y.consumption : null,
      })),
      tooltip: (i) => this._costTooltip(years[i], meter),
    });
    return html;
  }

  _costSource(year) {
    if (!year.source) return "";
    return esc(this._t(`source_${year.source}`));
  }

  _costTooltip(year, meter) {
    if (!year) return "";
    let html = `<strong>${esc(year.label)}</strong> <span class="muted">${this._date(year.start)} – ${this._date(year.end)}</span>`;
    if (year.forecast) html += `<div><em>${esc(this._t("forecast_year_note"))}</em></div>`;
    if (year.total_cost === null) {
      return html + `<div>${esc(this._t(`gap_${year.gap_reason || "no_data"}`))}</div>`;
    }
    html += `<div>${esc(this._t("total_cost"))}: <strong>${this._money(year.total_cost)}</strong></div>`;
    html +=
      year.split_known === false
        ? `<div class="muted">${esc(this._t("split_unknown"))}</div>`
        : `<div>${esc(this._t("energy_cost"))}: ${this._money(year.energy_cost)}</div>
      <div>${esc(this._t("base_cost"))}: ${this._money(year.base_cost)}</div>`;
    if (year.estimated_days) html += `<div class="muted">${esc(this._t("days_estimated", { n: year.estimated_days }))}</div>`;
    if (meter && year.consumption !== null) html += `<div>${esc(this._t("consumption"))}: ${this._auto(year.consumption)} ${esc(meter.unit)}</div>`;
    if (year.change !== null && year.change !== undefined) html += `<div>${esc(this._t("change_prev"))}: ${year.change > 0 ? "+" : ""}${this._money(year.change)}</div>`;
    html += `<div class="muted">${esc(this._t("source"))}: ${this._costSource(year)}${year.status === "partial" && year.cost_coverage !== undefined ? ` · ${esc(this._t("covered", { p: this._num(year.cost_coverage * 100, 0) }))}` : ""}</div>`;
    if (year.incomplete?.length) html += `<div class="warn-text">${esc(this._t("incomplete_meters", { names: year.incomplete.join(", ") }))}</div>`;
    return html;
  }

  _costRows(years, meter) {
    // rows as plain values: used for the table and the CSV export
    return years.map((y) => {
      const gap = y.total_cost === null;
      return {
        year: y,
        label: y.label + (y.forecast ? ` (${this._t("forecast_year_note")})` : ""),
        source: gap ? this._t(`gap_${y.gap_reason || "no_data"}`) : this._t(`source_${y.source}`),
        consumption: meter && y.consumption !== null ? y.consumption : null,
        total: y.total_cost,
        base: y.base_cost,
        avg: y.avg_price ?? null,
        avgUnit: y.avg_price_unit || "",
        change: y.change ?? null,
        changePct: y.change_pct ?? null,
        advances: y.advances ?? null,
        result: y.result ?? null,
        coverage: y.cost_coverage,
        incomplete: y.incomplete || [],
      };
    });
  }

  _costTable(years, meter) {
    const rows = this._costRows(years, meter)
      .map((r) => {
        const y = r.year;
        const cls = [y.forecast ? "forecast-row" : "", y.total_cost === null ? "gap-row" : ""].join(" ");
        let partial =
          y.status === "partial"
            ? `<div class="warn-text small">${esc(r.incomplete.length ? this._t("incomplete_meters", { names: r.incomplete.join(", ") }) : this._t("covered", { p: this._num((r.coverage || 0) * 100, 0) }))}</div>`
            : "";
        if (y.estimated_days) partial += `<div class="muted small">${esc(this._t("days_estimated", { n: y.estimated_days }))}</div>`;
        const avg = r.avg === null ? "–" : r.avgUnit === "ct/kWh" ? `${this._num(r.avg, 2)} ct/kWh` : `${this._money(r.avg)}/${esc(r.avgUnit.replace("€/", ""))}`;
        return `<tr class="${cls}"><td>${esc(r.label)}</td>
          <td><span class="badge source-${y.source || "gap"}">${esc(r.source)}</span></td>
          ${meter ? `<td class="num">${r.consumption === null ? "–" : `${this._auto(r.consumption)} ${esc(meter.unit)}`}</td>` : ""}
          <td class="num"><strong>${r.total === null ? "–" : this._money(r.total)}</strong>${partial}</td>
          <td class="num">${r.base === null ? (r.total !== null && y.split_known === false ? `<span class="muted small" title="${esc(this._t("split_unknown"))}">?</span>` : "–") : this._money(r.base)}</td>
          ${meter ? `<td class="num">${avg}</td>` : ""}
          <td class="num">${r.change === null ? "–" : `${r.change > 0 ? "+" : ""}${this._money(r.change)}`}</td>
          <td class="num">${r.changePct === null ? "–" : this._delta(r.total, r.total - r.change)}</td>
          <td class="num">${r.advances === null ? "–" : this._money(r.advances)}</td>
          <td class="num">${r.result === null ? "–" : this._signedResult(r.result)}</td></tr>`;
      })
      .join("");
    return `<div class="table-wrap"><table><thead><tr>
      <th>${esc(this._t("year"))}</th><th>${esc(this._t("source"))}</th>
      ${meter ? `<th class="num">${esc(this._t("consumption"))}</th>` : ""}
      <th class="num">${esc(this._t("total_cost"))}</th><th class="num">${esc(this._t("base_cost"))}</th>
      ${meter ? `<th class="num">${esc(this._t("avg_price"))}</th>` : ""}
      <th class="num">${esc(this._t("change_prev"))}</th><th class="num">%</th>
      <th class="num">${esc(this._t("advances"))}</th><th class="num">${esc(this._t("bill_result"))}</th>
      </tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  _exportCostsCsv() {
    const data = this._costs;
    if (!data) return;
    const single = this._state.costMeter !== "all";
    const meter = single ? data.meters[0] : null;
    const years = single ? meter.years : data.total;
    const header = ["year", "start", "end", "forecast", "source", "status", "consumption", "unit", "total_cost", "energy_cost", "base_cost", "avg_price", "avg_price_unit", "change", "change_pct", "advances", "result", "cost_coverage_pct", "split_known", "estimated_days"];
    const rows = [header];
    for (const y of years) {
      rows.push([
        y.label,
        y.start,
        y.end,
        y.forecast ? 1 : 0,
        y.total_cost === null ? y.gap_reason || "" : y.source || "",
        y.status,
        meter ? this._csvNum(y.consumption) : "",
        meter ? meter.unit : "",
        this._csvNum(y.total_cost),
        this._csvNum(y.energy_cost),
        this._csvNum(y.base_cost),
        this._csvNum(y.avg_price ?? null),
        y.avg_price_unit || "",
        this._csvNum(y.change ?? null),
        this._csvNum(y.change_pct ?? null),
        this._csvNum(y.advances ?? null),
        this._csvNum(y.result ?? null),
        y.cost_coverage === undefined ? "" : this._csvNum(y.cost_coverage * 100),
        y.split_known === false ? 0 : 1,
        y.estimated_days || 0,
      ]);
    }
    this._download(`kosten_${meter ? meter.name : "alle"}_${data.mode}_${this._data.today}`, rows);
  }

  /* meters */

  _render_meters() {
    const s = this._state;
    let html = `<div class="card controls admin-only"><button class="primary" data-action="new-meter">${esc(this._t("add_meter"))}</button></div>`;
    if (s.showMeterForm) html += this._meterForm(this._meter(s.editMeter));
    for (const m of this._data.meters) {
      const count = this._data.readings.filter((r) => r.meter_id === m.id).length;
      html += `<div class="card"><div class="card-head">${this._icon(m.type)}
        <div class="grow"><div class="card-title">${esc(m.name)}</div>
        <div class="muted">${esc(this._t(`type_${m.type}`))} · ${esc(m.unit)}${m.number ? ` · ${esc(m.number)}` : ""} · ${count} ${esc(this._t("tab_readings"))} · ${esc(this._t(`profile_${m.profile || "auto"}`))}${m.annual_estimate ? ` · ${esc(this._t("reference"))}: ${this._auto(m.annual_estimate)} ${esc(m.unit)}` : ""}</div>
        <div class="muted">${esc(this._t("billing_date_short"))}: ${String(m.billing_day || 30).padStart(2, "0")}.${String(m.billing_month || 9).padStart(2, "0")}. · ${esc(this._t(`forecast_${m.forecast_method || "last_year"}`))}</div>
        ${this._data.statistics_available ? `<div class="muted">${esc(this._t("dashboard_hint", { name: `${m.name} ${this._t("stat_consumption")}` }))}</div>` : ""}</div>
        <button class="icon admin-only" data-action="edit-meter" data-id="${m.id}" title="${esc(this._t("edit"))}"><ha-icon icon="mdi:pencil"></ha-icon></button>
        <button class="icon admin-only" data-action="delete-meter" data-id="${m.id}" title="${esc(this._t("delete"))}"><ha-icon icon="mdi:delete"></ha-icon></button>
      </div></div>`;
    }
    return html;
  }

  _meterForm(m) {
    const type = this._formType || m?.type || "electricity";
    const unit = m && m.type === type ? m.unit : DEFAULT_UNIT[type];
    const def = DEFAULT_ANNUAL[`${type}|${unit}`] ?? 0;
    return `<div class="card"><div class="card-title">${esc(m ? this._t("edit") : this._t("add_meter"))}</div>
      <form data-form="meter" class="form-grid">
        <label class="field"><span>${esc(this._t("name"))}</span><input name="name" required maxlength="100" value="${esc(m?.name || "")}"></label>
        <label class="field"><span>${esc(this._t("meter_type"))}</span><select name="meter_type" data-bind="formType">${METER_TYPES.map((t) => `<option value="${t}" ${t === type ? "selected" : ""}>${esc(this._t(`type_${t}`))}</option>`).join("")}</select></label>
        <label class="field"><span>${esc(this._t("unit"))}</span><select name="unit">${UNITS.map((u) => `<option ${u === unit ? "selected" : ""}>${u}</option>`).join("")}</select></label>
        <label class="field"><span>${esc(this._t("meter_number"))}</span><input name="number" value="${esc(m?.number || "")}"><small>${esc(this._t("meter_number_hint"))}</small></label>
        <label class="field"><span>${esc(this._t("profile"))}</span><select name="profile">${PROFILES.map((p) => `<option value="${p}" ${p === (m?.profile || "auto") ? "selected" : ""}>${esc(this._t(`profile_${p}`))}</option>`).join("")}</select><small>${esc(this._t("profile_hint"))}</small></label>
        <label class="field"><span>${esc(this._t("annual_estimate", { unit }))}</span><input type="text" name="annual_estimate" inputmode="decimal" pattern="[0-9]+([.,][0-9]+)*" autocomplete="off" value="${esc(m?.annual_estimate ?? "")}" placeholder="${def}"><small>${esc(this._t("annual_hint", { value: `${def} ${unit}` }))}</small></label>
        <fieldset class="field billing-date"><legend>${esc(this._t("billing_date"))}</legend>
          <div class="change-row"><input type="number" name="billing_day" min="1" max="31" step="1" aria-label="${esc(this._t("day"))}" value="${esc(m?.billing_day ?? 30)}">
          <select name="billing_month" aria-label="${esc(this._t("month"))}">${Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}" ${i + 1 === Number(m?.billing_month ?? 9) ? "selected" : ""}>${esc(this._monthName(`2000-${String(i + 1).padStart(2, "0")}-01`, "long"))}</option>`).join("")}</select></div>
          <small>${esc(this._t("billing_date_hint"))}</small></fieldset>
        <label class="field"><span>${esc(this._t("forecast_method"))}</span><select name="forecast_method">
          ${["last_year", "average"].map((f) => `<option value="${f}" ${f === (m?.forecast_method || "last_year") ? "selected" : ""}>${esc(this._t(`forecast_${f}`))}</option>`).join("")}</select>
          <small>${esc(this._t("forecast_method_hint"))}</small></label>
        <div class="buttons wide"><button class="primary" type="submit">${esc(this._t("save"))}</button>
          <button type="button" class="flat" data-action="cancel-meter">${esc(this._t("cancel"))}</button></div>
      </form></div>`;
  }

  /* ----------------------------------------------------------- charts */

  _drawCharts() {
    const root = this.shadowRoot;
    if (!root) return;
    for (const box of root.querySelectorAll("[data-chart]")) {
      const factory = this._charts[box.dataset.chart];
      const spec = factory && factory();
      if (!spec) continue;
      const width = box.clientWidth || 300;
      box._spec = spec;
      if (spec.type === "cost") {
        box.innerHTML = renderCostChart(width, spec.height, spec, {
          formatMoney: (v, step) => this._axis(v, step, false, true),
          formatUnit: (v, step) => this._axis(v, step, false),
        });
      } else if (spec.type === "bar") {
        box.innerHTML = renderBarChart(width, spec.height, spec.groups, {
          id: box.dataset.chart,
          color: spec.color,
          formatAxis: (v, step) => this._axis(v, step, box.dataset.chart === "main"),
        });
      } else {
        box.innerHTML = renderLineChart(width, spec.height, spec.series, {
          formatAxis: (v, step) => this._axis(v, step, box.dataset.chart === "cumulative"),
          xTicks: spec.xTicks,
          zero: spec.zero,
          xMin: spec.xMin,
          xMax: spec.xMax,
        });
      }
    }
  }

  _onHover(ev) {
    const target = ev.composedPath()[0];
    if (!(target instanceof SVGElement) || !target.classList.contains("hover")) {
      this._hideTooltip();
      return;
    }
    const box = target.closest("[data-chart]");
    const spec = box?._spec;
    if (spec?.tooltip) {
      this._showTooltip(ev, spec.tooltip(Number(target.dataset.idx)));
      return;
    }
    const group = spec?.groups?.[Number(target.dataset.idx)];
    if (!group) return;
    const b = group.bucket;
    const u = esc(spec.unit);
    const fmt = (v) => `${this._num(v, 2)} ${u}`;
    let html = `<strong>${esc(this._bucketLabel(b, spec.gran, true))}</strong>`;
    if (b.measured) html += `<div>${esc(this._t("measured"))}: ${fmt(b.measured)}</div>`;
    if (b.estimated) html += `<div>${esc(this._t("estimated"))}: ${fmt(b.estimated)}</div>`;
    if (b.forecast) html += `<div>${esc(this._t("forecasted"))}: ${fmt(b.forecast)}</div>`;
    html += `<div><strong>${esc(this._t("total"))}: ${fmt(b.total)}</strong></div>`;
    if (b.cost !== null) html += `<div>${esc(this._t("cost"))}: ${this._money(b.cost)}</div>`;
    if (group.cmpBucket) {
      const c = group.cmpBucket;
      html += `<hr><div>${esc(this._bucketLabel(c, spec.gran, true))}: ${fmt(c.total)} ${this._delta(b.total, c.total)}</div>`;
      if (c.cost !== null) html += `<div>${esc(this._t("cost"))}: ${this._money(c.cost)}</div>`;
    }
    this._showTooltip(ev, html);
  }

  _showTooltip(ev, html) {
    const tip = this.shadowRoot.querySelector(".tooltip");
    tip.innerHTML = html;
    tip.style.display = "block";
    const rect = this.getBoundingClientRect();
    let left = ev.clientX - rect.left + 14;
    if (left + tip.offsetWidth > rect.width - 8) left = ev.clientX - rect.left - tip.offsetWidth - 14;
    tip.style.left = `${Math.max(4, left)}px`;
    tip.style.top = `${ev.clientY - rect.top + 14}px`;
  }

  _hideTooltip() {
    const tip = this.shadowRoot?.querySelector(".tooltip");
    if (tip) tip.style.display = "none";
  }

  /* ----------------------------------------------------------- events */

  async _onClick(ev) {
    const el = ev.composedPath().find((e) => e.dataset?.action);
    if (!el) return;
    const s = this._state;
    const action = el.dataset.action;
    switch (action) {
      case "photo":
        this.shadowRoot.querySelector(".photo-input").click();
        break;
      case "photo-close":
        this._closePhoto();
        break;
      case "import-files":
        this.shadowRoot.querySelector(".csv-input").click();
        break;
      case "import-close":
        this._import = null;
        this._renderImport();
        break;
      case "import-commit":
        await this._commitImport();
        break;
      case "tab":
        s.tab = el.dataset.tab;
        s.editReading = null;
        if (el.dataset.new) {
          s.showMeterForm = true;
          s.editMeter = null;
        }
        this._render();
        await this._loadTabData();
        break;
      case "quick-reading":
        s.meterId = el.dataset.meter;
        s.tab = "readings";
        s.editReading = null;
        this._render();
        this.shadowRoot.querySelector('input[name="value"]')?.focus();
        break;
      case "gran":
        s.gran = el.dataset.gran;
        if (["month", "billing"].includes(s.gran) && s.compare === "prev_period") s.compare = "prev_year";
        this._render();
        await this._loadStats();
        break;
      case "shift":
        this._shiftAnchor(Number(el.dataset.dir));
        this._render();
        await this._loadStats();
        break;
      case "mode":
        s.mode = el.dataset.mode;
        this._render();
        break;
      case "edit-reading":
        s.editReading = el.dataset.id;
        this._render();
        this.shadowRoot.querySelector('input[name="value"]')?.focus();
        break;
      case "cancel-edit":
        s.editReading = null;
        this._render();
        break;
      case "delete-reading": {
        const r = this._data.readings.find((x) => x.id === el.dataset.id);
        if (r && confirm(this._t("confirm_delete_reading", { date: this._date(r.date) }))) {
          await this._mutate("reading/delete", { reading_id: r.id });
        }
        break;
      }
      case "cost-mode":
        s.costMode = el.dataset.mode;
        this._render();
        await this._loadCosts();
        break;
      case "export-costs":
        this._exportCostsCsv();
        break;
      case "clear-row":
        for (const input of el.closest(".change-row").querySelectorAll("input")) input.value = "";
        break;
      case "view-photo":
        await this._viewPhoto(el.dataset.id);
        break;
      case "export-all":
        this._exportAllCsv();
        break;
      case "export-stats":
        this._exportStatsCsv();
        break;
      case "export":
        this._exportCsv();
        break;
      case "new-contract":
        s.showContractForm = true;
        s.editContract = null;
        this._render();
        break;
      case "edit-contract":
        s.showContractForm = true;
        s.editContract = el.dataset.id;
        this._render();
        this.shadowRoot.querySelector('form[data-form="contract"]')?.scrollIntoView({ behavior: "smooth" });
        break;
      case "cancel-contract":
        s.showContractForm = false;
        s.editContract = null;
        this._render();
        break;
      case "delete-contract":
        if (confirm(this._t("confirm_delete_contract"))) {
          await this._mutate("contract/delete", { contract_id: el.dataset.id });
        }
        break;
      case "period":
        s.billingIndex[s.meterId] = Number(el.dataset.idx);
        await this._loadBilling();
        break;
      case "new-bill":
        s.showBillForm = true;
        s.editBill = null;
        this._render();
        break;
      case "edit-bill":
        s.showBillForm = true;
        s.editBill = el.dataset.id;
        this._render();
        this.shadowRoot.querySelector('form[data-form="bill"]')?.scrollIntoView({ behavior: "smooth" });
        break;
      case "cancel-bill":
        s.showBillForm = false;
        s.editBill = null;
        this._render();
        break;
      case "delete-bill":
        if (confirm(this._t("confirm_delete_bill"))) {
          await this._mutate("bill/delete", { bill_id: el.dataset.id });
        }
        break;
      case "new-meter":
        s.showMeterForm = true;
        s.editMeter = null;
        this._formType = null;
        this._render();
        break;
      case "edit-meter":
        s.showMeterForm = true;
        s.editMeter = el.dataset.id;
        this._formType = null;
        this._render();
        break;
      case "cancel-meter":
        s.showMeterForm = false;
        s.editMeter = null;
        this._render();
        break;
      case "delete-meter": {
        const m = this._meter(el.dataset.id);
        if (m && confirm(this._t("confirm_delete_meter", { name: m.name }))) {
          await this._mutate("meter/delete", { meter_id: m.id });
        }
        break;
      }
    }
  }

  async _onChange(ev) {
    const el = ev.composedPath()[0];
    const bind = el?.dataset?.bind;
    if (!bind) return;
    const s = this._state;
    if (bind === "costMeter") {
      s.costMeter = el.value;
      this._render();
      await this._loadCosts();
      return;
    }
    if (bind === "costLine") {
      s.costLine = el.checked;
      this._render();
      return;
    }
    if (bind === "imp") {
      await this._onImportChange(el);
      return;
    }
    if (bind === "photoMeter") {
      const last = this.shadowRoot.querySelector(".photo-last");
      if (last) last.textContent = this._photoLastText(el.value);
      return;
    }
    if (bind === "meterId") {
      s.meterId = el.value;
      s.editReading = null;
      s.showContractForm = false;
      this._render();
      await this._loadTabData();
    } else if (bind === "compare") {
      s.compare = el.value;
      this._render();
      await this._loadStats();
    } else if (bind === "estimates") {
      s.estimates = el.checked;
      this._render();
    } else if (bind === "formType") {
      // keep entered values, only refresh unit and defaults
      const form = el.closest("form");
      const values = Object.fromEntries(new FormData(form));
      this._formType = el.value;
      this._render();
      const newForm = this.shadowRoot.querySelector('form[data-form="meter"]');
      for (const key of ["name", "number", "profile"]) if (newForm.elements[key]) newForm.elements[key].value = values[key];
    }
  }

  async _onSubmit(ev) {
    ev.preventDefault();
    const form = ev.composedPath()[0];
    const kind = form.dataset.form;
    const data = Object.fromEntries(new FormData(form));
    const s = this._state;
    if (kind === "reading") {
      const payload = {
        meter_id: s.meterId,
        date: data.date,
        value: parseNum(data.value),
        reset: form.elements.reset.checked,
        note: data.note || "",
      };
      if (s.editReading) payload.reading_id = s.editReading;
      if (!(await this._saveReading(payload))) return;
      s.editReading = null;
      this._toast(this._t("saved"));
      await this._reload();
    } else if (kind === "photo") {
      const payload = {
        meter_id: data.meter_id,
        date: data.date,
        value: parseNum(data.value),
        reset: form.elements.reset.checked,
        note: "",
      };
      // the backend moves the photo into the archive together with the reading
      if (this._photo?.result?.photo_id) payload.photo_id = this._photo.result.photo_id;
      if (!(await this._saveReading(payload))) return;
      this._photo.saved = true;
      const number = this._photo?.result?.meter_number;
      if (form.elements.save_number?.checked && number) {
        try {
          await this._ws("meter/save", { meter_id: data.meter_id, number });
        } catch (err) {
          this._toast(this._errorText(err), true);
        }
      }
      s.meterId = data.meter_id;
      this._closePhoto();
      this._toast(this._t("saved"));
      await this._reload();
    } else if (kind === "import") {
      if (!(data.csv || "").trim()) {
        this._toast(this._t("import_nothing"), true);
        return;
      }
      this._startImport([{ name: "", label: this._t("import_textfield"), text: data.csv, meterId: s.meterId }]);
    } else if (kind === "contract") {
      const num = (key) => parseNum(data[key]);
      const changes = [];
      const priceChanges = [];
      for (let i = 0; data[`pc_date_${i}`] !== undefined; i++) {
        if (!data[`pc_date_${i}`]) continue;
        const value = (key) => {
          const parsed = parseNum(data[`${key}_${i}`]);
          return parsed === undefined || Number.isNaN(parsed) ? null : parsed;
        };
        priceChanges.push({
          date: data[`pc_date_${i}`],
          unit_price: value("pc_unit"),
          base_price: value("pc_base"),
          conversion_factor: data[`pc_factor_${i}`] === undefined ? null : value("pc_factor"),
          note: data[`pc_note_${i}`] || "",
        });
      }
      for (let i = 0; data[`chg_date_${i}`] !== undefined; i++) {
        const amount = parseNum(data[`chg_amount_${i}`]);
        if (data[`chg_date_${i}`] && amount !== undefined && !Number.isNaN(amount)) changes.push({ date: data[`chg_date_${i}`], amount });
      }
      const payload = {
        meter_id: s.meterId,
        provider: data.provider || null,
        tariff: data.tariff || null,
        customer_number: data.customer_number || null,
        start_date: data.start_date,
        end_date: data.end_date || null,
        unit_price: num("unit_price") ?? 0,
        base_price: num("base_price") ?? 0,
        advance_payment: num("advance_payment") ?? 0,
        conversion_factor: num("conversion_factor") ?? 1,
        payments_per_year: Number(data.payments_per_year) || 12,
        payment_day: Number(data.payment_day) || 1,
        first_payment: data.first_payment || null,
        advance_changes: changes,
        price_changes: priceChanges,
        notice_period: data.notice_period || null,
        note: data.note || null,
      };
      if (s.editContract) payload.contract_id = s.editContract;
      if (await this._mutate("contract/save", payload)) {
        s.showContractForm = false;
        s.editContract = null;
        this._render();
      }
    } else if (kind === "bill") {
      const num = (key) => {
        const value = parseNum(String(data[key] ?? "").replace(/^-/, ""));
        if (value === undefined || Number.isNaN(value)) return null;
        return String(data[key]).trim().startsWith("-") ? -value : value;
      };
      const amount = num("result_amount");
      const payload = {
        meter_id: s.meterId,
        start_date: data.start_date,
        end_date: data.end_date,
        consumption: num("consumption"),
        consumption_unit: data.consumption_unit,
        total_cost: num("total_cost"),
        advances_paid: num("advances_paid"),
        balance: data.result_type === "auto" || amount === null ? null : data.result_type === "refund" ? Math.abs(amount) : -Math.abs(amount),
        new_advance: num("new_advance"),
        new_advance_from: data.new_advance_from || null,
        reading_start: num("reading_start"),
        reading_end: num("reading_end"),
        reading_end_estimated: Boolean(form.elements.reading_end_estimated?.checked),
        unit_price: num("unit_price"),
        base_price: num("base_price"),
        conversion_factor: data.conversion_factor === undefined ? undefined : num("conversion_factor"),
        take_readings: Boolean(form.elements.take_readings?.checked),
        note: data.note || null,
      };
      if (payload.conversion_factor === undefined) delete payload.conversion_factor;
      if (s.editBill) payload.bill_id = s.editBill;
      try {
        const result = await this._ws("bill/save", payload);
        const imported = result.imported_readings || [];
        const added = imported.filter((r) => r.status === "added").length;
        const problems = imported
          .filter((r) => r.status === "conflict")
          .map((r) => this._t("readings_conflict", { date: this._date(r.date), value: this._num(r.value, 2), message: this._errorText(r) }));
        if (problems.length) this._toast([added ? this._t("readings_imported", { added }) : "", ...problems].filter(Boolean).join("\n"), true);
        else this._toast(added ? this._t("readings_imported", { added }) : this._t("saved"));
        s.showBillForm = false;
        s.editBill = null;
        await this._reload();
      } catch (err) {
        this._toast(this._errorText(err), true);
      }
    } else if (kind === "meter") {
      const payload = {
        name: data.name,
        meter_type: data.meter_type,
        unit: data.unit,
        number: data.number || null,
        profile: data.profile,
        annual_estimate: parseNum(data.annual_estimate) ?? null,
        billing_day: Number(data.billing_day) || 30,
        billing_month: Number(data.billing_month) || 9,
        forecast_method: data.forecast_method || "last_year",
      };
      if (s.editMeter) payload.meter_id = s.editMeter;
      try {
        const meter = await this._ws("meter/save", payload);
        s.showMeterForm = false;
        s.editMeter = null;
        if (!s.meterId) s.meterId = meter.id;
        this._toast(this._t("saved"));
        await this._reload();
      } catch (err) {
        this._toast(this._errorText(err), true);
      }
    }
  }

  async _mutate(type, payload) {
    try {
      await this._ws(type, payload);
      this._toast(type.endsWith("delete") ? this._t("deleted") : this._t("saved"));
      await this._reload();
      return true;
    } catch (err) {
      this._toast(this._errorText(err), true);
      return false;
    }
  }

  _csvField(value) {
    const text = String(value ?? "");
    return /[;"\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }

  _csvNum(value) {
    return value === null || value === undefined ? "" : this._plain(value);
  }

  _download(name, rows) {
    // BOM + semicolons: opens correctly in Excel with a German locale
    const text = "\ufeff" + rows.map((row) => row.map((v) => this._csvField(v)).join(";")).join("\r\n");
    const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${name.replace(/[^\w.-]+/g, "_")}.csv`;
    this.shadowRoot.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  _sortedReadings(meterId) {
    return this._data.readings
      .filter((r) => r.meter_id === meterId)
      .sort((a, b) => (a.date + (a.reset ? 1 : 0) < b.date + (b.reset ? 1 : 0) ? -1 : 1));
  }

  /** Readings of the selected meter; the file can be imported again. */
  _exportCsv() {
    const meter = this._meter(this._state.meterId);
    const rows = [["date", "value", "reset", "note"]];
    for (const r of this._sortedReadings(meter.id)) rows.push([r.date, this._csvNum(r.value), r.reset ? 1 : 0, r.note || ""]);
    this._download(`${meter.name}_${this._data.today}`, rows);
  }

  /** Readings of all meters including the consumption since the previous reading. */
  _exportAllCsv() {
    const rows = [["meter", "meter_number", "type", "unit", "date", "value", "reset", "consumption", "days", "note", "source"]];
    for (const meter of this._data.meters) {
      let prev = null;
      for (const r of this._sortedReadings(meter.id)) {
        const usable = prev && !r.reset && r.date > prev.date;
        rows.push([
          meter.name,
          meter.number || "",
          this._t(`type_${meter.type}`),
          meter.unit,
          r.date,
          this._csvNum(r.value),
          r.reset ? 1 : 0,
          usable ? this._csvNum(r.value - prev.value) : "",
          usable ? daysBetween(prev.date, r.date) : "",
          r.note || "",
          r.source || "manual",
        ]);
        prev = r;
      }
    }
    this._download(`energy_tracker_${this._data.today}`, rows);
  }

  /** The evaluation that is currently shown (consumption, estimates, cost, comparison). */
  _exportStatsCsv() {
    const stats = this._stats;
    const meter = this._meter(this._state.meterId);
    if (!stats || !meter) return;
    const header = ["start", "end", "measured", "estimated", "forecast", "total", "unit", "cost"];
    if (stats.compare) header.push("compare_start", "compare_end", "compare_total", "compare_cost");
    const rows = [header];
    stats.buckets.forEach((b, i) => {
      const row = [b.start, b.end, this._csvNum(b.measured), this._csvNum(b.estimated), this._csvNum(b.forecast), this._csvNum(b.total), meter.unit, this._csvNum(b.cost)];
      if (stats.compare) {
        const c = stats.compare.buckets[i];
        row.push(c?.start ?? "", c?.end ?? "", this._csvNum(c?.total), this._csvNum(c?.cost));
      }
      rows.push(row);
    });
    this._download(`${meter.name}_${stats.granularity}_${stats.start}_${stats.end}`, rows);
  }
}

const STYLE = `
  :host { display:block; min-height:100vh; background:var(--primary-background-color); color:var(--primary-text-color);
    font-family:var(--paper-font-body1_-_font-family, Roboto, sans-serif); position:relative; }
  .header { position:sticky; top:0; z-index:3; background:var(--app-header-background-color, var(--primary-color));
    color:var(--app-header-text-color, var(--text-primary-color, #fff)); }
  .toolbar { display:flex; align-items:center; height:56px; padding:0 12px; gap:8px; }
  .main-title { font-size:20px; }
  .tabs { display:flex; overflow-x:auto; padding:0 8px; scrollbar-width:none; }
  .tab { background:none; border:none; color:inherit; opacity:.75; padding:12px 16px; font-size:14px; cursor:pointer;
    border-bottom:2px solid transparent; text-transform:uppercase; letter-spacing:.04em; white-space:nowrap; }
  .tab.active { opacity:1; border-bottom-color:currentColor; }
  .content { max-width:1200px; margin:0 auto; padding:16px; box-sizing:border-box; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(min(100%, 420px), 1fr)); gap:16px; }
  .card { background:var(--card-background-color, #fff); border-radius:var(--ha-card-border-radius, 12px);
    box-shadow:var(--ha-card-box-shadow, none); border:1px solid var(--divider-color); padding:16px; margin-bottom:16px; box-sizing:border-box; }
  .grid .card { margin-bottom:0; }
  .meter-card { border-top:4px solid var(--accent); }
  .card-head { display:flex; align-items:center; gap:12px; margin-bottom:12px; }
  .card-title { font-size:18px; font-weight:500; margin-bottom:4px; }
  .grow { flex:1; min-width:0; }
  .center { text-align:center; }
  .muted { color:var(--secondary-text-color); font-size:13px; }
  .big { font-size:24px; font-weight:500; }
  .empty { text-align:center; color:var(--secondary-text-color); padding:32px; }
  .hint { color:var(--secondary-text-color); font-size:12px; margin-top:8px; }
  .badge { font-size:12px; padding:2px 8px; border-radius:10px; white-space:nowrap; }
  .q-good { background:rgba(67,160,71,.15); color:var(--success-color, #43a047); }
  .q-low { background:rgba(251,140,0,.15); color:var(--warning-color, #fb8c00); }
  .q-none { background:rgba(158,158,158,.2); color:var(--secondary-text-color); }
  .last-reading { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:12px; margin-bottom:12px;
    border-radius:8px; background:var(--secondary-background-color); flex-wrap:wrap; }
  .figures { display:grid; grid-template-columns:repeat(auto-fill, minmax(130px, 1fr)); gap:12px; }
  .figures.wide { grid-template-columns:repeat(auto-fill, minmax(170px, 1fr)); margin-bottom:12px; }
  .figure .label { font-size:12px; color:var(--secondary-text-color); }
  .figure .value { font-size:18px; font-weight:500; }
  .figure .sub { font-size:12px; color:var(--secondary-text-color); }
  .delta { font-weight:500; }
  .delta.up { color:var(--error-color, #db4437); }
  .delta.down { color:var(--success-color, #43a047); }
  .spark-title { margin-top:12px; }
  .chart-box { width:100%; min-height:40px; position:relative; }
  .chart { display:block; overflow:visible; }
  .chart .grid { stroke:var(--divider-color); stroke-width:1; }
  .chart .baseline { stroke:var(--secondary-text-color); stroke-width:1; }
  .chart .axis { fill:var(--secondary-text-color); font-size:11px; }
  .chart .cmp-bar { fill:var(--secondary-text-color); opacity:.35; }
  .chart .hover { cursor:crosshair; }
  .chart .hover:hover { fill:var(--primary-text-color); fill-opacity:.05; }
  .legend { display:flex; flex-wrap:wrap; gap:16px; margin-top:8px; font-size:12px; color:var(--secondary-text-color); }
  .legend i { display:inline-block; width:12px; height:12px; border-radius:2px; margin-right:6px; vertical-align:-2px; }
  .legend i.cmp { background:var(--secondary-text-color); opacity:.35; }
  .hatched { background:repeating-linear-gradient(45deg, var(--c) 0 3px, transparent 3px 6px); }
  .tooltip { position:absolute; display:none; z-index:10; pointer-events:none; background:var(--card-background-color, #fff);
    border:1px solid var(--divider-color); border-radius:8px; padding:8px 10px; font-size:12px; box-shadow:0 2px 8px rgba(0,0,0,.2); max-width:280px; }
  .tooltip hr { border:none; border-top:1px solid var(--divider-color); margin:6px 0; }
  .billing { margin-top:16px; padding-top:12px; border-top:1px solid var(--divider-color); }
  .billing-head { display:flex; align-items:center; gap:8px; flex-wrap:wrap; justify-content:space-between; margin-bottom:8px; }
  .progress { height:6px; border-radius:3px; background:var(--secondary-background-color); overflow:hidden; margin-bottom:12px; }
  .progress div { height:100%; background:var(--accent, var(--primary-color)); }
  .billing-row { display:flex; gap:16px; flex-wrap:wrap; align-items:stretch; }
  .result { flex:0 0 auto; min-width:180px; border-radius:10px; padding:12px 16px; background:var(--secondary-background-color);
    display:flex; flex-direction:column; justify-content:center; }
  .result.good { background:rgba(67,160,71,.15); color:var(--success-color, #2e7d32); }
  .result.bad { background:rgba(219,68,55,.13); color:var(--error-color, #c62828); }
  .result .label { font-size:13px; }
  .result .amount { font-size:28px; font-weight:600; }
  .billing-facts { flex:1; min-width:220px; display:flex; flex-direction:column; gap:4px; font-size:14px; }
  .billing-facts div { display:flex; justify-content:space-between; gap:12px; border-bottom:1px dashed var(--divider-color); padding:2px 0; }
  .billing-facts span { color:var(--secondary-text-color); }
  .stack-bar { display:flex; height:14px; border-radius:7px; overflow:hidden; margin-top:16px; background:var(--secondary-background-color); }
  .chips { display:flex; flex-wrap:wrap; gap:8px; font-size:13px; }
  .chips span { background:var(--secondary-background-color); border-radius:12px; padding:4px 10px; }
  .controls { display:flex; flex-wrap:wrap; gap:12px; align-items:center; }
  .segmented { display:inline-flex; border:1px solid var(--divider-color); border-radius:8px; overflow:hidden; }
  .segmented button { background:none; border:none; padding:8px 12px; cursor:pointer; color:var(--primary-text-color); font-size:14px; }
  .segmented button + button { border-left:1px solid var(--divider-color); }
  .segmented button.active { background:var(--primary-color); color:var(--text-primary-color, #fff); }
  .nav { display:flex; align-items:center; gap:4px; }
  .range-label { min-width:130px; text-align:center; font-weight:500; }
  button { font-family:inherit; }
  button.primary { background:var(--primary-color); color:var(--text-primary-color, #fff); border:none; border-radius:8px;
    padding:9px 16px; font-size:14px; cursor:pointer; font-weight:500; }
  button.flat { background:none; border:1px solid var(--divider-color); color:var(--primary-text-color); border-radius:8px; padding:8px 14px; cursor:pointer; font-size:14px; }
  button.icon { background:none; border:none; color:var(--secondary-text-color); cursor:pointer; font-size:22px; line-height:1;
    padding:6px; border-radius:50%; min-width:36px; min-height:36px; }
  button.icon:hover:not([disabled]) { background:var(--secondary-background-color); }
  button[disabled] { opacity:.3; cursor:default; }
  .field { display:flex; flex-direction:column; gap:4px; font-size:13px; color:var(--secondary-text-color); }
  .field.inline { flex-direction:row; align-items:center; gap:8px; }
  .field small { font-size:11px; }
  input, select, textarea { font:inherit; font-size:15px; color:var(--primary-text-color); background:var(--input-fill-color, var(--secondary-background-color));
    border:1px solid var(--divider-color); border-radius:8px; padding:9px 10px; box-sizing:border-box; min-width:0; }
  textarea { width:100%; font-family:monospace; }
  input:focus, select:focus, textarea:focus { outline:2px solid var(--primary-color); outline-offset:-1px; }
  .check { display:flex; align-items:center; gap:6px; font-size:14px; cursor:pointer; }
  .check input { width:18px; height:18px; }
  .form-row { display:flex; flex-wrap:wrap; gap:12px; align-items:flex-end; }
  .form-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(min(100%, 240px), 1fr)); gap:12px; align-items:start; }
  .form-grid .wide { grid-column:1 / -1; }
  .buttons { display:flex; gap:8px; align-items:center; margin-top:8px; }
  .table-wrap { overflow-x:auto; }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th, td { padding:8px; text-align:left; border-bottom:1px solid var(--divider-color); white-space:nowrap; }
  th { font-weight:500; color:var(--secondary-text-color); font-size:12px; }
  td.num, th.num { text-align:right; }
  td.actions { text-align:right; width:1%; }
  td.actions button.icon { font-size:inherit; --mdc-icon-size:20px; }
  tr.editing td { background:var(--secondary-background-color); }
  details summary { cursor:pointer; font-weight:500; }
  .readonly .admin-only { display:none !important; }
  .legend i.unsplit-swatch { background:repeating-linear-gradient(90deg, var(--c) 0 6px, transparent 6px 7px); opacity:.75; }
  .chart .gap-bar { fill:none; stroke:var(--secondary-text-color); stroke-dasharray:4 4; opacity:.6; }
  .chart .gap-text { font-size:10px; }
  .chart .warn-fill { fill:var(--warning-color, #e65100); font-weight:bold; }
  .chart .cons-line { stroke:var(--primary-text-color); stroke-width:2; opacity:.75; }
  .chart .line-dot { fill:var(--primary-text-color); opacity:.75; }
  .legend i.forecast-swatch { background:none; border:1.5px dashed var(--c); box-sizing:border-box; }
  .legend i.line-swatch { height:2px; background:var(--primary-text-color); vertical-align:3px; }
  tr.forecast-row td { font-style:italic; opacity:.8; }
  tr.gap-row td { color:var(--secondary-text-color); }
  .small { font-size:11px; }
  .badge.source-calculated { background:rgba(3,169,244,.12); }
  .badge.source-bill { background:rgba(67,160,71,.15); }
  .badge.source-mixed { background:rgba(251,140,0,.15); }
  .badge.source-gap { background:rgba(158,158,158,.2); }
  .change-row .note-input { flex:1; min-width:120px; }
  .timeline ol { list-style:none; margin:8px 0 0; padding:0 0 0 12px; border-left:2px solid var(--divider-color); }
  .timeline li { display:flex; gap:10px; flex-wrap:wrap; padding:4px 0 4px 10px; position:relative; font-size:13px; }
  .timeline li::before { content:""; position:absolute; left:-7px; top:9px; width:10px; height:10px; border-radius:50%; background:var(--accent, var(--primary-color)); }
  .timeline li.tl-advance::before { background:var(--secondary-text-color); }
  .timeline li.tl-end::before { background:var(--error-color, #c62828); }
  .tl-date { min-width:84px; font-weight:500; }
  .tl-kind { min-width:110px; color:var(--secondary-text-color); }
  .section-title { margin:24px 4px 12px; font-size:16px; font-weight:500; color:var(--secondary-text-color); text-transform:uppercase; letter-spacing:.04em; }
  .warn-text { color:var(--warning-color, #e65100); }
  .billing-facts em { font-style:normal; font-size:12px; }
  .last-bill { margin-top:12px; padding-top:10px; border-top:1px dashed var(--divider-color); font-size:14px; }
  .comparison { margin-top:16px; padding-top:12px; border-top:1px solid var(--divider-color); }
  .result-badge.good { background:rgba(67,160,71,.15); color:var(--success-color, #2e7d32); }
  .result-badge.bad { background:rgba(219,68,55,.13); color:var(--error-color, #c62828); }
  fieldset { border:1px solid var(--divider-color); border-radius:8px; padding:8px 12px 12px; margin:0; min-width:0; }
  fieldset legend { font-size:13px; color:var(--secondary-text-color); padding:0 4px; }
  .change-row { display:flex; gap:8px; align-items:center; margin-bottom:6px; flex-wrap:wrap; font-size:13px; color:var(--secondary-text-color); }
  .change-row input[type="text"] { width:110px; }
  .change-row input[type="number"] { width:72px; }
  .card details { margin-top:12px; font-size:14px; }
  .wide-modal { width:min(100%, 760px); }
  .import-item { border-top:1px solid var(--divider-color); padding:14px 0; }
  .import-item details { margin-top:8px; font-size:13px; }
  .import-item details ul { margin:6px 0 0; padding-left:20px; color:var(--secondary-text-color); max-height:180px; overflow:auto; }
  .import-facts { margin-top:12px; }
  .import-facts .bad strong { color:var(--error-color, #c62828); }
  .import-item .notice { margin:12px 0 0; }
  .import-item td.wrap { white-space:normal; }
  .import-item td select { max-width:100%; }
  .photo-preview.large { max-height:70vh; }
  .actions-row { display:flex; justify-content:flex-end; margin-bottom:12px; }
  button.with-icon { display:inline-flex; align-items:center; gap:8px; --mdc-icon-size:20px; }
  .modal-backdrop { position:fixed; inset:0; z-index:15; background:rgba(0,0,0,.55); display:flex; align-items:center;
    justify-content:center; padding:12px; box-sizing:border-box; }
  .modal { width:min(100%, 560px); max-height:calc(100vh - 24px); overflow-y:auto; margin:0; }
  .photo-preview { display:block; width:100%; max-height:38vh; object-fit:contain; border-radius:8px;
    background:var(--secondary-background-color); margin-bottom:12px; }
  .photo-status { display:flex; align-items:center; gap:12px; padding:12px 0; }
  .spinner { width:22px; height:22px; border-radius:50%; border:3px solid var(--divider-color);
    border-top-color:var(--primary-color); animation:spin 1s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }
  .notice { border-radius:8px; padding:10px 12px; margin-bottom:12px; font-size:14px; white-space:pre-line;
    background:var(--secondary-background-color); }
  .notice.good { background:rgba(67,160,71,.15); }
  .notice.warn { background:rgba(251,140,0,.15); }
  .notice.bad { background:rgba(219,68,55,.13); color:var(--error-color, #c62828); }
  .buttons.end { justify-content:flex-end; flex-wrap:wrap; }
  .toast { position:fixed; left:50%; bottom:24px; transform:translateX(-50%) translateY(100px); opacity:0; transition:all .25s;
    background:#323232; color:#fff; padding:12px 20px; border-radius:8px; z-index:20; max-width:90vw; white-space:pre-line; }
  .toast.show { transform:translateX(-50%); opacity:1; }
  .toast.error { background:var(--error-color, #c62828); }
  @media (max-width: 600px) {
    .content { padding:8px; }
    .card { padding:12px; }
    .result .amount { font-size:22px; }
  }
`;

customElements.define("energy-tracker-panel", EnergyTrackerPanel);
