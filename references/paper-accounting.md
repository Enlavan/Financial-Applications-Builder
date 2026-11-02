# Paper trading, journals and portfolio accounting

> Methods with formulas, steps and acceptance checks: [methods-planning-wealth](methods-planning-wealth.md), [methods-quant-research](methods-quant-research.md), [methods-performance-risk](methods-performance-risk.md) (sizing, pre-trade rule engine §16.4, margin model §16.6).

EODHD provides market data, not brokerage execution. A paper broker is application code. Live brokerage actions are outside this skill's data integration; do not invent an EODHD order endpoint or add a different service implicitly.

## Simulator state

Maintain accounts, cash by currency, positions/lots, orders, fills, fees, corporate actions and valuations. Use stable local IDs and an append-only event journal. State transitions include submitted, accepted/rejected, partially filled, filled, cancelled and expired. Retrying a request/event must not create a second fill.

Freshness gates require observation timestamps, expected session and maximum age. Unknown or stale prices block simulated execution under a strict gate even when the UI can show the last observation. A quote update is not evidence of a fill. A bar high/low touching a limit does not prove queue priority or sufficient liquidity.

## Accounting

Reconcile opening cash + deposits − withdrawals + trade proceeds − purchases − fees + distributions + other confirmed flows = closing cash. Reconcile opening quantity + buys − sells + share actions = closing quantity. Preserve trade versus settlement dates; a tax lot is not the same as an aggregate position.

For long cash equity, realized P&L uses the declared lot selection and actual fill/basis; unrealized P&L uses a dated mark and compatible units. Shorts, leverage, option assignment, FX and fractional entitlements need separate logic: leverage and shorts use the [margin model](methods-performance-risk.md#166-margin-model-for-paper-trading-and-backtests) with user-supplied ratios and rates; dividends, cash in lieu, mergers and spin-offs use the [corporate-action ledger events](corporate-actions.md#corporate-action-ledger-events). Do not infer missing broker fees or cash-in-lieu from market data.

## Double-entry trading ledger

**Use when:** a paper account or a reconstructed broker account needs statements that tie: P&L, balance
sheet and cash flow derived from one journal, matching the position and lot ledger.

**EODHD inputs:** raw closes for marks (`/api/eod`, normalized GBX/ZAC units), `unadjustedValue` and
`currency` from `/api/div?fmt=json` for dividend cash, `*.FOREX` closes for conversion and revaluation (a
market close, not an official fixing — label it). Trades, fees, deposits, withholding tax and conversions
are application or user records.

**Chart of accounts** (extend as needed; one base currency):

| Account | Type | Normal balance |
|---|---|---|
| `Assets:Cash:{CCY}` | asset, one per currency; lines carry the currency amount and the base amount | debit |
| `Assets:Securities:Cost:{SYM}` | asset at cost (sum of open lot cost) | debit |
| `Assets:Securities:MTM:{SYM}` | asset, mark-to-market adjustment | debit or credit |
| `Equity:Capital` | deposits less withdrawals | credit |
| `Income:Realized`, `Income:Unrealized`, `Income:Dividends`, `Income:FX` | income | credit |
| `Expense:Fees`, `Expense:WithholdingTax`, `Expense:Financing`, `Expense:Borrow` | expense | debit |

**Entries** (debit +, credit −; every entry sums to zero in base currency):

| Event | Lines |
|---|---|
| Deposit | Dr Cash, Cr Capital |
| Buy (fees expensed; capitalizing fees into cost is a user rule) | Dr Securities:Cost, Dr Fees, Cr Cash |
| Mark at close | Dr/Cr Securities:MTM, Cr/Dr Unrealized for the **change** since the last mark: `q·P − cost − MTM balance` |
| Sell | reverse the sold shares' share of the MTM balance; Dr Cash (net proceeds), Dr Fees, Cr Securities:Cost (relieved lot cost), Cr/Dr Realized |
| Dividend (on payment date; entitlement at ex-date per [corporate actions](corporate-actions.md#corporate-action-ledger-events)) | Dr Cash:{div CCY}, Dr WithholdingTax, Cr Dividends |
| FX conversion | Dr Cash:{to} (currency amount, base amount), Cr Cash:{from} |
| FX revaluation of foreign cash | Dr/Cr Cash:{CCY} (base amount only), Cr/Dr FX |
| Margin interest, borrow fee ([margin model](methods-performance-risk.md#166-margin-model-for-paper-trading-and-backtests)) | Dr Financing / Borrow, Cr Cash |

**Method:**

1. Post each event once, keyed by its source event id; a replay returns "already posted".
2. Reject any entry whose base amounts do not sum to zero.
3. **Statements:** P&L = income accounts (credit positive) minus expense accounts; balance sheet = assets
   = capital + retained earnings; cash flow = movements of `Assets:Cash:*` grouped by event type (trading,
   income, fees and financing, FX, capital).
4. **Tie-outs:** `Securities:Cost:{SYM}` = sum of open lot cost in the lot ledger;
   `Cost + MTM` = `q × latest raw close` per symbol; cash per currency = the simulator's cash balance;
   trial balance sums to zero.

```python
from collections import defaultdict

class Ledger:
    """Double-entry journal in a base currency. Each line: (account, base_amount, ccy, ccy_amount);
    debit > 0, credit < 0. An entry that does not balance in base currency is rejected."""
    def __init__(self, base="USD", tol=0.005):
        self.base, self.tol, self.entries = base, tol, []

    def post(self, date, memo, lines, source_id):
        total = sum(l[1] for l in lines)
        if abs(total) > self.tol:
            raise ValueError(f"unbalanced entry {source_id}: {total:+.4f}")
        if any(e["source_id"] == source_id for e in self.entries):
            return False                               # idempotent: a replayed event posts once
        self.entries.append({"date": date, "memo": memo, "lines": lines, "source_id": source_id})
        return True

    def balances(self, upto=None, ccy=False):
        b = defaultdict(float)
        for e in self.entries:
            if upto is None or e["date"] <= upto:
                for acct, amt, c, camt in e["lines"]:
                    b[(acct, c) if ccy else acct] += camt if ccy else amt
        return dict(b)

def trial_balance_ok(ledger):
    return abs(sum(ledger.balances().values())) <= ledger.tol

def statements(ledger, upto=None):
    b = ledger.balances(upto)
    pick = lambda prefix: {k: v for k, v in b.items() if k.startswith(prefix)}
    income = {k: -v for k, v in pick("Income:").items()}          # credits shown positive
    expense = pick("Expense:")
    net = sum(income.values()) - sum(expense.values())
    assets = pick("Assets:")
    capital = -sum(pick("Equity:").values())
    return {"pnl": {**income, **{k: -v for k, v in expense.items()}, "net_income": net},
            "balance_sheet": {"assets": sum(assets.values()), "capital": capital,
                              "retained": net, "check": sum(assets.values()) - capital - net}}

def mark_entry(ledger, date, positions, marks, source_id):
    """Revalue securities to market: post the change in unrealized P&L since the last mark.
    positions: {sym: (qty, cost_base)}; marks: {sym: raw close in base currency (normalized)}."""
    bal = ledger.balances(upto=date)
    lines = []
    for s, (q, cost) in positions.items():
        target = q * marks[s] - cost
        delta = round(target - bal.get(f"Assets:Securities:MTM:{s}", 0.0), 2)
        if delta:
            lines += [(f"Assets:Securities:MTM:{s}", delta, ledger.base, delta),
                      ("Income:Unrealized", -delta, ledger.base, -delta)]
    return ledger.post(date, "mark to market", lines, source_id) if lines else False
```

**Pitfalls:**

- Marking with `adjusted_close` books dividends twice (once as income, once inside the price).
- Revaluing foreign cash and foreign securities at different FX dates creates spurious FX gains.
- A sale without reversing the sold shares' MTM leaves unrealized P&L on shares no longer held.

**Acceptance checks** (values from the code above): deposit 10,000; buy 50 AAPL at 150 (fee 1); mark at
160; dividend 12.50; sell 20 at 170 (fee 1, FIFO); convert 1,000 USD to 925.93 EUR at 1.0800; mark at 165;
revalue EUR at 1.1000. Then: trial balance zero; replaying the buy posts nothing; P&L realized 400.00,
unrealized 450.00, dividends 12.50, FX 18.52, fees −2.00, **net income 879.02**; assets 10,879.02 =
capital 10,000 + retained 879.02; `Cost` 4,500 + `MTM` 450 = 30 × 165 = 4,950; EUR cash 925.93 in
currency. An entry with one 1.00 debit line is rejected as unbalanced.

## Trade journal and performance coaching

Import user-provided CSV/PDF records with field mapping and reconciliation; preserve original files and parse confidence. Separate strategy intent from execution outcome: setup, signal time, planned risk, actual fills, rule adherence, fees, exit reason and notes. Do not optimize a strategy by relabelling losing trades after the fact.

Metrics include expectancy, win rate, average win/loss, profit factor, R-multiples, duration, adverse/favourable excursion, turnover and drawdown. Handle zero denominators and open trades explicitly. Monte Carlo resampling illustrates sequencing sensitivity under chosen assumptions; it does not prove independent outcomes or future profitability. Formulas and edge cases: [methods-planning-wealth §12](methods-planning-wealth.md#12-trade-statement-audit-and-journal-analytics).

**Breakdowns and chase flag.** Group closed trades by setup tag, by holding-period bucket (intraday, 1–5,
6–20, > 20 sessions) and by their combination; show n beside every cell and suppress statistics below a
user minimum (e.g. 20 trades). A long entry is flagged as **chased** when the actual entry exceeds the
planned pivot by more than `max_chase` (default 2%, the same limit as the
[trade-plan worst-case entry](methods-technical-market.md#10-trade-plans-entry-stop-r-targets-time-exit-heat));
trades without a recorded plan are "no plan", not "not chased". Compare expectancy of chased and unchased
trades; wording follows [methods-planning-wealth §12.5](methods-planning-wealth.md#125-behaviour-flags-evidence-based-non-diagnostic-wording).

```python
def holding_bucket(sessions):
    return ("intraday" if sessions == 0 else "1-5" if sessions <= 5 else
            "6-20" if sessions <= 20 else ">20")

def chase_flag(trade, max_chase=0.02):
    """Long entries only: entry above the planned pivot by more than max_chase. None = no plan."""
    if trade.get("planned_pivot") is None:
        return None
    return trade["entry"] > trade["planned_pivot"] * (1 + max_chase)

def breakdown(trades, key, min_n=20):
    """Group closed trades by key(trade); buckets with n < min_n show n only (suppressed)."""
    groups = {}
    for t in trades:
        groups.setdefault(key(t), []).append(t["pnl"])
    out = {}
    for g, p in sorted(groups.items(), key=lambda kv: str(kv[0])):
        n = len(p)
        if n < min_n:
            out[g] = {"n": n, "suppressed": True}
            continue
        wins = [x for x in p if x > 0]
        losses = [-x for x in p if x < 0]
        out[g] = {"n": n, "win_rate": len(wins) / n, "expectancy": sum(p) / n,
                  "profit_factor": (sum(wins) / sum(losses)) if losses else None}
    return out
```

Fixture: 25 breakout trades (3 sessions, 15 winners of 100, 10 losers of −80, 5 entered 3% above the
pivot) and 8 pullback trades without a plan → breakout n 25, win rate 60%, expectancy 28.0, profit factor
1.875; pullback n 8 suppressed; chase groups (minimum 5): chased 5, not chased 20, no plan 8.

## Operational controls

Persist state before acknowledging a critical transition, reconcile on restart, stop on inconsistent balances and surface a repair report. A halt should preserve evidence and distinguish no new orders from liquidation; a margin call blocks new risk and never liquidates silently ([margin model](methods-performance-risk.md#166-margin-model-for-paper-trading-and-backtests)). Paper orders pass the [pre-trade rule engine](methods-performance-risk.md#164-pre-trade-checklist-all-must-pass-and-rule-engine) before a simulated fill. Simulation may run autonomously within the requested scope; sending messages, changing accounts, or executing trades requires separate authorization.
