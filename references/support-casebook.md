# Support casebook: symptom → cause → what to build

Anonymized, recurring situations from EODHD customer support (2025–2026). Use them two ways: to diagnose
a user's failing integration quickly, and to design applications that never hit these traps. Each case
names the check that settles it. Details that change (prices, coverage) live in
[plans-limits.md](plans-limits.md) and [coverage-notes.md](coverage-notes.md).

## Contents

1. Access, entitlement and errors (A1–A12)
2. Limits and quotas (L1–L8)
3. Symbols and coverage (S1–S14)
4. Prices, adjustments and corrections (P1–P12)
5. Intraday, live and streaming (R1–R9)
6. Fundamentals, calendars and events (F1–F10)
7. Options and Marketplace (M1–M5)
8. Licensing and account questions that shape a design (C1–C10)

---

## 1. Access, entitlement and errors

**A1. "Fundamentals return 403 (or 401) but my key works for prices."** Fundamentals is in Fundamentals
Data Feed and All-In-One only. *Check:* one `filter=General` request on the user's key. *Build:* map
each feature to its plan and degrade the UI with a "not in your plan" state instead of an error toast.

**A2. "I bought Fundamentals Data Feed and now `/eod` is 403."** That plan has no prices — it does not
even keep the Free plan's year of EOD. Prices + fundamentals = All-In-One, or EOD All World + Fundamentals.

**A3. "Earnings calendar / trends return 403 on EOD All World."** Calendar endpoints are in Fundamentals,
All-In-One or the same-priced Calendar & News Feed product — a common wrong purchase at checkout.

**A4. "Intraday says `Only EOD data allowed for free users`."** Free key on a non-EOD endpoint. The demo
key works for its sample symbols; it does not prove the user's own entitlement.

**A5. "`/api/user` returns 200 but data calls fail."** `/api/user` validates the token, not the plan
(e.g. a cancelled or past-due subscription). Health-check with a 1-call EOD request instead.

**A6. "401 Unauthenticated though I copied the key."** Placeholder text left in, surrounding quotes,
whitespace/newline from an env file, a stray `}` from string formatting, or an old key after
regeneration (regeneration revokes instantly). Strip and validate the token at startup.

**A7. "Exchange symbol list gives 403 on the Free plan."** URL missing `/api/`
(`https://eodhd.com/exchange-symbol-list/US` hits the website). The endpoint itself is on every plan.

**A8. "I bought Marketplace tick data but `/api/ticks` fails."** Marketplace ticks are served from
`/api/mp/unicornbay/tickdata/ticks`; `/api/ticks` belongs to All-In-One. Route by entitlement.

**A9. "Splits endpoint returns an empty list for my date range — no splits?"** `200 []` also happens for
an invalid date format; `404` means unknown symbol; `403` means not in plan. Validate `YYYY-MM-DD` before
interpreting emptiness.

**A10. "My browser app can't call the API / my key leaked from the front end."** Tokens in URLs are
visible to anyone using the page. Put a server-side adapter in front; never ship the key to the client.

**A11. "Search finds the ticker but EOD returns nothing."** Search lists instruments, not guaranteed price
coverage (common for markets EODHD does not cover). Probe one EOD request before
adding a symbol to a universe.

**A12. "The billing page still shows my old plan."** Dashboard status can lag after payment events; what
the API serves is authoritative. Applications should key features off actual responses, not plan names.

## 2. Limits and quotas

**L1. "I hit the limit after a few thousand requests."** Limits are in API calls: intraday/technical/
screener 5, news 5 per ticker, fundamentals/options 10, bulk 100, live 1 per symbol. The usage chart
counts requests. *Build:* a cost-aware limiter that charges each request its documented weight.

**L2. "Two subscriptions should give me 200k calls."** Plans union their APIs; the daily allowance does
not add. Raise the limit separately.

**L3. "The counter didn't reset at midnight."** Reset is midnight GMT and the counter clears on the first
request after it; until then `/api/user` shows the last active day (`apiRequestsDate`).

**L4. "Options/ticks return 429 but my main quota is fine."** Marketplace products have their own
100,000-call quota per 24 h from that product's first request, 10 calls per request; `X-RateLimit-*`
headers describe only the minute limiter.

**L5. "Backfilling every ticker with the bulk endpoint burned my day."** Bulk = one exchange-day for 100
calls — ideal for daily updates, wasteful for history. Backfill per ticker (1 call per full history).

**L6. "I get 429 bursts from my parallel workers."** 1,000 requests/min shared by all workers on the key.
Use one shared token-bucket, honour `Retry-After`, spread requests over the minute.

**L7. "My app polls live quotes for every visitor."** Cost scales with users × symbols × refresh rate. Poll
once per symbol per interval server-side and fan out from cache; use WebSockets (no call cost) or bulk live
for many symbols. (Serving other people also needs a commercial licence — C3.)

**L8. "402 and the job keeps retrying."** 402 = daily calls and extra calls exhausted; retrying wastes
requests. Stop, checkpoint, resume after midnight GMT.

## 3. Symbols and coverage

**S1. "Do you have Milan?"** Yes, beta on `cboe.eodhd.com` with `.MI` codes; the main host fails for
`.MI`. Keep a host map in the adapter.

**S2. "FTSE 100 / FTSE MIB / Russell 2000 index?"** Not provided; old rows are discontinued. Offer the
constituent stocks or an ETF proxy, labelled as such.

**S3. "Do you cover market X?"** Some markets are not covered at all, and a Search hit does not prove price
coverage. Check the exchanges list (plus `HK`, which is missing from it) and probe one EOD request.

**S4. "Hong Kong isn't in the exchanges list."** It is available on all plans as `HK` (`0700.HK`); the
exchanges list is not a complete coverage map.

**S5. "LSE/JSE prices are 100× too big."** UK shares on LSE quote in pence (`GBX`), JSE in cents (`ZAC`); many LSE lines are in USD/EUR/GBP instead. Normalize per symbol from
metadata `Currency`.

**S6. "Ticker for the S&P 500?"** `GSPC.INDX`; Search returns ETFs for "S&P 500".

**S7. "Map 8,000 broker holdings to EODHD symbols with Search."** Build a local index from symbol lists
(active + delisted) for the relevant exchanges, match by ISIN first; numeric codes return `[]` in Search and
`isPrimary` ≠ best match. Keep unresolved items visible.

**S8. "My delisted ticker shows another company."** Code reuse: the earlier company is `CODE_old.US`
(`_old1`, `_old2` …). Resolve by ISIN/name/dates, never by code text.

**S9. "The renamed company's old history vanished."** History moves to the new code; the old code may be a
separate delisted record. Symbol Change History is US-only from 2022-07-22.

**S10. "Survivorship-free US universe for 2005–2020 with fundamentals."** `delisted=1` lists give the
names; fundamentals exist mostly for delistings after 2018 and intraday after 2021. Design the study around
what exists and state the gap.

**S11. "Historical Nasdaq-100 / Russell membership."** Only S&P 500 history is in Fundamentals (from 2012,
latest interval per ticker); S&P/Dow Jones families via the Marketplace product; others current members
only.

**S12. "Market breadth (advance/decline) for NYSE."** Use `ADVN`, `DECN`, `UNCN`, `AVVN` on `INDX`
rather than rebuilding from bulk files (bulk membership is current, not historical).

**S13. "Individual bond prices by ISIN."** Mostly not available (government yields via `.GBOND` in
Fundamentals/All-In-One); specific ISINs can be requested. Don't design a bond-pricing product on it.

**S14. "The index exists in the list but stopped updating in 2023."** Discontinued row, not a delay. Check
the last data date before offering any symbol.

## 4. Prices, adjustments and corrections

**P1. "Close doesn't match my chart."** Raw `close` vs `adjusted_close`; the chart may show adjusted
values. Compare like with like.

**P2. "Are open/high/low adjusted?"** No — raw. Adjusted OHLC = raw × (`adjusted_close`/`close`) per day.
Volume is split-adjusted; intraday is fully unadjusted.

**P3. "Old adjusted closes and volumes changed in my cache."** A new split/dividend restates the whole
adjusted history; there is no versioning. Re-download the full series after any corporate action; keep
dated raw captures if you need reproducibility.

**P4. "I need prices as originally published (point-in-time)."** Not available. Archive forward from now,
or rebuild an as-of adjusted series from raw OHLC plus actions with ex-date ≤ D.

**P5. "Does the daily close include after-hours?"** No; regular session only, bulk included.

**P6. "Monthly total return?"** `period=m` and the ratio of consecutive `adjusted_close`; rows are
labelled with the month's first trading day. No precomputed return field.

**P7. "Fund returns differ slightly from the fund's factsheet."** Adjustment reinvests at the close
before ex-date; funds reinvest at NAV on their own dates. Small differences are expected.

**P8. "Live `change_p` is wrong on ex-dividend day."** Live change uses the unadjusted previous close.
Adjust it by the dividend or split for return calculations.

**P9. "Bulk file for a holiday returned data."** It fell back to the previous trading day. Always compare
the returned `date` to the requested one.

**P10. "Flat bars on holidays / a 0.01 bar before IPO."** Bad rows exist; filter with the exchange holiday
calendar and report specific symbol/date pairs. Don't silently delete without logging.

**P11. "Dividend CSV lacks payment and record dates."** Extended fields come only with `fmt=json`.

**P12. "Market cap history for a non-US stock."** Historical Market Cap is US-only (weekly, from
2021-07-09). Derive an estimate from `outstandingShares` × close (normalize GBX first) and label it.

## 5. Intraday, live and streaming

**R1. "SPY 1-minute from 2004 returns nothing."** The 2004 start is dataset-level; SPY 1m starts
2013-08-13. Probe each symbol's first bar; respect 120/600/7200-day windows.

**R2. "Today's intraday bars are missing."** Historical intraday is finalized 2–3 h after the close; use
WebSockets (US/EU/forex/crypto) or live snapshots during the session.

**R3. "Earliest 5m/1h bars are 2020."** Correct (October 2020); aggregate 1m for older hourly history and
label it as derived.

**R4. "WebSocket volume is lower than the daily volume."** The US stream is a single venue, not the
consolidated tape. Use it for live display/signals; take daily volume from EOD.

**R5. "I opened 50 sockets and still get 50 symbols."** The allowance is per token across sockets (50 by
default; trades + quotes for one ticker = 2 slots); max 64 connections. One socket per stream type.

**R6. "Gold, EUR/USD and BTC on one socket?"** Forex (`XAUUSD`, `EURUSD`) and crypto (`BTC-USD`) are
separate endpoints with different symbol formats.

**R7. "Live snapshot high/low look stuck / close outside the range."** Treat snapshots as provisional;
validate invariants, skip invalid rows, and take final daily values from EOD.

**R8. "Pre-market prices?"** WebSocket US stream covers 04:00–20:00 ET; Live v2 carries extended-hours
fields; daily EOD never includes them.

**R9. "Ticks for a date with no trading returned an error."** Treat as "no data"; don't retry endlessly.

## 6. Fundamentals, calendars and events

**F1. "Sector isn't in the ticker list."** Use Fundamentals `filter=General::Sector` or the Screener.

**F2. "Analyst ratings are null for European listings."** `AnalystRatings` is populated for US lines; use
`Highlights` estimates or `Earnings::Trend` elsewhere.

**F3. "I need EPS consensus as it was on past dates."** Trends are one row per fiscal period and horizon,
updated in place, not split-adjusted. Snapshot daily from now on; history can't be reconstructed.

**F4. "Earnings calendar with `symbols=` returns empty."** Query a `from`/`to` window and filter.

**F5. "Surprise % doesn't match my consensus."** Calendar actuals/estimates and trend consensus can use
different bases; compute surprises within one source.

**F6. "Economic event actual changed."** `actual` is the first release; revisions appear as the next
row's `previous`. Store releases as events.

**F7. "Historical constituents show one interval for a stock that left and rejoined."** Only the latest
interval per ticker is returned; `IsActiveNow` can be set for future starts. Filter by dates and record
the limitation.

**F8. "Filing date equals period end for my non-US company."** Not a real publication time; apply a
conservative lag in point-in-time research and disclose it.

**F9. "ISIN/CUSIP missing in Fundamentals."** Use the exchange symbol list ISIN or ID Mapping as fallback;
store identifiers as observations with retrieval dates.

**F10. "Do you keep quarterly numbers as first reported, with release dates?"** Release timing, yes:
quarterly `filing_date` and `Earnings::History` `reportDate` with `beforeAfterMarket`. The number is the
one stored now and may be a restatement next to the original `filing_date` (`GE.US` 2017 quarters show
2018 recast revenue; `KHC.US` 2017 quarters do not show its 2019 restatement). For US issuers, the SEC
Filings API has one row per 10-Q/10-K with `filed_at` (All-In-One, 10 calls), but only for recent years
(oldest 10-Q: `AAPL.US` 2015, `AMZN.US` 2020); elsewhere and earlier, archive forward.
Check: compare a known restated quarter in Fundamentals with its SEC Filings row.

## 7. Options and Marketplace

**M1. "SPX options?"** Not available — US stock/ETF options only (SPY/QQQ/IWM as approximations, labelled).

**M2. "Options history before 2023?"** Not available; history starts in early Q4 2023.

**M3. "Chain looks incomplete with a trade-time filter."** `tradetime` can be null/old for untraded
contracts; partition by expiry; paginate (`page[limit]` ≤ 1000, offset ≤ 10,000).

**M4. "Full-market options sweep every day."** ~7,000 underlyings × 10 calls ≈ 70,000 Marketplace calls
before pagination; budget, partition, and schedule after the US close.

**M5. "Is Options included in All-In-One?"** No — separate Marketplace subscription with its own quota.

## 8. Licensing and account questions that shape a design

**C1. "Can I store everything in my own database and keep it after cancelling?"** Yes for personal use —
no deletion clause; redistribution remains prohibited; new data needs an active plan.

**C2. "Can I analyse the data with ChatGPT/Claude or the MCP server?"** Yes, through your own account
for your own analysis. A bot or AI service other people use is commercial.

**C3. "Dashboard for my clients / family / Discord / website — free, no revenue."** Displaying data to
anyone else is commercial even without revenue or behind a password. Prototype with synthetic data;
contact sales@eodhistoricaldata.com before launch.

**C4. "Can my team share one key?"** No — one key, one person. Teams need commercial seats.

**C5. "Private dashboard on a VPS/cloud with a public IP."** Fine for personal use if only you can access
it.

**C6. "Open-source my project."** Share code without keys, data or private outputs; ship synthetic
fixtures.

**C7. "Student discount?"** 50% for 12 months on card payments (not PayPal), proof sent to support after
subscribing; it does not grant redistribution or class-wide sharing.

**C8. "Annual plan or a free trial?"** No trial on core plans; annual = 10 months' price for 12. Use Free
or demo for evaluation.

**C9. "Cheaper plan for one exchange / low volume?"** No per-exchange plans. A reduced-limit All-In-One
(10,000 calls/day at a discount, card payments) exists via support for light users.

**C10. "Refund if the data doesn't fit?"** Payments are final under the Terms; cancellation stops renewal
with access to the end of the period. This is why a pre-purchase coverage probe ([recipe 37](build-recipes.md#37-pre-purchase-coverage-probe))
on Free/demo is worth building first.
