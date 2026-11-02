# Valuation, integrated models and transactions

> Methods with formulas, steps and acceptance checks: [methods-fundamentals-valuation](methods-fundamentals-valuation.md).

## Build a model that can be changed

Keep historical actuals, explicit assumptions, formulas and checks separate. Preserve an existing workbook's input/formula cells, named ranges, units and scenarios. Use formulas for projections and derived values so the model responds to assumptions. Do not ask for repeated approvals of routine modelling steps; build and validate within the authorized task.

## Three-statement model

Project revenue from stated growth or operating drivers; expense margins; taxes; working capital; capex and depreciation; debt and interest; equity/dividends; and cash. Link net income to cash flow and retained earnings, capex/depreciation to PP&E, debt issuance/repayment to financing cash flow, and ending cash to the balance sheet. State whether interest uses beginning, average or ending debt and avoid unintentional circularity.

Working-capital schedules can use DSO, DIO and DPO with consistent day counts and denominators. Cash release is the negative of an increase in operating working capital under the usual convention. Checks: assets = liabilities + equity; ending cash = beginning cash + net cash flow; retained earnings roll-forward; debt roll-forward; no unexplained balancing plugs.

## DCF

For an enterprise DCF: `FCFF = EBIT * (1 - tax_rate) + D&A - capex - change_in_operating_NWC`. Discount using a currency- and nominal/real-consistent WACC; declare market-value equity/debt weights, risk-free input, beta/ERP and cost-of-debt assumptions. Do not source a nonexistent premium or private forecast from an API field.

Perpetuity terminal value is `FCFF_(n+1) / (WACC - g)` only when WACC > g and long-run assumptions are economically coherent. Exit multiples are a separate method with comparable definitions. Bridge enterprise value to equity using net debt and relevant nonoperating assets/liabilities, then divide by compatible diluted shares. Do not subtract debt twice or mix FCFE with WACC.

Use base/upside/downside scenarios and a sensitivity grid whose centre reproduces the base model. Recompute each cell, not a linear approximation of a nonlinear valuation. Show the fraction of value attributable to terminal value. A moat assessment maps to the competitive-advantage period and the terminal return on new investment, not to a lower discount rate ([methods §9.2](methods-fundamentals-valuation.md)). Dates, share count, currency and dilution often matter more than extra decimal places.

## Comparable companies and transactions

Define EV and denominator consistently: EV/revenue, EV/EBITDA, P/E or book-based measures as appropriate. Match LTM/forward periods and adjusted/GAAP bases. A current market multiple is not a historical transaction multiple. EODHD does not guarantee a complete M&A transaction, private-company or broker-consensus dataset; user-supplied deal assumptions can supplement a model without becoming “API facts.”

Sum-of-the-parts values user-supplied segment metrics at EODHD pure-play peer multiples, subtracts capitalized corporate costs, net debt and minorities, and applies a declared holding-company discount (methods §8.9). Segment data is never an API fact.

## LBO, merger and private-company models

An LBO needs sources-and-uses balance, debt tranches, fees, mandatory amortization, cash sweep, covenants if known, interest and exit assumptions. Compute investor cash flows, MOIC and dated IRR; no exit valuation is guaranteed. Two-way IRR and MOIC grids (entry × exit multiple, leverage × exit multiple, growth × hold period) recompute the full model in every cell, with the centre equal to the base case and fees as an explicit input (methods §13.4). A merger model needs purchase consideration, financing, new shares, synergies, integration costs, taxes and purchase-accounting assumptions; distinguish EPS accretion from value creation.

Private equity unit-economics models require user-provided revenue cohorts, retention/churn, margins, CAC and operating costs. Match cohorts and distinguish gross/net retention. Deal screening, due-diligence lists and investment-committee memos can use EODHD public-company/sector context; private operational facts must come from supplied material. The IC memo section template, the data-pack tab set and the release ties are in methods §13.5.

## Validation

Check period/scale consistency, formula dependencies, scenario propagation, sign conventions, balance checks and terminal sensitivities. Recalculate workbooks with an actual spreadsheet engine when available; openpyxl alone does not evaluate formulas. If no engine is available, state that formula results are unverified and provide independently checked calculation examples rather than claiming a recalculated file.
