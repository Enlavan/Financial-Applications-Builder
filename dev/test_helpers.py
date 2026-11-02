"""Offline contract tests; run with python -m unittest discover -s dev."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib import error, parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import eodhd_request as c
import financial_checks as f
import market_cap_series as market_cap


class Response:
    status = 200
    headers = {'Content-Type': 'application/json'}
    def __init__(self, body=b'[{"close":100}]'):
        self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, limit): return self.body[:limit]


class Opener:
    def __init__(self, results): self.results, self.calls = iter(results), 0
    def open(self, req, timeout):
        self.calls += 1
        value = next(self.results)
        if isinstance(value, Exception): raise value
        return value


class Tests(unittest.TestCase):
    def test_encoded_filter_and_secret_redaction(self):
        url = c.build_url('id-mapping', {'filter[symbol]':'A&B.US'}, 'a+b/?secret')
        self.assertEqual(parse.parse_qs(parse.urlsplit(url).query)['filter[symbol]'], ['A&B.US'])
        safe = c.redacted_url(url)
        self.assertNotIn('secret', safe)
        self.assertEqual(parse.parse_qs(parse.urlsplit(safe).query)['api_token'], ['REDACTED'])

    def test_host_path_and_token_injection_rejected(self):
        for path in ['https://elsewhere.test/api', '/user', '../user', 'eod//A', 'eod/%2e%2e', 'user?x=1']:
            with self.assertRaises(ValueError): c.build_url(path, {}, 'secret')
        with self.assertRaises(ValueError): c.build_url('user', {}, 'secret', 'elsewhere.test')
        with self.assertRaises(ValueError): c.build_url('user', {'api_token':'x'}, 'secret')
        with self.assertRaises(c.RequestFailure): c.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere.test')

    def test_path_symbols_are_encoded(self):
        url = c.build_url('eod/C&A.XETRA', {}, 'secret')
        self.assertIn('/C%26A.XETRA?', url)
        self.assertEqual(parse.parse_qs(parse.urlsplit(url).query)['api_token'], ['secret'])
        self.assertIn('/Apple%20Inc?', c.build_url('search/Apple Inc', {}, 'secret'))

    def test_market_cap_keeps_observed_values_and_frequency(self):
        rows = market_cap.normalize({'1': {'date':'2025-01-03', 'value':23}, '0': {'date':'2025-01-02','value':20}})
        self.assertEqual(rows, [{'date':'2025-01-02','market_cap':20}, {'date':'2025-01-03','market_cap':23}])
        with self.assertRaises(ValueError): market_cap.normalize({'error':'no data'})

    def test_transient_retry_and_capture(self):
        op = Opener([error.HTTPError('secret-url', 503, 'oops', {}, io.BytesIO()), Response()])
        sleeps = []
        result = c.collect(c.build_url('eod/AAPL.US', {}, 'secret'), opener=op, sleep=sleeps.append)
        self.assertEqual(op.calls, 2)
        self.assertEqual(len(sleeps), 1)
        with tempfile.TemporaryDirectory() as tmp:
            m = c.archive(result, Path(tmp))
            p = Path(tmp) / (m['capture_id']+'.json')
            self.assertNotIn('secret', p.read_text())
            self.assertEqual(json.loads(p.read_text())['bytes'], len(result['body']))

    def test_permanent_failure_no_retry(self):
        op = Opener([error.HTTPError('secret-url', 403, 'secret', {}, io.BytesIO())])
        with self.assertRaises(c.RequestFailure) as caught:
            c.collect('https://eodhd.com/api/user?api_token=secret', opener=op)
        self.assertNotIn('secret', str(caught.exception))
        self.assertEqual(op.calls, 1)

    def test_large_response_rejected(self):
        with self.assertRaises(c.RequestFailure):
            c.collect('https://eodhd.com/api/user', opener=Opener([Response(b'0123456789')]), max_bytes=2)

    def test_long_retry_after_is_deferred(self):
        self.assertIsNone(c.retry_delay({'Retry-After':'1000'}, 0))
        self.assertEqual(c.retry_delay({'Retry-After':'3'}, 0), 3)

    def test_financial_invariants(self):
        f.self_test()


if __name__ == '__main__':
    unittest.main()
