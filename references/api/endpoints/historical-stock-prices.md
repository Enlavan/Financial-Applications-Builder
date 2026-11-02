> Public API reference snapshot: 2026-10-25. Read [the integration contract](../../api-contract.md) first; its corrections override older examples. Verify current parameters before a production build.

# Historical Stock Prices API (End-of-Day)

Status: complete
Source: financial-apis (End-Of-Day Historical Stock Market Data API)
Docs: https://eodhd.com/financial-apis/api-for-historical-data-and-volumes
Service: EODHD public API
Base URL: https://eodhd.com/api
Path: /eod/{SYMBOL}
Method: GET
Auth: api_token (query)

## Purpose

Fetches end-of-day historical OHLCV (Open, High, Low, Close, Volume) data for a symbol,
with optional date range, period aggregation, and output format controls. The primary
endpoint for historical price analysis, backtesting, and charting.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| {SYMBOL} | Yes | path | Ticker with exchange suffix (e.g., 'AAPL.US', 'BMW.XETRA') |
| api_token | Yes | string | Your API key for authentication |
| from | No | string (YYYY-MM-DD) | Start date. Defaults to earliest available |
| to | No | string (YYYY-MM-DD) | End date. Defaults to latest available |
| period | No | string | Aggregation period: 'd' (daily), 'w' (weekly), 'm' (monthly). Default: 'd' |
| order | No | string | Sort order: 'a' (ascending), 'd' (descending). Default: 'a' |
| fmt | No | string | Output format: 'json' or 'csv'. Default: 'csv' |
| filter | No | string | Return single value: 'last_close' or 'last_volume' (requires fmt=json) |

## Response (shape)

```json
[
  {
    "date": "2025-01-02",
    "open": 182.15,
    "high": 185.60,
    "low": 181.50,
    "close": 184.25,
    "adjusted_close": 184.25,
    "volume": 45678900
  },
  {
    "date": "2025-01-03",
    "open": 184.50,
    "high": 186.90,
    "low": 183.20,
    "close": 186.75,
    "adjusted_close": 186.75,
    "volume": 52341200
  }
]
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| date | string (date) | Trading date (YYYY-MM-DD) |
| open | number | Opening price |
| high | number | Highest price during the period |
| low | number | Lowest price during the period |
| close | number | Closing price (unadjusted) |
| adjusted_close | number | Close adjusted for splits and dividends |
| volume | integer | Trading volume (adjusted for splits) |

### Adjustment Notes

- `open`, `high`, `low`, `close`: Raw/unadjusted prices
- `adjusted_close`: Adjusted for stock splits and dividends
- `volume`: Adjusted for stock splits only
- For accurate historical comparisons, use `adjusted_close`

## Example Requests

```bash
# Full history for Apple
curl "https://eodhd.com/api/eod/AAPL.US?api_token=YOUR_API_TOKEN&fmt=json"

# Specific date range
curl "https://eodhd.com/api/eod/AAPL.US?from=2020-01-05&to=2020-02-10&api_token=YOUR_API_TOKEN&fmt=json"

# Weekly aggregation
curl "https://eodhd.com/api/eod/MSFT.US?from=2024-01-01&to=2024-12-31&period=w&api_token=YOUR_API_TOKEN&fmt=json"

# Monthly aggregation
curl "https://eodhd.com/api/eod/GOOGL.US?from=2020-01-01&period=m&api_token=YOUR_API_TOKEN&fmt=json"

# Just the last close price
curl "https://eodhd.com/api/eod/NVDA.US?filter=last_close&api_token=YOUR_API_TOKEN&fmt=json"

# Descending order (most recent first)
curl "https://eodhd.com/api/eod/TSLA.US?order=d&api_token=YOUR_API_TOKEN&fmt=json"

# Using the helper client
python eodhd_client.py --endpoint eod --symbol AAPL.US --from-date 2025-01-01 --to-date 2025-01-31
```

## Notes

- **Default format is CSV**: Always pass `fmt=json` for programmatic access. Without it, the API returns CSV which is harder to parse.
- API call consumption: 1 call per request (any length of history)
- Symbol format: `{TICKER}.{EXCHANGE}` (e.g., `AAPL.US`, `BMW.XETRA`, `BTC-USD.CC`)
- Free plan: Limited to 1 year of historical data
- Updates arrive in rounds. US initial EOD data may appear around 15 minutes after close and be refined over subsequent hours; timing varies by ticker/exchange.
- Weekends and holidays have no data (trading days only)
- **Zero volume**: Retain and flag these records according to the application contract. Zero volume does not by itself prove missing data or justify deleting a session. Do not infer trade provenance from a flat candle.
- For intraday data, use the `/intraday/{SYMBOL}` endpoint
- For delayed live snapshots, use the `/real-time/{SYMBOL}` endpoint where supported.

## HTTP Status Codes

The API returns standard HTTP status codes to indicate success or failure:

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| **200** | OK | Request succeeded. Data returned successfully. |
| **402** | Payment Required | API limit used up. Upgrade plan or wait for limit reset. |
| **403** | Unauthorized | Invalid API key. Check your `api_token` parameter. |
| **429** | Too Many Requests | Exceeded rate limit (requests per minute). Slow down requests. |

### Error Response Format

When an error occurs, the API returns a JSON response with error details:

```json
{
  "error": "Error message description",
  "code": 403
}
```

### Handling Errors

**Python Example**:
```python
import requests

def make_api_request(url, params):
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises HTTPError for bad status codes
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 402:
            print("Error: API limit exceeded. Please upgrade your plan.")
        elif e.response.status_code == 403:
            print("Error: Invalid API key. Check your credentials.")
        elif e.response.status_code == 429:
            print("Error: Rate limit exceeded. Please slow down your requests.")
        else:
            print(f"HTTP Error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
```

**Best Practices**:
- Always check status codes before processing response data
- Implement exponential backoff for 429 errors
- Cache responses to reduce API calls
- Monitor your API usage in the user dashboard
