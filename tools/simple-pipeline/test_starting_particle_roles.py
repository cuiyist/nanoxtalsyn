"""Synthetic regression cases for the owner W graph-preservation rule."""
import unittest

from starting_particle_roles import revise, role_for


def record(materials, inputs):
    return {
        'quality': {'review_status':'source_extracted'},
        'material': {'formula':'CdSe/ZnS','architecture':'core_shell','components':['CdSe','ZnS']},
        'materials':[{'id':mid,'name':name,'formula':None,'role':'reagent','identity':{},
                      'quantities':{},'notes':[],'evidence':[]} for mid,name in materials],
        'operations':[{'inputs':inputs,'optional_inputs':inputs}],
        'material_states':[{'parent_ids':inputs}],
        'stocks':[],'condition_options':[],
    }


class ExactGraphTests(unittest.TestCase):
    def test_plural_core_keeps_its_name_evidence_and_exact_graph_links(self):
        original = record([('cores', 'CdSe cores'), ('alias', 'CdSe'),
                           ('reagent', 'CdS precursors')], ['alias', 'reagent', 'cores'])
        original['materials'][0]['evidence'] = [{'id': 'core-locator'}]
        original['materials'][1]['evidence'] = [{'id': 'alias-locator'}]
        changed, ledger = revise(original)
        self.assertEqual([(row['id'], row['role']) for row in changed['materials']],
                         [('cores', 'starting_particles'), ('reagent', 'reagent')])
        self.assertEqual(changed['materials'][0]['evidence'],
                         [{'id': 'core-locator'}, {'id': 'alias-locator'}])
        self.assertEqual(changed['operations'][0]['inputs'], ['cores', 'reagent'])
        self.assertEqual(changed['operations'][0]['optional_inputs'], ['cores', 'reagent'])
        self.assertEqual(changed['material_states'][0]['parent_ids'], ['cores', 'reagent'])
        self.assertEqual(ledger['counts'], {'W1': 2, 'W3': 1})
        self.assertFalse(ledger['holds'])

    def test_plural_shell_description_is_not_a_chemical(self):
        material = {'formula': 'CdSe/ZnS', 'architecture': 'core_shell',
                    'components': ['CdSe', 'ZnS']}
        self.assertEqual(role_for('ZnS shell layers', material), ('omit', 'ZnS'))
        self.assertEqual(role_for('ZnS shells', material), ('omit', 'ZnS'))
        self.assertEqual(role_for('ZnS shells', material, ['Added ZnS nanoparticles.']),
                         ('start', 'ZnS'))

    def test_distinct_powder_and_named_seeds_retain_both_and_bind_specific_alias(self):
        for quote, target in [('CdSe powders were used.', 'powder'),
                              ('The CdSe t-NCs were used.', 'seed')]:
            original=record([('alias','CdSe'),('powder','CdSe powder'),
                             ('seed','CdSe nanocrystal seeds (t-NCs)')],['alias','powder'])
            changed,ledger=revise(original,{'alias':[quote]})
            self.assertEqual([m['id'] for m in changed['materials']],['powder','seed'])
            self.assertTrue(all(m['role']=='starting_particles' for m in changed['materials']))
            self.assertIn(('W3','alias',target), ledger['entries'])
            self.assertEqual(changed['operations'][0]['inputs'],
                             ['powder'] if target=='powder' else ['seed','powder'])

    def test_bare_alias_without_a_unique_match_does_not_merge_input(self):
        original=record([('alias','CdSe'),('powder','CdSe powder'),
                         ('seed','CdSe nanocrystal seeds (t-NCs)')],['alias','powder','seed'])
        changed,ledger=revise(original,{'alias':['CdSe powder and CdSe t-NCs']})
        self.assertNotIn('W3',ledger['counts'])
        self.assertEqual(changed['operations'],original['operations'])
        self.assertEqual(len(changed['materials']),3)
        self.assertEqual(role_for('V2O5 (c.p.)', {'formula':'V2O5'}),('unchanged',None))

    def test_no_w_action_retains_original_input_order_and_repetitions(self):
        original=record([('x','a synthetic solvent')],['x','x'])
        new,ledger=revise(original)
        self.assertEqual(new,original)
        self.assertEqual(ledger['counts'],{})

    def test_merge_only_deduplicates_the_w3_target(self):
        original=record([('a','CdSe'),('b','CdSe core'),('x','a synthetic solvent')],
                        ['b','x','a','x'])
        new,ledger=revise(original)
        self.assertEqual(ledger['counts']['W3'],1)
        for sequence in (new['operations'][0]['inputs'],new['operations'][0]['optional_inputs'],
                         new['material_states'][0]['parent_ids']):
            self.assertEqual(sequence,['a','x','x'])
        self.assertEqual(original['operations'][0]['inputs'],['b','x','a','x'])


if __name__=='__main__':
    unittest.main()
