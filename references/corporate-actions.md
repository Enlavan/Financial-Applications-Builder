# Splits, distributions and adjustment ledgers

## Keep event and price representations separate

Store raw split strings and parsed numerator/denominator, date, raw dividend amount, adjusted amount when provided, currency and all event dates. Document which direction a split ratio represents using known examples. Do not interpret every noninteger ratio as a simple share split: spin-offs and other adjustments may appear as fractional events.

For a forward split of `new_shares / old_shares = r`, earlier split-only prices divide by r, earlier share counts multiply by r, and as-traded earlier volume becomes r times larger on the post-split basis. Reverse splits use r below one. The action changes position quantity and per-share cost; it does not itself create investment profit.

Cash distributions have distinct declaration, ex, record and payment dates. Eligibility/accounting and forecast calendars use different dates. A dividend API amount may be adjusted for later splits; use the appropriate unadjusted amount when modelling actual cash per share at the event. Several distributions on one ex-date may be represented by a combined amount. Do not invent an unsupported regular/special breakdown.

## Reconstruct an adjusted series carefully

When implementing a simple cash-dividend backward adjustment, a commonly used event factor is `(P_previous - D) / P_previous`, applied before the ex-date, composed with split factors in a declared basis/order. This is a modelling convention; do not claim it reproduces every EODHD event treatment. Large/special distributions, same-day splits, spin-offs and currency mismatches need explicit handling. A nonpositive factor is a reason to investigate, not to clamp to an arbitrary epsilon.

Derive fully adjusted OHLC using the reported daily `adjusted_close / close` when that is the requested basis. Do not recalculate and overwrite source values merely because a simplified event model differs. Maintain observed and derived columns separately.

## Two valid backtest accounting approaches

1. **Total-return adjusted-price research:** calculate returns from adjusted close. Do not add dividends again. Results reflect today's adjustment vintage unless a local earlier capture is used.
2. **Explicit ledger simulation:** transact/mark on appropriate raw prices, update position quantities for splits, accrue distribution entitlement and settle cash on the payment policy, model cash-in-lieu and fees when known. Use compatible raw/split-adjusted volumes for liquidity constraints.

Never combine current total-return prices with a second cash-dividend credit. Do not treat merger consideration as a traded closing bar. A record after trading ceased may be suspect, but its cause must not be invented from a single value.

## Investigating anomalies in a user's archive

Compare a bounded event window; retrieve current EOD, splits and dividends together; match currencies, share bases, ex-dates and capture versions. Check price factor discontinuities, duplicate events, unit shifts and clamped values. A 100× discrepancy can indicate units but is not sufficient evidence to multiply an entire history.

Correct only the user's derived/local dataset when requested and supported by verified evidence. Preserve old captures, write a scoped transformation with before/after counts and repeatability, and distinguish confirmed correction from unresolved anomaly. This skill has no EODHD service-side mutation capability. For an unresolved source record, produce a minimal reproducible example with symbols, dates, sanitized requests and observed values.

## Corporate-action ledger events

**Use when:** a paper ledger, tax-lot book or backtest has to turn an action into entitlements, lot changes
and cash: dividends around the ex/record dates, fractional shares paid in cash, cash or stock merger
consideration, and spin-offs. The lot mechanics follow
[methods-planning-wealth §7](methods-planning-wealth.md#7-tax-lot-accounting) step 2.

**EODHD inputs:** `/api/div/{SYM}?fmt=json` (1 call; `date` = ex-date, `recordDate`, `paymentDate`,
`unadjustedValue`, `currency`); `/api/splits/{SYM}` (1 call); raw closes from `/api/eod` for fair-market
values; `/api/v2/exchange-details/{EX}` for sessions and holidays (Extended or All-In-One).
**User-supplied, with no EODHD source:** merger terms (ratio, cash per share, elections, proration),
spin-off distribution ratio when it is not in the split feed, the cash-in-lieu price actually paid, the
settlement-day calendar (bank holidays), and the **basis rules** of the user's jurisdiction (which
valuation date, which allocation, how much gain a cash leg triggers).

### Entitlement dates (US T+1)

- A holder is entitled to a cash dividend when the position was held at the close of the session **before**
  the ex-date (trade-date basis). Payment cash arrives on `paymentDate`.
- US regular-way settlement moved to T+1 on 2024-05-28 (T+2 from 2017-09-05). Rule: the ex-date is the
  first session whose trade would settle **after** the record date. Under T+1 this makes ex-date = record
  date; under T+2 the ex-date was one business day before it.
- Exception: when the record date is not a settlement day (the exchange is open but banks are closed,
  e.g. US Veterans Day), the ex-date moves one session earlier. Large stock distributions can follow
  different exchange rules (ex-date after the payable date); take those dates from the record, not the
  rule.
- Use the rule to **check** EODHD rows, not to overwrite them: for US rows from 2024-05-28 on, flag
  `date ≠ recordDate` for review.

### Cash in lieu of fractional shares

For a share-for-share event with ratio `k` new per old (split, reverse split, stock merger, spin-off):
`new_exact = q·k`, whole shares `⌊new_exact⌋`, fraction `φ = new_exact − ⌊new_exact⌋`. The basis per new
share is `B / new_exact`; the fraction carries basis `φ·B/new_exact` and is treated as sold for
`φ·P_cil`, where `P_cil` is the cash per whole share actually paid (from the statement; never estimated from
the close without a label). Gain = proceeds − fraction basis. The remaining whole shares keep the rest of
the basis and the original acquisition date.

### Merger consideration

- Close every target lot on the effective date. Open acquirer lots for `q·ratio` shares (fractions via cash
  in lieu above). The cash leg is proceeds. Do **not** create a target "closing bar" from the deal price.
- Fair-market value of the stock leg = acquirer raw close on the effective date (EODHD), labelled.
- Basis follows the **user-declared** rule. Two common shapes, both parameters, not advice:
  - fully taxable exchange: gain = stock FMV + cash − basis; new basis = stock FMV;
  - carry-over with cash "boot": recognized gain = `max(0, min(realized gain, cash))`; new basis =
    old basis − cash + recognized gain.
- Elections and proration (cash/stock election pools) come from the user's statement.

### Spin-off basis allocation

Child shares `= q·ratio`. Allocate the parent basis by relative market value on the declared valuation date
(commonly the first regular-way session; the jurisdiction or the issuer's notice decides):
`B_child = B·MV_child / (MV_parent + MV_child)` with raw closes of both listings on that date; the parent
keeps the rest. The child's acquisition date follows the user's rule (often the parent's date). A spin-off
may appear in the split or price-adjustment data as a fractional factor; do not book it as a split.

```python
import datetime as dt

def ex_date_from_record(record, settle_lag, trading_days, settlement_days):
    """US regular-way rule: the ex-date is the first trading session whose trade would settle AFTER
    the record date. settle_lag = 1 from 2024-05-28 (T+1), 2 before that (T+2 from 2017-09-05).
    trading_days / settlement_days: sorted lists of dt.date (exchange sessions; settlement-bank days)."""
    sset = sorted(settlement_days)
    def settle(t):
        later = [d for d in sset if d > t]
        return later[settle_lag - 1]
    return next(t for t in trading_days if settle(t) > record)

def cash_in_lieu(old_qty, old_basis, ratio_new_per_old, cil_price):
    """Share-for-share event with a fractional entitlement paid in cash.
    cil_price = cash paid per whole new share (user / statement supplied)."""
    new_exact = old_qty * ratio_new_per_old
    whole = int(new_exact)
    frac = new_exact - whole
    basis_per_new = old_basis / new_exact
    frac_basis = frac * basis_per_new
    proceeds = frac * cil_price
    return {"new_shares": whole, "new_basis": old_basis - frac_basis, "fraction": round(frac, 10),
            "cil_proceeds": round(proceeds, 2), "cil_basis": round(frac_basis, 2),
            "cil_gain": round(proceeds - frac_basis, 2)}

def merger_consideration(qty, basis, stock_ratio, cash_per_share, acq_price, basis_rule):
    """Target lot closed; acquirer lot opened at stock_ratio per target share; cash leg = proceeds.
    acq_price: acquirer raw close on the effective date (EODHD), used for FMV.
    basis_rule (USER-SUPPLIED, jurisdiction-specific):
      "taxable"             - full disposal: gain = FMV + cash - basis; new basis = stock FMV
      "carryover_with_boot" - gain recognized = min(realized gain, cash) (not below 0);
                              new basis = basis - cash + recognized gain"""
    new_shares = qty * stock_ratio
    stock_fmv = new_shares * acq_price
    cash = qty * cash_per_share
    realized = stock_fmv + cash - basis
    if basis_rule == "taxable":
        recognized, new_basis = realized, stock_fmv
    elif basis_rule == "carryover_with_boot":
        recognized = max(0.0, min(realized, cash))
        new_basis = basis - cash + recognized
    else:
        raise ValueError("basis_rule must be declared by the user")
    return {"close_target_qty": qty, "open_acquirer_qty": new_shares, "acquirer_basis": new_basis,
            "cash_proceeds": cash, "realized_gain": realized, "recognized_gain": recognized}

def spinoff_allocation(parent_qty, parent_basis, child_per_parent, parent_px, child_px):
    """Allocate basis by relative FMV on the declared valuation date (user rule; EODHD raw closes
    of the first regular-way session are the usual market input)."""
    child_qty = parent_qty * child_per_parent
    mv_p, mv_c = parent_qty * parent_px, child_qty * child_px
    child_basis = parent_basis * mv_c / (mv_p + mv_c)
    return {"child_qty": child_qty, "child_basis": child_basis,
            "parent_basis": parent_basis - child_basis,
            "child_share_of_basis": mv_c / (mv_p + mv_c)}
```

**Pitfalls:**

- Using the adjusted dividend `value` for cash received after a later split understates or overstates cash
  by the split factor; use `unadjustedValue`.
- Booking a spin-off or merger as a split changes quantity without creating the second lot or the cash.
- Fraction basis must come out of the lot, or total basis is overstated by the fraction's share.
- Missing user terms (ratio, cash, election, basis rule) block the event with an "awaiting terms"
  exception; never fill them with a default.

**Acceptance checks** (values from the code above; the dividend dates match the demo-key
`/api/div` pull of 2026-10-25):

- T+1, record 2024-08-12 → ex-date 2024-08-12 (AAPL row: `date` = `recordDate` = 2024-08-12).
- T+1, record 2024-11-11 with 2024-11-11 a settlement holiday → ex-date **2024-11-08** (AAPL row: `date`
  2024-11-08, `recordDate` 2024-11-11; flagged by the check, explained by the holiday).
- T+2, record 2024-05-16 → ex-date 2024-05-15 (MSFT row before the T+1 switch).
- 1-for-10 reverse split of 1,005 shares with basis 10,050 and `P_cil` 12.00 → 100 shares, basis 10,000;
  fraction 0.5, proceeds 6.00, fraction basis 50.00, loss −44.00.
- 100 target shares, basis 2,000, consideration 0.5 acquirer shares + 20 cash per share, acquirer close
  60 → 50 acquirer shares and 2,000 cash. Fully taxable: gain 3,000, new basis 3,000. Carry-over with boot:
  recognized 2,000, new basis 2,000. With basis 6,000 (a loss) and carry-over: recognized 0, new basis
  4,000.
- 100 parent shares, basis 10,000, 1 child per 4 parents, closes 72 and 32 → 25 child shares with basis
  1,000 (10%), parent basis 9,000; total basis unchanged.

## Acceptance checks

- A synthetic 2-for-1 split preserves portfolio value and halves per-share basis.
- A dividend is credited once, at the chosen accounting dates, in its actual currency.
- A split and dividend on one date use explicitly compatible share units.
- Adjustment factors are computed per day; invalid/zero closes cannot produce infinity.
- Rerunning a correction does not compound the factor a second time.
- The original response and original derived version remain reproducible.
- Ledger events: the fixtures under [Corporate-action ledger events](#corporate-action-ledger-events) reproduce, and total basis is conserved across every share-for-share event (fraction basis included).
