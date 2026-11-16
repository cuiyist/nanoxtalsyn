"""Synthetic navigation labels; no measured compositions or science are filled."""
import copy
import unittest
from unittest.mock import patch
import to_site


class NmLabelNavigationTests(unittest.TestCase):
    def pair(self, label, value=None):
        return {'product': label, 'structure': {'composition': value},
                'recipe': {'steps': [{'action': 'heat', 'description': 'Synthetic heating fixture', 'page': 2}],
                           'chemicals': []}}

    def record(self, pair):
        return to_site.Builder({'id': 'synthetic', 'doi': '10.1234/synthetic',
                                'authors': 'Fixture', 'year': '2026'}).record(pair, 3)

    def test_nm_label_navigation_never_populates_reported_fields(self):
        for label in ('CdSe420 nm', 'CdSe350 nm', 'CdSe380 nm', 'CdSe350.5 nm'):
            with self.subTest(label=label):
                pair = self.pair(label)
                before = copy.deepcopy(pair)
                record = self.record(pair)
                with patch.object(to_site, '_composition_from', return_value=to_site._formula_token(label)):
                    prior = self.record(pair)
                self.assertEqual(record['material']['formula'], 'CdSe')
                self.assertEqual(record['material']['elements'], ['Cd', 'Se'])
                for key in ('record_id', 'title', 'operations', 'products', 'quality'):
                    self.assertEqual(record[key], prior[key])
                self.assertIsNone(record['products'][0]['composition']['value'])
                self.assertEqual(record['quality']['review_status'], 'source_extracted')
                self.assertEqual(pair, before)

    def test_explicit_reported_compositions_win(self):
        for value in ('CdSe', 'CdSe420', 'CdSe/ZnS', 'unknown material'):
            pair = self.pair('CdSe420 nm', {'value': value, 'page': 4})
            self.assertEqual(to_site._composition_from(pair), to_site.formula_from(value))

    def test_unrelated_formula_labels_and_composites_unchanged(self):
        for label in ('CdSe', 'CdSe3', 'CdSe420', 'CdSe/ZnS', 'CdSe420 nm/ZnS',
                      'CdSe420 nm with ZnS shell', 'CuInS2', 'CsPbBr3',
                      'CdSe420 nM', 'CdSe0 nm', 'CdSe 420 nm', 'Sample B'):
            with self.subTest(label=label):
                pair = self.pair(label)
                prior_candidates = (to_site._embedded_product_formula(pair),
                                    to_site._explicit_compound_list_composition(pair),
                                    to_site._formula_token(label))
                prior = next((value for value in prior_candidates if value is not None), None)
                self.assertEqual(to_site._composition_from(pair), prior)

    def test_missing_and_blank_composition_same_narrow_fallback(self):
        for value in (None, {'value': None}, {'value': ''}, {'value': '  '}):
            self.assertEqual(to_site._composition_from(self.pair('CdSe420 nm', value)), 'CdSe')


if __name__ == '__main__':
    unittest.main()
