# Advisory, firm, fund and compliance applications

> Methods with formulas, steps and acceptance checks: [methods-fundamentals-valuation](methods-fundamentals-valuation.md), [methods-planning-wealth](methods-planning-wealth.md), [methods-performance-risk](methods-performance-risk.md).

These workflows describe useful methods without claiming that EODHD supplies private account, legal, identity-verification or execution systems. Company/team/client/public use requires the appropriate commercial licence. Market-data entitlement alone is not authorization to redistribute or advise clients.

## Advisory and client reporting

Combine user-authorized holdings/transactions/objectives with EODHD prices and fundamentals. Define benchmarks, mandate constraints, risk budgets, cash needs and review cadence. Build proposal/review documents with clear assumptions, costs, concentrations and scenario outcomes. A suitability conclusion cannot be generated from market data alone; required client facts and jurisdictional review remain separate.

Method sections for this work: composite returns and internal dispersion ([methods-performance-risk §5.5](methods-performance-risk.md#55-composite-returns-and-internal-dispersion-gips-style-calculation)), the client report's goal-progress panel and narrative rules (§7.7), the holdings trigger catalogue and ranked action queue (§11.4), model sleeves and held-away assets (§15.5), and fund-fee evaluation with the breakeven information ratio (§6.1).

A CRM/account lifecycle can track document status, consent, tasks and review dates using supplied records. Do not invent KYC identity verification, bank account opening, transfers, billing or custody endpoints. Keep personal records access-controlled and minimize copies sent to an LLM.

## Fund operations

NAV reconciliation combines prices with actual positions, cash, accrued income, liabilities, fees and share capital. Tie holdings, general-ledger balances and administrator statements; record breaks with owner, cause, age and resolution evidence. Price-source availability does not replace transaction/custody evidence.

Accrual schedules need basis, rate, day count, period, opening balance, movements and closing balance. Roll-forwards and variance commentary should reconcile mechanically before narrative generation. Performance fees require actual contract terms, high-water marks/hurdles and crystallization rules. Do not fill absent terms with a default industry convention.

### Price check against custodian or administrator prices

**Use when:** an administrator, custodian or broker valuation file must be checked against an independent
market close before NAV sign-off. The valuation file and its prices are **user-supplied**; EODHD supplies
the comparison close. A match is evidence that the price is plausible, not that the holding exists.

**EODHD inputs:** `/api/eod/{SYM}` raw `close` on the valuation date (1 call per symbol, or
`eod-bulk-last-day/{EX}?date=` at 100 calls per exchange-day), normalized to major units (GBX/ZAC ÷ 100);
`/api/splits/{SYM}` (1 call) for corporate-action breaks; `*.FOREX` for currency conversion;
`/api/v2/exchange-details/{EX}` for holidays.

**Method:**

1. Resolve each line to an EODHD listing (ISIN via `/api/id-mapping`, see [identity](identity.md)); an
   unresolved line is a `source` break, not a skip.
2. Normalize both sides: same currency and unit, raw (not adjusted) price, same valuation date.
3. `diff = P_custodian / P_EODHD − 1`. Tolerance per asset class, user-set (illustrative defaults:
   listed equity and ETFs 0.5%, bond ETFs 0.25%, FX 0.1%).
4. **Stale flag** when EODHD has no bar on the valuation date (holiday, suspension, late listing); compare
   with the last bar and mark the result `ok_stale` or a break.
5. **Break class** for differences outside tolerance: `unit` (ratio ≈ 100 or 0.01 — GBX/GBP, cents);
   `corporate_action` (ratio ≈ a split ratio dated within 5 days — one side not adjusted yet); `timing`
   (the custodian price matches an adjacent session's close); otherwise `source`.
6. **Aging:** each break keeps `first_seen`; report age in days, owner and resolution evidence, oldest
   first within each class.

```python
import datetime as dt

TOL = {"equity": 0.005, "etf": 0.005, "bond_etf": 0.0025, "fx": 0.001}   # user-overridable, labelled

def price_check(rows, eodhd, splits=None, tol=TOL, as_of=None):
    """rows: [{"symbol", "asset_class", "date", "price", "ccy", "first_seen"?}] custodian/administrator
    prices (user-supplied). eodhd: {symbol: [(date, raw close normalized to major units)]} sorted.
    splits: {symbol: [(date, ratio new/old)]}. Returns one result per row."""
    out = []
    for r in rows:
        bars = eodhd.get(r["symbol"], [])
        on = dict(bars)
        res = {"symbol": r["symbol"], "date": r["date"], "custodian": r["price"]}
        if not bars:
            out.append({**res, "status": "break", "class": "source", "reason": "no_eodhd_history"})
            continue
        prior = [d for d, _ in bars if d <= r["date"]]
        ref = on.get(r["date"])
        res["eodhd"] = ref if ref is not None else (on[max(prior)] if prior else None)
        res["stale"] = ref is None                     # no EODHD bar on the valuation date
        if res["eodhd"] is None:
            out.append({**res, "status": "break", "class": "source", "reason": "no_bar_on_or_before"})
            continue
        diff = r["price"] / res["eodhd"] - 1
        res["diff"] = round(diff, 6)
        t = tol[r["asset_class"]]
        if abs(diff) <= t:
            res.update(status="ok" if not res["stale"] else "ok_stale", **{"class": None})
        else:
            ratio = r["price"] / res["eodhd"]
            near = lambda x, y: abs(x / y - 1) < 0.01
            ca = [k for d, k in (splits or {}).get(r["symbol"], [])
                  if abs((dt.date.fromisoformat(d) - dt.date.fromisoformat(r["date"])).days) <= 5]
            if near(ratio, 100) or near(ratio, 0.01):
                cls = "unit"                                     # GBX/GBP, ZAc/ZAR, cents
            elif any(near(ratio, k) or near(ratio, 1 / k) for k in ca):
                cls = "corporate_action"                         # one side not split-adjusted yet
            elif any(abs(r["price"] / c - 1) <= t for d, c in bars
                     if d != r["date"] and abs((dt.date.fromisoformat(d) -
                                                dt.date.fromisoformat(r["date"])).days) <= 3):
                cls = "timing"                                   # matches an adjacent session
            else:
                cls = "source"
            res.update(status="break", **{"class": cls})
        if res["status"] == "break" and as_of:
            res["age_days"] = (as_of - dt.date.fromisoformat(r.get("first_seen", r["date"]))).days
        out.append(res)
    return out
```

**Pitfalls:** fund NAVs and OTC-priced holdings have no exchange close; mark them "not checkable" rather
than comparing with an ETF proxy. Custodians may use a different price point (official close, bid,
evaluated price); record which. An EODHD late correction can create a break on re-run; keep the capture
used.

**Acceptance checks** (valuation date 2026-09-30, run 2026-10-02): custodian 101.30 vs EODHD 101.00 →
`ok` (0.297%); 450.00 vs 4.50 → `unit`; 50.10 vs 52.00 with 50.00 on 09-29 → `timing`; 120.00 vs 30.00 with
a 4:1 split on 09-30 → `corporate_action`; 80.00 vs a last bar on 09-29 of 80.00 → `ok_stale`; 21.00 vs
20.00, first seen 09-25 → `source`, age 7 days.

### Ledger-to-subledger reconciliation

**Use when:** general-ledger balances must tie to a subledger (positions, cash, accruals) or to an
administrator or custodian statement. Both ledgers are **user-supplied**; EODHD supplies only the FX and
price references that explain some breaks.

**EODHD inputs:** `*.FOREX` close on the posting date (EOD, 1 call per pair) for FX-rate breaks; raw close
on the valuation date for price breaks (price check above).

**Method:**

1. **Coerce keys and types:** trim and upper-case identifiers, strip leading zeros on numeric account
   codes, ISO dates, decimal amounts. Keep the original values beside the normalized key.
2. **Full outer join** on the normalized key (e.g. account + security, or account + transaction reference).
3. **Bucket** each pair, in this order: `gl_only`, `sub_only`; `quantity` (quantities differ); `timing`
   (amounts agree within tolerance but posting dates differ by ≤ N days); `fx_rate` (local amounts agree,
   base amounts differ); `amount` (anything else outside tolerance); otherwise `matched`.
4. **FX-break test:** for an `fx_rate` break, compute each side's implied rate `base / local` and compare
   with the EODHD `*.FOREX` close on the posting date; the side more than a tolerance (e.g. 5 bp) away is
   off-market. A market close is not an official fixing; if the fund's policy names a fixing, the close
   only indicates which side is suspect.
5. **Price-break test:** for position lines, run the price check above on the valuation date.
6. **Summary** by bucket (count, Σ|Δ|), breaks sorted by |Δ|, each with owner, age and resolution evidence.
   The reconciliation passes only when every break is resolved or explicitly accepted.

```python
def norm_key(*parts):
    """Coerce join keys: strip, upper-case, drop leading zeros on account numbers, ISO dates."""
    out = []
    for p in parts:
        s = str(p).strip().upper()
        out.append((s.lstrip("0") or "0") if s.isdigit() else s)
    return tuple(out)

def reconcile(gl_rows, sub_rows, key_fields, tol_amount=0.01, tol_qty=0.0, timing_days=3,
              fx_close=None, fx_tol=0.0005):
    """Full outer join of GL and subledger rows on normalized keys.
    rows: dicts with key fields plus "amount_base", optional "amount_local", "ccy", "qty", "date".
    fx_close: {(ccy, date): EODHD *.FOREX close in base per unit of ccy} for the FX-break test.
    Buckets: matched | amount | quantity | fx_rate | timing | gl_only | sub_only."""
    gl = {norm_key(*(r[k] for k in key_fields)): r for r in gl_rows}
    sub = {norm_key(*(r[k] for k in key_fields)): r for r in sub_rows}
    breaks = []
    for k in sorted(set(gl) | set(sub)):
        g, s = gl.get(k), sub.get(k)
        if g is None or s is None:
            row = g or s
            breaks.append({"key": k, "bucket": "sub_only" if g is None else "gl_only",
                           "delta": row["amount_base"] * (1 if g else -1), "date": row.get("date")})
            continue
        d_amt = g["amount_base"] - s["amount_base"]
        d_qty = g.get("qty", 0) - s.get("qty", 0)
        dates_differ = g.get("date") and s.get("date") and g["date"] != s["date"]
        if abs(d_qty) > tol_qty:
            bucket = "quantity"
        elif abs(d_amt) <= tol_amount:
            within = dates_differ and abs((_d(g["date"]) - _d(s["date"])).days) <= timing_days
            bucket = "timing" if within else "matched"
        elif ("amount_local" in g and "amount_local" in s
              and abs(g["amount_local"] - s["amount_local"]) <= tol_amount):
            # local amounts agree, base differs: test both rates against the posting-date close
            ref = (fx_close or {}).get((g["ccy"], g["date"]))
            rates = {side: r["amount_base"] / r["amount_local"] for side, r in (("gl", g), ("sub", s))}
            off = {side: (None if ref is None else abs(v / ref - 1) > fx_tol) for side, v in rates.items()}
            breaks.append({"key": k, "bucket": "fx_rate", "delta": d_amt, "rates": rates,
                           "eodhd_close": ref, "off_market": off})
            continue
        else:
            bucket = "amount"
        if bucket != "matched":
            breaks.append({"key": k, "bucket": bucket, "delta": d_amt, "qty_delta": d_qty})
    summary = {}
    for b in breaks:
        x = summary.setdefault(b["bucket"], {"count": 0, "abs_delta": 0.0})
        x["count"] += 1
        x["abs_delta"] += abs(b["delta"])
    return sorted(breaks, key=lambda b: -abs(b["delta"])), summary

def _d(s):
    import datetime as dt
    return dt.date.fromisoformat(s)
```

**Pitfalls:** many-to-one matches (one GL line against several subledger lots) need aggregation to the GL
grain before joining; signs may be reversed between systems (normalize to one convention); a tolerance
that is too wide hides real breaks — keep it at the currency's minor unit for cash.

**Acceptance checks:** GL key `001200`/`aapl.us` matches subledger `1200`/`AAPL.US` with a 0.004
difference; TSLA only in the GL → `gl_only` 9,000; MCD only in the subledger → `sub_only` −3,000; SAP with
equal local amounts 20,000 EUR and base 21,960 vs 22,400 → `fx_rate`, implied rates 1.098 vs 1.120, EODHD
close 1.1200 → the GL side is off-market; MSFT quantities 100 vs 90 → `quantity`; VTI equal amounts posted
09-29 vs 09-30 → `timing`; AMZN 1,000 vs 1,100 → `amount`. Order by |Δ|: 9,000, 3,000, 440, 100, 0, 0.

## Risk, trade controls and audit trail

> Template: [governance manifest](../assets/governance-manifest.md) — claims tied to evidence, scope, controls verified only after a test saw them fire, known limitations.

Pre-trade simulation can check exposure, cash, concentration, liquidity and mandate rules using available inputs: the [rule engine](methods-performance-risk.md#164-pre-trade-checklist-all-must-pass-and-rule-engine) applies hard and soft limits, a restricted list matched at issuer level across share classes, and an append-only override log; leverage and shorts use the [margin model](methods-performance-risk.md#166-margin-model-for-paper-trading-and-backtests) with user-supplied terms. Post-trade reconciliation needs actual fills and settlements supplied by the user. Operational risk, counterparty exposure, margin and settlement controls depend on additional data that EODHD does not provide.

Record decisions, inputs, rule versions, exceptions and reviewer actions. An immutable log is useful evidence but not a certification of regulatory compliance. Do not describe performance as GIPS-compliant or a screening workflow as AML-complete solely because a checklist was followed. Backtests and other hypothetical results shown to others pass the [presentation checklist](methods-performance-risk.md#76-backtest-and-hypothetical-performance-presentation-checklist) first.

## Investment banking and private equity

Build public comps, market/sector overviews, diligence trackers, financial models, investment-committee memos, transaction scenarios and value-creation plans from verified public EODHD data plus supplied private documents. Maintain an explicit boundary between public observations, management projections, modelling assumptions and unresolved diligence items. Listed strategic acquirers can be screened from EODHD data ([methods-fundamentals-valuation.md](methods-fundamentals-valuation.md)); private buyers, deal terms, confidential forecasts and private-company unit economics are user-provided or unavailable in this EODHD-only workflow.

## Compliance datasets

Available sanctions/risk endpoints can support research and candidate matching. A matched name is not a confirmed identity and an empty result is not clearance. Retain query parameters, observation date, match evidence and ambiguity. Apply jurisdiction-specific rules only from appropriate current authority or user-supplied policy; do not hardcode old or generic thresholds.

For commercial licensing questions, prepare a concise description of datasets, API use, audience, display/download/redistribution, expected users and business model for sales@eodhistoricaldata.com. Do not quote a personal-plan price as a commercial licence.
