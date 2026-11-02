# Robustness, uncertainty and selection bias

> Methods with formulas, steps and acceptance checks: [methods-quant-research](methods-quant-research.md).

## Validation order

Establish temporal admissibility and identity first. Then validate calculations, execution/cost assumptions, out-of-sample design, statistical uncertainty and economic usefulness. A sophisticated p-value cannot rescue future information in features.

## Chronological evaluation

Use anchored or rolling walk-forward splits. Fit preprocessing, imputation, winsorization, scaling, feature selection, hyperparameters and allocation rules on training data only. Freeze them before testing. Keep a final chronological holdout untouched by iteration. Random shuffled stock-date rows commonly leak market regimes and overlapping outcomes.

Represent labels by their actual intervals `[decision_time, label_end_time]`. Purge training labels that overlap a validation/test interval. Apply an embargo/gap where feature or label dependence warrants it. Size it from the actual horizon and dependence, not a universal percentage. For cross-sectional panels, align split dates globally so the same future market period does not enter training through another asset. A combinatorial purged CV scheme may use training blocks on both sides; do not describe that as a deployable forward walk-forward simulation.

## Hypothesis search

Record every factor, parameter set, universe tweak, cost assumption and abandoned trial. Report multiplicity. Deflated Sharpe, probability of backtest overfitting and false-discovery control can inform interpretation, but depend on sample size, dependence and modelling assumptions. DSR is not a guaranteed posterior probability that a strategy has skill. Use per-period rather than annualized Sharpe inside formulas that require per-period inputs; handle one trial, short samples and zero variance explicitly.

Test sensitivity to nearby parameters and dates, alternative realistic costs, liquidity filters, delayed execution, sector/market exposures and subperiods. Stable plateaus are more persuasive than a single sharp optimum. Removing all difficult periods after seeing results creates another selection experiment.

## Statistical checks

- Use heteroskedasticity/autocorrelation-aware standard errors when returns or residuals are dependent.
- Block bootstrap time series; do not assume independent daily observations when resampling overlapping horizons.
- Report confidence intervals and effective sample size, not only t-statistics.
- Test stationarity/regime changes where relevant; passing a test is not a guarantee of stability.
- Rank IC measures monotonic association between factor and future outcome; it is not the same as implementable portfolio return.
- Residual return from a factor regression is model-specific unexplained return, not proof of investment skill.
- SHAP/feature importance explains a fitted model under its assumptions, not a causal effect.

## Decision record

State what passed, what failed, and what is untestable because EODHD lacks required versions, publication timing, historical membership or execution detail. A smaller honest sample is preferable to silently filled evidence. Do not impose a universal Sharpe threshold or invent quantitative improvements from applying this skill.

Deliver a concise comparison: baseline, candidate, net costs, held-out period, uncertainty, turnover, maximum drawdown, data exclusions, and next experiment only if warranted. Paper observation is a distinct later stage; a successful backtest does not authorize live deployment.
