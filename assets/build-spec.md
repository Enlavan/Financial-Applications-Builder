# Financial application build specification

## Outcome

- User decision / action:
- Deliverable and scope:
- Audience: private individual / firm / public / other:
- Assets, exchanges, date range, interval, currencies:
- Freshness and reproducibility requirement:

## Capability map

| Input | EODHD endpoint | Required access | Observed coverage | Missing-input treatment |
|---|---|---|---|---|

## Design

- Smallest working vertical slice:
- Raw capture, normalized schema and serving view:
- Natural keys, units, timestamp/basis definitions:
- Calendar, identity and corporate-action policy:
- Cache, pagination, quota and retry budget:
- User-supplied inputs and modelling assumptions:
- Deployment/access restrictions relevant to the audience:

## Metric map (dashboards and reports)

One row per displayed number. A label without a registry id or an explicit formula is not ready to build.
Registry ids and formulas: `references/data-engineering-patterns.md` §11; aggregation rules: same section.

| Label shown | Registry id or formula | Source dataset / view | Grain | Comparison (vs what, period) | Basis (raw / split / total return) | Currency and unit (FX date, GBX/ZAC) |
|---|---|---|---|---|---|---|
| e.g. 1Y return | `total_return` | `serving.price_daily` | listing × session | benchmark `SPXTR.INDX`, same dates | total return | listing currency; base-currency view converts at session close FX |
| | | | | | | |

## Panel freshness

Stale thresholds come from the exchange SLA (`references/data-engineering-patterns.md` §5, contract
`freshness_sla`) for EOD data and from the delayed-quote rule (`references/app-ai-patterns.md` §6) for live
panels. A holiday or weekend is `market closed`, never stale.

| Panel | Data type (EOD, delayed snapshot, stream, fundamentals, user data) | Stale when | UI state on breach |
|---|---|---|---|
| e.g. Watchlist | delayed snapshot, 15-min delay, refreshed each minute | `now − observation_time > 15 + 2 × 1 min` during the session | `stale` badge with observation time; values stay visible |
| e.g. Holdings value | EOD | last bar older than the last completed session after its SLA due time | `EOD <date>` badge turns `stale`; totals marked provisional |
| | | | |

## Completion evidence

- Representative request results (no tokens):
- Domain invariant and failure tests:
- UI/output checks where applicable:
- Unresolved limitations that change interpretation:
- Reproduction command / artifact location:
