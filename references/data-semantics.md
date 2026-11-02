# Prices, dates, units and missingness

## Price basis

EOD OHLC are raw regular-session prices (pre/after-hours never affect daily fields), not adjusted for splits/dividends. `adjusted_close` accounts for both, following the CRSP (Chicago Booth) method that EODHD cites, and is restated over the whole history whenever an action is added or corrected. EOD volume is split-adjusted. Historical intraday OHLC is raw; inspect endpoint-specific session and volume definitions rather than transferring EOD assumptions to every product.

For each day with finite nonzero raw close, `k = adjusted_close / close`; adjusted open/high/low are that day's raw values multiplied by `k`. Do not reuse one date's factor for an entire series. A factor calculation is invalid when close is zero or either input is missing. This reconstruction is a derived current-vintage adjusted series, not original executable prices.

For split-only OHLC use the Technical API's documented `splitadjusted` function or an explicit validated split ledger. For dollar-volume measures pair split-adjusted volume with split-adjusted prices; raw close × split-adjusted volume mixes share units, while total-return adjusted close introduces dividend effects.

## Time model

- EOD `date`: session label, not necessarily an instant at midnight UTC.
- Intraday timestamp: bar start in UTC according to its contract; compute bar end and availability separately.
- Trade/quote time: when the reported observation occurred, distinct from local receipt time.
- Fiscal period end: what economic period a statement describes, not when it was known.
- Filing/publication/disclosure time: available only if supplied and trustworthy; a date without time needs an explicit conservative policy.
- Retrieval time: when this application received the version. Store independently of all above.

Trading calendars need IANA timezone, holidays, half-days, breaks and DST. Do not assume weekdays or fixed UTC offsets. A late observation received now is still an old observation.

## Units and currencies

Normalize minor-unit quotes explicitly: `GBX` (LSE pence) → GBP and `ZAC` (JSE cents) → ZAR each divide by 100. Read the currency per symbol: an exchange can mix units (active LSE lines are a mix of GBX, USD, EUR and GBP). Retain the original code and multiplier. Do not infer a dividend's unit solely from the stock price's unit. Financial statements may use the primary listing's reporting currency or issuer currency. Market cap, enterprise value, EPS, shares, options multiplier and FX all need separate unit checks.

For FX quoted as units of currency B per one A, an amount in A becomes `amount * rate` in B. Invert only when using the reverse pair. Value the asset and FX on compatible dates/times; flag stale FX and use an explicit prior-session policy for holidays. Base-currency return is `(1 + local_return) * (1 + fx_return) - 1` with correctly oriented FX.

## Null, zero and absence

Zero OHLC does not prove a trade at zero. Positive close with missing/zero open, high, low may represent incomplete fields; it does not establish whether close was an actual trade, indicative value or carried reference. Volume zero does not establish that all quote fields are present. Do not relabel an unknown observation as a confirmed no-trade session.

Keep these states separately: no record, null field, invalid numeric value, zero value, unsupported field, no permission, stale record, and confirmed no event where independently established. Do not forward-fill OHLC or financial facts into trading signals as observed data. A display-only carry-forward should be labelled, keep its original timestamp, and be excluded from freshness/execution tests.

## Revision behavior

Historical values may change when corrected. Adjusted history also changes after new corporate actions. Raw OHLC remaining equal while adjusted close changes is not by itself an error. There is no general revision-notification or historical-version API. Capture dates and transformation versions allow local reproducibility from now onward.

Reference examples are not coverage guarantees. Delisted data is available as is, can have gaps and may not be restorable. A maximum advertised history start is not a guarantee for every symbol and interval.
