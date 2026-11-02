# Factors, features and financial ML

> Methods with formulas, steps and acceptance checks: [methods-quant-research](methods-quant-research.md), [methods-performance-risk](methods-performance-risk.md).

## Contents

1. Dataset construction
2. Feature engineering
3. Labels
4. Modelling sequence
5. Portfolio translation and monitoring
6. Triple-barrier labels, uniqueness weights and label balance
7. Feature selection inside cross-validation folds
8. Out-of-fold feature importance and SHAP stability
9. Model registry
10. Polars pattern for panel features

## 1. Dataset construction

Use a panel keyed by local security/listing ID and decision time. Preserve capture and transformation lineage, feature availability time, label end time and missingness indicators. A current fundamentals cross-section is suitable for a current screener, not automatically for a historical training panel. Apply the temporal-research contract before feature computation.

Feature families include momentum/trend, reversal, volatility, liquidity, valuation, profitability, investment, leverage, earnings surprises, sentiment, calendar effects, macro conditions and cross-asset exposures. Each needs a formula, unit, lookback, input availability and inclusion policy. Dividend/split-adjusted returns, raw cash flows and statement currencies must not be mixed accidentally.

## 2. Feature engineering

Compute rolling features only over past eligible observations; state whether windows count observations or sessions. Set minimum coverage and handle missing sessions explicitly. Cross-sectional ranks and z-scores use the universe eligible on that date. Industry/size neutralization requires contemporaneously defensible classifications and exposures; current categories introduce another retrospective assumption.

For technical features, verify indicator convention: EMA initialization, Wilder versus simple smoothing, RSI warm-up, ATR treatment of gaps, Bollinger standard deviation convention, and adjusted/raw basis. Do not assume two libraries with the same indicator name have identical output.

Use winsorization, robust scaling and missing-value treatment fitted on training data. Do not drop a feature solely because it underperforms on the final holdout. Feature selection and PCA/latent factors belong inside the validation loop (section 7); importance is read on held-out folds (section 8). For a feature store, retain definition version, event time, available time, materialization time and batch watermark.

## 3. Labels

Specify horizon in sessions/time, return basis, currency, entry/exit timing and transaction costs. A forward return requires a future outcome but its predictors must not. Triple-barrier labels have an event-dependent end time, so purge by actual intervals; do not use a fixed nominal horizon when an event closes sooner/later. Construction, sample weights and label balance are in section 6. Meta-labels estimate whether to take a separately defined directional signal; they do not create an independent direction model automatically.

## 4. Modelling sequence

Start with an interpretable baseline and compare candidate models under the same chronological splits. Evaluate regression error or classification calibration as well as economic outcomes. Probability calibration matters for sizing; a ranking score is not a probability. Check imbalance, leakage through identifiers/dates, sample weighting, grouped security dependence and regime drift.

For reinforcement learning, specify observed state, action constraints, execution delay, reward net of costs, and episode chronology. Prevent the environment from leaking full future paths or filling with unavailable prices. Compare against simple policies and examine reward hacking; do not make RL the default for a screener.

## 5. Portfolio translation and monitoring

Convert scores to constrained weights/positions with exposure, liquidity, turnover and concentration limits. Evaluate capacity and net returns, not only predictive metrics. Monitor feature distribution, missingness, schema changes, prediction calibration and realized performance separately. Retraining is versioned and evaluated before replacing a deployed model; drift alone does not justify autonomous live trading changes. The triggers, challenger evaluation, promotion and rollback rules are in [methods-quant-research §9.1](methods-quant-research.md).

Keep model artifacts, seed, code version, train/validation/test windows and capture IDs in a registry (section 9). A backtest run should be reproducible without re-downloading revised data. Label synthetic demonstrations as synthetic.

---

The sections below follow the method format of [methods-quant-research](methods-quant-research.md): use,
EODHD inputs, method, pitfalls and acceptance checks. Code uses numpy and pandas (section 10 uses Polars);
every acceptance value comes from running the code shown.

## 6. Triple-barrier labels, uniqueness weights and label balance

**Use when:** labelling setup or event signals by which comes first (a profit-take, a stop or a time
limit), for a classifier or a meta-label model.

**EODHD inputs.** EOD OHLC with `adjusted_close`, 1 call per symbol for full history, delisted listings
included. Adjusted high/low = raw × `adjusted_close/close` of the same day. Events come from the user's
signal rule or from EODHD calendars (earnings, dividends) timed as in
[temporal research](temporal-research.md).

**Method.**

1. Events `t0`: the signal is known at the close of `t0`, entry is at the open of `t0 + 1` (price `e`).
2. Volatility known at `t0`: `σ_t0` = EWMA standard deviation of daily log returns (span 20–50) through
   `t0`, or `ATR_14 / close` at `t0`. Never use a window that includes later sessions.
3. Barriers: upper `e·exp(k_up·σ_t0)`, lower `e·exp(−k_dn·σ_t0)`, vertical `max_h` sessions (exchange
   sessions, not calendar days). If the vertical barrier is long, put the horizon scaling into `k` and say so.
4. Walk forward from `t0 + 1`. Label +1 if the high reaches the upper barrier first, −1 if the low reaches
   the lower barrier first, 0 at the vertical barrier (or the sign of the return; declare which). If both
   are touched in one bar the label is **ambiguous**: the same rule as the outcome ledger in
   [methods-quant-research §7.1](methods-quant-research.md). Drop ambiguous events or keep them as a
   separate class, and report their share.
5. `t1` = the session of the touch. The label interval `[t0 + 1, t1]` drives purging and embargo
   (methods-quant-research §3.5), not the nominal `max_h`.
6. **Average uniqueness.** Concurrency `c_t` = number of labels whose interval covers session `t`.
   Uniqueness of label `i` = mean over its interval of `1/c_t`. Use it as the sample weight (optionally
   multiplied by `|return|`, then rescaled to sum to the number of samples).
7. **Sequential bootstrap (outline).** For bagging, draw samples one at a time with probability
   proportional to each candidate's average uniqueness recomputed against the samples already drawn. A
   cheaper alternative is to cap each bag at about the mean uniqueness × the sample count.
8. **Label balance report.** Shares of +1 / −1 / 0 / ambiguous overall, per year and per regime. Warn
   when the smallest class is below 10% or the ambiguous share above 5%. Correct imbalance with class
   weights inside training folds only; never resample a test fold.
9. **Calibrate `k`** on the training period from the distribution of `MFE/σ_t0` and `MAE/σ_t0` over
   `max_h` (for example `k_up` near the median `MFE/σ`). Every `(k_up, k_dn, max_h)` is a trial
   (methods-quant-research §3.1).

```python
import numpy as np
import pandas as pd

def ewma_vol(close: pd.Series, span=20) -> pd.Series:
    return np.log(close).diff().ewm(span=span, min_periods=span).std()

def triple_barrier(o, h, l, c, vol, events, k_up=2.0, k_dn=2.0, max_h=10):
    """Arrays on one adjusted basis. Label +1/-1/0, None = both barriers in one bar (ambiguous)."""
    out = []
    for t0 in events:
        if t0 + 1 >= len(c) or np.isnan(vol[t0]):
            continue
        e = o[t0 + 1]
        up, dn = e * np.exp(k_up * vol[t0]), e * np.exp(-k_dn * vol[t0])
        last = min(t0 + max_h, len(c) - 1)
        label, t1 = 0, last
        for i in range(t0 + 1, last + 1):
            hit_up, hit_dn = h[i] >= up, l[i] <= dn
            if hit_up or hit_dn:
                label, t1 = (None if hit_up and hit_dn else 1 if hit_up else -1), i
                break
        out.append({"t0": t0, "t1": t1, "label": label, "ret": c[t1] / e - 1,
                    "mfe_sigma": (h[t0 + 1:t1 + 1].max() / e - 1) / vol[t0],
                    "mae_sigma": (l[t0 + 1:t1 + 1].min() / e - 1) / vol[t0]})
    return pd.DataFrame(out)

def average_uniqueness(t0, t1, n_sessions):
    """Label i covers sessions t0_i+1 .. t1_i."""
    conc = np.zeros(n_sessions)
    for a, b in zip(t0, t1):
        conc[a + 1:b + 1] += 1
    return np.array([np.mean(1.0 / conc[a + 1:b + 1]) for a, b in zip(t0, t1)])
```

**Pitfalls.** Barriers on raw prices across a split trigger false stops; use one adjusted basis. With
close-only data the touch order inside a bar is unknown; the ambiguous rule exists for that. Purging by the
nominal horizon instead of `t1` leaks or wastes data. A label set dominated by the vertical barrier (wide
`k`) is a sign-of-return label in disguise. Meta-labels need the primary signal fixed before labelling.

**Acceptance checks.**

- Uniqueness fixture: labels covering sessions 1–3, 2–4 and 6–7 → (0.667, 0.667, 1.0).
- Deterministic path rising 1% a session, `σ = 1%`, `k = 2`, event at session 5 → upper barrier touched at
  session 7, label +1, return 2.01%.
- Simulated random walk (3,000 sessions, daily σ about 1% with intrabar noise, an event every session,
  `max_h = 10`, EWMA span 20):

| `k_up = k_dn` | +1 | −1 | 0 (vertical) | ambiguous |
|---|---|---|---|---|
| 1 | 0.462 | 0.515 | 0.002 | 0.021 |
| 2 | 0.439 | 0.487 | 0.074 | 0 |
| 3 | 0.305 | 0.367 | 0.329 | 0 |

  At `k = 2`: mean label span 4.35 sessions, mean average uniqueness 0.253, median `MFE/σ` 1.64 and
  median `MAE/σ` −1.88.

## 7. Feature selection inside cross-validation folds

**Use when:** many candidate features and the user wants a subset without leaking the test data into the
choice.

**EODHD inputs.** The research panel of [methods-quant-research §1](methods-quant-research.md); no extra
calls.

**Method.**

1. Splits from methods-quant-research §3.5 (purged, embargoed). Scaling, winsorising, selection and
   hyperparameters are fitted inside each training fold.
2. Choose one or more methods from the table; each is a trial dimension.

| Method | Scores | Fitted on | Notes |
|---|---|---|---|
| Rank-IC filter | per-date Spearman IC and Newey-West `t` (quant §2.1–2.2) | training fold | model-free; captures monotone relations only |
| Mutual information | any dependence | training fold | noisy estimator; rank-transform first; fix the estimator settings |
| L1 (lasso, L1-logistic) | non-zero coefficients, penalty from an inner purged CV | training fold | picks arbitrarily among correlated features |
| Recursive feature elimination (RFE) | repeated refit, drop the least important | training fold | expensive; inherits the model's importance bias |
| MDI (impurity decrease) | tree split gains | training fold, in-sample | biased toward continuous and high-cardinality features; never the only criterion |
| MDA (permutation) | loss increase when a feature is permuted | test fold | correlated features dilute each other; use clusters |
| SFI (single-feature importance) | out-of-fold score of a model on one feature | test folds | misses interactions; immune to substitution |
| Clustered MDI / MDA | importance of correlated feature groups | as above | cluster on distance `√(½(1 − ρ))` of the training-fold correlation |

3. Collinearity: inside the fold, prune pairs with `|ρ| > 0.7` (quant §2.8) or work at cluster level.
4. Use a **threshold** rule (for example `|t| ≥ 3`, or a fixed L1 penalty), not a forced top-`k`. A forced
   top-`k` fills its quota with noise, and training folds overlap by most of their data, so the same noise
   feature tends to recur in every fold.
5. **Selection frequency** `freq_j` = folds that selected feature `j` / number of folds. Keep features with
   `freq_j ≥` a declared share (for example 0.8). Report the frequency table beside the final model.
6. The final selection is refitted on the full training set by the same rule; the final holdout is never
   used for selection.

```python
def per_date_rank_ic(F, y):
    """F: dates x names x features, y: dates x names (no missing values). Mean IC and t per feature."""
    rank = lambda a: a.argsort(axis=-1).argsort(axis=-1).astype(float)
    ry = rank(y)
    ics = []
    for k in range(F.shape[2]):
        rf = rank(F[:, :, k])
        a, b = rf - rf.mean(1, keepdims=True), ry - ry.mean(1, keepdims=True)
        ics.append((a * b).sum(1) / np.sqrt((a * a).sum(1) * (b * b).sum(1)))
    ics = np.array(ics).T
    return ics.mean(0), ics.mean(0) / (ics.std(0, ddof=1) / np.sqrt(len(ics)))

def selection_frequency(F, y, folds, t_min=3.0):
    """folds: list of (train_date_idx, test_date_idx), purged and embargoed upstream."""
    chosen = np.zeros(F.shape[2])
    for train, _ in folds:
        _, t = per_date_rank_ic(F[train], y[train])
        chosen += np.abs(t) >= t_min
    return chosen / len(folds)
```

(The `t` here is the plain one for one-period labels; with overlapping labels use the Newey-West `t` of
quant §2.2.)

**Pitfalls.** Selecting on the full sample and then cross-validating the chosen features is the classic
leak. High selection frequency across heavily overlapping folds is weaker evidence than it looks.
Importance-based selection inherits the importance method's bias (section 8).

**Acceptance checks.** 300 dates × 100 names × 20 standard-normal features, label
`0.08·f0 + 0.05·f1 − 0.04·f2 + noise`, five contiguous folds with 5 sessions purged on each side of the
test block, `|t| ≥ 3`: across 20 seeds the three informative features were selected in 100% of folds, no
noise feature reached a frequency of 0.8, and noise features were selected in any fold in 1.5% of
(seed, feature) cases. With a forced top-5 instead, seed 0 kept a noise feature in all 5 folds.

## 8. Out-of-fold feature importance and SHAP stability

**Use when:** explaining what drives a model, and checking that the explanation is stable and not a
leakage symptom.

**EODHD inputs.** None beyond the model's panel.

**Method.**

1. Compute importance on **held-out folds only**. For each CV test fold: mean `|SHAP|` per feature
   (TreeSHAP for tree models, from a SHAP library) or permutation importance (MDA) on that fold.
   In-sample gain or impurity importance is shown only as a comparison column.
2. Per fold, convert to shares of the fold total (negative permutation values clipped to 0).
3. **Stability:** mean pairwise Spearman correlation of feature ranks across folds, and the mean top-`k`
   Jaccard overlap. Declared reading: ≥ 0.8 stable; below 0.5 do not interpret individual features.
4. **Dominance flag:** any feature with a mean share above 0.5. Before reading it as signal, check it for
   leakage: identifiers, date proxies, a target-derived feature, a missing activation lag.
5. **Gain vs SHAP:** rank correlation between in-sample gain and out-of-fold `|SHAP|`. A feature high in
   gain and low out of fold is fitted noise.
6. Correlated features split credit; report importance per correlation cluster (sum of shares) as well.
7. Check SHAP additivity on each fold (base value + Σ SHAP = model output per row).
8. Attribution is about the model, not about markets: no causal claim
   ([methods-quant-research §8](methods-quant-research.md)).

```python
import itertools

def importance_stability(I, names, top_k=3, dominance=0.5):
    """I: folds x features out-of-fold importance (mean |SHAP| or permutation loss increase)."""
    I = np.clip(np.asarray(I, dtype=float), 0, None)
    share = I / I.sum(axis=1, keepdims=True)
    ranks = (-share).argsort(axis=1).argsort(axis=1)
    rho = [np.corrcoef(ranks[a], ranks[b])[0, 1] for a, b in itertools.combinations(range(len(I)), 2)]
    tops = [set(np.argsort(-s)[:top_k]) for s in share]
    jac = [len(x & y) / len(x | y) for x, y in itertools.combinations(tops, 2)]
    mean_share = share.mean(axis=0)
    return {"mean_share": {n: round(float(s), 3) for n, s in zip(names, mean_share)},
            "rank_stability": round(float(np.mean(rho)), 3),
            "top_k_jaccard": round(float(np.mean(jac)), 3),
            "dominant": [n for n, s in zip(names, mean_share) if s > dominance]}
```

**Pitfalls.** SHAP computed on training rows describes the fit, not generalisation. Permuting one of two
near-duplicate features shows little loss, so both look unimportant. Rank stability on a handful of folds
is itself noisy; show the fold table.

**Acceptance checks.** Features (mom_12_1, vol_63, value_ep, size, noise):

- Four folds `[0.30, 0.20, 0.15, 0.10, 0.02]`, `[0.28, 0.22, 0.12, 0.11, 0.03]`, `[0.25, 0.18, 0.20, 0.09, 0.01]`,
  `[0.35, 0.15, 0.14, 0.12, 0.02]` → mean shares 0.387 / 0.247 / 0.202 / 0.138 / 0.026, rank stability
  0.95, top-3 Jaccard 1.0, no dominant feature.
- Three folds where the first feature holds 0.80–0.90 → mean share 0.85, flagged dominant.
- Three folds `[0.3, 0.1, 0.2, 0.05, 0.35]`, `[0.05, 0.3, 0.1, 0.4, 0.15]`, `[0.2, 0.25, 0.05, 0.3, 0.2]` →
  rank stability −0.233, top-3 Jaccard 0.3: do not interpret.

## 9. Model registry

**Use when:** many experiments are run and every reported number must trace back to its configuration,
data captures, code and predictions.

**Design.** A content-addressed configuration key links the tables. Every trial is kept, including the
abandoned ones; it is the same population as the trial ledger of methods-quant-research §3.1.

| Table | Key | Columns |
|---|---|---|
| `configs` | `config_hash` | canonical JSON: spec version, features (sorted), label definition, model class and hyperparameters, data-manifest hash, information-set mode, code commit, seed |
| `training_runs` | `run_id` | `config_hash`, train/validation windows, fold scheme, capture-manifest hash, artefact URI and artefact hash, metrics, start/end time, status |
| `predictions` | (`run_id`, `listing_id`, `decision_ts`) | score, fold, `available_ts`, artefact hash |
| `backtests` | `backtest_id` | `run_id`, cost model, net-return series reference, verdict (quant §3.11), trial count used for DSR |
| `promotions` | `model_id` | `run_id`, stage (research / paper / retired), decided at, approver, gate evidence, previous `model_id` (quant §9.1) |

Rules: the same `config_hash` must reproduce the same artefact hash (a mismatch is a reproducibility
defect to investigate); predictions carry `available_ts` so they join point-in-time; nothing is deleted,
only marked with a status.

```python
import hashlib
import json

def config_hash(cfg: dict) -> str:
    """Canonical JSON (sorted keys, compact separators); sort set-like lists before calling."""
    canon = json.dumps(cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]
```

**Pitfalls.** Timestamps, absolute paths or hostnames inside the config break content addressing. Lists
are ordered: a feature list in a different order hashes differently, so sort set-like lists first.
Non-deterministic training (threads, GPU) can produce different artefacts from one config; store the
artefact hash and flag it.

**Acceptance checks.** The configuration `{spec_version: "mom-v3", features: ["mom_12_1", "vol_63"],
label: {kind: "fwd", h: 21}, model: {type: "ridge", alpha: 1.0}, data: {panel_manifest: "sha256:ab12",
info_set: "current-vintage retrospective"}, code: "git:4f2c1e0", seed: 7}` hashes to `7a3de39f6b289774`,
and the same content with keys in another order gives the same hash. `alpha` 1.0000001 gives
`12d69d0d502b52c5`; the features list in reverse order gives `46659c3b0af80b25`.

## 10. Polars pattern for panel features

**Use when:** the panel is too large for pandas in memory, or the pipeline already stores Parquet
(see [storage](storage.md) and [architecture](architecture.md)).

**EODHD inputs.** EOD rows stored as Parquet with `listing_id, date, adjusted_close, volume`;
fundamentals rows with an `available_date` (filing date plus the declared activation lag).

**Method.**

1. `scan_parquet` is lazy. A `filter` and `select` placed right after the scan are pushed into the reader
   (check with `.explain()`: the plan shows `SELECTION` and `PROJECT n/m COLUMNS` on the scan).
2. Start the scan early enough to cover the longest lookback (warm-up), compute the windows, then trim to
   the study start. Warm-up is given in calendar days, so allow about 7/5 of the session count plus
   holidays.
3. Per-listing windows use `.over("listing_id")` on data sorted by `listing_id, date`. Apply `shift(1)`
   so the value at `t` uses data through `t − 1`.
4. Point-in-time join of slower data with `join_asof(..., by="listing_id", strategy="backward",
   tolerance=...)`: the last value whose `available_date` is on or before `t`, and nothing older than the
   tolerance. If decisions are made before the open, shift `available_date` by one session first.

```python
import datetime as dt
import polars as pl

def build_features(prices_glob: str, fundamentals_path: str, start: dt.date, warmup_days: int = 30) -> pl.DataFrame:
    prices = (
        pl.scan_parquet(prices_glob)
        .filter(pl.col("date") >= start - dt.timedelta(days=warmup_days))  # pushed into the scan
        .select("listing_id", "date", "adjusted_close", "volume")          # projection pushed into the scan
        .sort("listing_id", "date")
        .with_columns(ret_1d=pl.col("adjusted_close").pct_change().over("listing_id"))
        .with_columns(
            mom_5=(pl.col("adjusted_close").shift(1) / pl.col("adjusted_close").shift(6) - 1).over("listing_id"),
            vol_5=pl.col("ret_1d").shift(1).rolling_std(window_size=5).over("listing_id"),
        )
    )
    fund = pl.scan_parquet(fundamentals_path).sort("listing_id", "available_date")
    return (
        prices.join_asof(fund, left_on="date", right_on="available_date", by="listing_id",
                         strategy="backward", tolerance="400d")
        .filter(pl.col("date") >= start)                                   # trim warm-up after the windows
        .collect()
    )
```

**Pitfalls.** Filtering the scan at the study start leaves the first rows without features (nulls that
look like missing data). A window without `.over` runs across listings. `shift` counts rows, not sessions:
a listing with missing sessions needs a calendar join first (missing is not zero). `join_asof` needs both
sides sorted on the join key within each group.

**Acceptance checks.** Two listings with 30 daily rows from 2024-01-01 (AAA 100, 101, …; BBB 50, 50.5, …),
fundamentals for AAA available 2024-01-10 (EPS 5.0) and 2024-01-20 (5.5), for BBB available 2022-11-01
(2.0); `start = 2024-01-12`, `warmup_days = 10`: the first output row (AAA, 2024-01-12) already has
`mom_5 = 0.0476` (110/105 − 1) and EPS 5.0; on 2024-01-20 `mom_5 = 0.0442` (118/113 − 1) and EPS 5.5;
BBB has no EPS (older than the 400-day tolerance). `.explain()` shows the date predicate and a 2/4-column
projection on the Parquet scan. Tested with Polars 2.1.
