"""Synthetic transport proofs; no scientific record changes or network calls."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import record_export as export
from catalog_view import record_download_html


class RecordExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name)
        self.rows = [{'record_id': str(i), 'note': 'αβ' * 5, 'value': None} for i in range(4)]
        self.limit = len(export.encode_record(self.rows[0])) * 2

    def build(self):
        return export.write_export(self.data, self.rows, self.limit)

    def save_manifest(self, manifest):
        (self.data / export.MANIFEST).write_text(json.dumps(manifest), encoding='utf-8')

    def test_exact_order_objects_bytes_hashes_and_size_limit(self):
        before = copy.deepcopy(self.rows)
        manifest = self.build()
        self.assertEqual(self.rows, before)
        self.assertEqual([p['path'] for p in manifest['parts']], ['records.part0001.jsonl', 'records.part0002.jsonl'])
        raw = b''.join((self.data / p['path']).read_bytes() for p in manifest['parts'])
        self.assertEqual(raw, b''.join(export.encode_record(r) for r in self.rows))
        self.assertEqual(export.sha(raw), manifest['sha256'])
        self.assertEqual(export.read_export(self.data), self.rows)
        self.assertTrue(all(p['bytes'] <= self.limit for p in manifest['parts']))
        self.assertFalse((self.data / 'records.jsonl').exists())

    def test_single_and_empty_exports(self):
        for rows in (self.rows, []):
            export.write_export(self.data, rows)
            self.assertEqual(export.read_export(self.data), rows)
            self.assertTrue((self.data / 'records.jsonl').exists())

    def test_legacy_bom_export(self):
        (self.data / 'records.jsonl').write_text(json.dumps(self.rows[0]) + '\n', encoding='utf-8-sig')
        self.assertEqual(export.read_export(self.data), self.rows[:1])

    def test_deterministic_parts_and_manifest(self):
        self.assertEqual(export.plan_export(self.rows, self.limit), export.plan_export(iter(self.rows), self.limit))

    def test_oversized_record_rejected_before_any_write(self):
        with self.assertRaisesRegex(ValueError, 'One record exceeds'):
            export.write_export(self.data, self.rows, 1)
        self.assertEqual(list(self.data.iterdir()), [])

    def test_duplicate_or_nonfinite_record_rejected_before_any_write(self):
        for rows in ([self.rows[0]] * 2, [{'record_id': 'x', 'value': float('nan')}], [{}]):
            with self.assertRaises(ValueError):
                export.write_export(self.data, rows)
        self.assertEqual(list(self.data.iterdir()), [])

    def test_stale_monolith_fails_without_deleting_it(self):
        old = self.data / 'records.jsonl'; old.write_bytes(b'prior')
        with self.assertRaisesRegex(ValueError, 'Stale record'):
            self.build()
        self.assertEqual(old.read_bytes(), b'prior')
        self.assertEqual(list(self.data.iterdir()), [old])

    def test_truncated_or_tampered_part_fails(self):
        manifest = self.build(); leaf = self.data / manifest['parts'][0]['path']
        raw = leaf.read_bytes(); leaf.write_bytes(raw[:-1])
        with self.assertRaisesRegex(ValueError, 'size differs'): export.read_export(self.data)
        leaf.write_bytes(b'x' + raw[1:])
        with self.assertRaisesRegex(ValueError, 'SHA differs'): export.read_export(self.data)

    def test_missing_extra_reordered_and_unsafe_parts_fail(self):
        original = self.build()
        for paths in (list(reversed(original['parts'])), original['parts'][:1], [{**original['parts'][0], 'path': '../records.jsonl'}], original['parts'] * 2):
            manifest = {**original, 'parts': paths}; self.save_manifest(manifest)
            with self.assertRaises(ValueError): export.read_export(self.data)
        self.save_manifest(original)
        (self.data / 'records.part0003.jsonl').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'Missing or stale'): export.read_export(self.data)

    def test_aggregate_and_part_counts_and_hashes_fail_closed(self):
        original = self.build()
        for field, value in [('record_count', 2), ('bytes', 0), ('sha256', '0' * 64), ('schema', 'unknown')]:
            self.save_manifest({**original, field: value})
            with self.assertRaises(ValueError): export.read_export(self.data)
        wrong = copy.deepcopy(original); wrong['parts'][0]['record_count'] += 1; self.save_manifest(wrong)
        with self.assertRaisesRegex(ValueError, 'part count'): export.read_export(self.data)

    def test_reading_shards_without_manifest_cannot_fallback(self):
        (self.data / 'records.part0001.jsonl').write_bytes(b'{}\n')
        with self.assertRaisesRegex(ValueError, 'lacks its manifest'): export.read_export(self.data)

    def test_download_links_expose_every_part_and_no_false_full_file(self):
        manifest = self.build(); html = record_download_html({'record_export': manifest})
        self.assertNotIn('href="data/records.jsonl"', html)
        self.assertIn('id="record-export-download"', html)
        for part in manifest['parts']: self.assertIn('href="data/' + part['path'] + '"', html)
        self.assertIn('href="data/records.jsonl"', record_download_html({}))


if __name__ == '__main__':
    unittest.main()
