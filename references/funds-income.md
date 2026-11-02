# ETFs, mutual funds and income systems

> Methods with formulas, steps and acceptance checks: [methods-technical-market](methods-technical-market.md), [methods-planning-wealth](methods-planning-wealth.md).

## Fund identity and available fields

Check instrument type, ISIN/share class, accumulating/distributing policy, listing currency, fund currency, domicile, inception and available holdings/metrics dates. Similar fund names may refer to different classes, hedging or exchanges. An EUFUND price series does not imply fundamental coverage. Missing specialist metrics, including rating-style fields, must remain unavailable rather than inferred from a similar fund.

## Holdings and exposure

Use holdings weights as of their reported date. Calculate overlap as the sum of minimum weights for matching underlying securities under a stated identity map. Weighted sector/country/currency exposure requires known classifications and treatment of cash/derivatives. State covered weight and unclassified remainder; do not normalize a partial holdings list to 100% without labelling the result.

Look-through fund-of-fund exposure requires recursive expansion with cycle detection, date compatibility and an unknown remainder. Leverage, derivative notional and net asset weights differ; an inverse/leveraged ETF's stated daily objective is not a long-term return multiple.

## Dividend and income tracker

Store the position history and actual cash distributions separately from forecasts. Use ex-date for entitlement under the chosen market/accounting convention and payment date for cash availability. Handle record/declaration dates as their own fields. Calculate trailing distributions from compatible unadjusted cash amounts and price/share basis; projected yield is an assumption, not guaranteed future income.

Separate regular, special, capital-gain and return-of-capital classifications only where supported. If the response combines distributions for one ex-date, preserve the total and mark component details unavailable. Accumulating funds may have no cash distribution despite investment income; an empty dividend response alone does not prove the policy.

DRIP simulation needs reinvestment price/date, fractional-share rules, withholding/fees and FX. Report gross versus net income and tax assumptions. Never reinvest using adjusted close and also credit its embedded dividends a second time.

## Australian (ASX) income: franking, DRP and other corporate actions

**Use when** an income tracker, tax-aware dividend screen or portfolio ledger holds `.AU` securities.
**EODHD inputs**: `/api/asx-corporate-actions` ([reference](api/endpoints/asx-corporate-actions.md)), beta,
1 call per request, `page[limit]` ≤ 1000 with `links.next`; filters `type` (`dividends`, `splits`,
`bonus-issues`, `rights-issues`, `buybacks`, `capital-returns`, `spp`, `other`), `symbol` (`XXX.AU`),
`date_from`/`date_to` (event date). The docs list it under Fundamentals Data Feed and All-In-One but the
same page also says it is not in the standalone Fundamentals plan — verify with one request on the
user's key. Refreshed daily (same-day changes can lag up to 24 h). Prices come from normal EOD (`.AU`).

Dividend records carry the usual `date` (ex-date), `value`/`unadjustedValue`, `recordDate`, `paymentDate`,
`period` (Interim/Final), `currency`, plus `_asx_extra`: `franked_amount_aud`, `franked_percent`,
`drp_indicator`, `drp_price_aud`, `drp_discount_rate`, `bsp_indicator`, `special_indicator` (Y/N),
`withholding_tax_rate`, `tax_deferred_amount_aud`, `tax_advantaged_amount_aud`,
`foreign_source_dividend_aud`, `special_dividend_amount_aud`, free-text `comment`.

**Method.**
1. Pull `type=dividends` per holding (or for the exchange in pages) for the window; keep ex, record and
   payment dates separately (entitlement on ex-date, cash on payment date).
2. Franking credit per share = `franked × t / (1 − t)`, where `franked` = `franked_amount_aud` (or cash ×
   `franked_percent`/100) and `t` is the company tax rate the user supplies (30% general rate; 25% for
   base-rate entities). Grossed-up dividend = cash + credit. Whether the credit is usable (residency,
   holding-period rule, personal tax rate) is a user/tax-adviser question — show it, do not apply it.
3. Yields: cash yield and grossed-up yield on trailing regular dividends; exclude
   `special_indicator = Y` from the regular yield and show specials separately.
4. DRP: when the user participates, shares = entitlement / DRP price (`drp_price_aud`, after
   `drp_discount_rate`); residual cash handling is plan-specific (user). `drp_indicator` codes are
   exchange codes — map them only from the reference, and treat "DRP suspended" comments as no DRP.
5. Other actions feed the ledger ([corporate-actions](corporate-actions.md#corporate-action-ledger-events)):
   `capital-returns` reduce cost base (cash per share, payment date); `splits` (`split` "new:old") and
   `bonus-issues` (`ratio`) change quantity; `rights-issues` (`ratio`, `applicationPrice`,
   `applicationCloseDate`, renounceable or not) and `spp` (`price`, `minAmount`/`maxAmount`,
   `offerCloseDate`) are decisions the user makes — record them as offers, not as executed trades.
6. Reconcile with the general dividends endpoint (`/api/div/XXX.AU`): same ex-dates and cash amounts;
   the ASX endpoint adds franking and plan fields.

```python
def franking_credit(franked_amount, corp_tax_rate=0.30):
    """Franking credit attached to the franked part of a dividend (AUD per share).
    corp_tax_rate is user-supplied: 0.30 general rate, 0.25 for base-rate entities."""
    if not 0 <= corp_tax_rate < 1:
        raise ValueError("corp_tax_rate must be in [0, 1)")
    return franked_amount * corp_tax_rate / (1 - corp_tax_rate)

def asx_dividend_row(rec, corp_tax_rate=0.30):
    """Normalize one /api/asx-corporate-actions?type=dividends record."""
    x = rec.get("_asx_extra") or {}
    cash = rec["unadjustedValue"] if rec.get("unadjustedValue") is not None else rec["value"]
    franked = x.get("franked_amount_aud")
    if franked is None and x.get("franked_percent") is not None:
        franked = cash * x["franked_percent"] / 100
    credit = franking_credit(franked or 0.0, corp_tax_rate)
    return {
        "code": rec["code"], "ex_date": rec["date"], "pay_date": rec.get("paymentDate"),
        "cash": cash, "franked": franked, "credit": credit, "gross": cash + credit,
        "special": x.get("special_indicator") == "Y",
        "drp_price": x.get("drp_price_aud"), "drp_discount_pct": x.get("drp_discount_rate"),
        "withholding_pct": x.get("withholding_tax_rate"),
    }

def grossed_up_yield(rows, price, exclude_special=True):
    """Trailing cash and grossed-up yield from normalized rows of the last 12 months."""
    use = [r for r in rows if not (exclude_special and r["special"])]
    cash = sum(r["cash"] for r in use)
    gross = sum(r["gross"] for r in use)
    return cash / price, gross / price

def drp_shares(cash_amount, drp_price):
    """Whole and fractional DRP shares for a cash entitlement; residual handling is plan-specific (user)."""
    q = cash_amount / drp_price
    return int(q), q - int(q)
```

**Pitfalls.** ASX only; buybacks and "other" types are sparse; a non-resident sees withholding rather than
franking benefits; partially franked dividends need the franked amount, not the percentage of a rounded
amount; tax-deferred and conduit-foreign-income parts change the holder's tax treatment — label them.

**Acceptance checks.** A fully franked 0.45 dividend at `t = 0.30` → credit 0.1929, grossed up 0.6429;
a 50%-franked 0.40 dividend → franked 0.20, credit 0.0857; two regular 0.40 dividends (50% franked) plus a
1.00 special on a 10.00 price → cash yield 8.00%, grossed-up yield 9.71% (special excluded); at `t = 0.25`
a 1.00 franked amount carries a 0.3333 credit; 1,000 of entitlement at a 12.34 DRP price → 81 shares plus a
residual.

## Metrics and comparisons

Compare expense ratio, assets, spread/liquidity proxies, tracking difference, concentration and available historical total return on matched dates/currencies. Fund NAV, exchange market price and a benchmark index are distinct. Premium/discount requires compatible timestamped NAV and price; stale NAV should be flagged.

Yield definitions matter: trailing cash yield, indicated yield, distribution rate, yield to maturity and standardized fund yield are not interchangeable. Do not synthesize a regulatory yield from annualized recent payments. Money-market funds may target stable NAV, but do not force all fund histories to 1 based on their names.

Deliver fund comparison tables with field coverage and observation dates. A missing value should not automatically put a fund at the bottom of a ranking or trigger a fabricated estimate.
