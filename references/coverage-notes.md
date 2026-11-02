# Symbols, coverage and data behaviour learned in support

Field notes from EODHD customer support (2025–2026), checked against public documentation and live
responses where marked. They are the things a builder gets wrong first. Coverage evolves: treat every item
as "verify with a small request", and never present an example date as a guarantee for other tickers.

## Contents

- Symbol format and exchange codes
- What is and is not covered
- Virtual exchanges: indices, bonds, funds, forex, crypto
- Units and currencies
- History depth and start dates
- Delisted, renamed and reused tickers
- End-of-day semantics
- Intraday and real-time semantics
- Fundamentals, calendars and estimates
- Options (Marketplace)
- News, macro, commodities
- Hosts, tools and integrations

## Symbol format and exchange codes

- Every symbol is `CODE.EXCHANGE`: `AAPL.US`, `SAP.XETRA`, `BHP.AU`, `0700.HK`. Exchange codes come from
  `/api/exchanges-list`; the `Code` there equals `Exchange` in Search results. For US stocks the suffix is
  optional on some endpoints, but always send it.
- **All US venues share `.US`** (NYSE, Nasdaq, NYSE American, Arca, OTC). A venue move changes the
  exchange metadata, not the symbol. US EOD is consolidated across venues.
- Codes that surprise people: Toronto `TO`, TSX Venture `V`, NEO `NEO`, ASX `AU`, B3 Brazil `SA`,
  Johannesburg `JSE`, Pakistan `KAR` (not PSX), Warsaw `WAR`, Frankfurt `F` (distinct from `XETRA`),
  Euronext Paris `PA` (Euronext Growth codes start `AL`), Amsterdam `AS`, Brussels `BR`, Lisbon `LS`,
  Dublin `IR`, Oslo `OL`, Egypt `EGX`, Buenos Aires `BA` (stocks and CEDEARs; no Argentine bonds).
- **Hong Kong** (`HK`, numeric codes such as `0700.HK`) is covered on all plans but has been missing from
  `/api/exchanges-list`; request `exchange-symbol-list/HK` directly. Do not treat the exchanges list as the
  complete coverage list.
- **Milan (Borsa Italiana)** is in beta on a separate host: `https://cboe.eodhd.com/api/eod/ISP.MI?...`
  and `https://cboe.eodhd.com/api/exchange-symbol-list/MI?...`. Calling `.MI` on the main host fails; that is
  not "unsupported". Route `.MI` through a host map in the adapter.
- Search pitfalls: bare numeric codes return `[]`; alphabetic codes match many exchanges (`RIO` is Rio
  Tinto on AU/LSE/US and an unrelated company elsewhere); `isPrimary` marks the primary listing of that
  instrument, not the best match; "S&P 500" returns ETFs (SPY, IVV, VOO), not `GSPC.INDX`. For bulk
  resolution download symbol lists (active + `delisted=1`) for the needed exchanges and match locally by
  ISIN > name > currency/country > type. Never take the first search hit.
- WKN is not supported as an identifier (not unique across markets); use ISIN via Search or ID Mapping.

## What is and is not covered

- **Not every market is covered.** A Search hit does not imply price data; confirm the exchange in
  `/api/exchanges-list` (plus `HK`) and probe one EOD request before promising a market.
- **No FTSE indices** (FTSE 100, FTSE MIB, FTSE All-Share …). Old `FTSEMIB.INDX`-style rows are
  discontinued; do not offer them. The constituent stocks are available individually.
- **No current Russell indices** (Russell 1000/2000/3000 rows are discontinued — no data after early
  2023, same as the old FTSE rows); no index futures. No SPX/NDX/RUT/VIX index *options*. A symbol that
  exists in a list but stopped updating years ago is discontinued, not "temporarily delayed" — check the
  last available date before offering it.
- Individual bonds are limited: government benchmark yields via `.GBOND`; US corporate `.BOND` tickers in
  All-In-One; specific bond or fund ISINs can be requested from support and may be added (EUBOND/EUFUND)
  when a source exists. Do not promise a bond market.
- `COMM` (the old commodity futures exchange, e.g. `CL.COMM`) is not supported (phased out). Use the
  Commodities API for reference series.
- CBOE Europe indices (e.g. `BDE40P`) are a beta API; updates can lapse.
- **China A-shares** are on `SHG` (Shanghai, MIC XSHG) and `SHE` (Shenzhen, XSHE). Codes are 6-digit
  (`600519.SHG`, `000001.SHE`) and quotes are in CNY. EOD updates about 2–3 hours after the 15:00 CST
  close, and the trading-hours data shows the lunch break. Checked 2026-10-25: about 2,280 active common
  stocks on SHG and 2,820 on SHE, current to the last session; daily history starts at each listing
  (`000001.SHE` from 1991, `600519.SHG` from 2001, `601398.SHG` from 2006); Fundamentals return
  `General`/`Highlights` with ISIN, GICS and EPS estimates (`600519.SHG`); 1-hour intraday bars exist in UTC,
  with null-volume rows around the lunch break and a 07:00 UTC session-close marker. **Code collision:**
  `000001.SHG` is the SSE Composite index while `000001.SHE` is Ping An Bank — always keep the suffix.
  Still to probe per listing: statement depth, 1-minute coverage, and B-share lines (by market convention
  Shanghai B shares `900xxx` trade in USD and Shenzhen B shares `200xxx` in HKD; read `Currency`).

  Probe one listing per board before promising coverage. H shares are separate `.HK` listings.
- **Korea**: `KO` (KRX, 6-digit codes such as `005930.KO`) and `KQ` (KOSDAQ), in KRW. Probe prices and
  fundamentals for each listing. For disclosures, see "Not EODHD data" below.
- No earnings-call transcripts, no order books, no VWAP field, no trade conditions in EOD, no pre-computed
  sector returns or total-return field, no meaningful forex volume (the field exists but is undocumented), no tax character of dividends (return of capital,
  capital gain), no WKN, no S-1/S-3/424B filings.

## Virtual exchanges: indices, bonds, funds, forex, crypto

| Code | Content | Notes |
|---|---|---|
| `INDX` | ~1,700 indices: `GSPC` (from 1927-12-30), `DJI`, `IXIC`, `NDX`, `VIX` (from 1990), `AXJO`, `AORD`, `N225`, `GDAXI`, `FCHI` … | Not in `/exchanges-list`; list via `exchange-symbol-list/INDX`. Price indices unless the code ends in `TR`/`T`. `adjusted_close == close`; VIX volume 0 |
| `INDX` breadth | `ADVN`/`DECN`/`UNCN` (NYSE advancing/declining/unchanged), `AVVN` (advancing volume), `ADVQ`/`AVVQ` (Nasdaq), `ADVA`/`AVVA` (AMEX) | Use `close`; ADVN/DECN from 2007-11-09. Better than rebuilding breadth from bulk files |
| `GBOND` | Government yields by country/tenor: `US10Y`, `DE10Y`, `FR10Y`, `CA3M` … | Fundamentals Feed or All-In-One only |
| `EUFUND` | European funds by ISIN: `IE00B45H7020.EUFUND` | Missing funds can be requested by ISIN; watch GBX/GBP scale |
| `FOREX` | `EURUSD.FOREX`, `XAUUSD.FOREX` (gold from 1979) | No traded volume: the `volume` field can be non-zero (probe 2026-10-25, `EURUSD.FOREX`), but its meaning is undocumented, so do not use it as FX turnover. Daily rows include some Saturday/Sunday dates. WebSocket symbols have no suffix (`EURUSD`) |
| `CC` | `BTC-USD.CC`, `ETH-USD.CC` | 24/7 UTC days; volume aggregation differs between sources |
| `BOND` | Bond tickers (US corporate in All-In-One) | Sparse; probe each ISIN before relying on it |

Total-return benchmarks: price indices have `adjusted_close == close`, so compare a total-return portfolio
with a total-return index or an ETF's `adjusted_close`. Current TR series on `INDX` include `SPXTR` (S&P 500
TR, from about 1988), `SP500TR` / `SP500NTR` (gross/net, from about 2000), `XNDX` (Nasdaq-100 TR) and
`DJITR` (Dow TR); probe the first available date before relying on a start year. For longer total-return
history, extend a price index with an explicitly labelled dividend-yield assumption.

Missing index constituents: use an ETF tracking the index and read its holdings (`ETF_Data`) — often with
weights — and label it as a proxy.

## Units and currencies

- **LSE quote currencies are mixed.** UK shares are typically in pence (`GBX`): `BP.LSE` close 638.5
  means 6.385 GBP. But active LSE lines in late 2026 were roughly one third GBX, one third USD, with EUR,
  GBP and other currencies making up the rest (many ETFs and international depositary lines). Read
  `Currency` per symbol, never per exchange.
- **JSE prices are mostly in South African cents** (metadata code `ZAC`; a minority is `ZAR`):
  `NPN.JSE` 68430 = 684.30 ZAR. JSE financial statements are in the reporting currency (mostly ZAR, some
  USD).
- Dividend currency is a separate field: LSE dividends usually arrive in GBP (0.0175 GBP = 1.75p) even
  when the price is in GBX.
- Historical market cap is always USD; Fundamentals statements use the statement currency, which can
  differ from the listing currency.
- Normalize once, at ingestion, with `price_unit_multiplier` stored next to the raw value; never infer the
  unit from magnitude alone (a 100× jump can be a split, a unit change or an error).

## History depth and start dates

Depth is per instrument and starts at its listing; advertised dataset starts are not per-ticker promises.

- US: oldest stocks from 1962 (`IBM.US`), `AAPL.US` from 1980-12-12; `GSPC.INDX` from 1927; forex majors
  from the 1970s; BTC from 2010.
- Thinly traded listings have sparse early history (no row on days without trades): `IWDA.AS` from
  2009/2010, `CSPX.AS` from 2014.
- Intraday: US 1-minute since 2004 *at dataset level* — `SPY.US` 1m starts 2013-08-13; 5m and 1h since
  October 2020 for most markets; forex/crypto 1m since 2009; ASX 1m from May 2021. Probe each symbol's
  first bar before promising a range.
- Fundamentals: major US issuers from 1985, others typically from 2000; small caps often ~6 years / 20
  quarters.
- Free plan: last 12 months only, silently clipped.

## Delisted, renamed and reused tickers

- List delisted symbols with `exchange-symbol-list/{EX}?delisted=1` (available on every plan; the
  response *replaces* the active list, so call both and merge). Prices use the normal endpoints.
- Coverage by delisting date (support guidance): after 2018 → EOD, splits, dividends, fundamentals;
  after 2021 → also intraday; before 2018 → mostly EOD only. Some delisted symbols have no data at all.
  Delisted history is provided as is.
- **Reused codes**: the earlier company keeps the code with an `_old` suffix (`HTZ_old.US`, `WOLF_old2.US`),
  the new company gets the plain code. Never splice histories on ticker text.
- **Renames**: the new code usually carries the full history (`META.US` has the FB years); the old code may
  remain as a separate delisted record that is not reconciled. Symbol Change History is US-only from
  2022-07-22 and does not classify the change type.
- Reorganisations can split one economic history across codes (`CRCQQ.US` vs `CRC.US`).
- There are no suspension, halt or "pending delisting" flags; a delisted company can sit in the active list
  for a while before moving. Fundamentals `General.IsDelisted` flips once processed.
- `GOOG.US` is a continuous series spanning the 2014 share-class change (recorded as a 2.002:1 split); use
  `GOOGL.US` for class A only.

## End-of-day semantics

- `open/high/low/close` are raw as traded; `adjusted_close` is adjusted for splits **and** dividends
  (EODHD states it follows the CRSP / Chicago Booth method); `volume` is split-adjusted only.
  Fully adjusted OHLC: multiply each day's O/H/L by that day's `adjusted_close / close`. Split-only
  prices: Technical API `function=splitadjusted`. Unadjusted volume: divide by the cumulative split
  factor of later splits.
- Daily bars are **regular session only**; pre/after-hours trades never touch daily OHLCV (bulk files
  too). The open is the session's first trade, not labelled as the auction price. A day with one price
  shows O=H=L=C.
- `adjusted_close` and `volume` are **restated over the whole history** whenever a new split/dividend is
  added or corrected; `from`/`to` only filter rows. There is no revision feed, ETag, Last-Modified or
  vintage parameter — detect changes by re-downloading and hashing. After a corporate action, re-pull the
  full series instead of appending.
- Update timing: NYSE/NASDAQ about 15 minutes after the close (~16:15 ET), refined over the next hours;
  Arca ETFs, other exchanges (LSE, XETRA, Euronext, HK …) roughly 2–3 hours after their close; US mutual
  funds, OTC/PINK and some indices the next morning (~3–6 am ET). Schedule US jobs after ~06:00 ET for
  completeness, and always read the returned `date`.
- Bulk `eod-bulk-last-day/{EX}?date=` silently falls back to the previous trading day for a holiday and to
  the latest day for a future date. `filter=extended` adds current (not historical) type, market cap and
  beta. Exchange membership in bulk files is current, not point-in-time.
- Prices carry up to four decimals; trailing zeros are dropped.
- Occasional bad rows exist (pre-IPO placeholders, flat carried-over bars on holidays, missing sessions on
  delisted names). Filter holidays with `/api/exchange-details/{EX}?from=&to=`; report bad rows with
  symbol, date and observed values.

## Intraday and real-time semantics

- **Intraday historical** (`/api/intraday`): 1m/5m/1h; maximum range per request 120 / 600 / 7200 days;
  with no `from`/`to` the last 120 days; `from`/`to` are Unix seconds UTC; bars stamped at their start;
  fully unadjusted; US includes pre/after-hours (filter 09:30–16:00 New York); summed intraday volume is
  typically below consolidated daily volume. Bars are finalized ~2–3 h after the US close — not an
  intra-session feed. No-trade intervals can appear as null-filled bars; a US 5m 20:00 UTC record with
  O=H=L=C and null volume is a session-close marker. Treat nulls as missing, never as zero.
- **Live v1** (`/api/real-time/{SYM}`, `s=A,B`): a delayed snapshot (15–20 min stocks, ~1 min forex),
  refreshed about once a minute; O/H/L/V describe the session so far — it is not a one-minute bar.
  `change_p` and `previousClose` are price-only, so on ex-dividend or split days compare with
  `close/(previousClose − D) − 1` or `close·S/previousClose − 1`. Closed markets return the previous close
  and `NA` session fields. Validate snapshots: a live close outside the session high/low or an open of 0 is
  a bad snapshot to skip, and final daily values should come from EOD.
- **Live v2** (`/api/us-quote-delayed?s=`): US quotes with bid/ask, sizes, last trade and extended-hours
  times; also current market cap, shares outstanding and float — a cheap way to get *current* US market
  cap without Fundamentals.
- **WebSockets**: US trades/quotes 04:00–20:00 ET from a single venue (not a consolidated tape — volume is
  partial, quotes are not an NBBO); European stocks across 18 markets with a consolidated best bid/offer;
  forex and crypto. Candle and status streams exist (`us-candles`, `eu-status` …). Extended-hours trades
  are flagged. There is no WebSocket history or replay; reconnect gaps can only be backfilled from the
  intraday API after finalization.
- Tick data (US): `/api/ticks` (All-In-One) or the Marketplace path; `limit` 1–10000 (0 or more is 422);
  no ticks for a symbol/date can come back as an error rather than an empty list — treat it as "no data",
  don't retry.

## Fundamentals, calendars and estimates

- Fundamentals return one current record per fiscal period, restated, not point-in-time. `filing_date` is
  a real filing date for US issuers but often equals period end elsewhere. Use `filter=` to fetch one
  section (`General`, `Highlights`, `SharesStats`, `outstandingShares`, `Earnings`, `Financials`,
  `ETF_Data`, `Components`, `AnalystRatings`) — it saves bandwidth and prompt space, not calls.
- Identifiers (ISIN, CUSIP, CIK, FIGI, LEI) are current values only. If a Fundamentals identifier is
  missing, the exchange symbol list often carries the ISIN.
- `AnalystRatings` (1–5 scale, 5 = strong buy, counts, target price) is populated for US listings; for
  European lines use `Highlights` estimates and `Earnings::Trend`.
- `outstandingShares` gives annual/quarterly share counts (e.g. `BP.LSE` back to 1985); combined with
  prices it yields an *estimated* market-cap history outside the US — label it as derived and mind GBX.
- Index components: `Components` = current members; `HistoricalTickerComponents` for `GSPC.INDX` gives
  join/leave dates from April 2012 and `historical=1` snapshots, but only the latest interval per ticker
  (re-entries collapse) and `IsActiveNow` can be 1 for a future start date — filter on dates. Other indices'
  history needs the Marketplace constituents product (S&P/Dow Jones families); many indices have current
  members only (some partial, e.g. 10 names without weights).
- Earnings calendar (`/calendar/earnings`): `report_date`, `before_after_market`, `actual`, `estimate`,
  `difference`, `percent`; actual EPS is generally adjusted (non-GAAP) diluted; query with `from`/`to` —
  `symbols=` alone has returned an empty list. Earnings trends (`/calendar/trends`): one row per fiscal
  period and horizon (0q, +1q, 0y, +1y), updated in place, archive from mid-2017, estimates not
  split-adjusted, no as-of parameter — snapshot it yourself for point-in-time work. Do not mix calendar
  actuals with trends consensus as if they shared a basis.
- Economic events: `actual` is the first release (revisions show up as the next row's `previous`); times
  UTC; 00:00:00 means "no specific time"; euro area country code `EU`.
- Historical market cap: US NYSE/NASDAQ only, weekly from 2021-07-09, USD; crypto daily from late 2022.
- SEC Company Analytics (All-In-One, 10 calls): ≈5,900 US SEC filers, history from 1994, computed only from
  the company's own 10-K/10-Q; `debt_to_equity` there is total liabilities / equity; financial firms have
  null liquidity ratios; segments exist only when tagged. Demo key: `AAPL.US`, `TSLA.US`, `AMZN.US` only.
- ASX corporate actions (beta, 1 call): `.AU` only; dividends carry franking, DRP, special and withholding
  fields; also splits, bonus and rights issues, buybacks (sparse), capital returns and SPPs; refreshed daily.
  Plan wording on its page is contradictory (Fundamentals vs not in the standalone Fundamentals plan) —
  verify on the user's key. Franking credits need a user-supplied company tax rate.
- ETF `ETF_Data`: current fixed-income metrics (duration, YTM, maturity), allocations, top holdings
  (sometimes only a few positions), performance — no history of these fields.

## Options (Marketplace)

- US stocks and ETFs only, end-of-day chains (one snapshot per trading day, after the US close), history
  from early Q4 2023; about 7,000 underlyings (list size 7,003 on 2026-10-25). SPY/QQQ/IWM yes;
  SPX/SPXW/XSP/NDX/RUT/VIX/DJX no.
- Endpoints `/api/mp/unicornbay/options/{underlying-symbols,contracts,eod}`; filters
  `underlying_symbol`, `contract`, `exp_date_*`, `strike_*`, `type`, `tradetime_*`; `page[limit]` ≤ 1000,
  offset ≤ 10,000; `fields[options-eod]` trims payload; `links.next = null` ends paging.
- `tradetime` is the last trade date and can be null or old for illiquid contracts that still carry open
  interest — partition by expiry, not by trade time. The observation day is in the record id
  (`SPY260408C00653000-2026-04-07`). Bid and ask timestamps may use different time zones: normalize both
  and verify against a known contract. Holiday records repeat the previous session.
- 10 calls per request against the Marketplace quota; no whole-market file — every request names an
  underlying or contract. Demo key covers AAPL.

## News, macro, commodities

- News (`/api/news`): `s` (ticker) or `t` (topic), `from`/`to`, `limit` ≤ 1000, `offset`; each item has
  full content, `link` to the original, `symbols`, `tags`, sentiment. Archive is dense from 2021, sparser
  before 2020. Cost 5 per ticker.
- Commodities (beta): reference series (WTI, Brent, gas, metals, agriculture); some are published weekly
  and lag up to a week. Not futures contracts.
- UST rates: daily par, bill, long-term and real-yield curves (beta) on all plans.

## Hosts, tools and integrations

- REST: `https://eodhd.com/api/...`; Milan beta: `https://cboe.eodhd.com/api/...`. Keep the `/api/` prefix
  — `https://eodhd.com/exchange-symbol-list/US` hits the website and can return 403. Use HTTPS only.
- Token: dashboard https://eodhd.com/cp/dashboard. Regenerating revokes the old key immediately (no
  overlap); upgrading a plan keeps the same key. "Unauthenticated" usually means the token string is not
  exact (placeholder, quotes, whitespace, a stray `}`).
- `fmt=json` everywhere you can. CSV drops fields on some endpoints (dividends CSV has only date and
  amount; Fundamentals is JSON-only). `fmt=csv` URLs open directly in a spreadsheet for quick checks.
- MCP: `https://mcp.eodhd.com/v2/mcp` (OAuth; nothing after `/mcp`). Claude connects only to v2. Older
  `v1/mcp?apikey=` URLs exist for clients that need a key in the URL. If OAuth loops: disconnect and delete
  the connector, clear site data for the AI host and eodhd.com, restart the browser, re-add the exact URL,
  consent with the right account.
- Official tools: Python library (`pip install eodhd`), R library, Node/TypeScript SDK, Excel add-in
  (Windows), Google Sheets add-on ("Financial Data"), WordPress plugin, Power BI connector, Postman
  collection. They return the same data under the same plan limits.
- Service status: https://uptime.eodhistoricaldata.com (availability only, not data corrections).

## Observed behaviour found while writing the method chapters (probes, 2026-10-25)

Single-ticker or small-sample observations; re-check them with a probe before depending on them.

- **Technical API**: computes only from the requested window (short window → `[]`; recursive indicators
  depend on `from`); `sma/ema/rsi/macd/bbands` on `adjusted_close`, `atr/adx/stochastic` on unadjusted OHLC
  (split-day jumps); keys `macd/signal/divergence`, `uband/mband/lband`, `k_values/d_values`; `volatility`
  undocumented. The `beta` function's default benchmark `GSPC.INDX` is a price index.
- **Weekly bars** (`eod?period=w`) are labelled with the week's Monday but close on Friday — shift the label
  before joining to daily data or you leak four days.
- **Screener**: no instrument-type filter; only `200d_new_hi/lo` signals exist (50-day is rejected); P/E is
  not a screener field; `us` also returns OTC foreign lines (some with broken yields) — scope to `nyse` /
  `nasdaq` when needed. Codes containing `-` are often preferreds, but share classes such as `BRK-B` are
  common stock: check `Type` before dropping.
- **Fundamentals statements**: values arrive as strings; `0` and `null` both mean unavailable;
  `interestExpense` can be empty for indebted issuers (needs a fallback for cost of debt);
  `capitalExpenditures` and `dividendsPaid` are positive; `netDebt` = `shortLongTermDebtTotal − cash`;
  `netInvestedCapital` is not net of cash; `Valuation.EnterpriseValue` does not reconcile to market cap +
  net debt (definition undocumented); `outstandingShares` comes as `{annual, quarterly}` rows with shares in
  units plus `sharesMln`; `Earnings::Annual` for the unreported current year is a partial-year sum.
- **Options**: IV in decimals, vega per vol point, theta per calendar day, rho per 1 pp, `theoretical` =
  mid; Friday `dte` is one day short (compute T yourself); `filter[tradetime_eq]` drops contracts that did not
  trade but carry open interest; there is no observation-date filter.
- **Rates**: policy rates cover the Fed, ECB and BoE; reference rates cover USD (SOFR family, EFFR, OBFR,
  BGCR, TGCR), EUR (€STR) and GBP (SONIA) only — theoretical FX forwards and carry work only for those
  currencies without user-supplied rates. UST series follow the bond-market calendar (rows on Good Friday,
  none on Columbus Day). Corporate HQM yields are monthly, the distress index weekly with about a month's
  lag, sovereign CDS/ratings/risk premia annual snapshots.
- **Macro indicators**: annual only, the latest year lags by more than twelve months (US CPI ended at 2024
  on 2026-10-25), and `Indicator` returns a description rather than the code.
- **Economic events**: always pass `from`/`to` and `country` (otherwise far-future placeholder rows); `change`
  is 0 on unreleased rows; one `type` can carry both a level and a % change (use `comparison`); aggregate
  CFTC net-position rows are included (there are still no COT reports or contract-level positioning).
- **Commodities API**: default `interval` is monthly; request daily explicitly. Daily responses are capped
  at 1,000 rows, newest first. Page with `page[offset]`/`page[limit]` and follow `links.next`; plain
  `offset`, `from` and `to` were ignored (WTI, demo key, 2026-10-26). WTI monthly rows are stamped on the
  first of the month but carry the **month-end** value (2026-09-01 = 97.18 = the 2026-09-30 daily close),
  so re-stamp them before joining. Precious metals were discontinued at the source; use
  `XAUUSD.FOREX`.
- **Crypto EOD**: the latest `.CC` row can be the unfinished current UTC day (a 2026-10-26 row at
  02:27 UTC). Crypto `Statistics` (`MarketCapitalizationDiluted`, supplies, `MarketCapDominance`) is a
  current snapshot only.
- **Exchange calendar**: `v2/exchange-details` returns current-year holidays and uses its own codes for some
  exchanges (`XHKG`, `XPAR`, `XAMS`, `XASX` …); use v1 with `from`/`to` for past years and map codes
  explicitly.
- **Bulk splits/dividends files** list only events dated that day; corrections to older actions surface only
  through a full re-pull of the symbol.
- **WebSockets**: no sequence numbers or trade ids (dedupe by your own log position); a recent closed
  1-minute bar backfill exists for US/EU equities, otherwise backfill from `/api/intraday` after finalization.
- **Fund expense ratios**: `ETF_Data::NetExpenseRatio` came back as a decimal (VTI.US `0.0003`), while
  `MutualFund_Data::Expense_Ratio` for SWPPX.US returned `0.0201`, which only fits the fund as a percent.
  Check units per fund before weighting.
- **News word weights** are computed on request from a processed sample of matching articles (slow; words not
  stemmed in the probe); archive responses if you need historical topic features.
- **Exchange calendar**: `v2/exchange-details` gives pre-market/after-hours times only where they exist and
  no separate after-hours end on early-close days.
- **News**: no article ID field (derive one from link/title); `symbols` lists every mentioned ticker, not the
  primary subject; syndicated copies are not flagged.

## Not EODHD data (state the boundary, ask for user input or a labelled proxy)

- Holdings, accounts, transactions, fills, tax lots, fees, tax rules, wash-sale determinations, household or
  broker data, fund terms — always user-supplied.
- Historical bid/ask quotes (EOD has none; ticks are trades only; `us-quote-delayed` is a current snapshot),
  order-book depth, queue position, borrow availability/rates, locate/SSR status.
- Academic factor return series (build factor proxies from EODHD prices/fundamentals or ETF spreads).
- Historical sector/industry classification, historical `ETF_Data` metrics (current snapshots only).
- Market-wide put/call ratio, margin debt, fund flows, crypto funding rates/open interest, social-media
  sentiment as a separate feed, filer-level 13F history, estimate-revision history (archive trends
  yourself), earnings-call transcripts, guidance, segment data, FY+2 estimates, reported REIT FFO/AFFO.
- Swap curves and spreads, OIS, inflation swaps, cross-currency basis, FX forwards and implied vol,
  futures-implied policy paths, muni/MBS/ABS/CLO, bond covenants and maturity schedules, OAS. Also:
  - bond-futures prices, conversion factors and CTD;
  - term or special repo rates (only overnight SOFR/TGCR/BGCR exist);
  - bank deposit and CD rates.
- Exchange disclosure portals and regional filing systems outside the SEC filings API. Examples: Korea's
  DART and the KRX disclosure portal, other national regulator portals, and third-party aggregator pages.
  Probe the listing's prices and fundamentals in EODHD, and treat filings from those systems as
  user-supplied documents.
- Commodity inventories, production, rig counts, shipping and weather. The exception is the weekly US EIA
  inventory rows in `economic-events`, alongside the aggregate CFTC net-position rows. Futures contract
  specifications (multiplier, tick value, margin), futures curves and COT reports are also not EODHD
  data. Futures sizing runs on user-supplied specifications.
- Convertible-bond, warrant and structured-note terms: conversion ratio, strike, expiry, call, put and reset
  schedules. These are user-supplied, even when the listed instrument has an EOD price. OTC or exotic
  option quotes are also not EODHD data. Path-dependent payoffs are model prices only.
- Short-term-rental market data (nightly rate/ADR, occupancy, RevPAR, listing counts) and property-level
  rents, vacancy or valuations. These are user inputs. The EODHD real-estate endpoints are regional price
  indices for context only.
- On-chain and DeFi data: wallet balances and holders, pool reserves and fees, staking reward rates and
  validator data, token issuance and unlock schedules. Also global crypto market totals and dominance
  history, trending lists and token categories. Impermanent-loss and staking-yield modules run on
  user inputs.
- IPO lockup terms and private funding rounds. A lockup date of IPO date + 180 days is a labelled
  estimate. A capital-markets digest can use `calendar/ipos` plus topic news.
- Filing text as structured fields (risk factors, MD&A narrative) and SEC form types outside the SEC
  filings API's 10-K/10-Q/8-K/Form 4 set. Treat them as user-supplied documents.
- Broker and house terms: margin ratios, financing rates, borrow fees, margin-call procedures; merger terms
  (ratio, cash, elections, proration), the cash-in-lieu price actually paid, cost-basis rules and
  settlement-holiday calendars. EODHD supplies dividend/split records and closes only.
- Custodian, administrator and general-ledger records, approval decisions, composite membership policies and
  GIPS compliance. EODHD closes and `*.FOREX` closes are independent references (a FOREX close is not an
  official fixing).
- Private-fund capital calls, distributions and NAVs (PME compares the user's cash flows with an EODHD TR
  index); mortgage-rate surveys, property appraisals, local rents and peer net-worth benchmarks
  (`/api/real-estate/{CC}` series are country-level quarterly context only).
- An issuer master: derive issuer keys from LEI/CIK returned by ID Mapping or Fundamentals `General`
  (current values only); ADRs and ordinary shares carry separate ISINs.
- Crypto `Statistics` history (dominance, supplies, market caps are current snapshots); Form 4 rows have no
  Rule 10b5-1 plan flag (only footnote text can indicate a plan sale); historical sector classifications
  and dated theme-basket memberships.
- Market impact estimates: execution schedules (Almgren-Chriss, TWAP/VWAP) run on declared impact and
  risk-aversion parameters.
- Chart rendering and UI: computed client-side (signed changes only; colour conventions are a UI choice).
