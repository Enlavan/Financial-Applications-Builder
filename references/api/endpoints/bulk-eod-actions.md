> Public documentation snapshot, 2026-10-25. Read [the integration contract](../../api-contract.md).

# Bulk API: Whole-Exchange EOD, Splits and Dividends

Source: https://eodhd.com/financial-apis/bulk-api-eod-splits-dividends

 

One request, one exchange, one day. Instead of looping over thousands of tickers to close your books, this endpoint returns the whole market in a single download — end-of-day prices, or every split, or every dividend that landed on that date. A full US day — 18 August 2026, to name the one measured here — is **44,376 rows**, delivered as a 2.3 MB CSV or a 6.7 MB JSON file.

The same endpoint serves three datasets through the **type** parameter, and it reaches back decades rather than only to the last session: 2 January 1990 returns 2,197 US rows, 15 June 2000 returns 13,860, and non-US venues go back too — 303 rows on XETRA for that day in 2000, 425 on the LSE for 1 March 1995\. The row count is itself a record of how coverage grew.

Cost is worth understanding before you write the loop. A whole-exchange request is a flat **100 API calls** regardless of how many rows come back, while adding the symbols parameter charges **100 plus one call per ticker** — measured at 102 calls for two tickers and 104 for four. Asking for a handful of names through this endpoint is therefore _more_ expensive than taking the entire exchange, and far more expensive than the single call each ticker costs on the [End-of-Day API](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes). Use symbols for convenience, not to save quota.

Bulk downloads are not part of the Free plan, and each dataset carries the entitlement of its per-ticker equivalent: prices need the end-of-day feed, splits the splits feed, dividends the dividends feed. A plan with prices but not corporate actions will serve the first and refuse the other two. The sidebar lists the plans that include all three.

## End-of-day prices for a whole exchange

```
https://eodhd.com/api/eod-bulk-last-day/US?api_token=YOUR_API_TOKEN&fmt=json
```

#### Path Parameter

`exchangeCode` string  required 

Exchange code from the Exchanges API, for example US, XETRA or WAR. Four US venue codes are also accepted — NYSE, NASDAQ, BATS and AMEX — and return only that venue. An unknown code returns HTTP 404 with the body Exchange Not Found. 

#### Query Parameters

`api_token` string  required 

Your EODHD API token 

`type` enum  optional 

Which dataset to return. Allowed values: eod, splits, dividends. Any other value currently returns HTTP 500 with a generic error body rather than a validation error _(Default: eod)_ 

`date` date  optional 

The day to download, YYYY-MM-DD. Two silent fallbacks: a past non-trading day returns the previous trading day relative to the date you asked for (a Sunday gave the Friday, US Independence Day 2026 gave 2 July, Christmas 2020 gave 24 December), while a future date returns the latest available day instead. Read the date field in the response rather than assuming. An unparseable value returns HTTP 422 with a validation error naming the date field _(Default: last trading day)_ 

`symbols` string  optional 

Comma-separated tickers instead of the whole exchange. Suffixes are honoured and may cross exchanges — MSFT,AAPL,BMW.XETRA,SAP.F returns all four in one response, and the exchange in the path stops mattering (the same pair came back through the US, NASDAQ, XETRA and WAR paths alike). Ignored when type is splits or dividends. It also changes the shape of price rows: with symbols each row gains prev\_close, change and change\_p (CSV: Prev\_close, Change, Change\_%), which a whole-exchange response does not carry 

`fmt` enum  optional 

Response format. Allowed values: json, csv. JSON carries most of the dividend record that CSV does not, so pass fmt=json for dividends. For prices the format makes no difference to prev\_close, change and change\_p — those depend on the symbols parameter, not on fmt _(Default: csv)_ 

`filter` enum  optional 

Set to extended for company name, market capitalisation and technical fields. See the extended dataset section 

The four US venue codes cover the exchange one level down, and they carve it up cleanly: on 18 August 2026 NYSE returned 5,853 rows, NASDAQ 5,365, BATS 1,512 and AMEX 284, with **no ticker appearing in two of them** and all 13,014 also present in the composite. The composite is much larger, though — 44,376 rows — so **31,362 tickers, OTC and similar venues among them, are reachable only through US**. Note also that every row still reports the exchange as **US**: the venue lives in the path, not in the data. Codes outside those four behave unevenly — NMFQS, OTCQB, PINK and NYSEARCA all return 404, OTC returns HTTP 200 with an empty array, and NYSE ARCA returns a payload byte-identical to NYSE.

#### Request Example

**Whole exchange** — no symbols. Each row is the bare price bar:

 

 

```
https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&fmt=json
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

#### Response Example

```
[
    {
        "code": "MSFT",
        "exchange_short_name": "US",
        "date": "2026-08-18",
        "open": 481.54,
        "high": 484.27,
        "low": 477.15,
        "close": 481.63,
        "adjusted_close": 481.63,
        "volume": 24059700
    }
]
```

**With symbols** — the same rows plus prev\_close, change and change\_p:

 

 

```
https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&symbols=MSFT,AAPL&fmt=json
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&symbols=MSFT,AAPL&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&symbols=MSFT,AAPL&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

```
[
    {
        "code": "MSFT",
        "exchange_short_name": "US",
        "date": "2026-08-18",
        "open": 481.54,
        "high": 484.27,
        "low": 477.15,
        "close": 481.63,
        "adjusted_close": 481.63,
        "volume": 24059700,
        "prev_close": 480.35,
        "change": 1.28,
        "change_p": 0.2665
    }
]
```

The CSV form of a whole-exchange request is leaner — nine columns, headed **Code, Ex, Date, Open, High, Low, Close, Adjusted\_close, Volume**. It is also about a third of the size: 2.3 MB against 6.7 MB for a full US day.

The fields in the response depend on whether you pass symbols. A whole-exchange request returns the bare price bar (code, exchange\_short\_name, date, open, high, low, close, adjusted\_close, volume). Naming tickers with symbols returns the same rows **plus** prev\_close, change and change\_p — in JSON and in CSV alike, and with filter=extended too. The second example above was requested with symbols. If your code reads prev\_close, change or change\_p from a whole-exchange download, those keys are absent: calculate them yourself from the previous day’s close, or request the tickers with symbols.

#### Response Fields

| JSON field             | CSV column             | Description                                                                                  |
| ---------------------- | ---------------------- | -------------------------------------------------------------------------------------------- |
| code                   | Code                   | Ticker without the exchange suffix                                                           |
| exchange\_short\_name  | Ex                     | Exchange the instrument belongs to                                                           |
| date                   | Date                   | Trading day the row describes — check it, it is not always the date you asked for            |
| open, high, low, close | Open, High, Low, Close | Prices for the session                                                                       |
| adjusted\_close        | Adjusted\_close        | Close adjusted for splits and dividends                                                      |
| volume                 | Volume                 | Shares traded                                                                                |
| prev\_close            | Prev\_close            | Previous session’s close. Returned only when the symbols parameter is used                   |
| change                 | Change                 | Absolute change against the previous close. Returned only when the symbols parameter is used |
| change\_p              | Change\_%              | Change in percent. Returned only when the symbols parameter is used                          |

## Splits and dividends for the day

```
https://eodhd.com/api/eod-bulk-last-day/US?api_token=YOUR_API_TOKEN&type=splits&fmt=json
https://eodhd.com/api/eod-bulk-last-day/US?api_token=YOUR_API_TOKEN&type=dividends&fmt=json
```

Corporate actions rather than prices, filtered to the same single day. The files are small — the whole US market produced 4 splits and 96 dividends on 18 August 2026, 328 bytes and 21 KB of JSON — so a daily reconciliation against your own position keeping is light on bandwidth, though it costs the same 100 calls as a full price download.

The **symbols** parameter has no effect on these two datasets — the response is byte-for-byte identical with and without it, checked by checksum — yet you are still charged one extra call per ticker you name. So filter on your side, and leave symbols out: a whole-day corporate-actions request is a flat 100 calls, the same as a full price download, and naming tickers only makes it dearer.

#### Splits

 

 

```
https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&type=splits&fmt=json
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&type=splits&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&type=splits&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

```
[
    {
        "code": "CXAI",
        "exchange": "US",
        "date": "2026-08-18",
        "split": "1.000000/50.000000"
    },
    {
        "code": "LNOK",
        "exchange": "US",
        "date": "2026-08-18",
        "split": "2.000000/1.000000"
    }
]
```

The ratio is a single string, and the order is **new shares before old** — the same string the [Corporate Actions API](https://eodhd.com/financial-apis/api-splits-dividends) returns for the same event. Known splits pin it down: Tesla’s five-for-one in August 2020 reads 5.000000/1.000000, Apple’s four-for-one 4.000000/1.000000, and General Electric’s one-for-eight reverse split 1.000000/8.000000\. By that reading CXAI above is a one-for-fifty reverse split and LNOK a two-for-one forward split. Both directions arrive in the same feed, so compare the two sides rather than assuming a forward split. In CSV the columns are **Code, Ex, Date, Split**.

#### Dividends

 

 

```
https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&type=dividends&fmt=json
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&type=dividends&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&type=dividends&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

```
[
    {
        "code": "ACNDF",
        "exchange": "US",
        "date": "2026-08-18",
        "dividend": "0.02000",
        "currency": "USD",
        "declarationDate": "2026-07-29",
        "recordDate": "2026-08-18",
        "paymentDate": "2026-09-23",
        "period": "Semiannual",
        "unadjustedValue": "0.0200000000"
    }
]
```

This is where the format choice matters most. CSV gives you five columns — **Code, Ex, Date, Dividend, Currency** — while JSON adds the declaration, record and payment dates, the payment period and the unadjusted amount. Some fields can come back as null — declarationDate and period were empty on a same-day record checked on 14 October 2026 — so do not assume every dividend row is fully populated. Watch the naming while you are here: the dividend record is camelCase (declarationDate, paymentDate) where the price record is snake\_case (adjusted\_close, exchange\_short\_name), and splits report the venue as exchange rather than exchange\_short\_name. Three datasets, three conventions. If you need a dividend calendar rather than one day at a time, take the [Corporate Actions: Splits and Dividends API](https://eodhd.com/financial-apis/api-splits-dividends) or the [Calendar API](https://eodhd.com/financial-apis/calendar-upcoming-earnings-ipos-and-splits) instead.

[Sign up & Get Data](https://eodhd.com/register)

## The extended dataset

```
https://eodhd.com/api/eod-bulk-last-day/US?api_token=YOUR_API_TOKEN&fmt=json&filter=extended
```

Adding filter=extended turns each row from a price bar into a small profile: the company name and instrument type, market capitalisation and beta, two exponential moving averages, the 250-day high and low, and average volumes over 14, 50 and 200 days. With symbols, each row also carries prev\_close, change and change\_p, as for plain prices. It costs nothing extra — a whole-exchange request measured the same flat 100 calls with the filter as without it.

**Whole exchange** with filter=extended:

```
[
    {
        "code": "AAPL",
        "name": "Apple Inc.",
        "type": "Common Stock",
        "exchange_short_name": "US",
        "date": "2026-08-18",
        "MarketCapitalization": 4524633751552,
        "Beta": 1.086,
        "open": 307.53,
        "high": 311.49,
        "low": 305.74,
        "close": 310.03,
        "adjusted_close": 310.03,
        "volume": 46601840,
        "ema_50d": 308.777,
        "ema_200d": 282.161,
        "hi_250d": 339.787,
        "lo_250d": 224.072,
        "avgvol_14d": 54119474.285714,
        "avgvol_50d": 57919922.8,
        "avgvol_200d": 49631782.7
    }
]
```

**With symbols** — prev\_close, change and change\_p are added:

```
[
    {
        "code": "AAPL",
        "name": "Apple Inc.",
        "type": "Common Stock",
        "exchange_short_name": "US",
        "date": "2026-08-18",
        "MarketCapitalization": 4524633751552,
        "Beta": 1.086,
        "open": 307.53,
        "high": 311.49,
        "low": 305.74,
        "close": 310.03,
        "adjusted_close": 310.03,
        "volume": 46601840,
        "ema_50d": 308.777,
        "ema_200d": 282.161,
        "hi_250d": 339.787,
        "lo_250d": 224.072,
        "prev_close": 305.59,
        "change": 4.44,
        "change_p": 1.4529,
        "avgvol_14d": 54119474.285714,
        "avgvol_50d": 57919922.8,
        "avgvol_200d": 49631782.7
    }
]
```

Two traps live in this filter. The technical fields are computed for the **last 30 days only**, and an older date does not raise an error — it returns the row with ema\_50d, ema\_200d, hi\_250d, lo\_250d and every avgvol field set to **0**. Measured on 19 August 2026: a date 30 days back still carried real values, 31 days back returned zeros. And **MarketCapitalization and Beta are not point-in-time** — they hold today’s figure whatever date you request, identical on a row from 2024 and a row from yesterday. For historical market capitalisation use the [Historical Market Capitalization API](https://eodhd.com/financial-apis/historical-market-capitalization-api), and for indicators over longer windows the [Technical API](https://eodhd.com/financial-apis/technical-indicators-api).

The CSV variant carries most of the same data under different names — **EMA\_50**, **EMA\_200**, **High\_250**, **Low\_250**, **Change\_%**, **Avgvol\_14d**, and Prev\_close and Change\_% only with symbols — and drops two fields entirely: Beta and the instrument type are JSON-only.

## Where to go next

This endpoint is one day wide. For a full price history of one instrument use the [End-of-Day API](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes), which costs a single call per ticker; for intraday bars the [Intraday API](https://eodhd.com/financial-apis/intraday-historical-data-api). Complete split and dividend histories, with amounts and payment dates, are in the [Corporate Actions API](https://eodhd.com/financial-apis/api-splits-dividends), and what is still scheduled ahead is in the [Calendar API](https://eodhd.com/financial-apis/calendar-upcoming-earnings-ipos-and-splits).

To learn which exchange codes exist, list them with the [Exchanges API](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours); to see how the 100-call charge sits against your plan, see [API Limits](https://eodhd.com/financial-apis/api-limits). Fundamentals for a whole exchange in one request are a separate feed — the [Bulk Fundamentals API](https://eodhd.com/financial-apis/bulk-fundamentals-api-via-extended-fundamentals-plan).

Compare plans and find your fit

Free and paid plans for individual and commercial use

[ Go to Pricing ](https://eodhd.com/pricing)
