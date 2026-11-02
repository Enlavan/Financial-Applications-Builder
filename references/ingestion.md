# Acquisition, backfill and replay

> Methods with formulas, steps and acceptance checks: [data-engineering-patterns](data-engineering-patterns.md).

## Contract first

For each dataset declare request path and parameter names, response envelope, pagination method, event-date field, retrieval timestamp, natural key, account scope, expected cadence, and row-level units. Estimate requests and weighted calls before starting a large backfill. Bulk EOD may reduce requests for an exchange/day; it does not supply bulk fundamentals entitlement.

Select representative samples before the full universe. A coverage probe reports requested extent, returned extent, row count, duplicate count, null fields, gap intervals and API status. First/last dates alone do not certify completeness. Test the user's own key for access when authorized; a demo or another account is not an entitlement test.

## Reliable request loop

1. Normalize and encode parameters with an HTTP library. Do not concatenate unescaped filters, symbols or dates.
2. Apply connection/read timeouts, bounded retry count, and an overall work budget. Retry transient transport failures, 429 and selected 5xx with exponential backoff plus jitter and bounded `Retry-After`; do not loop on 401/403/422.
3. Capture exact response bytes and safe request metadata before parsing. Retain status, content type, retrieval UTC time, checksum, endpoint, nonsecret parameters and code version. Account-detail responses can contain personal information; keep those captures private and out of fixtures.
4. Check status and envelope. An HTML login/error body is not a CSV or JSON dataset. A nonempty error object is not a valid market record.
5. Stage, validate, then commit the normalized partition. Advance the checkpoint only after the write succeeds.
6. Finish with counts, coverage, failed windows, retries and estimated quota consumed. Do not label a partial run complete.

## Pagination and windows

Each page belongs to a fixed logical query. Store its filters, offset/cursor and checksum. Stop on documented termination; detect identical/repeated next links or pages. Empty pages do not automatically mean the requested historical interval is complete. Keep pagination tokens out of public logs if they contain credentials.

Date windows need explicit inclusive/exclusive rules. Deliberately overlap boundary dates where endpoint semantics warrant it, then deduplicate on the natural key. An overlap is not a substitute for checking all requested windows. Intraday requests use documented Unix-time boundaries; never interpret midnight UTC as an exchange's session open. Respect per-request maximum ranges and observed coverage without hardcoding a lifetime guarantee.

An unstable offset dataset can change during a scan. Prefer bounded event dates and stable sorting when supported. Otherwise record the scan as an observation, re-scan recent windows and compare counts/keys; do not claim an atomic snapshot.

## Incremental updates are not append-only

Corporate actions and historical values may be corrected in place. Maintain a rolling refresh window plus periodic longer reconciliation appropriate to the use case. When adjusted prices change, re-evaluate the affected historical factor range rather than updating just the newest row. Keep raw vintages separate from the current normalized view.

Use an idempotency key such as `(dataset, symbol, query-window, capture-hash, transform-version)`. A retry must not duplicate dividends, trades or holdings. Keep a checkpoint journal and failure queue. Recover by replaying the smallest affected partitions from raw captures; avoid deleting the archive to restart a job.

## Quota/cost and storage controls

Cache symbols and slowly changing metadata; batch only where supported; use response filters for necessary fields; query an exchange snapshot once rather than once per UI user. Do not return a million rows to an LLM when a deterministic aggregate answers the question. Use bounded concurrency and one limiter per applicable key/quota pool. A larger server does not increase the API allowance.

Compress immutable captures and partition normalized data for the dominant queries. Separate fresh, stale, failed and unavailable states. A stale-but-valid cached result may be useful for a research chart if labelled; it must not silently satisfy a trading freshness gate.

## Practical replay tests

- Fail halfway through a page/window; resume without omitted or duplicate rows.
- Return a repeated next link; stop with an explicit error.
- Replay an identical body; no duplicate logical events.
- Return corrected data under the same key; preserve old capture and update the current view with lineage.
- Return 429 or 403; ensure bounded retry versus immediate diagnosis.
- Cross a holiday, DST boundary or inclusive date edge; reconcile requested and returned sessions.
