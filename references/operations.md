# Scheduling, observability and maintainability

> Methods with formulas, steps and acceptance checks: [data-engineering-patterns](data-engineering-patterns.md).

## Job design

Separate acquisition, validation, transformation and publishing. Use partitioned jobs keyed by dataset/date/symbol group, with idempotent writes and checkpoint state. A scheduler can be cron, an application worker, Dagster, Airflow or another existing tool; choose the smallest adequate system. Do not add cloud infrastructure the workload does not need.

Schedules follow expected dataset availability with retry windows, not a claim of guaranteed issuer update time. Keep live/session jobs separate from historical refresh/reconciliation. Backfills should have bounded parallelism, estimated quota, pause/resume and a target partition list. Reprocessing one failing partition must not republish unrelated data.

## Metrics and alerts

Track successful/failed requests, retry rates, quota estimates, latency, rows, missingness, last observation, last successful capture, normalization lag, stale outputs and checkpoint progress. Separate application availability from data freshness. Use actionable alerts with deduplication and recovery notifications; do not spam every missing optional field.

## Version and release discipline

Pin application dependencies and transformation versions. Test schemas/calculations offline; keep live smoke tests small and opt-in with authorized credentials. Use staged deployment and rollback of application versions/serving views. Preserve old raw captures to reproduce changed calculations. Do not run unreviewed setup scripts or hooks.

## Failure handling

For schema changes, preserve the response, stop incompatible normalization, and produce a contract difference. For quota exhaustion, stop or defer according to policy rather than repeatedly retrying. For authentication failure, ask the user to configure credentials without printing them. For partial coverage, publish an explicitly partial research result when useful and safe; don't pretend the failed partitions are empty valid datasets.

## Security and recovery

Use least-privilege application access, protected backups and token-free logs. Test restore of raw captures, local identifiers, portfolios and job state. User portfolio/account data is sensitive even if the price API is public-facing. Rotate exposed credentials through the user's account workflow; do not embed a key into an example to make it runnable.

Document the few operational facts another maintainer needs: how to run, inputs/outputs, quota assumptions, checkpoint/replay, validation and recovery. Keep those in the generated application as appropriate, not as extra installation rituals for every analysis task.
