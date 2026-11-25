import copy
import unittest

from mattersyn_simple import has_misattributed_optical_size, public_document


class OpticalSizeProjectionTests(unittest.TestCase):
    def setUp(self):
        optical = dict(value=1200, unit='nm', page=4,
                       quote='The absorption edge was observed near 1200 nm.')
        self.structure = {'size': dict(optical), 'absorption_peak': optical}

    def test_same_optical_evidence_is_not_particle_size(self):
        before = dict(values_kept=2, pairs=[{'structure': self.structure}])
        exact = copy.deepcopy(before)
        result = public_document(before)
        self.assertTrue(has_misattributed_optical_size(self.structure))
        self.assertEqual(before, exact)
        self.assertEqual(result['values_kept'], 1)
        self.assertNotIn('size', result['pairs'][0]['structure'])
        self.assertEqual(result['pairs'][0]['structure']['absorption_peak'],
                         dict(value=1200, unit='nm', page=4))

    def test_actual_size_evidence_or_different_locator_remains(self):
        for mutation in ('size_method', 'distinct_page', 'actual_size_cue',
                         'distinct_quote', 'other_unit'):
            with self.subTest(mutation=mutation):
                structure = copy.deepcopy(self.structure)
                if mutation == 'size_method':
                    structure['size_method'] = {'value': 'TEM'}
                elif mutation == 'distinct_page':
                    structure['size']['page'] = 5
                elif mutation == 'actual_size_cue':
                    for fact in structure.values():
                        fact['quote'] += ' The reported diameter was also 1200 nm.'
                elif mutation == 'distinct_quote':
                    structure['size']['quote'] = 'A 1200 nm aggregate was observed.'
                else:
                    structure['size']['unit'] = 'Å'
                self.assertFalse(has_misattributed_optical_size(structure))
                result = public_document(dict(values_kept=2, pairs=[{'structure': structure}]))
                self.assertIn('size', result['pairs'][0]['structure'])
                self.assertEqual(result['values_kept'], 2)


if __name__ == '__main__':
    unittest.main()
