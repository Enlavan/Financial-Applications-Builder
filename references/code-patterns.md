# Code patterns for EODHD integrations

Copy-adaptable Python (3.10+, `requests`, optional `pandas`/`websockets`). They encode the rules in
[plans-limits.md](plans-limits.md) and [coverage-notes.md](coverage-notes.md). Adapt names to the user's
stack; keep the behaviours. For one-off bounded captures with raw evidence use
`scripts/eodhd_request.py` instead. Run against the user's own key only when authorized; use `demo` for
AAPL.US/MSFT.US/TSLA.US-style smoke tests.

## Contents

1. Cost-aware client (limiter, errors, host routing)
2. EOD history with adjusted OHLC
3. Daily bulk update with date check
4. Intraday backfill in legal windows
5. Universe: active + delisted symbol lists
6. Unit normalization (GBX, ZAC)
7. Fundamentals sections
8. Screener partitioning
9. ID mapping pagination
10. Exchange calendar and freshness
11. WebSocket recorder
12. Marketplace options by expiry
13. Notebook research (Jupyter)
14. Outbound webhooks for alerts and events

## 1. Cost-aware client

```python
import os, time, threading, requests

COST = {  # API calls per request (public limits page, 2026-10)
    "eod": 1, "div": 1, "splits": 1, "real-time": 1, "search": 1, "exchange-symbol-list": 1,
    "exchanges-list": 1, "id-mapping": 1, "calendar": 1, "exchange-details": 1, "symbol-change-history": 1,
    "intraday": 5, "technical": 5, "screener": 5, "news": 5,
    "fundamentals": 10, "insider-transactions": 10, "macro-indicator": 10, "historical-market-cap": 10,
    "sec-filings": 10, "eod-bulk-last-day": 100,
}
HOSTS = {"MI": "https://cboe.eodhd.com/api"}       # Milan beta host
DEFAULT_HOST = "https://eodhd.com/api"

class EODHDError(Exception): ...
class NotEntitled(EODHDError): ...      # 403: plan/ticker outside entitlement or wrong path
class DailyLimit(EODHDError): ...       # 402: daily calls exhausted -> stop, resume after 00:00 GMT
class BadToken(EODHDError): ...         # 401

class Client:
    def __init__(self, token=None, per_minute=900, daily_budget=None):
        self.token = (token or os.environ["EODHD_API_TOKEN"]).strip()   # strip stray whitespace/newlines
        self.s = requests.Session()
        self.per_minute, self.sent = per_minute, []                       # one limiter per token
        self.daily_budget, self.spent = daily_budget, 0
        self.lock = threading.Lock()

    def _pace(self, cost):
        with self.lock:
            if self.daily_budget is not None and self.spent + cost > self.daily_budget:
                raise DailyLimit("local budget reached")
            now = time.monotonic()
            self.sent = [t for t in self.sent if now - t < 60]
            if len(self.sent) >= self.per_minute:
                time.sleep(60 - (now - self.sent[0]))
            self.sent.append(time.monotonic()); self.spent += cost

    def get(self, path, symbol_exchange=None, cost=None, **params):
        family = path.strip("/").split("/")[0]
        cost = cost if cost is not None else COST.get(family, 10)          # unknown -> assume expensive
        base = HOSTS.get(symbol_exchange, DEFAULT_HOST)
        params.setdefault("fmt", "json")
        for attempt in range(5):
            self._pace(cost)
            r = self.s.get(f"{base}/{path.lstrip('/')}", params={**params, "api_token": self.token},
                           timeout=(5, 60))
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:                                       # minute limit / Marketplace quota
                time.sleep(min(float(r.headers.get("Retry-After", 2 ** attempt)), 60)); continue
            if r.status_code >= 500:
                time.sleep(min(2 ** attempt, 30)); continue
            if r.status_code == 401: raise BadToken("check EODHD_API_TOKEN (no quotes/whitespace)")
            if r.status_code == 402: raise DailyLimit(r.text[:200])
            if r.status_code == 403: raise NotEntitled(f"{path}: not in plan, wrong path, or symbol not entitled")
            r.raise_for_status()                                           # 404 (charged!), 422 -> fix request
        raise EODHDError(f"{path}: retries exhausted")
```

Notes: never log `r.url` (it contains the token). Multi-symbol live requests cost one call per symbol —
pass `cost=len(symbols)`. Bulk with `symbols=` costs `100 + len(symbols)`. Read `X-RateLimit-Remaining`
from responses if you want adaptive pacing; it does not cover Marketplace quotas.

## 2. EOD history with adjusted OHLC

```python
import pandas as pd

def eod_frame(c: Client, symbol: str, start=None, end=None) -> pd.DataFrame:
    code, ex = symbol.rsplit(".", 1)
    rows = c.get(f"eod/{symbol}", symbol_exchange=ex, **{k: v for k, v in {"from": start, "to": end}.items() if v})
    df = pd.DataFrame(rows)
    if df.empty:
        return df                                    # empty != "no trading": record as coverage gap
    df["date"] = pd.to_datetime(df["date"]).dt.date  # session label, not an instant
    valid = df["close"].notna() & (df["close"] != 0) & df["adjusted_close"].notna()
    k = (df["adjusted_close"] / df["close"]).where(valid)   # per-day factor, never one factor for all rows
    for col in ("open", "high", "low"):
        df[f"adj_{col}"] = df[col] * k
    df["adj_close"] = df["adjusted_close"]
    # volume is already split-adjusted; pair it with split-adjusted prices for dollar volume
    return df
```

Re-pull the full series after any new split/dividend (adjusted values are restated). For split-only
prices use `technical/{symbol}?function=splitadjusted` (5 calls).

## 3. Daily bulk update with date check

```python
def bulk_day(c: Client, exchange: str, day: str | None = None):
    params = {"date": day} if day else {}
    rows = c.get(f"eod-bulk-last-day/{exchange}", **params)          # 100 calls per exchange-day
    dates = {r["date"] for r in rows}
    if day and dates != {day}:
        raise ValueError(f"asked {day}, got {sorted(dates)[:3]}: holiday/future-date fallback")
    return rows
```

Schedule US runs after the close and re-run next morning (~06:00 ET) for late funds/OTC; other exchanges
2–3 h after their close. Bulk is for daily increments; backfill history per ticker (1 call each).

## 4. Intraday backfill in legal windows

```python
from datetime import datetime, timedelta, timezone

MAX_DAYS = {"1m": 120, "5m": 600, "1h": 7200}

def intraday_windows(start: datetime, end: datetime, interval: str):
    step = timedelta(days=MAX_DAYS[interval] - 1)        # stay inside the documented maximum
    t = start
    while t < end:
        u = min(t + step, end)
        yield int(t.replace(tzinfo=timezone.utc).timestamp()), int(u.replace(tzinfo=timezone.utc).timestamp())
        t = u

def intraday(c: Client, symbol, start, end, interval="1m"):
    out = {}
    for a, b in intraday_windows(start, end, interval):
        for bar in c.get(f"intraday/{symbol}", interval=interval, **{"from": a, "to": b}):
            out[bar["timestamp"]] = bar                    # dedupe overlapping window edges
    return [out[k] for k in sorted(out)]                   # UTC bar starts; unadjusted; nulls = missing
```

Probe the first available bar before promising history (US 1m dataset since 2004, but SPY from 2013).
Filter regular hours with the exchange calendar, not fixed UTC offsets. Bars finalize ~2–3 h after close.

## 5. Universe: active + delisted symbol lists

```python
def universe(c: Client, exchange: str, type_=None):
    p = {"type": type_} if type_ else {}
    active = c.get(f"exchange-symbol-list/{exchange}", **p)
    delisted = c.get(f"exchange-symbol-list/{exchange}", delisted=1, **p)   # replaces, not extends
    seen = {}
    for row, flag in [(r, False) for r in active] + [(r, True) for r in delisted]:
        key = (row["Code"], row["Exchange"])
        seen.setdefault(key, {**row, "is_delisted_list": flag})
    return list(seen.values())   # current snapshot; store with retrieval date, not as history
```

Treat `_old`, `_old1` … suffixes as separate securities. Match external holdings by ISIN first.

## 6. Unit normalization

```python
# minor-unit codes seen in EODHD symbol metadata: LSE "GBX" (pence), JSE "ZAC" (cents)
MINOR_UNITS = {"GBX": ("GBP", 0.01), "ZAC": ("ZAR", 0.01)}

def normalize_price(value, currency):
    major, mult = MINOR_UNITS.get((currency or "").upper(), (currency, 1.0))
    return (None if value is None else value * mult), major, mult   # keep raw value + multiplier too
```

Take `currency` from the symbol list / `General.CurrencyCode` **per symbol**: active LSE lines are a mix
of GBX, USD, EUR and GBP (and others), JSE mostly ZAC with some ZAR. Dividends and statements have their
own currency fields.

## 7. Fundamentals sections

```python
def fundamentals(c: Client, symbol, section=None):
    p = {"filter": section} if section else {}
    return c.get(f"fundamentals/{symbol}", **p)        # 10 calls regardless of filter

profile = fundamentals(c, "AAPL.US", "General")
shares = fundamentals(c, "AAPL.US", "outstandingShares")      # annual/quarterly share counts
members = fundamentals(c, "GSPC.INDX", "HistoricalTickerComponents")
```

Cache fundamentals for days, refresh around earnings. Send only the needed section to an LLM.

## 8. Screener partitioning

```python
import json

def screen(c: Client, filters, sort="market_capitalization.desc", signals=None, page=500):
    rows, offset = [], 0
    while offset <= 999:                                  # offset 0..999, limit 1..500
        p = {"filters": json.dumps(filters), "sort": sort, "limit": page, "offset": offset}
        if signals: p["signals"] = ",".join(signals)
        batch = c.get("screener", **p).get("data", [])
        rows += batch
        if len(batch) < page: return rows, False          # complete
        offset += page
    return rows, True                                     # truncated at 1,000 -> partition further

# partition a big screen into non-overlapping market-cap bands on one exchange (one currency)
bands = [(0, 3e8), (3e8, 2e9), (2e9, 1e10), (1e10, 1e15)]
for lo, hi in bands:
    part, truncated = screen(c, [["exchange", "=", "us"], ["market_capitalization", ">=", lo],
                                 ["market_capitalization", "<", hi]])
```

Filters combine with AND; strings support `=`, `match`, `in`, `not in`; numbers also `!=`, `>`, `<`,
`>=`, `<=`. Use straight double quotes (curly quotes → 422). Market cap is in each listing's currency —
filter by exchange or read `currency_symbol`. `dividend_yield` is a fraction (0.05 = 5%). The screener is a
current snapshot: not a historical universe. Demo key does not work here.

## 9. ID mapping pagination

```python
def id_map(c: Client, **filters):            # e.g. isin="US0378331005" or ex="US"
    p = {f"filter[{k}]": v for k, v in filters.items()}
    offset, out = 0, []
    while True:
        page = c.get("id-mapping", **p, **{"page[limit]": 1000, "page[offset]": offset})
        out += page.get("data", [])
        if not page.get("links", {}).get("next"):
            return out                       # current identifiers only; no effective dates
        offset += 1000
```

## 10. Exchange calendar and freshness

```python
from zoneinfo import ZoneInfo

def exchange_calendar(c: Client, code="US"):
    d = c.get(f"v2/exchange-details/{code}")["data"]       # v2: hours + holidays keyed by date
    return ZoneInfo(d["Timezone"]), d["TradingHours"], d.get("ExchangeHolidays", {})

def is_fresh(observed_utc: datetime, now_utc: datetime, max_age_s: int, market_open: bool) -> bool:
    if observed_utc is None: return False                   # unknown time fails closed
    if not market_open: return False                        # last close is valid display, not a fresh quote
    return (now_utc - observed_utc).total_seconds() <= max_age_s
```

Holiday `Type` can be `Official`, `Bank` or `EarlyClose` (with `EarlyClose` time). Use the calendar to
drop flat holiday bars and to decide when a daily job may expect data.

## 11. WebSocket recorder

```python
import asyncio, json, random, websockets   # pip install websockets

async def stream(token, feed="us", symbols=("AAPL", "MSFT"), on_msg=print):
    url = f"wss://ws.eodhistoricaldata.com/ws/{feed}?api_token={token}"
    delay = 1
    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                await ws.send(json.dumps({"action": "subscribe", "symbols": ",".join(symbols)}))
                delay = 1
                async for raw in ws:
                    on_msg(json.loads(raw))              # trades/quotes, not candles; keep receipt time too
        except (websockets.ConnectionClosed, OSError):
            await asyncio.sleep(delay + random.random()); delay = min(delay * 2, 60)
```

One socket per feed (`us`, `us-quote`, `eu`, `forex`, `crypto` …) with all symbols in one subscribe
message; 50 symbol slots per token across sockets; forex symbols like `EURUSD`, crypto `BTC-USD`. Build
bars only from trades with an explicit lateness policy; backfill gaps from intraday after finalization.

## 12. Marketplace options by expiry

```python
def option_chain(c: Client, underlying: str, exp_from: str, exp_to: str):
    out, offset = [], 0
    while offset <= 10_000:
        page = c.get("mp/unicornbay/options/eod", cost=10, **{
            "filter[underlying_symbol]": underlying, "filter[exp_date_from]": exp_from,
            "filter[exp_date_to]": exp_to, "page[limit]": 1000, "page[offset]": offset})
        out += page.get("data", [])
        if not page.get("links", {}).get("next"): break
        offset += 1000
    return out   # partition by expiry, not tradetime (null/old for untraded contracts)
```

Marketplace calls draw on the product's own 100k/24 h quota. Check exact filter names against
[the options reference](api/endpoints/us-options-eod.md) before shipping; the reference wins over this
sketch.

## 13. Notebook research (Jupyter)

Notebooks are the most common way people explore EODHD data; the risks are leaked tokens, re-spent API
calls on every re-run, and results nobody can reproduce.

- **Token**: read `EODHD_API_TOKEN` from the environment (or a `.env` file listed in `.gitignore`); never
  paste it into a cell. Strip outputs before committing (`nbstripout` as a git filter) because printed URLs
  and tracebacks can contain it.
- **Cache every request** on disk keyed by endpoint + parameters (token excluded), so re-running a notebook
  costs no calls and the data stays fixed while you iterate. Expire live/intraday entries; keep historical
  pulls until you deliberately refresh them (adjusted series restate — note the retrieval date).
- **Structure**: parameters cell (symbols, dates, plan assumptions) → data cell (cached pulls, call budget
  printed) → checks (row counts, first/last dates, units, gaps) → analysis → conclusions with dates and
  basis. Move reusable code into a module once it is used twice.
- **Reproducible runs**: parameterize with `papermill` (`-p symbol AAPL.US -p start 2015-01-01`) and save the
  executed notebook next to the cache manifest. A notebook that only works top-to-bottom once is a script
  waiting to be written.
- **Sharing**: share code without cached data or outputs (personal-use data stays private); demos and
  public repositories use the synthetic generator in [app-ai-patterns](app-ai-patterns.md).

```python
import hashlib, json, os, pathlib, time

CACHE = pathlib.Path(os.environ.get("EODHD_CACHE_DIR", ".eodhd_cache"))

def cached(fetch, endpoint, params, max_age_s=None):
    """Disk cache for notebook research: same request -> same file; token never part of the key or file."""
    safe = {k: v for k, v in sorted(params.items()) if k != "api_token"}
    key = hashlib.sha256(json.dumps([endpoint, safe], sort_keys=True).encode()).hexdigest()[:24]
    path = CACHE / f"{endpoint.replace('/', '_')}-{key}.json"
    if path.exists() and (max_age_s is None or time.time() - path.stat().st_mtime < max_age_s):
        return json.loads(path.read_text())["body"]
    body = fetch(endpoint, safe)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"endpoint": endpoint, "params": safe, "retrieved_at": time.time(), "body": body}))
    return body
```

Acceptance: two calls with the same endpoint/params (different tokens) fetch once; no cache file contains
the token; `max_age_s` forces a refresh for live data.

## 14. Outbound webhooks for alerts and events

Use when an alert, screener hit or pipeline event must reach another system (the user's own app, a chat
workspace incoming-webhook, an automation tool). EODHD has no push API for these — your scheduler or stream
consumer detects the event and *you* send it. Personal-use limits still apply: posting to a channel other
people read is display to others ([licensing](licensing.md)).

- **Event identity**: derive a deterministic event id from (type, symbol, observation time, payload) so a
  re-run or retry produces the same id and the receiver can drop duplicates.
- **Signing**: HMAC-SHA256 over `timestamp + "." + body` with a shared secret kept outside the code; send the
  id, timestamp and signature as headers; the receiver checks signature, a ±5-minute freshness window and the
  id against recently seen ids.
- **Delivery**: retry network errors, 429 and 5xx with capped backoff and jitter; do not retry other 4xx
  (configuration problem); after the last attempt park the event in a dead-letter table for replay. Never
  block the market-data job on a slow receiver — queue and send from a separate worker.
- **Content**: include observation time and data basis ("delayed 15 min", "EOD close of 2026-10-23"), not
  just a price; never include the EODHD token or raw bulk data dumps.

```python
import hashlib, hmac, json, time, random, urllib.request, urllib.error

def sign(secret: bytes, ts: str, body: bytes) -> str:
    return hmac.new(secret, ts.encode() + b"." + body, hashlib.sha256).hexdigest()

def build_event(kind, symbol, observed_at, payload):
    """Deterministic event id = same alert, same id (lets the receiver drop duplicates)."""
    key = f"{kind}|{symbol}|{observed_at}|{json.dumps(payload, sort_keys=True)}"
    return {"id": hashlib.sha256(key.encode()).hexdigest()[:32], "type": kind, "symbol": symbol,
            "observed_at": observed_at, "data": payload}

def deliver(url, secret: bytes, event, attempts=5, timeout=10, post=None, sleep=time.sleep):
    """POST with HMAC signature; retry 429/5xx/network errors with capped backoff; never retry other 4xx."""
    body = json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
    for i in range(attempts):
        ts = str(int(time.time()))
        headers = {"Content-Type": "application/json", "X-Event-Id": event["id"],
                   "X-Timestamp": ts, "X-Signature": sign(secret, ts, body)}
        try:
            status = post(url, body, headers, timeout) if post else _post(url, body, headers, timeout)
        except OSError:
            status = None
        if status is not None and 200 <= status < 300:
            return {"ok": True, "attempts": i + 1}
        if status is not None and 400 <= status < 500 and status != 429:
            return {"ok": False, "attempts": i + 1, "status": status}   # permanent: fix config
        sleep(min(60, 2 ** i) + random.random())
    return {"ok": False, "attempts": attempts, "status": "gave_up"}  # park in a dead-letter table

def _post(url, body, headers, timeout):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code

def verify(secret: bytes, headers, body: bytes, seen_ids: set, max_skew=300, now=None):
    """Receiver side: signature, freshness window, replay/duplicate protection."""
    ts = headers.get("X-Timestamp", "")
    if not ts.isdigit() or abs((now or time.time()) - int(ts)) > max_skew:
        return "stale"
    if not hmac.compare_digest(sign(secret, ts, body), headers.get("X-Signature", "")):
        return "bad_signature"
    eid = headers.get("X-Event-Id")
    if eid in seen_ids:
        return "duplicate"
    seen_ids.add(eid)
    return "accept"
```

Acceptance: a 503 → 429 → 200 sequence delivers on attempt 3; a 401 stops after one attempt; the receiver
returns `accept`, then `duplicate` for the same event, `bad_signature` for a wrong secret and `stale` for an
old timestamp; reordering payload keys does not change the event id.
