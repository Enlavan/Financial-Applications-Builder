> Public documentation snapshot, 2026-10-25. Read [the integration contract](../../api-contract.md) and [plans and limits](../../plans-limits.md).
> In plans (docs): All-In-One plan. Cost: Each request consumes 10 API calls.

# SEC Company Analytics API | EODHD APIs Documentation

Source: https://eodhd.com/financial-apis/sec-company-analytics-api

 

The SEC Company Analytics API turns raw SEC EDGAR filings into ready-to-use company financials and metrics: full annual and quarterly statements, financial ratios, growth rates, trailing-twelve-month aggregates, a one-call snapshot, and revenue segments — plus a directory of covered companies. Everything is computed from the same parsed 10-K and 10-Q filings that power the [SEC Filings API](https://eodhd.com/financial-apis/sec-filings-api), so the numbers trace straight back to the source documents. If you are looking for standardized, multi-source company fundamentals, see the [Fundamentals API](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds); this endpoint is the SEC-EDGAR-native view of the same kind of data.

You can try these endpoints without an account using the demo API token (api\_token=demo). For SEC data the demo token is limited to three tickers: **AAPL.US**, **TSLA.US**, and **AMZN.US**.

## Coverage

Analytics cover roughly **5,900 US-listed companies** that file with SEC EDGAR, refreshed daily as new filings are parsed. Financial history follows the underlying filings, reaching back to 1994\. Every metric is derived from a company’s own 10-K and 10-Q filings — there is no third-party estimate or vendor blend.

## API Endpoints

| Method | Endpoint                               | Returns                                         |
| ------ | -------------------------------------- | ----------------------------------------------- |
| GET    | /api/sec-companies                     | Directory of covered companies (paginated)      |
| GET    | /api/sec-companies/{symbol}/financials | Annual and quarterly financial statements       |
| GET    | /api/sec-companies/{symbol}/ratios     | Financial ratios per period                     |
| GET    | /api/sec-companies/{symbol}/growth     | Year-over-year growth rates per period          |
| GET    | /api/sec-companies/{symbol}/ttm        | Trailing-twelve-month aggregates                |
| GET    | /api/sec-companies/{symbol}/snapshot   | Combined latest annual, ratios, growth, and TTM |
| GET    | /api/sec-companies/{symbol}/segments   | Revenue by business segment                     |

## Path Parameter

`symbol` string  required 

US-listed ticker, for example AAPL.US. The .US suffix is optional. Not used by the directory endpoint. 

## Query Parameters

`api_token` string  required 

Your EODHD API token 

`page[offset]` integer  optional 

Rows to skip, for pagination. Directory endpoint only. _(Default: 0)_ 

`page[limit]` integer  optional 

Rows per page. Directory endpoint only. _(Default: 20, Range: 1-100)_ 

`years` integer  optional 

Limit the number of periods returned. Applies to the ratios and growth endpoints. 

`axis` enum  optional 

Filter revenue segments by dimension. Applies to the segments endpoint. Allowed values: Geographic, ProductOrService. 

## Response Envelope

Every response is a JSON object with data, meta, and links. The directory endpoint returns data as an array with pagination in meta and links. The per-company endpoints return data as an object that always includes a company block (cik, name, ticker, exchange) alongside the requested payload.

## Company Directory

GET /api/sec-companies returns a paginated list of every company covered, with its SEC identifiers and ticker aliases. Useful for discovery and for mapping a CIK to its tickers.

#### Request Example

 

 

```
https://eodhd.com/api/sec-companies?api_token=YOUR_API_TOKEN
```
```
curl --location "https://eodhd.com/api/sec-companies?api_token=YOUR_API_TOKEN&fmt=json"
```
#### Response Example

```json
{
  "data": [
    {
      "cik": "0001084869",
      "name": "1-800-FLOWERS.COM, Inc.",
      "ticker": "FLWS",
      "exchange": "US",
      "sic_code": "5990",
      "state_of_incorporation": "DE",
      "fiscal_year_end": "0630",
      "tickers": [ { "ticker": "FLWS", "exchange": "US", "is_primary": true } ]
    }
  ],
  "meta": { "total": 5939, "page": { "offset": 0, "limit": 20 } },
  "links": { "next": "https://eodhd.com/api/sec-companies?page[offset]=20&page[limit]=20" }
}

```

#### Response Fields

| Field                    | Type   | Description                                                                 |
| ------------------------ | ------ | --------------------------------------------------------------------------- |
| cik                      | string | SEC Central Index Key, zero-padded                                          |
| name                     | string | Company name                                                                |
| ticker                   | string | Primary ticker                                                              |
| exchange                 | string | Exchange code, US for US listings                                           |
| sic\_code                | string | SEC Standard Industrial Classification code                                 |
| state\_of\_incorporation | string | State or country of incorporation                                           |
| fiscal\_year\_end        | string | Fiscal year end as MMDD, for example 0630                                   |
| tickers                  | array  | All ticker aliases for the CIK, each with ticker, exchange, and is\_primary |

## Financials

GET /api/sec-companies/{symbol}/financials returns the full annual and quarterly statement history for a company. Each row carries the same financial fields as the [SEC Filings API](https://eodhd.com/financial-apis/sec-filings-api) 10-K and 10-Q endpoints (revenue, income, EPS, balance sheet, and cash flow), keyed by reporting period.

#### Request Example

 

 

```
https://eodhd.com/api/sec-companies/AAPL.US/financials?api_token=YOUR_API_TOKEN
```
```
curl --location "https://eodhd.com/api/sec-companies/AAPL.US/financials?api_token=YOUR_API_TOKEN&fmt=json"
```
#### Response Example

```json
{
  "data": {
    "company": { "cik": "0000320193", "name": "Apple Inc.", "ticker": "AAPL", "exchange": "US" },
    "annual": [
      { "period": "2025-09-27", "revenue": 416161000000, "net_income": 112010000000, "eps_diluted": 7.46, "free_cash_flow": 98767000000 }
    ],
    "quarterly": [
      { "period": "2026-03-28", "revenue": 254940000000, "net_income": 71675000000, "eps_diluted": 4.85 }
    ]
  }
}

```

#### Response Fields

| Field     | Type   | Description                                                                                       |
| --------- | ------ | ------------------------------------------------------------------------------------------------- |
| company   | object | Company identifiers (cik, name, ticker, exchange)                                                 |
| annual    | array  | Annual statements, newest first. Each row uses the SEC Filings 10-K field set, keyed by period    |
| quarterly | array  | Quarterly statements, newest first. Each row uses the SEC Filings 10-Q field set, keyed by period |

## Ratios

GET /api/sec-companies/{symbol}/ratios returns financial ratios computed per reporting period, newest first. Use the years parameter to limit how many periods are returned.

#### Request Example

 

 

```
https://eodhd.com/api/sec-companies/AAPL.US/ratios?api_token=YOUR_API_TOKEN
```
```
curl --location "https://eodhd.com/api/sec-companies/AAPL.US/ratios?api_token=YOUR_API_TOKEN&fmt=json"
```
#### Response Example

```json
{
  "data": {
    "company": { "cik": "0000320193", "name": "Apple Inc.", "ticker": "AAPL", "exchange": "US" },
    "ratios": [
      {
        "period": "2025-09-27",
        "gross_margin": 0.4691, "operating_margin": 0.3197, "net_margin": 0.2692,
        "roa": 0.3118, "roe": 1.5191, "ebitda_margin": 0.3478,
        "current_ratio": 0.8933, "quick_ratio": 0.8588, "debt_to_equity": 3.8722,
        "working_capital": -17674000000, "tangible_book_value": 73733000000, "net_debt": 42394000000
      }
    ]
  }
}

```

#### Response Fields

| Field                 | Type            | Description                                   |
| --------------------- | --------------- | --------------------------------------------- |
| period                | string          | Reporting period end date, YYYY-MM-DD         |
| gross\_margin         | number or null  | Gross profit divided by revenue               |
| operating\_margin     | number or null  | Operating income divided by revenue           |
| net\_margin           | number or null  | Net income divided by revenue                 |
| roa                   | number or null  | Return on assets                              |
| roe                   | number or null  | Return on equity                              |
| ebitda\_margin        | number or null  | EBITDA divided by revenue                     |
| current\_ratio        | number or null  | Current assets divided by current liabilities |
| quick\_ratio          | number or null  | Quick assets divided by current liabilities   |
| debt\_to\_equity      | number or null  | Total liabilities divided by equity           |
| working\_capital      | integer or null | Current assets minus current liabilities      |
| tangible\_book\_value | integer or null | Equity minus goodwill and intangibles         |
| net\_debt             | integer or null | Total debt minus cash and equivalents         |

## Growth

GET /api/sec-companies/{symbol}/growth returns year-over-year growth rates per period, newest first. A period needs a prior-year comparison to produce values, so the earliest year in a company’s history returns nulls. The years parameter limits the number of periods.

#### Request Example

 

 

```
https://eodhd.com/api/sec-companies/AAPL.US/growth?api_token=YOUR_API_TOKEN
```
```
curl --location "https://eodhd.com/api/sec-companies/AAPL.US/growth?api_token=YOUR_API_TOKEN&fmt=json"
```
#### Response Fields

| Field                         | Type           | Description                               |
| ----------------------------- | -------------- | ----------------------------------------- |
| period                        | string         | Reporting period end date, YYYY-MM-DD     |
| revenue\_growth               | number or null | Year-over-year revenue growth             |
| net\_income\_growth           | number or null | Year-over-year net income growth          |
| operating\_income\_growth     | number or null | Year-over-year operating income growth    |
| total\_assets\_growth         | number or null | Year-over-year total assets growth        |
| eps\_diluted\_growth          | number or null | Year-over-year diluted EPS growth         |
| operating\_cash\_flow\_growth | number or null | Year-over-year operating cash flow growth |
| free\_cash\_flow\_growth      | number or null | Year-over-year free cash flow growth      |

## Trailing Twelve Months

GET /api/sec-companies/{symbol}/ttm returns a single object of trailing-twelve-month aggregates, summing the last four quarters for flow items and taking the latest value for balance-sheet items.

#### Request Example

 

 

```
https://eodhd.com/api/sec-companies/AAPL.US/ttm?api_token=YOUR_API_TOKEN
```
```
curl --location "https://eodhd.com/api/sec-companies/AAPL.US/ttm?api_token=YOUR_API_TOKEN&fmt=json"
```
#### Response Fields

TTM fields

| Field                       | Type            | Description                                         |
| --------------------------- | --------------- | --------------------------------------------------- |
| revenue                     | integer or null | Trailing-twelve-month revenue                       |
| net\_income                 | integer or null | Trailing-twelve-month net income                    |
| operating\_income           | integer or null | Trailing-twelve-month operating income              |
| cost\_of\_revenue           | integer or null | Trailing-twelve-month cost of revenue               |
| gross\_profit               | integer or null | Trailing-twelve-month gross profit                  |
| operating\_cash\_flow       | integer or null | Trailing-twelve-month operating cash flow           |
| free\_cash\_flow            | integer or null | Trailing-twelve-month free cash flow                |
| capital\_expenditure        | integer or null | Trailing-twelve-month capital expenditure           |
| interest\_expense           | integer or null | Trailing-twelve-month interest expense              |
| income\_tax\_expense        | integer or null | Trailing-twelve-month income tax expense            |
| depreciation\_amortization  | integer or null | Trailing-twelve-month depreciation and amortization |
| dividends\_paid             | integer or null | Trailing-twelve-month dividends paid                |
| share\_repurchase           | integer or null | Trailing-twelve-month share repurchases             |
| total\_assets               | integer or null | Latest total assets                                 |
| total\_liabilities          | integer or null | Latest total liabilities                            |
| stockholders\_equity        | integer or null | Latest stockholders equity                          |
| total\_current\_assets      | integer or null | Latest total current assets                         |
| total\_current\_liabilities | integer or null | Latest total current liabilities                    |
| cash\_and\_equivalents      | integer or null | Latest cash and equivalents                         |
| long\_term\_debt            | integer or null | Latest long-term debt                               |
| total\_equity               | integer or null | Latest total equity                                 |
| accounts\_receivable        | integer or null | Latest accounts receivable                          |
| inventory                   | integer or null | Latest inventory                                    |
| goodwill                    | integer or null | Latest goodwill                                     |

## Snapshot

GET /api/sec-companies/{symbol}/snapshot bundles the most useful views into one call: the latest annual statement, the latest ratios and growth, and the TTM aggregates. Ideal for a company profile page where you want everything in a single request.

#### Request Example

 

 

```
https://eodhd.com/api/sec-companies/AAPL.US/snapshot?api_token=YOUR_API_TOKEN
```
```
curl --location "https://eodhd.com/api/sec-companies/AAPL.US/snapshot?api_token=YOUR_API_TOKEN&fmt=json"
```
#### Response Fields

| Field          | Type   | Description                                                   |
| -------------- | ------ | ------------------------------------------------------------- |
| company        | object | Company identifiers                                           |
| latest\_annual | object | Most recent annual statement (SEC Filings 10-K field set)     |
| ratios         | object | Ratios for the latest period (see Ratios)                     |
| growth         | object | Growth for the latest period (see Growth)                     |
| ttm            | object | Trailing-twelve-month aggregates (see Trailing Twelve Months) |

## Segments

GET /api/sec-companies/{symbol}/segments returns revenue broken down by business segment, as disclosed in the filing XBRL. Use the axis parameter to filter by dimension.

#### Request Example

 

 

```
https://eodhd.com/api/sec-companies/AAPL.US/segments?api_token=YOUR_API_TOKEN
```
```
curl --location "https://eodhd.com/api/sec-companies/AAPL.US/segments?api_token=YOUR_API_TOKEN&fmt=json"
```
#### Response Example

```json
{
  "data": [
    {
      "axis": "Geographic",
      "member": "CN",
      "concept": "RevenueFromContractWithCustomerExcludingAssessedTax",
      "value": 64377000000,
      "unit": "USD",
      "period_end": "2025-09-27"
    }
  ]
}

```

#### Response Fields

| Field       | Type    | Description                                                                |
| ----------- | ------- | -------------------------------------------------------------------------- |
| axis        | string  | Segment dimension, for example Geographic or ProductOrService              |
| member      | string  | Segment member within the axis, for example a country code or product line |
| concept     | string  | The reported XBRL concept, typically a revenue concept                     |
| value       | integer | Reported value for the segment                                             |
| unit        | string  | Value unit, typically USD                                                  |
| period\_end | string  | Reporting period end date, YYYY-MM-DD                                      |

## Response Codes

| Code | Meaning                                    |
| ---- | ------------------------------------------ |
| 200  | Success; data returned                     |
| 401  | Unauthorized; missing or invalid API token |
| 402  | Daily API request limit exceeded           |
| 403  | Plan does not include SEC data access      |
| 404  | Symbol not found                           |
| 422  | Invalid query parameters                   |
| 429  | Too many requests; rate limit exceeded     |

## Known Limitations

- **Derived from filings.** Every metric comes from a company’s own 10-K and 10-Q filings. When a source line item is not reported, dependent ratios and aggregates are null rather than estimated.
- **Industry-specific ratios.** Some ratios do not apply to every business. Banks and other financial firms, for example, do not report a classified balance sheet, so current ratio, quick ratio, and working capital are null for them; gross margin is null where a company does not report gross profit.
- **Growth needs a prior year.** Year-over-year growth is null for the earliest period in a company’s history, since there is no comparison period.
- **Segments are as-disclosed.** Segment rows exist only when the company discloses segment revenue in its XBRL. Single-segment filers return no segment rows.

## Related APIs

- [SEC Filings API](https://eodhd.com/financial-apis/sec-filings-api) — the raw 10-K, 10-Q, and 8-K filings these analytics are built on.
- [Fundamentals API](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds) — standardized company fundamentals across global markets.
- [Insider Transactions API](https://eodhd.com/financial-apis/insider-transactions-api) — SEC Form 4 insider buys and sells for the same companies.
