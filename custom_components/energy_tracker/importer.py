"""CSV import of meter readings.

Free of Home Assistant imports so that it can be unit tested in isolation.

Understands the export of the iOS app "Energy Tracker" (one file per meter,
``Datum;Zählerstand;Beschreibung``, date with time, newest line first) as well
as the simple format of this integration (``date;value[;reset][;note]``, with
or without header line).  Nothing is dropped silently: every line that is not
imported is reported with a reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
import re
from typing import Any

DELIMITERS = (";", "\t", ",")

REASON_TOO_FEW_COLUMNS = "too_few_columns"
REASON_INVALID_DATE = "invalid_date"
REASON_MISSING_VALUE = "missing_value"
REASON_INVALID_VALUE = "invalid_value"
REASON_NEGATIVE_VALUE = "negative_value"

FLAG_LOWER = "lower_than_previous"
FLAG_HIGHER = "higher_than_next"

DECISION_RESET = "reset"
DECISION_KEEP = "keep"
DECISION_SKIP = "skip"
DECISIONS = (DECISION_RESET, DECISION_KEEP, DECISION_SKIP)

_HEADER_COLUMNS = {
    "date": ("datum", "date", "zeit", "time", "tag", "day"),
    "value": ("zählerstand", "zaehlerstand", "stand", "wert", "value", "reading"),
    "reset": ("reset", "wechsel", "zählerwechsel", "zaehlerwechsel", "replaced"),
    "note": ("beschreibung", "notiz", "note", "description", "kommentar", "comment", "bemerkung"),
}
_TRUE_FLAGS = {"1", "x", "true", "ja", "yes", "wechsel", "reset", "replaced"}
_FALSE_FLAGS = {"", "0", "false", "nein", "no"}

_ISO_RE = re.compile(
    r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ]+(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?)?"
    r"\s*(?:Z|[+-]\d{2}:?\d{2})?$"
)
_GERMAN_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})(?:,?\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?(?:\s*Uhr)?$")

# Keywords in file names -> meter type.  Order matters ("heizöl" before "öl").
_TYPE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("oil", ("heizöl", "heizoel", "heizo", "heiz_l", "heating oil", "oil")),
    ("heat", ("wärme", "waerme", "warme", "w_rme", "fernw", "heat")),
    ("electricity", ("strom", "electric", "power")),
    ("water", ("wasser", "water")),
    ("gas", ("gas",)),
)
DEFAULT_UNITS = {
    "electricity": "kWh",
    "gas": "m³",
    "water": "m³",
    "heat": "kWh",
    "oil": "L",
    "other": "kWh",
}


@dataclass(slots=True)
class ParsedRow:
    """A reading read from a CSV line."""

    day: date
    time: time
    value: float
    reset: bool = False
    note: str = ""
    line: int = 0


@dataclass
class ParseResult:
    """Result of parsing a CSV text."""

    rows: list[ParsedRow] = field(default_factory=list)  # one per day, ascending
    rejected: list[dict[str, Any]] = field(default_factory=list)
    merged: list[dict[str, Any]] = field(default_factory=list)  # same-day duplicates
    data_lines: int = 0
    delimiter: str = ";"
    header: bool = False


def parse_number(text: str) -> float | None:
    """Parse "39379,2", "10.915,83", "10,915.83" or "748"."""
    cleaned = re.sub(r"[\s' ]", "", text)
    if not re.fullmatch(r"[+-]?[0-9.,]+", cleaned) or not re.search(r"\d", cleaned):
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif cleaned.count(",") == 1:
        cleaned = cleaned.replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", "")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_datetime(text: str) -> tuple[date, time] | None:
    """Parse a date with optional time (ISO or German notation)."""
    text = text.strip()
    if match := _ISO_RE.match(text):
        year, month, day, hour, minute, second = match.groups()
    elif match := _GERMAN_RE.match(text):
        day, month, year, hour, minute, second = match.groups()
    else:
        return None
    try:
        return (
            date(int(year), int(month), int(day)),
            time(int(hour or 0), int(minute or 0), int(second or 0)),
        )
    except ValueError:
        return None


def detect_delimiter(lines: list[str]) -> str:
    """Detect the column separator from the first lines."""
    sample = lines[:20]
    for delimiter in DELIMITERS:
        # A comma only counts as separator if it is not just a decimal comma.
        if delimiter == ",":
            if all(len(line.split(",")) >= 2 for line in sample) and any(
                parse_datetime(line.split(",")[0]) for line in sample
            ):
                return ","
            continue
        if sum(delimiter in line for line in sample) * 2 >= len(sample):
            return delimiter
    return ";"


def _split(line: str, delimiter: str) -> list[str]:
    return [col.strip().strip('"').strip() for col in line.split(delimiter)]


def _header_columns(columns: list[str]) -> dict[str, int] | None:
    """Map a header line to column indexes, None if it is not a header."""
    if parse_datetime(columns[0]) is not None:
        return None
    mapping: dict[str, int] = {}
    for index, column in enumerate(columns):
        name = column.lower()
        for key, words in _HEADER_COLUMNS.items():
            if key not in mapping and any(word in name for word in words):
                mapping[key] = index
                break
    if "date" in mapping and "value" in mapping:
        return mapping
    return None


def parse_csv(text: str) -> ParseResult:
    """Parse CSV text into one reading per day.

    Several readings on one day are combined: the one with the latest time
    wins.  All lines that cannot be used are listed in ``rejected``.
    """
    result = ParseResult()
    lines = [
        (number, line.strip())
        for number, line in enumerate(text.lstrip("﻿").splitlines(), start=1)
        if line.strip()
    ]
    if not lines:
        return result
    result.delimiter = detect_delimiter([line for _, line in lines])
    mapping = _header_columns(_split(lines[0][1], result.delimiter))
    if mapping is not None:
        result.header = True
        lines = lines[1:]

    candidates: list[ParsedRow] = []
    for number, line in lines:
        result.data_lines += 1
        columns = _split(line, result.delimiter)

        def reject(reason: str, number: int = number, line: str = line) -> None:
            result.rejected.append({"line": number, "text": line[:120], "reason": reason})

        if mapping is not None:
            date_text = columns[mapping["date"]] if mapping["date"] < len(columns) else ""
            value_text = columns[mapping["value"]] if mapping["value"] < len(columns) else ""
            reset_text = (
                columns[mapping["reset"]] if "reset" in mapping and mapping["reset"] < len(columns) else ""
            )
            note = columns[mapping["note"]] if "note" in mapping and mapping["note"] < len(columns) else ""
        else:
            # date;value[;reset][;note] - a third column that is no flag is a note
            date_text = columns[0]
            value_text = columns[1] if len(columns) > 1 else ""
            third = columns[2] if len(columns) > 2 else ""
            if third.lower() in _TRUE_FLAGS | _FALSE_FLAGS:
                reset_text = third
                note = columns[3] if len(columns) > 3 else ""
            else:
                reset_text = ""
                note = third

        if len(columns) < 2:
            reject(REASON_TOO_FEW_COLUMNS)
            continue
        moment = parse_datetime(date_text)
        if moment is None:
            reject(REASON_INVALID_DATE)
            continue
        if not value_text:
            reject(REASON_MISSING_VALUE)
            continue
        value = parse_number(value_text)
        if value is None:
            reject(REASON_INVALID_VALUE)
            continue
        if value < 0:
            reject(REASON_NEGATIVE_VALUE)
            continue
        candidates.append(
            ParsedRow(
                day=moment[0],
                time=moment[1],
                value=value,
                reset=reset_text.lower() in _TRUE_FLAGS,
                note=note,
                line=number,
            )
        )

    # one reading per day (and reset flag): the latest time wins
    by_day: dict[tuple[date, bool], list[ParsedRow]] = {}
    for row in candidates:
        by_day.setdefault((row.day, row.reset), []).append(row)
    for (day, _reset), rows in by_day.items():
        rows.sort(key=lambda r: (r.time, r.value, r.line))
        result.rows.append(rows[-1])
        if len(rows) > 1:
            result.merged.append(
                {
                    "date": day.isoformat(),
                    "count": len(rows),
                    "kept": rows[-1].value,
                    "dropped": [r.value for r in rows[:-1]],
                }
            )
    result.rows.sort(key=lambda r: (r.day, r.reset))
    result.merged.sort(key=lambda m: m["date"])
    return result


def suggest_meter(filename: str) -> dict[str, str]:
    """Derive meter name, type and unit from a file name.

    "Nebenkosten / Strom - Zählerstände.csv" (or the download variant
    "Nebenkosten___Strom_-_Za_hlersta_nde.csv") -> Strom, electricity, kWh.
    """
    stem = re.sub(r"\.(csv|txt|tsv)$", "", filename.strip(), flags=re.IGNORECASE)
    lowered = stem.lower()
    meter_type = "other"
    for candidate, words in _TYPE_KEYWORDS:
        if any(word in lowered for word in words):
            meter_type = candidate
            break
    # drop the "- Zählerstände" suffix (umlauts may be replaced or decomposed)
    name = re.sub(r"[\s_-]*z[^\s/]{0,3}hlerst[^\s/]{0,3}nde.*$", "", stem, flags=re.IGNORECASE)
    name = re.sub(r"[\s_-]*(meter[\s_-]*readings?|readings?)$", "", name, flags=re.IGNORECASE)
    # the part after the group ("Nebenkosten / Strom", "Nebenkosten___Strom")
    parts = [p for p in re.split(r"\s*/\s*|_{2,}|\s+-\s+", name) if p.strip(" _-")]
    name = parts[-1] if parts else name
    name = re.sub(r"\s+", " ", name.replace("_", " ")).strip(" -")
    return {
        "name": name or filename,
        "type": meter_type,
        "unit": DEFAULT_UNITS[meter_type],
    }


def build_preview(
    parsed: ParseResult,
    existing: list[dict[str, Any]],
    replace: bool,
) -> dict[str, Any]:
    """Compare parsed rows with the readings of the target meter.

    ``existing`` are the stored readings of the meter (ignored if they are
    replaced).  Rows whose value does not fit to the neighbouring readings are
    flagged; the user has to decide what to do with them.
    """
    stored = [] if replace else existing
    stored_keys = {(str(r["date"])[:10], bool(r.get("reset"))) for r in stored}

    new_rows: list[ParsedRow] = []
    skipped: list[str] = []
    for row in parsed.rows:
        if (row.day.isoformat(), row.reset) in stored_keys:
            skipped.append(row.day.isoformat())
        else:
            new_rows.append(row)

    # stored and new readings in one timeline
    timeline: list[tuple[str, bool, float, ParsedRow | None]] = [
        (str(r["date"])[:10], bool(r.get("reset")), float(r["value"]), None) for r in stored
    ]
    timeline.extend((row.day.isoformat(), row.reset, row.value, row) for row in new_rows)
    timeline.sort(key=lambda item: (item[0], item[1]))

    flagged: list[dict[str, Any]] = []
    for index, (day, reset, value, row) in enumerate(timeline):
        if row is None or reset:
            continue
        previous = timeline[index - 1] if index > 0 else None
        following = timeline[index + 1] if index + 1 < len(timeline) else None
        if previous is not None and value < previous[2]:
            flagged.append(
                {
                    "date": day,
                    "value": value,
                    "reason": FLAG_LOWER,
                    "other_date": previous[0],
                    "other_value": previous[2],
                }
            )
        elif (
            following is not None
            and following[3] is None  # only against stored readings
            and not following[1]
            and value > following[2]
        ):
            flagged.append(
                {
                    "date": day,
                    "value": value,
                    "reason": FLAG_HIGHER,
                    "other_date": following[0],
                    "other_value": following[2],
                }
            )

    return {
        "start": parsed.rows[0].day.isoformat() if parsed.rows else None,
        "end": parsed.rows[-1].day.isoformat() if parsed.rows else None,
        "last_value": parsed.rows[-1].value if parsed.rows else None,
        "data_lines": parsed.data_lines,
        "days": len(parsed.rows),
        "new": len(new_rows),
        "merged": parsed.merged,
        "merged_lines": sum(m["count"] - 1 for m in parsed.merged),
        "skipped_existing": skipped,
        "rejected": parsed.rejected,
        "flagged": flagged,
        "replaced": len(existing) if replace else 0,
        "delimiter": parsed.delimiter,
        "header": parsed.header,
    }


def rows_to_import(
    parsed: ParseResult,
    existing: list[dict[str, Any]],
    replace: bool,
    decisions: dict[str, str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return the rows to store and the flagged dates without a decision."""
    preview = build_preview(parsed, existing, replace)
    flagged = {item["date"] for item in preview["flagged"]}
    undecided = sorted(d for d in flagged if decisions.get(d) not in DECISIONS)
    stored_keys = set() if replace else {(str(r["date"])[:10], bool(r.get("reset"))) for r in existing}
    rows: list[dict[str, Any]] = []
    for row in parsed.rows:
        day = row.day.isoformat()
        if (day, row.reset) in stored_keys:
            continue
        reset = row.reset
        if day in flagged and not row.reset:
            decision = decisions.get(day)
            if decision == DECISION_SKIP:
                continue
            reset = decision == DECISION_RESET
        rows.append({"date": day, "value": row.value, "reset": reset, "note": row.note})
    return rows, undecided
