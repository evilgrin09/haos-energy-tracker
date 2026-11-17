// Tests for the price helpers of the panel: node --test tests/js
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  billingUnit,
  changeStatus,
  formatPrice,
  implausiblePrice,
  newestFirst,
  parseDecimal,
  parsePriceInput,
  priceInputValue,
  priceUnitLabel,
  toDisplayPrice,
  usesCent,
} from "../../custom_components/energy_tracker/frontend/price-format.js";

test("parseDecimal accepts comma and point", () => {
  assert.equal(parseDecimal("39,8"), 39.8);
  assert.equal(parseDecimal("39.8"), 39.8);
  assert.equal(parseDecimal(" 29,3277 "), 29.3277);
  assert.equal(parseDecimal("25.600,5"), 25600.5);
  assert.equal(parseDecimal("1.234.567"), 1234567);
  assert.equal(parseDecimal(""), undefined);
  assert.equal(parseDecimal(null), undefined);
  assert.ok(Number.isNaN(parseDecimal("abc")));
  assert.ok(Number.isNaN(parseDecimal("1,2,3")));
});

test("cent input is stored in euro", () => {
  assert.equal(parsePriceInput("39,8", true), 0.398);
  assert.equal(parsePriceInput("29,3277", true), 0.293277);
  assert.equal(parsePriceInput("0,0039", true), 0.000039);
  assert.equal(parsePriceInput("4,25", false), 4.25);
  assert.equal(parsePriceInput("", true), null);
  assert.equal(parsePriceInput("  ", false), null);
  assert.ok(Number.isNaN(parsePriceInput("x", true)));
});

test("stored euro is shown in cent without float noise", () => {
  assert.equal(toDisplayPrice(0.398, true), 39.8);
  assert.equal(toDisplayPrice(0.293277, true), 29.3277);
  assert.equal(toDisplayPrice(0.1 + 0.2, true), 30);
  // more than 4 decimal places in cent are rounded
  assert.equal(toDisplayPrice(0.29327749, true), 29.3277);
  assert.equal(toDisplayPrice(0.29327751, true), 29.3278);
  assert.equal(toDisplayPrice(4.25, false), 4.25);
  assert.equal(toDisplayPrice(null, true), null);
  assert.equal(toDisplayPrice("", true), null);
  assert.equal(toDisplayPrice(undefined, false), null);
});

test("round trip input -> stored -> input", () => {
  for (const text of ["39,8", "29,3277", "0,5", "100", "12,34"]) {
    assert.equal(priceInputValue(parsePriceInput(text, true), true, "de"), text);
  }
  assert.equal(priceInputValue(0.398, true, "en"), "39.8");
  assert.equal(priceInputValue(4.25, false, "de"), "4,25");
  assert.equal(priceInputValue(null, true, "de"), "");
});

test("formatted prices", () => {
  assert.equal(formatPrice(0.398, true, "ct/kWh", "de"), "39,80 ct/kWh");
  assert.equal(formatPrice(0.293277, true, "ct/kWh", "de"), "29,3277 ct/kWh");
  assert.equal(formatPrice(4.25, false, "€/m³", "de"), "4,25 €/m³");
  assert.equal(formatPrice(null, true, "ct/kWh", "de"), "–");
});

test("billing unit and cent decision", () => {
  assert.equal(billingUnit({ type: "electricity", unit: "kWh" }), "kWh");
  assert.equal(billingUnit({ type: "gas", unit: "m³" }, 10.4), "kWh");
  assert.equal(billingUnit({ type: "gas", unit: "m³" }), "kWh");
  assert.equal(billingUnit({ type: "water", unit: "m³" }, 1), "m³");
  assert.equal(billingUnit({ type: "oil", unit: "L" }), "L");
  assert.equal(usesCent({ type: "heat", unit: "kWh" }), true);
  assert.equal(usesCent({ type: "water", unit: "m³" }), false);
  assert.equal(priceUnitLabel({ type: "water", unit: "m³" }, 1, "€"), "€/m³");
  assert.equal(priceUnitLabel({ type: "gas", unit: "m³" }, 10.4, "€"), "ct/kWh");
});

test("implausible prices", () => {
  assert.equal(implausiblePrice(0.398, true), null);
  assert.equal(implausiblePrice(0.000039, true), 0.0039); // typed 0,0039 instead of 39,8
  assert.equal(implausiblePrice(1.5, true), 150);
  assert.equal(implausiblePrice(0.01, true), null); // exactly 1 ct
  assert.equal(implausiblePrice(4.25, false), null);
  assert.equal(implausiblePrice(0.05, false), 0.05);
  assert.equal(implausiblePrice(25, false), 25);
  assert.equal(implausiblePrice(null, true), null);
});

test("newest first and status of changes", () => {
  const changes = [{ date: "2024-01-01" }, { date: "2026-03-01" }, { date: "2025-01-01" }];
  assert.deepEqual(newestFirst(changes).map((c) => c.date), ["2026-03-01", "2025-01-01", "2024-01-01"]);
  assert.deepEqual(changes.map((c) => c.date), ["2024-01-01", "2026-03-01", "2025-01-01"]); // unchanged
  const status = changeStatus(["2024-01-01", "2025-01-01", "2026-03-01"], "2025-06-01", "2023-01-01");
  assert.equal(status.get("2025-01-01"), "current");
  assert.equal(status.get("2026-03-01"), "planned");
  assert.equal(status.get("2024-01-01"), undefined);
  assert.equal(status.get("2023-01-01"), undefined);
  // before the first change the start prices are current
  assert.equal(changeStatus(["2026-01-01"], "2025-06-01", "2023-01-01").get("2023-01-01"), "current");
  // an ended contract has nothing current
  assert.equal(changeStatus(["2024-01-01"], "2025-06-01", "2023-01-01", "2024-12-31").get("2024-01-01"), undefined);
  assert.equal(changeStatus([], "2025-06-01", "2026-01-01").get("2026-01-01"), "planned");
});
