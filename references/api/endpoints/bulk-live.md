> Public documentation snapshot, 2026-10-25. Read [the integration contract](../../api-contract.md).

# Bulk Live (Delayed) OHLCV Stock Prices API — US | EODHD

Source: https://eodhd.com/financial-apis/bulk-for-live-ohlcv-stock-prices-api-us-exchanges-only

 

This is the bulk mode of the [Live OHLCV Stock Prices API](https://eodhd.com/financial-apis/live-ohlcv-stocks-api). With the ex=US parameter, a single request returns the latest live OHLCV values for every ticker listed on US exchanges, instead of quoting one symbol at a time.

Scope at a glance. Coverage: US exchanges only (NYSE and NASDAQ). One ex=US request returns all US-listed tickers in a single response, currently around 18,000 rows. The ticker in the path is only a placeholder and is ignored when ex=US is set, so any US ticker works. The default response format is CSV; add fmt=json for JSON.

## Quick Start

Call the Live (Real-Time) endpoint with ex=US. The path ticker is a placeholder, so AAPL.US below can be any US ticker:

```
GET https://eodhd.com/api/real-time/AAPL.US?ex=US
```

#### Parameters

`api_token` string  required 

Your EODHD API token 

`ex` enum  optional 

Aggregates all US exchanges into a single bulk response. Allowed value: US 

`fmt` enum  optional 

Response format. Allowed values: csv, json _(Default: csv)_ 

#### Request Example

 

 

```
https://eodhd.com/api/real-time/AAPL.US?ex=US&api_token=YOUR_API_TOKEN&fmt=json
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/real-time/AAPL.US?ex=US&api_token=YOUR_API_TOKEN&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/real-time/AAPL.US?ex=US&api_token=YOUR_API_TOKEN&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

#### Response Example

JSON returns an array with one object per US-listed ticker (around 18,000 rows):

```json
[
  {
    "code": "A.US",
    "timestamp": 1784059800,
    "gmtoffset": 0,
    "open": 133.93,
    "high": 135.8,
    "low": 132.89,
    "close": 135.2,
    "volume": 1683225,
    "previousClose": 134.04,
    "change": 1.16,
    "change_p": 0.87
  },
  {
    "code": "AAPL.US",
    "timestamp": 1784060820,
    "gmtoffset": 0,
    "open": 313.76,
    "high": 316.19,
    "low": 311.91,
    "close": 314.86,
    "volume": 34509408,
    "previousClose": 317.31,
    "change": -2.45,
    "change_p": -0.7721
  }
]
```

#### Response Fields

| Field         | Type    | Description                               |
| ------------- | ------- | ----------------------------------------- |
| code          | string  | Ticker code, for example AAPL.US          |
| timestamp     | integer | Quote time as a Unix timestamp, seconds   |
| gmtoffset     | integer | Offset from GMT in seconds                |
| open          | number  | Opening price of the session              |
| high          | number  | Session high                              |
| low           | number  | Session low                               |
| close         | number  | Latest price                              |
| volume        | integer | Traded volume                             |
| previousClose | number  | Previous session close                    |
| change        | number  | Change versus previous close, price units |
| change\_p     | number  | Change versus previous close, percent     |

[Sign up & Get Data](https://eodhd.com/register)

Each ex=US request consumes 100 API calls, compared with 1 call for a single-symbol quote. Poll it deliberately rather than in a tight loop.

Compare plans and find your fit

Free and paid plans for individual and commercial use

[ Go to Pricing ](https://eodhd.com/pricing)
