# Macro, rates, currencies, crypto and specialist datasets

> Methods with formulas, steps and acceptance checks: [methods-options-rates-macro](methods-options-rates-macro.md).

## Macro dashboard

Choose country/series, frequency, unit, seasonal-adjustment and growth convention. Levels, year-over-year growth, month-over-month growth and annualized rates differ. Join using release availability when known, not just economic period labels. Revised current macro history is not a real-time vintage dataset. Show observation and retrieval dates; do not forward-fill a missing release as if it were newly observed.

Combine EODHD macro indicators, economic events, rates and Treasury curves where entitled. Compute curve slopes on matched dates and comparable maturities. A missing tenor is not a zero rate. Rate changes in percentage points differ from percent changes; 25 basis points = 0.25 percentage points = 0.0025 in decimal yield units.

## Fixed-income concepts and limits

Yield curves, credit indices and available bond analytics are not a comprehensive individual-bond market. Check each symbol/ISIN, endpoint and entitlement; do not promise corporate issues, exchange bonds or futures simply because a related rates series exists.

For a supplied bond schedule, price is discounted coupons plus principal under specified settlement date, day count, compounding, calendar and accrued-interest rules. Clean price excludes accrued interest; dirty price includes it. Duration/convexity and key-rate exposures require those terms. Do not invent coupon schedules or calculate tradable yields from a reference index level.

Credit dashboards can use available ratings, risk premiums and spread series. Ratings are opinions/observations with timing; missing ratings are not risk-free. A country aggregate is not an individual issuer's credit spread.

## FX and multi-currency books

Retain pair orientation, observation time and currency units; invert rates explicitly and test reciprocal conversion. A quoted cross constructed from two pairs requires aligned timestamps and should be labelled derived. Carry/forward-return models require forward points and financing inputs not automatically available from spot history. Do not present indicative/reference FX as executable broker rates.

Methods: theoretical CIP forwards and hedged returns (C1), carry proxy (C2), momentum and the policy-rate divergence table (C2b) and PPP (C3) in [methods-options-rates-macro](methods-options-rates-macro.md). `*.FOREX` daily rows include some weekend dates; filter or count them before computing volatility.

## Commodities and futures

Use the EODHD historical commodities API for supported codes and intervals. Distinguish spot/reference price, index, CFD-like representation and a dated futures contract. Do not synthesize futures contracts, continuous rolls, COT positioning or executable commodity quotes from a spot/reference series. (Aggregate CFTC net-position rows do appear in the economic-events feed; there are no COT reports or contract-level positioning.)

If the user supplies contract-level data, general continuous-futures research can define roll date, liquidity criterion, back/ratio adjustment and separate execution prices, but this is a user-input modelling mode, not an EODHD retrieval promise. Preserve roll yield versus spot return and contract multiplier/margin assumptions.

Futures position sizing works only on user-supplied contract specifications: `contracts = floor(R / (|entry − stop| / tick_size × tick_value))`, with tick_value = tick_size × multiplier, and the notional and margin reported beside it (C9b). EODHD reference prices may set the stop distance, but they are not the contract's prices, so the basis risk must be labelled.

Inventories and supply: the only EODHD source is the weekly US EIA inventory rows in the economic-events feed. Other inventory, production, rig-count, shipping and weather data are not EODHD data. Commodity-API specifics are in C9b: 23 FRED-sourced codes, daily data for energy only, paged daily pulls, monthly rows stamped at the month start, and ETF-vs-reference tracking and inflation beta.

## Crypto and decentralized-finance requests

> `MaxSupply = 0` means "no hard cap" (seen for ETH; the reference says null) — never divide by it. Crypto regime recipe and crypto `Statistics` fields: [methods-technical-market §23](methods-technical-market.md#23-crypto-regime-recipe-and-crypto-fundamentals-fields).

Use supported EODHD crypto symbols and available fields for prices, returns, correlations, volatility and portfolio studies. Keep 24/7 calendar, UTC day boundaries, quote currency, aggregation and volume interpretation explicit. A ticker/pair does not identify every token contract or wrapped asset.

Wallet balances, on-chain swaps, pool reserves, MEV, staking positions, transaction execution and prediction-market books are not supplied by these market-data APIs. Keep general mathematical modules only when the user supplies inputs: pool invariant/reserve math, impermanent-loss scenarios, funding/fees and token supply models. Do not add another provider adapter or imply token-holder/wallet analytics can be recovered from EODHD OHLC.

### Crypto field map

- **Prices.** `/api/eod/{BASE}-{QUOTE}.CC` (1 call). Days are UTC on a 365-day calendar, so annualize with
  365. Volume is aggregated across the top 15 exchanges, with no per-exchange split. The latest row can be
  the **unfinished current UTC day**: a probe at 02:27 UTC on 2026-10-26 returned a 2026-10-26 row. Drop
  rows dated today (UTC) or later.
- **Snapshot fundamentals.** `/api/fundamentals/{X}.CC?filter=Statistics` (10 calls; Fundamentals Feed or
  All-In-One). Fields:
  - `MarketCapitalization` = `CirculatingSupply` × price;
  - `MarketCapitalizationDiluted` = `MaxSupply` × price;
  - `CirculatingSupply`, `TotalSupply`, `MaxSupply` (null if unlimited);
  - `MarketCapDominance` (% of the total crypto market).

  These are current values only, so archive them yourself to build history. FDV-to-cap ratio =
  `MarketCapitalizationDiluted / MarketCapitalization` (= MaxSupply / CirculatingSupply). It is
  unavailable when `MaxSupply` is null. Probe (demo, BTC-USD.CC, 2026-10-26): cap 1.618e12, diluted
  1.690e12, ratio 1.0446 = 21,000,000 / 20,103,165, dominance 60.14%.
- **History of market cap.** `/api/historical-market-cap` covers `.CC` daily from late 2022 (10 calls).
- **Not EODHD data:** global crypto totals and dominance history (dominance is a current snapshot),
  trending or "top gainers" lists, token categories and sectors, per-exchange books and volume,
  perpetual funding, basis and open interest, on-chain metrics, wallet or holder data, vesting and unlock
  schedules, staking reward rates and validator data.

### Crypto regime recipe

**Use when:** labelling the crypto market risk-on, neutral or risk-off from EODHD prices.

**Inputs:**
- `BTC-USD.CC` daily closes, at least 366 days (the RV percentile uses the 30-day windows inside the last
  365 daily returns);
- optionally a **declared** top-N `.CC` universe for breadth;
- optionally BTC `MarketCapDominance` (current only).

**Method:** use completed UTC days only.
1. Trend: close vs the 50- and 200-day SMAs. 200DMA slope = 200DMA(t)/200DMA(t − 20) − 1.
2. Breadth: the share of the universe above its own 200DMA. The universe is today's list, so label it
   "survivorship: current constituents".
3. Stress: drawdown from the 365-day high. 30-day RV = sd of log returns × √365. Its percentile is taken
   against the trailing 365 days of 30-day RV values.
4. Participation: the share of positive days over the last 30.
5. Score with declared thresholds:
   - +1 each for close > 200DMA, 200DMA slope > 0 and close > 50DMA;
   - −1 for drawdown < −25%;
   - −1 for RV percentile > 0.8;
   - breadth ≥ 0.6 gives +1 and ≤ 0.3 gives −1;
   - total ≥ 2 is risk-on, ≤ 0 is risk-off, anything else is neutral.

   Show every component and mark any that are unavailable. Funding rates and open interest are not
   inputs (boundary).

**Worked example (probe, demo key, BTC-USD.CC, as of 2026-10-25).**

| Component | Value | Score |
|---|---|---|
| Close | 80,024 | |
| 50DMA | 81,805 (close below) | 0 |
| 200DMA | 72,945 (close above) | +1 |
| 200DMA slope over 20 days | +1.91% | +1 |
| Drawdown from 365-day high | −30.1% | −1 |
| 30-day RV | 25.0% (percentile 0.03) | 0 |
| Positive days in the last 30 | 46.7% | |
| Breadth | not computed | |

The score is +1, so the label is **neutral**. Breadth is listed as unavailable.

**Acceptance checks.** No input uses a row dated after the as-of day. A universe with
one member gives breadth 0 or 1 and the "survivorship" label. Removing the last (incomplete) row changes
nothing for an as-of date before it.

### User-input modules: impermanent loss and staking yield

These are general formulas. EODHD supplies only the price ratio. Pool composition, fee income, reward
rates and token issuance are **user-supplied**, because on-chain data is not EODHD data.

- **Impermanent loss** for a 50/50 constant-product pool:
  `IL(k) = 2·√k/(1 + k) − 1`, where k = P_end/P_start is the price of token A in units of token B. It
  compares the LP value with holding the two tokens. k comes from aligned `.CC` closes (e.g.
  ETH-USD/BTC-USD on the same UTC dates).
  - Net LP result vs holding ≈ IL + the fee yield over the period. Fee yield is user-supplied.
  - Concentrated-liquidity and weighted pools need their own formulas (user model).
  - Check values: k = 0.25 or 4 gives −20.000%; k = 0.5 or 2 gives −5.719%; k = 0.8 or 1.25 gives
    −0.619%; k = 1 gives 0. IL(k) = IL(1/k).
- **Staking yield:**
  - APY from a stated APR compounded n times a year: `APY = (1 + APR/n)^n − 1`.
  - **Real (dilution-adjusted) staking yield** = `(1 + APY)/(1 + supply inflation) − 1`. Both inputs
    are per year. Supply inflation is user-supplied, or estimated from two archived `CirculatingSupply`
    snapshots one year apart, labelled.
  - USD return ≈ (1 + token-denominated yield)·(1 + token price change) − 1, with the price change from
    `.CC` closes.
  - Check values: APR 5% compounded daily gives APY 5.1267%. With 3% supply inflation the real yield is
    2.0648%. When inflation equals APY, the real yield is 0.

## ESG, risk and property analytics

Use entitled EODHD Marketplace ESG/risk products where relevant; missing/stale fields in Fundamentals are not automatically current ESG coverage. A score needs its scale, date, universe and available methodology. Do not convert scores from different methods into a common rank without explicit normalization assumptions.

Property-price indices describe a region/segment, not a specific home's value. Preserve nominal/real distinction and seasonal adjustment. For risk/sanctions screening, record query/date/matches and require appropriate identity resolution; name similarity is not a conclusive match or compliance clearance.
