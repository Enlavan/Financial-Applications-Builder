# End-to-end build recipes

Contents: quick map (endpoints, plan, budget) · recipes 1–36 · new recipes 37–50 (from support demand) · method recipes 51–98 · worked examples A–C · further methods.

Use these as starting architectures, not mandatory deliverables. Every recipe uses the integration contract, captures relevant observations and keeps missing inputs explicit. “Done” means the stated output and tests work for the scoped inputs, not that every instrument is covered.

## Recipe quick map: endpoints, minimum plan, call budget

Costs are API calls (see [plans-limits.md](plans-limits.md)); "N" = number of symbols. Minimum plan is the
cheapest personal plan that covers the core path; anything shown to other people needs a commercial
licence regardless of plan.

| # | Recipe | Core EODHD calls | Minimum plan | Typical budget |
|---|---|---|---|---|
| 1 | Dashboard / watchlist | `eod`, `real-time` (or `us-quote-delayed`), `div`, symbol list; optional `fundamentals` | EOD All World (+Fundamentals for metrics) | backfill N; daily 100 (bulk) or N; quotes N per refresh |
| 2 | Dividend tracker | `div` (json), `splits`, `eod`, `calendar/dividends` optional | EOD All World | 2N backfill; bulk `type=dividends` 100/day |
| 3 | Screener | `screener` or symbol lists + bulk + `fundamentals` | Extended (server-side) / AIO (fundamental screens) | 5 per page; local: 100/exchange/day + 10N weekly |
| 4 | Alerts | `real-time`, WebSockets, `eod-bulk-last-day`, `calendar/*` | EOD All World (polling) / Extended (stream) | N per poll; stream 0 |
| 5 | Valuation app | `fundamentals`, `eod`, `calendar/trends` | All-In-One (or two plans) | 10N + N |
| 6 | Events calendar | `calendar/earnings|ipos|splits|trends`, `economic-events` | Calendar & News Feed / Fundamentals | 1 per window; economic events 1 |
| 7 | News monitor | `news`, `sentiments`, `news-word-weights` | Free (low volume) / any | 5 per ticker |
| 8 | Insider / political trades | `insider-transactions`, `congressional-trades` | Fundamentals (insider) / AIO (congress) | 10 per request |
| 9 | ETF analyzer | `fundamentals` (`ETF_Data`), `eod`, ID mapping | All-In-One | 10 + 1 per fund |
| 10 | Multi-currency valuation | `eod` for assets and `*.FOREX`, symbol metadata | EOD All World | N + pairs |
| 11 | Daily backtester | `eod`, `splits`, `div`, symbol lists (`delisted=1`) | EOD All World | 1 per symbol history |
| 12 | Intraday research | `intraday`, `ticks`, `exchange-details` | Extended (ticks: AIO) | 5 per window |
| 13 | Delisted-inclusive universe | symbol lists active + `delisted=1`, `eod`, `fundamentals` (post-2018) | EOD All World (+Fundamentals) | 2/exchange + N |
| 14 | Security master | `search`, `id-mapping`, symbol lists, `fundamentals?filter=General`, `symbol-change-history` | Free/EOD (+Extended for renames) | 1–2/exchange + 1 per mapping page |
| 15 | ML / factor system | `eod`, `fundamentals`, `bulk`, `calendar/trends`, `macro-indicator` | All-In-One | backfill N + 10N; daily 100 |
| 16 | Event study | `calendar/earnings`, `eod`, `news` | Fundamentals + EOD (or AIO) | 1 per window + N |
| 17 | Long-horizon study | `eod` (`period=m` optional), `INDX`, `FOREX` | EOD All World | 1 per series |
| 18 | Macro dashboard | `macro-indicator`, `economic-events`, UST, GBOND, commodities, FX | Fundamentals (+free UST/commodities) | 10 per macro-indicator series; UST/rates 1 |
| 19 | Options analytics | Marketplace options `eod`/`contracts` | Marketplace US Options | 10 per page (own quota) |
| 20 | Crypto research | `eod`/`intraday` `*.CC`, WebSocket `crypto`, `fundamentals` (crypto) | EOD All World / Extended | N |
| 21 | Academic dataset | per question; usually `eod` + `fundamentals` | depends; academic discount on card | estimate before buying |
| 22 | Quality harness | same endpoints as the archive, re-pulled | same as archive | sample-based |
| 23 | Paper trading | WebSockets or `real-time`, `eod`, `exchange-details` | Extended | stream 0; polling N |
| 24 | Trading research | as 11/12/23; no order endpoints exist | Extended | as above |
| 25 | Streaming board | WebSockets `us`/`eu`/`forex`/`crypto` | Extended | 0 calls; 50 symbols/token |
| 26 | MCP assistant | MCP v2 tools | any (Free works, limited) | tool call = endpoint cost |
| 27 | RAG / agent pipeline | local archive + bounded REST/MCP tools | per data used | budgeted per run |
| 28 | AI signal product | prototype on synthetic data | commercial licence | — |
| 29 | Spreadsheet | Excel/Sheets add-ons or `fmt=csv` URLs | per data used | 1 per cell-call |
| 30 | Fintech / robo prototype | as 1/9/15 behind a server adapter | commercial licence | — |
| 31 | Public content | — | commercial licence | — |
| 32 | Team workspace | shared archive + commercial seats | commercial licence | — |
| 33 | B2B feed | — | redistribution agreement | — |
| 34 | Compliance monitor | `sanctions/*`, credit-risk, rates | All-In-One / Fundamentals | 10 per request |
| 35 | Tax / cost basis | `eod` (raw close on date), `splits`, `div`, FX | EOD All World | N lookups |
| 36 | Index replication | `fundamentals` (`Components`, `HistoricalTickerComponents`), Marketplace constituents, `eod` | Fundamentals + EOD / AIO | 10 per index + N |

## 1. Investing dashboard / watchlist

Input: user holdings/watchlist, reporting currency and refresh needs. Resolve listings, fetch entitled EOD/delayed/live data as appropriate, join fundamentals only for requested metrics, and compute positions/NAV with explicit FX. Build a small server-side adapter, cache and UI with observation times. Done: holdings reconcile to NAV, a stale quote is visibly stale, and a missing position price does not disappear from totals. Read applications, portfolio-risk and identity.

## 2. Dividend / income / DRIP tracker

Input: dated positions and income horizon. Ingest distributions and metadata, separate ex-date entitlement from payment cash, and build actual versus forecast income by currency. Add DRIP only with explicit reinvestment rules. Done: cash flows are counted once, special/combined distributions are handled transparently, and accumulating/missing-data cases are not fabricated. Read funds-income and corporate-actions.

## 3. Stock screener / scanner

Input: universe, filter/ranking criteria and rebalance cadence. Use documented Screener filters for supported current screens; otherwise download the universe and compute locally. Save filter definitions and dates. Done: explain why each candidate passed, distinguish missing scores and avoid paging beyond the endpoint contract. Historical testing requires historical eligibility inputs, not today's screen.

## 4. Alerts / notifier

Input: trigger, observation type, tolerance, channel and private audience. Build a scheduled poller or authorized stream, event state, deduplication, hysteresis and cooldown. Done: one crossing yields one event; stale data blocks a freshness-sensitive trigger; external delivery occurs only as authorized. Group/shared delivery invokes licensing review. Read screening, intraday and operations.

## 5. Valuation / financial-analysis app

Input: issuer, comparable peers and valuation method. Normalize fundamentals, expose historicals and assumptions, compute ratios or DCF and sensitivities, and provide a dated report/workbook. Done: currencies/periods agree, formulas recalculate, balance checks pass and unknown inputs remain labelled assumptions. Read fundamentals, valuation and reports.

## 6. Events / earnings / IPO calendar

Input: symbols, event categories and horizon. Ingest the relevant EODHD calendars, preserve changed schedules, classify confirmed versus estimated times and present a timezone-aware calendar. Done: changed dates update one logical event, unknown release times are not midnight facts, and surprises compare the same metric basis. Read events-news.

## 7. News / sentiment monitor

Input: symbols/topics, frequency and summary purpose. Collect bounded EODHD news/sentiment, deduplicate, aggregate under a stated scale and generate cited summaries. Done: article text cannot change tool permissions; duplicate headlines do not multiply evidence; publication and receipt times remain separate. Read events-news and ai-mcp.

## 8. Insider / political-trade tracker

Input: issuers/people/categories and observation window. Use the distinct EODHD disclosure datasets, preserve transaction versus disclosure dates and amendment captures, and show amount ranges accurately. Done: a historical signal activates on known disclosure, not a backdated transaction; trades are not presented as proof of intent. Read events-news and temporal-research.

## 9. ETF / fund analyzer

Input: exact fund/share classes and comparison goals. Resolve ISIN/listings, request available fundamentals/holdings, compute overlap and exposure with covered-weight reporting, compare matched total-return periods and fees. Done: share classes and currencies are distinct; missing holdings are not normalized away. Read funds-income and identity.

## 10. Multi-currency valuation

Input: holdings/cash currencies, reporting currency and valuation schedule. Normalize GBX/ZAc-like units before FX, fetch appropriately dated FX, and calculate local/FX/combined P&L. Done: inverse pairs and holiday policies are tested; units are not converted twice; stale FX is flagged. Read data-semantics and portfolio-risk.

## 11. Daily backtester

Input: strategy, available historical universe, dates, costs and execution rules. Archive prices/actions, construct features with time discipline, implement a lagged vectorized or event-driven engine, and compare baseline/net outcomes. Done: synthetic cash/action tests pass and no signal fills at a price learned afterwards. Read backtesting and research-validation.

## 12. Intraday / tick research

Input: supported symbols, interval, sessions and dates. Probe coverage, perform windowed backfill, normalize event times and build derived bars only from eligible observations. Done: session/DST boundaries and gaps are explicit; derived five-minute data is not mislabelled as the delivered five-minute product. Read intraday and ingestion.

## 13. Delisted-inclusive / historical universe

Input: universe definition and historical information requirements. Capture active/delisted lists, identity mappings, supported membership histories and observed coverage. Build eligibility with unknowns recorded. Done: delisted instruments are not silently excluded, and lack of historical listing/publication evidence prevents a false “fully survivorship-free” claim. Read identity and temporal-research.

## 14. Security master / identifier resolver

Input: symbols/identifiers and resolution level. Use Search, ID Mapping, lists and General metadata; assign local issuer/security/listing IDs, retain candidate ambiguity and rename/reuse evidence. Done: one ISIN may map to multiple listings without multiplying portfolio rows; reused symbols stay separate. Read identity and storage.

## 15. ML / factor research system

Input: target, horizon, features and feasible information set. Build a versioned panel/feature registry, leakage-aware chronological splits, baseline model and net portfolio evaluation. Done: transformations are fitted on training only, label overlap is purged, and results include all trials and missing evidence. Read ml-factors and research-validation.

## 16. Event study / look-ahead gate

Input: event definition, public timing, estimation/event windows and expected-return model. Join available event versions, apply a session-aware activation rule and compute abnormal returns with dependence-aware uncertainty. Done: the pipeline distinguishes retrospective from genuinely observed information and does not claim causality merely from a price move. Read temporal-research and backtesting.

## 17. Long-horizon history study

Input: desired assets and period. Probe actual per-symbol start/end/gaps and plan clipping, then build the covered subset and explicit exclusions. Done: advertised maximum history is not treated as universal, and absent early instruments/index dates are not synthesized. Read ingestion, identity and quality.

## 18. Macro / cross-asset dashboard

Input: countries, markets, series and economic question. Retrieve supported rates, macro, commodities, FX and prices; normalize frequency/units, preserve releases/revisions and show matched observations. Done: period date is not publication time and a reference commodity series is not a futures contract. Read cross-asset and applications.

## 19. Options analytics / volatility surface

Input: underlying, dates, expirations and Marketplace entitlement. Fetch contracts/EOD observations, filter quote quality, normalize multipliers and calculate payoff/Greeks/surfaces under stated models. Done: stale last trades are distinguished from quotes, nulls aren't zeroed, and index options are not replaced by ETF options without the user's chosen approximation. Read options.

## 20. Crypto dashboard / research bot

Input: supported crypto pairs and decision horizon. Use EODHD price/fundamentals/stream data as available, preserve 24/7 UTC conventions and quote currency, then compute indicators and portfolio risk. Done: no wallet, DEX, order-book or execution data is invented from OHLC. Read cross-asset, screening and paper-accounting.

## 21. Academic dataset / thesis

Input: research question, private/institutional audience and reproducibility needs. Build a bounded dataset with code, metadata, temporal limitations and methods; use synthetic/public-permitted material for a shared repository. Done: an academic discount is not treated as redistribution rights, and unavailable historical vintages are disclosed. Read licensing and temporal-research.

## 22. Data-quality / reconciliation harness

Input: concrete symbols, dates, fields and invariants. Capture comparable endpoint responses, normalize semantics and run independent transport/schema/financial checks. Done: confirmed application defects are fixed with regressions; unresolved source anomalies remain flagged rather than “corrected” by heuristics. Read quality.

## 23. Forward paper trading / shadow mode

Input: strategy, capital, freshness threshold and fill policy. Build a journalled simulated broker using entitled observations, persistent orders/cash/positions and data-quality gates. Done: stale/unknown quotes cannot fill, restarts are idempotent and synthetic versus observed fills are clear. Read paper-accounting and intraday.

## 24. Automated trading research

Input: strategy and whether the task is simulation or a separately authorized execution integration. Build the EODHD data/signal/risk side and a paper interface first when requested. Done: no EODHD order endpoint is invented; data quality and execution responsibility are separate; no live action follows merely from a backtest. Read paper-accounting and portfolio-risk.

## 25. Streaming ticker / heatmap

Input: audience, symbols and display latency. Implement entitled stream/polling, connection supervision, server-side secrets and UI state. Done: data is labelled by its actual observation type/time, reconnect does not duplicate subscriptions, and shared/public display has appropriate licensing. Read intraday and applications.

## 26. MCP research assistant

Input: host environment and supported EODHD tools. Configure the authorized OAuth connection, inspect schemas, use bounded tool calls and deterministic calculations, and answer with dated observations. Done: unavailable tools/fields remain explicit and no credentials enter prompts. Read ai-mcp.

## 27. Autonomous research / RAG pipeline

Input: research scope, local archive and action budget. Implement narrow tools, retrieval filters, numeric computation, provenance and stop conditions. Done: retrieved text cannot authorize actions, context truncation is visible, and a compact model uses tested tool schemas rather than guessed parameters. Read ai-mcp and operations.

## 28. AI signal product for others

Input: users, distribution and product outputs. Build a prototype with synthetic/authorized data, explicit model evaluation and commercial-rights boundary before serving real data. Done: derived signals are not assumed exempt from licensing and predictions are not marketed as guaranteed returns. Read ai-mcp, licensing and applications.

## 29. Spreadsheet / no-code tool

Input: workbook/app, refresh logic and desired formulas. Use documented EODHD integrations or a server/local collector with typed exports; preserve formulas and dates/units. Done: refresh does not expose the key, identifiers retain leading zeros, and formulas are evaluated or labelled unverified. Read reports.

## 30. Fintech / wealth / robo-advisor prototype

Input: audience, recommendations, portfolio inputs and business use. Build a licensed data adapter, identity/calculation services, tests and UI; use user-supplied account facts. Done: no custody, KYC, suitability or execution capability is fabricated from market data. Read professional-workflows and licensing.

## 31. Public content / community project

Input: intended charts, articles, bots and audience. Prepare calculations/design using appropriately authorized or synthetic data and identify required display/distribution rights. Done: free access or a derived chart is not automatically classified as personal use. Read licensing and reports.

## 32. Firm / team research workspace

Input: roles, datasets, access controls and outputs. Build commercial-entitled shared workflows, private evidence stores, review/audit records and reproducible analyses. Done: personal API credentials are not shared and private account information stays segregated. Read professional-workflows and operations.

## 33. B2B feed / downstream API

Input: redistribution agreement, consumers, schemas and service expectations. Design contracts, entitlements, metering, caching and lineage only within granted rights. Done: the service is not an unrestricted proxy to one personal key and freshness/coverage claims match available data. Read licensing, storage and operations.

## 34. Compliance / credit-risk monitor

Input: entities, identity evidence and applicable workflow. Use available sanctions/credit/risk datasets, retain matches/ambiguity and produce reviewable evidence. Done: an empty response is not clearance and a name match is not a confirmed identity. Read cross-asset and professional-workflows.

## 35. Tax / accounting / cost basis

Input: actual transactions, lots, jurisdiction and reporting dates. Reconcile user records, obtain dated valuations/FX, apply verified rules and expose missing evidence. Done: market history does not invent acquisition basis, adjustments do not double-count actions and tax estimates are labelled. Read personal-planning and paper-accounting.

## 36. Index replication / rebalancing

Input: index, historical/current scope, weight rules, tracking objective and costs. Obtain supported membership/weights with dates, map components via identifiers, compute target/current differences and tracking error. Done: current constituents are not used as historical truth, missing weights stay missing and proposed orders are not executed. Read identity and portfolio-risk.

## 37. Pre-purchase coverage probe

The most valuable first build for anyone unsure which plan fits (payments are non-refundable). Input: the
user's symbol list, required fields, intervals and date range. Using Free or demo access plus public docs,
resolve every symbol (symbol lists, ID mapping by ISIN), then for each symbol request a minimal sample and
record: resolved code and currency/unit, first and last EOD date, gaps against the exchange calendar,
intraday first bar (if entitled), fundamentals sections present (if entitled), and which endpoints answered
403. Output a coverage matrix, the cheapest plan that covers the requirement from
[plans-limits.md](plans-limits.md), the expected daily call budget, and a list of unsupported items
(e.g. Milan via the beta host, no FTSE/Russell indices, markets not covered at all). Done: every symbol has a status;
unknowns are labelled "needs entitled test", not "available"; the Free plan's one-year clipping is not
reported as the instrument's start date.

## 38. Local market-data warehouse

Input: exchanges, asset types, history depth. Day 0: symbol lists (active + delisted) → per-ticker EOD,
splits and dividends backfill (1 call each, resumable checkpoints). Daily: one bulk EOD request per
exchange after its update window, plus bulk `type=splits`/`type=dividends`; any symbol with a new action
gets its full history re-pulled because adjusted values restate. Weekly: symbol-list diff (new, delisted,
renamed, `_old` reuse). Store raw captures (hash, retrieval time) → normalized Parquet/DuckDB partitioned by
exchange and year → views for raw, split-adjusted and total-return series. Done: re-running a day is
idempotent, holidays are not filled, unit multipliers are stored, and a reconciliation report lists
symbols whose stored adjusted series differs from a fresh pull.

## 39. Point-in-time snapshot recorder

EODHD serves current versions only, so build the archive yourself, forward from today. Input: datasets
that revise (fundamentals sections, earnings trends, earnings/IPO calendars, index components, symbol
lists, economic events). Schedule daily/weekly captures, store raw body + hash + retrieval UTC, and write a
diff log of changed fields per key (fiscal period, horizon, event). Expose an `as_of(date)` view that
selects the latest capture on or before the date. Done: unchanged captures dedupe by hash, the diff log
shows restatements, and the documentation states the archive start date (nothing earlier is
point-in-time).

## 40. Broker holdings import and symbol resolver

Input: broker CSV/PDF exports with names, ISINs, local tickers, currencies, quantities. Build a local
index from symbol lists for candidate exchanges (1 call each) and ID mapping; match ISIN → listing by
exchange and currency, then name, then type; keep ambiguous rows in a review queue. Normalize quote units
(GBX/ZAC) and FX to the base currency. Done: each holding resolves to one listing or an explicit
unresolved state; nothing is matched by first search hit; cross-listed ISINs don't double positions.

## 41. Earnings season monitor

Input: watchlist and window. Pull `calendar/earnings` by `from`/`to` (filter locally; `symbols=` alone can
return empty), `calendar/trends` snapshots for consensus drift, and EOD for reaction windows aligned to
`before_after_market` (pre-market reports react the same session; after-market the next). Store each
calendar pull to catch date changes. Done: surprises compare the same basis within one source, unknown
report times are not midnight, and a moved date updates one logical event.

## 42. Market breadth and regime dashboard

Input: market(s) and indicators. Use ready series where they exist (`ADVN`, `DECN`, `UNCN`, `AVVN`,
`ADVQ`, `AVVQ` on `INDX`; `VIX.INDX`), the UST/GBOND curve for slope, and a locally computed
"% above 50/200-day average" from bulk EOD over a declared universe (current membership — label the
survivorship caveat). Done: each indicator shows its definition, universe, and last observation date;
missing days are gaps, not zeros.

## 43. Global ETF / fund portfolio in a base currency

Input: UCITS/US ETFs and funds by ISIN, base currency. Resolve via symbol lists/ID mapping (`EUFUND` for
funds by ISIN; LSE lines may be GBX, GBP, USD or EUR), pull EOD and dividends, and FX from `*.FOREX` on
matching dates. Compute local, FX and combined returns, distribution income by currency, and accumulating
vs distributing treatment. Done: unit and FX conversions happen once, stale NAV/prices are flagged, and a
missing fund is reported (it can be requested by ISIN), not silently dropped.

## 44. Personal alert bot (Telegram, Discord DM, email)

Input: the user's own rules and channel. Poll `real-time` for a few symbols on a budget (1 call per
symbol per poll), or use WebSockets on Extended; evaluate with hysteresis and cooldown; send only to the
user. Persist alert state to survive restarts. Done: one alert per crossing, stale snapshots never trigger,
the daily call budget is computed in the README, and the bot is not added to groups or shared (that is
commercial use).

## 45. Spreadsheet research model

Input: Excel or Google Sheets workflow. Prefer the official add-ins (same plan limits) or `fmt=csv` URLs
for simple pulls; for heavier models, a local script writes a typed sheet. Keep raw and adjusted columns
separate, keep ISIN/codes as text, and label units. Done: refreshes don't expose the token in shared
copies, formulas recalculate, and call usage per refresh is known (each cell formula can be a request).

## 46. Sector and industry rotation monitor

> Method: [methods-technical-market §17](methods-technical-market.md#17-sector-cycle-phase-and-rotation) (cycle phase) and §18 (theme baskets).

Input: universe and horizon. Use the Screener (sector/industry fields, `refund_*` returns, market-cap
bands) for a current snapshot, or `General.Sector/Industry` from Fundamentals with bulk EOD for custom
aggregation; compute equal- and cap-weighted sector returns locally (no pre-computed sector series
exists). Done: classification date is shown (current classifications applied to history are a
retrospective assumption), and screens over 1,000 matches are partitioned.

## 47. Rates and yield-curve monitor

Input: countries and tenors. Use UST par/bill/real-yield series (all plans), `.GBOND` country tenors
(Fundamentals/All-In-One), policy and reference rates, and economic events for release calendars. Compute
slopes (10Y–2Y, 10Y–3M) on matched dates; changes in basis points. Done: missing tenors stay missing, the
release time of each macro print is shown, and yields are kept in percent vs decimal explicitly.

## 48. Corporate-action ledger and total-return reconstructor

Input: symbols needing auditable returns. Store raw OHLC, splits (ratio as new/old, e.g.
`1.000000/8.000000` is a 1-for-8 reverse split) and dividends (`unadjustedValue`, currency, ex/pay dates).
Rebuild split-only and total-return series and an as-of variant that uses only actions with ex-date ≤ D;
compare the rebuilt factor with `adjusted_close/close`. Done: differences are listed with the responsible
event, spin-off-like fractional events are flagged rather than treated as splits, and dividends are never
counted twice.

## 49. Covered-call / wheel tracker (US options)

Input: positions and strategy rules; Marketplace Options subscription. Pull chains for held underlyings by
expiry window, pick strikes by delta/moneyness rules, and track premium, assignment risk and P&L with the
user's actual fills. Done: index options are not substituted silently, stale `tradetime` quotes are flagged,
history before Q4 2023 is not fabricated, and the Marketplace quota is budgeted separately.

## 50. Migration from another data source

Input: an existing pipeline built on another dataset. Inventory fields and semantics (raw vs adjusted,
volume basis, units, time zones, session coverage), map identifiers via ISIN and symbol lists, and run a
reconciliation on a sample before switching: compare like with like (raw close vs raw close, adjusted vs
adjusted, consolidated daily volume vs consolidated). Done: differences are classified (basis, units,
session, corporate action, genuine anomaly) and documented; no other provider's endpoints or credentials
are added to the new code.

## Worked example A: dividend tracker vertical slice

1. Plan check: EOD All World covers `eod`, `div`, `splits`; Free works for one year of testing.
2. Resolve holdings: `exchange-symbol-list/LSE` and `/US` (2 calls) → match ISINs → `VWRP.LSE` (GBP),
   `ULVR.LSE` (GBX), `O.US` (USD).
3. Pull `div/{SYM}?fmt=json` per holding (1 call each): keep `date` (ex-date), `paymentDate`,
   `recordDate`, `unadjustedValue`, `value`, `currency`.
4. Entitlement = shares held at ex-date × `unadjustedValue` (split-safe) in the dividend currency; cash
   appears on `paymentDate`; convert with FX of the payment date.
5. Forecast = trailing 12-month unadjusted amounts × current shares, labelled as an assumption.
6. Daily refresh: bulk `eod-bulk-last-day/{EX}?type=dividends` (100 calls per exchange) or per-symbol `div`
   for small portfolios (cheaper below 100 symbols).
7. Tests: a 2-for-1 split between declaration and payment, a GBX stock paying a GBP dividend, a special
   dividend, and an accumulating ETF with no dividends.

## Worked example B: survivorship-aware daily backtest data

1. Universe: `exchange-symbol-list/US?type=common_stock` + `&delisted=1` (2 calls); store with retrieval
   date; drop `_old` duplicates only after identity checks.
2. Prices: `eod/{SYM}` full history (1 call each, ~50,000 calls for all US common stocks including
   delisted — spread over the day under the 1,000/min limit).
3. Actions: `splits` and `div` per symbol if you need ledger accounting; otherwise use `adjusted_close`
   for total-return research and never add dividends again.
4. Eligibility at each date: has a bar, price/volume thresholds on split-adjusted values, membership if an
   index universe (S&P 500 history from 2012 via `GSPC.INDX` Fundamentals).
5. Execution: signal at close D, fill at open D+1 using raw open × that day's `adjusted_close/close` so
   fills and marks share a basis.
6. Disclose: delisted fundamentals are mostly post-2018; delisting proceeds are unknown; adjusted values are
   today's vintage.

## Worked example C: intraday opening-range study

1. Plan: EOD+Intraday Extended; probe each symbol's first 1m bar (SPY starts 2013-08-13).
2. Windows: 1m in 119-day chunks (`from`/`to` Unix UTC), 5 calls each; ~10 years ≈ 31 requests per
   symbol.
3. Sessions: convert UTC to America/New_York with the exchange calendar (`v2/exchange-details/US`),
   drop holidays, handle early closes (13:00), keep pre-market separate.
4. Opening range = first N minutes of the regular session from 09:30 local; nulls are no-trade minutes.
5. Prices are unadjusted: rescale pre-split bars by the split ratio before multi-year comparisons.
6. Tests: DST transitions, early-close days, a split day, and a symbol with sparse minutes.

## Method recipes 51–98 (cases from the wider skill-pack review and product review)

Each recipe points to the method chapter that holds the formulas, steps and acceptance checks. Inputs that
EODHD does not provide are marked *user-supplied*. Call costs follow [plans-limits.md](plans-limits.md).

### Portfolio, performance and risk — [methods-performance-risk.md](methods-performance-risk.md)

**51. Holdings risk report.** *User* tickers/weights + stated benchmark (TR index or ETF) → EOD, UST bills,
General, insider, sentiment → portfolio stats, per-holding flags (RSI, %B, ATR, insider net, sentiment),
stress rows. Done: benchmark basis printed, missing data shown as n/a, component VaR sums to 100%.

**52. Performance tearsheet / client period report.** *User* NAV and cash-flow ledger + TR benchmark + UST
bills → TWR (gross/net), MWR, period and monthly tables, ratios, drawdowns. Done: months compound to the
year; periods ≤1 year not annualized; TWR and MWR both labelled.

**53. Stress-test report.** Holdings + dated scenario library → full EOD history for holdings, FX and
benchmark → scenario P&L with proxy flags and coverage weights. Done: cash-only = 0; benchmark replays exactly.

**54. Rebalance proposal.** *User* accounts, lots, targets, bands + latest raw closes and FX → drift table,
cash-flow-first then tax-aware trades. Done: weights inside bands; every trade labelled *proposed*.

**55. Allocation lab (walk-forward vs equal weight).** Aligned adjusted returns → shrunk covariance →
min-variance, ERC, HRP, inverse-vol on identical dates and costs. Done: Sharpe-difference CI reported; "no
edge" stated when warranted.

**56. Current vs proposed what-if.** Same inputs as 51 for two weight vectors → side-by-side volatility, beta,
max drawdown, VaR, exposures, transition turnover. Done: identical windows and benchmark.

### Quant research and validation — [methods-quant-research.md](methods-quant-research.md)

**57. Factor evaluation report.** Factor definition + delisted-inclusive universe + horizons → IC, IC-IR,
Newey-West t, decay, quantile monotonicity, turnover, neutral variants, gates. Done: trial count recorded.

**58. Backtest validation gauntlet.** [Strategy spec](../assets/strategy-spec.md) + trial ledger + gross
returns/weights → cost ladder, IS/OOS rule, bootstrap CI, deflated Sharpe, PBO, parameter plateau,
Benjamini-Hochberg → PASS/WARN/FAIL. Done: a FAIL verdict is a valid deliverable.

**59. Execution-quality (TCA) report.** *User* fills with timestamps → finalized 1-minute bars → shortfall
decomposition vs decision price, interval VWAP. Done: participation labelled overstated; unmatched fills listed.

**60. Capacity and cost study.** Target weights + AUM grid → ADV and volatility from EOD, OHLC spread
estimates, square-root impact, participation cap → net return vs AUM. Done: binding names and break-even AUM.

**61. Signal outcome ledger and forecast scoreboard.** Alerts/screens with optional probabilities →
append-only ledger, nightly maturation via bulk EOD → cohort stats with Wilson CIs, Brier/log loss/ECE.
Done: pending vs matured separated; delisted signals kept as unresolved.

**62. Pairs research and monitor.** Candidate pairs → Engle-Granger on training only, BH across
candidates, half-life, z-score rules as declared trials, rolling monitor. Done: stop-trading rule per pair.

**63. Drift monitor for a deployed screen or model.** Reference window vs live feature/prediction log →
PSI/KS, rolling IC, calibration drift, data-event classifier (restatement, unit change, rename).

### Technical, market timing and setups — [methods-technical-market.md](methods-technical-market.md)

**64. Daily market recap.** Regions + watchlist → index and sector-ETF EOD, screener movers (cleaned), UST
curve, commodities, economic events. Done: every row dated; FTSE/Russell answered with the boundary.

**65. Market-timing monitor.** Index OHLCV → distribution-day count and follow-through-day state machine,
run after final bars; alert on state change only.

**66. Setup scanner with trade plans.** Screener universe (nyse/nasdaq) + EOD archive → trend template,
VCP, momentum burst computed locally → entry/stop/R targets/time exit or a refusal. Signal at close, fill
next open.

**67. PEAD / earnings-reaction tracker.** Earnings window → reaction session by `before_after_market`,
score, weekly stages. Done: after-market reports map to the next session; missing timing flagged.

**68. Dividend health monitor.** Holdings → `div` (json) + SplitsDividends + cash flow → OK/WARN/REVIEW.
Done: specials excluded; unchanged dividend between raises is not a cut.

**69. Single-stock decision brief.** Symbol, horizon, peers, loss budget → figure checks, factor
percentiles, sourced outlook, levels, separate fair-value table, thesis log. Probabilities only after
calibration.

**70. Technical API cross-check harness.** Same `from` for API and local code → compare to 4 dp; flags key
drift and basis changes (adjusted vs raw per function).

### Fundamentals, valuation and research — [methods-fundamentals-valuation.md](methods-fundamentals-valuation.md)

**71. Comps sheet and tear sheet.** Frozen peer set → one Fundamentals call per name + EOD → LTM, EV
bridge, not-meaningful-aware quartiles. Done: EV and margins recompute within 0.1%; exclusions listed.

**72. DCF workbook with EODHD inputs.** UST 10Y + regression beta + *user* ERP + cost of debt with
fallbacks → mid-year FCFF, Gordon and exit terminal value, centred sensitivity grid, reverse DCF.

**73. Earnings preview and post-earnings pack.** Calendar and history → pre-report trend snapshot,
reaction distribution, optional options-implied move → post-report revision log (append-only).

**74. Thesis tracker.** Thesis pillars → field-bound KPIs on dated captures, invalidation rules with
hysteresis, evidence log. Done: deterministic re-run; restatements logged as such.

**75. Listed strategic-buyer screen.** Target industry + size gate → Fundamentals per candidate →
leverage, cash, stock capacity → tiers. Private buyers and deal terms user-supplied.

### Options, rates, FX and macro — [methods-options-rates-macro.md](methods-options-rates-macro.md)

**76. Options chain archiver and IV history.** Nightly chain per underlying (Marketplace) → stored with
spot, rate, T → constant-maturity ATM IV, 25-delta risk reversal, put/call ratios, OI change. IV rank is
"unavailable" until enough sessions are stored.

**77. Earnings implied-move monitor.** Calendar timing + pre/post-event expiries → implied move vs actual
reaction. History starts Q4 2023.

**78. Gamma-exposure estimator.** Full chain with open interest → GEX by strike/expiry, zero-gamma flip,
walls, boundary banner (EOD snapshot, dealer sign assumed, no index options).

**79. Treasury curve analytics.** UST par/real/bill → bootstrapped zero and forward curves, slopes,
breakevens, shape label; DV01, G-spread for *user* bonds. Done: par bonds reprice to 100.

**80. Central-bank meeting preview.** Policy rates + next decision + releases since last meeting + 2Y −
policy proxy + curve snapshot. No implied probabilities claimed.

**81. Macro-surprise event study.** Economic events with standardized surprises (prior releases only) →
session-mapped returns for equities, bonds, FX, gold. Done: no-look-ahead test passes.

### Planning, wealth and journals — [methods-planning-wealth.md](methods-planning-wealth.md)

**82. Retirement / FIRE simulator.** Annual panel (TR index or ETF; price index + labelled yield splice;
UST bond model; annual CPI) → rolling start years and block bootstrap with fixed, guardrail and VPW rules →
success rate, failure years, terminal-wealth percentiles, lever table.

**83. Tax-lot ledger and harvest screen.** *User* transactions across accounts → split ledger, lot
relief (FIFO/HIFO/specific), realized report, loss candidates, repurchase-window check, replacement ranking
by overlap/correlation. Jurisdiction rules user-supplied.

**84. Advisory fee and client report pack.** Household accounts marked at raw close × qty → tiered fees
with proration, gross/net period table, blended TR benchmark.

**85. Trading-statement audit.** *User* fills → round trips, reconciliation, required starting equity,
Wilson CI, ruin simulation, behaviour flags, MAE/MFE from 1-minute bars, benchmark TWR.

### Data engineering — [data-engineering-patterns.md](data-engineering-patterns.md)

**86. Orchestrated daily exchange load (cron/Airflow/Dagster/Prefect).** Calendar partitions, close +
lag schedule, date guard, action-triggered re-pull, quality suite, view swap. Done: holiday skipped; a 402
halts every job on the key; replay is a no-op.

**87. Replayable WebSocket recorder.** Append-only log → event-time 1-minute bars with lateness →
idempotent sink → nightly reconciliation with finalized intraday.

**88. Listing history (SCD2) from symbol-list captures.** Weekly active + delisted captures → versions with
explicit absences, `_old` reuse and renames. Validity = capture dates, documented as such.

**89. Warehouse-backed BI dashboard.** Approved views + column dictionary + aggregation rules → Power BI /
Superset / Metabase; tie-out before release; shared workspaces need a commercial licence.

**90. Pipeline cutover / parity harness** (extends 50). Frozen captures → counts, anti-joins, per-listing
digests, tolerances, parallel run ≥10 sessions incl. a holiday and an action day, rehearsed rollback.

### Applications and AI — [app-ai-patterns.md](app-ai-patterns.md)

**91. Candlestick chart with markers and levels.** `eod`, `div`, `splits` (3 calls) → one-basis payload
with gaps and snapped markers, MAs, as-of support/resistance, provenance label.

**92. Private Streamlit dashboard.** Secrets, cached client, keyed `cache_data`, timed live fragment with
call budget, backfills as a separate job, staleness badges from observation time.

**93. Assistant evaluation and ask-my-archive.** Golden question set with capture-pinned numbers,
refusals and injection items; deterministic numeric scoring, recall@k/MRR; read-only NL-to-SQL over
approved views with deterministic rechecks. Synthetic demo dataset for public repos.

### Filing-native, regional and delivery recipes

**94. SEC filing-native company screen and profile.** US universe from `/api/sec-companies` (≈60 pages,
cached) → weekly `snapshot` per company (10 calls each, ≈59,000 for the full directory) → screen on ratios
and growth with definitions shown (`debt_to_equity` = liabilities/equity), drill down with `financials` and
`segments`, reconcile against Fundamentals. All-In-One. Done: nulls stay unscored, banks are not failed for
null liquidity ratios, and each value links to its period and filing date.
([methods-fundamentals-valuation §10.6](methods-fundamentals-valuation.md#106-sec-company-analytics-filing-native-fundamentals))

**95. Australian income tracker with franking.** `.AU` holdings → `/api/asx-corporate-actions?type=dividends`
(1 call per page) + EOD → cash and grossed-up income with a user-supplied company tax rate, specials
shown separately, DRP shares, capital returns and bonus issues posted to the ledger, rights issues and SPPs
listed as open offers. Done: ex/record/payment dates kept apart, franking shown but not applied as a tax
result. ([funds-income](funds-income.md#australian-asx-income-franking-drp-and-other-corporate-actions))

**96. Use the official tool first.** Spreadsheet, BI, no-code download, website widget, trading-platform or
AI-assistant requests → [official-tools.md](official-tools.md) → recommend the existing tool with plan and
call-cost notes; build only when the requirement exceeds it, and say why.

**97. Reproducible research notebook.** Parameters cell → cached pulls (token excluded from cache) → checks →
analysis → dated conclusions; `papermill` runs, stripped outputs in git, synthetic data for public sharing.
([code-patterns §13](code-patterns.md#13-notebook-research-jupyter))

**98. Alert and event relay via webhooks.** Alerts, screener hits or pipeline events → deterministic event
id → signed POST with retries and a dead-letter table → receiver verifies signature, freshness and
duplicates. Done: one event per crossing even after retries; personal destinations only unless licensed.
([code-patterns §14](code-patterns.md#14-outbound-webhooks-for-alerts-and-events))

## Further methods covered by the chapters

The chapters also support three-statement/DCF/comps/LBO/merger models; due diligence and investment memos; NAV/GL reconciliation and accruals; wealth planning and decumulation; trade journals and cost-basis ledgers; covariance optimization and attribution; pairs/cointegration, breadth, earnings drift, breakout and regime studies; option payoff/surface analysis; feature stores and purged validation; schema evolution, backfill/replay and observability; and chart/workbook/report generation.

Some requested capabilities have no EODHD equivalent: private client onboarding, broker order entry, DEX/wallet execution, prediction markets, detailed property/insurance/tax records, or strict historical data vintages. Keep their mathematical/workflow concepts only as explicitly user-input modelling or interface boundaries. Do not create another data-service integration to conceal the gap.
