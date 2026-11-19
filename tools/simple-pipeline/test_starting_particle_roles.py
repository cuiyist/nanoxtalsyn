"""Synthetic regression cases for the owner W graph-preservation rule."""
import unittest

from starting_particle_roles import revise


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
