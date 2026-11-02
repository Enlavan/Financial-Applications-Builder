# Quantitative research methods: factors, validation, costs and monitoring

Procedures for testing whether a signal, factor or strategy built on EODHD data is real, survives
selection bias and costs, and keeps working after deployment. Each method gives the user task it serves,
the EODHD inputs, the formulas with units, ordered steps, pitfalls, and acceptance checks an agent can
run on synthetic data. The chapter assumes the time discipline of [temporal research](temporal-research.md),
the engine rules of [backtesting](backtesting.md) and the guardrails of
[research validation](research-validation.md); it adds the procedures those chapters name. Portfolio risk
metrics, allocation algorithms and options analytics live in [portfolio and risk](portfolio-risk.md) and
[options](options.md). Nothing here is investment advice: every threshold below is a declared, editable
research default, not a universal truth.

## Contents

1. Conventions and the shared research panel
2. Factor evaluation toolkit
   - 2.1 Per-date rank IC, IC-IR and hit rate
   - 2.2 Newey-West t-statistic and overlap-adjusted sample size
   - 2.3 IC decay and horizon choice
   - 2.4 Quantile spreads and monotonicity
   - 2.5 Rank autocorrelation as a turnover proxy
   - 2.6 Stability: half-sample sign flip and sub-periods
   - 2.7 Market-neutral and sector-neutral variants
   - 2.8 Factor gates and feature-validation order
3. Overfitting and validation
   - 3.1 Trial ledger
   - 3.2 Probabilistic Sharpe ratio
   - 3.3 Deflated Sharpe ratio
   - 3.4 Probability of backtest overfitting (CSCV)
   - 3.5 Combinatorial purged cross-validation
   - 3.6 Parameter-sweep plateau and cliff checks
   - 3.7 In-sample / out-of-sample decay rule
   - 3.8 Stationary block bootstrap confidence intervals
   - 3.9 Multiple testing: Bonferroni, Benjamini-Hochberg, Benjamini-Yekutieli
   - 3.10 Effective breadth and the fundamental law
   - 3.11 Cost ladder and the PASS / WARN / FAIL backtest verdict
   - 3.12 Sequential model-validation gates
   - 3.13 Exit-rule lab
4. Stationarity and regime features
   - 4.1 ADF and KPSS jointly
   - 4.2 Transforms
   - 4.3 Lagged regime-feature catalogue from EODHD series
   - 4.4 Regimes for risk scaling and per-regime reporting
   - 4.5 CUSUM change points in mean and volatility
   - 4.6 Gaussian hidden Markov regimes
   - 4.7 Rolling-Hurst regimes
   - 4.8 Per-ticker fear score
5. Costs, impact and capacity
   - 5.1 Per-rebalance cost model
   - 5.2 ADV and volatility from EODHD
   - 5.3 Spread estimators from daily OHLC (Corwin-Schultz, Abdi-Ranaldo)
   - 5.4 Square-root market impact
   - 5.5 Safety margin and capacity
   - 5.6 TWAP and VWAP baselines from 1-minute bars
   - 5.7 Transaction-cost analysis of user fills against intraday bars
   - 5.8 Almgren-Chriss execution schedule
6. Pairs, cointegration and mean-reversion statistics
   - 6.1 Engle-Granger for two legs
   - 6.2 Johansen test for three or more legs
   - 6.3 Hurst exponent
   - 6.4 Variance ratio test (Lo-MacKinlay)
   - 6.5 Ornstein-Uhlenbeck fit, half-life and trading bands
7. Signal outcome tracking and forecast scoring
   - 7.1 Forward-outcome ledger
   - 7.2 Brier score, log loss and calibration
   - 7.3 Combining several probability forecasts
   - 7.4 Aggregating signals from several detectors
   - 7.5 Pooling several agents or models: run-state contract and diversity check
8. Causal identification basics for event and market studies
9. Model drift monitoring
   - 9.1 Retraining and promotion policy
10. Strategy specification template

---

## 1. Conventions and the shared research panel

| Symbol | Meaning | Unit |
|---|---|---|
| `t` | decision date (an exchange session) | session |
| `H` | label horizon | sessions |
| `r_{i,t→t+H}` | forward return of listing `i` from the fill after `t` to the horizon end | decimal (0.01 = 1%) |
| `f_{i,t}` | factor value known at decision time `t` | factor units |
| `IC_t` | cross-sectional Spearman correlation of `f_{·,t}` and `r_{·,t→t+H}` | −1…1 |
| `T` | number of periods in a series | count |
| `SR` | Sharpe ratio, **per period** inside formulas, annualised only for display | per period |
| `c` | one-way cost | basis points of traded notional (1 bp = 0.0001) |
| `ADV` | average daily volume | shares (or currency when written `ADV$`) |
| `σ_d` | daily volatility of log returns | decimal per day |

Rules used throughout:

- **Returns basis.** Research returns come from `adjusted_close` (split- and dividend-adjusted, restated over
  history on every new action). Cash accounting and executable levels use raw `open/high/low/close`.
  Never mix the two in one series. See [data semantics](data-semantics.md).
- **Annualisation.** Multiply per-period mean by `P` and per-period volatility by `√P`, where `P` is the
  number of periods per year in the calendar the data actually follows: 252 exchange sessions, 365 for
  `.CC` crypto daily, 52 weekly, 12 monthly. Annualised Sharpe = per-period Sharpe × `√P`.
- **Sample statistics.** Standard deviations use `ddof=1` unless a formula says otherwise.
- **Missing is not zero.** A missing bar, a holiday or a null volume is excluded, never filled with a zero
  return. Calendars come from `/api/v2/exchange-details/{EX}` (Extended or All-In-One), not weekday
  arithmetic.
- **Risk-free rate.** For US excess returns use `/api/ust/bill-rates` (13-week `coupon`, a coupon-equivalent
  annual rate in percent; 1 call per request, all plans, beta). Daily rate ≈ `(1 + y/100)^(1/252) − 1`.
  Bills are published on US government business days; carry the prior value over a stock-market session
  with no bill print and label it.

### Building the panel from EODHD

1. **Universe.** `exchange-symbol-list/{EX}` (active) plus `exchange-symbol-list/{EX}?delisted=1`; 1 call
   each; the second response replaces the first, so merge both. For S&P 500 membership use `GSPC.INDX`
   Fundamentals `HistoricalTickerComponents` (from April 2012, latest interval per ticker only). Any other
   index history needs the Marketplace constituents product. Current-membership universes carry
   survivorship bias; say so in the result.
2. **Prices.** `/api/eod/{SYM}?fmt=json` returns full history for 1 call per symbol. For a daily update use
   `/api/eod-bulk-last-day/{EX}` (100 calls per exchange-day; read the returned `date`, which falls back
   silently on holidays). After any new split or dividend, re-pull the symbol's whole series.
3. **Forward labels.** For a close-`t` signal filled at the open of `t+1`, the label is
   `r = adj_close_{t+H} / adj_open_{t+1} − 1`, with `adj_open_{t+1} = open_{t+1} × adjusted_close_{t+1} / close_{t+1}`.
   The simpler close-to-close label `adjusted_close_{t+H}/adjusted_close_t − 1` assumes a fill at the close
   that produced the signal; use it only if the strategy spec declares that.
4. **Eligibility at `t`.** A bar exists at `t`, price and liquidity floors on split-consistent values,
   membership (if an index universe), and the factor's inputs are admissible at `t`.
5. **Fundamental inputs.** Fundamentals are current-vintage and restated. Activate a value at
   `filing_date` plus a declared lag (and only on a later session), label the study "current-vintage
   retrospective" per [temporal research](temporal-research.md). Outside the US `filing_date` often equals
   period end, so use a larger lag. Each fundamentals request costs 10 calls (`filter=` does not reduce it).

Budget example: 1,500 US stocks, full history = 2 list calls + 1,500 EOD calls; sector labels via
`fundamentals?filter=General` = 15,000 calls; daily maintenance = 100 calls (bulk). The Free plan's one
year of EOD is too short for any of the validation methods below.

---

## 2. Factor evaluation toolkit

### 2.1 Per-date rank IC, IC-IR and hit rate

**Use when:** "Does this ranking predict next-month returns?" before any portfolio is built.

**EODHD inputs:** the panel of section 1. Factor values from prices (EOD), technicals (computed locally or
`/api/technical`, 5 calls per request) or fundamentals (10 calls per symbol).

**Method.**

1. For each decision date `t` in the evaluation calendar, take the listings eligible at `t` with both
   `f_{i,t}` and `r_{i,t→t+H}` present. Require a minimum cross-section (for example 20 names; record it).
2. `IC_t = Spearman(f_{·,t}, r_{·,t→t+H})` = Pearson correlation of the two rank vectors (average ranks for
   ties).
3. Summarise the IC time series:

| Statistic | Formula |
|---|---|
| mean IC | `ĪC = (1/T) Σ_t IC_t` |
| IC volatility | `s_IC = std(IC_t)` (ddof=1) |
| IC-IR (per period) | `ĪC / s_IC`; annualise by `√(periods per year)` only when IC dates do not overlap |
| hit rate | share of dates with `IC_t > 0` |
| t-statistic | Newey-West, section 2.2 |

Never pool all stock-dates into one correlation: pooled IC mixes cross-sectional skill with time-series
market moves and lets a few volatile dates dominate.

```python
import math
import numpy as np
import pandas as pd

def rank_ic_series(factor: pd.DataFrame, fwd: pd.DataFrame, min_names: int = 20) -> pd.Series:
    """factor, fwd: index = decision date, columns = listing id. fwd[t] is the label for decision t."""
    out = {}
    for d in factor.index.intersection(fwd.index):
        x, y = factor.loc[d], fwd.loc[d]
        ok = x.notna() & y.notna()
        if ok.sum() >= min_names:
            out[d] = x[ok].rank().corr(y[ok].rank())   # Spearman = Pearson on ranks
    return pd.Series(out, dtype=float).sort_index()
```

**Pitfalls.**

- A label built from `adjusted_close` downloaded today embeds dividends and splits that were announced
  later. That is correct for returns. It becomes look-ahead only if the *factor* also reads today's
  adjusted history (for example a "price level" factor on adjusted prices). Compute price-level features on
  raw prices or on a factor that is invariant to scaling.
- Thin listings have no row on non-trading days. A missing row at `t+H` is a missing label, not a zero
  return; do not shift to the next available row without recording it.
- GBX/ZAC listings: returns are unit-free, but liquidity floors are not. Normalise units first.

**Acceptance checks.**

- Synthetic panel: `fwd = 0.1·f + ε` with standard normal `f, ε`, 500 dates × 200 names → mean IC ≈ 0.09,
  hit rate > 0.85, monotone quintiles (section 2.4).
- Replace `f` with independent noise → mean IC within ±0.01 and |t| < 2 in about 95% of seeds.

### 2.2 Newey-West t-statistic and overlap-adjusted sample size

**Use when:** reporting whether a mean IC, a mean long-short return or a regression alpha differs from zero
when observations are autocorrelated (overlapping labels, persistent factors).

**Method.**

- Overlap: with daily decisions and an `H`-session label, consecutive labels share `H−1` sessions, so the IC
  series is roughly MA(`H−1`). Effective sample size `N_eff ≈ T / H`. Either evaluate on non-overlapping
  rebalance dates (every `H`-th session) or keep all dates and use HAC standard errors.
- Newey-West long-run variance with Bartlett weights, for a series `x_t` with mean `x̄`, `e_t = x_t − x̄`:

```
γ_l   = (1/T) Σ_{t=l+1..T} e_t e_{t−l}
LRV   = γ_0 + 2 Σ_{l=1..L} (1 − l/(L+1)) γ_l
t_NW  = x̄ / √(LRV / T)
```

- Lag choice: `L = max(H − 1, ⌊4·(T/100)^(2/9)⌋)`. Never use fewer lags than the overlap.

```python
def newey_west_tstat(x, lags: int) -> float:
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    T = len(x)
    if T < 3:
        return float("nan")
    e = x - x.mean()
    lrv = e @ e / T
    for l in range(1, min(lags, T - 1) + 1):
        lrv += 2.0 * (1.0 - l / (lags + 1.0)) * (e[l:] @ e[:-l]) / T
    return x.mean() / math.sqrt(lrv / T) if lrv > 0 else float("nan")
```

**Pitfalls.** A naive `ĪC/(s_IC/√T)` with overlapping 21-day labels overstates `t` by roughly `√H`. Cross-
sectional dependence (all names react to the same shock) is already absorbed in the per-date IC; do not
add a second correction on top. For regressions on returns (alpha against a benchmark), apply the same HAC
variance to the coefficient.

**Acceptance checks.** A zero-mean MA(4) series (the IC of overlapping `H = 5` labels), `T = 500`, 200
seeds: the naive `t` has a standard deviation of about 2.2 across seeds (so it "finds" significance far too
often), the NW `t` about 1.1. For an i.i.d. series the NW `t` is within ±10% of the naive `t` in about 90%
of seeds.

### 2.3 IC decay and horizon choice

**Use when:** choosing the label horizon and the rebalance interval.

**Method.**

1. Cumulative-horizon IC: compute `ĪC(h)` for `h ∈ {1, 5, 10, 21, 63}` sessions with labels
   `r_{t→t+h}`. Report with NW `t` (lags ≥ `h−1`).
2. Marginal (lagged) IC, which isolates decay: `IC^lag(k)` = IC of `f_t` against the one-period return from
   `t+k` to `t+k+1` (or a fixed 5-day block starting at `t+k`). Fit `IC^lag(k) ≈ IC_0·e^(−k/τ)` by least
   squares on `ln IC^lag(k)` for the positive part; half-life `= τ·ln 2`.
3. Rebalance interval ≤ about half the half-life; slower rebalancing leaves most of the edge unused, faster
   rebalancing pays costs for information already priced.
4. Pick the shortest horizon where expected edge per trade ≥ safety margin × round-trip cost (section 5.5).
5. Keep the feature lookback of the same order as the label horizon; a 252-day feature predicting a 1-day
   label is usually a sign of a mis-specified horizon.

**Pitfalls.** Cumulative IC can rise with `h` even when the signal has decayed, because longer returns have
more cross-sectional dispersion; read decay from the marginal IC. An IC that does **not** decay at all with
horizon, or is large at `h=1` for a slow fundamental factor, is a leakage flag: check activation lags and
label construction first.

**Acceptance checks.** Planted signal `r_{t+k→t+k+1} = a·e^(−k/10)·f_t + ε`: the fitted half-life is
within ±25% of `10·ln 2 ≈ 6.9` sessions on 500 dates × 200 names. A noise factor gives no decay curve
(IC near zero at every lag).

### 2.4 Quantile spreads and monotonicity

**Use when:** checking that the factor works across its whole range, not only in one tail.

**Method.**

1. Each date, sort eligible names into `Q` buckets (5 or 10) by factor rank (break ties by rank order so
   buckets are equal-sized).
2. Equal-weight mean forward return per bucket per date; average over dates.
3. Report: bucket means, top-minus-bottom spread with NW `t`, monotonicity = share of adjacent bucket
   steps in the expected direction (`(Q−1)` steps; 1.0 = fully monotone), and the spread **net of costs**
   from the bucket turnover (section 2.5) and the cost ladder (section 3.11).

```python
def quantile_returns(factor, fwd, q=5):
    rows = []
    for d in factor.index.intersection(fwd.index):
        x, y = factor.loc[d], fwd.loc[d]
        ok = x.notna() & y.notna()
        if ok.sum() >= 2 * q:
            b = pd.qcut(x[ok].rank(method="first"), q, labels=False) + 1
            rows.append(y[ok].groupby(b).mean())
    return pd.DataFrame(rows).mean()            # index 1..q

def monotone_share(qret: pd.Series) -> float:
    return float((np.diff(qret.values) > 0).mean())
```

**Pitfalls.** Equal-weighted bottom buckets are often micro-caps whose costs dwarf the spread; repeat with
a liquidity floor and with cap weights (market cap from `/api/historical-market-cap` is US NYSE/NASDAQ
weekly from 2021-07-09 only; otherwise price × `outstandingShares`, labelled derived). A U-shaped profile
with a big top-minus-bottom spread is not a monotone factor.

**Acceptance checks.** Planted panel of 2.1 → five rising bucket means and monotone share 1.0. Noise →
monotone share near 0.5 on average across seeds.

### 2.5 Rank autocorrelation as a turnover proxy

**Use when:** estimating how much trading a factor implies before simulating a portfolio.

**Method.**

1. Factor rank autocorrelation `ρ_rank(t) = Spearman(f_{·,t_prev}, f_{·,t})` over names present on both
   consecutive rebalance dates. Report the mean.
2. Directly measure bucket turnover: for the top bucket, share of names in the bucket at `t` that were not
   in it at `t_prev`. Two-sided turnover of a long-short top/bottom portfolio ≈ sum of both legs' entry
   shares.
3. High `ρ_rank` (≥ 0.9) → low turnover; values below about 0.5 at the chosen rebalance frequency mean most
   of the book trades every rebalance.

**Pitfalls.** Universe changes (listings entering and leaving) add turnover that the autocorrelation of
common names does not show; report both. Ranks computed on a changing universe size should be converted to
percentiles before comparing.

**Acceptance checks.** A random-walk factor (cumulative sums of noise) gives `ρ_rank` near 0.95 for
100 names; an i.i.d. factor gives `ρ_rank` near 0 and top-quintile turnover near 0.8.

### 2.6 Stability: half-sample sign flip and sub-periods

**Use when:** guarding against a factor whose average comes from one era.

**Method.**

1. Split the IC series chronologically into halves (and thirds if `T` allows). Compute mean IC and NW `t`
   in each.
2. **Sign-flip flag:** the mean IC changes sign between halves → FAIL the stability gate.
3. **Concentration flag:** one sub-period contributes more than about two thirds of the total mean → WARN.
4. Optional: calendar-year table of mean IC, and a rolling 252-session mean IC chart.

**Pitfalls.** Do not choose split points after looking at the IC chart; fix halves by count. Removing a
"bad" sub-period after seeing it is a new trial (section 3.1).

**Acceptance checks.** A synthetic factor with IC +0.05 in the first half and −0.05 in the second is
flagged; the planted factor of 2.1 is not.

### 2.7 Market-neutral and sector-neutral variants

**Use when:** checking that the factor is not a disguised market-beta or sector bet.

**EODHD inputs:** benchmark series (`GSPC.INDX` is a **price** index, `adjusted_close == close`; `SPY.US`
`adjusted_close` includes dividends); sector labels from Fundamentals `General.GicSector` (or `Sector`),
10 calls per symbol, **current classification only**.

**Method.**

- **Market-neutral label:** `r^mn_{i} = r_i − r̄_t` (cross-sectional mean of eligible names on that date), or
  `r_i − β̂_i·r_mkt` with `β̂_i` estimated on a past window ending at `t` (for example 252 sessions of daily
  adjusted returns). Re-run 2.1–2.6.
- **Sector-neutral factor and label:** within each sector on each date, demean (or rank-normalise) both the
  factor and the label, then compute IC over the pooled demeaned values for that date. Require at least a
  few names per sector; drop sectors below that and record them.
- Compare raw, market-neutral and sector-neutral IC side by side.

**Pitfalls.** Current GICS labels applied to past dates are a retrospective assumption: companies that
changed sector are mis-grouped in the past. Label it, and treat sector-neutral results as indicative. A
factor whose IC disappears after sector neutralisation is a sector-rotation signal; that is a finding, not
an error.

**Acceptance checks.** A factor equal to the sector average of returns (a pure sector bet) has strong raw
IC and near-zero sector-neutral IC on synthetic data with sector effects.

### 2.8 Factor gates and feature-validation order

**Use when:** deciding whether a factor moves on to portfolio simulation.

Feature-validation order (stop at the first failure and record it):

1. Null share and coverage per date (minimum cross-section met on most dates).
2. Outliers: winsorise at training-period percentiles (for example 1%/99%), never using test data.
3. IC significance: NW `t` with lags ≥ `H−1`.
4. Stability: half-sample sign check and sub-period IC-IR (2.6).
5. Leakage flags: sustained daily |IC| above about 0.10 for a cross-sectional equity factor, no decay with
   horizon, or IC that collapses when the activation lag increases by one session. Any flag → investigate
   before proceeding.
6. Redundancy: correlation of the factor's per-date ranks (or IC series) with existing factors; high
   correlation (for example > 0.7) adds little breadth (section 3.10).
7. Neutral variants (2.7) and net-of-cost quantile spread (2.4).
8. Capacity and cost feasibility (section 5.5).

Indicative reading at daily frequency (declare your own; these are research defaults): |mean IC| < 0.02 is
weak; 0.02–0.05 is typical of usable equity signals; > 0.10 sustained is suspect. Record pass/fail per gate
and the number of factors tried, which feeds sections 3.3 and 3.9.

---

## 3. Overfitting and validation

### 3.1 Trial ledger

Every factor, parameter set, universe variant, cost assumption, horizon and abandoned idea is one trial.
Store for each: trial ID, timestamp, spec hash (section 10), parameters, per-period net return series,
IS/OOS boundaries, metrics, and status (kept/dropped). The count of trials `N` and the matrix of trial
returns are inputs to DSR (3.3), PBO (3.4) and multiple-testing control (3.9). A ledger that only contains
the survivors makes every later statistic optimistic. Link it from the
[research record](../assets/research-record.md).

Stagnation rule: if the last `k` trials (for example 10) produced no out-of-sample improvement, stop tuning
parameters. Change the signal family, horizon or universe instead, and log that pivot as a new trial
family rather than continuing a parameter search that only raises the trial count.

### 3.2 Probabilistic Sharpe ratio

**Use when:** asking "how likely is the true Sharpe above a benchmark Sharpe `SR*`, given sample length,
skew and fat tails?"

**Method.** With per-period returns `r_1..r_T`, `ŜR = mean/std` (per period), sample skewness `γ̂_3` and
sample kurtosis `γ̂_4` (raw, equal to 3 for a normal distribution):

```
PSR(SR*) = Φ( (ŜR − SR*) · √(T − 1) / √(1 − γ̂_3·ŜR + ((γ̂_4 − 1)/4)·ŜR²) )
```

`SR*` is per period too (an annual benchmark of 1.0 on daily data is `1/√252 ≈ 0.063`). `Φ` is the standard
normal CDF (`statistics.NormalDist().cdf`).

```python
from statistics import NormalDist
N01 = NormalDist()

def psr(returns, sr_star: float = 0.0) -> float:
    r = np.asarray(returns, dtype=float)
    T, sd = len(r), r.std(ddof=1)
    if T < 3 or sd == 0:
        return float("nan")                     # zero variance: undefined, not infinite
    sr = r.mean() / sd
    z = (r - r.mean()) / r.std(ddof=0)
    g3, g4 = (z ** 3).mean(), (z ** 4).mean()
    denom = 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2
    if denom <= 0:
        return float("nan")
    return N01.cdf((sr - sr_star) * math.sqrt(T - 1) / math.sqrt(denom))
```

**Pitfalls.** Feeding an annualised Sharpe into this formula is the most common error. Negative skew and
fat tails lower PSR for the same Sharpe. PSR is not a posterior probability of skill; it is a frequentist
statement under i.i.d.-like assumptions.

**Acceptance checks.** `psr` of a constant series is `nan`. For normal returns with per-period Sharpe 0.1
and `T = 1260`, PSR(0) > 0.99. Doubling `T` at fixed `ŜR > SR*` raises PSR.

### 3.3 Deflated Sharpe ratio

**Use when:** the reported strategy was selected from `N` trials and the user wants the Sharpe corrected
for that search.

**Method.**

1. Expected maximum Sharpe of `N` zero-skill trials (per period), with `γ ≈ 0.5772` (Euler-Mascheroni):

```
SR_0 = σ_SR · [ (1 − γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e)) ]
```

   `σ_SR` = standard deviation of the per-period Sharpe estimates across the trials in the ledger. With few
   trials (fewer than about 10) use the null approximation `σ_SR ≈ √(1/T)`.
2. `DSR = PSR(SR_0)` evaluated on the selected trial's returns.
3. `N` is the number of **independent** trials. Highly correlated trials count for less: estimate an
   effective `N` by clustering trial return series (for example, number of clusters whose average pairwise
   correlation is below 0.5) and report both the raw and effective `N`.
4. `N = 1` → `SR_0 = 0`, so DSR = PSR(0). State that no search was disclosed.

```python
def expected_max_sr(n_trials: int, sr_std: float) -> float:
    if n_trials < 2:
        return 0.0
    g = 0.5772156649015329
    return sr_std * ((1 - g) * N01.inv_cdf(1 - 1 / n_trials)
                     + g * N01.inv_cdf(1 - 1 / (n_trials * math.e)))

def dsr(returns, n_trials: int, sr_std: float | None = None) -> float:
    if sr_std is None:
        sr_std = math.sqrt(1 / len(returns))
    return psr(returns, expected_max_sr(n_trials, sr_std))
```

**Pitfalls.** Under-counting trials (only those that "made it to the notebook") inflates DSR. Mixing
trials with different sample lengths in `σ_SR` distorts it; compare on a common window.

**Acceptance checks.** Fifty pure-noise trials, `T = 1260`, select the best: its PSR(0) is typically above
0.95, its DSR averages about 0.5 across 20 seeds (individual seeds range roughly 0.3–0.9).
`expected_max_sr(50, √(1/1260))` ≈ 0.064 per period (≈ 1.0 annualised): a 1.0 annual Sharpe is what pure
search produces. A planted per-period Sharpe of 0.1 over 1,260 sessions gives mean DSR(N=50) near 0.8.

### 3.4 Probability of backtest overfitting (CSCV)

**Use when:** many configurations were tried on the same history and the user asks whether picking the
in-sample best is reliable.

**Method (combinatorially symmetric cross-validation).**

1. Build `M`, a `T × N` matrix of per-period net returns, one column per trial, on a common date index.
2. Split rows into `S` contiguous blocks of equal size (`S` even; 10 → 252 splits, 16 → 12,870 splits).
3. For every choice of `S/2` blocks as in-sample (IS), the rest out-of-sample (OOS):
   - compute the performance metric (Sharpe) of every trial on IS and OOS rows;
   - `n*` = IS-best trial;
   - relative OOS rank `ω = rank_OOS(n*) / (N + 1)`, rank 1 = worst;
   - logit `λ = ln(ω / (1 − ω))`.
4. `PBO = share of splits with λ ≤ 0` (the IS winner lands at or below the OOS median).
5. Report PBO, the λ histogram, and the regression of OOS on IS performance across splits (a negative
   slope means selection hurts).

```python
from itertools import combinations

def pbo_cscv(M: np.ndarray, S: int = 10):
    T, N = M.shape
    blocks = np.array_split(np.arange(T), S)

    def sharpe(rows):
        x = M[rows]
        sd = x.std(axis=0, ddof=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(sd > 0, x.mean(axis=0) / sd, -np.inf)

    lam = []
    for is_ids in combinations(range(S), S // 2):
        is_rows = np.concatenate([blocks[i] for i in is_ids])
        oos_rows = np.concatenate([blocks[i] for i in range(S) if i not in is_ids])
        best = int(np.argmax(sharpe(is_rows)))
        oos = sharpe(oos_rows)
        w = ((oos < oos[best]).sum() + 1) / (N + 1)
        lam.append(math.log(w / (1 - w)))
    lam = np.array(lam)
    return float((lam <= 0).mean()), lam
```

**Pitfalls.** CSCV mixes past and future blocks; it measures selection instability, not deployable
forward performance. Overlapping labels across block boundaries leak; purge as in 3.5 if trials use
multi-day labels. All trials must share costs and the date index.

**Acceptance checks.** Forty pure-noise trials, 1,000 periods, `S = 10`: PBO averages about 0.5 across
seeds (single seeds range roughly 0.3–0.8). Add a constant edge of 0.3 per-period standard deviations to
one trial: PBO falls to about 0.

### 3.5 Combinatorial purged cross-validation

**Use when:** training a model and wanting many out-of-sample paths instead of one walk-forward path.

**Method.**

1. Represent every sample by its label interval `[t_decision, t_label_end]`.
2. Partition the timeline into `N_g` contiguous groups. Choose `k` test groups. Number of splits
   `C(N_g, k)`; number of complete backtest paths `φ = k/N_g · C(N_g, k)` (for `N_g = 6, k = 2`: 15 splits,
   5 paths).
3. For each split: purge from training every sample whose label interval overlaps any test group's time
   span; then apply an embargo of `e` sessions after each test group (size `e` from the label horizon and
   feature persistence, for example `e ≥ H`).
4. Fit the whole pipeline (scaling, winsorising, feature selection, hyperparameters) on the purged training
   set only; predict the test groups.
5. Assemble the `φ` paths from the test-group predictions; compute the metric per path. Report the median
   path Sharpe, the share of paths with Sharpe ≤ 0, and the dispersion.
6. Check the training share retained after purging and embargo for each split; a split that keeps less than
   about half of the non-test data is unreliable.

**Pitfalls.** For panels, purge on the global time axis: the same calendar dates from another listing are
still overlapping information. CPCV is not a forward simulation because training data can follow the test
block; keep a final chronological holdout for the deployability claim.

**Acceptance checks.** `N_g = 6, k = 2` yields 15 splits; each group is a test group in exactly
`C(N_g−1, k−1) = 5` splits, which gives 5 complete paths. A label whose interval ends inside a test group's
span is never in that split's training set (unit test on intervals). Embargoed sessions after each test
group are absent from training.

### 3.6 Parameter-sweep plateau and cliff checks

**Use when:** the strategy has tunable parameters (lookbacks, thresholds, holding periods).

**Method.**

1. Declare the grid before running; run every cell; store every result in the trial ledger.
2. For each cell compute net Sharpe (at the base cost), max drawdown and Calmar.
3. Report:
   - share of cells with net Sharpe > 0;
   - **plateau ratio** = median net Sharpe of the optimum's immediate neighbours / optimum net Sharpe
     (≥ 0.5 suggests a plateau; < 0.5 a spike);
   - **cliff** = any neighbour whose Sharpe is below half the optimum's or of opposite sign;
   - **edge optimum** = best cell on the boundary of the grid → extend the grid and re-run (the extension
     adds trials);
   - a heatmap for two-parameter grids.
4. Prefer the centre of a plateau over the single best cell, and say so.

**Pitfalls.** Grids with very fine steps inflate trial counts without adding independent information;
DSR then uses an effective `N`. Choosing the grid after seeing a first result is itself selection.

**Acceptance checks.** A monotone synthetic surface (Sharpe rising with lookback) triggers the edge-optimum
flag. A single spike surrounded by zeros gives plateau ratio ≈ 0 and a cliff flag.

### 3.7 In-sample / out-of-sample decay rule

**Use when:** a strategy was developed on one period and the user wants a quick honesty check.

**Method.**

1. Chronological split, never shuffled (for example first 70% IS, last 30% OOS, aligned to whole
   sessions; for long histories use anchored walk-forward folds).
2. Compute annualised net Sharpe in each: `SR_IS`, `SR_OOS`.
3. `decay = 1 − SR_OOS / SR_IS` (defined when `SR_IS > 0`).
4. Declared default rule: **FAIL** if `SR_IS > 0.5` and `SR_OOS ≤ 0`; **WARN** if decay > 50%; otherwise
   pass this gate. `SR_OOS` well above `SR_IS` is not a failure but triggers a leakage audit (holdout
   touched, look-ahead in features, OOS regime unusually favourable).

**Pitfalls.** Once the OOS period has been looked at and the strategy changed, it is in-sample. Keep a final
holdout untouched by iteration.

**Acceptance checks.** IS Sharpe 1.2 / OOS −0.1 → FAIL; IS 1.2 / OOS 0.5 → WARN (decay 58%); IS 1.2 / OOS
0.9 → pass (decay 25%).

### 3.8 Stationary block bootstrap confidence intervals

**Use when:** putting an interval around Sharpe, CAGR or max drawdown without assuming i.i.d. returns.

**Method (Politis-Romano stationary bootstrap).**

1. Choose a mean block length `b` (for daily returns, 10–20 sessions is a common default; longer when
   autocorrelation or volatility clustering is strong). Draw `B` resamples (≥ 1,000; 400 for quick checks).
2. Each resample: start at a random index; at each step, with probability `p = 1/b` jump to a new random
   index, else take the next index (wrapping around).
3. Compute the statistic per resample; report the 2.5–97.5 percentile interval and `p(stat ≤ 0)` (share of
   resamples with Sharpe ≤ 0).

```python
def stationary_bootstrap_sharpe(r, mean_block=20, n_boot=2000, seed=0, ppy=252):
    rng = np.random.default_rng(seed)
    r = np.asarray(r, dtype=float)
    T, p = len(r), 1.0 / mean_block
    out = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.empty(T, dtype=int)
        idx[0] = rng.integers(T)
        for t in range(1, T):
            idx[t] = rng.integers(T) if rng.random() < p else (idx[t - 1] + 1) % T
        x = r[idx]
        sd = x.std(ddof=1)
        out[b] = x.mean() / sd * math.sqrt(ppy) if sd > 0 else np.nan
    lo, hi = np.nanpercentile(out, [2.5, 97.5])
    return lo, hi, float(np.nanmean(out <= 0))
```

**Pitfalls.** The bootstrap reflects only the sample's own regimes; it cannot generate a crisis the sample
lacks. Bootstrapping the selected best trial without the selection step understates uncertainty (use DSR or
PBO for selection). State `b`, `B` and the seed.

**Acceptance checks.** Interval width shrinks as `T` grows (synthetic Sharpe ≈ 0.8: width about 2.9 at
`T = 252`, about 2.1 at `T = 1008` with `b = 20`). A zero-mean series gives `p(SR ≤ 0)` near 0.5.

### 3.9 Multiple testing: Bonferroni, Benjamini-Hochberg, Benjamini-Yekutieli

**Use when:** many factors, sub-periods or parameter sets were tested and the user asks which results are
real.

**Method.**

1. Collect every test from the ledger with its statistic `t_j` (NW or HAC) and degrees of freedom; convert
   to two-sided p-values (Student `t` with the df; the normal approximation `p = 2(1 − Φ(|t|))` is fine
   above about 60 observations).
2. **Bonferroni** (family-wise error): reject `j` if `p_j ≤ α/m`.
3. **Benjamini-Hochberg** (false discovery rate `α`): sort `p_(1) ≤ … ≤ p_(m)`; find the largest `k` with
   `p_(k) ≤ k·α/m`; reject tests `(1)…(k)`.
4. **Benjamini-Yekutieli** for arbitrarily dependent tests (factors built from the same prices usually
   are): use `α / Σ_{i=1..m} (1/i)` in place of `α` in step 3.
5. Report the survivor set under the chosen procedure, not the naive `|t| ≥ 2` list.

```python
def benjamini_hochberg(p, alpha=0.05, dependent=False):
    p = np.asarray(p, dtype=float)
    m = len(p)
    a = alpha / np.sum(1.0 / np.arange(1, m + 1)) if dependent else alpha
    order = np.argsort(p)
    passed = p[order] <= a * np.arange(1, m + 1) / m
    keep = np.zeros(m, dtype=bool)
    if passed.any():
        keep[order[: np.max(np.nonzero(passed)[0]) + 1]] = True
    return keep
```

**Acceptance checks.** Thirty pure-noise `t` statistics: about 1.4 naive `|t| ≥ 2` hits on average, BH
survivors in only about 5% of runs. p-values `[0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205,
0.212, 0.216]` at α = 0.05 → BH keeps the first two only.

### 3.10 Effective breadth and the fundamental law

**Use when:** a claimed information ratio rests on "many independent bets".

**Method.**

- Effective number of independent bets among `N` with average pairwise correlation `ρ̄`:
  `N_eff = N / (1 + (N − 1)·ρ̄)`. Measure `ρ̄` from EODHD return series of the positions (residual returns
  after market if the book is market-neutral) or from the signal series, over a stated window.
- Breadth per year `BR = N_eff × independent rebalances per year` (with overlapping horizons, rebalances per
  year ≈ `252/H`).
- Fundamental law sanity check: `IR ≈ TC · IC · √BR`, with transfer coefficient `TC ≤ 1` (1 for an
  unconstrained book; lower with long-only, turnover or position limits).
- A backtest IR far above `TC·ĪC·√BR` points to leakage, under-counted risk or an IC measured differently
  from the portfolio.

**Acceptance checks.** `N = 20, ρ̄ = 0.7` → `N_eff ≈ 1.40`. `N = 500, ρ̄ = 0` → 500. IC 0.03 with
`N_eff = 100` names rebalanced monthly (`BR = 1,200`) → IR ≈ 1.04 at `TC = 1`.

### 3.11 Cost ladder and the PASS / WARN / FAIL backtest verdict

**Use when:** deciding whether a backtest is believable before paper trading. On FAIL, the rejection is the
deliverable.

**Honest metric set** (computed once, one way, from the same net return series): total return, CAGR
(requires positive start and end equity), annualised volatility, Sharpe with stated risk-free rate and
frequency, Sortino, max drawdown and duration, Calmar = CAGR/|MaxDD|, win rate, profit factor, trade
count, and turnover. Formulas for the risk metrics are in [portfolio and risk](portfolio-risk.md).

**Turnover and cost ladder.**

```
traded_t      = Σ_i |w^target_{i,t} − w^drifted_{i,t}|        (fraction of NAV traded, buys + sells)
one-way TO_t  = 0.5 · traded_t
net_t         = gross_t − traded_t · c · 10⁻⁴      for c ∈ {0, 5, 10, 25, 50} bps one-way
```

`w^drifted` are the previous target weights after one period of price moves, not the previous targets. Add
a borrow column for shorts: `− Σ_{short} |w_i| · borrow_annual / P` (borrow rates are user-supplied; EODHD
has no borrow data).

```python
def cost_ladder(gross: pd.Series, traded: pd.Series, bps=(0, 5, 10, 25, 50), ppy=252):
    res = {}
    for c in bps:
        net = gross - traded * c * 1e-4
        sd = net.std(ddof=1)
        res[c] = net.mean() / sd * math.sqrt(ppy) if sd > 0 else float("nan")
    return res
```

**Verdict (declared defaults; record the thresholds used in the output).**

| Verdict | Conditions |
|---|---|
| **FAIL** (any one) | a temporal-admissibility or identity check failed; net Sharpe ≤ 0 at 10 bps; IS/OOS FAIL (3.7); half-sample sign flip; DSR < 0.5; PBO ≥ 0.5 |
| **WARN** (any one, no FAIL) | net Sharpe ≤ 0 at 25 bps; IS/OOS decay > 50%; DSR 0.5–0.95; bootstrap `p(SR ≤ 0)` ≥ 0.05; parameter cliff or edge optimum; capacity below the user's intended size |
| **PASS** | none of the above |

Strongest permitted claim on PASS: "survived validation on the disclosed information set and cost
assumptions". Never "proven", "guaranteed" or "risk-free". A PASS does not authorise live trading (see
[paper accounting](paper-accounting.md)).

**Acceptance checks.** Synthetic gross returns with mean 0.0006 and std 0.005 per day, trading 50% of NAV
per day: annualised Sharpe ≈ 2.6 at 0 bps, ≈ 1.0 at 10 bps, negative at 25 bps → WARN by the 25 bps rule
(assuming other gates pass). A zero-turnover strategy has identical Sharpe on every rung. A noise strategy
selected from 50 trials fails on DSR.

### 3.12 Sequential model-validation gates

> Record what passed each gate in the [governance manifest](../assets/governance-manifest.md).

**Use when:** a model or strategy moves from idea to paper stage; each gate's outcome is recorded with
evidence (test name, run ID, capture IDs).

| Gate | Test | Recorded outcome |
|---|---|---|
| G0 Data | admissibility (temporal, identity, units), coverage per date, missing-data policy | pass/fail + exclusions |
| G1 Signal | factor gates of 2.8 | per-gate pass/fail |
| G2 Baseline | beats buy-and-hold / equal-weight / cash on the same dates and costs | metric deltas |
| G3 Cross-validation | CPCV median path Sharpe > 0, share of losing paths, purge share | numbers |
| G4 Selection | DSR with trial count, PBO, BH survivors | numbers |
| G5 Robustness | parameter plateau, sub-periods, regimes (4.4), cost ladder | flags |
| G6 Capacity | section 5.5 at intended size | AUM limit |
| G7 Holdout | final untouched chronological holdout, evaluated once; degradation vs CV | decay |
| G8 Paper | forward paper period with the outcome ledger (7.1) and drift monitors (9) | live-vs-backtest gap |

A failed gate stops promotion; a re-run after a change is a new trial. Very small degradation from CV to
holdout combined with a high Sharpe is a reason to audit for leakage, not a reason to celebrate.

### 3.13 Exit-rule lab

**Use when:** "Should I hold, take profit at +x%, trail a stop, or exit on a signal?" for an entry rule that
is already defined. The lab compares exits on the same entries under the validation rules of this
section.

**EODHD inputs.** EOD OHLC with `adjusted_close` for every symbol in the universe, including delisted
listings (`exchange-symbol-list?delisted=1`), 1 call per symbol. Adjusted O/H/L =
raw × `adjusted_close/close` of the same day. ATR is computed on the same basis. Exit definitions (ATR
and chandelier stops, R targets, time exits) follow
[technical-market §10](methods-technical-market.md); this section adds the comparison protocol.

**Method.**

1. Fix the entry rule and generate the entry cohort once: every signal in the sample, entered at the next
   session's open. Exit variants never change the entries.
2. Declare the exit menu before running. Each item, and each parameter value, is a trial (3.1):
   - time: hold `N` sessions, exit at the next open;
   - fixed target and stop (percent or R multiples);
   - tiered: part at +1R, remainder on a trailing stop;
   - trailing percent from the highest high since entry;
   - chandelier `HH − m·ATR` (ratchets up only);
   - signal: close below `SMA_n`, decided at the close and filled at the next open;
   - any of these with a maximum holding period.
3. Simulation rules:
   - one adjusted basis per trade;
   - intrabar stop and target hits from the bar's high and low;
   - a gap through a level fills at the open;
   - when stop and target fall in the same bar, the stop comes first;
   - ratchets update after the bar's checks;
   - trades still open at the end of the sample are closed at the last close and flagged, never dropped;
   - per-side costs from 5.1.
4. Per variant, on the same entries: trade count, mean and median return per trade, hit rate, average
   holding in sessions, exposure (share of sessions invested), CAGR and MaxDD of a portfolio with a declared
   sizing rule, profit factor, the share of exits by reason, and
   **give-back** = `(MFE − realised return) / MFE`, averaged over trades with `MFE > 0`.
5. Compare each variant with the baseline (hold `N`) by per-trade differences on the same entries. Put a
   stationary block bootstrap interval (3.8) on the mean difference, with blocks over entry dates, because
   trades overlap in time.
6. Choose on the in-sample period, then evaluate once out of sample (3.7). Run DSR (3.3) with
   `N` = entry variants × exit variants, and the plateau check (3.6) on parameter grids such as trail
   2%–15%.

```python
def run_exit(o, h, l, c, i0, rule, atr=None, sma=None):
    """Long trade entered at the open of session i0. Returns (exit index, exit price, MFE, reason)."""
    e = o[i0]
    stop = e * (1 - rule["stop"]) if "stop" in rule else -np.inf
    target = e * (1 + rule["target"]) if "target" in rule else np.inf
    hh, mfe = e, 0.0
    max_n = rule.get("max_sessions", 10 ** 9)
    for i in range(i0, len(c)):
        if i > i0 and o[i] <= stop:
            return i, o[i], mfe, "stop_gap"
        if l[i] <= stop:
            return i, stop, mfe, "stop"                      # stop first in an ambiguous bar
        if i > i0 and o[i] >= target:
            return i, o[i], max(mfe, o[i] / e - 1), "target_gap"
        if h[i] >= target:
            return i, target, max(mfe, target / e - 1), "target"
        hh, mfe = max(hh, h[i]), max(mfe, h[i] / e - 1)
        k = rule["kind"]
        if k == "trailing_pct":
            stop = max(stop, hh * (1 - rule["trail"]))
        elif k == "chandelier" and atr is not None and not np.isnan(atr[i]):
            stop = max(stop, hh - rule["m"] * atr[i])
        if ((k == "signal" and sma is not None and c[i] < sma[i]) or i - i0 + 1 >= max_n) and i + 1 < len(c):
            return i + 1, o[i + 1], mfe, "signal" if k == "signal" else "time"
    return len(c) - 1, c[-1], mfe, "open_at_end"

def give_back(entry, exit_px, mfe):
    ret = exit_px / entry - 1
    return ret, ((mfe - ret) / mfe if mfe > 0 else float("nan"))
```

**Pitfalls.** Triggering on a close and filling at that same close is look-ahead. Close-only data hides
intrabar wicks, so tight stops look better than they are. Dropping delisted names removes the worst exits.
Exits with different holding periods carry different exposure; compare risk-adjusted results, not raw
return per trade. Give-back is undefined when MFE = 0.

**Acceptance checks.** Deterministic path: closes rise from 100 to 110 by 1 per session, then fall by 1
per session; each open equals the prior close; high and low are `max/min(open, close) ± 0.5`; entry at the
open of session 1 (100).

| Rule | Exit | Price | Return | MFE | Give-back |
|---|---|---|---|---|---|
| time, 5 sessions | open of session 6 | 105.00 | 5.00% | 5.5% | 0.091 |
| target +5% / stop −5% | session 5, target | 105.00 | 5.00% | 5.0% | 0 |
| trailing 3% | session 13, stop | 107.185 | 7.18% | 10.5% | 0.316 |
| close < SMA(3) | open of session 12 | 109.00 | 9.00% | 10.5% | 0.143 |

A single bar with high 106 and low 94 against a 105 target and a 95 stop exits at the stop, 95.

---

## 4. Stationarity and regime features

### 4.1 ADF and KPSS jointly

**Use when:** deciding whether a series can be used as a model input in levels or needs transformation, and
for pair spreads (section 6).

**Method.**

- **ADF** (null: unit root). Regress `Δy_t = a [+ b·t] + φ·y_{t−1} + Σ_{j=1..p} c_j Δy_{t−j} + e_t`; the
  statistic is the `t` of `φ`. Lags `p` by AIC up to `⌊12(T/100)^(1/4)⌋`. Asymptotic critical values,
  constant only: 1% −3.43, 5% −2.86, 10% −2.57; constant + trend: −3.96, −3.41, −3.12.
- **KPSS** (null: stationary). Residuals `e_t` from regressing `y` on a constant (level) or constant + trend;
  `S_t = Σ_{s≤t} e_s`; `KPSS = Σ S_t² / (T² · LRV)` with a Newey-West LRV. Critical values, level: 10%
  0.347, 5% 0.463, 1% 0.739; trend: 0.119, 0.146, 0.216.

| ADF rejects unit root? | KPSS rejects stationarity? | Reading |
|---|---|---|
| yes | no | stationary |
| no | yes | non-stationary (unit root) → difference |
| no | no | inconclusive (low power, short sample) → treat as non-stationary for modelling, gather data |
| yes | yes | conventionally difference-stationary or a structural break → difference; inspect for breaks |

Run the trend version of both when the series has an obvious deterministic trend; if ADF-ct rejects and
KPSS-trend does not, the series is trend-stationary (detrend rather than difference).

```python
def adf_tstat(y, lags=1, trend="c"):
    y = np.asarray(y, dtype=float)
    dy = np.diff(y)
    T = len(dy) - lags
    X = [y[lags:-1]] + [dy[lags - i:-i] for i in range(1, lags + 1)]
    if trend in ("c", "ct"):
        X.append(np.ones(T))
    if trend == "ct":
        X.append(np.arange(T, dtype=float))
    X, Y = np.column_stack(X), dy[lags:]
    beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    resid = Y - X @ beta
    cov = (resid @ resid / (T - X.shape[1])) * np.linalg.inv(X.T @ X)
    return beta[0] / math.sqrt(cov[0, 0])

def kpss_stat(y, trend="c", lags=None):
    y = np.asarray(y, dtype=float)
    T = len(y)
    if trend == "c":
        e = y - y.mean()
    else:
        X = np.column_stack([np.ones(T), np.arange(T)])
        e = y - X @ np.linalg.lstsq(X, y, rcond=None)[0]
    lags = lags or int(math.ceil(12 * (T / 100) ** 0.25))
    s = np.cumsum(e)
    lrv = e @ e / T
    for l in range(1, lags + 1):
        lrv += 2 * (1 - l / (lags + 1)) * (e[l:] @ e[:-l]) / T
    return (s @ s) / (T ** 2 * lrv)
```

(A statistics library gives the same tests with automatic lag selection and exact critical values; these
minimal versions make the definitions explicit.)

**Pitfalls.** Run the tests on the training window only. Price levels from `adjusted_close` are almost
always non-stationary; returns usually stationary in mean but not in variance. Passing a test once is no
guarantee of future stability (see [research validation](research-validation.md)).

**Acceptance checks.** A 1,000-step Gaussian random walk: ADF `t` above −2.86 (fails to reject) and KPSS
level well above 0.739 (rejects) → non-stationary. Its first difference: ADF `t` far below −3.43 and KPSS
below 0.347 → stationary.

### 4.2 Transforms

| Transform | Formula | Use |
|---|---|---|
| log return | `ln(P_t / P_{t−1})` on `adjusted_close` | prices, indices, FX |
| first difference | `y_t − y_{t−1}` | yields, spreads, rates (percentage points; ×100 for bp) |
| fractional difference | `Σ_k w_k y_{t−k}`, `w_0 = 1`, `w_k = −w_{k−1}(d − k + 1)/k`, truncate when `|w_k| < 10⁻⁴` | keep memory; choose the smallest `d` in 0…1 that passes ADF on training data |
| rolling z-score | `(x_t − mean_{t−W..t−1}) / std_{t−W..t−1}` | regime features; note the window excludes `t` |
| expanding percentile | rank of `x_t` among `x_{1..t−1}` | bounded 0–1 features |
| log level ratio | `ln(A_t / B_t)` | relative strength, spreads |

Fit any parameter (W, `d`, winsor bounds) on training data and freeze it. Rolling statistics need a
minimum number of observations; emit missing until it is met.

### 4.3 Lagged regime-feature catalogue from EODHD series

**Use when:** building regime features for risk scaling or for a per-regime evaluation table.

Every feature at decision `t` uses only observations available before the decision (default: through the
prior session's close, i.e. shifted one session). Store each feature's source capture and observation date.

| Feature | EODHD source | Definition | Notes |
|---|---|---|---|
| Implied-volatility level | `VIX.INDX` EOD `close` (from 1990) | trailing 252-session percentile of close | VIX volume is 0; INDX `adjusted_close == close` |
| Realised-volatility z | `SPY.US` or `GSPC.INDX` EOD | `σ20 = std(log returns, 20)·√252`; z vs trailing 252 values of `σ20` | GSPC is a price index |
| Trend | same | `close / SMA200 − 1`, or sign | warm-up 200 sessions |
| Curve slope | `/api/ust/yield-rates` (`date`, `tenor`, `rate` in percent; all plans; beta) | `10Y − 2Y`, `10Y − 3M` in percentage points | only where both tenors exist on the same date |
| Credit level | `/api/credit-risk/corporate/hqm-yields` (`as_of_date`, `tenor_years`, `yield_type`, `yield_value` percent) | HQM par yield − UST par yield at the matched tenor | observation frequency: verify with a probe; label as a corporate-spread proxy |
| CDS market structure | `/api/credit-risk/cds-market/aggregates` (`as_of_date`, `release_date`, `usd_notional_mn`) | change in gross notional by grade | use `release_date` as availability, not `as_of_date` |
| Funding stress | `/api/spreads/funding-stress` (`filter[code]` e.g. `EFFR_SOFR`, `OBFR_EFFR`; `filter[from]/[to]`) | level and 20-session change of the spread | spreads are in basis points; confirm the response fields with a probe |
| Policy rate | `/api/rates/policy-rates` | level, change since N sessions | step series; carry forward between decisions only as a labelled state |
| Breadth | `ADVN.INDX`, `DECN.INDX` closes (from 2007-11-09) | `(ADVN − DECN)/(ADVN + DECN)`, 10-session mean | NYSE only; `ADVQ` for Nasdaq |
| Participation | bulk EOD over a declared universe | % of names above their 200-day average | current membership → survivorship caveat |
| Correlation | universe or sector-ETF adjusted returns | average pairwise correlation over 63 sessions | align calendars; no zero-filled holidays |
| Macro | `macro-indicator` (annual series, 10 calls) or `economic-events` `actual` (first release, UTC time) | latest print available at `t` | annual CPI is annual; use the event release time, never the period label |

Cost: EOD series 1 call each for full history; UST 1 call per year-page; macro 10 calls per series.
Fundamentals Feed or All-In-One is needed for the credit, rates and macro endpoints (see
[plans and limits](plans-limits.md)).

**Pitfalls.** Hidden Markov or clustering regime models must be fitted walk-forward and read through
**filtered** state probabilities (using data up to `t`; procedure in 4.6). Smoothed probabilities use
future observations and leak. A regime named after the fact ("the 2022 rate shock") is not a feature known in real time.

**Acceptance checks.** For every feature, recomputing it on data truncated at `t−1` gives the same value as
the stored feature for decision `t`. The VIX percentile at the first session of a new 52-week high is 1.0
only if computed against prior values.

### 4.4 Regimes for risk scaling and per-regime reporting

**Use when:** making exposure respond to conditions, or showing where a strategy earns and loses.

**Method.**

- Prefer continuous scaling over binary in/out timing. Volatility targeting:
  `exposure_t = min(L_max, σ_target / σ̂_{t−1})` with `σ̂` from past returns (for example a 20-session or
  EWMA λ = 0.94 estimate). A percentile taper: `m_t = 1` below the 50th percentile of the feature,
  falling linearly to `m_min` at the 100th.
- Treat the scaling rule as one more set of trials in the ledger (section 3.1), with costs.
- Per-regime table: define regimes ex ante (for example terciles of the lagged VIX percentile, using
  expanding cut points), then report per regime: sessions, share of time, annualised return, volatility,
  Sharpe, max drawdown, hit rate and number of regime transitions.

**Pitfalls.** A filter that removes the worst months in-sample usually removes them by construction;
evaluate out of sample and net of the extra turnover. Regimes with few sessions give unstable Sharpe
values; show the session counts.

Statistical regime labels (change points, hidden Markov states, rolling Hurst) are in 4.5–4.7; each
feeds the same per-regime table.

**Acceptance checks.** Regime labels at `t` are reproducible from data through `t−1`. The per-regime table's
session counts sum to the total. Volatility targeting on a synthetic series with a variance jump reduces
exposure only after the jump has been observed.

### 4.5 CUSUM change points in mean and volatility

**Use when:** dating a shift in the mean return or the volatility of an index, a spread or a strategy's
P&L as it happens, to trigger a review or a regime label. It is an online detector, not a tool for
re-drawing history.

**EODHD inputs.** Any EOD series (1 call per symbol, full history); strategy P&L comes from the user's own
backtest or paper ledger.

**Method.**

1. Standardise with **training** statistics: `z_t = (x_t − μ_0)/σ_0`, with `μ_0, σ_0` frozen from a window
   that ends before monitoring starts.
2. Mean shift, two-sided Page CUSUM with reference value `k` (half the shift to detect, in σ units; 0.5
   for a 1σ shift) and threshold `h`:
   `S⁺_t = max(0, S⁺_{t−1} + z_t − k)`, `S⁻_t = max(0, S⁻_{t−1} − z_t − k)`; alarm when either exceeds `h`,
   then reset both to 0.
3. Volatility increase by a factor `ρ`, one-sided likelihood-ratio form on squared standardised values:
   `S_t = max(0, S_{t−1} + z_t² − k_ρ)` with `k_ρ = 2 ln ρ / (1 − 1/ρ²)` (1.848 for `ρ = 2`); alarm when
   `S_t > h`.
4. Choose `h` from the false-alarm budget, the average run length without a change (ARL0). The table is
   for Gaussian data (400 simulated paths each). Real returns have fat tails and volatility clusters, which
   shorten ARL0, so recalibrate `h` by block-bootstrapping the training residuals (3.8).

| Statistic | `k` | `h` | Mean ARL0 (sessions) | Mean detection delay |
|---|---|---|---|---|
| mean, two-sided | 0.5 | 4 | 150 | — |
| mean, two-sided | 0.5 | 5 | 408 | 8.3 sessions after a 1σ shift |
| volatility, `ρ = 2` | 1.848 | 8 | 264 | 4.7 sessions after σ doubles |
| volatility, `ρ = 2` | 1.848 | 10 | 597 | 5.8 |
| volatility, `ρ = 2` | 1.848 | 12 | 1,218 | 6.8 |

5. Record the alarm date (known in real time). The estimated change date (the last session at which the
   statistic was 0) is retrospective: label it so. Re-estimate `μ_0, σ_0` only from post-alarm data once
   enough of it has accrued.

```python
def cusum_alarms(x, mu0, sd0, k=0.5, h=5.0):
    """Two-sided Page CUSUM; mu0, sd0 from the training window. Statistics restart after an alarm."""
    sp = sn = 0.0
    alarms = []
    for t, zt in enumerate((np.asarray(x, dtype=float) - mu0) / sd0):
        sp, sn = max(0.0, sp + zt - k), max(0.0, sn - zt - k)
        if sp > h or sn > h:
            alarms.append(t)
            sp = sn = 0.0
    return alarms

def variance_cusum(r, sd0, rho=2.0, h=10.0):
    """One-sided CUSUM for volatility rising by the factor rho; sd0 from the training window."""
    k = 2 * math.log(rho) / (1 - 1 / rho ** 2)
    s, alarms = 0.0, []
    for t, x in enumerate(np.asarray(r, dtype=float) / sd0):
        s = max(0.0, s + x * x - k)
        if s > h:
            alarms.append(t)
            s = 0.0
    return alarms
```

**Pitfalls.** Feeding `(z² − 1)/√2` into the mean-shift rule looks natural but the squared values are
skewed: in our runs 95.5% of 500-session no-change paths alarmed. Use the likelihood-ratio form of
step 3. Full-sample change-point fits (binary segmentation, PELT and similar) use future data and are
descriptive only. If alarms drive positions, every `(k, h)` pair is a trial (3.1).

**Acceptance checks.** `x = [0, 0, 0, 0, 0, 2, 2, 2, 2, 2]`, `μ_0 = 0`, `σ_0 = 1`, `k = 0.5`, `h = 4` →
one alarm at index 7 (`S⁺` = 1.5, 3.0, 4.5). Alarms before session `t` are identical when the input is
truncated at `t`.

### 4.6 Gaussian hidden Markov regimes

**Use when:** the user wants probabilistic regimes (for example calm vs stressed) from index returns,
for risk scaling or a per-regime table (4.4).

**EODHD inputs.** `adjusted_close` of an index proxy (`SPY.US`; `GSPC.INDX` is a price index), 1 call;
optional second observation such as 21-session realised volatility (4.3). The code below is 1-D.

**Method.**

1. Observation `x_t` = daily log return. Model: `K` hidden states (2 or 3), transition matrix `A`
   (`a_ij = P(s_t = j | s_{t−1} = i)`), state densities `N(μ_k, σ_k²)`, initial distribution `π`.
2. Fit by Baum-Welch (EM) on the **training window only**, from several starting points; keep the highest
   log-likelihood. Order states by `σ_k` so that state 0 is always the calmest (this fixes label switching
   between refits).
3. Choose `K` by BIC on the training window: `BIC = −2 ln L + m ln T`, `m = K² + 2K − 1` free parameters
   for a 1-D Gaussian HMM.
4. Apply forward only. The filtered probability `p_t(k) = P(s_t = k | x_1..x_t)` follows the recursion
   `α_t ∝ (α_{t−1} A) ⊙ b(x_t)`. Smoothed (forward-backward) probabilities use `x_{t+1..T}`: description
   only, never a feature.
5. Walk-forward: refit every `M` sessions (for example 252) on data ending at the refit date, freeze the
   parameters until the next refit, and store the parameter version with each probability.
6. Persistence: expected duration of state `k` is `1/(1 − a_kk)` sessions. A state with an expected
   duration below about 5 sessions is noise for a daily allocation rule. Switch the published label with
   hysteresis (enter "stressed" when `p_t ≥ 0.6`, leave when `p_t ≤ 0.4`) and report switches per year.
7. Use: per-regime table (4.4), or exposure `m_t = 1 − c·p_t(stressed)` with a declared `c`. Each rule is a
   trial.

```python
def _pdf(x, mu, sd):
    return np.exp(-0.5 * ((x[:, None] - mu) / sd) ** 2) / (sd * math.sqrt(2 * math.pi))

def hmm_filter(x, pi, A, mu, sd):
    """Filtered P(state_t | x_1..x_t); uses no observation after t."""
    B = _pdf(np.asarray(x, dtype=float), mu, sd)
    out = np.empty_like(B)
    a = pi * B[0]
    out[0] = a / a.sum()
    for t in range(1, len(B)):
        a = (out[t - 1] @ A) * B[t]
        out[t] = a / a.sum()
    return out

def hmm_fit(x, K=2, n_iter=200, tol=1e-8, seed=0):
    """Baum-Welch on a TRAINING window. Smoothed weights are used for fitting only."""
    x = np.asarray(x, dtype=float)
    rng = np.random.default_rng(seed)
    mu = np.quantile(x, np.linspace(0.3, 0.7, K)) + 1e-4 * rng.standard_normal(K)
    sd = x.std() * np.linspace(0.5, 1.5, K)
    A = np.full((K, K), 0.05 / (K - 1)); np.fill_diagonal(A, 0.95)
    pi, prev, T = np.full(K, 1.0 / K), -np.inf, len(x)
    for _ in range(n_iter):
        B = _pdf(x, mu, sd) + 1e-300
        al, c = np.empty((T, K)), np.empty(T)
        al[0] = pi * B[0]; c[0] = al[0].sum(); al[0] /= c[0]
        for t in range(1, T):
            al[t] = (al[t - 1] @ A) * B[t]; c[t] = al[t].sum(); al[t] /= c[t]
        be = np.ones((T, K))
        for t in range(T - 2, -1, -1):
            be[t] = (A @ (B[t + 1] * be[t + 1])) / c[t + 1]
        g = al * be
        xi = sum(np.outer(al[t], B[t + 1] * be[t + 1]) * A / c[t + 1] for t in range(T - 1))
        pi, A = g[0], xi / xi.sum(axis=1, keepdims=True)
        w = g.sum(axis=0)
        mu = (g * x[:, None]).sum(axis=0) / w
        sd = np.sqrt((g * (x[:, None] - mu) ** 2).sum(axis=0) / w)
        ll = np.log(c).sum()
        if ll - prev < tol:
            break
        prev = ll
    o = np.argsort(sd)                                    # state 0 = calmest
    return pi[o], A[np.ix_(o, o)], mu[o], sd[o], ll
```

**Pitfalls.** Fitting on the full sample and then labelling history is look-ahead. Filtered probabilities
react several sessions after a true switch; that delay is the honest cost of the method. EM finds local
optima; use several starts. Fat tails create a "crash" state that holds a handful of sessions; check state
occupancy. Persistence estimates are noisy (see the acceptance numbers).

**Acceptance checks.** Simulated two-state returns (`A = [[0.98, 0.02], [0.04, 0.96]]`, `μ = (0.0005,
−0.001)`, `σ = (0.007, 0.02)`, 4,000 sessions, seed 3), fit on the first 3,000: `σ̂ = (0.0071, 0.0205)`,
`diag Â = (0.986, 0.964)`; the filtered state (`p > 0.5`) matches the true state on 89.7% of the last
1,000 sessions. Filtered probabilities computed on the test segment truncated after 500 sessions equal
the full-run values exactly. Expected durations 72.8 and 27.9 sessions against the true 50 and 25.

### 4.7 Rolling-Hurst regimes

**Use when:** labelling trending, mean-reverting or undetermined conditions for a strategy family
(momentum vs reversal) or for a per-regime table.

**Method.**

1. `H_t` = 6.3 estimate on the log price window `[t−W, t−1]` (`W = 252`, `max_lag = 20`), recomputed each
   session or each week.
2. Null band from the training window (5th–95th percentile of `H` on shuffled training returns).
3. Label trending if `H_t` is above the band, mean-reverting if below, otherwise "no evidence" (the usual
   case). Switch only after 5 consecutive sessions outside the band.
4. Lag the label by one session when it is used as a feature (4.3).

```python
def hurst_null_band(train_returns, window=252, max_lag=20, n_sim=300, seed=0, q=(5, 95)):
    rng = np.random.default_rng(seed)
    r = np.asarray(train_returns, dtype=float)
    sims = [hurst_lagged_var(np.cumsum(rng.choice(r, size=window, replace=False)), max_lag)
            for _ in range(n_sim)]
    return tuple(np.percentile(sims, q))
```

**Pitfalls.** The estimator's spread at `W = 252` (sd about 0.075) is larger than most real differences
between regimes, so the test has little power. Consecutive windows overlap, so labels are strongly
autocorrelated; count regime episodes, not sessions, as the sample size. Use the variance ratio (6.4) when
a p-value is needed.

**Acceptance checks.** One run (seed 5, 1,000 Gaussian training returns): band (0.353, 0.590). On a
3,000-session random walk, 11.6% of windows (every 5th session) fall outside the band, close to the 10%
built into the band. Cumulated AR(1) returns with `φ = 0.3` are labelled trending in 24.9% of windows, an
OU spread with half-life 10 mean-reverting in 51.8%: real effects are detected only part of the time.

### 4.8 Per-ticker fear score

> A market-practice variant with dashboard bands is in [methods-technical-market §21.2](methods-technical-market.md#212-per-ticker-fear-score); choose one definition per application.

**Use when:** "how stressed is this stock right now?". It is a descriptive composite with visible weights,
not a forecast. A user who wants to trade on it has a factor and goes through sections 2 and 3.

**EODHD inputs.**

| Component | Source and cost | Raw value at the close of `t` | Score 0–100 (higher = more fear) |
|---|---|---|---|
| Drawdown | EOD `adjusted_close`, 1 call (full history) | `dd = 1 − C_t / max(C_{t−251..t})` | percentile of `dd_t` among the listing's own previous 756 sessions |
| Realised volatility | same | `σ21 = std(log returns, 21)·√252` | own-history percentile |
| RSI | same, or `/api/technical?function=rsi` (5 calls) | Wilder RSI(14) | `100 − RSI` |
| Down-day volume | EOD `volume` (split-adjusted) | `V_t / median(V_{t−50..t−1})` on down sessions, 0 otherwise | own-history percentile |
| Down streak | EOD | consecutive down closes | `min(streak, 5)/5 × 100` |
| News sentiment | `/api/sentiments?s=SYM&from=&to=` (5 calls + 5 per ticker; fields `date`, `count`, `normalized` in −1…+1) | count-weighted mean of `normalized` over the last 5 days with data; require total `count` ≥ 10 | `(1 − s)/2 × 100` |
| IV rank | Marketplace US options EOD (10 calls per request; US underlyings; history from Q4 2023) → 30-day constant-maturity IV ([A6, A7](methods-options-rates-macro.md)) | IV rank over the past 252 sessions | rank × 100 |
| Put/call volume | same chain ([A5](methods-options-rates-macro.md)) | `PCR_vol` | own-history percentile; at least 120 past observations |

Default weights (declared research defaults, printed with every score): drawdown 0.25, realised volatility
0.20, RSI 0.10, down-day volume 0.10, down streak 0.05, sentiment 0.15, IV rank 0.10, put/call 0.05.

**Method.**

1. Compute each component at the close of `t`; windows end at `t`; percentiles compare `t` with earlier
   values only.
2. A component is missing when its input is stale (price inputs older than 2 sessions, no sentiment
   article in 5 days, no option chain for `t`) or its history is shorter than the minimum. Missing is never
   scored as 0 or 50.
3. `score = Σ_present w_i s_i / Σ_present w_i`; `coverage = Σ_present w_i / Σ_all w_i`. Below 0.6 coverage
   the result is "insufficient" and no score is shown.
4. Bands (labels, not thresholds with evidence): 0–25 calm, 25–50 normal, 50–75 elevated, 75–100 extreme.
5. Output the full component table (raw value, as-of date, score, weight used) and the coverage beside the
   composite.

```python
def past_percentile(s: pd.Series, lookback=756, min_obs=252) -> pd.Series:
    v = s.to_numpy(dtype=float)
    out = np.full(len(v), np.nan)
    for t in range(len(v)):
        past = v[max(0, t - lookback):t]
        past = past[~np.isnan(past)]
        if len(past) >= min_obs and not np.isnan(v[t]):
            out[t] = 100 * ((past < v[t]).mean() + 0.5 * (past == v[t]).mean())
    return pd.Series(out, index=s.index)

def wilder_rsi(c: pd.Series, n=14) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn)

def price_components(df: pd.DataFrame) -> pd.DataFrame:
    """One listing, sessions ascending: adjusted_close, split-adjusted volume."""
    c, v = df["adjusted_close"], df["volume"]
    r = np.log(c).diff()
    down = (r < 0).astype(int)
    return pd.DataFrame({
        "drawdown": past_percentile(1 - c / c.rolling(252, min_periods=252).max()),
        "realized_vol": past_percentile(r.rolling(21, min_periods=21).std() * np.sqrt(252)),
        "rsi": 100 - wilder_rsi(c),
        "down_volume": past_percentile((v / v.shift(1).rolling(50, min_periods=50).median()).where(r < 0, 0.0)),
        "down_streak": (down.groupby((down == 0).cumsum()).cumsum().clip(upper=5) / 5 * 100).astype(float),
    })

WEIGHTS = {"drawdown": 0.25, "realized_vol": 0.20, "rsi": 0.10, "down_volume": 0.10,
           "down_streak": 0.05, "sentiment": 0.15, "iv_rank": 0.10, "put_call": 0.05}

def fear_score(components: dict, weights=WEIGHTS, min_coverage=0.6):
    used = {k: w for k, w in weights.items() if components.get(k) is not None}
    coverage = sum(used.values()) / sum(weights.values())
    if coverage < min_coverage:
        return {"score": None, "coverage": round(coverage, 3), "status": "insufficient"}
    score = sum(components[k] * w for k, w in used.items()) / sum(used.values())
    band = "calm" if score < 25 else "normal" if score < 50 else "elevated" if score < 75 else "extreme"
    return {"score": round(score, 1), "coverage": round(coverage, 3), "band": band,
            "weights_used": {k: round(w / sum(used.values()), 3) for k, w in used.items()}}
```

**Pitfalls.** Own-history percentiles make a habitually volatile stock look calm next to a quiet one; for
a cross-sectional ranking use same-date percentiles across the universe and say which. Sentiment is a
vendor model over article text and is noisy at low article counts. Single-name put/call volume is thin;
market-wide put/call ratios are not EODHD data. Option inputs exist only for US underlyings and from
Q4 2023. `adjusted_close` history is restated after each new dividend or split; recompute, do not append.

**Acceptance checks.** Component scores (90, 80, 70, 60, 100, 65, 85, 50) in the weight order above →
77.2, "extreme", coverage 1.0. Without sentiment, IV rank and put/call → 80.7, coverage 0.7, weights
renormalised to 0.357/0.286/0.143/0.143/0.071. Only drawdown and volatility → coverage 0.45,
"insufficient". Synthetic listing (seed 0: 1,000 sessions of N(0.04%, 1%) returns with volume around
1,000,000, then 15 sessions of −2% on 2,500,000 shares): last session drawdown 100, realised volatility
90.9, RSI 92.4, down-day volume 98.1, streak 100 → 96.0 (price-only coverage 0.7); at its 252-session high
(session 859) → 8.5, "calm". Components at `t` are unchanged when data after `t` is removed.

---

## 5. Costs, impact and capacity

Order-book depth, queue position and fills are not EODHD data. Everything below is a labelled model on
bars, quotes snapshots or user-supplied fills, consistent with [backtesting](backtesting.md#execution-and-costs).

### 5.1 Per-rebalance cost model

```
cost_t (fraction of NAV) = Σ_i |Δw_i| · (commission_i + s_i/2 + slip_i)  +  Σ_i |Δw_i| · I_i
I_i  = Y · σ_d,i · √(Q_i / ADV_i)                                          (section 5.4)
Q_i  = |Δw_i| · NAV / P_i       (shares, on the same split basis as ADV_i)
```

`s_i` is the proportional bid-ask spread (section 5.3), `commission` and `slip` are user-supplied in
decimal of notional, `Y` is the impact coefficient. All costs are one-way per traded notional.

### 5.2 ADV and volatility from EODHD

- EOD `volume` is split-adjusted; `close` is raw. For currency volume on day `d`:
  `dollar_volume_d = close_d × volume_d / F_d`, where `F_d` = product of split ratios of splits **after**
  `d` (from `/api/splits/{SYM}`, 1 call). Equivalently, split-adjusted price × split-adjusted volume. Do not
  multiply raw close by split-adjusted volume across a split.
- `ADV` (shares) = median or mean of split-adjusted `volume` over the past 20–60 sessions ending at
  `t−1`; `ADV$` likewise from `dollar_volume`. The Technical API `avgvol` / `avgvolccy` functions (5 calls)
  are an alternative; verify their basis on a symbol with a recent split before relying on them.
- `σ_d` = standard deviation of daily log `adjusted_close` returns over 20–60 sessions ending at `t−1`.
- Convert `ADV$` to one currency with `*.FOREX` closes of the same date; normalise GBX/ZAC first.
- FX pairs have no volume; crypto volume aggregation differs by source. Impact models need a declared
  volume proxy there, or none.

### 5.3 Spread estimators from daily OHLC

**Use when:** historical bid-ask spreads are needed but EODHD has no historical quotes (EOD bars have no
bid/ask; `/api/ticks` records are trades only: `price`, `volume`, `mkt`, `sl`, `seq`). Current US bid/ask
comes from `/api/us-quote-delayed` (`bidPrice`, `askPrice`, `bidTime`, `askTime` in epoch ms; 1 call per
symbol; delayed snapshot) and is useful to calibrate the estimators below on today's universe.

**Corwin-Schultz (high-low).** For consecutive sessions `t−1, t` (consecutive in the exchange calendar,
not in rows):

```
β = [ln(H_t/L_t)]² + [ln(H_{t−1}/L_{t−1})]²
γ = [ln(max(H_t, H_{t−1}) / min(L_t, L_{t−1}))]²
α = (√(2β) − √β)/(3 − 2√2) − √(γ/(3 − 2√2))
S = 2(e^α − 1)/(1 + e^α)
```

Overnight adjustment: if day `t`'s low is above `C_{t−1}`, shift `H_t, L_t` down by the gap; if day `t`'s high
is below `C_{t−1}`, shift them up. Set negative two-day estimates to 0, then average over a month.

**Abdi-Ranaldo (close-high-low).** With mid-range `η_t = (ln H_t + ln L_t)/2` and `c_t = ln C_t`:

```
s²_t = 4 · (c_{t−1} − η_{t−1}) · (c_{t−1} − η_t)
S    = √(max(mean of s²_t over the window, 0))
```

```python
def corwin_schultz(high, low, close):
    """Inputs on one price basis; returns two-day estimates (fraction of price) indexed at day t."""
    h, l, c = high.astype(float), low.astype(float), close.astype(float)
    pc = c.shift(1)
    adj = (l - pc).clip(lower=0) + (h - pc).clip(upper=0)   # overnight gap shift for day t
    h2, l2, hp, lp = h - adj, l - adj, h.shift(1), l.shift(1)
    beta = np.log(h2 / l2) ** 2 + np.log(hp / lp) ** 2
    gamma = np.log(np.maximum(h2, hp) / np.minimum(l2, lp)) ** 2
    k = 3 - 2 * math.sqrt(2)
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / k - np.sqrt(gamma / k)
    return (2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))).clip(lower=0)

def abdi_ranaldo(high, low, close, window=21):
    eta, c = (np.log(high) + np.log(low)) / 2, np.log(close)
    s2 = 4 * (c.shift(1) - eta.shift(1)) * (c.shift(1) - eta)  # known at day t
    return np.sqrt(s2.rolling(window).mean().clip(lower=0))
```

**EODHD pitfalls.** Use one price basis inside each two-day window: multiply raw O/H/L/C by that day's
`adjusted_close/close` (or use the split-only `splitadjusted` function) so a split or ex-dividend day does
not create a false range. Daily bars are regular-session consolidated prices; a day with one trade has
`H = L` and carries no spread information. Thin names without rows on some sessions break the
consecutive-session requirement; skip those pairs. Both estimators are noisy per day and biased for very
liquid names (true spread smaller than tick-size effects); report monthly averages and label them
estimates.

**Acceptance checks.** Simulated prices (390 trades a day at mid ± 0.5% with a random-walk mid, 4,000 days,
true spread 1.00%): Corwin-Schultz mean ≈ 1.1%, Abdi-Ranaldo ≈ 1.0%. Doubling the true spread doubles both
estimates approximately. A series with `H = L` every day returns 0 from Corwin-Schultz.

### 5.4 Square-root market impact

**Use when:** costs depend on trade size relative to liquidity (capacity, large rebalances).

**Method.** Expected impact, as a fraction of price, of trading `Q` shares within about a day:
`I = Y · σ_d · √(Q / ADV)`. `Y` is a declared constant; values of order 0.5–1 are common in the literature,
so treat `Y` as a sensitivity parameter (report results at two values). Cost in currency
`= I · Q · P`, which scales with `Q^1.5`. For multi-day execution, apply per-day slices.

**Pitfalls.** The model is a cross-sectional average; it is not a forecast for a single order. It assumes
the trade is spread over the session; a market-on-close order behaves differently. Use split-consistent
`Q` and `ADV`. Do not apply it to FX (no volume) or to `.INDX` symbols (not tradable).

**Acceptance checks.** `Q/ADV = 1%`, `σ_d = 2%`, `Y = 1` → impact 0.20% (20 bps). Four times the size →
twice the bps. Doubling AUM at fixed weights raises per-trade impact by `√2`.

### 5.5 Safety margin and capacity

**Method.**

- **Safety margin** = expected gross edge per trade / expected round-trip cost (both in bps of notional,
  round trip = 2 × one-way). Report it per strategy and per liquidity bucket. A declared minimum (for
  example 2–3) protects against cost underestimation; below 1 the edge is consumed.
- **Participation capacity** with maximum participation `p_max` (for example 5–10% of ADV) and `D_exec`
  sessions allowed per rebalance:
  `AUM_part = min_i [ p_max · ADV$_i · D_exec / |Δw_i| ]` over names traded. Aggregate approximation:
  `AUM ≈ Σ_i (ADV$_i · p_max) / one-way turnover per rebalance`.
- **Cost capacity**: evaluate net expected return on a log grid of AUM values using 5.1 with impact; the
  AUM where net return reaches zero (or the user's hurdle) is the break-even capacity. Report the curve, not
  a single number.
- Show cost vs turnover and vs AUM.

**Acceptance checks.** A zero-turnover strategy pays zero cost at any AUM. With `p_max = 5%`, no simulated
fill exceeds 5% of that session's volume. Net return falls monotonically with AUM once impact is on.

### 5.6 TWAP and VWAP baselines from 1-minute bars

**Use when:** comparing user executions or simulated schedules with simple benchmarks.

**EODHD inputs:** `/api/intraday/{SYM}?interval=1m&from=&to=` (Unix seconds UTC, ≤ 120 days per request,
5 calls; EOD+Intraday Extended or All-In-One). Bars are stamped at bar start, fully unadjusted, US includes
pre/after-hours (filter to 09:30–16:00 America/New_York for the regular session), finalised about 2–3 hours
after the close. Null-filled bars mean no trades. Session calendar and early closes from
`/api/v2/exchange-details/{EX}`.

**Method.**

- **TWAP schedule:** split quantity `Q` evenly across `n` intervals of the execution window.
- **Volume profile:** for each regular-session bucket `b` (1m or 5m), `u_b = median over the past D
  sessions of v_{d,b} / Σ_b v_{d,b}`, renormalised to sum to 1. Exclude early-close days (build a separate
  profile) and sessions with a large share of null bars. `D` = 20 is a common default.
- **VWAP schedule:** `q_b = Q · u_b / Σ_{b∈window} u_b`.
- **Interval VWAP benchmark** (derived; EODHD has no VWAP field):
  `VWAP = Σ_b TP_b · v_b / Σ_b v_b` with typical price `TP_b = (H_b + L_b + C_b)/3`.

**Pitfalls.** Summed intraday volume is typically below consolidated daily volume, so profiles are shares,
not absolute volumes. DST shifts the UTC timestamps of the open; convert with the IANA zone, never a fixed
offset. Across a split the raw intraday prices jump; rescale earlier bars by the split ratio before
multi-day comparisons.

**Acceptance checks.** With identical volume in every bar, the VWAP schedule equals TWAP. The profile sums to
1. A DST-boundary day still yields 390 regular-session minutes for a full US session.

### 5.7 Transaction-cost analysis of user fills against intraday bars

**Use when:** "How good were my executions?" The fills, order times, quantities and fees are **user-
supplied**; EODHD supplies bars, not the user's executions or a trade-level consolidated tape.

**Method.** For an order with side `s` (+1 buy, −1 sell), decision price `P_dec` (user's decision time, or
the prior close if the decision was made on EOD data), arrival price `P_arr` = open of the first 1m bar at or
after order submission, average fill `P_fill`, filled fraction `f`, end-of-window price `P_end`:

| Component (bps of `P_dec`, positive = cost) | Formula |
|---|---|
| delay | `s · (P_arr − P_dec)/P_dec · f · 10⁴` |
| execution | `s · (P_fill − P_arr)/P_dec · f · 10⁴` |
| opportunity (unfilled part) | `s · (P_end − P_dec)/P_dec · (1 − f) · 10⁴` |
| fees | `fees / (Q_order · P_dec) · 10⁴` |
| implementation shortfall | sum of the four |
| vs interval VWAP | `s · (P_fill − VWAP)/VWAP · 10⁴` |
| participation | filled quantity / Σ bar volume in the window (overstated because bar volume is below consolidated volume; label it) |

```python
def tca(fills, bars, decision_px, decision_ts, end_ts, side, order_qty, fees=0.0):
    """fills: DataFrame[ts (UTC Timestamp), qty>0, px]; bars: /api/intraday 1m rows
    (timestamp = bar start, Unix s UTC), already filtered to the regular session."""
    b = bars.dropna(subset=["close"]).copy()
    b["ts"] = pd.to_datetime(b["timestamp"], unit="s", utc=True)
    win = b[(b.ts >= decision_ts) & (b.ts < end_ts)]
    arrival = float(win.iloc[0]["open"])
    tp, vol = (win.high + win.low + win.close) / 3, win.volume.fillna(0)
    vwap = float((tp * vol).sum() / vol.sum())
    filled = float(fills.qty.sum())
    avg_px = float((fills.qty * fills.px).sum() / filled)
    f, bp = filled / order_qty, 1e4 / decision_px
    out = {
        "delay_bps": side * (arrival - decision_px) * bp * f,
        "execution_bps": side * (avg_px - arrival) * bp * f,
        "opportunity_bps": side * (float(win.iloc[-1]["close"]) - decision_px) * bp * (1 - f),
        "fees_bps": fees / (order_qty * decision_px) * 1e4,
        "vs_vwap_bps": side * (avg_px - vwap) / vwap * 1e4,
        "participation": filled / float(vol.sum()) if vol.sum() > 0 else float("nan"),
    }
    out["shortfall_bps"] = sum(out[k] for k in ("delay_bps", "execution_bps", "opportunity_bps", "fees_bps"))
    return out
```

**Pitfalls.** Align broker timestamps (often local time) to UTC before matching bars. Intraday data for a
session is final only 2–3 hours after the close; do not run TCA on a provisional day. Extended-hours fills
need the extended-hours bars, not the regular-session profile. Fills on non-US venues need the venue's own
listing (`CODE.EXCHANGE`), not the US line. Bars cannot say whether a fill was at the bid or ask.

**Acceptance checks.** Synthetic case: decision 100.00, bars rising 0.01 per minute from 100.10, half of
2,000 shares filled at 100.50, last bar close 100.70, fees 10 → delay 5.0, execution 20.0, opportunity 35.0,
fees 0.5, shortfall 60.5 bps. A sell order on the mirrored (falling) path, filled at 99.50, gives the same
positive costs; a sell on the rising path shows negative (favourable) delay and execution.

### 5.8 Almgren-Chriss execution schedule

**Use when:** the user asks how fast to liquidate or build a large position, trading expected impact
against price risk, or wants a risk-averse schedule beside the TWAP and VWAP baselines (5.6). The output
is a simulated schedule under a stated impact model. It is not an order; EODHD has no order endpoints.

**EODHD inputs.** `σ_d` and `ADV` from EOD (5.2), price `P` (raw close of the decision date, same split
basis as ADV); 1-minute bars for a volume profile (5.6) if slices are mapped to clock or volume time.
The impact coefficients are model assumptions, not EODHD data.

**Model and formulas.** Sell (or buy) `X` shares over `T = N·τ` days in `N` slices of length `τ` days.
Holdings `x_j` at `t_j = jτ` (`x_0 = X`, `x_N = 0`), trades `n_j = x_{j−1} − x_j`.

| Symbol | Meaning | Unit |
|---|---|---|
| `σ` | price volatility, `σ_d·P` | currency per share per √day |
| `η` | temporary impact: price concession `η·n_j/τ` while trading at rate `n_j/τ` | currency per share per (share/day) |
| `γ` | permanent impact: price moves `γ·n_j` per slice and stays | currency per share per share |
| `ε` | fixed cost per share (half-spread, fees) | currency per share |
| `λ` | risk aversion: minimise `E + λ·V` | 1/currency |

```
η̃    = η − γτ/2                       (must be > 0)
κ̃²   = λσ²/η̃ ;   κ solves cosh(κτ) = 1 + κ̃²τ²/2
x_j  = X · sinh(κ(T − t_j)) / sinh(κT)        (λ = 0: x_j = X·(1 − t_j/T), the TWAP line)
E    = ½γX² + εX + (η̃/τ)·Σ_j n_j²            expected cost, currency
V    = σ²·τ·Σ_{j=1..N} x_j²                   variance of cost, currency²
```

**Method.**

1. `σ = σ_d·P` from 5.2.
2. Calibrate `η` by linearising the square-root model (5.4) at the planned average rate `v̄ = X/T`:
   `η = Y·σ_d·P·√(v̄/ADV) / v̄`. At `λ = 0` over one day the temporary cost then equals the 5.4 cost.
3. Declare the permanent impact as the price move it leaves after the whole order, `Δ_perm` (fraction of
   `P`): `γ = Δ_perm·P / X`. Report results for two values (for example `Δ_perm` = 0.1 and 0.3 of the
   5.4 impact `I`).
4. Compute the schedule for a grid of `λ`; plot the efficient frontier (`√V` against `E`); the user picks
   `λ` from it. Report `E` in currency and in bps of `X·P`.
5. Map slices to clock time; in volume time each slice is an equal share of the 5.6 profile.
6. Check the result against TWAP (`λ → 0`) and against the 5.4 cost.

```python
def almgren_chriss(X, N, tau, sigma, eta, gamma, lam, eps=0.0):
    eta_t = eta - 0.5 * gamma * tau
    if eta_t <= 0:
        raise ValueError("eta must exceed gamma*tau/2")
    t = np.arange(N + 1) * tau
    T = N * tau
    if lam == 0:
        x = X * (1 - t / T)
    else:
        kappa = math.acosh(0.5 * lam * sigma ** 2 / eta_t * tau ** 2 + 1) / tau
        x = X * np.sinh(kappa * (T - t)) / math.sinh(kappa * T)
    n = -np.diff(x)
    E = 0.5 * gamma * X ** 2 + eps * X + (eta_t / tau) * np.sum(n ** 2)
    V = sigma ** 2 * tau * np.sum(x[1:] ** 2)
    return x, n, float(E), float(V)
```

**Pitfalls.** Mixed time units are the usual error: `τ`, `σ` and `η` must all be in days (or all in
slices). Linear temporary impact understates the cost of high participation compared with the square-root
model; keep participation per slice under the 5.5 cap. `λ` is a preference, not an estimate. The model has
no intraday volume shape unless slices are in volume time, and no information about the order book.

**Acceptance checks.** `P = 50`, `σ_d = 2%`, `ADV = 1,000,000`, `X = 100,000` (10% of ADV) over one
day in 13 slices (`τ = 1/13`), `Y = 1` → `I = 0.632%`, `η = 3.162×10⁻⁶`, `γ = 3.162×10⁻⁷`
(`Δ_perm` = 0.1·`I`):

| `λ` | First slice, % of `X` | Holdings after 6 slices | `E` | `E`, bps | sd of cost |
|---|---|---|---|---|---|
| 0 (TWAP) | 7.69 | 53.8% | 33,082 | 66.2 | 54,393 |
| 10⁻⁶ | 8.40 | 51.9% | 33,148 | 66.3 | 53,148 |
| 10⁻⁵ | 13.60 | 38.6% | 37,238 | 74.5 | 44,773 |
| 10⁻⁴ | 34.96 | 7.6% | 88,341 | 176.7 | 23,746 |

The `λ = 0` cost equals `½γX² + η̃X²/T`. At `λ = 10⁻¹²` every slice is within 0.001 shares of TWAP.
Along a `λ` grid `E` rises and `V` falls monotonically.

---

## 6. Pairs, cointegration and mean-reversion statistics

**Use when:** testing a two-leg or basket mean-reversion idea, monitoring an existing pair, or asking
whether a single series (a price, a ratio, a spread) mean-reverts, follows a random walk or trends.

**EODHD inputs (all subsections):** `adjusted_close` for every leg (1 call each, full history), in one
currency (convert with `*.FOREX` closes of the same date) and aligned on sessions where all legs traded.
Legs on different exchanges close at different times; record the non-synchronous close. Every test below
runs on the training window only; its parameters are then frozen for the test period.

### 6.1 Engle-Granger for two legs

**Method.**

1. Confirm both log price series are non-stationary (4.1).
2. Hedge regression on training data: `ln P^y_t = α + β ln P^x_t + ε_t`. Freeze `α, β`. (Total least
   squares or the reverse regression give different `β`; choose one and keep it.)
3. ADF on the residual spread `s_t = ln P^y_t − α − β ln P^x_t` with **Engle-Granger** critical values (two
   variables, constant): 1% −3.90, 5% −3.34, 10% −3.04. Standard ADF values are too lenient here.
4. Half-life from `Δs_t = a + b·s_{t−1} + e_t`: `HL = −ln 2 / ln(1 + b)` sessions (requires −1 < b < 0).
   This is the same number as the Ornstein-Uhlenbeck half-life of 6.5.
5. Signal: `z_t = (s_t − μ) / σ` with `μ, σ` from training or a trailing window of a few half-lives ending at
   `t−1`. Declared rules, for example enter at `|z| > 2`, exit at `|z| < 0.5`, stop at `|z| > 4` or after
   3 × HL sessions. Every rule variant is a trial. Band arithmetic is in 6.5.
6. Out-of-sample: keep `β` fixed, or re-estimate only in walk-forward steps; monitor a rolling EG statistic
   on past windows and stop trading the pair when it is no longer significant.
7. Costs on both legs (5.1) plus borrow on the short leg (user-supplied).
8. Three or more legs: Johansen procedure (6.2).

```python
def half_life(spread) -> float:
    s = pd.Series(spread).dropna()
    ds, lag = s.diff().dropna(), s.shift(1).dropna()
    X = np.column_stack([np.ones(len(lag)), lag.values])
    a, b = np.linalg.lstsq(X, ds.values, rcond=None)[0]
    return -math.log(2) / math.log(1 + b) if -1 < b < 0 else float("inf")
```

**Pitfalls.** Correlation is not cointegration. Selecting pairs over the full sample and then backtesting
them is look-ahead; select on training data only and count every candidate pair as a trial (section 3.9).
Ratio spreads (`P^y / P^x`) assume `β = 1` in logs. Corporate actions are absorbed by `adjusted_close`;
cash P&L uses raw prices and actual dividends. A pair whose one leg is delisted needs the delisted history
and an unresolved-proceeds policy (see [backtesting](backtesting.md)).

**Acceptance checks.** Synthetic `y = 2 + 1.5x + OU(half-life 10)` with `x` a random walk: `β̂ ≈ 1.5`,
residual ADF `t` ≈ −6.5 (rejects), half-life estimate within about ±20% of 10 on 5,000 steps. Two
independent random walks: residual ADF `t` above −3.34 in about 95% of seeds.

### 6.2 Johansen test for three or more legs

**Use when:** a basket of three or more listings (an ETF against its largest holdings, three banks of one
country, a futures-proxy ETF triplet) may share one or more stationary combinations, or a two-leg test
should not depend on which leg is the dependent variable.

**Method (training window only).**

1. Confirm that each leg's log price is non-stationary (4.1). A stationary leg adds one to the rank by
   itself and produces a meaningless "cointegrating" vector that loads on that leg alone.
2. Choose the VAR lag order `p` in levels by AIC or BIC on training data (1–2 is typical for daily prices).
   The error-correction form then has `k = p − 1` lagged differences.
3. Error-correction model for the `n`-vector of log prices `Y_t`:
   `ΔY_t = c + Π·Y_{t−1} + Σ_{i=1..k} Γ_i·ΔY_{t−i} + e_t`. The rank `r` of `Π` is the number of
   cointegrating relations (0 = none, `n` = every leg stationary).
4. Reduced-rank regression. Regress `ΔY_t` and `Y_{t−1}` on the lagged differences and a constant; call the
   residuals `R_0` and `R_1` (`T` rows). `S_ij = R_i' R_j / T`. The eigenvalues `λ_1 ≥ … ≥ λ_n` of
   `S_11⁻¹ S_10 S_00⁻¹ S_01` lie in [0, 1).
5. Statistics for H0 "rank ≤ r":

```
trace(r)  = −T · Σ_{i=r+1..n} ln(1 − λ_i)
maxeig(r) = −T · ln(1 − λ_{r+1})
```

6. Rank choice: test `r = 0, 1, …` in order; `r̂` is the first `r` whose statistic is below its critical
   value. Report both statistics. If trace and max-eigenvalue disagree, report both and trade only the
   smaller rank.
7. Critical values at 5% for the case used here (unrestricted constant in the error-correction model,
   that is a drift in the levels). Source: the MacKinnon-Haug-Michelis (1999) tabulation, which statsmodels
   ships as `coint_johansen(det_order=0)`. The other cases (no constant, constant restricted to the
   cointegrating relation, trend) use different tables; name the case in the output.

| `n − r` | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| trace, 5% | 3.84 | 15.49 | 29.80 | 47.85 | 69.82 |
| max-eigenvalue, 5% | 3.84 | 14.26 | 21.13 | 27.59 | 33.88 |

8. Spread: the eigenvector of `λ_1`, normalised so that one leg's weight is 1, gives `s_t = β'Y_t` (log
   price units). Fit 6.5 on it. Share counts per leg are `β_i × gross notional / P_i` on the raw price of the
   trade date. With `r̂ > 1` any rotation of the first `r̂` vectors is also valid; pick one by an economic
   rule declared before looking at the backtest.
9. Freeze `β`; re-estimate only in walk-forward steps. Every basket tested is a trial (3.1, 3.9).

```python
def johansen(Y, k_ar_diff=1):
    """Y: T x n log prices (training window). Unrestricted constant. Returns eigenvalues (descending),
    trace and max-eigenvalue statistics for r = 0..n-1, and eigenvectors (columns, same order)."""
    Y = np.asarray(Y, dtype=float)
    dY = np.diff(Y, axis=0)
    T = len(dY) - k_ar_diff
    Z0, Z1 = dY[k_ar_diff:], Y[k_ar_diff:-1]
    lags = [dY[k_ar_diff - i:-i] for i in range(1, k_ar_diff + 1)]
    X = np.column_stack(lags + [np.ones(T)])
    def resid(A):
        return A - X @ np.linalg.lstsq(X, A, rcond=None)[0]
    R0, R1 = resid(Z0), resid(Z1)
    S00, S11, S01 = R0.T @ R0 / T, R1.T @ R1 / T, R0.T @ R1 / T
    lam, vec = np.linalg.eig(np.linalg.solve(S11, S01.T) @ np.linalg.solve(S00, S01))
    order = np.argsort(lam.real)[::-1]
    lam, vec = lam.real[order], vec.real[:, order]
    n = Y.shape[1]
    trace = np.array([-T * np.sum(np.log(1 - lam[r:])) for r in range(n)])
    maxeig = np.array([-T * math.log(1 - lam[r]) for r in range(n)])
    return lam, trace, maxeig, vec

TRACE_5 = {1: 3.8415, 2: 15.4943, 3: 29.7961, 4: 47.8545, 5: 69.8189}     # key = n - r
MAXEIG_5 = {1: 3.8415, 2: 14.2639, 3: 21.1314, 4: 27.5858, 5: 33.8777}

def johansen_rank(stat, n, crit=TRACE_5):
    for r in range(n):
        if stat[r] < crit[n - r]:
            return r
    return n
```

**Pitfalls.** The asymptotic critical values over-reject in short samples (a few hundred sessions with three
or more legs). Multiply the statistics by `(T − n·p)/T` (the Reinsel-Ahn small-sample factor) or bootstrap
the null, and say which. The result depends on the lag order; show the rank at `p` and `p + 1`. A break in
the relation (merger, index change, regulation) breaks the test; inspect the rolling spread. Baskets across
exchanges carry non-synchronous closes that look like mean reversion.

**Acceptance checks.** Synthetic three-leg system, `T = 2,000`: `x1` a random walk, `x2 = 0.5·x1 + random
walk`, `x3 = x1 − 0.8·x2 + OU(half-life 10)`. Results: trace (111.34, 12.64, 2.26) and max-eigenvalue
(98.70, 10.38, 2.26) → `r̂ = 1` by both; normalised vector (−1.01, 0.797, 1) against the true (−1, 0.8, 1);
the statistics equal statsmodels' `coint_johansen(Y, 0, 1)` to two decimals. Three independent random
walks (`T = 1,000`, 200 seeds): `r̂ > 0` in 6% of seeds against 5% nominal.

### 6.3 Hurst exponent

**Use when:** asking whether a level series (log price, ratio or spread) spreads out more slowly than a
random walk (mean reversion), at the same rate, or faster (persistence); also as a regime feature (4.7).

**Method.**

1. Work on the **level** series `x_t` (log `adjusted_close`, or the spread of 6.1/6.2), not on returns.
2. For lags `τ = 2 … τ_max` compute `sd_τ = std(x_{t+τ} − x_t)`. Under scaling, `sd_τ ∝ τ^H`.
3. `H` = OLS slope of `ln sd_τ` on `ln τ`. Reading: `H ≈ 0.5` random walk; `H < 0.5` mean-reverting;
   `H > 0.5` persistent. Keep `τ_max` well below a tenth of the window (20 for a 252-session window).
4. Judge `H` against a null band, not against 0.5: shuffle the training-period returns (which keeps their
   distribution and removes serial dependence), rebuild levels of the same length, estimate `H` many times
   and take the 5th and 95th percentiles (code in 4.7). Only an estimate outside that band is evidence.
5. The rescaled-range (R/S) estimator on returns is a common alternative. It is biased upward in small
   samples: on 252 i.i.d. returns with block sizes 8–128 it averaged 0.587 in our runs, so compare it with
   its own null band (or the Anis-Lloyd expected value), never with 0.5.

```python
def hurst_lagged_var(level, max_lag=20) -> float:
    """Variance-of-lagged-differences Hurst estimate on a LEVEL series (log price or spread)."""
    x = np.asarray(level, dtype=float)
    lags = np.arange(2, max_lag + 1)
    sd = np.array([np.std(x[l:] - x[:-l]) for l in lags])
    return float(np.polyfit(np.log(lags), np.log(sd), 1)[0])
```

**Pitfalls.** Small windows are noisy and biased low: on 252-session random walks the estimate averaged
0.474 with standard deviation 0.075 (5th–95th percentile 0.35–0.59), so 0.45 against 0.55 in one window
means nothing. A deterministic trend in the level raises `H`; detrend only if the trend is part of the
hypothesis. `H` is a descriptive exponent with no p-value; for a test use the variance ratio (6.4) or ADF
(4.1).

**Acceptance checks.** `max_lag = 20`, `T = 2,000`, 200 seeds: Gaussian random walk mean 0.497 (sd 0.027);
OU spread with half-life 10 sessions mean 0.373; cumulated AR(1) returns with `φ = 0.3` mean 0.557.

### 6.4 Variance ratio test (Lo-MacKinlay)

**Use when:** testing the random-walk null for a log price or spread with a p-value, at chosen horizons. It
complements ADF: it has power against short-horizon mean reversion and momentum in returns.

**Method.** Levels `p_0 … p_T` (log), one-period changes `r_t = p_t − p_{t−1}` (`T` of them), horizon `q`:

```
μ̂      = (p_T − p_0) / T
σ̂²_a   = Σ_t (r_t − μ̂)² / (T − 1)
σ̂²_c(q) = Σ_{t=q..T} (p_t − p_{t−q} − q·μ̂)² / m,     m = q·(T − q + 1)·(1 − q/T)
VR(q)  = σ̂²_c(q) / σ̂²_a
z(q)   = (VR − 1) / √( 2(2q − 1)(q − 1) / (3qT) )                       (homoskedastic)
δ̂_j    = T · Σ_{t=j+1..T} (r_t − μ̂)²(r_{t−j} − μ̂)² / [Σ_t (r_t − μ̂)²]²
θ̂(q)   = Σ_{j=1..q−1} [2(q − j)/q]² · δ̂_j
z*(q)  = (VR − 1) / √( θ̂(q) / T )                                        (heteroskedasticity-robust)
```

`VR < 1` = mean reversion over `q` periods, `VR > 1` = persistence. Report `z*` for financial returns.
Test `q ∈ {2, 5, 10, 20}`; with several `q`, control the family (Bonferroni `α/m`, or the Chow-Denning
maximum-|z*| test) rather than reporting the best `q`.

```python
def variance_ratio(logp, q):
    p = np.asarray(logp, dtype=float)
    r = np.diff(p)
    T = len(r)
    mu = (p[-1] - p[0]) / T
    var_a = np.sum((r - mu) ** 2) / (T - 1)
    m = q * (T - q + 1) * (1 - q / T)
    vr = np.sum((p[q:] - p[:-q] - q * mu) ** 2) / m / var_a
    z = (vr - 1) / math.sqrt(2 * (2 * q - 1) * (q - 1) / (3 * q * T))
    e2 = (r - mu) ** 2
    theta = sum((2 * (q - j) / q) ** 2 * T * np.sum(e2[j:] * e2[:-j]) / np.sum(e2) ** 2
                for j in range(1, q))
    return float(vr), float(z), float((vr - 1) / math.sqrt(theta / T))
```

**Pitfalls.** The homoskedastic `z` over-rejects on volatility-clustered data: on a GARCH-type random walk
(1,000 steps, `q = 10`, 500 seeds) it rejected 18.6% of the time at 5%, `z*` 6.2%. Power is low for slow
reversion at short `q`: for an OU spread with half-life 10 and `T = 1,000`, `z*` rejected at 5% in 42%
of seeds at `q = 5`, 71% at `q = 10`, 90% at `q = 20`. Use `q` well below `T/2`.

**Acceptance checks.** Gaussian random walk, `T = 1,000`, `q = 5`, 500 seeds: mean VR 1.000, rejection
rate 3.4% (`z`) and 3.6% (`z*`). Fixture `p = ln[100, 101, 100, 102, 101, 103, 102, 104, 103, 105]`,
`q = 2` → VR 0.0464, `z` −2.861, `z*` −2.900.

### 6.5 Ornstein-Uhlenbeck fit, half-life and trading bands

**Use when:** a spread passed 6.1 or 6.2 (or a single series passed 4.1 and 6.4) and the user wants its
mean, speed, volatility and entry/exit levels.

**Model.** `ds = θ(μ − s)dt + σ dW`. Its exact discretisation at step `Δt` (sessions) is the AR(1)
`s_t = a + φ s_{t−1} + e_t` with `φ = e^{−θΔt}`, `a = μ(1 − φ)`, `Var(e) = σ²(1 − φ²)/(2θ)`.

**Method.**

1. Fit the AR(1) by OLS on the training window. Refuse unless `0 < φ < 1`.
2. `θ = −ln φ / Δt` (per session); `μ = a / (1 − φ)` (equal to `−a/b` in 6.1 with `b = φ − 1`);
   stationary standard deviation `σ_eq = sd(e) / √(1 − φ²)`; diffusion `σ = σ_eq·√(2θ)`;
   half-life `HL = ln 2 / θ` (identical to 6.1 step 4). For calendar-year units divide `Δt` by 252.
3. Bands in units of `σ_eq`: `z_t = (s_t − μ)/σ_eq`; enter at `|z| ≥ z_in`, exit at `|z| ≤ z_out`, stop at
   `|z| ≥ z_stop` or after a time stop of a few half-lives. Each band set is a trial.
4. Edge per round trip per unit of spread ≈ `(z_in − z_out)·σ_eq` (log units ≈ fraction of gross notional);
   require it to exceed the safety margin × round-trip cost on all legs (5.5).
5. Sanity range: a half-life under one session is bid-ask bounce or a stale close; a half-life above about a
   quarter of the training window cannot be tested on that window.

```python
def fit_ou(spread, dt=1.0):
    s = np.asarray(spread, dtype=float)
    X = np.column_stack([np.ones(len(s) - 1), s[:-1]])
    (a, phi), *_ = np.linalg.lstsq(X, s[1:], rcond=None)
    if not 0 < phi < 1:
        return None
    sd_e = (s[1:] - X @ np.array([a, phi])).std(ddof=2)
    theta = -math.log(phi) / dt
    sigma_eq = sd_e / math.sqrt(1 - phi ** 2)
    return {"theta": theta, "mu": a / (1 - phi), "sigma_eq": sigma_eq,
            "sigma": sigma_eq * math.sqrt(2 * theta), "half_life": math.log(2) / theta}
```

**Pitfalls.** The fit returns `φ < 1` on a random walk too (a 1,000-step walk gave a "half-life" of 320
sessions), so test first (6.1/6.2/6.4) and fit second. `θ` is biased upward in short samples, so the
half-life is biased down: with 250 sessions and a true half-life of 10, estimates averaged 8.9 (median 8.5,
5th–95th percentile 4.8–14.9). Report an interval (block bootstrap, 3.8). `μ` and `σ_eq` move; recalibrate
only walk-forward.

**Acceptance checks.** Simulated OU with `θ = ln 2/10`, `μ = 0.5`, `σ_eq = 0.05`, 5,000 steps, seed 7:
`θ̂ = 0.0627`, `μ̂ = 0.495`, `σ̂_eq = 0.0521`, half-life 11.05, the same value `half_life` (6.1) returns on
that series. Over 100 seeds the half-life averaged 9.87 (5th–95th percentile 8.66–10.98).

---

## 7. Signal outcome tracking and forecast scoring

### 7.1 Forward-outcome ledger

**Use when:** a screener, alert bot or model emits signals and the user wants to know what happened after
each one.

**Record per signal** (append-only): signal ID, listing ID and `CODE.EXCHANGE`, signal session and time,
rule version / spec hash, tags (setup, regime), reference price (and basis), planned stop and target if any,
forecast probability if any, and the capture IDs of the inputs.

**Outcomes** at 1/3/5/10/20 sessions after the signal, computed from EOD once matured:
close-to-close return on `adjusted_close`, excess return over a declared benchmark, maximum favourable and
adverse excursion (from adjusted high/low: raw H/L × `adjusted_close/close` per day), whether stop or target
was hit first (ambiguous same-bar hits recorded as ambiguous), and the outcome label.

**Rules.** A signal is *pending* until its horizon has fully elapsed and the final EOD bar is in; do not mix
pending and matured records in statistics. Report cohort statistics (by rule, tag and month) with sample
sizes and Wilson intervals for hit rates. Use the bulk endpoint for daily maturation of many signals
(100 calls per exchange-day). Results change rules only through the trial ledger (section 3.1).

**Acceptance checks.** A signal issued today has no matured outcome. Re-running maturation is idempotent.
A delisted symbol's signal keeps its record with an "unresolved" outcome instead of disappearing.

### 7.2 Brier score, log loss and calibration

**Use when:** a model or analyst outputs probabilities ("60% chance the stock beats the index over 20
sessions") and the user wants them scored.

| Measure | Formula (`p_j` forecast, `o_j ∈ {0,1}` outcome, `n` forecasts) |
|---|---|
| Brier score | `BS = (1/n) Σ (p_j − o_j)²` (0 best; 0.25 for always 0.5) |
| Brier skill score | `BSS = 1 − BS / BS_ref`, `BS_ref = ō(1 − ō)` for the base rate `ō` |
| Murphy decomposition | `BS = REL − RES + UNC` over probability bins `k`: `REL = Σ n_k(p̄_k − ō_k)²/n`, `RES = Σ n_k(ō_k − ō)²/n`, `UNC = ō(1 − ō)` (exact when forecasts within a bin are equal) |
| Log loss | `−(1/n) Σ [o_j ln p_j + (1 − o_j) ln(1 − p_j)]`, with `p` clipped to `[10⁻⁶, 1 − 10⁻⁶]` |
| Expected calibration error | `ECE = Σ_k (n_k/n) · |p̄_k − ō_k|` over equal-width bins |
| Reliability table | per bin: count, mean forecast, observed frequency, Wilson interval |

```python
def brier(p, o):
    return float(np.mean((np.asarray(p, float) - np.asarray(o, float)) ** 2))

def log_loss(p, o, eps=1e-6):
    p, o = np.clip(np.asarray(p, float), eps, 1 - eps), np.asarray(o, float)
    return float(-np.mean(o * np.log(p) + (1 - o) * np.log(1 - p)))

def ece(p, o, bins=10):
    p, o = np.asarray(p, float), np.asarray(o, float)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum((idx == b).mean() * abs(p[idx == b].mean() - o[idx == b].mean())
                     for b in range(bins) if (idx == b).any()))
```

**Pitfalls.** Score only forecasts whose outcome was resolved **after** the forecast timestamp. Overlapping
forecast horizons are dependent; use block bootstrap (3.8) for score intervals. A ranking score is not a
probability: calibrate it (isotonic or logistic fit on past resolved data, walk-forward) before emitting
probabilities; otherwise call it a relative score.

**Acceptance checks.** Constant forecast 0.3 on outcomes with base rate 0.3 → Brier ≈ 0.21, BSS ≈ 0,
ECE ≈ 0, log loss ≈ 0.611. Perfect forecasts → Brier 0, log loss ≈ 0.

### 7.3 Combining several probability forecasts

**Method.**

- **Linear pool:** `p̄ = Σ w_i p_i`. Robust, but under-confident when the forecasters hold different
  information.
- **Logit pool:** `logit(p̄) = a · Σ w_i logit(p_i)` with `logit(p) = ln(p/(1 − p))`, `Σ w_i = 1`. `a = 1`
  is the geometric-odds average; `a > 1` (extremising) is justified only if fitted on past resolved
  questions.
- Weights from past performance on resolved questions (for example inversely proportional to recent log
  loss), never from the period being scored.
- Always report the ablation: the combined forecast vs the simple mean vs the best single forecaster, on the
  same resolved set.
- When the forecasters are agents or models, run the diversity check and keep the run-state contract of 7.5
  before pooling.

```python
def logit_pool(probs, weights=None, extremize=1.0, eps=1e-6):
    p = np.clip(np.asarray(probs, float), eps, 1 - eps)
    w = np.full(len(p), 1 / len(p)) if weights is None else np.asarray(weights, float) / np.sum(weights)
    z = extremize * np.sum(w * np.log(p / (1 - p)))
    return float(1 / (1 + math.exp(-z)))
```

**Acceptance checks.** `logit_pool([0.7, 0.8]) ≈ 0.7534` (linear pool 0.75); with `extremize = 1.5`,
≈ 0.842; pooling `[0.5, 0.5]` returns 0.5 for any `a`.

### 7.4 Aggregating signals from several detectors

> A practitioner variant with detector-specific scales is in [methods-technical-market §21.1](methods-technical-market.md#211-multi-detector-signal-aggregation); keep one implementation per application.

**Use when:** several screens or detectors (setups in [technical-market §9](methods-technical-market.md),
earnings reactions, factor screens, news flags) each emit candidate tickers, and the user wants one ranked
conviction list with duplicates removed and conflicts visible.

**EODHD inputs.** None beyond what each detector used. Each detector row must carry its own provenance: run
ID, capture IDs and the as-of date of its input data.

**Method.**

1. **Common scale.** Each detector reports, per hit, its rank in the universe it scored on that date and
   the size of that universe: `u = 1 − (rank − 1)/universe_n`, in (0, 1], 1 = strongest. Raw scores of
   different detectors are never added. A detector that emits hits without a scored universe gets `u = 1`
   for every hit and is flagged "unranked".
2. **Window.** Keep signals whose as-of date falls inside the declared window (for example the last 5
   sessions). List excluded stale signals separately.
3. **Dedupe.** Each detector declares a theme (momentum, earnings, trend, value, …). Keep one vote per
   (ticker, theme, direction): the highest `u`, then the fresher as-of. The other detectors behind the same
   vote are listed under "also". Two momentum screens that agree are one piece of evidence.
4. **Conviction** = `Σ w_d · direction · u / W_max`, where `w_d` are declared detector weights and
   `W_max` = sum over themes of the largest weight in each theme (the best case: every theme fires at
   `u = 1`). Range −1…+1. Agreement across themes ranks above one strong detector.
5. **Conflict flag.** A bullish and a bearish vote, each with `u ≥ 0.5`, on the same ticker. Keep the net
   conviction but show the flag; a flagged name is never presented as a clean buy or sell candidate.
6. **Deterministic order:** conviction (descending), coverage = smallest `universe_n` behind the votes
   (descending), freshest as-of (descending), ticker (ascending).
7. Weights and the window are trials if the list feeds a strategy; the conviction is then a factor (2.x).

```python
def aggregate_signals(sig: pd.DataFrame, weights: dict, conflict_min=0.5) -> pd.DataFrame:
    """sig columns: detector, ticker, theme, direction (+1/-1), rank (1 = strongest), universe_n,
    as_of (Timestamp), provenance. All rows already lie inside the evaluation window."""
    s = sig.copy()
    s["u"] = 1 - (s["rank"] - 1) / s["universe_n"]
    s["w"] = s["detector"].map(weights).fillna(0.0)          # undeclared detector -> weight 0
    w_max = s.groupby("theme")["w"].max().sum()
    s = s.sort_values(["ticker", "theme", "direction", "u", "as_of"],
                      ascending=[True, True, True, False, False])
    s["also"] = s.groupby(["ticker", "theme", "direction"])["detector"].transform(",".join)
    s = s.drop_duplicates(["ticker", "theme", "direction"])
    rows = []
    for t, g in s.groupby("ticker"):
        strong = g[g.u >= conflict_min]
        rows.append({
            "ticker": t,
            "conviction": round(float((g.w * g.direction * g.u).sum() / w_max), 4),
            "conflict": bool((strong.direction > 0).any() and (strong.direction < 0).any()),
            "coverage": int(g.universe_n.min()),
            "freshest": g.as_of.max(),
            "sources": "; ".join(f"{r.detector}[{r.also}]:{r.provenance}@{r.as_of:%Y-%m-%d}"
                                 for r in g.itertuples()),
        })
    return (pd.DataFrame(rows)
            .sort_values(["conviction", "coverage", "freshest", "ticker"], ascending=[False, False, False, True])
            .reset_index(drop=True))
```

**Pitfalls.** Percentiles computed inside a detector's hit list (instead of its scored universe) turn the
weakest hit of a short list into a zero. Detectors built on the same input (two moving-average screens) are
not independent; give them one theme. A list that mixes as-of dates without showing them hides staleness.

**Acceptance checks.** Weights `mom_a` 1.0, `mom_b` 1.0 (theme momentum), `earn` 1.5 (earnings), `brk` 1.0
(trend, bearish), so `W_max` = 3.5. Rows (detector, ticker, direction, rank/universe): `mom_a` AAA +1 1/500;
`mom_b` AAA +1 4/400; `earn` AAA +1 10/300; `mom_a` BBB +1 26/500; `brk` BBB −1 5/450; `mom_a` CCC +1 51/500;
`earn` DDD +1 1/300; `mom_a` EEE +1 1/500; `mom_b` FFF +1 1/400. Output order and conviction: AAA 0.7014
(momentum vote kept from `mom_a`, `mom_b` listed under "also"), DDD 0.4286, EEE 0.2857, FFF 0.2857 (tie
broken by coverage 500 > 400), CCC 0.2571, BBB −0.0117 with the conflict flag.

### 7.5 Pooling several agents or models: run-state contract and diversity check

> The application-side version of the run-state contract and diversity check is in [app-ai-patterns §13](app-ai-patterns.md); this section is the statistical reference.

**Use when:** several LLM agents, analysts or models each produce a probability for the same question and
the user wants one pooled forecast (7.3). This section is the contract and the pre-pooling check; the
pooling formula and scoring stay in 7.2 and 7.3.

**Run-state contract.** Serialise the state after every tool call, as JSON, append-only:

| Field | Content |
|---|---|
| `run_id`, `role`, `model_version`, `prompt_hash` | which forecaster, with which method and instructions |
| `task` | question, resolution rule, horizon, resolution date |
| `evidence[]` | `capture_id`, endpoint, parameter hash, `observed_at` (data date), `retrieved_at`, one-line summary |
| `decisions[]` | step, choice, reason, evidence IDs used |
| `forecast` | `p`, `issued_at`, data cut-off |
| `open_questions[]`, `gates` | unresolved items; gate ID → pass / fail / pending with evidence |

Rules:

- **Replay.** A run is re-executed from its captured tool outputs (capture IDs) with no live calls and
  must reproduce the same evidence set and forecast.
- **Admissibility.** A forecast whose evidence contains anything observed after `issued_at` is invalid
  and is not scored.
- **Memory.** Long-term memory keeps methods and user preferences, never undated market facts; market facts
  live only in `evidence[]` with `observed_at` (see [AI and MCP](ai-mcp.md)).

**Diversity check (on past resolved questions only).**

1. Pairwise correlation `ρ_ij` of the forecasters' logits on the same resolved questions; mean `ρ̄`;
   effective number of forecasters `N_eff = N / (1 + (N − 1)·ρ̄)` (as in 3.10).
2. Evidence overlap: Jaccard index `J_ij` of the capture-ID sets.
3. Role distinctness: different declared roles or methods (a judgement; record it).
4. Rule: merge any pair with `ρ_ij > 0.9` or `J_ij > 0.8` into one forecaster (average in logit space)
   before pooling. Extremise (`a > 1` in 7.3) only when `N_eff ≥ 2` after merging and `a` was fitted on
   resolved questions; otherwise use `a = 1`.
5. Report the 7.3 ablation (pooled vs simple mean vs best single) scored by 7.2.

```python
import itertools

def diversity_report(P, evidence, rho_max=0.9, jac_max=0.8, eps=1e-6):
    """P: forecasters x resolved questions (probabilities). evidence: list of capture-ID sets."""
    p = np.clip(np.asarray(P, dtype=float), eps, 1 - eps)
    R = np.corrcoef(np.log(p / (1 - p)))
    pairs, merge = [], []
    for i, j in itertools.combinations(range(len(p)), 2):
        jac = len(evidence[i] & evidence[j]) / max(1, len(evidence[i] | evidence[j]))
        pairs.append((i, j, round(float(R[i, j]), 3), round(jac, 3)))
        if R[i, j] > rho_max or jac > jac_max:
            merge.append((i, j))
    rho_bar = float(np.mean([q[2] for q in pairs]))
    n_eff = len(p) / (1 + (len(p) - 1) * max(rho_bar, 0.0))
    return {"pairs": pairs, "rho_bar": round(rho_bar, 3), "n_eff": round(n_eff, 2), "merge": merge}
```

**Pitfalls.** Several prompts to the same model with the same evidence are one forecaster, however
different the personas sound. Correlation measured on unresolved questions, or on the period being scored,
leaks. Extremising correlated forecasters makes the pool over-confident.

**Acceptance checks.** Sixty resolved questions (seed 0, latent truth `N(0, 1)`): forecasters A and B see
the truth plus independent noise (sd 0.6 in logits) and use evidence {c1, c2, c3} and {c4, c5, c6}; C copies A
plus noise of sd 0.1 with A's evidence. Result: `ρ(A,B)` = 0.666, `ρ(A,C)` = 0.994 with `J(A,C)` = 1.0 →
merge (A, C); `ρ̄` = 0.778, `N_eff` = 1.17, so no extremising.

---

## 8. Causal identification basics for event and market studies

**Use when:** the user asks whether an event (earnings, dividend change, index inclusion, insider purchase,
macro release, news) *caused* a price move, not only whether it predicts one.

**State the claim first.** A predictive signal can be useful without a causal claim. Say which one the
study makes: "returns after X differ from comparable non-X cases" (association) or "X moved prices"
(causal, needs identification).

**EODHD inputs.** Events: `/api/calendar/earnings` (`report_date`, `before_after_market`), `/api/div`,
`/api/splits`, insider data (`/api/insider-transactions` flat feed or SEC Form 4 via `/api/sec-filings/{symbol}/form4`; the two do not always overlap), `/api/economic-events` (`actual` = first release, UTC times),
`/api/news` (`date`, `symbols`, `tags`); prices from EOD; index membership from `GSPC.INDX`
`HistoricalTickerComponents`. Event timing rules are in [temporal research](temporal-research.md) and the
abnormal-return mechanics in [backtesting](backtesting.md#event-studies).

**Method.**

1. **Draw the DAG.** Write the treatment (event), outcome (abnormal return over a window), and every variable
   that could affect both. Control for confounders (common causes, determined before the event: size,
   prior momentum, sector, market move). Do **not** control for mediators (the earnings surprise itself when
   the treatment is the announcement), colliders (selection into the sample by an outcome-related filter
   such as "stocks still listed today"), or anything measured after the event.
2. **Timing discipline.** Controls must be known before the event session. Current-vintage fundamentals
   restated after the event can embed post-treatment information; use values filed before the event plus
   a lag, and label the residual risk.
3. **Comparison group.** Matched non-event listings (same sector, size and pre-period return bucket) on the
   same dates, so common shocks cancel.
4. **Confounding events.** Same-day earnings, dividends, splits, index changes and company news (scan
   `/api/news` for the symbol and window) are flagged; run the analysis with and without contaminated
   events.
5. **Placebo tests.**
   - Pseudo-events: random non-event sessions for the same listings; the effect should vanish.
   - Placebo outcomes: windows **before** the event (pre-trends) should show no effect beyond known
     run-ups.
   - Placebo units: matched controls assigned the treatment date.
6. **Difference-in-differences** (for policy or rule changes affecting a group):
   `ATT = (Ȳ_treated,post − Ȳ_treated,pre) − (Ȳ_control,post − Ȳ_control,pre)`. Requires parallel pre-trends
   (test lead coefficients). With staggered adoption, a two-way fixed-effects regression can be biased;
   compare each adoption cohort with not-yet-treated or never-treated units instead.
7. **Uncertainty.** Cluster by date (events on the same day share market shocks) and by issuer; calendar-
   time portfolios are an alternative when events cluster.
8. **Sensitivity.** Report how large an unobserved confounder would need to be to remove the effect (for
   example re-estimate after adding progressively stronger proxies) and refutation checks: random common
   cause added, data subsets, alternative windows.

**Pitfalls.** A post-event drift is not proof of causation. Survivorship in the event sample (only firms
still listed) is a collider. Events identified from today's data (current index members, current sector)
select on the outcome.

**Acceptance checks.** On synthetic data with a planted effect only on event dates, pseudo-event placebos
show no effect and the estimated effect is recovered. Adding a mediator as a control visibly shrinks a
planted total effect, demonstrating why it is excluded.

---

## 9. Model drift monitoring

**Use when:** a deployed screener, model or signal needs alerts when its inputs, labels or calibration
change. Retraining remains a versioned, evaluated change (see [ML and factors](ml-factors.md)).

| Drift type | Measure | Definition |
|---|---|---|
| Feature (data) drift | PSI | Bin edges from reference-period quantiles (10 bins); `PSI = Σ_b (a_b − e_b)·ln(a_b/e_b)` with `e_b`, `a_b` the reference and current shares, floored at 10⁻⁴ |
| Feature drift (continuous) | KS statistic | `D = sup_x |F_ref(x) − F_cur(x)|`; compare with its critical value for the two sample sizes |
| Missingness drift | null share | per feature, current vs reference; schema changes listed separately |
| Label drift | base rate / return distribution | share of positive labels, mean and dispersion of forward returns |
| Concept drift | rolling IC | 63-session mean IC with NW interval vs the validation IC |
| Calibration drift | rolling Brier, ECE | vs validation values on resolved forecasts only |

Conventional PSI bands (heuristics, not statistical tests): < 0.1 stable, 0.1–0.2 moderate, > 0.2 major.

```python
def psi(expected, actual, bins=10, eps=1e-4):
    e, a = np.asarray(expected, float), np.asarray(actual, float)
    edges = np.unique(np.quantile(e, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    ef = np.clip(np.histogram(e, edges)[0] / len(e), eps, None)
    af = np.clip(np.histogram(a, edges)[0] / len(a), eps, None)
    return float(np.sum((af - ef) * np.log(af / ef)))
```

**EODHD-specific triggers that look like drift but are data events:** `adjusted_close` restated after a new
dividend or split (re-download and hash, see [quality](quality.md)); unit change (GBX ↔ GBP lines);
symbol renames and `_old` reuse; universe shrinkage from delistings; fundamentals schema or field changes;
holiday fallback in bulk files. Separate "vendor revision" from "world changed" before acting.

**Acceptance checks.** Identical distributions → PSI < 0.01. Standard normal reference vs a 0.5σ mean shift
→ PSI ≈ 0.24; 1σ shift → ≈ 0.92; variance × 1.5 (standard deviation × 1.5) → ≈ 0.19 (10 decile bins,
large samples). A monitor triggered by a restatement event is labelled as a data event, not model drift.

### 9.1 Retraining and promotion policy

**Use when:** a monitor in the table above fires, or a scheduled refit date arrives, and the user asks
whether to retrain or replace the deployed model.

**Method.**

1. **Two paths.** Scheduled refits follow the declared walk-forward calendar (the same refit cadence the
   backtest used, for example quarterly). Monitors open a **review**, never an automatic retrain. Review
   triggers (declared defaults): PSI > 0.2 on a top-importance feature on two consecutive checks; 63-session
   rolling IC below the lower edge of the validation IC interval; ECE above its validation value plus a
   declared margin on resolved forecasts; a CUSUM alarm (4.5) on live or paper P&L.
2. **Triage first.** Classify the trigger as a data event (restatement, unit change, symbol reuse, universe
   shrinkage, schema change, bulk holiday fallback; the list above) or a change in the world. A data event
   is fixed in the data and the model re-scored; it does not lead to a retrain.
3. **Challenger.** Same spec version with a new training cut-off `c` is a refit. Any change of features,
   label, model class or hyperparameters is a new spec version and a new trial (3.1). Train on data up to
   `c` only.
4. **Evaluation window.** The most recent sessions after `c` that neither champion nor challenger used for
   fitting or tuning, purged and embargoed by the label horizon (3.5), at least a declared minimum (for
   example 63 sessions). Score both models on that window with the same metrics.
5. **Promotion rule.** The challenger replaces the champion only if (a) it is not worse on the primary
   metric beyond a declared tolerance (block-bootstrap interval of the difference, 3.8), (b) its calibration
   is not worse, (c) it re-passes gates G0–G5 (3.12), and (d) a shadow period (scores computed and logged,
   not used) shows no new failure.
6. **Record and rollback.** Log the decision with both config hashes, the evaluation window, the metrics
   and the approver in the model registry ([ML and factors](ml-factors.md)). Rollback re-points to the
   previous model ID; predictions must reproduce bit-for-bit from the stored artefact.
7. **Limits.** At most one promotion per declared cool-down period. Every retrain counts in the trial ledger.
   Promotion changes research and paper outputs only; it never changes live trading without a human
   decision (see [paper accounting](paper-accounting.md)).

**Acceptance checks.** A challenger whose training data overlaps the evaluation window is rejected. An
alert classified as a data event produces a data fix and no retrain record. Each promotion record holds two
config hashes and an evaluation window that starts after both training cut-offs. A rollback reproduces the
previous model's stored prediction hash.

---

## 10. Strategy specification template

Fill this before writing strategy code; the code implements exactly the spec, and every change bumps the
version and counts as a new trial. The completed spec travels with the backtest output.

```markdown
# Strategy specification

- Spec ID / version / date:
- Author and audience (private research | shared — check licensing.md):
- Archetype: trend | mean reversion | cross-sectional factor | pairs | event-driven | carry proxy | other:
- Hypothesis (one sentence, economic rationale):

## Data
- Universe rule (exchange(s), type, liquidity floor, membership source, delisted handling):
- EODHD endpoints and plan (with call budget):
- Price basis: signals on adjusted_close | raw; fills and cash on raw OHLC × adjustment policy:
- Currency and unit normalisation (GBX/ZAC, FX source and timing):
- Information-set mode: current-vintage retrospective | forward archived | strict (temporal-research.md):
- Fundamental activation lag (if used):

## Signal
- Formula with symbols, units, lookbacks:
- Parameters and their declared grid (every cell is a trial):
- Signal time (e.g. after close D) and fill time (e.g. open D+1); same-bar ambiguity rule:

## Positions
- Entry rule:
- Exit rule(s) (signal, target, time stop):
- Stop rule and gap treatment:
- Sizing rule (volatility target, risk budget, equal weight):
- Constraints (max weight, sector cap, gross/net, participation cap % ADV):
- Rebalance frequency and calendar:

## Risk controls (at least one hard control)
- Hard control (e.g. max drawdown halt, max position, freshness gate) and what it does on trigger
  (stop new orders; never silent liquidation):

## Costs
- Commission, half-spread source (5.3 estimate or quotes), slippage, impact coefficient Y:
- Borrow for shorts (user-supplied rate) and FX conversion cost:
- Cost ladder to report: 0 / 5 / 10 / 25 / 50 bps one-way:

## Validation plan
- Train / validation / final holdout dates (holdout untouched until final run):
- Purge and embargo:
- variants_tried (running count, feeds DSR/PBO/BH):
- Gates and thresholds used for PASS / WARN / FAIL:
- Benchmarks (buy-and-hold, equal weight, cash):

## Claims policy
- Forbidden wording: "guaranteed", "risk-free", "cannot lose", "proven edge".
- Rejected designs: all-in sizing, martingale/averaging down without limit, leverage without a
  financing and margin model, live order placement from this research.
- Strongest permitted claim: "survived validation on the disclosed information set".

## Pipeline
spec → code exactly from spec → validation verdict (methods-quant-research.md 3.11) →
risk profile (portfolio-risk.md) → paper only (paper-accounting.md)
```
