# User-owned storage and data contracts

> Methods with formulas, steps and acceptance checks: [data-engineering-patterns](data-engineering-patterns.md).

The schemas below are application designs, not EODHD database schemas.

## Three layers

1. **Raw evidence:** exact response bytes, safe request metadata, retrieval UTC time, hash and capture ID. Immutable.
2. **Normalized data:** typed records, resolved listing IDs, standardized units and explicit quality flags; every row links to a capture and transformation version.
3. **Serving/research views:** calculations, features, dashboards and current snapshots. Rebuildable from selected normalized/raw versions.

DuckDB + Parquet is suitable for local analytic scans; SQLite works for a small app's state and jobs; PostgreSQL fits concurrent transactional application needs. Choose distributed processing only after measuring memory, partition size and query latency. Store a daily date as a date and event instants as timezone-aware UTC timestamps.

## Suggested grains

| Dataset | Grain / key | Fields that prevent ambiguity |
|---|---|---|
| Price observation | listing + session + interval + basis + capture | raw OHLC, adjusted close, volume basis, currency, unit multiplier, session timezone |
| Corporate action observation | listing + event type + ex-date + event identity if available + capture | payment/record/declaration dates, value, unadjusted value, ratio, currency, status |
| Financial fact | issuer/listing + statement + period + field + capture | annual/quarterly/YTD duration, statement currency, units, publication time if known |
| Identifier observation | listing + identifier type + value + capture | issuer/security/listing role, asserted validity versus observed date |
| Membership observation | index + member + interval/as-of query + capture | joining/leaving dates, current flags, unresolved boundaries |
| Portfolio transaction | account + broker/user transaction ID | trade/settlement time, quantity, raw fill price, fees, cash currency |
| Feature | security + decision time + feature version | parent capture IDs, latest admissible input time, missingness/quality state |

Ticker alone is not a timeless primary key. Assign local immutable IDs and retain mapping evidence. ISIN is not a unique exchange listing. Store metadata history instead of replacing old issuer names during symbol reuse.

## Type and null rules

Use Decimal or a documented integer minor-unit representation for cash/fees; analytical float arrays are fine where a stated numerical tolerance is appropriate. Preserve identifier leading zeros. Preserve original values beside normalized ones. Distinguish absent field, JSON null, numeric zero, empty array, parse error and unavailable entitlement.

Use explicit `price_currency`, `statement_currency`, `distribution_currency`, `reporting_currency`, `price_unit_multiplier`, and FX date/rate orientation. Do not infer a statement's currency from the listing suffix. A `value` field means nothing without dataset context.

## Schema evolution

Version contracts. Additive optional fields can be compatible; key/type/unit changes are breaking. Stage new schemas, validate representative historical partitions, run dual calculations where material, and cut over with rollback of serving views. Do not rewrite old raw bytes. Deprecate fields with a migration map instead of silently changing meaning.

For dbt-style transformations, declare source grains, uniqueness, relationships, accepted values and custom unit/freshness checks. Incremental models must include correction windows and deduplication; `max(date)` append logic misses historical revisions. Snapshot metadata/facts only when their changing values matter to the task. Use model dependencies for targeted rebuilds; avoid a full warehouse refresh for a local field fix.

## Query patterns

Partition large price panels by coarse date and exchange/dataset, sorting by listing and time within files. Avoid millions of tiny per-ticker files. Push date/column filters down; select only needed fundamentals sections; cache expensive joins at a declared grain. Test join cardinality: a one-to-many identifier mapping can multiply every price row.

Use an as-of view only after defining which timestamp governs admissibility. For a local archive, select the latest capture at or before the decision time and then the appropriate record within that capture. A dataset first retrieved today cannot answer what the API contained years earlier.
