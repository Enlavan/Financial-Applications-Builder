# Point-in-time discipline and local archives

> Methods with formulas, steps and acceptance checks: [methods-quant-research](methods-quant-research.md).

## Four times, not one

Track `period_end/event_time`, `published_at` if known, `retrieved_at`, and `decision/execution_time`. Track the value version too. A quarterly value dated March 31 may have become public weeks later and been restated years later. Moving its date to a filing date while retaining the latest restated number fixes only one source of look-ahead.

For a fact to enter a decision, its required information must have been observable by then, its value version and identity mapping must be appropriate, every derived parent must be admissible, and the execution rule must occur after the decision could actually be made. The application should expose why a record was excluded.

EODHD Fundamentals, adjusted prices and most other datasets serve the current version, without an as-of parameter or revision ledger. Which version a past period carries is not predictable either. In October 2026, `GE.US` 2017 quarters showed revenue recast in 2018 (Q1 26,880 against 27,660 first reported) beside their original 2017 `filing_date`, while `KHC.US` 2017 quarters still showed the figures from before its 2019 restatement. Treat `filing_date` as timing evidence, never as proof that the value beside it is the one published then. Do not manufacture `available_at` from period end, row order or today's retrieval timestamp. A delay assumption can define a conservative sensitivity analysis; it does not certify strict point-in-time correctness.

## Point-in-time sources EODHD does provide

| Need | Source | Limits |
|---|---|---|
| US statements as each filing reported them | SEC Filings API `/api/sec-filings/{SYMBOL}/10q` and `/10k`: one row per filing with `accession_number`, `filed_at` (public date) and `period_of_report` ([reference](api/endpoints/sec-filings-api.md), [method](methods-fundamentals-valuation.md#105-sec-filings-10-k-10-q-8-k-in-research-workflows)) | US filers only; All-In-One; 10 calls per request, up to 100 rows per page. History is short and varies by company: in October 2026 the oldest 10-Q was 2015 for `AAPL.US`, 2018 for `TSLA.US` and 2020 for `AMZN.US`, so read `meta.total` and the oldest `filed_at` before planning a sample. An amendment is a separate filing; probe one before relying on amended periods |
| S&P 500 membership on a past date | `fundamentals/GSPC.INDX` `HistoricalTickerComponents` (join and leave dates, removed and delisted members included) or `historical=1&from=&to=` snapshots | From April 2012; only the latest interval per ticker; other indices need the Marketplace constituents product |
| Macro surprise at release | `economic-events` `actual` (first release, UTC time) | From 2020 |
| When results became public | Fundamentals `Earnings::History` `reportDate` and `beforeAfterMarket`; quarterly `filing_date` | Timing only; the values beside them are current |

Use these where they apply and label the rest of the dataset as current-vintage.

## Three project modes

| Mode | Honest claim |
|---|---|
| Current-vintage retrospective research | Historical calculations using currently available values; disclosed revision/identity limitations |
| Forward archived research | Reproducible decisions from versions this application actually captured from its start date |
| Strict historical information-set study | Requires contemporaneous versions, public timing and valid historical identity evidence; unsupported portions must remain excluded/unproven |

Dated captures are valuable even without strict historical vintages. Record hash, endpoint, safe parameters, retrieval UTC, parser version, schema and transformation dependencies. A hash proves file identity, not factual accuracy or historical public availability.

## Temporal joins

Use a backward as-of join on the relevant known-availability time, with entity identity and a maximum age policy. Do not forward-join future facts. A derived Q4 = annual − nine-month YTD inherits the latest availability of both parents, compatible currency/basis and versions; it is not observable at the fiscal year-end by construction.

A date-only publication cannot establish an intraday trade at that day's close. For a conservative daily model, activate at a later actual session using the exchange calendar; disclose that policy. Weekday offsets miss holidays. A signal computed after the closing bar cannot buy at that same observed close unless an independently modelled pre-close process justifies it.

## Comparison experiments

If the required evidence exists, compare otherwise identical pipelines using period-end latest values, publication-dated latest values, originally observed versions, and execution-aware versions. Differences reveal timing/version sensitivity. Do not simulate an “originally observed” variant if those original records are absent. Keep the same universe, strategy, costs and sample when attributing differences to information timing.

## Research record

Record universe construction, security exclusions, current versus archived versions, decision timing, treatment of unknown dates, missingness, execution assumptions, code commit, parameters and all trial IDs. Store rejected hypotheses too. Filtering actions by ex-date reconstructs an as-of adjustment convention from present records; it cannot prove what those records or prices were known to be on that date.
