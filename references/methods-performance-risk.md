# Methods: returns, performance, risk, allocation and sizing

Formulas, ordered steps, EODHD inputs and acceptance checks for portfolio and strategy analytics built on
EODHD prices. This chapter expands the principles in [portfolio and risk](portfolio-risk.md); it does not
repeat its single-period Brinson-Fachler formulas, FX cross term or duration approximation. Price basis
and units follow [data semantics](data-semantics.md); plan and call costs follow
[plans and limits](plans-limits.md). Holdings, transactions, fees, tax lots, account types, tax rules and
declared trading edges are **user-supplied**: EODHD supplies market data, not account records. All
outputs are analytical results and proposals, not advice or executed orders.

## Contents

1. [EODHD inputs used in this chapter](#1-eodhd-inputs-used-in-this-chapter)
2. [Return conventions](#2-return-conventions)
3. [Aggregation rules](#3-aggregation-rules)
4. [Risk-free rate and benchmarks](#4-risk-free-rate-and-benchmarks)
5. [Flow-adjusted performance: Modified Dietz, TWR, money-weighted, composites](#5-flow-adjusted-performance)
6. [Risk-adjusted ratios and fund evaluation](#6-risk-adjusted-ratios)
7. [Reporting: period table, monthly table, fees, tearsheet, regimes, backtest checklist, drawdown episodes](#7-reporting)
8. [Attribution: contribution, multi-period linking, factor attribution](#8-attribution)
9. [Volatility estimators](#9-volatility-estimators)
10. [VaR and expected shortfall](#10-var-and-expected-shortfall)
11. [Risk profile, correlation and the holdings trigger queue](#11-risk-profile-and-correlation)
12. [Stress testing](#12-stress-testing)
13. [Exposure analysis and long/short hedge ratios](#13-exposure-analysis)
14. [Allocation methods and custom baskets](#14-allocation-methods)
15. [Rebalancing engine, sleeves and held-away assets](#15-rebalancing-engine)
16. [Position sizing, pre-trade rule engine and margin](#16-position-sizing-and-pre-trade-controls)
17. [Recipe: holdings risk report](#17-recipe-holdings-risk-report)
18. [Acceptance fixture summary](#18-acceptance-fixture-summary)

Code snippets use the standard library and numpy only, read no key, and were checked against the
expected values quoted beside them. Read the token from `EODHD_API_TOKEN` in the data adapter, not here.

---

## 1. EODHD inputs used in this chapter

| Input | Endpoint / field | Plan | Calls per request |
|---|---|---|---|
| Daily prices | `/api/eod/{SYM}`: `date, open, high, low, close, adjusted_close, volume`; `period=d`, `w` or `m` | EOD All World, Extended, All-In-One (Free: last 12 months) | 1 (full history) |
| Dividends, splits | `/api/div/{SYM}` (`value`, `unadjustedValue`, `currency`), `/api/splits/{SYM}` | as EOD | 1 |
| Whole-exchange day | `/api/eod-bulk-last-day/{EX}` | as EOD | 100 |
| Technical functions | `/api/technical/{SYM}?function=` `beta` (`code2`, default `GSPC.INDX`), `volatility`, `stddev`, `atr`, `rsi`, `bbands`, `avgvol`, `avgvolccy`, `splitadjusted`; default `period=50` | Extended or All-In-One | 5 |
| Risk-free rate | `/api/ust/bill-rates?filter[year]=YYYY`: `date, tenor (4WK…52WK), discount, coupon` (percent) | all plans incl. Free (beta) | 1 per page |
| Total-return benchmarks | `SPXTR.INDX`, `SP500TR.INDX` / `SP500NTR.INDX` (gross/net), `XNDX.INDX`, `DJITR.INDX` | as EOD | 1 |
| Price-index benchmarks | `GSPC.INDX`, `NDX.INDX`, `DJI.INDX`… (`adjusted_close == close`) | as EOD | 1 |
| ETF benchmarks / proxies | any covered ETF's `adjusted_close` (e.g. `SPY.US`) | as EOD | 1 |
| Classification | `/api/fundamentals/{SYM}?filter=General` (`Sector`, `Industry`) | Fundamentals Feed or All-In-One | 10 |
| ETF look-through | `filter=ETF_Data` (`Sector_Weights`, `World_Regions`, holdings, `Fixed_Income` → `ModifiedDuration.Fund_%`, `NetExpenseRatio` — numbers arrive as strings) | Fundamentals Feed or All-In-One | 10 |
| Market caps | `Highlights.MarketCapitalization` (current); historical market cap (US NYSE/NASDAQ weekly from 2021-07-09, USD) | Fundamentals Feed or All-In-One | 10 |
| Insider activity | `/api/sec-filings/{SYM}/form4` (`transaction_code`, `acquired_or_disposed`, `shares_amount`, `price_per_share`) | Fundamentals Feed or All-In-One ([insider transactions](api/endpoints/insider-transactions.md)); legacy `/api/insider-transactions` | 10 (Form 4); 1 (legacy) |
| News sentiment | `/api/sentiments?s=` (`date, count, normalized` in −1…+1) | all plans | 5 per ticker |
| Holidays/sessions | `/api/v2/exchange-details/{EX}` | Extended or All-In-One | 1 |
| FX | `{PAIR}.FOREX` via `/api/eod` | as EOD | 1 |
| Current US bid/ask | `/api/us-quote-delayed?s=` | plans with Live (delayed) | live pricing per symbol (verify) |
| Identifier mapping | `/api/id-mapping` with `filter[symbol]`, `filter[isin]`, `filter[lei]` or `filter[cik]` (`isin`, `lei`, `cik`, `cusip`, `figi` per listing) | listed for Free in the [integration contract](api-contract.md) | not stated; verify with a probe |
| Event calendars | `/api/calendar/dividends?filter[symbol]=`, `/api/calendar/earnings?symbols=` | All-In-One, Fundamentals Feed, Calendar & News | 1 |
| News | `/api/news?s=&from=&to=` | see [company news](api/endpoints/company-news.md) | 5 + 5 per ticker |
| Reference rates (financing base) | `/api/rates/reference-rates?filter[code]=SOFR` | verify with a probe | verify |

Basis rules used throughout (from [data semantics](data-semantics.md)):

| Purpose | Use | Never |
|---|---|---|
| Total return, risk, correlation, beta | `adjusted_close` | raw `close` across a split/ex-date |
| Range-based volatility, ATR, candles | raw O/H/L scaled by that day's `k = adjusted_close/close` | raw O/H/L across a split |
| Executable levels (entry, stop, order notional) | raw latest price in its quote unit (GBX/ZAC normalized) | adjusted history as a fill price |
| Dollar volume / ADV | split-adjusted price × split-adjusted `volume`, or `avgvolccy` | raw close × split-adjusted volume across a split |
| Cash accounting, lots | raw prices, `unadjustedValue` dividends, split ledger | `adjusted_close` |

At the latest date `k = 1`, so ATR and stops computed on adjusted OHLC are already in current price units.

---

## 2. Return conventions

**Use when:** any return, volatility or ratio is computed.

### 2.1 Definitions

| Quantity | Formula | Notes |
|---|---|---|
| Simple return | `r_t = P_t / P_{t-1} − 1` | additive **across assets** (weighted by start-of-period weights) |
| Log return | `ℓ_t = ln(P_t / P_{t-1}) = ln(1 + r_t)` | additive **across time**, not across assets |
| Cumulative return | `R_{0,T} = Π_t (1 + r_t) − 1 = exp(Σ ℓ_t) − 1` | never `Σ r_t` |
| Excess return | `r_t − rf_t` (same period length) | rf converted to the return frequency (§4) |
| CAGR | `(E_T / E_0)^(1/Y) − 1`, `Y = calendar days / 365.25` or `n_obs / A` | requires `E_0 > 0` and `E_T > 0`; state which `Y` |
| Arithmetic annual mean | `A · mean(r_t)` | used in Sharpe; ≠ CAGR (≈ CAGR + σ²/2) |
| Drawdown | `DD_t = E_t / max_{s≤t} E_s − 1` | `MaxDD = min_t DD_t` (negative number) |
| Time under water | sessions from a peak until `E_t` regains it; open if not regained | report longest and current |

`P` is `adjusted_close` for total return. For a portfolio, `E_t` is NAV after flows are removed (§5).

### 2.2 Annualization factor `A`

| Data calendar | `A` | Volatility | Mean |
|---|---|---|---|
| Exchange sessions (stocks, ETFs, indices) | 252 | `σ_d·√252` | `μ_d·252` |
| Crypto daily (`.CC`, 24/7 UTC) | 365 | `σ_d·√365` | `μ_d·365` |
| Forex daily | sessions actually present (≈ 260); state it | | |
| Weekly / monthly / quarterly | 52 / 12 / 4 | `σ·√A` | `μ·A` |

Use the factor of the calendar the series really follows. A mixed crypto+equity portfolio must be built on
one calendar (usually the equity sessions, with crypto compounded across weekends into the next session)
before annualizing. Do not annualize a period shorter than one year in a report (show cumulative instead).
Square-root-of-time scaling assumes uncorrelated returns; it is a convention, not a fact about the series.

### 2.3 Windows count observations

- A "21-day" or "252-day" window means **21 / 252 observations** of the aligned series, not calendar days.
  State the minimum observations required (e.g. 80% of the window) and emit "insufficient data" below it.
- A missing bar is a missing observation, not a zero return. A holiday is not a zero return.
- Multi-asset statistics use the **intersection** of dates after aligning on each asset's own sessions
  (inner join). For assets on different exchanges with different holidays, either compute the return over
  the gap (compounding across the missing day of one market) or use weekly returns (Friday-to-Friday) for
  correlations; daily cross-time-zone correlations are biased low by asynchronous closes.
- Rolling statistics at date `t` use observations up to and including `t` and are applied from `t+1`.

### 2.4 Pitfalls

- Price indices (`GSPC.INDX`) have `adjusted_close == close`: they omit dividends (§4.2).
- `adjusted_close` is restated over the whole history when a new action arrives; recompute stored return
  series from a fresh full pull, never by appending to an old adjusted series.
- Weekly/monthly bars from `period=w|m`: verify the bar's `date` label convention with a probe; computing
  month-end returns locally from daily `adjusted_close` keeps the month-end date under your control.
- GBX/ZAC quote units cancel in returns but not in values; normalize before any NAV.

### 2.5 Acceptance checks

- `Σ ln(1+r_t)` equals `ln(1 + R_{0,T})` to 1e-12.
- For the same synthetic daily series, `σ_crypto / σ_equity = √365 / √252 = 1.2035`.
- Daily returns `[+10%, −10%]`: sum is 0, compounded is −1%.
- Equity `[100, 120, 90, 130]`: `MaxDD = −25%`, under water for 1 session, recovered at 130.
- A series with a missing session does not contain a 0.0 return for that date.

---

## 3. Aggregation rules

**Use when:** rolling per-security values up to sector, portfolio or period numbers (SQL, BI, reports).

| Measure type | Examples | Across securities | Across time |
|---|---|---|---|
| Additive | volume, cash flows, dividends received, fees, P&L in one currency | sum | sum |
| Semi-additive | position value, NAV, market cap, shares | sum (same currency, same timestamp) | last value (or average balance, labelled) — never sum |
| Non-additive | prices, returns, ratios, yields, volatilities, percentages | weighted formula below | compound / recompute — never sum or average |

Rules:

1. **Returns over time compound:** `Π(1+r)−1`. Log returns may be summed over time, then converted back.
2. **Portfolio return in a period** = `Σ_i w_i,start · r_i` with weights at the **start** of the period
   (after flows). End-of-period weights or average weights give the wrong number.
3. **Ratio of aggregates, not mean of ratios.** Sector P/E = `Σ market cap / Σ earnings` (equivalently the
   cap-weighted harmonic mean of P/E). Exclude or separately flag negative-earnings members and say how.
   Dividend yield of a basket = `Σ dividends(value-weighted) / Σ value`.
4. **Volatility does not aggregate linearly:** `σ_p = √(wᵀΣw)`; a weighted mean of volatilities is an upper
   bound for long-only books (the diversification-ratio numerator, §11).
5. **Averages need a declared weight:** equal, market cap, holding value. Store the weight with the metric.
6. **Round after aggregating.** Keep percent, decimal and basis points distinct (`0.25 pp = 25 bp = 0.0025`).
7. Division by zero or a negative denominator yields a labelled "not meaningful" value, not 0 or ∞.

Metric dictionary row (one per metric): name, numerator, denominator, weight, basis (raw/adjusted),
currency, grain (security×date), period, null policy, annualization factor.

**Acceptance:** two stocks, caps 100 and 300, earnings 10 and 5: mean P/E = (10+60)/2 = 35, aggregate
P/E = 400/15 = 26.67 — the report must show 26.67. A query that sums NAV across dates is rejected in review.

---

## 4. Risk-free rate and benchmarks

### 4.1 Risk-free series from UST bills

**EODHD inputs:** `/api/ust/bill-rates`, one request per year page (1 call); `coupon` is the
coupon-equivalent (bond-equivalent) annual yield in **percent**; use tenor `4WK` or `13WK` and state it.

Steps:

1. Pull each needed year (`filter[year]=YYYY`), follow `links.next` until null, keep one tenor.
2. Convert to a decimal annual rate `y = coupon / 100`.
3. Convert to the return frequency: daily `rf_d = (1 + y)^(1/252) − 1` (or `y/252`; state it), monthly
   `(1 + y)^(1/12) − 1`. Use the rate observed at the **start** of each return period.
4. Align to the asset's sessions; on a session with no bill observation carry the last rate forward and
   flag it as carried (a rate level, not a price observation).
5. Non-USD portfolios: EODHD UST bills are a USD rate. For other currencies use a user-supplied rate or a
   labelled proxy (e.g. a short tenor from the rates endpoints if the user's plan includes it — verify with
   a probe); never apply the USD bill rate to a EUR return without saying so.

Probe the earliest available year before promising long histories (the UST API is beta).

### 4.2 Benchmark basis

| Portfolio return basis | Valid benchmark |
|---|---|
| Total return (from `adjusted_close`) | Total-return index (`SPXTR.INDX`, `SP500TR.INDX`, `XNDX.INDX`, `DJITR.INDX` — probe the first available date) or an ETF's `adjusted_close` (net of fund fees) |
| Net-dividend total return | `SP500NTR.INDX` |
| Price return only | price index (`GSPC.INDX`) |

A total-return portfolio compared against `GSPC.INDX` overstates active return by roughly the index
dividend yield per year. No FTSE indices and no current Russell indices exist on EODHD; use a covered ETF
tracking that index and label it a proxy. The Technical API `beta` defaults to `code2=GSPC.INDX`
(a price index); pass `code2` explicitly.

### 4.3 Blended benchmark

`r_B,t = Σ_k b_k,t · r_k,t`, where `b_k,t` are the policy weights at the start of period t. State the
rebalance rule: **monthly reset** (`b_k,t = b_k` on the first session of each month, drifting with
`r_k` in between) or **daily fixed** (`b_k,t = b_k` every day). They differ; do not mix.

**Acceptance:** a 60/40 blend reset monthly has weights exactly 60/40 on every month's first session and
drifted weights in between; a daily-fixed blend has a constant weight vector.

---

## 5. Flow-adjusted performance

**Use when:** the portfolio has deposits/withdrawals (user-supplied ledger) and the user asks "what did I
earn" (money-weighted) or "how did the manager/strategy do" (time-weighted).

**EODHD inputs:** daily valuation `V_t = Σ_i q_i,t · P_i,t · FX_t + cash_t` from **raw** closes (in
normalized units), quantities from the user's ledger with splits from `/api/splits` applied, and cash that
includes dividends received (`/api/div`, user-confirmed). `adjusted_close` is not a valuation price: use it
only for holding-level returns, and then do not also credit the dividends (double counting).

Flow sign convention: `CF > 0` = external contribution into the portfolio; `CF < 0` = withdrawal.
Dividends, coupons, fees and taxes paid inside the portfolio are **not** external flows.

### 5.1 Modified Dietz (one period, no intra-period valuations)

```
R_MD = (EMV − BMV − Σ CF_i) / (BMV + Σ W_i · CF_i),   W_i = (CD − D_i) / CD
```

`CD` = calendar days in the period; `D_i` = days from period start to flow i. This weight assumes the flow
arrives at the **end** of day `D_i`; for start-of-day flows use `(CD − D_i + 1) / CD`. State which.

Pitfalls: inaccurate when a flow is large relative to BMV (> ~10%) and the market moves within the period:
revalue on the flow date and chain (5.2). If the denominator ≤ 0, the return is not meaningful.

Acceptance: BMV 1,000, contribution 500 at the end of day 15 of 30, EMV 1,600 → `R_MD = 100 / 1,250 = 8.00%`.

### 5.2 Time-weighted return (TWR) with daily valuation

For each session t with valuation `V_t` (after the flow) and flow `CF_t`:

```
end-of-day flow:    r_t = (V_t − CF_t) / V_{t−1} − 1
start-of-day flow:  r_t = V_t / (V_{t−1} + CF_t) − 1
TWR = Π_t (1 + r_t) − 1
```

Without daily valuations, value the portfolio immediately before each external flow, compute each
sub-period return (Modified Dietz within a sub-period is acceptable for small flows), and chain.
A sub-period with `V_{t−1} ≤ 0` breaks the chain: report it, do not skip it.

### 5.3 Money-weighted return (IRR / XIRR)

Solve for `r` in `Σ_i CF_i / (1 + r)^((d_i − d_0)/365) = 0`, investor view: contributions negative,
withdrawals and the ending value positive.

Steps: bracket the root (`r` from −0.9999 to 10), solve by bisection or Brent; count sign changes in the
dated flow sequence — more than one sign change means multiple roots are possible: report "not unique" and
show NPV at candidate rates. No sign change → no IRR. Do not annualize an IRR for a span under one year in a
report (show the period rate).

```python
from datetime import date

def xirr(cashflows, lo=-0.9999, hi=10.0, tol=1e-10):
    """cashflows: [(date, amount)], investor view. Annual rate on Actual/365, or None."""
    d0 = min(d for d, _ in cashflows)
    npv = lambda r: sum(a / (1 + r) ** ((d - d0).days / 365) for d, a in cashflows)
    signs = [a > 0 for _, a in sorted(cashflows) if a != 0]
    if sum(x != y for x, y in zip(signs, signs[1:])) != 1:
        return None  # zero or several sign changes: no unique IRR; report NPV profile instead
    f_lo = npv(lo)
    if f_lo * npv(hi) > 0:
        return None
    while hi - lo > tol:
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if f_lo * f_mid <= 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2
```

### 5.4 Worked TWR vs MWR divergence (acceptance fixture)

Start 100; period 1 return +50% → 150; investor adds 1,000 at the end of period 1 → 1,150; period 2
return −20% → 920.

- TWR = 1.5 × 0.8 − 1 = **+20.0%** (the strategy's result).
- MWR per period: `100x² + 1000x − 920 = 0`, `x = 1 + r` → r = **−15.19%** (the investor's result,
  hurt by adding money before the loss). With yearly dates 2024-01-01, 2025-01-01, 2026-01-01 the
  `xirr` above returns −15.19% (Actual/365, leap day included).

Report both with labels; neither is "the" return.

### 5.5 Composite returns and internal dispersion (GIPS-style calculation)

**Use when:** a firm or adviser groups several discretionary portfolios run to one strategy into a
composite and needs one return per period plus a measure of how far member results spread. The
calculations follow the shape of the GIPS composite rules. Computing them does **not** make a firm or a
report GIPS-compliant: compliance needs firm-wide policies, presentation rules and, usually, verification,
none of which this skill supplies (see [professional workflows](professional-workflows.md#risk-trade-controls-and-audit-trail)).

**EODHD inputs:** nothing beyond §5. Each member's period return (§5.1 or §5.2) and beginning value come
from the user's holdings and transactions, valued with EODHD raw closes and `*.FOREX` closes. Membership
rules are **user-supplied policy**: when a new portfolio joins (e.g. the first full month under
management), when a terminated one leaves (after its last full month), minimum size, and how a large
external flow is treated.

**Method:**

1. **Membership per period.** List the portfolios that meet the user's rules for the whole period and store
   that list with the period. Terminated portfolios stay in past periods; dropping them is survivorship bias.
2. **Member returns** `R_p` for the period, all gross or all net (§7.3), in one currency.
3. **Composite return** (asset-weighted). Let `BMV_p` be the beginning value and `W_i`, `CF_p,i` the
   §5.1 day weights and external flows:
   - beginning-value weights: `R_C = Σ_p BMV_p·R_p / Σ_p BMV_p`;
   - beginning value plus weighted flows: `R_C = Σ_p (BMV_p + Σ_i W_i·CF_p,i)·R_p / Σ_p (BMV_p + Σ_i W_i·CF_p,i)`;
   - aggregate method (alternative): treat all members as one portfolio (sum BMV, EMV and flows), then
     apply §5.1 or §5.2.
   State the method and keep it for the whole history.
4. **Longer periods** compound the monthly composite returns (§2.1); never average them.
5. **Internal dispersion** per calendar year, over members that were in the composite for the **full**
   year: asset-weighted standard deviation `σ_AW = √(Σ_p w_p·(R_p − R_C)²)` with `w_p = BMV_p / Σ BMV`
   (start-of-year values), or the equal-weighted standard deviation (n − 1), or the high/low range. Name the
   measure. Below a user-set member count (e.g. 6), print "not meaningful" and n.
6. Each annual row shows: composite return (gross and net), benchmark return on a matching basis (§4.2),
   number of portfolios, composite assets, firm assets if supplied, and the dispersion measure.

```python
import math

def composite_period(members, weighting="bv_flows"):
    """members: [{"id", "bmv", "r", "flows": [(W_i, CF_i)]}] for ONE period (e.g. a month).
    weighting: "bv" = beginning value; "bv_flows" = beginning value + day-weighted external flows."""
    def base(m):
        return m["bmv"] + (sum(w * cf for w, cf in m.get("flows", ())) if weighting == "bv_flows" else 0.0)
    eligible = [m for m in members if base(m) > 0]
    total = sum(base(m) for m in eligible)
    if not eligible:
        return None
    return sum(base(m) * m["r"] for m in eligible) / total

def internal_dispersion(annual, min_n=6):
    """annual: [(beginning value of the year, annual return)] for portfolios in the composite
    for the FULL year. Returns asset-weighted SD, equal-weighted SD (n-1), range, or not meaningful."""
    n = len(annual)
    if n < min_n:
        return {"status": "not_meaningful", "n": n}
    tot = sum(v for v, _ in annual)
    rc = sum(v * r for v, r in annual) / tot
    aw = math.sqrt(sum(v / tot * (r - rc) ** 2 for v, r in annual))
    mean = sum(r for _, r in annual) / n
    ew = math.sqrt(sum((r - mean) ** 2 for _, r in annual) / (n - 1))
    rs = [r for _, r in annual]
    return {"status": "ok", "n": n, "asset_weighted_sd": aw, "equal_weighted_sd": ew,
            "high": max(rs), "low": min(rs)}
```

**Pitfalls:**

- A member with a non-positive weighting base is excluded from that period, with a note.
- Mixing gross and net member returns, or changing the weighting method mid-history, breaks comparability.
- The 3-year annualized standard deviation of composite and benchmark is a different statistic: §6 on 36
  monthly composite returns.
- Composite returns are only as good as the member valuations: stale prices and missing flows (§11.3 of
  [methods-planning-wealth](methods-planning-wealth.md)) must be resolved before compositing.

**Acceptance checks** (values from running the code above):

- Members A 1,000 at +2%, B 2,000 at +3%, C 7,000 at +1%: beginning-value composite **1.5000%**. With a
  1,000 contribution into C at mid-period (`W = 0.5`), beginning value plus weighted flows gives
  **1.4762%**.
- Monthly composite +1.5%, −0.4%, +2.1% → quarter **3.2170%**.
- Six full-year members (1,000 at 8%, 2,000 at 10%, 1,500 at 6%, 4,000 at 9%, 500 at 12%, 1,000 at 7%):
  `R_C` 8.60%, asset-weighted SD **1.5297%**, equal-weighted SD **2.1602%**, range 6%–12%. The first five
  members only, with a minimum of 6, → `not_meaningful`, n = 5.

---

## 6. Risk-adjusted ratios

**Use when:** a strategy, fund or portfolio needs comparable statistics.

**Inputs:** periodic returns `r_t` (portfolio or strategy, net of costs unless labelled gross), benchmark
`b_t` on the same dates and basis (§4.2), risk-free `rf_t` (§4.1), annualization `A` (§2.2), minimum
acceptable return `MAR` (per period; often `rf_t` or 0 — state it).

| Ratio | Formula (per-period inputs, then annualize) | Undefined when |
|---|---|---|
| Sharpe | `mean(r − rf) / sd(r − rf) · √A` (sample sd, n−1) | `sd ≈ 0` (use a tolerance, e.g. `< 1e-12`) |
| Sortino | `mean(r − MAR) / DD · √A`, `DD = √( (1/N) Σ min(0, r_t − MAR)² )` over **all** N observations | no observation below MAR |
| Calmar | `CAGR / abs(MaxDD)` over a stated window (commonly 36 months) | `MaxDD = 0` |
| Omega(θ) | `Σ max(r_t − θ, 0) / Σ max(θ − r_t, 0)` | no observation below θ |
| Tracking error | `sd(r − b) · √A` | — |
| Information ratio | `mean(r − b) · A / TE` | `TE ≈ 0` |
| Beta | `cov(r − rf, b − rf) / var(b − rf)` | `var = 0` |
| Jensen's alpha | intercept `α` of `r − rf = α + β(b − rf) + ε`, annualized `α·A`; report HAC (Newey-West) t-stat | < ~36 monthly or ~60 daily observations: show "insufficient" |
| Treynor | `mean(r − rf) · A / β` | `β ≈ 0` or negative (not meaningful) |
| M² (Modigliani) | `Sharpe_p · σ_b,ann + rf_ann`; M² excess = `M² − r_b,ann` | Sharpe undefined |
| Up capture | `[Π_{b_m>0}(1+r_m)]^(1/n_up) − 1` ÷ same for `b_m`, on **monthly** returns | no up months |
| Down capture | same over months with `b_m < 0` (lower is better) | no down months |
| Win rate / profit factor | see [paper accounting](paper-accounting.md) | zero trades / zero losses |

Rolling Sharpe: the Sharpe formula over a trailing window of 126 or 252 observations, plotted from the first
full window; mark windows with fewer than the minimum observations as missing.

```python
import math
import numpy as np

def perf_stats(r, rf, b=None, A=252, mar=0.0, eps=1e-12):
    r = np.asarray(r, float); rf = np.broadcast_to(np.asarray(rf, float), r.shape)
    ex = r - rf
    sd = ex.std(ddof=1)
    out = {"sharpe": None if sd < eps else ex.mean() / sd * math.sqrt(A)}
    dd = math.sqrt((np.minimum(r - mar, 0.0) ** 2).mean())
    out["sortino"] = None if dd < eps else (r - mar).mean() / dd * math.sqrt(A)
    loss = np.maximum(mar - r, 0).sum()
    out["omega"] = None if loss < eps else np.maximum(r - mar, 0).sum() / loss
    if b is not None:
        b = np.asarray(b, float); act = r - b; te = act.std(ddof=1)
        out["tracking_error"] = te * math.sqrt(A)
        out["information_ratio"] = None if te < eps else act.mean() / te * math.sqrt(A)
        bex = b - rf; vb = bex.var(ddof=1)
        beta = None if vb < eps else np.cov(ex, bex, ddof=1)[0, 1] / vb
        out["beta"] = beta
        out["treynor"] = None if beta is None or beta <= 0 else ex.mean() * A / beta
        if out["sharpe"] is not None:
            out["m2"] = out["sharpe"] * b.std(ddof=1) * math.sqrt(A) + rf.mean() * A
    return out
```

Pitfalls:

- Sharpe from monthly vs daily returns differs; state the frequency. Inside statistical tests (deflated
  Sharpe, t-stats) use per-period, not annualized, Sharpe — see [validation](research-validation.md).
- A constant-return series has zero variance: report "undefined", never a huge number from floating noise.
- Sortino variants that divide by the count of negative observations only are a different statistic;
  name the convention.
- Beta and capture ratios against a price index understate dividends (§4.2).
- Compute ratios on returns **net** of fees/costs for the headline; show gross separately (§7.3).

Acceptance: monthly returns `[1%, −2%, 3%, −1%, 2%]`, rf = MAR = 0, `A = 12`: Sharpe = 1.002,
Sortino = 2.078, Omega = 2.000. Constant series → Sharpe `None`.

### 6.1 Fund evaluation: breakeven information ratio and closet-index flag

**Use when:** "is this active or factor fund worth its fee compared with a cheap index fund?"

**EODHD inputs:** `adjusted_close` of the fund and of the passive alternative (EOD, 1 call each; fund
prices are already net of the fund's expenses); `ETF_Data.NetExpenseRatio` or
`MutualFund_Data.Expense_Ratio` (decimal strings; Fundamentals Feed or All-In-One, 10 calls); for active
share, the full `ETF_Data::Holdings` of both funds (`Top_10_Holdings` alone is not enough).

**Method:**

1. Fee gap `Δf = ER_active − ER_passive` (annual, decimal).
2. Tracking error `TE` of the fund against the passive alternative on aligned returns (§6), annualized.
3. **Breakeven information ratio** `IR_be = Δf / TE`: the information ratio before the fee gap that the
   manager must sustain just to match the cheap alternative after fees.
4. Compare with the realized information ratio against the passive alternative (§6, from prices, so already
   net of both funds' fees): a realized IR ≤ 0 means the fee was not earned in the sample.
5. **Evidence horizon:** years needed for a t-statistic of 2 at information ratio IR: `Y ≈ (2 / IR)²`.
6. **Closet-index flag** (heuristic, thresholds user-set): R² of the fund's excess returns on the
   benchmark's ≥ 0.95 and TE ≤ 2% → "behaves like the index at an active fee". Active share
   `AS = ½·Σ_i |w_fund,i − w_bench,i|` only when both full holdings lists exist and each covers at least
   95% of its fund's weight; otherwise show "active share unavailable".

**Pitfalls:**

- The expense ratio is already inside the price; never subtract it again (§7.3).
- A factor fund measured against a cap-weighted index has structural tracking error. Use the factor index
  or a covered factor ETF as the passive alternative when one exists, and name it.
- Information ratios from short windows are very noisy; show the window and n beside them.

**Acceptance checks:** ER 0.75% against 0.05% with TE 4% → `IR_be = 0.175`, and `Y ≈ 130.6` years to reach
t = 2 at that IR. A fund whose returns equal the benchmark plus small noise (TE 1%, R² 0.99) is flagged as
closet indexing.

---

## 7. Reporting

### 7.1 Period table

Columns: MTD, QTD, YTD, 1Y, 3Y, 5Y, since inception (SI), each for portfolio (TWR, net), portfolio gross,
benchmark, active (`portfolio − benchmark`, arithmetic, labelled). Periods ≤ 1 year are cumulative;
periods > 1 year are annualized (`(1+R)^(1/Y) − 1`) and labelled "annualized". A period longer than the
available history shows "n/a", not a shorter-period number. Use the last valuation date ≤ report date and
print it.

### 7.2 Monthly return table

Rows = years, columns = Jan…Dec + Year. Each cell compounds daily returns within the calendar month;
Year = `Π(1 + monthly) − 1`. Partial first/last months are marked. Acceptance: compounding the twelve
cells reproduces the Year column to 1e-10, and the Year column compounds to the SI cumulative return.

### 7.3 Gross vs net of fees

Fees are user-supplied (schedule, accrual frequency, billing dates). Net return per period:
`r_net,t = (V_t − CF_t − fee_t) / V_{t−1} − 1` when fees are paid from the portfolio, or
`(1 + r_gross)(1 − f_period) − 1` for a modelled fee rate `f_period = f_annual / periods`. A fee paid by the
client outside the portfolio is not a portfolio flow; model it explicitly if the user wants net-of-all-fees.
Fund expense ratios (`ETF_Data.NetExpenseRatio`) are already inside an ETF's price; do not deduct them again.

### 7.4 Tearsheet layout

1. Header: name, period, currency, basis (TR/price), benchmark symbol and basis, rf tenor, data as-of.
2. Headline table: CAGR, cumulative return, annualized vol, Sharpe, Sortino, MaxDD, Calmar, beta, IR,
   TE — net and gross columns.
3. Equity curve vs benchmark (log scale for > 5 years).
4. Underwater (drawdown) curve; top 5 drawdowns table: peak, trough, recovery dates, depth, length.
5. Rolling 126/252-observation volatility and Sharpe; rolling beta.
6. Monthly return table (§7.2) and annual returns bar chart vs benchmark.
7. Return distribution: histogram, skew, excess kurtosis, worst day/week/month, VaR/ES (§10).
8. Exposure and turnover (strategies): gross/net exposure, turnover, cost drag.
9. Per-regime table (§7.5).
10. Data notes: excluded symbols, missing sessions, proxies used, hypothetical/backtest label.

### 7.5 Per-regime table

Define regimes **before** looking at results and from data available at `t−1` only, e.g. benchmark
63-observation realized volatility percentile (expanding window) split into low/mid/high terciles, or a
trend flag (benchmark above/below its 200-observation average). Columns per regime: share of observations,
annualized return, vol, Sharpe, MaxDD, hit rate. A regime with < 60 observations shows "insufficient".
Acceptance: the regime label at date t is unchanged when data after t is deleted.

### 7.6 Backtest and hypothetical-performance presentation checklist

**Use when:** a backtest, model portfolio or other hypothetical result will be shown to anyone other than
its author (client, investment committee, website, social post). Every item must pass; one failure blocks
the presentation.

1. **Label.** "Hypothetical / backtested results, not actual trading" at the top and beside each chart,
   with the run date and the strategy version (config hash).
2. **Full period first.** Show the full available period. Any highlighted sub-window appears beside it,
   never instead of it. State why the start date was chosen (e.g. first date with data for the universe).
3. **Gross and net.** Both columns (§7.3), with the cost model listed: commission, spread, impact (§16.2),
   borrow and financing (user-supplied, §16.6). Say whether taxes are excluded.
4. **Assumptions list.** Universe and survivorship treatment (delisted included or not), price basis
   (`adjusted_close`), fill rule (signal at close t, fill at open t+1), rebalance schedule, leverage and
   margin terms, cash rate (§4.1), FX conversion.
5. **Benchmark** with symbol and matching basis (§4.2).
6. **Selection disclosure.** Number of variants tried and the selection rule, with the deflated Sharpe ratio
   where available ([research validation](research-validation.md)).
7. **Risk beside return.** MaxDD, worst calendar year and volatility next to CAGR; no annualized figure for
   less than one year.
8. **Data notes.** As-of dates, missing sessions, proxies, excluded symbols.
9. **Licence.** Showing EODHD-derived results to clients or the public needs the appropriate commercial
   licence ([licensing](licensing.md)); a personal plan does not cover it.
10. **Wording.** No "GIPS-compliant", "guaranteed" or regulator-approval language. Jurisdiction-specific
    marketing rules are the user's compliance review, not this checklist.

**Acceptance checks:** a deck that shows a 3-year sub-window without the full-period row fails item 2; a
results table without a net column fails item 3; a public page with no licence reference fails item 9.

### 7.7 Client performance report: goal progress, attribution summary, narrative rules

**Use when:** §7.4 is turned into a periodic client report.

1. **Goal-progress panel.** For a goal `G` at horizon `T` (years) with starting value `V_0` and planned
   end-of-year contributions `C`, solve the required return `r_req` from
   `V_0·(1 + r)^T + C·((1 + r)^T − 1)/r = G` (bisection, as in §5.3). The required path is
   `V_req,t = V_0·(1 + r_req)^t + C·((1 + r_req)^t − 1)/r_req`. Show actual value against the required
   path, the gap, and the return now required from today's value over the remaining years. Goals and
   contributions are user-supplied; return assumptions come from
   [methods-planning-wealth](methods-planning-wealth.md#4-goals-based-planning).
2. **Attribution summary.** Top 3 and bottom 3 contributors (§8.1), linked allocation and selection totals
   (§8.2), and a currency effect line when the portfolio holds foreign assets.
3. **Narrative rules.** Every sentence cites a number that appears in the report's tables, with its period
   and basis. The numbers are recomputed from the same tables before release (deterministic recheck). No
   forecasts. No causal claim about a market move unless a dated source is cited (e.g. a news item from
   `/api/news`), and then as "coincided with", not "caused". Losses are written as plainly as gains.
   Hypothetical sections carry the §7.6 label.

**Acceptance checks:** `V_0` 100,000, `C` 10,000 a year, `G` 200,000 in 5 years → `r_req` **7.289%**;
required path 117,289 / 135,838 / 155,740 / 177,092 / 200,000 at years 1–5. With an actual value of 130,000
after year 2 the gap is −5,838 and the return required over the remaining 3 years is **8.770%**.

### 7.8 Cross-sectional drawdown-episode study

**Use when:** "how deep and how long are corrections in this sector or size tier?"

**EODHD inputs:** `adjusted_close` per listing (EOD, 1 call each, or `eod-bulk-last-day` per date at
100 calls); `General.Sector` (Fundamentals, 10 calls; **current** classification only); size tier from
current `Highlights.MarketCapitalization`, or historical market cap (US NYSE/NASDAQ, weekly from
2021-07-09). Delisted listings only where the symbol lists provide them
([delisted tickers](api/general/delisted-tickers-guide.md)); otherwise label the study survivorship-biased.

**Method:**

1. Per listing, find episodes on `adjusted_close`: from a running peak until the peak is regained; an
   episode counts when its depth reaches `−θ` (θ declared, e.g. 10% or 20%).
2. Per episode: peak, trough and recovery dates, depth, decline sessions (peak → trough) and recovery
   sessions (trough → regained peak). An episode still open at the end of the data is **censored**.
3. Group by sector and size tier: count, median and 75th/90th percentile of depth, decline sessions and
   recovery sessions, plus histograms. Report the share of censored episodes; medians of completed
   recoveries alone understate recovery time.

```python
def drawdown_episodes(closes, theta=0.10):
    """closes: [(date, adjusted_close)] in date order. An episode runs from a running peak until the
    peak is regained; it counts only if its depth reaches -theta. Durations are in sessions."""
    eps, peak_i, trough_i = [], 0, 0
    for i in range(1, len(closes)):
        p = closes[i][1]
        if p >= closes[peak_i][1]:
            depth = closes[trough_i][1] / closes[peak_i][1] - 1
            if depth <= -theta:
                eps.append(_ep(closes, peak_i, trough_i, i, depth))
            peak_i = trough_i = i
        elif p < closes[trough_i][1]:
            trough_i = i
    depth = closes[trough_i][1] / closes[peak_i][1] - 1
    if depth <= -theta:
        eps.append(_ep(closes, peak_i, trough_i, None, depth))        # still open
    return eps

def _ep(c, pk, tr, rec, depth):
    return {"peak": c[pk][0], "trough": c[tr][0], "recovered": c[rec][0] if rec is not None else None,
            "depth": round(depth, 6), "decline_sessions": tr - pk,
            "recovery_sessions": (rec - tr) if rec is not None else None}
```

**Pitfalls:** current sector labels applied to past episodes (state it); price-index series omit dividends,
so use `adjusted_close` of listings or TR indices; thin listings create false episodes from one bad print
(run the quality checks first).

**Acceptance checks:** closes 100, 105, 98, 92, 95, 106, 104, 90, 85, 88, 99, 107, 101, 96 (`d00`–`d13`)
with θ = 10% → three episodes: `d01`→`d03`→`d05` depth −12.381%, 2 + 2 sessions; `d05`→`d08`→`d11` depth
−19.811%, 3 + 3 sessions; `d11`→`d13` depth −10.280%, open (censored).

---

## 8. Attribution

### 8.1 Contribution to return

Single period: `c_i = w_i,start · r_i`; `Σ c_i = r_p`. Over several periods contributions do not add up to
the compounded return; link them with Carino (8.2) using `R_b,t = 0`, so the linked contributions sum to
the compounded portfolio return. Report top and bottom 3 contributors.

### 8.2 Multi-period linking of Brinson effects

Single-period Brinson-Fachler allocation/selection/interaction (see [portfolio-risk](portfolio-risk.md))
sum each period to `a_t = R_p,t − R_b,t`, but their plain sum over t does not equal the compounded active
return `R_p − R_b` (with `R = Π(1+R_t) − 1`). Scale each period's effects:

**Carino (logarithmic):**

```
k   = [ln(1+R_p) − ln(1+R_b)] / (R_p − R_b)        (k = 1/(1+R_p) if R_p = R_b)
k_t = [ln(1+R_p,t) − ln(1+R_b,t)] / (R_p,t − R_b,t) (k_t = 1/(1+R_p,t) if equal)
linked effect = Σ_t (k_t / k) · E_t
```

**Menchero (optimized):**

```
M   = [(R_p − R_b)/T] / [(1+R_p)^(1/T) − (1+R_b)^(1/T)]     (M = (1+R_p)^((T−1)/T) if R_p = R_b)
α_t = [(R_p − R_b) − M·Σ_s a_s] / Σ_s a_s² · a_t
linked effect = Σ_t (M + α_t) · E_t
```

```python
import math
import numpy as np

def carino(Rp_t, Rb_t, effects):
    """effects: T x K single-period effects, each row summing to Rp_t - Rb_t."""
    kf = lambda p, b: 1 / (1 + p) if abs(p - b) < 1e-12 else (math.log1p(p) - math.log1p(b)) / (p - b)
    Rp, Rb = np.prod(1 + np.asarray(Rp_t)) - 1, np.prod(1 + np.asarray(Rb_t)) - 1
    kt = np.array([kf(p, b) for p, b in zip(Rp_t, Rb_t)])
    return (kt / kf(Rp, Rb)) @ np.asarray(effects, float)
```

Acceptance fixture: `R_p,t = [5%, −2%, 3%]`, `R_b,t = [4%, −1%, 1%]`, two effects per period
`[[0.004, 0.006], [−0.006, −0.004], [0.012, 0.008]]`. Naive sum = 0.020000; compounded active
= 0.019974; Carino linked = `[0.009975, 0.009999]` (sum 0.019974); Menchero linked =
`[0.009941, 0.010033]` (sum 0.019974). Residual after linking < 1e-12.

Pitfalls: the effects must be computed with matched sector weights and returns from the same price basis;
cash and unclassified holdings need their own row; sectors come from current `General.Sector`, which is a
current classification applied retrospectively — state it. Geometric (multiplicative) attribution is a
different family; do not mix it with linked arithmetic effects.

### 8.3 Returns-based factor attribution

**Use when:** "how much of my return is market/size/value/sector exposure and how much is residual?"

Academic factor return series are **not** EODHD data. Build factors from EODHD series and label them proxies:

| Factor | Proxy from EODHD (verify each symbol and start date with a probe) |
|---|---|
| Market | TR index (`SPXTR.INDX`) or broad ETF `adjusted_close` minus rf |
| Size | small-cap ETF minus large-cap ETF returns (e.g. `IWM.US − SPY.US`) |
| Value vs growth | value ETF minus growth ETF of the same index family |
| Momentum, quality, low volatility | the corresponding style ETF minus the market proxy |
| Sector | sector ETF minus market proxy |
| Rates / credit | treasury ETF, credit ETF minus treasury ETF |
| Self-built | long-short quantile portfolios from EODHD fundamentals + prices on a dated universe ([ML and factors](ml-factors.md)) |

Steps:

1. Daily or weekly excess returns `y_t = r_p,t − rf_t`; factor returns `f_k,t` on the same dates.
2. OLS `y_t = α + Σ_k β_k f_k,t + ε_t` over ≥ 36 monthly or ≥ 126 daily observations; Newey-West standard
   errors with lag ≥ the return-overlap horizon; check VIF < 5 (long-short proxies of overlapping ETFs are
   collinear).
3. Contribution of factor k over the window: `β_k · Σ_t f_k,t` (arithmetic; link as 8.2 when compounding).
   Residual = `α·T + Σ ε_t`. Annualized alpha = `α·A`; residual volatility = `sd(ε)·√A`; appraisal ratio
   = annualized alpha / residual vol.
4. Rolling 63/126-observation betas reveal style drift (§13.1).
5. Report R², alternative baseline (market-only vs multi-factor), sample size, and that residual return is
   model-specific unexplained return, not proven skill.

Acceptance: synthetic `y = 0.0002 + 1.2·f_1 + noise` recovers β ≈ 1.2 and α ≈ 0.0002 within standard
error; contributions + residual sum to `Σ y_t`.

---

## 9. Volatility estimators

**Use when:** realized volatility, volatility forecasts, vol-target sizing, regime inputs.

### 9.1 Preparing OHLC (EODHD rule)

EOD `open/high/low/close` are raw. Build one consistent price basis before any estimator:

```
k_t = adjusted_close_t / close_t             (skip the row if close_t ≤ 0 or either is missing)
O'_t = k_t·open_t,  H'_t = k_t·high_t,  L'_t = k_t·low_t,  C'_t = adjusted_close_t
```

Within one bar the factor cancels (`H'/L' = H/L`), so Parkinson, Garman-Klass and Rogers-Satchell are
unchanged by scaling. Every term that **crosses days** — close-to-close, Yang-Zhang overnight
`ln(O'_t / C'_{t−1})`, true range with the previous close — is wrong on raw prices across a split or
ex-date. Scale everything anyway so all estimators share one basis. Exclude bars with missing/zero O/H/L,
`H < L`, or O/C outside `[L, H]`, and count exclusions. Intraday bars are unadjusted: never mix them with
adjusted daily bars without the same scaling.

### 9.2 Estimators (per-period variance; annualize with `σ = √(v·A)`)

With `n` bars, `o_t = ln(O'_t/C'_{t−1})`, `c_t = ln(C'_t/O'_t)`, `u_t = ln(H'_t/O'_t)`,
`d_t = ln(L'_t/O'_t)`:

| Estimator | Variance | Uses / caveat |
|---|---|---|
| Close-to-close | `v = Σ (ℓ_t − ℓ̄)² / (n−1)`, `ℓ_t = ln(C'_t/C'_{t−1})` | baseline; noisy for short windows |
| Parkinson | `v = Σ (ln H'_t/L'_t)² / (4·ln2·n)` | ignores overnight gaps and drift → biased low for gappy stocks |
| Garman-Klass | `v = (1/n) Σ [0.5(ln H'/L')² − (2ln2 − 1)(ln C'/O')²]` | ignores overnight gaps; assumes zero drift |
| Rogers-Satchell | `v = (1/n) Σ [ln(H'/C')·ln(H'/O') + ln(L'/C')·ln(L'/O')]` | drift-robust; ignores overnight |
| Yang-Zhang | `v = v_o + κ·v_c + (1−κ)·v_RS`, `v_o = var(o_t)`, `v_c = var(c_t)` (n−1), `κ = 0.34 / (1.34 + (n+1)/(n−1))` | includes overnight; best default for daily equity bars |

```python
import math
import numpy as np

def vol_estimators(O, H, L, C, A=252):
    """Adjusted OHLC arrays of length n+1 (row 0 supplies the first previous close)."""
    O, H, L, C = (np.asarray(x, float) for x in (O, H, L, C))
    o, c = np.log(O[1:] / C[:-1]), np.log(C[1:] / O[1:])
    hl, cc = np.log(H[1:] / L[1:]), np.log(C[1:] / C[:-1])
    n = len(cc)
    rs = (np.log(H[1:] / C[1:]) * np.log(H[1:] / O[1:])
          + np.log(L[1:] / C[1:]) * np.log(L[1:] / O[1:]))
    kappa = 0.34 / (1.34 + (n + 1) / (n - 1))
    v = {"close_to_close": cc.var(ddof=1),
         "parkinson": (hl ** 2).sum() / (4 * math.log(2) * n),
         "garman_klass": (0.5 * hl ** 2 - (2 * math.log(2) - 1) * c ** 2).mean(),
         "rogers_satchell": rs.mean(),
         "yang_zhang": o.var(ddof=1) + kappa * c.var(ddof=1) + (1 - kappa) * rs.mean()}
    return {k: math.sqrt(x * A) for k, x in v.items()}
```

Acceptance: on a synthetic series with a 2:1 split, raw inputs and k-scaled inputs give identical
Parkinson/GK/RS values, while close-to-close and Yang-Zhang on raw inputs jump (in the test fixture,
0.31 → 0.71 annualized) and return to the correct value after scaling. For `n = 20`, `κ = 0.1390`.

### 9.3 EWMA

`σ²_t = λ·σ²_{t−1} + (1 − λ)·ℓ²_{t−1}` (zero-mean log returns), `λ = 0.94` for daily data (state it).
Seed with the sample variance of the first 30 observations and discard that warm-up. Half-life of a shock =
`ln 0.5 / ln λ` = 11.2 observations for 0.94. EWMA covariance uses `ℓ_i·ℓ_j` in place of `ℓ²`.

### 9.4 GARCH(1,1) outline

```
σ²_t = ω + α·ε²_{t−1} + β·σ²_{t−1},   ω > 0, α, β ≥ 0, α + β < 1
long-run variance V_L = ω / (1 − α − β)
h-step forecast E[σ²_{t+h}] = V_L + (α + β)^(h−1)·(σ²_{t+1} − V_L)
shock half-life = ln 0.5 / ln(α + β)
```

Steps: demeaned daily log returns (×100 for numerical stability), Gaussian or Student-t maximum likelihood on
a **training window only** (a GARCH library or a constrained optimizer), check constraints and convergence,
forecast out of sample, compare against EWMA and close-to-close with a variance loss (QLIKE or MSE on
realized squared returns). Persistence `α + β ≥ 0.999` means the model is close to integrated: report it.
The term-structure forecast for horizon H is `Σ_{h=1..H} E[σ²_{t+h}]`, not `H·σ²_{t+1}`.

### 9.5 Other sources and views

- Technical API `function=volatility` returns an annualized historical volatility in **percent** over
  `period` observations (default 50). Its exact annualization factor and sample/population convention:
  compare with your close-to-close on the same window before relying on it.
- Realized volatility from intraday bars (Extended/All-In-One, 5 calls per window): `RV_day = Σ ℓ²_j` over
  regular-session 5-minute bars (filter US to 09:30–16:00 New York); intraday is unadjusted, so never
  span a split day; add the overnight return squared or report session-only RV.
- Volatility cone: for horizons h ∈ {10, 21, 63, 126, 252}, the distribution (min, 25th, median, 75th, max)
  of rolling h-observation close-to-close vol over the history, with the current value marked.

---

## 10. VaR and expected shortfall

**Use when:** "how much could I lose on a bad day/week at X% confidence?"

Convention: loss `L = −r·V` (positive = loss), confidence `α` (0.95, 0.99), horizon `h` sessions. VaR is a
modelled quantile, not a maximum loss.

### 10.1 Historical simulation

1. Portfolio return series from **current** weights applied to the history of asset returns
   (`r_p,t = Σ w_i r_i,t`, aligned dates, ≥ 250 observations for 99%; state the window).
2. `VaR_α = −Q_{1−α}(r_p)·V` (state the quantile interpolation), `ES_α = −mean(r_p | r_p ≤ Q_{1−α})·V`.
3. Assets with shorter history: proxy mapping (§12.2) and a flag, or drop the window start.

### 10.2 Parametric (normal)

`VaR_α = −(μ + z_{1−α}·σ)·V`, `ES_α = −(μ − σ·φ(z_{1−α}) / (1 − α))·V`, with `z_{0.05} = −1.645`,
`z_{0.01} = −2.326`, `σ = √(wᵀΣw)` per period. Often set `μ = 0` for short horizons; say so.

### 10.3 Cornish-Fisher (modified) VaR

With sample skewness `S` and **excess** kurtosis `K` of `r_p`, and `z = z_{1−α}` (negative):

```
z_CF = z + (z² − 1)·S/6 + (z³ − 3z)·K/24 − (2z³ − 5z)·S²/36
VaR_CF = −(μ + z_CF·σ)·V
```

Negative skew and fat tails push `z_CF` further negative. The expansion is unreliable for large `|S|` or
`K` (it can overshoot or become non-monotonic): in a Student-t(4) test fixture with `K ≈ 9.8`,
99% CF VaR was 71k vs historical 41k on 1M. When CF and historical disagree by more than ~25%, report
both and the more conservative, and say why.

### 10.4 Monte Carlo

Simulate `r = μ + Lz` with `L` the Cholesky factor of a (shrunk, §14.2) covariance and `z` i.i.d. normal or
Student-t scaled to unit variance; or block-bootstrap historical return rows (block length ≈ 5–20 sessions)
to keep cross-asset and short-term dependence. For h-day VaR simulate h steps and compound. ≥ 10,000 paths;
report the Monte Carlo standard error of the quantile (repeat with different seeds). Fix and record the seed.

### 10.5 Marginal and component VaR (parametric)

```
VaR_p     = z·σ_p·V,     z = −z_{1−α} > 0,  σ_p = √(wᵀΣw)
marginal_i  = ∂VaR_p/∂w_i = z·(Σw)_i / σ_p · V
component_i = w_i · marginal_i,   Σ_i component_i = VaR_p
```

Report component VaR as a share of total. For historical VaR, component ES can be estimated as
`−mean(w_i r_i,t | r_p,t ≤ Q)·V`, which also sums to ES.

### 10.6 Horizon scaling

`VaR_h ≈ √h·VaR_1` only for i.i.d. zero-mean returns. Prefer direct h-day returns (non-overlapping when
the sample allows; overlapping windows understate uncertainty) or simulation. Never scale 1-day 99% VaR to
one year and present it as a forecast.

### 10.7 Backtest (Kupiec proportion-of-failures)

Count exceptions `x` (days with loss > the VaR forecast made the day before) over `T` days; `p = 1 − α`,
`p̂ = x/T`:

```
LR_POF = −2·ln[(1−p)^(T−x)·p^x] + 2·ln[(1−p̂)^(T−x)·p̂^x]     ~ χ²(1), reject at 5% if LR > 3.841
```

(`0^0 = 1` when `x = 0`.) Fixtures for `T = 250`, `α = 99%` (2.5 expected): `x = 2` → LR = 0.108
(accept); `x = 8` → LR = 7.73 (reject); `x = 0` → LR = 5.03 (reject: VaR too conservative). The
regulatory "traffic light" for 250 days at 99% is 0–4 green, 5–9 yellow, ≥ 10 red. Add an independence
test (Christoffersen) when exceptions cluster. A VaR model is backtested only on out-of-sample forecasts.

### 10.8 Acceptance

- ES ≥ VaR at the same α (losses positive).
- Component VaR sums to total parametric VaR to 1e-9.
- A cash-only portfolio has VaR 0.
- Historical VaR with fewer than `1/(1−α)` × 2 observations is refused ("insufficient sample").

---

## 11. Risk profile and correlation

**Use when:** "how risky is my portfolio", "am I diversified", "what does a 20% market drop do to me?"

### 11.1 Profile statistics

| Statistic | Formula / rule |
|---|---|
| Skewness | `(1/n) Σ (r−r̄)³ / s³` (state population vs adjusted) |
| Excess kurtosis | `(1/n) Σ (r−r̄)⁴ / s⁴ − 3` |
| Jarque-Bera | `n/6 · (S² + K²/4)`; rejects normality for almost any long daily series — use as description |
| Average pairwise correlation | mean of the off-diagonal entries of the correlation matrix (`N(N−1)/2` pairs) |
| Diversification ratio | `DR = Σ w_i σ_i / σ_p` (≥ 1 for long-only; 1 = no diversification) |
| Concentration | `HHI = Σ w_i²`, effective N = `1/HHI`; weights 60/25/15 → 2.247 |
| Worst windows | minimum of rolling compounded returns over 1, 5, 21 observations, with dates |
| Beta-shock estimate | `ΔV ≈ β_p · m · V` for a market move `m` (e.g. −20%) |

The beta-shock estimate is a **linear lower bound on the loss magnitude**: in crashes correlations and betas
rise, so realized losses tend to exceed it. Omit the shock table when no benchmark is stated or fewer than
60 overlapping observations exist, and say why.

### 11.2 Flag list (configurable, leads the report)

Default thresholds (user-overridable, labelled heuristics): single position > 30% of value; average
pairwise correlation > 0.7; annualized vol > 20% (elevated) or > 35% (high); MaxDD worse than −30%;
excess kurtosis > 3 or skew < −1 (fat/left tail); any position with stale or missing price; any proxy used.
End with: "Statistics describe the sample window only; a low value is not a forecast."

### 11.3 Correlation toolkit

- Pearson on returns (never on price levels); Spearman/Kendall for rank dependence and outlier robustness.
- Rolling (63/126 observations) and EWMA correlation `ρ_t = cov_t / (σ_i,t σ_j,t)` from EWMA moments.
- Cross-exchange alignment: inner-join dates; no zero returns for one market's holiday; use weekly returns
  or a one-day-lagged term (`corr(r_i,t, r_j,t) + corr(r_i,t, r_j,t−1)`) for asynchronous closes.
- Stress correlation: correlation over days when the benchmark return is below its 10th percentile, beside
  full-sample correlation.
- Lower-tail co-exceedance: share of days both assets are below their own 5th percentile, vs 0.25% expected
  under independence.
- Absorption ratio: share of total variance explained by the top `k ≈ N/5` eigenvectors of the covariance
  matrix over a rolling window; rising values mean more concentrated common risk.
- Hierarchical clustering on distance `√((1 − ρ)/2)` for a correlation heatmap ordering (same as §14.7).

### 11.4 Holdings trigger catalogue and action queue

**Use when:** an adviser or self-directed investor wants one ranked list of "what needs attention today"
across accounts, instead of separate alerts. Every item is a review prompt; none places or proposes a trade
by itself.

**EODHD inputs and costs:**

| Data | Endpoint | Calls |
|---|---|---|
| Closes, drawdowns, relative strength | `/api/eod/{SYM}` (`adjusted_close`; raw `close` for values) | 1 per symbol |
| Upcoming ex-dates | `/api/calendar/dividends?filter[symbol]=` (or future rows of `/api/div`) | 1 per request |
| Upcoming earnings | `/api/calendar/earnings?symbols=A,B,…` | 1 per request |
| Dividend monitor | `/api/div/{SYM}?fmt=json` + Fundamentals ([technical-market §13](methods-technical-market.md#13-dividend-screens-and-the-dividend-monitor)) | 1 + 10 |
| News volume | `/api/news?s=&from=&to=` | 5 + 5 per ticker |
| Insider sales | `/api/sec-filings/{SYM}/form4` (Fundamentals Feed or All-In-One) | 10 per page |
| Expected session | `/api/v2/exchange-details/{EX}` | 1 per exchange |

**Trigger catalogue** (thresholds are user-set defaults, labelled heuristics):

| Trigger | Rule | Level |
|---|---|---|
| `BAND_DRIFT` | §15.1 combined band breached; hysteresis: open above 5 pp, close below 4 pp | WARN |
| `POSITION_DRAWDOWN` | `adjusted_close` ≤ −15% from its 252-session peak | WARN |
| `SECTOR_DRAWDOWN` | holdings-weighted sector sleeve (§13.2) ≤ −15% from its peak | WARN |
| `REL_DRAWDOWN` | `(1 + R_i,126)/(1 + R_idx,126) − 1 ≤ −20%` against a total-return index on the same basis (§4.2) | REVIEW |
| `LOT_LOSS` | lot unrealized loss ≥ user threshold (harvest candidate, [methods-planning-wealth §9.1](methods-planning-wealth.md#91-candidate-screen)) | INFO |
| `CONCENTRATION` | position or issuer above the §11.2 / §16.4 limit | WARN |
| `EX_DIVIDEND` | held symbol with an ex-date within the next 10 sessions | INFO |
| `EARNINGS` | report date within the next 10 sessions | INFO |
| `DIVIDEND_FLAG` | dividend monitor state CUT or SUSPENSION_SUSPECTED (REVIEW), FREEZE or PAYOUT_STRETCH (WARN) | REVIEW / WARN |
| `NEWS_CLUSTER` | article count over the last 5 sessions ≥ 3 × the trailing 60-session mean of 5-session counts and ≥ 5 articles, or a deduplicated cluster from [app-ai-patterns §10](app-ai-patterns.md#10-news-rag-specifics) | WARN |
| `INSIDER_SELLING` | net open-market sales (Form 4 code `S` minus `P`, `shares_amount × price_per_share`) over 90 days ≥ user threshold; codes `A`/`M`/`F`/`G` excluded | WARN |
| `STALE_PRICE` | no bar for the expected session | WARN |

The last three rows (`REL_DRAWDOWN`, `NEWS_CLUSTER`, `INSIDER_SELLING`) also extend the dividend monitor:
an income holding with a stable dividend can still deserve review when the price lags the index badly, news
volume spikes, or insiders sell.

**Method:**

1. Run each trigger per (account, symbol) on the latest complete session in the exchange's time zone.
2. **Priority score** `S = Σ_k w_k·x_k`, with components shown in the output: severity `x_sev` (REVIEW 1,
   WARN 0.5, INFO 0.2); urgency `x_urg` = 1 for state triggers, `max(0, 1 − days_to_event / horizon)` for
   event triggers (0 once the event has passed); size `x_size = min(1, weight / w_ref)`. Default weights
   0.5 / 0.3 / 0.2, `horizon` 10 days, `w_ref` 10%.
3. **Deduplicate** on (account, symbol, trigger, event date or empty). A repeat hit updates evidence and
   `last_seen` on the open item; it never opens a second item. A rescheduled event date closes the old item
   as "rescheduled" and opens a new one.
4. **Hysteresis** for level triggers (drift, drawdown): open at the fire threshold, close only below the
   clear threshold, so an item does not flap daily.
5. Order by score, then position weight, then symbol (deterministic). Snoozed items stay hidden until their
   snooze date. Each item keeps its evidence rows and data as-of dates.

```python
import datetime as dt

SEVERITY = {"REVIEW": 1.0, "WARN": 0.5, "INFO": 0.2}
DEFAULT_WEIGHTS = {"severity": 0.5, "urgency": 0.3, "size": 0.2}

def score(item, as_of, weights=DEFAULT_WEIGHTS, horizon_days=10, w_ref=0.10):
    """Priority in [0, 1] with visible components. Event triggers get urgency from days to the
    event; state triggers (drift, drawdown) have urgency 1."""
    if item.get("event_date"):
        days = (dt.date.fromisoformat(item["event_date"]) - as_of).days
        urgency = 0.0 if days < 0 else max(0.0, 1 - days / horizon_days)
    else:
        urgency = 1.0
    parts = {"severity": SEVERITY[item["level"]], "urgency": urgency,
             "size": min(1.0, item.get("weight", 0.0) / w_ref)}
    return round(sum(weights[k] * parts[k] for k in weights), 4), parts

def build_queue(raw, open_items, as_of, **kw):
    """raw: today's trigger hits; open_items: {dedup_key: item} from earlier runs.
    Dedup key = (account, symbol, trigger, event_date or ""). A repeat hit updates the open item
    (evidence, as_of) instead of creating a second one; snoozed items stay hidden until snooze_until."""
    queue = dict(open_items)
    for hit in raw:
        key = (hit["account"], hit["symbol"], hit["trigger"], hit.get("event_date") or "")
        prev = queue.get(key, {})
        item = {**prev, **hit, "first_seen": prev.get("first_seen", as_of.isoformat()),
                "last_seen": as_of.isoformat()}
        item["score"], item["parts"] = score(item, as_of, **kw)
        queue[key] = item
    visible = [v for v in queue.values()
               if not v.get("snooze_until") or v["snooze_until"] <= as_of.isoformat()]
    # deterministic order: score desc, then position weight desc, then symbol
    return queue, sorted(visible, key=lambda v: (-v["score"], -v.get("weight", 0), v["symbol"]))

def band_state(drift_abs, was_open, fire=0.05, clear=0.04):
    """Hysteresis: open at |drift| > fire, close only when |drift| < clear."""
    return drift_abs > fire if not was_open else drift_abs >= clear
```

**Pitfalls:**

- Form 4 code `S` includes pre-arranged plan sales; the method cannot tell them apart unless the payload
  carries a plan flag (verify with a probe before relying on one).
- Calendar dates move; keep the dedup key on the event date so a move is visible.
- Missing entitlement (e.g. no Form 4 access) shows "not entitled" on that trigger, not "no trigger".
- Relative drawdown against a price index (`GSPC.INDX`) overstates the holding's lag by the index dividend
  yield; use a TR index or ETF `adjusted_close`.

**Acceptance checks** (as of 2026-10-26, values from the code above): `ABC.US REL_DRAWDOWN` (REVIEW,
weight 4%) **0.88**; `XYZ.US BAND_DRIFT` (WARN, 18%) **0.75**; `MSFT.US EARNINGS` (INFO, 12%, event in 2
days) **0.54**; `MSFT.US EX_DIVIDEND` (INFO, 12%, event in 24 days) **0.30**, in that order. Re-running on
2026-10-27 with the drift hit again leaves 4 items, with `first_seen` 2026-10-26 and `last_seen`
2026-10-27. Hysteresis: drift 5.1% from closed → open; 4.5% while open → stays open; 3.9% → closes; 4.5%
from closed → stays closed.

---

## 12. Stress testing

**Use when:** "what would 2008/2020/2022 do to this portfolio?" or a hypothetical shock.

### 12.1 Historical scenario library (user-adjustable windows)

Windows are approximate peak/trough dates of the US large-cap price index; verify each on `GSPC.INDX`
(and the local market index for non-US books) before use, and store the window with the result.

| Scenario | Start → end | Character |
|---|---|---|
| Black Monday | 1987-10-14 → 1987-10-19 | one-day crash |
| Dot-com bust | 2000-03-24 → 2002-10-09 | long equity bear, tech-heavy |
| Global financial crisis | 2007-10-09 → 2009-03-09 (acute: 2008-09-15 → 2009-03-09) | equity −50%+, credit stress |
| US downgrade / euro stress | 2011-07-22 → 2011-10-03 | correlation spike |
| Taper tantrum | 2013-05-22 → 2013-06-24 | rates up, EM down |
| China devaluation | 2015-08-17 → 2015-08-25 | gap down |
| Brexit vote | 2016-06-23 → 2016-06-27 | GBP shock |
| Q4 2018 | 2018-09-20 → 2018-12-24 | rates + growth scare |
| COVID crash | 2020-02-19 → 2020-03-23 | fastest bear, liquidity |
| 2022 rates shock | 2022-01-03 → 2022-10-12 | stocks and bonds down together |

### 12.2 Replay procedure

1. Current holdings and weights `w_i` (user-supplied), reporting currency.
2. For each scenario window, fetch `adjusted_close` for each holding, the FX pairs (`*.FOREX`) and the
   benchmark (1 call per symbol; full history in one request covers every scenario).
3. Scenario return per asset `R_i = P_i,end / P_i,start − 1` in local currency, then
   `(1 + R_i)(1 + R_FX) − 1` in reporting currency, using FX on the same dates.
4. **Proxy mapping** for holdings without history in the window (IPO later, short history): regress the
   holding's returns on a proxy (local index, sector ETF or a covered ETF) over all overlapping data
   (≥ 126 observations): `r_i = a + β_i·r_proxy + ε`. Scenario return ≈ `β_i·R_proxy` (drop `a`); optionally
   add a residual shock `±z·σ_ε·√(window length)`. Flag the position "proxy" with β, R² and overlap length.
   No proxy available → "not covered", excluded from totals but shown, with its weight.
5. Portfolio scenario P&L = `Σ w_i·R_i·V` (static buy-and-hold weights over the window); also report the
   **path** maximum drawdown inside the window from daily compounding.
6. Output per scenario: P&L and %, benchmark return, top 5 contributors, covered weight / proxied weight /
   uncovered weight, and the dates used.

Delisted constituents of a historical index do not matter here (we replay current holdings), but a holding
that is itself a renamed/reused ticker needs identity checks ([identity](identity.md)).

### 12.3 Hypothetical and factor shocks

| Shock | Computation |
|---|---|
| Equity market −X% | `ΔV_i = β_i·(−X)·V_i` with betas from §13.1 (linear; label it) |
| Factor shocks | `ΔV = V·Σ_i w_i Σ_k β_ik·s_k` for shocks `s_k` to factor proxies (§8.3) |
| Correlation spike | set all off-diagonal correlations to ρ* (e.g. 0.8), `Σ* = D·R*·D`, recompute σ_p and VaR; ensure `R*` is positive semi-definite |
| Volatility spike | multiply σ by m (e.g. 2) and recompute VaR/ES |
| Rates ±Δy | bond ETF: `ΔP/P ≈ −D_mod·Δy + ½·C·Δy²` with `D_mod` from `ETF_Data::Fixed_Income` → `ModifiedDuration.Fund_%` (a string; confirm it is in years with a probe on a known bond ETF, treat `"0"` as missing; convexity user-supplied or omitted); Δy in decimal (100 bp = 0.01) |
| FX ±Y% | apply to each non-reporting-currency position value |
| Liquidity | cost of exiting = `Σ abs(position)·(½·spread_bps + impact_bps)·1e-4`, with impact from §16.2 and a spread multiplier (e.g. ×3) |

### 12.4 Acceptance

- A cash-only portfolio shows zero P&L in every scenario.
- Proxied and uncovered positions appear in the output with flags; their weights add up with covered weight
  to 100%.
- Replaying the benchmark itself returns exactly the benchmark scenario return.

---

## 13. Exposure analysis

### 13.1 Rolling betas and style drift

Rolling OLS of `r_i − rf` on factor excess returns over 63/126/252 observations (daily) or 36 months.
EODHD alternative for single-factor beta: Technical API `function=beta&code2=<benchmark>&period=<n>`
(5 calls per symbol); verify its return basis by comparing with a local estimate. Portfolio beta =
`Σ w_i β_i` (weights at the estimate date). Style drift = change in rolling betas beyond ±2 standard errors.

### 13.2 Sector, region and asset-class exposure

- Single stocks: `General.Sector` / `General.Industry` (10 calls each; current classification only).
- ETFs and funds: look through with `ETF_Data::Sector_Weights` and `World_Regions` (percent strings →
  decimal); exposure = `Σ_f w_f · weight_f,sector`. Report **covered weight** (share of the portfolio with
  classification data) and leave the remainder as "unclassified", not redistributed.
- Asset-class buckets come from instrument type plus user mapping; label user-mapped rows.
- **Fund cost and look-through audit.** Weighted expense ratio `ER_p = Σ_f w_f·ER_f` over fund holdings
  (`ETF_Data.NetExpenseRatio` or `MutualFund_Data.Expense_Ratio`, decimal strings; single stocks 0), with
  covered weight reported. Asset-class look-through from `ETF_Data::Asset_Allocation`: per class (`Cash`,
  `Stock US`, `Stock non-US`, `Bond`, `Other`, `NotClassified`) the `Net_Assets_%` string (percent),
  exposure `= Σ_f w_f·Net_Assets_%_f / 100`; `Long_%` and `Short_%` show funds that hold shorts.
- **ETF screen rules** (user thresholds, labelled): `NetExpenseRatio` ≤ x; `TotalAssets` ≥ y (string, fund
  currency); top-10 concentration `Σ Top_10_Holdings.Assets_%` ≤ z; holdings overlap between two funds
  flagged when they share top-10 keys (`{CODE}.{EXCHANGE}`) with combined weight above a threshold;
  `Holdings_Count` ≥ n for diversification (a low count with a broad `Index_Name` signals sampling or a
  partial holdings list); `Index_Name` filter or match for "tracks index X" screens (string match, case-
  insensitive; empty for active funds — report as "no index", not as a failure).
- Acceptance: funds at 60% (ER 0.0003) and 40% (ER 0.0050) → portfolio ER **0.218%**; a stock-only
  portfolio shows ER 0 with 100% covered weight.

### 13.3 PCA with a random-matrix noise threshold

1. Standardized returns `Z` (T × N, aligned, no filled values) over a training window.
2. Eigen-decompose the correlation matrix.
3. Marchenko-Pastur upper edge for pure noise: `λ+ = (1 + √(N/T))²` (unit-variance case). Keep
   eigenvalues above `λ+` as signal; the rest are indistinguishable from noise.
4. Refit walk-forward; a component counts as a factor only if it is stable across windows and, for return
   forecasting, priced out of sample (IC or premium per [ML and factors](ml-factors.md)).

Acceptance: synthetic one-factor returns (N = 50, T = 1000) give exactly one eigenvalue above
`λ+ = 1.497`. Pure noise gives none (up to edge fluctuation).

### 13.4 Long/short hedge ratios (dollar-neutral, beta-neutral, sector-neutral)

**Use when:** "how much index ETF do I short to neutralize this book?" or "is my long/short book really
market-neutral?" The output is a proposed hedge notional, not an order.

**EODHD inputs:** betas from §13.1 (local OLS on `adjusted_close` returns) or the Technical API `beta`
with `code2` set explicitly (5 calls per symbol); the hedge instrument's beta against the **same**
benchmark (1.0 when the hedge is the benchmark ETF itself); sector ETFs for sector-neutral hedges; raw
latest prices and `*.FOREX` for position values in one currency.

**Method** (signed values `V_i`, long > 0, short < 0; hedge beta `β_h`):

1. Dollar-neutral: `H = −Σ_i V_i`. Net dollars become 0; beta exposure remains.
2. Beta-neutral: `H = −Σ_i β_i·V_i / β_h`. Net beta dollars become 0; net dollars remain.
3. Sector-neutral: for each sector s with a covered sector ETF `h_s`, `H_s = −Σ_{i∈s} β_i,s·V_i / β_h_s,s`,
   with betas estimated against that sector ETF. Holdings without a sector ETF stay in the residual.
4. Residual report: gross `Σ|V_i| + |H|`, net dollars `Σ V_i + H`, net beta dollars `Σ β_i·V_i + β_h·H`,
   and the uncertainty of the beta dollars `√(Σ_i (SE(β_i)·V_i)²)` (ignores covariance between estimates).
5. Recompute when betas are re-estimated or positions change; report drift of net beta dollars between
   rebalances.

```python
import math

def hedge_notional(positions, mode="beta", beta_hedge=1.0):
    """positions: [{"symbol", "value" (signed, long > 0), "beta", "beta_se"}] in one currency,
    betas against the same benchmark as beta_hedge. Returns the hedge notional H (negative = short
    the hedge) and the residual exposure report."""
    gross = sum(abs(p["value"]) for p in positions)
    net = sum(p["value"] for p in positions)
    beta_dollars = sum(p["beta"] * p["value"] for p in positions)
    if mode == "dollar":
        H = -net
    elif mode == "beta":
        if abs(beta_hedge) < 1e-9:
            raise ValueError("hedge beta ~ 0: beta-neutral hedge undefined")
        H = -beta_dollars / beta_hedge
    else:
        raise ValueError(mode)
    se = math.sqrt(sum((p.get("beta_se", 0.0) * p["value"]) ** 2 for p in positions))
    return {"hedge_notional": H, "gross": gross + abs(H), "net_dollars": net + H,
            "net_beta_dollars": beta_dollars + beta_hedge * H,
            "beta_dollars_se": se}   # SE ignores covariance between beta estimates
```

**Pitfalls:**

- Betas against a price index and a hedge in a TR ETF mix bases; use one benchmark for every beta.
- Beta estimates are noisy: in the fixture below the beta-dollar standard error (131,149) is almost half
  the hedge (290,000). Show it, and do not present "beta-neutral" as "riskless".
- Dollar-neutral is not market-neutral when long and short betas differ.
- Short positions need borrow availability and fees, which EODHD does not provide (user-supplied).

**Acceptance checks:** longs A 600,000 (β 1.2, SE 0.10) and B 400,000 (β 0.8, SE 0.15), short C −500,000
(β 1.5, SE 0.20), hedge β 1.0. Dollar-neutral → H = −500,000, net beta dollars −210,000. Beta-neutral → H =
−290,000, net dollars +210,000, net beta dollars 0, beta-dollar SE 131,149. With hedge β 1.1 → H =
−263,636.

---

## 14. Allocation methods

**Use when:** "how much of each asset should I hold?" Outputs are research weights, not instructions.

### 14.1 Common preparation

1. Universe and constraints (user): long-only or not, bounds `l_i ≤ w_i ≤ u_i`, budget `Σ w_i = 1`,
   group limits, turnover cap.
2. Aligned daily `adjusted_close` returns in one currency; common-date policy: inner join; drop assets
   failing a minimum history (e.g. 252 observations) and report them.
3. Estimation window `T` (e.g. 252 or 504 observations) and `N` assets. If `T < 2N` print: "Covariance
   estimated from T observations for N assets — estimation error is large; shrinkage applied." If `T ≤ N`,
   the sample covariance is singular: shrinkage is mandatory.
4. Annualize Σ by `A` only for reporting; optimizers are scale-invariant in Σ except where μ enters.

### 14.2 Ledoit-Wolf shrinkage (to scaled identity)

```
S = (1/T) X_cᵀ X_c       (X_c demeaned returns)
m = tr(S)/N,  d² = ‖S − mI‖²_F / N,  b̄² = (1/T²) Σ_t ‖x_t x_tᵀ − S‖²_F / N,  b² = min(b̄², d²)
δ = b²/d²,   Σ_LW = δ·m·I + (1 − δ)·S
```

```python
import numpy as np

def ledoit_wolf(X):
    X = np.asarray(X, float); T, N = X.shape
    Xc = X - X.mean(axis=0)
    S = Xc.T @ Xc / T
    m = np.trace(S) / N
    d2 = ((S - m * np.eye(N)) ** 2).sum() / N
    b2 = min(sum(((np.outer(x, x) - S) ** 2).sum() for x in Xc) / N / T ** 2, d2)
    delta = 0.0 if d2 == 0 else b2 / d2
    return delta * m * np.eye(N) + (1 - delta) * S, delta
```

Report δ. Fixtures: i.i.d. equal-variance noise (target is the truth) → δ near 1; strong one-factor data
with T = 1000, N = 10 → δ ≈ 0.003. A constant-correlation target is a common alternative for equities.

### 14.3 Minimum variance

Unconstrained (budget only): `w = Σ⁻¹1 / (1ᵀΣ⁻¹1)`. Long-only or bounded: quadratic program
`min wᵀΣw` s.t. constraints, with a QP solver (any ordinary optimization library); check solver status,
feasibility, `Σ w = 1` and bounds to 1e-8. Never renormalize a failed solve.
Acceptance: in sample, min-variance volatility ≤ equal-weight volatility (fixture: 8.67% vs 13.00%).

### 14.4 Mean-variance

`max_w wᵀμ − (λ/2)·wᵀΣw` s.t. constraints; budget-only closed form
`w = (1/λ)Σ⁻¹(μ − γ1)`, `γ` chosen so `Σ w = 1`. Sample means are noisy forecasts: use views
(§14.5), shrink μ toward a common value, or report the efficient frontier as sensitivity, never as a
forecast. Small changes in μ cause large weight changes; show that sensitivity.

### 14.5 Black-Litterman

```
Π = δ·Σ·w_mkt                      (implied equilibrium excess returns)
μ_BL = [(τΣ)⁻¹ + PᵀΩ⁻¹P]⁻¹ [(τΣ)⁻¹Π + PᵀΩ⁻¹Q]
Σ_BL = Σ + [(τΣ)⁻¹ + PᵀΩ⁻¹P]⁻¹
```

`w_mkt`: market-cap weights from `Highlights.MarketCapitalization` (current; mind listing currency) or
user-supplied asset-class weights. `δ` = risk aversion, `(E[r_m] − rf)/σ_m²`, user-declared (often 2.5–3).
`τ` ≈ 0.025–0.05 or `1/T`. Views `P` (K × N), `Q` (K), uncertainty `Ω = diag(P·τΣ·Pᵀ)` by default or from
declared confidence. With no views, `μ_BL = Π` and the optimizer returns `w_mkt` — a fixture.

### 14.6 Equal risk contribution (ERC)

Target: `RC_i = w_i(Σw)_i = σ_p²/N` (or budgets `b_i`). Solve the convex form
`min ½ yᵀΣy − Σ b_i ln y_i`, `y > 0`, then `w = y / Σy`, by cyclic coordinate updates:

```python
import math
import numpy as np

def erc(cov, budget=None, tol=1e-10, max_iter=10000):
    cov = np.asarray(cov, float); n = len(cov)
    b = np.full(n, 1 / n) if budget is None else np.asarray(budget, float)
    y = 1 / np.sqrt(np.diag(cov))
    for _ in range(max_iter):
        y_old = y.copy()
        for i in range(n):
            c = cov[i] @ y - cov[i, i] * y[i]
            y[i] = (-c + math.sqrt(c * c + 4 * cov[i, i] * b[i])) / (2 * cov[i, i])
        if np.abs(y - y_old).max() < tol:
            w = y / y.sum()
            return w, w * (cov @ w) / (w @ cov @ w)   # weights, risk-contribution shares
    raise RuntimeError("ERC did not converge")
```

Acceptance: contribution shares equal `b_i` within 1e-8; with a diagonal Σ, ERC equals inverse-volatility
weights.

### 14.7 Hierarchical risk parity (HRP)

1. Correlation `ρ` → distance `d_ij = √((1 − ρ_ij)/2)`.
2. Distance between assets' distance vectors `d̃_ij = ‖d_·i − d_·j‖₂`; single-linkage hierarchical clustering
   on `d̃` (a standard hierarchical-clustering routine).
3. Quasi-diagonalize: order assets by the dendrogram leaves.
4. Recursive bisection: start with all assets weight 1; split the ordered list in halves; for each half
   compute the inverse-variance portfolio variance `V = w_ivpᵀ Σ_sub w_ivp` with `w_ivp ∝ 1/diag(Σ_sub)`;
   allocate `α = 1 − V_L/(V_L + V_R)` to the left half and `1 − α` to the right; recurse until single
   assets.

No matrix inversion; robust when `T < N`. Acceptance: with diagonal Σ, HRP equals inverse-variance weights
(fixture variances 0.04, 0.09, 0.01 → 0.1837, 0.0816, 0.7347).

### 14.8 Other baselines

Equal weight; inverse volatility `w_i ∝ 1/σ_i`; maximum diversification (maximize DR, §11.1, via a solver).

### 14.9 Walk-forward evaluation and "no edge"

1. Fit on `T_fit` observations (e.g. 252), hold `T_hold` (e.g. 21); weights drift with returns during the
   hold; rebalance at the next fit date.
2. Charge costs: `cost_t = Σ_i |w_i,target − w_i,drifted|·c_bps·1e-4` per rebalance (cost ladder 5/10/25 bp).
3. Run equal weight on the **same** rebalance dates and costs.
4. Report net CAGR, vol, Sharpe, MaxDD, turnover for both, the Sharpe difference with a block-bootstrap
   95% interval, and sensitivity to `T_fit`, shrinkage and constraints.
5. If the interval includes zero, write plainly: **"The optimized allocation shows no reliable edge over
   equal weight in this sample."** Do not hide it behind a better-looking in-sample frontier.

Outputs per method: weights, risk-contribution shares, σ_p, effective N, turnover, solver status.

### 14.10 Custom basket or theme index

**Use when:** "build me an index of these 15 AI stocks", "equal-weight vs cap-weight version of my theme",
"cap each name at 10%".

**EODHD inputs:** `adjusted_close` for returns (EOD, 1 call per member); weights from current
`Highlights.MarketCapitalization` (Fundamentals, 10 calls) or US historical market cap (NYSE/NASDAQ,
weekly from 2021-07-09); revenue or other fundamentals from `Financials` for fundamental weights;
volatility from §9 for inverse-volatility weights. Membership lists are user-supplied.

**Method:**

1. **Raw scores per rebalance date:** equal = 1; cap = market cap; fundamental = e.g. trailing revenue;
   inverse-vol = `1/σ_i` over a stated window ending at the rebalance date.
2. **Normalize and cap:** `w_i = score_i / Σ score`; any weight above cap `c` is set to `c` and the excess
   is spread pro rata over the uncapped names, repeated until no weight exceeds `c`. Infeasible when
   `n·c < 1`.
3. **Rebalance schedule:** weights are set at the close of the rebalance date (e.g. third Friday of each
   quarter) and apply from the next session.
4. **Index level:** `I_t = I_{t−1}·(1 + Σ_i w_i,t−1·r_i,t)`, where weights drift between rebalances,
   `w_i,t = w_i,t−1·(1 + r_i,t)/(1 + r_p,t)`. On a rebalance date charge `turnover·cost_bps·1e-4`, with
   `turnover = Σ_i |w_new,i − w_drifted,i|`.
5. Report the level series, weights at each rebalance, turnover, and members added or removed.

```python
def capped_weights(raw, cap, tol=1e-12, max_iter=100):
    """raw: {symbol: positive score} (market cap, revenue, 1/vol, or 1 for equal weight).
    Normalize, cap every weight at `cap`, redistribute the excess pro rata over uncapped names."""
    if cap * len(raw) < 1 - tol:
        raise ValueError("infeasible: n * cap < 1")
    tot = sum(raw.values())
    w = {k: v / tot for k, v in raw.items()}
    capped = set()
    for _ in range(max_iter):
        over = {k for k, v in w.items() if v > cap + tol}
        if not over:
            return w
        capped |= over
        excess = sum(w[k] - cap for k in over)
        for k in over:
            w[k] = cap
        free = {k: w[k] for k in w if k not in capped}
        ftot = sum(free.values())
        for k, v in free.items():
            w[k] = v + excess * v / ftot
    raise RuntimeError("cap redistribution did not converge")

def index_levels(returns, rebalance_weights, base=100.0, cost_bps=0.0):
    """returns: [(date, {sym: simple return})] in date order (adjusted_close returns).
    rebalance_weights: {date: {sym: w}} fixed at that date's CLOSE, applied from the next session.
    Weights drift with returns between rebalances; turnover cost is charged on the rebalance date."""
    level, w, out = base, None, []
    for d, r in returns:
        if w is not None:
            port = sum(w[s] * r[s] for s in w)
            level *= 1 + port
            w = {s: w[s] * (1 + r[s]) / (1 + port) for s in w}   # drifted weights
        if d in rebalance_weights:
            new = rebalance_weights[d]
            turnover = sum(abs(new.get(s, 0) - (w or {}).get(s, 0)) for s in set(new) | set(w or {}))
            if w is not None:
                level *= 1 - turnover * cost_bps * 1e-4
            w = dict(new)
        out.append((d, level))
    return out
```

**Pitfalls:**

- **Look-ahead:** current market caps used for past rebalances weight the winners more heavily. Outside
  the US historical market-cap window, label cap-weighted backtests "current-cap weights".
- **Survivorship:** a theme list drawn up today excludes names that failed; say so.
- Returns from `adjusted_close` give a total-return index; a price-only index needs split-only prices
  ([data semantics](data-semantics.md)).

**Acceptance checks:** caps 50/30/10/5/5 with `c` = 25% → weights **25 / 25 / 25 / 12.5 / 12.5%** (the
third name reaches the cap only after redistribution). Inverse-vol with σ 20%/40%/25% → 43.48 / 21.74 /
34.78%. Two members at 50/50 with returns d1 (+10%, −5%), d2 (−2%, +4%), d3 (+1%, +1%) and a rebalance at
the d2 close → levels 100, 102.5, 103.3, 104.333; with 10 bp cost on the d2 rebalance, 103.2955 on d2 and
104.3285 on d3.

---

## 15. Rebalancing engine

**Use when:** "which trades bring me back to target?" Outputs are **proposed** trades.

**Inputs:** user holdings per account (quantity, account type, lots with cost and date), targets `w*_i`,
bands, contribution/withdrawal amount, min trade, lot size, tax rules and account-eligibility rules
(user-supplied). EODHD: latest raw close per holding (normalize GBX/ZAC), FX for non-reporting currencies.

### 15.1 Drift and bands

```
V = Σ_i v_i + cash,  w_i = v_i / V,  drift_i = w_i − w*_i
absolute band:  |drift_i| > B_abs           (e.g. 0.05 = 5 percentage points)
relative band:  |drift_i| / w*_i > B_rel    (e.g. 0.25 = 25% of target)
combined (common): trigger if |drift_i| > min(B_abs, B_rel · w*_i)
```

Trade size to target `t_i = (w*_i − w_i)·V`; to band edge `t_i = (w*_i ± band_i − w_i)·V` (smaller turnover).
State which.

### 15.2 Ordering

1. **Cash flows first.** Contribution `C`: deficits `d_i = max(0, w*_i(V + C) − v_i)`; if `Σd ≥ C`
   allocate `C·d_i/Σd`; otherwise fill all deficits and spread the remainder by `w*`. Withdrawals mirror this
   on overweights. Only then check bands again; often no sale is needed.
2. **Tax-aware sales** (taxable accounts, user lots and rules): prefer selling in tax-advantaged accounts;
   in taxable accounts sell loss lots first, then long-term lots with the smallest gain per unit, avoid
   short-term gains unless the drift breach exceeds a user threshold; check the user's wash-sale window
   across **all** supplied accounts before proposing a loss sale plus repurchase. "Substantially identical"
   is a user/advisor judgement.
3. **Eligibility:** never place a security in an account that cannot hold it (user rules).
4. **Rounding:** whole shares or lots unless fractional is allowed; drop trades below the minimum notional;
   recompute weights after rounding.

### 15.3 Band-policy backtest

On EODHD `adjusted_close` returns of the target assets: compare calendar (monthly/quarterly/annual) vs bands
(e.g. 3/5/10 pp, and 5/25) over the same period. Metrics: tracking error vs a continuously-rebalanced
target portfolio, turnover, number of trades, cost at a stated bp level, final drift distribution. Taxes
are excluded unless the user supplies lots and rates; say so.

### 15.4 Output and acceptance

Drift table (target, current, drift, band, breach flag) and a trade list (account, symbol, side, quantity,
price used and its date, notional, reason, tax note) labelled **proposed, not executed**.
Acceptance: after proposed trades, weights sum to 1 and lie within bands (allowing rounding); contribution
`C = 100` into values [700, 300] with target 60/40 buys only the underweight (0, 100); `C = 1,000` →
(500, 500); no account receives an ineligible security.

### 15.5 Model sleeves, cash buffer and held-away assets

**Use when:** an account follows several model sleeves (unified managed account) or a household holds
assets at another custodian that should count toward the allocation.

**Inputs:** sleeve weights `W_s` and in-sleeve targets `w*_i|s` (user); cash-buffer target `b`; held-away
positions with identifiers (ISIN, CUSIP, ticker). EODHD: `/api/id-mapping` to resolve identifiers to
listings (listed for Free in the [integration contract](api-contract.md); call cost not stated — verify
with a probe), latest raw closes, `*.FOREX`.

**Method:**

1. Account target per security: `w*_i = (1 − b)·Σ_s W_s·w*_i|s`; the cash target is `b`. A security held in
   two sleeves gets the sum.
2. Drift and trades follow §15.1–§15.2 on the rolled-up targets; report drift per sleeve too
   (`Σ_{i∈s} w_i` vs `(1 − b)·W_s`).
3. **Held-away assets:** resolve each identifier to an EODHD listing and value it with the raw close. An
   unresolved or unpriced position is flagged "unpriced", shown with its quantity, and excluded from the
   drift base, never valued at zero or at cost silently. Held-away positions count toward household
   allocation only when the user says so, and no trades are proposed in held-away accounts.

**Acceptance checks:** sleeves Core 70% (VTI 60%, BND 40%) and Satellite 30% (QQQ 100%) with `b` = 2% →
targets VTI 41.16%, BND 27.44%, QQQ 29.40%, cash 2.00% (sum 100%). An unresolved CUSIP appears in the
output as unpriced and the drift base excludes it.

---

## 16. Position sizing and pre-trade controls

**Use when:** "how many shares?" and "is new risk allowed today?" Output is a **paper intent or a refusal**,
never a live order.

### 16.1 Sizing formulas

| Method | Formula | Inputs |
|---|---|---|
| Fixed fractional (risk budget) | `shares = ⌊E·f / (entry − stop)⌋` (long) | equity E, risk fraction f (e.g. 0.5–1%), raw entry and stop |
| ATR stop | `stop = entry − m·ATR_n` (m scenarios 1.5/2/3) | ATR on k-scaled OHLC (§9.1), Wilder n = 14 |
| Volatility target | `w = min(σ_target / σ_i, w_max)`; portfolio: scale `σ_target/σ_p` | σ from `adjusted_close`, stated window |
| Kelly (binary) | `f* = p − (1 − p)/b` | **user-declared** win probability p and payoff ratio b |
| Kelly (continuous) | `f* = (μ − rf)/σ²` | **user-declared** μ; σ from data |
| Capped Kelly | `f = min(c·f*, f_cap)`, `c ≤ 0.5` (default 0.25), `f* ≤ 0 → no position` | haircut p to its lower confidence bound (Wilson) when p comes from a sample of n trades |

Kelly is computed only from an edge the user declares; never infer p or μ from a backtest silently. Echo the
declaration in the output.

```python
def capped_kelly(p=None, b=None, c=0.25, f_cap=0.25):
    """p: declared win probability; b: declared average win / average loss."""
    if p is None or b is None or b <= 0 or not 0 < p < 1:
        return {"status": "refused", "reason": "edge_not_declared"}
    f_star = p - (1 - p) / b
    if f_star <= 0:
        return {"status": "refused", "reason": "no_positive_edge", "kelly": f_star}
    return {"status": "ok", "kelly": f_star, "fraction": min(c * f_star, f_cap),
            "declared": {"p": p, "b": b}}
```

Fixture: p = 0.55, b = 1.0 → f* = 0.10, fraction 0.025; p = 0.45, b = 1.0 → refused `no_positive_edge`.

**Kelly growth function.** The Kelly fraction maximizes expected log growth; the curve around it shows why a
fraction of Kelly is the usual choice.

- Binary bet (win `b·f` with probability p, lose `f`): `g(f) = p·ln(1 + b·f) + (1 − p)·ln(1 − f)`, defined
  for `0 ≤ f < 1`, maximized at `f* = p − (1 − p)/b`.
- Continuous (constant fraction f of equity in an asset with arithmetic mean μ and volatility σ, rest at
  rf): `g(f) = rf + f·(μ − rf) − ½·f²·σ²`, maximized at `f* = (μ − rf)/σ²` with
  `g(f*) − rf = (μ − rf)²/(2σ²)`.
- Half Kelly keeps about 75% of the maximum excess growth with half the volatility; `2·f*` brings excess
  growth back to about zero; above it growth is negative. Because μ and p are uncertain, an overestimated
  edge pushes the "Kelly" bet into the over-betting zone — the reason for the cap `c ≤ 0.5`.

```python
import math

def growth_binary(f, p, b):
    """Expected log growth per bet: win b*f with prob p, lose f otherwise. Needs 0 <= f < 1."""
    return p * math.log1p(b * f) + (1 - p) * math.log1p(-f)

def growth_continuous(f, mu, sigma, rf=0.0):
    """Expected log growth per year of a constant fraction f in an asset with arithmetic mean mu."""
    return rf + f * (mu - rf) - 0.5 * f * f * sigma * sigma
```

Fixtures (from the code): p = 0.55, b = 1 → `g(f*)` = 0.0050084 per bet; `g(f*/2)` = 0.0037526 (74.9% of
the maximum); `g(2f*)` = −0.000138. Continuous μ = 8%, rf = 2%, σ = 20% → `f*` = 1.5, maximum excess growth
4.5% a year, half Kelly 3.375% (75%), `2f*` → 0.

**Per-position VaR budget.** With a daily VaR budget `B` (fraction of equity E) per position, confidence
quantile `z` and daily volatility `σ_d`, the position cap is `V_i ≤ B·E / (z·σ_d·√h)` for horizon h days
(parametric, §10.2). Fixture: E = 1,000,000, B = 0.2%, z = 2.326, σ_d = 2%, h = 1 → cap 42,992.

### 16.2 Liquidity and cost caps

- `ADV$ = mean over 20 sessions of (price × volume)` on one split basis: Technical API
  `function=avgvolccy&period=20` (5 calls) or local split-adjusted price × split-adjusted volume.
- Participation `= order notional / ADV$`; fail above the cap (default 10%, user-set). Days to trade at
  cap `= notional / (cap·ADV$)`. No volume data (indices, forex) → skip the check and say so.
- Cost estimate in bp: `½·spread_bps + impact_bps`, `impact_bps = η·σ_daily·√(Q/ADV)·1e4` with η an
  explicit assumption (e.g. 0.5–1). Spread: current US bid/ask from `us-quote-delayed`, otherwise a user
  assumption; EOD has no historical quotes. Label "estimate".
- Stop distance below ~1 daily ATR → warning (stop likely inside normal noise).

### 16.3 Portfolio controls

- **Portfolio heat** = `Σ_open (entry − stop)·shares / E`; refuse new risk above the cap (user, e.g. 6%).
- **Loss limits:** daily/weekly/monthly P&L (realized + marked) vs equity at the period start, periods in
  the **exchange time zone**; breach → no new entries until the next period.
- **Drawdown tiers:** e.g. −5% from equity peak → halve new risk; −10% → no new entries; resume after a
  stated recovery (e.g. new equity high or N sessions). All thresholds user-set.
- **Losing-streak cooldown:** after k consecutive losing trades, pause new entries for a stated period.
- A halt blocks new orders and keeps state; it never liquidates positions.

### 16.4 Pre-trade checklist (all must pass) and rule engine

1. Price fresh (observation date = expected session; not stale/carried).
2. Plan present: entry, stop, target or time exit, horizon.
3. Size computed and ≤ every cap (risk, weight, sector, vol target, ADV, cash).
4. Actual risk at size ≤ planned risk.
5. Heat, loss-limit and drawdown gates open; not inside a revenge/cooldown window.
6. Identity and units resolved (symbol, currency, GBX/ZAC).
7. Decision journaled with inputs and as-of dates.

**Rule engine (pre-trade compliance).** The checklist above becomes a rule set that every paper order
passes through. Rules and lists are **user-supplied policy**; EODHD supplies identifiers, classification
and liquidity inputs.

| Rule type | Rule | Data |
|---|---|---|
| Restricted list | buy of a listed symbol **or any listing of a listed issuer** → hard block | user list |
| Single symbol / issuer limit | post-trade weight of the symbol, and of the issuer summed over all its share classes and listings, ≤ limit | ID mapping, raw closes |
| Sector limit | post-trade sector weight ≤ limit, using **current** `General.Sector` (labelled current classification) | Fundamentals, 10 calls |
| Liquidity | order notional / ADV$ ≤ limit (§16.2) | `avgvolccy` or EOD |
| Cash / margin | §16.6 buying power | user ledger |

- **Issuer grouping.** Resolve each listing with `/api/id-mapping` (`filter[symbol]=` returns `isin`,
  `lei`, `cik`, `cusip`, `figi`). An ISIN groups the listings of one share class across exchanges; share
  classes of one company (e.g. two voting classes) have different ISINs, so group issuers by `lei`, then
  `cik` (US), then a user map. Verify with a probe that both share classes of a known dual-class issuer
  return the same `lei`/`cik` before relying on it; unmapped symbols raise a soft finding.
- **Hard vs soft.** A hard finding blocks the order. A soft finding blocks until an override is logged
  with approver, reason and timestamp in an append-only log; hard blocks cannot be overridden in the tool.
  Sells that reduce an exposure never breach a limit.

```python
import datetime as dt

def post_trade_exposures(holdings, order, ref, nav):
    """holdings: {symbol: market value}; order: {"symbol", "side", "notional"} (notional > 0).
    ref: {symbol: {"issuer", "sector"}} - issuer key from ID mapping (LEI, else CIK, else user map).
    Returns post-trade weights by symbol, issuer and sector."""
    mv = dict(holdings)
    sign = 1 if order["side"] == "buy" else -1
    mv[order["symbol"]] = mv.get(order["symbol"], 0.0) + sign * order["notional"]
    by = {"symbol": {}, "issuer": {}, "sector": {}}
    for s, v in mv.items():
        by["symbol"][s] = by["symbol"].get(s, 0) + v / nav
        for dim in ("issuer", "sector"):
            k = ref.get(s, {}).get(dim) or f"UNMAPPED:{s}"
            by[dim][k] = by[dim].get(k, 0) + v / nav
    return by

def pretrade_check(order, holdings, nav, ref, rules, restricted, adv_value=None):
    """rules: [{"id", "kind": "hard"|"soft", "dim": "symbol"|"issuer"|"sector"|"adv", "limit"}].
    restricted: {issuer or symbol: reason} (user-supplied list, matched at issuer level too).
    Returns status pass | soft_breach (needs a logged override) | hard_block, with every finding."""
    findings = []
    issuer = ref.get(order["symbol"], {}).get("issuer")
    for key in (order["symbol"], issuer):
        if key and key in restricted and order["side"] == "buy":
            findings.append({"rule": "restricted_list", "kind": "hard", "key": key,
                             "detail": restricted[key]})
    if issuer is None:
        findings.append({"rule": "issuer_unmapped", "kind": "soft", "key": order["symbol"]})
    exp = post_trade_exposures(holdings, order, ref, nav)
    exp0 = post_trade_exposures(holdings, {**order, "notional": 0.0}, ref, nav)
    for r in rules:
        if r["dim"] == "adv":
            if adv_value is None:
                findings.append({"rule": r["id"], "kind": "soft", "detail": "no volume data"})
            elif order["notional"] / adv_value > r["limit"]:
                findings.append({"rule": r["id"], "kind": r["kind"],
                                 "value": order["notional"] / adv_value, "limit": r["limit"]})
            continue
        key = order["symbol"] if r["dim"] == "symbol" else ref.get(order["symbol"], {}).get(r["dim"])
        key = key or f"UNMAPPED:{order['symbol']}"
        w, before = exp[r["dim"]].get(key, 0.0), exp0[r["dim"]].get(key, 0.0)
        if w > r["limit"] and order["side"] == "buy":   # sells that reduce exposure never breach
            findings.append({"rule": r["id"], "kind": r["kind"], "key": key,
                             "value": round(w, 6), "limit": r["limit"], "before": round(before, 6)})
    kinds = {f["kind"] for f in findings}
    status = "hard_block" if "hard" in kinds else "soft_breach" if "soft" in kinds else "pass"
    return {"status": status, "findings": findings}

def log_override(log, check, order, approver, reason, now=None):
    """Append-only override record; hard blocks cannot be overridden here."""
    if check["status"] != "soft_breach":
        raise PermissionError("only soft breaches can be overridden")
    if not reason.strip():
        raise ValueError("override needs a reason")
    rec = {"ts": (now or dt.datetime.now(dt.timezone.utc)).isoformat(), "order": dict(order),
           "rules": [f["rule"] for f in check["findings"]], "approver": approver, "reason": reason}
    log.append(rec)
    return rec
```

Fixtures (NAV 1,000,000; holdings GOOGL 80,000, META 160,000, XOM 60,000; issuer limit 10% hard, sector
limit 25% soft, both GOOG and GOOGL mapped to one issuer key): buy GOOG 50,000 → `hard_block`, issuer
weight 8% → 13%, sector 24% → 29%; buy GOOG 15,000 → `soft_breach` (sector 25.5%), override logged with
approver and reason; buy XOM with its issuer key on the restricted list → `hard_block`; sell META 50,000 →
`pass`; an override attempt on a hard block raises `PermissionError`.

### 16.5 Output contract

```python
import math

def size_position(equity, entry, stop, risk_frac, side="buy", max_weight=0.20, adv_value=None,
                  max_participation=0.10, sigma_ann=None, target_vol=None, requested_shares=None,
                  current_shares=0, allow_short=False, spread_bps=None, sigma_daily=None, eta=None):
    """side='buy' (stop below entry) or 'sell' = sell-to-open short (stop above entry).
    Cost estimate (bp) = 0.5*spread_bps + eta*sigma_daily*sqrt(notional/adv_value)*1e4 (§16.2)."""
    if side not in ("buy", "sell"):
        return {"status": "refused", "reason": "unknown_side"}
    if side == "sell" and not allow_short:
        return {"status": "refused", "reason": "short_not_allowed"}
    per_share_risk = entry - stop if side == "buy" else stop - entry
    if per_share_risk <= 0:
        return {"status": "refused", "reason": "stop_on_wrong_side_of_entry"}
    held_same_side = max(0, current_shares if side == "buy" else -current_shares)
    caps = {"risk_budget": math.floor(equity * risk_frac / per_share_risk),
            "max_weight": max(0, math.floor((equity * max_weight - held_same_side * entry) / entry))}
    warnings = []
    if target_vol is not None:
        if not sigma_ann:
            return {"status": "refused", "reason": "volatility_unavailable"}
        room = equity * min(target_vol / sigma_ann, max_weight) - held_same_side * entry
        caps["vol_target"] = max(0, math.floor(room / entry))
    if adv_value:
        caps["adv_participation"] = math.floor(adv_value * max_participation / entry)
    else:
        warnings.append("liquidity_check_skipped_no_volume")
    binding = min(caps, key=caps.get)
    if requested_shares is not None:
        exceeded = [k for k, v in caps.items() if requested_shares > v]
        if exceeded:
            return {"status": "refused", "reason": "exceeds_" + "+".join(exceeded), "caps": caps}
    shares = requested_shares or caps[binding]
    if shares <= 0:
        return {"status": "refused", "reason": f"zero_size_{binding}", "caps": caps}
    notional = shares * entry
    signed = shares if side == "buy" else -shares
    cost_bps = None
    if spread_bps is not None:
        cost_bps = 0.5 * spread_bps
        if eta is not None and sigma_daily and adv_value:
            cost_bps += eta * sigma_daily * math.sqrt(notional / adv_value) * 1e4
        else:
            warnings.append("impact_not_estimated")
    else:
        warnings.append("cost_not_estimated_no_spread")
    w0 = current_shares * entry / equity
    w1 = (current_shares + signed) * entry / equity
    return {"status": "paper_intent", "side": side, "shares": shares, "binding": binding,
            "notional": notional, "risk": shares * per_share_risk,
            "cost_bps": None if cost_bps is None else round(cost_bps, 2),
            "cost_value": None if cost_bps is None else round(notional * cost_bps * 1e-4, 2),
            "weight_before": round(w0, 6), "weight_after": round(w1, 6),
            "weight_change": round(w1 - w0, 6), "caps": caps, "warnings": warnings}
```

Fixtures: E = 100,000, entry 50, stop 47, f = 1%, ADV$ 2,000,000, σ 30%, target 15% → 333 shares,
binding `risk_budget`, weight change +16.65%. Target vol given but σ missing → refused
`volatility_unavailable`. With f = 5%, `max_weight = 1.0` and ADV$ 200,000, a requested 600 shares
(30,000 = 15% of ADV$, cap 10%) → refused `exceeds_adv_participation`. Holding 100 shares already, with
spread 4 bp, σ_daily 1.9% and η 0.5 → 300 shares (binding `max_weight`, post-trade weight 20.0%),
`cost_bps` 10.23, `cost_value` 15.34. `side='sell'` without `allow_short` → refused `short_not_allowed`;
with it, entry 50 and stop 53 → 333 shares, weight change −16.65%. A buy with the stop above entry →
refused `stop_on_wrong_side_of_entry`. Kelly without a declared edge → refused `edge_not_declared` (16.1).

### 16.6 Margin model for paper trading and backtests

**Use when:** a paper account or backtest uses leverage or short sales. A strategy that borrows must declare
these terms; without them it runs unlevered or is refused (the [strategy spec](../assets/strategy-spec.md) rejects leverage without a financing and margin model). Margin
ratios, financing rates, borrow fees and the call procedure are **user-supplied broker or house terms**:
EODHD provides prices, not margin rules, borrow availability or broker rates.

**EODHD inputs:** raw closes (normalized units) for marking; optional base rate for financing from
`/api/rates/reference-rates?filter[code]=SOFR` (or the UST bill series in §4.1) plus a user spread —
verify the series and entitlement with a probe.

**Definitions** (one currency; `cash` may be negative = debit balance, and includes short-sale proceeds):

```
MV_L = Σ long qty·P,  MV_S = Σ short qty·P
equity        E = cash + MV_L − MV_S
maintenance   MR = m_L·MV_L + m_S·MV_S          (m = user maintenance ratios)
initial       IR = i_L·MV_L + i_S·MV_S          (i = user initial ratios)
buying power  BP = max(0, E − IR) / i_L         (new long notional allowed)
call          CALL = max(0, MR − E)             → status MARGIN_CALL when E < MR
long trigger  P* = D / (q·(1 − m_L))            (single long, debit D, q shares)
short trigger P* = C / (q·(1 + m_S))            (single short, total cash credit C)
financing     debit · rate · days / basis       (basis 360 or 365, user terms)
cure by sale  S = CALL / m_L                    (selling S cuts debit and MV by S; E unchanged)
```

**Method:**

1. Before each simulated order: compute the post-trade state; refuse if post-trade `E < IR` (initial
   margin) or the order exceeds `BP`.
2. Daily, after marking at the raw close: accrue financing on the debit balance and borrow fees on shorts
   (user rates), then recompute `E`, `MR` and the call.
3. **Margin call workflow:** status `MARGIN_CALL` blocks new risk-increasing orders, records the call
   amount, the trigger date and the deadline (user terms), and reports both cures (deposit `CALL`, or sell
   `S = CALL / m_L` of longs). It **never liquidates silently**: a forced liquidation runs only under a
   declared user rule (which positions, at which price — e.g. next open), and every step is logged.
4. Report leverage `(MV_L + MV_S)/E`, distance to the call price per position, and cumulative financing
   cost beside returns (§7.6 item 3).

```python
def margin_state(cash, longs, shorts, prices, im_long, mm_long, im_short, mm_short):
    """Paper margin account in one currency. cash may be negative (debit balance) and includes
    short-sale proceeds. longs/shorts: {symbol: shares > 0}. Ratios are user-supplied decimals
    (e.g. im_long 0.50, mm_long 0.25, im_short 0.50, mm_short 0.30)."""
    mv_long = sum(q * prices[s] for s, q in longs.items())
    mv_short = sum(q * prices[s] for s, q in shorts.items())
    equity = cash + mv_long - mv_short
    maint_req = mm_long * mv_long + mm_short * mv_short
    init_req = im_long * mv_long + im_short * mv_short
    excess = equity - init_req
    return {"mv_long": mv_long, "mv_short": mv_short, "equity": equity,
            "maintenance_requirement": maint_req, "initial_requirement": init_req,
            "buying_power_long": max(0.0, excess) / im_long,   # new long notional allowed
            "call": max(0.0, maint_req - equity),                # deposit needed to cure
            "status": "MARGIN_CALL" if equity < maint_req else "OK"}

def long_call_price(debit, shares, mm):
    """Price at which a single long position financed by `debit` hits maintenance:
    q*P - D = m*q*P  ->  P* = D / (q*(1 - m))."""
    return debit / (shares * (1 - mm))

def short_call_price(credit, shares, mm):
    """Short with total cash credit C (proceeds + deposited margin): C - q*P = m*q*P -> P* = C/(q*(1+m))."""
    return credit / (shares * (1 + mm))

def financing_cost(debit, annual_rate, days, basis=360):
    """Interest on a debit balance; rate and day-count basis are the user's broker terms."""
    return max(0.0, debit) * annual_rate * days / basis

def cure_by_sale(call, mm):
    """Long-only cure by selling: selling S reduces debit and MV by S, equity unchanged,
    requirement falls by m*S -> S = call / m."""
    return call / mm
```

**Pitfalls:**

- Gaps jump over trigger prices: a call at the open can already be a deficit (`E < 0`); report it, do not
  floor equity at zero.
- Intraday margin is not modelled from daily bars; state "end-of-day margin only".
- Financing day counts include weekends and holidays (calendar days on the debit), unlike return
  annualization (§2.2).
- Concentrated or volatile positions often carry higher house requirements; take them from the user.

**Acceptance checks** (`i_L` = `i_S` = 50%, `m_L` 25%, `m_S` 30%): buy 1,000 at 50 with debit 25,000 →
E 25,000, MR 12,500, BP 0; long trigger price **33.33**. At 30: E 5,000, MR 7,500, call **2,500**, cure by
sale 10,000. At 60: E 35,000, BP 10,000. Financing 25,000 at 6% for 30 days, basis 360 → **125.00**.
Short 1,000 at 50 with total credit 75,000 → E 25,000, trigger **57.69**; at 60, call **3,000**.

---

## 17. Recipe: holdings risk report

**Use when:** "give me a risk report for these tickers/weights".

**Inputs (user):** tickers and weights or quantities, reporting currency, benchmark (default: a TR index
or ETF matching the holdings' market — ask if ambiguous), horizon.

**Plan:** prices on EOD All World; technical flags on Extended; sector and insider data on Fundamentals
Feed/All-In-One (Form 4 needs All-In-One). Degrade gracefully: missing entitlement → that column shows
"not entitled", not neutral.

**Call budget for N holdings:**

| Step | Calls |
|---|---|
| EOD history per holding + benchmark + FX pairs | N + 1 + pairs |
| UST bills (one page per year in window) | years |
| Technical `rsi` (14), `bbands` (20), `atr` (14) | 15N (or compute locally from EOD: 0) |
| `fundamentals?filter=General` | 10N |
| Form 4 (90 days, one page each) | 10N |
| Sentiments (one request for all tickers) | 5N |

For 20 holdings ≈ 20 + 1 + 3 + 300 + 200 + 200 + 105 ≈ 830 calls; computing RSI/%B/ATR locally from
the already-fetched EOD rows saves 300.

**Steps:**

1. Resolve symbols ([identity](identity.md)); normalize units; align returns (§2.3), no zero filling.
2. Portfolio return from current weights; benchmark on the same basis (§4.2); rf from bills.
3. Portfolio statistics: annualized vol, Sharpe, Sortino, MaxDD, beta, TE, IR (§6), historical and CF VaR/ES
   (§10), worst windows, average correlation, DR, effective N (§11), sector weights and HHI (§13.2).
4. Per-holding table: weight, 1Y return, vol, beta, MaxDD, component VaR share, sector, RSI(14),
   Bollinger %B `= (close − lower)/(upper − lower)` on 20/2σ, ATR(14)/close, 90-day insider net value
   (Form 4 codes `P` minus `S` only, `shares_amount × price_per_share`; grants, exercises, tax withholding
   and gifts excluded), 30-day sentiment mean and trend (`normalized`, weighted by `count`).
5. Flags (§11.2) plus heuristic technical flags (RSI > 70 / < 30, %B > 1 / < 0, ATR/close above its
   1-year 90th percentile) — labelled heuristics, not signals.
6. Stress table (§12) for 2–3 scenarios and a beta-shock row if the §11.1 conditions hold.
7. Header with as-of dates per dataset; data notes (missing sentiment shown "n/a", proxies, exclusions).

**Acceptance:** benchmark basis printed; no zero returns on holidays; a ticker with no sentiment shows "n/a"
not 0; insider net excludes code `A`/`M`/`F`/`G` rows; component VaR shares sum to 100%; effective N matches
`1/Σw²`.

---

## 18. Acceptance fixture summary

| Fixture | Expected |
|---|---|
| Returns +10%, −10% | sum 0, compounded −1% |
| Same series, crypto vs equity vol | ratio 1.2035 |
| Mean P/E vs aggregate P/E (caps 100/300, earnings 10/5) | 35 vs 26.67 |
| Modified Dietz (1,000; +500 day 15/30; 1,600) | 8.00% |
| TWR vs MWR (100 → +50%, +1,000, −20%) | +20.00% vs −15.19% |
| Monthly [1, −2, 3, −1, 2]%, A = 12 | Sharpe 1.002, Sortino 2.078, Omega 2.000 |
| Constant returns | Sharpe/Sortino undefined |
| Carino / Menchero linking fixture (§8.2) | linked sums 0.019974; naive 0.020000 |
| Split in OHLC: raw vs scaled | Parkinson/GK/RS equal; CC and YZ corrected |
| Yang-Zhang κ, n = 20 | 0.1390 |
| EWMA λ = 0.94 half-life | 11.2 observations |
| Kupiec T = 250, 99%: x = 2 / 8 / 0 | LR 0.108 accept / 7.73 reject / 5.03 reject |
| Component VaR | sums to total |
| Effective N, weights 60/25/15 | 2.247 |
| MP edge N = 50, T = 1000; one-factor data | 1.497; one eigenvalue above |
| ERC with diagonal Σ; HRP with diagonal Σ | inverse-vol; inverse-variance weights |
| Min-var vs EW (fixture Σ) | 8.67% ≤ 13.00% |
| Black-Litterman with no views | returns market weights |
| Cash-flow-first, C = 100 into 700/300 at 60/40 | buys (0, 100) |
| Sizing E = 100k, 50/47, 1% | 333 shares, risk budget binds |
| Sizing with vol target and no σ; Kelly without edge | refused with reason |
| Cash-only portfolio | VaR 0, stress P&L 0 |
| Composite 1,000/2,000/7,000 at 2/3/1% (§5.5) | 1.5000%; with mid-period flow 1.4762% |
| Internal dispersion, six members (§5.5) | asset-weighted SD 1.5297%; five members → not meaningful |
| Breakeven IR, fee gap 0.70%, TE 4% (§6.1) | 0.175; ≈ 130.6 years to t = 2 |
| Goal path V0 100k, C 10k, G 200k, T 5 (§7.7) | r_req 7.289% |
| Drawdown episodes, θ 10% (§7.8) | 3 episodes, last one censored |
| Trigger queue (§11.4) | 0.88 / 0.75 / 0.54 / 0.30; repeat hit keeps 4 items |
| Hedge: longs 600k/400k, short −500k (§13.4) | dollar-neutral −500,000; beta-neutral −290,000 |
| Capped weights 50/30/10/5/5, cap 25% (§14.10) | 25/25/25/12.5/12.5% |
| Sleeves 70/30 with 2% cash buffer (§15.5) | VTI 41.16%, BND 27.44%, QQQ 29.40% |
| Kelly growth p 0.55, b 1 (§16.1) | half Kelly keeps 74.9% of max growth |
| Pre-trade: second share class over issuer limit (§16.4) | hard_block; soft breach needs logged override |
| Margin: 1,000 at 50, debit 25k, m 25% (§16.6) | trigger 33.33; call at 30 = 2,500 |
