# Intraday, ticks, sessions and streaming

> Methods with formulas, steps and acceptance checks: [data-engineering-patterns](data-engineering-patterns.md), [methods-quant-research](methods-quant-research.md).

## Pick the correct observation

Historical intraday bars, delayed snapshots, live trade events, quote events and EOD records are different products. Verify interval, symbol syntax, entitlement, timestamp units, fields and available dates before building. One-minute coverage varies by ticker/exchange; a five-minute series does not imply a one-minute series exists. A maximum historical start date is not a coverage promise.

### EODHD specifics (public docs and support, 2026-10)

| Product | Endpoint | What it is | Limits / timing |
|---|---|---|---|
| Intraday historical | `/api/intraday/{SYM}?interval=1m\|5m\|1h&from=&to=` (Unix UTC) | OHLCV bars stamped at bar start, fully unadjusted, US incl. pre/after-hours | Max range per request 120 / 600 / 7200 days; default last 120 days; finalized ~2–3 h after the US close; 5 calls |
| Live v1 (delayed) | `/api/real-time/{SYM}?s=…` | Session snapshot (latest price + session O/H/L/V, previous close) — not a minute bar | 15–20 min stocks, ~1 min forex; ~1-minute refresh; 1 call per symbol |
| Live v2 (US) | `/api/us-quote-delayed?s=…` | Delayed US quote: bid/ask, sizes, last trade, extended-hours times, current market cap/float | 1 call per symbol |
| Bulk live (US) | `/api/real-time/AAPL.US?ex=US` (any US symbol in the path) | Whole-exchange delayed snapshot | 100 calls |
| WebSockets | `wss://ws.eodhistoricaldata.com/ws/{us,us-quote,us-candles,eu,eu-quote,eu-candles,forex,crypto,…}` | US trades/quotes 04:00–20:00 ET from a single venue (not consolidated); 18 European markets with consolidated BBO; forex; crypto | <50 ms; 50 symbols per token across sockets; 64 connections; no API-call cost; no history/replay |
| US ticks | `/api/ticks` (All-In-One) or Marketplace tick path | Trade-by-trade US history | `limit` 1–10000 |

History: US 1-minute since 2004 at dataset level, but per-symbol starts differ (`SPY.US` 1m from
2013-08-13); 5m/1h from October 2020 for most markets; forex/crypto 1m since 2009; ASX 1m from May 2021.
Probe the first bar per symbol. Summed intraday volume is typically below consolidated daily volume, and
WebSocket US volume is partial (single venue) — take daily volume from EOD. Null-filled bars mean no trades;
a US 5m record at 20:00 UTC with O=H=L=C and null volume is a session-close marker, not a traded interval.
Validate live snapshots (a close outside the session range or an open of 0 is a bad snapshot) and take final
daily values from EOD.

WebSocket messages do not inherently provide OHLC. To build candles, accumulate eligible trades using an explicit event-time policy. A quote-only stream cannot produce traded volume or certify trade OHLC. Do not invent a history/replay endpoint or backfill path; reconcile disconnections only using documented available products.

## Bar building

For each symbol/session and half-open time bucket `[start,end)`, open = first eligible trade, high/low = extrema, close = last eligible trade, volume = sum of trade sizes on a compatible basis. Sort by event time and use sequence/tie-break evidence where available. Preserve `bar_start`, `bar_end`, last-event time, receipt watermark and provisional/final state. A locally finalized bar means finalized under this application's lateness policy, not immutable official data.

Do not fabricate zero-volume OHLC bars for missing observations. A chart may display whitespace. Reconstructing five-minute bars from available one-minute bars yields a derived series and may differ from the separately delivered five-minute product; record completeness and session coverage.

For tick/volume/dollar bars, use actual trades with price/size. Define whether the trade crossing the threshold closes the bar and whether overshoot resets or carries; test with oversized trades. OHLC bars cannot recover the original tick sequence. Calibrate thresholds using past data and do not assert that activity bars guarantee normal returns.

## Calendar and freshness

Map UTC event times to an exchange calendar with DST, early closes and lunch breaks. Keep regular/extended sessions separate. Compute freshness from observation time, not HTTP receipt or the time the app last repainted. Include market-open/closed state: yesterday's close on a holiday is expected but is not a fresh executable quote.

A rule like “price younger than 20 minutes” needs an observation timestamp, trustworthy clock, session policy and fail-closed handling for unknown/stale times. The API's nominal delay does not guarantee every thinly traded symbol has traded recently. Do not make a stale last trade fresh by polling it again.

## Connection supervisor

Maintain desired versus acknowledged subscriptions, heartbeat/idle state, exponential reconnect backoff with jitter, bounded retry, resubscription and cancellation cleanup. Respect documented connection/symbol allowances; test simultaneous behavior if essential rather than guessing from plan names. Detect duplicate/out-of-order events and sequence gaps where observable; absence of a sequence field limits gap detection.

Use bounded buffers and backpressure. On overload, distinguish a display coalescing policy from lossless research capture. Do not silently discard events and then claim complete tick history. Keep raw stream capture private and timestamped when authorized/needed.

## UI contract and acceptance

Display dataset type, interval, timezone, observed time, freshness and provisional status. Test one trade at a boundary, out-of-order event, duplicate event, empty interval, lunch break, early close, DST shift, reconnect and stale last trade. Do not certify consolidated/SIP/NBBO execution quality from these tests or infer venue coverage from matching prices.
