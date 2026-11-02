# Methods: fundamentals, ratios, valuation and equity-research workflows

Formula-level methods for company analysis on EODHD data. The chapter covers the Fundamentals field map,
period and TTM handling, a ratio library, cost of capital, DCF, dividend-discount, residual-income and
reverse-DCF models, comps and tear sheets, competitive positioning, industry outlines, sum-of-the-parts,
composite scores, a moat evidence rubric, short-side and special-situation screens, earnings workflows,
SEC filings in research, thesis tracking and headline scenarios, quality gates and initiation staging for
research reports, listed-acquirer screens and deal maths with returns grids and IC packs, and a model
audit checklist.
Each method has a one-line **Use when**, its **EODHD inputs**, the **Method**, **Pitfalls** and
**Acceptance checks**. Principles already in [fundamentals.md](fundamentals.md) and
[valuation.md](valuation.md) are not repeated. Price-basis rules are in [data-semantics.md](data-semantics.md),
and coverage facts are in [coverage-notes.md](coverage-notes.md). These are analytical methods. A
computed value is not a recommendation.

## Contents

0. Conventions
1. Fundamentals field map
2. Periods, TTM, semi-annual reporters and restatements
3. Ratio library (3.14 owner earnings and investor-lens checklists)
4. Cost-of-capital inputs
5. DCF (FCFF), sensitivity grid and reverse DCF
6. Dividend discount and residual income models
7. EV bridge and reconciliation
8. Comps, tear sheets and sector valuation history (8.6 snapshot rows, macro and news blocks;
   8.7 competitive positioning; 8.8 industry research outline; 8.9 sum-of-the-parts)
9. Composite scoring, moat evidence and idea screens (9.1 composite; 9.2 moat rubric; 9.3 short-side
   screen; 9.4 special situations from the IPO calendar)
10. Earnings workflows: preview, post-earnings update and chart list, model-update log, morning note,
    SEC filings (10-K, 10-Q, 8-K) in research, SEC Company Analytics (filing-native fundamentals)
11. Thesis tracker and headline-to-scenario workflow
12. Equity research reports: quality gates, initiation staging and rating rule
13. M&A: listed strategic-buyer screen, merger maths, deal milestones, LBO returns attribution and
    sensitivity grids, IC memo template and data pack
14. Spreadsheet and model audit checklist
15. Boundaries: what EODHD does not supply

---

## 0. Conventions

| Item | Rule |
|---|---|
| Rates and ratios | Decimal internally (0.084 = 8.4%). Convert API percent fields once, at ingestion: UST `rate`, HQM `yield_value`, `surprisePercent`, `SharesStats.PercentInsiders/PercentInstitutions` are percent, while `Highlights` margins, `DividendYield` and `ShortPercentFloat` are decimal. |
| Basis points | 1 bp = 0.0001. A 25 bp move in yield is 0.0025 in decimal terms. |
| Statement values | JSON **strings** (`"112010000000.00"`). Parse with `float()`. `None` means unavailable. The FAQ says `0` and `null` both mean "not available", so a 0 in a denominator or in a cost-of-debt input is unavailable, not a true zero, unless independently confirmed. |
| Signs | Normalize to an economic sign convention at ingestion (see §1.4). Store the raw value next to the normalized one. |
| Flows vs stocks | Income and cash-flow lines are period flows. Balance-sheet lines are point-in-time stocks. A ratio of a flow to a stock uses the **average** of opening and closing balances unless stated. |
| Not meaningful | A ratio with a zero, negative or missing denominator returns the state `NM` with a reason. It is never 0 and never a large number. |
| Currency | Statement currency = `Financials::*::currency_symbol`. Listing currency = `General.CurrencyCode` (can be `GBX`/`ZAC`). Convert price into statement currency (or the reverse) with a dated `*.FOREX` close, after normalizing minor units ([data-semantics.md](data-semantics.md#units-and-currencies)). |
| Evidence record | Every reported number carries `{endpoint, symbol, field path, period, retrieved_at_utc, units, currency, transform}`. §12 uses it. |

---

## 1. Fundamentals field map

**Use when:** mapping an analysis input to the exact EODHD field before any calculation.

**EODHD inputs:** `GET /api/fundamentals/{SYMBOL}` with `filter=` (comma-separated sections or
`Section::Sub` paths). Plans: Fundamentals Data Feed or All-In-One. Neither the Feed alone nor the Calendar
product includes EOD prices, so prices plus fundamentals need All-In-One or two plans
([plans-limits.md](plans-limits.md)). **Cost: 10 calls per request regardless of `filter`**, so fetch all
needed sections in one request and cache them. `from`/`to` limit statement periods. Full guide:
[api/general/fundamentals-common-stock.md](api/general/fundamentals-common-stock.md). FAQ:
[api/general/fundamentals-faq.md](api/general/fundamentals-faq.md).

### 1.1 Snapshot versus history

Per the FAQ, only `outstandingShares`, `Earnings` and `Financials` hold history. Every other section is a
**current snapshot** with no as-of parameter. No section is point-in-time: periods are restated in place
([temporal-research.md](temporal-research.md), recipe 39 in [build-recipes.md](build-recipes.md)).

| Section | Key fields (exact names) | Units / basis | History? |
|---|---|---|---|
| `General` | `Code`, `Type`, `Name`, `Exchange`, `CurrencyCode`, `CountryISO`, `ISIN`, `CIK`, `PrimaryTicker`, `FiscalYearEnd` (month name), `IPODate`, `Sector`, `Industry`, `GicSector`, `GicGroup`, `GicIndustry`, `GicSubIndustry`, `HomeCategory` (Domestic/ADR), `IsDelisted`, `FullTimeEmployees`, `Description`, `Listings`, `Officers`, `UpdatedAt` | `countryName` is the exchange country, not headquarters. Use `Address`/`AddressData` for location. GICS is mainly filled for US and major markets. | Current only. Classification is today's, so historical sector panels carry look-ahead in membership. |
| `Highlights` | `MarketCapitalization`, `EBITDA`, `PERatio`, `PEGRatio`, `WallStreetTargetPrice`, `BookValue` (per share), `DividendShare`, `DividendYield`, `EarningsShare`, `DilutedEpsTTM`, `EPSEstimateCurrentYear`, `EPSEstimateNextYear`, `EPSEstimateCurrentQuarter`, `EPSEstimateNextQuarter`, `MostRecentQuarter`, `ProfitMargin`, `OperatingMarginTTM`, `ReturnOnAssetsTTM`, `ReturnOnEquityTTM`, `RevenueTTM`, `RevenuePerShareTTM`, `GrossProfitTTM`, `QuarterlyRevenueGrowthYOY`, `QuarterlyEarningsGrowthYOY` | Ratios decimal. Vendor-computed. Formula and averaging are not documented, so reconcile before use (§3). | Current |
| `Valuation` | `TrailingPE`, `ForwardPE`, `PriceSalesTTM`, `PriceBookMRQ`, `EnterpriseValue`, `EnterpriseValueRevenue`, `EnterpriseValueEbitda` | EV documented as "market cap + debt − cash" without a field-level definition (§7). | Current |
| `SharesStats` | `SharesOutstanding`, `SharesFloat`, `PercentInsiders`, `PercentInstitutions`, `SharesShort`, `SharesShortPriorMonth`, `ShortRatio`, `ShortPercentOutstanding`, `ShortPercentFloat` | Percent fields are percent (1.648 = 1.648%). `ShortPercentFloat` is decimal. Short data is US only. Float can exceed outstanding (timing, multi-class). | Current. No historical float. |
| `Technicals` | `Beta`, `52WeekHigh`, `52WeekLow`, `50DayMA`, `200DayMA`, `SharesShort`, `ShortRatio`, `ShortPercent` | `Beta` = 5-year **monthly** levered beta against the country's main index, updated about weekly (FAQ). | Current |
| `SplitsDividends` | `ForwardAnnualDividendRate`, `ForwardAnnualDividendYield`, `PayoutRatio`, `DividendDate`, `ExDividendDate`, `LastSplitFactor`, `LastSplitDate`, `NumberDividendsByYear` | Payout decimal and vendor-computed. For amounts, use the `div` endpoint (`value` is split-adjusted, `unadjustedValue` is the amount actually paid). | Counts by year only |
| `AnalystRatings` | `Rating` (1–5, 5 = strong buy), `TargetPrice`, `StrongBuy`, `Buy`, `Hold`, `Sell`, `StrongSell` | Collected from public reports via NLP. Populated for top US (and some EU) names. | Current |
| `Holders` | `Institutions`/`Funds` → `name`, `date`, `totalShares` (% of shares), `totalAssets` (% of holder assets), `currentShares`, `change`, `change_p` | Typically the top ~20 holders. Each row has its own report `date`. | Current snapshot. Quarter-over-quarter history only from your own captures. |
| `InsiderTransactions` | `date`, `ownerName`, `transactionDate`, `transactionCode` (P/S/M/A/G/F), `transactionAmount`, `transactionPrice`, `transactionAcquiredDisposed`, `postTransactionAmount` | Recent rows only. For depth use `/api/sec-filings/{symbol}/form4` (All-In-One, 10 calls). | Recent |
| `outstandingShares` | `annual` / `quarterly` → rows with `date`, `dateFormatted`, `shares`, `sharesMln` (live shape, see §1.3) | FAQ: **diluted**, split-adjusted. | Yes |
| `Earnings::History` | per quarter: `date` (period end), `epsActual`, `epsEstimate`, `epsDifference`, `surprisePercent` (+ observed `reportDate`, `beforeAfterMarket`, `currency`) | EPS is generally adjusted (non-GAAP). GAAP diluted for the largest US filers (FAQ). | Yes |
| `Earnings::Trend` | per horizon: `period` (`0q`,`+1q`,`0y`,`+1y`), `earningsEstimateAvg/Low/High`, `earningsEstimateNumberOfAnalysts`, `earningsEstimateYearAgoEps`, `earningsEstimateGrowth`, `revenueEstimateAvg/Low/High`, `revenueEstimateNumberOfAnalysts`, `revenueEstimateGrowth`, `epsTrendCurrent`, `epsTrend7daysAgo` … `epsTrend90daysAgo`, `epsRevisionsUpLast7days/30days`, `epsRevisionsDownLast7days/30days` | Strings. Updated in place. Not split-adjusted. One-year-ahead horizon only (no FY+2). The v1.1 path splits `Quarterly`/`Annual` and adds `fiscalQuarter`. | Old rows persist with their last value, not as-of history |
| `Earnings::Annual` | `date`, `epsActual` | See the partial-year trap in §2.4. | Yes |
| `Financials` | `Balance_Sheet`, `Cash_Flow`, `Income_Statement` × `quarterly`/`yearly`, keyed by period-end date. Each row has `date`, `filing_date`, `currency_symbol`. | Statement currency. `filing_date` is reliable mainly for US. | Yes. Major US from 1985, others from about 2000, small caps about 6 years / 20 quarters. |

### 1.2 Request plan per company

| Need | Request | Calls |
|---|---|---|
| Everything for a tear sheet or model | `fundamentals/{S}?filter=General,Highlights,Valuation,SharesStats,Technicals,SplitsDividends,AnalystRatings,Holders,outstandingShares,Earnings,Financials` | 10 |
| Price history (adjusted and raw) | `eod/{S}?from=…` (`period=w` or `m` for beta) | 1 |
| Dividend cash amounts | `div/{S}?fmt=json` | 1 |
| Consensus for many names | `calendar/trends?symbols=A,B,C` | 1 per request (Calendar) |
| Report dates in a window | `calendar/earnings?from=&to=` | 1 |
| Risk-free | `ust/yield-rates?filter[year]=YYYY` (US) or `US10Y.GBOND`-style EOD (Fundamentals/All-In-One) | verify cost with `/api/user` before and after |
| US weekly market cap history | `historical-market-cap/{S}` (NYSE/NASDAQ, from 2021-07-09, USD) | 10 |

S&P 500 coverage at 10 calls per name is about 5,000 calls. Refresh after earnings, not daily. Whole-exchange
bulk fundamentals need the Extended Fundamentals arrangement ([plans-limits.md](plans-limits.md)).

### 1.3 Statement fields (probe-verified)

A probe on 2026-10-25 (`AAPL.US`, demo key, `yearly`, FY2024–FY2025) returned the fields below. Field
availability varies by issuer, exchange and year, and the FAQ notes that names can differ between years.
Test presence with `.get()`. Never assume a field exists because it existed for another ticker.

| Statement | Fields used in this chapter |
|---|---|
| Income_Statement | `totalRevenue`, `costOfRevenue`, `grossProfit`, `researchDevelopment`, `sellingGeneralAdministrative`, `sellingAndMarketingExpenses`, `totalOperatingExpenses`, `otherOperatingExpenses`, `operatingIncome`, `ebit`, `ebitda`, `depreciationAndAmortization`, `reconciledDepreciation`, `interestExpense`, `interestIncome`, `netInterestIncome`, `totalOtherIncomeExpenseNet`, `incomeBeforeTax`, `taxProvision`, `incomeTaxExpense`, `minorityInterest`, `netIncomeFromContinuingOps`, `discontinuedOperations`, `extraordinaryItems`, `nonRecurring`, `netIncome`, `netIncomeApplicableToCommonShares`, `preferredStockAndOtherAdjustments` |
| Balance_Sheet | `cash`, `cashAndEquivalents`, `shortTermInvestments`, `cashAndShortTermInvestments`, `netReceivables`, `inventory`, `otherCurrentAssets`, `totalCurrentAssets`, `propertyPlantEquipment`, `propertyPlantAndEquipmentNet`, `propertyPlantAndEquipmentGross`, `goodWill` (capital W), `intangibleAssets`, `longTermInvestments`, `nonCurrentAssetsTotal`, `totalAssets`, `accountsPayable`, `currentDeferredRevenue`, `shortTermDebt`, `shortLongTermDebt`, `otherCurrentLiab`, `totalCurrentLiabilities`, `longTermDebt`, `longTermDebtTotal`, `capitalLeaseObligations`, `shortLongTermDebtTotal`, `nonCurrentLiabilitiesTotal`, `totalLiab`, `totalStockholderEquity`, `retainedEarnings`, `commonStock`, `treasuryStock`, `accumulatedOtherComprehensiveIncome`, `noncontrollingInterestInConsolidatedEntity`, `preferredStockTotalEquity`, `liabilitiesAndStockholdersEquity`, `commonStockSharesOutstanding` (units), `netDebt`, `netWorkingCapital`, `netInvestedCapital`, `netTangibleAssets` |
| Cash_Flow | `netIncome`, `depreciation`, `stockBasedCompensation`, `changeInWorkingCapital`, `changeToAccountReceivables`, `changeToInventory`, `otherNonCashItems`, `totalCashFromOperatingActivities`, `capitalExpenditures`, `investments`, `totalCashflowsFromInvestingActivities`, `dividendsPaid`, `salePurchaseOfStock`, `issuanceOfCapitalStock`, `netBorrowings`, `totalCashFromFinancingActivities`, `changeInCash`, `beginPeriodCashFlow`, `endPeriodCashFlow`, `freeCashFlow` |

Observed in that one probe. Treat these as hypotheses to re-test per ticker, not as documented definitions:

- `netDebt` = `shortLongTermDebtTotal` − `cash`, exactly, in both years.
- `shortLongTermDebtTotal` (112,377m) exceeded `shortTermDebt` + `longTermDebt` (100,774m). It probably
  includes other debt-like items such as leases. Choose one debt definition and keep it everywhere.
- `netInvestedCapital` = `totalStockholderEquity` + `longTermDebt` + `shortLongTermDebt`, exactly. It is
  **not net of cash**, despite the name.
- `ebit` equalled `incomeBeforeTax` in FY2025 and differed from `operatingIncome` (132,729m vs 133,050m).
  In FY2024 the two were equal.
- `interestExpense` was `null` in FY2025 and `0.00` in FY2024 for an issuer with more than 100bn of debt.
- `freeCashFlow` = `totalCashFromOperatingActivities` − `capitalExpenditures`, with capex stored positive.
- `outstandingShares` came back as `{annual:{…}, quarterly:{…}}` with `date` (`"2026"` / `"2026-Q2"`),
  `dateFormatted`, `sharesMln` (string) and `shares` (units). The reference example shows a flat list in
  millions. Annual rows were labelled by calendar year (`2026-12-31`) for a September fiscal year.
- `Valuation.EnterpriseValue` (4,940bn) was **below** `Highlights.MarketCapitalization` (5,075bn) while
  `netDebt` was +76bn, so the vendor EV is not market cap + `netDebt`.

### 1.4 Sign normalization

| Field (raw) | Raw sign in probe | Normalized meaning |
|---|---|---|
| `capitalExpenditures` | positive | `capex_out = abs(raw)`. Confirm per issuer with `freeCashFlow ≈ CFO − capex_out`, and flag if neither sign ties. |
| `dividendsPaid` | positive | `div_out = abs(raw)` |
| `salePurchaseOfStock` | negative = net repurchase | `net_buyback = −raw` (positive = net shares bought back). Net of issuance, as presented. |
| `netBorrowings` | negative = net repayment | `net_borrowing = raw` (positive = new debt) |
| `changeInWorkingCapital` | cash-flow sign | negative = cash absorbed by working capital |
| `totalCashflowsFromInvestingActivities` | cash-flow sign | can be positive when investments mature, so do not use it as a capex proxy |

**Statement identities** (from the FAQ trajectory plus accounting identities). Check each one per
period with a tolerance of max(0.5% of the larger term, one reporting unit):

- `totalRevenue − costOfRevenue = grossProfit`
- `grossProfit − totalOperatingExpenses = operatingIncome`
- `incomeBeforeTax − taxProvision = netIncome`. This can differ by minority interest, discontinued
  operations or extraordinary items. Explain any difference before flagging it.
- `netIncome − minorityInterest = netIncomeApplicableToCommonShares`
- `totalAssets = liabilitiesAndStockholdersEquity`, and `totalAssets ≈ totalLiab + totalStockholderEquity + noncontrolling + temporary equity`
- `beginPeriodCashFlow + changeInCash = endPeriodCashFlow`. Also `CFO + CFI + CFF (+ FX effect) ≈ changeInCash`.

**Pitfalls.** A single failed identity usually means a missing sub-line, not a wrong total. The FAQ says
totals and major fields are correct while the template cannot hold every line, so keep the totals and
mark components as incomplete. Banks and insurers use a different statement logic: revenue, COGS and
working capital are not meaningful. Use the bank statement endpoints in the API library, or mark the
ratios NM.

**Acceptance checks.** (a) A parser fed the probe numbers above reproduces `freeCashFlow` 98,767m from
111,482m − 12,715m. (b) The string `"0.00"` in `interestExpense` yields the state `unavailable`, not 0, in
the cost-of-debt function. (c) A missing `goodWill` (the capital-W spelling) is reported as absent, not
silently read from `goodwill`.

---

## 2. Periods, TTM, semi-annual reporters and restatements

### 2.1 Period typing

**Use when:** any calculation combines more than one period.

**Method.** Label every statement row with `{period_end, fiscal_year, fiscal_period, duration_months,
basis: standalone|cumulative|derived, currency, retrieved_at}`.

1. The fiscal year comes from `General.FiscalYearEnd` (a month name). A fiscal year ending in January
   2026 is usually called FY2025 by the issuer. Store the issuer label and the period-end date. Never infer
   the fiscal quarter from the report date.
2. Quarterly rows are spaced 80–100 days apart. Larger gaps mean missing or semi-annual periods.
3. **Semi-annual detection.** The API has no flag. The FAQ lists these signs:
   - four quarters of one year are identical, so an annual figure was split evenly;
   - pairs of quarters are identical, so a half-year was split;
   - only even quarters have values and odd quarters are null or missing;
   - odd quarters are of a clearly different magnitude.
   Treat any of these as `duration_months = 6` (or 12) data. Do not use it as four standalone quarters.
4. **Cumulative (YTD) detection.** Within one fiscal year, a flow line that rises monotonically and whose
   last interim ≈ the annual value (±1%) is cumulative. Standalone value =
   `YTD_k − YTD_{k−1}` within the same fiscal year. Q1 is its own YTD.
5. **Derived Q4** = `FY − (Q1 + Q2 + Q3)` and **derived H2** = `FY − H1`. Allowed only when currency,
   consolidation scope and accounting basis match and the parts are standalone. Mark the result
   `basis=derived`.

### 2.2 TTM (LTM) construction

**Use when:** comparing companies with different fiscal year ends, or valuing on the latest twelve months.

**Method.** Flow TTM = sum of the **four consecutive standalone quarters** ending at the latest quarter
(or two consecutive standalone halves for semi-annual reporters). If only the annual and a later interim
YTD exist:
`TTM = FY_prev + YTD_current − YTD_prev_same_period`.
For balance-sheet items there is no TTM: use the latest balance for "as at" ratios and the average of the
balance at the start and end of the TTM window (or the five quarter-ends) for return ratios.

```python
import math
from datetime import date

def num(x):
    """EODHD statement values are strings; None/'' -> None. Callers decide whether 0 means unavailable."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None

def ttm(quarterly: dict, field: str, end: str, gap_days=(80, 100)):
    """Sum `field` over the 4 consecutive quarterly rows ending exactly at `end`.
    `quarterly` is Financials::<Statement>::quarterly. Returns (value, dates) or (None, reason)."""
    dates = sorted(d for d in quarterly if d <= end)[-4:]
    if len(dates) < 4 or dates[-1] != end:
        return None, "fewer than 4 quarters ending at end"
    ds = [date.fromisoformat(d) for d in dates]
    for a, b in zip(ds, ds[1:]):
        if not gap_days[0] <= (b - a).days <= gap_days[1]:
            return None, f"gap {a}->{b} is not one quarter"
    if len({quarterly[d].get("currency_symbol") for d in dates}) != 1:
        return None, "mixed statement currencies"
    vals = [num(quarterly[d].get(field)) for d in dates]
    if any(v is None for v in vals):
        return None, "missing value in window"
    if vals[0] != 0 and len({round(v, 6) for v in vals}) == 1:
        return None, "4 identical quarters: likely an annual figure split evenly"
    return sum(vals), dates
```

**Pitfalls.**
- Taking "the latest four dictionary keys" silently spans a missing quarter. The gap check above prevents it.
- `Highlights.RevenueTTM` and similar vendor fields may use a different window or may be updated at a
  different time than `Financials`. Reconcile them and store both.
- Mixing a quarterly TTM numerator with a price observed months later is fine for "current multiple". For
  a historical series, align the price date to when the period was **known** (§8.5).
- EPS TTM: sum quarterly EPS only if the share count was stable. Otherwise use TTM net income ÷ the latest
  diluted shares, and state which method you used.

**Acceptance checks.**
- Quarters 100, 110, 120, 130 ending 2025-06-30 … 2026-03-31 give TTM = 460.
- Delete 2025-09-30 from that series and it returns `None`: "fewer than 4 quarters" if no earlier row
  exists, or the "gap" reason when an earlier quarter (e.g. 2025-03-31) is present.
- Four identical quarters of 250 return the "split evenly" reason.

### 2.3 Restatements and vintages

EODHD keeps **one version** of each period. A restatement replaces the stored value, typically when the next
full report includes the restated figure (FAQ). Consequences:

- Back-tests and "what did we know then" analyses need your own dated captures (recipe 39). The current
  history is a revised history, and a restated value can keep the original `filing_date`. For US issuers
  the SEC Filings API (§10.5) is the exception: one row per filing, dated by `filed_at`.
- A model-update log (§10.3) must record the captured value, not re-read the history later.
- When two captures disagree for the same `period_end`, keep both and flag the newer one as `restated`. A
  statement row that disappears is a data event to log, not a reason to delete local history.
- `filing_date` is reliable mainly for US issuers. Elsewhere it can equal the period end. For
  availability lags use `filing_date` when it is later than the period end. Otherwise use a declared
  conservative lag, for example 90 days after a quarter and 120 after a year (an assumption, labelled).

### 2.4 Earnings::Annual partial-year trap

The probe showed `Earnings::Annual` for the not-yet-reported fiscal year equal to the **sum of the quarters
reported so far**: FY ending 2026-09-30 had `epsActual` 6.87 = 2.84 + 2.01 + 2.02, before the Q4 report.
Use an annual EPS only when four standalone quarters (or the 10-K/annual row in `Financials`) exist for
that fiscal year. Otherwise label it `YTD`.

---

## 3. Ratio library

**EODHD inputs for all ratios:** `Financials` (quarterly and yearly), `Highlights`/`Valuation` for
vendor cross-checks, EOD `close` for market values (convert GBX/ZAC and FX first), `outstandingShares`
for share history. One Fundamentals request (10 calls) plus one EOD request (1 call) per company.

Notation: `avg(X) = (X_open + X_close)/2` over the measurement period; `t` = tax rate (§4.5); `TTM` per §2.2.

### 3.1 Margins and profitability

| Ratio | Formula | Fields |
|---|---|---|
| Gross margin | grossProfit / totalRevenue | IS |
| Operating margin | operatingIncome / totalRevenue | IS |
| EBIT margin | EBIT / totalRevenue (declare EBIT = `operatingIncome` or `ebit`) | IS |
| EBITDA margin | (EBIT + D&A) / totalRevenue, with D&A = `depreciationAndAmortization` (or CF `depreciation`) | IS, CF |
| Net margin | netIncomeApplicableToCommonShares / totalRevenue | IS |
| R&D intensity | researchDevelopment / totalRevenue | IS |
| SBC intensity | stockBasedCompensation / totalRevenue | CF, IS |

Use matching periods (both TTM, or both FY). Revenue ≤ 0 → NM.

### 3.2 Returns: ROE, ROA, ROIC

| Ratio | Formula | Notes |
|---|---|---|
| ROE | NI_common_TTM / avg(totalStockholderEquity) | Equity ≤ 0 → NM. Buybacks can make equity tiny or negative, which inflates ROE (e.g. vendor `ReturnOnEquityTTM` 1.49). |
| ROA | NI_TTM / avg(totalAssets) | One variant adds back after-tax interest: (NI + interest×(1−t)) / avg TA. State which. |
| NOPAT | EBIT_TTM × (1 − t) | `t` per §4.5 |
| Invested capital (financing view) | totalStockholderEquity + debt + noncontrollingInterestInConsolidatedEntity + preferredStockTotalEquity − cash_def | Declare debt = `shortLongTermDebtTotal` or `shortTermDebt + longTermDebt`. Declare cash_def = `cashAndEquivalents`, or `cashAndShortTermInvestments` (excess cash). Do not use the vendor `netInvestedCapital` as-is (§1.3). |
| Invested capital (operating view) | (totalCurrentAssets − cash_def) − (totalCurrentLiabilities − shortTermDebt − shortLongTermDebt) + propertyPlantAndEquipmentNet + goodWill + intangibleAssets | Should approximate the financing view, and the gap shows non-operating items |
| ROIC | NOPAT_TTM / avg(IC) | Report both IC views when they differ by more than 10% |
| ROIC − WACC spread | ROIC − WACC (§4) | Economic-profit sign. Economic profit = (ROIC − WACC) × avg IC. |
| Incremental ROIC | ΔNOPAT / ΔIC over 3–5 years | Noisy, so require ΔIC > 0 |

**Pitfalls.** Goodwill-heavy acquirers have a low ROIC including goodwill and a high ROIC excluding it, so
show both. Leases: if debt includes lease liabilities, EBIT should exclude lease interest. Keep it
consistent across peers. Financials (banks, insurers) → ROIC is NM. Use ROE and ROA.

### 3.3 DuPont

- **3-step:** ROE = (NI / Sales) × (Sales / avg TA) × (avg TA / avg Equity)
- **5-step:** ROE = (NI / EBT) × (EBT / EBIT) × (EBIT / Sales) × (Sales / avg TA) × (avg TA / avg Equity)
  - The five factors are tax burden, interest burden, EBIT margin, asset turnover and equity multiplier.

The product equals NI / avg Equity exactly **only if every factor uses the same NI, the same period and the
same averages**. Use NI attributable to common throughout, or total NI throughout.

**Acceptance check.** NI 80, Sales 1,000, TA 800, Equity 400, EBT 100, EBIT 120. ROE 0.20 equals the
3-step product 0.08 × 1.25 × 2.0 and the 5-step product 0.8 × 0.8333 × 0.12 × 1.25 × 2.0.

### 3.4 Cash-flow measures and earnings quality

| Measure | Formula (normalized signs, §1.4) |
|---|---|
| FCF (simple) | CFO − capex_out. Cross-check `freeCashFlow`. |
| SBC-adjusted FCF | CFO − capex_out − stockBasedCompensation. Treats SBC as a cash-equivalent cost. Always show it next to plain FCF. |
| FCF conversion | FCF / NI_common (NI ≤ 0 → NM) |
| FCFF (from CFO) | CFO + interestExpense × (1 − t) − capex_out. If interest is unavailable, FCFF is NM by this route. |
| FCFF (from EBIT) | EBIT × (1 − t) + D&A − capex_out − ΔNWC_operating, with ΔNWC_operating > 0 = investment |
| FCFE | CFO − capex_out + net_borrowing, or equivalently FCFF − interest × (1 − t) + net_borrowing |
| Accruals ratio (cash-flow) | (NI − CFO) / avg(totalAssets). High positive = earnings ahead of cash. |
| Accruals ratio (incl. investing) | (NI − CFO − CFI) / avg(totalAssets). CFI in cash-flow sign. |
| Accruals ratio (balance-sheet, Sloan-style) | [(ΔCA − Δcash) − (ΔCL − ΔSTD) − D&A] / avg TA. The original also removes Δtaxes payable, which is not a field here, so label the variant. |
| Receivables vs sales | growth(netReceivables) − growth(totalRevenue). Persistently positive is a quality flag. |
| Inventory vs sales | growth(inventory) − growth(costOfRevenue) |

**Pitfall.** CFO can contain interest paid (US GAAP) or not (IFRS options). The FCFF from CFO route above
assumes interest was deducted inside CFO. For IFRS issuers that classify interest paid in financing, drop
the add-back.

### 3.5 Working capital days and cash conversion cycle

With `D` = days in the measurement period (365 for annual or TTM, actual days for a quarter):

- DSO = avg(netReceivables) / totalRevenue × D
- DIO = avg(inventory) / costOfRevenue × D
- DPO = avg(accountsPayable) / costOfRevenue × D
- **CCC = DSO + DIO − DPO**

Some analysts compute DPO on purchases (COGS + Δinventory). State the denominator. Revenue or COGS ≤ 0 →
NM. Service companies with no inventory → DIO = 0 only if `inventory` is explicitly reported as 0 for
several periods. Otherwise it is unavailable.

**Acceptance check.** Revenue 1,000, COGS 600, avg AR 120, avg inventory 90, avg AP 60, D = 365 →
DSO 43.8, DIO 54.75, DPO 36.5, CCC 62.05 days.

### 3.6 Leverage, liquidity, coverage and credit ratios

| Ratio | Formula |
|---|---|
| Debt / EBITDA | Debt / EBITDA_TTM |
| Net debt / EBITDA | (Debt − cash_def) / EBITDA_TTM. Negative = net cash. Report the value, do not rank it as "low leverage". EBITDA ≤ 0 → NM. |
| Debt / Equity (book) | Debt / totalStockholderEquity. Equity ≤ 0 → NM. |
| Debt / Capital | Debt / (Debt + totalStockholderEquity) |
| Debt / market EV | Debt / EV (§7) |
| Interest coverage | EBIT_TTM / interestExpense_TTM. Interest unavailable or 0 → NM, never infinity. |
| EBITDA coverage | EBITDA_TTM / interestExpense_TTM |
| FFO / Debt (credit-style) | (CFO − ΔNWC) / Debt, approximated as (CFO − changeInWorkingCapital) / Debt, sign-normalized |
| FCF / Debt, CFO / Debt | FCF / Debt, CFO / Debt |
| Current ratio | totalCurrentAssets / totalCurrentLiabilities |
| Quick ratio | (cashAndEquivalents + shortTermInvestments + netReceivables) / totalCurrentLiabilities |
| Cash ratio | cashAndShortTermInvestments / totalCurrentLiabilities |

**Pitfall.** Ratings-agency adjustments (pensions, leases, hybrids) are not in the data. A ratio here is
an unadjusted analytical proxy, not a rating.

### 3.7 Altman Z-score

**Use when:** screening industrial and commercial companies for balance-sheet distress.

| Variant | Formula | Zones |
|---|---|---|
| Original (public manufacturers) | Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5 | > 2.99 safe, 1.81–2.99 grey, < 1.81 distress |
| Z″ (non-manufacturers, non-US) | Z″ = 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4b | > 2.60 safe, 1.10–2.60 grey, < 1.10 distress |

- X1 = (totalCurrentAssets − totalCurrentLiabilities) / totalAssets
- X2 = retainedEarnings / totalAssets
- X3 = EBIT_TTM / totalAssets
- X4 = market value of equity (price × shares, statement currency) / totalLiab
- X4b = book equity / totalLiab
- X5 = totalRevenue_TTM / totalAssets

**Sector limits.** The models are not designed for banks, insurers, other financials or REITs, where
leverage and liquidity work differently. Return NM for those (`General.Sector`/`GicSector`). Results for
utilities and asset-light software companies are often outside the calibration range. Large buybacks drive
`retainedEarnings` negative (the probe issuer shows −14bn), which depresses X2 without indicating
distress. Show the components, not just Z.

**Acceptance check.** X = (0.10, 0.20, 0.08, 1.50, 1.10) → Z = 2.664 (grey zone).

### 3.8 Piotroski F-score

**Use when:** scoring improvement in financial strength year over year, usually within a value universe.

Use fiscal-year data for year `y` against `y−1`. Each signal is 1 if true and 0 if false. **Missing inputs
→ the signal is unscored, not 0.**

| # | Signal | Test |
|---|---|---|
| 1 | ROA > 0 | NI_y / TA_{y−1} > 0 |
| 2 | CFO > 0 | CFO_y > 0 |
| 3 | ΔROA > 0 | ROA_y > ROA_{y−1} |
| 4 | Accrual | CFO_y / TA_{y−1} > ROA_y |
| 5 | ΔLeverage < 0 | (longTermDebt / avg TA)_y < same at y−1 |
| 6 | ΔLiquidity > 0 | current ratio_y > current ratio_{y−1} |
| 7 | No equity issuance | diluted shares (`outstandingShares` annual) at y ≤ y−1. If shares rose, check `issuanceOfCapitalStock` and treat an increase from compensation only as an issuance unless the user states otherwise. |
| 8 | ΔGross margin > 0 | GM_y > GM_{y−1} |
| 9 | ΔAsset turnover > 0 | (Sales_y / TA_{y−1}) > (Sales_{y−1} / TA_{y−2}) |

Report `F = points / scored` (e.g. `7/8`) and keep the unscored list. Requires three balance sheets
(y, y−1, y−2), which is not possible for issuers with short history.

### 3.9 Graham number and defensive criteria

- **Graham number** = √(22.5 × EPS × BVPS), where 22.5 = 15 (P/E cap) × 1.5 (P/B cap). Only when EPS > 0
  and BVPS > 0, otherwise NM. EPS = TTM diluted EPS. BVPS = totalStockholderEquity / diluted shares (or
  `Highlights.BookValue`, reconciled). Example: EPS 2.0, BVPS 20 → 30.0.
- **Defensive criteria** (each pass/fail/unscored):

| Criterion | Test |
|---|---|
| Adequate size | Revenue ≥ user-supplied threshold in today's currency. Do not use the original nominal amount. |
| Strong financial condition | Current ratio ≥ 2, and longTermDebt ≤ net current assets |
| Earnings stability | NI > 0 in each of the last 10 fiscal years |
| Dividend record | Uninterrupted payments for 20 years (`div` history). Unscored if the history is shorter than 20 years. |
| Earnings growth | 3-year average EPS at the end ≥ 1.33 × 3-year average EPS 10 years earlier |
| Moderate P/E | price / 3-year average EPS ≤ 15 |
| Moderate P/B | P/B ≤ 1.5, or P/E × P/B ≤ 22.5 |

- **Net-net (NCAV):** NCAV/share = (totalCurrentAssets − totalLiab) / shares. The classic test is
  price < 2/3 × NCAV/share.

**Pitfall.** History of 10–20 years exists mainly for US large caps. Non-US data typically starts in 2000,
and small caps have about 6 years. Criteria that need more history are unscored, not failed.

### 3.10 REIT FFO and AFFO (approximation only)

**Use when:** a user wants REIT payout or P/FFO and no company-reported FFO is supplied.

- Standard FFO = NI_common + real-estate depreciation and amortization − gains on sale of depreciable
  property + impairments of depreciable real estate + adjustments for unconsolidated partnerships and JVs.
- **EODHD approximation:** FFO_approx = netIncomeApplicableToCommonShares + `depreciation` (CF).
  - Gains on sale and impairments are not separately reliable fields.
  - `depreciation` includes non-real-estate D&A.
  - Label the result "FFO (approximate, from statement totals)".
- **AFFO** = FFO − recurring (maintenance) capex − straight-line rent adjustments − leasing costs. None of
  these components is separable in EODHD data (`capitalExpenditures` mixes development and acquisitions),
  so **AFFO is user-supplied** or not computed.
- Use the approximation for P/FFO = market cap / FFO_approx_TTM and payout = dividends / FFO_approx_TTM.

**Acceptance check.** The output label contains "approximate", and AFFO is absent unless the user supplies
the inputs.

Property-level cash-flow maths for a single user-owned property (NOI, cap rate, cash-on-cash, DSCR) runs
on user inputs and belongs to the planning modules in [methods-planning-wealth.md](methods-planning-wealth.md),
not to listed-REIT analysis.

### 3.11 Dividend payout and cover

| Measure | Formula |
|---|---|
| Earnings payout | div_out_TTM / NI_common_TTM, or DPS_TTM / EPS_TTM on the same share basis |
| Cash payout | div_out_TTM / FCF_TTM. FCF ≤ 0 → NM, flagged as "dividend not covered by FCF". |
| Cover | 1 / payout |
| Total shareholder payout | (div_out + net_buyback) / NI_common |
| TTM DPS | Sum of the `div` endpoint's `value` (split-adjusted, today's share terms) for ex-dates in the last 365 days. Exclude rows with `period` = Special or detected outliers, and report specials separately. |
| Indicated (forward) yield | latest regular `value` × payments per year / current price (same currency and units) |

Cross-check `SplitsDividends.PayoutRatio`, which is vendor-defined. Dividend currency can differ from the
price currency: LSE dividends usually arrive in GBP while the price is in GBX. Full dividend-quality
screening and monitoring belongs in [funds-income.md](funds-income.md).

### 3.12 Share count: dilution, buybacks and shareholder yield

- **Dilution rate** (annual) = S_y / S_{y−1} − 1, with S = diluted shares from `outstandingShares`
  (split-adjusted per the FAQ). For CAGR use (S_y / S_{y−n})^(1/n) − 1.
- **Share-count buyback yield** = −(S_y / S_{y−1} − 1). Positive = net shrinkage.
- **Cash buyback yield** = net_buyback_TTM / market cap. Net of issuance, per `salePurchaseOfStock`.
- **Gross issuance** = `issuanceOfCapitalStock` (often null) and SBC = `stockBasedCompensation`. Report
  "buybacks offsetting SBC" when net_buyback ≈ SBC and the share count is flat.
- **Shareholder yield** = dividend yield + cash buyback yield. Optionally add net debt paydown / market cap,
  and label it if so.

**Pitfall.** `commonStockSharesOutstanding` (balance sheet, units), `SharesStats.SharesOutstanding`
(current) and `outstandingShares` (diluted history) are different quantities. Do not difference one
against another. Before a split, check that the series is split-consistent by looking for a jump equal to
the split ratio at `LastSplitDate`.

### 3.13 Market multiples and yields

| Multiple | Formula | Notes |
|---|---|---|
| P/E (trailing) | price / diluted EPS_TTM | EPS ≤ 0 → NM. Compare with `Valuation.TrailingPE`. |
| Earnings yield | EPS_TTM / price | Defined for negative EPS. Preferred for ranking. |
| EV/EBITDA, EV/EBIT, EV/Sales | EV (§7) / metric_TTM | Metric ≤ 0 → NM (except sales) |
| P/B | price / BVPS | |
| P/FCF, FCF yield | market cap / FCF_TTM, FCF_TTM / market cap | |
| PEG | (P/E) / (EPS growth in percent points), e.g. P/E 20 with 10% growth → 2.0 | Growth from `Earnings::Trend` `+1y` vs `0y` average, or the `growth` field. State the source. Growth ≤ 0 → NM. |
| Earnings yield spread | EPS_TTM / price − UST 10Y (decimal) | Use the same date for both, and a local government yield (`.GBOND`) outside the US |

**Acceptance checks for §3.** A test fixture with one negative-EPS company: P/E is NM, earnings yield is
negative, and the company is excluded from P/E quartiles (§8.4) but included in earnings-yield ranks.
Revenue 0 gives NM margins.

### 3.14 Owner earnings and investor-lens checklists

**Use when:** a user asks for "owner earnings", or for a named investor-style checklist (deep value,
quality compounder, GARP, magic-formula-type rank, cycle checklist) applied to one stock.

**EODHD inputs:** `Financials` yearly: `netIncomeApplicableToCommonShares` (IS), `depreciation` (CF) or
`depreciationAndAmortization` (IS), `capitalExpenditures` (CF, normalized to `capex_out` per §1.4),
`changeInWorkingCapital` (CF, cash-flow sign), `totalRevenue`, `propertyPlantAndEquipmentNet`. One
Fundamentals request (10 calls). Maintenance capex is **not** a reported field.

**Method.**
- **Owner earnings** OE = NI_common + D&A + other non-cash charges − maintenance capex +
  `changeInWorkingCapital` (cash-flow sign, so cash absorbed by working capital reduces OE). Units:
  statement currency per fiscal year. Do not add back `stockBasedCompensation`: SBC stays a cost here,
  and if the user wants it added back, label the variant.
- **Maintenance capex** (choose one and label it):
  1. user-supplied (from the annual report or management commentary);
  2. growth-capex split: growth capex = (avg PP&E_net / avg revenue) × Δrevenue, maintenance =
     capex_out − growth capex, floored at 0 and capped at capex_out. In a year with falling revenue,
     growth capex is negative, so the cap applies and maintenance = capex_out;
  3. D&A proxy: maintenance = min(capex_out, D&A), labelled "D&A proxy" (it understates maintenance in
     inflationary periods).
- Report OE next to plain FCF (§3.4) and OE yield = OE / market cap on the same date and currency.
- **Investor-lens wrapper.** A lens is a list of criteria. Each criterion has a type:
  - `quantified`: bound to a formula in this chapter (e.g. §3.9 Graham tests, §3.8 F-score, earnings yield
    and return on capital ranks in [methods-technical-market.md](methods-technical-market.md) §14, §9.2
    moat metrics). Each is pass, fail or unscored (missing input), never a silent 0.
  - `qualitative`: management quality, candour, competitive behaviour, "a business I understand", cycle
    sentiment. These are recorded as **unscored judgement** with the evidence the user or analyst cites.
    They never enter a numeric total.
  Output `passed / scored` for the quantified criteria, the unscored list, and the qualitative notes in a
  separate column. Do not name the lens after a person unless the user did, and do not claim the person
  would endorse the result.

**Pitfalls.** A maintenance-capex estimate drives OE more than any reported line, so show the method and
an alternative. Acquisitive companies spend on `investments` rather than `capitalExpenditures`, so OE
ignores acquisition spend unless the user adds it. Banks and insurers: OE is NM (no meaningful capex or
working capital).

**Acceptance checks.** NI 100, D&A 40, capex_out 60, `changeInWorkingCapital` −10, avg PP&E / avg revenue
0.30, Δrevenue 100 → growth capex 30, maintenance 30, OE = 100.0. The same with the D&A proxy → OE = 90.
A lens with 4 quantified criteria (one input missing) and 2 qualitative ones reports `x/3` plus 1 unscored
and 2 judgement notes.

---

## 4. Cost-of-capital inputs

**Use when:** building a discount rate for DCF, residual income or an ROIC − WACC spread.

### 4.1 Risk-free rate

- **US:** `/api/ust/yield-rates?filter[year]=YYYY` (all plans, beta). Read the row with `tenor == "10Y"`
  on or before the valuation date. `rate` is **percent**, so r_f = rate / 100. Paginate with
  `page[offset]` until `links.next` is null.
- **Other currencies:** `{CC}10Y.GBOND` through EOD (e.g. `DE10Y.GBOND`, `GB10Y.GBOND`; Fundamentals Feed
  or All-In-One). Treat `close` as a percent yield. Verify units with a probe before use.
- Match currency to the cash flows (a EUR model gets a EUR risk-free). Match tenor to duration (10Y is the
  convention), and use nominal with nominal (real yields come from `/ust/real-yield-rates`).

### 4.2 Beta

| Option | How | Notes |
|---|---|---|
| A. Fundamentals `Technicals.Beta` | Read the field | 5-year monthly vs the country's main index. Current only. Label "vendor beta". |
| B. Own regression (preferred for audit) | Weekly (`eod?period=w`) or monthly `adjusted_close` returns of the stock and of a local index (`GSPC.INDX`, `GDAXI.INDX`, …) over 2–5 years. β = cov(r_i, r_m) / var(r_m), with the **same** ddof for both. | Report the window, frequency, index, n and the standard error. Align dates by inner join, never forward-fill missing weeks. |
| C. Technical API `function=beta` | `technical/{S}?function=beta&code2=IXIC.INDX&period=N` (Extended or All-In-One, 5 calls) | `period` = number of data points (default 50). Confirm the return frequency by probe. |

Optional adjustments: **Blume** β_adj = 0.67·β + 0.33. **Unlever/relever (Hamada):**
β_U = β_L / (1 + (1 − t)·D/E) and β_L* = β_U·(1 + (1 − t)·D*/E*), using market D/E.
For a peer-median beta, unlever each peer, take the median, then relever at the target's structure.

**Pitfalls.** Index returns are price-only (`adjusted_close == close` for `INDX`) while stock adjusted
returns include dividends. The resulting bias is small for beta but should be noted. There are no FTSE or
current Russell indices: use a constituent-weighted proxy or a local ETF and label it. Thin trading biases
beta toward 0, so prefer weekly or monthly data for illiquid names.

**Acceptance check.** r_i = (0.02, −0.01, 0.03, 0.00), r_m = (0.01, −0.005, 0.015, 0.00) → β = 2.0.

### 4.3 Equity risk premium

**User-supplied**, with its source and date recorded. EODHD has no ERP field. A country-risk add-on can
reference the credit-risk sovereign endpoints (`/credit-risk/sovereign/*`, Fundamentals/All-In-One). Treat
it as an input the user accepts, not as a computed ERP.

Cost of equity (CAPM): **r_e = r_f + β × ERP** (+ user country premium).

### 4.4 Cost of debt

- **Primary:** r_d (pre-tax) = interestExpense_TTM / avg(Debt), with Debt per your §3.2 definition.
- **Fallbacks**, in order:
  1. If interest is null or 0 (FAQ: unavailable), or the result is outside [r_f − 1%, r_f + 15%], mark it
     unavailable.
  2. Use a user-supplied yield or spread.
  3. As a labelled proxy, use the HQM corporate par yield at a matching tenor:
     `/credit-risk/corporate/hqm-yields`, where `yield_value` is percent. It is a high-quality US curve,
     so add a user spread for lower credit quality.

### 4.5 Tax rate

- Effective t = taxProvision_TTM / incomeBeforeTax_TTM, bounded to [0, 0.5]. If pre-tax income ≤ 0, or the
  result is outside the bounds, use a **user-supplied statutory/marginal** rate.
- State which rate you used. Marginal is conventional for the debt shield in WACC. Effective is common for
  NOPAT in a near-term forecast.

### 4.6 Weights and WACC

- E = price × diluted shares, in statement currency (latest `outstandingShares` or `SharesStats`, reconciled).
- D = book Debt as a market-value proxy, labelled. With net cash, keep the weights on **gross** debt, never
  negative weights.
- WACC = E/(D+E) · r_e + D/(D+E) · r_d · (1 − t)

**Acceptance checks.** r_f printed with its date and tenor. Weights sum to 1. With D = 0, WACC = r_e.
Re-running with the UST row of the previous date changes WACC by exactly Δr_f × E/(D+E).

---

## 5. DCF (FCFF), sensitivity grid and reverse DCF

**Use when:** an intrinsic enterprise value is needed from explicit forecasts.

**EODHD inputs:** historical drivers from `Financials` (revenue growth, EBIT margin, D&A, capex,
`changeInWorkingCapital`, tax), WACC from §4, net debt and shares from the balance sheet and
`outstandingShares`, and the current price from EOD. **Forecast assumptions are user-supplied or
explicit model choices.** Consensus revenue and EPS from `Earnings::Trend` cover one year ahead at most.

**Method.**
1. Base year = latest TTM or FY (state which). Forecast N = 5–10 years of revenue, EBIT margin, tax,
   D&A/revenue, capex/revenue and NWC/revenue. Fade growth toward g by the last year.
2. FCFF_t = EBIT_t(1 − t) + D&A_t − capex_t − ΔNWC_t.
3. Discount factors. End-year convention: DF_t = (1 + WACC)^−t. **Mid-year:** DF_t = (1 + WACC)^−(t − 0.5).
   With a stub (valuation date inside a fiscal year), use year fractions from the valuation date to each
   period's midpoint, and include only the remaining part of the current-year flow.
4. Terminal value at the end of year N:
   - **Gordon:** TV_N = FCFF_N·(1 + g) / (WACC − g), only if WACC > g. Keep g ≤ long-run nominal growth for
     that currency (user-supplied), and typically ≤ r_f.
   - Under the mid-year convention the perpetuity's flows also arrive mid-year, so the consistent discount
     exponent is N − 0.5. Discounting at N is a common conservative simplification. Pick one and state it.
   - **Exit multiple:** TV_N = multiple × EBITDA_N (or EBIT_N), a price at the end of N, discounted at N.
     Take the multiple from §8 comps on the same definition.
5. EV = Σ PV(FCFF_t) + PV(TV). **TV share** = PV(TV) / EV. Flag it when > 75%.
6. Equity bridge and per-share value (§7). Divide by **diluted** shares on the same date as the price.
7. Report implied multiples (EV/EBITDA_TTM, implied exit multiple from a Gordon TV, implied g from an exit
   TV) as a coherence check.

```python
def dcf_fcff(fcff, wacc, g=None, exit_multiple=None, exit_metric=None, mid_year=True):
    """fcff: forecast FCFF for years 1..N (statement currency); rates decimal."""
    n = len(fcff)
    if g is not None and wacc <= g:
        raise ValueError("WACC must exceed g")
    times = [(i + 0.5) if mid_year else (i + 1) for i in range(n)]
    pv_explicit = sum(f / (1 + wacc) ** t for f, t in zip(fcff, times))
    if g is not None:
        tv, tv_time = fcff[-1] * (1 + g) / (wacc - g), (n - 0.5 if mid_year else n)
    else:
        tv, tv_time = exit_multiple * exit_metric, n
    pv_tv = tv / (1 + wacc) ** tv_time
    ev = pv_explicit + pv_tv
    return {"ev": ev, "pv_explicit": pv_explicit, "pv_tv": pv_tv, "tv_share": pv_tv / ev}

def sensitivity(fcff, wacc, g, dw=0.005, dg=0.005, k=2, **kw):
    """(2k+1)x(2k+1) grid; centre cell == base case; None where WACC <= g."""
    ws = [wacc + i * dw for i in range(-k, k + 1)]
    gs = [g + j * dg for j in range(-k, k + 1)]
    return ws, gs, [[dcf_fcff(fcff, w, x, **kw)["ev"] if w > x else None for x in gs] for w in ws]

def reverse_dcf_growth(target_ev, base_fcff, years, wacc, g_terminal, lo=-0.5, hi=1.0):
    """Constant explicit-period FCFF growth that reproduces target_ev (bisection)."""
    def gap(gr):
        flows = [base_fcff * (1 + gr) ** (i + 1) for i in range(years)]
        return dcf_fcff(flows, wacc, g_terminal)["ev"] - target_ev
    if gap(lo) * gap(hi) > 0:
        return None                               # no solution in bracket: report, do not extrapolate
    for _ in range(200):
        mid = (lo + hi) / 2
        if gap(lo) * gap(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2
```

**Sensitivity grid.** Use an odd size with WACC on rows and g (or exit multiple) on columns. Recompute
every cell with the full model, never by linear approximation. Blank cells where WACC ≤ g. Optional second
grids: margin × growth, and per-share value. **The centre cell must equal the base case exactly.**

**Reverse DCF.** Solve for the single unknown (explicit-period growth, terminal margin or g) that makes the
model EV equal the **market EV** (§7). Present the result as "the market price is consistent with X% FCFF
growth for N years at WACC Y", together with the sensitivity of X to WACC. Return "no solution in range"
rather than an extrapolated number.

**Pitfalls.**
- TV not discounted, or discounted at N + 1.
- WACC on book equity.
- FCFF computed after interest (that is FCFE).
- FCFE discounted at WACC.
- Statement currency ≠ listing currency, or GBX price × GBP shares.
- Net cash subtracted twice: in the weights and again in the bridge, inconsistently.
- Dividing by basic shares while the market cap uses diluted shares.
- `capitalExpenditures` sign not normalized.
- Using `Valuation.EnterpriseValue` as the market EV without reconciliation (§7).

**Acceptance checks.**
- FCFF = 100 for 5 years, WACC 10%, g 0, end-year convention: EV = 1,000.00 (TV share 62.09%).
- The same with mid-year convention and the consistent TV timing: EV = 1,048.81 = 1,000 × 1.1^0.5.
- Grid centre = base (1,227.90 for FCFF 100 × 5, WACC 10%, g 2%, mid-year).
- Reverse DCF on a model built with 5% growth (base FCFF 100, WACC 9%, g 2%) returns 0.0500 ± 1e-6.
- EV − net debt − minorities − preferred + non-operating assets = equity, and per-share × diluted shares
  = equity.

---

## 6. Dividend discount and residual income models

### 6.1 Gordon growth and multi-stage DDM

**Use when:** valuing a stable dividend payer (utilities, banks, where FCFF is NM) on dividends.

**EODHD inputs:** the `div` endpoint (`value` split-adjusted, `unadjustedValue`, `period`, `currency`),
`SplitsDividends.ForwardAnnualDividendRate` (cross-check), and the cost of equity from §4. Payout and ROE
come from `Financials`.

**Method.**
- D0 = TTM regular DPS (§3.11) in today's share terms (`value`). Exclude specials.
- **Gordon:** P0 = D1 / (r_e − g), D1 = D0 × (1 + g), r_e > g. Sustainable-growth cross-check:
  g ≈ ROE × (1 − payout).
- **Two-stage:** P0 = Σ_{t=1..N} D0(1+g1)^t / (1+r)^t + [D_N(1+g2)/(r − g2)] / (1+r)^N.
- **H-model** (linear fade from g_S to g_L over 2H years): P0 = D0(1+g_L)/(r − g_L) + D0·H·(g_S − g_L)/(r − g_L).
- Historical dividend growth: CAGR of calendar-year sums of split-adjusted `value`, excluding specials.
  Unscore years with missing payments rather than counting them as cuts. A year with fewer payments than
  `NumberDividendsByYear` implies is a timing artefact, not a cut.

**Pitfalls.** Using `unadjustedValue` across a split inflates or deflates growth. Mixing the GBP dividend
with a GBX price gives a 100× yield error. A DDM is meaningless for non-payers and fragile when payout is
volatile.

**Acceptance checks.** D0 = 1.00, g = 3%, r = 8% → 20.60. A two-stage model with g1 = g2 equals Gordon.

### 6.2 Residual income (abnormal earnings)

**Use when:** valuing on book value and ROE, which suits financials and companies with negative FCF.

**Method.**
- V0 = B0 + Σ_{t=1..N} RI_t / (1+r)^t + TV_N / (1+r)^N
- RI_t = E_t − r·B_{t−1} = (ROE_t − r)·B_{t−1}
- Clean surplus: B_t = B_{t−1} + E_t − D_t (net of buybacks if they are modelled as distributions)
- TV_N = RI_{N+1} / (r − g) for growing RI, or RI_{N+1} / (1 + r − ω) with persistence 0 ≤ ω < 1 (fading)

Inputs:
- B0 = totalStockholderEquity (common: less `preferredStockTotalEquity` and noncontrolling interest)
- E_t from forecast ROE or from `Earnings::Trend` EPS × shares for year 1
- r = r_e from §4

**Pitfalls.** Clean surplus breaks when OCI is large (`accumulatedOtherComprehensiveIncome` swings). Note
it. Book value per share must use the same share count as the EPS.

**Acceptance checks.**
- If ROE_t = r every year, V0 = B0.
- Example: B0 = 100, r = 10%, E = 15 each year, D = 5 each year, N = 3, no TV →
  B = (100, 110, 120, 130), RI = (5, 4, 3), V0 = 110.11.

---

## 7. EV bridge and reconciliation

**Use when:** computing EV for multiples, bridging DCF EV to equity, or checking vendor EV.

**Method.** All in statement currency, at one date:

```
Market cap (MC)      = price × diluted shares         (price converted from GBX/ZAC and FX)
+ Debt               = shortLongTermDebtTotal  OR  shortTermDebt + longTermDebt   (declare; leases in or out)
+ Preferred          = preferredStockTotalEquity
+ Minority interest  = noncontrollingInterestInConsolidatedEntity
− Cash               = cashAndEquivalents  OR  cashAndShortTermInvestments        (declare)
− Non-operating assets (user-identified: longTermInvestments, equity-method stakes)  optional, labelled
= Enterprise value (EV)
```

DCF bridge (reverse direction): Equity = EV_DCF − Debt − Preferred − Minority + Cash + non-operating
assets. Per share = Equity / diluted shares.

**Reconciliation steps.**
1. Compute EV_own with the latest balance sheet (`Highlights.MostRecentQuarter` should equal its date)
   and today's price.
2. Compare with `Valuation.EnterpriseValue` and MC with `Highlights.MarketCapitalization`. Also compare
   `us-quote-delayed.marketCap` for US names, and `historical-market-cap` for US weekly history in USD.
3. If |EV_own / EV_vendor − 1| > 2%, show both, list the candidate causes (cash definition, lease
   inclusion, share count, price date, currency) and use EV_own in the model. The probe in §1.3 shows a
   real gap of this kind.
4. Multiples must use an EV whose debt and cash definition matches the denominator. EBITDA after
   IFRS 16 or ASC 842 lease reclassification pairs with debt including leases.

**Acceptance checks.** EV_own components sum exactly. The price date, balance-sheet date and FX date are
printed. A GBX listing gives MC within 1% of the vendor value only after ÷100 normalization.

---

## 8. Comps, tear sheets, sector history, positioning, industry outlines and SOTP

### 8.1 Peer set

**Use when:** building a comparable-companies table or a sector-relative view.

**EODHD inputs:**
- Screener (Extended or All-In-One, 5 calls per page, ≤ 500 rows, offset ≤ 999) with filters on `sector`
  and `industry` (`match` for multi-word values), `exchange` and a `market_capitalization` band. Market
  cap is in listing currency, so constrain the exchange or convert.
- Alternatively, local filtering of `General.Sector`/`Industry`/`GicSubIndustry` over a symbol list.
- Fundamentals for each peer (10 calls each).

**Rules.**
1. Start from the narrowest classification (GICS sub-industry or industry) and widen only to reach n ≥ 5
   (target 8–15). Record the widening step.
2. Size band: 0.2× to 5× the target's market cap (user-adjustable). Apply the same band on revenue for
   loss-makers.
3. One line per issuer: keep `PrimaryTicker`, drop secondary listings and ADR duplicates
   (`HomeCategory`, ISIN).
4. Exclude companies that cannot be aligned: no LTM period within 6 months of the target's, a different
   business model, or financials when the target is not. Write each exclusion with its reason.
5. Freeze the peer list with a date. Re-runs use the frozen list unless the user changes it.

### 8.2 Comps table construction

Operating block (from statements, LTM and FY+1):
- revenue, growth, gross, EBITDA and EBIT margins, NI, EPS, FCF, ROIC
- net debt / EBITDA

Market block:
- price (date), MC, EV (§7), EV/Sales, EV/EBITDA, EV/EBIT, P/E LTM, P/E FY+1, P/B, FCF yield, dividend yield

Multiples reference the operating cells (in a workbook, as formulas).

- **Calendarization.** For different fiscal year ends, compute LTM to the latest quarter (§2.2) or
  calendarize: CY metric = w·FY_a + (1 − w)·FY_b, where w = months of FY_a inside the calendar year / 12.
- **Forward P/E.** price / EPS_FY+1, with EPS from `Earnings::Trend` (`+1y` `earningsEstimateAvg`) or
  `Highlights.EPSEstimateNextYear`.
  - "Current year" in `Highlights` means the fiscal year not yet reported, which may already have ended
    (probe: the September-2026 FY was "current" in October 2026).
  - **NTM EPS** = w·EPS_0y + (1 − w)·EPS_+1y, with w = fraction of the current fiscal year remaining.
  - Compare with `Valuation.ForwardPE`, whose horizon is not documented.
- **Consensus dispersion** = (earningsEstimateHigh − earningsEstimateLow) / |earningsEstimateAvg|, shown
  with `earningsEstimateNumberOfAnalysts`. If the count is < 3, show the dispersion as "thin". If
  |avg| < 0.01, it is NM.
- **Revision momentum** = epsTrendCurrent / epsTrend30daysAgo − 1, and the net revision count
  (up30 − down30) / analysts.
- **52-week position** = (P − 52WeekLow) / (52WeekHigh − 52WeekLow), in the same price basis. Vendor
  52-week fields can be on another basis, so recompute from EOD raw high and low.
- **Currency.** Convert every monetary column to one reporting currency with the dated FX rate shown in
  the table footer. Ratios need no conversion if numerator and denominator are in the same currency.

### 8.3 Aggregation rules

- A ratio of aggregates is not a mean of ratios. **Aggregate (sector) P/E = Σ MC / Σ earnings**, which
  equals the cap-weighted harmonic mean of P/E. State whether loss-makers are included (they lower the
  denominator) or excluded.
- Equal-weight sector "average P/E" uses the **median** of meaningful values, not the arithmetic mean.
- Never sum or average percentages that have different bases.

### 8.4 Statistics rows

Max, 75th percentile, median, 25th percentile and min, computed **only on meaningful values** (exclude NM).
Show `n used / n peers`. State the percentile method (e.g. linear interpolation, the pandas default). Do not
compute statistics on absolute values such as revenue (they are not comparable). Do compute them on
growth and margins. The target's percentile rank within peers goes in a separate column.

**Implied valuation range.** Target metric × peer 25th–75th percentile multiple → implied EV → equity
(§7) → per share. Present it as a range. Do not present a point estimate from the median alone.

### 8.5 Sector valuation history

**Use when:** showing whether a sector's multiple is high or low versus its own history.

**Method.**
1. Members = current classification (look-ahead and survivorship, so **label it**). Add delisted names
   from `exchange-symbol-list/{EX}?delisted=1` where fundamentals exist (post-2018 delistings) to reduce
   survivorship.
2. For each quarter-end q and member i:
   - available date a_i = `filing_date` if it is later than the period end, otherwise period end + the
     declared lag (§2.3);
   - price at the first trading day ≥ max(q, a_i);
   - shares from `outstandingShares` quarterly;
   - TTM earnings or EBITDA (§2.2).
   - US alternative for market cap: `historical-market-cap` (weekly, USD, from 2021-07-09).
3. Sector multiple per date = aggregate (Σ MC / Σ E, positive E only, labelled) and median.
4. Show sector premium or discount = sector multiple / market multiple − 1, where the market is a broad
   proxy universe built the same way.

**Pitfalls.** Fundamentals are restated current versions, so a "history" is a current-vintage
reconstruction, not what was known then. Equal-sized peers with outliers dominate the means, which is why
the median is used.

### 8.6 Tear sheet and chart pack

Tear sheet sections:
- identity (General: name, ticker, ISIN, sector/industry, country, FY end, employees, description excerpt)
- price block (price, date, 52-week range and position, MC, EV, beta with source)
- valuation (P/E LTM and NTM, EV/EBITDA, P/B, FCF yield, dividend yield)
- operating trend (5-year revenue, margins, FCF, ROIC)
- balance sheet (net debt/EBITDA, coverage, current ratio)
- consensus (FY0/FY+1 average, high, low, count, revisions)
- ownership (top holders with dates, insider net activity over 90 days)
- events (next report date and timing)
- data notes

**Chart pack.**
1. Price rebased to 100 vs a benchmark, both adjusted close and both in the same currency.
2. Revenue bars with a margin line (FY, actual vs estimate styled differently).
3. Valuation band: historical P/E or EV/EBITDA from §8.5-style reconstruction, with median and ±1 sd.
4. Peer multiple bars with the target highlighted.
5. **Football field:** horizontal ranges for the 52-week trading range, the comps interquartile implied
   value (§8.4), the DCF sensitivity range (the inner 3×3 of the grid) and any user-supplied ranges, with
   the current price marked by a vertical line.

Every chart carries an as-of date and units.

**Snapshot performance rows** (equity-research snapshot and strip profile):

| Row | Formula | Source |
|---|---|---|
| YTD total return | adj_close(t) / adj_close(last session of the prior calendar year) − 1 | EOD `adjusted_close` (1 call) |
| 1Y total return | adj_close(t) / adj_close(last session on or before t − 365 days) − 1 | same request |
| Benchmark YTD / 1Y | same formulas on the benchmark, shown in the next column | `.INDX` is price-only (`adjusted_close == close`), so either label it "price return" or use a total-return ETF proxy's `adjusted_close`, labelled |
| Relative | stock return − benchmark return, in percentage points | calculation |

Both legs use the same end date t and the same currency. A listing younger than the window shows
"n/a (listed YYYY-MM-DD)", not a shorter-window return under the same label.

**Macro-context block** (one line each, every value with its own date or period):
- 10Y government yield: US from `/api/ust/yield-rates` (`tenor == "10Y"`, `rate` in percent, §4.1);
  elsewhere `{CC}10Y.GBOND` through EOD, units verified by probe.
- CPI inflation and real GDP growth for the listing country: `/api/macro-indicator/{ISO3}` with
  `indicator=inflation_consumer_prices_annual` and `gdp_growth_annual` (annual, percent, `Date` and
  `Period` printed). `General.CountryISO` is a 2-letter code, so map it to ISO 3166-1 alpha-3 with a
  maintained table. An unknown indicator code returns plain text, not JSON
  ([api/endpoints/macro-indicator.md](api/endpoints/macro-indicator.md)), so treat a non-JSON reply as
  "unavailable".
- Annual macro values are often more than a year old. Print the period, never "current inflation".

**Recent-news block** (strip profile and tear sheet): `news?s={S}&from={D−90}&to={D}&limit=50`
(5 calls per ticker, [plans-limits.md](plans-limits.md)). Show 3–8 headlines with publication date and
link, newest first, after removing near-duplicate titles (same cluster per
[app-ai-patterns.md](app-ai-patterns.md) §10). Headlines are observations; do not attribute a price move
to a headline without the event-study method in [methods-quant-research.md](methods-quant-research.md) §8.
If nothing was returned, print "no news items in the window" rather than leaving the block out.

**Acceptance checks for §8.**
- Recomputed EV and margins match the displayed cells within 0.1%.
- Every number has an as-of date.
- Peers lacking an aligned LTM are listed as excluded, not silently dropped.
- Two stocks with MC (100, 100) and E (10, 1) give a mean P/E of 55 but an aggregate P/E of 18.18.
- A negative-EPS peer is excluded from P/E statistics and appears as "NM".
- Adjusted closes 100 (last session of the prior year), 95 (one year ago) and 112 (today) give YTD
  +12.0% and 1Y +17.9%. Every macro line prints its period.

### 8.7 Competitive positioning: 2×2 chart and metric-definition table

**Use when:** a competitive-landscape deck or section needs a positioning chart and a side-by-side
metrics table for the §8.1 peer set.

**EODHD inputs:** the §8.2 comps table (one Fundamentals request per peer, 10 calls each, plus EOD for
prices). Market share, segment KPIs and industry-specific operating metrics (subscribers, same-store
sales, ARPU) are **user-supplied**.

**Method.**
1. **Metric-definition table** (printed with the comps, one row per metric):

   | Metric | Formula | Period | Basis | Source field(s) | NM rule |
   |---|---|---|---|---|---|
   | Revenue growth | Rev_LTM / Rev_LTM−4q − 1 | LTM | reported, statement currency | `totalRevenue` quarterly (§2.2) | prior ≤ 0 |
   | EBITDA margin | (EBIT + D&A) / revenue | LTM | declared EBIT field | IS, CF (§3.1) | revenue ≤ 0 |
   | EV/EBITDA | EV (§7) / EBITDA_LTM | price date + LTM | own EV | §7 | EBITDA ≤ 0 |
   | ROIC | NOPAT_LTM / avg IC | LTM | declared IC view | §3.2 | IC ≤ 0, financials |
   | Market cap | price × diluted shares | price date | reporting currency, dated FX | EOD, `outstandingShares` | — |

   Add a row for every metric that appears anywhere in the deck. A metric with no row is not shown.
2. **2×2 positioning chart spec.**
   - Axis pairs (choose one per chart): revenue growth (x) vs EBITDA margin (y); revenue growth (x) vs
     EV/EBITDA (y); ROIC (x) vs EV/invested capital (y). Both axes use the same period and basis for all
     peers.
   - Quadrant lines at the **peer medians** of meaningful values (§8.4), with the target excluded from
     the median calculation and the medians printed on the lines.
   - Bubble area ∝ market cap in one reporting currency (radius ∝ √cap). Print the cap legend.
   - Points that are NM on either axis are **listed in a footnote** with the reason, never plotted at 0
     or at an axis edge.
   - Highlight the target; label every point with its ticker; print the as-of date, period and currency.
   - Clip extreme values only with a visible break marker and the true value in the label.
3. Quadrant labels (e.g. "high growth, high margin") are descriptive. Do not label a quadrant
   "undervalued".

**Pitfalls.** Mixing fiscal years across peers without calendarization (§8.2). Bubble radius ∝ cap
(instead of area) exaggerates large peers. Medians that include the target move the lines when the
target changes.

**Acceptance checks.** Peers with growth (0.05, 0.10, 0.15, NM) give an x median of 0.10 on 3 meaningful
values, and the NM peer appears in the footnote. Every metric shown has a definition row.

### 8.8 Industry research outline

**Use when:** writing an industry or sector report from listed companies, as opposed to a single-company
report.

**EODHD inputs:** members from the Screener (`sector`, `industry`) or local `General.Industry` /
`GicIndustry` over a symbol list, Fundamentals per member (10 calls each), EOD for prices, sector ETFs as
price proxies, `macro-indicator` for the country backdrop and `news?t=` topic tags. Market size, TAM,
private competitors and regulation are user-supplied.

**Method.**
1. **Constant-member aggregates.** Use the same members in both periods (drop anyone missing either
   period and list them):
   - industry revenue growth = Σ Rev_t / Σ Rev_t−1 − 1;
   - industry margin = Σ OperatingIncome_t / Σ Rev_t (ratio of sums, not the mean of margins);
   - industry multiples per §8.3 (Σ MC / Σ E, positive E only, labelled).
2. **Concentration among listed members.** Shares s_i = Rev_i / Σ Rev. Top-N share = Σ of the N largest
   s_i. HHI = Σ (100·s_i)², on a 0–10,000 scale. Label it "listed-company concentration": private
   companies and foreign competitors without a listing are missing, so it is not a market HHI.
3. **Section order:** (1) definition and member list with the classification date; (2) size and growth
   (aggregates, with the user-supplied TAM if any); (3) profitability and returns (aggregate margins,
   ROIC distribution); (4) concentration and positioning (§8.7 chart); (5) valuation vs own history
   (§8.5); (6) drivers and macro backdrop (§8.6 macro block, sector-ETF relative performance); (7) risks
   and recent news; (8) company short-list with the §9.1 composite; (9) data notes (classification is
   current only, survivorship, currency conversions).
4. Convert all monetary values to one currency with dated FX before summing.

**Pitfalls.** Membership is today's classification, so historical aggregates carry look-ahead and
survivorship (§8.5). One large member can dominate a ratio of sums, so also show the median.

**Acceptance checks.** Revenues (500, 300, 120, 80) against prior (450, 280, 130, 60) and operating income
(100, 45, 6, −8) give industry growth 8.70%, aggregate margin 14.3% (the mean of margins would be 7.5%),
top-2 share 0.80 and HHI 3,608.

### 8.9 Sum-of-the-parts (SOTP)

**Use when:** a company has segments that deserve different multiples (conglomerates, holding companies,
groups with a listed subsidiary).

**EODHD inputs:** segment metrics are **user-supplied** (EODHD has no segment data, §15). Peer
multiples per segment come from §8 comps on EODHD pure-play peers. A listed subsidiary or stake can be
valued at market: EOD price × shares held (holding user-supplied) in the reporting currency. Net debt,
minorities and preferred come from the group balance sheet (§7).

**Method.**
1. Per segment k: EV_k = metric_k × multiple_k, with the metric (EBITDA, EBIT, revenue) matching the
   multiple's definition and period. Take the multiple from the peer interquartile range (§8.4), so each
   segment has low/mid/high values.
2. Unallocated corporate costs: subtract central cost × a blended multiple (user-chosen, labelled), or
   allocate the costs to segments before step 1. Do not do both.
3. Gross value = Σ EV_k − capitalized corporate costs + listed stakes at market + other non-operating
   assets.
4. Equity = gross value − net debt − minorities − preferred (§7). Apply the holding-company discount d
   (user-supplied, e.g. 0–30%) to equity: Equity_adj = Equity × (1 − d). Some analysts apply d to gross
   asset value instead; state which.
5. Per share = Equity_adj / diluted shares. Show the low/mid/high range and the share of value per segment.
6. Compare with the market cap: implied discount = 1 − market cap / Equity (before d).

**Pitfalls.** Segment EBITDA that already absorbs corporate costs, then subtracting the costs again.
Using a listed subsidiary's EV instead of the parent's share of its equity. Taxes on a hypothetical
disposal of a stake are user-supplied, not ignored silently.

**Acceptance checks.** Segment A EBITDA 200 × 10 = 2,000; B EBIT 50 × 14 = 700; C revenue 100 × 1.5 = 150;
corporate costs 20 × 8 = 160 → gross value 2,690. Net debt 600 and minorities 40 → equity 2,050; with a
10% holding discount → 1,845, or 18.45 per share on 100 diluted shares.

---

## 9. Composite scoring, moat evidence and idea screens

### 9.1 Composite scoring within a sector

**Use when:** ranking companies on several fundamentals at once (value, quality, growth, momentum, revisions).

**EODHD inputs:** §3 and §8 metrics for one dated peer universe. Momentum comes from EOD `adjusted_close`.
Revisions come from `Earnings::Trend` (current snapshot only, so history of revisions needs your captures).

**Method.**
1. Define the universe and date. Group by sector (or industry if n ≥ 10 per group). Groups with fewer than
   `n_min` (default 10) members merge into the parent level, and the merge is recorded.
2. Per metric, set the orientation: higher is better (ROIC, earnings yield, FCF yield) or lower is better
   (net debt/EBITDA, accruals). Use **yields instead of multiples** so that negative earnings rank
   correctly.
3. Clean: drop NM, then winsorize within the group at the 5th and 95th percentiles (or 1st/99th for
   n > 100).
4. Standardize within the group, using either:
   - **percentile rank** p = (rank − 0.5) / n, with ties averaged and inverted when lower is better; or
   - **z-score** z = (x − mean) / sd with sample sd (ddof = 1), and z = 0 when sd = 0.
   Percentiles are robust and bounded. z-scores keep magnitude. Do not mix them in one composite.
5. Composite = Σ w_m·s_m / Σ w_m over **available** metrics only. Compute coverage = Σ w_available /
   Σ w_all. If coverage < 0.6 (default), the company is **not scored**. Never impute 0 or the group mean
   silently.
6. Output the score, coverage, group, n in group, each component's raw value and standardized value, and
   the list of missing components.

```python
def composite(rows, weights, higher_is_better, min_coverage=0.6):
    """rows: {ticker: {metric: value or None}} for ONE peer group. Percentile ranks; missing = unscored."""
    pct = {}
    for m in weights:
        vals = sorted((v, t) for t, r in rows.items() if (v := r.get(m)) is not None)
        n, i, pct[m] = len(vals), 0, {}
        while i < n:                                  # average rank for ties
            j = i
            while j + 1 < n and vals[j + 1][0] == vals[i][0]:
                j += 1
            p = ((i + j) / 2 + 0.5) / n
            for k in range(i, j + 1):
                pct[m][vals[k][1]] = p if higher_is_better[m] else 1 - p
            i = j + 1
    out, w_all = {}, sum(weights.values())
    for t in rows:
        got = {m: pct[m][t] for m in weights if t in pct[m]}
        cov = sum(weights[m] for m in got) / w_all
        score = None if cov < min_coverage else sum(weights[m] * got[m] for m in got) / sum(weights[m] for m in got)
        out[t] = {"score": score, "coverage": cov, "missing": [m for m in weights if m not in got]}
    return out
```

**Pitfalls.**
- Cross-sector z-scores reward sector membership, not company quality.
- Ranking "cheapest P/E" sorts loss-makers first.
- A score computed on today's restated fundamentals and today's classification is not a historical signal.
  Factor back-tests need captured vintages (see [research-validation.md](research-validation.md)).

**Acceptance check.** Rows A (ey 0.08, roic 0.20), B (0.05, None), C (0.02, 0.10), D (None, None) with equal
weights give A 0.7917, C 0.2083, and B and D not scored (coverage 0.5 and 0.0).

### 9.2 Moat evidence rubric (quantified evidence, qualitative judgement labelled)

**Use when:** assessing whether a company has a durable competitive advantage and turning that view into
explicit valuation inputs.

**EODHD inputs:** up to 10 fiscal years of `Financials` yearly (ROIC per §3.2, gross margin per §3.1,
`totalRevenue`) and `outstandingShares` annual, plus WACC per §4 (a single current WACC applied to all
years, labelled). One Fundamentals request (10 calls). History depth: major US from 1985, others from
about 2000, small caps about 6 years (§1.1).

**Method.**
1. Compute per fiscal year: spread_y = ROIC_y − WACC, GM_y, revenue growth_y, and the diluted-share CAGR
   over the window.
2. Score each metric 0/1/2 with declared bands. The defaults below are heuristics, user-adjustable, and
   printed with the result:

   | Metric | 2 points | 1 point | 0 points |
   |---|---|---|---|
   | Spread persistence = share of years with spread > 0 | ≥ 0.8 | ≥ 0.5 | < 0.5 |
   | Median spread | ≥ 0.05 | ≥ 0 | < 0 |
   | Gross-margin stability = sample sd of GM (ddof = 1) | ≤ 0.02 | ≤ 0.05 | > 0.05 |
   | Revenue-growth consistency = share of years with growth > 0 | ≥ 0.8 | ≥ 0.6 | < 0.6 |
   | Dilution = diluted-share CAGR | ≤ 0 | ≤ 0.02 | > 0.02 |

   A metric with fewer than 5 years of inputs is **unscored**, never 0. Evidence score = points /
   (2 × scored metrics), computed only if at least 3 metrics are scored. Bands: ≥ 0.75 strong,
   0.5–0.75 moderate, < 0.5 weak (heuristic labels).
3. **Qualitative sources of advantage** (brand, network effects, switching costs, cost advantage,
   regulation, management capital allocation) go in a separate table: claim, evidence cited, who made
   the judgement. They are labelled `judgement` and never change the numeric score.
4. **Map to valuation inputs** (model choices, labelled):
   - competitive-advantage period: the number of explicit years before ROIC on new investment (RONIC)
     reaches WACC, e.g. strong 10, moderate 7, weak 5 (user-set);
   - terminal value by value drivers: TV_N = NOPAT_{N+1} × (1 − g / RONIC) / (WACC − g). With RONIC =
     WACC, growth adds no value and TV_N = NOPAT_{N+1} / WACC. Use RONIC > WACC in the terminal value only
     for a strong score, and show the sensitivity;
   - do not also cut the discount rate for a moat. That counts the same advantage twice. A weak or
     unscored result widens the scenario range (§5 grid) rather than adding an unexplained premium to
     WACC. If the user insists on a WACC adjustment, record it as a judgement input.

```python
import statistics as st

BANDS = {  # metric: ((2-point, 1-point) thresholds, higher_is_better) - heuristics, user-adjustable
    "spread_persistence": ((0.8, 0.5), True),
    "median_spread":      ((0.05, 0.0), True),
    "gm_sd":              ((0.02, 0.05), False),
    "growth_pos_share":   ((0.8, 0.6), True),
    "share_cagr":         ((0.0, 0.02), False),
}

def moat_evidence(spread, gm, growth, shares, min_years=5):
    """spread: ROIC-WACC per FY; gm: gross margin per FY; growth: revenue growth per FY;
    shares: diluted shares first..last FY. Lists may contain None. Returns points per metric."""
    clean = lambda xs: [x for x in xs if x is not None]
    s, g, r = clean(spread), clean(gm), clean(growth)
    m = {
        "spread_persistence": sum(x > 0 for x in s) / len(s) if len(s) >= min_years else None,
        "median_spread": st.median(s) if len(s) >= min_years else None,
        "gm_sd": st.stdev(g) if len(g) >= min_years else None,
        "growth_pos_share": sum(x > 0 for x in r) / len(r) if len(r) >= min_years - 1 else None,
        "share_cagr": (shares[-1] / shares[0]) ** (1 / (len(shares) - 1)) - 1 if len(shares) >= min_years else None,
    }
    pts = {}
    for k, v in m.items():
        if v is None:
            pts[k] = None                                 # unscored, never 0
            continue
        (t2, t1), hib = BANDS[k]
        pts[k] = (2 if v >= t2 else 1 if v >= t1 else 0) if hib else (2 if v <= t2 else 1 if v <= t1 else 0)
    scored = [p for p in pts.values() if p is not None]
    score = sum(scored) / (2 * len(scored)) if len(scored) >= 3 else None
    return {"metrics": m, "points": pts, "score": score, "coverage": len(scored) / len(pts)}
```

**Pitfalls.** Ten years of history exist mainly for US large caps. ROIC is NM for banks and insurers, so
use ROE − cost of equity instead and say so. Buyback-driven negative equity distorts the financing-view
IC (§3.2). A high spread in a cyclical peak year is not persistence. Today's WACC applied to old years is
an approximation.

**Acceptance checks.** Spreads (0.06, 0.07, 0.05, 0.08, 0.06, 0.04, 0.07, 0.05, 0.06, 0.09), gross margins
around 0.40 with sd 0.0095, revenue growth positive in 7 of 9 years and shares 100 → 103 over 9 years give
points (2, 2, 2, 1, 1) and score 0.8 (strong). With only 3 years of inputs every metric is unscored and
the score is `None`. TV check: NOPAT 100, g 3%, WACC 8% → TV 1,250 at RONIC 8% and 1,625 at RONIC 16%.

### 9.3 Short-side screen

**Use when:** generating short ideas or a "what could go wrong" list from accounting and positioning
signals. The output is a list of flags for research, not a recommendation to sell short.

**EODHD inputs:** `Financials` quarterly and yearly (§3.4, §3.1), insider transactions (Fundamentals
`InsiderTransactions` for recent rows; `/api/insider-transactions?code=` or
`/api/sec-filings/{S}/form4` for depth, 10 calls), and `SharesStats.ShortPercentFloat` (decimal, **US
only**, current snapshot). The Screener gives the candidate pool (§8.1).

**Method.** Each flag is true, false or unscored (missing input).

| Flag | Rule (defaults user-adjustable) |
|---|---|
| Receivables ahead of sales | growth(netReceivables) − growth(totalRevenue) > 10 pp in the latest FY, or in each of the last 2 FY |
| Inventory ahead of COGS | growth(inventory) − growth(costOfRevenue) > 10 pp (NM for companies with no inventory) |
| Margin compression | operating margin_LTM − operating margin_LTM one year earlier ≤ −200 bp, and YoY margin down in at least 3 of the last 4 quarters |
| Accruals | cash-flow accruals ratio (§3.4) in the top quintile of the sector |
| Net insider selling, 90 days | Σ (shares × price) for code `S` − Σ for code `P` over the last 90 days > 0. Codes `M`, `A`, `G`, `F` and option exercises are excluded. Sales that a Form 4 footnote describes as made under a Rule 10b5-1 plan are listed separately (there is no dedicated field; read the `footnotes` text). |
| Dilution | diluted-share growth > 5% YoY without a matching acquisition |

Rank candidates by the number of true flags over scored flags, then by the accruals ratio. Print
`ShortPercentFloat` as **crowding context**: a high value (e.g. ≥ 0.15) means a crowded short and squeeze
risk, not a stronger signal. Borrow availability, borrow fees and locate data are not EODHD data, so the
user supplies them before any short is sized.

**Pitfalls.** Seasonal receivables at a fiscal year end, or an acquisition, can trip the receivables flag,
so check the quarterly pattern and `investments` first. Insider sales cluster around vesting and tax
dates. `ShortPercentFloat` is US-only and has no history in Fundamentals.

**Acceptance checks.** Receivables +25% vs revenue +8% (17 pp) → flag. Operating margin 0.12 vs 0.15 a year
earlier (−300 bp) with 3 of 4 quarters down → flag. Insider rows S 10,000 × 50, S 4,000 × 52, P 1,000 × 48
and M 20,000 → net selling 660,000 (the `M` row ignored) → flag. A non-US name shows `ShortPercentFloat`
as unavailable, and its flag count excludes it.

### 9.4 Special situations from the IPO calendar

**Use when:** looking for event-driven ideas around recent listings: lockup expiries, first earnings as
a public company, and IPOs trading far from the offer price.

**EODHD inputs:** `calendar/ipos?from=&to=&fmt=json` (1 call per request; All-In-One, Fundamentals Data
Feed or the Calendar & News product; data from January 2015 up to 2–3 weeks ahead). Fields: `code`,
`name`, `exchange`, `currency`, `start_date`, `offer_price`, `price_from`, `price_to`, `shares`,
`deal_type`. EOD for post-listing prices, `calendar/earnings` for the first report. Lockup terms are
**not** in the data.

**Method.**
1. Pull IPOs whose `start_date` lies 150–200 days before the as-of date (a window around the typical
   180-day lockup), plus the forward window for upcoming listings.
2. Keep rows with a `start_date`, a real ticker (`code` not `n/a`; resolve `n/a` by name via the Search
   API) and `offer_price` > 0. Zero means "not set", not a price of 0.
3. **Lockup estimate** = `start_date` + 180 calendar days, printed as "lockup date: **estimate**
   (180-day assumption; actual terms are in the prospectus, user-supplied)". Flag names whose estimate
   falls within the next N days (default 30).
4. Per name: return since offer = close / `offer_price` − 1 (same currency, raw close; check splits
   since listing), shares offered vs current shares outstanding, the next report date, and the
   estimated lockup date.
5. Output the dated list with every estimate labelled and the call count.

**Pitfalls.** Some filed IPOs never list. Lockups can be 90 days, staged or released early, so the
estimate is a screening date only. `start_date` can move. A rename after listing needs the symbol-change
history.

**Acceptance checks.** `start_date` 2026-05-01 → lockup estimate 2026-10-28, which is 3 days after an
as-of date of 2026-10-25, so the name is flagged in a 30-day window and the label contains "estimate".
A row with `offer_price` 0 is excluded from the return-since-offer column with the reason "not priced".

---

## 10. Earnings workflows and SEC filings

Links: event model and alert state in [events-news.md](events-news.md), the earnings-season monitor
(recipe 41), and option-quote hygiene in [options.md](options.md).

### 10.1 Earnings preview

**Use when:** preparing for a scheduled report: consensus, history of reactions, market-implied move.

**EODHD inputs:**
- Next report: `calendar/earnings?from=&to=` (Calendar, 1 call; filter locally because `symbols=` alone
  has returned empty), or `Earnings::History` rows with `epsActual` null, which carry `reportDate` and
  `beforeAfterMarket`.
- Consensus: `Earnings::Trend` (`0q`, `0y`; average, low, high, count, `epsTrend7/30daysAgo`, revisions)
  or `calendar/trends` (1 call for many symbols).
- Past reactions: `Earnings::History` (`reportDate`, `beforeAfterMarket`, `epsActual`, `epsEstimate`),
  EOD for the stock and its index.
- Implied move: Marketplace US options `options/eod` (US stocks and ETFs only, from Q4 2023, separate
  quota, 10 calls per page).

**Method.**
1. Label the fiscal quarter from the period-end `date`, never from `reportDate`. A January fiscal year end
   shifts the labels (§2.1).
2. **Reaction session** R: `BeforeMarket` → the report date itself. `AfterMarket` → the next trading
   session (use `exchange-details` holidays). Null or unknown timing → compute both and show both, or
   exclude.
3. Reaction return r = adj_close(R) / adj_close(R−1) − 1. Abnormal return a = r − r_index (or r − β·r_index).
   For each of the last N reports (N ≤ 12), record r, a, |r| and the surprise sign.
4. Distribution: median |r|, mean |r|, 25th/75th percentile of r, the fraction of up moves, and n. Never
   present the mean alone with N < 8.
5. **Implied move** (US optionable only): on the last observation day before R, which is the report day's
   close for an AMC report:
   - select the first expiry on or after R;
   - select the strike nearest spot;
   - straddle = call mid + put mid, with mid = `midpoint` or (bid + ask)/2;
   - **implied move ≈ straddle / spot**.
   This approximates the expected absolute move to expiry and includes the non-event days in that window.
   For a normal distribution E|X| = σ√(2/π) ≈ 0.80σ, so do not call it a 1σ move.
   Reject quotes with a null or zero bid, bid > ask, a relative spread > 25%, or a stale observation date.
6. Scenario table: bull, base and bear values for revenue, EPS and the reaction, **user-supplied**.

**Pitfalls.** Report dates are estimates until confirmed (FAQ), so re-pull on the day before. Calendar
`actual` is generally adjusted EPS and the trend consensus can be on another basis, so do not mix them
(coverage notes). Options are EOD snapshots and cannot show the intraday pre-report price.

**Acceptance checks.** An AMC report dated Thursday maps to Friday's session (or Monday if Friday is a
holiday). A test with a straddle of 6.00 on spot 100 gives 6.0%. The preview lists n, the source and the
basis for every statistic.

### 10.2 Post-earnings update

**Method.**
1. Beat/miss table: EPS actual vs estimate from **one source and basis** (`Earnings::History` or calendar).
   Show `difference` and percent. Revenue actual = quarterly `totalRevenue` for that period vs the
   consensus `revenueEstimateAvg` **captured before** the report. `Trend` updates in place, so without a
   pre-report capture the revenue surprise is unavailable.
2. Comparable quarter: YoY growth vs the same fiscal quarter last year from quarterly `Financials`.
   Margins and their changes in basis points.
3. Reaction: §10.1 step 3 for this event, plus the percentile of this |r| within the history.
4. Estimate changes: compare the pre-report and post-report Trend captures for `0y`/`+1y` (average and
   count).
5. Update model inputs (§10.3) and the thesis KPIs (§11).

**Chart list for the update** (each with as-of date, basis and source):
1. **EPS actual vs estimate**, last 8 quarters: paired bars of `epsActual` and `epsEstimate` from
   `Earnings::History`, with `surprisePercent` labels. One basis only. Quarters labelled by fiscal
   period-end, not report date.
2. **This reaction against history:** a strip or histogram of |r| for the previous reports (§10.1 step 3,
   n printed), with this event's |r| marked and its percentile in the caption.
3. **Consensus revision path** for `0y` and `+1y`: from your dated Trend captures. Without captures, one
   current capture still gives a 90-day path from `epsTrend90daysAgo`, `epsTrend60daysAgo`,
   `epsTrend30daysAgo`, `epsTrend7daysAgo` and `epsTrendCurrent`. Label that path "from one capture
   dated …" because older rows are overwritten in place.
4. **Revenue and margin YoY** for the same fiscal quarter, actual vs prior year (bars) with the margin
   change in bp.

**Acceptance check.** Quarterly statements arrive later than the calendar actual. Until the statement
row exists, revenue and margin cells show "pending statement", not zero. The EPS chart has exactly 8
quarters or prints the number available.

### 10.3 Model-update revision log

Append-only table, one row per changed assumption or captured input:

| Column | Example |
|---|---|
| `logged_at_utc` | 2026-10-31T07:10Z |
| `symbol`, `model_version` | XYZ.US, v14 |
| `item` | FY+1 revenue, WACC, share count, target-price input |
| `old_value`, `new_value`, `unit` | 412.0, 425.5, USD bn |
| `reason_class` | new fact, consensus change, model judgement, data restatement, error fix |
| `evidence` | endpoint + field path + capture id |
| `derived_effect` | per-share value 182 → 189 |

Rules:
- Refresh the share count from `outstandingShares` at each update.
- Recompute the per-share value and the upside vs the current price with that price's date.
- Never edit past rows. Corrections are new rows referencing the corrected one.

### 10.4 Daily morning note

| Block | EODHD source | Cost |
|---|---|---|
| Reports today and overnight | `calendar/earnings?from=D-1&to=D` filtered to the watchlist | 1 |
| Results already out | `calendar/earnings` actual vs estimate (same basis) | — |
| US pre-market / after-hours | `us-quote-delayed?s=…` (`ethPrice`, `ethVolume`, `ethTime`; delayed, US only) | 1 per symbol |
| Index and sector moves | EOD last day for indices and sector ETFs (or bulk last day, 100 per exchange) | 1 each |
| Macro calendar | `economic-events` for today. Times in UTC. `00:00:00` = "time not given". | see plans |
| News since last close | `news?s=SYM&from=` (5 per ticker) | 10+ |
| Dividends/splits today | `calendar/splits`, `div`/bulk dividends | 1–100 |

Every item carries its observation timestamp. When nothing qualifies, print "nothing material" rather than
padding. Delayed quotes are labelled delayed. Do not call EOD figures "live".

### 10.5 SEC filings (10-K, 10-Q, 8-K) in research workflows

**Use when:** a US issuer's research needs the as-filed annual or quarterly statements, a filing review,
or monitoring of material events (results, agreements, auditor changes, restatements, leadership changes,
regulatory and legal events) through 8-K items.

**EODHD inputs** ([api/endpoints/sec-filings-api.md](api/endpoints/sec-filings-api.md)):
- Overview `GET /api/sec-filings/{S}`: per form (`10k`, `10q`, `8k`, `form4`) a `count`, the `latest`
  filing date and a URL. Not paginated.
- Per form `GET /api/sec-filings/{S}/10k`, `/10q`, `/8k`: `page[limit]` (default 20, max 100) and
  `page[offset]`, follow `links.next`.
- **All-In-One only. 10 calls per request, overview included. JSON only.** 404 means an unknown symbol
  or no filings of that form.
- **History is short and varies by company:** in October 2026 the oldest 10-Q was 2015 for `AAPL.US`
  (35 10-Qs, 11 10-Ks), 2018 for `TSLA.US` and 2020 for `AMZN.US`. Read the overview `count` or `meta.total`
  before promising a long as-filed sample.
- 10-K/10-Q fields: `accession_number`, `filed_at`, `period_of_report`, `fiscal_year_end` (10-K) or
  `fiscal_quarter_end` and `fiscal_quarter` (10-Q), and a parsed statement set (`revenue`, `net_income`,
  `operating_cash_flow`, `capital_expenditure`, `free_cash_flow`, `eps_diluted`,
  `weighted_avg_shares_diluted`, `total_assets`, …). Any field can be `null`. Amounts are integers.
- 8-K fields: `accession_number`, `filed_at`, `period_of_report`, `items` (codes such as `"2.02"`),
  `item_sections` (`item`, `title`, `text`) and `exhibits` (`number`, `description`).
- Form 4 is a separate endpoint (`/sec-filings/{S}/form4`, [insider-transactions.md](api/endpoints/insider-transactions.md)).

**Method.**
1. **Overview first.** One overview request (10 calls) tells you which forms exist and when the latest
   was filed. Pull a per-form list only when its `latest` is newer than your stored value. That keeps a
   daily watchlist poll at 10 calls per symbol.
2. **Cross-check `Financials` against the filing.** Match `period_of_report` to the `Financials` period
   end and compare revenue, net income, CFO, capex and total assets with the §1.4 identities tolerance.
   Normalize signs first: in the filing schema `capital_expenditure`, `dividends_paid` and
   `share_repurchase` are negative (cash-flow sign), while `Financials` stores capex positive (§1.4). A
   difference is a finding to explain (restatement, template mapping, a different line definition), not
   an automatic error in either source.
3. **Availability date.** `filed_at` is the date the filing was public. Use it as the availability date
   for US periods instead of the §2.3 lag assumption. Whether the parsed values are as originally filed
   or later amended is not documented, so **verify with a probe** (compare an amended filing) before
   treating them as a point-in-time vintage.
4. **Quarter labels.** The reference describes `fiscal_quarter` as the calendar quarter 1–4. Derive the
   fiscal quarter from `fiscal_quarter_end` and `General.FiscalYearEnd` (§2.1). Whether 10-Q flows are
   standalone quarters or year-to-date is not documented, so run the §2.1 cumulative test. There is no
   Q4 10-Q: derive Q4 = 10-K − (Q1 + Q2 + Q3) under the §2.1 rules.
5. **8-K event monitor.** Deduplicate by `accession_number`. Map each item code to a declared review
   tier (SEC item numbering; the tiers are defaults, user-adjustable):

   | Tier | Items |
   |---|---|
   | High: review the same day | 1.03 bankruptcy or receivership; 1.05 material cybersecurity incident; 2.04 triggering events that accelerate an obligation; 2.06 material impairments; 3.01 delisting notice or failure to meet a listing rule; 4.01 change in certifying accountant; 4.02 non-reliance on previously issued financial statements |
   | Medium | 1.01 entry into, or 1.02 termination of, a material definitive agreement; 2.01 completion of an acquisition or disposition; 2.03 creation of a direct financial obligation; 2.05 exit or disposal costs; 3.02 unregistered equity sales; 3.03 material modification of security-holder rights; 5.01 change in control; 5.02 director or officer departure or appointment |
   | Information | 2.02 results of operations; 5.03 bylaw amendments; 5.07 shareholder vote results; 7.01 Regulation FD disclosure; 8.01 other events; 9.01 financial statements and exhibits |

   An alert row holds symbol, `filed_at`, items, tier, the section `title`, a short quoted excerpt of
   `text`, exhibit list and accession number. A summary generated from `text` is labelled as a summary
   and quotes the filing for any number it states.
6. **Regulatory and legal monitoring.** Combine the 8-K monitor with `news?s=` (and topic tags `t=`) for
   the same symbols. A news item without a matching filing stays "news, unconfirmed by filing".
7. **Filing review output:** filing list with dates, the cross-check table (step 2), event items since
   the last review, and the Form 4 summary (§9.3). Text sections other than the 8-K items (risk factors,
   MD&A) are not fields in this schema, so a request for them is user-supplied or out of scope.

**Pitfalls.** US SEC filers only. The reference lists 10-K, 10-Q, 8-K and Form 4 only, so issuers that
file other forms (for example foreign private issuers) may return 404 for these forms; verify with a
probe. The overview's `latest` is a filing date, not a period end. Polling the per-form endpoints
instead of the overview multiplies cost. An 8-K item 2.02 usually precedes the 10-Q by weeks, so
"results announced" and "statements filed" are separate states.

**Acceptance checks.** On the reference's 10-K example, `revenue` 391,035,000,000 − `cost_of_revenue`
210,352,000,000 = `gross_profit` 180,683,000,000, and `operating_cash_flow` 118,254,000,000 +
`capital_expenditure` (−9,447,000,000) = `free_cash_flow` 108,807,000,000. After sign normalization the
same capex is 9,447,000,000 as `capex_out`. An 8-K with items `["2.02","9.01"]` is tier Information;
one with `["4.02"]` is tier High. The same accession number fetched twice produces one alert.

---

### 10.6 SEC Company Analytics: filing-native fundamentals

**Use when** a US-focused tool needs statements, ratios, growth, TTM or revenue segments that trace back to
the company's own 10-K/10-Q, a CIK ↔ ticker directory, or a second view to check the standardized
Fundamentals feed. **EODHD inputs** ([reference](api/endpoints/sec-company-analytics.md)): All-In-One,
10 calls per request.

| Endpoint | Returns | Notes |
|---|---|---|
| `/api/sec-companies` | Directory: `cik`, `name`, `ticker`, `exchange`, `sic_code`, `state_of_incorporation`, `fiscal_year_end` (MMDD), `tickers[]` aliases with `is_primary` | ≈5,900 US filers; `page[limit]` 1–100, `page[offset]`; `links.next` |
| `/api/sec-companies/{SYM}/financials` | `annual[]` and `quarterly[]` rows keyed by `period` (10-K/10-Q field set) | history follows filings, back to 1994 |
| `/ratios` | margins, `roa`, `roe`, `ebitda_margin`, `current_ratio`, `quick_ratio`, `debt_to_equity`, `working_capital`, `tangible_book_value`, `net_debt`; newest first; `years=` | |
| `/growth` | YoY `revenue_growth`, `net_income_growth`, `operating_income_growth`, `total_assets_growth`, `eps_diluted_growth`, `operating_cash_flow_growth`, `free_cash_flow_growth`; `years=` | earliest period is null |
| `/ttm` | last four quarters for flows, latest value for balance-sheet items | |
| `/snapshot` | `latest_annual`, `ratios`, `growth`, `ttm` in one call | best value for profile pages |
| `/segments` | `axis` (`Geographic`, `ProductOrService`), `member`, `concept`, `value`, `unit`, `period_end`; `axis=` filter | only when the filer tags segments |

**Method.**
1. Resolve the company: directory → CIK and primary ticker; keep `tickers[]` aliases (share classes,
   renames) as identity evidence ([identity](identity.md)). Cache the directory (≈60 pages of 100).
2. Pull `snapshot` for a profile or screen row; `financials`/`ratios`/`growth` only for drill-down. A full
   directory screen is ≈5,900 × 10 = 59,000 calls — run it weekly, not per user request.
3. Read definitions before comparing: `debt_to_equity` here is **total liabilities / equity** (not
   interest-bearing debt), `net_debt` is total debt minus cash; banks and other financials have null current
   ratio, quick ratio and working capital; gross margin is null where gross profit is not reported.
4. Reconcile against Fundamentals (§1) when both exist: same fiscal period, same TTM cut-off. Report
   differences; do not overwrite one source with the other — this one is as-filed, Fundamentals is
   standardized and may restate.
5. Segments: sum members per `axis` and `period_end`; compare with total revenue and label the
   unallocated remainder. Members are as disclosed (country codes, product lines) and can change names
   between years.
6. Timing: values become knowable on the filing's `filed_at` (§10.5), not on `period`; apply that lag in any
   backtest ([temporal-research](temporal-research.md)).

```python
def reconcile(sec_ttm, fund_highlights, tol=0.02):
    """Compare SEC Company Analytics TTM revenue with Fundamentals Highlights.RevenueTTM.
    Differences beyond tol are reported, not 'fixed' (different period cut-offs and definitions)."""
    a, b = sec_ttm.get("revenue"), fund_highlights.get("RevenueTTM")
    if a in (None, 0) or b in (None, 0):
        return {"status": "not_comparable"}
    diff = abs(float(a) - float(b)) / abs(float(b))
    return {"status": "ok" if diff <= tol else "check", "rel_diff": round(diff, 4)}

def debt_to_equity_strict(fin_row):
    """SEC analytics `debt_to_equity` is total liabilities / equity; this is interest-bearing debt / equity."""
    debt = (fin_row.get("long_term_debt") or 0) + (fin_row.get("short_term_debt") or 0)
    eq = fin_row.get("stockholders_equity")
    return None if not eq or eq <= 0 else debt / eq
```

**Pitfalls.** US filers only (foreign issuers filing 20-F/40-F are not covered); null means the line item
was not reported, never zero; amended filings can change history (keep dated captures); the demo key covers
only `AAPL.US`, `TSLA.US`, `AMZN.US` for SEC data.

**Acceptance checks.** Identical TTM revenue in both sources → `ok`; a 3.9% gap → `check` with the
difference shown; a missing value → `not_comparable`. Debt 90bn + 10bn on equity 50bn → strict
debt/equity 2.0; negative equity → `None`, not a negative ratio. A bank row shows null liquidity ratios
without an error.

## 11. Thesis tracker and headline-to-scenario workflow

### 11.1 Thesis tracker

**Use when:** monitoring a written investment thesis against measurable evidence over time.

**EODHD inputs:** dated captures (recipe 39) of `Financials`, `Earnings::Trend`, `Highlights`,
`AnalystRatings`, `Holders`, EOD prices, `calendar/earnings` and news.

**Record structure.**

| Element | Content |
|---|---|
| Thesis | One paragraph plus 2–5 **pillars**, each a falsifiable claim |
| KPIs per pillar | Metric bound to an exact field and formula (e.g. "LTM gross margin from `Financials::Income_Statement::quarterly` ≥ 0.42"), with threshold, direction and the period it applies to |
| Catalysts | Dated events (next report from the calendar, user-supplied product or regulatory dates), each with an expected-direction note |
| Invalidation criteria | Explicit levels: KPI below threshold for k consecutive periods, a price below a level on a closing basis, net debt/EBITDA above X, a consensus `+1y` cut > Y% over 90 days |
| Review cadence | After each report capture, plus a calendar review (e.g. monthly) |
| Evidence log | Append-only: `date, source (endpoint + field + capture id), observation, pillar, effect (supports / weakens / neutral), action, conviction before → after` |
| Disconfirming evidence | Mandatory field per review. "None found" must state what was checked. |

**Method.**
1. On each new capture, recompute every KPI and classify each change as a **new fact** (new period), a
   **data restatement** (same period, changed value), a **valuation change** (price only) or a **wording
   change** (description or news only).
2. Pillar status = intact / weakened / broken by rule. Thesis status = broken if any invalidation criterion
   fires.
3. Alerts use hysteresis: fire on a crossing and re-arm only after the metric recovers past threshold ±
   buffer ([screening.md](screening.md#position-plans-and-alerts)).
4. Lifecycle: idea → active → under review → closed, with a post-mortem that compares the outcome with the
   original pillars.

**Pitfalls.** A restatement must not rewrite earlier log entries. Consensus revision history exists only
from your own captures.

**Acceptance checks.** Re-running the tracker on the same captures produces the identical log, so it is
deterministic. A restated quarter produces a `data restatement` entry, not a `new fact`.

### 11.2 Headline-to-scenario workflow

**Use when:** a user brings a news headline (a tariff, a rate decision, a regulation, a supply shock)
and wants base, bull and bear scenarios with sector effects and candidate beneficiaries and losers over
a stated horizon (for example 18 months).

**EODHD inputs:** the Screener (`sector`, `industry`) or local `General.Sector`/`Industry` for the
universe; `General.Description` and `Industry` for exposure evidence (Fundamentals, 10 calls per name);
EOD for sector ETFs (XLK, XLF, …, labelled proxies) and indices; `economic-events` for dated macro
analogs; `news?s=`/`news?t=` for the current story. Segment revenue, geographic revenue split, supplier
lists and policy details are **user-supplied** (§15).

**Method.**
1. **Parse the headline** into: event type, date, region, the directly affected industries and the
   transmission channel (prices, volumes, costs, rates, FX). This mapping is judgement and is labelled
   as such.
2. **Analog windows.** Collect past dated events of the same type, user-listed or from
   `economic-events`. For each analog and each affected sector ETF compute the return relative to the
   broad index over [−1, +5], [0, +20] and [0, +60] sessions (adjusted closes, sessions from the exchange
   calendar). Report n, median, interquartile range and the share of negative outcomes per window. With
   n < 5, print the individual analogs instead of statistics.
3. **Candidate tickers.** Filter the universe by affected industries. Exposure evidence per name:
   industry membership, keyword evidence quoted from `General.Description`, and user-supplied segment or
   geographic data. Each candidate carries the evidence type; "industry member only" is the weakest.
4. **Scenarios.** Base, bull and bear, each with: stated assumptions, first-order effects (directly
   affected industries), second-order effects (their customers and suppliers), third-order effects
   (macro, rates, FX), the analog statistics that support or contradict it, and signposts that would
   show which scenario is unfolding. Probabilities, if given, are labelled **judgement** and sum to 1.
5. **Reviewer pass** before release: every claim tagged `observation`, `calculation` or `judgement`;
   every analog statistic shows n and window; no causal language from analog co-movement (association,
   not causation: [methods-quant-research.md](methods-quant-research.md) §8); the horizon is stated;
   the output says it is a scenario analysis, not a forecast or a recommendation.

**Pitfalls.** Analogs are few and confounded by other news in the same window. Current sector
membership is applied to old analogs (look-ahead). Sector ETFs are proxies with their own weights. A
company's description can mention a market it barely sells into.

**Acceptance checks.** Five analog relative returns (−0.04, 0.01, −0.06, −0.02, 0.03) give median −0.02
and a negative share of 0.6, printed with n = 5. Scenario probabilities (0.5, 0.3, 0.2) pass; (0.5, 0.3,
0.3) fail. A claim with no tag fails the reviewer pass.

---

## 12. Equity research reports: quality gates, initiation staging and rating rule

### 12.1 Quality gates

**Use when:** producing a single-stock report (initiation, update, one-pager) that must be honest about
evidence.

**Method.**
1. **One data bundle.** Fetch once (§1.2), store it with retrieval times, and make every section read
   from the bundle. No section re-fetches with different timing.
2. **Evidence per number.** Each figure in the text, tables and charts maps to an evidence record (§0) or
   to a calculation id whose inputs are evidence records. Unsupported numbers are removed.
3. **Critic pass** (run as a separate review step before release):
   - [ ] Units: GBX/ZAC normalized, statement scale (units vs millions; `sharesMln` vs `shares`),
     decimal vs percent.
   - [ ] Currency: statement vs listing currency, FX date shown.
   - [ ] Staleness: quote date, `MostRecentQuarter`, Trend capture date, and holder `date` all printed.
     Flag anything older than its policy (e.g. a price older than 3 sessions).
   - [ ] Cross-endpoint conflicts: own EV vs `Valuation.EnterpriseValue`, own ROE vs
     `ReturnOnEquityTTM`, own TTM revenue vs `RevenueTTM`. Show reconciled values or a range with both
     sources.
   - [ ] Ratio basis: average vs ending equity, LTM vs FY, GAAP vs adjusted EPS, stated once per table.
   - [ ] NM handling: no negative P/E in statistics, no 0 for unavailable.
   - [ ] Targets and fair values trace to a model (§5–§8) with a sensitivity range. No unsupported target.
   - [ ] Conclusions do not exceed the evidence: no causal claims from insider filings or news timing, no
     certainty language.
   - [ ] Every requested source that was not retrieved is listed (see step 4).
4. **Declaration block at the top** listing requested but unretrieved sources. Examples: "management
   guidance: not provided", "transcript: not available from EODHD", "segment data: user did not supply",
   "options-implied move: non-US listing, not available".
5. **Status:**
   - `complete`: all gates pass.
   - `partial`: some sections degraded and labelled in place, with failed checks listed.
   - `blocked`: a core input is missing (no statements, or price/statement currency unresolvable), so
     only a data-status note is issued.
   Failed checks stay in the appendix. They are never deleted to reach `complete`.

**Acceptance checks.** Remove `Financials` from a test bundle: the report status becomes `blocked`. Remove
only `Holders`: status `partial` with the ownership section labelled. Seed a GBX price without
normalization: the critic pass fails on units.

### 12.2 Initiating coverage: staged sequence and rating rule

**Use when:** producing an initiation-of-coverage report, which is too large to build in one pass.

**EODHD inputs:** the §1.2 bundle (Fundamentals 10 calls, EOD, `div`, `calendar/earnings`,
`calendar/trends`), peers per §8.1, news, and SEC filings for US issuers (§10.5, All-In-One).

**Method.** Run the stages in order. Each stage writes a dated artifact, and the next stage starts only
after its input check passes. A failed check stops the downstream stages or degrades them to `partial`
with the reason (§12.1 step 5).

| Stage | Output | Input check before the stage starts |
|---|---|---|
| 1. Company research | profile, business description, history, management (user-supplied), ownership, news, filings list | symbol resolved (`General.Type`, primary listing, currency); bundle stored with retrieval times |
| 2. Financial model | historical statements, TTM, ratios, 3-statement projection ([valuation.md](valuation.md)) | statement identities (§1.4) pass or are explained; period typing (§2.1) done; statement and listing currency resolved |
| 3. Valuation | DCF with grid (§5), comps with implied range (§8.4), other methods, football field | model balances and cash ties; WACC inputs dated (§4); peer n ≥ 5 or the widening is recorded |
| 4. Chart pack | §8.6 charts plus the §10.2 earnings charts where relevant | every chart source is a stage-2 or stage-3 artifact; as-of dates and units present |
| 5. Report | thesis, valuation summary, risks, rating, data notes | §12.1 critic pass; the price target traces to stage 3 |

**Rating rule.** Upside u = PT / P − 1, with the price P and its date from the bundle and the price
target PT from stage 3 (state the method weights if PT blends methods). The bands and their names are
**supplied by the user** (for example: u ≥ θ_high → top band; u ≤ θ_low → bottom band; otherwise middle
band). Without user thresholds, report u and leave the rating blank. Optionally require u to cross the
threshold by a buffer before a rating changes (hysteresis). The rating is the output of a declared rule,
not investment advice; print the rule next to it.

**Pitfalls.** A target built in stage 3 on one share count and a price from a different date. Re-running
stage 2 after stage 3 without re-running stage 3. Ratings without a printed rule.

**Acceptance checks.** PT 120, P 100, thresholds (θ_low, θ_high) = (−0.10, +0.15) → u = 0.20 → top
band. The same with no thresholds → u = 0.20 and the rating blank. Removing the stage-2 identity check
result blocks stage 3.

---

## 13. M&A: listed strategic-buyer screen, merger maths, LBO returns and IC packs

### 13.1 Listed strategic-buyer screen

**Use when:** generating a list of **listed** companies that could plausibly acquire a target. Listed
acquirers can be screened from EODHD data. Private buyers, sponsors, M&A track records, strategic intent
and deal terms are **user-supplied**.

**EODHD inputs:** the Screener (`sector`, `industry` match, `exchange`, `market_capitalization`) or local
`General` classification, plus Fundamentals for each candidate (10 calls each). The target's EV comes from
§7 (listed target) or is user-supplied (private target).

**Method.**
1. Universe: same industry plus user-listed adjacent industries, with the exchanges/countries in scope.
2. Size gate: candidate MC ≥ k × target EV (default k = 3, user-set), in one currency.
3. Capacity metrics per candidate:
   - cash = `cashAndShortTermInvestments`;
   - current net debt/EBITDA;
   - **pro-forma leverage if all-debt funded** = (ND_A + EV_T) / (EBITDA_A + EBITDA_T). Equity purchase
     price + target net debt = EV_T, and synergies are excluded;
   - **stock capacity** = equity purchase price / acquirer MC (dilution proxy).
4. Tiering, for example:
   - Tier 1: PF leverage ≤ user limit (e.g. 3.0×) and cash ≥ 50% of price.
   - Tier 2: PF leverage ≤ limit + 1.0× or stock capacity ≤ 20%.
   - Tier 3: the rest that passed the size gate.
5. Output: ranked list with every metric, the tier rule, data dates, exclusions, and a "user-supplied"
   column for strategic-fit notes.

**Acceptance check.** Acquirer ND 2,000, EBITDA 1,000, target EV 3,000, EBITDA 300 → PF leverage 3.85×.

### 13.2 Merger accretion/dilution

**Method.**
- New shares = stock consideration / acquirer share price.
- Pro-forma net income = NI_A + NI_T + synergies(1 − t) − foregone interest on cash used × (1 − t)
  − interest on new debt × (1 − t) − incremental amortization of acquired intangibles × (1 − t).
- PF EPS = PF NI / (S_A + new shares). Accretion = PF EPS / EPS_A − 1.
- **Breakeven pre-tax synergies** = [EPS_A × (S_A + new shares) − PF NI ex-synergies] / (1 − t).
- Grids: offer premium × synergies, and cash/stock mix × premium.

Inputs: NI and EPS (`Earnings::Trend` FY+1 or LTM from statements, stating GAAP vs adjusted), shares
(`outstandingShares`), and prices from EOD. Offer premium = offer / unaffected price − 1, where the
unaffected price is the close before the first public report (date user-supplied) or an N-day average,
labelled.

**Acceptance check.** All-stock, no premium, zero synergies, equal P/E (A: NI 100, 100 shares, price 20;
T: NI 50, bought for 1,000 = 20× NI) → 50 new shares, PF EPS 150/150 = 1.00, accretion 0.

### 13.3 Merger-arbitrage spread and deal milestones

- Cash deal gross spread = Offer / P − 1. Annualized = (1 + spread)^(365/days) − 1, where days = expected
  close (user-supplied) − today. Include dividends expected before close.
- Stock deal: offer value = ratio × P_acquirer on the same timestamp.
- **Implied completion probability** = (P − P_down) / (Offer − P_down), where P_down is the user-supplied
  fall-back price (e.g. the unaffected price adjusted for market moves). It is a model, not a forecast.
- **Deal milestone tracker.** States: `announced` → `filings` → `shareholder vote` → `regulatory
  approvals` → `closed`, with `terminated` reachable from any state. Each transition stores its date and
  evidence. For US parties the 8-K items in §10.5 are the evidence: 1.01 (definitive agreement), 5.07
  (vote results), 2.01 (completion), 1.02 (termination). Other states (antitrust decisions, foreign
  approvals) are user-supplied or news items labelled "unconfirmed by filing". Recompute the spread and
  the implied probability at each transition with that day's prices.

### 13.4 LBO mechanics, returns attribution and sensitivity grids

**Method.**
- Entry EV = EBITDA_0 × m_0 (or take-private price = (1 + premium) × unaffected price × diluted shares +
  net debt).
- Sources = uses. Uses: equity purchase price, refinanced net debt, fees. Sources: debt tranches, sponsor
  equity. Check that the difference is 0.
- Each year:
  - interest on average balances (circular; use iteration with a switch, or opening balances, and state
    which);
  - mandatory amortization;
  - **cash sweep** = min(cash available after mandatory service and minimum cash, tranche balance),
    applied by seniority.
- Exit equity = EBITDA_N × m_N − ND_N. MOIC = total equity proceeds / equity invested. IRR on dated cash
  flows (XIRR), including interim dividends or recaps.
- **Returns attribution**, which sums exactly to the equity gain:
  - EBITDA growth = (EBITDA_N − EBITDA_0) × m_0
  - Multiple change = (m_N − m_0) × EBITDA_N
  - Deleveraging = ND_0 − ND_N (including cash build)
  - Fees and costs = −fees (if they were funded with equity)
  - Interim distributions are added separately.

  The cross term (ΔEBITDA × Δm) is assigned to the multiple here. The alternative ordering (growth at m_N,
  multiple on EBITDA_0) or a symmetric split (growth = ΔE × (m_0 + m_N)/2, multiple = Δm × (E_0 + E_N)/2)
  is equally valid. State which one you used.

Listed-peer EV/EBITDA from §8 gives entry and exit context, labelled as current trading multiples, not
transaction multiples. Debt terms, fees and covenants are user-supplied.

**Acceptance check.** EBITDA 100 → 150, multiple 8 → 9, ND 500 → 300, fees 20: equity 320 → 1,050, gain
730 = 400 + 150 + 200 − 20. MOIC 3.28×, 5-year IRR 26.8%.

**Two-way IRR and MOIC sensitivity grids.**
- Standard pairs: entry multiple × exit multiple; leverage (entry debt / EBITDA) × exit multiple; EBITDA
  growth × hold period. Show IRR and MOIC grids for each pair.
- Every cell is a **full recompute** of the model (sources and uses, debt schedule, sweep, exit), never
  an interpolation. Changing the entry multiple changes the equity cheque and the fees, so both move.
- The centre cell equals the base case exactly. Fees are an explicit input (percent of EV or an
  amount), never buried in the multiple.
- Mark cells where a constraint fails (leverage above the user's limit, negative equity, a covenant
  breach if covenants are supplied) instead of printing a number.
- Listed-peer multiples (§8) give the context lines on the exit-multiple axis, labelled as current
  trading multiples.

```python
def lbo(ebitda0, m_entry, m_exit, lev, years, g, conv=0.5, r=0.08, tax=0.25, fee_pct=0.02):
    """Annual LBO with a 100% cash sweep. lev = entry debt / EBITDA0; conv = unlevered FCF / EBITDA
    (after tax and capex, before interest); interest on opening debt (no circularity); fees funded by
    equity. Returns sponsor equity in/out, MOIC and IRR (single entry and exit cash flow)."""
    ev0 = ebitda0 * m_entry
    debt, cash, e = lev * ebitda0, 0.0, ebitda0
    eq_in = ev0 - debt + fee_pct * ev0                   # sources = uses: debt + equity = EV + fees
    for _ in range(years):
        e *= 1 + g
        fcf = conv * e - r * (1 - tax) * debt             # levered FCF after after-tax interest
        pay = min(max(fcf, 0.0), debt)
        debt -= pay
        cash += fcf - pay                                 # surplus (or shortfall) after the sweep
    eq_out = m_exit * e - debt + cash
    moic = eq_out / eq_in
    irr = moic ** (1 / years) - 1 if moic > 0 else None
    return {"eq_in": eq_in, "eq_out": eq_out, "moic": moic, "irr": irr}

def grid(base, row_key, row_vals, col_key, col_vals, out="irr"):
    """Two-way grid; every cell is a full recompute of lbo(); returns rows of values."""
    return [[lbo(**{**base, row_key: rv, col_key: cv})[out] for cv in col_vals] for rv in row_vals]
```

With interim dividends or recaps, replace the single-flow IRR with XIRR on dated flows
([methods-performance-risk.md](methods-performance-risk.md) §5.3).

**Grid acceptance checks** (base: EBITDA 100, entry and exit 10×, leverage 5×, 5 years, growth 5%,
conversion 0.5, rate 8%, tax 25%, fees 2%):
- base equity in 520.0, equity out 932.37, MOIC 1.793×, IRR 12.39%;
- entry × exit IRR rows (entry 9, 10, 11; exit 9, 10, 11): (14.00%, 17.40%, 20.46%), (9.13%, 12.39%,
  15.31%), (5.29%, 8.43%, 11.25%); MOIC for entry 10× across exit 9, 10, 11: (1.55×, 1.79×, 2.04×);
- leverage 4, 5, 6 at exit 10×: IRR 11.45%, 12.39%, 13.71%;
- growth 0%, 5%, 10% at 5 years: IRR 3.34%, 12.39%, 20.40%;
- the centre cell of every grid equals the base case exactly; with fees 0 the base IRR rises to 13.27%.

### 13.5 IC memo: section template, data pack and ties

**Use when:** drafting a private-equity investment-committee memo and its supporting workbook.

**Section template** (source column: E = EODHD data or a calculation on it; U = user-supplied; C =
calculation on U and E):

| # | Section | Content | Source |
|---|---|---|---|
| 1 | Overview and recommendation summary | target, deal size, ask, one-paragraph thesis | U, C |
| 2 | Company | business model, history, management, customers | U |
| 3 | Industry and public peers | listed peers (§8.1), trading multiples (§8.2, dated), sector valuation history (§8.5), industry aggregates (§8.8), macro backdrop (§8.6) | E |
| 4 | Historical financials | normalized IS, BS, CF and KPIs from the CIM or accounts; EBITDA adjustments | U, C |
| 5 | Investment thesis | 3–5 pillars, each with evidence and a test (§11.1 format) | U, C |
| 6 | Deal terms | price, structure, sources and uses, debt terms, fees, governance | U |
| 7 | Returns | base, upside, downside cases; IRR and MOIC; attribution (§13.4); sensitivity grids | C |
| 8 | Risks and mitigants | key risks, diligence findings, open questions | U |
| 9 | Recommendation and conditions | decision asked for, conditions precedent, next steps | U |
| 10 | Appendix and data notes | evidence log, data dates, public-peer methodology, boundaries | E, C |

Every number in sections 3 and 7 traces to the evidence record (§0). Sections marked U state the
document they came from.

**Data-pack workbook tab set:**

| Tab | Content |
|---|---|
| Cover / notes | deal name, version, as-of dates, units and currency, colour legend (input vs formula), change log |
| IS, BS, CF | normalized historical statements by period, with the source of each line (CIM page, accounts) |
| KPIs | operating metrics from the supplied material, with definitions |
| EBITDA adjustments | reported → adjusted bridge, one row per adjustment with direction and evidence, in a **conservative** and an **aggressive** column |
| Public comps | §8.2 table from EODHD with prices dated and the §8.7 metric definitions |
| Returns | model output and the §13.4 grids |
| Sources | every source document and EODHD request (endpoint, symbol, date, no token) |

Formatting and formula rules follow [reports.md](reports.md#workbooks) and the §14 audit checklist.

**Ties that must hold before release:**
- sources = uses;
- the EBITDA bridge reconciles base to forecast, and the adjustments tab ties to the IS;
- the returns table equals the model output, and every grid centre equals the base case;
- the attribution sums to the equity gain;
- comps and multiples carry dates;
- private inputs are labelled user-supplied.

---

## 14. Spreadsheet and model audit checklist

**Use when:** reviewing a user's model or a generated workbook. Workbook construction rules are in
[reports.md](reports.md#workbooks) and [valuation.md](valuation.md#validation).

| Area | Check |
|---|---|
| Errors | No `#REF!`, `#DIV/0!`, `#VALUE!`, `#N/A` (or each one is intentional and labelled) |
| Hard-codes | No constants inside formulas (`=B5*1.05`). Assumptions live in input cells. |
| Pattern breaks | A row whose formula differs from its neighbours. Off-by-one SUM ranges. Pasted values over formulas. |
| Units and scale | Thousands vs millions vs units consistent. `sharesMln` vs `shares`. Percent vs decimal. GBX vs GBP. |
| Hidden content | Hidden sheets, rows or columns. Very hidden sheets. External links. |
| Statement ties | CFO + CFI + CFF (+ FX) = Δcash. Balance sheet balances each period (report the gap per period). Retained earnings roll-forward = RE_prev + NI − dividends ± other. PP&E roll-forward = prev + capex − D&A − disposals. Debt roll-forward. |
| Tax | Tax = pre-tax × rate (± deferred-tax allowance). Rate within a plausible range. |
| Circularity | Interest on average debt is circular: needs an iteration switch, or opening balances by design |
| DCF | TV discounted at the right exponent (§5). WACC > g. Mid-year flag consistent. Grid centre = base. FCFF not after interest. |
| Bridge and shares | Same diluted share count for the market cap and the per-share value. Net debt sign. Minorities and preferred handled once. |
| Credit metrics | Debt/EBITDA, net debt/EBITDA, interest coverage, FCF/debt computed on the declared definitions |
| Source trace | Every historical cell maps to an EODHD field path and capture (§1.3 names). Sign normalization documented (§1.4). |
| Normalizations | EBITDA adjustments (one-offs, SBC, leases) listed with direction. Conservative and aggressive cases shown separately. |
| Format | Currency vs counts vs percent formats distinct. Years as labels, not numbers. Negatives in parentheses if that is the house style. |
| Recalculation | Recalculated in a real spreadsheet engine. openpyxl alone does not evaluate formulas, so say so if no engine is available. |

Deliver a **severity-ranked findings list**:
- critical: wrong value or broken tie;
- major: wrong method or units;
- minor: hard-code or format.

Each finding names the cell or range, the evidence, the expected vs actual value, and a fix. For slide
decks, the cross-slide consistency check in [reports.md](reports.md#deck-refresh-and-qc) produces
findings in the same three severity classes: a number that conflicts across slides or fails a recomputed
total is critical; a wrong period label or unit is major; a precision or format variant is minor.

---

## 15. Boundaries: what EODHD does not supply

State these when a task depends on them, and do not substitute another data source:

- Earnings-call transcripts, management guidance, segment and KPI disclosures, market share/TAM, and
  private-company financials. These are user-supplied.
- Broker consensus beyond `Earnings::Trend`/`calendar/trends` (one fiscal year ahead; no FY+2; no
  per-broker detail; no as-of history except your captures).
- Point-in-time fundamentals, classification history and historical float. These come only from your own
  archive.
- Equity risk premium, statutory tax rates, credit spreads for specific issuers, and lease and pension
  adjustments. These are user-supplied or labelled proxies.
- M&A transaction databases, deal terms, sponsor lists and buyer track records. These are user-supplied.
  Listed acquirers **can** be screened (§13.1).
- Private funding rounds and venture deal databases. For a capital-markets digest, the feasible EODHD
  subset is the IPO calendar (`calendar/ipos`: filed, expected, amended and priced listings by exchange,
  §9.4) plus sector or topic news (`news?t=`), with the private-round section marked user-supplied.
- IPO lockup terms (only a labelled estimate, §9.4), borrow availability and borrow fees (§9.3).
- SEC filing text beyond 8-K item sections (risk factors, MD&A, notes) and non-US regulatory filings.
  The SEC filings API gives parsed 10-K/10-Q statements and 8-K items for US filers on All-In-One
  (§10.5).
- Filer-level 13F portfolios. `Holders` is a current top-holder snapshot. Filings carry a reporting lag,
  so holder dates trail the market.
- Options-implied moves outside US stocks and ETFs, and for indices (no index options). The Marketplace
  options product is separate from every core plan.
- REIT FFO/AFFO as reported. Only the §3.10 approximation is possible.
