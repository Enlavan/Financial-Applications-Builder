# Screeners, technical signals and strategy ideas

> Methods with formulas, steps and acceptance checks: [methods-technical-market](methods-technical-market.md), [methods-quant-research](methods-quant-research.md).

## Server-side versus local screening

Use the EODHD Screener for supported current filters and signals. Validate exact field names, operators, units and result dates. Its bounded offset is not a full-universe export. For custom conditions, fetch symbol lists and entitled bulk/individual data, then screen locally. A snapshot screener is not a historical universe.

Separate the candidate filter, ranking formula, portfolio constraints and execution rule. Keep missing data visible: “not scored” differs from “fails criterion.” Return the values that caused each inclusion so the screen can be audited.

## Common research patterns

| Pattern | Required data / implementation | Checks |
|---|---|---|
| Value + quality | Earnings/cash-flow yields, leverage, margins and growth | Negative denominators, statement currencies, comparable periods |
| Dividend growth/value | Distribution history, raw/adjusted amount meaning, earnings/cash-flow cover | Special dividends, payout changes, missing payment dates |
| Momentum/trend | Consistent adjusted returns, moving averages, relative strength | Warm-up, stale prices, universe survivorship |
| Breakout/VCP | Past range contraction, volatility, volume and breakout timing | No future pivot detection; volume basis; signal/fill separation |
| CANSLIM-style | Earnings/sales growth, price strength, shares and market trend | Any unavailable qualitative component remains unscored |
| Earnings drift/PEAD | Comparable actual/estimate EPS, public release time, post-release return | GAAP versus adjusted basis; estimate vintage; no backdated surprise |
| Mean reversion | Past deviation, volatility, liquidity and holding horizon | Structural breaks, falling-company risk, execution costs |
| Pairs/statistical arbitrage | Aligned price bases, hedge ratio fit on training, spread diagnostics | Correlation is not cointegration; borrow, stability, rebalance costs |
| Breadth/regime | Percent above averages, advances/declines, new highs/lows in a defined universe | Historical membership and denominator changes |
| Event/catalyst ranking | Earnings, corporate actions, news, known calendar events | Forecast versus confirmed event; publication time |
| Sector cycle / rotation | Sector-ETF relative strength over 1w/1m/3m, curve, labour and inflation releases, uptrend ratio per sector | Stylised map labelled heuristic; evidence for and against; release-date alignment |
| Theme baskets | Declared member lists, basket momentum, breadth, volume, news clusters | Basket built from today's winners has look-ahead; current industry labels |
| Daily movers / gaps | Two whole-exchange bulk days with `filter=extended`, splits of the day, news for flagged names | Split artefacts; price and dollar-volume floors; outcomes tracked in a ledger |
| Composite scores (CANSLIM, fear, bubble, crypto regime) | Declared components, breakpoints and weights | Missing component re-normalizes weights and lowers coverage; never a probability |

Method sections: sector cycle phase, theme baskets, movers scan, correction statistics, detector aggregation and the fear, bubble and crypto-regime scores are sections 17–23 of [methods-technical-market](methods-technical-market.md); the CANSLIM composite is its section 9.3 and trailing or signal-based exits its section 10.

These are explicit algorithms, not recommendations to buy. A named pattern does not substitute for defining thresholds, windows and data requirements.

## Pairs and regime analysis

Estimate hedge ratios on the training period; evaluate residual stationarity and rolling stability. Compute spread z-scores from past data, specify entry/exit/stop, and model both legs' costs and borrow. A regression of price levels can be spurious. Avoid selecting pairs using the whole evaluation period.

Regime indicators can combine breadth, volatility, trend and macro series, but date-align macro availability rather than period labels. Evaluate whether a regime filter adds value after turnover/costs. Do not treat a retrospectively named regime as a feature known in real time.

## Combining several screens

When several screens or detectors flag the same names, normalize each detector's score to a percentile within its own universe and date, apply declared detector weights, deduplicate by ticker, theme and date window, and show bullish-versus-bearish conflicts instead of netting them away. Keep each signal's source and as-of date, and break ties deterministically (coverage, then freshness, then ticker). Detectors built on the same input are not independent votes. Method and fixture: [methods-technical-market §21.1](methods-technical-market.md#211-multi-detector-signal-aggregation).

## Position plans and alerts

For a proposed setup state trigger, invalidation, horizon, maximum research risk and missing inputs. Position size can be based on a user-set loss budget divided by price-to-stop distance, capped by cash, notional and liquidity. Stops can gap; a calculated loss budget is not guaranteed. Trailing (ATR, chandelier) and signal-based exits are computed at the close and act on the next session; compare exit rules on the same entries before choosing one ([methods-technical-market §10](methods-technical-market.md#10-trade-plans-entry-stop-r-targets-time-exit-heat)).

Alert state needs hysteresis, cooldown, deduplication and re-arming rules. Emit an event once per actual crossing, not on every poll. Private alerts are different from a group/channel product under licensing. Do not send an alert externally without the user's authorization.
