> Public documentation snapshot, 2026-10-25. Read [the integration contract](../../api-contract.md).

# Commodities API: Historical Prices for Oil, Gas, Metals & Agriculture (beta) | EODHD APIs Documentation

Source: https://eodhd.com/financial-apis/commodities-api-historical-prices-for-oil-gas-metals-agriculture-beta

 

The EODHD Commodities API provides historical price data for 23 commodity series. It covers energy, metals, and agricultural commodities with daily, weekly, monthly, quarterly, and annual intervals — going back decades for most series.

To quickly try the API, use the demo API key by passing api\_token=demo in your request. The demo key only provides access to WTI (West Texas Intermediate crude oil). Requests for any other commodity code will return a 403 error.

## Data Freshness

New observations appear when each series is published; the lag below is set by the publication schedule of each series, not by your request.

| Category         | Commodities                                                                                   | Data Frequency                                                                            | Typical Lag                                                                                                                   |
| ---------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Energy (daily)   | WTI, BRENT, NATURAL\_GAS, DIESEL\_USGULF, HEATING\_OIL\_NYH, JET\_FUEL\_USGULF, PROPANE\_MBTX | Daily data points, published in **weekly batches** (typically every Tuesday) | **Up to \~1 week.** Although each business day has its own data point, the entire batch for the previous week appears at once |
| Energy (weekly)  | GASOLINE\_US                                                                                  | Weekly (Monday observation)                                                               | \~1 day (published Tuesday)                                                                                                   |
| Energy (monthly) | COAL\_AU, URANIUM                                                                             | Once per month                                                                            | **2–3 weeks after month end.** E.g. March data appears mid-April                                                              |
| Metals           | ALUMINUM, COPPER                                                                              | Once per month                                                              | **2–3 weeks after month end.** E.g. March data appears mid-April                                                              |
| Agricultural     | WHEAT, CORN, SUGAR, COTTON, COFFEE\_MILD\_ARABICA, COFFEE\_ROBUSTAS                           | Once per month                                                              | **2–3 weeks after month end.** E.g. March data appears mid-April                                                              |
| Indices          | ALL\_COMMODITIES, ALL\_COMMODITIES\_PRODUCER, ENERGY\_INDEX, NATGAS\_EU, LNG\_ASIA            | Once per month                                                                            | **2–3 weeks after month end.** E.g. March data appears mid-April                                                              |

**Why does daily energy data have a \~1 week lag?** The daily energy series are published once per week (typically on Tuesdays), even though the underlying data is daily. Each release contains all business-day data points for the previous week. So if today is Thursday, the most recent available data point may be from last Friday or Monday — this is normal for these series. Weekends and US public holidays are skipped — no data points are generated on non-trading days.

## Known Limitations

- **Precious metals removed:** Gold (LBMA), Silver, Platinum, and Palladium series have been discontinued.
- **Monthly series lag:** Metals, agricultural commodities, indices, coal, and uranium are published once per month with a 2–3 week delay after the reference month ends. For example, in mid-May you will typically see data through March — April data may not yet be available.
- **Interval availability:** Not all commodities support all intervals. Daily data is only available for energy commodities. Metals and agricultural commodities are typically monthly only.

## API Endpoint

```
https://eodhd.com/api/commodities/historical/{CODE}
```

**Parameters:**

| Parameter  | Required | Description                                                                         |
| ---------- | -------- | ----------------------------------------------------------------------------------- |
| CODE       | Yes      | Commodity code (e.g., WTI, BRENT, URANIUM) or ALL\_COMMODITIES for the global index |
| api\_token | Yes      | Your EODHD API token                                                                |
| interval   | No       | Data frequency: daily, weekly, monthly (default), quarterly, annual                 |

### Request Example

 

 

```
https://eodhd.com/api/commodities/historical/WTI?api_token=YOUR_API_TOKEN&interval=monthly
```

 for free to get an API token)

```
curl --location "https://eodhd.com/api/commodities/historical/WTI?api_token=YOUR_API_TOKEN&interval=monthly&fmt=json"
```

 for free to get an API token)


 for free to get an API token)

```
import requests

url = f'https://eodhd.com/api/commodities/historical/WTI?api_token=YOUR_API_TOKEN&interval=monthly&fmt=json'
data = requests.get(url).json()

print(data)
```

 for free to get an API token)


 for free to get an API token)

 

## Response Format

The API returns a JSON object with two sections: **meta** (commodity metadata) and **data** (price history).

```json
{
    "meta": {
        "name": "US Regular All Formulations Gas Price",
        "interval": "monthly",
        "unit": "Dollars per Gallon",
        "total": 427
    },
    "data": [
        {"date": "2026-03-01", "value": 3.99},
        {"date": "2026-02-01", "value": 2.937},
        {"date": "2026-01-01", "value": 2.853}
    ]
}
```

| Field          | Type    | Description                                                   |
| -------------- | ------- | ------------------------------------------------------------- |
| meta.name      | string  | Full commodity name                                 |
| meta.interval  | string  | Data frequency (daily, weekly, monthly, quarterly, annual)    |
| meta.unit      | string  | Measurement unit (e.g., Dollars per Barrel, Index 2016 = 100) |
| meta.total     | integer | Total number of data points available                         |
| data\[\].date  | string  | Date in YYYY-MM-DD format                                     |
| data\[\].value | number  | Price or index value                                          |

## Available Commodities

The API covers 23 commodity series across four categories:

### Energy (10 series)

| Code              | Name                                   | Unit                    | Frequency |
| ----------------- | -------------------------------------- | ----------------------- | --------- |
| WTI               | Crude Oil WTI (Cushing, Oklahoma)      | Dollars per Barrel      | Daily     |
| BRENT             | Crude Oil Brent (Europe)               | Dollars per Barrel      | Daily     |
| NATURAL\_GAS      | Henry Hub Natural Gas Spot Price       | Dollars per Million BTU | Daily     |
| GASOLINE\_US      | US Regular All Formulations Gas Price  | Dollars per Gallon      | Weekly    |
| DIESEL\_USGULF    | No. 2 Diesel (US Gulf Coast)           | Dollars per Gallon      | Daily     |
| HEATING\_OIL\_NYH | No. 2 Heating Oil (NY Harbor)          | Dollars per Gallon      | Daily     |
| JET\_FUEL\_USGULF | Kerosene-Type Jet Fuel (US Gulf Coast) | Dollars per Gallon      | Daily     |
| PROPANE\_MBTX     | Propane (Mont Belvieu, Texas)          | Dollars per Gallon      | Daily     |
| COAL\_AU          | Coal (Australian thermal)              | Dollars per Metric Ton  | Monthly   |
| URANIUM           | Uranium (Global Spot Price)            | Dollars per Pound       | Monthly   |

### Metals (2 series)

| Code     | Name                     | Unit                   | Frequency |
| -------- | ------------------------ | ---------------------- | --------- |
| ALUMINUM | Global Price of Aluminum | Dollars per Metric Ton | Monthly   |
| COPPER   | Global Price of Copper   | Dollars per Metric Ton | Monthly   |

### Agricultural (6 series)

| Code                  | Name                                 | Unit                   | Frequency |
| --------------------- | ------------------------------------ | ---------------------- | --------- |
| WHEAT                 | Global Price of Wheat                | Dollars per Metric Ton | Monthly   |
| CORN                  | Global Price of Corn                 | Dollars per Metric Ton | Monthly   |
| SUGAR                 | Global Price of Sugar                | Cents per Pound        | Monthly   |
| COTTON                | Global Price of Cotton               | Cents per Pound        | Monthly   |
| COFFEE\_MILD\_ARABICA | Global Price of Coffee, Mild Arabica | Cents per Pound        | Monthly   |
| COFFEE\_ROBUSTAS      | Global Price of Coffee, Robustas     | Cents per Pound        | Monthly   |

### Indices (5 series)

| Code                       | Name                                  | Unit                    | Frequency |
| -------------------------- | ------------------------------------- | ----------------------- | --------- |
| ALL\_COMMODITIES           | Global Price Index of All Commodities | Index 2016 = 100        | Monthly   |
| ALL\_COMMODITIES\_PRODUCER | Producer Price Index: All Commodities | Index 1982 = 100        | Monthly   |
| ENERGY\_INDEX              | Energy Price Index                    | Index 2016 = 100        | Monthly   |
| NATGAS\_EU                 | Natural Gas Price (EU)                | Dollars per Million BTU | Monthly   |
| LNG\_ASIA                  | LNG Price (Asia)                      | Dollars per Million BTU | Monthly   |

## Quick Start: Python

Fetch the latest WTI crude oil prices:

```python
import requests

API_TOKEN = "YOUR_API_TOKEN"

def get_commodity(code, interval="monthly"):
    url = f"https://eodhd.com/api/commodities/historical/{code}"
    params = {"api_token": API_TOKEN, "interval": interval}
    response = requests.get(url, params=params)
    return response.json()

# Monthly WTI prices
data = get_commodity("WTI")
print(f"Commodity: {data['meta']['name']}")
print(f"Unit: {data['meta']['unit']}")
print(f"Total records: {data['meta']['total']}")

for row in data["data"][:5]:
    print(f"  {row['date']}: ${row['value']}")
```

Output:

```
Commodity: Crude Oil Prices: West Texas Intermediate (WTI) - Cushing, Oklahoma
Unit: Dollars per Barrel
Total records: 483

  2026-03-01: $104.69
  2026-02-01: $66.96
  2026-01-01: $64.5
  2025-12-01: $57.26
  2025-11-01: $58.58
```

## Using Intervals

The **interval** parameter controls the data frequency. Available values: **daily**, **weekly**, **monthly** (default), **quarterly**, **annual**. Not all intervals are available for every commodity — check the series before requesting it.

```python
# Daily WTI prices — much more granular
daily = get_commodity("WTI", interval="daily")
print(f"Daily records: {daily['meta']['total']}")

for row in daily["data"][:5]:
    print(f"  {row['date']}: ${row['value']}")
```

Output:

```
Daily records: 10129

  2026-03-30: $104.69
  2026-03-27: $101.26
  2026-03-26: $96.18
  2026-03-25: $95.82
  2026-03-24: $93.26
```

## Building a Commodity Dashboard

Fetch multiple commodities and compare their recent performance:

```python
import requests

API_TOKEN = "YOUR_API_TOKEN"

def get_commodity(code, interval="monthly"):
    url = f"https://eodhd.com/api/commodities/historical/{code}"
    params = {"api_token": API_TOKEN, "interval": interval}
    return requests.get(url, params=params).json()

commodities = ["WTI", "BRENT", "NATURAL_GAS", "ALUMINUM", "COPPER", "WHEAT"]

print(f"{'Code':<15} {'Name':<45} {'Latest':>10} {'Unit':<25}")
print("-" * 100)

for code in commodities:
    data = get_commodity(code)
    meta = data["meta"]
    latest = data["data"][0] if data["data"] else None

    print(f"{code:<15} {meta['name'][:44]:<45} "
          f"{' + str(latest['value']) if latest else 'N/A':>10} "
          f"{meta['unit']:<25}")
```

Output:

```
Code            Name                                          Latest Unit
--------------------------------------------------------------------------
WTI             Crude Oil Prices: West Texas Intermediate      $104.69 Dollars per Barrel
BRENT           Crude Oil Prices: Brent - Europe                $99.33 Dollars per Barrel
NATURAL_GAS     Henry Hub Natural Gas Spot Price                 $4.38 Dollars per Million BTU
ALUMINUM        Global Price of Aluminum                      $2614.58 Dollars per Metric Ton
COPPER          Global Price of Copper                        $9474.24 Dollars per Metric Ton
WHEAT           Global Price of Wheat                          $249.18 Dollars per Metric Ton
```

## Year-over-Year Comparison

Compare current prices with the same month last year to identify trends:

```python
def yoy_comparison(code):
    """Compare latest monthly value with same month a year ago."""
    data = get_commodity(code, interval="monthly")
    meta = data["meta"]
    records = data["data"]

    if len(records) < 13:
        return None

    current = records[0]
    year_ago = records[12]

    change = ((current["value"] - year_ago["value"]) / year_ago["value"]) * 100

    return {
        "name": meta["name"],
        "unit": meta["unit"],
        "current_date": current["date"],
        "current_value": current["value"],
        "year_ago_date": year_ago["date"],
        "year_ago_value": year_ago["value"],
        "yoy_change_pct": round(change, 1),
    }

energy = ["WTI", "BRENT", "NATURAL_GAS", "GASOLINE_US"]

print(f"{'Commodity':<15} {'Current':>10} {'Year Ago':>10} {'YoY Change':>12}")
print("-" * 50)

for code in energy:
    result = yoy_comparison(code)
    if result:
        direction = "+" if result["yoy_change_pct"] > 0 else ""
        print(f"{code:<15} ${result['current_value']:>8} "
              f"${result['year_ago_value']:>8} "
              f"{direction}{result['yoy_change_pct']}%")
```

## Loading into Pandas DataFrame

For deeper analysis, load commodity data into a Pandas DataFrame:

```python
import pandas as pd

def commodity_to_dataframe(code, interval="monthly"):
    """Fetch commodity data and return as a Pandas DataFrame."""
    data = get_commodity(code, interval=interval)
    df = pd.DataFrame(data["data"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df.attrs["name"] = data["meta"]["name"]
    df.attrs["unit"] = data["meta"]["unit"]
    return df

# Load WTI daily prices
wti = commodity_to_dataframe("WTI", interval="daily")

print(f"{wti.attrs['name']}")
print(f"Date range: {wti.index.min().date()} to {wti.index.max().date()}")
print(f"Records: {len(wti)}")
print(f"\nDescriptive statistics:")
print(wti.describe())

# Calculate 20-day moving average
wti["ma_20"] = wti["value"].rolling(window=20).mean()
print(f"\nLatest value: ${wti['value'].iloc[-1]:.2f}")
print(f"20-day MA: ${wti['ma_20'].iloc[-1]:.2f}")
```

## Correlation Analysis

Compare price movements across commodities to find correlations:

```python
import pandas as pd

codes = ["WTI", "BRENT", "NATURAL_GAS", "COPPER", "ALUMINUM"]

# Fetch all commodities and merge on date
frames = {}
for code in codes:
    df = commodity_to_dataframe(code)
    frames[code] = df["value"]

combined = pd.DataFrame(frames).dropna()

# Calculate monthly returns
returns = combined.pct_change().dropna()

# Correlation matrix
print("Correlation Matrix (Monthly Returns)")
print("=" * 60)
print(returns.corr().round(2).to_string())
```

Output:

```
Correlation Matrix (Monthly Returns)
============================================================
              WTI  BRENT  NATURAL_GAS  COPPER  ALUMINUM
WTI          1.00   0.97         0.38    0.52      0.45
BRENT        0.97   1.00         0.35    0.50      0.44
NATURAL_GAS  0.38   0.35         1.00    0.21      0.18
COPPER       0.52   0.50         0.21    1.00      0.72
ALUMINUM     0.45   0.44         0.18    0.72      1.00
```

WTI and Brent are highly correlated (0.97) as expected. Copper and Aluminum also show strong co-movement (0.72), both being industrial metals sensitive to global manufacturing demand.

## API Endpoints Summary

| Endpoint                                         | Description                                |
| ------------------------------------------------ | ------------------------------------------ |
| GET /api/commodities/historical/{CODE}           | Historical prices for a specific commodity |
| GET /api/commodities/historical/ALL\_COMMODITIES | Global commodity price index               |

All endpoints require authentication via **api\_token** parameter. The Commodities API is available across all plans, including free plan.

[Sign up & Get Data](https://eodhd.com/register)
