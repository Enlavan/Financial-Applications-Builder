# Governance and due-diligence manifest

One manifest per release of a research or trading-simulation system built on EODHD data. It ties every
claim to evidence, separates what is in production scope from research, records which risk controls were
seen to fire, and lists the limitations a reviewer must know. It is an evidence index, not a certification
of regulatory compliance ([professional-workflows.md](../references/professional-workflows.md#risk-trade-controls-and-audit-trail)).
Gates: [methods-quant-research.md](../references/methods-quant-research.md) §3.12. Strategy definition:
[strategy-spec.md](strategy-spec.md). Run records: [research-record.md](research-record.md).

## Header

- manifest_date (UTC):
- system / strategy IDs and versions:
- prepared_by / reviewed_by:
- archive snapshot or capture-ID range read by the runs:
- code commit(s):

## Claims → evidence

Every statement made to a reader (performance, risk, capacity, data quality) gets one row. A claim without a
pointer fails review.

| id | Claim as worded for the reader | Evidence pointer (file, test name, run ID, capture ID) | Scope (production / research) |
|---|---|---|---|
| C1 | | | |

## Scope

- **production_scope**: strategies or models that passed **every** gate G0–G8 (§3.12), each with its gate
  results. Paper trading only unless the user's own execution stack is in scope.
- **research_scope**: everything else, including strategies that passed some gates. Research results are
  never quoted as production performance.

| Strategy / model | Scope | G0 | G1 | G2 | G3 | G4 | G5 | G6 | G7 | G8 | Gate evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|

## Risk controls

`declared_present` = the control exists in code or configuration. `verified_triggering` = an end-to-end test
fed a real NAV or price series (a captured EODHD series or a replay) through the running system and saw the
control fire. A unit test of the threshold function alone is not enough. Controls that never fired in a
test stay `declared_present` only.

| id | Control (kill switch, drawdown halt, exposure cap, loss limit, order-size cap …) | declared_present | verified_triggering | Test name | Input series (capture IDs) | Fired at (date / bar) | Action observed (orders blocked, reason logged; never silent liquidation) |
|---|---|---|---|---|---|---|---|

## Known limitations (mandatory; pre-filled EODHD limits, add system-specific ones)

- No point-in-time vintages: Fundamentals are one current, restated record per period (US statements as filed come only from the SEC Filings API, All-In-One); `adjusted_close`
  and split-adjusted volume are restated over the whole history when an action arrives. Only the system's
  own dated captures show "as retrieved" values.
- No execution data: no historical bid/ask quotes, order-book depth, queue position, borrow availability or
  borrow rates; fills and costs are modelled, not observed.
- Sector and industry classification is current only; historical classification is not available.
- Options: US stocks and ETFs only, end-of-day chains, history from early Q4 2023; no index options.
- Symbol lists carry no effective dates: listing history is dated by capture, from the first capture.
- Identifiers (ISIN, CUSIP, CIK, FIGI, LEI) are current values only.
- WebSocket streams have no history or replay; anything not recorded locally is gone.
- Index membership history is limited (for `GSPC.INDX` from April 2012, re-entries collapsed); other indices
  often have current members only.
- System-specific:

## Open items and sign-off

- Unresolved breaks, failed checks, open questions:
- Reviewer decision and date:

## Validation

```python
GATES = [f"G{i}" for i in range(9)]                      # methods-quant-research.md section 3.12

def check_manifest(m: dict) -> list[tuple[str, str]]:
    """Returns (severity, message) findings; FAIL blocks sign-off, WARN needs a reviewer note."""
    out = []
    for c in m.get("claims", []):
        if not any(c.get("evidence", {}).get(k) for k in ("file", "test", "run_id", "capture_id")):
            out.append(("FAIL", f"claim without evidence pointer: {c.get('id')}"))
    for s in m.get("production_scope", []):
        missing = [g for g in GATES if m.get("gate_results", {}).get(s, {}).get(g) != "PASS"]
        if missing:
            out.append(("FAIL", f"{s} in production_scope but gates not passed: {missing}"))
    for rc in m.get("risk_controls", []):
        if rc.get("verified_triggering") and not (rc.get("evidence", {}).get("test")
                                                   and rc.get("evidence", {}).get("fired_at")):
            out.append(("FAIL", f"{rc.get('id')}: verified_triggering without a test that saw it fire"))
        if rc.get("declared_present") and not rc.get("verified_triggering"):
            out.append(("WARN", f"{rc.get('id')}: declared but never seen firing"))
    if not m.get("known_limitations"):
        out.append(("FAIL", "known_limitations is empty"))
    return out
```

**Acceptance checks.**

- A claim whose evidence has no file, test, run ID or capture ID → `FAIL`.
- A strategy listed in `production_scope` with any gate other than `PASS` → `FAIL` listing the missing gates.
- A risk control marked `verified_triggering` without a test name and a `fired_at` → `FAIL`; one that is
  only `declared_present` → `WARN`.
- An empty `known_limitations` → `FAIL` (the section is mandatory).
- Fixture (run): claims C1 (with run ID) and C2 (no pointer), `mom_v3` with all gates passed and `carry_v1`
  with G0–G1 only, a drawdown halt with a test that fired on 2020-03-16, a kill switch marked verified with
  no evidence, an exposure cap only declared, no limitations → exactly 3 FAIL (C2; `carry_v1` missing
  G2–G8; the kill switch) and 2 WARN (the exposure cap; empty limitations).
