import hashlib
import unittest
from chemical_name_card_identity import name_card_id


def slug(name, length):
    return 'same-truncated-label'


class NameCardTests(unittest.TestCase):
    def test_old_unused_id_is_retained(self):
        self.assertEqual(name_card_id('A', [], slug), 'name-card-same-truncated-label')

    def test_same_printed_name_keeps_existing_id(self):
        rows = [{'id': 'name-card-same-truncated-label', 'name': ' A   B '}]
        self.assertEqual(name_card_id('A B', rows, slug), rows[0]['id'])

    def test_distinct_name_gets_deterministic_suffix(self):
        rows = [{'id': 'name-card-same-truncated-label', 'name': 'A'}]
        result = name_card_id('B', rows, slug)
        self.assertEqual(result, rows[0]['id'] + '-' + hashlib.sha256(b'B').hexdigest()[:12])
        self.assertEqual(rows, [{'id': 'name-card-same-truncated-label', 'name': 'A'}])

    def test_formula_case_is_not_equated(self):
        rows = [{'id': 'name-card-same-truncated-label', 'name': 'CO'}]
        self.assertNotEqual(name_card_id('Co', rows, slug), rows[0]['id'])

    def test_repeat_uses_existing_suffix(self):
        rows = [{'id': 'name-card-same-truncated-label', 'name': 'A'}]
        identifier = name_card_id('B', rows, slug)
        rows.append({'id': identifier, 'name': 'B'})
        self.assertEqual(name_card_id('B', rows, slug), identifier)

    def test_suffix_collision_extends_hash(self):
        rows = [{'id': 'name-card-same-truncated-label', 'name': 'A'}]
        short = name_card_id('B', rows, slug)
        rows.append({'id': short, 'name': 'C'})
        self.assertEqual(name_card_id('B', rows, slug), rows[0]['id'] + '-' + hashlib.sha256(b'B').hexdigest()[:24])

    def test_duplicate_registry_ids_fail_closed(self):
        with self.assertRaises(ValueError):
            name_card_id('A', [{'id': 'x', 'name': 'A'}, {'id': 'x', 'name': 'B'}], slug)

    def test_empty_name_fails_closed(self):
        with self.assertRaises(ValueError):
            name_card_id(' ', [], slug)


if __name__ == '__main__':
    unittest.main()
