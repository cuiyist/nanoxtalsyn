"""Small synthetic registries: formatting changes no rights or provenance."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import register_batch_assets as helper
import test_register_batch_assets as native


class SerializationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.data = {'assets': [{'rights': {'status': 'permission_not_established',
                                           'copyright_permission_verified': False},
                                'title': 'α β', 'unknown_future_field': ['\n', 12, None]}],
                     'other': {'keep': True}}

    def fixture(self, filename='asset-rights-registry.json', ending='\n', crlf=False):
        path = self.folder / filename
        text = json.dumps(self.data, ensure_ascii=False, indent=2) + ending
        if crlf:
            text = text.replace('\n', '\r\n')
        path.write_bytes(text.encode())
        return path

    def test_small_registry_bytes_unchanged(self):
        path = self.fixture()
        self.assertEqual(helper.serialized(path, self.data), path.read_bytes())

    def test_compact_preserves_all_objects_and_utf8(self):
        path = self.fixture()
        before = path.read_bytes()
        with patch.object(helper, 'COMPACT_RIGHTS_THRESHOLD', 1):
            raw = helper.serialized(path, self.data)
        self.assertEqual(json.loads(raw), self.data)
        self.assertLess(len(raw), len(before))
        self.assertIn('α'.encode(), raw)
        self.assertEqual(path.read_bytes(), before)

    def test_crlf_and_terminal_newline_preserved(self):
        path = self.fixture(crlf=True)
        with patch.object(helper, 'COMPACT_RIGHTS_THRESHOLD', 1):
            raw = helper.serialized(path, self.data)
        self.assertTrue(raw.endswith(b'\r\n'))
        self.assertEqual(raw.count(b'\n'), 1)
        self.assertEqual(json.loads(raw), self.data)

    def test_no_terminal_newline_preserved(self):
        path = self.fixture(ending='')
        with patch.object(helper, 'COMPACT_RIGHTS_THRESHOLD', 1):
            raw = helper.serialized(path, self.data)
        self.assertFalse(raw.endswith(b'\n'))
        self.assertEqual(json.loads(raw), self.data)

    def test_other_controls_keep_original_format(self):
        path = self.fixture('public-release-policy.json')
        with patch.object(helper, 'COMPACT_RIGHTS_THRESHOLD', 1), patch.object(helper, 'RIGHTS_BLOB_LIMIT', 1):
            self.assertEqual(helper.serialized(path, self.data), path.read_bytes())

    def test_compact_is_idempotent(self):
        path = self.fixture()
        with patch.object(helper, 'COMPACT_RIGHTS_THRESHOLD', 1):
            raw = helper.serialized(path, self.data)
            path.write_bytes(raw)
            self.assertEqual(helper.serialized(path, self.data), raw)

    def test_size_failure_precedes_any_write(self):
        path = self.fixture()
        before = path.read_bytes()
        with patch.object(helper, 'COMPACT_RIGHTS_THRESHOLD', 1), patch.object(helper, 'RIGHTS_BLOB_LIMIT', 50):
            with self.assertRaisesRegex(ValueError, 'before writing'):
                helper.serialized(path, self.data)
        self.assertEqual(path.read_bytes(), before)


class CompactRegistrationTests(native.RegistrationTest):
    def setUp(self):
        super().setUp()
        self.patcher = patch.object(helper, 'COMPACT_RIGHTS_THRESHOLD', 1)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)


if __name__ == '__main__':
    unittest.main()
