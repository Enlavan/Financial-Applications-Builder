# Quality checks and endpoint reconciliation

> Methods with formulas, steps and acceptance checks: [data-engineering-patterns](data-engineering-patterns.md).

## Separate transport, coverage and financial validity

A successful job only proves execution. Validate HTTP/envelope first, then schema/types, keys, dates and coverage, then financial relationships. Keep warnings and failures distinct. A heuristic flag identifies a record for examination; it does not prove an error or prescribe a correction.

## Useful checks

| Check | Interpretation / caveat |
|---|---|
| Unique listing/date/interval/basis keys | Duplicate captures are allowed in archive, not duplicate current logical rows |
| Finite OHLC and nonnegative volume | Zero/missing fields need separate interpretation; derivative prices can have special cases |
| `low ≤ open,close ≤ high` | Requires same bar/basis and known values; do not replace zeros automatically |
| Price/adjustment-factor jumps | Compare actions and neighbouring rows; genuine splits/spin-offs can cause discontinuities |
| Repeated maximum/clamped values | Flag suspicious plateaus; cannot infer true replacement values from the cap |
| Currency/unit shifts | Verify metadata and event amounts before multiplying a range |
| Trading-session gaps | Use actual exchange calendars and instrument availability; missing bar is not always a missed trade |
| Statement identities | Use compatible periods, units and accounting fields; ratios can differ by convention |
| Dividend > price | Investigate share basis, special/cash-stock distributions and units; not conclusive by itself |
| Identifier/name mismatch | Examine reuse, cross-listing and historical issuer identity |
| Identifier check digits | ISIN (ISO 6166, Luhn) and CUSIP (modulus 10) validators flag malformed values; a valid digit does not prove the mapping — [Q13](data-engineering-patterns.md#4-executable-data-quality-suite) |
| Day-over-day move by asset class | Per-class limits (equity, ETF, fund, index, FX, crypto, bond) send large moves and ×100 unit shifts to a review queue, never to an automatic fix — [Q14](data-engineering-patterns.md#4-executable-data-quality-suite) |
| Freshness | Compare observation time, session expectations and business threshold, not only retrieval time |

## Cross-endpoint reconciliation

Align symbol identity, currency, price basis, trading date/session, interval, timezone, capture time and revision before comparing. EOD, intraday aggregation, delayed quotes and streaming last trades need not match because they measure different observations. Retrieve compared endpoints close together when testing a claimed discrepancy. If current responses agree, say that; do not assert why an older capture differed without evidence.

An independently delivered five-minute bar is not guaranteed equal to resampled one-minute observations. Adjusted data from another archive cannot be compared directly with raw OHLC. Small decimal discrepancies can reflect rounding/representation, but a large mismatch needs investigation rather than a generic explanation.

## Price-check reconciliation against a custodian or administrator

**Use when** the user compares EODHD prices with prices on a custodian statement, a fund administrator's
valuation file or a broker export, and needs every difference classified rather than "fixed".

**EODHD inputs**: `eod/{SYM}` around the valuation date (1 call per listing, full range in one request) or
the archived rows; `div/` and `splits/` (1 each) for the action check; the symbol list for currency and unit
(1 per exchange). The external prices, their dates and their currencies are user-supplied.

**Method.**

1. Match on listing and **valuation date**. Resolve the external identifier (ISIN, CUSIP) to one EODHD
   listing with the holding's exchange and currency first ([identity.md](identity.md)); an unresolved line
   is a break of class `identity`, not a skipped row.
2. Normalize before comparing: the same currency (FX only with a dated `*.FOREX` close and a stated
   orientation), the same unit (GBX/GBP, ZAC/ZAR), and the same basis (raw close for valuation; never
   `adjusted_close`).
3. Relative difference `δ = P_ext/P_eodhd − 1`; matched if `|δ| ≤ tol(class)`. Tolerances are user policy;
   starting points: equities and ETFs 5 bp, funds 10 bp, bonds 25 bp, FX 2 bp.
4. Classify each break: `unit` (ratio within 10·tol of 100 or 0.01), `corporate_action` (ratio ≈ split
   ratio, with a split ex-date between the two observation dates), `timing` (external price equals the
   previous or next session's close: stale or forward-dated feed), `missing_external` / `missing_eodhd`,
   else `source` (an unexplained difference).
5. Stale flag: the external price date, or the EODHD bar date, is older than the last completed session for
   that exchange ([data-engineering-patterns.md](data-engineering-patterns.md) §5 SLA).
6. Age open breaks from first seen (`0–1d`, `2–5d`, `>5d`) and escalate by age and value at stake. Never
   overwrite either side; a `source` break goes to the minimal reproduction in the repair workflow below.

```python
TOL = {"equity": 0.0005, "etf": 0.0005, "fund": 0.001, "bond": 0.0025, "fx": 0.0002}   # relative, user policy

def classify_break(ours, theirs, prev_close, next_close, split_ratio, tol):
    """ours/theirs: prices for the same listing and valuation date, already in the same currency unit
    where the metadata says so. Returns None when matched, else the break class."""
    if theirs is None:
        return "missing_external"
    if ours is None:
        return "missing_eodhd"
    r = theirs / ours
    if abs(r - 1) <= tol:
        return None
    for k in (100.0, 0.01):
        if abs(r / k - 1) <= 10 * tol:
            return "unit"                                # GBX/GBP, ZAC/ZAR
    if split_ratio and (abs(r * split_ratio - 1) <= 10 * tol or abs(r / split_ratio - 1) <= 10 * tol):
        return "corporate_action"
    for other in (prev_close, next_close):
        if other and abs(theirs / other - 1) <= tol:
            return "timing"                              # their price belongs to a neighbouring session
    return "source"

def age_breaks(open_breaks, today):
    """open_breaks: {key: first_seen date}; aging buckets drive escalation."""
    out = {}
    for key, first in open_breaks.items():
        d = (today - first).days
        out[key] = "0-1d" if d <= 1 else "2-5d" if d <= 5 else ">5d"
    return out
```

**Pitfalls.** A custodian "price" can be a bid, a mid or an evaluated price for bonds and funds: a
difference against an EODHD close is expected and is classified, not corrected. Funds strike NAV once a day,
often with a one-day lag. Comparing after converting only one side's currency produces a false `source`
break.

**Acceptance checks.** With equity tolerance 5 bp: 100.00 vs 100.03 matches; 6.385 vs 638.5 is `unit`;
50 vs 100 with a 2:1 split is `corporate_action`; 100 vs 99 when the previous close was 99 is `timing`;
100 vs 97 is `source`; a missing external price is `missing_external`. Breaks first seen on 2026-10-20 and
2026-10-23 age to `>5d` and `2–5d` on 2026-10-26.

## Repair workflow for local data

1. Reproduce the smallest affected records from a pinned capture and current EODHD request.
2. Classify: parsing, units, identity, dates, revision, entitlement/coverage, or unresolved source anomaly.
3. Fix application transformations when evidence supports it; keep raw bytes untouched.
4. Write a scoped, repeatable migration with expected row counts and preconditions if persistent local data changes.
5. Test known valid neighbouring records and the corrected output.
6. For unavailable/corrupt source data without a verified replacement, preserve a quality flag and a concise reproduction for support. Never invent a replacement price or claim a provider correction ETA.

## Contract tests and monitoring

Use synthetic fixtures for split/dividend accounting, zero/null separation, timezone/DST, symbol reuse, multi-currency statements, duplicate pagination, stale quotes and malformed envelopes. Track row-count/coverage/freshness distributions and unexpected schema changes; classify schema changes against [assets/dataset-contract.json](../assets/dataset-contract.json) as additive (WARN) or breaking (FAIL) with the contract diff in [data-engineering-patterns.md](data-engineering-patterns.md) §10. Set thresholds per dataset; arbitrary universal thresholds create false positives.

Quarantine failed normalized partitions in the user's application while preserving captures. Keep an issue record with actual symbol/date/field/observed value/expected invariant and capture ID. Do not send secrets or internal service assumptions in a support report. Output checks as PASS/WARN/FAIL/NOT TESTED with evidence.
