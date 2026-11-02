> Public documentation snapshot, 2026-10-25. Read [the integration contract](../../api-contract.md).

# Congressional Trades API (beta) | EODHD APIs Documentation

Source: https://eodhd.com/financial-apis/congressional-trades-api

 

The EODHD Congressional Trades API returns stock-trade disclosures filed by members of the US Congress. Under the STOCK Act, senators and representatives must publicly disclose their securities transactions within 45 days. EODHD collects these filings directly from the two official government portals — the Senate Electronic Financial Disclosure system and the House Clerk disclosure site — normalises them into a single schema, and serves both chambers through one endpoint.

Each record pairs the trading member with the traded asset and the transaction, and adds fields the raw filings do not provide directly: numeric bounds parsed from the disclosed amount range, the number of days between the trade and its disclosure, a flag for filings that missed the 45-day window, and a link back to the original filing for verification.

## Overview

The endpoint is reached over HTTPS with a GET request and authenticated by an api\_token query parameter, the same token used across the EODHD API. It returns a JSON object with three top-level keys: data (the array of trade records), meta (the number of rows matching the filter across all pages, plus the offset and limit of the page you received), and links (the path of the next page, when one exists). Results are paged with page\[offset\] and page\[limit\], where the default page size is 20 rows and the maximum is 100.

```
https://eodhd.com/api/congressional-trades?api_token=YOUR_TOKEN
```

Records are always returned newest first, ordered by transaction date descending. The order is fixed — there is no sort parameter, so narrow a result set with the filters below rather than by re-ordering it. A handful of filings carry a mistyped transaction date that falls in the future, and descending order puts them at the very top of an unfiltered request, so set transaction\_date\_to to today’s date when you want a clean first page. JSON is the only output format; there is no fmt parameter, and any unrecognised query parameter is ignored rather than rejected.

Filter parameters are passed as flat query keys, for example chamber=senate and transaction\_type=purchase,sale. Only the two pagination parameters use bracket notation: page\[offset\] and page\[limit\]. Recognised parameters are validated at the gateway, so an invalid value returns HTTP 422 before the request reaches the data service.

## Coverage and History

History goes back to the first electronic periodic transaction reports published under the STOCK Act, which took effect in 2012\. Both chambers appear from 2012 onwards, with sparse coverage before 2014 while electronic filing was still being adopted. The figures below were measured in August 2026 and grow with every new filing.

| Measure                       | Value                                   |
| ----------------------------- | --------------------------------------- |
| Earliest transaction          | 14 June 2012                            |
| Most recent transaction       | 6 August 2026, disclosed 17 August 2026 |
| Total trade records           | 45,561                                  |
| House / Senate                | 31,611 / 13,878                         |
| Purchases / sales / exchanges | 23,068 / 22,177 / 316                   |

Annual volume is sparse at the start and then becomes continuous: 2012 contributes 8 trades and 2013 contributes 123\. From 2014 the record runs without gaps — 1,486 trades that year, then roughly 2,900 to 4,800 per year through 2024, with 2025 the heaviest year so far at 7,379\. For a study that needs a uniform history, 2014 is the practical starting point; 2012 and 2013 are better treated as a fragment than as full years.

Every count above can be reproduced from the API itself, so you never have to rely on this page being current. Request a date window and read total from the meta object — this returns the number of trades that took place during the 2025 calendar year:

```
https://eodhd.com/api/congressional-trades?api_token=YOUR_TOKEN&transaction_date_from=2025-01-01&transaction_date_to=2025-12-31&page%5Blimit%5D=1
```

Freshness follows the source, not the market. A trade appears once the member files it, and the STOCK Act allows up to 45 days for that, so the newest transaction date in the feed trails the current date by days to weeks. Filings are collected four times on each weekday, at 00:00, 06:00, 12:00 and 19:00 UTC, with a separate reconciliation pass at 03:00 UTC that re-reads recent filings and picks up amendments.

To load the full history once, page through the endpoint with no date filter except transaction\_date\_to set to today, using the maximum page size of 100 and following the next link until it is absent. After that, refresh a rolling recent window rather than only appending: a filing amended at the source is corrected in place, so rows you already hold can change. For backtesting, remember that a trade only becomes public on its disclosure date — use disclosure-date filters for public timing, while retaining the limitation that current amended records are not historical vintages, and treat transaction\_date as the event date rather than the date the information was available.

## Request

All parameters are optional except api\_token. Filters combine with logical AND, and the member, date-range, symbol, and transaction-type filters can be used together to narrow the result set.

#### Parameters

`api_token` string  required 

Your EODHD API token 

`symbol` string  optional 

Restrict to a single ticker symbol, for example AAPL. Records whose asset carries no ticker are excluded by this filter 

`chamber` enum  optional 

Chamber of Congress, lower case. Allowed values: senate, house 

`bioguide_id` string  optional 

Congressional Biographical Directory ID of a single member, for example S000250\. Format is one upper-case letter followed by six digits 

`transaction_type` enum  optional 

One or more transaction types, comma-separated, for example purchase,sale. Allowed values: purchase, sale, exchange 

`transaction_date_from` date  optional 

Earliest transaction date, YYYY-MM-DD, inclusive 

`transaction_date_to` date  optional 

Latest transaction date, YYYY-MM-DD, inclusive, on or after transaction\_date\_from 

`disclosure_date_from` date  optional 

Earliest disclosure date, YYYY-MM-DD, inclusive 

`disclosure_date_to` date  optional 

Latest disclosure date, YYYY-MM-DD, inclusive, on or after disclosure\_date\_from 

`page[limit]` integer  optional 

Rows per page _(Default: 20, Range: 1-100)_ 

`page[offset]` integer  optional 

Rows to skip _(Default: 0)_ 

#### Request Example

 

 

```
https://eodhd.com/api/congressional-trades?api_token=YOUR_TOKEN&chamber=senate&transaction_type=purchase,sale&transaction_date_from=2026-01-01&page[limit]=5
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/congressional-trades?api_token=YOUR_TOKEN&chamber=senate&transaction_type=purchase,sale&transaction_date_from=2026-01-01&page[limit]=5&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/congressional-trades?api_token=YOUR_TOKEN&chamber=senate&transaction_type=purchase,sale&transaction_date_from=2026-01-01&page[limit]=5&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

## Response

Each record carries a top-level chamber field and four nested objects: member, asset, transaction, and source. The example below is a single record; a real response returns an array under data.

#### Response Example

```json
{
  "data": [
    {
      "chamber": "senate",
      "member": {
        "bioguide_id": "W000802",
        "first_name": "Sheldon",
        "last_name": "Whitehouse",
        "full_name": "Sheldon Whitehouse",
        "office": "Whitehouse, Sheldon (Senator)",
        "state": null,
        "party": null,
        "district": null
      },
      "asset": {
        "symbol": "NVDA",
        "description": "NVIDIA Corporation - Common Stock",
        "asset_type": "Stock"
      },
      "transaction": {
        "type": "sale",
        "transaction_date": "2026-06-30",
        "disclosure_date": "2026-07-08",
        "owner": "Self",
        "amount_range": "$15,001 - $50,000",
        "amount_low": 15001,
        "amount_high": 50000,
        "days_to_disclose": 8,
        "is_late": false,
        "comment": null
      },
      "source": {
        "filing_url": "EXTERNAL_LINK_OMITTED",
        "source_system": "senate",
        "filing_identifier": "5d9b1b8e-2ae1-442b-860c-e79b8a701dc6"
      }
    }
  ],
  "meta": { "total": 45561, "page": { "offset": 0, "limit": 20 } },
  "links": { "next": "/api/congressional-trades?page%5Boffset%5D=20&page%5Blimit%5D=20" }
}
```

The next link is a path relative to the API host, with the pagination brackets URL-encoded. Prefix it with https://eodhd.com and add your api\_token to fetch the following page. The next key is absent on the last page, which is the signal to stop paging.

#### Response Fields

| Field                          | Type           | Description                                                                                                                                                                                               |
| ------------------------------ | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| chamber                        | string         | Chamber of Congress: senate or house                                                                                                                                                                      |
| member.bioguide\_id            | string or null | Congressional Biographical Directory identifier. Populated where the filed name matches the public congressional directory; null for roughly a quarter of records, mostly older filings and name variants |
| member.first\_name             | string         | Member first name                                                                                                                                                                                         |
| member.last\_name              | string         | Member last name                                                                                                                                                                                          |
| member.full\_name              | string         | Member full name as filed                                                                                                                                                                                 |
| member.office                  | string or null | Office label as it appears in the source filing                                                                                                                                                           |
| member.state                   | string or null | Two-letter US state code, when the filing provides it                                                                                                                                                     |
| member.party                   | null           | Reserved for the member’s political party. Neither source portal publishes party on the disclosure, so this field is currently always null                                                                |
| member.district                | number or null | House district number. Null for senators                                                                                                                                                                  |
| asset.symbol                   | string or null | Ticker symbol, when the asset maps to a listed instrument. Null for roughly a quarter of records — bonds, funds held outside listed markets, and other untickered holdings                                |
| asset.description              | string         | Asset description as filed                                                                                                                                                                                |
| asset.asset\_type              | string         | Normalised asset class: Stock, StockOption, Bond, or Other                                                                                                                                                |
| transaction.type               | string         | Transaction type: purchase, sale, or exchange                                                                                                                                                             |
| transaction.transaction\_date  | string (date)  | Date the trade took place, YYYY-MM-DD                                                                                                                                                                     |
| transaction.disclosure\_date   | string (date)  | Date the trade was disclosed, YYYY-MM-DD                                                                                                                                                                  |
| transaction.owner              | string or null | Account owner: Self, Spouse, Joint, or Child                                                                                                                                                              |
| transaction.amount\_range      | string         | Disclosed transaction amount band, as filed, for example $1,001 – $15,000\. Also carries open-ended bands such as Over $1,000,000, and Unknown where the filing states no band                            |
| transaction.amount\_low        | number or null | Lower bound of the amount range, in US dollars. Null when the band cannot be parsed into bounds                                                                                                           |
| transaction.amount\_high       | number or null | Upper bound of the amount range, in US dollars. Null for open-ended bands and unparsable ones                                                                                                             |
| transaction.days\_to\_disclose | number         | Days between transaction\_date and disclosure\_date                                                                                                                                                       |
| transaction.is\_late           | boolean        | True when the filing missed the 45-day STOCK Act disclosure window. Around one record in ten is late                                                                                                      |
| transaction.comment            | string or null | Free-text note from the filing, when present                                                                                                                                                              |
| source.filing\_url             | string         | Link to the original filing on the official government portal                                                                                                                                             |
| source.source\_system          | string         | Origin of the filing: senate or house                                                                                                                                                                     |
| source.filing\_identifier      | string         | Identifier of the filing at the source system                                                                                                                                                             |

[Sign up & Get Data](https://eodhd.com/register)

## Response Codes

| Code | Meaning                                                                                                                                                                                                                                 |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 200  | Success. Response body carries data, meta, and links                                                                                                                                                                                    |
| 401  | Missing or invalid api\_token                                                                                                                                                                                                           |
| 403  | Token is valid but the plan does not include Congressional Trades                                                                                                                                                                       |
| 422  | Invalid parameter — malformed date, page\[limit\] above 100 or below 1, end date before start date, an unknown chamber or transaction type, or a malformed symbol or bioguide\_id. The response body names the parameter and the reason |

## Notes and Limitations

- Both chambers are returned together. Use chamber=senate or chamber=house to restrict to one; the chamber field on each record identifies its origin.
- Exchanges are rare. Purchases and sales are split almost evenly across the history — roughly 23,000 each — while the exchange type accounts for 316 records in total, so a filter on it returns a small set by nature.
- The amount\_low and amount\_high fields are parsed from the disclosed amount band; days\_to\_disclose and is\_late are computed against the 45-day STOCK Act window. These are provided by EODHD and are not part of the raw filing.
- Some holdings, including many bonds and other instruments, carry no ticker symbol. For those records asset.symbol is null while asset.description and asset.asset\_type remain populated, and a request filtered by symbol will not return them.
- Source data is reproduced as filed. Member details such as state are populated only where the source provides them, and data-entry errors in the original disclosures are passed through rather than silently corrected. The filing\_url on each record links to the official source for verification.
- 82 records carry a mistyped transaction date that falls in the future, the most extreme in the year 3031\. They are copied from the filings as submitted, and because results are ordered by transaction date descending they surface on the first unfiltered page. Set transaction\_date\_to to today’s date to exclude them.
- Disclosure timing is set by the filer, not by EODHD. The STOCK Act allows up to 45 days between a trade and its disclosure, and late filings occur, so treat this data as a disclosure record rather than a real-time signal.

## Related APIs

- [Insider Transactions API](https://eodhd.com/financial-apis/insider-transactions-api) — the corporate counterpart: trades filed by company officers and directors on SEC Form 4.
- [SEC Filings API](https://eodhd.com/financial-apis/sec-filings-api) — the filings themselves, for readers who need the underlying disclosure documents.
- [End-of-Day Historical Data API](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes) — prices to join to a trade, for measuring what a disclosed transaction was worth or how the stock moved afterwards.
- [Search API](https://eodhd.com/financial-apis/search-api-for-stocks-etfs-mutual-funds) — resolve a company name from a filing into the ticker to pass as symbol.
- [Sanctions API](https://eodhd.com/financial-apis/sanctions-api-ofac-screening-data-entities-vessels) — another compliance and screening dataset built on official government sources.

Compare plans and find your fit

Free and paid plans for individual and commercial use

[ Go to Pricing ](https://eodhd.com/pricing)
