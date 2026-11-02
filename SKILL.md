---
name: eodhd-financial-applications-skill
description: "Design, build, test and explain financial applications on the EODHD API: investing dashboards, portfolio and dividend trackers, screeners, alert bots, backtests and research datasets, valuation and fundamentals tools, options and macro analytics, AI/MCP assistants, spreadsheets and reports. Use whenever a task involves EODHD/eodhistoricaldata data or its endpoints, choosing an EODHD plan, API call budgets or limits, ticker/exchange formats, adjusted vs raw prices, delisted or point-in-time data, or personal-vs-commercial use of the data — even if the user only describes the app they want."
---

# EODHD Financial Applications Builder

Turn an investing or research intention into a working, appropriately scoped system. Use EODHD for financial data retrieval. Keep programming libraries, local storage, charting, statistical methods, and user-supplied portfolio inputs independent of the data service.

This is one skill with task-specific references. **Do not load the whole library.** Read the integration contract, then the one or two workflow chapters relevant to the task. The `methods-*`, `data-engineering-patterns` and `app-ai-patterns` chapters run 1,600–2,400 lines each (up to ~25,000 tokens): read the contents list at the top, then open only the section you need by line range or by searching for its heading. Never read one end to end. References contain methods and public API knowledge, not prebuilt guarantees of coverage or returns.

## Start with the requested outcome

1. Determine the deliverable: answer/report, workbook, prototype, production application, data repair in the user's own archive, or review of existing code. Continue within that scope.
2. Identify assets, exchanges, dates, frequency, currency, required fields, freshness, audience, and the decision the system supports. Infer routine choices; ask only for information that materially changes the build. A simple task does not require a full architecture interview.
3. Read [the EODHD integration contract](references/api-contract.md) and, for plan/cost questions, [plans and limits](references/plans-limits.md). Select actual endpoints and check a small representative response with the user's authorized credentials or supported demo access. Keep verified access separate from documented coverage. If the request cannot reach eodhd.com at all, see [the next section](#when-eodhdcom-is-unreachable).
4. For a build, use [architecture and delivery](references/architecture.md) and the relevant [recipe](references/build-recipes.md). Implement a useful vertical slice, then extend it. For analysis, compute from retrieved observations and retain dates and units.
5. Verify the result against the task: calculations, schemas, edge cases, relevant UI behavior, and coverage. State what was tested and any limitation that changes the conclusion. Never claim a live test or a completed data correction without evidence.

## When eodhd.com is unreachable

Live checks need outbound HTTPS to `eodhd.com`. Claude Code and the user's own machine normally have it. Code execution in claude.ai and the Claude apps reaches only the domains its network settings allow, and code execution through the Claude API has no internet access at all. A proxy or tunnel error (including a proxy's `403 Forbidden`), a DNS failure, a reset connection or a "host not allowed" message comes from the sandbox before any EODHD response. Do not report the API as down, the key as invalid or the data as missing because of it. Only a status returned by eodhd.com itself (401, 402, 403, 404, 429) says something about the account or the data.

- If EODHD MCP tools are connected (`https://mcp.eodhd.com/v2/mcp`, OAuth; claude.ai accepts it as a custom connector), use them for the check and the data.
- Otherwise tell the user once that `eodhd.com` has to be allowed in the code-execution network settings, or give them the code or request URL to run themselves. Continue from the documented response shape in the API references and mark the result as not live-verified.
- Never ask the user to paste an API key into the conversation to get around the block.

## Essential invariants

- Do not substitute another financial-data provider, its endpoints, credentials, SDK, terminal, or scraping workflow. An unavailable EODHD input stays unavailable, is supplied by the user, or becomes an explicitly labelled modelling assumption. Ordinary Python/SQL/JS libraries are fine.
- Keep keys server-side or in environment variables. Do not place them in source control, browser bundles, public reports, prompts, request logs, or downloadable samples.
- An endpoint response, an empty response, a subscription entitlement, and complete historical coverage are four different things. Diagnose them separately.
- Preserve EOD raw OHLC, adjusted close, and split-adjusted volume as distinct series. Do not double-count dividends. Keep price, financial-statement, distribution, and reporting currencies distinct.
- Historical corrections overwrite the available API version. Local dated captures preserve what **you retrieved**; they cannot recover unavailable historical vintages. A filing date alone does not make revised fundamentals point-in-time.
- Missing values and missing bars are not zero. Unknown publication time, identity, or execution price must not silently become known.
- EODHD supplies data and analytics, not broker execution or customer account/transaction records. Build simulations explicitly; do not invent trading, wallet, payment, or order-placement endpoints.
- Use [licensing guidance](references/licensing.md) when audience or deployment makes it relevant. Private individual research is distinct from team, business, public-display, or redistribution use. Do not make a separate support-approval step for explicitly permitted personal uses.
- Do not expose private operational details or use support-side account access. Only public documented interfaces belong in generated applications.

## Quick facts that change designs

- Plans: Free (20 calls/day, 1 year EOD) · EOD All World (EOD, actions, bulk, delayed live) · EOD+Intraday Extended (+ intraday, technicals, screener, WebSockets) · Fundamentals Data Feed (fundamentals, calendar, macro — **no prices**) · All-In-One (everything core). Marketplace (US options, constituent history for indices other than the S&P 500, …) is separate from all of them. Two plans union APIs, not limits.
- Costs per request: EOD/splits/dividends/lists 1 · live 1 per symbol · intraday/technical/screener 5 · news 5 per ticker · fundamentals/options/macro 10 · bulk exchange 100 · `/api/user` 0. Limits: 1,000 requests/min; 100,000 calls/day (midnight GMT); Marketplace 100,000 per product per 24 h from first request. 402 = daily limit, 429 = minute limit/Marketplace.
- Symbols are `CODE.EXCHANGE`; all US venues are `.US`; Milan is beta on `cboe.eodhd.com`; no FTSE or current Russell indices; some markets are not covered at all (a Search hit is not coverage — probe); LSE/JSE can quote in minor units (`GBX`, `ZAC`) — read currency per symbol.
- EOD OHLC raw, `adjusted_close` split+dividend adjusted (restated over all history on new actions), volume split-adjusted, intraday unadjusted; regular session only in daily bars.
- Fundamentals keep one current value per period. A restatement can replace it while the original `filing_date` stays, so `filing_date` and `Earnings::History` `reportDate`/`beforeAfterMarket` give timing, not the number as first published. Point-in-time sources are narrow: SEC Filings API 10-K/10-Q rows (US filers, one row per filing with `accession_number` and `filed_at`; All-In-One, 10 calls; short history, e.g. oldest 10-Q 2015 for AAPL, 2020 for AMZN), S&P 500 membership (`GSPC.INDX` `HistoricalTickerComponents` or `historical=1`, from April 2012) and economic-event `actual` (first release). For anything else, archive forward ([temporal research](references/temporal-research.md)).
- Intraday windows: 1m ≤120 days, 5m ≤600, 1h ≤7200 per request; finalized 2–3 h after close; per-symbol start dates vary. Weekly EOD bars are labelled with Monday but close on Friday.
- Total-return benchmarks exist (`SPXTR`, `SP500TR`, `XNDX`, `DJITR` on INDX); price indices have `adjusted_close == close`.

## Choose the references

| User wants | Read |
|---|---|
| “Build an app”, “What can I make?”, ambiguous system idea | [Intent map](references/intent-map.md), [build recipes](references/build-recipes.md), [architecture](references/architecture.md) |
| Which plan, what it costs in calls, limits, error codes, quotas | [Plans, limits and call costs](references/plans-limits.md) |
| Ticker formats, exchange coverage, units, start dates, known data behaviour | [Coverage notes](references/coverage-notes.md) |
| A failing integration or a confusing response ("403", "empty", "100× too big", "data changed") | [Support casebook](references/support-casebook.md) |
| Code: client with limiter, backfill windows, bulk updates, screener paging, WebSocket recorder | [Code patterns](references/code-patterns.md) |
| Download data, large backfill, ETL, database, scheduled jobs | [Ingestion](references/ingestion.md), [storage and contracts](references/storage.md), [operations](references/operations.md) |
| Tickers, ISINs, renamed/delisted instruments, historical universe | [Identity and universe](references/identity.md) |
| OHLC, dividends, splits, adjusted prices, FX and units | [Data semantics](references/data-semantics.md), [corporate actions](references/corporate-actions.md) |
| Minute/tick data, streaming, calendars, quote freshness | [Intraday and streaming](references/intraday.md) |
| “As known then”, archived data, publication timing | [Temporal research](references/temporal-research.md) |
| Screener, technical signals, market breadth, pairs | [Screening and signals](references/screening.md) |
| Backtest, event study, strategy evaluation | [Backtesting](references/backtesting.md), [validation](references/research-validation.md) |
| ML, factor models, embeddings, model monitoring | [ML and factors](references/ml-factors.md), [AI and MCP](references/ai-mcp.md) |
| Company analysis, financial statements, DCF, deal models | [Fundamentals](references/fundamentals.md), [valuation and modelling](references/valuation.md) |
| Portfolio, attribution, rebalancing, position sizing, stress | [Portfolio and risk](references/portfolio-risk.md) |
| ETF/fund analysis, dividend income, FIRE | [Funds and income](references/funds-income.md), [planning](references/personal-planning.md) |
| Earnings, news, insider/political disclosures | [Events and news](references/events-news.md) |
| Options, macro, rates, FX, crypto, credit, real estate | [Options](references/options.md), [cross-asset research](references/cross-asset.md) |
| Paper trading, trading journal, order simulation | [Paper trading and accounting](references/paper-accounting.md) |
| UI, charts, spreadsheet, PDF, presentation | [Applications](references/applications.md), [reports and workbooks](references/reports.md) |
| Bad data, endpoint discrepancies, regression tests | [Quality and reconciliation](references/quality.md) |
| Firm, advisory, fund administration, compliance systems | [Professional workflows](references/professional-workflows.md), [licensing](references/licensing.md) |
| Formulas and checks: returns, Sharpe/Sortino/attribution, volatility estimators, VaR/ES, stress tests, allocation (MV, BL, ERC, HRP), rebalancing, position sizing | [Performance and risk methods](references/methods-performance-risk.md) |
| Factor tests (IC), overfitting (deflated Sharpe, PBO, CPCV), multiple testing, stationarity/regimes, costs/impact/capacity, TCA, pairs, forecast scoring, drift | [Quant research methods](references/methods-quant-research.md), [strategy spec](assets/strategy-spec.md) |
| Indicators and Technical API conventions, breadth, distribution/follow-through days, setups (trend template, VCP, CANSLIM), PEAD, screener mapping, dividend monitor, daily recap | [Technical and market methods](references/methods-technical-market.md) |
| Fundamentals field map, TTM, ratio library, DCF/DDM/residual income, comps, earnings preview/post, thesis tracker, research report gates, buyer screen | [Fundamentals and valuation methods](references/methods-fundamentals-valuation.md) |
| Options pricing/IV/skew/GEX/implied move, Treasury curve bootstrapping, breakevens, credit, FX forwards/carry, macro events and surprise studies | [Options, rates and macro methods](references/methods-options-rates-macro.md) |
| Retirement/FIRE simulation, capital-market assumptions, IPS, tax lots and harvesting, AUM fees, client reporting, trading-statement audit | [Planning and wealth methods](references/methods-planning-wealth.md) |
| Schedulers (cron/Airflow/Dagster/Prefect), dbt layer, executable DQ suite, SLAs, warehouse DDL, stream log, SCD2 listings, parity tests, CI and secrets | [Data-engineering patterns](references/data-engineering-patterns.md) |
| Chart payloads (Lightweight Charts), Streamlit, UI conventions, dashboard tie-out, AI evaluation, NL-to-SQL, news RAG, private MCP server, synthetic data | [App and AI patterns](references/app-ai-patterns.md) |
| Spreadsheet add-ins, Power BI, no-code downloader, SDKs (Python, Node, R, .NET, Java, PHP, MATLAB), NinjaTrader, WordPress, Chrome extension, Telegram bot, Postman | [Official tools — check first](references/official-tools.md) |
| US filing-native statements/ratios/segments (SEC Company Analytics); ASX franking, DRP and corporate actions | [Fundamentals methods §10.6](references/methods-fundamentals-valuation.md#106-sec-company-analytics-filing-native-fundamentals), [funds and income](references/funds-income.md) |
| Jupyter notebooks; pushing alerts/events to other systems (webhooks) | [Code patterns §13–14](references/code-patterns.md) |
| Exact public API fields, parameters and examples | [API index](references/api/index.md); open only the endpoint/general guide needed |

## Included helpers and templates

- `scripts/eodhd_request.py`: bounded HTTPS GET collector with EODHD host restrictions, URL encoding, token redaction, retry limits, and local raw-response capture. Read its help first. It does not exhaust pagination automatically.
- `scripts/eodhd_client.py`: adapted compatibility CLI for the original EODHD endpoint recipes. Prefer the bounded collector for production ingestion; this CLI is a single-request reference, not a scheduler.
- `scripts/financial_checks.py`: deterministic OHLC checks, adjustment factors, point-in-time eligibility, and attribution calculations; run `--self-test` to verify examples.
- [Build specification](assets/build-spec.md), [dataset contract](assets/dataset-contract.json), [research record](assets/research-record.md), [QA cases](assets/acceptance-cases.md) (45 cases, over half drawn from real support questions), [strategy spec](assets/strategy-spec.md), [governance manifest](assets/governance-manifest.md).

API references are a **2026-10-25 snapshot**. Public contracts in `api-contract.md` and the curated workflow chapters take precedence over older illustrative examples. Check current official documentation when implementing a changing endpoint or library version.
