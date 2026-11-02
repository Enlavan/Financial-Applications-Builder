# Public EODHD API library

Read [the integration contract](../api-contract.md) before selecting an endpoint. This is a curated snapshot, not a claim that every example has been live-tested with your key.

- [Endpoint contracts and response fields](endpoints/README.md)
- [General field definitions and instrument guides](general/README.md)
- [Subscription scope](subscriptions/README.md)

The library retains the public EODHD service paths, including Marketplace path segments. A branded segment inside an EODHD Marketplace route is part of the actual EODHD API, not an instruction to connect to another provider.

## Common routes through the library

| Task | References |
|---|---|
| EOD, actions, backfills | [Historical prices](endpoints/historical-stock-prices.md), [corporate actions](../corporate-actions.md), [ingestion](../ingestion.md) |
| Fundamentals fields | [Company](general/fundamentals-common-stock.md), [ETF](general/fundamentals-etf.md), [fund](general/fundamentals-fund.md), [ratios](general/financial-ratios-calculation-guide.md) |
| Security discovery | [Exchange tickers](endpoints/exchange-tickers.md), [search](endpoints/stocks-from-search.md), [ID Mapping](endpoints/id-mapping.md), [symbol changes](endpoints/symbol-change-history.md) |
| Intraday/live | [Historical bars](endpoints/intraday-historical-data.md), [WebSocket fields](endpoints/websockets-realtime.md), [live quotes](endpoints/us-live-extended-quotes.md) |
| Screening and events | [Screener](endpoints/stock-screener-data.md), [earnings](endpoints/upcoming-earnings.md), [news](endpoints/company-news.md), [congressional disclosures](endpoints/congressional-trades.md) |
| Macro and markets | [Macro](endpoints/macro-indicator.md), [commodity history](endpoints/commodities.md), [sessions](endpoints/trading-hours-v2.md) |
| Filing-native analytics and ASX actions | [SEC Company Analytics](endpoints/sec-company-analytics.md), [ASX corporate actions](endpoints/asx-corporate-actions.md), [SEC filings](endpoints/sec-filings-api.md) |
| Options and indices | [Options EOD](endpoints/us-options-eod.md), [contracts](endpoints/us-options-contracts.md), [index membership](endpoints/index-components.md) |

Use exact fields from the relevant schema. Do not infer a public interface from a script's endpoint selector or a similar product name. Some original examples are illustrative and require additional validation, pagination and input handling in an application.
