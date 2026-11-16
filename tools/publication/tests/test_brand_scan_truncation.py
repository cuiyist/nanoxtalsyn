"""Offline HTTP fixtures: truncation retries never waive the exact-byte gate."""
import http.client
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[2] / 'ci/brand_name_scan.py'
spec = importlib.util.spec_from_file_location('brand_scan_truncation', MODULE)
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)
URL = n.NEW_BASE + 'data/fixture.json?n_source=' + 'a' * 40
EXPECTED = b'complete-fixture'
ROW = {'path': 'data/fixture.json', 'bytes': len(EXPECTED), 'sha256': n.digest(EXPECTED)}


class Response(io.BytesIO):
    status = 200

    def __init__(self, body, length=None):
        super().__init__(body)
        self.headers = {} if length is None else {'Content-Length': str(length)}

    def geturl(self):
        return URL


class TruncationTests(unittest.TestCase):
    def test_advertised_full_length_with_early_eof_is_incomplete_read(self):
        with patch.object(n.urllib.request, 'urlopen', return_value=Response(EXPECTED[:3], len(EXPECTED))):
            with self.assertRaises(http.client.IncompleteRead) as raised:
                n.anonymous_bytes(URL, len(EXPECTED))
        self.assertEqual(raised.exception.partial, EXPECTED[:3])
        self.assertEqual(raised.exception.expected, len(EXPECTED) - 3)
        self.assertTrue(n.transient(raised.exception))

    def test_retry_requires_full_matching_response_and_retains_failure(self):
        replies = [Response(EXPECTED[:3], len(EXPECTED)), Response(EXPECTED, len(EXPECTED))]
        sleeps = []
        with patch.object(n.urllib.request, 'urlopen', side_effect=replies) as request:
            raw, receipt = n.read_live(ROW, 'a' * 40, n.anonymous_bytes, sleeps.append)
        self.assertEqual(raw, EXPECTED)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(sleeps, [1])
        self.assertEqual(receipt['attempt_failures'][0]['error_class'], 'IncompleteRead')
        self.assertEqual(receipt['final_outcome'], 'exact_bytes_SHA256_match')

    def test_repeated_truncation_exhausts_original_three_attempt_limit(self):
        replies = [Response(EXPECTED[:3], len(EXPECTED)) for _ in range(3)]
        with patch.object(n.urllib.request, 'urlopen', side_effect=replies) as request:
            raw, receipt = n.read_live(ROW, 'a' * 40, n.anonymous_bytes, lambda _: None)
        self.assertIsNone(raw)
        self.assertEqual(request.call_count, 3)
        self.assertEqual(receipt['attempts'], 3)
        self.assertEqual(len(receipt['attempt_failures']), 3)

    def test_short_complete_or_unproven_response_still_fails_without_retry(self):
        for length in (3, None, 'invalid', len(EXPECTED) + 1):
            with self.subTest(length=length):
                with patch.object(n.urllib.request, 'urlopen', return_value=Response(EXPECTED[:3], length)) as request:
                    raw, receipt = n.read_live(ROW, 'a' * 40, n.anonymous_bytes, lambda _: self.fail('No retry'))
                self.assertIsNone(raw)
                self.assertEqual(request.call_count, 1)
                self.assertEqual(receipt['final_outcome'], 'bytes_or_SHA256_mismatch')

    def test_complete_wrong_or_oversized_bytes_never_retry(self):
        for body in (b'x' * len(EXPECTED), EXPECTED + b'x'):
            with self.subTest(body=body):
                with patch.object(n.urllib.request, 'urlopen', return_value=Response(body, len(body))) as request:
                    raw, receipt = n.read_live(ROW, 'a' * 40, n.anonymous_bytes, lambda _: self.fail('No retry'))
                self.assertIsNone(raw)
                self.assertEqual(request.call_count, 1)
                self.assertFalse(receipt['attempt_failures'][0]['retryable'])

    def test_chunked_incomplete_read_is_transient_but_bounded(self):
        failure = http.client.IncompleteRead(b'chunk', 2)
        with patch.object(n.urllib.request, 'urlopen', side_effect=failure) as request:
            raw, receipt = n.read_live(ROW, 'a' * 40, n.anonymous_bytes, lambda _: None)
        self.assertIsNone(raw)
        self.assertEqual(request.call_count, 3)
        self.assertEqual(receipt['final_outcome'], 'fetch_error')


if __name__ == '__main__':
    unittest.main()
