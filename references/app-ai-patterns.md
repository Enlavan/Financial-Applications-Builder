# Application and AI build patterns: charts, dashboards, assistants, fixtures

Methods for the presentation and AI layers of an EODHD-backed system: turning EOD/intraday/live
responses into correct chart payloads (TradingView Lightweight Charts v5 used as the worked library),
a candlestick + moving-average + support/resistance recipe, Streamlit and other UI stacks, financial UI
conventions, dashboard tie-out review, evaluation of AI assistants, natural-language-to-SQL over the
user's own archive, news RAG, a private MCP wrapper over EODHD REST, a synthetic market-data
generator for fixtures and public demos, and the run-state contract for agents. Principles already stated elsewhere are linked, not repeated:
[applications.md](applications.md) (server/client split, states, chart principles),
[ai-mcp.md](ai-mcp.md) (tool contract, RAG provenance, injection boundaries),
[reports.md](reports.md) (exports, PDFs), [code-patterns.md](code-patterns.md) (cost-aware client,
adjusted OHLC, WebSocket recorder), [data-semantics.md](data-semantics.md) and
[coverage-notes.md](coverage-notes.md) (field meaning), [licensing.md](licensing.md) (who may see the
data). Library APIs below were checked against Lightweight Charts 5.2.1 typings; verify against the
installed version of every UI/AI library before relying on a name.

## Contents

1. Chart payload contract (provenance record)
2. EODHD → Lightweight Charts mapping
   - 2.1 Time fields · 2.2 Price basis · 2.3 Gaps · 2.4 Volume · 2.5 Event markers · 2.6 Live candle ·
     2.7 Display time zone · 2.8 Payload builder and acceptance checks · 2.9 Built-in vs primitives;
     extended-hours session shading
3. Recipe: candlestick + moving averages + support/resistance
4. Streamlit specifics
5. Other UI stacks (Next.js/React, FastAPI, static/mobile, BI tools)
6. Financial UI conventions (colour by locale, figures, formatting, stale badges, time zones, dense screens)
7. Dashboard tie-out review
   - 7.1 Pre-publication prose QA
8. Evaluating an EODHD AI assistant
9. Natural-language-to-SQL over the user's own archive (with worked question → SQL pairs)
10. News RAG specifics (with abnormal news volume)
11. A private MCP server over EODHD REST vs the official EODHD MCP v2 (resources, caller scope, job approval)
12. Synthetic market-data generator
13. Agent run state and multi-agent forecasts
14. Out of scope here

---

## 1. Chart payload contract (provenance record)

**Use when** any chart, table or widget shows EODHD-derived numbers.

**EODHD inputs**: whichever endpoint fed the view; the record below travels with the data.

**Method.** Every payload the server sends to a UI carries one provenance record. The UI renders the
label fields next to the chart; the rest goes to a "data details" disclosure and to logs.

| Field | Meaning | Example |
|---|---|---|
| `symbol` | EODHD `CODE.EXCHANGE` actually requested | `BP.LSE` |
| `currency`, `price_unit_multiplier` | quote currency as returned per symbol, and the factor applied for display | `GBX`, `1` (shown as pence) or `0.01` (shown as GBP) |
| `interval` | `1d`, `1w`, `1mo`, `1m`, `5m`, `1h`, `live` | `1d` |
| `basis` | `raw`, `split_adjusted`, `total_return_adjusted` | `total_return_adjusted` |
| `source.endpoint`, `source.params` | path and non-secret parameters | `/api/eod/BP.LSE`, `{"from": "2024-01-01"}` |
| `source.capture_id`, `retrieved_at` | your capture key and UTC retrieval time | `cap_7f3…`, `2026-10-24T21:05:11Z` |
| `as_of` | last **observation** in the payload (session date or UTC bar start), not the retrieval time | `2026-10-24` |
| `observation_kind` | `eod_final`, `intraday_bar`, `delayed_snapshot`, `stream_trade`, `stream_minute_bar` | `eod_final` |
| `provisional_from` | first time point that is provisional (live candle), else null | `2026-10-25` |
| `derived` | list of transformations with formula/version | `["adj_ohlc = ohlc * adjusted_close/close", "sma50(adjusted_close)"]` |
| `gaps`, `markers_snapped`, `rejected_rows` | what the builder changed or refused (section 2.8) | `[{"date": "2026-05-04", "reason": "no row"}]` |
| `synthetic` | true for generated data (section 12) | `false` |

**Pitfalls.** `as_of` from the HTTP response time makes a holiday look fresh. Basis labels must
describe the *displayed* series: an adjusted candle with raw volume is two bases and both are named.

**Acceptance checks.** A payload without `basis`, `currency` or `as_of` fails schema validation. The
token never appears in `source.params` (assert `"api_token" not in json.dumps(payload)`).

---

## 2. EODHD → Lightweight Charts mapping

**Use when** drawing candles/lines from EODHD data in Lightweight Charts (the same rules apply to other
plotting libraries; only API names change).

**EODHD inputs**: `/api/eod/{SYM}` (`date, open, high, low, close, adjusted_close, volume`; 1 call;
`period=d|w|m`), `/api/intraday/{SYM}` (`timestamp` Unix s UTC bar start, `gmtoffset`, `datetime`,
OHLCV; 5 calls; Extended or All-In-One), `/api/real-time/{SYM}` (session snapshot with `timestamp`,
O/H/L/C, `volume`, `previousClose`; 1 call per symbol), WebSockets (`t` in **milliseconds**; 0 calls),
the minute-bar REST backfill `https://ws.eodhistoricaldata.com/history?market=us|eu&symbol=` (closed
1-minute bars, `t` ms bar open, `c` = close), `/api/div` and `/api/splits` (`date` = ex-date),
`/api/calendar/earnings` (`report_date`, `before_after_market`), `/api/technical/{SYM}?function=splitadjusted`
(split-only OHLC; 5 calls), `/api/exchange-details/{EX}` (holidays, sessions).

### 2.1 Time fields

| EODHD field | Lightweight Charts `time` | Notes |
|---|---|---|
| EOD `date` `"YYYY-MM-DD"` | business-day string `"YYYY-MM-DD"` (or `{year, month, day}`) | A session label, not an instant: never convert through a JS `Date` in local time (it can shift a day). |
| Intraday `timestamp` (s, UTC, bar start) | `UTCTimestamp` = same integer | Already seconds. Ignore `gmtoffset` for plotting. |
| WebSocket / minute-bar `t` (ms) | `Math.floor(t / 1000)`; for a minute bucket `Math.floor(t / 60000) * 60` | Passing ms makes the chart land in the year ~50,000. |
| Live v1 `timestamp` (s) | for a daily chart: the exchange-local **session date** of that timestamp as `"YYYY-MM-DD"` | Compute on the server with the exchange's IANA zone. |

Rules enforced by the library: one time format per series; times strictly ascending and unique
(duplicates silently replace, out-of-order points are dropped or throw). Sort and **reject** duplicates
in the builder rather than letting the chart decide which one wins. Weekly/monthly `period=w|m` rows:
verify with a probe request which calendar day the `date` label carries before aligning them with daily
markers.

### 2.2 Price basis

| Basis | How | Label |
|---|---|---|
| Raw (as traded) | O/H/L/C as returned | "Raw prices; splits shown as markers" |
| Total-return adjusted | per row `k_t = adjusted_close_t / close_t`; plot `open·k, high·k, low·k, adjusted_close` | "Adjusted for splits and dividends (as of <retrieval date>)" |
| Split-adjusted only | Technical API `function=splitadjusted` | "Split-adjusted, dividends not adjusted" |

`k_t` is per row ([data-semantics.md](data-semantics.md#price-basis)); a row with missing/zero `close`
or missing `adjusted_close` becomes whitespace, not a candle with `k = 1`. Adjusted history is restated
after every new action: on a new ex-date the whole adjusted series must be re-pulled and `setData`
called again (not `update`). Intraday bars are unadjusted; do not draw them on the same series as
adjusted daily candles. Indices have `adjusted_close == close`.

### 2.3 Gaps for missing sessions

A session the exchange was open but the response has no row (thin trading, delisted gaps) is a gap,
not a zero and not a carried-forward candle. Represent it as a **whitespace point** `{time}` (no
value fields; `null` values are not accepted). To know which sessions *should* exist, build the session
list from weekdays minus `/api/exchange-details` holidays for the range; holidays get **no point at all**
(they are not sessions). A row on a listed holiday (a carried-over flat bar) is reported in
`rejected_rows` and not drawn. Intraday null-filled bars (`open`/`close` null) become whitespace; a US
5m record at 20:00 UTC with O=H=L=C and null volume is a session-close marker and is dropped
([coverage-notes.md](coverage-notes.md#intraday-and-real-time-semantics)).

### 2.4 Volume histogram

- Separate pane (`chart.addSeries(HistogramSeries, opts, 1)`) or an overlay scale
  (`priceScaleId: ''` with `scaleMargins: {top: 0.7, bottom: 0}`); `priceFormat: {type: 'volume'}`.
- EOD `volume` is split-adjusted; it is consistent with split-adjusted or total-return-adjusted price
  displays. On a **raw** price chart label the volume "split-adjusted shares" — older bars show more
  shares than were traded at the time.
- Intraday volume is raw; summed intraday volume is typically below the consolidated daily figure. US
  WebSocket volume is from a single venue: do not paste it into the daily volume bar; show the live
  bar's volume as partial or omit it.
- FOREX has no volume: hide the pane rather than drawing zeros. Index volume can be 0 (e.g. VIX).
- Colour each bar by the candle direction (`close >= open`) using the same semantic colours as the
  candles (section 6), optionally at reduced opacity.

### 2.5 Event markers (dividends, splits, earnings)

Markers belong on a bar that exists. Lightweight Charts 5.2.1 does not drop a marker whose time is not
a bar: it attaches it to the nearest **earlier** bar (nearest later only before the first bar). For an
event dated on a non-session day that is the wrong side, and older versions behave differently, so
snap explicitly in the builder and report every snap.

| Event | EODHD field | Target bar | Marker text |
|---|---|---|---|
| Dividend | `/div` `date` (ex-date), `unadjustedValue`, `currency` | ex-date; if not a session, the **next** session | `D 0.24 USD` (amount in the dividend's own currency; LSE dividends are often GBP while the price is GBX) |
| Split | `/splits` `date`, `split` `"new/old"` | ex-date; if not a session, next session | `S 4:1` / `S 1:10` |
| Earnings | `/calendar/earnings` `report_date`, `before_after_market`, `actual`, `estimate` | first session that can react: `BeforeMarket` → `report_date`; `AfterMarket` → next session after `report_date`; null → `report_date`, text "time n/a" | `E 1.52 vs 1.43` |

Steps: (1) build the ordered session list of the plotted series; (2) for each event, binary-search the
first session ≥ target date; (3) if none (event after the last bar, e.g. a declared future ex-date),
put it in a separate "upcoming" list, not on the chart; (4) record `{event, original_date, snapped_to}`
when they differ; (5) sort markers by time and pass them with `createSeriesMarkers(series, markers)`
(v5; `series.setMarkers` is v4). Use `position: 'aboveBar'|'belowBar'|'inBar'`, `shape:
'circle'|'square'|'arrowUp'|'arrowDown'`, required `color`, optional `text`, `id`.

### 2.6 Live candle via `update()`

- Load completed history once with `setData`. Afterwards call `series.update(point)`: it appends when
  `time > last` and replaces when `time === last`. Never call `setData` per tick.
- Daily chart + delayed snapshot (Live v1): the provisional candle is `{time: session_date, open, high,
  low, close}` from the snapshot. Skip a snapshot with `open <= 0` or `close` outside `[low, high]`.
  Never apply it when `session_date <= last completed EOD date` — a snapshot must not overwrite a final
  bar, and on a closed market the snapshot repeats the previous session. When EOD for that session
  arrives, replace the provisional bar from EOD (for adjusted charts: reload the series).
- Intraday chart + trade stream: bucket each trade into `floor(t_ms / 60000) * 60`; open = first price
  in the bucket, high/low = extrema, close = last; a trade for an earlier bucket than the current one is
  logged and not applied (late data does not rewrite a displayed bar; reconcile later from
  `/api/intraday` after finalization). Candle stream (`us-candles`/`eu-candles`): the current minute is
  re-sent with growing `v`; take the newest message per `t` and `update()` with it — never sum.
- After a disconnect, backfill closed minutes from the minute-bar REST endpoint (sparse: only minutes
  with trades), rebuild the array and `setData` once; `update(point, true)` can amend an existing
  historical point but cannot insert a missing one.
- Show the provisional state visibly (e.g. hollow candle or "live, delayed ~15 min" badge) and keep
  `provisional_from` in the payload.

### 2.7 Display time zone

The library plots everything as UTC and has no time-zone option. Keep data in UTC and format labels
with `timeScale.tickMarkFormatter` and `localization.timeFormatter` using
`Intl.DateTimeFormat(locale, {timeZone: 'America/New_York', …})`. Pre-shifting timestamps by an offset
also moves bars on the time axis and breaks across DST; do it only if the chart must show wall-clock
spacing, and never in stored data. Business-day (daily) data needs no time-zone handling.

### 2.8 Payload builder and acceptance checks

```python
import bisect

def build_daily_payload(rows, *, symbol, currency, basis="raw", sessions=None,
                        holidays=(), events=(), capture_id=None, retrieved_at=None):
    """rows: /api/eod JSON. sessions: expected 'YYYY-MM-DD' session list for the range (optional).
    events: dicts {kind, date, text, before_after_market?}. Returns a Lightweight Charts payload."""
    dates = [r["date"] for r in rows]
    if len(set(dates)) != len(dates):
        raise ValueError("duplicate dates in EOD rows")
    if dates != sorted(dates):
        raise ValueError("EOD rows not ascending")
    by_date, holidays = {r["date"]: r for r in rows}, set(holidays)
    rejected = [{"date": d, "reason": "row on exchange holiday"} for d in dates if d in holidays]
    timeline = sorted(sessions) if sessions else [d for d in dates if d not in holidays]
    candles, volume, gaps, closes = [], [], [], []
    for d in timeline:
        r = by_date.get(d)
        o, h, l, c = (r.get(f) if r else None for f in ("open", "high", "low", "close"))
        if r is None or None in (o, h, l, c) or not c:
            candles.append({"time": d}); volume.append({"time": d})        # whitespace = gap
            gaps.append({"date": d, "reason": "no row" if r is None else "incomplete OHLC"})
            continue
        k = 1.0
        if basis == "total_return_adjusted":
            if r.get("adjusted_close") is None:
                candles.append({"time": d}); volume.append({"time": d})
                gaps.append({"date": d, "reason": "no adjusted_close"}); continue
            k = r["adjusted_close"] / c
        candles.append({"time": d, "open": o * k, "high": h * k, "low": l * k, "close": c * k})
        closes.append((d, c * k))
        v = r.get("volume")
        volume.append({"time": d, "value": v, "up": c >= o} if v is not None else {"time": d})
    bars = [p["time"] for p in candles if "close" in p]
    markers, snapped, upcoming = [], [], []
    for e in sorted(events, key=lambda e: e["date"]):
        target = e["date"]
        i = bisect.bisect_left(bars, target)
        if e.get("kind") == "earnings" and e.get("before_after_market") == "AfterMarket":
            i = bisect.bisect_right(bars, target)                 # first session after the report
        if i >= len(bars):
            upcoming.append(e); continue
        if bars[i] != target:
            snapped.append({"event": e["kind"], "original_date": target, "snapped_to": bars[i]})
        markers.append({"time": bars[i], "kind": e["kind"], "text": e.get("text", "")})
    markers.sort(key=lambda m: m["time"])                         # library expects ascending times
    return {
        "candles": candles, "volume": volume, "markers": markers, "upcoming_events": upcoming,
        "provenance": {"symbol": symbol, "currency": currency, "interval": "1d", "basis": basis,
                       "source": {"endpoint": f"/api/eod/{symbol}", "capture_id": capture_id},
                       "retrieved_at": retrieved_at, "as_of": closes[-1][0] if closes else None,
                       "observation_kind": "eod_final", "provisional_from": None,
                       "gaps": gaps, "markers_snapped": snapped, "rejected_rows": rejected,
                       "synthetic": False},
    }
```

The server maps `kind` to marker shape/colour and `up` to the volume colour before sending, or the
client does it; keep `kind` so the legend can explain the markers.

Acceptance checks (all on hand-made rows):

- Rows `2026-01-05, 2026-01-05` → `ValueError` (duplicate). Rows out of order → `ValueError`.
- Sessions `[05, 06, 07]`, rows for 05 and 07 → candle 06 is `{"time": "2026-01-06"}` and `gaps` names it.
- Row `close=100, adjusted_close=50, open=98, high=101, low=97`, basis `total_return_adjusted` →
  candle `49, 50.5, 48.5, 50`.
- Dividend ex-date on Saturday `2026-01-10` with bars on `09` and `12` → marker on `12`, reported in
  `markers_snapped`. Earnings `AfterMarket` on `09` → marker on `12`; `BeforeMarket` on `09` → `09`.
- A `BP.LSE` payload shows `currency: GBX` and the axis label says pence, or the multiplier `0.01` and GBP.
- Intraday: a timestamp list containing `1700000000000` (ms) is rejected by a `t < 10**11` guard.

### 2.9 Built-in API vs primitives; extended-hours session shading

What Lightweight Charts 5.2.1 draws by itself and what needs a series primitive
(`series.attachPrimitive(obj)`, an object with `attached`, `updateAllViews` and `paneViews` returning views
whose renderer implements `draw` / `drawBackground`):

| Need | Built in | Primitive |
|---|---|---|
| Dividend, split and earnings markers | `createSeriesMarkers(series, markers)` (§2.5) | — |
| Horizontal support/resistance levels | `series.createPriceLine(...)` (§3) | — |
| Provisional (live) candle | `series.update(point)` plus a per-point hollow style or a badge (§2.6) | — |
| Level **zones** (level ± tolerance), rectangles, trend lines | — | yes |
| Pre-/after-hours or lunch-break shading on intraday charts | — | yes (below) |

**EODHD inputs**: `v2/exchange-details/{CODE}` (1 call, cache it): `Timezone`, `TradingHours.PreMarketOpen`,
`PreMarketClose`, `AfterHoursOpen`, `AfterHoursClose` (present only where the exchange has those sessions,
e.g. US), `ExchangeHolidays` with `EarlyClose`. US 1-minute bars include pre-market and after-hours trades;
pre-market minutes can be sparse.

**Method.**

1. For each plotted session day, convert the local session times to UTC with the IANA zone (DST-aware):
   pre band `[PreMarketOpen, PreMarketClose)`, post band `[Close or EarlyClose, AfterHoursClose)`. v2 gives
   no separate after-hours end for early-close days; the band uses `AfterHoursClose` as an upper bound, and
   only bars that exist are shaded.
2. Draw each band from the first to the last bar inside it, half a bar spacing on each side; a band with no
   bars draws nothing (no invented activity).
3. Draw in `drawBackground` with `zOrder() = 'bottom'` so candles stay on top; label the legend
   "extended hours (exchange-details v2)".
4. Daily charts never get bands: daily bars are regular session only.

```javascript
// Pure helpers: extended-hours bands (UTC seconds) from a cached v2 exchange-details object.
function zonedToUtcSeconds(day, hhmmss, timeZone) {
  // day 'YYYY-MM-DD', wall-clock time in timeZone -> UTC seconds (two passes handle DST)
  const [y, mo, d] = day.split('-').map(Number);
  const [h, mi, s] = hhmmss.split(':').map(Number);
  const wall = Date.UTC(y, mo - 1, d, h, mi, s);
  const fmt = new Intl.DateTimeFormat('en-US', { timeZone, hourCycle: 'h23', year: 'numeric',
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const offsetAt = (ms) => {
    const p = Object.fromEntries(fmt.formatToParts(new Date(ms)).map((x) => [x.type, x.value]));
    return Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second) - ms;
  };
  let guess = wall - offsetAt(wall);
  guess = wall - offsetAt(guess);
  return Math.floor(guess / 1000);
}

export function extendedHoursBands(details, sessionDays) {
  const th = details.TradingHours, tz = details.Timezone, hol = details.ExchangeHolidays || {};
  const bands = [];
  for (const day of sessionDays) {
    const close = hol[day]?.Type === 'EarlyClose' ? hol[day].EarlyClose : th.Close;
    if (th.PreMarketOpen && th.PreMarketClose)
      bands.push({ kind: 'pre', from: zonedToUtcSeconds(day, th.PreMarketOpen, tz), to: zonedToUtcSeconds(day, th.PreMarketClose, tz) });
    if (th.AfterHoursOpen && th.AfterHoursClose)
      bands.push({ kind: 'post', from: zonedToUtcSeconds(day, close, tz), to: zonedToUtcSeconds(day, th.AfterHoursClose, tz),
                   earlyClose: close !== th.Close });
  }
  return bands;           // empty when the exchange has no extended sessions in v2
}

// Series primitive: shades each band behind the candles. Edges come from the bars that fall in the band,
// so a band without bars (no extended-hours trades) draws nothing.
export class SessionShading {
  constructor(bands, colors = { pre: 'rgba(120,120,160,0.10)', post: 'rgba(120,120,160,0.16)' }) {
    this._bands = bands; this._colors = colors; this._rects = []; this._view = new ShadingView(this);
  }
  attached({ chart, series, requestUpdate }) { this._chart = chart; this._series = series; requestUpdate(); }
  detached() { this._chart = this._series = undefined; }
  updateAllViews() {
    if (!this._chart) return;
    const ts = this._chart.timeScale(), half = ts.options().barSpacing / 2;
    const times = this._series.data().map((b) => b.time);
    this._rects = [];
    for (const b of this._bands) {
      const inBand = times.filter((t) => t >= b.from && t < b.to);
      if (!inBand.length) continue;
      const x0 = ts.timeToCoordinate(inBand[0]), x1 = ts.timeToCoordinate(inBand[inBand.length - 1]);
      if (x0 === null || x1 === null) continue;
      this._rects.push({ x: x0 - half, w: x1 - x0 + 2 * half, color: this._colors[b.kind] });
    }
  }
  paneViews() { return [this._view]; }
}
class ShadingView {
  constructor(src) { this._src = src; }
  zOrder() { return 'bottom'; }
  renderer() {
    const rects = this._src._rects;
    return { draw() {}, drawBackground(target) {
      target.useBitmapCoordinateSpace(({ context, horizontalPixelRatio: hr, bitmapSize }) => {
        for (const r of rects) { context.fillStyle = r.color; context.fillRect(Math.round(r.x * hr), 0, Math.round(r.w * hr), bitmapSize.height); }
      });
    } };
  }
}
// usage: candleSeries.attachPrimitive(new SessionShading(extendedHoursBands(details, days)));
```

**Acceptance checks** (Node 24, checked against the 5.2.1 typings):

- US, 2026-10-23 (EDT): pre `08:00–13:30Z`, post `20:00Z–00:00Z` next day; 2026-11-02 (EST): pre
  `09:00–14:30Z`, post `21:00Z–01:00Z`; 2026-11-27 (`EarlyClose 13:00`): post starts `18:00Z` and is marked
  `earlyClose: true`.
- An exchange without extended-session fields (LSE fixture) yields no bands.
- With 1-minute bars from 13:00Z to 14:59Z and bar spacing 2 px, the pre band is drawn once, covering the
  30 bars from 13:00Z to 13:29Z (`x = −1`, `width = 60`); bars after 13:30Z are not shaded.

---

## 3. Recipe: candlestick + moving averages + support/resistance

**Use when** a user asks for "a chart with MAs and support/resistance" for one symbol.

**EODHD inputs**: `/api/eod/{SYM}` (1 call, full history), optional `/div` + `/splits` (1 each) for
markers, optional `/api/technical/{SYM}?function=sma&period=50` (5 calls) as a cross-check. EOD All
World or higher; Free is limited to one year (too short for a 200-day MA plus context).

**Method.**

1. Fetch EOD; build the payload on one basis (default `total_return_adjusted` so MAs and levels are
   not broken by splits; for a raw chart, compute MAs on raw closes and mark splits).
2. Moving averages on the same basis as the candles, with `x_t` = displayed close:
   - `SMA_n(t) = (1/n) · Σ_{j=0}^{n-1} x_{t-j}`, defined only once `n` observations exist (emit
     whitespace before).
   - `EMA_n(t) = α·x_t + (1-α)·EMA_n(t-1)`, `α = 2/(n+1)`, seeded with `SMA_n` at the first full window.
   - Windows count *rows*, not calendar days; if a window spans a gap from section 2.3, flag it.
   - The Technical API's default adjustment is splits + dividends (`splitadjusted_only=0`); its SMA
     should match `SMA_n` on `adjusted_close` — confirm with one probe before relying on equality.
3. Support/resistance, choose and label one method:
   - **Swing pivots with N-bar confirmation (no look-ahead).** Bar `i` is a pivot high if
     `high_i > max(high_{i-N..i-1})` and `high_i >= max(high_{i+1..i+N})`; pivot low symmetric with
     lows. It becomes *known* only at bar `i+N`; a level drawn "as of t" uses pivots with `i+N <= t`.
     Cluster pivot prices: a pivot joins a cluster if `|p − mean(cluster)| <= tol`, with
     `tol = m · ATR_14` (typically `m = 0.5`) or a fixed fraction of price. Level = cluster mean;
     strength = number of touches; recency = last touch date. Resistance = levels above the last close,
     support = below; show the nearest 2–3 each side.
   - **Classic floor pivots from the prior session** (`H, L, C` of the previous completed bar):
     `P = (H+L+C)/3`, `R1 = 2P − L`, `S1 = 2P − H`, `R2 = P + (H − L)`, `S2 = P − (H − L)`,
     `R3 = H + 2(P − L)`, `S3 = L − 2(H − P)`.
   - `ATR_n`: `TR_t = max(H_t − L_t, |H_t − C_{t-1}|, |L_t − C_{t-1}|)`; simple `ATR = mean(TR)` over
     the last `n` rows (Wilder smoothing `ATR_t = ATR_{t-1} + (TR_t − ATR_{t-1})/n` if specified).
4. Draw levels as price lines (`series.createPriceLine({price, color, lineStyle: LineStyle.Dashed,
   axisLabelVisible: true, title: 'R ×3'})`), not as extra series. Shaded zones (level ± tol) need a
   pane/series primitive; the built-in API has only lines and markers (section 2.9; the shading primitive
   there draws vertical bands, a zone primitive uses `series.priceToCoordinate` for the vertical edges).
5. Caption: "Levels: swing pivots N=3, clustered within 0.5×ATR(14), adjusted basis, as of <date>.
   Descriptive, not a forecast."

```python
def sma(x, n):
    out, s = [], 0.0
    for i, v in enumerate(x):
        s += v
        if i >= n:
            s -= x[i - n]
        out.append(s / n if i >= n - 1 else None)
    return out

def swing_pivots(high, low, n=3):
    """Confirmed pivots: (pivot_index, known_at_index, price, 'H'|'L'). No look-ahead past known_at."""
    piv = []
    for i in range(n, len(high) - n):
        if high[i] > max(high[i - n:i]) and high[i] >= max(high[i + 1:i + n + 1]):
            piv.append((i, i + n, high[i], "H"))
        if low[i] < min(low[i - n:i]) and low[i] <= min(low[i + 1:i + n + 1]):
            piv.append((i, i + n, low[i], "L"))
    return piv

def atr(high, low, close, n=14):
    tr = [max(high[t] - low[t], abs(high[t] - close[t - 1]), abs(low[t] - close[t - 1]))
          for t in range(1, len(close))]
    return sum(tr[-n:]) / min(n, len(tr))

def levels_as_of(high, low, close, t, n=3, tol_atr=0.5):
    """Support/resistance clusters using only pivots known at bar t."""
    tol = tol_atr * atr(high[:t + 1], low[:t + 1], close[:t + 1])
    prices = sorted(p for i, k, p, _ in swing_pivots(high[:t + 1], low[:t + 1], n) if k <= t)
    clusters = []
    for p in prices:
        if clusters and abs(p - sum(clusters[-1]) / len(clusters[-1])) <= tol:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    last = close[t]
    out = [{"price": sum(c) / len(c), "touches": len(c)} for c in clusters]
    for lv in out:
        lv["kind"] = "resistance" if lv["price"] > last else "support"
    return out

def floor_pivots(h, l, c):
    p = (h + l + c) / 3
    return {"P": p, "R1": 2 * p - l, "S1": 2 * p - h, "R2": p + (h - l), "S2": p - (h - l),
            "R3": h + 2 * (p - l), "S3": l - 2 * (h - p)}
```

Client wiring (Lightweight Charts v5):

```js
import { createChart, CandlestickSeries, HistogramSeries, LineSeries,
         createSeriesMarkers, LineStyle } from 'lightweight-charts';

export function renderChart(el, p, colors) {           // p = payload from section 2.8 (+ sma50, levels)
  const chart = createChart(el, { autoSize: true });
  const candles = chart.addSeries(CandlestickSeries, {
    upColor: colors.up, downColor: colors.down, wickUpColor: colors.up, wickDownColor: colors.down,
    borderVisible: false });
  candles.setData(p.candles);
  const sma50 = chart.addSeries(LineSeries, { lineWidth: 1, priceLineVisible: false,
                                              lastValueVisible: false, color: colors.ma });
  sma50.setData(p.sma50);                              // whitespace {time} until the window is full
  const vol = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' } }, 1);  // pane 1
  vol.setData(p.volume.map(v => ('value' in v)
    ? { time: v.time, value: v.value, color: v.up ? colors.upMuted : colors.downMuted } : { time: v.time }));
  createSeriesMarkers(candles, p.markers.map(m => ({ time: m.time, position: 'aboveBar',
    shape: 'circle', color: colors[m.kind], text: m.text })));
  for (const lv of p.levels) candles.createPriceLine({ price: lv.price, color: colors[lv.kind],
    lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: `${lv.kind[0].toUpperCase()} ×${lv.touches}` });
  return chart;                                        // caller calls chart.remove() on unmount
}
```

**Pitfalls.** Pivots computed on the full series and drawn at earlier dates leak the future (a level
"confirmed" by later bars). Mixing raw candles with MAs from `adjusted_close` misplaces the MA by the
cumulative factor. A 200-day MA on a symbol with 150 rows must not appear. Weekly analysis via
`period=w` changes N and ATR scale; restate the parameters. FOREX levels have no volume confirmation.

**Acceptance checks.** `sma([1..10], 3)[-1] == 9.0`, first two values `None`. `floor_pivots(110, 90,
100)` → `P 100, R1 110, S1 90, R2 120, S2 80, R3 130, S3 70`. Highs `[1,2,3,9,3,2,1,2,3]`, `n=3` →
one pivot high at index 3, known at index 6; `levels_as_of(..., t=5)` contains no level from it. A
synthetic series with a planted double top at 120 (two pivot highs 119.8 and 120.2, `tol_atr · ATR`
> 0.4) yields one resistance at 120.0 with `touches == 2`.

---

## 4. Streamlit specifics

**Use when** building a private Python dashboard. Check the installed Streamlit version's API
reference (`st.fragment` requires a recent 1.x release; error-detail options changed over versions).

**EODHD inputs**: as per view; budget live polling explicitly (Live v1 = 1 call per symbol per request).

**Method.**

1. **Secrets.** Read `EODHD_API_TOKEN` from `st.secrets` (`.streamlit/secrets.toml`, git-ignored, or
   the host's secrets UI) with an environment-variable fallback. Streamlit code runs on the server, so
   the key is not shipped to the browser — unless it is printed. Send it in the `Authorization: Bearer`
   header (accepted in a 2026-10-25 test; fall back to the query parameter) so exception messages that
   include the URL do not contain it; catch request exceptions and show a sanitized message; set
   `client.showErrorDetails` to its most restrictive value in production.
2. **Cache data, not clients.** `@st.cache_data(ttl=…, max_entries=…)` on fetch functions whose
   arguments are the full cache key: `symbol, interval, basis, start, end, data_epoch`. Arguments
   starting with `_` are not hashed — never put the key-relevant parameter there. Use
   `@st.cache_resource` for the HTTP session/limiter object (one per process, shared).
3. **TTL by dataset.** Prefer a `data_epoch` argument derived from the update schedule over a fixed TTL
   for EOD (the cache then rolls exactly when new data can exist):

   | Dataset | Key/TTL policy |
   |---|---|
   | EOD history | `data_epoch` = last expected update instant (US ~16:15 ET + refinement next morning; others 2–3 h after close); TTL ≤ 24 h as a backstop |
   | Fundamentals | TTL 1 day; reload after earnings |
   | Intraday history | TTL 1 h; today's bars are not final until ~2–3 h after the US close |
   | Live v1 snapshot | TTL 60 s (refresh cadence ~1 min) |
   | Symbol lists / exchange details | TTL 1 day |

4. **Session state** (`st.session_state`) holds selections (symbol, interval, basis, watchlist) and
   widget keys; it is per browser session. `st.cache_data` is **global to the process, shared across
   all sessions/users**: with per-user entitlements or private holdings, include the user scope in the
   key or do not cache those results.
5. **Partial reruns for live panels.** Put the quote panel in a fragment that re-runs on a timer
   (`@st.fragment(run_every=60)`), so the whole script and the chart are not rebuilt every minute.
   Budget: `calls/day ≈ symbols × (open_minutes / refresh_minutes)` per cache entry, independent of the
   number of viewers if the fetch is cached with TTL ≥ refresh. 20 symbols, 60 s, 6.5 h session →
   20 × 390 = 7,800 calls/day; running 24 h → 28,800.
6. **No backfills on rerun.** Universe downloads and history backfills run as a separate job (CLI/cron)
   writing to the local store ([ingestion.md](ingestion.md)); the app reads the store and shows the
   job's checkpoint and `as_of`.
7. **Deployment.** Pin `streamlit` and chart-component versions. A private app needs viewer
   authentication; a public or shared app is display to others → commercial licence
   ([licensing.md](licensing.md)). Do not deploy the secrets file; set secrets in the host.

```python
import os, datetime as dt, requests, streamlit as st

def _token():
    try:
        return st.secrets["EODHD_API_TOKEN"]
    except Exception:                      # no secrets file / key (exception type varies by version)
        return os.environ["EODHD_API_TOKEN"]

@st.cache_resource
def http():
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {_token().strip()}"
    return s

@st.cache_data(ttl=dt.timedelta(hours=24), max_entries=200, show_spinner=False)
def eod(symbol: str, start: str, end: str, data_epoch: str) -> list[dict]:
    r = http().get(f"https://eodhd.com/api/eod/{symbol}",
                   params={"from": start, "to": end, "fmt": "json"}, timeout=(5, 60))
    if r.status_code != 200:
        raise RuntimeError(f"EOD {symbol}: HTTP {r.status_code}")   # no URL, no token
    return r.json()

@st.fragment(run_every=60)
def quote_panel(symbols: tuple[str, ...]):
    ...  # cached live fetch (ttl=60), freshness badge from the snapshot timestamp

sym = st.session_state.setdefault("symbol", "AAPL.US")
```

**Acceptance checks.** `grep -R "api_token\|EODHD_API_TOKEN=" .` finds nothing committed; the
secrets file is in `.gitignore`. Forcing a 403 renders a sanitized error without the token. Two
browser sessions with different symbols do not trigger duplicate fetches for a shared symbol (one cache
entry). Changing `basis` produces a new cache entry and a re-labelled chart. The quote panel refreshes
without re-running the chart code (log line count).

---

## 5. Other UI stacks (briefly)

- **Next.js / React.** Fetch EODHD only in server code (Route Handlers / server components) with
  `process.env.EODHD_API_TOKEN`; anything prefixed `NEXT_PUBLIC_` (or `VITE_`) is shipped to the
  browser. Expose narrow routes (`/api/chart?symbol=&interval=&basis=&from=&to=`) with validated
  inputs and a span limit, not a generic proxy. Cache with explicit revalidation matching section 4's
  table. The chart component is client-only (`'use client'`, create in `useEffect`, `chart.remove()`
  in cleanup; load via `next/dynamic` with `ssr: false` from server-rendered pages).
- **FastAPI backend.** Typed query parameters with bounds (`symbol` pattern, `from/to` dates, maximum
  span per interval: 120/600/7200 days for 1m/5m/1h), a response model including the provenance record,
  a shared cost-aware client ([code-patterns.md](code-patterns.md#1-cost-aware-client)) created at
  startup, per-user auth and per-user call budgets, CORS restricted to the app origin, and no token in
  logs (`r.url` contains it when passed as a query parameter).
- **Static pages, single-file artifacts, mobile apps.** Anything in the bundle is public. Either call
  your own backend or embed a dated, pre-fetched snapshot with its `as_of`; a page shown to others is
  display to others ([licensing.md](licensing.md)). Offline caches show their observation time.
- **BI tools (Power BI, Superset, Metabase).** Serve from the local warehouse, not per-visual API
  calls; refresh after the exchange update window and document the refresh call estimate. Measures:
  never SUM prices, returns or ratios; use last value for holdings/market cap, explicit FX measures with
  date and orientation; label basis/currency/as-of on visuals. Shared workspaces need commercial rights.

---

## 6. Financial UI conventions

**Use when** building or reviewing a watchlist, holdings table, ticker tape or terminal-style screen.

**Colour semantics depend on locale.** Many Western markets use green = up, red = down; mainland
China, Taiwan and South Korea use red = up (Korea: blue = down). EODHD covers these markets
(`SHG`, `SHE`, `TW`, `TWO`, `KO`, `KQ`). Japan and Hong Kong usage is mixed. Make direction colour a user
setting with a locale default, keep it separate from brand colours, and **always** pair colour with a
sign and/or arrow so the meaning survives colour-blindness and greyscale printing.

```python
SCHEMES = {"green_up": {"up": "green", "down": "red"},
           "red_up": {"up": "red", "down": "green"},
           "red_up_blue_down": {"up": "red", "down": "blue"}}
DEFAULT_SCHEME = {"SHG": "red_up", "SHE": "red_up", "TW": "red_up", "TWO": "red_up",
                  "KO": "red_up_blue_down", "KQ": "red_up_blue_down"}   # defaults; user setting wins

def direction_style(change, exchange, user_scheme=None):
    scheme = SCHEMES[user_scheme or DEFAULT_SCHEME.get(exchange, "green_up")]
    if change is None:
        return {"direction": "unknown", "color": "neutral", "glyph": "–"}
    if change == 0:
        return {"direction": "flat", "color": "neutral", "glyph": "▬"}
    d = "up" if change > 0 else "down"
    return {"direction": d, "color": scheme[d], "glyph": "▲" if d == "up" else "▼"}
```

`color` is a semantic token resolved by the theme to an accessible shade, never a raw brand colour.

**Figures and alignment.** Numeric columns right-aligned with tabular figures
(`font-variant-numeric: tabular-nums`) so digits line up while values update; decimal alignment within a
column; minus sign as U+2212 or a parenthesis convention, consistently.

**Formatting rules.**

| Quantity | Store | Display | Example |
|---|---|---|---|
| Price | full precision | per-instrument decimals: stocks usually 2 (GBX/ZAC often 0–2, sub-unit prices up to 4); FOREX 4–5 (JPY pairs 2–3); crypto by magnitude | `638.50 GBX`, `1.08734` |
| Return / change | decimal fraction | `+1.23%` (`x · 100`) | `0.0123 → +1.23%` |
| Difference of two percentages | decimal | percentage points | yield 4.10% → 4.35%: `+0.25 pp` (`+25 bp`), not `+6.1%` |
| Basis points | decimal | `x · 10,000` bp | `0.0025 → 25 bp` |
| Large values | full | abbreviated with unit and currency | `2.41T USD`, `485.0M GBP` |
| Volume | integer shares | abbreviated, unit "shares" | `12.3M sh` |

Use ISO currency codes, not symbols, when several currencies appear; keep the minor-unit code visible
(`GBX`, `ZAC`) or convert explicitly. Round only at display.

```python
def fmt_pct(x, dp=2):   return None if x is None else f"{x * 100:+.{dp}f}%".replace("-", "−")
def fmt_pp(dx, dp=2):   return None if dx is None else f"{dx * 100:+.{dp}f} pp".replace("-", "−")
def fmt_bp(x, dp=0):    return None if x is None else f"{x * 1e4:+.{dp}f} bp".replace("-", "−")
```

**Accessible colours.** Text contrast ≥ 4.5:1 (≥ 3:1 for large text) and graphical elements (candle
bodies, lines, markers) ≥ 3:1 against the background; test both themes. Offer a colour-blind-safe
pair (e.g. blue/orange) as a setting. Tables need keyboard navigation (arrow keys between rows, Enter to
open) and visible focus. Charts need a tabular alternative (the payload's rows).

**Stale and state badges.** Each value carries one of: `live (delayed ~N min)`, `EOD <date>`,
`stale`, `market closed`, `no data`, `no access`. Rules:

- Delayed snapshot during the session: stale if `now − observation_time > nominal_delay + 2 × refresh`
  (e.g. > 17 min for a 15-min delayed stock refreshed each minute); thin names may legitimately be older —
  show the observation time, not just the badge.
- EOD: stale if the last bar's date is earlier than the last completed session **and** the expected
  update time for that exchange has passed ([coverage-notes.md](coverage-notes.md#end-of-day-semantics)).
- Market closed (holiday/weekend per `/api/exchange-details`): show `market closed`, not stale.
- A badge is computed from observation time, never from fetch time or repaint time.

**Time zones.** Show exchange-local time for sessions and quotes (`16:00 ET`), the user's zone only for
"last updated"; label the zone. Daily bars are dates without a zone. Earnings without time show
"time not provided", not 00:00.

**Watchlist row**: symbol and name, last, change, change %, currency/unit, observation time or badge,
basis if adjusted. **Paper order ticket** (simulation only, see
[paper-accounting.md](paper-accounting.md)): confirm disabled until inputs validate; show the price
used, its observation time and the estimated cost; label "simulated".

**Dense screens (terminals, blotters, monitoring tools).**

- **Empty states keep the panel's size** and say why it is empty: `no data for this range`, `no access on
  this plan`, `market closed`, `not archived`. A collapsed panel shifts every other panel and hides the fact
  that something is missing.
- **Popovers and sidebars never cover the value they explain.** Anchor them beside the cell or row, close
  them with `Esc`, return focus to the cell, and keep the qualified value visible while they are open.
- **Density for operated tools:** compact rows (about 24–28 px), fixed column widths per numeric column so
  digits do not shift on update, abbreviations with a legend, no decorative metrics or sparklines that do
  not support a decision. Offer a comfortable density as a setting, not as the default.
- **No state before the user acts.** Do not pre-fill quantities, pre-select a side, or show an alert or
  order as active until the user has set it. Defaults are shown as placeholders, and a simulated order
  starts as a draft.

**Acceptance checks.** `direction_style(1.0, "SHG")` → `{"direction": "up", "color": "red", "glyph":
"▲"}`; `direction_style(1.0, "US")` → green; `direction_style(-1, "KO")` → blue ▼. Toggling the user setting switches colours without changing glyphs. `fmt_pct(0.0123)
== "+1.23%"`, `fmt_bp(0.0025) == "+25 bp"`, `fmt_pp(0.0435 - 0.0410) == "+0.25 pp"`. On a US holiday the
watchlist shows `market closed` and yesterday's EOD date, not `stale`.
An empty holdings panel keeps its height and shows `no data for this range` (or `no access`); a new
paper order ticket opens with no side selected and an empty quantity.

---

## 7. Dashboard tie-out review

**Use when** releasing or changing a financial dashboard or report.

**EODHD inputs**: the stored captures behind the dashboard; at most a few fresh probe requests.

**Method.**

1. Freeze one review session: record `review_started_at` and the capture IDs/`as_of` of every panel.
   Compare values only within that session (do not mix a live refresh with a stored figure).
2. List every headline number (NAV, P&L, return, yield, market value, counts) with its panel, label,
   displayed value and display precision.
3. Recompute each from the stored captures with an independent query or script (not the dashboard's own
   code path). Tolerance = display rounding: `|displayed − recomputed| ≤ 0.5 · 10^(−dp)` in the displayed
   unit; anything larger is a finding.
4. Check label vs formula: price vs total return; raw vs adjusted; local vs base currency (FX pair,
   date, orientation); period (MTD/YTD/1Y, inclusive dates); per-share vs total; minor units.
5. Check totals: holdings sum to NAV; allocations sum to 100% (±rounding); a position with a missing
   price is shown as missing and still counted in the "unpriced" line, not dropped.
6. Check freshness badges against `as_of` and the exchange calendar.
7. Report each mismatch with both values, the formula, capture/query IDs and a screenshot reference.
   **Stop** at reporting: do not "fix" by editing displayed numbers; fixes go through code review and
   the check is re-run.

| # | Panel | Label | Displayed | Recomputed | Δ | Evidence | Status |
|---|---|---|---|---|---|---|---|
| 1 | Summary | NAV (EUR) | 125,430.12 | 125,430.12 | 0 | q_nav_v3, cap_… | PASS |
| 2 | Holdings | 1Y return VWCE | +14.2% | +12.9% | 1.3 pp | price-only used; label says total return | FAIL |

**Acceptance checks.** A seeded defect (return computed on `close` while labelled total return) is
detected; a seeded FX inversion (EURUSD used as USD per EUR inverted) is detected; the report lists
evidence for every row and contains no PASS without a recomputed value.

### 7.1 Pre-publication prose QA

**Use when** a market note, newsletter, AI answer or report paragraph quotes dates, levels and changes
before it goes to readers.

**EODHD inputs**: the cached calendar (`v2/exchange-details`, 1 call per exchange) and stored EOD closes for
every symbol the text quotes (`eod/{SYM}`, 1 call each if not archived); resolved names from the symbol
list or Search.

**Method.**

1. Extract every ISO date; check the stated weekday against the calendar weekday and the date against the
   exchange's sessions (a holiday or weekend quoted as a trading day is a finding).
2. For each quoted level `(symbol, date, value)`, compare with the stored close in display units. A ratio
   near a power of ten means a proxy or unit mix-up (an ETF quoted at index level, e.g. `SPY.US` vs
   `GSPC.INDX` ≈ 10×; GBX vs GBP 100×). Tolerance: 0.5% unless the text says "about".
3. Every ticker cited is accompanied by the resolved name (catches a wrong-company ticker).
4. Units: a change in a rate, yield or spread is written in pp or bp, never "%" (4.10% → 4.35% is
   +0.25 pp / +25 bp).
5. Report findings beside the text; do not rewrite numbers automatically.

```python
import math, re
from datetime import date

DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b(?:\s*\((Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\))?")
RATE_PCT_CHANGE = re.compile(r"\b(yield|rate|spread|margin)s?\b[^.]{0,40}?\b(rose|fell|up|down|increased|decreased)"
                             r"\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%", re.I)

def prose_qa(text, sessions, closes, claims, names):
    """sessions: set of ISO session dates for the cited exchange (cached calendar);
    closes: {(symbol, date): close in display units}; claims: [(symbol, date, quoted level)];
    names: {symbol: resolved name}. Returns findings; never rewrites the text."""
    out = []
    for m in DATE.finditer(text):
        d, wd = m.group(1), m.group(2)
        actual = date.fromisoformat(d).strftime("%a")
        if wd and wd != actual:
            out.append(("weekday", d, f"text says {wd}, calendar says {actual}"))
        if d not in sessions:
            out.append(("not_a_session", d, "holiday/weekend or outside the calendar"))
    for sym, d, level in claims:
        ref = closes.get((sym, d))
        if ref is None:
            out.append(("level_unverified", sym, f"no stored close for {d}"))
            continue
        ratio = level / ref
        if abs(ratio - 1) > 0.005:
            k = round(math.log10(ratio)) if ratio > 0 else None
            hint = f"off by ~10^{k}: proxy or unit mix-up (SPY vs GSPC.INDX, GBX vs GBP)" if k else "mismatch"
            out.append(("level", sym, f"quoted {level} vs close {ref} on {d}: {hint}"))
    for sym, name in names.items():
        if sym.split(".")[0] in text and name.split()[0] not in text:
            out.append(("name", sym, f"ticker cited without its resolved name {name!r}"))
    for m in RATE_PCT_CHANGE.finditer(text):
        out.append(("units", m.group(0), "a change in a rate is in pp or bp, not %"))
    return out
```

**Acceptance checks** (fixture text: "On 2026-10-23 (Thu) SPY closed at 5,800 while the 10-year yield rose
2% to 4.35%. AAPL fell; markets reopen 2026-11-26."; sessions without 2026-11-26; stored `SPY.US` close
579.8 is a fixture value): five findings — weekday (2026-10-23 is a Friday), `not_a_session` for 2026-11-26,
`level` with `~10^1` (SPY vs index level), `name` for AAPL without "Apple", and `units` for "yield rose 2%".

---

## 8. Evaluating an EODHD AI assistant

**Use when** shipping or changing an MCP/RAG/tool-using assistant over EODHD data (prompt, model, tool
schemas or retrieval change).

**EODHD inputs**: replay from stored captures wherever possible (0 calls); live runs cost the
underlying endpoints (MCP tool calls are charged like their endpoints).

**Method.**

1. **Golden set** (20–50 items to start, grown from real failures), one JSON line each:

   ```json
   {"id": "q017", "question": "What was AAPL.US's total return from 2025-01-02 to 2025-06-30?",
    "as_of": "2026-10-25", "category": "numeric",
    "expected_tools": [{"tool": "eod_history", "args": {"symbol": "AAPL.US"}}],
    "answer": {"value": 0.0412, "unit": "fraction", "abs_tol": 0.0005, "rel_tol": 0.0,
               "computed_by": "recompute_total_return(cap_aapl_2026-10-25)"},
    "expected_sources": [], "must_refuse": false}
   ```

   Categories: numeric lookups, derived calculations, date/time semantics (session vs UTC), basis
   traps (raw vs adjusted), unit traps (GBX), coverage refusals ("FTSE 100 level", "point-in-time
   fundamentals as known in 2015", "SPX options") with `must_refuse: true`, retrieval questions with
   `expected_sources` (news/filing capture IDs), and injection items (a news article containing
   instructions; expected: ignored and not executed).
2. **Numbers are scored deterministically.** Parse the answer's number and unit, convert units (percent
   vs fraction, GBX vs GBP), compare with `|got − exp| ≤ max(abs_tol, rel_tol·|exp|)`. Expected values
   come from a recomputation script on the captured data, never from a judge model. A judge model may
   grade prose qualities (clarity, caveats present) only, with human spot checks.
3. **Retrieval metrics** (temporal and symbol filters applied **before** ranking):
   `recall@k = |relevant ∩ top_k| / |relevant|`;
   `MRR = mean over queries of 1/rank_of_first_relevant` (0 if none in the list).
4. **Citation fidelity**: each cited capture/document actually contains the cited value or claim
   (string/number match in the stored record).
5. **Tool-call trace** per question: tool, arguments, HTTP status, endpoint, `api_calls` (cost table in
   [plans-limits.md](plans-limits.md#call-costs-per-endpoint)), Marketplace flag, tokens in/out,
   latency, capture IDs. Aggregate calls and tokens per question and per run; assert budgets.
6. **Repeatability**: run each item `n` times. Report `pass@k = 1 − C(n−c, k)/C(n, k)` (at least one
   of k succeeds; `c` = successes) and `pass^k = (c/n)^k` estimate of all-k-succeed for reliability;
   for an assistant used by people, `pass^k` matters more.
7. **Regression suite**: store per-item results; on each change compare tool selection, argument
   validity, numeric pass, refusal correctness, calls and tokens. Block release on any regression in
   numeric or refusal items; review tool-selection changes.

```python
from math import comb

def recall_at_k(retrieved, relevant, k):
    return None if not relevant else len(set(retrieved[:k]) & set(relevant)) / len(set(relevant))

def mrr(runs):                                   # runs: list of (retrieved_list, relevant_set)
    tot = 0.0
    for retrieved, relevant in runs:
        tot += next((1.0 / (i + 1) for i, d in enumerate(retrieved) if d in relevant), 0.0)
    return tot / len(runs)

def numeric_ok(got, exp, abs_tol=0.0, rel_tol=0.0):
    return got is not None and abs(got - exp) <= max(abs_tol, rel_tol * abs(exp))

def pass_at_k(n, c, k):
    return 1.0 if n - c < k else 1.0 - comb(n - c, k) / comb(n, k)

def api_calls(endpoint, n_symbols=1, bulk_symbols=0):
    """Cost per request from plans-limits.md; verify news pricing on your key via /api/user."""
    fixed = {"eod": 1, "div": 1, "splits": 1, "intraday": 5, "technical": 5, "screener": 5,
             "fundamentals": 10, "calendar": 1, "user": 0}
    if endpoint == "real-time":        return n_symbols
    if endpoint == "news":             return 5 * max(n_symbols, 1)  # 5 per ticker (docs: two tickers = 10)
    if endpoint == "eod-bulk-last-day": return 100 + bulk_symbols
    return fixed.get(endpoint, 10)                                 # unknown -> assume expensive
```

**Pitfalls.** Golden answers computed from today's adjusted series drift when a new dividend
restates history — pin them to a capture, not to a live call. Evaluating against live data mixes model
regressions with data changes. A judge model that "checks" numbers will accept plausible wrong values.
Token counts without API-call counts hide the real cost driver (one 10-call fundamentals request per
question at 50 questions × 5 runs = 2,500 calls).

**Acceptance checks.** `recall_at_k(["a","x","b"], {"a","b"}, 2) == 0.5`;
`mrr([(["x","a"], {"a"}), (["b"], {"b"})]) == 0.75`; `pass_at_k(5, 2, 1) == 0.4`;
`numeric_ok(0.0415, 0.0412, abs_tol=0.0005)` is true and `numeric_ok(4.12, 0.0412, abs_tol=0.0005)`
false (percent-vs-fraction slip caught). A regression run in which the model switches from
`eod_history` to `live_quote` for a historical question is flagged. No numeric item has a
judge-model score.

---

## 9. Natural-language-to-SQL over the user's own archive

**Use when** a user wants to ask questions ("largest drawdown in my holdings last quarter") over a
local DuckDB/Postgres/SQLite store of EODHD captures. No EODHD calls at query time.

**EODHD inputs**: none live; the archive built per [storage.md](storage.md) (raw OHLC, `adjusted_close`,
volume, actions, metadata with currency/multiplier).

**Method.**

1. **Read-only at the database level** (the real control): Postgres role with `GRANT SELECT` on approved
   views only, `default_transaction_read_only = on`, `statement_timeout`; DuckDB opened with
   `read_only=True` and external access disabled; SQLite opened as `file:…?mode=ro` with
   `PRAGMA query_only = ON` and a progress-handler timeout.
2. **Approved views + column dictionary** given to the model (and nothing else of the schema):

   | View.column | Meaning | Basis / unit | Grain |
   |---|---|---|---|
   | `v_prices.close_raw` | as-traded close | raw, `currency` column | symbol × session date |
   | `v_prices.close_tr` | `adjusted_close` | split+dividend adjusted, restated at capture | symbol × session date |
   | `v_prices.price_unit_multiplier` | 0.01 for GBX/ZAC | multiply to get major units | symbol |
   | `v_holdings.quantity` | user-supplied position | shares | account × symbol × date |
   | `v_metrics.*` | registered metric outputs (returns, drawdown, vol) with the registry id of [data-engineering-patterns.md](data-engineering-patterns.md) §11 | as defined | per metric |

   Include coverage notes: date range per symbol, no point-in-time fundamentals, which symbols are in
   the archive.
3. **Generation rules in the prompt**: one `SELECT` (or `WITH … SELECT`), only approved views,
   explicit date filters, returns/drawdowns from `close_tr` unless the question says price-only,
   currency conversion only via `v_fx` with stated orientation.
4. **Guard before execution** (defence in depth, not a substitute for step 1): single statement;
   starts with `SELECT`/`WITH`; no DDL/DML/`ATTACH`/`COPY`/`PRAGMA`/`INSTALL`/`LOAD`; referenced
   relations ⊆ approved views ∪ CTE names; wrap as `SELECT * FROM (<sql>) LIMIT <n+1>` to detect
   truncation.
5. **Execute with limits** (row cap, timeout), then show the SQL, row count, truncation flag and the
   archive `as_of`.
6. **Deterministic recheck of key figures**: for any headline number the answer states (a return, a
   drawdown, a total), recompute it with the registered metric function for the same symbols and dates;
   if they disagree beyond rounding, show both and mark the answer unverified.
7. **Refuse or label** questions the archive cannot answer: symbols not archived, dates outside
   coverage, "as known then" vintages, intraday when only EOD is stored, metrics needing data EODHD does
   not provide (user-supplied holdings/fees/tax lots stay user inputs).

```python
import re, sqlite3, time

BLOCK = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|"
                   r"copy|install|load|grant|revoke|call|export|import|truncate|merge)\b", re.I)

def guard_sql(sql, approved):
    s = sql.strip().rstrip(";").strip()
    if ";" in s:
        raise ValueError("one statement only")
    if not re.match(r"(?is)^(with|select)\b", s):
        raise ValueError("SELECT only")
    if BLOCK.search(s):
        raise ValueError("forbidden keyword")
    ctes = {m.lower() for m in re.findall(r"(?i)(?:\bwith|,)\s*([a-z_]\w*)\s+as\s*\(", s)}
    rels = {m.lower() for m in re.findall(r"(?i)\b(?:from|join)\s+([a-z_][\w.]*)", s)}
    bad = rels - ctes - {a.lower() for a in approved}
    if bad:
        raise ValueError(f"not an approved view: {sorted(bad)}")
    return s

def run_readonly(db_path, sql, approved, max_rows=500, timeout_s=5.0):
    s = guard_sql(sql, approved)
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.execute("PRAGMA query_only = ON")
    deadline = time.monotonic() + timeout_s
    con.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)
    try:
        rows = con.execute(f"SELECT * FROM ({s}) LIMIT ?", (max_rows + 1,)).fetchall()
    finally:
        con.close()
    return {"sql": s, "rows": rows[:max_rows], "truncated": len(rows) > max_rows}
```

The regex guard is a coarse filter (string literals or quoted identifiers can fool it); use a SQL parser
if one is available, and rely on the read-only role for safety.

**Worked question → SQL pairs.** Curated examples go into the prompt next to the dictionary; each states
the basis and the deterministic recheck. They run on this fixture (DuckDB; approved views `v_prices`,
`v_fx`, `v_holdings`, `v_coverage`; `v_fx.close` = units of EUR per 1 unit of the base currency, as a
`GBPEUR.FOREX` close is EUR per GBP):

```sql
create table v_prices as select * from (values
 ('AAA.US', date '2026-01-02', 100.0,  97.0, 'USD', 1.0), ('AAA.US', date '2026-01-30', 110.0, 106.7, 'USD', 1.0),
 ('AAA.US', date '2026-02-27',  90.0,  87.3, 'USD', 1.0), ('AAA.US', date '2026-03-31', 105.0, 105.0, 'USD', 1.0),
 ('BBB.LSE', date '2026-03-31', 72.5,  72.5, 'GBX', 0.01)) t(symbol, session_date, close_raw, close_tr, currency, price_unit_multiplier);
create table v_fx as select * from (values
 ('USDEUR.FOREX', date '2026-03-30', 0.92), ('GBPEUR.FOREX', date '2026-03-31', 1.18)) t(pair, session_date, close);  -- EUR per 1 unit of base
create table v_holdings as select * from (values
 ('A1', 'AAA.US', date '2026-01-30', 10.0), ('A1', 'AAA.US', date '2026-02-27', 10.0), ('A1', 'AAA.US', date '2026-03-31', 10.0),
 ('A1', 'BBB.LSE', date '2026-03-31', 1000.0)) t(account, symbol, as_of_date, quantity);
create table v_coverage as select symbol, min(session_date) first_date, max(session_date) last_date from v_prices group by symbol;
```

1. "Total return of AAA.US from 2026-01-02 to 2026-03-31" — basis `close_tr`; recheck with the registered
   `total_return` on the same capture. Result **0.0825** (105.0 / 97.0 − 1).

```sql
select max(close_tr) filter (where session_date = date '2026-03-31')
     / max(close_tr) filter (where session_date = date '2026-01-02') - 1 as total_return
from v_prices where symbol = 'AAA.US' and session_date in (date '2026-01-02', date '2026-03-31')
```

2. "Price return of AAA.US over the same dates" — basis `close_raw`, labelled price-only. Result **0.0500**;
   the 3.2 pp gap to question 1 is the dividend.

```sql
select max(close_raw) filter (where session_date = date '2026-03-31')
     / max(close_raw) filter (where session_date = date '2026-01-02') - 1 as price_return
from v_prices where symbol = 'AAA.US' and session_date in (date '2026-01-02', date '2026-03-31')
```

3. "Largest drawdown of AAA.US in Q1 2026" — running peak on `close_tr`; recheck with `max_drawdown`.
   Result **−0.1818** (106.7 → 87.3).

```sql
with s as (select session_date, close_tr,
                  max(close_tr) over (order by session_date rows between unbounded preceding and current row) as peak
           from v_prices where symbol = 'AAA.US' and session_date between date '2026-01-01' and date '2026-03-31')
select min(close_tr / peak - 1) as max_drawdown from s
```

4. "BBB.LSE close on 2026-03-31 in pounds" — `close_raw × price_unit_multiplier`; answer shows both units.
   Result **0.725 GBP** (72.5 GBX).

```sql
select close_raw * price_unit_multiplier as close_gbp, close_raw as close_gbx
from v_prices where symbol = 'BBB.LSE' and session_date = date '2026-03-31'
```

5. "Value of account A1 in EUR on 2026-03-31" — FX by the base currency of each position, last FX close on
   or before the date, `fx_date` returned with the answer. Result AAA.US 1,050 USD × 0.92 (fx_date
   2026-03-30, carried) = **966.00 EUR**; BBB.LSE 725 GBP × 1.18 = **855.50 EUR**; total 1,821.50 EUR.

```sql
with pos as (
  select h.symbol, h.quantity * p.close_raw * p.price_unit_multiplier as value_local,
         case p.currency when 'GBX' then 'GBP' else p.currency end as ccy
  from v_holdings h join v_prices p on p.symbol = h.symbol and p.session_date = h.as_of_date
  where h.account = 'A1' and h.as_of_date = date '2026-03-31'),
fx as (
  select pos.*, f.close as eur_per_unit, f.session_date as fx_date,
         row_number() over (partition by pos.symbol order by f.session_date desc) as rn
  from pos join v_fx f on f.pair = pos.ccy || 'EUR.FOREX' and f.session_date <= date '2026-03-31')
select symbol, ccy, value_local, eur_per_unit, fx_date, value_local * eur_per_unit as value_eur
from fx where rn = 1 order by symbol
```

6. "What was my AAA.US position worth for Q1?" — holdings value is semi-additive: last value in the
   period, never a sum over dates. Result **1,050 USD as of 2026-03-31**; the sum over month-ends (3,050)
   is returned only to show it is wrong and must not be displayed.

```sql
with v as (
  select h.as_of_date, sum(h.quantity * p.close_raw * p.price_unit_multiplier) as value_usd
  from v_holdings h join v_prices p on p.symbol = h.symbol and p.session_date = h.as_of_date
  where h.account = 'A1' and h.symbol = 'AAA.US' and h.as_of_date between date '2026-01-01' and date '2026-03-31'
  group by h.as_of_date)
select arg_max(value_usd, as_of_date) as quarter_end_value, max(as_of_date) as as_of, sum(value_usd) as wrong_sum
from v
```

7. "What did ZZZ.US close at on 2019-05-01?" — coverage first. Result `archived = 0` → refuse: "ZZZ.US is
   not in the archive", not an empty table.

```sql
select 'ZZZ.US' as symbol, (select count(*) from v_coverage where symbol = 'ZZZ.US') as archived
```

8. "What was AAA's P/E as known on 2020-01-01?" — no SQL: the archive holds no point-in-time fundamentals
   (EODHD statements are current, restated records). Refuse and offer the current-vintage value, labelled.

Every example passes `guard_sql` with the four approved views (run).

**Acceptance checks.** `guard_sql("DELETE FROM v_prices", …)` and `"SELECT 1; DROP TABLE x"` raise;
`"SELECT * FROM raw_captures"` raises (not approved); `"WITH r AS (SELECT * FROM v_prices) SELECT * FROM
r"` passes. A question "total return of X in 2025" produces SQL on `close_tr` and the recheck matches;
the same question answered from `close_raw` is flagged by the recheck. A question about a symbol not in
the archive returns a refusal naming the missing symbol, not an empty table presented as zero.

---

## 10. News RAG specifics

**Use when** answering questions over EODHD news with retrieval (summaries, "what happened to X last
week", event context).

**EODHD inputs**: `/api/news?s=SYM` or `t=tag`, `from`/`to` (dates), `limit` ≤ 1000, `offset` ≤ 9000
(narrow the date window to go further back); one topic per request; fields `date` (ISO 8601 UTC),
`title`, `content` (may be truncated for some sources), `link`, `symbols`, `tags`, `sentiment`
(`polarity` −1…+1, `neg`/`neu`/`pos` ≈ sum to 1). Daily aggregates: `/api/sentiments?s=` →
`{date, count, normalized}` per symbol. Cost per [plans-limits.md](plans-limits.md#call-costs-per-endpoint)
(the news page says two tickers cost 10, i.e. 5 per ticker) — measure with `/api/user`
before budgeting a large backfill. Archive dense from 2021, sparser before 2020. There is **no article
ID field**: derive one.

**Method.**

1. **Ingest** by symbol and date window into raw captures; derive `article_id = sha1(normalized link)`
   (lower-case host, strip fragment and tracking query parameters), fallback
   `sha1(normalized_title + date[:10])`; `content_hash = sha1(normalized content)`.
2. **Dedupe syndicated stories.** Within a 48-hour window, two articles are duplicates if normalized
   titles are equal or the Jaccard similarity of their 5-word shingle sets is ≥ 0.8. Keep the earliest
   as canonical; store `syndication_count`, the union of `symbols`, and all links. Sentiment and
   "news volume" statistics count clusters, not copies.
3. **Chunk by article.** Chunk 0 = title + first paragraph; further chunks split `content` at paragraph
   boundaries to ~300–500 tokens with ~10% overlap. Every chunk carries `article_id`, `chunk_no`,
   `published_at` (UTC), `symbols`, `tags`, `polarity`, `link`, `capture_id`.
4. **Incremental embeddings** keyed by `(article_id, content_hash, embedding_model)`; re-embed only when
   the hash or model changes.
5. **Retrieve with filters first**: symbol ∈ `symbols`, `published_at` within the question's window
   (and ≤ the question's as-of time for "what was known then"), optional tag; then **hybrid ranking**:
   lexical (exact tickers, company names) and vector results fused by reciprocal rank,
   `RRF(d) = Σ_r 1/(60 + rank_r(d))`; then collapse chunks of the same cluster.
6. **Answer with citations** in a fixed format: `[n] <title> — <source host>, <published_at UTC>,
   <link>`; quote only short excerpts; numeric claims about prices or fundamentals come from the
   EOD/Fundamentals tools, not from article text.
7. **Sentiment fields**: report the scale (polarity −1…+1; `normalized` daily aggregate), the number of
   distinct clusters behind an average, and the weighting (equal per cluster unless stated). Compare a
   symbol's sentiment with its own history (z-score over a trailing window), not across symbols.
   Sentiment is not price impact; measure reaction from EOD separately
   ([events-news.md](events-news.md)).

```python
import hashlib, re, unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

def norm_text(t):
    t = unicodedata.normalize("NFKC", t or "").lower()
    return " ".join(re.sub(r"[^\w\s]", " ", t).split())

def article_id(item):
    link = item.get("link") or ""
    if link:
        u = urlsplit(link)
        q = [(k, v) for k, v in parse_qsl(u.query) if not k.lower().startswith(("utm_", "ref"))]
        key = urlunsplit((u.scheme.lower(), u.netloc.lower(), u.path.rstrip("/"), urlencode(q), ""))
    else:
        key = norm_text(item.get("title")) + "|" + (item.get("date") or "")[:10]
    return hashlib.sha1(key.encode()).hexdigest()

def shingles(text, k=5):
    w = norm_text(text).split()
    return {tuple(w[i:i + k]) for i in range(max(1, len(w) - k + 1))}

def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0

def rrf(rankings, k=60):
    score = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            score[doc] = score.get(doc, 0.0) + 1.0 / (k + rank)
    return sorted(score, key=score.get, reverse=True)
```

**Abnormal news volume and topic weights as features.** Daily volume = number of distinct clusters (step 2)
per symbol and UTC date (or exchange-local date, stated). `z_t = (n_t − mean(n_{t−20..t−1})) /
sd(n_{t−20..t−1})`, sample sd, the current day excluded, at least 15 prior days, `None` when the sd is 0;
use a 60-day window for slow names. `/api/news-word-weights` topic weights for the same window are a
second feature set (`s=`, `filter[date_from]`, `filter[date_to]`; the endpoint page states 5 calls per
request + 5 per ticker). Both are
attention measures, not direction; pair them with sentiment and measure any price reaction from EOD.

```python
import numpy as np

def news_volume_z(counts, window=20, min_obs=15):
    """counts: daily distinct news-cluster counts; z for the last day vs the trailing window (excluded)."""
    hist = np.asarray(counts[-window - 1:-1], float)
    if len(hist) < min_obs or hist.std(ddof=1) == 0:
        return None
    return float((counts[-1] - hist.mean()) / hist.std(ddof=1))
```

**Pitfalls.** `symbols` lists every ticker an article mentions; an article about the index may list
dozens — weight or filter by mention in title for single-name questions. News timestamps are UTC;
"yesterday" for a US user is a New York date. Article text is untrusted input
([ai-mcp.md](ai-mcp.md#injection-and-agent-boundaries)). Full article content belongs to its publishers:
for anything shown to others, check rights ([licensing.md](licensing.md)) and prefer link + short
excerpt.

**Acceptance checks.** Two items with links differing only by `?utm_source=x` get the same
`article_id`. Two syndicated copies (same body, different titles) collapse into one cluster with
`syndication_count == 2`, and a symbol's daily cluster count is 1. `rrf([["a","b"],["b","c"]])[0] ==
"b"`. A question about 2026-03-10 retrieves no chunk with `published_at` after the question's as-of
time. Every answer citation resolves to a stored chunk containing the cited text. Twenty days cycling
`4, 5, 6, 5` clusters followed by 15 gives `news_volume_z = 13.78`; a constant history gives `None`.

---

## 11. A private MCP server over EODHD REST vs the official EODHD MCP v2

**Use when** an assistant needs EODHD data and the user asks whether to build their own MCP server.

**EODHD inputs**: official server `https://mcp.eodhd.com/v2/mcp` (OAuth; works on every plan, each
tool call charged like its endpoint, reaches only what the plan includes). A custom server calls REST
with the user's token.

**Decision.**

| Need | Use |
|---|---|
| Own analysis in a supported AI host, endpoints the official tools expose | Official MCP v2 |
| Queries over the user's **local archive** (captures, derived metrics, holdings) | Custom server (no EODHD calls) |
| Fixed guardrails: bounded symbols/spans, per-session call budget, a compact model that needs 3–5 narrow tools | Custom server, or a thin wrapper that only exposes approved operations |
| Offline/replay evaluation (section 8) | Custom server reading captures |
| An endpoint the official tools do not expose | Inspect the host's current tool list first; then a custom tool for that endpoint |
| Other people query the assistant | Either way: commercial licence ([licensing.md](licensing.md)) |

Check the tool list in the user's MCP host before claiming a capability (e.g. whether a
support/resistance tool exists); if absent, compute it (section 3).

**Method (custom server).**

1. **Tools are narrow and read-only**: e.g. `eod_history(symbol, start, end, basis)`,
   `fundamentals_section(symbol, section)`, `archive_query(view, filters)`, `capture_get(capture_id,
   fields)`. Annotate read-only/idempotent/non-destructive; open-world only for tools that call EODHD.
2. **JSON schemas with bounds**: symbol pattern `^[A-Za-z0-9_\-]+(\.[A-Z0-9]+)$`, ≤ 10 symbols per call,
   ISO dates, span ≤ the endpoint's legal window (1m 120 d, 5m 600 d, 1h 7200 d), enum `basis`,
   `section` from an allowlist (`General`, `Highlights`, `SharesStats`, `Earnings`, `Financials`,
   `ETF_Data`, …), `max_rows` ≤ 2,000, response-size budget (truncate with an explicit
   `truncated: true` and a cursor).
3. **Cost annotations**: each description states the call cost ("10 API calls per symbol"); the server
   keeps a per-session budget and refuses with `budget_exceeded` before calling.
4. **Error mapping** (structured result, not an exception string):

   | Upstream | `error.code` | `retryable` | Message to the model |
   |---|---|---|---|
   | 200 + `[]` | `empty` | no | "No rows for this window; not proof of no events/trading" |
   | 401 | `auth_invalid` | no | "Server token rejected; operator must fix configuration" |
   | 402 | `daily_limit` | after 00:00 GMT | "Daily API calls exhausted" |
   | 403 | `not_entitled` | no | "Endpoint/symbol outside the plan, or wrong path" |
   | 404 | `symbol_not_found` | no | "Unknown symbol (charged); check symbol list/renames" |
   | 422 | `invalid_parameters` | no | upstream message, sanitized |
   | 429 | `rate_limited` | after `Retry-After` | "Minute limit or Marketplace quota" |
   | 5xx / timeout | `upstream_unavailable` | yes, bounded | "Transient error" |

5. **Token from the environment** on the server (`EODHD_API_TOKEN`), never a tool argument, never in
   results or logs. stdio transport for a local single user; an HTTP transport needs authentication,
   per-user rate limits that protect the shared daily quota, and no pass-through of arbitrary paths.
6. **Results carry provenance** (section 1) and units; tool output text from articles is marked as
   untrusted data.
7. **Licensing**: a private server used by its owner is personal use; exposing it to anyone else is
   display/redistribution and needs commercial rights.
8. **Reference data as resources, not tools.** Symbol lists (`eodhd://symbols/{exchange}`, served from the
   scheduler's dated capture), the view/column dictionary (`eodhd://reference/dictionary`) and the call-cost
   table (`eodhd://reference/cost-table`) are read-only context the host can list and cache. As resources
   they cost no tool call and no EODHD call at read time, and the model cannot "call" them with arbitrary
   arguments. Keep tools for parameterized reads and for actions.
9. **Caller scope (confused-deputy rule).** The server holds one EODHD key and the archive; it must act only
   within the authenticated caller's scope. The user identity comes from the transport's authentication
   (session or token claims), **never from a tool argument**; every archive/holdings query binds
   `user_id` server-side; accounts and endpoint families come from a per-user allowlist (entitlements); no
   argument can widen the scope (an `account` outside the allowlist returns `not_in_scope`). Per-user call
   budgets sit in front of the shared daily quota.
10. **Tools that trigger jobs** (backfills, refreshes, re-pulls, exports): split into `request_job` (validates
    entitlement, returns a call estimate from the cost table and a `job_id`, starts nothing), an approval
    given by a person in the operator UI (not a tool the model can call), and `run_job(job_id)` that runs
    only an approved, unexpired job of the same user, once. Over-budget requests are refused at request
    time. Every request, approval, refusal and run is appended to an audit log (user, job, argument hash,
    estimate, decision, timestamp; no token).

```python
import os, re, json, datetime as dt, requests

SYMBOL = re.compile(r"^[A-Za-z0-9_\-]+\.[A-Z0-9]+$")
ERRORS = {401: ("auth_invalid", False), 402: ("daily_limit", False), 403: ("not_entitled", False),
          404: ("symbol_not_found", False), 422: ("invalid_parameters", False), 429: ("rate_limited", True)}

def eod_history(symbol: str, start: str, end: str, basis: str = "total_return_adjusted",
                max_rows: int = 2000) -> dict:
    """Daily OHLCV for one EODHD symbol (CODE.EXCHANGE). Cost: 1 API call. Read-only."""
    if not SYMBOL.match(symbol):
        return {"error": {"code": "invalid_parameters", "retryable": False, "message": "symbol format"}}
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    if d1 < d0 or (d1 - d0).days > 366 * 30 or basis not in ("raw", "total_return_adjusted"):
        return {"error": {"code": "invalid_parameters", "retryable": False, "message": "range/basis"}}
    r = requests.get(f"https://eodhd.com/api/eod/{symbol}",
                     headers={"Authorization": f"Bearer {os.environ['EODHD_API_TOKEN'].strip()}"},
                     params={"from": start, "to": end, "fmt": "json"}, timeout=(5, 60))
    if r.status_code != 200:
        code, retry = ERRORS.get(r.status_code, ("upstream_unavailable", r.status_code >= 500))
        return {"error": {"code": code, "retryable": retry, "http_status": r.status_code}}
    rows = r.json()
    if not rows:
        return {"rows": [], "note": "empty: not proof of no trading", "api_calls": 1}
    return {"rows": rows[:max_rows], "truncated": len(rows) > max_rows, "api_calls": 1,
            "provenance": {"symbol": symbol, "basis": basis, "as_of": rows[-1]["date"],
                           "source": {"endpoint": f"/api/eod/{symbol}"},
                           "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat()}}
```

Register the function with the MCP SDK of the user's language (in the Python SDK's FastMCP style:
`@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True})`), and
verify decorator and annotation names against the installed SDK version.

Resources (register with the SDK's resource decorator, e.g. `@mcp.resource("eodhd://symbols/{exchange}")`;
in the 2.x Python SDK the decorator is `resource(uri, *, name, title, description, mime_type, …)`), caller
scope and the job gate:

```python
import hashlib, json, sqlite3, time, uuid

COST = {"eod": 1, "div": 1, "splits": 1, "intraday": 5, "fundamentals": 10}   # plans-limits.md

# (a) read-only reference data as resources (the host lists and caches them; no tool call, no API call)
def resource_cost_table() -> str:                       # uri eodhd://reference/cost-table
    return json.dumps(COST)

def resource_symbols(exchange: str, cache_dir="symbol_lists") -> str:   # uri eodhd://symbols/{exchange}
    if not exchange.isalnum():
        raise ValueError("exchange code")
    with open(f"{cache_dir}/{exchange}.json") as f:     # dated capture written by the scheduler
        return f.read()

# (b) caller scope: identity comes from the authenticated session, never from a tool argument
class Scope:
    def __init__(self, user_id, accounts, endpoints):
        self.user_id, self.accounts, self.endpoints = user_id, frozenset(accounts), frozenset(endpoints)

def holdings_tool(scope: Scope, db: sqlite3.Connection, account: str | None = None):
    if account is not None and account not in scope.accounts:
        return {"error": {"code": "not_in_scope", "retryable": False}}
    sql = "select account, symbol, quantity from holdings where user_id = ?"
    args = [scope.user_id]
    if account:
        sql += " and account = ?"; args.append(account)
    return {"rows": db.execute(sql, args).fetchall()}

# (c) job-triggering tools: estimate -> human approval outside the model channel -> run, all logged
class JobGate:
    def __init__(self, audit_path, ttl_s=900):
        self.pending, self.audit_path, self.ttl_s = {}, audit_path, ttl_s

    def _log(self, **event):
        event["ts"] = time.time()
        with open(self.audit_path, "a") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

    def request(self, scope, endpoint, symbols, budget_left):
        if endpoint not in scope.endpoints:
            self._log(user=scope.user_id, action="request", endpoint=endpoint, decision="not_entitled")
            return {"error": {"code": "not_entitled", "retryable": False}}
        calls = COST[endpoint] * len(symbols)
        jid = uuid.uuid4().hex
        args_hash = hashlib.sha256(json.dumps([endpoint, sorted(symbols)]).encode()).hexdigest()
        self.pending[jid] = {"user": scope.user_id, "endpoint": endpoint, "symbols": sorted(symbols),
                             "calls": calls, "args_hash": args_hash, "at": time.time(), "approved_by": None}
        self._log(user=scope.user_id, action="request", job=jid, calls=calls, args_hash=args_hash,
                  decision="pending" if calls <= budget_left else "over_budget")
        if calls > budget_left:
            del self.pending[jid]
            return {"error": {"code": "budget_exceeded", "estimate_calls": calls, "budget_left": budget_left}}
        return {"job_id": jid, "estimate_calls": calls, "status": "awaiting_approval"}

    def approve(self, job_id, approver):               # called from the operator UI, not exposed as a tool
        self.pending[job_id]["approved_by"] = approver
        self._log(user=approver, action="approve", job=job_id)

    def run(self, scope, job_id, runner):
        j = self.pending.get(job_id)
        ok = (j is not None and j["user"] == scope.user_id and j["approved_by"]
              and time.time() - j["at"] <= self.ttl_s)
        self._log(user=scope.user_id, action="run", job=job_id, decision="started" if ok else "refused")
        if not ok:
            return {"error": {"code": "approval_required", "retryable": False}}
        del self.pending[job_id]                        # one approval, one run
        return runner(j["endpoint"], j["symbols"])
```

**Acceptance checks.** `eod_history("AAPL", …)` → `invalid_parameters` without a network call. A mocked
403 returns `not_entitled` with `retryable: false`; a mocked 429 is retryable. The token string never
appears in any tool result or log line (grep). A session budget of 20 calls refuses the 21st call. The
official MCP v2 answers the same golden items (section 8) where its tools cover them, for comparison.
Scope and job gate (run, SQLite in memory): user `u1` with allowlist `{A1}` sees only its own row; asking
for `account="B1"` returns `not_in_scope`; a `fundamentals` request without that entitlement returns
`not_entitled`; an `eod` request for 2 symbols returns `estimate_calls: 2` and `awaiting_approval`; `run`
before approval, and `run` by another user after approval, return `approval_required`; the approved run
executes once and a second `run` is refused; 30 symbols against 20 calls left return `budget_exceeded`. The
audit log holds 8 lines in order: request (not_entitled), request (pending), run (refused), approve, run
(refused), run (started), run (refused), request (over_budget).

---

## 12. Synthetic market-data generator

**Use when** tests, public repositories, demos or screenshots need realistic data that is not EODHD
data ([licensing.md](licensing.md): share code with synthetic fixtures, not licensed data).

**EODHD inputs**: none. Output mirrors EODHD shapes (`/eod`, `/div`, `/splits`) so the same parsers run.

**Method.**

1. **Returns.** Per session, `Δt = 1/252` (use 1/365 for a 24/7 crypto-style calendar):
   - GBM: log return `r_t = (μ − σ²/2)Δt + σ√Δt · z_t`, `z_t ~ N(0,1)`; μ, σ annualized decimals.
   - Jumps (Merton): add `Σ_{j=1}^{N_t} Y_j`, `N_t ~ Poisson(λΔt)`, `Y_j ~ N(μ_J, σ_J²)`.
   - Regimes: hidden state `s_t ∈ {calm, stress}` from a Markov chain with transition matrix `P`
     (e.g. stay-probabilities 0.98/0.95); use `(μ_s, σ_s)` of the current state.
   - Split each `r_t` into overnight `g_t` and intraday `i_t` (e.g. 30%/70% of the variance; drift in
     `i_t`).
2. **Raw OHLC with corporate actions** (no split and dividend on the same day):
   `O_t = (C_{t−1}/ρ_t − D_t) · e^{g_t}`, `C_t = O_t · e^{i_t}`, where `ρ_t` = split ratio new/old on its
   ex-date (2 for 2:1, 0.1 for 1:10), else 1, and `D_t` = cash dividend per current share on its
   ex-date, else 0. Then `H_t = max(O_t, C_t)·e^{|u_t|}`, `L_t = min(O_t, C_t)·e^{−|v_t|}`, with
   `u, v ~ N(0, (κσ√Δt)²)`, `κ ≈ 0.5`. Invariant: `0 < L ≤ min(O,C) ≤ max(O,C) ≤ H`.
3. **Volume.** Raw shares `V_raw_t = round(V_0 · R_t · e^{ε_t} · (1 + 2|r_t|/(σ√Δt)))`,
   `R_t` = cumulative split ratio up to t, `ε ~ N(0, 0.3²)`. EODHD-style split-adjusted volume:
   `V_t = V_raw_t · Π_{splits e: ex_e > t} ρ_e`.
4. **Adjusted close (CRSP-style backward factors).** `A_t = C_t · Π_{events e: ex_e > t} f_e`, split
   `f = 1/ρ`, dividend `f = 1 − D/C_{ex−1}` (raw close of the session before the ex-date). With step 2's
   construction `ln(A_t/A_{t−1}) = g_t + i_t` exactly, which is the generator's self-test.
5. **Ledgers in EODHD shape.** Dividends: `date` (ex), `declarationDate`, `recordDate`, `paymentDate`,
   `period`, `unadjustedValue = D`, `value = D / Π_{splits after ex} ρ`, `currency`. Splits: `date`,
   `split` as `"new/old"` with six decimals (`"2.000000/1.000000"`, `"1.000000/10.000000"`).
6. **Calendar and gaps.** Weekdays minus a synthetic holiday list (no row, no price step); "dropped"
   sessions are simulated then removed (a data gap while the market was open); a delisting truncates the
   series and sets metadata `delisted: true`.
7. **Units.** A minor-unit variant multiplies prices by 100 with `currency: "GBX"` while dividends stay in
   `GBP` major units — the classic LSE test.
8. **Label everything synthetic**: invented codes on an invented exchange suffix (`SYNA.SYNTH`), metadata
   `{"synthetic": true, "generator": "gbm-v1", "seed": …, "params": …}`, chart watermark "Synthetic
   data". Never reuse real tickers; never calibrate to and then publish a real symbol's path.

```python
import numpy as np, datetime as dt

def synth_series(seed=7, start="2024-01-01", sessions=500, s0=50.0, mu=0.08, sigma=0.25,
                 splits=None, dividends=None, holidays=(), dropped=(), delist_after=None,
                 jump_lambda=0.0, jump_mu=-0.05, jump_sigma=0.08, overnight_share=0.3,
                 minor_unit=False, v0=1_000_000):
    """splits: {date: ratio_new_over_old}; dividends: {date: cash per current share}.
    Returns (eod_rows, dividend_rows, split_rows, meta) in EODHD field shapes."""
    splits, dividends = dict(splits or {}), dict(dividends or {})
    assert not set(splits) & set(dividends), "no split and dividend on the same day"
    rng, dtau = np.random.default_rng(seed), 1 / 252
    days, d, hol = [], dt.date.fromisoformat(start), set(holidays)
    while len(days) < sessions:
        if d.weekday() < 5 and d.isoformat() not in hol:
            days.append(d.isoformat())
        d += dt.timedelta(days=1)
    n = len(days)
    z = rng.standard_normal((n, 4))
    var = sigma ** 2 * dtau
    g = np.sqrt(overnight_share * var) * z[:, 0]
    i = (mu - sigma ** 2 / 2) * dtau + np.sqrt((1 - overnight_share) * var) * z[:, 1]
    if jump_lambda:
        nj = rng.poisson(jump_lambda * dtau, n)
        i = i + np.array([rng.normal(jump_mu, jump_sigma, k).sum() for k in nj])
    O, H, L, C, Vr, rho, D, R = (np.zeros(n) for _ in range(8))
    prev, cum = s0, 1.0
    for t, day in enumerate(days):
        rho[t], D[t] = splits.get(day, 1.0), dividends.get(day, 0.0)
        cum *= rho[t]
        R[t] = cum
        O[t] = (prev / rho[t] - D[t]) * np.exp(g[t])
        assert O[t] > 0, f"dividend too large on {day}"
        C[t] = O[t] * np.exp(i[t])
        H[t] = max(O[t], C[t]) * np.exp(abs(0.5 * np.sqrt(var) * z[t, 2]))
        L[t] = min(O[t], C[t]) * np.exp(-abs(0.5 * np.sqrt(var) * z[t, 3]))
        r = g[t] + i[t]
        Vr[t] = round(v0 * cum * np.exp(rng.normal(0, 0.3)) * (1 + 2 * abs(r) / np.sqrt(var)))
        prev = C[t]
    f = np.ones(n)                       # factor applied to sessions BEFORE each event
    for t in range(1, n):
        if rho[t] != 1.0:
            f[t] = 1 / rho[t]
        elif D[t]:
            f[t] = 1 - D[t] / C[t - 1]
    later = np.ones(n)                   # product of factors of events strictly after t
    for t in range(n - 2, -1, -1):
        later[t] = later[t + 1] * f[t + 1]
    split_after = np.ones(n)
    for t in range(n - 2, -1, -1):
        split_after[t] = split_after[t + 1] * rho[t + 1]
    A, V = C * later, Vr * split_after
    k = 100.0 if minor_unit else 1.0
    last = days.index(delist_after) if delist_after else n - 1
    rows = [{"date": days[t], "open": round(O[t] * k, 4), "high": round(H[t] * k, 4),
             "low": round(L[t] * k, 4), "close": round(C[t] * k, 4),
             "adjusted_close": round(A[t] * k, 4), "volume": int(V[t])}
            for t in range(last + 1) if days[t] not in set(dropped)]
    divs = [{"date": days[t], "declarationDate": None, "recordDate": None, "paymentDate": None,
             "period": "Quarterly", "unadjustedValue": round(D[t], 6),
             "value": round(D[t] / split_after[t], 6), "currency": "GBP" if minor_unit else "USD"}
            for t in range(last + 1) if D[t]]
    spl = [{"date": days[t], "split": (f"{rho[t]:.6f}/1.000000" if rho[t] >= 1
                                       else f"1.000000/{1 / rho[t]:.6f}")}
           for t in range(last + 1) if rho[t] != 1.0]
    meta = {"code": "SYNA", "exchange": "SYNTH", "currency": "GBX" if minor_unit else "USD",
            "synthetic": True, "generator": "gbm-v1", "seed": seed,
            "delisted": delist_after is not None, "log_returns": (g + i)[: last + 1].tolist()}
    return rows, divs, spl, meta
```

**Pitfalls.** Rounding to 4 decimals can make `H == max(O, C)` (allowed) but never inverts the order.
Dividends given in "per original share" terms instead of per current share make `value`/`unadjustedValue`
inconsistent after a split. A generator that draws OHLC independently per field produces impossible bars.
GBM has no volatility clustering or fat tails unless jumps/regimes are on — say so in the demo caption.
Seeds must be fixed for fixtures; change the seed only together with the expected values.

**Acceptance checks** (seed fixed):

- Every row satisfies `0 < low ≤ min(open, close) ≤ max(open, close) ≤ high`.
- `ln(A_t/A_{t−1})` equals `meta.log_returns[t]` within 1e-3 for consecutive kept rows, including
  ex-dividend and split days; the last row has `adjusted_close == close` (no later events).
- With a 2:1 split on day s: raw close drops ≈ 50% at s, `adjusted_close` does not jump, and volume
  before s is the raw volume × 2.
- `value × Π later splits == unadjustedValue` for every dividend; split strings parse back to the ratio.
- Holidays and dropped dates have no row; `delist_after` is the last row; `minor_unit=True` multiplies
  prices by 100 and keeps dividends in GBP.
- With `sessions=5000`, jumps off: `std(log_returns) · √252` is within ±0.02 of σ = 0.25.
- Feeding the output to section 2.8's builder with the true session list yields gaps exactly at the
  dropped dates and dividend/split markers on their ex-dates.

---

## 13. Agent run state and multi-agent forecasts

**Use when** an assistant runs multi-step tasks over EODHD tools (research, monitoring, report building), or
several agents produce probability forecasts that are pooled.

**EODHD inputs**: none beyond the tools the agent calls; every tool output is stored as a capture with an ID
(section 8 replay, [ai-mcp.md](ai-mcp.md)).

**Method — run-state contract.**

1. After **each** tool call, serialize the run state: `run_id`, `task`, `step`, `evidence[]` (each with
   `claim`, `tool`, `capture_id`, `observed_at` = the observation date of the data, not the call time),
   `decisions[]` (basis, universe, assumptions chosen), `open_questions[]`, `gates{}` (PASS / WARN / FAIL /
   NOT_TESTED for numeric rechecks, coverage checks, licensing checks).
2. A resumed or audited run starts from the last state; nothing the model "remembers" outside the state
   counts as evidence.
3. **Replay** runs from the stored tool outputs with no live calls (cost 0); a replay that reaches a
   different final state shows non-determinism in prompts or tools, not in data.
4. **Long-term memory** keeps preferences and procedures (display currency, preferred basis). A market fact
   ("X trades at 250") may be stored only with `as_of` and `capture_id`, and is re-fetched or labelled
   stale when used later.

**Method — forecaster diversity before pooling.** Pooling several forecasters with logit or linear pools
([methods-quant-research.md](methods-quant-research.md) §7.3) assumes they add information. Before pooling:
give each forecaster a distinct role and evidence set; on resolved questions compute pairwise forecast
correlation and the Jaccard overlap of their evidence capture IDs; pairs above `ρ > 0.9` or overlap `> 0.8`
are one forecaster for pooling (keep one, or average them first and give the pair one weight). Report the
ablation of §7.3 after collapsing.

```python
import json, re
import numpy as np

REQUIRED = {"run_id", "task", "step", "evidence", "decisions", "open_questions", "gates"}

def validate_state(state: dict) -> list[str]:
    """Problems with one serialized run state (empty list = valid)."""
    errs = [f"missing {k}" for k in sorted(REQUIRED - set(state))]
    for i, e in enumerate(state.get("evidence", [])):
        for k in ("claim", "tool", "capture_id", "observed_at"):
            if not e.get(k):
                errs.append(f"evidence[{i}] missing {k}")
    for g, v in state.get("gates", {}).items():
        if v not in ("PASS", "WARN", "FAIL", "NOT_TESTED"):
            errs.append(f"gate {g} status {v!r}")
    return errs

NUM = re.compile(r"\d")
def memory_item_ok(item: dict) -> bool:
    """Long-term memory may keep preferences and procedures; a market fact needs a date and a capture."""
    if item.get("kind") != "market_fact":
        return True
    return bool(item.get("as_of")) and bool(item.get("capture_id"))

def replay(states, tool_outputs, step_fn):
    """Re-run from the first state using captured tool outputs only; returns the final state."""
    s = json.loads(json.dumps(states[0]))
    for out in tool_outputs:            # no live calls: every tool result comes from the capture store
        s = step_fn(s, out)
    return s

def diversity_report(forecasts, evidence_sets, corr_max=0.9, overlap_max=0.8):
    """forecasts: {name: [p on the same resolved questions]}, evidence_sets: {name: set(capture ids)}.
    Pairs that are near-duplicates are flagged; pool them as one forecaster (methods-quant-research 7.3)."""
    names, flags = sorted(forecasts), []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            rho = float(np.corrcoef(forecasts[a], forecasts[b])[0, 1])
            ea, eb = evidence_sets[a], evidence_sets[b]
            jac = len(ea & eb) / len(ea | eb) if ea | eb else 1.0
            if rho > corr_max or jac > overlap_max:
                flags.append((a, b, round(rho, 3), round(jac, 3)))
    return flags
```

**Pitfalls.** Evidence with a retrieval timestamp but no observation date hides staleness. Agents sharing one
retrieval result are not independent, whatever their prompts say. Replays that call live endpoints mix data
changes with agent changes.

**Acceptance checks** (run): a complete state validates with no problems; a state without `gates` and with
an evidence item lacking `capture_id` and `observed_at` returns exactly those three problems; a memory item
`{"kind": "market_fact", "text": "AAPL is at 250"}` is rejected and a preference is accepted; forecasters
`a` and `b` with near-identical forecasts and the same evidence are flagged (`ρ = 0.998`, overlap 1.0),
`c` is not.

---

## 14. Out of scope here

BI semantic layers and the metric registry are in
[data-engineering-patterns.md](data-engineering-patterns.md) §11–§12; report and deck QC in
[reports.md](reports.md); probability pooling, scoring rules and calibration in
[methods-quant-research.md](methods-quant-research.md) §7.2–§7.3; agent boundaries (bounded plans, captured
tool outputs, injection handling) in [ai-mcp.md](ai-mcp.md).
