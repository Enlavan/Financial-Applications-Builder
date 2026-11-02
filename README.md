# EODHD Financial Applications Builder

An agent skill for designing and building financial applications with the EODHD API. It connects a user's goal—such as a dividend tracker, investing dashboard or research backtester—to data contracts, implementation recipes, calculation methods and validation checks.

The pack contains instructions and reference material for a coding assistant, plus a small set of Python helpers. It is not a hosted application or an API subscription. The assistant reads the relevant chapters as needed rather than loading the entire library.

## What you can build

| Workflow | Examples |
| --- | --- |
| Investing applications | Portfolio dashboards, watchlists, dividend income trackers, ETF comparison tools |
| Screening and monitoring | Fundamental and technical screens, earnings calendars, price alerts, news monitoring |
| Research systems | Historical data pipelines, security mapping, corporate-action checks, backtests, factor and ML experiments |
| Financial analysis | Company research, valuation models, portfolio risk, performance attribution and scenario analysis |
| Cross-asset analytics | Options research, FX, crypto, macro and rates analysis where the required EODHD data is available |
| AI and delivery | MCP assistants, private research agents, notebooks, spreadsheets, charts and reports |

Start with [SKILL.md](SKILL.md) for the assistant's workflow and reference router. Browse the [build recipes](references/build-recipes.md) for concrete project ideas and the [API index](references/api/index.md) for endpoint references.

## Requirements

- A coding assistant that supports directory-based `SKILL.md` skills, or one that can read these instructions and local references explicitly.
- Python 3.10 or newer for the bundled helpers and offline checks. They use the Python standard library; no package installation is required for those helpers.
- An EODHD API key and access to the endpoints needed by your project. A paid subscription is not required to read the pack or run offline checks. The public `demo` key works only on its supported endpoints and symbols.
- Dependencies such as a web framework, plotting library or database driver are chosen and installed for the application you build; they are not bundled with this skill.

API access and dataset coverage depend on the product and instrument. Review [plans and limits](references/plans-limits.md), [coverage notes](references/coverage-notes.md) and [current EODHD documentation](https://eodhd.com/financial-apis/).

## Installation

Clone or download this repository. The repository root must be the directory containing this README and `SKILL.md`. The skill itself is `SKILL.md`, `LICENSE`, `assets/`, `references/` and `scripts/`; `README.md`, `dev/` and `.github/` are repository tooling and are not installed.

### Claude Code

From the repository root:

```bash
mkdir -p "$HOME/.claude/skills/eodhd-financial-applications-skill"
cp -R SKILL.md LICENSE assets references scripts "$HOME/.claude/skills/eodhd-financial-applications-skill/"
```

For project scope, use `.claude/skills/eodhd-financial-applications-skill/` inside the project. Invoke `/eodhd-financial-applications-skill` or describe a matching task. This is a standalone skill installation; the repository is not a Claude plugin marketplace package.

### Claude apps (claude.ai, Desktop)

Build the skill ZIP (see [Validation and contributions](#validation-and-contributions)) and upload it in the Skills section of Claude's settings; skills there require code execution to be enabled. Code execution reaches `eodhd.com` only if the domain is allowed in its network settings. Without that, connect the EODHD MCP server (`https://mcp.eodhd.com/v2/mcp`) as a custom connector, or Claude will write and explain code without running it against the API. Code execution through the Claude API has no internet access at all.

### Other assistants

Ask the assistant to read `SKILL.md` and follow its links to the relevant local references. Keep the directory structure intact. Installing this pack does not configure an MCP connection; see [AI and MCP integration](references/ai-mcp.md) when that is needed.

## Quick start

Run a request preview without credentials or network access:

```bash
python3 scripts/eodhd_request.py eod/AAPL.US --param from=2025-01-01 --param to=2025-01-31 --dry-run
```

For a live example, use the public demo key with AAPL and retain the response locally:

```bash
export EODHD_API_TOKEN=demo
python3 scripts/eodhd_request.py eod/AAPL.US --param from=2025-01-01 --param to=2025-01-31 --out captures/aapl
```

For your own key, set `EODHD_API_TOKEN` through your environment or secret manager. Do not commit it, include it in prompts, or expose it in browser code. Live requests consume the applicable API allowance. Captures can contain licensed data or account information and are excluded from version control.

## Example prompts

- “Use EODHD Financial Applications Builder to build a private dividend tracker for my ETF portfolio, with a local database and monthly income chart.”
- “Build an EODHD stock screener for US companies with positive free cash flow. Check currencies, missing values and API costs.”
- “Create a backtest data pipeline that stores dated captures and handles splits, dividends and delisted symbols without inventing historical vintages.”
- “Audit my adjusted-price calculations against EODHD raw OHLC, adjusted_close and corporate actions.”
- “Build an earnings dashboard using the EODHD tools available through my MCP connection.”
- “Create a portfolio risk report with reproducible calculations and a clear distinction between observed data and modelling assumptions.”

Specify your intended audience, markets, date range and deliverable when you know them. The assistant should check representative API responses before assuming coverage or access.

## Package layout

```text
SKILL.md              Agent entrypoint and reference router
references/           Workflow chapters, methods, recipes and public API references
assets/               Build specifications, dataset contracts and acceptance cases
scripts/              Request helpers and financial checks (installed with the skill)
dev/                  Tests, release validation and packaging (repository only)
.github/workflows/    Offline continuous integration (repository only)
```

The main collector, `scripts/eodhd_request.py`, makes bounded read-only requests, redacts tokens from request metadata and can preserve raw responses. `scripts/eodhd_client.py` provides a compatibility CLI for endpoint examples. `scripts/financial_checks.py` implements selected deterministic checks; it is not a complete backtesting or risk engine.

## Limits and expectations

- This pack does not include API access, market data or permission to redistribute financial data. Personal and commercial use remain governed by the applicable EODHD terms.
- Availability varies by dataset, exchange, ticker, field and date. A subscription entitlement is not a completeness guarantee.
- Historical API values may be revised. Local captures preserve what you retrieved; they do not recover historical data vintages that EODHD does not supply.
- Raw OHLC, adjusted close and split-adjusted volume have different meanings. The workflows keep those distinctions explicit.
- Trading simulations are separate from broker execution. The pack supplies no order-placement or custody service.
- Embedded API references are a dated snapshot, identified in `SKILL.md`. Check current documentation and actual responses when implementing changing interfaces.
- Offline tests check helper behavior and package integrity. They do not certify all workflow methods, paid API access or end-to-end application behavior.

## Validation and contributions

From the repository root:

```bash
python3 -B dev/validate_release.py
python3 -B -m unittest discover -s dev -v
python3 -B scripts/financial_checks.py --self-test
```

GitHub Actions runs these checks on pushes and pull requests without API credentials or live network tests. When contributing, keep examples synthetic, preserve license notices, update relevant references and tests, and describe any live verification separately from offline checks.

To create the skill ZIP for Claude:

```bash
python3 -B dev/package_release.py --output ../eodhd-financial-applications-skill.zip
```

The packager includes only the skill (`SKILL.md`, `LICENSE`, `assets/`, `references/`, `scripts/`) and excludes this README, `dev/`, `.github/`, Git metadata, caches and local captures. The surrounding research workspace is not part of the release.

## License and data terms

This skill pack is available under the [MIT License](LICENSE), retaining the copyright notice from the EODHD skills on which parts of the API references and client are based.

The license covers the skill instructions, documentation and code. Access to EODHD APIs and use of financial data remain subject to the applicable subscription and data-licensing terms. See [EODHD pricing](https://eodhd.com/pricing), [personal-use terms](https://eodhd.com/financial-apis/terms-conditions) and [licensing guidance](references/licensing.md).
