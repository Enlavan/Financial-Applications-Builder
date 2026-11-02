> Public documentation snapshot, 2026-10-25. Read [the integration contract](../../api-contract.md).

# Stock Screener API for Global Markets | EODHD

Source: https://eodhd.com/financial-apis/stock-market-screener-api

 

The Screener API filters the whole covered stock universe in a single request — by market capitalisation, exchange, sector, industry, EPS, dividend yield, recent performance and traded volume — and returns the matching tickers with the values you filtered on. It is the endpoint behind “top gainers today”, “large-cap technology companies”, “high-yield dividend payers” and similar screens.

Filters are passed as a JSON array of conditions that all have to hold at once, sorting is a single field with a direction, and results are paginated with limit and offset. Values come from the latest completed trading day — every row carries the date it was taken from in **last\_day\_data\_date**.

## How to call the Screener API

```
https://eodhd.com/api/screener?api_token=YOUR_API_TOKEN&filters=[["exchange","=","us"],["market_capitalization",">",10000000000]]&sort=market_capitalization.desc&limit=10&offset=0
```

#### Parameters

`api_token` string  required 

Your EODHD API token 

`filters` string  optional 

Filter conditions as a JSON array of triples: \[\[field, operation, value\], …\]. Conditions are combined with AND. Must be valid JSON with straight double quotes 

`signals` string  optional 

Comma-separated list of pre-calculated signals, for example bookvalue\_neg,200d\_new\_lo. Several signals narrow the result further 

`sort` string  optional 

Sort as field\_name.direction, for example market\_capitalization.desc. Direction is asc or desc; every filterable field is also sortable 

`limit` integer  optional 

Number of tickers to return _(Default: 50, Range: 1-500)_ 

`offset` integer  optional 

Number of tickers to skip, for paging. limit=100 with offset=200 returns rows 201-300\. Because the offset stops at 999, no screen can be paged beyond its first 1,000 matches _(Default: 0, Range: 0-999)_ 

The filters value must be valid JSON with straight double quotes. Curly typographic quotes — the kind a word processor produces — return HTTP 422 with “The filters must be a valid JSON string”. Requesting more than 500 rows, or an offset above 999, also returns 422\. Since paging stops at offset 999, a single screen exposes at most its first 1,000 matches — narrow the filters, or split the screen by exchange or by market-capitalisation band, when a query matches more than that.

#### Request Example

The five largest companies by market capitalisation, no filters:

 

 

```
https://eodhd.com/api/screener?api_token=YOUR_TOKEN&sort=market_capitalization.desc&limit=5
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/screener?api_token=YOUR_TOKEN&sort=market_capitalization.desc&limit=5&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/screener?api_token=YOUR_TOKEN&sort=market_capitalization.desc&limit=5&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

#### Response Example

```
{
    "data": [
        {
            "code": "AAPL",
            "name": "Apple Inc.",
            "last_day_data_date": "2026-08-12",
            "adjusted_close": 302.25,
            "refund_1d": -2.66,
            "refund_1d_p": -0.87,
            "refund_5d": -8.482,
            "refund_5d_p": -2.73,
            "exchange": "US",
            "currency_symbol": "$",
            "market_capitalization": 4411090796544,
            "earnings_share": 8.72,
            "dividend_yield": 0.0034,
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "avgvol_1d": 40588500,
            "avgvol_200d": 49738504
        }
    ]
}
```

#### Response Fields

| Field                  | Type   | Description                                                                                                        |
| ---------------------- | ------ | ------------------------------------------------------------------------------------------------------------------ |
| code                   | string | Ticker code without the exchange suffix                                                                            |
| name                   | string | Company name                                                                                                       |
| last\_day\_data\_date  | date   | Trading day the price and performance values come from                                                             |
| adjusted\_close        | number | Latest known end-of-day adjusted close                                                                             |
| refund\_1d             | number | Absolute price change over the last trading day, in the listing currency                                           |
| refund\_1d\_p          | number | Price change over the last trading day, in percent                                                                 |
| refund\_5d             | number | Absolute price change over the last 5 trading days                                                                 |
| refund\_5d\_p          | number | Price change over the last 5 trading days, in percent                                                              |
| exchange               | string | Exchange code the ticker belongs to                                                                                |
| currency\_symbol       | string | Currency the price and market capitalisation are expressed in — read this before comparing values across exchanges |
| market\_capitalization | number | Latest market capitalisation, in the listing currency (see the note below)                                         |
| earnings\_share        | number | Latest earnings per share                                                                                          |
| dividend\_yield        | number | Latest dividend yield as a fraction — 0.0034 means 0.34% (see the note below)                                      |
| sector                 | string | Sector name                                                                                                        |
| industry               | string | Industry name                                                                                                      |
| avgvol\_1d             | number | Last trading day volume                                                                                            |
| avgvol\_200d           | number | Average volume over the last 200 trading days                                                                      |

## Filter fields

Fourteen fields can be filtered on, and each of them can also be used for sorting. String fields take the string operations, number fields take the numeric ones.

| Field                  | Type   | Notes                                                                                                                      |
| ---------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------- |
| code                   | string | Ticker code, for example AAPL                                                                                              |
| name                   | string | Company name. Use the match operation for partial names                                                                    |
| exchange               | string | Exchange code, for example us or lse. NYSE and NASDAQ are also accepted here and narrow the US exchange down to that venue |
| sub\_exchange          | string | Venue inside a composite exchange — NYSE or NASDAQ. Equivalent to passing those values in exchange                         |
| sector                 | string | Sector name. Multi-word values need the match operation rather than an exact match                                         |
| industry               | string | Industry name, same rule as sector                                                                                         |
| market\_capitalization | number | Latest market capitalisation, in the listing currency                                                                      |
| earnings\_share        | number | Latest earnings per share                                                                                                  |
| dividend\_yield        | number | Latest dividend yield as a fraction: use 0.05 for 5%                                                                       |
| refund\_1d\_p          | number | Last trading day gain or loss in percent — the field for top gainers and losers                                            |
| refund\_5d\_p          | number | Last 5 trading days gain or loss in percent                                                                                |
| adjusted\_close        | number | Latest known end-of-day adjusted close                                                                                     |
| avgvol\_1d             | number | Last trading day volume — useful as a liquidity floor                                                                      |
| avgvol\_200d           | number | Average volume over the last 200 trading days                                                                              |

Exchange codes come from the [Exchanges API](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours). The full sector and industry taxonomy is available as a [CSV download](https://eodhd.com/download/SectorIndustries.csv).

Not every ticker carries a value for the fundamentals-derived fields — market capitalisation, EPS, dividend yield, sector, industry and average volume are all missing for a sizeable share of the global universe, mostly on secondary listings and smaller venues. Filtering on one of those fields therefore also excludes every ticker where the value is absent, which is a different result from “every company that fails the condition”. Where that distinction matters, screen per exchange and compare the row counts.

Market capitalisation and prices are expressed in the currency each ticker is listed in, not converted to US dollars. A filter such as market\_capitalization greater than 10 billion therefore matches companies whose capitalisation is 10 billion in dong, baht or euro as readily as in dollars, and the same company can appear several times through its foreign listings. Add an exchange condition — or read the currency\_symbol field of every row — when you need one currency. The same caution applies to dividend\_yield: most rows are clean fractions, but a minority of secondary foreign listings carry values in the thousands, so cap the upper bound of the filter or restrict it to the exchanges you trust.

## Operations

| Field type | Operations                              |
| ---------- | --------------------------------------- |
| String     | \= · match · in · not in                |
| Number     | \= · != · > · < · >= · <= · in · not in |

- **match** matches from the start of a word, and an asterisk extends the prefix: “Apple” and “App\*” both find Apple Inc., while a mid-word fragment such as “pple” matches nothing.
- **in** and **not in** take a JSON array as the value, for example \[“exchange”,”in”,\[“us”,”to”\]\] or \[“sector”,”not in”,\[“Technology”,”Energy”\]\]. A single-element array is fine.
- String comparisons are case-insensitive: “aapl” and “AAPL” behave the same, as do “technology” and “Technology”.
- Applying a numeric operation to a string field, or the other way round, returns HTTP 422 with an invalid-operation error. A screen that matches nothing returns HTTP 200 with an empty data array, and a missing or invalid token returns HTTP 401.

[Sign up & Get Data](https://eodhd.com/register)

## Signals

Signals are pre-calculated conditions that would be awkward to express as a filter. Pass them comma-separated in the signals parameter. Several signals narrow the result rather than widen it — a ticker has to satisfy every signal listed — and signals combine with filters the same way.

| Signal         | Selects                                              |
| -------------- | ---------------------------------------------------- |
| 200d\_new\_lo  | Tickers making a new 200-day low                     |
| 200d\_new\_hi  | Tickers making a new 200-day high                    |
| bookvalue\_neg | Tickers with a negative book value                   |
| bookvalue\_pos | Tickers with a positive book value                   |
| wallstreet\_lo | Tickers trading below the Wall Street analyst target |
| wallstreet\_hi | Tickers trading above the Wall Street analyst target |

```
https://eodhd.com/api/screener?api_token=YOUR_API_TOKEN&signals=bookvalue_neg,200d_new_lo&limit=10
```

New signals are added over time, and we can build one on request — write to support@eodhistoricaldata.com or raise it in the community subreddit.

## Screener API examples

### Top gainers of the last trading day

Sort by the one-day percentage change and put a volume floor under it, so the list is not dominated by illiquid micro-caps:

```
https://eodhd.com/api/screener?api_token=YOUR_API_TOKEN&filters=[["exchange","=","us"],["avgvol_1d",">",1000000]]&sort=refund_1d_p.desc&limit=10
```

### Large-cap technology companies on NASDAQ

```
https://eodhd.com/api/screener?api_token=YOUR_API_TOKEN&filters=[["exchange","=","NASDAQ"],["sector","=","Technology"],["market_capitalization",">",10000000000],["earnings_share",">",0]]&sort=market_capitalization.desc&limit=10
```

### Dividend payers above five percent

Yield is a fraction, so five percent is 0.05\. The upper bound and the exchange condition keep the mis-scaled foreign listings out:

```
https://eodhd.com/api/screener?api_token=YOUR_API_TOKEN&filters=[["exchange","=","us"],["dividend_yield",">",0.05],["dividend_yield","<",0.25],["market_capitalization",">",1000000000]]&sort=dividend_yield.desc&limit=10
```

### Partial name search across two exchanges

```
https://eodhd.com/api/screener?api_token=YOUR_API_TOKEN&filters=[["exchange","in",["us","to"]],["name","match","Apple*"]]&limit=10
```

## More examples

Four screens that combine several conditions at once. Each one was run against the live endpoint and returns real matches.

### Income screen with excluded sectors

Profitable US dividend payers above 2 billion, liquid enough to trade, with financials, utilities and real estate left out and the yield capped at a plausible 15% so the mis-scaled rows cannot creep in:

```
https://eodhd.com/api/screener?api_token=YOUR_API_TOKEN&filters=[["exchange","=","us"],["sector","not in",["Financial Services","Utilities","Real Estate"]],["earnings_share",">",0],["dividend_yield",">",0.04],["dividend_yield","<",0.15],["market_capitalization",">",2000000000],["avgvol_1d",">",300000]]&sort=dividend_yield.desc&limit=25
```

Seven conditions in one request. The **not in** operation takes a JSON array, and the two dividend\_yield conditions form a band, since the API has no between operation.

### Large caps trading below the analyst target

A signal and a filter set working together: liquid US companies above 10 billion whose price sits under the Wall Street target:

```
https://eodhd.com/api/screener?api_token=YOUR_API_TOKEN&signals=wallstreet_lo&filters=[["exchange","=","us"],["adjusted_close",">",5],["market_capitalization",">",10000000000],["avgvol_200d",">",1000000]]&sort=market_capitalization.desc&limit=25
```

The price and volume floors matter more than they look: without them a signal screen fills up with sub-cent tickers that technically satisfy the condition.

### One industry across four markets

Semiconductor companies above 1 billion, listed in the US, Toronto, London or XETRA:

```
https://eodhd.com/api/screener?api_token=YOUR_API_TOKEN&filters=[["exchange","in",["us","to","lse","xetra"]],["industry","match","Semiconductors"],["market_capitalization",">",1000000000]]&sort=market_capitalization.desc&limit=25
```

This is the screen that shows the currency caveat in action. The same company comes back several times — once per listing — and the capitalisations are not comparable, because each is expressed in its own listing currency. Read **currency\_symbol** on every row before ranking them.

### NASDAQ mid-caps by name prefix

Companies whose name starts with “Bio”, listed on NASDAQ, with a reported EPS and a capitalisation between 300 million and 20 billion:

```
https://eodhd.com/api/screener?api_token=YOUR_API_TOKEN&filters=[["sub_exchange","=","NASDAQ"],["name","match","Bio*"],["earnings_share","!=",0],["market_capitalization",">=",300000000],["market_capitalization","<=",20000000000]]&sort=market_capitalization.desc&limit=25
```

Four techniques in one request: venue selection through **sub\_exchange**, a wildcard name prefix through **match**, exclusion of unreported EPS through **!=**, and a capitalisation band built from two inclusive bounds.

## Where to go next

The screener returns tickers; the detail comes from the other endpoints. Pull statements and ratios for a match from the [Fundamental Data API](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds), price history from the [End-of-Day API](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes), and indicators such as RSI or SMA from the [Technical Indicators API](https://eodhd.com/financial-apis/technical-indicators-api). To resolve a code you got back into every venue it trades on, use the [Search API](https://eodhd.com/financial-apis/search-api-for-stocks-etfs-mutual-funds).

Screening without writing code is possible too: the screener ships inside our [Google Sheets and Excel add-ons](https://eodhd.com/financial-apis/spreadsheets-for-stocks-etfs-forex-markets) and in the [Python library](https://eodhd.com/financial-apis/python-financial-libraries-and-code-samples).

Building a screener into a product? Our Stock Market Logos API on the EODHD Marketplace returns a company logo for any ticker across 60+ equity exchanges, which is usually the missing piece when screener results are rendered as a list.

Compare plans and find your fit

Free and paid plans for individual and commercial use

[ Go to Pricing ](https://eodhd.com/pricing)
