from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from method_recipe_patterns import all_precursor_ids,declared_sources,family_order,recipe_class


class RouteFallback(unittest.TestCase):
    def identity(self,m):
        return {'key':m['name'],'label':m['name'],'elements':set(m.get('elements',[]))}

    def source(self,ms):
        return declared_sources({'material':{'formula':'CdSe'},'materials':ms},'Cd',True,identity=self.identity,excluded_source=lambda m:False)

    def test_explicit_role_first_and_starting_particles_substrate_not_sources(self):
        m=[{'name':'Cadmium acetate','role':'cation precursor','elements':['Cd']},
           {'name':'Cadmium oxide','role':'reagent','elements':['Cd']},
           {'name':'CdSe','role':'starting_particles','elements':['Cd','Se']},
           {'name':'CdSe substrate','role':'substrate','elements':['Cd','Se']}]
        self.assertEqual(self.source(m)['key'],'Cadmium acetate')
        m[0]['role']='reagent';self.assertIsNone(self.source(m))
        self.assertEqual(self.source(m[1:])['key'],'Cadmium oxide')

    def test_product_is_not_reinferred_as_source(self):
        self.assertIsNone(self.source([{'name':'CdSe','formula':'CdSe','role':'metal_precursor','elements':['Cd','Se']}]))

    def test_nonmetal_precursor_does_not_block_metal_composition_fallback(self):
        ms=[{'name':'Cadmium oxide','role':'reagent','elements':['Cd','O']},
            {'name':'Selenium source','role':'non-metal precursor','elements':['Se']}]
        self.assertEqual(self.source(ms)['key'],'Cadmium oxide')

    def test_heat_then_linked_inject_distinct_from_unlinked_heat(self):
        record={'material_states':[{'id':'mix','parent_ids':['a']}],
                'operations':[{'id':'s1','action':'heat','inputs':['a'],'outputs':['mix']},
                              {'id':'s2','action':'inject','inputs':['b','mix'],'depends_on':['s1']}]}
        self.assertEqual(recipe_class(record,['a','b']),'Hot injection')
        record['operations'][1]['inputs']=['b'];self.assertEqual(recipe_class(record,['a','b']),'')

    def test_heat_up_only_when_all_precursors_are_heated_together(self):
        r={'materials':[{'id':'a'},{'id':'b'}],'operations':[{'action':'heat','inputs':['a','b']}],
           'material_states':[]}
        self.assertEqual(recipe_class(r,['a','b']),'Heat-up')
        r['operations'][0]['inputs']=['a'];self.assertEqual(recipe_class(r,['a','b']),'')
        r['operations'][0]['description']='Heat in a sealed autoclave';self.assertEqual(recipe_class(r,['a','b']),'Solvothermal or hydrothermal')

    def test_two_metal_feeds_do_not_establish_a_complete_binary_heat_up(self):
        r={'materials':[{'id':'oxide','role':'metal precursor'},{'id':'acetate','role':'cation precursor'}],
           'operations':[{'action':'heat','inputs':['oxide','acetate']}], 'material_states':[]}
        def named():
            return all_precursor_ids(r['materials'],'Cd',['Se'],role_matches=lambda *_:False,excluded_source=lambda _:False)
        self.assertEqual(named(),[])
        self.assertEqual(recipe_class(r,named()),'')
        r['materials'].append({'id':'selenium','role':'non-metal precursor'})
        self.assertEqual(named(),['acetate','oxide','selenium'])
        self.assertEqual(recipe_class(r,named()),'')
        r['operations'][0]['inputs'].append('selenium')
        self.assertEqual(recipe_class(r,named()),'Heat-up')

    def test_linking_to_cooled_mixture_does_not_infer_hot_injection(self):
        record={'material_states':[{'id':'hot','parent_ids':['a']},{'id':'cold','parent_ids':['hot']}],
                'operations':[{'action':'heat_clear','inputs':['a'],'outputs':['hot']},
                              {'action':'cool_to_ambient','inputs':['hot'],'outputs':['cold']},
                              {'action':'inject','inputs':['b','cold']}]}
        self.assertEqual(recipe_class(record,['a','b']),'')

    def test_solution_precedes_larger_vapour_family(self):
        large={'kind':'synthesis','route':'Molecular beam epitaxy','paper_count':100,'earliest_year':1980,'id':'a','label':'MBE'}
        small={'kind':'synthesis','route':'Heat-up','paper_count':5,'earliest_year':1990,'id':'b','label':'Heat-up'}
        self.assertEqual(sorted([large,small],key=family_order)[0],small)


class PriorSourceRoles(unittest.TestCase):
    def test_recognizable_bare_particle_or_layer_is_not_a_source(self):
        from method_families import pick_source
        entry={'id':'m','name':'Se','formula':'Se','role':'starting_particles'}
        record={'record_id':'demo-cdse-1','material':{'formula':'CdSe'},'materials':[entry]}
        for role in ('starting_particles','starting particles','grown_layer','substrate'):
            entry['role']=role
            self.assertEqual(pick_source(record,'Se',False),(None,'missing_source'))
        entry['role']='nonmetal_precursor'
        source,reason=pick_source(record,'Se',False)
        self.assertIsNone(reason)
        self.assertEqual(source['label'],'Se')
