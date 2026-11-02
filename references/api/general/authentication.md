> Public API reference snapshot: 2026-10-25. Read [the integration contract](../../api-contract.md) and [plans and limits](../../plans-limits.md) first; they override older examples here.

# EODHD API Authentication

This document explains how to authenticate with the EODHD API.

## Overview

EODHD uses API token-based authentication for all API requests. Authentication is simple and consistent across all endpoints.

## Authentication Method

### API Token

Public REST requests require an API token. The documented query-parameter method is:

```
?api_token=YOUR_API_TOKEN
```

**Example**:
```bash
curl "https://eodhd.com/api/eod/AAPL.US?api_token=demo&fmt=json"
```

### Query parameter and Bearer transport

Authentication headers are not required when using `api_token`. In a demo-key test on
2026-10-25, `Authorization: Bearer <token>` was also accepted. This is an observed
alternative, not evidence that every endpoint, host or WebSocket accepts the same
transport. Check the current endpoint contract before relying on it. The bundled
request collector uses the documented query parameter and redacts it from metadata.

Do not assume support for `X-API-Key` or HTTP Basic authentication. Use one token
transport per request, keep credentials server-side, and redact headers as well as
URLs from logs. See [the integration contract](../../api-contract.md).

## Getting Your API Token

### Step 1: Sign Up

Register for an account at:
- **Website**: https://eodhd.com/register

Choose a plan:
- **Free Tier**: Limited API calls, delayed data
- **Paid Plans**: Increased limits, real-time data, extended history

### Step 2: Access Your Token

After registration:
1. Log in to your EODHD account
2. Open the dashboard at https://eodhd.com/cp/dashboard
3. Copy your API token

**Token Format**:
- Use the token exactly as issued; do not infer access from its shape or length.
- `demo` is the public demo token. `YOUR_API_TOKEN` in examples is a placeholder,
  not a working private credential.

### Step 3: Secure Your Token

**Important Security Practices**:
- ✅ Store in environment variables
- ✅ Use secrets management (AWS Secrets Manager, Azure Key Vault, etc.)
- ✅ Rotate tokens periodically
- ❌ Never commit tokens to version control
- ❌ Don't share tokens publicly
- ❌ Avoid embedding in client-side code

## Using the API Token

### Command Line (curl)

```bash
# Basic request
curl "https://eodhd.com/api/eod/AAPL.US?api_token=YOUR_TOKEN&fmt=json"

# With environment variable
export EODHD_API_TOKEN="your_token_here"
curl "https://eodhd.com/api/eod/AAPL.US?api_token=${EODHD_API_TOKEN}&fmt=json"
```

### Python

#### Using requests library

```python
import os
import requests

# Store token in environment variable
api_token = os.environ.get('EODHD_API_TOKEN')

# Make request
url = "https://eodhd.com/api/eod/AAPL.US"
params = {
    'api_token': api_token,
    'fmt': 'json'
}
response = requests.get(url, params=params)
data = response.json()
```

#### Using the provided client

```python
import os
# Set environment variable
os.environ['EODHD_API_TOKEN'] = 'your_token_here'

# Use the client (it reads from environment)
# The client automatically includes the token
```

```bash
# Command line with client
export EODHD_API_TOKEN="your_token_here"
python eodhd_client.py --endpoint eod --symbol AAPL.US
```

### JavaScript/Node.js

```javascript
// Using environment variable
const apiToken = process.env.EODHD_API_TOKEN;

// Using fetch
const url = `https://eodhd.com/api/eod/AAPL.US?api_token=${apiToken}&fmt=json`;
fetch(url)
  .then(response => response.json())
  .then(data => console.log(data));

// Using axios
const axios = require('axios');
axios.get('https://eodhd.com/api/eod/AAPL.US', {
  params: {
    api_token: apiToken,
    fmt: 'json'
  }
})
.then(response => console.log(response.data));
```

### PHP

```php
<?php
// Store token in environment
$api_token = getenv('EODHD_API_TOKEN');

// Build URL
$url = "https://eodhd.com/api/eod/AAPL.US?api_token=" . $api_token . "&fmt=json";

// Make request
$response = file_get_contents($url);
$data = json_decode($response, true);
?>
```

### R

```r
# Store token
api_token <- Sys.getenv("EODHD_API_TOKEN")

# Using httr
library(httr)
library(jsonlite)

url <- "https://eodhd.com/api/eod/AAPL.US"
response <- GET(url, query = list(
  api_token = api_token,
  fmt = "json"
))
data <- fromJSON(content(response, "text"))
```

## Demo Token

EODHD provides a `demo` API key for free testing without registration. For a comprehensive guide see [API Authentication & Demo Access Guide](api-authentication-demo-access.md) and the [official EODHD API documentation](https://eodhd.com/financial-apis/).

**Demo Token**: `demo`

**Example**:
```bash
curl "https://eodhd.com/api/eod/AAPL.US?api_token=demo&fmt=json"
```

**Supported Demo Tickers** (work across all relevant main REST API endpoints):

| Asset Class | Ticker(s) |
|-------------|-----------|
| US Stocks | `AAPL.US`, `MSFT.US`, `TSLA.US` |
| ETF | `VTI.US` |
| Mutual Fund | `SWPPX.US` |
| Forex | `EURUSD.FOREX` |
| Cryptocurrency | `BTC-USD.CC` |

**Limitations**:
- Restricted to the 7 demo tickers above — other symbols return plain-text `Unauthenticated`
- Rate-limited (lower request quota than production keys)
- Not suitable for production use
- **WebSockets**: use a separate demo symbol set — `AAPL`, `MSFT`, `TSLA` (stocks), `EURUSD` (forex), `BTC-USD`, `ETH-USD` (crypto) — without exchange suffixes; Marketplace APIs may have their own demo symbols too

**What is fully available with the demo key**:
- Complete historical data (no date restrictions)
- All main REST API features: EOD, intraday, fundamentals, technicals, calendar, etc.
- Full data quality (not degraded or sampled)

**Use Cases**:
- Testing API endpoints and data structure
- Learning the API
- Prototyping applications
- Documentation examples

## Environment Variables

### Recommended Setup

**Linux/macOS**:
```bash
# Temporary (current session only)
export EODHD_API_TOKEN="your_token_here"

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export EODHD_API_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

**Windows (Command Prompt)**:
```cmd
# Temporary
set EODHD_API_TOKEN=your_token_here

# Permanent
setx EODHD_API_TOKEN "your_token_here"
```

**Windows (PowerShell)**:
```powershell
# Temporary
$env:EODHD_API_TOKEN = "your_token_here"

# Permanent
[System.Environment]::SetEnvironmentVariable('EODHD_API_TOKEN', 'your_token_here', 'User')
```

### Docker

```dockerfile
# Dockerfile
ENV EODHD_API_TOKEN=${EODHD_API_TOKEN}

# Or at runtime
docker run -e EODHD_API_TOKEN=your_token_here your_image
```

### Environment Files

**.env file** (for local development):
```ini
EODHD_API_TOKEN=your_token_here
```

**Load in Python**:
```python
from dotenv import load_dotenv
load_dotenv()

import os
api_token = os.environ.get('EODHD_API_TOKEN')
```

**Load in Node.js**:
```javascript
require('dotenv').config();
const apiToken = process.env.EODHD_API_TOKEN;
```

## Security Best Practices

### 1. Never Hardcode Tokens

❌ **Bad**:
```python
api_token = "YOUR_API_TOKEN"  # Anti-pattern: never hardcode a private token.
```

✅ **Good**:
```python
api_token = os.environ.get('EODHD_API_TOKEN')
if not api_token:
    raise ValueError("EODHD_API_TOKEN not set")
```

### 2. Use .gitignore

Add to your `.gitignore`:
```
# Environment files
.env
.env.local
.env.*.local

# Token files
*token*
*secret*
*credential*

# IDE files that might contain tokens
.vscode/settings.json
.idea/
```

### 3. Rotate Tokens Regularly

- Change tokens every 3-6 months
- Immediately rotate if token is exposed
- Keep old token active briefly during rotation
- Update all services using the token

### 4. Limit Token Exposure

- Don't log tokens in application logs
- Redact tokens in error messages
- Don't send tokens to client-side code
- Use server-side proxies for web apps

**Example - Log Redaction**:
```python
def log_url(url, token):
    safe_url = url.replace(token, "***REDACTED***")
    print(f"Request: {safe_url}")
```

### 5. Implement Token Validation

```python
def validate_token(token):
    """Validate token format before use."""
    if not token:
        raise ValueError("Token is empty")
    if len(token) < 4:
        raise ValueError("Token too short")
    # Add more validation as needed
    return token
```

### 6. Use Secrets Management

**AWS Secrets Manager**:
```python
import boto3
import json

def get_token():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='eodhd-api-token')
    secret = json.loads(response['SecretString'])
    return secret['EODHD_API_TOKEN']
```

**Azure Key Vault**:
```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

def get_token():
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url="EXTERNAL_LINK_OMITTED", credential=credential)
    secret = client.get_secret("eodhd-api-token")
    return secret.value
```

**HashiCorp Vault**:
```python
import hvac

def get_token():
    client = hvac.Client(url='EXTERNAL_LINK_OMITTED')
    secret = client.secrets.kv.v2.read_secret_version(path='eodhd')
    return secret['data']['data']['api_token']
```

## Authentication Errors

### Invalid or Expired Token

**Error Response**: The API returns plain text `Unauthenticated` (not JSON), regardless of the requested format (`fmt=json` or `fmt=csv`).

**Real example**:
```bash
$ curl "https://eodhd.com/api/exchange-symbol-list/INDX?api_token=INVALID_OR_EXPIRED_TOKEN&fmt=json"
Unauthenticated

$ curl "https://eodhd.com/api/exchange-symbol-list/INDX?api_token=INVALID_OR_EXPIRED_TOKEN&fmt=csv"
Unauthenticated
```

**With a valid token, the same request succeeds**:
```bash
$ curl "https://eodhd.com/api/exchange-symbol-list/INDX?api_token=YOUR_VALID_TOKEN&fmt=json"
[{"Code":"000906","Name":"China Securities 800","Country":"China","Exchange":"INDX","Currency":"CNY","Type":"INDEX","Isin":null},...]
```

**Important**: The error response is always plain text `Unauthenticated` — it is **not** a JSON object. Your code must handle this plain-text response rather than attempting to parse JSON.

**Solutions**:
- Verify token is correct (copy-paste from account dashboard)
- Check for typos or extra spaces
- Ensure token hasn't been revoked or expired
- Try with demo token to confirm API is working

### Missing Token

**Error Response**: Plain text `Unauthenticated`

**Solutions**:
- Add `?api_token=YOUR_TOKEN` to URL
- Check environment variable is set
- Verify token is passed in request

### Rate Limit Exceeded

**Error Response**:
```json
{
  "error": "API rate limit exceeded"
}
```

**HTTP Status**: 429 Too Many Requests

**Solutions**:
- Wait and retry after rate limit resets
- Upgrade to a higher plan
- Implement request throttling
- Use bulk endpoints for large datasets

## Checking Token Status

### User Details Endpoint

Verify your token and check account details using the `/api/user` endpoint:

```bash
curl "https://eodhd.com/api/user?api_token=YOUR_TOKEN"
```

**Request example** (using the public demo token):
```bash
$ curl "https://eodhd.com/api/user?api_token=demo"
```

**Illustrative response** (synthetic account fields; values are not a live demo-account snapshot):
```json
{
  "name": "Example User",
  "email": "demo-user@example.com",
  "subscriptionType": "test",
  "paymentMethod": "Not Available",
  "apiRequests": 19340,
  "apiRequestsDate": "2026-02-16",
  "dailyRateLimit": 100000,
  "extraLimit": 0,
  "inviteToken": null,
  "inviteTokenClicked": 0,
  "subscriptionMode": "demo",
  "canManageOrganizations": false,
  "availableDataFeeds": [],
  "availableMarketplaceDataFeeds": []
}
```

**Illustrative response** (synthetic paid account with Marketplace subscriptions):
```json
{
  "name": "John Doe",
  "email": "researcher@example.com",
  "subscriptionType": "monthly",
  "paymentMethod": "PayPal",
  "apiRequests": 5301,
  "apiRequestsDate": "2026-01-25",
  "dailyRateLimit": 100000,
  "extraLimit": 500,
  "inviteToken": null,
  "inviteTokenClicked": 0,
  "subscriptionMode": "paid",
  "canManageOrganizations": false,
  "availableDataFeeds": [
    "Bulk Splits and Dividends API",
    "News API",
    "EOD Historical Data",
    "Search API",
    "dividends",
    "Dividends Data Feed",
    "Split Data Feed",
    "Live (delayed) Data API",
    "CBOE Data API",
    "Sentiment Data API",
    "Exchanges List API",
    "Daily Treasury Bill Rates",
    "Daily Treasury Real Long-Term Rates, Daily Treasury Long-Term Rates",
    "Daily Treasury Par Yield Curve Rates",
    "Daily Treasury Par Real Yield Curve Rates"
  ],
  "availableMarketplaceDataFeeds": {
    "dailyRateLimit": 100000,
    "requestsSpent": 80,
    "timeToReset": "19:01 GMT+0000",
    "subscriptions": ["US Stock Options Data API"]
  }
}
```

**Response Fields**:
| Field | Description |
|-------|-------------|
| `name` | Account name |
| `email` | Account email |
| `subscriptionType` | Subscription plan type (e.g., `monthly`, `yearly`, `commercial`, `test`) |
| `paymentMethod` | Payment method on file (e.g., `PayPal`, `Stripe`, `Wire`, `Not Available`) |
| `apiRequests` | Number of API requests made on `apiRequestsDate` |
| `apiRequestsDate` | Date for the request count |
| `dailyRateLimit` | Maximum daily API requests allowed for the main subscription |
| `extraLimit` | Remaining amount of additionally purchased API calls |
| `inviteToken` | Invitation token for the affiliate program |
| `inviteTokenClicked` | Number of invite token clicks |
| `subscriptionMode` | Subscription mode: `demo`, `free`, or `paid` |
| `canManageOrganizations` | Whether the account can manage organizations |
| `availableDataFeeds` | Array of available data feed names for the main subscription |
| `availableMarketplaceDataFeeds` | Marketplace subscription info (see below). Empty array `[]` if no Marketplace subscriptions. |

**Marketplace Data Feeds Object** (when Marketplace subscriptions are active):
| Field | Description |
|-------|-------------|
| `dailyRateLimit` | Maximum daily API calls per Marketplace subscription (100,000) |
| `requestsSpent` | Number of Marketplace API calls used in the current 24-hour period |
| `timeToReset` | Time when all Marketplace subscription limits reset (e.g., `19:01 GMT+0000`). This is the same reset time for all Marketplace products on the account — based on when the user first made any Marketplace API request. |
| `subscriptions` | Array of active Marketplace subscription names (e.g., `["US Stock Options Data API"]`) |

> **Note**: Each Marketplace subscription has its own separate 100,000-call daily limit pool, but all Marketplace subscriptions share the same reset time (`timeToReset`). These limits are also separate from the main subscription `dailyRateLimit`. See `rate-limits.md` for full details.

**Use Cases**:
- Verify token is valid
- Check daily API request count vs limit
- Monitor subscription type and mode
- Validate available data feeds

## Multiple Tokens

### Using Different Tokens

If you have multiple EODHD accounts:

```python
# Token per environment
dev_token = os.environ.get('EODHD_DEV_TOKEN')
prod_token = os.environ.get('EODHD_PROD_TOKEN')

# Select based on environment
if os.environ.get('ENV') == 'production':
    api_token = prod_token
else:
    api_token = dev_token
```

### Token Rotation

Implement seamless token rotation:

```python
class TokenManager:
    def __init__(self):
        self.primary = os.environ.get('EODHD_TOKEN_PRIMARY')
        self.secondary = os.environ.get('EODHD_TOKEN_SECONDARY')
        self.current = self.primary

    def get_token(self):
        return self.current

    def rotate(self):
        """Switch to secondary token if primary fails."""
        self.current = self.secondary if self.current == self.primary else self.primary
```

## Troubleshooting

### Issue: Token Not Working

**Checklist**:
1. Token is correct (copy-paste from account)
2. No extra spaces or newlines
3. Environment variable is set correctly
4. Account is active and not suspended
5. Token hasn't been revoked

**Test**:
```bash
# Confirm configuration without printing the token.
python3 -c 'import os; print("EODHD_API_TOKEN is set" if os.environ.get("EODHD_API_TOKEN", "").strip() else "EODHD_API_TOKEN is not set")'

# Test with demo token
curl "https://eodhd.com/api/eod/AAPL.US?api_token=demo&fmt=json"

# Check your account using the bundled collector from the repository root.
# It redacts the request URL and saves the response privately rather than
# printing account information. This response must not be committed.
python3 scripts/eodhd_request.py user --out captures/account-check

# If you see "Unauthenticated" (plain text), your token is invalid
```

### Issue: Token in Version Control

**If token was committed**:
1. Immediately revoke the token in EODHD dashboard
2. Generate a new token
3. Update environment variables everywhere
4. Rewrite git history (if public repo):
   ```bash
   # Use git filter-branch or BFG Repo-Cleaner
   # This is advanced - seek help if unsure
   ```

### Issue: Token Exposed Publicly

**Immediate Actions**:
1. Revoke token immediately in EODHD dashboard
2. Generate new token
3. Check account for unusual activity
4. Change password if account security is compromised
5. Review where token was exposed and remove

## WebSocket Authentication

For real-time WebSocket connections, the same `api_token` is used during the connection handshake. The EODHD WebSocket proxy validates the token to confirm subscription status and permitted access level (markets and symbol count).

See `../endpoints/websockets-realtime.md` for full WebSocket documentation.

## API Key FAQ

### Where to Enter the API Key

EODHD uses a REST API. The API key goes into the URL as a query parameter: `?api_token=YOUR_KEY`. For example, to get EOD data for AAPL: `https://eodhd.com/api/eod/AAPL.US?api_token=YOUR_KEY`

### Does the API Key Change When Switching Subscription?

No. Switching subscription plans within the same account (same email) does not change the API key. A different API key would only result from creating an entirely new account with a different email.

### WKN Lookup

EODHD does not support stock data selection via WKN (Wertpapierkennnummer). WKN is not unique — tickers on several markets can share the same WKN. Use `TICKER + EXCHANGE` format instead.

## Related Resources

- **API Documentation**: https://eodhd.com/financial-apis/
- **Account Settings**: https://eodhd.com/cp/settings
- **Support**: https://eodhd.com/contact
- **Rate Limits**: See `rate-limits.md` in this directory

## Browser and front-end applications

Do not call the API from browser JavaScript with a private token: both query parameters and
authentication headers are visible to the browser user; query tokens can also appear in URL logs. Put a
small server-side adapter (your own backend, serverless function or local process) between the UI and
EODHD, keep the token in an environment variable or secret store, and return only the fields the UI
needs. A private dashboard on your own server is fine under personal use; serving the data to other
people is a licensing question, not a proxy question (see [licensing](../../licensing.md)).
