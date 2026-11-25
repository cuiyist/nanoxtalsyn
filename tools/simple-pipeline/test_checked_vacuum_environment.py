import unittest

from to_site import Builder, checked_vacuum_environment


class TestCheckedVacuumEnvironment(unittest.TestCase):
    step = {'action': 'degas', 'description': 'Degassing under vacuum',
            'quote': 'The mixture was degassed under vacuum.', 'page': 10}

    def test_uses_same_checked_step_and_locator(self):
        self.assertEqual(checked_vacuum_environment(self.step), {'value': 'vacuum', 'page': 10})

    def test_never_infers_from_label_or_nearby_context_alone(self):
        for override in ({'quote': 'The mixture was degassed.'},
                         {'description': 'Degassing'}, {'page': None}, {'action': 'wash'},
                         {'quote': 'The mixture was degassed under vacuum, then backfilled with N2.'}):
            with self.subTest(override=override):
                self.assertIsNone(checked_vacuum_environment({**self.step, **override}))

    def test_converter_keeps_recipe_gas_off_only_the_vacuum_step(self):
        doc = {'id': 'fixture', 'doi': '10.1234/fixture', 'authors': 'Test Author', 'year': 2026}
        recipe = {'atmosphere': {'value': 'N2', 'page': 9}, 'steps': [
            self.step, {'action': 'heat', 'description': 'Heat', 'quote': 'The mixture was heated.', 'page': 9}]}
        pair = {'product': 'CdSe', 'structure': {'composition': {'value': 'CdSe', 'page': 9}}, 'recipe': recipe}
        record = Builder(doc).record(pair, 1)
        a, b = record['operations']
        self.assertEqual((a['environment']['value'], b['environment']['value']), ('vacuum', 'N2'))
        self.assertEqual(a['environment']['evidence'], a['evidence'])


if __name__ == '__main__':
    unittest.main()
