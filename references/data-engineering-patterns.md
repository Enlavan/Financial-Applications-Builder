# Data-engineering patterns for EODHD pipelines

Concrete, EODHD-specific engineering for people who run EODHD data through a scheduler, a warehouse, a BI
tool or a stream processor. It maps the principles in [ingestion](ingestion.md), [storage](storage.md),
[operations](operations.md), [quality](quality.md) and [code patterns](code-patterns.md) onto the tools users
name (cron, Airflow, Dagster, Prefect, Mage, dbt, SQLMesh, Great Expectations, Soda, PostgreSQL, ClickHouse,
Iceberg/Delta, DuckDB, Polars, Kafka/Redpanda, Power BI, Superset, Metabase, CI and containers). It does not repeat those chapters:
read them for the request loop, raw/normalized/serving layers, replay tests and repair workflow. Call costs
and limits come from [plans-limits.md](plans-limits.md); symbol, unit and timing facts from
[coverage-notes.md](coverage-notes.md). Every schema below is an application design for the user's own
archive, not an EODHD database schema. Library and orchestrator APIs change between versions: the names used
here were current in 2026; check the installed version before copying.

## Contents

1. [Scheduler recipe: partitions, timing, retries, quota](#1-scheduler-recipe-partitions-timing-retries-quota)
2. [Orchestrator mapping: cron, Airflow, Dagster, Prefect, connectors](#2-orchestrator-mapping-cron-airflow-dagster-prefect-connectors)
   - Mage mapping; dbt build step between publish and swap
3. [dbt/SQL transformation layer](#3-dbtsql-transformation-layer)
   - SQLMesh model, audits and restatement
4. [Executable data-quality suite](#4-executable-data-quality-suite)
   - Q13 identifier check digits, Q14 per-asset-class move thresholds
5. [Data SLAs, ops dashboard, failure taxonomy, incident record](#5-data-slas-ops-dashboard-failure-taxonomy-incident-record)
6. [Storage DDL with correction-friendly keys](#6-storage-ddl-with-correction-friendly-keys)
7. [Durable streaming log for WebSockets](#7-durable-streaming-log-for-websockets)
8. [SCD2 listing history from symbol-list snapshots](#8-scd2-listing-history-from-symbol-list-snapshots)
   - issuer → security (ISIN) → listing keys, same-as links, Data Vault mapping and PIT table
9. [Pipeline migration and parity testing](#9-pipeline-migration-and-parity-testing)
10. [Fixture-based unit tests](#10-fixture-based-unit-tests)
   - contract and schema-diff test against `assets/dataset-contract.json`
11. [Metric dictionary and aggregation rules](#11-metric-dictionary-and-aggregation-rules)
   - populated registry: price/total return, CAGR, volatility, Sharpe, Sortino, drawdown, dividend yield TTM, yield on cost
12. [Serving BI tools](#12-serving-bi-tools)
13. [CI, containers and secret handling](#13-ci-containers-and-secret-handling)
14. [Deletable user data versus immutable market captures](#14-deletable-user-data-versus-immutable-market-captures)
15. [Replay and re-pull checklist with atomic swap](#15-replay-and-re-pull-checklist-with-atomic-swap)
16. [Research-engineering patterns: trial registry, Polars, DuckDB over raw captures](#16-research-engineering-patterns-trial-registry-polars-duckdb-over-raw-captures)

Facts used throughout (details in the linked chapters):

| Fact | Consequence for a pipeline |
|---|---|
| Bulk `eod-bulk-last-day/{EX}` = 100 calls per exchange-day; `type=splits` / `type=dividends` 100 each; `symbols=` adds 1 per ticker | Daily increments use bulk; history uses per-ticker `eod` (1 call for the full series) |
| Bulk `date=` on a non-trading day silently returns the previous session; a future date returns the latest | Never trust the requested date; check the returned `date` |
| `adjusted_close` (split + dividend) and `volume` (split-adjusted) are restated over the whole history when an action is added or corrected; raw OHLC are not | Incremental loads cannot be append-only; a new action means a full-symbol re-pull |
| Limits: 1,000 requests/min; 100,000 weighted calls/day reset at 00:00 GMT; Marketplace 100,000 per product per 24 h from first use | One limiter and one budget per key; separate pools per Marketplace product |
| 401 token, 402 daily calls exhausted, 403 not entitled/wrong path, 404 unknown symbol (charged), 422 bad parameters, 429 minute limit (`Retry-After`) or Marketplace quota | Status-aware retry; most 4xx never retry |
| `v2/exchange-details/{CODE}`: IANA timezone, regular/extended hours, current-year holidays with `Type` `Official` / `Bank` / `EarlyClose`; 1 call; EOD+Intraday Extended or All-In-One | Calendar-driven partitions; cache it, never call it at parse time |
| Typical availability: NYSE/NASDAQ ~16:15 ET then refined; Arca ETFs 18:00–19:00 ET; US funds, OTC/PINK next morning 03:00–06:00 ET; most other exchanges close + 2–3 h | Schedule after the lag, keep a retry window and a refinement re-run |
| WebSockets: no history, no replay, no sequence numbers; US trades from a single venue | Persist the stream yourself if anything downstream needs replay |
| No point-in-time vintages for Fundamentals, adjusted prices and most datasets; exceptions are SEC Filings rows (one per filing), S&P 500 membership from 2012 and economic-event first releases ([temporal research](temporal-research.md)) | Local captures are the only "as retrieved" history for everything else; say so in every as-of view |

---

## 1. Scheduler recipe: partitions, timing, retries, quota

**Use when** the user schedules daily EODHD ingestion (EOD, actions, fundamentals, intraday) and wants it to
survive holidays, late data, quota exhaustion and corrections without manual repair.

**EODHD inputs**

| Dataset | Endpoint | Partition | Cost |
|---|---|---|---|
| Daily prices | `eod-bulk-last-day/{EX}?date=YYYY-MM-DD&fmt=json` | exchange × session | 100 |
| Daily actions | same path with `type=splits` / `type=dividends` (use `fmt=json` for dividend dates) | exchange × session | 100 each |
| Full series for one listing | `eod/{CODE}.{EX}?fmt=json` (+ `div/…`, `splits/…`) | listing | 1 each |
| Calendar | `v2/exchange-details/{CODE}` (v1 `exchange-details/{EX}?from=&to=` for other years and exchanges) | exchange × year | 1 |
| Universe | `exchange-symbol-list/{EX}` and `?delisted=1` | exchange × capture date | 1 each |
| Fundamentals | `fundamentals/{SYM}?filter=…` | listing × week (or earnings event) | 10 |
| Intraday | `intraday/{SYM}?interval=1m&from=&to=` (Unix UTC) | listing × window ≤120/600/7200 days (1m/5m/1h) | 5 |
| Budget | `/api/user` (`apiRequests`, `apiRequestsDate`, `dailyRateLimit`, `extraLimit`) | — | 0 |

### 1.1 Partitions from the exchange calendar

Partition key = `(exchange, session_date)` for EOD and actions. Generate the set from the calendar, so a
holiday never becomes a partition, and keep separate partition sets for other datasets (fundamentals weekly
per listing, intraday per listing × legal window, symbol lists per exchange × capture date).

Method:

1. Once a week (and on 1 January), fetch `v2/exchange-details/{CODE}` per exchange (1 call each) and store it
   as a dated file or table, `calendar_cache(exchange, year, captured_at, body)`.
2. A session is a date whose weekday is in `TradingHours.WorkingDays` and that is not an `Official` holiday.
   `EarlyClose` is a session whose close is the `EarlyClose` time. `Bank` is ambiguous: treat it as a session
   until the bulk date check (§1.3) proves otherwise for that exchange, then record the finding.
3. Compute the local close instant with the IANA `Timezone` (DST-aware), then `close_utc`. Never use a fixed
   UTC offset.
4. Pitfalls specific to this endpoint:
   - v2 covers 73 exchanges and returns **the current year's** holidays; for earlier years use v1 with
     `from`/`to` (its holiday array is indexed, with a lowercase `type`).
   - v2 codes are not always EODHD exchange codes: the documentation shows `US`, `LSE`, `TO`, `NEO` but also
     `XHKG` (Hong Kong, EOD code `HK`), `XPAR`, `XAMS`, `XASX`. Keep an explicit `eod_code → v2_code` map and
     verify every entry with a probe request; do not derive it from string similarity.
   - The endpoint needs EOD+Intraday Extended or All-In-One. On EOD All World, build an **observed calendar**:
     the dates present in one liquid reference listing's full EOD history (1 call per exchange). It is correct
     for the past, cannot predict future holidays, and must be labelled as observed; the bulk date check
     then decides whether a weekday was a session.

```python
from datetime import date, datetime, time as dtime, timedelta, timezone
from zoneinfo import ZoneInfo

DAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def expected_sessions(details: dict, start: date, end: date) -> list[dict]:
    """details = cached v2 exchange-details `data` object. Sessions with their UTC close instants."""
    tz, th = ZoneInfo(details["Timezone"]), details["TradingHours"]
    working = {d.strip() for d in th["WorkingDays"].split(",")}
    holidays, out, d = details.get("ExchangeHolidays") or {}, [], start
    while d <= end:
        h = holidays.get(d.isoformat()) or {}
        if DAY_ABBR[d.weekday()] in working and h.get("Type") != "Official":
            hh, mm, ss = (int(x) for x in (h["EarlyClose"] if h.get("Type") == "EarlyClose" else th["Close"]).split(":"))
            close_utc = datetime.combine(d, dtime(hh, mm, ss), tz).astimezone(timezone.utc)
            out.append({"session": d.isoformat(), "close_utc": close_utc, "flag": h.get("Type", "Regular")})
        d += timedelta(days=1)
    return out
```

### 1.2 Schedule at close + documented lag, with a retry window and a refinement run

A partition becomes **due** at `close_utc + lag`. Retry inside a **retry window**; after it the partition is
**late** (alert, keep trying at a slower cadence). Some data is refined later, so run a second, refining
request and upsert with a diff log. Lags below are the typical times in the public update-time guide, not
guarantees; tune them from your own `retrieved_at` history.

| Exchange (EOD code) | Local close | Typically available | First attempt | Retry window | Refinement run |
|---|---|---|---|---|---|
| US (NYSE/NASDAQ part) | 16:00 ET | ~16:15 ET, refined over hours | 16:45 ET | to 20:00 ET | next day 06:30 ET (Arca ETFs, funds, OTC/PINK, some indices) |
| LSE | 16:30 London | ~18:30–19:30 | 19:45 | to 23:30 | next morning |
| XETRA, PA (Euronext Paris) | 17:30 CET | ~19:30–20:30 | 20:45 | to 23:59 | next morning |
| HK | 16:00 HKT | ~18:00–19:00 | 19:30 | to 23:00 | next morning |
| SHG / SHE | 15:00 CST | ~17:00–18:00 | 18:30 | to 23:00 | next morning |
| EUFUND | — | ~19:00 GMT | 20:00 GMT | to 23:00 GMT | — |
| INDX | several updates: 00:30, 04:30, 07:00, 16:30, 20:30 ET | +10–15 min each | per update | to next update | — |
| Other exchanges | local close | close + 2–3 h | close + 3 h 15 | + 4 h | next morning |

```python
def due_sessions(sessions, committed: set[str], now_utc, lag: timedelta, retry_window: timedelta):
    """(session, "DUE"|"LATE") for uncommitted sessions whose close + lag has passed."""
    out = []
    for s in sessions:
        if s["session"] in committed:
            continue
        t0 = s["close_utc"] + lag
        if now_utc >= t0:
            out.append((s["session"], "DUE" if now_utc <= t0 + retry_window else "LATE"))
    return out
```

### 1.3 Commit guard: the bulk `date` must equal the expected session

```python
def bulk_guard(rows: list[dict], expected_session: str) -> str:
    dates = {r.get("date") for r in rows}
    if not rows:
        return "EMPTY"                   # investigate; never "no trading"
    if dates == {expected_session}:
        return "COMMIT"
    if max(dates) < expected_session:
        return "NOT_YET_AVAILABLE"       # not published yet, or a holiday fallback
    return "UNEXPECTED_DATES"            # mixed or future dates: fail and keep the capture
```

`NOT_YET_AVAILABLE` is a retryable state, not a failure and not an empty partition. If it persists past the
retry window on a date the calendar marked `Bank` or that comes from an observed calendar, record the date as
"no session (inferred)" only after a 1-call probe of a liquid reference listing also lacks it. Save the raw
response before evaluating the guard ([ingestion.md](ingestion.md)).

Cheap gating: a sensor that polls every 15 minutes with the 100-call bulk request burns 400 calls an hour.
Poll a 1-call `eod/{REF}.{EX}?from=S&to=S` for a liquid reference listing until it returns session `S`, then
issue the bulk request once. The reference row does not prove the exchange is complete (Arca ETFs and funds
arrive later): that is what the refinement run is for.

### 1.4 Status-aware retry and a circuit breaker

| Status / condition | Retry? | Action |
|---|---|---|
| 200 + guard `COMMIT` | — | Commit partition |
| 200 + `NOT_YET_AVAILABLE` | Yes, until the retry window ends | Re-check at 15–30 min cadence |
| 200 + `[]` / `EMPTY` | No automatic retry | Validate parameters (bad dates also give `[]`); probe one symbol |
| 401 | Never | Stop all jobs on this key; fix configuration (placeholder, quotes, whitespace) |
| 402 | Never inside the day | Stop every job on the key until 00:00 GMT (+5 min), or until extra calls are bought |
| 403 | Never | Entitlement or wrong path; one symbol's 403 is a per-symbol fact, many symbols' 403 is a plan fact |
| 404 | Never (each probe is charged) | Fix the symbol; check renames, `_old` reuse and delisted lists |
| 422 | Never | Fix the request (range too long, bad date, curly quotes) |
| 429 | Yes, bounded | Honour `Retry-After`; for Marketplace, wait for that product's window |
| 5xx, timeout, connection reset | Yes, bounded | Exponential backoff with jitter, max ~5 attempts |

```python
import random
from datetime import datetime, timedelta

def retry_decision(status: int, headers: dict, attempt: int, now_utc: datetime, max_attempts: int = 5):
    """-> (action, wait_seconds); action in OK | RETRY | DEFER | FAIL. status 0 = transport error."""
    if status == 200:
        return "OK", 0.0
    if status in (401, 403, 404, 422):
        return "FAIL", 0.0
    if status == 402:
        midnight = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return "DEFER", (midnight - now_utc).total_seconds() + 300
    if attempt + 1 >= max_attempts:
        return "FAIL", 0.0
    if status == 429:
        ra = headers.get("Retry-After", "")
        base = float(ra) if ra.strip().isdigit() else 2.0 ** attempt
        return "RETRY", min(base, 120.0) + random.uniform(0, 1)      # never earlier than Retry-After
    if status in (0, 500, 502, 503, 504):
        return "RETRY", min(2.0 ** attempt, 60.0) * random.uniform(0.5, 1.0)
    return "FAIL", 0.0
```

Circuit breaker, one per key (and per Marketplace product): **open** on a 402 (until after 00:00 GMT), on a
401 or on 403s for K distinct symbols of a family (until a person resets it, because every further request
fails too), or after N consecutive transient failures (cool down 15 min, then **half-open**: allow one cheap
probe, close on success). Every job checks the breaker before spending calls, so one exhausted key does not
produce a storm of failing tasks across DAGs.

```python
from dataclasses import dataclass

@dataclass
class CircuitBreaker:
    threshold: int = 5
    cooldown_s: float = 900
    failures: int = 0
    open_until: float = 0.0          # epoch seconds; float("inf") = manual reset required
    reason: str = ""

    def allow(self, now: float) -> bool:
        return now >= self.open_until

    def record(self, action: str, wait_s: float, now: float, manual: bool = False) -> None:
        if action == "OK":
            self.failures, self.reason = 0, ""
        elif action == "DEFER":
            self.open_until, self.reason = now + wait_s, "daily limit (402)"
        elif manual:
            self.open_until, self.reason = float("inf"), "auth/entitlement: needs a person"
        else:
            self.failures += 1
            if self.failures >= self.threshold:
                self.open_until, self.reason = now + self.cooldown_s, f"{self.failures} consecutive failures"
```

Persist breaker state in the job store (a row per key), not in process memory, so all workers see it.

### 1.5 One concurrency pool per API key, sized to the minute limit and a weighted daily budget

Two limits apply to one key regardless of how many machines, DAGs or users run: requests per minute and
weighted calls per GMT day ([plans-limits.md](plans-limits.md)).

- **Rate**: target 80–90% of `X-RateLimit-Limit` (1,000 → 800–900 requests/min), enforced by one token bucket.
- **Concurrency**: `slots = ceil(target_rate_per_min / 60 × p95_latency_s)`; 800/min at 0.6 s → 8 slots. A
  pool alone does not bound the rate when latency drops, so keep both.
- **Daily budget** in calls, not requests: each request reserves its endpoint cost. Reserve the daily jobs'
  needs first; backfills get the remainder.

```text
reserved_daily = Σ_exchanges (100 EOD + 100 splits + 100 dividends) + refinement runs (100 each)
               + action re-pulls (≈ number of listings with an action × 1–3)
               + rolling full refresh (N_listings / R days) + weekly lists/calendars ÷ 7
backfill_cap   = floor(0.9 × dailyRateLimit) − reserved_daily − spent_today
```

Example: 10 exchanges (3,000) + US refinement (100) + ~150 action re-pulls (150) + US rolling refresh of
~44,000 listings over 30 days (~1,470) + lists/calendars (~5) ≈ 4,725 calls/day reserved; with the default
100,000 a backfill may take about 85,000 calls today.

`spent_today` comes from `/api/user` (0 calls): use `apiRequests` only when `apiRequestsDate` is today (GMT);
otherwise the counter has not reset yet and today's spend is 0. That number covers every application on the
account, which is what you want. Extra purchased calls are spent after the daily limit; decide explicitly
whether backfills may consume them.

Parallel and distributed fetchers (multiprocessing, Spark, Dask, several containers) do not share an
in-process limiter. Either (a) run one fetch service that owns the key and receives work from a queue —
simplest and usually enough — or (b) keep the token bucket and the budget ledger in a shared store
(PostgreSQL row with `SELECT … FOR UPDATE`, or Redis), or (c) pre-plan partitions with per-worker quotas
that sum below the limits. Read the key from the environment on each worker; never serialize a client object
holding the token into task closures or logs. Do not spread work across several personal accounts to raise
limits: each person needs their own account ([licensing.md](licensing.md)); raise the limit instead.

Marketplace products (options, constituents, tick data) get their own pool and budget: 100,000 calls per
product per 24 h counted from that product's first request, so the window drifts; record the first-request
time of each window.

### 1.6 No API calls at definition time

Orchestrators import definition files often: Airflow re-parses each DAG file about every 30 s by default, so
one top-level `requests.get` costs ~2,880 requests a day per file and fails parsing whenever the key is
throttled. Build partition lists from the cached calendar (§1.1), resolve the key only inside tasks
(environment or secrets backend), and test it: importing the definitions with networking disabled must
succeed and make zero HTTP calls (§13).

### 1.7 Backfill with a call estimate

Estimate before starting, run from an explicit target-partition list, cap concurrency, make it resumable and
let it yield to the daily job (lower priority in the same pool, never a separate pool on the same key).

```text
calls = 2·E (active + delisted lists per exchange)
      + N·(1 EOD + 1 splits + 1 dividends)                      per-ticker full history
      + N·10                                                    if fundamentals
      + N·ceil(span_days / (max_days − 1))·5                    if intraday (max_days 120/600/7200)
      × (1 + retry_overhead)                                    5% is a reasonable start
days  = ceil(calls / backfill_cap)
```

```python
import math

INTRADAY_MAX_DAYS = {"1m": 120, "5m": 600, "1h": 7200}

def backfill_estimate(n_symbols, *, n_exchanges=1, eod=True, actions=True, fundamentals=False,
                      intraday=None, retry_overhead=0.05) -> int:
    calls = 2 * n_exchanges
    calls += n_symbols * ((1 if eod else 0) + (2 if actions else 0) + (10 if fundamentals else 0))
    if intraday:                                   # ("1m", span_days)
        interval, span_days = intraday
        calls += n_symbols * math.ceil(span_days / (INTRADAY_MAX_DAYS[interval] - 1)) * 5
    return math.ceil(calls * (1 + retry_overhead))
```

Checks: 5,000 US listings with EOD and actions → `ceil(15,002 × 1.05)` = 15,753 calls, one day.
One listing, 10 years of 1m bars → 31 windows × 5 = 155 calls (+2 for lists). Bulk is the wrong tool for
history: one exchange-day per 100 calls (≈25,200 calls for a year of US sessions) versus 1 call per listing
for its full series. Free-plan keys return one year silently clipped; never record that as a listing's start.

### 1.8 Corporate-action-triggered full re-pull

Because `adjusted_close` and `volume` are restated over the whole history, any listing with a new split or
dividend needs its full series replaced, not one new row.

1. After session `S` commits for an exchange, request bulk `type=splits` and `type=dividends` for `date=S`
   (200 calls). Apply the same date guard to every row.
2. For each listing in either file, enqueue `full_refresh(listing)`: `eod/{SYM}` without `from`/`to`
   (1 call); add `div/{SYM}` and `splits/{SYM}` (1 each) if you keep a full action ledger.
3. Verify the restatement arrived: compare the factor across the ex-date in the new pull,
   `f = k(S_prev) / k(S)` with `k = adjusted_close / close`. Expect `f ≈ 1/r` for a split with ratio
   `r = new/old` (bulk splits report `"new/old"`, e.g. `"2.000000/1.000000"`) and `0 < f < 1` close to
   `(P_prev − D)/P_prev` for a cash dividend `D` (EODHD's exact treatment can differ; use a band, not
   equality). If `f` is still 1, re-queue for the next run (at most 3 times), then flag.
4. Replace that listing's normalized rows in one transaction (delete + insert for the listing), with the new
   capture id, and mark its marts for a full-symbol rebuild (§3).
5. Separately, run a **rolling full refresh**: re-pull `N/R` listings per day so the whole universe is
   re-read every `R` days. It is the only way to catch corrections whose action does not appear in a daily
   file. Compare against stored rows and log the differences ([quality.md](quality.md)).

Pitfalls: the bulk dividends file uses `dividend` and `unadjustedValue` (strings), while `div/{SYM}` uses
`value` and `unadjustedValue`; splits use `exchange`, prices `exchange_short_name`. Same-day split and
dividend need compatible share bases ([corporate-actions.md](corporate-actions.md)).

### 1.9 Calendar-gap targeted backfill

1. Exchange level: `expected_sessions(calendar) − committed_sessions` within the archive span → re-request
   bulk for those dates (100 calls each; dated bulk reaches back decades).
2. Listing level: only for listings that traded on at least 95% of the trailing 60 sessions. Thinly traded
   listings have no row on no-trade days; their gaps are normal, not errors.
3. Per missing `(listing, session)` request `eod/{SYM}?from=S1&to=S2` (1 call, any range). When more than
   ~100 listings miss the same session, one bulk request for that date is cheaper (100 calls).
4. A gap still present after the re-request is recorded as `absent_as_of(capture_id)`; never fabricate a row
   or a zero-volume bar.

### Acceptance checks

- Importing the definitions with networking disabled makes zero HTTP calls.
- A holiday produces no partition; `Bank` and observed-calendar dates are decided by the bulk date check.
- A bulk response dated the previous session leaves the partition `NOT_YET_AVAILABLE`, not failed or empty.
- Re-running a committed partition with an identical response changes no rows (same capture hash).
- A 402 opens the breaker until 00:05 GMT, and no task on that key issues a request meanwhile.
- A 401 or a family-wide 403 is never retried; a 429 waits at least `Retry-After`.
- A synthetic new split for one listing triggers exactly one full re-pull and one symbol rebuild.
- A backfill started with 10,000 calls left stops at its cap and resumes the next GMT day without gaps or
  duplicates; the daily job still runs on time.

---

## 2. Orchestrator mapping: cron, Airflow, Dagster, Prefect, connectors

**Use when** the user already has, or asks for, a specific scheduler.

| Concept (§1) | cron + small runner | Airflow 2.x/3.x | Dagster 1.x | Prefect 3.x |
|---|---|---|---|---|
| Partition exchange × session | job args + `committed_partition` table | one DAG per exchange from a factory; run → session via cached calendar | `DynamicPartitionsDefinition` keys `"US\|2026-10-23"` added by a sensor | flow parameters `(exchange, session)` |
| Schedule after close + lag | tick every 15 min (UTC host); the runner decides what is due | `CronTriggerTimetable(cron, timezone=exchange_tz)` | sensor emitting `RunRequest`s for due partitions | deployment cron schedule with the exchange timezone |
| Holiday | not due → nothing runs | `@task.short_circuit` returns `False` → downstream skipped | no partition key exists | flow returns early with a "no session" state |
| Retry window | next tick retries until the window ends | `retries` × `retry_delay` = window | `RetryRequested(max_retries, seconds_to_wait)` | `retries`, `retry_delay_seconds` |
| Never retry 401/403/422 | exit code ≠ temp-fail, alert | `AirflowFailException` | `Failure(..., allow_retries=False)` | `retry_condition_fn` returns `False` |
| 402 | breaker row; runner skips the key | `AirflowFailException` + breaker row checked by every DAG | breaker resource checked by the sensor | breaker check before the flow |
| One pool per key | single process (`flock`) + limiter | Pool `eodhd_api` used by every EODHD task | `pool="eodhd_api"` (older: `dagster/concurrency_key` tag) | global concurrency limit `eodhd-api` |
| Quality gate before publish | run checks, then swap | validate task upstream of publish | `@asset_check(blocking=True)` | task order + state check |
| Backfill | script over a partition list | separate DAG, `catchup=False`, `max_active_runs` | backfill a partition subset | separate deployment, lower priority |

**cron** (simplest; enough for one person's archive):

```text
# UTC host; the runner computes due partitions from the cached calendar, so DST never shifts the job
*/15 * * * * flock -n /var/lock/eodhd.lock /opt/eodhd/venv/bin/python -m pipeline.tick >> /var/log/eodhd/tick.log 2>&1
```

```python
# pipeline/tick.py (sketch): one pass, bounded work, idempotent
def tick(now_utc):
    for ex in EXCHANGES:
        if not breaker(ex.key).allow(now_utc.timestamp()):
            continue
        for session, state in due_sessions(cached_sessions(ex), committed(ex), now_utc, ex.lag, ex.window):
            if not budget.reserve(ex.key, 100):
                return                                   # nothing more today
            rows, status, headers = fetch_bulk(ex.code, session)   # saves the raw capture first
            action, wait = retry_decision(status, headers, attempt=0, now_utc=now_utc)
            breaker(ex.key).record(action, wait, now_utc.timestamp(), manual=status in (401, 403))
            if action == "OK" and bulk_guard(rows, session) == "COMMIT":
                commit_partition(ex.code, session, rows)  # validate → publish (§4, §15)
            elif state == "LATE":
                alert_once(ex.code, session, "late")
```

If the host's cron supports it (cronie), `CRON_TZ=America/New_York` runs a line in exchange time; the
tick pattern avoids depending on that.

**Airflow** (factory; no calls at import; the pool caps concurrency for every EODHD task):

```python
from datetime import timedelta
import pendulum
from airflow.decorators import dag, task              # Airflow 3: from airflow.sdk import dag, task
from airflow.exceptions import AirflowFailException
from airflow.timetables.trigger import CronTriggerTimetable
from pipeline import calendar_cache, eodhd, store     # user package; reads EODHD_API_TOKEN inside tasks
from pipeline.guards import bulk_guard                # §1.3

class NotYetAvailable(Exception):
    pass

def make_dag(exchange: str, cron: str, tz: str):
    @dag(dag_id=f"eodhd_eod_{exchange.lower()}", schedule=CronTriggerTimetable(cron, timezone=tz),
         start_date=pendulum.datetime(2026, 1, 1, tz=tz), catchup=False, max_active_runs=1,
         default_args={"pool": "eodhd_api", "retries": 8, "retry_delay": timedelta(minutes=20)})
    def eod_daily():
        @task.short_circuit
        def session_for_run(**ctx):
            local_day = ctx["logical_date"].in_timezone(tz).date()
            return calendar_cache.session_on(exchange, local_day) or False   # holiday → skip, not fail

        @task
        def load_bulk(session: str):
            if not store.breaker_allows(exchange):
                raise AirflowFailException("breaker open")
            rows = eodhd.bulk_eod(exchange, session)   # raises AirflowFailException on 401/402/403/422
            state = bulk_guard(rows, session)
            if state == "NOT_YET_AVAILABLE":
                raise NotYetAvailable(session)          # ordinary exception → retried inside the window
            if state != "COMMIT":
                raise AirflowFailException(state)
            return store.stage_partition(exchange, session, rows)

        @task
        def actions_and_repulls(session: str): ...      # §1.8
        @task
        def validate_and_publish(session: str): ...     # §4, then §15 swap

        s = session_for_run()
        load_bulk(s) >> actions_and_repulls(s) >> validate_and_publish(s)
    return eod_daily()

for ex, cron, tz in [("US", "45 16 * * 1-5", "America/New_York"), ("LSE", "45 19 * * 1-5", "Europe/London")]:
    globals()[f"eodhd_eod_{ex.lower()}"] = make_dag(ex, cron, tz)
```

Create the pool once (`airflow pools set eodhd_api 8 "EODHD key"`); the refinement run is a second DAG
(`30 6 * * 2-6` New York) that re-requests the previous session and upserts with a diff log.

**Dagster** (dynamic partitions so holidays never exist; blocking check gates downstream assets):

```python
import dagster as dg
from pipeline import calendar_cache, eodhd, store
from pipeline.guards import bulk_guard

sessions = dg.DynamicPartitionsDefinition(name="eodhd_exchange_session")       # "US|2026-10-23"

@dg.asset(partitions_def=sessions, pool="eodhd_api",                            # Dagster ≥1.10
          retry_policy=dg.RetryPolicy(max_retries=3, delay=60, backoff=dg.Backoff.EXPONENTIAL))
def eod_bulk(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    exchange, session = context.partition_key.split("|")
    rows = eodhd.bulk_eod(exchange, session)       # raises dg.Failure(allow_retries=False) on 401/402/403/422
    state = bulk_guard(rows, session)
    if state == "NOT_YET_AVAILABLE":
        raise dg.RetryRequested(max_retries=12, seconds_to_wait=1200)
    if state != "COMMIT":
        raise dg.Failure(description=state, allow_retries=False)
    return dg.MaterializeResult(metadata={"rows": len(rows), "capture_id": store.stage_partition(exchange, session, rows)})

@dg.asset_check(asset=eod_bulk, blocking=True)
def eod_bulk_quality(context) -> dg.AssetCheckResult:
    result = store.run_checks(context)              # §4; FAIL blocks downstream materialization
    return dg.AssetCheckResult(passed=result.passed, severity=result.severity, metadata=result.metadata)

@dg.sensor(asset_selection=[eod_bulk], minimum_interval_seconds=900)
def due_partitions(context: dg.SensorEvaluationContext):
    due = calendar_cache.due_partition_keys()        # cached calendar; no API call here
    known = set(context.instance.get_dynamic_partitions("eodhd_exchange_session"))
    new = [k for k in due if k not in known]
    return dg.SensorResult(
        run_requests=[dg.RunRequest(partition_key=k, run_key=k) for k in due if not store.committed(k)],
        dynamic_partitions_requests=[sessions.build_add_request(new)] if new else [])
```

**Prefect** (global concurrency limit shared by every flow using the key):

```python
from prefect import flow, task
from prefect.concurrency.sync import concurrency
from pipeline import calendar_cache
from pipeline.errors import NotYetAvailable, TransientHTTPError   # raised by your client wrapper

def transient_only(task, task_run, state) -> bool:      # retry NotYetAvailable / 429 / 5xx only
    try:
        state.result()
    except (NotYetAvailable, TransientHTTPError):
        return True
    except Exception:
        return False
    return False

@task(retries=8, retry_delay_seconds=1200, retry_condition_fn=transient_only)
def load_bulk(exchange: str, session: str):
    with concurrency("eodhd-api", occupy=1):           # create once: limit = pool slots
        ...

@flow
def eod_daily(exchange: str):
    session = calendar_cache.latest_due_session(exchange)
    if session is None:
        return "no session"
    load_bulk(exchange, session)
```

**Connector frameworks** (Airbyte, Singer taps, dlt): one stream per endpoint family; slice per exchange-day
(bulk) or per listing (history); cursor = `date` with a lookback of at least the refinement horizon; primary
key `(code, exchange, date)` for prices, `(code, exchange, date, type)` for actions; full refresh for symbol
lists. Keep the token in the connector's secret store. A generic HTTP connector does not know the call
weights: budget it with §1.5 and give it the same pool.

**Mage** (same concepts, block types instead of tasks):

| Concept (§1) | Mage |
|---|---|
| Fetch | a **data loader** block calls bulk EOD and applies the §1.3 date guard; `NOT_YET_AVAILABLE` raises an ordinary exception so the block retry runs |
| Normalize | a **transformer** block (types, units, `listing_id` resolution) |
| Publish | an **exporter** block that writes the staged partition only after the §4 checks pass, then the dbt build step below, then the §15 swap |
| Schedule after close + lag | a schedule trigger in the exchange timezone at close + lag; the loader still asks the cached calendar whether today is a session |
| Never retry 401/403/422 | the loader checks the status and raises a non-retried failure (set the block's retry count to 0 for these paths, or check a breaker row before calling) |
| 402 | breaker row checked at the start of the loader |
| One pool per key | one shared limiter (the §1.5 token bucket in a database or Redis) used by every pipeline on the key; Mage's per-pipeline concurrency settings alone do not cap the key across pipelines |

Verify block retry and concurrency setting names against the installed Mage version.

### dbt build step between publish and swap

The scheduler runs one more step after `validate_and_publish` and before the serving-view swap (§15):
`dbt build` on the models that depend on the new partition.

- **`build` vs `run`.** `dbt run` only materializes models. `dbt build` runs seeds, models, snapshots and
  tests in DAG order, and skips every node downstream of a failing error-severity test. Use `build` so a
  failing test stops the swap.
- **The model table is already rewritten when a test fails.** dbt materializes a model and then tests it.
  A failed test leaves the new rows in the mart table (verified with dbt-duckdb 1.11 / dbt-core 1.12, run
  below). Serving views must therefore point at a published copy that only the swap changes, never at the
  dbt model table itself.
- **Selection.** Select by tag for the daily path: `dbt build --select tag:eodhd_daily`. Declare the tag in `dbt_project.yml` (`models: {my_project: {staging: {+tags: ['eodhd_daily']}, marts: {+tags: ['eodhd_daily']}}}`) or as a named selector in `selectors.yml` (`selectors: [{name: eodhd_daily, definition: {method: tag, value: eodhd_daily}}]`, run with `dbt build --selector eodhd_daily`); a model without the tag is silently skipped by the daily run. `state:modified+`
  selects on **code** changes (CI, §13). It does not see data restatements. Restated listings come from
  §1.8 and reach the incremental models as a variable: `--vars '{session: 2026-10-23, lookback_days: 14,
  restated_listings: [101, 205]}'`. The model adds `or listing_id in (...)` to its incremental filter (§3).
- **Timeout per task.** Airflow `execution_timeout=timedelta(minutes=45)` on the task; Prefect
  `@task(timeout_seconds=2700)`; Dagster has no per-asset timeout argument, so set `timeout=` on the
  subprocess (and a run-level `dagster/max_runtime` tag if run monitoring is enabled); cron: the same
  `timeout=` in the runner. A timeout is a failure: no swap.
- **Exit codes.** 0 = success; 1 = a model or test failed or errored; 2 = dbt itself failed. Only 0 lets the
  swap run.

```python
import json, subprocess
import duckdb

class BuildFailed(RuntimeError):
    pass

def dbt_build(session, restated_listings, project_dir, timeout_s=2700, dbt="dbt"):
    """Run after validate_and_publish; returns only if every error-severity test passed."""
    vars_ = {"session": session, "lookback_days": 14, "restated_listings": sorted(restated_listings)}
    cmd = [dbt, "build", "--select", "tag:eodhd_daily", "--vars", json.dumps(vars_),
           "--project-dir", project_dir, "--profiles-dir", project_dir]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as e:
        raise BuildFailed(f"dbt build timed out after {timeout_s}s") from e
    if p.returncode != 0:            # 1 = a model/test failed or errored, 2 = dbt itself failed
        raise BuildFailed(f"dbt build exit {p.returncode}: {p.stdout[-400:]}")

def publish(db_path, version):
    """Copy the built mart to an immutable version and swap the serving view (section 15)."""
    con = duckdb.connect(db_path)
    con.execute("create schema if not exists serving")
    con.execute(f"create table marts.fct_price_daily_{version} as select * from marts.fct_price_daily")
    con.execute("begin")
    con.execute(f"create or replace view serving.price_daily as select * from marts.fct_price_daily_{version}")
    con.execute("commit")
    con.close()
```

Wiring per orchestrator (the function is the same; only the wrapper changes):

```python
# Airflow: ... >> validate_and_publish(s) >> dbt_build_task(s) >> swap_serving(s)
@task(execution_timeout=timedelta(minutes=45), retries=0)
def dbt_build_task(session: str):
    dbt_build(session, store.restated_listings(session), DBT_DIR)    # BuildFailed -> task failed, no swap

# Prefect
@task(timeout_seconds=2700, retries=0)
def dbt_build_task(session: str):
    dbt_build(session, store.restated_listings(session), DBT_DIR)

# Dagster: an asset downstream of eod_bulk; the blocking check on eod_bulk already gates it
@dg.asset(deps=[eod_bulk], partitions_def=sessions)
def marts_built(context):
    _, session = context.partition_key.split("|")
    dbt_build(session, store.restated_listings(session), DBT_DIR, timeout_s=2700)

# cron runner (tick.py), after commit_partition(...)
dbt_build(session, restated, DBT_DIR); publish(DB_PATH, f"v{run_no}")
```

On a larger warehouse, replace the `create table … as select` copy with a zero-copy clone or a
versioned schema where the engine has one; the rule is the same: the swap is the only publish.

### Acceptance checks

- The same partition fired twice (manual + scheduled) produces one committed version.
- A planted OHLC violation (high < low) makes `dbt build` exit 1; `publish` does not run and the serving
  view still returns the previous version (run: serving rows 2 with max date 2026-10-23, while the dbt mart
  table already held 3 rows up to 2026-10-26).
- A listing passed in `restated_listings` is rebuilt over its full history; other listings outside the
  lookback are untouched (run: listing 2's 2026-01-05 close, outside the 14-day lookback, changed
  5.2 → 5.3 in the published view when listing 2 was passed).
- A `dbt build` that exceeds its timeout fails the task and no swap happens.
- The daily DAG for an exchange on its holiday shows "skipped", not "failed".
- With the pool at 8 slots, no more than 8 EODHD requests are in flight across all DAGs (log check).
- A forced 402 in one DAG stops the others on the same key before their next request.

---

## 3. dbt/SQL transformation layer

**Use when** the user builds staging → intermediate → mart models over captured EODHD data and needs them
to stay correct under restatements. The one-paragraph rule in [storage.md](storage.md) is implemented here.

**EODHD inputs**: captured rows from `eod` / bulk EOD, `div` / bulk dividends, `splits` / bulk splits,
`exchange-symbol-list` snapshots (`Code`, `Name`, `Exchange`, `Currency`, `Type`, `Isin`), cached calendars,
optionally `fundamentals` sections. Each raw row carries `capture_id`, `retrieved_at`, endpoint and request
parameters (no token).

### Layout

| Layer | Model | Grain / key | Materialization | Content |
|---|---|---|---|---|
| source | `eodhd_raw.*` | as loaded | — | `loaded_at_field: retrieved_at` |
| staging | `stg_eodhd__eod` | code + exchange + date + capture | view | typed, snake_case, `price_currency`, `price_unit_multiplier` from the symbol list (GBX/ZAC → 0.01) |
| staging | `stg_eodhd__dividends` | code + exchange + ex_date + capture | view | strings → decimals; `value` vs `unadjusted_value`; `distribution_currency` |
| staging | `stg_eodhd__splits` | code + exchange + ex_date + capture | view | `"new/old"` → `ratio = new/old` |
| intermediate | `int_listing_master` / `dim_listing` | listing_id (SCD2) | table | active + delisted, `_old` handling (§8) |
| intermediate | `int_eod_current` | listing_id + session_date | incremental | latest capture per key, `capture_kind` = bulk / full_history / refinement |
| intermediate | `int_corporate_actions` | listing_id + ex_date + type | incremental | splits and dividends resolved to `listing_id`, with `retrieved_at` |
| intermediate | `int_split_factor` | listing_id + session_date | incremental | `S(d) = Π r` over splits with ex_date > d |
| mart | `fct_price_daily` | listing_id + session_date + basis | incremental | basis ∈ `raw`, `split_adjusted`, `total_return` |
| mart | `fct_dividend_cash` | listing_id + ex_date + seq | incremental | unadjusted cash per share in its own currency |
| mart | `dim_exchange_calendar` | exchange + date | table | `is_session`, `close_utc`, `sla_due_utc` |

Basis definitions (per day `d`, `k(d) = adjusted_close/close`, `S(d)` cumulative later split ratio):

| Basis | open/high/low/close | volume |
|---|---|---|
| `raw` | as delivered | `volume / S(d)` (EODHD volume is split-adjusted; this is derived) |
| `split_adjusted` | raw ÷ `S(d)` | `volume` as delivered |
| `total_return` | O/H/L × `k(d)`, close = `adjusted_close` | `volume` as delivered |

### Incremental strategy

Rows to (re)build on each run = sessions inside a lookback window **plus** the full history of every listing
whose series was restated since the last build (new action, full-history re-pull, or a unit/currency change
in `dim_listing`).

```sql
-- models/marts/fct_price_daily.sql
{{ config(
    materialized='incremental',
    unique_key=['listing_id', 'session_date', 'basis'],
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}

with cur as (
    select * from {{ ref('int_eod_current') }}
    {% if is_incremental() %}
    where session_date >= {{ dbt.dateadd('day', -var('lookback_days', 14), 'current_date') }}
       or listing_id in (
            select listing_id from {{ ref('int_eod_current') }}
            where capture_kind = 'full_history'
              and retrieved_at > (select max(source_retrieved_at) from {{ this }})
            union
            select listing_id from {{ ref('int_corporate_actions') }}
            where retrieved_at > (select max(source_retrieved_at) from {{ this }})
       )
    {% endif %}
),
f as (
    select c.*, coalesce(s.split_factor_after, 1.0) as s_after,
           case when c.close > 0 and c.adjusted_close > 0 then c.adjusted_close / c.close end as k
    from cur c
    left join {{ ref('int_split_factor') }} s using (listing_id, session_date)
)
select listing_id, session_date, 'raw' as basis, open, high, low, close,
       volume / s_after as volume, price_currency, price_unit_multiplier, capture_id,
       retrieved_at as source_retrieved_at
from f
union all
select listing_id, session_date, 'split_adjusted', open / s_after, high / s_after, low / s_after,
       close / s_after, volume, price_currency, price_unit_multiplier, capture_id, retrieved_at
from f
union all
select listing_id, session_date, 'total_return', open * k, high * k, low * k, adjusted_close,
       volume, price_currency, price_unit_multiplier, capture_id, retrieved_at
from f
```

Notes:

- `lookback_days` covers the refinement run and late fixes (14 calendar days ≈ 10 sessions); justify it from
  the observed revision lag in your capture diff log, not by habit.
- `delete+insert` with the full key set of a rebuilt listing replaces all its rows. A row that disappears
  upstream (a removed bad bar) survives an incremental run; the scheduled `--full-refresh` (weekly or
  monthly) and the parity test (§9, §10) catch it. Add a `pre_hook` deleting rebuilt listings if that lag is
  unacceptable.
- `total_return` rows are null where `close` is 0 or missing: the factor is undefined, not 1.
- Never filter on `session_date > (select max(session_date) from {{ this }})`: it misses every restatement.
- The scheduler calls this layer with `dbt build` and passes the restated listings as a variable
  (§2, "dbt build step between publish and swap"). Replace the `capture_kind` subquery with
  `listing_id in ({{ (var('restated_listings', []) + [-1]) | join(', ') }})` when the list comes from the
  scheduler (the `-1` sentinel keeps an empty list valid SQL; tested with dbt-core 1.12).

**SQLMesh equivalent** (checked with SQLMesh 0.236 on DuckDB):

```sql
-- models/fct_price_daily.sql
MODEL (
  name marts.fct_price_daily,
  kind INCREMENTAL_BY_UNIQUE_KEY (
    unique_key (listing_id, session_date, basis),
    lookback 10                       -- re-process the last 10 daily intervals each run (refinement + late fixes)
  ),
  cron '@daily',
  grain (listing_id, session_date, basis),
  audits (
    unique_combination_of_columns(columns := (listing_id, session_date, basis)),   -- Q1
    assert_ohlc_bounds,                                                            -- Q2
    accepted_range(column := volume, min_v := 0),                                  -- Q4
    assert_factor_jump_has_action(blocking := false)                               -- Q11, warn only
  )
);

WITH cur AS (
  SELECT *
  FROM eodhd.int_eod_current
  WHERE session_date BETWEEN @start_ds AND @end_ds
     OR listing_id IN (SELECT listing_id FROM eodhd.restated_listing
                       WHERE restated_at BETWEEN @start_ts AND @end_ts)   -- whole history of restated listings
)
SELECT listing_id, session_date, 'raw' AS basis, open, high, low, close, volume, retrieved_at
FROM cur
UNION ALL
SELECT listing_id, session_date, 'total_return', open * adjusted_close / close, high * adjusted_close / close,
       low * adjusted_close / close, adjusted_close, volume, retrieved_at
FROM cur
WHERE close > 0 AND adjusted_close > 0
```

The SQLMesh audits above cover Q1, Q2, Q4 and Q11 only; keep the remaining checks (§4) in the separate quality suite that gates the view swap.

```sql
-- audits/assert_ohlc_bounds.sql (one AUDIT per file; returns the violating rows)
AUDIT (name assert_ohlc_bounds);
SELECT * FROM @this_model
WHERE open > 0 AND high > 0 AND low > 0 AND close > 0
  AND (low > LEAST(open, close) OR high < GREATEST(open, close))
```

`assert_factor_jump_has_action` is the §4 Q11 query with `eod_daily` replaced by `@this_model` (joining the
`raw` and `total_return` rows to get `k`). Audit → check mapping: `unique_combination_of_columns` = Q1, the
custom OHLC audit = Q2, `accepted_range(min_v := 0)` = Q4, the factor audit = Q11 (non-blocking, so WARN).

Restatement:

- **Listing-scoped** (a new dividend or split for some listings): write the listings to
  `eodhd.restated_listing` with `restated_at`, then a normal `sqlmesh run` rebuilds their full history
  through the `OR listing_id IN (...)` branch and merges on the unique key. Run: listing 1's
  `total_return` rows for January changed from 99.0/100.0 to 98.0/99.0 after a restatement row; listing 2
  was untouched.
- **Whole model** (`sqlmesh plan --restate-model marts.fct_price_daily`): SQLMesh restates
  `INCREMENTAL_BY_UNIQUE_KEY` models over their **full history** only; `--start`/`--end` do not narrow it
  (the run backfilled 2026-01-05 → 2026-10-25 for a one-day request). Use it as the equivalent of dbt
  `--full-refresh`.
- **A failed blocking audit does not roll back the rows.** In the run, the restatement wrote a bad row,
  the OHLC audit failed and the plan failed, but the model's view already returned the bad row. As with
  dbt, publish through the §15 swap and point consumers at the swapped view, not at the SQLMesh model.

### Source freshness and tests per layer

```yaml
# models/sources.yml — "loader alive" freshness per exchange (one table entry per exchange, same identifier)
sources:
  - name: eodhd_raw
    loaded_at_field: retrieved_at
    tables:
      - name: eod_rows_us
        identifier: eod_rows
        freshness:
          filter: "exchange = 'US'"
          warn_after: {count: 26, period: hour}
          error_after: {count: 74, period: hour}    # spans a normal weekend; long holidays still warn
```

Time-based freshness cannot know holidays, so the authoritative check is calendar-aware:

```sql
-- tests/assert_sessions_fresh.sql (fails with rows)
with expected as (
    select exchange, max(session_date) as expected_last
    from {{ ref('dim_exchange_calendar') }}
    where is_session and sla_due_utc <= current_timestamp
    group by exchange),
actual as (
    select exchange, max(session_date) as last_loaded
    from {{ ref('int_eod_current') }} group by exchange)
select e.exchange, e.expected_last, a.last_loaded
from expected e left join actual a using (exchange)
where a.last_loaded is null or a.last_loaded < e.expected_last
```

| Layer | Test | Severity |
|---|---|---|
| staging | `unique` / `not_null` on (code, exchange, date, capture_id); `accepted_values` for currency codes, unit multiplier {1, 0.01}, instrument type | error |
| staging | split ratio parses to a positive number; dividend amount ≥ 0 | error |
| intermediate | `relationships` to `dim_listing`; one current row per `listing_id` in `dim_listing` | error |
| intermediate | ISIN join fan-out (below) | error |
| mart | unique (listing_id, session_date, basis) | error |
| mart | `low ≤ least(open, close)` and `high ≥ greatest(open, close)` where all four > 0 | warn (fail above a share) |
| mart | `k > 0`; `k` constant between action dates (§4 factor check) | warn |
| mart | duplicate dividends on (listing, ex_date, unadjusted_value, currency) | warn (several distributions can be combined or listed separately) |
| mart | calendar-aware freshness (above) | error after the SLA |

```sql
-- tests/assert_isin_join_no_fanout.sql: one ISIN often has several listings (cross-listings, venues)
select h.holding_id, count(*) as matches
from {{ ref('stg_user__holdings') }} h
join {{ ref('dim_listing') }} l on l.isin = h.isin and l.is_current
group by h.holding_id
having count(*) > 1
```

Fix fan-out with an explicit rule (holding's exchange and currency first, then primary listing), never with
`distinct`. Rank tests by the decision they protect: a duplicated dividend inflates income and yield; a
missing company name does not change a number.

Use `config(severity='warn', warn_if='>0', error_if='>50', store_failures=true)` on heuristic tests so
failures are stored for trending (§4). Slim CI: `dbt build --select state:modified+ --defer --state
prod-artifacts/` against a DuckDB profile loaded with synthetic fixtures (§10, §13).

### Acceptance checks

- Re-running a day with unchanged captures is a no-op (row hashes identical).
- A fixture with a new dividend for one listing rewrites all of that listing's `total_return` rows and no
  other listing's rows.
- A late correction inside the lookback updates in place; one outside it is caught by the full refresh and
  reported by the incremental-vs-full parity test.
- The fan-out test fails on a fixture ISIN listed on two exchanges.
- The calendar-aware freshness test passes on an exchange holiday and a weekend.

---

## 4. Executable data-quality suite

**Use when** the user wants the invariants of [quality.md](quality.md) as runnable checks with thresholds,
severities, quarantine and a history. Checks run on a **staged partition** (exchange × session) before it is
published (write-audit-publish).

**EODHD inputs**: the staged bulk rows, the current normalized table, the latest symbol-list snapshot
(expected universe), the action ledger, the calendar.

### Check catalogue

| # | Check | Definition | Default severity |
|---|---|---|---|
| Q1 | Key uniqueness | no duplicate (listing_id, session_date) in the partition | FAIL |
| Q2 | OHLC bounds | where O, H, L, C > 0: `L ≤ min(O, C)`, `H ≥ max(O, C)` | WARN per row; FAIL if > 0.5% of rows |
| Q3 | Incomplete bar | O, H or L null/0 while C > 0 | WARN (keep; do not repair) |
| Q4 | Volume | `volume ≥ 0`; null kept as null | FAIL if negative |
| Q5 | Freshness | partition date = expected session from the calendar | FAIL after SLA |
| Q6 | Completeness | `|returned ∩ expected| / |expected|`, expected = listings in the latest symbol-list snapshot of in-scope types that traded on ≥ 15 of the trailing 20 sessions | WARN < 0.98; FAIL < 0.90 |
| Q7 | Row-count z-score | `z = (n_t − mean₂₀)/sd₂₀`, trailing 20 sessions excluding t, sample sd | WARN abs(z) ≥ 3; FAIL ≥ 6 |
| Q8 | Volume z-score | same on `ln(Σ volume + 1)` (volume is heavy-tailed) | WARN abs(z) ≥ 3 |
| Q9 | Null-rate drift | per column: `null_rate_t − mean₂₀(null_rate)` | WARN > 2 pp; FAIL > 10 pp |
| Q10 | Stuck price with volume | ≥ 5 consecutive sessions with identical close and volume > 0 | WARN |
| Q11 | Factor jump without action | `f = k(t−1)/k(t)` differs from 1 beyond tolerance and no split/dividend has ex-date in (t−1, t] | WARN (FAIL if many listings) |
| Q12 | Unit/currency change | `Currency` or unit multiplier of a listing changed between symbol-list snapshots | WARN; block publish of derived values for that listing |
| Q13 | Identifier check digits | `Isin` from symbol lists / ID mapping passes ISO 6166 (letters → 10..35, then Luhn); CUSIP passes its modulus-10 check; for `US`/`CA` ISINs, `ISIN[2:11] = CUSIP` | WARN (keep the value, never "fix" a digit; resolve via `/api/id-mapping`) |
| Q14 | Per-asset-class move | one-session move above the class limit (table below) on `adjusted_close`; a raw-close ratio within 5% of ×100 or ×0.01 is a unit shift | WARN → review queue; never edits the value |

Q14 limits (absolute one-session return on `adjusted_close`; starting points — set each class at about the
99.9th percentile of its trailing two-year moves in your archive, and scale leveraged ETFs by leverage):

| Class key (assigned from symbol-list `Type` and exchange code) | Limit | Note |
|---|---|---|
| `Common Stock` | 0.30 | penny stocks need a higher limit or a price floor |
| `Preferred Stock` | 0.20 | |
| `ETF` | 0.15 | leveraged/inverse: × leverage |
| `FUND` (mutual fund NAV) | 0.10 | |
| `INDEX` (`.INDX`) | 0.10 | |
| `FOREX` (`.FOREX`) | 0.05 | pegged or devaluation-prone pairs need their own limit |
| `CRYPTO` (`.CC`) | 0.35 | 365-day calendar |
| `BOND` (`.BOND`) | 0.10 | `.GBOND` rows are yields: compare an absolute change (e.g. > 0.5 pp), not a return |

A move on an action ex-date is reported as `move_with_action` (expected for spin-offs and specials), not
suppressed.

```python
import math

def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            d = d - 9 if d > 9 else d
        total += d
    return total % 10 == 0

def isin_ok(isin: str) -> bool:
    """ISO 6166: 2 letters + 9 alphanumerics + 1 check digit; letters -> 10..35, then Luhn."""
    s = (isin or "").strip().upper()
    if len(s) != 12 or not s[:2].isalpha() or not s[2:11].isalnum() or not s[11].isdigit():
        return False
    return _luhn_ok("".join(str(int(c, 36)) for c in s))

def cusip_ok(cusip: str) -> bool:
    """CUSIP: 8 characters + check digit; letters -> 10..35, * @ # -> 36 37 38; double every 2nd value."""
    s = (cusip or "").strip().upper()
    if len(s) != 9 or not s[8].isdigit():
        return False
    total = 0
    for i, c in enumerate(s[:8]):
        if c.isdigit():
            v = int(c)
        elif c.isalpha():
            v = ord(c) - 55
        elif c in "*@#":
            v = 36 + "*@#".index(c)
        else:
            return False
        if i % 2 == 1:
            v *= 2
        total += v // 10 + v % 10
    return (10 - total % 10) % 10 == int(s[8])

MOVE_LIMIT = {"Common Stock": 0.30, "Preferred Stock": 0.20, "ETF": 0.15, "FUND": 0.10,
              "INDEX": 0.10, "FOREX": 0.05, "CRYPTO": 0.35, "BOND": 0.10}

def move_review(rows, asset_class, actions=frozenset(), limit=None):
    """rows: [(date, close_raw, adjusted_close)] sorted; actions: dates with a split/dividend ex-date.
    Returns review items; never edits a value."""
    lim = limit if limit is not None else MOVE_LIMIT.get(asset_class, 0.20)
    out = []
    for (d0, c0, a0), (d1, c1, a1) in zip(rows, rows[1:]):
        if not (c0 and c1 and c0 > 0 and c1 > 0):
            continue
        raw = math.log(c1 / c0)
        if abs(abs(raw) - math.log(100)) < 0.05 and d1 not in actions:
            out.append((d1, "unit_shift_x100", round(c1 / c0, 4)))
            continue
        r = (a1 / a0 - 1) if (a0 and a1 and a0 > 0 and a1 > 0) else (c1 / c0 - 1)
        if abs(r) > lim:
            out.append((d1, "move_with_action" if d1 in actions else "move_no_action", round(r, 4)))
    return out
```

Thresholds are starting points. Calibrate per exchange: compute each metric over the last 60 sessions and
place WARN near the 99th percentile; early-close days and index rebalancing days legitimately move row counts
and volume. Robust alternative for Q7/Q8: `(x − median₂₀) / (1.4826 · MAD₂₀)`.

Tolerance for Q11: prices have at most four decimals, so `adjusted_close` carries rounding error up to
0.00005 and `k` up to `0.00005/close`. Flag when
`abs(f − 1) > 0.001 + 0.0001 · (1/close_t + 1/close_{t−1})`; otherwise penny stocks flood the report.

### SQL forms (DuckDB/PostgreSQL)

```sql
-- Q11 adjustment-factor jump without a corporate action
with k as (
  select listing_id, session_date, close,
         adjusted_close / close                as k,
         lag(adjusted_close / close) over w    as k_prev,
         lag(close) over w                     as close_prev,
         lag(session_date) over w              as prev_date
  from eod_daily
  where close > 0 and adjusted_close > 0
  window w as (partition by listing_id order by session_date))
select listing_id, session_date, k_prev / k as backward_factor
from k
where k_prev is not null
  and abs(k_prev / k - 1) > 0.001 + 0.0001 * (1 / close + 1 / close_prev)
  and not exists (select 1 from corporate_action a
                  where a.listing_id = k.listing_id
                    and a.ex_date > k.prev_date and a.ex_date <= k.session_date);

-- Q10 stuck price with volume (gaps-and-islands)
with x as (
  select listing_id, session_date,
         case when close = lag(close) over w and volume > 0 then 0 else 1 end as brk
  from eod_daily window w as (partition by listing_id order by session_date)),
g as (select *, sum(brk) over (partition by listing_id order by session_date) as grp from x)
select listing_id, min(session_date) as run_start, max(session_date) as run_end, count(*) as sessions
from g group by listing_id, grp
having count(*) >= 5;

-- Q7/Q8 z-scores against the trailing 20 sessions (exclude the current one)
with daily as (
  select exchange, session_date, count(*) as n_rows, ln(sum(volume) + 1) as log_vol
  from eod_daily group by 1, 2),
z as (
  select *, avg(n_rows) over w as mu_n, stddev_samp(n_rows) over w as sd_n,
            avg(log_vol) over w as mu_v, stddev_samp(log_vol) over w as sd_v, count(*) over w as k
  from daily
  window w as (partition by exchange order by session_date rows between 20 preceding and 1 preceding))
select exchange, session_date, n_rows,
       (n_rows - mu_n) / nullif(sd_n, 0) as z_rows,
       (log_vol - mu_v) / nullif(sd_v, 0) as z_log_volume
from z where k = 20;

-- Q6 completeness for one staged partition (:ex = exchange, last_20_sessions = your calendar view)
with liquid as (
  select listing_id from eod_daily
  where exchange = :ex and session_date in (select session_date from last_20_sessions(:ex))
  group by listing_id having count(*) >= 15),
expected as (
  select l.listing_id from liquid l join dim_listing d using (listing_id)
  where d.is_current and not d.delisted_list and d.type in ('Common Stock', 'ETF'))
select cast(count(s.listing_id) as double precision) / nullif(count(*), 0) as completeness
from expected e left join staged_partition s using (listing_id);
```

### Tool equivalents

| Check | dbt | Great Expectations (1.x names) | Soda CL |
|---|---|---|---|
| Q1 | `unique` on a key expression / `dbt_utils.unique_combination_of_columns` | `ExpectCompoundColumnsToBeUnique` | `duplicate_count(listing_id, session_date) = 0` |
| Q2 | singular test (SQL above) | `ExpectColumnPairValuesAToBeGreaterThanB` (high ≥ low, `or_equal`) + custom SQL | `failed rows` with the SQL |
| Q4 | `dbt_utils.accepted_range` min 0 | `ExpectColumnValuesToBeBetween` min 0 | `invalid_count(volume) = 0` with `valid min: 0` |
| Q5 | calendar-aware singular test (§3) | `ExpectColumnMaxToBeBetween` on `session_date` | `freshness(retrieved_at) < 26h` (+ calendar SQL) |
| Q6–Q11 | singular tests with `warn_if` / `error_if` | `UnexpectedRowsExpectation` with the SQL | `failed rows` / user-defined metric with the SQL |
| Q9 | custom test per column | `ExpectColumnValuesToNotBeNull` with `mostly` | `missing_percent(col) < x%` |

Plain SQL plus a results table is enough for one person's archive; adopt a framework when several people own
the checks.

### Warn versus fail, quarantine, result history

1. Load the partition into `staging.eod_<ex>_<session>`; run all checks; write one result row per check.
2. Any FAIL → move the staged rows to `quarantine` with the run id, keep the raw capture, alert; the serving
   view keeps the previous good state. WARN → publish, setting `quality_flags` on affected rows.
3. Re-running after a fix re-evaluates the same capture (or a new one) and publishes atomically (§15).

```sql
create table dq_result (
  run_id        uuid        not null,
  capture_id    uuid        not null,
  exchange      text        not null,
  session_date  date        not null,
  check_id      text        not null,      -- 'Q11'
  check_version text        not null,
  status        text        not null check (status in ('PASS', 'WARN', 'FAIL', 'NOT_TESTED')),
  observed      double precision,
  threshold     text,
  n_failed      integer,
  sample_keys   jsonb,                      -- up to 20 listing/date keys for triage
  checked_at    timestamptz not null default now(),
  primary key (run_id, check_id)
);
```

Trend `dq_result` per exchange and check; a check that WARNs every day needs recalibration, not muting.

### Acceptance checks

- Synthetic fixtures trigger each check exactly once: a duplicate row (Q1), `high < low` (Q2), negative
  volume (Q4), a listing missing from a liquid set (Q6), a 0.5 factor change with no action (Q11), a
  10-session flat close with volume (Q10). The fixture dividend with a matching action is not flagged.
- A FAIL partition is never visible through the serving view; a WARN partition is, with flags.
- Q13: `isin_ok` is true for `US0378331005`, `US5949181045`, `GB0002634946` and false for `US0378331006`
  (bad check digit) and `US037833100` (11 characters); `cusip_ok` is true for `037833100`, `594918104`,
  `38259P508` and false for `037833101`; `US0378331005` embeds `037833100`.
- Q14 on rows `(100/100), (62/62), (31.5/63.0, 2:1 split ex-date), (3150/6300), (31.6/63.2)` for a common
  stock returns `move_no_action −0.38` on day 2, nothing on the split day, and `unit_shift_x100` on days 4
  (ratio 100) and 5 (ratio 0.01). With a 0.5 limit only the two unit shifts remain.
- Every result row references its capture id; re-running the suite on the same capture reproduces it.

---

## 5. Data SLAs, ops dashboard, failure taxonomy, incident record

**Use when** a pipeline has users who need to know whether today's numbers are usable, or the user asks for
monitoring, alerting or a post-incident write-up.

### SLA per exchange

An SLA here is the user's internal target derived from documented typical timing, never an EODHD guarantee.

| Dataset | Freshness SLA (state "complete") | Warn | Completeness SLA |
|---|---|---|---|
| US EOD provisional | session committed by 18:00 ET | 17:00 ET | Q6 ≥ 0.98 |
| US EOD refined | refinement run done by 07:30 ET next day | 06:45 ET | funds/OTC present |
| LSE / XETRA / Euronext / HK | local close + 4 h | close + 3 h 15 | Q6 ≥ 0.98 |
| Actions (all) | 1 h after the exchange EOD SLA | — | dated rows only |
| Fundamentals (weekly) | weekly run done by Sunday 12:00 UTC | — | ≥ 99% of listings returned 200 |

Record the targets, the Q6 completeness floor, each check's severity and threshold, and the owner in the
dataset contract (`freshness_sla`, `completeness_min`, `checks`, `owner` in
[assets/dataset-contract.json](../assets/dataset-contract.json)) so the checks and the dashboard read one source.

SLO = share of sessions meeting the SLA over the trailing 20 sessions (e.g. ≥ 95%). Page only on SLA breach
and on FAIL checks; send a recovery notice; deduplicate alerts per (exchange, session, cause).

### Ops dashboard panels

| Panel | Source |
|---|---|
| Last committed session per exchange vs expected | `committed_partition`, calendar |
| Calls spent today vs `dailyRateLimit`, by job class; forecast to 00:00 GMT | budget ledger + `/api/user` (0 calls) |
| Requests/min vs `X-RateLimit-Limit`; 429 count | request log |
| Breaker state per key / Marketplace product | breaker table |
| Failed, late and quarantined partitions | partition state, `dq_result` |
| Listings re-pulled after actions today; restatements not yet visible | re-pull queue |
| Stale serving outputs (dashboards built from a session older than expected) | serving view metadata |
| Check trends (WARN/FAIL counts by check) | `dq_result` |

### Failure taxonomy

| Class | Signal | Retry | First action | See |
|---|---|---|---|---|
| Auth | 401, no rate-limit headers | no | fix token string; check regeneration (old key revoked at once) | [casebook](support-casebook.md) §1 |
| Entitlement | 403 on an endpoint family or symbol | no | compare plan matrix; wrong path (`/api/` missing)? | [plans-limits](plans-limits.md) |
| Daily quota | 402 | no (until 00:00 GMT) | breaker; review job costs | §1.5 |
| Minute rate | 429 + `Retry-After` | yes | lower pool slots / rate | §1.5 |
| Marketplace quota | 429 on `/api/mp/…` | wait for window | separate budget | [plans-limits](plans-limits.md) |
| Bad request | 422 | no | fix range/date/JSON quotes | — |
| Unknown symbol | 404 (charged) | no | rename, `_old`, delisted list | [identity](identity.md) |
| Not yet published | 200, bulk date < session | yes, in window | wait; refinement run | §1.3 |
| Empty | 200 + `[]` | no | validate dates; probe one symbol | — |
| Schema change | missing/new keys, HTML body, type change | no | keep capture; stop normalization; contract diff | [operations](operations.md) |
| Restatement | factor change with action; full-series diff | — | full-symbol rebuild | §1.8 |
| Unexplained factor jump | Q11 | — | re-pull; if persistent, minimal report | [quality](quality.md) |
| Identity | code reused (`_old`), rename, venue move | — | SCD2 + listing resolution | §8 |
| Units | GBX/GBP or ZAC/ZAR change | — | block derived values; verify metadata | [data-semantics](data-semantics.md) |
| Discontinued | listing stopped updating long ago | — | mark discontinued; not "delayed" | [coverage-notes](coverage-notes.md) |
| Transport | timeout, reset, 5xx | yes, bounded | backoff; check status page | — |

### Incident record

```text
id / title / severity
detected_at (UTC), detected_by (check id or person), first_bad_capture_id, last_good_capture_id
affected: exchanges, sessions, listings (count + sample), datasets, downstream outputs
evidence: requests (no token), response hashes, observed vs expected values, check results
class: one row of the taxonomy above
fix: code/config change (commit id), or "source anomaly reported" with the minimal reproduction
reprocessing scope: partitions replayed from captures vs re-requested, calls spent, swap time
consumer notice: who was told, when, what changed
follow-up: new check/threshold, test fixture added
```

Do not write an EODHD correction timetable or a cause for a source anomaly into the record unless evidence
supports it.

---

## 6. Storage DDL with correction-friendly keys

**Use when** the user picks a storage engine and needs upsert semantics that keep corrections and captures.
Pattern for every engine: an **append-only observation table** keyed by `(listing_id, session_date,
capture_id)` and a **current table** keyed by `(listing_id, session_date)` updated only when the row hash
changes. Raw response bytes stay in files ([storage.md](storage.md)).

**PostgreSQL**

```sql
create table md.eod_observation (
  listing_id            bigint        not null,
  session_date          date          not null,
  capture_id            uuid          not null,
  open                  numeric(20,6),
  high                  numeric(20,6),
  low                   numeric(20,6),
  close                 numeric(20,6),
  adjusted_close        numeric(20,6),
  volume                numeric(24,4),                -- split-adjusted as delivered; nullable
  price_currency        text          not null,       -- GBX, ZAC kept as delivered
  price_unit_multiplier numeric(8,6)  not null,       -- 0.01 for GBX/ZAC
  row_hash              bytea         not null,
  retrieved_at          timestamptz   not null,
  primary key (listing_id, session_date, capture_id)
) partition by range (session_date);

create table md.eod_current (                     -- same columns, one row per key
  listing_id            bigint        not null,
  session_date          date          not null,
  open                  numeric(20,6),
  high                  numeric(20,6),
  low                   numeric(20,6),
  close                 numeric(20,6),
  adjusted_close        numeric(20,6),
  volume                numeric(24,4),
  price_currency        text          not null,
  price_unit_multiplier numeric(8,6)  not null,
  capture_id            uuid          not null,       -- capture that produced the current value
  row_hash              bytea         not null,
  retrieved_at          timestamptz   not null,
  primary key (listing_id, session_date)              -- includes the partition key, as required
) partition by range (session_date);
-- one partition per year for both tables, e.g.:
create table md.eod_current_2026 partition of md.eod_current for values from ('2026-01-01') to ('2027-01-01');

insert into md.eod_current as t
select listing_id, session_date, open, high, low, close, adjusted_close, volume, price_currency,
       price_unit_multiplier, capture_id, row_hash, retrieved_at
from staging.eod_batch
on conflict (listing_id, session_date) do update
set open = excluded.open, high = excluded.high, low = excluded.low, close = excluded.close,
    adjusted_close = excluded.adjusted_close, volume = excluded.volume,
    price_currency = excluded.price_currency, price_unit_multiplier = excluded.price_unit_multiplier,
    capture_id = excluded.capture_id, row_hash = excluded.row_hash, retrieved_at = excluded.retrieved_at
where t.row_hash is distinct from excluded.row_hash;
```

Use `numeric` (or integer minor units) for anything that becomes cash; `double precision` is fine for
analytic copies with a stated tolerance. Do not add `CHECK (low <= high)`: a rejected source anomaly
disappears silently; store it and flag it (§4).

**ClickHouse**

```sql
CREATE TABLE md.eod_current
(
  listing_id      UInt64,
  session_date    Date,
  open            Nullable(Decimal(20, 6)),
  high            Nullable(Decimal(20, 6)),
  low             Nullable(Decimal(20, 6)),
  close           Nullable(Decimal(20, 6)),
  adjusted_close  Nullable(Decimal(20, 6)),
  volume          Nullable(Float64),
  price_currency  LowCardinality(String),
  unit_multiplier Decimal(8, 6),
  capture_id      UUID,
  retrieved_at    DateTime64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(retrieved_at)        -- latest retrieval wins per ORDER BY key
PARTITION BY toYear(session_date)
ORDER BY (listing_id, session_date);

-- deduplication happens at merge time: correct reads use FINAL or argMax
SELECT listing_id, session_date, argMax(close, retrieved_at) AS close, argMax(adjusted_close, retrieved_at) AS adj
FROM md.eod_current WHERE listing_id = 42 GROUP BY listing_id, session_date ORDER BY session_date;
```

Keep a plain `MergeTree` observation table (ORDER BY listing_id, session_date, retrieved_at) for history.

**Iceberg / Delta (Spark SQL)**

```sql
MERGE INTO md.eod_current t
USING staged s
ON t.listing_id = s.listing_id AND t.session_date = s.session_date
WHEN MATCHED AND t.row_hash <> s.row_hash THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;

-- table state as this application held it at a time (not an EODHD vintage)
SELECT * FROM md.eod_current TIMESTAMP AS OF '2026-10-01 00:00:00';
```

Snapshot time travel shows what *your table* contained; snapshot expiry/vacuum deletes it, so it is not an
archive. Keep raw captures and the observation table for reproducibility. Partition by
`(exchange, years(session_date))`, sort/cluster by `listing_id`.

**DuckDB + Parquet**

```sql
CREATE VIEW eod_obs AS
SELECT * FROM read_parquet('lake/eod/exchange=*/year=*/*.parquet', hive_partitioning = true);

-- latest capture of each row as retrieved on or before an as-of instant
SELECT * FROM eod_obs
WHERE retrieved_at <= TIMESTAMP '2026-10-01 00:00:00'
QUALIFY row_number() OVER (PARTITION BY listing_id, session_date ORDER BY retrieved_at DESC) = 1;

-- ASOF JOIN: FX on or before each session (EURUSD.FOREX close = USD per EUR)
SELECT p.listing_id, p.session_date,
       p.close * p.price_unit_multiplier * fx.close AS close_usd, fx.date AS fx_date
FROM px p ASOF JOIN fx ON fx.pair = p.fx_pair AND p.session_date >= fx.date;

-- ASOF JOIN: fundamentals admissible after a conservative availability date (see temporal-research.md)
SELECT p.*, f.eps_ttm
FROM px p ASOF JOIN fundamentals_avail f
  ON f.listing_id = p.listing_id AND p.session_date >= f.available_date;

-- returns per listing on the total-return basis
SELECT listing_id, session_date,
       adjusted_close / lag(adjusted_close) OVER w - 1     AS simple_ret,
       ln(adjusted_close / lag(adjusted_close) OVER w)     AS log_ret
FROM px WINDOW w AS (PARTITION BY listing_id ORDER BY session_date);
```

Report `fx_date` next to the converted value so stale FX is visible. Write Parquet per exchange/year (not per
ticker: millions of tiny files are slow). After any ISIN or mapping join, compare row counts (§3).

### Acceptance checks (all engines)

- Loading the same capture twice changes nothing in the current table.
- A corrected value replaces the current row, and the previous capture stays queryable in the observation
  table.
- An `as_of` query before the correction returns the old value and labels the result "as retrieved".

---

## 7. Durable streaming log for WebSockets

**Use when** WebSocket data feeds research, audit, backtests or reconciliation, i.e. anything that must be
replayed. A display-only ticker needs none of this ([intraday.md](intraday.md)).

**EODHD inputs**: `wss://ws.eodhistoricaldata.com/ws/{us|us-quote|eu|eu-quote|forex|crypto|…}`; EOD+Intraday
Extended or All-In-One; 50 symbol slots per token across sockets, up to 64 connections, no API-call cost.
Trade messages carry `s`, `p`, `v`, `c` (condition), `dp` (dark pool), `ms` (`open` / `closed` /
`extended-hours`), `t`; quotes `s`, `ap`, `as`, `bp`, `bs`, `t`; forex `s`, `a`, `b`, `dc`, `dd`, `ppms`, `t`;
crypto `s`, `p`, `q`, `dc`, `dd`, `t`. `t` is epoch milliseconds in the documented examples; one documented
index example uses seconds, so normalize by magnitude. There is no sequence number, no history and no replay;
US trades come from a single venue (partial volume, not a consolidated tape). Reconciliation source:
`/api/intraday` 1m, finalized ~2–3 h after the US after-hours close, 5 calls per request.

### Method

1. **Persist before processing.** The socket reader does only: receive → append `{recv_ns, conn_id,
   feed, raw}` to the log → next. Parsing, bars and UI run as consumers.
2. Log choices: Kafka/Redpanda topic per feed (`eodhd.ws.us.trades`), key = symbol (keeps per-symbol order),
   `cleanup.policy=delete` (never compaction for trades), retention ≥ replay need (e.g. 14 days), replicated
   if available. For ≤ 50 symbols, rotating append-only JSONL files per feed and hour, `fsync` on rotation,
   compressed when closed, are enough.
3. **Event-time bars** per (symbol, interval): bucket `[start, start + Δ)` with `start = t − t mod Δ`;
   watermark `W = max_event_time − allowed_lateness`; a bar becomes **final** when `start + Δ ≤ W`; a trade
   for a bar already final goes to a late-event log, never silently into the bar. Keep `ms=extended-hours`
   trades in separate session bars.
4. **Idempotent sink** keyed `(feed, symbol, interval, bar_start)` with `state` ∈ provisional / final /
   reconciled and the last log offset applied. Deduplicate on log position (topic-partition-offset or
   file+line): the messages have no trade id, so identical (s, t, p, v) pairs may be two genuine trades.
5. **Dead-letter** unparsable messages with the raw bytes.
6. **Reconcile** after intraday finalization: fetch `/api/intraday/{SYM}?interval=1m&from=&to=` for the
   session (5 calls per symbol per request; 50 symbols ≈ 250 calls/day), compare per bar: presence, OHLC
   within a tick, and the volume ratio (stream volume below intraday volume is expected for US). Flag
   differences in a reconciliation table; serve the intraday API bar as the final historical bar, labelled.

```python
from dataclasses import dataclass, field

@dataclass
class BarBuilder:
    interval_ms: int = 60_000
    lateness_ms: int = 2_000
    watermark: int = 0
    bars: dict = field(default_factory=dict)     # (sym, start) -> provisional bar
    final: dict = field(default_factory=dict)    # (sym, start) -> final bar (flush to the sink)
    late: list = field(default_factory=list)
    seen: set = field(default_factory=set)       # applied log offsets (persist with the sink)

    def on_trade(self, offset, sym, t, price, size):
        if offset in self.seen:                  # replay or redelivery: no effect
            return
        self.seen.add(offset)
        t = t * 1000 if t < 100_000_000_000 else t          # seconds -> ms
        start = t - t % self.interval_ms
        key = (sym, start)
        if key in self.final or start + self.interval_ms <= self.watermark:
            self.late.append((offset, sym, t, price, size))
            return
        b = self.bars.get(key)
        if b is None:
            self.bars[key] = {"o": price, "h": price, "l": price, "c": price, "v": size, "first_t": t, "last_t": t}
        else:
            if t < b["first_t"]:
                b["o"], b["first_t"] = price, t
            if t >= b["last_t"]:
                b["c"], b["last_t"] = price, t
            b["h"], b["l"], b["v"] = max(b["h"], price), min(b["l"], price), b["v"] + size
        self.watermark = max(self.watermark, t - self.lateness_ms)
        for k in [k for k in self.bars if k[1] + self.interval_ms <= self.watermark]:
            self.final[k] = self.bars.pop(k)
```

Pitfalls: a reconnect gap cannot be refilled from the stream (no replay); mark the gap and backfill from
intraday after finalization. The 50-symbol allowance is shared by every socket on the token, including a
developer's laptop. A quote stream cannot produce traded volume. Clock skew: keep `recv_ns` and event `t`
separately and alert when `recv − t` drifts.

### Acceptance checks

- Restarting the consumer and replaying the log from offset 0 produces byte-identical final bars.
- A duplicated log record leaves bars unchanged; a trade 1 s late (lateness 2 s) updates the provisional bar;
  a trade 60 s late lands in the late-event log.
- Killing the reader for 2 minutes produces a recorded gap, not a zero-volume bar.
- The reconciliation report shows, per symbol and session, bars missing on either side and price differences.

---

## 8. SCD2 listing history from symbol-list snapshots

**Use when** the user needs the history of listing attributes (name, venue, currency, type, ISIN, delisted
state) for joins "as of" a date, or to explain renames and reused tickers.

**EODHD inputs**: dated captures of `exchange-symbol-list/{EX}` and `?delisted=1` (1 call each; the delisted
response replaces, not extends, the active one); fields `Code`, `Name`, `Country`, `Exchange` (venue, e.g.
`NASDAQ` under `US`), `Currency`, `Type`, `Isin`. Optional: `symbol-change-history` (US only, from
2022-07-22, EOD+Intraday Extended or All-In-One; `old_symbol`, `new_symbol`, `effective`), Fundamentals
`General`.

**State this in the model documentation:** `valid_from` and `valid_to` are **capture dates**. The real change
happened at some unknown time between the previous capture and the first capture that shows it. EODHD symbol
lists carry no effective dates and earlier states cannot be downloaded later; history starts at your first
capture.

### Method

1. Capture both lists per exchange on a fixed cadence (weekly is enough for most uses) into
   `symbol_list_snapshot(capture_date, exchange, code, name, venue, currency, type, isin, delisted_list)`.
2. Build a grid of every known `(exchange, code)` × every capture date, so "absent from both lists" is an
   explicit state rather than a silently extended old version.
3. Hash the tracked attributes, start a new version when the hash changes, collapse runs.
4. Resolve listings (`listing_id`) separately from codes: a code is not an identity.
   - **Reuse**: when code `X` changes ISIN and `X_old` (or `X_old1`, `X_old2`) appears in the same capture with
     X's previous ISIN, the existing `listing_id` moves to `X_old`; the new company under `X` gets a new
     `listing_id`. Never splice price histories across the change.
   - **Rename**: a new code appears with the ISIN of a code that disappeared or moved to the delisted list,
     confirmed by `symbol-change-history` (US) where available; keep one `listing_id` and record both codes
     as aliases with the evidence ([identity.md](identity.md)).
   - Require two consecutive absences before treating a listing as gone: one list can be incomplete.
5. Point-in-time join: `fact.session_date >= valid_from and (valid_to is null or fact.session_date < valid_to)`,
   accepting that dates before the first capture have only the earliest known version (label them).

```sql
with captures as (select distinct exchange, capture_date from symbol_list_snapshot),
keys as (select distinct exchange, code from symbol_list_snapshot),
grid as (
  select k.exchange, k.code, c.capture_date, s.name, s.venue, s.currency, s.type, s.isin, s.delisted_list,
         case when s.code is null then 'ABSENT'
              else md5(concat_ws('|', coalesce(s.name, ''), coalesce(s.venue, ''), coalesce(s.currency, ''),
                                 coalesce(s.type, ''), coalesce(s.isin, ''), cast(s.delisted_list as varchar)))
         end as attr_hash
  from keys k join captures c using (exchange)
  left join symbol_list_snapshot s
         on s.exchange = k.exchange and s.code = k.code and s.capture_date = c.capture_date),
flagged as (
  select *, case when attr_hash is distinct from lag(attr_hash) over w then 1 else 0 end as is_new
  from grid window w as (partition by exchange, code order by capture_date)),
versioned as (
  select *, sum(is_new) over (partition by exchange, code order by capture_date) as version_no
  from flagged)
select exchange, code, version_no,
       any_value(name) as name, any_value(venue) as venue, any_value(currency) as currency,
       any_value(type) as type, any_value(isin) as isin, any_value(delisted_list) as delisted_list,
       any_value(attr_hash) = 'ABSENT' as is_absent,
       min(capture_date) as valid_from_observed,       -- first capture showing this version
       max(capture_date) as last_confirmed,            -- last capture still showing it
       lead(min(capture_date)) over (partition by exchange, code order by version_no) as valid_to_observed
from versioned
group by exchange, code, version_no;
```

(DuckDB syntax; PostgreSQL 16+ also has `any_value`, older versions can use `min`.)
Add a surrogate key per version and an "unknown" member row for facts whose listing cannot be resolved.

### Acceptance checks

- A name change between two weekly captures produces two versions of one listing; the first version's
  `valid_to_observed` equals the second capture date, not the change date.
- A code missing from one capture yields an `is_absent` version, not a closed listing.
- A reused code produces two `listing_id`s; price facts before the reuse join to the `_old` listing.
- A US rename confirmed by `symbol-change-history` keeps one `listing_id` with two aliases.

### Issuer, security and listing keys; Data Vault mapping

**Use when** the model must answer questions at more than one identity level ("all lines of this company",
"same security on another venue") or the team uses a dimensional or Data Vault warehouse.

**EODHD inputs**: the symbol-list captures above (`Isin` per listing); `/api/id-mapping?filter[isin]=…` or
`filter[symbol]=…` (1 call; returns `symbol`, `isin`, `figi`, `lei`, `cusip`, `cik`, current values only);
Fundamentals `General` for the same identifiers (10 calls). There is no issuer table in EODHD: the issuer
key is derived (LEI, else CIK, else a user-assigned key), and its history starts at your first capture.

**Method.**

1. Three levels, each with its own key:
   - `dim_issuer(issuer_id)`: `lei` when present, else `'CIK:' || cik`, else a user-assigned key. One
     issuer has many securities (ordinary shares, preferred lines, ADRs with their own ISIN).
   - `dim_security(security_id = isin)`: one economic security. One ISIN often trades on several
     exchanges, in several currencies.
   - `dim_listing(listing_id)`: the SCD2 table above, one row per `(exchange, code)` version.
2. `bridge_security_issuer(security_id, issuer_id)` from ID mapping; unresolved securities map to a
   placeholder issuer `'ISIN:' || isin`, flagged, not dropped.
3. `link_same_as(listing_id_a, listing_id_b, evidence, observed_at)` with `listing_id_a < listing_id_b`, one
   row per pair of listings that showed the same ISIN in the same capture. `evidence` names the source
   (`shared ISIN …`, `id-mapping`, or a user decision); `observed_at` is the capture date. A same-as link
   does not make prices interchangeable: currency, unit, session and liquidity differ by venue.
4. Facts keep `listing_id`. Roll up to security or issuer only through these tables, and only for
   quantities that are comparable across venues (positions, exposure), never by averaging prices.

Data Vault mapping of the same captures:

| Vault object | Business key / content | Built from |
|---|---|---|
| `hub_listing` | `(exchange, code)` hashed as `hk_listing` | each symbol-list capture |
| `hub_isin` | `isin` hashed as `hk_isin` | each symbol-list capture, ID mapping |
| `link_listing_isin` | `hk_listing` × `hk_isin` | rows that carry an ISIN |
| `link_same_as` | `hk_listing` × `hk_listing` with evidence | pairs sharing an ISIN, or a user decision |
| `sat_listing_attrs` | name, venue, currency, type, delisted flag; `load_date` = capture date; insert-only on hashdiff change | symbol-list captures |
| `pit_listing` | one row per `hk_listing` × snapshot date, pointing at the satellite `load_date` valid then | capture calendar |

`load_date` is the capture date, so the vault has the same limitation as the SCD2 table: changes are
dated by when you saw them, not when they happened.

```sql
-- inputs: symbol_list_snapshot (section 8 step 1), listing_map(listing_id, exchange, code) from step 4,
-- issuer_xref(isin, lei, cik) from /api/id-mapping
create table dim_security as
select isin as security_id, isin, any_value(type) as security_type
from symbol_list_snapshot where isin is not null and isin <> '' group by isin;

create table bridge_security_issuer as
select s.security_id, coalesce(x.lei, 'CIK:' || x.cik, 'ISIN:' || s.isin) as issuer_id
from dim_security s left join issuer_xref x using (isin);

create table link_same_as as                      -- one row per unordered listing pair sharing an ISIN
select a.listing_id as listing_id_a, b.listing_id as listing_id_b,
       'shared ISIN ' || sa.isin as evidence, max(sa.capture_date) as observed_at
from symbol_list_snapshot sa
join listing_map a on a.exchange = sa.exchange and a.code = sa.code
join symbol_list_snapshot sb on sb.isin = sa.isin and sb.capture_date = sa.capture_date
join listing_map b on b.exchange = sb.exchange and b.code = sb.code
where a.listing_id < b.listing_id
group by all;

create table hub_listing as
select md5(exchange || '|' || code) as hk_listing, exchange, code, min(capture_date) as load_date,
       'exchange-symbol-list' as record_source
from symbol_list_snapshot group by exchange, code;

create table hub_isin as
select md5(isin) as hk_isin, isin, min(capture_date) as load_date, 'exchange-symbol-list' as record_source
from symbol_list_snapshot where isin is not null and isin <> '' group by isin;

create table link_listing_isin as
select distinct md5(exchange || '|' || code || '|' || isin) as hk_link,
       md5(exchange || '|' || code) as hk_listing, md5(isin) as hk_isin
from symbol_list_snapshot where isin is not null and isin <> '';

create table sat_listing_attrs as                 -- insert-only; a new row only when the hashdiff changes
select hk_listing, capture_date as load_date, hashdiff, name, venue, currency, type, delisted_list
from (select md5(exchange || '|' || code) as hk_listing, capture_date,
             md5(concat_ws('|', name, venue, currency, type, cast(delisted_list as varchar))) as hashdiff,
             name, venue, currency, type, delisted_list,
             lag(md5(concat_ws('|', name, venue, currency, type, cast(delisted_list as varchar))))
               over (partition by exchange, code order by capture_date) as prev_hashdiff
      from symbol_list_snapshot)
where prev_hashdiff is null or prev_hashdiff <> hashdiff;

create table pit_listing as                       -- one row per hub key and snapshot date
select h.hk_listing, c.capture_date as snapshot_date,
       (select max(s.load_date) from sat_listing_attrs s
        where s.hk_listing = h.hk_listing and s.load_date <= c.capture_date) as sat_attrs_load_date
from hub_listing h cross join (select distinct capture_date from symbol_list_snapshot) c;
```

**Pitfalls.** Merging listings by ISIN into one price series mixes currencies and sessions. A listing with an
empty `Isin` is not a new security; leave it unlinked and flagged. ADRs and ordinary shares are different
securities of one issuer. Identifiers from ID mapping are current values only: a CIK or LEI found today is
applied to past captures as an assumption, labelled.

**Acceptance checks** (DuckDB, fixture of two weekly captures with one ISIN on a `US` and a `XETRA` line and
one single-listed ISIN; codes are illustrative):

- The shared ISIN gives 2 listings, 1 `dim_security` row and 1 `link_same_as` row
  `(101, 102, 'shared ISIN US0378331005', 2026-10-23)`.
- The issuer with an LEI is keyed by the LEI; the security without an ID-mapping row gets
  `ISIN:US5949181045` as a flagged placeholder issuer.
- A name change between the captures gives 4 satellite rows for 3 listings, and `pit_listing` returns the
  old name for the first snapshot date and the new name for the second.

---

## 9. Pipeline migration and parity testing

**Use when** replacing a pipeline, an engine, a transformation version, or moving from another data source
([build-recipes.md](build-recipes.md) recipe 50): prove the new output equals the old or differs for stated
reasons before cutover.

**EODHD inputs**: none beyond the archives being compared; a fresh pull of a small sample when differences
need a tie-breaker (budget it).

### Method

1. Freeze inputs: both pipelines read the same captures (same `capture_id`s) unless the test is about
   re-requesting.
2. Row counts per `(exchange, session_date)` and per dataset.
3. Key anti-joins both ways on `(listing_id, session_date)` (after mapping identifiers, see §8).
4. Per-listing aggregates: count, first/last date, sum of volume, and an ordered digest.
5. Field comparison on matching keys with the tolerances below; classify every difference.
6. Parallel run for N sessions (≥ 10, including a holiday, a month end and a session with splits and
   dividends); compare daily; block cutover while unexplained differences remain.
7. Cutover by swapping serving views (§15); keep the old path runnable for one release as rollback.

```sql
-- anti-joins
select 'missing_in_new' as side, o.listing_id, o.session_date
from old_px o left join new_px n using (listing_id, session_date) where n.listing_id is null
union all
select 'missing_in_old', n.listing_id, n.session_date
from new_px n left join old_px o using (listing_id, session_date) where o.listing_id is null;

-- per-listing digest (format numbers to fixed decimals before hashing)
select listing_id, count(*) as n, min(session_date) as first_d, max(session_date) as last_d, sum(volume) as vol,
       md5(string_agg(cast(session_date as varchar) || ':' || cast(cast(close as decimal(18,4)) as varchar)
                      || ':' || coalesce(cast(volume as varchar), 'null'), '|' order by session_date)) as digest
from new_px group by listing_id;
```

| Field | Tolerance | Typical difference class |
|---|---|---|
| raw open/high/low/close | exact at 4 decimals | units (GBX vs GBP ×100), session (extended hours in one side), identity |
| `adjusted_close` | relative 1e-6 on the same capture; else classify | restatement timing (captured before/after an action), method |
| volume | exact on the same basis | split basis (raw vs split-adjusted), consolidated vs venue |
| dividends | exact on `unadjustedValue` + currency | adjusted vs unadjusted amount, currency |
| dates | exact | timezone/session-label shifts, holiday fallback rows |

Difference classes: basis, units, session, action timing, identity, coverage, genuine anomaly. Only
"genuine anomaly" is a data defect; report it per [quality.md](quality.md).

**Incremental-versus-full-refresh parity** is the same test between `fct_price_daily` built incrementally and
a full rebuild from the same captures: `(A EXCEPT ALL B) UNION ALL (B EXCEPT ALL A)` must be empty.

### Acceptance checks

- A report lists every key mismatch and field difference with a class; the count of "unexplained" is zero
  before cutover.
- Rollback (pointing the serving views back) is executed once in the test environment.
- The parity job runs weekly after cutover on incremental vs full refresh.

---

## 10. Fixture-based unit tests

**Use when** writing tests for transformations. Fixtures are synthetic, token-free and small; do not commit
EODHD responses to public repositories ([licensing.md](licensing.md)). Each case states its invariant and
should fail on a planted bug.

| Case | Given | Expect | Planted bug it catches |
|---|---|---|---|
| Split (2:1) | raw close 100 on d−1, 50 on d; split `"2.000000/1.000000"` ex d; volume (already split-adjusted) 2,000 on d−1 | split-adjusted close d−1 = 50; volume unchanged 2,000; raw-basis volume d−1 = 1,000 | dividing delivered volume by the ratio again |
| Reverse split (1:8) | `"1.000000/8.000000"` ex d | factor ×8 before d; parsed ratio 0.125 | reading the ratio as old/new |
| Dividend restatement | capture A: no dividend, `adjusted_close == close`; capture B: dividend 1.00 ex d, close(d−1) = 100 | all rows before d in `total_return` rebuilt (factor ≈ 0.99 band); rows ≥ d unchanged; other listings untouched | append-only incremental by `max(date)` |
| No double dividend | total-return series + dividend ledger | total return = adjusted-close return only | adding cash dividends on top of `adjusted_close` |
| GBX price, GBP dividend | close 638.5, currency GBX; dividend 0.0175 GBP | price 6.385 GBP; yield = 0.0175/6.385; dividend not ×0.01 | scaling the dividend by the price unit |
| `_old` reuse | `ABC_old` (ISIN A, rows to 2021) and `ABC` (ISIN B, rows from 2022) | two `listing_id`s; no return across the boundary | joining histories on ticker text |
| Holiday bulk fallback | request date 2026-07-03, response rows dated 2026-07-02 | zero rows written for 07-03; state `NOT_YET_AVAILABLE`; no error | writing previous-session rows under the requested date |
| Null vs zero volume | intraday bar volume `null`; EOD row volume 0 | null stays null and is excluded from sums; 0 stays 0 and is flagged | `fillna(0)` |
| Duplicate page | page 2 repeated by the API | stop with an explicit error; no duplicate rows | blind offset loop |
| DST boundary | US 1m bars around the March DST change | regular-session filter uses the calendar (13:30 vs 14:30 UTC open) | fixed UTC offsets |
| Incremental == full | 3 runs of captures with one correction | incremental table equals full rebuild | missed restatement path |

A pytest sketch for the first case (the transform under test is the user's):

```python
def test_split_adjusts_prices_but_not_delivered_volume():
    rows = [{"date": "2026-03-02", "close": 100.0, "volume": 2000.0},
            {"date": "2026-03-03", "close": 50.0, "volume": 900.0}]
    splits = [{"date": "2026-03-03", "split": "2.000000/1.000000"}]
    out = {r["date"]: r for r in build_split_adjusted(rows, splits)}
    assert out["2026-03-02"]["split_adjusted_close"] == 50.0
    assert out["2026-03-02"]["volume"] == 2000.0          # already split-adjusted by EODHD
    assert out["2026-03-02"]["raw_volume"] == 1000.0      # derived: volume / S(d)
```

dbt (≥ 1.8) unit test for the same rule:

```yaml
unit_tests:
  - name: split_adjusts_pre_split_rows_only
    model: int_split_adjusted
    given:
      - input: ref('int_eod_current')
        rows:
          - {listing_id: 1, session_date: 2026-03-02, close: 100.0, volume: 2000}
          - {listing_id: 1, session_date: 2026-03-03, close: 50.0, volume: 900}
      - input: ref('stg_eodhd__splits')
        rows:
          - {listing_id: 1, ex_date: 2026-03-03, ratio: 2.0}
    expect:
      rows:
        - {listing_id: 1, session_date: 2026-03-02, split_adjusted_close: 50.0, volume: 2000}
        - {listing_id: 1, session_date: 2026-03-03, split_adjusted_close: 50.0, volume: 900}
```

Synthetic EODHD-shaped series for fixtures and public demos (label output "synthetic"; the dividend factor is
a modelling convention, not EODHD's exact method):

```python
import math, random
from datetime import date, timedelta

def synthetic_eod(n=60, seed=7, start=date(2026, 1, 5), split=(30, 2.0), dividend=(45, 0.5),
                  holidays=frozenset({date(2026, 1, 19)}), missing=frozenset({12})):
    rng, days, d = random.Random(seed), [], start
    while len(days) < n:
        if d.weekday() < 5 and d not in holidays:
            days.append(d)
        d += timedelta(days=1)
    raw, px = [], 100.0
    for i, day in enumerate(days):
        if i == split[0]:
            px /= split[1]
        o = px * math.exp(rng.gauss(0, 0.005)); c = o * math.exp(rng.gauss(0, 0.01))
        h = max(o, c) * (1 + abs(rng.gauss(0, 0.004))); l = min(o, c) * (1 - abs(rng.gauss(0, 0.004)))
        raw.append(dict(date=day.isoformat(), open=round(o, 4), high=round(h, 4), low=round(l, 4),
                        close=round(c, 4), shares=rng.randint(10_000, 50_000)))
        px = c
    out, f_price, f_vol = [], 1.0, 1.0
    for i in range(n - 1, -1, -1):                     # walk backwards applying later actions
        r = dict(raw[i]); shares = r.pop("shares")
        r["adjusted_close"], r["volume"] = round(r["close"] * f_price, 4), shares * f_vol
        out.append(r)
        if i == split[0]:
            f_price /= split[1]; f_vol *= split[1]
        if i == dividend[0]:
            p_prev = raw[i - 1]["close"]; f_price *= (p_prev - dividend[1]) / p_prev
    out.reverse()
    return [r for j, r in enumerate(out) if j not in missing]   # a missing bar, never a zero bar
```

Self-check: every row satisfies the OHLC bounds, the holiday is absent, 59 rows remain, and Q11 finds exactly
two factor jumps (split and dividend ex-dates) when the action ledger is withheld, none when it is supplied.
Extend with a GBX listing (multiplier 0.01), a delisting (rows stop) and an `_old` pair as needed.

### Contract and schema-diff test

**Use when** a captured response (or a fixture shaped like one) must be checked against the dataset
contract ([assets/dataset-contract.json](../assets/dataset-contract.json), `response_schema`) before
normalization, and in CI before a parser change ships.

**Method.** Compare keys, JSON types, date format and nullability of every row (first 200 rows by default)
with the contract; compare the listing's expected currency/unit (from `dim_listing`) with the capture's
metadata. Classify:

| Change | Class | Status |
|---|---|---|
| new key not in the contract | ADDITIVE | WARN (record it; update the contract in a reviewed change) |
| required key missing; JSON type changed; date format changed; null in a non-nullable field; body not a JSON array of objects (HTML, error object) | BREAKING | FAIL (keep the capture, stop normalization, §5 "Schema change") |
| currency or unit multiplier differs from the listing's registered one | BREAKING | FAIL (block derived values, Q12) |

A JSON integer satisfies `number` (prices such as `340` arrive as integers). The run status is the worst
finding: any BREAKING → FAIL, only ADDITIVE → WARN, none → PASS.

```python
import json, re, sys

JSON_TYPE = {bool: "boolean", int: "integer", float: "number", str: "string",
             list: "array", dict: "object", type(None): "null"}

def _type_ok(declared, value):
    t = JSON_TYPE[type(value)]
    return t == declared or (declared == "number" and t == "integer")

def contract_diff(contract, body, expected_units=None, observed_units=None, sample=200):
    """Compare one captured response body with contract["response_schema"].
    Returns (status, findings): status FAIL if any BREAKING, WARN if only ADDITIVE, else PASS."""
    spec = contract["response_schema"]["fields"]
    findings = []
    if not isinstance(body, list) or not all(isinstance(r, dict) for r in body):
        return "FAIL", [("BREAKING", "envelope", "body is not a JSON array of objects")]
    seen = set()
    for row in body[:sample]:
        seen |= set(row)
        for name, f in spec.items():
            if name not in row:
                if f.get("required"):
                    findings.append(("BREAKING", name, "missing required field"))
                continue
            v = row[name]
            if v is None:
                if not f.get("nullable"):
                    findings.append(("BREAKING", name, "null in non-nullable field"))
            elif not _type_ok(f["type"], v):
                findings.append(("BREAKING", name, f"type {JSON_TYPE[type(v)]} != {f['type']}"))
            elif f.get("format") == "YYYY-MM-DD" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                findings.append(("BREAKING", name, f"format {v!r}"))
    for name in sorted(seen - set(spec)):
        findings.append(("ADDITIVE", name, "new field not in contract"))
    for name, unit in (expected_units or {}).items():      # e.g. {"price_currency": "GBX"} from dim_listing
        got = (observed_units or {}).get(name)
        if got != unit:
            findings.append(("BREAKING", name, f"unit {got!r} != {unit!r}"))
    findings = sorted(set(findings))
    status = "FAIL" if any(k == "BREAKING" for k, *_ in findings) else "WARN" if findings else "PASS"
    return status, findings

if __name__ == "__main__":          # CI: python contract_diff.py contract.json capture1.json [...]
    contract = json.load(open(sys.argv[1]))
    worst = "PASS"
    for path in sys.argv[2:]:
        status, findings = contract_diff(contract, json.load(open(path)))
        print(path, status, *findings, sep="\n  ")
        worst = max(worst, status, key=["PASS", "WARN", "FAIL"].index)
    sys.exit(1 if worst == "FAIL" else 0)
```

**Acceptance checks** (contract file as shipped; the PASS row is an EOD row in the documented shape):

- A row with `date, open, high, low, close, adjusted_close, volume` → `PASS`; the same row with
  `open = 349` (integer) → `PASS`.
- An extra key `vwap` → `WARN` with one `ADDITIVE` finding.
- `adjusted_close` missing → `FAIL` (`missing required field`); `volume` as a string → `FAIL`
  (`type string != number`); `close = null` → `FAIL`.
- Expected `price_currency` `GBX`, observed `GBP` → `FAIL`; the body `"<html>"` → `FAIL` (`envelope`).
- The CLI exits 1 when any file FAILs and 0 otherwise.

### Acceptance checks

- Each fixture case has a named invariant; mutating the transform as in the "planted bug" column makes the
  test fail.
- The fixture directory contains no token, no `/api/user` response and no real EODHD capture.

---

## 11. Metric dictionary and aggregation rules

**Use when** values are rolled up across securities, accounts or time in SQL, a semantic layer or BI, or
when "the same label must mean the same number" across dashboards and AI answers.

**EODHD inputs**: `adjusted_close` (total-return basis), raw `close` (cash accounting, executable levels),
split-adjusted `volume`, dividends (`unadjustedValue` and currency), FX via `*.FOREX`, Fundamentals
`Highlights`/`Valuation`/`SharesStats`/statements for ratios; holdings and cash flows are user-supplied.

### Measure types

| Type | Across securities | Across time | Examples |
|---|---|---|---|
| Additive | sum | sum | traded volume, dividend cash received, fees, cash flows |
| Semi-additive | sum (same currency, same date) | last value of the period (or average balance if defined) | holdings value, market cap, shares, NAV |
| Non-additive | recompute from components | recompute | prices, returns, ratios, yields, percentages |

### Aggregation rules

| Quantity | Correct aggregation | Wrong |
|---|---|---|
| Group P/E, P/B, EV/EBITDA | ratio of sums `Σ cap / Σ earnings` (equivalently cap-weighted harmonic mean of P/E); report negative or zero denominators as excluded with a count | mean of P/E |
| Weighted average yield | `Σ wᵢ yᵢ` with stated weights (value, equal, cap) | unweighted mean presented as portfolio yield |
| Return over time | `Π(1 + rₜ) − 1`; log returns add over time: `Σ ln(1 + rₜ)` | sum of simple returns |
| Portfolio return in a period | `Σ wᵢ rᵢ` with start-of-period weights, simple returns | sum of log returns across assets |
| Annualized return | `(Π(1 + rₜ))^(P/n) − 1`, P periods per year of the series' calendar | `mean × P` presented as compound |
| Volatility | `sd(r) · √P` with P = 252 sessions, 365 crypto days, 52 weeks, 12 months; sample sd | mixing calendars |
| Price level of a group | an index with a defined base and weights | sum or average of prices |
| Market cap in a base currency | `Σ capᵢ · FXᵢ` on the same date, FX oriented correctly | summing local-currency caps |
| NAV over a period | last value (or time-weighted average if defined) | sum over dates |
| Percent vs percentage points | changes in rates/yields in pp or bp; changes of a value in % | "+2%" for 3% → 5% |

Round only after aggregation; keep decimals (0.05) and percents (5%) in separate, labelled columns; division
by zero or by a negative denominator yields an explicit "not meaningful" state (`NULLIF`, `SAFE_DIVIDE`), not
0. Detailed return/volatility and performance formulas belong in the performance and risk chapters
([portfolio-risk.md](portfolio-risk.md), [backtesting.md](backtesting.md)); this section governs how stored
values roll up.

### Metric dictionary template

| Field | Example |
|---|---|
| name / label | `pe_group_cap` / "Group P/E (cap-weighted)" |
| numerator / denominator / weight | Σ market_cap / Σ trailing earnings / — |
| basis | raw close × shares; adjusted; reported statement |
| currency and unit | USD, converted at session close FX, `fx_date` shown |
| grain | sector × session_date |
| period / frequency | TTM earnings; daily |
| null and negative policy | exclude earnings ≤ 0; show count excluded |
| source datasets | `fct_price_daily` (raw), `Highlights` (EPS), `SharesStats` |
| owner / version / test | analytics / v2 / two-stock fixture |

```python
def aggregate_pe(caps, earnings):
    """Ratio of sums; non-positive or missing earnings are excluded and counted."""
    keep = [(c, e) for c, e in zip(caps, earnings) if c is not None and e is not None and e > 0]
    if not keep:
        return None, len(caps)
    return sum(c for c, _ in keep) / sum(e for _, e in keep), len(caps) - len(keep)

def compound(returns):
    g = 1.0
    for r in returns:
        g *= 1.0 + r
    return g - 1.0
```

### Populated registry: standard return and income metrics

Formulas are defined once in [methods-performance-risk.md](methods-performance-risk.md) (§2 return
conventions, §4.1 risk-free, §6 ratios); the registry pins the choices a label hides. `A` = periods per year
(252 sessions, 365 crypto days, 12 months). All returns are decimals; display converts.

| id | Formula | Price basis | Frequency / annualization | Currency | Null / undefined policy | Fixture → expected |
|---|---|---|---|---|---|---|
| `price_return` | `P_T/P_0 − 1` (§2.1) | raw `close` (split-adjusted if a split falls inside) | none; period stated | listing currency; GBX/ZAC cancel | null if `P_0 ≤ 0` or either end missing | close 100 → 99 with a 2.00 dividend → −0.0100 |
| `total_return` | `A_T/A_0 − 1` on `adjusted_close` (§2.1) | `adjusted_close` as delivered (split + dividend) | none | listing currency | null if either end missing; never `price_return + yield` | adjusted 98.0 → 99.0 → +0.0102 |
| `cagr` | `(E_T/E_0)^(1/Y) − 1`, `Y = days/365.25` (§2.1) | `total_return` series unless labelled price-only | annual; **not shown for periods < 1 year** (show cumulative) | portfolio base currency | null if `E_0 ≤ 0`, `E_T ≤ 0` or `Y < 1` | 100 → 121 over 731 days → 0.0999; 181 days → null |
| `vol_ann` | `sd(r)·√A`, sample sd (§2.2) | simple returns of `adjusted_close` | `A` of the series' calendar | — | null below the minimum observations (80% of window) | monthly `[1%, −2%, 3%, −1%, 2%]`, `A = 12` → 0.0718 |
| `sharpe` | `mean(r − rf)/sd(r − rf)·√A` (§6) | total-return series, net of costs | frequency stated; rf from UST bills `13WK` (§4.1), converted per period | rf in the return currency; non-USD needs a user rate | null if `sd < 1e-12` | same series, rf = 0 → 1.002 |
| `sortino` | `mean(r − MAR)/DD·√A`, DD over all N (§6) | as `sharpe` | as `sharpe`; MAR stated | — | null if no observation below MAR | same series, MAR = 0 → 2.078 |
| `max_drawdown` | `min_t(E_t/max_{s≤t}E_s − 1)` plus peak, trough and recovery dates; duration = sessions peak → recovery (open if not recovered) (§2.1) | total-return series | none | base currency | null if < 2 observations | `[100, 120, 90, 130]` → −0.25, peak idx 1, trough 2, recovered 3; `[100, 120, 90, 100]` → recovery open |
| `div_yield_ttm` | `Σ D_i / P_t` over ex-dates in `(t − 365 d, t]`, each `D_i` restated to the share basis of `t` (÷ splits with ex-date in `(ex_i, t]`) | raw `close` at `t`; dividends `unadjustedValue` | trailing 365 calendar days | dividend currency = price currency **after** unit normalization (GBX ÷ 100) | null if `P_t ≤ 0`; dividends in another currency need dated FX | 0.50, 0.50, then 2:1 split, 0.25, 0.25; close 50 → 0.0200 |
| `yield_on_cost` | annual dividends per current share ÷ (lot cost ÷ shares held now) | user lot cost (user-supplied), split-adjusted quantity | TTM or forward run-rate — stated | lot currency; FX at purchase date for cost | null without a cost basis | 100 shares bought for 4,000, now 200 after 2:1, TTM 1.00 → 0.0500 |

GBX check for `div_yield_ttm`: close 638.5 GBX = 6.385 GBP, TTM dividends 0.35 GBP → 0.0548; dividing
pence by pounds (or the reverse) gives a value 100× off, which Q12 and the §7 tie-out must catch.

```python
import math
from datetime import date, timedelta

def period_return(levels):                       # price_return on close, total_return on adjusted_close
    return None if len(levels) < 2 or levels[0] <= 0 else levels[-1] / levels[0] - 1

def cagr(v0, v1, d0, d1):
    years = (d1 - d0).days / 365.25
    return None if v0 <= 0 or v1 <= 0 or years < 1 else (v1 / v0) ** (1 / years) - 1   # < 1 year: not annualized

def ann_vol(r, A=252):
    n = len(r); m = sum(r) / n
    return math.sqrt(sum((x - m) ** 2 for x in r) / (n - 1)) * math.sqrt(A)

def max_drawdown(levels):
    """(MaxDD as a negative fraction, peak index, trough index, recovery index or None)."""
    peak_i, best = 0, (0.0, 0, 0)
    for i, v in enumerate(levels):
        if v > levels[peak_i]:
            peak_i = i
        dd = v / levels[peak_i] - 1
        if dd < best[0]:
            best = (dd, peak_i, i)
    dd, p, t = best
    rec = next((j for j in range(t + 1, len(levels)) if levels[j] >= levels[p]), None)
    return dd, p, t, rec

def dividend_yield_ttm(divs, splits, close_t, t):
    """divs: [(ex_date, unadjusted amount)] in the price's major currency unit; splits: [(ex_date, new/old)].
    Each dividend is restated to the share basis of date t (divide by splits with ex in (ex_i, t])."""
    total = 0.0
    for ex, amt in divs:
        if t - timedelta(days=365) < ex <= t:
            f = 1.0
            for sx, ratio in splits:
                if ex < sx <= t:
                    f *= ratio
            total += amt / f
    return None if close_t <= 0 else total / close_t

def yield_on_cost(annual_div_per_current_share, lot_cost_total, lot_shares_now):
    """Cost per current share = lot cost / shares held now (split-adjusted quantity)."""
    return annual_div_per_current_share / (lot_cost_total / lot_shares_now)
```

### Acceptance checks

- Caps (100, 100), earnings (10, 1): mean of P/E = 55, group P/E = 200/11 ≈ 18.18; a third name with
  earnings −5 is excluded and counted.
- Returns +10% then −10%: sum 0, compound −1%.
- A query summing NAV or close prices across dates is rejected by review or by the BI measure rules (§12).
- The same metric name returns the same number in the warehouse, the BI tool and an AI answer.
- Each populated registry row reproduces its fixture value with the functions above (run results are in
  the table); a metric with no fixture is not registered.

---

## 12. Serving BI tools

**Use when** the user puts EODHD-derived data in Power BI, Superset, Metabase or similar.

**EODHD inputs**: none at report time. The BI tool reads the user's warehouse. The official Power BI
connector (and the Excel/Sheets add-ons) call the API directly: every refresh spends calls per symbol and
endpoint cost against the same daily limit, so reserve it in the budget (§1.5) or use it only for small
personal workbooks.

### Method

1. Serve from **approved views** (`serving.price_daily`, `serving.holdings_value`, …) with a column dictionary:
   grain, keys, basis (raw / split / total return), currency and unit multiplier, date vs UTC timestamp,
   as-of capture, coverage limits. The same dictionary serves NL-to-SQL assistants ([ai-mcp.md](ai-mcp.md)).
2. Refresh BI extracts after the exchange's SLA (§5), not on a fixed clock; show "data as of session S,
   retrieved at T" on every page.
3. Define measures with the rules of §11:
   - Power BI (DAX): ratio of sums `DIVIDE(SUM(f[market_cap]), SUM(f[earnings]))`; semi-additive last value
     `CALCULATE(SUM(h[value]), LASTDATE('Date'[Date]))`; compound return `PRODUCTX(r, 1 + r[ret]) - 1`.
     Set default summarization to "Don't summarize" on price, return, ratio and yield columns.
   - Superset / Metabase: datasets on the approved views; metrics defined once in the dataset/semantic layer
     (`sum(market_cap)/nullif(sum(earnings),0)`), not per chart; disable ad-hoc SUM on non-additive columns
     where the tool allows.
4. FX: one explicit measure per conversion with date and orientation; never convert in a visual.
5. Multi-user: row-level security for user portfolios; shared workspaces showing EODHD data to other people
   need a commercial licence regardless of login ([licensing.md](licensing.md)).
6. **Tie-out before release**: recompute each headline KPI (NAV, return, yield, P&L) from stored captures in
   one timestamped query; check label vs formula (price vs total return, local vs base currency); report
   mismatches with both values and the query/capture id; do not "fix" a number to match.

### Acceptance checks

- The refresh's API-call cost (zero for warehouse-backed reports) is documented.
- A visual that sums close prices or averages P/E is caught by the measure rules or the tie-out.
- Every KPI tile shows basis, currency and as-of session.

---

## 13. CI, containers and secret handling

**Use when** the pipeline lives in a repository, a container or a hosted service.

### CI

Default CI runs **offline** on synthetic fixtures; a live smoke job is opt-in, tiny and never runs for
untrusted code.

```yaml
# .github/workflows/pipeline.yml
name: pipeline
on: [pull_request, workflow_dispatch]
permissions: {contents: read}
jobs:
  offline:
    runs-on: ubuntu-latest
    env: {EODHD_API_TOKEN: "", NO_NETWORK: "1"}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -r requirements.lock
      - run: python scripts/scan_secrets.py --all          # same check as the pre-commit hook
      - run: pytest -q tests/                              # fixtures, retry/guard logic, parity
      - run: python -c "import dags"                       # definitions import with no network
      - run: python scripts/contract_diff.py assets/dataset-contract.json tests/fixtures/contract/*.json   # §10
      - run: dbt build --profiles-dir ci --target duckdb_fixtures --select state:modified+ --defer --state prod-artifacts
  live-smoke:
    if: github.event_name == 'workflow_dispatch'           # manual only; secrets never reach fork PRs
    runs-on: ubuntu-latest
    env: {EODHD_API_TOKEN: "${{ secrets.EODHD_API_TOKEN }}"}
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.lock && python -m pipeline.smoke --max-calls 5   # e.g. one EOD + /api/user
```

Make network access fail loudly in the offline job (e.g. a test fixture that patches socket connect) so a
hidden API call is a test failure, not a quota leak. Never use `pull_request_target` to run PR code with
secrets.

Change-review checklist for a pipeline PR: call/quota delta per run (from the estimate function); token
exposure in code, logs, fixtures or notebooks; basis/unit/currency semantics changed; raw captures rewritten
or deleted; idempotency and checkpoint keys changed; affected downstream models, dashboards and reports;
new checks or fixtures added.

### Container

```dockerfile
FROM python:3.12-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY pipeline/ pipeline/
USER app
# raw captures + DuckDB/Parquet live on a persistent volume
VOLUME ["/data"]
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "pipeline.tick"]
```

The token is injected at run time (environment from a secret store or a mounted secret file), never via
`ARG`/`ENV` at build time: build arguments persist in image history. `.dockerignore` excludes `.env`,
`captures/`, `data/` and notebooks with outputs. One image serves collector and scheduler; pin dependencies.

### Secrets across deployment targets

| Target | Where the token lives | Never |
|---|---|---|
| Laptop / notebook | environment or a git-ignored `.env`; strip notebook outputs before sharing | in code cells, URLs printed in outputs |
| Server / VM | secret manager or a root-only (0600) environment file read by the service | shell history, crontab line, logs (`r.url` contains `api_token`) |
| Container / Kubernetes | runtime secret (mounted file or env from a secret object) | image layers, build args |
| Serverless functions | the platform's encrypted secret store, read at cold start | function source, client-visible config |
| CI | repository/organization secret, masked; live jobs manual only | PR jobs from forks |
| Static site, SPA, mobile app, browser extension, shared HTML artifact | **nowhere**: anything shipped to a client is public (`NEXT_PUBLIC_*`, `VITE_*`, app bundles). Call your own backend (authenticated, rate-limited, field/range allowlists) or ship a dated pre-built snapshot | an embedded key, a "hidden" key, a key in a mobile binary |
| Self-hosted MCP server / API wrapper | server-side environment | passthrough of arbitrary EODHD paths |

Logging: redact `api_token` from URLs and headers before logging; prefer the `Authorization: Bearer` header in
server code ([plans-limits.md](plans-limits.md)). Rotation: regenerating the key in the dashboard revokes the
old one immediately, so update every deployment in one change window. Showing data to others from any of
these targets is a licensing question, not only a security one.

Pre-commit secret scan (blocks the actual token value, literal `api_token=` values and raw captures; prints
paths, never the token):

```python
#!/usr/bin/env python3
import os, re, subprocess, sys

PLACEHOLDERS = {"demo", "YOUR_API_TOKEN", "{YOUR_API_TOKEN}", "<token>", ""}
TOKEN_PARAM = re.compile(r"api_token=([^&\s\"'}]+)")
BLOCKED = re.compile(r"(^|/)(captures|raw)(/|$)|(^|/)\.env$|user[-_]details.*\.json$")

def main() -> int:
    full = "--all" in sys.argv                      # CI: scan tracked files; hook: scan the staged index
    real = os.environ.get("EODHD_API_TOKEN", "").strip()
    cmd = ["git", "ls-files"] if full else ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
    files = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.split()
    problems = []
    for path in files:
        if BLOCKED.search(path):
            problems.append(f"{path}: raw capture / env / account response")
            continue
        raw = open(path, "rb").read() if full else subprocess.run(["git", "show", f":{path}"], capture_output=True).stdout
        text = raw.decode("utf-8", "ignore")
        if len(real) >= 8 and real in text:
            problems.append(f"{path}: contains the EODHD_API_TOKEN value")
        if any(m.group(1) not in PLACEHOLDERS and not m.group(1).startswith(("$", "{", "%"))
               for m in TOKEN_PARAM.finditer(text)):
            problems.append(f"{path}: literal api_token= value")
    for p in problems:
        print(p, file=sys.stderr)                   # paths only, never the token
    return 1 if problems else 0

if __name__ == "__main__":
    sys.exit(main())
```

### Acceptance checks

- With networking disabled, the offline CI job passes and makes no HTTP request.
- A fixture with a removed required field or a changed type makes the contract step exit 1 and fails the
  job; a fixture with only a new field passes with a WARN line in the log.
- Staging a file with the token value, or a file under `captures/`, makes the hook exit 1; `api_token=demo`
  and `api_token={token}` pass.
- `docker history` of the image shows no token; the container runs as a non-root user.

---

## 14. Deletable user data versus immutable market captures

**Use when** an application stores user portfolios, journals or account responses next to market data, and
must honour retention or deletion requests (a multi-user application also needs a commercial licence).

### Method

1. Two storage domains:
   - **Market captures and derived market tables**: raw EODHD responses, normalized prices, actions,
     listings. Immutable, contain no user identifiers, shared across users.
   - **User data**: holdings, transactions, watchlists, alerts, journal entries, uploaded broker files,
     per-user derived outputs (NAV series, P&L, tax lots), `/api/user` responses (personal account details).
     Keyed by `user_id`, deletable.
2. Never write user identifiers, holdings or account details into capture files, shared logs, fixtures or
   prompts. Fetch market data by listing, not "for user X".
3. Deletion = delete rows keyed by `user_id` in user schemas and their caches/exports; market captures and
   lineage stay intact. Backups: document the expiry after which deleted user data leaves backups.
4. Retention policy per domain: market captures as long as the archive is useful (private retention is
   permitted after cancellation per [licensing.md](licensing.md), without redistribution rights); user data
   per the application's privacy policy.

### Acceptance checks

- Deleting a test user removes holdings, journal, alerts and per-user outputs; a checksum of the market
  tables is unchanged.
- A grep of capture files and shared logs for the test user's email and holdings finds nothing.

---

## 15. Replay and re-pull checklist with atomic swap

**Use when** reprocessing history after a detected restatement, a transform bug fix, a unit-multiplier
correction or a schema change.

### Checklist

1. **Scope**: affected listings, sessions and partitions; the reason (restatement, code fix, units, identity).
2. **Mode**: replay from raw captures (0 API calls) when the source data was right and the transform wrong;
   re-request when the source changed. Mixed is allowed per partition.
3. **Cost**: re-request calls from the §1.7 formula against `backfill_cap` today; split across days if needed.
4. **Idempotency**: the write path keys on `(listing_id, session_date[, basis])` and row hashes; a second run
   is a no-op.
5. **Build to staging**: new tables or a new versioned schema (`md_v43`), never in place.
6. **Diff**: compare staging with current, restricted to the declared scope. Any difference outside the scope,
   or an unexpected class (§9), blocks the swap.
7. **Checks**: the §4 suite on the rebuilt partitions; no FAIL.
8. **Atomic swap** of serving views (below); record the old and new versions.
9. **Notice**: tell consumers what changed (sessions, listings, magnitude), with the incident record (§5).
10. **Rollback**: keep the previous version until the next successful release; swapping back is one statement.

```sql
-- PostgreSQL: views switch in one transaction
BEGIN;
CREATE OR REPLACE VIEW serving.price_daily AS SELECT * FROM md_v43.fct_price_daily;
CREATE OR REPLACE VIEW serving.dividend_cash AS SELECT * FROM md_v43.fct_dividend_cash;
COMMIT;

-- DuckDB
CREATE OR REPLACE VIEW serving_price_daily AS SELECT * FROM fct_price_daily_v43;

-- ClickHouse (Atomic database engine)
EXCHANGE TABLES md.fct_price_daily AND md.fct_price_daily_staging;
```

Iceberg/Delta: one `MERGE` or partition-overwrite commit is atomic; for multi-table releases swap views as
above. PostgreSQL `CREATE OR REPLACE VIEW` cannot drop, rename or retype columns; for such a release run
`DROP VIEW` and `CREATE VIEW` inside the same transaction.

### Acceptance checks

- A replay from captures spends zero API calls (budget ledger unchanged).
- A planted difference outside the declared scope stops the swap.
- During the swap, readers see either the old or the new version, never a mix (concurrent read test).
- Rolling back restores the previous view definitions and the previous numbers exactly.

---

## 16. Research-engineering patterns: trial registry, Polars, DuckDB over raw captures

**Use when** a research or ML workflow on EODHD data needs every trial traceable to its inputs, or uses
Polars / DuckDB directly on the archive.

**EODHD inputs**: none at research time; the captures and normalized tables of §6 and the capture IDs they
carry.

### Trial registry keyed by a config hash

1. Canonicalize everything that changes a result into one JSON object: universe definition, feature and
   label definitions with versions, date ranges and holdout, cost model, code commit, and the capture IDs
   (or the archive snapshot) read. `config_hash = sha256(canonical JSON)[:16]`.
2. Tables keyed by it: `trial(config_hash, created_at, config_json, author, status)`,
   `training_run(run_id, config_hash, fold, metrics_json)`, `prediction(run_id, listing_id, session_date,
   value)`, `backtest(run_id, config_hash, verdict, metrics_json)`.
3. Keep **every** trial, including failed and abandoned ones: the trial count feeds the deflated Sharpe
   and multiple-testing corrections ([methods-quant-research.md](methods-quant-research.md) §3.1, §3.3,
   §3.9). Deleting losers biases every later statistic.
4. A re-run with the same hash must reproduce the stored metrics within numeric tolerance; a difference
   means the inputs changed (new capture, restated `adjusted_close`) and the run gets a new hash.

### Polars: lagged per-listing features and as-of joins

- `over("listing_id")` scopes `shift` and rolling windows to one listing, so no value crosses listings.
- A feature used at session `t` is shifted so it uses data through `t − 1` (or through `t` if the decision is
  made after the close and executed at `t + 1`; state which).
- Slow data (captured Fundamentals fields, symbol-list attributes) join with `join_asof(strategy="backward",
  tolerance=…)` on the **capture date**, by `listing_id`; anything older than the tolerance becomes null
  rather than stale.
- `scan_parquet` + `filter` pushes the predicate into the Parquet scan (check `explain()`); `collect` only
  what the step needs.

```python
import hashlib, json
import polars as pl

def config_hash(cfg: dict) -> str:
    """Stable key for one trial: canonical JSON of everything that changes the result."""
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]

# Polars: per-listing lagged features (no look-ahead) and an as-of join of slow data
px = pl.DataFrame({
    "listing_id": [1, 1, 1, 1, 2, 2, 2],
    "session_date": pl.Series(["2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05",
                               "2026-03-02", "2026-03-03", "2026-03-05"]).str.to_date(),
    "adjusted_close": [100.0, 102.0, 101.0, 104.0, 50.0, 49.0, 51.0],
}).sort("listing_id", "session_date")

feat = px.with_columns(
    (pl.col("adjusted_close") / pl.col("adjusted_close").shift(1) - 1).over("listing_id").alias("ret_1d"),
).with_columns(
    pl.col("ret_1d").shift(1).over("listing_id").alias("ret_1d_lag1"),   # value known before the session
)

fund = pl.DataFrame({                       # e.g. a captured Highlights field, keyed by capture date
    "listing_id": [1, 2],
    "captured_on": pl.Series(["2026-03-03", "2026-02-01"]).str.to_date(),
    "pe": [25.0, 12.0],
}).sort("listing_id", "captured_on")

panel = feat.sort("session_date").join_asof(
    fund.sort("captured_on"), left_on="session_date", right_on="captured_on",
    by="listing_id", strategy="backward", tolerance="21d")              # older than 21 days -> null
```

### DuckDB directly over raw JSON captures

```sql
-- captures/eod/<capture_date>/<SYMBOL>.json; pin the columns so a file of integer-only prices
-- does not change the inferred type, and keep the file name as lineage
select regexp_extract(filename, '([^/]+)\.json$', 1)            as symbol,
       regexp_extract(filename, 'eod/([0-9-]+)/', 1)::date        as captured_on,
       date::date as session_date, open, high, low, close, adjusted_close, volume
from read_json_auto('captures/eod/*/*.json', filename = true, union_by_name = true,
                    columns = {date: 'VARCHAR', open: 'DOUBLE', high: 'DOUBLE', low: 'DOUBLE',
                               close: 'DOUBLE', adjusted_close: 'DOUBLE', volume: 'BIGINT'})
order by symbol, session_date;
```

Keys not listed in `columns` (a new `vwap` field) are ignored here; the §10 contract diff is what reports
them.

### Pitfalls

- A config hash that omits the capture IDs makes two runs on different restatements look identical.
- `shift(1)` without `over(...)` leaks the previous listing's last value into the next listing's first row.
- A return computed across a missing bar (listing 2 in the fixture has no 2026-03-04 row) spans two
  sessions; flag it or require consecutive sessions from the calendar.
- A Fundamentals capture taken after the close of day `t` is first usable at `t + 1`.

### Acceptance checks (Polars 1.20, DuckDB 1.5)

- `ret_1d_lag1` is null on the first two rows of each listing and equals the previous row's `ret_1d`
  afterwards (listing 1, 2026-03-04: 0.02).
- The as-of join gives listing 1 `pe = 25.0` from 2026-03-03 onward and null before; listing 2's capture
  from 2026-02-01 is 29+ days old, so its `pe` is null under the 21-day tolerance.
- `scan_parquet(...).filter(...).explain()` shows the `SELECTION` inside the Parquet scan.
- `config_hash` is identical for the same config with keys in another order and differs when `cost_bps`
  changes.
- The DuckDB query over two capture files returns 3 rows with `symbol` and `captured_on` from the paths,
  and a `null` volume stays null.
