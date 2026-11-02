> Public documentation snapshot, 2026-10-25. Read [the integration contract](../../api-contract.md) and [plans and limits](../../plans-limits.md).
> In plans (docs): Fundamentals, All-in-one plans. Cost: 1 API call per request.

# ASX (Australia) Corporate Actions API (beta) | EODHD APIs Documentation

Source: https://eodhd.com/financial-apis/asx-australia-corporate-actions-beta

 

The EODHD ASX Corporate Actions API provides structured corporate action data for the Australian Securities Exchange (ASX): dividends, stock splits, bonus issues, rights issues, buybacks, capital returns, and share purchase plans.

Coverage is limited to ASX-listed securities. All tickers use the **.AU** suffix. You will need an EODHD API subscription that includes access to the Corporate Actions endpoint — available on **Fundamentals** and **All-in-One** plans.

## API Endpoint

```
https://eodhd.com/api/asx-corporate-actions
```

**Method:** GET. **Auth:** **api\_token** query parameter. **Cost:** 1 API call per request. **Pagination:** offset/limit based, default 100 per page (max 1000).

## Query Parameters

| Parameter      | Required | Description                                                               |
| -------------- | -------- | ------------------------------------------------------------------------- |
| api\_token     | Yes      | Your EODHD API token                                                      |
| type           | No       | Corporate action type (see table below). Omit to return all types         |
| symbol         | No       | Ticker with .AU suffix (e.g. PMV.AU). Filter results to a single security |
| date\_from     | No       | Start date in YYYY-MM-DD format (inclusive, applied to event date)        |
| date\_to       | No       | End date in YYYY-MM-DD format (inclusive, applied to event date)          |
| page\[offset\] | No       | Pagination offset, zero-based (default 0)                                 |
| page\[limit\]  | No       | Page size, 1 to 1000 (default 100)                                        |
| fmt            | No       | Response format. Currently only json is supported                         |

## Action Types

The **type** parameter accepts one of the following values. Each value groups one or more ASX action codes:

| Value           | ASX Codes                  | Description                                                |
| --------------- | -------------------------- | ---------------------------------------------------------- |
| dividends       | DV                         | Cash dividends (including franked amounts and DRP details) |
| splits          | RC                         | Stock splits and reconstructions                           |
| bonus-issues    | BN                         | Bonus share issues                                         |
| rights-issues   | RR, NR, PR, XR             | Rights issues, including non-renounceable variants         |
| buybacks        | BB                         | Share buyback programmes                                   |
| capital-returns | CR                         | Return of capital to shareholders                          |
| spp             | SP                         | Share Purchase Plans                                       |
| other           | AO, CC, CG, CL, CN, IN, OP | Other action types not covered by the categories above     |

## Request Example

 

 

```
https://eodhd.com/api/asx-corporate-actions?api_token=YOUR_TOKEN&type=dividends&symbol=PMV.AU&fmt=json
```
```
curl --location "https://eodhd.com/api/asx-corporate-actions?api_token=YOUR_TOKEN&type=dividends&symbol=PMV.AU&fmt=json"
```
## Response Format

All responses share the same envelope. The **data** array contains records whose structure depends on the requested **type**:

```json
{
  "data": [ /* type-specific records */ ],
  "meta": {
    "total": 566,
    "page": { "offset": 0, "limit": 100 }
  },
  "links": {
    "next": "https://eodhd.com/api/asx-corporate-actions?page%5Boffset%5D=100&page%5Blimit%5D=100"
  }
}
```

### Dividends

```json
{
  "code": "PMV.AU",
  "date": "2026-08-03",
  "value": 0.45,
  "unadjustedValue": 0.45,
  "period": "Interim",
  "currency": "AUD",
  "exchange": "AU",
  "recordDate": "2026-08-04",
  "paymentDate": "2026-08-20",
  "declarationDate": null,
  "_asx_extra": {
    "isin": "AU000000PMV2",
    "asx_ticker": "PMV",
    "corporate_action_id": "000478776",
    "transaction_type": "A",
    "franked_amount_aud": 0.45,
    "franked_percent": 100,
    "drp_indicator": 4,
    "drp_discount_rate": 0,
    "special_indicator": "N",
    "withholding_tax_rate": 0,
    "comment": "AUD 0.45 FRANKED, 30% CTR, DRP SUSP"
  }
}
```

The **\_asx\_extra** object carries ASX-specific fields such as franking credits, DRP (Dividend Reinvestment Plan) details, BSP (Bonus Share Plan) flags, withholding tax, and tax-advantaged amounts. See the AU-specific fields section below for the full field list.

### Splits

```json
{
  "code": "NTM.AU",
  "date": "2026-06-03",
  "split": "2000:3",
  "exchange": "AU",
  "_asx_extra": {
    "asx_ticker": "NTM",
    "record_date": "2026-06-04",
    "effective_date": "2026-06-05",
    "new_security_code": "NTM",
    "calculation_method": "M",
    "corporate_action_id": "000478901"
  }
}
```

### Bonus Issues

```json
{
  "code": "RDM.AU",
  "date": "2026-05-13",
  "ratio": "4:21",
  "exchange": "AU",
  "pariPassu": false,
  "recordDate": "2026-05-14",
  "despatchDate": "2026-05-21"
}
```

### Rights Issues

```json
{
  "code": "CRR.AU",
  "date": "2026-05-07",
  "type": "non-renounceable",
  "ratio": "1:10",
  "currency": "AUD",
  "exchange": "AU",
  "pariPassu": false,
  "recordDate": "2026-05-08",
  "despatchDate": "2026-05-29",
  "applicationPrice": 0.001,
  "applicationCloseDate": "2026-05-22"
}
```

### Capital Returns

```json
{
  "code": "FAR.AU",
  "date": "2026-06-02",
  "value": 0.0035,
  "currency": "AUD",
  "exchange": "AU",
  "recordDate": "2026-06-03",
  "paymentDate": "2026-06-11"
}
```

### Share Purchase Plan (SPP)

```json
{
  "code": "WBT.AU",
  "price": 405,
  "currency": "AUD",
  "exchange": "AU",
  "maxAmount": 30000,
  "minAmount": 2500,
  "recordDate": "2026-03-25",
  "despatchDate": "2026-05-06",
  "offerCloseDate": "2026-04-29"
}
```

## AU-specific Fields (Dividends)

Australian dividends carry additional attributes that reflect the local tax and reinvestment framework. These are exposed under **\_asx\_extra**:

| Field                          | Type           | Description                                             |
| ------------------------------ | -------------- | ------------------------------------------------------- |
| franked\_amount\_aud           | number         | Portion of the dividend that is franked, in AUD         |
| franked\_percent               | number         | Franking percentage (0–100)                             |
| drp\_indicator                 | integer        | Dividend Reinvestment Plan status flag (ASX E34 code)   |
| drp\_price\_aud                | number or null | DRP issue price in AUD when applicable                  |
| drp\_discount\_rate            | number         | Percentage discount offered under the DRP               |
| bsp\_indicator                 | integer        | Bonus Share Plan status flag                            |
| special\_indicator             | string         | Y/N flag indicating a special dividend                  |
| withholding\_tax\_rate         | number         | Non-resident withholding tax rate in percent            |
| tax\_deferred\_amount\_aud     | number         | Tax-deferred portion of the distribution, in AUD        |
| tax\_advantaged\_amount\_aud   | number         | Conduit foreign income / tax-advantaged portion, in AUD |
| foreign\_source\_dividend\_aud | number         | Foreign source portion, in AUD                          |
| special\_dividend\_amount\_aud | number         | Special dividend portion, in AUD                        |
| comment                        | string         | Free-text annotation from the ASX feed                  |

## Response Codes

| Code | Meaning                                                            |
| ---- | ------------------------------------------------------------------ |
| 200  | Success. Response includes data, meta, and links.                  |
| 401  | Missing or invalid api\_token.                                     |
| 403  | Plan does not include access to this endpoint.                     |
| 422  | Validation error — invalid type, date format, or pagination range. |
| 429  | Rate limit exceeded.                                               |

## Known Limitations

- **ASX only.** Only Australian Securities Exchange tickers are covered. Use the [Splits and Dividends API](https://eodhd.com/financial-apis/api-splits-dividends/) for other exchanges.
- **Daily refresh.** Data is refreshed once per day. Same-day changes may appear with up to a 24-hour delay.
- **Sparse categories.** Buybacks and other action types currently have low record counts — ASX publishes these less frequently than dividends or rights issues.
- **Plan access.** The endpoint is available on Fundamentals and All-in-One plans. It is **not** included in the standalone Fundamental plan.
