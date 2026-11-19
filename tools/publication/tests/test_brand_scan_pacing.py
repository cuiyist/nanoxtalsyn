"""Synthetic transport clocks only: no network, papers or publication credit."""
import importlib.util
from pathlib import Path
import unittest
import urllib.error

MODULE = Path(__file__).resolve().parents[2] / 'ci/brand_name_scan.py'
spec = importlib.util.spec_from_file_location('paced_brand_scan', MODULE)
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)


class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        assert seconds > 0
        self.sleeps.append(seconds)
        self.now += seconds


class PacingTests(unittest.TestCase):
    def test_ordinary_probe_uses_four_then_two_starts_per_second(self):
        clock, starts = Clock(), []
        response = object()
        def fetch(req, timeout):
            self.assertEqual(timeout, 60)
            starts.append((req, clock.now))
            if req == 'b':
                raise urllib.error.HTTPError(req, 429, 'limited', {'Retry-After': '90'}, None)
            return response
        paced = n.PacedAnonymousFetch(fetch, clock.time, clock.sleep, initial_rps=4, throttled_rps=2)
        self.assertIs(paced('a',60),response)
        with self.assertRaises(urllib.error.HTTPError): paced('b',60)
        self.assertIs(paced('c',60),response)
        self.assertIs(paced('d',60),response)
        self.assertEqual(starts,[('a',0),('b',.25),('c',90.25),('d',90.75)])

    def test_out_of_window_retry_after_blocks_other_workers(self):
        clock, starts = Clock(), []
        def fetch(url, expected):
            starts.append(url)
            raise urllib.error.HTTPError(url, 429, 'limited', {'Retry-After': '3601'}, None)
        paced = n.PacedAnonymousFetch(fetch, clock.time, clock.sleep)
        for url in ('a','b'):
            with self.assertRaisesRegex(ValueError,'bounded publisher'): paced(url,1)
        self.assertEqual(starts,['a'])

    def test_request_budget_is_shared_across_distinct_urls_and_retries(self):
        clock = Clock()
        starts = []
        def fetch(url, expected):
            starts.append((url, clock.now))
            return b'x'
        paced = n.PacedAnonymousFetch(fetch, clock.time, clock.sleep)
        for url in ('a', 'b', 'a', 'c'):
            self.assertEqual(paced(url, 1), b'x')
        self.assertEqual([x[0] for x in starts], ['a', 'b', 'a', 'c'])
        for before, after in zip(starts, starts[1:]):
            self.assertGreaterEqual(after[1] - before[1], 0.05 - 1e-12)
        self.assertEqual(paced.receipt()['requests_started'], 4)

    def test_429_pauses_next_unrelated_url_and_reduces_rate(self):
        clock = Clock()
        starts = []
        def fetch(url, expected):
            starts.append(clock.now)
            if len(starts) == 1:
                raise urllib.error.HTTPError(url, 429, 'limited', {'Retry-After': '90'}, None)
            return b'x'
        paced = n.PacedAnonymousFetch(fetch, clock.time, clock.sleep)
        with self.assertRaises(urllib.error.HTTPError):
            paced('https://example.invalid/a', 1)
        self.assertEqual(paced('https://example.invalid/b', 1), b'x')
        paced('https://example.invalid/c', 1)
        self.assertEqual(starts, [0.0, 90.0, 90.1])
        self.assertEqual(paced.receipt()['HTTP_429_responses'], 1)

    def test_429_minimum_and_http_date(self):
        error = urllib.error.HTTPError('x', 429, '', {'Retry-After': 'Thu, 01 Jan 1970 00:02:00 GMT'}, None)
        self.assertEqual(n.retry_after_seconds(error, lambda: 10), 110)
        for header in ('garbage', '-1', 'NaN', ''):
            error.headers = {'Retry-After': header}
            self.assertEqual(n.retry_after_seconds(error), 0)
        error.headers = {'Retry-After': '3601'}
        with self.assertRaisesRegex(ValueError, 'bounded publisher'):
            n.retry_after_seconds(error)

    def test_complete_three_attempt_failure_still_fails_and_preserves_all_errors(self):
        clock = Clock()
        def fetch(url, expected):
            raise urllib.error.HTTPError(url, 429, 'limited', {}, None)
        paced = n.PacedAnonymousFetch(fetch, clock.time, clock.sleep)
        raw, report = n.read_live({'path': 'a.json', 'bytes': 1, 'sha256': n.digest(b'x')},
                                  'a' * 40, paced, clock.sleep)
        self.assertIsNone(raw)
        self.assertEqual(report['attempts'], 3)
        self.assertEqual([x['http_status'] for x in report['attempt_failures']], [429] * 3)
        self.assertEqual(paced.receipt()['requests_started'], 3)
        self.assertEqual(clock.now, 120)

    def test_404_and_wrong_bytes_cannot_become_success(self):
        for mode in ('404', 'bytes'):
            clock = Clock()
            def fetch(url, expected):
                if mode == '404':
                    raise urllib.error.HTTPError(url, 404, 'missing', {}, None)
                return b'wrong'
            paced = n.PacedAnonymousFetch(fetch, clock.time, clock.sleep)
            raw, report = n.read_live({'path': 'a.json', 'bytes': 1, 'sha256': n.digest(b'x')},
                                      'a' * 40, paced, clock.sleep)
            self.assertIsNone(raw)
            self.assertEqual(report['attempts'], 1)
            self.assertEqual(paced.receipt()['requests_started'], 1)


if __name__ == '__main__':
    unittest.main()
