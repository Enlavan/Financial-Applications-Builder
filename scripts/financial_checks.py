#!/usr/bin/env python3
"""Small deterministic financial checks. No network or third-party dependencies.

Run --self-test; import the functions into a generated application as needed.
These checks detect inconsistencies, not authoritative replacement prices.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import math


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def adjusted_ohlc(row):
    close, adj = row.get('close'), row.get('adjusted_close')
    if not finite(close) or not finite(adj) or close <= 0 or adj <= 0:
        raise ValueError('Positive finite close and adjusted_close are required.')
    factor = adj / close
    out = {'factor': factor, 'adjusted_close': adj}
    for key in ('open', 'high', 'low'):
        val = row.get(key)
        # Keep unavailable/zero equity fields missing, never manufacture a price.
        out['adjusted_' + key] = val * factor if finite(val) and val > 0 else None
    return out


def check_equity_bar(row):
    issues = []
    for key in ('open', 'high', 'low', 'close'):
        val = row.get(key)
        if val is None:
            issues.append(f'{key}:missing')
        elif not finite(val):
            issues.append(f'{key}:nonfinite')
        elif val <= 0:
            issues.append(f'{key}:nonpositive-or-unavailable')
    if all(finite(row.get(k)) and row[k] > 0 for k in ('open', 'high', 'low', 'close')):
        if not row['low'] <= min(row['open'], row['close']) <= max(row['open'], row['close']) <= row['high']:
            issues.append('ohlc:inconsistent-range')
    vol = row.get('volume')
    if vol is None:
        issues.append('volume:missing')
    elif not finite(vol) or vol < 0:
        issues.append('volume:invalid')
    return issues


def eligible_fact(*, observed_version_at, available_at, decision_at, identity_valid,
                  parents_available_at=()):
    """For a forward archive: all times must be known timezone-aware instants."""
    times = [observed_version_at, available_at, decision_at, *parents_available_at]
    if any(not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None for t in times):
        return False
    return bool(identity_valid and observed_version_at <= decision_at and available_at <= decision_at
                and all(t <= decision_at for t in parents_available_at))


def brinson_fachler(portfolio_weights, benchmark_weights, portfolio_returns, benchmark_returns):
    arrays = [portfolio_weights, benchmark_weights, portfolio_returns, benchmark_returns]
    if not arrays[0] or len({len(a) for a in arrays}) != 1:
        raise ValueError('Equal-length nonempty sector arrays are required.')
    if not all(finite(v) for a in arrays for v in a):
        raise ValueError('Finite numeric inputs are required.')
    if not all(math.isclose(sum(a), 1, abs_tol=1e-9) for a in arrays[:2]):
        raise ValueError('This implementation requires fully invested weights summing to one.')
    wp, wb, rp, rb = arrays
    total_b = sum(w * r for w, r in zip(wb, rb))
    total_p = sum(w * r for w, r in zip(wp, rp))
    allocation = sum((a-b)*(r-total_b) for a,b,r in zip(wp,wb,rb))
    selection = sum(b*(p-r) for b,p,r in zip(wb,rp,rb))
    interaction = sum((a-b)*(p-r) for a,b,p,r in zip(wp,wb,rp,rb))
    return dict(allocation=allocation, selection=selection, interaction=interaction,
                active_return=total_p-total_b, residual=total_p-total_b-allocation-selection-interaction)


def self_test():
    from datetime import timedelta, timezone
    bar = dict(open=100., high=110., low=90., close=105., adjusted_close=52.5, volume=0)
    assert check_equity_bar(bar) == []
    assert adjusted_ohlc(bar)['adjusted_high'] == 55
    assert 'ohlc:inconsistent-range' in check_equity_bar(dict(bar, open=80))
    assert adjusted_ohlc(dict(bar, open=0))['adjusted_open'] is None
    try:
        adjusted_ohlc(dict(bar, close=0))
        raise AssertionError('Zero close accepted')
    except ValueError:
        pass
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    kwargs = dict(observed_version_at=now, available_at=now, decision_at=now, identity_valid=True)
    assert eligible_fact(**kwargs)
    assert not eligible_fact(**dict(kwargs, available_at=now + timedelta(seconds=1)))
    assert not eligible_fact(**dict(kwargs, observed_version_at=None))
    assert not eligible_fact(**kwargs, parents_available_at=[now + timedelta(days=1)])
    a = brinson_fachler([.35,.65],[.25,.75],[.15,.08],[.12,.06])
    assert math.isclose(a['active_return'], .0295)
    assert abs(a['residual']) < 1e-12
    print('PASS: adjustment, null/zero handling, OHLC range, temporal eligibility, attribution identity')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        parser.print_help()
