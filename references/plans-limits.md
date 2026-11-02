# Plans, access, call costs and limits

Snapshot of the public EODHD documentation and pricing pages, reviewed 2026-10-25. Plan contents, prices
and limits change; confirm on https://eodhd.com/pricing and https://eodhd.com/financial-apis/api-limits
before recommending a purchase, and confirm the user's *actual* entitlement with a small request on their
own key. Prices below are monthly personal-plan list prices without currency sign (customers are billed in
their regional currency, VAT included).

## Contents

- Which plan includes which API
- Choosing the cheapest plan for a build
- Free plan and the demo key
- Call costs per endpoint
- The three limits (minute, daily, Marketplace) and error codes
- WebSocket allowances
- Monitoring usage with `/api/user`
- Budgeting examples

## Which plan includes which API

Core personal plans: **Free**; **EOD Historical Data — All World** (19.99); **EOD+Intraday — All World
Extended** (29.99); **Fundamentals Data Feed** (59.99); **All-In-One** (99.99). Also sold separately:
**Corporate Events Calendar & News Feed** (19.99) and **Marketplace** products. Annual billing costs 10
months for 12. **Extended Fundamentals** (All-In-One plus Bulk Fundamentals, 119.99) is arranged through
support, not self-serve.

| API / dataset | Free | EOD All World | EOD+Intraday Extended | Fundamentals Feed | All-In-One |
|---|---|---|---|---|---|
| End-of-day prices (`/eod`), incl. indices, forex, crypto, delisted | 1 year | ✓ full | ✓ full | — | ✓ |
| Splits, dividends (`/splits`, `/div`) | 1 year | ✓ | ✓ | — | ✓ |
| Bulk EOD / splits / dividends (`/eod-bulk-last-day`) | — | ✓ | ✓ | — | ✓ |
| Live (delayed) v1 `/real-time`, Live v2 `/us-quote-delayed`, bulk live (US) | ✓ | ✓ | ✓ | — | ✓ |
| Search, exchanges list, exchange symbol list (incl. `delisted=1`) | ✓ | ✓ | ✓ | ✓ | ✓ |
| ID Mapping (ISIN/CUSIP/FIGI/LEI/CIK ↔ symbol) | ✓ | ✓ | ✓ | ✓ | ✓ |
| News API, sentiment | ✓ | ✓ | ✓ | ✓ | ✓ |
| Commodities (beta), US Treasury rates (beta) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Intraday historical (1m/5m/1h) | — | — | ✓ | — | ✓ |
| Technical indicators API | — | — | ✓ | — | ✓ |
| Screener API | — | — | ✓ | — | ✓ |
| Real-time WebSockets (US, EU, forex, crypto) | — | — | ✓ | — | ✓ |
| Trading hours & holidays (`/exchange-details`), US symbol change history | — | — | ✓ | — | ✓ |
| Fundamentals (stocks, ETFs, funds, indices, crypto) | — | — | — | ✓ | ✓ |
| Calendar: earnings, trends, IPOs, splits; economic events | — | — | — | ✓ | ✓ |
| Insider transactions, macro indicators, historical market cap | — | — | — | ✓ | ✓ |
| Interest rates (policy/reference), credit & sovereign risk, real estate | — | — | — | ✓ | ✓ |
| Government bond yields (`.GBOND`), CBOE Europe indices (beta) | — | — | — | ✓ | ✓ |
| ASX corporate actions (beta) | — | — | — | ✓ | ✓ |
| SEC filings, SEC company analytics, congressional trades, sanctions | — | — | — | — | ✓ |
| US tick data `/api/ticks` | — | — | — | — | ✓ |
| Bulk fundamentals | — | — | — | — | Extended Fundamentals only |

Reading the matrix:

- **Fundamentals Data Feed has no end-of-day prices.** On a Fundamentals-only account `/api/eod` returns
  403. Prices plus fundamentals means All-In-One, or EOD All World + Fundamentals Data Feed (79.98).
- **EOD All World → Fundamentals is a switch, not an upgrade**: the API sets are disjoint.
- **Calendar endpoints** (`/calendar/earnings`, `/calendar/trends`, `/calendar/ipos`, `/calendar/splits`)
  are in Fundamentals, All-In-One, or the 19.99 Calendar & News product — not in EOD All World or
  Extended (403).
- **Buying two plans unions their APIs but does not add their limits.** The account keeps one daily
  allowance (100,000 by default); limits are raised separately.
- **No per-exchange plans.** Every core plan covers all supported exchanges; personal plans carry no
  exchange or non-display fees.
- **Marketplace products** (US options, Marketplace tick data, S&P/Dow Jones historical constituents,
  trading hours/market status, ESG, PRAAMS analytics, logos, …) are separate subscriptions, *not* part of
  All-In-One, with their own quota. Paths usually start with `/api/mp/`; logos use `/api/logo`.
- `/api/ticks` (All-In-One) and the Marketplace tick product `/api/mp/unicornbay/tickdata/ticks` are the
  same dataset under different entitlements and paths. A Marketplace buyer calling `/api/ticks` gets a
  permission error.
- The MCP server works on every plan, Free included; each tool call is charged like its underlying
  endpoint and reaches only what the plan includes.

## Choosing the cheapest plan for a build

| Build needs | Cheapest fit |
|---|---|
| Daily prices, dividends, splits, delisted, any exchange; delayed quotes | EOD All World |
| … plus intraday bars, technicals, screener, real-time stream | EOD+Intraday Extended |
| Earnings calendar / estimates only | Calendar & News Feed |
| Statements, ratios, ETF holdings, index components, macro, GBOND — no prices | Fundamentals Data Feed |
| Prices **and** fundamentals | All-In-One (or EOD All World + Fundamentals Feed) |
| SEC filings, congressional trades, sanctions, US ticks | All-In-One |
| US equity/ETF options chains | Marketplace US Options (separate) |
| Point-in-time membership of indices other than the S&P 500 | Marketplace historical constituents (separate) |
| Bulk fundamentals for whole exchanges | Extended Fundamentals (via support) |
| Anything shown to other people, a team, clients or a company | Commercial licence (sales@eodhistoricaldata.com) |

## Free plan and the demo key

- **Free**: 20 API calls/day plus a one-time 500-call welcome bonus; one year of EOD, splits and dividends for any supported exchange; live
  delayed, search, symbol lists, ID mapping, news. No intraday, fundamentals, bulk, calendar or WebSockets.
  Intraday on a free key returns `403 Only EOD data allowed for free users`.
- **Demo key** (`api_token=demo`): a handful of symbols only — AAPL.US, MSFT.US, TSLA.US, AMZN.US,
  VTI.US, EURUSD.FOREX (EUR.FOREX on live), BTC-USD.CC; anything else returns 403. Fundamentals demo
  works for the large US names; the Screener does not accept it; options demo covers AAPL; WebSocket demo
  covers forex/crypto. Use demo only for fixtures and smoke tests, never as an entitlement test.
- There is no free trial of paid core plans; some Marketplace products offer trials.

## Call costs per endpoint

The daily limit is spent in **API calls**; one request may cost several calls. Costs below are from the
public limits page.

| Endpoint | Calls per request |
|---|---|
| EOD, splits, dividends — full history in one request, any date range | 1 |
| Live (delayed), per symbol (10 symbols in `s=` = 10 calls) | 1 per symbol |
| Search, exchanges list, exchange symbol list (whole exchange), calendar, ID mapping | 1 |
| Exchange details / trading hours & holidays, US symbol change history | 1 |
| Economic events, US Treasury rates, policy/reference rates, credit & sovereign risk, ASX corporate actions | 1 |
| `.GBOND` series | 1 |
| Commodities | 5 |
| Real estate (country price series) | 5 |
| CBOE Europe indices list / data | 10 |
| Intraday, technical indicators, screener | 5 |
| News | 5 per ticker (one request for two tickers = 10) |
| Fundamentals (any `filter`), options, bond fundamentals, macro indicators, insider, historical market cap, `.MONEY` series | 10 |
| SEC filings, SEC Company Analytics, congressional trades | 10 |
| Each Marketplace product (against its own quota) | 10 unless its page says otherwise |
| Bulk EOD/splits/dividends, whole exchange; bulk live `ex=US` | 100 |
| Bulk with `symbols=` | 100 + number of symbols |
| `/api/user` | 0 |
| WebSocket messages | 0 (governed by symbol/connection allowances) |

Traps: `filter=` narrows the response, not the cost. A 404 for an unknown ticker is still charged —
validate symbols against the symbol list (1 call per exchange) instead of probing. The dashboard usage chart
counts **requests**; multiply by endpoint cost to compare with the call limit (19,965 intraday requests ×
5 = 99,825 calls).

## The three limits and error codes

| Limit | Counts | Default | Resets |
|---|---|---|---|
| Minute | HTTP requests of any cost | 1,000/min (read `X-RateLimit-Limit`) | rolling minute |
| Daily | API calls | 20 Free; 100,000 paid | midnight GMT; counter clears on the first request after midnight |
| Marketplace | API calls per product | 100,000 per product | 24 h after that product's first request (window drifts) |

| Status | Meaning | Client behaviour |
|---|---|---|
| 200 + `[]` | Valid request, no rows in that window — or an unparseable date | Validate dates client-side; do not read "no events" from an invalid query |
| 401 | Missing/invalid token (placeholder left in, quotes, trailing newline) | Stop; fix configuration; do not retry |
| 402 | Daily call limit and extra calls exhausted | Stop until midnight GMT or buy calls; no retry loop |
| 403 | Endpoint or ticker outside the plan, or a wrong path (missing `/api/`) | Diagnose entitlement; do not retry |
| 404 | Symbol not found (charged) | Fix the symbol; check renames/delisted list |
| 422 | Invalid parameters (e.g. intraday range too long, screener JSON with curly quotes) | Fix the request |
| 429 | Minute limit exceeded (with `Retry-After`), or Marketplace quota exhausted | Honour `Retry-After`; for Marketplace, wait for the window |
| 5xx | Transient server/maintenance | Bounded exponential backoff with jitter |

Every successful response carries `X-RateLimit-Limit` and `X-RateLimit-Remaining` for the minute limiter
(it does not reflect Marketplace quotas). Requests refused for an invalid token carry no rate-limit headers.
A request costing more calls than remain is refused whole. Extra API calls bought in the dashboard never
expire and are spent only after the daily limit; they do not extend Marketplace quotas. The daily limit
itself can be raised from the dashboard ("Increase Daily Limit") or through support; Marketplace increases go
through support.

Authentication: pass `api_token=` as a query parameter (all examples in the docs). The API also accepted
`Authorization: Bearer <token>` in a 2026-10-25 test with the demo key; prefer the header in server code
so tokens stay out of URLs and logs, and fall back to the query parameter if a deployment rejects it.

## WebSocket allowances

- Hosts: `wss://ws.eodhistoricaldata.com/ws/{us|us-quote|us-candles|us-status|eu|eu-quote|eu-candles|eu-status|forex|crypto}?api_token=…`;
  subscribe with `{"action":"subscribe","symbols":"AAPL,TSLA"}`.
- **50 concurrent symbol subscriptions per API token by default**, shared across all sockets; the same
  ticker on trades and quotes uses two slots. Opening more sockets does not add symbols. The allowance can
  be raised in the dashboard for a monthly fee.
- **Up to 64 concurrent connections per token**; beyond that the handshake is refused with 429. Use one
  connection per stream type with one subscribe message listing the symbols.
- Streaming does not consume daily API calls.

## Monitoring usage with `/api/user`

`GET /api/user?api_token=…&fmt=json` costs nothing. Useful fields: `apiRequests` (calls spent on
`apiRequestsDate`, despite the name), `apiRequestsDate` (if not today, the counter has not reset yet),
`dailyRateLimit`, `extraLimit`. A 200 here proves the token is recognised, **not** that a dataset is
entitled — a lapsed plan can still answer `/api/user` while data endpoints return 401/403. Use a cheap data
request (one EOD call) as the entitlement health check. The response contains personal account details:
keep it out of logs, fixtures and prompts.

## Budgeting examples

- Daily US update: one bulk EOD request (100 calls) instead of ~45,000 per-ticker calls.
- Full history for 5,000 tickers: 5,000 EOD calls (one per ticker); the bulk endpoint is the wrong tool for
  backfill (one exchange-day per 100 calls: 252 trading days ≈ 25,200 calls).
- Fundamentals for the S&P 500: ~500 × 10 = 5,000 calls; refresh weekly or on earnings, not daily.
- Intraday 1m backfill: 120-day windows × 5 calls; ten years for one ticker ≈ 31 windows ≈ 155 calls.
- Options full-market sweep: ~7,000 underlyings × 10 calls ≈ 70,000 Marketplace calls/day before
  pagination — close to the default 100,000; partition and schedule.
- A shared app polling live quotes for 200 symbols every minute: 200 calls/min ≈ 288,000/day — above the
  default limit; use WebSockets or bulk live instead (and note shared display needs a commercial licence).
