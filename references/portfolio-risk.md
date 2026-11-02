# Portfolio construction, performance and risk

> Methods with formulas, steps and acceptance checks: [methods-performance-risk](methods-performance-risk.md), [methods-planning-wealth](methods-planning-wealth.md).

## Inputs and return conventions

Holdings, cash flows, account constraints and tax lots are user inputs, not EODHD market data. Resolve securities, normalize quote units/currencies and align valuation timestamps. Flag stale/unpriced positions rather than dropping them from NAV. Use an explicit benchmark and reporting currency.

Time-weighted return chains subperiod returns around external flows; money-weighted return solves dated investor cash flows and may have multiple/no roots. An IRR is not interchangeable with CAGR. Separate price return, distributions, FX, fees and external contributions. Do not count deposits as investment profit.

## Core metrics

For weights w and covariance Σ, variance is `wᵀΣw`; annualize using a justified observation frequency. Marginal volatility contribution is `(Σw)_i / σp`; component contribution is `w_i * (Σw)_i / σp`. Contributions sum to portfolio volatility for the model. Herfindahl concentration `sum(w_i²)` and effective N `1/sum(w_i²)` require a defined weight convention, particularly for leveraged/short books.

Report drawdown as equity relative to its running peak; include duration and recovery. VaR is a modelled quantile, not maximum loss; expected shortfall averages the tail under a stated estimator. Stress tests should include shocks, correlations, FX, liquidity and gaps beyond recent normal volatility. Historical crisis replays need valid instrument history or clearly labelled proxies.

## Allocation methods

Compare equal weight, constrained inverse volatility, minimum variance, equal-risk contribution and hierarchical approaches where useful. Shrink covariance when sample size is short relative to asset count. Expected-return optimization can be used with explicit uncertainty/views, but do not sell noisy sample means as reliable forecasts. Verify optimizer feasibility, sum of weights, bounds, turnover, cash, leverage and solver status. Do not normalize a failed optimizer output and call it a solution.

Walk-forward allocations against a simple baseline under equal costs and rebalance dates. Sensitivity to input window, covariance shrinkage and constraints is part of the result. Rebalancing can be calendar-based, tolerance-band or signal-driven; distinguish proposed trades from executed ones.

## Sizing and controls

Risk-budget sizing uses price-to-stop distance or volatility, bounded by cash, notional, concentration and liquidity. Fractional Kelly can illustrate sensitivity to uncertain edge estimates; full Kelly with noisy probabilities is not a default. Stops and drawdown circuit breakers limit intended behavior but do not guarantee exit price. A kill switch should stop new simulated/live-authorized orders, retain state and explain its reason; it must not silently liquidate positions without authorization.

## Attribution

For single-period fully invested Brinson-Fachler sector attribution:

- Allocation: `(wp_i - wb_i) * (rb_i - rb_total)`.
- Selection: `wb_i * (rp_i - rb_i)`.
- Interaction: `(wp_i - wb_i) * (rp_i - rb_i)`.

The sum equals portfolio minus benchmark return under matched sector weights/returns. Declare treatment of missing sectors, cash and leverage. Multi-period effects require a consistent linking method; summing single-period contributions does not reproduce compounded performance. Factor regression attributes model exposures and residuals, not proven skill or causation.

For FX, `(1+r_local)*(1+r_fx)-1` includes the cross term. Fixed-income approximations use `ΔP/P ≈ -duration*Δyield + 0.5*convexity*(Δyield)^2`; yields must use decimal units and duration definition must match. Unsupported bond-level inputs remain missing.
