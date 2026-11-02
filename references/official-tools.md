# Official EODHD tools and connectors — check these first

Before building a collector, add-in or bot, check whether an official EODHD tool already does the job. It
is usually faster for the user, already handles the API's quirks, and is maintained by EODHD. Build custom
code when the tool cannot express the requirement (custom logic, scheduling, storage, joins, tests) — and
say why. Facts here come from the public documentation pages (snapshot 2026-10-25); confirm the current
version, install steps and supported features on the linked page before giving instructions.

Every tool below calls the same API with the user's own key, so it spends calls under the same plan and
limits ([plans-limits.md](plans-limits.md)), and can only return data the plan includes. Personal-use rules
apply to the output ([licensing.md](licensing.md)): a tool that *displays* data to other people (a WordPress
site, a shared Power BI workspace, a public dashboard) needs a commercial licence even though the tool is free.

## Contents

- Choose by need
- Tool notes
- When to build instead
- Acceptance checks

## Choose by need

| User need | Official tool first | Link |
|---|---|---|
| Ask questions about markets in an AI assistant (ChatGPT, Claude, other MCP hosts) | EODHD MCP server, v2 OAuth endpoint `https://mcp.eodhd.com/v2/mcp` | https://eodhd.com/financial-apis/mcp-server-for-financial-data-by-eodhd |
| Spreadsheet formulas for prices, fundamentals, screener, technicals | Excel add-in (Windows); Google Sheets add-on "Financial Data" | https://eodhd.com/financial-apis/excel-financial-add-on-fundamentals-end-of-day-charts · https://eodhd.com/financial-apis/google-sheets-financial-add-in-for-eod-fundamentals-data |
| BI reports | Power BI connector (copy the connector folder into the Power BI Desktop user folder) | https://eodhd.com/financial-apis/power-bi-connector-for-financial-data-apis |
| Bulk download EOD/intraday files without code | Windows and Linux downloader (multi-threaded, proxy support; whole US market in one run) | https://eodhd.com/financial-apis/windows-downloader-end-of-day-data |
| Python research or apps | Official Python library (`pip install eodhd`) | https://eodhd.com/financial-apis/python-financial-libraries-and-code-samples |
| JavaScript/TypeScript (Node, Deno, Bun) | Official Node.js/TypeScript SDK (typed client, retries, rate-limit handling) | https://eodhd.com/financial-apis/node-js-typescript-sdk-for-eodhd-financial-apis |
| R | `eodhdR2` package (≈60 functions returning data frames, call costs documented) | https://eodhd.com/financial-apis/r-library-v-2-for-financial-data-by-eodhd-2024 |
| C#/.NET | Open-source .NET wrapper (EOD, fundamentals, options and more) | https://eodhd.com/financial-apis/c-net-financial-data-api-stock-wrapper |
| Java, F#, PHP/Laravel, MATLAB | Example projects and wrappers | https://eodhd.com/financial-apis/java-stock-api-example · https://eodhd.com/financial-apis/f-sharp-stock-api-example · https://eodhd.com/financial-apis/php-laravel-example · https://eodhd.com/financial-apis/matlab-api-connector-and-example |
| Explore endpoints interactively | Postman collection (all documented endpoints) | https://eodhd.com/financial-apis/postman-financial-data-api-collection |
| Charting/trading platform | NinjaTrader adapter (EOD, intraday and fundamentals; import via NinjaScript) | https://eodhd.com/financial-apis/ninjatrader-adapter-for-eod-intraday-and-fundamentals-data |
| Excel/COM power users | XLQ2 partner integration (stand-alone app feeding Excel and COM clients) | https://eodhd.com/financial-apis/xlq2-integration |
| Prices on a website | WordPress plugin (widgets, converters, fundamentals reports, news feed) | https://eodhd.com/financial-apis/wordpress-financial-stocks-crypto-market-data-plugin |
| Prices in the browser toolbar | Chrome extension (price bar and currency/crypto converter) | https://eodhd.com/financial-apis/real-time-stocks-prices-data-bar-and-crypto-currency-converter-chrome-extension |
| Ready-made strategy alerts in Telegram | EODHDSignals bot (free; watch tickers, buy/sell signals, quick backtests) | https://eodhd.com/financial-apis/eodhdsignals-telegram-bot-user-guide |
| Teach an AI assistant the API | This skill, or the public EODHD Claude skills plugin | https://eodhd.com/financial-apis/eodhd-claude-skills-teach-your-ai-assistant-the-entire-financial-api |

## Tool notes

- **MCP server.** Claude connects only to the v2 OAuth URL (nothing after `/mcp`); some other hosts use the
  older key-in-URL v1. Tool calls cost what the matching endpoint costs and see only what the plan
  includes. Troubleshooting OAuth loops is in [coverage-notes](coverage-notes.md#hosts-tools-and-integrations).
  Build a private MCP server only for custom tools or archive access ([app-ai-patterns](app-ai-patterns.md)).
- **Spreadsheet add-ins.** Each formula cell can be a request: a sheet with 500 tickers × 5 functions
  refreshed hourly spends calls quickly. Share workbooks without the key (add-in settings, not cells).
- **Power BI.** Every refresh spends calls; publishing to a shared workspace shows data to others.
- **Downloader.** Good for no-code bulk history; for daily automation with checks use the pipeline patterns
  in [data-engineering-patterns](data-engineering-patterns.md). The older grey-UI version is unsupported.
- **SDKs.** Same data and limits as direct REST. The Node SDK also runs in browsers — keep the token on a
  server anyway ([applications](applications.md)). Check the SDK's current method names in its repository
  rather than guessing.
- **MATLAB example.** The documented sample URL uses plain HTTP and an old CSV route; use
  `https://eodhd.com/api/eod/{SYMBOL}?fmt=json` with `webread` instead — never send a token over HTTP.
- **WordPress plugin, website widgets.** Display to site visitors is commercial use; the plugin being free
  does not change that.
- **EODHDSignals bot.** A personal convenience for the user; a bot that the user builds and shares with a
  group or channel needs a commercial licence ([licensing](licensing.md)).

## When to build instead

Build (and say why) when the user needs: custom signals or calculations the tool lacks; scheduled jobs
with validation, storage and replay; joins with their own holdings or other EODHD datasets; reproducible
research with versioned captures; an application with users, roles and its own UI; or tests and audit
trails. Otherwise point to the tool, with one sentence on plan requirements and call cost.

## Acceptance checks

- A request for "pull prices into my Google Sheet" is answered with the add-on first, not a script.
- A request for a public website price widget mentions the WordPress plugin **and** the commercial licence.
- A MATLAB answer uses HTTPS and JSON, not the plain-HTTP sample.
- A custom build is justified against the official tool in one sentence.
