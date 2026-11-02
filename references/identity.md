# Security identity and historical universes

## Separate issuer, security and listing

An issuer can have several securities; one security can trade on several exchanges/currencies. Assign local IDs at the level the application actually models. Preserve `Code`, exchange, name, type, primary ticker, ISIN/FIGI/CUSIP/CIK/LEI where returned, and observation timestamp. A CIK identifies a filer, not every economic security; an ISIN may span listings; ticker symbols are reused.

Resolve symbols with EODHD Search, exchange lists, Fundamentals `General`, and ID Mapping. Return candidates when the identifier is ambiguous; do not select the first search hit merely because it has the right name. Verify type, exchange, currency, issuer and dates before merging histories. Primary-ticker hints improve joins but are not proof that two series are interchangeable.

## Renames and reuse

A rename usually leaves the economic security continuous, but old/new API codes can coexist while metadata catches up. Treat confirmed aliases as one security in a research universe, select a documented canonical listing/history, and preserve the alias evidence. Do not count duplicate identifiers as separate investment opportunities or erase legitimate cross-listings.

Reused symbols need separate security identities. Suffixes such as `_old`, `_old1` and `_old2` are useful clues, not a universal chronological rule. Historical names can reflect current users of the symbol; validate the relevant interval. Never splice histories on matching ticker text alone.

The symbol-change-history API has a documented coverage start and plan access. It cannot reconstruct every earlier rename. Current mapping supplies useful identifiers for constituents; it does not itself supply their historical effective dates. Store current mappings as observed, without inventing historical validity.

## Build an available universe

1. Fetch active and `delisted=1` symbol lists for the relevant exchanges; preserve dated captures.
2. Normalize types and identifiers. Keep ambiguous units, warrants, rights, preferreds or trust classifications flagged for the strategy's inclusion policy.
3. Probe first/last available bars and intervals for selected securities. These are observed coverage boundaries, not listing/delisting/suspension dates.
4. If using an index, request its supported historical product with explicit dates and historical mode. Preserve membership rows and missing dates; current constituents cannot stand in for a past universe.
5. Apply a recorded eligibility policy at each decision date: security type, known membership, observed trading availability, liquidity and unresolved identity status.

Including delisted symbols reduces a source of survivorship bias, but does not certify a complete historical universe. Absent merger cash payments, old identity mappings, trading suspensions and incomplete member histories remain material limitations.

## Index constituents

Fundamentals offers historical S&P 500 components for `GSPC.INDX`; other supported index history may require the separate Marketplace historical-constituents product. Do not assume all indices have the same history or field semantics. Use `historical=1` for dated Marketplace requests where required and validate the returned date scope.

`StartDate=null` is unknown, not “included since inception.” A row count is not a completeness guarantee. `IsDelisted` and current-membership flags describe current state, not a historical classification at every date. Joining/leaving date boundaries and weekend dates need explicit interpretation. An endpoint without announcement timestamps cannot prove when a change became knowable. Re-entry may require multiple membership intervals; verify whether the response actually represents them.

Validate: unique economic securities per snapshot, overlapping intervals, future/unordered dates, named issuer consistency, duplicated ISINs explained by listings, weights if supplied, and count deviations. Do not rewrite an official index universe to an expected round number to make checks pass.
