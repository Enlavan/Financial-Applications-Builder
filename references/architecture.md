# From intention to a working system

## Requirements that change the design

Record the decision or user action the system supports; asset universe; interval and history; input types; audience; refresh cadence; acceptable staleness; expected dataset size; reproducibility requirement; and the smallest useful result. Distinguish “a portfolio dashboard” from brokerage connectivity, and “historical research” from strict historical information-set reconstruction.

Create a capability matrix with `required input → public endpoint → entitlement → observed coverage → fallback`. A fallback can be a coarser supported interval, a smaller verified universe, user-provided data, or a disabled feature with a reason. It cannot silently switch providers or fabricate a field.

## Choose complexity from the workload

| Workload | Appropriate starting architecture |
|---|---|
| One-off analysis/sample | Bounded collector, JSON/CSV, deterministic notebook or script |
| One person's daily research | Python package, SQLite or DuckDB, Parquet archive, scheduled process, optional Streamlit |
| Interactive app with shared deployment | Server-side EODHD adapter, authenticated application service, relational store/cache, background workers, licensed audience |
| Large research panels | Partitioned Parquet, manifest/catalog, DuckDB/Polars initially; distributed execution only when measurements justify it |
| Streaming display/simulation | Connection supervisor, event buffer, event-time normalization, bar builder, freshness state, durable capture if needed |
| Auditable research programme | Immutable captures, versioned transformations, experiment registry, temporal joins, explicit information-set contract |

Keep acquisition, normalization, domain calculations, and presentation separate. A chart should not fetch a different price basis than the portfolio calculator. Keep domain functions pure where possible; wrap I/O in adapters that can be tested with fixtures. Put library versions in the target application's dependency lock, not in speculative hardcoded skill instructions.

## Implementation sequence

1. Probe representative examples: one common stock, one delisted/renamed security if relevant, one non-US listing, one incomplete response, and one unsupported request. Do not spend a user's quota on an entire universe to discover a design error.
2. Define field names, grain, units, timestamps, null meaning, schema version, and key constraints. Use `assets/dataset-contract.json` as a starting point.
3. Build one end-to-end slice: request → raw capture → normalized record → calculation → visible output.
4. Add checkpointed backfill, bounded retries, scheduling, cache policy, and incremental refresh only to the extent required.
5. Test domain invariants and representative failures before expansion. Keep fixtures synthetic or properly licensed and token-free.
6. Deliver runnable code, configuration examples without secrets, tested commands, and a concise account of verified behavior. Use the user's existing stack and conventions unless they obstruct the requirement.

## Useful boundaries

A service layer exposes normalized application objects, not arbitrary proxy access to a paid API key. A product for others requires suitable licensing; adding login or a server-side proxy alone does not confer redistribution rights. A local research archive may contain private API captures, but a public repository should contain synthetic fixtures.

Do not impose repeated approvals for reversible coding and analysis already authorized. Purchases, publication, live trading, external communication, and changes to another system require authorization appropriate to that action. Building a prototype does not authorize any of those actions.
