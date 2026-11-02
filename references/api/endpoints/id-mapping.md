> Public documentation snapshot, 2026-10-25. Read [the integration contract](../../api-contract.md).

# ID Mapping API: CUSIP / ISIN / FIGI / LEI / CIK ↔ Symbol | EODHD APIs Documentation

Source: https://eodhd.com/financial-apis/id-mapping-api-cusip-isin-figi-lei-cik-%e2%86%94-symbol

 

The **ID Mapping API** lets you resolve common identifiers (CUSIP, ISIN, OpenFIGI, LEI, CIK) to a tradable **symbol** (e.g. AAPL) and vice-versa using flexible filters. It’s ideal for onboarding portfolios, normalizing vendor feeds, or building “search-and-resolve” experiences.

## API Endpoint

```
GET https://eodhd.com/api/id-mapping
```

## Description

Retrieve common identifiers for a symbol or by a specific identifier. Supports CUSIP, ISIN, OpenFigi, LEI, and CIK. At least one filter value is required.

## Request Example

 

 

```
https://eodhd.com/api/id-mapping?filter[symbol]=AAPL.US&page[limit]=100&page[offset]=0&api_token=YOUR_API_TOKEN&fmt=json
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/id-mapping?filter[symbol]=AAPL.US&page[limit]=100&page[offset]=0&api_token=YOUR_API_TOKEN&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/id-mapping?filter[symbol]=AAPL.US&page[limit]=100&page[offset]=0&api_token=YOUR_API_TOKEN&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

## Parameters

| Parameter        | Required                          | Type    | Description                                                     |
| ---------------- | --------------------------------- | ------- | --------------------------------------------------------------- |
| filter\[symbol\] | Yes (if no other filter provided) | string  | Scope results by ticker, for example: AAPL.US                   |
| filter\[ex\]     | Yes (if no other filter provided) | string  | Scope results by exchange code, for example: US                 |
| filter\[isin\]   | Yes (if no other filter provided) | string  | Scope results by ISIN, for example: US0378331005                |
| filter\[figi\]   | Yes (if no other filter provided) | string  | Scope results by OpenFigi identifier, for example: BBG000B9XRY4 |
| filter\[lei\]    | Yes (if no other filter provided) | string  | Scope results by LEI, for example: HWUPKR0MPOU8FGXBT394         |
| filter\[cusip\]  | Yes (if no other filter provided) | string  | Scope results by CUSIP, for example: 037833100                  |
| filter\[cik\]    | Yes (if no other filter provided) | string  | Scope results by CIK, for example: 0000320193                   |
| page\[limit\]    | No                                | integer | Limit results per request. Default: 1000, min: 1, max: 1000     |
| page\[offset\]   | No                                | integer | Offset for pagination. Default: 0                               |
| api\_token       | Yes                               | string  | Your unique API access token                                    |

Notes:

- Provide at least one of the following: filter\[symbol\], filter\[ex\], filter\[isin\], filter\[figi\], filter\[lei\], filter\[cusip\], filter\[cik\].
- Filters use deep-object style (filter\[…\]) for clarity and future extensibility.

## Output Format (JSON)

The response includes meta for pagination, a data array of mapping objects, and links for pagination.

| Field           | Type           | Description                                     |
| --------------- | -------------- | ----------------------------------------------- |
| meta.total      | integer        | Total number of results available               |
| meta.limit      | integer        | Max number of results returned in this response |
| meta.offset     | integer        | Offset applied to this response                 |
| data            | array          | List of mapping records                         |
| data\[\].symbol | string         | Ticker symbol                                   |
| data\[\].isin   | string         | ISIN identifier                                 |
| data\[\].figi   | string         | OpenFigi identifier                             |
| data\[\].lei    | string         | LEI identifier                                  |
| data\[\].cusip  | string         | CUSIP identifier                                |
| data\[\].cik    | string         | CIK identifier                                  |
| links.next      | string or null | URL to the next page, if available              |

## Output Response Example

```json
{
  "meta": {
    "total": 1,
    "limit": 100,
    "offset": 0
  },
  "data": [
    {
      "symbol": "AAPL.US",
      "isin": "US0378331005",
      "figi": "BBG000B9XRY4",
      "lei": "HWUPKR0MPOU8FGXBT394",
      "cusip": "037833100",
      "cik": "0000320193"
    }
  ],
  "links": {
    "next": null
  }
}

```

## Additional Examples

Lookup by ISIN:

 

 

```
https://eodhd.com/api/id-mapping?filter[isin]=US0378331005&api_token=YOUR_API_TOKEN
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/id-mapping?filter[isin]=US0378331005&api_token=YOUR_API_TOKEN&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/id-mapping?filter[isin]=US0378331005&api_token=YOUR_API_TOKEN&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

Looking by exchange code:

 

 

```
https://eodhd.com/api/id-mapping?filter[ex]=US&page[limit]=50&api_token=YOUR_API_TOKEN
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/id-mapping?filter[ex]=US&page[limit]=50&api_token=YOUR_API_TOKEN&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/id-mapping?filter[ex]=US&page[limit]=50&api_token=YOUR_API_TOKEN&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

Use our [Search API](https://eodhd.com/financial-apis/search-api-for-stocks-etfs-mutual-funds) to locate assets filtering by asset category, exchange or ticker name.
