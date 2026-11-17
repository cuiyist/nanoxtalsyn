import copy
import unittest
import to_site
import completeness_policy as policy
from completeness_conversion import AmbiguousChemicalUse

QUOTE='Synthetic fixture: dissolve 2 g sodium chloride in water; measured emission is 600 nm and quantum yield is 50 percent.'


def document():
    fact=lambda value,unit=None:{'value':value,'quote':QUOTE,'page':1,**({'unit':unit} if unit else {})}
    return {'id':'synthetic','doi':'10.0000/synthetic','title':'Synthetic fixture','authors':'Example Author','year':2000,
        'check':policy.CALIBRATED_CHECK,'check_policy':policy.binding(),
        'pairs':[{'product':'NaCl particles','structure':{'composition':fact('NaCl'),'absorption_peak':fact(500,'nm'),
            'emission_peak':fact(600,'nm'),'plqy':fact(50,'%')},
            'recipe':{'chemicals':[{'name':'sodium chloride','role':'reagent','amount':2,'unit':'g','quote':QUOTE,'page':1}],
                'steps':[{'action':'dissolve','description':'Dissolve sodium chloride in water.','quote':QUOTE,'page':1,'uses':['NaCl']}]}}]}


class Tests(unittest.TestCase):
    def test_actual_adoption_policy(self):
        p=policy.load_policy();self.assertEqual(p['adopted_check_variant'],5)
        self.assertEqual(set(p['optical_fields']),{'emission_peak','plqy'})
    def test_calibrated_marker_requires_exact_decision(self):
        doc=document();self.assertTrue(policy.is_checked_document(doc))
        doc['check_policy']['decision_sha256']='0'*64;self.assertFalse(policy.is_checked_document(doc))
        with self.assertRaises(ValueError):to_site.records_of(doc)
    def test_legacy_cannot_claim_calibrated_policy(self):
        doc=document();doc['check']=policy.LEGACY_CHECK
        self.assertFalse(policy.is_checked_document(doc))
        with self.assertRaises(ValueError):to_site.records_of(doc)
    def test_legacy_marker_stays_exact(self):
        for marker in (None,'one pass, quotes found',policy.LEGACY_CHECK+' ',policy.CALIBRATED_CHECK):
            self.assertFalse(policy.is_checked_document({'check':marker}))
        self.assertTrue(policy.is_checked_document({'check':policy.LEGACY_CHECK}))
    def test_alias_inputs_link_to_material(self):
        _,records=to_site.records_of(document());r=records[0]
        self.assertIn(r['materials'][0]['id'],r['operations'][0]['inputs'])
    def test_optics_gate_applies_without_legacy_opt_in(self):
        _,records=to_site.records_of(document())
        self.assertEqual({m['property'] for m in records[0]['measurements']},
                         {'photoluminescence_peak','photoluminescence_quantum_yield'})
    def test_legacy_opt_in_cannot_override_absorption_hold(self):
        _,records=to_site.records_of(document(),include_optical=True)
        self.assertNotIn('absorption_peak',{m['property'] for m in records[0]['measurements']})
    def test_distinct_charge_ambiguity_holds(self):
        doc=document();chemicals=doc['pairs'][0]['recipe']['chemicals']
        chemicals.append({**chemicals[0],'amount':4})
        with self.assertRaises(AmbiguousChemicalUse):to_site.records_of(doc)
    def test_distinct_charges_preserved_without_guessed_use(self):
        doc=document();recipe=doc['pairs'][0]['recipe'];recipe['steps']=[]
        recipe['chemicals'].append({**recipe['chemicals'][0],'amount':4})
        _,records=to_site.records_of(doc);materials=records[0]['materials']
        self.assertEqual(len(materials),2);self.assertNotEqual(materials[0]['id'],materials[1]['id'])
    def test_status_scope_and_input_preservation(self):
        doc=document();before=copy.deepcopy(doc);builder,records=to_site.records_of(doc);r=records[0]
        self.assertEqual(doc,before);self.assertEqual(r['quality']['review_status'],'source_extracted')
        self.assertIn('CHECK V5',r['quality']['review_scope'])
        self.assertEqual(to_site.inventory_entry(builder,doc,[r['record_id']])['notes'],[r['quality']['review_scope']])
    def test_unchecked_metadata_cannot_change_optics(self):
        doc=document();doc['check_policy']['optical_fields']=['absorption_peak']
        self.assertFalse(policy.is_checked_document(doc))

if __name__=='__main__':unittest.main()
