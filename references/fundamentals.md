# Company research and statement normalization

> Methods with formulas, steps and acceptance checks: [methods-fundamentals-valuation](methods-fundamentals-valuation.md).

## Resolve the object first

Read `General.Type`, name, exchange, identifiers, primary ticker and currency. Stocks, ETFs, funds, indices and crypto expose different structures. Use a filtered Fundamentals request for the sections needed; do not repeatedly send a whole multi-year response to an LLM. SEC availability is a separate dataset question and may differ from fundamentals coverage for the same ticker. For US filers, the SEC filings API (All-In-One, 10 calls per request) returns parsed 10-K/10-Q statements with `filed_at` dates and 8-K item sections. Use it to cross-check `Financials` and to monitor material events ([methods §10.5](methods-fundamentals-valuation.md)).

## Financial periods

Preserve annual, quarterly and year-to-date duration explicitly. A balance sheet is a point-in-time stock; income/cash flow are period flows. Do not sum balance sheets. Non-US interim data may be half-year or cumulative rather than standalone quarters. Derive a quarter only from compatible parent periods, currency, basis and versions and record the derivation. Avoid doubling revenue just because EPS differs.

Use statement currency, not listing currency, for financials. Keep scaling (units/thousands/millions), sign convention, fiscal year and period dates. Missing `filing_date` or one equal to period end does not prove timely public availability. TTM requires four compatible nonoverlapping quarters, not merely the latest four dictionary entries.

## Core calculations

- Gross/operating/net margins use matching revenue and profit periods; zero/negative denominators require labelled interpretation.
- ROE/ROA generally pair period income with average balance-sheet equity/assets; disclose if only end balances exist.
- Net debt subtracts the chosen cash definition from interest-bearing debt; retain that definition.
- FCF commonly uses operating cash flow minus capital expenditure, with signs normalized; vendor fields may use another convention.
- EPS, earnings-calendar actuals and estimates may use different adjusted/GAAP bases. Compare like with like; a discrepancy alone is not proof either is wrong.
- Shares outstanding, weighted-average basic/diluted shares, float and split-adjusted historical shares are different quantities.
- Market cap = compatible price × shares for that date; a current share count times historical price is an estimate, not verified historical cap.

## Company brief workflow

1. Profile and business classification, with the observed metadata date.
2. Financial trend over comparable periods: growth, margins, cash conversion, balance-sheet risk.
3. Valuation against transparent assumptions and comparable peers; use currency-consistent multiples.
4. Price/volume context, events and news as separately timestamped evidence.
5. Insider/disclosure context where available, avoiding causality claims from filings alone.
6. A concise thesis, contrary evidence, catalysts, scenario range and data limitations that materially affect the result.

Formula-level pieces for the brief: YTD/1Y return rows, a dated macro block and a 90-day news block (methods §8.6), moat evidence with qualitative claims labelled as judgement (§9.2), and owner earnings (§3.14).

Separate observation, calculation, estimate and judgement in output. Cite public EODHD pages/request context without exposing tokens. Missing data is not permission to invent an industry average.

## Earnings review and peer comparison

Compare actual versus estimate on the same EPS/revenue basis, current versus prior-year comparable period, and guidance versus explicitly supplied prior guidance. Consensus and source values can change; store capture versions for monitors. Decompose beat/miss into operations, taxes, share count or one-offs only when the required evidence exists. The update's chart list (EPS actual vs estimate, reaction vs history, revision path) is in methods §10.2.

For peer tables choose business model, geography, fiscal period, growth/profitability and capital structure comparability. Show exclusions; do not rank a loss-making company as “cheap” because a negative P/E sorts first. Distinguish current screening multiples from a fully normalized analyst model.

## Regional note: China A-shares (SHG, SHE)

What the references state: Shanghai is exchange code `SHG` and Shenzhen is `SHE`, both trading in CNY;
tickers are 6-digit numbers with the suffix (`600519.SHG`, `000001.SHE`), and the suffix is required
because a bare 6-digit code is ambiguous (`000001.INDX` is the Shanghai Composite). End-of-day data is
updated about 17:00–18:00 CST, 2–3 hours after the 15:00 close. The IPO calendar includes `.SHG`
listings. Not stated in the references, so **verify with a probe** before promising them: the first
available EOD date per listing, live or delayed quote availability, fundamentals depth and statement
currency, and how B shares are coded. Probe with `exchange-symbol-list/SHG`, one `eod` request without
`from`, and one filtered Fundamentals request (`filter=General,Financials::Income_Statement::yearly`),
and record the results with their date.
