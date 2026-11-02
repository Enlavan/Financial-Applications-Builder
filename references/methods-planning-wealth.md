# Methods: retirement planning, wealth operations, household finance, tax lots and trade-journal audit

Formulas, ordered steps, EODHD inputs and acceptance checks for household and advisory computations
that combine EODHD market history with **user-supplied** records. Covered: return-panel construction for
planning (total-return proxies, inflation, bonds, cash), retirement/FIRE simulation (balance recursion,
contributions, withdrawal rules including guardrails and variable-percentage withdrawal, historical
rolling paths, block-bootstrap Monte Carlo, outcome metrics, sequence-of-returns analysis), goals-based
planning and glide paths, capital-market assumptions, an investment policy statement (IPS) template,
investment-proposal assembly (weighted expense ratio, proxy statistics, fee drag, transition cost),
tax-lot accounting and dividend holding-period windows, repurchase-window (wash-sale-type) checks,
tax-loss-harvesting screens, AUM fee billing and performance fees, client-reporting maths (goal progress,
model/UMA sleeves, held-away assets, review packs), trade-statement/journal audit, household finance
modules (time value of money, intake, dashboard, net worth, budget, debt, lending, emergency fund,
rent-vs-buy and other two-scenario comparisons, rental property, concentrated stock, liquidity tiers,
after-tax growth) and private-fund metrics with public-market equivalents. EODHD supplies prices,
dividends, splits, FX, index levels, fund metadata, Treasury and reference rates, residential property
indices and annual macro series. Holdings, transactions, fills, cash flows, tax rules, fee schedules,
contract and loan terms, incomes, expenses, ages and goals are user inputs; nothing here invents them.
These are analytical methods, not advice, tax filings or certified performance records.

Read first when relevant: [data semantics](data-semantics.md) (price bases),
[coverage notes](coverage-notes.md), [plans and limits](plans-limits.md). Narrative context lives in
[personal planning](personal-planning.md), [paper trading and accounting](paper-accounting.md),
[portfolio and risk](portfolio-risk.md), [funds and income](funds-income.md),
[corporate actions](corporate-actions.md) and [professional workflows](professional-workflows.md).

## Contents

1. Conventions used in this chapter
2. Planning return panel from EODHD
   - 2.1 Equity total return: the `GSPC.INDX` price-index trap
   - 2.2 Inflation from `macro-indicator`
   - 2.3 Bond and cash returns from Treasury yields
   - 2.4 Assembling and checking the panel
3. Retirement / FIRE simulation engine
   - 3.1 Balance recursion and timing
   - 3.2 Contributions and savings rate
   - 3.3 Withdrawal rules
   - 3.4 Path generators: deterministic, historical rolling, block bootstrap
   - 3.5 Outcome metrics
   - 3.6 Sequence-of-returns analysis
   - 3.7 FIRE numbers and goal-seek solvers
   - 3.8 Reference implementation and tests
4. Goals-based planning
   - 4.1 Glide path (time-varying target weights)
5. Capital-market assumptions (CMA) from EODHD proxies
6. Investment policy statement (IPS) and investment proposal
   - 6.1 IPS template
   - 6.2 Investment proposal assembly
7. Tax-lot accounting
   - 7.1 Dividend holding-period window (estimate)
8. Repurchase-window (wash-sale-type) checks across accounts
9. Tax-loss harvesting: screen, replacements, net benefit
10. AUM fee billing and performance fees
11. Client and household reporting maths
   - 11.1–11.4 Period returns, aggregation, valuation tie-out, benchmarks
   - 11.5 Goal-progress panel and narrative rules
   - 11.6 Model portfolios, UMA sleeves and held-away assets
   - 11.7 Client review pack template
12. Trade-statement audit and journal analytics
13. Household finance modules
   - 13.1 Time-value-of-money block
   - 13.2 Household intake schema
   - 13.3 Household dashboard metrics and composite score
   - 13.4 Net-worth statement
   - 13.5 Budget categorization and rule-of-thumb frameworks
   - 13.6 Debt payoff, refinance and prepay-vs-invest
   - 13.7 Lending: extra payments, points, 15 vs 30 years, ARM paths
   - 13.8 Emergency-fund sizing
   - 13.9 Two-scenario engine (rent vs buy and other life choices)
   - 13.10 Rental property cash flow: NOI, cap rate, DSCR, levered IRR
   - 13.11 Concentrated stock position
   - 13.12 Liquidity tiers and ladders
   - 13.13 After-tax growth and asset location
14. Private-fund metrics and public-market equivalents (PME)
15. Boundaries

---

## 1. Conventions used in this chapter

| Symbol | Meaning | Unit |
|---|---|---|
| `t` | period index, `t = 1..T` (years unless stated) | — |
| `B_t` | portfolio balance at end of period `t` (`B_0` = start) | currency |
| `r_t` | nominal portfolio return in period `t` | decimal (0.05 = 5%) |
| `i_t` | inflation in period `t` | decimal |
| `ρ_t` | real return `(1 + r_t)/(1 + i_t) − 1` | decimal |
| `W_t` | withdrawal (spending) in period `t` | currency |
| `C_t` | contribution in period `t` | currency |
| `CPI_t` | price index, `CPI_0 = 1`, `CPI_t = CPI_{t-1}(1 + i_t)` | ratio |

- All rates are decimals in code. EODHD returns several series in **percent** (`macro-indicator`
  `Value`, UST `rate`, ETF `Yield` as a string, `Assets_%`, `Net_Assets_%`, reference-rate `rate`, bill
  `coupon`): divide by 100 at ingestion and store the unit. `ETF_Data::NetExpenseRatio` is already a
  decimal (probe 2026-10-25: `VTI.US` → `0.0003`, i.e. 0.03%). `MutualFund_Data::Expense_Ratio` is
  documented as a decimal, but `SWPPX.US` returned `0.0201` on the same date, which matches that fund's
  published ratio of about 0.02% only if you read it as a percent. Check the unit per fund against a known
  prospectus figure before you weight it (6.2).
- Python blocks in this chapter use the stdlib, numpy and pandas only. They were run on synthetic data, and
  the acceptance numbers come from those runs.
- Real values are "money of the start date": `real = nominal / CPI`. Never mix a real spending target with
  nominal returns (or the reverse). Simplest safe design: simulate in **nominal** terms with an explicit
  inflation path, convert to real for reporting.
- `1 + ρ = (1 + r)/(1 + i)`; the approximation `ρ ≈ r − i` is not acceptable in compounding code.
- Annualize a multi-year cumulative return `R` over `Y` years as `(1 + R)^(1/Y) − 1`. Do not annualize
  periods shorter than one year in reports.
- Sample statistics use `n − 1`. A monthly volatility annualizes with `√12`, daily with `√252` (equity
  sessions), only for i.i.d.-style approximations; state it.

---

## 2. Planning return panel from EODHD

**Use when:** any long-horizon simulation, CMA or proposal needs annual (or monthly) asset-class returns and
inflation.

### 2.1 Equity total return: the `GSPC.INDX` price-index trap

**EODHD inputs** (EOD endpoint, 1 call per symbol for full history; EOD All World or All-In-One; Free is
clipped to one year):

| Series | Basis | History (verify first date with a probe) | Use |
|---|---|---|---|
| `GSPC.INDX` | **price index** — no dividends; `adjusted_close == close` | from 1927-12-30 | long history, must add a dividend assumption |
| `SPXTR.INDX` | S&P 500 total return (gross) | from about 1988 | preferred TR source where history suffices |
| `SP500TR.INDX` / `SP500NTR.INDX` | S&P 500 gross / net-of-withholding TR | from about 2000 | net TR for non-US-resident framing |
| `XNDX.INDX` | Nasdaq-100 TR | from about 2000 | |
| `DJITR.INDX` | Dow Jones TR | from about 2000 | |
| ETF `adjusted_close` (e.g. `SPY.US`, `VTI.US`) | split+dividend adjusted, **net of fund costs** | fund inception (probe) | investable proxy; includes expense ratio drag |

INDX codes ending in `TR`/`T` are total-return indices; all others are price indices
(`api/general/indices-data-notes.md`). List candidates with `exchange-symbol-list/INDX` (1 call) and
filter codes ending in `TR`, then check each symbol's **last** date too — discontinued rows exist (no FTSE,
no current Russell; see coverage notes).

**Method — choose in this order:**

1. TR index over its available span (gross of fees: subtract a user fee assumption if the plan models an
   investable portfolio).
2. ETF `adjusted_close` over its span (already net of the fund's expenses; do not subtract the expense
   ratio again; do not add dividends again).
3. Before the TR span: splice `GSPC.INDX` price return plus a dividend-yield series:

   `r_TR,y ≈ r_price,y + d_y`, with `r_price,y = P_y / P_{y−1} − 1` from year-end closes and `d_y` the
   trailing dividend yield for year `y` (decimal). `d_y` is **user-supplied** or a documented, labelled
   constant assumption; EODHD has no historical index dividend-yield series. The additive form ignores
   intra-year reinvestment (error ≈ `d_y · r_price,y / 2`); state it.
4. Splice **returns, never levels**: use the proxy's returns up to the year before the TR series starts,
   then the TR series' returns. Record the splice year and the source of each year in the panel.
5. In overlapping years, compute the implied yield `r_TR,y − r_price,y` and compare it with the user's `d_y`;
   report mean and max absolute difference as a calibration check.

Non-US investors: convert local-currency returns to the home currency with `*.FOREX` year-end closes,
`(1 + r_local)(1 + r_fx) − 1` with correctly oriented FX (see data-semantics), and use **home** CPI.

**Pitfalls**
- Using `GSPC.INDX` alone understates US equity growth by roughly the dividend yield every year — over
  30 years this changes a simulation's success rate materially. Name the basis in every output.
- Using `adjusted_close` of an ETF **and** a dividend stream double-counts income.
- `adjusted_close` is restated whenever a new action is added; cache raw captures with retrieval date.
- Annual returns from `period=m` rows: take the last row of each calendar year; a year with missing December
  data is incomplete, not a zero return.

### 2.2 Inflation from `macro-indicator`

**EODHD inputs:** `GET /api/macro-indicator/{ISO3}?indicator=inflation_consumer_prices_annual&fmt=json`
(Fundamentals Data Feed or All-In-One; 10 calls per request per [plans and limits](plans-limits.md); one
request returns the full annual history). Response rows: `CountryCode`, `CountryName`, `Indicator`,
`Date` (`YYYY-12-31`), `Period`, `Value` (percent).

Observed on 2026-10-25 (probe, USA): annual values from 1960 through 2024; **the latest one to two years can
be missing**. The series is annual-average CPI change (World Bank style), not December-to-December.

**Method**
1. `i_y = Value / 100`, keyed by `int(Date[:4])`.
2. Missing recent years: take user-supplied values (or an explicit planning assumption) and flag them.
3. Projection years: user assumption (constant or path) or bootstrap jointly with returns (3.4).
4. Monthly simulations: either user-supplied monthly CPI or `(1 + i_y)^(1/12) − 1` labelled
   "interpolated from annual".

**Pitfalls:** an invalid indicator code returns plain text, not JSON (see the endpoint page); annual-average
inflation paired with year-end market returns has a half-year timing mismatch — acceptable for planning,
state it. Non-US paths need that country's code (`DEU`, `GBR`, …); euro-area aggregates may not exist under
`macro-indicator` — verify with a probe.

### 2.3 Bond and cash returns from Treasury yields

**EODHD inputs:** `/api/ust/yield-rates?filter[year]=YYYY` (daily par curve; tenors observed 1990: 3M, 6M,
1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 30Y; later years add more), `/api/ust/bill-rates?filter[year]=YYYY`; 1 call per
request per the endpoint pages, available on Free, EOD All World, Extended and All-In-One (beta). The par
curve was probed back to 1990; probe earlier years before promising them. `.GBOND` yields (e.g.
`US10Y.GBOND`, Fundamentals Feed / All-In-One) are an alternative; verify depth per symbol. Bond ETF
`adjusted_close` gives an investable proxy for its span.

**Method — constant-maturity par bond, annual step:** buy a par bond with coupon `y_0` (the year-start
yield, decimal, semiannual coupons), revalue one year later at yield `y_1` with maturity `M − 1`:

```
P_1 = (y_0/2) · [1 − (1 + y_1/2)^(−2(M−1))] / (y_1/2) + (1 + y_1/2)^(−2(M−1))
r_bond = P_1 − 1 + y_0          # price change + one year of coupons per unit face
```

Sanity: `y_1 = y_0` gives `r_bond = y_0`. With `y_0 = 4%`, `y_1 = 5%`, `M = 10`: `r_bond ≈ −3.18%`.
Cash: compound the 3M rate sampled quarterly, `Π(1 + y_q/4) − 1`, labelled "T-bill proxy, no fees".

**Pitfalls:** this is a model of a rolling constant-maturity bond, not a fund; credit, TIPS and municipal
returns are not derivable from these curves. Yields are percent — divide by 100.

### 2.4 Assembling and checking the panel

Steps: (1) fetch and cache raw responses; (2) build `year → {equity, bond, cash, inflation, source flags}`;
(3) keep only years where every column is observed or explicitly assumed; (4) write the panel with a
manifest (symbols, splice years, assumptions, retrieval date).

**Acceptance checks**
- No year has a missing column silently filled with 0.
- Compounding the equity column over the TR span matches `last/first − 1` of the TR series within rounding.
- Overlap test: annual SPXTR return − SPY `adjusted_close` return averages near the fund's expense ratio
  (order of a few basis points; a gap of ~2% means a price series slipped in).
- `GSPC.INDX` column, if used without dividends, is labelled "price only".
- Real returns recomputed from the stored nominal and inflation columns reproduce the stored real column.

---

## 3. Retirement / FIRE simulation engine

**Use when:** "will my savings last", "would my plan have survived 1929 / 1966 / 2000", "what withdrawal is
sustainable", "when can I retire", guardrail spending.

**EODHD inputs:** the panel of section 2. **User inputs:** starting balance, allocation, horizon, spending
target (real), contribution schedule, fees, other income (pensions, benefits) and their indexation, taxes
on withdrawals (or a pre-tax spending convention), rule parameters. Ages and longevity are user inputs or
an explicitly labelled planning horizon.

### 3.1 Balance recursion and timing

State the timing; results differ.

```
start-of-period withdrawal:  B_t = (B_{t−1} + C_t − W_t) · (1 + r_t)
end-of-period withdrawal:    B_t =  B_{t−1} · (1 + r_t) + C_t − W_t
```

Portfolio return for allocation `a` (rebalanced each period): `r_t = Σ_j a_j r_{j,t} − f` with `f` the
annual fee drag (or `(1 + Σ a_j r_{j,t})(1 − f) − 1`; state which). Depletion: when `W_t` exceeds the
available balance, pay what is available, record the unmet real amount as shortfall, set `B = 0` and keep
stepping (do not let the balance go negative unless modelling borrowing).

Closed forms for zero-volatility tests (constant real return `ρ`, constant real `W`, start-of-period):
- Perpetual withdrawal keeping `B` constant: `W* = B_0 · ρ/(1 + ρ)`.
- Years until depletion: `n = −ln(1 − B_0 ρ / (W(1 + ρ))) / ln(1 + ρ)` (undefined, i.e. never depletes, when
  `W ≤ W*`). `B_0 = 1,000,000`, `ρ = 4%`, `W = 50,000` → `n ≈ 37.39`, so year 38 is the first unfunded year.

### 3.2 Contributions and savings rate

- Contribution path: `C_t = C_1 · Π(1 + g_k)` (real growth `g` user-supplied), stopping at the retirement
  year. Employer match and caps are user inputs.
- Savings rate (state the definition, they differ by 10+ points): `s = (C_employee + C_employer) / gross
  income` or `/ net income`. Report which.
- Accumulation then decumulation in one path: contributions until retirement index `R`, withdrawals after.

### 3.3 Withdrawal rules

All parameters are user inputs; the values below are common research defaults, not recommendations.

| Rule | Formula (nominal unless stated) | Notes |
|---|---|---|
| Constant real | `W_t = W_1 · CPI_{t−1}` | classic "x% of initial balance, inflation-adjusted" |
| Constant percentage | `W_t = p · B_{t−1}` (start-of-period) | never depletes; income volatile |
| Variable percentage (VPW) | `W_t = B_{t−1} · q_t`, `q_t = g / ((1 + g)(1 − (1 + g)^(−n_t)))` (start-of-period annuity factor), `n_t` = remaining years incl. `t`, `g` = assumed real return; `g = 0` → `q_t = 1/n_t` | exhausts exactly at horizon if returns equal `g`; spending tracks markets |
| Floor and ceiling | `W_t = clamp(p · B_{t−1}, F · CPI_{t−1}, K · CPI_{t−1})` | floor can deplete; report floor breaches |
| Guardrails (Guyton–Klinger style) | see below | rule set; each switch configurable |

Guardrails, per year `t ≥ 2` (initial rate `WR_0 = W_1 / B_0`):
1. **Inflation rule:** `W_t = W_{t−1}(1 + i_{t−1})`, except skip the raise when the prior-year portfolio
   return was negative **and** the current rate `W_{t−1}/B_{t−1} > WR_0`.
2. **Capital-preservation rule:** if `W_t / B_{t−1} > WR_0 (1 + u)` (e.g. `u = 0.20`) and more than `H`
   years remain (e.g. 15), cut: `W_t ← W_t (1 − c)` (e.g. `c = 0.10`).
3. **Prosperity rule:** if `W_t / B_{t−1} < WR_0 (1 − l)` (e.g. `l = 0.20`), raise: `W_t ← W_t (1 + c)`.

Run guardrails in nominal terms with the inflation path, then deflate for reporting.
Success rate is not meaningful for constant-percentage/VPW rules (they never deplete); report spending
outcomes instead (3.5).

### 3.4 Path generators

Report the three side by side, never one alone.

**Deterministic.** Constant real return (e.g. CMA geometric mean) and inflation. Used for explanation and as
a code test (closed forms in 3.1).

**Historical rolling start years.** For a panel of `Y` complete years and horizon `N`, start years
`s = y_first … y_last − N + 1` give `Y − N + 1` paths, each using the actual joint sequence of returns and
inflation. Steps:
1. Build the panel (section 2); confirm all columns observed for every year used.
2. For each `s`, run the engine on years `s … s + N − 1`.
3. Report per-start-year outcomes (table and chart by start year), the count of paths, and the worst start
   years. Highlight known stress starts the panel covers (e.g. 1929, 1966, 1973, 2000) — only if the data
   for those years is real or explicitly spliced.
4. Paths overlap heavily (adjacent starts share `N − 1` years): **do not** put a binomial confidence interval
   on the historical success rate; state the number of paths and the number of distinct decades.
5. Horizons longer than the panel allow few or no full paths; circular wrapping (`(s + k) mod Y`) is an
   option only if labelled "wrapped".

**Block-bootstrap Monte Carlo.** Resample **rows** of the joint panel (all assets and inflation from the same
year) in contiguous blocks, to keep cross-correlation and some serial dependence (inflation is persistent).
1. Choose block length `L` (annual data: 3–10 years; monthly: 12–36 months) and number of paths
   (≥ 5,000; report Monte Carlo error).
2. Circular moving-block bootstrap: repeatedly draw a start `u ~ Uniform{0..Y−1}`, append rows
   `u, u+1, …, u+L−1 (mod Y)` until the horizon is filled; truncate.
3. Optionally centre the sampled real returns to a CMA mean (`ρ − mean(ρ) + μ_CMA`) and label it.
4. Run the engine on every path with a fixed seed recorded in the output.

Independent i.i.d. sampling (`L = 1`) understates the dispersion of long sequences; parametric normal
draws understate fat tails. Either may be offered as an alternative, labelled.

### 3.5 Outcome metrics

| Metric | Definition |
|---|---|
| Success rate | share of paths with no unmet spending through horizon (`depleted_year` is null) |
| Success-rate CI (Monte Carlo only) | Wilson interval on `k` successes out of `n` paths (12.3); expresses simulation error, not model error |
| Failure-year distribution | first unfunded year per failed path; report median and 10th percentile |
| Shortfall | sum of unmet real spending per path; report mean over failed paths and the worst path |
| Years funded | count of fully funded years (out of `N`) |
| Terminal real wealth | `B_N / CPI_N`; report median, 10th and 90th percentile across paths |
| Spending outcomes (variable rules) | min real `W_t`, years below the user's floor, real spending percentiles by year, year-on-year spending volatility |
| Worst path | path with lowest terminal wealth or earliest depletion; show its sequence |

Never derive ranges from heuristic multipliers of a deterministic projection ("× 1.5 / × 0.6"); ranges come
from simulated paths.

### 3.6 Sequence-of-returns analysis

1. **Order invariance check (no flows):** with `C = W = 0`, terminal wealth is `B_0 · Π(1 + r_t)`, identical
   for any ordering — a mandatory engine test.
2. **Reversal test:** same returns, reversed order, with withdrawals. Example: `B_0 = 1,000,000`, real
   returns `[−30%, +10% × 9]`, constant real `W = 60,000` start-of-year → terminal ≈ **655,284**; reversed
   order → ≈ **981,192**; with no withdrawals both give ≈ 1,650,563.
3. **Permutation spread:** for a historical window, shuffle the order `K` times (e.g. 1,000) holding the set
   of returns fixed; the spread of terminal wealth across permutations is the sequence effect for that
   return set.
4. **Early-return attribution:** across rolling or bootstrap paths, regress (or rank-correlate) outcome on
   the annualized real return of the first 5–10 years versus the last 10; early years typically dominate
   during decumulation.
5. Report the **retirement red zone**: outcome sensitivity to the first decade; levers are lower initial
   withdrawal, guardrails, cash buffer, or flexible retirement date.

### 3.7 FIRE numbers and goal-seek solvers

| Quantity | Formula |
|---|---|
| FI number | `FI = S / w` (annual real spending `S`, withdrawal rate `w`, a user parameter; `w = 4%` → 25× spending) |
| Lean / Fat / Barista FI | same formula with user-defined spending levels; Barista: `(S − part-time income) / w` |
| Coast FI (amount needed now) | `FI / (1 + ρ)^n` for `n` years to retirement; `FI = 1,000,000`, `ρ = 5%`, `n = 20` → ≈ 376,889 |
| Years to FI (end-of-year contributions `C`) | `n = ln((FI·ρ + C)/(B_0·ρ + C)) / ln(1 + ρ)`; `B_0 = 100,000`, `C = 30,000`, `ρ = 5%`, `FI = 1,000,000` → ≈ 16.94 (crossed during year 17) |
| Required contribution | `C = (G − B_0(1 + ρ)^n) · ρ / ((1 + ρ)^n − 1)` (end-of-year); `G = 500,000`, `B_0 = 50,000`, `ρ = 5%`, `n = 15` → ≈ 18,354 |

Stochastic goal-seek: bisection on the lever (contribution, retirement year, spending, allocation) until the
simulated success rate hits the user's target; report the solution with the Monte Carlo error at that point.
Present a **lever sensitivity table**: success rate and median terminal wealth for ±1 retirement year,
±10% spending, ±25% savings, two allocations.

### 3.8 Reference implementation and tests

```python
import numpy as np

def simulate(B0, nominal_r, infl, spend_real, rule="constant_real",
             contrib_real=None, timing="start", params=None):
    """Annual steps. nominal_r, infl: decimals per year. spend_real: year-1 spending in today's
    money (constant_real, guardrails). Returns real balances, real spending, depletion, shortfall."""
    p = params or {}
    T = len(nominal_r)
    cpi, B, W = 1.0, float(B0), float(spend_real)
    wr0 = spend_real / B0
    bal, spend, short, dep = [], [], 0.0, None
    for t in range(T):
        if contrib_real is not None:
            B += contrib_real[t] * cpi
        if rule == "constant_real":
            W = spend_real * cpi
        elif rule == "constant_pct":
            W = p["pct"] * max(B, 0.0)
        elif rule == "vpw":
            n, g = T - t, p["g"]
            q = 1 / n if g == 0 else g / ((1 + g) * (1 - (1 + g) ** -n))
            W = q * max(B, 0.0)
        elif rule == "guardrails" and t > 0:
            if not (p.get("inflation_rule", True) and nominal_r[t - 1] < 0 and B > 0 and W / B > wr0):
                W *= 1 + infl[t - 1]
            wr = W / B if B > 0 else float("inf")
            if wr > wr0 * (1 + p.get("upper", 0.20)) and T - t > p.get("no_cut_last", 15):
                W *= 1 - p.get("adj", 0.10)
            elif wr < wr0 * (1 - p.get("lower", 0.20)):
                W *= 1 + p.get("adj", 0.10)
        if timing == "start":
            paid = min(W, max(B, 0.0)); B = (B - paid) * (1 + nominal_r[t])
        else:
            B = B * (1 + nominal_r[t]); paid = min(W, max(B, 0.0)); B -= paid
        if paid < W - 1e-9:
            short += (W - paid) / cpi
            dep = dep or t + 1
        spend.append(paid / cpi)          # real, money of the start date
        cpi *= 1 + infl[t]
        bal.append(B / cpi)
    return {"balance_real": bal, "spend_real": spend, "depleted_year": dep,
            "shortfall_real": short, "success": dep is None}

def block_bootstrap(panel, horizon, block, n_paths, seed=0):
    """panel: array (Y, k) of jointly observed rows. Circular moving-block bootstrap."""
    rng = np.random.default_rng(seed)
    Y = panel.shape[0]
    out = np.empty((n_paths, horizon, panel.shape[1]))
    for i in range(n_paths):
        idx = []
        while len(idx) < horizon:
            u = int(rng.integers(Y))
            idx.extend((u + j) % Y for j in range(block))
        out[i] = panel[idx[:horizon]]
    return out
```

**Acceptance checks**
- Zero inflation, `r = 4%`, `W = 1,000,000 × 0.04/1.04` (= 38,461.54): real balance stays 1,000,000 for every
  year (start-of-period).
- `r = 4%`, `W = 50,000`, 50 years → `depleted_year == 38`.
- Real/nominal consistency: `(r = 4%, i = 0)` and `(r = 1.04·1.03 − 1, i = 3%)` give identical real
  balances.
- No-flow ordering invariance and the reversal example in 3.6.
- VPW with `g` equal to the realized constant return yields constant real spending and a terminal balance of 0.
- Guardrail switches individually disabled reproduce the constant-real result.
- Bootstrap with `block = Y` and one path reproduces a circular historical path; a fixed seed reproduces
  results exactly.

---

## 4. Goals-based planning

**Use when:** several goals (retirement, education, house deposit) compete for one balance sheet.

**Method**
1. Goal table (user): name, target amount in today's money, target date, priority (needs / wants /
   wishes), minimum acceptable probability, earmarked accounts.
2. Present value of each goal at a discount rate `ρ_g` matching its funding assets:
   `PV_g = G_g / (1 + ρ_g)^{n_g}`. **Funded ratio** = assets earmarked / `Σ PV_g`.
3. Required return for a single goal: solve `B_0 (1 + ρ)^n + C · ((1 + ρ)^n − 1)/ρ = G` for `ρ` by
   bisection on `[−0.5, 1]`; report "no solution" if the goal is reachable with `ρ ≤ 0` or unreachable at the
   upper bound.
4. Probability of reaching each goal: run the section 3 engine on the goal's sub-portfolio; report probability
   with the Monte Carlo interval.
5. Priority allocation: fund needs to their minimum probability first, then wants, then wishes; show the
   trade-off table (goal × probability) rather than a single score.

**Pitfalls:** mixing real goal amounts with nominal growth; double-counting an account across goals;
treating a deterministic required return as a forecast.

**Acceptance:** a goal with `G = B_0 (1 + ρ)^n` and `C = 0` returns exactly `ρ`; funded ratio of 1 with
deterministic `ρ_g` reaches every goal exactly.

### 4.1 Glide path (time-varying target weights)

**Use when:** a goal's allocation should de-risk as its date approaches (target-date style), or the user
wants to compare a glide path with a static mix.

**EODHD inputs:** the same return panel as section 2 (one TR proxy per asset class). The schedule itself is a
**user-declared policy**, not something EODHD supplies or this method optimizes.

**Method**
1. The user declares anchor rows `(y_k, w_{k,j})`: years to goal `y_k` and the weight of asset class `j` at that
   point. Each row sums to 1 and lies inside the IPS bands (6.1). Also declare the mode: "to" (weights stop
   changing at the goal date) or "through" (they keep changing for a stated number of years after it).
2. Interpolate linearly between anchors to get `w_j(y)` for any years-to-goal `y`, fractional values
   included. Outside the anchor range, hold the nearest anchor.
3. **Planning engine (3.1):** year `t` uses `a_{t,j} = w_j(Y_goal − t)` in `r_t = Σ_j a_{t,j} r_{j,t} − f`, and
   the portfolio is rebalanced to the glide weights each period.
4. **Rebalancing engine** ([methods-performance-risk §15](methods-performance-risk.md)): on each review date,
   set the targets to `w*_j = w_j(y_now)` and apply the usual bands and ordering. Label trades caused by a glide
   step as "glide-path step", separately from drift trades.
5. Compare the glide path with one or two static mixes on the **same** paths (historical rolling and block
   bootstrap, 3.4). Report success rate, 10th-percentile terminal wealth and the sensitivity to the last
   decade before the goal.

**Pitfalls:** presenting a glide path as optimal (it is a policy choice); a risky-asset share that rises as
`y` falls (warn, because the user may have intended something else); proxies on mixed bases (price vs TR).

**Acceptance:** with anchors 20 years → 90/10 and 0 years → 40/60 (equity/bonds), `y = 10` gives exactly 65/35,
and an anchor date returns its own row. A flat schedule reproduces the static-allocation engine result
exactly. Every interpolated row sums to 1.

---

## 5. Capital-market assumptions (CMA) from EODHD proxies

**Use when:** a proposal, IPS or planning engine needs expected returns, volatilities and correlations per
asset class.

**EODHD inputs:** total-return proxies (section 2.1), bond and cash from section 2.3 or bond-ETF
`adjusted_close`, international equity via ETF `adjusted_close` in the investor's currency (`*.FOREX`),
inflation (2.2). Current yields for building blocks: `ETF_Data::Yield` (percent string),
`ETF_Data::Fixed_Income` (current duration/YTM where populated), UST curve. Fundamentals calls cost 10 each.

**Method**
1. Fix the window and frequency (e.g. monthly, longest common span); record them.
2. Historical estimates per asset: arithmetic mean `a`, geometric mean `g = (Π(1 + r))^{1/n} − 1`
   (annualized), volatility `σ`. Relationship check: `g ≈ a − σ²/2`.
3. Forward building blocks (labelled as such):
   - Equity: `E[R] ≈ dividend yield + real earnings growth + inflation + valuation change` — yield from ETF
     `Yield`, the rest user assumptions.
   - Government bonds: current yield-to-maturity of the matching tenor (UST par) ≈ nominal return over a
     horizon close to duration.
   - Cash: current bill rate.
4. Covariance: sample covariance shrunk toward a target, `Σ̂ = δ F + (1 − δ) S`, with `F` the
   constant-correlation matrix (average sample correlation, sample variances) and `δ ∈ [0, 1]` stated (or
   estimated with a published shrinkage estimator).
5. Convert to real with `1 + ρ = (1 + r)/(1 + i)`.
6. Store a **versioned assumption set**: as-of date, window, proxies (symbols and basis), formulas, values,
   author. Plans and IPS documents reference the version id.

**Pitfalls:** price indices without dividends; ETF windows too short for crises; mixing arithmetic means into
compounding (use geometric for wealth projections, arithmetic for one-period expectations); currency of
proxy ≠ investor currency; sample means presented as forecasts.

**Acceptance:** `Σ̂` is symmetric and positive semi-definite (all eigenvalues ≥ −1e-12); geometric means
recompute from stored returns; every value carries a proxy and window.

---

## 6. Investment policy statement (IPS) and investment proposal

### 6.1 IPS template

An IPS is a governance document produced from user facts; EODHD contributes benchmark proxies and CMA
inputs. Fields marked (user) cannot come from market data.

| Section | Content |
|---|---|
| Parties and scope (user) | accounts covered, decision authority, review cadence |
| Objectives | return objective derived from goals (section 4, required return), risk tolerance (user: ability and willingness), income needs |
| Constraints (user) | horizon, liquidity, taxes, legal/regulatory, unique circumstances (concentrated stock, ESG exclusions) |
| Strategic allocation | target weights per asset class with min/max bands (absolute or relative) |
| Policy benchmark | blend of EODHD TR proxies with symbols, basis and rebalance rule (11.4) |
| CMA reference | assumption-set version (section 5) and expected return/volatility of the policy mix |
| Rebalancing policy | calendar, band or hybrid; cash-flow-first routing; tax-aware ordering (user rules) |
| Spending policy (if decumulating) | rule from 3.3 with parameters; smoothing (e.g. `W_t = α·W_{t−1}(1 + i) + (1 − α)·p·B_{t−1}`) |
| Monitoring and reporting | report set (section 11), drift review, IPS review triggers |
| Approval (user) | signatures/dates — the template does not certify suitability |

Acceptance: target weights sum to 1; bands contain targets; every benchmark component resolves to an EODHD
symbol with stated basis and start date; the CMA version exists.

### 6.2 Investment proposal assembly

**Use when:** a prospect or client proposal compares current holdings with a recommended model. It covers
the all-in cost, asset-class look-through, proxy risk statistics, projected goal outcomes, the fee-drag
illustration and the cost of moving.

**EODHD inputs**
- `fundamentals/{ETF}?filter=ETF_Data` (10 calls per request; the filter narrows the response, not the
  cost). One request returns `NetExpenseRatio` (a decimal string), `Asset_Allocation` (rows `Cash`,
  `Stock US`, `Stock non-US`, `Bond`, `Other`, `NotClassified`, each with `Long_%`, `Short_%` and
  `Net_Assets_%` as percent strings) and `Holdings`. These are current snapshots only.
- Mutual funds: `MutualFund_Data::Expense_Ratio`. Check its unit before use (section 1).
- Proxy returns: EOD `adjusted_close` of ETFs, or the TR indices in 2.1 (1 call per symbol). Use `*.FOREX`
  closes for the investor's currency.
- Projections: the section 3 engine and the section 4 goal probabilities on the CMA version from section 5.

**User inputs:** current holdings with lots and accounts; the proposed model and its vehicles; current and
proposed advisory fees; tax rates and the lot-relief method; trading-cost assumptions; goals.

**Method**
1. Resolve the current holdings to EODHD listings, using the held-away rules in 11.6. Price them at the raw
   close on the proposal date to get weights `w_i`.
2. Weighted expense ratio: `ER_p = Σ_i w_i·ER_i / Σ_{i covered} w_i`, with every `ER_i` as a decimal.
   Single stocks carry 0. A fund whose ratio is missing stays out of the numerator and the denominator, and
   the covered weight is reported. All-in annual cost: `f = advisory fee + ER_p + other user-supplied costs`.
3. Asset-class look-through: `A_c = Σ_i w_i·Net_Assets_%_{i,c} / 100`. Map single stocks to `Stock US` or
   `Stock non-US` by listing country. Report `Σ_c A_c` and the residual, because allocation rows seldom sum
   to exactly 100. Show `Other` and `NotClassified` rather than spreading them over the other rows.
4. Proxy-portfolio statistics for the current and the proposed mix. Use the same window and monthly
   returns in the investor's currency, rebalanced monthly to the weights. Report months covered, CAGR,
   annualized volatility, maximum drawdown, and the worst and best **complete** calendar year with the
   year named. List partial years and leave them out of the calendar-year statistics. Label everything
   "hypothetical, proxy-based". Do not deduct expense ratios from ETF `adjusted_close` returns, because they
   are already net of fund costs. Deduct the advisory fee only in a column labelled "net of advisory fee".
5. Projections: run the section 3 and section 4 goal probabilities for both mixes on the same paths and the
   same CMA version. Show the deterministic, historical-rolling and bootstrap results side by side.
6. Fee-drag illustration. Use start value `V`, gross annual return `r` (CMA geometric, labelled), horizon `n`
   and all-in fee `f`:
   `drag(f) = V·[(1 + r)^n − (1 + r − f)^n]`, and
   `difference = V·[(1 + r − f_prop)^n − (1 + r − f_cur)^n]`.
   The multiplicative form `(1 + r)(1 − f)` is an alternative; state which one you use.
7. Transition cost: add up three parts and report the total.
   - Estimated tax on the lots that would be sold. Relieve them by the user's method (section 7; specific ID
     if the user allows it) and apply the user's tax rates by term class. Losses offset gains under the
     user's rules.
   - Trading costs: commission plus half-spread × notional, as estimated by the user.
   - Fund exit or redemption fees, from the user.

   Report the total in currency and as a percentage of `V`. Add a simple payback: the first year in which the
   cumulative fee saving from step 6 is at least the transition cost. List phased options (harvest losses
   first, keep low-basis lots, direct contributions to the new model) as alternatives. Do not decide among
   them.
8. Assemble the pack in this order:
   1. summary;
   2. current vs proposed allocation and look-through;
   3. costs (ER, advisory, all-in, fee drag);
   4. risk statistics;
   5. projections and goal probabilities;
   6. transition cost and options;
   7. assumptions, proxies with symbols and windows, data as-of dates;
   8. a hypothetical label and a disclosures slot for the user.

```python
import pandas as pd

def weighted_expense_ratio(weights, er):
    """weights: symbol -> portfolio weight; er: symbol -> annual expense ratio as a DECIMAL or None.
    Single stocks carry 0. Returns (weighted ER over covered weight, covered weight)."""
    cov = sum(w for s, w in weights.items() if er.get(s) is not None)
    wer = sum(w * er[s] for s, w in weights.items() if er.get(s) is not None)
    return (wer / cov if cov else None), cov

def proxy_stats(monthly, weights):
    """monthly: DataFrame of monthly total returns (month-end DatetimeIndex, investor currency),
    one column per proxy; weights: column -> weight (rebalanced monthly)."""
    r = (monthly[list(weights)] * pd.Series(weights)).sum(axis=1)
    wealth = (1 + r).cumprod()
    years = len(r) / 12
    by_year = (1 + r).groupby(r.index.year).agg(["prod", "count"])
    full = by_year[by_year["count"] == 12]["prod"] - 1          # complete calendar years only
    dd = wealth / wealth.cummax().clip(lower=1.0) - 1
    return {"months": len(r), "cagr": wealth.iloc[-1] ** (1 / years) - 1,
            "vol": r.std(ddof=1) * 12 ** 0.5, "max_drawdown": dd.min(),
            "worst_year": (int(full.idxmin()), full.min()) if len(full) else None,
            "best_year": (int(full.idxmax()), full.max()) if len(full) else None,
            "partial_years": [int(y) for y in by_year.index[by_year["count"] < 12]]}
```

**Pitfalls:** mixing a decimal `NetExpenseRatio` with a percent-valued fund field (a 100× error); deducting
fund costs twice; a worst-year statistic taken from a partial year; current and proposed statistics on
different windows; estimating transition tax from today's price without the user's lots (report it as
"unknown basis" instead); fee-drag projections presented as forecasts.

**Acceptance checks**
- Weights {0.42, 0.18, 0.38, 0.02} with ERs {0.0003, 0.0008, 0.0003, 0 (stock)} → `ER_p = 0.000384`
  (3.84 bp), covered weight 1.0. Weights {0.5, 0.3, 0.2} with the third ER missing → `ER_p = 0.0025` on covered
  weight 0.8.
- Synthetic monthly series from 2020-01 to 2023-06: equity +1%/month except −2%/month in 2022, bonds
  +0.3%/month, 60/40. Result: worst complete year 2022 = `(1 − 0.0108)^12 − 1 = −12.217%`, best year 2020
  = +8.990%, maximum drawdown −12.217%, 2023 listed as partial.
- Fee drag with `V = 500,000`, `r = 6%`, `n = 20`: at `f_cur = 1.25%`, drag 338,684 and end value 1,264,884; at
  `f_prop = 0.85%`, drag 238,496 and end value 1,365,072. The difference is 100,188.
- With `f_prop = f_cur`, the difference is 0. With every sold lot at a loss and zero trading costs, the
  transition cost is 0 under a rule that does not tax losses.

---

## 7. Tax-lot accounting

**Use when:** cost basis, realized gains, unrealized P&L per lot, lot-method comparison. Section 35 of
[build recipes](build-recipes.md) is the build outline.

**EODHD inputs:** raw `close` for marking (EOD, 1 call/symbol); `/api/splits` and `/api/div` for basis
transforms and income (`unadjustedValue` = amount actually paid per share then; `value` = split-adjusted —
see the dividends endpoint page); `*.FOREX` closes for currency conversion; `General.CurrencyCode` /
symbol-list `Currency` for units (GBX/ZAC ÷ 100). **User inputs:** every buy, sell, fee, transfer and
corporate-action election with trade date, settlement date, account, quantity, price, currency; jurisdiction
rules (holding-period threshold, permitted lot methods, FX convention, treatment of fees).

**Lot record:** `lot_id, account, security_id (ISIN + listing), acquired_date, qty, total_cost (incl.
fees, home currency), cost_ccy, fx_rate_used, source_txn_ids, adjustments[]`.

**Relief methods for a sale of quantity `Q`:**

| Method | Order of lots consumed |
|---|---|
| FIFO | earliest `acquired_date` first |
| LIFO | latest first |
| HIFO | highest unit cost first (ties: earliest) |
| Specific ID | user-designated lot ids, recorded at trade time |
| Average cost | pooled unit cost `Σ cost / Σ qty`; basis taken `= Q · avg` (only where the jurisdiction/fund type permits) |

Worked example (sell 150 at 14.00, proceeds 2,100; lots A 100 @ 10.00, B 100 @ 15.00, C 100 @ 12.00 in date
order):

| Method | Basis relieved | Realized gain |
|---|---|---|
| FIFO | 1,750 (A 100 + B 50) | 350 |
| LIFO | 1,950 (C 100 + B 50) | 150 |
| HIFO | 2,100 (B 100 + C 50) | 0 |
| Average cost | 1,850 (avg 12.3333) | 250 |

**Steps**
1. Import and reconcile transactions (quantity roll-forward per account/security = statement position).
2. Apply corporate actions in date order: **split** `k:1` multiplies lot quantity by `k`, keeps total cost and
   acquisition date; reverse split divides; cash-in-lieu for fractions is a user-reported sale. Spin-offs and
   mergers: basis allocation by FMV ratio on the first regular-way date from EODHD closes, ratio confirmed by
   the user ([corporate actions](corporate-actions.md)). Ledger events:
   - **Cash-in-lieu:** for a fraction `φ` of a share, proceeds = `φ × cash price per share` (the company's
     announced price, taken from the statement). Basis relieved = `φ × post-action basis per share`; gain =
     proceeds − basis relieved. The disposal keeps the parent lot's acquisition date.
   - **Stock merger at ratio `k`:** close each target lot and open an acquirer lot with quantity `q·k`. A
     fractional remainder becomes cash-in-lieu. Carry basis and acquisition date by the user's rule.
   - **Cash-and-stock or all-cash consideration:** record the cash leg as proceeds at the deal terms, never at
     the last traded close. How much gain is recognized (for example, limited to the cash received) is a
     user or jurisdiction rule.
   - **Entitlement:** a lot is entitled to a distribution if it was held at the close of the session before
     the ex-date (EODHD `/api/div` `date`). Under US T+1 settlement (since 2024-05-28) the regular ex-date
     equals the record date; the endpoint's sample rows show `date == recordDate`. Verify the convention
     for other markets.
3. On each sale, relieve lots by the account's method; produce disposal rows.
4. Holding period: `sale_date − acquired_date` against the **user-supplied** threshold and counting
   convention; classify short/long (or the jurisdiction's classes).
5. Currency: basis at the acquisition-date rate, proceeds at the disposal-date rate (or the user's rule);
   EODHD `*.FOREX` daily close is a market close, not an official fixing — label it.
6. Unrealized P&L per lot: `qty · close_raw(normalized) · fx − total_cost`.

**Realized gain report columns:** account, security, lot id, acquired, sold, qty, proceeds, basis,
adjustments (e.g. disallowed loss), gain, term class, method, FX source, source transaction ids.

**Pitfalls**
- Marking lots with `adjusted_close` understates market value after dividends and splits; lots hold actual
  shares, so mark with raw `close` and a split ledger.
- Never re-create missing acquisitions from price history; a missing lot is an "unknown basis" exception.
- Transfers between own accounts move lots (with dates and basis), they are not sales.
- GBX quotes against GBP cost basis: a 100× error.

**Acceptance checks**
- Lot-method example above reproduces exactly.
- Σ remaining lot qty = statement position; Σ relieved basis + Σ remaining basis = Σ purchase cost
  (+ adjustments).
- Split neutrality: market value and total basis unchanged across a `k:1` split.
- Overselling raises an error, not a negative lot.
- Cash-in-lieu: 0.5 share at 40.00 with post-split basis 30.00 per share → proceeds 20.00, basis relieved
  15.00, gain 5.00. Remaining lot basis + relieved basis = pre-action basis.

### 7.1 Dividend holding-period window (estimate)

**Use when:** estimating whether the dividends on a user's lots meet a jurisdiction's holding-period test
(for example, for a reduced-rate dividend class), or reviewing dividend-capture trades. The broker's or tax
authority's classification decides; this is a labelled estimate.

**EODHD inputs:** `/api/div/{SYM}` (1 call per symbol, full history): `date` (the ex-dividend date),
`recordDate`, `paymentDate` and `unadjustedValue` (the amount actually paid per share). **User inputs:** the
lots from section 7 with acquisition and disposal dates, and the rule parameters:
- window offset `a`: the window starts `a` days before the ex-date;
- window length `L` in days;
- minimum holding days `N`, and whether the rule says "at least" or "more than";
- the day-count convention (commonly the acquisition day is excluded and the disposal day included);
- hedged days to exclude;
- longer windows for some security types (for example, certain preferred dividends).

Never hard-code these parameters.

**Method**
1. For each dividend event with ex-date `X`, select the shares that were entitled (held at the close before
   `X`). After partial sales, use the lot-relief method to decide which shares those are.
2. Build the window `W = [X − a, X − a + L − 1]`.
3. For each lot, count `days_held = |[max(acq + 1, W_start), min(disposal or W_end, W_end)]|` under the
   user's convention, minus hedged days.
4. Assign a status: **meets** if `days_held` passes the threshold. **Fails** if it cannot pass. **Pending** if
   the lot is still open and the window has not ended. **Unknown** if the lot dates are missing.
5. Report each dividend × lot: shares, amount (`shares × unadjustedValue`, in the payment currency), days
   held, status and the parameters used.

**Acceptance** (parameters a US-style user might supply: `a = 60`, `L = 121`, more than 60 days required,
acquisition day excluded): ex-date 2026-05-11 gives the window 2026-03-12 to 2026-07-10. A lot bought on
2026-04-01 and sold on 2026-05-20 has 49 days → fails. Sold on 2026-05-31: 60 days → fails. Sold on
2026-06-01: 61 days → meets. The same lot, still open and evaluated on 2026-05-25 (54 days so far, window
not ended), is pending; it becomes "meets" on 2026-06-01.

---

## 8. Repurchase-window (wash-sale-type) checks across accounts

**Use when:** a loss sale may be disallowed or deferred because the same or an equivalent security was
acquired within a window around the sale. **All rule parameters are user-supplied** (window length before and
after, which accounts count, what counts as equivalent, basis treatment); do not hard-code a jurisdiction.

**Method**
1. Equivalence groups: identical ISIN (all listings: use `/api/id-mapping` with `filter[isin]` to collect
   listing symbols), plus user-declared groups (share classes, options on the same underlying if the user's
   rule says so). Market-data similarity is evidence for review, never the decision.
2. For each disposal at a loss (`gain < 0`) on date `D` with quantity `Q_s`: collect acquisitions in the same
   group across **all supplied accounts** (including spouse/retirement accounts if the user's rule includes
   them) with trade date in `[D − w_before, D + w_after]`, excluding the lots relieved by the sale itself.
3. Matched quantity `Q_m = min(Q_s, Σ replacement qty)` (allocate replacements in date order; a replacement
   share can absorb only one disallowed sale).
4. Disallowed loss `= |loss| · Q_m / Q_s`. If the user's rule defers it: add it to the replacement lots'
   basis pro rata and, if the rule says so, carry the original holding period.
5. Output per disposal: matched replacements, disallowed amount, adjusted basis, and accounts involved;
   unresolved items (missing account data, ambiguous equivalence) go to a review list.

**Pitfalls:** dividend reinvestments are acquisitions; checking one account only; matching on ticker text
(reused tickers, `_old` codes); trade vs settlement date (use the user's rule, default trade date).

**Acceptance:** sell 100 at a loss of 500, buy 60 in another account 10 days later with a 30/30 window
supplied → disallowed 300, replacement basis +300; the same purchase 31 days later → disallowed 0; a gain
sale never triggers.

---

## 9. Tax-loss harvesting: screen, replacements, net benefit

**Use when:** finding lots with harvestable losses and exposure-preserving replacements. The output is a
research list for the user/adviser; it does not certify "substantially identical" status or eligibility.

### 9.1 Candidate screen
Inputs: lots (section 7), current raw close, user thresholds.
1. Unrealized loss per lot `L = total_cost − market value > 0`.
2. Keep lots with `L ≥ L_min` (currency) **and** `L / total_cost ≥ p_min`.
3. Exclude or flag lots whose sale would hit the repurchase window (recent buys, scheduled reinvestments,
   section 8).
4. Annotate: term class, days until the term class changes, gains available to offset this year (user's
   realized-gain report), expected distributions before the window ends (EODHD `/api/div` history as context;
   future amounts unknown).

### 9.2 Replacement ranking
**EODHD inputs:** `fundamentals/{ETF}?filter=ETF_Data::Holdings` (10 calls; keys like `AAPL.US` with
`Assets_%`), `ETF_Data` top level (`NetExpenseRatio`, `Index_Name`, `TotalAssets`, `Inception_Date`),
EOD `adjusted_close` (1 call each), `volume` for liquidity.

| Measure | Formula |
|---|---|
| Holdings overlap | `Σ_i min(w_A,i, w_B,i)` over matched constituents (weights as decimals; report covered weight) |
| Return correlation | Pearson correlation of weekly log returns of `adjusted_close`, common dates, 1–3 years |
| Tracking error | `std(r_A − r_B) · √52` (weekly) |
| Beta | `cov(r_B, r_A) / var(r_A)` |
| Cost | `NetExpenseRatio` difference; liquidity proxy = median daily traded value, pairing split-adjusted `volume` with split-adjusted prices (raw close × split-adjusted volume mixes share units; see data-semantics) |

Rank by low tracking error / high correlation subject to the user's similarity policy (e.g. overlap below a
user threshold, different `Index_Name`). Flag pairs with overlap or correlation so high that the user's
equivalence rule may treat them as the same security; the decision stays with the user/adviser.

### 9.3 Net benefit
With user tax rates `τ_now` (rate on the gains/income offset now), `τ_later` (rate expected when the
replacement is sold), deferral years `H` and discount rate `k`:

```
gross tax value   = L · τ_now
future tax cost   = L · τ_later / (1 + k)^H        # lower basis in the replacement
trading costs     = commissions + spread_A + spread_B (both legs, user/estimated)
net benefit       = gross tax value − future tax cost − trading costs
```

Report tracking error as a risk, not a cost. Tax drag context: annual distribution yield (from dividends)
`× τ_div` for the old vs the replacement fund.

**Acceptance:** `τ_later = τ_now`, `H = 0` → net benefit = −trading costs; a lot with `L < L_min` never
appears; replacements identical to the sold security (same ISIN) are never proposed.

---

## 10. AUM fee billing and performance fees

**Use when:** advisory fee calculation, invoice checks, fee impact in proposals. Fee schedules, billing
terms, exclusions and contract language are user inputs.

### 10.1 Schedules
| Type | Formula | Behaviour at a boundary |
|---|---|---|
| Tiered (marginal) | `Fee = Σ_k rate_k · max(0, min(A, U_k) − U_{k−1})` | continuous |
| Breakpoint (whole balance) | `Fee = A · rate_{k(A)}`, `k(A)` = tier containing `A` | drops at boundary (cliff) |
| Flat / minimum | `max(rate·A, minimum)` | |

Example schedule: 1.00% to 1m, 0.75% 1m–5m, 0.50% above. `A = 6,000,000`: tiered 45,000/year (blended 0.75%),
breakpoint 30,000. Cliff test: breakpoint fee at 5,000,000 = 37,500, at 5,000,001 = 25,000.

### 10.2 Billing period
1. Billing value per user terms: period-end MV, average daily balance, or average of period-end values;
   exclusions (held-away, unsupervised assets, cash) applied first. Mark with EODHD raw close × qty, units
   normalized, FX at the valuation date.
2. Household aggregation (if contracted): compute the fee on aggregate household value, then allocate to
   accounts pro rata to their billable value.
3. Proration: `Fee_period = Fee_annual(A) · days_in_period / days_in_year` under the stated day count
   (actual/365, actual/actual, 30/360). `A = 6m`, 92-day quarter, actual/365 → 11,342.47.
4. Intra-period flows (advance billing): adjustment `= blended_rate · flow · days_remaining / days_in_year`,
   positive for deposits, refund for withdrawals, subject to the user's minimum-flow threshold.
5. Output invoice lines: account, billable value, schedule, rate, days, fee, adjustments, exclusions.
6. **Tie-out to the valuation file.** Billable value per account = valuation-file NAV for that account on
   the billing valuation date (11.3), minus the listed exclusions. Each exclusion line names the security
   or account, its value, the contract reason and the source. The valuation file's date must equal the
   billing valuation date. Any difference from the billed value is a break: list it with the account,
   amount and likely cause (exclusion not applied, stale price, flow timing). Do not absorb it silently.

### 10.3 Performance fees with high-water mark and hurdle
Per unit/series (user terms decide crystallization frequency, hurdle type, equalization):

```
hurdle_level = HWM · (1 + h)^(days/365)        # if a hurdle applies; else HWM
fee_per_unit = rate · max(0, NAV_gross − hurdle_level)
NAV_net      = NAV_gross − fee_per_unit
HWM_new      = NAV_net if fee_per_unit > 0 else HWM   (on crystallization)
```

Example (rate 20%, no hurdle, HWM 100): NAV 112 → fee 2.40, NAV_net 109.60, HWM 109.60; next period NAV 105 →
fee 0; then NAV 115 → fee 1.08. Investor-level equalization or series accounting comes from the fund
documents; do not default it.

**Acceptance:** tiered fee continuous across boundaries; Σ allocated household fee = household fee; HWM never
decreases; no fee while NAV ≤ HWM. Billing tie-out: account NAV 1,250,400.00 on the valuation date, with
exclusions "unsupervised stock" 80,400.00 and "cash sweep" 20,000.00 (excluded by contract) → billable
1,150,000.00 to the cent. A billed value of 1,170,000.00 is reported as a +20,000.00 break ("cash exclusion
not applied"), not passed.

---

## 11. Client and household reporting maths

**Use when:** quarterly client reports, household dashboards, proposals with history. User inputs:
positions, transactions, external flows, fees. Broader return/attribution formulas are in
[portfolio and risk](portfolio-risk.md).

### 11.1 Period returns
- **Modified Dietz** for a period of `CD` days: `R = (EMV − BMV − F) / (BMV + Σ_i F_i · (CD − D_i)/CD)`,
  `F = Σ F_i`, `D_i` = day of flow (contributions +, withdrawals −). Example: BMV 100,000, EMV 112,000,
  +10,000 on day 10 of 30 → `R = 2,000 / 106,666.67 = 1.875%`.
- **TWR:** value the portfolio at every external flow (daily with EODHD closes), sub-period
  `r_k = (V_end − V_start − F_k)/V_start` with flows at the start of day, then `R = Π(1 + r_k) − 1`.
- **Money-weighted (IRR/XIRR)** for the investor's experience; may have no or multiple roots — report.
- **Gross vs net of fees:** net uses values after fees deducted from the account; gross adds fees back
  (treat fees as if they were external withdrawals). Show the fee source.
- Period table: MTD, QTD, YTD, 1y, 3y, 5y, since inception; annualize only periods > 1 year:
  `(1 + R)^(365/days) − 1`.

### 11.2 Contribution and household aggregation
- Single-period contribution `c_i = w_i,begin · r_i`; `Σ c_i = R_portfolio` for a buy-and-hold period. Multi-
  period contributions need linking (portfolio-risk). Show top/bottom 3.
- **Household return**: aggregate MVs and flows across accounts first, then compute TWR; never average
  account returns. Account-level and household tables must tie: Σ account EMV = household EMV.
- AUM change decomposition: `EMV − BMV = net flows + market effect (− fees if billed from the account)`;
  organic growth rate = `net flows / BMV`.

### 11.3 Valuation tie-out
`NAV = Σ qty · price_raw(normalized) · fx + cash`; stale or missing prices are flagged and listed, not
dropped. Price-source date must match the report date (or carry an explicit stale flag).

### 11.4 Benchmarks
- Blended benchmark: `r_b,t = Σ_j W_j r_j,t` with TR proxies (section 2.1) on the same dates and currency;
  rebalanced to `W` on stated dates (monthly) or left to drift between stated rebalance dates.
- Excess return = portfolio − benchmark (geometric `(1 + R_p)/(1 + R_b) − 1` if stated).

**Acceptance:** Modified Dietz example reproduces; contributions sum to portfolio return; a portfolio holding
exactly the benchmark ETF with no flows shows ≈ 0 excess return; household tables tie to account tables.

### 11.5 Goal-progress panel and narrative rules

**Use when:** a performance or client report should show whether each goal is on track, not just returns.

**Inputs:** the goal table (section 4) and its assumption set (real discount or return `ρ_g`, planned
contributions `C` per year, the CMA version); earmarked account values at the report date. No EODHD call is
needed beyond the valuation (11.3) and, optionally, a fresh simulation (section 3).

**Method**
1. Required value today for goal `g`, with `n_t` years left and end-of-year contributions:
   `B_req(t) = [G − C·((1 + ρ)^{n_t} − 1)/ρ] / (1 + ρ)^{n_t}` (use `G − C·n_t` in the numerator when `ρ = 0`).
   If `B_req ≤ 0`, contributions alone reach the goal, and the panel says so.
2. Progress ratio = `B_t / B_req(t)`. Status bands are user-set; a default is on track ≥ 1.00, watch
   0.90–1.00, off track < 0.90. Label the bands as heuristics.
3. Optionally add the simulated probability of reaching the goal (4, step 4), with the simulation date,
   CMA version and Monte Carlo interval.
4. Chart the actual value against the required path. Either keep the path fixed at the plan date or
   recompute it with the assumptions in force at each date, and state which.
5. Place it in the report after the period table and benchmark comparison and before holdings. The
   tearsheet order is in [methods-performance-risk §7.4](methods-performance-risk.md). Put the attribution
   summary (top and bottom contributors, 11.2) between the returns and the goal panel.

**Narrative rules** (plain-language text generated from computed fields only):
- Every number in the text comes from a table cell and carries its period, basis (TWR or money-weighted,
  gross or net) and currency.
- Use this order: what happened (returns vs benchmark), why (attribution summary), where the goals stand,
  what is proposed (actions are "proposed", never "executed").
- No forecast language: write "under assumption set X the simulated probability is 78%", not "you will
  reach".
- Write missing or stale data as such ("price as of 2026-10-22, stale").

**Acceptance:** `G = 200,000` (real), `n_t = 10`, `ρ = 4%`, `C = 10,000` per year → `B_req = 54,003.88`; with an
actual value of 60,000 the ratio is 1.111, "on track". With `C = 0`, `B_req = G/(1 + ρ)^{n_t}`. Every number
in the narrative matches a table cell.

### 11.6 Model portfolios, UMA sleeves and held-away assets

**Use when:** an account is run as several sleeves, each following its own model (a unified managed
account), with a cash buffer, and the household also has assets held elsewhere.

**User inputs:** sleeves (sleeve id, model id, sleeve share `S_s` of the invested part with `Σ S_s = 1`), model
weights `m_{s,i}`, the cash-buffer target `c` (fraction of account value) with tolerance, sleeve
sub-accounting of positions (from the custodian), held-away statements (identifier, quantity, statement
value and date).

**EODHD inputs:** raw close on the valuation date (EOD, 1 call per symbol; GBX/ZAC ÷ 100; `*.FOREX`);
`/api/id-mapping?filter[isin]=…` or `filter[cusip]=…` (1 call; current identifiers only) to resolve
held-away lines; the exchange symbol list (1 call per exchange) to validate the chosen listing.

**Method**
1. Account targets: `w*_i = (1 − c)·Σ_s S_s·m_{s,i}`, and `w*_cash = c` plus any cash the models hold.
2. Valuation: value each sleeve's positions as `qty × raw close × FX`. Σ sleeve values + unassigned cash =
   account value.
3. Drift is checked at two levels.
   - Sleeve share: `V_s / (V − cash)` against `S_s`.
   - Within each sleeve: weights against `m_{s,i}`.

   For concentration and repurchase-window checks (section 8), the same security held in two sleeves
   counts as **one** account position.
4. Trades:
   - Investable value is `V_inv = V − max(c·V, pending withdrawals + reserved cash)`.
   - Size each sleeve's trades to its targets on `V_inv`.
   - Net buys and sells of the same security across sleeves at account level before release, so one sleeve
     does not buy what another sells.
   - Bands, ordering and rounding follow [methods-performance-risk §15](methods-performance-risk.md).
   - Cash must stay at or above `c·V` minus the tolerance after the trades.
5. Performance: sleeve TWR treats transfers between sleeves as external flows for each sleeve, but account
   TWR ignores them. Sleeve contributions, using start-of-sub-period weights, sum to the account return.
6. **Held-away assets:**
   - Resolve each statement line by ISIN or CUSIP through `id-mapping`. Pick the listing whose exchange and
     currency match the statement, then price it at the raw close on the valuation date.
   - Lines that are unresolved, ambiguous or have no EODHD price stay **unpriced**: carry the statement value
     and date, flagged "user statement". Examples are private funds, annuities, bank CDs and collective
     trusts.
   - Never price a line from a similar-looking ticker.
   - Flag statement values older than a user-set number of days as stale.
7. Usage rules:
   - Household views include held-away assets.
   - Billing excludes them unless the contract says otherwise (10.2).
   - Drift includes them only if the IPS sets the allocation at household level.
   - Computed TWR excludes unpriced lines, or shows them as a separate flagged line.

**Acceptance:** sleeves equity 0.6 (model A 0.7 / B 0.3) and bonds 0.4 (model C 1.0) with `c = 0.02` → account
targets A 0.4116, B 0.1764, C 0.392, cash 0.02, summing to 1. Σ sleeve values + cash = account value. A
held-away line with an unknown CUSIP appears as unpriced at its statement value, with a flag. A security
held in two sleeves appears once in the account concentration table, and a buy and a sell of it in
different sleeves on the same day are netted.

### 11.7 Client review pack template

**Use when:** preparing a periodic client review: performance since the last review, allocation against the
IPS, proposed rebalancing with its tax effect, and talking points.

| # | Section | Content and source |
|---|---|---|
| 0 | Cover | client, accounts, review period `D_prev` → `D_now`, data as-of date, currency, basis |
| 1 | Performance since last review | net and gross TWR from `D_prev` to `D_now` (11.1), the standard period table, benchmark and excess return (11.4), attribution summary (11.2) |
| 2 | Goal progress | panel from 11.5 |
| 3 | Allocation vs IPS | drift table: target, current, drift, band, breach flag ([methods-performance-risk §15.1](methods-performance-risk.md)); household view including held-away assets if the IPS says so (11.6) |
| 4 | Proposed rebalance | trade list labelled **proposed, not executed**; per sale the lots relieved by the account's method (section 7), estimated realized gain/loss by term class, estimated tax at the user's rates, repurchase-window check (section 8), harvesting candidates (9.1) |
| 5 | Flows and fees | contributions and withdrawals since `D_prev`; fees billed (10.2) |
| 6 | Changes in circumstances | slots for the advisor: income, goals, risk tolerance, constraints (user input only) |
| 7 | Talking points | 3–6 slots; each one cites the table cell it relies on (for example "§1 row YTD") |
| 8 | Agenda and action items | owner and date for each item; decisions are recorded by the user |
| 9 | Data notes and disclosures | proxies, stale prices, unpriced held-away lines, hypothetical labels, disclosure slot |

**Acceptance:** the drift-table weights sum to 1; every talking point resolves to a cell in sections 1–5; the
realized gains of the proposed trades recompute from the stored lots and method; no section claims an
executed trade.

---

## 12. Trade-statement audit and journal analytics

**Use when:** a trader uploads broker statements/fills (CSV/PDF) and asks "what is my edge", "am I
over-trading", "what did costs do". Fills, fees, account balances and timestamps are user data; EODHD adds
benchmark returns, marks, FX and intraday paths. See also
[paper trading and accounting](paper-accounting.md#trade-journal-and-performance-coaching).

### 12.1 Parsing and reconstruction
1. Preserve the original file; map columns (symbol, side, qty, price, fee, currency, time, account) with a
   per-row parse confidence; quarantine rows that fail.
2. Resolve symbols to EODHD listings ([identity](identity.md), recipe 40); normalize units/currency.
3. Build round-trip trades: a trade opens when the position leaves 0 and closes when it returns to 0;
   partial fills aggregate; scale-ins/outs are fills within one trade. Open trades are reported separately
   and excluded from closed-trade statistics.
4. Trade P&L (net) `= Σ sell proceeds − Σ buy costs − fees` (signs reversed for shorts), in account currency;
   convert to base currency with `*.FOREX` at the exit date (state the rule).
5. Reconcile: Σ net trade P&L + other cash items (interest, financing, dividends) = statement net change −
   deposits + withdrawals. A residual blocks the report or is shown as unexplained.

### 12.2 Starting equity
Take the opening balance from the statement. If absent, **ask**. Never back it out from P&L or assume a
round number; percentage returns, drawdowns, Kelly sizing and ruin all depend on it. Equity curve:
`E_t = E_0 + cumulative net P&L + deposits − withdrawals`.

### 12.3 Statistics (closed trades, `n` trades, `n_w` wins, `n_l` losses)

| Metric | Formula | Edge cases |
|---|---|---|
| Win rate | `p = n_w / n` (define scratch trades, e.g. abs(P&L) ≤ fees, and state whether excluded) | `n = 0` → undefined |
| Wilson 95% CI | `(p + z²/2n ± z·√(p(1−p)/n + z²/4n²)) / (1 + z²/n)`, `z = 1.96` | 30/50 → [0.462, 0.724] |
| Average win / loss | `W̄ = Σwins/n_w`, `L̄ = Σ|losses|/n_l` | zero count → undefined |
| Expectancy | `Σ P&L / n` (= `p·W̄ − (1−p)·L̄`); also in R if planned risk exists | |
| Profit factor | `Σ wins / Σ |losses|` | no losses → undefined ("no losing trades"), not ∞ |
| Payoff ratio | `b = W̄ / L̄` | |
| Kelly fraction | `f* = p − (1 − p)/b` | negative → no edge; show half-Kelly `f*/2`; recompute with the Wilson lower bound for `p` as a conservative variant; warn when `n < 30` |
| R-multiple | `P&L / planned risk` | planned risk missing → unavailable, not inferred |
| Max drawdown | from the equity curve (needs `E_0`) | |
| Longest loss streak | longest run of consecutive losing trades | compare with expectation ≈ `ln(n(1−q)) / ln(1/q)`, `q = 1 − p` (`n = 200`, `q = 0.45` → ≈ 5.9) |

Small-sample rule: show `n` beside every statistic; grey out or suppress breakdown buckets with fewer than a
user-set minimum (e.g. 20 trades).

### 12.4 Risk of ruin (Monte Carlo)
Ruin is user-defined, e.g. peak-to-trough equity drawdown ≥ `D` (or equity below a floor) within `M` future
trades.
1. Per-trade returns on equity `x_j = P&L_j / E_{before j}` (requires 12.2).
2. Simulate `N` paths (≥ 10,000) of `M` trades by resampling `x_j` with replacement (or in blocks to keep
   streak dependence); `E ← E (1 + x)`.
3. `P(ruin)` = share of paths that hit the threshold; report with Wilson interval and the assumption that
   past trades are exchangeable.

### 12.5 Behaviour flags (evidence-based, non-diagnostic wording)
Thresholds are user parameters; each flag lists the trades that triggered it.

| Flag | Evidence rule |
|---|---|
| Size after loss | median position size (or risk) of trades opened within `m` minutes after a losing exit ÷ overall median > 1.5 |
| Frequency after loss | trades per hour in the `h` hours after a loss ÷ baseline > 2 |
| Holding asymmetry (disposition) | median holding time of losers ÷ winners > 1.5 |
| Size creep | rolling 20-trade median size rising > 50% while rolling expectancy ≤ 0 |
| Overtrading days | days with trade count above the user's 95th percentile and negative net P&L |
| Stop changes | planned stop moved further away after entry (only if stop history exists) |
| Chasing entries | needs a planned entry (pivot or limit) in the journal. Long: `P_fill / P_plan − 1 > max_chase` (user parameter; [paper-accounting](paper-accounting.md) defaults to 0.02, the examples here use 0.05); short: mirror it. Report the chase rate and the expectancy of chased vs non-chased trades with `n` for each. Trades without a planned entry count as "no plan", not as compliant ([methods-technical-market §10](methods-technical-market.md) for entry/exit rules) |

Write "pattern observed in N trades" rather than psychological labels.

### 12.6 Time and cost breakdowns
- Convert fill timestamps to exchange time with `Timezone` (IANA) from `/api/exchange-details/{EX}`
  (Extended or All-In-One); bucket by hour, session (pre-market / regular / after-hours from `TradingHours`)
  and weekday. Compute only if ≥ 80% of trades have timestamps (state coverage).
- Rolling 30/60/90-day windows of expectancy, win rate and profit factor against the full history.
- **Setup-tag breakdown:** group closed trades by the user's setup tag. Untagged trades form their own bucket
  and are never assigned a tag by inference. For each bucket show `n`, win rate with its Wilson interval,
  expectancy (in currency and in R where planned risk exists), profit factor and share of total P&L.
- **Holding-period breakdown:** bucket by sessions held, counted on the exchange calendar. Default buckets
  (user-adjustable): intraday, 1–5, 6–20 and more than 20 sessions. Show the same columns as the setup-tag
  breakdown. Buckets with fewer trades than the user's minimum (12.3) are suppressed or greyed out, with `n`
  shown.
- Cost drag: `costs / gross P&L` when gross P&L > 0; otherwise report `Σ costs / Σ |notional| × 10,000` in
  basis points. Costs = commissions + fees + financing/swaps (+ estimated spread if the user supplies a
  method).

### 12.7 MAE / MFE from EODHD intraday bars
**EODHD inputs:** `/api/intraday/{SYM}?interval=1m|5m|1h&from=&to=` (Unix seconds UTC; 5 calls per request;
EOD+Intraday Extended or All-In-One; max 120/600/7200 days per request for 1m/5m/1h); bars stamped at their
start, unadjusted, US bars include extended hours; per-symbol start dates vary (probe).
For a long trade entered at `P_in`, time `t_in`, exited at `t_out`:

```
MAE = min(low over bars fully inside (t_in, t_out)) − P_in      (≤ 0)
MFE = max(high over bars fully inside (t_in, t_out)) − P_in     (≥ 0)
```

Shorts swap high/low and signs. Express in currency, % of entry and R. The entry and exit bars contain
prices from before/after the fills: exclude them or include them with a flag (state which). Include
extended-hours bars only if the trade was open through that session. A split during the holding period
requires scaling bars before the split date (intraday is unadjusted). Multi-day holds may use EOD raw
high/low for whole days in between, labelled. Missing bars are missing, not flat.

### 12.8 Benchmark comparison
Daily account TWR (from equity and flows) vs a TR benchmark (`SPXTR.INDX` or an ETF `adjusted_close`) on the
same dates; report excess return, beta of daily account returns to the benchmark, and the share of P&L
explained by market exposure. Positions must be marked daily with raw close × qty to build daily equity.

**Acceptance checks**
- Example `[100, −50, 200, −50, −50, 150, −100, 120]`: n 8, win rate 0.50 (Wilson [0.215, 0.785]),
  avg win 142.5, avg loss 62.5, expectancy 40, profit factor 2.28, payoff 2.28, Kelly ≈ 0.281, half-Kelly
  ≈ 0.140, longest loss streak 2.
- Zero trades → all metrics undefined, no division error; all-winning sample → profit factor undefined with
  reason.
- Ruin probability is 0 when every resampled trade return is positive and 1 when one return is ≤ −D on
  every path.
- Every metric recomputes from the stored parsed trade table; the reconciliation residual is reported.
- Chase flag with `max_chase = 0.05`: planned 50.00 and filled at 52.60 (+5.2%) → flagged; filled at 52.40 (+4.8%) →
  not flagged; no planned entry → "no plan". The bucket counts of the setup-tag and holding-period breakdowns
  sum to the closed-trade count.

```python
import math

def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)

def journal_stats(pnl):
    n = len(pnl)
    if n == 0:
        return {"n": 0}
    wins = [x for x in pnl if x > 0]
    losses = [-x for x in pnl if x < 0]
    p = len(wins) / n
    aw = sum(wins) / len(wins) if wins else None
    al = sum(losses) / len(losses) if losses else None
    b = aw / al if aw is not None and al else None
    kelly = p - (1 - p) / b if b else None
    streak = cur = 0
    for x in pnl:
        cur = cur + 1 if x < 0 else 0
        streak = max(streak, cur)
    return {"n": n, "win_rate": p, "win_ci": wilson(len(wins), n),
            "avg_win": aw, "avg_loss": al, "expectancy": sum(pnl) / n,
            "profit_factor": sum(wins) / sum(losses) if losses else None,  # None = undefined
            "payoff": b, "kelly": kelly, "half_kelly": kelly / 2 if kelly is not None else None,
            "max_loss_streak": streak}
```

---

## 13. Household finance modules

Context and boundaries: [personal planning](personal-planning.md). Income, spending, balances, debts, loan
notes, insurance, property data and tax rates are **user inputs**. EODHD supplies:
- investment return ranges (section 2 panel, section 5 CMA);
- prices of held securities;
- UST bill and par yields (`/api/ust/bill-rates`, `/api/ust/yield-rates`; all plans; 1 call per request);
- reference rates such as `SOFR` and `SOFR30D` (`/api/rates/reference-rates`; Fundamentals Feed or
  All-In-One; 1 call; percent);
- country-level BIS residential property price indices (`/api/real-estate/{CC}`; Fundamentals Feed or
  All-In-One; 5 calls per request; quarterly).

Thresholds in this section are **labelled heuristics** that the user can override. They are not standards or
lending rules.

### 13.1 Time-value-of-money block

Here `r` is the rate per period, `n` the number of periods and `g` the growth per period. An ordinary annuity
pays at the end of each period; an annuity due pays at the start.

| Quantity | Formula | Example (`r = 5%`, `n = 10`, payment 1,000) |
|---|---|---|
| FV of a lump sum | `PV·(1 + r)^n` | PV 1,000 → 1,628.89 |
| PV of a lump sum | `FV / (1 + r)^n` | |
| PV, ordinary annuity | `PMT·[1 − (1 + r)^(−n)] / r` | 7,721.73 |
| PV, annuity due | ordinary × `(1 + r)` | 8,107.82 |
| FV, ordinary annuity | `PMT·[(1 + r)^n − 1] / r` | 12,577.89 (due: 13,206.79) |
| PV, growing annuity (first payment `PMT` at end of period 1) | `PMT/(r − g)·[1 − ((1 + g)/(1 + r))^n]`; `r = g` → `n·PMT/(1 + r)` | `g = 2%` → 8,388.11 |
| Perpetuity / growing perpetuity | `PMT / r`; `PMT_1 / (r − g)`, only for `r > g` | 20,000; 33,333.33 |
| NPV | `Σ_{t=0}^{T} CF_t / (1 + r)^t` (date-based: exponent `days/365`) | `[−1,000, 300, 400, 500]` at 8% → 17.63 |
| IRR / XIRR | root of NPV = 0; may not exist or may not be unique (11.1, [methods-performance-risk §5.3](methods-performance-risk.md)) | |

Compounding conventions:
- Periodic rate from a nominal annual rate `APR` compounded `m` times a year: `APR/m`.
- Effective annual rate `EAR = (1 + APR/m)^m − 1`; continuous compounding gives `e^{APR} − 1`. For 6% monthly,
  EAR = 6.1678%; continuous, 6.1837%.
- If payments and compounding differ in frequency, convert through EAR: `r_p = (1 + EAR)^{1/p} − 1`. For
  example, 6% compounded semiannually gives a monthly payment rate of 0.49386%, which some jurisdictions use
  for mortgages. The user's loan note sets the convention.

**Acceptance:** the examples above reproduce; the annuity-due value equals the ordinary value × `(1 + r)`; the
growing-annuity formula at `g = 0` equals the ordinary annuity.

### 13.2 Household intake schema

Collect only what the requested outputs need. Every field carries a unit and a frequency. Normalize
frequencies to monthly: annual ÷ 12, weekly × 52/12, biweekly × 26/12. A missing field makes the dependent
metric **unavailable**; it is never set to zero.

| Group | Fields (unit, frequency) | Notes |
|---|---|---|
| Household | members and ages (years), dependents (count), reporting currency, jurisdiction (only if tax or loan rules are used) | no names or identifiers needed |
| Income | gross and net income per earner (currency/month), variability class (stable salary / variable / self-employed), other income (pension, rental, benefits) | net = after tax and payroll deductions; state which one each ratio uses |
| Spending | essential (housing, utilities, food, insurance, minimum debt payments, transport), discretionary, irregular annual items (currency/month or /year) | essential vs discretionary is the user's split |
| Debts | type, balance, APR, minimum payment, remaining term, fixed or variable (index, margin, caps), secured flag, housing flag | housing debt feeds front-end DTI |
| Assets | cash and deposits; brokerage holdings as symbol + exchange + quantity (priced through EODHD); retirement accounts by tax type; property, vehicles and business interests as user value + valuation date + source | holdings resolve through [identity](identity.md) |
| Protection | cover type, amount, premium, need estimate (user) | used for coverage ratios only |
| Goals | as in section 4 | |
| Constraints | liquidity needs, risk tolerance (user statement), restrictions | |

Output an input-completeness table (field → present, missing, assumed) at the top of every report.

### 13.3 Household dashboard metrics and composite score

| Metric | Formula | Common heuristic (label as such) |
|---|---|---|
| Savings rate | `(employee + employer contributions + other saving) / gross income` (or `/ net`; 3.2) | ≥ 15–20% of gross for retirement saving |
| Front-end DTI | housing payment (principal, interest, property tax, insurance, association fees, as the user includes them) / gross monthly income | ≤ 28% |
| Back-end DTI | all recurring debt payments incl. housing / gross monthly income | ≤ 36% (lender rules vary) |
| Emergency months | liquid reserves / essential monthly spending; liquid = cash + deposits + money-market + bills (taxable investments only with a stated haircut) | 3–6 months (13.8) |
| Funded ratio | section 4 | ≥ 1 |
| Retirement on track | progress ratio from 11.5 for the retirement goal, or the simulated success rate (section 3) | user band |
| Insurance coverage ratio | existing cover / user-estimated need (per cover type) | ≥ 1 |
| Net worth, liquid net worth | 13.4 | — |

**Composite score (optional).**
1. Map each metric to 0–100 with a declared piecewise-linear rule: 0 at the "bad" breakpoint, 100 at the
   "good" one, clamped. For lower-is-better metrics such as DTI, the bad breakpoint is the higher value.
2. Apply the declared weights.
3. Renormalize over the metrics that are available, and show how many are missing.
4. Always print the component table (metric, value, breakpoints, score, weight) beside the composite. Never
   show a lone number.

Example (breakpoints and weights are illustrative):

| Metric | Value | Bad → good | Score | Weight |
|---|---|---|---|---|
| Savings rate | 12% | 0% → 20% | 60.0 | 0.25 |
| Back-end DTI | 30% | 50% → 20% | 66.7 | 0.25 |
| Emergency months | 6.0 | 0 → 6 | 100.0 | 0.20 |
| Funded ratio | 0.80 | 0 → 1 | 80.0 | 0.20 |
| Insurance coverage | missing | 0 → 1 | — | 0.10 |

Composite = (0.25·60 + 0.25·66.7 + 0.20·100 + 0.20·80) / 0.90 = **75.2** (4 of 5 components).

**Report section order:**
1. Header (as-of date, currency, input completeness).
2. Snapshot metrics.
3. Net-worth statement.
4. Cash flow and budget.
5. Debt.
6. Emergency reserve.
7. Investments (allocation, weighted expense ratio, 6.2).
8. Retirement and goals (11.5).
9. Protection.
10. Composite score with components.
11. Levers and a 90-day action list. These are proposals the user decides on.
12. Assumptions and data notes.

**Acceptance:** gross income 10,000/month, housing payment 2,200 and other debt payments 800 give front-end
DTI 22.0% and back-end DTI 30.0%. Liquid reserves 24,000 with essential spending 4,000 give 6.0 months. The
composite example above reproduces 75.2, and adding the missing insurance metric changes the
denominator to 1.00.

### 13.4 Net-worth statement

| Line | Valuation | Source flag |
|---|---|---|
| Listed securities | qty × raw close on the statement date × FX (GBX/ZAC ÷ 100) | EODHD close + date |
| Cash, deposits | balance | user statement + date |
| Retirement accounts | holdings priced as above, or statement value | EODHD / user |
| Unpriced and held-away items (11.6) | statement value | user + date, flagged |
| Property, vehicles, business interests | user value with method and date; the BIS country index (13.9) is regional context, not an appraisal | user |
| Liabilities | outstanding balances on the statement date | user |

- Net worth = total assets − total liabilities.
- Liquid net worth = (cash + taxable securities) − short-term liabilities.
- Investable assets = liquid investments + retirement accounts (excluding home and personal-use assets).

State the definitions, because conventions differ.

- **History:** store dated snapshots, one row per date and line, with source flags. Decompose the change
  between snapshots as ΔNW = net saving (income − spending) + market change on priced lines (from EODHD
  closes) + revaluation of user-valued lines − change in liabilities not explained by payments, plus a
  residual. Show the residual; do not hide it.
- **Projection:** use the section 3 engine on investable assets, with contributions from the budget and
  debt amortization from 13.6. Show milestones (for example 1×, 5× or 10× annual spending) as the dates on
  which percentile paths cross them.
- **Peer or age benchmarks** ("net worth for your age") are not EODHD data. Use them only if the user supplies
  a source.

**Acceptance:** lines sum to the totals; every priced line carries its close date; a close older than the
statement date is flagged as stale; the ΔNW decomposition plus residual equals the change in net worth.

### 13.5 Budget categorization and rule-of-thumb frameworks

**Categorization rules** (for user transaction exports):
1. Apply an ordered rule table. Each rule is (priority, field, pattern, category, essential flag); the first
   match wins. Unmatched rows go to an "uncategorized" queue for the user; do not let a model guess them
   silently.
2. **Transfers between the user's own accounts** are matched (same amount, opposite sign, within ±3 days) and
   excluded from income and spending. Card payments are transfers; the card purchases are the spending.
3. Refunds net against their original category. Irregular annual items become monthly sinking-fund lines
   (annual ÷ 12).
4. Report coverage: the share of outflows categorized, and the size of the uncategorized queue.

**Frameworks** (all heuristics; the user picks one):

| Framework | Rule | Check |
|---|---|---|
| 50/30/20 | needs 50%, wants 30%, saving and extra debt payments 20% of **net** income | actual shares vs the targets |
| Zero-based | income − Σ category allocations = 0 each month | the residual is exactly 0 |
| Envelope | a cap per category; overspending must be covered by moving money from another envelope | no envelope negative at month end |

12-month budget: rows are categories and columns are months, including seasonal and annual items. Variance
= actual − budget, with year-to-date totals. The cash-flow tie from 13.6 must hold every month.

**Acceptance:** a matched transfer pair changes neither income nor spending; zero-based allocations leave a
residual of 0; in the 50/30/20 check the three shares sum to 100% of net income (plus a printed "unallocated"
line if not).

### 13.6 Debt payoff, refinance and prepay-vs-invest

| Item | Formula |
|---|---|
| Level payment | `PMT = P · r / (1 − (1 + r)^(−n))`, periodic rate `r` (APR/12 for monthly); 200,000 at 6%/12, 360 months → 1,199.10 |
| Months to payoff | `n = −ln(1 − P·r/PMT) / ln(1 + r)`; undefined if `PMT ≤ P·r` (never amortizes) |
| Remaining balance after `k` payments | `P(1 + r)^k − PMT · ((1 + r)^k − 1)/r` |
| Total interest | `Σ_k interest_k` from the schedule (level loan: `n·PMT − P`, with the final payment adjusted) |
| Effective annual rate | `(1 + APR/m)^m − 1` |
| Avalanche / snowball | pay minimums on all debts, direct surplus to highest rate (avalanche) or smallest balance (snowball); when a debt clears, roll its payment to the next |
| Cash-flow tie | opening cash + inflows − outflows = closing cash; transfers between own accounts net to zero |

**Payoff schedule output.** Produce a month-by-month table per debt (payment, interest, principal, balance),
plus the payoff month per debt, the total months and the **total interest**. Run avalanche and snowball on
the same budget and show both.

Example: card 5,000 at 22% (minimum 150), car 12,000 at 7% (minimum 300), store card 1,500 at 15% (minimum
50), budget 900/month. Both orders finish in 23 months. Total interest is 1,772.49 for avalanche and
1,854.64 for snowball.

**Refinance or consolidation.**
1. New payment `PMT_new` from the new rate, term and amount. Roll the costs into the balance only if the
   user says so.
2. Monthly saving `ΔPMT = PMT_old − PMT_new`; simple breakeven months = costs / `ΔPMT`.
3. Compare the **total cost** over the user's horizon `H`: Σ payments + upfront costs + remaining balance at
   `H`. Compare the totals over the full remaining terms too. Optionally discount at the user's rate.
4. Flag term extension: a lower payment can still cost more interest.

Example: 200,000 balance with 300 months left at 7% (payment 1,413.56), refinanced to 6% over 300 months
with 4,000 of costs. The payment is 1,288.60, a saving of 124.96/month; simple breakeven is 32.0 months.
Total interest falls from 224,067.52 to 190,580.84, costs included. Refinancing to 6% over **360** months
gives a payment of 1,199.10 but 231,676.38 of interest, more than staying.

**Prepay vs invest.** Use the two-scenario engine (13.9) with the same monthly budget.
- Scenario A pays an extra `E` into the mortgage. After payoff, it invests the full former payment plus `E`.
- Scenario B invests `E` every month.
- Net worth at `H` = portfolio − remaining mortgage balance.

Prepaying earns a certain after-tax return of `r_m·(1 − τ·d)`, where `d` is the deductible share of interest
and `τ` the marginal rate (both user inputs). Investing earns an uncertain return. Run B on historical
rolling and bootstrap paths of the user's allocation (section 3.4, monthly panel, after a user tax drag,
13.13). Report P(B ahead at `H`), the median and the 10th-percentile difference, and the liquidity
difference: prepaid principal cannot be withdrawn. Present it as a trade-off, not a recommendation.

**Acceptance:**
- Each amortization schedule ends at 0 within rounding, and avalanche total interest ≤ snowball for the same
  budget.
- In prepay vs invest with the portfolio return equal to the mortgage rate and no taxes, the net-worth
  difference is 0 at every horizon (verified at 60, 240 and 360 months with 200,000 at 6%, `E = 300`).
- At an 8% portfolio return the difference (prepay − invest) is −1,112.05 at 60 months and −103,850.62 at
  360 months. The prepaid loan ends in month 221.

### 13.7 Lending: extra payments, points, 15 vs 30 years, ARM paths

**Use when:** comparing mortgage or loan structures. The loan note (rate, index, margin, caps, floor,
rounding, lookback, fees and points) is a user input.

**EODHD inputs (index context only):**
- `SOFR30D` or `SOFR` from `/api/rates/reference-rates` (percent, daily);
- the 1-year Treasury par yield from `/api/ust/yield-rates` (tenor `1Y`).

The loan's actual index value on each reset date, with its lookback, comes from the lender. Use these
series to build scenarios:
- **flat:** the index stays at its current level;
- **shock:** the index moves ±200 bp;
- **historical replay:** apply the index changes from a chosen past window to the current level.

Label each one as a scenario.

**Method**
1. **Extra payments:** run the schedule with additional principal `e` each month. Report months saved and
   interest saved.
2. **Points:** cost = points × loan amount.
   - Simple breakeven = cost / monthly payment saving.
   - Horizon breakeven: the first month `H` at which (payment saving × `H` + balance difference at `H`) ≥ cost.
     The lower-rate loan also amortizes faster, so this comes earlier. It is the relevant number for a user
     who may sell or refinance.
3. **15 vs 30 years:** payment, total interest, and balance after the user's horizon. Optionally add the
   invested payment difference (13.9).
4. **ARM:** after the fixed period, each reset sets the rate to round(index + margin). The rate is limited to
   the initial cap on the first reset and the periodic cap afterwards (both relative to the previous rate),
   to the lifetime cap above the start rate, and to the floor. The payment is recast over the remaining term
   at each reset.

```python
def level_payment(P, r, n):
    return P / n if r == 0 else P * r / (1 - (1 + r) ** -n)

def amortize(P, n, annual_rates, extra=0.0):
    """Monthly schedule. annual_rates: list of len n with the note rate (decimal) for each month;
    the payment is recast whenever the rate changes (ARM) over the remaining term.
    extra: additional principal per month. Returns rows (month, rate, payment, interest, principal, balance)."""
    rows, bal, pay, prev = [], float(P), None, None
    for k in range(n):
        if bal <= 1e-9:
            break
        r = annual_rates[k] / 12
        if annual_rates[k] != prev:
            pay, prev = level_payment(bal, r, n - k), annual_rates[k]
        it = bal * r
        total = min(pay + extra, bal + it)
        bal = bal + it - total
        rows.append((k + 1, annual_rates[k], total, it, total - it, max(bal, 0.0)))
    return rows

def arm_rate_path(start, fixed_months, reset_months, n, index_at_resets, margin,
                  initial_cap, periodic_cap, lifetime_cap, floor=None, rounding=0.00125):
    """Note-rate path for a hybrid ARM. index_at_resets: index level (decimal) at each reset;
    the last value is held. Rate = round(index + margin) clamped by the caps and the floor."""
    floor = margin if floor is None else floor
    rates, rate, j = [], start, 0
    for k in range(n):
        if k >= fixed_months and (k - fixed_months) % reset_months == 0:
            idx = index_at_resets[min(j, len(index_at_resets) - 1)]
            target = round((idx + margin) / rounding) * rounding
            cap = initial_cap if j == 0 else periodic_cap
            rate = min(max(target, rate - cap, floor), rate + cap, start + lifetime_cap)
            j += 1
        rates.append(rate)
    return rates
```

**Pitfalls:**
- Comparing a fixed-rate payment with the ARM's start payment only.
- Ignoring the floor.
- Using a daily overnight rate where the note specifies a 30-day average or a term rate.
- Treating the EODHD index series as the lender's determination.
- Points breakeven that ignores the balance effect, or the chance of selling early.

**Acceptance**
- 200,000 at 6% over 360 months: interest 231,676.38. With +200/month extra: 252 months and 151,875.87 of
  interest (108 months and 79,800.51 saved).
- Points: 300,000 at 6.50% vs 6.25% with 1 point (3,000). Payments 1,896.20 vs 1,847.15 (saving 49.05).
  Simple breakeven is 61.2 months; including the balance effect it is 48 months. The net advantage is
  −743.33 at 36 months and +4,501.54 at 120 months (undiscounted).
- 15 vs 30 years on 300,000: 15 years at 5.5% costs 2,451.25/month and 141,225.07 of interest; 30 years at 6%
  costs 1,798.65/month and 347,514.57 of interest.
- A 5/1 ARM of 400,000 over 30 years, start 5.5%, margin 2.75%, caps 2/2/5, floor = margin, with the index at
  4.5%, 6.0% and then 1.0% (held). Rates by year 6–10: 7.25%, 8.75%, 6.75%, 4.75%, 3.75%. Payments: 2,271.16
  (years 1–5), 2,673.25, 3,031.09, 2,569.93, 2,157.47, 1,972.34. A shock index of 6.5% held gives 7.5% (initial
  cap), then 9.25% from year 7.
- An index path with index + margin = start rate leaves the payment unchanged at every reset.

### 13.8 Emergency-fund sizing

**Method**
1. Months target `M`. Use a user-declared tier table; the default heuristic, labelled:
   - stable salary with two earners: 3 months;
   - one earner, or dependents: 6 months;
   - variable, commission or self-employed income: 9–12 months.

   The user may add adjustments (health, job-market, single-asset household).
2. Target = `M × essential monthly spending − M × reliable replacement income per month` (user-supplied, for
   example insurance benefits). Do not reduce the target for income the user cannot rely on.
3. Holding tiers (13.12):
   - instant-access cash for about one month;
   - bills or money-market funds for the rest;
   - optionally a short ladder for the slow tier.
4. Opportunity cost per year = balance × (expected portfolio return − cash yield). Take the cash yield from
   the 13-week bill `coupon` (`/api/ust/bill-rates`, percent ÷ 100) or the user's account rate, and the
   expected return from the CMA (section 5), before tax. Label it: it ignores the forced-sale risk that the
   reserve avoids.
5. Replenishment months: with balance `B`, target `T`, monthly saving `c` and monthly yield `i`,
   `n = ln((T·i + c)/(B·i + c)) / ln(1 + i)` (`(T − B)/c` when `i = 0`). Show a month-by-month refill table.

**Acceptance:** essential spending 4,000 and `M = 6` → target 24,000. Opportunity cost at 6% expected vs 4% cash
is 480 per year. Refill from 6,000 at 1,000/month and 4%/12 takes 17.18 → 18 months. With `i = 0` it takes
exactly 18.

### 13.9 Two-scenario engine (rent vs buy and other life choices)

**Use when:** comparing two choices over a shared horizon: rent vs buy, prepay vs invest (13.6), 15 vs 30
years, lease vs buy a car, two job offers. Each scenario is a monthly cash-flow ledger plus a terminal
non-portfolio net worth.

**Method**
1. Both scenarios start with the same cash and face the same monthly budget, `max(outflow_A, outflow_B)`.
   Whatever a scenario does not spend is invested in the same portfolio, so the comparison includes
   opportunity cost.
2. Portfolio return paths come from EODHD (section 2 panel, monthly): deterministic CMA, historical
   rolling windows and block bootstrap, in nominal terms with an inflation path. Report in real terms.
3. Terminal net worth = portfolio + scenario assets after selling costs − remaining debts. Taxes on the sale
   or the portfolio are user rules.
4. **Break-even solve:** bisection on one variable (home appreciation, rent growth, investment return,
   horizon) for `NW_A − NW_B = 0`.
5. **Sensitivity grid:** two variables (for example home appreciation × investment return); each cell is a
   full recompute.
6. Context for home appreciation: the country's BIS real or nominal index (`/api/real-estate/{CC}`,
   `filter[type]=real|nominal`, `filter[metric]=yoy|index`, quarterly). Use its historical range of annual
   changes to choose sensible grid bounds. It is a national index, not a forecast of the user's home.

The block below uses `level_payment` from 13.7.

```python
def two_scenarios(out_a, out_b, init_a, init_b, end_nw_a, end_nw_b, r_month):
    """Generic two-scenario comparison on one cash budget.
    out_a/out_b: monthly cash outflows (len H). init_a/init_b: cash needed at t0.
    end_nw_a/end_nw_b: terminal non-portfolio net worth (e.g. home value after selling costs minus loan).
    r_month: monthly portfolio returns (len H), e.g. a path built from the section 2 panel.
    Both start with the same cash K = max(init_a, init_b); what a scenario does not spend is invested.
    Each month the budget is max(out_a, out_b); the cheaper scenario invests the difference at month end."""
    K = max(init_a, init_b)
    pa, pb = K - init_a, K - init_b
    for t, r in enumerate(r_month):
        budget = max(out_a[t], out_b[t])
        pa = pa * (1 + r) + budget - out_a[t]
        pb = pb * (1 + r) + budget - out_b[t]
    return {"nw_a": pa + end_nw_a, "nw_b": pb + end_nw_b, "port_a": pa, "port_b": pb}

def rent_vs_buy(H_years, price, down, close_cost, rate, term_years, tax, ins, maint, sale_cost,
                g_home, rent0, g_rent, r_annual):
    H, n = 12 * H_years, 12 * term_years
    loan = price * (1 - down)
    pmt = level_payment(loan, rate / 12, n)
    bal, buy_out, rent_out = loan, [], []
    for t in range(H):
        value = price * (1 + g_home) ** (t / 12)
        bal = bal * (1 + rate / 12) - pmt
        buy_out.append(pmt + value * (tax + ins + maint) / 12)
        rent_out.append(rent0 * (1 + g_rent) ** (t // 12))
    end_value = price * (1 + g_home) ** H_years
    r_m = [(1 + r_annual) ** (1 / 12) - 1] * H
    res = two_scenarios(buy_out, rent_out, price * (down + close_cost), 0.0,
                        end_value * (1 - sale_cost) - bal, 0.0, r_m)
    res["buy_minus_rent"] = res["nw_a"] - res["nw_b"]
    return res

def breakeven(f, lo, hi, tol=1e-7):
    """Bisection for f(x) = 0 on [lo, hi]; None if f has no sign change there."""
    flo = f(lo)
    if flo * f(hi) > 0:
        return None
    while hi - lo > tol:
        mid = (lo + hi) / 2
        fm = f(mid)
        if fm * flo > 0:
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2
```

Swap `r_m` for a path from the section 2 panel (historical or bootstrap) to get the distribution of
outcomes, rather than a single deterministic number.

**Pitfalls:**
- Comparing the buyer's equity with zero for the renter (the renter's invested down payment is the point).
- Omitting selling costs.
- Mixing real home appreciation with nominal mortgage rates.
- Using a national index as the home's value.
- Leaving out property tax, insurance and maintenance.

**Acceptance**
- Base case: price 500,000, 20% down, 3% closing costs, 6.5% over 30 years, property tax 1.1%, insurance
  0.35%, maintenance 1% of value per year, 6% selling costs, home +3%/year, rent 2,300/month growing 3%/year,
  portfolio 6%/year, 10 years. Net worth: buy 292,536.19, rent 384,358.94, difference −91,822.74.
- Break-even home appreciation: 5.55% at 5 years, 4.62% at 10 years, 4.34% at 15 years.
- Grid (buy − rent, thousands; rows home appreciation 1/3/5%, columns portfolio return 3/6/9%):
  `[−111.3, −187.8, −284.1]`, `[−13.8, −91.8, −189.8]`, `[103.5, 23.7, −76.1]`.
- Identical scenarios give a difference of exactly 0. With zero returns, each portfolio equals its cumulative
  uninvested cash.

### 13.10 Rental property cash flow: NOI, cap rate, DSCR, levered IRR

**Use when:** analysing a buy-to-let or small multifamily property from the user's rent roll and expenses.
For listed REITs use [methods-fundamentals-valuation §3.10](methods-fundamentals-valuation.md) instead.

**User inputs:** price, closing costs, initial repairs, gross scheduled rent, vacancy and credit loss,
operating expenses, loan terms, growth rates, holding period, exit cap rate and selling costs.
- Operating expenses: tax, insurance, management %, repairs, reserves.
- State whether replacement reserves are deducted above or below NOI.

Depreciation, passive-loss rules, cost segregation and exchange deferrals are jurisdiction rules supplied
by the user; they are not computed here. EODHD context: the BIS country index (13.9) and, for financing,
UST and reference rates.

| Quantity | Formula |
|---|---|
| Effective gross income | `EGI = GSI·(1 − vacancy) + other income` |
| NOI | `EGI − operating expenses` (excludes debt service, depreciation, income tax) |
| Cap rate | `NOI_1 / price` (or `/ value`) |
| Debt service | `DS = 12 · PMT` (13.6) |
| DSCR | `NOI / DS` (< 1: the property does not cover its debt) |
| Cash flow before tax | `CFBT = NOI − DS` (− below-the-line reserves) |
| Cash-on-cash | `CFBT_1 / equity invested` (down payment + closing + initial repairs) |
| Break-even occupancy | `(OpEx + DS) / GSI` (treats OpEx as fixed; state it) |
| Levered IRR | IRR of `[−equity, CFBT_1, …, CFBT_H + net sale]`, with net sale = `NOI_{H+1}/exit cap × (1 − selling costs) − loan balance_H` |
| Unlevered IRR | same with `−(price + closing)`, NOI flows and no loan |

**Acceptance:**
- Inputs: price 400,000, closing 8,000, 25% down, loan 300,000 at 7% over 30 years. Rent 3,200/month, 5%
  vacancy. Fixed expenses 10,000/year (tax 4,800, insurance 1,600, repairs 2,400, reserves 1,200) plus 8%
  management on EGI. Rent and expenses grow 3%/year; exit cap 6%; selling costs 6%; 5-year hold.
- Year-1 results: EGI 36,480; OpEx 12,918.40; NOI 23,561.60. Cap rate 5.89%, DS 23,950.89, DSCR 0.98 (flag),
  CFBT −389.29, cash-on-cash −0.36%, break-even occupancy 96.0%.
- Exit: loan balance after 5 years 282,394.77; NOI in year 6 is 27,314.35, so the sale price is 455,239.20
  and the net sale proceeds 145,530.08.
- Levered IRR 6.95% and unlevered IRR 6.96%. Leverage adds nothing when the unlevered return is about the
  7% borrowing cost. Positive leverage needs an unlevered return above the cost of debt.

### 13.11 Concentrated stock position

**Use when:** a household holds a large single-stock position (employer stock, vested equity awards, an
inheritance) and asks how risky it is and what staged diversification would do. Grant terms, vesting,
exercise and tax treatment are user inputs. Hedging costs are in
[methods-options-rates-macro A13](methods-options-rates-macro.md).

**EODHD inputs:** EOD `adjusted_close` of the stock and of a diversified proxy (a TR index or a broad ETF), 1
call each for full history. Use delisted peers from the exchange symbol list with `delisted=1` for a
survivorship check.

**Method**
1. **Risk comparison**, stock vs proxy on common dates:
   - annualized volatility, maximum drawdown and its recovery time, worst 12-month return;
   - beta, and idiosyncratic volatility `√(σ_s² − β²σ_m²)`.
2. **Probability of a decline of at least X% over horizon h.**
   - Historical: the share of overlapping h-windows with a return ≤ −X. The windows overlap, so do not
     attach a binomial interval.
   - Bootstrap: a joint block bootstrap of monthly returns. Report both the end-of-horizon probability and
     the probability of touching −X at some point.
   - A single survivor's own history understates failure risk. Add the cross-section of peers, including
     delisted ones, labelled.
3. **Staged-sale simulation:** a schedule sells fraction `q_k` of the original position at month `k`. Tax at
   the user's rate is due on the gain over the basis relieved, and after-tax proceeds go into the proxy.
   Compare hold, sell now and staged schedules on the same joint bootstrap paths, which keeps the
   stock–proxy correlation. Show median, 10th and 90th percentile terminal wealth and P(terminal < floor).

```python
import numpy as np

def staged_sale_sim(stock_r, index_r, sell_fracs, basis_frac, tax_rate, horizon, block, n_paths, seed=0):
    """stock_r, index_r: aligned monthly total returns (adjusted_close) over the same dates.
    sell_fracs: share of the ORIGINAL position sold at the end of month k (dict k -> fraction).
    basis_frac: cost basis / initial value (average basis, user lots in practice).
    Gains tax = tax_rate * (proceeds - basis relieved); after-tax proceeds go into the index.
    Joint circular block bootstrap keeps the stock-index correlation. Returns terminal wealth per path
    (start value 1)."""
    rng = np.random.default_rng(seed)
    X = np.column_stack([stock_r, index_r])
    T = len(X)
    out = np.empty(n_paths)
    for p in range(n_paths):
        idx = []
        while len(idx) < horizon:
            u = int(rng.integers(T))
            idx.extend((u + j) % T for j in range(block))
        path = X[idx[:horizon]]
        shares_val, div_val, sold = 1.0, 0.0, 0.0
        for k in range(horizon):
            shares_val *= 1 + path[k, 0]
            div_val *= 1 + path[k, 1]
            q = sell_fracs.get(k + 1, 0.0)
            if q > 0:
                remaining = 1.0 - sold
                frac_of_holding = q / remaining
                proceeds = shares_val * frac_of_holding
                gain = proceeds - basis_frac * q
                div_val += proceeds - tax_rate * max(gain, 0.0)  # losses: no tax credit modelled
                shares_val -= proceeds
                sold += q
        out[p] = shares_val + div_val
    return out
```

**Pitfalls:** treating the stock's past drift as its expected return (the bootstrap carries it, so also run
a version with the stock's mean set equal to the proxy's, labelled); ignoring taxes on diversification;
ignoring blackout windows and trading restrictions (user input); a single path presented as the outcome.

**Acceptance:**
- **Fixture:** 240 synthetic months, seed 42. The market draws are normal with mean 0.7% and sd 4.5%; the
  stock is 1.2 × market plus normal(0.2%, 8%) noise. Annualized volatility: stock 31.4%, proxy 14.0%.
- **Historical 12-month decline probability:** P(return ≤ −30%) is 8.3% for the stock and 0.0% for the
  proxy, over 229 windows.
- **Bootstrap:** 60 months, block 12, 4,000 paths, seed 7, basis 20% of value, tax 20%. Terminal wealth:

  | Plan | Median | 10th–90th percentile | P(< 0.7) |
  |---|---|---|---|
  | Hold | 1.433 | 0.582–3.357 | 15.3% |
  | Sell now | 1.079 | 0.732–1.531 | 7.6% |
  | 8 quarterly sales of 12.5% | 1.126 | 0.676–1.769 | 11.7% |

- **Invariants:** with identical stock and proxy series and zero tax, all three plans give the same terminal
  wealth on every path. Hold is unaffected by the tax rate.

### 13.12 Liquidity tiers and ladders

| Tier | Purpose | Instruments | Rate source |
|---|---|---|---|
| T0 operating | 1–2 months of spending | current account, savings | user's account rate |
| T1 reserve | the rest of the emergency fund (13.8) | bills, money-market funds | `/api/ust/bill-rates` `coupon` (4WK…52WK), percent |
| T2 known needs, 1–5 years | dated liabilities (tuition, a car, a deposit) | Treasury ladder ([methods-options-rates-macro B7](methods-options-rates-macro.md)), CDs | UST par curve; **CD rates, terms and penalties are user-supplied** (EODHD has no bank-deposit rates) |
| T3 long-term | everything else | portfolio (section 3) | section 2 panel |

**Method**
1. Assign every dated liability to the tier whose horizon covers it; fund tiers in order T0 → T3.
2. **Blended ladder yield:** the exact figure is the IRR of the ladder's combined cash flows (cost at `t = 0`,
   rung cash flows after that). The cost-weighted average yield is an approximation that is biased when rung
   durations differ. Weighting by cost × duration comes close to the IRR. Report the IRR.
3. **Reinvestment rule:** a maturing rung either funds its liability or is rolled to the longest rung at the
   curve yield of the roll date. Record the source date, so the ladder's length stays constant.
4. **Comparing rates:** bill `coupon` is a bond-equivalent yield; deposit rates are usually quoted as an annual
   effective yield (APY). Convert with `APY = (1 + BEY/2)^2 − 1`; 4.00% BEY ≈ 4.04% APY. State the
   conversion; taxes differ by instrument and are user rules.

**Acceptance:** three zero-coupon rungs of 10,000 face at years 1, 2 and 3 with yields of 4.0%, 3.8% and 3.7%.
The cost is 27,863.95 and the ladder IRR is 3.786%. The face-weighted average is 3.833% and the cost-weighted
average 3.837%, both off. The cost × duration-weighted figure is 3.786%. Every liability maps to exactly one
tier.

### 13.13 After-tax growth and asset location

Here `r` is the pre-tax annual return, `n` the number of years, `τ` the tax rate on income taxed each year,
`τ_cg` the tax rate on realized gains and `τ_w` the tax rate on withdrawals. All rates and account rules are
user inputs, never defaults.

| Account / treatment | After-tax value of 1 invested |
|---|---|
| Taxable, all return taxed yearly | `(1 + r(1 − τ))^n` |
| Taxable, pure deferred gain realized at the end | `(1 + r)^n(1 − τ_cg) + τ_cg` |
| Taxable, mixed (income yield `y` taxed yearly at `τ_inc`, price growth `g` taxed at the end) | simulate yearly: reinvest after-tax income, track basis, and tax the gain at the end |
| Tax-deferred (pre-tax contribution, withdrawals taxed at `τ_w`) | `(1 + r)^n(1 − τ_w)` per unit of **pre-tax** money |
| Tax-exempt (after-tax contribution) | `(1 + r)^n` |

Tax drag (annualized) = `r − [(after-tax value)^(1/n) − 1]`.

**Asset location ranking**
1. For each asset class, take the income yield from EODHD: trailing 12-month `unadjustedValue` sum from
   `/api/div` divided by price, or `ETF_Data::Yield` (percent). Take the expected price growth from the CMA,
   and the income tax class from the user (ordinary, qualified, interest).
2. Compute each asset's tax drag if held in a taxable account.
3. Fill the tax-advantaged capacity with the highest-drag assets first, subject to the target allocation.
   Compare after-tax values, remembering that deferred accounts hold pre-tax money.
4. The result is a heuristic ranking. Withdrawal sequencing, contribution limits and the account rules
   come from the user.

**Acceptance:**
- `r = 7%`, `n = 20`, `τ = 30%`, `τ_cg = 20%`. Taxable-yearly 2.6032 (drag 210 bp); deferred gain 3.2957 (drag
  86 bp); exempt 3.8697 (drag 0); tax-deferred 2.7088 per pre-tax unit.
- Illustrative 20-year ranking with `τ_cg = 15%`. Drags: REIT fund (yield 4%, growth 3%, income taxed at 37%)
  177 bp; bond fund (4.5%, 0%, 37%) 166 bp; international equity (3%, 4%, 15%) 81 bp; US equity index (1.5%,
  5.5%, 15%) 72 bp. Locate the REIT and bond funds first.

---

## 14. Private-fund metrics and public-market equivalents (PME)

**Use when:** an investor in private equity, venture or private credit funds wants multiples and a
comparison with a listed index. The capital calls, distributions and reported NAVs are **user data** from
capital-account statements. EODHD has no private-fund data.

**EODHD inputs:** a total-return index or ETF in the investor's currency: `SPXTR.INDX` or another TR code
from 2.1, or ETF `adjusted_close`, with `*.FOREX` conversion if needed. One EOD call gives the full history.
On each cash-flow date, use the close of the last session on or before that date. A price index understates
the benchmark by its dividend yield, so it is never acceptable here.

**Method** (`C_t` calls, `D_t` distributions, `NAV_T` at the valuation date `T`, `I_t` the index level):

| Metric | Formula |
|---|---|
| DPI | `Σ D_t / Σ C_t` (realized) |
| RVPI | `NAV_T / Σ C_t` (unrealized) |
| TVPI | `DPI + RVPI` |
| IRR | XIRR of `−C_t`, `+D_t` and `+NAV_T` at `T` (actual/365) |
| Kaplan–Schoar PME | `[Σ D_t·(I_T/I_t) + NAV_T] / Σ C_t·(I_T/I_t)`; above 1 means the fund beat the index |
| Long–Nickels PME | an index portfolio receives the same calls and pays the same distributions, giving terminal value `NAV_LN = Σ C_t·I_T/I_t − Σ D_t·I_T/I_t`; the LN-PME is the IRR of `−C_t`, `+D_t` and `+NAV_LN`, compared with the fund IRR. If `NAV_LN ≤ 0` (large distributions), LN is undefined: report it as such and rely on KS |

```python
from datetime import date

def xirr(flows):
    """flows: list of (date, amount). Actual/365. Bisection on [-0.99, 10]."""
    t0 = flows[0][0]
    f = lambda r: sum(a / (1 + r) ** ((d - t0).days / 365) for d, a in flows)
    lo, hi = -0.99, 10.0
    flo = f(lo)
    if flo * f(hi) > 0:
        return None
    while hi - lo > 1e-10:
        mid = (lo + hi) / 2
        fm = f(mid)
        if fm * flo > 0:
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2

def private_fund_metrics(calls, dists, nav, nav_date, index_level):
    """calls, dists: lists of (date, amount > 0) from the LP's statements (user data).
    nav: reported NAV at nav_date. index_level: callable date -> TR index level on that date
    (EODHD close of the last session <= date, in the LP's currency)."""
    C, D = sum(a for _, a in calls), sum(a for _, a in dists)
    I_T = index_level(nav_date)
    fv = lambda flows: sum(a * I_T / index_level(d) for d, a in flows)
    ks = (fv(dists) + nav) / fv(calls)
    ln_nav = fv(calls) - fv(dists)                       # index portfolio fed by the same flows
    flows = sorted([(d, -a) for d, a in calls] + [(d, a) for d, a in dists])
    return {"paid_in": C, "distributed": D, "DPI": D / C, "RVPI": nav / C, "TVPI": (D + nav) / C,
            "IRR": xirr(flows + [(nav_date, nav)]), "KS_PME": ks,
            "LN_PME_IRR": xirr(flows + [(nav_date, ln_nav)]) if ln_nav > 0 else None,
            "LN_NAV": ln_nav}
```

**Pitfalls:**
- Reported NAV is an appraisal that lags and is smoothed, so interim multiples and PMEs are estimates.
- Fees and carry are inside the LP's cash flows; do not deduct them again.
- Recallable distributions and unfunded commitments come from the documents.
- Matching the benchmark's currency to the LP's currency matters.
- A short track record makes the IRR unstable, and it may have no root.
- Interpret the J-curve (negative early IRR) as timing, not performance.
- Comparing the IRR with an index CAGR over a different window is not a PME.

**Acceptance**
- **Example:** calls 100 on 2018-03-15 and 50 on 2019-06-14; distributions 60 on 2021-09-15 and 90 on
  2023-03-15; NAV 80 on 2024-12-31. TR index levels on those dates: 1,000, 1,100, 1,400, 1,300, 1,600.
- **Results:** DPI 1.000, RVPI 0.533, TVPI 1.533, IRR 9.39%, KS-PME 1.114, LN terminal value 53.39, LN-PME IRR
  6.88%. The fund beat the index.
- **Tracker check:** a fund whose distributions and NAV exactly track the index (call 100 on 2018-03-15;
  distribute half the index-grown value on 2021-09-15; NAV equal to the other half grown to 2024-12-31) gives
  KS-PME = 1.000000 and LN-PME IRR = fund IRR = 8.178%.
- **Undefined case:** when the distributions exceed the index-grown calls, LN reports undefined, not a number.

---

## 15. Boundaries

- EODHD has no historical index dividend-yield series; pre-TR-index equity history needs a user-supplied or
  labelled yield assumption. TR index start dates are approximate — probe the first and last date per symbol.
- `macro-indicator` CPI is annual (no monthly CPI); the latest years can lag; values are percent.
- No household, brokerage, custody, tax-authority or billing data; no tax rules, wash-sale rulings, fee
  contracts or fund equalization terms. These come from the user.
- "Substantially identical" or equivalent-security status is a user/adviser judgement; overlap and
  correlation are evidence only.
- Intraday bars are not a trade tape; MAE/MFE are bar-resolution estimates. No order-book or fill-quality data.
- Simulated success rates depend on the chosen proxies, window, block length and rules; they are not
  probabilities of real-world outcomes. Label historical, bootstrap and deterministic results separately.
- Reports produced here are not certified (e.g. not GIPS-compliant by construction) and are not tax filings.
- Household inputs (incomes, spending, balances, insurance, loan notes, rent rolls, property values, grant
  terms, private-fund capital accounts) are user data. EODHD has no bank-deposit or CD rates, mortgage-rate
  surveys, property appraisals, local rents or occupancy, peer or age net-worth benchmarks, private-fund
  cash flows or NAVs.
- The BIS residential property series (`/api/real-estate/{CC}`) are country-level quarterly indices. They give
  context for appreciation ranges, not a home's value.
- Reference rates and UST yields are index context for ARMs. The lender's index value, lookback and rounding
  decide the actual rate.
- `ETF_Data` and `MutualFund_Data` fields (expense ratio, asset allocation) are current snapshots; there is no
  history of them. Fund expense-ratio units differ by field (section 1).
- Heuristic thresholds (DTI, emergency months, savings rate, 50/30/20) are labelled conventions the user can
  override; they are not lending or regulatory rules.
