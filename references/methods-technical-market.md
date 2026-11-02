# Methods: technical indicators, market health, setups and screens

Exact, testable definitions for price-based analytics built on EODHD data: indicator formulas with warm-up
and price basis, when to call the Technical API versus computing locally, support/resistance levels,
membership-aware market breadth and timing (distribution and follow-through days), regime and posture
scores, named swing setups with trade plans, earnings-reaction and drift scoring, natural-language Screener
mapping with result cleaning, dividend and value/GARP screens, a daily market recap, a single-stock
decision workflow, sector cycle phase and theme baskets, a daily movers scan, correction statistics,
detector aggregation, fear, bubble and crypto regime scores, and pre-publication checks. Every threshold below is a **declared default or heuristic**, not a validated edge; a
system must expose it as a parameter and show the values that made each candidate pass. Outputs are
research candidates and plans, never orders or advice. Read [data semantics](data-semantics.md) for price
bases and [screening](screening.md) for the general server-side vs local rules; this chapter adds the
methods.

## Contents

1. [Conventions used in this chapter](#1-conventions-used-in-this-chapter)
2. [Technical API or local computation](#2-technical-api-or-local-computation)
3. [Indicator definitions and warm-up](#3-indicator-definitions-and-warm-up)
4. [Weekly bars and multi-timeframe analysis](#4-weekly-bars-and-multi-timeframe-analysis)
5. [Support and resistance levels](#5-support-and-resistance-levels)
6. [Market health: breadth, highs/lows, uptrend ratio](#6-market-health-breadth-highslows-uptrend-ratio)
7. [Distribution days and the follow-through-day state machine](#7-distribution-days-and-the-follow-through-day-state-machine)
8. [Regime detection and a fail-safe posture score](#8-regime-detection-and-a-fail-safe-posture-score)
9. [Setup definitions](#9-setup-definitions)
10. [Trade plans: entry, stop, R targets, time exit, heat](#10-trade-plans-entry-stop-r-targets-time-exit-heat)
11. [Earnings reaction scoring and post-earnings drift](#11-earnings-reaction-scoring-and-post-earnings-drift)
12. [Screener: natural language to filters, and result cleaning](#12-screener-natural-language-to-filters-and-result-cleaning)
13. [Dividend screens and the dividend monitor](#13-dividend-screens-and-the-dividend-monitor)
14. [GARP, value and quality screens](#14-garp-value-and-quality-screens)
15. [Market overview / daily recap recipe](#15-market-overview--daily-recap-recipe)
16. [Single-stock decision workflow](#16-single-stock-decision-workflow)
17. [Sector cycle phase and rotation](#17-sector-cycle-phase-and-rotation)
18. [Theme baskets: detection, heat and lifecycle](#18-theme-baskets-detection-heat-and-lifecycle)
19. [Daily big-movers and gap scan feeding the outcome ledger](#19-daily-big-movers-and-gap-scan-feeding-the-outcome-ledger)
20. [Correction duration and depth across stocks](#20-correction-duration-and-depth-across-stocks)
21. [Combining detectors, and a per-ticker fear score](#21-combining-detectors-and-a-per-ticker-fear-score)
22. [Bubble-risk score (heuristic)](#22-bubble-risk-score-heuristic)
23. [Crypto regime recipe and crypto fundamentals fields](#23-crypto-regime-recipe-and-crypto-fundamentals-fields)
24. [Pre-publication checks for market commentary](#24-pre-publication-checks-for-market-commentary)
25. [Boundaries: what EODHD does not supply here](#25-boundaries-what-eodhd-does-not-supply-here)

---

## 1. Conventions used in this chapter

**Price basis.** Pick one basis per purpose and record it with every output.

| Purpose | Basis | How to get it from EODHD |
|---|---|---|
| Returns, momentum, moving averages, RS, signals over long history | Total-return adjusted | `adjusted_close`; adjusted O/H/L = raw × (`adjusted_close`/`close`) per day ([data-semantics](data-semantics.md#price-basis)) |
| Range-based indicators (ATR, ADX, stochastic, Keltner, Donchian, candles) | Consistently adjusted OHLC (all four fields on one basis) | Adjusted OHLC as above, or split-only OHLC from Technical API `function=splitadjusted` (5 calls) |
| Executable levels shown to a user (pivot, entry, stop, targets) | Raw prices as traded now | `open/high/low/close`; for dates after the latest split/ex-date raw equals adjusted |
| Volume, dollar volume | Split-adjusted volume × split-adjusted price | EOD `volume` is split-adjusted; pair it with split-only or adjusted prices, never with raw prices across a split |
| Intraday (VWAP, opening range) | Raw intraday bars, one session at a time | `/api/intraday` is unadjusted; never mix a split day into a multi-day intraday calculation |

**Signal and fill timing.** A signal computed from a daily bar is known only after that bar is final
(US about 16:15 ET for a first version, refined for hours; see
[coverage-notes](coverage-notes.md#end-of-day-semantics)). Default: signal at close of day *t*, earliest
simulated fill at the open of *t+1*; a stop can gap through its level and fills at the open in that case.

**Missing data.** A missing bar or field is a gap, never a zero. A component that cannot be computed is
"not scored", not "failed"; composite scores re-normalize weights over scored components and report the
covered weight.

**Sessions, not calendar days.** All windows (`n`) count trading sessions of the instrument's exchange.
Crypto (`.CC`) trades every UTC day; forex has no volume.

**Notation.** `C_t, O_t, H_t, L_t, V_t` = close/open/high/low/volume of session *t*; `SMA_n`, `EMA_n` over
the last *n* sessions including *t*; `R` (in plans) = entry − stop per share.

---

## 2. Technical API or local computation

**Use when** deciding whether to call `GET /api/technical/{SYMBOL}?function=…` or compute from EOD bars.

**EODHD inputs.** Technical API: EOD+Intraday Extended or All-In-One, **5 calls per request** (one symbol,
one function). EOD history: 1 call per symbol, any plan with EOD (Free = 1 year). Endpoint reference:
[technical-indicators](api/endpoints/technical-indicators.md).

| Situation | Prefer | Reason |
|---|---|---|
| One latest value for a few symbols (dashboard tile, spreadsheet cell, alert) | API with `filter=last_<field>` | Single number, no code |
| Several indicators per symbol | Local from one EOD pull | 1 call instead of 5 per indicator |
| Universe scans (hundreds of symbols) | Local on bulk/EOD archive | 500 symbols × 3 indicators × 5 = 7,500 calls/day via API |
| ATR, ADX, stochastic, anything using highs/lows across a split | **Local on adjusted OHLC** | API uses unadjusted H/L/C (see probe below) |
| Historical volatility | Local | API `volatility` did not match a standard definition in a probe |
| Keltner, Donchian, OBV, VWAP, anchored VWAP, pivots, candles | Local | No API function |
| Split-only OHLC, weekly/monthly split-only bars | API `function=splitadjusted&agg_period=d|w|m` | Avoids building a split ledger |
| Beta versus an index or another symbol | API `function=beta&code2=…` or local | Local lets you state the return basis and window |

**What a 2026-10-25 probe established** (AAPL.US, NVDA.US, compared against local recomputation from EOD;
treat as observed behaviour, re-probe before depending on it):

- **Warm-up happens inside the requested window.** The API computes from the `from` date only. With
  `from=2025-10-13&to=2025-10-24&period=14` every function returned `[]` (HTTP 200); with
  `from=2025-08-01`, RSI(14) first appeared on the 15th session and Bollinger(20) on the 20th. Recursive
  indicators (EMA, RSI, ATR, ADX, MACD) therefore **change with `from`**: RSI(14) on 2025-10-24 was 64.80
  starting 2025-08-01 versus about 64.19 with history from mid-2024. Request `from` = first wanted date
  minus the warm-up in the table of section 3 (or omit `from`) and discard the warm-up rows. Cost is 5
  calls regardless of window length.
- **Conventions reproduced exactly** by the local code in section 3: EMA seeded with the SMA of the first
  *n* closes; RSI and ATR with Wilder smoothing seeded by an SMA; MACD with both EMAs starting on the bar
  where the slow EMA is first defined; Bollinger with **population** standard deviation (ddof = 0);
  stochastic 14/3/3 slow; ADX with smoothed sums seeded over the first *n*−1 values. These are the
  conventions of the widely used TA-Lib library.
- **Price basis differs by function.** `sma`, `ema`, `rsi`, `macd`, `bbands` used `adjusted_close` (split
  and dividend adjusted). `atr`, `adx`, `stochastic` used **unadjusted** high/low/close: NVDA ATR(5) jumped
  from 51.7 to 259.7 on the 2024-06-10 10:1 split session, and `splitadjusted_only=1` did not change it
  (that parameter is documented only for `sma, ema, wma, volatility, rsi, slope, macd`).
- **Field names in responses** were `macd`, `signal`, `divergence` (MACD); `uband`, `mband`, `lband`
  (Bollinger); `k_values`, `d_values` (stochastic); single-value functions use the function name (`rsi`,
  `atr`, `adx`, `sma`, …). The bundled endpoint page shows other names (`macd_signal`, `bbands_upper`,
  `stochastic_k`); parse keys from a live response, and fail loudly on an unknown shape.
- `volatility` with `period=20` returned values (54.4 → 14.6 → 26.5 over eight sessions) that matched no
  rolling standard deviation of daily simple or log returns at any window 2–20; treat its definition as
  undocumented and compute realized volatility locally ([portfolio-risk](portfolio-risk.md)).
- API defaults are 50 for most `period` parameters (RSI, ATR, ADX, Bollinger, CCI). Always pass `period`.

**Acceptance checks.**
- For one liquid symbol, fetch EOD from date *D*₀ and the API indicator with `from=D₀`; local values match to
  4 decimals for EMA/RSI/MACD/Bollinger (adjusted close) and ATR/ADX/stochastic (raw OHLC).
- A request window shorter than the warm-up returns no rows; the client reports "insufficient window", not
  "no data".
- The call budget printed by the job equals symbols × functions × 5 for API paths and symbols × 1 for local
  paths.

---

## 3. Indicator definitions and warm-up

**Use when** implementing or checking an indicator, or explaining a value to a user.

**EODHD inputs.** `/api/eod/{SYM}?fmt=json` (1 call; full history in one request): raw OHLC,
`adjusted_close`, split-adjusted `volume`. Intraday bars for VWAP: `/api/intraday` (5 calls per window).

| Indicator | Definition (session *t*) | Defaults | First value at bar | Warm-up for stable values |
|---|---|---|---|---|
| SMA | `mean(C_{t-n+1..t})` | n = 20/50/150/200 | n | n (exact after n) |
| EMA | `E_t = α·C_t + (1−α)·E_{t−1}`, `α = 2/(n+1)`, seed `E_{n} = SMA_n` | n = 10/20/50 | n | ≈3.5n (seed weight < 0.1%) |
| WMA | `Σ w_i C_{t−n+i} / Σ w_i`, `w_i = i` (1 = oldest) | n = 20 | n | n |
| Wilder smoothing (RMA) | `S_t = S_{t−1} + (x_t − S_{t−1})/n`, seed SMA of first n x | — | n | ≈7n (seed weight < 0.1%) |
| RSI (Wilder) | `Δ_t = C_t − C_{t−1}`; `G,L` = RMA_n of `max(Δ,0)`, `max(−Δ,0)`; `RSI = 100 − 100/(1+G/L)` | n = 14 | n+1 | ≈100 bars for n = 14 |
| MACD | `EMA_12 − EMA_26`; signal = EMA_9 of MACD; hist = MACD − signal | 12/26/9 | 26 (MACD), 34 (signal) | ≥ 100 bars |
| Bollinger | `mid = SMA_n`; `σ` = population sd of last n closes; `upper/lower = mid ± k·σ` | n = 20, k = 2 | n | n |
| %B | `(C − lower)/(upper − lower)`; 0 = lower band, 1 = upper | — | n | n |
| Bandwidth | `(upper − lower)/mid` (fraction) | — | n | n |
| True range | `max(H−L, |H−C_{t−1}|, |L−C_{t−1}|)` | — | 2 | — |
| ATR (Wilder) | RMA_n of TR | n = 14 | n+1 | ≈7n |
| +DI / −DI | `up = H_t−H_{t−1}`, `dn = L_{t−1}−L_t`; `+DM = up` if `up>dn and up>0` else 0 (mirror for −DM); `±DI = 100·smooth(±DM)/smooth(TR)` | n = 14 | n+1 | ≈10n |
| ADX | `DX = 100·|+DI − −DI|/(+DI + −DI)`; ADX = RMA_n of DX | n = 14 | 2n | ≈10n (double smoothing) |
| Stochastic (slow) | fast %K = `100·(C − LL_k)/(HH_k − LL_k)`; slow %K = SMA_3(fast %K); %D = SMA_3(slow %K) | 14/3/3 | k+4 | k+4 |
| OBV | `OBV_t = OBV_{t−1} + sign(C_t − C_{t−1})·V_t`, `OBV_0 = 0` | — | 1 | level is start-dependent; compare slopes |
| VWAP (session) | `Σ TP_i·V_i / Σ V_i` over the session's bars, `TP = (H+L+C)/3` | 1m/5m bars | first bar | resets each session |
| Anchored VWAP (daily) | same sum from an anchor date (earnings day, pivot low) on daily bars | — | anchor | — |
| Keltner | `mid = EMA_20(C)`; `mid ± m·ATR_10` | m = 2 | max(20, 11) | ≈7·10 |
| Donchian | upper = `max(H_{t−n..t−1})`, lower = `min(L_{t−n..t−1})` (prior n bars) | n = 20/55 | n+1 | n |
| Rate of change | `C_t / C_{t−n} − 1` (fraction) | n = 5/21/63 | n+1 | n |
| Relative strength line | `C^{stock}_t / C^{bench}_t` on matched dates, both adjusted | bench GSPC.INDX or SPY.US | 1 | — |

Notes on definitions that differ between libraries:

- **RSI** with a plain SMA instead of Wilder smoothing (“Cutler's RSI”) gives very different values
  (64.8 vs 56.9 on the probe date). State "Wilder". If `G = L = 0`, RSI is undefined; this code reports 50;
  if only `L = 0`, RSI = 100.
- **Bollinger** with sample sd (ddof = 1) is ≈2.6% wider at n = 20; the API uses population sd.
- **Keltner**'s original form used SMA of typical price ± SMA of (H − L); declare which variant.
- **Donchian** must exclude the current bar when testing a breakout, otherwise `C_t > upper` can never fire
  on a close at the high.
- **VWAP** from EODHD bars is an approximation: EODHD has no VWAP field; US intraday bars include pre/after
  hours (filter 09:30–16:00 America/New_York before summing; bar timestamps are UTC bar starts), and summed
  intraday volume is typically below consolidated daily volume. Null-volume bars are skipped, not zeroed.
- **OBV** uses split-adjusted volume and the adjusted-close direction; a dividend-only adjustment can flip
  the sign of a tiny move on the ex-date, so use split-only closes when that matters.

**Reference implementation** (pandas/numpy; reproduces the API conventions found in the probe).

```python
import numpy as np
import pandas as pd

def _recursive(x: pd.Series, n: int, alpha: float) -> pd.Series:
    v = x.dropna(); out = pd.Series(np.nan, index=v.index)
    if len(v) < n:
        return out.reindex(x.index)
    acc = v.iloc[:n].mean(); out.iloc[n - 1] = acc          # SMA seed
    for i in range(n, len(v)):
        acc = alpha * v.iloc[i] + (1 - alpha) * acc; out.iloc[i] = acc
    return out.reindex(x.index)

def sma(x, n):    return x.rolling(n, min_periods=n).mean()
def ema(x, n):    return _recursive(x, n, 2.0 / (n + 1))
def wilder(x, n): return _recursive(x, n, 1.0 / n)

def rsi(close, n=14):
    d = close.diff().iloc[1:]
    g, l = wilder(d.clip(lower=0), n), wilder(-d.clip(upper=0), n)
    out = 100 - 100 / (1 + g / l)
    out[(l == 0) & (g > 0)] = 100.0
    out[(l == 0) & (g == 0)] = 50.0
    return out.reindex(close.index)

def true_range(h, l, c):
    pc = c.shift()
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.where(pc.notna())                               # no TR on the first bar

def atr(h, l, c, n=14): return wilder(true_range(h, l, c), n)

def macd(close, fast=12, slow=26, signal=9):
    v = close.dropna()
    f = ema(v.iloc[slow - fast:], fast).reindex(v.index)       # both EMAs start at bar `slow`
    m = f - ema(v, slow); s = ema(m, signal)
    return pd.DataFrame({"macd": m, "signal": s, "hist": m - s}).reindex(close.index)

def bollinger(close, n=20, k=2.0):
    mid = sma(close, n); sd = close.rolling(n, min_periods=n).std(ddof=0)
    up, lo = mid + k * sd, mid - k * sd
    return pd.DataFrame({"mid": mid, "upper": up, "lower": lo,
                         "pct_b": (close - lo) / (up - lo), "bandwidth": (up - lo) / mid})

def adx(h, l, c, n=14):
    """Inputs without NaNs. Sums seeded over the first n-1 values (API-compatible)."""
    H, L, C = h.to_numpy(float), l.to_numpy(float), c.to_numpy(float)
    out = pd.DataFrame(np.nan, index=h.index, columns=["plus_di", "minus_di", "adx"])
    if len(C) < 2 * n:
        return out
    up, dn = H[1:] - H[:-1], L[:-1] - L[1:]
    pdm = np.where((up > dn) & (up > 0), up, 0.0); ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = np.maximum.reduce([H[1:] - L[1:], abs(H[1:] - C[:-1]), abs(L[1:] - C[:-1])])
    P, M, T = pdm[:n - 1].sum(), ndm[:n - 1].sum(), tr[:n - 1].sum(); dxs = []
    for i in range(n - 1, len(tr)):
        P, M, T = P - P / n + pdm[i], M - M / n + ndm[i], T - T / n + tr[i]
        pdi, mdi = 100 * P / T, 100 * M / T; out.iloc[i + 1, :2] = (pdi, mdi)
        dxs.append(100 * abs(pdi - mdi) / (pdi + mdi) if pdi + mdi else 0.0)
        if len(dxs) == n:   a = float(np.mean(dxs))
        elif len(dxs) > n:  a = (a * (n - 1) + dxs[-1]) / n
        if len(dxs) >= n:   out.iloc[i + 1, 2] = a
    return out

def stochastic(h, l, c, k=14, k_slow=3, d=3):
    ll, hh = l.rolling(k).min(), h.rolling(k).max()
    slow_k = (100 * (c - ll) / (hh - ll)).rolling(k_slow).mean()
    return pd.DataFrame({"slow_k": slow_k, "slow_d": slow_k.rolling(d).mean()})

def obv(c, v):           return (np.sign(c.diff()).fillna(0) * v).cumsum()
def donchian(h, l, n=20): return pd.DataFrame({"upper": h.rolling(n).max().shift(),
                                               "lower": l.rolling(n).min().shift()})
def keltner(h, l, c, n=20, m=2.0, atr_n=10):
    mid, a = ema(c, n), atr(h, l, c, atr_n)
    return pd.DataFrame({"mid": mid, "upper": mid + m * a, "lower": mid - m * a})

def session_vwap(bars):  # one regular session of intraday bars: high, low, close, volume
    tp = (bars["high"] + bars["low"] + bars["close"]) / 3
    v = bars["volume"].fillna(0)
    return (tp * v).cumsum() / v.cumsum().replace(0, np.nan)
```

Adjusted OHLC frame for the range-based functions:

```python
k = df["adjusted_close"] / df["close"]          # per-day factor; invalid where close is 0/missing
adj = pd.DataFrame({"open": df["open"] * k, "high": df["high"] * k, "low": df["low"] * k,
                    "close": df["adjusted_close"], "volume": df["volume"]})
```

**Pitfalls.**
- Raw OHLC across a split produces a giant false true range (the API ATR case above). Range functions need
  one consistent adjusted basis.
- `adjusted_close` is restated whenever a new dividend or split arrives; stored indicator values computed
  from an older download will not match a fresh recomputation. Store the capture date and recompute after
  corporate actions ([corporate-actions](corporate-actions.md)).
- Thinly traded listings have no row on no-trade days; a 20-bar window then spans more calendar time. Do not
  insert zero-volume bars to "fill" them.
- An indicator value on a holiday "bar" (flat carried row) is not an observation; filter holidays with
  `/api/exchange-details/{EX}` ([coverage-notes](coverage-notes.md#end-of-day-semantics)).

**Acceptance checks** (synthetic; all pass with the code above).
- `sma([1,2,3,4,5], 5) = 3`; `ema([1,2,3,4,5], 3) = [nan, nan, 2, 3, 4]`.
- RSI(14) of a strictly increasing series = 100.
- ATR(14) of bars with H = 11, L = 9, C = 10 every day = 2.
- `obv(C=[10,11,11,10,12], V=[100,200,300,400,500]) = [0, 200, 200, −200, 300]`.
- Session VWAP of bars (H,L,C,V) = (10,9,9.5,100), (11,10,10.5,300) = [9.5, 10.25].
- %B = 0.5 when the close equals the middle band.
- Against EODHD (probe 2026-10-25, AAPL.US, EOD from 2025-08-01): RSI(14) 2025-10-24 = 64.7974,
  ATR(14) on raw OHLC = 5.2031, EMA(20) on 2025-08-28 = 223.3753, MACD/signal = 4.4151/4.1891, Bollinger(20)
  upper/mid = 264.383/254.0899, ADX(14) = 29.1001, slow %K/%D (from 2025-09-15) = 76.4835/78.2446.

---

## 4. Weekly bars and multi-timeframe analysis

**Use when** a method is defined on weekly candles (10/40-week MAs, PEAD weekly rules, weekly pivots).

**EODHD inputs.** `/api/eod/{SYM}?period=w` or `period=m` (1 call); Technical API
`function=splitadjusted&agg_period=w` (5 calls, split-only OHLC).

**Method.**
1. Prefer resampling daily adjusted OHLC locally: week = Monday–Friday of the exchange calendar;
   `O = first open`, `H = max high`, `L = min low`, `C = last close`, `V = sum volume`; label the bar with
   its **last session date**.
2. If you use `period=w`: in a probe the weekly bar was **labelled with the Monday date** (2025-10-20 for the
   week ending 2025-10-24) while its close was Friday's, with raw OHLC plus `adjusted_close`. Re-label to the
   last session before joining with daily signals, or the bar leaks four days of the future.
3. A weekly bar for the current week is partial until the last session closes; mark it `partial=true` and
   exclude it from "completed candle" rules.
4. 10-week and 40-week SMAs ≈ 50- and 200-session SMAs, but they are not identical; do not mix them in one
   rule.

**Acceptance checks.** A resampled week ending on a Friday holiday ends on Thursday; the weekly close equals
the last daily close of that week; a daily join never sees a weekly value before its last session.

---

## 5. Support and resistance levels

**Use when** a user asks for "levels", a technical snapshot, or stop/target placement anchored to
structure.

**EODHD inputs.** Daily/weekly EOD (1 call). There is no support/resistance REST endpoint in the bundled
API reference. An MCP tool that computes pivot-point levels (classic, Fibonacci, Woodie, Camarilla,
DeMark on d/w/m bars) has been seen in an EODHD tool list; confirm it in the user's MCP v2 tool listing
before relying on it, and expect it to compute the same formulas below from OHLC.

**Method A — pivot points** from the prior completed bar (day for intraday levels, week or month for swing
levels); `H, L, C, O` = prior bar, raw prices if no split since:

| Method | Pivot P | Resistances | Supports |
|---|---|---|---|
| Classic | `(H+L+C)/3` | `R1 = 2P−L`, `R2 = P+(H−L)`, `R3 = H+2(P−L)` | `S1 = 2P−H`, `S2 = P−(H−L)`, `S3 = L−2(H−P)` |
| Fibonacci | `(H+L+C)/3` | `P + f·(H−L)`, f = 0.382, 0.618, 1.000 | `P − f·(H−L)` |
| Woodie | `(H+L+2C)/4` | `R1 = 2P−L`, `R2 = P+(H−L)` | `S1 = 2P−H`, `S2 = P−(H−L)` |
| Camarilla | — | `R_k = C + 1.1·(H−L)/m_k`, m = 12, 6, 4, 2 | `S_k = C − 1.1·(H−L)/m_k` |
| DeMark | `X/4`; `X = H+2L+C` if C<O, `2H+L+C` if C>O, `H+L+2C` if C=O | `R1 = X/2 − L` | `S1 = X/2 − H` |

**Method B — structural zones from swing pivots.**
1. Build a zigzag on closes (or highs/lows) with a reversal threshold `θ` = max(p%, k·ATR14/C), defaults
   p = 5%, k = 2. A swing high at bar *i* is **confirmed** only on the first later bar where price has fallen
   θ below it; store both `pivot_date` and `confirm_date`. Signals may use a pivot only after
   `confirm_date` (otherwise the screen uses the future).
2. Collect confirmed pivots over a lookback (default 252 sessions) plus prior range extremes (52-week high
   and low, prior month high/low, gap edges).
3. Cluster pivot prices whose distance is ≤ `tol` (default 0.5·ATR14 or 1.5% of price); a zone is
   `[min, max]` of its members.
4. Score each zone: touches (count), recency (exponential decay, half-life 63 sessions), volume at touches
   (pivot-day volume / 50-day average), and role reversal (a former resistance later acting as support).
5. Report the nearest support zone below and resistance zone above the current raw close, their distance in
   % and in ATR units, and an **invalidation level** (the close beyond which the stated scenario is wrong).
6. Volume confirmation of a break: close beyond the zone with `V_t ≥ 1.5 × SMA_50(V)`; not available for
   FOREX (no volume) and meaningless for `VIX.INDX` (volume 0). `GSPC.INDX` carries volume.
7. Scenario wording is conditional ("if close above 254.0–256.5 on ≥ 1.5× volume, next zone 264–266;
   invalid below 243.8"). Attach probabilities only from a backtest of the same rule on the same universe
   ([backtesting](backtesting.md)).

**Pitfalls.** Pivots on adjusted history are shifted relative to the raw chart before the latest ex-date;
draw user-facing levels on the basis the user sees. Zigzag pivots repaint until confirmed. Weekly levels
from `period=w` need the label fix in section 4.

**Acceptance checks.** Classic pivots for H = 110, L = 100, C = 105: P = 105, R1 = 110, S1 = 100, R2 = 115,
S2 = 95. A zigzag on a series that never reverses by θ yields no confirmed pivots. Each reported zone lists
its member pivots and dates.

---

## 6. Market health: breadth, highs/lows, uptrend ratio

**Use when** scoring participation ("is the rally broad?"), building a breadth dashboard
([build-recipes #42](build-recipes.md#42-market-breadth-and-regime-dashboard)) or feeding the posture score.

**EODHD inputs.**

| Need | Source | Cost / plan |
|---|---|---|
| NYSE advancers/decliners/unchanged, advancing volume | `ADVN.INDX`, `DECN.INDX`, `UNCN.INDX`, `AVVN.INDX` (read `close`); Nasdaq `ADVQ`, `AVVQ`; AMEX `ADVA`, `AVVA`. ADVN/DECN from 2007-11-09 | 1 call each, EOD plans |
| S&P 500 membership history | `fundamentals/GSPC.INDX` → `HistoricalTickerComponents` (StartDate/EndDate from April 2012; only the latest interval per ticker; `IsActiveNow` can be 1 for a future start) | 10 calls, Fundamentals or All-In-One |
| Other indices' history | Marketplace `/api/mp/unicornbay/spglobal/comp/{INDEX}` (S&P/Dow Jones families, 2–12 years) | Marketplace quota |
| Member prices | Full EOD per member incl. delisted (1 call each) for backfill; `eod-bulk-last-day/US` (100) daily forward | EOD All World |
| Sector | `General.Sector` (Fundamentals, 10 each) or Screener `sector` (current) | — |

**Method.**
1. **Universe as of date D.** Member if `StartDate ≤ D` and (`EndDate` is null or `EndDate > D`). For
   dates before 2012-04 or indices with current members only, use current members and label the series
   "survivorship-biased (current membership)". Resolve codes through `_old` suffixes and renames
   ([identity](identity.md)).
2. **% above MA (n = 50, 200).** `num_D` = members with `C_D > SMA_n,D` (adjusted closes); `den_D` = members
   with a close on D **and** n valid closes ending D. `pct_D = num_D / den_D`. Store `den_D` and the
   member count; flag dates where `den_D / members_D < 0.95`.
3. **A/D series** (NYSE, all issues, ready-made): net `A−D = ADVN − DECN`; A/D line = cumulative sum
   from a stated start; McClellan oscillator = `EMA_19(r) − EMA_39(r)` with `r = 1000·(A−D)/(A+D)` (ratio
   form is comparable across years); summation index = cumulative oscillator. Up-volume share needs total
   volume; only advancing volume (`AVVN`) is documented — verify a declining-volume code in
   `exchange-symbol-list/INDX` before using one.
4. **New highs/lows** (constituent universe): new 52-week high if `C_D ≥ max(C_{D−251..D−1})` (or use
   adjusted highs; declare). `NH − NL`, and `NH/(NH+NL)` (undefined when both are 0). The Screener signals
   `200d_new_hi/lo` are a 200-day, current-snapshot alternative only (a `50d_new_hi` signal was rejected
   with 422 in a probe). Bulk `filter=extended` `hi_250d/lo_250d` are valid only for the last ~30 days.
5. **Uptrend ratio by sector.** Declared rule, default `C > SMA_50 > SMA_200` and `SMA_50,D > SMA_50,D−10`.
   Ratio = uptrend members / members with data, per sector and overall. Current sector labels applied to
   history are a retrospective assumption; say so.
6. **Smoothing and shape.** 8-session SMA of `pct_D`; compare with its 200-session SMA (crossover); percentile
   of today's value within the series' own history (state window, e.g. 5 years); peaks/troughs via zigzag
   (θ = 10 percentage points) with confirmation dates.
7. **Divergence.** Negative divergence on D if the index made a 20-session closing high while the 8-SMA of
   %>200 is ≥ x points (default 5) below its own 20-session high; positive divergence mirrors this on lows.
   Repeat at 60 sessions.
8. **Leadership and rotation (optional).** Median 63-session RS of the top RS decile (leading-stock
   deterioration when it falls below its 20-session median); defensive vs growth ratio such as XLU+XLP vs
   XLK+XLY sector ETFs (labelled proxies, adjusted closes).

**Pitfalls.** ADVN/DECN cover all NYSE issues (including non-common lines), so they will not match a
constituent-based count. A component without data is excluded and the weight redistributed, with coverage
shown. Exchange membership in bulk files is current, not point-in-time
([coverage-notes](coverage-notes.md#end-of-day-semantics)).

**Acceptance checks.** `den_D` is printed for every date; a synthetic universe of 4 members with closes above
their 50-SMA for 3 of them gives 0.75; a member added on D+1 does not count on D; missing sessions remain
gaps in all smoothed series (no zero fill).

Sector cycle phase and overbought/oversold sector flags built on the uptrend ratio are in section 17;
theme baskets in section 18.

---

## 7. Distribution days and the follow-through-day state machine

**Use when** timing exposure changes from index action ("is selling pressure building?", "has the rally
attempt confirmed?").

**EODHD inputs.** `GSPC.INDX` and/or `IXIC.INDX`/`NDX.INDX` daily OHLCV (1 call each). `GSPC.INDX` carried
nonzero volume in a 2026-10-25 probe; confirm the index you choose has volume, otherwise use one ETF
(SPY.US, QQQ.US) consistently for both price and volume. `VIX.INDX` volume is 0.

**Distribution day (DD).** Session *t* with `C_t/C_{t−1} − 1 ≤ −0.2%` **and** `V_t > V_{t−1}` (both volumes
> 0). A DD expires after 25 sessions, or earlier once the index closes ≥ 5% above the DD's close.
Count active DDs over the last 5/15/25 sessions. Risk tiers (heuristic): 0–2 normal, 3–4 caution, 5
elevated, ≥ 6 severe.

**Follow-through day (FTD) state machine** (closes, one row per session):

| State | Entered when |
|---|---|
| NO_SIGNAL | Default; also after the index recovers its pre-correction peak |
| CORRECTION | Close ≤ (1 − 5%) × highest close of the last 60 sessions; swing low = that close, updated on every lower close |
| RALLY_ATTEMPT (day 1…) | First session after the swing low that closes above the prior close; day count increments every session |
| FTD_CONFIRMED | On day 4–10 of the attempt: gain ≥ 1.25% **and** volume > prior session; record `ftd_low` = that day's low |
| WINDOW_EXPIRED | Day 10 passes without an FTD (a new swing low restarts the cycle) |
| FTD_INVALIDATED | After an FTD, a close below `ftd_low` |
| reset to CORRECTION | Any close below the swing low (new swing low, day count 0) |

```python
def ftd_state(close, volume, low, corr_pct=0.05, lookback=60, ftd_gain=0.0125, window=(4, 10)):
    state, swing, day, ftd_low, peak, log = "NO_SIGNAL", None, 0, None, None, []
    for i in range(1, len(close)):
        d, c, pc = close.index[i], close.iloc[i], close.iloc[i - 1]
        hi, gain, prev = close.iloc[max(0, i - lookback):i + 1].max(), c / pc - 1, (state, day)
        if state == "NO_SIGNAL":
            if c <= hi * (1 - corr_pct):
                state, swing, day, peak = "CORRECTION", c, 0, hi
        elif state in ("CORRECTION", "RALLY_ATTEMPT", "WINDOW_EXPIRED"):
            if c < swing:
                state, swing, day = "CORRECTION", c, 0
            elif state == "CORRECTION":
                if c > pc: state, day = "RALLY_ATTEMPT", 1
            else:
                day += 1
                if state == "RALLY_ATTEMPT" and window[0] <= day <= window[1] \
                        and gain >= ftd_gain and volume.iloc[i] > volume.iloc[i - 1]:
                    state, ftd_low = "FTD_CONFIRMED", low.iloc[i]
                elif state == "RALLY_ATTEMPT" and day > window[1]:
                    state = "WINDOW_EXPIRED"
        else:                                                  # FTD_CONFIRMED / FTD_INVALIDATED
            if c < swing:                    state, swing, day = "CORRECTION", c, 0
            elif state == "FTD_CONFIRMED" and c < ftd_low: state = "FTD_INVALIDATED"
            elif c >= peak:                  state = "NO_SIGNAL"
        if (state, day) != prev: log.append((d, state, day))
    return state, log
```

Run it per index; report both and a combined state (confirmed if either confirms, with which one). After an
FTD, keep counting DDs: several DDs within the first weeks after the FTD weaken it (report the count, do not
hide it).

**Pitfalls.** Use closes for the swing low, not intraday lows. Index bars arrive in rounds after the close;
run after the final update. A holiday carry-over bar (identical OHLC to the prior day) must be removed before
counting days.

**Acceptance checks.** Synthetic path: 61 flat closes at 100, seven −1% sessions, then +0.5%, +0.3%, −0.2%,
+1.5% on higher volume → CORRECTION on the sixth down day, RALLY_ATTEMPT days 1–3, FTD_CONFIRMED on day 4;
a following close below that day's low → FTD_INVALIDATED. DD check: closes 100, 99.7, 99.8, 99.5, 99.6 with
volumes 1, 2, 1, 3, 1 (×10⁹) → two active DDs (sessions 2 and 4).

---

## 8. Regime detection and a fail-safe posture score

> Statistical regime methods (CUSUM, HMM, rolling Hurst) are in [methods-quant-research §4.5–4.7](methods-quant-research.md#45-cusum-change-points-in-mean-and-volatility).

**Use when** classifying the market environment or converting several indicators into an exposure ceiling
or a conviction score.

**EODHD inputs.** ETF ratios from EOD `adjusted_close` (1 call per ETF; verify each symbol once): RSP/SPY
(equal-weight vs cap-weight), IWM/SPY (small vs large), HYG/LQD (high-yield vs investment-grade credit),
XLY/XLP (discretionary vs staples), SPY/TLT rolling correlation; `VIX.INDX`; UST par curve
`/api/ust/yield-rates?filter[year]=YYYY` (fields `date`, `tenor`, `rate` in percent; tenors 1M…30Y);
optional credit series `/api/credit-risk/corporate/hqm-yields`; breadth from section 6.

**Method.**
1. **Ratio trend score** for each ratio `X = A/B` (matched dates): `s_trend = +1` if `X > SMA_50(X) > SMA_200(X)`,
   `−1` if `X < SMA_50(X) < SMA_200(X)`, else 0. **Percentile score**: rank of `X_t` within its trailing
   756 sessions, mapped to `2·pct − 1`. Ratio score = mean of the two. Orientation: higher RSP/SPY, IWM/SPY,
   HYG/LQD, XLY/XLP = risk-on.
2. **Stock–bond correlation**: 63-session Pearson correlation of daily log returns SPY vs TLT; report level
   and sign change (positive correlation removes the bond hedge).
3. **Curve**: `10Y − 2Y` and `10Y − 3M` in percentage points on the same date; changes in basis points
   (1 pp = 100 bp). Missing tenor = missing, not 0.
4. **Volatility regime**: percentile of `VIX.INDX` close over 756 sessions; realized-vol percentile (21-day,
   ×√252) of the index; Bollinger bandwidth percentile. High percentile = risk-off score.
5. **Trend regime**: index `C` vs `SMA_200`, slope of `SMA_50` over 20 sessions, `ADX_14` (≥ 25 trending,
   < 20 range-bound; heuristic).
6. **Statistical alternatives** (fit on training windows only, applied forward): rolling Hurst exponent
   (> 0.5 trending), CUSUM change points on returns, a 2–3 state Gaussian HMM on returns and volatility.
   Never fit an HMM on the full sample and then label history with it. Estimation procedures:
   [methods-quant-research §4](methods-quant-research.md#4-stationarity-and-regime-features).
7. **Composite posture score.** Each component `s_i ∈ [−1, +1]` with declared weight `w_i` and as-of date.
   `score = Σ w_i s_i / Σ_{scored} w_i`; `coverage = Σ_{scored} w_i / Σ w_i`.
   - **Stale or missing** (as-of older than 2 sessions for daily inputs): component unscored.
   - **Fail-safe**: missing data can only lower exposure. `ceiling = map(score)` (declared table, e.g.
     score ≤ −0.5 → 20%, −0.5…0 → 40%, 0…0.5 → 70%, > 0.5 → 100%); if `coverage < 0.7`, cap the
     ceiling at 40% and set `confidence = low`; if any hard gate fires (FTD_INVALIDATED, ≥ 6 DDs,
     VIX percentile ≥ 95%), cap at 20%.
   - **Contradiction flag** when two components with `|s| ≥ 0.5` have opposite signs; list them.
   - The mapping score → exposure is a heuristic unless validated out of sample
     ([research-validation](research-validation.md)).

**Boundaries.** Market-wide CBOE put/call ratios, FINRA margin debt, fund flows and crypto perpetual
funding rates/open interest are **not EODHD data**; a "bubble" or crypto-leverage score must omit them or
take them as user-supplied inputs. Usable EODHD substitutes: `VIX.INDX`, IPO counts from
`/api/calendar/ipos`, breadth, price acceleration (ROC of ROC), single-name option chains for US
stocks/ETFs from the Marketplace (no index options; history from Q4 2023 — [options](options.md)).
The bubble score built from these substitutes is section 22; the crypto regime recipe is section 23;
combining several detectors into one list is section 21.

**Acceptance checks.** Dropping one input lowers `coverage` and never raises the ceiling; a stale input shows
its as-of date and is excluded; regime features at date *t* use only data through *t*−1 when used as a
backtest filter.

---

## 9. Setup definitions

**Use when** screening for a named swing setup. Every candidate output lists each rule, its value, the
threshold and pass/fail/not-scored. Universe first (Screener or bulk, section 12), then local rules on
adjusted daily OHLC, signal at the close, fill no earlier than the next open.

### 9.1 Trend template (eight-condition stage-2 template popularized by Minervini)

| # | Rule (all on adjusted closes, session *t*) |
|---|---|
| 1 | `C > SMA_150` and `C > SMA_200` |
| 2 | `SMA_150 > SMA_200` |
| 3 | `SMA_200,t > SMA_200,t−21` (rising ≥ 1 month) |
| 4 | `SMA_50 > SMA_150` and `SMA_50 > SMA_200` |
| 5 | `C > SMA_50` |
| 6 | `C ≥ 1.30 × min(L_{t−251..t})` (≥ 30% above 52-week low) |
| 7 | `C ≥ 0.75 × max(H_{t−251..t})` (within 25% of 52-week high) |
| 8 | RS rank ≥ 70 |

**RS rank** (an approximation of commercial RS ratings, label it so): `RS_raw = 0.4·ROC_63 + 0.2·ROC_126 +
0.2·ROC_189 + 0.2·ROC_252` on adjusted closes; RS rank = percentile (1–99) of `RS_raw` within the declared
universe on the same date. Needs 253 sessions; younger listings are "not scored" on rules 3, 6, 7, 8.

### 9.2 Volatility contraction pattern (VCP)

1. Prerequisite: trend template passes (or at least rules 1–5).
2. Base window: from the most recent confirmed swing high `B_0` within the last 15–65 sessions to today.
3. Contractions: successive confirmed swing high→low pullbacks inside the base (zigzag θ = 3% or 1·ATR),
   depths `d_k = 1 − low_k/high_k`.
4. Rules: at least 2 contractions; `d_{k+1} ≤ 0.75·d_k` for each step; first `d_1 ≤ 35%`; last
   `d_last ≤ 10%`; base length ≥ 15 sessions.
5. Volume dry-up: `SMA_10(V)` during the last contraction ≤ 0.7 × `SMA_50(V)` at base start.
6. Pivot = high of the last contraction. Breakout = `C > pivot` with `V ≥ 1.4 × SMA_50(V)`.
7. Only pivots confirmed before *t* may be used (no future swing detection).

### 9.3 CANSLIM components on EODHD data

| Letter | EODHD-computable proxy | Source fields | Default pass |
|---|---|---|---|
| C | Latest quarter EPS YoY growth and revenue YoY | `Earnings::History.{date}.epsActual` vs same quarter a year earlier; `Financials::Income_Statement::quarterly.totalRevenue` | EPS ≥ +25%, revenue ≥ +20%; acceleration = growth rising vs prior quarter |
| A | 3-year annual EPS CAGR; ROE | `Earnings::Annual` (or yearly income statement); `Highlights.ReturnOnEquityTTM` (fraction) | CAGR ≥ 25%; ROE ≥ 0.17 |
| N | Distance to 52-week high | Local max of adjusted highs, or `Technicals.52WeekHigh` (current) | Within 15%; "new product/management" unscored |
| S | Up/down volume ratio, 50 sessions; float | Σ V on up-close days / Σ V on down-close days; `SharesStats.SharesFloat` | Ratio ≥ 1.0 (heuristic) |
| L | RS rank (9.1) | — | ≥ 80 |
| I | Institutional sponsorship, **current snapshot** | `Holders.Institutions` / `Holders.Funds` (top ~20 each: `name`, `date`, `totalShares` %, `currentShares`, `change`, `change_p`); `SharesStats.PercentInstitutions` | Net `change` of listed holders > 0; trend only from your own dated captures |
| M | Market direction | `GSPC.INDX` C vs `EMA_50`; section 7 state | C > EMA_50 and not FTD_INVALIDATED / ≥ 6 DDs |

The "I" boundary: Fundamentals `Holders` shows the latest reported positions of the largest holders (quarterly
filings with up to a 45-day lag, often top 20 only). Filer-level 13F portfolios across all institutions and
their history are **not EODHD data**; quarter-over-quarter change beyond the `change` field requires your own
dated snapshots ([build-recipes #39](build-recipes.md#39-point-in-time-snapshot-recorder)). Fundamentals are
current restated values, so a historical CANSLIM backtest is not point-in-time
([temporal-research](temporal-research.md)). EPS from `Earnings::History` is generally adjusted
(non-GAAP) — compare like with like ([fundamentals](fundamentals.md#core-calculations)).

**CANSLIM composite (0–100, declared defaults; a heuristic, not a validated ranking).** Each letter maps
its input to a sub-score by piecewise-linear interpolation between breakpoints (clamped at both ends).

| Letter | Input | Breakpoints (input → sub-score) | Adjustments |
|---|---|---|---|
| C | Latest-quarter EPS YoY growth `g` (fraction) | 0 → 0, 0.25 → 60, 0.50 → 85, 1.00 → 100 | cap 70 if revenue YoY < 0.20; +10 if growth is accelerating (cap 100). Prior-year quarter EPS ≤ 0 → unscored (flag `turnaround`), never a huge growth rate |
| A | 3-year annual EPS CAGR | 0 → 0, 0.25 → 70, 0.50 → 100 | **stability** `σ_g` = sample sd of the last 8 quarterly YoY EPS growth rates (≥ 6 needed): ×1.00 if σ_g ≤ 0.15, ×0.85 if ≤ 0.30, else ×0.70; cap 50 if ROE < 0.17 |
| N | Distance below the 52-week high `d = 1 − C/max(H_{t−251..t})` | 0 → 100, 0.05 → 90, 0.15 → 60, 0.25 → 0 | — |
| S | Up/down volume ratio (50 sessions) | 0.8 → 0, 1.0 → 50, 1.5 → 80, 2.0 → 100 | — |
| L | RS rank 1–99 (9.1) | 50 → 0, 70 → 40, 80 → 70, 90 → 90, 99 → 100 | — |
| I | Share of listed `Holders.Institutions` rows with `change > 0` | 0.3 → 0, 0.5 → 50, 0.7 → 100 | unscored if fewer than 5 holders are listed |
| M | Market state | `confirmed` → 100, `caution` → 50, `invalidated` → 0 | M = 0 caps the composite at 40 (market gate) |

M states: `confirmed` = `GSPC.INDX` close > `EMA_50`, section 7 state not `FTD_INVALIDATED` and ≤ 4 active
distribution days; `invalidated` = `FTD_INVALIDATED` or ≥ 6 active distribution days; otherwise `caution`.
Weights: C 0.20, A 0.15, N 0.15, S 0.10, L 0.20, I 0.05, M 0.15. `Composite = Σ_scored w_k·s_k / Σ_scored w_k`,
`coverage = Σ_scored w_k / Σ w_k`. Bands (heuristic): ≥ 80 strong candidate, 65–80 watch, < 65 not a
candidate; coverage < 0.7 adds a `low coverage` label.

```python
import numpy as np

def interp(x, xs, ys):
    return float(np.interp(x, xs, ys))

def composite(scores, weights):
    """Weighted mean over scored components; coverage = scored weight / total weight."""
    w = {k: weights[k] for k in scores if scores[k] is not None}
    cov = sum(w.values()) / sum(weights.values())
    val = sum(scores[k] * w[k] for k in w) / sum(w.values()) if w else None
    return val, cov

CANSLIM_W = {"C": .20, "A": .15, "N": .15, "S": .10, "L": .20, "I": .05, "M": .15}

def canslim_scores(d):
    s = {}
    if d.get("eps_yoy") is not None:
        v = interp(d["eps_yoy"], [0, .25, .5, 1.0], [0, 60, 85, 100])
        if d.get("rev_yoy") is not None and d["rev_yoy"] < .20: v = min(v, 70)
        if d.get("eps_accel"): v = min(100, v + 10)
        s["C"] = v
    if d.get("eps_cagr3") is not None:
        v = interp(d["eps_cagr3"], [0, .25, .5], [0, 70, 100])
        sd = d.get("eps_growth_sd")
        if sd is not None: v *= 1.0 if sd <= .15 else (.85 if sd <= .30 else .70)
        if d.get("roe") is not None and d["roe"] < .17: v = min(v, 50)
        s["A"] = v
    if d.get("dist_52wh") is not None:
        s["N"] = interp(d["dist_52wh"], [0, .05, .15, .25], [100, 90, 60, 0])
    if d.get("updown_vol") is not None:
        s["S"] = interp(d["updown_vol"], [.8, 1.0, 1.5, 2.0], [0, 50, 80, 100])
    if d.get("rs_rank") is not None:
        s["L"] = interp(d["rs_rank"], [50, 70, 80, 90, 99], [0, 40, 70, 90, 100])
    if d.get("holders_up_share") is not None and d.get("n_holders", 0) >= 5:
        s["I"] = interp(d["holders_up_share"], [.3, .5, .7], [0, 50, 100])
    if d.get("market") is not None:
        s["M"] = {"confirmed": 100, "caution": 50, "invalidated": 0}[d["market"]]
    return s

def canslim_composite(d, weights=CANSLIM_W, market_gate_cap=40):
    s = canslim_scores(d)
    val, cov = composite(s, weights)
    if s.get("M") == 0:
        val = min(val, market_gate_cap)
    return round(val, 1), round(cov, 2), s
```

**Acceptance checks (composite).** EPS YoY 0.40 with revenue YoY 0.25 and acceleration, 3-year CAGR 0.30
with σ_g = 0.20 and ROE 0.22, 4% below the 52-week high, up/down volume 1.3, RS rank 88, 60% of 20 listed
holders adding, market `confirmed` → sub-scores C 85, A 64.6, N 92, S 68, L 86, I 75, M 100 and composite
**83.2** (coverage 1.0). Dropping the holders input and setting the market to `invalidated` → composite
capped at **40**, coverage 0.95.

### 9.4 Momentum burst (short-term range-expansion breakout)

Trigger (any one, on session *t*):
- **Percent breakout**: `C_t / C_{t−1} ≥ 1.04` and `V_t > V_{t−1}` and `V_t ≥ 100,000` shares.
- **Absolute breakout**: `C_t − O_t ≥ 0.90` price units and `V_t ≥ 100,000` (scale-dependent; only for
  prices roughly 10–100 in listing currency; state it).
- **Range expansion**: `(H_t − L_t) > max` of the prior 3 ranges and `C_{t−1}/C_{t−2} − 1 < 2%`.

Quality and failure filters: prior contraction (20-session close range ≤ 15%, or narrowest range of 7
sessions on *t*−1); close location `CLV = (C − L)/(H − L) ≥ 0.7`; reject if `C_{t−1}/C_{t−4} − 1 ≥ 10%`
(already extended) or a ≤ −4% session occurred in the last 5. Planning reference: entry = next session open
(or above `H_t`), stop = `L_t`, horizon 3–5 sessions (time exit).

### 9.5 Exhaustion hammer (pullback reversal candle)

Candle geometry on session *t* (`R = H − L > 0`, `body = |C − O|`, `lw = min(O,C) − L`, `uw = H − max(O,C)`):
`lw ≥ 2·body`, `lw ≥ 0.5·R`, `uw ≤ 0.25·R`, `CLV ≥ 0.6`. Context: prior momentum (`C` at the 63-session high
within the last 30 sessions, or RS rank ≥ 70); pullback depth from that high between 8% and 35%;
**undercut and reclaim**: `L_t < min(L_{t−10..t−1})` and `C_t > min(L_{t−10..t−1})`; `V_t ≥ 1.2 × SMA_20(V)`;
liquidity floor `SMA_20(C·V) ≥` declared value. Plan: entry above `H_t` next session, stop below `L_t` minus a
buffer (0.1·ATR).

A "near-close" variant uses a live snapshot before the close (`/api/real-time` or `us-quote-delayed`,
15–20 min delayed); label it provisional and re-check on the final EOD bar.

### 9.6 Parabolic exhaustion (and a short-side plan)

Daily conditions (all, heuristics): extension `(C − EMA_10)/ATR_14 ≥ 3`; `ROC_5 ≥ 30%` (small caps) or
≥ 15% (large caps); ≥ 3 consecutive higher closes; climax volume `V_t ≥ 3 × SMA_50(V)`; range expansion
`H − L ≥ 2 × ATR_14`.

Intraday trigger (next session, 5m bars from `/api/intraday/{SYM}?interval=5m`, raw, regular hours only):
opening range = high/low of the first 30 minutes; trigger = first 5m close below the opening-range low
**and** below session VWAP (section 3), or first lower-high bar after a failed new high. Plan: stop above the
session high (plus 0.1·ATR); targets at session VWAP, then `EMA_10` daily, expressed as R multiples; time
exit at the close if neither target nor stop is hit.

Boundaries: short-borrow availability, locate, fees and short-sale-restriction (SSR) status are **not EODHD
data** — they are user/broker-supplied gates. Intraday bars are finalized 2–3 h after the US close, so a
same-day intraday trigger needs WebSockets or polling, not the intraday history API
([intraday](intraday.md)).

---

## 10. Trade plans: entry, stop, R targets, time exit, heat

> To compare exit rules under the validation protocol (IS/OOS, deflated Sharpe), use the exit-rule lab in [methods-quant-research §3.13](methods-quant-research.md#313-exit-rule-lab).

**Use when** turning a setup into a plan the user can review. A plan is never an order; EODHD has no order
endpoints.

**Inputs.** Setup pivot/trigger (section 9), ATR (adjusted OHLC), user-supplied equity, risk fraction, caps.
Liquidity from `avgvolccy` (Technical API, average volume × price, 5 calls) or locally
`SMA_20(C·V)` on split-adjusted values.

**Method.**
1. **Worst-case entry** `E = pivot × (1 + max_chase)`, default `max_chase = 2%`; a fill above `E` is a
   skipped trade, not a chased one.
2. **Stop** `S` = structural low (setup low, zone bottom) or `E − k·ATR_14` (k = 1.5–3 scenarios), whichever
   the rule declares; refuse the plan if `(E − S)/E > max_stop` (default 8%) or `E ≤ S`.
3. **R** = `E − S`. Targets at `E + m·R`, m = 1, 2, 3; optional partial exits (e.g. 1/3 at 2R, move stop to
   breakeven after 1R — declared, applied with conservative same-bar ordering: stop first).
4. **Time exit**: close the simulated position after `N` sessions (3–5 for momentum bursts, 20–60 for base
   breakouts) if 1R was not reached.
5. **Size** `shares = floor(min(equity·risk_frac / R, equity·max_pos / E, ADV_value·max_adv / E))`; report
   which cap binds.
6. **Portfolio heat** = Σ over open plans of `shares × (current price − stop)⁺` / equity; refuse new plans
   above the heat cap (default 6%). Daily/weekly loss limits and halts are in
   [portfolio-risk](portfolio-risk.md#sizing-and-controls).

```python
import math
def trade_plan(pivot, stop, equity, risk_frac, max_chase=0.02, r_targets=(1, 2, 3),
               adv_value=None, max_adv_frac=0.01, max_position_frac=0.25, max_stop=0.08):
    entry = pivot * (1 + max_chase); r = entry - stop
    if not (r > 0 and stop > 0) or r / entry > max_stop:
        return None                                            # refusal: undefined or too wide
    caps = {"risk": math.floor(equity * risk_frac / r),
            "position": math.floor(equity * max_position_frac / entry)}
    if adv_value:
        caps["liquidity"] = math.floor(adv_value * max_adv_frac / entry)
    bind = min(caps, key=caps.get); shares = max(caps[bind], 0)
    return {"entry_max": round(entry, 4), "stop": stop, "R": round(r, 4), "shares": shares,
            "binding_cap": bind, "risk_amount": round(shares * r, 2),
            "targets": {f"{m}R": round(entry + m * r, 4) for m in r_targets}}
```

**Acceptance checks.** `trade_plan(50, 47.5, 100000, 0.005)` → entry 51.0, R = 3.5, 142 shares (risk cap),
targets 54.5/58.0/61.5; a stop above entry returns `None`; with `adv_value=200000` the liquidity cap
(39 shares) binds.

**Trailing and signal-based exits.** Signals and stop levels are computed on adjusted OHLC (section 1);
convert to raw prices only for display.

- **ATR trailing stop**: `S_t = max(S_{t−1}, C_t − m·ATR_n,t)`.
- **Chandelier stop**: `S_t = max(S_{t−1}, HH_n,t − m·ATR_n,t)` with `HH_n,t = max(H_{t−n+1..t})`; defaults
  n = 22, m = 3 (both stops).
- `S` starts at the plan's initial stop (step 2) and **only ratchets upward**. Before ATR warm-up (n + 1
  bars) the initial stop holds.
- `S_t` is known after the close of *t* and is active on *t*+1: exit if `L_{t+1} ≤ S_t`, filled at
  `min(O_{t+1}, S_t)` (a gap through the stop fills at the open).
- **Signal exit**: `C_t < SMA_n,t` (default n = 50) or `EMA_fast` crossing below `EMA_slow` at the close of
  *t*; filled at `O_{t+1}`.
- Order of checks inside one bar: stop, target, signal, time exit (conservative: stop first).

**Exit-rule lab** (compare hold, fixed, tiered, trailing and signal exits on the same entries).
1. Entry cohort: every signal of one rule version from the outcome ledger
   ([methods-quant-research §7.1](methods-quant-research.md#71-forward-outcome-ledger)), filled at the next
   open, on a universe that includes delisted listings.
2. Run every exit rule on the same trades independently. Per trade record the exit date, return
   `ret = exit/entry − 1`, `R = (exit − entry)/(entry − initial stop)` and `MFE = max(H over the hold)/entry − 1`.
3. Per rule report n, win rate, mean R, **give-back** = median of `1 − ret/MFE` over trades with MFE > 0
   (share of the best open gain handed back), and an R-equity curve: trades ordered by exit date,
   `E_k = Π_{i≤k} (1 + f·R_i)` with risk fraction f (default 1%), `CAGR = E_end^{365/days} − 1` (days between
   the first and last exit) and the maximum drawdown of `E`. This simplified curve ignores overlapping
   positions and capital limits; use [backtesting](backtesting.md) for a capital-constrained version.
4. Choosing a rule is a trial: log every rule tried in the trial ledger
   ([methods-quant-research §3.1](methods-quant-research.md#31-trial-ledger)), choose on a training period and
   confirm out of sample.

```python
import numpy as np
import pandas as pd

def trailing_stop(h, l, c, entry_idx, initial_stop, m=3.0, n=22, kind="chandelier"):
    """Stop known after the close of each bar; ratchets up only. Uses atr() from section 3."""
    a = atr(h, l, c, n)
    ref = h.rolling(n, min_periods=1).max() if kind == "chandelier" else c
    stop = pd.Series(np.nan, index=c.index); s = initial_stop
    for i in range(entry_idx, len(c)):
        cand = ref.iloc[i] - m * a.iloc[i]
        if not np.isnan(cand):
            s = max(s, cand)
        stop.iloc[i] = s
    return stop

def run_exit(o, h, l, c, entry_idx, entry_px, stop_series=None, fixed_stop=None,
             target=None, signal_exit=None, max_hold=None):
    """One long trade filled at the open of entry_idx. stop_series[i] is active on bar i+1."""
    stop = fixed_stop
    for i in range(entry_idx, len(c)):
        if i > entry_idx and stop_series is not None:
            stop = stop_series.iloc[i - 1]
        if stop is not None and l.iloc[i] <= stop:
            return i, min(o.iloc[i], stop) if i > entry_idx else stop, "stop"
        if target is not None and h.iloc[i] >= target:
            return i, max(o.iloc[i], target) if i > entry_idx else target, "target"
        if signal_exit is not None and signal_exit.iloc[i] and i + 1 < len(c):
            return i + 1, o.iloc[i + 1], "signal"            # signal at close, fill next open
        if max_hold is not None and i - entry_idx + 1 >= max_hold:
            return i, c.iloc[i], "time"
    return len(c) - 1, c.iloc[-1], "open"

def exit_lab(trades, dates, risk_frac=0.01):
    """trades: dicts {exit_idx, ret, R, mfe} for one exit rule."""
    t = sorted(trades, key=lambda x: x["exit_idx"])
    eq = np.cumprod([1 + risk_frac * x["R"] for x in t])
    peak = np.maximum.accumulate(np.r_[1.0, eq])[1:]
    days = (dates[t[-1]["exit_idx"]] - dates[t[0]["exit_idx"]]).days or 1
    gb = [1 - x["ret"] / x["mfe"] for x in t if x["mfe"] > 0]
    return {"n": len(t), "win_rate": float(np.mean([x["ret"] > 0 for x in t])),
            "avg_R": float(np.mean([x["R"] for x in t])), "cagr": float(eq[-1] ** (365 / days) - 1),
            "max_dd": float((1 - eq / peak).max()), "median_giveback": float(np.median(gb)) if gb else None}
```

**Acceptance checks (exits).** Closes 100, 102, …, 110, 109, 107, 104, 101, 99, 98 with H = C + 1, L = C − 1,
O = prior close, initial stop 95, n = 3, m = 2: chandelier stops 95, 95, 95, 101, 103, 105, 105.67 (then
flat), exit on bar index 8 at 105.67; if that bar opens at 100 the fill is 100 (gap through). ATR trailing
stops 95, 95, 95, 100, 102, 104 (then flat). Signal exit `C < SMA_3` fires at the close of index 7 and fills
at the next open, 107. Exit lab with four trades (R = 2, −1, 0.8, −1; ret = 0.10, −0.05, 0.04, −0.05; MFE =
0.15, 0.02, 0.12, 0) → win rate 0.5, mean R 0.2, median give-back 0.667, max drawdown 0.0121.

---

## 11. Earnings reaction scoring and post-earnings drift

**Use when** grading post-earnings movers, tracking drift setups, or explaining a reaction. Complements
[events-news](events-news.md) and [build-recipes #41](build-recipes.md#41-earnings-season-monitor).

**EODHD inputs.** `/api/calendar/earnings?from=&to=` (1 call; filter symbols locally — `symbols=` alone has
returned empty): `report_date`, `before_after_market` (`BeforeMarket`, `AfterMarket`, or null), `actual`,
`estimate`, `difference`, `percent`. EOD for the reaction window (1 call per symbol). News for catalyst
typing (5 per ticker). Fundamentals or Calendar & News plan for the calendar.

**Method.**
1. **Reaction session** `t*`: `BeforeMarket` → the `report_date` session; `AfterMarket` → the next trading
   session after `report_date`; null → exclude, or compute both and flag `timing_unknown`. Use the exchange
   calendar, not weekday arithmetic.
2. **Factors** (`p` = session before `t*`):
   - Gap = `O_{t*}/C_p − 1` (raw prices; if `t*` is an ex-dividend or split session, use adjusted values).
   - Reaction = `C_{t*}/C_p − 1`; hold = `C_{t*+k}/C_{t*} − 1` for k = 1, 5, 20.
   - Pre-trend = `C_p/C_{p−20} − 1` (adjusted).
   - Volume ratio = `V_{t*} / SMA_50(V)` ending at `p`.
   - Position = `C_{t*}` vs `SMA_50` and `SMA_200` (adjusted).
   - Surprise sign and size: `actual` vs `estimate` from the **same calendar row** (one source, one basis);
     never mix calendar actuals with `calendar/trends` consensus.
   - Abnormal reaction = reaction − beta·(benchmark return over the same session); state the benchmark.
3. **Score** (declared, example): gap 30, volume ratio 25, pre-trend 15, above 50-SMA 15, above 200-SMA 15;
   each factor mapped to 0–100 by declared breakpoints (e.g. gap: < 2% → 0, 2–5% → 50, 5–10% → 80,
   ≥ 10% → 100). Grade by score band; unscored factors re-normalize weights.
4. **Episodic pivot** (variant): gap ≥ 10% on volume ratio ≥ 3 after a typed catalyst, from a base without
   a prior run-up (`ROC_63 < 30%`). Catalyst typing from EODHD news `tags`/titles is model judgement — label it.
5. **PEAD on weekly candles** (weekly bars built as in section 4, labelled by last session):
   - Reaction week = the week containing `t*`; require gap ≥ 5% and reaction > 0.
   - Watch window = the next 5 completed weeks.
   - **Red week** = first completed week in the window with weekly `C < O`. Stage `SIGNAL_READY`.
   - Entry trigger = a later daily high above the red week's high (stage `TRIGGERED`); stop = red week's low;
     targets in R; time exit after N weeks.
   - `INVALIDATED` if any daily close falls below the reaction session's low (gap filled);
     `EXPIRED` if the window ends without a red week or trigger.
6. **Pre/post drift study**: average abnormal returns over [−5, −1] and [+1, +20] sessions around `t*` by
   surprise tercile, with counts per cohort ([backtesting](backtesting.md)).

**Pitfalls.** An AfterMarket report dated Friday reacts on Monday (or the next session after a holiday).
Estimates in `calendar/trends` are not split-adjusted and are updated in place; archive them if drift
studies need "consensus as known then". Report dates move; store each calendar pull.

**Acceptance checks.** An AfterMarket report on 2025-07-31 (Thursday) maps to 2025-08-01; a BeforeMarket
report maps to the same date; a null timing row never receives a score without the `timing_unknown` flag;
a PEAD candidate whose red week is still partial stays `MONITORING`.

---

## 12. Screener: natural language to filters, and result cleaning

**Use when** a user describes a screen in words ("high-dividend large caps", "oversold quality names") and
needs a clean list of common stocks. Verified against
[stock-screener-data](api/endpoints/stock-screener-data.md); paging code in
[code-patterns §8](code-patterns.md#8-screener-partitioning).

**EODHD inputs.** `/api/screener` (5 calls per request; EOD+Intraday Extended or All-In-One; demo key not
accepted). `filters` = JSON array of `[field, op, value]` triples combined with AND; `signals`
comma-separated; `sort=field.direction` (`asc`/`desc`); `limit` 1–500, `offset` 0–999 → at most 1,000 rows
per screen. Filterable fields (14): `code`, `name`, `exchange`, `sub_exchange`, `sector`, `industry`,
`market_capitalization`, `earnings_share`, `dividend_yield`, `refund_1d_p`, `refund_5d_p`,
`adjusted_close`, `avgvol_1d`, `avgvol_200d`. Signals: `200d_new_hi`, `200d_new_lo`, `bookvalue_neg`,
`bookvalue_pos`, `wallstreet_hi`, `wallstreet_lo`. Every row carries `last_day_data_date` and
`currency_symbol`.

**Natural-language mapping** (defaults; one exchange or one currency per screen):

| Phrase | Filters / post-step |
|---|---|
| US common stock | `["exchange","in",["nyse","nasdaq"]]` (or `sub_exchange`), then the cleaning steps |
| large / mid / small / micro cap | `market_capitalization` ≥ 10e9 / 2e9–10e9 / 3e8–2e9 / < 3e8, **in listing currency** |
| high dividend | `["dividend_yield",">=",0.03]` and `["dividend_yield","<=",0.25]` (fraction) |
| income, excluding rate-sensitive sectors | add `["sector","not in",["Financial Services","Utilities","Real Estate"]]` (check names against the sector/industry taxonomy CSV) |
| profitable | `["earnings_share",">",0]` |
| cheap (P/E < 15) | P/E is **not** a Screener field: keep `earnings_share > 0`, compute `adjusted_close/earnings_share` locally, or read `Valuation.TrailingPE` for the shortlist (10 calls each) |
| liquid | `["avgvol_200d",">",500000]` and `["adjusted_close",">",5]`; dollar volume `adjusted_close × avgvol_200d` computed locally |
| top gainers / losers today | `sort=refund_1d_p.desc` / `.asc` with `avgvol_1d` floor |
| 52-week high | no 52-week signal: `200d_new_hi` is 200-day; for 52-week use bulk `filter=extended` `hi_250d` (last 30 days only) or local EOD |
| below analyst target | `signals=wallstreet_lo` plus price and volume floors |
| negative book value | `signals=bookvalue_neg` |
| oversold / RSI < 30, above 200-day | not Screener fields: shortlist, then RSI(14)/SMA locally from EOD (section 3) |
| sector X | `["sector","=","Technology"]`; multi-word values need `match` (`"Consumer*"`) |
| name starts with | `["name","match","Bio*"]` (word-prefix match) |

**Cleaning rules** (apply in this order, log every drop with a reason):
1. **No instrument-type filter.** `type` is not a Screener field (a `type` triple has been reported to return
   422). Join results to `/api/exchange-symbol-list/{EX}` (1 call per exchange; `Type` = `Common Stock`,
   `Preferred Stock`, `ETF`, `FUND`, …) or to bulk `filter=extended` `type`, and keep the requested type.
2. **Scope away OTC.** `exchange=us` covers every US venue including OTC foreign ordinaries and ADR lines
   (five-letter codes ending in `F` or `Y`), whose yields and caps are often broken. For clean common stock
   use `nyse`/`nasdaq`. If the user insists on `us`, drop or flag F/Y five-letter codes after the type join.
3. **Hyphenated codes.** Preferreds, units, warrants and rights use `-` (`BAC-PB`, `ABC-WT`). Drop hyphen
   codes unless the symbol list says `Common Stock` (share classes such as `BRK-B`, `BF-B` are common).
4. **Yield sanity.** `dividend_yield` is a fraction; keep `0 ≤ y ≤ 0.25` (secondary listings with values in
   the thousands exist). Convert to percent only for display. A yield screen should be confirmed from the
   dividend history (section 13).
5. **Currency.** Show `currency_symbol` with every cap and price; never rank caps across currencies; dedupe a
   company listed on several exchanges by ISIN (symbol list) when screening more than one exchange.
6. **Missing fields.** A filter on `market_capitalization`, `earnings_share`, `dividend_yield`, `sector`
   or average volume silently excludes rows where that field is absent; report "excluded for missing
   field" counts by comparing an unfiltered count per exchange.
7. **Staleness.** Rows whose `last_day_data_date` is older than the exchange's latest session are flagged.
8. **Truncation.** If a screen returns 1,000 rows, partition it into non-overlapping bands
   (`market_capitalization` ≥ lo and < hi) or exchanges until each part returns < 1,000, and check the union
   has no duplicates.

**Presets** (filters + local rules): *dividend growth* = high-dividend filters + section 13 streak ≥ 5 and
no CUT flag; *trend template* = liquid + mid/large cap shortlist + section 9.1 locally; *oversold quality* =
profitable + large cap + `Highlights.ReturnOnEquityTTM ≥ 0.15` + RSI(14) < 30 and `C > SMA_200` locally.

**Enrichment budget.** Shortlist ≤ N names; each Fundamentals call is 10, each EOD 1, each Technical API call
5. Print `5·pages + 10·N_fund + N_eod` before running.

**Acceptance checks.** No `Preferred Stock`, ETF, or five-letter F/Y OTC line appears in a "US common stock"
result; `BRK-B` survives the hyphen rule; every cap is shown with its `currency_symbol`; a yield of 3.4 (i.e.
340%) is dropped; a 1,000-row response triggers partitioning; sort strings look like
`market_capitalization.desc`.

---

## 13. Dividend screens and the dividend monitor

**Use when** screening dividend growers or value-income stocks, and watching a dividend portfolio for
deterioration. Complements [funds-income](funds-income.md#dividend-and-income-tracker).

**EODHD inputs.** `/api/div/{SYM}?fmt=json` (1 call; **pass `fmt=json`** — CSV keeps only date and adjusted
amount): `date` (ex-date), `value` (split-adjusted, today's share terms), `unadjustedValue` (amount actually
paid then), `period` (`Quarterly`, `Interim`, `Final`, `Special`, `Other`, or null), `currency`,
`declarationDate`, `recordDate`, `paymentDate`. Fundamentals `SplitsDividends`
(`ForwardAnnualDividendRate`, `ForwardAnnualDividendYield`, `PayoutRatio`, `NumberDividendsByYear`),
`Highlights` (`EarningsShare`, `DilutedEpsTTM`), `Financials::Cash_Flow` for FCF; price from EOD or live.

**Method — screening metrics.**
1. **Classify** each payment: `Special`/`Other` labels → special; an unlabelled amount > 1.5 × median of
   the last 8 regular amounts → special with flag `amount_outlier`; otherwise regular.
2. **Frequency** f = regular payments in the last 24 months / 2, rounded.
3. **Forward regular yield** = latest regular `value` × f / current raw price (same currency: LSE prices can
   be GBX while dividends are GBP — normalize first, see [data-semantics](data-semantics.md#units-and-currencies)).
   For `Interim`/`Final` payers (unequal halves) use the regular sum of the last 12 months instead.
   TTM yield including specials is reported separately, never as the forward yield.
4. **Growth**: 3- and 5-year CAGR of complete calendar-year regular sums of `value` (split-safe);
   `CAGR = (S_end/S_start)^(1/years) − 1`.
5. **Streak**: consecutive complete years with a higher regular sum than the prior year; stop at an
   incomplete year (fewer than f payments) — unscored, not a break or a raise.
6. **Payout triad**: `DPS_TTM / EPS_TTM` (GAAP, from statements), `/ adjusted EPS` (`Highlights`), and
   `dividends paid / FCF` with FCF = operating cash flow − capex (signs normalized; see
   [methods-fundamentals-valuation](methods-fundamentals-valuation.md)). REIT FFO payout only when net income, real-estate D&A
   and gains on sale are present; otherwise "FFO not computable". **FCF growth**: CAGR of annual FCF over 3 and
   5 fiscal years, `(FCF_t / FCF_{t−n})^{1/n} − 1`, computed only when both endpoints are positive (otherwise
   "not meaningful"), and the count of years in the window with FCF ≥ dividends paid.
7. **Balance sheet and value**: debt/equity, current ratio, P/E, P/B, P/E × P/B (≤ 22.5 is the Graham
   product bound); revenue/EPS 3-year trend.
8. **Timing (optional)**: RSI(14) pullback (< 40) while `C > SMA_200`.
9. **Composite**: percentile of each metric within the screened universe, declared weights, missing ≠ zero.

**Method — monitor flags** (same-slot comparison: each regular payment against the payment with the same
`period` label 320–410 days earlier, using split-adjusted `value`):

| Flag | Rule | Monitor state |
|---|---|---|
| CUT | latest same-slot change < −0.5% | REVIEW |
| SUSPENSION_SUSPECTED | no regular ex-date for > 1.5 × 365/f days | REVIEW |
| FREEZE | last 4 same-slot changes all within ±0.5% after a growth history | WARN |
| PAYOUT_STRETCH | FCF payout > 100% or EPS payout > 90% (REITs/utilities: declared sector thresholds) | WARN |
| SPECIAL_ONLY_GROWTH | TTM growth driven by specials | WARN |
| none | — | OK |

Flat quarterly payments between annual raises are **not** cuts (the same-slot rule handles this). Deduplicate
alerts by (symbol, flag, triggering ex-date). A flag never triggers an automatic sale; it creates a review
item with the evidence rows.

```python
import datetime as dt, statistics as st

def classify_dividends(divs, special_mult=1.5):
    out = []
    for r in sorted((dict(x) for x in divs if x.get("value") is not None), key=lambda x: x["date"]):
        recent = [x["value"] for x in out[-8:] if x["kind"] == "regular"]
        if (r.get("period") or "").lower() in ("special", "other"):
            r["kind"] = "special"
        elif len(recent) >= 4 and r["value"] > special_mult * st.median(recent):
            r["kind"], r["flag"] = "special", "amount_outlier"
        else:
            r["kind"] = "regular"
        out.append(r)
    return out

def payments_per_year(rows, as_of, years=2):
    start = (as_of - dt.timedelta(days=365 * years)).isoformat()
    n = sum(r["kind"] == "regular" and start < r["date"] <= as_of.isoformat() for r in rows)
    return round(n / years)

def forward_regular_yield(rows, price, as_of):
    reg = [r for r in rows if r["kind"] == "regular" and r["date"] <= as_of.isoformat()]
    f = payments_per_year(rows, as_of)
    if not reg or not f or not price:
        return None
    if {r.get("period") for r in reg[-f:]} & {"Interim", "Final"}:
        start = (as_of - dt.timedelta(days=365)).isoformat()
        return sum(r["value"] for r in reg if r["date"] > start) / price
    return reg[-1]["value"] * f / price
```

**Acceptance checks.** Quarterly 0.26 × 4 at price 10.40 → forward yield 0.10; a payment of 1.00 labelled
`Special` is excluded from the forward yield; 0.26 → 0.13 same-slot → CUT; four unchanged same-slot payments →
FREEZE; quarterly sums 0.80/0.88/0.96/1.04 over four complete years → streak 3; an ex-date gap of 203 days for
a quarterly payer → SUSPENSION_SUSPECTED.

**Monitor flags — extra dividend-specific triggers.** These rows add price, news and insider evidence to
the payment-based flags above. Holdings-level triggers that are not dividend-specific (band drift,
concentration, lot losses, upcoming events) belong to the general trigger catalogue in
[methods-performance-risk §11.4](methods-performance-risk.md); do not duplicate them here. That catalogue names the
same two ideas `REL_DRAWDOWN` and `NEWS_CLUSTER`; when both run, emit one flag per idea (these names map
one-to-one: `RELATIVE_DRAWDOWN` ↔ `REL_DRAWDOWN`, `MATERIAL_NEWS` ↔ `NEWS_CLUSTER`).

| Flag | Rule (defaults are heuristics) | Monitor state |
|---|---|---|
| RELATIVE_DRAWDOWN | `(1 + R_stock)/(1 + R_index) − 1` over 126 sessions (≈ 6 months) on adjusted closes, index = the declared benchmark (e.g. `GSPC.INDX`) ≤ −20% | WARN; ≤ −35% → REVIEW |
| MATERIAL_NEWS | ≥ 1 deduplicated news cluster in the last 10 sessions matching the declared dividend-risk keyword list (dividend cut/suspension, going concern, restatement, credit rating downgrade, covenant breach, bankruptcy, guidance cut), or abnormal news volume z ≥ 2 ([events-news](events-news.md#abnormal-news-volume-and-topic-weights)) | WARN; ≥ 2 distinct matching clusters or a rating downgrade → REVIEW |
| INSIDER_SELLING | US only. Form 4 non-derivative rows over 90 days with `transaction_code = S` and `acquired_or_disposed = D`: ≥ 2 distinct `reporting_owner_cik` with sales **not** footnoted as Rule 10b5-1 plan sales, and net value Σ sales − Σ purchases (`P`) ≥ a declared floor (default 1,000,000 in listing currency) | WARN |

Inputs: EOD for the stock and benchmark (1 call each); news per ticker (5 calls) clustered as in
[app-ai-patterns §10](app-ai-patterns.md#10-news-rag-specifics); Form 4 from
`/api/sec-filings/{SYM}/form4` (10 calls per page of up to 100 filings; Fundamentals Data Feed or All-In-One).
The Form 4 schema has no plan flag: detect 10b5-1 sales from footnote text containing "10b5-1" and label
the result. `total_value` can be null; use `shares_amount × price_per_share`. Keyword matching is a
labelled judgement; show the matched headlines with links. The state is the most severe flag; deduplicate
by (symbol, flag, window end).

```python
def dividend_extra_flags(rel_ret_126, news_clusters_10d, news_z, insider_rows_90d, sale_value_floor=1e6):
    """news_clusters_10d: dicts {id, risk_keywords: [...]}; insider rows: dicts
    {owner_cik, code, ad, value, plan_10b5_1}."""
    flags = []
    if rel_ret_126 is not None:
        if rel_ret_126 <= -0.35: flags.append(("RELATIVE_DRAWDOWN", "REVIEW"))
        elif rel_ret_126 <= -0.20: flags.append(("RELATIVE_DRAWDOWN", "WARN"))
    risky = [c for c in news_clusters_10d if c["risk_keywords"]]
    if len(risky) >= 2 or any("credit rating downgrade" in c["risk_keywords"] for c in risky):
        flags.append(("MATERIAL_NEWS", "REVIEW"))
    elif risky or (news_z is not None and news_z >= 2):
        flags.append(("MATERIAL_NEWS", "WARN"))
    sales = [r for r in insider_rows_90d if r["code"] == "S" and r["ad"] == "D"]
    buys = [r for r in insider_rows_90d if r["code"] == "P" and r["ad"] == "A"]
    discretionary = [r for r in sales if not r.get("plan_10b5_1")]
    net = sum(r["value"] for r in sales) - sum(r["value"] for r in buys)
    if len({r["owner_cik"] for r in discretionary}) >= 2 and net >= sale_value_floor:
        flags.append(("INSIDER_SELLING", "WARN"))
    state = "REVIEW" if any(s == "REVIEW" for _, s in flags) else ("WARN" if flags else "OK")
    return state, flags
```

**Acceptance checks (extra triggers).** Relative return −22% and nothing else → WARN
(`RELATIVE_DRAWDOWN`); −40% → REVIEW. One "dividend cut" cluster plus discretionary sales of 800,000 and
600,000 by two insiders and a 5,000,000 plan sale by a third → WARN with `MATERIAL_NEWS` and
`INSIDER_SELLING`; if only the plan sale existed, `INSIDER_SELLING` does not fire.

---

## 14. GARP, value and quality screens

**Use when** screening for growth at a reasonable price, deep value or quality. Formulas are kept brief here;
statement-level definitions, sign conventions and period handling are in
[fundamentals](fundamentals.md#core-calculations), [valuation](valuation.md) and the full ratio library in [methods-fundamentals-valuation](methods-fundamentals-valuation.md).

**EODHD inputs.** Screener for a bounded candidate pool (section 12), then Fundamentals per name (10 calls):
`Highlights` (`PERatio`, `PEGRatio`, `EarningsShare`, `EPSEstimateCurrentYear/NextYear`,
`ReturnOnEquityTTM`), `Valuation` (`TrailingPE`, `ForwardPE`, `EnterpriseValue`, `PriceBookMRQ`),
`Earnings::Trend` (forward EPS by period), `Financials` (quarterly/yearly statements), `outstandingShares`.

**Method.**

| Screen | Rule set (defaults) |
|---|---|
| GARP | PEG = P/E ÷ (expected EPS growth in %) with P/E and growth on the **same EPS basis and horizon** (forward P/E with next-year growth from `Earnings::Trend`); PEG ≤ 1.5; EPS growth 10–40%; ROE ≥ 0.15 |
| SBC-adjusted FCF yield | `(OCF − capex − stockBasedCompensation) / market cap` from `Cash_Flow`; ≥ 4% |
| EV/FCF, net debt/EBITDA | EV from `Valuation.EnterpriseValue` (current) or rebuilt; net debt/EBITDA ≤ 3 |
| Dilution | diluted-share CAGR from `outstandingShares` over 3 years ≤ 2% per year |
| Graham number | `√(22.5 × EPS × BVPS)` (both positive, same currency); value if price < Graham number |
| Graham defensive (subset) | current ratio ≥ 2; positive EPS each of 10 years; dividends 20 years (only where history exists, else unscored); P/E × P/B ≤ 22.5 |
| Piotroski F-score | 9 binary tests on two consecutive fiscal years (ROA > 0, CFO > 0, ΔROA > 0, CFO > NI, Δleverage < 0, Δcurrent ratio > 0, no new shares, Δgross margin > 0, Δasset turnover > 0); 8–9 strong, 0–2 weak |
| Earnings yield + return on capital rank | rank by EBIT/EV and by EBIT/(net working capital + net fixed assets); combined rank |

Gates output **eligible / conditional / review** (conditional = one input unscored, review = a data
inconsistency such as negative equity making P/B meaningless). An empty result is reported as "no qualifying
candidates", not padded with near misses.

**Pitfalls.** Statement currency can differ from listing currency; Fundamentals are restated current values
(no point-in-time), so historical screens built on them carry look-ahead; negative EPS or equity invalidates
multiples instead of ranking them "cheap".

**Acceptance checks.** EPS 4, BVPS 25 → Graham number = √2250 = 47.43; a loss-making company is excluded from
PEG ranking with reason; each candidate shows the fields and dates used.

---

## 15. Market overview / daily recap recipe

**Use when** "How's the market?" or a daily wrap: indices, sectors, movers, rates, commodities, macro and a
risk-on/off checklist in one dated summary.

**EODHD inputs and call budget** (EOD plan for prices; Fundamentals for macro/economic events):

| Block | Source | Calls |
|---|---|---|
| Indices | EOD `GSPC`, `DJI`, `IXIC`, `NDX`, `VIX`, `GDAXI`, `FCHI`, `N225`, `AXJO`, `HSI`, `STOXX50E` `.INDX` (check each code's last date in `exchange-symbol-list/INDX`) | 1 each |
| Sectors | Sector ETFs XLK, XLF, XLV, XLY, XLP, XLE, XLI, XLB, XLU, XLRE, XLC `.US` (labelled proxies) | 1 each (cheaper than bulk with `symbols=` = 100 + N) |
| Movers | Screener `sort=refund_1d_p.desc/asc` on `nyse`/`nasdaq` with `adjusted_close > 5` and `avgvol_1d` floor | 5 per list |
| Full breadth (optional) | `eod-bulk-last-day/US` today and the prior session (whole-exchange rows lack `change_p`) | 100 per day |
| Rates | `/api/ust/yield-rates?filter[year]=YYYY` (+ `ust/bill-rates`, real yields) | per endpoint page |
| Commodities | `/api/commodities/historical/{WTI,BRENT,NATURAL_GAS}?interval=daily`; metals/agriculture monthly only | per series |
| FX | `EURUSD.FOREX`, `USDJPY.FOREX`, `XAUUSD.FOREX` | 1 each |
| Calendar | `economic-events` with `from/to` and `country`; `calendar/earnings` for today/tomorrow | per plans-limits |

**Method.**
1. Determine the as-of session per region from the returned `date` (Asia and Europe close earlier; US bars
   finalize after ~16:15 ET in rounds). Every row shows its own as-of date.
2. Day change = `C_t/C_{t−1} − 1` (indices: `close`, `adjusted_close == close`); YTD change from the **last
   close of the prior year**; for ETFs use `adjusted_close` for total return and say so.
3. Movers: apply section 12 cleaning (type join, no hyphen preferreds, liquidity floor) before listing.
4. Curve: `2s10s = 10Y − 2Y` and `3m10y = 10Y − 3M` in percentage points; day change in bp; shape label
   (inverted if `2s10s < 0`).
5. Commodities: WTI/Brent/Henry Hub daily series lag up to a week (published in weekly batches); show the
   observation date. Never use `.COMM` symbols (phased out); GLD/USO are ETF proxies if labelled.
6. Risk-on/off checklist (each item with direction rule and value): VIX level and 1-year percentile; USDJPY
   change (yen strength = risk-off); gold vs oil; 10Y change; index vs 50/200-SMA; breadth (ADVN−DECN) and
   section 8 posture score if available.
7. Unsupported requests are named, not silently dropped: FTSE indices (FTSE 100, FTSE MIB, …) and current
   Russell indices (Russell 2000 / `RUT`) are not available; offer constituents individually or an ETF proxy
   (e.g. IWM for small caps) labelled as a proxy.
8. Movers with gaps, volume surges and new 52-week extremes, written to the outcome ledger, are section 19.
   Before the recap is shared with anyone, run the section 24 checks.

**Acceptance checks.** Every row has an as-of date and unit (%, pp, bp); proxies are labelled; a request for
the Russell 2000 returns the boundary sentence plus the proxy option; the printed call budget matches the
requests made.

---

## 16. Single-stock decision workflow

**Use when** a user asks "should I look at X" and wants a structured, auditable brief — mechanical baseline,
sourced outlook, trade levels and a valuation range kept apart. The output is analysis, not a
recommendation.

**Inputs.** `as_of` date, horizon (20/60/120 sessions), benchmark, ≥ 5 peers (same industry/region from
Fundamentals `General`), position state (flat or held), user loss budget. EODHD: EOD (1 per symbol),
Fundamentals (10 per symbol), `calendar/earnings`, `calendar/trends` (current only), news (5 per ticker),
`AnalystRatings` (US).

**Method.**
1. **Identity and figure check.** Resolve `General.Type`, currency, primary listing. Check
   `|price × SharesOutstanding − Highlights.MarketCapitalization| / MarketCapitalization ≤ 5%` with matching
   currency and share basis; a failure blocks the brief until explained (units, GBX, share class).
2. **Factor score** (percentile within peers + the stock, declared weights): momentum (`ROC_126` skipping the
   last 21 sessions, adjusted), value (earnings and FCF yield), quality (ROE, gross-margin stability, accruals),
   revisions (change in `Earnings::Trend` forward EPS between **your own** dated snapshots — EODHD keeps no
   estimate history; without snapshots this factor is unscored). Report each percentile and coverage.
3. **Sourced outlook.** Each claim carries its source and date: consensus EPS/revenue from `Earnings::Trend`,
   next report from `calendar/earnings`, analyst target/ratings, specific news items (link and publication
   time), insider activity. Separate observation, calculation and judgement.
4. **Trade levels** (raw prices): entry reference, stop = entry − k·ATR_14 (Wilder, adjusted OHLC; k
   scenarios 1.5/2/3) or a structural level from section 5, R targets at 1/2/3R, time exit at the horizon,
   size = loss budget ÷ (entry − stop) capped by liquidity and position limits (section 10). Signals use
   adjusted history; executable levels use raw prices.
5. **Probabilities only after calibration.** Map score → probability of a declared outcome (e.g. "+1R hit
   before stop within the horizon") with an expanding-window calibration (logistic or isotonic fit on past
   signals only). Report Brier score `BS = (1/N) Σ (p_i − o_i)²`, its reference `BS_ref = ō(1 − ō)` (base
   rate ō), skill `1 − BS/BS_ref`, sample size N and a reliability table (10 bins). With no calibration file,
   or N < 100 resolved outcomes, output a **relative score**, never a probability.
6. **Fair-value range, separate from trade levels.** Bear/base/bull values with method (DCF, multiples, DDM),
   assumptions and date ([valuation](valuation.md)); never place a stop or target at a fair-value number.
7. **Held positions: thesis-change log.** Append-only rows: date, data point, class (`new_fact`,
   `valuation_change`, `wording_change`, `data_correction`), pillar affected, conviction before/after, action
   (`none`/`review`/`exit-plan`). A data correction (restated fundamentals, revised adjusted prices) never
   counts as new evidence.

**Acceptance checks.** A synthetic panel (entry 100, ATR 2, k = 2, loss budget 1,000) yields stop 96, R = 4,
250 shares, targets 104/108/112; a probability field is present only when a calibration file with N ≥ 100
exists; a held-position update lists change classes; the fair-value table and the trade-level table are
separate objects.

---

## 17. Sector cycle phase and rotation

**Use when** a user asks which phase of the business cycle sector leadership suggests, wants a rotation
read with evidence for and against, or wants overbought/oversold sector flags. The leadership map below is
a **stylised heuristic**; real cycles often break it. The output is a labelled reading, not a forecast.

**EODHD inputs.**

| Need | Source | Cost |
|---|---|---|
| Sector proxies | EOD `adjusted_close` of XLK, XLF, XLV, XLY, XLP, XLE, XLI, XLB, XLU, XLRE, XLC `.US` (labelled ETF proxies) | 1 call each |
| Benchmark | `SPY.US` (or `GSPC.INDX`, price only) | 1 |
| Curve | `/api/ust/yield-rates?filter[year]=YYYY` (2Y, 10Y; `rate` in percent) | per endpoint page |
| Labour and inflation | `economic-events` US "Unemployment Rate", "Inflation Rate" (`comparison=yoy`), keyed as in [methods-options-rates-macro C5](methods-options-rates-macro.md#c5-economic-events-call-rules-fields-and-impact-tiers) | 1 per page |
| Credit | `HYG.US`, `LQD.US` adjusted closes (labelled proxy) | 1 each |
| Sector uptrend ratio | Section 6 step 5 (constituents + `General.Sector`) | see section 6 |

**Method.**
1. **Relative strength.** For each sector ETF and horizon h ∈ {5, 21, 63} sessions (≈ 1 week, 1 month,
   3 months): `RS_h = (C_t/C_{t−h}) / (B_t/B_{t−h}) − 1` on adjusted closes, B = benchmark. Composite
   `RS = 0.2·RS_5 + 0.3·RS_21 + 0.5·RS_63`; convert to a percentile across the 11 sectors (`rank/n`).
2. **Leadership map and macro rules** (declared in config; each macro rule votes +1 agree, −1 disagree,
   0 if its input is missing; the phase's macro vote `V_p` is the mean of its votes):

   | Phase | Leaders | Macro confirmations |
   |---|---|---|
   | early | XLF, XLY, XLI, XLRE | 10Y − 2Y rising over 63 sessions from < 0.5 pp; unemployment ≥ its 12-month mean with 3-month change ≤ 0; HYG/LQD 63-session return > 0 |
   | mid | XLK, XLC, XLI | 10Y − 2Y > 0.5 pp with \|63-session change\| < 0.25 pp; unemployment 3-month change < 0; CPI yoy within 1 pp of its 12-month mean |
   | late | XLE, XLB, XLP | CPI yoy above its 12-month mean and rising; 10Y − 2Y falling over 63 sessions; unemployment at a 24-month low |
   | recession | XLU, XLP, XLV | 10Y − 2Y < 0, or rising fast out of inversion; unemployment 3-month change ≥ +0.3 pp; HYG/LQD 63-session return < 0 |

3. **Phase score.** Price part `P_p` = mean RS percentile of the phase's leaders. With macro data,
   `S_p = 0.7·P_p + 0.3·(V_p + 1)/2`; without, `S_p = P_p`. The top phase is reported only if it beats the
   second by ≥ 0.10; otherwise the reading is `mixed/transition`.
4. **Evidence lists (always both).** Confirming: the top phase's leaders in the top third by RS, and macro
   rules voting +1. Contradicting: its leaders in the bottom third, and macro rules voting −1.
5. **Overbought / oversold sector flags.** Per sector, the percentile of today's uptrend ratio within its own
   history (≥ 3 years, excluding today): `overbought` if percentile ≥ 0.90 and ratio ≥ 0.70; `oversold` if
   percentile ≤ 0.10 and ratio ≤ 0.30.
6. **Probabilities** appear only as stated judgement ("judgement: early 50%, mid 30%, …", summing to 100%),
   or from a calibration backtest (section 16 step 5). Never present the score itself as a probability.

```python
import pandas as pd

PHASES = {"early": ["XLF", "XLY", "XLI", "XLRE"], "mid": ["XLK", "XLC", "XLI"],
          "late": ["XLE", "XLB", "XLP"], "recession": ["XLU", "XLP", "XLV"]}

def rel_strength(px, bench, horizons=(5, 21, 63), w=(0.2, 0.3, 0.5)):
    """px: adjusted closes (sessions x ETFs); bench: adjusted closes of the benchmark."""
    rs = sum(wi * ((px.iloc[-1] / px.iloc[-1 - h]) / (bench.iloc[-1] / bench.iloc[-1 - h]) - 1)
             for h, wi in zip(horizons, w))
    return rs.rank(pct=True)

def cycle_phase(rs_pct, macro_votes=None, w_price=0.7, min_margin=0.10):
    price = {p: rs_pct.reindex(m).dropna().mean() for p, m in PHASES.items()}
    score = ({p: w_price * price[p] + (1 - w_price) * (macro_votes.get(p, 0) + 1) / 2 for p in PHASES}
             if macro_votes else price)
    (top, s1), (_, s2) = sorted(score.items(), key=lambda kv: -kv[1])[:2]
    top3 = set(rs_pct.sort_values(ascending=False).index[:len(rs_pct) // 3])
    bot3 = set(rs_pct.sort_values().index[:len(rs_pct) // 3])
    return {"phase": top if s1 - s2 >= min_margin else "mixed/transition",
            "scores": {k: round(float(v), 3) for k, v in score.items()},
            "confirming": sorted(set(PHASES[top]) & top3),
            "contradicting": sorted(set(PHASES[top]) & bot3)}

def sector_extremes(uptrend_hist, lo_pct=0.10, hi_pct=0.90, lo_abs=0.30, hi_abs=0.70):
    today, hist = uptrend_hist.iloc[-1], uptrend_hist.iloc[:-1].dropna()
    pct = float((hist < today).mean())
    if pct >= hi_pct and today >= hi_abs: return "overbought", pct
    if pct <= lo_pct and today <= lo_abs: return "oversold", pct
    return "neutral", pct
```

**Pitfalls.** Macro rows are dated by release time (`date` in economic events), not by reference period; a
signal on day *t* may use only releases published before *t*. XLRE and XLC have much shorter histories than
the original nine sector ETFs, and the 2018 sector reshuffle moved large names into XLC: check the first EOD
date of each ETF and do not splice RS across the change. Sector ETFs are cap-weighted and concentrated; one
holding can drive a sector's RS. Sector labels are current classifications. XLI and XLP appear in two phases
on purpose.

**Acceptance checks.** RS percentiles XLF 0.95, XLY 0.90, XLI 0.80, XLRE 0.70, XLK 0.60, XLC 0.50, XLB 0.40,
XLE 0.30, XLP 0.20, XLV 0.15, XLU 0.10 → phase `early` (scores early 0.838, mid 0.633, late 0.30, recession
0.15), confirming XLF, XLI, XLY, no contradicting leaders. Adding macro votes early +1, late −1, recession −1
keeps `early` (0.886). All percentiles near 0.5 → `mixed/transition`. An uptrend-ratio history spread
evenly over 0.20–0.60 with today at 0.75 → `overbought`; a history over 0.30–0.60 with today at 0.25 →
`oversold`.

---

## 18. Theme baskets: detection, heat and lifecycle

**Use when** "what themes are hot?", tracking a theme (AI hardware, uranium, GLP-1, defence) or listing its
leading stocks. A theme here is a **declared basket**, not something discovered by the model; the model may
only propose candidate baskets for the user to declare.

**EODHD inputs.** Members from a user list, the Screener `industry` field (5 calls per page, current values)
or `General.Industry` (Fundamentals, 10 calls each); EOD per member (1 call each) or your bulk archive;
news per member (5 calls per ticker) or by topic `t=` (5 calls); `/api/news-word-weights` for candidate
keywords (5 + 5 per ticker).

**Method.**
1. **Declare** each basket: `theme_id`, name, members (`CODE.EXCHANGE`), source (user list, or industry
   query with its date), keyword set, `as_of`. Membership is current unless the user keeps dated versions;
   say so.
2. **Basket index**: equal-weight daily return = mean of member adjusted-close returns that exist that day
   (no zero fill), chained to a level. Optional cap weights with a per-name cap (e.g. 10%), labelled as using
   current market caps.
3. **Momentum**: excess return over the benchmark for h ∈ {5, 21, 63, 126} sessions; `p_h` = percentile of
   that excess return across all declared themes on the date; momentum component = mean(`p_21`, `p_63`).
4. **Breadth**: share of members with `C > SMA_50` (members with 50 valid bars only) and its 10-session
   change.
5. **Volume**: median across members of `SMA_10(V)/SMA_50(V)`.
6. **News**: deduplicated clusters per theme per session ([app-ai-patterns §10](app-ai-patterns.md#10-news-rag-specifics));
   a cluster counts if a member is in `symbols`, or if two theme keywords hit the title or content (one
   keyword alone gives too many false positives). Abnormal news volume z as in
   [events-news](events-news.md#abnormal-news-volume-and-topic-weights). To **propose** a new theme, look
   for terms that newly enter the top 20 word weights of ≥ 3 different tickers in the same window; the user
   decides whether to declare a basket.
7. **Heat** = 100 × Σ w_k·pct_k / Σ_scored w_k, with percentiles across themes and weights momentum 0.40,
   breadth 0.30, volume 0.15, news 0.15 (`composite()` from 9.3); report coverage.
8. **Lifecycle label** (checked in this order; percentiles across themes):
   - `extended`: leading, and median member `C/SMA_50 − 1` ≥ 15% or (heat ≥ 90 and news z ≥ 2);
   - `leading`: `p_63 ≥ 0.7`, `p_126 ≥ 0.7` and breadth ≥ 0.6;
   - `emerging`: `p_21 ≥ 0.7`, `p_126 < 0.5` and breadth rising;
   - `fading`: `p_126 ≥ 0.6`, `p_21 ≤ 0.3` and breadth falling;
   - otherwise `neutral`.
9. **Leading stocks**: members with `C > SMA_50`, ranked by 63-session RS, after the liquidity floor of
   section 12; show the top 5 with their values.
10. **Confidence**: `high` if ≥ 10 members and data coverage ≥ 0.9; `low` if < 5 members or coverage < 0.7;
    otherwise `medium`.

```python
THEME_W = {"momentum": .40, "breadth": .30, "volume": .15, "news": .15}

def theme_heat(pcts):
    v, cov = composite(pcts, THEME_W)            # composite() from 9.3
    return round(100 * v, 1), round(cov, 2)

def lifecycle(p21, p63, p126, breadth, breadth_chg, ext50, heat, news_z=None, ext_max=0.15):
    leading = p63 >= .7 and p126 >= .7 and breadth >= .6
    if leading and (ext50 >= ext_max or (heat >= 90 and (news_z or 0) >= 2)): return "extended"
    if leading: return "leading"
    if p21 >= .7 and p126 < .5 and breadth_chg > 0: return "emerging"
    if p126 >= .6 and p21 <= .3 and breadth_chg < 0: return "fading"
    return "neutral"
```

**Pitfalls.** A basket assembled from today's winners has look-ahead: its backtested momentum is inflated.
Industry labels are current. In cap-weighted baskets one mega-cap dominates; show equal weight beside it.
Theme ETFs, where they exist, are fine as labelled proxies but their holdings are a current snapshot
(`ETF_Data`). Heat ranks themes against each other; it is not an absolute strength measure.

**Acceptance checks.** `lifecycle(0.8, 0.4, 0.3, 0.5, +0.1, 0.05, 60)` → `emerging`;
`(0.8, 0.8, 0.9, 0.7, 0, 0.05, 70)` → `leading`; the same with median extension 0.20 → `extended`;
`(0.2, 0.6, 0.7, 0.5, −0.1, 0.02, 50)` → `fading`. Heat with momentum 0.9, breadth 0.8, volume 0.6 and no
news data → 81.2, coverage 0.85.

---

## 19. Daily big-movers and gap scan feeding the outcome ledger

**Use when** a nightly job should list the day's big movers, gaps, volume surges and new 52-week
highs/lows, attach a catalyst label and record each as a hypothesis whose outcome is tracked later.

**EODHD inputs.**

| Need | Source | Cost |
|---|---|---|
| Today and the prior session, whole exchange | `/api/eod-bulk-last-day/{EX}?filter=extended` and the same with `&date=` for the prior session | 100 calls each (the filter costs nothing extra) |
| Type, name, 50-day average volume, 250-day high/low | the `extended` fields `type`, `name`, `avgvol_50d`, `hi_250d`, `lo_250d` (valid for the last 30 days only; older dates return 0 — never backfill with them) | included |
| Same-day splits | `/api/eod-bulk-last-day/{EX}?type=splits` | 100 |
| Earnings timing | `/api/calendar/earnings?from=&to=` | 1 |
| Catalyst text | `/api/news?s={SYM}&from=&to=` for flagged names only | 5 per ticker |

Whole-exchange bulk rows carry no `change_p`; compute returns from the prior session's rows.

**Method.**
1. Join today's rows to the prior session's rows by code. Keep `type = Common Stock`; apply the section 12
   cleaning (hyphen codes, five-letter F/Y OTC lines); drop codes with a split today (or adjust the prior
   close by the ratio). Floors (declared): close ≥ 3 and `close × volume` ≥ 5,000,000 in listing currency.
2. Metrics: `ret = C_t/C_{t−1} − 1`, `gap = O_t/C_{t−1} − 1` (raw prices; corporate actions handled in step
   1), `vol_ratio = V_t / avgvol_50d`. New high if `H_t >` the **prior session's** `hi_250d` (avoids the
   question of whether today's bar is inside the field); new low mirrors it.
3. Flags (defaults): `mover_up` ret ≥ +20%, `mover_down` ret ≤ −20%, `gap_up`/`gap_down` |gap| ≥ 4%,
   `vol_surge` ratio ≥ 3, `new_high`, `new_low`.
4. **Catalyst label.** Earnings is deterministic: the code has a `calendar/earnings` row whose reaction
   session (section 11 step 1) is today. Otherwise map same-day news clusters to sessions as in
   [events-news](events-news.md#news-reaction-ranking-and-failed-reactions) and classify them into
   earnings, guidance, M&A, regulatory/approval, offering/dilution, analyst action, legal, sector/macro or
   `none_found`. That classification is model judgement; label it and keep the headline links.
5. **Write to the ledger** ([methods-quant-research §7.1](methods-quant-research.md#71-forward-outcome-ledger))
   as hypothesis candidates: `signal_id = sha1(date|code|rule_version|flag)`, reference price = close (raw
   and adjusted), tags = flags + catalyst, status `pending`. Outcomes mature at 1/3/5/10/20 sessions.
6. **Cohort report** by (flag, catalyst, direction): n, median forward return, hit rate with a Wilson
   interval; suppress cohorts with n < 20. Delisted names keep their records.

```python
import numpy as np
import pandas as pd

def movers_scan(today, prev, splits_today=(), move=0.20, gap=0.04, vol_x=3.0,
                min_price=3.0, min_dollar_vol=5e6):
    """today/prev: whole-exchange bulk rows with filter=extended, indexed by code."""
    t = today.join(prev[["close", "hi_250d", "lo_250d"]].add_prefix("prev_"), how="inner")
    t = t[(t["type"] == "Common Stock") & ~t.index.isin(list(splits_today))]
    t = t[~t.index.str.contains("-") & ~((t.index.str.len() == 5) & t.index.str[-1].isin(["F", "Y"]))]
    t = t[(t["close"] >= min_price) & (t["close"] * t["volume"] >= min_dollar_vol)]
    t = t.assign(ret=t["close"] / t["prev_close"] - 1, gap=t["open"] / t["prev_close"] - 1,
                 vol_ratio=t["volume"] / t["avgvol_50d"].replace(0, np.nan))
    flags = pd.DataFrame({"mover_up": t["ret"] >= move, "mover_down": t["ret"] <= -move,
                          "gap_up": t["gap"] >= gap, "gap_down": t["gap"] <= -gap,
                          "vol_surge": t["vol_ratio"] >= vol_x,
                          "new_high": t["high"] > t["prev_hi_250d"], "new_low": t["low"] < t["prev_lo_250d"]})
    t["flags"] = flags.apply(lambda r: ",".join(r.index[r.values]), axis=1)
    return t[t["flags"] != ""]
```

**Pitfalls.** A split or reverse split without the step 1 check shows as a ±50% or larger "mover". A first
trading day has no prior close. Halted names have stale rows. Penny stocks dominate raw ±20% lists, so the
floors matter. Bulk rows can be corrected later in the evening: run after the final update, and re-run
idempotently (the signal ID does not change). The cohort study inherits survivorship bias unless delisted
names stay in.

**Acceptance checks.** Six synthetic rows: AAA 10 → 12.5 (open 12, high 13 above the prior 250-day high
12.8, volume 6× average) → `mover_up, gap_up, vol_surge, new_high` with ret 0.25 and gap 0.20; CCC 10.5 → 8.0
with low 7.8 below 7.9 → `mover_down, gap_down, vol_surge, new_low` (ret −0.2381); a 2.4 close is dropped by
the price floor; a code with a split today and an ETF row are excluded; an unchanged stock produces no row.

---

## 20. Correction duration and depth across stocks

**Use when** "how long do corrections last in this sector?", "how deep do drawdowns get for small caps?",
or setting expectations for a stop or a holding period.

**EODHD inputs.** Full EOD history per listing (1 call each), **including delisted listings**
(`exchange-symbol-list/{EX}?delisted=1`); `General.Sector` (current); cap tier from historical market cap
(US NYSE/NASDAQ weekly from 2021-07-09, 10 calls) or current `Highlights.MarketCapitalization` (label it).

**Method.**
1. Per listing, on adjusted closes: track the running peak. An episode becomes **active** when the close
   falls ≥ θ below the peak (default θ = 10%; declare it). Its trough is the lowest close before recovery.
   It ends when a close regains the peak. Record peak date, trough date, `depth = 1 − trough/peak`,
   `decline_sessions` (peak → trough) and `recovery_sessions` (trough → recovery). An episode still open at
   the end is **censored** (`recovered = false`). Section 5's zigzag gives the same peaks for θ = p%.
2. Segment by sector and cap tier at episode start (declared bands, e.g. ≥ 10e9 / 2e9–10e9 / < 2e9 in USD).
   Current sector labels and current caps applied to history are retrospective assumptions; say so.
3. Per segment report episodes, censored share, depth median and 90th percentile, decline-duration median,
   and recovery median **from recovered episodes only, labelled as biased low** (long recoveries are
   still censored). Show histograms of depth and duration.
4. Survivorship: delisted listings stay in (their last episode is usually censored). Without them, label
   the table "survivorship-biased".

```python
def correction_episodes(close, theta=0.10):
    eps, peak_i, trough_i, active = [], 0, None, False
    c = close.to_numpy(float)
    def rec(end_i):
        return {"peak": close.index[peak_i], "trough": close.index[trough_i],
                "depth": 1 - c[trough_i] / c[peak_i], "decline_sessions": trough_i - peak_i,
                "recovery_sessions": None if end_i is None else end_i - trough_i,
                "recovered": end_i is not None}
    for i in range(1, len(c)):
        if c[i] >= c[peak_i]:
            if active: eps.append(rec(i))
            peak_i, trough_i, active = i, None, False
            continue
        if trough_i is None or c[i] < c[trough_i]: trough_i = i
        if 1 - c[trough_i] / c[peak_i] >= theta: active = True
    if active: eps.append(rec(None))                       # censored
    return eps

def episode_table(rows, by):
    df = pd.DataFrame(rows); g = df.groupby(by)
    return pd.DataFrame({"episodes": g.size(),
                         "censored_share": g["recovered"].apply(lambda s: 1 - s.mean()),
                         "depth_median": g["depth"].median(),
                         "depth_p90": g["depth"].quantile(.9),
                         "decline_median": g["decline_sessions"].median(),
                         "recovery_median_recovered_only": g["recovery_sessions"].median()})
```

**Pitfalls.** Price-only closes overstate depth for high-yield stocks; use `adjusted_close`. A delisting
after a takeover is not a loss; a delisting after bankruptcy often has no final print, so the depth is a
lower bound. Thinly traded listings have gaps; count sessions with data, not calendar days. Overlapping
episodes across many stocks in one crash are not independent observations; report the market-wide
episode separately.

**Acceptance checks.** Closes 100, 105, 95, 90, 99, 106, 104, 108, 100, 96.5, 97 with θ = 10% → one recovered
episode (peak 105, trough 90, depth 0.1429, decline 2 sessions, recovery 2 sessions) and one censored
episode (peak 108, trough 96.5, depth 0.1065). Three Tech episodes (depths 0.12, 0.20, 0.15; one censored) →
censored share 0.333, depth median 0.15, recovery median 20 from the two recovered episodes.

---
## 21. Combining detectors, and a per-ticker fear score

### 21.1 Multi-detector signal aggregation

**Use when** several screens or detectors (sections 9, 11, 18, 19) each emit signals and the user wants one
ranked list with conflicts shown. For combining **probability** forecasts use
[methods-quant-research §7.3](methods-quant-research.md#73-combining-several-probability-forecasts) instead.

**Inputs.** Signal rows `{detector, ticker, theme, direction (+1/−1), score, as_of, source}` from your own
detectors; declared detector weights `w_d`.

**Method.**
1. Normalize each detector's raw score to [0, 1] by its percentile within that detector's universe on the
   same `as_of` (`rank/n`). Raw scores of different detectors are never compared directly.
2. Keep signals inside the window (default 5 calendar days ending at the latest `as_of`); deduplicate by
   (ticker, theme, detector), keeping the latest.
3. Per (ticker, theme): `conviction = Σ_d w_d·p_d·dir_d / Σ_d w_d` over detectors that fired;
   `coverage = Σ_fired w_d / Σ_all w_d`.
4. **Conflict** flag when bullish and bearish signals exist for the same ticker in the window; keep the
   item, show both sides, never net them silently.
5. Rank by |conviction|, then higher coverage, then fresher `as_of`, then ticker (deterministic tie-break).
   Every row keeps its provenance list (detector, source section, `as_of`).

```python
import pandas as pd

def aggregate_signals(rows, weights, window_days=5):
    df = pd.DataFrame(rows)
    df["as_of"] = pd.to_datetime(df["as_of"])
    df["p"] = df.groupby(["detector", "as_of"])["score"].rank(pct=True, method="average")
    end = df["as_of"].max()
    df = df[df["as_of"] > end - pd.Timedelta(days=window_days)]
    df = df.sort_values("as_of").groupby(["ticker", "theme", "detector"]).tail(1)
    out = []
    for (tic, theme), g in df.groupby(["ticker", "theme"]):
        w = g["detector"].map(weights)
        out.append({"ticker": tic, "theme": theme,
                    "conviction": round(float((w * g["p"] * g["direction"]).sum() / w.sum()), 4),
                    "coverage": round(w.sum() / sum(weights.values()), 4), "fresh": g["as_of"].max(),
                    "conflict": g["direction"].nunique() > 1,
                    "provenance": list(zip(g["detector"], g["source"], g["as_of"].dt.date))})
    out = pd.DataFrame(out).assign(abs_conv=lambda x: x["conviction"].abs())
    return out.sort_values(["abs_conv", "coverage", "fresh", "ticker"],
                           ascending=[False, False, False, True]).drop(columns="abs_conv")
```

**Pitfalls.** Two detectors built on the same input (e.g. two momentum screens) double-count; group them or
cut their weights. Percentiles inside a tiny universe are coarse (3 names → 1/3, 2/3, 1). Conviction is a
ranking aid, not a probability.

**Acceptance checks.** Weights trend 0.5, PEAD 0.3, parabolic 0.2. Trend scores AAA 9, BBB 5, CCC 1 (same
day), PEAD AAA 0.5, CCC 0.9, parabolic (bearish) BBB 4, DDD 2, plus an AAA trend signal 13 days older →
AAA conviction 0.8125 (coverage 0.8; the old signal is ignored), CCC 0.5833, DDD −0.5 (coverage 0.2), BBB
0.1905 with `conflict = True`; order AAA, CCC, DDD, BBB.

### 21.2 Per-ticker fear score

> A statistically specified variant (coverage threshold, re-weighting rules) is in [methods-quant-research §4.8](methods-quant-research.md#48-per-ticker-fear-score). Use one definition per application and record which.

**Use when** "how fearful is the tape for this stock?" for a review or a contrarian watchlist. A heuristic
state measure, not a timing signal unless validated ([research-validation](research-validation.md)).

**Components** (each a percentile against the **ticker's own** trailing history — 756 sessions for price
components, all available history ≥ 120 observations for options — oriented so higher = more fear):

| Component | Definition | Source | Weight |
|---|---|---|---|
| RSI | percentile of −RSI(14) | EOD (section 3) | 0.20 |
| Drawdown | `1 − C/max(C_{t−251..t})` | EOD adjusted | 0.25 |
| Volume anomaly | `V/SMA_50(V)` on down-close days, 0 otherwise | EOD | 0.15 |
| Down-day streak | consecutive down closes ending *t* | EOD | 0.10 |
| IV rank | [methods-options-rates-macro A7](methods-options-rates-macro.md#a7-iv-rank-and-iv-percentile) (US options, history from Q4 2023) | Marketplace options | 0.20 |
| Put/call volume | Σ put volume / Σ call volume across the chain for the date | Marketplace `options/eod` (`type`, `volume`) | 0.10 |

Score = 100 × weighted mean of available percentiles (`composite()` from 9.3); unavailable if coverage
< 0.6. Bands (heuristic): ≥ 80 extreme fear, 60–80 elevated, 40–60 neutral, 20–40 calm, < 20 complacent.
Non-US listings have no options inputs, so their maximum coverage is 0.70.

```python
FEAR_W = {"rsi": .20, "drawdown": .25, "volume": .15, "streak": .10, "iv_rank": .20, "put_call": .10}

def fear_score(pcts, weights=FEAR_W, min_cov=0.6):
    v, cov = composite({k: x for k, x in pcts.items() if x is not None}, weights)
    if v is None or cov < min_cov:
        return None, round(cov, 2), "unavailable"
    s = 100 * v
    band = ("extreme fear" if s >= 80 else "elevated" if s >= 60 else "neutral" if s >= 40
            else "calm" if s >= 20 else "complacent")
    return round(s, 1), round(cov, 2), band
```

**Acceptance checks.** Percentiles RSI 0.9, drawdown 0.95, volume 0.8, streak 0.7, no options data → 86.8,
coverage 0.70, `extreme fear`. Only RSI and streak available → `unavailable` (coverage 0.30).

---

## 22. Bubble-risk score (heuristic)

**Use when** a user asks for a "bubble meter" for the US market. Several classic inputs (market-wide put/call
ratio, margin debt, fund flows) are **not EODHD data**: they are dropped and the weights re-normalize, or the
user supplies them as dated inputs. The score is a labelled heuristic, never a crash probability.

**Components** (index = `GSPC.INDX`; each sub-score 0–100, higher = more bubble-like):

| Component | Formula | Sub-score | Default weight |
|---|---|---|---|
| Volatility complacency | percentile `p` of `VIX.INDX` close over 756 sessions | `100·(1 − p)` | 0.20 |
| IPO activity | `r` = IPO count in the last 3 months ÷ median 3-month count over the prior 3 years, counting `calendar/ipos` rows on US exchanges with `deal_type` Priced (or `offer_price > 0`) | 1.0 → 0, 1.5 → 50, 2.0 → 100 (linear, clamped) | 0.15 |
| Breadth divergence | index distance to its 252-session closing high `δ`, % of members above the 200-day SMA `b` (section 6) | 100 if δ ≤ 2% and b < 60%; 50 if δ ≤ 5% and b < 70%; else 0 | 0.20 |
| Price acceleration | `ROC_63(t) − ROC_63(t−63)` (ROC of ROC), percentile over 2,520 sessions | `100·pct` | 0.20 |
| Distance above the 200-day SMA | `C/SMA_200 − 1` | 5% → 0, 10% → 50, 15% → 100 | 0.25 |
| *User-supplied (optional)* | market-wide put/call (inverted percentile), margin-debt YoY growth percentile | `100·pct` | 0.10 each |

`Score = Σ w·s / Σ_scored w` (`composite()` from 9.3) plus an optional **qualitative adjustment** of at most
±10 points, each with a written reason. Bands: < 30 low, 30–50 normal, 50–70 elevated, ≥ 70 high. Report
coverage and each component with its as-of date. The IPO calendar's history depth is not documented here;
verify the earliest returned year with a probe before computing a 3-year baseline.

```python
BUBBLE_W = {"vix": .20, "ipo": .15, "breadth_div": .20, "accel": .20, "dist200": .25}

def bubble_components(vix_pct, ipo_ratio, idx_to_high, pct_above_200, accel_pct, dist200):
    return {"vix": 100 * (1 - vix_pct),
            "ipo": interp(ipo_ratio, [1.0, 1.5, 2.0], [0, 50, 100]),
            "breadth_div": 100 if (idx_to_high <= .02 and pct_above_200 < .60) else
                           50 if (idx_to_high <= .05 and pct_above_200 < .70) else 0,
            "accel": 100 * accel_pct,
            "dist200": interp(dist200, [.05, .10, .15], [0, 50, 100])}

def bubble_score(comp, weights=BUBBLE_W, user=None, user_w=None, adj=0, adj_cap=10):
    comp, weights = dict(comp), dict(weights)
    for k, v in (user or {}).items():
        comp[k] = v; weights[k] = (user_w or {}).get(k, .10)
    v, cov = composite(comp, weights)
    s = max(0, min(100, v + max(-adj_cap, min(adj_cap, adj))))
    band = "high" if s >= 70 else "elevated" if s >= 50 else "normal" if s >= 30 else "low"
    return round(s, 1), round(cov, 2), band
```

**Acceptance checks.** VIX percentile 0.10, IPO ratio 1.8, index 1% below its high with 55% of members above
the 200-day SMA, acceleration percentile 0.85, distance 12% → sub-scores 90, 80, 100, 85, 70 and score
**84.5** (`high`). Adding a user put/call sub-score of 70 at weight 0.10 → 83.2. A requested +25 qualitative
adjustment is capped at +10 → 94.5.

---

## 23. Crypto regime recipe and crypto fundamentals fields

**Use when** "is crypto risk-on?", or a crypto dashboard needs supply, market-cap or dominance fields.

**EODHD inputs.**

| Need | Source | Notes |
|---|---|---|
| Prices | EOD `BTC-USD.CC` and a **declared** top-N `.CC` list (1 call each) | every UTC day; volume aggregated from the top 15 crypto exchanges ([crypto notes](api/general/crypto-data-notes.md)) |
| Snapshot fields | `/api/fundamentals/{SYM}.CC?filter=Statistics` (10 calls) | `MarketCapitalization`, `MarketCapitalizationDiluted`, `CirculatingSupply`, `TotalSupply`, `MaxSupply`, `MarketCapDominance` (% of total crypto market cap), `HighAllTime`, `LowAllTime` — **current snapshot only** ([fields](api/general/fundamentals-crypto-currency.md)) |
| Market-cap history | `/api/historical-market-cap/{SYM}.CC` (10 calls) | daily from late 2022; a probe returned an object keyed "0", "1", … with `date` and `value`, not a list |

**Method (risk-on / neutral / risk-off).** Components in [−1, +1], composite as in section 8 step 7, weights
declared.
1. **BTC trend** (0.30): +1 if `C > SMA_50 > SMA_200` and the 20-day change of `SMA_50` > 0; −1 for the mirror;
   else 0 (windows in calendar days, since `.CC` trades every day).
2. **Alt breadth** (0.25): share `a` of the declared top-N (excluding BTC and stablecoins) with
   `C > SMA_200`, members with 200 bars only; score `2a − 1`; needs ≥ 5 members. A list built from today's
   market caps is survivorship-biased; label it.
3. **Drawdown** (0.15): `dd = 1 − C/max(C over 365 days)`; +1 if dd < 10%, 0 if 10–25%, −1 if > 25%.
4. **Realized volatility** (0.15): `RV_30 = sd(log returns, 30 days)·√365`; percentile `q` within the prior
   1,095 days (≥ 365 needed); score `1 − 2q` (high vol = risk-off).
5. **Positive-day share** (0.15): share `u` of the last 30 daily returns > 0; score `clip((u − 0.5)/0.15, −1, 1)`.
6. Label: composite ≥ +0.3 `risk-on`, ≤ −0.3 `risk-off`, else `neutral`; report coverage.
7. **Dominance** is context only: `MarketCapDominance` has no history in EODHD. A historical proxy is BTC's
   share of the declared universe's summed historical market cap (from late 2022), labelled "dominance
   within the declared universe".
8. **FDV vs market cap** (snapshot): `FDV/MC = MarketCapitalizationDiluted / MarketCapitalization`. A probe
   on 2026-10-25 returned `MaxSupply = 0` for ETH (no hard cap) where the reference says null, with diluted
   cap equal to market cap; treat 0 as "no cap". If `MarketCapitalization` is missing, the crypto notes
   suggest `MarketCapitalizationDiluted` as the fallback; label it.

```python
import numpy as np

CRYPTO_W = {"btc_trend": .30, "breadth": .25, "drawdown": .15, "rv": .15, "pos_days": .15}

def crypto_regime(btc, universe_close):
    s = {}
    sma50, sma200 = btc.rolling(50).mean(), btc.rolling(200).mean()
    c, slope = btc.iloc[-1], sma50.iloc[-1] - sma50.iloc[-21]
    s["btc_trend"] = (1 if c > sma50.iloc[-1] > sma200.iloc[-1] and slope > 0 else
                      -1 if c < sma50.iloc[-1] < sma200.iloc[-1] and slope < 0 else 0)
    ok = universe_close.rolling(200).count().iloc[-1] == 200
    above = (universe_close.iloc[-1] > universe_close.rolling(200).mean().iloc[-1])[ok]
    s["breadth"] = 2 * above.mean() - 1 if len(above) >= 5 else None
    dd = 1 - c / btc.iloc[-365:].max()
    s["drawdown"] = 1 if dd < .10 else 0 if dd <= .25 else -1
    rv = np.log(btc).diff().rolling(30).std() * np.sqrt(365)
    hist = rv.iloc[-1095:-1].dropna()
    s["rv"] = 1 - 2 * float((hist < rv.iloc[-1]).mean()) if len(hist) >= 365 else None
    share = (btc.diff().iloc[-30:] > 0).mean()
    s["pos_days"] = float(np.clip((share - .5) / .15, -1, 1))
    v, cov = composite(s, CRYPTO_W)                           # composite() from 9.3
    label = "risk-on" if v >= .3 else "risk-off" if v <= -.3 else "neutral"
    return round(v, 3), round(cov, 2), label, s, round(float(dd), 4)
```

**Boundaries.** Funding rates, open interest, liquidations, on-chain flows, exchange-level volume, global
crypto totals (total market cap, total volume), trending lists, category/sector taxonomies and stablecoin
supply are **not EODHD data**. Token unlock and vesting schedules are user-supplied.

**Acceptance checks.** A synthetic BTC path rising about 0.12% per day for 1,200 days, with eight alts moving
with it → composite 0.927, `risk-on`, drawdown 0. The same path turning down 0.2% per day for the last 300
days → −0.753, `risk-off`, drawdown 0.4501. ETH-style `MaxSupply = 0` is reported as "no hard cap", never as
FDV = 0.

---

## 24. Pre-publication checks for market commentary

**Use when** a recap (section 15), newsletter draft, research note or AI-written article is about to be
shared. Run these checks on the final text, after editing.

**EODHD inputs.** The capture used to write the piece (each number's symbol, field, date, basis, value);
`/api/exchange-details/{EX}` for working days and holidays (1 call per [plans-limits](plans-limits.md#call-costs-per-endpoint);
the endpoint page says 5); EOD closes of every cited symbol.

**Checks** (`block` = fix before publishing; `warn` = review):

| # | Check | Rule |
|---|---|---|
| 1 | Numbers tie to data | Every figure has a provenance row; it must round from the data at the decimals shown (half a unit of the last digit). Percent changes are recomputed from the two endpoint values. Totals and allocations sum to 100% ± 0.1 pp. |
| 2 | Scale and instrument | The quoted level ÷ the cited symbol's close must lie in [0.5, 2]; otherwise block (`SPY.US` vs `GSPC.INDX` is about 10×; GBX vs GBP is 100×). |
| 3 | Names and tickers | Each company name matches `General.Name` (or search) of the cited ticker and exchange. |
| 4 | Dates | A stated weekday matches the date; no date is after the as-of date; a "session" date is a trading day of the cited exchange; "yesterday/last week" is resolved to absolute dates. |
| 5 | Units | Changes in yields, rates and spreads are in pp or bp, not %, unless explicitly relative; % vs pp in sentences about percentages. |
| 6 | Time labels | Live or delayed quotes carry their delay ("15–20 min delayed") and time zone; EOD values carry their session date. |
| 7 | Labels and disclaimers | Research/education, not advice; hypothetical or backtested results labelled; proxies labelled; data source and as-of time stated. |
| 8 | Licence | Publishing to others (newsletter, public site, group, client) is display to others and needs commercial rights ([licensing](licensing.md)); no raw data tables, downloadable series or bulk quotes beyond what the licence allows; no API key or token-bearing URL in the text. |
| 9 | Third-party text | News content is quoted briefly with a link to the original, never reproduced in full. |

```python
import datetime as dt, re

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

def check_dates(text, sessions, as_of):
    out = []
    for m in re.finditer(r"(?:(\b[A-Z][a-z]+day),?\s+)?(\d{4}-\d{2}-\d{2})", text):
        wd, d = m.group(1), dt.date.fromisoformat(m.group(2))
        if wd and wd.lower() != WEEKDAYS[d.weekday()]:
            out.append(("block", f"{m.group(0)}: {d} is a {WEEKDAYS[d.weekday()].title()}"))
        if d > as_of:
            out.append(("block", f"{d} is after the as-of date {as_of}"))
        elif d not in sessions:
            out.append(("warn", f"{d} is not a trading session for the cited exchange"))
    return out

def check_level(quoted, data_close, decimals_shown):
    ratio = quoted / data_close
    if not 0.5 <= ratio <= 2.0:
        return ("block", f"scale mismatch x{ratio:.3g} (wrong symbol, index vs ETF, GBX vs GBP?)")
    if abs(quoted - data_close) > 0.5 * 10 ** (-decimals_shown) + 1e-12:
        return ("block", f"{quoted} does not round from {data_close}")
    return None

def check_units(text):
    pat = (r"(yield|rate|spread)s?\b[^.]{0,40}?\b(rose|fell|up|down|climbed|dropped)\b"
           r"[^.]{0,15}?(\d+(?:\.\d+)?)\s?%")
    return [("warn", f"'{m.group(0)}': a change in a rate is in pp or bp, not % (unless relative)")
            for m in re.finditer(pat, text, re.I)]
```

**Pitfalls.** Regex date checks only catch ISO dates; normalize other date formats first. A level that
passes the scale check can still be the wrong basis (adjusted vs raw close after an ex-date): the provenance
row must state the basis. A check that passes is not editorial approval; a person still reads the piece.

**Acceptance checks.** Text "On Friday 2026-10-22 …" → block (2026-10-22 is a Thursday); a date of
2026-10-24 → warn (Saturday, not a session); 2026-10-30 with as-of 2026-10-25 → block. Quoted 5,432.1 vs
close 5,432.06 at one decimal → passes; vs 543.21 → block, scale ×10; 5,432.2 vs 5,432.06 → block (does not
round); 245.0 vs 2.45 → block, scale ×100. "10-year yields rose 0.25%" → warn.

---

## 25. Boundaries: what EODHD does not supply here

State these instead of inventing a source (no substitute provider):

- Market-wide put/call ratios, FINRA margin debt, fund flows, crypto perpetual funding rates, open interest,
  global crypto totals, crypto trending lists and category taxonomies, on-chain data, and history of
  `MarketCapDominance` (current snapshot only).
- Short-borrow availability, locate, borrow fees and short-sale-restriction (SSR) status.
- Filer-level 13F portfolios and their history (Fundamentals `Holders` is a current top-holders snapshot).
- Estimate-revision history and "consensus as known then" (archive `calendar/trends` yourself).
- A VWAP field, order book, trade conditions in EOD, and pre-computed sector or breadth series other than the
  `INDX` advance/decline codes.
- FTSE indices and current Russell indices; index options (SPX/NDX/RUT/VIX).
- Point-in-time index membership other than `GSPC.INDX` `HistoricalTickerComponents` (from 2012) or the
  Marketplace constituents product.
- Social-media or influencer sentiment.
- Historical sector classifications and dated theme-basket memberships (declare and version baskets yourself).
- Rule 10b5-1 plan flags as a field (only footnote text in Form 4 rows).
