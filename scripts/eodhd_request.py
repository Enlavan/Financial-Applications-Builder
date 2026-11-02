#!/usr/bin/env python3
"""Bounded, read-only EODHD collector. Stdlib only; no automatic pagination.

Set EODHD_API_TOKEN in the environment. Use --dry-run to inspect a redacted
request without network access. Captures are private data, not public fixtures.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import random
import re
import sys
import time
from urllib import error, parse, request

HOSTS = {'eodhd.com', 'cboe.eodhd.com'}
RETRYABLE = {429, 500, 502, 503, 504}


class RequestFailure(Exception):
    """Safe error without a credential-bearing request URL."""


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RequestFailure(f'Redirect refused (HTTP {code}); verify the endpoint host/path.')


def build_url(path: str, params: dict, token: str, host: str = 'eodhd.com') -> str:
    if host not in HOSTS:
        raise ValueError('Only the documented EODHD REST hosts are allowed.')
    if not path or not re.fullmatch(r'[\w .,&+\-/]+', path):
        raise ValueError('Use a relative public API path with no URL, query or encoded segments.')
    if path.startswith('/') or '//' in path or any(s in {'.', '..'} for s in path.split('/')):
        raise ValueError('Invalid relative API path.')
    if any(k.lower() in {'api_token', 'token', 'authorization'} for k in params):
        raise ValueError('Supply credentials only through EODHD_API_TOKEN.')
    if not token:
        raise ValueError('EODHD_API_TOKEN is not set.')
    query = {'fmt': 'json', **params, 'api_token': token}
    encoded_path = '/'.join(parse.quote(segment, safe='-_.') for segment in path.split('/'))
    return f'https://{host}/api/{encoded_path}?' + parse.urlencode(query)


def redacted_url(url: str) -> str:
    parts = parse.urlsplit(url)
    pairs = [(k, 'REDACTED' if k.lower() in {'api_token', 'token', 'authorization'} else v)
             for k, v in parse.parse_qsl(parts.query, keep_blank_values=True)]
    return parse.urlunsplit((parts.scheme, parts.netloc, parts.path, parse.urlencode(pairs), ''))


def retry_delay(headers, attempt: int, cap: float = 30.0):
    """Return None when a requested wait exceeds the caller's retry budget."""
    value = headers.get('Retry-After') if headers else None
    if value:
        try:
            wait = max(0.0, float(value))
        except ValueError:
            try:
                dt = parsedate_to_datetime(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                wait = max(0.0, (dt - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                wait = min(cap, 2 ** attempt + random.uniform(0, 0.5))
        return wait if wait <= cap else None
    return min(cap, 2 ** attempt + random.uniform(0, 0.5))


def collect(url, *, attempts=3, timeout=20.0, max_bytes=20_000_000,
            budget=90.0, opener=None, sleep=time.sleep):
    if not 1 <= attempts <= 5 or timeout <= 0 or budget <= 0 or max_bytes <= 0:
        raise ValueError('Invalid request bounds.')
    opener = opener or request.build_opener(NoRedirect())
    started = time.monotonic()
    for attempt in range(attempts):
        remaining = budget - (time.monotonic() - started)
        if remaining <= 0:
            raise RequestFailure('Request time budget exhausted.')
        req = request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'EODHD-Financial-Applications-Builder/1'})
        headers, status = {}, None
        try:
            with opener.open(req, timeout=min(timeout, remaining)) as response:
                body = response.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise RequestFailure('Response exceeds byte limit; narrow the request.')
                # Do not print response values: account endpoints can contain PII.
                return {
                    'body': body,
                    'status': response.status,
                    'content_type': response.headers.get('Content-Type', ''),
                    'attempts': attempt + 1,
                    'retrieved_at': datetime.now(timezone.utc).isoformat(),
                    'request': redacted_url(url),
                }
        except error.HTTPError as exc:
            status, headers = exc.code, exc.headers
            exc.close()
            if status not in RETRYABLE:
                raise RequestFailure(f'HTTP {status}; inspect access, parameters and endpoint documentation.') from None
        except (error.URLError, TimeoutError, ConnectionError):
            pass  # Exception text may contain the original secret-bearing URL.
        if attempt + 1 >= attempts:
            raise RequestFailure(f'Request failed after {attempts} attempts' + (f' (HTTP {status}).' if status else '.'))
        delay = retry_delay(headers, attempt)
        if delay is None or time.monotonic() - started + delay >= budget:
            raise RequestFailure('Retry deferred: server wait exceeds the bounded request budget.')
        sleep(delay)
    raise RequestFailure('Request failed.')


def archive(result, directory: Path):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    body = result['body']
    digest = hashlib.sha256(body).hexdigest()
    capture = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + digest[:12]
    metadata = {k: v for k, v in result.items() if k != 'body'}
    metadata.update(sha256=digest, bytes=len(body), capture_id=capture)
    try:
        parsed = json.loads(body)
        metadata['json_type'] = type(parsed).__name__
        metadata['validation'] = 'json-parsed; dataset schema not yet validated'
    except (ValueError, UnicodeDecodeError):
        metadata['validation'] = 'not-json; inspect content type and endpoint format'
    for suffix, content in [('.body', body), ('.json', json.dumps(metadata, indent=2).encode())]:
        p = directory / (capture + suffix)
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', help='Public relative path, e.g. eod/AAPL.US or id-mapping')
    parser.add_argument('--param', action='append', default=[], metavar='KEY=VALUE')
    parser.add_argument('--host', choices=sorted(HOSTS), default='eodhd.com')
    parser.add_argument('--out', type=Path, help='Private capture directory; required for network calls')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--attempts', type=int, choices=range(1, 6), default=3)
    parser.add_argument('--timeout', type=float, default=20)
    parser.add_argument('--budget', type=float, default=90)
    parser.add_argument('--max-bytes', type=int, default=20_000_000)
    args = parser.parse_args()
    try:
        params = {}
        for item in args.param:
            key, sep, value = item.partition('=')
            if not sep or not key or key in params:
                raise ValueError('Each --param must have a unique nonempty KEY=VALUE.')
            params[key] = value
        token = os.getenv('EODHD_API_TOKEN', 'DRY_RUN' if args.dry_run else '')
        url = build_url(args.path, params, token, args.host)
        if args.dry_run:
            print(redacted_url(url))
            return 0
        if args.out is None:
            raise ValueError('--out is required to retain response evidence.')
        result = collect(url, attempts=args.attempts, timeout=args.timeout,
                         max_bytes=args.max_bytes, budget=args.budget)
        metadata = archive(result, args.out)
        print(json.dumps({k: metadata[k] for k in ('capture_id', 'status', 'bytes', 'sha256', 'validation')}, indent=2))
        return 0
    except (ValueError, RequestFailure) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError:
        print('Cannot write the private capture; check destination permissions and available disk space.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
