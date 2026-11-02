# Strategy specification

Fill this in before writing strategy code. The code implements exactly this spec; every change bumps the
version and is recorded as a new trial in the trial ledger. Attach the completed spec to every backtest
output. Methods referenced: [quant research methods](../references/methods-quant-research.md),
[backtesting](../references/backtesting.md), [temporal research](../references/temporal-research.md),
[portfolio and risk](../references/portfolio-risk.md), [paper accounting](../references/paper-accounting.md).

## Identity
- Spec ID / version / date:
- Author and audience (private research | shared with others — check ../references/licensing.md):
- Archetype: trend | mean reversion | cross-sectional factor | pairs | event-driven | carry proxy | other:
- Hypothesis (one sentence, with the economic rationale):

## Data
- Universe rule (exchange(s), instrument type, liquidity floor, membership source, delisted handling):
- EODHD endpoints, plan and call budget (backfill and daily):
- Price basis: signals on adjusted_close | raw; fills and cash on raw OHLC; adjustment policy for fills:
- Currency and unit normalisation (GBX/ZAC, FX symbol and timing):
- Information-set mode: current-vintage retrospective | forward archived | strict historical:
- Fundamental activation lag (if fundamentals are used):
- Known data limitations accepted for this study:

## Signal
- Formula with symbols, units and lookbacks:
- Parameters and their declared grid (every grid cell counts as a trial):
- Signal time (e.g. after close of session D) and fill time (e.g. open of D+1):
- Same-bar stop/target ambiguity rule:

## Positions
- Entry rule:
- Exit rule(s) (signal exit, target, time stop):
- Stop rule and treatment of gaps through the stop:
- Sizing rule (volatility target, risk budget per trade, equal weight):
- Constraints (max weight, sector cap, gross/net exposure, participation cap as % of ADV):
- Rebalance frequency and calendar source:

## Risk controls (at least one hard control is mandatory)
- Hard control (e.g. drawdown halt, maximum position, data-freshness gate):
- Action on trigger (stop new orders and record the reason; never silent liquidation):

## Costs
- Commission, half-spread source (estimator or quotes), slippage, impact coefficient Y (two values):
- Borrow rate for shorts (user-supplied) and FX conversion cost:
- Cost ladder to report: 0 / 5 / 10 / 25 / 50 bps one-way:

## Validation plan
- Train / validation / final holdout dates (holdout untouched until the final run):
- Purge and embargo (sessions) and their rationale:
- variants_tried (running count; feeds DSR, PBO and multiple-testing control):
- Gates and thresholds used for the PASS / WARN / FAIL verdict:
- Benchmarks (buy-and-hold, equal weight, cash):

## Claims policy
- Forbidden wording: "guaranteed", "risk-free", "cannot lose", "proven edge".
- Rejected designs: all-in sizing; unlimited averaging down or martingale; leverage without a financing
  and margin model; live order placement from this research.
- Strongest permitted claim: "survived validation on the disclosed information set and cost assumptions".

## Pipeline
spec → code exactly from the spec → validation verdict (methods-quant-research.md §3.11) →
risk profile (portfolio-risk.md) → paper trading only (paper-accounting.md)
