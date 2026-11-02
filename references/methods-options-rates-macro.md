# Methods: options, rates, fixed income, FX and macro

Scope: step-by-step analytical methods for US stock/ETF options (EODHD Marketplace end-of-day chains),
US Treasury and credit series, policy/reference rates, FX and macro indicators, economic events and news
sentiment. Each method lists the EODHD inputs, formulas with units, ordered steps, EODHD-specific pitfalls
and acceptance checks. It complements [options.md](options.md) (contract normalization, quote quality,
surfaces) and [cross-asset.md](cross-asset.md) (macro, fixed-income and FX principles); read those for the
general rules. Everything here is an analytical method, not a forecast or a recommendation. Field facts
marked "probe 2026-10-25" were observed in live responses on that date (AAPL options and AAPL.US EOD with
the demo key; rates, macro and credit endpoints with a paid key). `EURUSD.FOREX` and WTI
commodity facts come from demo-key probes on 2026-10-25/26. Re-verify all of them before relying on them
in production.

## Contents

Part A — Options
- A0. Data contract: fetching a chain, verified field units, spot, rate and dividend inputs
- A1. Vendor IV/Greeks or recompute?
- A2. Black-Scholes-Merton pricing and Greek units
- A3. Implied-volatility solver with bounds
- A4. American options: CRR binomial tree with discrete dividends
- A5. Chain summary (put/call ratios, ATM IV, term structure, skew)
- A6. Constant-maturity ATM implied volatility
- A7. IV rank and IV percentile
- A8. Realized volatility, IV–RV spread and variance risk premium
- A9. 25-delta skew: risk reversal and butterfly
- A10. Earnings implied move vs actual move
- A11. IV-crush scenarios
- A12. Strategy P/L grid, breakevens, maximum loss, probability of profit
- A12b. Monte Carlo pricing for path-dependent payoffs (Asian, barrier) with variance reduction
- A13. Hedge-cost tables (protective put, collar, put spread)
- A14. Activity metrics (volume/OI, OI change, unusual activity)
- A15. Gamma exposure (GEX), zero-gamma flip and walls
- A16. Options boundaries

Part B — Rates and fixed income
- B0. Data contract: UST curves, GBOND, policy/reference rates, funding stress, credit; unit table
- B1. Curve slopes, butterflies and shape labels
- B2. Bootstrapping zero (spot) rates and forwards from the UST par curve
- B3. Price, yield, duration, DV01 and convexity for user-supplied bonds
- B3b. Bond portfolio cash-flow waterfall
- B4. Breakeven inflation and real-rate regime
- B5. G-spread, Treasury-curve Z-spread and corporate credit context
- B6. DV01-neutral steepener/flattener sizing
- B7. Treasury and TIPS ladders (indicative); liquidity tiers, blended ladder yield, reinvestment rule
- B8. Credit and sovereign-risk endpoints: what each one is for
- B9. Money-market funding stress and the policy-rate path
- B10. Rates and credit boundaries (with user-input modules: bond-futures basis and implied repo, tax-equivalent yield)

Part C — FX and macro
- C1. Covered-interest-parity forward and hedged returns
- C2. Carry proxy and carry-to-volatility
- C2b. FX momentum and policy-rate divergence table
- C3. PPP gap and real exchange rate from annual CPI
- C4. Macro indicators: codes, units, call rules
- C5. Economic events: call rules, fields and impact tiers
- C6. Macro-surprise event study
- C7. Central-bank meeting preview
- C8. Composite sentiment index
- C9. Macro dashboard recipe
- C9b. Commodity reference series: data contract, ETF tracking, inflation beta, futures contract sizing
- C10. FX and macro boundaries

---

# Part A — Options

## A0. Data contract: fetching a chain, verified field units, spot, rate and dividend inputs

**Use when:** any options computation starts; settle these inputs once and reuse them.

**EODHD inputs.** Marketplace "US Stock Options" product (separate subscription and separate 100,000
calls/24 h quota; 10 calls per request). Endpoints `/api/mp/unicornbay/options/{underlying-symbols,contracts,eod}`
([us-options-eod](api/endpoints/us-options-eod.md)). US stocks and ETFs only, EOD snapshots, history from
early Q4 2023, no cash-settled index options. Demo key: AAPL only.

**Field units (probe 2026-10-25, AAPL rows dated 2026-10-23; consistent with Black-Scholes on the AAPL.US
close 347.725):**

| Field | Observed meaning and unit |
|---|---|
| `volatility` | Implied volatility, decimal per year (0.2742 = 27.42%). `0` appears for illiquid contracts: treat as missing |
| `delta` | Per 1 share; calls positive, puts negative |
| `gamma` | Change in delta per 1 USD move of the underlying, per share |
| `vega` | Price change per **1 volatility point** (BS vega / 100) |
| `theta` | Price change per **calendar day** (annual theta / 365) |
| `rho` | Price change per **1 percentage point** of rate; call values matched BS, put values were ~15% smaller (model not documented) |
| `theoretical` | Equalled `midpoint` on every row checked — not an independent model value |
| `midpoint` | (bid + ask) / 2 |
| `moneyness` | Signed distance from spot, rounded to 0.01: calls (S − K)/S, puts (K − S)/S; positive = in the money |
| `dte` | Calendar days to expiry, but Friday rows were one day short (27 on 2026-10-23 and 34 on 2026-10-16 for the 2026-11-20 expiry; true values 28 and 35) |
| `open_interest_change` | OI(t) − OI(t−1) for the same contract (checked over 8 sessions) |
| `vol_oi_ratio` | volume / open_interest, rounded to 0.01 |
| `bid_date`, `ask_date` | ISO UTC stamps such as `2026-10-24T04:00:00Z` (midnight New York after the session): a snapshot stamp, not the quote time. The doc example shows a different format |
| `tradetime` | Date of last trade; can be old for contracts that still carry OI |
| record `id` | `{contract}-{observation date}`; the suffix is the observation date |

**How to fetch a chain.**
1. Latest session for one underlying: request `filter[underlying_symbol]=X&filter[exp_date_eq]=E`
   (one expiry at a time keeps pages small) with `page[limit]=1000`. In the probe the rows came back newest
   observation first, but no sort by observation date is documented: read the id suffix of every row and keep
   only rows whose suffix equals the target date; stop paging once the suffix is older than the target.
2. `filter[tradetime_eq]=D` returns only contracts **traded** on D. It drops untraded contracts that carry
   open interest, so do not use it for OI, GEX or put/call OI ratios.
3. A past date: a contract's whole history comes back newest first (the 2026-11-20 350 call returned 205
   daily rows from its listing on 2026-01-12). Offset is capped at 10,000, so cut requests by expiry and
   strike band (`filter[strike_from|to]`) until each request holds ≤ 11,000 rows. Calls ≈
   10 × ceil(rows / 1000) per filter set.
4. Ongoing work: archive the latest-day chain each evening (recipe 39 pattern) so later studies do not
   need to page through history.
5. Trim payloads with `fields[options-eod]=...`; it narrows the response, not the call cost.

**Spot.** Use the underlying's raw EOD `close` (`/api/eod/X.US`) for the same date. Strikes are in raw
terms, so never use `adjusted_close` for moneyness or pricing. Cross-check with put–call parity at the two
strikes nearest spot: `S_impl = C − P + K·e^(−rT) + PV(dividends)`. On 2026-10-23, the 350 strike gave
`9.70 − 11.20 + 350·e^(−0.04·28/365) ≈ 347.4` before adding the PV of the dividend expected before expiry, against an EOD close of 347.725. A gap larger than about half the
combined bid–ask spread points to a stale quote or wrong dividend input.

**Risk-free rate.** Use UST par yields from `/api/ust/yield-rates` (B0), linearly interpolated at the option's T.
Convert the bond-equivalent par yield to continuous with `r = 2·ln(1 + y/2)`, where y is decimal.
Alternatively use SOFR (`/api/rates/reference-rates`) as an overnight proxy. State which one you used.
The vendor's own rate is undocumented. The probe fitted best near 4%, against a 1M UST yield of 4.11%.

**Dividends.** For single stocks, use the dividend history from `/api/div/X.US` (ex-date `date`,
`value`) and declared upcoming dividends from `/api/calendar/dividends`. For dividends not yet declared
inside the option's life, repeat the last amount at the observed frequency and label it an assumption.
For broad ETFs, a continuous yield q = trailing 12-month dividends / price is acceptable.

**Time to expiry.** `T = (expiry date − observation date) / 365` in calendar days, from the id suffix
date. Do not take it from `dte`. Equity options stop trading at 16:00 New York on expiry day. For a
same-day-expiry contract, T = 0 at the snapshot: exclude it from IV work.

**Pitfalls.** The endpoint page says "2-year historical depth"; the product scope (options.md) is history
from early Q4 2023 with no rolling window — probe the first date for each underlying. Holiday rows repeat
the previous session: drop observation dates that are not NYSE sessions (`/api/exchange-details/US`).

**Acceptance checks.**
- Parity-implied spot is within 0.5% of the EOD close on liquid at-the-money strikes.
- Every stored row carries observation date (from the id), spot, rate, q or dividend list, and T.
- A chain built with `tradetime_eq` is rejected for OI-based metrics.

## A1. Vendor IV/Greeks or recompute?

**Use when:** deciding whether `volatility`/`delta`/`gamma`/`vega`/`theta` can be used as delivered.

| Situation | Use vendor fields | Recompute |
|---|---|---|
| Screening liquid near-the-money contracts (0.10 ≤ abs(delta) ≤ 0.90) | ✓ after the checks below | — |
| `volatility == 0`, null, or Greeks all 0 | — | ✓ from mid, or mark unavailable |
| Deep in-the-money (abs(delta) > 0.90) | — | ✓ from out-of-the-money side; the probe showed ITM call IVs scattering between 0.25 and 0.81 across 240–300 strikes while OTM puts were smooth |
| American early exercise matters (deep ITM puts; calls before an ex-dividend date) | — | ✓ with A4 |
| Time series across dates (constant-maturity IV, IV rank) | — | ✓ with your own T (vendor `dte` is off by one on Friday rows) |
| Your own r, q or day-count conventions must be consistent across a surface | — | ✓ |
| GEX on a spot grid (A15) | vendor gamma at current spot only | ✓ at other spots |

Validation rule for vendor rows: reprice `midpoint` with the vendor IV under your r, q and T. Accept the
row when the repriced value is within half the bid–ask spread. Also require `|vendor IV − own IV from mid|
≤ 0.01`. Count the rows you reject by reason (zero IV, crossed or empty quote, stale `tradetime`,
off-model).

**Acceptance checks.** On the 2026-10-23 AAPL 350 call (mid 9.70, vendor IV 0.2742, T = 27/365,
r = 4%, q = 0.3%), the BS price at the vendor IV is 9.72 and the own IV from mid is 0.2738. Vendor vega
0.3771 equals BS vega/100. The report lists each excluded count.

## A2. Black-Scholes-Merton pricing and Greek units

**Use when:** pricing European-style payoffs, or computing Greeks with explicit units.

**Method.** With S = spot, K = strike, T = years, r = continuous risk-free rate, q = continuous dividend
yield, σ = volatility (all decimals):

```
d1 = [ln(S/K) + (r − q + σ²/2)·T] / (σ·√T),   d2 = d1 − σ·√T
Call = S·e^(−qT)·N(d1) − K·e^(−rT)·N(d2)
Put  = K·e^(−rT)·N(−d2) − S·e^(−qT)·N(−d1)
Parity: C − P = S·e^(−qT) − K·e^(−rT)
```

For discrete dividends (single stocks), use the escrowed model: replace S with
`S − Σ D_i·e^(−r·t_i)` for the dividends paid before expiry, and set q = 0.

| Greek | Formula (call; put by parity) | Raw unit | Display convention |
|---|---|---|---|
| Delta | e^(−qT)·N(d1); put −e^(−qT)·N(−d1) | per 1 share | ×100 for per-contract delta in shares |
| Gamma | e^(−qT)·n(d1)/(S·σ·√T) | delta per 1 USD | per contract ×100 |
| Vega | S·e^(−qT)·n(d1)·√T | per 1.00 vol | /100 → per vol point (EODHD style) |
| Theta | −S·e^(−qT)·n(d1)·σ/(2√T) − rK·e^(−rT)·N(d2) + qS·e^(−qT)·N(d1) | per year | /365 per calendar day (EODHD style) or /252 per session — state which |
| Rho | K·T·e^(−rT)·N(d2); put −K·T·e^(−rT)·N(−d2) | per 1.00 rate | /100 per percentage point |

Position Greeks = Greek × quantity × multiplier (100 for standard contracts; check adjusted contracts).

```python
import math
from statistics import NormalDist
N, n = NormalDist().cdf, NormalDist().pdf

def bsm(S, K, T, r, q, sigma, kind):
    """Price and raw Greeks (vega per 1.00 vol, theta per year, rho per 1.00 rate)."""
    if T <= 0 or sigma <= 0:
        raise ValueError("T and sigma must be positive")
    sq = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / sq
    d2 = d1 - sq
    dq, dr = math.exp(-q * T), math.exp(-r * T)
    gamma = dq * n(d1) / (S * sq)
    vega = S * dq * n(d1) * math.sqrt(T)
    common = -S * dq * n(d1) * sigma / (2 * math.sqrt(T))
    if kind == "call":
        return dict(price=S * dq * N(d1) - K * dr * N(d2), delta=dq * N(d1), gamma=gamma, vega=vega,
                    theta=common - r * K * dr * N(d2) + q * S * dq * N(d1), rho=K * T * dr * N(d2))
    return dict(price=K * dr * N(-d2) - S * dq * N(-d1), delta=-dq * N(-d1), gamma=gamma, vega=vega,
                theta=common + r * K * dr * N(-d2) - q * S * dq * N(-d1), rho=-K * T * dr * N(-d2))
```

**Pitfalls.** Volatility in percent (27.4) instead of decimal (0.274). Mixing a 252-session T with a
365-day theta. Using `adjusted_close` as S. Treating the vendor `theoretical` as a model price (it equals mid).

**Acceptance checks.** S = K = 100, T = 1, r = 5%, q = 0, σ = 20%: call 10.4506, put 5.5735, call
delta 0.6368, gamma 0.0188, vega 37.52 (0.3752 per vol point), theta −6.414/yr (−0.01757/day), rho 53.23.
Parity residual < 1e−10.

## A3. Implied-volatility solver with bounds

**Use when:** vendor IV is zero/null/rejected, or you need IV under your own conventions.

**Method.**
1. Choose the price: `midpoint` when both bid > 0 and ask > bid; otherwise mark the row unavailable. Use
   the out-of-the-money side (puts below spot, calls above), or average call and put IV at the same strike
   near the money.
2. No-arbitrage bounds (European):
   call `max(S·e^(−qT) − K·e^(−rT), 0) < C < S·e^(−qT)`;
   put `max(K·e^(−rT) − S·e^(−qT), 0) < P < K·e^(−rT)`.
   A price outside the bounds returns **unavailable**, never a clipped IV.
3. Solve `BS(σ) = price` on σ ∈ [0.0001, 5.0] by bisection or Brent (BS price is monotone in σ).
   Newton steps are faster but fail when vega is tiny (deep wings, short T); fall back to bisection.
4. Report convergence (|price error| < 1e−6 or interval < 1e−8) and the iteration count.

```python
def implied_vol(price, S, K, T, r, q, kind, lo=1e-4, hi=5.0, tol=1e-8):
    dq, dr = math.exp(-q * T), math.exp(-r * T)
    lower = max(S * dq - K * dr, 0.0) if kind == "call" else max(K * dr - S * dq, 0.0)
    upper = S * dq if kind == "call" else K * dr
    if not (lower < price < upper):
        return None                                   # outside model bounds: unavailable
    f = lambda s: bsm(S, K, T, r, q, s, kind)["price"] - price
    if f(lo) > 0 or f(hi) < 0:
        return None
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if f(mid) > 0 else (mid, hi)
    return 0.5 * (lo + hi)
```

**Pitfalls.** American options: a deep-ITM American put can trade above the European upper region, and a
European IV then overstates volatility. Invert with A4 instead, or use the OTM call at the same strike.
Stale `tradetime` with a fresh quote is fine (IV comes from bid/ask); a `last`-price IV is not.

**Acceptance checks.** IV of the A2 call price (10.4506) returns 0.2000 ± 1e−6. A call priced 0.01 with
S = 150, K = 100 returns None. A synthetic chain priced at 30% returns 30% on every strike.

## A4. American options: CRR binomial tree with discrete dividends

**Use when:** pricing or inverting IV for single-stock options where early exercise matters: deep-ITM puts,
and calls just before an ex-dividend date.

**Method (Cox-Ross-Rubinstein, escrowed dividends).** With Δt = T/n:
`u = e^(σ√Δt)`, `d = 1/u`, `p = (e^(rΔt) − d)/(u − d)`. Build the tree on `S* = S − PV(dividends before
expiry)`. At each node the exercisable spot is `S*_node + PV(dividends still to be paid)`. The node value
is max(exercise value, discounted continuation). Use n ≥ 500 for 4-decimal stability, or average n and
n + 1 to damp odd–even oscillation.

```python
import numpy as np

def crr_american(S, K, T, r, sigma, kind, steps=500, divs=()):
    """divs: (t_years, cash) pairs with 0 < t < T. Escrowed-dividend CRR tree."""
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt)); d = 1 / u
    p = (math.exp(r * dt) - d) / (u - d); disc = math.exp(-r * dt)
    s_star = S - sum(D * math.exp(-r * t) for t, D in divs if 0 < t < T)
    pv_left = lambda now: sum(D * math.exp(-r * (t - now)) for t, D in divs if now < t < T)
    ex = (lambda x: np.maximum(x - K, 0.0)) if kind == "call" else (lambda x: np.maximum(K - x, 0.0))
    v = ex(s_star * u ** (steps - 2 * np.arange(steps + 1)))
    for i in range(steps - 1, -1, -1):
        spots = s_star * u ** (i - 2 * np.arange(i + 1)) + pv_left(i * dt)
        v = np.maximum(disc * (p * v[:-1] + (1 - p) * v[1:]), ex(spots))
    return float(v[0])
```

**Pitfalls.** The escrowed model slightly misprices options when dividends are large relative to S; keep
it labelled as a model. Corporate-action-adjusted contracts (non-100 deliverable) need their own
deliverable. Do not apply the tree to ETF options with continuous-yield assumptions and then also subtract
discrete dividends (double count).

**Acceptance checks.** S = K = 100, T = 1, r = 5%, σ = 20%, n = 1000: American call without dividends
10.4486 (European 10.4506). American put 6.0896 (> European 5.5735). Call with a 5.00 dividend at
t = 0.5: 7.9213, which exceeds the escrowed European value 7.5774 (early-exercise premium).

## A5. Chain summary (put/call ratios, ATM IV, term structure, skew)

**Use when:** a user asks "summarize the AAPL chain", or an assistant needs a compact view instead of
dumping thousands of rows.

**EODHD inputs.** Latest-day chain (A0) for all expiries; underlying EOD close; UST rate.
Cost ≈ 10 calls × pages (a large underlying is a few thousand contracts → 3–10 requests).

**Method.** Per expiry E (exclude expiries with T < 7 days from IV statistics; keep them in volume/OI):

| Output | Definition |
|---|---|
| Call / put volume, OI | Σ `volume`, Σ `open_interest` by type |
| PCR_vol, PCR_OI | Σ put / Σ call (undefined when the call side is 0) |
| ATM IV | A6 step 1 at spot |
| RR25, BF25 | A9 |
| Expected move (1σ) | S·σ_ATM·√T; mean absolute move ≈ 0.798·S·σ_ATM·√T ≈ ATM straddle mid |
| Liquidity | n contracts, n with bid > 0, median relative spread (ask − bid)/mid |

Aggregate rows: totals across expiries; DTE buckets 0–7, 8–30, 31–90, > 90; term structure = ATM IV
against T; slope = IV_CM30 − IV_CM90 (positive = inverted, often event-driven).

**Pitfalls.** Put/call ratios from an ETF chain describe that ETF's listed options only. They are not the
CBOE market-wide ratio, which EODHD does not provide. A single heavy expiry (monthly, quarterly) dominates
totals: show the per-expiry table. Exclude repeated holiday rows.

**Acceptance checks.** Σ per-expiry OI equals the total. Expiries with no two-sided quotes show ATM IV
"unavailable". Probe example, 2026-10-23, AAPL 2026-11-20 expiry: ATM IV 0.2791 (A6). The ATM straddle
mid at 347.5 was 21.13 (6.08% of spot), against 0.798·σ·√T = 6.17%.

## A6. Constant-maturity ATM implied volatility

**Use when:** building a daily 30-day IV series for IV rank, IV–RV, VRP or regime work. A single
rolling contract's IV drifts with moneyness and time, so it is not a valid series.

**Method.**
1. ATM IV per expiry: at each strike, average call and put IV (vendor or own, after A1 filtering). Linearly
   interpolate in strike between the two strikes bracketing spot S. If spot is outside the quoted strikes, the result is unavailable.
   Delta-neutral or forward-ATM variants are fine: state which.
2. Total variance per expiry: `w_i = σ_i² · T_i`.
3. For target τ (e.g. 30/365), take the expiries with `T1 < τ ≤ T2`, both with T ≥ 7 days. Then
   `w(τ) = w1 + (w2 − w1)·(τ − T1)/(T2 − T1)` and `σ_CM(τ) = √(w(τ)/τ)`.
4. If `w2 < w1` (calendar total-variance inversion), flag it and do not interpolate. If τ lies outside the
   available expiries, the value is unavailable; never extrapolate.
5. Store σ_CM(τ) with: date, T1, T2, σ1, σ2, strikes used, and source (vendor/own).

```python
def constant_maturity_iv(t1, iv1, t2, iv2, target):
    if not (t1 < target <= t2):
        raise ValueError("expiries must bracket the target")
    w1, w2 = iv1 * iv1 * t1, iv2 * iv2 * t2
    if w2 < w1:
        raise ValueError("calendar total-variance inversion")
    return math.sqrt((w1 + (w2 - w1) * (target - t1) / (t2 - t1)) / target)
```

**Pitfalls.** An earnings date between T1 and T2 makes the interpolation mix event and non-event
variance; mark such dates (A10). Weekly expiries make T1/T2 close together, which is fine. Do not use `dte`
for T (Friday rows are one day short).

**Acceptance checks.** Constant 30% IV at 20 and 48 days → 30.00% at 30 days. 32% at 20 days and 28% at
48 days → 29.78%. Probe 2026-10-23 AAPL: 2026-11-20 (28 d) ATM 0.2791 and 2026-11-27 (35 d) ATM 0.2639
→ CM30 = 0.2741.

## A7. IV rank and IV percentile

**Use when:** "is IV high for this stock?"

**Method.** Over a stated window of past observations `H` (e.g. the last 252 sessions of σ_CM30, ending
at t−1 or t; state which):
- IV rank = (IV_t − min H)/(max H − min H). Undefined when max = min.
- IV percentile = share of observations in H strictly below IV_t.
- Require `len(H) ≥ min_obs` (suggest 120 sessions); otherwise return "unavailable (n = …)".

```python
def iv_rank_percentile(history, current, min_obs=120):
    h = [x for x in history if x is not None and x > 0]
    if len(h) < min_obs:
        return None, None, len(h)
    lo, hi = min(h), max(h)
    rank = None if hi == lo else (current - lo) / (hi - lo)
    return rank, sum(x < current for x in h) / len(h), len(h)
```

**EODHD inputs and history.** No vendor IV-history series exists. Build H from your archived σ_CM30 or
reconstruct it from `options/eod` history: per past date, the near-ATM contracts of the two bracketing
expiries. Budget roughly 10 calls per 1,000 rows of contract history. History starts in early Q4 2023,
so a 252-session window exists only from about Q4 2024. Report the window start, n, and whether it was
reconstructed or archived.

**Pitfalls.** Rank is dominated by one spike (e.g. a 2025 shock); percentile is more robust, so show both.
Earnings make IV seasonal: also report ex-earnings rank or exclude event windows. A newly listed
underlying has a short window.

**Acceptance checks.** H = 1..100 and IV = 75 give rank 0.7475 and percentile 0.74. Fewer than min_obs
values return unavailable with n. The window length appears in the output.

## A8. Realized volatility, IV–RV spread and variance risk premium

**Use when:** comparing implied with realized volatility, or measuring the premium sellers earned historically.

**EODHD inputs.** Underlying `/api/eod/X.US`: `adjusted_close` for close-to-close; raw O/H/L/C for
range estimators (same-day ratios cancel the adjustment factor). For overnight terms, adjust O and the
previous C with the day's factor `k = adjusted_close/close` ([data-semantics.md](data-semantics.md)).

**Method.** With r_t = ln(C_t/C_{t−1}) over n returns and A = 252 sessions per year:

| Estimator | Formula (annualized) | Notes |
|---|---|---|
| Close-to-close | √A · stdev_sample(r) | Default; includes overnight gaps |
| Parkinson | √(A · mean(ln(H/L)²) / (4 ln 2)) | Intraday range only; daily bars are regular session, so it misses overnight moves and understates close-to-close vol |
| Garman–Klass | √(A · mean(0.5·ln(H/L)² − (2 ln 2 − 1)·ln(C/O)²)) | Same caveat |
| Yang–Zhang | σ² = σ_o² + k·σ_c² + (1 − k)·σ_RS², k = 0.34/(1.34 + (n+1)/(n−1)); σ_o² = var of ln(O_t/C_{t−1}), σ_c² = var of ln(C_t/O_t), σ_RS² = mean[ln(H/C)·ln(H/O) + ln(L/C)·ln(L/O)] | Handles overnight jumps; needs adjusted O and previous C |

- **IV–RV spread (ex-ante, observable on date t):** `σ_CM30(t) − RV20(t)`, where RV20 is the trailing
  20-return close-to-close vol. 30 calendar days ≈ 21 sessions; say which horizon you matched.
- **Variance risk premium (ex-post):** `VRP_t = σ_CM30(t)² − RV²(t+1 … t+21)`, in variance units;
  √-difference in vol units for display. The window ends 21 sessions later. Use non-overlapping
  observations (every 21st day) or HAC standard errors for statistics.

**Pitfalls.** IV is annualized on calendar time and RV on sessions; the ratio is still comparable because
both are per-year figures. Crypto underlyings use 365 (not relevant for options here). Do not mix raw
`close` across a split. A constant-return series has RV = 0.

**Acceptance checks.** Constant daily return → RV = 0. Simulated i.i.d. returns with sd 2% → RV ≈ 0.3175
(√252·0.02). The 365/252 annualization ratio = 1.2035. Probe: AAPL RV20 on 2026-10-23 = 0.1645 and
RV60 = 0.2479, against CM30 IV 0.2741. The spread is wide because the 2026-11-02 earnings sit inside
the 30-day window, so label it event-inclusive.

## A9. 25-delta skew: risk reversal and butterfly

**Use when:** measuring put/call skew comparably across names and dates.

**Method (per expiry, OTM options only).**
1. Collect (delta, IV) for calls with 0.05 ≤ delta ≤ 0.50 and puts with −0.50 ≤ delta ≤ −0.05, after A1
   filtering (bid > 0, relative spread ≤ a stated cap such as 50% of mid).
2. Interpolate linearly in delta: σ_C25 at delta +0.25 and σ_P25 at delta −0.25. If the target delta is
   outside the quoted range, the result is unavailable.
3. `RR25 = σ_C25 − σ_P25` (this convention makes equity skew usually negative; some desks quote put minus
   call: state the sign). `BF25 = (σ_C25 + σ_P25)/2 − σ_ATM`.
4. Constant-maturity skew: interpolate RR25 linearly in T between bracketing expiries.
5. Moneyness alternative: `σ(K = 0.9·S) − σ(K = 1.1·S)` by linear strike interpolation. Use it when deltas
   are missing, and label it.

```python
def iv_at_delta(points, target):
    """points: (delta, iv) pairs for one expiry and one type; linear interpolation in delta."""
    pts = sorted(points)
    for (d1, v1), (d2, v2) in zip(pts, pts[1:]):
        if d1 <= target <= d2:
            return v1 if d2 == d1 else v1 + (v2 - v1) * (target - d1) / (d2 - d1)
    return None
```

**Pitfalls.** Vendor deltas come from vendor IV; mixing vendor deltas with own IVs is inconsistent.
Recompute both, or use both from the vendor. Wings with zero bids give absurd IV; exclude them and count them.

**Acceptance checks.** On a flat-IV chain, RR25 = 0 and BF25 = 0. Swapping the sign convention flips RR25
exactly. Unavailable is returned when no put has |delta| ≥ 0.25.

## A10. Earnings implied move vs actual move

**Use when:** "what move is the market pricing for earnings, and how did past reactions compare?"

**EODHD inputs.** Earnings calendar `/api/calendar/earnings?symbols=X.US&from=&to=` (`report_date`,
`before_after_market`; pass `from`/`to`), options chain on the last session before the report, EOD closes.

**Method.**
1. **Event session.** If `before_after_market = BeforeMarket`, the reaction session is the report date D.
   If AfterMarket, it is the next session D+1. If the timing is unknown, use the two-session window D−1 → D+1
   and flag it.
2. **Straddle implied move:** `M_straddle = (call_mid + put_mid at the ATM strike of the first expiry after
   the event) / S`. This includes ordinary diffusion until that expiry.
3. **Event-only variance (preferred):** base variance from the last expiry *before* the event,
   `σ_b² = σ_ATM(T_pre)²`. Event variance `m² = σ_ATM(T_post)²·T_post − σ_b²·T_post`, so the event-day
   standard deviation is m. Expected absolute event move ≈ `√(2/π)·m ≈ 0.798·m`. If there is no pre-event
   expiry, use two post-event expiries T1 < T2:
   `σ_b² = (w2 − w1)/(T2 − T1)`, `m² = w1 − σ_b²·T1`. This is unstable when T2 − T1 is small, so
   flag results with m² ≤ 0 or σ_b² ≤ 0 as unavailable.
4. **Actual move:** `R = C_after / C_before − 1` around the event session, using `adjusted_close`.
   Ratio = |R| / (0.798·m). Over past events, report the median ratio and the share of events with
   |R| > implied. Options history begins in Q4 2023, so this is about 10–12 events per name.

**Worked example (probe 2026-10-23, AAPL, report 2026-11-02 AfterMarket).** S = 347.725. Pre-event
expiry 2026-10-30 (T = 7/365): ATM 0.2388. Post-event 2026-11-04 (T = 12/365): ATM 0.3269.
m² = 0.3269²·12/365 − 0.2388²·12/365 → m = 4.05%, expected |move| ≈ 3.23%. The Nov-04 straddle mid
15.775 = 4.54% of spot (includes 12 days of diffusion). Previous event (2026-07-30 AfterMarket): actual
R = 308.6438/333.1427 − 1 = −7.35%.

**Pitfalls.** The calendar date can move: re-read the calendar before the event. Weekly expiries may not
exist for small names; then only the straddle measure is available. Dividends inside the window distort
parity; ignore them for short windows.

**Acceptance checks.** A synthetic chain with base 25% and event sd 5% gives back σ_b = 0.25 and m = 0.05
from any two expiries. The output states the reaction-session rule used.

## A11. IV-crush scenarios

**Use when:** "what happens to this position after earnings if IV collapses?"

**Method.**
1. Estimate the event variance m² (A10).
2. For each leg with expiry T (after the event), post-event IV = `√((σ_pre(T)²·T − m²)/T)`, with T
   measured from now. This removes the event variance and keeps the base variance. If the radicand is ≤ 0,
   floor it at the pre-event base σ_b and flag it.
3. Re-time: after the event, T' = T − (days to the event session + 1)/365.
4. Spot scenarios `S·exp(z·m)` for z ∈ {−2, −1, 0, +1, +2}, plus the user's own levels.
5. Value each leg with BS (or A4) at (S_scen, T', σ_post). P/L = value − entry cost, × qty × multiplier.
6. Sensitivity rows: σ_post ± 2 vol points.

**Pitfalls.** Sticky-strike (each strike keeps its own IV shift) and sticky-delta give different results:
state which. The crush assumption is a model, and realized post-event IV can differ.

**Acceptance checks.** With m = 0, post-event IV equals pre-event IV and P/L is pure theta/delta. A long
straddle at z = 0 shows a loss ≈ vega × (σ_pre − σ_post) + theta.

## A12. Strategy P/L grid, breakevens, maximum loss, probability of profit

**Use when:** analysing covered calls, verticals, iron condors, straddles/strangles, calendars or
butterflies.

**Method.**
1. Legs: kind (call/put/stock), strike K, expiry T, entry price (mid, or the user's fill), quantity (+ long,
   − short), multiplier (100). Net entry cost = Σ qty·mult·entry (debit positive).
2. Grid: spots `S0·(1 + x)`, x from −20% to +20% in 2.5% steps (or ±3 expected moves). Dates: today,
   midpoints, the day before the first expiry, and expiry.
3. Value: for each grid cell, Σ qty·mult·BS(S, K, T − t, r, q, σ_leg) (sticky strike; σ_leg from entry).
   At expiry use intrinsic values. Calendars: value the back leg with BS at the front expiry.
4. P/L = value − net entry cost − fees (user-supplied).
5. Breakevens: at the final expiry, find sign changes of P/L on a fine grid and refine by bisection.
6. Maximum loss/gain at expiry: P/L is piecewise linear in S. Evaluate at S = 0, at every strike and at
   S = 10·max(K). Report "unbounded" when the slope beyond the largest strike is negative (short calls).
7. Probability of profit (model output): for a breakeven B,
   `P(S_T > B) = N(d2)` with `d2 = [ln(S/B) + (μ − q − σ²/2)T]/(σ√T)`. μ = r is risk-neutral; a
   user-supplied drift is labelled "assumed". Sum over profitable intervals.

```python
def strategy_value(legs, S, t_elapsed, r, q, iv_shift=0.0):
    total = 0.0
    for g in legs:
        if g["kind"] == "stock":
            total += g["qty"] * S
            continue
        T = g["T"] - t_elapsed
        if T <= 1e-9:
            v = max(S - g["K"], 0) if g["kind"] == "call" else max(g["K"] - S, 0)
        else:
            v = bsm(S, g["K"], T, r, q, max(g["iv"] + iv_shift, 1e-4), g["kind"])["price"]
        total += g["qty"] * g.get("mult", 100) * v
    return total
```

**Pitfalls.** Use the same r, q and IV as used to compute the entry, or the grid centre will not be zero.
American short legs can be assigned early (dividends); flag short calls with an ex-date before expiry.
EOD mids are not fills. Path-dependent payoffs (barriers, Asians) need Monte Carlo paths at the A6 volatility: use
A12b. The same lognormal formula gives P(L < S_T < U) = N(d2(L)) − N(d2(U)) for range questions
on any EODHD price series. That is a model probability; label it.

**Acceptance checks.** The grid at (S0, today) reproduces the entry value (P/L = −fees). The breakevens
of a long call are K + premium. A covered call's max loss is S0 − premium (at S = 0) and its max gain is
K − S0 + premium. A short naked call is "unbounded".

## A12b. Monte Carlo pricing for path-dependent payoffs (Asian, barrier) with variance reduction

**Use when:** a user asks for the model value of a payoff that depends on the price path. Examples are an
average-price (Asian) option, a knock-in or knock-out barrier, or a structured-note coupon with a barrier
observed on closes. EODHD chains contain only US listed (American, vanilla) options, so these prices cannot
be checked against a market quote. Every output is a **model price under GBM**: label it that way and
print the inputs.

**EODHD inputs.** Spot S0 = the underlying's raw `close` (A0). σ from A6 constant-maturity ATM IV at the
payoff's tenor. A8 realized vol is an alternative; label which one you used. r from UST bills/par
(B0, decimal, continuous: `ln(1 + y·τ)/τ` for a bill BEY y), or SOFR. q from the dividend yield (A0), or
discrete dividends with the escrowed spot (A2). Fixing dates come from the contract terms
(user-supplied). For daily fixings, use NYSE sessions from `/api/exchange-details/US`. Cost: the
inputs only (EOD 1 call; one chain if you take σ from A6).

**Method.**
1. Grid: fixing times `t_1 … t_n` in years from the contract terms. Use equal steps only when the fixings
   are equally spaced. Δt_j = t_j − t_{j−1}.
2. Paths (risk-neutral GBM, exact at the grid points):
   `S_{t_j} = S_{t_{j−1}}·exp((r − q − σ²/2)·Δt_j + σ·√Δt_j·Z_j)`, Z_j ~ N(0, 1), with a fixed seed.
3. Payoff per path, discounted with D = e^(−rT):
   - Arithmetic Asian call: `max(A − K, 0)`, where `A = (1/n)·Σ S_{t_j}`.
   - Geometric Asian call: `max(G − K, 0)`, where `G = exp((1/n)·Σ ln S_{t_j})`. It has a closed form
     (step 5).
   - Down-and-out call (barrier H < S0): `max(S_T − K, 0)` if `min_j S_{t_j} > H`, else 0. Down-and-in =
     the same payoff when the barrier was touched. The barrier is checked **only at the fixings**: this is
     discrete monitoring.
4. Estimator and error: price = mean of the discounted payoffs. Standard error SE = sample sd/√M, where M
   is the number of independent samples. Report price ± 1.96·SE, together with M, the seed and n.
5. Variance reduction (use at least one, and report the SE before and after):
   - **Antithetic:** for each Z, also simulate −Z. Average each pair first, then compute the mean and the
     SE over the pairs, because the two halves of a pair are not independent.
   - **Control variate:** `Y* = Y − b·(C − E[C])`, where `b = cov(Y, C)/var(C)` is estimated from the same
     paths. For the arithmetic Asian, use C = the discounted geometric Asian, with its closed form
     (discrete fixings `t_i = i·T/n`):
     `μ_G = ln S0 + (r − q − σ²/2)·T·(n+1)/(2n)`,
     `v_G = σ²·T·(n+1)(2n+1)/(6n²)`,
     `price_G = e^(−rT)·[e^(μ_G + v_G/2)·N(d1) − K·N(d2)]`, where `d1 = (μ_G − ln K + v_G)/√v_G` and
     `d2 = d1 − √v_G`.
     For a European payoff, use C = D·S_T with E[C] = S0·e^(−qT).
6. Barrier monitoring: match the contract. If the contract monitors continuously but you simulate daily
   fixings, shift the barrier to `H·exp(−0.5826·σ·√Δt)` for a down barrier. Use `exp(+0.5826·σ·√Δt)` for
   an up barrier. Label it "continuity correction (approximation)".
7. American exercise is not priced here. Use A4 for American vanillas.

```python
import math
import numpy as np

def gbm_paths(S0, r, q, sigma, T, n_steps, n_paths, seed=7, antithetic=True):
    """Risk-neutral GBM on an equal grid. Returns array (n_paths, n_steps) of S at t_1..t_n."""
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    half = n_paths // 2 if antithetic else n_paths
    z = rng.standard_normal((half, n_steps))
    if antithetic:
        z = np.concatenate([z, -z])                     # row i and row i+half are a pair
    incr = (r - q - 0.5 * sigma ** 2) * dt + sigma * math.sqrt(dt) * z
    return S0 * np.exp(np.cumsum(incr, axis=1))

def mc_price(disc_payoff, antithetic=True):
    """Mean and standard error; antithetic pairs are averaged first so the SE is honest."""
    x = disc_payoff
    if antithetic:
        h = len(x) // 2
        x = 0.5 * (x[:h] + x[h:])
    return x.mean(), x.std(ddof=1) / math.sqrt(len(x))

def control_variate(y, c, c_mean):
    """y: discounted payoffs, c: control payoffs with known mean c_mean. Returns adjusted sample and b."""
    b = np.cov(y, c, ddof=1)[0, 1] / c.var(ddof=1)
    return y - b * (c - c_mean), b

def geometric_asian_call(S0, K, T, r, q, sigma, n):
    """Closed form, n equally spaced fixings t_i = i*T/n (discrete geometric average)."""
    mu = math.log(S0) + (r - q - 0.5 * sigma ** 2) * T * (n + 1) / (2 * n)
    v = sigma ** 2 * T * (n + 1) * (2 * n + 1) / (6 * n * n)
    d1 = (mu - math.log(K) + v) / math.sqrt(v)
    d2 = d1 - math.sqrt(v)
    return math.exp(-r * T) * (math.exp(mu + 0.5 * v) * N(d1) - K * N(d2))   # N from A2

# usage: arithmetic Asian with a geometric control (252 daily fixings)
# P = gbm_paths(100, 0.05, 0.0, 0.20, 1.0, 252, 40_000); D = math.exp(-0.05)
# ya = D * np.maximum(P.mean(axis=1) - 100, 0); yg = D * np.maximum(np.exp(np.log(P).mean(axis=1)) - 100, 0)
# y_adj, b = control_variate(ya, yg, geometric_asian_call(100, 100, 1.0, 0.05, 0.0, 0.20, 252)); mc_price(y_adj)
```

Memory scales as paths × steps (40,000 × 252 doubles ≈ 80 MB per array). Simulate in batches of paths and
pool the batch means and variances, instead of allocating one large array.

**Pitfalls.**
- Computing the SE over 2M antithetic draws as if they were independent understates it. Use the pairs.
- Using the A6 30-day IV for a one-year payoff mixes tenors. Interpolate σ to the payoff's T.
- Barrier fixings on calendar days instead of sessions. Ignoring the monitoring mismatch.
- Spot from `adjusted_close`.
- A barrier price is very sensitive to σ near H, and GBM has no skew. Show a ±σ bump table rather than one
  number.
- A model price is not a quote. The listed chain cannot validate it.

**Acceptance checks (seed 7, numpy `default_rng`; S0 = K = 100, T = 1, r = 5%, q = 0, σ = 20%).**
- European call (one step) against BSM 10.4506. Plain MC with 100,000 paths: 10.4067, SE 0.0464.
  Antithetic: 10.4160, SE 0.0327. Antithetic + D·S_T control (b = 0.673): 10.4249, SE 0.0247. All three
  are within 3 SE of BSM, and each method lowers the SE.
- Geometric Asian, 252 fixings, 40,000 antithetic paths: closed form 5.5655, MC 5.5349 (SE 0.0268),
  within 3 SE.
- Arithmetic Asian on the same paths: 5.7498 (SE 0.0277) without the control. With the geometric control
  (b = 1.035): 5.7815 (SE 0.0011), about 24× lower SE. The arithmetic price is at least the geometric price.
- Down-and-out (H = 90, daily fixings) 8.8468 + down-and-in 1.5513 = vanilla on the same paths 10.3981.
  The in–out parity residual is 0.0 path by path.

## A13. Hedge-cost tables (protective put, collar, put spread)

**Use when:** a holder of a US stock/ETF asks what downside protection costs.

**Method.** For each tenor (e.g. 30/60/90/180 days → nearest listed expiries) and strike choice (by
% of spot or by delta):

| Structure | Net cost per share | Floor (max loss per share, from S0) | Cap | Breakeven at expiry |
|---|---|---|---|---|
| Protective put K_p | P(K_p) | S0 − K_p + P | none | S0 + P |
| Collar K_p < K_c | P(K_p) − C(K_c) (can be ≤ 0) | S0 − K_p + net | K_c − S0 − net | S0 + net |
| Put spread K_low < K_p | P(K_p) − P(K_low) | protection only between K_low and K_p | none | S0 + net |

Report the cost as % of spot and annualized (`cost% × 365/days`). Show executable-side pricing (pay ask,
receive bid) and mid side by side, plus OI, volume and relative spread for each leg.

**Pitfalls.** Concentrated-position tax effects and grant restrictions are user/jurisdiction inputs, not
EODHD data. Index puts (SPX) are not available; an ETF put (SPY) is a different contract.
Never pick strikes from a stale `tradetime` row without a two-sided quote.

**Acceptance checks.** A zero-cost collar has net ≈ 0 within one tick at mid. Floor + cap arithmetic
equals the expiry payoff evaluated at S = 0 and S = 10·S0.

## A14. Activity metrics (volume/OI, OI change, unusual activity)

**Use when:** building an "options activity" panel from EOD chains.

**Method.**
- Volume/OI per contract: `volume / open_interest`. Undefined when OI = 0: show "new/zero OI" instead
  of infinity. The vendor `vol_oi_ratio` is the same, rounded.
- ΔOI per contract: `OI_t − OI_{t−1}`. The vendor `open_interest_change` matched this in the probe.
  Recompute from two stored (or two retrieved) daily records and flag mismatches. On the first stored day
  of a contract it is "unavailable".
- Put/call ratios by volume and OI per expiry bucket (A5).
- Unusual-activity flag (declared thresholds): volume ≥ 3× the contract's trailing 20-session mean volume
  AND volume > OI AND volume ≥ 500 AND a two-sided quote on the observation date. Premium proxy =
  volume × mid × 100 (an EOD-mid estimate, not traded premium).
- Rank by premium proxy or ΔOI; show the observation date and spot.

**Pitfalls.** EOD data has no trade side, no sweep/block classification and no intraday timing. "Unusual"
means unusual volume or OI, not "bullish flow". OI is end-of-day position count with a clearing-house lag;
its exact as-of convention is not documented (verify). Exclude rows whose `tradetime` is older than the
observation date from volume-based ranks (no trades that day).

**Acceptance checks.** The first archived day gives ΔOI unavailable. A contract with `tradetime` older than
the observation date is excluded from activity ranks. Σ ΔOI per expiry equals the change in summed OI.

## A15. Gamma exposure (GEX), zero-gamma flip and walls

**Use when:** estimating a dealer-gamma regime, flip level and "gamma walls" for a US stock/ETF.

**EODHD inputs.** Full latest-day chain (A0 step 1, not `tradetime_eq`): `open_interest`, `gamma`,
`volatility`, `strike`, `type`, `exp_date`; underlying close; rate. Cost: the whole chain (all expiries).

**Method.**
1. Per contract, dollar gamma per 1% move:
   `GEX_i = sign_i · Γ_i · OI_i · M · S² · 0.01`, where M = 100 shares/contract and Γ is per share per USD.
   Derivation: Γ·OI·M is the change in shares of delta per 1 USD; × S × (0.01·S) is the USD delta change
   for a 1% move.
2. Sign convention (assumption, state it): dealers are long calls and short puts held by customers →
   calls +, puts −. Alternatives (all customer positions long, or a user-specified split) change the result;
   OI does not reveal who holds what.
3. Aggregate by strike and by expiry; net GEX = Σ GEX_i. Positive is labelled "dealer long gamma (model)".
4. Zero-gamma flip: for spot levels s on a grid (e.g. ±15% around S, step 0.5%), recompute every Γ_i with
   BS at s (keep each contract's IV and T fixed, sticky strike) and sum GEX(s). The flip is the linearly
   interpolated zero crossing nearest to S. If there is no crossing, report "none in range".
5. Walls: call wall = strike with the largest positive call GEX; put wall = strike with the largest |put
   GEX|. Report the top 3 of each with their share of |net|.
6. Use vendor gamma only at the current spot (step 1). Step 4 needs your own Γ.

```python
def gex_by_strike(chain, spot, r, q, use_vendor=True, mult=100):
    out = {}
    for c in chain:   # c: strike, type, oi, gamma (vendor), iv, T
        g = c["gamma"] if use_vendor else bsm(spot, c["strike"], c["T"], r, q, c["iv"], c["type"])["gamma"]
        sign = 1 if c["type"] == "call" else -1
        out[c["strike"]] = out.get(c["strike"], 0.0) + sign * g * c["oi"] * mult * spot * spot * 0.01
    return out

def gamma_flip(chain, r, q, grid):
    tot = [sum(gex_by_strike(chain, s, r, q, use_vendor=False).values()) for s in grid]
    for s1, g1, s2, g2 in zip(grid, tot, grid[1:], tot[1:]):
        if g1 == 0:
            return s1
        if g1 * g2 < 0:
            return s1 + (s2 - s1) * (-g1) / (g2 - g1)
    return None
```

**Boundaries to print with every GEX output.** EOD snapshot: OI is from the last session and positions
change intraday. No index options (SPX/SPXW/NDX/RUT/VIX), so SPY/QQQ GEX misses most index dealer exposure.
No OTC or flex positions. The dealer sign is an assumption. GEX is a positioning estimate, not a price
forecast.

**Pitfalls.** Contracts with zero or null IV must be recomputed or excluded (count them), otherwise their
gamma is 0. Expiring (T ≈ 0) contracts have huge gamma near the strike: report GEX with and without the
nearest expiry. A sparse chain (< 20 contracts with OI) gets a warning.

**Acceptance checks.** One ATM call (K = S = 100, 30 days, 30%, r = q = 0, OI 1): Γ = 0.04634 → GEX
463.4 USD per 1%. Synthetic chain with put 95 and call 105, OI 1,000 each, 30% IV, 30 days, S = 100:
strike GEX −378,096 and +404,286, net +26,190, flip ≈ 99.51. Σ strike GEX = net. Regime sign = sign of
net. The flip lies inside the strike range or is reported as "none".

## A16. Options boundaries

State these where relevant (they are facts about EODHD coverage, not soft caveats):
- US stocks and ETFs only. No SPX/SPXW/XSP/NDX/RUT/VIX/DJX index options, no VIX futures term structure,
  no non-US options.
- EOD snapshots only: no intraday chains, no trade-level prints, no trade side, sweeps, blocks or
  exchange-by-exchange flow, and no official NBBO certification.
- History from early Q4 2023; earlier IV rank/percentile, VRP or earnings-move history cannot be computed.
- No market-wide CBOE put/call ratio, no short-borrow or securities-lending data, no dealer positions.
- Vendor model inputs (rate, dividends, exercise style) are undocumented; recompute when they matter.

---

# Part B — Rates and fixed income

## B0. Data contract: UST curves, GBOND, policy/reference rates, funding stress, credit; unit table

**Use when:** any rates or credit computation starts.

**Endpoints and observed behaviour (probe 2026-10-25).**

| Series | Endpoint | Content | Calendar / frequency | Plan |
|---|---|---|---|---|
| UST nominal par curve | `/api/ust/yield-rates?filter[year]=YYYY` | rows `date, tenor, rate`. 14 tenors in 2026: 1M, 1.5M, 2M, 3M, 4M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y. A year request returned the whole year (2,856 rows) in one response | US bond-market days: 2026-10-12 (Columbus Day, NYSE open) has no row; 2026-04-03 (Good Friday, NYSE closed) has one | All plans per endpoint page (beta). The demo key is refused |
| UST real par curve | `/api/ust/real-yield-rates` | 5Y, 7Y, 10Y, 20Y, 30Y | same | same |
| UST bills | `/api/ust/bill-rates` | `tenor` 4WK…52WK, `discount`, `coupon` (bond-equivalent), `avg_*`, `maturity_date`, `cusip` | same | same |
| UST long-term | `/api/ust/long-term-rates` | `rate_type` BC_20year, Over_10_Years, Real_Rate | same | same |
| Government yields by country | `/api/eod/US10Y.GBOND` etc. | EOD rows; `close` is the yield (verify per symbol) | local market days | Fundamentals Feed or All-In-One |
| Policy rates | `/api/rates/policy-rates` (`filter[code]`, `[country]`, `[central_bank]`, `[from]`, `[to]`) | Observed codes (all codes on 2026-10-01): `FED_TARGET_LOWER`, `FED_TARGET_UPPER`, `ECB_DFR`, `ECB_MRO`, `ECB_MLF`, `BOE_BANK_RATE`. `filter[central_bank]=BOJ` returned 422 | daily (business days) | Fundamentals Feed / All-In-One |
| Reference rates | `/api/rates/reference-rates` (`filter[code]`, `[currency]`, `[from]`, `[to]`) | USD: `SOFR`, `EFFR`, `OBFR`, `BGCR`, `TGCR` (overnight, with `percentiles` p1/p25/p75/p99 and `volume_billion_usd`), `SOFR30D/90D/180D` (backward-looking averages), `SOFRINDEX` (an index level, not a rate). EUR: `ESTR`. GBP: `SONIA` | daily; the latest SOFR row on 2026-10-25 was 2026-10-22 (published next business day) | same |
| Funding stress | `/api/spreads/funding-stress` (`filter[code]`, `[from]`, `[to]`) (no pagination) | `EFFR_SOFR`, `OBFR_EFFR`, `TGCR_BGCR`, `SOFR_TARGET_LOWER`, `EFFR_TARGET_MID`, `TARGET_UPPER_SOFR`; `value_bps`, legs in percent | daily | same |
| HQM corporate curve | `/api/credit-risk/corporate/hqm-yields` (`filter[tenor]`, `[type]`, `[from]`, `[to]`) | par or spot, tenors 1–30 years | **monthly** (stamped first of month, e.g. `2026-09-01T00:00:00+00:00`) | same |
| Corporate distress index | `/api/credit-risk/corporate/cmdi` | `market_cmdi`, `ig_cmdi`, `hy_cmdi`; the response meta names the NY Fed corporate bond market distress index | **weekly** (Fridays); latest on 2026-10-25 was 2026-09-25 | same |
| Sovereign CDS, ratings, default spreads, risk premium | `/api/credit-risk/sovereign/*` | see B8 | **annual** snapshot (`as_of_date` 2026-01-01 for ITA CDS) | same |

**Unit table (normalize once, at ingestion).**

| Field | Unit | To decimal |
|---|---|---|
| UST `rate`, bill `discount`/`coupon`, policy/reference `rate`, HQM `yield_value`, funding legs | percent | ÷ 100 |
| funding `value_bps` | basis points | ÷ 10,000 |
| sovereign `cds_spread`, `default_spread`, `country_risk_premium`, `equity_risk_premium`, `corporate_tax_rate` | fraction (0.0061 = 61 bp) | as is |
| `SOFRINDEX` | index level | not a rate; compounded SOFR between dates d1 < d2 = (I2/I1 − 1)·360/days |
| CMDI | index level (0–1 in the probe; verify scale) | as is |
| CDS market aggregates `usd_notional_mn` | USD millions | × 1e6 |

Changes are in basis points: 1 bp = 0.01 percentage point = 0.0001 decimal.

**Pitfalls.**
- Treasury changed the tenor set over time (for example, 2M from 2018, 4M from 2022 and 1.5M from 2025;
  30Y absent 2002–2006). Count tenors per date before computing slopes. A missing tenor is missing, not
  interpolated, unless you label it.
- Join rates to equity data with an as-of rule, not an inner join on dates (bond and stock holidays differ).
- Overnight reference rates for day D appear on D+1.

**Acceptance checks.**
- Each stored curve row has date, tenor, value and unit, and the tenor count per date is logged.
- A bill check passes: `coupon ≈ 365·d/(360 − d·t)` with d = discount (decimal) and t = days to
  maturity (≤ 182 days). The endpoint-page example (discount 3.58, 32 days) gives 3.64, matching its
  `coupon`.

## B1. Curve slopes, butterflies and shape labels

**Use when:** building a curve monitor or labelling the curve state.

**Method.** Using par yields `y(T)` in percent on one date, with differences in bp:

| Measure | Formula |
|---|---|
| 2s10s | (y10 − y2) × 100 |
| 3m10y | (y10 − y3M) × 100 |
| 5s30s | (y30 − y5) × 100 |
| 2s5s10s butterfly | (2·y5 − y2 − y10) × 100 (positive = belly cheap) |
| Change over horizon h | value(t) − value(t − h) on matched bond-market days (−1M, −3M, −1Y) |
| Bull/bear steepening/flattening | sign of Δ2y, Δ10y and Δ(2s10s): bull = yields down, bear = up; steepener = slope up |

Shape label (declared thresholds; tune and keep them in config):
1. If 2s10s < −10 bp **and** 3m10y < 0, the label is **inverted**.
2. Else, if |2s10s| ≤ 25 bp, the label is **flat**.
3. Else, if max(y2…y7) − max(y3M, y10) > 10 bp, the label is **humped**.
4. Otherwise the label is **normal** (upward sloping).

**Worked example (probe, 2026-10-23).** y3M 4.22, y2 4.69, y5 4.82, y10 5.00, y30 5.33:
2s10s +31 bp, 3m10y +78 bp, 5s30s +51 bp, butterfly −5 bp → "normal". Against 2026-09-23 (y2 4.85,
y10 5.11): Δ2y −16 bp, Δ10y −11 bp, Δ2s10s +5 bp → bull steepening. Note 20Y (5.37) > 30Y (5.33):
a local hump at the long end.

**Pitfalls.** Comparing a GBOND tenor to a UST par tenor mixes instruments: keep each country's own
source. Do not compute percent changes of yields.

**Acceptance checks.** A missing 2Y makes 2s10s unavailable (not computed from 1Y). Changes are in bp and
levels in percent, with the unit visible in the column name.

## B2. Bootstrapping zero (spot) rates and forwards from the UST par curve

**Use when:** discounting user cash flows, computing forwards, or Z-spreads (B5).

**Method.**
1. Inputs: par yields for tenors ≥ 6M from one date, as decimals. Treat them as semiannual
   bond-equivalent par yields; the 6M point is a zero rate with semiannual compounding.
2. Interpolate par yields linearly onto a semiannual grid 0.5, 1.0, …, 30.0 years (state the method;
   monotone cubic is an alternative).
3. Bootstrap discount factors. With c = y(t)/2:
   `DF(0.5) = 1/(1 + c)`; for t > 0.5, `DF(t) = (1 − c·Σ_{u<t} DF(u)) / (1 + c)`.
4. Zero rate (semiannual): `z(t) = 2·(DF(t)^(−1/(2t)) − 1)`; continuous: `−ln DF(t)/t`.
5. Forward between t1 < t2 (semiannual): `f = 2·((DF(t1)/DF(t2))^(1/(2(t2 − t1))) − 1)`.
6. Tenors below 6M (bills) are money-market points; use them only for a separate short-end curve.

```python
def bootstrap_par_curve(par):
    """par: {maturity_years: par_yield_decimal} for maturities >= 0.5. Returns {t: DF} on a 0.5y grid."""
    mats = sorted(par)
    def par_at(t):
        if t <= mats[0]:
            return par[mats[0]]
        for a, b in zip(mats, mats[1:]):
            if a <= t <= b:
                return par[a] + (par[b] - par[a]) * (t - a) / (b - a)
        return par[mats[-1]]
    grid = [0.5 * i for i in range(1, int(round(mats[-1] * 2)) + 1)]
    df = {}
    for t in grid:
        c = par_at(t) / 2
        df[t] = 1 / (1 + c) if t <= 0.5 else (1 - c * sum(df[u] for u in grid if u < t)) / (1 + c)
    return df

zero = lambda t, d: 2 * (d ** (-1 / (2 * t)) - 1)
fwd = lambda t1, d1, t2, d2: 2 * ((d1 / d2) ** (1 / (2 * (t2 - t1))) - 1)
```

**Worked example (probe 2026-10-23 curve).** Zero rates: 1Y 4.442%, 2Y 4.698%, 5Y 4.831%,
10Y 5.036%, 20Y 5.552%, 30Y 5.411%. Forwards: 1y1y 4.954%, 5y5y 5.241%. The 10y10y (6.07%) and
20y10y (5.13%) forwards amplify the 20Y hump and the linear-interpolation kinks, so treat forwards beyond
20Y as fragile.

**Pitfalls.** Par yields are not zero rates: a 10Y par yield of 5.00% gives a 5.036% zero. Discount
factors must decrease with t while rates are positive. A missing interior tenor silently widens the
interpolation span, so log it.

**Acceptance checks.** A flat 4% par curve gives 4% zero rates and 4% forwards at every tenor. Repricing
each input par bond (coupon = par yield) with the bootstrapped DFs gives 100.000. Σ DF·coupon + DF(T)
reproduces 1.

## B3. Price, yield, duration, DV01 and convexity for user-supplied bonds

**Use when:** a user supplies bond terms (coupon, maturity, frequency, price or yield) and wants risk
measures or rate-shock P/L. EODHD does not supply individual bond cash-flow schedules, prices or call
schedules (see B10). Optional context: `ETF_Data` duration/YTM for bond ETFs, PRAAMS bond analytics by
ISIN (Marketplace, separately entitled; probe each ISIN).

**Method (cash-flow form, yield y decimal, frequency f).**
- Cash flows `(t_i, CF_i)` in years from settlement. User-supplied, or generated for a bullet bond. Use
  the stated day count: ACT/ACT for Treasuries, 30/360 for most US corporates.
- Dirty price `P = Σ CF_i / (1 + y/f)^(f·t_i)`; clean = dirty − accrued (accrued = coupon/f × fraction
  of the current period elapsed).
- Macaulay `D_mac = Σ t_i·PV_i / P`; modified `D_mod = D_mac/(1 + y/f)`.
- Convexity `C = Σ CF_i·t_i·(t_i + 1/f)/(1 + y/f)^(f·t_i + 2) / P` (years²).
- DV01 per 100 face `= D_mod·P·0.0001`; in currency = DV01 × face/100.
- Shock P/L approximation: `ΔP/P ≈ −D_mod·Δy + 0.5·C·Δy²` (Δy decimal). Also report full repricing.
- Effective duration/convexity by bumping (use them for callable bonds only with a user-supplied model):
  `D_eff = (P− − P+)/(2·P·Δy)`, `C_eff = (P− + P+ − 2P)/(P·Δy²)`.
- Portfolio: MV-weighted YTM and D_mod (state the convention); total DV01 = Σ DV01_i; maturity buckets.
- Yield to worst (user-supplied call schedule): for each call date j, truncate the cash flows at that date and
  replace the principal with call price_j; solve the yield to call with `ytm_from_price`. YTW = min(YTM, all YTC_j).
  This is a deterministic bound, not an option-adjusted measure.

```python
def price_from_yield(cfs, y, f=2):
    return sum(cf / (1 + y / f) ** (f * t) for t, cf in cfs)

def ytm_from_price(cfs, dirty, f=2, lo=-0.05, hi=1.0):
    g = lambda y: price_from_yield(cfs, y, f) - dirty
    if g(lo) < 0 or g(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if g(mid) > 0 else (lo, mid)
    return (lo + hi) / 2

def risk_measures(cfs, y, f=2):
    P = price_from_yield(cfs, y, f)
    mac = sum(t * cf / (1 + y / f) ** (f * t) for t, cf in cfs) / P
    conv = sum(cf * t * (t + 1 / f) / (1 + y / f) ** (f * t + 2) for t, cf in cfs) / P
    mod = mac / (1 + y / f)
    return dict(price=P, macaulay=mac, modified=mod, convexity=conv, dv01=mod * P * 1e-4)
```

**Pitfalls.** Mixing percent and decimal yields (D_mod × 1.0 instead of × 0.01 overstates the move by
100×). Using clean price in the yield solve: use dirty. Applying a portfolio-level duration to ETF prices
ignores the fund's rolling maturity.

**Acceptance checks.** 10-year 4% semiannual bullet at 4%: P = 100.000, D_mac 8.3392, D_mod 8.1757,
C 78.898, DV01 0.08176 per 100. +100 bp: full reprice 92.2054, approximation 92.2188. YTM solved from
P = 100 returns 4.0000%.

## B3b. Bond portfolio cash-flow waterfall

**Use when:** a user with a bond portfolio wants to know how much coupon and principal arrives in each
period, for income planning, ladder gaps or a liability match. The table must tie to the maturity
buckets from B3. Every schedule is **user-supplied** or generated from user-supplied terms. EODHD has no
individual-bond schedules, call or sinking-fund terms, or amortization tables (B10).

**EODHD inputs.** None are needed for the cash flows. Optionally:
- Discount factors from B2 (UST par curve, 1 call per year of data) for a PV column. Label the PV
  "Treasury-curve PV", not "market value".
- `*.FOREX` closes for converting foreign-currency bonds. Convert at a stated spot date: this is a
  translation, not a forecast.

**Method.**
1. Per bond, either take the user's dated schedule `(date, coupon_cf, principal_cf)` (amortizing,
   sinking-fund, step-up or floating with user-projected coupons), or generate a fixed-rate bullet:
   - coupon dates step back from maturity every 12/f months;
   - coupon = face·c/f;
   - principal = face at maturity;
   - keep only dates after settlement.
   Use unadjusted dates unless the user supplies a business-day rule.
2. Callable bonds: the default is to maturity. Run a second waterfall to the call date when a user-supplied
   call is "in the money" (YTW < YTM in B3). Show both; never mix them silently.
3. Bucket each cash flow by period: calendar year, quarter or month, or the user's fiscal year. Sum the
   coupon and principal per bucket. Total = coupon + principal. Add a cumulative column.
4. Add the bonds that mature in each bucket. For bullets, principal in a bucket = Σ face maturing there.
   This is the tie-out to the B3 maturity buckets. Amortizing principal appears in earlier buckets and is
   listed separately.
5. Optional PV column: Σ CF·DF(t), with DF from B2 interpolated at t in years from settlement.
6. Coupons are shown in full on payment dates. The accrued interest paid at purchase is a separate
   outflow, not a reduction of the first coupon. Reinvestment is not assumed. If you show a reinvestment
   line, it is a labelled scenario (B7 rule).

```python
import datetime as dt
from collections import defaultdict

def add_months(d, m):
    y, mo = divmod(d.month - 1 + m, 12)
    y += d.year; mo += 1
    last = [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1]
    return dt.date(y, mo, min(d.day, last))

def bullet_schedule(face, coupon, maturity, freq, settle):
    """Dated (date, coupon_cf, principal_cf) after settlement for a fixed-rate bullet bond."""
    rows, k = [], 0
    while True:
        d = add_months(maturity, -k * 12 // freq)
        if d <= settle:
            break
        rows.append((d, face * coupon / freq, face if k == 0 else 0.0))
        k += 1
    return sorted(rows)

def waterfall(bonds, settle, bucket=lambda d: d.year):
    """bonds: dicts with 'id' and either 'cfs' (user schedule) or face/coupon/maturity/freq."""
    table = defaultdict(lambda: {"coupon": 0.0, "principal": 0.0, "maturing": []})
    for b in bonds:
        cfs = b.get("cfs") or bullet_schedule(b["face"], b["coupon"], b["maturity"], b["freq"], settle)
        last = max(d for d, _, _ in cfs)
        for d, c, p in cfs:
            row = table[bucket(d)]
            row["coupon"] += c
            row["principal"] += p
            if p and d == last:
                row["maturing"].append(b["id"])
    out, cum = [], 0.0
    for k in sorted(table):
        r = table[k]
        tot = r["coupon"] + r["principal"]
        cum += tot
        out.append((k, round(r["coupon"], 2), round(r["principal"], 2), round(tot, 2), round(cum, 2), r["maturing"]))
    return out
```

**Pitfalls.**
- Generating coupons forward from the settlement date instead of backward from maturity (wrong dates and
  wrong odd first coupon).
- Mixing currencies in one column: keep one waterfall per currency, or convert at one stated spot date.
- A user-supplied floating-rate coupon projection is an assumption. Label it, for example "SOFR flat at
  the latest `reference-rates` value".
- Showing calls as certain.

**Acceptance checks (synthetic, settlement 2026-10-30).** The portfolio:
- A: 100,000 face, 4% semiannual, matures 2028-05-15.
- B: 250,000 face, 5.25% semiannual, matures 2031-02-15.
- C: 150,000 face, 3% annual, matures 2029-11-30.
- D: user schedule of 50,000 principal plus 2,000 coupon on 2027-06-01, and 50,000 plus 1,000 on
  2028-06-01.

| Year | Coupon | Principal | Total | Cumulative | Maturing |
|---|---|---|---|---|---|
| 2026 | 6,500.00 | 0 | 6,500.00 | 6,500.00 | |
| 2027 | 23,625.00 | 50,000 | 73,625.00 | 80,125.00 | |
| 2028 | 20,625.00 | 150,000 | 170,625.00 | 250,750.00 | A, D |
| 2029 | 17,625.00 | 150,000 | 167,625.00 | 418,375.00 | C |
| 2030 | 13,125.00 | 0 | 13,125.00 | 431,500.00 | |
| 2031 | 6,562.50 | 250,000 | 256,562.50 | 688,062.50 | B |

Σ principal = 600,000 = Σ face. Σ coupon = 88,062.50 = 8,000 (A, 4 coupons) + 59,062.50 (B, 9 coupons)
+ 18,000 (C, 4 coupons) + 3,000 (D). The bullet principal in 2029 and 2031 equals the B3 maturity-bucket
face (C 150,000; B 250,000). The 2026 row holds only the A and C coupons (B pays in February and August).

## B4. Breakeven inflation and real-rate regime

**Use when:** "what inflation is the Treasury market pricing?" or a real-rate dashboard.

**Method.**
- Breakeven `BE(T) = y_nominal(T) − y_real(T)` in percentage points, same date and tenor, for T ∈
  {5, 7, 10, 20, 30} (the real curve has no shorter tenors).
- 5y5y forward breakeven ≈ `(10·BE10 − 5·BE5)/5 = 2·BE10 − BE5` (linear approximation; the exact
  version bootstraps both curves with B2 and differences the 5y5y forwards).
- Real-rate regime from the 10Y real yield, with declared thresholds: < 0 negative, 0–1 low, 1–2 moderate,
  > 2 high. Report its 1M/1Y change in bp.

**Worked example (probe 2026-10-23).** Nominal 5Y/10Y/30Y 4.82/5.00/5.33; real 2.34/2.66/3.08 →
BE5 2.48, BE10 2.34, BE30 2.25 pp. 5y5y ≈ 2.20 pp. 10Y real 2.66% → "high".

**Pitfalls.** Breakeven includes inflation risk premium, TIPS liquidity premium and the inflation-index
lag; label it "market-implied breakeven", not "expected inflation". Do not compare with annual CPI from
`macro-indicator` without stating the period mismatch.

**Acceptance checks.** BE is computed only where both tenors exist on the same date. A 2Y breakeven
request returns unavailable. Units are pp for levels and bp for changes.

## B5. G-spread, Treasury-curve Z-spread and corporate credit context

**Use when:** comparing a user-supplied corporate or agency bond yield with Treasuries.

**Method.**
1. G-spread (bp) = `(YTM_bond − y_UST(T_bond)) × 10,000`, where y_UST is the par yield on the **same
   date** linearly interpolated at the bond's remaining maturity in years.
2. Treasury-curve Z-spread: the constant s added to the bootstrapped Treasury zero curve (B2, semiannual)
   such that `Σ CF_i / (1 + (z(t_i) + s)/2)^(2·t_i) = dirty price`. Solve by bisection. This is not a
   swap-curve Z-spread, so label it.
3. Context series:
   - HQM corporate par curve minus the UST par curve at the same tenor. HQM is monthly, so compare it
     with the **monthly average** of daily UST par yields for that month. This gives a high-quality
     corporate spread level.
   - CMDI (weekly) for market-wide stress.
   - `ETF_Data` YTM/duration of IG/HY bond ETFs as current-only proxies.
4. Scenario P/L for ±50/100/200 bp parallel shifts, and for spread ±25/50 bp holding the curve: B3 full
   repricing.

```python
def z_spread(cfs, dirty, df_at, f=2):
    """df_at(t): Treasury discount factor interpolated from bootstrap_par_curve (interpolate zero rates)."""
    def pv(s):
        return sum(cf / (1 + (f * (df_at(t) ** (-1 / (f * t)) - 1) + s) / f) ** (f * t) for t, cf in cfs)
    lo, hi = -0.05, 0.5
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if pv(mid) > dirty else (lo, mid)
    return (lo + hi) / 2
```

**Worked example (synthetic bond on the 2026-10-23 curve).** 7-year 5.5% semiannual bond at dirty
101.20 → YTM 5.293%. The 7Y UST par yield is 4.89%, so the G-spread is +40.3 bp; the Treasury Z-spread is
+40.5 bp.

**Pitfalls.** Mismatched dates (bond price from one day, curve from another). Comparing an HQM spot rate
with a UST par rate. Using HQM or CMDI as an issuer's credit spread: they are market aggregates. OAS needs
a call schedule and a rate-volatility model; it is not provided, and a computed value is a user model.

**Acceptance checks.** A Treasury par bond priced at 100 off the same curve has Z-spread 0 ± 0.01 bp.
A bond maturing exactly on a tenor uses that tenor's yield without interpolation.

## B6. DV01-neutral steepener/flattener sizing

**Use when:** expressing a curve view (2s10s, 5s30s) without a net parallel-rate exposure. Government-curve
analogue only; swap curves are not available.

**Method.** For legs A (short tenor) and B (long tenor) with DV01 per 100 face from B3 (par bonds at the
current par yields, or the user's actual bonds):
`Face_B = Face_A · DV01_A / DV01_B`. Steepener = long A / short B; flattener = the reverse.
P/L ≈ DV01_A(currency) × (Δy_B − Δy_A) in bp for the steepener (positive when the curve steepens).
Report the residual P/L for a parallel shift: it should be ≈ 0 to first order, with a convexity residual.

**Worked example (2026-10-23 par yields).** DV01 per 100 face: 2Y at 4.69% → 0.018880; 10Y at 5.00% →
0.077946. A 10,000,000 face 2Y position needs 2,422,236 face of 10Y. The DV01 is 1,888 USD per bp on each
leg.

**Pitfalls.** DV01 changes with yields: re-hedge ratios on each date. Repo/financing and futures basis
are user inputs (not EODHD).

**Acceptance checks.** A +10 bp parallel shift produces |P/L| < 1% of the DV01 × 10 bp of one leg. A
+10 bp steepening gives ≈ +10 × DV01 of a leg.

## B7. Treasury and TIPS ladders (indicative)

**Use when:** planning a ladder that funds known yearly cash needs.

**EODHD inputs.** UST par curve (B2 discount factors), bill rates for rungs under 1 year, and the real par
curve for TIPS (5Y+). Individual CUSIP prices for notes/bonds are not supplied; bill CUSIPs appear in
`bill-rates`.

**Method.**
1. Liabilities `L_k` for years k = 1…N (nominal or real, user-supplied).
2. Zero-coupon approximation: cost = Σ L_k·DF(k) (nominal, B2). For a real ladder, discount real
   liabilities with real zero rates bootstrapped from the real par curve (5–30Y only). Rungs below 5Y have
   no EODHD real yield: mark them unavailable or use a user-supplied assumption.
3. Coupon-bond ladder (annual-coupon simplification, par bonds at par yields c_k), solved from the
   longest rung down: `F_N = L_N/(1 + c_N)`; `F_k = (L_k − Σ_{j>k} c_j·F_j)/(1 + c_k)`. Cost = Σ F_k
   (at par).
4. Show each rung: maturity, face, coupon, cost, cash flow by year, and the yield source date.

**Worked example (2026-10-23, L = 10,000 per year for 5 years).** Zero-coupon cost 43,518. Coupon ladder
faces (year 5 → 1): 9,540; 9,105; 8,692; 8,302; 7,949 (4Y coupon interpolated between 3Y and 5Y); total
43,588. Each year's inflow equals 10,000.

**Liquidity tiers, blended ladder yield and the reinvestment rule.**
1. Tiers (the horizons and amounts are user-declared):

   | Tier | Purpose | Instrument | Yield source |
   |---|---|---|---|
   | 0 Cash | Spending over the next 0–3 months, plus the emergency reserve | Deposit, money-market fund | User-supplied deposit rate. SOFR/€STR/SONIA (`reference-rates`) as context only |
   | 1 Bills | Needs 3–12 months out | T-bills | `bill-rates` `coupon` (bond-equivalent) per tenor |
   | 2 Ladder | Needs 1–N years out | Notes/TIPS rungs (method above), or CDs | B2/B7 par yields. CD rates are **user-supplied** (EODHD has no bank or brokered-CD rates) |
   | 3 Growth | Beyond N years | Portfolio | Not a liquidity tier |

   Size each tier from the user's liabilities L_k, and show the coverage in months of essential spending.
2. Blended ladder yield. Report three numbers and label each:
   - cost-weighted average yield `Σ C_k·y_k / Σ C_k` (simple; it understates when the curve is upward
     sloping);
   - duration-weighted average yield `Σ D_k·y_k / Σ D_k`;
   - **portfolio yield** = the IRR of the combined ladder cash flows against the total cost. This is the
     headline number.
3. CD versus Treasury on an after-tax basis. Treasury interest is exempt from state tax, CD interest is
   not. With user-supplied marginal rates t_f and t_s, the CD yield that matches a Treasury yield y_T
   is `y_CD* = y_T·(1 − t_f)/(1 − t_f − t_s)` (this ignores deductibility interactions; label it).
4. Reinvestment rule (declared, one of):
   - **funding ladder:** maturing rungs are spent, nothing is reinvested;
   - **rolling ladder:** each maturing rung buys a new N-year rung.
   A rolling ladder needs an assumed future yield. Use either today's B2 forward rate for that date or the
   current par yield ± a stated shift. Label it "reinvestment assumption", never a forecast. Re-run B7 on
   the actual curve on the reinvestment date and record that date.

**Pitfalls.** These are indicative yields, not executable prices. Taxes and inflation indexation lag are
user/jurisdiction inputs. Do not treat TIPS breakeven as guaranteed real income. Bill `discount` is not a
yield: use `coupon` (bond-equivalent) when comparing bills with notes. Do not show the cost-weighted
average as "the ladder yield".

**Acceptance checks.** The cash-flow table reproduces L_k exactly in every year. Cost rises when the curve
falls. Unavailable real rungs are listed. Five annual-coupon rungs bought at par (face 10,000 each;
1–5Y yields 4.00/4.10/4.20/4.30/4.40%) have cash flows 12,100; 11,700; 11,290; 10,870; 10,440 against a
cost of 50,000. The cost-weighted yield is 4.2000%, the duration-weighted yield 4.2633% and the IRR
4.2635%. A flat curve makes all three equal. A 4.20% Treasury with t_f = 24% and t_s = 6% needs a CD
yield of 4.56%.

## B8. Credit and sovereign-risk endpoints: what each one is for

| Endpoint | Key fields | Use for | Not for |
|---|---|---|---|
| `credit-risk/corporate/hqm-yields` | `tenor_years`, `yield_type` par/spot, `yield_value` %, `as_of_date` (monthly) | Discounting long-dated liabilities; high-quality corporate term structure; HQM − UST spread (monthly averages) | Daily trading signals; issuer spreads |
| `credit-risk/corporate/cmdi` | `market_cmdi`, `ig_cmdi`, `hy_cmdi` (weekly) | Corporate-bond market stress regime; composite risk index input (C8) | Default probability of a named issuer |
| `credit-risk/cds-market/aggregates` | `metric`, `breakdown_dimension` grade/cleared_status, `usd_notional_mn`, `as_of_date`, `release_date` | Structural CDS-market size and clearing share | Spreads or pricing |
| `credit-risk/sovereign/cds-spreads` | `cds_spread`, `cds_spread_net_of_switzerland` (fractions), `moodys_rating`, annual `as_of_date`; null where no liquid market | Country risk context; cost-of-equity inputs | Daily sovereign CDS moves |
| `credit-risk/sovereign/credit-ratings` | Moody's/S&P/Fitch strings | Rating screens and mapping to default spreads | Point-in-time rating history (snapshot; check `as_of`) |
| `credit-risk/sovereign/default-spreads` | `rating`, `default_spread` (fraction) | Rating → spread lookup for cost of debt | Market-observed spread |
| `credit-risk/sovereign/risk-premium` | `country_risk_premium`, `equity_risk_premium`, `adj_default_spread`, `corporate_tax_rate` (fractions) | WACC / cost-of-equity build-ups ([valuation.md](valuation.md)) | Live market data |

Countries use ISO-3 codes (`USA`, `ITA`); names are not matched. Keep `as_of_date` with every value and
show its frequency. Expected loss for a user-supplied exposure is `EL = PD × LGD × EAD`, with all three
user-supplied or labelled assumptions (a rating-mapped default spread is not a PD).

## B9. Money-market funding stress and the policy-rate path

**Use when:** monitoring funding conditions or summarising the policy-rate path.

**Method.**
- Policy path: daily `FED_TARGET_LOWER`/`UPPER` (midpoint = average), `ECB_DFR`/`MRO`/`MLF`,
  `BOE_BANK_RATE`. Derive change events where the rate differs from the previous row. Cross-check against
  economic-events rows such as "Fed Interest Rate Decision": in the probe, `actual` 4 on 2026-09-16 equals
  `FED_TARGET_UPPER`. Other central banks: use economic-events "… Interest Rate Decision" rows (verify the
  `type` string per country) and label the source.
- Funding stress: read `/spreads/funding-stress` directly (bp), or recompute from reference rates:
  SOFR − target lower bound, EFFR − target midpoint, TGCR − BGCR, OBFR − EFFR. Flag days where SOFR's
  p99 percentile exceeds the upper bound.
- Distribution: SOFR p1–p99 spread and `volume_billion_usd` show dispersion and depth.

**Pitfalls.** SOFR/EFFR for day D arrive on D+1. Month-end and quarter-end spikes are calendar effects:
show them, but compare with the same calendar point in prior periods.

**Acceptance checks.** Recomputed `EFFR_TARGET_MID` matches `value_bps` (0.5 bp on 2026-10-22: EFFR
3.88 − 3.875). Change events reproduce the decision dates in economic events.

## B10. Rates and credit boundaries

- No swap curves, swap spreads, OIS/term SOFR curves, inflation swaps, cross-currency basis or swaptions.
  Offer the Treasury-curve analogue (B1, B2, B6) and label it.
- No futures-implied policy paths (fed funds/SOFR futures probabilities), and no bond futures CTD/implied repo.
- No individual-bond cash-flow schedules, covenants, call/put schedules, maturity walls or issuer debt
  stacks. Corporate `.BOND` tickers are sparse (probe per ISIN); PRAAMS bond analytics are a separately
  entitled Marketplace product.
- No municipal bond data (a tax-equivalent yield needs a user-supplied muni yield; muni-ETF `ETF_Data` YTM
  is a labelled current proxy), no MBS/ABS/CLO pool or tranche data.
- No OAS, key-rate durations of callables or issuer-level CDS. Sovereign CDS is an annual snapshot.
- Policy rates cover the Fed, ECB and BoE in `rates/policy-rates` (probe 2026-10-25); reference rates
  cover USD, EUR (€STR) and GBP (SONIA) only.
- No bank deposit or CD rates. They are user inputs (B7 tiers).

**User-input modules for requests that land on a boundary.** Each one runs only on values the user
supplies, uses EODHD for context, and labels its output.

*Bond-futures basis and implied repo.* The user supplies:
- futures price F;
- conversion factor CF (from the exchange's contract specifications);
- the deliverable bond's clean price and accrued interest now (AI_0);
- accrued interest at delivery (AI_d);
- days to delivery d;
- any coupon c paid before delivery.

All prices are per 100 face.

```
gross basis   = clean − F·CF
carry         = (AI_d + c − AI_0) − dirty·repo·d/360            dirty = clean + AI_0
net basis     = gross basis − carry
implied repo  = (F·CF + AI_d + c − dirty)/dirty · 360/d          (interim coupon not reinvested)
```

The repo rate is user-supplied. If it is missing, use SOFR or TGCR from `reference-rates` as an
overnight general-collateral proxy, labelled as such: a term or special repo can differ. Identity check:
net basis = (repo − implied repo)·dirty·d/360. Run it for each deliverable bond the user lists. The
cheapest-to-deliver is the bond with the highest implied repo. That ranking is only as complete as the
user's list. Synthetic check: clean 98.50, AI_0 1.20, F 115.20, CF 0.8520, AI_d 1.8575, d = 60, repo
3.90%. The result is gross basis 0.3496, carry 0.00945, net basis 0.34015 and implied repo 1.853%, and the
identity holds.

*Tax-equivalent yield.* `TEY = y_muni/(1 − t)`, where t is the user's combined marginal rate. If the muni is
exempt from state tax but the comparison bond is not, use
`t = t_f + t_s·(1 − t_f)` (state tax deductible) or `t_f + t_s` (not deductible). State which.
y_muni is user-supplied. A muni-ETF `ETF_Data` YTM is a current proxy only. Check: 3.00% at t = 32% →
TEY 4.41%.

---

# Part C — FX and macro

## C1. Covered-interest-parity forward and hedged returns

**Use when:** estimating a theoretical FX forward, forward points, or a currency-hedged return. EODHD has
no FX forwards or forward points, so every output here is a **theoretical CIP value**, not an executable
rate.

**EODHD inputs.** Spot `/api/eod/EURUSD.FOREX` (`close`, USD per 1 EUR). Rates from
`/api/rates/reference-rates`: `SOFR` (USD), `ESTR` (EUR), `SONIA` (GBP), or policy rates. Other
currencies have no reference/policy rate there (probe 2026-10-25): a short-tenor `.GBOND` yield, if
present for that country, is a substitute (verify with a probe request), otherwise the method is
unavailable.

**Method.** For a pair quoted as quote-currency units per 1 base-currency unit (EURUSD: base EUR, quote
USD), simple money-market rates r_q, r_b (decimals) and year fraction τ (ACT/360 for USD and EUR,
ACT/365 for GBP):

```
F = S · (1 + r_q·τ_q) / (1 + r_b·τ_b)          forward points = (F − S) × 10^4 (pips for 4-decimal pairs)
Hedged return of a base-currency asset for a quote-currency investor, hedging the initial value:
R_hedged = (F/S − 1) + R_local · S_T/S          (exact for this hedge)
         ≈ R_local + (r_q − r_b)·τ              (approximation)
Unhedged:  R_unhedged = (1 + R_local)·S_T/S − 1
```

Using overnight rates for a 3M horizon assumes they stay flat; label it "overnight-rate approximation".
The cross-currency basis is not available and is set to 0; label that as well.

```python
def cip_forward(spot, r_quote, r_base, days, basis_quote=360, basis_base=360):
    return spot * (1 + r_quote * days / basis_quote) / (1 + r_base * days / basis_base)

def hedged_return(r_local, spot0, spot_T, fwd):
    return (fwd / spot0 - 1) + r_local * spot_T / spot0
```

**Worked example (probe values).** EURUSD close 1.12023 (2026-10-23). SOFR 3.90%, €STR 2.442%
(2026-10-22). 92 days: F = 1.12438, +41.5 pips; hedge carry +0.370% for 3 months. A EUR asset returning
+2.0% with spot ending at 1.10: hedged +2.33%, unhedged +0.16%.

**Pitfalls.** Pair orientation: USDJPY quotes JPY per USD, so the base is USD. Rates in percent must be
divided by 100. A reference rate dated D−1 combined with a spot dated D is acceptable for daily work;
record both dates. Do not present F as a bank quote.

**Acceptance checks.** Equal rates give F = S. Swapping base and quote rates inverts the direction of the
points. The exact and approximate hedged returns differ by R_local·(S_T/S − 1) plus a second-order rate
term (F/S − 1 = (r_q − r_b)·τ/(1 + r_b·τ) when both legs use the same day basis).

## C2. Carry proxy and carry-to-volatility

**Use when:** ranking currencies by carry, or explaining a carry-trade backtest, with a labelled proxy.

**Method.**
- Annual carry of long base / short quote: `carry = r_b − r_q` (policy or overnight reference rates;
  state which).
- Daily carry excess return: `x_t = ln(S_t/S_{t−1})` (sign oriented so that long base gains when S rises)
  `+ (r_b − r_q)·Δt`, with Δt = calendar days/365 (or the money-market basis).
- FX realized vol `σ_FX = stdev(ln S_t/S_{t−1}) × √A`. Here A is the number of observations per year
  actually present in `*.FOREX` data: count them, do not assume 252 or 365.
- Carry-to-vol = carry / σ_FX. 52-week range position = (S − min_52w)/(max_52w − min_52w).

**Worked example.** Long EUR / short USD on 2026-10-22: carry = 2.442% − 3.90% = −1.46% per year
(negative carry).

**Pitfalls.** Only USD/EUR/GBP have EODHD policy/reference rates (B0); a G10 or EM carry ranking needs
user-supplied rates or verified GBOND short tenors. A carry backtest ignores the cross-currency basis,
forward bid/ask and roll costs: label it gross.

**Acceptance checks.** With S constant, cumulative excess return = carry × time. Swapping the orientation
flips the sign.

## C2b. FX momentum and policy-rate divergence table

**Use when:** an FX dashboard needs trend (time-series and cross-sectional momentum) next to carry (C2), or
a "who is hiking or cutting relative to the Fed" table.

**EODHD inputs.**
- Daily `*.FOREX` closes (1 call per pair, full history).
- `rates/policy-rates`: `FED_TARGET_LOWER`/`UPPER`, `ECB_DFR`, `BOE_BANK_RATE` (1 call per request; Fed,
  ECB and BoE only, B0).
- Other central banks: "… Interest Rate Decision" rows from `economic-events` (C5/C7), labelled with that
  source.
- Optional market proxy: 2Y `.GBOND` yields (verify each symbol with a probe).

**Method — momentum.**
1. Normalize the orientation: express every currency against one numeraire, e.g. USD per 1 unit of
   foreign currency. USDJPY is quoted in JPY per USD, so invert it: `S' = 1/S`. The return of the inverted
   pair is `1/(1 + r) − 1`, not −r.
2. Choose the as-of date t (a completed session). For each horizon h ∈ {1, 3, 12} months, look up the last
   close on or before `t − h months`. Calendar-month offsets are more stable than row counts, because
   `*.FOREX` rows include some weekend dates (step 5). `r_h = S_t / S_{t−h} − 1`. If the start row is more
   than 4 days before the target date, the value is unavailable.
3. Variants (declare the one you use):
   - **12-1 momentum** = `S_{t−1m}/S_{t−12m} − 1`, which skips the last month.
   - **Carry-adjusted (excess) momentum:** add `(r_base − r_quote)·h/12`, using C2 rates (USD/EUR/GBP
     only).
   - **Vol-scaled:** `r_h / (σ_FX·√(h/12))`, with σ_FX from C2 and the observation count actually present.
4. Cross-section: rank the currencies by the chosen measure, and show the rank, value, start and end dates.
   A momentum *signal* (top-k long, bottom-k short) is a research rule. Backtest it with the lags in
   [backtesting.md](backtesting.md) before showing any performance.
5. Calendar: `EURUSD.FOREX` daily rows include Saturday and Sunday dates (probe 2026-10-25: 102 weekend
   rows in 402 since 2025-09-01). Before computing vol, either drop weekend rows or keep them and count A
   from the data. Decide once and store the rule.

**Method — policy divergence table.** One row per central bank:

| Column | Definition |
|---|---|
| Policy rate | Fed: (lower + upper)/2. ECB: DFR (state the choice: DFR, not MRO). BoE: Bank Rate |
| Last change | Date and size (bp) of the latest row where the rate differs from the previous row (B9) |
| Δ3M, Δ12M | Rate(t) − rate on or before t − 3M / t − 12M, in bp |
| Differential vs Fed | (rate − Fed midpoint) × 100, in bp |
| Δ differential 12M | Change in that differential: negative = diverging more below the Fed |
| 2Y market proxy (optional) | 2Y `.GBOND` − UST 2Y in bp, on matched dates, labelled "market proxy" |

Pair the table with the momentum of the matching `*.FOREX` pair. Do not claim that divergence causes the
FX move: show both side by side.

```python
import bisect, datetime as dt

def asof(rows, day):
    """rows sorted by date: last (date, close) on or before day, else None."""
    i = bisect.bisect_right([r[0] for r in rows], day) - 1
    return rows[i] if i >= 0 else None

def months_back(d, m):
    y, mo = divmod(d.month - 1 - m, 12)
    mo += 1
    last = 28 if mo == 2 else 30 if mo in (4, 6, 9, 11) else 31
    return dt.date(d.year + y, mo, min(d.day, last))

def fx_momentum(rows, t, horizons=(1, 3, 12), invert=False, max_gap_days=4):
    """rows: [(date, close)] of one *.FOREX pair. Returns {h: base-currency return}; invert=True gives
    the quote currency's return (1/S)."""
    end, out = asof(rows, t), {}
    for h in horizons:
        target = months_back(t, h)
        start = asof(rows, target)
        if end is None or start is None or (target - start[0]).days > max_gap_days:
            out[h] = None
            continue
        r = end[1] / start[1] - 1
        out[h] = (1 / (1 + r) - 1) if invert else r
    return out
```

**Worked example (probe, demo key, `EURUSD.FOREX`, weekend rows dropped, as of 2026-10-23).**

| Measure | Value |
|---|---|
| Closes | 1.12023 (2026-10-23), 1.13779 (2026-07-23), 1.16158 (2025-10-23) |
| EUR return vs USD | 1M −1.602%, 3M −1.543%, 12M −3.560% |
| USD return vs EUR (inverted pair) | 1M +1.628%, 3M +1.568%, 12M +3.691% |
| 63-row realized vol | 4.69% (annualized with 260) |
| 3M vol-scaled score | −0.66 |

Divergence (synthetic rates): Fed midpoint 3.875% (3.75–4.00), ECB DFR 2.00%, BoE 3.75%. Twelve months
earlier they were 4.375%, 2.25% and 4.25%. Differential vs Fed: ECB −187.5 bp, BoE −12.5 bp. Δ
differential over 12M: ECB +25 bp (converging), BoE 0 bp.

**Pitfalls.**
- Mixing orientations in one ranking.
- Using −r for an inverted pair.
- Row-count horizons on a series with weekend rows.
- The unfinished current day: the probe returned a 2026-10-25 row before the week had opened. Use the
  last completed session.
- The ECB has three policy rates. Pick one and keep it.
- `economic-events` decision rows give the announcement date, not the effective date.

**Acceptance checks.** The inverted return equals `1/(1 + r) − 1` (the probe's 12M values satisfy
1/(1 − 0.03560) − 1 = +3.691%). A constant series gives 0 for every h. A gap of more than 4 days at the
start date returns unavailable. Every differential uses rates on or before the same t. A bank without an
EODHD policy-rate code shows its source as "economic events".

## C3. PPP gap and real exchange rate from annual CPI

**Use when:** a long-horizon valuation view of a currency pair.

**EODHD inputs.** `/api/macro-indicator/{ISO3}?indicator=inflation_consumer_prices_annual` (annual %,
`Date` = year end). Annual FX averages computed from `*.FOREX` daily closes. The probe showed USA annual
CPI through 2024 on 2026-10-25, so the latest year lags by more than a year.

**Method (relative PPP from a base year t0).** For pair quote-per-base, with inflation π (decimal per year):

```
CPI index:  I_c(t) = Π_{y=t0+1..t} (1 + π_c,y)       (I_c(t0) = 1)
PPP rate:   S_PPP(t) = S_avg(t0) · I_quote(t) / I_base(t)
Gap:        S_avg(t)/S_PPP(t) − 1    (> 0: base currency expensive vs the base-year parity)
Real exchange rate index: RER(t) = S_avg(t) · I_base(t) / I_quote(t)
```

Use annual-average FX against annual-average CPI inflation. If you compare a current spot with the
latest PPP value, state the period mismatch.

**Worked example (synthetic).** S_avg(t0) = 1.10 USD/EUR; US inflation 3% and euro-area inflation 2% per
year for 3 years → S_PPP = 1.10·(1.03/1.02)³ = 1.13268; actual 1.12 → gap −1.12% (EUR cheap against
the base-year parity).

**Pitfalls.** The result depends entirely on the base year: show it, and optionally average over several
base years. For the euro area, macro-indicator country codes are ISO-3 per country. An aggregate euro-area
code is not confirmed, so use a weighted member-country proxy (e.g. DEU, FRA, ITA) and label it.
Missing years break the product: do not fill them.

**Acceptance checks.** Equal inflation keeps S_PPP = S_avg(t0). A missing CPI year marks every later PPP
value unavailable.

## C4. Macro indicators: codes, units, call rules

**Use when:** pulling country macro series for a dashboard or model.

**EODHD inputs.** `/api/macro-indicator/{ISO3}?indicator=CODE&fmt=json`. Fundamentals Feed or All-In-One.
Budget 10 calls per request ([plans-limits.md](plans-limits.md); the endpoint page says 1). One indicator per
request.

| Code | Meaning | Unit |
|---|---|---|
| `gdp_current_usd` | GDP, current USD | USD |
| `gdp_growth_annual` | Real GDP growth | % per year |
| `inflation_consumer_prices_annual` | CPI inflation | % per year |
| `unemployment_total_percent` | Unemployment | % of labour force |
| `real_interest_rate` | Real lending rate (no nominal policy-rate indicator here: use B9) | % |
| `population_total`, `population_growth_annual` | Population | count, % |
| `merchandise_trade_percent_gdp` | Merchandise trade volume (not a balance) | % of GDP |
| `net_trades_goods_services` | Net exports (trade balance) | USD |
| `debt_percent_gdp` | Central government debt | % of GDP |

Rules:
1. Always pass `indicator=`. A call without it returns only GDP, and an unknown code returns plain text
   `Indicator or Country are Not Found.` (not JSON). Parse defensively.
2. The response `Indicator` field is a description ("Inflation, consumer prices (annual %)"), not the code.
   Validate it against an expected-description map, not against the code string.
3. Series are annual (`Period` "Annual", `Date` = 12-31). Keep `Date` as the period end; there is no
   release date, so availability must be a stated assumption (e.g. period end + 6 months) for any
   backtest join.
4. For monthly/quarterly prints (CPI, payrolls, GDP releases) use economic events (C5).

**Acceptance checks.** A wrong code raises an error, not an empty or GDP series. Each value carries
country, code, period end and retrieval date. Multi-country tables use the same period for every country,
or show the period per cell.

## C5. Economic events: call rules, fields and impact tiers

**Use when:** building an economic calendar, event filters, or surprise datasets.

**EODHD inputs.** `/api/economic-events?from=YYYY-MM-DD&to=YYYY-MM-DD&country=XX&limit=1000&offset=0`
(ISO-2 country, `EU` for the euro area). History from 2020. `limit` ≤ 1000, `offset` ≤ 1000 (narrow the
date window to go deeper). Calendar & News Feed, Fundamentals Feed or All-In-One. Cost: 1 call per the
endpoint page; recipe 6 budgets 10, so confirm with `/api/user` before and after.

**Call rules (probe 2026-10-25).**
1. Always pass `from`, `to` **and** `country`. A bare call returned far-future placeholder rows (January
   2027) with null `actual`/`previous`/`estimate`.
2. Volume: one US week returned about 100 rows (Treasury auctions, EIA stocks, CFTC positions, Fed
   speeches), so use windows of a month or less with `limit=1000`.
3. Sort order is newest first; sort locally.

**Fields.**

| Field | Meaning and handling |
|---|---|
| `type` | Event name (free text, e.g. "Inflation Rate", "Core Inflation Rate", "Fed Interest Rate Decision", "Initial Jobless Claims") |
| `comparison` | `mom`, `qoq`, `yoy`, `wow` or null. **The same `type` with null comparison can be a level**: US "Inflation Rate" null = CPI index 336.94, while `yoy` = 3.7 (2026-10-14) |
| `period` | Reference period label ("Sep", "Q3", "Oct/10") |
| `date` | Release time, UTC, `YYYY-MM-DD HH:MM:SS`; `00:00:00` means no time given |
| `actual` | First release; null until released (revisions appear in the next row's `previous`) |
| `estimate` | Consensus, often null for minor events |
| `previous`, `change`, `change_percentage` | `change` is 0 (not null) on unreleased rows: ignore it when `actual` is null |

Key every row by `(country, type, comparison, period, date)`. Never key by `type` alone.

**Impact tiers.** No impact field is returned. Declare the tier list in config, match exact `type` strings
per country, and log unmatched types for review. A starting list for the US:

| Tier | Types (exact strings to verify per country) |
|---|---|
| High | Fed Interest Rate Decision, Inflation Rate (yoy/mom; the US CPI rows use this name, not "CPI"), Core Inflation Rate, Nonfarm Payrolls, Unemployment Rate, GDP Growth Rate, PCE Price Index, Core PCE Price Index |
| Medium | Retail Sales, ISM Manufacturing/Services PMI, Producer Price Index, Core PPI, Initial Jobless Claims, JOLTs, Michigan Consumer Sentiment |
| Low | everything else (auctions, EIA inventories, regional Fed surveys, speeches) |

Event-risk window rule (example): no new simulated entries from 2 hours before to 30 minutes after a
High-tier release, in UTC.

**Pitfalls.** Event strings differ by country and can change: test the tier map against a recent month.
CFTC "speculative net positions" rows are aggregate weekly figures inside this feed. They are not full
Commitments of Traders reports and are not contract-level futures data.

**Acceptance checks.** A request without `from/to/country` is rejected by your client. An unreleased row's
`change` is not shown as "0 change". Two US CPI rows on the same date with different `comparison` stay
separate. Tier coverage (matched/total rows) is reported.

## C6. Macro-surprise event study

**Use when:** "how do SPY, Treasuries, EURUSD or gold react to CPI/payroll surprises?"

**EODHD inputs.** Economic events (C5) since 2020. Daily EOD for `SPY.US`, `TLT.US`, `EURUSD.FOREX`,
`XAUUSD.FOREX`. UST par 2Y/10Y (yield changes in bp). Optional intraday 5m bars (Extended plan,
unadjusted, UTC; 5 calls per request).

**Method.**
1. Select the series `(country, type, comparison)`, e.g. (US, "Inflation Rate", yoy). Keep rows with
   non-null `actual` and `estimate`.
2. Raw surprise `u = actual − estimate`. Standardized surprise
   `z_k = u_k / stdev(u_{k−n} … u_{k−1})` using the **previous** n releases only (n ≥ 12). Earlier rows
   get z = unavailable.
3. Reaction session: release time converted to New York time. If before 09:30, use the same session
   D: r = C_D/C_{D−1} − 1. If after 16:00, use the next session. If during the session, use daily D with
   a flag, or intraday bars [t − 5m, t + 30m].
   Yields: Δy in bp over the same window. FX/gold: same-day close-to-close (24-hour markets; note the
   FOREX daily close convention).
4. Cross-section: `r_k = α + β·z_k + ε_k` per asset. Report β, t-stat, n, R², and the average reaction for
   z > +1 and z < −1. Releases are monthly and non-overlapping, so OLS SEs are acceptable. Use HAC when you
   stack overlapping windows.
5. Robustness: exclude days with another High-tier event in the same window, or include them with a flag.

**Pitfalls.** `estimate` is the consensus as stored now; its timestamp is unknown, and it may differ from
the pre-release survey. `actual` is the first release, which is good for surprises. CPI yoy rounded to 0.1
creates discrete surprises. Daily returns include other news; intraday narrows the window but costs calls.
Survivorship: not relevant for ETFs/FX, but use `adjusted_close` for ETFs.

**Acceptance checks.** z is never computed with the current or future releases. Every reaction row
shows the release time (UTC) and the session used. A synthetic test where r = 0.5·z exactly returns
β = 0.5, R² = 1.

## C7. Central-bank meeting preview

**Use when:** a pre-meeting brief for the Fed, ECB or BoE.

**Steps (EODHD inputs in brackets).**
1. Current policy setting and history of changes [`rates/policy-rates`; B9].
2. Meeting date and consensus: next "… Interest Rate Decision" row, with `estimate` [economic events,
   country filter, window = next 60 days]. Fed rows also carry "Interest Rate Projection - Current/1st Yr/
   2nd Yr/3rd Yr/Longer" (median projections) on projection meetings.
3. Data since the last meeting: latest High/Medium-tier prints (CPI yoy/core, payrolls/unemployment,
   GDP), each with `actual − estimate` [economic events].
4. Market proxies, labelled heuristics: 2Y UST − policy midpoint (bp) and 3M bill − midpoint (bp)
   [UST curves, bills]; change in 2Y since the last meeting; SOFR − lower bound [funding stress].
   For the ECB/BoE, use the country's 2Y `.GBOND` if entitled.
5. Curve snapshot since the last meeting: 2s10s, 10Y real yield, 5Y breakeven [B1, B4].
6. Output: one table with as-of dates, and a short neutral summary of what moved.

**Boundary.** No futures- or OIS-implied meeting probabilities (no fed funds/SOFR futures or OIS curves).
"2Y − policy" is a coarse pricing proxy, not a probability.

**Acceptance checks.** Every number shows its source date. The consensus is shown only when `estimate` is
non-null. The previous decision in policy-rates matches the previous decision row in economic events.

## C8. Composite sentiment index

> News-volume and reaction methods: [events-news](events-news.md) (reaction ranking, abnormal news volume) and [app-ai-patterns §10](app-ai-patterns.md#10-news-rag-specifics).

**Use when:** a "fear/greed"-style composite or a news-sentiment index for a basket.

**Components (each oriented so that higher = more risk appetite).**

| Component | EODHD source | Transform |
|---|---|---|
| Volatility | `VIX.INDX` close | inverted percentile |
| Breadth | `ADVN.INDX`, `DECN.INDX` closes (NYSE advancers/decliners, from 2007-11-09) | 10-day mean of ADVN/(ADVN + DECN) |
| Trend | `SPY.US` adjusted close | (price / 125-day SMA − 1) |
| Safe-haven demand | `SPY.US` vs `TLT.US` | 20-day return SPY − TLT |
| Credit stress | CMDI `market_cmdi` (weekly; forward-filled for display only, keep its date) | inverted percentile |
| Options put/call | Σ put volume / Σ call volume of SPY + QQQ chains (Marketplace) | inverted percentile |
| News sentiment | `/api/sentiments?s=…` (5 calls per ticker, ≤ 100 tickers) | count-weighted basket average, z-scored |

**Method.**
1. For each component, compute a percentile rank p_i(t) ∈ [0, 1] against its **own trailing window**
   (e.g. 252 sessions ending at t), never the full sample.
2. Composite `CSI(t) = Σ w_i·p_i(t) / Σ w_i` over components available at t, with weights declared (equal by
   default) and shown. Require at least 4 of 7 components; otherwise output unavailable. Report each
   component's as-of date and value.
3. News-sentiment sub-index: daily basket score `s_t = Σ_j count_j,t·norm_j,t / Σ_j count_j,t`. Then
   z-score it against a rolling 60-day mean and standard deviation, because raw scores are biased
   positive (AAPL's daily `normalized` ranged 0.36–0.96 in Oct 2026). Weekend rows exist: assign them to
   the next session. A day with no articles is missing, not neutral.
4. Contrarian extremes (if used) are defined ex ante (e.g. CSI < 0.1 or > 0.9) and tested out of sample.
5. Abnormal news volume per ticker. The source is the daily `count` in `/api/sentiments` (articles used
   for that day's score; 5 calls per request plus 5 per ticker per the endpoint page). For a deduplicated
   measure, use the daily count of news clusters (`/api/news`, 5 calls per ticker; clustering in
   [app-ai-patterns.md](app-ai-patterns.md) §10). With c_t = the count on day t (0 when there are no
   articles, which is valid here, unlike the score):
   `AV_t = c_t / mean(c_{t−20} … c_{t−1})` and `z_t = (c_t − mean)/sd`, using only the **previous**
   20 (or 60) days. AV is unavailable when the trailing mean is < 1 article per day; z is unavailable
   when sd = 0. Use AV or z as an attention feature, or as a gate: read sentiment only on days with
   z ≥ 2. Do not treat it as a direction signal.
6. Topic weights from `/api/news-word-weights?s=…&filter[date_from]=…&filter[date_to]=…&page[limit]=…`
   (5 calls per request plus 5 per ticker). It returns stemmed words with relative weights (`data`),
   plus `meta.news_found` and `meta.news_processed`.
   - Declare topic dictionaries of stems (e.g. tariffs = {tariff, trade, china}).
   - The topic weight for a window = Σ of the weights of the stems in that dictionary.
   - Compute it per non-overlapping window (weekly or monthly) and store it with the window dates and
     both meta counts.
   - The feature is the change in topic weight between windows.
   - When `news_processed` < `news_found`, the weights describe a sample: record the processed share.
   - Re-running the same window later may return different weights, because late articles get added and
     the processing is AI-based (not verified). Store each response; do not refetch it for a backtest.

```python
import math

def abnormal_news_volume(counts, window=20, min_mean=1.0):
    """counts: daily article (or cluster) counts, oldest first, 0 for a day with none.
    Returns (ratio, z) per day from the previous `window` days only; None until the window is full."""
    out = []
    for i, c in enumerate(counts):
        if i < window:
            out.append((None, None))
            continue
        past = counts[i - window:i]
        m = sum(past) / window
        sd = math.sqrt(sum((x - m) ** 2 for x in past) / (window - 1))
        out.append((c / m if m >= min_mean else None, (c - m) / sd if sd > 0 else None))
    return out

def topic_weight(word_weights, topic_stems):
    """word_weights: the `data` object of /api/news-word-weights."""
    return sum(w for word, w in word_weights.items() if word in topic_stems)
```

**Pitfalls.** This is not any published third-party index and must not carry such a name. Market-wide
CBOE put/call, margin debt, fund flows and social-media sentiment are not EODHD data; the SPY/QQQ ratio
is a labelled proxy. The `sentiments` endpoint description mentions news and social sources; its per-source
mix is not exposed.

**Acceptance checks.** The percentile at t uses no data after t. Dropping a component re-normalizes the
weights and lowers the coverage figure. A constant component gives p = undefined and is excluded (not
0.5). For the counts 4, 6, 5, 5 repeated five times (20 days, mean 5, sd 0.7255) followed by 20, the
day-21 value is AV = 4.0 and z = 20.68. The weights {tariff 0.01889, china 0.0079, trade 0.00723} give a
tariffs topic weight of 0.03402. A count series that changes only on day t leaves AV and z for days
before t unchanged.

## C9. Macro dashboard recipe

**Use when:** a country (or multi-country) macro/markets dashboard. Extends recipe 18 and recipe 47 in
[build-recipes.md](build-recipes.md).

| Block | Series (EODHD source) | Display rule |
|---|---|---|
| Inflation | Monthly CPI yoy, core yoy (economic events); annual CPI (macro-indicator) | Latest print, consensus, surprise; release date |
| Growth | GDP growth (events, quarterly); `gdp_growth_annual` | Period label + release date |
| Labour | Payrolls, unemployment, claims (events); `unemployment_total_percent` | 3-month average for noisy series |
| Policy & money | Policy rates; SOFR/€STR/SONIA; funding-stress spreads | Level, last change date |
| Curve | UST par today, −1M, −1Y on matched bond-market days; 2s10s, 3m10y, 5s30s; real 10Y; BE5/BE10; `.GBOND` for other countries | Curve chart + slope table (B1, B4) |
| Credit | HQM − UST (monthly), CMDI (weekly) | Show frequency badges |
| FX | `*.FOREX` majors vs USD; 1M/1Y change; carry proxy (C2) | Pair orientation in header |
| Commodities | `/api/commodities/historical/WTI?interval=daily` (and `BRENT`); gold `XAUUSD.FOREX`; copper monthly | The default `interval` is monthly: pass it explicitly. Weekly batch lag for energy. Daily pulls are paged and monthly rows are stamped at the month start (C9b) |
| Equity/risk | Index closes (`GSPC.INDX`, `VIX.INDX`), CSI (C8) | — |
| Calendar | Next 14 days of High/Medium events (C5) | UTC → local time, "time not given" shown as such |

Budget (US, daily refresh): UST 1–3 calls (one per curve per year), policy/reference/funding a few calls,
events 1–2 calls per window, EOD 1 per symbol, macro-indicator 10 per series (refresh monthly).

**Acceptance checks.** Every cell shows the observation date and, for releases, the release time. Stale
cells beyond their expected frequency are flagged. A missing tenor stays missing. A multi-country table
uses one period per column. No value is forward-filled without a "carried" marker.

## C9b. Commodity reference series: data contract, ETF tracking, inflation beta, futures contract sizing

**Use when:** a commodity brief or dashboard, comparing a commodity ETF with its reference price, asking
whether a commodity hedged inflation, or sizing a futures position from user-supplied contract specs.

**EODHD inputs and data contract.**
- `/api/commodities/historical/{CODE}?interval=daily|weekly|monthly|quarterly|annual`. There are 23
  codes (WTI, BRENT, NATURAL_GAS, …, COPPER, WHEAT, ALL_COMMODITIES …). The response has
  `meta` (name, unit, interval, total) and `data[]` of `{date, value}`. Cost 5 calls per request; all
  plans; the demo key covers WTI only.
- Daily data exists for energy only. Metals, agriculture and indices are monthly, published 2–3 weeks
  after month end. Daily energy points arrive in weekly EIA batches, typically on Tuesdays, so the lag can
  be up to about a week.
- Precious-metal series were discontinued at the source. Use `XAUUSD.FOREX` / `XAGUSD.FOREX` (verify
  the silver symbol with a probe) and label them "spot FX-style quote".
- **Paging (probe 2026-10-26, WTI daily).** The response is newest first and capped at 1,000 rows
  (`meta.limit` 1000, `meta.total` 10,270). Plain `offset`/`limit`/`from`/`to` were ignored. Use
  `page[offset]` and `page[limit]`, and follow `links.next` until it is null. Full daily WTI is 11 pages.
  Budget 5 calls per page (assumed from the per-request cost; verify with `/api/user`).
- **Monthly label (probe, WTI).** The monthly row stamped `2026-09-01` had value 97.18. That equals the
  2026-09-30 daily value, not the September average (97.31); July and August matched their month-end
  values too. The label is the month start, but the value is the month end. Re-stamp it to the month end
  before any join, or you leak up to a month. Verify for each code: a monthly series can be a
  monthly average.
- Units come from `meta.unit` (USD per barrel, cents per pound, index 2016 = 100 …). Store them. Never
  mix cents and dollars.
- Inventories and supply: the only EODHD source is the weekly US EIA inventory rows inside
  `economic-events`. Those are low-tier events (C5). Probe which EIA series appear and their exact `type`
  strings before you rely on them. Other inventory, production, rig-count and shipping data are not
  EODHD data.

**Method — ETF vs reference tracking.**
1. Choose the pair, e.g. a crude-oil ETF on EODHD (`adjusted_close`) vs WTI daily, both at month end.
   Re-stamp the monthly reference rows as above. Compute matched-period simple returns.
2. Tracking difference `TD_t = r_ETF,t − r_ref,t`. Report the annualized mean TD (× 12 for monthly) and
   the tracking error `sd(TD)·√12`.
3. Fee part = `ETF_Data.NetExpenseRatio` (current value only; label it). The residual =
   mean TD × 12 + expense ratio. That residual combines futures roll yield, collateral income and timing
   (the fund's NAV strike vs the reference print time). It cannot be split further without the
   futures-curve prices, which are user-supplied (`cross-asset.md#Commodities and futures`).
4. Show the cumulative ETF vs reference chart, with both units and the as-of dates.

**Method — inflation beta.**
1. Choose the inflation series and its frequency:
   - annual `inflation_consumer_prices_annual` (macro-indicator, C4) against calendar-year commodity
     returns from year-end values; or
   - monthly US "Inflation Rate" yoy or mom rows from `economic-events` (from 2020 only, C5), against
     the monthly return of the release month.
2. OLS `r_commodity = α + β·π + ε`. Report β, R², n and the sample dates. With annual data n is small,
   so show the scatter and call the result descriptive.
3. Optional: use the inflation surprise (actual − estimate, C6) instead of the level, against
   release-day returns of the ETF. Daily reference energy data is batched, so release-day reactions
   need the ETF.

**Method — futures contract sizing (user-supplied specifications).**
`contracts = floor(R / (|entry − stop| / tick_size × tick_value))`, where:
- R is the risk budget in account currency;
- tick_size and tick_value (= tick_size × multiplier) come from the user's contract specification.

Report the notional (`contracts × price × multiplier`), the risk per contract, and the margin
(user-supplied). This module sizes contracts only. Fees and gap risk are not included. EODHD reference
prices can set the stop distance, e.g. an ATR from the reference daily series. They are not the contract's
own prices: label that basis risk.

```python
import math
import numpy as np

def tracking(etf_ret, ref_ret, expense_ratio, periods_per_year=12):
    td = np.asarray(etf_ret) - np.asarray(ref_ret)
    return dict(mean_td_ann=td.mean() * periods_per_year,
                te_ann=td.std(ddof=1) * math.sqrt(periods_per_year),
                residual_ann=td.mean() * periods_per_year + expense_ratio)  # roll + collateral + timing

def inflation_beta(asset_ret, infl):
    b, a = np.polyfit(np.asarray(infl), np.asarray(asset_ret), 1)
    return dict(beta=b, alpha=a, r2=np.corrcoef(infl, asset_ret)[0, 1] ** 2, n=len(infl))

def futures_contracts(risk_budget, entry, stop, tick_size, tick_value):
    ticks = abs(entry - stop) / tick_size
    if ticks <= 0:
        raise ValueError("entry and stop must differ")
    per_contract = ticks * tick_value
    return math.floor(risk_budget / per_contract + 1e-9), per_contract
```

**Pitfalls.**
- Leaving the interval at the monthly default.
- Using the first page of daily rows as the full history.
- Joining monthly rows on their month-start label.
- Comparing a monthly average with a month-end ETF close.
- Presenting a reference spot price as a futures price.
- Annualizing TD from a few months.
- Calling a 6-point annual regression an inflation hedge "proof".

**Acceptance checks.**
- Six monthly reference returns (2, −1, 3, 0, −2, 1%) and ETF returns = reference − 0.4% ± noise, with an
  expense ratio of 0.60%: mean TD −4.80%/yr, TE 0.49%/yr, residual −4.20%/yr.
- Returns built as 0.01 + 3·π give β = 3.0, α = 0.01, R² = 1.
- Sizing a USD 5,000 risk budget, entry 80.00, tick 0.01, tick value 10: a stop at 78.50 gives 150 ticks,
  1,500 per contract and 3 contracts; a stop at 78.30 gives 1,700 per contract and 2 contracts.
- A paged daily pull ends with `links.next = null` and its row count equals `meta.total`.

## C10. FX and macro boundaries

- No FX forwards, forward points, NDFs, FX implied volatility or cross-currency basis. CIP forwards are
  theoretical and labelled.
- Policy/reference rates only for USD, EUR and GBP. Other currencies need verified `.GBOND` short tenors
  or user inputs.
- `macro-indicator` is annual with no release dates or vintages. Economic events start in 2020, and their
  consensus timestamps are unknown.
- No futures-implied policy paths, no OIS curves, no market-wide CBOE put/call ratio, no FINRA margin
  debt, no fund-flow data, no social-media sentiment breakdown.
- Commodity series are reference prices (weekly or monthly batches for many), not futures curves. No
  inventory or supply data apart from the weekly US EIA rows in economic events (C9b), no contract
  specifications, margins or COT reports.
