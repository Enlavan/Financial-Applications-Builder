# Options chains, volatility and strategy research

> Methods with formulas, steps and acceptance checks: [methods-options-rates-macro](methods-options-rates-macro.md).

Use the current EODHD Marketplace Options APIs for new builds. The separate subscription is not included in All-In-One merely because a legacy options endpoint remains accessible. Read the contracts, underlyings and EOD references for exact filters, pagination and fields. Historical availability starts in the supported dataset period and varies by contract; do not assume a rolling two-year window or index-options coverage.

Coverage facts (product page, docs and support checks, 2026-10): US stocks and ETFs only; end-of-day
chains, one snapshot per trading day after the US close; history from early Q4 2023; about 7,000 underlyings
(`underlying-symbols` returned 7,003 on 2026-10-25), including SPY, QQQ and IWM but no cash-settled index
options (SPX, SPXW, XSP, NDX, RUT, VIX, DJX). Endpoints: `/api/mp/unicornbay/options/{underlying-symbols,contracts,eod}`
with `filter[underlying_symbol]`, `filter[contract]`, `filter[type]`, `filter[exp_date_eq|from|to]`,
`filter[strike_eq|from|to]`, `filter[tradetime_eq|from|to]`, `page[limit]` ≤ 1000, offset ≤ 10,000,
`fields[options-eod]`; `links.next = null` ends paging. 10 calls per request against the product's own
100,000/24 h quota (window starts with the first request); a full-market daily sweep is ~70,000 calls before
pagination. The observation day is the date suffix of the record id (`SPY260408C00653000-2026-04-07`);
`tradetime` is the last trade and can be null or old. Bid and ask timestamps can be expressed in different
time zones — normalize both and verify on a known contract. Holiday rows repeat the prior session. The demo
key covers AAPL. MCP tools: `get_us_options_underlyings`, `get_us_options_contracts`, `get_us_options_eod`.

## Normalize contracts

Key contracts by stable contract identifier plus observation date. Retain underlying, expiration, type, strike, currency, contract size/multiplier, exercise/settlement details if supplied, and adjusted-contract status. Do not assume every option delivers 100 ordinary shares after corporate actions. An ETF option is not interchangeable with a cash-settled index option.

Separate option observation time, last trade time, bid time, ask time and underlying price time. An old last trade compared with today's underlying can appear inconsistent without proving the current quote is wrong. A negative reported intrinsic value or a stale underlying requires investigation; do not silently recompute all fields and overwrite the observation.

## Quote quality

Null bid, zero bid, absent ask, crossed market and wide spread are distinct flags. A null bid with a positive ask can be a one-sided/no-bid quote, but that pattern alone does not prove its cause. Do not convert all nulls to zero or all zeros to null. Inspect sizes and dates, liquidity, moneyness and trade activity.

Do not promise a single snapshot instant or official NBBO/certified execution quality. EOD quotes are research observations. Exclude stale or excessively wide contracts from executable-price studies under an explicit policy; record exclusions.

## Analytics

Compute payoff at expiry from contract terms and net premium; scale by multiplier and quantity. Before expiry, distinguish payoff from modelled mark-to-market P&L. Long calls/puts, verticals, straddles/strangles, calendars and butterflies need leg alignment, fees, assignments and exercise assumptions. A spread's theoretical maximum loss is contingent on contract and execution assumptions.

For Black-Scholes-style calculations, document European exercise assumptions, dividends/yield, risk-free convention, year fraction, volatility units and currency. American options, discrete dividends and adjusted deliverables may require other models. Implied volatility inversion needs a valid price interval and convergence checks; return unavailable when the inputs violate model bounds. Greeks are model- and unit-dependent: report whether vega is per unit or percentage point and theta per day or year.

Path-dependent payoffs (Asian averages, knock-in or knock-out barriers, autocallable-style coupons) have no listed EODHD market. Price them only as labelled model values: Monte Carlo under GBM with the volatility from the chain, a reported standard error, variance reduction and a barrier monitoring rule that matches the user's terms (A12b in [methods-options-rates-macro](methods-options-rates-macro.md)). Convertible bonds, warrants and structured notes: listed warrants can appear as ordinary tickers with EOD prices (suffixes such as `W`/`WT`; a `Warrant` type exists, but warrants are not reliably separated from stocks, so probe each one), but their terms are user-supplied. Those terms include the conversion ratio, strike, expiry, call and put schedules, and reset or anti-dilution clauses. EODHD does not provide conversion premia, issuer terms sheets or credit spreads for these instruments.

Construct a volatility surface only from a consistently filtered chain. Check monotonicity/convexity/calendar relationships with appropriate exercise assumptions; a violation flags data/model inconsistency, not guaranteed arbitrage. Interpolation is estimated data and should remain labelled.

## Portfolio and backtest use

Aggregate delta/gamma/vega/theta/rho on compatible units. Stress underlying, vol, rates and time jointly; nonlinear risks are not captured by delta alone. Gamma-exposure estimates require positioning/sign assumptions that open interest does not reveal; label them.

Historical option strategy tests need contracts available on each date, expired contracts, corporate-action handling and realistic fills, spreads, assignment and liquidity. Selecting today's chain for a past date introduces survivorship. If required historical fields are absent, deliver a bounded analytics sample rather than a fabricated strategy result.
