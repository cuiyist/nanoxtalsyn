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
        p=policy.load_policy();self.assertEqual(p['adopted_check_variant'],6)
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
        self.assertIn('CHECK V6',r['quality']['review_scope'])
        self.assertEqual(to_site.inventory_entry(builder,doc,[r['record_id']])['notes'],[r['quality']['review_scope']])
    def test_unchecked_metadata_cannot_change_optics(self):
        doc=document();doc['check_policy']['optical_fields']=['absorption_peak']
        self.assertFalse(policy.is_checked_document(doc))
    def test_number_locator_is_separate_from_name_and_step_locator(self):
        doc=document();pair=doc['pairs'][0]
        pair['recipe']['chemicals'][0]['amount_page']=2
        pair['recipe']['steps'][0].update(temperature=25, temperature_unit='C',temperature_page=3)
        r=to_site.records_of(doc)[1][0]
        self.assertEqual(r['materials'][0]['evidence'][0]['locator'],'Main PDF p.1')
        self.assertEqual(r['materials'][0]['quantities']['mass']['evidence'][0]['locator'],'Main PDF p.2')
        self.assertEqual(r['operations'][0]['evidence'][0]['locator'],'Main PDF p.1')
        self.assertEqual(r['operations'][0]['parameters']['temperature']['evidence'][0]['locator'],'Main PDF p.3')
    def test_check_v6_admits_only_calibrated_one_sided_fields(self):
        from completeness_check import check
        left=document()
        right=copy.deepcopy(left)
        right['pairs'][0]['recipe']['chemicals'][0].pop('amount')
        right['pairs'][0]['structure'].pop('emission_peak')
        right['pairs'][0]['structure'].pop('plqy')
        pairs=check('[page 1]\n'+QUOTE,left,right,6)
        self.assertEqual(pairs[0]['recipe']['chemicals'][0]['amount'],2)
        self.assertEqual(pairs[0]['structure']['emission_peak']['value'],600)
        self.assertNotIn('plqy',pairs[0]['structure'])
        right['pairs'][0]['structure']['emission_peak']={'value':650,'unit':'nm','quote':QUOTE}
        self.assertNotIn('emission_peak',check('[page 1]\n'+QUOTE,left,right,6)[0]['structure'])
    def test_w_roles_run_after_complete_chemical_and_step_binding(self):
        doc=document();pair=doc['pairs'][0];pair['product']='CdSe/ZnS research sample'
        pair['structure']={'composition':{'value':'CdSe/ZnS','page':1},
                           'architecture':{'value':'core/shell','page':1}}
        def chemical(name,page,quote,amount=None):
            return {'name':name,'role':'metal source','amount':amount,'unit':'mg',
                    'quote':quote,'page':page}
        pair['recipe']={'chemicals':[
            chemical('CdSe',1,'Use CdSe particles.',2),chemical('CdSe core',2,'Mix the CdSe core.'),
            chemical('ZnS shell',2,'The resulting sample had a ZnS shell.')],
            'steps':[{'action':'mix','description':'Mix the CdSe core.','page':2,
                      'quote':'Mix the CdSe core.','uses':['CdSe core']}]}
        record=to_site.records_of(doc)[1][0]
        self.assertEqual([(m['name'],m['role']) for m in record['materials']],[('CdSe','starting_particles')])
        starting=record['materials'][0]
        self.assertEqual(starting['quantities']['mass']['value'],2)
        self.assertEqual({e['locator'] for e in starting['evidence']},{'Main PDF p.1','Main PDF p.2'})
        self.assertEqual(record['operations'][0]['inputs'],[starting['id']])

if __name__=='__main__':unittest.main()
