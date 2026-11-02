> Public documentation snapshot, 2026-10-25. Read [the integration contract](../../api-contract.md).

# Stock Market Trading Hours and Holidays API | EODHD APIs Documentation

Source: https://eodhd.com/financial-apis/exchanges-api-trading-hours-and-stock-market-holidays

 

## Get Exchange Details and Trading Hours

EODHD provides two versions of the Exchange Details endpoint. The v2 endpoint is recommended for all new integrations — it returns verified data for 73 exchanges, including extended trading sessions, lunch breaks, early close days, and a complete holiday calendar.

### v2: List Available Exchanges

 

 

```
https://eodhd.com/api/v2/exchange-details?api_token={YOUR_API_TOKEN}
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/v2/exchange-details?api_token={YOUR_API_TOKEN}&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/v2/exchange-details?api_token={YOUR_API_TOKEN}&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

Returns an array of all exchange codes supported by the v2 endpoint. Use these codes to request details for a specific exchange.

```json
{
  "data": [
    "ASEX", "BMEX", "BVMF", "LSE", "NEO", "NILX",
    "ROCO", "TO", "US", "XAMS", "XASX", "XHKG",
    "XKRX", "XNSE", "XPAR", "XTKS", "..."
  ]
}
```

### v2: Get Exchange Details

 

 

```
https://eodhd.com/api/v2/exchange-details/US?api_token={YOUR_API_TOKEN}
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/v2/exchange-details/US?api_token={YOUR_API_TOKEN}&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/v2/exchange-details/US?api_token={YOUR_API_TOKEN}&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

Returns trading hours, extended sessions, and the full holiday calendar for the requested exchange. The code parameter is case-insensitive.

### v2: Response Fields

| Field                          | Type   | Description                                 |
| ------------------------------ | ------ | ------------------------------------------- |
| Name                           | string | Full exchange name                          |
| Code                           | string | Exchange code used in this endpoint         |
| Timezone                       | string | IANA timezone (e.g. America/New\_York)      |
| TradingHours.Open              | string | Regular session open time (HH:MM:SS)        |
| TradingHours.Close             | string | Regular session close time (HH:MM:SS)       |
| TradingHours.WorkingDays       | string | Trading days (e.g. Mon, Tue, Wed, Thu, Fri) |
| TradingHours.PreMarketOpen     | string | Pre-market session open (if available)      |
| TradingHours.PreMarketClose    | string | Pre-market session close (if available)     |
| TradingHours.AfterHoursOpen    | string | After-hours session open (if available)     |
| TradingHours.AfterHoursClose   | string | After-hours session close (if available)    |
| TradingHours.LunchBreakStart   | string | Lunch break start (if applicable)           |
| TradingHours.LunchBreakEnd     | string | Lunch break end (if applicable)             |
| ExchangeHolidays               | object | Holiday calendar keyed by date (YYYY-MM-DD) |
| ExchangeHolidays.\*.Holiday    | string | Holiday name                                |
| ExchangeHolidays.\*.Type       | string | Official, Bank, or EarlyClose               |
| ExchangeHolidays.\*.EarlyClose | string | Early close time (only for EarlyClose type) |

Session fields (PreMarketOpen, AfterHoursOpen, LunchBreakStart, etc.) are only present when the exchange has that session. For example, US exchanges include pre-market and after-hours, Hong Kong includes a lunch break.

### v2 Example: US Exchange (Pre-Market and After-Hours)

```json
{
  "data": {
    "Name": "NYSE / NASDAQ",
    "Code": "US",
    "Timezone": "America/New_York",
    "TradingHours": {
      "Open": "09:30:00",
      "Close": "16:00:00",
      "WorkingDays": "Mon, Tue, Wed, Thu, Fri",
      "PreMarketOpen": "04:00:00",
      "PreMarketClose": "09:30:00",
      "AfterHoursOpen": "16:00:00",
      "AfterHoursClose": "20:00:00"
    },
    "ExchangeHolidays": {
      "2026-01-01": {
        "Holiday": "New Year's Day",
        "Type": "Official"
      },
      "2026-11-27": {
        "Holiday": "Day after Thanksgiving",
        "Type": "EarlyClose",
        "EarlyClose": "13:00:00"
      },
      "2026-12-24": {
        "Holiday": "Christmas Eve",
        "Type": "EarlyClose",
        "EarlyClose": "13:00:00"
      },
      "2026-12-25": {
        "Holiday": "Christmas Day",
        "Type": "Official"
      }
    }
  }
}
```

### v2 Example: Hong Kong Exchange (Lunch Break and Early Close)

```json
{
  "data": {
    "Name": "Hong Kong Stock Exchange",
    "Code": "XHKG",
    "Timezone": "Asia/Hong_Kong",
    "TradingHours": {
      "Open": "09:30:00",
      "Close": "16:00:00",
      "WorkingDays": "Mon, Tue, Wed, Thu, Fri",
      "LunchBreakStart": "12:00:00",
      "LunchBreakEnd": "13:00:00"
    },
    "ExchangeHolidays": {
      "2026-02-16": {
        "Holiday": "Lunar New Year's Eve",
        "Type": "EarlyClose",
        "EarlyClose": "12:00:00"
      },
      "2026-02-17": {
        "Holiday": "Lunar New Year",
        "Type": "Official"
      },
      "2026-07-01": {
        "Holiday": "HKSAR Establishment Day",
        "Type": "Official"
      },
      "2026-12-25": {
        "Holiday": "Christmas Day",
        "Type": "Official"
      }
    }
  }
}
```

### What v2 Adds Over v1

- **Pre-market and after-hours sessions** – available for US and other supported exchanges
- **Lunch breaks** – for exchanges that halt midday (Hong Kong, Shanghai, and others)
- **Early close days** – exact close time on shortened trading days (e.g. Christmas Eve at 13:00)
- **Verified holiday calendars** – complete and manually verified for all 73 exchanges
- **Correct timezones** – IANA format for all exchanges

### v1: Legacy Endpoint

The v1 endpoint remains available for backward compatibility. It covers all exchanges supported by EODHD and includes real-time status fields not available in v2.

 

 

```
https://eodhd.com/api/exchange-details/{EXCHANGE_CODE}?api_token={YOUR_API_TOKEN}&fmt=json
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/exchange-details/{EXCHANGE_CODE}?api_token={YOUR_API_TOKEN}&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/exchange-details/{EXCHANGE_CODE}?api_token={YOUR_API_TOKEN}&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

Use the exchange codes from the Exchanges API List endpoint. The v1 response includes:

- **Timezone** – the timezone of the exchange
- **isOpen** – boolean value indicating if the exchange is open right now or closed
- **TradingHours** – open and close times with working days in the exchange timezone, may include lunch hours
- **ActiveTickers** – tickers with any activity for the past two months
- **UpdatedTickers** – tickers updated for the current day

```json
{
  "Name": "USA Stocks",
  "Code": "US",
  "OperatingMIC": "XNAS, XNYS, OTCM, XCBO",
  "Country": "USA",
  "Currency": "USD",
  "Timezone": "America/New_York",
  "isOpen": true,
  "TradingHours": {
    "Open": "09:30:00",
    "Close": "16:00:00",
    "OpenUTC": "13:30:00",
    "CloseUTC": "20:00:00",
    "WorkingDays": "Mon,Tue,Wed,Thu,Fri"
  },
  "ActiveTickers": 52334,
  "UpdatedTickers": 0
}
```

## Stock Market Holidays Data API

Holiday data is included in both v2 and v1 exchange details responses.

In v2, the full holiday calendar for the current year is always returned along with exchange details. No additional parameters are needed. Holidays are keyed by date and include a Type field (Official, Bank, or EarlyClose). The EarlyClose type also includes the exact early close time for that day.

In v1, holidays are part of the same exchange-details response and can be filtered with additional parameters:

- **from** – the format is ‘YYYY-MM-DD’. The default value is 6 months before the current date.
- **to** – the format is ‘YYYY-MM-DD’. The default value is 6 months after the current date.

The two versions use different response formats for holidays:

```json
// v2 format – keyed by date, includes EarlyClose type
"ExchangeHolidays": {
  "2026-01-01": {
    "Holiday": "New Year's Day",
    "Type": "Official"
  },
  "2026-12-24": {
    "Holiday": "Christmas Eve",
    "Type": "EarlyClose",
    "EarlyClose": "13:00:00"
  }
}

// v1 format – indexed array with Date field
"ExchangeHolidays": {
  "0": {
    "Holiday": "New Year's Day",
    "Date": "2026-01-01",
    "Type": "official"
  }
}
```

And do not forget to check our Exchanges API and Symbol Change History API.

[Sign up & Get Data](https://eodhd.com/register)
