# Reports, spreadsheets and reusable exports

> Methods with formulas, steps and acceptance checks: [app-ai-patterns](app-ai-patterns.md), [methods-fundamentals-valuation](methods-fundamentals-valuation.md).

## Research output

Lead with the answer or decision-relevant finding. Include dates, units, covered universe and material assumptions. Separate API observations from calculations and scenarios. A missing value should appear as unavailable with its reason, not zero. Avoid long operational recaps in customer-facing responses.

Company reports can contain profile, financial trends, valuation, peers, catalysts, risks and data qualifications. Portfolio reports can contain NAV, contributions/withdrawals, returns, allocation, attribution, risk and proposed rebalances. Investment memos can separate thesis, evidence, scenarios, contrary evidence and unresolved diligence questions. Do not imply that an automatically generated report has regulatory certification.

## Workbooks

Organize inputs, assumptions, calculations and outputs. Preserve formulas, named ranges and existing formatting when editing a template. Use cell formulas for derived values and scenario calculations rather than frozen results. Make units, currency, periods and Actual/Estimate labels visible. Distinguish inputs/formulas by restrained styling and a legend, not mandatory aesthetic choices.

In Office JS, write a merged header's value to its top-left cell before merging/formatting when required by the API; a multi-cell range cannot accept an incorrectly shaped one-cell value array. In standalone Python, openpyxl writes formulas but does not calculate them. Recalculate with an available spreadsheet engine and inspect errors/cached results; otherwise disclose the limitation.

For an investment-committee data pack, use the standard tab set (cover/notes, IS, BS, CF, KPIs, EBITDA adjustments in conservative and aggressive columns, public comps, returns, sources) in [methods-fundamentals-valuation.md](methods-fundamentals-valuation.md) §13.5.

Test assets = liabilities + equity, cash roll-forward, debt roll-forward, scenario propagation, DCF base/sensitivity consistency and input links. Check for broken references, division by zero, unintended hardcodes and circularity.

## CSV/JSON/data samples

Include the fields the user needs, with correct symbol/date scope and units. Avoid API tokens in filenames, metadata or requests. A simple sample usually needs a short explanation of dataset, interval and dates, not a pile of manifests. Detailed manifests are appropriate for research reproducibility when requested/needed.

For CSV opened in spreadsheets, defend against formula injection in untrusted textual fields beginning with spreadsheet-control characters while retaining an unmodified raw archive. Preserve identifier leading zeros and date formats. Use UTF-8 and an explicit delimiter/decimal convention.

### Cleaning messy user spreadsheets

**Use when** a user uploads holdings, transactions or a model export (XLSX/CSV) that must be joined with
EODHD data. **EODHD inputs**: none until symbols are resolved (then symbol lists / ID Mapping, 1 call each).

**Method — profile first, propose, apply only after approval.**
1. Keep the original file untouched; work on a copy with a cleaning log (cell/column, rule, before, after).
2. Profile each column: inferred type (number, date, text, identifier), blank and error-cell counts
   (`#N/A`, `#VALUE!`, `#REF!`, `#DIV/0!`), numbers stored as text, leading/trailing spaces, mixed case,
   distinct-value counts, garbled characters (mojibake such as `Ã©` from a wrong encoding — re-decode the
   source as UTF-8/cp1252 rather than patching characters).
3. Detect the locale per column: decimal comma vs point (`1.234,56` vs `1,234.56`), parentheses for
   negatives, percent signs, non-breaking or thin spaces as thousands separators; dates in mixed orders
   (`03/04/2026` is ambiguous — decide per column from values above 12, else ask).
4. Identifiers: keep ISIN/CUSIP/codes as text (leading zeros), validate check digits
   ([data-engineering-patterns §4](data-engineering-patterns.md), Q13), upper-case codes, strip spaces.
5. Duplicates: exact duplicate rows, and near-duplicates on a business key (account, date, symbol,
   quantity, price within tolerance) — report, never delete silently.
6. Present the proposed fixes as a table with counts; apply after the user approves; re-profile and show the
   before/after summary. Unparseable cells stay flagged, not coerced to zero.

```python
import re, unicodedata

ERROR_TOKENS = {"#N/A", "#VALUE!", "#REF!", "#DIV/0!", "#NAME?", "#NUM!", "#NULL!", "N/A", "NA", "-", "—", ""}

def detect_decimal(samples):
    """Return ',' or '.' as the decimal separator from a column of number-like strings."""
    votes = {",": 0, ".": 0}
    for s in samples:
        s = s.strip().replace(" ", "").replace(" ", "")
        m = re.fullmatch(r"[-+(]?[\d.,]+\)?%?", s)
        if not m: continue
        last = max(s.rfind(","), s.rfind("."))
        if last == -1: continue
        tail = len(re.sub(r"\D", "", s[last + 1:]))
        sep = s[last]
        if s.count(sep) == 1 and tail != 3:      # unambiguous decimal mark
            votes[sep] += 1
        elif "," in s and "." in s:               # both present: the last one is decimal
            votes[sep] += 1
    return "," if votes[","] > votes["."] else "."

def parse_number(s, decimal="."):
    """Parse a spreadsheet cell to float, or None for blanks/error tokens. Never guesses silently."""
    if s is None: return None
    t = unicodedata.normalize("NFKC", str(s)).strip().replace(" ", "").replace(" ", "")
    if t.upper() in ERROR_TOKENS: return None
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    pct = t.endswith("%"); t = t.rstrip("%")
    thousands = "." if decimal == "," else ","
    t = t.replace(thousands, "").replace(decimal, ".")
    if not re.fullmatch(r"[-+]?\d+(\.\d+)?", t): raise ValueError(f"unparseable number: {s!r}")
    v = float(t) * (-1 if neg else 1)
    return v / 100 if pct else v
```

**Acceptance checks.** `detect_decimal(["1.234,56","12,5","3,14"]) == ","`; `parse_number("1.234,56", ",")
== 1234.56`; `parse_number("(1,200.50)") == -1200.5`; `parse_number("12,5%", ",") == 0.125`;
`parse_number("#N/A") is None`; `parse_number("12abc")` raises instead of guessing.

## PDF and presentations

Use ordinary available rendering libraries and inspect the output for overflow, missing glyphs, clipped tables, unreadable charts and incorrect page breaks. Charts must show axes, currency/units, dates and basis. Use forecast/actual styling consistently. A chart title should not claim “live” for delayed/EOD observations.

Present key conclusions and supporting evidence, not every intermediate table. Keep source attribution appropriate to the output; omit private implementation details. Include required licences with reused code/assets rather than putting unrelated service links in the data workflow.

## Deck refresh and QC

Applies to slide decks, pitch books, tear sheets and memo documents that already contain numbers. Method
format and severity classes match [methods-fundamentals-valuation.md](methods-fundamentals-valuation.md)
§12 and §14.

### Deck refresh procedure

**Use when:** rolling an existing deck to a new quarter, a new price date or a refreshed comps set, so
that every old figure is found and replaced and nothing derived from it is left stale.

**EODHD inputs:** the same requests that produced the original figures, re-run with the new as-of date
(Fundamentals 10 calls per company, EOD 1 call per symbol, calendar and news as used). Keep the old and
the new bundle side by side with their retrieval times.

**Method.**
1. **Inventory.** Extract every number from slide text, tables, chart data (the embedded data sheet,
   not the picture), footnotes, speaker notes and the source line. Record slide, location, raw text and
   the context scale (a table under "USD m" has scale 10^6).
2. **Re-pull** each input with the new as-of date and record old value, new value, unit and source per
   metric id.
3. **Variant map.** For each old value, find every form it takes in the deck: scale (1.2bn, 1,200m),
   precision (1,200 vs 1,200.0), unit words (billion, bn, b), separators, parentheses for negatives,
   and per-share or percent forms. Match a token when the old value, rounded to the token's own
   precision and scale, equals the token (code below). A rounded form ("1.2bn") can match several close
   values, so confirm by location.
4. **Stale derived numbers.** Build the dependency list for every derived figure (growth rates, margins,
   per-share values, multiples, CAGR, share counts, totals, "x% of revenue" sentences). Any derived
   figure whose input changed is stale and must be recomputed from the new inputs, never edited by hand.
   Narrative words tied to a number ("record", "doubled", "ahead of consensus") are re-checked too.
5. **Change plan before editing.** Present a table: slide, location, old text, new text, reason (new
   period, new price, restatement, recomputed derived), plus figures found but not mapped. Edit only
   after the plan is accepted.
6. **Apply with formatting kept.** Replace text runs and chart data in place, keeping fonts, number
   formats and the original precision of each occurrence. Update every as-of date and the source line.
7. **Re-run the cross-slide check** below and render the deck to images for inspection.

```python
import re

SCALE = {"": None, "k": 1e3, "thousand": 1e3, "m": 1e6, "mn": 1e6, "mm": 1e6, "million": 1e6,
         "b": 1e9, "bn": 1e9, "billion": 1e9, "t": 1e12, "tn": 1e12, "trillion": 1e12}
TOKEN = re.compile(
    r"(?<![\w.,])(\()?(-)?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(\))?"
    r"(?:\s?(%|bn|billion|mn|mm|million|thousand|trillion|tn|b|m|k|t)(?![A-Za-z]))?", re.I)

def tokens(text, context_scale=1.0):
    """Yield (raw, shown, decimals, scale, lo, hi) for each number in text.
    Bare numbers take context_scale (1e6 under a 'USD m' header). [lo, hi] is the
    base-unit interval of values that would display as this token."""
    for mt in TOKEN.finditer(text):
        po, minus, intpart, frac, pc, unit = mt.groups()
        unit = (unit or "").lower()
        if unit == "%":
            continue                                    # percentages are checked as their own metric
        scale = SCALE[unit] or context_scale
        dec = len(frac) - 1 if frac else 0
        shown = float(intpart.replace(",", "") + (frac or ""))
        closed = pc or text[mt.end():mt.end() + 1] == ")"     # (1,200) or (1,200m)
        if minus or (po and closed):
            shown = -shown
        half = 0.5 * 10 ** -dec
        yield mt.group(0).strip("() "), shown, dec, scale, (shown - half) * scale, (shown + half) * scale

def find_variants(text, target, context_scale=1.0):
    """Tokens that display `target` (base units) at their own precision and scale."""
    out = []
    for raw, shown, dec, scale, lo, hi in tokens(text, context_scale):
        if abs(round(target / scale, dec) - shown) < 1e-9 * max(1.0, abs(shown)):
            out.append(raw)
    return out

def consistent(occurrences):
    """occurrences: [(where, raw_text, context_scale)] for ONE metric. True if one value could
    produce every displayed token (interval intersection is non-empty)."""
    lo, hi = float("-inf"), float("inf")
    for where, raw, cs in occurrences:
        t = next(tokens(raw, cs))
        lo, hi = max(lo, t[4]), min(hi, t[5])
    return lo <= hi, (lo, hi)

def stale(derived_inputs, changed):
    """derived_inputs: {derived_id: {input_ids}}; returns derived figures to recompute."""
    return sorted(d for d, ins in derived_inputs.items() if ins & changed)
```

**Pitfalls.** Updating the chart picture but not its data sheet. Search-and-replace on "1.2" that also
hits "1.25" or a date. Footnote periods ("LTM to June") left on the old quarter. Rounding the new value
to a different precision than the slot had. A restated old period counted as a "new period" change.

**Acceptance checks.** For an old figure of 1,200.0m (target 1.2e9): the slide text "Revenue reached 1.2bn
in FY2025 (1,200m in the appendix), up 9% on 1,100m; EBITDA 1,250m." yields `['1.2bn', '1,200m']`, and
the table row "1,200.0 | 1,100.0 | 2021" under a "USD m" header yields `['1,200.0']`; 1,250m, 9%, 2021 and
FY2025 are not matched. For an old figure of 1,203.4m, "1.2bn | 1,203m | 1,203.4 | 1,200m" yields
`['1.2bn', '1,203m', '1,203.4']`. "(1,200m)" is a negative and does not match a positive target. With
dependencies {{rev_growth: rev_fy25, rev_fy24; eps: ni, shares; ev_ebitda: ev, ebitda}} and changed inputs
{{rev_fy25, shares}}, the stale list is `['eps', 'rev_growth']`.

### Cross-slide consistency check

**Use when:** QC of a client deck or report before release, independent of whether it was refreshed.

**Method.**
1. Tag every number occurrence with a metric id, period and basis (text, table, chart data, footnote).
2. Normalize each occurrence to base units with its own scale, and turn it into the interval of values
   that would display that way (`tokens()` above).
3. **Consistency:** all occurrences of one metric and period must have a non-empty interval
   intersection (`consistent()` above). An empty intersection means two slides show different values.
4. **Recompute** totals from components (allow n × half a display unit for rounding), growth from the
   two endpoints, margins from numerator and denominator, and per-share values from the stated share
   count.
5. Check period labels (FY vs LTM vs CY), currency and units against the metric-definition table
   ([methods-fundamentals-valuation.md](methods-fundamentals-valuation.md) §8.7), and that every chart
   carries a source, an as-of date and units.
6. Report findings ranked by the §14 severity classes: conflict or failed recompute = critical; wrong
   period, unit or currency label = major; precision or format inconsistency = minor.

**Acceptance checks.** "1.2bn" (slide 2 text), "1,203.4" under "USD m" (slide 5 table) and "1,203m" (slide
9 chart) are consistent (intersection 1,203.35m–1,203.45m). "1.2bn" and "1,260.0" under "USD m" conflict
(empty intersection), which is a critical finding. Components 400.4 + 300.3 + 500.4 displayed as 400,
300, 500 with a total of 1,201 pass (within 3 × 0.5).

### Template population (pitch decks and strip profiles)

**Use when:** filling a house template (pitch book, strip profile, tear sheet) from EODHD data and user
files.

**Method.**
1. **Back up the template** and work on a copy. Record the template version.
2. **Placeholder map.** List every placeholder (text tag, table cell, chart data range) and map it to a
   data field: endpoint and field path or calculation id, period, basis and display format. A
   placeholder with no mapping stays visibly empty with "n/a (reason)", never a stale sample value.
3. **Convert units and currency once,** at the mapping step: GBX/ZAC to major units, statement currency
   to the presentation currency with one dated FX rate, and scale to the slot's unit (m or bn). Store the
   converted value. Templates never convert again.
4. Populate, keeping the template's formatting and the slot's precision.
5. **Render to images** (each slide or page) and inspect for overflow, clipped tables, missing glyphs,
   wrapped numbers and empty charts. Fix by layout changes, not by dropping data silently.
6. **State the renderer's limitations** in the delivery note: for example, a converter that does not
   evaluate embedded chart formulas, substitutes fonts or ignores animations. If no renderer is
   available, say that the visual check was not done.
7. Run the cross-slide consistency check and the §12.1 critic pass of
   [methods-fundamentals-valuation.md](methods-fundamentals-valuation.md).

**Pitfalls.** Converting units both in the data step and through a template number format ("#,##0,,"
already divides by a million). Sample numbers left in an unused slot. A chart whose data range is longer
than the new series, leaving old points visible.

**Acceptance checks.** Every placeholder appears in the map with a field or a reason. A GBX price of 2,450
is stored once as 24.50 GBP, and the rendered slide shows 24.50. The backup file exists and is unchanged.
