#!/usr/bin/env python3
"""Fetch observed historical market cap; never back-project today's shares.

Uses the bounded EODHD transport. Actual coverage/frequency is ticker-specific.
"""
import argparse
import csv
import io
import json
import os
import sys
from eodhd_request import build_url, collect, RequestFailure

def normalize(data):
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    if isinstance(data, dict):
        if not all(str(k).isdigit() for k in data):
            raise ValueError("Unexpected market-cap response envelope.")
        data = list(data.values())
    if not isinstance(data, list):
        raise ValueError("Expected market-cap observations.")
    rows = []
    for r in data:
        if not isinstance(r, dict) or "date" not in r or "value" not in r:
            raise ValueError("Unexpected market-cap row schema.")
        rows.append({"date": r["date"], "market_cap": r["value"]})
    return sorted(rows, key=lambda r: r["date"])

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbol", required=True)
    p.add_argument("--from-date", required=True)
    p.add_argument("--to-date", required=True)
    p.add_argument("--method", choices=["api"], default="api")
    p.add_argument("--csv", action="store_true")
    args = p.parse_args()
    try:
        url = build_url("historical-market-cap/" + args.symbol,
                        {"from": args.from_date, "to": args.to_date}, os.getenv("EODHD_API_TOKEN", ""))
        rows = normalize(json.loads(collect(url)["body"]))
        if args.csv:
            w = csv.DictWriter(sys.stdout, fieldnames=["date", "market_cap"])
            w.writeheader(); w.writerows(rows)
        else:
            print(json.dumps({"symbol":args.symbol, "frequency":"inspect returned dates", "series":rows}, indent=2))
        return 0
    except (ValueError, RequestFailure) as exc:
        print(str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
