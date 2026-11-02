# Dashboards, charts and application engineering

> Methods with formulas, steps and acceptance checks: [app-ai-patterns](app-ai-patterns.md).

## Build for the user's decision

A useful investing screen exposes holdings/watchlist, dated valuation, changes, filters and drill-down evidence. Prefer a small number of meaningful views over dense decorative metrics. Display interval, currency, adjusted/raw basis, observation time and stale/missing state close to the values they qualify. Do not bury these distinctions in developer-only logs.

## Server/client split

Keep the EODHD token on the server. The browser calls authenticated application routes returning only the necessary dataset. Cache with keys including symbol, interval, basis, dates and relevant user entitlement scope. A cache for one account must not leak data to another. Validate query ranges and field allowlists; do not expose an arbitrary paid-API proxy.

For a private local Streamlit app, use session state for interactions and deliberate caching for immutable or freshness-bounded data. Cache invalidation should match the dataset's revision behavior. Do not let rerenders redownload a universe. Pin dependencies in the application and consult the installed version's API before using library-specific features.

## Chart correctness

Use actual calendar dates for daily candles and UTC timestamps for intraday, converting only for display. Sort and deduplicate before setting chart data. Respect the chart library's timestamp units and unique-time rules. Keep volume on a distinct scale and label adjustment basis. Null/missing bars should create gaps/whitespace unless a visibly derived carry-forward display is intended.

Initialize chart instances once, update incrementally where appropriate, resize responsively, and remove listeners/subscriptions on unmount. Do not mutate historical series with a live snapshot that has different price/session semantics. A current provisional candle is distinct from a completed historical candle.

For Lightweight Charts or another ordinary plotting library, follow its installed version's series/plugin interfaces. These are visualization dependencies, not financial-data services. Downsampling must preserve relevant extrema/volume and be labelled; averaging closes into a candle is wrong.

## States, accessibility and performance

Provide loading, empty, partial, stale, no-access and error states with actionable messages. Do not turn every empty response into a subscription upsell. Use accessible colour contrast, keyboard controls, tabular alternatives and text labels beyond red/green. Format numbers with units and precision appropriate to the asset; retain full precision in calculations.

Avoid fetch waterfalls, duplicate requests and unnecessary large client payloads. Debounce expensive search, cancel superseded requests, bound result tables and preserve user selections. Use background jobs for backfills; the UI should show progress/checkpoints rather than freeze.

## Verification

Test empty/partial responses, unsupported access, long ticker names, multiple currencies, decimal precision, missing series, timezones, filters, download contents and mobile layout. Check browser console/runtime errors and API failure recovery. Use screenshots for actual UI verification when appropriate, but do not replace deterministic data validation with appearance checks.

Public deployment, embeds, group bots, shared dashboards and client-facing tools require appropriate licensing before serving real data. A private authenticated personal dashboard on an internet-facing server is not prohibited merely because the server has a public IP.
