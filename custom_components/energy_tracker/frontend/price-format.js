/*
 * Pure helpers for prices in the Energy Tracker panel (no DOM, no Home Assistant).
 *
 * Prices are always stored in currency per billing unit (e.g. €/kWh).  For
 * billing units in kWh the panel shows and accepts cent (ct/kWh); the
 * conversion happens only here.  Tested with `node --test tests/js`.
 */

/** Parse "25.600,5", "25600,5", "25600.5" or "39,8" into a number.
 * Empty -> undefined, invalid -> NaN. */
export const parseDecimal = (value) => {
  let text = String(value ?? "").trim().replace(/\s/g, "");
  if (text === "") return undefined;
  if (text.includes(",")) text = text.replace(/\./g, "").replace(",", ".");
  else if ((text.match(/\./g) || []).length > 1) text = text.replace(/\./g, "");
  if (!/^[+-]?(\d+\.?\d*|\.\d+)$/.test(text)) return NaN;
  const num = Number(text);
  return Number.isFinite(num) ? num : NaN;
};

/** Round to a number of decimal places without float noise (0.1 + 0.2). */
export const roundTo = (value, digits) => {
  const factor = 10 ** digits;
  return Math.round((value + Number.EPSILON) * factor) / factor;
};

/** Up to 4 decimal places in cent, i.e. 6 in euro. */
export const CENT_DECIMALS = 4;
export const EURO_DECIMALS = 6;

/**
 * Billing unit of a meter: kWh for electricity/heat in kWh and for gas in m³
 * (converted with the calorific value), otherwise the meter unit.
 */
export const billingUnit = (meter, conversionFactor) => {
  const unit = meter?.unit || "";
  if (unit === "kWh") return "kWh";
  if (unit === "m³" && (meter?.type === "gas" || (conversionFactor && conversionFactor !== 1))) return "kWh";
  return unit;
};

/** True if unit prices are shown and entered in cent (ct/kWh). */
export const usesCent = (meter, conversionFactor) => billingUnit(meter, conversionFactor) === "kWh";

/** Label of the unit price unit, e.g. "ct/kWh" or "€/m³". */
export const priceUnitLabel = (meter, conversionFactor, currencySymbol = "€") =>
  usesCent(meter, conversionFactor) ? "ct/kWh" : `${currencySymbol}/${billingUnit(meter, conversionFactor)}`;

/** Stored price (€/unit) -> value shown in the input (ct or €). null/undefined/"" -> null. */
export const toDisplayPrice = (euro, cent) => {
  if (euro === null || euro === undefined || euro === "") return null;
  const value = Number(euro);
  if (!Number.isFinite(value)) return null;
  return cent ? roundTo(value * 100, CENT_DECIMALS) : roundTo(value, EURO_DECIMALS);
};

/**
 * Input text (ct or €) -> stored price in €/unit.
 * Empty -> null, invalid -> NaN.  Cent values are divided by 100.
 */
export const parsePriceInput = (text, cent) => {
  const value = parseDecimal(text);
  if (value === undefined) return null;
  if (Number.isNaN(value)) return NaN;
  return cent ? roundTo(value / 100, CENT_DECIMALS + 2) : roundTo(value, EURO_DECIMALS);
};

/** Format a number for an input field: locale decimal separator, no grouping. */
export const formatInputNumber = (value, lang = "de", maxDigits = CENT_DECIMALS) => {
  if (value === null || value === undefined || Number.isNaN(value)) return "";
  return new Intl.NumberFormat(lang, { useGrouping: false, maximumFractionDigits: maxDigits }).format(value);
};

/** Stored price -> text for an input field (ct or €). */
export const priceInputValue = (euro, cent, lang = "de") =>
  formatInputNumber(toDisplayPrice(euro, cent), lang, cent ? CENT_DECIMALS : EURO_DECIMALS);

/** Stored price -> display text, e.g. "39,80 ct/kWh" or "4,25 €/m³". */
export const formatPrice = (euro, cent, unitLabel, lang = "de") => {
  const shown = toDisplayPrice(euro, cent);
  if (shown === null) return "–";
  const text = new Intl.NumberFormat(lang, {
    minimumFractionDigits: 2,
    maximumFractionDigits: cent ? CENT_DECIMALS : 4,
  }).format(shown);
  return `${text} ${unitLabel}`;
};

/** Plausible range of a unit price: cent 1-100 ct/kWh, otherwise 0.10-20 €/unit. */
export const PRICE_RANGE = { cent: [1, 100], euro: [0.1, 20] };

/**
 * Check a stored price (€/unit).  Returns null if plausible or empty,
 * otherwise the value as shown (ct or €) for a confirmation question.
 */
export const implausiblePrice = (euro, cent) => {
  if (euro === null || euro === undefined || Number.isNaN(euro)) return null;
  const shown = toDisplayPrice(euro, cent);
  const [min, max] = cent ? PRICE_RANGE.cent : PRICE_RANGE.euro;
  return shown < min || shown > max ? shown : null;
};

/** Sort changes newest first (by "date"); the stored order stays ascending. */
export const newestFirst = (items) => [...(items || [])].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));

/**
 * Status of dated changes relative to today: the latest one that has started
 * is "current", later ones are "planned".  Returns a Map date -> status.
 * ``startDate`` (contract start) is current if no change has started yet.
 */
export const changeStatus = (dates, today, startDate = null, endDate = null) => {
  const result = new Map();
  const active = !endDate || today <= endDate;
  const started = [...dates].filter((d) => d && d <= today).sort();
  const current = started.length ? started[started.length - 1] : startDate && startDate <= today ? startDate : null;
  for (const d of dates) if (d && d > today) result.set(d, "planned");
  if (startDate && startDate > today) result.set(startDate, "planned");
  if (current && active) result.set(current, "current");
  return result;
};
