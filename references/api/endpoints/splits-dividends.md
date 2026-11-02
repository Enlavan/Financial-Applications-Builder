> Public documentation snapshot, 2026-10-25. Read [the integration contract](../../api-contract.md).

# Corporate Actions API: Dividend & Split History Since 1970

Source: https://eodhd.com/financial-apis/api-splits-dividends

 

Corporate actions rewrite a price series after the fact. A dividend takes cash out of the share price on the ex-date; a split multiplies the share count and divides the price. Get either one wrong and a backtest, a yield calculation or a total-return chart is quietly wrong with it. This API gives you both histories for a single instrument in one request: every dividend with its amount, its currency and its declaration, record and payment dates, and every split with its exact ratio.

History is deep. For the longest-running US payers the record starts in **1970** — Procter & Gamble on 19 January 1970 is the earliest dividend found anywhere in our sampling, and the same floor holds for Johnson & Johnson, General Electric, IBM, Exxon and Coca-Cola. That is **more than fifty-five years** and, for Coca-Cola, 226 individual payments in one response. Splits go back almost as far: Procter & Gamble on 19 May 1970.

Both endpoints cost **1 API call per request**, whatever the date range and however many rows come back — measured directly against the request counter, with zero drift in the measurement window. Asking for one ticker’s entire fifty-five-year dividend history costs exactly as much as asking for last quarter. Take the whole history once and filter locally rather than paging by year.

These endpoints are per-ticker. To pull every split or every dividend that landed on one date across an entire exchange, use the [Bulk API](https://eodhd.com/financial-apis/bulk-api-eod-splits-dividends). For events that have been announced but have not happened yet, use the [Calendar API](https://eodhd.com/financial-apis/calendar-upcoming-earnings-ipos-and-splits) — this API is history, not schedule.

You can try both endpoints before you have a key, using **demo** as the api\_token — every request example on this page is a live one you can run as you read. The demo key is not limited to Apple: for these two feeds it covers **AAPL.US, MSFT.US, AMZN.US, TSLA.US, MCD.US, VTI.US and SWPPX.US**, with full history and no truncation — demo returns Apple dividends all the way back to 1987, the same 92 records a paid key sees. Any other ticker returns HTTP 403\. The demo key is for evaluation only; it carries its own rate limit and is not a substitute for a plan.

## Dividends History API

```
https://eodhd.com/api/div/{SYMBOL}?api_token=YOUR_API_TOKEN&fmt=json
```

#### Path Parameter

`SYMBOL` string  required 

Ticker in EODHD format, SYMBOL.EXCHANGE — for example AAPL.US, BMW.XETRA, SHEL.LSE or RY.TO. Exchange codes come from the Exchanges API. A ticker we do not carry returns HTTP 404 with the body Symbol not found, and that failed request is still billed as one call 

#### Query Parameters

`api_token` string  required 

Your EODHD API token. Omitting it returns HTTP 401 Unauthenticated 

`from` date  optional 

Start of the window, YYYY-MM-DD, inclusive. Omit it and you get the full history for the symbol _(Default: earliest available)_ 

`to` date  optional 

End of the window, YYYY-MM-DD, inclusive. Works on its own — passing only to returns everything up to that date _(Default: latest available)_ 

`fmt` enum  optional 

Response format, either json or csv. The default is csv, and the comparison is case-sensitive: fmt=JSON in capitals silently serves CSV instead of failing. CSV also carries far less data than JSON — see the field table below _(Default: csv)_ 

#### Request Example

 

 

```
https://eodhd.com/api/div/AAPL.US?from=2026-05-01&api_token=YOUR_API_TOKEN&fmt=json
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/div/AAPL.US?from=2026-05-01&api_token=YOUR_API_TOKEN&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/div/AAPL.US?from=2026-05-01&api_token=YOUR_API_TOKEN&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

#### Response Example

```
[
    {
        "date": "2026-05-11",
        "declarationDate": "2026-04-30",
        "recordDate": "2026-05-11",
        "paymentDate": "2026-05-14",
        "period": "Quarterly",
        "value": 0.27,
        "unadjustedValue": 0.27,
        "currency": "USD"
    },
    {
        "date": "2026-08-10",
        "declarationDate": "2026-07-30",
        "recordDate": "2026-08-10",
        "paymentDate": "2026-08-13",
        "period": "Quarterly",
        "value": 0.27,
        "unadjustedValue": 0.27,
        "currency": "USD"
    }
]
```

#### Response Fields

| Field           | Type           | Description                                                                                                                                                        | In CSV?           |
| --------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------- |
| date            | date           | **Ex-dividend date** — the day the share starts trading without the right to this payment. This is the date the from and to window filters on                      | Yes, as Date      |
| declarationDate | date or null   | Day the board announced the dividend                                                                                                                               | No                |
| recordDate      | date or null   | Day the register is closed to decide who gets paid                                                                                                                 | No                |
| paymentDate     | date or null   | Day the cash actually reaches shareholders                                                                                                                         | No                |
| period          | string or null | Payment cadence or nature. Values observed across a 20-ticker global sample: Quarterly, Final, Interim, Special and Other. Null on many funds and on older records | No                |
| value           | number         | **Split-adjusted** amount per share, restated in today’s share terms                                                                                               | Yes, as Dividends |
| unadjustedValue | number         | The amount **actually paid** per share on the day, in the share count of the time                                                                                  | No                |
| currency        | string         | Currency of the payment. Not always the currency the share is quoted in — see the warning below                                                                    | No                |

**CSV gives you two columns out of eight.** The CSV response is Date and Dividends and nothing else — declaration, record and payment dates, the period label, the unadjusted amount and the currency are all JSON-only. Since csv is also the _default_, a request without an explicit fmt parameter silently loses six fields. Pass fmt=json in lowercase whenever you need more than the ex-date and the adjusted amount.

### Adjusted versus unadjusted amounts

Two money fields come back for every payment, and mixing them up is the most expensive mistake you can make on this endpoint. **unadjustedValue** is the historical fact: what one share received on that day. **value** is that same payment restated in today’s shares, divided by every split that has happened since.

Apple makes the arithmetic visible. Its dividend on 11 May 1987 comes back as unadjustedValue 0.12096 and value 0.00054 — a ratio of exactly **224**, which is the product of all five Apple splits since: 2 × 2 × 2 × 7 × 4\. The next payment, on 10 August 1987, sits just after the first of those splits, and its ratio is **112**. Closer to the present, the payment of 8 May 2020 reads unadjustedValue 0.82 against value 0.205 — a ratio of exactly 4, the 4-for-1 split of that August — while the payment of 6 November 2020, the first one after it, has both fields at 0.205\. From there to today they stay identical, because no split has happened since.

Which one you want depends on what you are building. Use **value** when you are combining dividends with adjusted prices — a total-return series, a dividend-reinvestment backtest, a per-share income chart over decades. Use **unadjustedValue** when you are reconstructing what an account actually received, reconciling against a broker statement, or reading an old filing. Never mix an adjusted amount with an unadjusted price.

### How far the extended dates reach

Every record everywhere carries the ex-date, the amount, the unadjusted amount and the currency. The three extra dates thin out as you move away from North America. Measured over dividends since 2015 for a twenty-ticker global sample:

| Market                                                                              | Declaration    | Record                                                      | Payment        | Period                       |
| ----------------------------------------------------------------------------------- | -------------- | ----------------------------------------------------------- | -------------- | ---------------------------- |
| US stocks and ETFs — AAPL, MSFT, KO, JNJ, XOM, SPY, VTI                             | Complete       | Complete                                                    | Complete       | Complete except two ETF rows |
| Canada — RY.TO                                                                      | 47 of 48       | 47 of 48                                                    | 47 of 48       | 47 of 48                     |
| UK and Europe — SHEL.LSE, VOD.LSE, BMW.XETRA, SAP.XETRA, AIR.PA, NESN.SW, NOVO-B.CO | Mostly present | **Almost always null** (12 of 47 on SHEL, none on the rest) | Mostly present | Mostly present               |
| Hong Kong — 0700.HK                                                                 | 12 of 14       | None                                                        | 12 of 14       | 12 of 14                     |
| Australia — BHP.AU                                                                  | None           | None                                                        | Complete       | Complete                     |
| Brazil — PETR4.SA                                                                   | None           | None                                                        | Complete       | None                         |
| Korea — 005930.KO                                                | None           | None                                                        | None           | None                         |

So treat declarationDate, recordDate, paymentDate and period as optional fields rather than guaranteed ones, and null-check them before you use them in a join. Coverage is best on US and Canadian names, thinnest on the Indian and Korean exchanges.

**On the LSE the dividend currency is not the quote currency.** London tickers are quoted in pence — the Fundamentals API reports their currency as GBX — while dividends come back in **pounds**. Shell trades around 3,650 pence a share while its latest dividend reads 0.28915 GBP; AstraZeneca trades around 12,100 against a dividend of 0.795 GBP; Vodafone around 130 against 0.02044 GBP. Dividing one by the other without converting gives a yield that is wrong by a factor of **100**. Always read the currency field and compare it against the instrument’s quote currency before you divide.

## Historical Splits API

```
https://eodhd.com/api/splits/{SYMBOL}?api_token=YOUR_API_TOKEN&fmt=json
```

The splits endpoint takes exactly the same parameters as the dividends endpoint — the same symbol format, the same inclusive from and to, the same case-sensitive fmt defaulting to csv — and costs the same single API call.

#### Request Example

 

 

```
https://eodhd.com/api/splits/AAPL.US?from=2000-01-01&api_token=YOUR_API_TOKEN&fmt=json
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/splits/AAPL.US?from=2000-01-01&api_token=YOUR_API_TOKEN&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/splits/AAPL.US?from=2000-01-01&api_token=YOUR_API_TOKEN&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

#### Response Example

```
[
    {
        "date": "2000-06-21",
        "split": "2.000000/1.000000"
    },
    {
        "date": "2005-02-28",
        "split": "2.000000/1.000000"
    },
    {
        "date": "2014-06-09",
        "split": "7.000000/1.000000"
    },
    {
        "date": "2020-08-31",
        "split": "4.000000/1.000000"
    }
]
```

#### Response Fields

| Field | Type   | Description                                                                        | In CSV?              |
| ----- | ------ | ---------------------------------------------------------------------------------- | -------------------- |
| date  | date   | Ex-split date — the first session the price reflects the new share count           | Yes, as Date         |
| split | string | Ratio as two fixed-point numbers separated by a slash, new shares first. See below | Yes, as Stock Splits |

### Reading the split ratio

The string is **new over old**: how many shares you end up with, over how many you started with. Divide the first number by the second and you get the factor the share count is multiplied by — and the factor the price is divided by.

| Ticker and date            | split              | What happened                                           |
| -------------------------- | ------------------ | ------------------------------------------------------- |
| NVDA.US, 10 June 2024      | 10.000000/1.000000 | 10-for-1 forward split: ten new shares for each old one |
| TSLA.US, 31 August 2020    | 5.000000/1.000000  | 5-for-1 forward split                                   |
| NVDA.US, 11 September 2007 | 3.000000/2.000000  | 3-for-2: the share count rises by half                  |
| GE.US, 2 August 2021       | 1.000000/8.000000  | **Reverse** 1-for-8: eight old shares become one        |
| C.US, 9 May 2011           | 1.000000/10.000000 | Reverse 1-for-10                                        |
| AIG.US, 1 July 2009        | 1.000000/20.000000 | Reverse 1-for-20                                        |

A numerator larger than the denominator is a forward split; smaller is a reverse split.

**Do not assume the ratio is a tidy pair of small integers.** The same field also carries stock dividends, spin-off adjustments and capital reorganisations, and those produce ratios that look nothing like 2-for-1\. Real examples from the feed: GE.US on 26 February 2019 returns 104.000000/100.000000, and again 1281.000000/1000.000000 on 4 January 2023; Ford on 8 April 1998 returns 10000.000000/6641.000000 and on 3 August 2000 returns 1748175.000000/1000000.000000; BMW.XETRA on 23 August 1999 returns 71371.000000/2745.000000\. Parse the string by splitting on the slash and dividing the two numbers as floats. Pattern-matching for a leading integer, or reading only the numerator, will corrupt your adjustment factors.

## Dates, formats and error handling

Both endpoints share one date parser and one error surface. The behaviour below was measured on both.

**Both bounds are inclusive.** Apple’s dividend of 11 May 2026 is returned by a request with from and to both set to 2026-05-11, and disappears when both are moved to 2026-05-12.

**The date parser is lenient, and that is the danger.** Values like 2020/01/01, 20200101, 2020-1-1 and 2020-01-01T00:00:00 are all accepted and all resolve to 1 January 2020\. But a value it cannot read is not rejected either — it silently produces an **empty array with HTTP 200**. A US-style from=01/01/2020 returns no rows at all, and so does the impossible from=2020-13-45\. There is no validation error to catch, so a date-format bug in your client looks exactly like a company that never paid a dividend.

An empty array is ambiguous and it is worth knowing the four things it can mean: the company genuinely has no such events (Tesla and Berkshire Hathaway both return an empty dividend array), the window you asked for contains none (Alphabet returns nothing for dividends before 2024), the instrument has no corporate actions by nature (crypto, forex, indices and government bonds all return an empty array rather than an error), or **your date failed to parse**. Only the last of those is a bug on your side, and the response looks identical in all four cases. Validate your dates before you send them.

#### Status codes

| Code | Body                                | When                                                                                                              |
| ---- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 200  | Array of records, or an empty array | Success. An empty array is a success, not an error                                                                |
| 401  | Unauthenticated                     | The api\_token parameter is missing                                                                               |
| 403  | Forbidden                           | Your plan or your token does not cover this ticker — this is what the demo token returns outside its allowed list |
| 404  | Symbol not found                    | The ticker is not in our database. Still billed as one API call                                                   |

[Sign up & Get Data](https://eodhd.com/register)

## Coverage and depth of history

Both feeds follow the equity universe: stocks and funds on the exchanges listed by the [Exchanges API](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours), across the US, Canada, Europe, Asia, Australia and Latin America. ETFs and mutual funds are included and distribute normally — Vanguard Total Stock Market pays back to 2001 in the feed, and the SPDR S&P 500 ETF returns a full record set. Instruments that cannot have corporate actions — crypto, forex, indices, government bonds — return an empty array rather than an error, which makes them safe to include in a bulk loop.

On depth, nothing in our sampling predates **1970**, and several of the oldest US payers start within the first half of that year, which suggests the dataset floor rather than the companies’ own first payments. Typical full histories: Coca-Cola 226 dividends from June 1970, Johnson & Johnson 227 from February 1970, McDonald’s 208 from May 1976, Apple 92 from May 1987, Microsoft 91 from February 2003.

## Where to go next

Corporate actions are rarely the whole job. Prices for the same instrument, already split- and dividend-adjusted in the adjusted\_close field, come from the [End-of-Day API](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes) at one call per ticker — if all you need is an adjusted series, you may not need this API at all; you need it when you want the events themselves. Every split and every dividend across a whole exchange on a single date is the [Bulk API](https://eodhd.com/financial-apis/bulk-api-eod-splits-dividends), at 100 calls per exchange. Events that are announced but still ahead — including forthcoming ex-dates — are in the [Calendar API](https://eodhd.com/financial-apis/calendar-upcoming-earnings-ipos-and-splits).

For payout ratios, dividend yield and the rest of the company picture, see [Fundamental Data](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds) — and note that its General.CurrencyCode field is what tells you whether a quote is in pence or pounds. To find valid exchange codes and tickers, use the [Exchanges API](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours). To see how the one-call charge sits against your daily allowance, see [API Limits](https://eodhd.com/financial-apis/api-limits).

Compare plans and find your fit

Free and paid plans for individual and commercial use

[ Go to Pricing ](https://eodhd.com/pricing)
