# EODHD integration contract

This curated contract resolves conflicts in the bundled 2026-10-25 reference snapshot. It describes customer-facing behavior only. Read the exact endpoint reference before coding; parameters, envelopes, pagination and entitlements differ by family.

## Authentication and transport

- Public REST base: `https://eodhd.com/api` (keep the `/api/` prefix; HTTPS only). The documented token transport is the `api_token` query parameter; `Authorization: Bearer <token>` was also accepted in a 2026-10-25 demo-key test and keeps tokens out of URLs. Request `fmt=json` where supported (some CSV outputs drop fields; Fundamentals is JSON-only). Read the token from `EODHD_API_TOKEN` or a server-side secret store and strip whitespace.
- Public account/usage endpoint: `/api/user`. Do not assume any field not present in its documented response. The billing/dashboard pages are another way for the user to inspect their plan.
- EODHD MCP: `https://mcp.eodhd.com/v2/mcp` uses OAuth. Use available tool descriptions and schemas; do not invent a tool name or assume a tool's pagination/filter parameters match REST exactly.
- Milan beta uses `https://cboe.eodhd.com` and `.MI` when available. Probe the current EODHD exchange list and the user's access before choosing a host. A historical reference listing an exchange is not a promise that it remains available.
- WebSocket connections use `wss://ws.eodhistoricaldata.com/ws/{us,us-quote,eu,eu-quote,forex,crypto,…}`. Allowance: 50 symbol subscriptions per token across all sockets, up to 64 connections; streaming costs no API calls. A successful REST call does not prove a WebSocket entitlement or vice versa.
- `401` invalid/missing token; `402` daily calls exhausted (stop until midnight GMT); `403` endpoint/ticker outside the plan or a wrong path; `404` unknown symbol (still charged); `422` invalid input; `429` minute limit (honour `Retry-After`) or Marketplace quota. Do not retry 401/402/403/404/422. A `200` containing an empty array is not evidence of no historical event (an invalid date can also produce it). Full table: [plans and limits](plans-limits.md#the-three-limits-and-error-codes).

Use `scripts/eodhd_request.py` for a bounded request with raw capture. Example:

```bash
python scripts/eodhd_request.py eod/AAPL.US --param from=2025-01-01 --param to=2025-01-31 --out captures/aapl
python scripts/eodhd_request.py fundamentals/AAPL.US --param filter=General --out captures/aapl-general
python scripts/eodhd_request.py id-mapping --param 'filter[symbol]=AAPL.US' --param 'page[limit]=10' --out captures/mapping
```

These commands consume the applicable request allowance. They do not establish coverage of all instruments or dates. For testing without a paid token, use `demo` only on explicitly supported demo symbols/endpoints; it is not universal access.

## Core and Marketplace access

Read [plans, limits and call costs](plans-limits.md) for the full plan-to-API matrix, call costs and
budgeting. The rules that most often change a design:

- **Free**: 20 calls/day, one year of EOD/splits/dividends, live delayed, search, symbol lists, ID mapping,
  news. No intraday, fundamentals, bulk, calendar or WebSockets.
- **EOD All World**: full EOD/splits/dividends, bulk EOD, live delayed, all exchanges, delisted. No
  intraday, fundamentals, calendar, screener, technicals.
- **EOD+Intraday Extended**: adds intraday, technicals, screener, WebSockets, exchange hours/holidays,
  symbol change history.
- **Fundamentals Data Feed**: fundamentals, calendar, macro, insider, market cap, GBOND, rates —
  **no end-of-day prices**. Prices + fundamentals = All-In-One or two plans.
- **All-In-One**: all core APIs, plus SEC filings, congressional trades, sanctions, `/api/ticks`. Bulk
  fundamentals needs Extended Fundamentals (via support).
- **Marketplace** (options, Marketplace ticks, S&P/Dow Jones historical constituents, trading-hours
  status, ESG, PRAAMS, logos …) is separate from every core plan, including All-In-One.
- Several subscriptions union their APIs; they do **not** add daily limits. A legacy permission flag is not
  a current product promise; new options projects use the Marketplace endpoints.

## Limits and pagination

Three independent limits: **1,000 requests/minute** (all request types; read `X-RateLimit-Limit`/
`X-RateLimit-Remaining`), a **daily call allowance** (20 Free, 100,000 paid; weighted by endpoint: EOD 1,
intraday/technical/screener/news 5, fundamentals 10, bulk 100; resets midnight GMT and the counter clears
on the first request after it), and **per-product Marketplace quotas** (100,000 calls per product, 10 per
request, window of 24 h from that product's first request). Extra purchased calls never expire and are
spent after the daily allowance; they do not extend Marketplace quotas. Pace evenly over the minute, use one
shared limiter per token, budget retries, and charge each request its endpoint weight. A bigger server does
not raise the allowance.

Pagination may use `limit/offset`, `page[limit]/page[offset]`, `links.next`, or bounded date windows. Follow the documented family, track repeated pages and termination, and reattach the token only to allowed EODHD URLs. Filter parameters may be flat or bracketed. Never move a filter to an invented parameter name because another endpoint uses it.

The Screener API takes JSON triples combined with AND, e.g. `[["exchange","=","us"],["market_capitalization",">",1000000000]]`. String fields accept `=`, `match` (word prefix, `*` wildcard), `in`, `not in`; numeric fields also `!=`, `>`, `<`, `>=`, `<=`. Curly quotes or a numeric operator on a string field return 422. `limit` is 1–500 and `offset` 0–999, so one screen yields at most 1,000 rows: partition by non-overlapping bands/exchanges, or download the universe and screen locally. Market cap is in each listing's own currency, and the same company can appear through foreign listings. `dividend_yield` is a fraction (0.03 = 3%) and a few secondary listings carry outliers — cap the upper bound. Signals (`200d_new_hi`, `wallstreet_lo`, …) narrow results like filters. The demo key does not work on the Screener.

## Additional public interfaces absent from older skill recipes

- `/api/id-mapping`: at least one of `filter[symbol]`, `filter[ex]`, `filter[isin]`, `filter[figi]`, `filter[lei]`, `filter[cusip]`, `filter[cik]`; `page[limit]` up to 1000 and `page[offset]`. Preserve the mapping list; one identifier can have several listings. These identifiers help resolve constituents; they are not a historical event ledger.
- `/api/congressional-trades`: flat filters, including transaction/disclosure dates, plus bracketed pagination. Disclosure date governs when a trade becomes public. Follow current documented page limits and beta coverage.
- `/api/commodities/historical/{CODE}`: historical commodity reference series with interval-specific availability. This does not create live commodity, individual futures-contract or executable price coverage.
- `/api/v2/exchange-details` and `/api/v2/exchange-details/{EXCHANGE_CODE}`: current exchange/session details where supported. Use official holiday/session fields rather than weekday arithmetic.
- Bulk live and other newer interfaces: find the exact public page in the API index; inspect the actual contract before implementation rather than guessing from similarly named APIs.

## Coverage and semantics corrections

There is no universal guarantee of complete dates, fields, delisted history, or continued availability. An entitlement grants access to the available dataset. Free history clipping can return only the allowed interval without warning placeholders. Null fundamentals/SEC fields and gaps must remain distinguishable from zero.

Do not promise one-minute coverage outside a verified ticker/exchange sample. Coarser bars may exist independently. Historical intraday updates are not the same as current-session live OHLC. WebSocket events must be inspected as trades/quotes, not presumed to be OHLC candles; do not invent a WebSocket history endpoint.

EOD data can arrive in several rounds; for US markets an initial update may arrive around 15 minutes after close, with later refinements over a few hours. These are approximate expectations, not guaranteed per-symbol deadlines. Historical market cap is documented as US NYSE/NASDAQ only, weekly from 2021-07-09 (crypto daily from late 2022), in USD; still detect actual observation dates rather than assuming a calendar grid.

Current fundamentals are not historical vintages. Original filing dates, current metadata and renamed symbols require temporal interpretation. Do not infer exact trade provenance, certified execution quality, tape/venue coverage, corporate-action cause, or a correction timetable from a price discrepancy.

Official starting points: [documentation](https://eodhd.com/financial-apis/), [pricing](https://eodhd.com/pricing), [API limits](https://eodhd.com/financial-apis/api-limits), [screener](https://eodhd.com/financial-apis/stock-market-screener-api), [ID mapping](https://eodhd.com/financial-apis/id-mapping-api-cusip-isin-figi-lei-cik-%e2%86%94-symbol), [personal terms](https://eodhd.com/financial-apis/terms-conditions).
