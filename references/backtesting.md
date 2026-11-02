# Backtesting engines and event studies

> Methods with formulas, steps and acceptance checks: [methods-quant-research](methods-quant-research.md), [methods-performance-risk](methods-performance-risk.md), [strategy-spec](../assets/strategy-spec.md).

## Declare the simulation

Specify universe selection, data version, calendar, signal observation time, order submission, fill time, order type, price basis, cash/position accounting, transaction costs, borrow constraints, corporate actions, missing-data treatment and benchmark. Keep all data visible to a strategy bounded by its simulated decision time.

Vectorized research is useful for broad signal experiments if positions are correctly lagged and accounting assumptions explicit. Event-driven simulation is preferable for pending orders, partial fills, cash constraints, portfolio interactions, stops and actions. Neither engine style automatically eliminates look-ahead or guarantees realistic fills.

## Daily engine order

1. Apply known effective actions to positions according to the ledger.
2. Process previously submitted orders against the eligible session data and constraints.
3. Accrue/pay cash flows and fees in the declared currencies.
4. Mark the portfolio and record balances, exposures, stale marks and unresolved valuations.
5. Compute signals from information now available, then submit orders for a future eligible event.

Use next-session open for a close-based signal when that matches the strategy. A close-only series cannot simulate next-open fills accurately by renaming the next close “open.” Same-bar stop and target crossings are ambiguous with OHLC alone: use a declared conservative rule or mark the fill unresolved, rather than selecting the profitable sequence.

## Execution and costs

Model commission, bid/ask spread, slippage, minimum fees, financing, borrow costs, FX conversion and market impact as relevant. Keep basis points per one-way notional distinct from annual borrow rates and round-trip costs. Cap participation against compatible volume units; prevent buying more than available cash unless explicit margin is modelled. Missing borrow availability is not free unlimited shorting.

Use a cost ladder around a defensible base assumption, not a magic constant claimed to fit every market. Report turnover and capacity sensitivity. EOD or bar data alone cannot determine order-book depth, queue priority, all trade conditions, actual execution or market impact.

## Corporate actions and missing data

Choose adjusted-return or explicit cash/share accounting as described in corporate-actions.md. Unknown delisting proceeds do not become zero or the last close by default. Specify an unresolved valuation policy and disclose sensitivity. Keep stale marks distinct from executable fills. Do not remove failed securities merely because they hurt results.

## Event studies

Select events using publication/disclosure time, define estimation and event windows in actual sessions, avoid overlapping/confounded events where needed, and select an appropriate expected-return model. CAR is the sum of abnormal returns under its model; buy-and-hold abnormal return compounds instead. Cluster uncertainty when events share issuers/dates; calendar-date shocks can correlate observations. A post-event move is not proof that the event caused it.

## Performance outputs

Report total and annualized return, volatility, Sharpe with stated risk-free/frequency, drawdown and duration, turnover, trade count, exposure, costs, gross/net results, missing/excluded records, and benchmark. CAGR requires positive starting/ending equity and a meaningful elapsed period; insolvency cannot be hidden by a convenient annualization. Sharpe with zero variance is undefined, not infinite skill.

Compare against buy-and-hold, cash and a simple strategy appropriate to the universe. Keep all trial results, not only the best. Provide a reproducible parameter/data manifest for research output when useful; do not clutter a simple customer sample with implementation paperwork.

## Engine tests

Use synthetic paths for: no-trade cash preservation, one buy/sell with exact fees, dividend credited once, forward/reverse split neutrality, insufficient cash, stop/target ambiguity, missing bar, delayed signal, stale mark, delisting and short borrowing cost. Cross-check vectorized and event-driven results only under assumptions where they should agree.
