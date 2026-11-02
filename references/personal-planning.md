# Personal planning, FIRE, cash flow and taxes

> Methods with formulas, steps and acceptance checks: [methods-planning-wealth](methods-planning-wealth.md).

EODHD supplies market context and investment histories. Household income, expenses, debts, account balances, goals, tax residency, ages and constraints are user inputs. Do not infer them from a portfolio or ask for unnecessary identifying information.

## Planning engine

Model time-stepped cash flows: income, essential/discretionary spending, contributions, debt payments, investment returns, inflation, fees and taxes. Define nominal versus real values and convert consistently: `1+r_real = (1+r_nominal)/(1+inflation)`. Solve funding gaps under explicit assumptions rather than projecting historical returns as promises.

FIRE and savings-goal tools need horizon, spending, existing capital, contribution schedule and a range of return/inflation paths. Compare deterministic scenarios and stochastic simulations. Sequence-of-returns risk matters for withdrawals: two paths with the same average return can produce different survival outcomes. A fixed withdrawal-rate rule is a research assumption, not a guarantee across markets, horizons or fees.

## Useful modules

Section numbers refer to [methods-planning-wealth](methods-planning-wealth.md).

- **Intake and dashboard** (13.2–13.3): a structured intake (fields, units, frequencies, missing-input table); savings rate, front-end and back-end DTI, emergency months, funded ratio, insurance coverage ratio. Thresholds are labelled heuristics. Any composite score shows its weights and components, and the report follows a fixed section order.
- **Net worth** (13.4): EODHD-priced securities plus user-valued assets minus liabilities. Separate liquid from investable assets, keep dated snapshots with a change decomposition, and project with the planning engine. Peer or age benchmarks need a user-supplied source.
- **Budget/cash flow** (13.5): reconcile opening cash + inflows − outflows = closing cash, and label transfers to avoid double counting. Categorize with an ordered rule table and an uncategorized queue. 50/30/20, zero-based and envelope budgets are heuristics the user chooses.
- **Debt** (13.6): amortization, APR versus effective rate, fixed/variable rates, fees and prepayment assumptions. Compare avalanche and snowball on the user's constraints with total interest from the schedule. Refinance and consolidation get a breakeven and a total-cost comparison. Prepay-vs-invest weighs the certain after-tax loan rate against EODHD-derived return ranges.
- **Lending** (13.7): extra-payment schedules, points breakeven including the balance effect, 15 vs 30 years, and ARM rate paths with caps and floors. SOFR and UST series serve as index scenarios, never as the lender's determination.
- **Emergency reserve** (13.8): months of essential spending by income-variability tier (a heuristic, not a universal required number), opportunity cost against the bill yield, and a replenishment timeline.
- **Liquidity tiers** (13.12): operating cash, a bills reserve, a ladder for dated needs and a long-term portfolio. CD rates are user-supplied.
- **Retirement** (sections 3–4): accumulation and decumulation, inflation, longevity paths, variable spending guardrails, glide paths (4.1) and a tax-account withdrawal order supplied by the user.
- **Taxes and location** (13.13, 7.1): after-tax growth by account type, asset-location ranking by tax drag, and dividend holding-period windows as labelled estimates.
- **Equity compensation and concentrated stock** (13.11): vesting, exercise/strike and scenario dilution come from the user, because issuer market data does not supply grant terms. EODHD history supports the risk comparison, decline probabilities and staged-sale simulation.
- **Real estate/rent-versus-buy** (13.9–13.10): purchase and transaction costs, financing, maintenance, vacancy, rent growth, taxes and opportunity cost in a two-scenario engine with break-even and sensitivity grids. Rental NOI, cap rate, DSCR and levered IRR are computed on user inputs. BIS country property indices are context, not a property appraisal.
- **Private funds** (14): TVPI, DPI, RVPI, IRR and Kaplan–Schoar / Long–Nickels PME against an EODHD total-return index, from the user's capital-account statements.
- **Insurance/estate/relocation**: scenario cash-flow consequences with supplied legal/contract terms, not fabricated benefits or jurisdiction rules.

## Tax/accounting boundary

Use actual dated user transactions and jurisdiction-specific rules supplied or verified for the task. Market price history alone cannot reconstruct cost basis, withholding, wash-sale treatment or tax liability. Separate estimates from a filing-ready calculation. Keep acquisition/disposal lots, fees, FX conventions and corporate-action basis transformations auditable.

A tax-loss-harvesting research screen can identify unrealized losses and exposure-preserving candidates; it cannot certify substantially-identical status or legal eligibility. Do not hardcode a country's thresholds from memory or an outdated source. Missing transaction history blocks precise tax results; offer a model with explicit missing inputs rather than inventing trades.

## Output

Show assumptions, base and stress scenarios, sensitivity to inflation/returns/longevity, cash shortfalls and the levers the user controls. Advisory deliverables (proposal packs, goal-progress panels, review packs, sleeve and held-away reporting) are in methods-planning-wealth 6.2 and 11.5–11.7. Keep private financial inputs local/appropriately secured. Avoid unnecessary product pitches, guaranteed savings or automated transactions.
