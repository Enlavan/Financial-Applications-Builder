# User intentions and reusable components

Match the user's language to a recipe; do not make them name an endpoint. The numbers below correspond to [the 98 build recipes](build-recipes.md). Components describe application capabilities, not guaranteed EODHD coverage.

Users rarely say "I need the EOD API". They describe a product. This table maps their wording to the archetypes in Part 2.

| What the user says | Archetype |
|---|---|
| investing dashboard, portfolio tracker, net-worth app, watchlist, personal market terminal, personal terminal, market overview page | 1. Personal investing dashboard |
| dividend tracker, income portfolio, FIRE planner, dividend calendar, yield-on-cost tool, DRIP calculator | 2. Dividend and income tracker |
| stock screener, scanner, idea generator, value screen, momentum scanner, filter app, "find stocks with P/E < 15" | 3. Screener |
| price alerts, notifier, Telegram/Discord/Slack bot, watch bot, daily digest email | 4. Alerts and notification bot |
| valuation tool, DCF model, fair-value calculator, fundamental analysis app, stock comparison, peer analysis | 5. Valuation and fundamental analysis |
| earnings calendar, events tracker, IPO tracker, split calendar, economic calendar | 6. Events and calendar tracker |
| news monitor, sentiment tracker, news-driven signals, headline scanner | 7. News and sentiment monitor |
| insider trading tracker, "follow the smart money", congress trades tracker | 8. Insider and political trades tracker |
| ETF analyzer, fund look-through, overlap checker, ETF comparison | 9. ETF and fund analyzer |
| multi-currency portfolio, FX converter, base-currency valuation | 10. Multi-currency valuation |
| backtester, strategy tester, trading-system research, "test my strategy on 20 years" | 11. Daily backtester |
| intraday backtester, scalping research, minute-bar study, opening-range study | 12. Intraday and tick research |
| survivorship-bias-free dataset, point-in-time universe, delisted-inclusive research | 13. Point-in-time research dataset |
| security master, identifier mapping, ISIN-to-ticker resolver, reference-data pipeline | 14. Security master and reference data |
| ML model, factor model, feature store, training dataset, deep-learning price prediction | 15. ML and factor research dataset |
| event study, earnings drift, look-ahead-bias guard, "no future leakage" research gate | 16. Event study and look-ahead-safe research |
| long-term study, "100 years of data", market history, index since 1900 | 17. Long-horizon historical study |
| macro dashboard, cross-asset monitor, rates/commodities/FX overview, recession indicator | 18. Macro and cross-asset dashboard |
| options analytics, volatility surface, Greeks dashboard, options backtest, wheel-strategy tracker | 19. Options analytics |
| crypto bot, crypto dashboard, coin screener, crypto backtest | 20. Crypto research |
| thesis, dissertation, university project, course assignment, research paper dataset | 21. Academic research |
| data-quality check, vendor comparison, reconciliation, "these datasets disagree" | 22. Data-quality harness |
| paper trading, forward test, shadow mode, simulation, demo account | 23. Paper trading and shadow mode |
| trading bot, algo trading, automated trading, execution engine | 24. Live algo trading bot |
| live ticker, heatmap, real-time board, streaming chart | 25. Real-time display |
| AI research assistant, Claude/ChatGPT with market data, MCP connector, "ask questions about stocks" | 26. AI assistant via MCP |
| AI agent, autonomous analyst, LLM pipeline, RAG over financial data, multi-agent research | 27. Autonomous AI agents and pipelines |
| AI signals app, AI stock picker, "GPT trading advisor" for users | 28. AI signal product |
| Excel model, Google Sheets portfolio, VBA downloader, no-code tool, WordPress site | 29. Spreadsheets and no-code |
| fintech app, robo-advisor, wealth platform, brokerage front-end, white-label widget | 30. Fintech or wealth product |
| website, blog charts, newsletter, YouTube or Telegram channel, community dashboard | 31. Public content and community project |
| team use, firm research, family office, fund, PE/VC, analyst desk, "our company" | 32. Internal use in an organization |
| data resale, B2B API, data feed for clients | 33. Redistribution and B2B |
| KYC, sanctions screening, credit-risk monitor, sovereign risk | 34. Compliance and risk data |
| tax report, cost-basis tool, historical price on date X, year-end valuation | 35. Tax and accounting helper |
| index replication, rebalancing tool, smart-beta / sector rotation | 36. Index and rebalancing tool |

## More user wording (recipes 37–98)

| What the user says | Recipe |
|---|---|
| "which plan do I need?", "do you have these tickers?", "test before I buy", coverage check | 37. Pre-purchase coverage probe |
| "download everything", local database, data lake, "mirror EODHD daily" | 38. Local market-data warehouse |
| "as it was known then", archive fundamentals/estimates, "track revisions" | 39. Point-in-time snapshot recorder |
| import my broker CSV, map ISINs, "load my broker export" | 40. Broker holdings import and resolver |
| earnings season tracker, surprise monitor, post-earnings drift | 41. Earnings season monitor |
| market breadth, advance/decline, risk-on/off, regime | 42. Breadth and regime dashboard |
| UCITS ETF portfolio, multi-currency funds, ISIN fund tracker | 43. Global ETF/fund portfolio |
| Telegram bot for me, price alert to my phone, daily email to myself | 44. Personal alert bot |
| Excel/Google Sheets model, "pull prices into my sheet" | 45. Spreadsheet research model |
| sector rotation, industry heatmap, sector performance | 46. Sector rotation monitor |
| yield curve, bond yields, rates dashboard, inversion tracker | 47. Rates and yield-curve monitor |
| total return calculation, dividend-adjusted series, verify adjusted close | 48. Corporate-action ledger |
| covered calls, wheel strategy, cash-secured puts | 49. Covered-call / wheel tracker |
| switching data vendor, migrate my pipeline, "numbers differ from my old data" | 50. Migration from another data source |
| risk report on my holdings, portfolio VaR, stress test, what if I rebalance | 51–56. Portfolio, performance and risk recipes |
| tearsheet, client report, TWR vs IRR, Sharpe/Sortino, attribution | 52. Performance tearsheet |
| is my backtest overfit, deflated Sharpe, factor IC, walk-forward validation | 57–58. Factor evaluation, validation gauntlet |
| transaction cost analysis, slippage vs VWAP, capacity of my strategy | 59–60. TCA, capacity study |
| pairs trading, cointegration, signal tracking, forecast calibration, model drift | 61–63. Signals, pairs, drift |
| market recap, distribution days, follow-through day, VCP/Minervini/CANSLIM scanner, PEAD | 64–70. Technical and market recipes |
| comps table, DCF with real inputs, earnings preview, thesis tracker, acquirer screen | 71–75. Fundamentals and valuation recipes |
| IV rank, implied move, gamma exposure, yield curve bootstrap, breakevens, Fed preview, macro surprise | 76–81. Options, rates and macro recipes |
| retirement Monte Carlo, safe withdrawal rate, tax-loss harvesting, advisory fees, trade journal audit | 82–85. Planning, wealth and journal recipes |
| Airflow/Dagster pipeline, dbt models, data quality tests, WebSocket recorder, Power BI | 86–90. Data-engineering recipes |
| TradingView-style chart, Streamlit app, evaluate my AI assistant, chat with my database | 91–93. Application and AI recipes |
| screen US companies from SEC filings, CIK to ticker, revenue by segment, as-filed ratios | 94. SEC filing-native screen |
| Australian dividends, franking credits, grossed-up yield, DRP, ASX rights issue or SPP | 95. Australian income tracker |
| prices in Excel/Google Sheets, Power BI, download all EOD files, NinjaTrader, WordPress widget, Python/R/Node library | 96. Official tool first |
| Jupyter notebook, reproducible research, papermill | 97. Research notebook |
| send alerts to my app/Slack/Discord/Zapier, webhook, push notifications | 98. Webhook relay |

## Component catalogue

This is the merged list of everything users described building, as reusable components. Use it to recognise the parts of a request and map each one to an API.

**Ingestion**
1. scheduled EOD pulls after exchange publication time
2. full-history backfill paced under the limits
3. bulk exchange pulls
4. intraday windowed downloader
5. 1m-to-5m/1h aggregation
6. corporate-action sync
7. fundamentals sync
8. news and sentiment sync
9. calendar sync
10. live poller
11. WebSocket recorder
12. FX reference collector
13. macro, rates and commodities collector
14. multi-host routing (cboe.eodhd.com)
15. universe and delisted sync
16. symbol-change feed

**Storage**
17. immutable raw-response archive
18. normalized tables
19. dated snapshots
20. revision diff engine
21. archive-on-first-retrieval
22. encrypted backups and retention after cancellation
23. provenance per record (endpoint, host, retrieval time, hash)
24. AI decision audit trail
25. private cloud deployment

**Reference data**
26. local application security ID
27. identifier observations and evidence-backed validity intervals
28. rename-versus-event classifier
29. series-to-security binding
30. issuer → listing chain
31. ticker-reuse guard
32. ISIN-to-symbol resolver
33. currency and unit normalizer (GBX, ZAc)
34. index catalogue with "not available" flags

**Universe**
35. delisted-inclusive universe with explicit historical-coverage limits
36. historical index membership
37. user-supplied constituent-list matcher
38. first-date coverage checker

**Adjustments**
39. k-factor full adjustment
40. split-only series
41. intraday adjuster
42. as-of adjusted series (only actions with ex-date on or before D)
43. volume and dollar-volume consistency
44. corporate-action completeness check
45. distribution tracker

**Time**
46. timestamp normalizer
47. session classifier
48. holiday calendar
49. freshness gate
50. trade-versus-quote discriminator
51. missing-bar handling
52. publication-time scheduler

**Quality**
53. cross-endpoint reconciliation
54. zero, null and missing detector
55. comparison against user-supplied captures on matched semantics
56. regression fixtures from the demo key
57. data-quality dashboard
58. pre-purchase coverage probe

**Analytics**
59. indicators
60. signals
61. rankings and screens
62. risk scores
63. statistics
64. daily backtester
65. intraday backtester
66. earnings event studies
67. look-ahead gate
68. benchmark-relative performance
69. emerging-market fundamentals research
70. long-horizon studies
71. cross-asset macro monitor
72. valuation and DCF
73. dividend income projection
74. ETF look-through and overlap
75. options surfaces and Greeks
76. insider and congress flow
77. sentiment scoring

**Simulation and trading**
78. paper-trading engine
79. shadow-mode logger
80. multi-currency valuation
81. market-data/signal interface separated from any separately authorized execution system

**AI**
82. MCP assistant
83. AI extract builder
84. autonomous agents over the archive
85. AI decision logging
86. office-app integration (Excel, Outlook, Sheets)

**User-facing**
87. local or password-protected dashboard
88. alerts and scheduled scans
89. private single-user notification bot; shared bots require commercial rights
90. future multi-user product (commercial)

**Compliance**
91. personal-versus-commercial classifier
92. retention-rights record
93. AI-use policy
94. fee check
95. plan-to-feature map
